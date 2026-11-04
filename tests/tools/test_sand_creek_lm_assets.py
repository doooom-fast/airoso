"""Sand Creek on Lake Murray's engine, the assets round (ledger 0079): every new key is opt-in and Lake Murray names none of
them; the crowns reader finds one tree per crown and nothing on bare ground; the lidar roof helpers; the texture gate.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
LM = ROOT / "tracks" / "san-diego-lake-murray"
SC = ROOT / "tracks" / "sand-creek-lm"


def test_lake_murray_names_none_of_the_round_keys():
    cfg = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))
    assert "lm_intake" not in cfg                        # the intake never runs on Lake Murray
    plan = json.loads((LM / "source" / "bespoke" / "buildings.plan.json").read_text(encoding="utf-8"))
    assert "lidar" not in plan and "ml_height_check" not in plan
    ship = json.loads((LM / "ship.json").read_text(encoding="utf-8"))
    assert "textures" not in ship["steps"]["gate"]


def test_sand_creek_port_declares_the_round():
    cfg = json.loads((SC / "track.config.json").read_text(encoding="utf-8"))
    assert cfg["lm_intake"]["heightfield"] == "port" and cfg["lm_intake"]["tree_models"] is True
    assert cfg["scenery"]["bespoke"]["blocks"][0]["file"] == "source/bespoke/buildings.lm.json"
    assert cfg["scenery"]["treefx"]["planted"]["file"] == "source/bespoke/trees.lm.json"
    ship = json.loads((SC / "ship.json").read_text(encoding="utf-8"))
    for g in ("houses", "textures"):
        assert g in ship["steps"]["gate"]
    assert "treefx" in ship["steps"]["ship"]
    for a in ship["sync_in"]["assets"]:                  # every texture the rows name is tracked in airoso
        assert (ROOT / a).exists(), a
    for row in cfg["texture_overrides"].values():
        for k, v in row.items():
            if not k.startswith("_") and v.startswith("assets/"):
                assert v in ship["sync_in"]["assets"] or v.startswith("assets/textures/asphalt") or v.startswith("assets/textures/grass"), v


def test_the_port_grid_keeps_every_source_sample():
    import lm_engine_intake as li
    src = li._read_npy(ROOT / "tracks" / "sand-creek" / "data" / "heightfield.npy")
    own = li._read_npy(SC / "data" / "heightfield.npy")
    m = json.loads((SC / "data" / "heightfield.meta.json").read_text(encoding="utf-8"))
    off = round((m["margin_m"] - 150.0) / m["spacing_m"])
    assert off == 8
    assert all(own[j + off][i + off] == src[j][i] for j in range(len(src)) for i in range(len(src[0])))


def test_crowns_reads_one_tree_per_crown_and_none_on_bare_ground():
    from PIL import Image, ImageDraw
    import plan_bespoke_vegetation as pv
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        im = Image.new("RGB", (400, 400), (160, 150, 130))           # a dirt lot
        d = ImageDraw.Draw(im)
        for cx, cy in ((80, 80), (250, 120), (150, 300)):            # three crowns, ~10 m across at ~0.46 m/px
            d.ellipse((cx - 11, cy - 11, cx + 11, cy + 11), fill=(70, 95, 60))
        d.rectangle((300, 300, 380, 380), fill=(120, 124, 110))      # a street: not canopy
        im.save(t / "img.png")
        plan = {"place": "crowns", "image": "img.png", "bbox_lonlat": [-104.0, 39.0, -103.99784, 39.00166],
                "track_box_lonlat": [-104.0, 39.0, -103.99784, 39.00166],
                "rule": {"max_mean": 100, "min_mean": 30, "g_over_r": 1.15, "g_over_b": 1.2, "min_exg": 38},
                "crowns": {"min_crown_m2": 7.0, "smooth_m": 1.2, "min_sep_m": 3.5, "edge_m_min": 0.8, "max_radius_m": 7.0,
                           "wood_cell": 3, "single_cell": 1, "w_over_h": {"3": 0.85, "1": 0.8}},
                "cols": 2, "rows": 2, "out": "trees.json"}
        assert pv.crowns(t, plan) == 0
        pts = json.loads((t / "trees.json").read_text())["points"]
        assert len(pts) == 3
        assert all(p[2] == 1 and 6.0 < p[4] < 14.0 for p in pts)


def test_lidar_roof_helpers():
    import numpy as np
    import lidar_buildings as lb
    sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert lb.shrink(sq, 1)[0] == (1.0, 1.0)
    assert list(lb.pip(sq, np.array([[5, 5], [11, 5], [0.5, 9.5]]))) == [True, False, True]


def test_texture_gate_on_the_spawn_free_road_kn5_shape():
    import verify_textures as vt
    with tempfile.TemporaryDirectory() as t:
        assert vt.main([t]) == 2                          # no config: an input error, never a pass
