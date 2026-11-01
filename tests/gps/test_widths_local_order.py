"""scripts.gps.widths_from_osm writes its per-vertex widths in centerline.local.json's ORDER (2026-11-01).

The widths are computed per centerline.geojson vertex; projection re-orders the local ring to route.start_at /
route.reverse after the geojson is written and records the permutation (source_index, ledger 0060). Until this
change the stage wrote the arrays 1:1, so on a rotated ring every width sat k vertices off (High Plains: 815 of
1,074). Now it applies the recorded permutation once and marks ``widths_order: "local"``; an unrotated ring (no
source_index) is the identity. Offline: the Overpass answer is a cache file under the query's own fingerprint.
Plain ``test_*`` for tests/run_tests.py.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from scripts.geometry.projection import _meters_per_degree, in_local_order
from scripts.gps import widths_from_osm as wfo

LAT0, LON0 = 39.74, -105.22


def _ring():
    pts = [(float(x), 0.0) for x in range(0, 400, 4)] + [(400.0, float(y)) for y in range(0, 100, 4)]
    pts += [(400.0 - float(x), 100.0) for x in range(0, 400, 4)] + [(0.0, 100.0 - float(y)) for y in range(0, 100, 4)]
    pts.append(pts[0])
    return pts


def _project(tmp: Path, k: int) -> Path:
    mlon, mlat = _meters_per_degree(LAT0)
    ring = _ring()
    m = len(ring) - 1
    lonlat = [(LON0 + x / mlon, LAT0 + y / mlat) for x, y in ring]
    (tmp / "data").mkdir(parents=True)
    (tmp / "track.config.json").write_text(json.dumps({
        "slug": "t", "name": "t", "loop": True, "default_width_m": 6.0, "mirror_x": False,
        "route": {"width_profile": "urban", "osm_max_age_days": 1e9}}), encoding="utf-8")
    (tmp / "data" / "centerline.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"kind": "full", "closed": True},
         "geometry": {"type": "LineString", "coordinates": [list(p) for p in lonlat]}}]}), encoding="utf-8")
    local_pts = [ring[(i + k) % m] for i in range(m)] + [ring[k % m]]
    local = {"origin": {"lon": LON0, "lat": LAT0, "elev_m": 0.0},
             "points_xyz_m": [[x, 0.0, y] for x, y in local_pts], "widths_m": [6.0] * (m + 1)}
    if k:
        local["source_index"] = [(i + k) % m for i in range(m)] + [k % m]
    (tmp / "data" / "centerline.local.json").write_text(json.dumps(local), encoding="utf-8")
    # the Overpass answer: the south side a 4-lane primary, the north side a 2-lane residential, the ends tertiary
    def way(wid, pts, **tags):
        return {"type": "way", "id": wid, "tags": tags, "nodes": list(range(len(pts))),
                "geometry": [{"lon": LON0 + x / mlon, "lat": LAT0 + y / mlat} for x, y in pts]}
    elements = [way(1, [(0.0, 0.0), (400.0, 0.0)], highway="primary", lanes="4"),
                way(2, [(400.0, 0.0), (400.0, 100.0)], highway="tertiary"),
                way(3, [(400.0, 100.0), (0.0, 100.0)], highway="residential", lanes="2"),
                way(4, [(0.0, 100.0), (0.0, 0.0)], highway="tertiary")]
    lons = [p[0] for p in lonlat]; lats = [p[1] for p in lonlat]
    pad = 0.0015
    bbox = (min(lats) - pad, min(lons) - pad, max(lats) + pad, max(lons) + pad)
    q = (f'[out:json][timeout:120];(way["highway"~"^({wfo.DRIVABLE})(_link)?$"]'
         f'({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}););out geom;')
    (tmp / "data" / "osm.widths.cache.json").write_text(json.dumps({
        "query_fingerprint": hashlib.sha256(q.encode()).hexdigest()[:16], "fetched_utc": "2026-11-01T00:00:00Z",
        "source": "test", "payload": {"version": 0.6, "elements": elements,
                                      "osm3s": {"timestamp_osm_base": "2026-11-01T00:00:00Z"}}}), encoding="utf-8")
    return tmp


def _widths(p: Path):
    return json.loads((p / "data" / "centerline.local.json").read_text(encoding="utf-8"))


def test_widths_follow_the_recorded_permutation_and_say_so():
    with tempfile.TemporaryDirectory() as d0, tempfile.TemporaryDirectory() as d1:
        plain = _project(Path(d0), k=0)
        rotated = _project(Path(d1), k=37)
        wfo.build(plain)
        wfo.build(rotated)
        lp, lr = _widths(plain), _widths(rotated)
        assert lp["widths_order"] == "local" and lr["widths_order"] == "local"
        assert max(lp["widths_m"]) > min(lp["widths_m"]) + 2.0, "the two sides must differ for the order to show"
        # the rotated ring's widths are the plain ring's, re-ordered by its own recorded permutation: local vertex i
        # carries geojson vertex (i + 37)'s width, not geojson vertex i's
        assert lr["widths_m"] == in_local_order(lr, lp["widths_m"])
        assert lr["widths_base_m"] == in_local_order(lr, lp["widths_base_m"])
        assert lr["widths_m"] != lp["widths_m"]
