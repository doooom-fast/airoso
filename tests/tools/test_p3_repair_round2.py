"""Ledger 0054 P3 repair round 2 (2026-10-19): the truth lens's refutation of round 1, each fix at its cause.

* tools/aerial_paint_north.py — the yellow centre paint of the undivided north roads is MEASURED off NAIP: a stacked
  cross profile in a smooth frame (the station line is OSM's chords), its yellow stretches read as a painted median's two
  faces, a narrow median blurred into one stretch, or one double yellow; stray readings (a painted curb return, a yellow
  car, a shadowed face) are dropped and short gaps interpolated (the lens: Jackson's painted median ~1.65 m to one side
  for ~1 km; Princess View's 5 m centre lane painted as one double yellow).
* tools/author_expansion.py — the measured paint replaces the eye-interpolated centre of every undivided station of
  Princess View and Jackson; the raised islands the aerial shows (MEASURED_ISLANDS) replace the dossier's misplaced
  Fontaine nose; the committed intermediate carries what it took.
* tools/ground_release_blend.py — a raise-only cut's batter rises from the back of the WALK, not the foot of its buried
  apron (the lens: Mission Gorge's south rock face 1.2-1.5 m short 18-20 m out).
* p3-proofs/measure_p3.py — the pads read on the plan's own ground-guide points (the lens's J3 0.226 m, not 0.17).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import aerial_paint_north as apn  # noqa: E402
import author_expansion as ae  # noqa: E402

TRACK = ROOT / "tracks" / "san-diego-lake-murray"


def _profile(lines, lo=-8.0, hi=8.0, bg=-5.0, peak=20.0, half_w=0.35):
    """a cross profile [(offset, yellowness)]: asphalt at bg, each line a flat-topped stretch of +-half_w at peak"""
    out = []
    o = lo
    while o <= hi + 1e-9:
        v = bg
        for c in lines:
            if abs(o - c) <= half_w:
                v = peak
        out.append((round(o, 2), v))
        o += apn.DL_M
    return out


# --- reading one stacked profile -------------------------------------------------------------------------------------
def test_two_faces_read_as_a_painted_median_at_their_middle():
    q = apn.read_segments(apn.segments(_profile([0.2, 3.6])), 0.0)
    assert q[0] == "median"
    assert abs(q[1] - 1.9) < 0.06 and abs(q[2] - (3.4 + 2 * apn.FACE_IN_M)) < 0.12


def test_one_narrow_stretch_is_a_double_yellow_and_one_wide_stretch_a_narrow_median():
    q = apn.read_segments(apn.segments(_profile([1.0])), 0.0)
    assert q[0] == "line" and abs(q[1] - 1.0) < 0.06
    wide = apn.read_segments(apn.segments(_profile([2.0], half_w=1.2)), 0.0)        # 2.4 m: two faces blurred
    assert wide[0] == "median" and abs(wide[1] - 2.0) < 0.06
    blurred = apn.read_segments(apn.segments(_profile([2.0], half_w=0.65)), 0.0)    # 1.3 m: one double yellow
    assert blurred[0] == "line"


def test_nothing_yellow_reads_nothing():
    assert apn.read_segments(apn.segments(_profile([])), 0.0) is None


def test_the_smooth_frame_measures_a_chord_kink():
    rows = []
    for k in range(81):                                  # a straight line with one 6 deg kink at its middle
        s = 2.5 * k
        x = 0.0 if s <= 100 else (s - 100) * 0.1045
        rows.append({"x": x, "z": min(s, 100) + (s - 100) * 0.9945 if s > 100 else s})
    d = apn.smooth_frame(rows, apn.FRAME_SIGMA_M)
    assert abs(d[0]) < 0.05 and abs(d[40]) > 0.3          # the smooth line cuts the kink's corner
    assert max(abs(v) for v in d) < 1.0


def test_clean_drops_a_stray_reading_and_interpolates_a_short_gap():
    recs = []
    for k in range(40):
        s = 2.5 * k
        r = {"s": s, "built_off_m": 0.0, "raised": False}
        if k == 10:
            r.update({"kind": "line", "centre_off_m": 4.2, "width_m": 0.0})        # a painted curb return
        elif 20 <= k <= 24:
            pass                                                                    # 12.5 m under a tree shadow
        else:
            r.update({"kind": "median", "centre_off_m": 1.6, "width_m": 4.6})
        recs.append(r)
    apn.clean(recs)
    assert recs[10].get("dropped") == "outlier" and recs[10]["use"]["how"] == "interpolated"
    assert all(recs[k]["use"]["how"] == "interpolated" and abs(recs[k]["use"]["centre_off_m"] - 1.6) < 1e-6
               for k in range(20, 25))
    assert recs[0]["use"] == {"kind": "median", "centre_off_m": 1.6, "width_m": 4.6, "how": "read"}


def test_clean_drops_what_is_off_the_road_centre():
    recs = [{"s": 2.5 * k, "built_off_m": -0.7, "raised": False, "kind": "median", "centre_off_m": -8.6, "width_m": 2.0}
            for k in range(6)]
    apn.clean(recs)
    assert all(r.get("dropped") == "off the road's centre" and "use" not in r for r in recs)


# --- what the intermediate takes -------------------------------------------------------------------------------------
def test_measured_paint_replaces_the_centre_of_undivided_stations_only():
    recs = [{"s": s, "mtype": t, "m": 3.0, "moff": 0.0, "paint_src": "eye"}
            for s, t in ((300.0, "painted"), (302.5, "line"), (305.0, "hatched"), (307.5, "planted"))]
    measured = {"D": {300.0: {"kind": "median", "centre_off_m": 1.65, "width_m": 4.66, "how": "read"},
                      302.5: {"kind": "line", "centre_off_m": 2.4, "width_m": 0.0, "how": "interpolated"},
                      305.0: {"kind": "median", "centre_off_m": 1.0, "width_m": 3.5, "how": "read"},
                      307.5: {"kind": "median", "centre_off_m": 9.0, "width_m": 9.0, "how": "read"}}}
    n_paint, n_isl = ae.apply_paint_measured("D", recs, measured)
    assert (n_paint, n_isl) == (3, 0)
    assert (recs[0]["mtype"], recs[0]["moff"], recs[0]["m"]) == ("painted", 1.65, 4.66)
    assert (recs[1]["mtype"], recs[1]["moff"], recs[1]["m"]) == ("line", 2.4, 0.0)
    assert recs[2]["mtype"] == "hatched"                         # the J4 hatching stays hatched
    assert (recs[3]["mtype"], recs[3]["moff"]) == ("planted", 0.0)  # a raised median is never re-read
    assert ae.apply_paint_measured("A", recs, {"A": measured["D"]}) == (0, 0)   # Waring keeps its raised median


def test_a_measured_island_takes_its_outline_less_the_edge_paint():
    recs = [{"s": s, "mtype": "line", "m": 0.0, "moff": 0.0, "paint_src": "eye"} for s in (400.0, 402.5, 405.0)]
    measured = {"B": {400.0: {"kind": "median", "centre_off_m": 0.4, "width_m": 4.56, "how": "read"},
                      405.0: {"kind": "line", "centre_off_m": 0.3, "width_m": 0.0, "how": "read"}}}
    ae.apply_paint_measured("B", recs, measured)
    w = 4.56 - 2 * ae.FACE_IN_M - 2 * ae.ISLAND_EDGE_M
    assert all(r["mtype"] == "nose" for r in recs)
    assert abs(recs[0]["m"] - w) < 1e-9 and recs[0]["moff"] == 0.4
    assert recs[1]["m"] == recs[0]["m"] and recs[2]["m"] == recs[0]["m"]    # no reading inside: the island carries on


def test_the_committed_intermediate_took_the_measured_paint():
    d = json.loads((TRACK / "data" / "expansion.north.json").read_text(encoding="utf-8"))
    assert "aerial__paint_north.json" in d["provenance"]
    pcs = {p["id"]: p for p in d["pieces"]}
    assert pcs["A"]["paint_measured"] == {"stations_paint": 0, "stations_island": 0}
    assert pcs["C"]["paint_measured"] == {"stations_paint": 0, "stations_island": 0}
    assert pcs["B"]["paint_measured"]["stations_paint"] > 250 and pcs["B"]["paint_measured"]["stations_island"] > 60
    assert pcs["D"]["paint_measured"]["stations_paint"] > 600
    D = [dict(zip(pcs["D"]["columns"], r)) for r in pcs["D"]["stations"]]
    climb = [r["median_off_m"] for r in D if 900 <= r["s"] <= 1300 and r["median_type"] == "painted"]
    assert len(climb) > 100 and 1.0 <= sorted(climb)[len(climb) // 2] <= 2.2       # the lens: real centre ~+1.65 m
    B = [dict(zip(pcs["B"]["columns"], r)) for r in pcs["B"]["stations"]]
    lane = [r["median_w_m"] for r in B if 860 <= r["s"] <= 990]
    assert min(lane) >= 4.5                                                          # the 5-6 m centre lane


def test_the_paint_measurement_records_its_windows_and_thresholds():
    p = json.loads((TRACK / "source" / "expansion" / "aerial__paint_north.json").read_text(encoding="utf-8"))
    assert p["windows"] and all(w["url"].startswith("https://imagery.nationalmap.gov/") for w in p["windows"])
    for k in ("SEG_MIN", "MEDIAN_SEP_M", "MEDIAN_MIN_M", "FRAME_SIGMA_M", "OUTLIER_M", "GAP_MAX_M", "SANITY_M"):
        assert k in p["parameters"], k
    gc = (ROOT / "fleet" / "GATES-CHANGELOG.md").read_text(encoding="utf-8")
    for k in ("SEG_MIN", "MEDIAN_MIN_M", "FRAME_SIGMA_M", "OUTLIER_M", "GAP_MAX_M", "SANITY_M", "CENTRE_CLEAR_M"):
        assert k in gc, k


# --- the raise-only batter's origin ----------------------------------------------------------------------------------
def test_a_raise_only_cut_has_a_fine_toe():
    """the cut face's toe on 1 m facets within 5 m of the pavement (on 2.5 m facets one facet rose 1.2-1.55 m per metre
    behind Mission Gorge's south walk, not the batter's 2: 1.1-1.5 m short 18-20 m out)"""
    src = (ROOT / "tools" / "ground_release_blend.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert "CUT_SUBDIV_M = 1.0" in src and "CUT_NEAR_M = 5.0" in src
    i = src.index("n_cut_sub = 0")
    blk = src[i:i + 1400]
    assert 'zn_.get("raise_only")' in blk and "flat.find_nearest((mx, my, 0.0), CUT_NEAR_M)" in blk
    assert i < src.index("# 2. released heights")
    assert '"cut_toe_edges_halved": n_cut_sub' in src
    gc = (ROOT / "fleet" / "GATES-CHANGELOG.md").read_text(encoding="utf-8")
    assert "CUT_SUBDIV_M" in gc and "CUT_NEAR_M" in gc


def test_the_pad_measure_reads_the_plans_own_guide_points():
    src = (TRACK / "source" / "expansion" / "p3-proofs" / "measure_p3.py").read_text(encoding="utf-8")
    assert 'res["pads"]' in src and '_p["ground"]["xz"]' in src and '"1ROAD_PAD_" + _p["id"]' in src


# --- the kn5 writer's own vertex count (the engine-july snapshot prep, PENDING MIRROR) --------------------------------
def _prep_src():
    return (TRACK / "engine-july-snapshot" / "scripts" / "ac" / "build_kn5_loop.py").read_text(
        encoding="utf-8").replace("\r\n", "\n")


def test_the_writer_count_is_the_unique_corner_keys():
    src = _prep_src()
    i = src.index("def export_vertex_count(face_keys):")
    ns = {}
    exec(src[i:src.index("\n\n\n", i)], ns)
    flat_box_face = [[(0, (0, 0, 1), (0, 0), (1, 0, 0)), (1, (0, 0, 1), (1, 0), (1, 0, 0))],
                     [(1, (1, 0, 0), (1, 0), (0, 1, 0)), (0, (1, 0, 0), (0, 0), (0, 1, 0))]]
    assert ns["export_vertex_count"](flat_box_face) == 4          # two Blender vertices, four writer vertices
    assert ns["export_vertex_count"]([flat_box_face[0], flat_box_face[0]]) == 2


def test_a_mesh_past_the_writer_cap_is_tiled_under_unique_names_before_export():
    src = _prep_src()
    assert "def _export_vertex_keys(me):" in src and "def _split_for_writer(ob, cap=SPLIT_CAP):" in src
    i = src.index("assert_under_cap(ob.name, len(me.vertices))")
    j = src.index("for t in _split_for_writer(ob):", i)
    assert j - i < 600 and "assert_under_cap(t.name, export_vertex_count(_export_vertex_keys(t.data)[0]))" in src[j:j + 200]
    assert 'nm = bpy.data.meshes.new(f"{base}_{k}")' in src[src.index("def _split_for_writer"):]
    k = src.index("from scripts.ac import pbr\n    overrides")
    assert j < k                                                 # tiles exist before the materials pass
    pend = (TRACK / "engine-july-snapshot" / "PENDING-MIRROR.md5").read_text()
    assert "scripts/ac/build_kn5_loop.py" in pend
