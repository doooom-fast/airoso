"""Mac stand-in for kn5_to_gate_obj: the split blends' meshes -> one gate OBJ in the engine frame.

scene (E, N, up) -> engine (E, up, N) (red_repairs_blend.py's mapping; the kn5 is z-mirrored engine and kn5_to_gate_obj
mirrors it back). Evaluated meshes, world transform, loop triangles. Diagnostic only, never shipped.

    blender --background --python blend_to_gate_obj.py -- <out.obj> <a.blend> [<b.blend> ...]
"""
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
out, blends = argv[0], argv[1:]
voff = 0
with open(out, "w", encoding="ascii", newline="\n") as f:
    f.write("# gate OBJ (Mac stand-in) from " + " + ".join(blends) + "\n")
    for bl in blends:
        bpy.ops.wm.open_mainfile(filepath=bl)
        dg = bpy.context.evaluated_depsgraph_get()
        nm = 0
        for ob in bpy.data.objects:
            if ob.type != "MESH":
                continue
            ev = ob.evaluated_get(dg)
            me = ev.to_mesh()
            me.calc_loop_triangles()
            mw = ob.matrix_world
            f.write(f"o {ob.name}\n")
            for v in me.vertices:
                w = mw @ v.co
                f.write(f"v {w.x:.4f} {w.z:.4f} {w.y:.4f}\n")
            for t in me.loop_triangles:
                a, b, c = t.vertices
                f.write(f"f {a + 1 + voff} {b + 1 + voff} {c + 1 + voff}\n")
            voff += len(me.vertices)
            ev.to_mesh_clear()
            nm += 1
        print(f"[gate-obj] {bl}: {nm} meshes, offset now {voff}")
print(f"[gate-obj] wrote {out}")
