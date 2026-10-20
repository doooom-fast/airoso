"""The north network's DRIVE LINES for drive_test --line expansion (ledger 0054 P3 step 7; EXPANSION-PLAN V6).

drive_test walks the mainline only; without this 10.8 of 24.3 km of drivable road would never be swept (Risk 10). Two
lines, one per direction, each the RIGHT-HAND carriageway of travel (US traffic) — its centre and its width, curb (or
the parking / bike line's curb) to the median's face (or the centre line) — strung end to end through the network:

  fwd  J1 -> Waring -> J2 -> Princess View -> J3 -> Mission Gorge -> J4 -> Jackson north -> J5  (every turn a right)
  rev  J5 -> Jackson north -> J4 -> Mission Gorge -> J3 -> Princess View -> J2 -> Waring -> J1

Each piece's part is read off the connector as trim left it (data/connectors.local.json: its points, its width) and the
intermediate's per-station median (the carriageway stops at the raised or painted median's face, MEDIAN_CLEAR_M off it;
an undivided road's at its centre line); through each pad the line turns on a cubic curve tangent to both arms' lane
lines (the right turn a car makes there), its width eased between theirs. The welds' first PAD_IN_M of the loop are not
part of it: the mouths are verify_mouths' (on the same built road). Wheel paths, steps, obstructions: drive_test's own.

THE TURN STAYS INSIDE THE CURB (ledger 0054 P3 repair round 1, the gates lens): a cubic between two lane lines is the
centre of the turn, not its edges — at J2 / J3 / J4 the carriageway it carried (12-16 m, eased between the arms') put
the right-hand wheel paths of every right turn up the pad's curb return (kinks of 10-17 %-points at s ~960, ~2060,
~4320 on the forward line: a wheel climbing a 0.14 m curb, not the deck). Where the pads are built
(data/pads.built.json: each deck's outline, its 'edge' runs = the curb faces), every line point casts a ray to each
side; a carriageway edge within CURB_CLEAR_M of a curb face is pulled back to it (the other edge stays), the width
never under MIN_W_M, and each edge eased into it over EASE_PTS points (never past the face) so the line never jogs. Only the pads' curbs
are read: a piece's own curbs are its carriageway already.

    python tools/expansion_lines.py <project-dir>       -> data/drive_lines.expansion.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import expansion_pieces as ep  # noqa: E402

MEDIAN_CLEAR_M = 0.3       # [invented] the carriageway's inner edge stands this far off a median face / centre line
EASE_M = 15.0              # [invented] the line's offset and width are eased over +- this along the road (a median nose
                           # that starts in one 3 m station would otherwise jog the line 1.5 m sideways at once — and a
                           # jogging line's cross-section reads the road's own 10 % grade as a step)
STEP_M = 3.0               # the lines' point spacing (the connectors' own)
ORDER = ["A", "B", "C", "D"]   # J order: J1 -A- J2 -B- J3 -C- J4 -D- J5
CURB_CLEAR_M = 0.5         # [invented] a carriageway edge stands this far inside a pad's curb face (drive_test's edge
#                            wheel path runs 0.25 m past the edge it is given: it then stays 0.25 m off the face)
MIN_W_M = 6.0              # [invented] ...never narrower than this (one 3.6 m lane + its edge paths)
EASE_PTS = 4               # [invented] each edge's pulled-back half-width eases over +- this many line points
RAY_PAD_M = 1.0            # a curb face is looked for out to the edge + this


def carriageway(pc, s, side):
    """(offset of the carriageway centre, its width) at piece station s, side -1 = right of J-order travel (fwd),
    +1 = left (rev), in the PIECE frame (+ = left)"""
    L, R = pc.curbs(s)
    mtype = pc.near(s, "median_type")
    mw = pc.num(s, "median_w_m") if mtype not in ("none", "line") else 0.0
    moff = pc.num(s, "median_off_m")
    inner = moff + side * (mw / 2.0 + MEDIAN_CLEAR_M)
    outer = L if side > 0 else R
    return (inner + outer) / 2.0, abs(outer - inner)


def piece_lane(conn, pc, side):
    """[(x, y, z)], [width] along one connector piece's carriageway on `side`, in the CONNECTOR's own order"""
    P = conn["points_xyz_m"]
    out, ws = [], []
    n = len(P)
    for i, p in enumerate(P):
        a, b = P[max(0, i - 1)], P[min(n - 1, i + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        Lt = math.hypot(tx, tz) or 1.0
        _d, s, lat = pc.project(p[0], p[2])
        pt = pc.tangent(s)
        sense = 1.0 if (tx * pt[0] + tz * pt[1]) >= 0 else -1.0
        off, w = carriageway(pc, s, side)
        o = sense * (off - lat)                          # in the connector's frame
        out.append((o, (-tz / Lt, tx / Lt)))
        ws.append(w)
    arc = [0.0]
    for a, b in zip(P, P[1:]):
        arc.append(arc[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    pts, wout = [], []
    for i, p in enumerate(P):
        js = [j for j in range(n) if abs(arc[j] - arc[i]) <= EASE_M]
        o = sum(out[j][0] for j in js) / len(js)
        w = min(ws[j] for j in js)
        nx, nz = out[i][1]
        pts.append((p[0] + nx * o, p[1], p[2] + nz * o))
        wout.append(w)
    return pts, wout


def bezier(p0, t0, p1, t1, n):
    """n+1 points of the cubic leaving p0 along t0 and arriving at p1 along t1 (handles a third of the chord)"""
    d = math.dist((p0[0], p0[2]), (p1[0], p1[2])) / 3.0
    c0 = (p0[0] + t0[0] * d, p0[2] + t0[1] * d)
    c1 = (p1[0] - t1[0] * d, p1[2] - t1[1] * d)
    out = []
    for k in range(n + 1):
        u = k / n
        a, b, c, e = (1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u * u * (1 - u), u ** 3
        x = a * p0[0] + b * c0[0] + c * c1[0] + e * p1[0]
        z = a * p0[2] + b * c0[1] + c * c1[1] + e * p1[2]
        y = p0[1] + (p1[1] - p0[1]) * (3 * u * u - 2 * u * u * u)
        out.append((x, y, z))
    return out


def _dir(pts, at_end):
    a, b = (pts[-2], pts[-1]) if at_end else (pts[0], pts[1])
    dx, dz = b[0] - a[0], b[2] - a[2]
    L = math.hypot(dx, dz) or 1.0
    return dx / L, dz / L


def _ray_hit(px, pz, dx, dz, segs, reach):
    """distance along the ray (px, pz) + t (dx, dz) to the first segment in segs, within reach; None"""
    best = None
    for (ax, az), (bx, bz) in segs:
        ex, ez = bx - ax, bz - az
        den = dx * ez - dz * ex
        if abs(den) < 1e-12:
            continue
        t = ((ax - px) * ez - (az - pz) * ex) / den
        u = ((ax - px) * dz - (az - pz) * dx) / den
        if 0.0 <= u <= 1.0 and 0.0 <= t <= reach and (best is None or t < best):
            best = t
    return best


def curb_segments(pads_built):
    """the pads' curb faces: every outline segment whose two ends are both 'edge' vertices"""
    segs = []
    for pad in (pads_built or {}).get("pads", []):
        O, K = pad["outline_xz"], pad["kind"]
        n = len(O)
        for i in range(n):
            j = (i + 1) % n
            if K[i] == "edge" and K[j] == "edge":
                segs.append((tuple(O[i]), tuple(O[j])))
    return segs


def keep_inside_curbs(P, W, segs):
    """(P, W, n_pulled): the line points and widths with every carriageway edge kept CURB_CLEAR_M inside the pads'
    curb faces (see the module doc); P [(x, y, z)], W [width]; nothing moves where no edge comes near a face"""
    if not segs:
        return list(P), list(W), 0
    n = len(P)
    cell = 20.0
    grid = {}
    for k, (a, b) in enumerate(segs):
        for gx in range(int(math.floor(min(a[0], b[0]) / cell)), int(math.floor(max(a[0], b[0]) / cell)) + 1):
            for gz in range(int(math.floor(min(a[1], b[1]) / cell)), int(math.floor(max(a[1], b[1]) / cell)) + 1):
                grid.setdefault((gx, gz), []).append(k)
    lbs, rbs, pulled = [w / 2.0 for w in W], [w / 2.0 for w in W], [False] * n
    for i in range(n):
        a, b = P[max(0, i - 1)], P[min(n - 1, i + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / L, tx / L                      # left of travel
        half = W[i] / 2.0
        reach = half + RAY_PAD_M
        x, z = P[i][0], P[i][2]
        near = set()
        r = int(math.ceil(reach / cell))
        for gx in range(int(math.floor(x / cell)) - r, int(math.floor(x / cell)) + r + 1):
            for gz in range(int(math.floor(z / cell)) - r, int(math.floor(z / cell)) + r + 1):
                near.update(grid.get((gx, gz), ()))
        if not near:
            continue
        cand = [segs[k] for k in near]
        lb, rb = half, half
        dl = _ray_hit(x, z, nx, nz, cand, reach)
        dr = _ray_hit(x, z, -nx, -nz, cand, reach)
        if dl is not None:
            lb = min(lb, dl - CURB_CLEAR_M)
        if dr is not None:
            rb = min(rb, dr - CURB_CLEAR_M)
        if lb + rb < MIN_W_M:                          # keep the width; split the shortfall off the freer side
            short = MIN_W_M - (lb + rb)
            if lb >= rb:
                lb += short
            else:
                rb += short
        if lb < half - 1e-6 or rb < half - 1e-6:
            pulled[i] = True
            lbs[i], rbs[i] = lb, rb
    if not any(pulled):
        return list(P), list(W), 0

    # ease: each edge's half-width is the lesser of its own bound and its +- EASE_PTS moving average, so a face is never
    # crossed (a pulled point keeps at most its bound) and the neighbours ease into it (the line never jogs)
    def eased(v):
        out = []
        for i in range(n):
            js = range(max(0, i - EASE_PTS), min(n, i + EASE_PTS + 1))
            if not any(pulled[j] for j in js):
                out.append(v[i])            # no face near: exactly as before
                continue
            out.append(min(v[i], sum(v[j] for j in js) / len(js)))
        return out
    lbe, rbe = eased(lbs), eased(rbs)
    so = [(lbe[i] - rbe[i]) / 2.0 for i in range(n)]
    sw = [lbe[i] + rbe[i] for i in range(n)]
    out = []
    for i in range(n):
        a, b = P[max(0, i - 1)], P[min(n - 1, i + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / L, tx / L
        out.append((P[i][0] + nx * so[i], P[i][1], P[i][2] + nz * so[i]))
    return out, sw, sum(pulled)


def build(proj):
    proj = Path(proj)
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    src = (((cfg.get("route") or {}).get("route_connectors") or {}).get("authored_routes") or {}).get("north")
    out_p = data / "drive_lines.expansion.json"
    if not src:
        if out_p.exists():
            out_p.unlink()
        print("[lines] no north route: nothing written")
        return None
    doc, pieces = ep.load(proj / src)
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    by_piece = {}
    for c in conns:
        base = c["name"].split("#")[0]
        for pid, nm in ep.PIECE_CONN.items():
            if base == nm:
                by_piece.setdefault(pid, []).append(c)
    if sorted(by_piece) != ORDER or any(len(v) != 1 for v in by_piece.values()):
        raise SystemExit(f"[lines] FATAL: expected one connector per north piece, got "
                         f"{ {k: [c['name'] for c in v] for k, v in by_piece.items()} }")
    lines = {}
    for name, side, order in (("fwd", -1, ORDER), ("rev", +1, ORDER[::-1])):
        segs = []
        for pid in order:
            c = by_piece[pid][0]
            pts, ws = piece_lane(c, pieces[pid], side)
            # travel order: J order for fwd, against it for rev; the connector's own order may be reversed (D)
            pc = pieces[pid]
            _d0, s0, _l0 = pc.project(c["points_xyz_m"][0][0], c["points_xyz_m"][0][2])
            _d1, s1, _l1 = pc.project(c["points_xyz_m"][-1][0], c["points_xyz_m"][-1][2])
            j_order = s1 > s0
            if j_order != (name == "fwd"):
                pts, ws = pts[::-1], ws[::-1]
            segs.append((pid, pts, ws))
        P, W, parts = [], [], []
        for k, (pid, pts, ws) in enumerate(segs):
            if k > 0:
                q0, w0 = P[-1], W[-1]
                q1, w1 = pts[0], ws[0]
                t0, t1 = _dir(P, True), _dir(pts, False)
                n = max(4, int(math.ceil(math.dist((q0[0], q0[2]), (q1[0], q1[2])) / STEP_M)))
                cur = bezier(q0, t0, q1, t1, n)[1:-1]
                for j, q in enumerate(cur):
                    f = (j + 1) / (len(cur) + 1)
                    P.append(q)
                    W.append(w0 + (w1 - w0) * f)
                    parts.append("pad")
            P += list(pts)
            W += list(ws)
            parts += [pid] * len(pts)
        pb = data / "pads.built.json"
        segs = curb_segments(json.loads(pb.read_text(encoding="utf-8"))) if pb.exists() else []
        P, W, n_pull = keep_inside_curbs(P, W, segs)
        lines[name] = {"points_xyz_m": [[round(v, 3) for v in q] for q in P], "widths_m": [round(w, 3) for w in W],
                       "parts": parts, "curb_pulled_points": n_pull}
        L = sum(math.dist((a[0], a[2]), (b[0], b[2])) for a, b in zip(P, P[1:]))
        print(f"[lines] {name}: {len(P)} pts, {L / 1000:.2f} km, carriageway {min(W):.1f}-{max(W):.1f} m, "
              f"{n_pull} point(s) kept {CURB_CLEAR_M} m inside a pad curb")
    out_p.write_text(json.dumps({"_doc": "tools/expansion_lines.py (ledger 0054 P3 step 7): the north network's "
                                         "right-hand carriageway per direction, for drive_test --line expansion",
                                 "frame": "local = engine (x E, y up, z N), the gate OBJ's", "lines": lines}),
                     encoding="utf-8")
    return lines


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/expansion_lines.py <project-dir>")
    build(sys.argv[1])
