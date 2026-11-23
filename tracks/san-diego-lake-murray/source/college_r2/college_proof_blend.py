"""College Ave realism+: the standalone PROOF SCENE (stage A). Before = the road as built in 0.20.2 (the gate OBJ);
after = the design (college_design.json) on the surveyed ground. Three cameras, the same in both. Nothing in the
build is read or written except the gate OBJ.

    blender --background --factory-startup --python college_proof_blend.py -- <gate track.obj> <area_ground_1m.npz> <out dir>

After, inside the corridor (CORR_M each side of the line, v1130-1480): the built road, curb, paint and ground are
left out; in their place the design's two carriageways and the lidar's 1 m ground (the bank between the
carriageways drawn green). Outside the corridor everything is the build's. The seam between the two grounds at the
corridor's edge is not closed: this is a picture of the road's shape, not a mesh for the game.
Frames: engine x east, y up, z north -> Blender (x, z, y)."""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
argv = sys.argv[sys.argv.index("--") + 1:]
OBJ, NPZ, OUT = Path(argv[0]), Path(argv[1]), Path(argv[2])
OUT.mkdir(parents=True, exist_ok=True)
CORR_M = 40.0          # [chosen] the corridor's half width
BBOX_M = 260.0         # [chosen] the build shown this far around the design
EYE_M = 1.15           # driver's eye over the road

D = json.loads((HERE / "college_design.json").read_text(encoding="utf-8"))
L = json.loads((HERE / "college_xsec.lidar.g10.json").read_text(encoding="utf-8"))
R = D["stations"]
vi = {v: i for i, v in enumerate(L["stations"]["v"])}
P = np.array([[L["stations"]["x"][vi[r["v"]]], L["stations"]["z"][vi[r["v"]]]] for r in R])
Nn = np.array([[L["stations"]["nx"][vi[r["v"]]], L["stations"]["nz"][vi[r["v"]]]] for r in R])
YL = np.array([L["stations"]["y_line"][vi[r["v"]]] for r in R])
KEYS = ("sb_outer", "sb_inner", "nb_inner", "nb_outer")
OFFS = {k: np.array([r[k]["offset_m"] for r in R]) for k in KEYS}
YD = {k: np.array([r[k]["y"] for r in R]) for k in KEYS}
YB = {k: np.array([r[k]["y_built"] for r in R]) for k in KEYS}
XZ = {k: np.array([[r[k]["x"], r[k]["z"]] for r in R]) for k in KEYS}
ISL = np.array([r["island"] for r in R])
n = len(R)


def station_frame(pts):
    """nearest station index, offset (+ west) and along-line distance for points [m, 2]"""
    out_k = np.zeros(len(pts), int)
    out_o = np.zeros(len(pts))
    out_a = np.zeros(len(pts))
    for a in range(0, len(pts), 20000):
        q = pts[a:a + 20000]
        d2 = ((q[:, None, :] - P[None, :, :]) ** 2).sum(axis=2)
        k = d2.argmin(axis=1)
        dv = q - P[k]
        out_k[a:a + 20000] = k
        out_o[a:a + 20000] = (dv * Nn[k]).sum(axis=1)
        out_a[a:a + 20000] = dv[:, 0] * Nn[k][:, 1] * -1 + dv[:, 1] * Nn[k][:, 0]      # along the tangent (-nz, nx) rotated
    return out_k, out_o, out_a


def in_corridor(pts):
    k, o, a = station_frame(pts)
    return (np.abs(o) <= CORR_M) & (np.abs(a) <= 4.0), k, o


# --- the build, from the gate OBJ ------------------------------------------------------------------------------------------
x0, x1 = P[:, 0].min() - BBOX_M, P[:, 0].max() + BBOX_M
z0, z1 = P[:, 1].min() - BBOX_M, P[:, 1].max() + BBOX_M
GROUPS = (("road", ("1ROAD",)), ("kerb", ("1KERB",)), ("mark", ("MARKINGS",)), ("ground", ("1GRASS",)),
          ("wall", ("1WALL",)), ("bldg", ("HOUSE", "BUILDING", "ROOFTOP", "FARBLOCK")))
verts = []
faces = {g: [] for g, _ in GROUPS}
cur = None
with OBJ.open(encoding="ascii", errors="replace") as fh:
    for line in fh:
        c = line[:2]
        if c == "v ":
            p = line.split()
            verts.append((float(p[1]), float(p[2]), float(p[3])))
        elif c == "o ":
            name = line[2:].strip()
            cur = next((g for g, pre in GROUPS if name.startswith(pre)), None)
        elif c == "f " and cur:
            idx = [int(t.split("/")[0]) - 1 for t in line.split()[1:]]
            v = verts[idx[0]]
            if x0 <= v[0] <= x1 and z0 <= v[2] <= z1:
                faces[cur].append(idx[:3] if len(idx) == 3 else idx[:4])
verts = np.array(verts)
print("[proof] build faces:", {g: len(f) for g, f in faces.items()})

COLORS = {"road": (0.07, 0.07, 0.075), "kerb": (0.42, 0.41, 0.39), "mark": (0.85, 0.85, 0.8), "ground": (0.30, 0.33, 0.20),
          "wall": (0.5, 0.5, 0.48), "bldg": (0.62, 0.58, 0.52), "bank": (0.20, 0.36, 0.14), "design": (0.085, 0.085, 0.09)}
MATS = {}
for name, col in COLORS.items():
    m = bpy.data.materials.new("proof_" + name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*col, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    MATS[name] = m


def add_mesh(name, vs, fs, mat, coll):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(float(a), float(c), float(b)) for a, b, c in vs], [], [tuple(int(i) for i in f) for f in fs])
    me.update()
    me.materials.append(MATS[mat])
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def compact(fs):
    used = sorted({i for f in fs for i in f})
    remap = {g: k for k, g in enumerate(used)}
    return verts[used], [[remap[i] for i in f] for f in fs]


scene = bpy.context.scene
before = bpy.data.collections.new("before")
after = bpy.data.collections.new("after")
scene.collection.children.link(before)
scene.collection.children.link(after)
for g, fs in faces.items():
    if not fs:
        continue
    vs, f2 = compact(fs)
    add_mesh("built_" + g, vs, f2, g, before)
    if g in ("road", "kerb", "mark", "ground"):
        cen = np.array([verts[f].mean(axis=0) for f in fs])
        inside, _, _ = in_corridor(cen[:, [0, 2]])
        keep = [f for f, i in zip(fs, inside) if not i]
    else:
        keep = fs
    if keep:
        vs, f2 = compact(keep)
        add_mesh("kept_" + g, vs, f2, g, after)

# --- the design's two carriageways -------------------------------------------------------------------------------------------
for name, a, b in (("design_sb", "sb_outer", "sb_inner"), ("design_nb", "nb_inner", "nb_outer")):
    vs = []
    fs = []
    for k in range(n):
        vs.append((XZ[a][k, 0], YD[a][k] + 0.03, XZ[a][k, 1]))
        vs.append((XZ[b][k, 0], YD[b][k] + 0.03, XZ[b][k, 1]))
    for k in range(n - 1):
        fs.append((2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2))
    add_mesh(name, vs, fs, "design", after)

# --- the surveyed ground in the corridor ---------------------------------------------------------------------------------------
z = np.load(NPZ, allow_pickle=True)
meta = json.loads(str(z["meta"]))
G = z["h_navd88_m"].astype(float) - 100.8
gx0, gzn, cm = meta["x0"], meta["z_north"], meta["cell_m"]
rows_i, cols_j = G.shape
jj0, jj1 = max(0, int((x0 - gx0) / cm)), min(cols_j, int((x1 - gx0) / cm))
ii0, ii1 = max(0, int((gzn - z1) / cm)), min(rows_i, int((gzn - z0) / cm))
sub = G[ii0:ii1, jj0:jj1].copy()
for _ in range(6):                      # close small holes (no ground return) from their neighbours
    nan = np.isnan(sub)
    if not nan.any():
        break
    pad = np.pad(sub, 1, constant_values=np.nan)
    stack = np.stack([pad[1 + di:pad.shape[0] - 1 + di, 1 + dj:pad.shape[1] - 1 + dj] for di in (-1, 0, 1) for dj in (-1, 0, 1)])
    with np.errstate(all="ignore"):
        fill = np.nanmean(stack, axis=0)
    sub[nan] = fill[nan]
gi, gj = np.mgrid[0:sub.shape[0], 0:sub.shape[1]]
gxx = gx0 + (jj0 + gj + 0.5) * cm
gzz = gzn - (ii0 + gi + 0.5) * cm
ins, kk, oo = in_corridor(np.stack([gxx.ravel(), gzz.ravel()], axis=1))
ins = ins.reshape(sub.shape)
kk = kk.reshape(sub.shape)
oo = oo.reshape(sub.shape)
pav = ((oo < OFFS["sb_outer"][kk] - 0.5) & (oo > OFFS["sb_inner"][kk] + 0.5)) | ((oo < OFFS["nb_inner"][kk] - 0.5) & (oo > OFFS["nb_outer"][kk] + 0.5))
bank = ISL[kk] & (oo <= OFFS["sb_inner"][kk] + 0.5) & (oo >= OFFS["nb_inner"][kk] - 0.5)
use = ins & ~pav & ~np.isnan(sub)
idx = -np.ones(sub.shape, int)
idx[use] = np.arange(use.sum())
gv = np.stack([gxx[use], sub[use], gzz[use]], axis=1)
fg, fb_ = [], []
a_, b_, c_, d_ = idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]
ok = (a_ >= 0) & (b_ >= 0) & (c_ >= 0) & (d_ >= 0)
isb = bank[:-1, :-1] & ok
for arr, mask in ((fg, ok & ~isb), (fb_, isb)):
    q = np.stack([a_[mask], d_[mask], c_[mask], b_[mask]], axis=1)
    arr.extend(q.tolist())


def sub_mesh(name, fs, mat):
    if not fs:
        return
    used = sorted({i for f in fs for i in f})
    remap = {g: k for k, g in enumerate(used)}
    add_mesh(name, gv[used], [[remap[i] for i in f] for f in fs], mat, after)


sub_mesh("survey_ground", fg, "ground")
sub_mesh("survey_bank", fb_, "bank")
# how well the grid agrees with the per-station lidar on the line (a check of the grid's frame)
chk = []
for k in range(0, n, 10):
    j = int((P[k, 0] - gx0) / cm)
    i = int((gzn - P[k, 1]) / cm)
    if 0 <= i < rows_i and 0 <= j < cols_j and not np.isnan(G[i, j]):
        chk.append(G[i, j] - 0.5 * (YD["sb_inner"][k] + YD["nb_inner"][k]) if not ISL[k] else np.nan)
chk = np.array([c for c in chk if not np.isnan(c)])
print(f"[proof] grid minus design on the line where there is no island: median {np.median(chk):+.3f} m, max abs {np.abs(chk).max():.3f} m ({len(chk)} stations)")

# --- light, sky, cameras, render -----------------------------------------------------------------------------------------------
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x, scene.render.resolution_y = 1600, 720
scene.render.image_settings.file_format = "PNG"
scene.eevee.taa_render_samples = 32
world = bpy.data.worlds.new("sky")
world.use_nodes = True
sky = world.node_tree.nodes.new("ShaderNodeTexSky")
sky.sky_type = "NISHITA"
sky.sun_elevation = math.radians(42)
sky.sun_rotation = math.radians(200)
world.node_tree.links.new(sky.outputs["Color"], world.node_tree.nodes["Background"].inputs["Color"])
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
scene.world = world
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 3.5
so = bpy.data.objects.new("sun", sun)
so.rotation_euler = (math.radians(48), 0, math.radians(200))
scene.collection.objects.link(so)
cam = bpy.data.cameras.new("cam")
cam.clip_end = 4000
co = bpy.data.objects.new("cam", cam)
scene.collection.objects.link(co)
scene.camera = co
ks = {r["v"]: i for i, r in enumerate(R)}


def mid(a, b, v, built):
    k = ks[v]
    y = 0.5 * ((YB if built else YD)[a][k] + (YB if built else YD)[b][k])
    xz = 0.5 * (XZ[a][k] + XZ[b][k])
    return Vector((xz[0], xz[1], y))


def aim(pos, target, lens):
    cam.lens = lens
    co.location = pos
    co.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()


VIEWS = []
for state in ("before", "after"):
    b = state == "before"
    e = Vector((0, 0, EYE_M))
    VIEWS.append((state, "1_northbound_v1215", mid("nb_inner", "nb_outer", 1215, b) + e, mid("nb_inner", "nb_outer", 1250, b) + e, 26))
    VIEWS.append((state, "2_southbound_v1410", mid("sb_inner", "sb_outer", 1410, b) + e, mid("sb_inner", "sb_outer", 1372, b) + e, 26))
    k = ks[1215]
    west = Vector((P[k, 0] + 150 * Nn[k, 0], P[k, 1] + 150 * Nn[k, 1], YL[k] + 85))
    VIEWS.append((state, "3_from_the_southwest", west, mid("nb_inner", "sb_inner", 1310, False), 32))
for state, name, pos, tgt, lens in VIEWS:
    before.hide_render = state != "before"
    after.hide_render = state != "after"
    aim(pos, tgt, lens)
    scene.render.filepath = str(OUT / f"proof_{name}_{state}.png")
    bpy.ops.render.render(write_still=True)
    print("[proof] rendered", scene.render.filepath)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "college_proof.blend"))
print("[proof] done")
