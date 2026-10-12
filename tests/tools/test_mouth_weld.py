"""tools/mouth_weld.py — the side-street mouth weld's pure geometry (2026-10-11).

A synthetic mouth that reproduces the Del Cerro W defect: a straight host 20 m wide on a -5 % grade, a 16 m
connector meeting it at 76 deg from the left with its end row LEVEL and SQUARE at the cut (the cut on the host
centreline height, as tools/trim_connectors.py leaves it). Before the weld its acute corner stands ~0.39 m over
the host's deck inside the host's pavement; after it every road line ends on the host edge minus 0.4 m AT the
host deck, every curb line ends on the host edge, nothing of the connector stands over the host deck inside its
pavement, no quad folds, and the connector is untouched past BLEND_M. Plus: the ribbon unfold (a swallowtail cut
at its self-intersection, a hook replaced by a forward chord, a U-turn refused when strict), the gap window's skew,
the marking carry and the mesh layout's indices.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import mouth_weld as mw  # noqa: E402

GRADE = -0.05
HALF_H = 10.0
HALF_C = 8.0
ANG = 76.0
CURB = ((0.0, 0.0), (0.08, 0.14), (1.58, 0.14), (2.78, -0.20))      # (offset past the edge, height over the road)


def host_y(x):
    return 10.0 + GRADE * x


def host_rows():
    return [((x, host_y(x), HALF_H), (x, host_y(x), 0.0), (x, host_y(x), -HALF_H))
            for x in [-90.0 + 3.0 * i for i in range(61)]]


def conn_frame():
    a = math.radians(ANG)
    d = (math.cos(a), math.sin(a))                  # away from the host, toward +z (side +1)
    n = (-d[1], d[0])                              # the piece's left normal (it runs away from the host)
    return d, n


def conn_lines(n_rows=24, spacing=3.0):
    """END-FIRST lateral lines of a piece whose START is the cut (0, host_y(0), 9.6): level for 30 m, then climbing"""
    d, n = conn_frame()
    cut = (0.0, HALF_H - mw.OVERLAP_M)
    lines = {("road", 0): [], ("road", 1): [], ("road", 2): []}
    for s in (1, -1):
        for p in range(4):
            lines[("curb", s, p)] = []
    for j in range(n_rows):
        u = spacing * j
        cx, cz = cut[0] + d[0] * u, cut[1] + d[1] * u
        y = host_y(0.0) + 0.04 * max(0.0, u - 30.0)
        for lane, o in ((0, HALF_C), (1, 0.0), (2, -HALF_C)):
            lines[("road", lane)].append((cx + n[0] * o, y, cz + n[1] * o))
        for s in (1, -1):
            for p, (off, h) in enumerate(CURB):
                o = s * (HALF_C + off)
                lines[("curb", s, p)].append((cx + n[0] * o, y + h, cz + n[1] * o))
    inset = {k: (mw.OVERLAP_M if k[0] == "road" else mw.CURB_INSET_M) for k in lines}
    h = {k: (0.0 if k[0] == "road" else CURB[k[2]][1]) for k in lines}
    return lines, inset, h


def deck():
    rows = host_rows()
    return mw.HostDeck(rows, mw.host_window(rows, False, 0.0, HALF_H))


def test_the_defect_is_reproduced_before_the_weld():
    lines, _i, _h = conn_lines()
    dk = deck()
    r0 = lines[("road", 2)][0]           # the right end corner: inside the host (acute side)
    assert dk.inside(r0[0], r0[2])
    assert r0[1] - dk.at(r0[0], r0[2]) > 0.35, r0[1] - dk.at(r0[0], r0[2])
    l0 = lines[("road", 0)][0]           # the left one stops short of the host edge
    assert dk.edge_gap(l0[0], l0[2], 1, 0.0) > 1.0


def test_weld_end_lands_every_line_on_the_host():
    lines, inset, h = conn_lines()
    dk = deck()
    res = mw.weld_end(lines, dk, 1, inset, h)
    new = res["new"]
    for lane in range(3):
        e = new[("road", lane)][0]
        assert abs(dk.edge_gap(e[0], e[2], 1, mw.OVERLAP_M)) < 1e-6
        assert abs(e[1] - dk.at(e[0], e[2])) < 1e-9
    for s in (1, -1):
        for p in range(4):
            e = new[("curb", s, p)][0]
            assert abs(dk.edge_gap(e[0], e[2], 1, 0.0)) < 1e-6
            assert abs(e[1] - (dk.at(e[0], e[2]) + CURB[p][1])) < 1e-9
    # the skew: the left line was extended, the right one shortened, by ~half x cot(76 deg)
    expect = HALF_C / math.tan(math.radians(ANG))
    assert abs(res["u_x"][("road", 0)] + expect) < 0.15 and abs(res["u_x"][("road", 2)] - expect) < 0.15
    assert abs(res["u_x"][("road", 1)]) < 1e-6


def test_nothing_of_the_connector_stands_over_the_host_and_nothing_folds():
    lines, inset, h = conn_lines()
    dk = deck()
    new = mw.weld_end(lines, dk, 1, inset, h)["new"]
    for k, pts in new.items():
        for q in pts:
            if dk.inside(q[0], q[2], 0.01):
                assert q[1] <= dk.at(q[0], q[2]) + mw.SELF_TOL_M, (k, q, dk.at(q[0], q[2]))
    old_rows = [tuple(lines[("road", lane)][j] for lane in range(3)) for j in range(len(lines[("road", 0)]))]
    new_rows = [tuple(new[("road", lane)][j] for lane in range(3)) for j in range(len(new[("road", 0)]))]
    for a, b in zip(mw.quad_areas(old_rows), mw.quad_areas(new_rows)):
        assert a * b > 0 and abs(b) > 1e-4


def test_the_approach_eases_back_and_the_far_rows_are_untouched():
    lines, inset, h = conn_lines()
    dk = deck()
    res = mw.weld_end(lines, dk, 1, inset, h)
    new = res["new"]
    c_old, c_new = lines[("road", 1)], new[("road", 1)]
    for j in range(len(c_old)):
        s = 3.0 * j
        if s >= mw.BLEND_M + 0.5:
            assert c_new[j] == c_old[j]
    # grade change per metre along every road line over the blend stays far under the 3 %/m gate
    for lane in range(3):
        ys = [p[1] for p in new[("road", lane)]]
        xs = mw.arc_lengths(new[("road", lane)])
        worst = 0.0
        for j in range(1, len(ys) - 1):
            g0 = (ys[j] - ys[j - 1]) / max(xs[j] - xs[j - 1], 1e-9)
            g1 = (ys[j + 1] - ys[j]) / max(xs[j + 1] - xs[j], 1e-9)
            worst = max(worst, abs(g1 - g0) / max(0.5 * (xs[j + 1] - xs[j - 1]), 1e-9))
        assert worst < 0.03, (lane, worst)
    assert res["J"] >= 2 and res["K"] > res["J"]


def test_map_marking_keeps_its_fraction_and_lift():
    lines, inset, h = conn_lines()
    dk = deck()
    new = mw.weld_end(lines, dk, 1, inset, h)["new"]
    rows_old = [tuple(lines[("road", lane)][j] for lane in range(3)) for j in range(len(lines[("road", 0)]))]
    rows_new = [tuple(new[("road", lane)][j] for lane in range(3)) for j in range(len(new[("road", 0)]))]
    L, C, R = rows_old[0]
    f = 0.5
    v = (C[0] + (L[0] - C[0]) * f, C[1] + mw.MARK_LIFT_M, C[2] + (L[2] - C[2]) * f)
    nv = mw.map_marking(v, rows_old, rows_new, 6)
    Ln, Cn, _Rn = rows_new[0]
    want = (Cn[0] + (Ln[0] - Cn[0]) * f, Cn[1] + (Ln[1] - Cn[1]) * f + mw.MARK_LIFT_M, Cn[2] + (Ln[2] - Cn[2]) * f)
    assert all(abs(a - b) < 1e-6 for a, b in zip(nv, want)), (nv, want)
    assert mw.map_marking((v[0] + 1.0, v[1], v[2] + 1.0), rows_old, rows_new, 6) is None   # on no row's cross line


def test_a_line_that_never_reaches_the_host_is_refused():
    lines, inset, h = conn_lines()
    far = {k: [(p[0], p[1], p[2] + 40.0) for p in v] for k, v in lines.items()}    # 40 m short of the edge
    try:
        mw.weld_end(far, deck(), 1, inset, h)
    except mw.WeldError:
        return
    raise AssertionError("a connector 40 m short of its host was welded")


def test_mesh_layout_indices():
    main = [(float(i), 0.0, 0.0) for i in range(10)] + [(0.0, 0.0, 0.0)]          # closed: 10 rows
    conns = [{"name": "a", "points_xyz_m": [(0.0, 0.0, float(i)) for i in range(5)]},
             {"name": "b", "points_xyz_m": [(1.0, 0.0, 0.0), (2.0, 0.0, 0.0), (1.0, 0.0, 1.0), (1.0, 0.0, 0.0)]}]
    lay = mw.mesh_layout(main, conns)
    assert lay["MAINLINE"] == {"rows": 10, "closed": True, "road": 0, "curb": 0}
    assert lay["a"]["road"] == 30 and lay["a"]["curb"] == 80 and lay["a"]["rows"] == 5
    assert lay["b"]["closed"] and lay["b"]["rows"] == 3 and lay["b"]["road"] == 45 and lay["b"]["curb"] == 120
    assert lay["_road_total"] == 54 and lay["_curb_total"] == 144
    assert mw.road_index(lay, "a", 2, 1) == 37
    assert mw.curb_index(lay, "a", 1, 1, 3) == 80 + 4 + 3
    assert mw.curb_index(lay, "a", 1, -1, 0) == 80 + 20 + 4


# ------------------------------------------------------------------------------------------------ unfold

def _corner(R=6.0, spacing=1.0):
    """heading +x along z=0 to (0, 0), a right-hand arc of radius R (centre (0, -R)), then heading -z along x=R"""
    C = [(x, 0.0, 0.0) for x in [-30.0 + spacing * i for i in range(31)]]
    for k in range(1, 10):
        a = math.radians(90.0 * k / 9.0)
        C.append((R * math.sin(a), 0.01 * k, -R + R * math.cos(a)))
    C += [(R, 0.09, -R - spacing * i) for i in range(1, 31)]
    return C


def _right_edge(C, h):
    out = []
    for i in range(len(C)):
        a, b = C[max(0, i - 1)], C[min(len(C) - 1, i + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz)
        nx, nz = -tz / L, tx / L
        out.append((C[i][0] - nx * h, C[i][1], C[i][2] - nz * h))
    return out


def test_unfold_cuts_a_swallowtail_at_its_self_intersection():
    C = _corner()
    E = _right_edge(C, 10.0)
    assert mw.backward_segments(E, C, False)
    newE, done, left = mw.unfold_line(E, C, False)
    assert not left and len(done) == 1
    assert not mw.backward_segments(newE, C, False)
    k, l, X = done[0]
    assert abs(X[0] - (-4.0)) < 0.05 and abs(X[2] - (-10.0)) < 0.05, X   # the legs' inside lines cross at (-4, -10)
    assert all(newE[r] == X for r in range(k + 1, l + 1))
    assert all(newE[r] == E[r] for r in range(len(E)) if r <= k or r > l)
    # a line on a smaller offset (no fold) is left alone
    E2 = _right_edge(C, 4.0)
    assert mw.unfold_line(E2, C, False)[1] == []


def test_unfold_replaces_a_hook_with_a_forward_chord():
    C = [(float(i), 0.0, 0.0) for i in range(10)]
    E = [(0.0, 0.0, -5.0), (1.0, 0.0, -5.0), (2.0, 0.0, -5.0), (3.0, 0.0, -5.0), (2.6, 0.0, -5.5), (2.4, 0.0, -6.0),
         (4.0, 0.0, -6.5), (5.0, 0.0, -6.5), (6.0, 0.0, -6.5), (7.0, 0.0, -6.5)]
    newE, done, left = mw.unfold_line(E, C, False)
    # the smallest forward window is two rows wide; of (2, 4) and (3, 5) the first keeps more pavement
    assert done == [(2, 4, None)] and not left, done
    assert not mw.backward_segments(newE, C, False)
    assert abs(newE[3][0] - (2.0 + 0.4 / 3)) < 1e-9 and abs(newE[3][2] - (-5.0 - 1.0 / 3)) < 1e-9
    assert abs(newE[4][0] - (2.0 + 0.8 / 3)) < 1e-9 and abs(newE[4][2] - (-5.0 - 2.0 / 3)) < 1e-9
    assert newE[4][1] == E[4][1]                          # each row keeps its own height
    assert all(newE[r] == E[r] for r in (0, 1, 2, 5, 6, 7, 8, 9))


def test_unfold_refuses_a_u_turn_narrower_than_the_ribbon_when_strict():
    C = [(float(i), 0.0, 0.0) for i in range(12)]
    for k in range(1, 9):
        a = math.radians(180.0 * k / 8.0)
        C.append((11.0 + 2.0 * math.sin(a), 0.0, -2.0 + 2.0 * math.cos(a)))
    C += [(11.0 - i, 0.0, -4.0) for i in range(1, 12)]
    E = _right_edge(C, 5.0)
    try:
        mw.unfold_line(E, C, False, strict=True)
    except mw.WeldError:
        pass
    else:
        raise AssertionError("a U-turn whose legs overlap was 'unfolded'")
    _newE, _done, left = mw.unfold_line(E, C, False, strict=False)
    assert left


# ------------------------------------------------------------------------------------------------ gap window

def test_gap_window_widens_with_the_skew():
    host = [(3.0 * i, 0.0, 0.0) for i in range(40)]
    # the cut at arc 31.5: stations within 10 + 3 = 13 m are 7..14, plus the first one past on each side (a strip
    # face is gapped only when both its stations are in the set: 6-7 and 14-15 straddle the window's ends)
    square = mw.gap_window(host, 40, False, 10, 0.5, 20.0, 90.0)
    assert square == set(range(6, 16)), sorted(square)
    skew = mw.gap_window(host, 40, False, 10, 0.5, 20.0, 30.0)          # 10 / sin 30 + 3 = 23 m
    assert skew == set(range(2, 20)), sorted(skew)
    ring = [(30.0 * math.cos(2 * math.pi * i / 60), 0.0, 30.0 * math.sin(2 * math.pi * i / 60)) for i in range(60)]
    ring.append(ring[0])
    w = mw.gap_window(ring, 60, True, 0, 0.0, 8.0, 90.0)                # 7 m each way, wrapping the seam
    assert w == {57, 58, 59, 0, 1, 2, 3}, sorted(w)


def test_gap_window_reaches_past_the_connector_edge():
    """the Del Cerro W regression: College stations 3.08 m apart, the window's last station inside at 12.06 m, the
    connector's edge on the host edge at 12.86 m — the face from that station to the next must be gapped too"""
    host = [(0.0, 0.0, 3.08 * i) for i in range(30)]
    w = mw.gap_window(host, 30, False, 14, 0.89, 22.91, 76.94)
    c = 3.08 * 14.89
    lo = min(3.08 * q for q in w)
    assert c - lo >= 12.86 + 1e-9 and c - 3.08 * (min(w) + 1) < 12.86 + 3.08, (c - lo, sorted(w))
