"""Driver's-seat stills of every phase-5 STUB (ledger 0054) on a BUILT gate OBJ — what Kevin sees pulling up to it.

    blender --background --factory-startup --python-exit-code 1 --python tools/stub_stills_blend.py -- \\
        --proj <project> --obj <project>/data/track[.<layout>].obj --layout street|race_cw|race_acw --out <prefix>
        [--only <id,...>] [--type3 <id>]

Engine frame x=E, y=up, z=N -> Blender (x, z, y). Workbench, back faces culled (as AC), each mesh class in a flat colour
(road grey, curb pale, grass green, K-rail concrete, race kerb red, paint white / yellow) so the stub, its returns and
its barrier read. The eye stands on the BUILT road (a ray down onto the 1ROAD sheets) at a driver's 1.2 m:
  street   in the lane on the stub's side, travelling the way that lane runs (right-hand traffic), MOUTH_BACK_M before
           the mouth, looking at the barrier; and `_in`: turned in, on the stub IN_M past the mouth line in its right
           lane, looking at the barrier;
  race_*   in the middle of that layout's declared lane (data/barrier_bands.json corridors.<id>.lane_by_vertex) at the
           same distance, travelling the layout's direction, looking at the barrier behind the sealed mouth.
--type3 <id>: the same street still of that stub with its K-rail replaced by a MUTCD Type III barricade sketch (three
orange / white rails on two posts, 1.5 m) — the option for Kevin; nothing of it ships (tools/stub_roads.py refuses it).
Writes <prefix>_<layout>_<id>.png (and <prefix>_street_<id>_type3.png).
"""
import json
import math
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]


def arg(k, d=None):
    return a[a.index(k) + 1] if k in a else d


PROJ, OBJ, LAYOUT, OUT = arg("--proj"), arg("--obj"), arg("--layout", "street"), arg("--out")
ONLY = set((arg("--only") or "").split(",")) - {""}
TYPE3 = arg("--type3")
MOUTH_BACK_M = 16.0
IN_M = 2.0               # the 'turned in' still: on the stub this far past the mouth line, looking at the barrier
COL = [("GRASS_FAR", (93 / 255, 93 / 255, 66 / 255)), ("1GRASS", (68 / 255, 92 / 255, 40 / 255)),
       ("1ROAD", (0.34, 0.34, 0.35)), ("1KERB_RACE", (0.62, 0.10, 0.08)), ("1KERB", (0.66, 0.66, 0.64)),
       ("MARKINGS", (0.92, 0.92, 0.90)), ("YLINE", (0.85, 0.68, 0.1)), ("HOUSE", (0.78, 0.70, 0.58)),
       ("BUILDING", (0.72, 0.72, 0.70)), ("BRIDGESTRUCT", (0.70, 0.69, 0.66)), ("LIGHTPOST", (0.25, 0.25, 0.27)),
       ("LIGHTS", (0.9, 0.8, 0.5)), ("1WALL_STUB", (0.86, 0.85, 0.80)), ("1WALL", (0.78, 0.78, 0.76)),
       ("SIGNARROW", (0.03, 0.03, 0.03)), ("SIGNPLATE", (0.95, 0.78, 0.05)), ("SIGNPOST", (0.55, 0.55, 0.57))]


def color_of(name):
    u = name.upper()
    for p, c in COL:
        if u.startswith(p):
            return c
    return None


bpy.ops.wm.read_factory_settings(use_empty=True)
plan = json.load(open(PROJ + "/data/stubs.plan.json", encoding="utf-8"))
mouths = json.load(open(PROJ + "/data/mouths.json", encoding="utf-8"))["mouths"]
conns = {c["name"]: c for c in json.load(open(PROJ + "/data/connectors.local.json", encoding="utf-8"))["connectors"]}
local = json.load(open(PROJ + "/data/centerline.local.json", encoding="utf-8"))
cfg = json.load(open(PROJ + "/track.config.json", encoding="utf-8"))
P = local["points_xyz_m"]
W = local["widths_m"]
n = len(P) - 1 if abs(P[0][0] - P[-1][0]) < 1e-6 and abs(P[0][2] - P[-1][2]) < 1e-6 else len(P)
stubs = [s for s in plan["stubs"] if not ONLY or s["id"] in ONLY]
FOCUS = [tuple(s["cut_xz"]) for s in stubs]
KEEP = 450.0

V, groups, cur = [], {}, None
with open(OBJ, encoding="utf-8", errors="replace") as f:
    for ln in f:
        c = ln[:2]
        if c == "v ":
            p = ln.split()
            V.append((float(p[1]), float(p[3]), float(p[2])))
        elif c == "o " or c == "g ":
            nm = ln[2:].strip()
            cur = nm if color_of(nm) else None
            if cur:
                groups.setdefault(cur, [])
        elif c == "f " and cur:
            idx = [int(t.split("/")[0]) - 1 for t in ln.split()[1:]]
            p0 = V[idx[0]]
            if min((p0[0] - fx) ** 2 + (p0[1] - fz) ** 2 for fx, fz in FOCUS) <= KEEP * KEEP:
                groups[cur].append(idx)
mats = {}


def solid_mat(col):
    if col in mats:
        return mats[col]
    m = bpy.data.materials.new("m%d" % len(mats))
    m.diffuse_color = (*col, 1.0)
    mats[col] = m
    return m


def add_mesh(nm, vs, fs, col):
    me = bpy.data.meshes.new(nm)
    me.from_pydata(vs, [], fs)
    me.update()
    ob = bpy.data.objects.new(nm, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(solid_mat(col))
    return ob


road_parts = []
stub_obs = {}
for nm, faces in groups.items():
    if not faces:
        continue
    used, vs, fs = {}, [], []
    for fc in faces:
        q = []
        for i in fc:
            if i not in used:
                used[i] = len(vs)
                vs.append(V[i])
            q.append(used[i])
        fs.append(q[::-1])
    ob = add_mesh(nm, vs, fs, color_of(nm))
    if nm.upper().startswith("1WALL_STUB"):
        stub_obs[nm.upper()] = ob
    if nm.upper().startswith("1ROAD"):
        road_parts.append((vs, fs))
rv, rf = [], []
for vs, fs in road_parts:
    off = len(rv)
    rv += vs
    rf += [[i + off for i in q] for q in fs]
road = BVHTree.FromPolygons(rv, rf)


def deck(x, y, near=None):
    z0 = 3000.0 if near is None else near + 6.0
    h = road.ray_cast(Vector((x, y, z0)), Vector((0, 0, -1)))
    return h[0].z if h[0] is not None else None


sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"
sh.color_type = "MATERIAL"
sh.show_shadows = True
sh.shadow_intensity = 0.45
sh.show_cavity = True
sh.cavity_type = "WORLD"
sh.show_backface_culling = True
sh.show_specular_highlight = False
sh.background_type = "WORLD"
world = bpy.data.worlds.new("sky")
world.color = (0.55, 0.70, 0.88)
sc.world = world
sc.display.light_direction = (0.35, -0.45, 0.82)
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.view_settings.view_transform = "Standard"
cd = bpy.data.cameras.new("cam")
cd.sensor_fit = "HORIZONTAL"
cd.clip_start = 0.05
cd.clip_end = 15000.0
cam = bpy.data.objects.new("cam", cd)
sc.collection.objects.link(cam)
sc.camera = cam


def nrm(i):
    a_, b_ = P[(i - 1) % n], P[(i + 1) % n]
    tx, tz = b_[0] - a_[0], b_[2] - a_[2]
    L = math.hypot(tx, tz)
    return -tz / L, tx / L


def at(row, off):
    nx, nz = nrm(row)
    return (P[row][0] + nx * off, P[row][2] + nz * off)


def walk(v, dist, direction):
    acc, i = 0.0, v
    while acc < dist:
        j = (i + direction) % n
        acc += math.hypot(P[j][0] - P[i][0], P[j][2] - P[i][2])
        i = j
    return i


def stub_at(piece, u, lat=0.0):
    pts = [(q[0], q[2]) for q in conns[piece]["points_xyz_m"]]
    acc, i = 0.0, 0
    while i < len(pts) - 2 and acc + math.dist(pts[i], pts[i + 1]) < u:
        acc += math.dist(pts[i], pts[i + 1])
        i += 1
    a_, b_ = pts[i], pts[i + 1]
    tx, tz = b_[0] - a_[0], b_[1] - a_[1]
    L = math.hypot(tx, tz) or 1.0
    t = (u - acc) / L
    return (a_[0] + tx * t - tz / L * lat, a_[1] + tz * t + tx / L * lat)


def shoot(path, eye_xy, target_xy, fov=72.0, eye_up=1.2, t_up=0.6):
    z = deck(*eye_xy)
    if z is None:
        raise SystemExit(f"no road under the eye of {path} at {eye_xy}")
    eye = Vector((eye_xy[0], eye_xy[1], z + eye_up))
    tz = deck(*target_xy, near=z)
    tgt = Vector((target_xy[0], target_xy[1], (tz if tz is not None else z) + t_up))
    cd.angle = math.radians(fov)
    cam.location = eye
    cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[stills] wrote", path, "eye", [round(c, 2) for c in eye], "target", [round(c, 2) for c in tgt])


lane = None
direction = 1
if LAYOUT != "street":
    bands = json.load(open(PROJ + "/data/barrier_bands.json", encoding="utf-8"))
    lane = bands["corridors"][LAYOUT]["lane_by_vertex"]
    lo = next(l for l in cfg["layouts"] if str(l["id"]) == LAYOUT)
    direction = -1 if str(lo.get("direction", "forward")) == "reverse" else 1


def type3(piece, u_bar, half):
    """a MUTCD Type III barricade sketch across the stub at u_bar: two posts and three 0.2 m rails at 0.6 / 0.95 /
    1.3 m, alternating orange / white 0.6 m stripes (preview only)"""
    orange, white = (0.95, 0.42, 0.05), (0.96, 0.96, 0.94)
    span = half + 0.6
    base = deck(*stub_at(piece, u_bar, 0.0)) or 0.0
    for k in (-1, 1):
        x, y = stub_at(piece, u_bar, k * (span - 0.3))
        vs = [(x - 0.05, y - 0.05, base), (x + 0.05, y - 0.05, base), (x + 0.05, y + 0.05, base), (x - 0.05, y + 0.05, base)]
        vs += [(p[0], p[1], base + 1.55) for p in vs]
        add_mesh("T3POST", vs, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)], (0.5, 0.5, 0.52))
    nseg = int(2 * span / 0.6)
    for h in (0.6, 0.95, 1.3):
        for s in range(nseg):
            l0 = -span + s * 0.6
            l1 = l0 + 0.6
            p0, p1 = stub_at(piece, u_bar - 0.05, l0), stub_at(piece, u_bar - 0.05, l1)
            vs = [(p0[0], p0[1], base + h), (p1[0], p1[1], base + h), (p1[0], p1[1], base + h + 0.2), (p0[0], p0[1], base + h + 0.2)]
            add_mesh("T3RAIL", vs, [(0, 1, 2, 3), (3, 2, 1, 0)], orange if s % 2 == 0 else white)
    px, py = stub_at(piece, u_bar - 0.08, -0.6)
    qx, qy = stub_at(piece, u_bar - 0.08, 0.6)
    vs = [(px, py, base + 1.55), (qx, qy, base + 1.55), (qx, qy, base + 2.05), (px, py, base + 2.05)]
    add_mesh("T3SIGN", vs, [(0, 1, 2, 3), (3, 2, 1, 0)], (0.97, 0.97, 0.97))


for s in stubs:
    mo = next(m for m in mouths if m["connector"] == s["connector"] and m.get("piece"))
    piece = mo["piece"]
    side = int(mo["side"])
    hv = int(mo["host_vertex"]) % n
    half = W[hv] / 2.0
    if LAYOUT == "street":
        travel = -1 if side == 1 else 1           # right-hand traffic: the lane on the stub's side runs this way
        ev = walk(hv, MOUTH_BACK_M, -travel)
        eye = at(ev, side * half * 0.45)
    else:
        travel = direction
        ev = walk(hv, MOUTH_BACK_M, -travel)
        y0, y1 = lane[ev]
        eye = at(ev, 0.5 * (y0 + y1))
    tgt = stub_at(piece, float(s["u_barrier_from_cut_m"]) - 1.0)
    shoot(f"{OUT}_{LAYOUT}_{s['id']}.png", eye, tgt)
    if LAYOUT == "street":
        w2 = float(conns[piece]["widths_m"][0]) / 2.0
        ein = stub_at(piece, float(s["u_mouth_from_cut_m"]) + IN_M, -w2 * 0.45)
        shoot(f"{OUT}_{LAYOUT}_{s['id']}_in.png", ein, stub_at(piece, float(s["u_barrier_from_cut_m"]), -w2 * 0.2), fov=75.0)
    if TYPE3 and TYPE3 == s["id"] and LAYOUT == "street":
        ob = stub_obs.get(("1WALL_STUB_" + s["id"]).upper())
        if ob is not None:
            ob.hide_render = True
        type3(piece, float(s["u_barrier_from_cut_m"]), float(conns[piece]["widths_m"][0]) / 2.0 + 1.58)
        shoot(f"{OUT}_{LAYOUT}_{s['id']}_type3.png", eye, tgt)
        shoot(f"{OUT}_{LAYOUT}_{s['id']}_in_type3.png", ein, stub_at(piece, float(s["u_barrier_from_cut_m"]), -w2 * 0.2),
              fov=75.0)
