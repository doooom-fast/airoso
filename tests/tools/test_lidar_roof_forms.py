"""tools/lidar_roof_forms.py (ledger 0083 pass 4) on drawn roofs, and the planner's / author's opt-in pass-4 keys. numpy only:
laspy / pyproj are imported inside extract_main(), never here."""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def _load(name, as_name=None):
    spec = importlib.util.spec_from_file_location(as_name or name, ROOT / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[as_name or name] = m
    spec.loader.exec_module(m)
    return m


rf = _load("lidar_roof_forms")
pb = _load("plan_buildings")

RING = [(-15.0, -5.0), (15.0, -5.0), (15.0, 5.0), (-15.0, 5.0)]      # 30 x 10 m, the long axis east


def _pts(fn, ring=RING, step=0.5, noise=0.03, seed=1):
    xs = np.arange(min(p[0] for p in ring) + 0.8, max(p[0] for p in ring) - 0.8, step)
    ys = np.arange(min(p[1] for p in ring) + 0.8, max(p[1] for p in ring) - 0.8, step)
    X, Y = np.meshgrid(xs, ys)
    X, Y = X.ravel(), Y.ravel()
    return X, Y, fn(X, Y) + np.random.default_rng(seed).normal(0.0, noise, X.shape)


def _fit(fn, ring=RING, rec=None, edge=None, stepped=False):
    x, y, h = _pts(fn, ring)
    ex, ey, eh = edge if edge is not None else (np.zeros(0), np.zeros(0), np.zeros(0))
    return rf.fit_one(ring, x, y, h, ex, ey, eh, rec or {"status": "measured"}, stepped)


def test_a_gable_along_the_long_axis_reads_its_eave_and_ridge():
    r = _fit(lambda x, y: 7.0 - 0.4 * np.abs(y))                      # eave 5.0 at the walls (|y| = 5), ridge 7.0
    assert r["form"] == "gable_long" and r["rms_m"] < 0.1
    g = r["fits"]["gable_long"]
    assert abs(g["ridge_m"] - 7.0) < 0.1 and abs(g["eave_m"] - 5.0) < 0.1


def test_a_gable_across_the_short_axis_and_a_hip_are_told_apart():
    assert _fit(lambda x, y: 9.0 - 0.2 * np.abs(x))["form"] == "gable_short"
    hip = _fit(lambda x, y: 8.0 - 0.5 * np.maximum(np.abs(y), np.abs(x) - 10.0))
    assert hip["form"] == "hip" and abs(hip["fits"]["hip"]["eave_m"] - 5.5) < 0.1


def test_the_trim_holds_the_roof_not_the_mean_a_low_wing_pulls_it_to():
    # osm1325614529 (pass 4's first fit): 83 % of a hall's roof at 13.45 m, the rest well under it. The least-squares level
    # (12.7) sat between the two; a trim about zero kept only the 1 % of points there and locked onto them
    x, y, h = _pts(lambda x, y: np.where(x < -9.0, 9.0, 13.45), noise=0.02)
    coef, _, kept, _ = rf.robust_fit(np.c_[np.ones(len(h))], h)
    assert abs(coef[0] - 13.45) < 0.05 and kept > 0.7


def test_a_shed_is_one_plane_and_a_flat_roof_stays_flat():
    shed = _fit(lambda x, y: 5.0 + 0.15 * y)
    assert shed["form"] == "shed" and abs(shed["fits"]["shed"]["gy"] - 0.15) < 0.01 and abs(shed["fits"]["shed"]["gx"]) < 0.01
    flat = _fit(lambda x, y: np.full(x.shape, 6.2))
    assert flat["form"] == "flat" and abs(flat["fits"]["flat"]["h_m"] - 6.2) < 0.05


def test_a_parapet_is_read_off_the_edge_band_and_none_is_none():
    ex = np.r_[np.linspace(-14.5, 14.5, 60), np.linspace(-14.5, 14.5, 60)]
    ey = np.r_[np.full(60, -4.7), np.full(60, 4.7)]
    up = _fit(lambda x, y: np.full(x.shape, 6.0), edge=(ex, ey, np.full(120, 7.1)))
    assert up["form"] == "flat" and abs(up["parapet_m"] - 1.1) < 0.1
    none = _fit(lambda x, y: np.full(x.shape, 6.0), edge=(ex, ey, np.full(120, 6.05)))
    assert none["parapet_m"] == 0.0
    # a taller neighbour's eave over ONE side (the four sides read, one of them 6 m up) is no parapet
    ex4 = np.r_[ex, np.full(40, -14.7), np.full(40, 14.7)]
    ey4 = np.r_[ey, np.linspace(-4.5, 4.5, 40), np.linspace(-4.5, 4.5, 40)]
    eh4 = np.r_[np.full(60, 12.0), np.full(60, 6.05), np.full(80, 6.05)]
    one = _fit(lambda x, y: np.full(x.shape, 6.0), edge=(ex4, ey4, eh4))
    assert one["parapet_m"] == 0.0 and len(one["edge"]["sides_p75_over_median_m"]) == 4


def test_two_levels_become_two_parts_covering_the_footprint():
    r = _fit(lambda x, y: np.where(x < 3.0, 5.0, 12.0))
    assert r["form"] == "parts" and len(r["parts"]) == 2
    assert sorted(round(p["h_m"]) for p in r["parts"]) == [5, 12]


def test_a_stepped_profile_keeps_its_slope_as_a_slope():
    ring = [(-40.0, -20.0), (40.0, -20.0), (40.0, 20.0), (-40.0, 20.0)]
    # flat 6 m to y = -8, a rise to 18 m at y = 4, flat 18 m beyond: three runs, the middle one sloped
    prof = lambda x, y: np.clip(6.0 + (y + 8.0), 6.0, 18.0)
    r = _fit(prof, ring=ring, stepped=True)
    forms = [p.get("form") for p in r["parts"]]
    assert r["form"] == "parts" and forms.count("shed") == 1 and len(forms) >= 3
    s = next(p for p in r["parts"] if p.get("form") == "shed")
    assert abs(abs(s["gy"]) - 1.0) < 0.15 and s["high_m"] - s["low_m"] > 8.0


def test_a_hillside_deck_is_read_over_its_low_ground():
    rec = {"status": "no_roof", "ground_m": 24.84, "ground_p10_p90": [18.74, 30.02], "ground_share": 0.005,
           "h_pct": {"p50": -1.21}}
    assert abs(rf.hillside_shift(rec) - 6.1) < 1e-6
    assert rf.hillside_shift(dict(rec, ground_share=0.9)) is None             # bare ground inside the walls: no deck
    assert rf.hillside_shift(dict(rec, ground_p10_p90=[24.0, 25.0])) is None  # level ground: not a hillside
    r = _fit(lambda x, y: np.full(x.shape, -1.2), rec=rec)
    assert r["hillside"]["shift_m"] == 6.1 and r["form"] == "flat" and abs(r["median_m"] - 4.9) < 0.1


def test_the_planner_stands_the_fitted_form():
    rec = {"status": "measured", "roof_src": "single returns, not ground", "n_roof": 400, "ground_m": 3.2, "ground_n": 90,
           "ground_ring_m": [1, 8], "h_pct": {"p05": 4.9, "p10": 5.0, "p25": 5.5, "p50": 6.0, "p75": 6.5, "p90": 6.8, "p95": 6.9,
                                              "p98": 7.0}, "levels": []}
    row = {"key": "a", "class": "shed", "form": "gable", "wall_h_m": 2.1, "ridge_h_m": 2.9, "_h": "class default [invented]"}
    g = {"form": "gable_short", "rms_m": 0.08, "fits": {"gable_short": {"eave_m": 5.02, "ridge_m": 7.04, "pitch": 0.2}}}
    out = pb.roof_form_rows(dict(row), rec, g, None)
    assert len(out) == 1 and out[0]["form"] == "gable" and out[0]["ridge_axis"] == "short"
    assert out[0]["wall_h_m"] == 5.0 and out[0]["ridge_h_m"] == 7.0
    flat = {"form": "flat", "rms_m": 0.1, "parapet_m": 0.0, "fits": {"flat": {"h_m": 6.0}}}
    f = pb.roof_form_rows(dict(row, form="flat_parapet", class_="commercial"), rec, flat, None)[0]
    assert f["form"] == "flat" and f["wall_h_m"] == 6.0 and "parapet_m" not in f
    par = pb.roof_form_rows(dict(row, form="flat"), rec, dict(flat, parapet_m=0.92), None)[0]
    assert par["form"] == "flat_parapet" and par["parapet_m"] == 0.92
    poor = pb.roof_form_rows(dict(row), rec, {"form": "poor", "rms_m": 0.9, "median_m": 6.04, "_poor": "flat"}, None)[0]
    assert poor["form"] == "flat" and poor["wall_h_m"] == 6.0 and poor["_fit"].startswith("poor")
    parts = {"form": "parts", "rms_m": 0.2, "_how": "levels", "parts": [
        {"footprint_lonlat": [[0, 0], [1, 0], [1, 1]], "h_m": 5.0, "n": 50, "rms_m": 0.1},
        {"footprint_lonlat": [[1, 0], [2, 0], [2, 1]], "h_m": 9.0, "n": 50, "rms_m": 0.1, "form": "shed", "low_m": 7.0,
         "high_m": 11.0, "ref_lonlat": [1.5, 0.5], "gx": 0.0, "gy": 1.0}]}
    pr = pb.roof_form_rows(dict(row), rec, parts, None)
    assert [r["key"] for r in pr] == ["a_p0", "a_p1"] and pr[0]["form"] == "flat" and pr[1]["form"] == "shed"
    assert pr[1]["wall_h_m"] == 7.0 and pr[1]["ridge_h_m"] == 11.0 and pr[1]["plane"]["gy"] == 1.0
    # no record (or no form): exactly lidar_rows
    assert pb.roof_form_rows(dict(row), rec, None, None) == pb.lidar_rows(dict(row), rec, None)
    assert pb.roof_form_rows(dict(row), {"status": "no_roof"}, {"form": None}, None) == []


def test_no_other_plan_names_the_pass_4_keys():
    for f in ROOT.glob("tracks/*/source/bespoke/buildings.plan.json"):
        plan = json.loads(f.read_text(encoding="utf-8"))
        if f.parts[-4] != "del-mar-lm":
            assert "roof_forms" not in plan and "roof_colour" not in plan, f


def test_no_other_track_overrides_the_roof_row():
    for f in ROOT.glob("tracks/*/track.config.json"):
        cfg = json.loads(f.read_text(encoding="utf-8"))
        if f.parent.name != "del-mar-lm":
            assert "ROOF" not in (cfg.get("texture_overrides") or {}), f


def test_a_naip_roof_maps_into_its_palette_cell():
    for name in ("bpy", "mathutils", "mathutils.bvhtree"):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules["mathutils"].Vector = object
    sys.modules["mathutils.bvhtree"].BVHTree = object
    ab = _load("author_bespoke_blend", "author_bespoke_blend_p4")
    rect = [0.1, 0.2, 0.11, 0.21]
    uv = [ab.naip_uv(rect, RING, p) for p in RING]
    assert uv[0] == (0.1, 0.2) and uv[2] == (0.11, 0.21)
    assert all(0.1 <= u <= 0.11 and 0.2 <= v <= 0.21 for u, v in uv)
