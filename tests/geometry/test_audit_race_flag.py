"""audit_mesh check D under ``--race`` (ledger 0047): a 1WALL on its DECLARED barrier band is exempt
only when the race flag is given; a strip off its band counts either way. Plain ``test_*``.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.geometry.test_drive_test import _grass_plane, _write_obj
from tests.geometry.test_drive_test_layouts import _box, BH, EDGE_C, W, N_M, STEP

from scripts.geometry import ribbon
from scripts.geometry.audit_mesh import audit


def _project(*, on_band=True, off_band=False) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False}))
    cl = [(0.0, 0.0, float(z)) for z in range(0, N_M + 1, STEP)]
    n = len(cl)
    widths = [W] * n
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": widths,
         "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}))
    groups = [("1ROAD_main", ribbon.road_ribbon(cl, widths)), ("1GRASS", _grass_plane())]
    if on_band:
        groups.append(("1WALL_race_c0_0", _box(0.0, 50.0, 150.0)))
    if off_band:
        groups.append(("1WALL_race_c0_1", _box(3.0, 80.0, 90.0)))    # 3 m off the centreline: no band there
    _write_obj(d / "data" / "track.obj", groups)
    _write_obj(d / "data" / "track.race.obj", groups)
    cw = [2 * BH if 10 <= i <= 30 else 0.0 for i in range(n)]
    (d / "data" / "barrier_bands.json").write_text(json.dumps({
        "centre_w_by_vertex": cw, "edge_strip_by_vertex": [1] * n, "edge_inset_by_vertex": [0.82] * n,
        "params": {"barrier_half_m": BH, "edge_centre_from_lip_m": -0.485}, "closed_mouths": []}))
    return d


def test_d_counts_the_strip_without_race_and_exempts_it_with_race():
    d = _project()
    r = audit(d)
    assert r["D_wall_on_road"] > 0 and r["race"] is False and r["obj"] == "track.obj"
    assert (d / "data" / "audit.json").exists()
    r2 = audit(d, race=True, obj="track.race.obj", out="audit.race.json")
    assert r2["D_wall_on_road"] == 0 and r2["race"] is True and r2["obj"] == "track.race.obj"
    assert (d / "data" / "audit.race.json").exists()
    assert json.loads((d / "data" / "audit.json").read_text())["D_wall_on_road"] == r["D_wall_on_road"]


def test_d_counts_a_strip_off_its_band_either_way():
    d = _project(on_band=False, off_band=True)
    assert audit(d)["D_wall_on_road"] > 0
    assert audit(d, race=True, obj="track.race.obj", out="audit.race.json")["D_wall_on_road"] > 0


# --- per-layout (ledger 0049): D exempt on THAT layout's bands only; W = a race strip through another wall --

def _layout_project(*, guard_through_strip=False) -> Path:
    from tests.geometry.test_drive_test_layouts import _corridor_bands
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False}))
    cl = [(0.0, 0.0, float(z)) for z in range(0, N_M + 1, STEP)]
    n = len(cl)
    widths = [W] * n
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": widths, "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}))
    base = [("1ROAD_main", ribbon.road_ribbon(cl, widths)), ("1GRASS", _grass_plane()),
            ("1WALL_race_edge_L_s0_0", _box(+EDGE_C, 0.0, float(N_M))),
            ("1WALL_race_edge_R_s0_0", _box(-EDGE_C, 0.0, float(N_M)))]
    cw = base + [("1WALL_race_close_cw_s0_0", _box(-1.0, 0.0, float(N_M)))]       # forward-left 1 m = x -1
    if guard_through_strip:
        cw.append(("1WALL_guard", _box(-EDGE_C, 60.0, 70.0, half=0.1, h=0.9, y0=0.3)))   # a rail inside the strip
    _write_obj(d / "data" / "track.race_cw.obj", cw)
    _write_obj(d / "data" / "track.race_acw.obj", cw)        # the WRONG closure kn5 loaded for race_acw
    (d / "data" / "barrier_bands.json").write_text(json.dumps(_corridor_bands(n)))
    return d


def test_d_exempts_only_the_layouts_own_closure():
    d = _layout_project()
    r = audit(d, layout="race_cw", obj="track.race_cw.obj", out="audit.race_cw.json")
    assert r["race"] is True and r["layout"] == "race_cw" and r["D_wall_on_road"] == 0, r["D_wall_on_road"]
    assert r["W_race_wall_clash"] == 0
    assert (d / "data" / "audit.race_cw.json").exists()
    r2 = audit(d, layout="race_acw", obj="track.race_acw.obj", out="audit.race_acw.json")
    assert r2["D_wall_on_road"] > 0                          # race_cw's closure is a wall on race_acw's road


def test_w_counts_a_race_strip_through_another_wall_and_gates_per_layout():
    from scripts.geometry.audit_mesh import main as audit_main
    d = _layout_project(guard_through_strip=True)
    r = audit(d, layout="race_cw", obj="track.race_cw.obj", out="audit.race_cw.json")
    assert r["W_race_wall_clash"] > 0 and r["samples"]["race_wall_clash"]
    assert audit_main([str(d), "--layout", "race_cw"]) == 1   # defaults: track.race_cw.obj -> audit.race_cw.json
    assert json.loads((d / "data" / "audit.race_cw.json").read_text())["W_race_wall_clash"] > 0
    assert audit_main([str(_layout_project()), "--layout", "race_cw"]) == 0
