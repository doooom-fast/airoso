"""Far-clip test piece v3 -> project/blender/farclip.blend (Denver far-clip test, README d174240, + a distance ladder).
Blender frame = x east, y north, z up (the AC add-on writes AC (x, z, -y)). Every panel faces the track origin.
  FARCLIP_025/060/105      the spec's walls: 25 / 60 / 105 km at 250 / 270 / 290 deg, 0..2 deg tall, 4 deg wide
  FARCLIP_025/060/105_HI   a beacon above each, 2..10 deg (the 2 deg walls hide behind Sand Creek's own buildings)
  FARLAD_<km>_<R|G|B>      the LADDER: 2..10 deg tall, 2 deg wide beacons at 2, 5, 10, 15, 19, 25, 40, 60, 105 km on
                           bearings 262..302 deg (5 deg apart, near on the left), colours cycling red / green / blue"""
import bpy, math, sys
from mathutils import Vector
P = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
T = lambda deg: math.tan(math.radians(deg))
PANELS = []   # name, distance m, bearing deg, elevation lo deg, hi deg, width deg, texture
for name, d, brg, col in (("FARCLIP_025", 25000.0, 250.0, "red"), ("FARCLIP_060", 60000.0, 270.0, "green"), ("FARCLIP_105", 105000.0, 290.0, "blue")):
    PANELS.append((name, d, brg, 0.0, 2.0, 4.0, col))
    PANELS.append((name + "_HI", d, brg, 2.0, 10.0, 4.0, col + "_hi"))
for k, km in enumerate((2, 5, 10, 15, 19, 25, 40, 60, 105)):
    c = "RGB"[k % 3]
    PANELS.append((f"FARLAD_{km:03d}_{c}", km * 1000.0, 262.0 + 5.0 * k, 2.0, 10.0, 2.0, {"R": "red", "G": "green", "B": "blue"}[c] + "_hi"))
for name, d, brg, lo, hi, wdeg, tex in PANELS:
    t = math.radians(brg)
    c = Vector((d * math.sin(t), d * math.cos(t), 0.0))
    tang = Vector((math.cos(t), -math.sin(t), 0.0))
    w = 2.0 * d * T(wdeg / 2.0) if not name.startswith("FARCLIP") else {25000.0: 1746.0, 60000.0: 4190.0, 105000.0: 7333.0}[d]
    z0 = d * T(lo) if lo else 0.0
    z1 = d * T(hi) if name.endswith("_HI") or name.startswith("FARLAD") else {25000.0: 873.0, 60000.0: 2095.0, 105000.0: 3667.0}[d]
    a, b = c - tang * (w / 2), c + tang * (w / 2)
    verts = [a + Vector((0, 0, z0)), b + Vector((0, 0, z0)), b + Vector((0, 0, z1)), a + Vector((0, 0, z1))]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [(0, 1, 2, 3)]); me.update()
    if me.polygons[0].normal.dot(-c.normalized()) < 0:
        me.polygons[0].flip(); me.update()
    uv = me.uv_layers.new(name="UVMap")
    for li, loop in enumerate(me.loops):
        uv.data[li].uv = {0: (0, 0), 1: (1, 0), 2: (1, 1), 3: (0, 1)}[loop.vertex_index]
    mat = bpy.data.materials.new(name + "_mat"); mat.use_nodes = True
    tx = mat.node_tree.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(f"{P}/../tex/farclip_{tex}.png")
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    print(f"[farclip] {name:16} d {d/1000:5.0f} km brg {brg:5.1f} elev {lo}..{hi} deg w {w:7.0f} m")
bpy.ops.wm.save_as_mainfile(filepath=f"{P}/blender/farclip.blend")
print("[farclip] saved", len(PANELS), "panels")
