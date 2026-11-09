"""Ledger 0084 stills: the same cameras on two builds' SPLIT road scenes (0.1.5 before, 0.1.7 after), car height and from
above. Not a gate (L12). Sun, sky and render as source/edges/edge_stills_blend.py.

    blender --background --factory-startup --python-exit-code 1 --python road_wear_stills_blend.py -- \
        <loop_main.blend> <out-prefix> <spots.json>

spots.json: [{"tag", "eye": [x, y, z], "look": [x, y, z], "fov"}] in the scene's frame (Blender: x = E, y = N, z = up).

The 0.1.7 road material is AC's ksPerPixelMultiMap_NMDetail, which Blender does not have: where a material carries the
road-wear images (tools/road_wear_blend.py labels its nodes by slot) this script wires the stand-in AC computes —
base colour = txDiffuse(uv) x txDetail(uv x detailUVMultiplier), normal = txNormalDetail(uv x detailUVMultiplier).
0.1.5's materials render as built (the tiled asphalt and its normal at the prep's 4 m planar uv).
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
BLEND, OUT, SPOTS = Path(a[0]), a[1], json.loads(Path(a[2]).read_text(encoding="utf-8"))
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
rw = BLEND.parents[2] / "data" / "road_wear.json"
mult = json.loads(rw.read_text(encoding="utf-8"))["detail_uv_multiplier"] if rw.exists() else None
n_wired = 0
for mat in bpy.data.materials:
    if not mat.use_nodes:
        continue
    nt = mat.node_tree
    tex = {n.label: n for n in nt.nodes if n.type == "TEX_IMAGE" and n.label.startswith("tx")}
    if not ({"txDiffuse", "txDetail", "txNormalDetail"} <= set(tex)) or mult is None:
        continue
    bsdf = nt.nodes.get("Principled BSDF")
    # the macro's alpha is AC's detail mask (0 = full detail), not a transparency: Blender would premultiply it to black
    tex["txDiffuse"].image.alpha_mode = "NONE"
    uv = nt.nodes.new("ShaderNodeUVMap")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (mult, mult, 1.0)
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
    nt.links.new(uv.outputs["UV"], tex["txDiffuse"].inputs["Vector"])
    for k in ("txDetail", "txNormalDetail"):
        nt.links.new(mp.outputs["Vector"], tex[k].inputs["Vector"])
    mul = nt.nodes.new("ShaderNodeMixRGB"); mul.blend_type = "MULTIPLY"; mul.inputs["Fac"].default_value = 1.0
    nt.links.new(tex["txDiffuse"].outputs["Color"], mul.inputs["Color1"])
    nt.links.new(tex["txDetail"].outputs["Color"], mul.inputs["Color2"])
    nt.links.new(mul.outputs["Color"], bsdf.inputs["Base Color"])
    tex["txNormalDetail"].image.colorspace_settings.name = "Non-Color"
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex["txNormalDetail"].outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    n_wired += 1
print(f"[stills] {BLEND.parents[2].name}: {n_wired} road-wear materials wired as the NMDetail stand-in (mult {mult})")

sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.render.resolution_x, sc.render.resolution_y = 1400, 788
sc.render.image_settings.file_format = "JPEG"
sc.render.image_settings.quality = 88
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
for s in SPOTS:
    cam.angle = math.radians(s["fov"])
    cam_ob.location = Vector(s["eye"])
    cam_ob.rotation_mode = "QUATERNION"
    cam_ob.rotation_quaternion = (Vector(s["look"]) - Vector(s["eye"])).to_track_quat("-Z", "Y")
    sc.render.filepath = f"{OUT}_{s['tag']}.jpg"
    bpy.ops.render.render(write_still=True)
    print(f"[stills] {s['tag']}")
print("[stills] done")
