"""A track's driving direction is a contract (ledger 0026), so the AI writer measures it instead
of trusting the order the source data arrived in. These pin the two rulers apart: a closed loop is
judged by the grid→timing chord, a point-to-point stage by where the grid sits along the line —
because on a 25 km stage the timing line is the *finish*, 18 km away, and the chord means nothing.
"""

import math

from scripts.ac.write_ai_line import grid_alignment

# A unit square loop, counter-clockwise in XZ, sampled every 1 m.
_LOOP = ([[float(x), 0.0, 0.0] for x in range(0, 40)]
         + [[40.0, 0.0, float(z)] for z in range(0, 40)]
         + [[float(40 - x), 0.0, 40.0] for x in range(0, 40)]
         + [[0.0, 0.0, float(40 - z)] for z in range(0, 40)])

# A straight 100 m stage running +x.
_STAGE = [[float(x), 0.0, 0.0] for x in range(0, 101)]


def _loop_dummies(grid_x: float, timing_x: float) -> dict:
    """Grid on the +x straight; timing gate across the road `timing_x` metres along it."""
    return {"AC_START_0": [grid_x, 0.0, 0.0],
            "AC_TIME_0_L": [timing_x, 0.0, -4.0],
            "AC_TIME_0_R": [timing_x, 0.0, 4.0]}


def test_loop_agreeing_grid_scores_positive():
    dot, how = grid_alignment(_LOOP, _loop_dummies(5.0, 35.0), closed=True)
    assert dot > 0.99, dot
    assert "chord" in how


def test_loop_opposed_grid_scores_negative():
    """The IMI case: the grid faces back down the line the spline runs forward along."""
    dot, _ = grid_alignment(_LOOP, _loop_dummies(35.0, 5.0), closed=True)
    assert dot < -0.99, dot


def test_loop_refuses_a_timing_line_too_far_to_be_a_heading():
    """Across a curve a long chord is not a local heading — refuse rather than sound confident."""
    far = {"AC_START_0": [0.0, 0.0, 0.0],
           "AC_TIME_0_L": [0.0, 0.0, 396.0], "AC_TIME_0_R": [8.0, 0.0, 396.0]}
    assert grid_alignment(_LOOP, far, closed=True) is None


def test_stage_uses_position_along_the_line_not_the_finish_gate():
    """under-the-dragon: finish gate 18 km away scored +0.11; position along the stage is +1.00."""
    dummies = {"AC_START_0": [0.0, 0.0, 0.0],
               "AC_TIME_0_L": [100.0, 0.0, -4.0], "AC_TIME_0_R": [100.0, 0.0, 4.0]}
    dot, how = grid_alignment(_STAGE, dummies, closed=False)
    assert math.isclose(dot, 1.0, abs_tol=1e-6), dot
    assert "along the stage" in how


def test_stage_gridded_at_the_far_end_runs_reverse():
    dummies = {"AC_START_0": [100.0, 0.0, 0.0]}
    dot, _ = grid_alignment(_STAGE, dummies, closed=False)
    assert math.isclose(dot, -1.0, abs_tol=1e-6), dot


def test_no_start_dummy_is_unmeasurable():
    assert grid_alignment(_LOOP, {"AC_TIME_0_L": [0, 0, 0]}, closed=True) is None
