"""Seat the terrain under every road at facet-level precision — the verge finer than the road.

Kevin (2026-10-09): "grass cutting through the road ... side street intersections, lots of hovering."
Measured on the built mesh: the Del Cerro hilltop loop had 28 grass-over-road and 37 road-floats up
to 2.58 m; the assembler conforms the 40→20 m terrain GRID NODES to the roads, but a 20 m facet
between nodes cannot follow a steep, curved side street — at a crest it cuts through the deck, in a
dip the road floats over it (docs/PRO-KN5-CONSTRUCTION.md: pro terrain density is a gradient anchored
to the road, the verge finer than the road).

This pass, after build_loop_blend and BEFORE the island author (the island deck lives in TERRAIN):
  1. subdivides every TERRAIN face within (half-width + BAND_M) of any road centreline (edge cuts=2
     → ~7 m facets), mainline and connectors alike;
  2. sets every TERRAIN vertex within the pavement + sidewalk width to road_y − CLEAR_M (never above
     the deck, never more than a sidewalk grade below it), and blends vertices in the outer band from
     that height back to their own height over the band.

Runs INSIDE Blender:

    blender --background --python tools/seat_terrain_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

BAND_M = 8.0        # outer blend band past the sidewalk's grass lip
SIDEWALK_M = 3.1    # curb_face + sidewalk + grade band (build_loop_blend's curb_sidewalk profile)
CLEAR_M = 0.06      # terrain sits this far under the sidewalk's grass lip (road_edge − 0.10)
LIFT = 0.10


class Roads:
    def __init__(self, lines, cell=30.0):
        self.lines = lines
        self.cell = cell
        self.cells = {}
        for li, (pts, halves) in enumerate(lines):
            for i in range(len(pts) - 1):
                for p in (pts[i], pts[i + 1]):
                    self.cells.setdefault((int(p[0] // cell), int(p[2] // cell)), set()).add((li, i))

    def nearest(self, x, z):
        """(edge distance, deck height at the nearest station, half-width) or None"""
        best = None
        cx, cz = int(x // self.cell), int(z // self.cell)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for (li, i) in self.cells.get((cx + dx, cz + dz), ()):
                    pts, halves = self.lines[li]
                    ax, ay, az = pts[i]
                    bx, by, bz = pts[i + 1]
                    ddx, ddz = bx - ax, bz - az
                    L2 = ddx * ddx + ddz * ddz
                    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * ddx + (z - az) * ddz) / L2))
                    d = math.hypot(x - (ax + t * ddx), z - (az + t * ddz))
                    half = halves[i] * (1 - t) + halves[min(i + 1, len(halves) - 1)] * t
                    if best is None or d - half < best[0]:
                        best = (d - half, ay + (by - ay) * t + LIFT, half)
        return best


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    lines = [([tuple(p) for p in local["points_xyz_m"]], [w / 2.0 for w in local["widths_m"]])]
    cp = data / "connectors.local.json"
    if cp.exists():
        for c in json.loads(cp.read_text(encoding="utf-8")).get("connectors", []):
            lines.append(([tuple(p) for p in c["points_xyz_m"]], [w / 2.0 for w in c["widths_m"]]))
    roads = Roads(lines)

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    ob = bpy.data.objects.get("TERRAIN")
    if ob is None:
        raise SystemExit("[seat] no TERRAIN object")
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    # Blender (x, y, z) = local (x, z_north, y_up)
    reach = SIDEWALK_M + BAND_M
    near_faces = []
    for f in bm.faces:
        cx = sum(v.co.x for v in f.verts) / len(f.verts)
        cz = sum(v.co.y for v in f.verts) / len(f.verts)
        r = roads.nearest(cx, cz)
        if r is not None and r[0] < reach + 12.0:
            near_faces.append(f)
    edges = {e for f in near_faces for e in f.edges}
    before = len(bm.verts)
    bmesh.ops.subdivide_edges(bm, edges=list(edges), cuts=2, use_grid_fill=True)
    bm.verts.ensure_lookup_table()
    moved = 0
    for v in bm.verts:
        r = roads.nearest(v.co.x, v.co.y)
        if r is None:
            continue
        off, deck, half = r
        if off > reach:
            continue
        target = deck - LIFT - CLEAR_M        # the grass lip height: road edge − 0.10 − 0.06
        if off <= SIDEWALK_M:
            # under the pavement/sidewalk: pinned just below the lip, never above the deck
            v.co.z = min(v.co.z, target) if v.co.z > target else target
            moved += 1
        else:
            t = (off - SIDEWALK_M) / BAND_M     # 0 at the lip → 1 at the outer band edge
            goal = target * (1 - t) + v.co.z * t
            # only pull the terrain DOWN when it would stand over the verge, never push it up hard
            if v.co.z > goal:
                v.co.z = goal
                moved += 1
            elif target - v.co.z > 2.5 * (1 - t):
                v.co.z = goal                   # a deep dip under the verge: lift to the blend
                moved += 1
    bm.to_mesh(me)
    bm.free()
    me.update()
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[seat] TERRAIN: {len(near_faces)} faces near roads subdivided ({before} -> {len(me.vertices)} verts); "
          f"{moved} verts seated to the verge; saved loop.blend")


main()
