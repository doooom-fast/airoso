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
SECTION_MAX_COLS = 16  # [invented] the most columns route.densify.section forces on a half-width


class Section:
    """route.densify.section (opt-in; ledger 0102, Milford round 2: a real banked turn whose cross-section is not a plane):
    the product of tools/measured_surface.py section, delta = what the fit product's plane (the intake's c + u b, the
    assembler's planar row) misses, per station and lateral offset (+ = left of travel). On the declared spans (the
    product's own s) every row is cut into columns about col_m apart and each of its vertices, and every vertex of the
    named objects over it (the CURB strip, MARKINGS), moves up by delta at its offset, by full weight inside the spans and
    a smoothstep to nothing over taper_m outside them."""

    def __init__(self, proj, cfg):
        self.d = json.loads((proj / cfg["file"]).read_text(encoding="utf-8"))
        self.offs = [float(o) for o in self.d["offsets_m"]]
        self.spans = [(float(a), float(b)) for a, b in cfg["spans"]]
        self.taper = float(cfg.get("taper_m", 15.0))
        self.col_m = float(cfg.get("col_m", 1.0))
        self.objects = list(cfg.get("objects", ["CURB", "MARKINGS", "YLINE"]))
        self.reach = float(cfg.get("reach_m", 3.0))       # how far past its offsets a vertex still takes the last delta
        self.n = len(self.d["s"])
        self.grid = {}
        for i in range(self.n):
            self.grid.setdefault((int(self.d["x"][i] // 6), int(self.d["z"][i] // 6)), []).append(i)

    def nearest(self, x, y):
        bx, by = int(x // 6), int(y // 6)
        best, bi = None, None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for i in self.grid.get((bx + dx, by + dy), ()):
                    d = (self.d["x"][i] - x) ** 2 + (self.d["z"][i] - y) ** 2
                    if best is None or d < best:
                        best, bi = d, i
        return bi

    def weight(self, s):
        w = 0.0
        for a, b in self.spans:
            if a <= s <= b:
                return 1.0
            g = (a - s) if s < a else (s - b)
            if g < self.taper:
                t = 1.0 - g / self.taper
                w = max(w, t * t * (3 - 2 * t))
        return w

    def at(self, x, y):
        """(station, weight) of the station nearest to a row's centre, or (None, 0) off the product"""
        i = self.nearest(x, y)
        if i is None:
            return None, 0.0
        return i, self.weight(self.d["s"][i])

    def delta(self, i, u):
        row = self.d["delta"][i]
        pts = [(o, v) for o, v in zip(self.offs, row) if v is not None]
        if len(pts) < 2:
            return 0.0
        if u <= pts[0][0]:
            return pts[0][1] if pts[0][0] - u <= self.reach else 0.0
        if u >= pts[-1][0]:
            return pts[-1][1] if u - pts[-1][0] <= self.reach else 0.0
        for (o0, v0), (o1, v1) in zip(pts, pts[1:]):
            if o0 <= u <= o1:
                return v0 + (v1 - v0) * (u - o0) / (o1 - o0)
        return 0.0


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
    sec = Section(proj, dcfg["section"]) if dcfg.get("section") else None
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
    # route.densify.section: the rows over the product's spans (by their centre's nearest station) and their columns
    sec_row = {}
    if sec is not None:
        for r in range(rows):
            c = BV[vi(r, 1)].co
            i, w = sec.at(c.x, c.y)
            if i is not None and w > 0.0:
                sec_row[r] = (i, w)
        for r, s in pairs:
            if r in sec_row or s in sec_row:
                for h in (0, 1):
                    half = max((BV[vi(q, halves[h][0])].co - BV[vi(q, halves[h][1])].co).length for q in (r, s))
                    need[(r, h)] = max(need[(r, h)], min(SECTION_MAX_COLS, max(1, math.ceil(half / sec.col_m))))
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
    # route.densify.section: every vertex of a section row (its two half lines) up by delta at its lateral offset
    sec_rep = None
    row_frames = []
    if sec_row:
        moved, dmax = 0, 0.0
        for r, (i, w) in sorted(sec_row.items()):
            c = BV[vi(r, 1)].co.copy()
            a_, b_ = BV[vi((r - 1) % rows if closed else max(r - 1, 0), 1)].co, BV[vi((r + 1) % rows if closed else min(r + 1, rows - 1), 1)].co
            tx, ty = b_.x - a_.x, b_.y - a_.y
            L_ = math.hypot(tx, ty) or 1.0
            nx_, ny_ = -ty / L_, tx / L_                    # the left normal in plan (Blender x east, y north)
            row_frames.append((c, nx_, ny_, i, w, tx / L_, ty / L_))
            seen = set()
            for h in (0, 1):
                line = edge_pts.get((r, h)) or [BV[vi(r, halves[h][0])], BV[vi(r, halves[h][1])]]
                for v in line:
                    if v in seen:
                        continue
                    seen.add(v)
                    u = (v.co.x - c.x) * nx_ + (v.co.y - c.y) * ny_
                    dz = w * sec.delta(i, u)
                    v.co.z += dz
                    moved += 1
                    dmax = max(dmax, abs(dz))
        sec_rep = {"rows": len(sec_row), "road_vertices": moved, "largest_m": round(dmax, 3)}
    bm.normal_update()
    n_new = sum(len(v) - 2 for v in edge_pts.values())
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    if row_frames:
        # the objects laid over the road (the strip, the paint): each vertex by its nearest section row's frame
        from mathutils.kdtree import KDTree
        kd = KDTree(len(row_frames))
        for k, (c, *_r) in enumerate(row_frames):
            kd.insert((c.x, c.y, 0.0), k)
        kd.balance()
        for name in sec.objects:
            o2 = bpy.data.objects.get(name)
            if o2 is None or o2.type != "MESH":
                continue
            n2 = 0
            for v in o2.data.vertices:
                co, k, dist = kd.find((v.co.x, v.co.y, 0.0))
                if k is None or dist > 15.0:
                    continue
                c, nx_, ny_, i, w, tx_, ty_ = row_frames[k]
                if abs((v.co.x - c.x) * tx_ + (v.co.y - c.y) * ty_) > 2.0:
                    continue                                # another part of the lap passing near, not over this row
                u = (v.co.x - c.x) * nx_ + (v.co.y - c.y) * ny_
                dz = w * sec.delta(i, u)
                if dz:
                    v.co.z += dz
                    n2 += 1
            o2.data.update()
            sec_rep[name + "_vertices"] = n2
        print(f"[densify] section ({dcfg['section']['file']}): {sec_rep}")
    print(f"[densify] {len(todo)} mainline half-quads re-cut (worst {measure} {worst * 1000:.1f} mm; columns up to "
          f"{max(k_edge.values())}, {n_new} new row vertices, {len(add)} triangles for {len(kill)}); saved loop.blend")
    if sec_rep is not None:
        (data / "densify_section.json").write_text(json.dumps(sec_rep, indent=1), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))


if __name__ == "__main__":      # blender --python runs it as __main__; the tests import Section
    main()
