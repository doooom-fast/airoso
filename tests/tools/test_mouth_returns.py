"""ledger 0086: the through-mouth corner returns' pure half (tools/mouth_returns.py), stub_geom's meet_h, and the opt-in
contract (Lake Murray names none of the new keys, so every reader keeps its old behaviour)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import mouth_returns as mr  # noqa: E402
import stub_geom as sg  # noqa: E402


def _row(x0, z0, nx, nz, y0, prof=((0.0, 0.0), (0.1, 0.0), (0.3, 0.0), (1.8, -0.2))):
    return tuple((x0 + nx * o, y0 + h, z0 + nz * o) for o, h in prof)


def test_config_reads_list_and_dict_and_absent():
    assert mr.config({}) == ([], None)
    assert mr.config({"route": {"mouth_returns": ["grid_"]}}) == (["grid_"], mr.DEFAULT_RADII)
    assert mr.config({"route": {"mouth_returns": ["grid_"], "mouth_radii_file": "x.json"}}) == (["grid_"], "x.json")
    assert mr.config({"route": {"mouth_returns": {"prefixes": ["a"], "radii_file": "y.json"}}}) == (["a"], "y.json")


def test_radius_measured_else_host_median_else_all():
    radii = {"p|start|+1": {"measured": True, "radius_m": 4.0, "host": "H"},
             "q|start|+1": {"measured": True, "radius_m": 6.0, "host": "H"},
             "r|start|+1": {"measured": True, "radius_m": 10.0, "host": "G"},
             "s|start|+1": {"measured": False, "radius_m": 19.0, "host": "H", "why": "host edge not found"}}
    assert mr.radius_for(radii, "p|start|+1", "H") == (4.0, "measured")
    R, src = mr.radius_for(radii, "s|start|+1", "H")
    assert R == 5.0 and src.startswith("median of 2 measured on H") and "host edge not found" in src
    R, src = mr.radius_for(radii, "t|end|-1", "Z")
    assert R == 6.0 and src.startswith("median of all 3")
    assert mr.radius_for({}, "x", "H")[0] is None


def test_rows_between_wraps_a_closed_host():
    pts = [(math.cos(2 * math.pi * k / 40) * 100, 0, math.sin(2 * math.pi * k / 40) * 100) for k in range(40)]
    pts.append(pts[0])
    arc = mr.host_arcs(pts, 40, True)
    seg = 1.0 * arc[1]
    got = mr.rows_between(arc, 40, True, 0.0, -2.5 * seg, 1.5 * seg)
    assert got == {38, 39, 0, 1}


def test_walk_polyline_both_ways_and_open_end():
    poly = [(0, 0, 0), (10, 1, 0), (20, 2, 0)]
    p, q, t = mr.walk_polyline(poly, False, 0, 0.5, 7.0, 1)
    assert abs(p[0] - 12.0) < 1e-9 and q == 1 and abs(p[1] - 1.2) < 1e-9
    p, q, t = mr.walk_polyline(poly, False, 1, 0.5, 7.0, -1)
    assert abs(p[0] - 8.0) < 1e-9 and q == 0
    assert mr.walk_polyline(poly, False, 1, 0.5, 9.0, 1) is None


def test_return_stations_keep_the_no_curb_profile_with_meet_h_none():
    # a square corner: host edge along +x from K (0, 0), the street edge along +z; host rows' outward normal is +z
    K = (0.0, 0.0, 0.0)
    R = 5.0
    A_row = _row(R, 0.0, 0.0, 1.0, 0.0)
    J_row = _row(0.0, R + 1.0, 1.0, 0.0, 0.0)
    rows_keep, rec = sg.return_stations(A_row, J_row, K, (0.0, 1.0), meet_h=None)
    assert abs(rec["radius_m"] - R) < 1e-6
    for row in rows_keep:                      # the grass meet stays 0.20 m under the lane edge all the way round
        assert abs((row[3][1] - row[0][1]) - (-0.2)) < 1e-9
    rows_stub, _ = sg.return_stations(A_row, J_row, K, (0.0, 1.0))
    mid = rows_stub[len(rows_stub) // 2]
    assert abs((mid[3][1] - mid[0][1]) - sg.MEET_H_M) < 1e-9      # the stubs' default is unchanged


def test_corner_pavement_closes_the_corner_with_a_zero_height_curb():
    K = (0.0, 0.0, 0.0)
    A_row = _row(4.0, 0.0, 0.0, 1.0, 0.0)
    J_row = _row(0.0, 4.5, 1.0, 0.0, 0.0)
    rows, rec = sg.return_stations(A_row, J_row, K, (0.0, 1.0), meet_h=None)
    assert rec["compress"] == 1.0            # R 4 m leaves room for the 1.8 m strip: no compression
    pv, pt = sg.corner_pavement(K, 0.0, rows, rec["n_arc_rows"])
    area = 0.0
    for a, b, c in pt:
        area += 0.5 * abs((pv[b][0] - pv[a][0]) * (pv[c][2] - pv[a][2]) - (pv[c][0] - pv[a][0]) * (pv[b][2] - pv[a][2]))
    # the fillet of a square corner: R^2 (1 - pi / 4)
    assert abs(area - 16.0 * (1 - math.pi / 4)) < 0.05


def test_paint_window_widens_to_the_returns():
    pts = [(float(x), 0.0, 0.0) for x in range(0, 100, 5)]
    mo = {"host_seg": 10, "host_t": 0.0, "connector_width_m": 8.0, "angle_deg": 90.0}
    c, lo, hi = mr.paint_window(mo, pts, False)
    assert c == 50.0 and lo == -4.0 and hi == 4.0
    c, lo, hi = mr.paint_window(mo, pts, False, {"paint_window_off": [-9.5, 8.0]})
    assert (lo, hi) == (-9.5, 8.0)


def test_lake_murray_names_none_of_the_keys():
    for track in ("san-diego-lake-murray",):
        cfg = json.loads((ROOT / "tracks" / track / "track.config.json").read_text(encoding="utf-8"))
        route = cfg.get("route") or {}
        assert not route.get("mouth_returns") and not route.get("verify_mouth_corners")
        assert not (cfg.get("strip_seam") or {}).get("connectors")
        assert not (cfg.get("road_markings") or {}).get("gap_mouths")


def test_sand_creek_opts_in_and_ships_its_radii():
    d = ROOT / "tracks" / "sand-creek-lm"
    cfg = json.loads((d / "track.config.json").read_text(encoding="utf-8"))
    pre, rf = mr.config(cfg)
    assert pre == ["grid_"] and (d / rf).exists()
    assert cfg["route"]["verify_mouth_corners"] is True
    assert cfg["strip_seam"]["connectors"] is True and cfg["road_markings"]["gap_mouths"] is True
    ship = json.loads((d / "ship.json").read_text(encoding="utf-8"))
    draft = ship["steps"]["draft"]
    assert draft.index("lm_pads") < draft.index("mouth_returns") < draft.index("strip_seam") < draft.index("gap_mouths")
    assert "verify_mouth_corners" in ship["steps"]["gate"]
    assert rf in ship["sync_in"]["optional"]
    radii = json.loads((d / rf).read_text(encoding="utf-8"))
    assert radii["summary"]["measured"] > 0 and all("measured" in r for r in radii["corners"].values())


def test_skip_list_names_its_why():
    """route.mouth_returns_skip (ledger 0086, 0.2.7): the named mouths get no returns; a row without a why is refused;
    Sand Creek names exactly the two owed mouths whose returns turned verify_mouths red on m7a"""
    assert mr.skip_list({}) == {}
    assert mr.skip_list({"route": {"mouth_returns_skip": [{"piece": "a#0", "end": "end", "why": "w"}]}}) == \
        {("a#0", "end"): "w"}
    try:
        mr.skip_list({"route": {"mouth_returns_skip": [{"piece": "a#0", "end": "end"}]}})
        raise AssertionError("a row with no why was accepted")
    except ValueError:
        pass
    cfg = json.loads((ROOT / "tracks" / "sand-creek-lm" / "track.config.json").read_text(encoding="utf-8"))
    assert set(mr.skip_list(cfg)) == {("grid_primary_78#0", "end"), ("grid_primary_80#0", "end")}
