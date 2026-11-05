"""scripts/geometry/cutfill.py: the road-building section as a ground function (V3-PLAN P3a, ledger 0048).

Synthetic roads only (stdlib): a straight road across a side slope, and two stacked legs (a hairpin pair) 20 m apart in
plan and 10 m apart in height. Checks the section's two slopes, that natural ground stands where the section leaves it,
that a stacked leg's ground is held on its own side of the midpoint (the stacked-leg gate's own rule), and the lateral
cap the shoulder face is limited to.
"""

from __future__ import annotations

import math

from scripts.geometry.cutfill import CrossSection, parse_ratio


def _straight(y=100.0, n=201, z=0.0, step=1.0):
    return [(i * step, y, z) for i in range(n)]


def test_parse_ratio():
    assert parse_ratio("0.25:1", 9.0) == 0.25
    assert parse_ratio("1.5:1 (hand-placed rock)".split(" ")[0], 9.0) == 1.5
    assert parse_ratio(2, 9.0) == 2.0
    assert parse_ratio("1-1.5:1", 9.0) == 9.0      # a range is not a ratio: the default
    assert parse_ratio(None, 9.0) == 9.0


def test_fill_and_cut_slopes():
    line = _straight()
    cs = CrossSection(line, [6.0] * len(line), verge_m=0.4, cut_hv=0.25, fill_hv=1.5, clearance=0.0)
    # left side (+z) of a road running +x; road edge at z = 3, verge to 3.4
    # FILL: natural 10 m below the road; at 3 m past the verge the face has fallen 3 / 1.5 = 2 m
    assert abs(cs.height(100.0, 3.4 + 3.0, 90.0) - 98.0) < 1e-6
    # ...and it never goes below natural: 30 m out the face would be at 80, natural 90 stands
    assert abs(cs.height(100.0, 3.4 + 30.0, 90.0) - 90.0) < 1e-6
    # CUT: natural 10 m above; 1 m past the verge the rock face has risen 1 / 0.25 = 4 m
    assert abs(cs.height(100.0, -(3.4 + 1.0), 110.0) - 104.0) < 1e-6
    assert abs(cs.height(100.0, -(3.4 + 5.0), 110.0) - 110.0) < 1e-6
    # the verge carries the edge height; under the deck the pins own the ground (natural returned)
    assert abs(cs.height(100.0, 3.2, 90.0) - 100.0) < 1e-6
    assert cs.height(100.0, 1.0, 90.0) == 90.0
    # beyond the reach: untouched
    assert cs.height(100.0, 200.0, 37.0) == 37.0


def test_crossfall_sets_the_edge():
    line = _straight()
    tilt = math.atan(0.02)                           # +2 %: left edge up
    cs = CrossSection(line, [6.0] * len(line), verge_m=0.4, clearance=0.0, bank_at=lambda s: tilt)
    assert abs(cs.height(100.0, 3.3, 50.0) - (100.0 + 3.0 * 0.02)) < 1e-6     # left verge: edge + 6 cm
    assert abs(cs.height(100.0, -3.3, 50.0) - (100.0 - 3.0 * 0.02)) < 1e-6    # right verge: edge - 6 cm


def _stacked():
    """A closed lap: a lower leg along z = 0 at y 100 and an upper leg along z = 20 at y 110, joined by long loops so
    the legs are > 150 m apart along the lap."""
    pts = []
    for i in range(0, 101):                          # lower leg, x 0 -> 100
        pts.append((float(i), 100.0, 0.0))
    for k in range(1, 200):                          # a 200 m detour east and back (no point near the legs)
        a = math.pi * k / 200.0
        pts.append((100.0 + 100.0 * math.sin(a), 105.0, 10.0 - 10.0 * math.cos(a)))
    for i in range(100, -1, -1):                     # upper leg, x 100 -> 0
        pts.append((float(i), 110.0, 20.0))
    for k in range(1, 200):
        a = math.pi * k / 200.0
        pts.append((-100.0 * math.sin(a), 105.0, 10.0 + 10.0 * math.cos(a)))
    pts.append(pts[0])
    return pts


def test_stacked_legs_hold_their_own_side():
    line = _stacked()
    cs = CrossSection(line, [6.0] * len(line), verge_m=0.4, clearance=0.0)
    assert any(cs.stacked)
    # a point nearer the lower leg (z = 9) on natural ground at 107 (closer to the upper road) is held down to 105 - m
    g = cs.height(50.0, 9.0, 107.0)
    assert g <= 105.0 - 0.05 + 1e-9 and abs(g - 110.0) > abs(g - 100.0)
    # a point nearer the upper leg (z = 11) on natural ground at 103 is held up
    g = cs.height(50.0, 11.0, 103.0)
    assert g >= 105.0 + 0.05 - 1e-9 and abs(g - 100.0) > abs(g - 110.0)
    # far from the pair (on the detour) nothing is held
    assert not cs.stacked[150]


def test_lateral_cap_is_the_medial_line():
    line = _stacked()
    cs = CrossSection(line, [6.0] * len(line), verge_m=0.4, clearance=0.0)
    # the lower leg at x = 50 (index 50), outward normal toward the upper leg (+z): the medial line is 10 m out
    cap = cs.lateral_cap(50, 1.0, 0.0, 1.0)
    assert 9.0 <= cap <= 10.0, cap
    # the other side faces open ground: the full reach
    assert cs.lateral_cap(50, -1.0, 0.0, -1.0) == 60.0


def test_grade_grid_counts():
    line = _straight()
    cs = CrossSection(line, [6.0] * len(line), verge_m=0.4, clearance=0.0)
    grid = [[(x * 5.0, 90.0, z * 5.0) for x in range(0, 41)] for z in range(-4, 5)]
    st = cs.grade_grid(grid)
    assert st["fill"] > 0 and st["cut"] == 0 and st["graded"] > 0
    # every graded node sits on or above natural and never above the road edge
    for row in grid:
        for x, y, z in row:
            assert 90.0 - 1e-9 <= y <= 100.0 + 1e-9
