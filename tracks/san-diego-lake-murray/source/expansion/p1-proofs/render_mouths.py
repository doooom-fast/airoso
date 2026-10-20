"""Ledger 0054 P1: driver's-eye stills of the two rehearsed weld mouths (W1 at J1, W5 at J5) on a BUILT gate OBJ.

    blender --background --factory-startup --python-exit-code 1 --python render_mouths.py -- \\
        --obj <project>/data/track[.<layout>].obj --proj <project> --out <prefix> --shots a,b,...

Engine frame x=E, y=up, z=N -> Blender (x, z, y). Workbench, back faces culled (as AC), each mesh group in a flat
colour (road grey, curb pale, grass green, walls light, paint white / yellow) so steps and seams read. The eye stands on
the BUILT road (a ray down onto the 1ROAD sheets) at a driver's 1.2 m. Shots:
  j1_college_nb   Free Roam: northbound on College, 3 m right of the centre at v1500, looking straight on into Waring (W1)
  j1_waring_sb    on the Waring stub 45 m out, looking back at the J1 corner (the weld seam across the loop edge)
  j1_race         race_cw / race_acw OBJ: the same College approach, the curb strip sealing the opening
  j5_navajo_eb    Free Roam: eastbound on Navajo at v2307 (3 m right of the centre), looking into Jackson north (W5)
  j5_jackson_sb   on the Jackson-north stub 45 m out, looking back down at the Navajo/Jackson corner
  j5_race         race OBJ: the Navajo approach, the strip sealing the Jackson-north opening
  j1_return       (P1 fix round) Free Roam: on the loop's outer lane at v1535 looking back at the J1 R 30 return (apron
                  AP1, its curb + walk, lamp 77 behind it, the ground beyond)
"""
import bpy, sys, math, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
arg = lambda k, d=None: a[a.index(k) + 1] if k in a else d
OBJ, PROJ, OUT = arg("--obj"), arg("--proj"), arg("--out")
SHOTS = (arg("--shots") or "").split(",")
COL = [("GRASS_FAR", (93 / 255, 93 / 255, 66 / 255)), ("1GRASS", (68 / 255, 92 / 255, 40 / 255)), ("1ROAD", (0.34, 0.34, 0.35)),
       ("1KERB_RACE", (0.62, 0.10, 0.08)), ("1KERB", (0.66, 0.66, 0.64)), ("MARKINGS", (0.92, 0.92, 0.90)),
       ("YLINE", (0.85, 0.68, 0.1)), ("HOUSE", (0.78, 0.70, 0.58)), ("BUILDING", (0.72, 0.72, 0.70)),
       ("BRIDGESTRUCT", (0.70, 0.69, 0.66)), ("LIGHTPOST", (0.25, 0.25, 0.27)), ("LIGHTS", (0.9, 0.8, 0.5)),
       ("1WALL", (0.80, 0.80, 0.78)), ("SIGNARROW", (0.03, 0.03, 0.03)), ("SIGNPLATE", (0.95, 0.78, 0.05)),
       ("SIGNPOST", (0.55, 0.55, 0.57)), ("MEDIAN", (0.40, 0.55, 0.30)), ("ISLAND", (0.40, 0.55, 0.30))]


def color_of(name):
    u = name.upper()
    for p, c in COL:
        if u.startswith(p):
            return c
    return None


bpy.ops.wm.read_factory_settings(use_empty=True)
gc = json.load(open(PROJ + "/data/gate_centerline.json", encoding="utf-8"))
P = gc["points_xyz_m"]
n = len(P) - 1
conns = {c["name"]: c for c in json.load(open(PROJ + "/data/connectors.local.json", encoding="utf-8"))["connectors"]}
FOCUS = [(P[1517][0], P[1517][2]), (P[2318][0], P[2318][2])]
KEEP = 700.0

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


road_parts = []
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
    if nm.upper().startswith("1ROAD"):
        road_parts.append((vs, fs))
rv, rf = [], []
for vs, fs in road_parts:
    off = len(rv)
    rv += vs
    rf += [[i + off for i in q] for q in fs]
road = BVHTree.FromPolygons(rv, rf)


def deck(x, y):
    h = road.ray_cast(Vector((x, y, 3000.0)), Vector((0, 0, -1)))
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


def normal(i):
    a_, b_ = P[(i - 1) % n], P[(i + 1) % n]
    tx, tz = b_[0] - a_[0], b_[2] - a_[2]
    L = math.hypot(tx, tz)
    return -tz / L, tx / L


def at(row, off):
    nx, nz = normal(row)
    return (P[row][0] + nx * off, P[row][2] + nz * off)


def stub_at(prefix, u_from_cut, lat=0.0):
    c = next(v for k, v in conns.items() if k.startswith(prefix))
    pts = [(q[0], q[2]) for q in c["points_xyz_m"]]
    acc, i = 0.0, 0
    while i < len(pts) - 1 and acc + math.dist(pts[i], pts[i + 1]) < u_from_cut:
        acc += math.dist(pts[i], pts[i + 1])
        i += 1
    a_, b_ = pts[i], pts[min(i + 1, len(pts) - 1)]
    tx, tz = b_[0] - a_[0], b_[1] - a_[1]
    L = math.hypot(tx, tz) or 1.0
    t = (u_from_cut - acc) / L
    return (a_[0] + tx * t - tz / L * lat, a_[1] + tz * t + tx / L * lat)


def shoot(name, eye_xy, eye_up, target_xy, fov=70.0, t_up=0.6):
    z = deck(*eye_xy)
    if z is None:
        raise SystemExit(f"no road under {name} at {eye_xy}")
    eye = Vector((eye_xy[0], eye_xy[1], z + eye_up))
    tz = deck(*target_xy)
    tgt = Vector((target_xy[0], target_xy[1], (tz if tz is not None else z) + t_up))
    cd.angle = math.radians(fov)
    cam.location = eye
    cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{OUT}_{name}.png"
    bpy.ops.render.render(write_still=True)
    print("[render] wrote", sc.render.filepath, "eye", [round(c, 2) for c in eye], "target", [round(c, 2) for c in tgt])


for s in SHOTS:
    if s == "j1_college_nb":
        shoot(s, at(1500, -3.0), 1.2, stub_at("north_J1", 25.0), 75.0)
    elif s == "j1_waring_sb":
        shoot(s, stub_at("north_J1", 45.0, 6.0), 1.2, at(1517, 4.0), 75.0)
    elif s == "j1_race":
        shoot(s, at(1503, -3.0), 1.2, stub_at("north_J1", 15.0), 75.0)
    elif s == "j5_navajo_eb":
        shoot(s, at(2307, -3.0), 1.2, stub_at("north_J5", 12.0), 80.0)
    elif s == "j5_jackson_sb":
        shoot(s, stub_at("north_J5", 45.0, 6.0), 1.2, at(2320, 4.0), 75.0)
    elif s == "j1_return":
        shoot(s, at(1535, 6.0), 1.2, at(1521, 17.0), 75.0)
    elif s == "j5_race":
        shoot(s, at(2307, -3.0), 1.2, stub_at("north_J5", 12.0), 80.0)
    else:
        raise SystemExit("unknown shot " + s)
