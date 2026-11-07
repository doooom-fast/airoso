"""Milford furniture pass 2 stills (ledger 0082): what changed, F1's screen along the NW boundary, from the driver's seat
and from above, on a build's SPLIT road scene. Run it on 0.1.1 (c2) and on 0.1.2 (c3) for the before / after. Not a gate
(L12: show, don't assert). Same camera, sun and render as furniture_stills_blend.py.

    blender --background --factory-startup --python-exit-code 1 --python furniture_stills_pass2_blend.py -- \
        <project> <source/lidar/f1_entries.json> <out-prefix>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
PROJ, F1, OUT = Path(a[0]), Path(a[1]), a[2]
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
ground = bvh(("1ROAD", "1GRASS", "1KERB"))
cl = json.loads((PROJ / "data" / "centerline.local.json").read_text(encoding="utf-8"))
origin = cl["origin"]
pts = [(p[0], p[2]) for p in cl["points_xyz_m"]]
phi = math.radians(origin["lat"])
m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
to_xy = lambda p: ((p[0] - origin["lon"]) * m_lon, (p[1] - origin["lat"]) * m_lat)

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


def nearest_i(x, y):
    return min(range(len(pts)), key=lambda i: (pts[i][0] - x) ** 2 + (pts[i][1] - y) ** 2)


def along(i, metres):
    """the lap point `metres` from i (negative = back)"""
    s, j, step = 0.0, i, (1 if metres > 0 else -1)
    while s < abs(metres):
        k = (j + step) % len(pts)
        s += math.dist(pts[j], pts[k])
        j = k
    return pts[j]


pieces = {p["tag"]: [to_xy(q) for q in p["polyline_lonlat"]] for p in json.loads(F1.read_text())}
print("[stills] screens in the scene:", sorted(o.name for o in bpy.data.objects if o.name.upper().startswith("1WALL_TILTUP_SCREEN")))
for tag, back in (("ne", 45.0), ("sw", 45.0)):
    line = pieces[tag]
    mx, my = line[len(line) // 2]
    i = nearest_i(mx, my)
    for name, d in ((f"lap_F1_{tag}_back", -back), (f"lap_F1_{tag}_ahead", back)):
        ex, ey = along(i, d)
        ez = z_at(road, ex, ey, 0.0) + EYE_M
        mz = z_at(ground, mx, my, ez - EYE_M) + 1.8
        shoot(name, (ex, ey, ez), (mx, my, mz), fov=70.0)
allp = [q for t in ("ne", "step", "sw") for q in pieces[t]]
cx = sum(p[0] for p in allp) / len(allp)
cy = sum(p[1] for p in allp) / len(allp)
gz = z_at(ground, cx, cy, 0.0)
shoot("above_nw_boundary_F1", (cx + 85.0, cy - 75.0, gz + 60.0), (cx, cy, gz), fov=60.0)
print("[stills] done")
