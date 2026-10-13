"""Smoke tests for the virtual drive test gate (scripts/geometry/drive_test.run).

Builds a tiny synthetic project — a straight, flat 200 m road ribbon seated on a grass plane —
and drives it: a clean build must PASS; a wall dropped across the lane must be reported as an
obstruction and FAIL the gate. Plain ``test_*`` for tests/run_tests.py (no pytest fixtures).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.geometry import ribbon
from scripts.geometry.drive_test import run as drive_run

W = 8.0
N_M = 200


def _write_obj(path: Path, groups: list[tuple[str, dict]]) -> None:
    lines: list[str] = []
    base = 1
    for name, mesh in groups:
        lines.append(f"o {name}")
        for x, y, z in mesh["vertices"]:
            lines.append(f"v {x:.4f} {y:.4f} {z:.4f}")
        for u, v in mesh.get("uvs") or [(0.0, 0.0)] * len(mesh["vertices"]):
            lines.append(f"vt {u:.4f} {v:.4f}")
        for a, b, c in mesh["tris"]:
            lines.append(f"f {base+a}/{base+a} {base+b}/{base+b} {base+c}/{base+c}")
        base += len(mesh["vertices"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _grass_plane(y: float = -0.02, half: float = 40.0, zmax: float = float(N_M), cell: float = 10.0) -> dict:
    xs, zs = [], []
    x = -half
    while x <= half + 1e-9:
        xs.append(x); x += cell
    z = -20.0
    while z <= zmax + 20.0 + 1e-9:
        zs.append(z); z += cell
    verts = [(x, y, z) for z in zs for x in xs]
    nx = len(xs)
    tris = []
    for j in range(len(zs) - 1):
        for i in range(nx - 1):
            a = j * nx + i
            tris.append((a, a + 1, a + nx + 1))
            tris.append((a, a + nx + 1, a + nx))
    return {"vertices": verts, "tris": tris,
            "uvs": [(0.0, 0.0)] * len(verts)}


def _project(with_wall_across_lane: bool = False) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False}))
    cl = [(0.0, 0.0, float(z)) for z in range(0, N_M + 1, 5)]
    widths = [W] * len(cl)
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": widths,
         "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}))
    road = ribbon.road_ribbon(cl, widths)
    groups = [("1ROAD_main", road), ("1GRASS", _grass_plane())]
    if with_wall_across_lane:
        wall = {"vertices": [(-2.0, 0.0, 100.0), (2.0, 0.0, 100.0),
                             (2.0, 1.2, 100.0), (-2.0, 1.2, 100.0)],
                "tris": [(0, 1, 2), (0, 2, 3)],
                "uvs": [(0.0, 0.0)] * 4}
        groups.append(("BARRIER_block", wall))
    _write_obj(d / "data" / "track.obj", groups)
    return d


def test_clean_straight_road_passes():
    r = drive_run(_project())
    assert r["fail"] is False
    assert r["soft_top_in_lane"] == 0
    assert r["obstruction_stations"] == 0
    assert r["daylight_gaps"] == 0


def test_wall_across_the_lane_is_an_obstruction_and_fails():
    r = drive_run(_project(with_wall_across_lane=True))
    assert r["obstruction_stations"] > 0
    assert any(k.startswith("BARRIER") for k in r["obstruction_by_mesh"]), r["obstruction_by_mesh"]
    assert r["fail"] is True


def _apron_project(fan_rows=None, levelled=True, pad_h=0.10) -> Path:
    """a 12 m straight on a 1 m row pitch whose right edge steps up 0.12 m at z = 100: at offset -5 the wheel meets
    a 0.10 m rise inside one metre — on pavement this wide that is filed as an exempt apron step, unless a ledger-0050
    fold fan (data/mouth_welds.json) covers it"""
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False}))
    cl = [(0.0, 0.0, float(z)) for z in range(0, N_M + 1)]
    widths = [12.0] * len(cl)
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": widths, "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}))
    road = ribbon.road_ribbon(cl, widths)
    # the outer 2.4 m of one side stands 0.10 m proud from z = 100 on: only paths more than 3.5 m out cross its edge
    pv, pt = [], []
    for z in range(100, N_M + 1):
        pv += [(-6.0, pad_h, float(z)), (-3.6, pad_h, float(z))]
        if z > 100:
            a = len(pv) - 4
            pt += [(a, a + 3, a + 1), (a, a + 2, a + 3)]
    pad = {"vertices": pv, "tris": pt, "uvs": [(0.0, 0.0)] * len(pv)}
    _write_obj(d / "data" / "track.obj", [("1ROAD_main", road), ("1ROAD_pad", pad), ("1GRASS", _grass_plane(y=-0.05))])
    if fan_rows is not None:
        k, l = fan_rows
        fm = {"cuts": [["road", 2, k, l]], "rows": len(cl), "level_rows": 8}
        if levelled:
            fm["levelled"] = [{"line": ["road", 2], "k": k, "l": l, "X": [-6.0, 0.1, float(k)], "y_k": 0.1, "y_l": 0.1}]
        (d / "data" / "mouth_welds.json").write_text(json.dumps({"folds": {"MAINLINE": fm}}))
    return d


def test_fold_fan_zones_turn_the_apron_exemption_off_ledger_0050():
    """ledger 0050: the 0.24 m Navajo / Jackson riser was an exempt street 'apron step'. Inside a levelled fold fan
    (k - 8 .. l + 1 + 8, half-width + 0.5 m) the step is severe; the same step outside any fan is still an apron
    step; a weld file with no road cut (and no file: every other track) leaves the result exactly as it was"""
    base = drive_run(_apron_project())
    assert base["severe_steps"] == 0 and base["apron_steps"] > 0, base
    inside = drive_run(_apron_project((95, 98)))
    assert inside["severe_steps"] > 0 and inside["apron_steps"] == 0, inside
    outside = drive_run(_apron_project((150, 152)))
    assert outside["severe_steps"] == 0 and outside["apron_steps"] == base["apron_steps"], outside
    d = _apron_project()
    (d / "data" / "mouth_welds.json").write_text(json.dumps({"folds": {"MAINLINE": {"cuts": []}}}))
    same = drive_run(d)
    strip = lambda r: {k: v for k, v in r.items() if k not in ("obj",)}
    assert strip(same) == strip(base)
    # a 4 cm rise (a bump, not a step) keeps the apron rule inside a fan: fixed-station paths round a tight corner
    # read 2.5-4.7 cm from their own spacing; verify_fold_fans judges sub-6 cm on real wheel paths
    b0 = drive_run(_apron_project(pad_h=0.04))
    b1 = drive_run(_apron_project((95, 98), pad_h=0.04))
    assert b0["steps_per_km"] == b1["steps_per_km"] and b1["severe_steps"] == 0, (b0, b1)
    assert b0["severe_steps"] == 0 and b0["apron_steps"] == 0


def test_fold_fan_discs_refuse_a_row_count_mismatch():
    from scripts.geometry.drive_test import fold_fan_discs
    pts = [(0.0, 0.0, float(z)) for z in range(50)]
    w = [12.0] * 50
    welds = {"folds": {"MAINLINE": {"cuts": [["road", 2, 20, 22]], "rows": 49, "level_rows": 2}}}
    try:
        fold_fan_discs(welds, pts, w)
    except SystemExit as e:
        assert "rows" in str(e)
    else:
        raise AssertionError("a weld indexing another row count was accepted")
    welds["folds"]["MAINLINE"]["rows"] = 50
    discs = fold_fan_discs(welds, pts, w)
    assert [round(d[1]) for d in discs] == list(range(18, 26)) and all(d[3] == 6.5 for d in discs)
