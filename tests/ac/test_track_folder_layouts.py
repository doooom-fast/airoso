"""track_folder's multi-layout contract (ledger 0047, fleet/LAWS.md L8 as amended) and the
regression rule for every single-layout track: build/<slug>/ stays byte-identical pack to pack
except for stale structure that never belonged there.

Synthetic project (a 100 m square loop), stub kn5s where only the file names matter. Plain
``test_*`` for tests/run_tests.py (no pytest fixtures).
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from scripts.ac import track_folder as tf
from tools.make_map import map_targets

SLUG = "sq_loop"


def _config(layouts):
    return {"name": "Square Loop", "slug": SLUG, "ui_series": "", "version": "0.1",
            "location": {"lat": 32.78, "lon": -117.04, "timezone": "America/Los_Angeles",
                         "city": "San Diego", "country": "United States"},
            "source": {"type": "osm"}, "loop": True, "mirror_x": False, "default_width_m": 12.0,
            "origin": "centroid", "surfaces": {"road": "1ROAD"}, "lighting": {},
            "layouts": layouts}


_THREE = [
    {"id": "street", "name": "Street Loop", "kind": "street", "direction": "forward",
     "race_furniture": False, "run": "open two-way street"},
    {"id": "race_cw", "name": "Race — Clockwise", "kind": "race", "direction": "forward",
     "race_furniture": True, "run": "clockwise, one-way"},
    {"id": "race_acw", "name": "Race — Anticlockwise", "kind": "race", "direction": "reverse",
     "race_furniture": True, "run": "anticlockwise, one-way"},
]


def _project(root: Path, layouts, *, kn5s=(), dummies_for=(), ai_root=False, ai_layouts=()) -> Path:
    d = root / "proj"
    data = d / "data"
    data.mkdir(parents=True)
    (d / "track.config.json").write_text(json.dumps(_config(layouts)), encoding="utf-8")
    pts = ([[float(x), 0.0, 0.0] for x in range(0, 100)] + [[100.0, 0.0, float(z)] for z in range(0, 100)]
           + [[float(100 - x), 0.0, 100.0] for x in range(0, 100)] + [[0.0, 0.0, float(100 - z)] for z in range(0, 100)])
    pts.append(pts[0])
    (data / "centerline.local.json").write_text(json.dumps({"points_xyz_m": pts, "widths_m": [12.0] * len(pts)}))
    (data / "centerline.geojson").write_text(json.dumps(
        {"features": [{"geometry": {"type": "LineString", "coordinates": [[-117.04, 32.78], [-117.03, 32.78]]},
                       "properties": {"length_m": 400.0}}]}))
    (data / "dummies.json").write_text(json.dumps({f"AC_PIT_{i}": [0, 0, 0] for i in range(4)}))
    (d / "loop.blend").write_bytes(b"")                      # Blender-first track: WALL surface entry
    (d / "build").mkdir()
    for name in kn5s:
        (d / "build" / name).write_bytes(b"sc6969" + name.encode())
    for lid in dummies_for:
        (data / f"dummies_{lid}.json").write_text(json.dumps({f"AC_PIT_{i}": [0, 0, 0] for i in range(8)}))
    if ai_root:
        (d / "ai").mkdir()
        (d / "ai" / "fast_lane.ai").write_bytes(b"ROOT")
    for lid in ai_layouts:
        (d / "ai" / lid).mkdir(parents=True, exist_ok=True)
        (d / "ai" / lid / "fast_lane.ai").write_bytes(b"LAYOUT " + lid.encode())
    return d


def _ini_models(p: Path) -> list[str]:
    return [ln.split("=", 1)[1] for ln in p.read_text().splitlines() if ln.startswith("FILE=")]


def _md5_tree(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.md5(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def test_three_layouts_pack_the_0047_shape():
    with tempfile.TemporaryDirectory() as td:
        d = _project(Path(td), _THREE,
                     kn5s=(f"{SLUG}.kn5", f"{SLUG}_race.kn5", f"{SLUG}__street.kn5",
                           f"{SLUG}__race_cw.kn5", f"{SLUG}__race_acw.kn5", f"{SLUG}__full.kn5"),
                     dummies_for=("street", "race_cw", "race_acw"),
                     ai_root=True, ai_layouts=("race_cw", "race_acw"))
        out = d / "build" / SLUG
        # stale single-layout + retired-layout structure from an earlier pack
        (out / "ui" / "full").mkdir(parents=True)
        (out / "ui" / "ui_track.json").write_text("{}")
        (out / "full" / "data").mkdir(parents=True)
        (out / "full" / "map.png").write_bytes(b"x")
        (out / "ai").mkdir()
        (out / "ai" / "fast_lane.ai").write_bytes(b"x")
        (out / "models.ini").write_text("x")
        (out / "models_full.ini").write_text("x")
        info = tf.generate(d)
        assert info["layouts"] == ["street", "race_cw", "race_acw"]
        assert sorted(p.name for p in out.glob("models*.ini")) == \
            ["models_race_acw.ini", "models_race_cw.ini", "models_street.ini"]
        # the kn5 set each layout loads: shared road first, race furniture only for race layouts,
        # the layout's own spawn kn5 LAST
        assert _ini_models(out / "models_street.ini") == [f"{SLUG}.kn5", f"{SLUG}__street.kn5"]
        assert _ini_models(out / "models_race_cw.ini") == [f"{SLUG}.kn5", f"{SLUG}_race.kn5", f"{SLUG}__race_cw.kn5"]
        assert _ini_models(out / "models_race_acw.ini") == [f"{SLUG}.kn5", f"{SLUG}_race.kn5", f"{SLUG}__race_acw.kn5"]
        for name in (f"{SLUG}_race.kn5", f"{SLUG}__street.kn5", f"{SLUG}__race_cw.kn5", f"{SLUG}__race_acw.kn5"):
            assert (out / name).exists(), name
        assert not (out / f"{SLUG}__full.kn5").exists()          # retired id: never copied
        # ui per layout: name suffix from layouts[].name, run from layouts[].run, pits from dummies_<id>
        for lo in _THREE:
            ui = json.loads((out / "ui" / lo["id"] / "ui_track.json").read_text(encoding="utf-8"))
            assert ui["name"] == f"Square Loop — {lo['name']}", ui["name"]
            assert ui["run"] == lo["run"]
            assert ui["pitboxes"] == "8"
            assert "circuit" in ui["tags"]
            assert (out / lo["id"] / "map.png").exists() and (out / lo["id"] / "data" / "surfaces.ini").exists()
            assert "KEY=WALL" in (out / lo["id"] / "data" / "surfaces.ini").read_text()
        # ai: the layout's own ai/<id>/ first, the project ai/ for a layout without one
        assert (out / "race_cw" / "ai" / "fast_lane.ai").read_bytes() == b"LAYOUT race_cw"
        assert (out / "race_acw" / "ai" / "fast_lane.ai").read_bytes() == b"LAYOUT race_acw"
        assert (out / "street" / "ai" / "fast_lane.ai").read_bytes() == b"ROOT"
        assert not (out / "street" / "ai" / "README.txt").exists()
        # stale structure gone: NEVER both shapes in one folder
        for stale in ("models.ini", "models_full.ini", "ui/full", "ui/ui_track.json", "full", "ai"):
            assert not (out / stale).exists(), stale
        # make_map targets the root and every layout dir the inis name
        assert sorted(p.name for p in map_targets(out)) == sorted([SLUG, "race_acw", "race_cw", "street"])


def test_race_layout_without_the_race_kn5_is_a_hard_error():
    with tempfile.TemporaryDirectory() as td:
        d = _project(Path(td), _THREE,
                     kn5s=(f"{SLUG}.kn5", f"{SLUG}__street.kn5", f"{SLUG}__race_cw.kn5", f"{SLUG}__race_acw.kn5"),
                     dummies_for=("street", "race_cw", "race_acw"))
        try:
            tf.generate(d)
        except FileNotFoundError as e:
            assert f"{SLUG}_race.kn5" in str(e)
        else:
            raise AssertionError("a race layout must not pack silently plain")
        # nothing half-packed: the error fires before any ini is written
        assert not list((d / "build" / SLUG).glob("models*.ini")) if (d / "build" / SLUG).exists() else True
        # dry runs lay the folder out anyway, inis still naming the file
        info = tf.generate(d, strict_kn5=False)
        assert info["models"]["race_cw"] == [f"{SLUG}.kn5", f"{SLUG}_race.kn5", f"{SLUG}__race_cw.kn5"]
        assert not (d / "build" / SLUG / f"{SLUG}_race.kn5").exists()


def test_declared_spawn_set_without_its_kn5_is_a_hard_error():
    with tempfile.TemporaryDirectory() as td:
        d = _project(Path(td), _THREE,
                     kn5s=(f"{SLUG}.kn5", f"{SLUG}_race.kn5", f"{SLUG}__street.kn5", f"{SLUG}__race_cw.kn5"),
                     dummies_for=("street", "race_cw", "race_acw"))
        try:
            tf.generate(d)
        except FileNotFoundError as e:
            assert f"{SLUG}__race_acw.kn5" in str(e)
        else:
            raise AssertionError("a layout with dummies_<id>.json and no spawn kn5 has no grid")


def test_race_furniture_needs_kind_race():
    with tempfile.TemporaryDirectory() as td:
        bad = [dict(_THREE[0]), dict(_THREE[1])]
        bad[1]["kind"] = "street"
        d = _project(Path(td), bad, kn5s=(f"{SLUG}.kn5", f"{SLUG}_race.kn5"))
        try:
            tf.generate(d)
        except ValueError as e:
            assert "race_furniture" in str(e)
        else:
            raise AssertionError("race_furniture on a non-race layout must fail")


def test_single_layout_is_byte_identical_pack_to_pack_and_sheds_stale_dirs():
    with tempfile.TemporaryDirectory() as td:
        d = _project(Path(td), [{"id": "full"}], kn5s=(f"{SLUG}.kn5",), ai_root=True)
        out = d / "build" / SLUG
        tf.generate(d)
        first = _md5_tree(out)
        assert "models.ini" in first and "ui/ui_track.json" in first and "ai/fast_lane.ai" in first
        assert not [k for k in first if k.startswith("models_")]
        ui = json.loads((out / "ui" / "ui_track.json").read_text(encoding="utf-8"))
        assert ui["name"] == "Square Loop" and ui["run"] == "clockwise"       # no suffix, old run text
        # stale multi-layout leftovers appear (an earlier pack of the other shape) …
        (out / "ui" / "old").mkdir()
        (out / "ui" / "old" / "ui_track.json").write_text("{}")
        (out / "old" / "data").mkdir(parents=True)
        (out / "old" / "map.png").write_bytes(b"x")
        (out / "models_old.ini").write_text("x")
        tf.generate(d)
        second = _md5_tree(out)
        # … and the second pack is byte-identical to the first except for their removal
        assert second == first, {k: (first.get(k), second.get(k)) for k in set(first) | set(second)
                                 if first.get(k) != second.get(k)}
        assert not (out / "ui" / "old").exists() and not (out / "old").exists() and not (out / "models_old.ini").exists()
        assert map_targets(out) == [out]


def test_models_ini_extras_in_load_order_and_old_call_shape():
    assert tf.models_ini("a.kn5") == "[MODEL_0]\nFILE=a.kn5\nPOSITION=0,0,0\nROTATION=0,0,0\n"
    two = tf.models_ini("a.kn5", ["a_race.kn5", "a__x.kn5"])
    assert _ini_models_text(two) == ["a.kn5", "a_race.kn5", "a__x.kn5"]
    assert "[MODEL_2]" in two
    assert tf.models_ini("a.kn5", "a__x.kn5") == tf.models_ini("a.kn5", ["a__x.kn5"])


def _ini_models_text(s: str) -> list[str]:
    return [ln.split("=", 1)[1] for ln in s.splitlines() if ln.startswith("FILE=")]


# --- 0047 fix round: previews on every OS (finding D), honest ui text and README (finding E) -------

def test_every_layout_gets_a_preview_png_without_qlmanage_and_no_svg_is_left():
    import shutil
    from PIL import Image
    real_which = shutil.which
    shutil.which = lambda *a, **k: None                      # no qlmanage anywhere (Windows, Linux)
    try:
        with tempfile.TemporaryDirectory() as td:
            d = _project(Path(td), _THREE,
                         kn5s=(f"{SLUG}.kn5", f"{SLUG}_race.kn5", f"{SLUG}__street.kn5",
                               f"{SLUG}__race_cw.kn5", f"{SLUG}__race_acw.kn5"),
                         dummies_for=("street", "race_cw", "race_acw"))
            out = d / "build" / SLUG
            (out / "ui" / "street").mkdir(parents=True)
            (out / "ui" / "street" / "preview.svg").write_text("<svg/>")   # an older Windows pack's leftover
            tf.generate(d)
            for lo in _THREE:
                ui = out / "ui" / lo["id"]
                assert (ui / "preview.png").exists(), lo["id"]
                assert not (ui / "preview.svg").exists(), lo["id"]
                im = Image.open(ui / "preview.png").convert("RGB")
                assert im.size == (600, 600)
                # the dark background with the red outline drawn on it — not an empty canvas
                assert im.getpixel((2, 2)) == (0x0c, 0x11, 0x16)
                assert any(px[0] > 200 and px[1] < 120 for px in im.getdata()), "no outline drawn"
    finally:
        shutil.which = real_which


def test_svg_raster_draws_the_engines_own_elements():
    from PIL import Image
    from scripts.ac.svg_raster import rasterize_svg
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20" viewBox="0 0 80 40">'
           '<rect width="100%" height="100%" fill="#102030"/>'
           '<polygon points="0,0 40,0 0,40" fill="rgb(200, 10, 10)"/>'
           '<line x1="60" y1="0" x2="60" y2="40" stroke="#00ff00" stroke-width="8"/>'
           '<polyline points="44,38 78,38" fill="none" stroke="#0000ff" stroke-width="4"/>'
           '<text x="1" y="1">ignored</text></svg>')
    with tempfile.TemporaryDirectory() as td:
        png = Path(td) / "p.png"
        assert rasterize_svg(svg, png)
        im = Image.open(png).convert("RGB")
        assert im.size == (40, 20)                                  # width/height, viewBox scaled into it
        r, g, b = im.getpixel((2, 2))
        assert r > 150 and g < 60                                   # the polygon
        r, g, b = im.getpixel((30, 10))
        assert g > 150 and r < 80                                   # the line
        assert im.getpixel((15, 15)) == (0x10, 0x20, 0x30)           # background
        assert rasterize_svg(svg, png, size=100) and Image.open(png).size == (100, 50)
        assert not rasterize_svg('<svg width="10" height="10"><rect width="100%" height="100%" fill="#000"/></svg>',
                                 Path(td) / "none.png")
        assert not (Path(td) / "none.png").exists()


def test_ui_track_json_text_per_layout_tags_and_width():
    from scripts.config import load_config
    layouts = [dict(_THREE[0], ui_description="the open street"), dict(_THREE[1], ui_tags=["street", "race"]),
               dict(_THREE[2])]
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "track.config.json"
        p.write_text(json.dumps(dict(_config(layouts), archetype="real_road", ui_description="track text",
                                     ui_tags=["street", "loop", "real-roads"])), encoding="utf-8")
        cfg = load_config(p)
        st = tf.ui_track_json(cfg, "street", 13489.7, 8, 13.0)
        cw = tf.ui_track_json(cfg, "race_cw", 13489.7, 8, 13.0)
        acw = tf.ui_track_json(cfg, "race_acw", 13489.7, 8)
        assert st["description"] == "[build 0.1] the open street"           # the layout's own text first
        assert acw["description"] == "[build 0.1] track text"               # else the track's
        assert st["tags"] == ["circuit", "street", "loop", "real-roads"]     # circuit for CM race modes
        assert cw["tags"] == ["circuit", "street", "race"]
        assert st["width"] == "13" and acw["width"] == "12"                 # measured, else default_width_m
        assert st["length"] == "13490"
        # the engine default no longer calls a real-roads loop fictional; an invented circuit still is
        p.write_text(json.dumps(dict(_config(_THREE), archetype="real_road")), encoding="utf-8")
        assert "fictional" not in tf.ui_track_json(load_config(p), "street", 1000.0, 1)["tags"]
        p.write_text(json.dumps(dict(_config(_THREE), archetype="street_circuit")), encoding="utf-8")
        assert "fictional" in tf.ui_track_json(load_config(p), "street", 1000.0, 1)["tags"]
        p.write_text(json.dumps(dict(_config(_THREE), ui_width_m=14.5)), encoding="utf-8")
        assert tf.ui_track_json(load_config(p), "street", 1000.0, 1, 13.0)["width"] == "14"


def test_readme_says_what_the_folder_is_and_where_it_installs():
    with tempfile.TemporaryDirectory() as td:
        d = _project(Path(td), _THREE,
                     kn5s=(f"{SLUG}.kn5", f"{SLUG}_race.kn5", f"{SLUG}__street.kn5",
                           f"{SLUG}__race_cw.kn5", f"{SLUG}__race_acw.kn5"),
                     dummies_for=("street", "race_cw", "race_acw"), ai_layouts=("street", "race_cw", "race_acw"))
        cfg = json.loads((d / "track.config.json").read_text(encoding="utf-8"))
        cfg["install_folder"] = "sq_loop_v3"
        (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
        for lid in ("street", "race_cw", "race_acw"):
            (d / "ai" / lid / "ai_draft.json").write_text("{}")             # write_ai_line's draft marker
        tf.generate(d)
        text = (d / "build" / SLUG / "README.txt").read_text(encoding="utf-8")
        assert "STILL NEEDED" not in text and "prodrive-ac-builder" not in text
        assert "airoso" in text
        assert "content/tracks/sq_loop_v3/" in text
        for lo in _THREE:
            assert f"{lo['name']} ({lo['id']})" in text
        assert f"{SLUG}_race.kn5" in text                                   # what the race layouts load
        assert "GENERATED DRAFT" in text
        # a line without write_ai_line's ai_draft.json is never called a draft (nor a recording)
        (d / "ai" / "street" / "ai_draft.json").unlink()
        tf.generate(d)
        text = (d / "build" / SLUG / "README.txt").read_text(encoding="utf-8")
        assert "AI (street): shipped from the project's ai/" in text and "AI (race_cw): a GENERATED DRAFT" in text


# --- ledger 0049: race corridors — each race layout loads the common race kn5 + its OWN closure kn5 --------

_CORRIDOR = [dict(_THREE[0]), dict(_THREE[1], closure_token="cw"), dict(_THREE[2], closure_token="acw")]
_CORRIDOR_KN5 = (f"{SLUG}.kn5", f"{SLUG}_race.kn5", f"{SLUG}_closure_race_cw.kn5", f"{SLUG}_closure_race_acw.kn5",
                 f"{SLUG}__street.kn5", f"{SLUG}__race_cw.kn5", f"{SLUG}__race_acw.kn5")


def _corridor_project(root: Path, layouts=None, kn5s=_CORRIDOR_KN5) -> Path:
    d = _project(root, layouts or _CORRIDOR, kn5s=kn5s, dummies_for=("street", "race_cw", "race_acw"))
    cfg = json.loads((d / "track.config.json").read_text(encoding="utf-8"))
    cfg["race"] = {"corridor": {"clear_width_m": 11.36}}
    (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return d


def test_corridor_race_layouts_load_their_own_closure_and_never_the_other():
    with tempfile.TemporaryDirectory() as td:
        d = _corridor_project(Path(td))
        out = d / "build" / SLUG
        out.mkdir(parents=True)
        (out / f"{SLUG}_closure_race_old.kn5").write_bytes(b"stale")            # a retired layout's closure
        info = tf.generate(d)
        assert _ini_models(out / "models_race_cw.ini") == \
            [f"{SLUG}.kn5", f"{SLUG}_race.kn5", f"{SLUG}_closure_race_cw.kn5", f"{SLUG}__race_cw.kn5"]
        assert _ini_models(out / "models_race_acw.ini") == \
            [f"{SLUG}.kn5", f"{SLUG}_race.kn5", f"{SLUG}_closure_race_acw.kn5", f"{SLUG}__race_acw.kn5"]
        assert _ini_models(out / "models_street.ini") == [f"{SLUG}.kn5", f"{SLUG}__street.kn5"]
        assert f"{SLUG}_closure_race_acw.kn5" not in (out / "models_race_cw.ini").read_text()
        assert f"{SLUG}_closure_race_cw.kn5" not in (out / "models_race_acw.ini").read_text()
        for name in (f"{SLUG}_closure_race_cw.kn5", f"{SLUG}_closure_race_acw.kn5"):
            assert (out / name).read_bytes() == b"sc6969" + name.encode()
        assert not (out / f"{SLUG}_closure_race_old.kn5").exists()
        assert info["models"]["race_cw"][2] == f"{SLUG}_closure_race_cw.kn5"
        readme = (out / "README.txt").read_text(encoding="utf-8")
        assert f"{SLUG}_closure_race_cw.kn5" in readme and "OWN" in readme


def test_a_missing_closure_kn5_is_a_hard_error_and_dry_runs_still_name_it():
    with tempfile.TemporaryDirectory() as td:
        d = _corridor_project(Path(td), kn5s=tuple(k for k in _CORRIDOR_KN5 if "closure_race_acw" not in k))
        try:
            tf.generate(d)
        except FileNotFoundError as e:
            assert f"{SLUG}_closure_race_acw.kn5" in str(e)
        else:
            raise AssertionError("a corridor race layout must not pack without its closure walls")
        info = tf.generate(d, strict_kn5=False)
        assert info["models"]["race_acw"] == [f"{SLUG}.kn5", f"{SLUG}_race.kn5", f"{SLUG}_closure_race_acw.kn5",
                                              f"{SLUG}__race_acw.kn5"]


def test_closure_tokens_must_make_a_whole_declaration():
    with tempfile.TemporaryDirectory() as td:
        bad_sets = ([dict(_THREE[0]), dict(_THREE[1], closure_token="cw"), dict(_THREE[2])],          # acw has none
                    [dict(_THREE[0]), dict(_THREE[1], closure_token="cw"), dict(_THREE[2], closure_token="cw")],
                    [dict(_THREE[0], closure_token="st"), dict(_THREE[1], closure_token="cw"),
                     dict(_THREE[2], closure_token="acw")])                                             # street has one
        for i, layouts in enumerate(bad_sets):
            d = _corridor_project(Path(td) / str(i), layouts=layouts)
            try:
                tf.generate(d)
            except ValueError as e:
                assert "closure_token" in str(e), e
            else:
                raise AssertionError(f"declaration {i} must be refused")
        # no corridor and no tokens: the 0047 shape (no closure kn5) — test_three_layouts_pack_the_0047_shape
        assert tf.closure_kn5_name({"slug": "s", "layouts": _THREE}, _THREE[1]) is None
