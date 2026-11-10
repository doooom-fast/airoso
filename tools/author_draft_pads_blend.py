"""ENGINE-DRAFT PADS, the Blender half: build every route.draft_pads deck into loop.blend (AUTH_pads), after the underlay.

docs/JUNCTIONS.md §2.0 topology B on an engine draft (ledger 0048 P3b): the lap is both main arms, cut at two of its own
rows; one deck fills the junction between them out to the MEASURED outline in ``source/pads/<id>.json``
(tools/draft_pad_outline.py; pure geometry in tools/draft_pads.py). Per pad, in this order:

  1. THE CUT ROWS. Each cut is the ribbon's own row at the declared lap vertex: the ``1ROAD_main`` vertices collinear with
     the lap point (rule 3: the deck welds to those very vertices, seams 0.000 m).
  2. THE LAP CUT TWICE. Every lap sheet's faces between the two rows go: ``1ROAD_main``, ``1ROAD_shoulder*``,
     ``SHOULDERUND*``, ``MARKINGS*``, ``YLINE*`` (a face goes when its centroid's nearest lap vertex lies strictly between
     the cuts and it stands on the pad side of both row lines). The engine's corner pleat goes with them.
  3. THE OUTLINE AS BUILT: the measured ring with its run along each cut line replaced by that cut's row vertices (the
     asphalt's own crossing points either side kept), so the boundary IS the weld.
  4. THE DECK: the outline + interior points every DECK_STEP_M (JUNCTIONS rule 6: never coarser than the arm), triangulated
     inside the outline (mathutils.geometry.delaunay_2d_cdt, the outline as the constraint); heights = the measured ground
     (the pad file's deck grid) + the seams' own departure from it, inverse-distance blended (draft_pads.seam_blend), so the
     row vertices are exact and the inside follows the lidar. One object ``1ROAD_pad_<id>`` with 1ROAD_main's material.
  5. THE GROUND UNDER IT: every ``1GRASS*`` vertex inside the outline is held GROUND_UNDER_M under the deck there (and a
     the ground within EDGE_BAND_M outside never stands above the deck edge; the ground stays one sheet), so no ground
     pokes through and none hangs far below.

Then ``data/pads.built.json`` (per pad: rows, seam residuals, faces removed per sheet, deck vertices / faces, the outline
as built) and every pad's footprint into ``pavement_exemptions.json`` (the road-inventory gate's polygon for its
``mouth_<id>`` entry, measured). Idempotent: AUTH_pads is rebuilt from scratch every run; the underlay rebuilt GEN_*.
Self-checks (exit 1, loop.blend not saved): a row not found, a seam vertex off its row, a deck vertex left without a
height, a deck face with its normal pointing down.

    blender -b --python tools/author_draft_pads_blend.py -- <project>
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))
from tools import draft_pads as dp  # noqa: E402

COLLECTION = "AUTH_pads"
LAP_SHEETS = ("1ROAD_MAIN", "1ROAD_SHOULDER", "SHOULDERUND", "MARKINGS", "YLINE")
GROUND_PREFIXES = ("1GRASS",)
DECK_STEP_M = 1.1            # [invented] interior points: the Lariat's arms are 1.72 m rows, rule 6 allows up to ~1.6x denser
EDGE_CLEAR_M = 0.45          # [invented] no interior point closer than this to the outline (no sliver triangles)
ROW_COLLINEAR_M = 0.03       # a ribbon row vertex lies on the row line through the lap point within this
GROUND_UNDER_M = 0.04        # [invented] the ground under the deck: under kn5_ground_check's 0.05 m gap, never above it
EDGE_BAND_M = 2.5            # [invented] outside the outline, the ground this close is held under the deck's edge
                             # (0.17.2 run d: 1 m left ground on top where the cut shoulder used to run, 4-5.6 m out)
GROUND_EDGE_M = 1.4          # [invented] ground edges under a deck are split until shorter (the corridor grid is 1.11 m)
EXEMPT_MARGIN_M = 0.15       # the exemption polygon stands this far outside the deck's outline (its edge triangles)
NEAR_LAP_M = 30.0            # a face farther than this from every lap vertex is not a lap sheet's


def _log(msg):
    print(f"[pads] {msg}")


def _lap(proj: Path):
    loc = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    return loc, [(p[0], p[2]) for p in loc["points_xyz_m"]]


class LapIndex:
    """nearest lap vertex to a plan point (a 10 m cell hash)"""
    CELL = 10.0

    def __init__(self, P):
        self.P, self.h = P, {}
        for i, (x, y) in enumerate(P):
            self.h.setdefault((int(x // self.CELL), int(y // self.CELL)), []).append(i)

    def nearest(self, x, y, reach=NEAR_LAP_M):
        cx, cy = int(x // self.CELL), int(y // self.CELL)
        r = int(math.ceil(reach / self.CELL))
        best, bi = reach * reach, None
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                for i in self.h.get((cx + dx, cy + dy), ()):
                    d = (self.P[i][0] - x) ** 2 + (self.P[i][1] - y) ** 2
                    if d < best:
                        best, bi = d, i
        return bi


def find_row(main_obj, p, half_hint):
    """the ribbon row through lap point p: 1ROAD_main's vertices collinear with p on both sides of it, ordered along the
    row; of every such line (each nearby vertex tried as its direction), the one whose ends sit closest to +-half_hint
    (at a tight corner a neighbouring row's inner vertex can be nearer p than the row's own); (verts, dir)"""
    mw = main_obj.matrix_world
    cand = []
    for v in main_obj.data.vertices:
        w = mw @ v.co
        d = math.hypot(w.x - p[0], w.y - p[1])
        if 0.3 <= d <= half_hint + 3.0:
            cand.append((w.x, w.y, w.z))
    best, bkey = None, None
    for fx, fy, _ in cand:
        ux, uy = fx - p[0], fy - p[1]
        L = math.hypot(ux, uy)
        ux, uy = ux / L, uy / L
        on = sorted((((x - p[0]) * ux + (y - p[1]) * uy), x, y, z) for x, y, z in cand
                    if abs(-(x - p[0]) * uy + (y - p[1]) * ux) <= ROW_COLLINEAR_M)
        if len(on) < 2 or not (on[0][0] < -0.5 and on[-1][0] > 0.5):
            continue
        key = abs(on[-1][0] - half_hint) + abs(-on[0][0] - half_hint)
        if bkey is None or key < bkey:
            best, bkey = ([(x, y, z) for _, x, y, z in on], (ux, uy)), key
    return best if best else (None, None)


def row_cut(row, node_en, reach=dp.CUT_HALF_M):
    """the ribbon row's own line as a cut: through its two end vertices, kept side the node's, drawn +-reach"""
    (ax, ay), (bx, by) = (row[0][0], row[0][1]), (row[-1][0], row[-1][1])
    c = dp.sealed_cut(((ax, ay), (bx, by)), node_en)
    L = math.hypot(bx - ax, by - ay) or 1.0
    ux, uy = (bx - ax) / L, (by - ay) / L
    mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
    c["a"], c["b"] = (mx - ux * reach, my - uy * reach), (mx + ux * reach, my + uy * reach)
    return c


def _project(c, q):
    s_ = dp.side(c, *q)
    return (q[0] - s_ * c["n"][0], q[1] - s_ * c["n"][1])


def splice_rows(ring, cuts_rows):
    """the measured ring with each cut's run along its MEASURED line replaced by the ribbon's ROW: the asphalt's two
    crossings projected onto the row's own line, the row's vertices between them, and any outline point left on the
    lap's side of the row line near it dropped (on a curve the two lines differ by a few degrees: that wedge was
    0.17.2's sliver / hole at every seam)"""
    out = list(ring)
    for c, cr, row in cuts_rows:
        on = [i for i, q in enumerate(out) if abs(dp.side(c, *q)) <= 0.05
              and dp.segment_band(c["a"], c["b"], q[0], q[1], 0.5)]
        if not on:
            raise SystemExit(f"[pads] cut at v{c['vertex']}: the outline never runs along it (measure again)")
        on_set, runs, seen = set(on), [], set()
        for i in on:
            if i in seen:
                continue
            j = i
            while (j - 1) % len(out) in on_set and (j - 1) % len(out) not in seen and (j - 1) % len(out) != i:
                j = (j - 1) % len(out)
            run = []
            k = j
            while k in on_set and k not in seen:
                run.append(k)
                seen.add(k)
                k = (k + 1) % len(out)
            runs.append(run)
        run = max(runs, key=len)
        a, b = _project(cr, out[run[0]]), _project(cr, out[run[-1]])
        # the row's order from the outline on either side of the run (the point before it to the point after it): a
        # short run (the asphalt narrower than the ribbon: C18's 5 m ramp) cannot be trusted for the direction
        pp, pn = out[(run[0] - 1) % len(out)], out[(run[-1] + 1) % len(out)]
        ux, uy = pn[0] - pp[0], pn[1] - pp[1]
        rv = sorted(row, key=lambda v: (v[0] - pp[0]) * ux + (v[1] - pp[1]) * uy)
        if (a[0] - pp[0]) * ux + (a[1] - pp[1]) * uy > (b[0] - pp[0]) * ux + (b[1] - pp[1]) * uy:
            a, b = b, a
        # the row's own vertices always stay (they are the weld); a projected crossing within 5 cm of a row end is the
        # row end itself
        rowpts = [(v[0], v[1]) for v in rv]
        clean = list(rowpts)
        rl = math.dist(rowpts[0], rowpts[-1]) or 1e-9
        ux, uy = (rowpts[-1][0] - rowpts[0][0]) / rl, (rowpts[-1][1] - rowpts[0][1]) / rl
        ta = (a[0] - rowpts[0][0]) * ux + (a[1] - rowpts[0][1]) * uy
        tb = (b[0] - rowpts[0][0]) * ux + (b[1] - rowpts[0][1]) * uy
        # a crossing beyond the row's end (the asphalt wider than the ribbon there) stays; one INSIDE the row's span
        # (the asphalt narrower than the ribbon: C14's out-cut) is dropped, or the outline would double back along the
        # row (a zero-width spike the triangulation drops together with the row's end vertex)
        if ta < -0.05:
            clean.insert(0, a)
        if tb > rl + 0.05:
            clean.append(b)
        s_, e_ = run[0], run[-1]
        if s_ <= e_:
            out = out[:s_] + clean + out[e_ + 1:]
            new_idx = set(range(s_, s_ + len(clean)))
        else:
            out = clean + out[e_ + 1:s_]
            new_idx = set(range(len(clean)))
        out = [q for i, q in enumerate(out) if i in new_idx or not (
            dp.side(cr, *q) < -0.02 and dp.segment_band(cr["a"], cr["b"], q[0], q[1], 6.0))]
    protect = {(round(v[0], 6), round(v[1], 6)) for _, _, row in cuts_rows for v in row}
    return untie(out, protect)


def _seg_x(p1, p2, p3, p4):
    d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
    if abs(d) < 1e-12:
        return None
    t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
    u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
    if 1e-9 < t < 1 - 1e-9 and 1e-9 < u < 1 - 1e-9:
        return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))
    return None


def untie(ring, protect=frozenset(), max_rounds=200):
    """a simple polygon: wherever two non-adjacent edges cross, the smaller loop between them is cut out at the
    crossing (a spur the smoothing folded back, or the seam wedge); delaunay_2d_cdt's 'inside' on a crossed ring
    leaves holes in the deck (0.17.2: C15 at 16,565 m, C18 at 24,279 m)"""
    r = list(ring)
    for _ in range(max_rounds):
        n = len(r)
        hit = None
        for i in range(n):
            a1, a2 = r[i], r[(i + 1) % n]
            for j in range(i + 2, n):
                if (j + 1) % n == i:
                    continue
                x = _seg_x(a1, a2, r[j], r[(j + 1) % n])
                if x is not None:
                    hit = (i, j, x)
                    break
            if hit:
                break
        if not hit:
            return r
        i, j, x = hit
        loop_a = r[i + 1:j + 1]                               # cut this way round: the inside run goes
        loop_b = r[j + 1:] + r[:i + 1]                        # or the other way round
        hits_a = sum((round(q[0], 6), round(q[1], 6)) in protect for q in loop_a)
        hits_b = sum((round(q[0], 6), round(q[1], 6)) in protect for q in loop_b)
        if (hits_a, len(loop_a)) <= (hits_b, len(loop_b)):
            if hits_a:
                raise SystemExit("[pads] the outline crosses itself through a seam row: measure again")
            r = r[:i + 1] + [x] + r[j + 1:]
        else:
            if hits_b:
                raise SystemExit("[pads] the outline crosses itself through a seam row: measure again")
            r = [x] + r[i + 1:j + 1]
    raise SystemExit("[pads] the outline would not untie into a simple polygon")


def build(proj: Path) -> dict:
    import bpy
    import bmesh
    from mathutils import Vector
    from mathutils.geometry import delaunay_2d_cdt

    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    decls = dp.declarations(cfg)
    loc, P = _lap(proj)
    lapi = LapIndex(P)
    # AUTH_pads from scratch
    col = bpy.data.collections.get(COLLECTION)
    if col is None:
        col = bpy.data.collections.new(COLLECTION)
        bpy.context.scene.collection.children.link(col)
    for ob in list(col.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    if not decls:
        _log("none declared: no-op")
        return {"pads": []}
    main = bpy.data.objects.get("1ROAD_main")
    if main is None:
        raise SystemExit("[pads] no 1ROAD_main in loop.blend (an engine draft's underlay is required)")
    widths = loc.get("widths_m") or []
    sheets = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith(LAP_SHEETS)]
    grounds = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith(GROUND_PREFIXES)]
    built = []
    for d in decls:
        pid = d["id"]
        rec = json.loads((proj / "source" / "pads" / f"{pid}.json").read_text(encoding="utf-8"))
        if rec.get("cuts") != d["cuts"] or rec.get("node") != d["node"]:
            raise SystemExit(f"[pads] {pid}: source/pads/{pid}.json was measured for other cuts / node — measure again")
        # 1. the rows
        cuts_rows, seams = [], []
        for k in d["cuts"]:
            c = dp.lap_cut(loc["points_xyz_m"], k, d["node"])
            half = (widths[k] / 2.0) if k < len(widths) else 6.0
            row, _ = find_row(main, c["p"], half)
            if row is None:
                raise SystemExit(f"[pads] {pid}: no 1ROAD_main row at lap vertex {k}")
            cr = row_cut(row, P[d["node"]])
            cr["vertex"] = k
            cuts_rows.append((c, cr, row))
            for x, y, z in row:
                g = dp.deck_near(rec["deck"], x, y)
                seams.append((x, y, (z - g) if g is not None else 0.0, z))
        # 2. the lap cut twice
        cut_lines = [cr for _, cr, _ in cuts_rows]
        removed = {}
        lo_k, hi_k = d["cuts"]
        for ob in sheets:
            mw = ob.matrix_world
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            doomed = []
            for f in bm.faces:
                cw = mw @ f.calc_center_median()
                if not all(dp.side(c, cw.x, cw.y) > 0.0 for c in cut_lines):
                    continue
                k = lapi.nearest(cw.x, cw.y)
                if k is not None and lo_k <= k <= hi_k:
                    doomed.append(f)
            if doomed:
                bmesh.ops.delete(bm, geom=doomed, context="FACES")
                bm.to_mesh(ob.data)
                ob.data.update()
                removed[ob.name] = len(doomed)
            bm.free()
        # 3. the outline as built
        ring = [tuple(q) for q in rec["outline_en"]]
        ring = splice_rows(ring, cuts_rows)
        if dp.ring_area(ring) < 0:
            ring.reverse()
        # 4. the deck
        xs, ys = [q[0] for q in ring], [q[1] for q in ring]
        pts = list(ring)
        x = math.floor(min(xs))
        while x <= max(xs):
            y = math.floor(min(ys))
            while y <= max(ys):
                if dp.point_in_ring(x, y, ring) and min(math.dist((x, y), q) for q in ring) >= EDGE_CLEAR_M:
                    pts.append((x, y))
                y += DECK_STEP_M
            x += DECK_STEP_M
        n_ring = len(ring)
        edges = [(i, (i + 1) % n_ring) for i in range(n_ring)]
        out = delaunay_2d_cdt([Vector(q) for q in pts], edges, [list(range(n_ring))], 1, 1e-5)
        vco, faces = out[0], out[2]
        used = sorted({i for f in faces for i in f})            # mode 1 keeps unused inputs: no loose vertex in a deck
        remap = {old: new for new, old in enumerate(used)}
        vco = [vco[i] for i in used]
        faces = [[remap[i] for i in f] for f in faces]
        tri_area = sum(abs((vco[f[1]].x - vco[f[0]].x) * (vco[f[2]].y - vco[f[0]].y)
                           - (vco[f[2]].x - vco[f[0]].x) * (vco[f[1]].y - vco[f[0]].y)) / 2.0 for f in faces)
        ring_a = dp.ring_area(ring)
        if abs(tri_area - ring_a) > 0.002 * ring_a:
            raise SystemExit(f"[pads] {pid}: the deck covers {tri_area:.1f} m2 of a {ring_a:.1f} m2 outline (holes)")
        seam_xy = {(round(s[0], 3), round(s[1], 3)): s[3] for s in seams}
        prof = dp.seam_profile([(cr, row) for _, cr, row in cuts_rows], lambda x, y: dp.deck_near(rec["deck"], x, y))
        abs_seams = [(sv[0], sv[1], sv[3]) for sv in seams]

        def deck_z(x, y):
            g = dp.deck_near(rec["deck"], x, y)
            if g is None:                                  # no ground within reach: the seams' own heights carry it
                return dp.seam_blend(x, y, abs_seams)
            return g + dp.seam_offset(prof, x, y)
        verts3 = []
        for v in vco:
            key = (round(v.x, 3), round(v.y, 3))
            if key in seam_xy:
                verts3.append((v.x, v.y, seam_xy[key]))
                continue
            verts3.append((v.x, v.y, deck_z(v.x, v.y)))
        me = bpy.data.meshes.new(f"1ROAD_pad_{pid}")
        me.from_pydata(verts3, [], [tuple(f) for f in faces])
        me.update()
        down = sum(1 for poly in me.polygons if poly.normal.z < 0)
        if down:
            for poly in me.polygons:
                if poly.normal.z < 0:
                    poly.flip()
            me.update()
        if any(poly.normal.z < 0 for poly in me.polygons):
            raise SystemExit(f"[pads] {pid}: deck faces still point down after the flip")
        ob = bpy.data.objects.new(f"1ROAD_pad_{pid}", me)
        if main.data.materials:
            me.materials.append(main.data.materials[0])
        col.objects.link(ob)
        # the seams exact
        for sx, sy, _, sz in seams:
            if not any(abs(v[0] - sx) < 1e-3 and abs(v[1] - sy) < 1e-3 and abs(v[2] - sz) < 1e-4 for v in verts3):
                raise SystemExit(f"[pads] {pid}: seam vertex ({sx:.2f}, {sy:.2f}) is not in the deck at its row height")
        # 5. the ground under it. The ground is coarse away from the road corridor (13.3 m cells on the Lariat), so its
        # triangles under a wide junction span vertices far outside the deck (0.17.2: road over ground p95 0.37 m):
        # every ground edge in the deck's box (+ EDGE_BAND_M + 2 m) is split until it is under GROUND_EDGE_M, then every
        # ground vertex inside the outline sits GROUND_UNDER_M under the deck (raised or lowered) and within EDGE_BAND_M
        # outside it never stands above the deck's edge. The ground stays one sheet.
        lowered = raised = split = 0
        bx0, by0 = min(xs) - EDGE_BAND_M - 2.0, min(ys) - EDGE_BAND_M - 2.0
        bx1, by1 = max(xs) + EDGE_BAND_M + 2.0, max(ys) + EDGE_BAND_M + 2.0
        for ob_g in grounds:
            mw = ob_g.matrix_world
            inv = mw.inverted()
            bm = bmesh.new()
            bm.from_mesh(ob_g.data)
            touched = False
            for _ in range(6):
                long_edges = []
                for e in bm.edges:
                    w0, w1 = mw @ e.verts[0].co, mw @ e.verts[1].co
                    mx, my = (w0.x + w1.x) / 2.0, (w0.y + w1.y) / 2.0
                    L = math.hypot(w1.x - w0.x, w1.y - w0.y)
                    if L > GROUND_EDGE_M and bx0 - L / 2 <= mx <= bx1 + L / 2 and by0 - L / 2 <= my <= by1 + L / 2:
                        long_edges.append(e)
                if not long_edges:
                    break
                res = bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1, use_grid_fill=True)
                split += len(long_edges)
                bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
                touched = True
            for v in bm.verts:
                w = mw @ v.co
                if not (bx0 <= w.x <= bx1 and by0 <= w.y <= by1):
                    continue
                inside = dp.point_in_ring(w.x, w.y, ring)
                if not inside and min(math.dist((w.x, w.y), q) for q in ring) > EDGE_BAND_M:
                    continue
                want = deck_z(w.x, w.y) - GROUND_UNDER_M
                if inside and abs(w.z - want) > 1e-4:
                    if w.z < want:
                        raised += 1
                    else:
                        lowered += 1
                    v.co = inv @ Vector((w.x, w.y, want))
                    touched = True
                elif not inside and w.z > want:
                    v.co = inv @ Vector((w.x, w.y, want))
                    lowered += 1
                    touched = True
            if touched:
                bm.to_mesh(ob_g.data)
                ob_g.data.update()
            bm.free()
        m_lon, m_lat = dp.meters_per_degree(loc["origin"]["lat"])
        built.append({
            "id": pid, "object": f"1ROAD_pad_{pid}", "cuts": d["cuts"], "node": d["node"],
            "rows": [[[round(v[0], 3), round(v[1], 3), round(v[2], 3)] for v in row] for _, _, row in cuts_rows],
            "seam_residual_m": {"max": round(max(abs(r) for p_ in prof for r in p_["r"]), 3),
                                "per_cut": [[round(r, 3) for r in p_["r"]] for p_ in prof],
                                "fade_m": [round(p_["fade"], 1) for p_ in prof]},
            "faces_removed": removed, "deck_vertices": len(verts3), "deck_faces": len(faces),
            "ground_lowered": lowered, "ground_raised": raised, "ground_edges_split": split,
            "outline_en": [[round(q[0], 3), round(q[1], 3)] for q in ring],
            "outline_lonlat": [[round(loc["origin"]["lon"] + q[0] / m_lon, 8), round(loc["origin"]["lat"] + q[1] / m_lat, 8)]
                               for q in ring],
            "area_m2": round(dp.ring_area(ring), 1),
            "source": rec.get("source"), "uncertainty_m": rec.get("uncertainty_m"),
            "outline_flags_paint": len(rec.get("outline_flags_paint") or []),
        })
        _log(f"{pid}: rows v{d['cuts'][0]} ({len(cuts_rows[0][2])} verts) / v{d['cuts'][1]} ({len(cuts_rows[1][2])}); "
             f"lap faces removed {sum(removed.values())} {removed}; deck {len(verts3)} v / {len(faces)} f, "
             f"{built[-1]['area_m2']} m2; seam residual max {built[-1]['seam_residual_m']['max']} m; ground {split} edges split, {lowered} "
             f"lowered, {raised} raised")
    return {"pads": built}


def exemptions(proj: Path, built: list) -> int:
    """each pad's footprint into pavement_exemptions.json's mouth_<id> entry (measured); returns how many were written"""
    p = proj / "pavement_exemptions.json"
    if not p.exists() or not built:
        return 0
    d = json.loads(p.read_text(encoding="utf-8"))
    n = 0
    for b in built:
        eid = f"mouth_{b['id'].lower()}"
        e = next((x for x in d.get("exemptions") or [] if x.get("id") == eid), None)
        if e is None:
            e = {"id": eid, "object": f"AUTH_mouth_{b['id']}", "match": "footprint"}
            d.setdefault("exemptions", []).append(e)
        e.pop("polygon_lonlat", None)
        e["polygon_xz"] = dp.offset_ring([tuple(q) for q in b["outline_en"]], EXEMPT_MARGIN_M)
        e["status"] = (f"measured: tools/author_draft_pads_blend.py from source/pads/{b['id']}.json "
                       f"({(b.get('source') or {}).get('kind')}, outline +-{(b.get('uncertainty_m') or {}).get('outline')} m)")
        n += 1
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    return n


def main():
    import bpy
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if len(argv) != 1:
        raise SystemExit("usage: blender -b --python tools/author_draft_pads_blend.py -- <project>")
    proj = Path(argv[0]).resolve()
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    if not dp.declarations(cfg):
        _log("none declared: no-op (loop.blend untouched)")
        return
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    res = build(proj)
    res["written"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (proj / "data" / "pads.built.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    n = exemptions(proj, res["pads"])
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    _log(f"{len(res['pads'])} pad(s) built into {COLLECTION}; {n} exemption polygon(s) written; loop.blend saved")


if __name__ == "__main__":
    main()
