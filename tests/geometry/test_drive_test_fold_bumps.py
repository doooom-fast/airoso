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


# --- FOLD SEVERE (opt-in, ledger 0054 P1 fix round) -----------------------------------------------------------------

def _fan_project(grade: float, opt_in: bool, width: float = 12.0) -> Path:
    """the U-turn on a steep plane with a WIDE road (its third paths at +-4 m lie past the 3 m turning centre and hop
    back ~0.5 m a metre), the turn declared a levelled fan in data/mouth_welds.json; `opt_in` sets
    track.config.json drive_test.fold_fan_severe"""
    d = _uturn_project(grade)
    cl = json.loads((d / "data" / "centerline.local.json").read_text())
    cl["widths_m"] = [width] * len(cl["points_xyz_m"])
    (d / "data" / "centerline.local.json").write_text(json.dumps(cl))
    sheet = _grid(lambda z: grade * z, cell=1.0)
    grass = _grid(lambda z: -10.0)
    _write_obj(d / "data" / "track.obj", [("1ROAD_main", sheet), ("1GRASS", grass)])
    n = len(cl["points_xyz_m"])
    (d / "data" / "mouth_welds.json").write_text(json.dumps({"folds": {"MAINLINE": {
        "cuts": [["road", 2, 100, 109]], "levelled": [{"line": ["road", 2], "k": 100, "l": 109}],
        "level_rows": 8, "rows": n}}}))
    cfg = {"slug": "t", "mirror_x": False}
    if opt_in:
        cfg["drive_test"] = {"fold_fan_severe": "verify_fold_fans"}
    (d / "track.config.json").write_text(json.dumps(cfg))
    return d


def test_fold_severe_is_opt_in_and_only_hands_folded_fan_samples_to_verify_fold_fans():
    off = drive_run(_fan_project(0.08, opt_in=False))
    on = drive_run(_fan_project(0.08, opt_in=True))
    # without the key: the plane's re-traced hops read as severe steps, as on v0.18.0, and no new key is written
    assert off["severe_steps"] > 0, off
    assert "fold_severe" not in off and "fold_severe" not in off["worst"]
    # with it: the ones on a folded sample (the inside paths past the 3 m turning centre) inside the levelled fan ->
    # fold_severe, judged elsewhere; the outside paths' severe readings (forward samples) stay severe, unchanged
    assert on["fold_severe"] > 0 and on["severe_steps"] + on["fold_severe"] == off["severe_steps"], (on, off)
    moved = {tuple(r) for r in on["worst"]["fold_severe"]}
    kept = {tuple(r) for r in on["worst"]["severe_all"]}
    assert kept | moved == {tuple(r) for r in off["worst"]["severe_all"]} and not (kept & moved)
    assert all(r[1] < 0 for r in moved)                     # the inside of this right-hand U-turn
    assert on["fold_severe_judge"].startswith("tools/verify_fold_fans.py")
    for k in ("soft_top_in_lane", "steps_per_km", "fold_bumps", "kinks_per_km"):
        assert on[k] == off[k], k


def test_fold_severe_never_covers_a_forward_step_or_one_outside_a_fan():
    # a real 0.3 m riser across the straight before the U-turn (z 50): forward samples, outside the fan zone -> severe
    # with or without the key
    def riser(grade_unused=None):
        return lambda z: 0.3 if z >= 50.0 else 0.0
    for opt_in in (False, True):
        d = _fan_project(0.0, opt_in=opt_in)
        sheet = _grid(riser(), cell=1.0)
        _write_obj(d / "data" / "track.obj", [("1ROAD_main", sheet), ("1GRASS", _grid(lambda z: -10.0))])
        r = drive_run(d)
        assert r["severe_steps"] > 0, (opt_in, r)
        assert r.get("fold_severe", 0) == 0
