"""PHASE 5 stub geometry — the PURE half (no bpy) of tools/author_stubs_blend.py, shared with tools/verify_stubs.py
and the tests. Engine frame throughout: x east, y up, z north; a "row" is the curb strip's 4 profile points
(p0 lane edge, p1 curb top, p2 sidewalk back, p3 grass meet — ribbon.curb_sidewalk).

CURB RETURN (docs/JUNCTIONS.md R5 / R9 / R10, 2.2 rt_macau: "each curb strip wraps a corner-return arc and terminates
at the main-road edge"). At each corner of a stub mouth:
  K   the corner: the stub's road edge line (straight, read off its rows past the weld's re-spread) meets the host's
      road edge line;
  A   the host curb row where gap_mouths' sidewalk gap ENDS on that side (mouth_weld.gap_window — the same window, so the
      return starts exactly on the last host curb row that keeps its faces);
  tH  = |K A|, the tangent length; phi the ground wedge's angle at K between K->A and the stub edge outward;
  R   = tH tan(phi / 2): the circle tangent to the host edge AT A and to the stub edge at B = K + tH (stub outward);
  J   the first stub curb row at or past B — the stub's own curb faces before it are removed (the return replaces them).
The return strip runs A (the host row, copied exactly) -> the arc at <= RETURN_STEP_M stations -> B -> J (the stub row,
copied exactly): the curb wraps the corner and is continuous from the host's strip into the stub's. Every profile
point keeps its offset from the lane edge toward the circle's centre (linear from A's offsets to J's along the path),
compressed so the outermost stays inside COMPRESS_R x R (a tight acute corner never folds the back of walk through
the centre). The CORNER PAVEMENT (the wedge between K, the host edge, the arc and the stub edge) is a fan from K,
merged into the road: single coverage (it never overlaps the host or the stub pavement — its two straight sides lie
ON their edges).

BARRIER: Kevin's concrete_barrier_4m.obj jersey profile (tools/race_furniture.HALF_PROFILE, 1.20 m, 0.67 m base) swept
ACROSS the stub at its declared distance from the mouth line, from the right grass meet over the right sidewalk, the
curb, the carriageway, the left curb and sidewalk to the left grass meet — rings at every profile point of the stub's
own curb row there and every <= BARRIER_RING_M between, each base seated on the LOWEST of the surfaces under its
footprint (front, centre, back) less BARRIER_BURY_M. The texture tiles at the module pitch (u = arc / 4.04 m) so the
module joints read.

Numbers marked [INVENTED] are in fleet/GATES-CHANGELOG.md (2026-10-14, phase 5).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import race_furniture as rf  # noqa: E402

RETURN_STEP_M = 0.3        # JUNCTIONS R5/R10: corner returns at ~0.2-0.3 m stations (macau 0.18 m median)
COMPRESS_R = 0.85          # [INVENTED] the outermost profile point stays inside this x R of the arc
BARRIER_RING_M = 0.25      # [INVENTED] ring spacing across the stub (the curb step is ringed exactly)
BARRIER_BURY_M = 0.02      # [INVENTED] the base sunk this far under the lowest surface under its footprint
BARRIER_H = rf.BARRIER_H
BARRIER_HALF_BASE = rf.HALF_PROFILE[0][0]
PHI_MIN_DEG, PHI_MAX_DEG = 20.0, 160.0


class GeomError(RuntimeError):
    pass


def sub(a, b):
    return (a[0] - b[0], a[2] - b[2])


def unit2(dx, dz):
    L = math.hypot(dx, dz)
    if L < 1e-12:
        raise GeomError("zero-length direction")
    return dx / L, dz / L


def dist2(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def cross2(a, b):
    return a[0] * b[1] - a[1] * b[0]


def line_seg_intersect(p, d, a, b):
    """the infinite line p + s d (plan) vs the segment a-b: (x, z, s, t) or None"""
    e = (b[0] - a[0], b[2] - a[2])
    den = cross2(d, e)
    if abs(den) < 1e-12:
        return None
    w = (a[0] - p[0], a[2] - p[2])
    s = cross2(w, e) / den
    t = cross2(w, d) / den
    if -1e-9 <= t <= 1.0 + 1e-9:
        return p[0] + d[0] * s, p[2] + d[1] * s, s, t
    return None


def corner(K, A0, b_dir):
    """the return's circle: (tH, phi, R, O, a_dir, B) for corner K, host gap-end lane edge A0 and the stub edge's
    outward unit b_dir (plan). Raises GeomError when the wedge is degenerate."""
    a_dir = unit2(A0[0] - K[0], A0[2] - K[2])
    tH = dist2(K, A0)
    c = max(-1.0, min(1.0, a_dir[0] * b_dir[0] + a_dir[1] * b_dir[1]))
    phi = math.acos(c)
    if not (math.radians(PHI_MIN_DEG) <= phi <= math.radians(PHI_MAX_DEG)):
        raise GeomError(f"corner wedge {math.degrees(phi):.1f} deg outside {PHI_MIN_DEG}-{PHI_MAX_DEG}")
    R = tH * math.tan(phi / 2.0)
    bis = unit2(a_dir[0] + b_dir[0], a_dir[1] + b_dir[1])
    h = R / math.sin(phi / 2.0)
    O = (K[0] + bis[0] * h, K[2] + bis[1] * h)
    B = (K[0] + b_dir[0] * tH, K[2] + b_dir[1] * tH)
    return tH, phi, R, O, a_dir, B


def arc_points(A, B, O, step=RETURN_STEP_M):
    """plan points from A to B on the circle about O (the short way), A and B included"""
    a0 = math.atan2(A[1] - O[1], A[0] - O[0])
    a1 = math.atan2(B[1] - O[1], B[0] - O[0])
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    R = math.hypot(A[0] - O[0], A[1] - O[1])
    n = max(2, int(math.ceil(abs(da) * R / step)))
    return [(O[0] + R * math.cos(a0 + da * k / n), O[1] + R * math.sin(a0 + da * k / n)) for k in range(n + 1)], abs(da) * R


def _offsets(row):
    """per profile point: (plan offset from p0, height over p0)"""
    return [dist2(row[p], row[0]) for p in range(4)], [row[p][1] - row[0][1] for p in range(4)]


def return_stations(A_row, J_row, K, b_dir, step=RETURN_STEP_M, y0_of=None):
    """the curb return as station rows (4 engine points each), A_row first and J_row last (exact copies), plus the
    corner record. A_row / J_row: the host gap-end curb row and the stub's first kept curb row. y0_of(x, z): the lane
    edge's height at a station (tools/author_stubs_blend.py blends the host deck and the stub's edge by distance to
    each, so the corner pavement meets both at their own heights); default linear from A to J along the path."""
    A0 = A_row[0]
    tH, phi, R, O, a_dir, B = corner(K, A0, b_dir)
    arc, arc_len = arc_points((A0[0], A0[2]), B, O, step)
    J0 = J_row[0]
    tail = math.hypot(J0[0] - B[0], J0[2] - B[1])
    if (J0[0] - B[0]) * b_dir[0] + (J0[2] - B[1]) * b_dir[1] < -0.05:
        raise GeomError(f"the stub's first kept curb row stands {tail:.2f} m BEFORE the return's end B")
    path = list(arc[1:])                                # arc stations past A (B included)
    nt = int(math.ceil(tail / step)) if tail > 1e-3 else 0
    for k in range(1, nt):
        f = k / nt
        path.append((B[0] + (J0[0] - B[0]) * f, B[1] + (J0[2] - B[1]) * f))
    total = arc_len + tail
    oA, hA = _offsets(A_row)
    oJ, hJ = _offsets(J_row)
    o_max = max(oA[3], oJ[3])
    # the walk + verge (offsets past the curb top) scale about the curb top so the outermost stays inside COMPRESS_R x R
    o_top = oA[1]
    room = COMPRESS_R * R - o_top
    if room <= 0.1:
        raise GeomError(f"return radius {R:.2f} m leaves no room for a walk behind the curb")
    scale = min(1.0, room / (o_max - o_top)) if o_max > o_top else 1.0
    rows = [tuple(tuple(p) for p in A_row)]
    acc = 0.0
    prev = (A0[0], A0[2])
    for k, (x, z) in enumerate(path):
        acc += math.hypot(x - prev[0], z - prev[1])
        prev = (x, z)
        f = min(1.0, acc / total) if total > 0 else 1.0
        on_arc = k < len(arc) - 1
        if on_arc:
            nx, nz = unit2(O[0] - x, O[1] - z)          # outward = toward the circle centre (away from the pavement)
        else:
            nx, nz = unit2(J_row[3][0] - J0[0], J_row[3][2] - J0[2])
        y0 = A0[1] + (J0[1] - A0[1]) * f if y0_of is None else y0_of(x, z)
        row = []
        for p in range(4):
            o = oA[p] + (oJ[p] - oA[p]) * f
            if p >= 2 and on_arc:
                o = oA[1] + (o - oA[1]) * scale if o > oA[1] else o
            h = hA[p] + (hJ[p] - hA[p]) * f
            row.append((x + nx * o, y0 + h, z + nz * o))
        rows.append(tuple(row))
    rows.append(tuple(tuple(p) for p in J_row))
    rec = {"K": [round(K[0], 3), round(K[2], 3)], "A": [round(A0[0], 3), round(A0[2], 3)],
           "B": [round(B[0], 3), round(B[1], 3)], "J": [round(J0[0], 3), round(J0[2], 3)],
           "O": [round(O[0], 3), round(O[1], 3)], "tangent_m": round(tH, 3), "phi_deg": round(math.degrees(phi), 2),
           "radius_m": round(R, 3), "arc_len_m": round(arc_len, 3), "stations": len(rows), "compress": round(scale, 3),
           "n_arc_rows": len(arc)}
    return rows, rec


def strip_faces(n_rows, base=0, P=4):
    """quads between consecutive 4-point rows laid out row-major: [(a, b, c, d)]"""
    out = []
    for r in range(n_rows - 1):
        a, b = base + r * P, base + (r + 1) * P
        for p in range(P - 1):
            out.append((a + p, a + p + 1, b + p + 1, b + p))
    return out


def corner_pavement(K, Ky, rows, n_arc_rows):
    """the corner pavement fan: K plus every station's lane edge from A up to the last ARC station B (rows[:n_arc_rows];
    past B the return runs straight along the stub edge and the stub's own road is the pavement). Returns (verts,
    tris) with tris facing up."""
    edge = [r[0] for r in rows[:n_arc_rows]]
    verts = [(K[0], Ky, K[2])] + [tuple(p) for p in edge]
    tris = []
    for i in range(1, len(verts) - 1):
        t = (0, i, i + 1)
        tris.append(up_facing(verts, t))
    return verts, tris


def up_facing(verts, t):
    a, b, c = verts[t[0]], verts[t[1]], verts[t[2]]
    ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
    return t if ny >= 0 else (t[0], t[2], t[1])


def point_in_poly(x, z, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, zi = poly[i]
        xj, zj = poly[j]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / ((zj - zi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def tri_height(x, z, a, b, c):
    """the height of triangle abc at (x, z) when the point is inside it in plan, else None"""
    d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
    if abs(d) < 1e-12:
        return None
    l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
    l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
    l3 = 1.0 - l1 - l2
    if min(l1, l2, l3) < -1e-7:
        return None
    return l1 * a[1] + l2 * b[1] + l3 * c[1]


# ------------------------------------------------------------------------------------------------ barrier

def barrier_path(right_row, left_row, ring_m=BARRIER_RING_M):
    """plan stations across the stub, right grass meet -> left grass meet: every profile point of both curb rows
    (right p3 p2 p1 p0, left p0 p1 p2 p3) plus <= ring_m between. right_row / left_row: (p0..p3) engine points of the
    stub's curb at the barrier. Returns [(x, z, kind)] with kind in {'p0'..'p3', 'mid'}."""
    key = [(right_row[3], "p3"), (right_row[2], "p2"), (right_row[1], "p1"), (right_row[0], "p0"),
           (left_row[0], "p0"), (left_row[1], "p1"), (left_row[2], "p2"), (left_row[3], "p3")]
    out = []
    for (a, ka), (b, kb) in zip(key, key[1:]):
        if not out:
            out.append((a[0], a[2], ka))
        L = dist2(a, b)
        n = max(1, int(math.ceil(L / ring_m)))
        for k in range(1, n):
            f = k / n
            out.append((a[0] + (b[0] - a[0]) * f, a[2] + (b[2] - a[2]) * f, "mid"))
        out.append((b[0], b[2], kb))
    return out


def barrier_rings(path, base_of, bury=BARRIER_BURY_M, height=BARRIER_H):
    """ring records for race_furniture.strip_mesh. base_of(x, z, ax, az) -> (lowest surface under the footprint,
    [samples]) where (ax, az) is the profile axis (along the stub). Returns (rings, seat rows)."""
    rings, seat = [], []
    arc = 0.0
    n = len(path)
    for i, (x, z, kind) in enumerate(path):
        a = path[max(0, i - 1)]
        b = path[min(n - 1, i + 1)]
        tx, tz = unit2(b[0] - a[0], b[1] - a[1])
        if i > 0:
            arc += math.hypot(x - path[i - 1][0], z - path[i - 1][1])
        ax, az = rf.left_normal(tx, tz)
        low, samples = base_of(x, z, ax, az)
        if low is None:
            raise GeomError(f"no stub surface under the barrier ring at ({x:.2f}, {z:.2f})")
        y = low - bury
        rings.append({"cx": x, "cz": z, "y": y, "tx": tx, "tz": tz, "lat": 0.0, "ls": 1.0, "h": height, "arc": arc})
        seat.append({"x": round(x, 3), "z": round(z, 3), "kind": kind, "base": round(y, 4),
                     "surface": [None if s is None else round(s, 4) for s in samples]})
    return rings, seat


def barrier_mesh(rings):
    """(verts, faces, uvs) engine frame, outward normals (race_furniture.strip_mesh, both ends capped)"""
    return rf.strip_mesh(rings, True, True)


def footprint_samples(x, z, ax, az, half=BARRIER_HALF_BASE):
    """the plan points a ring's base stands on: back toe, centre, front toe (along the profile axis)"""
    return [(x - ax * half, z - az * half), (x, z), (x + ax * half, z + az * half)]
