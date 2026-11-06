"""Size the EPT read beside Milford's lap: nodes whose XY box comes within BUF_M of the lane edge (half-width + BUF_M of
the centreline), their point counts, and their .laz byte sizes (HEAD). Saves ept.json + hierarchy into DL and writes
DL/plan.json. Fetches no point data.

    python -I ept_plan.py <centerline.local.json> <DL dir> [BUF_M]
"""
import json, math, sys, urllib.request
from pathlib import Path

import numpy as np
ROOT = Path(__file__).resolve().parents[5]          # airoso: TLS goes through scripts/tls.py (tests/net/test_https_everywhere.py)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.tls import https_context  # noqa: E402
from pyproj import Transformer

EPT = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/USGS_LPC_MI_31Co_Oakland_2016_LAS_2019/ept.json"
BASE = EPT.rsplit("/", 1)[0]
cl_path, DL = Path(sys.argv[1]), Path(sys.argv[2])
BUF = float(sys.argv[3]) if len(sys.argv) > 3 else 45.0
fetched = {"bytes": 0, "files": 0}


def get(url, save=None):
    for k in range(5):
        try:
            with urllib.request.urlopen(url, timeout=120, context=https_context()) as r:
                b = r.read()
            break
        except Exception as e:  # noqa
            import time; time.sleep(3 * (k + 1)); err = e
    else:
        raise SystemExit(f"refused {url}: {err}")
    fetched["bytes"] += len(b); fetched["files"] += 1
    if save:
        save.parent.mkdir(parents=True, exist_ok=True); save.write_bytes(b)
    return b


def head(url):
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=60, context=https_context()) as r:
        return int(r.headers["Content-Length"])


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


loc = json.loads(cl_path.read_text())
o = loc["origin"]
P = np.array(loc["points_xyz_m"]); W = np.array(loc["widths_m"])
# densify to <= 2 m
E, N, HW = [], [], []
for i in range(len(P) - 1):
    a, b = P[i], P[i + 1]; L = math.hypot(b[0] - a[0], b[2] - a[2]); n = max(1, int(L / 2.0))
    for t in np.arange(n) / n:
        E.append(a[0] + (b[0] - a[0]) * t); N.append(a[2] + (b[2] - a[2]) * t); HW.append((W[i] + (W[i + 1] - W[i]) * t) / 2)
E, N, HW = map(np.array, (E, N, HW))
m_lon, m_lat = mpd(o["lat"])
to_merc = Transformer.from_crs(4326, 3857, always_xy=True)
mx, my = to_merc.transform(o["lon"] + E / m_lon, o["lat"] + N / m_lat)
k = 1.0 / math.cos(math.radians(o["lat"]))          # mercator metres per ground metre
reach = (HW + BUF) * k

ept = json.loads(get(EPT, DL / "ept.json"))
b = ept["bounds"]; print("ept srs", ept["srs"].get("horizontal"), "points", ept["points"], "span", ept["span"])
hier = {}


def h_of(key):
    if key not in hier:
        hier[key] = json.loads(get(f"{BASE}/ept-hierarchy/{key}.json", DL / "ept-hierarchy" / f"{key}.json"))
    return hier[key]


keys = []


def walk(d, x, y, z, h):
    kk = f"{d}-{x}-{y}-{z}"
    if kk not in h:
        return
    if h[kk] == -1:
        h = h_of(kk)
    sz = (b[3] - b[0]) / 2 ** d
    x0, y0 = b[0] + x * sz, b[1] + y * sz
    dx = np.maximum(np.maximum(x0 - mx, 0), mx - (x0 + sz)); dy = np.maximum(np.maximum(y0 - my, 0), my - (y0 + sz))
    if not np.any(np.hypot(dx, dy) <= reach):
        return
    if h[kk] > 0:
        keys.append((kk, h[kk], sz / k))
    for ddx in (0, 1):
        for ddy in (0, 1):
            for ddz in (0, 1):
                walk(d + 1, 2 * x + ddx, 2 * y + ddy, 2 * z + ddz, h)


walk(0, 0, 0, 0, h_of("0-0-0-0"))
print("hierarchy files", len(hier), "bytes", fetched["bytes"])
sizes = {}
for kk, n, s in keys:
    sizes[kk] = head(f"{BASE}/ept-data/{kk}.laz")
tot = sum(sizes.values()); pts = sum(n for _, n, _ in keys)
by_depth = {}
for kk, n, s in keys:
    d = int(kk.split("-")[0]); e = by_depth.setdefault(d, [0, 0, 0, round(s, 1)]); e[0] += 1; e[1] += n; e[2] += sizes[kk]
for d in sorted(by_depth):
    print(f"depth {d:2d} (node {by_depth[d][3]} m): {by_depth[d][0]} nodes, {by_depth[d][1]:,} pts, {by_depth[d][2]/1e6:.1f} MB")
print(f"TOTAL {len(keys)} nodes, {pts:,} points in them, {tot:,} B ({tot/1e6:.1f} MB) laz; metadata fetched {fetched['bytes']:,} B")
(DL / "plan.json").write_text(json.dumps({"ept": EPT, "buffer_m_past_edge": BUF, "nodes": [[kk, n, sizes[kk]] for kk, n, _ in keys],
                                          "laz_bytes": tot, "node_points": pts, "metadata_bytes": fetched["bytes"]}, indent=0))
