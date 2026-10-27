"""Night stills of the streetlights on a BUILT gate OBJ (ledger 0054 P4 step 2) — the lamps lit, their pools on the road.

    blender --background --factory-startup --python-exit-code 1 --python tools/lamp_stills_blend.py -- \\
        --proj <project> --obj <project>/data/track.obj --out <png> \\
        ( --piece <connector name> --u <m> [--lane R|L] [--back] | --lamp <index> [--dist 7] )  [--day]

Local frame x = E, y = up, z = N -> Blender (x, z, y), as tools/stub_stills_blend.py. The scene is the gate OBJ within
KEEP_M of the eye, each mesh class a flat material. NIGHT (default, EEVEE): a near-black sky, the LIGHTS lenses
emissive in the sodium colour, and one spot light at every lens within LIGHT_REACH_M of the eye, pointing down, in
track.config.json lighting.streetlight's colour (CSP's own pool is not reproduced; this shows WHERE the lamps stand and
that each one lights the road under it). --day: Workbench daylight (for a close-up of a pole's foot).
  --piece/--u  the eye on the road, a driver's EYE_M up, at arc length u along that connector (data/connectors.local.json),
               in the right-hand lane of travel (--lane L for the other), looking along the piece (--back: the other way)
  --lamp       a close-up: the eye DIST m from lamp <index>'s base (data/lights.local.json lamp_bases_xz), 1.5 m up,
               looking at the base
"""
import json
import math
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]


def arg(k, d=None):
    return a[a.index(k) + 1] if k in a else d


PROJ, OBJ, OUT = arg("--proj"), arg("--obj"), arg("--out")
PIECE, U, LANE, BACK = arg("--piece"), arg("--u"), arg("--lane", "R"), "--back" in a
LAMP, DIST, DAY = arg("--lamp"), float(arg("--dist", "7")), "--day" in a
KEEP_M = 420.0
LIGHT_REACH_M = 320.0
EYE_M = 1.2
LANE_OFF_M = 4.5
COL = [("GRASS_FAR", (0.30, 0.30, 0.22)), ("1GRASS", (0.22, 0.30, 0.13)), ("1ROAD", (0.30, 0.30, 0.31)),
       ("1KERB_RACE", (0.62, 0.10, 0.08)), ("1KERB", (0.58, 0.58, 0.56)), ("MARKINGS", (0.92, 0.92, 0.90)),
       ("YLINE", (0.85, 0.68, 0.1)), ("HOUSE", (0.70, 0.62, 0.52)), ("BUILDING", (0.62, 0.62, 0.60)),
       ("BRIDGESTRUCT", (0.60, 0.59, 0.56)), ("LIGHTPOST", (0.28, 0.28, 0.30)), ("LIGHTS", (1.0, 0.75, 0.25)),
       ("1WALL_STUB", (0.80, 0.79, 0.74)), ("1WALL", (0.72, 0.72, 0.70)), ("SIGNARROW", (0.03, 0.03, 0.03)),
       ("SIGNPLATE", (0.95, 0.78, 0.05)), ("SIGNPOST", (0.5, 0.5, 0.52)), ("MEDIAN", (0.45, 0.30, 0.22))]


def color_of(name):
    u = name.upper()
    for p, c in COL:
        if u.startswith(p):
            return c
    return None


cfg = json.load(open(PROJ + "/track.config.json", encoding="utf-8"))
lights = json.load(open(PROJ + "/data/lights.local.json", encoding="utf-8"))
sl = (cfg.get("lighting") or {}).get("streetlight") or {}
SODIUM = tuple(float(v) for v in sl.get("color", [1.0, 0.647, 0.118]))
lenses = ((lights.get("provenance") or {}).get("lens_xyz")) or []
bases = lights.get("lamp_bases_xz") or []

# --- the eye -------------------------------------------------------------------------------------------------
if LAMP is not None:
    i = int(LAMP)
    bx, bz = bases[i]
    hx, hy, hz = lights["lampheads"][i]
    # from the road side, looking at the base: the eye DIST m along the lamp's road-ward direction from the base
    rx, rz = (hx - bx), (hz - bz)
    L = math.hypot(rx, rz) or 1.0
    rx, rz = rx / L, rz / L
    eye_xz = (bx + rx * DIST, bz + rz * DIST)
    look_xz = (bx, bz)
    focus = look_xz
else:
    conns = {c["name"]: c for c in json.load(open(PROJ + "/data/connectors.local.json", encoding="utf-8"))["connectors"]}
    pts = [(q[0], q[2]) for q in conns[PIECE]["points_xyz_m"]]
    u = float(U)
    acc, k = 0.0, 0
    while k < len(pts) - 2 and acc + math.dist(pts[k], pts[k + 1]) < u:
        acc += math.dist(pts[k], pts[k + 1])
        k += 1
    a_, b_ = pts[k], pts[k + 1]
    tx, tz = b_[0] - a_[0], b_[1] - a_[1]
    Lt = math.hypot(tx, tz) or 1.0
    tx, tz = tx / Lt, tz / Lt
    if BACK:
        tx, tz = -tx, -tz
    t = (u - acc) / Lt
    cx, cz = a_[0] + (b_[0] - a_[0]) * t, a_[1] + (b_[1] - a_[1]) * t
    nx, nz = -tz, tx                                  # left of travel
    lane = -LANE_OFF_M if LANE.upper() == "R" else LANE_OFF_M
    eye_xz = (cx + nx * lane, cz + nz * lane)
    look_xz = (eye_xz[0] + tx * 60.0, eye_xz[1] + tz * 60.0)
    focus = eye_xz

# --- the OBJ within KEEP_M of the focus ------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
V, groups, cur = [], {}, None
fx, fz = focus
with open(OBJ, encoding="utf-8", errors="replace") as f:
    for ln in f:
        c = ln[:2]
        if c == "v ":
            p = ln.split()
            V.append((float(p[1]), float(p[3]), float(p[2])))
        elif c == "o " or c == "g ":
            nm = ln[2:].strip()
            cur = nm if color_of(nm) else None
            if cur:
                groups.setdefault(cur, [])
        elif c == "f " and cur:
            idx = [int(q.split("/")[0]) - 1 for q in ln.split()[1:]]
            p0 = V[idx[0]]
            if (p0[0] - fx) ** 2 + (p0[1] - fz) ** 2 <= KEEP_M * KEEP_M:
                groups[cur].append(idx)
mats = {}


def mat(col, emissive=False):
    key = (col, emissive)
    if key in mats:
        return mats[key]
    m = bpy.data.materials.new("m%d" % len(mats))
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*col, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.85
    if emissive:
        bsdf.inputs["Emission Color"].default_value = (*col, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 40.0
    m.diffuse_color = (*col, 1.0)
    mats[key] = m
    return m


road_parts = []
for nm, faces in groups.items():
    if not faces:
        continue
    used, vs, fs = {}, [], []
    for fc in faces:
        q = []
        for i in fc:
            if i not in used:
                used[i] = len(vs)
                vs.append(V[i])
            q.append(used[i])
        fs.append(q[::-1])
    me = bpy.data.meshes.new(nm)
    me.from_pydata(vs, [], fs)
    me.update()
    ob = bpy.data.objects.new(nm, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat(color_of(nm), emissive=nm.upper().startswith("LIGHTS")))
    if nm.upper().startswith(("1ROAD", "1KERB", "1GRASS")):
        road_parts.append((vs, fs))
rv, rf = [], []
for vs, fs in road_parts:
    off = len(rv)
    rv += vs
    rf += [[i + off for i in q] for q in fs]
ground = BVHTree.FromPolygons(rv, rf)


def deck(x, y):
    h = ground.ray_cast(Vector((x, y, 3000.0)), Vector((0, 0, -1)))
    return h[0].z if h[0] is not None else None


sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("sky")
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
sc.world = world
if DAY:
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_shadows = True
    sh.shadow_intensity = 0.45
    sh.show_cavity = True
    sh.cavity_type = "WORLD"
    sh.show_backface_culling = True
    sh.background_type = "WORLD"
    world.color = (0.55, 0.70, 0.88)
    sc.display.light_direction = (0.35, -0.45, 0.82)
else:
    sc.render.engine = "BLENDER_EEVEE_NEXT" if hasattr(bpy.types, "SceneEEVEE") and "BLENDER_EEVEE_NEXT" in \
        [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    bg.inputs[0].default_value = (0.004, 0.006, 0.014, 1.0)
    bg.inputs[1].default_value = 1.0
    sc.eevee.use_shadows = True if hasattr(sc.eevee, "use_shadows") else None
    n = 0
    for lx, ly, lz in lenses:
        if (lx - fx) ** 2 + (lz - fz) ** 2 > LIGHT_REACH_M * LIGHT_REACH_M:
            continue
        ld = bpy.data.lights.new("lamp%d" % n, type="SPOT")
        ld.color = SODIUM
        ld.energy = 6000.0                            # a render light, not CSP's intensity: enough for a pool to read
        ld.spot_size = math.radians(150.0)
        ld.spot_blend = 0.5
        ld.shadow_soft_size = 0.4
        lo = bpy.data.objects.new("lamp%d" % n, ld)
        lo.location = (lx, lz, ly - 0.15)
        lo.rotation_euler = (0.0, 0.0, 0.0)           # a spot points down -Z: straight down
        sc.collection.objects.link(lo)
        n += 1
    print(f"[stills] {n} lamps lit within {LIGHT_REACH_M:.0f} m of the eye")
cd = bpy.data.cameras.new("cam")
cd.sensor_fit = "HORIZONTAL"
cd.lens = 24.0 if LAMP is None else 35.0
cd.clip_start = 0.05
cd.clip_end = 15000.0
cam = bpy.data.objects.new("cam", cd)
sc.collection.objects.link(cam)
sc.camera = cam
ex, ez = eye_xz
gy = deck(ex, ez)
if gy is None:
    raise SystemExit(f"[stills] no ground under the eye at ({ex:.1f}, {ez:.1f})")
eye_h = EYE_M if LAMP is None else 1.5
eye = Vector((ex, ez, gy + eye_h))
lx_, lz_ = look_xz
ly_ = (deck(lx_, lz_) or gy) + (EYE_M if LAMP is None else 0.3)
look = Vector((lx_, lz_, ly_))
cam.location = eye
cam.rotation_euler = (look - eye).to_track_quat("-Z", "Y").to_euler()
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print(f"[stills] wrote {OUT}: eye ({ex:.1f}, {gy + eye_h:.1f}, {ez:.1f}) looking at ({lx_:.1f}, {lz_:.1f}); "
      f"{'day' if DAY else 'night'}; {len(groups)} mesh classes within {KEEP_M:.0f} m")
