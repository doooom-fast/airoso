"""Ledger 0070 B2: ribbon.lane_markings paints the street's own lanes (OSM `lanes` per vertex, width-derived where
untagged) and holds every line inside 0.9 of the local radius. Stdlib only."""
import math

from scripts.geometry.ribbon import lane_markings

STRAIGHT = [(0.0, 0.0, float(z)) for z in range(0, 120, 3)]


def _offsets(mesh):
    return sorted({round(v[0], 3) for v in mesh["vertices"]})


def test_untagged_stations_keep_the_width_derived_dividers():
    a = lane_markings(STRAIGHT, [20.0] * len(STRAIGHT))
    b = lane_markings(STRAIGHT, [20.0] * len(STRAIGHT), lanes=[None] * len(STRAIGHT))
    assert a == b                                                   # the fallback is the old behaviour, exactly


def test_osm_lanes_set_the_dividers():
    w = [20.0] * len(STRAIGHT)
    two = lane_markings(STRAIGHT, w, lanes=[2] * len(STRAIGHT))["white"]
    four = lane_markings(STRAIGHT, w, lanes=[4] * len(STRAIGHT))["white"]
    width_only = lane_markings(STRAIGHT, w)["white"]
    edge = 20.0 / 2 - 0.55
    assert max(abs(o) for o in _offsets(two)) > edge - 0.1                # the edge lines stand
    assert all(abs(abs(o) - edge) < 0.1 for o in _offsets(two))           # a two-lane street: edges only, no divider
    assert sum(1 for o in _offsets(four) if abs(abs(o) - 3.65) < 0.1) == 4  # one divider a side (both line faces)
    assert len(_offsets(width_only)) > len(_offsets(four))                 # the width alone painted phantom lanes


def test_no_line_reaches_the_inside_of_a_tight_corner():
    r = 8.0                                                              # a 90 deg corner tighter than the edge offset
    arc = [(r - r * math.cos(t), 0.0, r * math.sin(t)) for t in [i * math.pi / 2 / 12 for i in range(13)]]
    pts = [(0.0, 0.0, float(z)) for z in range(-30, 0, 3)] + arc + [(r + 3.0 * k, 0.0, r) for k in range(1, 10)]
    m = lane_markings(pts, [22.0] * len(pts), lanes=[2] * len(pts))
    cx, cz = r, 0.0                                                      # the corner's centre
    reach = min(math.hypot(v[0] - cx, v[2] - cz) for v in m["white"]["vertices"]
                if 0 < v[2] < r and v[0] < r)
    assert reach >= 0.1 * r - 0.07                                       # held 0.9 R out from the centre, not folded past it
