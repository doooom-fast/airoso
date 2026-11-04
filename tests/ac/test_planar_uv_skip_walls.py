"""Ledger 0071 (0070 C2): the prep's top-down planar_uv (u = x / 4 m, v = y / 4 m) leaves the engine draft's
textured vertical walls alone. On a vertical face that projection is one texel column top to bottom, and the concrete
of Sand Creek's 1WALL_barrier smeared into vertical streaks.

Read off the source of scripts/ac/build_kn5_loop.py (airoso's prep, which every track but Lake Murray runs), the way
test_build_kn5_loop.test_planar_uv_skips_the_race_furniture reads it. Plain ``test_*``, stdlib only.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / "scripts" / "ac" / "build_kn5_loop.py"


def _skip_tuple() -> tuple[str, ...]:
    s = PREP.read_text(encoding="utf-8")
    m = re.search(r"if not ob\.name\.upper\(\)\.startswith\(\((.*?)\)\):\s*\n\s*planar_uv\(me\)", s, re.S)
    assert m, "the planar_uv call site with its skip tuple"
    return ast.literal_eval("(" + m.group(1) + ")")


def test_planar_uv_skips_the_barrier_the_stone_lips_the_fences_and_the_swept_jersey():
    skip = _skip_tuple()
    for key in ("1WALL_BARRIER", "1WALL_PARA", "1WALL_CHAINL", "BARRIER_WARNING"):
        assert key in skip, key
    # the names build_mesh writes (and the underlay keeps), as the prep sees them, split pieces included
    for name in ("1WALL_barrier", "1WALL_barrier_1", "1WALL_PARA_stone", "1WALL_CHAINL_warn", "BARRIER_warning"):
        assert name.upper().startswith(skip), name
    # still projected: the ground, the pavement, the kerbs and the paint, which tile at world scale from above
    for name in ("1ROAD_main", "1GRASS_3", "1KERB_sidewalk", "1KERB_corners", "MARKINGS"):
        assert not name.upper().startswith(skip), name
