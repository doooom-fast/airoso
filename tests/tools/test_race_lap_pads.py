"""Phase 2: a stitched lap must not lose the unused arms of an authored junction pad.

Synthetic topology tests plus a read-only rehearsal of Lake Murray's held north-loop spec.
No Blender, AI generation, live config edits, or writes to track data.
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

from scripts.geometry import race_lap as lap
import barrier_bands as bb


def _fixture():
    def line(points):
        return {"pts": points, "widths": [10.0] * len(points),
                "island_w": [0.0] * len(points), "closed": False}

    lines = {
        "a": line([(5.0 * k, 0.0, 0.0) for k in range(9)]),
        "b": line([(50.0, 0.0, 10.0 + 5 * k) for k in range(9)]),
        "c": line([(50.0 - 5 * k, 0.0, 50.0) for k in range(11)] +
                  [(0.0, 0.0, 45.0 - 5 * k) for k in range(9)]),
    }
    cfg = {"race": {"laps": {"test": {
        "pieces": [{"line": name, "from": 0, "to": len(ln["pts"]) - 1} for name, ln in lines.items()],
        "junction_pads": ["J"]}}}}
    pads = [{"id": "J", "arms": [
        {"kind": "route", "connector": "a", "end": "end"},
        {"kind": "route", "connector": "b", "end": "start"},
        {"kind": "stub", "stub": "east"}, {"kind": "stub", "stub": "south"}],
        "stubs": {
            "east": {"road": "East", "width_m": 10.0,
                     "mouth_line_xz": [[60.0, -5.0], [60.0, 5.0]],
                     "far_xz": [[76.0, -5.0], [76.0, 0.0], [76.0, 5.0]]},
            "south": {"road": "South", "width_m": 10.0,
                      "mouth_line_xz": [[45.0, -10.0], [55.0, -10.0]],
                      "far_xz": [[45.0, -26.0], [50.0, -26.0], [55.0, -26.0]]}}}]
    return cfg, lines, pads


def _stitch(cfg, lines, pads):
    return lap.stitch(ROOT, cfg, "test", lines=lines, mouths=[], spans=[], pads=pads)


def _reverse(spec):
    spec["pieces"] = [{**p, "from": p["to"], "to": p["from"],
                       **({"reverse": not p["reverse"]} if "reverse" in p else {})}
                      for p in reversed(spec["pieces"])]


def _refused(cfg, lines, pads, message):
    try:
        _stitch(cfg, lines, pads)
    except SystemExit as e:
        assert message in str(e), str(e)
    else:
        raise AssertionError("invalid pad declaration accepted")


def test_pad_arms_are_probed_on_their_own_stubs_in_both_directions():
    cfg, lines, pads = _fixture()
    fwd = _stitch(cfg, lines, pads)
    expected = {"J:east": [70.0, 0.0], "J:south": [50.0, -20.0]}
    assert {mo["piece"]: mo["probe_xz"] for mo in fwd["mouths"]} == expected
    assert all(mo["kind"] == "pad_branch" and mo["side"] == -1 for mo in fwd["mouths"])
    _reverse(cfg["race"]["laps"]["test"])
    rev = _stitch(cfg, lines, pads)
    assert {mo["piece"]: mo["probe_xz"] for mo in rev["mouths"]} == expected
    assert all(mo["side"] == 1 for mo in rev["mouths"])
    # Rotating the declaration puts the pad across the closure seam; no lost arm or off-lap index.
    cfg, lines, pads = _fixture()
    ps = cfg["race"]["laps"]["test"]["pieces"]
    ps[:] = ps[1:] + ps[:1]
    seam = _stitch(cfg, lines, pads)
    assert {mo["piece"]: mo["probe_xz"] for mo in seam["mouths"]} == expected
    assert all(0 <= mo["host_vertex"] < seam["point_count"] - 1 for mo in seam["mouths"])


def test_pad_declarations_fail_if_missing_disconnected_duplicate_or_too_short():
    cfg, lines, pads = _fixture()
    _refused(cfg, lines, [], "expected one entry")
    _refused(cfg, lines, pads + pads, "expected one entry")
    bad = copy.deepcopy(cfg)
    bad["race"]["laps"]["test"]["pieces"][0]["to"] -= 1
    _refused(bad, lines, pads, "two route endpoints")
    bad = copy.deepcopy(cfg)
    bad["race"]["laps"]["test"]["junction_pads"] = ["J", "J"]
    _refused(bad, lines, pads, "unique pad ids")
    short = copy.deepcopy(pads)
    short[0]["stubs"]["east"]["far_xz"] = [[65.0, -5.0], [65.0, 5.0]]
    _refused(cfg, lines, short, "too short")
    with tempfile.TemporaryDirectory() as tmp:
        try:
            lap.stitch(tmp, cfg, "test", lines=lines, mouths=[], spans=[])
        except SystemExit as e:
            assert "pads.plan.json is missing" in str(e)
        else:
            raise AssertionError("missing declared pad file accepted")


def test_undeclared_pads_do_not_change_existing_laps():
    cfg, lines, pads = _fixture()
    del cfg["race"]["laps"]["test"]["junction_pads"]
    assert _stitch(cfg, lines, pads) == _stitch(cfg, lines, [])


def test_held_north_lap_keeps_source_geometry_and_all_six_pad_arms():
    proj = ROOT / "tracks" / "san-diego-lake-murray"
    held = json.loads((proj / "source/expansion/race.north.held.json").read_text())
    cfg = {"race": {"laps": {held["lap"]: held["spec"]}}}
    assert held["status"] == "held"
    rec = lap.stitch(proj, cfg, held["lap"])
    assert 8700 < rec["lap_m"] < 8800
    assert rec["points_xyz_m"][0] == rec["points_xyz_m"][-1]
    lines = lap.load_lines(proj)
    for point, (name, vertex) in zip(rec["points_xyz_m"], rec["source_by_vertex"]):
        if name != "join":
            assert point == [round(c, 4) for c in lines[name]["pts"][vertex]]
    arms = [mo for mo in rec["mouths"] if mo["kind"] == "pad_branch"]
    assert {mo["piece"] for mo in arms} == {"J2:S1", "J2:S2", "J3:S3", "J3:S4", "J4:S5", "J4:S6"}
    baseline_cfg = copy.deepcopy(cfg)
    baseline_cfg["race"]["laps"][held["lap"]].pop("junction_pads")
    baseline = lap.stitch(proj, baseline_cfg, held["lap"])
    assert {k: v for k, v in rec.items() if k != "mouths"} == {k: v for k, v in baseline.items() if k != "mouths"}
    assert [mo for mo in rec["mouths"] if mo["kind"] != "pad_branch"] == baseline["mouths"]
    # The consumer must carry the actual branch XY into no_route, not replace it with a lateral guess.
    pts, widths = rec["points_xyz_m"], rec["widths_m"]
    m = len(pts) - 1
    closed = [{**mo, "side": "L" if mo["side"] > 0 else "R"} for mo in arms]
    probes = bb._mouth_probes(closed, widths, m, pts, bb._normals(pts, m))
    assert [p["xz"] for p in probes] == [mo["probe_xz"] for mo in arms]
    assert all(p["why"].startswith("pad_branch ") for p in probes)
    pads = json.loads((proj / "data/pads.plan.json").read_text())["pads"]
    for mo in arms:
        pid, sid = mo["piece"].split(":")
        stub = next(p for p in pads if p["id"] == pid)["stubs"][sid]
        mouth = stub["mouth_line_xz"]
        centre = [sum(p[j] for p in mouth) / len(mouth) for j in (0, 1)]
        assert abs(math.dist(centre, mo["probe_xz"]) - lap.BRANCH_PROBE_M) < 0.001
    _reverse(cfg["race"]["laps"][held["lap"]])
    rev = lap.stitch(proj, cfg, held["lap"])
    backwards = {mo["piece"]: mo for mo in rev["mouths"] if mo["kind"] == "pad_branch"}
    assert len(backwards) == 6
    for mo in arms:
        assert backwards[mo["piece"]]["probe_xz"] == mo["probe_xz"]
        assert backwards[mo["piece"]]["side"] == -mo["side"]
