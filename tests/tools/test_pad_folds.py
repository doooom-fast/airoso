"""Ledger 0092 round 2: tools/pad_clip.lift_over_folds, the seat-pads step's raise of a rebuilt pad vertex over a fold of
the prepped ground (Milford 0.1.13's first full rehearsal stopped on "[seat-pads] FATAL: 1RUNOFF_apron_9: ground over 1
of its vertices": the vertex (-2.068, 444.711, 7.1748), ground hit 7.1165, 58.3 mm under it instead of 60)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import pad_clip as pc  # noqa: E402

LIFT = 0.06


def _self_check_fails(verts, top):
    """tools/seat_pads_blend.py's own self-check, as written"""
    return sum(1 for x, y, z in verts if (g := top(x, y, z)) is not None and g > z - LIFT + 1e-3)


def test_the_pc_vertex_is_raised_onto_the_higher_piece_and_then_passes():
    v = [(-2.068, 444.711, 7.1748), (0.0, 0.0, 5.06)]
    top = lambda x, y, z: 7.1165 if x < -1 else 5.0                    # the fold under the first; the second sits right
    assert _self_check_fails(v, top) == 1
    out, raised, worst = pc.lift_over_folds(v, top, LIFT)
    assert raised == 1 and abs(out[0][2] - (7.1165 + LIFT)) < 1e-12 and out[1] == v[1]
    assert abs(worst - 0.0017) < 1e-9 and _self_check_fails(out, top) == 0


def test_a_pad_that_passed_is_unchanged_and_real_ground_through_it_still_stops():
    v = [(1.0, 2.0, 10.06), (3.0, 4.0, 10.06), (5.0, 6.0, 10.06)]
    within = lambda x, y, z: 10.0009                                   # 0.9 mm over: the self-check passes it
    assert pc.lift_over_folds(v, within, LIFT) == (v, 0, 0.0)
    assert pc.lift_over_folds(v, lambda x, y, z: None, LIFT) == (v, 0, 0.0)
    through = lambda x, y, z: 10.02                                    # 20 mm over: ground through the pad, not a fold
    out, raised, _ = pc.lift_over_folds(v, through, LIFT)
    assert out == v and raised == 0 and _self_check_fails(out, through) == 3
    assert pc.FOLD_MAX_M == 0.01
