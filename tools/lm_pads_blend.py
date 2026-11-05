"""THE LAP'S JUNCTION PADS on Lake Murray v4's engine: the mainline arm for the pad tooling (ledger 0078 round 7).

docs/JUNCTIONS.md section 2.0 topology B where the LAP itself is both main arms: Lake Murray's tools/junction_pad.py
welds a pad onto connector pieces' end rows and cannot take a lap arm; 0.17.2's tools/author_draft_pads_blend.py took
one on the airoso engine's draft (10 severe steps, a soft top at C14's out-cut, red). This is the same pad on Lake
Murray v4's assembler, whose mainline ribbon has an exact vertex layout (tools/mouth_weld.py), with Lake Murray's
stub rule for the roads the lap does not take. Per declared pad (track.config.json lm_pads.pads, the 0.17.2
declarations; the measurement source/pads/<id>.json from tools/draft_pad_outline.py: the CO_DRCOG_2_2020 lidar
intensity edge, +-0.4 m, and its class-2 deck grid):

  1. THE CUT ROWS: the mainline ROAD row at each declared lap vertex, by index (mouth_weld.road_index: left edge, centre,
     right edge) plus every ROAD vertex densify_ribbon added on that row's line. The deck welds to those very
     vertices (rule 3, seam 0.000 m).
  2. THE LAP CUT TWICE: every ROAD / CURB / MARKINGS / YLINE face between the rows goes (centroid on the pad side of
     both row lines, nearest lap vertex between the cuts). ROAD and CURB keep their vertices (FACES_ONLY), so every
     later step that reads the assembler's layout by index (cutfill, strip_seam, split_strip) still can.
  3. THE OUTLINE AS BUILT: the measured ring with its run along each cut replaced by that cut's row (draft_pads.
     splice_rows), the ribbon's corners beside each row end kept paved (ribbon_edges), untied into a simple polygon.
     Where this port's ribbon (its ROAD rows as built) would still leave the lane off the measured asphalt, the ribbon
     is united into the measured ring first (union_ribbon, on the measurement's own grid).
  4. THE DECK: the outline + interior points every DECK_STEP_M, triangulated inside it (delaunay_2d_cdt, the outline as
     the constraint); heights = the measured deck grid + each seam's departure from it, faded in over the seam's own
     length (draft_pads.seam_profile / seam_offset): the rows exact, the inside on the lidar; the lap's own ribbon
     surface where only the ribbon paves. One object 1ROAD_pad_<id> with ROAD's material. The ground under it is split
     to GROUND_EDGE_M and held GROUND_UNDER_M under the deck (0.17.2's numbers); the prep then pins it as under any
     1ROAD.
  5. THE ROADS THE LAP DOES NOT TAKE (Kevin: "a road we are not completing gets a barrier, not a curve"; JUNCTIONS
     18(d)): wherever the measured outline runs along a mouth line (a declared sealed cut or an edge of the pad's box:
     the measurement closed the side road there), a K-rail of Kevin's 4.04 m module (tools/stub_geom, the very
     barrier Lake Murray's stubs and pads stand) on the deck, BARRIER_INSET_M inside the edge:
     1WALL_STUB_PAD_<id>_m<k>.

Then data/pads.built.json and each pad's footprint into the project's pavement_exemptions.json (mouth_<id>,
polygon_xz); the K-rails also as `stubs` (the record scripts/geometry/audit_mesh.py's D rule reads for a barrier that
stands on pavement by design). Self-checks (exit 1, loop.blend not saved): a measurement for other cuts, a seam vertex
off its row height, the deck not covering its outline, a deck face pointing down, a lap row between the cuts whose lane
is not on the deck, a barrier within the lap's lane. Opt-in: the draft step `lm_pads` (after cutfill, before
strip_seam) and lm_pads.pads declared; Lake Murray never runs it.

    blender --background --python-exit-code 1 --python tools/lm_pads_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import draft_pads as dp  # noqa: E402
import mouth_weld as mw  # noqa: E402
import race_furniture as rf  # noqa: E402
import stub_geom as sg  # noqa: E402

LAP_SHEETS = ("ROAD", "CURB", "MARKINGS", "YLINE")
KEEP_VERTS = ("ROAD", "CURB")   # read by index after this step
DECK_STEP_M = 1.1               # 0.17.2's [invented] interior spacing (the Lariat's rows are ~1.7 m apart)
EDGE_CLEAR_M = 0.45             # 0.17.2's [invented]: no interior point closer than this to the outline
ROW_ON_M = 0.03                 # a densify vertex lies on its row's line within this
NEAR_LAP_M = 30.0               # a face farther than this from every lap vertex is not the lap's
MOUTH_ON_M = 0.6                # draft_pads.ON_CUT_M: an outline point this close to a mouth line runs along it
MOUTH_MIN_M = 1.5               # [invented] a shorter run along a mouth line is a corner touching it, not a road
BARRIER_INSET_M = 0.45          # [invented] the K-rail's centre this far inside the deck edge (its base is 0.3 m half-wide)
LANE_EDGE_M = 0.3               # the lane-on-deck check samples the lap's width less this at each side
GROUND_EDGE_M = 1.4             # 0.17.2's [invented]: ground edges near a deck halved until under this
GROUND_UNDER_M = 0.04           # 0.17.2's [invented]: the ground under a deck (under kn5_ground_check's 0.05 m gap)
EDGE_BAND_M = 2.5               # 0.17.2's [invented]: outside the outline the ground this close never stands over its edge
LAP_CLEAR_M = 1.0               # [invented] an outline run along a mouth line closer than the lap's half width + this is the lap's own edge
EXEMPT_MARGIN_M = 0.15          # 0.17.2's: the exemption polygon this far outside the deck's outline
WALL_PREFIX = "1WALL_STUB_PAD_"


def _log(msg):
    print(f"[lm-pads] {msg}")


class LapIndex:
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


def row_verts(road, lay, k, name="MAINLINE"):
    """the mainline row k: its three indexed vertices and every ROAD vertex on the segment between its edges (`name`: a
    connector piece's row instead, lm_pads.arms "streets")"""
    V = road.data.vertices
    idx = [mw.road_index(lay, name, k, j) for j in (0, 1, 2)]
    L, R = V[idx[0]].co, V[idx[2]].co
    ux, uy = R.x - L.x, R.y - L.y
    span = math.hypot(ux, uy)
    ux, uy = ux / span, uy / span
    out = {i: V[i].co for i in idx}
    for v in V:
        if v.index in out:
            continue
        dx, dy = v.co.x - L.x, v.co.y - L.y
        t = dx * ux + dy * uy
        if -1e-3 <= t <= span + 1e-3 and abs(-dx * uy + dy * ux) <= ROW_ON_M and abs(v.co.z - L.z) < 5.0:
            out[v.index] = v.co
    return sorted(((c.x, c.y, c.z) for c in out.values()), key=lambda q: (q[0] - L.x) * ux + (q[1] - L.y) * uy)


def mouth_runs(ring, segs):
    """the outline's runs along each mouth line: [(segment k, [ring points])], each at least MOUTH_MIN_M long"""
    out = []
    n = len(ring)
    for k, (a, b) in enumerate(segs):
        on = [dp.segment_band(a, b, q[0], q[1], MOUTH_ON_M) for q in ring]
        if not any(on):
            continue
        start = next((i for i in range(n) if not on[i]), None)
        if start is None:
            continue
        run = []
        for j in range(1, n + 1):
            i = (start + j) % n
            if on[i]:
                run.append(ring[i])
            elif run:
                if sum(math.dist(p, q) for p, q in zip(run, run[1:])) >= MOUTH_MIN_M:
                    out.append((k, run))
                run = []
    return out


def barrier_path(a, b, ring_m=sg.BARRIER_RING_M):
    """a straight K-rail a -> b: stations every <= ring_m, Kevin's module joints (stub_geom.joint_stations), the
    stub_geom kinds"""
    L = math.dist(a, b)
    n = max(1, int(math.ceil(L / ring_m)))
    out = [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n, "p0" if i in (0, n) else "mid")
           for i in range(n + 1)]
    arcs = [L * i / n for i in range(n + 1)]
    js = sg.joint_stations(L, [0.0, L])
    ins = []
    for s in js:
        for ds, kind in ((-sg.JOINT_HALF_M, "jside"), (0.0, "joint"), (sg.JOINT_HALF_M, "jside")):
            f = (s + ds) / L
            ins.append((s + ds, (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, kind)))
    kept = [(s, p) for s, p in zip(arcs, out) if p[2] != "mid" or all(abs(s - j) > 1.5 * sg.JOINT_HALF_M for j in js)]
    return [p for _s, p in sorted(kept + ins, key=lambda t: t[0])]


def _inset(a, b, d):
    """the point d along a -> b"""
    L = math.dist(a, b) or 1.0
    return (a[0] + (b[0] - a[0]) * d / L, a[1] + (b[1] - a[1]) * d / L)


def ribbon_edges(ring, cuts_rows, edges, node, lip_rows=None):
    """THE RIBBON'S CORNERS AT A CUT. The row spans the lap's whole width; where the measured asphalt is narrower than
    the ribbon (C14's out-cut) or the row line and the measurement's cut line differ by a few degrees, the outline goes
    straight from the row's end back in to the asphalt edge and the ribbon's corner beside it is left unpaved, under
    the lane the car drives (0.17.2: the wedge, soft top 28). Here the ribbon's own edge (the ROAD's edge vertex on
    each row, as the assembler built it) is walked from each row end toward the node and every edge point outside the
    outline goes into it after that row end, until the edge is back on the asphalt. Returns (ring, points added)."""
    out = list(ring)
    added = 0
    for _c, _cr, row in cuts_rows:
        k = _cr["vertex"]
        step = 1 if node > k else -1
        for end in (row[0], row[-1]):
            side_ = 0 if math.dist(end[:2], edges[k][0]) <= math.dist(end[:2], edges[k][1]) else 1
            key = (round(end[0], 6), round(end[1], 6))
            i = next((j for j, q in enumerate(out) if (round(q[0], 6), round(q[1], 6)) == key), None)
            if i is None:
                continue
            row_keys = {(round(v[0], 6), round(v[1], 6)) for v in row}
            prv, nxt = out[i - 1], out[(i + 1) % len(out)]
            forward = (round(prv[0], 6), round(prv[1], 6)) in row_keys    # the row runs in before it: walk on after
            pts = []
            j = k + step
            while j != node:
                q = edges[j][side_]
                lane = _inset(q, edges[j][1 - side_], LANE_EDGE_M)
                pts.append(q)
                if dp.point_in_ring(q[0], q[1], out) and dp.point_in_ring(lane[0], lane[1], out):
                    break                          # the edge is back on the asphalt: this point closes the patch
                j += step
            if len(pts) == 1:
                pts = []                           # the first edge point was already on the asphalt
            if not pts:
                continue
            if lip_rows:                           # the lane's lip at the cut row itself (lm_pads.deck.lane_lip): the patch
                pts = [lip_rows[k][side_]] + pts   # starts on the row's own line, beside the strip's flat lip outside it
            if forward:
                out = out[:i + 1] + pts + out[i + 1:]
            else:
                out = out[:i] + list(reversed(pts)) + out[i:]
            added += len(pts)
    protect = {(round(v[0], 6), round(v[1], 6)) for _, _, row in cuts_rows for v in row}
    return dp.untie(out, protect), added


def arm_edges(ring, arm_rows, all_rows, lip=0.0, step=0.75):
    """THE STREET'S CORNERS AT AN ARM ROW (lm_pads.arms "streets", ledger 0079 0.2.3): ribbon_edges for a street arm.
    The street's ribbon ends at its row (trim cut it at the box edge), so its edge is walked on from each row end straight
    into the pad (the row's normal, the street's own direction) every `step` (the outline's own resample step), the lane's
    lip `lip` outside it as the lap's, until the edge point and the lane LANE_EDGE_M inside it are both on the outline;
    those points go into the outline after the row end, so the deck's corner beside the row is square, not a sliver
    (verify_pads P3 sampled a hole at four arm row ends, 0.0-0.05 m off them). Returns (ring, points added)."""
    out = list(ring)
    added = 0
    span = math.dist((min(q[0] for q in ring), min(q[1] for q in ring)), (max(q[0] for q in ring), max(q[1] for q in ring)))
    for _c, cr, row in arm_rows:
        nx, ny = cr["n"]
        C = ((row[0][0] + row[-1][0]) / 2.0, (row[0][1] + row[-1][1]) / 2.0)
        row_keys = {(round(v[0], 6), round(v[1], 6)) for v in row}
        for end in (row[0], row[-1]):
            key = (round(end[0], 6), round(end[1], 6))
            i = next((j for j, q in enumerate(out) if (round(q[0], 6), round(q[1], 6)) == key), None)
            if i is None:
                continue
            ol = math.dist(end[:2], C) or 1.0
            ox, oy = (end[0] - C[0]) / ol, (end[1] - C[1]) / ol
            prv = out[i - 1]
            forward = (round(prv[0], 6), round(prv[1], 6)) in row_keys
            pts = []
            d = step
            while d <= span:
                q = (end[0] + ox * lip + nx * d, end[1] + oy * lip + ny * d)
                lane = (q[0] - ox * (lip + LANE_EDGE_M), q[1] - oy * (lip + LANE_EDGE_M))
                pts.append(q)
                if dp.point_in_ring(q[0], q[1], out) and dp.point_in_ring(lane[0], lane[1], out):
                    break
                d += step
            if len(pts) == 1:
                pts = []
            if not pts:
                continue
            if lip > 0.0:
                pts = [(end[0] + ox * lip, end[1] + oy * lip)] + pts
            if forward:
                out = out[:i + 1] + pts + out[i + 1:]
            else:
                out = out[:i] + list(reversed(pts)) + out[i:]
            added += len(pts)
    protect = {(round(v[0], 6), round(v[1], 6)) for _, _, row in all_rows for v in row}
    return dp.untie(out, protect), added


def union_ribbon(ring0, pts3, P, edges, lo_k, hi_k, node, segs):
    """THIS PORT'S LAP ON THE MEASURED DECK. The measurement paved the lap's own ribbon between the cuts (the live
    line +- its half width: 'never clipped by a box or a seal'); this port's line is the live one with the corner fits
    of round 6, up to ~3.6 m off it at a junction node, and the assembler smooths it again (its ROAD rows are the
    ribbon as built: their edge vertices are read here). Where that ribbon leaves the measured ring, the two are
    united on the measurement's own grid (GRID_M cells, traced, smoothed SMOOTH_M along the edge, every cut and mouth
    line kept straight, resampled every STEP_M: tools/draft_pad_outline.py's numbers). Unchanged when the ribbon is
    already on it. Returns (ring, cells added)."""
    import numpy as np
    GRID_M, SMOOTH_M, STEP_M = 0.25, 1.0, 0.75
    cuts = [dp.lap_cut(pts3, k, node) for k in (lo_k, hi_k)]
    xs_r = [q[0] for q in ring0] + [e[0] for k in range(lo_k, hi_k + 1) for e in edges[k]]
    ys_r = [q[1] for q in ring0] + [e[1] for k in range(lo_k, hi_k + 1) for e in edges[k]]
    pad = 2.0
    x0, x1, y0, y1 = min(xs_r) - pad, max(xs_r) + pad, min(ys_r) - pad, max(ys_r) + pad
    xs = x0 + (np.arange(int((x1 - x0) / GRID_M)) + 0.5) * GRID_M
    ys = y1 - (np.arange(int((y1 - y0) / GRID_M)) + 0.5) * GRID_M
    gx, gy = np.meshgrid(xs, ys)
    meas = dp.in_ring_grid(ring0, gx, gy)
    rib = np.zeros_like(meas)
    for k in range(lo_k, hi_k):
        quad = [edges[k][0], edges[k + 1][0], edges[k + 1][1], edges[k][1]]
        rib |= dp.in_ring_grid(quad, gx, gy)
    for c in cuts:
        rib &= dp.half_plane_mask(c, gx, gy)
    extra = int((rib & ~meas).sum())
    if extra * GRID_M * GRID_M < 0.5:
        return ring0, 0
    region = meas | rib
    ring = dp.trace_boundary(region.tolist(), xs.tolist(), ys.tolist())
    keep_on = cuts + [dp.sealed_cut(s, P[node]) for s in segs]
    ring = dp.smooth_ring(ring, SMOOTH_M, keep_on=keep_on, pin=cuts)
    ring = dp.resample_ring(ring, STEP_M)
    for i, q in enumerate(ring):
        ring[i] = dp.snap(q, keep_on)
    return ring, extra


def union_arms(ring0, short, keep_on, pin):
    """A STREET ARM SHORT OF THE MEASURED ASPHALT (lm_pads.arms "streets", ledger 0079 0.2.3): the lidar outline need not
    reach the box edge where a street was cut (colorado_50th: grid_unclassified_10 and _76 stop 3-8 m short of it). The
    street's own ribbon between its end row and the measured ring is united into the ring, on union_ribbon's grid and
    with its numbers: per arm the quad from its end row (L, R) inward, perpendicular to the row, as far as the row's two
    edges and centre all stand inside the measured ring. `short` = [row cut, (L, R) plan]. Returns the ring."""
    import numpy as np
    GRID_M, SMOOTH_M, STEP_M = 0.25, 1.0, 0.75
    quads = []
    for cr, (L, R) in short:
        nx, ny = cr["n"]                                  # into the pad
        C = ((L[0] + R[0]) / 2.0, (L[1] + R[1]) / 2.0)
        d, reach = 0.0, None
        span = math.dist((min(q[0] for q in ring0), min(q[1] for q in ring0)),
                         (max(q[0] for q in ring0), max(q[1] for q in ring0)))
        while d <= span:
            if all(dp.point_in_ring(q[0] + nx * d, q[1] + ny * d, ring0) for q in (L, C, R)):
                reach = d
                break
            d += GRID_M
        if reach is None:
            raise SystemExit(f"[lm-pads] FATAL: an arm row at ({C[0]:.1f}, {C[1]:.1f}) never meets the measured outline")
        quads.append([L, R, (R[0] + nx * reach, R[1] + ny * reach), (L[0] + nx * reach, L[1] + ny * reach)])
    xs_r = [q[0] for q in ring0] + [v[0] for qd in quads for v in qd]
    ys_r = [q[1] for q in ring0] + [v[1] for qd in quads for v in qd]
    pad = 2.0
    x0, x1, y0, y1 = min(xs_r) - pad, max(xs_r) + pad, min(ys_r) - pad, max(ys_r) + pad
    xs = x0 + (np.arange(int((x1 - x0) / GRID_M)) + 0.5) * GRID_M
    ys = y1 - (np.arange(int((y1 - y0) / GRID_M)) + 0.5) * GRID_M
    gx, gy = np.meshgrid(xs, ys)
    region = dp.in_ring_grid(ring0, gx, gy)
    for qd, (cr, _e) in zip(quads, short):
        region |= dp.in_ring_grid(qd, gx, gy) & dp.half_plane_mask(cr, gx, gy)
    ring = dp.trace_boundary(region.tolist(), xs.tolist(), ys.tolist())
    ring = dp.smooth_ring(ring, SMOOTH_M, keep_on=keep_on, pin=pin)
    ring = dp.resample_ring(ring, STEP_M)
    for i, q in enumerate(ring):
        ring[i] = dp.snap(q, keep_on)
    return ring


def ground_under(ring, deck_z, edge_m=GROUND_EDGE_M):
    terr = bpy.data.objects.get("TERRAIN")
    if terr is None:
        return {}
    xs, ys = [q[0] for q in ring], [q[1] for q in ring]
    m = EDGE_BAND_M + 2.0
    bx0, by0, bx1, by1 = min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m
    bm = bmesh.new(); bm.from_mesh(terr.data)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    split = 0
    for _ in range(12):
        todo = []
        for e in bm.edges:
            a, b = e.verts
            mx, my = (a.co.x + b.co.x) / 2.0, (a.co.y + b.co.y) / 2.0
            L = math.hypot(b.co.x - a.co.x, b.co.y - a.co.y)
            if L > edge_m and bx0 - L / 2 <= mx <= bx1 + L / 2 and by0 - L / 2 <= my <= by1 + L / 2:
                todo.append((L, e))
        if not todo:
            break
        todo.sort(key=lambda t: -t[0])
        for _L, e in todo:
            if not e.is_valid:
                continue
            tris = [(f, next(v for v in f.verts if v not in e.verts)) for f in e.link_faces if len(f.verts) == 3]
            _ne, nv = bmesh.utils.edge_split(e, e.verts[0], 0.5)
            for f, far in tris:
                if f.is_valid and len(f.verts) == 4:
                    bmesh.utils.face_split(f, nv, far)
            split += 1
    lowered = raised = 0
    for v in bm.verts:
        x, y = v.co.x, v.co.y
        if not (bx0 <= x <= bx1 and by0 <= y <= by1):
            continue
        inside = dp.point_in_ring(x, y, ring)
        if not inside and min(math.dist((x, y), q) for q in ring) > EDGE_BAND_M:
            continue
        want = deck_z(x, y) - GROUND_UNDER_M
        if inside and abs(v.co.z - want) > 1e-4:
            raised += v.co.z < want
            lowered += v.co.z > want
            v.co.z = want
        elif not inside and v.co.z > want:
            v.co.z = want
            lowered += 1
    bm.to_mesh(terr.data); bm.free(); terr.data.update()
    return {"edges_split": split, "lowered": lowered, "raised": raised}


def build(proj, cfg, decls):
    src = proj / ((cfg.get("lm_pads") or {}).get("source") or "source/pads")
    loc = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    pts3 = loc["points_xyz_m"]
    P = [(p[0], p[2]) for p in pts3]
    W = loc.get("widths_m") or [7.0] * len(P)
    lay = mw.mesh_layout([tuple(p) for p in pts3], [])
    lapi = LapIndex(P)
    road = bpy.data.objects.get("ROAD")
    if road is None:
        raise SystemExit("[lm-pads] FATAL: no ROAD in loop.blend")
    for ob in [o for o in bpy.data.objects if o.name.startswith(("1ROAD_pad_", WALL_PREFIX))]:
        bpy.data.objects.remove(ob, do_unlink=True)
    built = []
    # THE STREET ARMS (opt-in lm_pads.arms "streets", ledger 0079 0.2.3; Kevin "authored pad junctions", "Real
    # junctions"): tools/trim_connectors.py (route.street_junctions.pad_arms) cut every street entering a built pad's box
    # at the box edge (data/pad_arms.json). Each arm's end row joins the deck exactly as a lap cut row does: spliced into
    # the outline along its box edge, a seam (its vertices pinned), its departure from the lidar faded in. The lap's faces
    # between the cuts go only within the lap's half width + its edge strip of the lap line (the streets' own faces stay).
    # Absent = the lap's two rows alone, as before (the Lariat)
    arms_mode = (cfg.get("lm_pads") or {}).get("arms")
    arm_all, lay_c, strip_w = [], None, 0.0
    if arms_mode == "streets":
        arm_all = json.loads((proj / "data" / "pad_arms.json").read_text(encoding="utf-8"))["arms"]
        conns = json.loads((proj / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
        lay_c = mw.mesh_layout([tuple(p) for p in pts3], conns)
        re_ = (cfg.get("route") or {}).get("edge") or {}
        strip_w = sum(float(re_.get(k) or 0.0) for k in ("curb_face_w", "sidewalk_w", "grade_w"))
    elif arms_mode is not None:
        raise SystemExit(f"[lm-pads] FATAL: lm_pads.arms {arms_mode!r}: only \"streets\" is known")

    def lap_lateral(x_, y_, k_):
        """plan distance from (x, y) to the lap polyline near vertex k"""
        best = math.inf
        for i in (k_ - 1, k_):
            if 0 <= i < len(P) - 1:
                (ax, ay), (bx, by) = P[i], P[i + 1]
                dx, dy = bx - ax, by - ay
                L2 = dx * dx + dy * dy or 1e-12
                t = max(0.0, min(1.0, ((x_ - ax) * dx + (y_ - ay) * dy) / L2))
                best = min(best, math.hypot(x_ - ax - dx * t, y_ - ay - dy * t))
        return best
    for d in decls:
        pid = d["id"]
        rec = json.loads((src / f"{pid}.json").read_text(encoding="utf-8"))
        if rec.get("cuts") != d["cuts"] or rec.get("node") != d["node"]:
            raise SystemExit(f"[lm-pads] FATAL: {pid}: {src.name}/{pid}.json was measured for other cuts / node")
        lo_k, hi_k = d["cuts"]
        # 0. THE DECK AS MEASURED, ITS HOLES FILLED FROM ITSELF, IN THE LAP'S DATUM (ledger 0079 round D; opt-in
        # lm_pads.deck: {"fill": "lidar", "datum_m": <the assembler's ROAD lift>}; absent = the measured grid as before, the
        # Lariat's C14 / C15 unchanged): draft_pads.deck_filled
        deck_cfg = (cfg.get("lm_pads") or {}).get("deck") or {}
        deck_rep = None
        if deck_cfg.get("fill") == "lidar":
            rec = dict(rec)
            rec["deck"], deck_rep = dp.deck_filled(rec["deck"], [tuple(q) for q in rec["outline_en"]],
                                                   float(deck_cfg.get("datum_m") or 0.0), deck_cfg.get("smooth_m"))
            _log(f"{pid}: deck {deck_rep}")
        # 1. the rows
        cuts_rows, seams = [], []
        for k in d["cuts"]:
            c = dp.lap_cut(pts3, k, d["node"])
            row = row_verts(road, lay, k)
            cr = dp.row_cut(row, P[d["node"]])
            cr["vertex"] = k
            cuts_rows.append((c, cr, row))
            seams += row
        cut_lines = [cr for _, cr, _ in cuts_rows]
        arm_rows, arm_meta = [], []
        for a in [a for a in arm_all if a["pad"] == pid]:
            if not a.get("piece") or a["piece"] not in lay_c:
                raise SystemExit(f"[lm-pads] FATAL: {pid}: arm {a['connector']} has no final piece in the mesh layout")
            r_ = 0 if a["end"] == "start" else lay_c[a["piece"]]["rows"] - 1
            row = row_verts(road, lay_c, r_, a["piece"])
            # the arm row's line drawn over the row's own span only (a lap row's reaches CUT_HALF_M): splice_rows drops
            # outline points on its far side within 6 m of that line, and a street's row line run on 30 m took the next
            # arm's row end (colorado_50th: grid_primary_15's took grid_unclassified_10's left end)
            cr = dp.row_cut(row, P[d["node"]], reach=math.dist(row[0][:2], row[-1][:2]) / 2.0)
            c = dp.sealed_cut((tuple(a["box_edge"][0]), tuple(a["box_edge"][1])), P[d["node"]])
            c["vertex"] = f"{a['piece']} ({a['end']})"
            cr["vertex"] = c["vertex"]
            arm_rows.append((c, cr, row))
            arm_meta.append({"connector": a["connector"], "piece": a["piece"], "end": a["end"], "row": r_})
            seams += row
        RV = road.data.vertices
        edges = {}
        for k in range(lo_k, hi_k + 1):
            a_, b_ = RV[mw.road_index(lay, "MAINLINE", k, 0)].co, RV[mw.road_index(lay, "MAINLINE", k, 2)].co
            edges[k] = ((a_.x, a_.y), (b_.x, b_.y))
        # THE LANE'S LIP (opt-in lm_pads.deck.lane_lip "route.edge", ledger 0079 round D): with no curb the lap's lane edge
        # stays at road height for route.edge curb_face_w + sidewalk_w past the ROAD edge (Sand Creek 0.1 + 0.2 m), and
        # drive_test's edge wheel path reads 0.25 m past the ROAD edge. Between the cuts that flat lip goes with the strip,
        # so where the measured asphalt is narrower than the lane the deck keeps the lip paved too: the edge points this
        # step walks stand the lip outside the ROAD edge. Absent = the ROAD edge, as before (the Lariat).
        lip = 0.0
        if deck_cfg.get("lane_lip") == "route.edge":
            re_ = (cfg.get("route") or {}).get("edge") or {}
            if float(re_.get("curb_h", 1.0)) == 0.0:
                lip = float(re_.get("curb_face_w") or 0.0) + float(re_.get("sidewalk_w") or 0.0)
        lip_rows = None
        edges0 = dict(edges)
        if lip > 0.0:
            def _out(p_, q_):
                L_ = math.dist(p_, q_) or 1.0
                return (p_[0] + (p_[0] - q_[0]) / L_ * lip, p_[1] + (p_[1] - q_[1]) / L_ * lip)
            edges = {k: (_out(a_, b_), _out(b_, a_)) for k, (a_, b_) in edges.items()}
            lip_rows = {k: edges[k] for k in d["cuts"]}
        # 2. the lap cut twice
        removed = {}
        ribbon_bvh = None
        for name in LAP_SHEETS:
            ob = bpy.data.objects.get(name)
            if ob is None:
                continue
            bm = bmesh.new(); bm.from_mesh(ob.data)
            doomed = []
            for f in bm.faces:
                cw = f.calc_center_median()
                if not all(dp.side(c, cw.x, cw.y) > 0.0 for c in cut_lines):
                    continue
                k = lapi.nearest(cw.x, cw.y)
                if k is not None and lo_k <= k <= hi_k:
                    if arms_mode == "streets":
                        # only the lap's own faces: ROAD / CURB by the assembler's layout (the mainline block first,
                        # densify's vertices appended past every connector block); the paint by the lateral test
                        if name in ("ROAD", "CURB"):
                            n_main = (3 if name == "ROAD" else 2 * mw.CURB_P) * lay_c["MAINLINE"]["rows"]
                            total = lay_c["_road_total" if name == "ROAD" else "_curb_total"]
                            if not all(v.index < n_main or v.index >= total for v in f.verts):
                                continue                           # a street's own face, not the lap's
                        elif lap_lateral(cw.x, cw.y, k) > W[k] / 2.0 + strip_w:
                            continue                               # a street's own paint, not the lap's
                    doomed.append(f)
            if doomed and name == "ROAD":                      # the lap's own surface, where nothing measured paves it
                rv_, rf_ = [], []
                for f in doomed:
                    rf_.append([len(rv_) + i for i in range(len(f.verts))])
                    rv_ += [tuple(v.co) for v in f.verts]
                ribbon_bvh = BVHTree.FromPolygons([Vector(q) for q in rv_], rf_)
            if doomed:
                bmesh.ops.delete(bm, geom=doomed, context="FACES_ONLY" if name in KEEP_VERTS else "FACES")
                bm.to_mesh(ob.data); ob.data.update()
                removed[name] = len(doomed)
            bm.free()
        # 3. the outline as built
        segs = [tuple(map(tuple, s)) for s in (d.get("sealed") or [])]
        box = d.get("box") or []
        segs += [(tuple(box[i - 1]), tuple(box[i])) for i in range(len(box))]
        # the measured ring first; this port's ribbon united into it only where the lap's lane is not on it
        def lane_off(ring_):
            off = []
            for k in range(lo_k + 1, hi_k):
                a_, b_ = edges0[k]                 # the lane check reads the ROAD edge, lip or not
                for t, q in (("left", _inset(a_, b_, LANE_EDGE_M)), ("mid", ((a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2)),
                             ("right", _inset(b_, a_, LANE_EDGE_M))):
                    if not dp.point_in_ring(q[0], q[1], ring_):
                        off.append((k, t))
            return off

        def as_built(ring_in):
            ring_ = dp.splice_rows(ring_in, cuts_rows + arm_rows)
            if dp.ring_area(ring_) < 0:
                ring_.reverse()
            ring_, added_ = ribbon_edges(ring_, cuts_rows, edges, d["node"], lip_rows)
            if arm_rows:
                ring_, a2_ = arm_edges(ring_, arm_rows, cuts_rows + arm_rows, lip)
                added_ += a2_
            return ring_, added_
        united = 0
        meas_ring = [tuple(q) for q in rec["outline_en"]]
        # a street arm whose box edge the measured outline never runs along: its own ribbon to the measured ring is
        # united in (union_arms), and the outline then runs along the arm's ROW line, which is its splice line
        short = []
        for ai, (c, cr, row) in enumerate(arm_rows):
            if not any(abs(dp.side(c, *q)) <= 0.05 and dp.segment_band(c["a"], c["b"], q[0], q[1], 0.5) for q in meas_ring):
                short.append(ai)
        if short:
            lap_cuts = [c for c, _, _ in cuts_rows]
            keep_on = lap_cuts + [dp.sealed_cut(s_, P[d["node"]]) for s_ in segs] + [arm_rows[ai][1] for ai in short]
            meas_ring = union_arms(meas_ring, [(arm_rows[ai][1], ((arm_rows[ai][2][0][0], arm_rows[ai][2][0][1]),
                                                                  (arm_rows[ai][2][-1][0], arm_rows[ai][2][-1][1])))
                                               for ai in short], keep_on, lap_cuts + [arm_rows[ai][1] for ai in short])
            for ai in short:
                c, cr, row = arm_rows[ai]
                arm_rows[ai] = (cr, cr, row)
                arm_meta[ai]["spliced_on"] = "row (the street's ribbon united to the measured outline)"
            _log(f"{pid}: {len(short)} arm(s) short of the measured outline, their ribbon united: "
                 f"{[arm_meta[ai]['piece'] for ai in short]}")
        ring, widened = as_built(meas_ring)
        off_deck = lane_off(ring)
        if off_deck:
            ring0, united = union_ribbon(meas_ring, pts3, P, edges, lo_k, hi_k, d["node"], segs)
            try:
                ring, widened = as_built(ring0)
            except SystemExit as ex:
                raise SystemExit(f"[lm-pads] FATAL: {pid}: {len(off_deck)} lane samples off the measured deck "
                                 f"(first {off_deck[:6]}), and with this line's ribbon united ({united * 0.0625:.1f} m2): {ex}")
            off_deck = lane_off(ring)
        if off_deck:
            raise SystemExit(f"[lm-pads] FATAL: {pid}: {len(off_deck)} lane samples between the cuts are off the deck "
                             f"even with this line's ribbon united (first {off_deck[:6]})")
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
        out = delaunay_2d_cdt([Vector(q) for q in pts], [(i, (i + 1) % n_ring) for i in range(n_ring)],
                              [list(range(n_ring))], 1, 1e-5)
        vco, faces = out[0], out[2]
        used = sorted({i for f in faces for i in f})
        remap = {old: new for new, old in enumerate(used)}
        vco = [vco[i] for i in used]
        faces = [[remap[i] for i in f] for f in faces]
        tri_area = sum(abs((vco[f[1]].x - vco[f[0]].x) * (vco[f[2]].y - vco[f[0]].y)
                           - (vco[f[2]].x - vco[f[0]].x) * (vco[f[1]].y - vco[f[0]].y)) / 2.0 for f in faces)
        ring_a = dp.ring_area(ring)
        if abs(tri_area - ring_a) > 0.002 * ring_a:
            raise SystemExit(f"[lm-pads] FATAL: {pid}: the deck covers {tri_area:.1f} m2 of a {ring_a:.1f} m2 outline")
        seam_xy = {(round(s[0], 3), round(s[1], 3)): s[2] for s in seams}
        prof = dp.seam_profile([(cr, row) for _, cr, row in cuts_rows], lambda x_, y_: dp.deck_near(rec["deck"], x_, y_))
        for _c, cr, row in arm_rows:
            # an arm's fade: seam_profile's own rule (as long as its departure needs at SEAM_MAX_SLOPE, from SEAM_FADE_M),
            # up to 45 % of the way to the node, as the lap's two cuts are held to 45 % of the way to each other; and never
            # onto the lap's own lane, whose seams the lap's two rows rule (round G build k2: 50th_ash's arm, 8.5 m off the
            # lane, faded over 12 m added 3 kinks to the lap at s 549-552)
            pa_ = dp.seam_profile([(cr, row)], lambda x_, y_: dp.deck_near(rec["deck"], x_, y_))[0]
            need = max(abs(r) for r in pa_["r"]) * math.pi / (2.0 * dp.SEAM_MAX_SLOPE)
            mid_ = ((row[0][0] + row[-1][0]) / 2.0, (row[0][1] + row[-1][1]) / 2.0)
            lane_d = min(math.dist(v[:2], P[k]) - W[k] / 2.0 for v in row for k in range(lo_k, hi_k + 1))
            pa_["fade"] = min(max(dp.SEAM_FADE_M, min(need, 0.45 * math.dist(mid_, P[d["node"]]))), max(lane_d, 0.5))
            pa_["lane_clear_m"] = round(lane_d, 2)
            pa_["lateral"] = True
            prof.append(pa_)
        s_off = dp.seam_offset_multi if arm_rows else dp.seam_offset

        def deck_z(x_, y_):
            """the measured deck where the lidar paves it (+ the seams' departures, faded in); the lap's own ribbon
            surface where only the ribbon does (the asphalt narrower than the lane, or this line off the measured edge);
            the nearest measured node, then the seams, beyond"""
            g = dp.deck_at(rec["deck"], x_, y_)
            if g is not None:
                return g + s_off(prof, x_, y_)
            if ribbon_bvh is not None:
                hit = ribbon_bvh.ray_cast(Vector((x_, y_, 1e4)), Vector((0.0, 0.0, -1.0)))
                if hit[0] is not None:
                    return hit[0].z
            g = dp.deck_near(rec["deck"], x_, y_)
            if g is None:
                return dp.seam_blend(x_, y_, [(s[0], s[1], s[2]) for s in seams])
            return g + s_off(prof, x_, y_)
        verts3 = []
        for v in vco:
            key = (round(v.x, 3), round(v.y, 3))
            verts3.append((v.x, v.y, seam_xy[key] if key in seam_xy else deck_z(v.x, v.y)))
        for sx, sy, sz in seams:
            if not any(abs(v[0] - sx) < 1e-3 and abs(v[1] - sy) < 1e-3 and abs(v[2] - sz) < 1e-4 for v in verts3):
                near_ring = sorted((round(math.dist((sx, sy), q), 3), round(q[0], 3), round(q[1], 3)) for q in ring)[:3]
                raise SystemExit(f"[lm-pads] FATAL: {pid}: seam vertex ({sx:.3f}, {sy:.3f}) not in the deck at its row height "
                                 f"(the outline's nearest points {near_ring})")
        me = bpy.data.meshes.new(f"1ROAD_pad_{pid}")
        me.from_pydata(verts3, [], [tuple(f) for f in faces])
        me.update()
        for poly in me.polygons:
            if poly.normal.z < 0:
                poly.flip()
        me.update()
        if any(poly.normal.z < 0 for poly in me.polygons):
            raise SystemExit(f"[lm-pads] FATAL: {pid}: deck faces still point down")
        if road.data.materials:
            me.materials.append(road.data.materials[0])
        deck_ob = bpy.data.objects.new(f"1ROAD_pad_{pid}", me)
        bpy.context.scene.collection.objects.link(deck_ob)
        # 4b. THE GROUND UNDER IT (0.17.2's numbers): the terrain's edges near the deck halved until under
        # GROUND_EDGE_M (longest first, triangles only), every ground vertex inside the outline GROUND_UNDER_M under the
        # deck, and within EDGE_BAND_M outside never above the deck's edge: no ground chord over a measured bowl
        held = ground_under(ring, deck_z, float(deck_cfg.get("ground_edge_m") or GROUND_EDGE_M))   # opt-in finer (L3b)
        # 5. the barriers across the roads the lap does not take
        bvh = BVHTree.FromPolygons([Vector(v) for v in verts3], [tuple(f) for f in faces])

        def base_of(x_, z_, ax, az):
            samples = []
            for qx, qz in sg.footprint_samples(x_, z_, ax, az):
                hit = bvh.ray_cast(Vector((qx, qz, 1e4)), Vector((0.0, 0.0, -1.0)))
                samples.append(None if hit[0] is None else hit[0].z)
            got = [s for s in samples if s is not None]
            return (min(got) if got else None), samples
        bars = []
        along_lap = 0
        # lm_pads.close_arms false (ledger 0079, Sand Creek's free roam: the side streets are joined, not closed): no K-rail
        # across a road the lap does not take; the deck stays open to the street (its weld is the junction step's).
        # Absent = true, the Lariat's barriers as before
        runs_ = mouth_runs(ring, segs) if (cfg.get("lm_pads") or {}).get("close_arms", True) else []
        for m, (k_seg, run) in enumerate(runs_):
            # a box edge the outline follows BESIDE the lap (the measurement's box clipped the lap arm's own wide
            # pavement; the lap's ribbon was kept) is not a road leaving: no barrier along the lap
            near = [lapi.nearest(*q) for q in run]
            if any(k is not None and math.dist(q, P[k]) < W[k] / 2.0 + LAP_CLEAR_M for k, q in zip(near, run)):
                along_lap += 1
                continue
            a_, b_ = segs[k_seg]
            c_ = dp.sealed_cut((a_, b_), P[d["node"]])
            ux, uy = b_[0] - a_[0], b_[1] - a_[1]
            ul = math.hypot(ux, uy) or 1.0
            ux, uy = ux / ul, uy / ul
            ts = [(q[0] - a_[0]) * ux + (q[1] - a_[1]) * uy for q in run]
            t0, t1 = min(ts) + BARRIER_INSET_M, max(ts) - BARRIER_INSET_M
            if t1 - t0 < MOUTH_MIN_M:
                continue
            nx, ny = c_["n"]
            tm = (t0 + t1) / 2.0                      # the deck's side of the mouth line (a box notch faces away)
            if not dp.point_in_ring(a_[0] + ux * tm + nx * BARRIER_INSET_M, a_[1] + uy * tm + ny * BARRIER_INSET_M, ring):
                nx, ny = -nx, -ny
            pa = (a_[0] + ux * t0 + nx * BARRIER_INSET_M, a_[1] + uy * t0 + ny * BARRIER_INSET_M)
            pb = (a_[0] + ux * t1 + nx * BARRIER_INSET_M, a_[1] + uy * t1 + ny * BARRIER_INSET_M)
            for q in (pa, pb, ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)):
                k = lapi.nearest(*q)
                if k is not None:
                    lane = W[k] / 2.0 + 0.5
                    if math.dist(q, P[k]) < lane:
                        raise SystemExit(f"[lm-pads] FATAL: {pid}: a mouth barrier at ({q[0]:.1f}, {q[1]:.1f}) stands in "
                                         f"the lap's lane (v{k})")
            try:
                rings, seat = sg.barrier_rings(barrier_path(pa, pb), base_of)
            except sg.GeomError as ex:
                raise SystemExit(f"[lm-pads] FATAL: {pid} mouth {m}: {ex}")
            bv_, bf_, uvs = sg.barrier_mesh(rings)
            sharp = rf.sharp_edges(bv_, bf_)
            bv, bf = rf.to_blender(bv_, bf_)
            name = f"{WALL_PREFIX}{pid}_m{m}"
            wme = bpy.data.meshes.new(name)
            wme.from_pydata(bv, [], bf)
            wme.validate()
            uvl = wme.uv_layers.new(name="UVMap")
            for poly in wme.polygons:
                for li in poly.loop_indices:
                    uvl.data[li].uv = uvs[wme.loops[li].vertex_index]
            wme.shade_smooth()
            key = {(a, c) if a < c else (c, a) for a, c in sharp}
            wme.edges.foreach_set("use_edge_sharp", [tuple(sorted(e.vertices)) in key for e in wme.edges])
            wme.update()
            bpy.context.scene.collection.objects.link(bpy.data.objects.new(name, wme))
            bars.append({"object": name, "mouth": [list(a_), list(b_)], "from": [round(v, 3) for v in pa],
                         "to": [round(v, 3) for v in pb], "span_m": round(math.dist(pa, pb), 2), "rings": len(rings),
                         "barrier": {"object": name, "style": "krail", "half_base_m": sg.BARRIER_HALF_BASE,
                                     "height_m": sg.BARRIER_H, "path_xz": [[r["x"], r["z"]] for r in seat]}})
        lo_lat = loc["origin"]["lat"]
        m_lon, m_lat = dp.meters_per_degree(lo_lat)
        built.append({
            "id": pid, "object": deck_ob.name, "cuts": d["cuts"], "node": d["node"],
            "rows": [[[round(v, 3) for v in q] for q in row] for _, _, row in cuts_rows + arm_rows],
            **({"arm_rows": arm_meta} if arm_meta else {}),
            "seam_residual_m": {"max": round(max(abs(r) for p_ in prof for r in p_["r"]), 3),
                                "fade_m": [round(p_["fade"], 1) for p_ in prof]},
            "faces_removed": removed, "deck_vertices": len(verts3), "deck_faces": len(faces),
            "area_m2": round(ring_a, 1), "ribbon_edge_points_added": widened, "ground": held, "ribbon_union_m2": round(united * 0.0625, 1), "barriers": bars,
            "outline_en": [[round(q[0], 3), round(q[1], 3)] for q in ring],
            "outline_lonlat": [[round(loc["origin"]["lon"] + q[0] / m_lon, 8), round(lo_lat + q[1] / m_lat, 8)]
                               for q in ring],
            "source": rec.get("source"), "uncertainty_m": rec.get("uncertainty_m"),
        })
        if deck_rep is not None:
            built[-1]["deck_fill"] = deck_rep
        _log(f"{pid}: rows v{lo_k} ({len(cuts_rows[0][2])} verts) / v{hi_k} ({len(cuts_rows[1][2])}); lap faces removed "
             f"{removed}; deck {len(verts3)} v / {len(faces)} f, {built[-1]['area_m2']} m2; seam residual max "
             f"{built[-1]['seam_residual_m']['max']} m; {widened} ribbon-edge points, {united * 0.0625:.1f} m2 of this line's ribbon united; {len(arm_rows)} street arm row(s) {[m_['piece'] for m_ in arm_meta]}; ground {held}; {len(bars)} mouth barrier(s) ({along_lap} box runs along the lap skipped) "
             f"{[b['span_m'] for b in bars]} m")
    return built


def exemptions(proj, built):
    p = proj / "pavement_exemptions.json"
    if not p.exists() or not built:
        return 0
    d = json.loads(p.read_text(encoding="utf-8"))
    n = 0
    for b in built:
        eid = f"mouth_{b['id'].lower()}"
        e = next((x for x in d.get("exemptions") or [] if x.get("id") == eid), None)
        if e is None:
            e = {"id": eid, "object": b["object"], "match": "footprint"}
            d.setdefault("exemptions", []).append(e)
        e.pop("polygon_lonlat", None)
        e["polygon_xz"] = dp.offset_ring([tuple(q) for q in b["outline_en"]], EXEMPT_MARGIN_M)
        e["status"] = (f"measured: tools/lm_pads_blend.py from source/pads/{b['id']}.json "
                       f"({(b.get('source') or {}).get('kind')}, outline +-{(b.get('uncertainty_m') or {}).get('outline')} m)")
        n += 1
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    return n


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    proj = Path(argv[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    decls = dp.declarations({"route": {"draft_pads": (cfg.get("lm_pads") or {}).get("pads") or []}})
    if not decls:
        _log("no lm_pads.pads declared: nothing to do")
        return
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    built = build(proj, cfg, decls)
    # "stubs": every K-rail in the shape scripts/geometry/audit_mesh.py reads (its D rule exempts a 1WALL_STUB vertex
    # inside its declared footprint, as for Lake Murray's pads and stubs)
    res = {"pads": built, "stubs": [b for p_ in built for b in p_["barriers"]],
           "written": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (proj / "data" / "pads.built.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    n = exemptions(proj, built)
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))
    _log(f"{len(built)} pad(s) built; {n} exemption polygon(s) written; saved loop.blend")


main()
