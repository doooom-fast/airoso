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


def _deck_project(panel_h=None, panel_x=4.15) -> Path:
    """an 8 m road on a deck 3 m over the grass (every excursion crossing falls 3 m off its edge), optionally railed by
    the loop's I-8 bridge-rail kind: a double-sided VERTICAL panel (no plan area) ``panel_h`` tall at +/-``panel_x``"""
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False}))
    cl = [(0.0, 0.0, float(z)) for z in range(0, N_M + 1, 5)]
    widths = [W] * len(cl)
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": widths, "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}))
    groups = [("1ROAD_main", ribbon.road_ribbon(cl, widths)), ("1GRASS", _grass_plane(y=-3.0))]
    if panel_h is not None:
        for side in (1.0, -1.0):
            v, t = [], []
            for z in range(-5, N_M + 6, 5):                          # one panel per 5 m, as build_guardrails writes it
                v += [(side * panel_x, 0.0, float(z)), (side * panel_x, panel_h, float(z))]
                if z > -5:
                    q = len(v) - 4
                    t += [(q, q + 1, q + 3), (q, q + 3, q + 2), (q, q + 3, q + 1), (q, q + 2, q + 3)]   # both windings
            groups.append((f"1WALL_guard_{'L' if side > 0 else 'R'}", {"vertices": v, "tris": t, "uvs": [(0.0, 0.0)] * len(v)}))
    _write_obj(d / "data" / "track.obj", groups)
    return d


def test_a_vertical_panel_rail_guards_the_deck_edge_drop_v0181():
    """v0.18.1 (ledger 0057's Lake Murray Blvd I-8 deck): the loop's bridge rails are vertical panels with no plan area,
    which the downward top_at guard probe can never land on — every drop behind one read 'unguarded'. The crossing
    probe credits a 1WALL the car's path passes THROUGH; a rail too low to stop a car, or one standing beyond the drop,
    still guards nothing"""
    bare = drive_run(_deck_project())
    assert bare["excursion_drops"] > 0, bare["excursion_drops"]
    railed = drive_run(_deck_project(panel_h=0.95))
    assert railed["excursion_drops"] == 0, railed["worst_gated_excursions"]
    assert railed["excursion_far_ledges"] >= bare["excursion_drops"]        # still REPORTED, no longer gated
    low = drive_run(_deck_project(panel_h=0.3))
    assert low["excursion_drops"] == bare["excursion_drops"]
    beyond = drive_run(_deck_project(panel_h=0.95, panel_x=6.0))
    assert beyond["excursion_drops"] == bare["excursion_drops"]


def _plane_grid(fy, x0, x1, z0, z1, cell=5.0) -> dict:
    """a surface y = fy(x, z) sampled on a cell x cell grid (exact for a plane; creased along grid lines otherwise)"""
    xs, zs = [], []
    x = x0
    while x <= x1 + 1e-9:
        xs.append(x); x += cell
    z = z0
    while z <= z1 + 1e-9:
        zs.append(z); z += cell
    verts = [(x, fy(x, z), z) for z in zs for x in xs]
    nx = len(xs)
    tris = []
    for j in range(len(zs) - 1):
        for i in range(nx - 1):
            a = j * nx + i
            tris += [(a, a + 1, a + nx + 1), (a, a + nx + 1, a + nx)]
    return {"vertices": verts, "tris": tris, "uvs": [(0.0, 0.0)] * len(verts)}


def _vertex_hop_project(corner: bool, fy) -> Path:
    """a 9 m road (under the 9.5 m apron width) whose surface is ``fy``; ``corner``: a polygon turning 10 deg at each of
    eight 8 m vertices between two straights, so every fixed-offset wheel path hops 0.4-0.65 m at every vertex"""
    import math
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False}))
    cl = [(0.0, 0.0, float(z)) for z in range(0, 61, 5)]
    if corner:
        h = 0.0
        for _ in range(8):
            h += math.radians(10.0)
            x, _y, z = cl[-1]
            cl.append((x + 8.0 * math.sin(h), 0.0, z + 8.0 * math.cos(h)))
        for _ in range(12):
            x, _y, z = cl[-1]
            cl.append((x + 5.0 * math.sin(h), 0.0, z + 5.0 * math.cos(h)))
    else:
        cl = [(0.0, 0.0, float(z)) for z in range(0, N_M + 1, 5)]
    cl = [(x, fy(x, z), z) for x, _y, z in cl]
    xs, zs = [p[0] for p in cl], [p[2] for p in cl]
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": [9.0] * len(cl),
         "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}))
    box = (min(xs) - 20.0, max(xs) + 20.0, min(zs) - 20.0, max(zs) + 20.0)
    _write_obj(d / "data" / "track.obj", [("1ROAD_main", _plane_grid(fy, *box)),
                                          ("1GRASS", _plane_grid(lambda x, z: fy(x, z) - 0.05, *box, cell=10.0))])
    return d


def test_a_plane_round_a_polygon_corner_reads_vertex_bumps_not_gated_bumps_v0181():
    """v0.18.1 VERTEX BUMPS: a fixed-offset wheel path hops forward (outside) or creeps (inside) at every centreline
    vertex, so the 1 m second difference of a PLANE at 5 % reads grade x (hop - 1) there — gated bumps on the smoothest
    surface a road can have (the pre-v0.18.1 rule, measured here by disabling the re-measure). Re-measured on the
    path's own travel they are under 2.5 cm: reported as vertex_bumps, not gated. A real 5 cm crease is still a bump
    (both of its metres cover 1 m: the re-measure is the old measure), and a severe step is never re-measured."""
    from scripts.geometry import drive_test as dtm
    plane = lambda x, z: 0.05 * z
    new = drive_run(_vertex_hop_project(True, plane))
    keep = dtm._own_travel_step
    try:
        dtm._own_travel_step = lambda *a: None                   # the pre-v0.18.1 measure: every bump counts as read
        old = drive_run(_vertex_hop_project(True, plane))
    finally:
        dtm._own_travel_step = keep
    assert old["steps_per_km"] > 0, old
    assert new["steps_per_km"] == 0 and new["vertex_bumps"] > 0, new
    assert new["severe_steps"] == old["severe_steps"] and new["fold_bumps"] == old["fold_bumps"]
    assert all(r[3] <= dtm.STEP_BUMP_M for r in new["vertex_bumps_worst"])
    crease = drive_run(_vertex_hop_project(False, lambda x, z: 0.05 * max(0.0, z - 100.0)))
    assert crease["steps_per_km"] > 0 and crease["vertex_bumps"] == 0, crease
    # the helper itself: exactly the old second difference where both metres cover STEP_M; None under the floor
    assert dtm._own_travel_step(0.03, -0.01, 1.0, 1.0) == abs(0.03 - -0.01)
    assert dtm._own_travel_step(0.03, 0.01, 1.0, dtm.VERTEX_MIN_TRAVEL_M / 2) is None
    assert abs(dtm._own_travel_step(0.05 * 1.65, 0.05, 1.65, 1.0)) < 1e-12           # a plane across a hop
