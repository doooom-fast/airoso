"""tools/road_lanes.py: one line per lane centre for road wear on streets (ledger 0084's owed "lanes" source; ledger
0099 "Full road wear at 10 cm"). The lanes are the spaces between the lines scripts-v021 ribbon.lane_markings paints,
both directions, never over a median, none in an excluded row range, nothing at all without road_wear.lanes."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import road_lanes as rl  # noqa: E402

LM = ROOT / "tracks" / "san-diego-lake-murray"
RULE = rl.paint_rule()
STEP = 3.0                  # the synthetic roads' station spacing (m), the loop's own ~3 m


def _straight(widths):
    """an open road due north (+z): station i at z = 3 i. Its left normal is -x (west), so offset o sits at x = -o."""
    return [(0.0, 10.0, STEP * i) for i in range(len(widths))]


def _project(tmp_path, pts, widths, *, lanes=None, island=None, connectors=None, connector_islands=None, route=None,
             road_wear=None):
    proj = tmp_path / "proj"
    (proj / "data").mkdir(parents=True, exist_ok=True)
    cfg = {"route": route or {}}
    if road_wear is not None:
        cfg["road_wear"] = road_wear
    elif lanes is not None:
        cfg["road_wear"] = {"lanes": lanes}
    (proj / "track.config.json").write_text(json.dumps(cfg))
    (proj / "data" / "centerline.local.json").write_text(json.dumps(
        {"frame": "ENU local meters (X=east, Y=up, Z=north)", "points_xyz_m": [list(p) for p in pts],
         "widths_m": list(widths)}))
    (proj / "data" / "median_bands.json").write_text(json.dumps(
        {"island_w_by_vertex": island or [0.0] * len(pts), "runs": [], "connector_islands": connector_islands or []}))
    (proj / "data" / "connectors.local.json").write_text(json.dumps({"connectors": connectors or []}))
    return proj


def _painted_offsets(mesh, pts):
    """{station: {offset}} of every quad lane_markings painted on a straight road due north"""
    out: dict[int, set] = {}
    v = mesh["vertices"]
    for q in range(0, len(v), 4):
        for a, b in ((v[q], v[q + 1]), (v[q + 2], v[q + 3])):
            i = int(round(a[2] / STEP))
            out.setdefault(i, set()).add(round(-(a[0] + b[0]) / 2.0, 6))
    return out


def _bounds(i, lanes):
    """{offset} of every lane edge at station i, read back off the output (offset +- width / 2)"""
    out = set()
    for ln in lanes:
        for r, o, w in zip(ln["rows"], ln["offset_m"], ln["width_m"]):
            if r == i:
                out.add(round(o - w / 2, 3))
                out.add(round(o + w / 2, 3))
    return out


# --- the paint rule -----------------------------------------------------------------------------------------------------
def test_the_rule_is_read_off_lane_markings_own_signature():
    assert RULE == {"lane_w": 3.65, "edge_inset": 0.55, "line_w": 0.12, "max_lanes_side": 6}


def test_lanes_match_the_paint_rules_dividers(tmp_path):
    """a road widening 13 -> 31 m: at every station the spaces' bounds are exactly the painted lines (the yellow pair's
    middle, the dividers, the edge lines), and every lane the tool keeps lies between two of them"""
    n = 140
    W = [13.0 + 18.0 * min(1.0, i / 120.0) for i in range(n)]
    pts = _straight(W)
    paint = rl.RB.lane_markings(pts, W, center_yellow=True, dash_gap=0.0)      # every dash drawn: the lines whole
    white, yellow = _painted_offsets(paint["white"], pts), _painted_offsets(paint["yellow"], pts)
    for i in range(n):
        spaces = rl.rule_lanes(W[i] / 2.0, RULE)
        bounds = {round(b, 6) for _s, _k, lo, hi, _e in spaces for b in (lo, hi)}
        assert {round(o, 6) for o in yellow[i]} == {0.09, -0.09}
        assert white[i] <= bounds - {0.0}                     # every painted white line is a lane bound
        # every bound but the centre is painted where the segment on either side of the station carries it
        for b in bounds - {0.0}:
            fits_next = i + 1 < n and any(abs(b - x) < 1e-6 for _s, _k, lo, hi, _e in rl.rule_lanes(W[i + 1] / 2, RULE)
                                          for x in (lo, hi))
            fits_prev = i > 0 and any(abs(b - x) < 1e-6 for _s, _k, lo, hi, _e in rl.rule_lanes(W[i - 1] / 2, RULE)
                                      for x in (lo, hi))
            if (fits_next or fits_prev) and abs(abs(b) - (W[i] / 2 - RULE["edge_inset"])) > 1e-6:
                assert b in white[i], (i, b)
    doc = rl.run(_project(tmp_path, pts, W, lanes={}))
    painted = {i: white[i] | {0.0} for i in range(n)}
    for ln in doc["lanes"]:
        for r, o, w in zip(ln["rows"], ln["offset_m"], ln["width_m"]):
            for b in (o - w / 2, o + w / 2):
                assert min(abs(b - x) for x in painted[r]) < 2e-3, (ln["id"], r, b)


@pytest.mark.parametrize("width, lanes_a_side, outer", [
    (13.0, 1, (0.0, 3.65)),        # one lane and a 2.30 m strip (a two-lane street's parking / bike lane)
    (17.0, 2, (3.65, 7.30)),       # two lanes and a 0.65 m strip
    (22.6, 3, (7.30, 10.75)),      # the third is the 3.45 m left before the edge line: narrower, still a lane
    (23.05, 3, (7.30, 10.975)),    # the third divider's line would cross the edge line by 0.035 m: not painted, so the
                                   # third lane runs 3.675 m to the edge line
    (23.2, 3, (7.30, 10.95)),      # ...painted at 23.2 m: three full lanes and a 0.10 m strip
    (30.0, 4, (10.95, 14.45)),     # four, the outer 3.50 m
])
def test_widths_that_do_not_divide_by_3_65_are_split_as_the_paint_splits_them(tmp_path, width, lanes_a_side, outer):
    W = [width] * 30
    pts = _straight(W)
    doc = rl.run(_project(tmp_path, pts, W, lanes={}))
    white = _painted_offsets(rl.RB.lane_markings(pts, W, center_yellow=True, dash_gap=0.0)["white"], pts)
    assert (10.95 in white[10]) == (width >= 23.2)                     # the paint's own answer at the knife-edge
    for direction, sign in (("forward", -1), ("reverse", 1)):
        mine = sorted((ln for ln in doc["lanes"] if ln["direction"] == direction), key=lambda x: x["lane"])
        assert [ln["lane"] for ln in mine] == list(range(1, lanes_a_side + 1))
        o, w = mine[-1]["offset_m"][5], mine[-1]["width_m"][5]
        assert (round(abs(o) - w / 2, 3), round(abs(o) + w / 2, 3)) == pytest.approx(outer, abs=1e-3)
        assert all(math.copysign(1, x) == sign for ln in mine for x in ln["offset_m"])
    strip = width / 2 - RULE["edge_inset"] - outer[1]
    assert strip < rl.DEFAULTS["min_edge_lane_m"]                      # what is left past the outer lane is a strip


def test_an_edge_leftover_is_a_lane_only_at_min_edge_lane_m(tmp_path):
    W = [13.0] * 20                                                  # the leftover: 5.95 - 3.65 = 2.30 m
    pts = _straight(W)
    assert {ln["lane"] for ln in rl.run(_project(tmp_path, pts, W, lanes={}))["lanes"]} == {1}
    doc = rl.run(_project(tmp_path, pts, W, lanes={"min_edge_lane_m": 2.3}))
    assert {ln["lane"] for ln in doc["lanes"]} == {1, 2}
    assert doc["min_edge_lane_m"] == 2.3 and doc["car_width_m"] == pytest.approx(1.9)


# --- both directions ------------------------------------------------------------------------------------------------------
def test_both_directions_each_lane_running_its_own_way(tmp_path):
    W = [17.0] * 40
    pts = _straight(W)
    doc = rl.run(_project(tmp_path, pts, W, lanes={}))
    fwd = {ln["lane"]: ln for ln in doc["lanes"] if ln["direction"] == "forward"}
    rev = {ln["lane"]: ln for ln in doc["lanes"] if ln["direction"] == "reverse"}
    assert sorted(fwd) == sorted(rev) == [1, 2]
    for k in (1, 2):
        f, r = fwd[k], rev[k]
        assert f["rows"] == list(range(40)) and r["rows"] == list(range(39, -1, -1))
        z = [p[2] for p in f["points_xyz_m"]]
        assert z == sorted(z)                                    # forward: northbound, in its order of travel
        assert [p[2] for p in r["points_xyz_m"]] == z[::-1]       # reverse: southbound
        assert all(p[0] > 0 for p in f["points_xyz_m"])           # right of northbound travel = east
        assert all(p[0] < 0 for p in r["points_xyz_m"])
        assert f["offset_m"] == [-o for o in r["offset_m"][::-1]]
        assert f["offset_m"][0] == pytest.approx(-(k - 0.5) * RULE["lane_w"], abs=1e-3)
    assert doc["summary"]["km"]["forward"] == doc["summary"]["km"]["reverse"]


def test_a_loop_gives_closed_lanes_the_inside_ones_shorter(tmp_path):
    R, n = 200.0, 420
    pts = [(R * math.cos(2 * math.pi * i / n), 5.0, R * math.sin(2 * math.pi * i / n)) for i in range(n)]
    pts.append(pts[0])                                            # closed as the loop's file is: last = first
    W = [17.0] * len(pts)
    doc = rl.run(_project(tmp_path, pts, W, lanes={}))
    assert len(doc["lanes"]) == 4 and all(ln["closed"] for ln in doc["lanes"])
    assert all(len(ln["rows"]) == n for ln in doc["lanes"])
    for ln in doc["lanes"]:                       # anticlockwise: left of travel = the inside = "reverse"
        r = R - ln["offset_m"][0]
        assert ln["length_m"] == pytest.approx(2 * math.pi * r, rel=1e-3)
        assert (ln["direction"] == "reverse") == (r < R)


# --- medians ----------------------------------------------------------------------------------------------------------------
def test_no_lane_runs_over_a_median_band(tmp_path):
    """25 m: three lanes a side. A 7 m island (College's) leaves the first lane 0.15 m: gone; a 1.5 m island (Navajo's)
    leaves it 2.90 m: kept, centred on what is left. The second lane runs on through both."""
    n = 100
    W = [25.0] * n
    iw = [7.0 if 30 <= i <= 60 else 1.5 if 70 <= i <= 90 else 0.0 for i in range(n)]
    doc = rl.run(_project(tmp_path, _straight(W), W, lanes={}, island=iw))
    for ln in doc["lanes"]:
        for r, o, w in zip(ln["rows"], ln["offset_m"], ln["width_m"]):
            assert abs(o) - w / 2 >= iw[r] / 2 - 1e-3, (ln["id"], r)
    for direction in ("forward", "reverse"):
        l1 = {r for ln in doc["lanes"] if ln["lane"] == 1 and ln["direction"] == direction for r in ln["rows"]}
        l2 = {r for ln in doc["lanes"] if ln["lane"] == 2 and ln["direction"] == direction for r in ln["rows"]}
        assert not l1 & set(range(30, 61)) and set(range(70, 91)) <= l1 and l2 == set(range(n))
        l1_narrow = [ln for ln in doc["lanes"] if ln["lane"] == 1 and ln["direction"] == direction and 80 in ln["rows"]]
        k = l1_narrow[0]["rows"].index(80)
        assert l1_narrow[0]["width_m"][k] == pytest.approx(2.90, abs=1e-3)
        assert abs(l1_narrow[0]["offset_m"][k]) == pytest.approx((0.75 + 3.65) / 2, abs=1e-3)
    assert doc["summary"]["island_trimmed_km"] > 0 and doc["summary"]["no_car_fits_km"] > 0


def test_a_connector_island_off_the_centre_is_respected(tmp_path):
    """a connector's raised island (median_bands connector_islands, offset aware: its points are the island's centre)
    2 m left of the connector's line, 3 m wide: no lane over [0.5, 3.5]"""
    W = [17.0] * 10
    cpts = [(100.0, 10.0, STEP * i) for i in range(60)]
    isl_pts = [[100.0 - 2.0, 10.0, STEP * i] for i in range(60)]          # left = -x: the island 2 m west
    iw = [3.0 if 10 <= i <= 50 else 0.0 for i in range(60)]
    proj = _project(tmp_path, _straight(W), W, lanes={},
                    connectors=[{"name": "side_road#0", "kind": "connector", "points_xyz_m": [list(p) for p in cpts],
                                 "widths_m": [20.0] * 60}],
                    connector_islands=[{"name": "side_road", "points_xyz_m": isl_pts, "island_w_by_point": iw,
                                        "offset_aware": True}])
    doc = rl.run(proj)
    mine = [ln for ln in doc["lanes"] if ln["road"] == "side_road#0"]
    assert mine
    for ln in mine:
        for r, o, w in zip(ln["rows"], ln["offset_m"], ln["width_m"]):
            if 11 <= r <= 49:
                assert o + w / 2 <= 0.5 + 1e-3 or o - w / 2 >= 3.5 - 1e-3, (ln["id"], r, o, w)


# --- excluded rows (College Ave, until its split zone has a reader) ------------------------------------------------------
def test_an_excluded_vertex_range_produces_no_lanes(tmp_path):
    W = [17.0] * 100
    doc = rl.run(_project(tmp_path, _straight(W), W, lanes={"exclude": [{"from": 40, "to": 60, "why": "test"}]}))
    rows = [r for ln in doc["lanes"] for r in ln["rows"]]
    assert rows and not [r for r in rows if 40 <= r <= 60]
    assert {r for r in rows} == set(range(40)) | set(range(61, 100))
    assert len(doc["lanes"]) == 8                                  # each of the four lanes cut into two runs
    assert doc["sources"]["mainline"]["excluded_rows"] == 21


def test_a_split_zone_without_a_reader_is_refused_and_a_reader_supplies_its_rows(tmp_path, monkeypatch):
    W = [17.0] * 100
    zone = {"kind": "fake_split", "from": 40, "to": 60, "source": "nowhere.json"}
    with pytest.raises(SystemExit, match="has no reader"):
        rl.run(_project(tmp_path, _straight(W), W, lanes={"split_zones": [zone]}))

    def reader(proj, z, rule):
        assert rule == RULE
        rows = list(range(z["from"], z["to"] + 1))
        return [{"id": "zone/forward/1/0", "road": "mainline", "direction": "forward", "lane": 1, "rows": rows,
                 "closed": False, "points_xyz_m": [[5.0, 10.0, STEP * r] for r in rows], "offset_m": [-5.0] * len(rows),
                 "width_m": [3.65] * len(rows)}]
    monkeypatch.setitem(rl.SPLIT_ZONE_READERS, "fake_split", reader)
    doc = rl.run(_project(tmp_path, _straight(W), W, lanes={"split_zones": [zone]}))
    in_zone = [ln for ln in doc["lanes"] if any(40 <= r <= 60 for r in ln["rows"])]
    assert [ln["group"] for ln in in_zone] == ["split:fake_split"] and in_zone[0]["length_m"] == pytest.approx(60.0)

    def leaks(proj, z, rule):
        got = reader(proj, z, rule)
        got[0]["rows"][-1] = z["to"] + 1
        return got
    monkeypatch.setitem(rl.SPLIT_ZONE_READERS, "fake_split", leaks)
    with pytest.raises(SystemExit, match="outside"):
        rl.run(_project(tmp_path, _straight(W), W, lanes={"split_zones": [zone]}))


# --- opt-in -------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("road_wear", [
    None,                                                        # no road_wear at all (Lake Murray today)
    {"surfaces": ["1ROAD"], "lines": []},                        # a circuit's road wear, no lanes key
    {"lanes": {"enabled": False}},
    {"enabled": False, "lanes": {}},
    {"lanes": False},
])
def test_no_key_no_output(tmp_path, road_wear):
    W = [17.0] * 20
    proj = _project(tmp_path, _straight(W), W, road_wear=road_wear if road_wear is not None else None)
    if road_wear is None:
        cfg = json.loads((proj / "track.config.json").read_text())
        assert "road_wear" not in cfg
    assert rl.run(proj) is None
    assert not (proj / "data" / rl.OUT_NAME).exists()
    assert rl.main([str(proj), "--out", str(tmp_path / "elsewhere.json")]) == 0
    assert not (tmp_path / "elsewhere.json").exists()


def test_the_key_writes_one_new_file_and_refuses_unknown_keys(tmp_path):
    W = [17.0] * 20
    proj = _project(tmp_path, _straight(W), W, lanes={})
    before = sorted(p.name for p in (proj / "data").iterdir())
    rl.run(proj)
    assert sorted(p.name for p in (proj / "data").iterdir()) == sorted(before + [rl.OUT_NAME])
    with pytest.raises(SystemExit, match="unknown key"):
        rl.run(_project(tmp_path, _straight(W), W, lanes={"min_lane": 3.0}))


@pytest.mark.parametrize("route", [{"lane_dividers": False}, {"divided_double": False}])
def test_a_road_painted_without_lanes_is_refused(tmp_path, route):
    W = [17.0] * 20
    with pytest.raises(SystemExit, match="FATAL"):
        rl.run(_project(tmp_path, _straight(W), W, lanes={}, route=route))


# --- connectors ---------------------------------------------------------------------------------------------------------------
def test_connectors_are_smoothed_as_the_assembler_smooths_them_before_it_paints():
    src = (rl.V021 / "blender" / "build_loop_blend.py").read_text(encoding="utf-8")
    call = ", ".join(f"{k}={v}" for k, v in rl.CONNECTOR_SMOOTH.items())
    assert f"cpts = smoothmod.smooth_centerline(cpts, {call})" in src
    assert "ribbon.connector_markings(cpts, cw, stub_of.get(cname), paint_of.get(cname))" in src


def test_a_stubs_lanes_end_where_its_paint_ends(tmp_path):
    """a phase-5 stub (tests/geometry/test_v021_connector_markings.py's): one lane a side, none past the paint"""
    cpts = [(0.0, 5.0 + 0.02 * u, float(u)) for u in range(0, 17)] + [(0.0, 5.0 + 0.02 * 16.4, 16.4)]
    stub = {"id": "x", "tail_m": 1.0, "length_m": 15.0, "lanes_per_side": 1}
    W = [17.0] * 10
    proj = _project(tmp_path, [(500.0, 0.0, STEP * i) for i in range(10)], W, lanes={},
                    connectors=[{"name": "STUB_x#0", "kind": "connector", "points_xyz_m": [list(p) for p in cpts],
                                 "widths_m": [9.6] * len(cpts), "stub": stub}])
    doc = rl.run(proj)
    mine = [ln for ln in doc["lanes"] if ln["road"] == "STUB_x#0"]
    assert sorted((ln["direction"], ln["lane"]) for ln in mine) == [("forward", 1), ("reverse", 1)]
    sm = rl.SM.smooth_centerline(cpts, **rl.CONNECTOR_SMOOTH)
    paint = rl.RB.connector_markings(sm, [9.6] * len(sm), stub)
    z_paint = max(v[2] for v in paint["white"]["vertices"])
    for ln in mine:
        assert max(p[2] for p in ln["points_xyz_m"]) == pytest.approx(z_paint, abs=1e-3)
        assert ln["width_m"][0] == pytest.approx(9.6 / 2 - RULE["edge_inset"], abs=1e-3)
        assert all(ln["group"] == "stub" for ln in mine)


def test_an_authored_piece_is_read_as_painted_bike_lanes_left_out(tmp_path):
    """an authored record (tools/expansion_pieces.py decorate's form): a double yellow, a dashed lane line each side,
    the buffer's solid white, then the bike lane's: two lanes a side between the yellow and the buffer line"""
    n = 30
    cpts = [(200.0, 10.0, STEP * i) for i in range(n)]
    lines = [{"color": "yellow", "dash": False, "off": [0.09] * n}, {"color": "yellow", "dash": False, "off": [-0.09] * n},
             {"color": "white", "dash": True, "off": [3.6] * n}, {"color": "white", "dash": True, "off": [-3.6] * n},
             {"color": "white", "dash": False, "off": [7.1] * n}, {"color": "white", "dash": False, "off": [-7.1] * n},
             {"color": "white", "dash": False, "off": [8.0] * n}, {"color": "white", "dash": False, "off": [-8.0] * n}]
    W = [17.0] * 10
    proj = _project(tmp_path, [(500.0, 0.0, STEP * i) for i in range(10)], W, lanes={},
                    connectors=[{"name": "north_x", "kind": "connector", "points_xyz_m": [list(p) for p in cpts],
                                 "widths_m": [19.6] * n, "expansion": {"route": "north", "piece": "A"},
                                 "paint": {"lines": lines, "strokes": []}}])
    mine = [ln for ln in rl.run(proj)["lanes"] if ln["road"] == "north_x"]
    got = sorted((ln["direction"], ln["lane"], round(ln["offset_m"][3] - ln["width_m"][3] / 2, 3),
                  round(ln["offset_m"][3] + ln["width_m"][3] / 2, 3)) for ln in mine)
    assert got == [("forward", 1, -3.6, -0.09), ("forward", 2, -7.1, -3.6),
                   ("reverse", 1, 0.09, 3.6), ("reverse", 2, 3.6, 7.1)]
    assert {ln["group"] for ln in mine} == {"north"}


# --- the bake ----------------------------------------------------------------------------------------------------------------
def test_bake_lines_put_the_tyre_profile_on_each_lanes_wheel_paths(tmp_path):
    """the output as tools/road_wear_blend.py's lines, through scripts/aerial/road_wear.wear_at itself: across a lane
    the rubber peaks on its two wheel paths, track_m apart about the lane's centre"""
    W = [17.0] * 40
    doc = rl.run(_project(tmp_path, _straight(W), W, lanes={}))
    lines = rl.bake_lines(doc, layer_m=10.0)
    assert len(lines) == len(doc["lanes"])
    ln = next(L for L, d in zip(lines, doc["lanes"]) if d["direction"] == "forward" and d["lane"] == 2)
    assert ln["P"].shape[1] == 3 and set(ln) >= {"P", "I", "closed", "layer_m", "layout", "source"}
    assert np.all(ln["I"] == doc["rubber"])
    centre_x = -(-1.5 * RULE["lane_w"])                           # forward lane 2 at offset -5.475: x = +5.475
    w = {"amplitude": 0.2, "track_m": doc["track_m"], "spread_m": 0.25}
    X = np.linspace(centre_x - 2.0, centre_x + 2.0, 401)[None, :]
    Y = np.full_like(X, 60.0)                                     # Blender y = north = station 20
    D = rl.RW.wear_at(X, Y, 10.0, ln, w, reach=0.5 * w["track_m"] + 4 * w["spread_m"])[0]
    left, right = X[0][np.argmax(np.where(X[0] < centre_x, D, -1))], X[0][np.argmax(np.where(X[0] > centre_x, D, -1))]
    assert left == pytest.approx(centre_x - doc["track_m"] / 2, abs=0.02)
    assert right == pytest.approx(centre_x + doc["track_m"] / 2, abs=0.02)
    assert D[200] < 0.5 * D.max()                                  # lighter between the wheel paths


# --- Lake Murray's own data (read only; the key is set in memory, never in its config) -----------------------------------
@pytest.mark.skipif(not (LM / "data" / "connectors.local.json").exists(), reason="Lake Murray's data is not here")
def test_lake_murray_college_left_out_no_lane_over_a_median_north_as_authored():
    cfg = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))
    assert rl.spec_from_config(cfg) is None                       # no key on Lake Murray: the tool writes nothing
    cfg["road_wear"] = {"lanes": {"exclude": [{"from": 1130, "to": 1476, "why": "College Ave round 2"}]}}
    doc = rl.build(LM, cfg, rl.spec_from_config(cfg))
    lanes = doc["lanes"]
    main = [ln for ln in lanes if ln["road"] == "mainline"]
    assert main and not [r for ln in main for r in ln["rows"] if 1130 <= r <= 1476]
    # no lane over the mainline's island
    iw = json.loads((LM / "data" / "median_bands.json").read_text(encoding="utf-8"))["island_w_by_vertex"]
    for ln in main:
        for r, o, w in zip(ln["rows"], ln["offset_m"], ln["width_m"]):
            assert abs(o) - w / 2 >= iw[r] / 2 - 2e-3, (ln["id"], r)
    # ...nor over a connector's, recomputed off the connector as the tool frames it
    bands = json.loads((LM / "data" / "median_bands.json").read_text(encoding="utf-8"))
    conns = {c["name"]: c for c in json.loads((LM / "data" / "connectors.local.json").read_text())["connectors"]}
    for ci in bands["connector_islands"]:
        for name, c in conns.items():
            if name.split("#")[0] != ci["name"] or c.get("stub"):
                continue
            cp = rl.SM.smooth_centerline([tuple(p) for p in c["points_xyz_m"]], **rl.CONNECTOR_SMOOTH)
            fr = rl.frames(cp, False if c.get("paint") else rl.is_closed(cp))
            cr = rl.island_crossings(fr, ci["points_xyz_m"], ci["island_w_by_point"])
            for ln in (x for x in lanes if x["road"] == name):
                for r, o, w in zip(ln["rows"], ln["offset_m"], ln["width_m"]):
                    if cr[r] is not None:
                        assert o + w / 2 <= cr[r][0] + 2e-3 or o - w / 2 >= cr[r][1] - 2e-3, (ln["id"], r)
    # the north pieces: as many lanes a direction as tools/expansion_pieces.py authored (B's third lane downhill)
    import expansion_pieces as ep
    for pid, cname in ep.PIECE_CONN.items():
        name = next(n for n in conns if n.split("#")[0] == cname)
        n = len(conns[name]["points_xyz_m"])
        most = {}
        for d in ("forward", "reverse"):
            per = [0] * n
            for ln in lanes:
                if ln["road"] == name and ln["direction"] == d:
                    for r in ln["rows"]:
                        per[r] += 1
            most[d] = max(per)
        f, r = ep.LANES[pid]
        if pid == "B":
            f = 3
        if pid in ep.REVERSED:                                    # the connector runs against the piece's J order
            f, r = r, f
        assert (most["forward"], most["reverse"]) == (f, r), (pid, most)
    s = doc["summary"]
    assert s["lanes"] == len(lanes) and s["km"]["forward"] > 40 and s["km"]["reverse"] > 40
    assert {ln["group"] for ln in lanes} == {"mainline", "north", "stub", "connector"}
