"""The fleet on Lake Murray v4's engine (ledger 0078): what the port changed in Lake Murray's own code leaves Lake Murray as
it was, and the intake's grid helpers keep the 3DEP samples.

- scripts-v021 build_loop_blend: route.edge's defaults are exactly the literals the assembler always swept (curb 0.14
  over 0.08, walk 1.8 / 1.5 on connectors, grade 1.2, clearance 0.10, lift 0.10), and with no route.crossfall_file there
  is no bank (the ribbon / curb / paint / conform calls get no bank_at at all);
- tools/route_connectors.py: absent route.connector_max_grade_pct = Lake Murray's 11 %;
- tools/lm_engine_intake.py: the .npy writer round-trips the reader, and the bilinear upsample keeps every source sample.
"""
from __future__ import annotations

import ast
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASM = ROOT / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "blender" / "build_loop_blend.py"
sys.path.insert(0, str(ROOT / "tools"))


def _assembler_funcs(*names):
    """the named top-level functions / assignments of the assembler, executed without bpy"""
    tree = ast.parse(ASM.read_text(encoding="utf-8"))
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names)
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in names for t in n.targets))]
    ns = {"json": json, "math": __import__("math")}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(ASM), "exec"), ns)
    return ns


def _v021_ribbon():
    import importlib.util
    p = ROOT / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "ribbon.py"
    spec = importlib.util.spec_from_file_location("_v021_ribbon", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_edge_defaults_are_lake_murrays_literals():
    ns = vars(_v021_ribbon())
    main, conn = ns["edge_profile"]({})
    assert main == {"lift": 0.10, "curb_h": 0.14, "curb_face_w": 0.08, "sidewalk_w": 1.8, "grade_w": 1.2,
                    "grass_clearance": 0.10}
    assert conn == dict(main, sidewalk_w=1.5)
    # Lake Murray's route block declares no edge and no crossfall file
    cfg = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json").read_text(encoding="utf-8"))
    assert "edge" not in cfg.get("route", {}) and "crossfall_file" not in cfg.get("route", {})
    assert "lane_dividers" not in cfg.get("route", {}) and "draft_lamps" not in cfg.get("scenery", {})
    assert ns["edge_profile"](cfg.get("route"))[0] == main
    # an unknown key is refused, never silently ignored
    try:
        ns["edge_profile"]({"edge": {"curb_hieght": 0.1}})
    except SystemExit as e:
        assert "unknown key" in str(e)
    else:
        raise AssertionError("accepted a misspelt edge key")


def test_no_crossfall_file_no_bank():
    ns = _assembler_funcs("crossfall_bank")
    assert ns["crossfall_bank"](Path("."), {}, [(0, 0, 0), (1, 0, 0)]) == (None, None)
    text = ASM.read_text(encoding="utf-8")
    # absent: every call is made exactly as before (no bank_at keyword at all)
    assert '_bk = {"bank_at": bank_at} if bank_at is not None else {}' in text


def test_every_opt_in_is_absent_from_lake_murray_and_guarded_in_the_assembler():
    text = ASM.read_text(encoding="utf-8")
    assert 'route.get("lane_dividers", True) is False' in text
    assert '(cfg.get("scenery") or {}).get("draft_lamps", True) is False' in text
    assert "edge_main, edge_conn = ribbon.edge_profile(route)" in text
    weld = (ROOT / "tools" / "weld_mouths_blend.py").read_text(encoding="utf-8")
    assert "_edge_main, edge_conn = wr.edge_profile(cfg_route)" in weld and "curb_h=0.14" not in weld
    # the ports' tools are steps Lake Murray's ship.json never names
    sd = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "ship.json").read_text(encoding="utf-8"))
    names = {n for ph in sd["steps"].values() for n in ph}
    assert not names & {"lm_intake", "densify_ribbon", "seat_edges", "edge_report"}


def test_route_connectors_cap_default_is_lake_murrays():
    import route_connectors as rc
    assert rc.MAX_GRADE == 0.11
    lm = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json").read_text(encoding="utf-8"))
    assert "connector_max_grade_pct" not in (lm.get("route") or {})


def test_intake_npy_round_trip_and_upsample_keeps_samples():
    import lm_engine_intake as L
    grid = [[1.0, 2.0, 4.0], [3.0, 5.0, 9.0]]
    p = Path(tempfile.mkdtemp()) / "h.npy"
    L._write_npy(p, grid)
    assert L._read_npy(p) == grid
    up, meta = L._upsample(grid, {"nx": 3, "ny": 2, "spacing_m": 40.0}, 2)
    assert (meta["nx"], meta["ny"], meta["spacing_m"]) == (5, 3, 20.0)
    for j in range(2):
        for i in range(3):
            assert up[2 * j][2 * i] == grid[j][i]
    assert up[0][1] == 1.5 and up[1][0] == 2.0


def test_traced_kerbs_ship_in_the_road_kn5_with_their_own_uvs():
    """The traced kerbs are 1KERB_circuit_* (kerb physics, the ROAD kn5), never 1KERB_RACE_* (race furniture: the split
    routes it to the race kn5 and a track with no race layout refuses it); their stripe UVs are a layer that is not
    "UVMap" (engine-july's prep writes its planar UVs into "UVMap"); each port's kerb texture binds the 1KERB row."""
    src = (ROOT / "tools" / "author_kerbs_blend.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    consts = {t.id: n.value.value for n in tree.body if isinstance(n, ast.Assign) for t in n.targets
              if isinstance(t, ast.Name) and isinstance(n.value, ast.Constant)}
    assert consts["PREFIX"] == "1KERB_circuit_" and not consts["PREFIX"].upper().startswith(("1KERB_RACE", "1KERB_SIDEWALK"))
    assert consts["UV_LAYER"] != "UVMap"
    for t in ("high-plains-lm", "exotics-racing-lv-lm"):
        cfg = json.loads((ROOT / "tracks" / t / "track.config.json").read_text(encoding="utf-8"))
        assert "1KERB" in cfg["texture_overrides"] and "1KERB_RACE" not in cfg["texture_overrides"]
        assert (ROOT / "tracks" / t / cfg["texture_overrides"]["1KERB"]["diffuse"]).exists()
