import sys, json, math
from pathlib import Path
A = Path(sys.argv[sys.argv.index("--") + 1]); W = Path(sys.argv[sys.argv.index("--") + 2])
sys.path.insert(0, str(A / "tools")); sys.path.insert(0, str(A))
import bpy, numpy as np
import road_wear_blend as rwb
from scripts.aerial import road_wear as rw
proj = W / "proj"
# a lap: an ellipse; a kerb run on the inside of the tight end, 0.2-1.4 m inside the line's inner tyre region
t = np.linspace(0, 2 * np.pi, 400, endpoint=False)
P = np.column_stack([60 * np.cos(t), 35 * np.sin(t), np.full(len(t), 2.0)])
w = dict(rw.DEFAULTS["wear"])
I, _ = rw.rubber_intensity(P, 2.0, w, True)
lines = [{"P": P, "I": I, "closed": True, "layer_m": 10.0}]
reach = 0.5 * w["track_m"] + 4 * w["spread_m"]
verts, faces, uvs = [], [], []
rows_n = 30
offs = [-1.2, -0.6, 0.0, 0.6, 1.2, 2.2]
for i in range(rows_n):
    a = -0.3 + 0.6 * i / (rows_n - 1)
    c = np.array([60 * math.cos(a), 35 * math.sin(a)]); nrm = c / np.linalg.norm(c)
    for j, o in enumerate(offs):
        q = c - nrm * (o + 1.0)
        verts.append((q[0], q[1], 2.05)); uvs.append((0.05 + 0.4 * j / (len(offs) - 1), i * 0.5))
for i in range(rows_n - 1):
    for j in range(len(offs) - 1):
        q0 = i * len(offs) + j; q1 = q0 + len(offs)
        faces.append((q0, q0 + 1, q1 + 1, q1))
me = bpy.data.meshes.new("1KERB_circuit_0"); me.from_pydata(verts, [], faces); me.update()
uvl = me.uv_layers.new(name="KerbUV")
for poly in me.polygons:
    for li in poly.loop_indices:
        uvl.data[li].uv = uvs[me.loops[li].vertex_index]
ob = bpy.data.objects.new("1KERB_circuit_0", me); bpy.context.scene.collection.objects.link(ob)
mat = bpy.data.materials.new("1KERB_circuit_0_mat"); mat.use_nodes = True
img = bpy.data.images.load(str(proj / "textures" / "kerb_atlas_hp.png"))
nd = mat.node_tree.nodes.new("ShaderNodeTexImage"); nd.image = img
me.materials.append(mat)
spec = rw.spec_from_config({"road_wear": {"kerbs": {}}})
ksp = rw.kerb_spec(spec)
texdir = proj / "textures" / "road_wear"; texdir.mkdir(parents=True, exist_ok=True)
rows = {}
rec = rwb._kerbs(proj, None, ksp, spec, lines, w, reach, texdir, rows)
assert rec is not None
uv2 = np.empty(len(me.loops) * 2, dtype=np.float32); me.uv_layers.active.data.foreach_get("uv", uv2); uv2 = uv2.reshape(-1, 2)
print("rows", json.dumps(rows, default=str)[:400])
print("rec", {k: v for k, v in rec.items() if k != "faces"})
print("u range", uv2[:, 0].min(), uv2[:, 0].max(), "v range", uv2[:, 1].min(), uv2[:, 1].max())
print("node image", nd.image.name)
# write a fake decl + a fake kn5 parse for the gate's kerb rows (triangles = Blender loop triangles)
me.calc_loop_triangles()
V = []; idx = []
for lt in me.loop_triangles:
    for li in lt.loops:
        co = ob.matrix_world @ me.vertices[me.loops[li].vertex_index].co
        u, v = me.uv_layers.active.data[li].uv
        idx.append(len(V)); V.append((co.x, co.z, -co.y, u, v))
json.dump({"decl": {"materials": rows, "spec": spec, "kerbs": rec}, "V": V, "idx": idx,
           "line": [np.round(P, 3).tolist(), np.round(I, 4).tolist()]}, open(W / "fake.json", "w"), default=float)
print("OK")
