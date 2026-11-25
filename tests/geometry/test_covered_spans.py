"""A road under a roof (Denver Grand Prix PLAN 4 item 1; ledger 0096): track.config.json capture.covered_spans, the
bridge exemption the other way up, in scripts/geometry/covered_spans.py, drive_test and kn5_ground_check.

The world: the 200 m straight of tests/geometry/test_drive_test.py (8 m wide, on a grass plane), with a roof 5 m over
stations 60-140 and, by case, a parapet on the roof, lights hung from its soffit, a second pavement on top of it.

What these prove:
  * with no declaration nothing is set aside and both gates read exactly what they read before (the same reports, key
    for key, as a run with the zone code never reached);
  * a roof nobody declared turns the gates red in three real ways (a parapet as floating furniture, soffit lights as
    lamp heads without a mast, a pavement on the roof as a road floating over the ground) and leaves the road under a
    grass-named roof unjudged; declared, each is read right;
  * the declaration covers only its own stations, only what is min_clear_m above the road, and never what rises from
    the road (a wall across the lane under the roof is still an obstruction);
  * a declaration owes its clearance: a roof built under clear_m - 0.5 m fails drive_test.
Plain ``test_*`` for tests/run_tests.py.
"""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path

from tests.geometry.test_drive_test import _grass_plane, _plane_grid, _write_obj

from scripts.ac import kn5_ground_check as kg
from scripts.ac.kn5_write import build
from scripts.geometry import covered_spans as cs
from scripts.geometry import ribbon
from scripts.geometry.drive_test import run as drive_run

SPAN = {"name": "the roof", "center_m": 100.0, "len_m": 80.0, "clear_m": 5.0}


def _box(verts, tris, x0, x1, y0, y1, z0, z1):
    b = len(verts)
    for y in (y0, y1):
        for z in (z0, z1):
            for x in (x0, x1):
                verts.append((x, y, z))
    for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        a, b2, c, d = (b + k for k in q)
        tris.extend([(a, b2, c), (a, c, d)])


def _mesh(boxes):
    v, t = [], []
    for bx in boxes:
        _box(v, t, *bx)
    return {"vertices": v, "tris": t, "uvs": [(0.0, 0.0)] * len(v)}


def _project(roof=None, declare=None, roof_y=5.0, parapet=False, lights=False, wall=False) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    cfg = {"slug": "t", "mirror_x": False}
    if declare:
        cfg["capture"] = {"covered_spans": [dict(declare)]}
    (d / "track.config.json").write_text(json.dumps(cfg))
    cl = [(0.0, 0.0, float(z)) for z in range(0, 201, 5)]
    widths = [8.0] * len(cl)
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": widths, "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}))
    (d / "data" / "finished_centerline.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": widths}))
    groups = [("1ROAD_main", ribbon.road_ribbon(cl, widths)), ("1GRASS", _grass_plane())]
    if roof:
        groups.append((roof, _plane_grid(lambda x, z: roof_y, -10.0, 10.0, 60.0, 140.0)))
    if parapet:
        groups.append(("1WALL_parapet", _mesh([(3.0, 3.3, roof_y, roof_y + 1.0, 70.0, 130.0)])))
    if lights:
        groups.append(("LIGHTS_soffit", _mesh([(-0.3, 0.3, roof_y - 0.25, roof_y - 0.05, z - 0.3, z + 0.3)
                                               for z in range(65, 140, 10)])))
        groups.append(("LIGHTPOST_0", _mesh([(9.0, 9.2, 0.0, 9.0, 20.0, 20.2)])))       # a street lamp outside the span
    if wall:
        groups.append(("BARRIER_block", {"vertices": [(-2.0, 0.0, 100.0), (2.0, 0.0, 100.0), (2.0, 1.2, 100.0),
                                                      (-2.0, 1.2, 100.0)], "tris": [(0, 1, 2), (0, 2, 3)],
                                         "uvs": [(0.0, 0.0)] * 4}))
    _write_obj(d / "data" / "track.obj", groups)
    return d


def _quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def _drive(d):
    return _quiet(drive_run, d)


def _ground(d):
    _quiet(build, d)
    st: dict = {}
    r = _quiet(kg.check, d, stats=st)
    return r, st


# --- the declaration ------------------------------------------------------------------------------------------
def test_no_declaration_builds_no_zone():
    assert cs.declared({}) == [] and cs.declared({"capture": {"bridges": [{"center_m": 1, "len_m": 2}]}}) == []
    assert cs.zones_for({"slug": "t"}, [(0, 0, 0), (0, 0, 10)], [8.0, 8.0]) is None


def test_a_span_is_checked_as_written():
    for bad in ({"center_m": 10.0}, {"center_m": 10.0, "len_m": 0.0},
                {"center_m": 10.0, "len_m": 5.0, "min_clear_m": 1.5},          # under the strike ceiling's margin
                {"center_m": 10.0, "len_m": 5.0, "clear_m": 2.0}):             # a clearance under min_clear_m
        try:
            cs.declared({"capture": {"covered_spans": [bad]}})
        except SystemExit:
            continue
        raise AssertionError(f"accepted {bad}")
    (sp,) = cs.declared({"capture": {"covered_spans": [SPAN]}})
    assert sp["min_clear_m"] == cs.MIN_CLEAR_M == 2.5 and sp["reach_m"] == cs.REACH_M and sp["clear_m"] == 5.0
    assert cs.MIN_CLEAR_FLOOR_M > cs.STRIKE_CEILING_M == 1.8


def test_the_footprint_has_square_ends_the_roads_width_and_its_reach():
    pts = [(0.0, 0.0, float(z)) for z in range(0, 201, 5)]
    z = cs.zones_for({"capture": {"covered_spans": [SPAN]}}, pts, [8.0] * len(pts))
    assert z.under(0.0, 100.0)[:3] == (0.0, 0.0, 4.0)
    assert z.under(0.0, 60.0) is not None and z.under(0.0, 140.0) is not None      # its two stations
    assert z.under(0.0, 59.9) is None and z.under(0.0, 140.1) is None              # a decimetre beyond either end
    assert z.under(9.9, 100.0) is not None and z.under(10.1, 100.0) is None        # half-width 4 + reach 6
    # overhead = min_clear_m or more above the road THERE
    assert z.point_overhead(0.0, 2.5, 100.0) and not z.point_overhead(0.0, 2.4, 100.0)
    assert not z.point_overhead(0.0, 9.0, 150.0)                                   # high, and outside the span
    # a wall panel rising from the road is not the roof, whatever its top reaches
    assert not z.tri_overhead((4.0, 0.0, 100.0), (4.0, 5.0, 100.0), (4.0, 5.0, 101.0))
    assert z.tri_overhead((4.0, 5.0, 100.0), (-4.0, 5.0, 100.0), (4.0, 5.0, 101.0))


def test_a_span_across_the_seam_of_a_closed_lap_wraps():
    """LAWS L13: closed is derived (first point repeated), and stations wrap as well as indices"""
    sq = [(0.0, 0.0, 0.0), (100.0, 0.0, 0.0), (100.0, 0.0, 100.0), (0.0, 0.0, 100.0), (0.0, 0.0, 0.0)]
    cfg = {"capture": {"covered_spans": [{"center_m": 0.0, "len_m": 40.0}]}}        # 20 m either side of the line
    z = cs.zones_for(cfg, sq, [8.0] * 5)
    assert z.closed and z.lap == 400.0
    assert z.under(10.0, 0.0) is not None and z.under(0.0, 15.0) is not None        # after the seam, and before it
    assert z.under(30.0, 0.0) is None and z.under(0.0, 30.0) is None
    op = cs.zones_for(cfg, sq[:-1], [8.0] * 4)                                      # the same road, open: no wrap
    assert not op.closed and op.under(10.0, 0.0) is not None and op.under(0.0, 15.0) is None


# --- nothing declared: nothing changes ------------------------------------------------------------------------
def test_without_a_declaration_no_zone_is_ever_built_and_no_report_carries_a_covered_key():
    """a roof, a parapet and soffit lights, and no declaration: both gates run to their verdict with the zone class
    made unusable, so nothing in them can have read a zone; the reports carry no covered key. (The before / after
    comparison against main's own code is in ledger 0096's note: it cannot be a unit test.)"""
    d = _project(roof="BUILDING_cc", parapet=True, lights=True)
    real = cs.Zones.__init__

    def boom(self, *_a, **_k):
        raise AssertionError("a track with no covered span must not build a zone")
    cs.Zones.__init__ = boom
    try:
        r = _drive(d)
        g, st = _ground(d)
    finally:
        cs.Zones.__init__ = real
    assert "covered_spans" not in r and "covered_low_overhead" not in r and "covered_spans" not in st
    assert r["floating_furniture"] > 0 and st["lamp_orphans"] > 0          # and they read the roof as they always did


# --- a roof nobody declared, and the same roof declared ---------------------------------------------------------
def test_a_parapet_on_the_roof_is_floating_furniture_until_the_span_is_declared():
    bare = _drive(_project(roof="BUILDING_cc", parapet=True))
    assert bare["fail"] is True and bare["floating_furniture"] > 0
    r = _drive(_project(roof="BUILDING_cc", parapet=True, declare=SPAN))
    assert r["fail"] is False and r["floating_furniture"] == 0
    (row,) = r["covered_spans"]
    assert row["overhead_set_aside"] > 0 and row["lowest_overhead_m"] == 5.0 and row["under_declared_clearance"] == 0
    g, st = _ground(_project(roof="BUILDING_cc", parapet=True))
    assert g["fail"] is True and any("walls" in w for w in g["reasons"])
    g, st = _ground(_project(roof="BUILDING_cc", parapet=True, declare=SPAN))
    assert g["fail"] is False, g["reasons"]


def test_lights_hung_from_the_soffit_are_orphan_heads_until_the_span_is_declared():
    g, st = _ground(_project(roof="BUILDING_cc", lights=True))
    assert g["fail"] is True and st["lamp_orphans"] > 0
    g, st = _ground(_project(roof="BUILDING_cc", lights=True, declare=SPAN))
    assert g["fail"] is False, g["reasons"]
    assert st["seating"]["lampposts"]["objects"] == 1          # the street lamp outside the span is still judged


def test_a_pavement_on_the_roof_is_a_floating_road_until_the_span_is_declared():
    g, st = _ground(_project(roof="1ROAD_upper"))
    assert g["fail"] is True and any("floating over ground" in w for w in g["reasons"])
    g, st = _ground(_project(roof="1ROAD_upper", declare=SPAN))
    assert g["fail"] is False and st["road_over_ground"]["over"] == 0


def test_the_road_under_a_grass_named_roof_is_judged_once_declared():
    """undeclared, the road-over-ground lens finds the roof's grass above the deck and skips those samples"""
    _g, plain = _ground(_project())
    _g, bare = _ground(_project(roof="1GRASS_roof"))
    _g, decl = _ground(_project(roof="1GRASS_roof", declare=SPAN))
    assert bare["road_over_ground"]["samples"] < plain["road_over_ground"]["samples"]
    assert decl["road_over_ground"] == plain["road_over_ground"]


# --- the declaration's limits -----------------------------------------------------------------------------------
def test_what_rises_from_the_road_under_the_roof_is_still_an_obstruction():
    r = _drive(_project(roof="BUILDING_cc", wall=True, declare=SPAN))
    assert r["fail"] is True and r["obstruction_stations"] > 0
    assert any(k.startswith("BARRIER") for k in r["obstruction_by_mesh"])


def test_a_parapet_outside_the_declared_stations_is_still_floating():
    short = dict(SPAN, center_m=80.0, len_m=20.0)              # stations 70-90: the parapet runs 70-130
    r = _drive(_project(roof="BUILDING_cc", parapet=True, declare=short))
    assert r["fail"] is True and r["floating_furniture"] > 0


def test_a_roof_built_under_its_declared_clearance_fails_drive_test():
    r = _drive(_project(roof="BUILDING_cc", roof_y=3.5, declare=SPAN))       # clear_m 5.0, tolerance 0.5
    assert r["fail"] is True and r["covered_low_overhead"] > 0
    assert r["covered_spans"][0]["lowest_overhead_m"] == 3.5
    ok = _drive(_project(roof="BUILDING_cc", roof_y=4.6, declare=SPAN))
    assert ok["fail"] is False and ok["covered_low_overhead"] == 0
    # a hanging slab under min_clear_m but over the 1.8 m strike ceiling is not set aside, and is still counted
    low = _drive(_project(roof="BUILDING_cc", roof_y=2.2, declare=SPAN))
    assert low["fail"] is True and low["covered_low_overhead"] > 0 and low["covered_spans"][0]["overhead_set_aside"] == 0


def test_a_span_declared_before_its_roof_is_built_passes_and_says_so():
    r = _drive(_project(declare=SPAN))
    assert r["fail"] is False
    assert r["covered_spans"][0]["overhead_set_aside"] == 0 and r["covered_spans"][0]["lowest_overhead_m"] is None


def test_a_covered_span_without_the_centreline_it_is_stationed_on_fails_the_ground_check():
    d = _project(roof="BUILDING_cc", declare=SPAN)
    (d / "data" / "finished_centerline.json").unlink()
    g, _st = _ground(d)
    assert g["fail"] is True and any("covered_spans" in w for w in g["reasons"])
