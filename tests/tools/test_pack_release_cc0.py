"""tools/pack_release.py — the CC0 variant drops the race layouts (ledger 0047 Q10: the K-rail pack's
licence is UNRECORDED in assets/licenses.json, so san_diego_lake_murray_race.kn5 and the two race
layouts ship in the FULL package only)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import pack_release as pr  # noqa: E402

SLUG = pr.SLUG


def _folder(layouts):
    d = Path(tempfile.mkdtemp())
    f = d / SLUG
    f.mkdir()
    (f / f"{SLUG}.kn5").write_bytes(b"road")
    (f / f"{SLUG}_race.kn5").write_bytes(b"race")
    for lo in layouts:
        lid = lo["id"]
        (f / f"models_{lid}.ini").write_text("[MODEL_0]\n")
        (f / "ui" / lid).mkdir(parents=True)
        (f / "ui" / lid / "ui_track.json").write_text("{}")
        (f / lid / "data").mkdir(parents=True)
        (f / lid / "map.png").write_bytes(b"png")
        (f / f"{SLUG}__{lid}.kn5").write_bytes(b"spawn")
    cfg = d / "track.config.json"
    cfg.write_text(json.dumps({"slug": SLUG, "layouts": layouts}))
    return f, cfg


THREE = [{"id": "street", "kind": "street", "race_furniture": False},
         {"id": "race_cw", "kind": "race", "race_furniture": True},
         {"id": "race_acw", "kind": "race", "race_furniture": True}]


def test_race_layouts_and_race_kn5_leave_the_cc0_folder_street_stays():
    f, cfg = _folder(THREE)
    removed = set(pr.strip_race_layouts(f, cfg))
    assert removed == {f"{SLUG}_race.kn5",
                       "models_race_cw.ini", "ui/race_cw", "race_cw", f"{SLUG}__race_cw.kn5",
                       "models_race_acw.ini", "ui/race_acw", "race_acw", f"{SLUG}__race_acw.kn5"}, removed
    assert (f / "models_street.ini").exists() and (f / "ui" / "street" / "ui_track.json").exists()
    assert (f / "street" / "map.png").exists() and (f / f"{SLUG}__street.kn5").exists() and (f / f"{SLUG}.kn5").exists()
    assert not (f / f"{SLUG}_race.kn5").exists() and not (f / "ui" / "race_cw").exists()


def test_single_street_layout_folder_is_untouched_except_a_stray_race_kn5():
    f, cfg = _folder([{"id": "street", "kind": "street", "race_furniture": False}])
    removed = pr.strip_race_layouts(f, cfg)
    assert removed == [f"{SLUG}_race.kn5"], removed


def test_refuses_to_leave_no_layout():
    f, cfg = _folder([{"id": "race_cw", "kind": "race", "race_furniture": True}])
    try:
        pr.strip_race_layouts(f, cfg)
    except SystemExit as e:
        assert "no layout" in str(e)
    else:
        raise AssertionError("a race-only folder was stripped to nothing")
