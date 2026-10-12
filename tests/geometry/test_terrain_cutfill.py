"""scripts/geometry/terrain_cutfill.py — the real edge (Lookout Lariat V3, ledger 0048 "P2 fixed", 2026-10-12).

On synthetic roads whose truth is known:
- the section: a 0.4 x 1.2 m toe ditch then a 1:1 back-slope on a cut, 1.5:1 down on a fill, the real ground
  between the two lines (docs/ROAD-CONSTRUCTION.md); at 2 m past the PAVEMENT edge of a D4 A road (verge 0.4 m) a
  cut's ground is no higher than the edge (audit_mesh H's ``w/2 + 2`` sample);
- the edge strip: its verge-edge row IS the verge's outer edge in plan (welded), 2 cm under it; under the road the
  ground is the road's own section 2 cm down (no grass can stand in a lane); the rows past the verge follow the
  section; no grid triangle keeps a vertex closer than L_STRIP to its own verge edge;
- stacked legs: every ground vertex nearer one leg sits on that leg's side of the mid-height between the two roads
  (verify_stacked_legs' rule), with no crack: the grid crosses the mid-height between nodes.
Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import math

from scripts.geometry import terrain_cutfill as tcf
from scripts.geometry import underlay_draft as ud


def _grid(x0, x1, z0, z1, step, f):
    """project_grid's shape: rows north -> south (z decreasing), x increasing"""
    rows = []
    z = z1
    while z >= z0 - 1e-9:
        rows.append([(x, f(x, z), z) for x in [x0 + step * i for i in range(int(round((x1 - x0) / step)) + 1)]])
        z -= step
    return rows


def _straight(n=201, y=10.0):
    return [(float(i), y, 0.0) for i in range(n)]


def test_the_section_lines():
    ze = 100.0
    assert tcf.section(0.0, ze, 120.0) == ze
    assert abs(tcf.section(0.6, ze, 120.0) - (ze - 0.4)) < 1e-9          # ditch bottom
    assert abs(tcf.section(1.2, ze, 120.0) - (ze - 0.4)) < 1e-9
    assert abs(tcf.section(3.2, ze, 120.0) - (ze - 0.4 + 2.0)) < 1e-9    # 1:1 back-slope from the ditch
    assert abs(tcf.section(3.0, ze, 50.0) - (ze - 2.0)) < 1e-9           # 1.5:1 fill
    assert tcf.section(10.0, ze, ze + 1.0) == ze + 1.0                   # the real ground between the two lines
    # D4 A: verge 0.4 m, so audit_mesh H's sample 2 m past the PAVEMENT edge is 1.6 m past the verge edge
    assert tcf.section(1.6, ze, ze + 50.0) <= ze + 1e-9


def test_the_strip_is_welded_to_the_verge_and_the_grid_is_cut_back():
    pts = _straight()
    widths = [6.6] * len(pts)
    secs, closed = ud.sections(pts, widths, [0.0] * len(pts), [0.02] * len(pts), 0.4)
    slope = 0.5                                                          # north (left) up, south (right) down

    def g(x, z):
        return 10.0 + slope * z
    grid = _grid(-60.0, 260.0, -60.0, 60.0, 10.0, g)
    out = tcf.build(pts, secs, closed, grid, 10.0, None, (0.0, 0.0), 0.0, (1.0, 1.0), skirt_m=0.0)
    ev = out["edge"]["vertices"]
    m = len(secs)
    for i in (0, 37, 150):                                               # dense rows: vl, l, c, r, vr per station
        vl, l_, c, r, vr = ev[5 * i:5 * i + 5]
        left, centre, right, sv_l, sv_r = secs[i]
        assert (vl[0], vl[2]) == (sv_l[0], sv_l[2]) and abs(vl[1] - (sv_l[1] - 0.02)) < 1e-9
        assert (vr[0], vr[2]) == (sv_r[0], sv_r[2]) and abs(vr[1] - (sv_r[1] - 0.02)) < 1e-9
        assert abs(c[1] - (centre[1] - 0.02)) < 1e-9 and abs(l_[1] - (left[1] - 0.02)) < 1e-9
    rows = ev[5 * m:]
    lat = list(tcf.STRIP_L) + list(tcf.BAND_L)
    ze = secs[99][3][1]                                                  # x = 99: a sparse station (every 3rd at 1 m)
    for v in rows:
        if abs(v[0] - 99.0) > 1e-6:
            continue
        lpast = abs(v[2]) - (3.3 + 0.4)
        k = min(range(len(lat)), key=lambda q: abs(lat[q] - lpast))
        if lat[k] in tcf.BAND_L:
            continue
        want = tcf.section(lat[k], ze, g(v[0], v[2]))
        assert abs(v[1] - want) < 1e-6, (v, lat[k], want)
    # left (north, uphill): the ditch then the cut; right (south): the fill
    north = sorted((v for v in rows if abs(v[0] - 99.0) < 1e-6 and v[2] > 0), key=lambda v: v[2])
    south = sorted((v for v in rows if abs(v[0] - 99.0) < 1e-6 and v[2] < 0), key=lambda v: -v[2])
    assert abs(north[0][1] - (ze - 0.4)) < 1e-6 and north[3][1] > ze + 1.0
    assert all(b[1] < a[1] for a, b in zip(south, south[1:4]))
    # the grid: no kept vertex closer than L_STRIP to its own verge edge
    for x, y, z in out["grid"]["vertices"]:
        if -1.0 <= x <= 201.0:
            assert abs(z) - 3.7 >= tcf.L_STRIP - 1e-6, (x, z)
    assert out["report"]["grid_tris_removed_under_strip"] > 0


def test_stacked_legs_hold_each_side_of_the_mid_height():
    # a long U: leg A east along z = 0 at y = 0, a semicircle (R 12) round the east end, leg B west along z = 24
    # at y = 10 (climbing 10 m on the turn), a semicircle home at the west end descending again
    R, L = 12.0, 400.0
    pts = []
    for i in range(int(L)):
        pts.append((float(i), 0.0, 0.0))
    n = 40
    for k in range(n):
        a = -math.pi / 2 + math.pi * k / n
        pts.append((L + R * math.cos(a), 10.0 * k / n, R + R * math.sin(a)))
    for i in range(int(L)):
        pts.append((L - i, 10.0, 2 * R))
    for k in range(n):
        a = math.pi / 2 + math.pi * k / n
        pts.append((R * math.cos(a), 10.0 - 10.0 * k / n, R + R * math.sin(a)))
    pts.append(pts[0])
    widths = [6.6] * len(pts)
    secs, closed = ud.sections(pts, widths, [0.0] * len(pts), [0.0] * len(pts), 0.4)
    assert closed

    def g(x, z):                                       # a hillside rising north, through both roads roughly
        return 10.0 * z / (2 * R) + 1.5 * math.sin(x / 37.0)
    grid = _grid(-60.0, L + 60.0, -60.0, 2 * R + 60.0, 10.0, g)
    out = tcf.build(pts, secs, closed, grid, 10.0, None, (0.0, 0.0), 0.0, (1.0, 1.0), skirt_m=0.0)
    lap = tcf.Lap(pts, secs, closed)
    bad = tested = 0
    for mesh in ("edge", "grid"):
        for x, y, z in out[mesh]["vertices"]:
            if not (60.0 <= x <= 300.0 and 4.0 < z < 2 * R - 4.0):      # between the legs, mid-stretch
                continue
            q = lap.nearest(x, z)
            far = lap.nearest_far(x, z, q[4])
            if far is None:
                continue
            yo, yt = lap.y_at(q[1], q[2]), lap.y_at(far[1], far[2])
            tested += 1
            if abs(y - yt) < abs(y - yo):
                bad += 1
    assert tested > 50 and bad == 0, (tested, bad)
    assert out["report"]["section_counts"]["stacked_held"] > 0
