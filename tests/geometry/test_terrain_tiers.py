"""scripts/geometry/terrain_tiers.py — ledger 0046's tiered terrain (E1 tiering + far ring, E2 distance-weighted
clamp, E3 balanced tiling, E4 corridor tier): opt-in, tiers by pavement distance, 2:1 balanced and watertight,
face-up, x_split cells split in four, the physical/far partition (pockets enclosed by physical ground are
physical), balanced tiles under the cap where equal-width bands are not, the corridor carrying cut AND fill from the
data; the heightfield frame + KEPT cells (the graded grid's own triangles under and beside the roads, its finer
neighbours' nodes on their edges = T-junctions the prep welds without moving the surface). A synthetic 2 x 2 km
box, an 800 m road; no network."""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.geometry import terrain_tiers as tt  # noqa: E402

ORIGIN = {"lon": -117.0, "lat": 32.8, "elev_m": 100.0}
M_LON, M_LAT = tt.meters_per_degree(32.8)


def _box(half=1000.0):
    return [32.8 - half / M_LAT, -117.0 - half / M_LON, 32.8 + half / M_LAT, -117.0 + half / M_LON]


def _spec(**kw):
    t = {"terrain_band_m": 22.0,
         "tiers": [{"within_m": 60.0, "cell_m": 4.4, "x_split": True}, {"within_m": 300.0, "cell_m": 17.6},
                   {"cell_m": 52.8}],
         "tier_options": {"physical_within_m": 150.0},
         "far_extent": {"bbox_swne": _box()}}
    t.update(kw)
    return tt.TierSpec(t, ORIGIN)


ROAD = [([(float(x), 0.0, 0.0) for x in range(-400, 401, 5)], [10.0] * 161)]   # E-W, 10 m wide, open


def _topo(spec=None, roads=ROAD, corridors=(), closed=False):
    return tt.Topology(spec or _spec(), roads, corridors, closed_first=closed)


def _pav(x, z):
    """pavement distance from the test road"""
    dx = max(-400.0 - x, 0.0, x - 400.0)
    return math.hypot(dx, z) - 5.0


def _rect_pav(spec, L, i, j):
    c = spec.levels[L]
    xa, xb, za, zb = i * c, (i + 1) * c, j * c, (j + 1) * c
    dx = max(-400.0 - xb, 0.0, xa - 400.0)
    dz = max(za, 0.0, -zb)
    return math.hypot(dx, dz) - 5.0


def test_opt_in_only():
    assert not tt.TierSpec(None).enabled
    assert not tt.TierSpec({"terrain_band_m": 22.0, "terrain_max_grade": 0.35}).enabled
    s = _spec()
    assert s.enabled and s.levels == [52.8, 17.6, 4.4] and s.ratios == [3, 4] and s.r == [24, 8, 2]
    try:
        tt.TierSpec({"tiers": [{"within_m": 60, "cell_m": 5.0}, {"cell_m": 17.6}], "far_extent": {"bbox_swne": _box()}})
    except ValueError as e:
        assert "nest" in str(e)
    else:
        raise AssertionError("cells that do not nest by an integer ratio must be refused")


def test_cells_follow_pavement_distance():
    spec = _spec()
    topo = _topo(spec)
    seen = set()
    for L, i, j in topo.leaves:
        c = spec.levels[L]
        seen.add(c)
        d = _rect_pav(spec, L, i, j)
        if d <= 60.0:
            assert c == 4.4, (c, d)
        if d <= 300.0:
            assert c <= 17.6, (c, d)
        if c == 4.4:
            assert d <= 60.0 + 17.6 * math.sqrt(2), d       # fine only where a 17.6 parent touches the 60 m band
    assert seen == {4.4, 17.6, 52.8}


def _edges(topo):
    cnt = {}
    for t in topo.tris:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            k = (min(a, b), max(a, b))
            cnt[k] = cnt.get(k, 0) + 1
    return cnt


def test_balanced_watertight_face_up():
    spec = _spec()
    topo = _topo(spec)
    # 2:1 balance: no edge neighbour more than one level apart
    for k in topo.leaves:
        for _d, X2, Z2 in topo._edge_probes(*k):
            nb = topo.locate2(X2, Z2)
            assert nb is None or abs(nb[0] - k[0]) <= 1, (k, nb)
    # every interior edge has exactly two triangles (no T-junction crack); open edges only on the domain rim
    R0 = topo.r[0]
    d0, e0, d1, e1 = topo.dom
    rim_x, rim_z = {d0 * R0, (d1 + 1) * R0}, {e0 * R0, (e1 + 1) * R0}
    for (a, b), n in _edges(topo).items():
        assert n in (1, 2), n
        if n == 1:
            (ia, ja), (ib, jb) = topo.vkeys[a], topo.vkeys[b]
            assert (ia == ib and ia in rim_x) or (ja == jb and ja in rim_z), (topo.vkeys[a], topo.vkeys[b])
    # face-up in the left-handed local frame (n_y > 0), nothing degenerate
    for t in topo.tris:
        (x0, z0), (x1, z1), (x2, z2) = (topo.xz(v) for v in t)
        ny = (z1 - z0) * (x2 - x0) - (x1 - x0) * (z2 - z0)
        assert ny > 1e-6, t


def test_x_split_cells_split_in_four_and_fine_edges_short():
    spec = _spec()
    topo = _topo(spec)
    longest = {}
    for t in topo.tris:
        p = [topo.xz(v) for v in t]
        cx, cz = sum(q[0] for q in p) / 3, sum(q[1] for q in p) / 3
        e = max(math.dist(p[0], p[1]), math.dist(p[1], p[2]), math.dist(p[2], p[0]))
        d = _pav(cx, cz)
        band = "verge" if d <= 50.0 else None
        if band:
            longest.setdefault(band, []).append(e)
        band = "15-60" if 15.0 <= d <= 60.0 else ("60-300" if 60.0 < d <= 300.0 else None)
        if band:
            longest.setdefault(band, []).append(e)
    assert max(longest["verge"]) <= 4.4 + 1e-6              # x_split: the side, not the 6.2 m diagonal
    q = sorted(longest["15-60"])
    assert q[int(0.9 * len(q))] <= 7.0                       # criterion 5 near band: p90 <= 7 m
    q = sorted(longest["60-300"])
    assert q[int(0.9 * len(q))] <= 28.3                      # criterion 5 medium band


def test_far_ring_partition_and_enclosed_pockets_are_physical():
    spec = _spec()
    topo = _topo(spec)
    for t, p in zip(topo.tris, topo.tri_phys):
        cx = sum(topo.xz(v)[0] for v in t) / 3
        cz = sum(topo.xz(v)[1] for v in t) / 3
        if p:
            assert _pav(cx, cz) <= 150.0 + 17.6 * 1.5, (cx, cz)
        else:
            assert _pav(cx, cz) >= 150.0 - 1e-6, (cx, cz)
    assert any(topo.tri_phys) and not all(topo.tri_phys)
    # a closed square loop 600 m on a side: its middle is 300 m from any pavement (> physical 150) but enclosed
    sq = [(-300.0 + k, 0.0, -300.0) for k in range(0, 600, 5)] + [(300.0, 0.0, -300.0 + k) for k in range(0, 600, 5)] \
        + [(300.0 - k, 0.0, 300.0) for k in range(0, 600, 5)] + [(-300.0, 0.0, 300.0 - k) for k in range(0, 600, 5)]
    t2 = tt.Topology(spec, [(sq, [10.0] * len(sq))], (), closed_first=True)
    centre = [p for t, p in zip(t2.tris, t2.tri_phys) if all(abs(c) < 60 for v in t for c in t2.xz(v))]
    assert centre and all(centre), "the pocket inside the loop is physical ground (the lake / the hill inside it)"
    corner = [p for t, p in zip(t2.tris, t2.tri_phys) if all(c > 900 for v in t for c in t2.xz(v))]
    assert corner and not any(corner), "the outside beyond physical_within_m is the far ring"


def test_balanced_tiles_stay_under_the_cap_where_equal_bands_do_not():
    topo = _topo()
    cap = 1500
    tiles = tt.balanced_tiles(topo.tris, topo.xz, cap)
    assert sorted(t for tile in tiles for t in tile) == sorted(topo.tris)
    assert all(len({v for t in tile for v in t}) <= cap for tile in tiles)
    # the prep's old rule: K = n // cap + 1 equal-width bands along x — the fine road band lands in few of them
    n = len(topo.vkeys)
    K = n // cap + 1
    xs = [topo.xz(i)[0] for i in range(n)]
    lo, span = min(xs), max(xs) - min(xs)
    bands = [set() for _ in range(K)]
    for t in topo.tris:
        cx = sum(topo.xz(v)[0] for v in t) / 3
        bands[min(K - 1, int((cx - lo) / span * K))].update(t)
    assert max(len(b) for b in bands) > cap, "equal-width bands overflow on tiered density (why the split changed)"
    # engine-july's prep carries the same rule (balanced_face_tiles, pure, in the snapshot of record)
    p = ROOT / "tracks" / "san-diego-lake-murray" / "engine-july-snapshot" / "scripts" / "ac" / "build_kn5_loop.py"
    spec = importlib.util.spec_from_file_location("_bkl_snapshot", p)
    bkl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bkl)
    assert bkl.TERRAIN_TILES == ("1GRASS", "GRASS_FAR")
    cents = [(sum(topo.xz(v)[0] for v in t) / 3, sum(topo.xz(v)[1] for v in t) / 3) for t in topo.tris]
    groups = bkl.balanced_face_tiles(cents, topo.tris, cap)
    assert sorted(f for g in groups for f in g) == list(range(len(topo.tris)))
    assert all(len({v for f in g for v in topo.tris[f]}) <= cap for g in groups)


def test_distance_weighted_band_clamp():
    w = [tt.clamp_weight(d, 80.0, 250.0) for d in (0.0, 79.0, 80.0, 165.0, 249.0, 250.0, 2000.0)]
    assert w[0] == w[1] == w[2] == 1.0 and abs(w[3] - 0.5) < 1e-9 and 0.0 < w[4] < 0.01 and w[5] == w[6] == 0.0
    road_y, band = 100.0, 22.0
    assert tt.band_clamp_value(300.0, road_y, band, 1.0) == 122.0      # near a road: held to road + band
    assert tt.band_clamp_value(40.0, road_y, band, 1.0) == 78.0         # ... and road - band
    assert tt.band_clamp_value(300.0, road_y, band, 0.0) == 300.0      # Cowles, 1.6 km out: the data
    assert tt.band_clamp_value(300.0, road_y, band, 0.5) == 211.0
    assert tt.band_clamp_value(110.0, road_y, band, 1.0) == 110.0      # inside the band: untouched
    k = [tt.keep_weight(d, 20.0, 16.0) for d in (0.0, 20.0, 28.0, 36.0, 50.0)]
    assert k[0] == k[1] == 1.0 and abs(k[2] - 0.5) < 1e-9 and k[3] == k[4] == 0.0


def _surface(topo, H):
    """(x, z) -> height of the triangulated surface carrying per-vertex heights H"""
    def h(x, z):
        for t in topo.tris:
            (ax, az), (bx, bz), (cx, cz) = (topo.xz(v) for v in t)
            det = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
            l1 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / det
            l2 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / det
            l3 = 1 - l1 - l2
            if min(l1, l2, l3) >= -1e-9:
                return l1 * H[t[0]] + l2 * H[t[1]] + l3 * H[t[2]]
        return None
    return h


def test_corridor_tier_carries_cut_and_fill_from_the_data():
    """E4: a freeway corridor (N-S at x = 818, far from the road) in a 10 m-deep cut south of z = 0 and on an 8 m
    fill north of it. Without the corridor tier the 52.8 m lattice has no node in the 24 m-wide feature and the
    built ground reads neither; with it every vertex is the DEM at that vertex, so the surface goes DOWN into the
    cut and UP onto the fill — raising as well as lowering, from the data, not from a lower-only cutter."""
    def dem(x, z):
        if abs(x - 818.0) < 12.0:
            return 90.0 if z < 0 else 108.0
        return 100.0
    line = [(818.0, 0.0, float(z)) for z in range(-900, 901, 10)]
    plain = _topo()
    cor = _topo(_spec(corridors=[{"name": "fwy", "half_width_m": 40.0, "cell_m": 8.8}]), corridors=[line])
    assert 8.8 in {cor.spec.levels[L] for L, _i, _j in cor.leaves}
    for topo, expect in ((plain, False), (cor, True)):
        H = [dem(*topo.xz(i)) for i in range(len(topo.vkeys))]
        s = _surface(topo, H)
        cut, fill = s(818.0, -400.0), s(818.0, 400.0)
        if expect:
            assert abs(cut - 90.0) < 0.5 and abs(fill - 108.0) < 0.5, (cut, fill)
        else:
            assert cut > 97.0 and fill < 103.0, (cut, fill)


def test_deterministic():
    a, b = _topo(), _topo()
    assert a.vkeys == b.vkeys and a.tris == b.tris and a.tri_phys == b.tri_phys


def _meta(half=1000.0, sp=40.0):
    """a heightfield meta whose grid covers the test box (row 0 = north), as scripts.elevation.heightfield writes"""
    s, w, n, e = _box(half)
    midlat = (s + n) / 2
    gy, gx = sp / 111_000.0, sp / (111_000.0 * math.cos(math.radians(midlat)))
    return {"bbox_swne": [s, w, n, e], "nx": int((e - w) / gx) + 1, "ny": int((n - s) / gy) + 1, "spacing_m": sp,
            "row0": "north"}


def _kept_spec():
    return _spec(tiers=[{"within_m": 60.0, "cell_m": 5.0, "x_split": True}, {"within_m": 300.0, "cell_m": 20.0,
                                                                              "x_split": True}, {"cell_m": 40.0}],
                 tier_options={"physical_within_m": 150.0, "frame": {"kind": "heightfield", "upsample": 2},
                               "keep_cells": {"cell_m": 20.0, "within_m": 18.0}})


def test_heightfield_frame_puts_the_graded_grid_on_the_lattice():
    meta = _meta()
    spec = _kept_spec()
    fr = spec.frame(meta)
    # build_loop_blend.project_grid on the x2-upsampled grid: node (row j, col i)
    s, w, n, e = meta["bbox_swne"]
    sp = 20.0
    midlat = (s + n) / 2
    gy, gx = sp / 111_000.0, sp / (111_000.0 * math.cos(math.radians(midlat)))
    for j, i in ((0, 0), (3, 7), (40, 12)):
        x = (w + i * gx - ORIGIN["lon"]) * M_LON
        z = (n - j * gy - ORIGIN["lat"]) * M_LAT
        I, J = 8 * i, -8 * j                                   # 8 base units per 20 m cell, rows run south
        assert abs(fr.x0 + I * fr.ux - x) < 1e-9 and abs(fr.z0 + J * fr.uz - z) < 1e-9
    try:
        tt.TierSpec({"tiers": [{"within_m": 60, "cell_m": 6.0}, {"cell_m": 24.0}],
                     "tier_options": {"frame": {"kind": "heightfield", "upsample": 2}},
                     "far_extent": {"bbox_swne": _box()}}, ORIGIN).frame(meta)
    except ValueError as err:
        assert "must be one of the tier cells" in str(err)
    else:
        raise AssertionError("a lattice whose cells do not include the grid's own cell cannot anchor on it")


def test_kept_cells_are_the_graded_grids_own_triangles():
    meta = _meta()
    spec = _kept_spec()
    fr = spec.frame(meta)
    topo = tt.Topology(spec, ROAD, (), closed_first=False, frame=fr)
    kept = [k for k in topo.leaves if topo.is_keep(k)]
    assert kept and all(spec.levels[k[0]] == 20.0 for k in kept)
    # every cell of the grid within 18 m of the pavement is kept (a leaf, never split)
    for (_L, i, j) in kept:
        xa, xb = fr.x0 + i * 8 * fr.ux, fr.x0 + (i + 1) * 8 * fr.ux
        za, zb = fr.z0 + j * 8 * fr.uz, fr.z0 + (j + 1) * 8 * fr.uz
        dx = max(-400.0 - xb, 0.0, xa - 400.0)
        dz = max(za, 0.0, -zb)
        assert math.hypot(dx, dz) - 5.0 <= 18.0 + 1e-6
    index = {k: n for n, k in enumerate(topo.vkeys)}
    tris = set(topo.tris)
    for (L, i, j) in kept:
        r = topo.r[L]
        a, b = index[(i * r, (j + 1) * r)], index[((i + 1) * r, (j + 1) * r)]      # NW, NE
        c, d = index[((i + 1) * r, j * r)], index[(i * r, j * r)]                  # SE, SW
        assert (a, b, c) in tris and (a, c, d) in tris, "ribbon.grass_terrain's (a, b, c) + (a, c, d), same order"
        for v in (a, b, c, d):
            assert topo.vkeep[v]
    # the finer neighbours' nodes on kept edges are flagged kept (they take the graded height) and are T-junctions:
    # collinear with the kept edge, not connected to it
    edges = _edges(topo)
    t_nodes = [n for n, k in enumerate(topo.vkeys) if topo.vkeep[n] and k[0] % 8 and k[1] % 8 == 0
               or topo.vkeep[n] and k[1] % 8 and k[0] % 8 == 0]
    assert t_nodes, "5 m cells beside the kept band leave nodes on its edges"
    one_sided = [k for k, n in edges.items() if n == 1]
    assert one_sided, "the kept band's outer edges carry T-junctions until the prep welds them"
    # the prep's welder finds exactly those, on the BUILT positions (engine-july snapshot, pure)
    p = ROOT / "tracks" / "san-diego-lake-murray" / "engine-july-snapshot" / "scripts" / "ac" / "build_kn5_loop.py"
    sp_ = importlib.util.spec_from_file_location("_bkl_snapshot2", p)
    bkl = importlib.util.module_from_spec(sp_)
    sp_.loader.exec_module(bkl)
    co = [(topo.xz(n)[0], topo.xz(n)[1], 0.0) for n in range(len(topo.vkeys))]       # Blender (x, y=N, z=up)
    rim = set()
    R0 = topo.r[0]
    d0, e0, d1, e1 = topo.dom
    for (a, b), n in edges.items():
        (ia, ja), (ib, jb) = topo.vkeys[a], topo.vkeys[b]
        if (ia == ib and ia in (d0 * R0, (d1 + 1) * R0)) or (ja == jb and ja in (e0 * R0, (e1 + 1) * R0)):
            rim.add((a, b))
    hits = bkl.t_junctions(co, [e for e in one_sided if e not in rim])
    assert {v for _e, v, _t in hits} == set(t_nodes)
    assert all(0 < t < 1 for _e, _v, t in hits)


def test_t_junction_finder_is_exact():
    p = ROOT / "tracks" / "san-diego-lake-murray" / "engine-july-snapshot" / "scripts" / "ac" / "build_kn5_loop.py"
    sp_ = importlib.util.spec_from_file_location("_bkl_snapshot3", p)
    bkl = importlib.util.module_from_spec(sp_)
    sp_.loader.exec_module(bkl)
    co = [(0, 0, 0), (20, 0, 2), (5, 0, 0.5), (10, 0, 1.0), (15, 0.005, 1.5), (10, 0, 1.3), (10, 5, 1.0),
          (12, 0, 1.2), (12, -6, 1.2), (12, 6, 1.2)]
    hits = bkl.t_junctions(co, [(0, 1), (0, 2), (2, 3), (3, 4), (5, 6), (8, 7), (7, 9)], tol=0.01)
    assert sorted((e, v, round(t, 3)) for e, v, t in hits) == [(0, 2, 0.25), (0, 3, 0.5), (0, 4, 0.75)]
    # vertex 7 sits exactly on edge 0's line but its own boundary runs ACROSS it (a hole's rim, not a T): left alone
