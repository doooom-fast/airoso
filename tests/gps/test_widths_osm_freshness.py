"""widths_from_osm: a mirror fallback says which mirror answered and how old its OSM data is, and a live
answer older than ``route.osm_max_age_days`` is never written to the width snapshot unless forced.

2026-10-11: overpass.kumi.systems was serving OSM as of 2026-07-28 while overpass-api.de was minutes
old. ``_overpass`` fell back to it without a word whenever overpass-api.de failed (on this machine,
every time, until the TLS fix), and ``fetch_ways`` cached July-era tags under a current fingerprint.
The Lariat's own July snapshot holds OSM as of 2026-07-02, fetched 07-27. These pin: the log names
the mirror and its ``osm3s.timestamp_osm_base``; a stale mirror is skipped for a fresh one; with none
fresh, the snapshot is refused (SystemExit, nothing written) unless ``allow_stale``; a missing
timestamp counts as stale; ``max_age_days=None`` = no limit; a snapshot already on disk is used
offline whatever its age; the config key and CLI flags reach ``fetch_ways``. No network.
Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.gps import widths_from_osm as wfo

PRIMARY, KUMI, MAILRU = wfo.MIRRORS
BBOX = (39.70, -105.25, 39.75, -105.20)


def _ts(days_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _payload(days_ago: float | None, *, highway: str = "secondary") -> dict:
    p = {"version": 0.6, "elements": [
        {"type": "way", "id": 119006778, "tags": {"highway": highway, "lanes": "2", "oneway": "yes"},
         "nodes": [1, 2], "geometry": [{"lon": -105.22, "lat": 39.72}, {"lon": -105.21, "lat": 39.73}]}]}
    if days_ago is not None:
        p["osm3s"] = {"timestamp_osm_base": _ts(days_ago), "copyright": "OSM contributors, ODbL"}
    return p


def _fail(url: str) -> Exception:
    return urllib.error.URLError(f"certificate verify failed ({url.split('/')[2]})")


def _run(answers: dict, **kw):
    """Call fetch_ways with urlopen answering per mirror: a dict = that payload, an Exception = raised.
    Returns (ways or the SystemExit, stdout text, urls hit in order)."""
    hits: list[str] = []

    def fake_urlopen(req, *a, **k):
        url = req.full_url
        hits.append(url)
        ans = answers.get(url, _fail(url))
        if isinstance(ans, Exception):
            raise ans
        return io.BytesIO(json.dumps(ans).encode())

    saved_open, saved_pause = urllib.request.urlopen, wfo._RETRY_PAUSE_S
    urllib.request.urlopen, wfo._RETRY_PAUSE_S = fake_urlopen, 0.0
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            try:
                res = wfo.fetch_ways(BBOX, **kw)
            except SystemExit as e:
                res = e
    finally:
        urllib.request.urlopen, wfo._RETRY_PAUSE_S = saved_open, saved_pause
    return res, out.getvalue(), hits


def test_primary_answer_is_snapshotted_with_its_mirror_and_data_timestamp():
    with tempfile.TemporaryDirectory() as t:
        cache = Path(t) / "osm.widths.cache.json"
        fresh = _payload(0.01)
        ways, log, hits = _run({PRIMARY: fresh}, cache=cache)
        assert [w["id"] for w in ways] == [119006778] and hits == [PRIMARY]
        assert "overpass-api.de answered, primary" in log and fresh["osm3s"]["timestamp_osm_base"] in log
        snap = json.loads(cache.read_text(encoding="utf-8"))
        assert snap["source"] == PRIMARY and snap["osm_base"] == fresh["osm3s"]["timestamp_osm_base"]
        assert "stale_allowed" not in snap and snap["payload"] == fresh


def test_a_fallback_names_the_mirror_and_its_data_date():
    with tempfile.TemporaryDirectory() as t:
        cache = Path(t) / "osm.widths.cache.json"
        kumi = _payload(0.2)
        ways, log, hits = _run({KUMI: kumi}, cache=cache)
        assert hits == [PRIMARY, PRIMARY, KUMI]
        assert log.count("overpass-api.de failed") == 2 and "certificate verify failed" in log
        assert "overpass.kumi.systems answered, FALLBACK mirror (not overpass-api.de)" in log
        assert kumi["osm3s"]["timestamp_osm_base"] in log
        assert json.loads(cache.read_text(encoding="utf-8"))["source"] == KUMI


def test_a_stale_mirror_is_passed_over_for_a_fresh_one():
    with tempfile.TemporaryDirectory() as t:
        cache = Path(t) / "osm.widths.cache.json"
        july, fresh = _payload(75, highway="primary"), _payload(0.1)
        ways, log, hits = _run({KUMI: july, MAILRU: fresh}, cache=cache)
        assert hits == [PRIMARY, PRIMARY, KUMI, MAILRU]          # a stale mirror is not retried
        assert "overpass.kumi.systems fails the 7-day freshness limit" in log
        assert july["osm3s"]["timestamp_osm_base"] in log
        snap = json.loads(cache.read_text(encoding="utf-8"))
        assert snap["source"] == MAILRU and ways[0]["highway"] == "secondary"


def test_refuses_to_snapshot_when_no_mirror_is_fresh_and_leaves_the_old_file_alone():
    with tempfile.TemporaryDirectory() as t:
        cache = Path(t) / "osm.widths.cache.json"
        cache.write_text(json.dumps({"query_fingerprint": "another-bbox", "payload": {}}), encoding="utf-8")
        before = cache.read_bytes()
        older, newer = _payload(75, highway="primary"), _payload(40, highway="primary")
        res, log, _ = _run({KUMI: older, MAILRU: newer}, cache=cache)
        assert isinstance(res, SystemExit), res
        msg = str(res)
        assert "REFUSING to snapshot osm.widths.cache.json" in msg
        assert MAILRU in msg and newer["osm3s"]["timestamp_osm_base"] in msg     # the freshest stale one
        assert "7-day limit" in msg and "--allow-stale-osm" in msg
        assert cache.read_bytes() == before


def test_allow_stale_snapshots_it_and_marks_it():
    with tempfile.TemporaryDirectory() as t:
        cache = Path(t) / "osm.widths.cache.json"
        older, newer = _payload(75, highway="primary"), _payload(40, highway="primary")
        ways, log, _ = _run({KUMI: older, MAILRU: newer}, cache=cache, allow_stale=True)
        assert ways[0]["highway"] == "primary"
        assert "WARNING" in log and "snapshotting it anyway" in log
        snap = json.loads(cache.read_text(encoding="utf-8"))
        assert snap["stale_allowed"] is True and snap["source"] == MAILRU
        assert snap["osm_base"] == newer["osm3s"]["timestamp_osm_base"]


def test_a_missing_data_timestamp_counts_as_stale():
    with tempfile.TemporaryDirectory() as t:
        cache = Path(t) / "osm.widths.cache.json"
        res, log, hits = _run({PRIMARY: _payload(None)}, cache=cache)
        assert isinstance(res, SystemExit) and "MISSING" in str(res)
        assert not cache.exists()
        assert hits[0] == PRIMARY and "timestamp MISSING" in log


def test_the_limit_is_configurable_and_none_means_no_limit():
    with tempfile.TemporaryDirectory() as t:
        july = _payload(75, highway="primary")
        ways, _, _ = _run({KUMI: july}, cache=Path(t) / "a.json", max_age_days=100)
        assert ways and "stale_allowed" not in json.loads((Path(t) / "a.json").read_text(encoding="utf-8"))
        ways, log, hits = _run({KUMI: july}, cache=Path(t) / "b.json", max_age_days=None)
        assert ways and hits == [PRIMARY, PRIMARY, KUMI] and "FALLBACK" in log
        res, _, _ = _run({KUMI: july}, cache=Path(t) / "c.json", max_age_days=30)
        assert isinstance(res, SystemExit) and "30-day limit" in str(res)


def test_a_snapshot_on_disk_is_used_offline_whatever_its_age():
    with tempfile.TemporaryDirectory() as t:
        cache = Path(t) / "osm.widths.cache.json"
        _run({PRIMARY: _payload(0.01)}, cache=cache)
        snap = json.loads(cache.read_text(encoding="utf-8"))
        snap["payload"]["osm3s"]["timestamp_osm_base"] = snap["osm_base"] = _ts(400)
        cache.write_text(json.dumps(snap), encoding="utf-8")
        before = cache.read_bytes()
        ways, log, hits = _run({}, cache=cache)
        assert hits == [] and [w["id"] for w in ways] == [119006778]
        assert "using cached snapshot" in log and snap["osm_base"] in log and "overpass-api.de" in log
        assert cache.read_bytes() == before


def test_without_a_cache_stale_data_only_warns():
    ways, log, _ = _run({KUMI: _payload(75)}, cache=None)
    assert ways and "WARNING" in log and "snapshotting" not in log


def test_route_key_default_and_validation():
    assert wfo.max_age_from_route({}) == wfo.OSM_MAX_AGE_DAYS == 7.0
    assert wfo.max_age_from_route({"osm_max_age_days": 30}) == 30.0
    for bad in (0, -1, "7", True, [7]):
        try:
            wfo.max_age_from_route({"osm_max_age_days": bad})
        except ValueError:
            continue
        raise AssertionError(f"osm_max_age_days={bad!r} must be refused")


def test_osm_age_days_reads_the_overpass_timestamp():
    now = datetime(2026, 10, 11, 19, 28, 1, tzinfo=timezone.utc)
    assert wfo.osm_age_days({"osm3s": {"timestamp_osm_base": "2026-07-28T02:16:18Z"}}, now) > 75
    assert wfo.osm_age_days({"osm3s": {"timestamp_osm_base": "2026-10-11T19:28:01Z"}}, now) == 0.0
    assert wfo.osm_age_days({}, now) is None
    assert wfo.osm_age_days({"osm3s": {"timestamp_osm_base": "yesterday"}}, now) is None


def test_cli_flags_and_the_config_key_reach_fetch_ways():
    seen = {}

    def fake_fetch(bbox, cache=None, **kw):
        seen.update(kw)
        raise RuntimeError("stop here")

    with tempfile.TemporaryDirectory() as t:
        proj = Path(t)
        (proj / "data").mkdir()
        line = {"type": "LineString", "coordinates": [[-105.22, 39.72], [-105.21, 39.73]]}
        (proj / "data" / "centerline.geojson").write_text(json.dumps({"type": "Feature", "geometry": line}))
        (proj / "data" / "centerline.local.json").write_text(json.dumps({"widths_m": [6.5, 6.5]}))
        cfg = {"route": {"osm_max_age_days": 21}}
        (proj / "track.config.json").write_text(json.dumps(cfg))
        saved = wfo.fetch_ways
        wfo.fetch_ways = fake_fetch
        try:
            for argv, want in (([str(proj)], {"max_age_days": 21.0, "allow_stale": False}),
                               ([str(proj), "--allow-stale-osm"], {"max_age_days": 21.0, "allow_stale": True}),
                               ([str(proj), "--max-osm-age-days", "3"], {"max_age_days": 3.0, "allow_stale": False})):
                seen.clear()
                try:
                    wfo.main(argv)
                except RuntimeError:
                    pass
                assert seen == want, (argv, seen)
        finally:
            wfo.fetch_ways = saved
