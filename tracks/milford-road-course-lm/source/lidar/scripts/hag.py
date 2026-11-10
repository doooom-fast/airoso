"""Height above ground for every kept return: a plane through the GROUND_K nearest class-2 returns within GROUND_R_M
(least squares, z = a + b e + c n), evaluated at the return. Writes hag.npz beside pts.npz. Run with -I."""
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

GROUND_K, GROUND_R_M = 12, 4.0
src = Path(sys.argv[1]); out = Path(sys.argv[2])
d = np.load(src)
e, n, z, cls = d["e"].astype(np.float64), d["n"].astype(np.float64), d["z"].astype(np.float64), d["cls"]
keep = ~np.isin(cls, (7, 18))
g = keep & (cls == 2)
G = np.c_[e[g], n[g]]; Gz = z[g]
t = cKDTree(G)
hag = np.full(len(e), np.nan)
idx = np.where(keep)[0]
for s in range(0, len(idx), 200000):
    ii = idx[s:s + 200000]
    dist, j = t.query(np.c_[e[ii], n[ii]], k=GROUND_K, distance_upper_bound=GROUND_R_M)
    ok = np.isfinite(dist)
    cnt = ok.sum(1)
    jj = np.where(ok, j, 0)
    ge, gn, gz = G[jj, 0] - e[ii, None], G[jj, 1] - n[ii, None], Gz[jj]
    w = ok.astype(float)
    # weighted normal equations for z = a + b*de + c*dn (a = ground at the return)
    S = np.stack([w, w * ge, w * gn], -1)                       # (m, k, 3)
    A = np.einsum("mki,mkj->mij", S, np.stack([np.ones_like(ge), ge, gn], -1))
    B = np.einsum("mki,mk->mi", S, gz)
    A += np.eye(3)[None] * 1e-6
    good = cnt >= 6
    sol = np.full((len(ii), 3), np.nan)
    sol[good] = np.linalg.solve(A[good], B[good][..., None])[..., 0]
    # fall back to the median where too few
    few = (cnt >= 2) & ~good
    if few.any():
        gzm = np.where(ok, gz, np.nan)
        sol[few, 0] = np.nanmedian(gzm[few], 1)
    hag[ii] = z[ii] - sol[:, 0]
np.savez_compressed(out, hag=hag.astype(np.float32))
ng = keep & (cls != 2)
print("non-ground", ng.sum(), "with hag", np.isfinite(hag[ng]).sum())
for lo, hi in ((-1, 0.1), (0.1, 0.3), (0.3, 1.5), (1.5, 3), (3, 6), (6, 40)):
    print(f"hag {lo}..{hi}: {int(((hag >= lo) & (hag < hi) & ng).sum()):,}")
print("ground |hag| p95", float(np.nanpercentile(np.abs(hag[g]), 95)))
