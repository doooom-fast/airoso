"""College split, order of work step 2: THE SCENE'S RIBBONS (ROAD only). STEP-DESIGN.md has the why.

    blender --background <loop.blend> --python-exit-code 1 --python college_split_blend.py -- [--save-as <path>]

Reads college_split.data.json (college_split_data.py) beside this file and edits the object ROAD of the open blend:

  two roads, v1172..v1444   the mainline's row (ROAD vertices 3v, 3v+1, 3v+2 = west edge, line, east edge) becomes the
                            SOUTHBOUND road: the west vertex is not touched; the line vertex goes to the new line; the
                            east vertex goes to the island's west side. Its four faces per segment stay (they are the
                            southbound road now), so no old slab is left under the northbound road.
                            The NORTHBOUND road is a new ribbon of three vertices per station, appended to ROAD: the
                            island's east side, the piece's line, and where ROAD's east vertex stood (raised).
  the two forks             v1131..v1171 and v1445..v1475 keep their three vertices in place and take the tilt easing in
                            from the flat outer row (v1130, v1476 are not touched). At the nose and the tail the two
                            roads meet in ONE vertex (the island begins with no width): the piece's first and last
                            rows use the mainline's east vertex as their west one. Between the last fork row and that
                            row (v1171/v1172, v1444/v1445) the four old faces are replaced by a fan of six from the
                            fork row's centre vertex.

A row is tilted, not flat: each vertex has its own height (the measured crossfall laid onto the built west edge).
UVs keep the built convention on every vertex: u = offset from the BUILT line / 4, v = the built row's own v.

Nothing else is touched: CURB (the walks and the old island), the paint, the rail, the lamps and the ground still
stand where the one-slab road had them; they are steps 3 and 4.

Self-checks (exit 1, the blend is NOT saved): the rows are as drafted before anything moves; no vertex outside the moved
set moves, the west edge column included; vertex and face counts as planned; no face of the zone degenerate or turned
over; the pavement of the zone is covered exactly once and the bank between the roads not at all.
Idempotent: a ROAD that carries the custom property `college_split` is left alone."""
import json
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
R = S["rows"]
A0, A1 = S["mainline"]["from_v"], S["mainline"]["to_v"]
NOSE, TAIL = R["v"][0], R["v"][-1]
LIFT = 0.10
TOL = 0.005                 # a drafted vertex is where the data says within this (m)
MIN_AREA = 1e-3             # m2: a face under this is degenerate
EDGE_SKIP = 0.08            # coverage samples keep this far from a pavement edge (m)
SAMPLE_STEP = 0.5           # coverage samples across the road (m)


def die(msg):
    print(f"[college_split] FAIL: {msg}")
    sys.exit(1)


def bl(p):
    """engine (x east, y up, z north) -> Blender (x, z, y)"""
    return Vector((p[0], p[2], p[1]))


road = bpy.data.objects.get("ROAD")
if road is None:
    die("no object ROAD")
if road.get("college_split"):
    print(f"[college_split] ROAD already carries the split ({road['college_split']}): nothing to do, nothing saved")
    sys.exit(0)
if not np.allclose(np.array(road.matrix_world), np.eye(4)):
    die("ROAD has a transform; the step works in world coordinates")
me = road.data
n0, f0 = len(me.vertices), len(me.polygons)
co0 = np.empty(n0 * 3)
me.vertices.foreach_get("co", co0)
co0 = co0.reshape(-1, 3)
built_y = dict(zip(range(A0, A1 + 1), S["built_line_y"]))
k_of = {v: k for k, v in enumerate(R["v"])}
fk_of = {v: k for k, v in enumerate(R["fork_v"])}

# --- before anything moves: the rows are as drafted --------------------------------------------------------------------------
for v in range(A0, A1 + 1):
    w, c, e = co0[3 * v], co0[3 * v + 1], co0[3 * v + 2]
    for nm, p in (("west", w), ("line", c), ("east", e)):
        if abs(p[2] - (built_y[v] + LIFT)) > TOL:
            die(f"v{v} {nm} vertex is {p[2] - built_y[v]:+.3f} over the built line, not {LIFT} (the rows are not as drafted)")
    if np.hypot(*(0.5 * (w[:2] + e[:2]) - c[:2])) > TOL:
        die(f"v{v}: the line vertex is not midway between the edge vertices")
    if v in k_of:
        k = k_of[v]
        for nm, p, q in (("west", w, R["sb_west"][k]), ("east", e, R["nb_east"][k])):
            if np.hypot(p[0] - q[0], p[1] - q[2]) > TOL:
                die(f"v{v}: ROAD's {nm} vertex is {np.hypot(p[0] - q[0], p[1] - q[2]):.3f} m from the data's built {nm} edge")
        if abs(R["sb_west"][k][1] - w[2]) > 1e-3:
            die(f"v{v}: the data moves the built west edge in height ({R['sb_west'][k][1] - w[2]:+.4f} m)")

bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()
bm.normal_update()
uvl = bm.loops.layers.uv.active
if uvl is None:
    die("ROAD has no UV layer")
moved = set()


def row_v(v):
    """the built row's own v coordinate (every loop of its line vertex carries it)"""
    vs = {round(l[uvl].uv.y, 5) for l in bm.verts[3 * v + 1].link_loops}
    if len(vs) != 1:
        die(f"v{v}: the line vertex carries {len(vs)} different v coordinates")
    return next(iter(vs))


ROWV = {v: row_v(v) for v in range(A0, A1 + 1)}
ref = next(iter(bm.verts[3 * (NOSE + 10) + 1].link_faces))      # a drafted face that stays: the template for new ones
REF_UP = 1.0 if ref.normal.z > 0 else -1.0              # which way the drafted faces look
u_of = {}                                               # vertex -> u (offset from the built line / 4)


def place(vert, xyz, off):
    vert.co = bl(xyz)
    u_of[vert] = off / 4.0


# --- the two roads: the mainline's rows ----------------------------------------------------------------------------------------
for v in R["v"]:
    k = k_of[v]
    place(bm.verts[3 * v + 1], R["sb_line"][k], R["offsets_m"]["sb_line"][k])
    place(bm.verts[3 * v + 2], R["sb_east"][k], R["offsets_m"]["sb_east"][k])
    moved.update((3 * v + 1, 3 * v + 2))
for v in R["fork_v"]:                                    # the forks: heights only
    _yw, yc, ye = R["fork_y"][fk_of[v]]
    bm.verts[3 * v + 1].co.z = yc
    bm.verts[3 * v + 2].co.z = ye
    moved.update((3 * v + 1, 3 * v + 2))
for vert, u in u_of.items():                             # the moved vertices' u on the faces they already have
    for l in vert.link_loops:
        l[uvl].uv.x = u

# --- the northbound ribbon ----------------------------------------------------------------------------------------------------
piece = {}
SHARED = {v: bm.verts[3 * v + 2] for v in (NOSE, TAIL)}      # looked up before any vertex is added
for v in R["v"]:
    k = k_of[v]
    row = []
    for nm in ("nb_west", "nb_line", "nb_east"):
        if nm == "nb_west" and v in (NOSE, TAIL):       # the nose / the tail: the two roads share this vertex
            shared = SHARED[v]
            if (shared.co - bl(R[nm][k])).length > 1e-3:
                die(f"v{v}: the two inner edges are {(shared.co - bl(R[nm][k])).length:.3f} m apart, not one point")
            row.append(shared)
            continue
        nv = bm.verts.new(bl(R[nm][k]))
        u_of[nv] = R["offsets_m"][nm][k] / 4.0
        row.append(nv)
    piece[v] = row
bm.verts.ensure_lookup_table()
new_faces = []


def tri(a, b, c, va, vb, vc):
    """a face looking the way the drafted ones do; va / vb / vc = each corner's station (for its v coordinate)"""
    n = (b.co - a.co).cross(c.co - a.co)
    if n.z * REF_UP < 0:
        b, c, vb, vc = c, b, vc, vb
    f = bm.faces.new((a, b, c), ref)
    for l, vert, st in zip(f.loops, (a, b, c), (va, vb, vc)):
        u = u_of.get(vert)
        if u is None:                                    # an untouched drafted vertex: its own u
            u = next(iter(ll[uvl].uv.x for ll in vert.link_loops if ll.face is not f))
        l[uvl].uv = (u, ROWV[st])
    new_faces.append(f)
    return f


for v in range(NOSE, TAIL):                              # four faces per segment, the drafted pattern
    (l0, c0, r0), (l1, c1, r1) = piece[v], piece[v + 1]
    tri(l0, c1, c0, v, v + 1, v)
    tri(l0, l1, c1, v, v + 1, v + 1)
    tri(c0, r1, r0, v, v + 1, v)
    tri(c0, c1, r1, v, v + 1, v + 1)

# --- the two fans --------------------------------------------------------------------------------------------------------------
gone = 0
for fork_row, road_row in ((NOSE - 1, NOSE), (TAIL + 1, TAIL)):
    a = {3 * fork_row + i for i in range(3)} | {3 * road_row + i for i in range(3)}
    old = [f for f in {f for i in a for f in bm.verts[i].link_faces} if {x.index for x in f.verts} <= a]
    if len(old) != 4:
        die(f"between v{fork_row} and v{road_row}: {len(old)} drafted faces, not 4")
    # the fork row's edge vertices keep their u: read it before their faces go
    W, C, E = (bm.verts[3 * fork_row + i] for i in range(3))
    for vert in (W, E):
        u_of[vert] = next(iter(l[uvl].uv.x for l in vert.link_loops))
    u_of.setdefault(C, 0.0)
    W1 = bm.verts[3 * road_row]
    u_of[W1] = next(iter(l[uvl].uv.x for l in W1.link_loops))
    bmesh.ops.delete(bm, geom=old, context="FACES_ONLY")
    gone += 4
    chain = [W1, bm.verts[3 * road_row + 1]] + piece[road_row]     # west to east; piece[..][0] IS the mainline's east vertex
    tri(C, W, W1, fork_row, fork_row, road_row)
    for p, q in zip(chain, chain[1:]):
        tri(C, p, q, fork_row, road_row, road_row)
    tri(C, chain[-1], E, fork_row, road_row, fork_row)
bm.verts.index_update()
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()
bm.normal_update()

# --- self-checks -----------------------------------------------------------------------------------------------------------
n1, f1 = len(bm.verts), len(bm.faces)
want_v, want_f = n0 + 3 * len(R["v"]) - 2, f0 - gone + 4 * (TAIL - NOSE) + 12
if (n1, f1) != (want_v, want_f):
    die(f"counts: {n1} vertices / {f1} faces, planned {want_v} / {want_f}")
co1 = np.array([v.co[:] for v in bm.verts])
still = np.ones(n0, dtype=bool)
still[sorted(moved)] = False
if not np.array_equal(co1[:n0][still], co0[still]):
    die(f"{int((np.abs(co1[:n0][still] - co0[still]).max(axis=1) > 0).sum())} vertices outside the moved set moved")
west_col = [3 * v for v in range(A0, A1 + 1)]
if not np.array_equal(co1[west_col], co0[west_col]):
    die("the west edge column moved")
zone_verts = {3 * v + i for v in range(A0, A1 + 1) for i in range(3)} | set(range(n0, n1))
zone_faces = [f for f in bm.faces if any(x.index in zone_verts for x in f.verts)]
bad = [f.index for f in zone_faces if f.calc_area() < MIN_AREA]
if bad:
    die(f"{len(bad)} degenerate faces in the zone (first {bad[:5]})")
turned = [f.index for f in zone_faces if f.normal.z * REF_UP <= 0]
if turned:
    die(f"{len(turned)} faces of the zone are turned over (first {turned[:5]})")
steep = max(abs(f.normal.z) for f in zone_faces), min(abs(f.normal.z) for f in zone_faces)

# coverage in plan: every sample on pavement under exactly one ROAD face, every sample on the bank under none
T = np.array([[x.co[:2] for x in f.verts] for f in bm.faces])            # all of ROAD, plan
x0, y0 = co1[sorted(zone_verts)][:, :2].min(axis=0) - 5.0
x1, y1 = co1[sorted(zone_verts)][:, :2].max(axis=0) + 5.0
T = T[(T[:, :, 0].max(axis=1) > x0) & (T[:, :, 0].min(axis=1) < x1) & (T[:, :, 1].max(axis=1) > y0) & (T[:, :, 1].min(axis=1) < y1)]


def cover(pts):
    """how many of ROAD's faces lie over each plan point"""
    out = np.zeros(len(pts), dtype=np.int32)
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    for i0 in range(0, len(pts), 2000):
        p = pts[i0:i0 + 2000][:, None, :]
        d1 = (p[..., 0] - b[None, :, 0]) * (a[None, :, 1] - b[None, :, 1]) - (a[None, :, 0] - b[None, :, 0]) * (p[..., 1] - b[None, :, 1])
        d2 = (p[..., 0] - c[None, :, 0]) * (b[None, :, 1] - c[None, :, 1]) - (b[None, :, 0] - c[None, :, 0]) * (p[..., 1] - c[None, :, 1])
        d3 = (p[..., 0] - a[None, :, 0]) * (c[None, :, 1] - a[None, :, 1]) - (c[None, :, 0] - a[None, :, 0]) * (p[..., 1] - a[None, :, 1])
        neg = (d1 < 0) | (d2 < 0) | (d3 < 0)
        pos = (d1 > 0) | (d2 > 0) | (d3 > 0)
        out[i0:i0 + 2000] = (~(neg & pos)).sum(axis=1)
    return out


def row_plan(v):
    """the station's west and east built edge in plan, and the pavement / bank intervals in offsets from the built line"""
    w, e = co0[3 * v][:2], co0[3 * v + 2][:2]
    hw = 0.5 * float(np.hypot(*(w - e)))
    if v in k_of:
        o = R["offsets_m"]
        k = k_of[v]
        return w, e, hw, [(o["sb_east"][k], hw), (-hw, o["nb_west"][k])], [(o["nb_west"][k], o["sb_east"][k])]
    return w, e, hw, [(-hw, hw)], []


# Samples stand BETWEEN rows (on a row every point lies on the shared edge of two faces and counts twice), at offsets
# from the built line that are inside the same kind of ground on both rows of the segment.
pts, want, where = [], [], []
for v in range(A0, A1):
    w, e, hw, paved, bank = row_plan(v)
    w2, e2, hw2, paved2, bank2 = row_plan(v + 1)
    if v in k_of and (v + 1) in k_of:                    # two roads: each road once, the bank not at all
        spans = [(max(a[0], b[0]), min(a[1], b[1]), 1) for a, b in zip(paved, paved2)]
        spans += [(max(a[0], b[0]), min(a[1], b[1]), 0) for a, b in zip(bank, bank2)]
    else:                                                # a fork segment or a fan: paved right across the built width
        spans = [(-min(hw, hw2), min(hw, hw2), 1)]
    for frac in (0.3, 0.7):
        for lo, hi, want_n in spans:
            for off in np.arange(lo + EDGE_SKIP, hi - EDGE_SKIP, SAMPLE_STEP):
                p0 = w + (e - w) * (hw - off) / (2 * hw)
                p1 = w2 + (e2 - w2) * (hw2 - off) / (2 * hw2)
                pts.append((1 - frac) * p0 + frac * p1)
                want.append(want_n)
                where.append((v, frac, round(float(off), 2)))
got = cover(np.array(pts))
want = np.array(want)
wrong = np.nonzero(got != want)[0]
if len(wrong):
    for i in wrong[:12]:
        print(f"[college_split]   v{where[i][0]}+{where[i][1]} offset {where[i][2]:+.2f}: {int(got[i])} faces over it, want {int(want[i])}")
    die(f"coverage: {len(wrong)} of {len(pts)} samples wrong")

step_n = piece[NOSE + 1][0].co.z - bm.verts[3 * (NOSE + 1) + 2].co.z
step_t = piece[TAIL - 1][0].co.z - bm.verts[3 * (TAIL - 1) + 2].co.z
rise = max(piece[v][1].co.z - bm.verts[3 * v + 1].co.z for v in R["v"])
rep = {"vertices": [n0, n1], "faces": [f0, f1], "moved_vertices": len(moved), "piece_vertices": n1 - n0,
       "faces_removed": gone, "faces_added": len(new_faces), "coverage_samples": int(len(pts)),
       "on_pavement": int((want == 1).sum()), "on_the_bank": int((want == 0).sum()),
       "inner_edge_step_one_row_in_m": {"nose": round(step_n, 3), "tail": round(step_t, 3)},
       "northbound_line_over_southbound_line_max_m": round(rise, 2),
       "flattest_and_steepest_face_normal_z": [round(steep[0], 4), round(steep[1], 4)]}
bm.to_mesh(me)
bm.free()
me.update()
road["college_split"] = json.dumps(rep)
print("[college_split] " + json.dumps(rep))
if SAVE_AS:
    bpy.ops.wm.save_as_mainfile(filepath=SAVE_AS, copy=True)
    print(f"[college_split] saved a copy: {SAVE_AS}")
else:
    bpy.ops.wm.save_mainfile()
    print("[college_split] saved")
