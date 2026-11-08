"""AC menu preview for one layout, rendered in Blender from a build's SPLIT scenes (Kevin 2026-11-07: "Render them in
Blender"): loop_main + the layout's own scenes, a sun at a stated local time, a TV-style camera beside the road at N
stations along the layout's own line, looking the way the layout drives. Every shot writes <out>_<name>.png and a
sidecar <out>_<name>.json (camera, sun, scenes, line) that tools/menu_preview_cut.py turns into the ui/ files.

    blender --background --factory-startup --python-exit-code 1 --python tools/menu_preview_blend.py -- \
        <project> <layout_id> <out_prefix> [n_stations=6] [res_x=960] [stations=a,b,...] \
        [--scenes a.blend,b.blend] [--line data/<file>.json] [--reverse auto|yes|no] [--phase 0.0]

Defaults (the split's own names): scenes = loop_street.blend for "street", else loop_race.blend (or
loop_race_<lap>.blend when the layout id is <lap>_cw / <lap>_acw and that file exists) + loop_closure_<layout>.blend;
line = data/lap.<lap>.json when it exists, else data/centerline.local.json; the driving direction = the layout's grid
(data/dummies_<layout>.json, AC_START_0 ahead of AC_START_1) against the line's point order. --phase shifts the
stations along the lap (a fraction of one station step)."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ap = argparse.ArgumentParser(prog="menu_preview_blend.py")
ap.add_argument("project")
ap.add_argument("layout")
ap.add_argument("out")
ap.add_argument("n", nargs="?", type=int, default=6)
ap.add_argument("res_x", nargs="?", type=int, default=960)
ap.add_argument("stations", nargs="?", default="")
ap.add_argument("--scenes", default="")
ap.add_argument("--line", default="")
ap.add_argument("--reverse", default="auto", choices=("auto", "yes", "no"))
ap.add_argument("--phase", type=float, default=0.0)
A = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])
PROJ, LAYOUT, OUT, N, RES_X = Path(A.project), A.layout, A.out, A.n, A.res_x
ONLY = [int(s) for s in A.stations.split(",")] if A.stations else None
SPLIT, DATA = PROJ / "blender" / "split", PROJ / "data"
LAP = LAYOUT.rsplit("_", 1)[0] if LAYOUT.endswith(("_cw", "_acw")) else None

# San Diego (32.78 N), 7 Nov, 15:30 PST: sun elevation ~22 deg, azimuth ~228 deg (from north, clockwise)
SUN_AZ, SUN_EL = 228.0, 22.0

if A.scenes:
    SCENES = [s.strip() for s in A.scenes.split(",") if s.strip()]
elif LAYOUT == "street":
    SCENES = ["loop_street.blend"]
else:
    race = f"loop_race_{LAP}.blend" if LAP and (SPLIT / f"loop_race_{LAP}.blend").exists() else "loop_race.blend"
    SCENES = [race, f"loop_closure_{LAYOUT}.blend"]
if A.line:
    LINE = PROJ / A.line
else:
    LINE = DATA / f"lap.{LAP}.json" if LAP and (DATA / f"lap.{LAP}.json").exists() else DATA / "centerline.local.json"

bpy.ops.wm.open_mainfile(filepath=str(SPLIT / "loop_main.blend"))
appended = []
for extra in SCENES:
    p = SPLIT / extra
    if not p.exists():
        print(f"[preview] no {extra}, skipped")
        continue
    with bpy.data.libraries.load(str(p), link=False) as (src, dst):
        dst.objects = list(src.objects)
    for o in dst.objects:
        if o is not None and o.name not in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.link(o)
    appended.append(extra)
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
# the line files are engine frame (x = E, y = up, z = N); the split scene's plan is (x, y) = (E, N)
pts = [(p[0], p[2]) for p in json.loads(LINE.read_text(encoding="utf-8"))["points_xyz_m"]]
L = len(pts)


def grid_says_reverse():
    """the layout's grid: AC_START_0 is the front car, AC_START_1 the next; their difference is the driving direction.
    The dummies may be in either z sense (engine or kn5 frame): use the one that sits on the line."""
    f = DATA / f"dummies_{LAYOUT}.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    if "AC_START_0" not in d or "AC_START_1" not in d:
        return None
    best = None
    for zs in (1.0, -1.0):
        s0 = (d["AC_START_0"][0], zs * d["AC_START_0"][2])
        s1 = (d["AC_START_1"][0], zs * d["AC_START_1"][2])
        i, dist = min(((k, math.dist(s0, p)) for k, p in enumerate(pts)), key=lambda t: t[1])
        if best is None or dist < best[0]:
            best = (dist, i, s0, s1)
    dist, i, s0, s1 = best
    tx, ty = pts[(i + 3) % L][0] - pts[i - 3][0], pts[(i + 3) % L][1] - pts[i - 3][1]
    hx, hy = s0[0] - s1[0], s0[1] - s1[1]
    rev = tx * hx + ty * hy < 0
    print(f"[preview] grid: AC_START_0 {dist:.1f} m from line point {i}; drives {'against' if rev else 'with'} the line")
    return rev


REVERSE = {"yes": True, "no": False}.get(A.reverse)
if REVERSE is None:
    REVERSE = bool(grid_says_reverse())
if REVERSE:
    pts = pts[::-1]

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


def shoot(name, eye, look, fov, station):
    cam.angle = math.radians(fov)
    cob.rotation_mode = "QUATERNION"
    cob.rotation_quaternion = (Vector(look) - Vector(eye)).to_track_quat("-Z", "Y")
    cob.location = eye
    sc.render.filepath = f"{OUT}_{name}.png"
    bpy.ops.render.render(write_still=True)
    side = {"layout": LAYOUT, "project": str(PROJ).replace("\\", "/"), "scenes": ["loop_main.blend"] + appended,
            "line": str(LINE.relative_to(PROJ)).replace("\\", "/"), "reversed": REVERSE, "station": station,
            "camera": {"eye_m": [round(c, 2) for c in eye], "look_m": [round(c, 2) for c in look], "fov_deg": fov,
                       "frame": "blender scene (x, y = the split scene's plan, z up)"},
            "sun": {"azimuth_deg": SUN_AZ, "elevation_deg": SUN_EL, "as": "San Diego, 7 Nov, 15:30 PST"},
            "sky": "Nishita, strength 0.35, altitude 120 m, air 1.2, dust 1.5",
            "render": f"EEVEE Next, AgX, {sc.render.resolution_x}x{sc.render.resolution_y}"}
    Path(f"{OUT}_{name}.json").write_text(json.dumps(side, indent=2), encoding="utf-8")
    print(f"[preview] {name}: eye ({eye[0]:.1f}, {eye[1]:.1f}, {eye[2]:.1f}) look ({look[0]:.1f}, {look[1]:.1f}, "
          f"{look[2]:.1f}) fov {fov} sun az {SUN_AZ} el {SUN_EL} -> {sc.render.filepath}")


for k in range(N):
    if ONLY is not None and k not in ONLY:
        continue
    i = int((k + A.phase) * L / N) % L
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
    shoot(f"s{k}", tuple(eye), (lx, ly, lz + 1.0), 48.0,
          f"{LINE.name} point {i}{' (reversed order)' if REVERSE else ''} (s{k} of {N}, phase {A.phase})")
