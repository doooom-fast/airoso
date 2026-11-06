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


def test_round_j_keys_are_opt_in():
    """ledger 0079 round J: Lake Murray and the Lariat name none of the new keys (the weld's deck past a host's open end;
    the round I lidar profile file)"""
    for t in ("san-diego-lake-murray", "lookout-lariat"):
        p = ROOT / "tracks" / t / "track.config.json"
        if not p.exists():
            continue
        cfg = json.loads(p.read_text(encoding="utf-8"))
        assert "weld_deck_beyond_end" not in (cfg.get("route") or {})
        assert "round_i" not in str((cfg.get("lm_intake") or {}).get("connector_profiles") or "")


def test_weld_deck_beyond_end_reads_the_street_under_the_rows():
    """ledger 0079 round J (mouth_weld.BeyondEndDeck): a host street running north from z 0 (its open start welded onto
    a third street along z 0, which falls 0.01 m per m east); a point past the host's start on the third street reads the
    third street's deck, a point on the host reads the host's, and a point past the start but off the third street reads
    the host's end row held level, as before"""
    import mouth_weld as mw
    host = [((x - 5.0, 10.0, z), (x, 10.0, z), (x + 5.0, 10.0, z)) for x, z in ((0.0, 3.0 * j) for j in range(10))]
    third = [((x, 10.0 - 0.01 * x, 5.0), (x, 10.0 - 0.01 * x, 0.0), (x, 10.0 - 0.01 * x, -5.0))
             for x in (-30.0 + 3.0 * j for j in range(21))]
    base = mw.HostDeck(host, list(range(len(host))))
    d3 = mw.ExactHostDeck(third, list(range(len(third))))
    deck = mw.BeyondEndDeck(base, [d3], open_start=True, open_end=False)
    assert abs(deck.at(2.0, -2.0) - (10.0 - 0.02)) < 1e-6        # past the host's start, on the third street
    assert abs(deck.at(2.0, 6.0) - 10.0) < 1e-9                  # on the host
    assert abs(deck.at(2.0, -9.0) - 10.0) < 1e-9                 # past the start, off the third street: as before
    assert deck.hits == 1
    shut = mw.BeyondEndDeck(base, [d3], open_start=False, open_end=False)
    assert abs(shut.at(2.0, -2.0) - 10.0) < 1e-9


def test_naip_edge_road_runs_close_paint_and_keep_the_carriageway():
    """ledger 0079 round J (tools/naip_edge.road_runs): a 0.5 m lane line (bright) and a car shadow (dark) inside an
    asphalt run are closed over; the verge (dark) beyond 1 m ends it; a run under 3 m is not a carriageway"""
    import naip_edge as ne
    lat = [-10.0 + 0.5 * k for k in range(41)]
    gray = []
    for l in lat:
        if -6.0 <= l <= 6.0:
            gray.append(230.0 if abs(l - 1.0) < 0.3 else (90.0 if abs(l + 3.0) < 0.3 else 170.0))
        elif 8.0 <= l <= 9.0:
            gray.append(170.0)
        else:
            gray.append(110.0)
    runs = ne.road_runs(lat, gray)
    assert runs == [(-6.25, 6.25)]
    out = ne.trace_section(lat, gray, [None] * len(lat), 0.0)
    assert out["run"] == [-6.25, 6.25] and out["left"]["kind"] == "no_step"


def test_round_k_keys_are_opt_in():
    """ledger 0079 round K: Lake Murray, the Lariat and the circuits name none of the new keys (race.edge_fold_chord,
    race.spawn_gate_layouts, race.seat_on_pads, kerb.race_rule, kerb.surface, signs_name_blades)"""
    for t in ("san-diego-lake-murray", "lookout-lariat", "lookout-lariat-lm", "high-plains-lm", "aspen-lm", "pueblo-lm"):
        p = ROOT / "tracks" / t / "track.config.json"
        if not p.exists():
            continue
        cfg = json.loads(p.read_text(encoding="utf-8"))
        race, kerb = cfg.get("race") or {}, cfg.get("kerb") or {}
        for k in ("edge_fold_chord", "spawn_gate_layouts", "seat_on_pads"):
            assert k not in race, (t, k)
        assert "race_rule" not in kerb and "surface" not in kerb, t
        assert "signs_name_blades" not in cfg, t
    # round K's candidate (not live: its race layout is red on the race gates and on verify_kn5, ledger 0079 round K)
    live = json.loads((SC / "track.config.json").read_text(encoding="utf-8"))
    assert "race_rule" not in (live.get("kerb") or {}) and "signs_name_blades" not in live
    sc = json.loads((SC / "source" / "round_k" / "track.config.json").read_text(encoding="utf-8"))
    assert sc["version"] == "0.2.6"
    assert sc["race"]["edge_fold_chord"] is True
    # round L (call 2): Lake Murray's race-furniture kerbs, nothing dropped; the circuit kerb keys gone from the candidate
    assert "race_rule" not in sc["kerb"] and "surface" not in sc["kerb"]
    trims = sc["race"]["kerbs"]["trims"]
    assert not any(t.get("drop") for t in trims) and {(t["apex"], t["kind"]) for t in trims} == \
        {(3195, "outside"), (3205, "outside")}
    race = [l for l in sc["layouts"] if l["id"] == "race"][0]
    street = [l for l in sc["layouts"] if l["id"] == "street"][0]
    assert race["race_furniture"] is True and race["closure_token"] == "race"
    assert street["race_furniture"] is False and street["start"]["offset_right_m"] == 1.9


def _rounded_square_lap(half=100.0, R=15.0, step=2.0):
    """an anticlockwise rounded square (x = E, z = N): four left corners of radius R"""
    import math
    pts = []
    c = half - R
    centres = [(c, -c), (c, c), (-c, c), (-c, -c)]
    for q, (cx, cz) in enumerate(centres):
        a0 = -math.pi / 2 + q * math.pi / 2                       # the arc starts heading along +x rotated by q
        for k in range(0, 46):
            t = a0 + math.radians(90.0 * k / 45)
            pts.append((cx + R * math.cos(t), 0.0, cz + R * math.sin(t)))
        ex, ez = pts[-1][0], pts[-1][2]
        dx, dz = -math.sin(a0 + math.pi / 2), math.cos(a0 + math.pi / 2)   # the straight's heading
        n = int(2 * c / step)
        for s in range(1, n):
            pts.append((ex + dx * s * step, 0.0, ez + dz * s * step))
    pts.append(pts[0])
    return pts


def test_race_kerbs_rule_apex_and_exit_on_a_rounded_square():
    """tools/race_kerbs.py: an anticlockwise rounded square (four left corners of R 15 m): each corner gets the inside
    kerb PC..PT on the left edge and the outside kerb apex..PT + clamp(2 R, 10, 30) m on the right, on the lane"""
    import race_kerbs as rk
    pts = _rounded_square_lap()
    cl = {"points_xyz_m": [list(p) for p in pts], "widths_m": [10.0] * len(pts), "origin": {"lon": -104.9, "lat": 39.8}}
    rec = rk.rule({"kerb": {"width_m": 1.4, "race_rule": {"min_turn_deg": 45}}}, cl)
    assert len(rec["corners"]) == 4 and all(c["D_deg"] > 0 for c in rec["corners"])
    kinds = [(k["side"], tuple(k["rule"]["kind"])) for k in rec["kerbs"]]
    assert kinds.count(("left", ("apex",))) == 4 and kinds.count(("right", ("exit",))) == 4
    assert not rec["dropped"]
    for k in rec["kerbs"]:
        assert k["in_m"] == -1.4 and k["out_m"] == 0.0 and k["edge"] == "ribbon"


def test_name_blades_abbreviate_per_mutcd_1a15():
    import name_blades as nb
    assert nb.abbreviate("North Colorado Boulevard") == "N Colorado Blvd"
    assert nb.abbreviate("East 45th Avenue") == "E 45th Ave"
    assert nb.abbreviate("Sand Creek Drive South") == "Sand Creek Dr S"
    assert nb.abbreviate("North Northfield Quebec Street") == "N Northfield Quebec St"


def test_name_blades_plan_is_committed_and_fits_its_atlas():
    plan = json.loads((SC / "source" / "name_blades.json").read_text(encoding="utf-8"))
    rows = plan["atlas"]["rows"]
    assert plan["mutcd"]["blade_h_in"] == 12.0 and plan["mutcd"]["cap_in"] == 6.0
    assert (SC / "textures" / plan["atlas"]["file"]).exists()
    for p in plan["posts"]:
        assert p["lap_name"] in rows and p["cross_name"] in rows and p["lap_name"] != p["cross_name"]
        assert p["side"] in ("L", "R")
    for r in rows.values():
        assert 0.0 <= r["u"][0] < r["u"][1] <= 1.0 and 0.0 <= r["v"][0] < r["v"][1] <= 1.0
        assert r["length_in"] % 6.0 == 0.0


def test_edge_fold_chord_is_opt_in():
    """race_furniture: the chord fallback is off unless the declaration carries params.edge_fold_chord"""
    import race_furniture as rf
    assert "chord" in rf._trim_folds.__code__.co_varnames
    assert rf.trim_folded_rings.__defaults__[-1] is False
    assert rf.edge_fold_corners.__defaults__[-1] is False


def test_round_l_pad_decks_opt_in():
    """ledger 0079 round L (call 5): defaults.pad_decks is opt-in (absent from DEFAULTS, so a signs.json naming none
    writes the record it wrote before); only Sand Creek's names it, with its three pad corners per_layout; Lake
    Murray's pads.built.json (outline_xz) and lm_pads' (outline_en) read the same way"""
    import place_signs as ps
    import expansion_lines as el
    assert "pad_decks" not in ps.DEFAULTS and ps.OPT_IN_DEFAULTS == {"pad_decks": False}
    for t in ("san-diego-lake-murray", "lookout-lariat", "lookout-lariat-lm"):
        p = ROOT / "tracks" / t / "signs.json"
        if p.exists():
            assert "pad_decks" not in (json.loads(p.read_text(encoding="utf-8")).get("defaults") or {}), t
    sg = json.loads((SC / "signs.json").read_text(encoding="utf-8"))
    assert sg["defaults"]["pad_decks"] is True
    assert {c: sg["corners"][c]["vertex"] for c in ("SC-C50", "SC-ASH", "SC-DAH")} == \
        {"SC-C50": 140, "SC-ASH": 186, "SC-DAH": 410}
    assert all(sg["corners"][c]["per_layout"] is True for c in ("SC-C50", "SC-ASH", "SC-DAH"))
    try:
        ps.validate_overrides({"pad_decks": "yes"}, {})
    except ps.SignsConfigError:
        pass
    else:
        raise AssertionError("a non-bool pad_decks must be refused")
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "data").mkdir()
        ring = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0]]
        for key in ("outline_xz", "outline_en"):
            (Path(td) / "data" / "pads.built.json").write_text(json.dumps({"pads": [{"id": "p", key: ring}]}))
            assert el.pad_polygons(td) == [("p", [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)], [])], key


def test_round_m_keys_are_opt_in():
    """ledger 0079 round M: race.pad_corners and drive_test.dense_hops are opt-in — Lake Murray, the Lariat and the
    circuits name neither; only Sand Creek's parked candidate names them. Without a declaration the strip trims what it
    trimmed before; with one, the strip runs in_vertex -> X -> out_vertex (kind pad_corner, the vertices between removed)"""
    import race_furniture as rf
    for t in ("san-diego-lake-murray", "lookout-lariat", "lookout-lariat-lm", "high-plains-lm", "aspen-lm", "pueblo-lm"):
        p = ROOT / "tracks" / t / "track.config.json"
        if not p.exists():
            continue
        cfg = json.loads(p.read_text(encoding="utf-8"))
        assert "pad_corners" not in (cfg.get("race") or {}), t
        assert "dense_hops" not in (cfg.get("drive_test") or {}), t
    live = json.loads((SC / "track.config.json").read_text(encoding="utf-8"))
    assert "pad_corners" not in (live.get("race") or {}) and "dense_hops" not in (live.get("drive_test") or {})
    sc = json.loads((SC / "source" / "round_k" / "track.config.json").read_text(encoding="utf-8"))
    assert [(c["pad"], c["side"], c["in_vertex"], c["out_vertex"]) for c in sc["race"]["pad_corners"]] == \
        [("50th_ash", "R", 185, 190), ("50th_dahlia", "L", 410, 415)]
    assert sc["drive_test"]["dense_hops"] is True
    # a lap with a long straight edge (x = E, the left strip at z = +4.515): no fold there, so no corner unless declared
    pts = [(2.0 * k, 0.0, 0.0) for k in range(40)] + [(78.0, 0.0, -20.0), (40.0, 0.0, -30.0), (0.0, 0.0, -20.0)]
    pts.append(pts[0])
    widths, ei = [10.0] * len(pts), [0.82] * len(pts)
    base = rf.edge_fold_corners(pts, widths, ei)
    X = (14.0, 5.5)
    decl = [{"side": "L", "in_vertex": 5, "out_vertex": 9, "xz": list(X), "kind": "pad_corner"}]
    got = rf.edge_fold_corners(pts, widths, ei, declared=decl)
    new = [c for c in got if c not in base]
    assert len(new) == 1 and new[0]["kind"] == "pad_corner" and new[0]["side"] == "L"
    assert (new[0]["in_vertex"], new[0]["out_vertex"]) == (5, 9) and new[0]["removed"] == [6, 7, 8]
    assert tuple(new[0]["xz"]) == X
    assert rf.declared_corners({"params": {}}, "L") == [] and rf.declared_corners({"params": {"pad_corners": decl}}, "R") == []


def test_round_n_fold_chords_are_opt_in():
    """ledger 0079 round N: fold_fans.chords is opt-in — no track config names it (Lake Murray, the Lariat, the circuits,
    Sand Creek's live config and its candidate: the S's chord fails verify_fold_fans (5) at the parked 48th_colorado,
    so it is not adopted). Without it pinches_from / fold_fan_discs return what they did; with it a road cut no
    levelled pinch covers is surveyed as a chord (no X), and drive_test's discs take it beside the levelled pinches"""
    import verify_fold_fans as vf
    from scripts.geometry.drive_test import fold_fan_discs
    for t in ("san-diego-lake-murray", "lookout-lariat", "lookout-lariat-lm", "high-plains-lm", "aspen-lm", "pueblo-lm",
              "sand-creek-lm"):
        p = ROOT / "tracks" / t / "track.config.json"
        if p.exists():
            assert "fold_fans" not in json.loads(p.read_text(encoding="utf-8")), t
    sc = json.loads((SC / "source" / "round_k" / "track.config.json").read_text(encoding="utf-8"))
    # round P: the candidate takes them, with (7) on no_route's deck frame, once the S passes on 48th_colorado's deck
    assert {k: v for k, v in sc["fold_fans"].items() if not k.startswith("_")} == {"chords": True,
                                                                                  "wall_frame": "local_deck"}
    assert sc["drive_test"]["fold_fan_severe"] == "verify_fold_fans"
    gate = json.loads((SC / "source" / "round_k" / "ship.json").read_text(encoding="utf-8"))["steps"]["gate"]
    assert gate.index("fold_fans") == gate.index("race_gates") + 1
    # a straight 50-row line, 12 m wide; one levelled road pinch (20..22) and one road chord (35..37)
    pts = [(0.0, 0.0, float(z)) for z in range(50)]
    w = [12.0] * 50
    lev = {"line": ["road", 2], "k": 20, "l": 22, "X": [-6.0, 0.1, 21.0], "y_k": 0.1, "y_l": 0.1}
    welds = {"folds": {"MAINLINE": {"cuts": [["road", 2, 20, 22], ["road", 2, 35, 37]], "levelled": [lev],
                                    "rows": 50, "level_rows": 2}}}
    pins, B = vf.pinches_from(welds, pts, w, False)
    assert [(p["k"], p["l"]) for p in pins] == [(20, 22)] and B == 2
    assert vf.pinches_from(welds, pts, w, False, chords=False) == (pins, B)
    got, _ = vf.pinches_from(welds, pts, w, False, chords=True)
    assert [(p["k"], p["l"], p.get("chord", False)) for p in got] == [(20, 22, False), (35, 37, True)]
    assert got[1]["X"] is None and len(got[1]["ref"]) == 3
    base = fold_fan_discs(welds, pts, w)
    assert sorted({round(d[1]) for d in base}) == list(range(18, 26))
    both = fold_fan_discs(welds, pts, w, chords=True)
    assert sorted({round(d[1]) for d in both}) == list(range(18, 26)) + list(range(33, 41))


def test_round_n_paint_is_opt_in():
    """ledger 0079 round N: route.paint (tools/author_paint_blend.py, draft step paint) is named only by Sand Creek's
    candidate: Lake Murray, the Lariat, the circuits and the live 0.2.5 config name none (the step is then a no-op)"""
    for t in ("san-diego-lake-murray", "lookout-lariat", "lookout-lariat-lm", "high-plains-lm", "aspen-lm", "pueblo-lm",
              "sand-creek-lm"):
        p = ROOT / "tracks" / t / "track.config.json"
        if p.exists():
            assert "paint" not in (json.loads(p.read_text(encoding="utf-8")).get("route") or {}), t
    sc = json.loads((SC / "source" / "round_k" / "track.config.json").read_text(encoding="utf-8"))
    (item,) = sc["route"]["paint"]
    assert item["id"] == "fork_95_median" and len(item["lines"]) == 2 and len(item["clear"]) == 4
    assert all(l["color"] == "yellow" and l["w"] == 0.12 and l["double_gap_m"] == 0.06 for l in item["lines"])
    ship = json.loads((SC / "source" / "round_k" / "ship.json").read_text(encoding="utf-8"))["steps"]["draft"]
    assert ship.index("paint") == ship.index("islands") + 1
    assert "draft_paint()" in (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")


def test_round_o_cut_reach_arm_is_opt_in():
    """ledger 0079 round O: a lap cut drawn across the lap's own arm only (draft_pads.arm_reach, a pad's cut_reach
    "arm"), declared by 48th_colorado alone; its measurement records the ends lm_pads reads. Without the key every pad's
    cut is +-CUT_HALF_M, as before. The walk crosses a gap under ARM_GAP_M and stops at a longer one, ARM_MARGIN_M on"""
    import draft_pads as dp
    for t in ("san-diego-lake-murray", "lookout-lariat", "lookout-lariat-lm", "sand-creek-lm"):
        p = ROOT / "tracks" / t / "track.config.json"
        if p.exists():
            assert '"cut_reach"' not in p.read_text(encoding="utf-8"), t
    sc = json.loads((SC / "source" / "round_k" / "track.config.json").read_text(encoding="utf-8"))
    # round P unparks 48th_colorado (build rp1: verify_pads x4 PASS with seam_base) and drops 52's allowed mouth row
    decls = sc["lm_pads"]["pads"] + sc["lm_pads"]["parked"]
    assert [p["id"] for p in decls if p.get("cut_reach")] == ["48th_colorado"]
    assert "48th_colorado" in [p["id"] for p in sc["lm_pads"]["pads"]]
    assert all(not p.get("_parked_why") for p in sc["lm_pads"]["pads"])
    # round Q drops grid_primary_78's row (it passes on rp1 / rp2); grid_primary_80's is the mouth on E 56th (v847)
    assert [r["piece"] for r in sc["route"]["verify_mouths_allowed"]] == ["grid_primary_80#0"]
    sk = json.loads((SC / "signs.json").read_text(encoding="utf-8"))["corners"]["SC-48S"]
    assert sk["skip"] is True and "rev" in sk["reason"] and "fwd" in sk["reason"]
    for f in (SC / "source" / "pads").glob("*.json"):
        rec = json.loads(f.read_text(encoding="utf-8"))
        assert ("cut_ends_en" in rec) == (f.stem == "48th_colorado"), f.stem
        assert ("deck_class2" in rec) == (f.stem == "48th_colorado"), f.stem
    p48 = next(p for p in decls if p["id"] == "48th_colorado")
    assert (p48["seam"], p48["deck_beyond"]) == ("row", "class2")
    assert all("deck_beyond" not in p for p in decls if p["id"] != "48th_colorado")
    # a lap at x = 0 heading +z; asphalt |x| <= 5 with a 0.5 m paint gap at x 2.0..2.5, a 3 m median 5..8, road past it
    pts = [(0.0, 0.0, float(z)) for z in range(10)]
    c = dp.lap_cut(pts, 2, 5)
    assert abs(abs(c["a"][0]) - dp.CUT_HALF_M) < 1e-9

    def paved(x, y):
        return (abs(x) <= 5.0 and not 2.0 < x < 2.5) or abs(x) >= 8.0
    r = dp.arm_reach(c, paved)
    assert r["reach_m"] == [5.0 + dp.ARM_MARGIN_M] * 2
    assert sorted(round(abs(q[0]), 6) for q in (r["a"], r["b"])) == [6.0, 6.0]
    assert r["p"] == c["p"] and r["n"] == c["n"] and abs(c["a"][0]) == dp.CUT_HALF_M
    assert dp.arm_reach(c, lambda x, y: True)["reach_m"] == [dp.CUT_HALF_M, dp.CUT_HALF_M]
    # seam "row" beside street arms (seam_offset_multi): behind a lap row's line, past its ends, the row's departure no
    # longer applies in full; without near_row (every pad but 48th_colorado) the reading is as before
    row = [(-5.0, 2.0, 1.0), (0.0, 2.0, 1.0), (5.0, 2.0, 1.0)]
    prof = dp.seam_profile([(c, row)], lambda x, y: 0.8)
    prof[0]["fade"] = 12.0
    behind_past = (-20.0, -3.0)
    assert abs(dp.seam_offset_multi(prof, *behind_past) - 0.2) < 1e-9
    prof[0]["near_row"] = True
    assert dp.seam_offset_multi(prof, *behind_past) == 0.0
    assert abs(dp.seam_offset_multi(prof, 0.0, 2.0) - 0.2) < 1e-9
    assert dp.seam_offset_multi(prof, 0.0, 2.0) == dp.seam_offset(prof, 0.0, 2.0)
    # deck_beyond "class2": a road-less node inside the ring takes the class-2 plane before the plane fill; without the
    # grid deck_filled is as before; outside the ring nothing changes here
    Y = [[1.0] * 5 for _ in range(5)]
    Y[2][2] = None
    Y[0][4] = None
    deck = {"e0": 0.0, "n0": 0.0, "cell_m": 0.5, "nx": 5, "ny": 5, "y": Y}
    ring = [(0.6, 0.6), (1.4, 0.6), (1.4, 1.4), (0.6, 1.4)]
    c2 = {"y": [[None] * 5 for _ in range(5)]}
    c2["y"][2][2], c2["y"][0][4] = 0.7, 0.7
    old, rep_old = dp.deck_filled(deck, ring, 0.1)
    new, rep_new = dp.deck_filled(deck, ring, 0.1, class2=c2)
    assert "class2_nodes" not in rep_old and rep_new["class2_nodes"] == 1
    assert abs(new["y"][2][2] - 0.8) < 1e-9 and new["y"][0][4] is None and old["y"][0][4] is None
    assert dp.deck_filled(deck, ring, 0.1, class2=None) == (old, rep_old)


def test_round_p_wall_frame_and_vertex_kinks_are_opt_in():
    """ledger 0079 round P: verify_fold_fans' fold_fans.wall_frame "local_deck" ((7) reads no_route's deck frame too) and
    drive_test's drive_test.vertex_kinks (a kink re-measured on the wheel path's own travel) are named by no live config
    (Lake Murray, the Lariat, the circuits, Sand Creek 0.2.5); only Sand Creek's candidate may name them. all_at reads
    every sheet at a point; the own-travel kink of a constant grade read across a vertex creep is 0"""
    import verify_fold_fans as vf
    from scripts.geometry.drive_test import _own_travel_step, KINK_PCT, STEP_M
    for t in ("san-diego-lake-murray", "lookout-lariat", "lookout-lariat-lm", "high-plains-lm", "aspen-lm", "pueblo-lm",
              "sand-creek-lm"):
        p = ROOT / "tracks" / t / "track.config.json"
        if p.exists():
            c = json.loads(p.read_text(encoding="utf-8"))
            assert "wall_frame" not in (c.get("fold_fans") or {}), t
            assert "vertex_kinks" not in (c.get("drive_test") or {}), t
    sc = json.loads((SC / "source" / "round_k" / "track.config.json").read_text(encoding="utf-8"))
    assert sc["fold_fans"]["wall_frame"] == "local_deck" and sc["drive_test"]["vertex_kinks"] is True
    # two sheets over one plan triangle: all_at reads both, top the higher
    tri = lambda y: ((0.0, y, 0.0), (2.0, y, 0.0), (0.0, y, 2.0), 0)
    s = vf.Surface([tri(1.0), tri(1.4)])
    assert sorted(s.all_at(0.5, 0.5)) == [1.0, 1.4] and s.all_at(3.0, 3.0) == []
    assert s.top(0.5, 0.5)[0] == 1.4
    # a 4 % grade read by a path that crept 0.06 m then ran 1.0 m: the station slopes -0.24 % / -4 % read a 3.8 %/m kink;
    # on the path's own travel the grade is the same both metres (0 kink)
    dh0, dh1 = -0.04 * 0.06, -0.04 * 1.0
    assert abs(dh1 - dh0) * 100 / STEP_M > KINK_PCT
    assert _own_travel_step(dh1, dh0, 1.0, 0.06) < 1e-12
    assert _own_travel_step(dh1, dh0, 1.0, 0.01) is None      # under VERTEX_MIN_TRAVEL_M: the station reading stands


def test_round_q_curb_trace_follows_a_curb_and_cuts_unchecked_stretches():
    """ledger 0079 round Q (tools/lidar_curb_trace.py): on a synthetic step map the dynamic-programming line follows a
    0.15 m curb that drifts 1 m across over 100 m (through a 4 m driveway cut with no step), an outer line takes the curb
    before a taller berm further out, and a segment's rows are `ok` only where NAIP also agrees (a 20 m NAIP-silent
    stretch is cut out, a shorter one is not)"""
    import numpy as np
    import lidar_curb_trace as ct
    n, nb = 400, 81                                   # 200 m of 0.5 m rows, 20 m of 0.25 m bins
    L = np.arange(nb) * ct.BIN_M - 10.0
    D = np.full((n, nb), 0.01)
    curb = [2.0 + 1.0 * i / n for i in range(n)]      # the curb drifts +1 m across over the 200 m
    for i in range(n):
        if not (200 <= i < 208):                      # a 4 m driveway cut
            D[i, int(round((curb[i] + 10.0) / ct.BIN_M))] = 0.15
        D[i, int(round((7.0 + 10.0) / ct.BIN_M))] = 0.40     # a taller berm 5 m further out, all along
    sc = np.where(D >= 0, np.minimum(D, ct.OUTER_CAP_M), 0.0)
    lo = np.full(n, int(round((0.0 + 10.0) / ct.BIN_M)))
    hi = np.full(n, nb - 1)
    sc = sc - ct.INWARD_COST * np.abs(np.arange(nb)[None, :] - lo[:, None])
    path = ct.viterbi(sc, lo, hi)
    got = L[path]
    assert max(abs(got[i] - curb[i]) for i in range(n)) <= 0.25
    flags = [bool(D[i, path[i]] >= 0.08) for i in range(n)]
    naip = [not (100 <= i < 140) and not (300 <= i < 310) for i in range(n)]   # 20 m and 5 m without NAIP
    keep, ok = ct.segments(flags, naip)
    assert not any(ok[100:140]) and all(ok[300:310]) and ok[204]   # the driveway is bridged, the long silence cut
    assert [(round(a * ct.ROW_M), round(b * ct.ROW_M)) for a, b, _, _ in keep] == [(0, 50), (70, 200)]


def test_round_q_corner_flares_off_is_opt_in_and_only_narrows():
    """ledger 0079 round Q (tools/lm_engine_intake.corner_flares_off): a declared corner's flare (a crest that falls to a
    level leg on both sides) is re-laid by station between the two legs' widths; a slip's ramp up to a wider road (no
    fall on its far side within the radius) is left alone; Lake Murray never runs the intake and the Lariat's port does
    not name the key, nor (yet) Sand Creek's"""
    import lm_engine_intake as li
    from scripts.geometry.projection import _meters_per_degree
    origin = {"lat": 39.78, "lon": -104.92, "elev_m": 1500.0}
    pts = [(0.0, 0.0, 3.0 * k) for k in range(60)]
    flare = [11.0] * 20 + [16.8, 30.0] + [42.3] * 10 + [35.0, 27.0] + [23.5] * 26
    m_lon, m_lat = _meters_per_degree(origin["lat"])
    at = [origin["lat"] + 3.0 * 27 / m_lat, origin["lon"]]
    got, rep = li.corner_flares_off(pts, flare, origin, [{"name": "c", "at": at}])
    assert rep[0]["flare"] == [19, 34] and rep[0]["legs_m"] == [11.0, 23.5]
    assert got[:20] == flare[:20] and got[34:] == flare[34:]
    assert all(g <= f + 1e-9 for g, f in zip(got, flare)) and abs(got[26] - (11.0 + 12.5 * 7 / 15)) < 1e-3
    ramp = [5.5] * 20 + [7.0, 9.0] + [11.0] * 38
    got2, rep2 = li.corner_flares_off(pts, ramp, origin, [{"name": "slip", "at": at}])
    assert got2 == ramp and rep2[0]["flare"] is None
    lm = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))
    assert "lm_intake" not in lm
    lar = json.loads((ROOT / "tracks" / "lookout-lariat-lm" / "track.config.json").read_text(encoding="utf-8"))
    assert "corner_flare_off" not in (lar.get("lm_intake") or {})
    # round Q's build rq1 (dahlia_56th unparked with the flare off) went red: the candidate does not name the key yet
    for cfgp in (SC / "track.config.json", SC / "source" / "round_k" / "track.config.json"):
        assert "corner_flare_off" not in (json.loads(cfgp.read_text(encoding="utf-8")).get("lm_intake") or {})
