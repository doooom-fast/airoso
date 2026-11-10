"""Ledger 0083 pass 4b, the far ground from the lidar: tools/lidar_ground.py's product (the fill), tools/far_ground.py's
lattice and seam, the planner's set_in rows and tools/house_seat_check.py's set-in judgement. numpy only (no laspy, no bpy)."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


lg = _load("lidar_ground")
fg = _load("far_ground")
hs = _load("house_seat_check")


def test_the_fill_spans_a_plane_under_a_building_and_across_a_wide_gap():
    y, x = np.mgrid[0:120, 0:150].astype(float)
    plane = 3.0 + 0.05 * x - 0.02 * y
    known = np.ones(plane.shape, bool)
    known[40:60, 50:80] = False                                  # a hall's footprint: no ground points
    known[:, 100:] = False                                      # past the tiles: a 50-cell-wide gap on one side
    out = lg.harmonic_fill(np.where(known, plane, 0.0), known)
    assert np.abs(out[40:60, 50:80] - plane[40:60, 50:80]).max() < 0.02
    assert np.allclose(out[known], plane[known])
    # past the edge the fill only continues the edge (a harmonic surface, flagged): it is level away from it, not 0
    assert out[:, 140].min() > 3.0


def test_the_block_sum_is_exact():
    a = np.arange(36, dtype=float).reshape(6, 6)
    assert lg.block(a, 3).sum() == a.sum() and lg.block(a, 3).shape == (2, 2)


def test_the_feather_holds_the_grid_at_the_seam_and_lets_go_by_its_length():
    assert fg.feather_w(0.0, 40.0) == 1.0 and fg.feather_w(40.0, 40.0) == 0.0 and abs(fg.feather_w(20.0, 40.0) - 0.5) < 1e-9
    assert fg.ring_height(12.0, 0.8, 0.0, 40.0) == 11.2         # at the border: the grid's own height (lidar - r)
    assert fg.ring_height(12.0, 0.8, 50.0, 40.0) == 12.0        # past the feather: the lidar's


def test_the_ring_meets_the_finer_grid_with_no_t_junction_and_no_hole():
    NX, NY = 9, 7                                               # a grid of 8 x 6 cells, a ring tier of 2 cells
    nodes, polys = fg.ring_plan(NX, NY, 4, 4, step=2)
    assert all(i % 2 == 0 and j % 2 == 0 for i, j in nodes)
    assert not any(0 <= i <= NX - 1 and 0 <= j <= NY - 1 for i, j in nodes)
    edges = Counter()
    for p in polys:
        for a, b in zip(p, p[1:] + p[:1]):
            edges[frozenset((a, b))] += 1
    # every grid border segment is used by exactly one ring cell; every other edge is either shared by two ring cells or
    # lies on the ring's outer edge
    border = [frozenset(((i, 0), (i + 1, 0))) for i in range(NX - 1)] + [frozenset(((i, NY - 1), (i + 1, NY - 1))) for i in range(NX - 1)] \
        + [frozenset(((0, j), (0, j + 1))) for j in range(NY - 1)] + [frozenset(((NX - 1, j), (NX - 1, j + 1))) for j in range(NY - 1)]
    assert all(edges[e] == 1 for e in border)
    outer = {e for e, n in edges.items() if n == 1} - set(border)
    assert all(any(abs(c) == 4 or c in (NX - 1 + 4, NY - 1 + 4) for v in e for c in v) for e in outer)
    # the ring's area: the outer box less the grid
    area = 0.0
    for p in polys:
        area += 0.5 * abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1])))
    assert area == (NX - 1 + 8) * (NY - 1 + 8) - (NX - 1) * (NY - 1)


def test_a_grid_with_no_whole_tier_is_refused():
    try:
        fg.ring_plan(10, 7, 4, 4, step=2)
    except ValueError:
        return
    raise AssertionError("an odd grid took a 2-node tier")


def test_the_dem_reads_its_cell_centres_and_clamps_at_its_edge():
    z = np.array([[0.0, 1.0], [2.0, 3.0]])
    d = fg.Dem(z, {"x0": 0.0, "y0": 0.0, "cell_m": 10.0})
    assert d.at(5.0, 5.0) == 0.0 and d.at(15.0, 15.0) == 3.0 and abs(d.at(10.0, 10.0) - 1.5) < 1e-9
    assert d.at(-100.0, -100.0) == 0.0


def _obj(path, building_top, building_bottom=0.85, mid=False):
    """1GRASS: a slope y = 0.5 z over 0..20 x 0..20; one BUILDING box over x 2..12, z 2..12 (mid: two boxes, x 2..7 and
    7..12, sharing the wall at x 7 as the author's parts do)"""
    L = ["o 1GRASS"]
    L += [f"v {x} {0.5 * z} {z}" for z in (0, 20) for x in (0, 20)]
    L += ["f 1 2 4", "f 1 4 3", "o BUILDING_TILTUP_0"]
    boxes = [[(2, 2), (7, 2), (7, 12), (2, 12)], [(7, 2), (12, 2), (12, 12), (7, 12)]] if mid else [[(2, 2), (12, 2), (12, 12), (2, 12)]]
    k = 5
    for c in boxes:
        for i in range(4):
            (ax, az), (bx, bz) = c[i], c[(i + 1) % 4]
            L += [f"v {ax} {building_bottom} {az}", f"v {bx} {building_bottom} {bz}", f"v {bx} {building_top} {bz}",
                  f"v {ax} {building_top} {az}", f"f {k} {k + 1} {k + 2}", f"f {k} {k + 2} {k + 3}"]
            k += 4
    path.write_text("\n".join(L) + "\n")


def test_a_deck_set_into_its_slope_is_judged_against_its_deck_not_its_uphill_ground():
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        (proj / "data").mkdir()
        _obj(proj / "data" / "track.obj", building_top=4.0)        # the uphill ground under its walls reaches 6.0
        rep, _ = hs.run(proj)
        assert rep["buried"] == 1 and rep["verdict"] == "FAIL"   # without the declaration: a buried wall, as ever
        ring = [[2, 2], [12, 2], [12, 12], [2, 12]]
        (proj / "data" / "house_seat.set_in.json").write_text(json.dumps({"decks": [{"key": "g", "ring_xy": ring, "deck_top": 4.0}]}))
        rep, _ = hs.run(proj)
        assert rep["set_in"]["judged"] == 1 and rep["buried"] == 0 and rep["verdict"] == "PASS"
        (proj / "data" / "house_seat.set_in.json").write_text(json.dumps({"decks": [{"key": "g", "ring_xy": ring, "deck_top": 5.0}]}))
        rep, _ = hs.run(proj)
        assert rep["buried"] == 1                               # a deck built 1 m off its measure still fails
        # two parts sharing a wall are one island to the gate: judged against the higher part's deck
        halves = [{"key": "g_p0", "ring_xy": [[2, 2], [7, 2], [7, 12], [2, 12]], "deck_top": 3.0},
                  {"key": "g_p1", "ring_xy": [[7, 2], [12, 2], [12, 12], [7, 12]], "deck_top": 4.0}]
        _obj(proj / "data" / "track.obj", building_top=4.0, mid=True)
        (proj / "data" / "house_seat.set_in.json").write_text(json.dumps({"decks": halves}))
        rep, _ = hs.run(proj)
        assert rep["set_in"]["rows"][0]["set_in"] == "g_p0+g_p1" and rep["verdict"] == "PASS"


def test_the_planner_sets_a_hillside_deck_in_only_when_the_plan_asks():
    pb = _load("plan_buildings")
    row = {"key": "g", "wall_h_m": 3.0, "_h": "class", "form": "flat", "footprint_lonlat": [[0, 0], [1, 0], [1, 1]]}
    rec = {"status": "no_roof", "roof_src": "first", "n_roof": 500}
    rf = {"form": "flat", "rms_m": 0.2, "median_m": 4.9, "fits": {}, "parapet_m": 0.0,
          "hillside": {"shift_m": 6.1, "ground_p10_p90_navd88": [18.74, 30.02], "ground_median_navd88": 24.84}}
    plain = pb.roof_form_rows(dict(row), rec, rf, None)
    setin = pb.roof_form_rows(dict(row), rec, rf, None, set_in=True)
    assert "set_in" not in plain[0]
    assert setin[0]["set_in"]["ground_navd88"] == 18.74 and setin[0]["wall_h_m"] == plain[0]["wall_h_m"]


def test_no_other_plan_or_track_names_the_pass_4b_keys():
    for p in (ROOT / "tracks").glob("*/source/bespoke/*.plan.json"):
        if p.parts[-4] != "del-mar-lm":
            assert "set_in_slope" not in json.loads(p.read_text(encoding="utf-8")), p
    for p in (ROOT / "tracks").glob("*/track.config.json"):
        if p.parts[-2] not in ("del-mar-lm", "milford-road-course-lm"):    # Milford 0.1.11: ledger 0082's far ground
            assert "far_ground" not in json.dumps((json.loads(p.read_text(encoding="utf-8")).get("terrain") or {})), p
