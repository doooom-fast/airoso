"""ledger 0075: the network barrier's seat (scenery.walls.seat "seated", the San Diego freeway). Stdlib only."""
from scripts.geometry.build_network_mesh import (
    DECK_BARRIER_OFF_M, DECK_EDGE_EXT_M, DECK_EDGE_W_M, ROAD_LIFT_M, WALL_GROUND_BURY_M,
    _deck_edge, _drop_verge_on_pavement, _grid_ground, _pavement_hash, _pavement_in, _wall, _wall_seated,
)

DECK = [(0.0, 10.0, float(z)) for z in range(0, 40, 4)]     # a straight road north at y 10, half-width 5
N = len(DECK)
HALVES = [5.0] * N


def test_the_default_seat_is_untouched():
    m = _wall(DECK, 5.0, off=3.2, h=1.1)
    assert sorted({round(abs(v[0]), 3) for v in m["vertices"]}) == [8.2]
    assert min(v[1] for v in m["vertices"]) == 10.0 - 0.35


def test_at_grade_the_base_reaches_under_the_built_ground():
    falls = lambda x, z: 10.0 - 3.0 if abs(x) > 5.0 else 10.0          # noqa: E731  ground 3 m down past the pavement
    m = _wall_seated(DECK, HALVES, [False] * N, off=0.5, h=1.1, ground=falls)
    bases = sorted({round(v[1], 6) for v in m["vertices"] if v[1] < 10.0})
    tops = sorted({round(v[1], 6) for v in m["vertices"] if v[1] > 10.0})
    assert bases == [round(7.0 - WALL_GROUND_BURY_M, 6)] and tops == [11.1]
    assert {round(abs(v[0]), 3) for v in m["vertices"]} == {5.5}


def test_at_grade_in_a_cut_the_base_stays_under_the_deck():
    rises = lambda x, z: 14.0                                           # noqa: E731
    m = _wall_seated(DECK, HALVES, [False] * N, off=0.5, h=1.1, ground=rises)
    assert min(v[1] for v in m["vertices"]) == 10.0 - 0.35


def test_on_a_deck_the_barrier_stands_on_the_deck_edge():
    m = _wall_seated(DECK, HALVES, [True] * N, off=0.5, h=1.1, ground=lambda x, z: -20.0)
    assert {round(abs(v[0]), 3) for v in m["vertices"]} == {round(5.0 + DECK_BARRIER_OFF_M, 3)}
    assert min(v[1] for v in m["vertices"]) == 10.0 - 0.35             # never draped into the valley
    assert DECK_BARRIER_OFF_M < DECK_EDGE_W_M                          # ...and inside the slab it stands on


def test_the_barrier_follows_the_ribbons_own_width():
    taper = [5.0 - 0.5 * i for i in range(N)]
    m = _wall_seated(DECK, taper, [False] * N, off=0.5, h=1.1, ground=None)
    xs = sorted({round(v[0], 3) for v in m["vertices"] if v[0] > 0})
    assert xs[0] == round(taper[-1] + 0.5, 3) and xs[-1] == round(taper[0] + 0.5, 3)


def test_keep_gaps_one_side_only():
    keep = {1.0: [True] * N, -1.0: [True] * 4 + [False] + [True] * (N - 5)}
    m = _wall_seated(DECK, HALVES, [False] * N, off=0.5, h=1.1, keep=keep)
    panels = len(m["tris"]) // 2 // 2                                 # double-sided, two tris a panel
    assert panels == (N - 1) + (N - 1 - 2)                            # one vertex gapped = two panels gone, one side


def test_deck_edge_slab_spans_the_deck_edge_at_pavement_height():
    ok = {1.0: [True] * (N - 1), -1.0: [False] * (N - 1)}
    de = _deck_edge(DECK, HALVES, ok)
    assert {round(v[1], 6) for v in de["vertices"]} == {round(10.0 + ROAD_LIFT_M, 6)}
    assert sorted({round(abs(v[0]), 3) for v in de["vertices"]}) == [5.0, round(5.0 + DECK_EDGE_W_M, 3)]
    assert len({v[0] > 0 for v in de["vertices"]}) == 1                # one side only
    assert len(de["tris"]) == 2 * (N - 1)
    for a, b, c in de["tris"]:                                         # face up (drivable, verify_kn5)
        V = de["vertices"]
        ny = (V[b][2] - V[a][2]) * (V[c][0] - V[a][0]) - (V[b][0] - V[a][0]) * (V[c][2] - V[a][2])
        assert ny >= 0.0


def test_deck_edge_extends_past_an_end_node():
    ok = {1.0: [True] * (N - 1), -1.0: [False] * (N - 1)}
    de = _deck_edge(DECK, HALVES, ok, ext_ok={1.0: (True, True)})
    zs = sorted({round(v[2], 3) for v in de["vertices"]})
    assert zs[0] == -DECK_EDGE_EXT_M and zs[-1] == round(36.0 + DECK_EDGE_EXT_M, 3)


def test_pavement_in_is_triangle_exact_with_a_height_window_and_a_skip():
    road = {"vertices": [(-5.0, 1.0, 0.0), (5.0, 1.0, 0.0), (5.0, 1.0, 10.0), (-5.0, 1.0, 10.0)],
            "tris": [(0, 1, 2), (0, 2, 3)]}
    h = _pavement_hash([("e7", road)])
    assert _pavement_in(h, 0.0, 5.0, 0.0, 2.0)
    assert not _pavement_in(h, 6.0, 5.0, 0.0, 2.0)                     # beside it
    assert not _pavement_in(h, 0.0, 5.0, 2.5, 4.0)                     # under a deck high above
    assert not _pavement_in(h, 0.0, 5.0, 0.0, 2.0, skip="e7")


def test_grid_ground_is_the_rendered_triangle():
    # 2x2 nodes, row 0 north (z falls with j), x rises with i; the (a,b,c)+(a,c,d) split of _grass_tiles
    grid = [[(0.0, 0.0, 10.0), (10.0, 10.0, 10.0)],
            [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0)]]
    g = _grid_ground(grid)
    assert abs(g(9.0, 9.0) - 8.0) < 1e-9          # triangle a-b-c (u 0.9 >= v 0.1): 10 u - 10 v
    assert abs(g(1.0, 1.0) - 0.0) < 1e-9          # triangle a-c-d: all zero but b
    assert g(20.0, 5.0) is None


def test_a_shoulder_over_a_neighbours_lanes_is_dropped_its_own_edge_is_not():
    lanes = {"vertices": [(0.0, 1.0, 0.0), (10.0, 1.0, 0.0), (10.0, 1.0, 10.0), (0.0, 1.0, 10.0)],
             "tris": [(0, 1, 2), (0, 2, 3)]}
    pave = _pavement_hash([("e1", lanes), ("e2", lanes)])
    over = {"vertices": [(2.0, 1.02, 2.0), (4.0, 1.02, 2.0), (4.0, 1.02, 4.0)], "uvs": [(0, 0)] * 3, "tris": [(0, 1, 2)]}
    under = {"vertices": [(2.0, 0.5, 2.0), (4.0, 0.5, 2.0), (4.0, 0.5, 4.0)], "uvs": [(0, 0)] * 3, "tris": [(0, 1, 2)]}
    out, n = _drop_verge_on_pavement([("v2", over), ("v3", under)], _pavement_hash([("e1", lanes)]))
    assert n == 1 and [nm for nm, _m in out] == ["v3"]       # 2 cm over edge 1's lanes: gone; 0.5 m under: kept
    out, n = _drop_verge_on_pavement([("v1", over)], _pavement_hash([("e1", lanes)]))
    assert n == 0                                            # its own edge's pavement never drops it
    assert pave                                              # (both ribbons hashed)
