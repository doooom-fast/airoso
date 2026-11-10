"""Milford vegetation pass (ledger 0082): the opt-in keys (scenery.bespoke.trunks in tools/author_bespoke_blend.py,
scenery.treefx.planted.native_h_m in tools/make_treefx.py), and Milford's planted files against its own rules.

stdlib only (tempfile, no pytest fixtures: tests/run_tests.py): bpy and mathutils are stubbed so the author module imports
outside Blender.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MF = ROOT / "tracks" / "milford-road-course-lm"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_author():
    for name in ("bpy", "mathutils", "mathutils.bvhtree"):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules["mathutils"].Vector = object
    sys.modules["mathutils.bvhtree"].BVHTree = object
    return _load(ROOT / "tools" / "author_bespoke_blend.py", "author_bespoke_blend_mfveg")


def test_trunk_collider_is_an_own_ghost_prefix():
    m = _load_author()
    assert "1WALL_GHOST_TRUNK" in m.OWN_PREFIXES            # re-runs empty it; the ground / wall reads never see it
    assert m.TRUNK_SIDES == 8
    assert hasattr(m, "trunks")


def test_keys_are_opt_in():
    """no config but Milford's names scenery.bespoke.trunks or scenery.treefx.planted.native_h_m"""
    for cfgp in sorted((ROOT / "tracks").glob("*/track.config.json")):
        cfg = json.loads(cfgp.read_text(encoding="utf-8"))
        sc = cfg.get("scenery") or {}
        has_trunks = "trunks" in (sc.get("bespoke") or {})
        planted = ((sc.get("treefx") or {}).get("planted")) or {}
        has_native = "native_h_m" in planted or "native_w_m" in planted
        if cfgp.parent.name == "milford-road-course-lm":
            assert has_trunks and has_native
            continue
        assert not has_trunks and not has_native, cfgp


def _project(tmp, native):
    """a minimal project: a straight 200 m road east-west, a flat heightfield, two planted points"""
    proj = Path(tmp) / "p"
    (proj / "data").mkdir(parents=True)
    (proj / "source" / "trees").mkdir(parents=True)
    for b in ("Oak3.bin", "SycamoreV2.bin"):
        (proj / "source" / "trees" / b).write_bytes(b"x")
    o = {"lon": -83.66, "lat": 42.57, "elev_m": 300.0}
    (proj / "data" / "centerline.local.json").write_text(json.dumps(
        {"origin": o, "points_xyz_m": [[-100, 0, 0], [100, 0, 0]], "widths_m": [10, 10]}))
    import struct
    hdr = "{'descr': '<f8', 'fortran_order': False, 'shape': (2, 2), }"
    hdr = hdr + " " * (118 - len(hdr)) + "\n"
    (proj / "data" / "heightfield.npy").write_bytes(b"\x93NUMPY\x01\x00" + struct.pack("<H", len(hdr)) + hdr.encode()
                                                    + struct.pack("<4d", 300, 300, 300, 300))
    (proj / "data" / "heightfield.meta.json").write_text(json.dumps({"bbox_swne": [42.56, -83.67, 42.58, -83.65]}))
    # two trees 50 m north of the road: 10 m and 30 m tall
    pts = [[-83.66, 42.57 + 50 / 111000, 1, 10.0, 6.0], [-83.6598, 42.57 + 60 / 111000, 1, 30.0, 12.0]]
    (proj / "source" / "t.json").write_text(json.dumps({"cols": 1, "rows": 1, "points": pts}))
    planted = {"file": "source/t.json", "clear_m": 3.0, "zones": {"1": "planted_neighbourhood"}}
    if native:
        planted["native_h_m"] = native
    (proj / "track.config.json").write_text(json.dumps({"slug": "t", "scenery": {"treefx": {"planted": planted}}}))
    return proj


def test_native_height_sizes_a_tree_by_its_measured_height():
    mt = _load(ROOT / "tools" / "make_treefx.py", "make_treefx_mfveg")
    with tempfile.TemporaryDirectory() as tmp:
        p = mt.plan(_project(tmp, {"Oak3.bin": 15.0, "SycamoreV2.bin": 20.0}))
    sizes = {}
    for ln in p["lines"]:
        if ln.startswith("tree:"):
            model = ln.split(";")[0].split()[1]
            sizes.setdefault(model, []).append(float(ln.split("size =")[1]))
    got = sorted((m, s) for m, ss in sizes.items() for s in ss)
    want = {"Oak3.bin": 15.0, "SycamoreV2.bin": 20.0}
    # every size is a measured height (10 or 30 m) over its model's height
    for m, s in got:
        assert any(abs(s - h / want[m]) < 0.006 for h in (10.0, 30.0)), (m, s)


def test_native_width_keeps_the_measured_crown():
    """planted.native_w_m: width = crown / (native width x size), so the drawn crown is the measured one at any height"""
    mt = _load(ROOT / "tools" / "make_treefx.py", "make_treefx_mfveg3")
    with tempfile.TemporaryDirectory() as tmp:
        proj = _project(tmp, {"Oak3.bin": 8.673, "SycamoreV2.bin": 8.194})
        cfgp = proj / "track.config.json"
        cfg = json.loads(cfgp.read_text())
        cfg["scenery"]["treefx"]["planted"]["native_w_m"] = {"Oak3.bin": 6.089, "SycamoreV2.bin": 6.620}
        cfgp.write_text(json.dumps(cfg))
        p = mt.plan(proj)
    nw = {"Oak3.bin": 6.089, "SycamoreV2.bin": 6.620}
    drawn = sorted(round(nw[ln.split(";")[0].split()[1]] * float(ln.split("size =")[1].split(";")[0])
                         * float(ln.split("width =")[1]), 1) for ln in p["lines"] if ln.startswith("tree:"))
    assert len(drawn) == 2 and abs(drawn[0] - 6.0) < 0.1 and abs(drawn[1] - 12.0) < 0.1, drawn


def test_without_native_width_no_width_is_written():
    mt = _load(ROOT / "tools" / "make_treefx.py", "make_treefx_mfveg4")
    with tempfile.TemporaryDirectory() as tmp:
        p = mt.plan(_project(tmp, {"Oak3.bin": 15.0, "SycamoreV2.bin": 20.0}))
    assert not any("width =" in ln for ln in p["lines"])


def test_without_native_height_the_rank_rule_stands():
    """no native_h_m (Sand Creek, every other planted track): the shortest takes the bottom of its range, the tallest the top"""
    mt = _load(ROOT / "tools" / "make_treefx.py", "make_treefx_mfveg2")
    with tempfile.TemporaryDirectory() as tmp:
        p = mt.plan(_project(tmp, None))
    sizes = sorted(float(ln.split("size =")[1]) for ln in p["lines"] if ln.startswith("tree:"))
    rng = {s[0]: (s[1], s[2]) for s in mt.ZONES["planted_neighbourhood"]}
    assert len(sizes) == 2
    assert any(abs(sizes[0] - lo) < 0.006 for lo, _ in rng.values())
    assert any(abs(sizes[1] - hi) < 0.006 for _, hi in rng.values())


def test_milford_planted_files_keep_their_rules():
    cfg = json.loads((MF / "track.config.json").read_text(encoding="utf-8"))
    assert "(LM engine)" not in cfg["name"] and cfg["install_folder"] == cfg["slug"] == "milford_road_course"
    old = json.loads((MF.parent / "milford-road-course" / "track.config.json").read_text(encoding="utf-8"))
    assert old["slug"] != cfg["slug"] and old["install_folder"] != cfg["install_folder"]   # S7: one AC folder each
    assert "cards" not in cfg["scenery"]["bespoke"]
    trees = json.loads((MF / "source" / "vegetation" / "trees.lm.json").read_text(encoding="utf-8"))["points"]
    trunks = json.loads((MF / "source" / "vegetation" / "trunks.json").read_text(encoding="utf-8"))["points"]
    assert len(trees) > 1000 and all(p[2] == 1 and p[3] >= 5.0 for p in trees)   # trees only, measured >= 5 m
    assert all(p[3] < 45.0 for p in trees)
    keys = {(p[0], p[1]) for p in trees}
    assert all((t[0], t[1]) in keys for t in trunks)               # a collider only where a tree is planted
    assert all(t[3] <= 30.0 for t in trunks)
    inv = json.loads((MF / "source" / "vegetation" / "inventory.json").read_text(encoding="utf-8"))
    assert inv["planted"]["trees"] == len(trees) and inv["planted"]["trunk_colliders"] == len(trunks)
    ship = json.loads((MF / "ship.json").read_text(encoding="utf-8"))
    st = ship["steps"]["ship"]
    assert st.index("grassfx_aerial") < st.index("track_folder") < st.index("treefx")


def test_point_key_keeps_model_and_angle_when_an_earlier_point_goes():
    """Milford 0.1.5: a planted point's 6th element is its hash key, so removing a point before it changes nothing after it;
    without a key a point hashes by its place (every other track: unchanged)"""
    mt = _load(ROOT / "tools" / "make_treefx.py", "make_treefx_mfveg5")
    trees = lambda ls: [ln for ln in ls if ln.startswith("tree:")]
    with tempfile.TemporaryDirectory() as tmp:
        proj = _project(tmp, {"Oak3.bin": 8.673, "SycamoreV2.bin": 8.194})
        t = proj / "source" / "t.json"
        d = json.loads(t.read_text())
        base = trees(mt.plan(proj)["lines"])
        d["points"] = [p + [k] for k, p in enumerate(d["points"])]
        t.write_text(json.dumps(d))
        keyed = trees(mt.plan(proj)["lines"])
        d["points"] = d["points"][1:]
        t.write_text(json.dumps(d))
        after = trees(mt.plan(proj)["lines"])
    assert keyed == base and len(base) == 2                      # key == place: the same file
    assert after == keyed[1:]                                    # the second tree keeps its model and angle


def test_crown_fix_lists_every_case():
    fix = json.loads((MF / "source" / "vegetation" / "crown_fix.json").read_text(encoding="utf-8"))
    s = fix["summary"]
    assert len(fix["cases"]) == s["before"]["width_under_0.25"] + s["before"]["width_over_2"]
    assert s["after"]["width_under_0.25"] == 0 and s["after"]["width_over_2"] == 0
    trees = json.loads((MF / "source" / "vegetation" / "trees.lm.json").read_text(encoding="utf-8"))["points"]
    keys = [p[5] for p in trees]
    assert len(set(keys)) == len(keys) == s["after"]["planted"]
    assert not set(fix["removed_keys"]) & set(keys)
