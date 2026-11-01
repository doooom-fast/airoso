"""Fixed-station stills of the bespoke dressing on the SPLIT road scene, the scene the kn5 exports (L12: show, don't assert).

    blender --background --factory-startup --python-exit-code 1 --python tools/bespoke_stills_blend.py -- <project> <out-prefix>

Every station is read off data/bespoke.report.json and the lap, never typed: <prefix>_buildings_top.png (straight down at the
footprints, to lay beside source/trace/buildings_2013_measured.png), _buildings_road.png (a driver's eye on the nearest
road, looking at them), _cones.png (a driver's eye on the tightest corner's approach, looking at its apex cone), _scrub.png
(the eye on the road nearest the scrub, looking at it). EEVEE with the scene's own textures, one sun at the shadow-measured
elevation (33 deg, the NAIP morning), so the look is the materials' and not a flat lens. Not a gate.
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
EYE_M = 1.2


def road_bvh():
    verts, polys = [], []
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.name.upper().startswith("1ROAD"):
            continue
        mw = o.matrix_world
        off = len(verts)
        verts += [mw @ Vector(v.co) for v in o.data.vertices]
        polys += [[off + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def setup():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.render.image_settings.file_format = "PNG"
    w = bpy.data.worlds.new("still")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.74, 0.92, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    sc.world = w
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.5
    ob = bpy.data.objects.new("sun", sun)
    az, el = math.radians(122.0), math.radians(33.0)
    d = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))     # toward the sun
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = d.to_track_quat("Z", "Y")
    sc.collection.objects.link(ob)
    cam = bpy.data.cameras.new("cam")
    cam.clip_end = 5000
    cam_ob = bpy.data.objects.new("cam", cam)
    sc.collection.objects.link(cam_ob)
    sc.camera = cam_ob
    return cam, cam_ob


def shoot(cam, cam_ob, name, eye, look, fov=60.0, ortho=None):
    cam.type = "ORTHO" if ortho else "PERSP"
    if ortho:
        cam.ortho_scale = ortho
    cam.angle = math.radians(fov)
    d = Vector(look) - Vector(eye)
    cam_ob.rotation_mode = "QUATERNION"
    cam_ob.rotation_quaternion = d.to_track_quat("-Z", "Y")
    cam_ob.location = eye
    bpy.context.scene.render.filepath = f"{OUT}_{name}.png"
    bpy.ops.render.render(write_still=True)
    print(f"[stills] {name}: eye {[round(v, 1) for v in eye]} look {[round(v, 1) for v in look]} -> {OUT}_{name}.png")


def main():
    rep = json.loads((PROJ / "data" / "bespoke.report.json").read_text(encoding="utf-8"))
    cl = json.loads((PROJ / "data" / "centerline.local.json").read_text(encoding="utf-8"))["points_xyz_m"]
    pts = [(p[0], p[2]) for p in cl]
    bpy.ops.wm.open_mainfile(filepath=str(PROJ / "blender" / "split" / "loop_main.blend"))
    road = road_bvh()
    cam, cam_ob = setup()

    def eye_on_road(x, y):
        hit = road.ray_cast(Vector((x, y, 2000.0)), Vector((0, 0, -1)), 4000.0)
        return (x, y, float(hit[0].z) + EYE_M)

    def nearest(x, y):
        return min(range(len(pts)), key=lambda i: (pts[i][0] - x) ** 2 + (pts[i][1] - y) ** 2)
    shells = [o for o in bpy.data.objects if o.name.upper().startswith("BUILDING_FABRIC")]
    vs = [o.matrix_world @ Vector(v.co) for o in shells for v in o.data.vertices]
    cx, cy = sum(v.x for v in vs) / len(vs), sum(v.y for v in vs) / len(vs)
    cz = max(v.z for v in vs)
    shoot(cam, cam_ob, "buildings_top", (cx, cy, cz + 300.0), (cx, cy, cz), ortho=140.0)
    i = nearest(cx, cy)
    shoot(cam, cam_ob, "buildings_road", eye_on_road(*pts[i]), (cx, cy, cz - 2.0), fov=50.0)
    apexes = [c for c in rep["cones"] if c["role"] == "apex"]
    apex = apexes[3] if len(apexes) > 3 else apexes[0]         # the fourth corner is the lap's tightest, 20 m radius
    j = nearest(*apex["xy"])
    back = pts[(j - 14) % len(pts)]
    shoot(cam, cam_ob, "cones", eye_on_road(*back), (apex["xy"][0], apex["xy"][1], apex["ground"] + 0.4), fov=50.0)
    sx = sum(s["xy"][0] for s in rep["scrub"]) / len(rep["scrub"])
    sy = sum(s["xy"][1] for s in rep["scrub"]) / len(rep["scrub"])
    k = nearest(sx, sy)
    gy = sum(s["ground"] for s in rep["scrub"]) / len(rep["scrub"])
    shoot(cam, cam_ob, "scrub", eye_on_road(*pts[k]), (sx, sy, gy + 1.0), fov=35.0)


main()
