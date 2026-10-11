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
