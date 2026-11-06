"""tools/seat_edges_grade.py and seat_edges_blend.py's opt-in route.seat_edges_grade_pct (ledger 0083, Del Mar): the steep
stretches of a line seated as a bank of atan(grade) would be; absent key = the tool as before, and no track but Del Mar's
port names it."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import seat_edges_grade as sg  # noqa: E402


def _line(closed):
    # 0..60 m along x: flat, then a 2 m rise over 10 m (20 %), then flat
    P = []
    for i in range(0, 61, 2):
        y = 0.0 if i < 30 else (2.0 if i >= 40 else (i - 30) * 0.2)
        P.append([float(i), y, 0.0])
    if closed:
        P.append(list(P[0]))
    return P


def test_only_the_steep_points_are_named_with_their_grade():
    pts = sg.grade_points(_line(False), 5.0)
    xs = sorted(p[0] for p in pts)
    assert xs and min(xs) >= 28.0 and max(xs) <= 42.0
    assert abs(max(p[2] for p in pts) - math.atan(0.2)) < 1e-9
    assert sg.grade_points(_line(False), 25.0) == []


def test_a_closed_lap_skips_its_repeated_vertex():
    P = _line(True)
    pts = sg.grade_points(P, 5.0)
    assert len({(p[0], p[1]) for p in pts}) == len(pts)
    # the seam point (x 0, repeated last) takes x 60 and x 2 as its neighbours: 2 m over 58 m of plan, 3.4 %, not steep
    assert all(p[0] != 0.0 for p in pts)


def test_the_blend_tool_is_opt_in_and_only_del_mars_port_names_the_key():
    text = (ROOT / "tools" / "seat_edges_blend.py").read_text(encoding="utf-8")
    assert 'if not rel and grade_pct is None:' in text
    assert 'print("[seat-edges] no route.crossfall_file: nothing banked, nothing to do")' in text
    for cfg in sorted((ROOT / "tracks").glob("*/track.config.json")):
        route = json.loads(cfg.read_text(encoding="utf-8")).get("route") or {}
        if "seat_edges_grade_pct" in route:
            assert cfg.parent.name == "del-mar-lm", cfg.parent.name
