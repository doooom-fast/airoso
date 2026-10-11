"""route.exclude_ids — the opt-in route key that drops OSM ways from the name / ``ref:`` matches.

A ``ref:`` (or name) match takes BOTH carriageways of a divided road and the stitcher keeps the shorter
side wherever the road splits, which can be the side signed the other way: the Lariat's exit 259
(42005706, 84 m, south-west-bound, against the lap) and 19th St's ramp terminal (533500102, eastbound).
These pin: no key = exactly the old behaviour; the exclusion is applied at parse time (query,
fingerprint and snapshot unchanged); contradictions and stale ids fail loudly; and the stage, run
offline from a snapshot, takes the other carriageway. Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
import urllib.request
from pathlib import Path

from scripts.gps import centerline, overpass


def _way(wid, pts, **tags):
    return {"type": "way", "id": wid, "tags": tags, "geometry": [{"lon": lo, "lat": la} for lo, la in pts]}


PAYLOAD = {"elements": [
    _way(1, [(0.0, 0.0), (1.0, 0.0)], highway="secondary", ref="US 40"),
    _way(2, [(1.0, 0.0), (2.0, 0.0)], highway="secondary", ref="I 70 BUS;US 40", oneway="yes"),
    _way(3, [(2.0, 0.1), (1.0, 0.1)], highway="secondary", ref="I 70 BUS;US 40", oneway="yes"),
    _way(4, [(5.0, 5.0), (6.0, 5.0)], highway="motorway", ref="I 70"),
    _way(5, [(0.0, 1.0), (1.0, 1.0)], highway="residential", name="Paradise Road"),
    _way(6, [(1.0, 1.0), (2.0, 1.0)], highway="trunk_link"),
]}
NAMES = ["Paradise Road", "ref:US 40", "id:6"]


def test_no_key_is_exactly_the_old_behaviour():
    old = overpass._parse_payload(PAYLOAD, NAMES)
    assert overpass._parse_payload(PAYLOAD, NAMES, exclude_ids=None) == old
    assert overpass._parse_payload(PAYLOAD, NAMES, exclude_ids=[]) == old
    assert len(old["ref:US 40"]) == 3 and len(old["Paradise Road"]) == 1 and len(old["id:6"]) == 1


def test_exclusion_drops_the_way_from_ref_and_name_matches():
    out = overpass._parse_payload(PAYLOAD, NAMES, exclude_ids=[3, 5])
    assert len(out["ref:US 40"]) == 2
    assert [(0.0, 0.0), (1.0, 0.0)] in out["ref:US 40"] and [(2.0, 0.1), (1.0, 0.1)] not in out["ref:US 40"]
    assert out["Paradise Road"] == []
    assert len(out["id:6"]) == 1


def test_excluding_a_requested_id_is_a_contradiction():
    try:
        overpass._parse_payload(PAYLOAD, NAMES, exclude_ids=[6])
    except ValueError as e:
        assert "also requested by an id: entry" in str(e)
    else:
        raise AssertionError("excluding an id: way must raise")


def test_bad_values_raise():
    for bad in ("42005706", [True], [0], [-3], ["3"], [3.5], 3):
        try:
            overpass.exclude_set(NAMES, bad)
        except ValueError:
            continue
        raise AssertionError(f"exclude_ids={bad!r} must raise")


def test_a_stale_exclusion_fails_loudly():
    try:
        overpass._parse_payload(PAYLOAD, NAMES, exclude_ids=[3, 999])
    except SystemExit as e:
        assert "999" in str(e) and "stale" in str(e)
    else:
        raise AssertionError("an excluded id missing from the snapshot must fail")


def test_query_and_fingerprint_do_not_depend_on_the_exclusion():
    """Applied at parse time: the cached snapshot (keyed by the query) serves both, untouched."""
    bbox = (39.0, -105.0, 39.1, -104.9)
    q = overpass.build_query(bbox, NAMES)
    fp = hashlib.sha256(q.encode()).hexdigest()[:16]
    with tempfile.TemporaryDirectory() as t:
        cache = Path(t) / "osm.cache.json"
        cache.write_text(json.dumps({"query_fingerprint": fp, "fetched_utc": "x", "payload": PAYLOAD}), encoding="utf-8")
        before = cache.read_bytes()
        saved = urllib.request.urlopen

        def _blocked(*a, **k):
            raise AssertionError("network used")

        urllib.request.urlopen = _blocked
        try:
            plain = overpass.fetch_ways(bbox, NAMES, cache=cache)
            excl = overpass.fetch_ways(bbox, NAMES, cache=cache, exclude_ids=[3])
        finally:
            urllib.request.urlopen = saved
        assert cache.read_bytes() == before
        assert len(plain["ref:US 40"]) == 3 and len(excl["ref:US 40"]) == 2


def _offset(lat0):
    m_lat = 111132.954 - 559.822 * math.cos(2 * math.radians(lat0))
    m_lon = 111412.84 * math.cos(math.radians(lat0))
    return m_lon, m_lat


def _project(tmp: Path, exclude):
    """One road, ref 'US 40', splitting into a divided pair: the SHORT side (way 12, straight, 100 m)
    and the long side (way 13, bowed 5 m north). Open route, so the stage keeps the whole road."""
    lat0, lon0 = 39.70, -105.20
    m_lon, m_lat = _offset(lat0)

    def ll(x, y):
        return (lon0 + x / m_lon, lat0 + y / m_lat)

    elements = [
        _way(11, [ll(0, 0), ll(100, 0)], highway="secondary", ref="US 40"),
        _way(12, [ll(100, 0), ll(200, 0)], highway="secondary", ref="US 40", oneway="yes"),
        _way(13, [ll(200, 0), ll(150, 5), ll(100, 0)], highway="secondary", ref="US 40", oneway="yes"),
        _way(14, [ll(200, 0), ll(300, 0)], highway="secondary", ref="US 40"),
    ]
    bbox = [39.69, -105.21, 39.71, -105.19]
    cfg = {"name": "t", "slug": "t", "location": {"lat": lat0, "lon": lon0, "timezone": "UTC"},
           "source": {"type": "osm"}, "loop": False, "default_width_m": 7.0, "origin": "centroid",
           "surfaces": {}, "layouts": [], "lighting": {},
           "route": {"bbox": bbox, "roads": ["ref:US 40"], "start_at": [lat0, lon0]}}
    if exclude is not None:
        cfg["route"]["exclude_ids"] = exclude
    (tmp / "data").mkdir(parents=True, exist_ok=True)
    (tmp / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    fp = hashlib.sha256(overpass.build_query(tuple(bbox), ["ref:US 40"]).encode()).hexdigest()[:16]
    (tmp / "data" / "osm.cache.json").write_text(json.dumps({"query_fingerprint": fp, "fetched_utc": "x",
                                                             "payload": {"elements": elements}}), encoding="utf-8")
    return ll


def _run(exclude):
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        ll = _project(tmp, exclude)
        saved = urllib.request.urlopen

        def _blocked(*a, **k):
            raise AssertionError("network used")

        urllib.request.urlopen = _blocked
        try:
            out, stats = centerline.build_centerline(tmp)
        finally:
            urllib.request.urlopen = saved
        feat = json.loads(out.read_text(encoding="utf-8"))["features"][0]
        return feat, ll


def test_the_stage_takes_the_other_carriageway_offline():
    plain, ll = _run(None)
    lat_mid = ll(150, 5)[1]
    lats = [c[1] for c in plain["geometry"]["coordinates"]]
    assert max(lats) < ll(0, 1)[1]                        # the short, straight side
    assert "exclude_ids" not in plain["properties"]       # no key -> no property: output unchanged
    excl, _ = _run([12])
    lats = [c[1] for c in excl["geometry"]["coordinates"]]
    assert max(lats) > ll(0, 4)[1] and max(lats) <= lat_mid + 1e-9   # bowed side, way 13
    assert excl["properties"]["exclude_ids"] == [12]
    assert excl["properties"]["length_m"] > plain["properties"]["length_m"]
