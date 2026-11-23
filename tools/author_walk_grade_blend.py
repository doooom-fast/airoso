"""The street sidewalk's back grade at a slope a car can leave the road over (ledger 0099 round 1c, "the street drops").

The draft sweeps one curb + walk per road side (tracks/san-diego-lake-murray/scripts-v021/geometry/ribbon.py curb_sidewalk,
Lake Murray's EDGE_DEFAULTS): from the lane edge (0.10 over the centre line) a 0.08 m batter up 0.14 m to the curb top,
the walk flat for 1.8 m, then a BACK GRADE 1.2 m wide down to 0.10 m under the centre line, so the strip's outer lip
lands under the grass. That grade falls 0.34 m over 1.2 m (28 %, 0.142 m per 0.5 m), and the excursion sweep of
scripts/geometry/drive_test.py reads every 0.5 m step of it as a drop of more than 0.12 m (a tall curb, the most a car
survives at speed). On Lake Murray's Free Roam lap that is 94 of the 96 gated drops 0.20.2 was forced past: 66 with both
samples on the grade (0.142 m each), 28 from the grade onto the grass the prep pins just under it (0.126-0.141 m).

This author step (opt-in: track.config.json route.walk_back_grade; absent = nothing runs, no blend is saved) raises every
back-grade lip of the named strips (default the draft's CURB) so that no edge from it up to the walk's back edge is
steeper than max_slope: new lip = max(lip, walk back - max_slope * horizontal run), per vertex, over every such edge.
Nothing else moves: the curb, the walk, the strip's plan footprint and every other object stay where the draft put them.
At Lake Murray's 0.20 the grade falls 0.24 m over its 1.2 m (0.10 m per 0.5 m sample) and the lip lies at the centre
line's height, 0.10 m under the lane edge and 0.08 m under the ground the prep pins beside the road (build_kn5_loop
GROUND_CLEAR 0.02); the prep's anti-poke then holds the grass under the raised grade as it held it under the old one.

A lip is a strip vertex with an edge to a walk-back vertex DH_MIN..DH_MAX away in plan and DZ_MIN..DZ_MAX above it (the
draft's 1.2 m / 0.34 m, the mouth weld's warp, and an already raised lip, so a second run finds the same set). Held
(counted, never lowered):
  * a lip in a ground-release zone (data/ground_release.json, the near-road ground the draft released to the 3DEP bare
    earth, which the prep leaves unpinned): it is raised at most to GROUND_UNDER_M under that ground in loop.blend, so the
    strip's outer edge never stands over the real earth (where the earth behind the walk is low, the walk falls to it);
  * a lip with pavement (ROAD / 1ROAD*) over or under it within PAVE_WIN_M: it is raised at most to PAVE_UNDER_M under the
    lowest such pavement (a mouth's other street, a pad), so no strip pokes through a carriageway (audit K / I);
  * a lip of a face that furniture stands on (any 1WALL* / GUARDRAIL vertex over it in plan: a stub's K-rail laid back of
    walk to back of walk, a deck rail): the furniture keeps the seat the draft gave it (verify_stubs S5, verify_pads).
    The lamp posts on the grade (hw + 2.8 m) are not held: their poles are planted 3 m into the ground by design.
  * a lip the red repairs plan names (data/red_repairs.plan.json K / I / F, matched within RED_MATCH_M): the prep deletes
    those faces by position, so they must be where the plan saw them.

Self-checks (exit 1, loop.blend NOT saved): lips found in every named object; no vertex lowered; no vertex but a lip
moved; no move over MOVE_MAX_M; read back, every lip edge of a raised lip no steeper than max_slope.

Writes data/walk_grade.json (counts, the falls before and after, every held lip) and saves loop.blend. Idempotent: a
second run finds the same lips already at the grade and moves nothing. Not opted in: a stale report is removed.

THE SEAT (--seat, a prep sub-step on the PREPPED scene, after the red repairs; ledger 0099 round 1c). The prep pins the
ground beside the road to the deck (build_kn5_loop: within BAND_M 3 m of a pavement vertex, then a 6 m feather to the
natural ground) and the strip's lip lies 3.08 m out, on the feather's first metre; where the natural ground falls away (a
fill) the ground the prep leaves under a raised lip can lie below it, and the strip's outer edge would stand in the air
(the Mac rehearsal: 645 lips over 0.05 m against the draft's 497, where the ground beyond the walk falls away). The ground is only final
after the prep, so this half reads it there: every 1KERB_sidewalk* lip standing over GROUND_UNDER_M under the 1GRASS*
ground beneath it is lowered to that height, never below the draft's own back grade (DRAFT_SLOPE: 0.34 m over 1.2 m) and
never raised. There the walk falls to the real fill as the draft's did, and the drive test reads it. Self-checked (exit 1,
blend not saved): only lips move, only down, never past the draft's grade. Writes data/walk_grade.seat.json.

    blender --background --python-exit-code 1 --python tools/author_walk_grade_blend.py -- <project-dir>
    blender --background --python-exit-code 1 --python tools/author_walk_grade_blend.py -- <prepped.blend> --project <dir> --seat
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

DH_MIN, DH_MAX = 1.0, 1.45    # the draft's grade_w 1.2 m, +- the mouth weld's mitre and warp (measured: 98 % at 1.20-1.21)
DZ_MIN, DZ_MAX = 0.10, 0.45   # its fall 0.34 m (lift 0.10 + curb_h 0.14 + grass_clearance 0.10), down to a lip already raised
SLOPE_MIN = DZ_MIN / DH_MIN   # a gentler max_slope would raise lips past where a second run finds them
SLOPE_MAX = 0.24              # scripts/geometry/drive_test.py: a fall over 0.12 m between its 0.5 m excursion samples is a drop
WALK_DH_MIN, WALK_DH_MAX = 1.3, 2.4   # the walk across, curb top to walk back: 1.8 m mainline, 1.5 m connectors (+ diagonals)
WALK_DZ_M = 0.06              # [invented] ...level (the walk is flat across; the bank and the weld tilt it a little)
CURB_DH_M, CURB_DZ_M = 0.3, 0.08   # the curb face: 0.08 m out, 0.14 m up from the lane edge
PAVE_WIN_M = 1.0              # [invented] pavement this far above or below a lip is its own street at a mouth or a pad
PAVE_UNDER_M = 0.03           # [invented] a raised lip stays this far under that pavement
GROUND_UNDER_M = 0.03         # [invented] ...and this far under the released ground (the prep's own clearance is 0.02)
FURN_REACH_M = 2.5            # [invented] a furniture vertex stands on the strip face this far under it (a 1.2 m K-rail + sink)
RED_MATCH_M = 0.05            # tools/red_repairs_blend.py finds its named vertices within 0.03 m; this holds a margin
MOVE_MAX_M = DZ_MAX           # a lip never rises more than the steepest grade it can be found on falls
DRAFT_SLOPE = 0.34 / 1.2      # the draft's back grade (EDGE_DEFAULTS lift + curb_h + grass_clearance over grade_w): the seat's floor
SEAT_PREFIX = "1KERB_SIDEWALK"   # the prepped scene's walks (CURB is 1KERB_sidewalk_<tile> after the prep's rename and split)
EPS_M = 1e-4                  # a vertex is stored in float32 (7.6e-6 m at 64 m): a smaller difference is no move
REPORT = "walk_grade.json"
SEAT_REPORT = "walk_grade.seat.json"


def spec(cfg: dict) -> dict | None:
    """route.walk_back_grade -> {"max_slope", "objects"}, or None when the track does not opt in"""
    w = (cfg.get("route") or {}).get("walk_back_grade")
    if not w:
        return None
    if not isinstance(w, dict):
        raise SystemExit("[walk-grade] route.walk_back_grade must be an object {\"max_slope\": rise per metre}")
    s = w.get("max_slope")
    if isinstance(s, bool) or not isinstance(s, (int, float)) or not SLOPE_MIN <= float(s) < SLOPE_MAX:
        raise SystemExit(f"[walk-grade] route.walk_back_grade.max_slope must be a number in [{SLOPE_MIN:.2f}, {SLOPE_MAX}): "
                         f"from {SLOPE_MAX} a 0.5 m step down the grade is drive_test's 0.12 m drop, under {SLOPE_MIN:.2f} a "
                         f"raised lip is no longer found as one (got {s!r})")
    objs = w.get("objects") or ["CURB"]
    if not isinstance(objs, list) or not all(isinstance(o, str) and o for o in objs):
        raise SystemExit("[walk-grade] route.walk_back_grade.objects must be a list of mesh names")
    return {"max_slope": float(s), "objects": list(objs)}


def _adjacency(co, edges):
    nb: dict[int, list[tuple[int, float, float]]] = {}
    for a, b in edges:
        dh = math.hypot(co[b][0] - co[a][0], co[b][1] - co[a][1])
        nb.setdefault(a, []).append((b, dh, co[b][2] - co[a][2]))
        nb.setdefault(b, []).append((a, dh, co[a][2] - co[b][2]))
    return nb


def lip_edges(co, edges):
    """{lip vertex: [(walk-back vertex, plan run, rise)]}. A lip has an edge DH_MIN..DH_MAX long in plan up DZ_MIN..DZ_MAX
    to a WALK-BACK vertex: one with a level edge WALK_DH_MIN..WALK_DH_MAX long across the walk (the 1.8 m mainline / 1.5 m
    connector walk) to a CURB TOP (a vertex standing CURB_DZ_M or more over a neighbour under CURB_DH_M away in plan: the
    curb face). A lane-edge vertex (the curb face's foot) is never a lip, nor is a walk-back vertex.
    co: [(x, y, z)] (z up), edges: [(a, b)]"""
    nb = _adjacency(co, edges)
    curb_top = {v for v, ns in nb.items() if any(dh <= CURB_DH_M and dz <= -CURB_DZ_M for _, dh, dz in ns)}
    walk_back = {v for v, ns in nb.items()
                 if any(u in curb_top and WALK_DH_MIN <= dh <= WALK_DH_MAX and abs(dz) <= WALK_DZ_M for u, dh, dz in ns)}
    out: dict[int, list] = {}
    for v, ns in nb.items():
        if v in walk_back or v in curb_top or any(dh <= CURB_DH_M and dz >= CURB_DZ_M for _, dh, dz in ns):
            continue
        ups = [(u, dh, dz) for u, dh, dz in ns if DH_MIN <= dh <= DH_MAX and DZ_MIN <= dz <= DZ_MAX and u in walk_back]
        if ups:
            out[v] = ups
    return out


def target(z_lip: float, ups, co, max_slope: float) -> float:
    """the lip's height with every grade edge up from it no steeper than max_slope (never lower than it stands)"""
    t = max(co[h][2] - max_slope * dh for h, dh, _ in ups)
    return max(z_lip, t)


def plan(co, edges, max_slope: float, pave_at=None, red_xyz=(), ground_at=None, furnished=frozenset()):
    """the pure half: {lip: new z} plus the held lips. pave_at(x, y, z_lo, z_hi) -> pavement heights in that window;
    red_xyz: named red-repair vertices (x, y, z), z up; ground_at(x, y, z) -> the released ground's height under a lip in
    a release zone, else None; furnished: vertices of the faces furniture stands on"""
    lips = lip_edges(co, edges)
    red = {}
    for p in red_xyz:
        red.setdefault((int(math.floor(p[0])), int(math.floor(p[1]))), []).append(p)
    moves, held_pave, held_red, held_ground, held_furn, already, capped = {}, [], [], [], [], 0, set()
    for v, ups in lips.items():
        x, y, z = co[v]
        t = target(z, ups, co, max_slope)
        if t <= z + EPS_M:
            already += 1
            continue
        near_red = [p for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    for p in red.get((int(math.floor(x)) + dx, int(math.floor(y)) + dy), ())
                    if math.dist(p, (x, y, z)) <= RED_MATCH_M]
        if near_red:
            held_red.append([round(x, 3), round(y, 3), round(z, 3)])
            continue
        if v in furnished:
            held_furn.append([round(x, 3), round(y, 3), round(z, 3)])
            continue
        if ground_at is not None:
            g = ground_at(x, y, z)
            if g is not None and g - GROUND_UNDER_M < t:
                held_ground.append([round(x, 3), round(y, 3), round(z, 3), round(g, 3)])
                t = max(z, g - GROUND_UNDER_M)
                if t <= z + EPS_M:
                    continue
                capped.add(v)
        if pave_at is not None:
            pv = pave_at(x, y, z - PAVE_WIN_M, t + PAVE_WIN_M)
            if pv:
                cap = min(pv) - PAVE_UNDER_M
                if cap < t:
                    held_pave.append([round(x, 3), round(y, 3), round(z, 3), round(min(pv), 3)])
                    t = max(z, cap)
                    if t <= z + EPS_M:
                        continue
                    capped.add(v)
        moves[v] = t
    return {"lips": lips, "moves": moves, "held_pavement": held_pave, "held_red": held_red, "held_ground": held_ground,
            "held_furniture": held_furn, "already": already, "capped": capped}


def seat_plan(co, lips, ground_at, under=GROUND_UNDER_M, floor_slope=DRAFT_SLOPE):
    """the seat's pure half: {lip: new z} for every lip standing over ``under`` under the ground beneath it (ground_at(x, y,
    z) -> the ground's height there, or None), lowered to that height but never below the draft's grade (walk back -
    floor_slope * run, over its steepest edge) and never raised"""
    moves, at_floor = {}, 0
    for v, ups in lips.items():
        x, y, z = co[v]
        g = ground_at(x, y, z)
        if g is None or z <= g - under + EPS_M:
            continue
        floor = max(co[h][2] - floor_slope * dh for h, dh, _ in ups)
        t = max(g - under, floor)
        if t < z - EPS_M:
            moves[v] = t
            if t == floor:
                at_floor += 1
    return moves, at_floor


def _q(vals, f):
    s = sorted(vals)
    return round(s[min(len(s) - 1, int(f * len(s)))], 3) if s else None


def falls(co, lips, z_of=None):
    """the fall and the steepest slope over every lip's grade edges (z_of: the lip's height, default its co)"""
    fl, sl = [], []
    for v, ups in lips.items():
        z = co[v][2] if z_of is None else z_of(v)
        for h, dh, _ in ups:
            fl.append(co[h][2] - z)
            sl.append((co[h][2] - z) / dh)
    return {"fall_m": {"p50": _q(fl, 0.5), "max": _q(fl, 1.0)}, "slope": {"p50": _q(sl, 0.5), "max": _q(sl, 1.0)}}


FURNITURE = ("1WALL", "GUARDRAIL")   # what stands on a walk: the stubs' K-rails, the deck rails, the release rails


def furnished_vertices(bpy, ob, co):
    """the vertices of every face of ``ob`` some furniture vertex stands over in plan (a downward ray from 0.5 m over that
    vertex lands on the face within FURN_REACH_M): one BVH of the strip, one ray per furniture vertex"""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    polys = [list(p.vertices) for p in ob.data.polygons]
    bvh = BVHTree.FromPolygons([Vector(c) for c in co], polys)
    lo = [min(c[k] for c in co) for k in range(2)]
    hi = [max(c[k] for c in co) for k in range(2)]
    out = set()
    for f in bpy.data.objects:
        if f.type != "MESH" or not f.name.upper().startswith(FURNITURE):
            continue
        mw = f.matrix_world
        for v in f.data.vertices:
            w = mw @ v.co
            if not (lo[0] - 1 <= w.x <= hi[0] + 1 and lo[1] - 1 <= w.y <= hi[1] + 1):
                continue
            h = bvh.ray_cast(Vector((w.x, w.y, w.z + 0.5)), Vector((0.0, 0.0, -1.0)), FURN_REACH_M)
            if h[2] is not None:
                out.update(polys[h[2]])
    return out


def release_zones(proj: Path):
    """tools/ground_release.Zones over data/ground_release.json's zones on data/centerline.local.json (the membership the
    prep's ReleaseZones uses), or None (no file / no zone)"""
    p = proj / "data" / "ground_release.json"
    if not p.exists():
        return None
    R = json.loads(p.read_text(encoding="utf-8"))
    if not R.get("zones"):
        return None
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ground_release as gr
    local = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(q) for q in local["points_xyz_m"]]
    return gr.Zones(pts, local.get("widths_m") or [7.0] * len(pts), R["zones"])


def _red_points(proj: Path):
    p = proj / "data" / "red_repairs.plan.json"
    if not p.exists():
        return []
    r = json.loads(p.read_text(encoding="utf-8"))
    return [(row[0], row[2], row[1]) for k in ("K", "I", "F") for row in r.get(k) or []]   # engine (E, up, N) -> scene


def seat(blend: Path, proj: Path, sp: dict) -> int:
    """--seat on the prepped scene (see the module doc)"""
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    gv, gf = [], []
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.name.upper().startswith("1GRASS"):
            base = len(gv)
            gv += [ob.matrix_world @ v.co for v in ob.data.vertices]
            gf += [[base + i for i in p.vertices] for p in ob.data.polygons]
    if not gf:
        raise SystemExit("[walk-grade] --seat: no 1GRASS ground in the prepped scene")
    ground = BVHTree.FromPolygons(gv, gf)

    def ground_at(x, y, z):
        h = ground.ray_cast(Vector((x, y, z + 2.0)), Vector((0.0, 0.0, -1.0)), 4.0)
        return None if h[0] is None else h[0].z
    rep = {"_doc": "ledger 0099 round 1c: tools/author_walk_grade_blend.py --seat. On the prepped scene, every walk lip "
                   f"standing over {GROUND_UNDER_M} m under the ground beneath it lowered to that height, never below the "
                   "draft's back grade (DRAFT_SLOPE) and never raised", "objects": {}}
    total = 0
    for ob in [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith(SEAT_PREFIX)]:
        me = ob.data
        mw = ob.matrix_world
        co = [tuple(mw @ v.co) for v in me.vertices]
        lips = lip_edges(co, [tuple(e.vertices) for e in me.edges])
        if not lips:
            continue
        moves, at_floor = seat_plan(co, lips, ground_at)
        inv = mw.inverted()
        for v, z in moves.items():
            me.vertices[v].co = inv @ Vector((co[v][0], co[v][1], z))
        me.update()
        after = [tuple(mw @ v.co) for v in me.vertices]
        moved = [i for i in range(len(after)) if math.dist(after[i], co[i]) > 1e-6]
        if any(i not in moves for i in moved) or any(after[i][2] > co[i][2] + 1e-6 for i in moved):
            raise SystemExit(f"[walk-grade] --seat {ob.name}: a vertex that is not a lip moved, or a lip moved up")
        if any((after[h][2] - after[i][2]) / dh > DRAFT_SLOPE + 1e-4 and after[i][2] < co[i][2] - 1e-6
               for i in moved for h, dh, _ in lips[i]):
            raise SystemExit(f"[walk-grade] --seat {ob.name}: a lip lowered past the draft's back grade")
        drop = [co[i][2] - after[i][2] for i in moved]
        rep["objects"][ob.name] = {"lips": len(lips), "lowered": len(moves), "at_draft_grade": at_floor,
                                   "lowered_m": {"p50": _q(drop, 0.5), "max": _q(drop, 1.0)}}
        total += len(moves)
        print(f"[walk-grade] --seat {ob.name}: {len(lips)} lips, {len(moves)} lowered onto the ground (p50 "
              f"{_q(drop, 0.5)} max {_q(drop, 1.0)} m; {at_floor} of them at the draft's grade)")
    (proj / "data" / SEAT_REPORT).write_text(json.dumps(rep, indent=1), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print(f"[walk-grade] --seat: {total} lips lowered onto the prepped ground; wrote data/{SEAT_REPORT}; saved {blend}")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if argv is None and "--" in sys.argv else (argv or [])
    if "--seat" in argv:
        if len(argv) != 4 or argv[1] != "--project":
            raise SystemExit("usage: blender --background --python tools/author_walk_grade_blend.py -- <prepped.blend> "
                             "--project <project-dir> --seat")
        proj = Path(argv[2])
        sp = spec(json.loads((proj / "track.config.json").read_text(encoding="utf-8")))
        if sp is None:
            (proj / "data" / SEAT_REPORT).unlink(missing_ok=True)
            print("[walk-grade] --seat: route.walk_back_grade is not set: nothing to do")
            return 0
        return seat(Path(argv[0]), proj, sp)
    if len(argv) != 1:
        raise SystemExit("usage: blender --background --python tools/author_walk_grade_blend.py -- <project-dir>")
    proj = Path(argv[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    out = proj / "data" / REPORT
    sp = spec(cfg)
    if sp is None:
        if out.exists():
            out.unlink()
        print("[walk-grade] route.walk_back_grade is not set: nothing to do (the draft's back grade, as before)")
        return 0
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    blend = proj / "loop.blend"
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    pv, pf = [], []
    for ob in bpy.data.objects:
        if ob.type == "MESH" and (ob.name == "ROAD" or ob.name.upper().startswith("1ROAD")):
            base = len(pv)
            pv += [ob.matrix_world @ v.co for v in ob.data.vertices]
            pf += [[base + i for i in p.vertices] for p in ob.data.polygons]
    road = BVHTree.FromPolygons(pv, pf) if pf else None
    gv, gf = [], []
    for ob in bpy.data.objects:
        if ob.type == "MESH" and (ob.name == "TERRAIN" or ob.name.upper().startswith("1GRASS")):
            base = len(gv)
            gv += [ob.matrix_world @ v.co for v in ob.data.vertices]
            gf += [[base + i for i in p.vertices] for p in ob.data.polygons]
    terrain = BVHTree.FromPolygons(gv, gf) if gf else None
    zones = release_zones(proj)

    def ground_at(x, y, z):
        if zones is None or terrain is None or not zones.contains(x, y):
            return None
        h = terrain.ray_cast(Vector((x, y, z + 5.0)), Vector((0.0, 0.0, -1.0)), 10.0)
        return None if h[0] is None else h[0].z

    def pave_at(x, y, z_lo, z_hi):
        hits, z0 = [], z_hi
        for _ in range(8):
            if road is None:
                break
            h = road.ray_cast(Vector((x, y, z0)), Vector((0.0, 0.0, -1.0)), z0 - z_lo)
            if h[0] is None:
                break
            hits.append(h[0].z)
            z0 = h[0].z - 1e-3
        return hits

    red = _red_points(proj)
    rep = {"_doc": "ledger 0099 round 1c: tools/author_walk_grade_blend.py. The street sidewalk's back grade, every lip "
                   "raised so no edge up to the walk's back edge is steeper than max_slope (route.walk_back_grade); "
                   "scene frame (x east, y north, z up)",
           "max_slope": sp["max_slope"], "objects": {}}
    for name in sp["objects"]:
        ob = bpy.data.objects.get(name)
        if ob is None or ob.type != "MESH":
            raise SystemExit(f"[walk-grade] no mesh {name!r} in loop.blend (route.walk_back_grade.objects)")
        me = ob.data
        mw = ob.matrix_world
        co = [tuple(mw @ v.co) for v in me.vertices]
        before = list(co)
        edges = [tuple(e.vertices) for e in me.edges]
        p = plan(co, edges, sp["max_slope"], pave_at, red, ground_at, furnished_vertices(bpy, ob, co))
        if not p["lips"]:
            raise SystemExit(f"[walk-grade] {name}: no back-grade lip found (an edge {DH_MIN}-{DH_MAX} m in plan, "
                             f"{DZ_MIN}-{DZ_MAX} m rise): not the draft's strip")
        inv = mw.inverted()
        for v, z in p["moves"].items():
            if z - co[v][2] > MOVE_MAX_M + 1e-6:
                raise SystemExit(f"[walk-grade] {name} vertex {v} would rise {z - co[v][2]:.3f} m (> {MOVE_MAX_M})")
            me.vertices[v].co = inv @ Vector((co[v][0], co[v][1], z))
        me.update()
        after = [tuple(mw @ v.co) for v in me.vertices]
        moved = [i for i in range(len(after)) if math.dist(after[i], before[i]) > 1e-6]
        if any(i not in p["moves"] for i in moved):
            raise SystemExit(f"[walk-grade] {name}: a vertex that is not a lip moved")
        if any(after[i][2] < before[i][2] - 1e-6 or abs(after[i][0] - before[i][0]) > 1e-6
               or abs(after[i][1] - before[i][1]) > 1e-6 for i in moved):
            raise SystemExit(f"[walk-grade] {name}: a lip moved down or sideways")
        steep = [i for i in p["moves"] if i not in p["capped"] for h, dh, _ in p["lips"][i]
                 if (after[h][2] - after[i][2]) / dh > sp["max_slope"] + 1e-4]
        if steep:
            raise SystemExit(f"[walk-grade] {name}: {len(steep)} raised lips still steeper than {sp['max_slope']} on "
                             f"read-back, e.g. vertex {steep[0]}")
        rise = [after[i][2] - before[i][2] for i in moved]
        rep["objects"][name] = {
            "vertices": len(co), "lips": len(p["lips"]), "raised": len(p["moves"]), "already_at_grade": p["already"],
            "held_release_ground": len(p["held_ground"]), "held_furniture": len(p["held_furniture"]),
            "held_pavement": len(p["held_pavement"]),
            "held_red_plan": len(p["held_red"]),
            "rise_m": {"p50": _q(rise, 0.5), "max": _q(rise, 1.0)},
            "before": falls(before, p["lips"]), "after": falls(after, p["lips"]),
            "held_release_ground_at": p["held_ground"][:2000], "held_furniture_at": p["held_furniture"][:2000],
            "held_pavement_at": p["held_pavement"][:400],
            "held_red_plan_at": p["held_red"]}
        o = rep["objects"][name]
        print(f"[walk-grade] {name}: {o['lips']} lips, {o['raised']} raised (rise p50 {o['rise_m']['p50']} max "
              f"{o['rise_m']['max']} m), {o['already_at_grade']} already at grade, held {o['held_release_ground']} by the released ground + "
              f"{o['held_furniture']} under furniture + {o['held_pavement']} by pavement + {o['held_red_plan']} by the red plan; fall p50 {o['before']['fall_m']['p50']} -> "
              f"{o['after']['fall_m']['p50']} m, steepest {o['before']['slope']['max']} -> {o['after']['slope']['max']}")
    out.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print(f"[walk-grade] max_slope {sp['max_slope']}; wrote data/{REPORT}; saved {blend}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
