"""Stills of Lake Murray's race kerbs as built (0.20.2's loop.blend), from the driver's eye, for Kevin's look at how dirty
they are (ledger 0053 Q2 / 0099; Kevin 2026-11-22: "Show me stills first"). BLENDER STAND-INS, not Assetto Corsa: CSP's
shading, the kn5's ksPerPixelMultiMap and the game's tone map differ.

    blender --background --factory-startup tracks/san-diego-lake-murray/loop.blend --python-exit-code 1 \\
        --python tracks/san-diego-lake-murray/source/stills/kerb_dirt_stills_blend.py -- <out-dir> [--samples 96]

The blend is the committed one (sha256 3f13b887..., the workshop's loop.blend as 0.20.2's chain saved it, race furniture
authored); nothing is saved. Each mesh is bound as the kn5 prep binds it: the prep's AC names (ROAD -> 1ROAD_road, CURB ->
1KERB_sidewalk, TERRAIN -> 1GRASS), the prep's 4 m planar UVs on every mesh the prep projects (engine-july's
build_kn5_loop.planar_uv; the race kerbs and walls keep their own UVs), and airoso's scripts/ac/pbr.setup_material with
track.config.json's texture_overrides AS 0.20.2 BUILT THEM (the 0099 owned asphalt / concrete rows left out, so the road is
the installed borrowed asphalt). The race kerbs wrap kerb_race_worn_{diffuse,normal}.jpg, the four rubber columns
race_authored.json records per kerb (ledger 0053).

Camera: a driver on the line that uses the kerb: 3.0 m (the close look: 1.5 m) [invented] in from the kerb's lane-side edge where it is nearest
the camera vertex (toward the lap's centreline), 1.10 m over the road surface there [the eye height is invented: a seated
driver; AC cockpit cameras run about 1.0-1.2 m], looking at the kerb where it is nearest the look vertex, race_cw's way
(increasing vertex); field of view 60 deg [invented]. Sun: the menu pictures' (San Diego, 7 Nov,
15:30 PST: azimuth 228, elevation 22 deg; tools/menu_preview_blend.py), a Nishita sky. Each still is labelled in the
picture itself.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
TRACK = HERE.parents[1]
ROOT = TRACK.parents[1]
sys.path.insert(0, str(ROOT))
from scripts.ac import pbr  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(argv[0]) if argv else HERE
SAMPLES = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 96
RES = (1600, 900)
EYE_M = 1.10
FOV = 60.0
LATERAL_M = 3.0
SUN_AZ, SUN_EL = 228.0, 22.0
AC_NAME = {"ROAD": "1ROAD_road", "KERB": "1KERB_kerb", "CURB": "1KERB_sidewalk", "TERRAIN": "1GRASS",
           "GUARDRAIL": "1WALL_guard"}
NO_PLANAR = ("PALM", "TREE", "SCRUB", "BUSHES", "CHAINLINK", "ROADTEXT", "1WALL_RACE", "1KERB_RACE", "BRIDGESTRUCT",
             "1WALL_STUB", "BUILDING_FABRIC", "1WALL_FABRIC", "PROPCONE", "BUILDING_TILTUP", "BUILDING_METAL",
             "BUILDING_STUCCO", "BUILDING_SIDING", "ROOFTOP", "1WALL_TILTUP", "1WALL_TECPRO", "1WALL_KRAILBW", "GUARDRAIL",
             "PADAPRON", "BUILDING_DRYSTONE", "FARBLOCK")
UV_TILE = 4.0
OWNED_0099 = ("1ROAD", "1KERB_SIDEWALK")       # ledger 0099's rows: not in the build these stills show
BUILD = "0.20.2"                               # the build the committed loop.blend made (the config now says 0.20.3)

# (still, kerb, camera at centreline vertex, look at the kerb where it is nearest this vertex, what the picture shows)
SHOTS = [
    ("kerb_dirt_770_out_entry", "1KERB_race_770_out", 746, 753, LATERAL_M,
     "College hairpin (770) outside kerb, race_cw entry; heaviest rubber -59.1 to -49.8 m from the apex"),
    ("kerb_dirt_770_out_close", "1KERB_race_770_out", 749, 751, 1.5,
     "College hairpin (770) outside kerb, close on the heaviest rubber (-59.1 to -49.8 m from the apex)"),
    ("kerb_dirt_3296_out", "1KERB_race_3296_out", 3288, 3293, LATERAL_M,
     "Jackson / Lake Murray Blvd (3296) outside kerb, race_cw entry; heaviest rubber -16.1 to -11.3 m from the apex"),
]


def bind_materials():
    ov = {k: v for k, v in pbr.load_overrides(TRACK).items() if k not in OWNED_0099}
    n = 0
    for ob in list(bpy.data.objects):
        if ob.type != "MESH":
            continue
        name = AC_NAME.get(ob.name, ob.name)
        me = ob.data
        if not name.upper().startswith(NO_PLANAR):
            uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
            for loop in me.loops:
                co = me.vertices[loop.vertex_index].co
                uv.data[loop.index].uv = (co.x / UV_TILE, co.y / UV_TILE)
        if me.uv_layers:
            me.uv_layers.active = me.uv_layers[0]
        old = ob.name
        ob.name = name
        pbr.setup_material(bpy, ob, overrides=ov)
        ob.name = old
        n += 1
    return n, BUILD


def scene_setup():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception as e:  # CPU is fine, slower
        print("[kerb-stills] GPU not used:", e)
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "AgX"
    w = bpy.data.worlds.new("stills")
    w.use_nodes = True
    nt = w.node_tree
    sky = nt.nodes.new("ShaderNodeTexSky")
    for attr, val in (("sky_type", "NISHITA"), ("sun_elevation", math.radians(SUN_EL)),
                      ("sun_rotation", math.radians(SUN_AZ)), ("altitude", 120.0), ("air_density", 1.2),
                      ("dust_density", 1.5)):
        try:
            setattr(sky, attr, val)
        except Exception:
            pass
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
    cam.clip_start, cam.clip_end = 0.1, 4000.0
    cam.angle = math.radians(FOV)
    cob = bpy.data.objects.new("cam", cam)
    sc.collection.objects.link(cob)
    sc.camera = cob
    return sc, cob


def surface_z(x, y):
    """the highest road / kerb surface under (x, y) in the Blender frame"""
    from mathutils.bvhtree import BVHTree
    best = None
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.name.upper().startswith(("ROAD", "1ROAD")):
            continue
        dg = bpy.context.evaluated_depsgraph_get()
        bvh = BVHTree.FromObject(ob, dg)
        hit = bvh.ray_cast(ob.matrix_world.inverted() @ Vector((x, y, 2000.0)), Vector((0, 0, -1)), 4000.0)
        if hit[0] is not None:
            z = (ob.matrix_world @ hit[0]).z
            best = z if best is None else max(best, z)
    return best


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pts = json.loads((TRACK / "data" / "centerline.local.json").read_text(encoding="utf-8"))["points_xyz_m"]
    authored = {o["name"]: o for o in json.loads((TRACK / "data" / "race_authored.json").read_text(encoding="utf-8"))["objects"]}
    n, version = bind_materials()
    sc, cob = scene_setup()
    side = {"_doc": __doc__.split("\n\n")[0], "blend_version": version, "meshes_bound": n, "eye_m": EYE_M, "fov_deg": FOV,
            "sun": {"azimuth_deg": SUN_AZ, "elevation_deg": SUN_EL, "as": "San Diego, 7 Nov, 15:30 PST"},
            "samples": SAMPLES, "blender": bpy.app.version_string, "stills": []}
    for still, kerb, cam_v, look_v, lateral, what in SHOTS:
        ob = bpy.data.objects[kerb]
        p = pts[cam_v]                                   # local (x east, y up, z north) -> Blender (x, z, y)
        kv = [ob.matrix_world @ v.co for v in ob.data.vertices]
        edge = min(kv, key=lambda v: (v.x - p[0]) ** 2 + (v.y - p[2]) ** 2)    # the kerb's lane-side edge by the camera
        to_road = Vector((p[0] - edge.x, p[2] - edge.y, 0.0)).normalized()
        ex, ey = edge.x + to_road.x * lateral, edge.y + to_road.y * lateral
        z = surface_z(ex, ey)
        if z is None:
            raise SystemExit(f"[kerb-stills] no road under the eye by centreline vertex {cam_v}")
        eye = Vector((ex, ey, z + EYE_M))
        q = pts[look_v]
        near = sorted(kv, key=lambda v: (v.x - q[0]) ** 2 + (v.y - q[2]) ** 2)[:40]
        look = sum(near, Vector((0, 0, 0))) / len(near)
        cob.location = eye
        cob.rotation_mode = "QUATERNION"
        cob.rotation_quaternion = (look - eye).to_track_quat("-Z", "Y")
        png = OUT / f"{still}.png"
        sc.render.filepath = str(png)
        bpy.ops.render.render(write_still=True)
        wear = authored[kerb]["wear"]
        side["stills"].append({"still": still, "kerb": kerb, "what": what, "camera_vertex": cam_v, "look_vertex": look_v,
                               "lateral_from_kerb_m": lateral,
                               "eye_m": [round(c, 2) for c in eye], "look_m": [round(c, 2) for c in look],
                               "kerb_length_m": authored[kerb]["length_m"], "m_by_level": wear["m_by_level"],
                               "heavy_spans_m_from_apex": wear["heavy_spans_m_from_apex"], "png": png.name})
        print(f"[kerb-stills] {still}: eye {tuple(round(c, 1) for c in eye)} -> {png}")
    (OUT / "kerb_dirt_stills.json").write_text(json.dumps(side, indent=1), encoding="utf-8")


main()
