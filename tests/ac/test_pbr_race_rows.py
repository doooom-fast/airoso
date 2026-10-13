"""scripts/ac/pbr.py — the race furniture's own texture rows (ledger 0047).

Lake Murray's track.config.json carries ``pbr.network_walls: true`` (the merged freeway's 1WALL_fw
barriers read as cast concrete). load_overrides then reskins the generic ``1WALL`` key with the
building tile, and both the prep (setup_material) and the exporter (shader_and_textures) look the
override up by the MATCHED key. Before the explicit rows, ``1WALL_race_*`` matched ``1WALL`` and the
race K-rail would have shipped as building concrete. These tests resolve the real object names
through pbr with network_walls on and off: the race rows keep Kevin's concrete_barrier_* pair and the
red/white kerb stripe either way, while the generic 1WALL row still takes the network skin (so the
mechanism the rows defend against is pinned too). Plain ``test_*`` functions, no bpy.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.ac import pbr

STRIPS = ("1WALL_race_kbar_college_780_0", "1WALL_race_edge_L_alvarado_0_0", "1WALL_race_edge_R_navajo_1514_1")
KERBS = ("1KERB_race_770_in", "1KERB_race_0_out")


def _proj(d, network_walls):
    proj = Path(d)
    cfg = {"slug": "t", "pbr": {"network_walls": network_walls},
           "texture_overrides": {"1GRASS": {"diffuse": "assets/textures/grass_diffuse.jpg"}}}
    (proj / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return proj


def _check_race_rows(ov):
    for n in STRIPS:
        r = pbr.resolve(n, ov)
        assert r["key"] == "1WALL_RACE", (n, r["key"])
        assert r["diffuse"].name == "concrete_barrier_diffuse.png", (n, r["diffuse"])
        assert r["normal"].name == "concrete_barrier_normal.png", (n, r["normal"])
        assert r["roughness"] == 0.85 and r["color"] == (0.72, 0.72, 0.70, 1) and not r["overridden"]
    for n in KERBS:
        r = pbr.resolve(n, ov)
        assert r["key"] == "1KERB_RACE", (n, r["key"])
        assert r["diffuse"].name == "kerb_race_worn_diffuse.jpg", (n, r["diffuse"])     # ledger 0053: the worn atlas
        assert r["normal"] is not None and r["normal"].name == "kerb_race_worn_normal.jpg", (n, r["normal"])
        assert not r["overridden"]


def test_race_rows_with_network_walls_true():
    with tempfile.TemporaryDirectory() as d:
        ov = pbr.load_overrides(_proj(d, True))
        assert "1WALL" in ov and ov["1WALL"]["diffuse"].endswith("building_diffuse.jpg")
        _check_race_rows(ov)
        # the generic row DOES take the network skin — the mechanism the race rows are immune to
        g = pbr.resolve("1WALL_fw_3", ov)
        assert g["key"] == "1WALL" and g["diffuse"].name == "building_diffuse.jpg" and g["overridden"]


def test_race_rows_with_network_walls_false():
    with tempfile.TemporaryDirectory() as d:
        ov = pbr.load_overrides(_proj(d, False))
        assert "1WALL" not in ov
        _check_race_rows(ov)
        g = pbr.resolve("1WALL_fw_3", ov)
        assert g["key"] == "1WALL" and g["diffuse"].name == "concrete_barrier_diffuse.png" and not g["overridden"]


def test_race_rows_precede_the_generic_rows_and_their_files_exist():
    keys = list(pbr.TEXTURES)
    assert keys.index("1WALL_RACE") < keys.index("1WALL")
    assert keys.index("1KERB_RACE") < keys.index("1KERB")
    # every other 1WALL_* / 1KERB_* row is still reached by its own names
    assert pbr.match_key("1WALL_guard") == "1WALL_GUARD" and pbr.match_key("1KERB_sidewalk") == "1KERB_SIDEWALK"
    assert pbr.match_key("1KERB_kerb") == "1KERB"
    td = pbr.texture_dir()
    for f in ("concrete_barrier_diffuse.png", "concrete_barrier_normal.png", "kerb_diffuse.png",
              "kerb_race_worn_diffuse.jpg", "kerb_race_worn_normal.jpg"):
        assert (td / f).exists(), td / f


def test_real_lake_murray_config_binds_the_race_rows():
    """the committed track config (network_walls: true) through the real load_overrides"""
    root = Path(__file__).resolve().parents[2]
    track = root / "tracks" / "san-diego-lake-murray"
    if not (track / "track.config.json").exists():
        return
    cfg = json.loads((track / "track.config.json").read_text(encoding="utf-8"))
    assert (cfg.get("pbr") or {}).get("network_walls") is True, "the case this row exists for"
    _check_race_rows(pbr.load_overrides(track))


def test_the_worn_kerb_row_reaches_only_the_race_kerbs():
    """ledger 0053: the 1KERB_RACE row binds the worn atlas + its normal map (so the exporter's rule — a normal
    present -> ksPerPixelMultiMap with txDiffuse + txNormal — picks the path 1WALL_RACE already renders through),
    its KS_PROPS row matches only race-kerb names, and the generic 1KERB / 1KERB_SIDEWALK rows every other
    track's kerbs and every street curb bind are exactly what they were"""
    diff, norm, rough, color, metal, water = pbr.TEXTURES["1KERB_RACE"]
    assert (diff, norm) == ("kerb_race_worn_diffuse.jpg", "kerb_race_worn_normal.jpg")
    assert (rough, color, metal, water) == (0.55, (0.62, 0.10, 0.08, 1), 0.0, False)
    assert pbr.TEXTURES["1KERB"] == ("kerb_diffuse.png", None, 0.55, (0.62, 0.10, 0.08, 1), 0.0, False)
    assert pbr.TEXTURES["1KERB_SIDEWALK"] == ("building_diffuse.jpg", "building_normal.jpg", 0.75, (0.66, 0.66, 0.64, 1), 0.0, False)
    assert "1KERB_RACE" not in pbr.BILLBOARD
    ks = pbr.KS_PROPS["1KERB_RACE"]
    assert ks == {"ksAmbient": 0.40, "ksDiffuse": 0.40, "ksSpecular": 0.10, "ksSpecularEXP": 20.0}

    def ks_key(name):                                   # export_kn5_addon's own lookup
        return next((k for k in pbr.KS_PROPS if name.upper().startswith(k)), None)
    for n in KERBS:
        assert ks_key(n) == "1KERB_RACE", n
    for n in ("1KERB_sidewalk", "1KERB_kerb", "1KERB_sidewalk_3", "1WALL_race_edge_L_alvarado_0_0", "1ROAD_road"):
        assert ks_key(n) is None, n
