"""tools/trim_connectors.py — the cut lands on the host deck and the blend runs from the cut (2026-10-11).

The diagnosis: the cut height was the NEAREST host vertex's (up to 3 m of a 4.56 % grade away), and a cut at a
piece's START never blended (the walk was reversed twice): del_cerro_blvd#1 dropped 0.58 m in its first 2.1 m,
medium#2+0#0#0 0.33 m in 3.3 m. And the mouth's SIDE was read off the first point INSIDE the host, which can sit
past the host's centreline: medium#2+0#0 was recorded on side +1 of del_cerro_blvd#1 while it arrives from -1, so
gap_mouths gapped the wrong sidewalk. A synthetic host (straight, 20 m wide, +5 % grade) crossed by a level
connector 2 m above it at 70 deg: two pieces, both ends blended from the cut, the cut on the interpolated host
height, the side of each from its approach, the records carrying host_seg / host_t / angle / grade / piece / end.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import trim_connectors as tc  # noqa: E402

GRADE = 0.05


def _host():
    pts = [(-60.0 + 4.0 * i, 10.0 + GRADE * (-60.0 + 4.0 * i), 0.0) for i in range(31)]   # 4 m spacing
    return pts, [20.0] * len(pts)


def _crossing(angle=70.0, y=12.0):
    a = math.radians(angle)
    d = (math.cos(a), math.sin(a))
    pts = [(1.0 + d[0] * u, y, d[1] * u) for u in [-60.0 + 3.0 * k for k in range(41)]]
    return {"name": "x", "kind": "connector", "points_xyz_m": [list(p) for p in pts], "widths_m": [10.0] * len(pts)}


def test_host_height_is_interpolated_not_the_nearest_vertex():
    hpts, _w = _host()
    y, seg, t = tc.host_height(hpts, 1.5, 3.0)
    assert abs(y - (10.0 + GRADE * 1.5)) < 1e-9
    assert hpts[seg][0] <= 1.5 <= hpts[seg + 1][0] and 0.0 < t < 1.0


def test_blend_from_a_start_cut_walks_from_the_start():
    piece = [(3.0 * k, 5.0, 0.0) for k in range(1, 20)]
    cut = (0.0, 2.0, 0.0)
    moved = tc.blend_from_cut(piece, cut, 2.0, at_start=True)
    ys = [p[1] for p in piece]
    assert ys[0] < 2.2 and ys[0] > 2.0                    # the point next to the cut is pulled almost onto it
    assert all(ys[k] <= ys[k + 1] + 1e-12 for k in range(len(ys) - 1))
    assert ys[-1] == 5.0 and len(moved) == 9               # 30 m: points at 3..27 m move, 30 m on does not
    back = [(3.0 * k, 5.0, 0.0) for k in range(-19, 0)]
    tc.blend_from_cut(back, cut, 2.0, at_start=False)
    assert back[-1][1] < 2.2 and back[0][1] == 5.0


def test_blend_stops_at_a_frozen_cut():
    piece = [(0.0, 9.0, 0.0)] + [(3.0 * k, 5.0, 0.0) for k in range(1, 6)]     # 15 m piece, its start an earlier cut
    tc.blend_from_cut(piece, (18.0, 2.0, 0.0), 2.0, at_start=False, frozen={(0.0, 0.0)})
    assert piece[0][1] == 9.0
    assert piece[-1][1] < 2.3


def test_trim_a_crossing_cuts_both_pieces_onto_the_host_deck():
    hpts, hw = _host()
    mouths, deltas = [], {}
    out = tc._trim_against([_crossing()], [("MAINLINE", hpts, hw)], mouths, deltas)
    assert len(out) == 2 and len(mouths) == 2
    tc.resolve_pieces(mouths, out)
    by_end = {mo["end"]: mo for mo in mouths}
    assert set(by_end) == {"start", "end"}
    for mo in mouths:
        cx, cy, cz = mo["cut_xyz"]
        assert abs(cy - (10.0 + GRADE * cx)) < 2e-3, mo          # the deck under the cut, not a vertex's
        assert abs(abs(cz) - (10.0 - tc.OVERLAP_M)) < 0.05
        assert abs(mo["angle_deg"] - 70.0) < 0.5 and abs(mo["host_grade"] - GRADE) < 1e-6
        assert mo["piece"] in ("x#0", "x#1")
        assert 0.0 <= mo["host_t"] <= 1.0 and hpts[mo["host_seg"]][0] <= cx <= hpts[mo["host_seg"] + 1][0] + 1e-6
    # side from the approach: the piece south of the host (z < 0) is on the host's right (-1)
    for mo in mouths:
        assert mo["side"] == (1 if mo["cut_xyz"][2] > 0 else -1)
    # BOTH pieces are blended from their cut: the point next to each cut sits close to the cut's height
    pieces = {c["name"]: c["points_xyz_m"] for c in out}
    for mo in mouths:
        p = pieces[mo["piece"]]
        nxt = p[1] if mo["end"] == "start" else p[-2]
        assert abs(nxt[1] - mo["cut_xyz"][1]) < 0.15, (mo["end"], nxt, mo["cut_xyz"])
        far = p[-1] if mo["end"] == "start" else p[0]
        assert far[1] == 12.0
    assert deltas["x"]


def test_the_side_comes_from_the_approach_not_the_first_point_inside():
    """a piece whose first point inside the host lies PAST its centreline (a route node on the far carriageway)"""
    hpts, hw = _host()
    # outside down to z = 12 (2 m off the 10 m pavement edge), then straight to a node 2 m PAST the host centreline
    pts = [[2.0, 12.0, 30.0 - 3.0 * k] for k in range(7)] + [[2.0, 12.0, -2.0]]
    c = {"name": "y", "kind": "connector", "points_xyz_m": pts, "widths_m": [8.0] * len(pts)}
    mouths = []
    out = tc._trim_against([c], [("MAINLINE", hpts, hw)], mouths)
    assert len(out) == 1 and len(mouths) == 1
    assert mouths[0]["side"] == 1, mouths[0]                 # it arrives from z > 0: the host's left


# --- GRADE-CAPPED BLEND (opt-in, ledger 0054 P1 fix round) ---------------------------------------------------------

def test_grade_capped_blend_is_opt_in_and_keeps_the_piece_within_the_cap():
    """a connector 3 m BELOW the host (the J1 case: the loop stands over Waring's 3DEP): 30 m of smoothstep makes it
    climb 1.5 x 3 / 30 = 15 % onto the host; capped, the blend lengthens until it stays within 11 %"""
    hpts, hw = _host()
    plain, capped = [], []
    out0 = tc._trim_against([_crossing(angle=90.0, y=7.0)], [("MAINLINE", hpts, hw)], plain, {})
    out1 = tc._trim_against([_crossing(angle=90.0, y=7.0)], [("MAINLINE", hpts, hw)], capped, {}, capped=["x"])
    tc.resolve_pieces(plain, out0)
    tc.resolve_pieces(capped, out1)
    for mo in plain:                                         # absent the key: the record and the blend as before
        assert "blend_m" not in mo and "blend_max_grade" not in mo
    for mo0, mo1 in zip(plain, capped):
        assert mo0["cut_xyz"] == mo1["cut_xyz"] and mo0["piece"] == mo1["piece"]
        assert mo1["blend_max_grade"] <= tc.GRADE_CAP + 1e-9 and tc.BLEND_M < mo1["blend_m"] <= tc.BLEND_CAP_MAX_M
    p0 = {c["name"]: c["points_xyz_m"] for c in out0}
    p1 = {c["name"]: c["points_xyz_m"] for c in out1}
    for mo in capped:
        cut = mo["cut_xyz"]
        at_start = mo["end"] == "start"
        g0 = tc.blended_grade([tuple(p) for p in p0[mo["piece"]]], cut, at_start, 200.0)
        g1 = tc.blended_grade([tuple(p) for p in p1[mo["piece"]]], cut, at_start, 200.0)
        assert g0 > 0.13 and g1 <= tc.GRADE_CAP + 1e-9, (g0, g1)


def test_grade_capped_blend_keeps_30_m_where_30_m_is_within_the_cap():
    hpts, hw = _host()
    mouths = []
    out = tc._trim_against([_crossing(angle=90.0, y=10.5)], [("MAINLINE", hpts, hw)], mouths, {}, capped=["x"])
    tc.resolve_pieces(mouths, out)
    assert all(mo["blend_m"] == tc.BLEND_M for mo in mouths)


def test_a_banked_host_cut_lands_on_its_banked_deck():
    """ledger 0085 (route.trim_host_bank, Pikes Peak): with the host's bank declared, each cut lands on the deck where it
    stands (centreline + signed lateral x tan(bank), + = the host's left edge higher), not on the centreline; without
    it the centreline height, as before"""
    hpts, hw = _host()
    bank = -0.17                                                     # the left edge 17 % lower, as the oval's inside
    try:
        tc.HOST_BANK["MAINLINE"] = lambda x, z: math.atan(bank)
        mouths = []
        tc._trim_against([_crossing()], [("MAINLINE", hpts, hw)], mouths, {})
    finally:
        tc.HOST_BANK.clear()
    assert len(mouths) == 2
    for mo in mouths:
        cx, cy, cz = mo["cut_xyz"]
        lat = cz                                                     # the host runs +x: its left is +z
        assert abs(cy - (10.0 + GRADE * cx + lat * bank)) < 2e-3, mo
    plain = []
    tc._trim_against([_crossing()], [("MAINLINE", hpts, hw)], plain, {})
    assert all(abs(mo["cut_xyz"][1] - (10.0 + GRADE * mo["cut_xyz"][0])) < 2e-3 for mo in plain)
