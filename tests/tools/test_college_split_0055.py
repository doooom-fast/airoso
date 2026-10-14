"""Ledger 0055 — College Ave's split section (Kevin, seat, 2026-10-14: "one of the lanes swerves into where the other
lane should be ... I think we should just cut into the hillside the way California does ... But for the racetrack
versions, I do like the chicane that kind of goes from one side of the road across to the other and back").

  * tools/median_envelope.py: the trust test's upper bound is the CARRIAGEWAYS' separation, not the raw line's offset
    to the far one — OSM ways offset 3.5 m from the line (on College: the tool's sphere projection of OSM against the
    line's WGS84 series) with the carriageways 21 m apart is ONE divided run, no taper inside it (v0.18.0 split
    College's run at v1280-1352 and the road swerved); and the declared registration (round 2) moves the finished
    road sideways onto the measured carriageways, cosine between its points, only inside a run of its road;
  * scripts/geometry/race_chicane.py: the S of a leg, the declaration's guards, the race island, the island pieces;
  * tools/barrier_bands.py: a declared chicane carries a race layout's lane across the road and back — the closure
    into the far strip and a race-side wall from the race strip, both pinned, every self-gate and the planned fill
    holding — and each crafted defect fails.
Plain ``test_*`` for tests/run_tests.py."""
from __future__ import annotations

import copy
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import barrier_bands as bb  # noqa: E402
import median_envelope as me  # noqa: E402
from scripts.geometry import race_chicane as rc  # noqa: E402

SD = ROOT / "tracks" / "san-diego-lake-murray"


# --- the median trust test ------------------------------------------------------------------------------------
def _median_project(sep=21.0, outboard=3.5, length=900.0):
    """a straight divided road: the raw line `outboard` m west of its own carriageway's OSM way, the opposing way
    `sep` m east of that way (the College geometry as median_envelope reads it: its sphere projection of OSM puts
    both ways ~3.6 m east of the line the WGS84 series built from the southbound one)"""
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    lat0, lon0 = 32.79, -117.06
    m_lon, m_lat = me._meters_per_degree(lat0)
    n = int(length / 3.0) + 1
    pts = [[0.0, 0.0, 3.0 * k] for k in range(n)]                       # x = east, z = north
    raw = {"origin": {"lon": lon0, "lat": lat0, "elev_m": 0.0}, "points_xyz_m": pts, "widths_m": [17.0] * n}
    (d / "data" / "centerline.raw.local.json").write_text(json.dumps(raw), encoding="utf-8")

    def way(x_east, step=40.0):
        return [[lon0 + x_east / m_lon, lat0 + z / m_lat] for z in [i * step for i in range(int(length / step) + 1)]]
    cache = [{"name": "College Avenue", "geom": way(outboard)},           # the ridden carriageway's way
             {"name": "College Avenue", "geom": way(outboard + sep)}]     # the opposing one
    (d / "data" / "network.cache.json").write_text(json.dumps(cache), encoding="utf-8")
    (d / "data" / "connectors.local.json").write_text(json.dumps({"connectors": []}), encoding="utf-8")
    (d / "track.config.json").write_text(json.dumps({"route": {"median_islands": ["College Avenue"]}}), encoding="utf-8")
    return d


def test_a_raw_line_outboard_of_its_carriageway_is_one_run_with_no_taper_inside():
    d = _median_project()
    me.build(d)
    mb = json.loads((d / "data" / "median_bands.json").read_text(encoding="utf-8"))
    runs = mb["runs"]
    assert len(runs) == 1, runs                       # ONE run (v0.18.0 rule: s = 24.5 m > 24 -> no run at all here)
    i, j = runs[0]["i"], runs[0]["j"]
    raw = json.loads((d / "data" / "centerline.raw.local.json").read_text(encoding="utf-8"))
    pre = json.loads((d / "data" / "centerline.raw.local.json.pre-median").read_text(encoding="utf-8"))
    shift = [p[0] - q[0] for p, q in zip(raw["points_xyz_m"], pre["points_xyz_m"])]
    inner = shift[i + me.TAPER_VERTS:j - me.TAPER_VERTS]
    assert inner and max(inner) - min(inner) < 1e-6, (min(inner), max(inner))     # flat: no taper inside the run
    assert abs(inner[0] - 12.0) < 1e-3               # s/2 with s clamped at SEP_TRUST (the raw offset reads 24.5 m)
    isl = mb["island_w_by_vertex"]
    assert all(isl[k] > 0 for k in range(i + me.TAPER_VERTS + me.ISLAND_PULLBACK, j - me.TAPER_VERTS - me.ISLAND_PULLBACK))


def test_the_trust_test_reads_the_carriageway_separation_and_keeps_its_other_bounds():
    # College v1282-1350: raw->opposing 24.1-24.7 m, ridden way 3.05-3.73 m east of the raw line: trusted now
    assert me.trusted(-24.4, 0.3, -3.4, 3.4)
    assert not me.trusted(-24.4, 0.3, -3.4, 9.0)      # the ridden way out of the chain bound: separation unknown
    assert not me.trusted(-30.0, 0.3, -3.0, 3.0)      # carriageways 27 m apart: a junction flare
    assert not me.trusted(-10.0, 0.3, 0.0, 0.0)       # under MIN_SEP: no median
    assert not me.trusted(-20.0, 12.0, -3.0, 3.0)     # mostly along the road: a cross street at a corner
    d = _median_project(sep=25.5)                     # found (29 m off the raw line) but 25.5 m apart: no run
    me.build(d)
    assert json.loads((d / "data" / "median_bands.json").read_text(encoding="utf-8"))["runs"] == []
    d = _median_project(sep=21.0, outboard=0.0)       # a raw line ON its way, 21 m apart: one run, as always
    me.build(d)
    assert len(json.loads((d / "data" / "median_bands.json").read_text(encoding="utf-8"))["runs"]) == 1


def test_registration_is_a_cosine_between_declared_points_and_guards_its_declaration():
    lat, bad = me.registration(400, [{"road": "r", "points": [[100, 0.0], [150, 4.0], [250, 4.0], [300, 0.0]]}])
    assert bad == [] and lat[99] == 0.0 and lat[100] == 0.0 and lat[300] == 0.0 and lat[301] == 0.0
    assert abs(lat[125] - 2.0) < 1e-9 and all(abs(lat[k] - 4.0) < 1e-9 for k in range(150, 251))
    steps = [abs(b - a) for a, b in zip(lat, lat[1:])]
    assert max(steps) <= math.pi / 2 * 4.0 / 50 + 1e-9           # the cosine's steepest step, nothing sharper
    assert steps[100] < 0.01 and steps[149] < 0.01               # zero slope at each declared point: no kink
    for pts, what in (([[100, 1.0], [200, 0.0]], "first and last"), ([[100, 0.0], [90, 1.0], [200, 0.0]], "increasing"),
                      ([[100, 0.0], [150, 6.5], [200, 0.0]], "REG_MAX_M"), ([[100, 0.0], [500, 0.0]], "outside"),
                      ([[100, 0.0]], "fewer")):
        assert any(what in b for b in me.registration(400, [{"road": "r", "points": pts}])[1]), what


def test_a_declared_registration_moves_the_finished_road_inside_its_run_only():
    d = _median_project(sep=21.0, outboard=0.0)
    cfg = json.loads((d / "track.config.json").read_text(encoding="utf-8"))
    cfg["route"]["median_registration"] = [{"road": "College Avenue", "points": [[80, 0.0], [120, 3.0], [200, 3.0], [240, 0.0]]}]
    (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    me.build(d)
    raw = json.loads((d / "data" / "centerline.raw.local.json").read_text(encoding="utf-8"))["points_xyz_m"]
    pre = json.loads((d / "data" / "centerline.raw.local.json.pre-median").read_text(encoding="utf-8"))["points_xyz_m"]
    sx = [p[0] - q[0] for p, q in zip(raw, pre)]
    assert abs(sx[60] - 10.5) < 1e-3 and abs(sx[160] - (10.5 - 3.0)) < 1e-3   # + = left of travel north = west (-x)
    assert all(abs(p[2] - q[2]) < 1e-9 for p, q in zip(raw, pre))              # a straight road: sideways only
    assert max(abs(b - a) for a, b in zip(sx[60:260], sx[61:261])) < 0.2
    cfg["route"]["median_registration"] = [{"road": "College Avenue", "points": [[80, 0.0], [120, 3.0], [400, 0.0]]}]
    (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    try:
        me.build(d)
        raise AssertionError("a registration past its run must exit 1")
    except SystemExit as e:
        assert e.code == 1
    restored = json.loads((d / "data" / "centerline.raw.local.json").read_text(encoding="utf-8"))["points_xyz_m"]
    assert restored == pre                                                       # raw restored: nothing shipped


# --- race_chicane -----------------------------------------------------------------------------------------------
def test_the_leg_is_an_eased_s_with_a_bounded_slope():
    f = rc.slope_shape
    assert f(0.0) == 0.0 and abs(f(1.0) - 1.0) < 1e-12 and abs(f(0.5) - 0.5) < 1e-12
    ts = [i / 1000.0 for i in range(1001)]
    v = [f(t) for t in ts]
    assert all(b >= a for a, b in zip(v, v[1:]))
    slopes = [(b - a) * 1000.0 for a, b in zip(v, v[1:])]
    assert max(slopes) <= rc.slope_max() + 1e-3 and abs(max(slopes) - 1.0 / (1.0 - rc.EASE)) < 0.01
    assert slopes[0] < 0.01 and slopes[-1] < 0.01            # eased in and out: no corner in the wall line


def test_the_declaration_guards_the_race_island_and_the_pieces():
    cfg = {"slug": "t", "layouts": [{"id": "street"}, {"id": "race_cw", "race_furniture": True}],
           "race": {"chicanes": [{"name": "a", "out_leg": [100, 130], "back_leg": [190, 220], "layouts": ["race_cw"]}]}}
    chs, probs = rc.declared(cfg)
    assert probs == [] and chs[0]["street_only_island"] is True
    assert rc.street_only_spans(cfg) == [(100, 220)] and rc.has_street_kn5(cfg) and rc.street_kn5_name(cfg) == "t_street.kn5"
    for bad in ({"out_leg": [130, 100], "back_leg": [190, 220], "layouts": ["race_cw"]},
                {"out_leg": [100, 130], "back_leg": [120, 220], "layouts": ["race_cw"]},
                {"out_leg": [100, 130], "back_leg": [190, 220], "layouts": ["street"]},
                {"out_leg": [100, 130], "back_leg": [190, 220], "layouts": []}):
        c2 = copy.deepcopy(cfg)
        c2["race"]["chicanes"] = [dict(bad, name="b")]
        assert rc.declared(c2)[1], bad
    iw = [7.0] * 300
    r = rc.race_island_w(iw, cfg)
    n = rc.ISLAND_NOSE_VERTS
    assert all(r[k] == 7.0 for k in range(0, 101 + n)) and all(r[k] == 0.0 for k in range(101 + n, 220 - n))
    assert all(r[k] == 7.0 for k in range(220 - n, 300)) and iw == [7.0] * 300           # a copy
    assert rc.island_pieces(50, 260, [(100, 220)]) == [(50, 100, False), (100, 220, True), (220, 259, False)]
    assert rc.island_pieces(50, 90, [(100, 220)]) == [(50, 89, False)]
    assert rc.island_pieces(150, 260, [(100, 220)]) == [(150, 220, True), (220, 259, False)]
    assert rc.legs_in_travel(chs[0], "forward") == ([100, 130], [190, 220])
    assert rc.legs_in_travel(chs[0], "reverse") == ([220, 190], [130, 100])
    assert rc.is_street_only_name("1KERB_sidewalk_streetonly_median") and not rc.is_street_only_name("1KERB_sidewalk")


# --- the declared chicane on Lake Murray's v0.18.0 data (College's continuous island v846-v1073) ------------------
CHICANE = {"name": "test_college", "out_leg": [900, 930], "back_leg": [990, 1020], "layouts": ["race_cw", "race_acw"],
           "street_only_island": True, "why": "test"}


def _project(chicanes):
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    cfg = json.loads((SD / "track.config.json").read_text(encoding="utf-8"))
    cfg["race"]["chicanes"] = chicanes
    # the data pinned here is v0.18.0's centreline, where the detector reads the Jackson / Lake Murray Blvd apex at v3297
    # (the rebuilt road, 0.45 m shorter on College, reads v3296 — the config's box; see its _boxes_apex_doc)
    for b in cfg["race"]["corridor"]["boxes"]:
        if b["apex"] == 3296:
            b["apex"] = 3297
    (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    for f in ("centerline.local.json", "median_bands.json", "mouths.json", "bridge.spans.auto.json"):
        shutil.copyfile(SD / "data" / f, d / "data" / f)
    return d


_BUILT = {}


def _built():
    if "out" not in _BUILT:
        d = _project([CHICANE])
        _BUILT["d"], _BUILT["out"] = d, bb.build(d)
    return _BUILT["d"], _BUILT["out"]


def test_a_declared_chicane_carries_each_speedway_across_and_back_every_gate_holding():
    _d, out = _built()
    assert out["fails"] == [], out["fails"]
    pts = [tuple(p) for p in json.loads((SD / "data" / "centerline.local.json").read_text())["points_xyz_m"]]
    w = json.loads((SD / "data" / "centerline.local.json").read_text())["widths_m"]
    for lid in ("race_cw", "race_acw"):
        c = out["corridors"][lid]
        assert c["no_route"]["planned"]["fail"] is False and c["no_route"]["planned"]["leak_m2"] == 0
        (wall,) = c["chicane_walls"]
        (ch,) = c["chicanes"]
        assert (wall["i"], wall["j"]) == (900, 1020)
        rs = 1.0 if c["race_side"] == "L" else -1.0
        yw, y, lane, zn = c["race_wall_y_by_vertex"], c["closure_y_by_vertex"], c["lane_by_vertex"], c["zone_by_vertex"]
        for v in (900, 1020):                                    # the wall pinned in the RACE-side strip
            assert abs(yw[v] - rs * (w[v] / 2 - 0.485)) <= 0.01
        for v in (930, 990):                                     # the closure pinned in the FAR strip, none between
            assert abs(y[v] + rs * (w[v] / 2 - 0.485)) <= 0.01
        assert all(y[v] is None for v in range(931, 990)) and all(zn[v] == "chicane" for v in range(900, 1021))
        assert ch["crossing_m"] >= bb.MIN_CROSSING_M
        mid = [0.5 * (lane[v][0] + lane[v][1]) for v in (899, 960, 1021)]
        assert rs * mid[0] > 0 and rs * mid[1] < 0 and rs * mid[2] > 0       # own side -> far side -> own side
        # two runs where College had one: the closure ends in the far strip at the out leg and restarts after
        assert {(r["i"], r["j"]) for r in c["runs"]} >= {(777, 930), (990, 1506)}
    # the planned fill's probes include the race-side pocket behind each wall — spaced by TRAVEL on both layouts (the
    # gates lens, 0055 round 2: the reverse layout walks the stations backward and got ONE pocket probe)
    pocket = {lid: [p for p in out["corridors"][lid]["no_route"]["forbidden_probes"] if p["why"] == "chicane_pocket"]
              for lid in ("race_cw", "race_acw")}
    counts = {k: len(v) for k, v in pocket.items()}
    assert counts["race_cw"] >= 5 and abs(counts["race_acw"] - counts["race_cw"]) <= 2, counts


def test_the_chicane_self_gates_fire():
    d, out = _built()
    ctx = out["_ctx"]

    def fails_after(edit):
        o = copy.deepcopy({k: v for k, v in out.items() if k != "_ctx"})
        edit(o)
        return [f for f in bb.validate(o, ctx) if f.startswith("chicanes")]
    def unpin(o):
        o["corridors"]["race_cw"]["race_wall_y_by_vertex"][900] += 1.0

    def hole(o):
        o["corridors"]["race_cw"]["race_wall_y_by_vertex"][960] = None

    def closure_in_hold(o):
        o["corridors"]["race_cw"]["closure_y_by_vertex"][960] = 0.0

    def steep(o):
        o["corridors"]["race_cw"]["race_wall_y_by_vertex"][915] += 3.0

    def undeclare(o):
        o["corridors"]["race_acw"]["chicane_walls"] = []
    for edit, what in ((unpin, "race-side strip centre"), (hole, "not declared on every span vertex"),
                       (closure_in_hold, "between the legs"), (steep, "steeper than"), (undeclare, "declared")):
        fs = fails_after(edit)
        assert any(what in f for f in fs), (what, fs)
