"""ledger 0075: network.cap_dead_ends — a road the network does not complete gets a barrier, not a curve (Kevin,
JUNCTIONS 18(d)); network_reference then starts / ends its line inside the cap. Stdlib only."""
from scripts.geometry.build_network_mesh import CAP_SETBACK_M, WALL_GROUND_BURY_M, _along, _cap_wall
from scripts.geometry.network_reference import _trim_capped

ROAD = [(0.0, 10.0, float(z)) for z in range(0, 41, 5)]    # north at y 10, 40 m


def test_along_measures_in_from_either_end():
    i, j, t = _along(ROAD, 0, CAP_SETBACK_M)
    assert (i, j) == (0, 1) and abs(t - CAP_SETBACK_M / 5.0) < 1e-9
    i, j, t = _along(ROAD, 1, 7.0)
    assert (i, j) == (7, 6) and abs(t - 0.4) < 1e-9
    assert _along(ROAD, 0, 41.0) is None


def test_the_cap_spans_the_carriageway_to_both_side_barriers():
    m, (left, right) = _cap_wall((0.0, 10.0, 2.0), 1.0, 0.0, 5.0, off=0.5, h=1.1,
                                 ground=lambda x, z: 6.0)                     # ground 4 m down past the pavement
    xs = [v[0] for v in m["vertices"]]
    assert min(xs) == -5.5 and max(xs) == 5.5 and left == (-5.5, 2.0) and right == (5.5, 2.0)
    on_road = [v[1] for v in m["vertices"] if abs(v[0]) <= 5.0 and v[1] < 10.0]
    off_road = [v[1] for v in m["vertices"] if abs(v[0]) > 5.0 and v[1] < 10.0]
    assert set(on_road) == {10.0 - 0.35}                                      # on the pavement: under the deck
    assert set(off_road) == {6.0 - WALL_GROUND_BURY_M}                        # beyond it: into the ground
    assert {v[1] for v in m["vertices"] if v[1] > 10.0} == {11.1}
    assert len(m["tris"]) % 2 == 0 and all(v[2] == 2.0 for v in m["vertices"])


def _line(n=30):
    g = [[0.0, 0.0, 5.0 * i] for i in range(n)]
    return [list(p) for p in g], g, [16.0] * n, [[1, i] for i in range(n)]


def test_the_line_starts_and_ends_inside_its_caps():
    surf, grade, w, src = _line()
    caps = [{"id": "a", "node_xz": [0.0, 0.0], "line_trim_m": 12.0},
            {"id": "b", "node_xz": [0.0, 145.0], "line_trim_m": 12.0}]
    s2, g2, w2, src2, done = _trim_capped(surf, grade, w, src, caps)
    assert g2[0][2] == 15.0 and g2[-1][2] == 130.0                           # first vertex >= 12 m in, each end
    assert len(s2) == len(g2) == len(w2) == len(src2)
    assert [d["end"] for d in done] == ["start", "finish"]


def test_an_uncapped_end_is_left_alone():
    surf, grade, w, src = _line()
    s2, g2, _w, _s, done = _trim_capped(surf, grade, w, src, [{"id": "x", "node_xz": [50.0, 50.0], "line_trim_m": 12.0}])
    assert g2 == grade and done == []
