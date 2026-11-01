"""A driver's-eye still every sixth of the lap on the SPLIT road scene, plus one from above: what a track's bespoke dressing looks like
from the car, at stations nobody chose (L12: show, don't assert; tools/bespoke_stills_blend.py is Nevada's station list). Not a gate.

    blender --background --factory-startup --python-exit-code 1 --python tools/bespoke_lap_stills_blend.py -- <project> <out-prefix> [n]
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
PROJ, OUT = Path(a[0]), a[1]
N = int(a[2]) if len(a) > 2 else 6
EYE_M = 1.2


def road_bvh():
    verts, polys = [], []
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.name.upper().startswith("1ROAD"):
            continue
        off = len(verts)
        verts += [o.matrix_world @ Vector(v.co) for v in o.data.vertices]
        polys += [[off + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


bpy.ops.wm.open_mainfile(filepath=str(PROJ / "blender" / "split" / "loop_main.blend"))
road = road_bvh()
pts = [(p[0], p[2]) for p in json.loads((PROJ / "data" / "centerline.local.json").read_text(encoding="utf-8"))["points_xyz_m"]]
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
az, el = math.radians(150.0), math.radians(45.0)
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
    cam.angle = math.radians(fov)
    cam_ob.rotation_mode = "QUATERNION"
    cam_ob.rotation_quaternion = (Vector(look) - Vector(eye)).to_track_quat("-Z", "Y")
    cam_ob.location = eye
    sc.render.filepath = f"{OUT}_{name}.jpg"
    bpy.ops.render.render(write_still=True)
    print(f"[stills] {name}: {sc.render.filepath}")


xs, ys = [p[0] for p in pts], [p[1] for p in pts]
cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
shoot("top", (cx, cy, 1500.0), (cx, cy, 0.0), ortho=max(max(xs) - min(xs), max(ys) - min(ys)) * 1.25)
for k in range(N):
    i = k * len(pts) // N
    x, y = pts[i]
    hit = road.ray_cast(Vector((x, y, 2000.0)), Vector((0, 0, -1)), 4000.0)
    if hit[0] is None:
        print(f"[stills] station {k}: no road under the line, skipped")
        continue
    z = float(hit[0].z) + EYE_M
    fx, fy = pts[(i + 12) % len(pts)]
    shoot(f"lap{k}", (x, y, z), (fx, fy, z - 0.3))
