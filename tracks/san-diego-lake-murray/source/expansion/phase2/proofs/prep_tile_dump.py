"""blender --background <prepped.blend> --python tile_dump.py -- <out.json>: every terrain tile (1GRASS* / GRASS_FAR*) of a
prepped scene, each face keyed by its corners' world positions (1e-4 m, in order from the lowest corner) -> its centre"""
import hashlib
import json
import sys

import bpy

out = sys.argv[sys.argv.index("--") + 1]
rep = {}
for ob in bpy.data.objects:
    if ob.type != "MESH" or not ob.name.upper().startswith(("1GRASS", "GRASS_FAR")):
        continue
    me = ob.data
    mw = ob.matrix_world
    co = [mw @ v.co for v in me.vertices]
    faces = {}
    for p in me.polygons:
        pts = [(round(co[i].x, 4), round(co[i].y, 4), round(co[i].z, 4)) for i in p.vertices]
        k = min(range(len(pts)), key=lambda q: pts[q])
        pts = pts[k:] + pts[:k]
        h = hashlib.md5(repr(pts).encode()).hexdigest()[:16]
        cx = sum(q[0] for q in pts) / len(pts)
        cy = sum(q[1] for q in pts) / len(pts)
        faces[h] = (round(cx, 2), round(cy, 2))
    rep[ob.name] = {"v": len(me.vertices), "f": len(me.polygons), "faces": faces}
json.dump(rep, open(out, "w"))
print("[tiles]", len(rep), "tiles", sum(r["f"] for r in rep.values()), "faces")
