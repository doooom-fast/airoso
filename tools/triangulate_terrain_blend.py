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

One repair (v0.18.0 integration fix round 4, the runtime lens's zero-length vertex normals at the Del Cerro mouths):
where the seat left a quad with three collinear corners (a T-vertex on its diagonal), BEAUTY splits it into a
zero-area sliver plus a triangle, and the quad across the diagonal does the same with the opposite winding — two
coincident back-to-back slivers whose normals cancel (a NaN shading normal in the kn5). Every set of faces on the same
vertices whose area is under SLIVER_M2 is removed (it covers no ground), and a vertex left with no face (the T-vertex)
goes with it; nothing else changes.

    blender --background --python-exit-code 1 --python tools/triangulate_terrain_blend.py -- <project-dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

import bmesh
import bpy

SLIVER_M2 = 0.01   # [invented] coincident faces (one vertex set, either winding) smaller than this are removed


def remove_coincident_slivers(bm):
    """delete every group of 2+ faces on one vertex set whose area is under SLIVER_M2, then the vertices left with no
    face; returns (faces removed, vertices removed)"""
    bm.verts.index_update()
    groups = {}
    for f in bm.faces:
        groups.setdefault(frozenset(v.index for v in f.verts), []).append(f)
    kill = [f for g in groups.values() if len(g) > 1 and max(f.calc_area() for f in g) < SLIVER_M2 for f in g]
    nf = len(kill)
    touched = {v for f in kill for v in f.verts}
    if kill:
        bmesh.ops.delete(bm, geom=kill, context="FACES_ONLY")
    loose = [v for v in touched if v.is_valid and not v.link_faces]
    nv = len(loose)
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    return nf, nv


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
    bm.verts.ensure_lookup_table()
    nf, nv = remove_coincident_slivers(bm)
    bm.to_mesh(me)
    bm.free()
    me.update()
    if len(me.vertices) != before_v - nv:
        raise SystemExit(f"[tri] vertex count changed {before_v} -> {len(me.vertices)} ({nv} loose removed after {nf} "
                         f"coincident slivers): refusing to save")
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[tri] TERRAIN: {n} quads/ngons triangulated (BEAUTY), {before_f} -> {len(me.polygons)} faces "
          f"({nf} coincident back-to-back slivers removed, {nv} vertices left with no face), no vertex moved; "
          f"saved loop.blend")


main()
