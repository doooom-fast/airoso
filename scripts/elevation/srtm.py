"""Sample elevations (metres) outside USGS 3DEP coverage — i.e. every non-US track.

Primary source is **SRTM 30 m** via the keyless opentopodata.org public API. That choice is
measured, not assumed: built the Nordschleife from OSM + each candidate DEM and scored the road
profile against the Kunos laser scan (the answer key). Registered road-surface error, de-meaned:

    srtm30m     3.8 m RMS   <- winner
    mapzen      3.8 m RMS   (serves SRTM in this region; identical numbers)
    srtm90m     5.9 m RMS
    eudem25m    6.5 m RMS
    aster30m    8.3 m RMS
    Copernicus 90 m via Open-Meteo   9.7 m RMS   <- what this module used to do

Copernicus GLO-90 is a *surface* model and Open-Meteo rounds it to whole metres. Over dense forest
— which is most of the Eifel — it returns canopy, not road, and the integer rounding turns a 3 m
centerline step into a 33 % grade spike. Both faults are gone with SRTM 30 m, whose C-band radar
partially penetrates canopy and which comes back as floats.

Open-Meteo stays wired as a fallback so a build still completes if opentopodata is down.

Same interface as ``usgs_3dep.sample_points`` so heightfield.py can swap sources freely.

TLS is verified through ``scripts.tls.https_context()``, like every other live fetch. Until
2026-10-11 this module switched verification off (``check_hostname=False``, ``CERT_NONE``) on the
belief that "this box's Python 3.14 ships expired root certs". The real fault was one expired
cross-certificate in the Windows Intermediate store. Of the engine's HTTPS hosts it breaks only
overpass-api.de's chain; both hosts here verify with the default context too (see scripts/tls.py).

Run:  python -m scripts.elevation.srtm      (self-test)
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from scripts.tls import https_context

OPENTOPODATA_URL = "https://api.opentopodata.org/v1/{dataset}"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/elevation"
USER_AGENT = "prodrive-ac-builder/0.1"

DATASET = "srtm30m"        # measured winner; see module docstring
NATIVE_M = 30.0            # source resolution — sampling finer than this buys nothing
OTD_BATCH = 100            # opentopodata: 100 locations per call, 1 call/s, 1000 calls/day

Vertex = tuple[float, float]  # (lon, lat)


# --- transports -----------------------------------------------------------------

def _otd_batch(batch: list[Vertex], *, dataset: str, retries: int) -> list[float | None]:
    locs = "|".join(f"{lat:.6f},{lon:.6f}" for lon, lat in batch)
    url = OPENTOPODATA_URL.format(dataset=dataset) + "?" + urllib.parse.urlencode({"locations": locs})
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60, context=https_context()) as resp:
                payload = json.loads(resp.read().decode())
            if payload.get("status") != "OK":
                raise RuntimeError(payload.get("error", "opentopodata status != OK"))
            return [r["elevation"] for r in payload["results"]]
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503):
                time.sleep(5 * (attempt + 1))
                continue
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    return [None] * len(batch)


def _meteo_batch(batch: list[Vertex], *, retries: int) -> list[float | None]:
    lats = ",".join(f"{lat:.6f}" for _, lat in batch)
    lons = ",".join(f"{lon:.6f}" for lon, _ in batch)
    url = f"{OPEN_METEO_URL}?latitude={lats}&longitude={lons}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60, context=https_context()) as resp:
                payload = json.loads(resp.read().decode())
            return [float(e) if e is not None else None for e in payload.get("elevation", [])]
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                time.sleep(15 * (attempt + 1))
                continue
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    return [None] * len(batch)


def _fetch(points: list[Vertex], *, dataset: str, retries: int) -> list[float | None]:
    """opentopodata first; fall back to Open-Meteo wholesale if it cannot be reached."""
    out: list[float | None] = []
    try:
        for i in range(0, len(points), OTD_BATCH):
            if i:
                time.sleep(1.1)                      # published rate limit: 1 call/s
            out += _otd_batch(points[i:i + OTD_BATCH], dataset=dataset, retries=retries)
            if len(points) > OTD_BATCH * 4:
                print(f"    [{dataset}] {min(i + OTD_BATCH, len(points))}/{len(points)}", flush=True)
        return out
    except Exception as exc:
        print(f"  [srtm] opentopodata unavailable ({exc}); falling back to Open-Meteo 90 m")
    out = []
    for i in range(0, len(points), 80):
        if i:
            time.sleep(3.0)
        out += _meteo_batch(points[i:i + 80], retries=5)
    return out


# --- gap filling ----------------------------------------------------------------

def _fill_none(values: list[float | None]) -> list[float]:
    n = len(values)
    if all(v is None for v in values):
        raise SystemExit("elevation source returned no data — check coverage.")
    out: list[float] = [float(v) if v is not None else float("nan") for v in values]
    i = 0
    while i < n:
        if out[i] != out[i]:                          # NaN
            j = i
            while j < n and out[j] != out[j]:
                j += 1
            left = out[i - 1] if i > 0 else out[j]
            right = out[j] if j < n else out[i - 1]
            for k in range(i, j):
                t = (k - i + 1) / (j - i + 1)
                out[k] = left + (right - left) * t
            i = j
        else:
            i += 1
    return out


# --- public API -----------------------------------------------------------------

def sample_points(points: list[Vertex], *, dataset: str = DATASET,
                  spacing_m: float = 3.0, retries: int = 4) -> list[float]:
    """Return an elevation (m) for each (lon, lat), in order.

    Requests are decimated to the DEM's own resolution and linearly interpolated back up:
    a 30 m source cannot resolve a 3 m step, so querying every centerline point would spend
    10x the daily API budget to manufacture a staircase. ``spacing_m`` is the input spacing.
    """
    n = len(points)
    if n == 0:
        return []

    stride = max(1, int(NATIVE_M / max(spacing_m, 1e-6)))
    if stride == 1 or n <= OTD_BATCH:
        return _fill_none(_fetch(points, dataset=dataset, retries=retries))

    key_idx = list(range(0, n, stride))
    if key_idx[-1] != n - 1:
        key_idx.append(n - 1)
    print(f"  [srtm] {n} pts -> {len(key_idx)} samples at {dataset} native "
          f"(~{stride * spacing_m:.0f} m)")
    key_z = _fill_none(_fetch([points[i] for i in key_idx], dataset=dataset, retries=retries))

    out = [0.0] * n
    ki = 0
    for j in range(n):
        while ki < len(key_idx) - 1 and key_idx[ki + 1] <= j:
            ki += 1
        if ki >= len(key_idx) - 1:
            out[j] = key_z[-1]
            continue
        a, b = key_idx[ki], key_idx[ki + 1]
        t = (j - a) / (b - a)
        out[j] = key_z[ki] + t * (key_z[ki + 1] - key_z[ki])
    return out


if __name__ == "__main__":
    test = [(6.942, 50.332), (6.95, 50.34)]          # Nürburgring
    print(f"{DATASET}: {sample_points(test)}")
