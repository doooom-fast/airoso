"""Lake Murray, Jackson Dr north (piece D) s 1245-1295: lidar intensity across the road for the paint (USGS 3DEP
CA_SanDiegoCo_D24, 2024). Reads only. Cross-sections at the given stations along +u (the bearing given; + = left of
J4->J5 travel), u -12..+10.5 m, a +-1.25 m window along the road [invented], class 2 and all-class returns binned
at 0.10 m [invented]. Paint is retroreflective: a lane line reads as a narrow intensity peak over the asphalt's level."""
import json, math, sys, glob
from pathlib import Path
import numpy as np, laspy
from pyproj import Transformer
TILES = Path(sys.argv[1]); OUT = Path(sys.argv[2])
st = [(1245, -117.0508576, 32.8091744, 43.6), (1255, -117.0507803, 32.8091122, 43.4), (1265, -117.0507020, 32.8090510, 42.0),
      (1275, -117.0506225, 32.8089908, 41.8), (1285, -117.0505429, 32.8089307, 41.8), (1295, -117.0504633, 32.8088706, 41.8)]
# every 5 m between, linear
full = []
for (s0, lo0, la0, b0), (s1, lo1, la1, b1) in zip(st, st[1:]):
    for k in range(2):
        t = k / 2.0
        full.append((s0 + 10 * t, lo0 + (lo1 - lo0) * t, la0 + (la1 - la0) * t, b0 + (b1 - b0) * t))
full.append(st[-1])
tr = Transformer.from_crs("EPSG:4326", "EPSG:6340", always_xy=True)
pts = [(s, *tr.transform(lo, la), b) for s, lo, la, b in full]
E0 = min(p[1] for p in pts) - 30; E1 = max(p[1] for p in pts) + 30
N0 = min(p[2] for p in pts) - 30; N1 = max(p[2] for p in pts) + 30
xs = []; ys = []; zs = []; it = []; cl = []; rn = []
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
            xs.append(x[m]); ys.append(y[m]); zs.append(np.asarray(ch.z)[m]); it.append(np.asarray(ch.intensity)[m])
            cl.append(np.asarray(ch.classification)[m]); rn.append(np.asarray(ch.return_number)[m] == np.asarray(ch.number_of_returns)[m])
X = np.concatenate(xs); Y = np.concatenate(ys); Z = np.concatenate(zs); I = np.concatenate(it).astype(float); C = np.concatenate(cl); LAST = np.concatenate(rn)
res = {"_doc": __doc__, "points_in_box": int(len(X)), "stations": []}
bins = np.round(np.arange(-12.0, 10.5001, 0.10), 2)
for s, e, n, b in pts:
    ux, uy = math.sin(math.radians(b)), math.cos(math.radians(b))      # +u along bearing (E, N)
    vx, vy = -uy, ux                                                    # along-road
    dx, dy = X - e, Y - n
    u = dx * ux + dy * uy; v = dx * vx + dy * vy
    win = (np.abs(v) <= 1.25) & (u >= -12.0) & (u <= 10.5)
    row = {"s": s, "e": round(e, 2), "n": round(n, 2), "bearing": b}
    for name, m in (("ground", win & (C == 2)), ("last_returns", win & LAST)):
        uu = u[m]; ii = I[m]; zz = Z[m]
        k = np.clip(((uu + 12.0) / 0.10).astype(int), 0, len(bins) - 1)
        cnt = np.bincount(k, minlength=len(bins)); s_i = np.bincount(k, weights=ii, minlength=len(bins))
        mean = np.where(cnt > 0, s_i / np.maximum(cnt, 1), np.nan)
        row[name] = {"n": int(m.sum()), "bins_with_points": int((cnt > 0).sum()),
                     "intensity_by_0p1m": [None if not np.isfinite(v_) else round(float(v_), 1) for v_ in mean],
                     "count_by_0p1m": cnt.tolist()}
        if m.sum() > 20:
            base = float(np.nanmedian(ii)); row[name]["median_intensity"] = round(base, 1)
            # peaks: 0.3 m smoothed mean over 1.4 x median, local maxima
            sm = np.convolve(np.nan_to_num(mean, nan=base), np.ones(3) / 3, mode="same")
            pk = [round(float(bins[j]), 2) for j in range(1, len(sm) - 1)
                  if sm[j] > 1.4 * base and sm[j] >= sm[j - 1] and sm[j] >= sm[j + 1] and cnt[j] > 0]
            row[name]["peaks_u_over_1p4x_median"] = pk
            zr = zz[np.abs(uu) < 8]; row[name]["z_p50_road"] = round(float(np.median(zr)), 2) if zr.size else None
    res["stations"].append(row)
OUT.write_text(json.dumps(res))
for r in res["stations"]:
    g = r["ground"]; l = r["last_returns"]
    print(r["s"], "ground n", g["n"], "med", g.get("median_intensity"), "peaks", g.get("peaks_u_over_1p4x_median"), "| last n", l["n"], "peaks", l.get("peaks_u_over_1p4x_median"))
