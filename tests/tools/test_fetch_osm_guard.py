"""tools/fetch_osm.py — the 7-day freshness guard (ledger 0054 P0 step 3, 2026-10-14).

It used to fall back across three Overpass servers with no staleness check; it now fetches through
``scripts.gps.widths_from_osm._overpass`` (TLS verified, every fallback printed) and refuses to WRITE an answer
whose OSM data is older than ``--max-age-days`` (or carries no timestamp) unless ``--allow-stale-osm``. No network:
urlopen is replaced for the duration of each call.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.gps import widths_from_osm as wfo  # noqa: E402

PRIMARY, KUMI, MAILRU = wfo.MIRRORS


def _tool():
    spec = importlib.util.spec_from_file_location("_tool_fetch_osm_guard", ROOT / "tools" / "fetch_osm.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _payload(days_ago):
    p = {"elements": [
        {"type": "way", "id": 7, "nodes": [1, 2], "tags": {"highway": "secondary", "name": "Waring Road",
                                                          "oneway": "yes"}},
        {"type": "node", "id": 1, "lon": -117.07, "lat": 32.79, "tags": {"highway": "traffic_signals"}},
        {"type": "node", "id": 2, "lon": -117.071, "lat": 32.791}]}
    if days_ago is not None:
        ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
        p["osm3s"] = {"timestamp_osm_base": ts}
    return p


def _run(answers, argv):
    hits = []

    def fake_urlopen(req, *a, **k):
        hits.append(req.full_url)
        ans = answers.get(req.full_url, urllib.error.URLError("down"))
        if isinstance(ans, Exception):
            raise ans
        return io.BytesIO(json.dumps(ans).encode())

    mod = _tool()
    saved_open, saved_pause = urllib.request.urlopen, wfo._RETRY_PAUSE_S
    urllib.request.urlopen, wfo._RETRY_PAUSE_S = fake_urlopen, 0.0
    err = io.StringIO()
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            try:
                res = mod.main(argv)
            except SystemExit as e:
                res = e
    finally:
        urllib.request.urlopen, wfo._RETRY_PAUSE_S = saved_open, saved_pause
    return res, hits, err.getvalue()


def test_a_fresh_primary_answer_is_written_with_its_provenance():
    with tempfile.TemporaryDirectory() as t:
        out = Path(t) / "osm.json"
        res, hits, _ = _run({PRIMARY: _payload(0.01)}, ["--bbox", "32.75", "-117.1", "32.85", "-117.0",
                                                         "--out", str(out), "--service"])
        assert not isinstance(res, SystemExit) and hits == [PRIMARY]
        d = json.loads(out.read_text(encoding="utf-8"))
        assert d["source"] == PRIMARY and d["osm_base"] and d["max_age_days"] == 7.0
        assert d["bbox"] == [32.75, -117.1, 32.85, -117.0] and "|service" in d["query"]
        assert d["nodes"] == {"1": [-117.07, 32.79], "2": [-117.071, 32.791]}
        assert d["node_tags"] == {"1": {"highway": "traffic_signals"}}
        assert d["ways"] == [{"id": 7, "nodes": [1, 2], "tags": {"highway": "secondary", "name": "Waring Road",
                                                                 "oneway": "yes"}}]
        assert "stale_allowed" not in d and len(d["query_fingerprint"]) == 16


def test_a_stale_mirror_is_passed_over_and_an_all_stale_answer_is_refused():
    with tempfile.TemporaryDirectory() as t:
        out = Path(t) / "osm.json"
        # the primary is down, kumi is 75 days behind, mail.ru is fresh: mail.ru's answer is written
        res, hits, _ = _run({KUMI: _payload(75), MAILRU: _payload(0.2)}, ["--out", str(out)])
        assert not isinstance(res, SystemExit) and hits[-1] == MAILRU
        assert json.loads(out.read_text(encoding="utf-8"))["source"] == MAILRU
        out.unlink()
        # every answer stale (or without a timestamp): nothing written, the script stops naming the limit
        res, hits, _ = _run({KUMI: _payload(75), MAILRU: _payload(None)}, ["--out", str(out)])
        assert isinstance(res, SystemExit) and "REFUSING" in str(res.code) and "7-day" in str(res.code)
        assert not out.exists()


def test_allow_stale_writes_and_records_it():
    with tempfile.TemporaryDirectory() as t:
        out = Path(t) / "osm.json"
        res, hits, err = _run({PRIMARY: _payload(30)}, ["--out", str(out), "--allow-stale-osm"])
        assert not isinstance(res, SystemExit)
        d = json.loads(out.read_text(encoding="utf-8"))
        assert d["stale_allowed"] is True and "WARNING" in err


def test_the_default_box_and_drivable_set_are_unchanged():
    mod = _tool()
    assert mod.BBOX == (32.7600, -117.0750, 32.8080, -116.9980)
    q = mod.query_for(mod.BBOX)
    assert "(32.76,-117.075,32.808,-116.998)" in q and "service" not in q and "living_street" in q
    # no urlopen of its own: every fetch goes through the guarded client
    src = (ROOT / "tools" / "fetch_osm.py").read_text(encoding="utf-8")
    assert "urlopen" not in src and "ENDPOINTS" not in src


def test_committed_expansion_snapshot_is_the_guarded_fresh_fetch():
    """tracks/san-diego-lake-murray/data/osm.expansion.json: the P0 step 3 fetch (bbox S 32.755 / W -117.115 /
    N 32.850 / E -116.985, service ways included), fresh at the time of fetching, never stale-allowed"""
    d = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "data" / "osm.expansion.json").read_text(
        encoding="utf-8"))
    assert d["bbox"] == [32.755, -117.115, 32.85, -116.985] and "|service" in d["query"]
    assert d["max_age_days"] == 7.0 and d["osm_age_days"] < 1.0 and "stale_allowed" not in d
    assert d["source"] in wfo.MIRRORS and d["osm_base"] and "verified" in d["tls"]
    assert d["node_count"] == len(d["nodes"]) and d["way_count"] == len(d["ways"])
    names = {w["tags"].get("name") for w in d["ways"]}
    assert {"Waring Road", "Princess View Drive", "Mission Gorge Road", "Jackson Drive", "College Avenue",
            "Navajo Road"} <= names
