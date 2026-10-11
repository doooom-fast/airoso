"""tools/barrier_bands.py — the ledger-0049 corridor declaration (version 2) on the real Lake Murray data.

Pins the measured shape of the declaration and that every self-gate FIRES on a crafted defect:

  * the SD declaration passes: both curb strips on every vertex (no bridge gaps), five trimmed inside corners,
    the centre chain retired (centre_w all 0, no runs), the whole-street zone v4454 -> v0 -> v777, three open
    boxes, four closure runs per layout pinned on the far curb strip (+-0.01 m) at the spec's pins, the forced
    pin rates (1:4.7 / 1:3.6 / 1:3.3), 6.86 m minimum beside the islands, 22.4 m minimum plan radius, ten kerbs
    clear of both closures, the mirror within 0.3 m on the running vertices, the Alvarado re-measure (11.36 m),
    and the PLANNED no-route fill: 0 leaks and the lap complete for both layouts;
  * crafted defects each FAIL with their own message: a closure in a box, a pin off the far strip, a 1:2 rate, a
    far mouth not behind the closure, a kerb under a closure, a missing strip ring (and the planned fill finds the
    door), a closure on an island, `centre_runs` still in the config, a perturbed Alvarado width, the pinned
    closure_runs disagreeing with the zones.
Plain ``test_*`` for tests/run_tests.py (the SD build with the planned fill runs once per module, ~25 s).
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import barrier_bands as bb  # noqa: E402
import no_route as nr  # noqa: E402

SD = ROOT / "tracks" / "san-diego-lake-murray"
NOSES = [846, 1073, 1096, 1258, 1374, 1487, 1540, 1739, 2183, 2297]
PINS = [777, 1506, 1521, 2311, 2328, 3289, 3304, 4454]

CORRIDOR = {
    "clear_width_m": 11.36, "clear_width_source": "alvarado",
    "island_mode": "pavement",
    "whole": [4454, 777],
    "boxes": [{"apex": 1514, "i": 1506, "j": 1521}, {"apex": 2319, "i": 2311, "j": 2328},
              {"apex": 3297, "i": 3289, "j": 3304}],
    "closure_runs": [[777, 1506], [1521, 2311], [2328, 3289], [3304, 4454]],
    "rate_toward_race_side": 12, "rate_away": 6,
    "pin_zone_m": 120, "pin_rate_min": 6, "pin_rate": {"4454": 10}, "steepest_pin_rate": 3,
    "base_open_m": 60, "base_sigma_m": 20, "island_env_m": 30, "attract_m": 40, "smooth_sigma_m": 4,
    "clear_floor_m": 10.86, "clear_hard_min_m": 6.5, "pocket_min_m": 2.0,
}


def v2_config(cfg: dict) -> dict:
    """the ledger-0049 race block (spec §9.1) on a config — as-is when the config already declares it"""
    cfg = copy.deepcopy(cfg)
    race = cfg.setdefault("race", {})
    if "corridor" not in race:
        for k in ("centre_runs", "wide_threshold_m", "interior_corners"):
            race.pop(k, None)
        race["edge_gaps"] = "none"
        race["corridor"] = copy.deepcopy(CORRIDOR)
    for lo in cfg.get("layouts", []):
        if lo.get("race_furniture") and not lo.get("closure_token"):
            lo["closure_token"] = "cw" if lo.get("direction", "forward") == "forward" else "acw"
    return cfg


def _project(cfg_edit=None) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    cfg = v2_config(json.loads((SD / "track.config.json").read_text(encoding="utf-8")))
    if cfg_edit:
        cfg_edit(cfg)
    (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    for f in ("centerline.local.json", "median_bands.json", "mouths.json", "bridge.spans.auto.json"):
        shutil.copyfile(SD / "data" / f, d / "data" / f)
    return d


_SD = {}


def _sd():
    """(project, declaration) of the real SD build, planned fill included — built once per module"""
    if "out" not in _SD:
        d = _project()
        _SD["d"], _SD["out"] = d, bb.build(d)
    return _SD["d"], _SD["out"]


def test_lake_murray_v2_declaration_passes_every_self_gate_and_the_planned_fill():
    d, out = _sd()
    assert out["fails"] == [], out["fails"]
    assert out["version"] == 2 and (d / "data" / "barrier_bands.json").exists()
    assert sorted(out["corridors"]) == ["race_acw", "race_cw"]
    for lid in ("race_cw", "race_acw"):
        pl = out["corridors"][lid]["no_route"]["planned"]
        assert pl["fail"] is False and pl["leak_m2"] == 0 and pl["blocked"] == [], (lid, pl)
        assert 130_000 < pl["reached_m2"] < 150_000, pl          # the prototype: 138.8 k / 138.4 k m2
        assert (d / "data" / f"no_route.{lid}.planned.json").exists()


def test_strips_are_closed_loops_and_the_chain_is_retired():
    _d, out = _sd()
    n = out["n"]
    assert out["edge_strip_by_vertex"] == [1] * n and out["edge_gaps"] == []
    assert out["centre_w_by_vertex"] == [0.0] * n and out["runs"] == []
    assert out["params"]["edge_gaps"] == "none"
    assert [(c["side"], c["kind"], c["in_vertex"], c["out_vertex"]) for c in out["edge_corners"]] == [
        ("R", "loop", 763, 774), ("R", "loop", 1508, 1517), ("R", "loop", 2314, 2324),
        ("R", "extend", 3292, 3300), ("R", "extend", 4495, 5)]
    assert out["summary"]["nose_vertices"] == NOSES


def test_zones_runs_and_pins_are_the_spec():
    _d, out = _sd()
    assert out["zones"]["whole"] == [4454, 777]
    assert out["zones"]["openings"] == [[1074, 1095]]
    for lid, side in (("race_cw", "L"), ("race_acw", "R")):
        c = out["corridors"][lid]
        assert c["closure_side"] == side and c["token"] == ("cw" if lid == "race_cw" else "acw")
        assert sorted((r["i"], r["j"]) for r in c["runs"]) == [(777, 1506), (1521, 2311), (2328, 3289), (3304, 4454)]
        assert c["pins"] == PINS
        zn, y, lane = c["zone_by_vertex"], c["closure_y_by_vertex"], c["lane_by_vertex"]
        assert len(zn) == len(y) == len(lane) == out["n"]
        assert zn[300] == "whole" and zn[1514] == "box" and zn[777] == "pin" and zn[1000] == "island"
        assert zn[2000] == "closure" and y[300] is None and y[1514] is None
        cl = json.loads((SD / "data" / "centerline.local.json").read_text())
        w = cl["widths_m"]
        sgn = 1.0 if side == "L" else -1.0
        for v in PINS:
            assert abs(y[v] - sgn * (w[v] / 2 - 0.485)) <= 0.01, (lid, v, y[v])
            assert lane[v] == [round(-(w[v] / 2 - 0.82), 4), round(w[v] / 2 - 0.82, 4)]   # full width at a pin
        # Alvarado is the whole street: 11.36 m face to face
        assert abs((lane[300][1] - lane[300][0]) - 11.36) < 1e-3
        # 17 m Navajo: an Alvarado-wide lane, the closure 3.68 m past the centreline
        assert abs((lane[2000][1] - lane[2000][0]) - 11.36) < 0.05


def test_forced_pin_rates_clear_widths_radius_and_mirror_are_measured():
    _d, out = _sd()
    cw = {(r["i"], r["j"]): r for r in out["corridors"]["race_cw"]["runs"]}
    assert abs(cw[(777, 1506)]["max_rate"]["pin_out"] - 4.69) < 0.05            # 1:4.7 onto College-3 exit
    assert abs(cw[(1521, 2311)]["max_rate"]["pin_in"] - 3.56) < 0.05             # 1:3.6 off the Navajo box
    assert abs(cw[(1521, 2311)]["max_rate"]["pin_out"] - 3.29) < 0.05            # 1:3.3 into Navajo/Jackson
    assert abs(cw[(3304, 4454)]["max_rate"]["pin_out"] - 10.0) < 0.05            # the I-8 deck end, at speed
    L = out["summary"]["layouts"]
    for lid in ("race_cw", "race_acw"):
        assert abs(L[lid]["clear_min_m"] - 6.86) < 0.05, L[lid]
        assert abs(L[lid]["clear_median_m"] - 11.36) < 0.05, L[lid]
        assert 10_800 < L[lid]["closure_m"] < 11_000
        assert L[lid]["min_radius_m"] >= 20.0
    assert abs(L["race_cw"]["min_radius_m"] - 22.4) < 0.3
    assert out["summary"]["mirror_running_max_m"] <= 0.3
    assert out["params"]["corridor"]["clear_width_measured_m"] == 11.36


def test_ten_kerbs_clear_of_both_closures_cw_outside_kerbs_clipped():
    _d, out = _sd()
    ks = {(k["apex"], k["kind"]): k for k in out["kerbs"]}
    assert len(out["kerbs"]) == 10 and set(a for a, _ in ks) == {0, 770, 1514, 2319, 3297}
    assert all(ks[(a, "inside")]["side"] == "R" and ks[(a, "outside")]["side"] == "L" for a in (0, 770, 1514, 2319, 3297))
    for a in (1514, 2319, 3297):
        k = ks[(a, "outside")]
        assert k.get("clipped_from"), k                                          # cut back under race_cw's funnels
        assert "race_cw" in (k.get("clip") or {}).get("by", [])
        assert not ks[(a, "inside")].get("clipped_from")                         # acw's pins are on the inside, in the box


def test_mouth_policies_and_forbidden_probes():
    _d, out = _sd()
    pol = {lid: {(m["host_vertex"], m["side"]): m["policy"] for m in c["mouths"]} for lid, c in out["corridors"].items()}
    assert pol["race_cw"] == {(1085, "L"): "behind_closure", (1086, "R"): "sealed_race_strip",
                              (4424, "R"): "sealed_race_strip"}
    assert pol["race_acw"] == {(1085, "L"): "sealed_race_strip", (1086, "R"): "behind_closure",
                               (4424, "R"): "behind_closure"}
    whys = {}
    for p in out["corridors"]["race_cw"]["no_route"]["forbidden_probes"]:
        whys[p["why"].split()[0]] = whys.get(p["why"].split()[0], 0) + 1
    assert whys["pocket"] > 100 and whys["island"] > 50 and whys["side_street"] == 3


# --- every self-gate fires on its crafted defect --------------------------------------------------------

def _defect(edit) -> list[str]:
    _d, out = _sd()
    bad = copy.deepcopy({k: v for k, v in out.items() if k != "_ctx"})
    edit(bad)
    return bb.validate(bad, out["_ctx"])


def test_a_closure_in_a_box_fails():
    def edit(b):
        b["corridors"]["race_cw"]["closure_y_by_vertex"][1514] = 0.0
    fails = _defect(edit)
    assert any("a closure stands at v1514 inside the open box" in f for f in fails), fails


def test_a_pin_off_the_far_strip_fails():
    def edit(b):
        b["corridors"]["race_cw"]["closure_y_by_vertex"][1506] += 0.5
    fails = _defect(edit)
    assert any(f.startswith("pins race_cw: v1506") for f in fails), fails


def test_a_one_in_two_rate_fails():
    def edit(b):
        b["corridors"]["race_acw"]["closure_y_by_vertex"][2000] += 1.6     # ~3 m vertex spacing: 1:2
    fails = _defect(edit)
    assert any(f.startswith("rates race_acw") for f in fails), fails


def test_a_far_mouth_not_behind_the_closure_fails():
    def edit(b):
        b["corridors"]["race_cw"]["closure_y_by_vertex"][1085] = None
    fails = _defect(edit)
    assert any("del_cerro_blvd v1085 is declared behind the closure but no closure stands there" in f for f in fails), fails
    assert any("declares no closure" in f for f in fails), fails               # and the hole itself


def test_a_kerb_under_a_closure_fails():
    def edit(b):
        for k in b["kerbs"]:
            if k["apex"] == 1514 and k["kind"] == "outside":
                k["i"], k["j"] = k["clipped_from"]
    fails = _defect(edit)
    assert any(f.startswith("kerbs: the outside kerb at v1514") and "race_cw" in f for f in fails), fails


def test_a_closure_on_an_island_fails():
    def edit(b):
        y = b["corridors"]["race_cw"]["closure_y_by_vertex"]
        y[1000] += 1.0                                                       # 1 m onto the College island
    fails = _defect(edit)
    assert any(f.startswith("islands race_cw: v1000") for f in fails), fails


def test_a_missing_strip_ring_fails_and_the_planned_fill_finds_the_door():
    d, out = _sd()

    def edit(b):
        for v in range(1900, 1903):
            b["edge_strip_by_vertex"][v] = 0
    fails = _defect(edit)
    assert any(f.startswith("strips:") for f in fails), fails
    bad = copy.deepcopy({k: v for k, v in out.items() if k != "_ctx"})
    edit(bad)
    r = nr.run(d, "race_cw", planned=True, bands=bad, write=False, verbose=False)
    assert r["fail"] and r["leak_m2"] > 0
    assert any(dr["v0"] <= 1901 <= dr["v1"] and dr["side"] == "R" for dr in r["doors"]), r["doors"]


def test_centre_runs_still_in_the_config_fails():
    d = _project(lambda c: c["race"].__setitem__("centre_runs", [[780, 846]]))
    out = bb.build(d, planned_no_route=False)
    assert any("centre_runs is present" in f for f in out["fails"]), out["fails"]


def test_a_perturbed_alvarado_width_fails():
    d = _project(lambda c: c["race"]["corridor"].__setitem__("clear_width_m", 11.5))
    out = bb.build(d, planned_no_route=False)
    assert any(f.startswith("clear width: Alvarado Road as raced is 11.36 m") for f in out["fails"]), out["fails"]


def test_pinned_closure_runs_that_disagree_with_the_zones_fail():
    d = _project(lambda c: c["race"]["corridor"].__setitem__("closure_runs", [[777, 1500], [1521, 2311],
                                                                            [2328, 3289], [3304, 4454]]))
    out = bb.build(d, planned_no_route=False)
    assert any(f.startswith("zones: the declared zones give closure runs") for f in out["fails"]), out["fails"]


def test_a_v1_config_without_a_corridor_is_refused():
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    cfg = json.loads((SD / "track.config.json").read_text(encoding="utf-8"))
    cfg["race"].pop("corridor", None)
    (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    for f in ("centerline.local.json", "median_bands.json", "mouths.json", "bridge.spans.auto.json"):
        shutil.copyfile(SD / "data" / f, d / "data" / f)
    try:
        bb.build(d, planned_no_route=False)
    except SystemExit as e:
        assert "race.corridor" in str(e)
    else:
        raise AssertionError("a config without race.corridor was declared")
