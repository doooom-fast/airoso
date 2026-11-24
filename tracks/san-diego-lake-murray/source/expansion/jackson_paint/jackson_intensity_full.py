"""Lake Murray, Jackson Dr north (piece D of data/expansion.north.json): lidar intensity across the road at each
2.5 m station, for the paint (USGS 3DEP CA_SanDiegoCo_D24, 2024). Reads only. Paint is retroreflective: a painted
line reads as a narrow intensity peak over the asphalt; a hatched band as a stretch of raised mean intensity.

    python -I jackson_intensity_full.py <tiles dir> <stations.json> <out.json>

stations.json: [{s, lon, lat, bearing (+u, = left of J4->J5 travel), u_min, u_max, data{...}}] made from D's own rows.
Per station, LAST returns (class 2 is thin under canopy) in a window along the road:
  * lines: 0.10 m bins of mean intensity in a +-1.25 m window [invented]; a peak is a local max of the 0.3 m smoothed
    profile over 1.4 x the station's median [invented];
  * dashed vs solid: the share of 1 m sub-windows over +-6 m [invented] along the road where a peak sits within 0.25 m
    of that u (a solid line ~1, a 3 m dash in a 12 m cycle ~0.25-0.5);
  * a hatched band: in a +-3 m window [invented], the contiguous u where the 0.5 m smoothed mean exceeds 1.15 x the
    station's asphalt median [invented] for at least 1.5 m [invented], away from the road's edges by 1.5 m.
"""
import json, math, sys, glob
from pathlib import Path
import numpy as np, laspy
from pyproj import Transformer
TILES = Path(sys.argv[1]); ST = json.loads(Path(sys.argv[2]).read_text()); OUT = Path(sys.argv[3])
tr = Transformer.from_crs("EPSG:4326", "EPSG:6340", always_xy=True)
for s in ST:
    s["E"], s["N"] = tr.transform(s["lon"], s["lat"])
res = {"_doc": __doc__, "stations": []}
def load(E0, E1, N0, N1):
    xs = []; ys = []; it = []; last = []
    for f in sorted(glob.glob(str(TILES / "*.laz"))):
        with laspy.open(f) as fh:
            h = fh.header
            if h.maxs[0] < E0 or h.mins[0] > E1 or h.maxs[1] < N0 or h.mins[1] > N1:
                continue
            for ch in fh.chunk_iterator(2_000_000):
                x = np.asarray(ch.x); y = np.asarray(ch.y)
                m = (x >= E0) & (x <= E1) & (y >= N0) & (y <= N1)
                if not m.any():
                    continue
                xs.append(x[m]); ys.append(y[m]); it.append(np.asarray(ch.intensity)[m].astype(float))
                last.append((np.asarray(ch.return_number) == np.asarray(ch.number_of_returns))[m])
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(it), np.concatenate(last)
groups = [[s for s in ST if s["s"] <= 600], [s for s in ST if s["s"] > 600]]
for grp in groups:
    if not grp:
        continue
    E0 = min(s["E"] for s in grp) - 25; E1 = max(s["E"] for s in grp) + 25
    N0 = min(s["N"] for s in grp) - 25; N1 = max(s["N"] for s in grp) + 25
    X, Y, I, LAST = load(E0, E1, N0, N1)
    X, Y, I = X[LAST], Y[LAST], I[LAST]
    for s in grp:
        b = math.radians(s["bearing"]); ux, uy = math.sin(b), math.cos(b); vx, vy = -uy, ux
        dx, dy = X - s["E"], Y - s["N"]; u = dx * ux + dy * uy; v = dx * vx + dy * vy
        lo, hi = s["u_min"], s["u_max"]
        nb = int(round((hi - lo) / 0.10)) + 1; bins = lo + 0.10 * np.arange(nb)
        def prof(win):
            m = win & (u >= lo) & (u <= hi)
            k = np.clip(((u[m] - lo) / 0.10).astype(int), 0, nb - 1)
            c = np.bincount(k, minlength=nb); t = np.bincount(k, weights=I[m], minlength=nb)
            return c, np.where(c > 0, t / np.maximum(c, 1), np.nan), I[m]
        c1, p1, i1 = prof(np.abs(v) <= 1.25)
        row = {"s": s["s"], "bearing": s["bearing"], "u_range": [lo, hi], "n_points": int(c1.sum()), "data": s["data"]}
        if c1.sum() < 30:
            row["verdict"] = "too few returns"; res["stations"].append(row); continue
        med = float(np.median(i1)); row["median_intensity"] = round(med, 1)
        sm = np.convolve(np.nan_to_num(p1, nan=med), np.ones(3) / 3, mode="same")
        peaks = [j for j in range(1, nb - 1) if sm[j] > 1.4 * med and sm[j] >= sm[j - 1] and sm[j] >= sm[j + 1] and c1[j] > 0]
        # merge peaks closer than 0.3 m
        merged = []
        for j in peaks:
            if merged and bins[j] - bins[merged[-1]] < 0.3:
                if sm[j] > sm[merged[-1]]: merged[-1] = j
            else:
                merged.append(j)
        lines = []
        for j in merged:
            uj = float(bins[j]); hits = 0; wins = 0
            for v0 in np.arange(-6.0, 6.0, 1.0):
                w = (v >= v0) & (v < v0 + 1.0) & (np.abs(u - uj) <= 0.6)
                if w.sum() < 4: continue
                wins += 1
                near = (np.abs(u - uj) <= 0.25) & w
                if near.any() and np.mean(I[near]) > 1.3 * med: hits += 1
            lines.append({"u": round(uj, 2), "peak_over_median": round(float(sm[j] / med), 2),
                          "along_share": round(hits / wins, 2) if wins else None})
        row["lines"] = lines
        c3, p3, i3 = prof(np.abs(v) <= 3.0)
        sm3 = np.convolve(np.nan_to_num(p3, nan=med), np.ones(5) / 5, mode="same")
        hot = sm3 > 1.15 * med
        bands = []; j = 0
        while j < nb:
            if hot[j]:
                k = j
                while k + 1 < nb and hot[k + 1]: k += 1
                a, z = float(bins[j]), float(bins[k])
                if z - a >= 1.5 and a > lo + 1.5 and z < hi - 1.5:
                    bands.append({"u_from": round(a, 2), "u_to": round(z, 2), "mean_over_median": round(float(np.mean(sm3[j:k + 1]) / med), 2)})
                j = k + 1
            else:
                j += 1
        row["bands"] = bands
        row["profile_0p1m"] = [None if not np.isfinite(x) else round(float(x), 0) for x in p1]
        res["stations"].append(row)
OUT.write_text(json.dumps(res))
for r in res["stations"]:
    if "lines" not in r: print(r["s"], r.get("verdict")); continue
    print(r["s"], "lines", [(l["u"], l["along_share"]) for l in r["lines"] if r["u_range"][0] + 1.5 < l["u"] < r["u_range"][1] - 1.5], "bands", [(b["u_from"], b["u_to"]) for b in r["bands"]])
