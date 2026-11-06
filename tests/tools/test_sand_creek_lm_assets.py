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


def test_round_e_dedupe_by_overlap_is_opt_in_and_cross_source():
    """ledger 0079 round E: a Microsoft footprint over half on an OSM one is dropped even with its centroid outside it;
    a same-source neighbour never is; with no overlap key nothing new is dropped (Lake Murray's plan names none)"""
    import plan_buildings as pb
    d = 0.0001
    osm = {"key": "osm1", "src": "OSM", "ring": [[0, 0], [10 * d, 0], [10 * d, 10 * d], [0, 10 * d]]}
    # an L-shaped Microsoft copy: most of it on the OSM square, its centroid pulled outside by a long thin arm
    ms = {"key": "ms1", "src": "Microsoft", "ring": [[0, 0], [10 * d, 0], [10 * d, 10 * d], [0, 10 * d], [0, 10.5 * d],
                                                       [-40 * d, 10.5 * d], [-40 * d, 9.5 * d], [0, 9.5 * d]]}
    twin = {"key": "osm2", "src": "OSM", "ring": [[10 * d, 0], [20 * d, 0], [20 * d, 10 * d], [10 * d, 10 * d]]}
    assert [r["key"] for r in pb.dedupe([dict(osm), dict(twin), dict(ms)])] == ["osm1", "osm2", "ms1"]
    assert [r["key"] for r in pb.dedupe([dict(osm), dict(twin), dict(ms)], 0.5)] == ["osm1", "osm2"]
    lm = json.loads((LM / "source" / "bespoke" / "buildings.plan.json").read_text(encoding="utf-8"))
    assert "dedupe" not in lm
    sc = json.loads((SC / "source" / "bespoke" / "buildings.plan.json").read_text(encoding="utf-8"))
    assert sc["dedupe"]["overlap"] == 0.5


def _street(name, pts, w=8.0):
    return {"name": name, "kind": "connector", "points_xyz_m": [list(p) for p in pts], "widths_m": [w] * len(pts)}


def test_street_junctions_join_and_rank():
    """ledger 0079 0.2.3: route.street_junctions (tools/trim_connectors.py). Two pieces continuing through a node are one
    street (their ends' 0.4 m height step faded out); a third ending there is cut at the joined street's edge with a
    mouth; a fork (17 deg) is never joined; Lake Murray names none of the keys."""
    import trim_connectors as tc
    a = _street("grid_tertiary_1", [(x, 10.0, 0.0) for x in range(-60, 1, 3)])
    b = _street("grid_tertiary_2", [(x, 10.4, 0.0) for x in range(0, 61, 3)])
    c = _street("grid_unclassified_3", [(0.0, 10.2, z) for z in range(0, 61, 3)])
    out, recs = tc.join_street_pieces([a, b, c], 45.0, 135.0)
    assert len(out) == 2 and len(recs) == 1 and recs[0]["rule"] == "straight"
    j = next(p for p in out if p.get("joined"))
    ys = [p[1] for p in j["points_xyz_m"]]
    assert abs(ys[0] - 10.0) < 1e-6 and abs(ys[-1] - 10.4) < 1e-6
    assert max(abs(ys[i + 1] - ys[i]) for i in range(len(ys) - 1)) < 0.05
    mouths = []
    tc.rank_trim(out, mouths, {})
    assert len(mouths) == 1 and mouths[0]["host"] == j["name"] and mouths[0]["connector"] == "grid_unclassified_3"
    assert abs(mouths[0]["cut_xyz"][2] - (4.0 - tc.OVERLAP_M)) < 0.05
    f1 = _street("grid_unclassified_4", [(x, 0.0, 0.0) for x in range(0, 61, 3)])
    f2 = _street("grid_unclassified_5", [(x, 0.0, x * 0.3) for x in range(0, 61, 3)])
    out2, recs2 = tc.join_street_pieces([f1, f2], 45.0, 135.0)
    assert len(out2) == 2 and not recs2
    lm = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))
    assert "street_junctions" not in (lm.get("route") or {})


def test_paint_divided_fork_merges_into_one_measured_street():
    """ledger 0079 0.2.3: route.street_junctions.merge_forks. Two one-way pieces leaving one node (OSM's paint-divided
    approach) become ONE piece: the midline between them, its edges where the measured table puts them (the centre the
    edges' middle, the width their distance), the other pieces untouched."""
    import trim_connectors as tc
    a = _street("grid_tertiary_91", [(x * 0.15, 10.0, -x) for x in range(0, 61, 3)])
    b = _street("grid_tertiary_92", [(-x * 0.15, 10.2, -x) for x in range(0, 61, 3)])
    o = _street("grid_tertiary_36", [(0.0, 10.1, z) for z in range(0, 31, 3)])
    out, recs = tc.merge_forks([a, b, o], [{"pieces": ["grid_tertiary_91", "grid_tertiary_92"], "name": "grid_tertiary_92",
                                            "edges_m": [[0, -7.0, 7.0], [60, -12.0, 10.0]]}])
    assert [c["name"] for c in out] == ["grid_tertiary_36", "grid_tertiary_92"] and len(recs) == 1
    m = out[1]
    assert m["fork_merged"] == ["grid_tertiary_91", "grid_tertiary_92"]
    assert abs(m["widths_m"][0] - 14.0) < 1e-6 and abs(m["widths_m"][-1] - 22.0) < 0.05
    assert abs(m["points_xyz_m"][0][0]) < 1e-6 and abs(m["points_xyz_m"][0][1] - 10.1) < 1e-6
    # going -z, the normal (-dz, dx) points +x: the far end's centre is (-12 + 10) / 2 = -1 m along it
    assert abs(m["points_xyz_m"][-1][0] - (-1.0)) < 0.05


def test_median_crossing_is_kept_and_welded_at_both_ends():
    """ledger 0079 0.2.3: route.street_junctions.median_crossings adds the straight piece between two streets' ends, trim
    keeps it under MIN_PIECE_M (its own min_piece_m 0), and two weld_end passes eased over its whole length (the mouth
    keys weld_blend_m / weld_remap_min_m) leave each end ON its own host deck: the two smoothsteps sum to one."""
    import mouth_weld as mw
    import trim_connectors as tc
    west = _street("grid_unclassified_27", [(x, 20.0, 0.0) for x in range(-60, 1, 3)])
    east = _street("grid_tertiary_65", [(13.5 + x, 20.3, 0.0) for x in range(0, 61, 3)])
    out, recs = tc.median_crossings([west, east], [{"between": ["grid_unclassified_27", "grid_tertiary_65"],
                                                    "name": "x_crossing", "width_m": 10.0}])
    x = out[-1]
    assert recs[0]["length_m"] == 13.5 and x["min_piece_m"] == 0.0 and x["crossing"]
    zs = range(-60, 61, 3)
    hosts = [("h_w", [(0.0, 20.0, float(z)) for z in zs], [9.5] * len(zs)),
             ("h_e", [(13.5, 20.3, float(z)) for z in zs], [9.5] * len(zs))]
    mouths = []
    kept = tc._trim_against([x], hosts, mouths)
    assert len(kept) == 1 and len(mouths) == 2 and kept[0]["min_piece_m"] == 0.0
    assert tc._plan_len(kept[0]["points_xyz_m"]) < tc.MIN_PIECE_M

    def deck(cx, y):
        rows = [((cx + 4.75, y, z), (cx, y, z), (cx - 4.75, y, z)) for z in [-30.0 + 3.0 * i for i in range(21)]]
        return mw.HostDeck(rows, mw.host_window(rows, False, cx, 0.0))
    # the weld on two flat hosts 0.30 m apart: a 4.8 m piece (edge - 0.4 to edge + 0.4) eased from each end over it all
    x0, x1, n = 4.35, 9.15, 5
    ln = {("road", lane): [(x0 + (x1 - x0) * j / (n - 1), 20.15, o) for j in range(n)]
          for lane, o in ((0, 5.0), (1, 0.0), (2, -5.0))}
    inset = {k: mw.OVERLAP_M for k in ln}
    h = {k: 0.0 for k in ln}
    ra = mw.weld_end(ln, deck(0.0, 20.0), -1, inset, h, blend_m=x1 - x0, remap_min=0.0)
    back = {k: v[::-1] for k, v in ra["new"].items()}
    rb = mw.weld_end(back, deck(13.5, 20.3), 1, inset, h, blend_m=x1 - x0, remap_min=0.0)
    fin = {k: v[::-1] for k, v in rb["new"].items()}
    for k in fin:
        assert abs(fin[k][0][1] - 20.0) < 0.01, fin[k][0]
        assert abs(fin[k][-1][1] - 20.3) < 1e-6, fin[k][-1]
        ys = [q[1] for q in fin[k]]
        assert all(b_ >= a_ - 1e-9 for a_, b_ in zip(ys, ys[1:]))      # one climb from deck to deck, no bump


def test_acute_weld_holds_the_overlap_on_the_host_deck():
    """ledger 0079 0.2.3: mouth_weld.weld_end(hold_overlap=True), an acute meeting (20 deg) on a host steeper than the
    guest: every guest road vertex inside the host's pavement ends within SELF_TOL_M of the host deck, which the plain
    30 m ease from each line's own mitre does not do."""
    import math as m_
    import mouth_weld as mw
    rows = [((x, 10.0 + 0.03 * x, 5.0), (x, 10.0 + 0.03 * x, 0.0), (x, 10.0 + 0.03 * x, -5.0))
            for x in [-90.0 + 3.0 * i for i in range(61)]]
    dk = mw.HostDeck(rows, mw.host_window(rows, False, 0.0, 5.0))
    a = m_.radians(20.0)
    d, nrm = (m_.cos(a), m_.sin(a)), (-m_.sin(a), m_.cos(a))
    ln = {("road", 0): [], ("road", 1): [], ("road", 2): []}
    for j in range(30):
        u = 2.0 * j
        cx, cz = d[0] * u, 4.6 + d[1] * u
        for lane, o in ((0, 5.0), (1, 0.0), (2, -5.0)):
            ln[("road", lane)].append((cx + nrm[0] * o, 10.0 + 0.01 * u, cz + nrm[1] * o))
    inset = {k: mw.OVERLAP_M for k in ln}
    h = {k: 0.0 for k in ln}

    def worst(res):
        w = 0.0
        for pts in res["new"].values():
            for q in pts:
                if dk.inside(q[0], q[2], 0.01):
                    w = max(w, q[1] - dk.at(q[0], q[2]))
        return w
    plain = mw.weld_end(ln, dk, 1, inset, h, extend_max=60.0)
    held = mw.weld_end(ln, dk, 1, inset, h, extend_max=60.0, hold_overlap=True)
    assert worst(held) <= mw.SELF_TOL_M, worst(held)
    assert worst(plain) > worst(held)


def test_seam_offset_multi_is_exact_on_every_row_and_seam_offset_alone():
    """ledger 0079 0.2.3: draft_pads.seam_offset_multi (lm_pads.arms streets). On each row its own departure exactly;
    with one row, seam_offset's value."""
    import draft_pads as dp
    c1 = {"p": (0.0, 0.0), "n": (0.0, 1.0)}
    c2 = {"p": (0.0, 10.0), "n": (0.0, -1.0)}
    p1 = {"c": c1, "u": (-1.0, 0.0), "t": [-5.0, 5.0], "r": [0.2, 0.2], "fade": 12.0}
    p2 = {"c": c2, "u": (1.0, 0.0), "t": [-5.0, 5.0], "r": [-0.1, -0.1], "fade": 12.0, "lateral": True}
    assert abs(dp.seam_offset_multi([p1, p2], 0.0, 0.0) - 0.2) < 1e-9
    assert abs(dp.seam_offset_multi([p1, p2], 0.0, 10.0) + 0.1) < 1e-9
    for y in (0.5, 3.0, 7.0, 11.9):
        assert abs(dp.seam_offset_multi([p1], 1.0, y) - dp.seam_offset([p1], 1.0, y)) < 1e-12
    assert -0.1 < dp.seam_offset_multi([p1, p2], 0.0, 5.0) < 0.2


def test_round_g_keys_are_opt_in():
    """ledger 0079 0.2.3 round G: Lake Murray and the Lariat name none of the new keys"""
    for t in ("san-diego-lake-murray", "lookout-lariat"):
        p = ROOT / "tracks" / t / "track.config.json"
        if not p.exists():
            continue
        cfg = json.loads(p.read_text(encoding="utf-8"))
        sj = (cfg.get("route") or {}).get("street_junctions") or {}
        assert not {"merge_forks", "median_crossings", "weld_hold"} & set(sj)
        assert "arms" not in (cfg.get("lm_pads") or {})


def test_weld_runon_reads_the_deck_at_the_mitre_not_a_far_projection():
    """ledger 0079 round H: mouth_weld.weld_end(runon_at_mitre=True). A host whose deck reads 0.4 m lower for any point
    more than 12 m out (the projection onto another leg of a cornering lap): the plain warp carries that drop into the
    guest's rows 12-30 m out; the run-on from the mitre's own deck does not, and the end row is unchanged."""
    import mouth_weld as mw

    class Deck:
        def at(self, x, z):
            return 10.0 if z < 12.0 else 9.6

        def edge_gap(self, x, z, side, inset):
            return z - (5.0 - inset)

    ln = {("road", lane): [(o, 10.0, 4.6 + 2.0 * j) for j in range(30)] for lane, o in ((0, -5.0), (1, 0.0), (2, 5.0))}
    inset = {k: mw.OVERLAP_M for k in ln}
    h = {k: 0.0 for k in ln}
    plain = mw.weld_end(ln, Deck(), 1, inset, h)
    run = mw.weld_end(ln, Deck(), 1, inset, h, runon_at_mitre=True)
    for k in ln:
        assert abs(plain["new"][k][0][1] - run["new"][k][0][1]) < 1e-9
        assert max(abs(q[1] - 10.0) for q in run["new"][k]) < 1e-9
        assert min(q[1] for q in plain["new"][k]) < 9.95


def test_round_h_keys_are_opt_in():
    """ledger 0079 round H: Lake Murray and the Lariat name none of the new keys"""
    for t in ("san-diego-lake-murray", "lookout-lariat"):
        p = ROOT / "tracks" / t / "track.config.json"
        if not p.exists():
            continue
        cfg = json.loads(p.read_text(encoding="utf-8"))
        r = cfg.get("route") or {}
        assert "weld_runon" not in (r.get("street_junctions") or {})
        assert "weld_exact_deck_lines" not in r
        assert "verify_mouths_allowed" not in r
        assert "connector_widths" not in (cfg.get("lm_intake") or {})
        assert "connector_profiles" not in (cfg.get("lm_intake") or {})
        for g in ((cfg.get("scenery") or {}).get("bespoke") or {}).get("blocks") or []:
            assert "building_clear_m" not in g


def test_intake_applies_a_measured_connector_profile_and_refuses_other_points():
    """ledger 0079 round H: lm_intake.connector_profiles replaces the named streets' heights point by point, and stops
    when the profile was measured on other points"""
    import lm_engine_intake as li
    src = {"connectors": [{"name": "a", "kind": "connector", "points_xyz_m": [[0.0, 1.0, 0.0], [3.0, 1.0, 0.0]],
                           "widths_m": [8.0, 8.0]}]}
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "data"
        d.mkdir()
        (d / "connectors.local.json").write_text(json.dumps(src), encoding="utf-8")
        prof = {"connectors": {"a": {"xz": [[0.0, 0.0], [3.0, 0.0]], "y": [2.0, 2.5]}}}
        (Path(td) / "p.json").write_text(json.dumps(prof), encoding="utf-8")
        li.apply_connector_profiles(Path(td), "p.json")
        out = json.loads((d / "connectors.local.json").read_text(encoding="utf-8"))["connectors"][0]["points_xyz_m"]
        assert [p[1] for p in out] == [2.0, 2.5]
        prof["connectors"]["a"]["xz"][0] = [0.0, 0.5]
        (Path(td) / "p.json").write_text(json.dumps(prof), encoding="utf-8")
        try:
            li.apply_connector_profiles(Path(td), "p.json")
            raise AssertionError("a profile measured on other points was applied")
        except SystemExit:
            pass


def test_round_i_keys_are_opt_in():
    """ledger 0079 round I: Lake Murray and the Lariat name none of the new keys or steps (the islands on a street's built
    road, the lidar ground patches)"""
    for t in ("san-diego-lake-murray", "lookout-lariat"):
        p = ROOT / "tracks" / t / "track.config.json"
        if not p.exists():
            continue
        cfg = json.loads(p.read_text(encoding="utf-8"))
        assert "islands" not in (cfg.get("route") or {})
        assert "lidar_patches" not in (cfg.get("terrain") or {})
        assert "lidar_patches_file" not in (cfg.get("terrain") or {})
        sp = ROOT / "tracks" / t / "ship.json"
        if sp.exists():
            draft = json.loads(sp.read_text(encoding="utf-8")).get("steps", {}).get("draft") or []
            assert "islands" not in draft and "ground_patch" not in draft


def test_sand_creek_round_i_declares_the_island_and_the_patch():
    """ledger 0079 round I: the island's rows run end to end with edge A west of edge B, its rise is the measured one and
    flush on the east; the patch's polygon is closed by the wall's hard edges and the measured file is the config's"""
    cfg = json.loads((SC / "track.config.json").read_text(encoding="utf-8"))
    isl = cfg["route"]["islands"][0]
    assert isl["id"] == "fork_92" and len(isl["rows"]) >= 2
    assert all(r[0] < r[2] for r in isl["rows"])
    assert isl["rise_m"][1] == 0.0 and 0.0 < isl["rise_m"][0] < 0.10
    p = cfg["terrain"]["lidar_patches"][0]
    meas = json.loads((SC / cfg["terrain"]["lidar_patches_file"]).read_text(encoding="utf-8"))["patches"][p["id"]]
    assert meas["polygon"] == p["polygon"]
    assert len(meas["y"]) == meas["nx"] * meas["nz"]
    assert all(1 <= k < len(p["polygon"]) for k in p["hard_edges"])


def test_lidar_ground_patch_point_in_polygon():
    import lidar_ground_patch as lgp
    sq = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert lgp.point_in(sq, 5.0, 5.0) and not lgp.point_in(sq, 11.0, 5.0) and not lgp.point_in(sq, 5.0, -1.0)


def test_lidar_profile_surface_keeps_a_street_under_a_bridge_on_its_ground():
    """ledger 0079 round I (--surface): under an overhead deck (deck returns 7 m up, the ground under it unseen at some
    points) the street stays on its ground; a street climbing onto a deck by its ramps stays on the deck"""
    import numpy as np
    import lidar_connector_profile as lcp

    def fake(ground, deck):
        E, N, Z, C = [], [], [], []
        for k, (g, d) in enumerate(zip(ground, deck)):
            for dx in (-0.3, 0.0, 0.3):
                if g is not None:
                    E.append(k * 3.0 + dx); N.append(0.0); Z.append(g); C.append(2)
                if d is not None:
                    E.append(k * 3.0 + dx); N.append(0.1); Z.append(d); C.append(17)

        class T:
            def tile(self, i, j):
                return np.array(E), np.array(N), np.array(Z), np.array(C)
        return T()
    pts = [(k * 3.0, 0.0, 0.0) for k in range(10)]
    under = fake([1.0, 1.0, 1.0, None, None, 1.0, None, 1.0, 1.0, 1.0],
                 [None, None, 8.0, 8.0, 8.0, 8.0, 8.0, 8.0, None, None])
    ys = [m[0] for m in lcp.profile(under, pts, surface=True)]
    assert all(y is None or abs(y - 1.0) < 1e-9 for y in ys)
    ramp = [1.0, 2.0, 3.0, 4.0, 5.0, 5.0, 4.0, 3.0, 2.0, 1.0]
    on = fake([1.0, 2.0, 3.0, 4.0, None, None, 4.0, 3.0, 2.0, 1.0], [None, None, None, None, 5.0, 5.0, None, None, None, None])
    ys = [m[0] for m in lcp.profile(on, pts, surface=True)]
    assert ys == ramp
