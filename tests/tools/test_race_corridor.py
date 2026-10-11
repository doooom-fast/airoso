"""tools/race_corridor.py — the closure-line solver (ledger 0049), ported from the 2026-10-11 design study.

Pins:
  * the PORT: on the real Lake Murray data both directions reproduce the study's solution
    (tests/tools/fixtures/sd_corridor_proto.json, dumped from the study's solver before the port) to 1 mm,
    with the same runs, pins and pin rates; the spec §3 minima (6.86 m beside the islands, 7.9 m at cw v845,
    9.23 m at cw v1355, 8.81 m on College-3) within 0.05 m; 0 backward steps; plan radius >= 20 m (22.4 m at cw
    v1543); the mirror y_acw = -y_cw within 0.3 m on the running vertices;
  * the RULES on synthetic straights: a 17 m road puts the closure at +-4.015 m (11.36 m clear); a 13 m road
    leaves less than a 2 m pocket (the writer must declare it whole street); an island puts the closure on its
    race face + 0.485 m; the run ends are pinned on the far strip centre; a flare shorter than 120 m does not
    move the closure.
Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import race_corridor as rc  # noqa: E402

SD = ROOT / "tracks" / "san-diego-lake-murray" / "data"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sd_corridor_proto.json"
BOXES = [(1506, 1521), (2311, 2328), (3289, 3304)]
WHOLE = (4454, 777)


def _sd():
    cl = json.loads((SD / "centerline.local.json").read_text())
    pts = [tuple(p) for p in cl["points_xyz_m"]]
    w = [float(x) for x in cl["widths_m"]]
    iw = json.loads((SD / "median_bands.json").read_text())["island_w_by_vertex"]
    return pts, w, iw


_CACHE = {}


def _solved():
    if "sol" not in _CACHE:
        pts, w, iw = _sd()
        n = rc.ring_count(pts)
        p = rc.params_from({"pin_rate": {"4454": 10}})
        ctx = rc.prepare(pts, w, iw, p)

        def free(v):
            return rc.in_rng(v, *WHOLE, n) or any(rc.in_rng(v, a, b, n) for a, b in BOXES)
        _CACHE["sol"] = {d: rc.solve(pts, w, iw, free, d, p, context=ctx) for d in ("cw", "acw")}
        _CACHE["ctx"], _CACHE["data"], _CACHE["n"] = ctx, (pts, w, iw), n
    return _CACHE["sol"], _CACHE["ctx"], _CACHE["data"], _CACHE["n"]


def _y(o):
    return [None if g is None else o["e"] * g for g in o["g"]]


def test_the_port_reproduces_the_study_solution():
    sol, _ctx, _data, n = _solved()
    fx = json.loads(FIXTURE.read_text())
    for d in ("cw", "acw"):
        y, ref = _y(sol[d]), fx[d]["y_by_vertex"]
        assert len(y) == len(ref) == n
        assert [a is None for a in y] == [b is None for b in ref]
        assert max(abs(a - b) for a, b in zip(y, ref) if a is not None) < 1e-3
        runs = [(R["vs"][0], R["vs"][-1]) for R in sol[d]["runs"]]
        assert runs == [(r["i"], r["j"]) for r in fx[d]["runs"]], runs
        for R, r in zip(sol[d]["runs"], fx[d]["runs"]):
            assert all(abs(1 / k - x) < 0.01 for k, x in zip(R["k_pin"], r["pin_rate"])), (R["k_pin"], r["pin_rate"])
            assert R["infeas"] == []


def test_runs_and_pins_on_the_far_strip_centre():
    sol, _ctx, (pts, w, _iw), _n = _solved()
    want = {"cw": [(777, 1506), (1521, 2311), (2328, 3289), (3304, 4454)],
            "acw": [(4454, 3304), (3289, 2328), (2311, 1521), (1506, 777)]}
    for d in ("cw", "acw"):
        o = sol[d]
        assert [(R["vs"][0], R["vs"][-1]) for R in o["runs"]] == want[d]
        far = 1.0 if d == "cw" else -1.0             # cw closes on its LEFT (+y), acw on its right
        for R in o["runs"]:
            for v in (R["vs"][0], R["vs"][-1]):
                assert abs(o["e"] * o["g"][v] - far * (w[v] / 2 - 0.485)) < 0.01, (d, v)


def test_the_spec_minima_and_shape():
    sol, ctx, (pts, w, _iw), n = _solved()
    y = _y(sol["cw"])

    def clear(v):                                    # cw: right curb strip face .. the closure's right face
        return (w[v] / 2 - 0.82) + (y[v] - 0.335)
    isl = [v for v in range(846, 1259) if ctx["half_auth"][v] > 0]
    assert abs(min(clear(v) for v in isl) - 6.86) < 0.05
    assert abs(clear(845) - 7.91) < 0.05
    assert abs(clear(1355) - 9.23) < 0.05
    assert abs(min(clear(v) for v in range(1374, 1488)) - 8.81) < 0.05
    assert abs(min(clear(v) for v in range(1540, 1740)) - 6.86) < 0.05
    neck = [clear(v) for v in range(1279, 1347)]
    assert 10.85 <= min(neck) and max(neck) <= 11.3
    for d in ("cw", "acw"):
        yy = _y(sol[d])
        for R in sol[d]["runs"]:
            rad, _rv, back = rc.plan_radius(pts, n, R["vs"], yy)
            assert back == 0 and rad >= 20.0, (d, R["vs"][0], rad)
    rad, rv, _ = rc.plan_radius(pts, n, sol["cw"]["runs"][1]["vs"], y)
    assert abs(rad - 22.4) < 0.3 and rv == 1543


def test_the_mirror_on_the_running_vertices():
    sol, ctx, (pts, _w, _iw), n = _solved()
    st = ctx["st"]
    ycw, yacw = _y(sol["cw"]), _y(sol["acw"])
    ends = [e for z in ctx["island_zones"] + ctx["openings"] for e in z]
    pins = [777, 1506, 1521, 2311, 2328, 3289, 3304, 4454]
    worst = 0.0
    for v in range(n):
        if ycw[v] is None or yacw[v] is None or v in pins:
            continue
        if any(abs(st[v] - st[e]) < 100.0 for e in ends) or any(abs(st[v] - st[p]) <= 120.0 for p in pins):
            continue
        worst = max(worst, abs(ycw[v] + yacw[v]))
    assert worst <= 0.3, worst


# --- synthetic straights --------------------------------------------------------------------------------

def _straight(widths, island=None, step=3.0):
    pts = [(0.0, 0.0, step * k) for k in range(len(widths))]
    return pts, list(widths), list(island or [0.0] * len(widths))


def _solve_straight(widths, island=None, free_n=8, direction="cw", **params):
    pts, w, iw = _straight(widths, island)
    n = len(pts)

    def free(v):
        return v < free_n or v >= n - free_n
    p = rc.params_from(params)
    return rc.solve(pts, w, iw, free, direction, p), pts, w


def test_a_17_m_road_gets_an_alvarado_wide_lane():
    o, _pts, w = _solve_straight([17.0] * 200)
    y = _y(o)
    for v in range(90, 110):
        assert abs(y[v] - 4.015) < 0.01, (v, y[v])
        assert abs((w[v] / 2 - 0.82) + (y[v] - 0.335) - 11.36) < 0.01
    oa, _p, _w = _solve_straight([17.0] * 200, direction="acw")
    assert abs(_y(oa)[100] + 4.015) < 0.01                                  # the mirror


def test_a_13_m_road_leaves_no_pocket_so_it_must_be_whole_street():
    o, _pts, w = _solve_straight([13.0] * 200)
    y = _y(o)[100]
    pocket = (w[100] / 2 - 0.82) - (y + 0.335)                              # behind the closure, cw
    assert pocket < 2.0, pocket


def test_an_island_puts_the_closure_on_its_race_face():
    n = 300
    island = [4.0 if 100 <= v <= 200 else 0.0 for v in range(n)]
    o, _pts, _w = _solve_straight([24.0] * n, island)
    y = _y(o)
    for v in range(140, 160):
        assert abs(y[v] - (-(2.0 + 0.485))) < 0.02, (v, y[v])                  # cw: the island's right face
    half = rc.authored_half(island, n)
    for v in range(100, 201):
        assert y[v] + 0.335 <= -half[v] - 0.15 + 1e-6, (v, y[v], half[v])       # every nose on the race side


def test_a_short_flare_does_not_move_the_closure():
    n = 300
    base, _p, _w = _solve_straight([17.0] * n)
    flared = [24.0 if 140 <= v <= 160 else 17.0 for v in range(n)]          # 60 m flare (< 120 m)
    o, _p2, _w2 = _solve_straight(flared)
    yb, yf = _y(base), _y(o)
    assert max(abs(yb[v] - yf[v]) for v in range(120, 181)) < 0.05


def test_lane_by_vertex_faces_and_full_width_pins():
    def same(a, b):
        return all(abs(x - y) < 1e-9 for x, y in zip(a, b))
    y = [None, 4.0, 4.0, None]
    w = [17.0] * 4
    lane = rc.lane_by_vertex(y, w, 4, "cw", pins={2})
    assert same(lane[0], [-7.68, 7.68]) and same(lane[2], [-7.68, 7.68])     # no closure / a pin: full width
    assert same(lane[1], [-7.68, 3.665])                                     # cw: right strip face .. closure face
    lane = rc.lane_by_vertex([None, -4.0, None, None], w, 4, "acw")
    assert same(lane[1], [-3.665, 7.68])                                     # acw: closure face .. left strip face
