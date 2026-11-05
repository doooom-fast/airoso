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


def test_round_b_keys_are_absent_from_lake_murray():
    cfg = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))
    route = cfg.get("route") or {}
    for k in ("connector_hosts", "seat_edge_m"):
        assert k not in route
    assert "lm_pads" not in cfg
    src = (ROOT / "tools" / "seat_terrain_blend.py").read_text(encoding="utf-8")
    assert "SIDEWALK_M = 3.1 " in src                     # the default the absent key keeps


def test_hosts_match_names_pieces_and_prefixes():
    import grid_meetings as gm
    assert gm.host_match("grid_primary_51#0", ["grid_primary*"])
    assert gm.host_match("grid_secondary_8", ["grid_secondary_8"])
    assert not gm.host_match("grid_tertiary_4", ["grid_primary*", "grid_secondary*"])


def test_crowns_take_lidar_heights_before_the_ratio():
    from PIL import Image, ImageDraw
    import plan_bespoke_vegetation as pv
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        im = Image.new("RGB", (200, 200), (160, 150, 130))
        ImageDraw.Draw(im).ellipse((89, 89, 111, 111), fill=(70, 95, 60))
        im.save(t / "img.png")
        plan = {"place": "crowns", "image": "img.png", "bbox_lonlat": [-104.0, 39.0, -103.99892, 39.00083],
                "track_box_lonlat": [-104.0, 39.0, -103.99892, 39.00083],
                "rule": {"max_mean": 100, "min_mean": 30, "g_over_r": 1.15, "g_over_b": 1.2, "min_exg": 38},
                "crowns": {"min_crown_m2": 7.0, "smooth_m": 1.2, "min_sep_m": 3.5, "edge_m_min": 0.8, "max_radius_m": 7.0,
                           "wood_cell": 3, "single_cell": 1, "w_over_h": {"3": 0.85, "1": 0.8}},
                "cols": 2, "rows": 2, "out": "trees.json", "lidar": {"file": "lidar_trees.json"}}
        pv.crowns(t, plan)
        p = json.loads((t / "trees.json").read_text())["points"][0]
        (t / "lidar_trees.json").write_text(json.dumps({"trees": {f"{p[0]:.7f},{p[1]:.7f}": {"h_m": 13.7}}}))
        pv.crowns(t, plan)
        assert json.loads((t / "trees.json").read_text())["points"][0][3] == 13.7


def test_pad_declarations_validate_and_sit_between_their_cuts():
    import draft_pads as dp
    cfg = json.loads((SC / "track.config.json").read_text(encoding="utf-8"))
    pads = dp.declarations({"route": {"draft_pads": cfg["lm_pads"]["pads"] + cfg["lm_pads"].get("parked", [])}})
    assert sorted(p["id"] for p in pads) == sorted(["colorado_50th", "50th_ash", "50th_dahlia", "dahlia_56th",
                                                    "sandcreek_quebec", "48th_colorado"])
    assert all(p.get("_parked_why") for p in cfg["lm_pads"].get("parked", []))     # a parked pad says why
    assert all(p["cuts"][1] <= 3216 and len(p["box"]) >= 4 for p in pads)


def test_round_d_deck_fill_datum_and_smooth():
    """ledger 0079 round D: a hole inside the measured outline takes the plane of the lidar nodes round it (slope kept),
    every node stands datum_m higher, nothing outside the ring is filled, and the smoothing records its moves"""
    import draft_pads as dp
    nx = ny = 21
    deck = {"e0": 0.0, "n0": 0.0, "cell_m": 0.5, "nx": nx, "ny": ny,
            "y": [[0.02 * (i * 0.5) + 0.01 * (j * 0.5) for i in range(nx)] for j in range(ny)]}
    for j in range(8, 12):
        for i in range(8, 12):
            deck["y"][j][i] = None                            # a crosswalk's hole in the middle
    deck["y"][0][0] = None                                    # a hole outside the ring stays one
    ring = [(1.0, 1.0), (9.0, 1.0), (9.0, 9.0), (1.0, 9.0)]
    out, rep = dp.deck_filled(deck, ring, datum_m=0.10)
    assert rep["filled"] == 16 and rep["unfilled"] == 0
    assert abs(out["y"][10][10] - (0.02 * 5 + 0.01 * 5 + 0.10)) < 1e-6   # the plane carried across the hole
    assert out["y"][0][0] is None and abs(out["y"][0][1] - (0.01 + 0.10)) < 1e-9
    _sm, rep2 = dp.deck_filled(deck, ring, datum_m=0.10, smooth_m=1.0)
    assert rep2["smooth_m"] == 1.0 and rep2["smooth_moved_m"]["max"] < 0.05   # a plane barely moves (edges only)
    assert deck["y"][10][10] is None                          # the input is never edited


def test_round_d_keys_are_opt_in():
    """Lake Murray and the Lariat name none of round D's keys; absent = lm_pads and verify_pads as before"""
    lm = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))
    assert "lm_pads" not in lm
    for p in (ROOT / "tracks").glob("lookout-lariat*/track.config.json"):
        assert "deck" not in (json.loads(p.read_text(encoding="utf-8")).get("lm_pads") or {})
    sc = json.loads((SC / "track.config.json").read_text(encoding="utf-8"))
    assert sc["lm_pads"]["deck"]["fill"] == "lidar" and sc["lm_pads"]["deck"]["datum_m"] == 0.10
    ship = json.loads((SC / "ship.json").read_text(encoding="utf-8"))
    assert ship["steps"]["draft"].index("lm_pads") == ship["steps"]["draft"].index("seat_edges") + 1
    assert "verify_pads" in ship["steps"]["gate"]


def test_verify_pads_reads_lm_pads_shape_and_leaves_lake_murrays_alone():
    import verify_pads as vp
    with tempfile.TemporaryDirectory() as td:
        data = Path(td)
        (data / "centerline.local.json").write_text(json.dumps(
            {"origin": {"elev_m": 1500.0}, "points_xyz_m": [[0.0, 10.0, 0.0], [5.0, 10.5, 0.0], [10.0, 11.0, 0.0]]}))
        lm = {"pads": [{"id": "p", "node": 1, "cuts": [0, 2], "outline_en": [[0, -5], [10, -5], [10, 5], [0, 5]],
                        "rows": [[[0, -4, 10.1], [0, 0, 10.1], [0, 4, 10.1]],
                                 [[10, -4, 11.1], [10, 0, 11.1], [10, 4, 11.1]]],
                        "barriers": []}]}
        built, plan = vp.lm_pads_shape(lm, data)
        p = built["pads"][0]
        assert p["curb"] is False and p["stubs"] == [] and p["outline_xz"] == lm["pads"][0]["outline_en"]
        assert p["seams"][0]["xyz"] == [0, 10.1, -4]              # Blender (x, north, up) -> OBJ (x, up, north)
        assert plan["p"]["z_3dep_m"] == 1510.5 and plan["p"]["node_xz"] == [5.0, 0.0]
        assert vp.lm_pads_shape({"pads": [{"id": "x", "seams": [], "outline_xz": [], "stubs": []}]}, data) is None
    lm_built = json.loads((LM / "data" / "pads.built.json").read_text(encoding="utf-8"))
    assert vp.lm_pads_shape(lm_built, LM / "data") is None          # Lake Murray's J2-J4 take the old path
