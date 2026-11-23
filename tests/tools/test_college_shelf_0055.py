"""Ledger 0055 round 2, the east shelf of College's split (Lake Murray). 0.20.5's first rehearsal (2026-11-23) stopped at
kn5_ground_check, "terrain has 202 double-sheet cells": the strip of ground added east of the northbound road kept
falling after it went under the hill, up to 19.4 m down inside it, out to its last column 19.5 m past the edge. The
shelf's column rule is pure (tracks/san-diego-lake-murray/source/college_r2/college_shelf.py) and held here; the scene
work is self-checked in Blender (college_ground_blend.py, with the gate's own lens) and measured through the chain's
prep. Plain ``test_*`` for tests/run_tests.py."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT / "tracks" / "san-diego-lake-murray" / "source" / "college_r2"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CS = _load("college_shelf_0055", R2 / "college_shelf.py")
GROUND = (R2 / "college_ground_blend.py").read_text(encoding="utf-8")
# the ground step's own numbers (read off its source below, so this file cannot drift from it)
HOLD_M, FILL_SLOPE, BURY_M, UNDER_M, CLEAR = 3.5, 0.5, 0.30, 0.10, 0.02
COLS_M = [0.0, 1.0, 2.0, 3.1, HOLD_M] + [HOLD_M + 1.0 * k for k in range(1, 17)]


def _fill(edge_y):
    return [edge_y - CLEAR - max(0.0, d - HOLD_M) * FILL_SLOPE for d in COLS_M]


def test_these_are_the_ground_steps_own_numbers():
    for frag in ("HOLD_M = 3.5 ", "FILL_SLOPE = 0.5 ", "BURY_M = 0.30 ", "UNDER_M = 0.10 ", "GROUND_CLEAR_M = 0.02 ",
                 "COLS_M = [0.0, 1.0, 2.0, 3.1, HOLD_M] + [HOLD_M + 1.0 * k for k in range(1, 17)]"):
        assert frag in GROUND, frag


def test_under_a_rising_hill_the_shelf_lies_the_bury_depth_under_it_and_no_deeper():
    """the cut east of College: the old ground starts 5 m under the raised edge and climbs 1 m per metre"""
    tgt = _fill(60.0)
    og = [55.0 + d for d in COLS_M]
    z, first = CS.columns(tgt, og, COLS_M, UNDER_M, BURY_M)
    assert first == 6 and COLS_M[first] == 5.5                                # the first column 0.10 m or more under the hill
    assert z[:first] == tgt[:first]                                           # in the open: the fill's own height
    assert z[first] == min(tgt[first], og[first] - BURY_M)
    for c in range(first + 1, len(COLS_M)):
        assert abs((og[c] - z[c]) - BURY_M) < 1e-9, (c, og[c] - z[c])         # past it: 0.30 m under the hill, every column
    # what 0.20.5's first rehearsal built: min(the falling fill, the hill less the bury depth) on every column
    was = [min(t, o - BURY_M) for t, o in zip(tgt, og)]
    assert og[-1] - was[-1] > 12.0                                            # the gate's double sheet (22.5 m here)
    assert max(o - h for o, h in zip(og, z)) < 2.0


def test_a_fill_that_never_meets_the_ground_and_a_place_with_no_ground():
    tgt = _fill(60.0)
    z, first = CS.columns(tgt, [40.0] * len(COLS_M), COLS_M, UNDER_M, BURY_M)   # the ground far below: a fill all the way
    assert first is None and z == tgt
    z, first = CS.columns(tgt, [None] * len(COLS_M), COLS_M, UNDER_M, BURY_M)
    assert first is None and z == tgt
    og = [70.0] * len(COLS_M)                                                 # a hill over the edge itself
    z, first = CS.columns(tgt, og, COLS_M, UNDER_M, BURY_M)
    assert first == 1 and z[0] == tgt[0]                                      # never at the edge's own column
    og[5] = None                                                              # a hole in the old ground past it
    z, first = CS.columns(tgt, og, COLS_M, UNDER_M, BURY_M)
    assert z[5] == tgt[5] and abs(z[6] - (70.0 - BURY_M)) < 1e-9


def test_a_row_ends_where_it_or_a_row_beside_it_goes_under():
    assert CS.row_ends([6, 7, None, 5, 5, 9, 4], 21) == [7, 20, 20, 20, 9, 9, 9]
    assert CS.row_ends([6], 21) == [6] and CS.row_ends([], 21) == []
    firsts = [5, 5, 8, 6, 6]
    ends = CS.row_ends(firsts, 21)
    assert ends == [5, 8, 8, 8, 6]
    for k in range(len(firsts) - 1):                                          # the faces between two rows reach both rows' columns
        assert min(ends[k], ends[k + 1]) >= max(firsts[k], firsts[k + 1])
    assert max(ends) == max(firsts)                                           # and nothing runs on past the furthest of them


def test_the_ground_step_builds_its_shelf_from_this_rule_and_holds_the_gates_own_lens():
    assert "college_shelf.columns(tgt, og, COLS_M, UNDER_M, BURY_M)" in GROUND
    assert "college_shelf.row_ends(firsts, len(COLS_M))" in GROUND
    assert "min(tgt, og - BURY_M) if (buried" not in GROUND                   # the line that sent the shelf down inside the hill
    assert "SHEET_SPREAD_M = 12.0 " in GROUND and "sp > SHEET_SPREAD_M and sh0.get(k_, 0.0) <= SHEET_SPREAD_M" in GROUND
    gate = (ROOT / "scripts" / "ac" / "kn5_ground_check.py").read_text(encoding="utf-8")
    assert "if v[1] - v[0] > 12.0]" in gate and "c = cells[(int(x // 2), int(z // 2))]" in gate   # the number and the cell it copies


def test_the_ground_step_leaves_one_sheet_of_ground_at_the_split():
    """the other three things 0.20.5's first rehearsal and the scratch runs after it asked of the step, held by their lines:
    old ground under the step's own surfaces goes; what is left at a seam sits just under the shelf; the ground under the
    split's own roads stands where the prep will pin it (the prep splits long edges BEFORE it pins)"""
    for frag in ('bmesh.ops.delete(bm, geom=drop, context="FACES")',
                 'if len(f.verts) != 3 or not all(x in cover for x in f.verts):',
                 'x.co.z = s_ - TUCK_M',
                 't_ = hit[0].z - GROUND_CLEAR_M',
                 'road_obs = [o for o in bpy.data.objects if o.type == "MESH" and (o.name == "ROAD" or o.name.upper().startswith("1ROAD"))]',
                 'new_z[near_low] = (plane - UNDER_BANK_M)[near_low]',
                 'new_z[i] = c_ if t_ is None else min(c_, t_ - UNDER_BANK_M)'):
        assert frag in GROUND, frag
    prep = 'road_tris = _world_tris(lambda n: n.startswith("1ROAD"))'                # the pin's own pavement set, which the step copies
    assert prep in (ROOT / "scripts" / "ac" / "build_kn5_loop.py").read_text(encoding="utf-8")
