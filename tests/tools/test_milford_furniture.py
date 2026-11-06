"""Milford furniture pass 1 (ledger 0082): the rails kinds "wbeam" and "tyres" in tools/author_bespoke_blend.py, the tyre
skin in tools/make_bespoke_assets.py, and the rule that every new key is opt-in (no other track names them).

stdlib only: bpy and mathutils are stubbed so the module imports outside Blender.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_author():
    for name in ("bpy", "mathutils", "mathutils.bvhtree"):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules["mathutils"].Vector = object
    sys.modules["mathutils.bvhtree"].BVHTree = object
    spec = importlib.util.spec_from_file_location("author_bespoke_blend_mf", ROOT / "tools" / "author_bespoke_blend.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_resample_keeps_the_post_spacing_round_corners_and_the_end():
    m = _load_author()
    pts = m.resample_polyline([(0.0, 0.0), (10.0, 0.0), (10.0, 5.0)], m.RAIL_POST_M)
    assert pts[0] == (0.0, 0.0) and pts[-1] == (10.0, 5.0)
    arcs = []
    for a, b in zip(pts[:-2], pts[1:-1]):          # every gap but the last is one post spacing along the line
        arcs.append(abs(a[0] - b[0]) + abs(a[1] - b[1]))
    assert all(abs(d - m.RAIL_POST_M) < 1e-6 for d in arcs[:5])
    assert len(pts) == 9


def test_rail_faces_the_road_and_stands_its_height_over_the_ground():
    m = _load_author()
    line = m.resample_polyline([(0.0, 0.0), (20.0, 0.0)], m.RAIL_POST_M)
    run = [(x, y, 5.0 + 0.01 * x) for x, y in line]
    side = m.road_side(run, [(10.0, -6.0)])        # the road is south of an eastbound run: its right
    assert side == -1.0
    (rv, rf, ru), (pv, pf, pu), (kv, kf, ku) = m.wbeam_geometry(run, side, 0.70)
    assert len(rf) == len(ru) and len(pf) == len(pu) and len(kf) == len(ku)
    # the rail's top rides 0.70 m over the ground under it, at both ends
    top0 = max(v[2] for v in rv if abs(v[0]) < 1e-6)
    top1 = max(v[2] for v in rv if abs(v[0] - run[-1][0]) < 1e-6)
    assert abs(top0 - (5.0 + 0.70)) < 1e-6 and abs(top1 - (run[-1][2] + 0.70)) < 1e-6
    # the W bulges toward the road (south, -y), the posts and the collider stand behind the face (north, +y)
    assert min(v[1] for v in rv) < 0 and max(v[1] for v in rv) <= 1e-9
    assert min(v[1] for v in pv) > 0 and min(v[1] for v in kv) >= -1e-9
    # every post and the collider reach under the ground (the seat rule), never above the rail
    assert min(v[2] for v in kv) < 5.0 and max(v[2] for v in pv) <= max(v[2] for v in rv)
    assert len(pv) == 16 * len(run)                # four faces of four corners per post


def test_kinds_and_defaults():
    m = _load_author()
    assert m.RAIL_KINDS["tyres"][0].startswith("1WALL_TECPRO")   # the prefix whose UVs engine-july's prep keeps
    assert m.RAIL_KINDS["tecpro"] == ("1WALL_TECPRO", 1.2, 1.5, 0.8) and m.RAIL_KINDS["krail"] == ("1WALL_KRAILBW", 0.81, 3.0, 0.6)
    assert m.RAIL_LIP_H == 0.70 and m.RAIL_POST_M == 1.905
    assert "1WALL_GHOST_RAIL" in m.OWN_PREFIXES


def test_keys_are_opt_in():
    """no config but Milford's port names the wbeam / tyres kinds, depth_m or the tyre skin"""
    for cfgp in sorted((ROOT / "tracks").glob("*/track.config.json")):
        txt = cfgp.read_text(encoding="utf-8")
        cfg = json.loads(txt)
        rails = (((cfg.get("scenery") or {}).get("bespoke") or {}).get("rails")) or []
        kinds = {r.get("kind") for r in rails}
        if cfgp.parent.name == "milford-road-course-lm":
            assert "wbeam" in kinds
            continue
        assert not kinds & {"wbeam", "tyres"}, cfgp
        assert not any("depth_m" in r for r in rails), cfgp
        assert "tyre_wall_diffuse" not in txt, cfgp


def test_milford_rails_are_the_inventory_lines():
    cfg = json.loads((ROOT / "tracks" / "milford-road-course-lm" / "track.config.json").read_text(encoding="utf-8"))
    inv = json.loads((ROOT / "tracks" / "milford-road-course-lm" / "source" / "furniture" / "inventory.json").read_text())
    lines = {i["id"].lower(): i["polyline_lonlat"] for i in inv["items"] if "polyline_lonlat" in i}
    for r in cfg["scenery"]["bespoke"]["rails"]:
        gid = r["key"].split("_")[0]
        assert r["polyline_lonlat"] == lines[gid], r["key"]
        assert "[invented" in r["_source"]            # the heights say they are not measured

