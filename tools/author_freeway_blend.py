"""Lay the I-8's own pavement, lane lines and median barrier at the REAL freeway's height, and make the final ground meet
it (ledger 0046, v0.18.0 integration fix round and fix round 2; the plan, the heights and the WHY are in
tools/freeway_i8.py, which writes data/freeway_i8.json).

Runs INSIDE Blender on the PREPPED scene (<project>/blender/<slug>.blend, after build_kn5_loop and before
split_exports_blend), because the prep still reshapes the ground. It adds, all VISUAL ONLY (no digit prefix: no physics,
no gate scans them, the drive_test obstacle band is 0.25-1.8 m over a LANE of the loop, which nothing here is near):
  HIGHWAY_I8_NEAR_<k> / HIGHWAY_I8_FAR_<k>  the carriageways (pbr row HIGHWAY: cracked asphalt), lift_m over the slab's
        3DEP height; NEAR inside the 1ROAD extent (a GrassFX occluder: scripts/ac/ext_config.py), FAR beyond it;
  MARKINGS_I8_<k> / YLINE_I8_<k>            dashed lane lines and white outer / yellow median edge lines, NEAR only;
  BARRIER_I8_<k>                            the concrete median barrier (pbr row BARRIER), a Jersey profile.

Fix round 2 (2026-10-13), after the view lens refuted the integration fix round: the pavement was draped on the built
ground, so where that ground was wrong it went wrong with it — it climbed a 5-6 m hump under College Ave's deck, ran up
Lake Murray Blvd's abutment slopes, and the median barrier and a slab corner stood 0.94 / 0.63 m up THROUGH College's
deck (its "is a deck over me" ray started above the ground the draft had seated at the deck). Now:
  1. the slab's height is the real freeway's (3DEP, data/freeway_i8.json "h"), never the built ground's;
  2. a station is left out where any structure of the loop (1ROAD / 1KERB / BRIDGESTRUCT) stands anywhere from 1 m under
     its slab to DECK_CLEAR over it — the ray starts UNDER the slab, so a deck the ground reaches is seen;
  3. the GROUND meets the slab: in every near terrain tile (1GRASS_*) each edge crossing a carriageway's outline is split
     where it crosses, the two crossing points of each face joined, so the outline runs through the terrain; every
     terrain vertex on or inside it is set lift_m under the slab, and beside it the ground rises or falls from the
     pavement's edge no steeper than BATTER. Ground within HELD_KEEP_M of the loop's pavement never moves; within
     NEAR_LOOP_M (criterion 7's band) outside a release zone it takes the batter, and under the slab is only ever cut. The far ring (GRASS_FAR_*) is the
     data (criterion 6): never cut, a vertex under the slab only lowered by at most FAR_CUT_MAX;
  4. FATAL self-checks (scene NOT saved): a freeway vertex over a loop deck or within DECK_CLEAR under one; a pavement
     point (vertices, edge midpoints, centroids) under the ground + MIN_CLEAR; a terrain tile over 65,535 vertices.
Materials are bound exactly as the prep binds them (engine-july's pbr.setup_material by name prefix + the project's
overrides); UVs are the prep's planar 4 m projection; textures are packed and the scene saved in place. Writes
data/freeway_i8.report.json.

    blender --background --python-exit-code 1 --python tools/author_freeway_blend.py -- <project-dir> --eng <engine-july>
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

AIROSO = Path(__file__).resolve().parents[1]
UV_TILE = 4.0           # build_kn5_loop.UV_TILE
VERT_CAP = 60000        # build_kn5_loop.SPLIT_CAP
MIN_CLEAR = 0.03        # [invented] no pavement point within this of the ground
DECK_CLEAR = 2.0        # [invented] a station with any loop structure less than this over its slab is left out
DECK_UNDER = 1.0        # [invented] ...or less than this UNDER it (a deck the slab would stand on or poke through)
LINE_LIFT = 0.02        # [invented] lines over the pavement
SPLIT_MIN_M = 0.01       # [invented] the outline cut never splits an edge within this of its ends
BATTER = 1.0            # [invented] ground beside the freeway rises / falls from its edge no steeper than this (45 deg; fresh
#                         3DEP beyond the I-8's shoulders measured 27-45 deg east of College)
NEAR_LOOP_M = 20.0      # criterion 7's band: the ground this near the loop's pavement is never moved (outside release zones)
FAR_CUT_MAX = 0.15      # [invented] the most a far-ring vertex under the slab is lowered: criterion 6's 1 m less the far
#                         ring's own 0.85 m tent bound (GATES-CHANGELOG 0046 fix round 3), so no far vertex can leave 1 m
RAISE_MAX_FAR = 0.5     # [invented] beyond the loop's extent (HIGHWAY_I8_FAR, over the uncut far ring) the slab may rise this
#                         much over its 3DEP height where the ground stands over it, before a face is left out
HELD_KEEP_M = 6.0       # [invented] ground nearer than this to the loop's pavement is never moved (drive_test reads 4 m past the
#                         built edge; 2 m margin; at 10 m the 4-5 m rise from Alvarado's verge to the I-8's embankment was
#                         squeezed into walls 1,573 m2 >60 deg within 3 m of the freeway); between it and NEAR_LOOP_M
#                         held ground takes the freeway's batter (cut or fill) and, under the slab, is only ever cut down
#                         to it: the graded verges of the roads beside the I-8 stood 3.5 m under its real embankment and
#                         7.5 m over its real cut
BATTER_REACH_M = 8.0    # [invented] ...read within this of the outline
RAISE_MAX = 0.10        # [invented] most a slab vertex may rise over its 3DEP height where the outline cut fell short
GROUND_WIN = 1.5        # [invented] the clearance check reads the ground from this far over the slab down
OUTLINE_PAD = 0.03      # [invented] the ground conform reads the slab this far past its edges (the split points' float)
BAR_BASE, BAR_TOP, BAR_H, BAR_SINK = 0.60, 0.20, 0.81, 0.30
TILE_CAP = 65535


def _fw():
    spec = importlib.util.spec_from_file_location("_airoso_freeway_i8", AIROSO / "tools" / "freeway_i8.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _bvh(objs):
    vs, fs = [], []
    for ob in objs:
        base = len(vs)
        mw = ob.matrix_world
        vs += [tuple(mw @ v.co) for v in ob.data.vertices]
        fs += [tuple(base + i for i in p.vertices) for p in ob.data.polygons]
    return BVHTree.FromPolygons(vs, fs) if fs else None


class Mesh:
    def __init__(self):
        self.v, self.f = [], []

    def add(self, p):
        self.v.append(list(p))
        return len(self.v) - 1


def _ob(name, M):
    used = sorted({i for f in M.f for i in f})
    if len(used) != len(M.v):                     # faces left out leave loose vertices: compact
        remap = {o: n for n, o in enumerate(used)}
        M.v = [M.v[o] for o in used]
        M.f = [tuple(remap[i] for i in f) for f in M.f]
    me = bpy.data.meshes.new(name)
    me.from_pydata(M.v, [], M.f)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (co.x / UV_TILE, co.y / UV_TILE)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    down = [f for f in bm.faces if f.normal.z < 0 and abs(f.normal.z) > 0.2]
    if down and not name.startswith("BARRIER"):
        bmesh.ops.reverse_faces(bm, faces=down)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return ob


def _held_w(hd):
    """the share of a move a held vertex takes at plan distance hd from the loop's pavement: 0 at HELD_KEEP_M (the
    verge the drive gates read), smoothstep to 1 at NEAR_LOOP_M, so the freeway's batter meets the kept verge in a
    slope, never a step at the keep line"""
    t = max(0.0, min(1.0, (hd - HELD_KEEP_M) / (NEAR_LOOP_M - HELD_KEEP_M)))
    return t * t * (3.0 - 2.0 * t)


def _seg_x(a, b, c, d):
    """(t, u) where segment a->b meets segment c->d in plan (proper crossing, both strictly inside), else None"""
    r = (b[0] - a[0], b[1] - a[1])
    s = (d[0] - c[0], d[1] - c[1])
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-12:
        return None
    qp = (c[0] - a[0], c[1] - a[1])
    t = (qp[0] * s[1] - qp[1] * s[0]) / den
    u = (qp[0] * r[1] - qp[1] * r[0]) / den
    if 1e-6 < t < 1 - 1e-6 and -1e-9 <= u <= 1 + 1e-9:
        return t, u
    return None


def conform_ground(terr_objs, segs, slab_bvh, lift, slab_v=None, slab_f=None, loop_bvh=None, held=None):
    """cut every outline segment [(p, q, line_id)] into each terrain tile (split crossing edges, join each face's two
    crossing points) and set every vertex on or inside the outline lift under the slab. Returns stats."""
    cell = 10.0
    grid = {}
    for k, (p, q, _lid) in enumerate(segs):
        for gx in range(int(math.floor(min(p[0], q[0]) / cell)), int(math.floor(max(p[0], q[0]) / cell)) + 1):
            for gy in range(int(math.floor(min(p[1], q[1]) / cell)), int(math.floor(max(p[1], q[1]) / cell)) + 1):
                grid.setdefault((gx, gy), []).append(k)
    stats = {"edges_split": 0, "outline_edges_joined": 0, "vertices_set": 0, "max_down_m": 0.0, "max_up_m": 0.0,
             "tiles": {}}

    def slab_z(x, y):
        h = slab_bvh.ray_cast(Vector((x, y, 5000.0)), Vector((0, 0, -1)), 10000.0)
        return h[0].z if h[0] is not None else None

    flat = BVHTree.FromPolygons([(p[0], p[1], 0.0) for p in slab_v], slab_f) if slab_v else None
    stats["batter"] = {"m_per_m": BATTER, "reach_m": BATTER_REACH_M, "cut": 0, "fill": 0, "max_move_m": 0.0}

    def edge_z(x, y):
        """(plan distance to the slab's outline, the ground height at that outline point) within BATTER_REACH_M"""
        q, _n, fi, d = flat.find_nearest((x, y, 0.0), BATTER_REACH_M)
        if q is None:
            return None
        f = slab_f[fi]
        cx = sum(slab_v[i][0] for i in f) / len(f)
        cy = sum(slab_v[i][1] for i in f) / len(f)
        L = math.hypot(cx - q.x, cy - q.y) or 1.0
        z = slab_z(q.x + (cx - q.x) / L * 0.01, q.y + (cy - q.y) / L * 0.01)
        return None if z is None else (d, z - lift)

    for ob in terr_objs:
        mw = ob.matrix_world
        if any(abs(mw[i][j] - (1.0 if i == j else 0.0)) > 1e-6 for i in range(4) for j in range(4)):
            raise SystemExit(f"[freeway] FATAL: terrain tile {ob.name} has a non-identity transform")
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        n0 = len(bm.verts)
        on_line = {}                                   # BMVert -> outline line id
        far_tile = ob.name.upper().startswith("GRASS_FAR")
        # the far ring is never cut: a vertex the cut makes on a far slope has no 3DEP read of its own, and criterion 6
        # holds every far vertex within 1 m of 3DEP (a cut vertex on the I-8's steep far-east walls read 1.9 m off)
        for _round in range(0 if far_tile else 6):
            todo = []
            for e in bm.edges:
                a, b = e.verts[0].co, e.verts[1].co
                ks = set()
                for gx in range(int(math.floor(min(a.x, b.x) / cell)), int(math.floor(max(a.x, b.x) / cell)) + 1):
                    for gy in range(int(math.floor(min(a.y, b.y) / cell)), int(math.floor(max(a.y, b.y) / cell)) + 1):
                        ks.update(grid.get((gx, gy), ()))
                best = None
                L = math.hypot(b.x - a.x, b.y - a.y)
                ends = {on_line.get(e.verts[0]), on_line.get(e.verts[1])}
                for k in ks:
                    p, q, lid = segs[k]
                    if lid in ends:
                        continue                       # this edge already ends on that outline line
                    hit = _seg_x((a.x, a.y), (b.x, b.y), p, q)
                    # coordinates are float32 (~0.1 mm at 2 km): a crossing within SPLIT_MIN_M of an end is that end
                    if hit is not None and SPLIT_MIN_M < hit[0] * L < L - SPLIT_MIN_M                             and (best is None or hit[0] < best[0]):
                        best = (hit[0], lid, k)
                if best is not None:
                    todo.append((e, best[0], best[1], best[2]))
            if not todo:
                break
            for e, t, lid, k in todo:
                if not e.is_valid:
                    continue
                va, vb = e.verts[0], e.verts[1]
                at = va.co.copy().lerp(vb.co, t)          # placed explicitly: edge_split's fac direction is not ours
                _ne, nv = bmesh.utils.edge_split(e, va, t)
                nv.co = at
                on_line[nv] = lid
                stats["edges_split"] += 1
        # join the crossing points of the same outline line in each face, so the outline is an edge of the terrain
        for _round in range(4):
            pairs = []
            for f in bm.faces:
                mk = [v for v in f.verts if v in on_line]
                if len(mk) < 2:
                    continue
                by = {}
                for v in mk:
                    by.setdefault(on_line[v], []).append(v)
                for lid, vs in by.items():
                    if len(vs) == 2 and not any(vs[1] in (e.other_vert(vs[0]),) for e in vs[0].link_edges):
                        pairs.append((f, vs[0], vs[1]))
                        break
            if not pairs:
                break
            done_f = set()
            for f, v1, v2 in pairs:
                if f in done_f or not f.is_valid or not v1.is_valid or not v2.is_valid:
                    continue
                done_f.add(f)
                try:
                    bmesh.utils.face_split(f, v1, v2)
                    stats["outline_edges_joined"] += 1
                except ValueError:
                    pass
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3], quad_method="BEAUTY",
                              ngon_method="BEAUTY")
        # the ground on and inside the outline: lift under the slab
        for v in bm.verts:
            hd = held(v.co.x, v.co.y) if held is not None else None
            if hd is not None and hd < HELD_KEEP_M:
                continue                               # the loop's own verge: never moved
            z = slab_z(v.co.x, v.co.y)
            if z is None:
                if far_tile:
                    continue                           # the far ring is the data (criterion 6): no batter there
                # beside the outline: the ground rises or falls from the pavement's edge no steeper than the batter
                # (the 5 m lattice's vertex just past the shoulder carries a wall 4-8 m further out, filtered: a
                # vertical earth step at the shoulder that 3DEP does not have)
                ez = edge_z(v.co.x, v.co.y) if flat is not None else None
                if ez is None:
                    continue
                if loop_bvh is not None and loop_bvh.ray_cast(Vector((v.co.x, v.co.y, v.co.z + 200.0)),
                                                              Vector((0, 0, -1)), 400.0)[0] is not None:
                    continue                           # the loop's own pavement's ground is the drive gates'
                d, e = ez
                nz = max(e - BATTER * d, min(e + BATTER * d, v.co.z))
                if hd is not None:
                    nz = v.co.z + _held_w(hd) * (nz - v.co.z)
                if hd is not None and abs(nz - v.co.z) > 1e-5:
                    # held ground (criterion 7's band, 10-20 m from the loop's pavement) takes the freeway's batter both
                    # ways: the graded verge of a road beside the I-8 stood 3.5 m under the real fill slope of the
                    # freeway's embankment at its edge, and 7.5 m over the real cut of a road above it
                    stats["held_batter"] = stats.get("held_batter", 0) + 1
                    stats["held_batter_max_m"] = round(max(stats.get("held_batter_max_m", 0.0), abs(v.co.z - nz)), 3)
                    stats["held_batter_min_road_m"] = round(min(stats.get("held_batter_min_road_m", 99.0), hd), 2)
                if abs(nz - v.co.z) > 1e-5:
                    b = stats["batter"]
                    b["cut" if nz < v.co.z else "fill"] += 1
                    b["max_move_m"] = round(max(b["max_move_m"], abs(nz - v.co.z)), 3)
                    v.co.z = nz
                continue
            nz = z - lift
            dz = nz - v.co.z
            if far_tile and (dz > 0 or -dz > FAR_CUT_MAX):
                # the far ring is the data (criterion 6: every far vertex within 1 m of 3DEP, and its own 3DEP bound
                # is 0.85 m): a vertex under the slab is only ever lowered, by at most FAR_CUT_MAX; where the ground
                # still stands over the slab, the slab rises over it there (RAISE_MAX_FAR) or that face is left out
                stats["far_kept"] = stats.get("far_kept", 0) + 1
                continue
            if hd is not None:
                if dz >= 0:
                    continue                           # under the slab held ground is cut in full (the pavement covers it)
                stats["held_cut"] = stats.get("held_cut", 0) + 1
                stats["held_cut_max_m"] = round(max(stats.get("held_cut_max_m", 0.0), -dz), 3)
                stats["held_cut_min_road_m"] = round(min(stats.get("held_cut_min_road_m", 99.0), hd), 2)
            if abs(dz) > 1e-5:
                if -dz > stats["max_down_m"]:
                    stats["max_down_at"] = [round(v.co.x, 1), round(v.co.y, 1)]
                if dz > stats["max_up_m"]:
                    stats["max_up_at"] = [round(v.co.x, 1), round(v.co.y, 1)]
                stats["max_down_m"] = round(max(stats["max_down_m"], -dz), 3)
                stats["max_up_m"] = round(max(stats["max_up_m"], dz), 3)
                big = stats.setdefault("moves_over_1m", 0)
                stats["moves_over_1m"] = big + (abs(dz) > 1.0)
                v.co.z = nz
                stats["vertices_set"] += 1
        bm.to_mesh(ob.data)
        n1 = len(bm.verts)
        bm.free()
        ob.data.update()
        stats["tiles"][ob.name] = [n0, n1]
    return stats


def split_oversize(objs, cap):
    """a terrain tile over ``cap`` vertices after the outline cut is halved (faces by centroid about the median of its
    longer axis, the prep's balanced bisection) into <prefix>_<next free index>, materials and UVs kept; repeated
    until every tile fits. Returns {new name: vertices}."""
    made = {}
    todo = list(objs)
    while todo:
        ob = todo.pop()
        me = ob.data
        if len(me.vertices) <= cap:
            continue
        cs = [p.center for p in me.polygons]
        xs = sorted(c.x for c in cs)
        ys = sorted(c.y for c in cs)
        ax = 0 if xs[-1] - xs[0] >= ys[-1] - ys[0] else 1
        med = (xs if ax == 0 else ys)[len(cs) // 2]
        prefix = ob.name.rsplit("_", 1)[0]
        k = 0
        while bpy.data.objects.get(f"{prefix}_{k}") is not None:
            k += 1
        twin = ob.copy()
        twin.data = me.copy()
        twin.name = f"{prefix}_{k}"
        twin.data.name = twin.name
        for coll in ob.users_collection:
            coll.objects.link(twin)
        for target, keep_low in ((ob, True), (twin, False)):
            bm = bmesh.new()
            bm.from_mesh(target.data)
            gone = [f for f in bm.faces if (f.calc_center_median()[ax] <= med) != keep_low]
            bmesh.ops.delete(bm, geom=gone, context="FACES")
            loose = [v for v in bm.verts if not v.link_faces]
            if loose:
                bmesh.ops.delete(bm, geom=loose, context="VERTS")
            bm.to_mesh(target.data)
            bm.free()
            target.data.update()
        made[ob.name] = len(ob.data.vertices)
        made[twin.name] = len(twin.data.vertices)
        todo += [ob, twin]
    return made


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    eng = Path(argv[argv.index("--eng") + 1]) if "--eng" in argv else None
    data = proj / "data"
    fp = data / "freeway_i8.json"
    if not fp.exists():
        print("[freeway] no data/freeway_i8.json (scenery.freeway off) — nothing to do")
        return
    if eng is None:
        raise SystemExit("[freeway] --eng <engine-july> is required (materials bind through its pbr)")
    FW = _fw()
    F = json.loads(fp.read_text(encoding="utf-8"))
    P = F["params"]
    lift, lw = float(P["lift_m"]), float(P["line_w_m"])
    dash, period = float(P["dash_m"]), float(P["dash_period_m"])
    if any(st is not None and "h" not in st for ch in F["chains"] for st in ch):
        raise SystemExit("[freeway] data/freeway_i8.json has no slab heights (re-run tools/freeway_i8.py)")
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    blend = proj / "blender" / f"{cfg['slug']}.blend"
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    for ob in list(bpy.data.objects):
        if ob.name.upper().startswith(("HIGHWAY_I8", "MARKINGS_I8", "YLINE_I8", "BARRIER_I8")):
            bpy.data.objects.remove(ob, do_unlink=True)
    terr = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith(("1GRASS", "GRASS_FAR"))]
    roads = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith("1ROAD")]
    decks = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith(("1ROAD", "1KERB"))]
    structs = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith(("1ROAD", "1KERB",
                                                                                              "BRIDGESTRUCT"))]
    ground = _bvh(terr)
    deckb = _bvh(decks)
    structb = _bvh(structs)
    if ground is None or deckb is None:
        raise SystemExit("[freeway] the prepped scene has no 1GRASS/GRASS_FAR ground or no 1ROAD")
    rv = [o.matrix_world @ v.co for o in roads for v in o.data.vertices]
    box = (min(v.x for v in rv), max(v.x for v in rv), min(v.y for v in rv), max(v.y for v in rv))

    def near(x, y):
        return box[0] <= x <= box[1] and box[2] <= y <= box[3]

    def gz(x, y, bvh=None):
        h = (bvh or ground).ray_cast(Vector((x, y, 3000.0)), Vector((0, 0, -1)), 6000.0)
        return h[0].z if h[0] is not None else None

    def blocked(x, y, z, up):
        """a loop structure from DECK_UNDER under z to ``up`` over it"""
        return structb.ray_cast(Vector((x, y, z - DECK_UNDER)), Vector((0, 0, 1)), DECK_UNDER + up)[0] is not None

    # 1. the runs of stations that are laid: on the ground's extent, clear of every loop structure
    n_sta = n_skip = n_deck = 0
    runs_all = []
    for ch in F["chains"]:
        runs, cur = [], []
        for st in ch + [None]:
            ok = st is not None
            if ok:
                offs = sorted({-st["wr"], st["wl"], *st["edge"], *st["dash"]})
                offs = [o for o in offs if -st["wr"] - 1e-6 <= o <= st["wl"] + 1e-6]
                nx, ny = -st["tz"], st["tx"]
                cs = [(st["x"] + nx * o, st["z"] + ny * o) for o in offs]
                hs = [FW.height_at(st, o) for o in offs]
                if any(gz(x, y) is None for x, y in cs):
                    ok = False
                    n_skip += 1
                elif any(blocked(x, y, h + lift, DECK_CLEAR) for (x, y), h in zip(cs, hs)):
                    ok = False
                    n_deck += 1
            if ok and cur and (len(offs) != len(cur[-1]["offs"]) or near(st["x"], st["z"]) != cur[-1]["near"]
                               or st["lanes"] != cur[-1]["st"]["lanes"]):
                runs.append(cur)
                # the next strip starts ON the last station (no 4 m gap where the lane count changes): that station's
                # frame and slab, read at the new strip's offsets (a short taper over one 4 m step)
                pv = cur[-1]["st"]
                pnx, pny = -pv["tz"], pv["tx"]
                pcs = [(pv["x"] + pnx * o, pv["z"] + pny * o) for o in offs]
                phs = [FW.height_at(pv, o) for o in offs]
                if all(gz(x, y) is not None for x, y in pcs) and not any(
                        blocked(x, y, h + lift, DECK_CLEAR) for (x, y), h in zip(pcs, phs)):
                    cur = [{"st": pv, "offs": offs, "cs": pcs, "hs": phs, "near": cur[-1]["near"]}]
                else:
                    cur = []
            if not ok:
                if cur:
                    runs.append(cur)
                cur = []
                continue
            n_sta += 1
            cur.append({"st": st, "offs": offs, "cs": cs, "hs": hs, "near": near(st["x"], st["z"])})
        runs_all += [r for r in runs if len(r) >= 2]

    # 2. the slab (in memory first: the ground conform reads it)
    pave = {"NEAR": [Mesh()], "FAR": [Mesh()]}
    built = []
    for run in runs_all:
        kind = "NEAR" if run[-1]["near"] else "FAR"
        M = pave[kind][-1]
        if len(M.v) + len(run) * len(run[0]["offs"]) > VERT_CAP:
            pave[kind].append(Mesh())
            M = pave[kind][-1]
        rows = [[M.add((x, y, h + lift)) for (x, y), h in zip(r["cs"], r["hs"])] for r in run]
        for ra, rb in zip(rows, rows[1:]):
            for k in range(len(ra) - 1):
                M.f.append((ra[k], ra[k + 1], rb[k + 1], rb[k]))
        built.append((kind, M, run, rows))

    # 3. the ground meets the slab: the outline (each run's two edges and two ends) cut into the terrain; inside it,
    # the ground is lift under the slab. The conform reads a copy of the slab OUTLINE_PAD wider (the split points lie
    # on the outline to float precision)
    cv, cf, segs = [], [], []
    for kind, M, run, rows in built:
        base = len(cv)
        for ri, r in enumerate(run):
            st = r["st"]
            nx, ny = -st["tz"], st["tx"]
            # the end rows reach OUTLINE_PAD past the run's ends too
            ex = -OUTLINE_PAD if ri == 0 else (OUTLINE_PAD if ri == len(run) - 1 else 0.0)
            tx, ty = st["tx"] * ex, st["tz"] * ex
            o, cs, hs = r["offs"], r["cs"], r["hs"]
            gr0 = (hs[1] - hs[0]) / max(1e-6, o[1] - o[0])
            gr1 = (hs[-1] - hs[-2]) / max(1e-6, o[-1] - o[-2])
            cv.append((cs[0][0] - nx * OUTLINE_PAD + tx, cs[0][1] - ny * OUTLINE_PAD + ty, hs[0] - gr0 * OUTLINE_PAD + lift))
            for (x, y), h in zip(cs, hs):
                cv.append((x + tx, y + ty, h + lift))
            cv.append((cs[-1][0] + nx * OUTLINE_PAD + tx, cs[-1][1] + ny * OUTLINE_PAD + ty,
                       hs[-1] + gr1 * OUTLINE_PAD + lift))
        w = len(run[0]["offs"]) + 2
        for i in range(len(run) - 1):
            for k in range(w - 1):
                a = base + i * w + k
                cf.append((a, a + 1, a + w + 1, a + w))
        # the outline: right and left edges along the run, and the two end caps
        rr = [(r["cs"][0], r["cs"][-1]) for r in run]
        for i in range(len(run) - 1):
            segs.append((rr[i][0], rr[i + 1][0], ("R", id(run))))
            segs.append((rr[i][1], rr[i + 1][1], ("L", id(run))))
        segs.append((rr[0][0], rr[0][1], ("S", id(run))))
        segs.append((rr[-1][0], rr[-1][1], ("E", id(run))))
    slab_bvh = BVHTree.FromPolygons(cv, cf)
    # criterion 7: the ground within NEAR_LOOP_M of the loop's pavement is the drive gates' (v0.17.1), except inside a
    # declared release zone (tools/ground_release.py), where it is already the real earth
    lv = [tuple(o.matrix_world @ v.co) for o in decks for v in o.data.vertices]
    lf, base = [], 0
    for o in decks:
        lf += [tuple(base + i for i in p.vertices) for p in o.data.polygons]
        base += len(o.data.vertices)
    loop_flat = BVHTree.FromPolygons([(q[0], q[1], 0.0) for q in lv], lf)
    zones = None
    rp = data / "ground_release.json"
    if rp.exists():
        spec = importlib.util.spec_from_file_location("_airoso_ground_release", AIROSO / "tools" / "ground_release.py")
        GR = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(GR)
        R = json.loads(rp.read_text(encoding="utf-8"))
        cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
        zones = GR.Zones([tuple(q) for q in cl["points_xyz_m"]], cl["widths_m"], R["zones"])

    def held(x, y):
        """the plan distance to the loop's pavement where criterion 7 holds this ground (within NEAR_LOOP_M, outside
        every release zone), else None"""
        q = loop_flat.find_nearest((x, y, 0.0), NEAR_LOOP_M)
        if q[0] is None or (zones is not None and zones.contains(x, y)):
            return None
        return q[3]

    cstats = conform_ground(terr, segs, slab_bvh, lift, cv, cf, deckb, held)
    cstats["tiles_split"] = split_oversize(terr, VERT_CAP)
    terr = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith(("1GRASS", "GRASS_FAR"))]
    big = {o.name: len(o.data.vertices) for o in terr if len(o.data.vertices) > TILE_CAP}
    if big:
        raise SystemExit(f"[freeway] FATAL: terrain tiles over {TILE_CAP} vertices after the split {big}")
    ground = _bvh(terr)

    # 4. lines on the slab: dashed lane lines; solid edge lines (white outside, yellow on the median side)
    lines = {"MARKINGS": [Mesh()], "YLINE": [Mesh()]}
    for kind, M, run, rows in built:
        if kind != "NEAR":
            continue
        st0 = run[-1]["st"]           # the strip's own station (its first may be the previous strip's last)
        for li, o in enumerate(run[0]["offs"]):
            is_dash = any(abs(o - d) < 1e-6 for d in st0["dash"])
            is_edge = any(abs(o - e) < 1e-6 for e in st0["edge"])
            if not (is_dash or is_edge):
                continue
            med = is_edge and (o > 0) == (st0["median_side"] > 0)
            key = "YLINE" if med else "MARKINGS"
            if len(lines[key][-1].v) > VERT_CAP - 4 * len(run):
                lines[key].append(Mesh())
            L = lines[key][-1]
            acc = 0.0
            for ra, rb in zip(rows, rows[1:]):
                pa, pb = M.v[ra[li]], M.v[rb[li]]
                ax, ay, bx, by = pa[0], pa[1], pb[0], pb[1]
                seg = math.hypot(bx - ax, by - ay) or 1e-9
                t0, t1 = acc, acc + seg
                acc = t1
                if is_dash:
                    k = math.floor(t0 / period)
                    a = max(t0, k * period)
                    b = min(t1, k * period + dash)
                    if b <= a:
                        continue
                    u0, u1 = (a - t0) / seg, (b - t0) / seg
                else:
                    u0, u1 = 0.0, 1.0
                ha, hb = pa[2] + LINE_LIFT, pb[2] + LINE_LIFT
                nx, ny = -(by - ay) / seg, (bx - ax) / seg
                p0 = (ax + (bx - ax) * u0, ay + (by - ay) * u0, ha + (hb - ha) * u0)
                p1 = (ax + (bx - ax) * u1, ay + (by - ay) * u1, ha + (hb - ha) * u1)
                q = [L.add((p0[0] - nx * lw / 2, p0[1] - ny * lw / 2, p0[2])),
                     L.add((p0[0] + nx * lw / 2, p0[1] + ny * lw / 2, p0[2])),
                     L.add((p1[0] + nx * lw / 2, p1[1] + ny * lw / 2, p1[2])),
                     L.add((p1[0] - nx * lw / 2, p1[1] - ny * lw / 2, p1[2]))]
                L.f.append(tuple(q))

    # 5. the median barrier: on the ground between the carriageways (after the conform), clear of every loop structure
    bars = [Mesh()]
    prof = [(-BAR_BASE / 2, -BAR_SINK), (-BAR_BASE / 2, 0.0), (-BAR_TOP / 2, BAR_H), (BAR_TOP / 2, BAR_H),
            (BAR_BASE / 2, 0.0), (BAR_BASE / 2, -BAR_SINK)]
    n_bar = n_bar_deck = 0
    for line in F["barrier"]:
        rings = []
        for k, (x, y) in enumerate(line):
            a = line[max(0, k - 1)]
            b = line[min(len(line) - 1, k + 1)]
            L2 = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            nx, ny = -(b[1] - a[1]) / L2, (b[0] - a[0]) / L2
            h = gz(x, y)
            if h is None or blocked(x, y, h + lift, DECK_CLEAR + BAR_H):
                n_bar_deck += h is not None
                rings.append(None)
                continue
            M = bars[-1]
            rings.append([M.add((x + nx * o, y + ny * o, h + lift + dz)) for o, dz in prof])
        M = bars[-1]
        for ra, rb in zip(rings, rings[1:]):
            if ra is None or rb is None:
                continue
            for k in range(len(prof) - 1):
                M.f.append((ra[k], ra[k + 1], rb[k + 1], rb[k]))
            n_bar += 1
        if len(M.v) > VERT_CAP - 5000:
            bars.append(Mesh())

    # 6. self-checks: the slab clear of the (conformed) ground; nothing of the freeway on, over or just under a deck
    def gnear(x, y, z):
        """the ground under (x, y) read from GROUND_WIN over z down (never a grass layer on a deck far above)"""
        h = ground.ray_cast(Vector((x, y, z + GROUND_WIN)), Vector((0, 0, -1)), GROUND_WIN + 200.0)
        return h[0].z if h[0] is not None else None

    def short(M, f):
        ps = [Vector(M.v[i]) for i in f]
        tests = ps + [(ps[i] + ps[(i + 1) % len(ps)]) / 2 for i in range(len(ps))] + [sum(ps, Vector()) / len(ps)]
        worst = 0.0
        for t in tests:
            g = gnear(t.x, t.y, t.z)
            if g is not None and t.z < g + MIN_CLEAR:
                worst = max(worst, g + MIN_CLEAR - t.z)
        return worst

    # where the outline cut could not follow the slab exactly (an outline corner inside a terrain face, a split that
    # landed on an existing vertex) a face may still be a few cm short: its corners rise by the shortfall, up to
    # RAISE_MAX; a face still short after that is left out (counted)
    n_raised = 0
    n_dropped = 0
    for kind, Ms in pave.items():
        for M in Ms:
            for _round in range(4):
                bump = {}
                for f in M.f:
                    need = short(M, f)
                    if need > 0:
                        for i in f:
                            bump[i] = max(bump.get(i, 0.0), need + 0.002)
                if not bump:
                    break
                for i, dz in bump.items():
                    if dz <= (RAISE_MAX_FAR if kind == "FAR" else RAISE_MAX):
                        M.v[i][2] += dz
                        n_raised += 1
            keep = [f for f in M.f if short(M, f) <= 0]
            n_dropped += len(M.f) - len(keep)
            M.f = keep
    low = []
    for kind, Ms in pave.items():
        for M in Ms:
            for f in M.f:
                s = short(M, f)
                if s > 0:
                    low.append((round(M.v[f[0]][0], 1), round(M.v[f[0]][1], 1), round(s, 3)))
    over_deck, under_deck = [], []
    for Ms in list(pave.values()) + list(lines.values()) + [bars]:
        for M in Ms:
            used = sorted({i for f in M.f for i in f})
            for i in used:
                v = M.v[i]
                if deckb.ray_cast(Vector((v[0], v[1], v[2] + 0.01)), Vector((0, 0, -1)), 5.0)[0] is not None:
                    over_deck.append((round(v[0], 1), round(v[1], 1)))
                if deckb.ray_cast(Vector((v[0], v[1], v[2] - 0.01)), Vector((0, 0, 1)), DECK_CLEAR - lift)[0] is not None:
                    under_deck.append((round(v[0], 1), round(v[1], 1)))
    if low or over_deck or under_deck:
        raise SystemExit(f"[freeway] FATAL: {len(low)} pavement faces under the ground + {MIN_CLEAR} m {low[:4]}; "
                         f"{len(over_deck)} freeway vertices over a loop deck {over_deck[:4]}; {len(under_deck)} within "
                         f"{DECK_CLEAR - lift} m under one {under_deck[:4]} — scene NOT saved")
    spec = importlib.util.spec_from_file_location("_eng_pbr_freeway", eng / "scripts" / "ac" / "pbr.py")
    pbr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pbr)
    overrides = pbr.load_overrides(proj)
    made = {}
    for prefix, Ms in (("HIGHWAY_I8_NEAR", pave["NEAR"]), ("HIGHWAY_I8_FAR", pave["FAR"]),
                       ("MARKINGS_I8", lines["MARKINGS"]), ("YLINE_I8", lines["YLINE"]), ("BARRIER_I8", bars)):
        k = 0
        for M in Ms:
            if not M.f:
                continue
            if len(M.v) > 65535:
                raise SystemExit(f"[freeway] FATAL: {prefix}_{k} has {len(M.v)} vertices (> 65,535)")
            ob = _ob(f"{prefix}_{k}", M)
            pbr.setup_material(bpy, ob, overrides=overrides)
            made[ob.name] = len(M.v)
            k += 1
    try:
        bpy.ops.file.pack_all()
    except Exception as e:  # noqa: BLE001
        print(f"[freeway] pack_all warning: {e}")
    bpy.ops.wm.save_mainfile(filepath=str(blend))
    rep = {"_doc": "tools/author_freeway_blend.py (ledger 0046 v0.18.0 integration fix round 2)", "stations": n_sta,
           "stations_off_the_ground": n_skip, "stations_under_a_loop_structure": n_deck, "strips": len(built),
           "slab_vertices_raised": n_raised, "slab_faces_left_out": n_dropped, "barrier_segments": n_bar, "barrier_stations_under_a_loop_structure": n_bar_deck,
           "ground_conform": cstats, "objects": made, "road_extent_xy": [round(b, 1) for b in box], "lift_m": lift,
           "deck_clear_m": DECK_CLEAR}
    (data / "freeway_i8.report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"[freeway] I-8: {n_sta} stations laid at the 3DEP freeway height ({n_skip} off the ground, {n_deck} under or "
          f"on a loop structure, left out) in {len(built)} strips; ground conform: {cstats['edges_split']} terrain edges "
          f"split on the outline, {cstats['outline_edges_joined']} joined, {cstats['vertices_set']} vertices set under "
          f"the slab (down <= {cstats['max_down_m']} m, up <= {cstats['max_up_m']} m), tiles {cstats['tiles']} split "
          f"{cstats['tiles_split']}; slab {n_raised} vertices raised <= {RAISE_MAX} m, {n_dropped} faces left out; barrier "
          f"{n_bar} segments ({n_bar_deck} stations under a loop structure); objects {made}; saved {blend.name}")


main()
