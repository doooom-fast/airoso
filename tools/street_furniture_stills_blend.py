"""Preview stills of the street furniture (ledger 0096) — L12: show, don't assert. Run in Blender 4.2:

    "$(./scripts/bootstrap_blender.sh)" --background --python tools/street_furniture_stills_blend.py -- [OUT_DIR]

Builds each still from the committed OBJs, the JSON specs' own recipes and the proposed bindings, so a still also
proves the spec assembles (heads on the arm at head_origins_m, the pedestal recipe, the plate UVs). Renders with
Cycles on the CPU (headless-safe). The grey box in a still is 1.8 m tall, for scale. Default OUT_DIR:
tracks/denver-grand-prix/source/furniture/stills/. Nothing is exported, placed on a track or installed.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from street_furniture_mesh import read_obj_objects          # noqa: E402

MODELS, TEX = ROOT / "assets" / "models", ROOT / "assets" / "textures"
BLADES = ROOT / "tracks" / "denver-grand-prix" / "textures" / "blades"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(argv[0]) if argv else ROOT / "tracks" / "denver-grand-prix" / "source" / "furniture" / "stills"
SIG = json.loads((MODELS / "signals.json").read_text())
LAMPS = json.loads((MODELS / "streetlight_posts.json").read_text())
SIGNS = json.loads((MODELS / "sign_faces.json").read_text())

BIND = {"SIGNALPOST": "solid_metal_grey.png", "SIGNALHEAD": "solid_sign_black.png", "SIGNALBACKPLATE": "solid_sign_black.png",
        "SIGNALBUTTON": "solid_metal_grey.png", "SIGNBACK": "solid_metal_grey.png", "SIGNPOST": "solid_metal_grey.png",
        "LIGHTPOST": "solid_metal_dark.png", "LIGHTS": "solid_lens_warm.png", "SIGNFACE_R10-3": "mutcd_r10-3.png",
        "SIGNFACE_R15-1_RAILROAD": "mutcd_r15-1_railroad.png", "SIGNFACE_R15-1_CROSSING": "mutcd_r15-1_crossing.png",
        "PEDLENS": "ped_signal_hand.png"}
LIT = {"R", "RA_L", "BAR_H"}                                  # steady red (and the rail stop bar) lit, the rest unlit
for a, t in SIG["bindings_proposed"].items():
    if a.startswith("SIGNALLENS_"):
        BIND[a] = t["lit" if a[11:] in LIT else "unlit"]
_mats = {}


def mat(tex: Path, glow=0.0):
    key = (str(tex), glow)
    if key not in _mats:
        m = bpy.data.materials.new(tex.stem)
        m.use_nodes = True
        nt = m.node_tree
        b = nt.nodes["Principled BSDF"]
        im = nt.nodes.new("ShaderNodeTexImage")
        im.image = bpy.data.images.load(str(tex))
        nt.links.new(im.outputs["Color"], b.inputs["Base Color"])
        if im.image.channels == 4 and im.image.depth == 32:
            nt.links.new(im.outputs["Alpha"], b.inputs["Alpha"])
        b.inputs["Roughness"].default_value = 0.6
        if glow:
            nt.links.new(im.outputs["Color"], b.inputs["Emission Color"])
            b.inputs["Emission Strength"].default_value = glow
        _mats[key] = m
    return _mats[key]


def place(file, at=(0, 0, 0), yaw=0.0, bind=None, drop=(), root=MODELS):
    """engine frame (x, y up, z) -> Blender (x, -z, y): a rotation, so nothing is mirrored and winding is kept"""
    bind = {**BIND, **(bind or {})}
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    for name, o in read_obj_objects((root / file).read_text()).items():
        if name in drop:
            continue
        vs = []
        for x, y, z in o["verts"]:
            x, z = x * c + z * s, -x * s + z * c
            vs.append((x + at[0], -(z + at[2]), y + at[1]))
        me = bpy.data.meshes.new(name)
        me.from_pydata(vs, [], [f[0] for f in o["faces"]])
        uvl = me.uv_layers.new(name="UVMap")
        k = 0
        for poly, f in zip(me.polygons, o["faces"]):
            poly.use_smooth = f[2] != 0
            for uv in f[1]:
                uvl.data[k].uv = uv
                k += 1
        tex = bind[o["material"]]
        tex = tex if isinstance(tex, Path) else TEX / tex
        lit = name.startswith("LENS") and not tex.stem.endswith("_off")
        me.materials.append(mat(tex, 3.0 if lit else 0.0))
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)


def box(lo, hi, rgb):
    bpy.ops.mesh.primitive_cube_add(location=((lo[0] + hi[0]) / 2, -(lo[2] + hi[2]) / 2, (lo[1] + hi[1]) / 2))
    ob = bpy.context.object
    ob.scale = ((hi[0] - lo[0]) / 2, (hi[2] - lo[2]) / 2, (hi[1] - lo[1]) / 2)
    m = bpy.data.materials.new("flat")
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1)
    ob.data.materials.append(m)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 40
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 88
    sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.68, 0.85, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    sc.world = w
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    sc.collection.objects.link(sun)
    box((-80, -0.2, -80), (80, 0.0, 80), (0.30, 0.30, 0.31))


def shoot(name, eye, target, lens=50):
    """eye / target in the engine frame"""
    sc = bpy.context.scene
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.lens = lens
    e, t = Vector((eye[0], -eye[2], eye[1])), Vector((target[0], -target[2], target[1]))
    cam.location = e
    cam.rotation_euler = (t - e).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(cam)
    sc.camera = cam
    OUT.mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(OUT / name)
    bpy.ops.render.render(write_still=True)
    print("[stills] wrote", OUT / name)


def person(x, z):
    box((x - 0.22, 0.0, z - 0.12), (x + 0.22, 1.8, z + 0.12), (0.45, 0.45, 0.47))


# 1. the three mast arms, heads at the spec's default stations (the innermost a left-turn head)
reset()
z0 = 0.0
for i, (key, arm) in enumerate(SIG["mast_arms"].items()):
    z = -i * 9.0
    place(arm["file"], (0, 0, z))
    for j, o in enumerate(arm["head_origins_m"]):
        last = j == len(arm["head_origins_m"]) - 1 and len(arm["head_origins_m"]) > 1
        place("signal_head_4_fya_l.obj" if last else "signal_head_3.obj", (o[0], o[1], z + o[2]))
    r = SIG["recipes"]["ped_head_on_pole"]["at"]
    place("signal_ped_head.obj", (r[0], r[1], z + r[2]))
    person(-1.2, z + 1.0)
shoot("signal_mast_arms_25_35_45.jpg", (9.0, 4.2, 26.0), (6.0, 4.6, -7.0), lens=38)

# 2. the heads, the pedestal assembly, the pedestrian head and the pushbutton post
reset()
for i, key in enumerate(SIG["heads"]):
    place(key + ".obj", (i * 1.25, 1.6, 0.0))
x = len(SIG["heads"]) * 1.25 + 0.2
place("signal_ped_head.obj", (x, 1.6, 0.0))
place("signal_ped_head.obj", (x + 0.75, 1.6, 0.0), bind={"PEDLENS": "ped_signal_walk.png"})
shoot("signal_heads.jpg", (4.6, 1.75, 12.0), (4.6, 1.6, 0.0), lens=42)

reset()
place("signal_pedestal.obj", (0, 0, 0))
r = SIG["recipes"]["pedestal_head"]
place(r["part"] + ".obj", tuple(r["at"]), drop=r["drop"])
p = SIG["recipes"]["ped_head_on_pole"]["at"]
place("signal_ped_head.obj", (SIG["pedestal"]["pipe_radius_m"] + 0.12, p[1], 0.0), yaw=90)
place("signal_pushbutton_post.obj", (1.6, 0, 0.3))
person(-1.3, 0.3)
shoot("signal_pedestal_and_pushbutton.jpg", (2.8, 2.4, 11.0), (0.3, 2.1, 0.0), lens=45)

# 3. the lamp classes
reset()
xs = {"ped_acorn": 0.0, "ped_globe": 3.0, "arterial_single": 8.0, "arterial_twin": 15.0}
for key, c in LAMPS["classes"].items():
    place(c["file"], (xs[key], 0, 0))
person(-1.5, 0.5)
shoot("streetlight_classes.jpg", (7.5, 4.5, 30.0), (7.5, 5.2, 0.0), lens=40)
reset()
place("streetlight_ped_acorn.obj", (0, 0, 0))
place("streetlight_ped_globe.obj", (2.2, 0, 0))
person(-1.2, 0.3)
shoot("streetlight_pedestrian_posts.jpg", (1.0, 2.4, 11.0), (1.0, 2.3, 0.0), lens=45)

# 4. every sign face on its plate, and eight of the blades
reset()
faces = list(SIGNS["faces"].items())
cols = 7
for i, (code, f) in enumerate(faces):
    place(f["plate"], ((i % cols) * 1.25, 4.9 - (i // cols) * 1.2, 0.0), bind={"SIGNFACE": f["file"]})
for i, (street, f) in enumerate(list(SIGNS["blades"]["streets"].items())[10:18]):
    place(f["plate"], (0.3 + (i % 4) * 2.0, 0.55 - (i // 4) * 0.35, 0.0), bind={"SIGNFACE": BLADES / f["file"]})
shoot("sign_faces.jpg", (3.75, 2.6, 13.5), (3.75, 2.6, 0.0), lens=50)

# 5. the rail-crossing set
reset()
place("rail_crossbuck.obj", (0, 0, 0))
place("signal_pedestal.obj", (2.4, 0, 0))
place("signal_head_lrt_2.obj", (2.4, SIG["pedestal"]["top_m"] + SIG["heads"]["signal_head_lrt_2"]["half_height_m"] - 0.127, -0.1016), drop=("BRACKET",))
place("sign_plate_circle_36.obj", (-2.2, 2.6, 0.0), bind={"SIGNFACE": "mutcd_w10-1.png"})
box((-2.225, -0.2, -0.06), (-2.175, 2.6, -0.01), (0.45, 0.46, 0.48))
person(1.2, 0.4)
shoot("rail_crossing_set.jpg", (0.4, 2.4, 9.5), (0.2, 2.1, 0.0), lens=50)
