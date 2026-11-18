"""tools/make_treefx.py — plan() is exactly what build() writes (ledger 0049 fix round: tools/verify_race.py G judges
the TreeFX trunks against the race lanes and walls from the planner, before the models are copied, and the ship
re-judges the written trees.txt). A tiny project: a straight 200 m road, palms beside it and one on it."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import make_treefx as mt  # noqa: E402
import verify_race as vr  # noqa: E402


def _project(bins=("PalmV1.bin",)):
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "source" / "trees").mkdir(parents=True)
    for b in bins:
        (d / "source" / "trees" / b).write_bytes(b"bin")
    (d / "track.config.json").write_text(json.dumps({"slug": "tiny"}), encoding="utf-8")
    pts = [[float(x), 0.0, 0.0] for x in range(0, 201, 5)]
    (d / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": pts, "widths_m": [10.0] * len(pts)}))
    palms = [{"x": 20.0, "y": 0.0, "z": 9.0}, {"x": 60.0, "y": 0.0, "z": -12.0},
             {"x": 100.0, "y": 0.0, "z": 2.0},                      # ON the road: make_treefx's corridor guard drops it
             {"x": 140.0, "y": 0.5, "z": 30.0}]
    (d / "data" / "scatter_positions.json").write_text(json.dumps({"palms": palms, "trees": [], "scrub": [],
                                                                   "median_planting": []}))
    _gate_obj(d, ["1GRASS_0", "1ROAD_road"])
    return d


def _gate_obj(d, groups):
    """a stand-in gate OBJ: only the o / usemtl lines make_treefx reads"""
    (d / "data" / "track.obj").write_text("".join(f"o {g}\nusemtl {g}_mat\nv 0 0 0\n" for g in groups), encoding="utf-8")


def test_surface_materials_list_every_physical_tile_off_the_gate_obj():
    """ledger 0046: the tiered terrain tiles 1GRASS into as many tiles as it needs; TreeFX snaps onto every one of
    them (natural order) + the road, never onto the visual-only far ring, and never from a hard-coded pair"""
    d = _project()
    _gate_obj(d, ["1GRASS_10", "1GRASS_2", "GRASS_FAR_0", "1GRASS_0", "1ROAD_road", "1GRASS_1", "GRASS_FAR_1", "1KERB_sidewalk"])
    assert mt.surface_materials(d) == "1GRASS_0_mat, 1GRASS_1_mat, 1GRASS_2_mat, 1GRASS_10_mat, 1ROAD_road_mat"
    mt.build(d)
    ini = (d / "build" / "tiny" / "extension" / "ext_config.ini").read_text(encoding="utf-8")
    assert "SURFACE_MATERIALS = 1GRASS_0_mat, 1GRASS_1_mat, 1GRASS_2_mat, 1GRASS_10_mat, 1ROAD_road_mat" in ini
    assert "GRASS_FAR" not in ini
    (d / "data" / "track.obj").unlink()
    try:
        mt.surface_materials(d)
    except SystemExit as e:
        assert "track.obj" in str(e)
    else:
        raise AssertionError("no gate OBJ must stop the TreeFX writer, not fall back to a guessed tile list")


def test_plan_is_what_build_writes():
    d = _project()
    p = mt.plan(d)
    mt.build(d)
    written = (d / "build" / "tiny" / "extension" / "trees" / "trees.txt").read_text(encoding="utf-8")
    assert written == "\n".join(p["lines"]) + "\n"
    assert p["rejected"] == 1 and p["counts"] == {"palms": 3} and p["used"] == {"PalmV1.bin"}
    assert [(e["x"], e["z"]) for e in p["entries"]] == [(20.0, 9.0), (60.0, -12.0), (140.0, 30.0)]
    # the written file read back in the engine frame (trees.txt carries x, y, -z) is the plan's positions
    back = vr.tree_items_from_txt(written)
    assert [(i["x"], i["z"]) for i in back] == [(20.0, 9.0), (60.0, -12.0), (140.0, 30.0)]


def test_all_species_plans_positions_even_without_the_models():
    d = _project(bins=())
    assert mt.plan(d)["entries"] == []                              # no .bin: build() would write no palm at all
    e = mt.plan(d, all_species=True)["entries"]
    assert [(x["x"], x["z"]) for x in e] == [(20.0, 9.0), (60.0, -12.0), (140.0, 30.0)] and all(x["zone"] == "palms" for x in e)


def test_nothing_is_planted_on_a_corner_apron():
    """ledger 0054 P1 fix round: data/aprons.json (tools/author_aprons_blend.py) marks pavement no connector centreline
    describes; a palm on it, or within APRON_PLANT_CLEAR_M of its outline, is dropped — absent the file, kept"""
    d = _project()
    pos = json.loads((d / "data" / "scatter_positions.json").read_text())
    pos["palms"] += [{"x": 60.0, "y": 0.0, "z": 20.0}, {"x": 60.0, "y": 0.0, "z": 25.6}, {"x": 60.0, "y": 0.0, "z": 28.0}]
    (d / "data" / "scatter_positions.json").write_text(json.dumps(pos))
    before = {(round(e["x"], 1), round(e["z"], 1)) for e in mt.plan(d)["entries"]}
    assert {(60.0, 20.0), (60.0, 25.6), (60.0, 28.0)} <= before
    (d / "data" / "aprons.json").write_text(json.dumps({"aprons": [{"id": "AP1", "outline_xz": [
        [50.0, 15.0], [70.0, 15.0], [70.0, 25.0], [50.0, 25.0]]}]}))
    after = {(round(e["x"], 1), round(e["z"], 1)) for e in mt.plan(d)["entries"]}
    assert (60.0, 20.0) not in after and (60.0, 25.6) not in after       # on it, and 0.6 m off its edge
    assert (60.0, 28.0) in after and before - after == {(60.0, 20.0), (60.0, 25.6)}


def _fill_project(grow=None, tag=True):
    """a straight 400 m road with a 40 m heightfield under it (the density fill's grid); ``grow`` = (rows_n, rows_s,
    cols_w): the same grid grown by whole cells, the old block value for value, its meta recording grid_grow (``tag``)"""
    import math
    import struct
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "source" / "trees").mkdir(parents=True)
    (d / "track.config.json").write_text(json.dumps({"slug": "tiny"}), encoding="utf-8")
    o = {"lon": -117.0, "lat": 32.8, "elev_m": 100.0}
    pts = [[float(x), 0.0, 0.0] for x in range(0, 401, 5)]
    (d / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": pts, "widths_m": [10.0] * len(pts),
                                                                  "origin": o}))
    (d / "data" / "scatter_positions.json").write_text(json.dumps({"palms": [], "trees": [], "scrub": [],
                                                                   "median_planting": []}))
    _gate_obj(d, ["1GRASS_0", "1ROAD_road"])
    sp = 40.0
    s, w, n = 32.7982, -117.0021, 32.8018
    ny, nx = 11, 16
    gy, gx = sp / 111_000.0, sp / (111_000.0 * math.cos(math.radians((s + n) / 2)))
    grid = [[100.0 + 0.3 * i + 0.2 * j for i in range(nx)] for j in range(ny)]
    meta = {"bbox_swne": [s, w, n, w + (nx - 1) * gx], "nx": nx, "ny": ny, "spacing_m": sp}
    if grow:
        rn, rs, cw = grow
        grid = [[(grid[j - rn][i - cw] if 0 <= j - rn < ny and 0 <= i - cw < nx else 90.0) for i in range(nx + cw)]
                for j in range(ny + rn + rs)]
        meta = {"bbox_swne": [s - rs * gy, w - cw * gx, n + rn * gy, meta["bbox_swne"][3]], "nx": nx + cw,
                "ny": ny + rn + rs, "spacing_m": sp}
        if tag:
            meta["grid_grow"] = {"rows_n": rn, "rows_s": rs, "cols_w": cw, "cols_e": 0}
    NY, NX = len(grid), len(grid[0])
    hdr = "{'descr': '<f8', 'fortran_order': False, 'shape': (%d, %d), }" % (NY, NX)
    hdr += " " * ((64 - (10 + len(hdr) + 1) % 64) % 64) + "\n"
    buf = b"\x93NUMPY\x01\x00" + struct.pack("<H", len(hdr)) + hdr.encode("latin1")
    buf += b"".join(struct.pack("<d", v) for row in grid for v in row)
    (d / "data" / "heightfield.npy").write_bytes(buf)
    (d / "data" / "heightfield.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return d


def test_a_grown_grid_fills_the_loops_own_cells_exactly_as_before():
    """ledger 0054 P2: the heightfield grown by whole cells (grid_grow) must not move one fill tree near the loop - the
    loop's own cells keep their numbering (every hash: jitter, pick, thinning) and the added cells plant nothing
    until P4 (A9). Without the grid_grow record the same grown grid renumbers every cell: the trees move."""
    def fill(d):
        return sorted((e["zone"], e["model"], round(e["x"], 2), round(e["z"], 2))
                      for e in mt.plan(d, all_species=True)["entries"] if e["zone"].startswith("fill_"))
    before = fill(_fill_project())
    assert len(before) > 50
    assert fill(_fill_project(grow=(2, 2, 3))) == before
    assert fill(_fill_project(grow=(2, 2, 3), tag=False)) != before


# --- ledger 0054 P4 step 3 (EXPANSION-PLAN A9): the north network, planted by zone from the aerial bins -------------

def _north_project(bins=None, zones=None, median_trees=None, cap_scale=None, pads=None, cuts=None, config=True,
                   medians=None):
    """_fill_project grown by (2, 2, 3) with one north piece 'A' laid through the ADDED north rows: a straight 500 m road
    at z = 240 from x = -100 to 400 (20 m curb to curb), as a connector + the readable intermediate (stations every
    2.5 m, a raised planted median 4 m wide along s 0-500) + the aerial bins + scenery.treefx (``config``)"""
    d = _fill_project(grow=(2, 2, 3))
    rows = []
    for k in range(201):
        s = 2.5 * k
        rows.append([s, -100.0 + s, 240.0, 0.0, 0.0, 10.0, -10.0, 4.0, 0.0, "planted", 0.0, "2", "2", "eye"])
    cols = ["s", "x", "z", "y_3dep", "y_smooth", "left_m", "right_m", "median_w_m", "median_off_m", "median_type",
            "osm_sep_m", "lanes_fwd", "lanes_rev", "median_src"]
    md = medians if medians is not None else [
        {"id": "MD1", "piece": "A", "type": "planted", "raised": True, "s_from": 0.0, "s_to": 500.0, "width_m": [4.0, 4.0],
         "polygon_xz": [[-100.0, 238.0], [400.0, 238.0], [400.0, 242.0], [-100.0, 242.0]]}]
    (d / "data" / "expansion.north.json").write_text(json.dumps({
        "frame": {"origin": {"lon": -117.0, "lat": 32.8, "elev_m": 100.0}},
        "pieces": [{"id": "A", "name": "test", "columns": cols, "stations": rows}], "medians": md}), encoding="utf-8")
    cpts = [[-100.0 + x, 0.0, 240.0] for x in range(0, 501, 5)]
    (d / "data" / "connectors.local.json").write_text(json.dumps({"connectors": [
        {"name": "north_test#0", "kind": "connector", "points_xyz_m": cpts, "widths_m": [20.0] * len(cpts),
         "expansion": {"route": "north", "piece": "A"}}]}), encoding="utf-8")
    (d / "source" / "expansion").mkdir(parents=True, exist_ok=True)
    b = bins if bins is not None else {"A": {"0L": [800, 1000, 0, 200], "1L": [800, 1000, 0, 200],
                                             "0R": [800, 1000, 0, 200], "1R": [800, 1000, 0, 200]}}
    (d / "source" / "expansion" / "veg.json").write_text(json.dumps(b), encoding="utf-8")
    if pads is not None:
        (d / "data" / "pads.built.json").write_text(json.dumps({"pads": [{"id": "J9", "outline_xz": pads}]}), encoding="utf-8")
    if cuts is not None:        # the measured real walls of record (measure_p3.json's shape)
        (d / "source" / "expansion" / "walls.json").write_text(json.dumps({"walls": {"real_walls_ge_3m": cuts}}), encoding="utf-8")
    cfg = {"slug": "tiny"}
    if config:
        tf = {"veg_bins": "source/expansion/veg.json", "pieces": "data/expansion.north.json", "bin_m": 250,
              "zones": zones if zones is not None else [{"piece": "A", "trees": "north_canyon_trees", "bushes": "north_scrub"}],
              "median_tree_types": ["planted"], "median_trees": median_trees if median_trees is not None else []}
        if cuts is not None:
            tf["rock_walls"] = "source/expansion/walls.json"
        if cap_scale is not None:
            tf["cap_scale"] = cap_scale
        cfg["scenery"] = {"treefx": tf}
    (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return d


def _entries(d, prefix):
    return [e for e in mt.plan(d, all_species=True)["entries"] if e["zone"].startswith(prefix)]


def test_north_config_plants_the_added_cells_and_moves_nothing_of_the_loops():
    """the loop's own cells plant exactly as without the config (every fill_* entry identical); the north zones plant
    only with the config, every one at least the yard setback off every pavement and never in the loop's own cells"""
    on, off = _north_project(), _north_project(config=False)
    key = lambda es: sorted((e["zone"], e["model"], round(e["x"], 3), round(e["z"], 3)) for e in es)
    assert key(_entries(on, "fill_")) == key(_entries(off, "fill_")) and len(_entries(off, "fill_")) > 50
    assert _entries(off, "north_") == [] and mt.plan(off)["north"] is None
    north = _entries(on, "north_")
    assert len(north) > 100
    for e in north:
        assert e["zone"] in mt.NORTH_ZONE_ORDER
        if e["zone"].startswith("north_median"):
            continue
        if -100.0 <= e["x"] <= 400.0:
            assert abs(e["z"] - 240.0) >= 10.0 + 6.0, e        # the piece's curb + the 6 m yard setback
        assert not (-200.0 <= e["z"] <= 200.0 and -196.0 <= e["x"] <= 404.0), e    # never inside the loop's own block
    assert mt.plan(on)["north"]["area_loop_m2"] > 0


def test_north_density_follows_the_aerial_bins_per_side_and_station():
    """bin 0L a woodland, 1L bare ground, the right side scrub only: trees stand left of s 0-250 and nowhere on the
    bare bin; the right side gets bushes and no trees"""
    d = _north_project(bins={"A": {"0L": [200, 1600, 0, 200], "1L": [2000, 0, 0, 0],
                                   "0R": [1000, 0, 0, 1000], "1R": [1000, 0, 0, 1000]}})
    es = [e for e in _entries(d, "north_") if not e["zone"].startswith("north_median")]
    left = [e for e in es if e["z"] > 240.0]
    right = [e for e in es if e["z"] < 240.0]
    assert not [e for e in left if -100.0 + 250.0 <= e["x"]], "the bare bin (1L, s 250-500) plants nothing"
    assert [e for e in left if e["zone"] == "north_canyon_trees"], "the woodland bin plants trees"
    assert right and all(e["zone"] == "north_scrub" for e in right), "scrub only on the right (no canopy there)"


def test_nothing_on_a_junction_pad_or_a_rock_cut_face():
    """a pad outline in the band keeps every plant off it (and APRON_PLANT_CLEAR_M past its edge); a measured real wall
    (rock_walls, NORTH_ROCK_RISE_M or more) is bare from the curb to NORTH_ROCK_REACH_M on its side along its stations
    (+ NORTH_ROCK_PAD_M each end); a wall under the threshold is a bank and keeps its plants"""
    pad = [[50.0, 262.0], [90.0, 262.0], [90.0, 300.0], [50.0, 300.0]]
    rock = [{"piece": "A", "side": "right", "s_from": 0.0, "s_to": 245.0, "max_real_m": 5.0},      # right = z < 240
            {"piece": "A", "side": "left", "s_from": 0.0, "s_to": 245.0, "max_real_m": 1.5}]
    bare = _north_project(pads=pad, cuts=rock)
    es = [e for e in _entries(bare, "north_") if not e["zone"].startswith("north_median")]
    assert es
    for e in es:
        assert not (50.0 - 1.0 <= e["x"] <= 90.0 + 1.0 and 262.0 - 1.0 <= e["z"] <= 300.0 + 1.0), ("on the pad", e)
        if -100.0 <= e["x"] <= 150.0 - mt.NORTH_ROCK_PAD_M and e["z"] < 240.0:
            assert 230.0 - e["z"] > mt.NORTH_ROCK_REACH_M, ("on the rock face", e)
    assert [e for e in es if -100.0 <= e["x"] <= 150.0 and e["z"] > 240.0 and e["z"] - 250.0 <= mt.NORTH_ROCK_REACH_M], \
        "the 1.5 m bank keeps its plants"
    st = mt.plan(bare)["north"]
    assert st["drops"]["pad"] > 0 and st["drops"]["rock"] > 0
    assert len(_entries(_north_project(), "north_")) > len(_entries(bare, "north_"))


def test_median_trees_only_where_declared_and_on_raised_planted_medians_only():
    """the islands' low planting is the assembler's (scatter_positions.json median_planting), never duplicated here:
    the north adds only the declared trees, down the island's middle, inside its outline, 6 m clear of each nose"""
    d = _north_project(median_trees=[{"piece": "A", "s": [100.0, 300.0], "zone": "north_median_trees"}])
    trees = _entries(d, "north_median_trees")
    assert trees and not [e for e in _entries(d, "north_") if "median" in e["zone"] and e["zone"] != "north_median_trees"]
    for e in trees:
        assert 0.0 - 0.01 <= e["x"] <= 200.0 + 0.01 and abs(e["z"] - 240.0) < 0.01, e      # s 100-300 at the middle
        assert e["model"] in {"PepperV1.bin", "Oak3.bin"}
    xs = sorted(e["x"] for e in trees)
    assert all(abs((b - a) - mt.NORTH_MEDIAN_TREE_STEP_M) < 0.01 for a, b in zip(xs, xs[1:]))
    near_nose = _entries(_north_project(median_trees=[{"piece": "A", "s": [0.0, 500.0]}]), "north_median_trees")
    assert near_nose and all(-100.0 + mt.NORTH_MEDIAN_END_CLEAR_M - 0.01 <= e["x"] <= 400.0 - mt.NORTH_MEDIAN_END_CLEAR_M + 0.01
                             for e in near_nose)
    # a terracotta median (Mission Gorge) stays bare; so does one that is not raised
    md = [{"id": "MD1", "piece": "A", "type": "terracotta", "raised": True, "s_from": 0.0, "s_to": 500.0, "width_m": [4.0, 4.0],
           "polygon_xz": [[-100.0, 238.0], [400.0, 238.0], [400.0, 242.0], [-100.0, 242.0]]},
          {"id": "MD2", "piece": "A", "type": "planted", "raised": False, "s_from": 0.0, "s_to": 500.0, "width_m": [4.0, 4.0],
           "polygon_xz": [[-100.0, 238.0], [400.0, 238.0], [400.0, 242.0], [-100.0, 242.0]]}]
    assert _entries(_north_project(medians=md, median_trees=[{"piece": "A", "s": [100.0, 300.0]}]), "north_median") == []


def test_north_caps_scale_with_planted_area_at_the_loops_density():
    """cap = the loop's cap x (north area / loop area) x cap_scale, applied to the north alone; the loop's thinning is
    untouched (its fill count is the same with and without the north); a bigger cap_scale keeps more"""
    d = _north_project()
    p = mt.plan(d, all_species=True)
    st = p["north"]
    for name, cap in (("trees", mt.CAP_TREES), ("bushes", mt.CAP_BUSHES)):
        assert st["caps"][name] == round(cap * st["area_north_m2"] / st["area_loop_m2"])
        assert st["kept"][name] <= st["aerial_implied"][name]
    assert st["cap_scale"] == 1.0 and st["loop_density_per_ha"]["trees"] > 0
    assert sum(1 for e in p["entries"] if e["zone"].startswith("fill_")) == len(_entries(_north_project(config=False), "fill_"))
    big = mt.plan(_north_project(cap_scale=10.0), all_species=True)["north"]
    assert big["caps"]["trees"] == round(mt.CAP_TREES * 10.0 * big["area_north_m2"] / big["area_loop_m2"])
    assert big["caps"]["trees"] > st["caps"]["trees"] and big["kept"]["trees"] >= st["kept"]["trees"]
    assert sum(big["per_piece_total"].values()) >= sum(st["per_piece_total"].values())
    assert "A" in st["per_piece"] and all(isinstance(v, int) for v in st["per_piece"]["A"].values())


def test_build_writes_the_north_zones_and_the_report():
    d = _north_project(median_trees=[{"piece": "A", "s": [100.0, 300.0]}])
    for b in ("Oak3.bin", "Pine_Aleppo.bin", "Gum.bin", "Sage.bin", "Yucca.bin", "Bush.bin", "Bush3.bin", "Agave.bin", "PepperV1.bin"):
        (d / "source" / "trees" / b).write_bytes(b"bin")
    p = mt.plan(d)
    mt.build(d)
    written = (d / "build" / "tiny" / "extension" / "trees" / "trees.txt").read_text(encoding="utf-8")
    assert written == "\n".join(p["lines"]) + "\n"
    rep = json.loads((d / "data" / "treefx.report.json").read_text(encoding="utf-8"))
    assert rep["north"]["per_piece_total"]["A"] > 0 and rep["per_zone"]["north_median_trees"] > 0
    assert rep["surface_materials"] == "1GRASS_0_mat, 1ROAD_road_mat" and rep["total"] == sum(rep["per_zone"].values())


def test_a_declared_zoning_with_no_bins_file_is_an_error_not_a_bare_network():
    d = _north_project()
    (d / "source" / "expansion" / "veg.json").unlink()
    try:
        mt.plan(d)
    except SystemExit as e:
        assert "veg.json" in str(e)
    else:
        raise AssertionError("scenery.treefx naming a missing bins file must stop the planner")


def test_built_surface_guard_drops_plants_on_rock_walks_roads_and_in_buildings():
    """ledger 0054 P4 integration fix round: the gate OBJ is the truth — a plant whose spot the built road kn5 covers with
    a rock cut face (1GRASS_ROCK*), a walk (1KERB*), a road (1ROAD*) or a HOUSE / BUILDING footprint (+ BUILT_BUILDING_CLEAR_M)
    is dropped with its reason; the raised islands' planting (unguarded) is not; without the OBJ nothing is guarded"""
    d = _project()
    palms = [{"x": 20.0, "y": 0.0, "z": 30.0},     # inside the house roof
             {"x": 20.0, "y": 0.0, "z": 25.3},     # 0.7 m outside its wall: within BUILT_BUILDING_CLEAR_M
             {"x": 20.0, "y": 0.0, "z": 22.0},     # 4 m clear of it: kept
             {"x": 60.0, "y": 0.0, "z": 30.0},     # on the rock face
             {"x": 100.0, "y": 0.0, "z": 8.0},     # on the walk (6.0-9.0 beside the 10 m road), past the corridor guard's 6 m
             {"x": 140.0, "y": 0.5, "z": 30.0}]    # open ground: kept
    (d / "data" / "scatter_positions.json").write_text(json.dumps({"palms": palms, "trees": [], "scrub": [],
                                                                   "median_planting": []}))
    obj = ["o 1GRASS_0", "usemtl 1GRASS_0_mat", "v -10 0 -50", "v 200 0 -50", "v 200 0 50", "v -10 0 50", "f 1 2 3 4",
           "o HOUSE", "usemtl HOUSE_mat",
           "v 10 0 26", "v 30 0 26", "v 30 0 40", "v 10 0 40",            # floor ring (5-8)
           "v 10 5 26", "v 30 5 26", "v 30 5 40", "v 10 5 40",            # roof ring (9-12)
           "f 9 10 11 12", "f 5 6 10 9", "f 6 7 11 10",                   # roof + two walls (walls: no plan area)
           "o 1GRASS_ROCK_0", "usemtl 1GRASS_ROCK_0_mat", "v 50 0 20", "v 70 0 20", "v 70 8 40", "f 13 14 15",
           "o 1KERB_sidewalk", "usemtl 1KERB_sidewalk_mat", "v 90 0 6", "v 110 0 6", "v 110 0 9", "v 90 0 9", "f 16 17 18 19",
           "o 1ROAD_road", "usemtl 1ROAD_road_mat", "v 0 0 -5", "v 200 0 -5", "v 200 0 5", "v 0 0 5", "f 20 21 22 23"]
    (d / "data" / "track.obj").write_text("\n".join(obj) + "\n", encoding="utf-8")
    p = mt.plan(d)
    kept = sorted((e["x"], e["z"]) for e in p["entries"])
    assert kept == [(20.0, 22.0), (140.0, 30.0)], kept
    assert p["rejected_built"] == {"rock": 1, "road": 0, "walk": 1, "building": 2}
    assert p["rejected_built_loop"] == p["rejected_built"]
    (d / "data" / "track.obj").unlink()
    assert len(mt.plan(d)["entries"]) == 6 and mt.plan(d)["rejected_built"] == {"rock": 0, "road": 0, "walk": 0, "building": 0}


def test_built_surface_guard_reads_quads_and_ignores_walls():
    b = mt.BuiltSurfaces.__new__(mt.BuiltSurfaces)
    b.cells, b.counts = {}, {"building": 0}
    b._add("building", (0.0, 0.0), (10.0, 0.0), (10.0, 10.0))
    assert b.kinds_at(5.0, 2.0) == {"building"} and b.kinds_at(2.0, 8.0) == set()
    assert b.reject(10.6, 5.0) == "building" and b.reject(12.0, 5.0) is None


def test_built_surface_guard_judges_the_spot_as_written():
    """ledger 0054 P4 integration fix round (run 2): trees.txt carries centimetres; a plan spot a few millimetres clear of
    the building ring lands inside it once rounded. The guard must judge the rounded spot, and the plan's entries carry it."""
    # a house wall running diagonally (z = x - 124 between x 150 and 170): the plant stands just above the wall's line,
    # its 315-degree ring sample 0.4 mm outside the wall unrounded and 4 mm inside once the spot is rounded to centimetres
    b = mt.BuiltSurfaces.__new__(mt.BuiltSurfaces)
    b.cells, b.counts = {}, {"building": 0}
    b._add("building", (150.0, 26.0), (170.0, 26.0), (170.0, 46.0))
    raw = (164.996, 42.4121)
    assert b.reject(*raw) is None
    assert b.reject(round(raw[0], 2), round(raw[1], 2)) == "building"
    d = _project()
    palms = [{"x": raw[0], "y": 0.0, "z": raw[1]},     # the millimetre case: dropped only if judged as written
             {"x": 140.0, "y": 0.123456, "z": 30.0}]   # open ground: kept, its coordinates rounded in the plan
    (d / "data" / "scatter_positions.json").write_text(json.dumps({"palms": palms, "trees": [], "scrub": [],
                                                                   "median_planting": []}))
    obj = ["o 1GRASS_0", "usemtl 1GRASS_0_mat", "v -10 0 -50", "v 200 0 -50", "v 200 0 50", "v -10 0 50", "f 1 2 3 4",
           "o HOUSE", "usemtl HOUSE_mat", "v 150 0 26", "v 170 0 26", "v 170 0 46", "f 5 6 7"]
    (d / "data" / "track.obj").write_text("\n".join(obj) + "\n", encoding="utf-8")
    p = mt.plan(d)
    assert [(e["x"], e["y"], e["z"]) for e in p["entries"]] == [(140.0, 0.12, 30.0)]
    assert p["rejected_built"]["building"] == 1
    assert any(ln.startswith("tree: ") and "pos=140.00, 0.12, -30.00" in ln for ln in p["lines"])


def test_bush_bin_is_drawn_at_bush3_height_not_its_20_m_tree_ini():
    """Kevin 2026-11-13 after driving Lake Murray: "bushes are too big". Bush.bin's tree.ini says HEIGHT 20.66 m, so its
    rank-rule size takes RANK_SIZE_FIX (Bush3's height at the same size) and is written to 3 decimals; others unchanged"""
    p = mt.plan(_north_project(), all_species=True)

    def size_of(line):
        return line.rsplit("size = ", 1)[1].split(";")[0]

    bush = [ln for ln in p["lines"] if ln.startswith("tree: Bush.bin;")]
    assert bush
    for ln in bush:
        s = size_of(ln)
        assert len(s.split(".")[1]) == 3, ln
        assert float(s) <= mt.RANK_SIZE_FIX["Bush.bin"] * 1.0 + 0.0005, ln
        assert 20.66 * float(s) <= 2.1, ln          # drawn height, m
    rest = [ln for ln in p["lines"] if ln.startswith("tree: ") and not ln.startswith("tree: Bush.bin;")]
    assert rest and all(len(size_of(ln).split(".")[1]) == 2 for ln in rest)
