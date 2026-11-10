"""ledger 0075: network.stable_snap — one coordinate, one node. The greedy snap moves a cluster's centre as points join
it, so a point two OSM ways share could land in two clusters a few metres apart with no link between them (three
6.1-6.7 m holes in the freeway's I 8 eastbound). Stdlib only."""
from scripts.gps.network import _NodeGrid

S = (3.6, 0.0)      # the shared point


def _greedy():
    g = _NodeGrid(7.0)
    first = g.assign(*S)                      # way 1 meets S: cluster A
    for p in ((-3.0, 0.0), (-5.0, 0.0)):      # A's running mean drifts west, away from S
        g.assign(*p)
    g.assign(8.0, 0.0)                        # cluster B, east of S
    again = g.assign(*S)                      # way 2 meets the SAME point
    return g, first, again


def test_the_greedy_snap_can_put_one_point_in_two_nodes():
    _g, first, again = _greedy()
    assert first != again


def test_the_stable_snap_puts_one_point_in_one_node():
    g, first, again = _greedy()
    assert g.nearest(*S, first) == g.nearest(*S, again)
    c = g.nearest(*S, first)
    d = [((S[0] - g.cx[i]) ** 2 + (S[1] - g.cy[i]) ** 2) for i in range(len(g.cx))]
    assert d[c] == min(d)                     # the nearest FINAL centre


def test_nearest_falls_back_when_nothing_is_near():
    g = _NodeGrid(7.0)
    g.assign(0.0, 0.0)
    assert g.nearest(500.0, 500.0, -1) == -1


def test_layers_do_not_snap_together_but_a_shared_coordinate_does():
    g = _NodeGrid(7.0)
    deck = g.assign(0.0, 0.0, layer=2)          # a flyover vertex over...
    under = g.assign(3.0, 0.0, layer=0)         # ...a mainline vertex 3 m away in plan: no junction between them
    assert deck != under
    shared = g.assign(0.0, 0.0, layer=0)        # a ramp leaving the flyover at its own vertex: one node
    assert shared == deck
    assert g.nearest(3.0, 0.0, -1, layer=0) == under and g.nearest(0.5, 0.0, -1, layer=2) == deck
