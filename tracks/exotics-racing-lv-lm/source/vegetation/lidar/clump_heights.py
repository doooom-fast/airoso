"""Each NAIP clump's height off the lidar (ledger 0089): the clump's returns (noise classes out) within its crown radius
(at least 0.8 m), over a plane fitted to the class-2 ground returns 1-4 m beyond it. Height = the SECOND-highest return
over that plane (one stray return does not make a shrub). Usage: clump_heights.py <npz> <lat0> <scrub.naip.json> <out.json>"""
import json, sys
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0, sys.argv[0].rsplit("/", 1)[0])
import hag
P = hag.load(sys.argv[1], float(sys.argv[2]))
k = (P["C"] != 7) & (P["C"] != 18)
X, Y, Z, C = P["X"][k], P["Y"][k], P["Z"][k], P["C"][k]
T = cKDTree(np.c_[X, Y])
rows = []
for p in json.load(open(sys.argv[3]))["points"]:
    x, y = P["to_xy"](p[0], p[1])
    r = max(0.8, p[4] / 2)
    i_in = np.array(T.query_ball_point([x, y], r))
    ring = np.setdiff1d(T.query_ball_point([x, y], r + 4), T.query_ball_point([x, y], r + 1))
    ring = ring[C[ring] == 2]
    A = np.c_[X[ring] - x, Y[ring] - y, np.ones(len(ring))]
    cf, *_ = np.linalg.lstsq(A, Z[ring], rcond=None)
    res = np.sort(Z[i_in] - (np.c_[X[i_in] - x, Y[i_in] - y, np.ones(len(i_in))] @ cf))[::-1]
    sd = float(np.std(Z[ring] - A @ cf))
    rows.append({"key": p[5], "lon": p[0], "lat": p[1], "crown_m": p[4], "returns": int(len(i_in)),
                 "top_m": round(float(res[1]), 2), "top1_m": round(float(res[0]), 2), "ring_sd_m": round(sd, 3), "ranked_h_m": p[3]})
json.dump(rows, open(sys.argv[4], "w"), indent=0)
t = np.array([r["top_m"] for r in rows])
print(f"{len(rows)} clumps; second-highest return over the ground plane p10/50/90 {np.percentile(t, [10, 50, 90]).round(2)}; "
      f"ring sd p50 {np.median([r['ring_sd_m'] for r in rows]):.3f}; >=0.3 m: {(t >= 0.3).sum()}, >=0.5 m: {(t >= 0.5).sum()}")
