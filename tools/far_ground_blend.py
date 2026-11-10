"""The far ground from the lidar (ledger 0083 pass 4b; Kevin 2026-11-07: "Yes", to "Should Del Mar's far ground be built
from the lidar?"): the v021 assembler's skirt (ribbon.grass_terrain: a 500 m ramp from the 3DEP grid's border down to a
floor 5 m under the lowest ground) replaced by the REAL ground over the same reach, read off the lidar product of
tools/lidar_ground.py (data/far_ground.lidar.npy).

In TERRAIN (after the assembler, the weld, seat_edges and strip_seam; before the authored dressing stands on it):
  1. the skirt's outer vertices go (the vertices at the mesh's floor), and the skirt's faces with them;
  2. the grid's border vertices stay exactly where the assembler put them: the inner grid is not touched, so the drive is
     the drive (the 3DEP grid inside lap + 150 m stays the ground the lap was built on);
  3. a lattice on every cell_m of the grid's OWN lattice (a coarser tier, as Lake Murray's ledger-0046 tiers: Del Mar's
     grid is 5 m, the ring 10 m; each ring cell on the border takes the border's own nodes between its corners, so no
     T-junction) runs from the border out reach_m on every side, each node at
     the lidar's height less the border's residual feathered over feather_m (tools/far_ground.py: no step at the seam,
     a grade change of at most 1.5 |r| / feather_m), its faces wound and UV'd as the grid's (world-planar), its material
     the grid's.
Writes data/far_ground.report.json: the border residuals, the seam's measured grade change (the ground's grade across the
border, the grid's cell inside against the ring's outside), the feather's steepest added grade, the nodes on filled cells.

Opt-in: track.config.json terrain.far_ground {"reach_m", "feather_m", "cell_m"} and the draft step `far_ground`; absent = no-op,
loop.blend not saved. Self-check (exit 1, not saved): the skirt is not the assembler's (its floor vertices are not all
outside the grid), the border is not one vertex per lattice node, a ring cell's corner is missing.

    blender --background --python-exit-code 1 --python tools/far_ground_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import far_ground as fg  # noqa: E402


def fail(msg):
    print(f"[far-ground] FATAL: {msg}; loop.blend not saved")
    raise SystemExit(1)


def main():
    proj = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    spec = (cfg.get("terrain") or {}).get("far_ground")
    if not spec:
        print("[far-ground] no terrain.far_ground: nothing to do")
        return
    reach_m, feather_m = float(spec.get("reach_m", 500.0)), float(spec.get("feather_m", 40.0))
    cell_m = float(spec.get("cell_m", 10.0))
    data = proj / "data"
    dem = fg.Dem.load(data)
    elev0 = float(json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))["origin"]["elev_m"])
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    terr = bpy.data.objects.get("TERRAIN")
    if terr is None:
        fail("no TERRAIN in loop.blend")
    if not terr.matrix_world.is_identity:
        fail("TERRAIN carries an object transform")
    me = terr.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    n0 = len(bm.verts)
    zfloor = min(v.co.z for v in bm.verts)
    skirt = [v for v in bm.verts if v.co.z < zfloor + 1e-3]
    rest = [v for v in bm.verts if v.co.z >= zfloor + 1e-3]
    xmin, xmax = min(v.co.x for v in rest), max(v.co.x for v in rest)
    ymin, ymax = min(v.co.y for v in rest), max(v.co.y for v in rest)
    if not skirt or any(xmin + 1.0 < v.co.x < xmax - 1.0 and ymin + 1.0 < v.co.y < ymax - 1.0 for v in skirt):
        fail("the mesh's floor vertices are not the assembler's skirt (all outside the grid)")
    # the UV map (world-planar on the grid: u, v linear in x, y) and the faces' winding, read before anything moves
    uvl = bm.loops.layers.uv.active
    A, U, V = [], [], []
    up = down = 0
    for f in bm.faces:
        if any(v.co.z < zfloor + 1e-3 for v in f.verts):
            continue
        if len(A) < 4000:
            for lp in f.loops:
                A.append((lp.vert.co.x, lp.vert.co.y, 1.0))
                U.append(lp[uvl].uv.x)
                V.append(lp[uvl].uv.y)
        if f.normal.z >= 0:
            up += 1
        else:
            down += 1
    cu = np.linalg.lstsq(np.array(A), np.array(U), rcond=None)[0]
    cv = np.linalg.lstsq(np.array(A), np.array(V), rcond=None)[0]
    mat_ix = max(set(f.material_index for f in bm.faces), key=lambda m: sum(1 for f in bm.faces if f.material_index == m))
    bmesh.ops.delete(bm, geom=skirt, context="VERTS")
    bm.verts.ensure_lookup_table()
    # the grid's border: one vertex per lattice node on the bbox's edges
    tol = 0.05
    edge = [v for v in bm.verts if (abs(v.co.x - xmin) < tol or abs(v.co.x - xmax) < tol
                                    or abs(v.co.y - ymin) < tol or abs(v.co.y - ymax) < tol)]
    south = sorted(v.co.x for v in edge if abs(v.co.y - ymin) < tol)
    west = sorted(v.co.y for v in edge if abs(v.co.x - xmin) < tol)
    dx = float(np.median(np.diff(south)))
    dy = float(np.median(np.diff(west)))
    NX, NY = int(round((xmax - xmin) / dx)) + 1, int(round((ymax - ymin) / dy)) + 1
    dx, dy = (xmax - xmin) / (NX - 1), (ymax - ymin) / (NY - 1)
    border = {}
    for v in edge:
        i, j = int(round((v.co.x - xmin) / dx)), int(round((v.co.y - ymin) / dy))
        if abs(xmin + i * dx - v.co.x) > tol or abs(ymin + j * dy - v.co.y) > tol:
            continue                                   # a vertex on the edge between nodes (none on the assembler's grid)
        if (i, j) in border:
            fail(f"two border vertices at lattice node {(i, j)}")
        border[(i, j)] = v
    if len(border) != 2 * (NX + NY) - 4:
        fail(f"{len(border)} border vertices for a {NX} x {NY} grid (want {2 * (NX + NY) - 4})")
    # every vertex at a lattice node (the inward neighbours, for the seam's grade)
    onlat = {}
    for v in bm.verts:
        i, j = int(round((v.co.x - xmin) / dx)), int(round((v.co.y - ymin) / dy))
        if abs(xmin + i * dx - v.co.x) < tol and abs(ymin + j * dy - v.co.y) < tol:
            onlat[(i, j)] = v
    # the border residuals
    r = {k: dem.at(v.co.x, v.co.y) - elev0 - v.co.z for k, v in border.items()}
    ri, rj = int(round(reach_m / dx)), int(round(reach_m / dy))
    step = max(1, int(round(cell_m / dx)))
    ri, rj = int(round(ri / step)) * step, int(round(rj / step)) * step     # the nearest whole tier step: the skirt's own reach
    try:
        nodes, polys = fg.ring_plan(NX, NY, ri, rj, step)
    except ValueError as ex:
        fail(str(ex))
    new = {}
    fills = [0, 0, 0]
    for i, j in nodes:
        x, y = xmin + i * dx, ymin + j * dy
        bi, bj = fg.clamp_node(i, j, NX, NY)
        d = math.hypot(x - (xmin + bi * dx), y - (ymin + bj * dy))
        z = fg.ring_height(dem.at(x, y) - elev0, r[(bi, bj)], d, feather_m)
        new[(i, j)] = bm.verts.new((x, y, z))
        fills[dem.fill_at(x, y)] += 1
    bm.verts.ensure_lookup_table()

    def node(i, j):
        if (i, j) in new:
            return new[(i, j)]
        if (i, j) in border:
            return border[(i, j)]
        fail(f"ring cell corner {(i, j)} is neither a ring node nor a border vertex")

    flip = down > up
    newfaces = []
    for poly in polys:
        vs = [node(i, j) for i, j in poly]
        f = bm.faces.new(vs[::-1] if flip else vs)
        f.material_index = mat_ix
        newfaces.append(f)
    tri = bmesh.ops.triangulate(bm, faces=newfaces)["faces"]
    for f in tri:
        for lp in f.loops:
            p = lp.vert.co
            lp[uvl].uv = (cu[0] * p.x + cu[1] * p.y + cu[2], cv[0] * p.x + cv[1] * p.y + cv[2])
    nf = len(tri)
    # the seam measured: the grade across each border node, inside (the grid's own cell) against outside (the ring's)
    jumps, outer = [], []
    for (i, j), v in border.items():
        for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            o, n = (i + di * step, j + dj * step), (i - di, j - dj)
            if o in new and n in onlat:
                h = dx if di else dy
                g_out = (new[o].co.z - v.co.z) / (h * step)
                g_in = (v.co.z - onlat[n].co.z) / h
                jumps.append(abs(g_out - g_in))
                outer.append((round(v.co.x, 1), round(v.co.y, 1), round(g_in, 3), round(g_out, 3)))
    rv = np.array(list(r.values()))
    rep = {"_doc": "ledger 0083 pass 4b: tools/far_ground_blend.py on this build's TERRAIN (its header says how)",
           "grid": {"nx": NX, "ny": NY, "dx_m": round(dx, 4), "dy_m": round(dy, 4),
                    "bbox_xy": [round(xmin, 2), round(ymin, 2), round(xmax, 2), round(ymax, 2)]},
           "reach_m": reach_m, "feather_m": feather_m, "ring_cell_m": round(step * dx, 3), "skirt_vertices_removed": len(skirt),
           "ring_nodes": len(new), "ring_triangles": nf,
           "ring_nodes_on": {"measured": fills[0], "filled_under_cover": fills[1], "filled_off_the_tiles": fills[2]},
           "border_residual_m": {"n": len(rv), "median": round(float(np.median(rv)), 3), "p05": round(float(np.percentile(rv, 5)), 3),
                                 "p95": round(float(np.percentile(rv, 95)), 3), "max_abs": round(float(np.abs(rv).max()), 3)},
           "seam_step_m": 0.0,
           "seam_grade_change": {"n": len(jumps), "median": round(float(np.median(jumps)), 4),
                                 "p95": round(float(np.percentile(jumps, 95)), 4), "max": round(float(max(jumps)), 4)},
           "feather_added_grade_max": round(1.5 * float(np.abs(rv).max()) / feather_m, 4),
           "worst_seam": sorted(outer, key=lambda t: -abs(t[3] - t[2]))[:10]}
    bm.normal_update()
    bm.to_mesh(me)
    me.update()
    bm.free()
    (data / "far_ground.report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8", newline="\n")
    print(f"[far-ground] skirt out ({len(skirt)} vertices), {len(new)} ring nodes on the grid's {dx:.2f} x {dy:.2f} m lattice "
          f"out {reach_m:.0f} m ({fills[0]} on measured lidar, {fills[1]} under cover, {fills[2]} past the tiles); border "
          f"residual p05..p95 {rep['border_residual_m']['p05']}..{rep['border_residual_m']['p95']} m (max |{rep['border_residual_m']['max_abs']}|), "
          f"feathered over {feather_m:.0f} m; seam step 0, grade change p95 {rep['seam_grade_change']['p95']} max "
          f"{rep['seam_grade_change']['max']}; TERRAIN {n0} -> {len(me.vertices)} verts; saved loop.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))


main()
