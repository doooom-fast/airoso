"""Menu preview candidates for one layout, rendered from the built SPLIT scenes (Kevin 2026-11-07: "Render them in
Blender"): loop_main + the layout's race and closure scenes, a sun at a stated local time, a TV-style camera beside the
road at N stations. Prototype (scratchpad); prints each camera so a rebuild can re-shoot the same frame.

    blender --background --factory-startup --python-exit-code 1 --python menu_preview_blend.py -- \
        <project> <layout_id> <out_prefix> [n_stations=6] [res_x=960] [stations=a,b,...]
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
PROJ, LAYOUT, OUT = Path(a[0]), a[1], a[2]
N = int(a[3]) if len(a) > 3 else 6
RES_X = int(a[4]) if len(a) > 4 else 960
ONLY = [int(s) for s in a[5].split(",")] if len(a) > 5 and a[5] else None
SPLIT = PROJ / "blender" / "split"

# San Diego (32.78 N), 7 Nov, 15:30 PST: sun elevation ~22 deg, azimuth ~228 deg (from north, clockwise)
SUN_AZ, SUN_EL = 228.0, 22.0

bpy.ops.wm.open_mainfile(filepath=str(SPLIT / "loop_main.blend"))
for extra in ("loop_race.blend", f"loop_closure_{LAYOUT}.blend"):
    p = SPLIT / extra
    if not p.exists():
        print(f"[preview] no {extra}, skipped")
        continue
    with bpy.data.libraries.load(str(p), link=False) as (src, dst):
        dst.objects = list(src.objects)
    for o in dst.objects:
        if o is not None and o.name not in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.link(o)
    print(f"[preview] appended {extra}: {len(dst.objects)} objects")

# anything AC never draws: ghost / invisible colliders
hidden = 0
for o in bpy.data.objects:
    n = o.name.upper()
    if o.type == "MESH" and ("GHOST" in n or "INVISIBLE" in n or n.startswith(("AC_", "1WALL_COLLIDER"))):
        o.hide_render = True
        hidden += 1
print(f"[preview] hidden from render (ghost / collider / AC dummies): {hidden}")


def road_bvh():
    verts, polys = [], []
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.name.upper().startswith("1ROAD"):
            continue
        off = len(verts)
        verts += [o.matrix_world @ Vector(v.co) for v in o.data.vertices]
        polys += [[off + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


road = road_bvh()
pts = [(p[0], p[2]) for p in json.loads((PROJ / "data" / "centerline.local.json").read_text(encoding="utf-8"))["points_xyz_m"]]

sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.render.resolution_x, sc.render.resolution_y = RES_X, RES_X * 9 // 16
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "AgX"
try:
    sc.eevee.use_shadows = True
    sc.eevee.shadow_ray_count = 2
    sc.eevee.use_raytracing = True
except Exception:
    pass

w = bpy.data.worlds.new("preview")
w.use_nodes = True
nt = w.node_tree
sky = nt.nodes.new("ShaderNodeTexSky")
sky.sky_type = "NISHITA"
sky.sun_elevation = math.radians(SUN_EL)
sky.sun_rotation = math.radians(SUN_AZ)
sky.altitude = 120.0
sky.air_density = 1.2
sky.dust_density = 1.5
bg = nt.nodes["Background"]
bg.inputs[1].default_value = 0.35
nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
sc.world = w

sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 4.0
sun.angle = math.radians(0.6)
sun.color = (1.0, 0.93, 0.82)
sob = bpy.data.objects.new("sun", sun)
az, el = math.radians(SUN_AZ), math.radians(SUN_EL)
to_sun = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
sob.rotation_mode = "QUATERNION"
sob.rotation_quaternion = to_sun.to_track_quat("Z", "Y")
sc.collection.objects.link(sob)

cam = bpy.data.cameras.new("cam")
cam.clip_start, cam.clip_end = 0.5, 6000
cob = bpy.data.objects.new("cam", cam)
sc.collection.objects.link(cob)
sc.camera = cob


def road_z(x, y):
    hit = road.ray_cast(Vector((x, y, 2000.0)), Vector((0, 0, -1)), 4000.0)
    return None if hit[0] is None else float(hit[0].z)


def shoot(name, eye, look, fov):
    cam.angle = math.radians(fov)
    cob.rotation_mode = "QUATERNION"
    cob.rotation_quaternion = (Vector(look) - Vector(eye)).to_track_quat("-Z", "Y")
    cob.location = eye
    sc.render.filepath = f"{OUT}_{name}.png"
    bpy.ops.render.render(write_still=True)
    print(f"[preview] {name}: eye ({eye[0]:.1f}, {eye[1]:.1f}, {eye[2]:.1f}) look ({look[0]:.1f}, {look[1]:.1f}, "
          f"{look[2]:.1f}) fov {fov} sun az {SUN_AZ} el {SUN_EL} -> {sc.render.filepath}")


L = len(pts)
for k in range(N):
    if ONLY is not None and k not in ONLY:
        continue
    i = k * L // N
    x, y = pts[i]
    z = road_z(x, y)
    if z is None:
        print(f"[preview] station {k}: no road under the line, skipped")
        continue
    fx, fy = pts[(i + 10) % L]
    d = Vector((fx - x, fy - y, 0)).normalized()
    nrm = Vector((-d.y, d.x, 0))
    eye = Vector((x, y, z)) - d * 22.0 + nrm * 9.0 + Vector((0, 0, 5.5))
    lx, ly = pts[(i + 18) % L]
    lz = road_z(lx, ly) or z
    shoot(f"s{k}", tuple(eye), (lx, ly, lz + 1.0), 48.0)
