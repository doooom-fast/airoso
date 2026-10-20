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
