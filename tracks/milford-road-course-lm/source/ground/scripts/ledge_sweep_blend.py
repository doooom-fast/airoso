"""Milford round 2, the far ledges (read-only): drive_test's paved excursion sweep (scripts/geometry/drive_test.py,
surface = DRIVABLE groups, guard = any 1WALL between the edge and the drop), run every STEP m along the gate centreline
instead of every 150 m, and the 2017 lidar (source/lidar/milford_lidar_1m.npz) read at every sample.

blender -b --factory-startup --python ledge_sweep_blend.py -- <track.obj> <gate_centerline.json> <npz> <out.json> [step_m=3] [reach_extra=14]
A far ledge = a drop over 0.12 m between 0.5 m samples, past built_edge + 4 m, out to we + 9 m, unguarded, not in a flare
(drive_test's own rule). Every crossing is written with its samples out to we + reach_extra m."""
import json
import math
import sys

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
OBJ, GATE, NPZ, OUT = a[0], a[1], a[2], a[3]
STEP = float(a[4]) if len(a) > 4 else 3.0
EXTRA = float(a[5]) if len(a) > 5 else 14.0
ELEV0 = 316.26
DRIVABLE = ("1ROAD", "1KERB", "1RUNOFF", "1LAWN", "1GRASS")
PAINT = ("MARKINGS", "ROADTEXT", "YLINE")

V, groups, cur = [], [], None
if OBJ.lower().endswith(".blend"):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=OBJ)
    for o in bpy.context.scene.objects:
        if o.type != "MESH":
            continue
        mw = o.matrix_world
        base = len(V)
        V += [((mw @ v.co).x, (mw @ v.co).z, (mw @ v.co).y) for v in o.data.vertices]
        tris = []
        for f in o.data.polygons:
            idx = [base + k for k in f.vertices]
            for j in range(1, len(idx) - 1):
                tris.append((idx[0], idx[j], idx[j + 1]))
        groups.append({"name": o.name, "tris": tris})
    _obj_lines = []
else:
    _obj_lines = None
with (open(OBJ, encoding="utf-8", errors="replace") if _obj_lines is None else open(__file__, encoding="utf-8")) as fh:
    if _obj_lines is not None:
        fh = []
    for ln in fh:
        k = ln[:2]
        if k == "v ":
            p = ln.split()
            V.append((float(p[1]), float(p[2]), float(p[3])))
        elif k == "f ":
            if cur is not None:
                p = ln.split()
                idx = [int(q.partition("/")[0]) - 1 for q in p[1:]]
                for j in range(1, len(idx) - 1):
                    cur["tris"].append((idx[0], idx[j], idx[j + 1]))
        elif k == "o ":
            cur = {"name": ln[2:].strip(), "tris": []}
            groups.append(cur)


def bvh_of(pred):
    verts, polys, own = [], [], []
    for g in groups:
        up = g["name"].upper()
        if up.startswith(PAINT) or not pred(up):
            continue
        for t in g["tris"]:
            b = len(verts)
            for vi in t:
                x, y, z = V[vi]
                verts.append((x, z, y))
            polys.append((b, b + 1, b + 2))
            own.append(g["name"])
    return (BVHTree.FromPolygons(verts, polys) if polys else None), own


surf, surf_own = bvh_of(lambda up: up.startswith(DRIVABLE))
wall, _ = bvh_of(lambda up: up.startswith("1WALL"))

lid = np.load(NPZ)
e0, n0, z0 = int(lid["e0"]), int(lid["n0"]), float(lid["z0_m"])
gzc = lid["ground_z_cm_over_z0"]
ny, nx = gzc.shape
L = np.where(gzc != -1, z0 + gzc / 100.0 - ELEV0, np.nan)


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
    return float(sum(qq * ww for qq, ww in got) / sum(ww for _, ww in got))


def top(x, z, yref, win=8.0):
    h = surf.ray_cast(Vector((x, z, yref + win)), Vector((0, 0, -1)), 2 * win)
    if h[0] is None:
        return None, None
    return float(h[0].z), surf_own[h[2]]


def wall_at(x, z, yref, win=2.5):
    if wall is None:
        return False
    h = wall.ray_cast(Vector((x, z, yref + win)), Vector((0, 0, -1)), 2 * win)
    return h[0] is not None


gl = json.load(open(GATE, encoding="utf-8"))
pts, widths = gl["points_xyz_m"], gl["widths_m"]
n = len(pts)
wmed = sorted(widths)[n // 2]


def sweep(i, s2):
    in_flare = widths[i] > wmed + 1.5
    x0, y0, zc = pts[i]
    pa, pb = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
    dx, dz = pb[0] - pa[0], pb[2] - pa[2]
    Ln = math.hypot(dx, dz) or 1.0
    tx, tz = dx / Ln, dz / Ln
    nx_, nz_ = -tz, tx
    we = widths[i] / 2
    out = []
    for sgn in (1.0, -1.0):
        prev, off, built_edge, samples, ledges = None, 0.0, None, [], []
        while off <= we + EXTRA:
            ex, ez = x0 + nx_ * off * sgn, zc + nz_ * off * sgn
            ey, ow = top(ex, ez, y0)
            ly = lid_at(ex, ez)
            if ow is not None and ow.upper().startswith(("1ROAD", "1KERB")) and off <= we + 9.0:
                built_edge = off
            if ey is not None and prev is not None and prev - ey > 0.12 and off > we - 0.5 and off <= we + 9.0:
                in_band = built_edge is not None and off <= built_edge + 4.0 and not in_flare
                guarded = False
                wo = max(we - 0.4, 0.5)
                while wo < off - 0.25:
                    if wall_at(x0 + nx_ * wo * sgn, zc + nz_ * wo * sgn, y0 + 0.5):
                        guarded = True
                        break
                    wo += 0.5
                ledges.append({"off": round(off, 2), "drop": round(prev - ey, 3), "in_band": in_band,
                               "guarded": guarded, "far": (not in_band) and (not guarded)})
            samples.append([round(off, 2), None if ey is None else round(ey, 3), ow,
                            None if ly is None else round(ly, 3)])
            if ey is not None:
                prev = ey
            off += 0.5
        out.append({"s": round(s2, 1), "i": i, "side": int(sgn), "we": round(we, 3), "built_edge": built_edge,
                    "flare": in_flare, "xz": [round(x0, 2), round(zc, 2)], "n": [round(nx_ * sgn, 5), round(nz_ * sgn, 5)],
                    "ledges": ledges, "samples": samples})
    return out


res150, dense = [], []
s2, next150, nextd = 0.0, 0.0, 0.0
for i in range(1, n):
    s2 += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2])
    if s2 >= next150:
        next150 += 150.0
        res150 += sweep(i, s2)
    if s2 >= nextd:
        nextd += STEP
        dense += sweep(i, s2)

far150 = sum(1 for c in res150 for e in c["ledges"] if e["far"])
fard = sum(1 for c in dense for e in c["ledges"] if e["far"])
summary = {"obj": OBJ, "lap_m": round(s2, 1), "step_m": STEP, "crossings_150": len(res150), "far_150": far150,
           "crossings_dense": len(dense), "far_dense": fard,
           "crossings_with_far_dense": sum(1 for c in dense if any(e["far"] for e in c["ledges"]))}
json.dump({"summary": summary, "x150": res150, "dense": dense}, open(OUT, "w", encoding="utf-8"))
print("[ledges]", json.dumps(summary))
