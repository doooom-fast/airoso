"""scripts-v021 geometry/ribbon.connector_markings — a connector's paint, the ONE call the assembler
(blender/build_loop_blend.py) and tools/weld_mouths_blend.py's layout check both make (ledger 0054 phase 5,
2026-10-18). A plain connector is painted exactly as before (lane_markings, centre yellow). A phase-5 stub is painted as
the two-lane side street it is: no lane divider 0.6-1.8 m inside each edge line (the verifier's "doubled edge lines"),
and nothing within its barrier's footprint or on the 1 m tail behind it. Loaded by path: the module is pure Python."""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_s = importlib.util.spec_from_file_location(
    "_v021_ribbon", ROOT / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "ribbon.py")
rb = importlib.util.module_from_spec(_s)
_s.loader.exec_module(rb)

# a stub as tools/stub_roads.py writes it: a point 1 m inside the cut (trimmed away), then every metre to 16.4 m —
# the barrier's centre line 15.4 m from the cut, the road running on TAIL_M = 1 m behind it
PTS = [(0.0, 5.0 + 0.02 * u, float(u)) for u in range(0, 17)] + [(0.0, 5.0 + 0.02 * 16.4, 16.4)]
W = [9.6] * len(PTS)
STUB = {"id": "x", "tail_m": 1.0, "length_m": 15.0, "lanes_per_side": 1}


def _lines(mesh):
    """per painted quad (4 verts: s0 -, s0 +, s1 -, s1 +): (lateral centre, z0, z1)"""
    v = mesh["vertices"]
    out = []
    for q in range(0, len(v), 4):
        a, b, c, d = v[q:q + 4]
        out.append(((a[0] + b[0]) / 2.0, min(a[2], c[2]), max(a[2], c[2])))
    return out


def test_a_plain_connector_is_painted_exactly_as_before():
    for ws in (W, [17.0] * len(PTS)):
        a = rb.connector_markings(PTS, ws, None)
        b = rb.lane_markings(PTS, ws, center_yellow=True)
        assert a == b


def test_the_generic_rule_paints_a_divider_just_inside_a_side_streets_edge_lines():
    """the defect, pinned: on a 9.6 m two-lane street lane_markings lays a 3 m dash 0.6 m inside each 4.25 m edge line
    at both ends of a 15 m stub"""
    lm = _lines(rb.lane_markings(PTS, W, center_yellow=True)["white"])
    div = [l for l in lm if abs(abs(l[0]) - 3.65) < 0.01]
    assert div and min(l[1] for l in div) < 1.0 and max(l[2] for l in div) > 12.0


def test_a_stub_has_no_divider_and_no_paint_at_or_past_its_barrier():
    m = rb.connector_markings(PTS, W, STUB)
    white = _lines(m["white"])
    yellow = _lines(m["yellow"])
    assert white and yellow
    # only the two edge lines (half 4.8 - edge inset 0.55) and the double yellow (+-0.09)
    assert {round(abs(l[0]), 2) for l in white} == {4.25}
    assert {round(abs(l[0]), 2) for l in yellow} == {0.09}
    toe = 15.4 - rb.STUB_BARRIER_HALF_BASE_M
    end = max(l[2] for l in white + yellow)
    assert abs(end - (toe - rb.STUB_PAINT_STOP_M)) < 1e-9, end
    assert min(l[1] for l in white) == 0.0                         # still painted from the mouth


def test_a_four_lane_stub_keeps_one_divider_a_side():
    ws = [16.8] * len(PTS)
    white = _lines(rb.connector_markings(PTS, ws, dict(STUB, lanes_per_side=2))["white"])
    assert {round(abs(l[0]), 2) for l in white} == {3.65, round(8.4 - 0.55, 2)}
