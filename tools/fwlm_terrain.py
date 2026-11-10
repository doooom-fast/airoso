"""Tiered terrain for the SD freeway port (ledger 0080 2b round 1): the whole 3DEP box, fine only near the roads.

The port's ground is Lake Murray v4's assembler's (tracks/san-diego-lake-murray/scripts-v021/blender/build_loop_blend.py,
UNCHANGED): the 3DEP grid pre-divided x2 by the intake (lm_intake.grid_upsample), divided x2 again by the assembler,
conformed to every road, band-clamped, carved, and triangulated as one regular grid (ribbon.grass_terrain). Over the
port's whole network box (272 x 333 native 55 m samples) that grid is 1,329 x 1,085 = 1.44 M vertices at 13.75 m, and
the assembler's pure-Python band clamp (a ring search per vertex) never finished. Two port-only pieces, each opt-in:

  band_clamp_np    the assembler's band_clamp, vectorised: per 130 m node bucket the SAME candidate set (the 3 x 3
                   block, then ring by ring until one holds a road point, < 40 rings), the same squared distances in
                   float64, the same first-minimum, the same clamp. Byte-identical to the pure-Python pass (tests and
                   the ledger's A/B on Lake Murray's own grid); it changes no number, only the time.
  tiered_terrain   ribbon.grass_terrain's mesh with every native cell (``step`` fine cells a side) farther than
                   ``fine_m`` from a pavement edge collapsed to its four native corners. Fine cells are triangulated
                   EXACTLY as grass_terrain does (the same vertices, the same diagonals): near the roads the ground is
                   the ground every gate was green on. A coarse cell beside a fine one is a fan from its centre node
                   over its boundary, the fine side's nodes included, so no T-junction opens a crack. The skirt is
                   grass_terrain's, over the border nodes the mesh uses. Far vertices are the clamped grid's own nodes
                   at the native samples (the bilinear x4 is exact there): the 3DEP at native spacing.

Used by tools/fwlm_tiered_assembler_blend.py (ship.json draft step ``build_loop_blend_tiered``). Lake Murray never
runs either. numpy only (Blender's bundled numpy, or any venv).
"""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

BUCKET_M = 130.0       # the assembler's band_clamp bucket (B), not a new number
RINGS = 40             # the assembler's ring limit (r < 40), not a new number


def _rings_order(r: int):
    """the bucket offsets band_clamp visits at ring r, in its order (dx outer, dz inner; ring 1 = the full 3 x 3)"""
    out = []
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            if r > 1 and max(abs(dx), abs(dz)) != r:
                continue
            out.append((dx, dz))
    return out


def band_clamp_np(grid_xyz, road_pts, band):
    """In place, as build_loop_blend.band_clamp(grid_xyz, road_pts, band)."""
    B = BUCKET_M
    buck = defaultdict(list)
    for (x, y, z) in road_pts:
        buck[(int(x // B), int(z // B))].append((x, y, z))
    barr = {k: np.asarray(v, float) for k, v in buck.items()}
    ny, nx = len(grid_xyz), len(grid_xyz[0])
    G = np.asarray(grid_xyz, float)                       # (ny, nx, 3)
    X, Y, Z = G[..., 0], G[..., 1], G[..., 2]
    BX = np.floor_divide(X, B).astype(np.int64)
    BZ = np.floor_divide(Z, B).astype(np.int64)
    key = BX * 1_000_003 + BZ
    flat_order = np.argsort(key.ravel(), kind="stable")
    ks = key.ravel()[flat_order]
    cuts = np.flatnonzero(np.diff(ks)) + 1
    groups = np.split(flat_order, cuts)
    Xf, Zf, Yf = X.ravel(), Z.ravel(), Y.ravel()
    BXf, BZf = BX.ravel(), BZ.ravel()
    newY = Yf.copy()
    ring_cache = {}
    for g in groups:
        bx, bz = int(BXf[g[0]]), int(BZf[g[0]])
        cand = []
        r = 1
        while not cand and r < RINGS:
            if r not in ring_cache:
                ring_cache[r] = _rings_order(r)
            for dx, dz in ring_cache[r]:
                a = barr.get((bx + dx, bz + dz))
                if a is not None:
                    cand.append(a)
            r += 1
        if not cand:
            continue                                      # ry None: the vertex is left as it is
        C = np.concatenate(cand, axis=0)                  # in band_clamp's visiting order
        d = (Xf[g][:, None] - C[None, :, 0]) ** 2 + (Zf[g][:, None] - C[None, :, 2]) ** 2
        ry = C[np.argmin(d, axis=1), 1]                   # the first minimum, as its strict '<'
        newY[g] = np.maximum(ry - band, np.minimum(ry + band, Yf[g]))
    NY = newY.reshape(ny, nx)
    changed = np.argwhere(NY != Y)
    for j, i in changed.tolist():
        x, _y, z = grid_xyz[j][i]
        grid_xyz[j][i] = (x, float(NY[j, i]), z)
    return int(len(changed))


def _road_samples(roads, step_m=5.0):
    """(x, z, half width) every <= step_m along each (points_xyz, widths) line"""
    out = []
    for pts, ws in roads:
        n = len(pts)
        for k in range(n):
            out.append((pts[k][0], pts[k][2], ws[k] / 2.0))
            if k + 1 < n:
                a, b = pts[k], pts[k + 1]
                L = math.hypot(b[0] - a[0], b[2] - a[2])
                m = int(L // step_m)
                for s in range(1, m + 1):
                    t = s / (m + 1)
                    out.append((a[0] + (b[0] - a[0]) * t, a[2] + (b[2] - a[2]) * t,
                                (ws[k] + (ws[k + 1] - ws[k]) * t) / 2.0))
    return out


def fine_cells(grid_xyz, roads, fine_m, step):
    """bool (NJ, NI): the native cells (``step`` fine cells a side) whose square comes within fine_m of a pavement edge
    (the square's bounding box test: a superset, never fewer)"""
    ny, nx = len(grid_xyz), len(grid_xyz[0])
    NJ, NI = (ny - 1) // step, (nx - 1) // step
    x0, z0 = grid_xyz[0][0][0], grid_xyz[0][0][2]
    cx = (grid_xyz[0][nx - 1][0] - x0) / (nx - 1) * step     # native cell size, x (east)
    cz = (z0 - grid_xyz[ny - 1][0][2]) / (ny - 1) * step     # native cell size, rows run north -> south
    F = np.zeros((NJ, NI), bool)
    for x, z, hw in _road_samples(roads):
        R = fine_m + hw
        i_a = max(0, int(math.floor((x - R - x0) / cx)))
        i_b = min(NI - 1, int(math.floor((x + R - x0) / cx)))
        j_a = max(0, int(math.floor((z0 - (z + R)) / cz)))
        j_b = min(NJ - 1, int(math.floor((z0 - (z - R)) / cz)))
        if i_a <= i_b and j_a <= j_b:
            F[j_a:j_b + 1, i_a:i_b + 1] = True
    return F


def tiered_terrain(grid_xyz, roads, *, fine_m, step, tile_m=6.0, skirt_m=500.0):
    """grass_terrain's mesh dict, tiered (module doc). roads: [(points_xyz, widths)]."""
    ny, nx = len(grid_xyz), len(grid_xyz[0])
    if (ny - 1) % step or (nx - 1) % step:
        raise SystemExit(f"[fwlm_terrain] the grid ({ny} x {nx}) is not whole native cells of {step}: the intake's "
                         f"grid_upsample x the assembler's x2 must be {step}")
    NJ, NI = (ny - 1) // step, (nx - 1) // step
    F = fine_cells(grid_xyz, roads, fine_m, step)
    idx = {}
    verts, uvs, tris = [], [], []

    def v(j, i):
        k = idx.get((j, i))
        if k is None:
            k = idx[(j, i)] = len(verts)
            p = grid_xyz[j][i]
            verts.append(p)
            uvs.append((p[0] / tile_m, p[2] / tile_m))
        return k
    n_fan = 0
    for J in range(NJ):
        for I in range(NI):
            j0, i0 = J * step, I * step
            if F[J, I]:
                for jj in range(j0, j0 + step):
                    for ii in range(i0, i0 + step):
                        a, b, c, d = v(jj, ii), v(jj, ii + 1), v(jj + 1, ii + 1), v(jj + 1, ii)
                        tris.append((a, b, c))
                        tris.append((a, c, d))
                continue
            N = J > 0 and F[J - 1, I]
            S = J < NJ - 1 and F[J + 1, I]
            W = I > 0 and F[J, I - 1]
            E = I < NI - 1 and F[J, I + 1]
            if not (N or S or W or E):
                a, b, c, d = v(j0, i0), v(j0, i0 + step), v(j0 + step, i0 + step), v(j0 + step, i0)
                tris.append((a, b, c))
                tris.append((a, c, d))
                continue
            loop = []
            loop += [(j0, i0 + t) for t in (range(step) if N else (0,))]                       # NW -> NE
            loop += [(j0 + t, i0 + step) for t in (range(step) if E else (0,))]                # NE -> SE
            loop += [(j0 + step, i0 + step - t) for t in (range(step) if S else (0,))]         # SE -> SW
            loop += [(j0 + step - t, i0) for t in (range(step) if W else (0,))]                # SW -> NW
            c = v(j0 + step // 2, i0 + step // 2)
            L = [v(j, i) for j, i in loop]
            for k in range(len(L)):
                tris.append((c, L[k], L[(k + 1) % len(L)]))
            n_fan += 1
    if skirt_m > 0.0:
        # grass_terrain's watertight skirt, over the border nodes the mesh uses (in its order: N, E, S, W)
        perim = []
        for i in range(nx):
            perim.append(((0, i), 0.0, skirt_m))
        for j in range(1, ny):
            perim.append(((j, nx - 1), skirt_m, 0.0))
        for i in range(nx - 2, -1, -1):
            perim.append(((ny - 1, i), 0.0, -skirt_m))
        for j in range(ny - 2, 0, -1):
            perim.append(((j, 0), -skirt_m, 0.0))
        perim = [(idx[ji], dx, dz) for ji, dx, dz in perim if ji in idx]
        low_y = min(p[1] for row in grid_xyz for p in row) - 5.0      # grass_terrain's: every grid vertex
        outer = []
        for gi, dx, dz in perim:
            x, _y, z = verts[gi]
            outer.append(len(verts))
            verts.append((x + dx, low_y, z + dz))
            uvs.append(((x + dx) / tile_m, (z + dz) / tile_m))
        P = len(perim)
        for k in range(P):
            g0, g1 = perim[k][0], perim[(k + 1) % P][0]
            o0, o1 = outer[k], outer[(k + 1) % P]
            tris.append((g0, o0, o1))
            tris.append((g0, o1, g1))
    rep = {"grid": [ny, nx], "native_cells": int(NJ * NI), "fine_cells": int(F.sum()), "fan_cells": n_fan,
           "vertices": len(verts), "tris": len(tris), "grid_vertices_untiered": ny * nx, "fine_m": fine_m, "step": step}
    return {"vertices": verts, "uvs": uvs, "tris": tris}, rep
