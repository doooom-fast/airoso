"""tools/stub_geom.py — the phase-5 stub's pure geometry (ledger 0054, 2026-10-14): the curb return round each mouth
corner, the corner pavement fan, and the K-rail barrier across the stub.

A right-angle corner (wedge 90 deg, tangent 3 m) is a true quarter circle of R 3 m whose first row IS the host's
gap-end row and whose last row IS the stub's first kept curb row (exact copies: the curb is continuous), every station
on the arc within RETURN_STEP_M, the walk never folding through the circle's centre; a 60-deg wedge compresses the
walk; the corner pavement covers exactly the wedge minus the circle's quadrant, facing up; the barrier path rings
every profile point from grass meet to grass meet at <= BARRIER_RING_M and the swept K-rail is a closed solid seated
on the lowest surface under its footprint less the bury.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import race_furniture as rf  # noqa: E402
import stub_geom as sg  # noqa: E402

PROF_H = ((0.0, 0.0), (0.08, 0.14), (1.88, 0.14), (3.08, -0.20))   # host curb profile (walk 1.8 m)
PROF_C = ((0.0, 0.0), (0.08, 0.14), (1.58, 0.14), (2.78, -0.20))   # connector curb profile (walk 1.5 m)


def _row(x, z, y, nx, nz, prof):
    return tuple((x + nx * o, y + h, z + nz * o) for o, h in prof)


def _right_angle(tH=3.0, wedge_deg=90.0, y=10.0):
    """host edge along +x at z = 0 (host pavement at z < 0, ground at z > 0); the corner K at the origin; the stub's
    edge leaves K at `wedge_deg` from the host edge's +x, its pavement on the -x side of that edge"""
    K = (0.0, y, 0.0)
    A_row = _row(tH, 0.0, y, 0.0, 1.0, PROF_H)                     # host gap-end row: outward = +z
    a = math.radians(wedge_deg)
    b_dir = (math.cos(a), math.sin(a))
    J = tH + 0.6
    jx, jz = b_dir[0] * J, b_dir[1] * J
    out = (b_dir[1], -b_dir[0])                                    # away from the stub's pavement
    J_row = _row(jx, jz, y + 0.02, out[0], out[1], PROF_C)
    return K, A_row, J_row, b_dir


def test_right_angle_return_is_a_quarter_circle_welded_to_both_strips():
    K, A_row, J_row, b_dir = _right_angle()
    rows, rec = sg.return_stations(A_row, J_row, K, b_dir)
    assert abs(rec["radius_m"] - 3.0) < 1e-6 and abs(rec["phi_deg"] - 90.0) < 1e-6
    assert rows[0] == A_row and rows[-1] == J_row                   # exact copies: the curb is continuous
    O = rec["O"]
    assert abs(O[0] - 3.0) < 1e-6 and abs(O[1] - 3.0) < 1e-6
    n_arc = rec["n_arc_rows"]
    for r in rows[1:n_arc]:
        assert abs(math.hypot(r[0][0] - O[0], r[0][2] - O[1]) - 3.0) < 1e-6   # the lane edge ON the circle
        assert math.hypot(r[3][0] - O[0], r[3][2] - O[1]) > 0.0              # the walk stays on this side of O
    for a, b in zip(rows, rows[1:]):
        assert math.hypot(b[0][0] - a[0][0], b[0][2] - a[0][2]) <= sg.RETURN_STEP_M + 1e-6
    # every station's walk stands 0.14 m over its lane edge (interpolated between the two strips)
    for r in rows:
        assert abs((r[1][1] - r[0][1]) - 0.14) < 1e-6
    assert rec["compress"] <= 1.0


def test_acute_wedge_compresses_the_walk_inside_the_circle():
    K, A_row, J_row, b_dir = _right_angle(tH=3.0, wedge_deg=60.0)
    rows, rec = sg.return_stations(A_row, J_row, K, b_dir)
    R = rec["radius_m"]
    assert abs(R - 3.0 * math.tan(math.radians(30.0))) < 1e-3
    assert rec["compress"] < 1.0
    O = rec["O"]
    for r in rows[1:rec["n_arc_rows"]]:
        d0 = math.hypot(r[0][0] - O[0], r[0][2] - O[1])
        d3 = math.hypot(r[3][0] - O[0], r[3][2] - O[1])
        assert d0 - d3 <= sg.COMPRESS_R * R + 1e-6                 # never through the centre


def test_degenerate_wedges_are_refused():
    K, A_row, J_row, b_dir = _right_angle(wedge_deg=175.0)
    try:
        sg.return_stations(A_row, J_row, K, b_dir)
    except sg.GeomError:
        return
    raise AssertionError("a 175 deg wedge was accepted")


def test_corner_pavement_fills_the_wedge_minus_the_quadrant_facing_up():
    K, A_row, J_row, b_dir = _right_angle(tH=3.0)
    rows, rec = sg.return_stations(A_row, J_row, K, b_dir, step=0.05)
    verts, tris = sg.corner_pavement(K, K[1], rows, rec["n_arc_rows"])
    area = 0.0
    for t in tris:
        a, b, c = (verts[i] for i in t)
        ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
        assert ny >= 0                                              # up (engine frame)
        area += ny / 2.0
    R = 3.0
    assert abs(area - (R * R - math.pi * R * R / 4.0)) < 0.01, area


def test_barrier_path_rings_every_profile_point_grass_to_grass():
    right = _row(0.0, -5.0, 10.0, 0.0, -1.0, PROF_C)
    left = _row(0.0, 5.0, 10.0, 0.0, 1.0, PROF_C)
    path = sg.barrier_path(right, left)
    assert (path[0][0], path[0][1]) == (right[3][0], right[3][2])
    assert (path[-1][0], path[-1][1]) == (left[3][0], left[3][2])
    for p in list(right) + list(left):
        assert any(abs(q[0] - p[0]) < 1e-9 and abs(q[1] - p[2]) < 1e-9 for q in path)
    for a, b in zip(path, path[1:]):
        assert math.hypot(b[0] - a[0], b[1] - a[1]) <= sg.BARRIER_RING_M + 1e-9


def test_barrier_is_a_closed_jersey_solid_seated_on_the_lowest_surface():
    right = _row(0.0, -5.0, 10.0, 0.0, -1.0, PROF_C)
    left = _row(0.0, 5.0, 10.0, 0.0, 1.0, PROF_C)
    path = sg.barrier_path(right, left)

    def base_of(x, z, ax, az):
        s = [10.0 + 0.05 * px for px, _pz in sg.footprint_samples(x, z, ax, az)]   # a 5 % grade along the stub
        return min(s), s
    rings, seat = sg.barrier_rings(path, base_of)
    for r, s in zip(rings, seat):
        assert abs(r["y"] - (min(s["surface"]) - sg.BARRIER_BURY_M)) < 1e-3
        assert r["h"] == sg.BARRIER_H
    verts, faces, uvs = sg.barrier_mesh(rings)
    assert rf.signed_volume(verts, faces) > 0
    edges = {}
    for f in faces:
        for i in range(len(f)):
            e = (f[i], f[(i + 1) % len(f)])
            edges[e] = edges.get(e, 0) + 1
    assert all(edges.get((b, a), 0) == 1 for (a, b) in edges), "not a closed manifold"
    span = max(v[2] for v in verts) - min(v[2] for v in verts)
    assert span >= 10.0 + 2 * 2.78 - 1e-6                          # grass meet to grass meet
