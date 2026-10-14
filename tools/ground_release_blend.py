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
  2b. BATTER (fix round 2, 2026-10-13: the view lens's 3-4 m vertical grass curtains beside Alvarado, where the built
     sidewalk is wider than the real one and the real bank falls away under its outer half, and where a real 3.6 m
     terrace climbs at ~54 deg from Alvarado to College's south approach): a released vertex beside the pavement stands
     no higher than min over every ROAD / CURB face within BATTER_REACH_M of (its height + BATTER_CUT * d) (45 deg up
     from the LOWEST nearby pavement) and, beside pavement on the ground (within ON_GROUND_M), no lower than
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
     RAIL_H_M tall) stands on the outer lip of the curb, padded RAIL_PAD_M past each run. It is appended to GUARDRAIL
     (the prep's 1WALL_guard: physical, double-sided, the loop's own I-8 bridge rail material), never where GUARDRAIL
     already stands within RAIL_DUP_M.
     The rail's line is smoothed along its run (a 5-station median, then a 5-station mean of the curb lip's offset, its
     base the lowest pavement of its neighbours) and split where the lip jumps more than RAIL_JUMP_M (a bridge end's
     curb return), so it never kinks into shards; padding never runs it into a bank rising behind it (RAIL_BURY_M).
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

SUBDIV_M = 2.5        # [invented] zone terrain edges are halved down to this
CLEAR_M = 0.02        # build_kn5_loop.GROUND_CLEAR: ground stands this far under the deck
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
EDGE_SUBDIV_M = 1.0   # [invented] zone edges crossing the pavement's outer edge are halved down to this
TOP_NZ = 0.7          # [invented] a ROAD / CURB face is pavement to stand on when its normal is this close to up
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


def _release_module():
    spec = importlib.util.spec_from_file_location("_airoso_ground_release", AIROSO / "tools" / "ground_release.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
    flat = BVHTree.FromPolygons([(p[0], p[1], 0.0) for p in dv], dfaces)   # the pavement's plan, for edge distances
    road_only = _bvh([road_obj]) if road_obj is not None else None
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
            if e.calc_length() <= SUBDIV_M:
                continue
            a, b = e.verts[0].co, e.verts[1].co
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
            if e.calc_length() <= EDGE_SUBDIV_M:
                continue
            a, b = e.verts[0].co, e.verts[1].co
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
    # 2. released heights
    per_zone = {z["name"]: {"moved": 0, "max_down_m": 0.0, "max_up_m": 0.0, "under_deck": 0} for z in R["zones"]}
    bad_poke = []
    n_nodata = 0
    bm.verts.ensure_lookup_table()
    released = {}                     # vertex index -> (under a deck, zone name, height before this step)
    held = {}                         # vertex index -> height: in a bank zone but under the pavement (not released)
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
                held[v.index] = z    # in the zone, under the pavement: kept (the prep pins it, as in v0.17.1)
                continue
            t = D
        else:
            if under:
                t = min(D, min(hs) - CLEAR_M)
                per_zone[zone["name"]]["under_deck"] += 1
            else:
                t = D
        released[v.index] = (under, zone["name"], z)
        v.co.z = z + w * (t - z)
        if under:                     # in a zone's ramp the blend may not leave the ground over the deck either
            v.co.z = min(v.co.z, min(hs) - CLEAR_M)
        if under and v.co.z > min(hs) - CLEAR_M + 1e-4:
            bad_poke.append((round(x, 1), round(y, 1), round(v.co.z, 2), round(min(hs), 2)))

    def pave_at(x, y):
        """the LOWEST upward ROAD / CURB surface at (x, y), or None"""
        hs = _hits(top, x, y, 10000.0, -1000.0)
        return min(hs) if hs else None

    # 2b. the batter, from EVERY pavement face within reach (not only the nearest: between a low road and a high one
    # 8 m apart — Alvarado under College's south approach — the low road's edge is what the bank must not out-climb):
    # the vertex stands no higher than min(h_f + BATTER_CUT * d_f) and, beside pavement on the ground after step 2,
    # no lower than max(h_f - BATTER_FILL * d_f); h_f a face's mean height, d_f its plan distance. The cut wins.
    gr1 = BVHTree.FromBMesh(bm)
    face_h = [sum(dv[i][2] for i in f) / len(f) for f in dfaces]
    on_ground = {}

    def grounded(fi):
        if fi not in on_ground:
            f = dfaces[fi]
            cx = sum(dv[i][0] for i in f) / len(f)
            cy = sum(dv[i][1] for i in f) / len(f)
            g = gr1.ray_cast(Vector((cx, cy, face_h[fi] - 0.005)), Vector((0, 0, -1)), 500.0)[0]
            on_ground[fi] = g is not None and face_h[fi] - g.z <= ON_GROUND_M
        return on_ground[fi]

    n_cut = n_fill = 0
    for vi, (under, zname, z0) in released.items():
        if under:
            continue
        v = bm.verts[vi]
        near = flat.find_nearest_range((v.co.x, v.co.y, 0.0), BATTER_REACH_M)
        if not near:
            continue
        hi = min(face_h[fi] - CLEAR_M + BATTER_CUT * d for _q, _n, fi, d in near)
        los = [face_h[fi] - CLEAR_M - BATTER_FILL * d for _q, _n, fi, d in near if grounded(fi)]
        nz = v.co.z
        if los and nz < max(los):
            nz = max(los)
            n_fill += 1
        if nz > hi:
            nz = hi
            n_cut += 1
        v.co.z = nz

    # 2c. per-face cap: no face with a released vertex stands over a ROAD / CURB surface anywhere over its area
    rel_faces = {f for vi in released for f in bm.verts[vi].link_faces}

    def face_low_pave(f):
        co = [tuple(v.co) for v in f.verts]
        cx = sum(c[0] for c in co) / len(co)
        cy = sum(c[1] for c in co) / len(co)
        r = max(math.hypot(c[0] - cx, c[1] - cy) for c in co)
        if flat.find_nearest((cx, cy, 0.0), r + 0.01)[0] is None:
            return None
        low = None
        for x, y in face_samples(co, FACE_STEP_M):
            h = pave_at(x, y)
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
            if v.index in released and v.co.z > low - CLEAR_M:
                v.co.z = low - CLEAR_M
                n_capped += 1
    # the check reads each face as the prep will leave it: an unreleased corner under the pavement is held under its
    # lowest sheet (build_kn5_loop's anti-poke); a face still over the pavement because of an UNRELEASED corner beside
    # it was so before this step (lowering the released corners cannot have raised it) and is reported, not fatal
    bad_face, pre_face = [], []
    for f in low_of:
        co = []
        unrel_high = False
        for v in f.verts:
            z = v.co.z
            if v.index not in released:
                pv_ = pave_at(v.co.x, v.co.y)
                if pv_ is not None:
                    z = min(z, pv_ - CLEAR_M)
                if z > low_of[f] - CLEAR_M + FACE_TOL_M:
                    unrel_high = True
            co.append((v.co.x, v.co.y, z))
        for x, y in face_samples(co, FACE_STEP_M):
            h = pave_at(x, y)
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
    bm.to_mesh(me)
    bm.free()
    me.update()
    idle = [n for n, r in per_zone.items() if r["moved"] == 0]
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
    for zone in R["zones"]:
        a, b = float(zone["s_m"][0]), float(zone["s_m"][1])
        for side in zone["sides"]:
            st = []
            s = a
            while s <= b + 1e-6:
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
                need = False
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
                            need = True
                            break
                    gs = [t for o2, t in prof if o2 > e]
                    if gs and ye - min(gs) > RAIL_FALL_M:
                        need = True
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
                st.append({"s": s, "c": (cx, cy), "n": (nx, ny), "t": (tx * side, ty * side), "e": e, "ye": ye,
                           "need": need and e is not None})
                s += RAIL_STEP_M
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
                            rails.append({"zone": zone["name"], "side": side,
                                          "rows": [dict(q, o=o) for q, o in zip(pc, sm)]})
                    cur = []

    bmr = bmesh.new()
    if grd is not None:
        bmr.from_mesh(grd.data)
    n_rail_v0 = len(bmr.verts)
    prof = [(-RAIL_BASE_M / 2, -RAIL_SINK_M), (-RAIL_BASE_M / 2, 0.0), (-RAIL_TOP_M / 2, RAIL_H_M),
            (RAIL_TOP_M / 2, RAIL_H_M), (RAIL_BASE_M / 2, 0.0), (RAIL_BASE_M / 2, -RAIL_SINK_M)]
    bad_rail = []
    rail_rep = []
    for rl in rails:
        rings = []
        foot = []
        for r in rl["rows"]:
            (cx, cy), (nx, ny) = r["c"], r["n"]
            bx, by = cx + nx * r["o"], cy + ny * r["o"]
            base = deck_at(bx, by, r["ye"])
            foot.append((bx, by, r["ye"] if base is None else base))
        for k, r in enumerate(rl["rows"]):
            nx, ny = r["n"]
            bx, by, _b = foot[k]
            # the lowest pavement of its neighbours: the base never steps up and down with the curb's own facets
            base = min(f[2] for f in foot[max(0, k - 1):k + 2]) - 0.05
            ring = []
            for lat, h in prof:
                ring.append(bmr.verts.new((bx + nx * lat, by + ny * lat, base + h)))
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
                         "length_m": round(rl["rows"][-1]["s"] - rl["rows"][0]["s"], 1)})
    if bad_rail:
        bmr.free()
        raise SystemExit(f"[release] FATAL: {len(bad_rail)} rail vertices over a ROAD surface {bad_rail[:4]} — "
                         f"loop.blend NOT saved")
    if rails:
        if grd is None:
            gme = bpy.data.meshes.new("GUARDRAIL")
            grd = bpy.data.objects.new("GUARDRAIL", gme)
            bpy.context.scene.collection.objects.link(grd)
        bmr.normal_update()
        bmr.to_mesh(grd.data)
        grd.data.update()
    bmr.free()
    rep = {"_doc": "tools/ground_release_blend.py (ledger 0046 v0.18.0 integration fix round)",
           "terrain_vertices": [v0, len(me.vertices)], "edges_halved": n_sub, "no_data_vertices": n_nodata,
           "zones": per_zone, "batter": {"cut_m_per_m": BATTER_CUT, "fill_m_per_m": BATTER_FILL, "reach_m": BATTER_REACH_M, "cut": n_cut, "fill": n_fill},
           "face_cap": {"vertices_lowered": n_capped, "faces_over_pavement": len(low_of),
                        "faces_still_over_by_an_unreleased_corner": len(pre_face), "those": pre_face[:20]},
           "steep_faces_within_reach": n_steep, "steep_faces_within_reach_in_the_open": len(steep_open),
           "steep_open_sample": steep_open[:40],
           "rail_rows": {"padding_stopped_at_a_rising_bank": n_rail_bury, "split_at_a_lip_jump": n_rail_jump,
                         "already_behind_a_rail": n_rail_held},
           "rails": rail_rep}
    (data / "ground_release.report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[release] TERRAIN {v0} -> {len(me.vertices)} verts ({n_sub} edges halved in the zones); " + "; ".join(
        f"{n}: {r['moved']} moved (down <= {r['max_down_m']} m, up <= {r['max_up_m']} m, {r['under_deck']} under a deck)"
        for n, r in per_zone.items()) + f"; batter cut {n_cut} / fill {n_fill}, per-face cap lowered {n_capped} "
        f"vertices on {len(low_of)} faces over the pavement ({len(pre_face)} held over it by an unreleased corner "
        f"{pre_face[:3]}), {n_steep} steep faces within {BATTER_REACH_M} m "
        f"({len(steep_open)} not under a deck); "
        f"{len(rail_rep)} rail(s) "
        f"{[(r['zone'], r['side'], r['s_m']) for r in rail_rep]} on the curb lip; saved loop.blend")


main()
