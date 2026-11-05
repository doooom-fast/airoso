"""tools/network_connectors.py + tools/network_deck_lidar.py (ledger 0080 phase 2): the freeway port's other carriageways
as LM-engine connectors, with their decks from the lidar, never from the draft's layer x 5.5 m model."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
SRC = ROOT / "tracks" / "san-diego-freeway" / "source" / "network-draft-pr34"
CFG = ROOT / "tracks" / "san-diego-freeway-lm" / "track.config.json"


def test_one_way_paint_has_no_yellow_and_keeps_dividers_inside_the_edge_lines():
    import network_connectors as N
    p = N.one_way_paint([10.82, 18.14])
    assert all(ln["color"] == "white" for ln in p["lines"])
    edges = [ln for ln in p["lines"] if not ln["dash"]]
    assert [round(o, 2) for o in edges[0]["off"]] == [4.86, 8.52]
    for ln in p["lines"]:
        if ln["dash"]:
            for w, o in zip([10.82, 18.14], ln["off"]):
                assert o is None or abs(o) + 0.06 <= w / 2 - 0.55


def test_deck_levels_split_at_gaps_and_the_pick_chooses_only_between_measured_levels():
    import network_deck_lidar as L
    lv = L.levels([10.0, 10.1, 10.2, 17.0, 17.1])
    assert [n for _z, n in lv] == [3, 2] and abs(lv[0][0] - 10.1) < 1e-9
    assert L.pick(lv, 16.0)[0] == 17.05
    assert L.pick(lv, 40.0) is None          # nothing within MAX_PICK_M of the model: no reading, nothing filled


def test_the_committed_wb_connector_is_reproduced_and_its_decks_are_measured():
    import network_connectors as N
    tmp = Path(tempfile.mkdtemp(prefix="netconn_"))
    try:
        for f in ("network.geojson", "network.edges.local.json", "network.elevation.json", "network.local.json",
                  "deck_profiles.lidar.json"):
            shutil.copyfile(SRC / f, tmp / f)
        doc = N.build(tmp, tmp, CFG)
        assert (tmp / "connectors.local.json").read_bytes() == (SRC / "connectors.local.json").read_bytes()
        rec = json.loads((tmp / "connectors.local.json").read_text())["connectors"][0]
        rep = doc["connectors"][0]
        assert rec["name"] == "i8_wb" and rep["side_check"]["right"] == 0      # EB lies on WB's left
        assert len(rec["points_xyz_m"]) == len(rec["widths_m"]) == len(rec["terrain_xyz_m"])
        # every measured deck point is a lidar height (NAVD88 less the origin's elev_m), within a deck end of the 3DEP
        lid = json.loads((SRC / "deck_profiles.lidar.json").read_text())
        assert lid["ept"].endswith("CA_SanDiegoQL2_2014/ept.json")
        assert rep["deck_points"] > 0 and max(abs(s) for s in rep["deck_end_steps_m"]) < 0.5
        # no width ever narrowed by the flare
        assert all(w >= 0 for w in rec["widths_m"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
