"""Thin the terrain far from every road so the kn5 prep's grass tiles stay under the 65,535 cap.

The prep (engine-july build_kn5_loop) seats the terrain along the mainline by splitting ~56-100k
corridor edges and then tiles 1GRASS by halving its bounding box until each tile estimates under
60,000 verts — but AC counts POSITIONS (post-UV-split), and a tile near the estimate lands over
65,535 and the prep refuses to export ("'1GRASS_0' has 67114 positions", 2026-10-09). Any extra
terrain detail near the side streets (tools/seat_terrain_blend.py) tips it over. The headroom is
far away: the grid runs 150 m past the loop's bounding box and the hills nobody drives are meshed
at the same 20 m as the verges.

This decimates every TERRAIN vertex farther than FAR_M from any road (mainline or connector) to
RATIO of its density with a Decimate modifier weighted by a vertex group (bmesh.unsubdivide was
a no-op on this topology). Run AFTER seat_terrain_blend, BEFORE author_median (the island deck
lives in TERRAIN).

    blender --background --python tools/slim_far_terrain_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy

FAR_M = 220.0
RATIO = 0.35


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [(p[0], p[2]) for p in local["points_xyz_m"]]
    cp = data / "connectors.local.json"
    if cp.exists():
        for c in json.loads(cp.read_text(encoding="utf-8")).get("connectors", []):
            pts += [(p[0], p[2]) for p in c["points_xyz_m"]]
    cell = 100.0
    cells = {}
    for (x, z) in pts:
        cells.setdefault((int(x // cell), int(z // cell)), []).append((x, z))
    reach = int(math.ceil(FAR_M / cell))

    def near_road(x, z):
        cx, cz = int(x // cell), int(z // cell)
        for dx in range(-reach, reach + 1):
            for dz in range(-reach, reach + 1):
                for (px, pz) in cells.get((cx + dx, cz + dz), ()):
                    if (px - x) ** 2 + (pz - z) ** 2 < FAR_M * FAR_M:
                        return True
        return False

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    ob = bpy.data.objects.get("TERRAIN")
    if ob is None:
        raise SystemExit("[slim] no TERRAIN object")
    me = ob.data
    before = len(me.vertices)
    vg = ob.vertex_groups.new(name="far_terrain")
    far = [v.index for v in me.vertices if not near_road(v.co.x, v.co.y)]   # Blender (x, y) = local (x, z_north)
    if far:
        vg.add(far, 1.0, "REPLACE")
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    mod = ob.modifiers.new(name="slim_far", type="DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = RATIO
    mod.vertex_group = vg.name
    mod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    ob.vertex_groups.remove(ob.vertex_groups["far_terrain"])
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[slim] TERRAIN: {len(far)} far verts (> {FAR_M:.0f} m from any road) decimated to {RATIO:.2f}: "
          f"{before} -> {len(me.vertices)} verts; saved loop.blend")


main()
