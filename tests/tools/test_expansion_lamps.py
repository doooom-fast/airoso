"""Ledger 0054 P4 step 2 (EXPANSION-PLAN D4) — streetlights on the north pieces: the planner in
tracks/san-diego-lake-murray/scripts-v021/geometry/streetlights.py (pure python; the assembler calls it inside
build_streetlights after the loop's posts). The loop's spacing and gap, the post on the walk, every other pavement
kept clear (mainline, stubs with their returns, pads, curb cuts), the unlit stretch, the OSM-grounded stretch, the
slide-then-other-side-then-skip rule, and the record each lamp carries."""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "sd_streetlights", ROOT / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "streetlights.py")
SL = importlib.util.module_from_spec(_spec)
sys.modules["sd_streetlights"] = SL
_spec.loader.exec_module(SL)

W = 20.0


def _piece(length=600.0, width=W, step=3.0, z0=0.0, pid="A", name="piece_a", reverse_stations=False):
    n = int(length / step) + 1
    pts = [(i * step, 0.0, z0) for i in range(n)]
    st = [[round(i * step, 1), i * step, z0] for i in range(n)]
    if reverse_stations:               # the intermediate's table runs the other way (piece D: J4 -> J5)
        st = [[round(length - r[0], 1), r[1], r[2]] for r in st]
    return {"name": name, "id": pid, "pts": pts, "widths": [width] * n, "stations": st}


def _plan(pieces, **kw):
    args = dict(mainline=([], []), others=[], pads=[], stubs=[], curb_cuts=[], placed=[], cfg_expansion={"enabled": True},
                osm_nodes=[], ground=lambda x, z: 10.0)
    args.update(kw)
    return SL.plan(pieces, **args)


def test_loop_spacing_sides_and_record_on_a_straight_piece():
    out = _plan([_piece()])
    lamps = out["lamps"]
    us = [l["u_m"] for l in lamps]
    assert us == [55.0 + 55.0 * k for k in range(len(us))], us
    assert us[-1] <= 600.0 - SL.MIN_GAP_M
    assert [l["side"] for l in lamps] == ["L", "R"] * (len(lamps) // 2) + (["L"] if len(lamps) % 2 else [])
    for l in lamps:
        bx, bz = l["base_xz"]
        # the post ON the walk: hw + WALK_OFFSET_M off the centreline (z = 0), left = +z
        assert abs(abs(bz) - (W / 2 + SL.WALK_OFFSET_M)) < 1e-6, l
        assert (bz > 0) == (l["side"] == "L")
        rx, rz = l["roadward_xz"]
        assert abs(rx) < 1e-9 and abs(rz - (-1.0 if bz > 0 else 1.0)) < 1e-9     # road-ward points at the centreline
        hx, hy, hz = l["head"]
        assert abs(hx - bx) < 1e-6 and abs(hz - (bz + rz * SL.ARM_M)) < 1e-6
        assert abs(hy - (10.0 + SL.HEAD_OVER_GROUND_M)) < 1e-6
        assert l["source"] == "authored" and l["piece"] == "A" and l["name"] == "piece_a"
        assert abs(l["s_m"] - l["u_m"]) <= 1.5           # the station table at 3 m: nearest row
    assert out["skipped"] == []
    r = out["per_piece"]["A"]
    assert r["authored"] == len(lamps) and r["osm"] == 0 and r["skipped"] == 0


def test_station_table_may_run_the_other_way():
    out = _plan([_piece(pid="D", name="piece_d", reverse_stations=True)])
    for l in out["lamps"]:
        assert abs(l["s_m"] - (600.0 - l["u_m"])) <= 1.5, l


def test_unlit_stretch_gets_no_post_and_is_never_slid_around():
    cfg = {"enabled": True, "unlit": [{"piece": "A", "s_from": 200.0, "s_to": 400.0, "why": "D4"}]}
    out = _plan([_piece()], cfg_expansion=cfg)
    for l in out["lamps"]:
        assert not (200.0 <= l["s_m"] <= 400.0), l
    sk = [s for s in out["skipped"] if s["why"] == ["unlit"]]
    assert len(sk) == len([u for u in (55.0 + 55.0 * k for k in range(20)) if 200.0 <= u <= 400.0]), sk
    assert out["per_piece"]["A"]["skipped"] == 0            # an unlit station is not a failure
    assert out["per_piece"]["A"]["unlit"] == [{"s_from": 200.0, "s_to": 400.0, "why": "D4"}]
    # the other piece's unlit stretch is not this piece's
    out2 = _plan([_piece()], cfg_expansion={"enabled": True, "unlit": [{"piece": "D", "s_from": 0, "s_to": 600}]})
    assert len(out2["lamps"]) == len(_plan([_piece()])["lamps"])


def test_a_loop_post_too_close_moves_the_station_or_takes_the_other_side():
    # the walk alternates: 55 L, 110 R, 165 L ... A loop post 7 m from the u = 110 R station (its base would be at
    # (110, -10.83)): every slide within 12 m is still under the 25 m gap, so the post takes the LEFT side at the same
    # station, and the alternation goes on from there (165 R)
    out = _plan([_piece()], placed=[(112.0, -18.0)])
    lamps = {(l["u_m"], l["side"]): l for l in out["lamps"]}
    assert (110.0, "R") not in lamps and (110.0, "L") in lamps, sorted(lamps)
    near = [l for l in out["lamps"] if 95.0 <= l["u_m"] <= 125.0]
    assert len(near) == 1
    bx, bz = near[0]["base_xz"]
    assert math.hypot(bx - 112.0, bz + 18.0) >= SL.MIN_GAP_M
    assert (165.0, "R") in lamps
    assert out["skipped"] == []
    # a loop post 18 m ahead along the right walk: the station slides back past it (8 m), same side
    out2 = _plan([_piece()], placed=[(128.0, -10.83)])
    near2 = [l for l in out2["lamps"] if 90.0 <= l["u_m"] <= 130.0]
    assert len(near2) == 1 and near2[0]["side"] == "R" and near2[0]["u_m"] == 102.0, near2
    assert math.hypot(near2[0]["base_xz"][0] - 128.0, near2[0]["base_xz"][1] + 10.83) >= SL.MIN_GAP_M


def test_a_stub_blocks_its_side_and_its_returns_so_the_post_takes_the_other_side():
    # a side street leaving the left curb at u = 110, 10 m wide, 15 m long (+ its own connector line)
    stub_pts = [(110.0, 0.0, W / 2 + k * 3.0) for k in range(6)]
    others = [("STUB_x", stub_pts, [10.0] * 6, "stub")]
    stubs = [{"id": "x", "host": "piece_a", "side": 1, "cut_xz": [110.0, W / 2], "width_m": 10.0}]
    out = _plan([_piece()], others=others, stubs=stubs)
    near = [l for l in out["lamps"] if abs(l["u_m"] - 110.0) <= SL.SLIDE_M + 0.1]
    assert near, out["skipped"]
    for l in near:
        bx, bz = l["base_xz"]
        if bz > 0:   # still on the left: outside the stub's returns
            assert abs(bx - 110.0) >= 5.0 + SL.STUB_CLEAR_M - 1e-6, l
    assert any(l["side"] == "R" and abs(l["u_m"] - 110.0) < 1e-6 for l in near) or all(l["side"] == "L" for l in near)
    assert out["skipped"] == []


def test_a_curb_cut_blocks_only_its_own_side():
    cuts = [{"id": "drive", "host": "piece_a", "side": 1, "station_m": 165.0, "half_span_m": 4.0, "flare_m": 1.0,
             "cut_xz": [165.0, W / 2]}]
    out = _plan([_piece()], curb_cuts=cuts)
    for l in out["lamps"]:
        if l["side"] == "L":
            assert abs(l["u_m"] - 165.0) >= 4.0 + 1.0 + SL.PAVEMENT_CLEAR_M - 1e-6, l
    # a cut on the right side at a left station changes nothing there
    cuts_r = [dict(cuts[0], side=-1)]
    base = _plan([_piece()])
    out_r = _plan([_piece()], curb_cuts=cuts_r)
    assert [l["u_m"] for l in out_r["lamps"] if l["side"] == "L"] == [l["u_m"] for l in base["lamps"] if l["side"] == "L"]


def test_a_junction_pad_keeps_posts_off_its_outline():
    pad = [(560.0, -30.0), (640.0, -30.0), (640.0, 30.0), (560.0, 30.0)]
    out = _plan([_piece()], pads=[("J2", pad)])
    for l in out["lamps"]:
        bx, bz = l["base_xz"]
        assert not SL.point_in_polygon(pad, bx, bz)
        assert SL.dist_to_outline(pad, bx, bz) >= SL.PAD_CLEAR_M - 1e-6, l
    assert all(l["u_m"] < 560.0 - SL.PAD_CLEAR_M for l in out["lamps"])


def test_another_pavement_too_close_is_skipped_with_its_reasons():
    # a parallel road whose edge runs 1 m behind the left walk for the whole piece, and a wall-to-wall pad on the right
    side_road = [(x, 0.0, W / 2 + SL.WALK_OFFSET_M + 1.0 + 5.0) for x in (0.0, 600.0)]
    pad = [(-10.0, -W / 2 - 0.2), (610.0, -W / 2 - 0.2), (610.0, -60.0), (-10.0, -60.0)]
    out = _plan([_piece()], others=[("side", side_road, [10.0, 10.0], "connector")], pads=[("J9", pad)])
    assert out["lamps"] == []
    assert out["skipped"] and all(set(s["why"]) >= {"connector:side", "pad:J9"} or "pad:J9" in s["why"] for s in out["skipped"])
    assert out["per_piece"]["A"]["skipped"] == len(out["skipped"])


def test_osm_nodes_beside_the_piece_light_their_stretch_and_record_their_source():
    nodes = [{"id": 101, "x": 200.0, "z": W / 2 + 4.0}, {"id": 102, "x": 240.0, "z": -(W / 2 + 6.0)},
             {"id": 999, "x": 300.0, "z": 200.0}]          # 999 is 190 m off the piece: not its lamp
    out = _plan([_piece()], osm_nodes=nodes)
    osm = [l for l in out["lamps"] if l["source"].startswith("osm:")]
    assert [(l["u_m"], l["side"], l["source"]) for l in osm] == [(200.0, "L", "osm:101"), (240.0, "R", "osm:102")]
    for l in osm:
        assert abs(abs(l["base_xz"][1]) - (W / 2 + SL.WALK_OFFSET_M)) < 1e-6     # on the walk, not at the node's offset
    r = out["per_piece"]["A"]
    assert r["osm"] == 2 and r["osm_stretches_u"] == [[200.0 - SL.OSM_STRETCH_PAD_M, 240.0 + SL.OSM_STRETCH_PAD_M]]
    lo, hi = r["osm_stretches_u"][0]
    for l in out["lamps"]:
        if l["source"] == "authored":
            assert not (lo <= l["u_m"] <= hi), l
    assert any(s["why"] == ["osm_stretch"] for s in out["skipped"])
    assert r["skipped"] == 0
    assert len(r["osm_nodes"]) == 2


def test_project_osm_nodes_is_the_scripts_v021_series():
    nodes = [{"id": 1, "lat": 32.78835571285328, "lon": -117.04666413020487},
             {"id": 2, "lat": 32.79835571285328, "lon": -117.04666413020487}, {"id": "x", "lat": "bad"}]
    out = SL.project_osm_nodes(nodes, -117.04666413020487, 32.78835571285328)
    assert [n["id"] for n in out] == [1, 2]
    assert abs(out[0]["x"]) < 1e-9 and abs(out[0]["z"]) < 1e-9
    assert 1105.0 < out[1]["z"] < 1112.0 and abs(out[1]["x"]) < 1e-9       # 0.01 deg of latitude


def test_line_projection_lateral_sign_and_edge_distance():
    ln = SL.Line([(0.0, 0.0, 0.0), (100.0, 0.0, 0.0)], [20.0, 20.0])
    d, u, lat = ln.project(30.0, 7.0)
    assert abs(d - 7.0) < 1e-9 and abs(u - 30.0) < 1e-9 and lat > 0          # + = left of travel (+x -> +z)
    assert abs(ln.edge_distance(30.0, 7.0) - (-3.0)) < 1e-9
    assert abs(ln.edge_distance(30.0, -14.0) - 4.0) < 1e-9
    (x, y, z), (tx, tz), w = ln.at(25.0)
    assert (x, z, tx, tz, w) == (25.0, 0.0, 1.0, 0.0, 20.0)
