"""Every object in a .blend as numbers two builds can be compared by (ledger 0078, the PC's apples-to-apples check).

Per object: type, parent, world matrix (rounded to 1e-6), material slots, and for a mesh the vertex / face counts with
an md5 of the vertex positions (the float32s Blender stores, in index order), of the face vertex lists, and of every UV
layer. Nothing is judged here; tools/draft_equiv.py compares two digests (and the two projects' data files).

    blender --background <file.blend> --python tools/blend_digest.py -- --json <out.json>
"""
from __future__ import annotations

import hashlib
import json
import sys
from array import array

import bpy


def _md5_floats(values):
    return hashlib.md5(array("f", values).tobytes()).hexdigest()


def digest():
    out = {}
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        rec = {"type": ob.type, "parent": ob.parent.name if ob.parent else None,
               "matrix": [round(x, 6) + 0.0 for row in ob.matrix_world for x in row],
               "materials": [s.material.name if s.material else None for s in ob.material_slots]}
        if ob.type == "MESH":
            me = ob.data
            co = [0.0] * (3 * len(me.vertices))
            me.vertices.foreach_get("co", co)
            fv = hashlib.md5()
            for p in me.polygons:
                fv.update(array("i", p.vertices).tobytes())
            rec.update(verts=len(me.vertices), faces=len(me.polygons), co_md5=_md5_floats(co), faces_md5=fv.hexdigest())
            uvs = {}
            for uv in me.uv_layers:
                buf = [0.0] * (2 * len(uv.data))
                uv.data.foreach_get("uv", buf)
                uvs[uv.name] = _md5_floats(buf)
            rec["uv_md5"] = uvs
        out[ob.name] = rec
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) != 2 or argv[0] != "--json":
        raise SystemExit("usage: blender --background <file.blend> --python tools/blend_digest.py -- --json <out.json>")
    d = digest()
    with open(argv[1], "w", encoding="utf-8") as f:
        json.dump({"blend": bpy.data.filepath, "objects": d}, f, indent=1, sort_keys=True)
    meshes = [r for r in d.values() if r["type"] == "MESH"]
    print(f"[digest] {len(d)} objects ({len(meshes)} meshes, {sum(r['verts'] for r in meshes)} vertices) -> {argv[1]}")


main()
