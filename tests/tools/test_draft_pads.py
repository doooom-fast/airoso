"""tools/draft_pads.py, the pure half of the engine-draft pads (ledger 0048 P3b): the traced outline, the cut barriers, the
deck heights and the seam weld. Stdlib only."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools import draft_pads as dp  # noqa: E402


def _grid(rows):
    g = [[ch == "#" for ch in r] for r in rows]
    return g, [float(c) for c in range(len(rows[0]))], [float(-r) for r in range(len(rows))]


def test_the_traced_outline_is_closed_counter_clockwise_and_on_the_region():
    g, xs, ys = _grid(["........", "..####..", ".######.", ".######.", "...##...", "........"])
    ring = dp.trace_boundary(g, xs, ys)
    assert dp.ring_area(ring) > 0                                             # counter-clockwise in E/N
    cells = {(int(x), int(-y)) for x, y in ring}
    assert all(g[r][c] for c, r in cells)                                     # every outline point is a region cell
    outer = {(c, r) for r in range(len(g)) for c in range(len(g[0])) if g[r][c] and any(
        not g[r + dr][c + dc] for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)))}
    assert outer <= cells                                                     # and every border cell is on it


def test_smoothing_keeps_a_cut_edge_exactly_straight_and_only_near_its_segment():
    sq = [(float(x), 0.0) for x in range(0, 20)] + [(20.0, float(y)) for y in range(0, 20)] + \
         [(float(x), 20.0) for x in range(20, 0, -1)] + [(0.0, float(y)) for y in range(20, 0, -1)]
    cut = dp.sealed_cut(((5.0, -0.3), (15.0, -0.3)), (10.0, 10.0))           # a cut along the bottom edge's middle
    out = dp.smooth_ring(sq, 1.0, keep_on=[cut])
    on = [p for p in out if 6.0 <= p[0] <= 14.0 and p[1] < 1.0]
    assert on and all(abs(p[1] + 0.3) < 1e-9 for p in on)                    # snapped exactly onto the cut line
    corner = [p for p in out if p[0] < 2.0 and p[1] < 2.0]
    assert corner and all(abs(p[1] + 0.3) > 1e-6 for p in corner)           # outside the segment: left alone


def test_resampling_spaces_the_ring_evenly():
    ring = [(0.0, 0.0), (30.0, 0.0), (30.0, 10.0), (0.0, 10.0)]
    out = dp.resample_ring(ring, 0.75)
    steps = [math.dist(out[i - 1], out[i]) for i in range(len(out))]
    assert len(out) == round(80 / 0.75) and max(steps) <= 80 / len(out) + 1e-9      # equal along the ring;
    assert sum(1 for d in steps if abs(d - 80 / len(out)) < 1e-9) >= len(out) - 4      # a chord across a corner is shorter


def test_the_deck_is_the_ground_plane_with_one_trim():
    pts = [(dx, dy, 2.0 + 0.03 * dx - 0.01 * dy) for dx in (-1.5, -0.5, 0.5, 1.5) for dy in (-1.5, -0.5, 0.5, 1.5)]
    pts.append((0.2, 0.1, 2.6))                                              # a car roof / a curb top: trimmed
    assert abs(dp.plane_height(pts) - 2.0) < 1e-9
    assert dp.plane_height(pts[:5]) is None                                  # too few ground points: no plane


def test_deck_lookup_and_its_fallback_near_the_asphalt_edge():
    deck = {"e0": 0.0, "n0": 0.0, "cell_m": 0.5, "nx": 4, "ny": 4,
            "y": [[1.0, 1.0, None, None], [1.0, 1.0, None, None], [None] * 4, [None] * 4]}
    assert dp.deck_at(deck, 0.25, 0.25) == pytest.approx(1.0)
    assert dp.deck_at(deck, 1.5, 1.5) is None
    assert dp.deck_near(deck, 1.5, 1.5) == pytest.approx(1.0)               # the nearest measured node within 3 m
    assert dp.deck_near(deck, 40.0, 40.0) is None


def test_the_seam_blend_is_exact_on_a_seam_vertex_and_smooth_between():
    seams = [(0.0, 0.0, 0.3), (10.0, 0.0, -0.1)]
    assert dp.seam_blend(0.0, 0.0, seams) == 0.3 and dp.seam_blend(10.0, 0.0, seams) == -0.1
    mid = dp.seam_blend(5.0, 0.0, seams)
    assert -0.1 < mid < 0.3 and abs(mid - 0.1) < 1e-9


def test_a_cut_is_a_barrier_segment_not_a_half_plane():
    assert dp.segment_band((0.0, 0.0), (10.0, 0.0), 5.0, 0.2, 0.3)
    assert not dp.segment_band((0.0, 0.0), (10.0, 0.0), 15.0, 0.0, 0.3)    # past the segment's end: no barrier
    box = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert dp.in_ring_grid(box, 5.0, 5.0) and not dp.in_ring_grid(box, 15.0, 5.0)


def test_the_lap_cut_keeps_the_node_side():
    pts = [(float(i), 0.0, 0.0) for i in range(20)]                         # a straight lap along +E
    c_in, c_out = dp.lap_cut(pts, 5, 10), dp.lap_cut(pts, 15, 10)
    assert dp.side(c_in, 8.0, 0.0) > 0 and dp.side(c_in, 2.0, 0.0) < 0
    assert dp.side(c_out, 12.0, 0.0) > 0 and dp.side(c_out, 18.0, 0.0) < 0


def test_declarations_are_checked():
    ok = {"route": {"draft_pads": [{"id": "C14", "node": 10, "cuts": [5, 15]}]}}
    assert dp.declaration(ok, "C14")["node"] == 10
    for bad in ({"id": "X", "node": 3, "cuts": [5, 15]}, {"id": "X", "node": 10, "cuts": [5]},
                {"id": "X", "node": 10, "cuts": [5, 15], "sealed": [[[0, 0]]]}):
        with pytest.raises(SystemExit):
            dp.declarations({"route": {"draft_pads": [bad]}})
    assert dp.declarations({}) == []


def test_the_chain_carries_the_lm_pads_step():
    src = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")
    assert "draft_lm_pads() {" in src and "tools/lm_pads_blend.py" in src
    assert "draft_cutfill() {" in src and "tools/cutfill_blend.py" in src


def test_the_seam_offset_is_exact_on_the_row_linear_along_it_and_faded_in():
    c = {"p": (0.0, 0.0), "n": (0.0, 1.0)}                                  # a row along x, the pad on +y
    row = [(-4.0, 0.0, 10.10), (4.0, 0.0, 9.90)]
    prof = dp.seam_profile([(c, row)], lambda x, y: 10.0)                    # flat measured ground at 10.0
    assert dp.seam_offset(prof, -4.0, 0.0) == pytest.approx(0.10)
    assert dp.seam_offset(prof, 4.0, 0.0) == pytest.approx(-0.10)
    assert dp.seam_offset(prof, 0.0, 0.0) == pytest.approx(0.0)              # linear between the row's vertices
    assert dp.seam_offset(prof, -4.0, dp.SEAM_FADE_M / 2) == pytest.approx(0.05)
    assert dp.seam_offset(prof, -4.0, dp.SEAM_FADE_M + 1.0) == 0.0          # the measured ground beyond the fade
    steps = [dp.seam_offset(prof, -4.0, y * 1.0) for y in range(0, 14)]
    assert max(abs(b - a) for a, b in zip(steps, steps[1:])) < 0.06 * 0.1 / 0.06   # a smooth fade, no step


def test_the_row_splice_puts_the_row_into_the_ring_and_unties_it():
    # a square pad 0..10 x 0..10, the lap entering from the south (row along y = 0 from x = 3 to x = 7)
    ring = [(0.0, 0.0), (3.0, 0.0), (7.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    c = {"p": (5.0, 0.0), "n": (0.0, 1.0), "a": (-30.0, 0.0), "b": (30.0, 0.0), "vertex": 0}
    row = [(2.0, 0.0, 1.0), (5.0, 0.0, 1.1), (8.0, 0.0, 1.0)]
    cr = dp.row_cut(row, (5.0, 5.0))
    out = dp.splice_rows(ring, [(c, cr, row)])
    keys = {(round(q[0], 6), round(q[1], 6)) for q in out}
    assert {(2.0, 0.0), (5.0, 0.0), (8.0, 0.0)} <= keys                     # the row's vertices are the weld
    assert abs(dp.ring_area(out)) == pytest.approx(100.0, rel=1e-6)


def test_untie_cuts_a_folded_spur_out():
    bow = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (5.0, -1.0), (6.0, -1.0), (0.0, 4.0)]
    simple = dp.untie(bow)
    for i in range(len(simple)):
        for j in range(i + 2, len(simple)):
            if (j + 1) % len(simple) == i:
                continue
            assert dp._seg_x(simple[i], simple[(i + 1) % len(simple)], simple[j], simple[(j + 1) % len(simple)]) is None
