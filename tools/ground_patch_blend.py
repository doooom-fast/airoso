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

THE EDGE LIFT (opt-in per patch, "lift": {"clear_m", "gap_m", "road_prefixes"}; ledger 0098 round 2, Sand Creek's Quebec
pad and arms): a lift patch moves ground UP only, never down, and never above the measured lidar ground. Inside its polygon,
a TERRAIN vertex under a road-class surface (an object named with one of road_prefixes; the lowest sheet over it) rises to
min(lidar, that sheet - clear_m); a vertex off the road within gap_m of one (in plan) rises to min(lidar, the road's height
at its nearest point - clear_m): the lip. Nothing is cut, nothing past gap_m moves, and a vertex already at or over its
target stays where it is. It is for the ground next to a built edge that the seats left under the real ground: beside a
connector, seat_terrain pins only to route.seat_edge_m and past it only pulls ground down; outside a pad's outline lm_pads
only lowers within its edge band. Run after the patches that seat the ground beside (a lift patch is listed after them).
A patch may also name "feather_spares_roads": [prefix, ...] (opt-in, the same round): its feather then leaves every vertex
under a road-class surface of those names where it is (a soft edge's feather that reaches a road stops at the road's edge).

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
from mathutils.bvhtree import BVHTree

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


def tri_height(t, x, y):
    """the height of the plane through triangle t ((x, y, z) x 3) at plan point (x, y); None for a degenerate triangle"""
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(d) < 1e-12:
        return None
    l1 = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / d
    l2 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / d
    return l1 * az + l2 * bz + (1.0 - l1 - l2) * cz


def lift_to(z, ground, lip):
    """the edge lift's rule: up to min(the lidar ground, the lip), never down; None = the vertex stays"""
    if ground is None or lip is None:
        return None
    t = min(ground, lip)
    return t if z < t - 1e-4 else None


def road_sheets(prefixes, box):
    """the road-class objects' world triangles touching box (x0, x1, y0, y1): (plan BVH at z 0, 3D BVH, triangles)"""
    x0, x1, y0, y1 = box
    tris = []
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.name.upper().startswith(prefixes):
            continue
        mw = ob.matrix_world
        me = ob.data
        me.calc_loop_triangles()
        V = [mw @ v.co for v in me.vertices]
        for lt in me.loop_triangles:
            t = [V[i] for i in lt.vertices]
            if max(q.x for q in t) < x0 or min(q.x for q in t) > x1 or max(q.y for q in t) < y0 or min(q.y for q in t) > y1:
                continue
            if abs((t[1].x - t[0].x) * (t[2].y - t[0].y) - (t[2].x - t[0].x) * (t[1].y - t[0].y)) < 2e-4:
                continue                      # no plan area (a curb face, a skirt): it holds no height to lift to
            tris.append(tuple((q.x, q.y, q.z) for q in t))
    if not tris:
        return None, None, tris
    faces = [(3 * k, 3 * k + 1, 3 * k + 2) for k in range(len(tris))]
    flat = BVHTree.FromPolygons([(q[0], q[1], 0.0) for t in tris for q in t], faces)
    full = BVHTree.FromPolygons([q for t in tris for q in t], faces)
    return flat, full, tris


def edge_lift(bm, L, poly, cfg):
    """the opt-in edge lift (see the docstring): returns (under-road lifted, beside lifted, capped by the lidar, largest)"""
    clear, gap = float(cfg["clear_m"]), float(cfg["gap_m"])
    prefixes = tuple(str(s).upper() for s in cfg["road_prefixes"])
    xs, ys = [q[0] for q in poly], [q[1] for q in poly]
    box = (min(xs) - gap, max(xs) + gap, min(ys) - gap, max(ys) + gap)
    flat, full, tris = road_sheets(prefixes, box)
    if not tris:
        raise SystemExit(f"[ground-patch] FATAL: lift: no road-class triangle ({', '.join(prefixes)}) in the patch; not saved")
    n_under = n_side = capped = 0
    worst = 0.0
    for v in bm.verts:
        x, y = v.co.x, v.co.y
        if not (box[0] <= x <= box[1] and box[2] <= y <= box[3]) or not point_in(poly, x, y):
            continue
        near = flat.find_nearest((x, y, 0.0), gap)
        if near[0] is None:
            continue
        if near[3] < 1e-6:                    # under a road: its lowest sheet
            lo, top = None, 1e4
            for _ in range(8):
                hit = full.ray_cast((x, y, top), (0.0, 0.0, -1.0))
                if hit[0] is None:
                    break
                lo, top = hit[0].z, hit[0].z - 1e-4
            if lo is None:                    # on the sheet's very edge (a pad outline vertex): the ray slips past it,
                lo = tri_height(tris[near[2]], near[0].x, near[0].y)   # so its height there (0.2.11's median nose)
            lip = None if lo is None else lo - clear
        else:                                 # beside one: the road's height at its nearest point
            h = tri_height(tris[near[2]], near[0].x, near[0].y)
            lip = None if h is None else h - clear
        g = lattice_at(L, x, y)
        z = lift_to(v.co.z, g, lip)
        if z is None:
            continue
        capped += g < lip
        worst = max(worst, z - v.co.z)
        if near[3] < 1e-6:
            n_under += 1
        else:
            n_side += 1
        v.co.z = z
    return n_under, n_side, capped, worst


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
        if p.get("lift") is not None:              # opt-in (ledger 0098 round 2): the edge lift, up only, to the lidar
            if weighted or F > 0 or p.get("split_mode") or p.get("split_m") is not None:
                raise SystemExit(f"[ground-patch] FATAL: {p['id']}: a lift patch cuts nothing and has no feather, weight or "
                                 "split; not saved")
            bm = bmesh.new()
            bm.from_mesh(me)
            nu, ns_, cap, worst = edge_lift(bm, L, poly, p["lift"])
            bm.to_mesh(me)
            bm.free()
            me.update()
            print(f"[ground-patch] {p['id']}: edge lift: {nu} vertices under a road and {ns_} beside one (within "
                  f"{float(p['lift']['gap_m']):.2f} m) lifted, {cap} of them to the lidar (under the lip), largest lift "
                  f"{worst:.2f} m; nothing lowered")
            continue
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
        spare = None                               # opt-in (ledger 0098 round 2): the feather leaves the roads alone
        if p.get("feather_spares_roads") is not None:
            spare, _full, _tris = road_sheets(tuple(str(s).upper() for s in p["feather_spares_roads"]), (bx0, bx1, bz0, bz1))
            if not _tris:
                spare = None                       # no road in the box: nothing to spare
        spared = 0
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
                if spare is not None and spare.find_nearest((x, z, 0.0), 1e-3)[0] is not None:
                    spared += 1
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
              f"({fe} in the {F:.0f} m feather), largest move {worst:.2f} m"
              + (f"; {spared} under a road left by the feather" if spare is not None else ""))
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[ground-patch] {len(patches)} patch(es); saved loop.blend")


main()
