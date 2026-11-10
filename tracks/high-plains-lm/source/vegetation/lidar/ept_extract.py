"""Read EPT LAZ nodes, keep the points inside a lon/lat box, write x, y (EPSG:3857 m), z, class, return, nreturns, gps time as
npz (ledger 0089). Usage: python -I ept_extract.py <dir-with-ept.json-and-ept-data> <out.npz> w s e n"""
import glob, json, math, sys
import numpy as np, laspy
d, out = sys.argv[1], sys.argv[2]
w, s, e, n = map(float, sys.argv[3:7])
R = 6378137.0
x0, x1 = math.radians(w) * R, math.radians(e) * R
y0, y1 = (R * math.log(math.tan(math.pi / 4 + math.radians(v) / 2)) for v in (s, n))
cols = {k: [] for k in ("x", "y", "z", "c", "r", "nr", "t")}
tot = 0
for f in sorted(glob.glob(d + "/ept-data/*.laz")):
    las = laspy.read(f)
    tot += len(las.points)
    x, y = np.asarray(las.x), np.asarray(las.y)
    m = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
    cols["x"].append(x[m]); cols["y"].append(y[m]); cols["z"].append(np.asarray(las.z)[m])
    cols["c"].append(np.asarray(las.classification)[m].astype(np.uint8))
    cols["r"].append(np.asarray(las.return_number)[m].astype(np.uint8))
    cols["nr"].append(np.asarray(las.number_of_returns)[m].astype(np.uint8))
    cols["t"].append(np.asarray(las.gps_time)[m])
arr = {k: np.concatenate(v) for k, v in cols.items()}
np.savez_compressed(out, **arr)
cl, cn = np.unique(arr["c"], return_counts=True)
print(f"read {tot:,} points, kept {len(arr['x']):,} in the box; classes {dict(zip(cl.tolist(), cn.tolist()))}")
