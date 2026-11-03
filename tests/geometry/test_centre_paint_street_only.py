"""Ledger 0063: a track with both kinds of layout keeps its centre line in the street layouts alone."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("_rc_0063", ROOT / "scripts" / "geometry" / "race_chicane.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

MIXED = [{"id": "street", "kind": "street"}, {"id": "race_cw", "kind": "race", "race_furniture": True}]


def test_a_mixed_track_ships_a_street_kn5():
    assert rc.has_street_kn5({"slug": "t", "layouts": MIXED})


def test_a_race_with_no_furniture_is_still_a_race():
    assert rc.is_race_layout({"id": "race", "kind": "race"})
    assert rc.has_street_kn5({"slug": "t", "layouts": [{"id": "street"}, {"id": "race", "kind": "race"}]})


def test_one_kind_of_layout_keeps_its_paint_in_the_road_kn5():
    assert not rc.has_street_kn5({"slug": "t", "layouts": [{"id": "full"}]})
    assert not rc.has_street_kn5({"slug": "t", "layouts": [{"id": "a", "kind": "race"}, {"id": "b", "kind": "race"}]})


def test_a_track_that_paints_no_yellow_has_nothing_to_route():
    for mk in ({"style": "none"}, {"style": "lane", "center_yellow": False}):
        assert not rc.has_street_kn5({"slug": "t", "layouts": MIXED, "road_markings": mk})


def test_the_road_yellow_is_street_only_and_the_freeway_is_not():
    assert rc.is_street_only_name("YLINE") and rc.is_street_only_name("YLINE_0") and rc.is_street_only_name("YLINE_mat.001")
    assert not rc.is_street_only_name("YLINE_I8_0")
    assert not rc.is_street_only_name("MARKINGS_0") and not rc.is_street_only_name("1ROAD_road_0")
