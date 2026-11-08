"""Ledger 0087 stills: the lane edge close and low, the way a driver sees it, at the stretches tools/edge_smoothness.py ranks
worst, on a build's SPLIT road scene; run on 0.1.2 (before) and 0.1.4 (after) with the same cameras. Not a gate (L12).
Same sun and render as source/furniture/furniture_stills_pass2_blend.py.

    blender --background --factory-startup --python-exit-code 1 --python edge_stills_blend.py -- \
        <project> <out-prefix> <s>:<left|right>[:<tag>] ...

Per spot: `low`  the eye 1.0 m over the lane, 1.5 m in from that edge, 22 m back, looking 18 m ahead at the edge;
          `top`  12 m straight over the edge, looking down along it (the outline as a plan).
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
PROJ, OUT, SPOTS = Path(a[0]), a[1], a[2:]


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
road = bvh(("1ROAD", "1KERB"))
g = json.loads((PROJ / "data" / "gate_centerline.json").read_text(encoding="utf-8"))
P = [(p[0], p[2]) for p in g["points_xyz_m"]]
W = g["widths_m"]
st = [0.0]
for p, q in zip(P, P[1:]):
    st.append(st[-1] + math.dist(p, q))


def at(s):
    s %= st[-1]
    j = max(0, min(len(st) - 2, next(k for k in range(len(st) - 1) if st[k + 1] >= s)))
    f = (s - st[j]) / ((st[j + 1] - st[j]) or 1e-9)
    x = P[j][0] + (P[j + 1][0] - P[j][0]) * f
    y = P[j][1] + (P[j + 1][1] - P[j][1]) * f
    tx, ty = P[j + 1][0] - P[j][0], P[j + 1][1] - P[j][1]
    L = math.hypot(tx, ty) or 1.0
    return x, y, tx / L, ty / L, (W[j] + (W[j + 1] - W[j]) * f) / 2


sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.render.resolution_x, sc.render.resolution_y = 1400, 788
sc.render.image_settings.file_format = "JPEG"
sc.render.image_settings.quality = 85
w = bpy.data.worlds.new("still")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.74, 0.92, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
sc.world = w
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 3.5
ob = bpy.data.objects.new("sun", sun)
az, el = math.radians(113.0), math.radians(42.0)
ob.rotation_mode = "QUATERNION"
ob.rotation_quaternion = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))).to_track_quat("Z", "Y")
sc.collection.objects.link(ob)
cam = bpy.data.cameras.new("cam")
cam.clip_end = 4000
cam_ob = bpy.data.objects.new("cam", cam)
sc.collection.objects.link(cam_ob)
sc.camera = cam_ob


def shoot(name, eye, look, fov, up="Y"):
    cam.angle = math.radians(fov)
    cam_ob.location = Vector(eye)
    cam_ob.rotation_mode = "QUATERNION"
    cam_ob.rotation_quaternion = (Vector(look) - Vector(eye)).to_track_quat("-Z", up)
    sc.render.filepath = f"{OUT}_{name}.jpg"
    bpy.ops.render.render(write_still=True)
    print(f"[stills] {name}: eye {tuple(round(v, 1) for v in eye)} -> {tuple(round(v, 1) for v in look)}")


for spot in SPOTS:
    parts = spot.split(":")
    s0, side = float(parts[0]), parts[1]
    tag = parts[2] if len(parts) > 2 else f"s{int(s0)}_{side}"
    sg = 1.0 if side == "left" else -1.0
    x, y, tx, ty, hw = at(s0 - 22.0)
    nx, ny = -ty * sg, tx * sg
    ex, ey = x + nx * (hw - 1.5), y + ny * (hw - 1.5)
    ez = z_at(road, ex, ey, 0.0) + 1.0
    x2, y2, tx2, ty2, hw2 = at(s0 + 18.0)
    nx2, ny2 = -ty2 * sg, tx2 * sg
    lx, ly = x2 + nx2 * hw2, y2 + ny2 * hw2
    lz = z_at(road, lx, ly, ez - 1.0)
    shoot(f"{tag}_low", (ex, ey, ez), (lx, ly, lz), 55.0)
    x0, y0, tx0, ty0, hw0 = at(s0)
    cx, cy = x0 + (-ty0 * sg) * hw0, y0 + (tx0 * sg) * hw0
    cz = z_at(road, cx, cy, 0.0)
    shoot(f"{tag}_top", (cx - tx0 * 0.01, cy - ty0 * 0.01, cz + 12.0), (cx, cy, cz), 70.0)
print("[stills] done")
