"""Ledger 0092: Milford's ground beside the road (the 2026-11-18 scenery audit, items 1, 3, 5, 6, 7b).

Every key is opt-in: Milford names terrain.lidar_patches(_npz/_file) with a corridor patch, scenery.bespoke.pads_seat /
pads_surface and the run-off pads, grassfx_zones near / pad_looks / fade_by_map / frame; no other track does, and each tool
without them does what it did (the planner byte for byte on Milford's own committed reading)."""
from __future__ import annotations

import ast
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "tools"
MF = REPO / "tracks" / "milford-road-course-lm"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO))

np = pytest.importorskip("numpy")


def _cfg(track: Path) -> dict:
    return json.loads((track / "track.config.json").read_text(encoding="utf-8"))


def _blend_funcs(path: Path, names):
    """the pure helpers of a Blender script (it imports bpy and runs main() at import), compiled on their own"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mod = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
    ns = {"math": math}
    exec(compile(mod, str(path), "exec"), ns)
    return ns


# --- tools/lidar_ground_patch.py: the committed 1 m grid -----------------------------------------------------------------

def _grid_project(tmp_path: Path, patches, line=None):
    proj = tmp_path / "proj"
    (proj / "data").mkdir(parents=True)
    (proj / "source").mkdir()
    g = np.full((40, 60), -1, np.int16)                  # 60 x 40 m, row 0 = south; ground 2.00 m + 1 cm per column
    for j in range(40):
        for i in range(60):
            g[j, i] = 200 + i
    g[20, 30] = -1                                      # one hole (a roof)
    np.savez(proj / "source" / "grid.npz", e0=np.int64(-30), n0=np.int64(-20), cell=np.float64(1.0), nx=np.int64(60),
             ny=np.int64(40), z0_m=np.float64(100.0), ground_z_cm_over_z0=g)
    line = line or {"origin": {"lon": 0.0, "lat": 0.0, "elev_m": 100.0},
                    "points_xyz_m": [[-40.0, 0.0, 0.0], [40.0, 0.0, 0.0]], "widths_m": [10.0, 10.0]}
    (proj / "data" / "centerline.local.json").write_text(json.dumps(line), encoding="utf-8")
    (proj / "track.config.json").write_text(json.dumps({"terrain": {
        "lidar_patches_npz": "source/grid.npz", "lidar_patches_file": "data/patches.json", "lidar_patches": patches}}),
        encoding="utf-8")
    return proj


def test_npz_patch_reads_the_grid_on_its_own_cell_centres(tmp_path):
    import lidar_ground_patch as lgp
    poly = [[-5.0, -5.0], [5.0, -5.0], [5.0, 5.0], [-5.0, 5.0]]
    proj = _grid_project(tmp_path, [{"id": "box", "polygon": poly, "feather_m": 2.0}])
    assert lgp.main([str(proj)]) == 0
    L = json.loads((proj / "data" / "patches.json").read_text())["patches"]["box"]
    assert L["polygon"] == poly and "w" not in L
    assert L["cell_m"] == 1.0 and L["x0"] == -7.5 and L["z0"] == -7.5      # cell centres, the box grown by the feather
    y = L["y"]
    for jj in range(L["nz"]):
        for ii in range(L["nx"]):
            x, z = L["x0"] + ii, L["z0"] + jj
            col = int(math.floor(x + 30))
            v = y[jj * L["nx"] + ii]
            if (x, z) == (0.5, 0.5):                     # the hole: filled from its four neighbours (2.29 / 2.31 / 2.30 x2)
                assert v == pytest.approx(2.30, abs=1e-6)
            else:
                assert v == pytest.approx(2.0 + col / 100.0, abs=1e-6)   # local: 100 + cm / 100 - elev 100
    assert L["filled"] == 1


def test_corridor_weight_profile():
    import lidar_ground_patch as lgp
    c = {"in0_m": 9.0, "in1_m": 16.0, "full_m": 35.0, "zero_m": 45.0}
    d = np.array([-3.0, 0.0, 9.0, 12.5, 16.0, 20.0, 35.0, 40.0, 45.0, 60.0, np.inf])
    w = lgp.corridor_weight(d, c)
    assert w.tolist() == pytest.approx([0, 0, 0, 0.5, 1, 1, 1, 0.5, 0, 0, 0])


def test_corridor_patch_writes_weights_and_nulls_where_none(tmp_path):
    import lidar_ground_patch as lgp
    poly = [[-29.0, -19.0], [29.0, -19.0], [29.0, 19.0], [-29.0, 19.0]]
    cor = {"in0_m": 2.0, "in1_m": 4.0, "full_m": 8.0, "zero_m": 12.0}
    proj = _grid_project(tmp_path, [{"id": "c", "polygon": poly, "feather_m": 0.0, "corridor": cor}])
    assert lgp.main([str(proj)]) == 0
    L = json.loads((proj / "data" / "patches.json").read_text())["patches"]["c"]
    assert L["corridor"] == cor and len(L["w"]) == len(L["y"]) == L["nx"] * L["nz"]
    for jj in range(L["nz"]):
        z = L["z0"] + jj
        d = abs(z) - 5.0                                  # the lane edge of a straight 10 m road along x
        k = jj * L["nx"] + L["nx"] // 2
        assert L["w"][k] == pytest.approx(float(lgp.corridor_weight(np.array([d]), cor)[0]), abs=1e-3)
        assert (L["y"][k] is None) == (L["w"][k] == 0)


def test_ept_path_refuses_a_corridor_without_the_grid(tmp_path):
    import lidar_ground_patch as lgp
    proj = _grid_project(tmp_path, [{"id": "c", "polygon": [[0, 0], [1, 0], [1, 1]], "corridor": {"full_m": 1, "zero_m": 2}}])
    cfg = _cfg(proj)
    del cfg["terrain"]["lidar_patches_npz"]
    (proj / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(SystemExit, match="committed grid"):
        lgp.main([str(proj)])


def test_milford_corridor_lattice_off_the_committed_grid(tmp_path):
    """the real thing, as the chain's draft step ground_patch runs it (no network): Milford's two patches"""
    import lidar_ground_patch as lgp
    ter = _cfg(MF)["terrain"]
    assert ter["lidar_patches_npz"] == "source/lidar/milford_lidar_1m.npz" and (MF / ter["lidar_patches_npz"]).exists()
    proj = tmp_path / "mf"
    (proj / "data").mkdir(parents=True)
    (proj / "source" / "lidar").mkdir(parents=True)
    shutil.copy(MF / "track.config.json", proj / "track.config.json")
    shutil.copy(MF / "data" / "centerline.local.json", proj / "data" / "centerline.local.json")
    shutil.copy(MF / ter["lidar_patches_npz"], proj / ter["lidar_patches_npz"])
    assert lgp.main([str(proj)]) == 0
    P = json.loads((proj / ter["lidar_patches_file"]).read_text())["patches"]
    assert set(P) == {p["id"] for p in ter["lidar_patches"]}
    cor = P["corridor"]
    w = np.array(cor["w"])
    y = np.array([np.nan if v is None else v for v in cor["y"]])
    assert (np.isfinite(y) == (w > 0)).all()             # every weighted node has a ground, filled where the grid has none
    assert 250_000 < int((w > 0).sum()) < 400_000
    assert np.nanmin(y) > -5 and np.nanmax(y) < 45        # local metres (the grid is 313.3-361 m NAVD88, origin 316.26)


# --- tools/ground_patch_blend.py: the weighted lattice's own helpers ------------------------------------------------------

def test_weight_at_is_bilinear_and_zero_off_the_lattice():
    ns = _blend_funcs(TOOLS / "ground_patch_blend.py", {"weight_at", "lattice_at"})
    L = {"x0": 0.0, "z0": 0.0, "cell_m": 1.0, "nx": 2, "nz": 2, "w": [0.0, 1.0, 0.0, 1.0], "y": [1.0, 2.0, None, 4.0]}
    assert ns["weight_at"](L, 0.25, 0.5) == pytest.approx(0.25)
    assert ns["weight_at"](L, -0.1, 0.5) == 0.0 and ns["weight_at"](L, 0.5, 1.2) == 0.0
    assert ns["lattice_at"](L, 0.5, 0.0) == pytest.approx(1.5)


def test_ground_patch_blend_opt_ins_leave_the_old_paths():
    src = (TOOLS / "ground_patch_blend.py").read_text(encoding="utf-8")
    # the subdivide-and-triangulate pass is the default; bisection and the weight only when the patch / lattice names them
    assert 'p.get("split_mode") == "bisect"' in src and 'L.get("w") is not None' in src
    assert "for _ in range(0 if p.get(\"split_mode\") == \"bisect\" else 12):" in src
    assert 'bmesh.ops.subdivide_edges(bm, edges=long_e, cuts=1, use_grid_fill=False)' in src


# --- the run-off pads and the config ---------------------------------------------------------------------------------------

def test_milford_runoff_pads_are_the_outliners_and_seat_on_the_ground():
    bes = _cfg(MF)["scenery"]["bespoke"]
    assert bes["pads_seat"] == "ground" and bes["pads_surface"] == "1RUNOFF"
    pads = bes["pads"]
    assert pads[0]["key"] == "ride_pad" and "quad_lonlat" in pads[0]       # PADAPRON_0 stays the ride pad
    rec = json.loads((MF / "source" / "runoff" / "runoff_pads.json").read_text(encoding="utf-8"))
    kept = [b for b in rec["blobs"] if b["kept"]]
    assert [p["key"] for p in pads[1:]] == [b["key"] for b in kept]
    for p in pads[1:]:
        st = p["strip_lonlat"]
        assert len(st["inner"]) == len(st["outer"]) >= 2
    assert all(b["folds"] == 0 for b in kept) and not rec["overlaps"]
    assert all(b["naip_b_over_r"] >= rec["params"]["PAVED_B_OVER_R"] for b in kept)
    tex = _cfg(MF)["texture_overrides"]["1RUNOFF"]
    assert tex["diffuse"] == "assets/textures/building_diffuse.jpg" and (REPO / tex["diffuse"]).exists()


def test_runoff_outliner_reproduces_the_committed_record(tmp_path):
    """deterministic: the committed record is what the outliner writes off the line it names (its md5). Ledger 0091 moved the
    line (lm_intake.line_precomp, 0.75 m rows): the record is made off the intake's own line of this config, run here into
    an empty workshop (the build commits that line as data/centerline.local.json; the committed one may still be 0.1.12's)"""
    pytest.importorskip("PIL")
    import hashlib
    import lm_engine_intake as L
    rec_p = MF / "source" / "runoff" / "runoff_pads.json"
    before = rec_p.read_bytes()
    ws = tmp_path / "ws"
    spec = json.loads((MF / "ship.json").read_text(encoding="utf-8"))["sync_in"]
    for rel in spec.get("required", []) + [r for r in spec.get("optional", []) if (MF / r).exists()]:
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(MF / rel, ws / rel)
    L.intake(ws)
    line_p = ws / "data" / "centerline.local.json"
    assert json.loads(before)["line"]["md5"] == hashlib.md5(line_p.read_bytes()).hexdigest()
    try:
        out = subprocess.run([sys.executable, str(MF / "source" / "runoff" / "scripts" / "runoff_pads.py"), "--line",
                              str(line_p)], cwd=REPO, capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        assert rec_p.read_bytes() == before
    finally:
        rec_p.write_bytes(before)


# --- tools/plan_grassfx_aerial.py ---------------------------------------------------------------------------------------

def _gfx_project(tmp_path, drop_keys):
    proj = tmp_path / "gfx"
    for rel in ("data", "source/vegetation"):
        (proj / rel).mkdir(parents=True, exist_ok=True)
    cfg = _cfg(MF)
    gz = cfg["scenery"]["bespoke"]["grassfx_zones"]
    for k in drop_keys:
        gz.pop(k, None)
    (proj / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    shutil.copy(MF / "data" / "centerline.local.json", proj / "data")
    shutil.copy(MF / gz["image"], proj / gz["image"])
    return proj


def test_grassfx_without_the_new_keys_is_byte_identical(tmp_path):
    """the planner before ledger 0092 (main 74b46263) and now, on one reading without the new keys: the same bytes"""
    pytest.importorskip("PIL")
    old = subprocess.run(["git", "show", "74b46263:tools/plan_grassfx_aerial.py"], cwd=REPO, capture_output=True)
    if old.returncode != 0:
        pytest.skip("main 74b46263 is not in this clone")
    od = tmp_path / "old_tools"
    od.mkdir()
    (od / "plan_grassfx_aerial.py").write_bytes(old.stdout)
    proj = _gfx_project(tmp_path, ("frame", "near", "pad_looks", "fade_by_map"))
    env = {**__import__("os").environ, "PYTHONPATH": str(TOOLS)}       # the old copy finds tools/plan_bespoke_vegetation.py
    outs = []
    for tool in (od / "plan_grassfx_aerial.py", TOOLS / "plan_grassfx_aerial.py"):
        r = subprocess.run([sys.executable, str(tool), str(proj)], capture_output=True, text=True, cwd=REPO, env=env)
        assert r.returncode == 0, r.stderr
        outs.append((proj / "data" / "grassfx.aerial.json").read_bytes())
    assert outs[0] == outs[1] and len(json.loads(outs[1])["adjustments"]) > 1000


def test_grassfx_near_cells_pad_looks_and_fades(tmp_path):
    pytest.importorskip("PIL")
    proj = _gfx_project(tmp_path, ())
    gz = _cfg(MF)["scenery"]["bespoke"]["grassfx_zones"]
    assert gz["near"] == {"cell_m": 6, "reach_m": 30} and gz["frame"] == "projection"
    r = subprocess.run([sys.executable, str(TOOLS / "plan_grassfx_aerial.py"), str(proj)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    adj = json.loads((proj / "data" / "grassfx.aerial.json").read_text())["adjustments"]
    sizes = {s for a in adj for s in a["rect"]["size"]}
    assert all(abs(s / 6.0 - round(s / 6.0)) < 1e-6 for s in sizes) and any(abs(s / 12.0 - round(s / 12.0)) > 1e-6 for s in sizes)
    assert all(a["rect"]["fade"] == (12.0 if a["map"] == "B" else 6.0) for a in adj)
    # the ride pad reads D (no blades) over most of its quad
    from scripts.geometry.projection import _meters_per_degree
    cfg = _cfg(MF)
    o = json.loads((MF / "data" / "centerline.local.json").read_text())["origin"]
    mlon, mlat = _meters_per_degree(o["lat"])
    q = [((a - o["lon"]) * mlon, (b - o["lat"]) * mlat) for a, b in cfg["scenery"]["bespoke"]["pads"][0]["quad_lonlat"]]
    cx, cz = sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4
    hit = [a for a in adj if abs(a["rect"]["center"][0] - cx) <= a["rect"]["size"][0] / 2
           and abs(-a["rect"]["center"][2] - cz) <= a["rect"]["size"][1] / 2]
    assert hit and hit[0]["map"] == "D"


# --- opt-in: nobody else names the new keys ---------------------------------------------------------------------------------

NEW_TERRAIN = ("lidar_patches_npz",)
NEW_GFX = ("near", "pad_looks", "fade_by_map", "frame")


def test_only_milford_names_the_new_keys():
    for cfg_p in sorted((REPO / "tracks").glob("*/track.config.json")):
        cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
        ter = cfg.get("terrain") or {}
        gz = ((cfg.get("scenery") or {}).get("bespoke") or {}).get("grassfx_zones") or {}
        named = ([k for k in NEW_TERRAIN if k in ter] + [k for k in NEW_GFX if k in gz]
                 + [k for p in ter.get("lidar_patches") or [] for k in ("corridor", "split_mode") if k in p])
        if cfg_p.parent.name == "milford-road-course-lm":
            assert named, "Milford names its opt-ins"
        else:
            assert not named, f"{cfg_p.parent.name} names {named}"


def test_milford_ship_json_runs_the_ground_patch_and_syncs_the_grid():
    spec = json.loads((MF / "ship.json").read_text(encoding="utf-8"))
    assert "ground_patch" in spec["steps"]["draft"]
    assert "source/lidar/milford_lidar_1m.npz" in spec["sync_in"]["required"]
    sh = (TOOLS / "ship_track.sh").read_text(encoding="utf-8")
    body = sh[sh.index("draft_ground_patch() {"):]
    body = body[:body.index("\n}\n")]
    assert "lidar_patches_npz" in body and "tools/lidar_ground_patch.py" in body and "--npz" in body


def test_kn5_ground_check_reports_the_trunk_colliders_apart_and_gates_as_before():
    src = (REPO / "scripts" / "ac" / "kn5_ground_check.py").read_text(encoding="utf-8")
    assert "1WALL_GHOST_TRUNK" in src and '"gated": False' in src
    # the walls lens's own gate is the same expression on the same numbers
    assert "if med > 0.2 or p95 > 0.4 or bigf > 0.01 or nogf > 0.10:" in src
    assert src.count("= seat_lens(b, pts_b)") == 1 and "q = seat_lens(b, ghost[part])" in src


def _box(x, z, y0, h, r=0.3):
    v = [(x - r, y0, z - r), (x + r, y0, z - r), (x + r, y0, z + r), (x - r, y0, z + r),
         (x - r, y0 + h, z - r), (x + r, y0 + h, z - r), (x + r, y0 + h, z + r), (x - r, y0 + h, z + r)]
    t = [(0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7), (4, 5, 6), (4, 6, 7)]
    return v, t


def test_kn5_ground_check_trunk_split_is_info_and_the_verdict_is_mains(tmp_path):
    """a synthetic kn5 with sunk trunk colliders and a hovering rail: main's tool and this one give the same verdict and
    the same numbers; this one adds seating_info for the two parts, never a reason"""
    import importlib.util
    old = subprocess.run(["git", "show", "74b46263:scripts/ac/kn5_ground_check.py"], cwd=REPO, capture_output=True)
    if old.returncode != 0:
        pytest.skip("main 74b46263 is not in this clone")
    from tests.geometry.test_drive_test import _grass_plane, _write_obj
    from scripts.geometry import ribbon
    from scripts.ac.kn5_write import build
    from scripts.ac.kn5_ground_check import check
    d = tmp_path / "p"
    (d / "data").mkdir(parents=True)
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False}))
    cl = [(0.0, 0.0, float(z)) for z in range(0, 201, 5)]
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": [8.0] * len(cl), "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}))
    groups = [("1ROAD_main", ribbon.road_ribbon(cl, [8.0] * len(cl))), ("1GRASS", _grass_plane())]
    for name, boxes in (("1WALL_GHOST_TRUNK_0", [(12.0, 20.0 + 6 * k, -0.5, 3.0) for k in range(8)]),
                        ("1WALL_GHOST_RAIL_0", [(-8.0, 40.0 + 6 * k, 0.6, 0.7) for k in range(3)])):
        V, T = [], []
        for x, z, y0, h in boxes:
            v, t = _box(x, z, y0, h)
            T += [(a + len(V), b + len(V), c + len(V)) for a, b, c in t]
            V += v
        groups.append((name, {"vertices": V, "tris": T, "uvs": [(0.0, 0.0)] * len(V)}))
    _write_obj(d / "data" / "track.obj", groups)
    build(d)
    new = check(d)
    spec = importlib.util.spec_from_loader("kgc_main", loader=None)
    mod = importlib.util.module_from_spec(spec)
    exec(compile(old.stdout.decode("utf-8"), "kn5_ground_check@74b46263", "exec"), mod.__dict__)
    was = mod.check(d)
    assert new["fail"] == was["fail"] and new["reasons"] == was["reasons"]
    info = new.pop("seating_info")
    assert new == was
    assert set(info) == {"walls_trunk", "walls_rest"} and not any(v["gated"] for v in info.values())
    assert info["walls_trunk"]["objects"] == 8 and info["walls_trunk"]["median_m"] < 0
    assert info["walls_rest"]["median_m"] > 0.3            # the hovering rail, reported apart
