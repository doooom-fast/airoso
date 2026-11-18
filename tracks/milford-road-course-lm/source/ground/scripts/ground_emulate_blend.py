"""Ledger 0092, item 2: a gate OBJ's ground re-seated on the 2017 lidar the way terrain.lidar_patches + engine-july's prep
would leave it, then drive_test's excursion sweep replayed on it (a MODEL: the draft TERRAIN under that OBJ is not on the
Mac; under the pavement the prep pins, within 3 m of a road vertex it holds the shelf, 3-9 m it feathers onto the new TERRAIN,
beyond it the new TERRAIN; the anti-poke clamp; the sweep as scripts/geometry/drive_test.py's paved branch with its downward
wall guard). With full_m = zero_m = 0 it is the OBJ as built (on 0.1.5: 0 gated, 21 far ledges, its own drive_test.full.json).

blender -b --python ground_emulate_blend.py -- <track.obj> <gate_centerline.json> <out.json> <full_m> <zero_m> [in0 in1]
    env NPZ = the 1 m lidar grid (default: this track's source/lidar/milford_lidar_1m.npz)
    env DEDGE = the 1 m lane-edge distance raster on that grid (the scenery audit's out/lidar1m_dedge.npy)
full_m / zero_m: the corridor weight (1 to full_m off the lane edge, linear to 0 at zero_m); in0 / in1: 0 -> 1 from in0 to in1."""
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

a = sys.argv[sys.argv.index("--") + 1:]
obj_p, gate_p, out_p = Path(a[0]), Path(a[1]), Path(a[2])
FULL, ZERO = float(a[3]), float(a[4])
IN0, IN1 = (float(a[5]), float(a[6])) if len(a) > 6 else (None, None)
NPZ = Path(os.environ.get("NPZ") or Path(__file__).resolve().parents[2] / "lidar" / "milford_lidar_1m.npz")
DEDGE = Path(os.environ.get("DEDGE") or "/Volumes/Sundowning/codex/mac/milford-hp-audit-20261118/scenery/out/lidar1m_dedge.npy")
ELEV0 = 316.26
BAND_M, FEATHER_M, GROUND_CLEAR = 3.0, 6.0, 0.02

groups, V, cur = {}, [], None
with open(obj_p, encoding="utf-8", errors="replace") as f:
    for ln in f:
        c = ln[:2]
        if c == "v ":
            p = ln.split()
            V.append((float(p[1]), float(p[2]), float(p[3])))
        elif c in ("o ", "g "):
            cur = ln[2:].strip()
            groups.setdefault(cur, [])
        elif c == "f " and cur is not None:
            groups[cur].append([int(q.split("/")[0]) - 1 for q in ln.split()[1:]])
V = np.array(V, float)

lid = np.load(NPZ)
e0, n0, z0 = int(lid["e0"]), int(lid["n0"]), float(lid["z0_m"])
gzc = lid["ground_z_cm_over_z0"]
ny, nx = gzc.shape
L = np.where(gzc != -1, z0 + gzc / 100.0 - ELEV0, np.nan)
D = np.load(DEDGE)
# fill holes within the corridor from their neighbours (as tools/lidar_ground_patch.py does under roofs)
inside = np.isfinite(D) & (D <= ZERO + 1.0) if ZERO > 0 else np.zeros_like(D, bool)
filled = 0
while True:
    hole = np.isnan(L) & inside
    if not hole.any():
        break
    pad = np.pad(L, 1, constant_values=np.nan)
    nb = np.stack([pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]])
    cnt = (~np.isnan(nb)).sum(0)
    take = hole & (cnt > 0)
    if not take.any():
        break
    L[take] = np.nansum(nb, 0)[take] / cnt[take]
    filled += int(take.sum())


def wp_of(d):
    if ZERO <= 0 or not np.isfinite(d) or d >= ZERO:
        return 0.0
    w = 1.0 if d <= FULL else (ZERO - d) / (ZERO - FULL)
    if IN0 is not None:
        if d <= IN0:
            return 0.0
        if d < IN1:
            w *= (d - IN0) / (IN1 - IN0)
    return w


def lid_at(x, z):
    fx, fz = x - e0 - 0.5, z - n0 - 0.5
    i, j = int(math.floor(fx)), int(math.floor(fz))
    if i < 0 or j < 0 or i + 1 >= nx or j + 1 >= ny:
        return None
    q = [L[j, i], L[j, i + 1], L[j + 1, i], L[j + 1, i + 1]]
    u, v = fx - i, fz - j
    w = [(1 - u) * (1 - v), u * (1 - v), (1 - u) * v, u * v]
    got = [(qq, ww) for qq, ww in zip(q, w) if np.isfinite(qq)]
    if not got or sum(ww for _, ww in got) < 1e-9:
        return None
    return sum(qq * ww for qq, ww in got) / sum(ww for _, ww in got)


def d_at(x, z):
    i, j = int(math.floor(x - e0)), int(math.floor(z - n0))
    if 0 <= i < nx and 0 <= j < ny:
        return float(D[j, i])
    return float("inf")


def tris_of(pred):
    out = []
    for g, fs in groups.items():
        if pred(g.upper()):
            for fc in fs:
                for k in range(1, len(fc) - 1):
                    out.append((fc[0], fc[k], fc[k + 1], g))
    return out


def bvh(tris, Vz):
    verts = [(Vz[t][0], Vz[t][2], Vz[t][1]) for tr in tris for t in tr[:3]]
    return BVHTree.FromPolygons(verts, [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tris))]) if tris else None


road_t = tris_of(lambda g: g.startswith("1ROAD"))
driv_t = tris_of(lambda g: g.startswith(("1ROAD", "1KERB")))
grass_t = tris_of(lambda g: g.startswith("1GRASS"))
wall_t = tris_of(lambda g: g.startswith("1WALL"))
road_b = bvh(road_t, V)
driv_b = bvh(driv_t, V)
wall_b = bvh(wall_t, V)
rv = sorted({int(t) for tr in road_t for t in tr[:3]})
kd = KDTree(len(rv))
for k, i in enumerate(rv):
    kd.insert((V[i][0], V[i][2], 0.0), k)
kd.balance()

gidx = sorted({int(t) for tr in grass_t for t in tr[:3]})
V2 = V.copy()
moved, worst = 0, 0.0
stats = {"pinned": 0, "shelf": 0, "feather": 0, "beyond": 0}
if ZERO > 0:
    for i in gidx:
        x, y, z = V[i]
        d = d_at(x, z)
        wp = wp_of(d)
        if wp <= 0:
            continue
        g = lid_at(x, z)
        if g is None:
            continue
        co, k, d2d = kd.find((x, z, 0.0))
        hit = road_b.ray_cast(Vector((x, z, 4000.0)), Vector((0, 0, -1)))
        if hit[0] is not None and abs(hit[0].z - y) < 30.0:
            stats["pinned"] += 1
            continue                                        # under the pavement: the prep pins it
        if d2d <= BAND_M:
            stats["shelf"] += 1
            continue                                        # the prep's shelf: deck - 0.02 whatever was there
        if d2d < BAND_M + FEATHER_M:
            w = 1.0 - (d2d - BAND_M) / FEATHER_M
            w = w * w * (3 - 2 * w)
            nr = road_b.find_nearest(Vector((x, z, y)))
            tgt = (nr[0].z if nr[0] is not None else V[rv[k]][1]) - GROUND_CLEAR
            z_old = (y - tgt * w) / (1.0 - w)
            z_new = g * wp + z_old * (1 - wp)
            ny_ = tgt * w + z_new * (1 - w)
            stats["feather"] += 1
        else:
            ny_ = g * wp + y * (1 - wp)
            stats["beyond"] += 1
        # anti-poke: never over the lowest drivable sheet
        h2 = driv_b.ray_cast(Vector((x, z, ny_ + 20.0)), Vector((0, 0, -1)), 40.0)
        if h2[0] is not None:
            z_top = h2[0].z
            z_lo = z_top
            zz = z_top - 0.02
            for _ in range(6):
                h3 = driv_b.ray_cast(Vector((x, z, zz)), Vector((0, 0, -1)), zz - (ny_ - 20.0))
                if h3[0] is None:
                    break
                z_lo = h3[0].z
                zz = z_lo - 0.02
            if ny_ > z_lo - GROUND_CLEAR and abs(z_lo - ny_) < 20:
                ny_ = z_lo - GROUND_CLEAR
        if abs(ny_ - y) > 1e-6:
            moved += 1
            worst = max(worst, abs(ny_ - y))
            V2[i][1] = ny_

surf_t = tris_of(lambda g: g.startswith(("1GRASS", "1ROAD", "1KERB")))
verts = [(V2[t][0], V2[t][2], V2[t][1]) for tr in surf_t for t in tr[:3]]
surf = BVHTree.FromPolygons(verts, [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(surf_t))])
own = [tr[3] for tr in surf_t]


def top(x, z, yref, win=8.0):
    h = surf.ray_cast(Vector((x, z, yref + win)), Vector((0, 0, -1)), 2 * win)
    if h[0] is None:
        return None, None
    return float(h[0].z), own[h[2]]


def wall_top(x, z, yref, win):
    if wall_b is None:
        return None
    h = wall_b.ray_cast(Vector((x, z, yref + win)), Vector((0, 0, -1)), 2 * win)
    return h[0]


gl = json.loads(gate_p.read_text())
pts, widths = gl["points_xyz_m"], gl["widths_m"]
n = len(pts)
wmed = sorted(widths)[n // 2]
exc = []
s2, nxt = 0.0, 0.0
for i in range(1, n):
    s2 += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2])
    if s2 < nxt:
        continue
    nxt += 150.0
    in_flare = widths[i] > wmed + 1.5
    x0, y0, zc = pts[i]
    pa, pb = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
    dx, dz = pb[0] - pa[0], pb[2] - pa[2]
    Ln = math.hypot(dx, dz) or 1.0
    tx, tz = dx / Ln, dz / Ln
    nx_, nz_ = -tz, tx
    we = widths[i] / 2
    for sgn in (1.0, -1.0):
        prev, off, built_edge = None, 0.0, None
        while off <= we + 9.0:
            ex, ez = x0 + nx_ * off * sgn, zc + nz_ * off * sgn
            ey, ow = top(ex, ez, y0)
            if ow is not None and ow.upper().startswith(("1ROAD", "1KERB")):
                built_edge = off
            in_band = built_edge is not None and off <= built_edge + 4.0 and not in_flare
            if ey is not None and prev is not None and prev - ey > 0.12 and off > we - 0.5:
                guarded = False
                wo = max(we - 0.4, 0.5)
                while wo < off - 0.25:
                    if wall_top(x0 + nx_ * wo * sgn, zc + nz_ * wo * sgn, y0 + 0.5, 2.5) is not None:
                        guarded = True
                        break
                    wo += 0.5
                exc.append({"s": round(s2, 1), "off": round(off * sgn, 2), "drop": round(prev - ey, 3),
                            "gated": bool(in_band and not guarded), "in_band": bool(in_band), "guarded": guarded,
                            "past_edge": round(off - (built_edge or 0), 2)})
            if ey is not None:
                prev = ey
            off += 0.5
res = {"obj": str(obj_p), "full_m": FULL, "zero_m": ZERO, "inner": [IN0, IN1], "lidar_filled": filled,
       "ground_verts_moved": moved, "largest_move_m": round(worst, 2), "by_zone": stats,
       "drops_gated": sum(e["gated"] for e in exc), "far_ledges": sum(not e["in_band"] for e in exc),
       "in_band_guarded": sum(e["in_band"] and e["guarded"] for e in exc), "drops": exc}
out_p.write_text(json.dumps(res, indent=1))
print(json.dumps({k: v for k, v in res.items() if k != "drops"}))
for e in exc:
    print(e)
