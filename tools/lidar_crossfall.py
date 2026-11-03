"""Measure a street lap's REAL cross-slope from USGS 3DEP source lidar and write data/crossfall.json (ledger 0066).

Kevin 2026-11-03, after driving Sand Creek's 56th Ave -> Sand Creek Drive corner for real: "it dips and turns
dramatically for a passenger road ... it takes effort to keep the car on the correct side of the yellow line".
The built road there matched the 1 m DEM's heights within 0.2 m and was flat side to side; the 2020 source lidar shows
the real road rolling into that turn by 4 to 5 %. Asked to put it in: "Yes, build it".

Why not ``scripts.elevation.crossfall``: its footprint mode keeps a tilt only where it is >= 2 %, never INTO a curve
(L10 as first worded: "public streets are not superelevated"), and ramps every change at 0.12 %/m (3.6 % per 30 m),
so this corner would come out flat in the turn. Here the lidar IS the research L10 asks for (amended, ledger 0066), so
the measurement is used as measured, capped at the legacy 6 %.

Method, per station every ``STEP_M`` along the line build_mesh sweeps the road over and keys bank by:
``data/finished_centerline.json`` (corner-rounded and smoothed, 23 m shorter round Sand Creek than the draft line; the
first 0.31.0 keyed the draft line and its camber drifted up to 23 m along the lap and broke at the seam), or
``data/centerline.local.json`` before the first build:
  - the source lidar's points within ``HALF_M`` of the line across and ``ALONG_M`` along it: bridge-deck points
    (class 17) on the track's declared bridges (``capture.bridges``), ground points (class 2) everywhere else, so a
    deck overhead (an overpass) or a creek bed underneath never enters a road's fit;
  - a least-squares line z = a + b * lateral, refit ``TRIM_PASSES`` times without points over max(4 cm, 2.5 sd)
    from it (curbs, gutters); the tilt b is the cross-slope. A crowned road's halves cancel in it, so only the
    section's net tilt is kept (build_mesh's legacy file is one plane);
  - a fit is a road only with >= ``MIN_POINTS`` kept points, a residual sd <= ``MAX_SD_M`` and a tilt within
    ``MAX_READ_PCT``; anything else (an embankment, a median, a curb run) is dropped and the gap filled straight
    between its good neighbours, or held flat where the gap is longer than ``MAX_GAP_M``;
  - a ``SMOOTH_M`` along-lap median then mean, only enough to take the fit's noise out;
  - flat outside the track's ``road_profile.crossfall.spans_m`` when it declares any (the measured camber only where
    it has been checked against the seat), ramping in and out at ROLL_RATE;
  - capped at ``CAP_PCT``, then every change limited to ``ROLL_RATE`` per metre (scripts.elevation.crossfall's
    ``runoff``): the 56th Ave turn rolls in at about 0.16 %/m and passes untouched, where the DEM tool's 0.12 %/m
    flattened it; a reading that flips -7 % to +9 % inside 40 m (E 45th Ave by the creek, the line on an embankment
    rather than the pavement) becomes a ramp.

Writes data/crossfall.json in build_mesh's legacy shape (``station_m``, ``bank_rad``: + = LEFT edge up) with
``status: "measured"``, and caches the per-station fits in data/crossfall.lidar.json so a rerun (or a machine
without the lidar libraries) recomposes without fetching. Fetching needs numpy, scipy, laspy[lazrs] and pyproj.

    python tools/lidar_crossfall.py <project-dir> [--ept URL] [--refetch]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.geometry.projection import _meters_per_degree  # noqa: E402
from scripts.tls import https_context  # noqa: E402

EPT_DEFAULT = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_DRCOG_2_2020/ept.json"
STEP_M = 3.0          # station step: centerline.local.json's own vertex spacing
HALF_M = 4.5          # [invented] across: the 9 m two-lane carriageway each side of the line, inside the curbs
ALONG_M = 1.5         # [invented] along: half a station step either side, so neighbouring fits share no points
GROUND, DECK = 2, 17  # ASPRS classes
TRIM_PASSES = 4
TRIM_MIN_M = 0.04     # [invented] a residual under 4 cm is surface texture, never trimmed
MIN_POINTS = 12       # [invented] fewer kept points is no fit
MAX_SD_M = 0.08       # [invented] a road plane's residual: the 56th Ave turn's fits run 0.02 to 0.07 m
MAX_READ_PCT = 8.0    # [invented] a steeper reading is a bank or a curb run, not a carriageway
MAX_GAP_M = 30.0      # [invented] a longer run without a road fit is held flat
SMOOTH_M = 9.0        # [invented] three stations: the fit's noise out, a 15 m roll change kept
CAP_PCT = 6.0         # the legacy cap (scripts.elevation.crossfall CAP): rural superelevation maximum
ROLL_RATE = 0.2       # [invented] %/m (6 % per 30 m): just over the 56th Ave turn's measured ~0.16 %/m roll-in
CORRIDOR_PAD_M = 12.0  # fetch every EPT node within this of a station (HALF_M plus margin)


def fit_tilt(lateral: list[float], z: list[float]) -> tuple[float, float, int] | None:
    """(tilt %, residual sd m, points kept) of the trimmed least-squares line z = a + b*lateral; + = left side higher
    when ``lateral`` is + to the left. None with fewer than MIN_POINTS points."""
    keep = list(range(len(z)))
    a = b = 0.0
    for _ in range(TRIM_PASSES):
        if len(keep) < MIN_POINTS:
            return None
        n = len(keep)
        mx = sum(lateral[i] for i in keep) / n
        mz = sum(z[i] for i in keep) / n
        sxx = sum((lateral[i] - mx) ** 2 for i in keep)
        if sxx < 1e-9:
            return None
        b = sum((lateral[i] - mx) * (z[i] - mz) for i in keep) / sxx
        a = mz - b * mx
        res = [z[i] - (a + b * lateral[i]) for i in keep]
        sd = math.sqrt(sum(r * r for r in res) / n)
        lim = max(TRIM_MIN_M, 2.5 * sd)
        keep = [i for i in range(len(z)) if abs(z[i] - (a + b * lateral[i])) < lim]
    if len(keep) < MIN_POINTS:
        return None
    res = [z[i] - (a + b * lateral[i]) for i in keep]
    return 100.0 * b, math.sqrt(sum(r * r for r in res) / len(keep)), len(keep)


def is_road(fit) -> bool:
    return fit is not None and fit[1] <= MAX_SD_M and abs(fit[0]) <= MAX_READ_PCT


def _cyc(vals: list[float], k: int, reducer) -> list[float]:
    n = len(vals)
    return [reducer([vals[(i + d) % n] for d in range(-k, k + 1)]) for i in range(n)]


def compose(raw: list[float | None], step_m: float = STEP_M, lap_m: float | None = None,
            spans: list[tuple[float, float]] | None = None) -> list[float]:
    """Fill each run of missing fits straight between its good neighbours (round the closed lap), or flat where the run
    is longer than MAX_GAP_M; smooth by SMOOTH_M (median then mean); cap at CAP_PCT; limit every change to ROLL_RATE
    per metre. % per station, + = left higher."""
    n = len(raw)
    have = [i for i, v in enumerate(raw) if v is not None]
    if not have:
        return [0.0] * n
    filled = list(raw)
    for i in range(n):
        if raw[i] is not None:
            continue
        prev = min(have, key=lambda j: (i - j) % n)
        nxt = min(have, key=lambda j: (j - i) % n)
        dp, dn = (i - prev) % n, (nxt - i) % n
        if (dp + dn - 1) * step_m > MAX_GAP_M:
            filled[i] = 0.0
        else:
            filled[i] = (raw[prev] * dn + raw[nxt] * dp) / (dp + dn)
    k = max(1, int(round(SMOOTH_M / step_m / 2)))
    med = _cyc(filled, k, lambda w: sorted(w)[len(w) // 2])
    mean = _cyc(med, k, lambda w: sum(w) / len(w))
    capped = [max(-CAP_PCT, min(CAP_PCT, v)) for v in mean]
    st = [step_m * i for i in range(n)]
    if spans:
        capped = [v if any(a <= s <= b for a, b in spans) else 0.0 for v, s in zip(capped, st)]
    from scripts.elevation.crossfall import runoff
    return runoff(capped, st, lap_m or step_m * n, ROLL_RATE, closed=True)


def roll_worst(st: list[float], tilt: list[float], lap: float, window_m: float = 30.0) -> float:
    """The largest tilt change between two stations within window_m (reported, not gated)."""
    worst = 0.0
    n = len(st)
    for i in range(n):
        j = i + 1
        while True:
            jj = j % n
            d = (st[jj] - st[i]) % lap
            if d > window_m or jj == i:
                break
            worst = max(worst, abs(tilt[jj] - tilt[i]))
            j += 1
    return worst


def line_points(project: Path, cfg: dict) -> tuple[list[tuple[float, float]], str]:
    """(east, north) of the line the road is swept over, and which file it came from. finished_centerline.json is in
    the kn5 frame (x, y, -z of the local ENU frame, x mirrored with ``mirror_x``); centerline.local.json is ENU."""
    data = project / "data"
    fin = data / "finished_centerline.json"
    if fin.exists():
        sx = -1.0 if cfg.get("mirror_x") else 1.0
        return [(sx * p[0], -p[2]) for p in json.loads(fin.read_text(encoding="utf-8"))["points_xyz_m"]], fin.name
    lc = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    return [(p[0], p[2]) for p in lc["points_xyz_m"]], "centerline.local.json"


def stations(pts: list[tuple[float, float]], step_m: float = STEP_M):
    """[(station m, east, north, left-normal east, left-normal north)] every step_m along the line, and its length."""
    st_v = [0.0]
    for i in range(1, len(pts)):
        st_v.append(st_v[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    lap = st_v[-1]

    def at(s):
        import bisect
        s %= lap
        k = min(max(bisect.bisect_right(st_v, s), 1), len(st_v) - 1)
        t = (s - st_v[k - 1]) / max(1e-12, st_v[k] - st_v[k - 1])
        return (pts[k - 1][0] + t * (pts[k][0] - pts[k - 1][0]), pts[k - 1][1] + t * (pts[k][1] - pts[k - 1][1]))

    out, s = [], 0.0
    while s < lap - 1e-6:
        p = at(s)
        a, b = at(s - 3.0), at(s + 3.0)
        h = math.atan2(b[1] - a[1], b[0] - a[0])
        out.append((s, p[0], p[1], -math.sin(h), math.cos(h)))
        s += step_m
    return out, lap


def _fingerprint(ept: str, sts) -> str:
    h = hashlib.sha256(ept.encode())
    h.update(json.dumps([HALF_M, ALONG_M, GROUND, DECK, TRIM_PASSES, TRIM_MIN_M, MIN_POINTS]).encode())
    h.update(json.dumps([[round(v, 2) for v in s] for s in sts]).encode())
    return h.hexdigest()[:16]


def fetch_fits(ept_url: str, origin: dict, sts, log=print) -> list:
    """Fetch every EPT node within CORRIDOR_PAD_M of a station and fit each station twice: ground points alone and
    bridge-deck points alone ([ground fit, deck fit], each [tilt %, sd m, points] or None). Needs numpy, scipy,
    laspy, pyproj."""
    import numpy as np
    import laspy
    from pyproj import Transformer
    from scipy.spatial import cKDTree

    def get(url):
        with urllib.request.urlopen(url, timeout=180, context=https_context()) as r:
            return r.read()
    ept = json.loads(get(ept_url))
    base = ept_url.rsplit("/", 1)[0]
    if ept["srs"].get("horizontal") != "3857":
        raise SystemExit(f"lidar_crossfall: {ept_url} is not in EPSG:3857")
    m_lon, m_lat = _meters_per_degree(origin["lat"])
    to_merc = Transformer.from_crs(4326, 3857, always_xy=True)
    to_ll = Transformer.from_crs(3857, 4326, always_xy=True)
    E = np.array([s[1] for s in sts]); N = np.array([s[2] for s in sts])
    sx, sy = to_merc.transform(origin["lon"] + E / m_lon, origin["lat"] + N / m_lat)
    pad = CORRIDOR_PAD_M / math.cos(math.radians(origin["lat"]))     # web-mercator metres per ground metre
    b = ept["bounds"]
    hier_files = {}

    def hier(key):
        if key not in hier_files:
            hier_files[key] = json.loads(get(f"{base}/ept-hierarchy/{key}.json"))
        return hier_files[key]
    keys = []

    def walk(d, x, y, z, h):
        k = f"{d}-{x}-{y}-{z}"
        if k not in h:
            return
        if h[k] == -1:
            h = hier(k)
        sz = (b[3] - b[0]) / 2 ** d
        x0, y0 = b[0] + x * sz, b[1] + y * sz
        if not np.any((sx >= x0 - pad) & (sx <= x0 + sz + pad) & (sy >= y0 - pad) & (sy <= y0 + sz + pad)):
            return
        if h[k] > 0:
            keys.append(k)
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    walk(d + 1, 2 * x + dx, 2 * y + dy, 2 * z + dz, h)
    walk(0, 0, 0, 0, hier("0-0-0-0"))
    log(f"lidar_crossfall: {len(keys)} EPT nodes along the corridor")
    tree = cKDTree(np.c_[E, N])
    LE = np.array([s[3] for s in sts]); LN = np.array([s[4] for s in sts])
    per = {c: [[[], []] for _ in sts] for c in (GROUND, DECK)}      # class -> station -> (lateral, z)
    for q, k in enumerate(keys):
        las = laspy.read(io.BytesIO(get(f"{base}/ept-data/{k}.laz")))
        cls = np.asarray(las.classification)
        m = np.isin(cls, (GROUND, DECK))
        if not m.any():
            continue
        lon, lat = to_ll.transform(np.asarray(las.x)[m], np.asarray(las.y)[m])
        pe = (lon - origin["lon"]) * m_lon; pn = (lat - origin["lat"]) * m_lat
        pz = np.asarray(las.z)[m]; pc = cls[m]
        dist, i = tree.query(np.c_[pe, pn], distance_upper_bound=HALF_M + ALONG_M)
        ok = np.isfinite(dist)
        i, pe, pn, pz, pc = i[ok], pe[ok], pn[ok], pz[ok], pc[ok]
        de, dn = pe - E[i], pn - N[i]
        lat_ = de * LE[i] + dn * LN[i]
        along = de * LN[i] - dn * LE[i]
        ok = (np.abs(lat_) <= HALF_M) & (np.abs(along) <= ALONG_M)
        for ii, la, zz, cc in zip(i[ok].tolist(), lat_[ok].tolist(), pz[ok].tolist(), pc[ok].tolist()):
            per[cc][ii][0].append(la); per[cc][ii][1].append(zz)
        if q % 25 == 0:
            log(f"  node {q + 1}/{len(keys)}")
    fits = []
    for i in range(len(sts)):
        row = []
        for c in (GROUND, DECK):
            f = fit_tilt(*per[c][i])
            row.append(None if f is None else [round(f[0], 3), round(f[1], 4), f[2]])
        fits.append(row)
    return fits


def deck_spans(cfg: dict) -> list[tuple[float, float]]:
    """The declared bridges (``capture.bridges``: center_m, len_m in lap stations)."""
    return [(float(b["center_m"]) - float(b["len_m"]) / 2.0, float(b["center_m"]) + float(b["len_m"]) / 2.0)
            for b in ((cfg.get("capture") or {}).get("bridges") or [])]


def build(project_dir, *, ept_url: str = EPT_DEFAULT, refetch: bool = False, log=print) -> dict:
    project = Path(project_dir)
    data = project / "data"
    lc = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    cfgp = project / "track.config.json"
    cfg = json.loads(cfgp.read_text(encoding="utf-8")) if cfgp.exists() else {}
    pts, line = line_points(project, cfg)
    sts, lap = stations(pts)
    fp = _fingerprint(ept_url, sts)
    cache = data / "crossfall.lidar.json"
    fits = None
    if cache.exists() and not refetch:
        c = json.loads(cache.read_text(encoding="utf-8"))
        if c.get("fingerprint") == fp:
            fits = c["fits"]
            log(f"lidar_crossfall: {len(fits)} station fits from {cache.name}")
    if fits is None:
        fits = fetch_fits(ept_url, lc["origin"], sts, log)
        cache.write_text(json.dumps({"fingerprint": fp, "ept": ept_url,
                                     "fields": "per station [ground fit, deck fit], each [tilt %, sd m, points] or null",
                                     "fits": fits}), encoding="utf-8")
    decks = deck_spans(cfg)
    on_deck = [any(a <= s[0] <= b2 for a, b2 in decks) for s in sts]
    chosen = [f[1] if d else f[0] for f, d in zip(fits, on_deck)]
    raw = [c[0] if is_road(c) else None for c in chosen]
    spans = [tuple(map(float, s)) for s in ((cfg.get("road_profile") or {}).get("crossfall") or {}).get("spans_m") or []]
    tilt = compose(raw, lap_m=lap, spans=spans or None)
    st = [round(s[0], 1) for s in sts]
    dropped = sum(1 for v in raw if v is None)
    at = sorted(abs(v) for v in tilt)
    worst = roll_worst(st, tilt, lap)
    out = {
        "status": "measured",
        "_status_doc": "3DEP source lidar, measured at every station (ledger 0066); not estimated from the DEM",
        "method": "lidar", "tool": "tools/lidar_crossfall.py", "source": ept_url,
        "frame": f"stations along {line} (build_mesh's bank keys); + = left side higher", "line": line,
        "params": {"STEP_M": STEP_M, "HALF_M": HALF_M, "ALONG_M": ALONG_M, "GROUND": GROUND, "DECK": DECK,
                   "TRIM_PASSES": TRIM_PASSES, "TRIM_MIN_M": TRIM_MIN_M, "MIN_POINTS": MIN_POINTS,
                   "MAX_SD_M": MAX_SD_M, "MAX_READ_PCT": MAX_READ_PCT, "MAX_GAP_M": MAX_GAP_M,
                   "SMOOTH_M": SMOOTH_M, "CAP_PCT": CAP_PCT, "ROLL_RATE": ROLL_RATE},
        "deck_spans_m": decks, "spans_m": spans,
        "station_m": st,
        "bank_rad": [round(math.atan(v / 100.0), 5) for v in tilt],
        "tilt_pct": [round(v, 3) for v in tilt],
        "raw_pct": [None if v is None else round(v, 3) for v in raw],
        "deadband": 0.0, "cap": CAP_PCT / 100.0,
        "banked_pct": round(100.0 * sum(1 for v in tilt if abs(v) >= 2.0) / len(tilt), 1),
        "max_bank_pct": round(at[-1], 2),
        "summary": {"stations": len(st), "lap_m": round(lap, 1), "dropped_stations": dropped,
                    "abs_p50_pct": round(at[len(at) // 2], 2), "abs_p95_pct": round(at[19 * len(at) // 20], 2),
                    "max_abs_pct": round(at[-1], 2), "at_cap": sum(1 for v in tilt if abs(v) >= CAP_PCT - 1e-9),
                    "worst_change_pct_per_30m": round(worst, 2)},
    }
    (data / "crossfall.json").write_text(json.dumps(out), encoding="utf-8")
    s = out["summary"]
    log(f"lidar_crossfall: {s['stations']} stations ({dropped} not a road fit, filled); |tilt| p50 {s['abs_p50_pct']} % "
        f"p95 {s['abs_p95_pct']} % max {s['max_abs_pct']} % ({s['at_cap']} at the {CAP_PCT:g} % cap); worst roll change "
        f"{s['worst_change_pct_per_30m']} % per 30 m  [status: measured]")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--ept", default=EPT_DEFAULT)
    ap.add_argument("--refetch", action="store_true")
    a = ap.parse_args(argv)
    build(a.project, ept_url=a.ept, refetch=a.refetch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
