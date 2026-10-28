"""scripts.gps.centerline.build_for_source — the gps stage honours track.config.json source.type (2026-10-28,
the ship chain's draft for every track: Sand Creek's KML and Milford's / High Plains' traced fixes used to need
their builders run by hand, because `python -m scripts.gps.centerline` knew only the OSM route).

Offline: a KML line and a from_track fixes file each become data/centerline.geojson in the pipeline format;
an aerial source is pointed at its own front-end; an unknown type is refused. The OSM path (Overpass) is
not exercised here. Plain ``test_*`` for tests/run_tests.py.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.gps import centerline as C

KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><name>lap</name><LineString><coordinates>
-104.9000,39.7800,0 -104.8990,39.7800,0 -104.8990,39.7810,0 -104.9000,39.7810,0 -104.9000,39.7800,0
</coordinates></LineString></Placemark></Document></kml>
"""


def _cfg(d: Path, source: dict, **extra):
    base = {"slug": "t", "name": "t", "version": "0.0.1", "loop": True, "default_width_m": 9.0,
            "location": {"lat": 39.78, "lon": -104.9, "timezone": "America/Denver"}, "origin": "centroid",
            "surfaces": {"road": "asphalt"}, "layouts": [{"id": "full"}], "lighting": {}, "source": source,
            "route": {"bbox": [39.77, -104.91, 39.79, -104.89]}}
    base.update(extra)
    (d / "track.config.json").write_text(json.dumps(base), encoding="utf-8")


def test_kml_source_builds_the_drawn_line():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "source").mkdir()
        (d / "source" / "lap.kml").write_text(KML, encoding="utf-8")
        _cfg(d, {"type": "kml", "kml": "source/lap.kml"})
        out, stats = C.build_for_source(d)
        assert out == d / "data" / "centerline.geojson" and out.is_file()
        fc = json.loads(out.read_text(encoding="utf-8"))
        full = next(f for f in fc["features"] if f["properties"]["kind"] == "full")
        assert full["properties"]["source"] == "kml-line" and full["properties"]["closed"] is True
        assert stats["points"] > 20 and 0.25 < stats["length_km"] < 0.4


def test_from_track_source_builds_from_the_fixes_file_closed_at_the_configs_width():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "source").mkdir()
        # a plain closed rectangle, 48 fixes about 9-11 m apart
        pts = []
        for k in range(12):
            pts.append((39.7800, -104.9000 + 0.0001 * k))
        for k in range(12):
            pts.append((39.7800 + 0.0001 * k, -104.8988))
        for k in range(12):
            pts.append((39.7812, -104.8988 - 0.0001 * k))
        for k in range(12):
            pts.append((39.7812 - 0.0001 * k, -104.9000))
        fixes = [{"t": i, "lat": la, "lon": lo} for i, (la, lo) in enumerate(pts)]
        (d / "source" / "fixes.json").write_text(json.dumps(fixes), encoding="utf-8")
        _cfg(d, {"type": "from_track", "track": "source/fixes.json"}, default_width_m=11.0)
        out, _stats = C.build_for_source(d)
        assert out.is_file()
        fc = json.loads(out.read_text(encoding="utf-8"))
        full = next(f for f in fc["features"] if f["properties"]["kind"] == "full")
        coords = full["geometry"]["coordinates"]
        assert coords[0] == coords[-1], "closed because the config says loop"
        assert {round(w, 2) for w in full["properties"]["widths_m"]} == {11.0}, "default_width_m, no per-fix widths"


def test_aerial_points_at_its_front_end_and_unknown_types_are_refused():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _cfg(d, {"type": "aerial", "screenshot": "source/x.png"})
        try:
            C.build_for_source(d)
            raise AssertionError("aerial must not be built by the gps stage")
        except SystemExit as e:
            assert "scripts.aerial.build_aerial" in str(e)
        _cfg(d, {"type": "lidar-scan"})
        try:
            C.build_for_source(d)
            raise AssertionError("an unknown source type must be refused")
        except SystemExit as e:
            assert "lidar-scan" in str(e) and "from_track" in str(e)
        _cfg(d, {"type": "from_track"})
        try:
            C.build_for_source(d)
            raise AssertionError("from_track without a fixes file must be refused")
        except SystemExit as e:
            assert "source.track" in str(e)
