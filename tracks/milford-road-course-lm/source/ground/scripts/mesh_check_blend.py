"""Ledger 0092: a loop.blend's TERRAIN mesh census (faces by side count, duplicate faces, zero-area faces, edges with more
than two faces). blender -b <loop.blend> --python mesh_check_blend.py"""
import collections

import bmesh
import bpy
me = bpy.data.objects["TERRAIN"].data
print("verts", len(me.vertices), "edges", len(me.edges), "faces", len(me.polygons))
sides = collections.Counter(len(p.vertices) for p in me.polygons)
print("sides", dict(sides))
keys = collections.Counter(tuple(sorted(p.vertices)) for p in me.polygons)
print("duplicate faces", sum(c - 1 for c in keys.values() if c > 1))
area0 = sum(1 for p in me.polygons if p.area < 1e-6)
print("zero-area faces", area0)
bm = bmesh.new(); bm.from_mesh(me)
nm = sum(1 for e in bm.edges if len(e.link_faces) > 2)
print("edges with >2 faces", nm, "boundary edges", sum(1 for e in bm.edges if len(e.link_faces) == 1))
