"""A traced kerb run's cross-section at its MEASURED place across the built ribbon's lane edge (ledger 0081, round 2).

tools/kerb_spans.py measures where the paint sits (in_m / out_m) across the lane edge of the LIVE track's line, and keeps
that edge as lon/lat (edge_lonlat). A port's ribbon is its own line (Lake Murray's assembler smooths it: at High Plains'
apexes its lane edge lies 0.5-1.1 m off the live one), so the paint is placed by where it really is: the live edge point
nearest each ribbon row, moved across by in_m / out_m, read as an offset from THIS ribbon's edge (`edge_delta`). Pure
Python, so the arithmetic is tested without Blender; tools/author_kerbs_blend.py lays the mesh with it when the config
opts in (kerb.placement "measured"; Lake Murray sets no kerbs file at all).

Offsets are metres OUTWARD from the ribbon's lane edge (negative = over the lane). Each vertex's height is `dz` over the
surface under it: the ROAD ribbon's own triangles where the offset is over the lane, the lane edge's height outside it (as
the round-4 kerbs were). Nothing here is measured beyond in_m / out_m and the edge: the raised height is the config's
kerb.height_m and the ramps are author_kerbs_blend's [invented] constants, passed in.
"""
from __future__ import annotations

import math


def nearest_on_polyline(p, poly):
    """(qx, qy) on the polyline `poly` [(x, y), ...] nearest to p = (x, y)."""
    best, bq = None, None
    for (ax, ay), (bx, by) in zip(poly, poly[1:]):
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
        qx, qy = ax + dx * t, ay + dy * t
        d = (p[0] - qx) ** 2 + (p[1] - qy) ** 2
        if best is None or d < best:
            best, bq = d, (qx, qy)
    return bq if bq is not None else tuple(poly[0])


def edge_delta(edge, outward, live_edge):
    """How far OUTWARD of this ribbon's lane edge vertex `edge` (x, y) the measured (live) lane edge lies, metres, along
    the unit `outward` (x, y) across the lane edge. The measured paint then sits at in_m + delta .. out_m + delta."""
    q = nearest_on_polyline(edge, live_edge)
    return (q[0] - edge[0]) * outward[0] + (q[1] - edge[1]) * outward[1]


def section(off_in, off_out, h, paint, lip, ramp_in, ramp_out, drop):
    """[(offset outward of the lane edge, height over the surface under it)] across one row, inner edge first.

    kerb:  (in, lip) -> (in + ramp_in, h) -> (out, h) -> (out + ramp_out, -drop)
    paint: (in, lip) -> (out, lip) -> (out + ramp_out, -drop)      (flat: no height is seen in an image)
    A kerb narrower than its ramp keeps the ramp's top at its outer edge (in < in + ramp_in <= out)."""
    if paint:
        return [(off_in, lip), (off_out, lip), (off_out + ramp_out, -drop)]
    top = min(off_in + ramp_in, off_out - 1e-3)
    return [(off_in, lip), (top, h), (off_out, h), (off_out + ramp_out, -drop)]


def end_scale(arc, length, ramp_m):
    """The raised top's share of h at `arc` metres along a run of `length` m: 1 inside, falling linearly to 0 over the
    last ramp_m at either end (kerb.end_ramp_m, opt-in; None or 0 = full height end to end, as before)."""
    if not ramp_m or ramp_m <= 0:
        return 1.0
    return max(0.0, min(1.0, arc / ramp_m, (length - arc) / ramp_m))


def arc_of(poly, q):
    """Arc length along the polyline `poly` [(x, y), ...] of the point on it nearest q (the run's measured end, read on
    this ribbon's edge rows)."""
    best, at, run = None, 0.0, 0.0
    for (ax, ay), (bx, by) in zip(poly, poly[1:]):
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy)
        t = 0.0 if L < 1e-9 else max(0.0, min(1.0, ((q[0] - ax) * dx + (q[1] - ay) * dy) / (L * L)))
        d = (q[0] - ax - dx * t) ** 2 + (q[1] - ay - dy * t) ** 2
        if best is None or d < best:
            best, at = d, run + L * t
        run += L
    return at


def clipped_rows(arcs, s_start, s_end):
    """The cross-sections a run is laid on between its measured ends: [(i, j, t)] — the section is row i's lerped toward
    row j by t — at s_start, at every row strictly inside, and at s_end (arcs ascending, one per row)."""
    def at(s):
        for i in range(len(arcs) - 1):
            if arcs[i] <= s <= arcs[i + 1]:
                span = arcs[i + 1] - arcs[i]
                return (i, i + 1, 0.0 if span < 1e-9 else (s - arcs[i]) / span)
        return (0, 0, 0.0) if s < arcs[0] else (len(arcs) - 1, len(arcs) - 1, 0.0)
    inner = [(i, i, 0.0) for i, a in enumerate(arcs) if s_start + 1e-6 < a < s_end - 1e-6]
    return [at(s_start)] + inner + [at(s_end)]


def outward_unit(edge, centre):
    dx, dy = edge[0] - centre[0], edge[1] - centre[1]
    n = math.hypot(dx, dy) or 1.0
    return dx / n, dy / n
