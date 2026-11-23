"""Ledger 0098 (Sand Creek 0.2.9, Kevin 2026-11-22: "let's complete lake murray, sand creek, and high plains"): the grid's
map-edge cut reached (tools/grid_reach.py, lm_intake.grid_reach), the one-sided measured flares (tools/flare_one_sided.py,
lm_intake.flare_one_sided), both heads of the two-arm lamps lit (scenery.streetlights.light_both_heads,
tools/check_lights_ini.py), the owned asphalt and concrete. Every key opt-in; Sand Creek alone names them."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SC = ROOT / "tracks" / "sand-creek-lm"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import grid_reach as gr  # noqa: E402
import lm_engine_intake as li  # noqa: E402
import check_lights_ini as cli  # noqa: E402

# ledger 0098: the final piece names trim gives once E 56th is built (the dry trim's map; mouth radii and rows renamed)
RENAMED = {"grid_primary_6": "grid_primary_6#0", "grid_primary_71": "grid_primary_71#0",
           "grid_primary_73": "grid_primary_73#0", "grid_unclassified_57": "grid_unclassified_57#0",
           "grid_unclassified_82": "grid_unclassified_82#0", "grid_residential_22": "grid_residential_22#0",
           "grid_residential_12#0": "grid_residential_12#0#0", "grid_residential_19#0": "grid_residential_19#0#0",
           "grid_residential_21#0": "grid_residential_21#0#0", "grid_residential_24#0": "grid_residential_24#0#0",
           "grid_residential_26#0": "grid_residential_26#0#0", "grid_residential_29#0": "grid_residential_29#0#0",
           "grid_residential_29#1": "grid_residential_29#0#1", "grid_residential_29#2": "grid_residential_29#0#2",
           "grid_residential_47#0": "grid_residential_47#0#0", "grid_residential_47#1": "grid_residential_47#0#1"}


def _cfg(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ grid_reach
def test_the_walk_follows_osm_through_a_node_and_takes_the_via_branch():
    ways = [("primary", [(0.0, 0.0), (50.0, 0.0), (100.0, 0.0)]),
            ("primary", [(100.0, 0.0), (200.0, 10.0)]),          # the straighter-looking branch (5.7 deg left)
            ("primary", [(100.0, 0.0), (200.0, -12.0)])]         # the via's branch (6.8 deg right)
    pts, notes = gr.walk(ways, (0.0, 0.0), (1.0, 0.0))
    assert pts[-1] == (200.0, 10.0)                              # no via: the straightest
    pts, notes = gr.walk(ways, (0.0, 0.0), (1.0, 0.0), via=[(200.0, -12.0)])
    assert pts[-1] == (200.0, -12.0) and any("via" in n for n in notes)
    cut, how = gr.cut_at_stop(pts, {"x_max": 150.0}, {}, 6.0)
    assert abs(cut[-1][0] - 150.0) < 1e-9 and how == "x_max 150.0"
    with pytest.raises(ValueError):
        gr.cut_at_stop(pts, {"q": 1}, {}, 6.0)
    none, why = gr.cut_at_stop(pts, {"x_max": 999.0}, {}, 6.0)
    assert none is None and "never" in why


def test_the_on_stop_keeps_the_first_point_on_the_road():
    pts = [(0.0, 0.0), (0.0, 40.0)]
    host = ([[-50.0, 0.0, 30.0], [50.0, 0.0, 30.0]], [8.0, 8.0])     # a road along z 30, half width 4
    cut, how = gr.cut_at_stop(pts, {"on": "H"}, {"H": host}, 6.0)
    assert abs(cut[-1][1] - 20.0) < 0.51 and "on H" in how          # 30 - (4 + 6), read every 0.5 m


def test_the_frames_differ_as_measured():
    o = _cfg(ROOT / "tracks" / "sand-creek" / "data" / "centerline.local.json")["origin"]
    kx, kz = gr.frame_scale(o)
    # ledger 0098: the grid (sphere) and the lap / lidar (ellipsoid) frames: 0.25 % east, -0.15 % north at Sand Creek
    assert abs(kx - 1.0024949) < 1e-6 and abs(kz - 0.9985216) < 1e-6
    assert 1877.5 * (kx - 1) > 4.6 and 1315 * (1 - kz) > 1.9


def _proj(tmp, conns, recs):
    (tmp / "data").mkdir(parents=True)
    (tmp / "data" / "connectors.local.json").write_text(json.dumps({"connectors": conns}), encoding="utf-8")
    (tmp / "source").mkdir()
    (tmp / "source" / "r.json").write_text(json.dumps({"reach": recs}), encoding="utf-8")


def test_apply_grid_reach_adds_at_the_named_end_and_eases_a_moved_joint(tmp_path):
    p = [[0.0, 1.0, 0.0], [3.0, 1.0, 0.0], [6.0, 1.5, 0.0]]
    new = [[9.0, 1.5, 0.0], [12.0, 1.5, 0.0]]
    _proj(tmp_path, [{"name": "a", "points_xyz_m": [list(q) for q in p], "widths_m": [8.0] * 3}],
          [{"piece": "a", "end": "end", "from_xz": [6.0, 0.0], "from_y": 1.5, "points_xyz_m": new, "widths_m": [8.0, 8.0]},
           {"piece": "a", "end": "start", "from_xz": [0.0, 0.0], "from_y": 0.5, "ease_m": 30.0,
            "points_xyz_m": [[-3.0, 0.5, 0.0]], "widths_m": [8.0]}])
    li.apply_grid_reach(tmp_path, "source/r.json")
    c = _cfg(tmp_path / "data" / "connectors.local.json")["connectors"][0]
    xs = [q[0] for q in c["points_xyz_m"]]
    assert xs == [-3.0, 0.0, 3.0, 6.0, 9.0, 12.0] and len(c["widths_m"]) == 6
    # the start's record was eased onto 0.5 m; the piece's end stands at 1.0 m now: the joint follows (+0.5 faded)
    u = 1.0 - 3.0 / 30.0
    assert abs(c["points_xyz_m"][0][1] - round(0.5 + 0.5 * u * u * (3 - 2 * u), 3)) < 1e-9
    assert c["points_xyz_m"][-1][1] == 1.5                     # from_y as the end stands: untouched
    _proj(tmp_path / "b", [{"name": "a", "points_xyz_m": p, "widths_m": [8.0] * 3}],
          [{"piece": "a", "end": "end", "from_xz": [6.5, 0.0], "points_xyz_m": new, "widths_m": [8.0, 8.0]}])
    with pytest.raises(SystemExit):
        li.apply_grid_reach(tmp_path / "b", "source/r.json")


def test_sand_creek_reach_record_is_the_configs():
    cfg = _cfg(SC / "track.config.json")
    spec = cfg["route"]["grid"]["reach"]
    rec = _cfg(SC / cfg["lm_intake"]["grid_reach"])
    assert [(r["piece"], r["end"]) for r in rec["reach"]] == [(s["piece"], s["end"]) for s in spec] == [
        ("grid_primary_80", "start"), ("grid_primary_71", "start"), ("grid_primary_73", "end")]
    src = {c["name"]: c for c in _cfg(ROOT / "tracks" / "sand-creek" / "data" / "connectors.local.json")["connectors"]}
    for r in rec["reach"]:
        e = src[r["piece"]]["points_xyz_m"][0 if r["end"] == "start" else -1]
        assert abs(e[0] - r["from_xz"][0]) < 0.01 and abs(e[2] - r["from_xz"][1]) < 0.01
        assert len(r["points_xyz_m"]) == len(r["widths_m"]) == len(r["height_source"])
        assert r["max_neighbour_jump_m"] < 0.5                    # round I's own rule for a street's profile
    e56 = rec["reach"][0]
    assert abs(e56["points_xyz_m"][-1][0] - 1877.5) < 1e-6 and 2500 < e56["length_m"] < 2550
    assert 0.4 < e56["lidar_share"] < 0.5                         # 377 of 843 points read off the lidar
    assert rec["frame"]["kx"] == 1.0024949


def test_sand_creek_trim_meets_e56th_and_the_lap(tmp_path):
    """lm_intake + trim_connectors on the committed inputs (the 0.2.8 build's smoothed lap): the 13 streets and Quebec's two
    carriageways mouth on E 56th, Northfield Quebec meets the lap, and every allowed / skipped row names a real piece"""
    proj = tmp_path / "p"
    (proj / "data").mkdir(parents=True)
    for f in ("track.config.json", "signs.json"):
        shutil.copy(SC / f, proj / f)
    for d in ("source", "textures"):
        shutil.copytree(SC / d, proj / d)
    for f in ("heightfield.npy", "heightfield.meta.json"):
        shutil.copy(SC / "data" / f, proj / "data" / f)
    py = sys.executable
    r = subprocess.run([py, str(ROOT / "tools" / "lm_engine_intake.py"), str(proj)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    shutil.copy(SC / "data" / "centerline.local.json", proj / "data" / "centerline.local.json")
    r = subprocess.run([py, str(ROOT / "tools" / "trim_connectors.py"), str(proj)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    mouths = _cfg(proj / "data" / "mouths.json")["mouths"]
    names = {c["name"] for c in _cfg(proj / "data" / "connectors.local.json")["connectors"]}
    on80 = sorted(m["piece"] for m in mouths if m["host"] == "grid_primary_80#0")
    # 11 street ends (Monaco and Krameria are grid_residential_22's two) and Quebec's two carriageways
    assert len(on80) == 13 and len(set(on80)) == 12 and "grid_primary_6#0" in on80 and "grid_primary_7#0" in on80
    assert any(m["piece"] == "grid_primary_71#0" and m["host"] == "MAINLINE" for m in mouths)
    assert any(m["piece"] == "grid_primary_73#0" and m["host"] == "grid_primary_71#0" for m in mouths)
    # 128 on the Mac's round 1 alone; the PC's pads (claude/sc-finish-pc-20261122, merged into 0.2.9) take three of them as pad
    # arms: grid_primary_35#0 at Dahlia/56th, grid_primary_78#0 and grid_primary_84#0#0 at Quebec
    assert len(mouths) == 125
    assert not any(m["host"] == "MAINLINE" and m["piece"] in ("grid_primary_35#0", "grid_primary_78#0", "grid_primary_84#0#0") for m in mouths)
    cfg = _cfg(SC / "track.config.json")
    for key in ("verify_mouth_corners_allowed", "verify_mouths_allowed", "mouth_returns_skip"):
        for row in cfg["route"][key]:
            assert row["piece"] in names, (key, row["piece"])
    assert set(RENAMED.values()) <= names and not (set(RENAMED) & names)


def test_the_mouth_radii_follow_the_renamed_pieces():
    rad = _cfg(SC / "source" / "mouth_radii.naip.json")
    pieces = {k.split("|")[0] for k in rad["corners"]}
    assert not (pieces & set(RENAMED)) and len(rad["corners"]) == 216
    assert {"grid_residential_29#0#1", "grid_residential_47#0#1", "grid_residential_12#0#0"} <= pieces
    assert not ({v.get("host") for v in rad["corners"].values()} & set(RENAMED))


# ------------------------------------------------------------------ one-sided flares
def _line(tmp, rows, side=-1):
    (tmp / "source").mkdir(parents=True, exist_ok=True)
    (tmp / "source" / "f.json").write_text(json.dumps({"flares": [{"id": "x", "street_side": side, "rows": rows}]}),
                                           encoding="utf-8")


def test_a_one_sided_flare_keeps_the_near_edge_and_moves_the_far(tmp_path):
    pts = [[float(x), 0.0, 0.0] for x in range(0, 30, 3)]
    widths = [10.0] * len(pts)
    _line(tmp_path, [{"k": 4, "line_xz": [12.0, 0.0], "source_half_m": 5.0, "move_m": 0.5, "width_m": 9.0}])
    p2, w2, rep = li.apply_flare_one_sided(tmp_path, "source/f.json", pts, widths)
    # travel +x: left = +z; the street on the right (-1): the line moves 0.5 m to -z, the right edge stays at -5.0
    assert p2[4][2] == -0.5 and w2[4] == 9.0
    assert abs((p2[4][2] - w2[4] / 2) - (-5.0)) < 1e-9 and abs((p2[4][2] + w2[4] / 2) - 4.0) < 1e-9
    assert p2[3] == pts[3] and rep[0]["rows_moved"] == 1
    _line(tmp_path, [{"k": 4, "line_xz": [12.5, 0.0], "source_half_m": 5.0, "move_m": 0.5, "width_m": 9.0}])
    with pytest.raises(SystemExit):
        li.apply_flare_one_sided(tmp_path, "source/f.json", pts, widths)


def test_sand_creek_flares_as_measured():
    cfg = _cfg(SC / "track.config.json")
    rec = _cfg(SC / cfg["lm_intake"]["flare_one_sided"])
    by = {f["id"]: f for f in rec["flares"]}
    assert set(by) == {r["id"] for r in cfg["route"]["flare_one_sided"]}
    # Sand Creek Dr S: the far side is a graded platform as wide as the flare (the drop at 10.6-11.6 m): nothing moves
    assert all(r["move_m"] == 0.0 for r in by["sand_creek_dr_s_tertiary_5"]["rows"])
    f = by["e45th_n_dr_unclassified_81"]
    moved = [r for r in f["rows"] if r["move_m"] > 0]
    assert len(moved) == 11 and max(r["move_m"] for r in moved) == 0.565 and f["street_side"] == -1
    for r in f["rows"]:
        assert r["base_half_m"] - 1e-9 <= r["far_half_m"] <= r["source_half_m"] + 1e-9   # never past the flare / own width
        assert abs(r["width_m"] - (r["source_half_m"] + r["far_half_m"])) < 1e-6
        assert abs(r["move_m"] - (r["source_half_m"] - r["far_half_m"]) / 2) < 1e-3
    src = _cfg(ROOT / "tracks" / "sand-creek" / "data" / "centerline.local.json")
    for r in f["rows"]:
        q = src["points_xyz_m"][r["k"]]
        assert abs(q[0] - r["line_xz"][0]) < 0.01 and abs(q[2] - r["line_xz"][1]) < 0.01


# ------------------------------------------------------------------ lamps
def test_two_lit_heads_are_one_light_per_lens():
    heads = [[0.0, 9.0, 0.0], [40.0, 9.0, 0.0]]
    lenses = [[4.0, 11.8, 0.0], [-4.0, 11.8, 0.0], [44.0, 11.8, 0.0], [36.0, 11.8, 0.0]]
    blocks = [{"n": i, "keys": {}, "pos": (l[0], round(l[1] - 0.15, 2), -l[2])} for i, l in enumerate(lenses)]
    ok = cli.check({"lampheads": heads, "provenance": {"lens_xyz": lenses, "heads_lit": 2}}, blocks)
    assert ok["ok"] and ok["matched"] == 4 and ok["heads_lit"] == 2
    bad = cli.check({"lampheads": heads, "provenance": {"lens_xyz": lenses, "heads_lit": 2}}, blocks[:2])
    assert not bad["ok"]
    one = cli.check({"lampheads": heads, "provenance": {"lens_xyz": lenses[::2]}}, blocks[::2])
    assert "heads_lit" not in one                               # absent = one per lamp, as before


def test_both_heads_author_records_the_back_lens():
    s = (ROOT / "tools" / "author_lamps_blend.py").read_text(encoding="utf-8")
    assert "def both_heads(" in s and '"heads_lit": 2' in s and "place((-v[0], v[1], v[2]))" in s
    spec = _cfg(ROOT / "assets" / "models" / "streetlight_led.json")
    assert spec["lens_centre_m"][0] == 4.0376                   # the mirrored lens: the twin post's other arm, at -x
    tw = [tuple(map(float, l.split()[1:4])) for l in open(ROOT / "assets" / "models" / "streetlight_led_post_twin.obj")
          if l.startswith("v ")]
    hi = [v for v in tw if v[1] > 11.0]
    assert abs(min(v[0] for v in hi) + max(v[0] for v in hi)) < 1e-6   # symmetric heads


# both heads, two paths (2026-11-23, the 0.2.9 merge with main): the same key light_both_heads was written twice in two
# rounds; scenery.streetlights.both_heads_by "lamps" (Sand Creek) keeps ledger 0098's path, absent keeps ledger 0099's
def _author_lamps():
    import importlib.util
    import types
    sys.modules.setdefault("bpy", types.ModuleType("bpy"))
    spec = importlib.util.spec_from_file_location("author_lamps_0098", ROOT / "tools" / "author_lamps_blend.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _lamp_proj(tmp_path, cfg, lights=None):
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    if lights is not None:
        (tmp_path / "data" / "lights.local.json").write_text(json.dumps(lights), encoding="utf-8")
    return tmp_path


def test_the_lamps_step_lights_the_back_head_only_by_both_heads_by(tmp_path):
    al = _author_lamps()
    sc, lm = _cfg(SC / "track.config.json"), _cfg(ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json")
    assert sc["scenery"]["streetlights"]["both_heads_by"] == "lamps"
    assert al.both_heads(_lamp_proj(tmp_path / "sc", sc), al.LED, 2) is True
    # Lake Murray's config as main has it (light_both_heads, no both_heads_by): its draft lamps step lights ONE head, so
    # lamps + lamp_heads give 0.20.4's two lights a lamp, not three
    assert lm["scenery"]["streetlights"]["light_both_heads"] is True and "both_heads_by" not in lm["scenery"]["streetlights"]
    assert al.both_heads(_lamp_proj(tmp_path / "lm", lm), al.LED, 2) is False
    bad = json.loads(json.dumps(sc))
    bad["scenery"]["streetlights"]["both_heads_by"] = "lamp_heads"
    with pytest.raises(SystemExit, match="lamps"):
        al.both_heads(_lamp_proj(tmp_path / "bad", bad), al.LED, 2)
    lone = json.loads(json.dumps(sc))
    del lone["scenery"]["streetlights"]["light_both_heads"]
    with pytest.raises(SystemExit, match="needs light_both_heads"):
        al.both_heads(_lamp_proj(tmp_path / "lone", lone), al.LED, 2)


def _ini(lenses):
    return "".join(f"[LIGHT_{i}]\nPOSITION = {l[0]:.2f}, {l[1] - 0.15:.2f}, {-l[2]:.2f}\n\n" for i, l in enumerate(lenses))


def test_the_check_reads_heads_lit_by_the_lamps_and_the_heads_file_otherwise(tmp_path):
    heads = [[0.0, 9.0, 0.0], [40.0, 9.0, 0.0]]
    fronts, backs = [[4.0, 11.8, 0.0], [44.0, 11.8, 0.0]], [[-4.0, 11.8, 0.0], [36.0, 11.8, 0.0]]
    both = [fronts[0], backs[0], fronts[1], backs[1]]
    sc = _cfg(SC / "track.config.json")
    sc["slug"] = "t"
    del sc["lighting"]                                         # the look is not what this test judges
    # ledger 0098's path: heads_lit 2, both lenses in lens_xyz, no heads file wanted
    p = _lamp_proj(tmp_path / "a", sc, {"lampheads": heads, "provenance": {"lens_xyz": both, "heads_lit": 2}})
    (p / "ext_config.ini").write_text(_ini(both), encoding="utf-8")
    assert cli.both_heads_path(sc) == "lamps"
    assert cli.main([str(p), "--ini", str(p / "ext_config.ini")]) == 0
    # the same path with the author's record saying one head: refused
    (p / "data" / "lights.local.json").write_text(json.dumps({"lampheads": heads, "provenance": {"lens_xyz": fronts}}),
                                                 encoding="utf-8")
    (p / "ext_config.ini").write_text(_ini(fronts), encoding="utf-8")
    assert cli.main([str(p), "--ini", str(p / "ext_config.ini")]) == 1
    # ledger 0099's path (light_both_heads alone): the heads file is wanted, and with it the back lenses count
    lm = json.loads(json.dumps(sc))
    del lm["scenery"]["streetlights"]["both_heads_by"]
    assert cli.both_heads_path(lm) == "lamp_heads"
    q = _lamp_proj(tmp_path / "b", lm, {"lampheads": heads, "provenance": {"lens_xyz": fronts}})
    (q / "ext_config.ini").write_text(_ini(fronts + backs), encoding="utf-8")
    assert cli.main([str(q), "--ini", str(q / "ext_config.ini")]) == 1           # no data/lights.heads.json
    (q / "data" / "lights.heads.json").write_text(json.dumps({"back_lens_xyz": backs}), encoding="utf-8")
    assert cli.main([str(q), "--ini", str(q / "ext_config.ini")]) == 0
    # both records at once (heads_lit 2 AND a heads file) is the back head lit twice: refused by the check itself
    r = cli.check({"lampheads": heads, "provenance": {"lens_xyz": both, "heads_lit": 2}}, cli.parse_lights(_ini(both + backs)),
                  None, backs)
    assert not r["ok"] and any("lit twice" in s for s in r["problems"])
    # neither: one head a lamp, as before both
    none = json.loads(json.dumps(lm))
    del none["scenery"]["streetlights"]["light_both_heads"]
    assert cli.both_heads_path(none) is None


def test_lamp_heads_refuses_the_lamps_path(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("author_lamp_heads_0098", ROOT / "tools" / "author_lamp_heads_blend.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    p = _lamp_proj(tmp_path, _cfg(SC / "track.config.json"))
    with pytest.raises(SystemExit, match="twice"):
        m.main([str(p)])
    ship = _cfg(SC / "ship.json")
    assert "lamp_heads" not in [n for ph in ship["steps"].values() if isinstance(ph, list) for n in ph]


# ------------------------------------------------------------------ owned surfaces, opt-in
def test_sand_creek_binds_the_owned_pairs_and_syncs_them():
    cfg, ship = _cfg(SC / "track.config.json"), _cfg(SC / "ship.json")
    to = cfg["texture_overrides"]
    pairs = [(to["1ROAD"]["diffuse"], to["1ROAD"]["normal"]), (to["1KERB_SIDEWALK"]["diffuse"], to["1KERB_SIDEWALK"]["normal"])]
    assert pairs == [("assets/textures/asphalt_dense_diffuse.jpg", "assets/textures/asphalt_dense_normal.jpg"),
                     ("assets/textures/concrete_plain_diffuse.jpg", "assets/textures/concrete_plain_normal.jpg")]
    lic = json.dumps(_cfg(ROOT / "assets" / "licenses.json"))
    for a, b in pairs:
        assert (ROOT / a).is_file() and (ROOT / b).is_file()
        assert a in ship["sync_in"]["assets"] and b in ship["sync_in"]["assets"]
        assert Path(a).name in lic and Path(b).name in lic
    for f in (cfg["lm_intake"]["grid_reach"], cfg["lm_intake"]["flare_one_sided"]):
        assert f in ship["sync_in"]["optional"] and (SC / f).is_file()
    assert cfg["scenery"]["streetlights"]["light_both_heads"] is True and cfg["version"] == "0.2.9"


def test_the_0098_keys_are_opt_in():
    for cfgp in sorted((ROOT / "tracks").glob("*/track.config.json")):
        if cfgp.parent.name == "sand-creek-lm":
            continue
        cfg = _cfg(cfgp)
        t = cfgp.parent.name
        assert "grid_reach" not in (cfg.get("lm_intake") or {}), t
        assert "flare_one_sided" not in (cfg.get("lm_intake") or {}), t
        assert "reach" not in ((cfg.get("route") or {}).get("grid") or {}), t
        assert "flare_one_sided" not in (cfg.get("route") or {}), t
        sl = (cfg.get("scenery") or {}).get("streetlights") or {}
        if t != "san-diego-lake-murray":                          # ledger 0099: Lake Murray's own both heads (lamp_heads)
            assert "light_both_heads" not in sl, t
        assert "both_heads_by" not in sl, t                       # ledger 0098's path is Sand Creek's alone
        assert "split_strip_balanced" not in (cfg.get("route") or {}), t


def test_the_strip_split_is_balanced_only_where_asked():
    s = (ROOT / "tools" / "split_strip_blend.py").read_text(encoding="utf-8")
    assert '(cfg.get("route") or {}).get("split_strip_balanced") is True' in s and "def balanced_groups(" in s
    # the median-bisection rule, run here on a grid of quads: every group under the cap, every face once
    src = s[s.index("def balanced_groups("):s.index("def balanced(ob, n):")]
    ns = {}
    exec(src, ns)
    faces, centres, vid = [], [], {}
    for i in range(60):
        for j in range(20):
            q = [vid.setdefault((i + a, j + b), len(vid)) for a, b in ((0, 0), (1, 0), (1, 1), (0, 1))]
            faces.append(tuple(q)); centres.append((i + 0.5, j + 0.5))
    groups = ns["balanced_groups"](centres, faces, 400)
    assert sorted(f for g in groups for f in g) == list(range(len(faces)))
    assert all(len({v for f in g for v in faces[f]}) <= 400 for g in groups) and len(groups) >= 4
    cfg, ship = _cfg(SC / "track.config.json"), _cfg(SC / "ship.json")
    assert cfg["route"]["split_strip_balanced"] is True and ship["steps"]["draft"][-1] == "split_strip"
