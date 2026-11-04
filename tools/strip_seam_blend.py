"""A ground seam along the edge strip's outer lip, so the strip shows wherever it is built (ledger 0078 round 5).

The v021 edge strip (CURB; a circuit's `route.edge`: the asphalt edge held, then graded down to the grass meet) falls
below the lane edge towards its outer lip. engine-july's prep then seats the ground (build_kn5_loop._conform_and_reseat):
a TERRAIN vertex under a drivable sheet is clamped 0.02 m under it (anti-poke), one past the pavement goes to the 3 m
contact band at the LANE edge's height - 0.02. Wherever a ground triangle has a vertex inside the strip and one on the band
beyond it, it is a straight chord from under the strip up to lane-edge height, and it lies over the strip's lower, outer
part: at 1 m past the edge the strip was the top surface on 60.6 % of High Plains' side-stations with the ground cut to
0.6 m, and 24.4 % once the cut followed the bank (round 4; Nevada 57.2 -> 41.8 %).

This step gives the ground an edge ALONG the strip: one TERRAIN vertex per strip row, INSET_M inside the strip's outer lip
(so the prep's anti-poke finds the strip over it and clamps it under), and the consecutive ones joined by terrain edges
(bmesh connect_vert_pair cuts the faces between them). No ground triangle then spans the lip: inside it every triangle
is under the strip, outside it the band starts. Nothing else is moved; the prep places every new vertex. Opt-in: a track
lists the draft step `strip_seam` after `seat_edges`; Lake Murray never runs it.

Self-check, exit 1 and loop.blend not saved: CURB is not the assembler's layout; more than MAX_MISS_SHARE of the seam
points fall outside the terrain or fail to join.

    blender --background --python-exit-code 1 --python tools/strip_seam_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mouth_weld as mw  # noqa: E402

INSET_M = 0.05          # [invented] the seam this far inside the strip's outer lip: under the strip by construction
CELL_M = 4.0            # face lookup grid
MAX_MISS_SHARE = 0.01   # [invented] seam points that may miss (outside the terrain, a join that fails) before it refuses
JOIN_DEPTH = 3          # [invented] midpoint levels a failed join may try (ledger 0078 round 6: Sand Creek, 366 failed joins)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    proj = Path(argv[0])
    data = proj / "data"
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    cp = data / "connectors.local.json"
    conns = json.loads(cp.read_text(encoding="utf-8"))["connectors"] if cp.exists() else []
    lay = mw.mesh_layout([tuple(p) for p in local["points_xyz_m"]], conns)
    rows, closed = lay["MAINLINE"]["rows"], lay["MAINLINE"]["closed"]
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    curb, terr = bpy.data.objects.get("CURB"), bpy.data.objects.get("TERRAIN")
    if curb is None or terr is None:
        raise SystemExit("[strip-seam] FATAL: no CURB or TERRAIN in loop.blend (run after the assembler, before the prep)")
    if len(curb.data.vertices) != lay["_curb_total"]:
        raise SystemExit(f"[strip-seam] FATAL: CURB has {len(curb.data.vertices)} verts, the assembler's layout says "
                         f"{lay['_curb_total']}")
    CV = curb.data.vertices
    seams = []
    for side in (1, -1):
        pts = []
        for r in range(rows):
            o = CV[mw.curb_index(lay, "MAINLINE", r, side, 3)].co
            e = CV[mw.curb_index(lay, "MAINLINE", r, side, 0)].co
            dx, dy = e.x - o.x, e.y - o.y
            L = math.hypot(dx, dy) or 1.0
            pts.append((o.x + dx / L * INSET_M, o.y + dy / L * INSET_M))
        seams.append(pts)

    bm = bmesh.new(); bm.from_mesh(terr.data)
    n0 = len(bm.verts)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    grid = {}

    def put(f):
        xs = [v.co.x for v in f.verts]; ys = [v.co.y for v in f.verts]
        for gx in range(int(min(xs) // CELL_M), int(max(xs) // CELL_M) + 1):
            for gy in range(int(min(ys) // CELL_M), int(max(ys) // CELL_M) + 1):
                grid.setdefault((gx, gy), []).append(f)

    for f in bm.faces:
        put(f)

    def locate(x, y):
        for f in grid.get((int(x // CELL_M), int(y // CELL_M)), ()):
            if not f.is_valid or len(f.verts) != 3:
                continue
            a, b, c = (v.co for v in f.verts)
            d = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y)
            if abs(d) < 1e-12:
                continue
            w0 = ((b.y - c.y) * (x - c.x) + (c.x - b.x) * (y - c.y)) / d
            w1 = ((c.y - a.y) * (x - c.x) + (a.x - c.x) * (y - c.y)) / d
            w2 = 1.0 - w0 - w1
            if min(w0, w1, w2) >= -1e-9:
                return f, w0 * a.z + w1 * b.z + w2 * c.z
        return None, None

    miss = joined = 0
    total = 0
    for pts in seams:
        verts = []
        for x, y in pts:
            total += 1
            f, z = locate(x, y)
            if f is None:
                verts.append(None); miss += 1
                continue
            res = bmesh.ops.poke(bm, faces=[f])
            v = res["verts"][0]
            v.co.x, v.co.y, v.co.z = x, y, z
            for nf in res["faces"]:
                put(nf)
            verts.append(v)
        pairs = list(zip(verts, verts[1:])) + ([(verts[-1], verts[0])] if closed else [])

        def join(a, b, depth=0):
            """join a and b with terrain edges; where bmesh finds no cut between them (a path through a vertex, a
            sliver), seat a seam vertex at the midpoint and join the halves (up to JOIN_DEPTH levels)"""
            if any(b in e.verts for e in a.link_edges):
                return True
            try:
                res = bmesh.ops.connect_vert_pair(bm, verts=[a, b])
            except Exception:                                  # noqa: BLE001
                res = {}
            if res.get("edges"):
                for e in res["edges"]:
                    for nf in e.link_faces:
                        put(nf)
                for v in (a, b):
                    for nf in v.link_faces:
                        put(nf)
                return True
            if depth >= JOIN_DEPTH:
                return False
            mx, my = (a.co.x + b.co.x) / 2.0, (a.co.y + b.co.y) / 2.0
            f, z = locate(mx, my)
            if f is None:
                return False
            res = bmesh.ops.poke(bm, faces=[f])
            m = res["verts"][0]
            m.co.x, m.co.y, m.co.z = mx, my, z
            for nf in res["faces"]:
                put(nf)
            return join(a, m, depth + 1) and join(m, b, depth + 1)

        for a, b in pairs:
            if a is None or b is None:
                continue
            if join(a, b):
                joined += 1
            else:
                miss += 1
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    if miss > MAX_MISS_SHARE * total:
        raise SystemExit(f"[strip-seam] FATAL: {miss} of {total} seam points missed the terrain or failed to join; "
                         f"loop.blend not saved")
    bm.to_mesh(terr.data); bm.free(); terr.data.update()
    print(f"[strip-seam] {total} seam points {INSET_M} m inside the strip's outer lip, {joined} joins, {miss} missed; "
          f"TERRAIN {n0} -> {len(terr.data.vertices)} verts; saved loop.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))


main()
