"""Ledger 0099 round 3, item 3: the lanes of College Ave's two one-way roads (tools/road_lanes.py, split zone
"college_split"), read off the data the scene's rows were built to (source/college_r2/college_split.data.json) by the
paint's own rule (source/college_r2/college_middle_blend.py's paint section).

No numpy here: tools/road_lanes.py reads scripts/aerial/road_wear.DEFAULTS off its source and loads that module only for
whoever calls into it, so the tool and these tests run on the PC's interpreter. Plain ``test_*`` for tests/run_tests.py."""
from __future__ import annotations

import importlib.util
import json

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LM = ROOT / "tracks" / "san-diego-lake-murray"
SOURCE = "source/college_r2/college_split.data.json"
ZONE = {"kind": "college_split", "from": 1130, "to": 1476, "source": SOURCE}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RL = _load("road_lanes_college_0099", ROOT / "tools" / "road_lanes.py")
S = json.loads((LM / SOURCE).read_text(encoding="utf-8"))
RULE = RL.paint_rule()


def test_the_tool_reads_the_road_wear_defaults_without_loading_that_module():
    d = RL.rw_defaults()
    assert (d["wear"]["track_m"], d["wear"]["margin_m"], d["texel_m"], d["max_atlas_px"]) == (1.60, 0.95, 0.25, 8192)
    assert RL.car_width_m() == 1.9
    src = (ROOT / "tools" / "road_lanes.py").read_text(encoding="utf-8")
    assert "RW = _RoadWear()" in src and 'RW = _load("_road_lanes_road_wear"' not in src
    assert not [ln for ln in src.split("\n") if ln.startswith(("import numpy", "from numpy"))]   # only bake_lines asks for it, inside


def test_the_bounds_are_the_paints_own_expressions():
    assert (RULE["lane_w"], RULE["edge_inset"], RULE["line_w"], RULE["max_lanes_side"]) == (3.65, 0.55, 0.12, 6)
    paint = (LM / "source" / "college_r2" / "college_middle_blend.py").read_text(encoding="utf-8")
    for frag in ("LINE_W, EDGE_INSET, LANE_W, DASH_ON, DASH_GAP, MAX_LANES, PAINT_LIFT = 0.12, 0.55, 3.65, 3.0, 9.0, 6, 0.015",
                 'return OFF["sb_east"][K[v]] + EDGE_INSET if v in K else 0.09 + fork_t(v) * (meet(v) + EDGE_INSET - 0.09)',
                 'return lambda v: (OFF["sb_east"][K[v]] + EDGE_INSET if v in K else fork_t(v) * (meet(v) + EDGE_INSET)) + k * LANE_W',
                 'return lambda v: (OFF["nb_west"][K[v]] - EDGE_INSET if v in K else fork_t(v) * (meet(v) - EDGE_INSET)) - k * LANE_W',
                 "m_lines = [(lambda v: hw(v) - EDGE_INSET, False, False), (lambda v: -(hw(v) - EDGE_INSET), False, False)]",
                 "return smooth((v - A0) / (NOSE - A0)) if v < NOSE else smooth((A1 - v) / (A1 - TAIL))"):
        assert frag in paint, frag                                      # the rule this reader mirrors is still the paint's
    R, F = S["rows"], S["frame"]
    nose, tail = R["v"][0], R["v"][-1]
    assert (S["mainline"]["from_v"], nose, tail, S["mainline"]["to_v"]) == (1130, 1172, 1444, 1476)
    k = 1300 - nose
    hw = F["half_w"][1300 - F["from_v"]]
    b = RL.college_split_bounds(S, RULE, 1300)
    assert b[1] == (R["offsets_m"]["sb_east"][k] + 0.55, hw - 0.55) and b[-1] == (0.55 - R["offsets_m"]["nb_west"][k], hw - 0.55)
    assert abs(b[1][0] - 5.156) < 1e-3 and abs(b[-1][0] - 7.846) < 1e-3 and abs(hw - 16.25) < 1e-3
    # the forks: the base runs from the old line's centre (the zone's two end rows) to the yellow where the roads part
    for v in (1130, 1476):
        bb = RL.college_split_bounds(S, RULE, v)
        assert bb[1][0] == 0.0 and bb[-1][0] == 0.0, v
    meet = R["offsets_m"]["sb_east"][0]
    near = RL.college_split_bounds(S, RULE, nose - 1)
    assert abs(near[1][0] - (meet + 0.55)) < 0.02 and abs(near[-1][0] - (0.55 - meet)) < 0.02      # one row short of the nose
    mid = RL.college_split_bounds(S, RULE, (1130 + nose) // 2)
    assert abs(mid[1][0] - 0.5 * (meet + 0.55)) < 1e-9                                               # smoothstep's half way


def test_the_lanes_of_the_two_roads_and_their_forks():
    lanes = RL.read_college_split(LM, dict(ZONE), dict(RULE))
    ids = [ln["id"] for ln in lanes]
    assert len(ids) == len(set(ids)) == 12 and all(i.startswith("mainline/college_split/") for i in ids)
    car = RL.car_width_m()
    R = S["rows"]
    nose = R["v"][0]
    for ln in lanes:
        assert RL._check_zone_lane(dict(ln), ZONE) is None, ln["id"]
        west = all(o > 0 for o in ln["offset_m"]) or ln["direction"] == "reverse"
        # + is west on College and the mainline runs north: the southbound road is "reverse", the northbound "forward"
        assert (ln["direction"] == "reverse") == west
        step = [b - a for a, b in zip(ln["rows"], ln["rows"][1:])]
        assert set(step) == ({-1} if ln["direction"] == "reverse" else {1}), ln["id"]           # in its direction of travel
        assert min(ln["width_m"]) >= car and max(ln["width_m"]) <= 3.65 + 0.06, ln["id"]
        for v, o, w, p in zip(ln["rows"], ln["offset_m"], ln["width_m"], ln["points_xyz_m"]):
            b = RL.college_split_bounds(S, RULE, v)[1 if ln["direction"] == "reverse" else -1]
            d = abs(o)
            if nose <= v <= R["v"][-1]:                                  # on a one-way road: inside its yellow and its edge line
                assert b[0] - 2e-3 <= d - w / 2 and d + w / 2 <= b[1] + 2e-3, (ln["id"], v)   # (offsets and widths are written to 1 mm)
                k = v - nose
                ys = (R["sb_west"][k][1], R["sb_east"][k][1]) if ln["direction"] == "reverse" else (R["nb_west"][k][1], R["nb_east"][k][1])
                assert min(ys) - 1e-3 <= p[1] <= max(ys) + 1e-3, (ln["id"], v)            # at its own road's height
    two = {ln["id"]: ln for ln in lanes}
    for d in ("reverse", "forward"):                                     # two lanes a road run the whole zone, unbroken
        for k in (1, 2):
            rows = two[f"mainline/college_split/{d}/{k}/0"]["rows"]
            assert sorted(rows) == list(range(1130, 1477)), (d, k)
    # the two roads stand at different heights where they are apart: a lane keeps to its own
    k = 1300 - nose
    sb = next(p[1] for ln in lanes if ln["direction"] == "reverse" and ln["lane"] == 1 for v, p in zip(ln["rows"], ln["points_xyz_m"]) if v == 1300)
    nb = next(p[1] for ln in lanes if ln["direction"] == "forward" and ln["lane"] == 1 for v, p in zip(ln["rows"], ln["points_xyz_m"]) if v == 1300)
    assert R["sb_east"][k][1] <= sb <= R["sb_west"][k][1] and R["nb_east"][k][1] <= nb <= R["nb_west"][k][1] and nb - sb > 4.0


def test_the_zone_joins_the_mainlines_own_lanes_and_a_wrong_zone_is_refused():
    cfg = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))
    cfg["road_wear"] = {"lanes": {"split_zones": [dict(ZONE)]}}
    doc = RL.build(LM, cfg, RL.spec_from_config(cfg))
    zone = [ln for ln in doc["lanes"] if ln["group"] == "split:college_split"]
    main = [ln for ln in doc["lanes"] if ln["group"] == "mainline"]
    assert len(zone) == 12 and not [ln for ln in main if any(1130 <= r <= 1476 for r in ln["rows"])]
    at = sorted((ln["direction"], ln["lane"], ln["offset_m"][ln["rows"].index(1130)]) for ln in zone if 1130 in ln["rows"])
    before = sorted((ln["direction"], ln["lane"], ln["offset_m"][ln["rows"].index(1129)]) for ln in main if 1129 in ln["rows"])
    assert at == before == [("forward", 1, -1.825), ("forward", 2, -5.475), ("forward", 3, -9.125),
                            ("reverse", 1, 1.825), ("reverse", 2, 5.475), ("reverse", 3, 9.125)]
    assert doc["summary"]["by_group"]["split:college_split"]["lanes"] == 12
    assert "college_split" in RL.SPLIT_ZONE_READERS
    for bad in (dict(ZONE, **{"from": 1131}), dict(ZONE, to=1470)):
        try:
            RL.read_college_split(LM, bad, dict(RULE))
        except SystemExit:
            continue
        raise AssertionError(bad)
