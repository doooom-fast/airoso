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
    assert not names & {"lm_intake", "densify_ribbon", "seat_edges", "strip_seam", "kerbs", "edge_report", "cutfill",
                        "lm_pads", "split_strip"}
    lm = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json").read_text(encoding="utf-8"))
    assert "densify" not in (lm.get("route") or {}) and "lm_intake" not in lm
    assert "lm_pads" not in lm and "strip_seam" not in lm      # round 7's pads and local seam scope never reach it
    assert "road_seek" not in (lm.get("lm_intake") or {})     # round 8's road seek never reaches it
    assert "source_data" not in (lm.get("lm_intake") or {})   # ledger 0080's network line never reaches it
    bes = (lm.get("scenery") or {}).get("bespoke") or {}
    assert "rails" not in bes and "pads" not in bes       # round 5's rail height_m and strip pads never reach it


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


# Every file a port's chain reads from its workshop after the intake, that only the intake or ship.json's sync_in provides
# (2026-11-03, the PC's Sand Creek rehearsal: the track folder read data/centerline.geojson, which only the Mac's old
# workshop held). The later steps that read them: the assembler (centerline.local, heightfield, connectors, crossfall),
# the weld (connectors, mouths), the track folder (centerline.geojson; osm.ways.json optional), the bespoke / kerb authors
# (the files the config names), the prep (bridges.cache.json when the config declares decks).
WORKSHOP_INPUTS = ("track.config.json", "data/centerline.local.json", "data/centerline.geojson", "data/heightfield.npy",
                   "data/heightfield.meta.json", "data/connectors.local.json", "data/mouths.json", "data/lm_intake.json")
PORTS = ("sand-creek-lm", "high-plains-lm", "exotics-racing-lv-lm", "milford-road-course-lm", "pikes-peak-lm",
         "lookout-lariat-lm", "rally-dragon-tail-gravel-lm", "rally-under-the-dragon-gravel-lm",
         "san-diego-freeway-lm")


def _sync_in(port: str, ws: Path):
    """ship.json's sync_in, as tools/ship_track.sh does it, into an EMPTY workshop"""
    spec = json.loads((ROOT / "tracks" / port / "ship.json").read_text(encoding="utf-8"))
    src = ROOT / "tracks" / port
    sin = spec.get("sync_in") or {}
    for rel in sin.get("required", []):
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).write_bytes((src / rel).read_bytes())
    for rel in sin.get("optional", []):
        if (src / rel).exists():
            (ws / rel).parent.mkdir(parents=True, exist_ok=True)
            (ws / rel).write_bytes((src / rel).read_bytes())


def spec_steps(port: str):
    spec = json.loads((ROOT / "tracks" / port / "ship.json").read_text(encoding="utf-8"))
    return [s for v in (spec.get("steps") or {}).values() for s in v]


def test_the_intake_into_an_empty_workshop_leaves_every_file_the_chain_reads():
    import shutil
    import lm_engine_intake as L
    for port in PORTS:
        ws = Path(tempfile.mkdtemp(prefix=f"empty_{port}_"))
        try:
            _sync_in(port, ws)
            L.intake(ws)
            cfg = json.loads((ws / "track.config.json").read_text(encoding="utf-8"))
            want = list(WORKSHOP_INPUTS)
            if (cfg.get("lm_intake") or {}).get("connectors"):
                # side streets in (Sand Creek 0.2.3, ledger 0079): the intake deletes any old mouths.json and the chain's
                # trim_connectors step writes it before weld_mouths reads it
                assert "trim_connectors" in spec_steps(port), port
                want.remove("data/mouths.json")
            if (cfg.get("lm_intake") or {}).get("crossfall"):
                want.append("data/crossfall.lm.json")
            if (cfg.get("route") or {}).get("kerbs_file"):
                want.append(cfg["route"]["kerbs_file"])
            if (cfg.get("capture") or {}).get("bridges"):
                want.append("data/bridges.cache.json")
            rels = []

            def _files(node):
                if isinstance(node, dict):
                    for k, v in node.items():
                        if k == "file" and isinstance(v, str):
                            rels.append(v)
                        elif not k.startswith("_"):
                            _files(v)
                elif isinstance(node, list):
                    for v in node:
                        _files(v)
            _files((cfg.get("scenery") or {}).get("bespoke") or {})
            for row in (cfg.get("texture_overrides") or {}).values():
                rels += [v for v in (row or {}).values() if isinstance(v, str) and v.startswith("textures/")]
            missing = [r for r in want + rels if not (ws / r).exists()]
            assert not missing, (port, missing)
            gj = json.loads((ws / "data" / "centerline.geojson").read_text(encoding="utf-8"))
            assert float(gj["features"][0]["properties"]["length_m"]) > 0      # what the track folder reads
        finally:
            shutil.rmtree(ws, ignore_errors=True)


def test_the_round_5_intake_options_report_what_they_did():
    """Milford's width taper widens only and its rows are re-cut every 1.5 m; Pikes Peak's right edge sits on the lidar wall
    (ledger 0078 round 5). Each option is the declaring track's alone."""
    import shutil
    import lm_engine_intake as L
    for port, check in (("milford-road-course-lm", "mf"), ("pikes-peak-lm", "pp")):
        ws = Path(tempfile.mkdtemp(prefix=f"r5_{port}_"))
        try:
            _sync_in(port, ws)
            rep = L.intake(ws)
            if check == "mf":
                assert rep["width_taper"]["points_widened"] > 0 and rep["width_taper"]["rate_m_per_m"] == 0.1
                assert rep["resample"]["spacing_m"] == 1.5 and rep["resample"]["points_after"] > rep["resample"]["points_before"]
                assert rep["edge_on_wall"] is None
            else:
                e = rep["edge_on_wall"]
                assert e["side"] == "right" and e["face_offset_m"]["min"] < -2.0 and e["width_m"][0] < 15.0
                assert rep["width_taper"] is None and rep["resample"] is None
        finally:
            shutil.rmtree(ws, ignore_errors=True)


def test_the_lariat_arcs_read_the_ground_and_the_pad_outlines_come_with_it():
    """Round 7: the C12 / C13 arcs' heights are 3DEP where the arcs stand (the steepest 10 m is not the index-kept
    15.48 %), and the 0.17.2 lidar pad outlines the pad step reads are carried into the workshop."""
    import shutil
    import lm_engine_intake as L
    ws = Path(tempfile.mkdtemp(prefix="r7_lariat_"))
    try:
        _sync_in("lookout-lariat-lm", ws)
        rep = L.intake(ws)
        assert all(r.get("heights", "").startswith("3DEP along the arc") for r in rep["corner_arcs"])
        loc = json.loads((ws / "data" / "centerline.local.json").read_text(encoding="utf-8"))
        assert L._max_grade([tuple(p) for p in loc["points_xyz_m"]], 10.0) < 0.15
        cfg = json.loads((ws / "track.config.json").read_text(encoding="utf-8"))
        for d in cfg["lm_pads"]["pads"]:
            rec = json.loads((ws / "source" / "pads" / f"{d['id']}.json").read_text(encoding="utf-8"))
            assert rec["cuts"] == d["cuts"] and rec["node"] == d["node"]
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def test_the_freeway_port_reads_the_network_line_and_cuts_the_grid_to_it():
    """ledger 0080: lm_intake.source_data reads the network draft's line from inside the source track; grid_crop_m keeps
    only source 3DEP samples (none moved or made) within its margin of the line; the width steps flare, never narrow"""
    import shutil
    import lm_engine_intake as L
    ws = Path(tempfile.mkdtemp(prefix="fwlm_"))
    try:
        _sync_in("san-diego-freeway-lm", ws)
        # ledger 0080 2b round 2: the port dropped its crop (the whole box builds); the mechanism is still tested, on
        # the crop it carried (1,000 m)
        wcfg = json.loads((ws / "track.config.json").read_text(encoding="utf-8"))
        wcfg["lm_intake"].setdefault("grid_crop_m", 1000)
        (ws / "track.config.json").write_text(json.dumps(wcfg, indent=2), encoding="utf-8")
        rep = L.intake(ws)
        src = ROOT / "tracks" / "san-diego-freeway" / "source" / "network-draft-pr34"
        meta = json.loads((ws / "data" / "heightfield.meta.json").read_text(encoding="utf-8"))
        smeta = json.loads((src / "heightfield.meta.json").read_text(encoding="utf-8"))
        c = meta["lm_intake_crop"]
        g = L._read_npy(ws / "data" / "heightfield.npy")
        sg = L._read_npy(src / "heightfield.npy")
        j0, i0 = c["rows"][0], c["cols"][0]
        # ledger 0080 phase 2a: lm_intake.grid_upsample divides the cut grid's facets (bilinear, the same samples at
        # every f-th row / column), so the crop is checked on the samples the cut kept
        f = int((meta.get("lm_intake_upsample") or {}).get("factor", 1))
        ny0, nx0 = (meta["ny"] - 1) // f + 1, (meta["nx"] - 1) // f + 1
        assert nx0 < smeta["nx"] and ny0 < smeta["ny"]
        assert all(abs(g[j * f][i * f] - sg[j0 + j][i0 + i]) < 1e-9 for j in range(ny0) for i in range(nx0))
        loc = json.loads((ws / "data" / "centerline.local.json").read_text(encoding="utf-8"))
        # ledger 0080 2a: the line the intake reads is the config's lm_intake.line_file (the NAIP-measured line)
        cfg = json.loads((ROOT / "tracks" / "san-diego-freeway-lm" / "track.config.json").read_text(encoding="utf-8"))
        sloc = json.loads((src / (cfg["lm_intake"].get("line_file") or "centerline.local.json")).read_text(encoding="utf-8"))
        assert len(loc["points_xyz_m"]) == len(sloc["points_xyz_m"])
        assert all(a >= b - 1e-9 for a, b in zip(loc["widths_m"], sloc["widths_m"]))
        assert rep is not None
    finally:
        shutil.rmtree(ws, ignore_errors=True)
