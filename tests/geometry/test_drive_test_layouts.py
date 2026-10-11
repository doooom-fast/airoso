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
    removes a stale per-layout file;
  * (2026-10-11) a race road FLARING 17 -> 24 m with every strip exactly on its declaration has no
    obstruction (the lane is the lerped declared width at the station, not the vertex ahead's) while a
    strip ring shoved 1 m into the lane still fails;
  * (2026-10-11) a strip TRIMMED to its corner at a fold (barrier_bands edge_corners) is probed on the
    declared in -> X -> out polyline in both directions — present = 0 missing, cut away = missing — and
    the untrimmed knot standing in the exit carriageway is an obstruction.
Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.geometry.test_drive_test import _grass_plane, _write_obj

import math
import sys

from scripts.geometry import ribbon
from scripts.geometry.drive_test import run as drive_run, main as drive_main

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import race_furniture as rf  # noqa: E402

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


# --- the lane at the station on a flare (2026-10-11) -----------------------------------------------

def _poly_box(centres, half=BH, h=1.2, y0=0.0) -> dict:
    """a closed box strip through the (x, z) ring centres: square cross-sections on the local polyline normal"""
    v = []
    n = len(centres)
    for i, (x, z) in enumerate(centres):
        a, b = centres[max(0, i - 1)], centres[min(n - 1, i + 1)]
        tx, tz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, tz) or 1.0
        lx, lz = -tz / L, tx / L
        v += [(x + lx * half, y0, z + lz * half), (x - lx * half, y0, z - lz * half),
              (x - lx * half, y0 + h, z - lz * half), (x + lx * half, y0 + h, z + lz * half)]
    tris = []
    for r in range(n - 1):
        a = 4 * r
        tris += [(a + 3, a + 2, a + 6), (a + 3, a + 6, a + 7), (a + 1, a + 2, a + 6), (a + 1, a + 6, a + 5),
                 (a + 0, a + 3, a + 7), (a + 0, a + 7, a + 4)]
    last = 4 * (n - 1)
    tris += [(0, 1, 2), (0, 2, 3), (last, last + 1, last + 2), (last, last + 2, last + 3)]
    return {"vertices": v, "tris": tris, "uvs": [(0.0, 0.0)] * len(v)}


def _flare_project(shove: float = 0.0) -> Path:
    """200 m straight, 17 m wide to z = 80 then flaring 2.33 m per 5 m vertex to 24 m at z = 95 (an SD mouth
    flare), a centre chain the whole way (so the lane is one carriageway and its scan disc is centred
    mid-lane) and kerb-line strips EXACTLY on the declaration: centre at w/2 - 0.485, lerped between vertices
    (rings every 1 m). shove: one right-hand ring (z = 86) moved that far INTO the lane."""
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False, "layouts": _layouts()}))
    cl = [(0.0, 0.0, float(z)) for z in range(0, N_M + 1, STEP)]
    n = len(cl)
    widths = [17.0 if z <= 80 else (24.0 if z >= 95 else 17.0 + 7.0 * (z - 80) / 15.0) for z in range(0, N_M + 1, STEP)]
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": widths, "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}))
    road = ribbon.road_ribbon(cl, widths)
    base = [("1ROAD_main", road), ("1GRASS", _grass_plane())]
    _write_obj(d / "data" / "track.obj", base)

    def w_at(z):
        k = min(n - 2, int(z // STEP))
        u = (z - STEP * k) / STEP
        return widths[k] + (widths[k + 1] - widths[k]) * u
    zs = [float(z) for z in range(0, N_M + 1)]
    left = [(-(w_at(z) / 2 - 0.485), z) for z in zs]          # left of +z travel is -x (normal (-tz, tx) = (-1, 0))
    right = [(+(w_at(z) / 2 - 0.485) - (shove if z == 86.0 else 0.0), z) for z in zs]
    race = list(base) + [("1WALL_race_c0_0", _box(0.0, 0.0, float(N_M), ring_m=1.0)),
                         ("1WALL_race_eL_s0_0", _poly_box(left)), ("1WALL_race_eR_s0_0", _poly_box(right))]
    _write_obj(d / "data" / "track.race.obj", race)
    (d / "data" / "barrier_bands.json").write_text(json.dumps({
        "centre_w_by_vertex": [2 * BH] * n, "edge_strip_by_vertex": [1] * n, "edge_inset_by_vertex": [0.82] * n,
        "params": {"barrier_half_m": BH, "edge_centre_from_lip_m": -0.485, "edge_mode": "road"}, "closed_mouths": []}))
    return d


def test_a_flare_with_every_strip_on_its_declaration_is_not_an_obstruction():
    """the lane a station drives is the declared width LERPED at the station: widths[i] (the vertex ahead)
    made the lane up to 1.2 m too wide on a 2.33 m-per-vertex flare and the disc reached the previous ring's
    face — 341 of SD's 395 race obstruction stations. A ring standing 1 m in the lane still fails."""
    d = _flare_project()
    for lid in ("race_cw", "race_acw"):
        r = drive_run(d, lid)
        assert r["obstruction_stations"] == 0, (lid, r["obstruction_by_mesh"], r["worst"]["obstructions"][:4])
        assert r["barrier_missing"] == 0, (lid, r["barrier_missing_runs"])
    d = _flare_project(shove=1.0)
    r = drive_run(d, "race_cw")                                 # the right-hand lane of +z travel
    assert r["obstruction_stations"] > 0 and "1WALL_race_eR_s0_0" in r["obstruction_by_mesh"], r["obstruction_by_mesh"]


# --- trimmed corners (2026-10-11) -------------------------------------------------------------------

def _right_hander(R=8.0, leg=60.0, step=3.0):
    """a 90 deg right-hander (x = E, z = N): +x along z = 0 to (0, 0), a radius-R arc about (0, -R) to (R, -R),
    then -z along x = R"""
    pts = [(x, 0.0, 0.0) for x in [-leg + step * i for i in range(int(leg / step))]]
    n_arc = max(2, int(math.ceil(R * math.pi / 2 / step)))
    for i in range(n_arc + 1):
        a = math.pi / 2 - (math.pi / 2) * i / n_arc
        pts.append((R * math.cos(a), 0.0, -R + R * math.sin(a)))
    pts += [(R, 0.0, -R - step * (i + 1)) for i in range(int(leg / step))]
    return pts


def _tris(faces):
    out = []
    for f in faces:
        out += [(f[0], f[k], f[k + 1]) for k in range(1, len(f) - 1)]
    return out


def _corner_project(*, trim=True, declare=True, cut_corner=False) -> tuple[Path, dict]:
    """the right-hander, 24 m wide (strip centre 11.515 m out: the inside lip folds, R 8 m) with a centre chain,
    both kerb-line strips planned by tools/race_furniture (vertex rings, trim, densify, strip_mesh) exactly as
    the author sweeps them; bands carry the trim's corner as `edge_corners` when `declare`"""
    W2 = 24.0
    pts = _right_hander()
    n = len(pts)
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False, "layouts": _layouts()}))
    widths = [W2] * n
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in pts], "widths_m": widths, "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}))
    road = ribbon.road_ribbon(pts, widths)
    gx = [-80.0 + 10.0 * i for i in range(17)]
    gz = [-90.0 + 10.0 * j for j in range(13)]
    gv = [(x, -0.02, z) for z in gz for x in gx]
    gt = [t for j in range(len(gz) - 1) for i in range(len(gx) - 1)
          for t in ((j * 17 + i, j * 17 + i + 1, (j + 1) * 17 + i + 1), (j * 17 + i, (j + 1) * 17 + i + 1, (j + 1) * 17 + i))]
    base = [("1ROAD_main", road), ("1GRASS", {"vertices": gv, "tris": gt, "uvs": [(0.0, 0.0)] * len(gv)})]
    _write_obj(d / "data" / "track.obj", base)
    st = rf.stations(pts)
    lat = W2 / 2 - 0.485
    # a centre chain the whole way (SD's three chained corners): the lane is one carriageway, its scan disc
    # mid-lane — without a divider the disc stays within 6.3 m of the centreline (today's cap)
    dense = []
    for a, b in zip(pts, pts[1:]):
        dense += [(a[0] + (b[0] - a[0]) * q / 3, a[2] + (b[2] - a[2]) * q / 3) for q in range(3)]
    race = list(base) + [("1WALL_race_kbar_t_0_0", _poly_box(dense[3:-2]))]
    corners = []
    for side, sgn in (("L", 1.0), ("R", -1.0)):
        plan = rf._plan_run(pts + [pts[0]], widths + [W2], n, st, list(range(1, n - 1)), lambda k, g=sgn: g * lat,
                            "free", "free", rf.BARRIER_H, "edge", "t", side, (1, n - 2))
        rings = plan["rings"]
        if trim:
            rings, _, cs = rf.trim_folded_rings(rings)
            corners += [dict(c, side=side) for c in cs]
        rings, _ = rf.densify_rings(rings, n)
        if cut_corner and side == "R":
            X = corners[0]["xz"]
            rings = [r for r in rings if math.dist(rf._strip_xz(r), X) > 6.0]
        for r in rings:
            r["y"] = -rf.BURY_M
        pieces, cur = [], [rings[0]]
        for a, b in zip(rings, rings[1:]):                        # a cut-away corner leaves two pieces
            if math.dist(rf._strip_xz(a), rf._strip_xz(b)) > 6.0:
                pieces.append(cur)
                cur = []
            cur.append(b)
        pieces.append(cur)
        for pi, pr in enumerate(pieces):
            v, f, _ = rf.strip_mesh(pr, True, True)
            race.append((f"1WALL_race_edge_{side}_t_{pi}", {"vertices": v, "tris": _tris(f), "uvs": [(0.0, 0.0)] * len(v)}))
    _write_obj(d / "data" / "track.race.obj", race)
    ends = [0] + [1] * (n - 2) + [0]                              # the strips are planned on v1..v(n-2)
    bands = {"centre_w_by_vertex": [2 * BH * e for e in ends], "edge_strip_by_vertex": ends, "edge_inset_by_vertex": [0.82 * e for e in ends],
             "params": {"barrier_half_m": BH, "edge_centre_from_lip_m": -0.485, "edge_mode": "road"}, "closed_mouths": []}
    if declare:
        bands["edge_corners"] = corners
    (d / "data" / "barrier_bands.json").write_text(json.dumps(bands))
    return d, {"corners": corners}


def test_a_trimmed_corner_is_probed_on_its_declared_polyline_both_ways():
    d, info = _corner_project()
    assert len(info["corners"]) == 1 and info["corners"][0]["side"] == "R"
    for lid in ("race_cw", "race_acw"):          # reverse: the corner is on the walk's LEFT, out_vertex first
        r = drive_run(d, lid)
        assert r["barrier_missing"] == 0, (lid, r["barrier_missing_runs"])
        assert r["obstruction_stations"] == 0, (lid, r["obstruction_by_mesh"], r["worst"]["obstructions"][:4])
    # the same strip with its corner cut away: the declared polyline is probed and found empty
    d, _ = _corner_project(cut_corner=True)
    for lid, kind in (("race_cw", "edge_R"), ("race_acw", "edge_L")):
        r = drive_run(d, lid)
        assert r["barrier_missing"] > 0 and any(k == kind for _a, _b, k in r["barrier_missing_runs"]), (lid, r["barrier_missing_runs"])
    # the built corner WITHOUT its declaration: the probes stand on the folded offset curve and find nothing
    # there (the rehearsal's 52 fold stations) — the declaration is what puts the probe on the corner
    d, _ = _corner_project(declare=False)
    r = drive_run(d, "race_cw")
    assert r["barrier_missing"] > 0 and r["obstruction_stations"] == 0, (r["barrier_missing_runs"], r["obstruction_by_mesh"])
    # the untrimmed knot (the one-sided drop's class) stands in the exit carriageway: an obstruction for the
    # layout that drives the inside of the turn
    d, _ = _corner_project(trim=False, declare=False)
    r = drive_run(d, "race_cw")
    assert r["obstruction_stations"] > 0, r["obstruction_by_mesh"]


# --- per-layout corridors (ledger 0049): each race layout on its own gate OBJ, lane from the declaration ----

CLOSE_Y = 1.0     # race_cw's closure centre 1 m LEFT of the centreline (x = -1 here); race_acw's the mirror


def _corridor_bands(n):
    face = W / 2 - 0.82

    def cor(sgn):
        y = [sgn * CLOSE_Y] * n
        lane = [[-face, sgn * CLOSE_Y - BH] if sgn > 0 else [sgn * CLOSE_Y + BH, face]] * n
        return {"token": "cw" if sgn > 0 else "acw", "closure_y_by_vertex": y, "lane_by_vertex": lane,
                "zone_by_vertex": ["closure"] * n}
    return {"version": 2, "centre_w_by_vertex": [0.0] * n, "edge_strip_by_vertex": [1] * n,
            "edge_inset_by_vertex": [0.82] * n,
            "params": {"barrier_half_m": BH, "edge_centre_from_lip_m": -0.485, "edge_mode": "road"},
            "closed_mouths": [], "edge_corners": [],
            "corridors": {"race_cw": cor(1.0), "race_acw": cor(-1.0)}}


def _corridor_project(*, closure_built=True, stray_x=None) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False, "layouts": _layouts()}))
    cl = [(0.0, 0.0, float(z)) for z in range(0, N_M + 1, STEP)]
    n = len(cl)
    widths = [W] * n
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": widths, "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}))
    road = ribbon.road_ribbon(cl, widths)
    base = [("1ROAD_main", road), ("1GRASS", _grass_plane())]
    _write_obj(d / "data" / "track.obj", base)
    for lid, x in (("race_cw", -CLOSE_Y), ("race_acw", +CLOSE_Y)):       # forward-left = -x
        objs = list(base) + [("1WALL_race_edge_L_s0_0", _box(+EDGE_C, 0.0, float(N_M))),
                             ("1WALL_race_edge_R_s0_0", _box(-EDGE_C, 0.0, float(N_M)))]
        if closure_built:
            objs.append((f"1WALL_race_close_{'cw' if lid == 'race_cw' else 'acw'}_s0_0", _box(x, 0.0, float(N_M))))
        if stray_x is not None and lid == "race_cw":
            objs.append(("BARRIER_stray", _box(stray_x, 80.0, 90.0)))
        _write_obj(d / "data" / f"track.{lid}.obj", objs)
    (d / "data" / "barrier_bands.json").write_text(json.dumps(_corridor_bands(n)))
    return d


def test_each_race_layout_drives_its_declared_corridor_on_its_own_gate_obj():
    d = _corridor_project()
    for lid in ("race_cw", "race_acw"):
        r = drive_run(d, lid)
        assert r["obj"] == f"track.{lid}.obj" and r["lane"] == f"barrier_bands.json corridors.{lid}"
        assert r["obstruction_stations"] == 0, (lid, r["obstruction_by_mesh"])
        assert r["barrier_missing"] == 0, (lid, r["barrier_missing_runs"])
        assert r["fail"] is False, lid
    rs = drive_run(d, "street")                               # the street layout is unchanged: track.obj, no bands
    assert rs["obj"] == "track.obj" and rs["barrier_stations"] == 0 and rs["fail"] is False


def test_a_declared_closure_that_was_not_built_is_barrier_missing():
    d = _corridor_project(closure_built=False)
    r = drive_run(d, "race_cw")
    assert r["barrier_missing"] > 0 and r["fail"] is True
    assert {k for _a, _b, k in r["barrier_missing_runs"]} == {"closure"}, r["barrier_missing_runs"]


def test_the_lane_is_the_corridor_not_the_half_road():
    # a stray wall in the pocket behind race_cw's closure (forward-left 3 m = x -3) is outside its lane ...
    r = drive_run(_corridor_project(stray_x=-3.0), "race_cw")
    assert r["obstruction_stations"] == 0 and r["fail"] is False, r["obstruction_by_mesh"]
    # ... one 0.5 m right of the centreline (x +0.5) is INSIDE it: the corridor reaches past the centreline
    r2 = drive_run(_corridor_project(stray_x=0.5), "race_cw")
    assert r2["obstruction_stations"] > 0 and any(k.startswith("BARRIER_stray") for k in r2["obstruction_by_mesh"])
