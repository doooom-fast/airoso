"""tools/aerial_trace.py (ledger 0078 round 13): an even NAIP band of road width off a line that crosses uneven ground is
found, and a line on its road is left alone."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import aerial_trace as at  # noqa: E402


def _road_centre(x):
    return 8.0 if 100.0 <= x <= 200.0 else 0.0


class FakeRaster:
    """a 7 m gravel road (NAIP 190, even; the DEM level across) on the line (z = 0), except between x 100 and 200 where it
    runs 8 m to the left and the line crosses scrub (NAIP 90-170 in shrub-sized patches, the DEM +-0.2 m hummocks)"""

    def at(self, x, z):
        c = _road_centre(x)
        if abs(z - c) <= 3.5:
            return 0.03 * x, 190.0
        k = (math.floor(x / 1.5) * 7 + math.floor(z / 1.5) * 13) % 5
        return 0.03 * x + 0.2 * math.sin(x * 1.3) * math.cos(z * 1.7), 90.0 + 20.0 * k


def test_the_road_off_a_level_line_is_found_and_nowhere_else():
    P = [(3.0 * i, 0.0, 0.0) for i in range(101)]
    W = [6.5] * len(P)
    stations = [{"offset_m": 0.0} for _ in P]
    rows = at.trace(P, W, stations, FakeRaster())
    cand = at.candidates(rows)
    rr, st = at.runs(P, rows, cand)
    acted = [r for r in rr if r["acts"]]
    assert len(acted) == 1, rr
    r = acted[0]
    assert 95 <= r["s_m"][0] <= 125 and 175 <= r["s_m"][1] <= 205, r
    assert r["off_m"] == pytest.approx(8.0, abs=1.0)
    for i, p in enumerate(P):
        if p[0] < 80 or p[0] > 220:
            assert not cand[i], (p, rows[i])
