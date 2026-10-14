"""tools/fetch_buildings_cache.py — OSM footprints in the assembler's buildings-cache schema, 7-day guarded (ledger 0054
P0 step 7). No network: urlopen is replaced for each call.

- the cache is a bare list of {building, levels (= building:levels), height, geom [[lon, lat]]} — the schema
  scripts-v021 build_loop_blend.build_buildings reads (the committed v0.18.0 cache has exactly these keys);
- the provenance sits beside it (server, OSM data timestamp, query, md5) with the comparison against an old cache;
- a stale (or untimestamped) answer is refused and nothing is written; the old cache is never the output;
- the committed expansion cache covers the new box and its provenance says it is fresh and from a verified fetch.
"""
from __future__ import annotations

import contextlib
import hashlib
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

TRACK = ROOT / "tracks" / "san-diego-lake-murray"
PRIMARY = wfo.MIRRORS[0]


def _tool():
    spec = importlib.util.spec_from_file_location("_tool_fetch_buildings", ROOT / "tools" / "fetch_buildings_cache.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _payload(days_ago):
    p = {"elements": [
        {"type": "way", "id": 1, "tags": {"building": "house", "building:levels": "2"},
         "geometry": [{"lon": -117.0, "lat": 32.8}, {"lon": -117.0001, "lat": 32.8}, {"lon": -117.0001, "lat": 32.8001},
                      {"lon": -117.0, "lat": 32.8}]},
        {"type": "way", "id": 2, "tags": {"building": "yes", "height": "12"},
         "geometry": [{"lon": -117.01, "lat": 32.81}, {"lon": -117.0101, "lat": 32.81},
                      {"lon": -117.0101, "lat": 32.8101}, {"lon": -117.01, "lat": 32.81}]},
        {"type": "node", "id": 9, "lat": 32.8, "lon": -117.0}]}
    if days_ago is not None:
        ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
        p["osm3s"] = {"timestamp_osm_base": ts}
    return p


def _run(answers, argv):
    def fake_urlopen(req, *a, **k):
        ans = answers.get(req.full_url, urllib.error.URLError("down"))
        if isinstance(ans, Exception):
            raise ans
        return io.BytesIO(json.dumps(ans).encode())

    mod = _tool()
    saved_open, saved_pause = urllib.request.urlopen, wfo._RETRY_PAUSE_S
    urllib.request.urlopen, wfo._RETRY_PAUSE_S = fake_urlopen, 0.0
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            rc = mod.main(argv)
    finally:
        urllib.request.urlopen, wfo._RETRY_PAUSE_S = saved_open, saved_pause
    return rc, out.getvalue()


def test_schema_provenance_and_compare():
    with tempfile.TemporaryDirectory() as t:
        old = Path(t) / "old.json"
        old.write_text(json.dumps([{"building": "house", "levels": "2", "height": None,
                                    "geom": [[-117.0, 32.8], [-117.0001, 32.8], [-117.0001, 32.8001], [-117.0, 32.8]]},
                                   {"building": "yes", "levels": None, "height": None,
                                    "geom": [[-117.02, 32.79], [-117.0201, 32.79], [-117.02, 32.7901]]}]),
                       encoding="utf-8")
        out = Path(t) / "new.json"
        rc, log = _run({PRIMARY: _payload(0.01)}, ["--bbox", "32.7", "-117.1", "32.9", "-116.9", "--out", str(out),
                                                    "--compare", str(old)])
        assert rc == 0, log
        cache = json.loads(out.read_text(encoding="utf-8"))
        assert cache == [{"building": "house", "levels": "2", "height": None,
                          "geom": [[-117.0, 32.8], [-117.0001, 32.8], [-117.0001, 32.8001], [-117.0, 32.8]]},
                         {"building": "yes", "levels": None, "height": "12",
                          "geom": [[-117.01, 32.81], [-117.0101, 32.81], [-117.0101, 32.8101], [-117.01, 32.81]]}]
        prov = json.loads(Path(str(out) + ".provenance.json").read_text(encoding="utf-8"))
        assert prov["source"] == PRIMARY and prov["osm_base"] and prov["count"] == 2
        assert prov["cache_md5"] == hashlib.md5(out.read_bytes()).hexdigest()
        assert prov["compare"]["old_count"] == 2 and prov["compare"]["old_still_exact"] == 1


def test_stale_is_refused_and_the_old_cache_is_never_the_output():
    with tempfile.TemporaryDirectory() as t:
        out = Path(t) / "new.json"
        rc, log = _run({PRIMARY: _payload(30)}, ["--bbox", "32.7", "-117.1", "32.9", "-116.9", "--out", str(out)])
        assert rc == 1 and "REFUSING" in log and not out.exists()
        rc, log = _run({PRIMARY: _payload(None)}, ["--bbox", "32.7", "-117.1", "32.9", "-116.9", "--out", str(out)])
        assert rc == 1 and not out.exists()
        rc, log = _run({PRIMARY: _payload(0.1)}, ["--bbox", "32.7", "-117.1", "32.9", "-116.9", "--out", str(out),
                                                   "--compare", str(out)])
        assert rc == 2


def test_committed_expansion_cache_is_fresh_verified_and_in_the_assemblers_schema():
    p = TRACK / "data" / "buildings.expansion.cache.json"
    prov = json.loads(Path(str(p) + ".provenance.json").read_text(encoding="utf-8"))
    assert prov["bbox_swne"] == [32.755, -117.115, 32.85, -116.985]
    assert prov["max_age_days"] == 7.0 and prov["osm_age_days"] < 1.0 and "stale_allowed" not in prov
    assert prov["cache_md5"] == hashlib.md5(p.read_bytes()).hexdigest()
    cache = json.loads(p.read_text(encoding="utf-8"))
    assert len(cache) == prov["count"] and all(set(b) == {"building", "levels", "height", "geom"} for b in cache)
    assert max(pt[1] for b in cache for pt in b["geom"]) > 32.84            # reaches north past the old 32.808
    # the installed cache is untouched (the v0.18.0 build reads it)
    old = (TRACK / "data" / "buildings.cache.json").read_bytes()
    assert hashlib.md5(old).hexdigest() == "9009eacb4a8d2284b280c31f5d2f172e"
