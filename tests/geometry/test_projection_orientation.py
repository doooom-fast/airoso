"""The ring rotation / reversal in projection and the elevation file it leaves behind (ledger 0060, High Plains).

``route.start_at`` / ``route.reverse`` are applied in ``scripts.geometry.projection.build`` — after the elevation stage
wrote ``centerline.elevation.json`` in ``centerline.geojson`` order. Two readers paired that file with the local line by
bare index (build_mesh's bridge detector, drive_test's replication): on High Plains the ring was rotated by 815 of
1,074 points, the detector read the bare earth 2.4 km along the lap under every road point, invented a 549 m valley and
built a deck with no fill over real ground (kn5_ground_check road-over-ground p95 0.60 m; replication 14.6 m). Now the
projection records the permutation (``source_index``) and ``in_local_order`` applies it."""

import json
import math
import tempfile
from pathlib import Path

from scripts.geometry import projection

LON0, LAT0 = -103.8946, 39.735


def _ring(n=16, r_m=300.0):
    """A closed n-gon of lon/lat around (LON0, LAT0), radius r_m; the closing vertex repeats the first."""
    m_lon, m_lat = projection._meters_per_degree(LAT0)
    pts = [(LON0 + r_m * math.cos(2 * math.pi * i / n) / m_lon, LAT0 + r_m * math.sin(2 * math.pi * i / n) / m_lat)
           for i in range(n)]
    return pts + [pts[0]]


def _project(td: Path, route: dict | None, n=16):
    proj = td / "proj"
    (proj / "data").mkdir(parents=True)
    ring = _ring(n)
    (proj / "data" / "centerline.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [{
        "type": "Feature", "properties": {"kind": "full", "widths_m": [8.0 + i * 0.1 for i in range(len(ring))]},
        "geometry": {"type": "LineString", "coordinates": [list(p) for p in ring]}}]}), encoding="utf-8")
    z_smooth = [1500.0 + i for i in range(n)]           # distinct per vertex: a rotation is visible in Y
    z_raw = [v + 0.25 for v in z_smooth]
    (proj / "data" / "centerline.elevation.json").write_text(json.dumps({
        "z_raw_m": z_raw + [z_raw[0]], "z_smooth_m": z_smooth + [z_smooth[0]]}), encoding="utf-8")
    cfg = {"name": "t", "slug": "t", "location": {"lat": LAT0, "lon": LON0}, "source": {"type": "kml"}, "loop": True,
           "default_width_m": 8.0, "origin": "centroid", "surfaces": {}, "layouts": [], "lighting": {},
           "true_north_rotation_deg": 0.0}
    if route:
        cfg["route"] = route
    (proj / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    projection.build(proj)
    return proj, ring, z_raw + [z_raw[0]], z_smooth + [z_smooth[0]]


def test_start_at_records_the_rotation_and_in_local_order_undoes_it():
    with tempfile.TemporaryDirectory() as td:
        ring = _ring()
        k = 5
        proj, ring, z_raw, z_smooth = _project(Path(td), {"start_at": [ring[k][1], ring[k][0]]})
        loc = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
        assert loc["route_orientation"] == {"reversed": False, "rotated_by_points": k,
                                            "_doc": loc["route_orientation"]["_doc"]}
        idx = loc["source_index"]
        assert len(idx) == len(ring) == len(loc["points_xyz_m"])
        assert idx[0] == k and idx[-1] == k and idx[:len(ring) - 1] == list(range(k, 16)) + list(range(k))
        e0 = loc["origin"]["elev_m"]
        # every local point carries the elevation of ITS source point (projection re-orders z with the coords) …
        for i, p in enumerate(loc["points_xyz_m"]):
            assert math.isclose(p[1] + e0, z_smooth[idx[i]], abs_tol=0.011), (i, p, idx[i])
        # … and a per-point array from the elevation file, mapped through in_local_order, lines up with the local line
        zr_local = projection.in_local_order(loc, z_raw)
        for i, p in enumerate(loc["points_xyz_m"]):
            assert math.isclose(zr_local[i] - 0.25, p[1] + e0, abs_tol=0.011)
        # the bug: the bare-index pairing is off by the rotation at every point but the ones k apart
        off = sum(1 for i, p in enumerate(loc["points_xyz_m"]) if abs(z_raw[i] - 0.25 - (p[1] + e0)) > 0.5)
        assert off == len(ring), off


def test_reverse_and_start_at_compose_in_the_recorded_index():
    with tempfile.TemporaryDirectory() as td:
        ring = _ring()
        k = 3
        proj, ring, z_raw, _z = _project(Path(td), {"reverse": True, "start_at": [ring[k][1], ring[k][0]]})
        loc = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
        assert loc["route_orientation"]["reversed"] is True
        idx = loc["source_index"]
        assert idx[0] == k and idx[-1] == k and idx[1] == (k - 1) % 16, idx[:4]   # reversed: the lap runs the other way
        e0 = loc["origin"]["elev_m"]
        zr_local = projection.in_local_order(loc, z_raw)
        for i, p in enumerate(loc["points_xyz_m"]):
            assert math.isclose(zr_local[i] - 0.25, p[1] + e0, abs_tol=0.011)


def test_no_route_orientation_writes_no_index_and_in_local_order_is_the_identity():
    with tempfile.TemporaryDirectory() as td:
        proj, _ring_, z_raw, _z = _project(Path(td), None)
        loc = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
        assert "source_index" not in loc and "route_orientation" not in loc, "an unrotated file stays byte-identical"
        assert projection.in_local_order(loc, z_raw) == z_raw
        assert projection.in_local_order({}, [1, 2, 3]) == [1, 2, 3]


def test_in_local_order_leaves_a_length_mismatch_to_the_caller():
    loc = {"source_index": [2, 0, 1]}
    assert projection.in_local_order(loc, [10, 20, 30]) == [30, 10, 20]
    assert projection.in_local_order(loc, [10, 20]) == [10, 20], "the caller's own length guard decides"
    assert projection.in_local_order({"source_index": [0, 5, 1]}, [1, 2, 3]) == [1, 2, 3], "an index out of range: identity"
