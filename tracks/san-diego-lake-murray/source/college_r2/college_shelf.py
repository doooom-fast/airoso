"""College split, the east shelf's columns (pure: no Blender). college_ground_blend.py builds the shelf from these; the
rule is here so a test can hold it (tests/tools/test_college_shelf_0055.py).

The shelf is a strip of ground east of the northbound road's east edge: it holds the edge's height under and behind the
walk, then falls as a fill until it meets the ground that was there. Lake Murray 0.20.5's first rehearsal (2026-11-23)
stopped at kn5_ground_check, "terrain has 202 double-sheet cells": past the column where the shelf went under the old
ground, its height was min(the falling fill, the old ground less the bury depth), so under a hill that rises (the cut
east of College) it kept falling, up to 19.4 m down inside the hill, out to its last column 19.5 m past the edge: a
second sheet of ground under the first. Two rules now, both here:

  columns()   past the column where a row goes under the old ground it lies the bury depth under that ground, no deeper;
  row_ends()  a row ends at the column where it, or a row beside it, goes under: nothing runs on inside the hill."""


def columns(targets, old_ground, cols_m, under_m, bury_m):
    """One row. `targets`: the fill's own height at each column; `old_ground`: the old ground's height there (None: there
    is none); `cols_m`: metres past the edge. Returns (heights, first): `first` is the first column, past the edge
    itself, where the fill lies `under_m` or more under the old ground (None: it never does).
      before `first`              the fill's own height (in the open)
      at `first`                  the fill's own height, or `bury_m` under the old ground, whichever is lower
      past `first`                `bury_m` under the old ground (the fill's own height where there is no old ground)"""
    first, out = None, []
    for c, (tgt, og, d) in enumerate(zip(targets, old_ground, cols_m)):
        if og is not None and first is None and d > 0.0 and tgt <= og - under_m:
            first = c
        if first is None or og is None:
            z = tgt
        elif c == first:
            z = min(tgt, og - bury_m)
        else:
            z = og - bury_m
        out.append(z)
    return out, first


def row_ends(firsts, n_cols):
    """Per row, its last column: the furthest `first` of the row and the rows either side of it, so every face between
    two rows reaches both rows' own columns. A row that never goes under, or stands beside one, runs to the last column."""
    ends = []
    for k in range(len(firsts)):
        near = firsts[max(0, k - 1):k + 2]
        ends.append(n_cols - 1 if any(f is None for f in near) else max(near))
    return ends
