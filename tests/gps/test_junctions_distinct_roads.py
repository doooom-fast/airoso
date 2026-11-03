"""Ledger 0070 B1: widths_from_osm.detect_junctions flares a node only where two DISTINCT arterial roads meet.

OSM splits one street into ways at every tag change, bridge end and side street; counting ways flared Sand Creek
0.33.0 at 50 nodes that are not junctions (32 bare way splits, 18 minor side streets on one arterial). Stdlib only.
"""
from scripts.gps.widths_from_osm import detect_junctions, lanes_tag, road_ident

# a straight east-west arterial along the line, and the line itself (lon, lat), ~1 m apart
LINE = [(-104.9200 + i * 0.00001, 39.7800) for i in range(200)]
NODE = (-104.9190, 39.7800)        # a node on the line: its vertex 100


def _way(i, name, hw, geom, nodes, lanes=None, ref=None):
    return {"id": i, "name": name, "ref": ref, "highway": hw, "lanes": lanes, "geom": geom, "nodes": nodes}


WEST = [(-104.9200, 39.7800), NODE]
EAST = [NODE, (-104.9180, 39.7800)]
NORTH = [NODE, (-104.9190, 39.7810)]


def test_a_bare_way_split_of_one_arterial_is_not_a_junction():
    ways = [_way(1, "E 56th Ave", "secondary", WEST, [10, 99]), _way(2, "E 56th Ave", "secondary", EAST, [99, 11])]
    assert detect_junctions(ways, LINE) == []


def test_a_minor_side_street_on_one_arterial_is_not_a_junction():
    ways = [_way(1, "E 46th Ave", "tertiary", WEST, [10, 99]), _way(2, "E 46th Ave", "tertiary", EAST, [99, 11]),
            _way(3, "Ash St", "residential", NORTH, [99, 12])]
    assert detect_junctions(ways, LINE) == []


def test_two_distinct_arterials_are_a_junction():
    ways = [_way(1, "E 56th Ave", "secondary", WEST, [10, 99]), _way(2, "E 56th Ave", "secondary", EAST, [99, 11]),
            _way(3, "Dahlia St", "tertiary", NORTH, [99, 12])]
    j = detect_junctions(ways, LINE)
    assert len(j) == 1 and j[0]["idx"] == 100                           # the node is line vertex 100


def test_identity_is_name_then_ref_then_the_way():
    assert road_ident({"name": " E 56th Ave "}) == "e 56th ave"
    assert road_ident({"name": None, "ref": "SH 2"}) == "sh 2"
    assert road_ident({"id": 7}) == "way7"
    assert lanes_tag({"lanes": "3"}) == 3 and lanes_tag({"lanes": None}) is None and lanes_tag(None) is None
    assert lanes_tag({"lanes": "2;3"}) is None
