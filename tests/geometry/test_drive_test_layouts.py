"""Per-layout drive test (ledger 0047): scripts/geometry/drive_test.run(project, layout).

Synthetic 200 m straight (12 m wide) with the race furniture the bands declare: a centre chain
strip on the centreline (v10..v30) and kerb-line strips on both curb faces. Pins:

  * race_cw (forward) and race_acw (reverse) PASS on the race OBJ: obstruction 0, barrier_missing 0
    — each sweeps its own carriageway between the chain face and its kerb-line strip;
  * the same bands with the chain REMOVED → barrier_missing > 0 and FAIL (a declared-but-unbuilt
    chain fails; the band exemptions are not a bypass);
  * an extra wall in the forward-LEFT lane → race_cw (right lane) passes, race_acw (whose right
    lane that is) fails with an obstruction;
  * the street layout runs on track.obj (no furniture) without the bands and is unchanged;
  * the CLI writes data/drive_test.<id>.json per layout + the data/drive_test.json summary and
    removes a stale per-layout file.
Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.geometry.test_drive_test import _grass_plane, _write_obj

from scripts.geometry import ribbon
from scripts.geometry.drive_test import run as drive_run, main as drive_main

W = 12.0
N_M = 200
STEP = 5
BH = 0.335                      # chain half-width
EDGE_C = W / 2 - 0.485          # kerb-line strip centre (road mode)


def _box(xc: float, z0: float, z1: float, half: float = BH, h: float = 1.2, y0: float = 0.0,
         ring_m: float = 5.0) -> dict:
    """a closed box strip along z, one 4-vertex ring every ``ring_m`` (the authored strips carry a
    ring per centreline vertex; drive_test culls any triangle longer than 60 m as a terrain skirt,
    so a single 200 m quad would be invisible to it): top face + two long sides + end caps"""
    zs = []
    z = z0
    while z < z1 - 1e-9:
        zs.append(z); z += ring_m
    zs.append(z1)
    v = []
    for z in zs:
        v += [(xc - half, y0, z), (xc + half, y0, z), (xc + half, y0 + h, z), (xc - half, y0 + h, z)]
    tris = []
    for r in range(len(zs) - 1):
        a = 4 * r
        tris += [(a + 3, a + 2, a + 6), (a + 3, a + 6, a + 7),       # top
                 (a + 1, a + 2, a + 6), (a + 1, a + 6, a + 5),       # +x side
                 (a + 0, a + 3, a + 7), (a + 0, a + 7, a + 4)]       # -x side
    last = 4 * (len(zs) - 1)
    tris += [(0, 1, 2), (0, 2, 3), (last, last + 1, last + 2), (last, last + 2, last + 3)]   # end caps
    return {"vertices": v, "tris": tris, "uvs": [(0.0, 0.0)] * len(v)}


def _layouts():
    return [
        {"id": "street", "kind": "street", "direction": "forward", "race_furniture": False},
        {"id": "race_cw", "kind": "race", "direction": "forward", "race_furniture": True},
        {"id": "race_acw", "kind": "race", "direction": "reverse", "race_furniture": True},
    ]


def _project(*, chain=True, edges=True, extra_left_wall=False, bands=True) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False, "layouts": _layouts()}))
    cl = [(0.0, 0.0, float(z)) for z in range(0, N_M + 1, STEP)]
    n = len(cl)
    widths = [W] * n
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": widths,
         "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}))
    road = ribbon.road_ribbon(cl, widths)
    base = [("1ROAD_main", road), ("1GRASS", _grass_plane())]
    _write_obj(d / "data" / "track.obj", base)                       # the street layout's OBJ: no furniture
    race = list(base)
    if chain:
        race.append(("1WALL_race_c0_0", _box(0.0, 50.0, 150.0)))
    if edges:
        race.append(("1WALL_race_eL_s0_0", _box(+EDGE_C, 0.0, float(N_M))))
        race.append(("1WALL_race_eR_s0_0", _box(-EDGE_C, 0.0, float(N_M))))
    if extra_left_wall:
        # forward-left = -x here (travel +z: right of travel is +x, the normal (-tz, tx) = (-1, 0)
        # puts positive (left) offsets at -x)
        race.append(("BARRIER_stray", _box(-3.0, 80.0, 90.0)))
    _write_obj(d / "data" / "track.race.obj", race)
    if bands:
        cw = [2 * BH if 10 <= i <= 30 else 0.0 for i in range(n)]
        (d / "data" / "barrier_bands.json").write_text(json.dumps({
            "centre_w_by_vertex": cw,
            "edge_strip_by_vertex": [1 if edges else 0] * n,
            "edge_inset_by_vertex": [0.82 if edges else 0.0] * n,
            "params": {"barrier_half_m": BH, "edge_centre_from_lip_m": -0.485, "edge_mode": "road"},
            "closed_mouths": []}))
    return d


def test_both_race_layouts_pass_between_chain_and_kerb_line_strips():
    d = _project()
    for lid in ("race_cw", "race_acw"):
        r = drive_run(d, lid)
        assert r["layout"] == lid and r["obj"] == "track.race.obj"
        assert r["obstruction_stations"] == 0, (lid, r["obstruction_by_mesh"])
        assert r["barrier_stations"] > 0 and r["barrier_missing"] == 0, (lid, r["barrier_missing_runs"])
        assert r["soft_top_in_lane"] == 0 and r["floating_furniture"] == 0
        assert r["fail"] is False, lid
        assert (d / "data" / f"drive_test.{lid}.json").exists()
    assert json.loads((d / "data" / "drive_test.race_acw.json").read_text())["direction"] == "reverse"


def test_declared_chain_that_was_not_built_fails_barrier_missing():
    d = _project(chain=False)
    r = drive_run(d, "race_cw")
    assert r["obstruction_stations"] == 0
    assert r["barrier_missing"] > 0
    assert any(k == "centre" for _a, _b, k in r["barrier_missing_runs"])
    assert r["fail"] is True


def test_wall_in_the_other_carriageway_fails_only_the_layout_that_drives_it():
    d = _project(extra_left_wall=True)
    cw = drive_run(d, "race_cw")
    assert cw["obstruction_stations"] == 0 and cw["fail"] is False, cw["obstruction_by_mesh"]
    acw = drive_run(d, "race_acw")
    assert acw["obstruction_stations"] > 0
    assert any(k.startswith("BARRIER_stray") for k in acw["obstruction_by_mesh"]), acw["obstruction_by_mesh"]
    assert acw["fail"] is True


def test_street_layout_drives_the_road_obj_without_bands():
    d = _project()
    r = drive_run(d, "street")
    assert r["obj"] == "track.obj" and r["race_furniture"] is False
    assert r["barrier_stations"] == 0 and r["barrier_missing"] == 0
    assert r["obstruction_stations"] == 0 and r["fail"] is False
    # the same geometry judged as the full-width street: the centre sweep sees the chain if it is
    # fed the race OBJ (the street layout must never load it)
    r2 = drive_run(d, "street", obj="track.race.obj")
    assert r2["obstruction_stations"] > 0


def test_cli_runs_the_selected_layouts_and_writes_the_summary():
    d = _project()
    (d / "data" / "drive_test.bogus.json").write_text(json.dumps({"layout": "bogus", "fail": True}))   # a retired id's report
    (d / "data" / "drive_test.locked.json").write_text("{}")                                          # a foreign file
    rc = drive_main([str(d), "--layout", "race_cw", "--layout", "race_acw"])
    assert rc == 0
    summ = json.loads((d / "data" / "drive_test.json").read_text())
    assert summ["multi_layout"] is True and summ["fail"] is False
    assert set(summ["layouts"]) == {"street", "race_cw", "race_acw"}
    assert summ["layouts"]["race_cw"]["fail"] is False and summ["layouts"]["street"]["fail"] is None
    assert summ["not_run"] == ["street"] and summ["ran"] == ["race_cw", "race_acw"]
    assert not (d / "data" / "drive_test.bogus.json").exists()
    assert (d / "data" / "drive_test.locked.json").exists()
    rc2 = drive_main([str(d)])                       # no --layout: every declared layout
    assert rc2 == 0
    summ2 = json.loads((d / "data" / "drive_test.json").read_text())
    assert summ2["not_run"] == [] and all(r["fail"] is False for r in summ2["layouts"].values())
