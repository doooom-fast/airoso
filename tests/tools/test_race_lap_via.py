"""scripts/geometry/race_lap.py: a piece's optional "via" (ledger 0085, Pikes Peak's junction pads). The join INTO the
piece runs through the declared plan points instead of straight, resampled at the lap's spacing, heights and widths by
arc length; without "via" the join is straight, as before."""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.geometry import race_lap  # noqa: E402


def _lines():
    a = [(2.0 * i, 1.0, 0.0) for i in range(11)]                 # (0, 0) -> (20, 0)
    b = [(20.0 - 2.0 * i, 3.0, 20.0) for i in range(11)]         # (20, 20) -> (0, 20)
    return {"A": {"pts": a, "widths": [10.0] * 11, "closed": False, "island_w": [0.0] * 11},
            "B": {"pts": b, "widths": [6.0] * 11, "closed": False, "island_w": [0.0] * 11}}


def _cfg(via=None):
    pb = {"line": "B", "from": 0, "to": 10}
    if via is not None:
        pb["via"] = via
    return {"race": {"laps": {"t": {"pieces": [{"line": "A", "from": 0, "to": 10}, pb]}}}}


def _seg_d(p, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / (dx * dx + dz * dz)))
    return math.hypot(p[0] - a[0] - dx * t, p[1] - a[1] - dz * t)


def test_without_via_the_join_is_straight():
    lap = race_lap.stitch(None, _cfg(), "t", lines=_lines(), mouths=[], spans=[])
    j = [k for k, s in enumerate(lap["source_by_vertex"]) if s == ["join", 0]]
    assert j and all(abs(lap["points_xyz_m"][k][0] - 20.0) < 1e-3 for k in j)
    assert lap["joins"][0]["length_m"] == 20.0 and "via" not in lap["joins"][0]


def test_a_via_join_runs_through_its_points_with_heights_and_widths_by_arc_length():
    lap = race_lap.stitch(None, _cfg([[30.0, 10.0]]), "t", lines=_lines(), mouths=[], spans=[])
    jr = lap["joins"][0]
    L = 2 * math.hypot(10.0, 10.0)
    assert jr["via"] == 1 and abs(jr["length_m"] - L) < 1e-3
    j = [k for k, s in enumerate(lap["source_by_vertex"]) if s == ["join", 0]]
    assert len(j) == jr["points"] == math.ceil(L / 2.0) - 1
    for q, k in enumerate(j, start=1):
        x, y, z = lap["points_xyz_m"][k]
        assert min(_seg_d((x, z), (20.0, 0.0), (30.0, 10.0)), _seg_d((x, z), (30.0, 10.0), (20.0, 20.0))) < 1e-3      # the lap record keeps 4 decimals
        t = q / (len(j) + 1)
        assert abs(y - (1.0 + 2.0 * t)) < 1e-3
        assert abs(lap["widths_m"][k] - (10.0 - 4.0 * t)) < 1e-3
    assert max(lap["points_xyz_m"][k][0] for k in j) > 29.0


def test_via_points_with_widths_carry_them():
    lap = race_lap.stitch(None, _cfg([[30.0, 10.0, 4.0]]), "t", lines=_lines(), mouths=[], spans=[])
    j = [k for k, s in enumerate(lap["source_by_vertex"]) if s == ["join", 0]]
    half = math.hypot(10.0, 10.0)
    for q, k in enumerate(j, start=1):
        s = q / (len(j) + 1) * 2 * half
        want = 10.0 + (4.0 - 10.0) * s / half if s <= half else 4.0 + (6.0 - 4.0) * (s - half) / half
        assert abs(lap["widths_m"][k] - want) < 1e-3
