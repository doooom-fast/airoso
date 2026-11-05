"""Cut every side street at the pavement edge of the road it joins — the RIBBON-THROUGH junction
topology (docs/JUNCTIONS.md §2: host ribbon unbroken, side street butt-welded to its edge).

Hosts: the MAINLINE, plus every divided connector trunk (route.divided_connectors — Del Cerro Blvd
after tools/divide_connectors.py), so a street joining the boulevard is cut and gapped exactly like
one joining College (Kevin, 2026-10-08: side streets "not connecting correctly ... sidewalks
blocking them"). Two passes: all connectors vs the mainline, then the non-host pieces vs the host
trunks. For each cut: an endpoint OVERLAP_M inside the host's pavement edge (a hairline gap shows
terrain; 0.4 m of overlap does not), a record in data/mouths.json for tools/gap_mouths_blend.py,
tools/weld_mouths_blend.py and tools/verify_mouths.py, and — when the host carries a median island —
the island zeroed within MOUTH_ISLAND_GAP_M of the cut (left-turn pocket) in median_bands.json.

HEIGHT MATCH (Kevin 2026-10-09: "lots of hovering" at the side-street intersections). The cut lands
on the host centreline height INTERPOLATED along the host segment the cut projects onto (it was the
NEAREST host vertex's height: up to 3 m of a 4.56 % grade away — 0.14 m on College), and the piece's
last BLEND_M are blended onto it with a smoothstep weight (no grade kink where the blend starts or
at the mouth), walking FROM THE CUT END whichever end of the piece it is (a cut at a piece's START
used to walk from the far end and never blend at all: del_cerro_blvd#1 dropped 0.58 m in its first
2.1 m, medium#2+0#0#0 0.33 m in 3.3 m — diagnosis 2026-10-11). A divided connector's island
(median_bands.json connector_islands, the trunk's own points) gets the SAME blend, so the island
deck follows the trunk deck it stands on.

mouths.json, one record per cut:
  connector, host, host_vertex, side, connector_width_m, cut_xyz      (as before; host_vertex is the
                                                                      host vertex nearest the first
                                                                      dropped point — barrier_bands
                                                                      keys on it; side is now the side
                                                                      of the piece's last point OUTSIDE
                                                                      the host, its approach: the first
                                                                      point inside can lie past the host
                                                                      centreline — medium#2+0#0 at
                                                                      del_cerro_blvd#1 v82 read +1 while
                                                                      arriving from -1, and gap_mouths
                                                                      gapped the far sidewalk)
  host_seg, host_t        the host segment + fraction the CUT projects onto (the cut height's source)
  angle_deg               connector vs host direction at the cut, 0 < a <= 90
  host_grade              the host's grade along that segment (rise / run)
  piece, end              the FINAL connector piece whose endpoint is the cut and which end it is
                          ("start" | "end") — resolved after both passes (a pass-1 piece re-cut in
                          pass 2 is renamed <name>#<k>); null when the piece was dropped (< MIN_PIECE_M)

GRADE-CAPPED BLEND (opt-in, ledger 0054 P1 fix round: track.config.json route.trim_blend_grade_cap = [connector-name
prefixes]). The blend's smoothstep adds 1.5 x (host - piece) / BLEND_M to the piece's own grade at its steepest. At J1
the loop's deck stands 1.44 m over Waring's 3DEP at the cut and Waring itself falls ~5.5 % from it, so 30 m of blend
made the stub fall 14.8 % (rows 5-9 of the rehearsal's weld) — over route_connectors' 11 % cap (EXPANSION-PLAN A6: the
cap stays, and binds nowhere). For a listed connector the blend runs over the SHORTEST length of BLEND_M, BLEND_M + 5,
... BLEND_CAP_MAX_M whose blended grade stays within route_connectors.MAX_GRADE (else the least steep, with a
warning); its mouths.json record carries blend_m and blend_max_grade. Every other connector: BLEND_M, as before.

Idempotent from data/connectors.local.json.pre-trim (written once per base). Run after divide,
before build_loop_blend.

    python tools/trim_connectors.py <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

OVERLAP_M = 0.4
MIN_PIECE_M = 15.0
MOUTH_ISLAND_GAP_M = 18.0
BLEND_M = 30.0
BLEND_CAP_STEP_M = 5.0     # [invented] grade-capped blend (opt-in): lengths tried, BLEND_M upward in this step ...
BLEND_CAP_MAX_M = 90.0     # [invented] ... to at most this
GRADE_CAP = 0.11           # tools/route_connectors.py MAX_GRADE (EXPANSION-PLAN A6: the 11 % cap stays)
OWN_GRADE_PLUS = 0.03      # [invented] ledger 0054 P3: an authored piece's offset blend may steepen its own grade by at
                           # most this (drive_test's KINK_PCT, 3 %-points: the vertical curve's allowance)
REACH_M = 15.0
END_MATCH_M = 1e-3        # a piece endpoint IS the cut when within this (cut_xyz is rounded to 1 mm)


def smoothstep(x: float) -> float:
    x = 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)
    return x * x * (3.0 - 2.0 * x)


def _project(px, pz, line):
    """(distance, segment i, t) of the nearest point on the polyline in plan (x, z)"""
    best = (float("inf"), 0, 0.0)
    for i in range(len(line) - 1):
        ax, az, bx, bz = line[i][0], line[i][2], line[i + 1][0], line[i + 1][2]
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
        d = math.hypot(px - (ax + t * dx), pz - (az + t * dz))
        if d < best[0]:
            best = (d, i, t)
    return best


def _lateral(px, pz, line, widths):
    """(distance, host half-width there, nearest vertex, side) vs a polyline"""
    d, i, t = _project(px, pz, line)
    n = len(line)
    half = (widths[i] * (1 - t) + widths[min(n - 1, i + 1)] * t) / 2.0
    k = i if t < 0.5 else min(n - 1, i + 1)
    ax, az = line[i][0], line[i][2]
    bx, bz = line[min(n - 1, i + 1)][0], line[min(n - 1, i + 1)][2]
    tx, tz = bx - ax, bz - az
    s = (-(tz) * (px - ax) + tx * (pz - az))
    return d, half, k, (1 if s >= 0 else -1)


def host_height(hpts, px, pz):
    """(y, segment, t) — the host centreline height interpolated along the segment (px, pz) projects onto"""
    _d, i, t = _project(px, pz, hpts)
    j = min(len(hpts) - 1, i + 1)
    return hpts[i][1] + (hpts[j][1] - hpts[i][1]) * t, i, t


def junction_angle(cx, cz, ox, oz, hpts, seg):
    """degrees in (0, 90]: the connector's approach (o -> cut) vs the host segment's direction"""
    j = min(len(hpts) - 1, seg + 1)
    hx, hz = hpts[j][0] - hpts[seg][0], hpts[j][2] - hpts[seg][2]
    ax, az = cx - ox, cz - oz
    la, lh = math.hypot(ax, az), math.hypot(hx, hz)
    if la < 1e-9 or lh < 1e-9:
        return 90.0
    c = abs(ax * hx + az * hz) / (la * lh)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def host_grade(hpts, seg):
    j = min(len(hpts) - 1, seg + 1)
    run = math.hypot(hpts[j][0] - hpts[seg][0], hpts[j][2] - hpts[seg][2])
    return 0.0 if run < 1e-9 else (hpts[j][1] - hpts[seg][1]) / run


def blend_from_cut(piece, cut, host_y, at_start, blend_m=BLEND_M, frozen=()):
    """Blend the piece's heights onto host_y over the blend_m nearest the cut, walking FROM the cut end
    (the cut is not yet in `piece`). Weight smoothstep(1 - s / blend_m): 1 at the cut, 0 at blend_m, flat at
    both ends. The walk stops at a point in `frozen` ((x, z) rounded to 1 mm: an earlier pass's cut — a short
    piece cut at both ends never drags its other mouth off its host). Returns [(x, z, dy)] for every point moved
    (the island follows the same deltas)."""
    order = range(len(piece)) if at_start else range(len(piece) - 1, -1, -1)
    moved = []
    acc = 0.0
    prev = cut
    for q in order:
        p = piece[q]
        acc += math.hypot(p[0] - prev[0], p[2] - prev[2])
        if acc >= blend_m or (round(p[0], 3), round(p[2], 3)) in frozen:
            break
        w = smoothstep(1.0 - acc / blend_m)
        ny = p[1] + (host_y - p[1]) * w
        moved.append((p[0], p[2], ny - p[1]))
        piece[q] = (p[0], ny, p[2])
        prev = p
    return moved


def offset_blend_from_cut(piece, cut, host_y, at_start, blend_m=BLEND_M, frozen=()):
    """THE OFFSET BLEND (ledger 0054 P3, the grade-capped connectors only): the piece's own profile, extended to the cut
    along its own grade, is LIFTED (or lowered) by dy0 = host_y - that height, the lift easing out over blend_m
    (weight smoothstep(1 - s / blend_m), 1 at the cut). blend_from_cut pulls every point toward the FLAT host height
    instead, so on a road that itself falls away from the host its slope adds (host - piece) x the weight's slope —
    which grows along the blend: Waring, falling 6 % from J1 under a loop deck 1.6 m over its 3DEP, read 11.3 % at
    any blend up to 90 m that way, and 6 % + 1.5 x 1.6 / blend_m (9.0 % at 80 m) this way. Same walk, same frozen
    stop, same return as blend_from_cut."""
    order = list(range(len(piece))) if at_start else list(range(len(piece) - 1, -1, -1))
    if not order:
        return []
    p0 = piece[order[0]]
    d0 = math.hypot(p0[0] - cut[0], p0[2] - cut[2])
    g0 = 0.0
    if len(order) > 1:
        p1 = piece[order[1]]
        L01 = math.hypot(p1[0] - p0[0], p1[2] - p0[2])
        g0 = 0.0 if L01 < 1e-9 else (p0[1] - p1[1]) / L01      # rise per metre toward the cut
    dy0 = host_y - (p0[1] + g0 * d0)
    moved = []
    acc = 0.0
    prev = cut
    for q in order:
        p = piece[q]
        acc += math.hypot(p[0] - prev[0], p[2] - prev[2])
        if acc >= blend_m or (round(p[0], 3), round(p[2], 3)) in frozen:
            break
        w = smoothstep(1.0 - acc / blend_m)
        moved.append((p[0], p[2], dy0 * w))
        piece[q] = (p[0], p[1] + dy0 * w, p[2])
        prev = p
    return moved


def blended_grade(piece, cut, at_start, reach):
    """the steepest |grade| between consecutive points from the cut out to `reach` of arc along a blended piece"""
    order = list(range(len(piece))) if at_start else list(range(len(piece) - 1, -1, -1))
    g, acc, prev = 0.0, 0.0, cut
    for q in order:
        p = piece[q]
        L = math.hypot(p[0] - prev[0], p[2] - prev[2])
        if L > 1e-6:
            g = max(g, abs(p[1] - prev[1]) / L)
        acc += L
        if acc >= reach:
            break
        prev = p
    return g


def own_grade(piece, at_start, reach):
    """the steepest |grade| between the piece's OWN consecutive points over `reach` of arc from its cut end (the cut
    itself, at the host's height, left out)"""
    order = list(range(len(piece))) if at_start else list(range(len(piece) - 1, -1, -1))
    g, acc = 0.0, 0.0
    for a_, b_ in zip(order, order[1:]):
        p, q = piece[a_], piece[b_]
        L = math.hypot(q[0] - p[0], q[2] - p[2])
        if L > 1e-6:
            g = max(g, abs(q[1] - p[1]) / L)
        acc += L
        if acc >= reach:
            break
    return g


def capped_blend_length(piece, cut, host_y, at_start, frozen=(), cap=GRADE_CAP, blend=None, least_steep=False):
    """(blend_m, its max grade): the shortest BLEND_M + k * BLEND_CAP_STEP_M <= BLEND_CAP_MAX_M whose blended piece
    stays within `cap` over the blend (+ one step), else the least steep of them. `blend`: the blend function
    (blend_from_cut by default; offset_blend_from_cut for an offset-blended connector). least_steep (an authored piece,
    ledger 0054 P3): the cap is the road's OWN steepest grade over the same reach + OWN_GRADE_PLUS (and never over
    `cap`) — its real grade is what the road should keep, the lift onto the loop deck a gentle vertical curve on it
    (Waring at J1, 6.3 % of its own: 60 m at 9.3 %; the shortest within 11 % was 40 m at 10.8 %, the longest 90 m at
    8.4 % kept the road off its 3DEP over 54 m)"""
    blend = blend or blend_from_cut
    best = None
    L = BLEND_M
    while L <= BLEND_CAP_MAX_M + 1e-9:
        trial = list(piece)
        blend(trial, cut, host_y, at_start, blend_m=L, frozen=frozen)
        g = blended_grade(trial, cut, at_start, L + BLEND_CAP_STEP_M)
        lim = cap
        if least_steep:
            lim = min(cap, own_grade(piece, at_start, L + BLEND_CAP_STEP_M) + OWN_GRADE_PLUS)
        if g <= lim:
            return L, g
        if best is None or g < best[1]:
            best = (L, g)
        L += BLEND_CAP_STEP_M
    return best


def _trim_against(conns, hosts, mouths, deltas=None, capped=(), no_reach=()):
    """conns: list of connector dicts to trim; hosts: list of (name, pts, widths). Returns new list.
    `deltas` (optional dict connector name -> [(x, z, dy)]) collects every blended point's height change.
    `capped`: connector-name prefixes whose blends are grade-capped (module doc, GRADE-CAPPED BLEND)."""
    out = []
    host_pts = {hn: hp for hn, hp, _ in hosts}
    host_w = {hn: hw for hn, _, hw in hosts}
    for c in conns:
        pts = [tuple(p) for p in c["points_xyz_m"]]
        w = list(c["widths_m"])
        # REACH THE HOST: a piece whose end stops short of a host's pavement (the route node sits
        # on the host's carriageway, but a divided trunk's centre is the carriageway midpoint, so
        # the end lands outside half-width) is extended to the host's centreline so the cut below
        # butts it to the edge. Only ends within REACH_M of a host are extended. A phase-5 STUB (tools/stub_roads.py,
        # `stub` in its record) is never extended: its start already stands inside its host and its far end, the
        # barrier's tail, is a dead end that must stay where it was declared.
        for end in (() if c.get("stub") else (0, -1)):
            x, y, z = pts[end]
            # `no_reach` (opt-in, route.street_junctions): an end that is already a mouth's cut ((x, z) to 1 mm) stays
            # where it was cut, never stretched on to the next host (Sand Creek 48th / Colorado: grid_primary_49, cut at
            # the lap, was reached on across 14 m to grid_primary_52's centre). Empty = every end, as before
            if (round(x, 3), round(z, 3)) in no_reach:
                continue
            best = None
            for hname, hpts, hw in hosts:
                d, half, k, side = _lateral(x, z, hpts, hw)
                if best is None or d - half < best[0] - best[1]:
                    best = (d, half, k, hname, hpts)
            if best and best[1] - OVERLAP_M <= best[0] <= best[1] + REACH_M:
                hx, hy, hz = best[4][best[2]]
                tgt = (hx, y, hz)
                if end == 0:
                    pts.insert(0, tgt)
                    w.insert(0, w[0])
                else:
                    pts.append(tgt)
                    w.append(w[-1])
        m = len(pts)
        info = []
        inside = []
        for (x, y, z) in pts:
            best = None
            for hname, hpts, hw in hosts:
                d, half, k, side = _lateral(x, z, hpts, hw)
                if best is None or d - half < best[0] - best[1]:
                    best = (d, half, k, side, hname)
            info.append(best)
            inside.append(best is not None and best[0] < best[1] - OVERLAP_M)
        pieces = []
        i = 0
        while i < m:
            if inside[i]:
                i += 1
                continue
            j = i
            while j < m and not inside[j]:
                j += 1
            piece = list(pts[i:j])
            pw = list(w[i:j])
            for (edge_idx, nbr) in ((i - 1, i), (j, j - 1)):
                if 0 <= edge_idx < m and inside[edge_idx]:
                    at_start = edge_idx < i
                    po, pi_ = pts[nbr], pts[edge_idx]
                    do, ho, _, _, _ = info[nbr]
                    di, hi, k_in, _side_in, hname = info[edge_idx]
                    # the SIDE the piece approaches from: its first point OUTSIDE the host (po). The first point
                    # inside can sit on or past the host's centreline (a route node on the far carriageway of a
                    # divided trunk, or the REACH extension above): medium#2+0#0 at del_cerro_blvd#1 v82 was
                    # recorded on side +1 while it arrives from -1, and gap_mouths gapped the wrong sidewalk
                    side = _lateral(po[0], po[2], host_pts[hname], host_w[hname])[3]
                    target = hi - OVERLAP_M
                    f = 0.0 if do == di else max(0.0, min(1.0, (do - target) / (do - di)))
                    cx, cz = po[0] + (pi_[0] - po[0]) * f, po[2] + (pi_[2] - po[2]) * f
                    hpts = host_pts[hname]
                    host_y, hseg, ht = host_height(hpts, cx, cz)
                    cut = (cx, host_y, cz)
                    # the approach direction: from the piece's point next to the cut (po unless the cut IS po)
                    ox, oz = po[0], po[2]
                    if math.hypot(cx - ox, cz - oz) < 0.05 and len(piece) >= 2:
                        o2 = piece[1] if at_start else piece[-2]
                        ox, oz = o2[0], o2[2]
                    frozen = {(round(mo["cut_xyz"][0], 3), round(mo["cut_xyz"][2], 3)) for mo in mouths}
                    cap_rec = None
                    if capped and any(str(c["name"]).startswith(px) for px in capped):
                        # ledger 0054 P3: an authored piece (its record carries `expansion`, tools/expansion_pieces.py)
                        # is OFFSET-blended (offset_blend_from_cut); P1's weld stubs and every other capped connector
                        # keep blend_from_cut
                        bfun = offset_blend_from_cut if c.get("expansion") else blend_from_cut
                        bl, bg = capped_blend_length(piece, cut, host_y, at_start, frozen=frozen, blend=bfun,
                                                     least_steep=bfun is offset_blend_from_cut)
                        cap_rec = {"blend_m": bl, "blend_max_grade": round(bg, 4),
                                   **({"blend_kind": "offset"} if bfun is offset_blend_from_cut else {})}
                        if bg > GRADE_CAP:
                            print(f"[trim] WARNING: {c['name']}: no blend up to {BLEND_CAP_MAX_M:.0f} m keeps the "
                                  f"grade within {100 * GRADE_CAP:.0f} % (least: {100 * bg:.1f} % at {bl:.0f} m)")
                        moved = bfun(piece, cut, host_y, at_start, blend_m=bl, frozen=frozen)
                    else:
                        # a record's own `blend_m` (a phase-5 stub carries 0: its profile is already anchored on host_y
                        # with the host's own grade, tools/stub_roads.py) — every other connector keeps BLEND_M
                        moved = blend_from_cut(piece, cut, host_y, at_start, blend_m=float(c.get("blend_m", BLEND_M)),
                                               frozen=frozen)
                    if deltas is not None:
                        deltas.setdefault(c["name"], []).extend(moved)
                    if at_start:
                        piece.insert(0, cut)
                        pw.insert(0, w[nbr])
                    else:
                        piece.append(cut)
                        pw.append(w[nbr])
                    mouths.append({"connector": c["name"], "host": hname, "host_vertex": k_in, "side": side,
                                   "connector_width_m": float(w[nbr]), "cut_xyz": [round(v, 3) for v in cut],
                                   "host_seg": hseg, "host_t": round(ht, 4),
                                   "angle_deg": round(junction_angle(cx, cz, ox, oz, hpts, hseg), 2),
                                   "host_grade": round(host_grade(hpts, hseg), 5), **(cap_rec or {})})
            plen = sum(math.hypot(piece[q][0] - piece[q - 1][0], piece[q][2] - piece[q - 1][2])
                       for q in range(1, len(piece)))
            # a record's own min_piece_m (opt-in: a median crossing, route.street_junctions.median_crossings, is kept at
            # any length); absent = MIN_PIECE_M, as before
            if plen >= float(c.get("min_piece_m", MIN_PIECE_M)) and plen > 0.0 and len(piece) >= 2:
                pieces.append((piece, pw))
            i = j
        if len(pieces) == 1 and not any(inside):
            out.append(c)
            continue
        for q, (piece, pw) in enumerate(pieces):
            out.append({"name": f"{c['name']}#{q}", "kind": c.get("kind", "connector"),
                        "points_xyz_m": [[round(v, 3) for v in p] for p in piece], "widths_m": pw,
                        **({"stub": c["stub"]} if c.get("stub") else {}),
                        **({"expansion": c["expansion"]} if c.get("expansion") else {}),
                        **({k_: c[k_] for k_ in ("min_piece_m", "crossing") if k_ in c})})
        if any(inside):
            print(f"[trim] {c['name']}: {len(pieces)} piece(s), {sum(inside)} pt(s) inside a host dropped")
    return out


def resolve_pieces(mouths, pieces):
    """stamp every mouth with the FINAL piece whose endpoint is its cut, and which end"""
    for mo in mouths:
        cx, _, cz = mo["cut_xyz"]
        hit = None
        for c in pieces:
            p = c["points_xyz_m"]
            for end, q in (("start", p[0]), ("end", p[-1])):
                if math.hypot(q[0] - cx, q[2] - cz) <= END_MATCH_M:
                    hit = (c["name"], end)
                    break
            if hit:
                break
        mo["piece"], mo["end"] = (hit if hit else (None, None))
    return mouths


def apply_island_deltas(bands, deltas, tol=0.01):
    """add each blended trunk point's height change to the connector island point at the same plan position
    (the island's points are the trunk's own pre-trim points). Returns the number of island points moved."""
    moved = 0
    for ci in bands.get("connector_islands", []):
        dl = [d for name, ds in deltas.items()
              if name == ci["name"] or name.startswith(ci["name"] + "#") for d in ds]
        if not dl:
            continue
        cell = {}
        for x, z, dy in dl:
            cell.setdefault((round(x), round(z)), []).append((x, z, dy))
        pts = ci["points_xyz_m"]
        for q, p in enumerate(pts):
            # every blend that moved this point (a short piece blended from both ends moved it twice; the
            # second delta is relative to the first result, so they add)
            dy_sum, hit = 0.0, False
            for gx in (-1, 0, 1):
                for gz in (-1, 0, 1):
                    for x, z, dy in cell.get((round(p[0]) + gx, round(p[2]) + gz), ()):
                        if math.hypot(x - p[0], z - p[2]) <= tol:
                            dy_sum += dy
                            hit = True
            if hit and dy_sum != 0.0:
                pts[q] = [p[0], round(p[1] + dy_sum, 4), p[2]]
                moved += 1
    return moved


# ---- STREET-TO-STREET JUNCTIONS (opt-in, ledger 0079 0.2.3: Sand Creek's grid; Kevin 2026-11-05 "Real junctions") ----
# track.config.json route.street_junctions = {"join_turn_deg": .., "bend_turn_deg": ..}. Absent (Lake Murray, the Lariat):
# none of this runs. Two steps, both on the ribbon-through topology every other mouth here uses:
#   JOIN   OSM splits a street into ways at every junction node, so one street arrives as pieces that END at one node.
#          Pieces ending at one node whose directions continue (turn <= join_turn_deg) are ONE street: joined into one
#          piece (the higher-class / longer member's name, `joined` listing the members). Where exactly two pieces end at
#          a node and nothing else meets there, the street bends: joined while the turn <= bend_turn_deg (a sharper
#          pair is a fork: two carriageways leaving one node, trimmed below). Nodes inside `keep_out` polygons (a built
#          pad's box: the pad owns that junction) are left alone.
#   RANK   where two pieces meet that no earlier pass cut (two minors, or two arterials), the THROUGH piece is the host
#          and the other is cut at its pavement edge with a mouth, exactly as a side street at the lap: a piece that ENDS
#          on another's interior ranks below it; otherwise OSM's road hierarchy, then the wider, then the longer piece.
#          Pieces are cut in rank order, each against the FINAL pieces of the higher-ranked pieces it meets, so a host is
#          never cut after a mouth was recorded on it.
MEET_R_M = 2.5            # tools/grid_connectors.py's own meeting radius: two piece ends this close are one OSM node
HEADING_M = 8.0           # [invented] a piece's direction at a node: from the node to its point this far along
OSM_RANK = {"motorway": 0, "trunk": 1, "primary": 2, "secondary": 3, "tertiary": 4, "unclassified": 5, "residential": 6}


def _osm_class(name):
    p = str(name).split("#")[0].split("_")
    return p[1] if len(p) > 2 and p[0] == "grid" else "other"


def _plan_len(pts):
    return sum(math.hypot(pts[q][0] - pts[q - 1][0], pts[q][2] - pts[q - 1][2]) for q in range(1, len(pts)))


def _end_heading(pts, at_start, look_m=HEADING_M):
    seq = pts if at_start else pts[::-1]
    x0, z0 = seq[0][0], seq[0][2]
    acc, prev, far = 0.0, seq[0], seq[-1]
    for p in seq[1:]:
        acc += math.hypot(p[0] - prev[0], p[2] - prev[2])
        prev = p
        if acc >= look_m:
            far = p
            break
    dx, dz = far[0] - x0, far[2] - z0
    L = math.hypot(dx, dz) or 1.0
    return dx / L, dz / L


def _turn_deg(h1, h2):
    """0 = the two pieces continue straight through the node, 180 = they leave it side by side"""
    c = max(-1.0, min(1.0, -(h1[0] * h2[0] + h1[1] * h2[1])))
    return math.degrees(math.acos(c))


def _in_poly(x, z, poly):
    ins = False
    for i in range(len(poly)):
        a, b = poly[i - 1], poly[i]
        if (a[1] > z) != (b[1] > z) and x < a[0] + (z - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
            ins = not ins
    return ins


def _rank_key(c):
    return (OSM_RANK.get(_osm_class(c["name"]), 9), -max(c["widths_m"]), -_plan_len(c["points_xyz_m"]))


def join_street_pieces(conns, turn_deg, bend_deg, keep_out=()):
    """(new connector list, join records): the JOIN step above"""
    ends = []                                             # (piece index, at_start, x, z)
    for ci, c in enumerate(conns):
        p = c["points_xyz_m"]
        ends += [(ci, True, p[0][0], p[0][2]), (ci, False, p[-1][0], p[-1][2])]
    nodes = []
    for e in ends:
        for nd in nodes:
            if math.hypot(nd[0][2] - e[2], nd[0][3] - e[3]) <= MEET_R_M:
                nd.append(e)
                break
        else:
            nodes.append([e])
    link = {}                                             # (ci, at_start) -> (cj, at_start_j)
    recs = []
    for nd in nodes:
        if len(nd) < 2 or len({e[0] for e in nd}) < len(nd):
            continue
        x, z = nd[0][2], nd[0][3]
        if any(_in_poly(x, z, poly) for poly in keep_out):
            continue
        members = {e[0] for e in nd}
        through = False                                   # another piece passing the node (not ending there)
        for ci, c in enumerate(conns):
            if ci in members:
                continue
            if _project(x, z, c["points_xyz_m"])[0] <= MEET_R_M:
                through = True
                break
        hd = {(e[0], e[1]): _end_heading([tuple(q) for q in conns[e[0]]["points_xyz_m"]], e[1]) for e in nd}
        pairs = sorted(((_turn_deg(hd[(a[0], a[1])], hd[(b[0], b[1])]), a, b) for i, a in enumerate(nd) for b in nd[i + 1:]),
                       key=lambda r: r[0])
        lim = bend_deg if (len(nd) == 2 and not through) else turn_deg
        used = set()
        for t, a, b in pairs:
            if t > lim or (a[0], a[1]) in used or (b[0], b[1]) in used:
                continue
            used |= {(a[0], a[1]), (b[0], b[1])}
            link[(a[0], a[1])] = (b[0], b[1])
            link[(b[0], b[1])] = (a[0], a[1])
            recs.append({"node_xz": [round(x, 2), round(z, 2)], "pieces": [conns[a[0]]["name"], conns[b[0]]["name"]],
                         "turn_deg": round(t, 1), "rule": "bend" if lim == bend_deg and t > turn_deg else "straight"})
    seen, out = set(), []
    for ci in range(len(conns)):
        if ci in seen:
            continue
        # walk to one end of the chain (a cycle is opened where the walk started)
        cur, at_start = ci, True
        start_ci = ci
        while (cur, at_start) in link:
            nxt, nxt_start = link[(cur, at_start)]
            cur, at_start = nxt, not nxt_start
            if cur == start_ci:
                break
        chain = []                                        # (ci, reversed?) walking away from the free end
        cur, from_start = cur, at_start
        while cur not in seen:
            seen.add(cur)
            chain.append((cur, not from_start))
            far = (cur, not from_start)
            if far not in link:
                break
            nxt, nxt_start = link[far]
            cur, from_start = nxt, nxt_start
        if len(chain) == 1:
            out.append(conns[chain[0][0]])
            continue
        pts, ws = [], []
        for k, (cj, rev) in enumerate(chain):
            p = [list(q) for q in conns[cj]["points_xyz_m"]]
            w = list(conns[cj]["widths_m"])
            if rev:
                p, w = p[::-1], w[::-1]
            if pts:
                # the node: the two pieces' ends, which their own 3DEP profiles can leave apart (Quebec's west
                # carriageway: grid_primary_30 ends 0.43 m over grid_primary_6's start). Each side's profile is shifted
                # onto the mean by an offset faded out over BLEND_M from the node (smoothstep, as trim's own blend)
                a, b = pts[-1], p[0]
                ym = (a[1] + b[1]) / 2.0
                for seq, dy in ((pts[::-1], ym - a[1]), (p, ym - b[1])):
                    acc = 0.0
                    for q in range(len(seq)):
                        if q:
                            acc += math.hypot(seq[q][0] - seq[q - 1][0], seq[q][2] - seq[q - 1][2])
                        if acc >= BLEND_M:
                            break
                        seq[q][1] += dy * smoothstep(1.0 - acc / BLEND_M)
                pts[-1] = [(a[0] + b[0]) / 2.0, ym, (a[2] + b[2]) / 2.0]
                p, w = p[1:], w[1:]
            pts += p
            ws += w
        lead = min((conns[cj] for cj, _ in chain), key=_rank_key)
        rec = {k: v for k, v in lead.items() if k not in ("points_xyz_m", "widths_m")}
        rec.update({"points_xyz_m": [[round(v, 3) for v in q] for q in pts], "widths_m": ws,
                    "joined": [conns[cj]["name"] for cj, _ in chain]})
        out.append(rec)
    return out, recs


def merge_forks(conns, forks):
    """PAINT-DIVIDED FORKS (opt-in route.street_junctions.merge_forks, ledger 0079 0.2.3): OSM draws a short approach
    with a painted (flush) median as two one-way pieces leaving one node; on the ground it is ONE asphalt. Each record
    {"pieces": [a, b], "name": .., "edges_m": [[s, left, right], ..]} replaces the two pieces with one: stations at equal
    fractions of each piece from their shared node, s = that fraction x the pieces' mean length; the OSM midline (and
    its height) the two pieces' mean there; the asphalt edges `left` / `right` metres along the midline's normal
    (-dz, dx) of the direction away from the node, as measured off NAIP (interpolated in s, held past either end). The
    centre is the edges' middle, the width their distance. Returns (new list, records)."""
    by = {c["name"]: c for c in conns}
    out, recs, gone = list(conns), [], set()
    for f in forks:
        a, b = (by[n] for n in f["pieces"])
        pa, pb = [tuple(q) for q in a["points_xyz_m"]], [tuple(q) for q in b["points_xyz_m"]]
        ends = [(math.hypot(x[0] - y[0], x[2] - y[2]), ia, ib) for ia, x in ((0, pa[0]), (1, pa[-1]))
                for ib, y in ((0, pb[0]), (1, pb[-1]))]
        d, ia, ib = min(ends)
        if d > MEET_R_M:
            raise SystemExit(f"[trim] merge_forks {f['pieces']}: the pieces share no node ({d:.1f} m apart)")
        pa = pa if ia == 0 else pa[::-1]
        pb = pb if ib == 0 else pb[::-1]
        La, Lb = _plan_len(pa), _plan_len(pb)

        def at(p, s):
            acc = 0.0
            for i in range(1, len(p)):
                L = math.hypot(p[i][0] - p[i - 1][0], p[i][2] - p[i - 1][2])
                if L > 0 and acc + L >= s:
                    t = (s - acc) / L
                    return tuple(p[i - 1][k] + (p[i][k] - p[i - 1][k]) * t for k in range(3))
                acc += L
            return p[-1]
        n = max(len(pa), len(pb))
        mid = []
        for k in range(n):
            fr = k / (n - 1)
            qa, qb = at(pa, fr * La), at(pb, fr * Lb)
            mid.append(((qa[0] + qb[0]) / 2.0, (qa[1] + qb[1]) / 2.0, (qa[2] + qb[2]) / 2.0, fr * (La + Lb) / 2.0))
        tab = sorted(f["edges_m"])

        def edges(s):
            if s <= tab[0][0]:
                return tab[0][1], tab[0][2]
            for (s0, l0, r0), (s1, l1, r1) in zip(tab, tab[1:]):
                if s <= s1:
                    t = (s - s0) / (s1 - s0)
                    return l0 + (l1 - l0) * t, r0 + (r1 - r0) * t
            return tab[-1][1], tab[-1][2]
        pts, ws = [], []
        for k, (x, y, z, s) in enumerate(mid):
            j0, j1 = max(0, k - 1), min(n - 1, k + 1)
            dx, dz = mid[j1][0] - mid[j0][0], mid[j1][2] - mid[j0][2]
            L = math.hypot(dx, dz) or 1.0
            nx, nz = -dz / L, dx / L
            l, r = edges(s)
            c = (l + r) / 2.0
            pts.append([round(x + nx * c, 3), round(y, 3), round(z + nz * c, 3)])
            ws.append(round(r - l, 2))
        rec = {k: v for k, v in b.items() if k not in ("points_xyz_m", "widths_m", "name")}
        rec.update({"name": f.get("name", b["name"]), "points_xyz_m": pts, "widths_m": ws,
                    "fork_merged": [a["name"], b["name"]], "median": "paint"})
        out = [c for c in out if c["name"] not in (a["name"], b["name"])] + [rec]
        gone |= {a["name"], b["name"]}
        recs.append({"pieces": [a["name"], b["name"]], "name": rec["name"], "node_xz": [round(pa[0][0], 2), round(pa[0][2], 2)],
                     "length_m": round((La + Lb) / 2.0, 1), "width_m": [min(ws), max(ws)]})
    return out, recs


def median_crossings(conns, crossings):
    """MEDIAN CROSSINGS (opt-in route.street_junctions.median_crossings, ledger 0079 0.2.3): where a street crosses a
    divided road whose two carriageways OSM draws as two pieces, OSM may end the street at one carriageway and start it
    again at the other, leaving the median between them unpaved in the build. Each record {"between": [a, b], "name": ..,
    "width_m": ..} adds the crossing: a straight piece from a's end to b's end nearest each other (heights linear
    between them, a point every metre), `width_m` wide, kept at any length by trim (`min_piece_m` 0) and welded at both
    ends (tools/weld_mouths_blend.py: each mouth's weld eases over the whole piece, so the two eases sum to one). Returns
    (new list, records)."""
    by = {c["name"]: c for c in conns}
    out, recs = list(conns), []
    for x in crossings:
        a, b = (by[n] for n in x["between"])
        ea = [a["points_xyz_m"][0], a["points_xyz_m"][-1]]
        eb = [b["points_xyz_m"][0], b["points_xyz_m"][-1]]
        d, p, q = min((math.hypot(u[0] - v[0], u[2] - v[2]), u, v) for u in ea for v in eb)
        n = max(2, int(math.ceil(d)) + 1)
        pts = [[round(p[k] + (q[k] - p[k]) * i / (n - 1), 3) for k in range(3)] for i in range(n)]
        name = x.get("name") or f"{a['name']}__{b['name']}"
        out.append({"name": name, "kind": a.get("kind", "connector"), "points_xyz_m": pts,
                    "widths_m": [float(x["width_m"])] * n, "min_piece_m": 0.0, "crossing": [a["name"], b["name"]]})
        recs.append({"name": name, "between": [a["name"], b["name"]], "length_m": round(d, 2), "width_m": x["width_m"]})
    return out, recs


def _seg_cross(p, q, a, b):
    """t along p -> q where it crosses segment a -> b (plan x, z), or None"""
    rx, rz = q[0] - p[0], q[2] - p[2]
    sx, sz = b[0] - a[0], b[1] - a[1]
    den = rx * sz - rz * sx
    if abs(den) < 1e-12:
        return None
    t = ((a[0] - p[0]) * sz - (a[1] - p[2]) * sx) / den
    u = ((a[0] - p[0]) * rz - (a[1] - p[2]) * rx) / den
    return t if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0 else None


def cut_at_pads(conns, pads):
    """PAD ARMS (opt-in route.street_junctions.pad_arms, ledger 0079 0.2.3): a built pad (lm_pads.pads) owns its
    junction box, and its measured deck paves the arms out to the box edge (tools/lm_pads_blend.py). Every street piece
    entering a box is cut where it crosses the box edge, the part inside dropped; the end is an ARM (not a mouth): its
    end row becomes part of the deck's outline in lm_pads (lm_pads.arms "streets"). Returns (pieces, arm records)."""
    out, arms = [], []
    for c in conns:
        pts = [tuple(p) for p in c["points_xyz_m"]]
        w = list(c["widths_m"])
        hit = None
        for pd in pads:
            ins = [_in_poly(p[0], p[2], pd["box"]) for p in pts]
            if any(ins):
                hit = (pd, ins)
                break
        if hit is None:
            # a street that already ENDS on a box edge (the grid's OSM ways stop at the declared arm cut: 50th_dahlia's
            # grid_unclassified_0 and grid_tertiary_44, 2-4 mm off it) is an arm as it stands, its end never reached on
            # into the pad (round G: they were stretched to the lap and stood under the deck). On the edge = within
            # draft_pads.splice_rows' own 0.05 m of "on a cut line"
            out.append(c)
            for end, q in (("start", pts[0]), ("end", pts[-1])):
                for pd in pads:
                    box = [tuple(b) for b in pd["box"]]
                    e = next((e for e in range(len(box)) if _project(q[0], q[2], [(box[e - 1][0], 0, box[e - 1][1]),
                                                                                    (box[e][0], 0, box[e][1])])[0] <= 0.05),
                             None)
                    if e is not None:
                        arms.append({"pad": pd["id"], "connector": c["name"], "cut_xyz": [round(v, 3) for v in q],
                                     "box_edge": [list(box[e - 1]), list(box[e])], "on_edge": True,
                                     "declared_arm": next((a["connector"] for a in pd.get("arms") or []
                                                           if a["connector"] == c["name"]), None)})
                        print(f"[trim] {c['name']} ({end}) ends on pad {pd['id']}'s box edge: an arm as it stands")
                        break
            continue
        pd, ins = hit
        box = [tuple(q) for q in pd["box"]]
        m = len(pts)

        def crossing(i_out, i_in):
            p, q = pts[i_out], pts[i_in]
            for e in range(len(box)):
                t = _seg_cross(p, q, box[e - 1], box[e])
                if t is not None:
                    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, p[2] + (q[2] - p[2]) * t), e
            return None, None
        pieces = []
        i = 0
        while i < m:
            if ins[i]:
                i += 1
                continue
            j = i
            while j < m and not ins[j]:
                j += 1
            piece, pw, ends = list(pts[i:j]), list(w[i:j]), []
            if i > 0:
                cp, e = crossing(i, i - 1)
                piece.insert(0, cp)
                pw.insert(0, w[i])
                ends.append(("start", cp, e))
            if j < m:
                cp, e = crossing(j - 1, j)
                piece.append(cp)
                pw.append(w[j - 1])
                ends.append(("end", cp, e))
            if _plan_len(piece) >= MIN_PIECE_M:
                pieces.append((piece, pw, ends))
            i = j
        for q, (piece, pw, ends) in enumerate(pieces):
            name = f"{c['name']}#{q}" if len(pieces) > 1 or any(ins) else c["name"]
            rec = {k: v for k, v in c.items() if k not in ("name", "points_xyz_m", "widths_m")}
            rec.update({"name": name, "points_xyz_m": [[round(v, 3) for v in p] for p in piece], "widths_m": pw})
            out.append(rec)
            for end, cp, e in ends:
                arms.append({"pad": pd["id"], "connector": c["name"], "cut_xyz": [round(v, 3) for v in cp],
                             "box_edge": [list(box[e - 1]), list(box[e])],
                             "declared_arm": next((a["connector"] for a in pd.get("arms") or []
                                                   if _project(cp[0], cp[2], [(a["cut"][0][0], 0, a["cut"][0][1]),
                                                                              (a["cut"][1][0], 0, a["cut"][1][1])])[0] < 1.0),
                                                  None)})
        print(f"[trim] {c['name']}: cut at pad {pd['id']}'s box ({sum(ins)} pt(s) inside dropped, {len(pieces)} piece(s))")
    return out, arms


def _bbox(pts, pad):
    xs, zs = [p[0] for p in pts], [p[2] for p in pts]
    return min(xs) - pad, min(zs) - pad, max(xs) + pad, max(zs) + pad


def _meeting(g, h, no_reach=()):
    """None if piece g never enters piece h's pavement (or reaches it from an end within REACH_M), else
    "end" (g ends on h's interior: h is the through piece) or "cross" """
    gp, hp = g["points_xyz_m"], h["points_xyz_m"]
    hit = None
    for q, p in enumerate(gp):
        d, half, k, _s = _lateral(p[0], p[2], hp, h["widths_m"])
        endpt = q in (0, len(gp) - 1) and (round(p[0], 3), round(p[2], 3)) not in no_reach
        if d < half - OVERLAP_M or (endpt and d <= half + REACH_M and d >= half - OVERLAP_M):
            _d, i, t = _project(p[0], p[2], hp)
            h_end = (i == 0 and t <= 0.0) or (i == len(hp) - 2 and t >= 1.0)
            if d >= half - OVERLAP_M and h_end:
                continue                                  # a reach toward h's own end is no meeting
            kind = "end" if (q in (0, len(gp) - 1) or q in (1, len(gp) - 2)) and not h_end else "cross"
            if hit != "end":
                hit = kind
    return hit


def rank_trim(pieces, mouths, deltas, capped=(), keep_ends=()):
    """The RANK step above on `pieces` (every piece here a candidate host of every other). Returns the new list and
    the order used [(name, [host names])]."""
    boxes = [_bbox(c["points_xyz_m"], REACH_M + 10.0) for c in pieces]
    cut_ends = {(round(mo["cut_xyz"][0], 3), round(mo["cut_xyz"][2], 3)) for mo in mouths} | set(keep_ends)
    n = len(pieces)
    meet = {}
    for a in range(n):
        for b in range(n):
            if a == b:
                continue
            A, B = boxes[a], boxes[b]
            if A[0] > B[2] or B[0] > A[2] or A[1] > B[3] or B[1] > A[3]:
                continue
            m = _meeting(pieces[a], pieces[b], cut_ends)
            if m:
                meet[(a, b)] = m                          # a enters b
    above = {a: set() for a in range(n)}                  # a must rank below every b in above[a]
    for (a, b), m in meet.items():
        if m == "end" and meet.get((b, a)) != "end":
            above[a].add(b)
    order, placed = [], set()
    pending = set(range(n))
    while pending:
        ready = [a for a in pending if above[a] <= placed]
        if not ready:                                     # a cycle of T's: the hierarchy decides
            ready = list(pending)
        a = min(ready, key=lambda i: _rank_key(pieces[i]))
        order.append(a)
        placed.add(a)
        pending.discard(a)
    rank = {a: r for r, a in enumerate(order)}
    final = {}
    log = []
    for a in order:
        hosts_i = [b for b in range(n) if rank.get(b, n) < rank[a] and ((a, b) in meet or (b, a) in meet)]
        hosts = [(c["name"], [tuple(p) for p in c["points_xyz_m"]], c["widths_m"]) for b in hosts_i for c in final[b]]
        if not hosts:
            final[a] = [pieces[a]]
        else:
            final[a] = _trim_against([pieces[a]], hosts, mouths, deltas, capped=capped,
                                     no_reach={(round(mo["cut_xyz"][0], 3), round(mo["cut_xyz"][2], 3)) for mo in mouths}
                                     | set(keep_ends))
        log.append((pieces[a]["name"], [pieces[b]["name"] for b in hosts_i]))
    return [c for a in order for c in final[a]], log


def build(project_dir):
    proj = Path(project_dir)
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    divided = cfg.get("route", {}).get("divided_connectors", [])
    src = data / "connectors.local.json"
    bak = data / "connectors.local.json.pre-trim"
    if bak.exists():
        conns = json.loads(bak.read_text(encoding="utf-8"))
    else:
        conns = json.loads(src.read_text(encoding="utf-8"))
        bak.write_text(json.dumps(conns), encoding="utf-8")
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    main = [tuple(p) for p in local["points_xyz_m"]]
    mouths = []
    deltas = {}

    sj = (cfg.get("route") or {}).get("street_junctions")
    join_recs, rank_log, arms = [], [], []
    arm_ends = set()
    if sj and sj.get("pad_arms"):
        # opt-in (ledger 0079 0.2.3): a built pad's box is the pad's; streets entering it are cut at its edge (cut_at_pads)
        built_pads = [pd for pd in ((cfg.get("lm_pads") or {}).get("pads") or []) if pd.get("box")]
        conns = dict(conns)
        conns["connectors"], arms = cut_at_pads(conns.get("connectors", []), built_pads)
        arm_ends = {(round(a["cut_xyz"][0], 3), round(a["cut_xyz"][2], 3)) for a in arms}
        print(f"[trim] pad arms: {len(arms)} street end(s) cut at {len(built_pads)} built pad box(es)")
    fork_recs = []
    if sj and sj.get("merge_forks"):
        # opt-in (ledger 0079 0.2.3): a paint-divided approach OSM draws as two one-way pieces is one asphalt (merge_forks)
        conns = dict(conns)
        conns["connectors"], fork_recs = merge_forks(conns.get("connectors", []), sj["merge_forks"])
        for fr in fork_recs:
            print(f"[trim] fork {fr['pieces']} -> one street {fr['name']}: {fr['length_m']} m, width "
                  f"{fr['width_m'][0]}-{fr['width_m'][1]} m (measured edges)")
    if sj:
        # opt-in (ledger 0079 0.2.3; module section STREET-TO-STREET JUNCTIONS): one street's OSM pieces joined first
        keep_out = [[(q[0], q[1]) for q in pd["box"]] for pd in ((cfg.get("lm_pads") or {}).get("pads") or []) if pd.get("box")]
        conns = dict(conns)
        conns["connectors"], join_recs = join_street_pieces(conns.get("connectors", []), float(sj["join_turn_deg"]),
                                                            float(sj["bend_turn_deg"]), keep_out)
        print(f"[trim] street junctions: {len(join_recs)} node(s) joined -> {len(conns['connectors'])} piece(s)")
    cross_recs = []
    if sj and sj.get("median_crossings"):
        # opt-in (ledger 0079 0.2.3): the paved crossing of a divided road's median that OSM leaves out (median_crossings)
        conns["connectors"], cross_recs = median_crossings(conns["connectors"], sj["median_crossings"])
        for cr_ in cross_recs:
            print(f"[trim] median crossing {cr_['name']}: {cr_['between']}, {cr_['length_m']} m node to node, "
                  f"{cr_['width_m']} m wide")

    # pass 1: everything vs the mainline
    capped = [str(x) for x in (cfg.get("route", {}).get("trim_blend_grade_cap") or [])]
    first = _trim_against(conns.get("connectors", []), [("MAINLINE", main, local["widths_m"])], mouths, deltas,
                          capped=capped, **({"no_reach": arm_ends} if arm_ends else {}))
    # pass 2: non-host pieces vs the divided trunks (host = any piece of a divided connector, not its _loop)
    # route.connector_hosts (ledger 0079 round B, Sand Creek's grid): connectors that are HOSTS without being divided — the
    # arterials every other street is cut against (a name, a name#k piece, or a "prefix*"). Absent = the divided trunks
    # alone, as before (Lake Murray declares none)
    plain_hosts = [str(x) for x in (cfg.get("route", {}).get("connector_hosts") or [])]

    def is_host(c):
        return (any(c["name"] == d or c["name"].startswith(d + "#") for d in divided)
                or any(c["name"].startswith(h[:-1]) if h.endswith("*") else (c["name"] == h or c["name"].startswith(h + "#"))
                       for h in plain_hosts))
    if sj:
        # opt-in: the hosts where they meet each other (two arterials) ranked and cut first, so pass 2 reads final hosts
        host_pieces, lg = rank_trim([c for c in first if is_host(c)], mouths, deltas, capped=capped, keep_ends=arm_ends)
        rank_log += lg
        first = host_pieces + [c for c in first if not is_host(c)]
    hosts = [(c["name"], [tuple(p) for p in c["points_xyz_m"]], c["widths_m"]) for c in first if is_host(c)]
    hosts_set = {h[0] for h in hosts}
    rest = [c for c in first if c["name"] not in hosts_set and not any(c["name"].startswith(d + "_loop") for d in divided)]
    loops = [c for c in first if any(c["name"].startswith(d + "_loop") for d in divided)]
    # phase 5 (tools/stub_roads.py, ledger 0054): a stub declared on a CONNECTOR host (an expansion piece) is cut
    # against that host's pieces only — no other connector meets a non-divided host here. None declared: unchanged.
    conn_stubs = [c for c in rest if (c.get("stub") or {}).get("host", "MAINLINE") != "MAINLINE"]
    if conn_stubs:
        rest = [c for c in rest if c not in conn_stubs]
    second = _trim_against(rest, hosts, mouths, deltas, capped=capped,
                           no_reach=({(round(mo["cut_xyz"][0], 3), round(mo["cut_xyz"][2], 3)) for mo in mouths}
                                     | arm_ends if sj else ())) if hosts else rest
    for c in conn_stubs:
        h = c["stub"]["host"]
        hp = [(p["name"], [tuple(q) for q in p["points_xyz_m"]], p["widths_m"]) for p in first
              if p["name"] == h or p["name"].startswith(h + "#")]
        if not hp:
            raise SystemExit(f"[trim] stub {c['name']}: its host {h!r} is not a connector piece")
        second += _trim_against([c], hp, mouths, deltas)
    if sj:
        # opt-in pass 3: where two non-host streets meet (minor / minor), the through piece hosts the other
        second, lg = rank_trim(second, mouths, deltas, capped=capped, keep_ends=arm_ends)
        rank_log += lg
    out = [c for c in first if c["name"] in hosts_set] + loops + second
    resolve_pieces(mouths, out)
    if sj:
        # an ACUTE mouth (a fork: one carriageway leaving another at 13-24 deg) needs its outer lateral lines run on along
        # the host edge further than tools/mouth_weld.py's EXTEND_MAX_M: a line offset o from the piece's centre meets
        # the host edge o / tan(angle) past the centre's cut. o = half the piece's width + its edge strip (route.edge
        # curb_face_w + sidewalk_w + grade_w), so the record carries twice that reach where it passes 25 m [invented
        # bound: the host edge bends away at a fork; grid_unclassified_94 at 16 deg needed over 25 m where the
        # straight-edge reach is 20 m];
        # the weld reads it (tools/weld_mouths_blend.py) and every other mouth keeps EXTEND_MAX_M
        re_ = (cfg.get("route") or {}).get("edge") or {}
        strip = sum(float(re_.get(k) or 0.0) for k in ("curb_face_w", "sidewalk_w", "grade_w"))
        for mo in mouths:
            ang = math.radians(max(1.0, float(mo["angle_deg"])))
            reach = 2.0 * (mo["connector_width_m"] / 2.0 + strip) / math.tan(ang)
            if reach > 25.0:
                mo["extend_max_m"] = round(reach, 1)
                # and (opt-in street_junctions.weld_hold "overlap", ledger 0079 0.2.3; coordinator 2026-11-05) its rows
                # lie on the host deck for the length its ribbon overlaps the host (tools/mouth_weld.py hold_overlap),
                # the 30 m ease starting only past it
                if sj.get("weld_hold") == "overlap":
                    mo["weld_hold"] = "overlap"
        # a median crossing (median_crossings) is a mouth at both ends: each end's weld eases over the piece's whole
        # length with no extra re-spread, so the two smoothsteps sum to one and every row lies between the two decks
        crossing_len = {c["name"]: _plan_len(c["points_xyz_m"]) for c in out if c.get("crossing")}
        for mo in mouths:
            if mo["piece"] in crossing_len:
                mo["weld_blend_m"] = round(crossing_len[mo["piece"]], 3)
                mo["weld_remap_min_m"] = 0.0
    unresolved = [f"{mo['connector']}@{mo['host']}:{mo['host_vertex']}" for mo in mouths if mo["piece"] is None]
    if unresolved:
        print(f"[trim] WARNING: {len(unresolved)} mouth(s) whose piece was dropped (< {MIN_PIECE_M} m): {unresolved}")
        # ledger 0079 round B: a dropped piece has no end to weld, so its mouth is not a mouth (Sand Creek: a frontage road's
        # stub between the lap and a host arterial, cut twice, under 15 m); tools/weld_mouths_blend.py refused the whole set
        # on it. A set with none unresolved (Lake Murray) is untouched
        mouths[:] = [mo for mo in mouths if mo["piece"] is not None]
        print(f"[trim] {len(unresolved)} such mouth(s) left out of mouths.json")

    # island gaps on trunk hosts at every mouth; the trunk's blend applied to its island's heights
    bands_path = data / "median_bands.json"
    if bands_path.exists():
        bands = json.loads(bands_path.read_text(encoding="utf-8"))
        gapped = 0
        for ci in bands.get("connector_islands", []):
            ipts = ci["points_xyz_m"]
            for mo in mouths:
                if not mo["host"].startswith(ci["name"]):
                    continue
                cx, _, cz = mo["cut_xyz"]
                for q, p in enumerate(ipts):
                    if ci["island_w_by_point"][q] > 0 and math.hypot(p[0] - cx, p[2] - cz) <= MOUTH_ISLAND_GAP_M:
                        ci["island_w_by_point"][q] = 0.0
                        gapped += 1
        lifted = apply_island_deltas(bands, deltas)
        bands_path.write_text(json.dumps(bands), encoding="utf-8")
        if gapped:
            print(f"[trim] trunk island gapped on {gapped} point(s) at connector mouths")
        if lifted:
            print(f"[trim] trunk island heights blended with the trunk deck on {lifted} point(s)")

    payload = dict(conns)
    payload["connectors"] = out
    src.write_text(json.dumps(payload), encoding="utf-8")
    (data / "mouths.json").write_text(json.dumps({"mouths": mouths}, indent=1), encoding="utf-8")
    if sj:
        (data / "street_junctions.json").write_text(json.dumps(
            {"_doc": "tools/trim_connectors.py route.street_junctions (ledger 0079 0.2.3): the OSM pieces joined into one "
                     "street at a node, and the order the street-to-street passes cut pieces in (each against the hosts "
                     "named)", "config": sj, "joins": join_recs, **({"forks_merged": fork_recs} if fork_recs else {}),
             "ranked": [{"piece": a_, "hosts": h_} for a_, h_ in rank_log if h_]}, indent=1), encoding="utf-8")
    if sj and sj.get("pad_arms"):
        for a in arms:                                    # the FINAL piece whose end is the arm's cut
            cx, _, cz = a["cut_xyz"]
            a["piece"], a["end"] = next(((c["name"], end) for c in out for end, q in (("start", c["points_xyz_m"][0]),
                                                                                  ("end", c["points_xyz_m"][-1]))
                                         if math.hypot(q[0] - cx, q[2] - cz) <= END_MATCH_M), (None, None))
        (data / "pad_arms.json").write_text(json.dumps(
            {"_doc": "tools/trim_connectors.py route.street_junctions.pad_arms (ledger 0079 0.2.3): every street end cut at a "
                     "built pad's box edge; tools/lm_pads_blend.py (lm_pads.arms streets) welds its end row into the deck",
             "arms": arms}, indent=1), encoding="utf-8")
        lost = [a["connector"] for a in arms if a["piece"] is None]
        print(f"[trim] pad arms: {len(arms) - len(lost)} kept" + (f"; {len(lost)} dropped later: {lost}" if lost else ""))
    hosts_hit = sorted({mo["host"] for mo in mouths})
    print(f"[trim] {len(out)} connector piece(s), {len(mouths)} mouth cut(s) on {hosts_hit} -> connectors.local.json + mouths.json")
    for mo in mouths:
        print(f"[trim] mouth {mo['piece']} ({mo['end']}) -> {mo['host']} seg {mo['host_seg']}+{mo['host_t']:.2f} "
              f"side {mo['side']:+d}: angle {mo['angle_deg']:.1f} deg, host grade {100 * mo['host_grade']:+.2f} %, "
              f"cut y {mo['cut_xyz'][1]:.3f}"
              + (f"; blend {mo['blend_m']:.0f} m, max grade {100 * mo['blend_max_grade']:.1f} % (grade-capped)"
                 if "blend_m" in mo else ""))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/trim_connectors.py <project-dir>")
    build(sys.argv[1])
