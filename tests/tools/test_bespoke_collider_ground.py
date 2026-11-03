"""The bespoke collider's fine-ground rule (tools/author_bespoke_blend.py collider_ground_ok) and High Plains' override.

High Plains 0.71.0: post9 and post12 stood over 1GRASS_ring seating-fan slivers 12.2-12.3 m long, over the 8 m
COLLIDER_TRI_M, so the block was built without its 1WALL_TILTUP collider (ledger 0072). stdlib only: bpy and mathutils are
stubbed so the module imports outside Blender.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_author():
    for name in ("bpy", "mathutils", "mathutils.bvhtree"):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules["mathutils"].Vector = object
    sys.modules["mathutils.bvhtree"].BVHTree = object
    spec = importlib.util.spec_from_file_location("author_bespoke_blend_under_test", ROOT / "tools" / "author_bespoke_blend.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_default_limit_unchanged_and_applied():
    m = _load_author()
    assert m.COLLIDER_TRI_M == 8.0
    assert m.collider_ground_ok([2.1, 6.8, 8.0], m.COLLIDER_TRI_M)
    assert not m.collider_ground_ok([2.1, 12.3], m.COLLIDER_TRI_M)       # post9's sliver: refused at the default
    assert not m.collider_ground_ok([2.1, None], m.COLLIDER_TRI_M)       # no ground under a sample: always refused
    assert not m.collider_ground_ok([2.1, None], 1e9)


def test_group_override_admits_the_high_plains_slivers():
    m = _load_author()
    cfg = json.loads((ROOT / "tracks" / "high-plains" / "track.config.json").read_text(encoding="utf-8"))
    groups = cfg["scenery"]["bespoke"]["blocks"]
    posts = [g for g in groups if g["file"].endswith("posts.json")][0]
    limit = float(posts.get("collider_tri_m", m.COLLIDER_TRI_M))
    assert m.collider_ground_ok([12.3, 12.2, 6.8], limit)               # post9 and post12's longest edges
    assert not m.collider_ground_ok([500.3], limit)                       # a far skirt triangle is still refused
    other = [g for g in groups if g is not posts]
    assert all("collider_tri_m" not in g for g in other)                  # only the posts group opts in
