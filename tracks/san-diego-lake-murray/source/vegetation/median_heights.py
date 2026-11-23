"""Lake Murray: the real plant height at each median_planting spot (scatter_positions.json), off the lm-shrub job's
0.5 m canopy grids (USGS 3DEP CA_SanDiegoCo_D24, flown Nov 2024). Reads only; downloads nothing. Run with -I.

    python -I median_heights.py <scatter_positions.json> <centerline.local.json> <lm-shrub out dir> <out json>

At each spot: the canopy height over the lidar ground, as the 0089 rule reads a top (the second-highest return per
0.5 m cell, the highest of those in the 3 x 3 cells around the spot, 1.5 m square), and the nearest lm-shrub plant top
(not solid, not near a footprint) within 2 m [invented]. A spot under 0.3 m [invented, lm-shrub's H_MIN] is bare.
"""
import json, math, sys
from pathlib import Path
import numpy as np
from pyproj import Transformer
from scipy.spatial import cKDTree

sp, cl, outdir, outp = (Path(a) for a in sys.argv[1:5])
pos = json.loads(sp.read_text())["median_planting"]
org = json.loads(cl.read_text())["origin"]
phi = math.radians(org["lat"])
m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
x = np.array([p["x"] for p in pos]); z = np.array([p["z"] for p in pos])
tr = Transformer.from_crs("EPSG:4326", "EPSG:6340", always_xy=True)
E, N = tr.transform(org["lon"] + x / m_lon, org["lat"] + z / m_lat)
E, N = np.asarray(E), np.asarray(N)

CELL = 0.5
h3 = np.full(len(E), np.nan); n3 = np.zeros(len(E), int)
cache = {}
for i, (e, n) in enumerate(zip(E, N)):
    vals, cnt = [], 0
    for de in (-CELL, 0, CELL):
        for dn in (-CELL, 0, CELL):
            ee, nn = e + de, n + dn
            te, tn = int(ee // 1000) * 1000, int(nn // 1000) * 1000
            key = (te, tn)
            if key not in cache:
                f = outdir / "work" / f"chm_{te}_{tn}.npz"
                if f.exists():
                    with np.load(f) as zf:          # decompress each grid once (an NpzFile re-reads per access)
                        cache[key] = {"top2": zf["top2"], "n_hi": zf["n_hi"]}
                else:
                    cache[key] = None
            g = cache[key]
            if g is None:
                continue
            r, c = int((nn - tn) / CELL), int((ee - te) / CELL)
            vals.append(float(g["top2"][r, c])); cnt += int(g["n_hi"][r, c])
    if vals:
        h3[i] = max(vals); n3[i] = cnt

T = np.load(outdir / "lm_shrub.tops.npz")
keep = T["plant"] & ~T["solid"]
tree = cKDTree(np.c_[T["E"][keep], T["N"][keep]])
d, j = tree.query(np.c_[E, N], distance_upper_bound=2.0)
th = np.where(np.isfinite(d), T["h"][keep][np.minimum(j, keep.sum() - 1)], np.nan)
tmed = np.where(np.isfinite(d), T["median"][keep][np.minimum(j, keep.sum() - 1)], False)
tcr = np.where(np.isfinite(d), T["crown_d"][keep][np.minimum(j, keep.sum() - 1)], np.nan)
tdist = np.where(np.isfinite(d), d, np.nan)

def pct(a):
    a = a[np.isfinite(a)]
    return {f"p{p}": round(float(np.percentile(a, p)), 2) for p in (5, 10, 25, 50, 75, 90, 95)} if len(a) else {}

draft = np.array([p.get("height", np.nan) for p in pos], float)
bare = np.isfinite(h3) & (h3 < 0.3)
res = {
    "_doc": __doc__.strip(),
    "spots": len(pos), "spots_with_lidar": int(np.isfinite(h3).sum()),
    "bare_under_0.3m": int(bare.sum()),
    "canopy_3x3_h": pct(h3), "canopy_3x3_h_planted_only": pct(np.where(bare, np.nan, h3)),
    "canopy_bins_m": {f"{lo}-{hi}": int(((h3 >= lo) & (h3 < hi)).sum()) for lo, hi in
                      ((-99, 0.3), (0.3, 1), (1, 2), (2, 3), (3, 4), (4, 6), (6, 10), (10, 99))},
    "nearest_top_within_2m": {"n": int(np.isfinite(th).sum()), "flagged_median": int(tmed.sum()), "h": pct(th)},
    "draft_height_field": pct(draft),
    "nearest_top_crown_m": pct(tcr),
    "per_spot": [{"x": round(float(a), 2), "z": round(float(b), 2), "h3": None if not np.isfinite(c) else round(float(c), 2),
                  "top_h": None if not np.isfinite(t) else round(float(t), 2),
                  "top_crown_m": None if not np.isfinite(w) else round(float(w), 2),
                  "top_dist_m": None if not np.isfinite(q) else round(float(q), 2)}
                 for a, b, c, t, w, q in zip(x, z, h3, th, tcr, tdist)],
}
outp.write_text(json.dumps(res, indent=1))
print(json.dumps({k: v for k, v in res.items() if k not in ("per_spot", "_doc")}, indent=1))
