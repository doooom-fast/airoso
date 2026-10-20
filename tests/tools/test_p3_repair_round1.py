"""Ledger 0054 P3 repair round 1 (2026-10-19): the fixes for the three lenses' refutation, each at its cause.

* tools/terrain_mend.py — a vertical sliver (a T-vertex on a face's straight edge, cut into an ear by BEAUTY) is found;
  a real triangle and a seat curtain's vertical edge are not (the view lens's see-through slit on Jackson north).
* tools/ground_release.py AUTO CUTS — the real walls beside the north pieces become raise-only cut zones over every
  stretch they stand on, padded, their batter the face's own climb held to 1-2 m per metre (the truth lens: walls planed
  past the six hand zones' ends and at ten more places; Mission Gorge's rock face held to half its height by 1:1).
* tools/junction_pad.py — the pad's ground guide (3DEP inside the outline, a quadratic fit) the deck is stretched over
  (the truth lens: J4 0.32-0.43 m over the real ground).
* tools/expansion_lines.py — a line's turn through a pad stays inside the curb (the gates lens: the forward line's
  kinks were its own wheel paths climbing the J2 / J3 / J4 curb returns; the late travel_kinks exemption is gone).
* scripts/geometry/drive_test.py run_lines — the verdict is the documented LINE GATE (+ excursions per km), drive_test's
  own lap rule written beside it with its reasons, every uncounted reading written with its place.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import expansion_lines as el  # noqa: E402
import expansion_pieces as ep  # noqa: E402
import ground_release as gr  # noqa: E402
import junction_pad as jp  # noqa: E402
import terrain_mend as tm  # noqa: E402


# --- terrain_mend ---------------------------------------------------------------------------------------------------
def test_a_t_vertex_on_the_straight_edge_is_a_vertical_sliver():
    assert tm.collinear_middle([(0.0, 0.0), (1.0, 0.0), (2.5, 0.0)]) == 1
    assert tm.collinear_middle([(2.5, 0.0), (0.0, 0.0), (1.0, 0.0005)]) == 2     # within LINE_TOL_M of the line


def test_a_real_triangle_or_a_curtain_edge_is_not():
    assert tm.collinear_middle([(0.0, 0.0), (1.0, 0.05), (2.0, 0.0)]) is None     # 5 cm off the line: a real face
    assert tm.collinear_middle([(0.0, 0.0), (0.0, 0.0), (2.0, 0.0)]) is None      # two corners on one plan point
    assert tm.collinear_middle([(0.0, 0.0), (3.0, 0.0), (5.0, 0.0)]) == 1


def test_the_mend_runs_in_the_triangulation_and_the_release():
    tri = (ROOT / "tools" / "triangulate_terrain_blend.py").read_text(encoding="utf-8")
    rel = (ROOT / "tools" / "ground_release_blend.py").read_text(encoding="utf-8")
    assert "terrain_mend.mend_vertical_slivers(bm)" in tri
    assert rel.count("terrain_mend.mend_vertical_slivers(bm)") == 2       # after the halving, after the heights
    assert '"vertical_slivers_mended"' in rel


# --- AUTO CUTS -------------------------------------------------------------------------------------------------------
def _piece(L=400.0, step=5.0):
    rows = []
    s = 0.0
    while s <= L + 1e-9:
        rows.append([s, 0.0, s, 10.0, 10.0, 6.0, -6.0])          # straight north along x = 0, the road at y 10
        s += step
    return ep.Piece({"id": "C", "columns": ["s", "x", "z", "y_3dep", "y_smooth", "left_m", "right_m"],
                     "stations": rows, "cuts": {"start": {"s": 0.0}, "end": {"s": L}}})


def _ground(wall_from, wall_to, rise_per_m=1.5, top=6.0):
    """3DEP: level at the road, a wall on the RIGHT (x > 0 is right of northward travel) between two stations"""
    def h(key):
        x, z = key[0] * gr.CELL_M, key[1] * gr.CELL_M
        if wall_from <= z <= wall_to and x > 6.0:
            return 10.0 + min(top, rise_per_m * max(0.0, x - 8.0))
        return 10.0
    return h


def test_auto_cuts_declare_a_padded_raise_only_zone_over_a_wall():
    pcs = {"C": _piece()}
    ac = {"pieces": ["C"]}
    probes = gr.probe_points(pcs, ac)
    zones, st = gr.detect_cuts(pcs, ac, probes, _ground(150.0, 250.0))
    assert zones, st[:3]
    right = [z for z in zones if z["sides"] == ["right"]]
    assert right and not [z for z in zones if z["sides"] == ["left"]]
    a, b = right[0]["piece_s_m"][0], right[-1]["piece_s_m"][1]
    assert a <= 150.0 - gr.AUTO_DEFAULTS["pad_m"] + 5.0 + 1e-6 and b >= 250.0 + gr.AUTO_DEFAULTS["pad_m"] - 5.0 - 1e-6
    for z in right:
        assert z["raise_only"] and z["rails"] is False and z["auto"] and z["kind"] == "bank"
        assert z["line"] == "north_mission_gorge" and z["piece"] == "C"
        assert gr.AUTO_DEFAULTS["cut_slope_min"] <= z["cut_slope"] <= gr.AUTO_DEFAULTS["cut_slope_max"]
        assert z["measured"]["max_rise_m"] >= gr.AUTO_DEFAULTS["min_rise_m"]
    # the batter is the construction maximum (a bound only); the face's own climb (1.5 m per metre) is recorded
    assert all(z["cut_slope"] == gr.AUTO_DEFAULTS["cut_slope_max"] for z in right)
    assert max(z["measured"]["face_p90_m_per_m"] for z in right) == 1.5
    # ...and with batter "face" the face's own climb is the batter (windowed, rounded to 0.25)
    zf, _ = gr.detect_cuts(pcs, dict(ac, batter="face"), probes, _ground(150.0, 250.0))
    assert max(z["cut_slope"] for z in zf if z["sides"] == ["right"]) == 1.5


def test_auto_cuts_hold_the_batter_to_the_construction_range_and_ignore_a_bump():
    pcs = {"C": _piece()}
    ac = {"pieces": ["C"]}
    probes = gr.probe_points(pcs, ac)
    zones, _st = gr.detect_cuts(pcs, ac, probes, _ground(100.0, 300.0, rise_per_m=5.0))
    assert zones and all(z["cut_slope"] == gr.AUTO_DEFAULTS["cut_slope_max"] for z in zones)
    zones, _st = gr.detect_cuts(pcs, ac, probes, _ground(200.0, 202.0))       # one station: a bump, not a wall
    assert zones == []


def test_resolve_zones_carries_raise_only_and_refuses_what_is_not_a_cut():
    main = [(0.0, 0.0, float(z)) for z in range(0, 401, 5)]
    base = {"name": "x", "kind": "bank", "s_m": [10, 50], "sides": ["right"], "reach_m": 40.0, "cut_reach_m": 20.0,
            "rails": False, "raise_only": True, "cut_slope": 1.75}
    z = gr.resolve_zones({}, main, extra=[base])[0]
    assert z["raise_only"] is True and z["cut_slope"] == 1.75
    for bad in (dict(base, rails=True), dict(base, cut_slope=2.5), {k: v for k, v in base.items() if k != "cut_reach_m"}):
        try:
            gr.resolve_zones({}, main, extra=[bad])
        except SystemExit:
            continue
        raise AssertionError(bad)


def test_lake_murray_declares_auto_cuts_on_all_four_pieces_and_no_hand_cut_zone():
    cfg = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json").read_text(encoding="utf-8"))
    g = cfg["terrain"]["ground_release"]
    assert g["auto_cuts"]["pieces"] == ["A", "B", "C", "D"]
    names = [z["name"] for z in g["zones"]]
    assert not [n for n in names if n.startswith(("mission_gorge_cut_", "jackson_cut_"))]
    blend = (ROOT / "tools" / "ground_release_blend.py").read_text(encoding="utf-8")
    assert 'zone.get("raise_only")' in blend and 'zr.get("raise_only")' in blend and 'zr.get("cut_slope")' in blend


# --- the pads' ground guide -----------------------------------------------------------------------------------------
def test_the_ground_guide_fits_a_tilted_bowl_and_reads_inside_the_outline_only():
    g = jp.fit_quadratic([(x, z, 5.0 + 0.04 * x - 0.02 * z + 0.001 * x * z) for x in range(0, 30, 3) for z in range(0, 30, 3)])
    assert abs(g(12.0, 7.0) - (5.0 + 0.48 - 0.14 + 0.084)) < 1e-9
    sq = [(0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0)]
    pts = jp.ground_grid(sq, 2.0)
    assert all(jp.inside(sq, x, z) for x, z in pts) and len(pts) == 100
    assert not jp.inside(sq, 25.0, 5.0)


def test_the_screened_film_is_the_plain_film_without_pull_and_the_ground_with_it():
    import apron as ap_
    # a 5 x 5 grid, its border fixed at 0, a ground guide at 1 m everywhere
    xz = [(float(i), float(j)) for j in range(5) for i in range(5)]
    tris = []
    for j in range(4):
        for i in range(4):
            a, b, c, d = j * 5 + i, j * 5 + i + 1, (j + 1) * 5 + i + 1, (j + 1) * 5 + i
            tris += [(a, b, c), (a, c, d)]
    fixed = {k: 0.0 for k, (x, z) in enumerate(xz) if x in (0.0, 4.0) or z in (0.0, 4.0)}
    guess = [0.0] * 25
    plain = ap_.harmonic_heights(25, tris, fixed, guess, xz=xz)
    same = jp.screened_heights(25, tris, fixed, guess, xz, [1.0] * 25, [0.0] * 25)
    assert max(abs(a - b) for a, b in zip(plain, same)) < 1e-6
    pulled = jp.screened_heights(25, tris, fixed, guess, xz, [1.0] * 25, [5.0] * 25)
    centre = 12
    assert 0.5 < pulled[centre] < 1.0 and all(pulled[k] == 0.0 for k in fixed)      # toward the ground, seams exact
    w = jp.guide_weight([(0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0)])
    assert w(10.0, 10.0) == 1.0 and w(0.5, 10.0) < 0.1 and w(25.0, 10.0) == 0.0


def test_the_pad_deck_is_pulled_to_the_ground_only_as_far_as_its_steepness_and_seams_allow():
    src = (ROOT / "tools" / "author_junction_pad_blend.py").read_text(encoding="utf-8")
    assert "def film(outline, heights, fixed, what, guide=None, weight=None, lam=0.0):" in src
    assert "for lam in (jp.GUIDE_LAMBDAS if guide is not None else (0.0,)):" in src
    assert "if steep <= seam_grade + GRADE_OVER_SEAMS and crease <= max(crease0, CREASE_MAX):" in src
    assert '"ground_guide"' in src and '"seam_crease_pct"' in src and "def seam_crease(" in src
    assert jp.GUIDE_LAMBDAS[-1] == 0.0 and list(jp.GUIDE_LAMBDAS) == sorted(jp.GUIDE_LAMBDAS, reverse=True)
    plan = (ROOT / "tools" / "junction_pad.py").read_text(encoding="utf-8")
    assert '"ground": ground' in plan and "ground guide" in plan


# --- the lines stay inside the pads' curbs ---------------------------------------------------------------------------
def test_a_carriageway_edge_is_held_off_a_curb_face_and_the_rest_is_untouched():
    P = [(0.0, 0.0, float(z)) for z in range(0, 61, 3)]
    W = [12.0] * len(P)
    # a curb face 4 m right of the line (x = +4: right of northward travel is +x) between z 24 and 36
    segs = [((4.0, 24.0), (4.0, 30.0)), ((4.0, 30.0), (4.0, 36.0))]
    Q, W2, n = el.keep_inside_curbs(P, W, segs)
    assert n > 0
    for (x, _y, z), w in zip(Q, W2):
        right_edge = x + w / 2.0                    # the line's right edge (+x)
        if 24.0 <= z <= 36.0:
            assert right_edge <= 4.0 - el.CURB_CLEAR_M + 1e-6, (z, x, w)
            assert w >= el.MIN_W_M - 1e-6
            assert abs((x - w / 2.0) - (-6.0)) < 1e-6 or w == el.MIN_W_M     # the left edge stays
    # far from the face nothing moves
    assert Q[0] == P[0] and W2[0] == 12.0 and Q[-1] == P[-1] and W2[-1] == 12.0
    assert el.keep_inside_curbs(P, W, [])[2] == 0


def test_the_pads_curb_faces_are_the_outlines_edge_runs():
    pads = {"pads": [{"outline_xz": [[0, 0], [1, 0], [2, 0], [2, 1], [0, 1]],
                      "kind": ["edge", "edge", "cut", "edge", "edge"]}]}
    segs = el.curb_segments(pads)
    assert ((0, 0), (1, 0)) in [tuple(map(tuple, s)) for s in segs] and len(segs) == 3   # 0-1, 3-4, 4-0


# --- drive_test --line: one documented verdict, nothing hidden --------------------------------------------------------
def test_the_line_gate_has_no_late_exemption_and_writes_what_it_does_not_count():
    src = (ROOT / "scripts" / "geometry" / "drive_test.py").read_text(encoding="utf-8")
    assert "travel_kinks" not in src
    assert '"fold_kinks_all"' in src and '"excursions_all"' in src and '"soft_top_all"' in src
    assert "LINE_EXC_PER_KM = 7.12" in src and '"drive_test_rule_reasons"' in src
    assert "fail = drive_test's rule or EXPANSION-PLAN V6" not in src            # the old, wrong _doc
    assert "plus every rule of the lap gate" not in src                           # the old, wrong comment


def test_a_raise_only_cut_keeps_the_prep_contact_band_buries_the_apron_and_collapses_curtains():
    """repair round 1's first rehearsal: in the cut zones the grass behind every walk stood 0.2-0.35 m low (the prep
    leaves zone ground alone, and the per-face cap held it under the walk's buried apron) — 0.14 m drops off the walk
    (excursions 39 -> 60) — and 780 seat curtains stood (each vertex raised from its own sheet)"""
    src = (ROOT / "tools" / "ground_release_blend.py").read_text(encoding="utf-8")
    assert "PREP_BAND_M = 3.0" in src and "PREP_FEATHER_M = 6.0" in src
    assert "nz = max(nz, (n3[0].z - CLEAR_M) * wb + z0 * (1.0 - wb))" in src
    assert "nz = min(max(nz, z0), cut[0])" in src
    assert "top_walk = BVHTree.FromPolygons(dv, wfaces)" in src and "def walk_face(f):" in src
    assert "z = low_at[(round(x, 4), round(y, 4))]" in src
    prep = (ROOT / "tracks" / "san-diego-lake-murray" / "engine-july-snapshot" / "scripts" / "ac" /
            "build_kn5_loop.py").read_text(encoding="utf-8")
    assert "BAND_M = 3.0" in prep and "FEATHER_M = 6.0" in prep          # the numbers it copies


def test_the_kn5_prep_mends_its_own_corridor_slivers_before_anything_moves():
    """the author stage left 31 vertical faces near the north roads; the kn5 prep's corridor subdivision (a T-vertex on
    a coarser face's edge, BEAUTY after it) made 262 more in the gate OBJ — the snapshot prep mends them right after
    that triangulation, before the pin / feather move a vertex, by the same rule as tools/terrain_mend.py"""
    prep = (ROOT / "tracks" / "san-diego-lake-murray" / "engine-july-snapshot" / "scripts" / "ac" /
            "build_kn5_loop.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert "def _collinear_middle(pts, tol=1e-3, end=1e-3):" in prep and "def _mend_vertical_slivers(bm, rounds=6):" in prep
    i = prep.index("bmesh.ops.subdivide_edges(bm, edges=todo, cuts=1)")
    j = prep.index("bmesh.ops.triangulate(bm, faces=bm.faces)", i)
    k = prep.index("n_mend = _mend_vertical_slivers(bm)", j)
    assert k < prep.index("# 2. pin + feather", j)
    assert tm.LINE_TOL_M == 1e-3 and tm.END_FRAC == 1e-3                # the two copies' tolerances agree
    pend = (ROOT / "tracks" / "san-diego-lake-murray" / "engine-july-snapshot" / "PENDING-MIRROR.md5").read_text()
    assert "scripts/ac/build_kn5_loop.py" in pend                        # still to mirror into engine-july
