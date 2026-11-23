"""Ledger 0102: Milford round 2 (Kevin's answers of 2026-11-22: "Build the 2.9 mi loop", "Reshape the shoulder").

  1. GM's loop as a second data folder of the source track (tracks/milford-road-course/data_gm): every station outside the
     splice is the committed line's, the new piece is short and narrow enough, the splice's own controls held.
  2. tools/measured_surface.py section: what the fit's plane misses across a stretch, recovered on a synthetic curved bank.
  3. tools/densify_ribbon_blend.py's route.densify.section: the product's delta by lateral offset and the span weight.
  4. tools/shoulder_grade_blend.py: wired into ship_track.sh after the far ground's prep and before the pads, opt-in.
  5. 0.1.15's config on round 1's 0.1.14 (source/round2/apply_0102.sh): GM's loop, the files an empty workshop needs, the
     committed lines the build will write, and where rounds 1 and 2 meet: the start / finish re-read on the GM lap, the pads
     re-outlined by their own tool (round 1's shading kept), the trees and colliders re-planned (round 1's tests).
stdlib + numpy only: bpy / bmesh / mathutils are stubbed where a Blender tool is imported.
"""

from __future__ import annotations

import importlib.util
import json
import hashlib
import math
import subprocess
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


# ------------------------------------------------------------------------------------------------ 5. the config (0.1.15)
def test_config_is_0_1_15_on_the_gm_loop_and_an_empty_workshop_gets_its_files():
    c = _j(MF / "track.config.json")
    li = c["lm_intake"]
    assert c["version"] == "0.1.15" and c["_version_doc"].startswith("0.1.15 (ledger 0102")
    assert li["source_data"] == "data_gm"
    assert li["measured_surface"]["file"] == "source/surface/road_surface_gm.fit.json"
    assert li["edge_fit"]["evidence"] == "source/edges/edge_evidence_gm.json"
    assert all(e["evidence"] == "source/edges/edge_evidence_gm.json" for e in li["edge_retrace"])
    assert li["edge_retrace"][0]["spans"] == [[4355.5, 150.0]]
    assert len(li["edge_retrace"][1]["spans"]) == 7 and [1228.0, 1237.0] not in li["edge_retrace"][1]["spans"]
    rails = {r["key"] for r in c["scenery"]["bespoke"]["rails"]}
    assert "t3_s1000_apron_back" not in rails and set(li["edge_retrace"][1]["rails"]) == rails
    sec = c["route"]["densify"]["section"]
    assert sec["file"] == "source/surface/road_section_gm.json" and sec["spans"] == [[870.0, 1030.0]]
    t = c["terrain"]
    assert t["lidar_shift_m"] == [-0.375, 0.938]
    sg = t["shoulder_grade"]
    assert (sg["from_m"], sg["full_m"], sg["to_m"], sg["max_fill_m"]) == (2.0, 15.0, 20.0, 1.0)
    assert sg["keep_patches"] == ["culvert_4349_w"] and "culvert_4349_w" in {q["id"] for q in t["lidar_patches"]}
    ship = _j(MF / "ship.json")
    for f in (li["measured_surface"]["file"], li["edge_fit"]["evidence"], sec["file"], sg["npz"]):
        assert f in ship["sync_in"]["required"], f
    assert {"data/densify_section.json", "data/shoulder_grade.json"} <= set(ship["sync_out"]["files"])


def test_edit_config_takes_only_round_1s_0_1_14(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"version": "0.1.15"}), encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(MF / "source" / "round2" / "edit_config_0102.py"), str(p)],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "0.1.14" in r.stdout + r.stderr


def test_the_committed_lines_are_the_ones_the_build_will_write():
    """data/centerline.raw.local.json + centerline.local.json = the intake (an empty workshop) and the draft's smoothing, byte
    for byte (predict_lines_0102.py --check runs the intake): every plan below is made on the lap that will be built"""
    r = subprocess.run([sys.executable, "-I", str(MF / "source" / "round2" / "predict_lines_0102.py"), "--check"], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout[-1500:], r.stderr[-1500:])


def test_the_start_finish_is_re_read_on_the_gm_lap():
    from scripts.geometry import circuit_start as cs
    c, loc = _j(MF / "track.config.json"), _j(MF / "data" / "centerline.local.json")
    pl = cs.plan(c["race_start"], loc)
    assert pl["problems"] == []
    assert abs(pl["lap_m"] - 4723.67) < 0.01 and abs(pl["line_station_m"] - 4465.28) < 0.01      # 0.1.14: 4,639.86 / 4,898.25
    slots = [v["station_m"] for k, v in pl["nodes"].items() if k.startswith(("AC_START_", "AC_PIT_"))]
    assert len(slots) == 40 and all(4300.0 < s < 4600.0 for s in slots)       # the front straight, far off the splice
    assert "s 4465.28" in c["race_start"]["_gm_loop_0102_doc"]


def test_the_pads_are_the_outliners_on_the_gm_line_and_keep_round_1s_shading():
    b = _j(MF / "track.config.json")["scenery"]["bespoke"]
    rec = _j(MF / "source" / "runoff" / "runoff_pads.json")
    kept = [x for x in rec["blobs"] if x["kept"]]
    assert [q["key"] for q in b["pads"]] == ["ride_pad"] + [x["key"] for x in kept] and len(kept) == 18
    assert {"runoff_L0883", "runoff_R0998", "runoff_L1175"}.isdisjoint(q["key"] for q in b["pads"])
    new = [x for x in kept if x["key"] in ("runoff_R0880", "runoff_R1008")]
    assert len(new) == 2 and all(x["naip_b_over_r"] >= rec["params"]["PAVED_B_OVER_R"] and x["folds"] == 0 for x in new)
    assert b["pads_shade"] == "smooth" and b["pads_shade_crease_deg"] == 10        # the block's keys: every pad, the new two
    assert rec["line"]["md5"] == hashlib.md5((MF / "data" / "centerline.raw.local.json").read_bytes()).hexdigest()


# ------------------------------------------- 6. the first rehearsal's red (milford_0115_reh, 2026-11-23): the two fixes
def test_nearest_station_finishes_the_ring_search():
    """measured_surface.Product._nearest stopped after ring 1 (6 m cells) once ring 0 / 1 held ANY station; a point more
    than a cell off the line could then take a farther one. Synthetic: the line along x, a point 7 m off it at x = 0.5,
    in a ring-1 cell that holds only a station 9 m back; its own station (x = 0) sits in ring 2"""
    import measured_surface as ms
    xs = [-9.0, 0.0, 1.5, 3.0]
    prod = {"s": [x + 9.0 for x in xs], "x": xs, "z": [-1.0] * 4, "nx": [0.0] * 4, "nz": [1.0] * 4, "c": [0.0] * 4,
            "b": [0.0] * 4, "lap_m": 1000.0}
    P = ms.Product(prod)
    P.grid = {(-2, 0): [0], (0, -1): [1, 2, 3]}           # station 0 in ring 1 of the point's cell (-1, 1); the rest in ring 2
    assert P._nearest(-0.5, 6.0) == 1


def test_section_points_on_the_inside_of_the_gm_turn_take_their_own_station():
    """the red's cause 1: at s 970-976, u >= +7.0 took product station s 966.0 (4-10 m back), the plane under it fell
    0.3-0.5 m and the section's delta stepped +0.27..+0.47 m from u +6.5 to +7.0 (the raw read and the 1 m grid: no step).
    Fixed, every such point takes a station within 1.5 m of its own, and the committed section has no such step"""
    import measured_surface as ms
    P = ms.Product(_j(MF / "source" / "surface" / "road_surface_gm.fit.json"))
    sec = _j(MF / "source" / "surface" / "road_section_gm.json")
    U = sec["offsets_m"]
    i65, i70 = U.index(6.5), U.index(7.0)
    seen = 0
    for i, s in enumerate(sec["s"]):
        if not 966.0 <= s <= 980.0:
            continue
        x, z, nx, nz = sec["x"][i], sec["z"][i], sec["nx"][i], sec["nz"][i]
        for u in (7.0, 7.5, 8.0, 9.0, 9.5):
            k = P._nearest(x + nx * u, z + nz * u)
            assert abs(P.s[k] - s) <= 1.5, (s, u, P.s[k])
            seen += 1
        assert sec["delta"][i][i70] - sec["delta"][i][i65] < 0.08, (s, sec["delta"][i][i65], sec["delta"][i][i70])
    assert seen >= 40


def test_seat_edges_section_rule():
    """the red's cause 2: tools/seat_edges_section.py, the rule tools/seat_edges_blend.py's opt-in route.seat_edges_section
    cuts by: the face's chord over the road, and cuts that bring a fold's excess (linear in the leg) under 1 cm"""
    import seat_edges_section as ses
    assert ses.stretch({}, 10.0) is None
    with pytest.raises(SystemExit):
        ses.stretch({"seat_edges_section": True}, 10.0)
    r = {"seat_edges_section": True, "densify": {"section": {"spans": [[870.0, 1030.0]], "taper_m": 15.0}}}
    assert ses.stretch(r, 10.0) == (845.0, 1055.0)
    assert ses.stations([[0, 0, 0], [3, 0, 4], [6, 0, 8], [9, 0, 12]], 4.0, 11.0) == [1, 2]
    g = ses.bary()
    assert len(g) == 15 and all(abs(sum(w) - 1.0) < 1e-12 for w in g)
    # a fold under a 1 m face: the road flat to x = 0.5, then rising 20 %; the corners at x 0, 1, 0 (road 0, 0.1, 0)
    road = lambda x: 0.2 * max(0.0, x - 0.5)
    corners = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    samples = [(w0, w1, w2, road(w0 * corners[0][0] + w1 * corners[1][0] + w2 * corners[2][0])) for w0, w1, w2 in g]
    e = ses.fold_excess([road(c[0]) for c in corners], samples)
    assert e == pytest.approx(0.05)                        # at x = 0.5 the chord stands 0.1 x 0.5 = 5 cm over the fold
    assert ses.cuts_for(e) == 4 and ses.cuts_for(0.009) == 0 and ses.cuts_for(1.0) == ses.MAX_CUTS
    assert ses.FOLD_TOL_M == 0.01 and ses.CLEAR_M == 0.02


def test_seat_edges_section_is_opt_in_only_milford_names_it_and_its_config_reproduces():
    text = (ROOT / "tools" / "seat_edges_blend.py").read_text(encoding="utf-8")
    assert "ses.stretch(cfg.get(\"route\") or {}, PAD_M)" in text and "def section_pass" in text
    for cfgp in sorted((ROOT / "tracks").glob("*/track.config.json")):
        route = _j(cfgp).get("route") or {}
        if cfgp.parent.name == "milford-road-course-lm":
            assert route["seat_edges_section"] is True and route["densify"]["section"]["spans"]
        else:
            assert "seat_edges_section" not in route, cfgp
    # the round-2 edit script writes the key, so the one-command flow from 0.1.14 keeps it
    src = (MF / "source" / "round2" / "edit_config_0102.py").read_text(encoding="utf-8")
    assert 'd["route"]["seat_edges_section"] = True' in src
    assert _j(MF / "track.config.json")["route"]["_seat_edges_section_doc"] in src.replace('"\n    "', "")


def test_daylight_edge_ref_is_opt_in_only_milford_names_it_and_its_config_reproduces():
    """ledger 0102 section 6: drive_test.daylight_edge_ref (the daylight probe hung from the road's own edge height, the
    second rehearsal's 69 readings on the bowl's banked side) is named by Milford only; every other track's drive_test
    reads the centre deck as before (tests/geometry/test_drive_test.py proves the report without the key)"""
    text = (ROOT / "scripts" / "geometry" / "drive_test.py").read_text(encoding="utf-8")
    assert '_daylight_edge_ref = bool((cfg.get("drive_test") or {}).get("daylight_edge_ref"))' in text
    assert "gy_probe, _own = surface.top_at(x + nx * off, z + nz * off, y_ref - 2.5, 5.0)" in text
    for cfgp in sorted((ROOT / "tracks").glob("*/track.config.json")):
        dt = _j(cfgp).get("drive_test") or {}
        if cfgp.parent.name == "milford-road-course-lm":
            assert dt["daylight_edge_ref"] is True
        else:
            assert "daylight_edge_ref" not in dt, cfgp
    src = (MF / "source" / "round2" / "edit_config_0102.py").read_text(encoding="utf-8")
    assert 'd.setdefault("drive_test", {})["daylight_edge_ref"] = True' in src
    assert _j(MF / "track.config.json")["drive_test"]["_daylight_edge_ref_doc"] in src.replace('"\n    "', "")
