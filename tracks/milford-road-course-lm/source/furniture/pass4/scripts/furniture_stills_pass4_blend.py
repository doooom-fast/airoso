"""Milford furniture pass 4 stills (ledger 0082, 0.1.10): the far-west buildings NAIP 2022's west strip confirmed, from the driver's seat
(EYE_M over the built road) and from above, on a build's SPLIT road scene. Run it on 0.1.6's build and on 0.1.8's, the
same cameras, for the before / after. Not a gate (L12: show, don't assert). TreeFX is drawn by the game, not the kn5, so
the trees are STAND-INS (vegetation/scripts/veg_stills_blend.py's shape: a trunk and an ellipsoid crown at each planted
tree's measured height and crown), never the game's models. Sun: NAIP 2022's own (az 113, el 42).

    blender --background --factory-startup --python-exit-code 1 --python furniture_stills_pass3_blend.py -- \
        <project> <source/vegetation/trees.lm.json | none> <source/furniture/pass4> <out-prefix>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
PROJ, TREES, P3, OUT = Path(a[0]), a[1], Path(a[2]), a[3]
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


def nearest_i(x, y):
    return min(range(len(pts)), key=lambda i: (pts[i][0] - x) ** 2 + (pts[i][1] - y) ** 2)


def along(i, metres):
    s, j, step = 0.0, i, (1 if metres > 0 else -1)
    while s < abs(metres):
        k = (j + step) % len(pts)
        s += math.dist(pts[j], pts[k])
        j = k
    return pts[j]


def seat_at(x, y):
    return (x, y, z_at(road, x, y, 0.0) + EYE_M)



print("[stills] far blocks in the scene:", sorted(o.name for o in bpy.data.objects if o.name.upper().startswith(("FARBLOCK", "ROOFTOP"))))
blocks = json.loads((P3 / "blocks.json").read_text())
groups = {}
for b in blocks:
    ring = [to_xy(*q) for q in b["footprint_lonlat"]]
    groups.setdefault(b["key"].rsplit("_", 1)[0], []).extend(ring)
for g, ring in sorted(groups.items()):
    cx, cy = sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
    i = nearest_i(cx, cy)
    ex, ey, ez = seat_at(*pts[i])
    gz = z_at(ground, cx, cy, ez - EYE_M)
    shoot(f"seat_nearest_{g}", (ex, ey, ez), (cx, cy, gz + 8.0), fov=55.0)
    shoot(f"above_{g}", (ex + (cx - ex) * 0.45, ey + (cy - ey) * 0.45, ez + 60.0), (cx, cy, gz), fov=60.0)
print("[stills] done")
