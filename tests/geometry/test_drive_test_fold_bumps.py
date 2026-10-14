"""drive_test FOLD BUMPS (v0.18.0, the gates lens): a fixed-offset wheel-path point whose offset lies past the turning
centre of a corner tighter than the lane runs BACKWARDS along the lap; the second difference it reads there is a
re-traced plan, not a wheel's step. A 2.5-6 cm "bump" over such a metre is reported (``fold_bumps``), not gated; a
severe step (> 6 cm) there still counts. Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

from scripts.geometry.drive_test import _advance, run as drive_run
from tests.geometry.test_drive_test import _write_obj

R = 3.0       # the U-turn's centre radius: the inner third path (8 m road: -2.67 +/- 0.75 m) lies past it
W = 8.0


def test_advance_is_the_share_of_the_centre_move_and_negative_past_the_turning_centre():
    assert _advance(None, (5.0, 5.0), (0.0, 0.0)) == 1.0                       # no previous sample
    assert _advance((0.0, 0.0, 0.0, 0.0), (1.0, 1.0), (0.0, 0.0)) == 1.0      # the centre did not move
    assert abs(_advance((2.0, 0.0, 0.0, 0.0), (2.0, 1.0), (0.0, 1.0)) - 1.0) < 1e-12   # a straight
    # round a circle of radius 10 about the origin, a small step: inside offsets advance by 1 - off / R
    th = 0.01
    for off, want in ((2.0, 0.8), (-2.0, 1.2), (10.0, 0.0), (13.0, -0.3)):
        r = 10.0 - off
        prev = (r, 0.0, 10.0, 0.0)
        a = _advance(prev, (r * math.cos(th), r * math.sin(th)), (10.0 * math.cos(th), 10.0 * math.sin(th)))
        assert abs(a - want) < 1e-3, (off, a)


def _grid(height, cell: float = 2.0) -> dict:
    """a planar sheet over the whole U-turn, in ``cell`` m squares (the drive surface hashes faces by their corners)"""
    xs = [-14.0 + cell * i for i in range(int(34.0 / cell) + 1)]
    zs = [-10.0 + cell * j for j in range(int(126.0 / cell) + 1)]
    verts = [(x, height(z), z) for z in zs for x in xs]
    nx = len(xs)
    tris = []
    for j in range(len(zs) - 1):
        for i in range(nx - 1):
            a = j * nx + i
            tris += [(a, a + nx + 1, a + 1), (a, a + nx, a + nx + 1)]
    return {"vertices": verts, "tris": tris, "uvs": [(0.0, 0.0)] * len(verts)}


def _uturn_project(grade: float) -> Path:
    """a 100 m straight north, a U-turn of radius R round (R, 100), 100 m back south; the pavement is one planar sheet
    rising ``grade`` to the north (so the folded inner path re-traces a slope), grass 2 m under it"""
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False}))
    cl = [(0.0, 0.0, float(z)) for z in range(0, 100)]
    n_arc = 10
    for k in range(n_arc + 1):
        a = math.pi * k / n_arc
        cl.append((R - R * math.cos(a), 0.0, 100.0 + R * math.sin(a)))
    cl += [(2 * R, 0.0, float(z)) for z in range(99, -1, -1)]
    cl = [(x, grade * z, z) for x, _y, z in cl]
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": [W] * len(cl),
         "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}))
    sheet = _grid(lambda z: grade * z)
    grass = _grid(lambda z: -10.0)
    _write_obj(d / "data" / "track.obj", [("1ROAD_main", sheet), ("1GRASS", grass)])
    return d


def test_a_fold_on_a_plane_is_reported_not_gated_and_a_flat_fold_reads_nothing():
    flat = drive_run(_uturn_project(0.0))
    assert flat["fold_bumps"] == 0 and flat["steps_per_km"] == 0 and flat["severe_steps"] == 0, flat
    # the same U-turn on a 2 % plane: the inner path past the turning centre reads 2.5-6 cm second differences that
    # no wheel feels (the surface is a plane) - they are fold bumps, and nothing else changed
    sloped = drive_run(_uturn_project(0.02))
    assert sloped["fold_bumps"] > 0, sloped
    assert sloped["severe_steps"] == 0 and sloped["soft_top_in_lane"] == 0, sloped


def test_drive_test_source_keeps_severe_steps_gated_on_folded_samples():
    src = (Path(__file__).resolve().parents[2] / "scripts" / "geometry" / "drive_test.py").read_text(encoding="utf-8")
    sev = src.index("if step > STEP_SEVERE_M:")
    fold = src.index("if folded:")
    bump = src.index("elif step > STEP_BUMP_M:")
    # the fold rule lives in the BUMP branch only: a severe step on a folded sample is still severe
    assert sev < bump < fold, (sev, bump, fold)
    assert '"fold_bumps": len(problems.get("fold_bumps", []))' in src
