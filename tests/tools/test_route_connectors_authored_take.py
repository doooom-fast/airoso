"""tools/route_connectors.py route_connectors.authored_take (ledger 0054 P1, opt-in): the named weld stubs of the
authored intermediate (data/expansion.north.json welds[].connector) become connectors, exactly as authored in plan.

  * with the take, the [medium, short] connectors are written exactly as without it, the two stubs appended after
    them with the authored x / z and widths untouched (the flare IS the curb returns) and the 3DEP height smoothed as
    every route piece's is;
  * a take naming a weld the file lacks, a file in another frame, or a take without the file each stop the tool;
  * with the key absent the route stays HELD (test_route_connectors_held.py).
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRACK = ROOT / "tracks" / "san-diego-lake-murray"


def _tool():
    spec = importlib.util.spec_from_file_location("_tool_route_connectors_take", ROOT / "tools" / "route_connectors.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(rc: dict, with_file=True, edit_doc=None):
    from scripts.elevation import usgs_3dep
    mod = _tool()
    with tempfile.TemporaryDirectory() as t:
        proj = Path(t)
        (proj / "data").mkdir()
        for f in ("centerline.local.json", "connectors.local.json"):
            shutil.copy(TRACK / "data" / f, proj / "data" / f)
        if with_file:
            doc = json.loads((TRACK / "data" / "expansion.north.json").read_text(encoding="utf-8"))
            if edit_doc:
                edit_doc(doc)
            (proj / "data" / "expansion.north.json").write_text(json.dumps(doc), encoding="utf-8")
        cfg = json.loads((TRACK / "track.config.json").read_text(encoding="utf-8"))
        cfg["route"]["route_connectors"] = rc
        (proj / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
        saved = usgs_3dep.sample_points
        usgs_3dep.sample_points = lambda pts, **k: [100.0 + 1000.0 * (lat - 32.79) + 10.0 * (lon + 117.05)
                                                    for lon, lat in pts]
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                mod.build(proj)
        finally:
            usgs_3dep.sample_points = saved
        return json.loads((proj / "data" / "connectors.local.json").read_text(encoding="utf-8")), out.getvalue()


HELD = {"routes": ["medium", "short", "north"], "keep": ["del_cerro_blvd"],
        "authored_routes": {"north": "data/expansion.north.json"}}


def test_the_take_appends_the_two_weld_stubs_as_authored_and_changes_nothing_else():
    held, _ = _run(HELD)
    take, log = _run(dict(HELD, authored_take={"north": ["W1", "W5"]}))
    hc, tc = held["connectors"], take["connectors"]
    assert tc[:len(hc)] == hc, "the take changed the existing connectors"
    new = tc[len(hc):]
    assert [c["name"] for c in new] == ["north_J1_waring", "north_J5_jackson_north"]
    doc = json.loads((TRACK / "data" / "expansion.north.json").read_text(encoding="utf-8"))
    for c, w in zip(new, doc["welds"]):
        a = w["connector"]
        assert c["widths_m"] == a["widths_m"]
        assert [(p[0], p[2]) for p in c["points_xyz_m"]] == [(p[0], p[2]) for p in a["points_xyz_m"]]
        ys = [p[1] for p in c["points_xyz_m"]]
        assert max(abs(y1 - y0) for y0, y1 in zip(ys, ys[1:])) <= 0.11 * 3.0 + 1e-6     # the 11 % cap, 3 m step
    assert "W1 taken from expansion.north.json" in log and "HELD" not in log


def _refused(**kw) -> str:
    try:
        _run(**kw)
    except SystemExit as e:
        return str(e)
    raise AssertionError("route_connectors accepted it")


def test_a_take_of_an_unknown_weld_a_foreign_frame_or_a_missing_file_stops():
    assert "W9" in _refused(rc=dict(HELD, authored_take={"north": ["W9"]}))

    def shift(doc):
        doc["frame"]["origin"]["lon"] += 1e-4
    assert "another frame" in _refused(rc=dict(HELD, authored_take={"north": ["W1"]}), edit_doc=shift)
    assert "not in the project" in _refused(rc=dict(HELD, authored_take={"north": ["W1"]}), with_file=False)
