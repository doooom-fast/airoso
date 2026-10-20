"""Ledger 0046, v0.18.0 integration fix round: the pure halves of tools/deck_datum.py (real bridge decks between real
abutments), tools/ground_release.py (the near-road ground released to 3DEP in declared zones; engine-july's prep reads
the same zones), tools/freeway_i8.py (the I-8's own pavement), the GrassFX occluder rule for it and the TreeFX guard."""
from __future__ import annotations

import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
import sd_v0180  # noqa: E402  (the pinned v0.18.0 Lake Murray data, tests/fixtures/lake_murray_v0180)
sys.path.insert(0, str(ROOT / "tools"))
import deck_datum as dd  # noqa: E402
import freeway_i8 as fw  # noqa: E402
import ground_release as gr  # noqa: E402
import make_treefx as mt  # noqa: E402

SNAP = ROOT / "tracks" / "san-diego-lake-murray" / "engine-july-snapshot" / "scripts" / "ac" / "build_kn5_loop.py"


def _snapshot():
    spec = importlib.util.spec_from_file_location("_bkl_snapshot_release", SNAP)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# --- deck datum ----------------------------------------------------------------------------------------------
def test_deck_profile_straight_between_real_abutments_one_sided_approaches():
    ts = [float(t) for t in range(0, 101)]
    # a road climbing 4 % on its embankments, a span 40..70 whose bare earth dips 6 m under it
    dep = [0.04 * t - (6.0 if 41 <= t <= 69 else 0.0) for t in ts]
    tgt, ya, yb = dd.target_profile(ts, dep, (40.0, 70.0))
    assert abs(ya - 0.04 * 38.5) < 0.01 and abs(yb - 0.04 * 71.5) < 0.01        # never read across the abutment
    for t, y in zip(ts, tgt):
        if 40 < t < 70:
            assert abs(y - (ya + (yb - ya) * (t - 40) / 30)) < 1e-9               # a straight girder line
        assert y > 0.04 * t - 0.2                                                 # no dip under the deck
    st = [float(s) for s in range(-20, 121, 3)]
    old = [0.0] * len(st)
    new = dd.apply_deck(st, old, ts, tgt, (10.0, 90.0))
    for s, a, b in zip(st, old, new):
        if s < 10 or s > 90:
            assert a == b                                                           # outside the window: untouched
    mid = [b for s, b in zip(st, new) if 30 <= s <= 70]
    assert all(abs(b - dd.interp(ts, tgt, s)) < 1e-9 for s, b in zip([s for s in st if 30 <= s <= 70], mid))


def test_deck_datum_run_is_idempotent_and_refuses_a_deck_outside_its_window():
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    pts = [[float(x), 0.0, 0.0] for x in range(0, 301, 3)]
    raw = {"origin": {"lon": -117.0, "lat": 32.8, "elev_m": 100.0}, "points_xyz_m": pts, "widths_m": [10.0] * len(pts)}
    (d / "data" / dd.SRC_NAME).write_text(json.dumps(raw))
    cfg = {"road_datum": {"decks": [{"name": "t", "deck_m": [120.0, 180.0], "window_m": [90.0, 210.0]}]}}
    (d / "track.config.json").write_text(json.dumps(cfg))
    keys = {}
    t = 90.0
    while t <= 210.0 + 1e-9:
        keys[f"{t:.2f},{0.0:.2f}"] = 100.0 + (2.0 if (t <= 120 or t >= 180) else -5.0)
        t += 1.0
    (d / "data" / "deck_datum.samples.json").write_text(json.dumps({"_provenance": {"fetches": []}, "points": keys}))
    r1 = dd.run(d, offline=True)
    y1 = [p[1] for p in json.loads((d / "data" / dd.SRC_NAME).read_text())["points_xyz_m"]]
    assert r1["decks"][0]["abutment_heights_abs_m"] == [102.0, 102.0] and abs(max(y1) - 2.0) < 1e-6
    r2 = dd.run(d, offline=True)
    y2 = [p[1] for p in json.loads((d / "data" / dd.SRC_NAME).read_text())["points_xyz_m"]]
    assert y1 == y2 and r2["output_md5"] == r1["output_md5"]
    cfg["road_datum"]["decks"][0]["deck_m"] = [92.0, 180.0]
    (d / "track.config.json").write_text(json.dumps(cfg))
    (d / "data" / "deck_datum.json").unlink()
    try:
        dd.run(d, offline=True)
    except SystemExit as e:
        assert "inside window" in str(e)
    else:
        raise AssertionError("a deck closer than BLEND_M to its window's end must be refused")


# --- ground release ------------------------------------------------------------------------------------------
def _line():
    pts = [(float(x), 0.0, 0.0) for x in range(0, 401, 4)]          # eastbound: left of travel = north (+z)
    return pts, [10.0] * len(pts)


def test_zones_membership_side_reach_ramp_and_kind():
    pts, w = _line()
    Z = gr.Zones(pts, w, [{"name": "bank", "kind": "bank", "s_m": [100.0, 200.0], "sides": [1], "reach_m": 20.0}])
    assert Z.weight(150.0, 12.0)[0] == 1.0 and Z.weight(150.0, 12.0)[1]["name"] == "bank"
    assert Z.weight(150.0, -12.0) == (0.0, None)                    # the other side
    assert Z.weight(150.0, 3.0) == (0.0, None)                      # on the road, past inner_m
    assert Z.weight(150.0, 4.6)[0] > 0.0                            # the kerb seam (half-width - inner_m)
    assert 0.0 < Z.weight(150.0, 23.5)[0] < 1.0 and Z.weight(150.0, 25.5) == (0.0, None)   # the outer ramp
    assert 0.0 < Z.weight(101.0, 12.0)[0] < 1.0 and Z.weight(99.0, 12.0) == (0.0, None)    # the end ramp
    assert Z.contains(150.0, 12.0) and not Z.contains(250.0, 12.0)
    S = gr.Zones(pts, w, [{"name": "deck", "kind": "span", "s_m": [100.0, 200.0], "sides": [1, -1], "reach_m": 20.0}])
    assert S.weight(150.0, 0.0)[0] == 1.0 and S.weight(150.0, -3.0)[0] == 1.0     # a span zone: under the deck too
    assert S.weight(150.0, -12.0)[0] == 1.0 and S.weight(150.0, 26.0) == (0.0, None)


def test_snapshot_prep_reads_the_same_zones_as_the_author_tool():
    """engine-july's prep (snapshot of record) must leave exactly the released ground alone: its ReleaseZones agrees
    with tools/ground_release.Zones on every point with a non-zero weight, and is absent without the data file"""
    bkl = _snapshot()
    pts, w = _line()
    zones = [{"name": "a", "kind": "bank", "s_m": [100.0, 200.0], "sides": [1], "reach_m": 20.0},
             {"name": "b", "kind": "span", "s_m": [300.0, 340.0], "sides": [1, -1], "reach_m": 40.0}]
    Z = gr.Zones(pts, w, zones)
    R = bkl.ReleaseZones(pts, w, zones, inner_m=gr.INNER_M)
    n = 0
    for x in range(-10, 420, 7):
        for z in range(-60, 61, 3):
            if Z.weight(float(x), float(z))[0] > 0.0:
                assert R.contains(float(x), float(z)), (x, z)
                n += 1
    assert n > 200
    assert not R.contains(150.0, -12.0) and not R.contains(250.0, 12.0)
    assert R.contains(320.0, 0.0) and not R.contains(150.0, 0.0)          # span: the whole deck; bank: never the road
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    assert bkl._release_zones(d) is None
    src = SNAP.read_text(encoding="utf-8")
    assert "if rel is not None and rel.contains(x, y):" in src
    assert "skip=(rel.contains if rel is not None else None)" in src


def test_lattice_bilinear_and_holes():
    L = gr.Lattice(2.0, [0, 1, 0, 1], [0, 0, 1, 1], [0.0, 2.0, 4.0, 6.0])
    assert abs(L.at(1.0, 1.0) - 3.0) < 1e-12 and abs(L.at(1.5, 0.0) - 1.5) < 1e-12
    assert L.at(5.0, 1.0) is None


def test_plan_nodes_cover_every_zone_cell():
    pts, w = _line()
    Z = gr.Zones(pts, w, [{"name": "bank", "kind": "bank", "s_m": [100.0, 140.0], "sides": [1], "reach_m": 10.0}])
    nodes = set(gr.plan_nodes(Z, 2.0))
    L = gr.Lattice(2.0, [k[0] for k in nodes], [k[1] for k in nodes], [0.0] * len(nodes))
    for x in range(98, 143):
        for z in range(0, 20):
            if Z.weight(x + 0.5, z + 0.5)[0] > 0:
                assert L.at(x + 0.5, z + 0.5) is not None, (x, z)


def test_lake_murray_zones_are_declared_and_resolve():
    cfg = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json").read_text(encoding="utf-8"))
    # the vertex-declared zones (ledger 0055 round 2) resolve on the pinned v0.18.0 centreline to the stations they were
    # measured at there
    cl = json.loads((sd_v0180.DATA / "centerline.local.json").read_text(encoding="utf-8"))
    zs = gr.resolve_zones(cfg, [tuple(p) for p in cl["points_xyz_m"]])
    assert [z["name"] for z in zs] == ["alvarado_creek_bank", "college_south_approach", "lmb_alvarado_creek",
                                       "college_i8_span", "lmb_i8_span", "alvarado_college_terrace",
                                       "college_approach_foot", "college_north_approach", "college_split_cut"]
    assert [z["kind"] for z in zs] == ["bank", "span", "span", "span", "span", "bank", "bank", "bank", "bank"]
    # ledger 0055: College's cut face — east of the northbound slab only, read out to the construction zone (20 m =
    # terrain.clamp_corridor_m), its top rounded over 3 m (docs/ROAD-CONSTRUCTION.md 2-5 m), no rail (a cut has no drop)
    cut = zs[-1]
    assert cut["sides"] == [-1] and cut["cut_reach_m"] == 20.0 and cut["round_m"] == 3.0 and cut["rails"] is False
    assert cut["cut_reach_m"] == cfg["terrain"]["clamp_corridor_m"]
    assert cut["s_m"][0] <= 3600.0 and cut["s_m"][1] >= 4300.0
    assert all("cut_reach_m" not in z and "rails" not in z for z in zs[:-1])          # every other zone as it was
    assert all(z["reach_m"] >= 36.0 for z in zs)
    # fix round 2: each I-8 overcrossing's whole real span (fresh 3DEP abutments ~2580 / ~2670 and ~13338 / ~13407)
    spans = {z["name"]: z["s_m"] for z in zs}
    assert spans["college_i8_span"][0] <= 2576.0 and spans["college_i8_span"][1] >= 2676.0
    assert spans["lmb_i8_span"][0] <= 13334.0 and spans["lmb_i8_span"][1] >= 13411.0
    assert abs(spans["lmb_i8_span"][0] - 13330.0) < 0.05 and abs(spans["lmb_i8_span"][1] - 13428.0) < 0.05
    assert spans["lmb_alvarado_creek"][0] == spans["lmb_i8_span"][1]                    # still abutting: no ramp between
    assert abs(spans["lmb_alvarado_creek"][1] - 13464.0) < 0.05
    # fix round 4 (the view lens): the approach foot covers the whole College-over-Alvarado embankment edge, and the
    # north approach abuts the I-8 span (no ramp between them: the row of fins at s 2660-2700)
    assert spans["college_approach_foot"][0] <= 2410.0
    assert spans["college_north_approach"][0] == spans["college_i8_span"][1]
    rd = cfg["road_datum"]["decks"]
    assert rd[0]["name"] == "college_ave_over_i8" and rd[0]["deck_m"] == [2586.0, 2683.0]


def test_a_zone_declared_by_vertex_stays_on_its_place_when_the_road_before_it_changes_length():
    # ledger 0055 round 2: College's realignment shortened the lap 6.6 m; a station-declared zone past it slid 6.6 m
    pts = [(0.0, 0.0, 3.0 * k) for k in range(200)]
    base = {"name": "z", "kind": "span", "sides": ["left"], "reach_m": 40.0}
    (z,) = gr.resolve_zones({"terrain": {"ground_release": {"zones": [dict(base, v=[150.5, 170.0])]}}}, pts)
    assert z["s_m"] == [451.5, 510.0] and z["v"] == [150.5, 170.0]
    shorter = [(0.0, 0.0, 3.0 * k) if k <= 50 else (0.0, 0.0, 3.0 * k - 2.0) for k in range(200)]   # 2 m gone at v50
    (z2,) = gr.resolve_zones({"terrain": {"ground_release": {"zones": [dict(base, v=[150.5, 170.0])]}}}, shorter)
    assert abs(z2["s_m"][0] - (451.5 - 2.0)) < 1e-6 and abs(z2["s_m"][1] - (510.0 - 2.0)) < 1e-6   # the same place
    assert gr.station_at_vertex(pts, 0.0) == 0.0 and abs(gr.station_at_vertex(pts, 199.0) - 597.0) < 1e-9
    for bad, P in ((dict(base, v=[150.0, 170.0], s_m=[1.0, 2.0]), pts), (dict(base), pts), (dict(base, v=[170.0, 150.0]), pts),
                   (dict(base, v=[150.0, 170.0]), None), (dict(base, v=[150.0, 250.0]), pts)):
        try:
            gr.resolve_zones({"terrain": {"ground_release": {"zones": [bad]}}}, P)
        except SystemExit:
            continue
        raise AssertionError(f"accepted {bad}")


# --- the I-8 pavement ----------------------------------------------------------------------------------------
def test_freeway_carriageways_never_overlap_and_leave_room_for_the_barrier():
    P = {"lane_m": 3.66, "outer_shoulder_m": 3.0, "inner_shoulder_m": 1.2}
    a = [(float(x), 0.0, {"lanes": 5, "bridge": False}) for x in range(0, 201, 20)]
    sta = fw.resample(a, 4.0)
    other = [(float(x), 19.0) for x in range(-20, 221, 20)]          # the opposite carriageway 19 m to the left
    ch = fw.plan_chain(sta, other, P)
    for st in ch:
        assert st["median_side"] == 1 and st["wl"] <= 19.0 / 2 - fw.BARRIER_HALF_M + 1e-9
        assert abs(st["wr"] - (5 * 3.66 / 2 + 3.0)) < 1e-9 and len(st["dash"]) == 4
    far = [(float(x), 60.0) for x in range(-20, 221, 20)]
    assert all(abs(st["wl"] - (5 * 3.66 / 2 + 1.2)) < 1e-9 for st in fw.plan_chain(sta, far, P))
    bridge = fw.plan_chain(fw.resample([(0.0, 0.0, {"lanes": 4, "bridge": True}), (20.0, 0.0, {"lanes": 4, "bridge": True})], 4.0),
                           other, P)
    assert all(st is None for st in bridge)                         # an OSM bridge way is never draped
    lines = fw.barrier_lines(ch, other, 40.0)
    assert len(lines) == 1 and all(abs(p[1] - 9.5) < 1e-6 for p in lines[0])
    assert fw.barrier_lines(ch, far, 40.0) == []


def test_freeway_slab_heights_hold_the_cross_slope_and_interpolate_across():
    """fix round 2: the slab's height is 3DEP at its edges and centre, an edge caught on a cut wall held to XSLOPE_MAX"""
    hr, hc, hl = fw.edge_heights(5.0, 1.0, 1.1, 10.0, 8.0)          # the right edge read 4 m up a wall
    assert abs(hr - (1.0 + fw.XSLOPE_MAX * 10.0)) < 1e-9 and hc == 1.0 and abs(hl - 1.1) < 1e-9
    assert fw.edge_heights(1.05, 1.0, 0.95, 10.0, 8.0) == (1.05, 1.0, 0.95)      # a real crown is kept
    st = {"h": [0.8, 1.0, 1.4], "wr": 10.0, "wl": 8.0}
    assert abs(fw.height_at(st, 0.0) - 1.0) < 1e-12 and abs(fw.height_at(st, -10.0) - 0.8) < 1e-12
    assert abs(fw.height_at(st, 8.0) - 1.4) < 1e-12 and abs(fw.height_at(st, 4.0) - 1.2) < 1e-12
    assert abs(fw.height_at(st, -5.0) - 0.9) < 1e-12
    sm = fw.smooth_series([0.0, 0.0, 1.0, 0.0, 0.0], passes=1)
    assert sm == [0.0, 0.25, 0.5, 0.25, 0.0]
    assert fw.smooth_series([3.0, 4.0]) == [3.0, 4.0]                  # too short: kept


def test_freeway_heights_are_cached_3dep_and_offline_refuses_a_gap():
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    o = {"lon": -117.0, "lat": 32.8, "elev_m": 100.0}
    osm = {"nodes": {"1": [-117.0, 32.8], "2": [-116.999, 32.8], "3": [-117.0, 32.8002], "4": [-116.999, 32.8002]},
           "ways": [{"id": 10, "nodes": [1, 2], "tags": {"lanes": "4"}}, {"id": 20, "nodes": [4, 3], "tags": {"lanes": "4"}}]}
    osm_p = d / "osm.json"
    osm_p.write_text(json.dumps(osm))
    (d / "data" / "corridor.i8.json").write_text(json.dumps({"_provenance": {
        "source": "test", "osm_cache": str(osm_p), "chain_a_way_ids": [10], "chain_b_way_ids": [20]}}))
    (d / "data" / "centerline.local.json").write_text(json.dumps({"origin": o, "points_xyz_m": [[0, 0, 0], [1, 0, 0]],
                                                                  "widths_m": [10, 10]}))
    P = {"enabled": True, "corridor": "i8", "lane_m": 3.66, "outer_shoulder_m": 3.0, "inner_shoulder_m": 1.2,
         "default_lanes": 4, "step_m": 4.0, "lift_m": 0.15, "line_w_m": 0.15, "dash_m": 3.0, "dash_period_m": 12.0,
         "barrier_gap_max_m": 40.0}
    (d / "track.config.json").write_text(json.dumps({"scenery": {"freeway": P}}))
    try:
        fw.build(d, offline=True)
    except SystemExit as e:
        assert "not cached and --offline" in str(e)
    else:
        raise AssertionError("no cache + --offline must refuse (no silent fill, L2)")


def test_freeway_occludes_grass_near_only():
    sys.path.insert(0, str(ROOT))
    from scripts.ac import ext_config
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "lighting": {"grassfx": True}}))
    groups = ["1ROAD_road", "1GRASS_0", "HIGHWAY_I8_NEAR_0", "HIGHWAY_I8_FAR_0", "MARKINGS_I8_0", "YLINE_I8_0",
              "BARRIER_I8_0", "HIGHWAY"]
    (d / "data" / "environment.obj").write_text("\n".join(f"o {g}" for g in groups) + "\n")
    ini = ext_config.generate(d).read_text(encoding="utf-8")
    occ = [ln for ln in ini.splitlines() if ln.startswith("OCCLUDING_MESHES")][0]
    occ = {s.strip() for s in occ.split("=", 1)[1].split(",")}
    assert {"HIGHWAY_I8_NEAR_0", "MARKINGS_I8_0"} <= occ
    assert not ({"HIGHWAY_I8_FAR_0", "HIGHWAY", "BARRIER_I8_0"} & occ)


def test_treefx_keeps_trees_off_the_freeway_lanes():
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "source" / "trees").mkdir(parents=True)
    (d / "source" / "trees" / "PalmV1.bin").write_bytes(b"bin")
    (d / "track.config.json").write_text(json.dumps({"slug": "tiny"}), encoding="utf-8")
    pts = [[float(x), 0.0, 0.0] for x in range(0, 201, 5)]
    (d / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": pts, "widths_m": [10.0] * len(pts)}))
    palms = [{"x": 100.0, "y": 0.0, "z": 60.0}, {"x": 100.0, "y": 0.0, "z": 90.0}]
    (d / "data" / "scatter_positions.json").write_text(json.dumps({"palms": palms, "trees": [], "scrub": [],
                                                                   "median_planting": []}))
    (d / "data" / "track.obj").write_text("o 1GRASS_0\nusemtl 1GRASS_0_mat\nv 0 0 0\n", encoding="utf-8")
    assert len(mt.plan(d)["entries"]) == 2
    st = [{"x": float(x), "z": 60.0, "wl": 10.0, "wr": 12.0} for x in range(0, 201, 4)]
    (d / "data" / "freeway_i8.json").write_text(json.dumps({"chains": [st + [None] + st[:1]], "barrier": []}))
    e = mt.plan(d)["entries"]
    assert [(p["x"], p["z"]) for p in e] == [(100.0, 90.0)]       # the palm on the lane is gone, the other stays


def test_fix_round_2_guards_are_in_the_blender_steps():
    """fix round 2 (both lenses): the release caps each FACE under the pavement (not the nearest pavement vertex), reins
    banks in with a batter, smooths its rails; the freeway lays its slab at the 3DEP height, sees a deck from UNDER the
    slab, makes the ground meet the slab, and refuses a vertex over a deck. Source pins: the halves are bpy-only."""
    gr_src = (ROOT / "tools" / "ground_release_blend.py").read_text(encoding="utf-8")
    assert "near_pave" not in gr_src and "EDGE_CAP_M" not in gr_src
    for k in ("def face_samples(", "face_low_pave(f)", "released faces over a ROAD / CURB surface", "BATTER_CUT * d", "BATTER_FILL * d",
              "smooth_offsets(", "RAIL_JUMP_M", "RAIL_HELD_M", "RAIL_BURY_M", "TOP_NZ"):
        assert k in gr_src, k
    fw_src = (ROOT / "tools" / "author_freeway_blend.py").read_text(encoding="utf-8")
    for k in ("FW.height_at(st, o)", "Vector((x, y, z - DECK_UNDER))", "def conform_ground(", "def split_oversize(",
              "freeway vertices over a loop deck", "BRIDGESTRUCT"):
        assert k in fw_src, k
    assert "h + lift - 0.05" not in fw_src                     # the old deck ray, started over the ground at the deck


def test_freeway_is_off_for_lake_murray_and_off_builds_nothing():
    """Kevin's call (v0.18.0, ledger 0046): 'terrain only, NO I-8 pavement ribbon' stands — the freeway is OFF by config,
    and OFF means tools/freeway_i8.py writes no plan (a stale one is removed), so tools/author_freeway_blend.py never
    runs and no terrain is cut for a slab. The tool and its tests stay; enabled: true is the whole switch."""
    cfg = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json").read_text(encoding="utf-8"))
    assert cfg["scenery"]["freeway"]["enabled"] is False
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "data" / "freeway_i8.json").write_text(json.dumps({"chains": [], "barrier": []}))       # a stale plan
    (d / "track.config.json").write_text(json.dumps({"scenery": {"freeway": dict(cfg["scenery"]["freeway"])}}))
    fw.build(d, offline=True)
    assert not (d / "data" / "freeway_i8.json").exists()


def test_release_rails_are_one_line_per_side_over_the_union_of_zones():
    """the view lens (v0.18.0): overlapping / abutting zones (College's approach foot, south approach and I-8 span; Lake
    Murray Blvd's I-8 span and creek) each drew a rail over the shared stations — two prisms 3 cm apart, end caps
    standing up as white teeth. Stations are read per side over the union of the zones (source pin: bpy-only half)."""
    gr_src = (ROOT / "tools" / "ground_release_blend.py").read_text(encoding="utf-8")
    for k in ("by_side = {}", "seen = by_side.setdefault(side, {})", "if key in seen:", "for side, seen in by_side.items():",
              "for st in blocks:", "RAIL_TAPER_M", "RAIL_END_H_M + (h - RAIL_END_H_M) * hk"):
        assert k in gr_src, k


def test_release_fill_eases_with_the_gap_and_the_ramp_meets_the_prep():
    """the view lens (v0.18.0): grass teeth beside College's south abutment (the fill batter switched on and off face by
    face where the approach leaves its embankment) and a comb west of the north approach (the zone's ramp blended
    toward the graded ground the prep then refines away outside the zone). Source pins (bpy-only half) + the
    snapshot's RefineField the ramp reads is the one the prep runs."""
    gr_src = (ROOT / "tools" / "ground_release_blend.py").read_text(encoding="utf-8")
    for k in ("FILL_EASE_M", "def fill_top(fi, qx, qy):", "def pave_gap(fi, i):", "fill_top(fi, q[0], q[1])",
              "RF = _refine_field(proj)", "RF.target(x, y, z, d_built=", "zo + w * (t - zo)",
              'zone_kind.get(zname) == "span"', "def grounded(fi):"):
        assert k in gr_src, k
    m = _snapshot()
    assert hasattr(m, "RefineField") and hasattr(m.RefineField, "target") and hasattr(m.RefineField, "in_kept")


def test_abutting_zones_do_not_ramp_at_their_shared_end():
    """the view lens (v0.18.0): two zones meeting at one station (Lake Murray Blvd's I-8 span and creek) each ramped to
    nothing there — a dip back to the built ground between two released pieces"""
    pts, w = _line()
    Z = gr.Zones(pts, w, [{"name": "a", "kind": "span", "s_m": [100.0, 200.0], "sides": [1, -1], "reach_m": 20.0},
                          {"name": "b", "kind": "span", "s_m": [200.0, 260.0], "sides": [1, -1], "reach_m": 20.0}])
    for s in (196.0, 199.0, 200.0, 201.0, 204.0):
        assert Z.weight(s, 6.0)[0] == 1.0, s                      # no dip at the shared station
    assert 0.0 < Z.weight(101.0, 6.0)[0] < 1.0 and 0.0 < Z.weight(259.0, 6.0)[0] < 1.0   # the free ends still ramp


# --- v0.18.0 integration fix round 4 (the gates, runtime and view lenses) -------------------------------------
def test_rail_stands_full_height_over_every_drop_and_slopes_only_over_padding():
    """the gates lens: sloped ends (to 5 cm) stood over live drops wherever a run's padding was clipped — College
    Ave's approach foot, s 2500-2502, 4.9 m down. rail_heights: 1 over every station that needs the rail and for
    RAIL_HOLD_M past it; a slope only over the padding beyond, never shorter than RAIL_TAPER_MIN_M (else square)."""
    ss = [float(s) for s in range(0, 21)]
    need = [False] * 3 + [True] * 15 + [False] * 3          # 3 m padding each side
    h = gr.rail_heights(ss, need, taper=2.0)
    assert all(h[k] == 1.0 for k in range(len(ss)) if need[k])
    assert h[2] == 1.0 and h[18] == 1.0                    # the hold: full height 1 m past the first / last drop
    assert h[0] == 0.0 and h[-1] == 0.0                    # the sloped ends, over padding only
    # padding clipped (a zone end, a bridge rail's end): a station over a drop at the very end -> a square end
    h = gr.rail_heights(ss, [True] * 18 + [False] * 3, taper=2.0)
    assert h[0] == 1.0 and h[-1] == 0.0
    h = gr.rail_heights(ss, [False] + [True] * 20, taper=2.0)   # 1 m of padding is all hold: square
    assert h[0] == 1.0 and h[-1] == 1.0
    # a piece of padding with no drop: slopes at both ends over at most half its length
    h = gr.rail_heights([0.0, 1.0, 2.0], [False, False, False], taper=2.0)
    assert h == [0.0, 1.0, 0.0]


def test_batter_is_the_straight_bank_where_two_pavements_leave_no_room():
    """the view lens: College's south approach stands 5-6 m over Alvarado with 2-3 m of ground between the sidewalks —
    the fill from College and the cut from Alvarado cannot both hold, and 'the cut wins' left a vertical curtain under
    College's sidewalk. There the ground is the straight bank between the two edges; elsewhere nothing changes."""
    # no conflict: the fill lifts, the cut caps (as before)
    assert gr.batter_z(0.0, (5.0, 4.0, 1.0), (2.0, 3.0, 0.6)) == 2.0
    assert gr.batter_z(9.0, (5.0, 4.0, 1.0), None) == 5.0
    # conflict between two pavements 5.25 m apart: the straight line between the edges, by distance
    cut = (0.85 + 1.0 * 1.0, 0.85, 1.0)                    # Alvarado's sidewalk 1 m away
    fill = (6.1 - 1.7 * 2.0, 6.1, 2.0)                     # College's sidewalk 2 m away
    z = gr.batter_z(0.05, cut, fill)
    assert abs(z - (0.85 + (6.1 - 0.85) * 1.0 / 3.0)) < 1e-9
    assert cut[0] < z < fill[0]
    # a conflict on one road's own grade (less than STRAIGHT_BANK_MIN_M between the two faces): the cut still wins
    assert gr.batter_z(0.0, (1.2, 1.0, 0.2), (1.5, 1.6, 0.05)) == 1.2


def test_a_cut_zone_reads_its_own_reach_rounds_its_top_and_declares_no_rail():
    """ledger 0055 (College Ave, Kevin: 'cut into the hillside the way California does'): a zone's cut_reach_m lets the
    batter read the pavement farther than BATTER_REACH_M (the hill meets the cut 12-14 m out there), round_m rounds the
    cut's top into the real ground (a smooth minimum, never above the cut or the ground), rails false only on a cut"""
    # the rounding: far below the cut -> the ground; far above -> the cut; at the crease -> under both, by k / 4
    k = gr.round_k(3.0, 1.0)
    assert k == 1.5
    cut = (5.0, 0.0, 5.0)                                   # a 45 deg cut from a pavement 5 m away: limit 5 m
    assert gr.batter_z(1.0, cut, None, round_k=k) == 1.0    # the real ground well under the cut: untouched
    assert gr.batter_z(12.0, cut, None, round_k=k) == 5.0   # the hill well over the cut: cut back to the plane
    z = gr.batter_z(5.0, cut, None, round_k=k)
    assert abs(z - (5.0 - k / 4.0)) < 1e-9                  # the crease, rounded
    zs = [gr.batter_z(h, cut, None, round_k=k) for h in [3.0 + 0.1 * i for i in range(60)]]
    assert all(b >= a - 1e-12 for a, b in zip(zs, zs[1:])) and max(zs) <= 5.0      # monotone, never over the cut
    assert all(zr <= min(3.0 + 0.1 * i, 5.0) + 1e-12 for i, zr in enumerate(zs))    # never over the ground either
    assert gr.batter_z(12.0, cut, None) == 5.0              # no round_k: exactly as before
    # a fill below still lifts, and the straight bank between two pavements is untouched by the rounding
    assert gr.batter_z(0.0, (5.0, 4.0, 1.0), (2.0, 3.0, 0.6), round_k=k) == 2.0
    # the declaration's guards
    base = {"name": "z", "kind": "bank", "s_m": [0, 10], "sides": ["right"], "reach_m": 40.0}
    ok = gr.resolve_zones({"terrain": {"ground_release": {"zones": [dict(base, cut_reach_m=20.0, round_m=3.0, rails=False)]}}})
    assert ok[0]["cut_reach_m"] == 20.0 and ok[0]["round_m"] == 3.0 and ok[0]["rails"] is False
    for bad in (dict(base, cut_reach_m=50.0), dict(base, round_m=6.0), dict(base, rails=False),
                dict(base, cut_reach_m=20.0, rails="no")):
        try:
            gr.resolve_zones({"terrain": {"ground_release": {"zones": [bad]}}})
        except SystemExit:
            continue
        raise AssertionError(f"accepted {bad}")
    src = (ROOT / "tools" / "ground_release_blend.py").read_text(encoding="utf-8")
    for key in ('reach_c = max(BATTER_REACH_M, float(zr.get("cut_reach_m") or 0.0))', "near = [r for r in near_c if r[3] <= BATTER_REACH_M]",
                'rail_zones = [z for z in R["zones"] if z.get("rails", True)]', "DEGEN_AREA_M2 = 1e-5"):
        assert key in src, key


def test_round_4_release_holds_the_ground_under_the_pavement_and_leaves_no_coincident_faces():
    """the view lens's curtain under College's sidewalk (the prep pins under a deck only within its window of the
    vertex's own height, and leaves zone vertices alone, so ground the draft seated at Alvarado's level stayed a pit),
    and the runtime lens's zero-length normals (vertical curtain edges halved round after round stacked up to 31
    coincident faces; triangulated T-vertex quads left back-to-back slivers). Source pins: bpy-only halves."""
    src = (ROOT / "tools" / "ground_release_blend.py").read_text(encoding="utf-8")
    for k in ("v.co.z = min(ht) - CLEAR_M", "z < min(ht) - CLEAR_M - HELD_PIT_M", "lowerable = set(released) | pits", "math.hypot(a.x - b.x, a.y - b.y) <= SUBDIV_M",
              "math.hypot(a.x - b.x, a.y - b.y) <= EDGE_SUBDIV_M", "bmesh.ops.remove_doubles(bm, verts=weld, dist=1e-4)",
              "GR.batter_z(z_in, cut, fill, round_k=rk)", "GR.rail_heights(ss,", "RAIL_EXT_MAX_M", 'r["need"] = r["need_ext"]',
              '"coincident_faces_removed": n_coinc', 'RAIL_OBJECT = "1WALL_guard_release"', "RAIL_CHUNK_TRIS"):
        assert k in src, k
    assert "e.calc_length()" not in src                     # every halving is by plan length
    # the rails never join GUARDRAIL (it split past the exporter's vertex cap: two '1WALL_guard' meshes, verify_kn5)
    assert "bmr.from_mesh(grd.data)" not in src and "bmr.to_mesh(grd.data)" not in src
    tri = (ROOT / "tools" / "triangulate_terrain_blend.py").read_text(encoding="utf-8")
    assert "def remove_coincident_slivers(bm):" in tri and "SLIVER_M2" in tri


def test_lamp_lenses_never_ride_the_terrain_delta_and_the_far_ring_dims_at_night():
    """the runtime lens: the prep moved each LIGHTS lens by the ground change under its arm while its LIGHTPOST stayed
    (LIGHT_123 on Lake Murray Blvd's I-8 deck 0.68 m over its own plate, its head shadowing its pool); and the far ring
    kept its day ksDiffuse at night beside the dimmed near grass."""
    src = SNAP.read_text(encoding="utf-8")
    i = src.index("# palms / scrub")
    ride = src[i:src.index("_shift(ob, isl, dz)", i)]
    assert '"LIGHTS"' not in ride and '"PALMTRUNK"' in ride
    ext = (ROOT / "scripts" / "ac" / "ext_config.py").read_text(encoding="utf-8")
    assert '("1GRASS", "1LAWN", "GRASS_FAR")' in ext
