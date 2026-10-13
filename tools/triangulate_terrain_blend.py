"""Triangulate the TERRAIN (BEAUTY quads) right after the seat, before the median island joins it.

Why this exists (ledger 0046, 2026-10-11). The retired far-terrain decimation (slim_far_terrain_blend.py, a
COLLAPSE Decimate with use_collapse_triangulate) ran at this point of the ship chain and, besides collapsing the
far vertices, triangulated EVERY terrain face — including the seat's quads under and beside the roads. The kn5
prep's corridor subdivision, pin and feather then worked on those triangles, so the near-road ground every gate
was tuned on (soft-top 42, excursions 100, the mouths) is the ground of THAT triangulation. With the decimation
gone (the terrain is tiered at the source) the quads would reach the prep instead and come out triangulated the
other way after its subdivision — measured on the first tiered rehearsal: 21 more soft-top stations at the
Navajo / Jackson fold and grass 7 mm higher at the Del Cerro W mouth. The decimate's quad split is Blender's
BEAUTY rule (16,401 of the v0.17.1 near-road faces matched by both, the same faces), so this pass applies exactly
that and nothing else: no vertex moves, no vertex is added.

    blender --background --python-exit-code 1 --python tools/triangulate_terrain_blend.py -- <project-dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

import bmesh
import bpy


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    ob = bpy.data.objects.get("TERRAIN")
    if ob is None:
        raise SystemExit("[tri] no TERRAIN object")
    me = ob.data
    before_v, before_f = len(me.vertices), len(me.polygons)
    bm = bmesh.new()
    bm.from_mesh(me)
    n = sum(1 for f in bm.faces if len(f.verts) > 3)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(me)
    bm.free()
    me.update()
    if len(me.vertices) != before_v:
        raise SystemExit(f"[tri] vertex count changed {before_v} -> {len(me.vertices)}: refusing to save")
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[tri] TERRAIN: {n} quads/ngons triangulated (BEAUTY), {before_f} -> {len(me.polygons)} faces, "
          f"{before_v} verts unchanged; saved loop.blend")


main()
