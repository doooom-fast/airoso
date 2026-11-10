"""Isolated vertical objects (poles, posts, signs) the lidar holds: non-ground returns >= LO over ground, chained at
LINK_M; a cluster whose plan extent is <= MAX_EXT_M with no other non-ground return >= 0.3 m within CLEAR_M of it (not
the edge of a tree / shrub / F1). Reports each with its returns, top, plan extent, lap station and edge offset.
python -I poles.py pts.npz hag.npz centerline.local.json [out.json]"""
import json, sys
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

LO, LINK_M, MAX_EXT_M, CLEAR_M = 1.5, 1.0, 1.5, 3.0
pts = np.load(sys.argv[1]); hag = np.load(sys.argv[2])["hag"]; loc = json.load(open(sys.argv[3]))
e, n, cls = pts["e"].astype(float), pts["n"].astype(float), pts["cls"]
ok = ~np.isin(cls, (7, 18)) & np.isfinite(hag)
ngi = np.where(ok & (cls != 2) & (hag >= 0.3))[0]
Tng = cKDTree(np.c_[e[ngi], n[ngi]])
ci = np.where(ok & (cls != 2) & (hag >= LO))[0]
P = np.c_[e[ci], n[ci]]
pr = cKDTree(P).query_pairs(LINK_M, output_type="ndarray")
nc, lab = connected_components(coo_matrix((np.ones(len(pr)), (pr[:, 0], pr[:, 1])), shape=(len(ci), len(ci))), directed=False)
C = np.array(loc["points_xyz_m"])[:, [0, 2]]; Wd = np.array(loc["widths_m"])
st = np.r_[0, np.cumsum(np.hypot(*np.diff(C, axis=0).T))]
Tc = cKDTree(C)
out = []
order = np.argsort(lab); bounds = np.r_[0, np.cumsum(np.bincount(lab))]
for k in range(nc):
    mem = order[bounds[k]:bounds[k + 1]]
    Q = P[mem]
    ext = float(max(np.ptp(Q[:, 0]), np.ptp(Q[:, 1])))
    if ext > MAX_EXT_M:
        continue
    mu = Q.mean(0)
    near = Tng.query_ball_point(mu, r=CLEAR_M + ext / 2)
    others = set(ngi[near]) - set(ci[mem])
    # the object's own low returns (under it, within its extent + 0.5 m) are not "others"
    own_low = {i for i in others if np.hypot(e[i] - mu[0], n[i] - mu[1]) <= ext / 2 + 0.5}
    if len(others - own_low) > 0:
        continue
    d, j = Tc.query(mu)
    hh = hag[ci[mem]]
    out.append({"centre_en": [round(float(mu[0]), 2), round(float(mu[1]), 2)], "returns": int(len(mem)), "low_returns_under": len(own_low),
                "top_m": round(float(hh.max()), 2), "min_m": round(float(hh.min()), 2), "extent_m": round(ext, 2),
                "s_m": int(st[j]), "edge_off_m": round(float(d - Wd[j] / 2), 1)})
out.sort(key=lambda r: r["edge_off_m"])
print(f"isolated clusters >= {LO} m, extent <= {MAX_EXT_M} m, nothing else within {CLEAR_M} m: {len(out)}")
for r in out:
    print(r)
if len(sys.argv) > 4:
    json.dump(out, open(sys.argv[4], "w"), indent=0)
