"""ledger 0075: network.join_nodes — network_elev gives a node every edge shares ONE height (each edge used to be
smoothed and forward-capped alone: 19.86 m apart at the worst freeway node). Stdlib only."""
from scripts.elevation.network_elev import MAX_GRADE, _join_edges, _smooth_edge


def _edge(pid, lon0, lon1, n, ramp=False):
    return {"properties": {"id": pid, "is_ramp": ramp},
            "geometry": {"coordinates": [[lon0 + (lon1 - lon0) * k / (n - 1), 32.78] for k in range(n)]}}


def test_two_edges_meet_at_one_height():
    # edge 1 climbs steeper than the cap toward the shared node, edge 2 runs on flat from it
    F = [_edge(1, -117.20, -117.19, 21), _edge(2, -117.19, -117.18, 21)]
    raw = {1: [0.0 + 4.0 * k for k in range(21)], 2: [80.0] * 21}   # 8.5 % > the 5 % cap
    alone = {pid: _smooth_edge(raw[pid], 47.0) for pid in raw}
    assert abs(alone[1][-1] - alone[2][0]) > 1.0              # the defect: two heights at one node
    z = _join_edges(F, raw, 47.0)
    assert abs(z[1][-1] - z[2][0]) < 1e-9


def test_joined_edges_hold_the_cap_where_it_is_feasible():
    F = [_edge(1, -117.20, -117.19, 21), _edge(2, -117.19, -117.18, 21)]
    raw = {1: [10.0 + 0.1 * k for k in range(21)], 2: [12.0 - 0.1 * k for k in range(21)]}
    z = _join_edges(F, raw, 47.0)
    for pid in (1, 2):
        v = z[pid]
        # ~47 m segments; the cap is by real segment length
        assert max(abs(v[i] - v[i - 1]) for i in range(1, len(v))) <= MAX_GRADE * 47.0


def test_a_dead_end_keeps_its_own_profile_end():
    F = [_edge(1, -117.20, -117.19, 11)]
    raw = {1: [5.0] * 11}
    assert _join_edges(F, raw, 94.0)[1] == [5.0] * 11
