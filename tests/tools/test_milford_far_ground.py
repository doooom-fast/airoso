"""Milford's far ground (ledger 0082 'Far ground (0.1.11)'): the 2017 lidar's bare earth past the 3DEP grid, Del Mar's mesher
(tools/far_ground_blend.py) with two opt-in additions, beyond-the-reach keeps today's ground (terrain.far_ground "beyond": "keep")
and the planted trees past the grid start on the built far ground (scenery.treefx.planted.seat_far_on_built). numpy."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MF = ROOT / "tracks" / "milford-road-course-lm"
sys.path.insert(0, str(ROOT / "tools"))

import far_ground as fg  # noqa: E402


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_beyond_the_reach_feathers_from_the_lidar_to_todays_ground_with_no_step():
    assert fg.keep_today(30.0, 10.0, 0.0, 40.0) == 30.0                 # at the reach: the lidar's
    assert fg.keep_today(30.0, 10.0, 40.0, 40.0) == 10.0                # past the feather: today's, exactly
    mid = fg.keep_today(30.0, 10.0, 20.0, 40.0)
    assert 10.0 < mid < 30.0 and abs(mid - 20.0) < 1e-9                 # smoothstep's midpoint
    assert fg.keep_today(30.0, None, 5.0, 40.0) == 30.0                 # no ground today, the feather still holds: the fill
    assert fg.keep_today(30.0, None, 40.0, 40.0) is None                # no ground today nor lidar: none, as today


def test_a_product_without_a_reach_grid_reads_as_before():
    meta = {"x0": 0.0, "y0": 0.0, "cell_m": 5.0}
    z = np.arange(16, dtype=float).reshape(4, 4)
    d = fg.Dem(z, meta, np.zeros((4, 4), np.uint8))
    assert d.reach is None and d.reach_at(7.5, 7.5) is None
    assert abs(d.at(7.5, 7.5) - z[1, 1]) < 1e-12                         # a cell centre reads its own value
    r = np.zeros((4, 4))
    r[2:, :] = 10.0
    d2 = fg.Dem(z, meta, None, r)
    assert d2.reach_at(7.5, 7.5) == 0.0 and d2.reach_at(7.5, 12.5) == 10.0 and d2.reach_at(7.5, 10.0) == 5.0
    with tempfile.TemporaryDirectory() as t:
        p = Path(t)
        np.save(p / "far_ground.lidar.npy", z.astype(np.float32))
        (p / "far_ground.lidar.meta.json").write_text(json.dumps(meta))
        assert fg.Dem.load(p).reach is None                             # Del Mar's product (no reach file): as before
        np.save(p / "far_ground.lidar.reach.npy", r.astype(np.float32))
        assert fg.Dem.load(p).reach_at(7.5, 12.5) == 10.0


def test_the_product_fits_the_ground_at_the_cell_centre():
    prod = _load(MF / "source" / "far_ground" / "scripts" / "far_ground_product.py", "mf_far_ground_product")
    rng = np.random.default_rng(1)
    E = rng.uniform(10, 14, 40)                    # every return to one side of the centre (10, 10): a mean would be biased
    N = rng.uniform(6, 14, 40)
    Z = 300.0 + 0.1 * (E - 10) - 0.05 * (N - 10)
    v = prod.fit_cell(10.0, 10.0, E, N, Z, np.ones(40))
    assert abs(v - 300.0) < 1e-9
    Z2 = Z.copy()
    Z2[0] += 5.0                                   # a misclassified return is dropped
    assert abs(prod.fit_cell(10.0, 10.0, E, N, Z2, np.ones(40)) - 300.0) < 1e-6
    assert prod.fit_cell(0, 0, E[:2], N[:2], Z[:2], np.ones(2)) is None            # too few
    En = np.array([0.0, 1.0, 2.0, 3.0])            # collinear: no slope to fit -> the weighted mean
    assert abs(prod.fit_cell(10.0, 10.0, En, np.zeros(4), np.array([1.0, 2.0, 3.0, 4.0]), np.ones(4)) - 2.5) < 1e-12
    big = prod.fit_cell(50.0, 50.0, E, N, Z, np.ones(40))                          # never extrapolated past +-1 m
    assert Z.min() - 1.0 <= big <= Z.max() + 1.0


def test_the_built_ground_reads_the_highest_grass_surface():
    mt = _load(ROOT / "tools" / "make_treefx.py", "mt_far_ground")
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "track.obj"
        p.write_text("o 1GRASS_0\nv 0 10 0\nv 20 10 0\nv 0 30 20\nf 1 2 3\n"
                     "o 1ROAD_road\nv 0 50 0\nv 20 50 0\nv 0 50 20\nf 4 5 6\n"
                     "o 1GRASS_1\nv 0 12 0\nv 20 12 0\nv 0 12 20\nf 7 8 9\n")
        g = mt.BuiltGround(p)
        assert g.tris == 2
        assert abs(g.at(2.0, 2.0) - 12.0) < 1e-9                         # the higher of the two grass layers; the road ignored
        assert abs(g.at(2.0, 10.0) - 20.0) < 1e-9
        assert g.at(30.0, 30.0) is None


def test_milford_declares_it_and_ships_the_product():
    cfg = json.loads((MF / "track.config.json").read_text(encoding="utf-8"))
    fgc = cfg["terrain"]["far_ground"]
    assert fgc["beyond"] == "keep" and fgc["reach_m"] == 500.0 and fgc["cell_m"] == 10.0
    assert fgc["object"] == "1GRASS_FAR" and "1GRASS_FAR" in cfg["scenery"]["bespoke"]["names"]["far"]
    assert cfg["scenery"]["treefx"]["planted"]["seat_far_on_built"] is True
    ship = json.loads((MF / "ship.json").read_text(encoding="utf-8"))
    assert ship["steps"]["draft"].index("far_ground") == ship["steps"]["draft"].index("strip_seam") + 1
    for f in ("far_ground.lidar.npy", "far_ground.lidar.meta.json", "far_ground.lidar.fill.npy", "far_ground.lidar.reach.npy"):
        assert f"data/{f}" in ship["sync_in"]["required"] and (MF / "data" / f).exists()
    meta = json.loads((MF / "data" / "far_ground.lidar.meta.json").read_text(encoding="utf-8"))
    z = np.load(MF / "data" / "far_ground.lidar.npy")
    assert z.shape == (meta["ny"], meta["nx"]) and np.isfinite(z).all()
    fill = np.load(MF / "data" / "far_ground.lidar.fill.npy")
    reach = np.load(MF / "data" / "far_ground.lidar.reach.npy")
    assert ((reach > 0) == (fill == 2)).all()                            # a reach distance only where the lidar does not reach


def test_no_other_track_names_the_opt_in_keys():
    for cfgp in sorted((ROOT / "tracks").glob("*/track.config.json")):
        if cfgp.parent.name in ("milford-road-course-lm", "del-mar-lm"):
            continue
        txt = cfgp.read_text(encoding="utf-8")
        assert '"far_ground"' not in txt and "seat_far_on_built" not in txt, cfgp
    for shp in sorted((ROOT / "tracks").glob("*/ship.json")):
        if shp.parent.name in ("milford-road-course-lm", "del-mar-lm"):
            continue
        assert '"far_ground"' not in shp.read_text(encoding="utf-8"), shp


def test_the_prep_takes_the_sunk_skirt_out_only_when_the_config_names_the_object():
    sh = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")
    i = sh.index("far_ground_prep_blend.py")
    guard = sh[sh.rindex("if [", 0, i):i]
    assert "'far_ground'" in guard and ".get('object')" in guard           # opt-in by terrain.far_ground.object
    assert sh.index("build_kn5_loop.py") < i < sh.index("rock_faces_blend.py")  # first after the prep, before anything reads its ground
    blend = (ROOT / "tools" / "far_ground_blend.py").read_text(encoding="utf-8")
    assert 'obj_name = spec.get("object")' in blend and "if obj_name is None:\n        bmesh.ops.delete(bm, geom=skirt" in blend
