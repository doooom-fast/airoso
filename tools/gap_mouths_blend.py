"""Gap the HOST road's curb+sidewalk strip across every connector mouth — the other half of C2.

tools/trim_connectors.py cuts side streets at the pavement edge of the road they join (the
mainline or a divided trunk) and records each mouth in data/mouths.json. The host's own
`curb_sidewalk` strip still runs unbroken across that mouth (the sweep has no concept of other
roads, ledger 0036), so the side street butts into a raised sidewalk. This removes the strip's
faces across each mouth on the connector's side: window = connector half-width + CORNER_M.

Runs INSIDE Blender, AFTER build_loop_blend + author_median_blend, BEFORE the kn5 prep:

    blender --background --python tools/gap_mouths_blend.py -- <project-dir>

CURB vertex layout (ribbon.curb_sidewalk, scripts-v021/geometry/ribbon.py:139-163, and the
assembler's append order build_loop_blend.py:658/677): the ring strip first — side +1 (left of
travel) stations 0..m-1 as 4 verts each, then side -1 — then one such block per connector IN
connectors.local.json ORDER (m = n-1 when the polyline is closed), then whatever author_median
joined. Every strip face uses verts of one station pair on one side, so host-face identification by
vertex index is exact. The layout is asserted on the ring before anything is touched.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

CORNER_M = 3.0
P = 4


def _closed(pts):
    return abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    mouths = json.loads((data / "mouths.json").read_text(encoding="utf-8"))["mouths"]
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]

    # host blocks: name -> (block_start, m, closed, pts)
    blocks = {}
    main_pts = local["points_xyz_m"]
    m0 = len(main_pts) - 1 if _closed(main_pts) else len(main_pts)
    blocks["MAINLINE"] = (0, m0, _closed(main_pts), main_pts)
    start = 2 * m0 * P
    for c in conns:
        pts = c["points_xyz_m"]
        mc = len(pts) - 1 if _closed(pts) else len(pts)
        blocks[c["name"]] = (start, mc, _closed(pts), pts)
        start += 2 * mc * P

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    curb = bpy.data.objects.get("CURB")
    if curb is None:
        raise SystemExit("[gap-mouths] no CURB object")
    me = curb.data
    if len(me.vertices) < start:
        raise SystemExit(f"[gap-mouths] CURB has {len(me.vertices)} verts < expected blocks {start}")

    def _lat(vi, pts, k):
        v = me.vertices[vi].co
        a, b = pts[max(0, k - 1)], pts[min(len(pts) - 1, k + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1e-9
        return (-(tz / L) * (v.x - pts[k][0]) + (tx / L) * (v.y - pts[k][2]))
    l0, r0 = _lat(0, main_pts, 0), _lat(m0 * P, main_pts, 0)
    if not (l0 > 0 > r0):
        raise SystemExit(f"[gap-mouths] ring layout assertion failed: side+1 lat {l0:.2f}, side-1 lat {r0:.2f}")

    # gap windows per (host, side)
    gaps = {}
    for mo in mouths:
        host = mo["host"]
        if host not in blocks:
            print(f"[gap-mouths] WARNING: mouth host '{host}' not in the CURB block table — skipped")
            continue
        _, mh, closed, _ = blocks[host]
        k = int(mo["host_vertex"])
        nv = int(math.ceil((mo["connector_width_m"] / 2.0 + CORNER_M) / 3.0))
        s = gaps.setdefault((host, int(mo["side"])), set())
        for q in range(k - nv, k + nv + 1):
            s.add(q % mh if closed else max(0, min(mh - 1, q)))
    print(f"[gap-mouths] {len(mouths)} mouths on {sorted({h for h, _ in gaps})}")

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    doomed = []
    for f in bm.faces:
        idx = [v.index for v in f.verts]
        lo, hi = min(idx), max(idx)
        for (host, side), stations in gaps.items():
            bstart, mh, _, _ = blocks[host]
            side_base = bstart + (0 if side == 1 else mh * P)
            side_end = side_base + mh * P
            if lo >= side_base and hi < side_end:
                st = {((i - side_base) // P) for i in idx}
                if st <= stations:
                    doomed.append(f)
                    break
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.to_mesh(me)
    bm.free()
    me.update()
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[gap-mouths] deleted {len(doomed)} host curb/sidewalk faces across {len(mouths)} mouths; saved loop.blend")


main()
