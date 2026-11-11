"""Ledger 0084, engine fixes after the overnight run: road_wear_blend._kerbs on synthetic kerb runs (no track build).

    blender --background --factory-startup --python kerb_ab_blend.py -- <code tree> <paint png> <case> <out dir>

case hp:     High Plains 0.1.7's shape: u inside a kerb.atlas cell (0.05 .. 0.45), v = arc / 2 m
case repeat: the paint repeats (Pueblo / Aspen): run 0 sections u 0, 0.4, 1.3, 2.1 (faces straddle 1.0 and 2.0), run 1
             author_kerbs_blend's paint profile without a cell, u 0, 1, 2.111 (Pueblo's FATAL's u range)
Writes <out>/result.json (md5s of the UVs, positions, atlas and record) and <out>/fake.json (the gate's kerb input).
"""
import hashlib, json, math, sys
from pathlib import Path

a = sys.argv[sys.argv.index("--") + 1:]
TREE, PAINT, CASE, OUT = Path(a[0]), Path(a[1]), a[2], Path(a[3])
sys.path.insert(0, str(TREE / "tools")); sys.path.insert(0, str(TREE))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
import road_wear_blend as rwb  # noqa: E402
from scripts.aerial import road_wear as rw  # noqa: E402

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
proj = OUT / "proj"
(proj / "textures").mkdir(parents=True, exist_ok=True)
(proj / "textures" / PAINT.name).write_bytes(PAINT.read_bytes())
(proj / "track.config.json").write_text(json.dumps({"texture_overrides": {"1KERB": {"diffuse": f"textures/{PAINT.name}"}}}))

t = np.linspace(0, 2 * np.pi, 400, endpoint=False)
LP = np.column_stack([60 * np.cos(t), 35 * np.sin(t), np.full(len(t), 2.0)])
w = dict(rw.DEFAULTS["wear"])
I, _ = rw.rubber_intensity(LP, 2.0, w, True)
lines = [{"P": LP, "I": I, "closed": True, "layer_m": 10.0}]
reach = 0.5 * w["track_m"] + 4 * w["spread_m"]


def run(k, a0, a1, offs, us, rows_n=30):
    verts, faces, uvs = [], [], []
    for i in range(rows_n):
        ang = a0 + (a1 - a0) * i / (rows_n - 1)
        c = np.array([60 * math.cos(ang), 35 * math.sin(ang)]); nrm = c / np.linalg.norm(c)
        for j, o in enumerate(offs):
            q = c - nrm * (o + 1.0)
            verts.append((q[0], q[1], 2.05 + 0.01 * j)); uvs.append((us[j], i * 0.5))
    for i in range(rows_n - 1):
        for j in range(len(offs) - 1):
            q0 = i * len(offs) + j; q1 = q0 + len(offs)
            faces.append((q0, q0 + 1, q1 + 1, q1))
    name = f"1KERB_circuit_{k}"
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    uvl = me.uv_layers.new(name="KerbUV")
    for poly in me.polygons:
        for li in poly.loop_indices:
            uvl.data[li].uv = uvs[me.loops[li].vertex_index]
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new(f"{name}_mat"); mat.use_nodes = True
    img = bpy.data.images.load(str(proj / "textures" / PAINT.name))
    nd = mat.node_tree.nodes.new("ShaderNodeTexImage"); nd.image = img
    me.materials.append(mat)
    return ob


if CASE == "hp":
    obs = [run(0, -0.3, 0.3, [-1.2, -0.6, 0.0, 0.6, 1.2, 2.2], [0.05 + 0.4 * j / 5 for j in range(6)])]
else:
    obs = [run(0, -0.3, 0.3, [-1.2, -0.4, 0.8, 2.0], [0.0, 0.4, 1.3, 2.1]),
           run(1, 2.8, 3.4, [-0.5, 0.0, 0.555], [0.0, 1.0, 2.111])]


def snap():
    out = {}
    for ob in obs:
        me = ob.data
        co = np.empty(len(me.vertices) * 3, dtype=np.float32); me.vertices.foreach_get("co", co)
        uv = np.empty(len(me.loops) * 2, dtype=np.float32); me.uv_layers.active.data.foreach_get("uv", uv)
        out[ob.name] = (co, uv, len(me.polygons), len(me.loops))
    return out


s0 = snap()
spec = rw.spec_from_config({"road_wear": {"kerbs": {}}})
ksp = rw.kerb_spec(spec)
texdir = proj / "textures" / "road_wear"; texdir.mkdir(parents=True, exist_ok=True)
rows = {}
rec = rwb._kerbs(proj, None, ksp, spec, lines, w, reach, texdir, rows)
res = {"case": CASE, "tree": str(TREE), "ok": rec is not None}
if rec is not None:
    s1 = snap()
    md5 = lambda b: hashlib.md5(b).hexdigest()
    res["positions_same"] = all(np.array_equal(s0[n][0], s1[n][0]) for n in s0)
    res["topology_same"] = all(s0[n][2:] == s1[n][2:] for n in s0)
    res["positions_md5"] = md5(b"".join(s1[n][0].tobytes() for n in sorted(s1)))
    res["uv_before_md5"] = md5(b"".join(s0[n][1].tobytes() for n in sorted(s0)))
    res["uv_after_md5"] = md5(b"".join(s1[n][1].tobytes() for n in sorted(s1)))
    res["v_same"] = all(np.array_equal(s0[n][1][1::2], s1[n][1][1::2]) for n in s0)
    res["atlas"] = {v["atlas"]: md5((texdir / v["atlas"]).read_bytes()) for v in rec["paint"].values()}
    res["record_md5"] = md5(json.dumps({k: v for k, v in rec.items() if k != "paint"}, sort_keys=True).encode())
    res["record"] = {k: v for k, v in rec.items() if k not in ("faces", "objects", "materials")}
    res["rows_md5"] = md5(json.dumps({m: {kk: vv for kk, vv in r.items() if kk != "textures"} for m, r in rows.items()},
                                     sort_keys=True).encode())
    # paint per point: every loop's texel in the shipped atlas against the wrap's frac(u) in the paint
    V = []; idx = []
    for ob in obs:
        me = ob.data; me.calc_loop_triangles()
        for lt in me.loop_triangles:
            for li in lt.loops:
                co = ob.matrix_world @ me.vertices[me.loops[li].vertex_index].co
                u, v = me.uv_layers.active.data[li].uv
                idx.append(len(V)); V.append((co.x, co.z, -co.y, u, -v))
    json.dump({"decl": {"materials": rows, "spec": spec, "kerbs": rec}, "V": V, "idx": idx,
               "uv_before": {n: s0[n][1].tolist() for n in s0}, "uv_after": {n: s1[n][1].tolist() for n in s1},
               "line": [np.round(LP, 3).tolist(), np.round(I, 4).tolist()]}, open(OUT / "fake.json", "w"), default=float)
(OUT / "result.json").write_text(json.dumps(res, indent=1, default=str))
print("RESULT", json.dumps({k: v for k, v in res.items() if k != "record"}))
