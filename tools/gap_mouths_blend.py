"""Gap the mainline's curb+sidewalk strip across every connector mouth — the other half of C2.

tools/trim_connectors.py cuts the side streets at the mainline's pavement edge and records each
mouth in data/mouths.json. The mainline's own `curb_sidewalk` strip still runs unbroken across
that mouth (build_loop_blend.py:658 — the sweep has no concept of other roads, ledger 0036), so
the side street butts into a raised sidewalk. This removes the strip's faces across each mouth
on the connector's side: window = connector half-width + CORNER_M on each side of the cut point.

Runs INSIDE Blender, AFTER build_loop_blend + author_median_blend, BEFORE the kn5 prep:

    blender --background --python tools/gap_mouths_blend.py -- <project-dir>

Vertex layout it relies on (ribbon.curb_sidewalk, scripts-v021/geometry/ribbon.py:139-163): the
ring strip is the FIRST 8*m verts of CURB — side +1 (left of travel) stations 0..m-1 as 4 verts
each, then side -1 — and every strip face uses verts of one station pair on one side. Later
geometry (connector strips, the median island) is appended after, so ring-face identification by
vertex index is exact. The script asserts the layout before touching anything.

Pro corner returns (curb wrapping the corner on a 3-6.5 m radius, JUNCTIONS.md R4) are the next
authored step; v1 is the gap 0036 routes.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

CORNER_M = 3.0
PROFILE_PTS = 4


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    mouths = json.loads((data / "mouths.json").read_text(encoding="utf-8"))["mouths"]
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = local["points_xyz_m"]
    m = len(pts)
    closed = abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
    if closed:
        m -= 1
    ring_verts = 2 * m * PROFILE_PTS

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    curb = bpy.data.objects.get("CURB")
    if curb is None:
        raise SystemExit("[gap-mouths] no CURB object")
    me = curb.data
    if len(me.vertices) < ring_verts:
        raise SystemExit(f"[gap-mouths] CURB has {len(me.vertices)} verts < ring {ring_verts}")
    # layout assertion: vert 0 (side +1, station 0, lane edge) must be ~half-width left of pts[0];
    # vert 4m (side -1, station 0) ~half-width right. Blender (x, y, z) = local (x, z_north, y_up).
    def _lat(vi, k):
        v = me.vertices[vi].co
        a, b = pts[max(0, k - 1)], pts[min(m - 1, k + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1e-9
        return (-(tz / L) * (v.x - pts[k][0]) + (tx / L) * (v.y - pts[k][2]))
    l0, r0 = _lat(0, 0), _lat(m * PROFILE_PTS, 0)
    if not (l0 > 0 > r0):
        raise SystemExit(f"[gap-mouths] layout assertion failed: side+1 lat {l0:.2f}, side-1 lat {r0:.2f}")

    # per-station gap windows per side
    gap = {1: set(), -1: set()}
    for mo in mouths:
        k = int(mo["main_vertex"])
        side = int(mo["side"])
        reach = mo["connector_width_m"] / 2.0 + CORNER_M
        nv = int(math.ceil(reach / 3.0))
        for q in range(k - nv, k + nv + 1):
            gap[side].add(q % m if closed else max(0, min(m - 1, q)))
    print(f"[gap-mouths] {len(mouths)} mouths -> gap windows: side+1 {len(gap[1])} stations, "
          f"side-1 {len(gap[-1])} stations")

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    doomed = []
    for f in bm.faces:
        idx = [v.index for v in f.verts]
        if max(idx) >= ring_verts:
            continue
        side = 1 if max(idx) < m * PROFILE_PTS else -1
        base = 0 if side == 1 else m * PROFILE_PTS
        stations = {((i - base) // PROFILE_PTS) for i in idx}
        if stations <= gap[side]:
            doomed.append(f)
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.to_mesh(me)
    bm.free()
    me.update()
    # also drop the MARKINGS/YLINE paint across each mouth on the mainline? No — paint is visual
    # and the mainline's lines legitimately continue through a priority junction (JUNCTIONS §2).
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[gap-mouths] deleted {len(doomed)} ring curb/sidewalk faces across {len(mouths)} mouths; saved loop.blend")


main()
