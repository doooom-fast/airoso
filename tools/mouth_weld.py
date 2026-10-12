"""Side-street MOUTH WELD — the pure geometry (no bpy), shared by tools/weld_mouths_blend.py (the Blender pass),
tools/seat_terrain_blend.py, tools/gap_mouths_blend.py and their tests.

THE DEFECT (diagnosis 2026-10-11, Del Cerro W leg at College v1085, 76.9 deg, College grade 4.56 %): the
assembler (build_loop_blend.py:674-683) sweeps every connector as a LEVEL ribbon whose end row is SQUARE to the
connector. Where the connector meets its host at a skew on a grade, that row cannot lie on the host: the
acute corner reached 3.4 m inside College's pavement and stood up to +0.51 m over College's deck, the other
corner left a grass notch 0.3-0.6 m below it, and the sidewalk end ran 2.78 m further into the host at
+0.67..+0.75 m. tools/trim_connectors.py already lands the CENTRELINE on the host deck (interpolated along
the host segment) and blends its last 30 m; nothing below the centreline knew where the host was.

THE WELD, per mouth (data/mouths.json: piece, end, host, side), on the meshes the assembler wrote:
  1. MITRE — every lateral line of the connector (ROAD left/centre/right; CURB lane edge, curb top, sidewalk
     back, grass meet on both sides) is cut where IT crosses the host's edge line: road lines at the host
     edge minus OVERLAP_M (the 0.4 m overlap trim_connectors keeps), curb/sidewalk lines AT the host edge
     (a raised curb never stands in the host's pavement). Lines that stop short are extended along their
     last direction. The first rows (at least REMAP_MIN_M past the furthest cut) are re-spread along each
     line between its new end and the first untouched row, so no row folds and no vertex is added/removed
     (gap_mouths_blend and seat key on the assembler's vertex order).
  2. WARP — every vertex within BLEND_M of its line's new end moves by
         (host deck at that point + the line's profile height - the line's level end height)
         x smoothstep(1 - s / BLEND_M)
     so the end row lies ON the host deck (cross-fall and all) and the approach eases back to the
     connector's own profile with zero grade change at both ends of the blend. "The host deck at that point"
     is the host's own ribbon (rows read off the mesh) extended level across its edge.
  3. Markings ride along: a painted vertex at offset o on row j keeps its fraction of the (new) row between
     the centre and that side's edge and its 0.015 m lift over the road.

Also here: unfold_line (a ribbon line running backwards round a corner tighter than its offset is cut at its
self-intersection, or bridged by a forward chord — the Navajo / Jackson "other deck above the strip" 0.458 m) and
gap_window (the host sidewalk stations gap_mouths_blend removes at a mouth, sized for the skew).

Everything here works in the engine local frame: x east, y up, z north; rows are (L, C, R) tuples of
(x, y, z). The Blender wrapper converts (Blender co = (x, z, y)).
"""
from __future__ import annotations

import math

OVERLAP_M = 0.4          # tools/trim_connectors.py OVERLAP_M: a road end overlaps the host pavement by this
CURB_INSET_M = 0.0       # curb / sidewalk lines end ON the host's pavement edge
BLEND_M = 30.0           # the warp length (tools/trim_connectors.py BLEND_M: the centreline blend)
REMAP_MIN_M = 6.0        # rows are re-spread over at least this beyond the furthest mitre point
EXTEND_MAX_M = 25.0      # a line short of the host edge may be extended this far, no further
MARCH_M = 0.25           # root bracketing step along a line
HOST_WINDOW_M = 90.0     # host rows within this (arc) of the mouth station define its deck + edge
SELF_TOL_M = 0.02        # self-check: end row vs the host deck; nothing above the host deck by more
MARK_LIFT_M = 0.015      # markings sit this far over the road (build_loop_blend: +0.115 vs the road's +0.10)
CURB_P = 4               # ribbon.curb_sidewalk profile points per side per row
GAP_CORNER_M = 3.0       # tools/gap_mouths_blend.py: the host sidewalk gap runs this far past the connector's edge


class WeldError(RuntimeError):
    """a mouth the weld cannot build honestly — the caller stops loudly"""


# --------------------------------------------------------------------------------------------- layout

def is_closed(pts) -> bool:
    return abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6


def unique_rows(pts) -> int:
    """cross-sections the ribbon sweeps (a closed polyline's duplicate closing vertex is dropped)"""
    return len(pts) - 1 if is_closed(pts) else len(pts)


def mesh_layout(main_pts, conns) -> dict:
    """vertex blocks of the assembler's merged meshes (build_loop_blend.py:653-683): ROAD is 3 verts per row
    (left, centre, right), the mainline first, then each connector IN connectors.local.json ORDER; CURB is per
    line two side blocks (side +1 = left of the line's direction first, then side -1), rows x 4 profile points.
    {name: {"rows", "closed", "road", "curb"}} plus "_road_total" / "_curb_total" (vertex counts)."""
    out = {}
    road = curb = 0
    for name, pts in [("MAINLINE", main_pts)] + [(c["name"], c["points_xyz_m"]) for c in conns]:
        m = unique_rows(pts)
        out[name] = {"rows": m, "closed": is_closed(pts), "road": road, "curb": curb}
        road += 3 * m
        curb += 2 * m * CURB_P
    out["_road_total"] = road
    out["_curb_total"] = curb
    return out


def road_index(lay: dict, name: str, row: int, lane: int) -> int:
    """ROAD vertex of row `row`, lane 0 = left, 1 = centre, 2 = right"""
    return lay[name]["road"] + 3 * row + lane


def curb_index(lay: dict, name: str, row: int, side: int, p: int) -> int:
    """CURB vertex of row `row`, side +1 / -1, profile point p (0 lane edge, 1 curb top, 2 sidewalk back,
    3 grass meet)"""
    b = lay[name]
    return b["curb"] + (0 if side == 1 else b["rows"] * CURB_P) + row * CURB_P + p


# --------------------------------------------------------------------------------------------- basics

def smoothstep(x: float) -> float:
    x = 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)
    return x * x * (3.0 - 2.0 * x)


def _plan_len(a, b) -> float:
    return math.hypot(b[0] - a[0], b[2] - a[2])


def arc_lengths(pts) -> list:
    out = [0.0]
    for i in range(1, len(pts)):
        out.append(out[-1] + _plan_len(pts[i - 1], pts[i]))
    return out


# --------------------------------------------------------------------------------------------- host deck

class HostDeck:
    """The host ribbon's deck, read off its rows: level across each row unless the mesh says otherwise
    (the row heights are interpolated between centre and edge, held at the edge height beyond it), linear
    between rows. Only rows `idx` (a window around the mouth, in order; wrapped for a closed host) are used,
    so a far part of a curved host never captures a projection."""

    def __init__(self, rows, idx):
        self.rows = rows
        self.idx = list(idx)
        if len(self.idx) < 2:
            raise WeldError("host window holds fewer than 2 rows")

    def project(self, x, z):
        """(distance, window position k, t, signed lateral (+ = left of travel)) onto the centre polyline"""
        best = None
        for k in range(len(self.idx) - 1):
            c0 = self.rows[self.idx[k]][1]
            c1 = self.rows[self.idx[k + 1]][1]
            dx, dz = c1[0] - c0[0], c1[2] - c0[2]
            L2 = dx * dx + dz * dz
            if L2 < 1e-12:
                continue
            t = max(0.0, min(1.0, ((x - c0[0]) * dx + (z - c0[2]) * dz) / L2))
            px, pz = c0[0] + t * dx, c0[2] + t * dz
            d = math.hypot(x - px, z - pz)
            if best is None or d < best[0]:
                L = math.sqrt(L2)
                lat = (-dz * (x - c0[0]) + dx * (z - c0[2])) / L
                best = (d, k, t, lat)
        return best

    def _half(self, r, o):
        L, C, R = self.rows[r]
        S = L if o >= 0 else R
        return max(1e-6, _plan_len(C, S))

    def _row_h(self, r, o):
        L, C, R = self.rows[r]
        S = L if o >= 0 else R
        f = min(abs(o) / self._half(r, o), 1.0)
        return C[1] + (S[1] - C[1]) * f

    def at(self, x, z) -> float:
        _d, k, t, o = self.project(x, z)
        r0, r1 = self.idx[k], self.idx[k + 1]
        return self._row_h(r0, o) * (1 - t) + self._row_h(r1, o) * t

    def edge_gap(self, x, z, side, inset) -> float:
        """signed distance past the host edge line (minus `inset`) on `side`: > 0 outside, toward the connector"""
        _d, k, t, o = self.project(x, z)
        r0, r1 = self.idx[k], self.idx[k + 1]
        half = self._half(r0, side) * (1 - t) + self._half(r1, side) * t
        return o * side - (half - inset)

    def inside(self, x, z, margin=0.0) -> bool:
        """inside the host's pavement footprint (either side), `margin` inward"""
        _d, k, t, o = self.project(x, z)
        r0, r1 = self.idx[k], self.idx[k + 1]
        half = self._half(r0, o) * (1 - t) + self._half(r1, o) * t
        return abs(o) < half - margin


def host_window(rows, closed, x, z, reach=HOST_WINDOW_M):
    """row indices of the host within `reach` of arc from the row nearest (x, z), in order (wrapped if closed)"""
    m = len(rows)
    best, bi = None, 0
    for i in range(m):
        c = rows[i][1]
        d = math.hypot(c[0] - x, c[2] - z)
        if best is None or d < best:
            best, bi = d, i
    idx = [bi]
    acc = 0.0
    i = bi
    while acc < reach:
        j = i - 1
        if j < 0:
            if not closed:
                break
            j = m - 1
        if j == bi:
            break
        acc += _plan_len(rows[i][1], rows[j][1])
        idx.insert(0, j)
        i = j
    acc = 0.0
    i = bi
    while acc < reach:
        j = i + 1
        if j >= m:
            if not closed:
                break
            j = 0
        if j == idx[0]:
            break
        acc += _plan_len(rows[i][1], rows[j][1])
        idx.append(j)
        i = j
    return idx


# --------------------------------------------------------------------------------------------- one line

class Line:
    """a lateral line END-FIRST (pts[0] is the connector's end row), parameterised by plan arc u from the end;
    u < 0 runs past the end along the first segment's direction, held level"""

    def __init__(self, pts):
        if len(pts) < 2:
            raise WeldError("a lateral line needs 2+ rows")
        self.pts = [tuple(p) for p in pts]
        self.u = arc_lengths(self.pts)
        k = 1
        while k < len(self.pts) - 1 and _plan_len(self.pts[0], self.pts[k]) < 0.05:
            k += 1
        dx, dz = self.pts[0][0] - self.pts[k][0], self.pts[0][2] - self.pts[k][2]
        L = math.hypot(dx, dz) or 1.0
        self.ext = (dx / L, dz / L)

    def at(self, u):
        """(x, y, z) at arc u"""
        p = self.pts
        if u <= 0.0:
            return (p[0][0] + self.ext[0] * (-u), p[0][1], p[0][2] + self.ext[1] * (-u))
        us = self.u
        if u >= us[-1]:
            return p[-1]
        lo, hi = 0, len(us) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if us[mid] <= u:
                lo = mid
            else:
                hi = mid
        seg = us[hi] - us[lo]
        t = 0.0 if seg < 1e-12 else (u - us[lo]) / seg
        a, b = p[lo], p[hi]
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)

    def crossing(self, gap) -> float:
        """arc u where gap(x, z) changes sign from <= 0 (inside the host target) to > 0, nearest the end:
        marching forward along the line when the end is inside, backward along the extension when it is short"""
        def g(u):
            q = self.at(u)
            return gap(q[0], q[2])
        g0 = g(0.0)
        if g0 <= 0.0:
            a = 0.0
            umax = self.u[-1]
            while True:
                b = min(a + MARCH_M, umax)
                if g(b) > 0.0:
                    break
                if b >= umax:
                    raise WeldError("a lateral line never leaves the host")
                a = b
        else:
            b = 0.0
            while True:
                a = b - MARCH_M
                if a < -EXTEND_MAX_M:
                    raise WeldError(f"a lateral line stops > {EXTEND_MAX_M} m short of the host edge")
                if g(a) <= 0.0:
                    break
                b = a
        for _ in range(48):
            mid = 0.5 * (a + b)
            if g(mid) > 0.0:
                b = mid
            else:
                a = mid
        return 0.5 * (a + b)


# --------------------------------------------------------------------------------------------- the weld

def weld_end(lines: dict, deck: HostDeck, side: int, inset: dict, h: dict, *, blend_m=BLEND_M,
             remap_min=REMAP_MIN_M) -> dict:
    """Mitre + warp the lines of ONE connector end.

    lines: key -> points END-FIRST (all the same row count); inset: key -> host-edge inset of that line's cut;
    h: key -> the line's profile height over the road deck (0 for road lines; curb +0.14 etc.).
    Returns {"new": key -> new points (same length), "u_x": key -> cut arc, "J": rows re-spread, "K": rows
    touched (last + 1), "dy_end": key -> end height change}."""
    keys = list(lines)
    n = len(next(iter(lines.values())))
    if any(len(lines[k]) != n for k in keys):
        raise WeldError("lateral lines of one end differ in row count")
    L = {k: Line(lines[k]) for k in keys}
    ux = {k: L[k].crossing(lambda x, z, _i=inset[k]: deck.edge_gap(x, z, side, _i)) for k in keys}
    need = max(0.0, max(ux.values())) + remap_min
    J = None
    for j in range(1, n):
        if all(L[k].u[j] >= need for k in keys):
            J = j
            break
    if J is None:
        raise WeldError(f"piece too short to re-spread its end rows (needs {need:.1f} m)")
    new, dy_end, K = {}, {}, J
    for k in keys:
        ln = L[k]
        uJ = ln.u[J]
        y_end = ln.at(ux[k])[1]
        out = []
        for j in range(n):
            if j < J:
                u2 = ux[k] + (uJ - ux[k]) * (ln.u[j] / uJ)
                q = ln.at(u2)
            else:
                u2 = ln.u[j]
                q = ln.pts[j]
            s = u2 - ux[k]
            w = smoothstep(1.0 - s / blend_m)
            y = q[1]
            if w > 0.0:
                y = q[1] + (deck.at(q[0], q[2]) + h[k] - y_end) * w
                K = max(K, j + 1)
            out.append((q[0], y, q[2]))
        new[k] = out
        dy_end[k] = out[0][1] - ln.pts[0][1]
    return {"new": new, "u_x": ux, "J": J, "K": K, "dy_end": dy_end}


def map_marking(v, rows_old, rows_new, j_max, tol=2e-3):
    """A painted vertex of the connector: find its row j (end-first, j < j_max) — it lies ON that row's cross
    line — and carry it to the new row at the same fraction between the centre and its side's edge, keeping its
    height over the road. None when it is not on any of those rows (untouched)."""
    best = None
    for j in range(min(j_max, len(rows_old))):
        Lr, Cr, Rr = rows_old[j]
        ax, az = Lr[0] - Cr[0], Lr[2] - Cr[2]
        half_l = math.hypot(ax, az)
        if half_l < 1e-9:
            continue
        nx, nz = ax / half_l, az / half_l
        dx, dz = v[0] - Cr[0], v[2] - Cr[2]
        along = abs(dx * nz - dz * nx)          # distance from the row's cross line
        if along > tol:
            continue
        o = dx * nx + dz * nz
        half_r = math.hypot(Rr[0] - Cr[0], Rr[2] - Cr[2])
        if o > half_l + 0.5 or o < -half_r - 0.5:
            continue
        if best is None or along < best[0]:
            best = (along, j, o)
    if best is None:
        return None
    _a, j, o = best
    Lr, Cr, Rr = rows_old[j]
    Ln, Cn, Rn = rows_new[j]
    if o >= 0:
        S, Sn, half = Lr, Ln, math.hypot(Lr[0] - Cr[0], Lr[2] - Cr[2])
    else:
        S, Sn, half = Rr, Rn, math.hypot(Rr[0] - Cr[0], Rr[2] - Cr[2])
    f = abs(o) / max(half, 1e-9)
    y_road_old = Cr[1] + (S[1] - Cr[1]) * f
    lift = v[1] - y_road_old
    return (Cn[0] + (Sn[0] - Cn[0]) * f, Cn[1] + (Sn[1] - Cn[1]) * f + lift, Cn[2] + (Sn[2] - Cn[2]) * f)


def quad_areas(rows):
    """signed plan areas of the left and right quads between consecutive rows (a fold flips a sign)"""
    out = []
    for j in range(len(rows) - 1):
        a, b = rows[j], rows[j + 1]
        for (p, q) in ((0, 1), (1, 2)):
            poly = (a[p], a[q], b[q], b[p])
            s = 0.0
            for i in range(4):
                x0, z0 = poly[i][0], poly[i][2]
                x1, z1 = poly[(i + 1) % 4][0], poly[(i + 1) % 4][2]
                s += x0 * z1 - x1 * z0
            out.append(0.5 * s)
    return out


def gap_window(hpts, mh, closed, seg, t, width, angle_deg, corner=None):
    """tools/gap_mouths_blend.py: the host stations (row indices < mh) whose curb/sidewalk is gapped for a mouth —
    every station within connector half-width / sin(junction angle) + GAP_CORNER_M of the cut's station (host_seg + t),
    by arc, PLUS the first station past that on each side: gap_mouths deletes a strip face only when BOTH its stations
    are in the set, so without them the gap stopped at the last station inside — up to a station spacing short (the
    Del Cerro W mouth: the window reached 14.76 m, the gap ended at 12.06 m, the connector's road edge crossed the host
    edge at 12.86 m and College's raised sidewalk stood on the connector's corner)"""
    corner = GAP_CORNER_M if corner is None else corner
    arc = [0.0]
    for i in range(1, mh + (1 if closed else 0)):
        a, b = hpts[i - 1], hpts[i % len(hpts)]
        arc.append(arc[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    lap = arc[-1] if closed else None
    j = min(seg + 1, len(arc) - 1)
    c = arc[seg] + (arc[j] - arc[seg]) * t
    sin_a = max(math.sin(math.radians(max(1.0, min(90.0, angle_deg)))), 0.05)
    hw = (width / 2.0) / sin_a + corner
    out = set()
    for q in range(mh):
        d = abs(arc[q] - c)
        if closed:
            d = min(d, lap - d)
        if d <= hw:
            out.add(q)
    if out and len(out) < mh:
        for q in list(out):
            for nb in (q - 1, q + 1):
                if closed:
                    out.add(nb % mh)
                elif 0 <= nb < mh:
                    out.add(nb)
    return out


# --------------------------------------------------------------------------------------------- folds

FOLD_WINDOW = 30         # rows searched each side of a fold for the self-intersection


def _seg_cross(a, b, c, d):
    """(t, u) where plan segments a->b and c->d cross (both in [0, 1]), or None"""
    rx, rz = b[0] - a[0], b[2] - a[2]
    sx, sz = d[0] - c[0], d[2] - c[2]
    den = rx * sz - rz * sx
    if abs(den) < 1e-12:
        return None
    qx, qz = c[0] - a[0], c[2] - a[2]
    t = (qx * sz - qz * sx) / den
    u = (qx * rz - qz * rx) / den
    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return t, u
    return None


def backward_segments(E, C, closed):
    """segment indices j where the lateral line E runs against its centre line C (a ribbon fold)"""
    m = len(E)
    out = []
    for j in range(m if closed else m - 1):
        a, b = E[j], E[(j + 1) % m]
        ca, cb = C[j], C[(j + 1) % m]
        if (b[0] - a[0]) * (cb[0] - ca[0]) + (b[2] - a[2]) * (cb[2] - ca[2]) < -1e-9:
            out.append(j)
    return out


REMOVE_COST_ROWS_PER_M = 10.0   # a forward chord's cost: rows it moves + this x metres of pavement it takes away


def _forward_chord(E, C, closed, ja, jb, window, nseg):
    """(k, l, points) for a fold with no self-intersection (a hook): of every window around the backward run [ja, jb]
    (k <= ja, l >= jb, within `window` rows) whose straight chord E[k] -> E[l + 1] runs forward against every centre
    segment k..l, the cheapest — cost = rows moved + REMOVE_COST_ROWS_PER_M x the pavement the chord takes away (the
    summed inward move of the rows it replaces). Each moved row sits on the chord at its fraction of the centre's arc,
    at its own height. A hook bulging toward the centre is bridged across its mouth for nothing (v3292-3297); at the
    lap seam's 27.5 -> 17 m width step the wide rows keep their edge (the race strip and the inside kerb stand on it)
    and the narrow rows after the step widen onto the chord — never the reverse."""
    m = len(E)
    best = None
    for k in range(ja, ja - window - 1, -1):
        if not closed and k < 0:
            break
        for l in range(jb, jb + window + 1):
            if not closed and l >= nseg:
                break
            if l - k >= nseg or l <= k:
                continue
            a, b = E[k % m], E[(l + 1) % m]
            cx, cz = b[0] - a[0], b[2] - a[2]
            if not all(cx * (C[(r + 1) % m][0] - C[r % m][0]) + cz * (C[(r + 1) % m][2] - C[r % m][2]) > 0.0
                       for r in range(k, l + 1)):
                continue
            arcs = [0.0]
            for r in range(k, l + 1):
                c0, c1 = C[r % m], C[(r + 1) % m]
                arcs.append(arcs[-1] + math.hypot(c1[0] - c0[0], c1[2] - c0[2]))
            tot = arcs[-1] or 1.0
            removed, gain, pts, ok = 0.0, 0.0, [], True
            for i, r in enumerate(range(k + 1, l + 1), start=1):
                f = arcs[i] / tot
                q = (a[0] + cx * f, E[r % m][1], a[2] + cz * f)
                c, e = C[r % m], E[r % m]
                d_old = math.hypot(e[0] - c[0], e[2] - c[2])
                d_new = math.hypot(q[0] - c[0], q[2] - c[2])
                # the new point stays on the same side of the centre as the old one
                if d_new < 0.5 or ((q[0] - c[0]) * (e[0] - c[0]) + (q[2] - c[2]) * (e[2] - c[2])) <= 0.0:
                    ok = False
                    break
                removed += max(0.0, d_old - d_new)
                gain += d_new - d_old
                pts.append(q)
            if not ok:
                continue
            key = ((l - k) + REMOVE_COST_ROWS_PER_M * removed, l - k, -gain)
            if best is None or key < best[0]:
                best = (key, k, l, pts)
    if best is None:
        raise WeldError(f"a fold at rows {ja}..{jb + 1} has neither a self-intersection nor a forward chord within "
                        f"{window} rows")
    return best[1], best[2], best[3]


def unfold_line(E, C, closed, window=FOLD_WINDOW, strict=True):
    """A ribbon never overlaps itself. Where a lateral line E (one edge / curb / paint line, a point per row)
    runs AGAINST its centre line C — the inside of a corner tighter than the offset (Navajo / Jackson v2317-2320:
    half-width 12 m round a 7.4 m centreline radius) — the swallowtail is cut at the self-intersection X of the
    line before and after the fold, and every row between moves to X (height: the higher of the line's two heights
    at X — the fan rises to its apex). What stays inside the corner (a kerb or strip on a smaller offset) stays on the fan (C rows to X).
    A fold with no self-intersection (a hook) is replaced by the cheapest forward chord instead (X = None).
    Returns (new points, [(k, l, X or None)]: rows k+1..l (mod the row count on a closed line) moved, [(ja, jb)]:
    the runs left as they were). strict: a fold with neither raises WeldError; otherwise it is left and listed (a
    connector's hairpin whose legs stand closer than its width overlaps ITSELF, not a fold a cut can mend)."""
    m = len(E)
    E = [tuple(p) for p in E]
    nseg = m if closed else m - 1
    done, left, skip = [], [], set()
    for _round in range(64):
        back = [j for j in backward_segments(E, C, closed) if j not in skip]
        if not back:
            return E, done, left
        ja = back[0]
        jb = ja
        while (jb + 1) % m in back and (closed or jb + 1 < nseg) and (jb + 1 - ja) < nseg:
            jb += 1
        best = None
        for dk in range(1, window + 1):
            k = ja - dk
            if not closed and k < 0:
                break
            for dl in range(1, window + 1):
                l = jb + dl
                if not closed and l >= nseg:
                    break
                if l - k >= nseg:
                    continue
                a, b = E[k % m], E[(k + 1) % m]
                c, d = E[l % m], E[(l + 1) % m]
                hit = _seg_cross(a, b, c, d)
                if hit and (best is None or (l - k) < best[0]):
                    best = (l - k, k, l, hit)
        if best is None:
            # no self-intersection: a HOOK, not a swallowtail (a junction flare widening the inside edge faster than
            # the corner turns: v3295-3297, half-width 10.25 -> 15 m in 10 rows; the lap seam's 27.5 -> 17 m width
            # step). A forward chord replaces it — of those within the window, the one keeping the most pavement —
            # each row on the chord at its fraction of the centre's arc and at its own height (the row stays level)
            try:
                k, l, pts = _forward_chord(E, C, closed, ja, jb, window, nseg)
            except WeldError:
                if strict:
                    raise
                skip.update(j % m for j in range(ja, jb + 1))
                left.append((ja, jb))
                continue
            for r, q in zip(range(k + 1, l + 1), pts):
                E[r % m] = q
            done.append((k, l, None))
            continue
        _span, k, l, (t, u) = best
        a, b = E[k % m], E[(k + 1) % m]
        c, d = E[l % m], E[(l + 1) % m]
        # the apex takes the HIGHER of the line's two heights there: on a climbing corner the legs meet up to 0.5 m
        # apart (Navajo / Jackson), and with the apex on the high leg the fan is a cone rising to it — every crease
        # from a centre row to the apex a ridge. At their mean it was a saddle whose valleys let the prep's grass
        # facets (pinned 0.02 m under the deck at their vertices) stand 0.04-0.22 m over the race lane's inside edge.
        y = max(a[1] + (b[1] - a[1]) * t, c[1] + (d[1] - c[1]) * u)
        X = (a[0] + (b[0] - a[0]) * t, y, a[2] + (b[2] - a[2]) * t)
        for r in range(k + 1, l + 1):
            E[r % m] = X
        done.append((k, l, X))             # raw: on a closed line k may be < 0 or l >= m (use % m)
    raise WeldError("unfold did not converge in 64 rounds")
