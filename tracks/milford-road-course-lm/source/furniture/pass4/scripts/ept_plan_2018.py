"""Ledger 0082 pass 4 (Kevin 2026-11-09, "The three small ones": download a): size the 3DEP Livingston 2018 EPT read over
Milford's rails and tyre walls that lie inside that project's bounds (it ends at lon -83.66588: G1, G2, G3, T2, T3), every
node at every depth whose box comes within BUF_M of a rail line. Saves ept.json + the hierarchy into DL, HEADs each .laz,
writes DL/plan.json. Fetches no point data.

    python -I ept_plan_2018.py <track.config.json> <DL dir> [BUF_M]
"""
import json, math, sys, ssl, time, urllib.request
from pathlib import Path

import numpy as np

EPT = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/USGS_LPC_MI_31Co_Livingston_2018_LAS_2019/ept.json"
BASE = EPT.rsplit("/", 1)[0]
cfg_path, DL = Path(sys.argv[1]), Path(sys.argv[2])
BUF = float(sys.argv[3]) if len(sys.argv) > 3 else 25.0
KEYS = ("g1_", "g2_", "g3_", "t2_", "t3_")
fetched = {"bytes": 0, "files": 0}
CTX = ssl.create_default_context()


def get(url, save=None):
    err = None
    for k in range(5):
        try:
            with urllib.request.urlopen(url, timeout=120, context=CTX) as r:
                b = r.read()
            break
        except Exception as e:  # noqa
            err = e; time.sleep(3 * (k + 1))
    else:
        raise SystemExit(f"refused {url}: {err}")
    fetched["bytes"] += len(b); fetched["files"] += 1
    if save:
        save.parent.mkdir(parents=True, exist_ok=True); save.write_bytes(b)
    return b


def head(url):
    with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60, context=CTX) as r:
        return int(r.headers["Content-Length"])


def merc(lon, lat):
    R = 6378137.0
    return R * np.radians(lon), R * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


cfg = json.loads(cfg_path.read_text())
pts = []
for r in cfg["scenery"]["bespoke"]["rails"]:
    if r["key"].startswith(KEYS):
        L = np.array(r["polyline_lonlat"])
        for a, b in zip(L, L[1:]):
            n = max(1, int(np.hypot(*(b - a) * [82107, 111084]) / 2))
            pts += [a + (b - a) * t for t in np.arange(n) / n]
        pts.append(L[-1])
P = np.array(pts)
mx, my = merc(P[:, 0], P[:, 1])
k = 1.0 / math.cos(math.radians(42.57))
reach = BUF * k
ept = json.loads(get(EPT, DL / "ept.json"))
b = ept["bounds"]; print("ept points", ept["points"], "span", ept["span"])
hier, keys = {}, []


def h_of(key):
    if key not in hier:
        hier[key] = json.loads(get(f"{BASE}/ept-hierarchy/{key}.json", DL / "ept-hierarchy" / f"{key}.json"))
    return hier[key]


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
print("hierarchy files", len(hier), "metadata bytes", fetched["bytes"])
sizes = {kk: head(f"{BASE}/ept-data/{kk}.laz") for kk, n, s in keys}
tot = sum(sizes.values()); npts = sum(n for _, n, _ in keys)
by = {}
for kk, n, s in keys:
    d = int(kk.split("-")[0]); e = by.setdefault(d, [0, 0, 0, round(s, 1)]); e[0] += 1; e[1] += n; e[2] += sizes[kk]
for d in sorted(by):
    print(f"depth {d:2d} (node {by[d][3]} m): {by[d][0]} nodes, {by[d][1]:,} pts, {by[d][2]/1e6:.1f} MB")
print(f"TOTAL {len(keys)} nodes, {npts:,} points, {tot:,} B ({tot/1e6:.1f} MB) laz; metadata {fetched['bytes']:,} B")
(DL / "plan.json").write_text(json.dumps({"ept": EPT, "buffer_m": BUF, "lines": list(KEYS), "nodes": [[kk, n, sizes[kk]] for kk, n, _ in keys],
                                          "laz_bytes": tot, "node_points": npts, "metadata_bytes": fetched["bytes"]}, indent=0))
