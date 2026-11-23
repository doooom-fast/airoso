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
Opt-in route.seat_edges_grade_pct (ledger 0083, Del Mar): the line's points steeper than that grade are seated too, as a
bank of atan(grade) would be (tools/seat_edges_grade.py); absent = as before.
Opt-in route.seat_edges_section (ledger 0102, Milford's GM turn, a measured bowl: route.densify.section): every face UNDER
the road on the section's stretch is cut by the road's own fold under it, so no grass chord stands over a column line
(tools/seat_edges_section.py: the rule); self-checked, exit 1 and loop.blend not saved when a face still would; absent =
as before.

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
CHORD_M = 0.04       # [invented] tan(bank) x leg / 4 <= 1 cm: half the prep's 0.02 m clearance
PREP_EDGE_M = 4.5    # engine-july's own corridor split (build_kn5_loop.CORRIDOR_EDGE_M): no finer cut needed past this
BANK_REACH_M = 15.0  # [invented] the measured bank a face answers for: the steepest within this of it
SKIRT_M = 60.0       # a face with an edge longer than this is the terrain skirt, not ground beside a lane
MAX_CUTS = 16        # [invented] cuts per edge at most (a 10 m cell -> 0.6 m)


def _road_bvh():
    """ROAD + CURB as one BVH, world frame (Blender XY = the line's X, Z)"""
    from mathutils.bvhtree import BVHTree
    verts, polys = [], []
    for name in ("ROAD", "CURB"):
        o = bpy.data.objects.get(name)
        if o is None or o.type != "MESH":
            continue
        mw, base = o.matrix_world, len(verts)
        verts.extend(mw @ v.co for v in o.data.vertices)
        polys.extend([base + k for k in p.vertices] for p in o.data.polygons)
    if not polys:
        raise SystemExit("[seat-edges] route.seat_edges_section: no ROAD / CURB mesh in loop.blend")
    return BVHTree.FromPolygons(verts, polys)


def section_pass(bm, P, W, sec_s, ses):
    """route.seat_edges_section (ledger 0102; the rule: tools/seat_edges_section.py): every TERRAIN face under the road on
    the section's stretch cut by the road's own fold under it; then every such face read again, exit 1 (loop.blend not
    saved) when one would still stand over the road once the prep pins its corners at the deck - CLEAR_M"""
    from mathutils import Vector, kdtree
    idx = ses.stations(P, sec_s[0], sec_s[1])
    if not idx:
        raise SystemExit(f"[seat-edges] route.seat_edges_section: no line point on s {sec_s[0]:.1f}-{sec_s[1]:.1f}")
    kd = kdtree.KDTree(len(idx))
    for k, i in enumerate(idx):
        kd.insert((P[i][0], P[i][2], 0.0), k)
    kd.balance()
    reach = max(W[i] for i in idx) / 2.0 + 2.0
    x0 = min(P[i][0] for i in idx) - reach; x1 = max(P[i][0] for i in idx) + reach
    y0 = min(P[i][2] for i in idx) - reach; y1 = max(P[i][2] for i in idx) + reach
    bvh = _road_bvh()
    down = Vector((0.0, 0.0, -1.0))
    inner = [w for w in ses.bary() if max(w) < 1.0 - 1e-9]       # the corners are read once, as corner_road

    def road_at(x, y, zref):
        hit = bvh.ray_cast(Vector((x, y, zref + 30.0)), down, 80.0)
        return None if hit[0] is None else hit[0].z

    def excess(f):
        """the face's fold excess over the road, or None when any read misses the road (a face across the lane edge: the
        bank pass's shelf rule owns it)"""
        vs = [v.co for v in f.verts]
        if len(vs) != 3:
            return None
        c = (vs[0] + vs[1] + vs[2]) / 3.0
        if not (x0 <= c.x <= x1 and y0 <= c.y <= y1):
            return None
        _co, k, d = kd.find((c.x, c.y, 0.0))
        i = idx[k]
        if d > W[i] / 2.0 + 2.0:
            return None
        zref = P[i][1]
        corner = []
        for v in vs:
            h = road_at(v.x, v.y, zref)
            if h is None:
                return None
            corner.append(h)
        samples = []
        for w0, w1, w2 in inner:
            p = vs[0] * w0 + vs[1] * w1 + vs[2] * w2
            h = road_at(p.x, p.y, zref)
            if h is None:
                return None
            samples.append((w0, w1, w2, h))
        return ses.fold_excess(corner, samples)

    n0 = len(bm.verts)
    groups, read, worst0 = {}, 0, 0.0
    for f in bm.faces:
        e = excess(f)
        if e is None:
            continue
        read += 1
        worst0 = max(worst0, e)
        cuts = ses.cuts_for(e)
        if cuts:
            groups.setdefault(cuts, []).append(f)
    n_split = 0
    for cuts in sorted(groups, reverse=True):          # the finest first, as the bank pass
        fs = [f for f in groups[cuts] if f.is_valid]
        edges = list({e for f in fs for e in f.edges if e.is_valid})
        if edges:
            bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True)
            n_split += len(edges)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    after = [e for e in (excess(f) for f in bm.faces) if e is not None]
    over_tol = sum(1 for e in after if e > ses.FOLD_TOL_M)
    over = sum(1 for e in after if e > ses.CLEAR_M)
    worst1 = max(after) if after else 0.0
    print(f"[seat-edges] section s {sec_s[0]:.1f}-{sec_s[1]:.1f} (route.seat_edges_section): {read} faces under the road "
          f"read, fold excess max {worst0:.4f} m; cut " + (", ".join(f"{c} cuts x {len(g)}" for c, g in sorted(groups.items()))
                                                         or "none") +
          f"; {n_split} edges split, TERRAIN {n0} -> {len(bm.verts)} verts; after: {len(after)} faces, excess max "
          f"{worst1:.4f} m, {over_tol} over {ses.FOLD_TOL_M} m, {over} over the {ses.CLEAR_M} m clearance")
    if over:
        raise SystemExit(f"[seat-edges] FATAL: {over} faces under the road would still stand over it after the prep's pin "
                         f"(excess max {worst1:.4f} m > {ses.CLEAR_M} m); loop.blend not saved")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    proj = Path(argv[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    rel = (cfg.get("route") or {}).get("crossfall_file")
    grade_pct = (cfg.get("route") or {}).get("seat_edges_grade_pct")     # opt-in (ledger 0083); absent = as before
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import seat_edges_section as ses
    sec_s = ses.stretch(cfg.get("route") or {}, PAD_M)                    # opt-in (ledger 0102); absent = None
    if not rel and grade_pct is None and sec_s is None:
        print("[seat-edges] no route.crossfall_file: nothing banked, nothing to do")
        return
    loc = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    P, W = loc["points_xyz_m"], loc["widths_m"]
    cf = json.loads((proj / rel).read_text(encoding="utf-8")) if rel else {"points_xz": [], "bank_rad": []}
    if grade_pct is not None:
        # the steep stretches seated as a bank of atan(grade) would be (tools/seat_edges_grade.py)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from seat_edges_grade import grade_points
        gp = grade_points(P, float(grade_pct))
        cf = {"points_xz": list(cf["points_xz"]) + [[x, z] for x, z, _ in gp],
              "bank_rad": list(cf["bank_rad"]) + [g for _, _, g in gp]}
        print(f"[seat-edges] route.seat_edges_grade_pct {float(grade_pct):g}: {len(gp)} line points steeper, seated as banked "
              f"(steepest {100 * math.tan(max([g for _, _, g in gp] or [0.0])):.1f} %)")
    banked = [tuple(p) for p, b in zip(cf["points_xz"], cf["bank_rad"]) if abs(b) > 1e-6]
    # the bank each face must answer for: the steepest measured within BANK_REACH_M of it (a 10 m grid of the points)
    bgrid = {}
    for (bx, bz), b in zip(cf["points_xz"], cf["bank_rad"]):
        bgrid.setdefault((int(bx // 10), int(bz // 10)), []).append((bx, bz, abs(b)))

    def bank_near(x, z):
        best = 0.0
        r = int(BANK_REACH_M // 10) + 1
        for gx in range(int(x // 10) - r, int(x // 10) + r + 1):
            for gz in range(int(z // 10) - r, int(z // 10) + r + 1):
                for bx, bz, b in bgrid.get((gx, gz), ()):
                    if (bx - x) ** 2 + (bz - z) ** 2 <= BANK_REACH_M ** 2:
                        best = max(best, b)
        return best
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
    if not segs and sec_s is None:
        print("[seat-edges] crossfall file names no banked point on the line")
        return
    B = 4.0
    grid = {}
    for k, ((ax, az), (bx, bz)) in enumerate(segs):
        for gx in range(int(min(ax, bx) // B) - 1, int(max(ax, bx) // B) + 2):
            for gz in range(int(min(az, bz) // B) - 1, int(max(az, bz) // B) + 2):
                grid.setdefault((gx, gz), []).append(k)

    def d_edge(x, z, reach=0.0):
        best = 1e18
        r = int(math.ceil(reach / B)) + 1          # every bucket a segment within `reach` can sit in
        ks = set()
        for gx in range(int(x // B) - r, int(x // B) + r + 1):
            for gz in range(int(z // B) - r, int(z // B) + r + 1):
                ks.update(grid.get((gx, gz), ()))
        for k in ks:
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
    # ONE pass: every face that reaches within BAND_M of a lane edge is grid-filled with its edges cut to <= MAX_EDGE_M
    # (an iterative halving fans a long edge to the opposite vertex every round and does not converge in useful time)
    # ADAPTIVE (ledger 0078, the kn5 size): a grass chord across a banked low edge stands at most tan(bank) x t / 4 over
    # the lane for legs of t, so each face near a lane edge is cut to t = CHORD_M / tan(bank), between MAX_EDGE_M and
    # PREP_EDGE_M (what engine-july's corridor split already reaches); a face whose bank needs no more is left alone.
    groups = {}
    for f in bm.faces:
        lng = max(e.calc_length() for e in f.edges)
        if lng > SKIRT_M:
            continue                                     # the grid's far skirt (grass_terrain's 500 m apron), never near a lane
        c = f.calc_center_median()
        rad = max((v.co - c).length for v in f.verts)
        if d_edge(c.x, c.y, BAND_M + rad) > BAND_M + rad:
            continue
        tb = math.tan(bank_near(c.x, c.y))
        t = max(MAX_EDGE_M, min(PREP_EDGE_M, CHORD_M / tb)) if tb > 1e-6 else PREP_EDGE_M
        cuts = min(MAX_CUTS, math.ceil(lng / t) - 1)
        if cuts >= 1:
            groups.setdefault(cuts, []).append(f)
    n_split = 0
    for cuts in sorted(groups, reverse=True):          # the finest first; a coarser neighbour shares only edges
        fs = [f for f in groups[cuts] if f.is_valid]
        edges = list({e for f in fs for e in f.edges if e.is_valid})
        if not edges:
            continue
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True)
        n_split += len(edges)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    print(f"[seat-edges] faces cut by bank: " + ", ".join(f"{c} cuts x {len(g)}" for c, g in sorted(groups.items())))
    if sec_s is not None:
        section_pass(bm, P, W, sec_s, ses)
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    print(f"[seat-edges] {len(near)} banked line stations, {len(segs)} lane-edge segments: {n_split} terrain edges split "
          f"(<= {MAX_EDGE_M} m within {BAND_M} m of an edge), TERRAIN {n0} -> {len(ob.data.vertices)} verts")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))


main()
