"""The infield's TERRAIN patch for tools/ground_patch_blend.py (terrain.lidar_patches; ledger 0085): the oval's
inside, from the bank's edge in, seated on the 2018 lidar ground (infield_ground.py's 1 m DEM, nothing fetched).

    python make_ground_patch.py <project with the intake's data/centerline.local.json> <infield_dem.npz> <out json>

The polygon: the lane's left (inside) edge as the intake leaves it (centre + left normal x width / 2, the bank's
edge), INSET_M further in, simplified (Douglas-Peucker, SIMPLIFY_M) so the patch tool's per-vertex inside test stays
cheap; written into <out>'s "polygon" and printed for track.config.json terrain.lidar_patches (the tool refuses a
config polygon that is not the measured one). The lattice: the DEM's cells over the polygon's box + 2 m, row-major (z
then x), heights in the build's y (lidar z - 1634.84), the patch file's own format (tools/lidar_ground_patch.py).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

INSET_M = 0.5          # [invented] clear of the deck's own edge; the prep pins the ground under the deck anyway
SIMPLIFY_M = 0.25      # [invented] the polygon within 0.25 m of the edge line


def dp(P, tol):
    """Douglas-Peucker on an open polyline (indices kept)."""
    keep = np.zeros(len(P), bool); keep[0] = keep[-1] = True
    stack = [(0, len(P) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        A, B = P[a], P[b]; AB = B - A; L = np.hypot(*AB) or 1e-9
        Q = P[a + 1:b] - A
        d = np.abs(AB[0] * Q[:, 1] - AB[1] * Q[:, 0]) / L
        k = int(np.argmax(d))
        if d[k] > tol:
            m = a + 1 + k; keep[m] = True
            stack += [(a, m), (m, b)]
    return np.flatnonzero(keep)


def main(proj, dem_npz, out):
    c = json.loads((Path(proj) / "data/centerline.local.json").read_text(encoding="utf-8"))
    P = np.array(c["points_xyz_m"])[:, [0, 2]]; W = np.array(c["widths_m"])
    if np.hypot(*(P[0] - P[-1])) < 1e-6:
        P, W = P[:-1], W[:-1]
    T = np.roll(P, -1, 0) - np.roll(P, 1, 0); T /= np.linalg.norm(T, axis=1)[:, None]
    L = np.c_[-T[:, 1], T[:, 0]]
    E = P + L * (W / 2 + INSET_M)[:, None]
    far = int(np.argmax(np.hypot(*(E - E[0]).T)))          # a closed loop: two open halves, split at the far point
    h1 = dp(E[:far + 1], SIMPLIFY_M)
    h2 = far + dp(np.vstack([E[far:], E[:1]]), SIMPLIFY_M)
    idx = np.r_[h1, h2[1:-1]]
    loop = np.vstack([E, E[:1]])
    poly = E[idx]
    d = np.load(dem_npz)
    dem, e0, n0, cell = d["dem"], float(d["e0"]), float(d["n0"]), float(d["cell_m"])
    x0b, x1b = poly[:, 0].min() - 2.0, poly[:, 0].max() + 2.0
    z0b, z1b = poly[:, 1].min() - 2.0, poly[:, 1].max() + 2.0
    i0 = int(np.floor((x0b - e0) / cell - 0.5)); i1 = int(np.ceil((x1b - e0) / cell - 0.5))
    j0 = int(np.floor((z0b - n0) / cell - 0.5)); j1 = int(np.ceil((z1b - n0) / cell - 0.5))
    ny, nx = dem.shape
    if i0 < 0 or j0 < 0 or i1 >= nx or j1 >= ny:
        raise SystemExit(f"[ground-patch-make] the DEM ({nx} x {ny}) does not cover the polygon's box")
    sub = dem[j0:j1 + 1, i0:i1 + 1]
    lat = {"x0": round(e0 + (i0 + 0.5) * cell, 3), "z0": round(n0 + (j0 + 0.5) * cell, 3), "cell_m": cell,
           "nx": int(sub.shape[1]), "nz": int(sub.shape[0]),
           "y": [round(float(v), 3) for v in sub.ravel()], "filled": "infield_ground.py: holes linear inside the hull, then nearest",
           "polygon": [[round(float(x), 3), round(float(z), 3)] for x, z in poly]}
    res = {"_doc": "ledger 0085: the oval's inside on the 2018 lidar ground (tracks/pikes-peak/source/lidar/infield/"
                   "make_ground_patch.py from infield_ground.py's 1 m DEM; CO_Eastern_ElPaso_2018 class 2)",
           "patches": {"infield": lat}}
    Path(out).write_text(json.dumps(res, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"[ground-patch-make] polygon {len(poly)} vertices (of {len(loop) - 1}), box {x1b - x0b:.0f} x {z1b - z0b:.0f} m, "
          f"lattice {lat['nx']} x {lat['nz']}; heights {min(lat['y']):.2f}..{max(lat['y']):.2f} m -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
