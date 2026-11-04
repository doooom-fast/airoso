"""scripts/geometry/corner_arcs.py: a declared junction-node corner swept as clothoid-arc-clothoid at its measured radius.

Synthetic lines only (stdlib): a closed lap at 1 m spacing with a 78.5 deg node (the Lariat's C12 turn) and a 76 deg
node (C13), fitted at the aerial radii (14.9 / 16.08 m). The fit keeps the vertex count and the heights, passes the
plan's step gate (P2 step 2: per-vertex heading change <= spacing / R x 57.3 + 1 deg; neighbours differ <= 1.5 deg),
and moves nothing outside the corner's arms.
"""

from __future__ import annotations

import math

from scripts.geometry.corner_arcs import clothoid_arc, fit_corners, step_gate


def _kinked(turn_deg, n_in=200, n_out=200):
    """An open run: n_in metres east, a node turning ``turn_deg`` left, n_out metres on; y climbs 5 %."""
    pts = [(float(i), 0.05 * i, 0.0) for i in range(n_in + 1)]
    th = math.radians(turn_deg)
    x0, z0 = pts[-1][0], pts[-1][2]
    for k in range(1, n_out + 1):
        pts.append((x0 + k * math.cos(th), 0.05 * (n_in + k), z0 + k * math.sin(th)))
    return pts


def test_clothoid_arc_turns_exactly():
    pts, L = clothoid_arc(15.0, math.radians(78.5), 8.0)
    # the end heading: the last two points
    h = math.atan2(pts[-1][1] - pts[-2][1], pts[-1][0] - pts[-2][0])
    assert abs(math.degrees(h) - 78.5) < 0.1
    assert abs(L - (15.0 * math.radians(78.5) + 8.0)) < 1e-6        # 2 Lt + Lc, Lc = R delta - Lt


def test_a_node_becomes_a_smooth_curve():
    for turn, R in ((78.5, 14.9), (-76.0, 16.08)):
        line = _kinked(turn)
        before = step_gate(line, 150, 250, R, 1.0, 1.5)
        assert not before["pass"]                                    # the node is one ~77 deg step
        out, rep = fit_corners(line, [{"id": "C", "st_m": 200.0, "radius_m": R}])
        r = rep[0]
        assert r["status"] == "PASS", r
        assert len(out) == len(line)
        assert all(abs(a[1] - b[1]) < 1e-12 for a, b in zip(out, line))   # heights kept by index
        assert abs(abs(r["turn_deg"]) - abs(turn)) < 0.5
        # nothing moves outside the arms (40 m each side of the apex)
        for k in list(range(0, 150)) + list(range(251, len(line))):
            assert math.hypot(out[k][0] - line[k][0], out[k][2] - line[k][2]) < 1e-9, k
        # the apex moved inside the corner by about R (sec(delta/2) - 1) plus the transitions' shift
        assert 0.5 < r["max_move_m"] < 8.0, r["max_move_m"]


def test_closed_lap_keeps_its_seam():
    line = _kinked(80.0, 300, 300)
    line = line + [line[0]]                                         # close it (a long chord home)
    out, rep = fit_corners(line, [{"id": "C", "st_m": 300.0, "radius_m": 15.0}])
    assert rep[0]["status"] == "PASS"
    assert out[0] == out[-1]


def test_a_radius_too_large_is_skipped_not_forced():
    line = _kinked(78.5, 60, 60)
    out, rep = fit_corners(line, [{"id": "C", "st_m": 60.0, "radius_m": 80.0}])
    assert rep[0]["status"] == "SKIPPED"
    assert out == [tuple(p) for p in line]
