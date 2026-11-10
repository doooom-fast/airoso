"""Milford furniture pass 1 stills (ledger 0082): a driver's-eye still at each inventory item that was built, plus two from
above, on the SPLIT road scene (the shape of tools/bespoke_lap_stills_blend.py). Not a gate (L12: show, don't assert).

    blender --background --factory-startup --python-exit-code 1 --python furniture_stills_blend.py -- <project> <inventory.json> <out-prefix>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
PROJ, INV, OUT = Path(a[0]), Path(a[1]), a[2]
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
m_lat = 111132.954 - 559.822 * math.cos(2 * math.radians(origin["lat"])) + 1.175 * math.cos(4 * math.radians(origin["lat"]))
m_lon = 111412.84 * math.cos(math.radians(origin["lat"])) - 93.5 * math.cos(3 * math.radians(origin["lat"])) + 0.118 * math.cos(5 * math.radians(origin["lat"]))
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
except Exception:
    pass
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


def shoot(name, eye, look, fov=62.0, ortho=None):
    cam.type = "ORTHO" if ortho else "PERSP"
    if ortho:
        cam.ortho_scale = ortho
    else:
        cam.angle = math.radians(fov)
    cam_ob.location = Vector(eye)
    cam_ob.rotation_mode = "QUATERNION"
    cam_ob.rotation_quaternion = (Vector(look) - Vector(eye)).to_track_quat("-Z", "Y")
    sc.render.filepath = f"{OUT}_{name}.jpg"
    bpy.ops.render.render(write_still=True)
    print(f"[stills] {name}: eye {tuple(round(v, 1) for v in eye)} -> {tuple(round(v, 1) for v in look)}")


def nearest_i(x, y):
    return min(range(len(pts)), key=lambda i: (pts[i][0] - x) ** 2 + (pts[i][1] - y) ** 2)


def back_along(i, metres):
    s = 0.0
    j = i
    while s < metres:
        k = (j - 1) % len(pts)
        s += math.dist(pts[j], pts[k])
        j = k
    return pts[j]


inv = {it["id"]: it for it in json.loads(INV.read_text())["items"]}
SHOTS = [("pitstraight_G2_G3", "G3", 60.0, 0.5), ("nw_corner_G1", "G1", 45.0, 0.5), ("hairpin_exit_T1_G4", "T1", 35.0, 0.5),
         ("esses_T2_G4", "T2", 35.0, 0.5), ("s1000_apron_T3", "T3", 40.0, 0.5)]
for name, iid, back, frac in SHOTS:
    line = [to_xy(p) for p in inv[iid]["polyline_lonlat"]]
    mx, my = line[int(len(line) * frac) if len(line) > 2 else 0]
    if len(line) == 2:
        mx, my = (line[0][0] + line[1][0]) / 2, (line[0][1] + line[1][1]) / 2
    i = nearest_i(mx, my)
    ex, ey = back_along(i, back)
    ez = z_at(road, ex, ey, 0.0) + EYE_M
    mz = z_at(ground, mx, my, ez - EYE_M) + 0.5
    shoot(name, (ex, ey, ez), (mx, my, mz), fov=70.0)
# from above: the NW infield (G1, G4, T1, T2) and the ride pad (the tent and the sheds)
for name, iid in (("above_nw_infield", "T1"), ("above_pad_sheds", "S1")):
    it = inv[iid]
    ring = [to_xy(p) for p in (it.get("polyline_lonlat") or it["footprint_lonlat"])]
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    gz = z_at(ground, cx, cy, 0.0)
    shoot(name, (cx - 70.0, cy - 90.0, gz + 55.0), (cx, cy, gz), fov=55.0)
print("[stills] done")
