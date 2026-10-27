"""Ledger 0054 P4 (buildings + rock): driver's-eye stills of the north network on a BUILT gate OBJ.

    blender --background --factory-startup --python-exit-code 1 --python render_p4_buildings.py -- \\
        --obj <project>/data/track[.<layout>].obj --proj <project> --out <dir/prefix> --shots a,b,...

A copy of p3-proofs/render_p3.py with the P4 buildings / rock shots and the rock tiles' own colour (1GRASS_ROCK before
1GRASS: tan sandstone, so a still shows where the grass ends and the cut face begins). Engine frame x=E, y=up, z=N ->
Blender (x, z, y). Workbench, back faces culled (as AC), each mesh group a flat colour, the eye 1.2 m over the BUILT road
(a ray down onto the 1ROAD sheets), riding the north network's own drive lines (data/drive_lines.expansion.json). Shots:
  jackson_walls      fwd, Jackson north climbing at its s 1330 (the 1225-1525 cut wall on the right), as P3's still
  jackson_walls_rev  rev, Jackson north at its s 1150 looking down the climb (the 1005-1120 / 1225-1525 walls on the left)
  jackson_toe        a close look at the foot of the Jackson 320-485 cut: the eye 1.6 m over the sidewalk at D s 440, looking
                     along the toe (the thin lighter triangles of P3 "Left", before / after)
  mg_cut_cowles      fwd, Mission Gorge at its s 1465: the south rock face (s 1475-1560) on the right, Cowles ahead
  mg_apartments      fwd, Mission Gorge at its s 650, a LEVEL camera toward the apartment blocks on the south side (C 500-1000)
  grantville_waring  fwd, Waring at its s 900 toward J2 and Princess View: the Grantville roofs beyond
  grantville_pv      fwd, Princess View at its s 760 (the self-storage and industry on both sides, B 750-1078)
  j5_shops           the loop eastbound on Navajo at v2307 into Jackson north: the shops at Navajo / Jackson
"""
import bpy, sys, math, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
arg = lambda k, d=None: a[a.index(k) + 1] if k in a else d
OBJ, PROJ, OUT = arg("--obj"), arg("--proj"), arg("--out")
SHOTS = (arg("--shots") or "").split(",")
COL = [("GRASS_FAR", (93 / 255, 93 / 255, 66 / 255)), ("1GRASS_ROCK", (0.66, 0.56, 0.42)),
       ("1GRASS", (68 / 255, 92 / 255, 40 / 255)), ("1ROAD", (0.34, 0.34, 0.35)),
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


def piece_xz(pid, s):
    rows = pieces[pid]["stations"]
    cols = pieces[pid]["columns"]
    i = min(range(len(rows)), key=lambda k: abs(rows[k][0] - s))
    return rows[i][cols.index("x")], rows[i][cols.index("z")]


def piece_off(pid, s, off):
    """a point `off` metres LEFT of the piece's forward direction (negative = right) at station s"""
    rows = pieces[pid]["stations"]
    cols = pieces[pid]["columns"]
    ix, iz = cols.index("x"), cols.index("z")
    i = min(range(len(rows)), key=lambda k: abs(rows[k][0] - s))
    j = min(i + 1, len(rows) - 1); h = max(i - 1, 0)
    tx, tz = rows[j][ix] - rows[h][ix], rows[j][iz] - rows[h][iz]
    L = math.hypot(tx, tz) or 1.0
    return (rows[i][ix] - tz / L * off, rows[i][iz] + tx / L * off)


def line_at_near(name, xz, ahead):
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


# (eye xz, target xz[, level[, eye height over the surface[, surface: "road" | "any"]]])
SHOTDEF = {}
SHOTDEF["jackson_walls"] = lambda: line_at_near("fwd", piece_xz("D", 1330.0), 80.0)[:2]
SHOTDEF["jackson_walls_rev"] = lambda: line_at_near("rev", piece_xz("D", 1150.0), 90.0)[:2]
SHOTDEF["jackson_toe"] = lambda: (piece_off("D", 440.0, -14.0), piece_off("D", 452.0, -16.5), False, 1.6, "any")
SHOTDEF["mg_cut_cowles"] = lambda: line_at_near("fwd", piece_xz("C", 1465.0), 70.0)[:2]
SHOTDEF["mg_apartments"] = lambda: (line_at_near("fwd", piece_xz("C", 650.0), 0.0)[0], piece_off("C", 720.0, -70.0), True)
SHOTDEF["grantville_waring"] = lambda: line_at_near("fwd", piece_xz("A", 900.0), 120.0)[:2]
SHOTDEF["grantville_pv"] = lambda: line_at_near("fwd", piece_xz("B", 760.0), 90.0)[:2]
SHOTDEF["j5_shops"] = lambda: (ring(2307, -3.0), ring(2318, 25.0))
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
            far_ok = cur.upper().startswith(("GRASS_FAR", "1GRASS"))
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
    if nm.upper().startswith(("1ROAD", "1GRASS", "GRASS_FAR", "1KERB")):
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
    e, t = CAMS[s][:2]
    level = len(CAMS[s]) > 2 and CAMS[s][2]
    eye_h = CAMS[s][3] if len(CAMS[s]) > 3 else 1.2
    surf = CAMS[s][4] if len(CAMS[s]) > 4 else "road"
    z = hit(road, *e)
    if z is None and surf == "any":
        z = hit(ground, *e)
    if z is None:
        raise SystemExit(f"no road under {s} at {e}")
    eye = Vector((e[0], e[1], z + eye_h))
    tz = hit(road, *t)
    if tz is None:
        tz = hit(ground, *t)
    tgt = Vector((t[0], t[1], (tz if tz is not None else z) + 0.6))
    if level:
        tgt.z = eye.z
    cd.angle = math.radians(75.0)
    cam.location = eye
    cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{OUT}_{s}.png"
    bpy.ops.render.render(write_still=True)
    print("[render] wrote", sc.render.filepath, "eye", [round(c, 2) for c in eye], "target", [round(c, 2) for c in tgt])
