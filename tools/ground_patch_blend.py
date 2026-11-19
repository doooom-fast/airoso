"""Seat loop.blend's TERRAIN on a measured lidar ground patch (ledger 0079 round I; opt-in terrain.lidar_patches).

tools/lidar_ground_patch.py measured the real ground of each declared polygon on a lattice (source/ground_patches.lidar.json,
terrain.lidar_patches_file). Here, in the draft after the weld and the seats:
  1. TERRAIN's faces touching the polygon's box grown by feather_m are cut (edges split in the middle, pass after pass)
     until no edge there is longer than SPLIT_M, so the ground can hold a step as sharp as the lattice: a retaining wall
     stands as the step the lidar shows across one short edge (no wall object: the engine has no retaining-wall path);
  2. every TERRAIN vertex inside the polygon takes the lattice's ground (bilinear); outside it, within feather_m of an
     edge the patch does not mark hard (hard_edges: the wall's line, where the step IS the ground), the built height
     moves toward the lattice's by 1 - d / feather_m. Vertices with no reading around them stay as built.

Opt-in (ledger 0092, Milford; a patch without these is cut and seated exactly as before):
  - a lattice with its own weight per node ("w": a corridor patch, tools/lidar_ground_patch.py --npz) moves a vertex inside
    the polygon by that weight (bilinear) instead of all the way, and only edges with a vertex where the weight is over 0
    are cut;
  - "split_mode": "bisect" cuts by longest-edge bisection (each long edge split at its middle, each triangle on it split
    through the new vertex and its opposite corner, longest first, pass after pass): every face stays a triangle with no
    T-vertex. The default subdivide-and-triangulate pass, on ground that holds zero-area slivers (the 0.1.5 gate OBJ's
    prepped ground, a stand-in), cut the same few edges round after round and doubled duplicate faces each time
    (767,963 faces -> 2,348,881, 1,296,864 of them duplicates, for 146,000 new vertices).

Self-check, exit 1 and loop.blend not saved: no TERRAIN; a patch with no lattice in the file (re-run the measuring tool);
a polygon vertex the lattice does not cover; the measured file's polygon not the config's.

No terrain.lidar_patches = no-op (Lake Murray and the Lariat name none).

    blender --background --python tools/ground_patch_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

SPLIT_M = 1.5        # [invented] the longest TERRAIN edge left in a patch's box (the lattice is 1 m)


def seg_dist(px, pz, a, b):
    ax, az = a
    bx, bz = b
    dx, dz = bx - ax, bz - az
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
    return math.hypot(px - ax - t * dx, pz - az - t * dz)


def point_in(poly, x, z):
    c = False
    for k in range(len(poly)):
        (x1, z1), (x2, z2) = poly[k - 1], poly[k]
        if (z1 > z) != (z2 > z) and x < x1 + (z - z1) * (x2 - x1) / (z2 - z1):
            c = not c
    return c


def lattice_at(L, x, z):
    c = L["cell_m"]
    fx, fz = (x - L["x0"]) / c, (z - L["z0"]) / c
    i, j = int(math.floor(fx)), int(math.floor(fz))
    if i < 0 or j < 0 or i + 1 >= L["nx"] or j + 1 >= L["nz"]:
        return None
    y = L["y"]
    q = [y[(j + dj) * L["nx"] + i + di] for dj in (0, 1) for di in (0, 1)]
    w = [(1 - (fx - i)) * (1 - (fz - j)), (fx - i) * (1 - (fz - j)), (1 - (fx - i)) * (fz - j), (fx - i) * (fz - j)]
    got = [(a, b) for a, b in zip(q, w) if a is not None]
    if not got or sum(b for _, b in got) < 1e-9:
        return None
    return sum(a * b for a, b in got) / sum(b for _, b in got)


def weight_at(L, x, z):
    """a corridor lattice's own weight at (x, z), bilinear over its nodes (ledger 0092); 0 off the lattice"""
    c = L["cell_m"]
    fx, fz = (x - L["x0"]) / c, (z - L["z0"]) / c
    i, j = int(math.floor(fx)), int(math.floor(fz))
    if i < 0 or j < 0 or i + 1 >= L["nx"] or j + 1 >= L["nz"]:
        return 0.0
    w = L["w"]
    u, v = fx - i, fz - j
    return ((1 - u) * (1 - v) * w[j * L["nx"] + i] + u * (1 - v) * w[j * L["nx"] + i + 1]
            + (1 - u) * v * w[(j + 1) * L["nx"] + i] + u * v * w[(j + 1) * L["nx"] + i + 1])


def bisect(bm, split, live):
    """opt-in "split_mode": "bisect" (ledger 0092): longest-edge bisection of every edge longer than split with a live vertex"""
    tri = [f for f in bm.faces if len(f.verts) > 3 and any(live(v) for v in f.verts)]
    if tri:
        bmesh.ops.triangulate(bm, faces=tri)
    n = 0
    for _ in range(64):
        long_e = sorted((e for e in bm.edges if e.calc_length() > split and any(live(v) for v in e.verts)),
                        key=lambda e: -e.calc_length())
        if not long_e:
            break
        for e in long_e:
            if not e.is_valid or e.calc_length() <= split:
                continue
            opp = []
            for f in e.link_faces:
                o = [v for v in f.verts if v not in e.verts]
                opp.append((f, o[0] if len(o) == 1 else None))
            nv = bmesh.utils.edge_split(e, e.verts[0], 0.5)[1]
            n += 1
            for f, o in opp:
                if o is not None and f.is_valid and len(f.verts) == 4:
                    bmesh.utils.face_split(f, nv, o)
    return n


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    proj = Path(argv[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    ter = cfg.get("terrain") or {}
    patches = ter.get("lidar_patches") or []
    if not patches:
        print("[ground-patch] no terrain.lidar_patches: nothing to do")
        return
    meas = json.loads((proj / ter["lidar_patches_file"]).read_text(encoding="utf-8"))["patches"]
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    ob = bpy.data.objects.get("TERRAIN")
    if ob is None:
        raise SystemExit("[ground-patch] FATAL: no TERRAIN in loop.blend; not saved")
    mw = ob.matrix_world
    if any(abs(mw[r][c] - (1.0 if r == c else 0.0)) > 1e-9 for r in range(4) for c in range(4)):
        raise SystemExit("[ground-patch] FATAL: TERRAIN carries a transform; not saved")
    me = ob.data
    for p in patches:
        L = meas.get(p["id"])
        if L is None:
            raise SystemExit(f"[ground-patch] FATAL: {p['id']} not in {ter['lidar_patches_file']} (run "
                             "tools/lidar_ground_patch.py); not saved")
        if [list(map(float, q)) for q in L["polygon"]] != [list(map(float, q)) for q in p["polygon"]]:
            raise SystemExit(f"[ground-patch] FATAL: {p['id']}: the measured polygon is not the config's; not saved")
        poly = [tuple(q) for q in p["polygon"]]
        F = float(p.get("feather_m", 0.0))
        hard = set(int(k) for k in p.get("hard_edges", []))
        soft = [(poly[k - 1], poly[k]) for k in range(len(poly)) if k not in hard]
        allx = [q[0] for q in poly]
        allz = [q[1] for q in poly]
        bx0, bx1, bz0, bz1 = min(allx) - F, max(allx) + F, min(allz) - F, max(allz) + F
        # a patch's own edge length (opt-in "split_m", ledger 0085: Pikes Peak's whole infield, 1-4 % grades, at 3 m;
        # absent = SPLIT_M, Sand Creek's retaining-wall step)
        split = float(p.get("split_m", SPLIT_M))
        weighted = L.get("w") is not None          # a corridor lattice (ledger 0092): its own weight per node
        for q in poly:
            if lattice_at(L, q[0], q[1]) is None and not (L["x0"] <= q[0] <= L["x0"] + (L["nx"] - 1) * L["cell_m"]):
                raise SystemExit(f"[ground-patch] FATAL: {p['id']}: the lattice does not cover {q}; not saved")
        # 1. cut the box's faces down to SPLIT_M edges (Blender X = local x, Y = local z, Z = local y)
        bm = bmesh.new()
        bm.from_mesh(me)
        n0 = len(bm.verts)
        if p.get("split_mode") == "bisect":          # opt-in (ledger 0092): longest-edge bisection, triangles only
            def live(v):
                return (bx0 <= v.co.x <= bx1 and bz0 <= v.co.y <= bz1
                        and (not weighted or weight_at(L, v.co.x, v.co.y) > 0))
            bisect(bm, split, live)
        for _ in range(0 if p.get("split_mode") == "bisect" else 12):
            bm.edges.ensure_lookup_table()
            if weighted:
                # only where the corridor's weight is over 0 (every vertex read once per pass)
                bm.verts.index_update()
                live = [bx0 <= v.co.x <= bx1 and bz0 <= v.co.y <= bz1 and weight_at(L, v.co.x, v.co.y) > 0 for v in bm.verts]
                long_e = [e for e in bm.edges if e.calc_length() > split and any(live[v.index] for v in e.verts)]
            else:
                long_e = [e for e in bm.edges if e.calc_length() > split
                          and any(bx0 <= v.co.x <= bx1 and bz0 <= v.co.y <= bz1 for v in e.verts)]
            if not long_e:
                break
            bmesh.ops.subdivide_edges(bm, edges=long_e, cuts=1, use_grid_fill=False)
            bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3
                                             and any(bx0 <= v.co.x <= bx1 and bz0 <= v.co.y <= bz1 for v in f.verts)])
        # 2. seat the vertices
        moved, fe, worst = 0, 0, 0.0
        for v in bm.verts:
            x, z = v.co.x, v.co.y
            if not (bx0 <= x <= bx1 and bz0 <= z <= bz1):
                continue
            g = lattice_at(L, x, z)
            if g is None:
                continue
            if point_in(poly, x, z):
                w = weight_at(L, x, z) if weighted else 1.0
                if w <= 0:
                    continue
            elif F > 0 and soft:
                d_all = min(seg_dist(x, z, poly[k - 1], poly[k]) for k in range(len(poly)))
                d_soft = min(seg_dist(x, z, a, b) for a, b in soft)
                if d_soft > d_all + 1e-6 or d_soft >= F:
                    continue
                w = 1.0 - d_soft / F
                fe += 1
            else:
                continue
            dy = (g - v.co.z) * w
            if abs(dy) > 1e-6:
                worst = max(worst, abs(dy))
                v.co.z += dy
                moved += 1
        bm.to_mesh(me)
        bm.free()
        me.update()
        print(f"[ground-patch] {p['id']}: TERRAIN {n0} -> {len(me.vertices)} vertices (edges <= {split} m in the box"
              + (", where its weight is over 0" if weighted else "") + f"), {moved} seated on the lidar ground "
              f"({fe} in the {F:.0f} m feather), largest move {worst:.2f} m")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[ground-patch] {len(patches)} patch(es); saved loop.blend")


main()
