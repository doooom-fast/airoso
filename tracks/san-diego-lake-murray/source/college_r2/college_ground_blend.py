"""College split, order of work step 4b / 4c: THE GROUND and THE EAST LAMPS. STEP-DESIGN.md has the why.
Run on a blend whose CURB carries the middle (step 3).

    blender --background <loop.blend> --python-exit-code 1 --python college_ground_blend.py -- [--save-as <path>]

The split's ground is RELEASED ground (data/ground_release.json: the prep pins it under pavement but neither feathers nor
refines it), so it has to be right in the scene. Three things:

  the east shelf   The east walk rose with the northbound road (up to 5.55 m); the ground behind it still stood where the
                   one-slab road had it. A strip of ground is ADDED to TERRAIN along rows A0..A1, east of the built east
                   pavement edge: at the edge's road height less GROUND_CLEAR_M out to HOLD_M (under and behind the walk),
                   then falling FILL_SLOPE per metre, until it has gone under the old ground, and from there on it runs
                   BURY_M under the old ground. So where the hill already stands higher (the cut) the old ground shows,
                   where it lies lower a fill runs down to it, and the strip's own outer edge is never in the open.
                   The old ground is not moved: raising its own vertices worked only where it is dense (the first prep
                   run: between v1131 and v1197 it has no vertex within 8 m of the edge, and the walk stood up to 1.9 m
                   over the ground).
  the bank         Old ground inside the bank's footprint (it lay under the one slab) is first cut fine, then pushed
                   UNDER_BANK_M under the lower of the two roads' inner edges wherever it stands higher, so none of it shows through the
                   bank's top or through a road's inner edge (the first prep run: up to 0.35 m over the bank's top, 0.27 m
                   over the southbound road). The bank's own top (step 3) is not touched.
  the east lamps   LIGHTPOST_3, LIGHTPOST_4, LIGHTS_0: every part whose foot stands east of the built line on rows
                   A0..A1 rises by what the road's east edge rose at its place.

Self-checks (exit 1, NOT saved): TERRAIN's old vertices move only inside the bank's footprint and only down; the strip's
vertex and face counts as planned; every lamp part moved straight up as one piece.
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
    """under the split's own footprint: the built road's width on rows A0..A1 (both roads, the bank, the forks)"""
    _co, i_, _d = kd.find((x, y, 0.0))
    if not A0 < i_ + FV0 < A1:
        return False
    o = (x - FX[i_]) * FNX[i_] + (y - FZ[i_]) * FNZ[i_]
    return abs(o) <= FHW[i_] + margin


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
# the bank's own top (step 3): on a row, DECK_INSET inside an inner edge, CURB_H + 0.005 over that edge
own = inside & (np.abs(al) <= 0.02) & (
    ((np.abs(off - (nbw_o + DECK_INSET)) <= 0.02) & (np.abs(w[:, 2] - (nbw_y + CURB_H + 0.005)) <= 0.01))
    | ((np.abs(off - (sbe_o - DECK_INSET)) <= 0.02) & (np.abs(w[:, 2] - (sbe_y + CURB_H + 0.005)) <= 0.01)))
if int(own.sum()) != 2 * (TAIL - NOSE - 1):
    die(f"TERRAIN: {int(own.sum())} vertices look like the bank's top, not {2 * (TAIL - NOSE - 1)}")
down = inside & ~own & (w[:, 2] > plane - UNDER_BANK_M)
new_z = w[:, 2].copy()
new_z[down] = (plane - UNDER_BANK_M)[down]
moved = np.nonzero(down)[0]
co = w.copy()
co[:, 2] = new_z
terrain.data.vertices.foreach_set("co", co.reshape(-1))
terrain.data.update()
delta = world(terrain) - w
if np.abs(delta[:, :2]).max() > 0 or (delta[:, 2] > 1e-9).any() or set(np.nonzero(delta[:, 2] < 0)[0].tolist()) != set(moved.tolist()):
    die("TERRAIN: a vertex outside the bank's footprint moved, or one moved up or sideways")
rep["bank"] = {"old_ground_vertices_in_its_footprint": int((inside & ~own).sum()), "pushed_under_the_lower_inner_edge": int(len(moved)),
               "by_m": {"max": round(float(-delta[moved, 2].min()), 2) if len(moved) else 0.0,
                        "median": round(float(np.median(-delta[moved, 2])), 2) if len(moved) else 0.0},
               "bank_top_vertices_left_alone": int(own.sum())}

# ====================================================================================================== the east shelf
bm = bmesh.new()
bm.from_mesh(terrain.data)
old_bvh = BVHTree.FromBMesh(bm)                             # the old ground (after the bank's push), before the strip


def old_ground(x, y):
    hit = old_bvh.ray_cast(Vector((x, y, 5000.0)), Vector((0.0, 0.0, -1.0)))
    return hit[0].z if hit[0] is not None else None


rows = list(range(A0, A1 + 1))
grid, buried_at, open_end = {}, [], 0
for v in rows:
    i = v - FV0
    edge_y = float(EDGE[i])
    hw = float(FHW[i])
    col, buried = [], False
    for d in COLS_M:
        x, y = FX[i] + FNX[i] * (-hw - d), FZ[i] + FNZ[i] * (-hw - d)
        tgt = edge_y - GROUND_CLEAR_M - max(0.0, d - HOLD_M) * FILL_SLOPE
        og = old_ground(x, y)
        if og is not None and not buried and d > 0.0 and tgt <= og - UNDER_M:
            buried = True
            buried_at.append(d)
        z = min(tgt, og - BURY_M) if (buried and og is not None) else tgt
        col.append(bm.verts.new((x, y, z)))
    if not buried:
        open_end += 1
    grid[v] = col
n_faces = 0
for v in rows[:-1]:
    a, b = grid[v], grid[v + 1]
    for c in range(len(COLS_M) - 1):
        bm.faces.new((a[c], a[c + 1], b[c + 1], b[c]))
        n_faces += 1
bm.to_mesh(terrain.data)
bm.free()
terrain.data.update()
w2 = world(terrain)
if len(w2) != n_old + len(rows) * len(COLS_M) or not np.array_equal(w2[:n_old], w[:n_old] + delta):
    die("TERRAIN: the strip's vertex count is off, or an old vertex moved while it was added")
rep["east_shelf"] = {"rows": [A0, A1], "columns_past_the_edge_m": [COLS_M[0], COLS_M[-1]], "vertices_added": len(rows) * len(COLS_M),
                     "faces_added": n_faces, "rows_where_it_goes_under_the_old_ground": len(buried_at),
                     "where_m_past_the_edge": {"min": min(buried_at), "median": float(np.median(buried_at)), "max": max(buried_at)} if buried_at else None,
                     "rows_where_it_never_does_within_reach": open_end}

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
