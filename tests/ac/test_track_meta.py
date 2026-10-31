"""Track identity (version/author/year) is decoupled from the builder: it comes from
``track.config.json`` with sensible defaults, and flows into ui_track.json — never hardcoded."""

import json
import tempfile
from pathlib import Path

from scripts.ac.track_folder import ui_track_json
from scripts.config import load_config

_MINIMAL = {
    "name": "Test Loop", "slug": "test_loop",
    "location": {"lat": 39.78, "lon": -104.94, "timezone": "America/Denver"},
    "source": {"type": "osm"}, "loop": True, "default_width_m": 9.0, "origin": "centroid",
    "surfaces": {"road": "1ROAD", "grass": "GRASS", "kerb": "1KERB"},
    "layouts": [{"id": "full"}], "lighting": {"presets": ["noon"]},
}


def _load(extra: dict):
    with tempfile.TemporaryDirectory() as d:
        cfg_path = Path(d) / "track.config.json"
        cfg_path.write_text(json.dumps({**_MINIMAL, **extra}), encoding="utf-8")
        return load_config(cfg_path)


def test_defaults_when_absent():
    cfg = _load({})
    assert cfg.version == "0.1"
    assert cfg.author == "doooom"          # the default author is the brand, not the retired builder (2026-10-29)
    assert cfg.year == 2026


def test_version_decoupled_from_config():
    cfg = _load({"version": "2.3", "author": "K10 Motorsports", "year": 2027})
    assert cfg.version == "2.3"
    ui = ui_track_json(cfg, "full", length_m=1234.0, n_pits=4)
    assert ui["version"] == "2.3"           # the track's own version, not the builder's
    assert ui["author"] == "K10 Motorsports"
    assert ui["year"] == 2027


def test_numeric_version_coerced_to_string():
    # JSON may carry version as a number; ui_track.json must serialize it as a string.
    cfg = _load({"version": 1.5})
    assert ui_track_json(cfg, "full", 100.0, 1)["version"] == "1.5"


def test_default_description_follows_the_source_and_the_archetype():
    """Exotics' first install (2026-10-29, ledger 0060) carried "Real-world street circuit built from OpenStreetMap"
    for a closed circuit traced off NAIP: the default says where the road came from and what the place is; an
    explicit ui_description still wins; the default author is the brand."""
    ex = _load({"source": {"type": "aerial"}, "archetype": "race_circuit",
                "location": {"lat": 36.28, "lon": -115.02, "timezone": "America/Los_Angeles", "city": "Las Vegas",
                             "country": "United States"}})
    ui = ui_track_json(ex, "full", length_m=1822.0, n_pits=4)
    assert "Real-world circuit traced from USDA NAIP aerial imagery" in ui["description"], ui["description"]   # after the "[build x] " tag
    assert "street circuit" not in ui["description"] and "OpenStreetMap" not in ui["description"]
    assert "(Las Vegas, United States)" in ui["description"] and ui["author"] == "doooom"
    osm = ui_track_json(_load({}), "full", length_m=1000.0, n_pits=4)
    assert "built from OpenStreetMap" in osm["description"]
    kml = ui_track_json(_load({"source": {"type": "kml", "kml": "x.kml"}, "archetype": "street_circuit"}), "full", 1000.0, 4)
    assert "Racing loop on real streets built from a mapped route" in kml["description"]
    own = ui_track_json(_load({"ui_description": "My words."}), "full", 1000.0, 4)
    assert own["description"].endswith("My words.")           # behind the "[build x] " tag, as before
