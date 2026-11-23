"""College split, order of work step 4b / 4c: THE EAST GROUND and THE EAST LAMPS. STEP-DESIGN.md has the why.
Run on a blend whose CURB carries the middle (step 3).

    blender --background <loop.blend> --python-exit-code 1 --python college_ground_blend.py -- [--save-as <path>]

The east walk rose with the northbound road (up to 5.55 m); the ground behind it still stood where the one-slab road
had it. The split's ground is RELEASED ground (data/ground_release.json: the prep pins under pavement but does not
feather it), so it has to be right in the scene:

  TERRAIN   every vertex east of the built east pavement edge on rows A0..A1 is raised to at least
                the edge's road height less GROUND_CLEAR_M      out to HOLD_M past the edge (under and behind the walk)
                then that height falling FILL_SLOPE per metre   further out
            and is never lowered: where the hill already stands higher (the cut) it stays as it is, where the old ground
            lies lower a fill runs down to it. Nothing under the pavement is touched (the prep pins it), nothing west of
            the edge.
  LIGHTPOST_3, LIGHTPOST_4, LIGHTS_0   every lamp whose foot stands east of the built line on rows A0..A1 rises by
            what the road's east edge rose at its place (post, arm and head together).

Self-checks (exit 1, NOT saved): in TERRAIN only vertices east of the edge moved, and only up; every lamp part moved as
one piece, straight up.
Idempotent: a TERRAIN that carries the custom property `college_split_ground` is left alone."""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SAVE_AS = argv[argv.index("--save-as") + 1] if "--save-as" in argv else None
S = json.loads((HERE / "college_split.data.json").read_text(encoding="utf-8"))
R, F = S["rows"], S["frame"]
A0, A1 = S["mainline"]["from_v"], S["mainline"]["to_v"]
LIFT = 0.10
GROUND_CLEAR_M = 0.02      # the prep's own clearance of pinned ground under the deck (build_kn5_loop GROUND_CLEAR)
HOLD_M = 3.5               # [invented] the ground holds the edge's height this far past it: the walk is 3.08 m wide
FILL_SLOPE = 0.5           # [invented] past that a fill may fall this much per metre (1 in 2, an earth embankment)
REACH_M = 40.0             # how far east of the edge a vertex is looked at (the released zone's reach)
LAMPS = ("LIGHTPOST_3", "LIGHTPOST_4", "LIGHTS_0")

FV0 = F["from_v"]
FX, FY, FZ = np.array(F["x"]), np.array(F["y"]), np.array(F["z"])
FNX, FNZ, FHW = np.array(F["nx"]), np.array(F["nz"]), np.array(F["half_w"])
K = {v: k for k, v in enumerate(R["v"])}
FK = {v: k for k, v in enumerate(R["fork_v"])}


def die(msg):
    print(f"[college_ground] FAIL: {msg}")
    sys.exit(1)


# the road's east edge: its height now, per row of the frame (rows outside A0+1..A1-1 are the built road)
EDGE = FY + LIFT
for v in range(A0 + 1, A1):
    EDGE[v - FV0] = R["nb_east"][K[v]][1] if v in K else R["fork_y"][FK[v]][2]
RISE = EDGE - (FY + LIFT)


def world(ob):
    if not np.allclose(np.array(ob.matrix_world), np.eye(4)):
        die(f"{ob.name} has a transform")
    co = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


BX0, BX1 = FX.min() - 60.0, FX.max() + 60.0
BY0, BY1 = FZ.min() - 60.0, FZ.max() + 60.0


def classify(w):
    """per vertex in the built line's frame: station (-1 = not near), offset (+ west), along (m past the row), and the
    road's east edge height and rise interpolated along the road at its place"""
    st = np.full(len(w), -1, dtype=np.int64)
    off = np.zeros(len(w))
    al = np.zeros(len(w))
    edge = np.zeros(len(w))
    rise = np.zeros(len(w))
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
        edge[idx] = EDGE[k] * (1 - t) + EDGE[k2] * t
        rise[idx] = RISE[k] * (1 - t) + RISE[k2] * t
    return st, off, al, edge, rise


terrain = bpy.data.objects.get("TERRAIN")
curb = bpy.data.objects.get("CURB")
if terrain is None or curb is None:
    die("no TERRAIN / CURB")
if not curb.get("college_split"):
    die("CURB does not carry the middle: run college_middle_blend.py (step 3) first")
if terrain.get("college_split_ground"):
    print(f"[college_ground] TERRAIN already carries the east ground ({terrain['college_split_ground']}): nothing to do, nothing saved")
    sys.exit(0)

# ============================================================================================================ TERRAIN
w = world(terrain)
st, off, al, edge, rise = classify(w)
hw = FHW[np.clip(st - FV0, 0, len(FHW) - 1)]
d = -hw - off                                               # metres east of the built east pavement edge
zone = (st >= A0) & (st <= A1) & (d >= 0.0) & (d <= REACH_M)
# the first and last half-segment belong to the untouched road's rows: the rise is zero there by construction
tgt = edge - GROUND_CLEAR_M - np.maximum(0.0, d - HOLD_M) * FILL_SLOPE
up = zone & (tgt > w[:, 2] + 1e-6)
new_z = w[:, 2].copy()
new_z[up] = tgt[up]
moved = np.nonzero(up)[0]
if len(moved) == 0:
    die("TERRAIN: no vertex east of the edge lies under the raised walk's ground (nothing to do is not expected)")
co = w.copy()
co[:, 2] = new_z
terrain.data.vertices.foreach_set("co", co.reshape(-1))
terrain.data.update()
w1 = world(terrain)
delta = w1 - w
if np.abs(delta[:, :2]).max() > 0 or (delta[:, 2] < -1e-9).any():
    die("TERRAIN: a vertex moved sideways or down")
if set(np.nonzero(np.abs(delta[:, 2]) > 0)[0].tolist()) - set(moved.tolist()):
    die("TERRAIN: a vertex outside the east strip moved")
rep = {"TERRAIN": {"vertices_east_of_the_edge_looked_at": int(zone.sum()), "raised": int(len(moved)),
                   "raise_m": {"max": round(float(delta[moved, 2].max()), 2), "median": round(float(np.median(delta[moved, 2])), 2)},
                   "rows": [int(st[moved].min()), int(st[moved].max())],
                   "reach_of_the_fill_past_the_edge_m": round(float(d[moved].max()), 1),
                   "left_as_they_were_because_the_hill_stands_higher": int((zone & ~up).sum())}}

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
    stl, offl, all_, edgel, risel = classify(wl)
    zl = wl[:, 2].copy()
    lifted, parts, worst = 0, 0, 0.0
    for r in np.unique(root):
        m = root == r
        if (stl[m] < 0).all():
            continue
        # the part's foot: its lowest vertices' place (a post's base); a head or an arm has no foot of its own on the
        # ground, so it is placed by its own middle: both stand on the same side of the line as the post
        low = m & (wl[:, 2] <= wl[m, 2].min() + 0.05)
        foot = wl[low].mean(axis=0)
        s1, o1, a1, e1, r1 = classify(foot[None, :])
        if s1[0] <= A0 or s1[0] >= A1 or o1[0] >= 0.0:
            continue                                        # outside the zone, or on the west side
        if abs(r1[0]) < 1e-6:
            continue
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
