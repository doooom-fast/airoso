"""tools/verify_centreline_paint.py: is the lap on the painted road, smooth on the climb, never folding, closed?

Lookout Lariat V3 (ledger 0048, P2). Pins each of the four checks on synthetic lines whose truth is known:
(a) a line 0.3 m off the paint passes and 1.0 m off fails, and a stacked hairpin's other leg (running the
other way) never stands in for the leg the paint is on; (b) OSM-like facets fail, a 1 m circle and a 1 m
clothoid pass, a curvature jump fails the neighbour rule, 3 m points fail the spacing rule; (c) a figure of
eight and a folded vertex fail; (d) an open seam and a seam kink fail, a smooth closed lap passes across the
wrap (L13). Plus the real Lariat: the committed paint centreline passes, the OSM line does not. Plain
``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import verify_centreline_paint as vp  # noqa: E402
from scripts.geometry.projection import _meters_per_degree  # noqa: E402

LAT0, LON0 = 39.70, -105.20
MLON, MLAT = _meters_per_degree(LAT0)
LARIAT = ROOT / "tracks" / "lookout-lariat"


def ll(p):
    return (LON0 + p[0] / MLON, LAT0 + p[1] / MLAT)


def line_of(pts, props=None):
    return vp.Line([ll(p) for p in pts], props)


def traces_of(windows):
    """A paint_traces.json-shaped dict: windows = [(id, [(x, y, heading_deg, confidence), ...])] in the
    same local metres as ll()."""
    out = {"frame": {"origin_lonlat": [LON0, LAT0], "m_per_deg": [MLON, MLAT]}, "windows": []}
    for wid, pts in windows:
        out["windows"].append({"id": wid, "kind": "width_station", "window": wid,
                               "yellow": {"xz_m": [[p[0], p[1]] for p in pts], "lap_st_m": [None] * len(pts),
                                          "heading_deg": [p[2] for p in pts], "confidence": [p[3] for p in pts],
                                          "source": ["profile"] * len(pts)}})
    return out


def arc(c, R, a0, a1, step):
    n = max(2, int(abs(a1 - a0) * R / step) + 1)
    return [(c[0] + R * math.cos(a0 + (a1 - a0) * k / (n - 1)), c[1] + R * math.sin(a0 + (a1 - a0) * k / (n - 1)))
            for k in range(n)]


def straight(a, b, step):
    n = max(2, int(math.dist(a, b) / step) + 1)
    return [(a[0] + (b[0] - a[0]) * k / (n - 1), a[1] + (b[1] - a[1]) * k / (n - 1)) for k in range(n)]


def stadium(R=40.0, L=300.0, step=1.0):
    """A closed lap: east along y = 0, a left semicircle, west along y = 2R, a left semicircle home."""
    pts = straight((0.0, 0.0), (L, 0.0), step)[:-1]
    pts += arc((L, R), R, -math.pi / 2, math.pi / 2, step)[:-1]
    pts += straight((L, 2 * R), (0.0, 2 * R), step)[:-1]
    pts += arc((0.0, R), R, math.pi / 2, 3 * math.pi / 2, step)[:-1]
    return pts + [pts[0]]


def test_paint_distance_and_same_way_matching():
    road = straight((0, 0), (100, 0), 1.0)
    paint = [(x, 0.0, 0.0, "high") for x in range(10, 90, 2)] + [(x, 0.0, 0.0, "low") for x in (50.5, 51.5)]
    tr = traces_of([("W", paint)])
    for off, ok in ((0.3, True), (0.74, True), (1.0, False)):
        L = line_of([(x, y + off) for x, y in road])
        res = vp.gate(L, tr, [0, 0], loop=False)
        assert res["a_paint"]["pass"] is ok, (off, res["a_paint"]["max_m"])
        assert res["a_paint"]["points"] == 40  # low points are never judged
    # a U-turn: leg A eastbound at y = 0 (where the paint is), leg B westbound at y = 0.4. A line that has
    # lost leg A (moved 2 m south) still runs leg B 0.4 m from the paint, but the wrong way: it must FAIL.
    legA = [(x, -2.0) for x in range(0, 101)]
    turn = arc((100, -0.8), 1.2, -math.pi / 2, math.pi / 2, 0.3)
    legB = [(x, 0.4) for x in range(100, -1, -1)]
    L = line_of(legA + turn[1:-1] + legB)
    res = vp.gate(L, tr, [0, 0], loop=False)
    assert not res["a_paint"]["pass"] and res["a_paint"]["max_m"] > 1.9
    # paint on leg B, heading west, is matched to leg B
    trB = traces_of([("B", [(x, 0.4, 180.0, "medium") for x in range(10, 90, 2)])])
    assert vp.gate(L, trB, [0, 0], loop=False)["a_paint"]["max_m"] < 0.01


def test_curvature_facets_fail_smooth_curves_pass():
    tr = traces_of([])
    # a smooth R 12 m hairpin at 1 m between straights: passes
    smooth = straight((-30, 0), (0, 0), 1.0)[:-1] + arc((0, 12), 12.0, -math.pi / 2, math.pi / 2, 1.0)[:-1] + \
        straight((0, 24), (-30, 24), 1.0)
    res = vp.gate(line_of(smooth), tr, [0, 1e9], loop=False)
    b = res["b_curvature"]
    # a circle joined straight onto a straight is a curvature step (1/R at once): both rules see the join
    assert not b["pass"] and b["adjacent_fails"] > 0 and b["step_fails"] > 0 and b["spacing_fails"] == 0
    assert all(abs(w["osm_st_m"] - 30.0) < 3 or abs(w["osm_st_m"] - (30.0 + math.pi * 12)) < 3 for w in b["worst"])
    # the same hairpin with clothoid entries (curvature ramps over 15 m) passes every rule
    pts = [(0.0, 0.0)]
    th, x, y = 0.0, 0.0, 0.0
    ramp, R = 15.0, 12.0
    plan = [(30, 0.0, 0.0), (ramp, 0.0, 1 / R), (math.pi * R - ramp, 1 / R, 1 / R), (ramp, 1 / R, 0.0), (30, 0.0, 0.0)]
    for L_, k0, k1 in plan:
        n = int(round(L_))
        for i in range(n):
            k = k0 + (k1 - k0) * (i + 0.5) / n
            for _ in range(100):  # 1 cm integration
                th += k * 0.01 / 2
                x += 0.01 * math.cos(th)
                y += 0.01 * math.sin(th)
                th += k * 0.01 / 2
            pts.append((x, y))
    res = vp.gate(line_of(pts), tr, [0, 1e9], loop=False)
    assert res["b_curvature"]["pass"], res["b_curvature"]["worst"][:3]
    # OSM-like facets: 3 m chords whose turn is bunched on alternate vertices
    fac = []
    th, x, y = 0.0, 0.0, 0.0
    for i in range(40):
        fac.append((x, y))
        th += math.radians(20.0 if i % 2 else 0.0)
        x += 3.0 * math.cos(th)
        y += 3.0 * math.sin(th)
    res = vp.gate(line_of(fac), tr, [0, 1e9], loop=False)
    b = res["b_curvature"]
    assert not b["pass"] and b["step_fails"] > 0 and b["adjacent_fails"] > 0 and b["spacing_fails"] > 0


def test_topology_reversal_and_self_intersection():
    tr = traces_of([])
    # the line runs east, turns twice and crosses its own first segment (not at a vertex)
    loop_back = [(0, 0), (20, 0), (20, 10), (10, 10), (10, -10)]
    res = vp.gate(line_of(loop_back), tr, [0, 0], loop=False)
    assert not res["c_topology"]["pass"] and res["c_topology"]["self_intersections"][0]["segments"] == [0, 3]
    assert not res["c_topology"]["reversals"]  # 90 deg turns are not reversals
    # touching at a shared vertex is not a crossing (a closed lap's seam touches v0 by definition)
    assert vp.gate(line_of(stadium()), tr, [0, 0], loop=True)["c_topology"]["pass"]
    folded = [(0, 0), (10, 0), (20, 0), (12, 1.0), (2, 2.0)]
    res = vp.gate(line_of(folded), tr, [0, 0], loop=False)
    assert res["c_topology"]["reversals"] and not res["c_topology"]["pass"]
    dup = [(0, 0), (1, 0), (1, 0), (2, 0)]
    assert vp.gate(line_of(dup), tr, [0, 0], loop=False)["c_topology"]["short_segments"]


def test_closure_seam_and_wrap():
    tr = traces_of([])
    lap = stadium(step=1.0)
    # a curvature-continuous lap would need clothoids; judge only the straight first 200 m as "the climb",
    # so the seam (v0, on the straight) is on the climb and measured across the wrap
    res = vp.gate(line_of(lap), tr, [0, 200], loop=True)
    assert res["d_closure"]["pass"] and res["d_closure"]["closed_exactly"] and res["d_closure"]["seam_on_climb"]
    assert res["b_curvature"]["pass"]
    # the closing vertex 1 mm off v0: not closed
    opened = lap[:-1] + [(lap[0][0], lap[0][1] + 0.001)]
    L = line_of(opened)
    assert not vp.gate(L, tr, [0, 200], loop=True)["d_closure"]["pass"]
    # a 6 deg kink AT the seam (v0 moved sideways): fails (d) because it fails (b) across the wrap
    kinked = [(0.0, 0.3)] + lap[1:-1] + [(0.0, 0.3)]
    r = vp.gate(line_of(kinked), tr, [0, 200], loop=True)
    assert r["d_closure"]["closed_exactly"] and not r["d_closure"]["pass"] and r["d_closure"]["seam"]["step_deg"] > 1.0
    # the same kink 100 m from the seam is caught by (b), and (d) still passes
    k2 = [((x, y + 0.3) if abs(x - 100) < 0.5 and y == 0 else (x, y)) for x, y in lap]
    r = vp.gate(line_of(k2), tr, [0, 200], loop=True)
    assert r["d_closure"]["pass"] and not r["b_curvature"]["pass"]


def test_facets_off_the_climb_fail():
    # (e), 2026-10-12: the integrated Drive-1 line passed (a)-(d) with 52-72 deg single-vertex junction chevrons off
    # the climb (C12, C13, C14, exit 259, the lid's east end); (e) fails a vertex off the climb turning more than
    # FACET_STEP_DEG, or tighter than FACET_R_MIN_M over its own spacing, and passes the same corner as an arc
    tr = traces_of([])
    chevron = straight((0.0, 0.0), (200.0, 0.0), 3.0) + straight((200.0, 0.0), (200.0, 200.0), 3.0)[1:]
    r = vp.gate(line_of(chevron), tr, [0, 0], loop=False)
    assert not r["e_facets"]["pass"] and r["e_facets"]["max_step_deg"] > 85, r["e_facets"]
    filleted = straight((0.0, 0.0), (188.0, 0.0), 3.0) + arc((188.0, 12.0), 12.0, -math.pi / 2, 0.0, 1.0)[1:]         + straight((200.0, 12.0), (200.0, 200.0), 3.0)[1:]
    r = vp.gate(line_of(filleted), tr, [0, 0], loop=False)
    assert r["e_facets"]["pass"] and r["e_facets"]["tightest_radius_m"] > 10.0, r["e_facets"]
    # the same chevron ON the climb is (b)'s business, not (e)'s
    r = vp.gate(line_of(chevron), tr, [0, 1000], loop=False)
    assert r["e_facets"]["pass"] and r["e_facets"]["points_off_climb"] == 0


def test_cli_and_real_lariat():
    """The committed paint centreline passes all five checks; the OSM line it replaced fails (a), (b) and (e)."""
    cl = LARIAT / "data" / "centerline.geojson"
    tp = LARIAT / "data" / "aerial" / "paint_traces.json"
    osm = LARIAT / "data" / "centerline.osm.geojson"
    if not (cl.exists() and tp.exists() and osm.exists()):
        return
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "gate.json"
        assert vp.main([str(LARIAT), "--out", str(out)]) == 0
        r = json.loads(out.read_text(encoding="utf-8"))
        assert r["pass"] and r["a_paint"]["max_m"] <= vp.PAINT_MAX_M and r["a_paint"]["points"] > 5000
        assert r["b_curvature"]["points"] > 7000 and r["b_curvature"]["climb_by"] == "osm_station_m"
        assert r["d_closure"]["closed_exactly"] and r["d_closure"]["seam_on_climb"]
        assert r["e_facets"]["pass"] and r["e_facets"]["max_step_deg"] <= vp.FACET_STEP_DEG
        assert vp.main([str(LARIAT), "--centerline", str(osm), "--out", str(out)]) == 1
        r = json.loads(out.read_text(encoding="utf-8"))
        assert not r["a_paint"]["pass"] and r["a_paint"]["max_m"] > 7.0  # C4: OSM cuts the hairpin
        assert not r["b_curvature"]["pass"] and r["b_curvature"]["spacing_fails"] > 0
        assert not r["e_facets"]["pass"] and r["e_facets"]["max_step_deg"] > 70      # C12 / C13 / exit 259 nodes
        assert vp.main([str(LARIAT), "--centerline", str(Path(td) / "nope.geojson")]) == 2
