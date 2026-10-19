"""Ledger 0054 P3 (EXPANSION-PLAN P3 step 1, step 4 islands, step 5 paint): the north network's four road pieces as
connectors, from the readable intermediate (data/expansion.north.json, tools/author_expansion.py) — the whole pieces,
not only P1's two weld stubs.

THE PIECES. Each piece of the intermediate (A Waring J1 -> J2, B Princess View J2 -> J3, C Mission Gorge J3 -> J4,
D Jackson north J4 -> J5) becomes ONE connector record in the connector form tools/route_connectors.py takes:
  * the centre is the PAVEMENT MIDLINE — the piece's station point offset by (left curb + right curb) / 2 along its
    left normal — and the width is left - right, curb to curb (A3: the aerial eye readings, interpolated per station;
    never the connector tool's constant 10 m, never the automatic width walker). The assembler sweeps the ribbon
    symmetric about that centre, so its two edges land on the authored curbs;
  * a piece with a WELD end (A at J1, D at J5) starts with P1's weld connector (welds[].connector: from 6 m inside the
    loop's edge, the flare onto the loop's outer edge, the regular section out to 100 m) and runs on along the piece;
    D is therefore oriented J5 -> J4 (both welded pieces START at their mouth: tools/author_aprons_blend.py takes only a
    piece that starts at its cut);
  * a PAD end (J2, J3, J4) ends exactly at the pad's arm cut — the cut of tools/junction_pad.design_pads (the arm
    the line tangent to the piece at its cut, the corners re-filleted; the intermediate's pieces[].cuts moved 0.6-2.3 m)
    — and tools/author_junction_pad_blend.py welds the pad onto the arm's last row as the mesh has it;
  * points every RESAMPLE_M (route_connectors' 3 m) along the piece, the last one exactly on the cut;
  * the height: the piece's own 3DEP profile (stations y_3dep, node to node) through a local QUADRATIC fit over
    +- PROFILE_HALF_M (tricube weights) — not route_connectors' two 75 m running means, whose window is one-sided at a
    piece's end and lifts a 10 % descent's end by ~2 m (Princess View into J3; measured on the intermediate). The 11 %
    cap is checked here and reported, never applied blind (A6: it must bind nowhere).

DECORATE (after trim_connectors, before the second terrain plan; `decorate`): per point of every north piece as trim
left it, the paint (connector record `paint`, scripts-v021 ribbon.paint_markings) and the raised medians
(data/median_bands.json connector_islands, named after the piece so every consumer that matches an island to its
host by name — verify_mouths, median_zone, weld_mouths — finds it). Paint per road (EXPANSION-PLAN P3 step 5, the
intermediate's pieces[].paint, dossier §2):
  A Waring, C Mission Gorge  raised median: a yellow edge line MEDIAN_EDGE_M off each median face; the median's
                             painted approach where the raised island stops (double yellow round it); white dashed
                             lane lines; a bike lane each side (solid white BIKE_LINE_M from the curb)
  B Princess View            double yellow on the centre line (the Fontaine nose MD2 stands on it), lane lines,
                             a parking lane each side (solid white PARKING_LINE_M from the curb)
  D Jackson north            the painted median: a double yellow on each of its faces (the double-double yellow), a
                             plain double yellow where it narrows under PLAIN_DOUBLE_UNDER_M, hatched (diagonal yellow
                             strokes every HATCH_EVERY_M) on its last ~170 m into J4; lane lines; buffered bike lanes
                             (solid white at BIKE_LINE_M and BIKE_LINE_M + BUFFER_M from the curb)
Lanes per direction: A 2 (OSM 3 at the turn pockets), B 2 + 2 then 3 downhill on the last 614 m, C 3 + 3, D 2 + 2
(the intermediate's pieces[].paint); never narrower than LANE_MIN_M (a lane line that would make one is dropped).

    python tools/expansion_pieces.py decorate <project-dir>
    python tools/expansion_pieces.py show <intermediate.json>        (the four connectors' summary; no writes)

Every number marked [invented] is in fleet/GATES-CHANGELOG.md (2026-10-18, P3).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

RESAMPLE_M = 3.0            # tools/route_connectors.py RESAMPLE_M (the connector form)
PROFILE_HALF_M = 30.0       # [invented] the profile's local quadratic fit reaches this far each side (tricube weights)
MAX_GRADE = 0.11            # tools/route_connectors.py MAX_GRADE (A6: checked, never applied blind)
PIECE_CONN = {"A": "north_J1_waring", "B": "north_princess_view", "C": "north_mission_gorge",
              "D": "north_J5_jackson_north"}
REVERSED = {"D"}            # D runs J5 -> J4: both welded pieces start at their mouth
PREFIX = "north_"
# paint [invented unless noted]
LINE_W_M = 0.12             # scripts-v021 ribbon.lane_markings line_w
DOUBLE_HALF_M = 0.09        # ribbon.lane_markings: the double yellow's two lines at +-0.09
MEDIAN_EDGE_M = 0.30        # [invented] a yellow edge line this far off a raised median's face
BIKE_LINE_M = 1.80          # [invented] a bike lane's solid white line this far from the curb (lane + gutter pan)
BUFFER_M = 0.90             # [invented] Jackson's buffered bike lane: the buffer's second line this far further in
PARKING_LINE_M = 2.40       # [invented] Princess View's parking lane line this far from the curb (8 ft)
PAIR_IN_M = 0.24            # [invented] a painted median face's double yellow: lines at the face - 0.06 and - 0.30
PLAIN_DOUBLE_UNDER_M = 1.0  # [invented] a painted median narrower than this is painted as one double yellow
HATCH_EVERY_M = 6.0         # [invented] the J4 approach's hatching: a diagonal stroke every this along the road
LANE_MIN_M = 2.9            # [invented] no lane line that would leave a lane narrower than this
LANES = {"A": (2, 2), "B": (2, 2), "C": (3, 3), "D": (2, 2)}   # (fwd = right of J-order travel, rev)
B_THIRD_LANE_FROM_S = 496.0  # "3 + 2 on the last 614 m" of Princess View (1110 - 614): the third lane downhill (fwd)
RAISED = ("planted", "terracotta", "nose")
PAINTED = ("painted", "hatched")


def _dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


class Piece:
    """a piece of the intermediate: station rows, interpolation by station s, the profile fit"""

    def __init__(self, rec):
        self.id = rec["id"]
        self.rec = rec
        cols = rec["columns"]
        self.rows = [dict(zip(cols, r)) for r in rec["stations"]]
        self.s = [float(r["s"]) for r in self.rows]
        self.P = [(float(r["x"]), float(r["z"])) for r in self.rows]
        self.length = self.s[-1]
        self.cuts = rec.get("cuts") or {}

    def _seg(self, s):
        s = max(self.s[0], min(self.s[-1], s))
        lo, hi = 0, len(self.s) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.s[mid] <= s:
                lo = mid
            else:
                hi = mid
        L = self.s[hi] - self.s[lo]
        return lo, hi, (0.0 if L < 1e-12 else (s - self.s[lo]) / L)

    def num(self, s, key):
        lo, hi, t = self._seg(s)
        a, b = float(self.rows[lo][key] or 0.0), float(self.rows[hi][key] or 0.0)
        return a + (b - a) * t

    def near(self, s, key):
        lo, hi, t = self._seg(s)
        return self.rows[lo if t < 0.5 else hi][key]

    def point(self, s):
        lo, hi, t = self._seg(s)
        a, b = self.P[lo], self.P[hi]
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

    def tangent(self, s, h=2.5):
        a, b = self.point(s - h), self.point(s + h)
        L = _dist(a, b) or 1.0
        return ((b[0] - a[0]) / L, (b[1] - a[1]) / L)

    def frame(self, s):
        """(point, unit tangent, left normal) at s"""
        t = self.tangent(s)
        return self.point(s), t, (-t[1], t[0])

    def curbs(self, s):
        return self.num(s, "left_m"), self.num(s, "right_m")

    def project(self, x, z):
        """(distance, station s, signed lateral + = left) of (x, z) onto the station polyline"""
        best = None
        for i in range(len(self.P) - 1):
            a, b = self.P[i], self.P[i + 1]
            dx, dz = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dz * dz
            if L2 < 1e-12:
                continue
            t = max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / L2))
            q = (a[0] + t * dx, a[1] + t * dz)
            d = math.hypot(x - q[0], z - q[1])
            if best is None or d < best[0]:
                L = math.sqrt(L2)
                best = (d, self.s[i] + t * (self.s[i + 1] - self.s[i]), (-dz * (x - a[0]) + dx * (z - a[1])) / L)
        return best

    def y_fit(self, s, half=PROFILE_HALF_M):
        """the 3DEP profile through a tricube-weighted local quadratic fit at s (s outside [0, length]: the fit at the
        nearest end, extended along its own slope)"""
        sc = max(self.s[0], min(self.s[-1], s))
        X, Y, W = [], [], []
        for si, r in zip(self.s, self.rows):
            u = abs(si - sc) / half
            if u >= 1.0:
                continue
            X.append(si - sc)
            Y.append(float(r["y_3dep"]))
            W.append((1.0 - u ** 3) ** 3)
        # weighted least squares y = a + b x + c x^2 (normal equations)
        S = [[0.0] * 3 for _ in range(3)]
        R = [0.0] * 3
        for x, y, w in zip(X, Y, W):
            v = (1.0, x, x * x)
            for i in range(3):
                R[i] += w * v[i] * y
                for j in range(3):
                    S[i][j] += w * v[i] * v[j]
        a, b, _c = _solve3(S, R)
        return a + b * (s - sc)


def _solve3(A, b):
    M = [row[:] + [bb] for row, bb in zip(A, b)]
    for c in range(3):
        p = max(range(c, 3), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12:
            raise ValueError("singular profile fit")
        for r in range(3):
            if r != c:
                f = M[r][c] / M[c][c]
                for k in range(c, 4):
                    M[r][k] -= f * M[c][k]
    return [M[i][3] / M[i][i] for i in range(3)]


def load(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return doc, {p["id"]: Piece(p) for p in doc["pieces"]}


def _weld_of(doc, pid):
    return next((w for w in doc.get("welds", []) if w["piece"] == pid), None)


_DESIGN = {}


def pad_cuts(doc, pieces):
    """{(piece, 'start' | 'end'): the pad cut's station} as tools/junction_pad.design_pads finds it (each route arm the
    line tangent to its piece at the cut, the corners re-filleted, the cut where the piece's own station lands on it)"""
    key = id(doc)
    if key not in _DESIGN:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import junction_pad as jp
        d = jp.design_pads(doc, pieces)
        _DESIGN[key] = {(a["piece"], a["piece_end"]): float(a["cut_s"]) for pad in d.values() for a in pad["arms"]
                        if a["kind"] == "route"}
    return _DESIGN[key]


def piece_connector(doc, pieces, pid):
    """the connector record of piece pid (module doc): {name, kind, points_xyz_m, widths_m, expansion}"""
    pc = pieces[pid]
    rev = pid in REVERSED
    weld = _weld_of(doc, pid)
    cuts = {k: dict(v) for k, v in pc.cuts.items()}
    for end in ("start", "end"):                                   # a pad end: the redesigned pad's cut station
        pcut = pad_cuts(doc, pieces).get((pid, end))
        if pcut is not None and cuts.get(end, {}).get("kind") == "pad":
            cuts[end]["s"] = pcut
    s_far = float(cuts["end" if not rev else "start"]["s"])        # the pad cut at the far end
    pts, widths, parts = [], [], []
    if weld is not None:
        wc = weld["connector"]
        for p, w in zip(wc["points_xyz_m"], wc["widths_m"]):
            pts.append((float(p[0]), float(p[2])))
            widths.append(float(w))
            parts.append("weld")
        _d, s0, _lat = pc.project(*pts[-1])
    else:
        s0 = float(cuts["start" if not rev else "end"]["s"])
        pts.append(None)
    step = RESAMPLE_M if s_far > s0 else -RESAMPLE_M
    span = abs(s_far - s0)
    n = max(1, int(math.ceil(span / RESAMPLE_M - 1e-9)))
    ss = [s0 + (s_far - s0) * k / n for k in range(n + 1)]
    if weld is not None:
        ss = ss[1:]
    else:
        pts.pop()
    for s in ss:
        p, _t, nrm = pc.frame(s)
        L, R = pc.curbs(s)
        c = (L + R) / 2.0
        pts.append((p[0] + nrm[0] * c, p[1] + nrm[1] * c))
        widths.append(L - R)
        parts.append("piece")
    # heights: the piece's profile fit at each point's station
    ys = []
    for x, z in pts:
        _d, s, _lat = pc.project(x, z)
        ys.append(pc.y_fit(s))
    del step
    return {"name": PIECE_CONN[pid], "kind": "connector",
            "points_xyz_m": [[round(x, 3), round(y, 3), round(z, 3)] for (x, z), y in zip(pts, ys)],
            "widths_m": [round(w, 3) for w in widths],
            "expansion": {"route": "north", "piece": pid, "reverse": rev, "far_cut_s": round(s_far, 3),
                          "weld_points": sum(1 for q in parts if q == "weld")}}


def grade_report(conn):
    p = conn["points_xyz_m"]
    g, at = 0.0, None
    for a, b in zip(p, p[1:]):
        L = math.hypot(b[0] - a[0], b[2] - a[2])
        if L > 1e-6 and abs(b[1] - a[1]) / L > g:
            g, at = abs(b[1] - a[1]) / L, (a[0], a[2])
    return g, at


# ------------------------------------------------------------------------------------------------ decorate

def _lanes(pid, s, side):
    """lanes on `side` (+1 = left of J-order travel = the reverse carriageway, -1 = right = forward)"""
    f, r = LANES[pid]
    if pid == "B" and s >= B_THIRD_LANE_FROM_S:
        f = 3
    return f if side < 0 else r


def layout(pc, s, island_runs):
    """the paint lines at piece station s, in the PIECE frame (+ = left of J-order travel): [(key, offset, color,
    dash)] — the key names a continuous line"""
    pid = pc.id
    L, R = pc.curbs(s)
    mtype = pc.near(s, "median_type")
    mw = pc.num(s, "median_w_m") if mtype not in ("none", "line") else 0.0
    moff = pc.num(s, "median_off_m")
    on_island = any(a <= s <= b for a, b in island_runs)
    out = []
    # the centre
    if mtype in RAISED and mw > 0.0:
        if on_island:
            out.append(("med_edge_L", moff + mw / 2.0 + MEDIAN_EDGE_M, "yellow", False))
            out.append(("med_edge_R", moff - mw / 2.0 - MEDIAN_EDGE_M, "yellow", False))
            inner = (moff + mw / 2.0 + MEDIAN_EDGE_M, moff - mw / 2.0 - MEDIAN_EDGE_M)
        else:   # the raised island's painted approach: a double yellow round its outline
            out += [("pm_L1", moff + mw / 2.0 - 0.06, "yellow", False), ("pm_L2", moff + mw / 2.0 - 0.06 - PAIR_IN_M, "yellow", False),
                    ("pm_R1", moff - mw / 2.0 + 0.06, "yellow", False), ("pm_R2", moff - mw / 2.0 + 0.06 + PAIR_IN_M, "yellow", False)]
            inner = (moff + mw / 2.0, moff - mw / 2.0)
    elif mtype in PAINTED and mw >= PLAIN_DOUBLE_UNDER_M:
        out += [("pm_L1", moff + mw / 2.0 - 0.06, "yellow", False), ("pm_L2", moff + mw / 2.0 - 0.06 - PAIR_IN_M, "yellow", False),
                ("pm_R1", moff - mw / 2.0 + 0.06, "yellow", False), ("pm_R2", moff - mw / 2.0 + 0.06 + PAIR_IN_M, "yellow", False)]
        inner = (moff + mw / 2.0, moff - mw / 2.0)
    else:
        out += [("dy_L", moff + DOUBLE_HALF_M, "yellow", False), ("dy_R", moff - DOUBLE_HALF_M, "yellow", False)]
        inner = (moff + DOUBLE_HALF_M + 0.06, moff - DOUBLE_HALF_M - 0.06)
    # the edges (per side) and the lane lines
    for side, curb, inn in ((1, L, inner[0]), (-1, R, inner[1])):
        tag = "L" if side > 0 else "R"
        if pid in ("A", "C"):
            edge = curb - side * BIKE_LINE_M
            out.append((f"bike_{tag}", edge, "white", False))
        elif pid == "B":
            edge = curb - side * PARKING_LINE_M
            out.append((f"park_{tag}", edge, "white", False))
        else:
            out.append((f"bike_{tag}", curb - side * BIKE_LINE_M, "white", False))
            edge = curb - side * (BIKE_LINE_M + BUFFER_M)
            out.append((f"buf_{tag}", edge, "white", False))
        width = (edge - inn) * side
        n = _lanes(pid, s, side)
        while n > 1 and width / n < LANE_MIN_M:
            n -= 1
        for k in range(1, n):
            out.append((f"lane_{tag}{k}", inn + side * width * k / n, "white", True))
    return out


def decorate(proj):
    proj = Path(proj)
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    rc = (cfg.get("route") or {}).get("route_connectors") or {}
    src = (rc.get("authored_routes") or {}).get("north")
    take = [str(x) for x in ((rc.get("authored_take") or {}).get("north") or [])]
    if not src or not any(t in PIECE_CONN for t in take):
        print("[pieces] no north piece taken (route_connectors.authored_take) - nothing to decorate")
        return None
    doc, pieces = load(proj / src)
    cp = data / "connectors.local.json"
    cdoc = json.loads(cp.read_text(encoding="utf-8"))
    base_of = {v: k for k, v in PIECE_CONN.items()}
    runs = {pid: [(float(m["s_from"]), float(m["s_to"])) for m in doc.get("medians", [])
                  if m["piece"] == pid and m.get("raised")] for pid in pieces}
    islands, rep = [], []
    for c in cdoc["connectors"]:
        base = c["name"].split("#")[0]
        pid = base_of.get(base)
        if pid is None:
            continue
        pc = pieces[pid]
        P = c["points_xyz_m"]
        n = len(P)
        # each point's station, and the connector's sense against the piece (its direction at the point)
        st = []
        for p in P:
            _d, s, _lat = pc.project(p[0], p[2])
            st.append(s)
        lines = {}
        iw, ip = [0.0] * n, [None] * n
        for i, p in enumerate(P):
            a, b = P[max(0, i - 1)], P[min(n - 1, i + 1)]
            tx, tz = b[0] - a[0], b[2] - a[2]
            Lt = math.hypot(tx, tz) or 1.0
            tx, tz = tx / Lt, tz / Lt
            pt = pc.tangent(st[i])
            sense = 1.0 if tx * pt[0] + tz * pt[1] >= 0 else -1.0
            # the connector point's own lateral position in the piece frame (its offset from the piece line)
            _d, _s, lat = pc.project(p[0], p[2])
            for key, off, color, dash in layout(pc, st[i], runs[pid]):
                rec = lines.setdefault(key, {"color": color, "dash": dash, "off": [None] * n})
                rec["off"][i] = round(sense * (off - lat), 3)
            mtype = pc.near(st[i], "median_type")
            if mtype in RAISED and any(a_ <= st[i] <= b_ for a_, b_ in runs[pid]):
                mw = pc.num(st[i], "median_w_m")
                moff = pc.num(st[i], "median_off_m")
                o = sense * (moff - lat)
                nx, nz = -tz, tx
                iw[i] = round(mw, 3)
                ip[i] = [round(p[0] + nx * o, 3), round(p[1], 3), round(p[2] + nz * o, 3)]
        strokes = []
        if pid == "D":
            # the hatched approach into J4: diagonal strokes between the two inner lines of the painted median
            s_h = [s for s in st if pc.near(s, "median_type") == "hatched" and pc.num(s, "median_w_m") >= PLAIN_DOUBLE_UNDER_M]
            if s_h:
                a_s, b_s = min(s_h), max(s_h)
                k = math.ceil(a_s / HATCH_EVERY_M)
                while k * HATCH_EVERY_M <= b_s:
                    s0 = k * HATCH_EVERY_M
                    mw = pc.num(s0, "median_w_m")
                    s1 = s0 + max(0.5, mw - 2 * (0.06 + PAIR_IN_M + 0.06))
                    if s1 > b_s:
                        break
                    fi0, fi1 = _frac_index(st, s0), _frac_index(st, s1)
                    if fi0 is None or fi1 is None:
                        k += 1
                        continue
                    o0 = _off_at(lines.get("pm_R2"), fi0)
                    o1 = _off_at(lines.get("pm_L2"), fi1)
                    if o0 is not None and o1 is not None:
                        strokes.append({"color": "yellow", "w": 0.30, "a": [round(fi0, 4), round(o0 + (0.2 if o1 > o0 else -0.2), 3)],
                                        "b": [round(fi1, 4), round(o1 - (0.2 if o1 > o0 else -0.2), 3)]})
                    k += 1
        c["paint"] = {"lines": [{"color": v["color"], "dash": v["dash"], "off": v["off"]} for v in lines.values()
                                if any(o is not None for o in v["off"])],
                      "strokes": strokes,
                      "_doc": "tools/expansion_pieces.py decorate (ledger 0054 P3 step 5): authored paint, offsets per point"}
        if any(w > 0 for w in iw):
            # island points: the median's centre at each connector point (heights = the connector's; the weld's warp
            # moves them with the deck, weld_mouths_blend); points without an island take the connector point (w 0)
            pts_i = [ip[i] if ip[i] is not None else [round(v, 3) for v in P[i]] for i in range(n)]
            islands.append({"name": base, "points_xyz_m": pts_i, "island_w_by_point": iw, "offset_aware": True,
                            "_doc": "ledger 0054 P3: the raised median of an authored north piece (tools/expansion_pieces.py)"})
        rep.append((c["name"], n, len(c["paint"]["lines"]), len(strokes), sum(1 for w in iw if w > 0)))
    cp.write_text(json.dumps(cdoc), encoding="utf-8")
    bp = data / "median_bands.json"
    bands = json.loads(bp.read_text(encoding="utf-8")) if bp.exists() else {}
    keep = [ci for ci in bands.get("connector_islands", []) if not str(ci.get("name", "")).startswith(PREFIX)]
    bands["connector_islands"] = keep + islands
    bp.write_text(json.dumps(bands), encoding="utf-8")
    for name, n, nl, ns, ni in rep:
        print(f"[pieces] {name}: {n} pts, {nl} paint lines, {ns} hatch strokes, island on {ni} pts")
    print(f"[pieces] decorated {len(rep)} north connector piece(s); {len(islands)} island(s) -> median_bands.json")
    return rep


def _frac_index(st, s):
    for i in range(len(st) - 1):
        a, b = st[i], st[i + 1]
        if min(a, b) <= s <= max(a, b) and abs(b - a) > 1e-9:
            return i + (s - a) / (b - a)
    return None


def _off_at(line, fi):
    if line is None:
        return None
    i = int(math.floor(fi))
    offs = line["off"]
    if i < 0 or i + 1 >= len(offs) or offs[i] is None or offs[i + 1] is None:
        return None
    t = fi - i
    return offs[i] + (offs[i + 1] - offs[i]) * t


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) >= 2 and argv[0] == "decorate":
        decorate(argv[1])
        return 0
    if len(argv) >= 2 and argv[0] == "show":
        doc, pieces = load(argv[1])
        for pid in "ABCD":
            c = piece_connector(doc, pieces, pid)
            g, at = grade_report(c)
            ys = [p[1] for p in c["points_xyz_m"]]
            print(f"{c['name']}: {len(ys)} pts, width {min(c['widths_m']):.1f}-{max(c['widths_m']):.1f} m, "
                  f"y {ys[0]:.2f} .. {ys[-1]:.2f}, steepest {100 * g:.1f} % at {at}")
        return 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    raise SystemExit(main())
