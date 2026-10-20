"""The yellow centre paint of the Lake Murray north roads, MEASURED off public-domain NAIP (ledger 0054, P3 repair
round 2).

Why this exists. P1's intermediate placed every undivided road's centre paint from the aerial EYE readings
(source/expansion/aerial__widths_eye.csv): one reading every ~250 m, each splitting the curb-to-curb width into a left
carriageway, a median and a right carriageway by eye. Between readings the split was interpolated, and where OSM maps
one way (Jackson north, Princess View) the median was centred on that line. The truth lens of repair round 1 traced
the real paint in NAIP at 58 stations and found Jackson's painted median ~1.65 m to one side of the built one for
~1 km (s 600-1600), 2-3 m at s 380-520 — the curbs right, the lanes split wrong (OSM: 3 lanes one way, 2 the other) —
and Princess View s 680-1000 a ~5 m painted centre lane where the build had a plain double yellow. This tool measures
the real centre paint every SPACING_M along every piece and writes it beside the eye readings, where
tools/author_expansion.py reads it (source/expansion/aerial__paint_north.json).

    python tools/aerial_paint_north.py [--track <tracks/san-diego-lake-murray>] [--cache DIR] [--no-fetch]

HOW. NAIP true colour from The National Map's ImageServer in EPSG:3857 at a 0.3 m ground pixel (the San Diego
quarter-quads are UTM 11; tools/aerial/naip.py is pinned to UTM 13 for the Lariat, so this tool asks in web
mercator and converts each local (x, z) through the loop's own lon/lat series, author_expansion.Frame). TLS
verification is always on (scripts.tls.https_context). Windows are cached on disk (default
%LOCALAPPDATA%/airoso/naip_sd3857, never the repo); a cached window is reused only when its bbox and size match.

SAMPLING (profiles(), cached as profiles_<intermediate sha>_*.json.gz beside the windows). At every station of the
intermediate (pieces[].stations, s every 2.5 m, the station's own left normal) a cross profile over GRID every DL_M,
each sample the mean of ALONG_N readings ALONG_STEP_M apart along the road, of yellowness = min(R, G) - B (paint is
yellow; asphalt, concrete and shadow are grey; tree canopy is green, its red low).

READING (measure()). The station line is OSM's chords with sigma-4 m corners, the real road a smooth curve, so in the
station frame the real paint wanders by the chords' sagitta (up to ~2.5 m on Jackson): every profile is re-read about
the station line smoothed by a gaussian of FRAME_SIGMA_M (smooth_frame), the profiles within +-SMOOTH_HALF_M are
averaged (a single shadow, car or crack cannot make a line), and the mean profile between the curbs less
CENTRE_CLEAR_M each side is read:
  * yellow stretches (segments()): at least SEG_MIN and half the profile's peak over its own median (the asphalt);
  * read_segments(): the stretch nearest the expected centre and a partner MEDIAN_SEP_M from it (at least PAIR_RATIO
    of its strength) = a painted median's two faces, its centre their midpoint and its width their distance +
    2 * FACE_IN_M (the built face's double yellow sits FACE_IN_M inside the face: expansion_pieces.PAIR_IN_M / 2 +
    0.06); one stretch at least MERGED_W_M wide = a narrow median whose faces blur into one (each face BLUR_M inside
    its half-height edge); a reading narrower than MEDIAN_MIN_M, or one narrow stretch, = one double yellow at its
    centroid; nothing = no reading (shadow, a junction, a crosswalk).
Along the road (clean()): a reading more than SANITY_M off the intermediate's own centre is not centre paint (a painted
curb return at a side street); one more than OUTLIER_M off the running median of its neighbours over +-OUTLIER_HALF_M
is dropped; a run of one kind shorter than KIND_MIN_M between runs of the other is dropped; gaps up to GAP_MAX_M
between readings of one kind are interpolated; longer gaps keep the intermediate's values. Every station is measured,
raised medians included: tools/author_expansion.py decides what it takes (the undivided roads' paint, and the outline
of the raised islands the aerial shows, MEASURED_ISLANDS).

Writes source/expansion/aerial__paint_north.json: per piece, per station s the stretches read (smooth frame), the frame
offset, and `use` = {kind, centre_off_m (+ = left of the J-order direction, the intermediate's frame), width_m (0 = a
double yellow), how: read / interpolated} or why it was dropped, plus the NAIP windows' provenance. Every threshold here is [invented] and listed in fleet/GATES-CHANGELOG.md (2026-10-19
repair round 2).
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
for _p in (str(AIROSO), str(AIROSO / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.tls import https_context  # noqa: E402  (verification on, never disabled)

TRACK_DEFAULT = AIROSO / "tracks" / "san-diego-lake-murray"
SERVICE = "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer"
UA = {"User-Agent": "airoso-aerial-paint/1.0 (public-domain NAIP measurement; small windows)"}
RE = 6378137.0

PX_GROUND_M = 0.3      # the service's own pixel (the source is 0.6 m)
WIN_HALF_M = 150.0     # [invented] a window's half size on the ground
WIN_EVERY_M = 200.0    # [invented] a window centred every this along a piece
DL_M = 0.1             # [invented] cross-profile step
ALONG_N = 5            # [invented] readings averaged along the road per cross-profile sample ...
ALONG_STEP_M = 1.0     # [invented] ... this far apart (+-2 m)
EDGE_CLEAR_M = 2.5     # [invented] the profile stays this far inside the curbs (gutter pans, bike-lane symbols)
SEG_MIN = 6.0          # [invented] a yellow stretch stands at least this above the zone's asphalt (NAIP 8-bit units)
MEDIAN_SEP_M = (0.9, 6.5)  # [invented] two stretches this far apart (centroids) read as a painted median's faces
PAIR_RATIO = 0.35      # [invented] the weaker face's stretch peaks at least this fraction of the stronger
MERGED_W_M = 1.3       # [invented] one stretch at least this wide is a narrow median whose two faces blur together
BLUR_M = 0.35          # [invented] a blurred double yellow's centre lies this far inside its half-height edge
MEDIAN_MIN_M = 1.6     # [invented] a reading narrower than this is ONE double yellow: NAIP's 0.6 m pixel spreads a
                       # 0.36 m double yellow to a 1.2-1.4 m stretch, which reads 1.0-1.4 m wide (Princess View s 100-380)
FACE_IN_M = 0.18       # expansion_pieces: a face's double yellow is centred PAIR_IN_M / 2 + 0.06 inside the face
SMOOTH_HALF_M = 7.5    # [invented] the cross profiles are stacked (mean) over +- this along the road
FRAME_SIGMA_M = 15.0   # [invented] the smooth frame the profiles are stacked in: the station line, gaussian sigma
CENTRE_CLEAR_M = 3.3   # [invented] the centre paint is looked for this far inside each curb: a bike lane
                       # (expansion_pieces BIKE_LINE_M 1.8 m) + half a lane; the narrowest real carriageway on
                       # Jackson (s 380-520, one lane down) leaves the paint ~3.8 m off the curb
SANITY_M = 5.0         # [invented] a reading this far off the intermediate's centre is not centre paint (step 0)
OUTLIER_M = 1.5        # [invented] a reading this far off its neighbours' running median is dropped ...
OUTLIER_HALF_M = 25.0  # [invented] ... the running median over +- this along the road
KIND_MIN_M = 10.0      # [invented] a run of one kind (median / line) shorter than this between the other is dropped
GAP_MAX_M = 30.0       # [invented] a gap in the readings up to this long is interpolated; longer keeps the intermediate
RAISED = ("planted", "terracotta", "nose")


# ------------------------------------------------------------------------------------------------ NAIP (EPSG:3857)

def default_cache() -> Path:
    env = os.environ.get("AIROSO_NAIP_SD_CACHE")
    if env:
        return Path(env)
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "airoso" / "naip_sd3857"


def merc(lon, lat):
    return RE * math.radians(lon), RE * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def _get(url, tries=8):
    last = None
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), context=https_context(), timeout=120) as r:
                return r.read(), r.headers.get("Content-Type", "")
        except Exception as e:  # the service answers 502 now and then
            last = e
            time.sleep(3 + 5 * k)
    raise last


class Window:
    def __init__(self, meta, cache):
        from PIL import Image
        self.m = meta
        im = Image.open(Path(cache) / meta["file"]).convert("RGB")
        self.W, self.H = im.size
        self.px = im.load()

    def sample(self, mx, my):
        xmin, ymin, xmax, ymax = self.m["bbox3857"]
        p = self.m["px3857"]
        i = (mx - xmin) / p - 0.5
        j = (ymax - my) / p - 0.5
        if i < 1 or j < 1 or i > self.W - 2 or j > self.H - 2:
            return None
        i0, j0 = int(i), int(j)
        fi, fj = i - i0, j - j0
        out = [0.0, 0.0, 0.0]
        for (ii, jj, w) in ((i0, j0, (1 - fi) * (1 - fj)), (i0 + 1, j0, fi * (1 - fj)),
                            (i0, j0 + 1, (1 - fi) * fj), (i0 + 1, j0 + 1, fi * fj)):
            c = self.px[ii, jj]
            out[0] += w * c[0]
            out[1] += w * c[1]
            out[2] += w * c[2]
        return out


def window(cache, wid, lon, lat, fetch=True):
    cache = Path(cache)
    mx, my = merc(lon, lat)
    k = 1.0 / math.cos(math.radians(lat))
    px = PX_GROUND_M * k
    W = int(round(2 * WIN_HALF_M / PX_GROUND_M))
    xmin, ymin = round(mx - W * px / 2, 2), round(my - W * px / 2, 2)
    bbox = [xmin, ymin, round(xmin + W * px, 2), round(ymin + W * px, 2)]
    mp = cache / f"{wid}.json"
    if mp.exists():
        m = json.loads(mp.read_text(encoding="utf-8"))
        if m["bbox3857"] == bbox and m["W"] == W and (cache / m["file"]).exists():
            return m
    if not fetch:
        raise SystemExit(f"[paint] window {wid} not cached in {cache}; run with fetching allowed")
    cache.mkdir(parents=True, exist_ok=True)
    q = {"bbox": ",".join(str(v) for v in bbox), "bboxSR": 3857, "imageSR": 3857, "size": f"{W},{W}",
         "format": "png", "pixelType": "U8", "interpolation": "RSP_BilinearInterpolation", "bandIds": "0,1,2",
         "noData": "", "f": "image"}
    url = SERVICE + "/exportImage?" + urllib.parse.urlencode(q)
    data, ctype = _get(url)
    if not ctype.startswith("image/"):
        raise RuntimeError(f"{wid}: not an image ({ctype}): {data[:300]!r}")
    (cache / f"{wid}_rgb.png").write_bytes(data)
    qurl = SERVICE + "/query?" + urllib.parse.urlencode({
        "where": "Category=1", "geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects", "outFields": "Name,Year,State,acquisition_date,resolution_value",
        "returnGeometry": "false", "f": "json"})
    try:
        cat = [f["attributes"] for f in json.loads(_get(qurl)[0].decode("utf-8")).get("features", [])]
    except Exception as e:  # provenance only
        cat = [{"error": str(e)}]
    m = {"id": wid, "bbox3857": bbox, "W": W, "px3857": px, "file": f"{wid}_rgb.png", "url": url, "bytes": len(data),
         "centre_lonlat": [round(lon, 7), round(lat, 7)], "catalog": cat,
         "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    mp.write_text(json.dumps(m, indent=1), encoding="utf-8", newline="\n")
    return m


# ------------------------------------------------------------------------------------------------ measurement

def stacked_profile(offs, ys, lo, hi):
    """the MEAN raw yellowness of a window of cross profiles (already in the smooth frame), between offsets lo and hi:
    [(offset, value)], a sample kept where at least half the profiles read"""
    out = []
    for k, o in enumerate(offs):
        if not (lo <= o <= hi):
            continue
        vals = [y[k] for y in ys if y[k] is not None]
        if len(vals) >= max(1, len(ys) // 2):
            out.append((o, sum(vals) / len(vals)))
    return out


def segments(prof):
    """the yellow stretches of a stacked profile: above the zone's asphalt (its median) by at least half the profile's
    peak and at least SEG_MIN; [(lo, hi, centroid, peak)]"""
    if len(prof) < 10:
        return []
    vals = sorted(v for _o, v in prof)
    bg = vals[len(vals) // 2]
    top = vals[-1]
    thr = bg + max(SEG_MIN, 0.5 * (top - bg))
    segs, cur = [], []
    for o, v in prof + [(None, None)]:
        if v is not None and v >= thr:
            cur.append((o, v - bg))
            continue
        if cur:
            w = sum(x[1] for x in cur)
            segs.append((cur[0][0], cur[-1][0], sum(x[0] * x[1] for x in cur) / w, max(x[1] for x in cur)))
            cur = []
    return segs


def read_segments(segs, centre_hint):
    """(kind, centre offset, width, strength) from a stacked profile's yellow stretches; None when nothing reads.
    The OUTERMOST two stretches no more than MEDIAN_SEP_M[1] apart are a painted median's two faces (each face's
    double yellow centred FACE_IN_M inside the face); one stretch wider than MERGED_W_M is a narrow painted median whose
    faces blur together at NAIP's 0.6 m (its faces BLUR_M inside the stretch's half-height edges); one narrower stretch
    is a plain double yellow."""
    if not segs:
        return None
    # the stretch nearest the expected centre, then any partner within the median spacing
    best = min(segs, key=lambda g: abs(g[2] - centre_hint) - 0.2 * g[3])
    near = [g for g in segs if g is not best and MEDIAN_SEP_M[0] <= abs(g[2] - best[2]) <= MEDIAN_SEP_M[1]
            and g[3] >= PAIR_RATIO * best[3]]
    if near:
        mate = max(near, key=lambda g: g[3])
        a, b = sorted((best[2], mate[2]))
        if (b - a) + 2 * FACE_IN_M >= MEDIAN_MIN_M:
            return ("median", (a + b) / 2, (b - a) + 2 * FACE_IN_M, min(best[3], mate[3]))
        return ("line", (a + b) / 2, 0.0, min(best[3], mate[3]))
    w = best[1] - best[0]
    if w >= MERGED_W_M:
        a, b = best[0] + BLUR_M, best[1] - BLUR_M
        if (b - a) + 2 * FACE_IN_M >= MEDIAN_MIN_M:
            return ("median", (a + b) / 2, (b - a) + 2 * FACE_IN_M, best[3])
    return ("line", best[2], 0.0, best[3])


GRID = (-18.0, 18.0)   # the cross-profile grid about the station line (every DL_M)


def profiles(track: Path, cache: Path, fetch=True, log=print):
    """per piece: [(s, [yellowness per GRID offset or None])] across every station inside the piece's cuts"""
    from author_expansion import Frame
    X = json.loads((track / "data" / "expansion.north.json").read_text(encoding="utf-8"))
    cl = json.loads((track / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    fr = Frame(cl["origin"])
    n = int(round((GRID[1] - GRID[0]) / DL_M))
    offs = [round(GRID[0] + k * DL_M, 3) for k in range(n + 1)]
    out = {"offs": offs, "windows": [], "pieces": {}}
    for pc in X["pieces"]:
        pid = pc["id"]
        cols = pc["columns"]
        rows = [dict(zip(cols, r)) for r in pc["stations"]]
        wins = []
        last = -1e9
        for r in rows:
            if r["s"] - last >= WIN_EVERY_M or r is rows[-1]:
                last = r["s"]
                lon, lat = fr.lonlat(r["x"], r["z"])
                m = window(cache, f"sd_{pid}_{int(r['s'])}", lon, lat, fetch)
                wins.append(Window(m, cache))
                out["windows"].append({k: m[k] for k in ("id", "bbox3857", "W", "px3857", "url", "centre_lonlat",
                                                          "catalog", "fetched_utc")})
        prof = []
        for i, r in enumerate(rows):
            a, b = rows[max(0, i - 1)], rows[min(len(rows) - 1, i + 1)]
            tx, tz = b["x"] - a["x"], b["z"] - a["z"]
            L = math.hypot(tx, tz) or 1.0
            tx, tz = tx / L, tz / L
            nx, nz = -tz, tx
            yel = []
            for o in offs:
                acc, c = 0.0, 0
                for k in range(ALONG_N):
                    al = (k - (ALONG_N - 1) / 2) * ALONG_STEP_M
                    x, z = r["x"] + nx * o + tx * al, r["z"] + nz * o + tz * al
                    lon, lat = fr.lonlat(x, z)
                    mx, my = merc(lon, lat)
                    v = None
                    for w in wins:
                        v = w.sample(mx, my)
                        if v is not None:
                            break
                    if v is None:
                        continue
                    acc += min(v[0], v[1]) - v[2]      # yellowness: paint has R and G both over B
                    c += 1
                yel.append(round(acc / c, 2) if c else None)
            prof.append((r["s"], yel))
        out["pieces"][pid] = prof
        log(f"[paint] {pid}: {len(prof)} cross profiles sampled")
    return out


def smooth_frame(rows, sigma_m):
    """the station line smoothed by a gaussian over +-3 sigma (truncated, renormalised at the ends): the real road is a
    smooth curve, the station line is OSM's chords with sigma-4 m corners (author_expansion SMOOTH_SIGMA_M), so the
    real paint wanders by the chords' sagitta in the station frame. Returns per station delta = the smooth line's
    offset along the station's own left normal (+ = left)."""
    n = len(rows)
    sg = sigma_m / 2.5
    h = int(math.ceil(3 * sg))
    w = [math.exp(-0.5 * (k / sg) ** 2) for k in range(-h, h + 1)]
    out = []
    for i in range(n):
        sx = sz = sw = 0.0
        for k in range(-h, h + 1):
            j = i + k
            if 0 <= j < n:
                sx += w[k + h] * rows[j]["x"]
                sz += w[k + h] * rows[j]["z"]
                sw += w[k + h]
        a, b = rows[max(0, i - 1)], rows[min(n - 1, i + 1)]
        tx, tz = b["x"] - a["x"], b["z"] - a["z"]
        L = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / L, tx / L
        out.append((sx / sw - rows[i]["x"]) * nx + (sz / sw - rows[i]["z"]) * nz)
    return out


def shift(hp, k):
    """the profile hp read k samples further left: out[j] = hp[j + k]"""
    n = len(hp)
    return [hp[j + k] if 0 <= j + k < n else None for j in range(n)]


def clean(recs):
    """the readings along the road -> what the intermediate takes (rec["use"] = {kind, centre_off_m, width_m, how}):
      0. a reading more than SANITY_M off the intermediate's own centre is not the centre paint (a painted curb at a
         side-street return) and is dropped;
      1. a reading whose centre is more than OUTLIER_M off the running median of the readings over +-OUTLIER_HALF_M is
         dropped (a curb return, a yellow car, a canopy edge);
      2. a run of one kind shorter than KIND_MIN_M between two runs of the other kind takes its neighbours' kind and
         is re-read from them by interpolation (a face lost under a shadow for a few metres);
      3. a gap no longer than GAP_MAX_M between two readings of the same kind is filled by linear interpolation;
         longer gaps keep the intermediate's own values (no measurement there: crosswalks, junction mouths)."""
    n = len(recs)
    h = int(round(OUTLIER_HALF_M / 2.5))
    cen = [q.get("centre_off_m") if "kind" in q else None for q in recs]
    ok = [False] * n
    for i in range(n):
        if cen[i] is None:
            continue
        if abs(cen[i] - float(recs[i]["built_off_m"] or 0.0)) > SANITY_M:
            cen[i] = None
            recs[i]["dropped"] = "off the road's centre"
            continue
        seg = sorted(c for c in cen[max(0, i - h):i + h + 1] if c is not None)
        ok[i] = abs(cen[i] - seg[len(seg) // 2]) <= OUTLIER_M
        if not ok[i]:
            recs[i]["dropped"] = "outlier"
    kind = [recs[i]["kind"] if ok[i] else None for i in range(n)]
    # 2. short runs of one kind between the other kind
    runs, i = [], 0
    while i < n:
        j = i
        while j + 1 < n and kind[j + 1] == kind[i]:
            j += 1
        runs.append([i, j, kind[i]])
        i = j + 1
    for k in range(1, len(runs) - 1):
        a, b, kd = runs[k]
        if kd is None:
            continue
        if (recs[b]["s"] - recs[a]["s"]) < KIND_MIN_M and runs[k - 1][2] == runs[k + 1][2] and runs[k - 1][2] not in (None, kd):
            for t in range(a, b + 1):
                ok[t] = False
                kind[t] = None
                recs[t]["dropped"] = "short run"
    vals = [(recs[i]["centre_off_m"], recs[i]["width_m"]) if ok[i] else None for i in range(n)]
    for i in range(n):
        if vals[i] is not None:
            recs[i]["use"] = {"kind": kind[i], "centre_off_m": vals[i][0], "width_m": vals[i][1], "how": "read"}
            continue
        a = next((t for t in range(i - 1, -1, -1) if vals[t] is not None), None)
        b = next((t for t in range(i + 1, n) if vals[t] is not None), None)
        if a is None or b is None or kind[a] != kind[b] or recs[b]["s"] - recs[a]["s"] > GAP_MAX_M:
            continue
        f = (recs[i]["s"] - recs[a]["s"]) / (recs[b]["s"] - recs[a]["s"])
        recs[i]["use"] = {"kind": kind[a], "centre_off_m": round(vals[a][0] + (vals[b][0] - vals[a][0]) * f, 2),
                          "width_m": round(vals[a][1] + (vals[b][1] - vals[a][1]) * f, 2), "how": "interpolated"}
    return recs


def measure(track: Path, prof: dict, log=print):
    X = json.loads((track / "data" / "expansion.north.json").read_text(encoding="utf-8"))
    offs = prof["offs"]
    out = {}
    half = int(round(SMOOTH_HALF_M / 2.5))
    for pc in X["pieces"]:
        pid = pc["id"]
        cols = pc["columns"]
        rows = [dict(zip(cols, r)) for r in pc["stations"]]
        cuts = pc.get("cuts") or {}
        s0 = (cuts.get("start") or {}).get("s", 0.0)
        s1 = (cuts.get("end") or {}).get("s", pc["length_m"])
        delta = smooth_frame(rows, FRAME_SIGMA_M)
        # every profile re-read about the smooth line (offset o in the smooth frame = o + delta in the station frame)
        ys = [shift(y, int(round(delta[i] / DL_M))) for i, (_s, y) in enumerate(prof["pieces"][pid])]
        recs = []
        for i, r in enumerate(rows):
            if not (s0 + EDGE_CLEAR_M <= r["s"] <= s1 - EDGE_CLEAR_M):
                continue
            d = delta[i]
            # the centre zone (station frame), carried into the smooth frame
            lo = r["right_m"] + CENTRE_CLEAR_M
            hi = r["left_m"] - CENTRE_CLEAR_M
            segs = segments(stacked_profile(offs, ys[max(0, i - half):i + half + 1], lo - d, hi - d))
            q = read_segments(segs, float(r["median_off_m"] or 0.0) - d)
            rec = {"s": r["s"], "frame_delta_m": round(d, 3),
                   "stretches_smooth_frame": [[round(g[0], 2), round(g[1], 2), round(g[2], 2), round(g[3], 1)] for g in segs],
                   "built_type": r["median_type"], "built_off_m": r["median_off_m"], "built_w_m": r["median_w_m"],
                   "raised": r["median_type"] in RAISED, "zone": [round(lo, 2), round(hi, 2)]}
            if q is not None:
                rec.update({"kind": q[0], "centre_off_m": round(q[1] + d, 2), "width_m": round(q[2], 2),
                            "strength": round(q[3], 1)})
            recs.append(rec)
        clean(recs)
        out[pid] = recs
        meas = [q for q in recs if not q["raised"] and q.get("use")]
        dd = sorted(abs(q["use"]["centre_off_m"] - float(q["built_off_m"] or 0.0)) for q in meas)
        ad = sorted(abs(v) for v in delta)
        log(f"[paint] {pid}: {len(recs)} stations in the cuts, {len(meas)} taken (not raised; "
            f"{sum(1 for q in meas if q['use']['kind'] == 'median')} as a painted median, {sum(1 for q in meas if q['use']['how'] == 'interpolated')} interpolated); |measured - built centre| p50 "
            f"{dd[len(dd) // 2] if dd else None} p90 {dd[int(0.9 * (len(dd) - 1))] if dd else None}; station line vs "
            f"its {FRAME_SIGMA_M:g} m smooth: |delta| p95 {ad[int(0.95 * (len(ad) - 1))]:.2f} max {ad[-1]:.2f} m")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--track", default=str(TRACK_DEFAULT))
    ap.add_argument("--cache", default=None)
    ap.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args(argv)
    track = Path(a.track)
    cache = Path(a.cache) if a.cache else default_cache()
    import gzip
    import hashlib
    xp = track / "data" / "expansion.north.json"
    key = hashlib.sha256(xp.read_bytes()).hexdigest()[:12]
    pp = cache / f"profiles_{key}_{ALONG_N}_{DL_M}_ming.json.gz"     # the sampled cross profiles (slow to sample)
    if pp.exists():
        prof = json.loads(gzip.decompress(pp.read_bytes()).decode("utf-8"))
        print(f"[paint] cross profiles from {pp}")
    else:
        prof = profiles(track, cache, fetch=not a.no_fetch)
        cache.mkdir(parents=True, exist_ok=True)
        pp.write_bytes(gzip.compress(json.dumps(prof).encode("utf-8")))
    res = measure(track, prof)
    doc = {"_doc": __doc__.split("\n\n")[0] + " Written by tools/aerial_paint_north.py; read by "
                   "tools/author_expansion.py (paint_measured).",
           "ledger": "0054", "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "frame": "the intermediate's stations (data/expansion.north.json pieces[].stations); offsets + = left of the "
                    "J-order direction",
           "intermediate_sha256_12": key,
           "imagery": "USGS, USDA, The National Map: Orthoimagery (NAIP; public domain), EPSG:3857, TLS verified",
           "parameters": {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float, tuple))},
           "windows": prof["windows"], "pieces": res}
    p = track / "source" / "expansion" / "aerial__paint_north.json"
    p.write_text(json.dumps(doc, indent=0) + "\n", encoding="utf-8", newline="\n")
    print(f"[paint] wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
