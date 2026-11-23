"""scripts/geometry/circuit_start.py — a circuit's declared line, grid, pits and sectors (ledger 0093)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.geometry import circuit_start as cs  # noqa: E402

HP = ROOT / "tracks" / "high-plains-lm"


def _hp():
    cfg = json.loads((HP / "track.config.json").read_text(encoding="utf-8"))
    local = json.loads((HP / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    return cfg, local


def _oval(r=60.0, straight=300.0, step=2.0):
    """a closed clockwise-free test lap: two straights joined by half circles, widths 12 m; origin at lon/lat 0, 0"""
    pts = []
    x = 0.0
    while x < straight:
        pts.append((x, 0.0, 0.0)); x += step
    n = int(math.pi * r / step)
    for k in range(n):
        a = -math.pi / 2 + math.pi * k / n
        pts.append((straight + r * math.cos(a), 0.0, r + r * math.sin(a)))
    x = straight
    while x > 0:
        pts.append((x, 0.0, 2 * r)); x -= step
    for k in range(n):
        a = math.pi / 2 + math.pi * k / n
        pts.append((r * math.cos(a), 0.0, r + r * math.sin(a)))
    pts.append(pts[0])
    return {"origin": {"lon": 0.0, "lat": 0.0}, "points_xyz_m": [list(p) for p in pts], "widths_m": [12.0] * len(pts)}


def _rs(**kw):
    rs = {"line": {"station_m": 150.0},
          "grid": {"pattern": {"first_m": -7.0, "step_m": -4.55, "lateral_m": [-2.8, 2.4], "slots": 10}},
          "pits": {"pattern": {"first_m": 8.0, "step_m": 4.55, "lateral_m": [-2.8, 2.4], "slots": 10}}}
    rs.update(kw)
    return rs


def test_high_plains_declares_its_measured_line_grid_and_pits():
    cfg, local = _hp()
    pl = cs.plan(cfg["race_start"], local)
    assert pl["problems"] == []
    assert abs(pl["line_station_m"] - 12.15) < 0.3                  # the painted band's centre (audit: s 11.8 +-1)
    n = pl["nodes"]
    starts = sorted(k for k in n if k.startswith("AC_START_"))
    pits = sorted(k for k in n if k.startswith("AC_PIT_"))
    assert len(starts) == 25 and len(pits) == 25                      # the measured slots; as many pit boxes
    line = cs.Line(local["points_xyz_m"], local["widths_m"])
    pole = line.ahead(n["AC_START_0"]["station_m"], pl["line_station_m"])
    assert 6.5 < pole < 8.0                                          # 7 m behind the line (audit section 4.1)
    assert n["AC_START_0"]["lateral_m"] < 0 < n["AC_START_1"]["lateral_m"]   # the right column first, then the left
    behind = [line.ahead(n[f"AC_START_{k}"]["station_m"], pl["line_station_m"]) for k in range(25)]
    assert behind == sorted(behind) and 110 < behind[-1] < 120
    for k in range(2, 25):                                            # each column every ~9.1 m
        assert 8.7 < behind[k] - behind[k - 2] < 9.5, k
    for k in range(25):                                               # pits s 20-129 (8 m past the line), before the pit exit (s 160)
        assert 7.5 < line.ahead(pl["line_station_m"], n[f"AC_PIT_{k}"]["station_m"]) < 120
    assert n["AC_HOTLAP_START_0"]["x"] == n["AC_START_0"]["x"]
    for name, v in n.items():
        if name.startswith(cs.FACING):
            assert cs.kn5_heading_dot(math.radians(v["yaw_deg"]), *v["travel"]) > 0.999, name
    third = line.lap / 3.0
    assert abs(line.ahead(pl["line_station_m"], pl["sectors_m"][0]) - third) < 0.5
    assert abs(line.ahead(pl["line_station_m"], pl["sectors_m"][1]) - 2 * third) < 0.5


def test_the_preps_yaw_faces_high_plains_grid_backwards_and_ours_does_not():
    """engine-july's prep yaws every node atan2(tx, tz) from pts[0] -> pts[1]: at its own AC_START_0 (s 1080, the south
    straight) that reads about -0.97 in the kn5 (verify_kn5 (c)'s ruler); atan2(tx, -tz) from the node's own tangent +1"""
    _cfg, local = _hp()
    cl = local["points_xyz_m"]
    prep_yaw = math.atan2(cl[1][0] - cl[0][0], cl[1][2] - cl[0][2])
    line = cs.Line(cl, local["widths_m"])
    prep_start = (186.13, 8.88, -106.294)        # data/dummies.json's AC_START_0 on main 74b46263 (High Plains 0.1.7)
    s, _lat = line.project(prep_start[0], prep_start[2])
    assert 1070 < s < 1090
    t = line.tangent(s)
    assert cs.kn5_heading_dot(prep_yaw, *t) < -0.9
    assert cs.kn5_heading_dot(math.radians(cs.yaw_deg(*t)), *t) > 0.999


def test_pattern_slots_and_station_line_for_a_track_with_no_marks():
    pl = cs.plan(_rs(), _oval())
    assert pl["problems"] == []
    n = pl["nodes"]
    assert abs(n["AC_START_0"]["station_m"] - 143.0) < 1e-6 and n["AC_START_0"]["lateral_m"] == -2.8
    assert abs(n["AC_PIT_1"]["station_m"] - 162.55) < 1e-6 and n["AC_PIT_1"]["lateral_m"] == 2.4
    # on the first straight the lap runs +x: yaw atan2(1, -0) = 90 deg, kn5 +Z along +x
    assert abs(n["AC_START_0"]["yaw_deg"] - 90.0) < 1e-6
    assert abs(n["AC_TIME_0_L"]["z"] - 6.0) < 1e-6 and abs(n["AC_TIME_0_R"]["z"] + 6.0) < 1e-6   # L = left of travel


def test_off_road_overlapping_and_out_of_order_slots_are_refused():
    off = cs.plan(_rs(grid={"pattern": {"first_m": -7.0, "step_m": -5.0, "lateral_m": [-5.0], "slots": 3}}), _oval())
    assert any("inside the road" in p for p in off["problems"])
    over = cs.plan(_rs(grid={"pattern": {"first_m": -7.0, "step_m": -2.0, "lateral_m": [0.0], "slots": 3}}), _oval())
    assert any("overlap" in p for p in over["problems"])
    order = cs.plan(_rs(grid={"pattern": {"first_m": -20.0, "step_m": 6.0, "lateral_m": [-2.5], "slots": 3}}), _oval())
    assert any("runs back from the line" in p for p in order["problems"])
    far = cs.plan(_rs(grid={"pattern": {"first_m": -40.0, "step_m": -6.0, "lateral_m": [-2.5], "slots": 2}}), _oval())
    assert any("ahead of AC_START_0" in p for p in far["problems"])
    clash = cs.plan(_rs(pits={"pattern": {"first_m": -7.0, "step_m": -4.55, "lateral_m": [-2.8, 2.4], "slots": 2}}), _oval())
    assert any("overlap" in p for p in clash["problems"])
    back = cs.plan(_rs(sectors={"stations_m": [500.0, 300.0]}), _oval())
    assert any("AC_TIME_2" in p for p in back["problems"])


def test_a_line_lonlat_off_the_road_is_refused():
    loc = _oval()
    m_lon, m_lat = cs.meters_per_degree(0.0)
    bad = cs.plan(_rs(line={"lonlat": [150.0 / m_lon, 20.0 / m_lat]}), loc)
    assert any("off the centreline" in p for p in bad["problems"])
    good = cs.plan(_rs(line={"lonlat": [150.0 / m_lon, 1.0 / m_lat]}), loc)
    assert good["problems"] == [] and abs(good["line_station_m"] - 150.0) < 1e-6


def test_car_corners_stand_round_the_node():
    pl = cs.plan(_rs(), _oval())
    v = pl["nodes"]["AC_START_0"]
    cs_ = cs.car_corners(v)
    xs, zs = [c[0] for c in cs_], [c[1] for c in cs_]
    assert abs(max(xs) - min(xs) - 2 * cs.CAR_HALF_L_M) < 1e-6 and abs(max(zs) - min(zs) - 2 * cs.CAR_HALF_W_M) < 1e-6
