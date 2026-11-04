"""bridges.detector: false (ledger 0048, the Lariat): build_mesh's height detector mints no span on a track whose decks
are all declared; every other track keeps the detector on. Stdlib only."""
from scripts.geometry.build_mesh import bridge_detector_on


def test_the_detector_stays_on_unless_a_track_turns_it_off():
    assert bridge_detector_on({}) is True
    assert bridge_detector_on({"bridges": {"l13_seam_rule": True}}) is True
    assert bridge_detector_on({"bridges": {"detector": True}}) is True
    assert bridge_detector_on({"bridges": None}) is True
    assert bridge_detector_on({"bridges": {"detector": False}}) is False


def test_only_a_literal_false_turns_it_off():
    assert bridge_detector_on({"bridges": {"detector": 0}}) is True       # a typo never silently drops real decks
    assert bridge_detector_on({"bridges": {"detector": "off"}}) is True
