"""Ledger 0099 round 3, item 3 (after the first trial bake's look): tools/road_lanes.py LANE ENDS, opt-in
``road_wear.lanes.ends``. A lane that goes on in another record is welded to it; every other open end fades over
``fade_m``; and Lake Murray's key leaves the Speedway lap's line (college_nb) out, which the paint rule had read as a
two-way road on top of the split zone's own lanes.

Pure python (the tool loads without numpy). ``bake_lines`` and the bake's square ends are held beside the module's own
tests (tests/aerial/test_road_wear_smooth_0099.py, numpy). Plain ``test_*`` for tests/run_tests.py."""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RL = _load("road_lanes_ends_0099", ROOT / "tools" / "road_lanes.py")
LM = ROOT / "tracks" / "san-diego-lake-murray"
E = dict(RL.ENDS_DEFAULTS)


def _lane(id_, pts, closed=False):
    pts = [[float(v) for v in p] for p in pts]
    return {"id": id_, "road": id_.split("/")[0], "closed": closed, "length_m": round(RL.polyline_length(pts, closed), 1),
            "points_xyz_m": pts}


def _ss(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _street():
    a = _lane("a/forward/1/0", [(x, 0.0, 0.0) for x in range(0, 61, 3)])               # stops at x 60
    b = _lane("b/forward/1/0", [(x, 0.0, 0.05) for x in range(63, 124, 3)])            # goes on 3 m ahead, 5 cm to the side
    c = _lane("c/reverse/1/0", [(x, 0.0, 3.65) for x in range(123, -1, -3)])           # the neighbouring lane, the other way
    d = _lane("d/forward/1/0", [(x, 0.0, 40.0) for x in range(200, 213, 3)])           # 12 m, alone
    ring = _lane("r/forward/1/0", [(300 + 20 * math.cos(k * math.pi / 18), 0.0, 20 * math.sin(k * math.pi / 18))
                                   for k in range(36)], closed=True)
    return [a, b, c, d, ring]


def test_a_lane_that_runs_into_another_is_welded_and_every_other_end_fades():
    lanes = _street()
    a, b, c, d, ring = lanes
    s = RL.lane_ends(lanes, E)
    assert s["welds"] == 1 and s["ends_faded"] == 6 and s["weld_gap_m_max"] == 3.0 and s["weld_side_m_max"] == 0.05
    assert a["joined"] == {"head": None, "tail": "b/forward/1/0"} and a["bridge_to_xyz_m"] == [63.0, 0.0, 0.05]
    assert b["joined"] == {"head": "a/forward/1/0", "tail": None} and "bridge_to_xyz_m" not in b
    assert c["joined"] == {"head": None, "tail": None} and d["joined"] == {"head": None, "tail": None}
    # a: nothing at its head, whole from 8 m on and at the weld; b: whole at the weld, nothing at its tail
    assert a["rubber_share"][:4] == [0.0, round(_ss(3 / 8), 4), round(_ss(6 / 8), 4), 1.0] and set(a["rubber_share"][3:]) == {1.0}
    assert b["rubber_share"][0] == 1.0 and b["rubber_share"][-3:] == [round(_ss(6 / 8), 4), round(_ss(3 / 8), 4), 0.0]
    assert c["rubber_share"][0] == 0.0 and c["rubber_share"][-1] == 0.0 and max(c["rubber_share"]) == 1.0
    # a lane shorter than two fades never carries the whole rubber
    assert d["rubber_share"] == [0.0, round(_ss(3 / 8), 4), round(_ss(6 / 8), 4), round(_ss(3 / 8), 4), 0.0]
    # a closed lane has no end
    assert ring["rubber_share"] == [1.0] * 36 and "joined" not in ring and "bridge_to_xyz_m" not in ring
    assert s["lane_km"] > s["rubber_km"] > 0.9 * s["lane_km"]
    # the lane as it is drawn: the bridge is one more point, at the tail's share
    pts, share = RL.lane_line(a)
    assert pts[-1] == [63.0, 0.0, 0.05] and len(pts) == len(a["points_xyz_m"]) + 1 and share[-2:] == [1.0, 1.0]
    assert RL.lane_line(b) == (b["points_xyz_m"], b["rubber_share"])
    # no fade asked: every share is 1, the weld stands
    lanes = _street()
    s0 = RL.lane_ends(lanes, dict(E, fade_m=0.0))
    assert s0["welds"] == 1 and all(set(ln["rubber_share"]) == {1.0} for ln in lanes) and s0["rubber_km"] == s0["lane_km"]


def test_what_is_not_the_same_lane_is_not_welded():
    def welds(head_pts, **kw):
        a = _lane("a/forward/1/0", [(x, 0.0, 0.0) for x in range(0, 61, 3)])
        b = _lane("b/forward/1/0", head_pts)
        return RL.lane_ends([a, b], dict(E, **kw))["welds"]
    ahead = lambda x0, z, y=0.0, dz=0.0: [(x0 + 3 * k, y, z + dz * k) for k in range(8)]      # noqa: E731
    assert welds(ahead(63, 0.0)) == 1 and welds(ahead(69.9, 0.5)) == 1          # 9.9 m ahead, half a metre to the side
    assert welds(ahead(63, 0.6)) == 0                                            # a neighbour, not the same lane
    assert welds(ahead(71, 0.0)) == 0                                            # 11 m: too long a hole
    assert welds(ahead(57, 0.0)) == 0 and welds(ahead(60, 0.0)) == 0             # behind the tail, or on it
    assert welds(ahead(63, 0.0, y=4.0)) == 0                                     # another deck
    assert welds(ahead(63, 0.0, dz=3 * math.tan(math.radians(20)))) == 0         # turning away at 20 degrees
    assert welds(ahead(63, 0.0, dz=3 * math.tan(math.radians(10)))) == 1
    assert welds([(84 - 3 * k, 0.0, 0.0) for k in range(8)]) == 0                # its far end is near, but it runs the other way
    assert welds(ahead(63, 0.6), join_side_m=0.7) == 1                           # the numbers are the key's
    # the nearest head wins, and a head is welded once
    a = _lane("a/forward/1/0", [(x, 0.0, 0.0) for x in range(0, 61, 3)])
    a2 = _lane("a2/forward/1/0", [(x, 0.0, 0.2) for x in range(0, 59, 3)])       # stops at x 57, 6 m short of b
    b = _lane("b/forward/1/0", ahead(63, 0.0))
    b2 = _lane("b2/forward/1/0", ahead(66, 0.1))
    s = RL.lane_ends([a, a2, b, b2], E)
    assert a["joined"]["tail"] == "b/forward/1/0" and a2["joined"]["tail"] == "b2/forward/1/0" and s["welds"] == 2


def test_the_key_is_opt_in_and_checked():
    cfg = lambda lanes: {"road_wear": {"lanes": lanes}}                          # noqa: E731
    assert "ends" not in RL.spec_from_config(cfg({})) and "ends" not in RL.DEFAULTS
    assert RL.spec_from_config(cfg({"ends": False})).get("ends") is None
    assert RL.spec_from_config(cfg({"ends": True}))["ends"] == E == {"fade_m": 8.0, "join_gap_m": 10.0, "join_side_m": 0.5,
                                                                    "join_angle_deg": 15.0}
    assert RL.spec_from_config(cfg({"ends": {"fade_m": 6, "_doc": "x"}}))["ends"] == dict(E, fade_m=6.0)
    for bad in ({"ends": {"fade": 6}}, {"ends": {"fade_m": -1}}, {"end": {}}):
        try:
            RL.spec_from_config(cfg(bad))
        except SystemExit as e:
            assert "road_wear.lanes" in str(e)
        else:
            raise AssertionError(bad)
    src = (ROOT / "tools" / "road_lanes.py").read_text(encoding="utf-8")
    # without the key the doc is as it was: build runs lane_ends only where the spec names it
    assert 'ends = lane_ends(lanes, spec["ends"]) if spec.get("ends") else None' in src
    assert '**({"butt_ends": True} if ends else {})' in src


def test_lake_murray_names_the_ends_and_leaves_the_speedways_line_out():
    cfg = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))
    spec = RL.spec_from_config(cfg)
    assert spec["ends"] == E and cfg["road_wear"]["lanes"]["ends"] == {"fade_m": 8.0}
    assert "[invented]" in cfg["road_wear"]["lanes"]["_ends_doc"]
    ex = cfg["road_wear"]["lanes"]["exclude"]
    assert [(e["road"], e["from"], e["to"]) for e in ex] == [("college_nb", 0, 345)] and "twice" in ex[0]["why"]
    # the line it leaves out is the Speedway lap's, a plain connector record over the split zone's rows
    conns = {c["name"]: c for c in json.loads((LM / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]}
    nb = conns["college_nb"]
    assert len(nb["points_xyz_m"]) == 346 and not nb.get("paint") and not nb.get("stub")
    assert cfg["race"]["laps"]["college"]
    zone = cfg["road_wear"]["lanes"]["split_zones"][0]
    assert (zone["kind"], zone["from"], zone["to"]) == ("college_split", 1130, 1476)
