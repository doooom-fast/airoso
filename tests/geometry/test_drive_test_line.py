"""drive_test --line (ledger 0054 P3 step 7): an open line driven on the street OBJ, its own report file, the EXPANSION-
PLAN V6 verdict, a lap run unchanged; the furniture-seating check reads every wall on its own ground (a wall far off the
swept line was "floating 99" with no surface loaded under it)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.geometry import ribbon
from scripts.geometry import drive_test as dt

from tests.geometry.test_drive_test import _grass_plane, _write_obj, W, N_M


def _proj(far_wall=False):
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False}))
    cl = [(0.0, 0.0, float(z)) for z in range(0, N_M + 1, 5)]
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": [W] * len(cl), "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}))
    # a second road 300 m east, which only the line drives
    cl2 = [(300.0, 0.0, float(z)) for z in range(0, N_M + 1, 5)]
    groups = [("1ROAD_main", ribbon.road_ribbon(cl, [W] * len(cl))),
              ("1ROAD_north", ribbon.road_ribbon(cl2, [W] * len(cl2))),
              ("1GRASS", _grass_plane()), ("1GRASS_b", {**_grass_plane(), "vertices": [(x + 300.0, y, z) for x, y, z in _grass_plane()["vertices"]]})]
    if far_wall:
        wall = {"vertices": [(306.0, 0.0, 100.0), (306.0, 0.0, 104.0), (306.0, 1.0, 104.0), (306.0, 1.0, 100.0)],
                "tris": [(0, 1, 2), (0, 2, 3)], "uvs": [(0.0, 0.0)] * 4}
        groups.append(("1WALL_STUB_x", wall))
    _write_obj(d / "data" / "track.obj", groups)
    lines = {"lines": {"fwd": {"points_xyz_m": [list(p) for p in cl2], "widths_m": [W] * len(cl2)},
                       "rev": {"points_xyz_m": [list(p) for p in cl2[::-1]], "widths_m": [W] * len(cl2)}}}
    (d / "data" / "drive_lines.expansion.json").write_text(json.dumps(lines))
    return d


def test_a_line_is_driven_on_its_own_road_and_judged_by_v6():
    d = _proj()
    rc = dt.run_lines(d, "expansion")
    out = json.loads((d / "data" / "drive_test.expansion.json").read_text())
    assert rc == 0 and out["fail"] is False, out
    for k in ("fwd", "rev"):
        r = out["lines"][k]
        assert r["lap_m"] == 200.0 and r["severe_steps"] == 0 and r["obstruction_stations"] == 0
        assert (d / "data" / f"drive_test.line.expansion_{k}.json").exists()
        assert all(r["v6"].values())


def test_a_wall_far_off_the_swept_line_is_judged_on_its_own_ground():
    """the mainline lap never reaches x = 306: before P3 the wall read 'floating 99' there (no ground loaded under it);
    now its own ground is loaded and it stands on it"""
    d = _proj(far_wall=True)
    r = dt.run(d)
    assert r["floating_furniture"] == 0, r["floating_furniture"]


def test_main_with_line_flag_runs_the_lines_only():
    d = _proj()
    assert dt.main([str(d), "--line", "expansion"]) == 0
    assert not (d / "data" / "drive_test.json").exists()


def test_a_line_reports_where_its_bumps_stand_and_a_lap_run_does_not():
    """ledger 0054 step 2e: --line writes steps_at [s, lateral, step, x, z] for every bump it counts (the 0.20.2 rise in
    steps/km could not be placed); a lap run's report carries no such key (byte-identical)"""
    d = _proj()
    obj = d / "data" / "track.obj"
    txt = obj.read_text()
    n = sum(1 for ln in txt.splitlines() if ln.startswith("v "))
    h = 0.04                                         # a 4 cm plate across the line's road at z 100-102
    plate = [f"v {x} {h} {z}" for x, z in ((294.0, 100.0), (306.0, 100.0), (306.0, 102.0), (294.0, 102.0))]
    obj.write_text(txt + "o 1ROAD_plate\n" + "\n".join(plate) + f"\nf {n + 1} {n + 4} {n + 3}\nf {n + 1} {n + 3} {n + 2}\n")
    dt.run_lines(d, "expansion")
    r = json.loads((d / "data" / "drive_test.line.expansion_fwd.json").read_text())
    assert r["steps_at"], r.get("steps_per_km")
    assert all(abs(p[3] - 300.0) <= 6.0 and 99.0 <= p[4] <= 105.0 for p in r["steps_at"]), r["steps_at"][:4]
    assert "steps_at" not in dt.run(d)
