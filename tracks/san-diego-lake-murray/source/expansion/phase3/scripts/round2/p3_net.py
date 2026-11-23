"""Polite HTTPS for the Phase 3 Step 0 data run (data host, 2026-11-22).

3DEP getSamples in the exact request shape of scripts/elevation/usgs_3dep._sample_batch (POST multipoint in wkid 4326,
returnFirstValueOnly, f=json, 450 points a request as terrain_sample.CHUNK), but: one request at a time, User-Agent
airoso-fetch/1.0, TLS verified (CERT_REQUIRED + hostname), HTTPS-only redirects, back-off on 429 / 5xx, every byte
counted against a cap, every request logged. Responses are parsed as JSON data only.
"""
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "airoso-fetch/1.0"
GET_SAMPLES = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/getSamples"
CTX = ssl.create_default_context()
assert CTX.verify_mode == ssl.CERT_REQUIRED and CTX.check_hostname
GAP_S = 1.0                 # pause between requests
READ_MAX = 32 * 1024 * 1024


class Refused(Exception):
    pass


class HttpsOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.lower().startswith("https://"):
            raise Refused(f"non-https redirect refused: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX), HttpsOnly())


class Budget:
    def __init__(self, cap_bytes, log_path=None):
        self.cap, self.used, self.requests, self.log = int(cap_bytes), 0, 0, log_path
        self.backoffs = 0

    def note(self, rec):
        if self.log:
            with open(self.log, "a") as f:
                f.write(json.dumps(rec) + "\n")


def request(url, data, budget, headers=None, tries=8):
    """one HTTPS request (POST if data), polite; returns the body bytes"""
    if budget.used >= budget.cap:
        raise Refused(f"byte cap reached ({budget.used} of {budget.cap})")
    wait = 30.0
    last = None
    for k in range(tries):
        h = {"User-Agent": UA, "Accept": "application/json", "Accept-Encoding": "identity"}
        h.update(headers or {})
        req = urllib.request.Request(url, data=data, headers=h)
        t0 = time.time()
        try:
            with OPENER.open(req, timeout=180) as r:
                body = r.read(READ_MAX + 1)
                code = r.status
            if len(body) > READ_MAX:
                raise Refused("response over the read limit")
            budget.used += len(body) + (len(data) if data else 0)
            budget.requests += 1
            budget.note({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "url": url.split("?")[0],
                         "code": code, "bytes": len(body), "sent": len(data) if data else 0,
                         "s": round(time.time() - t0, 2)})
            time.sleep(GAP_S)
            return body
        except urllib.error.HTTPError as e:
            last = e
            budget.note({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "url": url.split("?")[0],
                         "code": e.code, "retry_in_s": wait})
            if e.code == 429 or 500 <= e.code < 600:
                budget.backoffs += 1
                ra = e.headers.get("Retry-After") if e.headers else None
                try:
                    w = max(wait, float(ra)) if ra else wait
                except ValueError:
                    w = wait
                time.sleep(w)
                wait = min(wait * 2, 1800.0)
                continue
            raise
        except Refused:
            raise
        except Exception as e:                    # timeouts, resets: back off and retry
            last = e
            budget.note({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "url": url.split("?")[0],
                         "error": repr(e)[:200], "retry_in_s": wait})
            time.sleep(wait)
            wait = min(wait * 2, 1800.0)
    raise RuntimeError(f"{url}: gave up after {tries} tries: {last!r}")


def sample_batch(batch, budget):
    """usgs_3dep._sample_batch's request and its echoed-location mapping; None where 3DEP has no value"""
    geometry = json.dumps({"points": [[lon, lat] for lon, lat in batch], "spatialReference": {"wkid": 4326}})
    body = urllib.parse.urlencode({"geometry": geometry, "geometryType": "esriGeometryMultipoint",
                                   "returnFirstValueOnly": "true", "f": "json"}).encode()
    raw = request(GET_SAMPLES, body, budget, {"Content-Type": "application/x-www-form-urlencoded"})
    payload = json.loads(raw.decode())
    if "error" in payload:
        raise RuntimeError(f"3DEP error: {str(payload['error'])[:300]}")
    by_loc = {}
    for s in payload.get("samples", []):
        loc = s.get("location", {})
        try:
            by_loc[(round(loc.get("x"), 6), round(loc.get("y"), 6))] = float(s["value"])
        except (TypeError, ValueError):
            pass
    return [by_loc.get((round(lon, 6), round(lat, 6))) for lon, lat in batch]


def sample_points(points, budget, chunk=450, progress=None):
    out = []
    for a in range(0, len(points), chunk):
        out += sample_batch(points[a:a + chunk], budget)
        if progress:
            progress(a // chunk + 1, -(-len(points) // chunk))
    return out
