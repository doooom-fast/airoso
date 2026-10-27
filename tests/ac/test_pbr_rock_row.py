"""scripts/ac/pbr.py — the road cuts' rock row (ledger 0054 P4 buildings + rock).

tools/rock_faces_blend.py splits the steep faces of the north network's cut walls out of the physical ground tiles as
``1GRASS_ROCK_<tile>``: the 1GRASS prefix on purpose (same surfaces.ini key GRASS, same physics, read as ground by every
gate), their OWN pbr row before ``1GRASS`` so they bind the rock texture and a track's ``1GRASS`` turf override never
reaches them, and ext_config leaves them out of GrassFX's GRASS_MESHES. These tests pin the three readers: pbr (row order,
the override by the matched key, both the prep's setup path and the exporter's expression), ext_config (GRASS_MESHES),
and the stock skin existing. Plain ``test_*`` functions, no bpy.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.ac import ext_config, pbr

ROOT = Path(__file__).resolve().parents[2]


def _proj(d, rock_override):
    proj = Path(d)
    tex = {"1GRASS": {"diffuse": "assets/textures/grass_diffuse.jpg", "normal": "assets/textures/grass_normal.jpg"}}
    if rock_override:
        (proj / "textures").mkdir()
        for n in ("sandstone_cut_diffuse.jpg", "sandstone_cut_normal.jpg"):
            (proj / "textures" / n).write_bytes(b"x")
        tex["1GRASS_ROCK"] = {"diffuse": "textures/sandstone_cut_diffuse.jpg", "normal": "textures/sandstone_cut_normal.jpg"}
    (proj / "track.config.json").write_text(json.dumps({"slug": "t", "texture_overrides": tex}), encoding="utf-8")
    return proj


def test_rock_row_precedes_1grass_and_binds_by_the_longer_prefix():
    keys = list(pbr.TEXTURES)
    assert keys.index("1GRASS_ROCK") < keys.index("1GRASS"), "prefix order = match priority (dict-ordered)"
    assert pbr.match_key("1GRASS_ROCK_12") == "1GRASS_ROCK"
    assert pbr.match_key("1GRASS_12") == "1GRASS"
    # the exporter's own expression (export_kn5_addon.shader_and_textures) is the same first-prefix scan
    assert next(k for k in pbr.TEXTURES if "1GRASS_ROCK_12".upper().startswith(k)) == "1GRASS_ROCK"
    assert "1GRASS_ROCK" in pbr.KS_PROPS and pbr.KS_PROPS["1GRASS_ROCK"] == pbr.KS_PROPS["1GRASS"]


def test_stock_skin_exists_and_the_track_override_wins_without_touching_1grass():
    assert (pbr.texture_dir() / pbr.TEXTURES["1GRASS_ROCK"][0]).exists(), "the stock stone_tan.png skin"
    with tempfile.TemporaryDirectory() as d:
        proj = _proj(d, rock_override=False)
        ov = pbr.load_overrides(proj)
        r = pbr.resolve("1GRASS_ROCK_3", ov)
        assert r["key"] == "1GRASS_ROCK" and r["diffuse"].name == "stone_tan.png" and not r["overridden"]
        g = pbr.resolve("1GRASS_3", ov)
        assert g["diffuse"].name == "grass_diffuse.jpg" and g["overridden"], "the turf override binds 1GRASS only"
    with tempfile.TemporaryDirectory() as d:
        proj = _proj(d, rock_override=True)
        ov = pbr.load_overrides(proj)
        r = pbr.resolve("1GRASS_ROCK_3", ov)
        assert r["overridden"] and r["diffuse"].name == "sandstone_cut_diffuse.jpg" \
            and r["normal"].name == "sandstone_cut_normal.jpg"
        assert pbr.resolve("1GRASS_3", ov)["diffuse"].name == "grass_diffuse.jpg"


def test_lake_murray_binds_its_own_sandstone_tile():
    proj = ROOT / "tracks" / "san-diego-lake-murray"
    ov = pbr.load_overrides(proj)
    r = pbr.resolve("1GRASS_ROCK_0", ov)
    assert r["overridden"] and r["diffuse"].exists() and r["normal"].exists(), r
    assert r["diffuse"].name == "sandstone_cut_diffuse.jpg"


def test_grassfx_leaves_the_rock_faces_out():
    with tempfile.TemporaryDirectory() as d:
        proj = Path(d)
        (proj / "data").mkdir()
        (proj / "track.config.json").write_text(json.dumps({"slug": "t", "lighting": {"grassfx": True}}), encoding="utf-8")
        (proj / "data" / "environment.obj").write_text("o 1GRASS_0\no 1GRASS_ROCK_0\no 1GRASS_1\no 1LAWN_a\no 1ROAD_road\n")
        txt = ext_config.generate(proj).read_text(encoding="utf-8")
    grass_lines = [ln for ln in txt.splitlines() if ln.strip().upper().startswith("GRASS_MESHES")]
    assert grass_lines, txt
    assert "1GRASS_ROCK" not in grass_lines[0] and "1GRASS_0" in grass_lines[0] and "1LAWN_a" in grass_lines[0], grass_lines
