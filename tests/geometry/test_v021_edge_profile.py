"""scripts-v021 geometry/ribbon.edge_profile: route.edge -> the mainline and connector strip keywords (ledger 0078), and the
opt-in connector_grass_clearance (ledger 0087, Sand Creek 0.2.8). Loaded by path: the module is pure Python."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_s = importlib.util.spec_from_file_location(
    "_v021_ribbon_edge_profile", ROOT / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "ribbon.py")
rb = importlib.util.module_from_spec(_s)
_s.loader.exec_module(rb)


def test_no_edge_is_lake_murrays_own():
    main, conn = rb.edge_profile({})
    assert main == {"lift": 0.10, "curb_h": 0.14, "curb_face_w": 0.08, "sidewalk_w": 1.8, "grade_w": 1.2, "grass_clearance": 0.10}
    assert conn == dict(main, sidewalk_w=1.5)


def test_connectors_take_the_mainline_clearance_unless_told():
    edge = {"curb_h": 0.0, "sidewalk_w": 0.2, "connector_sidewalk_w": 0.2, "grade_w": 1.5, "grass_clearance": -0.08}
    main, conn = rb.edge_profile({"edge": edge})
    assert main["grass_clearance"] == conn["grass_clearance"] == -0.08
    main2, conn2 = rb.edge_profile({"edge": dict(edge, connector_grass_clearance=0.10, _doc="x")})
    assert main2 == main
    assert conn2 == dict(conn, grass_clearance=0.10)


def test_an_unknown_key_is_refused():
    with pytest.raises(SystemExit):
        rb.edge_profile({"edge": {"grass_clearence": 0.1}})
