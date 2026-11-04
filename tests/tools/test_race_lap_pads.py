"""Ledger 0054 Phase 2 (Mission Gorge Speedway): the lap tool's declared joins and junction pads (scripts/geometry/race_lap.py),
on Lake Murray v4's committed intermediates and the held declaration
(tracks/san-diego-lake-murray/source/expansion/phase2/race.north.declaration.json).

The north loop's 34 exits: 26 side streets of its pieces, the 6 stub arms of the three pads it drives through (each probed 10 m
into the stub, before its Free Roam end barrier), and the 2 mainline branches it abandons at J1 and J5. Plain ``test_*``.
"""
from __future__ import annotations

import copy
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from scripts.geometry import race_lap  # noqa: E402

LM = ROOT / "tracks" / "san-diego-lake-murray"
DECL = LM / "source" / "expansion" / "phase2" / "race.north.declaration.json"
# the handoff's table (832facf PHASE2-HANDOFF.md), engine metres
PAD_PROBES = {"J2:S1": (-2723.198, 965.310), "J2:S2": (-2765.207, 969.103), "J3:S3": (-3063.121, 2020.674),
              "J3:S4": (-3041.091, 2073.459), "J4:S5": (-1167.662, 3199.999), "J4:S6": (-1221.486, 3222.699)}
_C = {}


def _cfg(spec=None):
    d = json.loads(DECL.read_text(encoding="utf-8"))
    s = copy.deepcopy(spec or d["laps"]["north"])
    return {"race": {"laps": {"north": s}}, "layouts": []}, s


def _lap():
    if "lap" not in _C:
        cfg, _s = _cfg()
        _C["lap"] = race_lap.stitch(LM, cfg, "north")
    return _C["lap"]


def test_the_north_loop_on_v4_has_34_exits():
    lap = _lap()
    kinds = {}
    for mo in lap["mouths"]:
        kinds[mo["kind"]] = kinds.get(mo["kind"], 0) + 1
    assert kinds == {"side_street": 26, "pad_arm": 6, "branch": 2}, kinds
    assert lap["point_count"] - 1 == 2936 and abs(lap["lap_m"] - 8732.7) < 0.05
    arms = {mo["connector"].split(" ")[0]: mo["probe_xz"] for mo in lap["mouths"] if mo["kind"] == "pad_arm"}
    assert set(arms) == set(PAD_PROBES)
    for k, (x, z) in PAD_PROBES.items():
        assert math.hypot(arms[k][0] - x, arms[k][1] - z) < 0.005, (k, arms[k])
    assert sorted(mo["connector"] for mo in lap["mouths"] if mo["kind"] == "branch") == ["MAINLINE before v2317", "MAINLINE beyond v1517"]


def test_declared_joins_replace_the_straight_ones_and_j1_j5_stay_straight():
    lap = _lap()
    js = {j.get("declared") or f"{j['from'][0]}->{j['to'][0]}": j for j in lap["joins"]}
    assert {"J2", "J3", "J4"} <= set(js)
    assert [round(js[k]["chord_m"], 1) for k in ("J2", "J3", "J4")] == [28.0, 46.0, 42.0]
    straight = [j for j in lap["joins"] if not j.get("declared")]
    assert sorted(round(j["length_m"], 1) for j in straight) == [11.6, 14.6]


def test_five_corners_one_per_junction():
    import barrier_bands as bb
    lap = _lap()
    cs = bb._corners(bb._load_place_signs(), [tuple(p) for p in lap["points_xyz_m"]], lap["widths_m"], 45.0)
    assert [c["apex"] for c in cs] == [320, 707, 1458, 2130, 2932]
    assert all(lap["source_by_vertex"][c["apex"]][0] == "join" for c in cs)


def test_refusals():
    cfg, s = _cfg()
    joins = json.loads((LM / s["joins_file"]).read_text(encoding="utf-8"))["joins"]

    def refused(spec, needle):
        c = {"race": {"laps": {"north": spec}}, "layouts": []}
        try:
            race_lap.stitch(LM, c, "north")
        except SystemExit as e:
            assert needle in str(e), str(e)
            return
        raise AssertionError(f"not refused: {needle}")
    bad = copy.deepcopy(s); bad.pop("joins_file")
    j = copy.deepcopy(joins); j[0]["points_xyz_m"][0][0] += 0.2
    bad["joins"] = j
    refused(bad, "off its piece end")
    bad = copy.deepcopy(s); bad.pop("joins_file")
    j = copy.deepcopy(joins); j[0]["to"] = ["north_mission_gorge", 0]
    bad["joins"] = j
    refused(bad, "join no consecutive piece ends")
    bad = copy.deepcopy(s); bad["junction_pads"] = ["J2", "J9"]
    refused(bad, "pad J9 is not in data/pads.plan.json")
    bad = copy.deepcopy(s); bad["junction_pads"] = ["J2", "J2"]
    refused(bad, "names a pad twice")
    bad = copy.deepcopy(s)
    bad["pieces"] = [bad["pieces"][0], bad["pieces"][2], bad["pieces"][1], bad["pieces"][3], bad["pieces"][4]]
    bad.pop("joins_file")
    refused(bad, "do not join two consecutive pieces")


def test_without_joins_or_pads_the_lap_is_the_straight_one():
    """the groundwork's behaviour is untouched when neither key is declared (test_race_lap pins the rest)"""
    _c, s = _cfg()
    plain = {k: v for k, v in s.items() if k in ("pieces", "roads")}
    lap = race_lap.stitch(LM, {"race": {"laps": {"north": plain}}, "layouts": []}, "north")
    assert all(not j.get("declared") for j in lap["joins"]) and len(lap["joins"]) == 5
    assert not [mo for mo in lap["mouths"] if mo["kind"] == "pad_arm"]
    assert sorted(round(j["length_m"], 1) for j in lap["joins"]) == [11.6, 14.6, 28.0, 42.0, 46.0]
