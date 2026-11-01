"""The Colorado circuits brought to the chain on 2026-11-01 (ONE-CHAIN §4 row 10: Pueblo, Aspen, Grand Junction,
Pikes Peak; Kevin 2026-11-01: "get a complete track list and installed by morning"), pinned on their files:

- ship.json: High Plains' first-pass shape (the same source type, from_track over an OSM node list): draft
  gps -> elev -> project -> mesh -> underlay, no authoring, prep / ship / gate and the sync lists as High Plains';
- track.config.json: the chain's frame (mirror_x false, true_north_rotation_deg 0; ledger 0060), the name set
  (ONE-CHAIN §3), one `full` layout, L3b terrain cells, smooth_window 0 for the node list (ledger 0060), a start at
  the site;
- Pikes Peak's turn banking: negative in the unmirrored frame (every turn a left-hander, raced counterclockwise),
  checked with the engine's own ribbon: the raised edge is the outside one;
- IMI stays off the chain while its trace is the placeholder (tracks/imi/track.config.json _chain_doc; L1).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import ship_track_spec as spec_mod  # noqa: E402

TRACKS = ("pueblo", "aspen", "grand-junction", "pikes-peak")


def _cfg(track):
    return json.loads((ROOT / "tracks" / track / "track.config.json").read_text(encoding="utf-8"))


def test_ship_json_is_high_plains_first_pass_shape():
    hp = spec_mod.load(ROOT / "tracks" / "high-plains" / "ship.json", "high-plains")
    for track in TRACKS:
        s = spec_mod.load(ROOT / "tracks" / track / "ship.json", track)
        assert s["steps"]["draft"] == ["gps", "elev", "project", "mesh", "underlay"], track
        assert s["steps"]["author"] == [], track
        for ph in ("prep", "ship", "gate"):
            assert s["steps"][ph] == hp["steps"][ph], (track, ph)
        assert s["sync_in"] == hp["sync_in"] and s["sync_out"] == hp["sync_out"], track
        assert s["workshop"] == f"C:/Users/Owner/Documents/k10-workshops/{track}", track
        assert s["ui_name_prefix"] == "doooom Colorado" and s["require_race_layout"] is False, track
        raw = json.loads((ROOT / "tracks" / track / "ship.json").read_text(encoding="utf-8"))
        assert raw.get("_doc") and raw.get("_owed"), track


def test_config_frame_names_layout_terrain_and_source():
    for track in TRACKS:
        c = _cfg(track)
        assert c["mirror_x"] is False and float(c["true_north_rotation_deg"]) == 0.0, track
        assert c["ui_series"] == "doooom Colorado" and "K10" not in c["name"], track
        assert c["install_folder"] == c["slug"], track
        assert "circuit" in c["ui_tags"], track
        assert [lo["id"] for lo in c["layouts"]] == ["full"], track
        assert not any(lo.get("race_furniture") for lo in c["layouts"]), track
        assert 1.25 <= float(c["terrain_cell_m"]) <= 1.5, track
        assert int(c.get("corridor_refine_factor", 0)) == 6, track
        src = c["source"]
        assert src["type"] == "from_track" and src["smooth_window"] == 0, track
        assert (ROOT / "tracks" / track / src["track"]).is_file(), track
        assert "2026-11-01" in c["_chain_doc"], track
        start, loc = c["route"]["start_at"], c["location"]
        d_km = 111.32 * ((start[0] - loc["lat"]) ** 2 + ((start[1] - loc["lon"]) * math.cos(math.radians(loc["lat"]))) ** 2) ** 0.5
        assert d_km < 3.0, (track, d_km)


def test_pikes_peak_banks_the_outside_edge_of_its_left_handers():
    from scripts.geometry import profile, ribbon

    c = _cfg("pikes-peak")
    assert c["route"]["reverse"] is True, "raced counterclockwise (route._orientation_doc)"
    cambers = c["road_profile"]["cambers"]
    assert [cm["bank_deg"] for cm in cambers] == [-10.0, -10.0], "L10: 10 deg; negative = left-hander unmirrored"
    assert int(c["road_profile"]["ribbon_cols"]) == 8
    _dip, bank_at, active = profile.build_profile(c["road_profile"])
    assert active
    # a counterclockwise circle of the lap's length (every station a left-hander) in the local ENU (x east, z north)
    lap, n = 1666.0, 556
    r = lap / (2 * math.pi)
    pts = [(r * math.cos(2 * math.pi * i / n), 0.0, r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
    road = ribbon.road_ribbon(pts, [15.0] * len(pts), tile_m=4.0, bank_at=bank_at, cols=1)
    V = road["vertices"]
    checked = 0
    for i in range(n):
        s = lap * i / n
        if abs(math.degrees(bank_at(s))) < 9.9:
            continue
        left, right = V[2 * i], V[2 * i + 1]
        hi, lo = (left, right) if left[1] > right[1] else (right, left)
        assert math.hypot(hi[0], hi[2]) > math.hypot(lo[0], lo[2]), (s, hi, lo)
        checked += 1
    assert checked > 200, checked
    # the straights stay flat (no researched banking for them: L10)
    for s in (100.0, 850.0, 1600.0):
        assert bank_at(s) == 0.0, s


def test_imi_stays_off_the_chain_while_its_trace_is_the_placeholder():
    c = _cfg("imi")
    placeholder = "placeholder" in c["source"].get("_trace_px_note", "")
    if placeholder:
        assert not (ROOT / "tracks" / "imi" / "ship.json").exists(), "L1: the IMI trace is not on the asphalt"
        assert c["mirror_x"] is True, "kept on the V1 frame so tools/ship_track.sh refuses it"
        assert "NOT brought to the chain" in c["_chain_doc"]
