"""scripts/gps/fillet.py + build_centerline's opt-in route.fillet (ledger 0073: Sand Creek's line re-sourced from OSM).

An OSM route is a polygon: a street corner is one shared node, a curve a chain of nodes. route.fillet rounds it once,
before the 3 m resample: a declared corner becomes the circle of its declared radius tangent to both legs, every other
node the arc inside its own segments. Offline (the Overpass snapshot is written by the test). Plain ``test_*``.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.gps import centerline as C  # noqa: E402
from scripts.gps import overpass  # noqa: E402
from scripts.gps.fillet import _mpd, fillet_ring, insert_point  # noqa: E402

LAT0, LON0 = 39.78, -104.92
ML, MT = _mpd(LAT0)


def ll(x, y):
    return (LON0 + x / ML, LAT0 + y / MT)


def xy(p):
    return ((p[0] - LON0) * ML, (p[1] - LAT0) * MT)


def circumradius(a, b, c):
    A, B, Cc = math.dist(b, c), math.dist(a, c), math.dist(a, b)
    ar = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2
    return float("inf") if ar < 1e-9 else A * B * Cc / (4 * ar)


def square(side=200.0):
    return [ll(*p) for p in ((0, 0), (side, 0), (side, side), (0, side), (0, 0))]


def test_a_declared_corner_is_the_circle_of_its_radius_tangent_to_both_legs():
    ring = square()
    corners = [{"name": "ne", "at": [ring[2][1], ring[2][0]], "radius_m": 20.0}]
    out, rep = fillet_ring(ring, corners=corners, round_nodes=False)
    assert out[0] == out[-1] and rep["closed"]
    c = rep["corners"][0]
    assert abs(c["deflection_deg"] - 90.0) < 1e-6 and abs(c["tangent_m"] - 20.0) < 1e-6
    assert abs(c["apex_moved_m"] - 20.0 * (math.sqrt(2) - 1)) < 0.05
    P = [xy(p) for p in out]
    arc = [p for p in P if p[0] > 180.001 and p[1] > 180.001]
    # every arc sample is R from the centre (180, 180); the curve leaves (200, 180) and reaches (180, 200)
    assert len(arc) >= 10
    assert all(abs(math.dist(p, (180.0, 180.0)) - 20.0) < 1e-3 for p in arc), max(abs(math.dist(p, (180, 180)) - 20) for p in arc)
    assert any(math.dist(p, (200.0, 180.0)) < 1e-3 for p in P) and any(math.dist(p, (180.0, 200.0)) < 1e-3 for p in P)
    # the undeclared corners are left as they are (round_nodes off)
    assert any(math.dist(p, (200.0, 0.0)) < 1e-3 for p in P)


def test_every_other_node_is_rounded_inside_its_own_segments():
    # an open road with one 20 deg node between 40 m and 30 m segments: T = 15 m, R = 15 / tan(10 deg)
    a = math.radians(20.0)
    line = [ll(0, 0), ll(40, 0), ll(40 + 30 * math.cos(a), 30 * math.sin(a))]
    out, rep = fillet_ring(line, round_nodes=True)
    P = [xy(p) for p in out]
    assert rep["nodes_rounded"] == 1 and not rep["closed"]
    assert math.dist(P[0], (0, 0)) < 1e-6 and math.dist(P[-1], xy(line[-1])) < 1e-6   # open ends stay
    R = 15.0 / math.tan(a / 2)
    inner = [circumradius(P[i - 1], P[i], P[i + 1]) for i in range(2, len(P) - 2)]
    assert all(abs(r - R) < 0.05 * R for r in inner), (R, min(inner), max(inner))
    # no point moved more than T tan(D/4) off the original polygon's node
    worst = min(math.dist(p, (40, 0)) for p in P)
    assert abs(worst - 15.0 * math.tan(a / 4)) < 0.05


def test_a_corner_not_on_the_route_or_two_overlapping_arcs_are_refused():
    ring = square()
    far = [{"name": "nowhere", "at": [LAT0 + 0.01, LON0 + 0.01], "radius_m": 10.0}]
    try:
        fillet_ring(ring, corners=far)
        raise AssertionError("a corner 1 km off the route was accepted")
    except ValueError as e:
        assert "nowhere" in str(e)
    big = [{"name": "a", "at": [ring[1][1], ring[1][0]], "radius_m": 150.0},
           {"name": "b", "at": [ring[2][1], ring[2][0]], "radius_m": 150.0}]
    try:
        fillet_ring(ring, corners=big)
        raise AssertionError("two 150 m arcs on a 200 m side were accepted")
    except ValueError as e:
        assert "overlap" in str(e)


def test_a_way_join_after_a_node_by_node_curve_keeps_the_curves_radius_with_simplify():
    # a ramp drawn as nodes every 3 m on a 100 m radius, joining a straight street at a 26 deg kink
    R = 100.0
    ramp = [(R * math.sin(t), R - R * math.cos(t)) for t in [k * 0.03 for k in range(0, 12)]]
    end = ramp[-1]
    h = math.atan2(ramp[-1][1] - ramp[-2][1], ramp[-1][0] - ramp[-2][0]) + math.radians(26.0)
    street = [(end[0] + s * math.cos(h), end[1] + s * math.sin(h)) for s in (3.0, 6.0, 60.0)]
    line = [ll(*p) for p in ramp + street]

    def min_r(out):
        r3 = C.resample(out, 1.0)
        P = [xy(p) for p in r3]
        return min(circumradius(P[i - 2], P[i], P[i + 2]) for i in range(2, len(P) - 2))
    plain, _ = fillet_ring(line)
    merged, rep = fillet_ring(line, simplify_m=0.25)
    assert rep["simplify_m"] == 0.25
    assert min_r(plain) < 10.0 < 15.0 < min_r(merged), (min_r(plain), min_r(merged))


def test_insert_point_puts_station_zero_on_the_line_at_start_at():
    line = [ll(0, 0), ll(100, 0), ll(100, 100)]
    tgt = ll(37.0, 2.0)
    out, k, d = insert_point(line, [tgt[1], tgt[0]])
    assert k == 1 and abs(d - 2.0) < 0.01 and math.dist(xy(out[1]), (37.0, 0.0)) < 0.01 and len(out) == 4


def _snapshot(d: Path, bbox, names, ways):
    q = overpass.build_query(tuple(bbox), names)
    els = [{"type": "way", "id": wid, "tags": {"highway": "tertiary", "name": f"w{wid}"},
            "geometry": [{"lon": p[0], "lat": p[1]} for p in g]} for wid, g in ways.items()]
    (d / "data").mkdir(exist_ok=True)
    (d / "data" / "osm.cache.json").write_text(json.dumps({
        "query_fingerprint": hashlib.sha256(q.encode()).hexdigest()[:16], "payload": {"elements": els}}))


def test_build_centerline_rounds_a_declared_corner_and_starts_at_start_at():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        sq = square(300.0)
        ways = {1: [sq[0], sq[1]], 2: [sq[1], sq[2]], 3: [sq[2], sq[3]], 4: [sq[3], sq[0]]}
        names = ["id:1", "id:2", "id:3", "id:4"]
        bbox = [LAT0 - 0.01, LON0 - 0.01, LAT0 + 0.01, LON0 + 0.01]
        _snapshot(d, bbox, names, ways)
        start = ll(150.0, 0.5)
        corners = [{"name": f"c{i}", "at": [sq[i][1], sq[i][0]], "radius_m": 25.0} for i in range(4)]
        cfg = {"slug": "t", "name": "t", "version": "0.0.1", "loop": True, "default_width_m": 9.0,
               "location": {"lat": LAT0, "lon": LON0, "timezone": "America/Denver"}, "origin": "centroid",
               "surfaces": {"road": "asphalt"}, "layouts": [{"id": "full"}], "lighting": {}, "source": {"type": "osm"},
               "route": {"bbox": bbox, "roads": names, "start_at": [start[1], start[0]],
                         "fillet": {"corners": corners, "simplify_m": 0.25}}}
        (d / "track.config.json").write_text(json.dumps(cfg))
        out, stats = C.build_for_source(d)
        f = json.loads(out.read_text())["features"][0]
        pts = [tuple(c) for c in f["geometry"]["coordinates"]]
        assert pts[0] == pts[-1] and math.dist(xy(pts[0]), (150.0, 0.0)) < 0.05
        assert len(f["properties"]["fillet"]["corners"]) == 4
        lap = 4 * 300.0 - 4 * 2 * 25.0 + 4 * (math.pi / 2) * 25.0
        assert abs(f["properties"]["length_m"] - lap) < 1.0, (f["properties"]["length_m"], lap)
        P = [xy(p) for p in pts[:-1]]
        rs = [circumradius(P[i - 1], P[i], P[(i + 1) % len(P)]) for i in range(len(P))]
        assert min(rs) > 24.0, min(rs)


def test_a_route_without_fillet_is_stitched_as_before():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        sq = square(300.0)
        ways = {1: [sq[0], sq[1]], 2: [sq[1], sq[2]], 3: [sq[2], sq[3]], 4: [sq[3], sq[0]]}
        names = ["id:1", "id:2", "id:3", "id:4"]
        bbox = [LAT0 - 0.01, LON0 - 0.01, LAT0 + 0.01, LON0 + 0.01]
        _snapshot(d, bbox, names, ways)
        cfg = {"slug": "t", "name": "t", "version": "0.0.1", "loop": True, "default_width_m": 9.0,
               "location": {"lat": LAT0, "lon": LON0, "timezone": "America/Denver"}, "origin": "centroid",
               "surfaces": {"road": "asphalt"}, "layouts": [{"id": "full"}], "lighting": {}, "source": {"type": "osm"},
               "route": {"bbox": bbox, "roads": names}}
        (d / "track.config.json").write_text(json.dumps(cfg))
        out, _ = C.build_for_source(d)
        f = json.loads(out.read_text())["features"][0]
        assert "fillet" not in f["properties"] and abs(f["properties"]["length_m"] - 1200.0) < 5.0
        P = [xy(tuple(c)) for c in f["geometry"]["coordinates"]]

        def turn(i):
            a, b, c = P[i - 1], P[i], P[i + 1]
            h1, h2 = math.atan2(b[1] - a[1], b[0] - a[0]), math.atan2(c[1] - b[1], c[0] - b[0])
            return abs(math.degrees((h2 - h1 + math.pi) % (2 * math.pi) - math.pi))
        assert max(turn(i) for i in range(1, len(P) - 1)) > 40.0     # the square corners are still kinks
