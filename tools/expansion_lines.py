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
        lines[name] = {"points_xyz_m": [[round(v, 3) for v in q] for q in P], "widths_m": [round(w, 3) for w in W],
                       "parts": parts}
        L = sum(math.dist((a[0], a[2]), (b[0], b[2])) for a, b in zip(P, P[1:]))
        print(f"[lines] {name}: {len(P)} pts, {L / 1000:.2f} km, carriageway {min(W):.1f}-{max(W):.1f} m")
    out_p.write_text(json.dumps({"_doc": "tools/expansion_lines.py (ledger 0054 P3 step 7): the north network's "
                                         "right-hand carriageway per direction, for drive_test --line expansion",
                                 "frame": "local = engine (x E, y up, z N), the gate OBJ's", "lines": lines}),
                     encoding="utf-8")
    return lines


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/expansion_lines.py <project-dir>")
    build(sys.argv[1])
