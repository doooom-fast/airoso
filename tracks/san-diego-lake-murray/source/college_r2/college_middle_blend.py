"""College split, order of work step 3: THE MIDDLE (the old island out, the bank's island in, the east walk, paint).
STEP-DESIGN.md, "Step 3, the plan", has the why. Run on a blend whose ROAD already carries the split (step 2).

    blender --background <loop.blend> --python-exit-code 1 --python college_middle_blend.py -- [--save-as <path>]

3a, out (everything told apart by station and offset in the BUILT line's frame, college_split.data.json `frame`):
  CURB       the old island's faces on the segments between rows CUT0 and CUT1; the two islands that stay get the
             median tool's own nose (their last three rows taper to a half width of 0.25 m and are capped)
  TERRAIN    the old island's grass top on the same segments (the tapered rows' top vertices follow the taper)
  GUARDRAIL  the College island's beam and posts from three rows before CUT0 on
  SCRUB      every clump on the old island from three rows before CUT0 to three rows after CUT1
  the two street-only median objects, whole
  YLINE, MARKINGS   every quad with both ends on rows A0..A1
3b, in:
  CURB       the bank's island: tools/author_median_blend.py's ring of six per station, its west side on the southbound
             road's inner edge and its east side on the northbound road's, each at its own road's height; a pointed
             nose from the point where the two roads meet up to the first ring, at both ends
             the EAST WALK's vertices on rows A0+1..A1-1 rise with the road's east edge (section unchanged)
  TERRAIN    the bank's grass top, one quad per segment between the two curb tops
  GUARDRAIL  nothing. No rail stands on the bank: the 2024 lidar shows none along the northbound road's inner edge
             (college_bank_rail.g10.json: 0 of 53 bins rail-like, 0.43 returns per metre in the 0.5-1.2 m band where a
             W-beam gives about 45 per bin) and none along the southbound's (the control)
  SCRUB      nothing. The bank's plants are the lidar's measured tops, planted as TreeFX data (college_bank_plants.py)
  YLINE, MARKINGS   paint on the tilted forks (the built pattern, the double yellow opening into a gore at the point where
             the roads part) and on the two one-way roads (yellow inside the median edge, white inside the outer edge,
             dashed dividers every 3.65 m counted from the yellow; the built clip rule)

Nothing else is touched. The ground under and beside all this, the lamps and the data are step 4.
Self-checks (exit 1, NOT saved): every count as planned; in CURB and TERRAIN no vertex moves but the east walk's and the
tapered rows'; every new ring and paint vertex stands on its own road's side of the bank.
Idempotent: a CURB that carries the custom property `college_split` is left alone."""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SAVE_AS = argv[argv.index("--save-as") + 1] if "--save-as" in argv else None
S = json.loads((HERE / "college_split.data.json").read_text(encoding="utf-8"))
R, F = S["rows"], S["frame"]
A0, A1 = S["mainline"]["from_v"], S["mainline"]["to_v"]
NOSE, TAIL = R["v"][0], R["v"][-1]
CUT0, CUT1 = 1116, 1476            # the last / first row of the islands that stay (the real island: v1104-1116, v1476-...)
LIFT = 0.10
# tools/author_median_blend.py's own numbers
CURB_H, LIP_IN, DECK_INSET, NOSE_HALF, NOSE_VERTS, SHRUB_EVERY_M = 0.18, 0.15, 0.22, 0.25, 3, 3.2
ISLAND_HALF = 3.5                  # the built island's half width on College (median_bands: 7.0 m)
# scripts-v021/geometry/ribbon.py lane_markings' own numbers
LINE_W, EDGE_INSET, LANE_W, DASH_ON, DASH_GAP, MAX_LANES, PAINT_LIFT = 0.12, 0.55, 3.65, 3.0, 9.0, 6, 0.015
STREET_OBJECTS = ("1KERB_sidewalk_streetonly_median", "1WALL_guard_streetonly_median")

FV0 = F["from_v"]
FX, FY, FZ = np.array(F["x"]), np.array(F["y"]), np.array(F["z"])
FNX, FNZ, FHW, FS = np.array(F["nx"]), np.array(F["nz"]), np.array(F["half_w"]), np.array(F["s_m"])
K = {v: k for k, v in enumerate(R["v"])}
FK = {v: k for k, v in enumerate(R["fork_v"])}
OFF = R["offsets_m"]


def die(msg):
    print(f"[college_middle] FAIL: {msg}")
    sys.exit(1)


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def plan(v, off):
    """Blender (x, y) of the point at offset `off` (+ west) on the BUILT row v"""
    i = v - FV0
    return FX[i] + FNX[i] * off, FZ[i] + FNZ[i] * off


def built_y(v):
    return float(FY[v - FV0]) + LIFT


def sections(v):
    """the road's cross-sections at row v as lists of (offset, surface height), west to east: one on a fork row, two
    (southbound, northbound) on a row of the two roads"""
    hw = float(FHW[v - FV0])
    if v in K:
        k = K[v]
        return [[(OFF["sb_west"][k], R["sb_west"][k][1]), (OFF["sb_line"][k], R["sb_line"][k][1]), (OFF["sb_east"][k], R["sb_east"][k][1])],
                [(OFF["nb_west"][k], R["nb_west"][k][1]), (OFF["nb_line"][k], R["nb_line"][k][1]), (OFF["nb_east"][k], R["nb_east"][k][1])]]
    if v in FK:
        yw, yc, ye = R["fork_y"][FK[v]]
        return [[(hw, yw), (0.0, yc), (-hw, ye)]]
    return [[(hw, built_y(v)), (0.0, built_y(v)), (-hw, built_y(v))]]


def surface(v, off):
    """the road surface's height at (row v, offset): linear between the row's own vertices; None off the pavement"""
    for sec in sections(v):
        if sec[0][0] + 1e-6 >= off >= sec[-1][0] - 1e-6:
            for (o0, y0), (o1, y1) in zip(sec, sec[1:]):
                if o0 + 1e-6 >= off >= o1 - 1e-6:
                    return y0 if abs(o0 - o1) < 1e-9 else y0 + (y1 - y0) * (o0 - off) / (o0 - o1)
    return None


def world(ob):
    if not np.allclose(np.array(ob.matrix_world), np.eye(4)):
        die(f"{ob.name} has a transform")
    co = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


BX0, BX1 = FX.min() - 45.0, FX.max() + 45.0
BY0, BY1 = FZ.min() - 45.0, FZ.max() + 45.0


def classify(w):
    """per vertex: station (absolute; -1 = not near the frame), offset (+ west), along (m past the row), height over
    the built LINE, in the built line's frame"""
    st = np.full(len(w), -1, dtype=np.int64)
    off = np.zeros(len(w))
    al = np.zeros(len(w))
    h = np.zeros(len(w))
    box = np.nonzero((w[:, 0] > BX0) & (w[:, 0] < BX1) & (w[:, 1] > BY0) & (w[:, 1] < BY1))[0]
    for c0 in range(0, len(box), 20000):
        idx = box[c0:c0 + 20000]
        d2 = (w[idx, None, 0] - FX[None, :]) ** 2 + (w[idx, None, 1] - FZ[None, :]) ** 2
        k = d2.argmin(axis=1)
        dx, dy = w[idx, 0] - FX[k], w[idx, 1] - FZ[k]
        st[idx] = k + FV0
        off[idx] = dx * FNX[k] + dy * FNZ[k]
        al[idx] = dx * FNZ[k] - dy * FNX[k]            # the tangent is (nz, -nx) for the left normal (nx, nz)
        h[idx] = w[idx, 2] - FY[k]
    return st, off, al, h


def open_bm(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    return bm


def close_bm(bm, ob):
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def drop_faces(bm, vert_ok, face_ok=None):
    """delete every face all of whose vertices pass vert_ok (a bool array by ORIGINAL index) and that passes face_ok
    (given the face's vertex indices); orphaned vertices go with them. Returns how many faces went."""
    gone = []
    for f in bm.faces:
        ids = [x.index for x in f.verts]
        if all(vert_ok[i] for i in ids) and (face_ok is None or face_ok(ids)):
            gone.append(f)
    if gone:
        bmesh.ops.delete(bm, geom=gone, context="FACES")
    return len(gone)


def need(name):
    ob = bpy.data.objects.get(name)
    if ob is None:
        die(f"no object {name}")
    return ob


road, curb, terrain, rail, yline, marks = (need(n) for n in ("ROAD", "CURB", "TERRAIN", "GUARDRAIL", "YLINE", "MARKINGS"))
scrub = bpy.data.objects.get("SCRUB")          # the median tool joins its shrubs into SCRUB; a scene without one has none
if not road.get("college_split"):
    die("ROAD does not carry the split: run college_split_blend.py (step 2) first")
if curb.get("college_split"):
    print(f"[college_middle] CURB already carries the middle ({curb['college_split']}): nothing to do, nothing saved")
    sys.exit(0)
rep = {"removed_faces": {}, "added_faces": {}}

# ============================================================================================================ CURB
w = world(curb)
st, off, al, h = classify(w)
onrow = (st >= 0) & (np.abs(al) <= 0.3)
isl = onrow & (np.abs(off) <= ISLAND_HALF + 0.1) & (h >= 0.05) & (h <= 0.31)
rows_isl = {}
for i in np.nonzero(isl)[0]:
    rows_isl.setdefault(int(st[i]), []).append(int(i))
for r in list(range(CUT0 - NOSE_VERTS, CUT0 + 1)) + list(range(CUT1, CUT1 + NOSE_VERTS + 1)):
    if len(rows_isl.get(r, [])) != 6:
        die(f"CURB: the island has {len(rows_isl.get(r, []))} vertices on row v{r}, not a ring of 6")
north_end = CUT1
while len(rows_isl.get(north_end + 1, [])) == 6:
    north_end += 1
if north_end - CUT1 + 1 < 2 * NOSE_VERTS:
    die(f"CURB: the island north of the split is only rows v{CUT1}..v{north_end}: too short for a nose at each end")
hw_arr = FHW[np.clip(st - FV0, 0, len(FHW) - 1)]
walk_e = onrow & (st > A0) & (st < A1) & (off <= -hw_arr + 0.02) & (off >= -hw_arr - 3.3)
if int(walk_e.sum()) != 4 * (A1 - A0 - 1):
    die(f"CURB: {int(walk_e.sum())} east-walk vertices on rows v{A0 + 1}..v{A1 - 1}, not 4 a row ({4 * (A1 - A0 - 1)})")
bm = open_bm(curb)
nv0 = len(bm.verts)
# an id on the mesh itself (an integer vertex layer): the check that nothing else moved must not lean on Python
# references to vertices, which Blender does not keep across every edit
OID = bm.verts.layers.int.new("college_orig_id")
for x in bm.verts:
    x[OID] = x.index + 1
ring_at ={r: sorted((bm.verts[i] for i in rows_isl[r]), key=lambda x, o=off: o[x.index])
           for r in list(range(CUT0 - NOSE_VERTS + 1, CUT0 + 1)) + list(range(CUT1, CUT1 + NOSE_VERTS))}
walk_verts = [(bm.verts[int(i)], int(st[i])) for i in np.nonzero(walk_e)[0]]
st_l = st.tolist()
rep["removed_faces"]["CURB"] = drop_faces(
    bm, isl, lambda ids: min(st_l[i] for i in ids) >= CUT0 and max(st_l[i] for i in ids) <= CUT1
    and not (len({st_l[i] for i in ids}) == 1 and st_l[ids[0]] in (CUT0, CUT1)))
moved_curb = set()
# the tool's nose on the two islands that stay: half widths 2.417, 1.333, 0.25 toward the end; then the end cap
tapers = {}
for j in range(NOSE_VERTS):
    half = NOSE_HALF + (ISLAND_HALF - NOSE_HALF) * j / NOSE_VERTS
    tapers[CUT0 - j] = half
    tapers[CUT1 + j] = half
for r, half in tapers.items():
    for vert, o in zip(ring_at[r], (-half, -half + 0.04, -half + LIP_IN, half - LIP_IN, half - 0.04, half)):
        x, y = plan(r, o)
        vert.co.x, vert.co.y = x, y
        moved_curb.add(vert)
z = ring_at[CUT0]
bm.faces.new((z[3], z[2], z[1], z[0]))
bm.faces.new((z[5], z[4], z[3], z[0]))
a = ring_at[CUT1]
bm.faces.new((a[0], a[1], a[2], a[3]))
bm.faces.new((a[0], a[3], a[4], a[5]))
n_new = 4
# the east walk rises with the road's east edge
dz_e = {}
for v in range(A0 + 1, A1):
    dz_e[v] = (R["nb_east"][K[v]][1] if v in K else R["fork_y"][FK[v]][2]) - built_y(v)
for vert, v in walk_verts:
    vert.co.z += dz_e[v]
    moved_curb.add(vert)
# the bank's island: rings on rows NOSE+1..TAIL-1, a pointed nose at each end
rings = {}
for v in range(NOSE + 1, TAIL):
    k = K[v]
    oe, ow = OFF["nb_west"][k], OFF["sb_east"][k]
    ye, yw = R["nb_west"][k][1], R["sb_east"][k][1]
    if ow - oe < 2 * LIP_IN + 0.1:
        die(f"v{v}: the bank is {ow - oe:.2f} m wide, too narrow for the island's ring")
    ring = []
    for o, y in ((oe, ye - 0.02), (oe + 0.04, ye + CURB_H), (oe + LIP_IN, ye + CURB_H),
                 (ow - LIP_IN, yw + CURB_H), (ow - 0.04, yw + CURB_H), (ow, yw - 0.02)):
        x, yy = plan(v, o)
        ring.append(bm.verts.new((x, yy, y)))
    rings[v] = ring
for v in range(NOSE + 1, TAIL - 1):
    ra, rb = rings[v], rings[v + 1]
    for p, q in ((0, 1), (1, 2), (3, 4), (4, 5)):
        bm.faces.new((ra[p], ra[q], rb[q], rb[p]))
        n_new += 1
for end, first in ((NOSE, NOSE + 1), (TAIL, TAIL - 1)):
    k = K[end]
    x, yy = plan(end, OFF["sb_east"][k])
    apex = bm.verts.new((x, yy, R["sb_east"][k][1] - 0.02))
    rb = rings[first]
    for p, q in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5)):
        bm.faces.new((apex, rb[q], rb[p]) if end == NOSE else (rb[p], rb[q], apex))
        n_new += 1
rep["added_faces"]["CURB"] = n_new
moved_ids = {x[OID] for x in moved_curb if x.is_valid}
if len(moved_ids) != len(moved_curb):
    die(f"CURB: {len(moved_curb) - len(moved_ids)} references to moved vertices were lost")
strays = survivors = 0
for x in bm.verts:
    oid = x[OID]
    if oid:
        survivors += 1
        if oid not in moved_ids and max(abs(x.co[c] - w[oid - 1, c]) for c in range(3)) > 1e-5:
            strays += 1
if strays:
    die(f"CURB: {strays} vertices moved that are neither the east walk's nor a tapered row's")
bm.verts.layers.int.remove(OID)
rep["CURB"] = {"old_vertices_checked_unmoved": survivors - len(moved_ids), "island_rows_tapered": sorted(tapers), "east_walk_vertices_raised": len(walk_verts),
               "east_walk_rise_m": [round(min(dz_e.values()), 3), round(max(dz_e.values()), 3)],
               "island_north_of_the_split": [CUT1, north_end], "bank_rings": len(rings)}
close_bm(bm, curb)

# ========================================================================================================= TERRAIN
w = world(terrain)
st, off, al, h = classify(w)
# the island's top: on a row, inside the island, at exactly the tool's height over the line (the island is 4.4 to 7 m wide
# on College, so its top stands at different offsets from row to row; the ground under the slab lies lower)
deck = (st >= 0) & (np.abs(al) <= 0.3) & (np.abs(off) <= ISLAND_HALF - DECK_INSET + 0.03) & (np.abs(h - (LIFT + CURB_H + 0.005)) <= 0.012)
rows_deck = {}
for i in np.nonzero(deck)[0]:
    rows_deck.setdefault(int(st[i]), []).append(int(i))
bm = open_bm(terrain)
nt0 = len(bm.verts)
deck_at = {}
for r, half in tapers.items():
    ids = rows_deck.get(r, [])
    if len(ids) != 2:
        die(f"TERRAIN: the island's top has {len(ids)} vertices on row v{r}, not 2")
    deck_at[r] = sorted((bm.verts[i] for i in ids), key=lambda x, o=off: o[x.index])
st_l = st.tolist()
rep["removed_faces"]["TERRAIN (the old island's top)"] = drop_faces(
    bm, deck, lambda ids: min(st_l[i] for i in ids) >= CUT0 and max(st_l[i] for i in ids) <= CUT1)
moved_terrain = 0
for r, half in tapers.items():
    di = max(0.05, half - DECK_INSET)
    for vert, o in zip(deck_at[r], (-di, di)):
        x, y = plan(r, o)
        vert.co.x, vert.co.y = x, y
        moved_terrain += 1
dk = {}
for v in range(NOSE + 1, TAIL):
    k = K[v]
    oe, ow = OFF["nb_west"][k], OFF["sb_east"][k]
    xe, ye_ = plan(v, oe + DECK_INSET)
    xw, yw_ = plan(v, ow - DECK_INSET)
    dk[v] = (bm.verts.new((xe, ye_, R["nb_west"][k][1] + CURB_H + 0.005)), bm.verts.new((xw, yw_, R["sb_east"][k][1] + CURB_H + 0.005)))
n_new = 0
for v in range(NOSE + 1, TAIL - 1):
    (e0, w0), (e1, w1) = dk[v], dk[v + 1]
    bm.faces.new((e0, w0, w1, e1))
    n_new += 1
rep["added_faces"]["TERRAIN (the bank's top)"] = n_new
rep["TERRAIN"] = {"top_vertices_tapered": moved_terrain}
close_bm(bm, terrain)

# ======================================================================================================= GUARDRAIL
w = world(rail)
st, off, al, h = classify(w)
on_line = (st >= CUT0 - NOSE_VERTS + 1) & (np.abs(al) <= 0.3) & (np.abs(off) <= 0.3) & (h >= 0.2) & (h <= 1.15)
bm = open_bm(rail)
rep["removed_faces"]["GUARDRAIL"] = drop_faces(bm, on_line)
rep["added_faces"]["GUARDRAIL"] = 0
rep["GUARDRAIL"] = {"beam": "none: no rail on the 2024 lidar on either inner edge (college_bank_rail.g10.json)", "posts": 0}
close_bm(bm, rail)

# =========================================================================================================== SCRUB
if scrub is None:
    rep["SCRUB"] = "no SCRUB object in this scene: no shrub stood on the old island here, none planted"
else:
    w = world(scrub)
    st, off, al, h = classify(w)
    on_isl = (st >= CUT0 - NOSE_VERTS + 1) & (st <= CUT1 + NOSE_VERTS - 1) & (np.abs(al) <= 1.3) & (np.abs(off) <= ISLAND_HALF) & (h >= 0.2) & (h <= 1.2)
    bm = open_bm(scrub)
    gone = drop_faces(bm, on_isl)
    rep["removed_faces"]["SCRUB"] = gone
    rep["added_faces"]["SCRUB"] = 0
    rep["SCRUB"] = {"clumps_removed_from_the_old_island": gone // 2, "clumps_planted_on_the_bank": 0}
    close_bm(bm, scrub)

# ===================================================================================== the street-only median pieces
for name in STREET_OBJECTS:
    ob = bpy.data.objects.get(name)
    if ob is None:
        rep["removed_faces"][name] = 0
        continue
    st, off, al, h = classify(world(ob))
    if (st < 0).any() or st.min() < A0 or st.max() > A1 or np.abs(off).max() > ISLAND_HALF + 0.1:
        die(f"{name} reaches outside the split's island (rows v{st.min()}..v{st.max()}, offsets to {np.abs(off).max():.2f} m): not removed blind")
    rep["removed_faces"][name] = len(ob.data.polygons)
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if me.users == 0:
        bpy.data.meshes.remove(me)

# =========================================================================================================== paint
def fork_t(v):
    return smooth((v - A0) / (NOSE - A0)) if v < NOSE else smooth((A1 - v) / (A1 - TAIL))


def meet(v):
    """the offset of the point where the two roads part / join, for the fork row v's side"""
    return OFF["sb_east"][K[NOSE if v < NOSE else TAIL]]


def hw(v):
    return float(FHW[v - FV0])


def yellow_w(v):
    return OFF["sb_east"][K[v]] + EDGE_INSET if v in K else 0.09 + fork_t(v) * (meet(v) + EDGE_INSET - 0.09)


def yellow_e(v):
    return OFF["nb_west"][K[v]] - EDGE_INSET if v in K else -0.09 + fork_t(v) * (meet(v) - EDGE_INSET + 0.09)


def div_w(k):
    return lambda v: (OFF["sb_east"][K[v]] + EDGE_INSET if v in K else fork_t(v) * (meet(v) + EDGE_INSET)) + k * LANE_W


def div_e(k):
    return lambda v: (OFF["nb_west"][K[v]] - EDGE_INSET if v in K else fork_t(v) * (meet(v) - EDGE_INSET)) - k * LANE_W


def paint(ob, lines):
    """lane_markings' strip: one loose quad per segment and line, two triangles, U across (0 / 1), V = the station"""
    w_ = world(ob)
    st_, off_, al_, h_ = classify(w_)
    inz = (st_ >= A0) & (st_ <= A1) & (np.abs(al_) <= 0.3) & (np.abs(off_) <= FHW[np.clip(st_ - FV0, 0, len(FHW) - 1)] + 0.2)
    bm_ = open_bm(ob)
    gone_ = drop_faces(bm_, inz)
    uvl = bm_.loops.layers.uv.active
    made, floating = 0, 0
    for offset_of, dashed, clip in lines:
        for v in range(A0, A1):
            o0, o1 = offset_of(v), offset_of(v + 1)
            if clip and (abs(o0) + LINE_W / 2 > hw(v) - EDGE_INSET or abs(o1) + LINE_W / 2 > hw(v + 1) - EDGE_INSET):
                continue
            if dashed and (float(FS[v - FV0]) % (DASH_ON + DASH_GAP)) > DASH_ON:
                continue
            q, ok = [], True
            for vv, o in ((v, o0), (v + 1, o1)):
                for sign in (-1, 1):
                    oo = o + sign * LINE_W / 2
                    y = surface(vv, oo)
                    if y is None:
                        ok = False
                        break
                    x, yy = plan(vv, oo)
                    q.append((bm_.verts.new((x, yy, y + PAINT_LIFT)), ((sign + 1) / 2, float(FS[vv - FV0]))))
                if not ok:
                    break
            if not ok:
                floating += 1
                for vert, _uv in q:
                    bm_.verts.remove(vert)
                continue
            for tri in ((0, 1, 3), (0, 3, 2)):
                f = bm_.faces.new([q[i][0] for i in tri])
                if uvl is not None:
                    for l, i in zip(f.loops, tri):
                        l[uvl].uv = q[i][1]
            made += 2
    close_bm(bm_, ob)
    return gone_, made, floating


y_lines = [(yellow_w, False, False), (yellow_e, False, False)]
gone, made, off_pave = paint(yline, y_lines)
rep["removed_faces"]["YLINE"], rep["added_faces"]["YLINE"] = gone, made
if off_pave:
    die(f"YLINE: {off_pave} quads would stand off the pavement")
m_lines = [(lambda v: hw(v) - EDGE_INSET, False, False), (lambda v: -(hw(v) - EDGE_INSET), False, False)]
for kk in range(1, MAX_LANES + 1):
    m_lines += [(div_w(kk), True, True), (div_e(kk), True, True)]
gone, made, off_pave = paint(marks, m_lines)
rep["removed_faces"]["MARKINGS"], rep["added_faces"]["MARKINGS"] = gone, made
rep["MARKINGS"] = {"divider_quads_left_out_because_they_would_cross_the_bank": off_pave}

# ====================================================================================================== self-checks
# CURB: nothing moved but the east walk and the tapered rows (positions compared by the vertices that survived, in order)
w1 = world(curb)
st1, off1, al1, h1 = classify(w1)
near_bank = (st1 > NOSE) & (st1 < TAIL) & (np.abs(al1) <= 0.3)
k_arr = np.clip(st1 - NOSE, 0, len(R["v"]) - 1)
sbE = np.array(OFF["sb_east"])[k_arr]
nbW = np.array(OFF["nb_west"])[k_arr]
in_bank = near_bank & (off1 < sbE - 1e-4) & (off1 > nbW + 1e-4) & (h1 > -8.0) & (h1 < 9.0)
on_sb = near_bank & (off1 > sbE + 1e-3) & (off1 < FHW[np.clip(st1 - FV0, 0, len(FHW) - 1)] - 0.01)
on_nb = near_bank & (off1 < nbW - 1e-3) & (off1 > -FHW[np.clip(st1 - FV0, 0, len(FHW) - 1)] + 0.01)
if int(on_sb.sum()) or int(on_nb.sum()):
    die(f"CURB: {int(on_sb.sum())} vertices stand on the southbound pavement and {int(on_nb.sum())} on the northbound, rows v{NOSE + 1}..v{TAIL - 1}")
left_isl = (st1 > CUT0) & (st1 < CUT1) & (np.abs(al1) <= 0.3) & (np.abs(off1) <= ISLAND_HALF + 0.1) & (h1 >= 0.05) & (h1 <= 0.31)
left_isl &= ~((st1 > NOSE) & (st1 < TAIL))          # the bank's own rings pass close to the old island's place
if int(left_isl.sum()):
    die(f"CURB: {int(left_isl.sum())} vertices of the old island are still there between rows v{CUT0} and v{CUT1}")
rep["CURB"]["vertices"] = [nv0, len(w1)]
rep["CURB"]["ring_vertices_in_the_bank"] = int(in_bank.sum())
for ob, key in ((yline, "YLINE"), (marks, "MARKINGS")):
    wq = world(ob)
    sq, oq, aq, hq = classify(wq)
    z = (sq >= A0) & (sq <= A1) & (np.abs(aq) <= 0.3) & (np.abs(oq) <= FHW[np.clip(sq - FV0, 0, len(FHW) - 1)] + 0.2)
    worst = 0.0
    for i in np.nonzero(z)[0][::7]:
        y = surface(int(sq[i]), float(oq[i]))
        if y is None:
            die(f"{key}: a paint vertex at row v{int(sq[i])}, offset {float(oq[i]):+.2f}, is not over pavement")
        worst = max(worst, abs(wq[i, 2] - y - PAINT_LIFT))
    if worst > 0.002:
        die(f"{key}: paint stands {worst:.3f} m off its {PAINT_LIFT} m over the road")
    rep[key] = dict(rep.get(key, {}), vertices_in_the_zone=int(z.sum()))
curb["college_split"] = json.dumps({"removed_faces": rep["removed_faces"], "added_faces": rep["added_faces"]})
print("[college_middle] " + json.dumps(rep))
if SAVE_AS:
    bpy.ops.wm.save_as_mainfile(filepath=SAVE_AS, copy=True)
    print(f"[college_middle] saved a copy: {SAVE_AS}")
else:
    bpy.ops.wm.save_mainfile()
    print("[college_middle] saved")
