"""Ledger 0054 P3: driver's-eye stills of the north network on a BUILT gate OBJ (Drive 1, v0.19.0).

    blender --background --factory-startup --python-exit-code 1 --python render_p3.py -- \\
        --obj <project>/data/track[.<layout>].obj --proj <project> --out <dir/prefix> --shots a,b,...

Engine frame x=E, y=up, z=N -> Blender (x, z, y). Workbench, back faces culled (as AC), each mesh group a flat colour
(road grey, curb pale, grass green, walls light, paint white / yellow), the eye 1.2 m over the BUILT road (a ray down
onto the 1ROAD sheets). The eye rides the north network's own drive lines (data/drive_lines.expansion.json, the right-hand
carriageway of each direction) at a station along them, looking ahead along the line (or at a named target). Shots:
  pv_descent      fwd, Princess View 70 m below J2, looking down the hill to J3
  j2              fwd, Waring 45 m before J2, looking into the J2 pad (Mound Ave + Waring SW barriered ahead / left)
  j3              fwd, Princess View 45 m before J3, looking into the J3 pad
  j4              fwd, Mission Gorge 45 m before J4, looking into the J4 pad (Jackson to the right)
  mg_cowles       fwd, Mission Gorge at its s 1865, looking at Cowles Mountain
  jackson_walls   fwd, Jackson north climbing at its s 1330 (the 1225-1525 cut wall on the right)
  stub_eldridge   fwd on Waring at Eldridge St, looking right into the barrier-closed stub
  stub_margerum   fwd on Mission Gorge at Margerum Ave, looking right into the barrier-closed stub
  j1_freeroam     the loop northbound on College 3 m right of the centre at v1500, straight on into Waring (W1)
  j5_freeroam     the loop eastbound on Navajo at v2307, into Jackson north (W5)
  (the same two on a race OBJ show the Speedway's curb strip sealing the opening)
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
       ("1WALL_STUB", (0.86, 0.85, 0.80)), ("1WALL", (0.80, 0.80, 0.78)), ("SIGNARROW", (0.03, 0.03, 0.03)),
       ("SIGNPLATE", (0.95, 0.78, 0.05)), ("SIGNPOST", (0.55, 0.55, 0.57)), ("SCRUB", (0.36, 0.42, 0.22))]


def color_of(name):
    u = name.upper()
    for p, c in COL:
        if u.startswith(p):
            return c
    return None


gc = json.load(open(PROJ + "/data/gate_centerline.json", encoding="utf-8"))
P = gc["points_xyz_m"]
n = len(P) - 1
lines = json.load(open(PROJ + "/data/drive_lines.expansion.json", encoding="utf-8"))["lines"]
exp = json.load(open(PROJ + "/data/expansion.north.json", encoding="utf-8"))
pieces = {p["id"]: p for p in exp["pieces"]}
conns = json.load(open(PROJ + "/data/connectors.local.json", encoding="utf-8"))["connectors"]
o = exp["frame"]["origin"]


def lonlat_xz(lon, lat):
    ph = math.radians(o["lat"])
    m_lat = 111132.954 - 559.822 * math.cos(2 * ph) + 1.175 * math.cos(4 * ph)
    m_lon = 111412.84 * math.cos(ph) - 93.5 * math.cos(3 * ph) + 0.118 * math.cos(5 * ph)
    return ((lon - o["lon"]) * m_lon, (lat - o["lat"]) * m_lat)


COWLES = lonlat_xz(-117.0309, 32.8128)        # Cowles Mountain's summit (485 m)


def piece_xz(pid, s):
    rows = pieces[pid]["stations"]
    cols = pieces[pid]["columns"]
    i = min(range(len(rows)), key=lambda k: abs(rows[k][0] - s))
    return rows[i][cols.index("x")], rows[i][cols.index("z")]


def line_at_near(name, xz, ahead):
    """(eye xz, target xz) on line `name`: its point nearest xz, and its point `ahead` metres further along"""
    pts = [(q[0], q[2]) for q in lines[name]["points_xyz_m"]]
    i = min(range(len(pts)), key=lambda k: (pts[k][0] - xz[0]) ** 2 + (pts[k][1] - xz[1]) ** 2)
    acc, j = 0.0, i
    while j < len(pts) - 1 and acc < ahead:
        acc += math.dist(pts[j], pts[j + 1])
        j += 1
    return pts[i], pts[j], i


def ring(row, off):
    a_, b_ = P[(row - 1) % n], P[(row + 1) % n]
    tx, tz = b_[0] - a_[0], b_[2] - a_[2]
    L = math.hypot(tx, tz)
    return (P[row][0] - tz / L * off, P[row][2] + tx / L * off)


def stub_view(prefix):
    c = next(c for c in conns if c["name"].startswith("STUB_" + prefix))
    q = c["points_xyz_m"]
    mouth, far = (q[0][0], q[0][2]), (q[-1][0], q[-1][2])
    return mouth, far


SHOTDEF = {}
SHOTDEF["pv_descent"] = lambda: line_at_near("fwd", piece_xz("B", 70.0), 120.0)[:2]
SHOTDEF["j2"] = lambda: line_at_near("fwd", piece_xz("A", 915.0), 60.0)[:2]
SHOTDEF["j3"] = lambda: line_at_near("fwd", piece_xz("B", 1035.0), 60.0)[:2]
SHOTDEF["j4"] = lambda: line_at_near("fwd", piece_xz("C", 2205.0), 60.0)[:2]
SHOTDEF["mg_cowles"] = lambda: (line_at_near("fwd", piece_xz("C", 1865.0), 0.0)[0], COWLES)
SHOTDEF["jackson_walls"] = lambda: line_at_near("fwd", piece_xz("D", 1330.0), 80.0)[:2]


def _stub_shot(prefix, back):
    mouth, far = stub_view(prefix)
    e, _t, _i = line_at_near("fwd", mouth, 0.0)
    pts = [(q[0], q[2]) for q in lines["fwd"]["points_xyz_m"]]
    i = min(range(len(pts)), key=lambda k: (pts[k][0] - e[0]) ** 2 + (pts[k][1] - e[1]) ** 2)
    acc, j = 0.0, i
    while j > 0 and acc < back:
        acc += math.dist(pts[j], pts[j - 1])
        j -= 1
    return pts[j], far


SHOTDEF["stub_eldridge"] = lambda: _stub_shot("eldridge_street_6013754_R", 22.0)
SHOTDEF["stub_margerum"] = lambda: _stub_shot("margerum_avenue", 22.0)
SHOTDEF["j1_freeroam"] = lambda: (ring(1500, -3.0), ring(1530, 25.0))
SHOTDEF["j5_freeroam"] = lambda: (ring(2307, -3.0), ring(2318, 25.0))
CAMS = {s: SHOTDEF[s]() for s in SHOTS}
FOCUS = [c[0] for c in CAMS.values()]
KEEP = 900.0

bpy.ops.wm.read_factory_settings(use_empty=True)
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
            far_ok = cur.upper().startswith("GRASS_FAR")
            if far_ok or min((p0[0] - fx) ** 2 + (p0[1] - fz) ** 2 for fx, fz in FOCUS) <= KEEP * KEEP:
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
    if nm.upper().startswith(("1ROAD", "1GRASS", "GRASS_FAR")):
        road_parts.append((vs, fs, nm.upper().startswith("1ROAD")))
rv, rf, gv, gf = [], [], [], []
for vs, fs, is_road in road_parts:
    tv, tf = (rv, rf) if is_road else (gv, gf)
    off = len(tv)
    tv += vs
    tf += [[i + off for i in q] for q in fs]
road = BVHTree.FromPolygons(rv, rf)
ground = BVHTree.FromPolygons(gv, gf) if gv else None


def hit(tree, x, y):
    if tree is None:
        return None
    h = tree.ray_cast(Vector((x, y, 3000.0)), Vector((0, 0, -1)))
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
for s in SHOTS:
    e, t = CAMS[s]
    z = hit(road, *e)
    if z is None:
        raise SystemExit(f"no road under {s} at {e}")
    eye = Vector((e[0], e[1], z + 1.2))
    tz = hit(road, *t)
    if tz is None:
        tz = hit(ground, *t)
    tgt = Vector((t[0], t[1], (tz if tz is not None else z) + 0.6))
    cd.angle = math.radians(75.0)
    cam.location = eye
    cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{OUT}_{s}.png"
    bpy.ops.render.render(write_still=True)
    print("[render] wrote", sc.render.filepath, "eye", [round(c, 2) for c in eye], "target", [round(c, 2) for c in tgt])
