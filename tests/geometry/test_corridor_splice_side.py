"""Ledger 0067: a grid node near the road takes the ground height from its own side of the road.

fetch_corridor writes rows along the LEFT normal (+ = left of travel). The splice used to read the
mirrored lateral, so a node on one side took the height of the same distance on the other."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("_bm_0067", ROOT / "scripts" / "geometry" / "build_mesh.py")
sys.path.insert(0, str(ROOT))
bm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bm)

HALF, STEP = 60.0, 4.0
OFFS = [-HALF + i * STEP for i in range(int(2 * HALF / STEP) + 1)]
LEFT_H, RIGHT_H = 100.0, 50.0
# left side (offset > 0) high, right side (offset < 0) low
ROW = [LEFT_H if o > 0 else RIGHT_H if o < 0 else 75.0 for o in OFFS]


def _height(node_real, mirror_x):
    """Road runs due north from the origin (real east, north); node_real = (east, north) offset.
    Returns the spliced height, working in the local frame (x negated when mirror_x)."""
    sx = -1.0 if mirror_x else 1.0
    tx, tz = 0.0, 1.0                       # travelling north, in the local frame
    dx, dz = sx * node_real[0], node_real[1]
    lat = bm.corridor_lateral(tx, tz, dx, dz, mirror_x)
    return bm.corridor_row_height(ROW, lat, HALF, STEP)


def test_node_left_of_travel_gets_left_height_unmirrored():
    assert _height((-20.0, 0.0), False) == LEFT_H      # west of a northbound road = left


def test_node_right_of_travel_gets_right_height_unmirrored():
    assert _height((20.0, 0.0), False) == RIGHT_H


def test_node_left_of_travel_gets_left_height_mirrored():
    assert _height((-20.0, 0.0), True) == LEFT_H


def test_node_right_of_travel_gets_right_height_mirrored():
    assert _height((20.0, 0.0), True) == RIGHT_H


def test_lateral_sign_with_a_turned_tangent():
    # eastbound road: left is north
    for mirror in (False, True):
        sx = -1.0 if mirror else 1.0
        assert bm.corridor_lateral(sx * 1.0, 0.0, 0.0, 15.0, mirror) == 15.0
        assert bm.corridor_lateral(sx * 1.0, 0.0, 0.0, -15.0, mirror) == -15.0


def test_missing_sample_gives_none():
    assert bm.corridor_row_height([None, 1.0, 2.0], -4.0, 4.0, 4.0) is None
