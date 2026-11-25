"""Denver Grand Prix 0.1.0 (ledger 0096, "0.1.0 (Drive 1)"): the track's identity, its chain, and its committed draft.

Held here, none of it in Blender:
  * identity: lm-v4, mirror_x false, north 0, slug / install folder denver_grand_prix, kind fictional_street_circuit,
    version 0.1.0, race and street layouts (the race furnished, its closure token), the registry entry;
  * ship.json is read by tools/ship_track_spec.py and names only steps tools/ship_track.sh defines;
  * the committed draft files are the ones source/draft/draft_line.py and mouth_stubs.py reported writing (md5), the
    line is a closed lap, its widths are the measured edges (never the provisional OSM-lane mode), and the draft's
    constructions are each declared with a reason;
  * no loop.blend is committed for this track (.gitignore: tracks/*/loop.blend; a record, never seeded).
Plain ``test_*`` for tests/run_tests.py."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = ROOT / "tracks" / "denver-grand-prix"
CFG = json.loads((T / "track.config.json").read_text(encoding="utf-8"))
SHIP = json.loads((T / "ship.json").read_text(encoding="utf-8"))


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def test_identity():
    assert CFG["slug"] == CFG["install_folder"] == "denver_grand_prix"
    assert CFG["name"] == "Denver Grand Prix" and CFG["version"] == "0.1.0"
    assert CFG["kind"] == "fictional_street_circuit" and CFG["archetype"] == "street_circuit"
    assert CFG["mirror_x"] is False and CFG["true_north_rotation_deg"] == 0.0 and CFG["loop"] is True
    assert SHIP["engine"] == "lm-v4" and SHIP["track"] == "denver-grand-prix"
    ids = {lo["id"]: lo for lo in CFG["layouts"]}
    assert set(ids) == {"race", "street"}
    assert ids["race"]["kind"] == "race" and ids["race"]["race_furniture"] is True and ids["race"]["closure_token"] == "race"
    assert ids["street"]["kind"] == "street" and ids["street"]["race_furniture"] is False
    reg = json.loads((ROOT / "fleet" / "registry.json").read_text(encoding="utf-8"))
    air = next(r for r in reg["repos"] if r["name"] == "airoso")
    assert "tracks/denver-grand-prix/track.config.json" in air["tracks_glob"]
    assert reg["track_annotations"]["airoso/denver-grand-prix"]["kind"] == "fictional_street_circuit"


def test_ship_json_reads_and_names_known_steps():
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "ship_track_spec.py"), str(T / "ship.json"),
                          "denver-grand-prix"], capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stderr
    sh = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")
    for phase, steps in SHIP["steps"].items():
        for s in steps:
            assert re.search(rf"^{phase}_{s}\(\) \{{", sh, re.M), f"{phase}_{s} is not a ship_track.sh step"


def test_committed_draft_is_what_the_scripts_wrote():
    rep = json.loads((T / "data" / "draft_line.report.json").read_text(encoding="utf-8"))
    for f, h in rep["md5"].items():
        assert _md5(T / "data" / f) == h, f
    assert rep["widths"]["mode"] == "measured", "the provisional OSM-lane widths are never shipped"
    assert rep["widths"]["md5"] == _md5(T / "source" / "widths" / "widths.json")
    ms = json.loads((T / "data" / "mouth_stubs.report.json").read_text(encoding="utf-8"))
    assert ms["md5"] == _md5(T / "data" / "connectors.local.json")
    local = json.loads((T / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    pts = local["points_xyz_m"]
    assert pts[0] == pts[-1] and len(pts) == len(local["widths_m"]), "a closed lap repeats point 0 (L13)"


def test_every_construction_says_why():
    dl = CFG["draft_line"]
    assert dl["widths"]["mode"] == "measured"
    for sp in dl["straight_spans"]:
        assert sp.get("why"), sp["name"]
    for f in dl["widths"].get("edge_fills") or []:
        assert "[invented]" in f["why"]
    for c in CFG["route"]["fillet"]["corners"]:
        assert c["radius_m"] == round(c["curb_radius_m"] + sum(c["half_widths_m"]) / 2, 1), c["name"]
    assert "[invented]" in CFG["route"]["fillet"]["_doc"] and "[invented]" in dl["mouths"]["_doc"]


def test_no_scene_file_committed():
    tracked = subprocess.run(["git", "-c", "core.commitGraph=false", "ls-files", "tracks/denver-grand-prix"],
                             capture_output=True, text=True, cwd=ROOT).stdout.split()
    assert not any(p.endswith(".blend") for p in tracked)
    ign = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "tracks/*/loop.blend" in ign and "!tracks/denver-grand-prix/loop.blend" not in ign
