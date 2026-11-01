"""tools/drive1_gates.py — the Lariat's Drive-1 verdict (V3-PLAN P5 "the Drive-1 gate set"; ledger 0048), on synthetic
gate reports whose truth is known:

- every gating row green -> PASS, force_install_ok; the recorded rows (drops, Drive-2 gates, race) never gate,
  and drive_test's OWN fail (it counts unguarded drops) does not make the Drive-1 row red;
- each P5 threshold flips its own row: a severe step, replication p95 over 0.5 m, kinks over the declared ceiling,
  a zero-count key, an audit hard class, F over 15, a kn5_ground_check FAIL, a lid-end step over 0.10 m (stations
  mirrored for the reverse layout);
- a missing report is red ("not run"), never a pass; tier seams are n/a, never a pass;
- --force-install: worse than the July reference on any key, or any of obstruction / floating / soft-top > 0,
  sets force_install_ok false; a red run that is no worse than July keeps it true;
- a config without gates.drive1 is an input error (exit 2).
Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import drive1_gates as d1  # noqa: E402

LAP = 1000.0
CFG = {
    "slug": "toy", "layouts": [{"id": "fwd", "direction": "forward", "race_furniture": False},
                               {"id": "rev", "direction": "reverse", "race_furniture": False}],
    "capture": {"bridges": [{"id": "lid", "center_m": 400.0, "len_m": 40.0}]},
    "gates": {"drive_test": {"kinks_per_km_max": 19.49},
              "drive1": {"drive_test": {"severe_steps_max": 0, "replication_p95_max_m": 0.5},
                         "audit": {"f_curb_max": 15}, "kn5_ground_check": {"lid_end_step_max_m": 0.10},
                         "july_reference": {"severe_steps": 253, "kinks_per_km": 68.3, "excursion_drops": 738,
                                            "excursion_far_ledges": 382, "obstruction_stations": 0,
                                            "floating_furniture": 0, "soft_top_in_lane": 0}}},
}
DT = {"lap_m": LAP, "soft_top_in_lane": 0, "obstruction_stations": 0, "floating_furniture": 0, "undrivable_corners": 0,
      "daylight_gaps": 0, "severe_steps": 0, "severe_per_km": 0.0, "kinks_per_km": 3.0, "excursion_drops": 300,
      "excursion_far_ledges": 10, "steps_per_km": 5.0, "apron_steps": 0, "fail": True,
      "replication_vs_measured": {"median": 0.05, "p95": 0.2, "max": 0.6}, "worst": {"severe_all": []}}
AUDIT = {"A_supports_in_road": 0, "B_terrain_poke": 0, "C_junction_crossings": 0, "D_wall_on_road": 0,
         "E_wall_floating": 0, "F_curb_not_flush": 0, "G_prop_floating": None, "H_ground_above_deck": 0,
         "I_sidewalk_isolating": 0, "J_terrain_span": 0, "K_kerb_in_carriageway": 0}
KGC = {"fail": False, "reasons": [], "fidelity": "skipped: gate OBJ written from this kn5", "double_sheet_cells": 0,
       "seating": {"walls": {"objects": 10, "hovering": 0}},
       "road_over_ground": {"over": 12, "samples": 3000, "p95_m": 0.04, "max_m": 0.3}}


def _proj(mut=None, skip=()):
    p = Path(tempfile.mkdtemp())
    (p / "data" / "aerial").mkdir(parents=True)
    (p / "build").mkdir()
    (p / "build" / "toy.kn5").write_bytes(b"kn5")
    files = {
        "track.config.json": copy.deepcopy(CFG),
        "data/drive_test.fwd.json": dict(copy.deepcopy(DT), direction="forward"),
        "data/drive_test.rev.json": dict(copy.deepcopy(DT), direction="reverse"),
        "data/audit.json": dict(AUDIT),
        "data/oneway_check.json": {"verdict": "PASS", "fails": [], "layouts": [
            {"id": "fwd", "checked": True, "verdict": "PASS", "against_total_m": 0, "undeclared_against_m": 0}]},
        "data/aerial/paint_gate.json": {"pass": True, **{k: {"pass": True} for k in
                                                         ("a_paint", "b_curvature", "c_topology", "d_closure")}},
        "data/crossfall_gate.json": {"status_of_file": "estimated", "stations": 300, "fail": False, "problems": [],
                                     "halves": {"left": {"worst_change_pct": 3.2, "swings": 0},
                                                "right": {"worst_change_pct": 3.4, "swings": 0}}},
        "data/road_inventory.json": {"fail": False, "pavement_triangles": 1000},
        "data/stacked_legs.json": {"fail": False, "pairs": 12},
        "data/kn5_ground_check.fwd.json": copy.deepcopy(KGC),
        "data/kn5_ground_check.rev.json": copy.deepcopy(KGC),
        "data/underlay.report.json": {"obj_md5": "abc", "groups": [{"name": "1ROAD_main"}]},
    }
    if mut:
        mut(files)
    for rel, obj in files.items():
        if rel in skip:
            continue
        (p / rel).write_text(json.dumps(obj), encoding="utf-8")
    return p


def _row(rep, name):
    return next(r for r in rep["rows"] if r["gate"] == name)


def test_all_green_passes_and_recorded_rows_never_gate():
    rep = d1.judge(_proj())
    assert rep["fail"] is False and rep["red"] == [] and rep["force_install_ok"] is True, rep["red"]
    assert _row(rep, "drive_test fwd")["pass"] is True     # drive_test's own fail (drops) does not gate Drive 1
    assert _row(rep, "drive_test fwd (recorded)")["numbers"]["drive_test_own_fail"] is True
    assert _row(rep, "tier seams")["pass"] is None and _row(rep, "tier seams")["kind"] == "n/a"
    for g in ("verify_edges", "verify_signs", "TreeFX check", "sightline_check", "race gates"):
        assert _row(rep, g)["kind"] == "recorded" and _row(rep, g)["pass"] is None, g
    k = _row(rep, "kn5_ground_check fwd")
    assert k["pass"] is True and k["numbers"]["road_over_ground_p95_m"] == 0.04 and k["numbers"]["fail"] is False
    assert d1.main([str(_proj())]) == 0


def test_each_threshold_flips_its_own_row():
    def dt(key, val, lid="fwd"):
        return lambda f: f[f"data/drive_test.{lid}.json"].__setitem__(key, val)
    cases = [
        (dt("severe_steps", 1), "drive_test fwd", "severe_steps 1 > 0"),
        (dt("replication_vs_measured", {"median": 0.1, "p95": 0.51, "max": 1.0}), "drive_test fwd", "replication p95"),
        (dt("replication_vs_measured", None), "drive_test fwd", "not measured"),
        (dt("kinks_per_km", 19.5, "rev"), "drive_test rev", "kinks 19.5/km > 19.49/km"),
        (dt("daylight_gaps", 2), "drive_test fwd", "daylight_gaps"),
        (dt("undrivable_corners", 1), "drive_test fwd", "undrivable_corners"),
        (lambda f: f["data/audit.json"].__setitem__("B_terrain_poke", 3), "audit_mesh", "B_terrain_poke 3"),
        (lambda f: f["data/audit.json"].__setitem__("F_curb_not_flush", 16), "audit_mesh", "F_curb_not_flush 16 > 15"),
        (lambda f: f["data/kn5_ground_check.rev.json"].update(fail=True, reasons=["road floating over ground"]),
         "kn5_ground_check rev", "floating"),
        (lambda f: f["data/road_inventory.json"].__setitem__("fail", True), "road inventory", ""),
        (lambda f: f["data/stacked_legs.json"].__setitem__("fail", True), "stacked legs", ""),
        (lambda f: f["data/crossfall_gate.json"].__setitem__("fail", True), "roll rate", ""),
        (lambda f: f["data/aerial/paint_gate.json"].__setitem__("pass", False), "hairpin / paint centreline", ""),
        (lambda f: f["data/oneway_check.json"].update(verdict="FAIL", fails=["x"]), "one-way", ""),
    ]
    for mut, gate, needle in cases:
        rep = d1.judge(_proj(mut))
        assert rep["red"] == [gate], (gate, rep["red"])
        assert needle in _row(rep, gate).get("note", ""), (gate, _row(rep, gate).get("note"))


def test_lid_end_steps_read_in_each_layouts_own_stations():
    # the lid spans 380-420 m forward; reverse stations are lap - s: its ends are at 580 and 620 m there
    def fwd_step(f):
        f["data/drive_test.fwd.json"]["worst"]["severe_all"] = [[381.0, 0.0, 0.12], [700.0, 0.0, 0.5]]
    rep = d1.judge(_proj(fwd_step))
    lid = _row(rep, "lid ends (no step > 0.1 m)")
    assert lid["pass"] is False and "lid ends (no step > 0.1 m)" in rep["red"]
    worst = {x["layout"]: x["worst_step_m"] for x in lid["numbers"]["decks"]}
    assert worst == {"fwd": 0.12, "rev": None}, worst            # the 0.5 m step at 700 m is not at the lid
    def rev_step(f):
        f["data/drive_test.rev.json"]["worst"]["severe_all"] = [[618.0, 1.0, 0.08], [381.0, 0.0, 0.3]]
    rep = d1.judge(_proj(rev_step))
    lid = _row(rep, "lid ends (no step > 0.1 m)")
    assert lid["pass"] is True, lid                      # 0.08 at the reverse end (620 m) passes; 381 m is not an end
    assert {x["layout"]: x["ends_m"] for x in lid["numbers"]["decks"]}["rev"] == [580.0, 620.0]


def test_a_missing_report_is_red_never_a_pass():
    for rel, gate in (("data/drive_test.rev.json", "drive_test rev"), ("data/audit.json", "audit_mesh"),
                      ("data/kn5_ground_check.fwd.json", "kn5_ground_check fwd"), ("data/road_inventory.json", "road inventory"),
                      ("data/stacked_legs.json", "stacked legs"), ("data/crossfall_gate.json", "roll rate"),
                      ("data/oneway_check.json", "one-way"), ("data/aerial/paint_gate.json", "hairpin / paint centreline")):
        rep = d1.judge(_proj(skip=(rel,)))
        assert gate in rep["red"] and "not run" in _row(rep, gate)["note"], (rel, rep["red"])
    p = _proj()
    (p / "build" / "toy.kn5").unlink()
    assert "verify_kn5" in d1.judge(p)["red"]


def test_force_install_follows_the_july_reference():
    # red (2 severe steps, drops far over the per-km line) but no worse than July on any key: forcing allowed
    def red_ok(f):
        f["data/drive_test.fwd.json"].update(severe_steps=2, excursion_drops=700)
    rep = d1.judge(_proj(red_ok))
    assert rep["fail"] is True and rep["force_install_ok"] is True, rep["force_install_why_not"]
    for key, val, needle in (("severe_steps", 254, "severe_steps 254 > July 253"),
                             ("kinks_per_km", 70.0, "kinks_per_km 70.0 > July 68.3"),
                             ("excursion_drops", 739, "excursion_drops 739 > July 738"),
                             ("obstruction_stations", 1, "always 0"), ("floating_furniture", 1, "always 0"),
                             ("soft_top_in_lane", 1, "always 0")):
        rep = d1.judge(_proj(lambda f, k=key, v=val: f["data/drive_test.rev.json"].__setitem__(k, v)))
        assert rep["force_install_ok"] is False and any(needle in w for w in rep["force_install_why_not"]), \
            (key, rep["force_install_why_not"])
    rep = d1.judge(_proj(skip=("data/drive_test.fwd.json",)))
    assert rep["force_install_ok"] is False and "fwd: drive_test not run" in rep["force_install_why_not"]


def test_input_errors_exit_2():
    p = _proj(lambda f: f["track.config.json"]["gates"].pop("drive1"))
    assert d1.main([str(p)]) == 2
    p = _proj(lambda f: f["track.config.json"]["gates"]["drive1"]["july_reference"].clear())
    assert d1.main([str(p)]) == 2
    assert d1.main([]) == 2


def test_the_lariat_declares_the_drive1_thresholds():
    cfg = json.loads((ROOT / "tracks" / "lookout-lariat" / "track.config.json").read_text(encoding="utf-8"))
    g = cfg["gates"]["drive1"]
    assert g["drive_test"]["severe_steps_max"] == 0 and g["drive_test"]["replication_p95_max_m"] == 0.5
    assert g["audit"]["f_curb_max"] == 15 and g["kn5_ground_check"]["lid_end_step_max_m"] == 0.10
    assert {k: v for k, v in g["july_reference"].items() if not k.startswith("_")} == {
        "severe_steps": 253, "kinks_per_km": 68.3, "excursion_drops": 738, "excursion_far_ledges": 382,
        "obstruction_stations": 0, "floating_furniture": 0, "soft_top_in_lane": 0}
    for doc in (g["drive_test"]["_severe_doc"], g["drive_test"]["_replication_doc"], g["audit"]["_doc"],
                g["kn5_ground_check"]["_doc"], g["july_reference"]["_doc"]):
        assert "[invented" in doc or "[std" in doc or "[measured" in doc, doc
