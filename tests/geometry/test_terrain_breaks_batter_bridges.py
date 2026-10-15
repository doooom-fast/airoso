"""Ledger 0046 fix round 4 (the truth and visual lenses refuted round 3):

* BREAK LINES — a sharp riser (a cut-slope bench, a drainage ledge) crossing the 5 m lattice at a slant was drawn as a
  staircase whatever the node heights (the washboard west of College, ~8 degrees off the lattice x axis). terrain_tiers'
  break-line helpers put 3DEP points ON the edges a riser crosses and triangulate the cell through them; the sampler
  wires them (half-metre profiles cached as fine samples, opt-in by tier_options.breaks); the result is watertight.
* STEP JOGS — tools/rib_check.py follows each riser across scan lines through the BUILT triangles and counts the places
  where it jumps a whole row while otherwise drifting slowly: a staircase is caught, a straight slanting riser is not.
* BATTER FEATHER — past criterion 7's 20 m the graded ground returns to 3DEP within an earth batter's run of the gap
  between them (keep_batter), not a fixed 16 m: the assembler and the engine-july prep agree.
* BRIDGE BODIES — tools/author_bridges_blend.py: visual only, concrete, its UVs kept, run by both chains after the
  mouths gap; its pure helpers behave.
No network, no Blender."""
from __future__ import annotations

import gzip
import importlib.util
import json
import math
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.elevation import terrain_sample as ts  # noqa: E402
from scripts.geometry import terrain_tiers as tt  # noqa: E402

SNAP = ROOT / "tracks" / "san-diego-lake-murray" / "engine-july-snapshot" / "scripts" / "ac"
ORIGIN = {"lon": -117.0, "lat": 32.8, "elev_m": 100.0}
M_LON, M_LAT = tt.meters_per_degree(32.8)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rc = _load("rib_check_r4", ROOT / "tools" / "rib_check.py")


# --- break lines: the pure helpers ----------------------------------------------------------------------------------
def test_edge_fine_keys_run_strictly_inside_the_edge_in_order():
    k = tt.edge_fine_keys((4, 6), (6, 6))
    assert k == [(20 + i, 30) for i in range(1, 10)]
    k = tt.edge_fine_keys((4, 6), (4, 8))
    assert k == [(20, 30 + i) for i in range(1, 10)] and len(k) == 2 * tt.BREAK_FINE - 1


def test_edge_screen_reads_edges_that_climb_a_riser_not_ones_that_run_along_it():
    # a riser along x at z = 0.6 base units (between rows J = 0 and J = 2), 5 m tall
    h = {(i, j): (5.0 if j >= 1 else 0.0) for i in range(-2, 6) for j in range(-2, 6)}
    assert tt.edge_screen(h, (0, 0), (0, 2), 0.25) is True        # climbs it
    assert tt.edge_screen(h, (0, 0), (2, 0), 0.25) is False       # runs along it
    flat = {k: 0.3 * k[0] - 0.1 * k[1] for k in h}
    assert tt.edge_screen(flat, (0, 0), (0, 2), 0.25) is False     # a plane: nothing to read
    assert tt.edge_screen({}, (0, 0), (0, 2), 0.25) is False       # never guessed


def test_edge_breaks_find_the_top_and_foot_of_a_riser_and_nothing_on_a_plane():
    prof = [0.0, 0.0, 0.0, 0.0, 2.5, 5.0, 5.0, 5.0, 5.0]           # fine points 1..9 of a 5 m edge
    br = tt.edge_breaks(prof, 0.0, 5.0, 5.0, 0.4, 3, 0.75)
    ks = [k for k, _h in br]
    assert 2 <= len(br) <= 3 and min(ks) <= 5 <= max(ks), br
    assert all(abs(k1 - k2) * 0.5 >= 0.75 - 1e-9 for k1 in ks for k2 in ks if k1 != k2)
    plane = [0.5 * k for k in range(1, 10)]
    assert tt.edge_breaks(plane, 0.0, 5.0, 5.0, 0.4, 3, 0.75) == []


def _area(p, t):
    (ax, az), (bx, bz), (cx, cz) = (p[t[0]][:2], p[t[1]][:2], p[t[2]][:2])
    return abs((bx - ax) * (cz - az) - (cx - ax) * (bz - az)) / 2.0


def test_triangulate_cell_runs_the_riser_straight_through_the_cell():
    # a 5 m cell; the riser's top crosses W at z 2.0 and E at z 3.0 (points on the edges), its foot below
    poly = [(0.0, 0.0, 0.0), (5.0, 0.0, 0.0), (5.0, 2.5, 0.0), (5.0, 3.0, 5.0), (5.0, 5.0, 5.0), (0.0, 5.0, 5.0),
            (0.0, 2.0, 5.0), (0.0, 1.5, 0.0)]
    samples = []
    for i in range(6):
        for j in range(6):
            x, z = i, j
            top = 2.0 + 0.2 * x
            samples.append((x, z, 5.0 if z >= top else (0.0 if z <= top - 0.5 else 5.0 * (z - top + 0.5) / 0.5)))
    tri = tt.triangulate_cell(poly, samples)
    assert len(tri) == len(poly) - 2
    assert abs(sum(_area(poly, t) for t in tri) - 25.0) < 1e-6, "the triangles tile the cell"
    assert all(_area(poly, t) > 1e-4 for t in tri), "no triangle on three collinear points"
    edges = {tuple(sorted((t[a], t[(a + 1) % 3]))) for t in tri for a in range(3)}
    assert (3, 6) in edges and (2, 7) in edges, "the riser's top and foot are triangle edges across the cell"
    up = [tt.face_up_xz([q[:2] for q in poly], *t) for t in tri]
    for a, b, c in up:
        dx1, dz1 = poly[b][0] - poly[a][0], poly[b][1] - poly[a][1]
        dx2, dz2 = poly[c][0] - poly[a][0], poly[c][1] - poly[a][1]
        assert dz1 * dx2 - dx1 * dz2 > 0


# --- break lines: the sampler, end to end ---------------------------------------------------------------------------
def _terrain(breaks=True):
    half = 300.0
    t = {"terrain_band_m": 22.0,
         "tiers": [{"within_m": 60.0, "cell_m": 4.4}, {"within_m": 120.0, "cell_m": 17.6}, {"cell_m": 52.8}],
         "tier_options": {"physical_within_m": 80.0,
                          **({"breaks": {"beyond_m": 20.0, "screen_m": 0.25, "tol_m": 0.4, "max_per_edge": 3,
                                         "min_spacing_m": 0.75}} if breaks else {})},
         "far_extent": {"bbox_swne": [32.8 - half / M_LAT, -117.0 - half / M_LON, 32.8 + half / M_LAT,
                                      -117.0 + half / M_LON]}}
    return t


def _riser(x, z):
    """a 5 m bench riser ~1 m wide running 8 degrees off the x axis, 35 m north of the road, on a 2 % slope"""
    zr = 35.0 + math.tan(math.radians(8.0)) * x
    u = (z - zr) / 1.0
    return 100.0 + 0.02 * z + (5.0 if u >= 0.5 else (0.0 if u <= -0.5 else 5.0 * (u + 0.5)))


def _project(terrain):
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "loop": False, "terrain": terrain}))
    pts = [[float(x), 0.0, 0.0] for x in range(-150, 151, 5)]
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": pts, "widths_m": [10.0] * len(pts), "origin": ORIGIN}))
    return d


def _seeded(terrain):
    d = _project(terrain)
    spec = tt.TierSpec(terrain, ORIGIN)
    lines, _o, _f = ts.road_inputs(d)
    frame = spec.frame(None)
    topo = tt.Topology(spec, lines, (), closed_first=False, frame=frame)
    cache = ts.SampleCache(d / "data" / ts.SAMPLES, spec, frame)
    keys = set(topo.vkeys)
    for i, j in list(keys):
        keys.update((i + a, j + b) for a in (-1, 0, 1) for b in (-1, 0, 1))
    for k in keys:
        cache.h[k] = round(_riser(k[0] * spec.base_m, k[1] * spec.base_m), 2)
    if spec.breaks:
        cells, edges = ts.plan_breaks(topo, spec, frame, lines, False, cache.h)
        q = float(tt.BREAK_FINE)
        for a, b in edges:
            for f in tt.edge_fine_keys(a, b):
                cache.fine[f] = round(_riser(f[0] / q * spec.base_m, f[1] / q * spec.base_m), 2)
    cache.save()
    return d, topo


def test_breaks_are_opt_in():
    d, _topo = _seeded(_terrain(breaks=False))
    ts.run(d, offline=True)
    T = json.loads(gzip.decompress((d / "data" / ts.TIERS).read_bytes()))
    assert "break" not in T


def test_sampler_draws_the_riser_through_edge_points_watertight():
    d, topo = _seeded(_terrain())
    ts.run(d, offline=True)
    T = json.loads(gzip.decompress((d / "data" / ts.TIERS).read_bytes()))
    B = T["break"]
    assert B["break_cells"] > 5 and len(B["h"]) > 5 and B["edges_read"] >= B["break_cells"] // 2
    x0, z0, ux, uz = T["frame"]
    q = float(B["fine"])
    P = [(x0 + i * ux, z0 + j * uz) for i, j in zip(T["I"], T["J"])]
    n_lat = len(P)
    P += [(x0 + i / q * ux, z0 + j / q * uz) for i, j in zip(B["I5"], B["J5"])]
    tris = [tuple(T["tris"][3 * k:3 * k + 3]) for k in range(len(T["tris"]) // 3)]
    assert all(0 <= v < len(P) for t in tris for v in t)
    # every extra vertex is 3DEP (smoothed) at its own position, and lies on the riser band's edge region
    for (x, z), h in zip(P[n_lat:], B["h"]):
        assert abs(h - _riser(x, z)) < 2.6
    # watertight: an edge is shared by at most two triangles, and no vertex sits inside another triangle's edge
    cnt = {}
    for t in tris:
        for a in range(3):
            e = tuple(sorted((t[a], t[(a + 1) % 3])))
            cnt[e] = cnt.get(e, 0) + 1
    assert max(cnt.values()) <= 2
    on = {}
    for v in range(n_lat, len(P)):
        on[(round(P[v][0], 3), round(P[v][1], 3))] = v
    for (a, b), _n in cnt.items():
        if a >= n_lat or b >= n_lat:
            continue
        (ax, az), (bx, bz) = P[a], P[b]
        for (vx, vz), v in on.items():
            if min(ax, bx) - 1e-6 <= vx <= max(ax, bx) + 1e-6 and min(az, bz) - 1e-6 <= vz <= max(az, bz) + 1e-6:
                cr = (bx - ax) * (vz - az) - (bz - az) * (vx - ax)
                inside = (vx - ax) * (bx - ax) + (vz - az) * (bz - az)
                L2 = (bx - ax) ** 2 + (bz - az) ** 2
                assert not (abs(cr) < 1e-6 and 1e-6 < inside < L2 - 1e-6), f"T-junction: {v} on {a}-{b}"
    # every triangle face-up
    for a, b, c in tris:
        dx1, dz1 = P[b][0] - P[a][0], P[b][1] - P[a][1]
        dx2, dz2 = P[c][0] - P[a][0], P[c][1] - P[a][1]
        assert dz1 * dx2 - dx1 * dz2 > 0


def test_an_offline_run_without_the_profiles_stops():
    terrain = _terrain()
    d, _topo = _seeded(terrain)
    spec = tt.TierSpec(terrain, ORIGIN)
    c = ts.SampleCache(d / "data" / ts.SAMPLES, spec, spec.frame(None))
    c.fine.clear()
    c.save()
    try:
        ts.run(d, offline=True)
    except SystemExit as e:
        assert "break-line profile" in str(e)
    else:
        raise AssertionError("missing break-line profiles must stop an offline run")


# --- step jogs ------------------------------------------------------------------------------------------------------
def _mesh(nodes_xz, h, cell=5.0, n=40):
    """a plain n x n lattice of ``cell`` m (frame x0 = z0 = 0, base unit cell / 2), SW->NE diagonals"""
    V, idx = [], {}
    for j in range(n + 1):
        for i in range(n + 1):
            idx[(i, j)] = len(V)
            V.append((i * cell, h(i * cell, j * cell), j * cell))
    T = []
    for j in range(n):
        for i in range(n):
            sw, se, ne, nw = idx[(i, j)], idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]
            T += [(sw, se, ne), (sw, ne, nw)]
    return V, T, [0.0, 0.0, cell / 2.0, cell / 2.0]


def test_step_jogs_catch_an_aliased_slanting_riser():
    slope = math.tan(math.radians(8.0))

    def aliased(x, z):                     # the riser snapped between two rows of nodes: a staircase
        return 5.0 if z > 60.0 + slope * x else 0.0
    V, T, fr = _mesh(None, aliased)
    jogs = rc.step_jogs(rc.scan_profiles(V, T, fr), fr)
    assert len(jogs) >= 3


def test_step_jogs_pass_a_riser_drawn_straight():
    # the same riser drawn at 0.5 m (what a break line gives: its top and foot follow the slant) and on a plane
    slope = math.tan(math.radians(8.0))

    def sharp(x, z):
        u = z - (60.0 + slope * x)
        return 5.0 if u >= 0.5 else (0.0 if u <= -0.5 else 5.0 * (u + 0.5))
    V, T, fr = _mesh(None, sharp, cell=0.5, n=400)
    fr = [0.0, 0.0, 2.5, 2.5]                                     # scan every 5 m, as on the build
    big = [t for t in T]
    jogs = rc.step_jogs(rc.scan_profiles(V, big, fr), fr)
    assert jogs == []
    V, T, fr = _mesh(None, lambda x, z: 0.3 * x + 0.1 * z)
    assert rc.step_jogs(rc.scan_profiles(V, T, fr), fr) == []


# --- the batter feather ---------------------------------------------------------------------------------------------
def test_feather_len_is_an_earth_batter_held_between_its_bounds_and_both_engines_agree():
    assert tt.feather_len(3.9, 16.0, None, 8.0) == 16.0                 # opt-in: no batter -> the fixed feather
    assert abs(tt.feather_len(3.9, 16.0, 3.5, 8.0) - 13.65) < 1e-9
    assert abs(tt.feather_len(-3.9, 16.0, 3.5, 8.0) - 13.65) < 1e-9
    assert tt.feather_len(0.3, 16.0, 3.5, 8.0) == 8.0
    assert tt.feather_len(20.0, 16.0, 3.5, 8.0) == 16.0
    # never steeper than 1.5 / batter, and never steeper than the fixed blend where that one was already steeper
    for dl in (0.5, 2.0, 2.3, 3.0, 4.6, 6.0, 9.0):
        L = tt.feather_len(dl, 16.0, 3.5, 8.0)
        assert 1.5 * dl / L <= max(1.5 / 3.5, 1.5 * dl / 16.0) + 1e-9
    blend = (ROOT / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "blender" / "build_loop_blend.py").read_text(
        encoding="utf-8")
    assert "tt.feather_len(" in blend and '"keep_batter": batter' in blend and '"L": nL' in blend
    cfg = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json").read_text(encoding="utf-8"))
    o = cfg["terrain"]["tier_options"]
    assert o["keep_batter"] == 3.5 and o["keep_feather_min_m"] == 8.0 and o["keep_feather_m"] == 16.0
    # at the truth lens's s 3800 south rim: graded ground 3.9 m over 3DEP, 29.0 m from the data's pavement
    w16 = tt.keep_weight(29.04, 20.0, 16.0)
    wb = tt.keep_weight(29.04, 20.0, tt.feather_len(3.93, 16.0, 3.5, 8.0))
    assert w16 * 3.93 > 1.55 and wb * 3.93 < 1.1      # (over the clamped 3DEP D; fresh 3DEP reads 0.31 m lower)


def test_snapshot_refine_field_takes_the_feather_length_per_node():
    bkl = _load("_bkl_batter", SNAP / "build_kn5_loop.py")
    R = {"frame": [0.0, 0.0, 2.5, 2.5], "keep_r": 8, "cell_r": 2, "kept_cells": [[0, 0]], "cells": [[0, 0]],
         "I": [0, 2, 2, 0, 1], "J": [0, 0, 2, 2, 1], "D": [0.0] * 5, "d": [26.0] * 5,
         "keep_m": 20.0, "keep_feather_m": 16.0, "edge_m": 5.5, "move_beyond_m": 20.0, "min_face_d_m": 12.0}
    old = bkl.RefineField(R).target(1.0, 1.0, 4.5)
    L = 9.0
    new = bkl.RefineField(dict(R, keep_batter=3.5, keep_feather_min_m=8.0, L=[L] * 5)).target(1.0, 1.0, 4.5)
    assert old > 2.0 and new < 1.5 and abs(new - tt.keep_weight(26.0, 20.0, 9.0) * 4.5) < 1e-9


# --- bridge bodies --------------------------------------------------------------------------------------------------
def _bridge_tool():
    for name in ("bpy", "mathutils", "mathutils.bvhtree"):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules["mathutils"].Vector = lambda v: v
    sys.modules["mathutils.bvhtree"].BVHTree = object
    return _load("_author_bridges", ROOT / "tools" / "author_bridges_blend.py")


def test_bridge_bodies_are_visual_only_and_concrete():
    from scripts.ac import ext_config, kn5_ground_check, pbr, verify_kn5
    from scripts.geometry import drive_test
    name = "BRIDGESTRUCT_1"
    assert not name[0].isdigit()
    for prefixes in (drive_test.DRIVABLE, drive_test.SOFT, verify_kn5.DRIVABLE, kn5_ground_check.BUCKETS,
                     ("1ROAD_MAIN", "1ROAD", "1GRASS", "HWYSTRUCT", "1WALL", "1KERB", "HOUSE", "BUILDING")):
        assert not name.upper().startswith(tuple(prefixes))
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "lighting": {"grassfx": True}}))
    (d / "data" / "track.obj").write_text("".join(f"o {g}\n" for g in ("1ROAD_road", "1GRASS_0", name, "HOUSE")))
    ini = ext_config.generate(d).read_text(encoding="utf-8")
    for ln in ini.splitlines():
        if ln.startswith(("GRASS_MESHES", "OCCLUDING_MESHES", "MESHES")):
            assert "BRIDGESTRUCT" not in ln, ln
    r = pbr.resolve(name)
    assert r["key"] == "BRIDGESTRUCT" and r["diffuse"] is not None and r["diffuse"].name == "building_diffuse.jpg"
    snap_pbr = (SNAP / "pbr.py").read_text(encoding="utf-8")
    assert '"BRIDGESTRUCT": ("building_diffuse.jpg"' in snap_pbr
    for prep in (SNAP / "build_kn5_loop.py", ROOT / "scripts" / "ac" / "build_kn5_loop.py"):
        # (the snapshot's tuple also carries the phase-5 stub barrier, ledger 0054: "BRIDGESTRUCT", "1WALL_STUB")
        assert '"1WALL_RACE", "1KERB_RACE", "BRIDGESTRUCT"' in prep.read_text(encoding="utf-8"), prep


def test_both_chains_run_the_bridge_pass_after_the_mouths_gap():
    sd = (ROOT / "tools" / "ship_sd.sh").read_text(encoding="utf-8")
    a = sd.index("tools/gap_mouths_blend.py")
    b = sd.index("tools/author_bridges_blend.py")
    c = sd.index("tools/export_scatter_blend.py")
    assert a < b < c and "--python-exit-code 1 --python \"$AIROSO/tools/author_bridges_blend.py\"" in sd
    spec = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "ship.json").read_text(encoding="utf-8"))
    st = spec["steps"]["draft"]
    # (the phase-5 stub tidy, ledger 0054 — a no-op without a declaration — sits between them, as in ship_sd.sh)
    assert st.index("gap_mouths") + 1 + (1 if "stubs_tidy" in st else 0) == st.index("bridges")
    assert "draft_bridges()" in (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")


def test_bridge_span_rule_crossing_and_bent_placement():
    m = _bridge_tool()
    pts = [(float(x), 0.0, 0.0) for x in range(0, 301, 2)]
    ways = [{"hw": "primary", "geom": [[100.0, 5.0], [160.0, 5.0]]}, {"hw": "motorway", "geom": [[0.0, 0.0], [300.0, 0.0]]}]
    spans = m.detect_spans(pts, lambda lon, lat: (lon, lat), ways)
    assert len(spans) == 1 and abs(spans[0][0] - 80.0) < 1e-6 and abs(spans[0][1] - 180.0) < 1e-6
    assert m.detect_spans(pts, lambda lon, lat: (lon, lat), [ways[1]]) == []
    assert abs(m.seg_cross((0, 0), (10, 0), (5, -1), (5, 1)) - 0.5) < 1e-9
    assert m.seg_cross((0, 0), (10, 0), (15, -1), (15, 1)) is None
    b = m.bent_stations([(40.0, 10.0), (80.0, 10.0)], 10.0, 110.0)
    assert b == [29.0, 60.0, 91.0]
    for s in b:
        assert not any(c - h <= s <= c + h for c, h in [(40.0, 10.0), (80.0, 10.0)])
    assert m.bent_stations([(40.0, 10.0), (80.0, 10.0)], 30.0, 90.0) == [60.0]
    assert m.bent_stations([(40.0, 10.0), (61.0, 10.0)], 0.0, 120.0) == [29.0, 72.0]
    assert m.DECK_T_M > 0 and m.FASCIA_TOP_M > 0 and m.BURY_M > 0


def test_the_prep_holds_moves_on_zero_area_faces_and_keeps_the_fin_gate():
    src = (SNAP / "build_kn5_loop.py").read_text(encoding="utf-8")
    a = src.index("n_held = 0")
    b = src.index("FATAL: the kept-cell refinement stood")
    assert a < b, "the hold runs before the FATAL fin check, which stays"
    assert '"held_on_zero_area_faces": n_held' in src
