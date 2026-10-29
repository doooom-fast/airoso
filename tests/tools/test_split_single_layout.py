"""The split (tools/split_exports_blend.py) on a SINGLE-layout track — the four of ledger 0060 (Exotics, Milford, High
Plains, Sand Creek's first pass). The Exotics run of 2026-10-29 stopped at the split with three PROBLEMs it could not
have satisfied: no race furniture (no layout declares any), no curb strip in a race scene it had no reason to write,
no data/dummies_full.json (the prep bakes a single layout's AC_* into the road scene; scripts/ac/build_kn5_loop.py,
and verify_kn5's single-layout branch judges them in <slug>.kn5).

The rule: one layouts[] entry = loop_main.blend KEEPS every AC_* object, no spawn scene, no race scene unless a layout
declares race_furniture; a single-layout road scene with no AC_* object is the PROBLEM. More than one entry = the
multi-layout rule as before (the AC_* leave the road scene; a layout without its dummies_<id>.json is a PROBLEM).

The scene parts need the ``bpy`` module (Blender 4.2 as a pip module); where it is absent they are skipped with a
note. Plain ``test_*`` for tests/run_tests.py."""
from __future__ import annotations

import json
import runpy
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "split_exports_blend.py"
TEXT = TOOL.read_text(encoding="utf-8")


def _bpy():
    try:
        import bpy
    except ImportError:
        print("  (no bpy module — the split's scene cases skipped; the text case ran)")
        return None
    return bpy


def _project(tmp: Path, layouts: list[dict]) -> Path:
    proj = tmp / "proj"
    (proj / "data").mkdir(parents=True)
    (proj / "track.config.json").write_text(json.dumps({"slug": "t", "layouts": layouts}), encoding="utf-8")
    # what the multi-layout spawn pass reads (rf.load_centerline): a short straight line
    pts = [[0.0, 0.0, 3.0 * k] for k in range(20)]
    (proj / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": pts, "widths_m": [10.0] * 20}),
                                                          encoding="utf-8")
    return proj


AC_NODES = ("AC_START_0", "AC_PIT_0", "AC_TIME_0_L", "AC_TIME_0_R", "AC_HOTLAP_START_0")


def _prepped_blend(bpy, path: Path) -> None:
    """what the prep leaves for a single layout: a 1ROAD mesh + the AC_* empties it baked in"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new("1ROAD_road")
    me.from_pydata([(0, 0, 0), (10, 0, 0), (10, 60, 0), (0, 60, 0)], [], [(0, 1, 2, 3)])
    me.update()
    ob = bpy.data.objects.new("1ROAD_road", me)
    ob.data.materials.append(bpy.data.materials.new("1ROAD_road"))
    bpy.context.scene.collection.objects.link(ob)
    for name in AC_NODES:
        e = bpy.data.objects.new(name, None)
        e.location = (5.0, 10.0, 0.0)
        bpy.context.scene.collection.objects.link(e)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=False)


def _run_split(blend: Path, proj: Path, out: Path) -> int:
    argv = sys.argv
    sys.argv = [str(TOOL), "--", str(blend), "--project", str(proj), "--out-dir", str(out)]
    try:
        runpy.run_path(str(TOOL), run_name="__main__")
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1
    finally:
        sys.argv = argv


def _names(bpy, blend: Path) -> set[str]:
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    return {o.name for o in bpy.data.objects}


def test_the_rule_is_stated_and_keyed_on_the_configs_layout_count():
    assert "SINGLE-layout track" in TEXT and "KEEPS every AC_* object" in TEXT
    assert "multi = len([lo for lo in (cfg.get(\"layouts\") or [])" in TEXT
    assert "has_main = bool(race_ids) and None in LAP.groups(cfg)" in TEXT
    assert "_remove(race | (ac if multi else set()) | street_in)" in TEXT
    assert "if race_ids and not race:" in TEXT
    assert "single layout but no AC_* node in the prepped scene" in TEXT
    assert "for lo in (layouts if multi else []):" in TEXT


def test_a_single_layout_keeps_its_ac_nodes_in_the_road_scene_and_writes_no_race_or_spawn_scene():
    bpy = _bpy()
    if bpy is None:
        return
    tmp = Path(tempfile.mkdtemp())
    proj = _project(tmp, [{"id": "full", "ai": "ai/full"}])
    blend = proj / "blender" / "t.blend"
    _prepped_blend(bpy, blend)
    out = proj / "blender" / "split"
    out.mkdir()
    (out / "loop_race.blend").write_bytes(b"stale")           # a failed earlier run's race scene never rides along
    (out / "loop_spawn_full.blend").write_bytes(b"stale")
    rc = _run_split(blend, proj, out)
    manifest = json.loads((out / "split_manifest.json").read_text(encoding="utf-8"))
    assert rc == 0 and manifest["problems"] == [], (rc, manifest["problems"])
    main = manifest["outputs"]["loop_main.blend"]
    assert sorted(main["ac_nodes"]) == sorted(AC_NODES) and main["meshes"] == 1
    assert set(manifest["outputs"]) == {"loop_main.blend"}
    assert not (out / "loop_race.blend").exists() and not (out / "loop_spawn_full.blend").exists()
    assert _names(bpy, out / "loop_main.blend") == {"1ROAD_road", *AC_NODES}
    assert _names(bpy, blend) == {"1ROAD_road", *AC_NODES}, "the input is never saved over"


def test_a_single_layout_road_scene_without_ac_nodes_is_the_problem():
    bpy = _bpy()
    if bpy is None:
        return
    tmp = Path(tempfile.mkdtemp())
    proj = _project(tmp, [{"id": "full"}])
    blend = proj / "blender" / "t.blend"
    _prepped_blend(bpy, blend)
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    for name in AC_NODES:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=False)
    out = proj / "blender" / "split"
    rc = _run_split(blend, proj, out)
    manifest = json.loads((out / "split_manifest.json").read_text(encoding="utf-8"))
    assert rc == 1 and any("single layout but no AC_* node" in p for p in manifest["problems"]), manifest["problems"]


def test_the_multi_layout_rule_is_unchanged():
    bpy = _bpy()
    if bpy is None:
        return
    tmp = Path(tempfile.mkdtemp())
    proj = _project(tmp, [{"id": "a"}, {"id": "b"}])
    blend = proj / "blender" / "t.blend"
    _prepped_blend(bpy, blend)                                # (a multi-layout prep bakes none; the split strips any)
    out = proj / "blender" / "split"
    rc = _run_split(blend, proj, out)
    manifest = json.loads((out / "split_manifest.json").read_text(encoding="utf-8"))
    assert rc == 1, manifest["problems"]
    assert manifest["outputs"]["loop_main.blend"]["ac_nodes"] == [], "a multi-layout road scene is spawn-free"
    assert {p for p in manifest["problems"] if p.startswith("spawn_")} == {"spawn_a: no dummies_a.json",
                                                                           "spawn_b: no dummies_b.json"}
    assert not any("race furniture" in p for p in manifest["problems"]), "no layout declares race_furniture"
    assert not (out / "loop_race.blend").exists()
