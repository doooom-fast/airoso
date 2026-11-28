"""The opt-in start.pit_offset_right_m (Denver 2026-11-27, Kevin: "Yes, both") is right of travel only, in both tools.

Codex's review of 582aa6e2: tools/layout_dummies.py places a SIGNED pit offset, while tools/barrier_bands.py took abs()
before its spawn check, so a negative declaration would put the pit cars on the left and the gate would check the mirrored
right side, which is a different place in an asymmetric corridor. Both tools now refuse a negative declaration. The
asymmetric case (pits at their own offset, the grid at another) is pinned on the real Lake Murray centreline, in both
travel directions. Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import layout_dummies as ld  # noqa: E402
import sd_v0180  # noqa: E402

SD = ROOT / "tracks" / "san-diego-lake-murray"


def _project(pit_off) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    cfg = sd_v0180.one_road_college(json.loads((SD / "track.config.json").read_text(encoding="utf-8")))
    cfg["layouts"] = [lo for lo in cfg["layouts"] if not lo.get("lap")]
    for lo in cfg["layouts"]:
        if lo.get("id") in ("race_cw", "race_acw"):
            lo.setdefault("start", {})["pit_offset_right_m"] = pit_off
    (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    shutil.copyfile(SD / "start_positions.json", d / "start_positions.json")
    for f in ("centerline.local.json", "median_bands.json"):
        shutil.copyfile(sd_v0180.DATA_0204 / f, d / "data" / f)
    return d


def _load(d: Path, lid: str) -> dict:
    return json.loads((d / "data" / f"dummies_{lid}.json").read_text(encoding="utf-8"))


def test_pits_stand_at_their_own_offset_right_of_travel_in_both_directions():
    d = _project(2.0)
    assert ld.write_all(d) == 0
    cl = json.loads((d / "data" / "centerline.local.json").read_text())
    line = ld.Line(cl["points_xyz_m"], cl["widths_m"])
    for lid in ("race_cw", "race_acw"):
        dj = _load(d, lid)
        assert dj["_right_of_travel_m"]["AC_START_0"] == 3.25, lid            # the grid keeps its own offset
        for p in range(8):
            assert dj["_right_of_travel_m"][f"AC_PIT_{p}"] == 2.0, (lid, p)   # the pits stand at theirs
    # right of TRAVEL: forward (cw) pits and reverse (acw) pits stand on opposite sides of the centreline
    cw, acw = _load(d, "race_cw"), _load(d, "race_acw")

    def side(dj, key):
        k = dj["_vertex"][key]
        a, b = line.pts[k], line.pts[min(k + 1, len(line.pts) - 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        px, pz = dj[key][0] - a[0], dj[key][2] - a[2]
        return 1.0 if (tx * pz - tz * px) > 0 else -1.0

    assert side(cw, "AC_PIT_0") == -side(acw, "AC_PIT_0")


def test_a_negative_pit_offset_is_refused_by_the_dummies():
    d = _project(-2.0)
    assert ld.write_all(d) != 0


def test_a_negative_pit_offset_is_refused_by_the_bands_gate():
    src = (ROOT / "tools" / "barrier_bands.py").read_text(encoding="utf-8")
    i = src.index('pit_off = float(start["pit_offset_right_m"])')
    block = src[i:i + 600]
    assert "abs(" not in block.split("\n")[0]
    assert "if pit_off < 0.0:" in block and "raise SystemExit" in block
