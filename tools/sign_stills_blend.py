"""Driver's-seat stills of W1-6 signs on a BUILT gate OBJ (ledger 0054 P4) — what Kevin sees driving up to a corner.

    blender --background --factory-startup --python-exit-code 1 --python tools/sign_stills_blend.py -- \\
        --proj <project> --obj <project>/data/track[.<layout>].obj --layout street|race_cw|race_acw --out <prefix> \\
        --sign <id>[,<id>...] [--corner <id>:<x>,<z>:<heading_deg>[,...]] [--back <m>] [--fov <deg>]

The OBJ is the kn5 set the layout loads (scripts/modkit/kn5_to_gate_obj): data/track.obj for the street layout (the road
kn5 + the street-only kn5), data/track.<id>.obj for a race layout (road + common race + ITS closure — so a race layout's
own plates, which ship in its closure kn5, are in its OBJ and in no other). Engine frame x=E, y=up, z=N -> Blender
(x, z, y). Workbench, back faces culled (as AC), each mesh class in a flat colour (road grey, curb pale, grass green,
K-rail / race wall concrete, race kerb red, paint white / yellow, SIGNPLATE yellow, SIGNARROW black, SIGNPOST grey).

--sign <id>: one still per sign record of data/signs.local.json (tools/place_signs.py): the eye stands on the BUILT road
  (a ray down onto the 1ROAD sheets) at a driver's 1.2 m, BACK_M before the sign's ray origin A along the approach
  tangent (the record's own approach, in the lane the rule launched from), looking at the plate; the file is
  <prefix>_<layout>_<id>.png. A sign id the layout cannot see (another layout's plate) is refused.
--corner <id>:<x>,<z>:<heading>: a still with NO sign — the eye BACK_M before (x, z) travelling along the heading
  (compass degrees), looking at (x, z): Free Roam at J1 with no arrow, for the comparison.
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


PROJ, OBJ, LAYOUT, OUT = arg("--proj"), arg("--obj"), arg("--layout", "street"), arg("--out")
SIGNS = [s for s in (arg("--sign") or "").split(",") if s]
CORNERS = [c for c in (arg("--corner") or "").split(";") if c]
BACK_M = float(arg("--back", "30"))
FOV = float(arg("--fov", "70"))
KEEP = 400.0
COL = [("GRASS_FAR", (93 / 255, 93 / 255, 66 / 255)), ("1GRASS", (68 / 255, 92 / 255, 40 / 255)),
       ("1ROAD", (0.34, 0.34, 0.35)), ("1KERB_RACE", (0.62, 0.10, 0.08)), ("1KERB", (0.66, 0.66, 0.64)),
       ("MARKINGS", (0.92, 0.92, 0.90)), ("YLINE", (0.85, 0.68, 0.1)), ("HOUSE", (0.78, 0.70, 0.58)),
       ("BUILDING", (0.72, 0.72, 0.70)), ("BRIDGESTRUCT", (0.70, 0.69, 0.66)), ("LIGHTPOST", (0.25, 0.25, 0.27)),
       ("LIGHTS", (0.9, 0.8, 0.5)), ("1WALL_RACE", (0.80, 0.79, 0.74)), ("1WALL_STUB", (0.86, 0.85, 0.80)),
       ("1WALL", (0.78, 0.78, 0.76)), ("SIGNARROW", (0.03, 0.03, 0.03)), ("SIGNPLATE", (0.95, 0.78, 0.05)),
       ("SIGNPOST", (0.55, 0.55, 0.57)), ("TERRAIN", (68 / 255, 92 / 255, 40 / 255)), ("CURB", (0.66, 0.66, 0.64))]


def color_of(name):
    u = name.upper()
    for p, c in COL:
        if u.startswith(p):
            return c
    return None


bpy.ops.wm.read_factory_settings(use_empty=True)
signs = json.load(open(PROJ + "/data/signs.local.json", encoding="utf-8"))
recs = {s["id"]: s for s in signs["signs"]}
for sid in SIGNS:
    if sid not in recs:
        raise SystemExit(f"[stills] no placed sign {sid!r} in data/signs.local.json")
    lay = recs[sid].get("layout")
    if lay and str(lay) != LAYOUT:
        raise SystemExit(f"[stills] sign {sid!r} is layout {lay}'s own plate: layout {LAYOUT} never loads it")
focus = [tuple(recs[s]["base_xz"]) for s in SIGNS]
corner_specs = []
for c in CORNERS:
    cid, xz, hd = c.split(":")
    x, z = (float(v) for v in xz.split(","))
    corner_specs.append((cid, (x, z), float(hd)))
    focus.append((x, z))
if not focus:
    raise SystemExit("[stills] nothing to shoot: --sign and/or --corner")

V, groups, cur = [], {}, None
with open(OBJ, encoding="utf-8", errors="replace") as f:
    for ln in f:
        c = ln[:2]
        if c == "v ":
            p = ln.split()
            V.append((float(p[1]), float(p[3]), float(p[2])))        # engine (x, y, z) -> Blender (x, z, y)
        elif c == "o " or c == "g ":
            nm = ln[2:].strip()
            cur = nm if color_of(nm) else None
            if cur:
                groups.setdefault(cur, [])
        elif c == "f " and cur:
            idx = [int(t.split("/")[0]) - 1 for t in ln.split()[1:]]
            p0 = V[idx[0]]
            if min((p0[0] - fx) ** 2 + (p0[1] - fz) ** 2 for fx, fz in focus) <= KEEP * KEEP:
                groups[cur].append(idx)
mats = {}


def solid_mat(col):
    if col in mats:
        return mats[col]
    m = bpy.data.materials.new("m%d" % len(mats))
    m.diffuse_color = (*col, 1.0)
    mats[col] = m
    return m


def add_mesh(nm, vs, fs, col):
    me = bpy.data.meshes.new(nm)
    me.from_pydata(vs, [], fs)
    me.update()
    ob = bpy.data.objects.new(nm, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(solid_mat(col))
    return ob


road_parts = []
n_sign = 0
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
    add_mesh(nm, vs, fs, color_of(nm))
    if nm.upper().startswith("1ROAD"):
        road_parts.append((vs, fs))
    if nm.upper().startswith("SIGN"):
        n_sign += 1
rv, rf = [], []
for vs, fs in road_parts:
    off = len(rv)
    rv += vs
    rf += [[i + off for i in q] for q in fs]
if not rv:
    raise SystemExit("[stills] no 1ROAD faces within reach of the focus points")
road = BVHTree.FromPolygons(rv, rf)
print(f"[stills] {OBJ}: {len(groups)} mesh groups kept near {len(focus)} focus point(s); {n_sign} SIGN* meshes in this layout's set")


def deck(x, y, near=None):
    z0 = 3000.0 if near is None else near + 6.0
    h = road.ray_cast(Vector((x, y, z0)), Vector((0, 0, -1)))
    return h[0].z if h[0] is not None else None


sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"
sh.color_type = "MATERIAL"
sh.show_shadows = True
sh.shadow_intensity = 0.45
sh.show_cavity = True
sh.cavity_type = "WORLD"
sh.show_backface_culling = True
sh.show_specular_highlight = False
sh.background_type = "WORLD"
world = bpy.data.worlds.new("sky")
world.color = (0.55, 0.70, 0.88)
sc.world = world
sc.display.light_direction = (0.35, -0.45, 0.82)
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.view_settings.view_transform = "Standard"
cd = bpy.data.cameras.new("cam")
cd.sensor_fit = "HORIZONTAL"
cd.clip_start = 0.05
cd.clip_end = 15000.0
cam = bpy.data.objects.new("cam", cd)
sc.collection.objects.link(cam)
sc.camera = cam


def shoot(path, eye_xy, target_xy, fov=FOV, eye_up=1.2, t_up=1.6):
    """eye on the BUILT road at eye_xy (driver's 1.2 m), looking at target_xy t_up over the road there"""
    z = deck(*eye_xy)
    if z is None:
        raise SystemExit(f"no road under the eye of {path} at {eye_xy}")
    eye = Vector((eye_xy[0], eye_xy[1], z + eye_up))
    tz = deck(*target_xy, near=z)
    tgt = Vector((target_xy[0], target_xy[1], (tz if tz is not None else z) + t_up))
    cd.angle = math.radians(fov)
    cam.location = eye
    cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[stills] wrote", path, "eye", [round(c, 2) for c in eye], "target", [round(c, 2) for c in tgt])


for sid in SIGNS:
    s = recs[sid]
    t = s["approach"]["t_xz"]
    A = s["ray"]["A_xz"]
    eye = (A[0] - t[0] * BACK_M, A[1] - t[1] * BACK_M)
    shoot("%s_%s_%s.png" % (OUT, LAYOUT, sid.replace("@", "_at_")), eye, tuple(s["base_xz"]))
for cid, (x, z), hd in corner_specs:
    tx, tz = math.sin(math.radians(hd)), math.cos(math.radians(hd))     # compass heading -> engine (E, N)
    shoot("%s_%s_%s_noarrow.png" % (OUT, LAYOUT, cid), (x - tx * BACK_M, z - tz * BACK_M), (x, z))
