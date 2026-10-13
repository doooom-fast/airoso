"""The road_surface fork: one config knob must change BOTH the physics and the look.

A rally stage and its fantasy-paved twin share every vertex of geometry, so ``road_surface`` is the
only thing standing between "drives like dirt" and "drives like asphalt". These tests pin both
halves — surfaces.ini (track_folder) and the texture binding (pbr) — plus the guard that a typo in
the config fails the build instead of silently shipping tarmac.
"""

import json
import tempfile
from pathlib import Path

from scripts.ac import pbr, track_folder


def _road_block(ini: str) -> dict:
    """Parse the SURFACE_* block whose KEY=ROAD into a plain dict."""
    for block in ini.split("\n\n"):
        kv = dict(ln.split("=", 1) for ln in block.splitlines() if "=" in ln)
        if kv.get("KEY") == "ROAD":
            return kv
    raise AssertionError("no ROAD surface block")


def test_tarmac_is_the_default_and_keeps_full_grip():
    road = _road_block(track_folder.surfaces_ini())
    assert road["FRICTION"] == "0.99"
    assert road["DIRT_ADDITIVE"] == "0"
    assert road["IS_VALID_TRACK"] == "1"


def test_gravel_is_loose_dirty_and_still_valid_track():
    road = _road_block(track_folder.surfaces_ini(road_surface="gravel"))
    assert float(road["FRICTION"]) < 0.8          # loose surface, far less grip than tarmac
    assert float(road["DAMPING"]) > 0             # soft surface absorbs energy
    assert road["DIRT_ADDITIVE"] == "1"           # car actually picks up dust
    assert road["IS_VALID_TRACK"] == "1"          # still the racing surface — not run-off
    assert road["WAV"] == "gravel.wav"


def test_only_the_road_surface_changes_between_variants():
    # The gravel fork must not quietly alter grass/kerb/runoff — a stage still has to behave
    # correctly when the car leaves the road.
    tar = track_folder.surfaces_ini()
    gra = track_folder.surfaces_ini(road_surface="gravel")
    strip = lambda s: [b for b in s.split("\n\n") if "KEY=ROAD\n" not in b + "\n"]
    assert strip(tar) == strip(gra)


def test_unknown_road_surface_is_an_error_not_a_silent_tarmac():
    try:
        track_folder.surfaces_ini(road_surface="dirt")   # plausible typo for "gravel"
    except ValueError as e:
        assert "dirt" in str(e) and "gravel" in str(e)
    else:
        raise AssertionError("an unknown road_surface must fail the build")


def _proj(root, cfg):
    proj = Path(root)
    (proj / "track.config.json").write_text(json.dumps(cfg))
    return proj


def test_gravel_config_binds_the_gravel_road_texture():
    with tempfile.TemporaryDirectory() as d:
        ov = pbr.load_overrides(_proj(d, {"slug": "t", "road_surface": "gravel"}))
        assert ov["1ROAD"]["diffuse"].endswith("gravel_road_diffuse.png")
        assert ov["1ROAD"]["normal"].endswith("gravel_road_normal.png")
        assert ov["1RUNOFF"]["diffuse"].endswith("gravel_road_diffuse.png")
        # the texture the config points at has to actually exist, or the road renders black in-engine
        assert Path(ov["1ROAD"]["diffuse"]).is_file()
        assert Path(ov["1ROAD"]["normal"]).is_file()


def test_tarmac_config_leaves_the_stock_asphalt_binding_alone():
    with tempfile.TemporaryDirectory() as d:
        ov = pbr.load_overrides(_proj(d, {"slug": "t", "road_surface": "tarmac"}))
        assert "1ROAD" not in ov and "1RUNOFF" not in ov


def test_explicit_texture_override_beats_the_gravel_default():
    with tempfile.TemporaryDirectory() as d:
        proj = _proj(d, {"slug": "t", "road_surface": "gravel",
                         "texture_overrides": {"1ROAD": {"diffuse": "source/my_road.png"}}})
        ov = pbr.load_overrides(proj)
        assert ov["1ROAD"]["diffuse"].endswith("my_road.png")
        assert ov["1RUNOFF"]["diffuse"].endswith("gravel_road_diffuse.png")   # untouched key still forks


# ledger 0053: the wheel's kerb effect is an opt-in per track; the default output is byte-identical to before
HEAD_MD5 = {(False, "tarmac"): "0dcf17257710ecd6b0617f02470c8cb3", (False, "gravel"): "1610ad72a36dbb30d07bc18011e9d5af",
            (True, "tarmac"): "94e06a31028963e0cb796e0f943595d2", (True, "gravel"): "5122238873158b2d7eed8c34a07f65e6"}


def test_kerb_ff_effect_default_is_byte_identical_and_opt_in_changes_one_line():
    import hashlib
    for (wall, rs), h in HEAD_MD5.items():
        ini = track_folder.surfaces_ini(wall=wall, road_surface=rs)
        assert hashlib.md5(ini.encode()).hexdigest() == h, (wall, rs)          # every track that does not opt in
        assert ini == track_folder.surfaces_ini(wall=wall, road_surface=rs, kerb_ff_effect=0)
        on = track_folder.surfaces_ini(wall=wall, road_surface=rs, kerb_ff_effect=1)
        a, b = ini.splitlines(), on.splitlines()
        assert len(a) == len(b)
        diff = [(x, y) for x, y in zip(a, b) if x != y]
        assert diff == [("FF_EFFECT=0", "FF_EFFECT=1")], diff                  # exactly one line ...
        kerb = next(blk for blk in on.split("\n\n") if "KEY=KERB" in blk)
        assert "FF_EFFECT=1" in kerb and "VIBRATION_GAIN=1.0" in kerb          # ... on the KERB block
    for bad in (2, -1):
        try:
            track_folder.surfaces_ini(kerb_ff_effect=bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"kerb_ff_effect={bad} must be refused")


def test_track_folder_reads_the_opt_in_from_the_config():
    """the knob is read from track.config.json (L2), absent = 0 — never inferred"""
    src = (Path(__file__).resolve().parents[2] / "scripts" / "ac" / "track_folder.py").read_text(encoding="utf-8")
    assert 'kerb_ff = int(cfg.raw.get("kerb_ff_effect", 0) or 0)' in src
    assert src.count("kerb_ff_effect=kerb_ff") == 2                          # root data/ and every layout's data/
    root = Path(__file__).resolve().parents[2]
    for cfgp in sorted((root / "tracks").glob("*/track.config.json")):
        cfg = json.loads(cfgp.read_text(encoding="utf-8"))
        assert int(cfg.get("kerb_ff_effect", 0) or 0) in (0, 1), cfgp
