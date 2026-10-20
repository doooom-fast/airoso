"""tools/mouth_weld.py ExactHostDeck (ledger 0054 P1, opt-in per mouth through track.config.json
route.weld_exact_deck): the host deck read off the ribbon's own triangles on the pavement, the projection model's
level run-on off it.

  * on a straight host (rectangular quads) it is the projection model to rounding: the opt-in changes nothing there;
  * on a fanned corner quad (the College/Navajo outer edge: 2.2 m between centre points, 6.2 m between edge points,
    on a grade) it is the triangle's own plane, which the projection model misses by millimetres to a centimetre;
  * off the pavement it IS the projection model (the same run-on the weld blends the approach onto).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import mouth_weld as mw  # noqa: E402


def _rows(centre, half=10.0):
    out = []
    for i in range(len(centre)):
        a, b = centre[max(0, i - 1)], centre[min(len(centre) - 1, i + 1)]
        dx, dz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(dx, dz)
        nx, nz = -dz / L, dx / L
        x, y, z = centre[i]
        out.append(((x + nx * half, y, z + nz * half), (x, y, z), (x - nx * half, y, z - nz * half)))
    return out


def test_straight_host_is_the_projection_model():
    rows = _rows([(0.0, 0.02 * k * 3.0, 3.0 * k) for k in range(30)])
    idx = list(range(30))
    a, b = mw.HostDeck(rows, idx), mw.ExactHostDeck(rows, idx)
    for x in (-9.5, -4.0, 0.0, 3.3, 9.9, 12.0, -14.0):
        for z in (4.1, 20.0, 47.3, 80.2):
            assert abs(a.at(x, z) - b.at(x, z)) < 1e-9, (x, z, a.at(x, z), b.at(x, z))


def test_a_fanned_corner_quad_is_read_off_its_triangles():
    # a quarter turn of radius 8 m (centre) carrying a 30 m road: the outer edge points fan out
    c = []
    for k in range(10):
        th = math.radians(10.0 * k)
        c.append((8.0 * math.sin(th), 0.4 * k, -8.0 * (1 - math.cos(th))))     # a right turn: L is the outer edge
    rows = _rows(c, half=15.0)
    idx = list(range(10))
    a, b = mw.HostDeck(rows, idx), mw.ExactHostDeck(rows, idx)
    worst = 0.0
    for k in range(9):
        l0, c0, _r0 = rows[k]
        l1, c1, _r1 = rows[k + 1]
        for (u, v) in ((0.2, 0.2), (0.5, 0.3), (0.3, 0.6)):
            # a point inside triangle (l0, c1, l1) and its plane height
            x = l0[0] + u * (c1[0] - l0[0]) + v * (l1[0] - l0[0])
            z = l0[2] + u * (c1[2] - l0[2]) + v * (l1[2] - l0[2])
            y = l0[1] + u * (c1[1] - l0[1]) + v * (l1[1] - l0[1])
            assert abs(b.at(x, z) - y) < 1e-9, (k, u, v)
            worst = max(worst, abs(a.at(x, z) - y))
    assert worst > 0.005, worst                     # the projection model misses the fanned triangles


def test_off_the_pavement_it_is_the_projection_run_on():
    rows = _rows([(3.0 * k, 0.1 * k, 0.5 * k * k / 30.0) for k in range(20)])
    idx = list(range(20))
    a, b = mw.HostDeck(rows, idx), mw.ExactHostDeck(rows, idx)
    for x, z in ((20.0, 25.0), (40.0, -14.0), (30.0, 40.0)):
        assert not a.inside(x, z)
        assert b.at(x, z) == a.at(x, z)
