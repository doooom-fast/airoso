"""scripts/elevation/terrain_sample.py — the tiered-terrain sampler (ledger 0046): the I-8 corridor centreline is
the median of the two carriageway chains (and carries on along whichever runs further), the corridor floor
replaces data/i8.local.json with its provenance while the replaced 64-point file is kept once as
i8.legacy.local.json, the 3DEP cache refuses a changed lattice/origin, and an offline run meshes from the cache
alone (and stops, not guesses, when a vertex has no sample). No network."""
from __future__ import annotations

import gzip
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.elevation import terrain_sample as ts  # noqa: E402
from scripts.geometry import terrain_tiers as tt  # noqa: E402

ORIGIN = {"lon": -117.0, "lat": 32.8, "elev_m": 100.0}
M_LON, M_LAT = tt.meters_per_degree(32.8)


def _ll(x, z):
    return [ORIGIN["lon"] + x / M_LON, ORIGIN["lat"] + z / M_LAT]


def _terrain(half=300.0, **kw):
    t = {"terrain_band_m": 22.0,
         "tiers": [{"within_m": 30.0, "cell_m": 4.4}, {"within_m": 120.0, "cell_m": 17.6}, {"cell_m": 52.8}],
         "tier_options": {"verge_within_m": 8.0, "physical_within_m": 80.0},
         "far_extent": {"bbox_swne": [32.8 - half / M_LAT, -117.0 - half / M_LON, 32.8 + half / M_LAT, -117.0 + half / M_LON]}}
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


def test_corridor_centreline_is_the_carriageway_median_and_runs_on():
    nodes, ways = {}, []
    # eastbound at z = +15 from x -1000 to 1000; westbound at z = -15 from x 1200 to -800 (it runs on 200 m further east)
    eb = [(x, 15.0) for x in range(-1000, 1001, 100)]
    wb = [(x, -15.0) for x in range(1200, -801, -100)]
    for name, line, wid in (("eb", eb, 1), ("wb", wb, 2)):
        ids = []
        for k, (x, z) in enumerate(line):
            nid = wid * 1000 + k
            nodes[str(nid)] = _ll(x, z)
            ids.append(nid)
        half = len(ids) // 2      # two ways per carriageway, joined end node -> start node
        ways.append({"id": wid * 10, "nodes": ids[:half + 1], "tags": {"highway": "motorway", "ref": "I 8", "oneway": "yes"}})
        ways.append({"id": wid * 10 + 1, "nodes": ids[half:], "tags": {"highway": "motorway", "ref": "I 8", "oneway": "yes"}})
    ways.append({"id": 99, "nodes": [1000, 2000], "tags": {"highway": "motorway_link", "ref": "I 8"}})
    spec = tt.TierSpec(_terrain(half=2000.0), ORIGIN)
    line, prov = ts.corridor_centreline({"nodes": nodes, "ways": ways}, spec, {"name": "i8", "ref": "I 8", "osm_cache": "x"})
    mid = [p for p in line if -800 <= p[0] <= 980]
    assert mid and max(abs(p[1]) for p in mid) < 1.0, "the median between the carriageways"
    assert max(p[0] for p in line) > 1150 and min(p[0] for p in line) < -950, "carried on along the longer chain"
    assert prov["ways_matched"] == 4 and sorted(prov["chain_a_way_ids"] + prov["chain_b_way_ids"]) == [10, 11, 20, 21]


def test_polyline_out_keeps_the_legacy_file_once():
    d = _project(_terrain())
    legacy = [[-50.0, -2.5, 0.0], [50.0, -1.0, 0.0]]
    (d / "data" / "i8.local.json").write_text(json.dumps(legacy))
    c = {"polyline_out": "data/i8.local.json", "legacy_copy": "data/i8.legacy.local.json"}
    cor = {"_provenance": {"source": "osm"}, "floor": [{"s": 0, "x": -60.0, "z": 0.0, "h": 98.0},
                                                       {"s": 10, "x": -50.0, "z": 0.0, "h": 99.0}]}
    ts.write_polyline(d, c, cor, 100.0)
    assert json.loads((d / "data" / "i8.legacy.local.json").read_text()) == legacy
    new = json.loads((d / "data" / "i8.local.json").read_text())
    assert new["points_xyz_m"] == [[-60.0, -2.0, 0.0], [-50.0, -1.0, 0.0]] and new["_provenance"]["elev0"] == 100.0
    ts.write_polyline(d, c, cor, 100.0)                       # a rerun never overwrites the kept legacy file
    assert json.loads((d / "data" / "i8.legacy.local.json").read_text()) == legacy


def _seed_cache(d, terrain, dem):
    spec = tt.TierSpec(terrain, ORIGIN)
    lines, _o, _f = ts.road_inputs(d)
    topo = tt.Topology(spec, lines, (), closed_first=False)
    cache = ts.SampleCache(d / "data" / ts.SAMPLES, spec, spec.frame(None))
    for k in topo.vkeys:
        cache.h[k] = dem(k[0] * spec.base_m, k[1] * spec.base_m)
    cache.save()
    return topo


def test_offline_run_meshes_from_the_cache_alone():
    terrain = _terrain()
    d = _project(terrain)
    topo = _seed_cache(d, terrain, lambda x, z: round(100.0 + 0.01 * x + 0.02 * z, 2))
    st = ts.run(d, offline=True)
    assert st["vertices"] == len(topo.vkeys)
    T = json.loads(gzip.decompress((d / "data" / ts.TIERS).read_bytes()))
    assert T["inputs_md5"] == ts.inputs_md5([d / "data" / "centerline.local.json"])
    for i, j, h in list(zip(T["I"], T["J"], T["h"]))[::97]:
        assert abs(h - (100.0 + 0.01 * i * 2.2 + 0.02 * j * 2.2)) < 0.011
    assert len(T["tris"]) == 3 * len(T["phys"]) and set(T["phys"]) == {0, 1}
    # a road that moves needs vertices the cache lacks: offline stops instead of guessing
    pts = [[float(x), 0.0, 40.0] for x in range(-150, 151, 5)]
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": pts, "widths_m": [10.0] * len(pts), "origin": ORIGIN}))
    try:
        ts.run(d, offline=True)
    except SystemExit as e:
        assert "no cached 3DEP sample" in str(e)
    else:
        raise AssertionError("an offline run with missing samples must stop")


def test_cache_refuses_a_changed_lattice():
    terrain = _terrain()
    d = _project(terrain)
    _seed_cache(d, terrain, lambda x, z: 100.0)
    moved = dict(ORIGIN, lon=-117.001)
    try:
        sp = tt.TierSpec(terrain, moved)
        ts.SampleCache(d / "data" / ts.SAMPLES, sp, sp.frame(None))
    except SystemExit as e:
        assert "lattice/origin changed" in str(e)
    else:
        raise AssertionError("samples keyed to another origin must never be reused")
