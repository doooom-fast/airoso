"""College split, order of work step 4b / 4c: THE GROUND and THE EAST LAMPS. STEP-DESIGN.md has the why.
Run on a blend whose CURB carries the middle (step 3).

    blender --background <loop.blend> --python-exit-code 1 --python college_ground_blend.py -- [--save-as <path>]

The split's ground is RELEASED ground (data/ground_release.json: the prep pins it under pavement but neither feathers nor
refines it), so it has to be right in the scene. Five things:

  the east shelf   The east walk rose with the northbound road (up to 5.55 m); the ground behind it still stood where the
                   one-slab road had it. A strip of ground is ADDED to TERRAIN along rows A0..A1, east of the built east
                   pavement edge: at the edge's road height less GROUND_CLEAR_M out to HOLD_M (under and behind the walk),
                   then falling FILL_SLOPE per metre, until it has gone under the old ground. There it ends: a row runs
                   on only as far as the row beside it needs (college_shelf.py), BURY_M under the old ground and no
                   deeper. So where the hill already stands higher (the cut) the old ground shows, where it lies lower a
                   fill runs down to it, and the strip's own outer edge is never in the open.
                   (0.20.5's first rehearsal: every row ran on to 19.5 m at min(the falling fill, the old ground less
                   BURY_M), up to 19.4 m down inside the hill: kn5_ground_check, 202 double-sheet cells.)
  the bank         Old ground inside the bank's footprint (it lay under the one slab) is first cut fine, then set
                   UNDER_BANK_M under the lower road's inner edge beside that road, and UNDER_BANK_M under the higher
                   road's inner edge (or under the bank's top, whichever is lower) beside that one, so none of it shows
                   through the bank's top or through a road's inner edge (the first prep run: up to 0.35 m over the
                   bank's top, 0.27 m over the southbound road), and none stands as a wall under the higher road's curb.
                   The bank's own top (step 3) is not touched.
  one sheet        Old ground that lies wholly under one of this step's own surfaces (the bank's top, the shelf where it
                   is in the open) is taken OUT of TERRAIN: it could not be seen, and it was a second sheet of ground
                   under the first. What is left of it at a seam (a face that reaches out from under the surface) is
                   set TUCK_M under the shelf, so no hidden wall of old ground stands under the walk.
  under the roads  Old ground under the split's own pavement (ROAD) is set where the prep will pin it: the road's surface
                   less GROUND_CLEAR_M. The prep splits every long edge near the road BEFORE it pins; left at the old
                   slab's height, this ground stood up to 5.5 m under the seam beside it, and the prep left the middles
                   of those edges half-way down, just outside the road (the second scratch run).
  the east lamps   LIGHTPOST_3, LIGHTPOST_4, LIGHTS_0: every part whose foot stands east of the built line on rows
                   A0..A1 rises by what the road's east edge rose at its place.

Self-checks (exit 1, NOT saved): TERRAIN's old vertices move only inside the bank's footprint, under the split's own
pavement or at a seam under the shelf, never sideways; every face taken out lay wholly under one of this step's surfaces; the strip's vertex and face
counts as planned; no 2 m cell of ground near the split holds heights more than SHEET_SPREAD_M apart that did not
before (the lens of scripts/ac/kn5_ground_check.py, its own number); every lamp part moved straight up as one piece.
Idempotent: a TERRAIN that carries the custom property `college_split_ground` is left alone."""
import json
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector, kdtree
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import college_shelf  # noqa: E402  (the shelf's column rule, pure: tests/tools/test_college_shelf_0055.py)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SAVE_AS = argv[argv.index("--save-as") + 1] if "--save-as" in argv else None
S = json.loads((HERE / "college_split.data.json").read_text(encoding="utf-8"))
R, F = S["rows"], S["frame"]
A0, A1 = S["mainline"]["from_v"], S["mainline"]["to_v"]
NOSE, TAIL = R["v"][0], R["v"][-1]
LIFT, CURB_H, DECK_INSET = 0.10, 0.18, 0.22
GROUND_CLEAR_M = 0.02      # the prep's own clearance of pinned ground under the deck (build_kn5_loop GROUND_CLEAR)
HOLD_M = 3.5               # [invented] the ground holds the edge's height this far past it: the walk is 3.08 m wide
FILL_SLOPE = 0.5           # [invented] past that a fill may fall this much per metre (1 in 2, an earth embankment)
BURY_M = 0.30              # [invented] once under the old ground, the strip runs this far under it
UNDER_M = 0.10             # [invented] the strip counts as under the old ground when it lies this far below it
COLS_M = [0.0, 1.0, 2.0, 3.1, HOLD_M] + [HOLD_M + 1.0 * k for k in range(1, 17)]     # metres past the edge; the last is 19.5
UNDER_BANK_M = 0.10        # [invented] old ground inside the bank goes at least this far under the lower of the two inner edges
DENSE_M = 1.5              # [invented] old ground under the split's footprint is cut to edges of at most this
DENSE_MARGIN_M = 1.0       # [invented] ...and this far past the built pavement edge on both sides
COVER_M = 0.10             # [invented] old ground lies under one of this step's surfaces when that stands this far over it (= UNDER_M)
TUCK_M = 0.05              # [invented] old ground left at a seam under the shelf is set this far under it
COVER_TOL_M = 1e-4         # a height read back off the mesh is a 32-bit float: a vertex set COVER_M under a surface reads a few microns short
CLEAR_M = 0.02             # a point of a face counts as hidden when a surface stands this far over it (= GROUND_CLEAR_M)
NEAR_EDGE_M = DENSE_M + DECK_INSET + 0.03    # old ground this near a road's inner edge can share a face with ground under that
#                            road or its curb (edges are DENSE_M at most; the bank's top starts DECK_INSET in)
SHEET_SPREAD_M = 12.0      # scripts/ac/kn5_ground_check.py: ground heights further apart than this in one 2 m cell = two sheets
LAMPS = ("LIGHTPOST_3", "LIGHTPOST_4", "LIGHTS_0")

FV0 = F["from_v"]
FX, FY, FZ = np.array(F["x"]), np.array(F["y"]), np.array(F["z"])
FNX, FNZ, FHW = np.array(F["nx"]), np.array(F["nz"]), np.array(F["half_w"])
K = {v: k for k, v in enumerate(R["v"])}
FK = {v: k for k, v in enumerate(R["fork_v"])}
O = R["offsets_m"]


def die(msg):
    print(f"[college_ground] FAIL: {msg}")
    sys.exit(1)


# per row of the frame: the road's east edge height now, and (rows of the two roads) the two inner edges
EDGE = FY + LIFT
SBE_O = np.full(len(FX), np.nan)
SBE_Y = np.full(len(FX), np.nan)
NBW_O = np.full(len(FX), np.nan)
NBW_Y = np.full(len(FX), np.nan)
for v in range(A0 + 1, A1):
    EDGE[v - FV0] = R["nb_east"][K[v]][1] if v in K else R["fork_y"][FK[v]][2]
for v, k in K.items():
    SBE_O[v - FV0], SBE_Y[v - FV0] = O["sb_east"][k], R["sb_east"][k][1]
    NBW_O[v - FV0], NBW_Y[v - FV0] = O["nb_west"][k], R["nb_west"][k][1]
RISE = EDGE - (FY + LIFT)


def world(ob):
    if not np.allclose(np.array(ob.matrix_world), np.eye(4)):
        die(f"{ob.name} has a transform")
    co = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


BX0, BX1 = FX.min() - 60.0, FX.max() + 60.0
BY0, BY1 = FZ.min() - 60.0, FZ.max() + 60.0


def classify(w, arrays=()):
    """per vertex in the built line's frame: station (-1 = not near), offset (+ west), along (m past the row), and each
    of `arrays` (per-row values) interpolated along the road at its place"""
    st = np.full(len(w), -1, dtype=np.int64)
    off = np.zeros(len(w))
    al = np.zeros(len(w))
    vals = [np.full(len(w), np.nan) for _ in arrays]
    box = np.nonzero((w[:, 0] > BX0) & (w[:, 0] < BX1) & (w[:, 1] > BY0) & (w[:, 1] < BY1))[0]
    for c0 in range(0, len(box), 20000):
        idx = box[c0:c0 + 20000]
        d2 = (w[idx, None, 0] - FX[None, :]) ** 2 + (w[idx, None, 1] - FZ[None, :]) ** 2
        k = d2.argmin(axis=1)
        dx, dy = w[idx, 0] - FX[k], w[idx, 1] - FZ[k]
        a = dx * FNZ[k] - dy * FNX[k]                       # along: the tangent is (nz, -nx)
        k2 = np.clip(k + np.where(a >= 0, 1, -1), 0, len(FX) - 1)
        seg = np.hypot(FX[k2] - FX[k], FZ[k2] - FZ[k])
        t = np.clip(np.abs(a) / np.where(seg > 0, seg, 1.0), 0.0, 1.0)
        st[idx] = k + FV0
        off[idx] = dx * FNX[k] + dy * FNZ[k]
        al[idx] = a
        for arr, out in zip(arrays, vals):
            a0, a1 = arr[k], arr[k2]
            out[idx] = np.where(np.isnan(a1), a0, a0 * (1 - t) + a1 * t)
    return (st, off, al, *vals)


terrain = bpy.data.objects.get("TERRAIN")
curb = bpy.data.objects.get("CURB")
if terrain is None or curb is None:
    die("no TERRAIN / CURB")
if not curb.get("college_split"):
    die("CURB does not carry the middle: run college_middle_blend.py (step 3) first")
if terrain.get("college_split_ground"):
    print(f"[college_ground] TERRAIN already carries the ground ({terrain['college_split_ground']}): nothing to do, nothing saved")
    sys.exit(0)
rep = {}

# ================================================================================ the east shelf, planned before the cut
# Planned against the ground as it stands: cutting an edge does not move the surface, and the bank's push below moves
# nothing east of the northbound road. The cut and the clean-up below then know where the shelf lies in the open.
w_start = world(terrain)
bm = bmesh.new()
bm.from_mesh(terrain.data)
plan_bvh = BVHTree.FromBMesh(bm)
bm.free()


def old_ground(x, y):
    hit = plan_bvh.ray_cast(Vector((x, y, 5000.0)), Vector((0.0, 0.0, -1.0)))
    return hit[0].z if hit[0] is not None else None


rows = list(range(A0, A1 + 1))
PLAN, firsts, deepest = {}, [], 0.0
for v in rows:
    i = v - FV0
    edge_y, hw = float(EDGE[i]), float(FHW[i])
    xy = [(FX[i] + FNX[i] * (-hw - d), FZ[i] + FNZ[i] * (-hw - d)) for d in COLS_M]
    tgt = [edge_y - GROUND_CLEAR_M - max(0.0, d - HOLD_M) * FILL_SLOPE for d in COLS_M]
    og = [old_ground(x, y) for x, y in xy]
    zs, first = college_shelf.columns(tgt, og, COLS_M, UNDER_M, BURY_M)
    PLAN[v] = [(x, y, z) for (x, y), z in zip(xy, zs)]
    firsts.append(first)
LAST = dict(zip(rows, college_shelf.row_ends(firsts, len(COLS_M))))
buried_at = [COLS_M[f] for f in firsts if f is not None]
open_end = sum(1 for f in firsts if f is None)
EAST_EXT = np.zeros(len(FX))                      # per row of the frame: how far past the east edge the shelf reaches
for v in rows:
    EAST_EXT[v - FV0] = COLS_M[LAST[v]]
    for c in range(LAST[v] + 1):
        o_ = old_ground(PLAN[v][c][0], PLAN[v][c][1])
        if o_ is not None:
            deepest = max(deepest, o_ - PLAN[v][c][2])
shelf_pts, shelf_polys, shelf_at = [], [], {}
for v in rows:
    for c in range(LAST[v] + 1):
        shelf_at[v, c] = len(shelf_pts)
        shelf_pts.append(Vector(PLAN[v][c]))
for v in rows[:-1]:
    for c in range(min(LAST[v], LAST[v + 1])):
        shelf_polys.append((shelf_at[v, c], shelf_at[v, c + 1], shelf_at[v + 1, c + 1], shelf_at[v + 1, c]))
shelf_bvh = BVHTree.FromPolygons(shelf_pts, shelf_polys)


def over(bvh, x, y, z):
    """how far a surface stands over (x, y, z); None where it has nothing over that place"""
    hit = bvh.ray_cast(Vector((x, y, 5000.0)), Vector((0.0, 0.0, -1.0)))
    return None if hit[0] is None else hit[0].z - z


# ====================================================================================== the bank: old ground under it
# The old ground under the one slab is a few large triangles (17 vertices in the whole bank's footprint). The prep
# pins ground under pavement at the ground's own vertices only, cuts long edges, and leaves every vertex it makes inside
# the released bank at the height the old slab's ground had. Measured on the second prep run: ground through the
# southbound road at 332 of 2,439 samples (up to 0.41 m): triangles from under one road to under the other, prep-made
# vertices in the bank 0.3 m over the southbound road's inner edge, and 10 m triangles sagging over the road's twist.
# So the old ground is first cut to edges of at most DENSE_M under the whole footprint of the split (both roads, the
# bank, the forks): the prep then pins a vertex every metre or so, and none is left for it to make inside the bank.
w = world(terrain)
st, off, al, sbe_o, sbe_y, nbw_o, nbw_y = classify(w, (SBE_O, SBE_Y, NBW_O, NBW_Y))
own0 = (st > NOSE) & (st < TAIL) & ~np.isnan(sbe_o) & (np.abs(al) <= 0.02) & (
    ((np.abs(off - (nbw_o + DECK_INSET)) <= 0.02) & (np.abs(w[:, 2] - (nbw_y + CURB_H + 0.005)) <= 0.01))
    | ((np.abs(off - (sbe_o - DECK_INSET)) <= 0.02) & (np.abs(w[:, 2] - (sbe_y + CURB_H + 0.005)) <= 0.01)))
hw_ = FHW[np.clip(st - FV0, 0, len(FHW) - 1)]
near = np.nonzero((st >= A0) & (st <= A1) & (np.abs(off) <= hw_ + 6.0))[0]
bm = bmesh.new()
bm.from_mesh(terrain.data)
bm.verts.ensure_lookup_table()
# the bank's own top is told apart by a TAG ON THE MESH (an integer vertex layer): a Python reference to a vertex does
# not survive bmesh.ops.subdivide_edges (every one read invalid after the first round, and the later rounds cut the
# bank's top to pieces: the third prep run)
# both tags are made before either is used, and their handles read back by name: making or removing a layer can
# re-seat the others
bm.verts.layers.int.new("college_bank_top")
bm.verts.layers.int.new("college_touch")
OWN = bm.verts.layers.int["college_bank_top"]
TOUCH = bm.verts.layers.int["college_touch"]
bm.verts.ensure_lookup_table()
for i in np.nonzero(own0)[0]:
    bm.verts[int(i)][OWN] = 1
if int(own0.sum()) != 2 * (TAIL - NOSE - 1):
    die(f"TERRAIN: {int(own0.sum())} vertices look like the bank's top before the cut, not {2 * (TAIL - NOSE - 1)}")


def own_faces():
    return sum(1 for f in bm.faces if all(x[OWN] for x in f.verts))


own_faces0 = own_faces()
kd = kdtree.KDTree(len(FX))
for i_ in range(len(FX)):
    kd.insert((FX[i_], FZ[i_], 0.0), i_)
kd.balance()


def in_zone(x, y, margin):
    """under the split's own footprint: the built road's width on rows A0..A1 (both roads, the bank, the forks), and
    east of it as far as the shelf reaches (the old ground under the shelf is cut fine too, so what is left of it at a
    seam is small)"""
    _co, i_, _d = kd.find((x, y, 0.0))
    if not A0 < i_ + FV0 < A1:
        return False
    o = (x - FX[i_]) * FNX[i_] + (y - FZ[i_]) * FNZ[i_]
    return -(FHW[i_] + EAST_EXT[i_]) - margin <= o <= FHW[i_] + margin


SAMPLES = (4, 2, 6, 1, 3, 5, 7)            # eighths along an edge; the middle first


def crosses(ca, cb):
    """does the edge run under the split's footprint? A long edge is tested at seven points along it, not at its middle
    only: one that starts in the bank and ends 60 m away has its middle outside, and the prep would put its own
    vertices on it inside the released bank."""
    for k_ in SAMPLES:
        q = ca.lerp(cb, k_ / 8.0)
        if in_zone(q.x, q.y, DENSE_MARGIN_M):
            return True
    return False


# Round 0 looks at every edge that has an end near the split (within WIDE_M of the built line on its rows); from then
# on only at what the cuts touched. The vertices in play carry a second tag on the mesh, TOUCH: the two ends of every
# edge cut, the vertex each cut makes, and every vertex of a many-sided face that was triangulated.
WIDE_M = 90.0
lim2 = DENSE_M * DENSE_M
wide = np.nonzero((st >= A0 - 4) & (st <= A1 + 4) & (np.abs(off) <= hw_ + WIDE_M))[0]
for i in wide:
    bm.verts[int(i)][TOUCH] = 1
n_split = n_rounds = 0
per_round = []
for _round in range(24):
    seen, todo = set(), []
    for v_ in bm.verts:
        if not v_[TOUCH]:
            continue
        for e in v_.link_edges:
            if e.index in seen:
                continue
            seen.add(e.index)
            a, b = e.verts
            if (a.co - b.co).length_squared <= lim2 or (a[OWN] and b[OWN]):
                continue
            if crosses(a.co, b.co):
                todo.append(e)
    if not todo:
        break
    # from here on only the cut's own neighbourhood is in play
    for v_ in bm.verts:
        if v_[TOUCH]:
            v_[TOUCH] = 0
    for e in todo:
        e.verts[0][TOUCH] = 1
        e.verts[1][TOUCH] = 1
    # use_single_edge / use_grid_fill: a triangle with one or all of its edges cut is split into triangles by the cut
    # itself. Left as a many-sided face and triangulated afterwards it fans out in long diagonals, which are cut again,
    # and the loop does not end (24 rounds were not enough).
    res = bmesh.ops.subdivide_edges(bm, edges=todo, cuts=1, use_single_edge=True, use_grid_fill=True)
    per_round.append(len(todo))
    n_split += len(todo)
    n_rounds += 1
    for g in res.get("geom", []):
        if isinstance(g, bmesh.types.BMVert) and g.is_valid:
            g[TOUCH] = 1
    # the many-sided faces a cut leaves are triangulated in the SAME round, so the diagonals that makes are cut in the
    # next one (triangulated once at the end, they came out as 10 m edges across the bank: the fifth prep run)
    ngons = []
    for v_ in bm.verts:
        if v_[TOUCH]:
            for f in v_.link_faces:
                if len(f.verts) > 3 and not f.tag and not all(x[OWN] for x in f.verts):
                    f.tag = True
                    ngons.append(f)
    for f in ngons:
        f.tag = False
        for x in f.verts:
            x[TOUCH] = 1
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons)
    bm.edges.index_update()
else:
    die(f"TERRAIN: the old ground under the split still has long edges after 24 rounds of cutting (edges cut per round: {per_round})")
left = [f for f in bm.faces if len(f.verts) > 3 and not all(x[OWN] for x in f.verts)]
if left:
    bmesh.ops.triangulate(bm, faces=left)
bm.verts.layers.int.remove(TOUCH)
OWN = bm.verts.layers.int["college_bank_top"]          # removing a layer re-seats the others
own_faces1 = own_faces()
if own_faces0 != TAIL - NOSE - 2 or own_faces1 != own_faces0:
    die(f"TERRAIN: the bank's top had {own_faces0} faces before the cut and {own_faces1} after it (planned {TAIL - NOSE - 2}, untouched)")
bm.verts.layers.int.remove(OWN)
bm.to_mesh(terrain.data)
bm.free()
terrain.data.update()
rep["old_ground_cut_finer_under_the_split"] = {"edges_split": n_split, "per_round": per_round, "to_at_most_m": DENSE_M}
w = world(terrain)
n_old = len(w)
st, off, al, sbe_o, sbe_y, nbw_o, nbw_y = classify(w, (SBE_O, SBE_Y, NBW_O, NBW_Y))
inside = (st > NOSE) & (st < TAIL) & ~np.isnan(sbe_o) & (off <= sbe_o + 0.5) & (off >= nbw_o - 0.5)
# the level old ground may reach inside the bank: UNDER_BANK_M under the LOWER of the two inner edges, flat across.
# (A plane rising from one inner edge to the other was tried first: the southbound road's inner edge lies up to 0.5 m
# under the old slab, the bank is steep, and old ground 1.5 m in stayed 0.27 m over that edge, under the 'plane':
# the triangle from there to the pinned ground under the road stood 0.16 m through the road's last half metre.)
plane = np.minimum(sbe_y, nbw_y)
high_y = np.maximum(sbe_y, nbw_y)
# the bank's own top (step 3): on a row, DECK_INSET inside an inner edge, CURB_H + 0.005 over that edge
own = inside & (np.abs(al) <= 0.02) & (
    ((np.abs(off - (nbw_o + DECK_INSET)) <= 0.02) & (np.abs(w[:, 2] - (nbw_y + CURB_H + 0.005)) <= 0.01))
    | ((np.abs(off - (sbe_o - DECK_INSET)) <= 0.02) & (np.abs(w[:, 2] - (sbe_y + CURB_H + 0.005)) <= 0.01)))
if int(own.sum()) != 2 * (TAIL - NOSE - 1):
    die(f"TERRAIN: {int(own.sum())} vertices look like the bank's top, not {2 * (TAIL - NOSE - 1)}")
# the bank's top as a surface to measure under
bm = bmesh.new()
bm.from_mesh(terrain.data)
bm.verts.ensure_lookup_table()
own_idx = set(np.nonzero(own)[0].tolist())
top_pts, top_polys, top_at, seen_f = [], [], {}, set()
for i in sorted(own_idx):
    for f in bm.verts[i].link_faces:
        if f.index in seen_f:
            continue
        seen_f.add(f.index)
        if not all(x.index in own_idx for x in f.verts):
            continue
        poly = []
        for x in f.verts:
            if x.index not in top_at:
                top_at[x.index] = len(top_pts)
                top_pts.append(x.co.copy())
            poly.append(top_at[x.index])
        top_polys.append(tuple(poly))
bm.free()
if len(top_polys) != TAIL - NOSE - 2:
    die(f"TERRAIN: the bank's top reads as {len(top_polys)} faces, not {TAIL - NOSE - 2}")
top_bvh = BVHTree.FromPolygons(top_pts, top_polys)
# Beside the LOWER road the old ground is set flat under that road's inner edge (up or down: 0.20.5's first rehearsal read
# it up to 0.66 m under the southbound road's edge where that road stands over the old slab). Beside the HIGHER road it
# is set under that road's inner edge, or under the bank's top where that is lower: left at the lower road's level it
# stood as a wall of up to 6 m under the higher road's curb, from the ground the prep pins under that road down to it
# (the same rehearsal: the road's edge read 5.18 m over the ground). In between it is only pushed down, as before.
ds, dn = sbe_o - off, off - nbw_o                 # metres into the bank from the southbound / the northbound inner edge
sb_low = sbe_y <= nbw_y
d_low, d_high = np.where(sb_low, ds, dn), np.where(sb_low, dn, ds)
bankv = inside & ~own
near_low = bankv & (d_low <= NEAR_EDGE_M)
near_high = bankv & ~near_low & (d_high <= NEAR_EDGE_M)
between = bankv & ~near_low & ~near_high & (w[:, 2] > plane - UNDER_BANK_M)
new_z = w[:, 2].copy()
new_z[near_low] = (plane - UNDER_BANK_M)[near_low]
new_z[between] = (plane - UNDER_BANK_M)[between]
for i in np.nonzero(near_high)[0]:
    c_ = high_y[i] - UNDER_BANK_M
    t_ = over(top_bvh, w[i, 0], w[i, 1], 0.0)
    new_z[i] = c_ if t_ is None else min(c_, t_ - UNDER_BANK_M)
moved = np.nonzero(np.abs(new_z - w[:, 2]) > 1e-9)[0]
co = w.copy()
co[:, 2] = new_z
terrain.data.vertices.foreach_set("co", co.reshape(-1))
terrain.data.update()
delta = world(terrain) - w
dz = delta[:, 2]
was_moved = np.zeros(len(w), dtype=bool)
was_moved[moved] = True
if (np.abs(delta[:, :2]).max() > 0 or (np.abs(dz) > 1e-6)[~bankv].any() or (dz > 1e-6)[between].any()
        or (np.abs(dz) > 1e-6)[~was_moved].any()):
    die("TERRAIN: a vertex outside the bank's footprint moved, one moved sideways, or one between the two edges moved up")
rep["bank"] = {"old_ground_vertices_in_its_footprint": int(bankv.sum()),
               "beside_the_lower_road": {"vertices": int(near_low.sum()),
                                         "set_m": [round(float(dz[near_low].min()), 2), round(float(dz[near_low].max()), 2)] if near_low.any() else None},
               "beside_the_higher_road": {"vertices": int(near_high.sum()),
                                          "set_m": [round(float(dz[near_high].min()), 2), round(float(dz[near_high].max()), 2)] if near_high.any() else None},
               "between_pushed_down": {"vertices": int(between.sum()), "by_m_max": round(float(-dz[between].min()), 2) if between.any() else 0.0},
               "bank_top_vertices_left_alone": int(own.sum())}

# =============================================================== under the two roads: the ground where the prep pins it
# engine-july build_kn5_loop._conform_and_reseat: first every ground edge near the road longer than CORRIDOR_EDGE_M
# (4.5 m, measured in space) is split, then every ground vertex under 1ROAD pavement is set to that surface less
# GROUND_CLEAR, and released ground beside the road is left alone. So an edge from old ground under the raised road
# (still at the old slab's height here) to ground this step sets beside it is split while it still stands on end, and
# its middle, if it falls outside the road, stays half-way down. The ground under the split's own roads is therefore
# set here to what the pin will make of it; the pin then finds it in place.
hw1 = FHW[np.clip(st - FV0, 0, len(FHW) - 1)]
road_obs = [o for o in bpy.data.objects if o.type == "MESH" and (o.name == "ROAD" or o.name.upper().startswith("1ROAD"))]
if not road_obs:
    die("no ROAD in the scene")
road_pts, road_polys = [], []
for o in road_obs:
    wr = world(o)
    near_r = (wr[:, 0] > BX0) & (wr[:, 0] < BX1) & (wr[:, 1] > BY0) & (wr[:, 1] < BY1)
    for poly in o.data.polygons:
        vs = list(poly.vertices)
        if not near_r[vs].any():
            continue
        k0 = len(road_pts)
        road_pts.extend(Vector(wr[i_]) for i_ in vs)
        road_polys.append(tuple(range(k0, k0 + len(vs))))
road_bvh = BVHTree.FromPolygons(road_pts, road_polys)
w_bank = world(terrain)
under = np.nonzero((st > A0) & (st < A1) & ~own & (np.abs(off) <= hw1 + 1.0))[0]
pin_z = w_bank[:, 2].copy()
n_pin, pin_up, pin_down = 0, 0.0, 0.0
for i in under:
    hit = road_bvh.ray_cast(Vector((float(w_bank[i, 0]), float(w_bank[i, 1]), 4000.0)), Vector((0.0, 0.0, -1.0)))
    if hit[0] is None:
        continue
    t_ = hit[0].z - GROUND_CLEAR_M
    if abs(t_ - pin_z[i]) > 1e-9:
        pin_up, pin_down = max(pin_up, t_ - pin_z[i]), max(pin_down, pin_z[i] - t_)
        pin_z[i] = t_
        n_pin += 1
co = w_bank.copy()
co[:, 2] = pin_z
terrain.data.vertices.foreach_set("co", co.reshape(-1))
terrain.data.update()
chk = world(terrain) - w_bank
if np.abs(chk[:, :2]).max() > 0 or int((np.abs(chk[:, 2]) > 1e-6).sum()) > n_pin:
    die("TERRAIN: a vertex moved sideways, or more moved than stand under the split's pavement")
rep["under_the_roads"] = {"old_ground_vertices_set_to_the_road_less_m": GROUND_CLEAR_M, "vertices": n_pin,
                          "by_m": {"up_max": round(float(pin_up), 2), "down_max": round(float(pin_down), 2)}}

# ================================================================= one sheet: old ground under this step's own surfaces
w1 = world(terrain)
cand = np.nonzero((st >= A0) & (st <= A1) & ~own & (off <= hw1 + 1.0) & (off >= -(hw1 + COLS_M[-1] + 1.0)))[0]
bm = bmesh.new()
bm.from_mesh(terrain.data)
bm.verts.ensure_lookup_table()
cover = {}                                        # the vertex -> which surface stands COVER_M or more over it
for i in cand:
    x_, y_, z_ = (float(q) for q in w1[i])
    t_ = over(top_bvh, x_, y_, z_)
    if t_ is not None and t_ >= COVER_M - COVER_TOL_M:
        cover[bm.verts[int(i)]] = "top"
        continue
    s_ = over(shelf_bvh, x_, y_, z_)
    if s_ is not None and s_ >= COVER_M - COVER_TOL_M:
        cover[bm.verts[int(i)]] = "shelf"


def hidden(q):
    for bvh in (top_bvh, shelf_bvh):
        d_ = over(bvh, q.x, q.y, q.z)
        if d_ is not None and d_ >= CLEAR_M:
            return True
    return False


# a face goes when its three corners are covered and its edges' middles and its own middle are hidden too
drop, seen_f = [], set()
for v_ in cover:
    for f in v_.link_faces:
        if f.index in seen_f:
            continue
        seen_f.add(f.index)
        if len(f.verts) != 3 or not all(x in cover for x in f.verts):
            continue
        a, b, c = (x.co for x in f.verts)
        if all(hidden(q) for q in ((a + b) / 2.0, (b + c) / 2.0, (c + a) / 2.0, (a + b + c) / 3.0)):
            drop.append(f)
n_v0, n_f0 = len(bm.verts), len(bm.faces)
drop_by = {"top": 0, "shelf": 0}
for f in drop:
    drop_by["top" if any(cover[x] == "top" for x in f.verts) else "shelf"] += 1
if drop:
    bmesh.ops.delete(bm, geom=drop, context="FACES")
alone = [x for x in cover if x.is_valid and not x.link_faces]
if alone:
    bmesh.ops.delete(bm, geom=alone, context="VERTS")
if n_f0 - len(bm.faces) != len(drop):
    die(f"TERRAIN: {n_f0 - len(bm.faces)} faces went, {len(drop)} were to go")
# what is left under the shelf at a seam: TUCK_M under it (only where every edge at the vertex is a cut one: a vertex of
# a long face reaches ground far outside the shelf, which this step does not reshape)
n_seam, n_long, seam_rise, long_at = 0, 0, 0.0, []
for x in cover:
    if not x.is_valid or cover[x] != "shelf":
        continue
    if any((e.verts[0].co.xy - e.verts[1].co.xy).length > DENSE_M + 1e-6 for e in x.link_edges):
        n_long += 1
        long_at.append((round(x.co.x, 1), round(x.co.y, 1), round(over(shelf_bvh, x.co.x, x.co.y, x.co.z) or 0.0, 2)))
        continue
    s_ = over(shelf_bvh, x.co.x, x.co.y, 0.0)
    if s_ is None:
        continue
    seam_rise = max(seam_rise, s_ - TUCK_M - x.co.z)
    x.co.z = s_ - TUCK_M
    n_seam += 1
n_left_top = sum(1 for x in cover if x.is_valid and cover[x] == "top")
rep["one_sheet"] = {"old_faces_taken_out": {"under_the_banks_top": drop_by["top"], "under_the_shelf": drop_by["shelf"]},
                    "old_vertices_taken_out": n_v0 - len(bm.verts),
                    "left_at_a_seam_under_the_shelf": {"set_under_it": n_seam, "by_m_max": round(seam_rise, 2),
                                                       "on_a_long_edge_left_as_they_were": n_long,
                                                       "those_x_y_and_m_under_the_shelf": sorted(long_at)[:20]},
                    "left_at_a_seam_under_the_banks_top": n_left_top}

# ====================================================================================================== the east shelf
n_old = len(bm.verts)
grid = {}
for v in rows:
    grid[v] = [bm.verts.new(q) for q in PLAN[v][:LAST[v] + 1]]
n_faces = 0
for v in rows[:-1]:
    a, b = grid[v], grid[v + 1]
    for c in range(min(LAST[v], LAST[v + 1])):
        bm.faces.new((a[c], a[c + 1], b[c + 1], b[c]))
        n_faces += 1
n_add = sum(LAST[v] + 1 for v in rows)
bm.to_mesh(terrain.data)
bm.free()
terrain.data.update()
w2 = world(terrain)
if len(w2) != n_old + n_add or n_faces != len(shelf_polys):
    die("TERRAIN: the strip's vertex or face count is off")
# the lens the first rehearsal failed (scripts/ac/kn5_ground_check.py: ground heights more than SHEET_SPREAD_M apart in
# one 2 m cell of plan), on the ground near the split, before this step and after it


def sheets(pts):
    m_ = (pts[:, 0] > BX0) & (pts[:, 0] < BX1) & (pts[:, 1] > BY0) & (pts[:, 1] < BY1)
    q = pts[m_]
    key = np.floor(q[:, 0] / 2.0).astype(np.int64) * 4000003 + np.floor(q[:, 1] / 2.0).astype(np.int64)
    order = np.argsort(key, kind="stable")
    k_, z_ = key[order], q[order, 2]
    starts = np.r_[0, np.nonzero(np.diff(k_))[0] + 1]
    spread = np.maximum.reduceat(z_, starts) - np.minimum.reduceat(z_, starts)
    return dict(zip(k_[starts].tolist(), spread.tolist()))


sh0, sh1 = sheets(w_start), sheets(w2)
two = [k_ for k_, sp in sh1.items() if sp > SHEET_SPREAD_M and sh0.get(k_, 0.0) <= SHEET_SPREAD_M]
if two:
    die(f"TERRAIN: {len(two)} cells of 2 m near the split hold ground heights more than {SHEET_SPREAD_M} m apart that did not before "
        f"(the worst {max(sh1[k_] for k_ in two):.1f} m): a second sheet of ground under the first")
rep["east_shelf"] = {"rows": [A0, A1], "columns_past_the_edge_m": [COLS_M[0], COLS_M[-1]], "vertices_added": n_add,
                     "faces_added": n_faces, "rows_where_it_goes_under_the_old_ground": len(buried_at),
                     "where_m_past_the_edge": {"min": min(buried_at), "median": float(np.median(buried_at)), "max": max(buried_at)} if buried_at else None,
                     "rows_where_it_never_does_within_reach": open_end,
                     "a_row_ends_m_past_the_edge": {"min": min(COLS_M[LAST[v]] for v in rows), "max": max(COLS_M[LAST[v]] for v in rows)},
                     "deepest_under_the_old_ground_m": round(float(deepest), 2),
                     "cells_2m_over_12m_spread_near_the_split": {"before": sum(1 for sp in sh0.values() if sp > SHEET_SPREAD_M),
                                                                 "after": sum(1 for sp in sh1.values() if sp > SHEET_SPREAD_M)}}

# ============================================================================================================= lamps
for name in LAMPS:
    ob = bpy.data.objects.get(name)
    if ob is None:
        rep[name] = "missing"
        continue
    me = ob.data
    wl = world(ob)
    n = len(wl)
    parent = np.arange(n)

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    e = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", e)
    for a_, b_ in e.reshape(-1, 2):
        ra, rb = find(a_), find(b_)
        if ra != rb:
            parent[ra] = rb
    root = np.array([find(i) for i in range(n)])
    stl = classify(wl)[0]
    zl = wl[:, 2].copy()
    lifted, parts, worst = 0, 0, 0.0
    for r in np.unique(root):
        m = root == r
        if (stl[m] < 0).all():
            continue
        # the part's foot: its lowest vertices' place (a post's base); an arm or a head is placed by its own lowest
        # point: both stand on the same side of the line as their post
        low = m & (wl[:, 2] <= wl[m, 2].min() + 0.05)
        foot = wl[low].mean(axis=0)
        s1, o1, _a1, r1 = classify(foot[None, :], (RISE,))
        if s1[0] <= A0 or s1[0] >= A1 or o1[0] >= 0.0 or abs(r1[0]) < 1e-6:
            continue                                        # outside the zone, on the west side, or no rise there
        zl[m] += r1[0]
        lifted += int(m.sum())
        parts += 1
        worst = max(worst, float(r1[0]))
    if parts:
        co = wl.copy()
        co[:, 2] = zl
        me.vertices.foreach_set("co", co.reshape(-1))
        me.update()
        chk = world(ob) - wl
        if np.abs(chk[:, :2]).max() > 0 or (chk[:, 2] < -1e-9).any():
            die(f"{name}: a lamp part moved sideways or down")
    rep[name] = {"parts_raised": parts, "vertices": lifted, "largest_rise_m": round(worst, 2)}

terrain["college_split_ground"] = json.dumps(rep)
print("[college_ground] " + json.dumps(rep))
if SAVE_AS:
    bpy.ops.wm.save_as_mainfile(filepath=SAVE_AS, copy=True)
    print(f"[college_ground] saved a copy: {SAVE_AS}")
else:
    bpy.ops.wm.save_mainfile()
    print("[college_ground] saved")
