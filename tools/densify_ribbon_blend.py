"""More columns where the mainline ribbon twists: the per-row column change for banked roads (ledger 0078).

The v021 assembler sweeps the road as 3 vertices a row (left, centre, right; scripts-v021 geometry/ribbon.road_ribbon),
so each half-width between two rows is ONE quad, two triangles. Where the bank changes between rows (a camber rolling
in, Nevada Nights' 10.5 % T2 bowl) or the width does, the quad is twisted: its two triangles meet in a crease along the
diagonal, a valley or a ridge of |(a + c) - (b + d)| / 2 for corners a, b on one row and d, c on the next. engine-july's
prep pins the ground to the deck - 0.02 m vertex by vertex, and a grass triangle that bridges a valley crease stands over
the lane: Nevada's T2 read 20 "ground on top" samples up to 4.4 cm over the deck, Sand Creek's camber peak on its merge
flare 1 (3 mm). airoso's build_mesh answered the same twist with ribbon columns (road_profile.ribbon_cols, Exotics T2).

This tool is that answer for the v021 ribbon, AFTER the steps that read its 3-vertices-a-row layout (the fold / mouth
weld, tools/mouth_weld.mesh_layout; the seat): every mainline half-quad whose crease exceeds CREASE_TOL_M is re-cut into
k columns, k = ceil(crease / CREASE_TOL_M) up to MAX_COLS, the new vertices ON the two row lines (each row is a straight
line across in plan and height, so a point on it is exact, nothing is invented) and the strip between the rows
re-triangulated. The crease of each column is the quad's divided by k. A row edge shared by two quads takes the larger
of their k, so the mesh stays watertight (no T-junction). Connectors are left alone. A ribbon with no crease over the
tolerance is not touched and the blend is not saved.

THE MEASURE (route.densify, opt-in per track; ledger 0078 round 5). The crease above is exact only when the two rows of a
half-quad are equally wide: where the width changes it reads the change of the half's cross-fall DROP, which a planar
trapezoid on a bank also has (Milford s 2,588: "177 mm" on a quad 3.7 mm out of plane), and it misses the warp of rows
that turn against each other on a grade (Milford's s 984-992 corner on the 15 % descent, ledger 0069: "16 mm" on quads up
to 105 mm out of plane). route.densify.measure "warp" uses the true out-of-plane distance instead (the fourth corner from
the plane of the other three) and route.densify.max_cols raises the cap; absent = the crease and MAX_COLS, as before.

Lake Murray never runs it (not in its ship.json); a ported track lists it as the draft step `densify_ribbon`.

    blender --background --python-exit-code 1 --python tools/densify_ribbon_blend.py -- <project-dir>
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

CREASE_TOL_M = 0.005   # [invented] a quarter of the prep's 0.02 m ground clearance: a column's crease under it cannot lift grass over the lane
MAX_COLS = 8           # [invented] the most columns a half-width is cut into (Nevada's T2 needs ~4 at 7.7 m half-width)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    proj = Path(argv[0])
    data = proj / "data"
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    cp = data / "connectors.local.json"
    conns = json.loads(cp.read_text(encoding="utf-8"))["connectors"] if cp.exists() else []
    main_pts = [tuple(p) for p in local["points_xyz_m"]]
    lay = mw.mesh_layout(main_pts, conns)
    dcfg = ((json.loads((proj / "track.config.json").read_text(encoding="utf-8")).get("route") or {}).get("densify") or {})
    measure = dcfg.get("measure", "crease")
    if measure not in ("crease", "warp"):
        raise SystemExit(f"[densify] FATAL: route.densify.measure {measure!r}: crease or warp")
    max_cols = int(dcfg.get("max_cols", MAX_COLS))
    rows, closed = lay["MAINLINE"]["rows"], lay["MAINLINE"]["closed"]
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    ob = bpy.data.objects.get("ROAD")
    if ob is None or len(ob.data.vertices) != lay["_road_total"]:
        raise SystemExit(f"[densify] FATAL: ROAD has {0 if ob is None else len(ob.data.vertices)} verts, the assembler's "
                         f"layout says {lay['_road_total']} — run after build_loop_blend (+ weld), before anything re-meshes ROAD")
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    BV = list(bm.verts)                 # the original vertices by index (the lookup table goes stale once one is added)

    def vi(r, lane):
        return mw.road_index(lay, "MAINLINE", r, lane)

    halves = ((0, 1), (1, 2))           # left half: lanes 0-1, right half: lanes 1-2
    pairs = [(r, (r + 1) % rows) for r in range(rows if closed else rows - 1)]

    def crease(r, s, h):
        a, b = BV[vi(r, halves[h][0])].co, BV[vi(r, halves[h][1])].co
        d, c = BV[vi(s, halves[h][0])].co, BV[vi(s, halves[h][1])].co
        if measure == "crease":
            return abs((a.z + c.z) - (b.z + d.z)) / 2.0     # Blender z = up
        n = (b - a).cross(c - a)                            # the warp: d's distance from the plane through a, b, c
        return abs((d - a).dot(n)) / (n.length or 1e-12)

    need = {}
    worst = 0.0
    for r, s in pairs:
        for h in (0, 1):
            g = crease(r, s, h)
            worst = max(worst, g)
            need[(r, h)] = min(max_cols, max(1, math.ceil(g / CREASE_TOL_M - 1e-9)))
    # a row edge takes the larger need of the two quads that share it
    k_edge = {}
    for (r, h), k in need.items():
        s = (r + 1) % rows if closed else r + 1
        for row in (r, s):
            k_edge[(row, h)] = max(k_edge.get((row, h), 1), k)
    todo = [(r, s, h) for r, s in pairs for h in (0, 1) if k_edge.get((r, h), 1) > 1 or k_edge.get((s, h), 1) > 1]
    if not todo:
        print(f"[densify] worst mainline {measure} {worst * 1000:.1f} mm <= {CREASE_TOL_M * 1000:.0f} mm: nothing to do")
        bm.free()
        return
    # the new vertices on each row edge (from lane a to lane b), shared by both quads that use the edge
    edge_pts = {}

    def row_line(row, h):
        if (row, h) in edge_pts:
            return edge_pts[(row, h)]
        a, b = BV[vi(row, halves[h][0])], BV[vi(row, halves[h][1])]
        k = k_edge.get((row, h), 1)
        line = [a]
        for j in range(1, k):
            t = j / k
            line.append(bm.verts.new(a.co.lerp(b.co, t)))
        line.append(b)
        edge_pts[(row, h)] = line
        return line

    # every half-quad's two faces, found BEFORE any vertex is added (bm.verts' lookup table goes stale on a new vertex)
    bm.normal_update()
    quad_faces = {}
    for r, s, h in todo:
        quad = {vi(r, halves[h][0]), vi(r, halves[h][1]), vi(s, halves[h][0]), vi(s, halves[h][1])}
        cand = {f for q in quad for f in BV[q].link_faces}
        olds = [f for f in cand if len(f.verts) == 3 and {v.index for v in f.verts} <= quad]
        if len(olds) != 2:
            raise SystemExit(f"[densify] FATAL: mainline rows {r}-{s} half {h}: {len(olds)} faces, expected 2 (a ROAD "
                             f"re-mesh before this step?)")
        quad_faces[(r, s, h)] = (olds, olds[0].normal.z < 0)
    kill, add = [], []
    for r, s, h in todo:
        olds, flip = quad_faces[(r, s, h)]
        kill += olds
        P, Q = row_line(r, h), row_line(s, h)
        i = j = 0
        while i < len(P) - 1 or j < len(Q) - 1:          # zip the two polylines into triangles
            if j >= len(Q) - 1 or (i < len(P) - 1 and (i + 1) / (len(P) - 1) <= (j + 1) / (len(Q) - 1)):
                tri = (P[i], P[i + 1], Q[j]); i += 1
            else:
                tri = (P[i], Q[j + 1], Q[j]); j += 1
            add.append(tri[::-1] if flip else tri)
    mat = olds[0].material_index if olds else 0
    bmesh.ops.delete(bm, geom=list(dict.fromkeys(kill)), context="FACES_ONLY")
    for tri in add:
        f = bm.faces.new(tri)
        f.material_index = mat
    bm.normal_update()
    n_new = sum(len(v) - 2 for v in edge_pts.values())
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    print(f"[densify] {len(todo)} mainline half-quads re-cut (worst {measure} {worst * 1000:.1f} mm; columns up to "
          f"{max(k_edge.values())}, {n_new} new row vertices, {len(add)} triangles for {len(kill)}); saved loop.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))


main()
