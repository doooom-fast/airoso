"""tools/lidar_building_heights.py (ledger 0083 pass 2) on a drawn point cloud, and the planner's opt-in "lidar" rows. numpy only:
laspy / pyproj are imported inside main(), never here."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


lh = _load("lidar_building_heights")
pb = _load("plan_buildings")


def _cloud(roof_fn, ring, ground_z=10.0, spacing=0.5, extent=40.0):
    """ground points (class 2) everywhere outside the ring, roof points (class 6) inside at ground + roof_fn(x, y)"""
    g = np.arange(-extent, extent, spacing)
    X, Y = np.meshgrid(g, g)
    X, Y = X.ravel(), Y.ravel()
    inside = lh.point_in_ring(ring, X, Y)
    Z = np.where(inside, ground_z + roof_fn(X, Y), ground_z)
    C = np.where(inside, 6, 2).astype(np.uint8)
    return lh.Cloud(X, Y, Z, C, np.ones(X.shape, dtype=np.uint8))


BOX = [(-10.0, -6.0), (10.0, -6.0), (10.0, 6.0), (-10.0, 6.0)]


def test_a_flat_roof_reads_its_height_over_the_ground_around_it():
    cloud = _cloud(lambda x, y: np.full(x.shape, 7.3), BOX)
    rec, roof = lh.measure(cloud, BOX, [])
    assert rec["status"] == "measured" and rec["roof_src"] == "class 6"
    assert abs(rec["ground_m"] - 10.0) < 1e-6 and abs(rec["h_pct"]["p50"] - 7.3) < 1e-6
    assert rec["cover"] == 1.0 and len(rec["levels"]) == 1


def test_two_roof_levels_are_both_found():
    cloud = _cloud(lambda x, y: np.where(x < 0, 4.0, 12.0), BOX)
    rec, _ = lh.measure(cloud, BOX, [])
    assert [round(lv["h_m"]) for lv in rec["levels"]] == [4, 12]


def test_a_footprint_off_the_cloud_is_uncovered_and_keeps_its_default():
    cloud = _cloud(lambda x, y: np.full(x.shape, 5.0), BOX)
    far = [(x + 500.0, y) for x, y in BOX]
    rec, roof = lh.measure(cloud, far, [])
    assert rec["status"] == "uncovered" and roof is None
    row = {"key": "k", "form": "flat_parapet", "wall_h_m": 4.5, "_h": "class default [invented]"}
    assert pb.lidar_rows(dict(row), rec, None) == [dict(row, _lidar="uncovered")]
    assert pb.lidar_rows(dict(row), None, None) == [row]
    assert pb.lidar_rows(dict(row), {"status": "no_roof"}, None) == []          # bare ground in the lidar: dropped


def test_a_stepped_stand_is_cut_into_tiers_across_its_short_axis():
    # a 60 x 20 m stand: the front 8 m at 6 m, the back 12 m at 18 m
    ring = [(-30.0, -10.0), (30.0, -10.0), (30.0, 10.0), (-30.0, 10.0)]
    cloud = _cloud(lambda x, y: np.where(y < -2.0, 6.0, 18.0), ring, extent=60.0)
    rec, roof = lh.measure(cloud, ring, [])
    tiers, profile, box = lh.stepped(ring, *roof)
    assert len(tiers) == 2 and box["short_m"] == 20.0
    hs = sorted(t["h_p50"] for t in tiers)
    assert abs(hs[0] - 6.0) < 1e-6 and abs(hs[1] - 18.0) < 1e-6
    assert abs(sum(lh.ring_area(t["ring"]) for t in tiers) - 1200.0) < 1.0


def test_the_planner_takes_a_measured_roof_over_every_other_source():
    rec = {"status": "measured", "roof_src": "class 6", "n_roof": 400, "ground_m": 3.2, "ground_n": 90, "ground_ring_m": [1, 8],
           "h_pct": {"p05": 3.1, "p10": 3.3, "p25": 3.6, "p50": 6.84, "p75": 7.0, "p90": 7.2, "p95": 7.9, "p98": 8.5}, "levels": []}
    flat = pb.lidar_rows({"key": "a", "form": "flat_parapet", "wall_h_m": 21.6, "_h": "OSM building:levels 6 x 3.6 m"}, rec, None)
    assert flat[0]["wall_h_m"] == 6.8 and flat[0]["_h"].startswith("lidar") and "OSM building:levels" in flat[0]["_h_was"]
    gable = pb.lidar_rows({"key": "b", "form": "gable", "wall_h_m": 2.1, "ridge_h_m": 2.9, "_h": "class default [invented]"}, rec, None)
    assert gable[0]["wall_h_m"] == 3.3 and gable[0]["ridge_h_m"] == 7.9
    st = {"tiers": [{"footprint_lonlat": [[0, 0], [1, 0], [1, 1]], "band_m": [-10, -2], "h_p50": 6.0, "h_p10": 5.8, "h_p90": 6.2, "n_roof": 50},
                    {"footprint_lonlat": [[0, 1], [1, 1], [1, 2]], "band_m": [-2, 10], "h_p50": 18.0, "h_p10": 17.0, "h_p90": 19.0, "n_roof": 80}]}
    rows = pb.lidar_rows({"key": "g", "form": "flat_parapet", "wall_h_m": 21.6, "_h": "x"}, rec, st)
    assert [r["key"] for r in rows] == ["g_t0", "g_t1"] and [r["wall_h_m"] for r in rows] == [6.0, 18.0]
    assert all(r["form"] == "flat" for r in rows)


def test_no_other_plan_names_lidar():
    for f in ROOT.glob("tracks/*/source/bespoke/buildings.plan.json"):
        plan = json.loads(f.read_text(encoding="utf-8"))
        if f.parts[-4] != "del-mar-lm":
            assert "lidar" not in plan, f


def test_without_class_6_a_roof_is_its_single_returns_and_a_tree_or_bare_ground_is_not_measured():
    g = np.arange(-40.0, 40.0, 0.5)
    X, Y = np.meshgrid(g, g)
    X, Y = X.ravel(), Y.ravel()
    inside = lh.point_in_ring(BOX, X, Y)
    one = np.ones(X.shape, dtype=np.uint8)

    def run(z_in, cls_in, nr_in):
        Z = np.where(inside, z_in, 10.0)
        C = np.where(inside, cls_in, 2).astype(np.uint8)
        return lh.measure(lh.Cloud(X, Y, Z, C, one, np.where(inside, nr_in, 1).astype(np.uint8)), BOX, [])[0]

    roof = run(16.0, 1, 1)                         # unclassified, single returns: a roof
    assert roof["status"] == "measured" and roof["roof_src"].startswith("single") and abs(roof["h_pct"]["p50"] - 6.0) < 1e-6
    assert run(16.0, 1, 3)["status"] == "vegetation"     # several returns per pulse: a tree
    assert run(10.0, 2, 1)["status"] == "no_roof"        # ground inside the walls: nothing stands there
