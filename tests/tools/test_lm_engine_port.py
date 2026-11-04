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


def test_edge_defaults_are_lake_murrays_literals():
    ns = _assembler_funcs("EDGE_DEFAULTS", "edge_profile")
    main, conn = ns["edge_profile"]({})
    assert main == {"lift": 0.10, "curb_h": 0.14, "curb_face_w": 0.08, "sidewalk_w": 1.8, "grade_w": 1.2,
                    "grass_clearance": 0.10}
    assert conn == dict(main, sidewalk_w=1.5)
    # Lake Murray's route block declares no edge and no crossfall file
    cfg = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json").read_text(encoding="utf-8"))
    assert "edge" not in cfg.get("route", {}) and "crossfall_file" not in cfg.get("route", {})
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
