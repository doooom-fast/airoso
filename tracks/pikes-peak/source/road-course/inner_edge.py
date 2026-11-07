"""Part 1: where the oval's inside pavement edge really is, off NAIP 2023 0.3 m (on disk), per survey station.

Along each station's left (inside) normal from the line's centre, the pavement mask (pave_mask.npy: grey / kerb pixels)
is read every 0.15 m out to 40 m. The INSIDE EDGE is the start of the first non-pavement run >= 1.5 m long. A station whose
profile runs into other pavement (pit lane, an infield road, the lot) with no such gap before 40 m reads None.
Reported against the built lane's left edge (the LM 0.1.0 deck: the live line's centre - half its width, as the intake
left it) and the wall face (lidar), so the racing surface's real width is wall face -> inside edge.
"""
import json, sys
import numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent) + "/")
from geo import en_to_px

REPO = str(__import__("pathlib").Path(__file__).resolve().parents[4]) + "/"
m = np.load(str(__import__("pathlib").Path(__file__).resolve().parent) + "/" + "pave_mask.npy")
ws = sys.argv[1]
cl = json.load(open(ws + "/data/centerline.local.json"))      # the port's line as built (edge_on_wall applied)
P = np.array(cl["points_xyz_m"]); Wd = np.array(cl["widths_m"])
st = np.r_[0, np.cumsum(np.hypot(np.diff(P[:, 0]), np.diff(P[:, 2])))]
T = np.gradient(P[:, [0, 2]], axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
L = np.c_[-T[:, 1], T[:, 0]]
offs = np.arange(0, 40.0, 0.15)
rows = []
for k in range(len(P) - 1):
    x = P[k, 0] + offs * L[k, 0]; z = P[k, 2] + offs * L[k, 1]
    px, py = en_to_px(x, z)
    ix = np.clip(np.round(px).astype(int), 0, m.shape[1] - 1); iy = np.clip(np.round(py).astype(int), 0, m.shape[0] - 1)
    pav = m[iy, ix]
    edge = None; run = 0
    for j, v in enumerate(pav):
        if not v:
            run += 1
            if run * 0.15 >= 1.5:
                edge = offs[j - run + 1]; break
        else:
            run = 0
    rows.append({"s": round(float(st[k]), 1), "lane_left_m": round(float(Wd[k] / 2), 2),
                 "inside_edge_m": None if edge is None else round(float(edge), 2)})
e = np.array([r["inside_edge_m"] if r["inside_edge_m"] is not None else np.nan for r in rows])
ll = np.array([r["lane_left_m"] for r in rows]); s = np.array([r["s"] for r in rows])
ok = np.isfinite(e)
extra = e - ll
summ = {"stations": len(rows), "with_edge": int(ok.sum()),
        "inside_edge_from_centre_m": {"p10": round(float(np.nanpercentile(e, 10)), 2), "median": round(float(np.nanmedian(e)), 2), "p90": round(float(np.nanpercentile(e, 90)), 2)},
        "pavement_past_built_left_edge_m": {"p10": round(float(np.nanpercentile(extra, 10)), 2), "median": round(float(np.nanmedian(extra)), 2), "p90": round(float(np.nanpercentile(extra, 90)), 2)},
        "no_edge_runs": []}
# runs of None
run0 = None
for k in range(len(rows) + 1):
    bad = k < len(rows) and not ok[k]
    if bad and run0 is None:
        run0 = k
    if not bad and run0 is not None:
        summ["no_edge_runs"].append([float(s[run0]), float(s[k - 1])]); run0 = None
print(json.dumps(summ, indent=1))
json.dump({"summary": summ, "rows": rows}, open(str(__import__("pathlib").Path(__file__).resolve().parent) + "/" + "inside_edge.naip.json", "w"), indent=0)
