"""Unit tests for the CSP TreeFX + GrassFX vegetation emitter (scripts/environment/treefx).

Pure ``test_*`` functions (no pytest fixtures) so tests/run_tests.py runs them under the
dependency-free system python. The emitter is stdlib-only by design, so these need no numpy/bpy.

Coverage:
  - trees.txt line format: exact field order, ';' separators, degrees, simple vs extended forms.
  - configure: directive lines.
  - the [TREES] ext block is well-formed (LIST_N, SURFACE_MATERIALS).
  - the [GRASS_FX] block: shipped-CSP grammar, our mesh + material names, mask presets, the V3
    golden, groups / configurations / adjustments, loud rejection of unknown and retired keys.
  - density INCREASES with elevation on a ramp fixture.
  - the creek band selects ONLY near-water positions.
  - N/E aspect adds density; round-trip JSON is stable.
"""

from __future__ import annotations

import json
import random
import tempfile
from pathlib import Path

from scripts.environment import treefx as tfx


# ---------------------------------------------------------------------------------- line format ---
def test_simple_tree_line_is_filename_then_position():
    t = tfx.Tree("MRS_pine_high_2_1.bin", 12.5, 2103.4, -55.2)
    # filename first (terminated by ';'), then X, Y, Z metres — no key=value params
    assert t.line() == "tree: MRS_pine_high_2_1.bin; 12.5, 2103.4, -55.2"


def test_extended_tree_line_field_order_and_separators():
    t = tfx.Tree("pine.bin", 10.0, 5.0, -3.0, angle=137.0, size=3.2, width=0.9,
                 color=(1.0, 1.0, 0.9))
    # extended form: pos=X, Y, Z then each param preceded by '; ', angle in DEGREES, ' = ' spacing
    assert t.line() == (
        "tree: pine.bin; pos=10, 5, -3; angle = 137; size = 3.2; width = 0.9; color = 1, 1, 0.9"
    )


def test_angle_wraps_into_0_360():
    assert tfx.Tree("t.bin", 0, 0, 0, angle=-90.0).line().endswith("angle = 270")
    assert tfx.Tree("t.bin", 0, 0, 0, angle=450.0).line().endswith("angle = 90")


def test_configure_line():
    assert tfx.Configure("size variance", [0.9, 1.1]).line() == "configure: size variance = 0.9, 1.1"
    assert tfx.Configure("angle variance", [0, 360]).line() == "configure: angle variance = 0, 360"
    assert tfx.Configure("seed", 42).line() == "configure: seed = 42"


def test_render_trees_txt_preserves_order_and_comments():
    directives = ["; hello", tfx.Configure("seed", 1), tfx.Tree("a.bin", 1, 2, 3)]
    txt = tfx.render_trees_txt(directives, header=["; H"])
    lines = txt.strip().splitlines()
    assert lines == ["; H", "; hello", "configure: seed = 1", "tree: a.bin; 1, 2, 3"]
    assert txt.endswith("\n")


# ------------------------------------------------------------------------------- [TREES] block ---
def test_trees_ext_section_well_formed():
    out = tfx.trees_ext_section(["trees/trees.txt", "trees/extra.txt"],
                                surface_materials=["1GRASS_mat", "1ROAD_main_mat"],
                                surface_meshes=["1GRASS"],
                                compiled_list="compiled_trees.bin",
                                expected_species=["pine.bin"])
    text = "\n".join(out)
    assert "[TREES]" in out
    assert "LIST_0 = trees/trees.txt" in out
    assert "LIST_1 = trees/extra.txt" in out
    assert "SURFACE_MATERIALS = 1GRASS_mat, 1ROAD_main_mat" in out
    assert "SURFACE_MESHES = 1GRASS" in out
    # COMPILED_LIST is OPTIONAL (external bakery) -> emitted commented-out, never active
    assert any(l.strip().startswith(";") and "COMPILED_LIST" in l for l in out)
    assert not any(l.strip().startswith("COMPILED_LIST") for l in out)  # never an ACTIVE key
    assert "pine.bin" in text


# ----------------------------------------------------------------------------- [GRASS_FX] block ---
# The grammar every shipped CSP track config uses (ledger 0045): lists + atlas + mask + shape in
# [GRASS_FX], optional TEXTURE_GROUP_n / CONFIGURATION_A..D / ADJUSTMENT_... blocks. The old
# [GRASS_FX_TEXTURE_0] / CONFIGURATION_0 / BRIGHTNESS / HEALTH / grass_ks.dds block matched no config
# on this machine and must never come back.
V3_GRASSFX_CFG = {
    "_doc": "documentation keys are skipped",
    "mask": "open", "shape_size": [0.7, 1.1], "shape_width": 0.6, "shape_tidy": [1, 0.6],
    "shape_cut": [1, 0.5], "trim_period": "THURSDAY",
    "texture": "grass_fx/highlands.dds", "texture_grid": [8, 3],
}
V3_GRASSFX_INI = (
    "; --- GrassFX: CSP 3D grass on the terrain tiles -------------------------------\n"
    "; Grammar = the one every shipped CSP track config uses: lists + atlas + mask + shape in [GRASS_FX];\n"
    "; optional [GRASS_FX_TEXTURE_GROUP_N], [GRASS_FX_CONFIGURATION_A..D], [GRASS_FX_ADJUSTMENT_...].\n"
    "; GRASS_* / OCCLUDING_MESHES are OUR kn5 names. OCCLUDING_MESHES is an ALLOW-LIST of near-field,\n"
    "; ground-seated solids only (road, kerbs, building + house footprints): a far-field or oversized\n"
    "; mesh here busts the GPU watchdog (shipped v0.12.1-v0.12.6). Blades take the colour of the ground\n"
    "; texel under them, so the look follows the 1GRASS texture. VERIFY IN-GAME.\n"
    "[GRASS_FX]\n"
    "GRASS_MATERIALS = 1GRASS_0_mat, 1GRASS_1_mat\n"
    "GRASS_MESHES = 1GRASS_0, 1GRASS_1\n"
    "OCCLUDING_MESHES = 1KERB_sidewalk, 1ROAD_road, BUILDING, HOUSE, MARKINGS_0, MARKINGS_1\n"
    "ORIGINAL_GRASS_MATERIALS =\n"
    "TEXTURE = grass_fx/highlands.dds\n"
    "TEXTURE_GRID = 8, 3\n"
    "; mask: spawn on every texel (wiki preset) - both listed tiles are 100% grass, no colour gating\n"
    "MASK_MAIN_THRESHOLD = -1\n"
    "MASK_RED_THRESHOLD = 0\n"
    "MASK_MIN_LUMINANCE = -1\n"
    "MASK_MAX_LUMINANCE = 1\n"
    "; shape: weekly-mown suburban turf; 'a, b' pairs span TRIM_PERIOD (just cut -> a week's growth)\n"
    "SHAPE_SIZE = 0.7, 1.1\n"
    "SHAPE_WIDTH = 0.6\n"
    "SHAPE_TIDY = 1, 0.6\n"
    "SHAPE_CUT = 1, 0.5\n"
    "TRIM_PERIOD = THURSDAY\n"
)


def _gfx(cfg=None, *, grass=("1GRASS", "1LAWN"), occ=("1ROAD_main", "1KERB_l", "BUILDINGS"), mats=None):
    return tfx.grassfx_block(grass_meshes=list(grass), occluding_meshes=list(occ),
                             grass_materials=mats, cfg=cfg)


def test_grassfx_block_binds_our_meshes_and_has_required_keys():
    out = _gfx()
    text = "\n".join(out)
    assert "[GRASS_FX]" in out
    assert "GRASS_MATERIALS = 1GRASS_mat, 1LAWN_mat" in out     # kn5 material names (23/23 shipped configs)
    assert "GRASS_MESHES = 1GRASS, 1LAWN" in out                 # mesh names (wiki; Nords-own override)
    assert "OCCLUDING_MESHES = 1ROAD_main, 1KERB_l, BUILDINGS" in out
    assert "ORIGINAL_GRASS_MATERIALS =" in out                   # a MISSING line hides every ksGrass object
    assert "SHAPE_SIZE = 0.9" in out                             # bare-bool fleet default, byte-stable
    # the default mask quartet = colorado-2013's shipped numbers, colour-gated
    assert "MASK_MAIN_THRESHOLD = 0.5" in out and "MASK_RED_THRESHOLD = 0.05" in out
    assert "MASK_MIN_LUMINANCE = 0.02" in out and "MASK_MAX_LUMINANCE = 0.35" in out
    assert out[-1] == ""                                         # ends with the blank separator
    # the retired grammar never comes back, and no TEXTURE line without a config asking for one
    # (checked on the value/section lines: the header comment legitimately names TEXTURE_GROUP_N)
    values = "\n".join(l for l in out if not l.startswith(";"))
    for dead in ("TEXTURE", "GRASS_FX_TEXTURE_0", "GRASS_FX_CONFIGURATION_0", "BRIGHTNESS", "HEALTH", "grass_ks"):
        assert dead not in values, dead
    assert "grass_ks" not in text
    # comments are own-line ';' lines only - never trailing a value
    assert not any(";" in l for l in out if l and not l.startswith(";"))


def test_grassfx_v3_dict_is_the_golden_ini():
    out = _gfx(V3_GRASSFX_CFG, grass=("1GRASS_0", "1GRASS_1"),
               occ=("1KERB_sidewalk", "1ROAD_road", "BUILDING", "HOUSE", "MARKINGS_0", "MARKINGS_1"),
               mats=["1GRASS_0_mat", "1GRASS_1_mat"])
    assert "\n".join(out) == V3_GRASSFX_INI


def test_grassfx_open_mask_preset_and_overrides():
    out = _gfx({"mask": "open"})
    assert "MASK_MAIN_THRESHOLD = -1" in out and "MASK_MAX_LUMINANCE = 1" in out
    assert "MASK_RED_THRESHOLD = 0" in out and "MASK_MIN_LUMINANCE = -1" in out
    # a single mask_* key overrides its one line on top of the preset
    out = _gfx({"mask": "open", "mask_max_luminance": 0.18, "mask_blur": 7})
    assert "MASK_MAIN_THRESHOLD = -1" in out and "MASK_MAX_LUMINANCE = 0.18" in out
    assert "MASK_BLUR = 3" in out                                # clamped 0..3


def test_grassfx_groups_configurations_and_material_adjustment():
    cfg = {"texture_groups": [[{"piece": [4, 1, 2, 2], "size_mult": [1.2, 1.5], "wind": 0.5}]],
           "configurations": {"A": {"texture_base_chance": 0.8, "texture_group_chances": [0.04]}},
           "adjustments": [{"materials": ["1GRASS_0_mat", "1GRASS_1_mat"], "map": "A"}]}
    out = _gfx(cfg)
    text = "\n".join(out)
    assert "[GRASS_FX_TEXTURE_GROUP_0]" in out
    assert "PIECE_0 = 4, 1, 2, 2" in out
    assert "PIECE_0_SIZE_MULT = 1.2, 1.5" in out and "PIECE_0_WIND = 0.5" in out
    assert "PIECE_0_CHANCE" not in text                          # unset -> CSP weight 1
    assert "[GRASS_FX_CONFIGURATION_A]" in out
    assert "TEXTURE_BASE_CHANCE = 0.8" in out and "TEXTURE_GROUP_0_CHANCE = 0.04" in out
    assert "[GRASS_FX_ADJUSTMENT_...]" in out                   # default name = CSP auto-index
    assert "MATERIALS = 1GRASS_0_mat, 1GRASS_1_mat" in out and "MAP = A" in out
    # groups without a texture default to the CSP-embedded highlands atlas (the piece coords index it)
    assert "TEXTURE = grass_fx/highlands.dds" in out and "TEXTURE_GRID = 8, 3" in out
    # TEXTURE_BASE_CHANCE is a configuration key, never accepted at [GRASS_FX] top level
    assert not any(l.startswith("TEXTURE_BASE_CHANCE") for l in out[:out.index("[GRASS_FX_CONFIGURATION_A]")])


def test_grassfx_rect_adjustment():
    cfg = {"configurations": {"B": {"shape_size": [0.6, 1.0], "trim_period": 365}},
           "adjustments": [{"name": "lake_basin", "map": "B, 0.5",
                            "rect": {"center": [120.5, 20, -300], "size": [800, 600], "angle": 12, "fade": 15}}]}
    out = _gfx(cfg)
    i = out.index("[GRASS_FX_ADJUSTMENT_lake_basin]")
    assert out[i + 1:i + 6] == ["CENTER = 120.5, 20, -300", "SIZE = 800, 600", "ANGLE = 12", "FADE = 15",
                                "MAP = B, 0.5"]
    assert "[GRASS_FX_CONFIGURATION_B]" in out and "TRIM_PERIOD = 365" in out


def test_grassfx_rejects_unknown_retired_and_unbound_keys():
    for bad in ({"brightness": 1}, {"health": 1}, {"shape_sise": 1},
                {"texture": "grass_fx/grass_ks.dds"},
                {"configurations": {"E": {}}},                          # dwrite.dll carries exactly A..D
                {"adjustments": [{"materials": ["x"], "map": "A"}]},    # A not defined
                {"mask": "lush"}, {"texture_grid": [8, 3]}):            # unknown preset; grid without texture
        try:
            _gfx(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} must raise ValueError")
    # documentation keys are skipped silently
    assert "[GRASS_FX]" in _gfx({"_doc": "x"})


def test_grassfx_no_occluder_line_when_list_is_empty():
    out = _gfx(occ=())
    assert "[GRASS_FX]" in out
    assert not any(l.startswith("OCCLUDING_MESHES") for l in out)  # never an empty 'OCCLUDING_MESHES ='


# --------------------------------------------------------------------------------- density model ---
def test_elevation_keep_prob_is_monotonic():
    ys = [1000, 1200, 1500, 1800, 2100, 2400]
    ps = [tfx.elevation_keep_prob(y, y_lo=1000, y_hi=2400, keep_lo=0.1, keep_hi=1.0) for y in ys]
    assert ps == sorted(ps)                     # never decreases with elevation
    assert abs(ps[0] - 0.1) < 1e-9 and abs(ps[-1] - 1.0) < 1e-9


def test_density_increases_with_elevation_on_a_ramp():
    # a ramp fixture: 400 candidates evenly spread 1600 m -> 2200 m. The mountain zone (elevation
    # density) must KEEP more trees in the upper half than the lower half.
    zone = tfx.Zone.from_config("forest", {
        "source": "fill_terrain",
        "species": ["MRS_pine_high_2_1.bin"],
        "density": {"by": "elevation", "elev_lo_m": 1600, "elev_hi_m": 2200,
                    "keep_lo": 0.1, "keep_hi": 1.0, "curve": 1.0},
    })
    rng = random.Random(2024)
    n = 400
    low = high = 0
    for i in range(n):
        y = 1600 + (2200 - 1600) * i / (n - 1)
        keep = rng.random() <= zone.keep_prob(y)
        if i < n / 2:
            low += keep
        else:
            high += keep
    assert high > low, (low, high)
    assert high > 1.5 * low                      # clearly denser toward the summit, not marginally


def test_aspect_bonus_favors_north_and_east():
    # NORTH = -Z, EAST = +X (documented convention). A north-facing slope gets the bonus; south none.
    dd = {"by": "elevation", "elev_lo_m": 1000, "elev_hi_m": 2000, "keep_lo": 0.2, "keep_hi": 0.5,
          "aspect_bonus": 0.4, "aspect_favored": ["N", "E"]}
    zone = tfx.Zone.from_config("f", {"density": dd, "species": ["x.bin"]})
    y = 1500
    base = zone.keep_prob(y, aspect=None)
    north = zone.keep_prob(y, aspect=(0.0, -1.0))     # faces north
    south = zone.keep_prob(y, aspect=(0.0, 1.0))      # faces south
    east = zone.keep_prob(y, aspect=(1.0, 0.0))       # faces east
    assert north > base and east > base
    assert abs(south - base) < 1e-9


# --------------------------------------------------------------------------------- creek band ---
def test_creek_band_selects_only_near_water():
    creek = [[(0.0, 0.0), (100.0, 0.0)]]           # a straight creek along z=0, x in [0,100]
    positions = [
        (10.0, 0.0, 5.0),      # 5 m off the bank -> in band
        (50.0, 0.0, 20.0),     # 20 m off -> in a 24 m band
        (50.0, 0.0, 60.0),     # 60 m off -> OUT
        (300.0, 0.0, 0.0),     # far downstream past the segment end -> OUT
    ]
    kept = tfx.select_creek_band(positions, creek, band_m=24.0)
    assert (10.0, 0.0, 5.0) in kept
    assert (50.0, 0.0, 20.0) in kept
    assert (50.0, 0.0, 60.0) not in kept
    assert (300.0, 0.0, 0.0) not in kept
    assert tfx.near_polylines(5.0, 1.0, creek, 24.0) is True
    assert tfx.near_polylines(5.0, 100.0, creek, 24.0) is False


# --------------------------------------------------------------------------------- collector ---
def test_collector_routes_source_to_zone_and_records_species():
    cfg = {
        "enabled": True, "seed": 7,
        "zones": {
            "forest": {"source": "fill_terrain", "species": ["pineA.bin", "pineB.bin"],
                       "size_variance": [0.85, 1.15],
                       "density": {"by": "constant", "keep": 1.0}},
            "riparian": {"source": "creek", "species": ["cottonwood.bin"],
                         "density": {"by": "constant", "keep": 1.0}},
        },
    }
    c = tfx.TreeFXCollector(cfg)
    assert c.has_source("fill_terrain") and c.has_source("creek")
    assert not c.has_source("bush")
    rng = random.Random(1)
    placed = 0
    for i in range(20):
        placed += c.add("fill_terrain", float(i), 1800.0, 0.0, rng=rng)
    assert placed == 20                            # keep=1.0 places all
    assert c.add("bush", 0, 0, 0, rng=rng) is False  # no zone -> never placed
    assert c.add("creek", 5.0, 1500.0, 2.0, rng=rng) is True
    # expected species is the union of DECLARED species (stable across seeds) + placed ones
    assert set(c.expected_species()) == {"pineA.bin", "pineB.bin", "cottonwood.bin"}
    txt = c.trees_txt()
    assert "; --- zone 'forest'" in txt
    assert "configure: size variance = 0.85, 1.15" in txt
    assert "configure: seed = 7" in txt
    assert "tree: cottonwood.bin;" in txt


def test_collector_json_round_trip_is_stable():
    cfg = {
        "enabled": True, "seed": 3, "surface_materials": ["1GRASS_mat"],
        "zones": {"forest": {"source": "fill_terrain", "species": ["p.bin"],
                             "angle_variance": [0, 360],
                             "density": {"by": "constant", "keep": 1.0}}},
    }
    c = tfx.TreeFXCollector(cfg)
    rng = random.Random(0)
    for i in range(5):
        c.add("fill_terrain", float(i), 100.0 + i, -float(i), rng=rng)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "treefx.json"
        c.write_json(p)
        c2 = tfx.TreeFXCollector.from_json(json.loads(p.read_text()))
    assert c2.enabled and c2.surface_materials == ["1GRASS_mat"]
    assert c2.trees_txt() == c.trees_txt()         # rendering survives the round trip byte-for-byte
    assert c2.expected_species() == c.expected_species()


def test_forest3d_size_and_angle_pass_through():
    cfg = {"enabled": True, "zones": {"f": {"source": "forest3d", "species": ["pine.bin"],
                                            "density": {"by": "constant", "keep": 1.0}}}}
    c = tfx.TreeFXCollector(cfg)
    rng = random.Random(0)
    c.add("forest3d", 1.0, 2.0, 3.0, rng=rng, size=3.4, angle=200.0)
    line = [d for d in c.directives() if isinstance(d, tfx.Tree)][0].line()
    assert "pos=1, 2, 3" in line and "size = 3.4" in line and "angle = 200" in line
