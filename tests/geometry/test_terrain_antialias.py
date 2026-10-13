"""Ledger 0046 fix round 2 — the washboard ribs: anti-aliased sampling of the finest tier
(``tier_options.antialias``: a tent of half-width one cell over the base lattice), the data-chosen diagonal of
plain square cells (``terrain_tiers.data_diagonals``), the sampler wiring them (taps fetched, filtered heights
written, the cache itself still point samples), and ``tools/rib_check.py`` — the measurement on the built terrain that
catches a sub-cell feature folded into a staircase. Synthetic lattices and a 300 m box; no network, no Blender."""
from __future__ import annotations

import gzip
import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.elevation import terrain_sample as ts  # noqa: E402
from scripts.geometry import terrain_tiers as tt  # noqa: E402

_spec = importlib.util.spec_from_file_location("rib_check", ROOT / "tools" / "rib_check.py")
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

ORIGIN = {"lon": -117.0, "lat": 32.8, "elev_m": 100.0}
M_LON, M_LAT = tt.meters_per_degree(32.8)


def _terrain(half=300.0, aa=True, **kw):
    t = {"terrain_band_m": 22.0,
         "tiers": [{"within_m": 30.0, "cell_m": 4.4}, {"within_m": 120.0, "cell_m": 17.6}, {"cell_m": 52.8}],
         "tier_options": {"physical_within_m": 80.0, **({"antialias": {"cell_m": 4.4}} if aa else {})},
         "far_extent": {"bbox_swne": [32.8 - half / M_LAT, -117.0 - half / M_LON, 32.8 + half / M_LAT,
                                      -117.0 + half / M_LON]}}
    t.update(kw)
    return t


def _project(terrain):
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "loop": False, "terrain": terrain}))
    pts = [[float(x), 0.0, 0.0] for x in range(-150, 151, 5)]
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": pts, "widths_m": [10.0] * len(pts), "origin": ORIGIN}))
    return d


def _channel(x, z):
    """a 4 m-wide, 5 m-deep channel crossing at 27 degrees (narrower than two 4.4 m cells) in a 1 % slope"""
    d = abs(z - 0.5 * x - 40.0) / math.hypot(1.0, 0.5)
    return 100.0 + 0.01 * x + (-5.0 if d < 2.0 else 0.0)


def test_tent_taps_are_a_unit_kernel_exact_on_a_plane_and_attenuate_a_sub_cell_pit():
    assert len(tt.AA_TAPS) == 9 and abs(sum(w for _a, _b, w in tt.AA_TAPS) - 1.0) < 1e-12
    assert {(a, b) for a, b, _w in tt.AA_TAPS} == {(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1)}
    plane = {(i, j): 3.0 + 0.7 * i - 0.2 * j for i in range(-3, 4) for j in range(-3, 4)}
    assert abs(tt.aa_value(plane, (0, 0)) - 3.0) < 1e-12 and abs(tt.aa_value(plane, (1, -1)) - 3.9) < 1e-12
    pit = {(i, j): (-4.0 if (i, j) == (0, 0) else 0.0) for i in range(-2, 3) for j in range(-2, 3)}
    assert abs(tt.aa_value(pit, (0, 0)) + 1.0) < 1e-12           # a one-sample pit keeps a quarter of its depth...
    assert abs(tt.aa_value(pit, (1, 0)) + 0.5) < 1e-12           # ...and spreads to the next tap: no lone spike
    assert set(tt.aa_taps([(0, 0), (5, 5)])) == {(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1)} | {
        (5 + a, 5 + b) for a in (-1, 0, 1) for b in (-1, 0, 1)}


def test_antialias_is_opt_in_and_names_the_finest_level_only():
    plain = tt.TierSpec(_terrain(aa=False), ORIGIN)
    assert plain.aa_cell_m is None
    topo = tt.Topology(plain, [([(float(x), 0.0, 0.0) for x in range(-150, 151, 5)], [10.0] * 61)], (),
                       closed_first=False)
    assert topo.aa_keys() == []
    for bad in ({"cell_m": 17.6}, {"cell_m": 4.4, "kernel": "box"}):
        t = _terrain(aa=False)
        t["tier_options"]["antialias"] = bad
        try:
            tt.TierSpec(t, ORIGIN)
        except ValueError as e:
            assert "antialias" in str(e)
        else:
            raise AssertionError(f"antialias {bad} must be refused")
    spec = tt.TierSpec(_terrain(), ORIGIN)
    topo = tt.Topology(spec, [([(float(x), 0.0, 0.0) for x in range(-150, 151, 5)], [10.0] * 61)], (),
                       closed_first=False)
    keys = set(topo.aa_keys())
    assert keys and keys <= set(topo.vkeys)
    L = topo.nlev - 1
    r = topo.r[L]
    fine_corners = {(i * r, j * r) for lev, i, j in topo.leaves if lev == L}
    assert fine_corners <= keys
    coarse_only = set(topo.vkeys) - keys
    assert coarse_only, "the coarse tiers keep their point samples"
    for k in sorted(coarse_only)[:200]:
        cell = topo.locate2(2 * k[0], 2 * k[1])          # the leaf NE of the node: never a finest one
        assert cell is None or cell[0] != L, k


def _seed(d, terrain, dem):
    spec = tt.TierSpec(terrain, ORIGIN)
    lines, _o, _f = ts.road_inputs(d)
    topo = tt.Topology(spec, lines, (), closed_first=False)
    cache = ts.SampleCache(d / "data" / ts.SAMPLES, spec, spec.frame(None))
    for k in set(topo.vkeys) | set(tt.aa_taps(topo.aa_keys())):
        cache.h[k] = round(dem(k[0] * spec.base_m, k[1] * spec.base_m), 2)
    cache.save()
    return topo, cache


def test_sampler_writes_filtered_heights_and_keeps_the_cache_as_points():
    terrain = _terrain()
    d = _project(terrain)
    topo, cache = _seed(d, terrain, _channel)
    ts.run(d, offline=True)
    T = json.loads(gzip.decompress((d / "data" / ts.TIERS).read_bytes()))
    assert T["antialias"]["nodes"] == len(topo.aa_keys()) and T["antialias"]["kernel"] == "tent"
    aa = set(topo.aa_keys())
    moved = 0
    for i, j, h in zip(T["I"], T["J"], T["h"]):
        k = (i, j)
        if k in aa:
            assert abs(h - round(tt.aa_value(cache.h, k), 3)) < 1e-9
            moved += abs(h - cache.h[k]) > 0.05
        else:
            assert h == cache.h[k], "a coarse-tier vertex stays the 3DEP point sample"
    assert moved, "the channel moved finest-level nodes"
    back = ts.SampleCache(d / "data" / ts.SAMPLES, tt.TierSpec(terrain, ORIGIN), tt.TierSpec(terrain, ORIGIN).frame(None))
    assert all(back.h[k] == cache.h[k] for k in list(cache.h)[::37]), "the cache stays point samples"
    # the taps are part of what an offline run needs: without them it stops, it never guesses
    d2 = _project(terrain)
    spec = tt.TierSpec(terrain, ORIGIN)
    c2 = ts.SampleCache(d2 / "data" / ts.SAMPLES, spec, spec.frame(None))
    for k in topo.vkeys:
        c2.h[k] = 100.0
    c2.save()
    try:
        ts.run(d2, offline=True)
    except SystemExit as e:
        assert "no cached 3DEP sample" in str(e)
    else:
        raise AssertionError("missing anti-alias taps must stop an offline run")


def _quad_lattice(n, h):
    """an n x n plain-cell lattice (step 2 base units), triangulated as _triangulate does (SW->NE)"""
    I, J, Y = [], [], []
    idx = {}
    for j in range(n + 1):
        for i in range(n + 1):
            idx[(i, j)] = len(I)
            I.append(2 * i); J.append(2 * j); Y.append(h(i, j))
    tris = []
    for j in range(n):
        for i in range(n):
            sw, se, ne, nw = idx[(i, j)], idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]
            for t in ((sw, se, ne), (sw, ne, nw)):
                tris.append(t)
    return I, J, Y, tris


def _up(t, I, J):
    a, b, c = t
    return (J[b] - J[a]) * (I[c] - I[a]) - (I[b] - I[a]) * (J[c] - J[a]) > 0


def test_data_diagonals_fold_along_the_grain_and_touch_only_eligible_cells():
    # a NW->SE ridge: the planned SW->NE diagonal crosses it in every cell
    I, J, Y, tris = _quad_lattice(6, lambda i, j: 5.0 if i == j else 0.0)
    tris = [t if _up(t, I, J) else (t[0], t[2], t[1]) for t in tris]
    out, n = tt.data_diagonals(tris, I, J, Y, [True] * len(I))
    assert n == 0, "a ridge running SW->NE already lies along the planned diagonal"
    I, J, Y, tris = _quad_lattice(6, lambda i, j: 5.0 if i + j == 6 else 0.0)
    tris = [t if _up(t, I, J) else (t[0], t[2], t[1]) for t in tris]
    out, n = tt.data_diagonals(tris, I, J, Y, [True] * len(I))
    assert n > 0 and len(out) == len(tris)
    assert sorted({v for t in out for v in t}) == sorted({v for t in tris for v in t}), "no vertex added or lost"
    assert all(_up(t, I, J) for t in out), "every triangle stays face-up"
    for k in range(0, len(out), 2):
        a, b = set(out[k]), set(out[k + 1])
        assert a | b == set(tris[k]) | set(tris[k + 1]), "a cell keeps its own four corners"
        u, v = sorted(a & b)
        p, q = sorted((a | b) - (a & b))
        assert abs(Y[u] - Y[v]) <= abs(Y[p] - Y[q]) + 1e-9, "the shared diagonal is the flatter one"
    elig = [False] * len(I)
    out2, n2 = tt.data_diagonals(tris, I, J, Y, elig)
    assert n2 == 0 and out2 == tris, "near-road / kept cells are never touched"
    again, n3 = tt.data_diagonals(out, I, J, Y, [True] * len(I))
    assert n3 == 0 and again == out, "idempotent"


def _write_obj(path, verts, faces, road=None):
    with open(path, "w") as f:
        for x, y, z in verts:
            f.write(f"v {x:.4f} {y:.4f} {z:.4f}\n")
        f.write("o 1GRASS_0\n")
        for a, b, c in faces:
            f.write(f"f {a + 1} {b + 1} {c + 1}\n")
        if road:
            n0 = len(verts)
            for x, y, z in road:
                f.write(f"v {x:.4f} {y:.4f} {z:.4f}\n")
            f.write("o 1ROAD_road\n")
            f.write(f"f {n0 + 1} {n0 + 2} {n0 + 3}\n")


def _rib_project(h, n=40, step=2.5, diag="fixed"):
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    frame = [0.0, 0.0, step, step]
    (d / "data" / "terrain.tiers.json.gz").write_bytes(gzip.compress(json.dumps({"frame": frame}).encode()))
    I, J, Y, tris = _quad_lattice(n, lambda i, j: h(i * 2 * step, j * 2 * step))
    if diag == "data":
        tris, _n = tt.data_diagonals(tris, I, J, Y, [True] * len(I))
    verts = [(i * step, y, j * step) for i, j, y in zip(I, J, Y)]
    road = [(-500.0, 0.0, -500.0), (-499.0, 0.0, -500.0), (-499.0, 0.0, -499.0)]   # far away: all ground counts
    _write_obj(d / "data" / "track.obj", verts, tris, road)
    return d


def test_staircase_ribs_shift_sideways_straight_ridges_do_not():
    rows = [(10, 0, 0, 2, 3.0), (10, 2, 0, 2, 3.0), (10, 4, 0, 2, 3.0),      # a ridge along z: the rib repeats in place
            (20, 0, 0, 2, 3.0), (22, 2, 0, 2, 3.0), (24, 4, 0, 2, 3.0)]      # a slanting channel: it shifts each row
    assert rc.staircase(rows) == [False, False, False, True, True, True]
    assert rc.staircase([(0, 0, 1, 2, 3.0), (2, 0, 1, 2, 3.0)]) == [False, False], "columns pair along x"


def test_rib_check_catches_the_staircase_and_passes_smooth_ground():
    smooth = lambda x, z: 100.0 + 0.05 * x + 3.0 * math.sin(z / 40.0)      # a real hillside: wider than two cells
    rep = rc.run(_rib_project(smooth))
    assert rep["nyquist"]["by_amplitude"][">0.5m"]["beyond_near"] == 0
    assert rep["verdict"] == "PASS", rep
    point = rc.run(_rib_project(_channel), rib_m=1.0, max_ribs=5, max_folds=5)   # the point-sampled channel, fixed diagonal
    assert point["nyquist"]["gated"] > 5 and point["cross_grain"]["gated"] > 5
    assert point["verdict"] == "FAIL"
    # the data-chosen diagonal clears the cross-grain folds on the same heights
    dd = rc.run(_rib_project(_channel, diag="data"), rib_m=1.0, max_ribs=10 ** 6, max_folds=0)
    assert dd["cross_grain"]["gated"] == 0 and dd["cross_grain"]["by_amplitude"][">0.5m"]["beyond_near"] == 0
    assert dd["verdict"] == "PASS"
    # the shipped limits are the module's (fleet/GATES-CHANGELOG.md 2026-10-13)
    assert (rc.RIB_M, rc.MAX_RIBS, rc.FOLD_M, rc.MAX_FOLDS) == (2.0, 100, 1.0, 100)


def test_far_ring_moves_are_held_to_criterion_6s_tolerance():
    """the far ring answers to criterion 6 (each vertex within 1 m of its 3DEP point): there the filter's move is
    bounded by antialias.far_max_move_m; physical ground takes the full filter"""
    terrain = _terrain()
    terrain["tier_options"]["antialias"]["far_max_move_m"] = 0.25
    # a finest-cell patch out in the far ring (as the I-8 corridor is at Lake Murray): x, z 150..250 m
    terrain["include"] = [{"name": "far_patch", "cell_m": 4.4,
                           "bbox_swne": [32.8 + 150 / M_LAT, -117.0 + 150 / M_LON, 32.8 + 250 / M_LAT, -117.0 + 250 / M_LON]}]
    d = _project(terrain)
    # the channel runs everywhere: deep enough that the unbounded filter moves nodes > 0.25 m in both rings
    topo, cache = _seed(d, terrain, lambda x, z: 100.0 + (-5.0 if (abs(z - 0.5 * x - 40.0) < 2.2 or abs(z - 0.5 * x - 90.0) < 2.2) else 0.0))
    ts.run(d, offline=True)
    T = json.loads(gzip.decompress((d / "data" / ts.TIERS).read_bytes()))
    far = {topo.vkeys[v] for t, ph in zip(topo.tris, topo.tri_phys) if not ph for v in t}
    aa = set(topo.aa_keys())
    big_phys = n_far = 0
    for i, j, h in zip(T["I"], T["J"], T["h"]):
        k = (i, j)
        if k not in aa:
            continue
        if k in far:
            n_far += 1
            assert abs(h - cache.h[k]) <= 0.25 + 1e-6
        else:
            big_phys += abs(h - cache.h[k]) > 0.25 + 1e-6
    assert n_far and big_phys, "finest nodes in both rings; the physical ground takes the full filter"
    assert T["antialias"]["far_max_move_m"] == 0.25 and T["antialias"]["far_nodes_bounded"] > 0
