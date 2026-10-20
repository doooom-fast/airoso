"""Ledger 0054 P2 step 6: preview stills of the grown ground from the four fixed camera stations (EXPANSION-PLAN), on a
BUILT rehearsal gate OBJ (every 1GRASS* / GRASS_FAR* / building / road triangle within 12 km; L5: the artifact).

    blender --background --factory-startup --python-exit-code 1 --python render_views.py -- \\
        --obj <project>/data/track.obj --inter <airoso>/tracks/san-diego-lake-murray/data/expansion.north.json \\
        --out <prefix>

Engine frame x = E, y = up, z = N -> Blender (x, z, y). Workbench, back faces culled (as AC), flat colours (physical
ground green, the far ring tan, road grey, buildings pale). P2 builds no north road: the eye stands 1.2 m over the
BUILT ground at the station (3DEP's own road surface there), and the planned pavement of the intermediate
(data/expansion.north.json: each piece's two curb lines, the J2-J4 pad outlines) is drawn as pale 0.6 m strips
0.15 m over the ground so the road-to-be reads; it is not geometry of the build. Stations (junction-node frame):
  j3_north     J3 (Princess View / Mission Gorge), looking north over the valley at the north wall
  mg1865       Mission Gorge s 1865, looking at Cowles
  jackson1050  Jackson north s 1050, looking at Cowles
  j4_pyles     the J4 approach, Mission Gorge s 2190, looking north-east at Pyles (Kwaay Paay hidden behind a knoll)
"""
import bpy, sys, math, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
arg = lambda k, d=None: a[a.index(k) + 1] if k in a else d
OBJ, INTER, OUT = arg("--obj"), arg("--inter"), arg("--out")
COL = [("GRASS_FAR", (0.47, 0.43, 0.31)), ("1GRASS", (0.30, 0.40, 0.19)), ("1ROAD", (0.30, 0.30, 0.31)),
       ("1KERB", (0.66, 0.66, 0.64)), ("HOUSE", (0.80, 0.72, 0.60)), ("BUILDING", (0.74, 0.74, 0.72)),
       ("BRIDGESTRUCT", (0.70, 0.69, 0.66)), ("1WALL", (0.80, 0.80, 0.78))]
COWLES, PYLES = (1380.0, 2700.0), (792.9, 3848.7)


def color_of(name):
    u = name.upper()
    for p, c in COL:
        if u.startswith(p):
            return c
    return None


bpy.ops.wm.read_factory_settings(use_empty=True)
X = json.load(open(INTER, encoding="utf-8"))
PIECE = {p["id"]: p for p in X["pieces"]}


def piece_rows(pid):
    p = PIECE[pid]
    col = {c: k for k, c in enumerate(p["columns"])}
    return [(r[col["s"]], r[col["x"]], r[col["z"]], r[col["left_m"]], r[col["right_m"]]) for r in p["stations"]]


def station(pid, s):
    rows = piece_rows(pid)
    k = min(range(len(rows)), key=lambda i: abs(rows[i][0] - s))
    a_, b_ = rows[max(0, k - 2)], rows[min(len(rows) - 1, k + 2)]
    tx, tz = b_[1] - a_[1], b_[2] - a_[2]
    L = math.hypot(tx, tz) or 1.0
    return (rows[k][1], rows[k][2]), (tx / L, tz / L)


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
            groups[cur].append([int(t.split("/")[0]) - 1 for t in ln.split()[1:]])

mats = {}


def solid_mat(col):
    if col in mats:
        return mats[col]
    m = bpy.data.materials.new("m%d" % len(mats))
    m.diffuse_color = (*col, 1.0)
    mats[col] = m
    return m


ground_parts = []
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
    me = bpy.data.meshes.new(nm)
    me.from_pydata(vs, [], fs)
    me.update()
    ob = bpy.data.objects.new(nm, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(solid_mat(color_of(nm)))
    if nm.upper().startswith(("1GRASS", "GRASS_FAR")):
        ground_parts.append((vs, fs))
gv, gf = [], []
for vs, fs in ground_parts:
    off = len(gv)
    gv += vs
    gf += [[i + off for i in q] for q in fs]
ground = BVHTree.FromPolygons(gv, gf)


def gz(x, y):
    h = ground.ray_cast(Vector((x, y, 3000.0)), Vector((0, 0, -1)))
    return h[0].z if h[0] is not None else None


# the planned pavement, drawn as its two curb lines (0.6 m strips, 0.15 m over the ground) and the pads' outlines, so
# the ground under the road-to-be stays visible
ov_v, ov_f = [], []


def strip(pts, w=0.6, lift=0.15):
    for (x0_, z0_), (x1_, z1_) in zip(pts, pts[1:]):
        tx, tz = x1_ - x0_, z1_ - z0_
        L = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / L * w / 2, tx / L * w / 2
        b0 = len(ov_v)
        for (px, pz) in ((x0_ + nx, z0_ + nz), (x0_ - nx, z0_ - nz), (x1_ - nx, z1_ - nz), (x1_ + nx, z1_ + nz)):
            ov_v.append((px, pz, (gz(px, pz) or 0.0) + lift))
        ov_f.append([b0, b0 + 1, b0 + 2, b0 + 3])


for pid in PIECE:
    rows = piece_rows(pid)
    for side in (3, 4):
        line = []
        for k in range(len(rows)):
            a_, b_ = rows[max(0, k - 1)], rows[min(len(rows) - 1, k + 1)]
            tx, tz = b_[1] - a_[1], b_[2] - a_[2]
            L = math.hypot(tx, tz) or 1.0
            off = rows[k][side]
            line.append((rows[k][1] - tz / L * off, rows[k][2] + tx / L * off))
        strip(line)
for pad in X.get("pads", []):
    ring = [tuple(q) for q in pad["outline_xz"]]
    strip(ring + [ring[0]])
me = bpy.data.meshes.new("PLANNED_PAVEMENT")
me.from_pydata(ov_v, [], ov_f)
me.update()
ob = bpy.data.objects.new("PLANNED_PAVEMENT", me)
bpy.context.scene.collection.objects.link(ob)
me.materials.append(solid_mat((0.92, 0.92, 0.88)))

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"
sh.color_type = "MATERIAL"
sh.show_shadows = True
sh.shadow_intensity = 0.45
sh.show_cavity = True
sh.cavity_type = "WORLD"
sh.show_backface_culling = False
sh.show_specular_highlight = False
sh.background_type = "WORLD"
world = bpy.data.worlds.new("sky")
world.color = (0.58, 0.72, 0.88)
sc.world = world
sc.display.light_direction = (0.35, -0.45, 0.82)
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.view_settings.view_transform = "Standard"
cd = bpy.data.cameras.new("cam")
cd.sensor_fit = "HORIZONTAL"
cd.clip_start = 0.1
cd.clip_end = 20000.0
cam = bpy.data.objects.new("cam", cd)
sc.collection.objects.link(cam)
sc.camera = cam


def shoot(name, eye_xy, look_xy=None, bearing=None, pitch=2.0, fov=75.0):
    z = gz(*eye_xy)
    if z is None:
        raise SystemExit(f"no ground under {name} at {eye_xy}")
    eye = Vector((eye_xy[0], eye_xy[1], z + 1.2))
    if look_xy is not None:
        tz = gz(*look_xy)
        d = math.hypot(look_xy[0] - eye_xy[0], look_xy[1] - eye_xy[1])
        # the summit in the upper third of the frame: aim 4 degrees under it
        tgt = Vector((look_xy[0], look_xy[1], (tz if tz is not None else z) - math.tan(math.radians(4.0)) * d))
    else:
        b = math.radians(bearing)
        tgt = eye + Vector((math.sin(b) * 1000.0, math.cos(b) * 1000.0, math.tan(math.radians(pitch)) * 1000.0))
    cd.angle = math.radians(fov)
    cam.location = eye
    cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{OUT}_{name}.png"
    bpy.ops.render.render(write_still=True)
    print("[render] wrote", sc.render.filepath, "eye", [round(c, 1) for c in eye], "target", [round(c, 1) for c in tgt])


j3 = X["junctions"]["J3"]["xz"]
# J3: stand 25 m east of the node on Mission Gorge (piece C s ~25), look due north over the valley
(cx, cz), _t = station("C", 30.0)
shoot("j3_north", (cx, cz), bearing=0.0, pitch=3.0, fov=80.0)
(mx, mz), _t = station("C", 1865.0)
shoot("mg1865_cowles", (mx, mz), look_xy=COWLES, fov=70.0)
(jx, jz), _t = station("D", 1050.0)
shoot("jackson1050_cowles", (jx, jz), look_xy=COWLES, fov=70.0)
(px, pz), _t = station("C", 2190.0)
shoot("j4_approach_pyles", (px, pz), look_xy=PYLES, fov=70.0)
