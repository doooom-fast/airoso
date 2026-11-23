"""Stills of the College split's RIBBONS (step 2): ROAD and TERRAIN only, three cameras, Workbench.

    blender --background <a loop.blend> --python college_split_stills_blend.py -- <out dir> <tag> [object,object,...]

Run it on the scene before the step (tag "before") and after it (tag "after"): the cameras are the same in both,
placed from college_split.data.json. Everything but ROAD and TERRAIN is hidden: the walks, the old island, the paint,
the rail and the lamps still stand where the one-slab road had them (steps 3 and 4), and would only confuse the picture.
Frames: engine x east, y up, z north -> Blender (x, z, y)."""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
argv = sys.argv[sys.argv.index("--") + 1:]
OUT, TAG = Path(argv[0]), argv[1]
OUT.mkdir(parents=True, exist_ok=True)
S = json.loads((HERE / "college_split.data.json").read_text(encoding="utf-8"))
R = S["rows"]
K = {v: k for k, v in enumerate(R["v"])}
EYE_M = 1.15


def bl(p, up=0.0):
    return Vector((p[0], p[2], p[1] + up))


def mid(v):
    a, b = bl(R["sb_line"][K[v]]), bl(R["nb_line"][K[v]])
    return 0.5 * (a + b)


scene = bpy.context.scene
COLOURS = {"ROAD": (0.16, 0.16, 0.17, 1.0), "TERRAIN": (0.36, 0.47, 0.27, 1.0), "CURB": (0.62, 0.61, 0.58, 1.0),
           "GUARDRAIL": (0.80, 0.80, 0.84, 1.0), "MARKINGS": (0.92, 0.92, 0.90, 1.0), "YLINE": (0.86, 0.68, 0.10, 1.0),
           "1KERB_sidewalk_streetonly_median": (0.62, 0.61, 0.58, 1.0), "1WALL_guard_streetonly_median": (0.80, 0.80, 0.84, 1.0)}
SHOW = argv[2].split(",") if len(argv) > 2 else ["ROAD", "TERRAIN"]          # a third argument names the objects to show
for ob in scene.objects:
    keep = ob.name in SHOW
    ob.hide_render = not keep
    ob.hide_viewport = not keep
    if keep and ob.name in COLOURS:
        ob.color = COLOURS[ob.name]
scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light = "STUDIO"
sh.color_type = "OBJECT"
sh.show_cavity = True
sh.cavity_type = "BOTH"
sh.show_shadows = True
sh.shadow_intensity = 0.35
sh.show_backface_culling = False
scene.display.render_aa = "8"
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 90
scene.render.film_transparent = False
if scene.world is None:
    scene.world = bpy.data.worlds.new("w")
scene.world.color = (0.62, 0.72, 0.82)

cam_data = bpy.data.cameras.new("split_cam")
cam = bpy.data.objects.new("split_cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.clip_start, cam_data.clip_end = 0.3, 4000.0

f = (mid(1330) - mid(1200))
f.z = 0.0
f.normalize()
west = Vector((-f.y, f.x, 0.0))                      # left of northbound travel
SHOTS = {
    "air": (mid(1215) - f * 150.0 + west * 120.0 + Vector((0, 0, 105.0)), mid(1300) + Vector((0, 0, 2.0)), 32.0),
    "air_nose": (mid(1172) - f * 95.0 + west * 20.0 + Vector((0, 0, 60.0)), mid(1195) + Vector((0, 0, 1.0)), 35.0),
    "nb_1215": (bl(R["nb_line"][K[1215]], EYE_M), bl(R["nb_line"][K[1250]], 1.0), 24.0),
    "sb_1410": (bl(R["sb_line"][K[1410]], EYE_M), bl(R["sb_line"][K[1375]], 1.0), 24.0),
    "fork_s": (bl(S["lap_zone"]["points_xyz_m"][1150 - S["lap_zone"]["from_v"]], EYE_M + 0.10),
               bl(R["nb_line"][K[1185]], 1.0), 24.0),
}
for name, (pos, look, lens) in SHOTS.items():
    cam.location = pos
    cam.rotation_euler = (look - pos).to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = lens
    scene.render.filepath = str(OUT / f"{TAG}_{name}.jpg")
    bpy.ops.render.render(write_still=True)
    print(f"[stills] {TAG}_{name}.jpg")
