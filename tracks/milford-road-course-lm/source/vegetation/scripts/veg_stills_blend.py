"""Milford vegetation pass stills (ledger 0082): the same cameras on 0.1.2 (its TREECARD cards, in the kn5) and 0.1.3 (TreeFX,
drawn by the game, not in the kn5). For 0.1.3 the trees are STAND-INS at the planted spots: a trunk and an ellipsoid crown at
each tree's measured height and measured crown width; the game draws Lake Murray's TreeFX models there instead. Not a gate
(L12: show, don't assert). Camera, sun and render as source/furniture/furniture_stills_pass2_blend.py.

    blender --background --factory-startup --python-exit-code 1 --python veg_stills_blend.py -- \
        <project> <trees.lm.json | none> <out-prefix> [<shots.json>]

shots.json (Milford 0.1.5, optional): a list of shots taken INSTEAD of the default set, each either a seat view
{"name", "s": lap station m, "ahead": m (60), "fov": deg (70)} or a free camera {"name", "eye": [x, y, dz], "look": [x, y, dz],
"fov"} in the split scene's plan (x = E, y = N), dz over the ground under that point.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
PROJ, TREES, OUT = Path(a[0]), a[1], a[2]
SHOTS = json.loads(Path(a[3]).read_text(encoding="utf-8")) if len(a) > 3 else None
EYE_M = 1.2


def bvh(prefixes):
    verts, polys = [], []
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.name.upper().startswith(prefixes):
            continue
        off = len(verts)
        verts += [o.matrix_world @ Vector(v.co) for v in o.data.vertices]
        polys += [[off + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def z_at(tree, x, y, default=None):
    hit = tree.ray_cast(Vector((x, y, 3000.0)), Vector((0, 0, -1)), 6000.0)
    return default if hit[0] is None else hit[0].z


bpy.ops.wm.open_mainfile(filepath=str(PROJ / "blender" / "split" / "loop_main.blend"))
road = bvh(("1ROAD",))
ground = bvh(("1ROAD", "1GRASS", "1KERB", "GRASS_FAR"))
cl = json.loads((PROJ / "data" / "centerline.local.json").read_text(encoding="utf-8"))
origin = cl["origin"]
pts = [(p[0], p[2]) for p in cl["points_xyz_m"]]
phi = math.radians(origin["lat"])
m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
to_xy = lambda lon, lat: ((lon - origin["lon"]) * m_lon, (lat - origin["lat"]) * m_lat)

n_stand = 0
if TREES != "none":
    d = json.loads(Path(TREES).read_text(encoding="utf-8"))
    verts, faces = [], []
    tv, tf = [], []
    SEG, RING = 10, 6
    for lon, lat, _zone, h, w, *_ in d["points"]:
        x, y = to_xy(lon, lat)
        g = z_at(ground, x, y)
        if g is None:
            continue
        crown_h = max(2.0, 0.62 * h)                # the stand-in's crown: its lower 38 % is bole [stand-in shape only]
        rx = max(1.0, w / 2.0)
        cz = g + h - crown_h / 2
        base = len(verts)
        for j in range(1, RING):
            t = math.pi * j / RING
            for i in range(SEG):
                p = 2 * math.pi * i / SEG
                verts.append((x + rx * math.sin(t) * math.cos(p), y + rx * math.sin(t) * math.sin(p), cz + crown_h / 2 * math.cos(t)))
        top, bot = len(verts), len(verts) + 1
        verts += [(x, y, cz + crown_h / 2), (x, y, cz - crown_h / 2)]
        for j in range(RING - 2):
            for i in range(SEG):
                a0 = base + j * SEG + i
                a1 = base + j * SEG + (i + 1) % SEG
                faces.append((a0, a1, a1 + SEG, a0 + SEG))
        for i in range(SEG):
            faces.append((top, base + (i + 1) % SEG, base + i))
            last = base + (RING - 2) * SEG
            faces.append((bot, last + i, last + (i + 1) % SEG))
        tb = len(tv)
        r = 0.25
        for i in range(6):
            p = 2 * math.pi * i / 6
            tv += [(x + r * math.cos(p), y + r * math.sin(p), g - 0.2), (x + r * math.cos(p), y + r * math.sin(p), cz)]
        for i in range(6):
            k, k1 = tb + 2 * i, tb + 2 * ((i + 1) % 6)
            tf.append((k, k1, k1 + 1, k + 1))
        n_stand += 1
    for name, V, F, col in (("STANDIN_CROWN", verts, faces, (0.16, 0.30, 0.10, 1)), ("STANDIN_TRUNK", tv, tf, (0.25, 0.19, 0.13, 1))):
        me = bpy.data.meshes.new(name)
        me.from_pydata(V, [], F)
        me.update()
        ob = bpy.data.objects.new(name, me)
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = col
        mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
        me.materials.append(mat)
        bpy.context.scene.collection.objects.link(ob)
print(f"[stills] stand-in trees: {n_stand}; cards in the scene: {sum(1 for o in bpy.data.objects if o.name.upper().startswith('TREECARD'))} objects")

sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.render.resolution_x, sc.render.resolution_y = 1400, 788
sc.render.image_settings.file_format = "JPEG"
sc.render.image_settings.quality = 82
w = bpy.data.worlds.new("still")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.74, 0.92, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
sc.world = w
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 3.5
ob = bpy.data.objects.new("sun", sun)
az, el = math.radians(113.0), math.radians(42.0)          # NAIP 2022's own sun (source/furniture/sun.py)
ob.rotation_mode = "QUATERNION"
ob.rotation_quaternion = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))).to_track_quat("Z", "Y")
sc.collection.objects.link(ob)
cam = bpy.data.cameras.new("cam")
cam.clip_end = 8000
cam_ob = bpy.data.objects.new("cam", cam)
sc.collection.objects.link(cam_ob)
sc.camera = cam_ob


def shoot(name, eye, look, fov=62.0):
    cam.angle = math.radians(fov)
    cam_ob.location = Vector(eye)
    cam_ob.rotation_mode = "QUATERNION"
    cam_ob.rotation_quaternion = (Vector(look) - Vector(eye)).to_track_quat("-Z", "Y")
    sc.render.filepath = f"{OUT}_{name}.jpg"
    bpy.ops.render.render(write_still=True)
    print(f"[stills] {name}: eye {tuple(round(v, 1) for v in eye)} -> {tuple(round(v, 1) for v in look)}")


lap = [0.0]
for i in range(1, len(pts)):
    lap.append(lap[-1] + math.dist(pts[i - 1], pts[i]))


def at(s):
    s %= lap[-1]
    i = max(0, min(len(lap) - 2, next(k for k in range(len(lap) - 1) if lap[k + 1] >= s)))
    t = (s - lap[i]) / max(1e-6, lap[i + 1] - lap[i])
    return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)


def seat(name, s, ahead=60.0, fov=70.0):
    ex, ey = at(s)
    lx, ly = at(s + ahead)
    ez = z_at(road, ex, ey, 0.0) + EYE_M
    lz = z_at(road, lx, ly, ez - EYE_M) + EYE_M
    shoot(name, (ex, ey, ez), (lx, ly, lz), fov=fov)


if SHOTS is not None:
    for q in SHOTS:
        if "s" in q:
            seat(q["name"], float(q["s"]), float(q.get("ahead", 60.0)), float(q.get("fov", 70.0)))
        else:
            (ex, ey, ez), (lx, ly, lz) = q["eye"], q["look"]
            shoot(q["name"], (ex, ey, z_at(ground, ex, ey, 0.0) + ez), (lx, ly, z_at(ground, lx, ly, 0.0) + lz), float(q.get("fov", 60.0)))
else:
    # the driver's seat: every 1/8 of the lap, looking 60 m down the road
    for k in range(8):
        s = lap[-1] * k / 8
        seat(f"seat_s{int(s):04d}", s)
    # aerial-style overviews
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    gz = z_at(ground, cx, cy, 0.0)
    shoot("above_lap_from_sw", (cx - 450.0, cy - 650.0, gz + 380.0), (cx, cy, gz), fov=55.0)
    shoot("above_lap_from_ne", (cx + 450.0, cy + 650.0, gz + 380.0), (cx, cy, gz), fov=55.0)
    shoot("above_infield_low", (cx + 150.0, cy - 250.0, gz + 120.0), (cx - 20.0, cy + 60.0, gz), fov=60.0)
print("[stills] done")
