"""ledger 0075: one height per shared node of a road network (scripts.geometry.network_joins). Stdlib only."""
from scripts.geometry.network_joins import away_dir, node_key, pinned_cap, ramped, through_targets


def test_node_key_matches_one_coordinate():
    assert node_key(-117.17, 32.78) == node_key(-117.1700000001, 32.7800000001)
    assert node_key(-117.17, 32.78) != node_key(-117.1701, 32.78)


def test_away_dir_reads_into_the_edge():
    xy = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0), (15.0, 0.0), (20.0, 0.0)]
    assert away_dir(xy, 0) == (1.0, 0.0)
    assert away_dir(xy, 1) == (-1.0, 0.0)


def test_a_two_edge_node_takes_the_mean():
    t = through_targets({"n": [(1, 1, 10.0, (-1.0, 0.0), False), (2, 0, 12.0, (1.0, 0.0), False)]})
    assert t == {"n": 11.0}


def test_a_ramp_takes_the_mainlines_value_not_the_reverse():
    # mainline 1 -> 2 runs straight through at 0 lift; ramp 3 leaves at 30 degrees carrying 4 m of OSM layer lift
    rows = [(1, 1, 0.0, (-1.0, 0.0), False), (2, 0, 0.0, (1.0, 0.0), False),
            (3, 0, 4.0, (0.866, 0.5), True)]
    assert through_targets({"n": rows}) == {"n": 0.0}


def test_the_straightest_pair_wins_among_mainlines():
    rows = [(1, 1, 10.0, (-1.0, 0.0), False), (2, 0, 10.0, (1.0, 0.0), False), (3, 0, 20.0, (0.0, 1.0), False)]
    assert through_targets({"n": rows}) == {"n": 10.0}


def test_a_dead_end_is_not_a_shared_node():
    assert through_targets({"n": [(1, 0, 3.0, (1.0, 0.0), False)]}) == {}


def _grades(v, d):
    return [abs(v[i] - v[i - 1]) / max(0.5, d[i]) for i in range(1, len(v))]


def test_pinned_cap_holds_both_ends_and_the_cap():
    d = [0.0] + [5.0] * 20
    vals = [0.0] * 21                                      # a flat profile that must meet a node 3 m up at its end
    out = pinned_cap(vals, d, 0.0, 3.0, 0.05)
    assert out[0] == 0.0 and out[-1] == 3.0
    assert max(_grades(out, d)) <= 0.05 + 1e-9
    assert out[5] == 0.0                                  # the far end is untouched: only what the cap forces moves


def test_pinned_cap_is_a_straight_grade_when_the_pins_are_too_far_apart():
    d = [0.0] + [5.0] * 4                                 # 20 m: 5 % allows 1 m, the pins are 4 m apart
    out = pinned_cap([0.0] * 5, d, 0.0, 4.0, 0.05)
    assert [round(v, 6) for v in out] == [0.0, 1.0, 2.0, 3.0, 4.0]


def test_pinned_cap_leaves_a_profile_inside_the_cap_alone():
    d = [0.0] + [5.0] * 6
    vals = [0.0, 0.1, 0.2, 0.25, 0.3, 0.35, 0.4]
    assert pinned_cap(vals, d, 0.0, 0.4, 0.05) == vals


def test_ramped_blends_each_end_back_and_holds_them_exactly():
    d = [0.0] + [10.0] * 20                               # 200 m
    out = ramped([5.0] * 21, d, -5.0, 0.0, ramp_grade=0.05, ramp_min_m=40.0)
    assert out[0] == 0.0 and out[-1] == 5.0
    assert out[10] == 5.0 and abs(out[5] - 2.5) < 1e-9   # 5 m / 5 % = 100 m ramp


def test_ramped_overlapping_ramps_become_one_straight_blend():
    d = [0.0] + [10.0] * 4                                # 40 m, both ramps 40 m long
    out = ramped([0.0] * 5, d, 2.0, -2.0, ramp_grade=0.05, ramp_min_m=40.0)
    assert [round(v, 6) for v in out] == [2.0, 1.0, 0.0, -1.0, -2.0]
