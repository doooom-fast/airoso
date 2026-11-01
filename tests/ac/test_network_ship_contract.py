"""The ship phase's DATA contract on a road network's reference line (no Blender here: the prep's bpy half cannot run).

scripts.geometry.network_reference writes the files a one-line track's draft writes; this pins that every reader of the
ship phase takes them as they are, with no reader changed for the line itself:
  * the prep (scripts/ac/build_kn5_loop.py): declare_bridge_spans converts the "mesh …" line to the KN5 frame and keeps
    the step's spans; a --from prep re-run keeps it; LegIndex reads an OPEN line (loop false); the 0020 corridor hash
    finds the reference carriageway; the single-layout dummies come from the step's dummies.json, facing the travel;
    an engine draft's ground is not re-conformed (the underlay report's auto rule);
  * kn5_to_gate_obj's gate centreline (z un-mirrored) is the step's own mesh-frame line, point for point;
  * write_ai_line reads the prepped line as the KN5 frame against centerline.local.json, and the grid says FORWARD on
    the point-to-point line;
  * make_map draws the reference line + every other built edge (Free Roam drives them all);
  * drive_test names every unjudged edge in its report when data/network.reference.json exists, and writes today's
    report byte for byte when it does not.
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

from scripts.ac import build_kn5_loop as bk
from scripts.geometry import dummies as dmod
from scripts.geometry import network_reference as nr
from tests.geometry.test_network_reference import LIFT, _network

ROOT = Path(__file__).resolve().parents[2]


def _drafted(tmp: Path, spans=None, z0=0.0) -> dict:
    fc, erec = _network(z0=z0)
    if spans:   # lift EB edge 2's surface 5.5 m (an OSM-layer deck the mesh raised): the step declares the span
        for e in erec["edges"]:
            if e["id"] == 2:
                e["surface_xyz_m"] = [[x, y + 5.5, z] for x, y, z in e["surface_xyz_m"]]
    (tmp / "data").mkdir(parents=True, exist_ok=True)
    (tmp / "data" / "network.geojson").write_text(json.dumps(fc))
    (tmp / "data" / "network.edges.local.json").write_text(json.dumps(erec))
    (tmp / "track.config.json").write_text(json.dumps({
        "slug": "net_t", "loop": False, "mirror_x": False, "true_north_rotation_deg": 0.0,
        "network": {"snap_grid_m": 7.0, "reference_line": {"ref": "I 8", "direction": "eastbound"}},
        "layouts": [{"id": "freeroam", "name": "Free Roam"}]}))
    nr.build(tmp)
    return erec


def test_the_prep_converts_the_reference_line_to_the_kn5_frame_and_keeps_its_spans():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _drafted(tmp, spans=True)
        mesh = json.loads((tmp / "data" / "finished_centerline.json").read_text())["points_xyz_m"]
        auto = json.loads((tmp / "data" / "bridge.spans.auto.json").read_text())
        assert auto and 295.0 <= auto[0][0] <= 305.0 and 595.0 <= auto[0][1] <= 600.0, auto
        spans = bk.declare_bridge_spans(tmp)
        assert spans == [tuple(s) for s in auto]
        fin = json.loads((tmp / "data" / "finished_centerline.json").read_text())
        assert fin["frame"] == bk.FC_FRAME_KN5 and "network" in fin["source"]
        assert fin["points_xyz_m"] == [[round(p[0], 3), round(p[1], 3), round(-p[2], 3)] for p in mesh]
        # a --from prep re-run keeps the prep's own earlier write
        assert bk.declare_bridge_spans(tmp) == spans
        assert json.loads((tmp / "data" / "finished_centerline.json").read_text()) == fin
        # kn5_to_gate_obj writes the gate centreline with z un-mirrored: the step's mesh-frame line, point for point
        gate = [[p[0], p[1], -p[2]] for p in fin["points_xyz_m"]]
        assert all(math.dist(g, m) < 1e-6 for g, m in zip(gate, mesh)) and len(gate) == len(mesh)


def test_the_prep_reads_an_open_line_its_corridor_and_its_grid():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _drafted(tmp)
        (tmp / "data" / "underlay.report.json").write_text("{}")
        bk.declare_bridge_spans(tmp)
        legs = bk.LegIndex.from_project(tmp)
        assert legs.closed == {"main": False} and abs(legs.length["main"] - 900.0) < 1e-6
        leg = legs.locate(450.0, 0.0)
        assert leg[0] == "main" and abs(leg[1] - 450.0) < 1e-6
        corr = bk._corridor_hash(tmp)
        d_in, deck = corr(450.0, 0.0, 14.62)                  # on the eastbound carriageway (Blender x=E, y=N, z=up)
        assert d_in < -7.0 and abs(deck - (14.5 + LIFT)) < 0.05
        d_out, _ = corr(450.0, 30.0, 14.62)                   # the other carriageway has no corridor: unjudged
        assert d_out > 0.0
        placed = dmod.load_draft(tmp / "data" / "dummies.json")
        assert {"AC_START_0", "AC_HOTLAP_START_0", "AC_TIME_0_L", "AC_TIME_0_R", "AC_PIT_0"} <= set(placed)
        local = json.loads((tmp / "data" / "centerline.local.json").read_text())
        yaw = dmod.facing_yaw([tuple(p) for p in local["points_xyz_m"]], placed["AC_START_0"])
        assert abs(math.degrees(yaw) - 90.0) < 1.0             # atan2(east, -north): facing east, the travel
        # an engine draft's ground is not conformed again (the underlay report's auto rule, build_kn5_loop.main)
        src = (ROOT / "scripts" / "ac" / "build_kn5_loop.py").read_text(encoding="utf-8")
        assert '_tc = not (proj / "data" / "underlay.report.json").exists()' in src


def test_write_ai_line_reads_the_kn5_frame_and_the_grid_says_forward():
    from scripts.ac.write_ai_line import _to_engine_frame, grid_alignment
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _drafted(tmp, z0=-1662.0)          # off the mirror axis, or the two frames read the same (the SD workshop: v0 z)
        bk.declare_bridge_spans(tmp)
        fin = json.loads((tmp / "data" / "finished_centerline.json").read_text())["points_xyz_m"]
        eng, how = _to_engine_frame(fin, tmp, False)
        assert how.startswith("kn5 frame"), how
        dums = json.loads((tmp / "data" / "dummies.json").read_text())
        closed = math.dist(eng[0], eng[-1]) < 1e-6
        assert closed is False
        dot, what = grid_alignment(eng, dums, closed)
        assert dot > 0.9 and "along the stage" in what


def test_make_map_draws_the_line_and_every_other_built_edge():
    import importlib.util
    spec = importlib.util.spec_from_file_location("make_map", ROOT / "tools" / "make_map.py")
    mm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mm)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _drafted(tmp)
        bk.declare_bridge_spans(tmp)
        main, conns = mm.load_lines(tmp)
        assert len(main) == 181 and main[0] == (0.0, -0.0)
        assert len(conns) == 4                                 # WB 4, 5, 6 and the ramp; EB 1-3 are the line itself
        assert any(abs(z + 30.0) < 1e-6 for c in conns for _x, z in c)     # kn5 frame: z mirrored


def test_drive_test_names_the_unjudged_edges_and_is_unchanged_without_the_record():
    from scripts.geometry.drive_test import run
    from tests.geometry.test_drive_test import _project
    d = _project()
    plain = run(d)
    assert "reference_line" not in plain
    before = (d / "data" / "drive_test.json").read_text()
    (d / "data" / "network.reference.json").write_text(json.dumps({
        "line": {"label": "I 8 eastbound", "edges": [1, 2, 3]}, "built_km": 1.86, "judged_km": 0.9,
        "unjudged_edges": 2, "unjudged_km": 0.96,
        "unjudged": [{"id": 4, "name": "I 8", "why": "the other carriageway", "length_m": 300.0},
                     {"id": 7, "name": None, "why": "ramp / interchange connector", "length_m": 61.0}]}))
    r = run(d)
    assert r["reference_line"]["unjudged"] == [[4, "I 8", "the other carriageway", 300.0],
                                               [7, None, "ramp / interchange connector", 61.0]]
    assert r["reference_line"]["unjudged_km"] == 0.96 and r["fail"] == plain["fail"]
    (d / "data" / "network.reference.json").unlink()
    run(d)
    assert (d / "data" / "drive_test.json").read_text() == before
