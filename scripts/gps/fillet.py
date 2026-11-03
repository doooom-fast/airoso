"""Round an OSM route's polyline into a line a car can follow: declared street corners at their declared radius,
every other OSM node inside its own two segments.

Ledger 0073 (Sand Creek, Kevin 2026-11-03: the roads "are a bit wiggly w/r/t lines and curves/edges, they're not
realistic and messy"; asked whether to re-source the line from OSM or smooth Google's: "Re-source from OSM"). An OSM
route stitched by :func:`scripts.gps.centerline.build_ring` is the real street centrelines, but as a POLYGON: a 90 deg
street corner is one shared node, a curve is a chain of straight segments, and every way join is a small kink.
``build_mesh``'s Laplacian smoothing and 28 deg corner rounding then made each 90 deg corner an apex of R ~ 7 m under a
20-42 m road (ledger 0070, A). This module rounds the polygon once, before the 3 m resample, so the line the engine
smooths is already a curve:

- **Declared corners** (``route.fillet.corners[]``: ``at`` [lat, lon] of the OSM junction node, ``radius_m``): the
  route's corner at the ring vertex nearest ``at`` is replaced by a circular arc of ``radius_m``, tangent to both legs.
  The tangent points sit ``T = R tan(D / 2)`` either side of the apex along the line (D = the deflection measured
  between the legs' chords just outside them), and the curve is the rational quadratic Bezier on the two leg tangents,
  which is exactly circular when the legs are straight there. The radius is the config's, with its evidence beside it:
  this module invents none.
- **Every other node** (``round_nodes``, on by default): a vertex that turns by D is replaced by the circular arc
  tangent to its two segments at their midpoints (the whole segment where the neighbour is a fixed arc end), i.e. the
  arc of radius ``min(half segment) / tan(D / 2)``. A curve OSM draws as a chain of nodes becomes the smooth curve
  through its segments' midpoints; a 1 deg node on a straight becomes an arc of hundreds of metres; no node moves by
  more than ``T tan(D / 4)``.

The ring is handled as a closed lap when its first and last points coincide (L13: the duplicate is dropped, arcs may
not straddle each other across the seam, and the closing point is re-added). Output points are (lon, lat), arcs
sampled every ``arc_step_m``; straights keep their two OSM end points (the caller resamples). Pure stdlib.
"""
from __future__ import annotations

import math

Vertex = tuple[float, float]  # (lon, lat)

SNAP_M = 15.0          # a declared corner's ``at`` must be within this of a ring vertex
LEG_CHORD_M = 10.0     # the legs' directions are the chords over this length just outside the arc
MIN_TURN_DEG = 0.2     # a node turning less than this is left as it is


def _mpd(lat0: float) -> tuple[float, float]:
    # scripts.geometry.projection._meters_per_degree (WGS84 series), repeated so this module needs nothing but math
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    return m_lon, m_lat


def _unit(v):
    n = math.hypot(v[0], v[1])
    return (v[0] / n, v[1] / n) if n > 1e-12 else (0.0, 0.0)


def _turn(u0, u1) -> float:
    """Signed angle from direction u0 to u1, radians (+ = left)."""
    return math.atan2(u0[0] * u1[1] - u0[1] * u1[0], u0[0] * u1[0] + u0[1] * u1[1])


def _conic(q0, x, q1, w: float, n: int):
    """n+1 points of the rational quadratic Bezier q0 -> q1 with control x and middle weight w (both ends included)."""
    out = []
    for k in range(n + 1):
        t = k / n
        b0, b1, b2 = (1 - t) ** 2, 2 * w * t * (1 - t), t * t
        s = b0 + b1 + b2
        out.append(((b0 * q0[0] + b1 * x[0] + b2 * q1[0]) / s, (b0 * q0[1] + b1 * x[1] + b2 * q1[1]) / s))
    return out


def _hermite(q0, t0, q1, t1, n: int):
    """Fallback when the leg tangents do not meet ahead of both ends: cubic Hermite with chord-length tangents."""
    L = math.dist(q0, q1)
    out = []
    for k in range(n + 1):
        s = k / n
        h00, h10, h01, h11 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s, -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
        out.append((h00 * q0[0] + h10 * L * t0[0] + h01 * q1[0] + h11 * L * t1[0],
                    h00 * q0[1] + h10 * L * t0[1] + h01 * q1[1] + h11 * L * t1[1]))
    return out


class _Ring:
    """A polyline in local metres with cyclic (closed) or clamped (open) station lookup."""

    def __init__(self, P, closed):
        self.P, self.closed = P, closed
        self.n = len(P)
        self.st = [0.0]
        for i in range(1, self.n + (1 if closed else 0)):
            self.st.append(self.st[-1] + math.dist(P[i - 1], P[i % self.n]))
        self.L = self.st[-1]

    def at(self, s):
        if self.closed:
            s %= self.L
        else:
            s = max(0.0, min(self.L, s))
        lo, hi = 0, len(self.st) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.st[mid] <= s:
                lo = mid
            else:
                hi = mid
        a, b = self.P[lo % self.n], self.P[hi % self.n]
        t = 0.0 if self.st[hi] == self.st[lo] else (s - self.st[lo]) / (self.st[hi] - self.st[lo])
        return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))


def _in_span(s, a, b, L, closed):
    """s strictly inside the station span (a, b), which may wrap past the end of a closed lap (a > b)."""
    if not closed or a <= b:
        return a < s < b
    return s > a or s < b


def _dp(pts, tol):
    """Douglas-Peucker keep-mask for an open run (both ends kept)."""
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        A, B = pts[a], pts[b]
        dx, dy = B[0] - A[0], B[1] - A[1]
        L = math.hypot(dx, dy)
        best, k = -1.0, -1
        for i in range(a + 1, b):
            P = pts[i]
            d = (abs(dx * (P[1] - A[1]) - dy * (P[0] - A[0])) / L) if L > 1e-12 else math.dist(P, A)
            if d > best:
                best, k = d, i
        if best > tol:
            keep[k] = True
            stack += [(a, k), (k, b)]
    return keep


def _simplify(seq, tol, closed):
    """seq [(point, fixed)] with the free nodes Douglas-Peucker'd to ``tol`` between consecutive fixed points (the
    declared arcs, which are all kept); an open line keeps its two ends, a ring with no arc is anchored at node 0."""
    m = len(seq)
    if m < 4:
        return seq
    fixed_idx = [i for i, (_p, f) in enumerate(seq) if f]
    if closed and not fixed_idx:
        # no anchor on a closed ring: anchor at node 0 and at the node farthest from it
        far = max(range(m), key=lambda i: math.dist(seq[i][0], seq[0][0]))
        anchors = sorted({0, far})
    else:
        anchors = fixed_idx if fixed_idx else [0, m - 1]
    keep = [f for _p, f in seq]
    for a in anchors:
        keep[a] = True
    order = anchors + ([anchors[0] + m] if closed else [])
    for k in range(len(order) - 1):
        a, b = order[k], order[k + 1]
        if b - a < 2:
            continue
        idx = [i % m for i in range(a, b + 1)]
        mask = _dp([seq[i][0] for i in idx], tol)
        for i, kp in zip(idx, mask):
            keep[i] = keep[i] or kp
    if not closed:
        keep[0] = keep[-1] = True
    return [s for s, k in zip(seq, keep) if k]


def fillet_ring(lonlat: list[Vertex], *, corners=(), round_nodes: bool = True, arc_step_m: float = 1.0,
                min_turn_deg: float = MIN_TURN_DEG, simplify_m: float = 0.0) -> tuple[list[Vertex], dict]:
    """(rounded line as (lon, lat), report). ``corners``: [{name, at: [lat, lon], radius_m}] (extra keys ignored)."""
    pts = [tuple(map(float, p)) for p in lonlat]
    closed = len(pts) > 2 and math.dist(pts[0], pts[-1]) < 1e-9
    if closed:
        pts = pts[:-1]
    lat0 = sum(p[1] for p in pts) / len(pts)
    lon0 = sum(p[0] for p in pts) / len(pts)
    m_lon, m_lat = _mpd(lat0)
    P = []
    for lo, la in pts:
        q = ((lo - lon0) * m_lon, (la - lat0) * m_lat)
        if not P or math.dist(P[-1], q) > 1e-6:
            P.append(q)
    if closed and len(P) > 1 and math.dist(P[0], P[-1]) <= 1e-6:
        P.pop()
    ring = _Ring(P, closed)
    rep = {"closed": closed, "length_in_m": round(ring.L, 2), "corners": [], "nodes_rounded": 0}

    # ---- declared corners: spans and arcs -------------------------------------------------------------------
    spans = []   # (s_lo, s_hi, arc points)
    for c in corners or ():
        name = c.get("name") or str(c.get("at"))
        R = float(c["radius_m"])
        if not R > 0:
            raise ValueError(f"route.fillet corner {name!r}: radius_m must be > 0")
        tgt = ((float(c["at"][1]) - lon0) * m_lon, (float(c["at"][0]) - lat0) * m_lat)
        a = min(range(ring.n), key=lambda i: math.dist(P[i], tgt))
        snap = math.dist(P[a], tgt)
        if snap > SNAP_M:
            raise ValueError(f"route.fillet corner {name!r}: no route vertex within {SNAP_M:g} m of {c['at']} "
                             f"(nearest {snap:.1f} m) - the corner is not on this route")
        sa = ring.st[a]
        apex = P[a]
        T = R
        for _ in range(4):   # the legs' chords just outside the arc -> deflection -> tangent length, to a fixed point
            u0 = _unit((ring.at(sa - T)[0] - ring.at(sa - T - LEG_CHORD_M)[0], ring.at(sa - T)[1] - ring.at(sa - T - LEG_CHORD_M)[1]))
            u1 = _unit((ring.at(sa + T + LEG_CHORD_M)[0] - ring.at(sa + T)[0], ring.at(sa + T + LEG_CHORD_M)[1] - ring.at(sa + T)[1]))
            D = _turn(u0, u1)
            T_new = R * math.tan(abs(D) / 2.0)
            if abs(T_new - T) < 1e-3:
                T = T_new
                break
            T = T_new
        if not closed and (sa - T < 0 or sa + T > ring.L):
            raise ValueError(f"route.fillet corner {name!r}: the arc (T {T:.1f} m) runs off the end of the route")
        p0, p1 = ring.at(sa - T), ring.at(sa + T)
        n_arc = max(2, int(math.ceil(R * abs(D) / arc_step_m)))
        # the two leg LINES (through the line's points at sa -/+ T, along the chords) meet at x; the arc is the circle
        # of radius R tangent to both, its tangent points T from x. Where a leg bends inside the corner (an OSM node
        # just before the junction) the tangent points sit on the leg line, not on the bend, so the radius stays R.
        den = u0[0] * u1[1] - u0[1] * u1[0]
        x = None
        if abs(den) > 1e-9:
            lam = ((p1[0] - p0[0]) * u1[1] - (p1[1] - p0[1]) * u1[0]) / den
            mu = (u0[0] * (p1[1] - p0[1]) - u0[1] * (p1[0] - p0[0])) / den
            if lam > -T and mu > -T:
                x = (p0[0] + lam * u0[0], p0[1] + lam * u0[1])
        if x is not None:
            q0 = (x[0] - u0[0] * T, x[1] - u0[1] * T)
            q1 = (x[0] + u1[0] * T, x[1] + u1[1] * T)
            arc = _conic(q0, x, q1, math.cos(abs(D) / 2.0), n_arc)
            r_eff = [R, R]
            how = "circular arc (rational quadratic Bezier on the leg lines)"
        else:
            q0, q1 = p0, p1
            arc = _hermite(q0, u0, q1, u1, n_arc)
            r_eff = [None, None]
            how = "cubic Hermite (the leg lines do not meet ahead of both ends)"
        # the span replaced: from the line's nearest station to q0 to its nearest station to q1
        def _near_st(q, s_guess):
            best_s, best_d = s_guess, float("inf")
            for k in range(-60, 61):
                s = s_guess + 0.5 * k
                d = math.dist(ring.at(s), q)
                if d < best_d:
                    best_s, best_d = s, d
            return best_s, best_d
        lo, off0 = _near_st(q0, sa - T)
        hi, off1 = _near_st(q1, sa + T)
        rep_join = [round(off0, 2), round(off1, 2)]
        if closed:
            lo %= ring.L
            hi %= ring.L
        spans.append((lo, hi, arc))
        mid = arc[len(arc) // 2]
        rep["corners"].append({"name": name, "apex_station_m": round(sa, 1), "snap_m": round(snap, 2),
                               "deflection_deg": round(math.degrees(D), 1), "radius_m": R,
                               "tangent_m": round(T, 2), "radius_achieved_m": [None if r is None else round(r, 2) for r in r_eff],
                               "apex_moved_m": round(math.dist(apex, mid), 2),
                               "tangent_point_off_line_m": rep_join, "curve": how})
    # arcs may not overlap (each other, or themselves round the seam)
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            a0, a1, _ = spans[i]
            b0, b1, _ = spans[j]
            if (_in_span(b0, a0, a1, ring.L, closed) or _in_span(a0, b0, b1, ring.L, closed)
                    or abs(a0 - b0) < 1e-9):
                raise ValueError(f"route.fillet corners {rep['corners'][i]['name']!r} and {rep['corners'][j]['name']!r} "
                                 f"overlap: their arcs need more road than lies between them")

    # ---- assemble: the ring with each declared span replaced by its arc (arc points fixed) -------------------------
    def inside_any(s):
        return any(_in_span(s, a, b, ring.L, closed) for a, b, _ in spans)
    # start from a vertex outside every span so no arc is split by the list's ends
    start = 0
    if closed and spans:
        start = next((i for i in range(ring.n) if not inside_any(ring.st[i])
                      and not any(abs(ring.st[i] - a) < 1e-9 for a, _b, _c in spans)), 0)
    order = list(range(start, ring.n)) + list(range(0, start)) if closed else list(range(ring.n))
    by_start = sorted(spans, key=lambda sp: (sp[0] - ring.st[start]) % ring.L if closed else sp[0])
    seq = []      # (point, fixed)
    k = 0
    for i in order:
        s = ring.st[i]
        rel = (s - ring.st[start]) % ring.L if closed else s
        while k < len(by_start):
            lo = by_start[k][0]
            lo_rel = (lo - ring.st[start]) % ring.L if closed else lo
            if lo_rel <= rel:
                seq.extend((p, True) for p in by_start[k][2])
                k += 1
            else:
                break
        if not inside_any(s):
            if seq and seq[-1][1] and math.dist(seq[-1][0], P[i]) < 1e-6:
                continue
            seq.append((P[i], False))
    while k < len(by_start):
        seq.extend((p, True) for p in by_start[k][2])
        k += 1
    # drop zero-length steps
    clean = []
    for p, f in seq:
        if clean and math.dist(clean[-1][0], p) < 1e-6:
            clean[-1] = (clean[-1][0], clean[-1][1] or f)
            continue
        clean.append((p, f))
    if closed and len(clean) > 1 and math.dist(clean[0][0], clean[-1][0]) < 1e-6:
        clean.pop()
    seq = clean

    # ---- optional: drop the nodes that sit within simplify_m of the chord their neighbours make (Douglas-Peucker on
    # each free run between fixed arcs). OSM draws a curve as nodes 2-3 m apart; where such a curve meets a way join
    # (a ramp merging at 26 deg into the street it serves) the half-segment rule below would round the join inside
    # one 3 m segment (R ~ 6 m). Merged, the segments are long enough for the arc to follow the curve's own radius.
    if simplify_m > 0:
        seq = _simplify(seq, simplify_m, closed)
        rep["simplify_m"] = simplify_m

    # ---- every other node: the arc tangent to its segments at their midpoints ------------------------------------
    out = []
    m = len(seq)
    thr = math.radians(min_turn_deg)
    for i in range(m):
        p, fixed = seq[i]
        if fixed or not round_nodes or (not closed and (i == 0 or i == m - 1)):
            out.append(p)
            continue
        pp, pf = seq[(i - 1) % m]
        nq, nf = seq[(i + 1) % m]
        L0, L1 = math.dist(pp, p), math.dist(p, nq)
        u0, u1 = _unit((p[0] - pp[0], p[1] - pp[1])), _unit((nq[0] - p[0], nq[1] - p[1]))
        D = _turn(u0, u1)
        if abs(D) < thr or abs(D) > math.radians(179.0):
            out.append(p)
            continue
        T = min(L0 if pf else L0 / 2.0, L1 if nf else L1 / 2.0)
        R = T / math.tan(abs(D) / 2.0)
        n_arc = max(2, int(math.ceil(R * abs(D) / arc_step_m)))
        q0 = (p[0] - u0[0] * T, p[1] - u0[1] * T)
        q1 = (p[0] + u1[0] * T, p[1] + u1[1] * T)
        arc = _conic(q0, p, q1, math.cos(abs(D) / 2.0), n_arc)
        for a in arc:
            if not out or math.dist(out[-1], a) > 1e-6:
                out.append(a)
        rep["nodes_rounded"] += 1
    if closed and len(out) > 1 and math.dist(out[0], out[-1]) < 1e-6:
        out.pop()
    res = [(lon0 + x / m_lon, lat0 + y / m_lat) for x, y in out]
    if closed:
        res.append(res[0])
    L = sum(math.dist(out[i - 1], out[i]) for i in range(1, len(out))) + (math.dist(out[-1], out[0]) if closed else 0.0)
    rep["length_out_m"] = round(L, 2)
    return res, rep


def insert_point(lonlat: list[Vertex], target_latlon) -> tuple[list[Vertex], int, float]:
    """Insert the foot of ``target_latlon`` ([lat, lon]) on the line as a vertex (unless a vertex is within 1 cm);
    returns (line, its index, distance m from the target to the line). Used to make ``route.start_at`` an exact
    point on a rounded ring instead of the nearest of vertices that can lie tens of metres apart on a straight."""
    pts = [tuple(map(float, p)) for p in lonlat]
    lat0 = float(target_latlon[0])
    m_lon, m_lat = _mpd(lat0)
    tx, ty = float(target_latlon[1]) * m_lon, lat0 * m_lat
    best = (float("inf"), 0, 0.0)
    for i in range(len(pts) - 1):
        ax, ay = pts[i][0] * m_lon, pts[i][1] * m_lat
        bx, by = pts[i + 1][0] * m_lon, pts[i + 1][1] * m_lat
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((tx - ax) * dx + (ty - ay) * dy) / L2))
        d = math.hypot(ax + t * dx - tx, ay + t * dy - ty)
        if d < best[0]:
            best = (d, i, t)
    d, i, t = best
    a, b = pts[i], pts[i + 1]
    q = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
    if math.hypot((q[0] - a[0]) * m_lon, (q[1] - a[1]) * m_lat) < 0.01:
        return pts, i, d
    if math.hypot((q[0] - b[0]) * m_lon, (q[1] - b[1]) * m_lat) < 0.01:
        return pts, i + 1, d
    return pts[:i + 1] + [q] + pts[i + 1:], i + 1, d
