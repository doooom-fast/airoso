"""Dragon Tail (Gravel), ledger 0076: two engine bugs on an open stage.

1. A measured-guard stone lip (1WALL_PARA_stone) was seated at its crossing and laid flat 1.5 m up and down the
   road's edge. Where the ground falls ALONG the edge (s 6,645, the exit of the second switchback: 2.4 m over the
   lip's 3 m) one foot hung 1.84 m in the air: drive_test "floating furniture" 2, the stage's only failing gate.
   lip_foot_reach pulls a foot back toward the crossing until it stands; a lip whose feet already stand is unchanged.
2. drive_test's replication compared the gate line's vertex i with measured height i, but an open stage's gate line
   carries build_mesh's 10-vertex lead-in: every vertex was read against the road 30 m on (0.96 m median; aligned
   0.02 m). pad_for_lead_in aligns them and leaves every other line alone.
3. Under the Dragon (Gravel), same ledger: past an open road end no pavement caps the seam-weld's 20 % floor, so a node
   at the lead-out's end corner rose 0.88 m over the deck and its triangle put grass 2.4 cm over the last pavement row
   (drive_test ground on top, 4 hits at 25,705-25,706 m). end_apron_cap gives such a node the end row's deck as its cap.
"""

from __future__ import annotations


def _plane(height_at):
    """ground_at(x, z, lo, hi) over one surface y = height_at(x, z)."""
    def ground_at(x, z, lo, hi):
        y = height_at(x, z)
        return y if lo <= y <= hi else None
    return ground_at


def test_lip_on_level_ground_keeps_full_length():
    from scripts.geometry.build_mesh import LIP_HALF_LEN_M, lip_foot_reach
    g = _plane(lambda x, z: 100.0)
    for d in (1.0, -1.0):
        assert lip_foot_reach(g, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 99.8, d) == LIP_HALF_LEN_M


def test_lip_on_its_own_grade_keeps_full_length():
    # the edge climbs 18 % (the stage's grade cap): a flat 3 m lip's feet sit 0.27 m off it, well inside 0.8 m
    from scripts.geometry.build_mesh import LIP_HALF_LEN_M, lip_foot_reach
    g = _plane(lambda x, z: 100.0 + 0.18 * z)
    for d in (1.0, -1.0):
        assert lip_foot_reach(g, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 99.8, d) == LIP_HALF_LEN_M


def test_foot_over_ground_falling_along_the_edge_is_pulled_back():
    # Dragon Tail s 6,645: base 187.94; the ground under the lip falls 0.8 m per metre toward one end
    from scripts.geometry.build_mesh import LIP_FOOT_MAX_GAP_M, lip_foot_gap, lip_foot_reach
    g = _plane(lambda x, z: 188.2 + 0.8 * z if z < 0 else 188.2)
    base = 187.94
    assert lip_foot_gap(g, 0.0, -1.5, base) > LIP_FOOT_MAX_GAP_M     # the old foot, 1.5 m down the fall: 0.94 m up
    r = lip_foot_reach(g, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, base, -1.0)
    assert r == 1.25
    assert lip_foot_gap(g, 0.0, -r, base) <= LIP_FOOT_MAX_GAP_M
    # the other end stands on level ground: untouched
    assert lip_foot_reach(g, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, base, 1.0) == 1.5


def test_outboard_corner_counts_too():
    # level along the edge, but the ground beyond x = 0.6 is a 2 m drop: the 1 m-thick lip's outer corner hangs
    from scripts.geometry.build_mesh import lip_foot_reach
    g = _plane(lambda x, z: 100.0 if (x < 0.6 or z > -0.6) else 98.0)
    assert lip_foot_reach(g, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 99.8, -1.0) == 0.5
    assert lip_foot_reach(g, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 99.8, 1.0) == 1.5


def test_no_surface_is_floating():
    from scripts.geometry.build_mesh import lip_foot_gap, lip_foot_reach
    assert lip_foot_gap(lambda x, z, lo, hi: None, 0.0, 0.0, 10.0) == 99.0
    assert lip_foot_reach(lambda x, z, lo, hi: None, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 10.0, 1.0) == 0.0


def test_gap_reads_the_gate_window():
    # drive_test reads the highest surface in [base-3, base+2] first: a deck 2.5 m above the foot is not its ground
    from scripts.geometry.build_mesh import lip_foot_gap

    def two(x, z, lo, hi):
        ys = [y for y in (99.5, 102.5) if lo <= y <= hi]
        return max(ys) if ys else None
    assert abs(lip_foot_gap(two, 0.0, 0.0, 100.0) - 0.5) < 1e-9


# END APRON (ledger 0076, Under the Dragon (Gravel) s 25,706): the road ends at the origin running +x (outward
# tangent +x), deck 10.54, half-width 3.25; one grass cell's diagonal of reach (1.913 m x sqrt 2, the stage's x7 refine)
_TIP = [(0.0, 10.54, 0.0, 1.0, 0.0, 3.25)]
_REACH = 2.705


def test_end_apron_caps_the_node_at_the_end_corner():
    from scripts.geometry.build_mesh import end_apron_cap
    # the node that rose 0.88 m: 0.08 m past the end row, 3.81 m off the axis (just outside the deck corner)
    assert end_apron_cap(0.08, -3.81, _TIP, _REACH) == 10.54
    assert end_apron_cap(2.0, 0.0, _TIP, _REACH) == 10.54


def test_end_apron_leaves_the_road_and_its_verges_alone():
    from scripts.geometry.build_mesh import end_apron_cap
    assert end_apron_cap(-0.5, 0.0, _TIP, _REACH) is None          # on the deck: the pavement cap's job
    assert end_apron_cap(-5.0, 4.5, _TIP, _REACH) is None          # beside the road: under the shoulder
    assert end_apron_cap(0.0, 0.0, _TIP, _REACH) is None           # ON the end row: not past it
    assert end_apron_cap(_REACH + 0.1, 0.0, _TIP, _REACH) is None  # too far out for a triangle to reach back
    assert end_apron_cap(1.0, 3.25 + _REACH + 0.1, _TIP, _REACH) is None
    assert end_apron_cap(1.0, 0.0, [], _REACH) is None             # a closed lap has no ends


def test_end_apron_two_ends_lowest_deck_wins():
    from scripts.geometry.build_mesh import end_apron_cap
    tips = _TIP + [(1.5, 9.0, 0.0, -1.0, 0.0, 3.25)]   # another end facing back over the same ground
    assert end_apron_cap(1.0, 0.0, tips, _REACH) == 9.0


def _line(n, x0=0.0):
    return [(x0 + 3.0 * i, 0.0, 0.0) for i in range(n)]


def test_replication_pads_an_open_stage_lead_in():
    from scripts.geometry.drive_test import pad_for_lead_in
    local = _line(5)
    gate = _line(9, x0=-6.0)               # 2 lead verts each end: vertex 2 sits on local[0]
    z = [1.0, 2.0, 3.0, 4.0, 5.0]
    out = pad_for_lead_in(z, gate, local)
    assert out == [None, None, 1.0, 2.0, 3.0, 4.0, 5.0, None, None]
    # driven in reverse the gate line is reversed first: vertex len-1-k is local[0]
    assert pad_for_lead_in(z, gate[::-1], local) == out


def test_replication_leaves_other_lines_alone():
    from scripts.geometry.drive_test import pad_for_lead_in
    z = [1.0, 2.0, 3.0, 4.0, 5.0]
    local = _line(5)
    assert pad_for_lead_in(z, _line(5), local) is z                 # same length: a loop, or no lead-in
    assert pad_for_lead_in(z, _line(6), local) is z                 # closed lap's duplicate: odd difference
    assert pad_for_lead_in(z, _line(9, x0=100.0), local) is z       # longer, but not this line's lead-in
    assert pad_for_lead_in(z, _line(9, x0=-6.0), []) is z


def test_replication_mirror_x_frame():
    from scripts.geometry.drive_test import pad_for_lead_in
    local = [(3.0 + 3.0 * i, 0.0, 0.0) for i in range(5)]
    gate = [(-3.0 * i, 0.0, 0.0) for i in range(7)]   # mesh frame mirrors x; vertex 1 sits on -local[0]
    assert pad_for_lead_in([1, 2, 3, 4, 5], gate, local) == [None, 1, 2, 3, 4, 5, None]
