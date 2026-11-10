"""ledger 0075: with network.stable_snap an edge's ends are junction nodes, and a node's point can be a ramp's vertex at
a gore, so classify's travel vote reads a short edge's middle, never its ends (an 18.7 m I 8 eastbound piece came out
undecided, [1, 1], and network_reference refused the line). Overpass is a stub, as in test_classify_travel_dir."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

LON = [-117.0, -116.99995, -116.9999]          # a ~9.4 m mainline piece, stored west -> east


def _project(tmp: Path, stable: bool) -> Path:
    cfg = {"name": "t", "slug": "t", "loop": False, "default_width_m": 14.0, "origin": "centroid",
           "surfaces": {}, "layouts": [{"id": "freeroam"}], "lighting": {},
           "location": {"lat": 32.77, "lon": -117.0, "timezone": "America/Los_Angeles"},
           "source": {"type": "osm-network"},
           "network": {"class_widths_m": {"motorway": 16.0, "ramp": 8.5},
                       "reference_line": {"ref": "I 8", "direction": "eastbound"}}}
    if stable:
        cfg["network"]["stable_snap"] = True
    (tmp / "data").mkdir(parents=True)
    (tmp / "track.config.json").write_text(json.dumps(cfg))
    fc = {"type": "FeatureCollection", "properties": {"ref_lon": -117.0, "ref_lat": 32.77},
          "features": [{"type": "Feature", "properties": {"id": 0, "length_m": 9.4},
                        "geometry": {"type": "LineString", "coordinates": [[x, 32.77] for x in LON]}}]}
    (tmp / "data" / "network.geojson").write_text(json.dumps(fc))
    return tmp


def _ways(q, retries=4):
    return {"elements": [
        # I 8 eastbound, drawn west -> east, ending at the piece's middle vertex
        {"type": "way", "id": 1, "tags": {"highway": "motorway", "ref": "I 8", "lanes": "4"},
         "geometry": [{"lon": -117.001, "lat": 32.77}, {"lon": LON[1], "lat": 32.77}]},
        # a ramp drawn the OTHER way whose vertex is the piece's end node (a gore)
        {"type": "way", "id": 2, "tags": {"highway": "motorway_link"},
         "geometry": [{"lon": -116.9995, "lat": 32.7703}, {"lon": LON[2], "lat": 32.77}]}]}


def _travel(stable: bool) -> dict:
    import scripts.trace.osm as tosm
    from scripts.gps.classify import classify
    saved = tosm._post
    tosm._post = _ways
    try:
        with tempfile.TemporaryDirectory() as td:
            p = _project(Path(td), stable)
            classify(p)
            return json.loads((p / "data" / "network.geojson").read_text())["features"][0]["properties"]
    finally:
        tosm._post = saved


def test_without_the_key_the_gore_vote_splits_the_short_piece():
    e = _travel(False)
    assert e["travel_votes"] == [1, 1] and e["travel_dir"] == 0


def test_with_stable_snap_the_short_piece_votes_from_its_middle():
    e = _travel(True)
    assert e["travel_votes"] == [1, 0] and e["travel_dir"] == 1
