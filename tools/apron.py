"""An authored corner APRON between a ribbon-through weld and its host (ledger 0054 P1 fix round; EXPANSION-PLAN A5 / P3).

At J1 (College / Navajo / Waring) Waring's NE curb does not meet the loop's outer curb at the straight line the welded
stub ribbon ends on (v1520.4): it sweeps round a free-flow return of R ~30 m and meets it at ~v1527.5 (A5). A 3-line
connector ribbon cannot carry that return: its end row is a straight ruler laid on the loop's curved, graded edge at
three points, and across the return the ruler stood 2.9-4 cm proud of the loop (the weld allows 2 cm). So the stub is
welded with Waring's straight curbs and the return is this apron — its own piece, pure geometry here, built in Blender
by tools/author_aprons_blend.py:

  P0  where the stub's road edge on the apron side crosses the host's road edge (the straight weld's corner)
  T   the stub edge vertex nearest the design tangent point (data/expansion.north.json welds[].aprons[].polygon_xz[0])
  arc the circle of the design's radius (welds[].curbs.<side>.return.R, 30 m; the dossier's 20-40 m) tangent to the
      stub's edge at T, its centre on the apron side: the return curb's pavement edge
  E   where that circle first meets the host's road edge (on a host segment; within one vertex of the design's own
      apron end, welds[].aprons[].loop_edge_vertices[1]); the host's curb + walk resumes at the next row, E_row, and
      the return's curb runs on along the host's curb line to it (gap_mouths deletes a host strip face only when both
      its stations are gapped)
  apron  the pavement between the stub edge P0 -> T, the arc T -> E and the host edge E -> P0

Heights (the deck): on the host edge the host's own vertices and on the stub edge the stub's own (L3: the loop is never
moved to meet a new road); arc points pinched within CUSP_M of either seam (the cusp at T, the shallow entry at E) that
seam's level run-on; every other vertex the soap film between them (harmonic_heights, the cotangent Laplacian on
Blender's constrained Delaunay mesh of the outline + a 1 m grid). The return arc is a free edge.

The return curb + sidewalk is build_loop_blend's curb_sidewalk profile (lane edge, +0.14 m curb top over 0.08 m,
1.5 m walk, 1.2 m grade down to edge - 0.20 m) swept along the arc toward the wedge (the circle's centre), its first
station the stub's own curb profile at T, its station at E turned to the host's outward normal, its last the host's
own profile at E_row.

No bpy, no numpy: tests/tools/test_apron.py runs it in plain Python.
"""
from __future__ import annotations

import math

R_MIN_M, R_MAX_M = 20.0, 40.0      # the dossier's J1 NE return, R ~30 +- 10 m (EXPANSION-PLAN A5)
T_SNAP_MAX_M = 3.0                 # the stub edge vertex taken as T lies within this of the design tangent point
ARC_STEP_M = 0.75                  # [invented] arc (return curb) points at most this far apart
GRID_M = 1.0                       # [invented] interior deck points every this (the CDT fills between)
GRID_CLEAR_M = 0.35                # ... none closer than this to the apron's outline
CUSP_M = 1.0                       # [invented] arc points this close to a seam take its run-on (the outline pinches)
PROFILE = ((0.0, 0.0), (0.08, 0.14), (1.58, 0.14), (2.78, -0.20))   # curb_sidewalk(lift 0.10, curb_h 0.14,
#   curb_face_w 0.08, sidewalk_w 1.5, grade_w 1.2, grass_clearance 0.10) relative to the pavement edge


class ApronError(RuntimeError):
    """an apron that cannot be built honestly — the caller stops loudly"""


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _norm(a):
    L = math.hypot(a[0], a[1])
    if L < 1e-12:
        raise ApronError("degenerate direction")
    return (a[0] / L, a[1] / L)


def seg_cross(a, b, c, d):
    """(t on a->b, u on c->d) where the two plan segments cross, else None"""
    r, q = _sub(b, a), _sub(d, c)
    den = _cross(r, q)
    if abs(den) < 1e-12:
        return None
    w = _sub(c, a)
    t = _cross(w, q) / den
    u = _cross(w, r) / den
    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return t, u
    return None


def project_polyline(P, x, z):
    """(distance, segment i, t, height lerp) of (x, z) onto the 3-D polyline P [(x, y, z)] in plan; the height is the
    polyline's at the projection (a level run-on off its side)"""
    best = None
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        dx, dz = b[0] - a[0], b[2] - a[2]
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[2]) * dz) / L2))
        d = math.hypot(x - (a[0] + t * dx), z - (a[2] + t * dz))
        if best is None or d < best[0]:
            best = (d, i, t, a[1] + (b[1] - a[1]) * t)
    return best


def point_in_polygon(poly, x, z):
    inside = False
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if (a[1] > z) != (b[1] > z):
            xc = a[0] + (z - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if xc > x:
                inside = not inside
    return inside


def polygon_area(poly):
    return 0.5 * sum(_cross(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def dist_to_outline(poly, x, z):
    best = float("inf")
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / L2))
        best = min(best, math.hypot(x - (a[0] + t * dx), z - (a[1] + t * dz)))
    return best


def is_simple(poly):
    """no two non-adjacent outline segments cross"""
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            c, d = poly[j], poly[(j + 1) % n]
            hit = seg_cross(a, b, c, d)
            if hit is not None and 1e-6 < hit[0] < 1 - 1e-6 and 1e-6 < hit[1] < 1 - 1e-6:
                return False
    return True


def arc_points(C, R, T, E, d, step=ARC_STEP_M):
    """plan points from T to E on the circle (C, R), leaving T along d"""
    a0 = math.atan2(T[1] - C[1], T[0] - C[0])
    a1 = math.atan2(E[1] - C[1], E[0] - C[0])
    # the sweep sense whose tangent at T is d: d(angle) > 0 moves along (-sin, cos)
    ccw = _dot((-math.sin(a0), math.cos(a0)), d) > 0
    da = (a1 - a0) % (2 * math.pi) if ccw else -((a0 - a1) % (2 * math.pi))
    n = max(2, int(math.ceil(abs(da) * R / step)))
    out = [(C[0] + R * math.cos(a0 + da * k / n), C[1] + R * math.sin(a0 + da * k / n)) for k in range(n + 1)]
    out[0], out[-1] = (T[0], T[1]), (E[0], E[1])
    return out, abs(da) * R


def circle_hits(C, R, a, b):
    """parameters t in [0, 1] along plan segment a -> b where it meets the circle (C, R)"""
    d = _sub(b, a)
    f = _sub(a, C)
    A = _dot(d, d)
    if A < 1e-12:
        return []
    Bq = 2 * _dot(f, d)
    Cq = _dot(f, f) - R * R
    disc = Bq * Bq - 4 * A * Cq
    if disc < 0:
        return []
    r = math.sqrt(disc)
    return sorted(t for t in ((-Bq - r) / (2 * A), (-Bq + r) / (2 * A)) if -1e-9 <= t <= 1 + 1e-9)


def _max_grade(P):
    g = 0.0
    for i in range(len(P) - 1):
        L = math.hypot(P[i + 1][0] - P[i][0], P[i + 1][2] - P[i][2])
        if L > 1e-6:
            g = max(g, abs(P[i + 1][1] - P[i][1]) / L)
    return g


def build(host_edge, host_rows_idx, stub_edge, stub_centre, design_T, R, design_end_vertex=None):
    """The apron's plan + heights.

    host_edge         {row: (x, y, z)} the host's road edge on the mouth side (welded mesh), rows around the mouth
    host_rows_idx     the host rows in order along the host (a window containing P0 .. E, increasing vertex)
    stub_edge         [(x, y, z)] the stub's road edge on the apron side, row 0 at the cut, outward
    stub_centre       [(x, y, z)] the stub's centre rows (same order)
    design_T          (x, z) the design tangent point
    R                 the return's radius (the design's; R_MIN_M .. R_MAX_M)
    design_end_vertex the design's true end on the host (fractional vertex): E must land within 1 vertex of it

    The return is the circle of radius R tangent to the stub's edge at T (the stub edge vertex nearest design_T, its
    centre on the apron side); E is where it first meets the host's edge (on a host segment) and the host's walk resumes
    at the next row, E_row. Returns a dict: P0 (x, y, z), P0_host (row, t), P0_stub (row, t), T_row, T (x, y, z),
    E (x, y, z), E_host (row, t), E_row, E_vertex, centre, R, entry_deg, arc [(x, z)] (T .. E), outline [(x, z)] (P0,
    the stub edge rows, the arc, the host edge rows back), outline_h (the seams' own heights; a run-on estimate on the
    free arc), outline_fixed (True on the seams and on arc points within CUSP_M of either, where the outline pinches),
    n_stub, area_m2, height(x, z) the distance-blend estimate (the deck's starting guess), seam_grade (the steepest
    grade along either seam)."""
    hw = [r for r in host_rows_idx if r in host_edge]
    H = [host_edge[r] for r in hw]
    # P0: the stub edge (rows 0 -> outward) crossing the host edge
    p0 = None
    for j in range(len(stub_edge) - 1):
        a, b = (stub_edge[j][0], stub_edge[j][2]), (stub_edge[j + 1][0], stub_edge[j + 1][2])
        for k in range(len(H) - 1):
            hit = seg_cross(a, b, (H[k][0], H[k][2]), (H[k + 1][0], H[k + 1][2]))
            if hit is not None:
                p0 = (j, hit[0], k, hit[1])
                break
        if p0 is not None:
            break
    if p0 is None:
        raise ApronError("the stub's apron-side edge never crosses the host edge in the window")
    j0, tj, k0, tk = p0
    ha, hb = H[k0], H[k0 + 1]
    P0 = (ha[0] + (hb[0] - ha[0]) * tk, ha[1] + (hb[1] - ha[1]) * tk, ha[2] + (hb[2] - ha[2]) * tk)
    P0_host_row = hw[k0]
    # T: the stub edge vertex nearest the design tangent point (outward of P0)
    cand = [(math.hypot(stub_edge[j][0] - design_T[0], stub_edge[j][2] - design_T[1]), j)
            for j in range(j0 + 1, len(stub_edge) - 1)]
    if not cand:
        raise ApronError("no stub edge row outward of P0")
    dT, kT = min(cand)
    if dT > T_SNAP_MAX_M:
        raise ApronError(f"no stub edge vertex within {T_SNAP_MAX_M} m of the design tangent point (nearest {dT:.2f} m)")
    if not R_MIN_M <= R <= R_MAX_M:
        raise ApronError(f"the return's R {R:.1f} m is outside the dossier's {R_MIN_M:.0f}-{R_MAX_M:.0f} m")
    T3 = stub_edge[kT]
    T = (T3[0], T3[2])
    d = _norm(_sub((stub_edge[kT - 1][0], stub_edge[kT - 1][2]), (stub_edge[kT + 1][0], stub_edge[kT + 1][2])))
    n = _norm(_sub(T, (stub_centre[kT][0], stub_centre[kT][2])))
    n = (n[0] - _dot(n, d) * d[0], n[1] - _dot(n, d) * d[1])     # square to the tangent
    n = _norm(n)
    C = (T[0] + R * n[0], T[1] + R * n[1])
    # E: the first meeting of the circle (swept from T along d) with the host edge, past P0
    a0 = math.atan2(T[1] - C[1], T[0] - C[0])
    ccw = _dot((-math.sin(a0), math.cos(a0)), d) > 0
    best = None
    for k in range(k0, len(H) - 1):
        a, b = (H[k][0], H[k][2]), (H[k + 1][0], H[k + 1][2])
        for t in circle_hits(C, R, a, b):
            if k == k0 and t < tk:
                continue
            q = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            aq = math.atan2(q[1] - C[1], q[0] - C[0])
            sweep = (aq - a0) % (2 * math.pi) if ccw else (a0 - aq) % (2 * math.pi)
            if best is None or sweep < best[0]:
                best = (sweep, k, t, q)
    if best is None:
        raise ApronError(f"the R {R:.1f} m return from T never meets the host edge in the window")
    _sw, kE, tE, Eq = best
    hE0, hE1 = H[kE], H[kE + 1]
    E3 = (Eq[0], hE0[1] + (hE1[1] - hE0[1]) * tE, Eq[1])
    E_row = hw[kE + 1]
    e_vertex = hw[kE] + tE
    if design_end_vertex is not None and abs(e_vertex - float(design_end_vertex)) > 1.0:
        raise ApronError(f"the return meets the host at v{e_vertex:.2f}, the design says v{float(design_end_vertex):.2f}")
    arc, arc_len = arc_points(C, R, T, (E3[0], E3[2]), d)
    tE_arc = _norm(_sub(arc[-1], arc[-2]))
    tE_host = _norm(_sub((hE1[0], hE1[2]), (hE0[0], hE0[2])))
    entry = math.degrees(math.acos(max(-1.0, min(1.0, _dot(tE_arc, tE_host)))))
    # the outline: P0, the stub edge rows j0+1 .. kT, the arc (T excluded, E included), the host edge rows kE .. k0+1
    stub_part = [(stub_edge[j][0], stub_edge[j][2]) for j in range(j0 + 1, kT + 1)]
    back_i = [i for i in range(kE, k0, -1) if math.hypot(H[i][0] - E3[0], H[i][2] - E3[2]) >= 1e-6]
    host_back = [(H[i][0], H[i][2]) for i in back_i]
    outline = [(P0[0], P0[2])] + stub_part + arc[1:] + host_back
    if not is_simple(outline):
        raise ApronError("the apron's outline crosses itself")
    hpoly = list(H)
    spoly = list(stub_edge[: kT + 2])

    def height(x, z):
        dh, _i, _t, yh = project_polyline(hpoly, x, z)
        ds, _i2, _t2, ys = project_polyline(spoly, x, z)
        if dh + ds < 1e-9:
            return yh
        return (yh * ds + ys * dh) / (dh + ds)
    # the outline's own heights: the seams' existing vertices exactly (P0 / E the host's); arc points pinched within
    # CUSP_M of a seam take that seam's level run-on (the cusp at T, where the arc leaves the stub edge tangentially,
    # and the shallow entry at E: a sliver triangle between a free arc point and a seam vertex would be a crease)
    oh, fixed = [P0[1]], [True]
    for j in range(j0 + 1, kT + 1):
        oh.append(stub_edge[j][1])
        fixed.append(True)
    for x, z in arc[1:-1]:
        ds, _i, _t, ys = project_polyline(spoly, x, z)
        dh, _i2, _t2, yh = project_polyline(hpoly, x, z)
        if ds <= CUSP_M and ds <= dh:
            oh.append(ys)
            fixed.append(True)
        elif dh <= CUSP_M:
            oh.append(yh)
            fixed.append(True)
        else:
            oh.append(height(x, z))
            fixed.append(False)
    oh.append(E3[1])
    fixed.append(True)
    for i in back_i:
        oh.append(H[i][1])
        fixed.append(True)
    if not len(oh) == len(outline) == len(fixed):
        raise ApronError("internal: outline / heights length mismatch")
    seam_grade = max(_max_grade(list(stub_edge[j0: kT + 2])), _max_grade(H[k0: kE + 2]))
    return {"P0": P0, "P0_host": (P0_host_row, tk), "P0_stub": (j0, tj), "T_row": kT, "T": T3, "E": E3,
            "E_host": (hw[kE], tE), "E_row": E_row, "E_vertex": e_vertex, "centre": C, "R": R, "arc": arc,
            "arc_len_m": arc_len, "entry_deg": entry, "outline": outline, "outline_h": oh, "outline_fixed": fixed,
            "n_stub": len(stub_part), "area_m2": abs(polygon_area(outline)), "height": height,
            "seam_grade": seam_grade, "tangent_T": d, "normal_T": n}


def interior_points(outline, step=GRID_M, clear=GRID_CLEAR_M):
    """a square grid of interior deck points, none within `clear` of the outline"""
    xs = [p[0] for p in outline]
    zs = [p[1] for p in outline]
    out = []
    x = math.floor(min(xs) / step) * step
    while x <= max(xs):
        z = math.floor(min(zs) / step) * step
        while z <= max(zs):
            if point_in_polygon(outline, x, z) and dist_to_outline(outline, x, z) >= clear:
                out.append((x, z))
            z += step
        x += step
    return out


def curb_stations(arc, centre, arc_h, first, last, e_normal=None):
    """the return curb's profile rows: [(p0, p1, p2, p3)] each (x, y, z). `first` = the stub's own profile row at T
    (shared exactly); the arc's interior stations swept toward the circle's centre (the wedge); the station at E (the
    arc's end, on the host edge) swept along `e_normal` (the host's outward normal there, so the last run lies on the
    host's curb line); then `last` = the host's own profile row at E_row (shared exactly)"""
    rows = [tuple(first)]
    for i in range(1, len(arc)):
        x, z = arc[i]
        w = _norm(_sub(centre, (x, z))) if (i < len(arc) - 1 or e_normal is None) else e_normal
        h = arc_h[i]
        rows.append(tuple((x + w[0] * o, h + dy, z + w[1] * o) for o, dy in PROFILE))
    rows.append(tuple(last))
    return rows


def curb_faces(nst, p=4):
    """triangles (vertex indices) of a profile strip with nst stations of p points each"""
    tris = []
    for k in range(nst - 1):
        a, b = k * p, (k + 1) * p
        for q in range(p - 1):
            tris.append((a + q, a + q + 1, b + q + 1))
            tris.append((a + q, b + q + 1, b + q))
    return tris


def seat_target(ap, x, z, *, sidewalk_m=3.1, band_m=8.0, lift=0.10, clear=0.06):
    """tools/seat_terrain_blend.py's verge rule for the apron: (t, target) — t = 0 under the apron and the return's
    sidewalk band (pinned to the edge - LIFT - CLEAR_M), 0 < t < 1 across the blend band past it, None elsewhere (off
    the wedge side of the arc, or past either end of it)"""
    if point_in_polygon(ap["outline"], x, z):
        return 0.0, ap["height"](x, z) - lift - clear
    C, R = ap["centre"], ap["R"]
    dc = math.hypot(x - C[0], z - C[1])
    if dc >= R:
        return None
    off = R - dc                                     # behind the return's pavement edge, toward the wedge
    if off > sidewalk_m + band_m:
        return None
    # the projection must fall within the arc (not past T or E)
    ang = math.atan2(z - C[1], x - C[0])
    arc = ap["arc"]
    a0 = math.atan2(arc[0][1] - C[1], arc[0][0] - C[0])
    a1 = math.atan2(arc[-1][1] - C[1], arc[-1][0] - C[0])
    mid = math.atan2(arc[len(arc) // 2][1] - C[1], arc[len(arc) // 2][0] - C[0])

    def rel(a):
        return (a - mid + math.pi) % (2 * math.pi) - math.pi
    lo, hi = sorted((rel(a0), rel(a1)))
    r = rel(ang)
    if not lo <= r <= hi:
        return None
    k = min(range(len(arc)), key=lambda i: math.hypot(arc[i][0] - x, arc[i][1] - z))
    edge_h = ap["arc_h"][k]
    target = edge_h - lift - clear
    if off <= sidewalk_m:
        return 0.0, target
    return (off - sidewalk_m) / band_m, target


def harmonic_heights(n_verts, tris, fixed, guess, xz=None, iters=20000, tol=1e-7):
    """THE DECK BETWEEN THE SEAMS. The heights of every vertex not in `fixed` ({index: height} - the host's and the
    stub's own edge vertices, the two seams, and the arc points pinched against them) chosen to make the deck as smooth
    as it can be: a discrete Laplace surface, the soap film stretched between the fixed edges. The rest of the return
    arc is a free edge (no height imposed): it climbs from the stub's height at T to the loop's at E wherever the film
    puts it. With `xz` (each vertex's plan position) the Laplacian is the cotangent one (the continuous surface's own,
    whatever the triangles' shapes; non-negative on a Delaunay mesh), else each free vertex is its neighbours' mean.
    Gauss-Seidel from `guess`. (A distance blend of the two edges' run-ons put an 18.9 % cross-fall beside the stub's
    tail on the first dry run; uniform weights 26.7 % beside the host's edge, where the grid points meet 3 m rows.)"""
    w = [dict() for _ in range(n_verts)]

    def add(i, j, v):
        w[i][j] = w[i].get(j, 0.0) + v
        w[j][i] = w[j].get(i, 0.0) + v
    for a, b, c in tris:
        if xz is None:
            for i, j in ((a, b), (b, c), (c, a)):
                w[i][j] = 1.0
                w[j][i] = 1.0
            continue
        for i, j, k in ((a, b, c), (b, c, a), (c, a, b)):
            # the angle at k, opposite edge i-j
            u = (xz[i][0] - xz[k][0], xz[i][1] - xz[k][1])
            v = (xz[j][0] - xz[k][0], xz[j][1] - xz[k][1])
            cr = abs(u[0] * v[1] - u[1] * v[0])
            add(i, j, 0.5 * max(0.0, (u[0] * v[0] + u[1] * v[1]) / cr) if cr > 1e-12 else 0.0)
    h = list(guess)
    for i, v in fixed.items():
        h[i] = v
    free = [i for i in range(n_verts) if i not in fixed and w[i] and sum(w[i].values()) > 1e-12]
    for _ in range(iters):
        dmax = 0.0
        for i in free:
            tot = sum(w[i].values())
            v = sum(h[j] * wij for j, wij in w[i].items()) / tot
            dmax = max(dmax, abs(v - h[i]))
            h[i] = v
        if dmax < tol:
            break
    return h


class TriSurface:
    """height queries on a triangle set [(x, y, z)] in plan"""

    def __init__(self, verts, tris, cell=2.0):
        self.v, self.t, self.cell = verts, tris, cell
        self.cells = {}
        for k, (a, b, c) in enumerate(tris):
            xs = [verts[q][0] for q in (a, b, c)]
            zs = [verts[q][2] for q in (a, b, c)]
            for ix in range(int(math.floor(min(xs) / cell)), int(math.floor(max(xs) / cell)) + 1):
                for iz in range(int(math.floor(min(zs) / cell)), int(math.floor(max(zs) / cell)) + 1):
                    self.cells.setdefault((ix, iz), []).append(k)

    def at(self, x, z):
        for k in self.cells.get((int(math.floor(x / self.cell)), int(math.floor(z / self.cell))), ()):
            a, b, c = (self.v[q] for q in self.t[k])
            d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(d) < 1e-12:
                continue
            w1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
            w2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
            w3 = 1.0 - w1 - w2
            if min(w1, w2, w3) >= -1e-9:
                return w1 * a[1] + w2 * b[1] + w3 * c[1]
        return None


def steepest(verts, tris):
    """(grade, triangle) of the steepest deck triangle"""
    best = (0.0, None)
    for t in tris:
        p, q, r = (verts[i] for i in t)
        ux, uy, uz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
        vx, vy, vz = r[0] - p[0], r[1] - p[1], r[2] - p[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        if abs(ny) > 1e-12:
            g = math.hypot(nx, nz) / abs(ny)
            if g > best[0]:
                best = (g, t)
    return best


# --------------------------------------------------------------------------------------------- the mouth fill

FILL_OUT_M = 0.05          # [invented] a connector row is "outside" the host when every point of it stands this far
                           # past the host's edge


class FillError(ApronError):
    """a mouth fill that cannot be built honestly"""


def _cross_polyline(a, b, H):
    """(t on a->b, host segment k, u on it) of the first crossing of plan segment a-b with polyline H [(x, y, z)]"""
    best = None
    for k in range(len(H) - 1):
        hit = seg_cross(a, b, (H[k][0], H[k][2]), (H[k + 1][0], H[k + 1][2]))
        if hit is not None and (best is None or hit[0] < best[0]):
            best = (hit[0], k, hit[1])
    return best


def mouth_fill(host_edge, host_rows_idx, L, C, R, outside):
    """THE MOUTH FILL (ledger 0054 P1 fix round, opt-in route.mouth_fill). A welded connector's end row lies on its
    host's edge line 0.4 m inside it at three points (L, C, R); on a convex host edge the straight chords between them
    cut deeper (J5: 2.55 m into the Navajo / Jackson corner's outer lane), so two road sheets lie within 1.9 cm of each
    other over the overlap — and the kn5 prep's anti-poke, which walks down road sheets 2 cm at a time, cannot see the
    lower one: the grass pinned 2 cm under the upper sheet stood 3 mm under the lower (verify_mouths HOST LANE, J5
    v2318 lat 11.5; J1 5 m past the cut). The fill replaces the connector's strips from its end out to its first row
    k* that stands wholly outside the host (`outside(x, z)` for its three points and both chords) with one piece whose
    outline is the host's own edge between the connector's two road edges' crossings of it, those edges out to k*,
    and row k*: no road over the host's pavement but the host's.

    host_edge {row: (x, y, z)} the host's road edge on the mouth side; host_rows_idx the rows in order along the host;
    L / C / R the connector's lines from its end row outward [(x, y, z)]. Returns {k_star, outline [(x, z)],
    outline_h, crossings: {"L": (host row, t, line seg j, t), "R": ...}, area_m2, seam_grade}."""
    hw = [r for r in host_rows_idx if r in host_edge]
    H = [host_edge[r] for r in hw]
    n = len(C)
    k_star = None
    for k in range(1, n):
        pts = (L[k], C[k], R[k])
        if not all(outside(p[0], p[2]) for p in pts):
            continue
        if any(_cross_polyline((a[0], a[2]), (b[0], b[2]), H) is not None for a, b in ((L[k], C[k]), (C[k], R[k]))):
            continue
        k_star = k
        break
    if k_star is None:
        raise FillError("no connector row stands wholly outside the host")
    cross = {}
    for tag, line in (("L", L), ("R", R)):
        hit = None
        for j in range(k_star - 1, -1, -1):
            h = _cross_polyline((line[j][0], line[j][2]), (line[j + 1][0], line[j + 1][2]), H)
            if h is not None:
                hit = (j,) + h
                break
        if hit is None:
            raise FillError(f"the connector's {tag} edge never crosses the host edge inside row {k_star}")
        j, t, k, u = hit
        a, b = H[k], H[k + 1]
        cross[tag] = {"seg": j, "t": t, "host_k": k, "host_u": u,
                      "xyz": (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u)}
    # the outline: XL, the host's edge vertices between the two crossings, XR, R out to k*, C k*, L back to XL
    kl, kr = cross["L"]["host_k"], cross["R"]["host_k"]
    ul, ur = cross["L"]["host_u"], cross["R"]["host_u"]
    if (kl, ul) <= (kr, ur):
        between = [H[i] for i in range(kl + 1, kr + 1)]
    else:
        between = [H[i] for i in range(kl, kr, -1)]
    pts3 = [cross["L"]["xyz"]] + between + [cross["R"]["xyz"]]
    pts3 += [R[j] for j in range(cross["R"]["seg"] + 1, k_star + 1)]
    pts3 += [C[k_star]]
    pts3 += [L[j] for j in range(k_star, cross["L"]["seg"], -1)]
    # drop coincident neighbours (a crossing landing on a vertex)
    clean = []
    for p in pts3:
        if not clean or math.hypot(p[0] - clean[-1][0], p[2] - clean[-1][2]) > 1e-6:
            clean.append(p)
    if math.hypot(clean[0][0] - clean[-1][0], clean[0][2] - clean[-1][2]) <= 1e-6:
        clean.pop()
    outline = [(p[0], p[2]) for p in clean]
    if not is_simple(outline):
        raise FillError("the fill's outline crosses itself")
    seam_grade = max(_max_grade(H[min(kl, kr): max(kl, kr) + 2]),
                     _max_grade(list(L[: k_star + 1])), _max_grade(list(R[: k_star + 1])),
                     _max_grade([L[k_star], C[k_star], R[k_star]]))
    return {"k_star": k_star, "outline": outline, "outline_h": [p[1] for p in clean], "crossings": cross,
            "area_m2": abs(polygon_area(outline)), "seam_grade": seam_grade}


BOUNDARY_STEP_M = 1.0      # [invented] outline segments longer than this get points on them for the CDT (the deck's
                           # triangles then meet the 1 m grid well shaped, not as 3-13 m slivers along the seams)


def densify(outline, heights, fixed, step=BOUNDARY_STEP_M):
    """points on every outline segment longer than `step`, ON the straight 3-D segment (a seam stays an existing edge:
    a point on it and its linear height leave no crack). Returns (outline, heights, fixed, where) — where[i] the new
    index of original outline vertex i; an inserted point is fixed when both its ends are"""
    out, hs, fx, where = [], [], [], []
    n = len(outline)
    for i in range(n):
        a, b = outline[i], outline[(i + 1) % n]
        ha, hb = heights[i], heights[(i + 1) % n]
        where.append(len(out))
        out.append(a)
        hs.append(ha)
        fx.append(fixed[i])
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        k = int(math.ceil(L / step)) if L > step else 1
        for q in range(1, k):
            t = q / k
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            hs.append(ha + (hb - ha) * t)
            fx.append(fixed[i] and fixed[(i + 1) % n])
    return out, hs, fx, where


def robust_grade(verts, tris, min_alt=0.25):
    """the steepest grade of any deck triangle whose smallest altitude is at least `min_alt` (a sliver's facet slope is
    its heights' rounding over centimetres; the well-shaped ones carry the surface)"""
    g = 0.0
    for t in tris:
        p, q, r = (verts[i] for i in t)
        area2 = abs((q[0] - p[0]) * (r[2] - p[2]) - (q[2] - p[2]) * (r[0] - p[0]))
        longest = max(math.hypot(a[0] - b[0], a[2] - b[2]) for a, b in ((p, q), (q, r), (r, p)))
        if longest < 1e-9 or area2 / longest < min_alt:
            continue
        g = max(g, steepest(verts, [t])[0])
    return g
