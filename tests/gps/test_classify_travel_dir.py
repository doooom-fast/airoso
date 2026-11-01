"""scripts.gps.classify records each network edge's direction of travel — only when the config asks for it.

network.py stores an edge in node-id order, not travel order; an OSM motorway way is drawn the way it is driven. With
``network.reference_line`` declared (scripts.geometry.network_reference drives one carriageway), classify votes each
edge's tangent against the nearest way's segment and writes ``travel_dir`` (+1 = vertex order is travel, -1 =
reversed, 0 = undecided) and ``travel_votes``. Without the block nothing new is written (the freeway is the only
network track; every other output stays byte-identical). Overpass is replaced by a stub returning two oneway ways.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path


def _project(tmp: Path, decl: bool) -> Path:
    cfg = {"name": "t", "slug": "t", "loop": False, "default_width_m": 14.0, "origin": "centroid",
           "surfaces": {}, "layouts": [{"id": "freeroam"}], "lighting": {},
           "location": {"lat": 32.77, "lon": -117.0, "timezone": "America/Los_Angeles"},
           "source": {"type": "osm-network"}, "network": {"class_widths_m": {"motorway": 16.0, "ramp": 8.5}}}
    if decl:
        cfg["network"]["reference_line"] = {"ref": "I 8", "direction": "eastbound"}
    (tmp / "data").mkdir(parents=True)
    (tmp / "track.config.json").write_text(json.dumps(cfg))
    lon = [-117.0 + 0.0005 * i for i in range(11)]
    fc = {"type": "FeatureCollection", "properties": {"ref_lon": -116.9975, "ref_lat": 32.77},
          "features": [
              # edge 0 stored west -> east along the eastbound way; edge 1 stored west -> east along the WESTBOUND way
              {"type": "Feature", "properties": {"id": 0, "length_m": 470.0},
               "geometry": {"type": "LineString", "coordinates": [[x, 32.7700] for x in lon]}},
              {"type": "Feature", "properties": {"id": 1, "length_m": 470.0},
               "geometry": {"type": "LineString", "coordinates": [[x, 32.7703] for x in lon]}}]}
    (tmp / "data" / "network.geojson").write_text(json.dumps(fc))
    return tmp


def _ways(q, retries=4):
    lon = [-117.0 + 0.0005 * i for i in range(11)]
    return {"elements": [
        {"type": "way", "id": 1, "tags": {"highway": "motorway", "ref": "I 8", "lanes": "4"},
         "geometry": [{"lon": x, "lat": 32.7700} for x in lon]},                 # eastbound: drawn west -> east
        {"type": "way", "id": 2, "tags": {"highway": "motorway", "ref": "I 8", "lanes": "4"},
         "geometry": [{"lon": x, "lat": 32.7703} for x in reversed(lon)]}]}      # westbound: drawn east -> west


def _classify(decl: bool) -> list[dict]:
    import scripts.trace.osm as tosm
    from scripts.gps.classify import classify
    saved = tosm._post
    tosm._post = _ways
    try:
        with tempfile.TemporaryDirectory() as td:
            p = _project(Path(td), decl)
            classify(p)
            return [f["properties"] for f in json.loads((p / "data" / "network.geojson").read_text())["features"]]
    finally:
        tosm._post = saved


def test_travel_dir_is_the_osm_ways_order_when_a_reference_line_is_declared():
    e0, e1 = _classify(True)
    assert e0["name"] == e1["name"] == "I 8" and not e0["is_ramp"]
    assert e0["travel_dir"] == 1 and e0["travel_votes"][1] == 0 and e0["travel_votes"][0] > 0
    assert e1["travel_dir"] == -1 and e1["travel_votes"][0] == 0 and e1["travel_votes"][1] > 0


def test_nothing_new_is_written_without_the_declaration():
    e0, e1 = _classify(False)
    assert "travel_dir" not in e0 and "travel_votes" not in e1
    assert e0["name"] == "I 8" and e0["width_m"] == round(4 * 3.66 + 3.5, 2)
