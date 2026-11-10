"""tools/trim_connectors.cut_at_pads (route.street_junctions.pad_arms): a street is cut at a built pad's box edge, the part
inside dropped, each cut end an ARM of that pad. Ledger 0085 (Pikes Peak): the infield road runs from one oval junction
pad to the other, so a street entering two boxes is cut at both, each arm naming its own pad; a street entering one box
is cut exactly as before (Sand Creek's)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import trim_connectors as tc  # noqa: E402


def _street(x0, x1, step=2.0):
    n = int(round((x1 - x0) / step))
    return {"name": "s", "points_xyz_m": [[x0 + step * i, 1.0, 0.0] for i in range(n + 1)], "widths_m": [8.0] * (n + 1)}


def _box(pid, x0, x1):
    return {"id": pid, "box": [[x0, -10.0], [x1, -10.0], [x1, 10.0], [x0, 10.0]]}


def test_a_street_through_one_box_is_two_pieces_with_an_arm_each():
    out, arms = tc.cut_at_pads([_street(-10.0, 110.0)], [_box("A", 40.0, 60.0)])
    assert [c["name"] for c in out] == ["s#0", "s#1"]
    assert out[0]["points_xyz_m"][-1] == [40.0, 1.0, 0.0] and out[1]["points_xyz_m"][0] == [60.0, 1.0, 0.0]
    assert [(a["pad"], a["cut_xyz"]) for a in arms] == [("A", [40.0, 1.0, 0.0]), ("A", [60.0, 1.0, 0.0])]
    assert arms[0]["box_edge"] == [[40.0, 10.0], [40.0, -10.0]]


def test_a_street_from_one_box_to_another_is_cut_at_both():
    out, arms = tc.cut_at_pads([_street(-5.0, 105.0)], [_box("NE", -20.0, 15.0), _box("NW", 85.0, 120.0)])
    assert [c["name"] for c in out] == ["s#0"]
    p = out[0]["points_xyz_m"]
    assert p[0] == [15.0, 1.0, 0.0] and p[-1] == [85.0, 1.0, 0.0]
    assert all(15.0 <= q[0] <= 85.0 for q in p)
    assert len(out[0]["widths_m"]) == len(p)
    assert [(a["pad"], a["cut_xyz"]) for a in arms] == [("NE", [15.0, 1.0, 0.0]), ("NW", [85.0, 1.0, 0.0])]
    assert arms[0]["box_edge"] == [[15.0, -10.0], [15.0, 10.0]]
    assert arms[1]["box_edge"] == [[85.0, 10.0], [85.0, -10.0]]


def test_a_street_missing_every_box_is_kept_whole():
    s = _street(0.0, 30.0)
    out, arms = tc.cut_at_pads([s], [_box("A", 40.0, 60.0)])
    assert out == [s] and arms == []
