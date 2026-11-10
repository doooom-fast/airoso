"""Milford furniture pass 4 (ledger 0082, 0.1.10): the far-west roofs NAIP 2022's west strip confirms, as far blocks at their
measured roof elevation, through existing keys only. stdlib."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MF = ROOT / "tracks" / "milford-road-course-lm"
P4 = MF / "source" / "furniture" / "pass4"


def test_blocks_are_measured_and_confirmed():
    tiers = json.loads((P4 / "tiers_p4.json").read_text())
    by_fp = {json.dumps(t["footprint_lonlat"]): t for t in tiers}
    seen = {r["id"] for r in json.loads((P4 / "strip_check.json").read_text())}
    blocks = json.loads((P4 / "blocks.json").read_text())
    assert blocks
    for b in blocks:
        t = by_fp[json.dumps(b["footprint_lonlat"])]
        assert t["src"] in (21, 77, 81) and t["src"] in seen          # only the roofs the 2022 strip shows standing
        assert b["roof_z_m"] == t["roof_z_local_m"] and b["off_terrain"] is True
        assert "[measured]" in b["_source"] and "[invented: no wall is seen from above]" in b["_source"]


def test_config_names_the_file_once_and_ships_it():
    cfg = json.loads((MF / "track.config.json").read_text(encoding="utf-8"))
    assert sum(g.get("file") == "source/furniture/pass4/blocks.json" for g in cfg["scenery"]["bespoke"]["blocks"]) == 1
    ship = json.loads((MF / "ship.json").read_text(encoding="utf-8"))
    assert "source/furniture/pass4/blocks.json" in ship["sync_in"]["required"]


def test_no_other_track_names_pass4():
    for cfgp in sorted((ROOT / "tracks").glob("*/track.config.json")):
        if cfgp.parent.name != "milford-road-course-lm":
            assert "source/furniture/pass4" not in cfgp.read_text(encoding="utf-8"), cfgp


def test_every_drop_is_listed_with_its_reason():
    drops = json.loads((P4 / "blocks_dropped.json").read_text())
    # 0.1.11 (ledger 0082 'Far ground (0.1.11)'): one more, refused by the author on the real ground (far_ground/scripts/drop_set_in.py)
    assert all(d["why"] in ("small or empty", "a planted tree within 1 m", "set into its slope") for d in drops)
    assert [d["key"] for d in drops if d["why"] == "set into its slope"] == ["mpg_nw_complex_0"]
    assert len(drops) + len(json.loads((P4 / "blocks.json").read_text())) == len(json.loads((P4 / "tiers_p4.json").read_text()))
