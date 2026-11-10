"""tools/switchback_fit.py (ledger 0078 round 10): a mapped kink rebuilt on its measured circle, joined to the legs as
they are, every step forward, the inside edge clear of the centre; a circle the legs cannot reach is refused."""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import switchback_fit as sf  # noqa: E402


def _hairpin():
    """two straight legs 16 m apart meeting in a sharp mapped kink at (0, 0), a left switchback"""
    a = [(-60.0 + 3.0 * i, 0.0, 0.0) for i in range(21)]                # east along z = 0 to x = 0
    b = [(0.0 - 3.0 * i, 0.0, 16.0) for i in range(21)]                  # back west along z = 16
    return a + [(4.0, 0.0, 8.0)] + b


def test_the_measured_circle_replaces_the_kink_and_proves_itself():
    P = _hairpin()
    W = [6.5] * len(P)
    c = {"id": "S1", "st_m": 63.0, "radius_m": 8.0, "width_m": 9.0, "centre_xz": [-2.0, 8.0],
         "r_inside_m": 3.5, "r_outside_m": 12.5}
    P2, W2, r = sf.fit_one(P, W, c)
    assert r["status"] == "PASS", r
    assert r["back_steps"] == 0 and r["inside_edge_r_m"] == 3.5
    on = [p for p in P2 if abs(math.hypot(p[0] + 2.0, p[2] - 8.0) - 8.0) < 0.05]
    assert len(on) >= 3                                     # the vertex count is kept: ~3 m spacing round a 25 m arc
    assert all(w == 9.0 for p, w in zip(P2, W2) if abs(math.hypot(p[0] + 2.0, p[2] - 8.0) - 8.0) < 0.05)


def test_a_circle_whose_inside_edge_folds_is_refused():
    P = _hairpin()
    c = {"id": "S1", "st_m": 63.0, "radius_m": 8.0, "width_m": 16.0, "centre_xz": [-2.0, 8.0],
         "r_inside_m": 0.0, "r_outside_m": 16.0}
    P2, W2, r = sf.fit_one(P, [6.5] * len(P), c)
    assert r["status"] == "FAIL" and P2 == P
