"""tools/edge_retrace.py + tools/measured_surface.py (fleet round 1, Milford 0.1.12).

edge_retrace (ledger 0087 Q1): inside a span each side moves out to the measured edge, never in, never closer than clear_m
to a rail's face; outside the span (past the taper) nothing moves; a side that moves alone moves the line by half of it.
measured_surface: apply() puts each line point on the product's plane (c + u b), the deck taken off; a point off the
measured band is refused. Both are opt-in: only Milford's port names them.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


er = _load("edge_retrace")
ms = _load("measured_surface")


def _loop(n=800, r=200.0):
    """a closed circle, travel counter-clockwise (left = inside), last == first"""
    pts = [(r * math.cos(2 * math.pi * k / n), 0.0, r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return pts + [pts[0]]


def _edge_points(pts, rows, off, src="naip"):
    """evidence points at lateral offset off (+ left) on the given rows, three per row"""
    out = []
    n = len(pts) - 1
    for i in rows:
        a, b = pts[(i - 1) % n], pts[(i + 1) % n]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz)
        nx, nz = -tz / L, tx / L
        for _ in range(3):
            out.append([pts[i][0] + nx * off, pts[i][2] + nz * off, src, 30.0])
    return out


def test_retrace_widens_inside_the_span_only_and_moves_the_line():
    pts = _loop()
    n = len(pts) - 1
    lap = 2 * math.pi * 200.0
    st = [lap * k / n for k in range(n)]
    w = [16.0] * len(pts)
    ev = _edge_points(pts, range(n), 9.5)                 # the left paving at 9.5 m all round; the right at 8.0 (today's)
    ev += _edge_points(pts, range(n), -8.0)
    span = [[300.0, 500.0]]
    new, shift, rep = er.retrace(pts, w, True, ev, span, [], taper_m=30.0)
    mid = min(range(n), key=lambda i: abs(st[i] - 400.0))
    far = min(range(n), key=lambda i: abs(st[i] - 900.0))
    assert abs(new[mid] - 17.5) < 0.05, new[mid]          # left 9.5 + right 8.0
    assert abs(shift[mid] - 0.75) < 0.03, shift[mid]      # the line moves half the left's 1.5 m
    assert abs(new[far] - 16.0) < 1e-6 and abs(shift[far]) < 1e-6
    assert new[-1] == new[0]


def test_retrace_stops_short_of_a_rail_and_never_moves_in():
    pts = _loop()
    n = len(pts) - 1
    lap = 2 * math.pi * 200.0
    st = [lap * k / n for k in range(n)]
    w = [16.0] * len(pts)
    ev = _edge_points(pts, range(n), 10.0) + _edge_points(pts, range(n), -6.0)   # right reads INSIDE today's edge
    # a rail on the left at 9.0 m over s 350-450 (a circle of radius 200 - 9 inside)
    rail = [((200.0 - 9.0) * math.cos(t), (200.0 - 9.0) * math.sin(t))
            for t in [2 * math.pi * (350.0 + k) / lap for k in range(0, 101, 5)]]
    new, shift, rep = er.retrace(pts, w, True, ev, [[300.0, 500.0]], [{"key": "r", "xz": rail}], clear_m=0.10,
                                 taper_m=30.0)
    mid = min(range(n), key=lambda i: abs(st[i] - 400.0))
    left = new[mid] / 2 + shift[mid]
    right = new[mid] / 2 - shift[mid]
    assert left <= 9.0 - 0.10 + 0.005, left               # short of the rail's face (the chords sample within 5 mm)
    assert abs(right - 8.0) < 1e-3, right                 # never in (the width is written to 1 mm)
    assert rep["rails"][0]["side"] == "left"


def test_rails_in_frame_refuses_an_unknown_key():
    try:
        er.rails_in_frame([{"key": "a", "polyline_lonlat": [[0, 0], [0, 0.001]]}], ["b"], {"lon": 0.0, "lat": 0.0})
    except SystemExit as e:
        assert "no such rail" in str(e)
    else:
        raise AssertionError("an unknown rail key must stop the intake")


def _product(n=400, step=1.5, c0=10.0, b=0.05):
    """a straight line due north with a plane y = c0 + 0.01 s + b o"""
    return {"s": [k * step for k in range(n)], "x": [0.0] * n, "z": [k * step for k in range(n)],
            "nx": [-1.0] * n, "nz": [0.0] * n, "c": [c0 + 0.01 * k * step for k in range(n)], "b": [b] * n,
            "lap_m": n * step * 10}


def test_apply_reads_the_plane_and_takes_the_deck_off():
    prod = _product()
    # a point 1 m left of travel (north: left = west = -x) at s 30
    ys, banks, rep = ms.apply(prod, [(-1.0, 30.0), (0.0, 60.0)], deck_m=0.10)
    assert abs(ys[0] - (10.0 + 0.3 + 0.05 * 1.0 - 0.10)) < 1e-6, ys[0]
    assert abs(ys[1] - (10.0 + 0.6 - 0.10)) < 1e-6, ys[1]
    assert abs(banks[0] - math.atan(0.05)) < 1e-9


def test_apply_refuses_a_point_off_the_measured_band():
    prod = _product()
    try:
        ms.apply(prod, [(-6.0, 30.0)], deck_m=0.10)
    except SystemExit as e:
        assert "off the measured line" in str(e)
    else:
        raise AssertionError("a point 6 m off the measured line must stop the intake")


def test_both_are_opt_in():
    """only Milford's port names lm_intake.edge_retrace / measured_surface; it takes no camber survey beside it"""
    cfgs = {p.parent.name: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "tracks").glob("*/track.config.json")}
    names = lambda key: sorted(t for t, c in cfgs.items() if (c.get("lm_intake") or {}).get(key))
    assert names("edge_retrace") == ["milford-road-course-lm"]
    assert names("measured_surface") == ["milford-road-course-lm"]
    mf = cfgs["milford-road-course-lm"]
    assert not mf["lm_intake"].get("crossfall")
    assert mf["route"]["smooth_sigma_y_pts"] == 0.0
    text = (ROOT / "tools" / "lm_engine_intake.py").read_text(encoding="utf-8")
    assert 'li.get("edge_retrace")' in text and 'li.get("measured_surface")' in text
