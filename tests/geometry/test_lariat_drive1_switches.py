"""The Lariat's Drive-1 build switches in build_mesh: each is opt-in, and absent it every track builds as before.

- ``road_profile.fold_plateaus: false`` (V3-PLAN A2, ledger 0048): a fitted hairpin is a graded corner, kept on its
  real profile; the +-40 m plateau loop is skipped. Absent: unchanged.
- ``road_profile.fold_pads`` (ledger 0074): off by default since #29; the Lariat states false: no disc, no flat zone.
- ``road_edge.draft_walls: false`` (V3-PLAN A13 / P3d): the draft writes none of the engine's rule-placed walls.
- ``terrain.cross_section.build: true`` (V3-PLAN P3a): the road-building section grades the ground (cutfill.py).

A full mesh build is too slow for the suite (the Lariat's takes ~2 min), so this checks each switch and reads build()'s
source for the loops and branches it must gate.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "scripts" / "geometry" / "build_mesh.py"


def _build_src() -> str:
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build")
    return ast.unparse(fn)


def _for_loops_over(target: str) -> list[ast.For]:
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build")
    return [n for n in ast.walk(fn) if isinstance(n, ast.For) and isinstance(n.target, ast.Name)
            and n.target.id == target]


def test_switches_default_to_the_old_build():
    from scripts.geometry.build_mesh import draft_walls_enabled, fold_pads_enabled, fold_plateaus_enabled
    from scripts.geometry.cutfill import section_enabled
    for cfg in ({}, {"road_profile": None, "road_edge": None, "terrain": None}, {"road_profile": {}, "road_edge": {}},
                {"terrain": {"cross_section": {}}}):
        assert fold_plateaus_enabled(cfg) is True
        assert fold_pads_enabled(cfg) is False   # main's default since #29 (ledger 0074): pads off
        assert draft_walls_enabled(cfg) is True
        assert section_enabled(cfg) is False
    # only an explicit value flips each one
    assert fold_plateaus_enabled({"road_profile": {"fold_plateaus": 0}}) is True
    assert fold_plateaus_enabled({"road_profile": {"fold_plateaus": False}}) is False
    assert fold_pads_enabled({"road_profile": {"fold_pads": False}}) is False
    assert draft_walls_enabled({"road_edge": {"draft_walls": False}}) is False
    assert section_enabled({"terrain": {"cross_section": {"build": 1}}}) is False
    assert section_enabled({"terrain": {"cross_section": {"build": True}}}) is True


def test_the_plateau_and_pad_loops_are_gated():
    plateau = [n for n in _for_loops_over("_ax") if "_t * _t * (3.0 - 2.0 * _t)" in ast.unparse(n)
               and "centerline[_i] =" in ast.unparse(n)]
    assert len(plateau) == 1, "the fold plateau loop not found"
    assert ast.unparse(plateau[0].iter) == "_apexes if _plateaus_on else []", ast.unparse(plateau[0].iter)
    disc = [n for n in _for_loops_over("_ax") if "_disc_apexes.append" in ast.unparse(n)]
    assert len(disc) == 1
    assert ast.unparse(disc[0].iter) == "_apexes if _pads_on else []", ast.unparse(disc[0].iter)
    src = _build_src()
    assert "_plateaus_on = fold_plateaus_enabled(cfg_raw)" in src
    assert "_pads_on = fold_pads_enabled(cfg_raw)" in src


def test_walls_and_section_are_gated():
    src = _build_src()
    assert "if not draft_walls_enabled(cfg_raw):" in src
    assert "if cutfill_mod.section_enabled(cfg_raw):" in src
    # the old grading still runs whenever the section is off, and the old shoulder keeps its apron rule
    assert "if _cutfill is None:\n        _grade_band = ribbon.grade_embankment(" in src
    assert "fill_apron=_cutfill is None and str(cfg_raw.get('road_surface', 'tarmac')) == 'tarmac'" in src
    # no empty 1GRASS_cutfill group is ever written (an OBJ without the section is byte-identical)
    assert "split_mesh_under_cap('1GRASS_cutfill', 'grass', _shoulder_face) if _shoulder_face['tris'] else []" in src


def test_the_lariat_opts_in():
    cfg = json.loads((ROOT / "tracks" / "lookout-lariat" / "track.config.json").read_text(encoding="utf-8"))
    from scripts.geometry.build_mesh import draft_walls_enabled, fold_pads_enabled, fold_plateaus_enabled
    from scripts.geometry.cutfill import section_enabled
    assert fold_plateaus_enabled(cfg) is False
    assert fold_pads_enabled(cfg) is False
    assert draft_walls_enabled(cfg) is False
    assert section_enabled(cfg) is True
    # A2: C1's 14 m widening stays OFF for Drive 1 (kept in _history, one switch away)
    assert not (cfg.get("route") or {}).get("wide_corners")
    assert (cfg.get("_history") or {}).get("route.wide_corners")


def test_no_other_track_opts_in():
    from scripts.geometry.build_mesh import draft_walls_enabled, fold_plateaus_enabled
    from scripts.geometry.cutfill import section_enabled
    for p in sorted((ROOT / "tracks").glob("*/track.config.json")):
        if p.parent.name == "lookout-lariat":
            continue
        sp = p.parent / "ship.json"
        if sp.exists() and json.loads(sp.read_text(encoding="utf-8")).get("engine") == "lm-v4":
            continue        # an LM-engine port (ledger 0078): build_mesh never runs on it, so its switches are unread
        cfg = json.loads(p.read_text(encoding="utf-8"))
        assert fold_plateaus_enabled(cfg) is True, p
        assert draft_walls_enabled(cfg) is True, p
        assert section_enabled(cfg) is False, p
