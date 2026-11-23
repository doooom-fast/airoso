"""Ledger 0102: Milford round 2 (Kevin's answers of 2026-11-22: "Build the 2.9 mi loop", "Reshape the shoulder").

  1. GM's loop as a second data folder of the source track (tracks/milford-road-course/data_gm): every station outside the
     splice is the committed line's, the new piece is short and narrow enough, the splice's own controls held.
  2. tools/measured_surface.py section: what the fit's plane misses across a stretch, recovered on a synthetic curved bank.
  3. tools/densify_ribbon_blend.py's route.densify.section: the product's delta by lateral offset and the span weight.
  4. tools/shoulder_grade_blend.py: wired into ship_track.sh after the far ground's prep and before the pads, opt-in.
stdlib + numpy only: bpy / bmesh / mathutils are stubbed where a Blender tool is imported.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "tracks" / "milford-road-course"
MF = ROOT / "tracks" / "milford-road-course-lm"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def _j(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _stub_blender():
    for name in ("bpy", "bmesh", "mathutils", "mathutils.bvhtree", "mathutils.kdtree"):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules["mathutils"].Vector = object
    sys.modules["mathutils.bvhtree"].BVHTree = object
    sys.modules["mathutils.kdtree"].KDTree = object


def _load(name, path):
    _stub_blender()
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------------------------------------- 1. GM loop
def test_gm_loop_keeps_every_station_outside_the_splice():
    old, new = _j(SRC / "data" / "centerline.local.json"), _j(SRC / "data_gm" / "centerline.local.json")
    rep = _j(SRC / "data_gm" / "splice.report.json")
    a, b_old = rep["splice"]["geojson_a"], rep["splice"]["geojson_b"]
    b_new = a + rep["splice"]["new_points"] + 1
    assert new["origin"] == old["origin"]
    pairs = [(i, i) for i in range(a + 1)] + [(b_old + k, b_new + k) for k in range(len(old["points_xyz_m"]) - b_old)]
    for i, j in pairs:
        po, pn = old["points_xyz_m"][i], new["points_xyz_m"][j]
        assert (po[0], po[2]) == (pn[0], pn[2])                              # the plan, bit for bit
        assert abs(po[1] - pn[1]) <= 0.025                                   # the profile's windows across the junction
    go, gn = _j(SRC / "data" / "centerline.geojson"), _j(SRC / "data_gm" / "centerline.geojson")
    co, cn = go["features"][0]["geometry"]["coordinates"], gn["features"][0]["geometry"]["coordinates"]
    assert cn[: a + 1] == co[: a + 1] and cn[b_new:] == co[b_old:]
    assert new["widths_m"][: a + 1] == old["widths_m"][: a + 1]
    assert new["widths_m"][b_new:] == old["widths_m"][b_old:]
    eo, en = _j(SRC / "data" / "centerline.elevation.json"), _j(SRC / "data_gm" / "centerline.elevation.json")
    assert en["z_raw_m"][: a + 1] == eo["z_raw_m"][: a + 1] and en["z_raw_m"][b_new:] == eo["z_raw_m"][b_old:]
    assert new["points_xyz_m"][0] == new["points_xyz_m"][-1]                 # still a closed loop (L13)


def test_gm_loop_length_and_the_new_piece():
    new = _j(SRC / "data_gm" / "centerline.local.json")
    P = [(p[0], p[2]) for p in new["points_xyz_m"]]
    lap = sum(math.dist(p, q) for p, q in zip(P, P[1:]))
    # GM's "2.9 mi" is 4,667 m; OSM's older ways 4,710 m on the PC's projection; ours was 4,900.7 m on this line
    assert 4700.0 < lap < 4760.0
    rep = _j(SRC / "data_gm" / "splice.report.json")
    a = rep["splice"]["geojson_a"]
    piece = new["widths_m"][a + 1: a + 1 + rep["splice"]["new_points"]]
    assert min(piece) >= 9.0 and max(piece) <= 16.0                          # to_fixes.py's clamp
    assert rep["controls"]["profile_dev_m"] <= 0.0101 and rep["controls"]["projection_dev_m"] <= 0.0101
    # no 3 m turn on the new piece sharper than the lap's own sharpest + 2 deg (the joins are blended)
    def turn(i):
        h0 = math.atan2(P[i][1] - P[i - 1][1], P[i][0] - P[i - 1][0])
        h1 = math.atan2(P[i + 1][1] - P[i][1], P[i + 1][0] - P[i][0])
        return abs((math.degrees(h1 - h0) + 180) % 360 - 180)
    b = a + rep["splice"]["new_points"] + 1
    kept = max(turn(i) for i in list(range(1, a)) + list(range(b + 2, len(P) - 1)))
    assert max(turn(i) for i in range(a, b + 1)) <= kept + 2.0


# ------------------------------------------------------------------------------------------------------- 2. section
def test_section_recovers_what_the_plane_misses():
    np = pytest.importorskip("numpy")
    import measured_surface as ms
    n, step = 400, 0.5
    s = [i * step for i in range(n)]
    offs = [-6.0, -3.0, 0.0, 3.0, 6.0]
    c, b, q = 10.0, -0.20, 0.03                    # the plane and the curvature it misses: y = c + u b + q u^2
    product = {"line_md5": "x", "lap_m": 10000.0, "s": s, "x": s, "z": [0.0] * n, "nx": [0.0] * n, "nz": [1.0] * n,
               "c": [c] * n, "b": [b] * n}
    wide = {"inputs": {"line_md5": "x"}, "step_m": step, "s": s, "x": s, "z": [0.0] * n, "nx": [0.0] * n,
            "nz": [1.0] * n, "paths": {f"{u:+.1f}": {"y_m": [c + u * b + q * u * u] * n} for u in offs}}
    out = ms.section(wide, product)
    i = len(out["s"]) // 2
    for u, d in zip(out["offsets_m"], out["delta"][i]):
        assert d == pytest.approx(q * u * u, abs=1e-3)
    with pytest.raises(SystemExit):
        ms.section(dict(wide, inputs={"line_md5": "other"}), product)


# -------------------------------------------------------------------------------------------- 3. densify's Section
def test_densify_section_delta_and_weight(tmp_path):
    dr = _load("densify_ribbon_blend_t", ROOT / "tools" / "densify_ribbon_blend.py")
    prod = {"offsets_m": [-4.0, 0.0, 4.0], "s": [0.0, 10.0, 20.0], "x": [0.0, 10.0, 20.0], "z": [0.0, 0.0, 0.0],
            "nx": [0.0, 0.0, 0.0], "nz": [1.0, 1.0, 1.0], "delta": [[0.4, 0.0, -0.2]] * 3}
    (tmp_path / "sec.json").write_text(json.dumps(prod), encoding="utf-8")
    sec = dr.Section(tmp_path, {"file": "sec.json", "spans": [[5.0, 15.0]], "taper_m": 10.0, "reach_m": 2.0})
    assert sec.delta(1, -2.0) == pytest.approx(0.2)
    assert sec.delta(1, 4.5) == pytest.approx(-0.2)                         # within reach past the last offset
    assert sec.delta(1, 7.0) == 0.0                                          # beyond it: nothing
    assert sec.weight(10.0) == 1.0 and sec.weight(25.0) == 0.0
    assert 0.0 < sec.weight(0.0) < 1.0
    assert sec.at(10.2, 0.3)[0] == 1


# -------------------------------------------------------------------------------------------------- 4. the shoulder
def test_shoulder_step_is_wired_opt_in_and_in_order():
    sh = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")
    i_fg = sh.index("tools/far_ground_prep_blend.py")
    i_sh = sh.index("tools/shoulder_grade_blend.py")
    i_pads = sh.index("tools/seat_pads_blend.py")
    i_reseat = sh.index("tools/reseat_bespoke_blend.py")
    assert i_fg < i_sh < i_pads < i_reseat
    block = sh[sh.rfind("\n  rm -f", 0, i_sh): i_sh]
    assert "get('shoulder_grade')" in block and "shoulder_grade.json" in block


def test_shoulder_helpers():
    pytest.importorskip("numpy")
    sg = _load("shoulder_grade_blend_t", ROOT / "tools" / "shoulder_grade_blend.py")
    sq = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert sg.poly_dist(sq, 5.0, 5.0) == 0.0
    assert sg.poly_dist(sq, 13.0, 5.0) == pytest.approx(3.0)
    assert sg.smoothstep(0.0) == 0.0 and sg.smoothstep(1.0) == 1.0 and sg.smoothstep(0.5) == pytest.approx(0.5)
