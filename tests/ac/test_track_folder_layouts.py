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
