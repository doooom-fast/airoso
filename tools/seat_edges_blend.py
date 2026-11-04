"""Finer ground along the lane edges of a BANKED stretch, so engine-july's contact shelf cannot chord over the low edge.

Ledger 0078 (the Sand Creek pilot on Lake Murray v4's engine). engine-july's prep (build_kn5_loop._conform_and_reseat)
pins every 1GRASS vertex under the pavement to the deck - 0.02 and holds the first 3 m past the edge FLAT at the edge's
own height - 0.02, splitting terrain edges near the road down to 4.5 m and no further. On a flat road that is exact. On
the low side of a banked road the lane keeps falling to its edge while the shelf beyond it is flat, so a grass triangle
with one vertex inside the lane (on the banked plane) and one on the shelf is a chord that stands over the lane near the
edge: tan(bank) x a b / (a + b) for vertices a inside and b outside, 3.7 cm at Sand Creek's 4.9 % camber on 1.5 m legs
against the 2 cm clearance (5 "ground on top" samples at s 2,561-2,602, 4.25-5.1 m right). Splitting the terrain's edges
to <= MAX_EDGE_M within BAND_M of each lane edge keeps every such chord under 1 cm.

Only where the line is banked (route.crossfall_file, keyed as build_loop_blend.crossfall_bank keys it, + PAD_M either
side): a flat road gains nothing and keeps its vertex count. No vertex moves (subdivision interpolates on the faces it
splits); the prep's pin and shelf then place the new vertices. A track without route.crossfall_file is left untouched.

    blender --background --python-exit-code 1 --python tools/seat_edges_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

MAX_EDGE_M = 0.6     # [invented] chord legs this short keep tan(5 %) x a b / (a + b) under 1 cm, half the prep's clearance
BAND_M = 1.5         # [invented] either side of each lane edge line: the legs of every chord that crosses it
PAD_M = 10.0         # [invented] past each end of the banked run, where the bank rolls in
ROUNDS = 8


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    proj = Path(argv[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    rel = (cfg.get("route") or {}).get("crossfall_file")
    if not rel:
        print("[seat-edges] no route.crossfall_file: nothing banked, nothing to do")
        return
    loc = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    P, W = loc["points_xyz_m"], loc["widths_m"]
    cf = json.loads((proj / rel).read_text(encoding="utf-8"))
    banked = [tuple(p) for p, b in zip(cf["points_xz"], cf["bank_rad"]) if abs(b) > 1e-6]
    # the lane-edge segments of every line station within PAD_M of a banked point
    near = set()
    for i, p in enumerate(P):
        if any((p[0] - bx) ** 2 + (p[2] - bz) ** 2 <= (PAD_M + 3.0) ** 2 for bx, bz in banked):
            near.add(i)
    segs = []
    for i in sorted(near):
        if i + 1 >= len(P):
            continue
        rows = []
        for j in (i, i + 1):
            a, b = P[max(0, j - 1)], P[min(len(P) - 1, j + 1)]
            tx, tz = b[0] - a[0], b[2] - a[2]
            L = math.hypot(tx, tz) or 1.0
            lx, lz = -tz / L, tx / L
            h = W[j] / 2.0
            rows.append(((P[j][0] + lx * h, P[j][2] + lz * h), (P[j][0] - lx * h, P[j][2] - lz * h)))
        segs.append((rows[0][0], rows[1][0]))
        segs.append((rows[0][1], rows[1][1]))
    if not segs:
        print("[seat-edges] crossfall file names no banked point on the line")
        return
    B = 4.0
    grid = {}
    for k, ((ax, az), (bx, bz)) in enumerate(segs):
        for gx in range(int(min(ax, bx) // B) - 1, int(max(ax, bx) // B) + 2):
            for gz in range(int(min(az, bz) // B) - 1, int(max(az, bz) // B) + 2):
                grid.setdefault((gx, gz), []).append(k)

    def d_edge(x, z):
        best = 1e18
        for k in grid.get((int(x // B), int(z // B)), ()):
            (ax, az), (bx, bz) = segs[k]
            dx, dz = bx - ax, bz - az
            L2 = dx * dx + dz * dz
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
            best = min(best, math.hypot(x - ax - t * dx, z - az - t * dz))
        return best

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    ob = bpy.data.objects.get("TERRAIN")
    if ob is None:
        raise SystemExit("[seat-edges] no TERRAIN mesh in loop.blend (run after the assembler, before the prep)")
    bm = bmesh.new(); bm.from_mesh(ob.data)
    n0 = len(bm.verts)
    n_split = 0
    for _r in range(ROUNDS):
        todo = []
        for e in bm.edges:
            if e.calc_length() <= MAX_EDGE_M:
                continue
            m = (e.verts[0].co + e.verts[1].co) / 2     # Blender x = E, y = N
            if d_edge(m.x, m.y) <= BAND_M + e.calc_length() / 2:
                todo.append(e)
        if not todo:
            break
        bmesh.ops.subdivide_edges(bm, edges=todo, cuts=1)
        n_split += len(todo)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    print(f"[seat-edges] {len(near)} banked line stations, {len(segs)} lane-edge segments: {n_split} terrain edges split "
          f"(<= {MAX_EDGE_M} m within {BAND_M} m of an edge), TERRAIN {n0} -> {len(ob.data.vertices)} verts")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))


main()
