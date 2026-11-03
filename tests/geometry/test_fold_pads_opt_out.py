"""Fold pads are OFF by default; road_profile.fold_pads: true opts in (ledger 0074). Off drops the pad and its flat zone, and nothing else.

At a fold apex build_mesh plateaus the profile over +-40 m and, where the +-60 m chord grade is under 2.5 %, lays a
paved disc and a w/2 + 16 m flat zone that snaps every pavement vertex inside it to the apex height. On Aspen's final
hairpin the corner climbs ~2.4 % while the chord reads 0.9 %, so the zone's rims were 17 severe steps. The opt-out is
per track; every track without the key must build exactly as before. A full mesh build is too slow for the suite, so
this checks the switch and reads build()'s source for the two loops it must (and must not) gate.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "scripts" / "geometry" / "build_mesh.py"


def _build_fn() -> ast.FunctionDef:
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build")


def _for_loops_over(fn: ast.FunctionDef, target: str) -> list[ast.For]:
    return [n for n in ast.walk(fn) if isinstance(n, ast.For) and isinstance(n.target, ast.Name)
            and n.target.id == target]


def test_switch_defaults_off():
    from scripts.geometry.build_mesh import fold_pads_enabled
    assert fold_pads_enabled({}) is False
    assert fold_pads_enabled({"road_profile": None}) is False
    assert fold_pads_enabled({"road_profile": {}}) is False
    assert fold_pads_enabled({"road_profile": {"fold_pads": False}}) is False
    # false is the same as the default
    assert fold_pads_enabled({"road_profile": {"fold_pads": False}}) == fold_pads_enabled({})
    assert fold_pads_enabled({"road_profile": {"fold_pads": True}}) is True


def test_on_path_is_the_old_path():
    # with the switch on, the selection walks every apex and the disc + flat-zone code is the old code
    src = ast.unparse(_build_fn())
    assert "_apexes if _pads_on else []" in src
    assert "abs(centerline[_i1d][1] - centerline[_i0d][1]) / _run_m < 0.025" in src
    assert "_cy + 0.028" in src and "_NS = 28" in src


def test_only_the_disc_selection_is_gated():
    fn = _build_fn()
    # the disc / flat-zone selection loop runs over the apexes only when the switch is on
    disc = [n for n in _for_loops_over(fn, "_ax") if "_disc_apexes.append" in ast.unparse(n)]
    assert len(disc) == 1, "the fold-pad selection loop (appends to _disc_apexes) not found"
    assert ast.unparse(disc[0].iter) == "_apexes if _pads_on else []", ast.unparse(disc[0].iter)
    src = ast.unparse(fn)
    assert "_pads_on = fold_pads_enabled(cfg_raw)" in src
    # the +-40 m plateau still runs at every apex (Aspen keeps it: it is not what stepped)
    plateau = [n for n in _for_loops_over(fn, "_ax") if "_t * _t * (3.0 - 2.0 * _t)" in ast.unparse(n)
               and "centerline[_i] =" in ast.unparse(n)]
    assert len(plateau) == 1, "the fold plateau loop not found"
    assert ast.unparse(plateau[0].iter) == "_apexes", ast.unparse(plateau[0].iter)
    # the flat zones are built from the disc set alone, so no disc means no snap
    assert "_flat_zones = [(centerline[_ax][0], centerline[_ax][2], centerline[_ax][1], widths[_ax] / 2.0 + 16.0) " \
           "for _ax in _disc_apexes]" in src


def test_aspen_opts_out():
    cfg = json.loads((ROOT / "tracks" / "aspen" / "track.config.json").read_text(encoding="utf-8"))
    from scripts.geometry.build_mesh import fold_pads_enabled
    assert fold_pads_enabled(cfg) is False
