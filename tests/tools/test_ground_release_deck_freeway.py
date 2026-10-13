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
    zs = gr.resolve_zones(cfg)
    assert [z["name"] for z in zs] == ["alvarado_creek_bank", "college_south_approach", "lmb_alvarado_creek"]
    assert [z["kind"] for z in zs] == ["bank", "span", "span"] and all(z["reach_m"] >= 36.0 for z in zs)
    rd = cfg["road_datum"]["decks"]
    assert rd[0]["name"] == "college_ave_over_i8" and rd[0]["deck_m"] == [2586.0, 2683.0]


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
