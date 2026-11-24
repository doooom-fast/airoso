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
    # 2026-11-23 (source/grid_reach_e56.md): re-run with the 14 tiles of row z 1300-1400 that round 1 lacked; all 843
    # points now read off the lidar (round 1: 377 of 843, lidar_share 0.447, the other 466 on 3DEP + offset)
    assert e56["lidar_share"] == 1.0 and set(e56["height_source"]) == {"lidar"}
    assert rec["tiles_missing"] == []
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
def test_sand_creek_lights_both_heads_by_lamp_heads():
    """round 2 (0.2.10, the Mac 2026-11-23): the two both-heads paths are one. Sand Creek runs Lake Murray's author step
    lamp_heads (ledger 0099); 0.2.9's discriminator scenery.streetlights.both_heads_by and the lamps step's own back
    lens (heads_lit) are gone, so author_lamps_blend / check_lights_ini / author_lamp_heads_blend are main's again"""
    sl = _cfg(SC / "track.config.json")["scenery"]["streetlights"]
    assert sl["light_both_heads"] is True and "both_heads_by" not in sl
    assert sl["model"] == "led_cobra" and int(sl.get("arms", 2)) == 2          # lamp_heads' twin-arm rule
    ship = _cfg(SC / "ship.json")
    assert ship["steps"]["author"][0] == "lamp_heads"                          # before anything reads the lamps
    assert "data/lights.heads.json" in ship["sync_out"]["files"]
    al = (ROOT / "tools" / "author_lamps_blend.py").read_text(encoding="utf-8")
    assert "heads_lit" not in al and "both_heads" not in al
    assert not hasattr(cli, "both_heads_path")
    assert "both_heads_by" not in (ROOT / "tools" / "author_lamp_heads_blend.py").read_text(encoding="utf-8")


def test_the_twin_post_is_symmetric_so_the_turned_lens_is_the_back_heads():
    spec = _cfg(ROOT / "assets" / "models" / "streetlight_led.json")
    assert spec["lens_centre_m"][0] == 4.0376
    tw = [tuple(map(float, l.split()[1:4])) for l in open(ROOT / "assets" / "models" / "streetlight_led_post_twin.obj")
          if l.startswith("v ")]
    hi = [v for v in tw if v[1] > 11.0]
    assert abs(min(v[0] for v in hi) + max(v[0] for v in hi)) < 1e-6   # symmetric heads


# ------------------------------------------------------------------ signs (round 2)
def _mesh_curb_crossing():
    """tools/author_signs_blend.mesh_curb_crossing's own source, run on stand-in surfaces (the module imports bpy)"""
    import types
    import place_signs as ps
    src = (ROOT / "tools" / "author_signs_blend.py").read_text(encoding="utf-8")
    i0 = src.index("def mesh_curb_crossing(")
    sm = types.SimpleNamespace(top_hit=lambda b, x, z: None if b is None else b(x, z),
                               on_road=lambda road, ground, x, z: road(x, z) is not None)
    ns = {"sm": sm, "ps": ps, "math": math}
    exec(src[i0:src.index(chr(10) + "def ", i0 + 10)], ns)
    return ns["mesh_curb_crossing"]


def test_walk_built_only_reads_no_walk_off_a_pad_ground_band():
    """Sand Creek round 2 item 3 (2026-11-23): past a pad's deck edge the pad's ground band is flat terrain (deck - 0.04 m;
    0.2.9's SC-D56-fwd ray: 6.924-6.937 m for 3.25 m) and the walk read off `ground` (TERRAIN included) took it for a
    3.6 m walk. With signs.json defaults.walk_built_only the walk is read off the built walk meshes alone: no walk there,
    so the march starts lateral_offset_m past the edge and the post's base is the ray-cast terrain (round L's rule)"""
    import place_signs as ps
    mcc = _mesh_curb_crossing()
    road = lambda x, z: 1.0 if x < 10.0 else None                          # the deck, to s 10 along +x
    terrain = lambda x, z: 0.96 if x < 13.5 else 0.96 - 0.2 * (x - 13.5)    # the band, then the bank falls
    old = mcc(road, terrain, (0.0, 0.0), (1.0, 0.0), 1.8, 10.0)
    assert old["s_C"] == 10.0 and 3.4 < old["walk_run_m"] < 3.9 and old["s_S"] > old["s_C"] + 3.0   # the misread
    new = mcc(road, terrain, (0.0, 0.0), (1.0, 0.0), 1.8, 10.0, walk=None) == old                      # absent: as before
    assert new
    none = mcc(road, terrain, (0.0, 0.0), (1.0, 0.0), 1.8, 10.0, walk=lambda x, z: None)
    assert none["s_C"] == 10.0 and "s_S" not in none                     # no built walk: no s_S (no modelled walk)
    strip = lambda x, z: 1.05 if 10.0 <= x < 12.4 else None             # a built 2.4 m strip still reads as the walk
    kept = mcc(road, lambda x, z: strip(x, z) or terrain(x, z), (0.0, 0.0), (1.0, 0.0), 1.8, 10.0, walk=strip)
    assert 2.3 < kept["walk_run_m"] < 2.5 and kept["s_S"] is not None
    # opt-in, Sand Creek alone; a non-bool is refused; SC-D56 is a live corner again
    assert ps.OPT_IN_DEFAULTS["walk_built_only"] is False and "walk_built_only" not in ps.DEFAULTS
    with pytest.raises(ps.SignsConfigError):
        ps.validate_overrides({"walk_built_only": "yes"}, {})
    for p in sorted((ROOT / "tracks").glob("*/signs.json")):
        d = _cfg(p)
        if p.parent.name == "sand-creek-lm":
            assert d["defaults"]["walk_built_only"] is True and "skip" not in d["corners"]["SC-D56"]
            # fwd only (the Mac, 2026-11-23, after rehearsal 0210's FAIL SC-D56-rev c_built_edge_clearance): rev is
            # skipped by its own sub-object, merged by place_signs.effective_override; fwd carries no skip
            ov = d["corners"]["SC-D56"]
            assert ps.effective_override(ov, True)["skip"] is True and "grid_primary_35" in ov["rev"]["reason"]
            assert not ps.effective_override(ov, False).get("skip") and "fwd" not in ov
        else:
            assert "walk_built_only" not in (d.get("defaults") or {}), p


# ------------------------------------------------------------------ street profiles (round 2)
def test_round_2_profiles_are_round_i_plus_three_streets_at_their_true_lonlat():
    """Sand Creek round 2 (2026-11-23): round I's seven held streets were re-read at each grid point's own lon / lat; the
    three that now pass round I's unchanged 0.5 m neighbour-jump rule join (grid_secondary_8, grid_secondary_42,
    grid_primary_71); grid_primary_15 (the viaduct) and the three still jumping stay on 3DEP; round I's 99 are as measured"""
    cfg = _cfg(SC / "track.config.json")
    assert cfg["lm_intake"]["connector_profiles"] == "source/connector_profiles.lidar.round_2.json"
    r2 = _cfg(SC / "source" / "connector_profiles.lidar.round_2.json")
    ri = _cfg(SC / "source" / "connector_profiles.lidar.round_i.json")
    joined = {"grid_secondary_8", "grid_secondary_42", "grid_primary_71"}
    assert set(r2["connectors"]) == set(ri["connectors"]) | joined
    assert all(r2["connectors"][n] == ri["connectors"][n] for n in ri["connectors"])
    assert not {"grid_primary_15", "grid_primary_11", "grid_secondary_39", "grid_unclassified_77"} & set(r2["connectors"])
    assert r2["ept"] == ri["ept"] and r2["radius_m"] == ri["radius_m"] and r2["min_returns"] == ri["min_returns"]
    src = {c["name"]: c for c in _cfg(ROOT / "tracks" / "sand-creek" / "data" / "connectors.local.json")["connectors"]}
    for n in joined:
        q, pts = r2["connectors"][n], src[n]["points_xyz_m"]
        ys = q["y"]
        assert max(abs(b - a) for a, b in zip(ys, ys[1:])) <= 0.5, n                       # round I's rule
        assert len(ys) == len(pts) and all(abs(p[0] - a[0]) <= 0.01 and abs(p[2] - a[1]) <= 0.01 for p, a in zip(pts, q["xz"]))
    assert "source/connector_profiles.lidar.round_2.json" in _cfg(SC / "ship.json")["sync_in"]["required"] +         _cfg(SC / "ship.json")["sync_in"].get("optional", [])


# ------------------------------------------------------------------ the ground beside the Quebec arms (round 2 item 2)
def _gp_funcs(names):
    """tools/ground_patch_blend.py's pure helpers, compiled on their own (the module imports bpy and runs main())"""
    import ast
    path = ROOT / "tools" / "ground_patch_blend.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mod = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
    ns = {"math": math}
    exec(compile(mod, str(path), "exec"), ns)
    return ns


def test_the_edge_lift_goes_up_to_the_lidar_or_the_lip_and_never_down():
    """ledger 0098 round 2 item 2: a lift patch raises a vertex to min(the measured lidar ground, the lip) and nothing else"""
    ns = _gp_funcs({"lift_to", "tri_height"})
    lift = ns["lift_to"]
    assert lift(24.0, 24.9, 24.7) == 24.7           # the lip (deck - clear) caps it: never past the lip
    assert lift(24.0, 24.5, 24.7) == 24.5           # the lidar caps it: never above the real ground
    assert lift(24.8, 24.9, 24.7) is None           # already over its target: it stays (nothing is lowered)
    assert lift(24.69995, 24.9, 24.7) is None       # within 0.1 mm: no move
    assert lift(24.0, None, 24.7) is None and lift(24.0, 24.9, None) is None
    th = ns["tri_height"]
    t = ((0.0, 0.0, 1.0), (2.0, 0.0, 3.0), (0.0, 2.0, 1.0))  # z = 1 + x
    assert th(t, 0.5, 0.5) == pytest.approx(1.5) and th(t, 1.0, 0.25) == pytest.approx(2.0)
    assert th(((0.0, 0.0, 1.0), (1.0, 1.0, 2.0), (2.0, 2.0, 3.0)), 0.5, 0.5) is None     # no plan area
    src = (ROOT / "tools" / "ground_patch_blend.py").read_text(encoding="utf-8")
    # a lift patch cuts nothing and carries no feather, weight or split; every other patch takes the old path
    assert 'if p.get("lift") is not None:' in src and "a lift patch cuts nothing and has no feather, weight or" in src
    assert 'if p.get("feather_spares_roads") is not None:' in src and "spare.find_nearest((x, z, 0.0), 1e-3)" in src
    assert "for _ in range(0 if p.get(\"split_mode\") == \"bisect\" else 12):" in src


WALL_49_SHA256 = "be105a14b3381c24da4eeb1e2e7e5199ad2cb395935f9060bb8f4679e600adf7"
QUEBEC = ("quebec_nw78", "quebec_median", "quebec_se84")
QUEBEC_LIFT = ("quebec_lift_pad", "quebec_lift_arms")


def test_sand_creek_quebec_patches_as_measured():
    """the three ground patches beside the Northfield Quebec arms and the two lift zones (round 2 item 2), measured by
    tools/lidar_ground_patch.measure off the cached CO_DRCOG_2_2020 tiles; wall_49's measured record untouched"""
    import hashlib
    ter = _cfg(SC / "track.config.json")["terrain"]
    ids = [p["id"] for p in ter["lidar_patches"]]
    assert ids == ["wall_49", *QUEBEC, *QUEBEC_LIFT]                 # the lift zones last: after the patches beside
    cand = _cfg(SC / "source" / "round_k" / "track.config.json")["terrain"]
    assert ter["lidar_patches"][0] == cand["lidar_patches"][0]       # wall_49's own entry as round I declared it
    assert ter["_lidar_patches_doc"].startswith(cand["_lidar_patches_doc"]) and "ROUND 2 (ledger 0098" in ter["_lidar_patches_doc"]
    meas = _cfg(SC / ter["lidar_patches_file"])
    assert list(meas["patches"]) == ids and meas["ept"].endswith("CO_DRCOG_2_2020/ept.json")
    w = json.dumps(meas["patches"]["wall_49"], separators=(",", ":"))
    assert hashlib.sha256(w.encode()).hexdigest() == WALL_49_SHA256
    by = {p["id"]: p for p in ter["lidar_patches"]}
    for pid in (*QUEBEC, *QUEBEC_LIFT):
        p, L = by[pid], meas["patches"][pid]
        assert L["polygon"] == p["polygon"] and L["cell_m"] == 1.0 and len(L["y"]) == L["nx"] * L["nz"]
        assert L["filled"] <= 0.02 * L["read"], pid                  # a few nodes under no return, filled
    for pid in QUEBEC:
        p = by[pid]
        assert "lift" not in p and set(p["hard_edges"]) <= set(range(len(p["polygon"])))
        # a feathered patch's feather never moves the ground under a road or walk (the 0.5 m gap and the walk stay the seats')
        assert (p.get("feather_spares_roads") == ["ROAD", "CURB", "1ROAD"]) == (p["feather_m"] > 0), pid
    assert by["quebec_median"]["feather_m"] == 0.0 and len(by["quebec_median"]["hard_edges"]) == len(by["quebec_median"]["polygon"])
    for pid, gap in zip(QUEBEC_LIFT, (2.0, 1.25)):       # 0.2.11: the pad's gap 1.25 -> 2.0 (the median nose's T)
        p = by[pid]
        assert p["feather_m"] == 0.0 and "hard_edges" not in p and "split_m" not in p
        assert p["lift"] == {"clear_m": 0.16, "gap_m": gap, "road_prefixes": ["ROAD", "CURB", "1ROAD"]}
    # the lift zones keep off both bridge decks the 2020 lidar reads as class 17: Quebec St over Sand Creek (the pad's
    # S end, x 1765-1790, z -530..-510) and I-70 NE of the arms' merge (x >= 1860, z >= -415)
    sys.path.insert(0, str(ROOT / "tools"))
    import lidar_ground_patch as lgp
    for pid in QUEBEC_LIFT:
        poly = [tuple(q) for q in by[pid]["polygon"]]
        for x, z in ((1775.0, -512.0), (1783.3, -521.1), (1790.0, -510.0), (1865.0, -390.0), (1880.0, -415.0)):
            assert not lgp.point_in(poly, x, z), (pid, x, z)


def test_nb12_stands_where_0_2_9_stood_it():
    """0.2.11 (the Mac, after 0.2.10 skipped nb12): its setback is hand-set to 0.2.9's built spot (1809.22, -501.43), 13.5 m
    along and 19.2 m left of v1942, now that the lap there is 17.25 m wide (the flare off); every other post keeps the
    generator's 2.1 m"""
    nb = _cfg(SC / "source" / "name_blades.json")
    posts = {p["id"]: p for p in nb["posts"]}
    assert posts["nb12"]["setback_m"] == 10.58 and posts["nb12"]["vertex"] == 1942 and posts["nb12"]["along_m"] == 7.75
    assert all(p["setback_m"] == nb["setback_m"] == 2.1 for k, p in posts.items() if k != "nb12")
    assert "HAND-SET" in nb["_doc"] and "nb12" in nb["_doc"]


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
    assert cfg["scenery"]["streetlights"]["light_both_heads"] is True and cfg["version"] == "0.2.11"


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
        for p in (cfg.get("terrain") or {}).get("lidar_patches") or []:                                     # round 2
            assert "lift" not in p and "feather_spares_roads" not in p, (t, p.get("id"))


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
