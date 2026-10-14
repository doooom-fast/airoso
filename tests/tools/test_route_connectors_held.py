"""tools/route_connectors.py — a route named in route_connectors.authored_routes is HELD (ledger 0054 P0 step 5).

The north loop's roads are 17-33 m divided boulevards; the connector tool's constant 10 m pieces are not used for them
(EXPANSION-PLAN A3). With `north` in route_connectors.routes AND in authored_routes, the tool must write exactly the
bytes it writes without `north` — on the track's own data, 3DEP stubbed by a deterministic function of the point (no
network). With the key absent, nothing changes either way.
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
    spec = importlib.util.spec_from_file_location("_tool_route_connectors", ROOT / "tools" / "route_connectors.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(cfg_route_connectors: dict) -> tuple[bytes, str]:
    from scripts.elevation import usgs_3dep
    mod = _tool()
    with tempfile.TemporaryDirectory() as t:
        proj = Path(t)
        (proj / "data").mkdir()
        for f in ("centerline.local.json", "connectors.local.json"):
            shutil.copy(TRACK / "data" / f, proj / "data" / f)
        cfg = json.loads((TRACK / "track.config.json").read_text(encoding="utf-8"))
        cfg["route"]["route_connectors"] = cfg_route_connectors
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
        return (proj / "data" / "connectors.local.json").read_bytes(), out.getvalue()


def test_a_held_authored_route_writes_exactly_what_its_absence_writes():
    base = {"routes": ["medium", "short"], "keep": ["del_cerro_blvd"]}
    held = {"routes": ["medium", "short", "north"], "keep": ["del_cerro_blvd"],
            "authored_routes": {"north": "data/expansion.north.json"}}
    a, log_a = _run(base)
    b, log_b = _run(held)
    assert a == b, "holding the authored north route changed connectors.local.json"
    assert "north: HELD" in log_b and "not written yet" in log_b and "HELD" not in log_a
    names = [c["name"] for c in json.loads(b)["connectors"]]
    assert not any(n.startswith("north") for n in names), names


def test_the_committed_config_holds_north():
    rc = json.loads((TRACK / "track.config.json").read_text(encoding="utf-8"))["route"]["route_connectors"]
    assert rc["routes"] == ["medium", "short", "north"]
    assert rc["authored_routes"] == {"north": "data/expansion.north.json"}
