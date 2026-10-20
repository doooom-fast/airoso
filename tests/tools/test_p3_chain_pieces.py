"""Ledger 0054 P3 pure pieces: the offset blend (tools/trim_connectors.py), the authored paint (scripts-v021
ribbon.paint_markings), ground_release line zones (tools/ground_release.Zones), verify_mouths' offset island."""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import trim_connectors as tc  # noqa: E402
import ground_release as gr  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "_v021_ribbon_p3", ROOT / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "ribbon.py")
RB = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RB)


def _falling(n=40, step=3.0, g=-0.06):
    return [(0.0, g * step * k, step * (k + 1)) for k in range(n)]


def test_offset_blend_lifts_the_piece_by_the_cut_gap_and_lets_go():
    piece = _falling()
    cut = (0.0, 1.5, 0.0)                         # the host stands 1.5 m over the piece's own line at the cut
    trial = list(piece)
    moved = tc.offset_blend_from_cut(trial, cut, 1.5, True, blend_m=60.0)
    assert moved
    # the gap is measured to the piece's own line extended to the cut (0.18 m there: 6 % over 3 m); at the first point
    # the lift is ~ all of it, past 60 m none
    dy0 = 1.5 - 0.06 * 3.0
    assert abs((trial[0][1] - piece[0][1]) - dy0 * tc.smoothstep(1.0 - 3.0 / 60.0)) < 1e-9
    assert all(abs(a[1] - b[1]) < 1e-12 for a, b in zip(trial[21:], piece[21:]))
    # the blended grade = own grade + the lift's slope, never the flat-host pull's
    flat = list(piece)
    tc.blend_from_cut(flat, cut, 1.5, True, blend_m=60.0)
    assert tc.blended_grade(trial, cut, True, 65.0) < tc.blended_grade(flat, cut, True, 65.0)


def test_capped_offset_blend_is_the_shortest_within_its_own_grade_plus_three_points():
    piece = _falling()
    cut = (0.0, 1.5, 0.0)
    L, g = tc.capped_blend_length(piece, cut, 1.5, True, blend=tc.offset_blend_from_cut, least_steep=True)
    own = tc.own_grade(piece, True, L + tc.BLEND_CAP_STEP_M)
    assert abs(own - 0.06) < 1e-6
    assert g <= own + tc.OWN_GRADE_PLUS + 1e-9
    if L > tc.BLEND_M:
        shorter = list(piece)
        tc.offset_blend_from_cut(shorter, cut, 1.5, True, blend_m=L - tc.BLEND_CAP_STEP_M)
        assert tc.blended_grade(shorter, cut, True, L) > own + tc.OWN_GRADE_PLUS


def test_paint_markings_draws_exactly_the_authored_lines():
    cl = [(0.0, 0.0, float(z)) for z in range(0, 61, 3)]
    w = [12.0] * len(cl)
    n = len(cl)
    paint = {"lines": [{"color": "yellow", "dash": False, "off": [0.09] * n},
                       {"color": "white", "dash": True, "off": [-3.0] * n},
                       {"color": "white", "dash": False, "off": [None] * 5 + [4.0] * (n - 5)}],
             "strokes": [{"color": "yellow", "w": 0.3, "a": [2.0, -1.0], "b": [3.0, 1.0]}]}
    mk = RB.paint_markings(cl, w, paint)
    assert len(mk["yellow"]["tris"]) == 2 * (n - 1) + 2
    solid4 = 2 * (n - 1 - 5)
    dashed = sum(1 for i in range(n - 1) if (3.0 * i) % 12.0 <= 3.0) * 2
    assert len(mk["white"]["tris"]) == solid4 + dashed
    assert RB.connector_markings(cl, w, None, paint) == mk
    assert RB.connector_markings(cl, w) == RB.lane_markings(cl, w, center_yellow=True)


def test_a_line_zone_is_judged_on_its_own_line_and_the_list_stays_aligned():
    main = [(0.0, 0.0, float(z)) for z in range(0, 201, 5)]
    line = [[500.0, float(z)] for z in range(0, 201, 5)]
    zones = [{"name": "m", "kind": "bank", "s_m": [50.0, 150.0], "sides": [1], "reach_m": 20.0},
             {"name": "l", "kind": "bank", "s_m": [50.0, 150.0], "sides": [-1], "reach_m": 20.0, "line": "x",
              "line_xz": line, "line_w": [10.0] * len(line)}]
    Z = gr.Zones(main, [10.0] * len(main), zones)
    assert [z["name"] for z in Z.zones] == ["m", "l"]
    w, z = Z.weight(500.0 + 10.0, 100.0)            # right of the line's travel (+z): x > 500
    assert w > 0.0 and z["name"] == "l"
    assert Z.weight(500.0 - 10.0, 100.0)[0] == 0.0
    w, z = Z.weight(-10.0, 100.0)
    assert w > 0.0 and z["name"] == "m"
    # resolve_zones without a project skips a line zone (it can be resolved only against the connectors)
    cfg = {"terrain": {"ground_release": {"zones": [dict(zones[0], sides=["left"]),
                                                    {"name": "l", "kind": "bank", "line": "x", "piece": "D",
                                                     "piece_s_m": [1, 2], "sides": ["right"], "reach_m": 40.0,
                                                     "cut_reach_m": 20.0, "rails": False}]}}}
    assert [z["name"] for z in gr.resolve_zones(cfg, main)] == ["m"]


def test_verify_mouths_reads_an_offset_island_on_the_mouth_side():
    spec = importlib.util.spec_from_file_location("_vm_p3", ROOT / "tools" / "verify_mouths.py")
    vm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vm)
    import json
    import tempfile
    d = Path(tempfile.mkdtemp())
    pts = [[0.0, 0.0, float(z)] for z in range(0, 101, 3)]
    isl = [[1.0, 0.0, float(z)] for z in range(0, 101, 3)]       # 1 m right of the host's centre line (+x), 4 m wide
    for aware, want in ((True, 3.0), (False, 2.0)):
        (d / "median_bands.json").write_text(json.dumps({"connector_islands": [
            {"name": "north_x", "points_xyz_m": isl, "island_w_by_point": [4.0] * len(isl),
             **({"offset_aware": True} if aware else {})}]}))
        hp = vm.Path2(pts, [20.0] * len(pts))
        got = vm._island_half({"host": "north_x", "side": -1}, hp, d, 50.0)
        assert abs(got - want) < 1e-6, (aware, got)
