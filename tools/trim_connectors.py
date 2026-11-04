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


def _trim_against(conns, hosts, mouths, deltas=None, capped=()):
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
            if plen >= MIN_PIECE_M and len(piece) >= 2:
                pieces.append((piece, pw))
            i = j
        if len(pieces) == 1 and not any(inside):
            out.append(c)
            continue
        for q, (piece, pw) in enumerate(pieces):
            out.append({"name": f"{c['name']}#{q}", "kind": c.get("kind", "connector"),
                        "points_xyz_m": [[round(v, 3) for v in p] for p in piece], "widths_m": pw,
                        **({"stub": c["stub"]} if c.get("stub") else {}),
                        **({"expansion": c["expansion"]} if c.get("expansion") else {})})
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

    # pass 1: everything vs the mainline
    capped = [str(x) for x in (cfg.get("route", {}).get("trim_blend_grade_cap") or [])]
    first = _trim_against(conns.get("connectors", []), [("MAINLINE", main, local["widths_m"])], mouths, deltas,
                          capped=capped)
    # pass 2: non-host pieces vs the divided trunks (host = any piece of a divided connector, not its _loop)
    # route.connector_hosts (ledger 0079 round B, Sand Creek's grid): connectors that are HOSTS without being divided — the
    # arterials every other street is cut against (a name, a name#k piece, or a "prefix*"). Absent = the divided trunks
    # alone, as before (Lake Murray declares none)
    plain_hosts = [str(x) for x in (cfg.get("route", {}).get("connector_hosts") or [])]

    def is_host(c):
        return (any(c["name"] == d or c["name"].startswith(d + "#") for d in divided)
                or any(c["name"].startswith(h[:-1]) if h.endswith("*") else (c["name"] == h or c["name"].startswith(h + "#"))
                       for h in plain_hosts))
    hosts = [(c["name"], [tuple(p) for p in c["points_xyz_m"]], c["widths_m"]) for c in first if is_host(c)]
    hosts_set = {h[0] for h in hosts}
    rest = [c for c in first if c["name"] not in hosts_set and not any(c["name"].startswith(d + "_loop") for d in divided)]
    loops = [c for c in first if any(c["name"].startswith(d + "_loop") for d in divided)]
    # phase 5 (tools/stub_roads.py, ledger 0054): a stub declared on a CONNECTOR host (an expansion piece) is cut
    # against that host's pieces only — no other connector meets a non-divided host here. None declared: unchanged.
    conn_stubs = [c for c in rest if (c.get("stub") or {}).get("host", "MAINLINE") != "MAINLINE"]
    if conn_stubs:
        rest = [c for c in rest if c not in conn_stubs]
    second = _trim_against(rest, hosts, mouths, deltas, capped=capped) if hosts else rest
    for c in conn_stubs:
        h = c["stub"]["host"]
        hp = [(p["name"], [tuple(q) for q in p["points_xyz_m"]], p["widths_m"]) for p in first
              if p["name"] == h or p["name"].startswith(h + "#")]
        if not hp:
            raise SystemExit(f"[trim] stub {c['name']}: its host {h!r} is not a connector piece")
        second += _trim_against([c], hp, mouths, deltas)
    out = [c for c in first if c["name"] in hosts_set] + loops + second
    resolve_pieces(mouths, out)
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
