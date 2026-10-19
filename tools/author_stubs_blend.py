"""PHASE 5 — author every declared side-road STUB's curb returns, corner pavement and barrier into loop.blend (ledger
0054, Kevin 2026-10-14: "a road we are not completing gets a barrier, not a curve"). The pure geometry and its reasons
are tools/stub_geom.py; the declaration and the stub road itself are tools/stub_roads.py (a stub is a connector, so
the assembler swept its road / curb / sidewalk / paint, weld_mouths welded its mouth and seat_terrain seated it).

Runs INSIDE Blender, in two stages around tools/gap_mouths_blend.py (which keys on the assembler's CURB vertex
order — this pass never deletes or reorders a vertex before it, and appends its own after every block):

    blender --background --python-exit-code 1 --python tools/author_stubs_blend.py -- <project> --stage author
    blender --background --python-exit-code 1 --python tools/gap_mouths_blend.py -- <project>
    blender --background --python-exit-code 1 --python tools/author_stubs_blend.py -- <project> --stage tidy

author (after author_median, before gap_mouths), per stub (data/stubs.plan.json + its mouth in data/mouths.json):
  1. RETURNS, both corners: the stub's road edge line (its rows past the weld's re-spread) meets the host's road edge
     at K; the return runs from the host curb row where gap_mouths' gap will end (mouth_weld.gap_window, the very same
     window) round a circle tangent to both edges to the stub's first curb row past B. The return strip is APPENDED
     to CURB; the corner pavement (a fan from K) to ROAD — merged like every connector, shared physics and material.
     The stub's own curb faces before row J are removed FACES_ONLY (no vertex moves or goes before gap_mouths).
     A return whose walk must be compressed (stub_geom.walk_scale < 1: an acute corner's small radius) is compressed
     continuously: the host's own curb rows behind the gap end ease into it over HOST_RAMP_M (their walk-back and grass-
     meet vertices MOVE, no index changes), and J is taken at least STUB_RAMP_M past B for the tail to ease back out.
  2. GROUND: TERRAIN edges in each corner zone (within its tangent + ZONE_PAD_M of K) are halved down to TERRAIN_EDGE_M
     — except under the straight strips' verges (the stub's own kept curb rows, the host's rows behind the gap end) and
     the COARSE_OUT_M behind their grass meet — then every TERRAIN vertex under a road or curb strip there (the corner
     fan, the return, the stub's road and kept curb rows, the host's eased rows) is pinned under it (seat_terrain's
     rule: deck - 0.10 - 0.06; under a verge 0.02 under it).
     WHY (2026-10-18, the phase-5 verifier's sawtooth "teeth" of grass behind the returns): the kn5 prep lays every
     ground vertex within 3 m of a road at deck - 0.02 and then clamps it 0.02 under the lowest drivable sheet, and the
     loop's verges end 0.20 m under their road (curb_sidewalk grass_clearance): the verge's foot is buried, and the two
     rules meet along it. On the host's coarse ground that meeting is one long gentle facet (the loop's look
     everywhere); refined to 0.75 m it alternated cell by cell — 0.2-0.6 m teeth along every grass meet in the zone
     (measured after the prep; the author stage's own ground there was smooth). The return's grass meet now lands on the
     prep's ground (stub_geom MEET_H_M), so the ground under and behind it may be fine; the straight strips keep the
     buried foot, so the ground there stays as coarse as the host's. The corner's pavement and nose stay refined (a
     coarse facet across an acute corner's narrow fan rode 5 mm over the road at Lambda Dr's 57 deg nose).
  3. BARRIER `1WALL_STUB_<id>` (collection STUBS): the K-rail jersey strip across the stub at its declared distance
     from the mouth line, grass meet to grass meet over both sidewalks, each ring seated on the lowest stub surface
     under its footprint (a BVH over ROAD + CURB) less 0.02 m; smooth-shaded with hard creases (race_furniture).
  CURB CUTS (driveways, `curb_cut` in the plan): the host curb top drops to the lip over the apron, flaring back.
tidy (after gap_mouths): the stub curb vertices the author stage orphaned (no face left) are deleted; self-check that
  every return's first row still meets a host curb face (gap_mouths ended the gap where this pass said it would).

Writes data/stubs.built.json (per stub: corners K/A/B/J, tangent, radius, wedge angle, stations; the barrier's ring
path, bases and the surfaces under each; faces removed, ground pinned; curb cuts). Exit 1 (loop.blend NOT saved) on
any failure: a mouth missing, a corner it cannot build honestly, a barrier ring with no stub surface under it.
Idempotent per assembler run: a second author stage on the same loop.blend is refused (CURB carries the stamp).
With no data/stubs.plan.json it prints that and exits 0 without opening loop.blend.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mouth_weld as mw  # noqa: E402
import race_furniture as rf  # noqa: E402
import stub_geom as sg  # noqa: E402

STAMP = "stub_returns"
COLLECTION = "STUBS"
WALL_PREFIX = "1WALL_STUB_"
TERRAIN_EDGE_M = 0.75      # terrain edges in a corner zone (within ZONE_PAD_M of its tangent length round K) are halved
ZONE_PAD_M = 3.5           # down to this; the return's walk + verge reach 3.1 m past the arc
HOST_KEEP_M = 0.3          # the ground under the host's pavement (+ this) is refined with the corner (the prep pins the finer
#                            vertices under both decks: a 4 m facet spanning the seam rose within 1 mm of the stub's road on the
#                            2026-10-14 rehearsal) but never PINNED here — the host's deck is the prep's to seat
PIN_UNDER_M = 0.16         # seat_terrain: deck - LIFT 0.10 - CLEAR_M 0.06
VERGE_UNDER_M = 0.02
EDGE_FIT_FROM_M = 8.0     # the stub's road edge line is fitted on its rows at least this far out AND past the weld's
EDGE_FIT_ROWS = 3          # re-spread (data/mouth_welds.json rows_respread), over at least this many rows
COARSE_OUT_M = 1.0         # [INVENTED] the ground behind a straight strip's grass meet left unrefined this far (GROUND)


def _box(t):
    return (min(p[0] for p in t), max(p[0] for p in t), min(p[2] for p in t), max(p[2] for p in t))


def _hash(tris, cell=1.0):
    """{(floor(x), floor(z)): [tri]} over each triangle's plan box (1 m cells)"""
    out = {}
    for t in tris:
        x0, x1, z0, z1 = _box(t)
        for i in range(math.floor(x0 / cell), math.floor(x1 / cell) + 1):
            for j in range(math.floor(z0 / cell), math.floor(z1 / cell) + 1):
                out.setdefault((i, j), []).append(t)
    return out


def B(p):
    """engine (x, y, z) -> Blender (x, z, y)"""
    return (p[0], p[2], p[1])


def E(v):
    return (v[0], v[2], v[1])


def _verts(ob):
    return [E(v.co) for v in ob.data.vertices]


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    stage = argv[argv.index("--stage") + 1] if "--stage" in argv else "author"
    return proj, stage


def _closed(pts):
    return abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6


def _gap_ends(stations, mh, closed):
    """the two end stations of a (possibly wrapping) contiguous gap set"""
    s = sorted(stations)
    if not s:
        return None
    if closed and len(s) < mh and 0 in stations and (mh - 1) in stations:
        # wraps the seam: find the hole
        for i in range(len(s) - 1):
            if s[i + 1] - s[i] > 1:
                return s[i + 1], s[i]
    return s[0], s[-1]


def main():
    proj, stage = _args()
    data = proj / "data"
    pp = data / "stubs.plan.json"
    if not pp.exists():
        print(f"[stubs] no data/stubs.plan.json — no stub declared, nothing to author ({stage})")
        return
    plan = json.loads(pp.read_text(encoding="utf-8"))
    if stage == "tidy":
        return tidy(proj, plan)
    if stage != "author":
        raise SystemExit(f"[stubs] unknown --stage {stage}")
    mouths = json.loads((data / "mouths.json").read_text(encoding="utf-8"))["mouths"]
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    main_pts = [tuple(p) for p in local["points_xyz_m"]]
    lay = mw.mesh_layout(main_pts, conns)
    hosts = {"MAINLINE": main_pts}
    hosts.update({c["name"]: [tuple(p) for p in c["points_xyz_m"]] for c in conns})

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    road, curb, terr = (bpy.data.objects.get(n) for n in ("ROAD", "CURB", "TERRAIN"))
    if road is None or curb is None or terr is None:
        raise SystemExit("[stubs] FATAL: loop.blend lacks ROAD / CURB / TERRAIN")
    if STAMP in curb.keys():
        raise SystemExit("[stubs] FATAL: loop.blend already carries the stub returns (CURB stamp) — rebuild it first")
    RV = _verts(road)
    CV = _verts(curb)
    if len(RV) != lay["_road_total"]:
        raise SystemExit(f"[stubs] FATAL: ROAD {len(RV)} verts, the assembler's layout says {lay['_road_total']} — "
                         f"the row order changed; not authoring")
    if len(CV) < lay["_curb_total"]:
        raise SystemExit(f"[stubs] FATAL: CURB {len(CV)} verts < the layout's {lay['_curb_total']}")
    # the layout contract on every stub block: CURB lane edge == ROAD edge, row for row, past the weld's re-spread
    # (there the weld mitred the road lines 0.4 m inside the host edge and the curb lines on it, line by line)
    welds = {w["piece"]: w for w in json.loads((data / "mouth_welds.json").read_text(encoding="utf-8"))["mouths"]
             if w.get("end") == "start"}
    stub_pieces = {}
    for st in plan["stubs"]:
        mo = next((m for m in mouths if str(m.get("connector")) == st["connector"]), None)
        if mo is None or not mo.get("piece"):
            raise SystemExit(f"[stubs] FATAL: {st['connector']}: no mouth / piece in data/mouths.json (trim dropped it?)")
        if mo["end"] != "start":
            raise SystemExit(f"[stubs] FATAL: {st['connector']}: the mouth is at the piece's {mo['end']} (a stub starts "
                             f"inside its host)")
        piece = mo["piece"]
        b = lay[piece]
        if piece not in welds:
            raise SystemExit(f"[stubs] FATAL: {piece}: not in data/mouth_welds.json (the weld did not run on it)")
        jw = int(welds[piece]["rows_respread"])
        cen0 = [RV[mw.road_index(lay, piece, r, 1)] for r in range(b["rows"])]
        arc0 = mw.arc_lengths(cen0)
        j1 = max(jw, next(j for j, a in enumerate(arc0) if a >= EDGE_FIT_FROM_M))
        if b["rows"] - 1 - j1 < EDGE_FIT_ROWS:
            raise SystemExit(f"[stubs] FATAL: {piece}: only {b['rows'] - 1 - j1} rows past the weld's re-spread (row {jw}) to "
                             f"fit its edges on — declare it longer")
        for side, lane in ((1, 0), (-1, 2)):
            for r in range(j1, b["rows"]):
                e = RV[mw.road_index(lay, piece, r, lane)]
                c = CV[mw.curb_index(lay, piece, r, side, 0)]
                # plan exact (the block order); height within 0.05 m (the weld warps each line off its own end height)
                if math.hypot(e[0] - c[0], e[2] - c[2]) > 2e-3 or abs(e[1] - c[1]) > 0.05:
                    raise SystemExit(f"[stubs] FATAL: {piece} row {r} side {side:+d}: CURB lane edge off the ROAD edge by "
                                     f"{math.dist(e, c):.4f} m — the block order changed; not authoring")
        stub_pieces[st["id"]] = (mo, piece)

    built = {"version": 1, "stubs": [], "curb_cuts": []}
    new_road_v, new_road_f = [], []
    new_curb_v, new_curb_f = [], []
    doomed_curb = set()          # (row, side, piece) stub curb faces to remove
    moved_curb = {}              # CURB vertex index -> engine point: a compressed return's host rows eased (stub_geom)
    zones = []                   # ground work: (pavement tris, return tris, verge tris, centre, reach)
    for st in plan["stubs"]:
        mo, piece = stub_pieces[st["id"]]
        b = lay[piece]
        host = mo["host"]
        hb = lay[host]
        hpts = hosts[host]
        mh = hb["rows"]
        closed = _closed(hpts)
        side = int(mo["side"])
        rows = [tuple(RV[mw.road_index(lay, piece, r, k)] for k in range(3)) for r in range(b["rows"])]
        cen = [r[1] for r in rows]
        arcs = mw.arc_lengths(cen)
        j1 = max(int(welds[piece]["rows_respread"]), next(j for j, a in enumerate(arcs) if a >= EDGE_FIT_FROM_M))
        j2 = b["rows"] - 1
        # the host gap (gap_mouths' own window) and its two end rows on the mouth side
        S = mw.gap_window(hpts, mh, closed, int(mo["host_seg"]), float(mo["host_t"]), float(mo["connector_width_m"]),
                          float(mo.get("angle_deg") or 90.0))
        ends = _gap_ends(S, mh, closed)
        if ends is None:
            raise SystemExit(f"[stubs] FATAL: {piece}: empty gap window")
        host_lane = 0 if side == 1 else 2
        # the host's own deck near the mouth: the ground under the HOST's pavement is the prep's (its mainline
        # conform) and seat_terrain's — never refined or moved here (a finer facet there let grass reach the host lane)
        hrows = [tuple(RV[mw.road_index(lay, host, r, k)] for k in range(3)) for r in range(mh)]
        hdeck = mw.HostDeck(hrows, mw.host_window(hrows, closed, mo["cut_xyz"][0], mo["cut_xyz"][2]))
        hedge = [RV[mw.road_index(lay, host, r, host_lane)] for r in range(mh)]
        corners = []
        for e, lane in ((1, 0), (-1, 2)):
            E1, E2 = rows[j1][lane], rows[j2][lane]
            bdir = sg.unit2(E2[0] - E1[0], E2[2] - E1[2])
            back = (-bdir[0], -bdir[1])
            # K: the stub edge line (from E1 backward) meets the host edge, searched over the host rows near the gap
            Kp, best_s = None, None
            lo, hi = ends
            if hi < lo:
                hi += mh
            for q in range(lo - 6, hi + 7):
                if not closed and not (0 <= q < mh - 1):
                    continue
                a, c = hedge[q % mh], hedge[(q + 1) % mh]
                hit = sg.line_seg_intersect(E1, back, a, c)
                if hit is not None and hit[2] >= 0 and (best_s is None or hit[2] < best_s):
                    best_s = hit[2]
                    Kp = (hit[0], a[1] + (c[1] - a[1]) * hit[3], hit[1])
            if Kp is None:
                raise SystemExit(f"[stubs] FATAL: {piece} edge {e:+d}: its road edge line never meets the host edge")
            # the gap end on THIS edge's side of the stub
            cands = []
            for kend in ends:
                A_row = tuple(CV[mw.curb_index(lay, host, kend, side, p)] for p in range(4))
                lat_e = (A_row[0][0] - E1[0]) * rf.left_normal(*bdir)[0] + (A_row[0][2] - E1[2]) * rf.left_normal(*bdir)[1]
                cands.append((lat_e * e, kend, A_row))
            cands.sort(reverse=True)
            if cands[0][0] <= 0:
                raise SystemExit(f"[stubs] FATAL: {piece} edge {e:+d}: no host gap end on its side")
            _s, kend, A_row = cands[0]
            tH = sg.dist2(Kp, A_row[0])
            # the walk's compression (stub_geom: continuous — a compressed return eases back over the host behind A and
            # over at least STUB_RAMP_M of the stub's tail); every stub curb row has the same profile offsets
            try:
                wscale = sg.walk_scale(A_row, tuple(CV[mw.curb_index(lay, piece, j1, e, p)] for p in range(4)), Kp, bdir)
            except sg.GeomError as ex:
                raise SystemExit(f"[stubs] FATAL: {piece} edge {e:+d}: {ex}")
            # J: the first stub curb row at or past B (u along the edge from K >= tH; + STUB_RAMP_M when compressed)
            J = None
            need = tH + 0.05 + (sg.STUB_RAMP_M if wscale < 1.0 else 0.0)
            for r in range(b["rows"]):
                p0 = CV[mw.curb_index(lay, piece, r, e, 0)]
                u = (p0[0] - Kp[0]) * bdir[0] + (p0[2] - Kp[2]) * bdir[1]
                if u >= need:
                    J = r
                    break
            if J is None or J >= b["rows"] - 3:
                raise SystemExit(f"[stubs] FATAL: {piece} edge {e:+d}: the return (tangent {tH:.2f} m) runs past the stub")
            J_row = tuple(CV[mw.curb_index(lay, piece, J, e, p)] for p in range(4))
            wscale = sg.walk_scale(A_row, J_row, Kp, bdir)            # exactly return_stations' own
            # the host's rows behind A, away from the mouth (the gap window S holds the mouth side)
            away = 1 if (((kend + 1) % mh) if closed else kend + 1) not in S else -1
            h_ramp_rows = []
            for k in range(0, 24):
                r = kend + away * k
                if closed:
                    r %= mh
                elif not 0 <= r < mh:
                    break
                h_ramp_rows.append(r)
            h_rows = [tuple(CV[mw.curb_index(lay, host, r, side, p)] for p in range(4)) for r in h_ramp_rows]
            eased = sg.host_ramp(h_rows, wscale)
            for k, nrow in eased:
                for p in (2, 3):
                    vi = mw.curb_index(lay, host, h_ramp_rows[k], side, p)
                    moved_curb[vi] = nrow[p]
                    CV[vi] = nrow[p]
            # the lane edge's height round the corner: the host deck (extended level past its edge) and this stub
            # edge's own height, blended by distance to each — the corner pavement meets both at their heights, so
            # the ground pinned under it never stands over either deck where a facet spans the seam
            sedge = [rows[r][lane] for r in range(b["rows"])]

            def y0_of(x, z, _se=sedge, _hd=hdeck, _side=side):
                a_ = max(0.0, _hd.edge_gap(x, z, _side, 0.0))
                best = None
                for q in range(len(_se) - 1):
                    p0, p1 = _se[q], _se[q + 1]
                    dx, dz = p1[0] - p0[0], p1[2] - p0[2]
                    L2 = dx * dx + dz * dz
                    if L2 < 1e-12:
                        continue
                    t = max(0.0, min(1.0, ((x - p0[0]) * dx + (z - p0[2]) * dz) / L2))
                    d = math.hypot(x - (p0[0] + dx * t), z - (p0[2] + dz * t))
                    if best is None or d < best[0]:
                        best = (d, p0[1] + (p1[1] - p0[1]) * t)
                b_, ys = best
                yh = _hd.at(x, z)
                return yh if a_ + b_ < 1e-9 else (b_ * yh + a_ * ys) / (a_ + b_)
            try:
                stations, rec = sg.return_stations(A_row, J_row, Kp, bdir, y0_of=y0_of)
            except sg.GeomError as ex:
                raise SystemExit(f"[stubs] FATAL: {piece} edge {e:+d}: {ex}")
            if eased and max(sg.dist2(stations[0][p], eased[0][1][p]) for p in range(4)) > 1e-9:
                raise SystemExit(f"[stubs] FATAL: {piece} edge {e:+d}: the return's first row is not the host's eased "
                                 f"row A")
            rec["host_rows_eased"] = len(eased)
            # the curb return strip -> CURB (appended)
            base = len(CV) + len(new_curb_v)
            for row in stations:
                new_curb_v.extend(row)
            for q in sg.strip_faces(len(stations), base):
                new_curb_f.append(q)
            # the corner pavement -> ROAD (appended)
            pv, pt = sg.corner_pavement(Kp, Kp[1], stations, rec["n_arc_rows"])
            rb = len(RV) + len(new_road_v)
            new_road_v.extend(pv)
            new_road_f.extend(tuple(rb + i for i in t) for t in pt)
            for r in range(J):
                doomed_curb.add((piece, e, r))
            rec.update({"edge": e, "host_gap_end_station": kend, "J_row": J, "faces_removed": J * 3,
                        "pavement_tris": len(pt)})
            corners.append(rec)
            # ground zone (GROUND below): every road and curb strip over the corner ground — the corner pavement fan,
            # the return, the stub's own kept curb rows (J on) and road, the host's kept curb rows behind A (as eased)
            reach = tH + ZONE_PAD_M
            ptris = [(pv[t[0]], pv[t[1]], pv[t[2]]) for t in pt]
            wtris, vtris = [], []

            def band(rows_, _w=wtris, _v=vtris):
                for r0, r1 in zip(rows_, rows_[1:]):
                    dy = min(r0[0][1], r1[0][1])
                    for p in range(3):
                        quad = (r0[p], r0[p + 1], r1[p + 1], r1[p])
                        tl = [(quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])]
                        if p == 2:
                            _v.extend(tl)
                        else:
                            _w.extend((t_, dy) for t_ in tl)

            def within(row, _K=Kp, _r=reach):
                return any(math.hypot(q[0] - _K[0], q[2] - _K[2]) <= _r for q in row)
            band(list(stations))
            s_rows = [tuple(CV[mw.curb_index(lay, piece, r, e, p)] for p in range(4)) for r in range(J, b["rows"])]
            s_rows = s_rows[:next((k for k, rw in enumerate(s_rows) if not within(rw)), len(s_rows)) + 1]
            band(s_rows)
            hz_rows = [tuple(CV[mw.curb_index(lay, host, r, side, p)] for p in range(4)) for r in h_ramp_rows]
            hz_rows = hz_rows[:next((k for k, rw in enumerate(hz_rows) if not within(rw)), len(hz_rows)) + 1]
            band(hz_rows)
            for r0, r1 in zip(rows, rows[1:]):
                if within(r0) or within(r1):
                    ptris += [(r0[0], r0[1], r1[1]), (r0[0], r1[1], r1[0]), (r0[1], r0[2], r1[2]), (r0[1], r1[2], r1[1])]
            # the straight strips' verges + COARSE_OUT_M behind them stay as coarse as the host's (GROUND below)
            coarse = []
            for rows_ in (s_rows, hz_rows):
                for r0, r1 in zip(rows_, rows_[1:]):
                    out_ = []
                    for r in (r0, r1):
                        n_ = sg.unit2(r[3][0] - r[0][0], r[3][2] - r[0][2])
                        out_.append((r[3][0] + n_[0] * COARSE_OUT_M, r[3][1], r[3][2] + n_[1] * COARSE_OUT_M))
                    coarse += [(r0[2], out_[0], out_[1]), (r0[2], out_[1], r1[2])]
            zones.append({"pave": ptris, "walk": wtris, "verge": vtris, "centre": (Kp[0], Kp[2]),
                          "reach": reach, "host": hdeck, "coarse": coarse})
        built["stubs"].append({"id": st["id"], "connector": st["connector"], "piece": piece, "host": host,
                               "side": side, "corners": corners})

    # ---- apply the CURB / ROAD edits (FACES_ONLY: every vertex index before ours stays)
    for ob, nv, nf, delset in ((curb, new_curb_v, new_curb_f, doomed_curb), (road, new_road_v, new_road_f, set())):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        if ob is curb:
            for vi, p in moved_curb.items():
                bm.verts[vi].co = B(p)
            built["host_curb_verts_eased"] = len(moved_curb)
        if delset:
            want = []
            for piece, e, r in delset:
                want.append(frozenset(mw.curb_index(lay, piece, rr, e, p) for rr in (r, r + 1) for p in range(4)))
            idx_all = set().union(*want)
            doomed = []
            for f in bm.faces:
                ids = frozenset(v.index for v in f.verts)
                if ids <= idx_all and any(ids <= w for w in want):
                    doomed.append(f)
            bmesh.ops.delete(bm, geom=doomed, context="FACES_ONLY")
            built["curb_faces_removed_total"] = len(doomed)
        start = len(bm.verts)
        n0 = len(CV) if ob is curb else len(RV)
        if start != n0:
            raise SystemExit(f"[stubs] FATAL: {ob.name} vertex count moved under the author stage")
        for p in nv:
            bm.verts.new(B(p))
        bm.verts.ensure_lookup_table()
        for f in nf:
            bm.faces.new([bm.verts[i] for i in f])
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
    # up-facing in ENGINE terms means the Blender normal's z > 0 for the new faces (the prep flips 1ROAD / 1KERB
    # faces up anyway; done here so loop.blend is right for Kevin's eye too)
    for ob, n0 in ((curb, len(CV)), (road, len(RV))):
        me = ob.data
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        flip = [f for f in bm.faces if min(v.index for v in f.verts) >= n0 and f.normal.z < 0]
        if flip:
            bmesh.ops.reverse_faces(bm, faces=flip)
        bm.to_mesh(me)
        bm.free()
        me.update()

    # ---- curb cuts (driveways): the host curb top drops to the lip over the apron
    for cc in plan.get("curb_cuts", []):
        host = cc["host"]
        hb = lay[host]
        hpts = hosts[host]
        arc = mw.arc_lengths(hpts)
        me = curb.data
        moved = 0
        for r in range(hb["rows"]):
            d = abs(arc[r] - cc["station_m"])
            if _closed(hpts):
                d = min(d, arc[-1] - d)
            if d > cc["half_span_m"] + cc["flare_m"]:
                continue
            f = 0.0 if d <= cc["half_span_m"] else (d - cc["half_span_m"]) / cc["flare_m"]
            i0 = mw.curb_index(lay, host, r, int(cc["side"]), 0)
            i1 = mw.curb_index(lay, host, r, int(cc["side"]), 1)
            y0 = me.vertices[i0].co.z
            full = me.vertices[i1].co.z - y0
            me.vertices[i1].co.z = y0 + cc["lip_m"] + (full - cc["lip_m"]) * f
            moved += 1
        me.update()
        built["curb_cuts"].append({**cc, "curb_rows_lowered": moved})

    # ---- ground under the corners
    for z_ in zones:                      # plan boxes + a 1 m hash, so a point reads only the triangles over it
        for kind in ("pave", "verge"):
            z_[kind] = [(t, _box(t)) for t in z_[kind]]
        z_["walk"] = [(t, dy, _box(t)) for t, dy in z_["walk"]]
        z_["coarse"] = _hash(z_["coarse"])

    def refine_here(x, z):
        """inside a corner zone and not under a straight strip's verge or the COARSE_OUT_M behind it"""
        inside = False
        for z_ in zones:
            if math.hypot(x - z_["centre"][0], z - z_["centre"][1]) > z_["reach"]:
                continue
            for t in z_["coarse"].get((math.floor(x), math.floor(z)), ()):
                if sg.tri_height(x, z, *t) is not None:
                    return False
            inside = True
        return inside
    tbm = bmesh.new()
    tbm.from_mesh(terr.data)
    halved = 0
    for _round in range(6):
        todo = []
        for e in tbm.edges:
            if e.calc_length() <= TERRAIN_EDGE_M:
                continue
            mx = 0.5 * (e.verts[0].co.x + e.verts[1].co.x)
            mz = 0.5 * (e.verts[0].co.y + e.verts[1].co.y)
            if refine_here(mx, mz):
                todo.append(e)
        if not todo:
            break
        halved += len(todo)
        bmesh.ops.subdivide_edges(tbm, edges=todo, cuts=1, use_grid_fill=True)
    pinned = 0
    for v in tbm.verts:
        x, z, y = v.co.x, v.co.y, v.co.z
        top = None
        for z_ in zones:
            if math.hypot(x - z_["centre"][0], z - z_["centre"][1]) > z_["reach"] or z_["host"].inside(x, z, -HOST_KEEP_M):
                continue
            for kind, under in (("pave", PIN_UNDER_M), ("verge", VERGE_UNDER_M)):
                for t, bx in z_[kind]:
                    if not (bx[0] <= x <= bx[1] and bx[2] <= z <= bx[3]):
                        continue
                    h = sg.tri_height(x, z, *t)
                    if h is not None:
                        top = h - under if top is None else min(top, h - under)
            for t, dy, bx in z_["walk"]:
                if bx[0] <= x <= bx[1] and bx[2] <= z <= bx[3] and sg.tri_height(x, z, *t) is not None:
                    # under the curb face + walk: pinned like the pavement, off its own lane edge's height
                    top = dy - PIN_UNDER_M if top is None else min(top, dy - PIN_UNDER_M)
        if top is not None and y > top:
            v.co.z = top
            pinned += 1
    tbm.to_mesh(terr.data)
    tbm.free()
    terr.data.update()
    built["terrain"] = {"edges_halved": halved, "verts_pinned": pinned}

    # ---- barriers
    col = bpy.data.collections.get(COLLECTION) or bpy.data.collections.new(COLLECTION)
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    for ob in [o for o in bpy.data.objects if o.name.upper().startswith(WALL_PREFIX)]:
        bpy.data.objects.remove(ob, do_unlink=True)
    def bvh_of(ob):
        me = ob.data
        return BVHTree.FromPolygons([tuple(v.co) for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    bvh, bvh_c = bvh_of(road), bvh_of(curb)

    def top_at(x, z, near_y):
        best = None
        for t in (bvh, bvh_c):
            hit = t.ray_cast(Vector((x, z, near_y + 4.0)), Vector((0.0, 0.0, -1.0)), 12.0)
            if hit[0] is not None and (best is None or hit[0].z > best):
                best = hit[0].z
        return best

    for st, sb in zip(plan["stubs"], built["stubs"]):
        mo, piece = stub_pieces[st["id"]]
        b = lay[piece]
        rows = [tuple(RV[mw.road_index(lay, piece, r, k)] for k in range(3)) for r in range(b["rows"])]
        cen = [r[1] for r in rows]
        arcs = mw.arc_lengths(cen)
        u_bar = float(st["u_barrier_from_cut_m"])
        if u_bar >= arcs[-1] - 0.5:
            raise SystemExit(f"[stubs] FATAL: {piece}: barrier at {u_bar:.2f} m but the stub is {arcs[-1]:.2f} m long")
        j = max(i for i, a in enumerate(arcs) if a <= u_bar)
        f = (u_bar - arcs[j]) / max(1e-9, arcs[j + 1] - arcs[j])

        def lerp_row(side_):
            return tuple(tuple(CV[mw.curb_index(lay, piece, j, side_, p)][k] * (1 - f)
                               + CV[mw.curb_index(lay, piece, j + 1, side_, p)][k] * f for k in range(3))
                         for p in range(4))
        left, right = lerp_row(1), lerp_row(-1)
        path = sg.barrier_path(right, left)
        yref = cen[j][1]

        def base_of(x, z, ax, az):
            samples = []
            for px, pz in sg.footprint_samples(x, z, ax, az):
                samples.append(top_at(px, pz, yref))
            got = [s for s in samples if s is not None]
            return (min(got) if got else None), samples
        try:
            rings, seat = sg.barrier_rings(path, base_of)
        except sg.GeomError as ex:
            raise SystemExit(f"[stubs] FATAL: {piece}: {ex}")
        verts, faces, uvs = sg.barrier_mesh(rings)
        sharp = rf.sharp_edges(verts, faces)
        bv, bf = rf.to_blender(verts, faces)
        name = WALL_PREFIX + st["id"]
        me = bpy.data.meshes.new(name)
        me.from_pydata(bv, [], bf)
        me.validate()
        uvl = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uvl.data[li].uv = uvs[me.loops[li].vertex_index]
        me.shade_smooth()
        key = {(a, c) if a < c else (c, a) for a, c in sharp}
        me.edges.foreach_set("use_edge_sharp", [tuple(sorted(e.vertices)) in key for e in me.edges])
        me.update()
        ob = bpy.data.objects.new(name, me)
        col.objects.link(ob)
        sinks = [max(s for s in r["surface"] if s is not None) - r["base"] for r in seat]
        sb["barrier"] = {"object": name, "style": st.get("barrier", "krail"), "u_from_cut_m": u_bar,
                         "half_base_m": sg.BARRIER_HALF_BASE, "height_m": sg.BARRIER_H, "rings": len(rings),
                         "path_xz": [[r["x"], r["z"]] for r in seat], "kinds": [r["kind"] for r in seat],
                         "seat": seat, "max_sink_m": round(max(sinks), 4),
                         "span_m": round(sum(math.hypot(seat[i + 1]["x"] - seat[i]["x"], seat[i + 1]["z"] - seat[i]["z"])
                                             for i in range(len(seat) - 1)), 3),
                         "verts": len(verts), "faces": len(faces)}
        sb["stub_length_m"] = round(arcs[-1], 3)
        print(f"[stubs] {piece}: returns R {', '.join(str(c['radius_m']) for c in sb['corners'])} m (tangent "
              f"{', '.join(str(c['tangent_m']) for c in sb['corners'])} m, wedge "
              f"{', '.join(str(c['phi_deg']) for c in sb['corners'])} deg); barrier {name} {len(rings)} rings over "
              f"{sb['barrier']['span_m']} m at {u_bar:.2f} m from the cut, max sink {sb['barrier']['max_sink_m']} m")
    curb[STAMP] = len(plan["stubs"])
    (data / "stubs.built.json").write_text(json.dumps(built, indent=1), encoding="utf-8")
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[stubs] author: {len(plan['stubs'])} stub(s), {len(new_curb_v) // 4} return stations, "
          f"{len(new_road_f)} corner pavement tris, {built.get('curb_faces_removed_total', 0)} stub curb faces removed, "
          f"{len(built['curb_cuts'])} curb cut(s); ground: {halved} edges halved, {pinned} verts pinned; saved loop.blend")


def tidy(proj, plan):
    data = proj / "data"
    bp = data / "stubs.built.json"
    if not bp.exists():
        raise SystemExit("[stubs] FATAL: tidy without data/stubs.built.json — the author stage did not run")
    built = json.loads(bp.read_text(encoding="utf-8"))
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    curb = bpy.data.objects.get("CURB")
    if curb is None or STAMP not in curb.keys():
        raise SystemExit("[stubs] FATAL: tidy on a loop.blend the author stage did not stamp")
    zones = [(c["K"][0], c["K"][1], c["tangent_m"] * 2.0 + 6.0) for s in built["stubs"] for c in s["corners"]]
    bm = bmesh.new()
    bm.from_mesh(curb.data)
    loose = [v for v in bm.verts if not v.link_faces
             and any(math.hypot(v.co.x - x, v.co.y - z) <= r for x, z, r in zones)]
    # every return's first row must still meet a host curb face (gap_mouths ended the gap at the predicted row)
    bad = []
    for s in built["stubs"]:
        for c in s["corners"]:
            ax, az = c["A"]
            near = [v for v in bm.verts if abs(v.co.x - ax) < 1e-3 and abs(v.co.y - az) < 1e-3]
            # the host strip is triangles (ribbon.curb_sidewalk), the return quads: the row needs both
            host_f = sum(1 for v in near for f in v.link_faces if len(f.verts) == 3)
            ret_f = sum(1 for v in near for f in v.link_faces if len(f.verts) == 4)
            if host_f < 1 or ret_f < 1:
                bad.append(f"{s['piece']} edge {c['edge']:+d}: the curb row at A ({ax:.2f}, {az:.2f}) carries {host_f} host "
                           f"and {ret_f} return faces — gap_mouths gapped past the return's start")
    if bad:
        bm.free()
        raise SystemExit("[stubs] FATAL tidy: " + "; ".join(bad))
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(curb.data)
    bm.free()
    curb.data.update()
    built["tidy"] = {"orphan_curb_verts_deleted": len(loose)}
    bp.write_text(json.dumps(built, indent=1), encoding="utf-8")
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[stubs] tidy: {len(loose)} orphaned stub curb verts deleted; every return meets its host curb; saved loop.blend")


main()
