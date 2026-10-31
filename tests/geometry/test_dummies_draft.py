"""The loop prep's single-layout dummies (ledger 0060, 2026-10-29): scripts/ac/build_kn5_loop.py takes the engine
draft's data/dummies.json (scripts.geometry.dummies.load_draft) instead of recomputing from centerline.local.json —
recomputed, Exotics Racing's 8 pits walked 14-45 m off the road (verify_kn5 on the Windows box) — and faces the grid
with atan2(east, -north) at the start (scripts.geometry.dummies.facing_yaw), the measured convention of the per-layout
spawn scenes (tools/layout_dummies.yaw_deg, ledger 0047); the atan2(east, north) that stood in the prep faced a
north-bound grid backwards. Plain ``test_*`` for tests/run_tests.py."""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

from scripts.geometry import dummies as dmod

ROOT = Path(__file__).resolve().parents[2]
PREP = (ROOT / "scripts" / "ac" / "build_kn5_loop.py").read_text(encoding="utf-8")


def test_load_draft_reads_the_engines_placements_and_nothing_else():
    d = Path(tempfile.mkdtemp())
    assert dmod.load_draft(d / "missing.json") == {}
    p = d / "dummies.json"
    p.write_text("not json", encoding="utf-8")
    assert dmod.load_draft(p) == {}
    p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert dmod.load_draft(p) == {}
    p.write_text(json.dumps({"AC_START_0": [9.543, 8.981, 171.408], "AC_PIT_0": [-2.286, 9.11, 174.519],
                             "_direction": "forward", "_yaw_deg": {"AC_START_0": 12.0}, "AC_BAD": [1, 2],
                             "AC_WORSE": ["x", 1, 2], "NOT_AC": [0, 0, 0]}), encoding="utf-8")
    got = dmod.load_draft(p)
    assert got == {"AC_START_0": (9.543, 8.981, 171.408), "AC_PIT_0": (-2.286, 9.11, 174.519)}
    assert all(isinstance(v, tuple) and len(v) == 3 for v in got.values())
    p.write_text("{}", encoding="utf-8")
    assert dmod.load_draft(p) == {}, "an empty placement (a multi-layout prep writes {}) is no placement"


def test_facing_yaw_is_atan2_east_minus_north_at_the_nearest_vertex():
    north = [(0.0, 0.0, 3.0 * k) for k in range(10)]            # travel +N
    assert math.isclose(dmod.facing_yaw(north, (0.3, 0.0, 0.0)), math.pi, abs_tol=1e-9)
    east = [(3.0 * k, 0.0, 0.0) for k in range(10)]             # travel +E
    assert math.isclose(dmod.facing_yaw(east, (0.0, 0.0, 0.2)), math.pi / 2, abs_tol=1e-9)
    south = north[::-1]
    assert math.isclose(dmod.facing_yaw(south, (0.0, 0.0, 27.0)), 0.0, abs_tol=1e-9), "an unrotated node faces south"
    # the same numbers tools/layout_dummies.yaw_deg gives (the per-layout spawn scenes Kevin drove on 0.19.1)
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import layout_dummies as ld
    for ux, uz in ((0.0, 1.0), (1.0, 0.0), (0.6, -0.8), (-0.6, 0.8)):
        line = [(0.0, 0.0, 0.0), (ux, 0.0, uz), (2 * ux, 0.0, 2 * uz)]
        assert math.isclose(math.degrees(dmod.facing_yaw(line, (0.0, 0.0, 0.0))), ld.yaw_deg(ux, uz), abs_tol=1e-9)
    # nearest vertex, not the first: a line that turns, the start on its second leg
    bent = [(0.0, 0.0, 0.0), (0.0, 0.0, 10.0), (0.0, 0.0, 20.0), (10.0, 0.0, 20.0), (20.0, 0.0, 20.0)]
    assert math.isclose(dmod.facing_yaw(bent, (12.0, 0.0, 20.4)), math.pi / 2, abs_tol=1e-9)
    # the last vertex uses the leg into it (a closed loop's closure vertex repeats v0: never a zero tangent)
    assert math.isclose(dmod.facing_yaw(bent, (20.0, 0.0, 20.0)), math.pi / 2, abs_tol=1e-9)
    assert dmod.facing_yaw([(0.0, 0.0, 0.0)], (0.0, 0.0, 0.0)) == 0.0


def test_facing_yaw_mirrors_east_with_a_mirrored_draft():
    east = [(3.0 * k, 0.0, 0.0) for k in range(10)]
    assert math.isclose(dmod.facing_yaw(east, (-15.0, 0.0, 0.0), mirror_x=True), -math.pi / 2, abs_tol=1e-9)
    north = [(0.0, 0.0, 3.0 * k) for k in range(10)]
    assert math.isclose(dmod.facing_yaw(north, (0.0, 0.0, 0.0), mirror_x=True), math.pi, abs_tol=1e-9)


def test_the_prep_takes_the_drafts_dummies_and_faces_travel():
    i = PREP.index("if len(_layouts) > 1:")
    branch = PREP[i:PREP.index("(proj / \"data\" / \"dummies.json\").write_text", i)]
    assert 'dmod.load_draft(proj / "data" / "dummies.json")' in branch
    assert "dmod.facing_yaw(cl, start_at, mirror_x=mirror_x and from_draft)" in branch
    assert 'placed.get("AC_START_0")' in branch
    assert "math.atan2(tx, ty)" not in branch, "the backwards facing is gone"
    assert "dmod.place_dummies(cl, widths, n_sectors=3, n_pits=n_pits" in branch, "the no-draft fallback stays"
