"""tools/road_seek.py (ledger 0078 round 8): the graded road found across the mapped line where the line's own DEM profile
is not a road, and nowhere else."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import road_seek as rs  # noqa: E402


def _centre(x):
    """the real road: on the mapped line, then 20 m to its left (+z) between x 200 and 400, ramped over 50 m"""
    if x < 150 or x > 450:
        return 0.0
    if x < 200:
        return 20.0 * (x - 150) / 50.0
    if x > 400:
        return 20.0 * (450 - x) / 50.0
    return 20.0


class FakeRaster:
    """a hillside rising 40 % to the left, a graded road bench on it climbing 5 % along x, and on the mapped line
    (z = 0) between x 250 and 350 an 8 m hump with 2:1 sides (the bank the mapped line crosses)"""

    def at(self, x, z):
        c = _centre(x)
        road = 0.05 * x + 0.4 * c
        if abs(z - c) <= 3.5:
            h = road
        else:
            h = road + 0.4 * (z - c - math.copysign(3.5, z - c))
        if 250 <= x <= 350 and abs(z) <= 6 and abs(z - c) > 3.5:
            h += 8.0 * min(1.0, (x - 250) / 4.0, (350 - x) / 4.0)
        return h, 100.0


def test_the_road_is_found_where_the_line_reads_a_bank_and_the_line_kept_elsewhere():
    P = [(3.0 * i, 0.0, 0.0) for i in range(201)]
    W = [7.0] * len(P)
    out, regions, st = rs.seek(P, W, FakeRaster())
    assert regions, "the hump on the mapped line flags a region"
    for i, p in enumerate(P):
        x = p[0]
        if 230 <= x <= 370:
            assert out[i]["offset_m"] == pytest.approx(20.0, abs=1.5), (x, out[i])
            assert out[i]["z_m"] == pytest.approx(0.05 * x + 8.0, abs=0.3)
        if x < 60 or x > 540:
            assert out[i]["offset_m"] == pytest.approx(0.0, abs=0.01)


def test_a_line_whose_profile_reads_a_road_is_left_alone():
    class Flat:
        def at(self, x, z):
            return 0.08 * x + 0.3 * abs(z), 100.0
    P = [(3.0 * i, 0.0, 0.0) for i in range(120)]
    out, regions, st = rs.seek(P, [6.5] * len(P), Flat())
    assert regions == []
    assert all(o["offset_m"] == 0.0 for o in out)
