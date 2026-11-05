"""Author measured concrete traffic islands that stand on a street's built road (ledger 0079 round I; opt-in).

Kevin, 2026-11-03: "I just want real". Fork 91/92 (Sand Creek, grid_tertiary_92 into the lap) has a concrete island
between its two directions, off the street's centre and inside the lap mouth's weld. Lake Murray's median author
(tools/author_median_blend.py) cannot build it: that one makes a GRASS-topped island with shrubs, centred on the
trunk, at heights from the trunk's pre-weld points. This step builds an island where it was measured, AFTER the weld,
with its heights read off the welded road:

  track.config.json route.islands = [{
      "id": "fork_92",
      "rows": [[xa, za, xb, zb], ...],   # the outline, one row per station, end to end: edge A and edge B (local x, z)
      "rise_m": [ra, rb],                 # the island's height over the built road at edge A / edge B
  }, ...]

For each row, the road's top under each edge point is read off the built ROAD sheet (a ray down through it); the deck
point stands rise_m over it. The deck is the rows' quads (edge A to edge B, straight across), with a face down to the
road along every edge whose rise is above 0 and across both ends. One object per island, `1KERB_sidewalk_island_<id>`:
the prep keeps an AC name as it is, binds the 1KERB_SIDEWALK row (the concrete curb's texture), lays its planar UVs and
turns its faces up; physics KERB (drivable, a car can mount it). No grass, no shrubs, no barrier.

Self-check, exit 1 and loop.blend not saved: a row whose edge point has no ROAD under it; fewer than 2 rows; a deck
point below the road it was read from.

No route.islands = no-op (Lake Murray and the Lariat name none).

    blender --background --python tools/author_islands_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree

NAME = "1KERB_sidewalk_island_"


def road_bvh():
    ob = bpy.data.objects.get("ROAD")
    if ob is None:
        raise SystemExit("[islands] FATAL: no ROAD object in loop.blend")
    mw = ob.matrix_world
    me = ob.data
    verts = [mw @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    return BVHTree.FromPolygons(verts, polys)


def road_top(bvh, x, z):
    """the built ROAD's top at local (x, z): Blender (X, Y, Z) = local (x, z, y)"""
    hit = bvh.ray_cast((x, z, 1.0e4), (0.0, 0.0, -1.0), 2.0e4)
    return None if hit[0] is None else hit[0].z


def build(bvh, isl):
    rows = isl["rows"]
    ra, rb = (float(v) for v in isl["rise_m"])
    if len(rows) < 2:
        raise SystemExit(f"[islands] FATAL: {isl['id']}: fewer than 2 rows; loop.blend not saved")
    top, base = [], []
    for k, (xa, za, xb, zb) in enumerate(rows):
        ya, yb = road_top(bvh, xa, za), road_top(bvh, xb, zb)
        if ya is None or yb is None:
            raise SystemExit(f"[islands] FATAL: {isl['id']} row {k}: no ROAD under ({xa}, {za}) / ({xb}, {zb}); "
                             "loop.blend not saved")
        base += [(xa, za, ya), (xb, zb, yb)]
        top += [(xa, za, ya + ra), (xb, zb, yb + rb)]
    n = len(rows)
    verts = top + base          # top row k: 2k (A), 2k+1 (B); base: 2n + 2k, 2n + 2k + 1
    faces = []
    for k in range(n - 1):
        a0, b0, a1, b1 = 2 * k, 2 * k + 1, 2 * k + 2, 2 * k + 3
        faces.append((a0, b0, b1, a1))                                   # deck
        if ra > 0:
            faces.append((2 * n + a0, a0, a1, 2 * n + a1))               # edge A's face
        if rb > 0:
            faces.append((b0, 2 * n + b0, 2 * n + b1, b1))               # edge B's face
    for a, b in ((0, 1), (2 * n - 2, 2 * n - 1)):                         # the two ends
        if ra > 0 or rb > 0:
            faces.append((a, 2 * n + a, 2 * n + b, b))
    me = bpy.data.meshes.new(NAME + isl["id"])
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    # winding: the deck faces up, every side face outward (from the deck's centroid); the prep turns drivable faces up
    # again regardless, this keeps the side faces right
    cx = sum(v[0] for v in top) / len(top)
    cy = sum(v[1] for v in top) / len(top)
    for p in me.polygons:
        c = p.center
        out = (c.x - cx, c.y - cy)
        if abs(p.normal.z) > 0.5:
            if p.normal.z < 0:
                p.flip()
        elif p.normal.x * out[0] + p.normal.y * out[1] < 0:
            p.flip()
    me.update()
    ob = bpy.data.objects.new(NAME + isl["id"], me)
    road = bpy.data.objects["ROAD"]
    for c in road.users_collection:
        c.objects.link(ob)
    # self-check: the deck stands rise_m over the road it was read from (re-read after the build)
    worst = 0.0
    for k, (xa, za, xb, zb) in enumerate(rows):
        for (x, z), r, t in (((xa, za), ra, top[2 * k]), ((xb, zb), rb, top[2 * k + 1])):
            y = road_top(bvh, x, z)
            worst = max(worst, abs((t[2] - y) - r))
            if t[2] < y - 1e-6:
                raise SystemExit(f"[islands] FATAL: {isl['id']} row {k}: the deck under the road; loop.blend not saved")
    w = [((xb - xa) ** 2 + (zb - za) ** 2) ** 0.5 for xa, za, xb, zb in rows]
    L = sum(((rows[k][0] + rows[k][2] - rows[k - 1][0] - rows[k - 1][2]) ** 2 / 4
             + (rows[k][1] + rows[k][3] - rows[k - 1][1] - rows[k - 1][3]) ** 2 / 4) ** 0.5 for k in range(1, n))
    print(f"[islands] {ob.name}: {n} rows over {L:.1f} m, {min(w):.2f}-{max(w):.2f} m wide, rise {ra:.3f} / {rb:.3f} m "
          f"over the built road ({len(me.polygons)} faces; deck vs road read-back {worst * 1000:.1f} mm)")
    return ob


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    proj = Path(argv[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    isls = (cfg.get("route") or {}).get("islands") or []
    if not isls:
        print("[islands] no route.islands: nothing to do")
        return
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    bvh = road_bvh()
    for isl in isls:
        old = bpy.data.objects.get(NAME + isl["id"])
        if old is not None:
            bpy.data.objects.remove(old, do_unlink=True)
        build(bvh, isl)
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[islands] {len(isls)} island(s) authored; saved loop.blend")


main()
