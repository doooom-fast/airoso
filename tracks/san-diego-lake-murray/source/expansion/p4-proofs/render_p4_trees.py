"""Ledger 0054 P4 trees: driver's-eye stills of the north network's TreeFX planting on a BUILT gate OBJ (Drive 2, v0.19.1).

    blender --background --factory-startup --python-exit-code 1 --python render_p4_trees.py -- \\
        --obj <project>/data/track.obj --proj <project> --trees <built>/extension/trees/trees.txt \\
        --out <dir/prefix> --shots waring_median,pv_canyon,mg_apartments,jackson_rim

The ground, roads, walls and furniture are the gate OBJ in flat colours, as p3-proofs/render_p3.py draws them. The
TreeFX trees themselves are CSP runtime models the game draws, not meshes a Blender render can show, so every planted
position gets a STAND-IN at its planted spot and size: a crown (cone or ball) on a trunk for a tree, a low ball for a
bush, each species at an [invented] stand-in height x the planted size multiplier, snapped onto the built ground the way
CSP snaps the real model. The stills show WHERE and HOW DENSE the planting is and what stands on what; the real foliage
is Kevin's seat. The eye rides the north network's forward drive line (data/drive_lines.expansion.json) at a station
along a piece (data/expansion.north.json), 1.2 m over the built road, looking ahead along the line. Shots:
  waring_median   Waring at its s 300: the planted median's trees (A2, st 250-550) on the left of the lane, the yards
  pv_canyon       Princess View at its s 420: the canyon sides, scrub and natives, the rock faces bare
  mg_apartments   Mission Gorge at its s 650: the apartment frontage's street trees on the right, the river belt left
  jackson_rim     Jackson north at its s 1150: the E1 belt (Gum) on the NE rim to the left, the SW rock wall bare
Writes <prefix>_<shot>.jpg.
"""
import bpy, sys, math, json, re
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
arg = lambda k, d=None: a[a.index(k) + 1] if k in a else d
OBJ, PROJ, OUT, TREES = arg("--obj"), arg("--proj"), arg("--out"), arg("--trees")
SHOTS = (arg("--shots") or "waring_median,pv_canyon,mg_apartments,jackson_rim").split(",")
COL = [("GRASS_FAR", (93 / 255, 93 / 255, 66 / 255)), ("1GRASS", (68 / 255, 92 / 255, 40 / 255)), ("1ROAD", (0.34, 0.34, 0.35)),
       ("1KERB_RACE", (0.62, 0.10, 0.08)), ("1KERB", (0.66, 0.66, 0.64)), ("MARKINGS", (0.92, 0.92, 0.90)),
       ("YLINE", (0.85, 0.68, 0.1)), ("HOUSE", (0.78, 0.70, 0.58)), ("BUILDING", (0.72, 0.72, 0.70)),
       ("BRIDGESTRUCT", (0.70, 0.69, 0.66)), ("LIGHTPOST", (0.25, 0.25, 0.27)), ("LIGHTS", (0.9, 0.8, 0.5)),
       ("1WALL_STUB", (0.86, 0.85, 0.80)), ("1WALL", (0.80, 0.80, 0.78)), ("SIGNARROW", (0.03, 0.03, 0.03)),
       ("SIGNPLATE", (0.95, 0.78, 0.05)), ("SIGNPOST", (0.55, 0.55, 0.57)), ("MEDIAN", (0.52, 0.40, 0.30))]
# stand-ins [invented]: (kind, height m at size 1, crown colour). Palms: the models' native heights (make_treefx);
# the rest are typical mature heights of the species the model names.
STANDIN = {"PalmV1.bin": ("palm", 20.0, (0.30, 0.50, 0.22)), "PalmV2.bin": ("palm", 25.0, (0.30, 0.50, 0.22)),
           "PalmV3.bin": ("palm", 28.0, (0.30, 0.50, 0.22)), "Gum.bin": ("tree", 25.0, (0.50, 0.58, 0.44)),
           "Oak3.bin": ("tree", 12.0, (0.22, 0.38, 0.16)), "SycamoreV1.bin": ("tree", 15.0, (0.36, 0.55, 0.24)),
           "SycamoreV2.bin": ("tree", 18.0, (0.36, 0.55, 0.24)), "SycamoreV3.bin": ("tree", 18.0, (0.36, 0.55, 0.24)),
           "PepperV1.bin": ("tree", 10.0, (0.40, 0.56, 0.30)), "Pine_Aleppo.bin": ("tree", 15.0, (0.20, 0.36, 0.22)),
           "Sage.bin": ("bush", 1.2, (0.55, 0.60, 0.48)), "Bush.bin": ("bush", 1.5, (0.30, 0.44, 0.20)),
           "Bush2.bin": ("bush", 1.5, (0.30, 0.44, 0.20)), "Bush3.bin": ("bush", 1.2, (0.34, 0.46, 0.22)),
           "Yucca.bin": ("bush", 2.0, (0.45, 0.55, 0.35)), "Agave.bin": ("bush", 1.2, (0.48, 0.58, 0.50))}
TRUNK = (0.36, 0.26, 0.16)
KEEP = 900.0          # ground kept whole; furniture within this of a shot
KEEP_TREES = 420.0    # stand-ins within this of a shot's eye


def color_of(name):
    u = name.upper()
    for p, c in COL:
        if u.startswith(p):
            return c
    return None


lines = json.load(open(PROJ + "/data/drive_lines.expansion.json", encoding="utf-8"))["lines"]
exp = json.load(open(PROJ + "/data/expansion.north.json", encoding="utf-8"))
pieces = {p["id"]: p for p in exp["pieces"]}


def piece_xz(pid, s):
    rows, cols = pieces[pid]["stations"], pieces[pid]["columns"]
    i = min(range(len(rows)), key=lambda k: abs(rows[k][0] - s))
    return rows[i][cols.index("x")], rows[i][cols.index("z")]


def line_at_near(name, xz, ahead):
    pts = [(q[0], q[2]) for q in lines[name]["points_xyz_m"]]
    i = min(range(len(pts)), key=lambda k: (pts[k][0] - xz[0]) ** 2 + (pts[k][1] - xz[1]) ** 2)
    acc, j = 0.0, i
    while j < len(pts) - 1 and acc < ahead:
        acc += math.dist(pts[j], pts[j + 1])
        j += 1
    return pts[i], pts[j]


SHOTDEF = {"waring_median": lambda: line_at_near("fwd", piece_xz("A", 300.0), 90.0),
           "pv_canyon": lambda: line_at_near("fwd", piece_xz("B", 420.0), 100.0),
           "mg_apartments": lambda: line_at_near("fwd", piece_xz("C", 650.0), 90.0),
           "jackson_rim": lambda: line_at_near("fwd", piece_xz("D", 1150.0), 90.0)}
CAMS = {s: SHOTDEF[s]() for s in SHOTS}
FOCUS = [c[0] for c in CAMS.values()]

bpy.ops.wm.read_factory_settings(use_empty=True)
V, groups, cur = [], {}, None
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
            idx = [int(t.split("/")[0]) - 1 for t in ln.split()[1:]]
            p0 = V[idx[0]]
            far_ok = cur.upper().startswith(("GRASS_FAR", "1GRASS"))
            if far_ok or min((p0[0] - fx) ** 2 + (p0[1] - fz) ** 2 for fx, fz in FOCUS) <= KEEP * KEEP:
                groups[cur].append(idx)
mats = {}


def solid_mat(col):
    if col in mats:
        return mats[col]
    m = bpy.data.materials.new("m%d" % len(mats))
    m.diffuse_color = (*col, 1.0)
    mats[col] = m
    return m


ground_parts = []
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
    me.materials.append(solid_mat(color_of(nm)))
    if nm.upper().startswith(("1ROAD", "1GRASS", "GRASS_FAR")):
        ground_parts.append((vs, fs, nm.upper().startswith("1ROAD")))
rv, rf, gv, gf = [], [], [], []
for vs, fs, is_road in ground_parts:
    tv, tf = (rv, rf) if is_road else (gv, gf)
    off = len(tv)
    tv += vs
    tf += [[i + off for i in q] for q in fs]
road = BVHTree.FromPolygons(rv, rf)
ground = BVHTree.FromPolygons(gv, gf) if gv else None


def hit(tree, x, y):
    if tree is None:
        return None
    h = tree.ray_cast(Vector((x, y, 3000.0)), Vector((0, 0, -1)))
    return h[0].z if h[0] is not None else None


# --- the stand-ins ---------------------------------------------------------------------------------------------
def standin_mesh(kind, col):
    """unit stand-in (height 1 at the origin, z up): a crown on a trunk, or a low ball"""
    key = (kind, col)
    if key in mats:
        return mats[key]
    me = bpy.data.meshes.new("standin_%s_%d" % (kind, len(mats)))
    vs, fs, mi = [], [], []
    n = 8

    def ring(r, z):
        base = len(vs)
        for k in range(n):
            t = 2 * math.pi * k / n
            vs.append((r * math.cos(t), r * math.sin(t), z))
        return base

    def tube(b0, b1, m):
        for k in range(n):
            fs.append([b0 + k, b0 + (k + 1) % n, b1 + (k + 1) % n, b1 + k])
            mi.append(m)

    def cap(b, zc, m, up):
        """a fan over ring b to a centre at zc; up = the face looks up (a crown top), else down (a crown underside)"""
        c = len(vs)
        vs.append((0.0, 0.0, zc))
        for k in range(n):
            fs.append([b + k, b + (k + 1) % n, c] if up else [b + (k + 1) % n, b + k, c])
            mi.append(m)
    if kind == "bush":
        b0 = ring(0.45, 0.0)
        b1 = ring(0.62, 0.45)
        b2 = ring(0.40, 0.85)
        tube(b0, b1, 0)
        tube(b1, b2, 0)
        cap(b2, 1.0, 0, True)
    elif kind == "palm":
        b0 = ring(0.025, 0.0)
        b1 = ring(0.02, 0.80)
        tube(b0, b1, 1)
        b2 = ring(0.16, 0.80)
        b3 = ring(0.20, 0.92)
        tube(b2, b3, 0)
        cap(b3, 1.0, 0, True)
        cap(b2, 0.80, 0, False)
    else:
        b0 = ring(0.03, 0.0)
        b1 = ring(0.025, 0.30)
        tube(b0, b1, 1)
        b2 = ring(0.32, 0.30)
        b3 = ring(0.28, 0.75)
        tube(b2, b3, 0)
        cap(b3, 1.0, 0, True)
        cap(b2, 0.30, 0, False)
    me.from_pydata(vs, [], fs)
    me.materials.append(solid_mat(col))
    me.materials.append(solid_mat(TRUNK))
    for p, m in zip(me.polygons, mi):
        p.material_index = m
    me.update()
    mats[key] = me
    return me


placed = skipped = 0
rx = re.compile(r"^tree:\s*([^;]+)\.bin\s*;\s*pos\s*=\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*;.*?size\s*=\s*([-\d.]+)")
with open(TREES, encoding="utf-8") as f:
    for ln in f:
        m = rx.match(ln.strip())
        if not m:
            continue
        model = m.group(1).strip() + ".bin"
        x, y, zneg, size = float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5))
        z = -zneg
        if min((x - fx) ** 2 + (z - fz) ** 2 for fx, fz in FOCUS) > KEEP_TREES * KEEP_TREES:
            continue
        kind, h, col = STANDIN.get(model, ("tree", 10.0, (0.3, 0.5, 0.25)))
        gz = hit(ground, x, z)
        rz = hit(road, x, z)
        base = max(v for v in (gz, rz) if v is not None) if (gz is not None or rz is not None) else y
        ob = bpy.data.objects.new("t%d" % placed, standin_mesh(kind, col))
        ob.location = (x, z, base)
        s = h * size
        ob.scale = (s, s, s)
        bpy.context.scene.collection.objects.link(ob)
        placed += 1
print("[render] stand-ins placed", placed, "within", KEEP_TREES, "m of a shot")

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
sc.render.image_settings.file_format = "JPEG"
sc.render.image_settings.quality = 88
sc.view_settings.view_transform = "Standard"
cd = bpy.data.cameras.new("cam")
cd.sensor_fit = "HORIZONTAL"
cd.clip_start = 0.05
cd.clip_end = 15000.0
cam = bpy.data.objects.new("cam", cd)
sc.collection.objects.link(cam)
sc.camera = cam
for s in SHOTS:
    e, t = CAMS[s][:2]
    z = hit(road, *e)
    if z is None:
        raise SystemExit(f"no road under {s} at {e}")
    eye = Vector((e[0], e[1], z + 1.2))
    tz = hit(road, *t)
    if tz is None:
        tz = hit(ground, *t)
    tgt = Vector((t[0], t[1], (tz if tz is not None else z) + 0.6))
    cd.angle = math.radians(75.0)
    cam.location = eye
    cam.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{OUT}_{s}.jpg"
    bpy.ops.render.render(write_still=True)
    print("[render] wrote", sc.render.filepath, "eye", [round(c, 2) for c in eye], "target", [round(c, 2) for c in tgt])
