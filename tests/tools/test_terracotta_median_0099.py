"""Ledger 0099 round 3, item 1: Mission Gorge Rd's raised median is terracotta pavers, not grass (Lake Murray 0.20.6).

Four readers are held here, none of them in Blender:
  * scripts/ac/pbr.py, the engine's table: the row 1KERB_PAVER above 1KERB, and NO other mesh name of any track bound
    differently because of it (the Mac, 2026-11-23: "every other track's resolved textures stay identical");
  * tools/author_median_tops_blend.py: which islands the config lists as paved, and what it refuses;
  * tracks/san-diego-lake-murray/textures/make_terracotta_median.py: the toned pair is on the measured tone and holds
    2 x 2 repeats (2.0 m per repeat on the prep's 4 m grid);
  * tools/make_treefx.py, scripts/ac/ext_config.py, scripts/ac/track_folder.py: plants stand on the paved top, no grass
    blade grows on it, and its surface is the KERB row every sidewalk already has (no value invented).
The scene work is self-checked in Blender and measured through the chain's own steps on a scratch workshop
(source/college_r2/scratch/). Plain ``test_*`` for tests/run_tests.py."""
from __future__ import annotations

import importlib.util
import json
import re
import tempfile
from pathlib import Path

from scripts.ac import ext_config, pbr, track_folder

ROOT = Path(__file__).resolve().parents[2]
LM = ROOT / "tracks" / "san-diego-lake-murray"
CFG = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))
SHIP = json.loads((LM / "ship.json").read_text(encoding="utf-8"))
ROW = "1KERB_PAVER"
OBJECT = "1KERB_PAVER_median"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MT = _load("author_median_tops_0099", ROOT / "tools" / "author_median_tops_blend.py")


# ---- the engine's table ---------------------------------------------------------------------------------------------

def test_the_paver_row_stands_above_the_racing_kerb_and_below_no_longer_prefix():
    keys = list(pbr.TEXTURES)
    assert keys.index("1KERB_SIDEWALK") < keys.index("1KERB_RACE") < keys.index(ROW) < keys.index("1KERB")
    assert pbr.match_key(OBJECT) == ROW and pbr.match_key("1kerb_paver_median_3") == ROW
    assert pbr.match_key("1KERB_sidewalk") == "1KERB_SIDEWALK" and pbr.match_key("1KERB_race_lap_college_0") == "1KERB_RACE"
    assert pbr.match_key("1KERB_kerb") == "1KERB" and pbr.match_key("1KERB_corners") == "1KERB"
    # the exporter's own expression (export_kn5_addon.shader_and_textures) is the same first-prefix scan
    assert next(k for k in pbr.TEXTURES if OBJECT.upper().startswith(k)) == ROW
    assert not any(k != ROW and k.startswith(ROW) for k in keys)             # no later row hides behind this one
    assert ROW not in pbr.KS_PROPS and ROW not in pbr.BILLBOARD               # shaded as the sidewalk beside it is
    diff, norm = pbr.TEXTURES[ROW][:2]
    assert (pbr.texture_dir() / diff).exists() and (pbr.texture_dir() / norm).exists()   # the untinted CC0 pair
    assert (diff, norm) == ("terracotta_paver_diffuse.jpg", "terracotta_paver_normal.jpg")
    snap = (LM / "engine-july-snapshot" / "scripts" / "ac" / "pbr.py").read_text(encoding="utf-8")
    assert '"1KERB_PAVER": ("terracotta_paver_diffuse.jpg", "terracotta_paver_normal.jpg"' in snap   # the build's own copy


def _names_the_repo_knows():
    """every mesh-like name written anywhere a track's meshes are named: the table's own keys, and each token that
    starts with a digit-1 surface prefix in the tools, the engine scripts, the tracks' configs and their assemblers"""
    names = set(pbr.TEXTURES)
    tok = re.compile(r"\b1[A-Z][A-Za-z0-9_]{3,}")
    files = list((ROOT / "tools").glob("*.py")) + list((ROOT / "scripts").rglob("*.py"))
    for t in sorted((ROOT / "tracks").iterdir()):
        files += [t / "track.config.json", t / "ship.json"] + list((t / "scripts-v021").rglob("*.py"))
    for f in files:
        if f.is_file():
            names.update(tok.findall(f.read_text(encoding="utf-8", errors="replace")))
    for k in list(pbr.TEXTURES):
        names.update({k + "_0", k.lower() + "_a", k + "x"})
    return names


def _resolve_without_the_row(name, overrides):
    keys = [k for k in pbr.TEXTURES if k != ROW]
    key = next((k for k in keys if name.upper().startswith(k)), None)
    diff, norm = (pbr.TEXTURES[key][0], pbr.TEXTURES[key][1]) if key else (None, None)
    ov = (overrides or {}).get(key or "", {})
    return (key, ov.get("diffuse") or diff, ov.get("normal") or norm)


def test_no_other_mesh_name_of_any_track_is_bound_differently():
    names = _names_the_repo_knows()
    assert len(names) > 300 and "1KERB_sidewalk" in names and "1ROAD_road" in names
    tracks = [t for t in sorted((ROOT / "tracks").iterdir()) if (t / "track.config.json").is_file()]
    assert len(tracks) >= 10
    for t in tracks:
        ov = pbr.load_overrides(t)
        for n in names:
            if n.upper().startswith(ROW):
                continue
            r = pbr.resolve(n, ov)
            now = (r["key"], (ov.get(r["key"] or "", {}).get("diffuse") or pbr.TEXTURES.get(r["key"], (None, None))[0]),
                   (ov.get(r["key"] or "", {}).get("normal") or pbr.TEXTURES.get(r["key"], (None, None))[1]))
            assert now == _resolve_without_the_row(n, ov), (t.name, n)
        if t != LM:                                                          # and no other track names such a mesh or key
            for f in (t / "track.config.json", t / "ship.json"):
                assert ROW not in (f.read_text(encoding="utf-8", errors="replace") if f.is_file() else ""), f
            assert ROW not in ov


def test_lake_murray_tones_the_row_with_its_own_pair_and_touches_no_other_kerb():
    ov = pbr.load_overrides(LM)
    r = pbr.resolve(OBJECT, ov)
    assert r["key"] == ROW and r["overridden"] and r["diffuse"].exists() and r["normal"].exists()
    assert (r["diffuse"].name, r["normal"].name) == ("terracotta_median_diffuse.jpg", "terracotta_median_normal.jpg")
    assert pbr.resolve("1KERB_sidewalk", ov)["diffuse"].name == "concrete_plain_diffuse.jpg"
    assert pbr.resolve("1KERB_race_lap_college_0", ov)["diffuse"].name == "kerb_race_worn_diffuse.jpg"
    for f in ("textures/terracotta_median_diffuse.jpg", "textures/terracotta_median_normal.jpg"):
        assert f in SHIP["sync_in"]["optional"], f                           # carried into the workshop
    lic = json.loads((ROOT / "assets" / "licenses.json").read_text(encoding="utf-8"))
    text = json.dumps(lic)
    assert "terracotta_paver_diffuse.jpg" in text and "terracotta_median_diffuse.jpg" in text and "PavingStones135" in text


# ---- the median step ------------------------------------------------------------------------------------------------

def test_the_config_lists_mission_gorges_islands_as_paved():
    sp = MT.spec(CFG)
    assert sp == {"object": "1LAWN_median",
                  "paver": {"object": OBJECT, "islands": [("north_mission_gorge", 8, 53), ("north_mission_gorge", 67, 354),
                                                          ("north_mission_gorge", 365, 741)]}}   # three since item 1b; rows as the lidar has the islands (item 2)
    isl = MT.islands(LM)
    paved = MT.surfaces(sp, isl)
    assert sorted((isl[i]["line"], isl[i]["first"], isl[i]["last"]) for i in paved) == sp["paver"]["islands"]
    assert set(paved.values()) == {"paver"} and len(isl) - len(paved) == 12   # the other twelve keep their grass
    assert MT.surfaces({"object": "1LAWN_median"}, isl) == {}                 # no paver key: every island grass, as 0.20.5
    assert MT.PAVER_PREFIX == ROW


def test_the_step_refuses_a_paved_top_it_cannot_name_or_place():
    def refused(mt):
        try:
            sp = MT.spec({"route": {"median_tops": mt}})
            MT.surfaces(sp, MT.islands(LM))
        except SystemExit:
            return True
        return False

    ok = {"object": "1LAWN_median", "paver": {"object": OBJECT, "islands": [{"line": "north_mission_gorge", "rows": [8, 53]}]}}
    assert not refused(ok)
    for bad_name in ("1KERB_median", "1LAWN_paver", "1KERB_SIDEWALK_median", "PAVER", ""):
        assert refused({"object": "1LAWN_median", "paver": {"object": bad_name, "islands": ok["paver"]["islands"]}}), bad_name
    for bad_islands in ([], [{"line": "north_mission_gorge"}], [{"rows": [8, 48]}],
                        [{"line": "north_mission_gorge", "rows": [8, 53]}, {"line": "north_mission_gorge", "rows": [8, 53]}],
                        [{"line": "north_mission_gorge", "rows": [8, 50]}],      # not an island as built, row for row
                        [{"line": "north_mission_gorge", "rows": [58, 61]}],     # a run too short to be an island (MD12)
                        [{"line": "no_such_line", "rows": [8, 53]}]):
        assert refused({"object": "1LAWN_median", "paver": {"object": OBJECT, "islands": bad_islands}}), bad_islands


def test_the_step_converges_and_checks_what_it_moves():
    src = (ROOT / "tools" / "author_median_tops_blend.py").read_text(encoding="utf-8")
    for frag in ('move = [t for t in tops if t["src"] != kind_of(t["island"])]',       # a top in the wrong object moves across
                 "nothing to do, nothing saved",                                         # a scene already right is not saved
                 "a scene half moved is not one this tool makes",
                 "is not a deck any more",
                 "listed as paved, with no top in the scene",
                 'if any(pl.normal.z <= 0.0 for pl in me.polygons):'):
        assert frag in src, frag
    # the prep's own lines this step leans on: it pins 1GRASS under 1ROAD only, and seats props on 1GRASS / 1ROAD / 1KERB
    prep = (LM / "engine-july-snapshot" / "scripts" / "ac" / "build_kn5_loop.py").read_text(encoding="utf-8")
    assert 'road_tris = _world_tris(lambda n: n.startswith("1ROAD"))' in prep
    assert 'ground_bvh = _bvh(_world_tris(lambda n: n.startswith(("1GRASS", "1ROAD", "1KERB"))))' in prep
    assert "UV_TILE = 4.0" in prep                                                      # the grid the toned pair is laid for


# ---- the surface, the grass, the plants -----------------------------------------------------------------------------

def test_the_paved_top_is_on_the_kerb_row_every_sidewalk_has():
    ini = track_folder.surfaces_ini(wall=True, kerb_ff_effect=int(CFG.get("kerb_ff_effect") or 0), lawn_as_grass=bool(CFG.get("lawn_as_grass")))
    keys = re.findall(r"^KEY=(\w+)$", ini, flags=re.M)
    assert "KERB" in keys and "PAVER" not in keys and not any(k.startswith("KERB_") for k in keys)
    # AC reads the digits, then the key: the paved top and the sidewalk take the same block
    for name in (OBJECT, "1KERB_sidewalk"):
        assert next(k for k in sorted(keys, key=len, reverse=True) if name[1:].upper().startswith(k)) == "KERB"


def test_grassfx_grows_nothing_on_the_paved_top():
    with tempfile.TemporaryDirectory() as d:
        proj = Path(d)
        (proj / "data").mkdir()
        (proj / "track.config.json").write_text(json.dumps({"slug": "t", "lighting": {"grassfx": True}}), encoding="utf-8")
        (proj / "data" / "environment.obj").write_text("o 1GRASS_0\no 1LAWN_median\no " + OBJECT + "\no 1ROAD_road\n")
        txt = ext_config.generate(proj).read_text(encoding="utf-8")
    grass = [ln for ln in txt.splitlines() if ln.strip().upper().startswith("GRASS_MESHES")]
    assert grass and "1LAWN_median" in grass[0] and "KERB_PAVER" not in grass[0], grass


def test_the_plants_of_a_paved_island_stand_on_its_top():
    mt = _load("make_treefx_0099", ROOT / "tools" / "make_treefx.py")
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    groups = ["1GRASS_1", "1LAWN_median", OBJECT, "1GRASS_0", "1ROAD_road", "1KERB_sidewalk"]
    (d / "data" / "track.obj").write_text("".join(f"o {g}\nusemtl {g}_mat\nv 0 0 0\n" for g in groups), encoding="utf-8")
    (d / "track.config.json").write_text(json.dumps({"slug": "tiny", "route": {"median_tops": {"object": "1LAWN_median"}}}))
    assert mt.surface_materials(d) == "1GRASS_0_mat, 1GRASS_1_mat, 1LAWN_median_mat, 1ROAD_road_mat"
    (d / "track.config.json").write_text(json.dumps({"slug": "tiny", "route": {"median_tops": CFG["route"]["median_tops"]}}))
    assert mt.surface_materials(d) == "1GRASS_0_mat, 1GRASS_1_mat, 1KERB_PAVER_median_mat, 1LAWN_median_mat, 1ROAD_road_mat"


# ---- the toned pair -------------------------------------------------------------------------------------------------

def test_the_toned_pair_is_on_the_measured_tone_and_holds_two_repeats_a_side():
    try:
        from PIL import Image, ImageStat
    except ImportError:                                                       # the pair is checked where Pillow is
        return
    mk = _load("make_terracotta_median_0099", LM / "textures" / "make_terracotta_median.py")
    note = (ROOT / "assets" / "textures" / "terracotta_paver.md").read_text(encoding="utf-8")
    assert "**147.9, 127.8, 115.6**" in note and "166.0, 123.7, 107.8" in note   # the numbers the maker copies
    assert mk.TARGET == (147.9, 127.8, 115.6) and mk.SOURCE_MEAN == (166.0, 123.7, 107.8)
    assert (mk.REPEATS, mk.SIZE) == (2, 2048) and 4.0 / mk.REPEATS == 2.0     # 2.0 m per repeat; the asset says ca. 1.9 m
    assert "ca. 1.9 m" in note
    d = Image.open(LM / "textures" / "terracotta_median_diffuse.jpg").convert("RGB")
    n = Image.open(LM / "textures" / "terracotta_median_normal.jpg").convert("RGB")
    assert d.size == n.size == (2048, 2048)
    mean = ImageStat.Stat(d).mean
    assert all(abs(a - b) <= mk.TOL for a, b in zip(mean, mk.TARGET)), mean
    assert mk.quarters_equal(d) and mk.quarters_equal(n)
    assert mk.check(LM / "textures") == 0
    src = ImageStat.Stat(Image.open(ROOT / "assets" / "textures" / "terracotta_paver_diffuse.jpg").convert("RGB")).mean
    assert all(abs(a - b) <= 0.1 for a, b in zip(src, mk.SOURCE_MEAN)), src   # the untinted asset is the one measured


def test_version_and_the_round():
    assert CFG["version"] == "0.20.8"                 # 0.20.6 was this item's; 0.20.7 road wear (item 3); 0.20.8 Jackson's paint (item 4)
    doc = CFG["route"]["median_tops"]["paver"]["_doc"]
    assert "[inferred from MD13]" in doc and "item 1b" in doc.lower()         # what is inferred, and what item 1b did after it
