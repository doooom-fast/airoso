"""Ledger 0070 D-pads — route.padded_corners: an authored junction pad owns a corner's pavement, so
scripts/gps/widths_from_osm.detect_turn_corners sweeps no corner flare there (opt-in; absent = byte-identical)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.gps import widths_from_osm as W  # noqa: E402

LAT0, LON0 = 39.78, -104.93
DLAT = 3.0 / 110540.0           # 3 m in latitude (the module's own constants)


def _dlon(m):
    import math
    return m / (111320.0 * math.cos(math.radians(LAT0)))


def _corner_world():
    """a lap driving east 150 m along "A St" then north 150 m up "B St"; the two ways share the corner node"""
    cl = [(LON0 + _dlon(3.0 * i), LAT0) for i in range(51)]
    cl += [(LON0 + _dlon(150.0), LAT0 + DLAT * i) for i in range(1, 51)]
    corner = (LON0 + _dlon(150.0), LAT0)
    ways = [{"id": 1, "name": "A St", "highway": "residential", "lanes": 2, "nodes": [10, 11], "geom": [cl[0], corner]},
            {"id": 2, "name": "B St", "highway": "residential", "lanes": 2, "nodes": [11, 12], "geom": [corner, cl[-1]]}]
    return cl, ways, corner


def test_a_corner_flares_unless_padded():
    cl, ways, corner = _corner_world()
    base = W.detect_turn_corners(ways, cl)
    assert len(base) == 1 and abs(base[0]["idx"] - 50) <= 6, base
    # padded at the corner node: no flare
    assert W.detect_turn_corners(ways, cl, padded=[(corner[0], corner[1], 30.0)]) == []
    # a pad elsewhere (200 m away) leaves this corner flared exactly as before
    far = (corner[0] + _dlon(200.0), corner[1])
    assert W.detect_turn_corners(ways, cl, padded=[(far[0], far[1], 30.0)]) == base
    # empty / None: byte-identical
    assert W.detect_turn_corners(ways, cl, padded=[]) == base
    assert W.detect_turn_corners(ways, cl, padded=None) == base
