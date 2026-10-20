"""scripts-v021 geometry/scenery.scatter — index_offset (ledger 0054 P2, 2026-10-14). The assembler's procedural trees and
scrub take their jitter and pick from each terrain node's (row, col); a heightfield grown by whole cells (grid_grow)
shifts every index, so build_loop_blend passes the rows / cols it added and every old node keeps its own. The added
nodes sit >= 150 m from the loop (the grid's margin) and place nothing. Loaded by path: the module is pure Python."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_s = importlib.util.spec_from_file_location(
    "_v021_scenery", ROOT / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "scenery.py")
sc = importlib.util.module_from_spec(_s)
_s.loader.exec_module(sc)


def _grid(rows, cols, r0=0, c0=0):
    """a 20 m grid whose node (r, c) stands at x = (c - c0) * 20, z = -(r - r0) * 20"""
    return [[((c - c0) * 20.0, 1.0 + 0.01 * (c - c0), -(r - r0) * 20.0) for c in range(cols)] for r in range(rows)]


ROAD = [(200.0 + x * 5.0, 0.0, -200.0) for x in range(0, 41)]          # >= 150 m inside every edge
W = [10.0] * len(ROAD)


def test_a_grown_grid_scatters_exactly_as_before():
    a, na, sa = sc.scatter(_grid(21, 31), ROAD, W, tree_pct=40, scrub_pct=26)
    assert na > 5 and sa > 5
    # the same ground grown by 8 rows north (+ 8 south) and 9 columns west: every old node shifts by (8, 9)
    b, nb, sb = sc.scatter(_grid(37, 40, 8, 9), ROAD, W, tree_pct=40, scrub_pct=26, index_offset=(8, 9))
    assert (na, sa) == (nb, sb) and a == b
    c, _nc, _sc = sc.scatter(_grid(37, 40, 8, 9), ROAD, W, tree_pct=40, scrub_pct=26)
    assert c != a                           # without the offset every jitter and pick moves
