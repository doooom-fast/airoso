"""Apply data/ground_release.json to loop.blend's TERRAIN, and rail every new drop a car could reach (ledger 0046,
v0.18.0 integration fix round; the plan, the zones and the WHY are in tools/ground_release.py).

Runs INSIDE Blender in the author stage, after the seat and the BEAUTY triangulation (the near-road ground every gate
was tuned on is that triangulation's: nothing outside a zone is touched) and before the median island and the bridge
bodies (which read the ground under each deck):

  1. every TERRAIN edge whose midpoint is in a zone and is longer than SUBDIV_M is halved (rounds), the new faces
     triangulated (BEAUTY) — the creek channel's walls are 7-16 m apart;
  2. every TERRAIN vertex in a zone takes the released height, blended by the zone weight (1 inside, smoothstep to 0
     over ground_release.RAMP_M at the zone's ends and outer edge):
       bank zone: under a ROAD / CURB surface -> unchanged (the prep pins it to the deck, as before); beside it -> 3DEP;
       span zone: under the deck -> min(3DEP, lowest deck over it - CLEAR_M); beside it -> 3DEP;
     in the ramp the blend runs toward the ground the kn5 prep will leave just outside the zone — a kept-cell vertex's
     refined height (engine-july build_kn5_loop.RefineField, read from the snapshot), not its graded height before the
     prep: the prep never touches a zone vertex, so a ramp toward the graded ground froze a band 2-4 m over 3DEP between
     two pieces of 3DEP (v0.18.0, the view lens's comb west of College's north approach); an end lying inside another
     zone on the same side does not ramp at all (ground_release.Zones: two abutting zones each ramped to nothing at the
     shared station);
  2b. BATTER (fix round 2, 2026-10-13: the view lens's 3-4 m vertical grass curtains beside Alvarado, where the built
     sidewalk is wider than the real one and the real bank falls away under its outer half, and where a real 3.6 m
     terrace climbs at ~54 deg from Alvarado to College's south approach): a released vertex beside the pavement stands
     no higher than min over every ROAD / CURB face within BATTER_REACH_M of (its height + BATTER_CUT * d) (45 deg up
     from the LOWEST nearby pavement) and, beside pavement on the ground (within ON_GROUND_M; from FILL_EASE_M on the fill
     starts lower, easing to the ground under the pavement at ON_GROUND_M, v0.18.0), no lower than
     max(height - BATTER_FILL * d) (56 deg down); the cut wins: an earth bank, never a cliff;
  2c. PER-FACE CAP (fix round 2: the truth + view lenses' grass 5 cm through Lake Murray Blvd's lane at the creek):
     every face with a released vertex is read on a FACE_STEP_M raster over its own area; where any of it lies over a
     ROAD / CURB surface, each of its released vertices is held CLEAR_M under the LOWEST pavement over that face, so the
     whole face (a plane under its corners) stays under the pavement, not only its corners. The old caps on the NEAREST
     pavement vertex's height are gone: they missed facets crossing the kerb, and pinned a real 3.6 m terrace beside
     College's south approach down to the height of a different, lower road (Alvarado);
  3. RAILS: along every zone side, every RAIL_STEP_M, the outer edge of the built pavement (ROAD + CURB, marched out
     from the centreline) and the NEW ground over the next EXC_BAND_M are read exactly as drive_test's excursion sweep
     reads them; where it would file an unguarded drop (a > EXC_DROP_M fall between 0.5 m samples, or the ground more
     than RAIL_FALL_M under the pavement edge) a concrete barrier (a Jersey profile, RAIL_BASE_M wide at the foot,
     RAIL_H_M tall) stands on the outer lip of the curb, padded RAIL_PAD_M past each run. It is its own physical mesh,
     RAIL_OBJECT (1WALL_guard_release: the prep's 1WALL_GUARD material row, double-sided, the loop's own I-8 bridge
     rail material; fix round 4 — appended to GUARDRAIL it split past the kn5 vertex cap), never where GUARDRAIL
     already stands within RAIL_DUP_M.
     The rail's line is smoothed along its run (a 5-station median, then a 5-station mean of the curb lip's offset, its
     base the lowest pavement of its neighbours) and split where the lip jumps more than RAIL_JUMP_M (a bridge end's
     curb return), so it never kinks into shards; padding never runs it into a bank rising behind it (RAIL_BURY_M).
     v0.18.0 (the view lens's white teeth on the parapet): the stations are read per SIDE over the union of the zones,
     so overlapping or abutting zones give ONE rail, not two prisms 3 cm apart with their end caps standing up; and
     each end slopes down over RAIL_TAPER_M (a sloped end treatment) instead of standing its square profile up.
  RAISE-ONLY CUTS (ledger 0054 P3 repair round 1, tools/ground_release.py AUTO CUTS): a zone with raise_only takes
     the released height only where it stands over the ground it had (the real wall over the graded verge) — never
     lower, except down to the cut batter where the ground stood over it at the pavement edge — and its batter is the
     zone's own cut_slope (the steepest the real face climbs there, 1-2 m per metre)
     instead of BATTER_CUT, measured from the back of the WALK (repair round 2), not from the foot of the walk's buried
     apron: the face climbs from the walk's own edge and buries the apron. After the halving and after the heights, every vertical sliver the halving's n-gons left
     (a T-vertex on a face's straight edge, tools/terrain_mend.py) is mended: no fin, no crack.
Self-checks (exit 1, loop.blend NOT saved): a zone that moved nothing; a released vertex left above the deck over it;
a face with a released vertex standing over a ROAD / CURB surface anywhere over its area (raster); a rail vertex over a
ROAD surface. Writes data/ground_release.report.json.

    blender --background --python-exit-code 1 --python tools/ground_release_blend.py -- <project-dir>
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import terrain_mend  # noqa: E402

SUBDIV_M = 2.5        # [invented] zone terrain edges are halved down to this
CLEAR_M = 0.02        # build_kn5_loop.GROUND_CLEAR: ground stands this far under the deck
HELD_PIT_M = 1.0      # [invented] a bank zone's ground under the pavement more than this under its sheet is a pit (fix round 4:
#                       College's south approach, 6 m under its sidewalk) and is lifted to the sheet; shallower stands
BATTER_CUT = 1.0      # [invented] steepest released bank RISING from a pavement edge: 1 m per metre (45 deg). Fresh 3DEP has
#                       the terrace beside Alvarado / College's south approach at ~54 deg over 2 m; on 1.25 m facets a
#                       steeper bound reads as a pleated green curtain from the road (the view lens), so the bank is
#                       laid back to 45 deg: the terrace edge moves <= ~1 m back
BATTER_FILL = 1.7     # [invented] steepest released bank FALLING from a pavement edge (59.5 deg, just under the view lens's
#                       60 deg cliff line: a fill is seen from above, and every gentler one builds more earth out over the
#                       real creek bank where the built sidewalk overhangs it — at 1.5 criterion 4's s 2400 rim, 1.3 m off
#                       the sidewalk, stood 2.004 m over 3DEP)
BATTER_REACH_M = 12.0 # [invented] the batter is read within this plan distance of the pavement edge
ON_GROUND_M = 1.0     # [invented] a pavement point carries a fill batter where the ground under it is within this
GAP_INSET_M = 0.4     # [invented] the ground under a pavement face's corner is read this far inside the face
FILL_EASE_M = 0.25    # [invented] ...and the fill starts at the pavement only while that gap is under this; from here to
#                       ON_GROUND_M it eases (smoothstep) down to the ground under the pavement, so where an approach
#                       leaves its embankment for a bridge the fill fades out with the ground instead of switching off face
#                       by face (the view lens, v0.18.0: grass teeth beside College's south abutment wall, 1.2-1.9 m over
#                       3DEP, where the sidewalk's 3.5 m faces flipped between 'on the ground' and 'in the air')
EDGE_SUBDIV_M = 1.0   # [invented] zone edges crossing the pavement's outer edge are halved down to this
TOP_NZ = 0.7          # [invented] a ROAD / CURB face is pavement to stand on when its normal is this close to up
PREP_BAND_M = 3.0     # engine-july build_kn5_loop BAND_M (the prep's full-contact shelf past the road's edge)
PREP_FEATHER_M = 6.0  # engine-july build_kn5_loop FEATHER_M (its smoothstep blend beyond the shelf)
APRON_NZ = 0.985      # [invented] repair round 1: a CURB face sloping more than this (|normal z| under it: ~10 deg, the
#                       walk's own 0.28 m-per-metre apron at 0.96; a walk top on a 15 % hill at 0.989) is the buried apron
FACE_STEP_M = 0.25    # [invented] raster step of the per-face pavement cap (zone faces are <= ~2.5 m)
FACE_TOL_M = 0.003    # [invented] the self-check: no released face more than this OVER the pavement (the cap holds the
#                       corners CLEAR_M under its lowest point; a curb edge's own camber may eat into that clearance)
RAIL_JUMP_M = 0.5     # [invented] a rail station whose curb lip departs this far from the run's smoothed line splits it
RAIL_HELD_M = 0.3     # [invented] an existing rail within this of the lane-to-lip line already holds the car
RAIL_BURY_M = 0.4     # [invented] padding stops where the ground behind the rail stands this far over the curb lip
DECK_WIN_M = 3.0      # a deck hit counts within this of the centreline deck height (author_bridges_blend)
XS_STEP_M = 0.25      # cross-section march for the pavement's outer edge
XS_MAX_M = 6.0        # ...at most this far past the nominal half-width (a mouth's side street is not the edge)
RAIL_STEP_M = 1.0     # rail stations along a zone
EXC_BAND_M = 4.0      # drive_test: the excursion band past the BUILT pavement edge
EXC_STEP_M = 0.5      # drive_test: lateral sample step
EXC_SCAN_M = 0.125    # read at a quarter of it, every 0.5 m pair compared (drive_test's phase is its own centreline's)
EXC_DROP_M = 0.12     # drive_test: a fall between samples larger than this is an excursion drop
RAIL_FALL_M = 0.5     # [invented] ...and a total fall under the pavement edge larger than this gets a rail too
RAIL_PAD_M = 3.0      # [invented] a rail runs this far past its run at each end
RAIL_GAP_M = 4.0      # [invented] runs closer than this merge
RAIL_MIN_M = 6.0      # [invented] no rail shorter than this
RAIL_DUP_M = 2.0      # [invented] no new rail within this of an existing GUARDRAIL vertex (the I-8 bridge rails)
RAIL_IN_M = 0.30      # the rail's centre stands this far inside the pavement's outer edge (on the curb's lip)
RAIL_BASE_M = 0.60    # Jersey barrier: foot width (drive_test probes every 0.5 m: a thinner one could fall between)
RAIL_TOP_M = 0.20     # ...top width
RAIL_H_M = 0.81       # ...height above its base (the standard 32 in)
RAIL_SINK_M = 0.30    # ...and its foot runs this far into the curb
RAIL_TAPER_M = 2.0    # [invented] a rail's top slopes down over this much of each end (a sloped end treatment)...
RAIL_END_H_M = 0.05   # ...to this height over its base: no square end standing up — only over padding past every
#                       station that needs the rail (ground_release.rail_heights; fix round 4)
DEGEN_AREA_M2 = 1e-5  # [invented] a zone face smaller than this is a sliver of the halving (dissolved; was 1e-8 before 0055)
DEGEN_DIST_M = 1e-3   # [invented] ...merged into its neighbours with vertices this close (dissolve_degenerate)
RAIL_OBJECT = "1WALL_guard_release"   # the release rails' own physical mesh(es) (never appended to GUARDRAIL)
RAIL_CHUNK_TRIS = 18000  # [invented] triangles per rail mesh: 3 kn5 vertices each at worst stays under the 65,536 cap
RAIL_EXT_FALL_M = 1.0  # [invented] ...and only while the ground falls more than this under the pavement edge, steeply
RAIL_EXT_MAX_M = 120.0  # [invented] a rail follows a drop this far past a zone's end at most (College's approach foot:
#                       the embankment edge runs ~100 m back from the zone to s ~2401)


def _release_module():
    spec = importlib.util.spec_from_file_location("_airoso_ground_release", AIROSO / "tools" / "ground_release.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# the kn5 prep's kept-cell refinement (engine-july scripts/ac/build_kn5_loop.RefineField, pure python): the record of
# the prep the chain runs is this snapshot (tracks/<slug>/engine-july-snapshot, mirrored byte-for-byte into engine-july)
PREP_SNAPSHOT = AIROSO / "tracks" / "san-diego-lake-murray" / "engine-july-snapshot" / "scripts" / "ac" / "build_kn5_loop.py"


def _refine_field(proj):
    """the prep's RefineField for this project (data/terrain.refine.json.gz), or None (no refinement data, no snapshot):
    what the prep will make of a kept-cell vertex the zones do NOT hold"""
    import gzip
    p = proj / "data" / "terrain.refine.json.gz"
    if not p.exists() or not PREP_SNAPSHOT.exists():
        return None
    spec = importlib.util.spec_from_file_location("_airoso_prep_snapshot", PREP_SNAPSHOT)
    mod = importlib.util.module_from_spec(spec)
    dwb, sys.dont_write_bytecode = sys.dont_write_bytecode, True     # no __pycache__ inside the mirrored snapshot
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = dwb
    return mod.RefineField(json.loads(gzip.decompress(p.read_bytes()).decode("utf-8")))


def _bvh(objs):
    vs, fs = [], []
    for ob in objs:
        me = ob.data
        base = len(vs)
        vs += [tuple(ob.matrix_world @ v.co) for v in me.vertices]
        fs += [tuple(base + i for i in p.vertices) for p in me.polygons]
    return BVHTree.FromPolygons(vs, fs) if fs else None


def _hits(tree, x, y, top, bottom):
    out = []
    z = top
    for _ in range(12):
        h = tree.ray_cast(Vector((x, y, z)), Vector((0, 0, -1)), z - bottom)
        if h[0] is None:
            break
        out.append(h[0].z)
        z = h[0].z - 1e-4
    return out


def _bary(x, y, a, b, c):
    d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(d) < 1e-12:
        return None
    l1 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / d
    l2 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / d
    l3 = 1.0 - l1 - l2
    if l1 >= -1e-9 and l2 >= -1e-9 and l3 >= -1e-9:
        return l1, l2, l3
    return None


def _plane_z(co, x, y):
    """height of the (fan-triangulated) face with corners co [(x, y, z)] at (x, y), or None outside it"""
    for k in range(1, len(co) - 1):
        w = _bary(x, y, co[0], co[k], co[k + 1])
        if w is not None:
            return w[0] * co[0][2] + w[1] * co[k][2] + w[2] * co[k + 1][2]
    return None


def face_samples(co, step):
    """plan sample points of a face: its corners, edge midpoints and a ``step`` raster inside it"""
    out = [(c[0], c[1]) for c in co]
    n = len(co)
    out += [((co[i][0] + co[(i + 1) % n][0]) / 2, (co[i][1] + co[(i + 1) % n][1]) / 2) for i in range(n)]
    xs = [c[0] for c in co]
    ys = [c[1] for c in co]
    x = min(xs)
    while x <= max(xs) + 1e-9:
        y = min(ys)
        while y <= max(ys) + 1e-9:
            if _plane_z(co, x, y) is not None:
                out.append((x, y))
            y += step
        x += step
    return out


def smooth_offsets(vals, k=2):
    """a (2k+1)-station running median, then a (2k+1)-station running mean (shorter windows at the run's ends)"""
    n = len(vals)
    med = []
    for i in range(n):
        w = sorted(vals[max(0, i - k):i + k + 1])
        med.append(w[len(w) // 2])
    return [sum(med[max(0, i - k):i + k + 1]) / len(med[max(0, i - k):i + k + 1]) for i in range(n)]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    rp = data / "ground_release.json"
    if not rp.exists():
        print("[release] no data/ground_release.json (no zones declared) — nothing to do")
        return
    GR = _release_module()
    R = json.loads(rp.read_text(encoding="utf-8"))
    cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in cl["points_xyz_m"]]
    Z = GR.Zones(pts, cl["widths_m"], R["zones"])
    L = GR.Lattice(R["cell_m"], R["I"], R["J"], R["h"])

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    ob = bpy.data.objects.get("TERRAIN")
    if ob is None:
        raise SystemExit("[release] no TERRAIN object")
    deck_objs = [o for o in (bpy.data.objects.get("ROAD"), bpy.data.objects.get("CURB")) if o is not None]
    road_obj = bpy.data.objects.get("ROAD")
    deck = _bvh(deck_objs)
    # the pavement a car or a foot stands on: ROAD / CURB faces near level (|normal z| >= TOP_NZ, either winding: the
    # assembler's ROAD faces point down), never a curb's or a deck's skirt face (a ray from above lands on a skirt too,
    # and the ground beside a sidewalk cannot be under it)
    dv, dfaces = [], []
    for o in deck_objs:
        base = len(dv)
        dv += [tuple(o.matrix_world @ v.co) for v in o.data.vertices]
        mw3 = o.matrix_world.to_3x3()
        dfaces += [tuple(base + i for i in p.vertices) for p in o.data.polygons if abs((mw3 @ p.normal).normalized().z) >= TOP_NZ]
    top = BVHTree.FromPolygons(dv, dfaces)
    # ...and that pavement less the sidewalk's outer APRON (the CURB profile's last 1.2 m, graded down to 0.20 m under the
    # edge so the ground buries it — the prep's contact feather leaves the grass over it on every street): what a
    # raise-only cut's faces must stay under (repair round 1: capped under the apron's foot, the grass behind every walk
    # in the cut zones fell 0.2-0.35 m and bared the apron, 0.14 m drops a car reads off the walk: excursions 39 -> 60)
    wfaces = []
    for o in deck_objs:
        base = sum(len(q.data.vertices) for q in deck_objs[:deck_objs.index(o)])
        mw3 = o.matrix_world.to_3x3()
        for p in o.data.polygons:
            nz_ = abs((mw3 @ p.normal).normalized().z)
            if nz_ >= TOP_NZ and (o is road_obj or nz_ >= APRON_NZ):
                wfaces.append(tuple(base + i for i in p.vertices))
    top_walk = BVHTree.FromPolygons(dv, wfaces)
    flat = BVHTree.FromPolygons([(p[0], p[1], 0.0) for p in dv], dfaces)   # the pavement's plan, for edge distances
    # ...and the plan of the pavement less the walk's buried apron, with each face's mean height: where a raise-only cut's
    # batter starts (repair round 2: from the apron's foot it started 1.1 m out and 0.3 m down, behind a walk the real
    # rock rises straight from — Mission Gorge's south face s 1490-1555 kept 1.2-1.5 m too little 18-20 m out)
    flat_walk = BVHTree.FromPolygons([(p[0], p[1], 0.0) for p in dv], wfaces) if wfaces else None
    wface_h = [sum(dv[i][2] for i in f) / len(f) for f in wfaces]
    road_only = _bvh([road_obj]) if road_obj is not None else None
    # the ROAD's plan (repair round 1: a raise-only cut keeps the prep's contact band — the prep leaves zone ground alone)
    flat_road = None
    if road_obj is not None:
        _rv = [tuple(road_obj.matrix_world @ v.co) for v in road_obj.data.vertices]
        flat_road = BVHTree.FromPolygons([(p[0], p[1], 0.0) for p in _rv], [tuple(q.vertices) for q in road_obj.data.polygons])
    if deck is None:
        raise SystemExit("[release] no ROAD/CURB deck")

    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    v0 = len(bm.verts)
    # 1. subdivide inside the zones
    n_sub = 0
    for _round in range(6):
        todo = []
        for e in bm.edges:
            a, b = e.verts[0].co, e.verts[1].co
            # PLAN length (v0.18.0 fix round 4, the runtime lens's zero-length normals): a vertical edge of the seat's
            # curtain (two vertices on one plan point) halved round after round stacked up to 31 coincident faces on
            # one plan point, back to back — the lattice is a plan resolution
            if math.hypot(a.x - b.x, a.y - b.y) <= SUBDIV_M:
                continue
            if Z.weight((a.x + b.x) / 2, (a.y + b.y) / 2)[0] > 0.0 or Z.weight(a.x, a.y)[0] > 0.0 \
                    or Z.weight(b.x, b.y)[0] > 0.0:
                todo.append(e)
        if not todo:
            break
        new = bmesh.ops.subdivide_edges(bm, edges=todo, cuts=1, use_grid_fill=True)
        n_sub += len(todo)
        faces = {f for g in new.get("geom", []) if isinstance(g, bmesh.types.BMVert) for f in g.link_faces}
        faces = [f for f in faces if len(f.verts) > 3]
        if faces:
            bmesh.ops.triangulate(bm, faces=faces, quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.faces.ensure_lookup_table()
    leftover = [f for f in bm.faces if len(f.verts) > 3]
    if leftover:
        bmesh.ops.triangulate(bm, faces=leftover, quad_method="BEAUTY", ngon_method="BEAUTY")
    # ...and every zone edge that crosses the pavement's outer edge (one end under a ROAD / CURB surface, the other not)
    # down to EDGE_SUBDIV_M: a 2.5 m facet reaching from beyond a 2 m sidewalk onto the road would be capped (2c) at
    # the road's height, a step down off the back of the sidewalk that drive_test reads as a drop (and the rails then
    # guard a terrace that rises)
    n_edge = 0

    def under_top(co):
        return top.ray_cast(Vector((co.x, co.y, co.z + 50.0)), Vector((0, 0, -1)), 200.0)[0] is not None

    for _round in range(4):
        todo = []
        for e in bm.edges:
            a, b = e.verts[0].co, e.verts[1].co
            if math.hypot(a.x - b.x, a.y - b.y) <= EDGE_SUBDIV_M:
                continue
            if Z.weight((a.x + b.x) / 2, (a.y + b.y) / 2)[0] <= 0.0:
                continue
            if under_top(a) != under_top(b):
                todo.append(e)
        if not todo:
            break
        new = bmesh.ops.subdivide_edges(bm, edges=todo, cuts=1, use_grid_fill=True)
        n_edge += len(todo)
        faces = {f for g in new.get("geom", []) if isinstance(g, bmesh.types.BMVert) for f in g.link_faces}
        faces = [f for f in faces if len(f.verts) > 3]
        if faces:
            bmesh.ops.triangulate(bm, faces=faces, quad_method="BEAUTY", ngon_method="BEAUTY")
    n_sub += n_edge
    # coincident faces (one vertex set, either winding) left by the halving: a sliver group goes (it covers no ground),
    # a real face keeps one copy (v0.18.0 fix round 4: 448 such sets in round 3, up to 31 faces deep, back to back)
    bm.verts.index_update()
    groups = {}
    for f in bm.faces:
        groups.setdefault(frozenset(v.index for v in f.verts), []).append(f)
    kill = []
    for g in groups.values():
        if len(g) > 1:
            kill += g if max(f.calc_area() for f in g) < 0.01 else g[1:]
    n_coinc = len(kill)
    if kill:
        touched = {v for f in kill for v in f.verts}
        bmesh.ops.delete(bm, geom=kill, context="FACES_ONLY")
        loose = [v for v in touched if v.is_valid and not v.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context="VERTS")
    mend0 = terrain_mend.mend_vertical_slivers(bm)
    bm.verts.index_update()
    bm.faces.index_update()
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    # 2. released heights
    per_zone = {z["name"]: {"moved": 0, "max_down_m": 0.0, "max_up_m": 0.0, "under_deck": 0} for z in R["zones"]}
    bad_poke = []
    n_nodata = 0
    bm.verts.ensure_lookup_table()
    released = {}                     # vertex index -> (under a deck, zone name, height before this step)
    held = {}                         # vertex index -> height: in a bank zone but under the pavement (not released)
    # the zone's ramp blends toward the ground the PREP leaves outside the zone, not the ground before it (v0.18.0, the
    # view lens's comb 37 m west of College's north approach: the prep refines a kept cell past 20 m to the data but
    # leaves every zone vertex alone, so a ramp blended toward the graded ground it had BEFORE the prep froze a 4 m band
    # 2-4 m over 3DEP between two pieces of 3DEP — sawn into teeth by the 1.25 m lattice)
    RF = _refine_field(proj)
    n_ramp_ref = 0
    n_held_pin = 0
    n_walk_seat = 0
    pits = set()
    # raise-only cuts: the ground a vertex "had" is the LOWEST sheet at its plan point (the seat's vertical curtains put
    # two vertices on one plan point at different heights; raising each from its own left the curtain standing — 780
    # vertical faces up to 1.3 m on repair round 1's first rehearsal — raising both from the lower one collapses it and
    # the weld below takes the pair)
    low_at = {}
    for v in bm.verts:
        k_ = (round(v.co.x, 4), round(v.co.y, 4))
        if k_ not in low_at or v.co.z < low_at[k_]:
            low_at[k_] = v.co.z
    for v in bm.verts:
        x, y, z = v.co.x, v.co.y, v.co.z
        w, zone = Z.weight(x, y)
        if w <= 0.0:
            continue
        D = L.at(x, y)
        if D is None:
            n_nodata += 1
            continue
        hs = _hits(deck, x, y, 10000.0, -1000.0)
        under = bool(hs)
        if zone["kind"] == "bank":
            if under:
                # in the zone, under the pavement: held CLEAR_M under its LOWEST upward sheet, here. The prep pins the
                # ground under a deck only to a sheet within its window of the vertex's own height, and leaves every
                # zone vertex alone otherwise (v0.18.0 fix round 4, the view lens's stepped curtain under College Ave's
                # south approach: the draft seats that ground at Alvarado's level, 6 m under College's sidewalk, so
                # it stayed a pit under the sidewalk, sawn against the released bank beside it)
                # Only a PIT is lifted (more than HELD_PIT_M under the sheet): elsewhere the seat's height under the
                # pavement stands, as in v0.17.1 (lifting every held vertex to its own sheet put the ground under a curb
                # top 0.13 m over the gutter beside it: soft top 42 -> 211 at Alvarado's lane edge, this round's first
                # rehearsal). A lifted pit is then capped with the released ground, face by face (2c)
                ht = _hits(top, x, y, 10000.0, -1000.0)
                if ht and z < min(ht) - CLEAR_M - HELD_PIT_M:
                    v.co.z = min(ht) - CLEAR_M
                    pits.add(v.index)
                    n_held_pin += 1
                elif (zone.get("raise_only") and ht and flat_road is not None
                      and not _hits(road_only, x, y, 10000.0, -1000.0)):
                    # repair round 1: under the WALK (not the road) in a raise-only cut, exactly what the prep does to
                    # such ground outside a zone (it leaves a zone's alone): its contact feather toward the nearest
                    # road deck, then its anti-poke under the lowest sheet over it — so the ground under the curb and
                    # the walk stands where it does on every other street (left at the seat's height, a face from a
                    # vertex under the curb top to one under the gutter stood 2-4 cm over the road: soft tops)
                    nr = flat_road.find_nearest((x, y, 0.0), PREP_BAND_M + PREP_FEATHER_M)
                    if nr[0] is not None:
                        d2 = nr[3]
                        wb = 1.0 if d2 <= PREP_BAND_M else GR.smoothstep(1.0 - (d2 - PREP_BAND_M) / PREP_FEATHER_M)
                        n3 = road_only.find_nearest((x, y, z))
                        if n3[0] is not None:
                            v.co.z = min((n3[0].z - CLEAR_M) * wb + z * (1.0 - wb), min(ht) - CLEAR_M)
                            n_walk_seat += 1
                held[v.index] = z
                continue
            t = D
        else:
            if under:
                t = min(D, min(hs) - CLEAR_M)
                per_zone[zone["name"]]["under_deck"] += 1
            else:
                t = D
        if zone.get("raise_only") and not under:
            z = low_at[(round(x, 4), round(y, 4))]
        released[v.index] = (under, zone["name"], z)
        zo = z
        if w < 1.0 and not under and RF is not None and RF.in_kept(x, y):
            nb_ = flat.find_nearest((x, y, 0.0), 1.0e6)
            tg = RF.target(x, y, z, d_built=nb_[3] if nb_[0] is not None else None)
            if tg is not None:
                zo = tg
        if w < 1.0 and zo != z:
            n_ramp_ref += 1
        if zone.get("raise_only"):
            t = max(t, z)              # the real wall over the graded verge: up to it, never below the ground it had
        v.co.z = zo + w * (t - zo)
        if under:                     # in a zone's ramp the blend may not leave the ground over the deck either
            v.co.z = min(v.co.z, min(hs) - CLEAR_M)
        if under and v.co.z > min(hs) - CLEAR_M + 1e-4:
            bad_poke.append((round(x, 1), round(y, 1), round(v.co.z, 2), round(min(hs), 2)))

    def pave_at(x, y, walk=False):
        """the LOWEST upward ROAD / CURB surface at (x, y), or None (walk: the sidewalk's buried apron left out)"""
        hs = _hits(top_walk if walk else top, x, y, 10000.0, -1000.0)
        return min(hs) if hs else None

    # 2b. the batter, from EVERY pavement face within reach (not only the nearest: between a low road and a high one
    # 8 m apart — Alvarado under College's south approach — the low road's edge is what the bank must not out-climb):
    # the vertex stands no higher than min(h_f + BATTER_CUT * d_f) and, beside pavement on the ground after step 2,
    # no lower than max(h_f - BATTER_FILL * d_f); h_f a face's mean height, d_f its plan distance. The cut wins.
    gr1 = BVHTree.FromBMesh(bm)
    face_h = [sum(dv[i][2] for i in f) / len(f) for f in dfaces]
    vgap = {}
    on_ground = {}
    zone_kind = {z["name"]: z.get("kind") for z in R["zones"]}

    def grounded(fi):
        """BANK zones: the face counts as on the ground when the ground under its centroid is within ON_GROUND_M — there
        the ground under the pavement is held (the prep pins it), so a corner over the released bank beyond the pavement's
        outer edge must not switch the fill off (the curtain the fill exists to close)"""
        if fi not in on_ground:
            f = dfaces[fi]
            cx = sum(dv[i][0] for i in f) / len(f)
            cy = sum(dv[i][1] for i in f) / len(f)
            g = gr1.ray_cast(Vector((cx, cy, face_h[fi] - 0.005)), Vector((0, 0, -1)), 500.0)[0]
            on_ground[fi] = g is not None and face_h[fi] - g.z <= ON_GROUND_M
        return on_ground[fi]

    def pave_gap(fi, i):
        """the ground's depth under face fi's corner i (after step 2), read GAP_INSET_M inside the face toward its centroid
        (a corner on the pavement's outer edge sits over the released bank beyond it; the ground the pavement stands on
        is just inside), or None (no ground under it)"""
        key = (fi, i)
        if key not in vgap:
            f = dfaces[fi]
            cx = sum(dv[j][0] for j in f) / len(f)
            cy = sum(dv[j][1] for j in f) / len(f)
            cz = sum(dv[j][2] for j in f) / len(f)
            x, y, z = dv[i]
            dx, dy = cx - x, cy - y
            L = math.hypot(dx, dy)
            k = min(GAP_INSET_M, 0.5 * L) / L if L > 1e-9 else 0.0
            px, py, pz = x + dx * k, y + dy * k, z + (cz - z) * k
            g = gr1.ray_cast(Vector((px, py, pz - 0.005)), Vector((0, 0, -1)), 500.0)[0]
            vgap[key] = None if g is None else max(0.0, pz - g.z)
        return vgap[key]

    def fill_top(fi, qx, qy):
        """the height a fill batter starts from at q, the point of face fi nearest the vertex (where its distance is
        measured): the pavement while the ground under it is within FILL_EASE_M, the ground under it at ON_GROUND_M,
        smoothstep between, none past that — read AT q, linear over the face, never at the face's centroid (v0.18.0, the
        view lens's teeth at College's south abutment: a 3.5 m sidewalk face whose centroid stood over the embankment
        held a vertex 0.8 m over 3DEP beside a corner of it already 2 m in the air), so the fill fades with the ground
        where an approach leaves its embankment for a bridge"""
        f = dfaces[fi]
        w = None
        for k in range(1, len(f) - 1):
            bc = _bary(qx, qy, dv[f[0]], dv[f[k]], dv[f[k + 1]])
            if bc is not None:
                w = {f[0]: bc[0], f[k]: bc[1], f[k + 1]: bc[2]}
                break
        if w is None:                 # q on the face's outline, a hair outside every fan triangle: its nearest corner
            i = min(f, key=lambda j: (dv[j][0] - qx) ** 2 + (dv[j][1] - qy) ** 2)
            w = {i: 1.0}
        gap = 0.0
        h = 0.0
        for i, wi in w.items():
            gi = pave_gap(fi, i)
            if gi is None:
                if wi > 1e-6:
                    return None
                continue
            gap += wi * gi
            h += wi * dv[i][2]
        if gap > ON_GROUND_M:
            return None
        u = 0.0 if ON_GROUND_M <= FILL_EASE_M else min(1.0, max(0.0, (gap - FILL_EASE_M) / (ON_GROUND_M - FILL_EASE_M)))
        return h - CLEAR_M - gap * u * u * (3.0 - 2.0 * u)

    n_cut = n_fill = n_bank = 0
    n_round = 0
    n_walk_origin = 0
    zone_rec = {z["name"]: z for z in R["zones"]}
    for vi, (under, zname, z0) in released.items():
        if under:
            continue
        v = bm.verts[vi]
        # ledger 0055: a zone may read its cut farther than BATTER_REACH_M (College Ave's cut face meets the real hill
        # 12-14 m out, 12-13.8 m over the deck) and round its top (round_m); the fill keeps BATTER_REACH_M
        zr = zone_rec.get(zname) or {}
        reach_c = max(BATTER_REACH_M, float(zr.get("cut_reach_m") or 0.0))
        cut_k = float(zr.get("cut_slope") or BATTER_CUT)
        rk = GR.round_k(float(zr.get("round_m") or 0.0), cut_k)
        near_c = flat.find_nearest_range((v.co.x, v.co.y, 0.0), reach_c)
        if not near_c:
            continue
        near = [r for r in near_c if r[3] <= BATTER_REACH_M]
        # (limit, the pavement height it starts from, its plan distance): the lowest cut, the highest fill
        cut = min((face_h[fi] - CLEAR_M + cut_k * d, face_h[fi] - CLEAR_M, d) for _q, _n, fi, d in near_c)
        if zr.get("raise_only") and flat_walk is not None:
            # repair round 2: a raise-only cut's batter rises from the BACK OF THE WALK, not from the foot of its buried
            # apron (the CURB profile's last 1.2 m, graded 0.2-0.3 m down so the ground buries it on every street): the
            # cut face climbs from the walk's own edge and buries the apron, as the real rock stands behind the walk
            near_w = flat_walk.find_nearest_range((v.co.x, v.co.y, 0.0), reach_c)
            if near_w:
                cut = min((wface_h[fi] - CLEAR_M + cut_k * d, wface_h[fi] - CLEAR_M, d) for _q, _n, fi, d in near_w)
                n_walk_origin += 1
        if zone_kind.get(zname) == "span":
            # SPAN zones: the ground under the pavement is the released real earth (a deck may stand over it), so the fill
            # starts where the pavement actually sits on it — read at the nearest point, eased by the gap (fill_top)
            fills = [(ft - BATTER_FILL * d, ft, d) for ft, d in ((fill_top(fi, q[0], q[1]), d) for q, _n, fi, d in near)
                     if ft is not None]
        else:
            fills = [(face_h[fi] - CLEAR_M - BATTER_FILL * d, face_h[fi] - CLEAR_M, d) for _q, _n, fi, d in near
                     if grounded(fi)]
        fill = max(fills) if fills else None
        z_in = v.co.z
        nz = GR.batter_z(z_in, cut, fill, round_k=rk)
        if zr.get("raise_only"):
            # raise-only: never under the ground it had (no fill side changes, no new drop) — but never over the cut
            # batter either: ground the seat left standing over the batter line at the pavement edge is trimmed to it
            # (it never falls below the pavement there: the limit starts at the pavement's own height), so no curtain
            # stands at the back of the walk (repair round 1's first rehearsal: 780 vertical faces kept, up to 1.3 m)
            nz = min(max(nz, z0), cut[0])
            # ...and never under the ground the prep's contact band would have left there: the prep feathers every
            # vertex outside a zone toward the nearest road deck (PREP_BAND_M full, smoothstep over PREP_FEATHER_M), which
            # is what buries the sidewalk's outer apron on every street; it leaves zone ground alone, so a raise-only cut
            # takes the UP half of it itself (repair round 1: without it the grass behind every walk in a cut stood
            # 0.2-0.35 m low and bared the apron)
            if flat_road is not None:
                nr = flat_road.find_nearest((v.co.x, v.co.y, 0.0), PREP_BAND_M + PREP_FEATHER_M)
                if nr[0] is not None:
                    d2 = nr[3]
                    wb = 1.0 if d2 <= PREP_BAND_M else GR.smoothstep(1.0 - (d2 - PREP_BAND_M) / PREP_FEATHER_M)
                    n3 = road_only.find_nearest((v.co.x, v.co.y, z0))
                    if n3[0] is not None:
                        nz = max(nz, (n3[0].z - CLEAR_M) * wb + z0 * (1.0 - wb))
        if rk > 0.0 and cut[0] - rk < max(z_in, fill[0] if fill is not None else z_in) < cut[0] + rk:
            n_round += 1
        if fill is not None and z_in < fill[0]:
            n_fill += 1
        if nz < max(z_in, fill[0] if fill is not None else z_in) - 1e-9:
            n_cut += 1
        if fill is not None and fill[0] > cut[0] and fill[1] - cut[1] > GR.STRAIGHT_BANK_MIN_M:
            n_bank += 1
        v.co.z = nz

    # 2c. per-face cap: no face with a released vertex stands over a ROAD / CURB surface anywhere over its area
    # ...and every face with a lifted PIT corner (step 2): lifted to the sheet over it, its faces may reach over a lower
    # sheet beside it (College's sidewalk over its gutter), so it is lowered with the released corners
    lowerable = set(released) | pits
    rel_faces = {f for vi in lowerable for f in bm.verts[vi].link_faces}

    raise_zone = {z["name"] for z in R["zones"] if z.get("raise_only")}

    def walk_face(f):
        """a face with a corner released in a raise-only cut stays under the walk and the road, not the apron"""
        return any(released.get(v.index, (None, None))[1] in raise_zone for v in f.verts)

    def face_low_pave(f):
        wk = walk_face(f)
        co = [tuple(v.co) for v in f.verts]
        cx = sum(c[0] for c in co) / len(co)
        cy = sum(c[1] for c in co) / len(co)
        r = max(math.hypot(c[0] - cx, c[1] - cy) for c in co)
        if flat.find_nearest((cx, cy, 0.0), r + 0.01)[0] is None:
            return None
        low = None
        for x, y in face_samples(co, FACE_STEP_M):
            h = pave_at(x, y, wk)
            if h is not None and (low is None or h < low):
                low = h
        return low

    n_capped = 0
    low_of = {}
    for f in rel_faces:
        low = face_low_pave(f)
        if low is None:
            continue
        low_of[f] = low
        for v in f.verts:
            # a released corner only: a corner under the pavement (held) is the prep's to pin and anti-poke under its
            # own sheet, as in v0.17.1 (capping it to a face's lowest point dropped the ground under a sidewalk's back
            # edge 0.5 m to a curb apron's foot)
            if v.index in lowerable and v.co.z > low - CLEAR_M:
                v.co.z = low - CLEAR_M
                n_capped += 1
    # the check reads each face as the prep will leave it: an unreleased corner under the pavement is held under its
    # lowest sheet (build_kn5_loop's anti-poke); a face still over the pavement because of an UNRELEASED corner beside
    # it was so before this step (lowering the released corners cannot have raised it) and is reported, not fatal
    bad_face, pre_face = [], []
    for f in low_of:
        co = []
        unrel_high = False
        wk = walk_face(f)
        for v in f.verts:
            z = v.co.z
            if v.index not in lowerable:
                pv_ = pave_at(v.co.x, v.co.y)
                if pv_ is not None:
                    z = min(z, pv_ - CLEAR_M)
                if z > low_of[f] - CLEAR_M + FACE_TOL_M:
                    unrel_high = True
            co.append((v.co.x, v.co.y, z))
        for x, y in face_samples(co, FACE_STEP_M):
            h = pave_at(x, y, wk)
            gz = _plane_z(co, x, y) if h is not None else None
            if gz is not None and gz > h + FACE_TOL_M:
                (pre_face if unrel_high else bad_face).append(
                    (round(x, 2), round(y, 2), round(gz - h, 3),
                     [(round(c[0], 2), round(c[1], 2), round(c[2], 3), v.index in released,
                       None if pave_at(c[0], c[1]) is None else round(pave_at(c[0], c[1]), 3)) for c, v in zip(co, f.verts)]))
                break
    # steep released faces within the batter's reach (reported: a real channel wall past the pavement edge is data)
    bm.normal_update()
    n_steep = 0
    steep_open = []                   # ...of which out in the open (not under a deck, where the bridge body stands)
    for f in rel_faces:
        co = [v.co for v in f.verts]
        if abs(f.normal.z) < 0.5 and max(c.z for c in co) - min(c.z for c in co) > 0.5:
            cx = sum(c.x for c in co) / len(co)
            cy = sum(c.y for c in co) / len(co)
            if flat.find_nearest((cx, cy, 0.0), BATTER_REACH_M)[0] is not None:
                n_steep += 1
                if not _hits(deck, cx, cy, 10000.0, -1000.0):
                    steep_open.append((round(cx, 1), round(cy, 1), round(max(c.z for c in co) - min(c.z for c in co), 2)))
    for vi, (under, zname, z0) in released.items():
        dz = bm.verts[vi].co.z - z0
        if abs(dz) < 1e-4:
            continue
        rec = per_zone[zname]
        rec["moved"] += 1
        rec["max_down_m"] = round(max(rec["max_down_m"], -dz), 3)
        rec["max_up_m"] = round(max(rec["max_up_m"], dz), 3)
    # the seat's vertical curtains (two vertices on one plan point) collapse where both ends take the same released
    # height: those coincident vertices are welded, so no zero-area face is left behind (v0.18.0 fix round 4, the runtime
    # lens: back-to-back slivers whose shading normals cancel)
    zone_v = set(released) | set(held)
    weld = list({v for vi in zone_v for f in bm.verts[vi].link_faces for v in f.verts})
    n_weld0 = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=weld, dist=1e-4)
    n_weld = n_weld0 - len(bm.verts)
    # ...and every near-zero-area face the zone's halving left (ledger 0055: College's cut zone, 800 m of kerb seam,
    # left 22 collinear slivers — three points on one line — and one of them on the terrain's open edge at the kerb
    # carried its own corner as a T-junction on its other edge: the kn5 prep's T-junction weld then built the same
    # fan triangle twice and stopped the chain). A sliver is any face under DEGEN_AREA_M2 touching a zone vertex or
    # lying in a zone; dissolved (merged into its neighbours, vertices within DEGEN_DIST_M), re-checked, at most 3 rounds
    n_degen = 0
    for _round in range(3):
        degen = [f for f in bm.faces if f.calc_area() < DEGEN_AREA_M2 and (
            any(v.index in zone_v for v in f.verts)
            or Z.weight(f.calc_center_median().x, f.calc_center_median().y)[0] > 0.0)]
        if not degen:
            break
        n_degen += len(degen)
        bmesh.ops.dissolve_degenerate(bm, dist=DEGEN_DIST_M, edges=list({e for f in degen for e in f.edges}))
    n_degen_left = sum(1 for f in bm.faces if f.calc_area() < DEGEN_AREA_M2 and (
        any(v.index in zone_v for v in f.verts) or Z.weight(f.calc_center_median().x, f.calc_center_median().y)[0] > 0.0))
    mend1 = terrain_mend.mend_vertical_slivers(bm)
    bm.to_mesh(me)
    bm.free()
    me.update()
    # an AUTO cut zone that moved nothing found the graded ground already holding its wall: reported, not fatal (a
    # declared zone that moves nothing is a mistaken declaration)
    idle_auto = [n for n, r in per_zone.items() if r["moved"] == 0 and (zone_rec.get(n) or {}).get("auto")]
    idle = [n for n, r in per_zone.items() if r["moved"] == 0 and n not in idle_auto]
    if idle or bad_poke or bad_face:
        raise SystemExit(f"[release] FATAL: zones that moved nothing {idle}; {len(bad_poke)} released vertices over the "
                         f"deck {bad_poke[:4]}; {len(bad_face)} released faces over a ROAD / CURB surface "
                         f"{bad_face[:4]} — loop.blend NOT saved")

    # 3. rails
    ground = _bvh([ob])
    grd = bpy.data.objects.get("GUARDRAIL")
    gv = [tuple(grd.matrix_world @ v.co) for v in grd.data.vertices] if grd is not None else []
    # the existing rails' plan (their faces, not their vertices: a long rail prism has vertices only at its ends)
    gflat = BVHTree.FromPolygons([(p[0], p[1], 0.0) for p in gv], [tuple(q.vertices) for q in grd.data.polygons])         if gv else None

    def deck_at(x, y, yref):
        hs = _hits(deck, x, y, yref + DECK_WIN_M, yref - DECK_WIN_M)
        return max(hs) if hs else None

    def ground_at(x, y, top):
        hs = _hits(ground, x, y, top, top - 200.0)
        return hs[0] if hs else None

    rails = []
    n_rail_bury = n_rail_jump = n_rail_held = 0
    # the stations are read per SIDE over the UNION of the zones, never per zone (v0.18.0, the view lens: where two zones
    # overlap or abut — College's approach foot / south approach / I-8 span, Lake Murray Blvd's I-8 span / creek — each
    # zone drew its own rail over the shared stations, two prisms 3 cm apart whose end caps stood up as white teeth on
    # the parapet). A station depends only on its s and side, so one shared station list gives one continuous rail.
    def station(s, side, zname):
        """one rail station: the built pavement's outer edge at s on this side and whether drive_test would file a drop
        there (or the ground falls RAIL_FALL_M under the edge) with no rail already holding the car"""
        nonlocal n_rail_held
        k = max(0, min(len(Z.s) - 2, next((i for i in range(len(Z.s) - 1) if Z.s[i + 1] >= s), len(Z.s) - 2)))
        u = (s - Z.s[k]) / max(1e-9, Z.s[k + 1] - Z.s[k])
        cx = Z.P[k][0] + (Z.P[k + 1][0] - Z.P[k][0]) * u
        cy = Z.P[k][1] + (Z.P[k + 1][1] - Z.P[k][1]) * u
        cz = pts[k][1] + (pts[k + 1][1] - pts[k][1]) * u
        tx, ty = Z.T[k]
        nx, ny = -ty * side, tx * side
        hw = Z.W[k] / 2.0
        o, e, ye, ylast = 0.0, None, None, cz
        ended = False
        while o < hw + XS_MAX_M:
            o += XS_STEP_M
            yh = deck_at(cx + nx * o, cy + ny * o, ylast)
            if yh is None:
                if o > hw:
                    ended = True
                    break
                continue
            e, ye, ylast = o, yh, yh
        if not ended:
            e = None                 # still on pavement XS_MAX_M past the half-width (a junction): no edge here
        need = steep = False
        fall = 0.0
        if e is not None:
            # drive_test's excursion rule, read finer than it reads it (it steps 0.5 m from its own centreline,
            # this every EXC_SCAN_M from this one, any 0.5 m pair): the highest surface (pavement or the NEW
            # ground), a fall of more than EXC_DROP_M between two points 0.5 m apart from the nominal edge
            # less 0.5 m out to EXC_BAND_M past the built edge, or the ground RAIL_FALL_M under the edge
            prof = []
            off = max(0.0, hw - 0.5)
            while off <= e + EXC_BAND_M + 0.5 + 1e-6:
                x, y = cx + nx * off, cy + ny * off
                d = deck_at(x, y, ye) if off <= e + 1e-6 else None
                g = ground_at(x, y, ye + 30.0)
                top = max(v for v in (d, g, ye - 50.0) if v is not None)
                prof.append((off, top))
                off += EXC_SCAN_M
            k = int(round(EXC_STEP_M / EXC_SCAN_M))
            for j in range(len(prof) - k):
                if prof[j][0] <= e + EXC_BAND_M and prof[j][1] - prof[j + k][1] > EXC_DROP_M:
                    steep = True
                    break
            gs = [t for o2, t in prof if o2 > e]
            fall = ye - min(gs) if gs else 0.0
            need = steep or fall > RAIL_FALL_M
        if need and e is not None and gflat is not None:
            # a rail already stands between the lane and the lip (a bridge's own barrier between the road and
            # its sidewalk): no car reaches the drop, so no second rail
            o2 = hw - 0.5
            while o2 <= e + 1e-6:
                if gflat.find_nearest((cx + nx * o2, cy + ny * o2, 0.0), RAIL_HELD_M)[0] is not None:
                    need = False
                    n_rail_held += 1
                    break
                o2 += XS_STEP_M
        return {"s": s, "c": (cx, cy), "n": (nx, ny), "t": (tx * side, ty * side), "e": e, "ye": ye,
                "need": need and e is not None, "zones": {zname},
                # past a zone's end only a real embankment edge carries the rail on: a steep fall AND the ground more
                # than RAIL_EXT_FALL_M under the edge (a street's ordinary 1:8 verge is not a hazard to fence)
                "need_ext": need and e is not None and steep and fall > RAIL_EXT_FALL_M}

    by_side = {}
    rail_zones = [z for z in R["zones"] if z.get("rails", True)]      # a declared cut zone (rails false) has no drop
    for zone in rail_zones:
        a, b = float(zone["s_m"][0]), float(zone["s_m"][1])
        for side in zone["sides"]:
            seen = by_side.setdefault(side, {})
            s = a
            while s <= b + 1e-6:
                key = round(s, 3)
                if key in seen:
                    seen[key]["zones"].add(zone["name"])
                else:
                    seen[key] = station(s, side, zone["name"])
                s += RAIL_STEP_M
    # a drop that runs on past a zone's end keeps its rail (v0.18.0 fix round 4, the gates lens: College Ave's approach
    # foot, s 2496-2500, a 3-5 m curtain off the sidewalk with no rail because the stations stopped at the zone's start;
    # the same embankment edge runs back to s ~2401, unguarded since v0.17.1): from every zone end that is not inside
    # another zone on that side, stations continue outward while the drop does (gaps up to RAIL_GAP_M), at most
    # RAIL_EXT_MAX_M, plus RAIL_PAD_M of padding stations past the last one that needs a rail
    n_ext = 0
    for zone in rail_zones:
        a, b = float(zone["s_m"][0]), float(zone["s_m"][1])
        for side in zone["sides"]:
            seen = by_side[side]
            for s0, step, open_end in ((a, -RAIL_STEP_M, side in Z.zones[R["zones"].index(zone)].get("open_a", ())),
                                       (b, RAIL_STEP_M, side in Z.zones[R["zones"].index(zone)].get("open_b", ()))):
                if open_end:
                    continue
                last_need, ext = s0, []
                s = s0 + step
                while abs(s - s0) <= RAIL_EXT_MAX_M + 1e-6:
                    key = round(s, 3)
                    if key in seen or not (Z.s[0] <= s <= Z.s[-1]):
                        break
                    r = station(s, side, zone["name"] + "+ext")
                    if r["e"] is None:
                        break
                    r["need"] = r["need_ext"]
                    ext.append(r)
                    if r["need"]:
                        last_need = s
                    elif abs(s - last_need) > max(RAIL_GAP_M, RAIL_PAD_M):
                        break
                    s += step
                for r in ext:
                    if abs(r["s"] - last_need) <= RAIL_PAD_M + 1e-6 or abs(r["s"] - s0) <= abs(last_need - s0):
                        seen[round(r["s"], 3)] = r
                        n_ext += r["need"]
    for side, seen in by_side.items():
        # contiguous blocks of stations (zones that neither overlap nor abut stay separate rails)
        blocks = []
        for key in sorted(seen):
            r = seen[key]
            if blocks and r["s"] - blocks[-1][-1]["s"] <= RAIL_STEP_M * 1.5:
                blocks[-1].append(r)
            else:
                blocks.append([r])
        for st in blocks:
            runs = []
            for i, r in enumerate(st):
                if not r["need"]:
                    continue
                if runs and (r["s"] - st[runs[-1][1]]["s"]) <= RAIL_GAP_M:
                    runs[-1][1] = i
                else:
                    runs.append([i, i])
            pad = int(round(RAIL_PAD_M / RAIL_STEP_M))
            for i0, i1 in runs:
                i0, i1 = max(0, i0 - pad), min(len(st) - 1, i1 + pad)
                seg = [r for r in st[i0:i1 + 1] if r["e"] is not None]
                # never on top of an existing rail (the I-8 bridge rails)
                keep = []
                for r in seg:
                    px = r["c"][0] + r["n"][0] * (r["e"] - RAIL_IN_M)
                    py = r["c"][1] + r["n"][1] * (r["e"] - RAIL_IN_M)
                    if gflat is not None and gflat.find_nearest((px, py, 0.0), RAIL_DUP_M)[0] is not None:
                        keep.append(None)
                        continue
                    if not r["need"]:
                        # padding only: never into a bank that rises behind the rail (it would stand half buried)
                        bo = r["e"] + RAIL_BASE_M / 2.0 + 0.25
                        gb = ground_at(r["c"][0] + r["n"][0] * bo, r["c"][1] + r["n"][1] * bo, r["ye"] + 30.0)
                        if gb is not None and gb > r["ye"] + RAIL_BURY_M:
                            keep.append(None)
                            n_rail_bury += 1
                            continue
                    keep.append(r)
                cur = []
                for r in keep + [None]:
                    if r is not None:
                        cur.append(r)
                        continue
                    # one smooth line per run: the curb lip's offset median- then mean-filtered; a station whose lip
                    # departs RAIL_JUMP_M from it (a bridge end's curb return) splits the run
                    pieces, piece = [], []
                    if len(cur) >= 2:
                        sm = smooth_offsets([q["e"] - RAIL_IN_M for q in cur])
                        for q, o in zip(cur, sm):
                            if abs((q["e"] - RAIL_IN_M) - o) > RAIL_JUMP_M:
                                n_rail_jump += 1
                                pieces.append(piece)
                                piece = []
                                continue
                            piece.append(q)
                        pieces.append(piece)
                    for pc in pieces:
                        if len(pc) >= 2 and pc[-1]["s"] - pc[0]["s"] >= RAIL_MIN_M:
                            sm = smooth_offsets([q["e"] - RAIL_IN_M for q in pc])
                            rails.append({"zone": "+".join(sorted(set().union(*(q["zones"] for q in pc)))),
                                          "side": side,
                                          "rows": [dict(q, o=o) for q, o in zip(pc, sm)]})
                    cur = []

    # the release rails are their OWN object, 1WALL_guard_release (fix round 4: appended to GUARDRAIL, the rails of fix
    # round 4 took the prep's double-sided 1WALL_guard past the kn5 exporter's 65,535-vertex mesh cap, and the exporter
    # split it into two meshes of one name — verify_kn5: "DUPLICATE physical mesh '1WALL_guard' x2", a mesh AC drops
    # from collision). The name keeps the prep's 1WALL_GUARD material row and the WALL surface (prefix match)
    chunks, chunk_tris = [bmesh.new()], [0]
    bmr = chunks[0]
    n_rail_v0 = 0
    prof = [(-RAIL_BASE_M / 2, -RAIL_SINK_M), (-RAIL_BASE_M / 2, 0.0), (-RAIL_TOP_M / 2, RAIL_H_M),
            (RAIL_TOP_M / 2, RAIL_H_M), (RAIL_BASE_M / 2, 0.0), (RAIL_BASE_M / 2, -RAIL_SINK_M)]
    bad_rail = []
    rail_rep = []
    for rl in rails:
        # one physical mesh per RAIL_CHUNK_TRIS triangles: the exporter writes each triangle corner with its own
        # normal / tangent, and a mesh past 65,536 vertices comes out as two meshes of one name
        est = 10 * (len(rl["rows"]) - 1) + 4
        if chunk_tris[-1] and chunk_tris[-1] + est > RAIL_CHUNK_TRIS:
            chunks.append(bmesh.new())
            chunk_tris.append(0)
            bmr = chunks[-1]
        chunk_tris[-1] += est
        rings = []
        foot = []
        nrms = []
        for r in rl["rows"]:
            (cx, cy), (nx, ny) = r["c"], r["n"]
            bx, by = cx + nx * r["o"], cy + ny * r["o"]
            base = deck_at(bx, by, r["ye"])
            foot.append((bx, by, r["ye"] if base is None else base))
            nrms.append((nx, ny))
        # a sloped end at both ends (v0.18.0, the view lens: a free-standing barrier's square end showed its Jersey
        # profile as a white pointed tooth on the parapet): the top falls to RAIL_END_H_M over the last RAIL_TAPER_M,
        # as a concrete barrier's sloped end treatment does
        ss = [r["s"] for r in rl["rows"]]
        hks = GR.rail_heights(ss, [bool(r["need"]) for r in rl["rows"]], RAIL_TAPER_M)
        for k in range(len(foot)):
            nx, ny = nrms[k]
            bx, by, _b = foot[k]
            # the lowest pavement of its neighbours: the base never steps up and down with the curb's own facets
            base = min(f[2] for f in foot[max(0, k - 1):k + 2]) - 0.05
            hk = hks[k]
            ring = []
            for lat, h in prof:
                hh = h if h <= 0.0 else RAIL_END_H_M + (h - RAIL_END_H_M) * hk
                ring.append(bmr.verts.new((bx + nx * lat, by + ny * lat, base + hh)))
            rings.append(ring)
        for ra, rb in zip(rings, rings[1:]):
            for k in range(len(prof) - 1):
                bmr.faces.new((ra[k], ra[k + 1], rb[k + 1], rb[k]))
        for ring in (rings[0], rings[-1]):
            bmr.faces.new(ring[1:5])
        for ring in rings:
            for v in ring:
                if road_only is not None:
                    h = road_only.ray_cast(Vector((v.co.x, v.co.y, v.co.z + 2.0)), Vector((0, 0, -1)), 3.5)
                    if h[0] is not None:
                        bad_rail.append((round(v.co.x, 1), round(v.co.y, 1)))
        rail_rep.append({"zone": rl["zone"], "side": "left" if rl["side"] > 0 else "right",
                         "s_m": [round(rl["rows"][0]["s"], 1), round(rl["rows"][-1]["s"], 1)],
                         "length_m": round(rl["rows"][-1]["s"] - rl["rows"][0]["s"], 1),
                         "ends_full_height": [hks[0] >= 1.0, hks[-1] >= 1.0]})
    if bad_rail:
        for b in chunks:
            b.free()
        raise SystemExit(f"[release] FATAL: {len(bad_rail)} rail vertices over a ROAD surface {bad_rail[:4]} — "
                         f"loop.blend NOT saved")
    for o in [o for o in bpy.data.objects if o.name.startswith(RAIL_OBJECT)]:
        bpy.data.objects.remove(o, do_unlink=True)
    rail_objects = []
    if rails:
        for k, b in enumerate(chunks):
            name = RAIL_OBJECT if len(chunks) == 1 else f"{RAIL_OBJECT}_{k}"
            rme = bpy.data.meshes.new(name)
            rob = bpy.data.objects.new(name, rme)
            bpy.context.scene.collection.objects.link(rob)
            b.normal_update()
            b.to_mesh(rme)
            if grd is not None and grd.data.materials:
                rme.materials.append(grd.data.materials[0])
            rme.update()
            rail_objects.append([rob.name, len(rme.vertices), chunk_tris[k]])
    for b in chunks:
        b.free()
    rep = {"_doc": "tools/ground_release_blend.py (ledger 0046 v0.18.0 integration fix round)",
           "terrain_vertices": [v0, len(me.vertices)], "edges_halved": n_sub, "no_data_vertices": n_nodata,
           "ramp_toward_the_prep_refinement": n_ramp_ref,
           "zones": per_zone, "batter": {"cut_m_per_m": BATTER_CUT, "fill_m_per_m": BATTER_FILL, "reach_m": BATTER_REACH_M, "cut": n_cut, "fill": n_fill,
                      "straight_bank_between_two_pavements": n_bank, "straight_bank_min_m": GR.STRAIGHT_BANK_MIN_M,
                      "rounded_cut_top": n_round,
                      "zone_cut_reach_m": {n: z.get("cut_reach_m") for n, z in zone_rec.items() if z.get("cut_reach_m")},
                      "zone_round_m": {n: z.get("round_m") for n, z in zone_rec.items() if z.get("round_m")},
                      "zone_cut_slope": {n: z.get("cut_slope") for n, z in zone_rec.items() if z.get("cut_slope")},
                      "raise_only": sorted(n for n, z in zone_rec.items() if z.get("raise_only"))},
           "vertical_slivers_mended": {"after_halving": mend0, "after_heights": mend1},
           "raise_only_under_walk_seated_as_the_prep": n_walk_seat,
           "raise_only_batter_from_the_walk_edge": n_walk_origin,
           "auto_zones_that_moved_nothing": idle_auto,
           "held_pits_lifted_under_the_pavement": n_held_pin, "coincident_faces_removed": n_coinc,
           "coincident_vertices_welded": n_weld, "zero_area_faces_dissolved": n_degen, "zero_area_faces_left": n_degen_left,
           "face_cap": {"vertices_lowered": n_capped, "faces_over_pavement": len(low_of),
                        "faces_still_over_by_an_unreleased_corner": len(pre_face), "those": pre_face[:20]},
           "steep_faces_within_reach": n_steep, "steep_faces_within_reach_in_the_open": len(steep_open),
           "steep_open_sample": steep_open[:40],
           "rail_rows": {"padding_stopped_at_a_rising_bank": n_rail_bury, "split_at_a_lip_jump": n_rail_jump,
                         "already_behind_a_rail": n_rail_held, "stations_past_a_zone_end_over_a_drop": n_ext},
           "rails": rail_rep, "rail_objects": rail_objects}
    (data / "ground_release.report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[release] TERRAIN {v0} -> {len(me.vertices)} verts ({n_sub} edges halved in the zones); " + "; ".join(
        f"{n}: {r['moved']} moved (down <= {r['max_down_m']} m, up <= {r['max_up_m']} m, {r['under_deck']} under a deck)"
        for n, r in per_zone.items()) + f"; {n_held_pin} pits under the pavement lifted to it; batter cut {n_cut} (rounded top {n_round}) / fill {n_fill} / straight bank "
        f"{n_bank}, per-face cap lowered {n_capped} "
        f"vertices on {len(low_of)} faces over the pavement ({len(pre_face)} held over it by an unreleased corner "
        f"{pre_face[:3]}), {n_steep} steep faces within {BATTER_REACH_M} m "
        f"({len(steep_open)} not under a deck); "
        f"{n_ramp_ref} ramp vertices blended toward the prep's refined ground; {len(rail_rep)} rail(s) "
        f"{[(r['zone'], r['side'], r['s_m'], r['ends_full_height']) for r in rail_rep]} on the curb lip ({n_ext} stations "
        f"past a zone's end over a drop); saved loop.blend")


main()
