"""Bespoke pads re-laid on the PREPPED ground's own triangles (ledger 0081 round 2: Nevada's 2013 concrete apron).

tools/author_bespoke_blend.py drapes each pad (PADAPRON_<k>) at the author stage on 4 m cells, PAD_LIFT_M over the ground
of that moment; engine-july's prep then re-seats the ground, and on Nevada's port the 1GRASS surface stood over the apron
at 57.1 % of 6,536 samples (median +0.046 m, p95 +0.70 m; tools/apron_seat_check.py, both on 0.1.1's visual pads and on
round 1's 1RUNOFF try). Here, on the prepped scene, each pad is rebuilt from the ground triangles under its own cells, each
cut to the cell's outline in plan (tools/pad_clip.py) and lifted PAD_LIFT_M: the pad keeps its measured outline and follows
the final ground's own planes, so no ground can stand over it.

Opt-in, config scenery.bespoke.pads_seat "ground" (tools/ship_track.sh runs this inside prep only then; Lake Murray sets
no bespoke pads). scenery.bespoke.pads_surface "1RUNOFF" (opt-in) also names each pad 1RUNOFF_apron_<k>: the RUNOFF
physics surfaces.ini already carries (paved, off-track), the same skin (texture_overrides["1RUNOFF"]).
Self-check, exit 1 and the blend not saved: a pad that keeps no ground triangle, or ground left over a rebuilt pad.

    blender --background --python-exit-code 1 --python tools/seat_pads_blend.py -- <prepped.blend> --project <proj>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pad_clip as pc  # noqa: E402

PAD_LIFT_M = 0.06     # author_bespoke_blend's own (invented, GATES-CHANGELOG round 5): the pad this far over the ground
UV_M = 8.0            # author_bespoke_blend's pad UVs: world metres / 8
HASH_M = 8.0          # the plan hash cell the ground triangles are filed in (a lookup, no effect on the result)
COPLANAR_RAD = 1e-4    # pieces of one ground plane merge back: faces this close to coplanar (radians), a tolerance, not a shape


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    blend = Path(argv[0])
    proj = Path(argv[argv.index("--project") + 1])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    bes = (cfg.get("scenery") or {}).get("bespoke") or {}
    if bes.get("pads_seat") != "ground":
        print("[seat-pads] no scenery.bespoke.pads_seat: nothing to do")
        return
    surface = bes.get("pads_surface")
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    pads = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("PADAPRON_")]
    grounds = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith("1GRASS")]
    tris = []
    for g in grounds:
        me = g.data
        me.calc_loop_triangles()
        mw = g.matrix_world
        W = [mw @ v.co for v in me.vertices]
        for t in me.loop_triangles:
            tris.append(tuple(W[i] for i in t.vertices))
    gb = BVHTree.FromPolygons([v for t in tris for v in t], [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tris))])
    bad, report = [], []
    # a plan hash of the ground triangles, so each pad cell meets only the ones near it
    grid = {}
    for n, t in enumerate(tris):
        x0, x1 = min(v.x for v in t), max(v.x for v in t)
        y0, y1 = min(v.y for v in t), max(v.y for v in t)
        for i in range(int(x0 // HASH_M), int(x1 // HASH_M) + 1):
            for j in range(int(y0 // HASH_M), int(y1 // HASH_M) + 1):
                grid.setdefault((i, j), []).append(n)
    for ob in pads:
        mw = ob.matrix_world
        P = [mw @ v.co for v in ob.data.vertices]
        verts, faces, idx = [], [], {}

        def vid(p):
            key = (round(p[0], 4), round(p[1], 4))
            if key not in idx:
                idx[key] = len(verts)
                verts.append((p[0], p[1], p[2] + PAD_LIFT_M))
            elif p[2] + PAD_LIFT_M > verts[idx[key]][2]:
                # two ground pieces meet here at different heights (a fold in the prepped ground: 1.5 mm on Nevada
                # 0.1.3's apron 11, ledger 0087): the pad takes the higher, so no ground stands over it
                k = idx[key]
                verts[k] = (verts[k][0], verts[k][1], p[2] + PAD_LIFT_M)
            return idx[key]
        for poly in ob.data.polygons:                          # the pad's own cells: its measured outline
            cell = [(P[i].x, P[i].y) for i in poly.vertices]
            x0, x1 = min(c[0] for c in cell), max(c[0] for c in cell)
            y0, y1 = min(c[1] for c in cell), max(c[1] for c in cell)
            near = {n for i in range(int(x0 // HASH_M), int(x1 // HASH_M) + 1)
                    for j in range(int(y0 // HASH_M), int(y1 // HASH_M) + 1) for n in grid.get((i, j), ())}
            for n in sorted(near):
                piece = pc.clip([tuple(v) for v in tris[n]], cell)
                if len(piece) < 3 or abs(pc.area2(piece)) < 2e-4:
                    continue
                piece = pc.ccw(piece)
                ids = [vid(p) for p in piece]
                for k in range(1, len(ids) - 1):
                    if len({ids[0], ids[k], ids[k + 1]}) == 3:
                        faces.append((ids[0], ids[k], ids[k + 1]))
        if not faces:
            bad.append(f"{ob.name}: no ground triangle in its footprint")
            continue
        me = bpy.data.meshes.new(ob.data.name + "_seated")
        me.from_pydata(verts, [], faces, shade_flat=True)
        # the cell cuts split one ground plane into many pieces: merge each plane's pieces back (coplanar only, so no
        # vertex moves and no height changes), then triangulate
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.dissolve_limit(bm, angle_limit=COPLANAR_RAD, use_dissolve_boundaries=False, verts=bm.verts[:],
                                 edges=bm.edges[:])
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(me)
        bm.free()
        verts = [tuple(v.co) for v in me.vertices]
        layer = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                x, y, _ = verts[me.loops[li].vertex_index]
                layer.data[li].uv = (x / UV_M, y / UV_M)
        for m in ob.data.materials:
            me.materials.append(m)
        me.validate(); me.update()
        old = ob.data
        ob.data = me
        bpy.data.meshes.remove(old)
        name0 = ob.name
        if surface == "1RUNOFF":
            ob.name = "1RUNOFF_apron_" + name0.split("_", 1)[1]
        # self-check: the ground under each rebuilt vertex lies PAD_LIFT_M below it (none over it)
        over = 0
        for x, y, z in verts:
            hit = gb.ray_cast(Vector((x, y, z + 0.5)), Vector((0.0, 0.0, -1.0)), 1.0)
            if hit[0] is not None and hit[0].z > z - PAD_LIFT_M + 1e-3:
                over += 1
        if over:
            bad.append(f"{ob.name}: ground over {over} of its vertices")
        if len(verts) >= 65535:
            bad.append(f"{ob.name}: {len(verts)} verts, over AC's 65,535 per mesh")
        report.append({"pad": name0, "name": ob.name, "tris": len(me.polygons), "verts": len(verts), "ground_over": over})
        print(f"[seat-pads] {name0} -> {ob.name}: {len(me.polygons)} triangles on the ground, {len(verts)} verts, ground over 0 / "
              f"{len(verts)}" if not over else f"[seat-pads] {ob.name}: ground over {over}")
    (proj / "data" / "seat_pads.json").write_text(json.dumps({"lift_m": PAD_LIFT_M, "surface": surface,
                                                               "pads": report}, indent=1), encoding="utf-8")
    if bad:
        print("[seat-pads] FATAL: " + "; ".join(bad))
        sys.exit(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print(f"[seat-pads] {len(report)} pads laid on the prepped ground ({len(tris)} ground triangles read); saved")


main()
