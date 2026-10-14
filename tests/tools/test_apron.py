"""tools/apron.py — the J1 corner apron's pure geometry (ledger 0054 P1 fix round): the return circle of the design's
radius tangent to the stub's edge at T, its first meeting E with the host's edge, the outline (P0, stub edge, arc, host
edge), a deck whose seams are the existing edge vertices (a cotangent-Laplace film between them), the return curb's
stations and the verge rule. Plain ``test_*``."""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import apron as ap  # noqa: E402

AXIS_DEG = 80.0


def _scene(stub_drop=1.5):
    """host: a straight road along +x, its left edge at z = 12, rows every 3 m rising 2 %; stub: a 26 m road leaving
    it at x ~ 0 heading north (a little east), its right (east) edge the apron side, falling `stub_drop` over 30 m"""
    host_edge = {r: (3.0 * r, 0.10 + 0.02 * 3.0 * r, 12.0) for r in range(-10, 30)}
    rows = list(range(-10, 30))
    ang = math.radians(AXIS_DEG)
    ax, az = math.cos(ang), math.sin(ang)
    nx, nz = az, -ax                           # the stub's right-hand normal (east)
    stub_edge, stub_centre = [], []
    for k in range(0, 14):
        u = -0.4 + 3.0 * k                     # row 0 overlaps the host 0.4 m (trim_connectors' OVERLAP_M)
        cx, cz = ax * u, 12.0 + az * u
        y = 0.10 - stub_drop * max(0.0, u) / 30.0
        stub_centre.append((cx, y, cz))
        stub_edge.append((cx + nx * 13.0, y, cz + nz * 13.0))
    return host_edge, rows, stub_edge, stub_centre


def _design_T(stub_edge, k=8):
    return (stub_edge[k][0] + 0.3, stub_edge[k][2] - 0.2)


def _build(R=30.0, **kw):
    host_edge, rows, stub_edge, stub_centre = _scene(**kw)
    return ap.build(host_edge, rows, stub_edge, stub_centre, _design_T(stub_edge), R), host_edge, stub_edge


def test_the_return_is_tangent_at_T_and_meets_the_host_edge_at_E():
    a, host_edge, stub_edge = _build()
    C, R = a["centre"], a["R"]
    T, E = a["T"], a["E"]
    assert a["T_row"] == 8 and R == 30.0
    assert abs(math.hypot(T[0] - C[0], T[2] - C[1]) - R) < 1e-9
    assert abs(math.hypot(E[0] - C[0], E[2] - C[1]) - R) < 1e-6
    d = a["tangent_T"]
    assert abs((T[0] - C[0]) * d[0] + (T[2] - C[1]) * d[1]) < 1e-9          # radius square to the stub edge at T
    assert abs(E[2] - 12.0) < 1e-9                                            # E on the host edge ...
    r, t = a["E_host"]
    assert a["E_row"] == r + 1 and abs(E[0] - 3.0 * (r + t)) < 1e-6          # ... between rows; the walk resumes next
    assert abs(E[1] - (0.10 + 0.02 * E[0])) < 1e-9                           # at the host's own height
    assert a["arc"][0] == (T[0], T[2]) and a["arc"][-1] == (E[0], E[2])
    assert all(abs(math.hypot(x - C[0], z - C[1]) - R) < 1e-6 for x, z in a["arc"])
    assert all(math.dist(a["arc"][i], a["arc"][i + 1]) <= ap.ARC_STEP_M + 1e-6 for i in range(len(a["arc"]) - 1))
    assert 0.0 < a["entry_deg"] < 90.0
    assert ap.is_simple(a["outline"]) and a["area_m2"] > 20.0


def test_P0_is_where_the_stub_edge_crosses_the_host_edge():
    a, host_edge, stub_edge = _build()
    assert abs(a["P0"][2] - 12.0) < 1e-9
    j, t = a["P0_stub"]
    e0, e1 = stub_edge[j], stub_edge[j + 1]
    assert abs(e0[0] + (e1[0] - e0[0]) * t - a["P0"][0]) < 1e-6
    r, tk = a["P0_host"]
    assert abs(a["P0"][1] - (host_edge[r][1] + (host_edge[r + 1][1] - host_edge[r][1]) * tk)) < 1e-9


def test_the_outline_keeps_the_seams_and_pins_the_arc_where_it_pinches():
    a, host_edge, stub_edge = _build()
    outline, oh, fixed = a["outline"], a["outline_h"], a["outline_fixed"]
    assert len(outline) == len(oh) == len(fixed)
    hv = {(round(p[0], 6), round(p[2], 6)): p[1] for p in host_edge.values()}
    sv = {(round(p[0], 6), round(p[2], 6)): p[1] for p in stub_edge}
    for i, (x, z) in enumerate(outline):
        key = (round(x, 6), round(z, 6))
        if key in hv:
            assert fixed[i] and oh[i] == hv[key]
        if key in sv:
            assert fixed[i] and oh[i] == sv[key]
    # the arc's first points (the cusp at T) are pinned to the stub's run-on, some of its middle is free
    n_stub = a["n_stub"]
    arc_fixed = fixed[n_stub:n_stub + len(a["arc"])]
    assert arc_fixed[0] and arc_fixed[1] and not all(arc_fixed)


def test_the_cotangent_film_keeps_both_seams_and_stays_between_them():
    a, host_edge, stub_edge = _build(stub_drop=2.5)
    outline = a["outline"]
    pts = list(outline) + ap.interior_points(outline)
    tris = _triangulate(pts, outline)
    fixed = {i: a["outline_h"][i] for i in range(len(outline)) if a["outline_fixed"][i]}
    guess = [a["height"](x, z) for x, z in pts]
    h = ap.harmonic_heights(len(pts), tris, fixed, guess, xz=pts)
    for i, v in fixed.items():
        assert h[i] == v
    lo, hi = min(fixed.values()), max(fixed.values())
    assert all(lo - 1e-6 <= v <= hi + 1e-6 for v in h)            # no interior extremum (maximum principle)


def test_the_cotangent_film_has_linear_precision():
    """held on a plane all round, the cotangent film inside is that plane (on stretched 2 m x 0.5 m cells)"""
    xs, zs = [2.0 * i for i in range(7)], [0.5 * j for j in range(7)]
    pts = [(x, z) for z in zs for x in xs]
    tris = []
    for j in range(6):
        for i in range(6):
            a = j * 7 + i
            tris += [(a, a + 1, a + 8), (a, a + 8, a + 7)]
    plane = lambda x, z: 0.3 + 0.01 * x - 0.08 * z  # noqa: E731
    border = {k for k, (x, z) in enumerate(pts) if x in (xs[0], xs[-1]) or z in (zs[0], zs[-1])}
    fixed = {k: plane(*pts[k]) for k in border}
    h = ap.harmonic_heights(len(pts), tris, fixed, [0.0] * len(pts), xz=pts)
    assert max(abs(h[k] - plane(*pts[k])) for k in range(len(pts)) if k not in border) < 1e-6


def _triangulate(pts, outline):
    """a plain-Python stand-in for Blender's CDT: ear-clip the outline, then insert every interior point into the
    triangle that holds it (a valid, if not Delaunay, triangulation of the same vertices)"""
    n = len(outline)
    idx = list(range(n))
    area = ap.polygon_area(outline)
    tris = []
    guard = 0
    while len(idx) > 3 and guard < 100000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = outline[i0], outline[i1], outline[i2]
            cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cr * area <= 1e-12:
                continue
            if any(ap.point_in_polygon([a, b, c], *outline[j]) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            break
    tris.append(tuple(idx[:3]))
    for q in range(n, len(pts)):
        x, z = pts[q]
        for t_i, (i, j, k) in enumerate(tris):
            if ap.point_in_polygon([pts[i], pts[j], pts[k]], x, z):
                tris[t_i:t_i + 1] = [(i, j, q), (j, k, q), (k, i, q)]
                break
    return tris


def test_curb_stations_share_the_end_profiles_and_face_the_wedge():
    a, host_edge, stub_edge = _build()
    arc_h = [a["height"](x, z) for x, z in a["arc"]]
    first = [a["T"], (0, 0, 0), (0, 0, 0), (0, 0, 0)]
    last = [host_edge[a["E_row"]], (1, 1, 1), (1, 1, 1), (1, 1, 1)]
    st = ap.curb_stations(a["arc"], a["centre"], arc_h, first, last, e_normal=(0.0, 1.0))
    assert st[0] == tuple(first) and st[-1] == tuple(last) and len(st) == len(a["arc"]) + 1
    C, R = a["centre"], a["R"]
    for k in range(1, len(st) - 2):
        p0, p1, p2, p3 = st[k]
        assert abs(math.hypot(p0[0] - C[0], p0[2] - C[1]) - R) < 1e-6 and abs(p0[1] - arc_h[k]) < 1e-12
        assert abs(math.hypot(p2[0] - C[0], p2[2] - C[1]) - (R - 1.58)) < 1e-6 and abs(p2[1] - p0[1] - 0.14) < 1e-12
        assert abs(math.hypot(p3[0] - C[0], p3[2] - C[1]) - (R - 2.78)) < 1e-6 and abs(p3[1] - p0[1] + 0.20) < 1e-12
    # the station at E lies along the host's outward normal (here +z), on the host's curb line
    pE = st[-2]
    assert abs(pE[3][0] - pE[0][0]) < 1e-9 and abs(pE[3][2] - pE[0][2] - 2.78) < 1e-9
    assert len(ap.curb_faces(len(st))) == 6 * (len(st) - 1)


def test_seat_target_pins_under_the_apron_and_walk_and_blends_past_it():
    a, host_edge, stub_edge = _build()
    a["arc_h"] = [a["height"](x, z) for x, z in a["arc"]]
    C, R = a["centre"], a["R"]
    mid = a["arc"][len(a["arc"]) // 2]
    w = ((C[0] - mid[0]) / R, (C[1] - mid[1]) / R)              # toward the wedge
    t0 = ap.seat_target(a, mid[0] + w[0] * 1.0, mid[1] + w[1] * 1.0)
    assert t0 is not None and t0[0] == 0.0
    t1 = ap.seat_target(a, mid[0] + w[0] * 7.1, mid[1] + w[1] * 7.1)
    assert t1 is not None and abs(t1[0] - 0.5) < 1e-6
    assert ap.seat_target(a, mid[0] + w[0] * 12.0, mid[1] + w[1] * 12.0) is None
    assert ap.seat_target(a, mid[0] - w[0] * 30.0, mid[1] - w[1] * 30.0) is None


def test_refusals():
    host_edge, rows, stub_edge, stub_centre = _scene()
    T = _design_T(stub_edge)
    for bad in (lambda: ap.build(host_edge, rows, stub_edge, stub_centre, (500.0, 500.0), 30.0),   # no T near
                lambda: ap.build(host_edge, rows, stub_edge, stub_centre, T, 12.0),               # R below 20
                lambda: ap.build(host_edge, rows, stub_edge, stub_centre, T, 45.0),               # R above 40
                lambda: ap.build(host_edge, rows, stub_edge, stub_centre, T, 30.0, design_end_vertex=1.0)):
        try:
            bad()
        except ap.ApronError:
            continue
        raise AssertionError("an impossible apron was built")
    # the right design end passes
    a = ap.build(host_edge, rows, stub_edge, stub_centre, T, 30.0)
    ap.build(host_edge, rows, stub_edge, stub_centre, T, 30.0, design_end_vertex=a["E_vertex"] + 0.5)


def test_trisurface_and_steepest():
    V = [(0.0, 0.0, 0.0), (10.0, 1.0, 0.0), (0.0, 0.0, 10.0)]
    s = ap.TriSurface(V, [(0, 1, 2)])
    assert abs(s.at(5.0, 1.0) - 0.5) < 1e-12 and s.at(20.0, 20.0) is None
    g, t = ap.steepest(V, [(0, 1, 2)])
    assert abs(g - 0.1) < 1e-12 and t == (0, 1, 2)


# --- the mouth fill (route.mouth_fill) ------------------------------------------------------------------------------

def _convex_host_and_mouth():
    """a host whose mouth-side edge bulges (a circle of radius 18 m, the J5 corner's outer edge), a 30 m wide connector
    leaving it square, its end row on the edge line 0.4 m inside at three points: the chords cut ~1.5 m into the host"""
    Rh = 18.0
    host_edge = {}
    for r in range(-25, 26):
        a = math.radians(90.0 - 3.0 * r)
        host_edge[r] = (Rh * math.cos(a), 0.10 + 0.01 * r, Rh * math.sin(a) - Rh)
    rows = list(range(-25, 26))

    def outside(x, z):
        return math.hypot(x, z + Rh) - Rh > ap.FILL_OUT_M
    L, C, R = [], [], []
    for k in range(8):
        u = -0.4 + 3.0 * k
        for line, xo in ((L, -15.0), (C, 0.0), (R, 15.0)):
            z = u if xo == 0.0 else (math.sqrt(max(0.0, (Rh - 0.4) ** 2 - xo * xo)) - Rh if k == 0 else u)
            line.append((xo, 0.10 + 0.002 * u, z))
    return host_edge, rows, L, C, R, outside


def test_the_mouth_fill_starts_at_the_first_row_wholly_outside_and_follows_the_host_edge():
    host_edge, rows, L, C, R, outside = _convex_host_and_mouth()
    # the end row's chords dig into the host: the overlap the fill removes
    mid = ((L[0][0] + C[0][0]) / 2, (L[0][2] + C[0][2]) / 2)
    assert not outside(*mid)
    f = ap.mouth_fill(host_edge, rows, L, C, R, outside)
    assert f["k_star"] == 1
    for p in (L[1], C[1], R[1]):
        assert outside(p[0], p[2])
    # the crossings lie on the host's edge polyline, every outline point is on a seam (host edge, connector edge, row)
    for tag in ("L", "R"):
        x, _y, z = f["crossings"][tag]["xyz"]
        assert abs(math.hypot(x, z + 18.0) - 18.0) < 0.05
    hv = {(round(p[0], 6), round(p[2], 6)) for p in host_edge.values()}
    on_host = [q for q in f["outline"] if (round(q[0], 6), round(q[1], 6)) in hv]
    assert len(on_host) >= 5 and ap.is_simple(f["outline"])
    # nothing of the fill lies inside the host by more than the polyline's chord
    assert all(math.hypot(x, z + 18.0) - 18.0 > -0.05 for x, z in f["outline"])


def test_the_mouth_fill_refuses_a_connector_that_never_leaves_the_host():
    host_edge, rows, L, C, R, _outside = _convex_host_and_mouth()
    try:
        ap.mouth_fill(host_edge, rows, L, C, R, lambda x, z: False)
    except ap.FillError:
        return
    raise AssertionError("a fill was built for a connector wholly inside its host")


def test_densify_puts_points_on_the_straight_seams():
    outline = [(0.0, 0.0), (5.0, 0.0), (5.0, 2.0)]
    hs = [1.0, 2.0, 3.0]
    fx = [True, True, False]
    out, h, f, where = ap.densify(outline, hs, fx, step=1.0)
    assert where == [0, 5, 7] and out[where[1]] == (5.0, 0.0)
    assert out[1:5] == [(1.0, 0.0), (2.0, 0.0), (3.0, 0.0), (4.0, 0.0)] and h[1:5] == [1.2, 1.4, 1.6, 1.8]
    assert all(f[1:5]) and not f[6] and not f[8]          # a segment to a free point gives free points


def test_robust_grade_skips_slivers():
    V = [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (5.0, 0.5, 0.01), (0.0, 0.1, 5.0)]
    assert ap.steepest(V, [(0, 1, 2)])[0] > 10.0           # a 1 cm-wide sliver standing 0.5 m up
    assert ap.robust_grade(V, [(0, 1, 2)]) == 0.0
    assert abs(ap.robust_grade(V, [(0, 1, 3)]) - 0.02) < 1e-9
