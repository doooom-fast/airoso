"""Ledger 0070 D1 — tools/plan_streetlights.py, the lamp post plan for an ENGINE-DRAFT track (Sand Creek): the loop's
walk (spacing, alternating sides, the head ARM_M road-ward at HEAD_OVER_GROUND_M over the ground), the pole footprint
off every road surface, >= 0.5 m + mast radius from every wall, off a pad, none at a deck span or a cut wall; slide,
then the other side, then skip with the reason; the record author_lamps_blend.py's base rule reads back; the opt-in."""
from __future__ import annotations

import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("plan_streetlights", ROOT / "tools" / "plan_streetlights.py")
PS = importlib.util.module_from_spec(_spec)
sys.modules["plan_streetlights"] = PS
_spec.loader.exec_module(PS)

W = 10.0          # the lap's pavement width
L = 600.0         # a straight lap piece along +x


def _quad(x0, x1, z0, z1, y=0.0):
    a, b, c, d = (x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)
    return [(a, b, c), (a, c, d)]


def _world(walls=(), extra_road=(), ground_y=0.0, road_y=0.0, shoulder=2.5):
    """a straight 10 m road along +x (z in [-5, 5]) + a shoulder sheet each side, ground everywhere"""
    road = []
    for x in range(-50, int(L) + 50, 10):
        road += _quad(x, x + 10, -W / 2 - shoulder, W / 2 + shoulder, road_y)
    for q in extra_road:
        road += _quad(*q, y=road_y)
    ground = []
    for x in range(-50, int(L) + 50, 10):
        for z in range(-60, 60, 10):
            ground += _quad(x, x + 10, z, z + 10, ground_y)
    wall = []
    for (x0, x1, z0, z1) in walls:
        wall += _quad(x0, x1, z0, z1, 0.5)
    return PS.Surfaces({"road": road, "wall": wall, "ground": ground})


def _lap():
    n = int(L / 3.0) + 1
    return PS.Lap([(i * 3.0, 0.0, 0.0) for i in range(n)], [W] * n)


def test_walk_spacing_sides_and_the_record():
    res = PS.plan(_lap(), _world())
    lamps = res["lamps"]
    assert len(lamps) >= 9, len(lamps)
    assert not res["skipped"], res["skipped"]
    # every SPACING_M from START_M, sides alternating (L = +z, the left of +x travel)
    assert [l["station_m"] for l in lamps[:3]] == [55.0, 110.0, 165.0]
    assert [l["side"] for l in lamps[:4]] == ["L", "R", "L", "R"]
    for l in lamps:
        bx, bz = l["base_xz"]
        hx, hy, hz = l["head"]
        # the post SIDE_OFF_M past the pavement edge; the head ARM_M road-ward at HEAD_OVER_GROUND_M over the ground
        assert abs(abs(bz) - (W / 2 + PS.SIDE_OFF_M)) < 1e-6
        assert abs(math.hypot(hx - bx, hz - bz) - PS.ARM_M) < 1e-3
        assert abs(hz) < abs(bz) - PS.ARM_M + 0.05        # road-ward (toward the nearest 3 m vertex)
        assert abs(hy - PS.HEAD_OVER_GROUND_M) < 1e-6
        # author_lamps_blend's base rule (road-ward = head -> nearest centreline vertex, base ARM_M behind) finds it
        lap = _lap()
        c = lap.pts[lap.nearest_vertex(hx, hz)]
        dx, dz = c[0] - hx, c[2] - hz
        Ld = math.hypot(dx, dz)
        assert abs(hx - dx / Ld * PS.ARM_M - bx) < 0.02 and abs(hz - dz / Ld * PS.ARM_M - bz) < 0.02
    # no two posts within MIN_GAP_M
    for i, a in enumerate(lamps):
        for b in lamps[i + 1:]:
            assert math.dist(a["base_xz"], b["base_xz"]) >= PS.MIN_GAP_M


def test_no_footprint_on_a_road_a_side_street_pushes_the_post_along():
    # a 10 m side street on the left at x 50..60 covers the first station's spot: the post slides past it
    res = PS.plan(_lap(), _world(extra_road=[(50.0, 60.0, 5.0, 60.0)]))
    first = res["lamps"][0]
    assert first["side"] == "L"
    bx, _bz = first["base_xz"]
    assert bx < 50.0 - PS.MAST_RADIUS_M - PS.ROAD_SETBACK_M or bx > 60.0 + PS.MAST_RADIUS_M + PS.ROAD_SETBACK_M, bx


def test_the_shoulder_sheet_is_road_too():
    # a 4 m shoulder sheet reaches past SIDE_OFF_M's assumption: every candidate is on it -> skipped, reason "road"
    res = PS.plan(_lap(), _world(shoulder=5.0))
    assert not res["lamps"]
    assert res["skipped"] and all("road" in s["why"] for s in res["skipped"])


def test_wall_clearance():
    # a barrier line 0.3 m behind where the left posts stand: too close (< 0.5 m + mast) -> the post goes right
    zb = W / 2 + PS.SIDE_OFF_M
    res = PS.plan(_lap(), _world(walls=[(0.0, L, zb + 0.3, zb + 0.9)]))
    for l in res["lamps"]:
        bx, bz = l["base_xz"]
        if bz > 0:
            assert zb + 0.3 - bz >= PS.WALL_CLEAR_M + PS.MAST_RADIUS_M - 1e-9
    assert res["lamps"][0]["side"] == "R"
    # a wall standing 2 m behind them is fine
    res2 = PS.plan(_lap(), _world(walls=[(0.0, L, zb + 2.0, zb + 2.6)]))
    assert res2["lamps"][0]["side"] == "L"


def test_deck_spans_and_cut_walls_get_no_post():
    res = PS.plan(_lap(), _world(), spans=[(100.0, 200.0)])
    for l in res["lamps"]:
        assert not (100.0 - PS.BRIDGE_PAD_M <= l["station_m"] <= 200.0 + PS.BRIDGE_PAD_M), l
    assert any(s["why"] == ["deck"] for s in res["skipped"])
    # the road 7 m over the ground under every post (an embankment / deck): nothing stands
    res2 = PS.plan(_lap(), _world(ground_y=-7.0))
    assert not res2["lamps"] and all("cut_wall" in s["why"] for s in res2["skipped"])


def test_pads_are_kept_clear():
    pad = [(40.0, 5.0), (70.0, 5.0), (70.0, 30.0), (40.0, 30.0)]
    res = PS.plan(_lap(), _world(), pads=[("P1", pad)])
    for l in res["lamps"]:
        x, z = l["base_xz"]
        assert not PS._in_poly(pad, x, z) and PS._poly_dist(pad, x, z) >= PS.PAD_CLEAR_M


def test_obj_reader_and_the_opt_in():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p / "data").mkdir()
        n = int(L / 3.0) + 1
        pts = [[i * 3.0, 0.0, 0.0] for i in range(n)]
        (p / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": pts, "widths_m": [W] * n}))
        lines, vi = [], 1
        for g, (x0, x1, z0, z1, y) in (("1ROAD_main", (-10, L + 10, -7.5, 7.5, 0.0)),
                                       ("1GRASS_a", (-10, L + 10, -60, 60, 0.0)),
                                       ("1WALL_barrier_a", (0, 20, 40, 41, 0.5))):
            lines.append(f"g {g}")
            for x, z in ((x0, z0), (x1, z0), (x1, z1), (x0, z1)):
                lines.append(f"v {x} {y} {z}")
            lines.append(f"f {vi} {vi + 1} {vi + 2} {vi + 3}")
            vi += 4
        (p / "data" / "track.obj").write_text("\n".join(lines) + "\n")
        cfg = {"scenery": {}}
        (p / "track.config.json").write_text(json.dumps(cfg))
        assert PS.run(p) is None and not (p / "data" / "lights.local.json").exists()     # not opted in: nothing
        cfg["scenery"]["streetlights"] = {"model": "led_cobra", "arms": 2, "planner": "engine_draft"}
        (p / "track.config.json").write_text(json.dumps(cfg))
        res = PS.run(p)
        out = json.loads((p / "data" / "lights.local.json").read_text())
        assert out["lampheads"] == [l["head"] for l in res["lamps"]] and len(out["lampheads"]) >= 9
        assert out["surfaces_read"] == {"road": 2, "wall": 2, "ground": 2}
