"""tools/layout_dummies.py on the real Lake Murray centreline (ledger 0047).

Pins, per layout: the pole vertex and its LANE (race_cw north of the centreline at v291, race_acw
south at v310 — the 0015 trap: drive_test negative = right, set_start positive = right, dummies.py
+half = left; this tool names the side), the grid/pit stations behind the pole in the layout's own
travel, the facing yaw (reverse = forward + 180 at one vertex; the measured calibration table is in
the docstring below), the AC_TIME L/R swap on the reverse layout, sectors increasing in driving
order, the street-only per-issue override, and the stale-id refusal.

Measured calibration (scratchpad/layouts/judge_facing.py, 2026-10-10, read-only): AC_START_0 local +Z
(kn5 frame) · fast_lane.ai travel — deepforest normal +1.00, six more references +0.98..+1.00, the
installed san_diego_lake_murray_v3 −0.91 (spawn faces ~155° backwards on College). The exporter
maps Blender rotation_euler.z = psi to kn5 local +Z = (sin psi, cos psi); the kn5-frame travel is
(tx, −tz); hence psi = atan2(tx, −tz). Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import layout_dummies as ld  # noqa: E402

SD = ROOT / "tracks" / "san-diego-lake-murray"


def _project() -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    cfg = json.loads((SD / "track.config.json").read_text(encoding="utf-8"))
    # the mainline's three layouts: a layout on another lap (ledger 0054 Phase 2's north_*) reads data/lap.<id>.json,
    # a build record the repo does not carry
    cfg["layouts"] = [lo for lo in cfg["layouts"] if not lo.get("lap")]
    (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    shutil.copyfile(SD / "start_positions.json", d / "start_positions.json")
    for f in ("centerline.local.json", "median_bands.json"):
        shutil.copyfile(SD / "data" / f, d / "data" / f)
    return d


def _load(d: Path, lid: str) -> dict:
    return json.loads((d / "data" / f"dummies_{lid}.json").read_text(encoding="utf-8"))


def _line(d: Path) -> ld.Line:
    cl = json.loads((d / "data" / "centerline.local.json").read_text())
    return ld.Line(cl["points_xyz_m"], cl["widths_m"])


FULL_SET = {"AC_START_%d" % g for g in range(8)} | {"AC_PIT_%d" % p for p in range(8)} | {
    "AC_HOTLAP_START_0", "AC_TIME_0_L", "AC_TIME_0_R", "AC_TIME_1_L", "AC_TIME_1_R", "AC_TIME_2_L", "AC_TIME_2_R"}


def test_three_full_sets_poles_and_lanes():
    d = _project()
    assert ld.write_all(d) == 0
    line = _line(d)
    cw, acw, street = _load(d, "race_cw"), _load(d, "race_acw"), _load(d, "street")
    for dj in (cw, acw, street):
        assert {k for k in dj if not k.startswith("_")} == FULL_SET
    assert cw["_vertex"]["AC_START_0"] == 291 and acw["_vertex"]["AC_START_0"] == 310
    assert cw["_direction"] == "forward" and acw["_direction"] == "reverse"
    # LANE: cw pole north of the centreline (forward-right on westbound Alvarado), acw pole south
    assert cw["AC_START_0"][2] > line.pts[291][2]
    assert acw["AC_START_0"][2] < line.pts[310][2]
    assert cw["_right_of_travel_m"]["AC_START_0"] == 3.25 and acw["_right_of_travel_m"]["AC_START_0"] == 3.25
    assert abs(math.dist(cw["AC_START_0"], line.pts[291]) - math.hypot(3.25, ld.LIFT + ld.DROP_IN)) < 0.05
    # the street layout = grid A by default (same spawn as race_cw), with its own id
    assert street["AC_START_0"] == cw["AC_START_0"] and street["_layout"] == "street"
    assert street["AC_HOTLAP_START_0"] == street["AC_START_0"]


def test_grid_and_pits_step_back_in_each_layouts_own_travel():
    d = _project()
    ld.write_all(d)
    line = _line(d)
    for lid, sgn in (("race_cw", -1.0), ("race_acw", +1.0)):      # "behind" = lower station when forward
        dj = _load(d, lid)
        s0 = line.st[dj["_vertex"]["AC_START_0"]]
        for g in range(1, 8):
            assert abs(dj["_station_m"][f"AC_START_{g}"] - (s0 + sgn * 5.5 * g)) < 0.01, (lid, g)
            assert dj["_right_of_travel_m"][f"AC_START_{g}"] == (4.25 if g % 2 else 2.25)     # stagger 1.0 m (was 1.4)
        for p in range(8):
            assert abs(dj["_station_m"][f"AC_PIT_{p}"] - (s0 + sgn * (45.0 + 7.0 * (p + 1)))) < 0.01, (lid, p)
            assert dj["_right_of_travel_m"][f"AC_PIT_{p}"] == 3.25
        # every slot inside the 13.0 m street AND >= 0.30 m off the kerb-line strip's face (6.5 - 0.82 m) —
        # the hard spawn margin (race_furniture.SPAWN_MARGIN_M / verify_race F); the outer column is 0.48 m clear
        worst = max(abs(v) for k, v in dj["_right_of_travel_m"].items() if k.startswith("AC_START"))
        assert abs((6.5 - 0.82) - (worst + 0.95) - 0.48) < 1e-9, worst
        assert (6.5 - 0.82) - (worst + 0.95) >= 0.30


def test_yaw_is_the_reflected_heading_and_reverse_adds_180():
    d = _project()
    ld.write_all(d)
    line = _line(d)
    cw, acw = _load(d, "race_cw"), _load(d, "race_acw")
    ux, uz = line.travel(291, "forward")
    assert abs(cw["_yaw_deg"]["AC_START_0"] - math.degrees(math.atan2(ux, -uz))) < 2e-3   # stored at 3 decimals
    # same vertex, opposite travel: +180
    assert abs(((ld.yaw_deg(-ux, -uz) - ld.yaw_deg(ux, uz)) % 360.0) - 180.0) < 1e-9
    ux2, uz2 = line.travel(310, "reverse")
    assert abs(acw["_yaw_deg"]["AC_START_0"] - math.degrees(math.atan2(ux2, -uz2))) < 2e-3
    # westbound Alvarado: cw ≈ -101.6°, acw ≈ +79.0° (measured 2026-10-10)
    assert abs(cw["_yaw_deg"]["AC_START_0"] - (-101.6)) < 1.0
    assert abs(acw["_yaw_deg"]["AC_START_0"] - 79.0) < 1.0
    assert "AC_TIME_0_L" not in cw["_yaw_deg"]                   # timing gates are never rotated
    # kn5 local +Z = (sin psi, cos psi) must equal the kn5-frame travel (ux, -uz)
    psi = math.radians(cw["_yaw_deg"]["AC_START_0"])
    assert abs(math.sin(psi) - ux) < 1e-4 and abs(math.cos(psi) + uz) < 1e-4


def test_time_gates_swap_sides_on_the_reverse_layout_and_sectors_increase():
    d = _project()
    ld.write_all(d)
    line = _line(d)
    cw, acw = _load(d, "race_cw"), _load(d, "race_acw")
    assert cw["AC_TIME_0_L"] == acw["AC_TIME_0_R"] and cw["AC_TIME_0_R"] == acw["AC_TIME_0_L"]
    assert cw["_line"]["vertex"] == acw["_line"]["vertex"] == 300
    assert cw["_line"]["sector_vertices"] == [1803, 3310] and acw["_line"]["sector_vertices"] == [3310, 1803]
    for dj, direction in ((cw, "forward"), (acw, "reverse")):
        s_line = line.st[300]
        a1 = line.ahead_m(s_line, line.st[dj["_vertex"]["AC_TIME_1_L"]], direction)
        a2 = line.ahead_m(s_line, line.st[dj["_vertex"]["AC_TIME_2_L"]], direction)
        assert 0 < a1 < a2 < line.lap, (direction, a1, a2)
        assert 0 < dj["_line"]["pole_behind_line_m"] <= ld.LINE_AHEAD_MAX_M


def test_issue_spawn_moves_the_street_layouts_grid_only():
    d = _project()
    assert ld.write_all(d, issue_spawn="0033-college-del-cerro") == 0
    street, cw = _load(d, "street"), _load(d, "race_cw")
    assert street["_issue_spawn"] == "0033-college-del-cerro"
    assert street["_vertex"]["AC_START_0"] == 1078 and cw["_vertex"]["AC_START_0"] == 291
    assert street["AC_TIME_0_L"] == cw["AC_TIME_0_L"]            # the line never moves
    assert street["_vertex"]["AC_PIT_0"] != cw["_vertex"]["AC_PIT_0"]
    assert cw["_issue_spawn"] is None


def test_stale_layout_id_is_refused_and_stale_files_are_removed():
    d = _project()
    (d / "data" / "dummies_full.json").write_text("{}")
    ld.write_all(d)
    assert not (d / "data" / "dummies_full.json").exists()
    try:
        ld.write_all(d, only=["bogus"])
    except SystemExit as e:
        assert "stale id" in str(e)
    else:
        raise AssertionError("--layout bogus must be refused")


def test_validate_layouts_rejects_the_suffix_suppressing_ids_and_bad_kinds():
    fails = ld.validate_layouts([{"id": "full", "direction": "forward", "kind": "street", "start": {}},
                                 {"id": "x", "direction": "sideways", "kind": "race", "start": {}},
                                 {"id": "y", "direction": "forward", "kind": "street", "race_furniture": True, "start": {}}])
    assert any("'full'" in f for f in fails) and any("forward|reverse" in f for f in fails)
    assert any("requires kind 'race'" in f for f in fails)


def test_stagger_is_one_metre_and_the_bands_tool_reads_it():
    """tools/barrier_bands.py declares the grid clearance from THIS module's constants (no restated copy)"""
    import importlib.util
    assert ld.GRID_STAGGER_M == 1.0
    spec = importlib.util.spec_from_file_location("_bb_t", Path(__file__).resolve().parents[2] / "tools" / "barrier_bands.py")
    bb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bb)
    assert bb.GRID_STAGGER_M == ld.GRID_STAGGER_M and bb.GRID_PITCH_M == ld.GRID_PITCH_M
    assert bb.PIT_SETBACK_M == ld.PIT_SETBACK_M and bb.PIT_PITCH_M == ld.PIT_PITCH_M
    assert bb.GRID_CLEAR_MIN_M == 0.30
