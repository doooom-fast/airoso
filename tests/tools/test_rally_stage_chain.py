"""The four Rally Colorado stages through the chain (ONE-CHAIN §4 row 6, 2026-11-01; Kevin: "get a complete track list
and installed by morning"). Pinned on the specs and configs only (nothing is built):

- each ship.json is the rally_stage draft row (gps -> elev -> project -> mesh -> underlay; no widths: no lane count on a
  graded county road), the four chain specs' prep / ship / gate shape, no authoring yet, no race layout;
- the name set (ONE-CHAIN §3): "<Stage> (Gravel)" / "<Stage> (Tarmac)" as two tracks (L8), "doooom Colorado",
  install_folder = slug, one `stage` layout named as the track;
- the chain's frame stated in the config (mirror_x false, true north 0), loop false (L11), road_surface per track;
- L8 / docs/RALLY-CONVENTIONS.md: a tarmac twin's geometry keys equal its gravel twin's — the pair differ only in what
  road_surface forks (the engine-era tarmac configs had dropped corridor_refine_factor and, on Under the Dragon,
  route.wide_corners);
- the tarmac pair carries `_deprioritised` (Kevin 2026-07-26) in both files, the gravel pair does not.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import ship_track_spec as spec_mod  # noqa: E402

STAGES = {
    "rally-dragon-tail-gravel": ("Dragon Tail", "Gravel", "gravel"),
    "rally-dragon-tail-tarmac": ("Dragon Tail", "Tarmac", "tarmac"),
    "rally-under-the-dragon-gravel": ("Under the Dragon", "Gravel", "gravel"),
    "rally-under-the-dragon-tarmac": ("Under the Dragon", "Tarmac", "tarmac"),
}
# what road_surface forks (and the identity keys); everything else is shared by the twins
SURFACE_KEYS = {"name", "_name_doc", "slug", "_slug_doc", "install_folder", "road_surface", "_road_surface_doc",
                "road_markings", "ui_description", "ui_tags", "layouts", "_version_doc", "_deprioritised", "_chain_doc"}


def _cfg(track):
    return json.loads((ROOT / "tracks" / track / "track.config.json").read_text(encoding="utf-8"))


def test_each_stage_spec_is_the_rally_stage_draft_row():
    for track in STAGES:
        s = spec_mod.load(ROOT / "tracks" / track / "ship.json", track)
        assert s["steps"]["draft"] == ["gps", "elev", "project", "mesh", "underlay"], (track, s["steps"]["draft"])
        assert s["steps"]["author"] == [] and s["steps"]["prep"] == ["prep", "split"]
        assert s["steps"]["ship"] == ["export_road", "ai", "verify_kn5", "road_obj", "track_folder", "verify_inis",
                                      "make_map"], track
        assert s["steps"]["gate"] == ["drive_test_street", "audit_street", "kn5_ground"], track
        assert s["workshop"] in (f"C:/Users/Owner/Documents/k10-workshops/{track}", f"D:/k10-workshops/{track}"), track
        assert s["require_race_layout"] is False and s["street_ai_july"] == ""
        assert s["ui_name_prefix"] == "doooom Colorado"
        assert s["sync_in"]["required"] == ["track.config.json"]
        assert "data/osm.cache.json" in s["sync_in"]["optional"] and "data/osm.cache.json" in s["sync_out"]["files"]
        assert "loop.blend" in s["sync_out"]["required"] and "data/underlay.report.json" in s["sync_out"]["files"]
        assert not any(f.endswith((".obj", ".blend")) for f in s["sync_out"]["files"]), "no generated mesh comes home"


def test_the_name_set_the_frame_and_one_point_to_point_layout():
    for track, (stage, surface, road) in STAGES.items():
        cfg = _cfg(track)
        name = f"{stage} ({surface})"
        assert cfg["name"] == name and "K10" not in json.dumps(cfg["name"] + cfg["ui_series"])
        assert cfg["ui_series"] == "doooom Colorado"
        assert cfg["install_folder"] == cfg["slug"] and cfg["slug"].endswith("_" + road)
        assert cfg["road_surface"] == road
        assert cfg["loop"] is False
        assert cfg["mirror_x"] is False and cfg["true_north_rotation_deg"] == 0.0
        assert isinstance(cfg["natural_ground"], bool)
        assert [lo["id"] for lo in cfg["layouts"]] == ["stage"] and cfg["layouts"][0]["name"] == name
        assert not any(lo.get("race_furniture") for lo in cfg["layouts"])
        assert "circuit" in cfg["ui_tags"] and road in cfg["ui_tags"]
        # Dragon Tail 0.2.1 (ledger 0076: the engine's lip feet and the stage's replication read; the twins move together)
        assert cfg["version"] == ("0.2.1" if "dragon-tail" in track else "0.2.0"), (track, cfg["version"])
        assert cfg["_chain_doc"].startswith("2026-11-01")


def test_tarmac_twins_share_the_gravel_geometry_and_are_marked_deprioritised():
    for stage in ("dragon-tail", "under-the-dragon"):
        g, t = _cfg(f"rally-{stage}-gravel"), _cfg(f"rally-{stage}-tarmac")
        shared = (set(g) | set(t)) - SURFACE_KEYS
        diff = sorted(k for k in shared if g.get(k) != t.get(k))
        assert not diff, (stage, diff)
        assert t["corridor_refine_factor"] == g["corridor_refine_factor"] and t["route"]["wide_corners"]
        assert t["_deprioritised"].startswith("Kevin 2026-07-26") and "_deprioritised" not in g
        assert next(iter(t)) == "_deprioritised", "top level, first, so a fleet runner reads it without parsing the rest"
        st = json.loads((ROOT / "tracks" / f"rally-{stage}-tarmac" / "ship.json").read_text(encoding="utf-8"))
        sg = json.loads((ROOT / "tracks" / f"rally-{stage}-gravel" / "ship.json").read_text(encoding="utf-8"))
        assert "_deprioritised" in st and "_deprioritised" not in sg
