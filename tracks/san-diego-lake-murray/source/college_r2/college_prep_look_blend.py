"""Look at a PREPPED scene (blender/<slug>.blend, the prep's output) on College: an OBJ of its ground, road and kerb
objects for measuring, and stills from the split's cameras.

    blender --background <prepped.blend> --python college_prep_look_blend.py -- <out obj> <stills dir> <tag>
    (tag "raw": a scene before the prep; TERRAIN / ROAD / CURB are written as 1GRASS_raw / 1ROAD_raw / 1KERB_raw, no stills)

The OBJ is in the engine frame (x east, y up, z north), one `o` per object, only objects whose name starts with 1GRASS,
1ROAD or 1KERB and only their faces near College (within BOX_M of the split's frame), so the file stays small.
The stills show 1ROAD* / 1KERB* / 1GRASS* / 1WALL* / MARKINGS / YLINE from the cameras of college_split_stills_blend.py."""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
argv = sys.argv[sys.argv.index("--") + 1:]
OBJ, STILLS, TAG = Path(argv[0]), Path(argv[1]), argv[2]
STILLS.mkdir(parents=True, exist_ok=True)
S = json.loads((HERE / "college_split.data.json").read_text(encoding="utf-8"))
R, F = S["rows"], S["frame"]
K = {v: k for k, v in enumerate(R["v"])}
BOX_M = 80.0
x0, x1 = min(F["x"]) - BOX_M, max(F["x"]) + BOX_M
y0, y1 = min(F["z"]) - BOX_M, max(F["z"]) + BOX_M
KINDS = ("1GRASS", "1ROAD", "1KERB")
# a scene BEFORE the prep (tag "raw"): its TERRAIN / ROAD / CURB are written under the kind the prep gives them; no stills
RAW = {"TERRAIN": "1GRASS_raw", "ROAD": "1ROAD_raw", "CURB": "1KERB_raw"} if TAG == "raw" else {}

# --- the OBJ -----------------------------------------------------------------------------------------------------------------
n_out = 0
with open(OBJ, "w", encoding="utf-8") as fh:
    base = 1
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        if ob.type != "MESH" or not (ob.name.upper().startswith(KINDS) or ob.name in RAW):
            continue
        me = ob.data
        M = np.array(ob.matrix_world)
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        w = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
        near = (w[:, 0] > x0) & (w[:, 0] < x1) & (w[:, 1] > y0) & (w[:, 1] < y1)
        if not near.any():
            continue
        faces = [list(p.vertices) for p in me.polygons if all(near[i] for i in p.vertices)]
        if not faces:
            continue
        used = sorted({i for f in faces for i in f})
        remap = {i: k for k, i in enumerate(used)}
        fh.write(f"o {RAW.get(ob.name, ob.name)}\n")
        for i in used:
            fh.write(f"v {w[i, 0]:.4f} {w[i, 2]:.4f} {w[i, 1]:.4f}\n")
        for f in faces:
            fh.write("f " + " ".join(str(base + remap[i]) for i in f) + "\n")
        base += len(used)
        n_out += 1
        print(f"[look] {ob.name}: {len(used)} vertices, {len(faces)} faces near College")
print(f"[look] wrote {OBJ} ({n_out} objects)")
if RAW:
    sys.exit(0)

# --- the stills ----------------------------------------------------------------------------------------------------------------
COLOURS = (("1ROAD", (0.16, 0.16, 0.17, 1.0)), ("1GRASS", (0.36, 0.47, 0.27, 1.0)), ("1KERB", (0.62, 0.61, 0.58, 1.0)),
           ("1WALL", (0.80, 0.80, 0.84, 1.0)), ("MARKINGS", (0.92, 0.92, 0.90, 1.0)), ("YLINE", (0.86, 0.68, 0.10, 1.0)),
           ("GRASS_FAR", (0.33, 0.43, 0.26, 1.0)))
scene = bpy.context.scene
for ob in scene.objects:
    col = next((c for p, c in COLOURS if ob.name.upper().startswith(p)), None)
    ob.hide_render = col is None
    ob.hide_viewport = col is None
    if col is not None:
        ob.color = col
EYE_M = 1.15


def bl(p, up=0.0):
    return Vector((p[0], p[2], p[1] + up))


def mid(v):
    return 0.5 * (bl(R["sb_line"][K[v]]) + bl(R["nb_line"][K[v]]))


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
if scene.world is None:
    scene.world = bpy.data.worlds.new("w")
scene.world.color = (0.62, 0.72, 0.82)
cam_data = bpy.data.cameras.new("look_cam")
cam = bpy.data.objects.new("look_cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.clip_start, cam_data.clip_end = 0.3, 4000.0
f = mid(1330) - mid(1200)
f.z = 0.0
f.normalize()
west = Vector((-f.y, f.x, 0.0))
zl = S["lap_zone"]
SHOTS = {
    "air": (mid(1215) - f * 150.0 + west * 120.0 + Vector((0, 0, 105.0)), mid(1300) + Vector((0, 0, 2.0)), 32.0),
    "air_nose": (mid(1172) - f * 95.0 + west * 20.0 + Vector((0, 0, 60.0)), mid(1195) + Vector((0, 0, 1.0)), 35.0),
    "air_east": (mid(1300) - f * 60.0 - west * 70.0 + Vector((0, 0, 45.0)), mid(1310) + Vector((0, 0, 3.0)), 32.0),
    "fork_s": (bl(zl["points_xyz_m"][1150 - zl["from_v"]], EYE_M + 0.10), bl(R["nb_line"][K[1185]], 1.0), 24.0),
    "nb_1215": (bl(R["nb_line"][K[1215]], EYE_M), bl(R["nb_line"][K[1250]], 1.0), 24.0),
    "nb_1300": (bl(R["nb_line"][K[1300]], EYE_M), bl(R["nb_line"][K[1335]], 1.0), 24.0),
    "sb_1410": (bl(R["sb_line"][K[1410]], EYE_M), bl(R["sb_line"][K[1375]], 1.0), 24.0),
    "sb_1260": (bl(R["sb_line"][K[1260]], EYE_M), bl(R["sb_line"][K[1225]], 1.0), 24.0),
}
for name, (pos, look, lens) in SHOTS.items():
    cam.location = pos
    cam.rotation_euler = (look - pos).to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = lens
    scene.render.filepath = str(STILLS / f"{TAG}_{name}.jpg")
    bpy.ops.render.render(write_still=True)
    print(f"[look] {TAG}_{name}.jpg")
