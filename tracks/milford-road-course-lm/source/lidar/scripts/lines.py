"""Linear structures anywhere in the buffer: non-ground returns BAND_LO..BAND_HI over ground with no canopy (a return
over CANOPY_M) within CANOPY_R_M in plan; chained at LINK_M; clusters reported with their length (PCA extent),
width (2nd axis p5-p95), height percentiles, returns per metre, and their nearest lap station / edge offset.
python -I lines.py pts.npz hag.npz centerline.local.json lo hi [out.json]"""
import json, math, sys
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

pts = np.load(sys.argv[1]); hag = np.load(sys.argv[2])["hag"]; loc = json.load(open(sys.argv[3]))
LO, HI = float(sys.argv[4]), float(sys.argv[5])
CANOPY_M, CANOPY_R_M, LINK_M = max(HI + 1.0, 2.0), 1.5, 2.5
e, n, cls = pts["e"].astype(float), pts["n"].astype(float), pts["cls"]
ok = ~np.isin(cls, (7, 18)) & np.isfinite(hag)
cand = ok & (cls != 2) & (hag >= LO) & (hag < HI)
tall = ok & (cls != 2) & (hag >= CANOPY_M)
Tt = cKDTree(np.c_[e[tall], n[tall]])
ci = np.where(cand)[0]
near_tall = np.array([len(x) > 0 for x in Tt.query_ball_point(np.c_[e[ci], n[ci]], r=CANOPY_R_M)])
ci = ci[~near_tall]
P = np.c_[e[ci], n[ci]]
pairs = cKDTree(P).query_pairs(LINK_M, output_type="ndarray")
g = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(ci), len(ci)))
nc, lab = connected_components(g, directed=False)
C = np.array(loc["points_xyz_m"])[:, [0, 2]]; Wd = np.array(loc["widths_m"])
st = np.r_[0, np.cumsum(np.hypot(*np.diff(C, axis=0).T))]
Tc = cKDTree(C)
out = []
for k in range(nc):
    m = lab == k
    if m.sum() < 8:
        continue
    Q = P[m]; mu = Q.mean(0); U, S, Vt = np.linalg.svd(Q - mu, full_matrices=False)
    pr = (Q - mu) @ Vt.T
    length = float(np.ptp(pr[:, 0])); width = float(np.percentile(pr[:, 1], 95) - np.percentile(pr[:, 1], 5))
    if length < 8 or width > max(2.5, 0.25 * length):
        continue
    hh = hag[ci[m]]
    d, j = Tc.query(Q)
    off = d - Wd[j] / 2
    out.append({"n": int(m.sum()), "len_m": round(length, 1), "width_m": round(width, 2), "per_m": round(m.sum() / max(length, 1), 2),
                "h_p50": round(float(np.median(hh)), 2), "h_p90": round(float(np.percentile(hh, 90)), 2),
                "s_m": [int(st[j].min()), int(st[j].max())], "edge_off_m": [round(float(off.min()), 1), round(float(off.max()), 1)],
                "centre_en": [round(float(mu[0]), 1), round(float(mu[1]), 1)],
                "ends_en": [[round(float(v), 1) for v in (mu + Vt[0] * pr[:, 0].min())], [round(float(v), 1) for v in (mu + Vt[0] * pr[:, 0].max())]]})
out.sort(key=lambda r: -r["len_m"])
print(f"band {LO}-{HI} m: {len(ci)} candidate returns (no canopy within {CANOPY_R_M} m), {len(out)} linear clusters >= 8 m")
for r in out[:40]:
    print(r)
if len(sys.argv) > 6:
    json.dump(out, open(sys.argv[6], "w"), indent=0)
