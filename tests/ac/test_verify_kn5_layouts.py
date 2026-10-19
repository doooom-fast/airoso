"""verify_kn5 on a multi-layout track (ledgers 0047 + 0049): spawn-free road kn5, one nodes-only spawn kn5
per layout facing its travel on the right side of the road (or, with a declared corridor, inside its lane),
AC_TIME_0 at the declared line with the sectors in driving order, the COMMON race-furniture kn5 carrying only
curb strips + kerbs, each race layout's closure kn5 carrying only its own closure, and (g) the models_<id>.ini
set listing exactly [road, common race, own closure, own spawns] with no other layout's closure.

The binary fixture is written here with the same layout verify_kn5._parse_full reads (header,
materials, class-1 nodes with a 4x4 row-major matrix whose third row is the local +Z, class-2
meshes). The synthetic line runs along +z in the kn5 frame; the real-data test derives the three
Lake Murray spawn sets with tools/layout_dummies.py, maps them to the kn5 frame the way the
Blender exporter does (position (x, y, -z); local +Z = (sin psi, cos psi) for rotation_euler.z =
psi) and pins that the two tools agree on heading, side, line and sectors. Plain ``test_*``.
"""

from __future__ import annotations

import json
import math
import shutil
import struct
import sys
import tempfile
from pathlib import Path

from scripts.ac.verify_kn5 import verify, _parse_full, _right_of

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
import sd_v0180  # noqa: E402  (the pinned v0.18.0 Lake Murray data, tests/fixtures/lake_murray_v0180)
sys.path.insert(0, str(ROOT / "tools"))
import layout_dummies as ld  # noqa: E402


# ---------------------------------------------------------------- a minimal kn5 writer
class _W:
    def __init__(self):
        self.b = bytearray(b"sc6969")

    def i32(self, v): self.b += struct.pack("<i", v)
    def u32(self, v): self.b += struct.pack("<I", v)
    def u16(self, v): self.b += struct.pack("<H", v)
    def f32(self, v): self.b += struct.pack("<f", v)
    def u8(self, v): self.b += struct.pack("<B", v)

    def s(self, t):
        e = t.encode("utf-8"); self.u32(len(e)); self.b += e


def _face_up(P, tri):
    a, b, c = P[tri[0]], P[tri[1]], P[tri[2]]
    ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
    return tri if ny >= 0 else (tri[0], tri[2], tri[1])


def write_kn5(path: Path, meshes, nodes, materials):
    """meshes: [(name, verts, tris, mat_index)]; nodes: [(name, (x, y, z), yaw_rad)] where the
    node's kn5 local +Z = (sin yaw, 0, cos yaw); materials: [name]."""
    w = _W()
    w.i32(5); w.i32(0)                       # version, textures
    w.u32(len(materials))
    for mn in materials:
        w.s(mn); w.s("ksPerPixel"); w.u8(0); w.u8(0); w.i32(0); w.u32(0); w.u32(0)
    w.i32(1); w.s("root"); w.u32(len(meshes) + len(nodes)); w.u8(1)
    for v in (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1):
        w.f32(float(v))
    for name, verts, tris, mi in meshes:
        w.i32(2); w.s(name); w.u32(0); w.u8(1)
        w.u8(1); w.u8(1); w.u8(0)
        w.u32(len(verts))
        for x, y, z in verts:
            for f in (x, y, z, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0):
                w.f32(float(f))
        w.u32(len(tris) * 3)
        for t in tris:
            for i in t:
                w.u16(i)
        w.u32(mi); w.u32(0); w.f32(0.0); w.f32(0.0)
        w.b += bytes(16); w.u8(1)
    for name, (x, y, z), yaw in nodes:
        s, c = math.sin(yaw), math.cos(yaw)
        w.i32(1); w.s(name); w.u32(0); w.u8(1)
        for v in (c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, x, y, z, 1):
            w.f32(float(v))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(w.b))


def _ribbon(pts, half, step=1):
    """1ROAD mesh along a polyline (kn5 frame): two verts per point, face-up quads"""
    V, T = [], []
    for i in range(0, len(pts), step):
        x, y, z = pts[i]
        a = pts[max(0, i - 1)]; b = pts[min(len(pts) - 1, i + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / L, tx / L
        V.append((x + nx * half, y, z + nz * half)); V.append((x - nx * half, y, z - nz * half))
    for k in range(0, len(V) - 2, 2):
        T.append(_face_up(V, (k, k + 1, k + 3)))
        T.append(_face_up(V, (k, k + 3, k + 2)))
    return V, T


_BOX = [(-0.3, 0.0, 10.0), (0.3, 0.0, 10.0), (0.3, 1.2, 10.0), (-0.3, 1.2, 10.0),
        (-0.3, 0.0, 20.0), (0.3, 0.0, 20.0), (0.3, 1.2, 20.0), (-0.3, 1.2, 20.0)]
_BTRIS = [(3, 2, 6), (3, 6, 7), (1, 2, 6), (1, 6, 5)]


def _race_meshes(ok_names=True, ok_mats=True, extra=()):
    """the COMMON race kn5: a curb strip + a kerb (+ `extra` mesh names, each a box)"""
    kerb = [(2.0, 0.0, 30.0), (3.0, 0.0, 30.0), (3.0, 0.05, 40.0), (2.0, 0.05, 40.0)]
    ktris = [_face_up(kerb, (0, 1, 2)), _face_up(kerb, (0, 2, 3))]
    names = ("1WALL_race_edge_L_t_0_0", "1KERB_race_40_out") if ok_names else ("1WALL_guard_0", "1KERB_race_40_out")
    mats = ["1WALL_race_edge_L_t_0_0_mat", "1KERB_race_40_out_mat"] if ok_mats else ["1WALL_race_mat", "1ROAD_main_mat"]
    ms = [(names[0], _BOX, _BTRIS, 0), (names[1], kerb, ktris, 1)]
    for n in extra:
        ms.append((n, _BOX, _BTRIS, 0))
    return ms, mats


def _closure_meshes(token, extra=()):
    """a layout's closure kn5: 1WALL_race_close_<token>_* boxes (+ `extra` names)"""
    names = [f"1WALL_race_close_{token}_t_10_0", f"1WALL_race_close_{token}_t_10_1"] + list(extra)
    return [(n, _BOX, _BTRIS, 0) for n in names], [f"{names[0]}_mat"]


# ---------------------------------------------------------------- the synthetic project
N_PTS = 81                      # z = 0..400 at 5 m, open line, kn5 frame


def _synthetic(*, spawn_in_main=False, drop_spawn_kn5=None, flip_heading=None, wrong_side=None,
               bad_sectors=None, race_kn5="ok", stray_spawn=False, closures="ok", lanes=None) -> Path:
    """closures: "ok" (t_closure_race_cw / _acw.kn5, own tokens), None (none written), "swap" (race_cw's file holds
    the acw closure), "kerb" (a kerb in race_cw's closure kn5), "no_token" (no closure_token declared);
    race_kn5 "closure_in_common" puts race_cw's closure into the common kn5 as well;
    lanes: {layout id: [lo, hi]} -> a barrier_bands.json corridor with that lane at every vertex (forward-left)"""
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir(); (d / "build").mkdir()
    pts = [[0.0, 0.0, 5.0 * i] for i in range(N_PTS)]
    layouts = [
        {"id": "street", "kind": "street", "direction": "forward", "race_furniture": False,
         "start": {"line_vertex": 40, "grid_vertex": 36, "offset_right_m": 3.25, "sector_vertices": [52, 64]}},
        {"id": "race_cw", "kind": "race", "direction": "forward", "race_furniture": True,
         "start": {"line_vertex": 40, "grid_vertex": 36, "offset_right_m": 3.25, "sector_vertices": [52, 64]}},
        {"id": "race_acw", "kind": "race", "direction": "reverse", "race_furniture": True,
         "start": {"line_vertex": 40, "grid_vertex": 44, "offset_right_m": 3.25, "sector_vertices": [28, 16]}},
    ]
    if closures != "no_token":
        layouts[1]["closure_token"], layouts[2]["closure_token"] = "cw", "acw"
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "loop": False, "layouts": layouts,
                                                      "race": {"grid_slots": 8, "pit_slots": 8}}))
    if lanes:
        (d / "data" / "barrier_bands.json").write_text(json.dumps({"corridors": {
            lid: {"token": {"race_cw": "cw", "race_acw": "acw"}[lid], "lane_by_vertex": [list(lane)] * N_PTS}
            for lid, lane in lanes.items()}}))
    (d / "data" / "finished_centerline.json").write_text(json.dumps({"points_xyz_m": pts, "widths_m": [8.0] * N_PTS}))
    V, T = _ribbon(pts, 4.0)
    main_nodes = []
    if spawn_in_main:
        main_nodes.append(("AC_START_0", (0.0, 0.3, 100.0), 0.0))
    write_kn5(d / "build" / "t.kn5", [("1ROAD_main", V, T, 0)], main_nodes, ["1ROAD_main_mat"])
    if race_kn5:
        ms, mats = _race_meshes(ok_names=(race_kn5 != "bad_name"), ok_mats=(race_kn5 != "bad_mat"),
                                extra=(["1WALL_race_close_cw_t_10_0"] if race_kn5 == "closure_in_common" else []))
        write_kn5(d / "build" / "t_race.kn5", ms, [], mats)
    if closures:
        for lid, tok in (("race_cw", "cw"), ("race_acw", "acw")):
            use = {"swap": {"cw": "acw", "acw": "cw"}[tok]}.get(closures, tok)
            ms, mats = _closure_meshes(use, extra=(["1KERB_race_9_in"] if closures == "kerb" and tok == "cw" else []))
            write_kn5(d / "build" / f"t_closure_{lid}.kn5", ms, [], mats)
    for lo in layouts:
        lid = lo["id"]
        if drop_spawn_kn5 == lid:
            continue
        rev = lo["direction"] == "reverse"
        t = (0.0, -1.0) if rev else (0.0, 1.0)                 # kn5-frame travel
        rx, rz = _right_of(t)
        yaw = math.atan2(t[0], t[1])                            # local +Z = (sin yaw, cos yaw) = t
        if flip_heading == lid:
            yaw += math.pi
        side = -1.0 if wrong_side == lid else 1.0
        st = lo["start"]
        z_pole = pts[st["grid_vertex"]][2]
        z_line = pts[st["line_vertex"]][2]
        behind = 1.0 if rev else -1.0                            # lower z is behind forward travel
        nodes = []
        names = []
        for g in range(8):
            lat = 3.25 + (1.4 if g % 2 else -1.4) * (1 if g else 0)
            zz = z_pole + behind * 5.5 * g
            nodes.append((f"AC_START_{g}", (rx * lat * side, 0.3, zz + rz * lat * side), yaw))
        nodes.append(("AC_HOTLAP_START_0", (rx * 3.25 * side, 0.3, z_pole), yaw))
        for p in range(8):
            zz = z_pole + behind * (45.0 + 7.0 * (p + 1))
            nodes.append((f"AC_PIT_{p}", (rx * 3.25 * side, 0.3, zz), yaw))
        secs = st["sector_vertices"]
        if bad_sectors == lid:
            secs = list(reversed(secs))
        for idx, zz in ((0, z_line), (1, pts[secs[0]][2]), (2, pts[secs[1]][2])):
            nodes.append((f"AC_TIME_{idx}_L", (-4.0, 0.1, zz), 0.0))
            nodes.append((f"AC_TIME_{idx}_R", (4.0, 0.1, zz), 0.0))
        names = [n for n, _p, _y in nodes]
        (d / "data" / f"dummies_{lid}.json").write_text(json.dumps({**{n: [0, 0, 0] for n in names},
                                                                     "_layout": lid, "_direction": lo["direction"]}))
        write_kn5(d / "build" / f"t__{lid}.kn5", [], nodes, [])
    if stray_spawn:
        shutil.copyfile(d / "build" / "t__street.kn5", d / "build" / "t__old.kn5")
    return d


def _has(fails, *subs):
    return any(all(s in f for s in subs) for f in fails)


def test_clean_multi_layout_build_passes():
    fails = verify(_synthetic())
    assert fails == [], fails


def test_spawn_node_in_the_road_kn5_fails():
    fails = verify(_synthetic(spawn_in_main=True))
    assert _has(fails, "MULTI-LAYOUT road kn5 carries"), fails


def test_missing_and_stray_spawn_kn5s_fail():
    assert _has(verify(_synthetic(drop_spawn_kn5="race_acw")), "missing spawn kn5", "t__race_acw.kn5")
    assert _has(verify(_synthetic(stray_spawn=True)), "stray spawn kn5", "t__old.kn5")


def test_heading_180_off_fails_with_the_dot_printed():
    fails = verify(_synthetic(flip_heading="race_cw"))
    assert _has(fails, "HEADING 'race_cw:AC_START_0'", "-1.00"), fails
    assert not _has(fails, "HEADING 'race_acw"), fails


def test_grid_on_the_wrong_side_fails():
    fails = verify(_synthetic(wrong_side="race_acw"))
    assert _has(fails, "SIDE 'race_acw:AC_START_0'", "LEFT"), fails
    assert not _has(fails, "SIDE 'race_cw"), fails


def test_sectors_out_of_driving_order_fail():
    fails = verify(_synthetic(bad_sectors="race_cw"))
    assert _has(fails, "SECTORS 'race_cw'"), fails
    assert not _has(fails, "SECTORS 'race_acw'"), fails


def test_race_kn5_checks():
    assert _has(verify(_synthetic(race_kn5=None)), "declare race_furniture but build/t_race.kn5 does not exist")
    assert _has(verify(_synthetic(race_kn5="bad_name")), "non-race mesh", "1WALL_guard_0")
    assert _has(verify(_synthetic(race_kn5="bad_mat")), "non-race material", "1ROAD_main_mat")
    # ledger 0049: no closure in the common kn5
    assert _has(verify(_synthetic(race_kn5="closure_in_common")), "RACE kn5 't_race.kn5' carries 1 closure mesh")


def test_closure_kn5s_carry_their_own_layouts_closure_only():
    """(f) since ledger 0049: one <slug>_closure_<id>.kn5 per race layout, holding only that layout's
    1WALL_RACE_CLOSE_<TOKEN>_* meshes — the token declared by barrier_bands.json corridors.<id>.token, else
    layouts[].closure_token"""
    assert verify(_synthetic()) == []
    fails = verify(_synthetic(closures=None))
    assert _has(fails, "race layout race_cw has no build/t_closure_race_cw.kn5") and _has(fails, "t_closure_race_acw.kn5"), fails
    fails = verify(_synthetic(closures="swap"))
    assert _has(fails, "CLOSURE kn5 't_closure_race_cw.kn5' (race_cw)", "not race_cw's closure"), fails
    assert _has(fails, "holds no 1WALL_RACE_CLOSE_CW_* mesh"), fails
    assert _has(verify(_synthetic(closures="kerb")), "CLOSURE kn5 't_closure_race_cw.kn5'", "1KERB_race_9_in")
    assert _has(verify(_synthetic(closures="no_token")), "race layout race_cw declares no closure token")
    d = _synthetic()
    shutil.copyfile(d / "build" / "t_closure_race_cw.kn5", d / "build" / "t_closure_race_old.kn5")
    assert _has(verify(d), "stray closure kn5 build/t_closure_race_old.kn5")


def test_spawns_stand_inside_the_declared_lane_of_a_race_layout():
    """(d) with a corridor declared the START / PIT cars must stand inside the layout's lane (>= 0.30 m off each
    face); the lane replaces "right of travel" (on Alvarado the race lane is the whole street)"""
    wide = {"race_cw": [-6.5, 6.5], "race_acw": [-6.5, 6.5]}
    assert verify(_synthetic(lanes=wide)) == []
    # the grid's outer column stands 4.65 m right of travel: a lane face at -5.0 leaves it -0.6 m
    fails = verify(_synthetic(lanes={"race_cw": [-5.0, 6.5], "race_acw": [-6.5, 6.5]}))
    assert _has(fails, "LANE 'race_cw:AC_START_1'", "OUTSIDE"), fails
    assert not _has(fails, "LANE 'race_acw"), fails
    # a car LEFT of its travel but inside the declared lane is legal for a race layout (the lane decides)...
    assert not _has(verify(_synthetic(lanes=wide, wrong_side="race_acw")), "SIDE 'race_acw")
    # ...and still a SIDE fail for a layout without a declared lane
    assert _has(verify(_synthetic(wrong_side="race_acw")), "SIDE 'race_acw:AC_START_0'", "LEFT")


def _write_inis(d, lists):
    out = d / "build" / "t"
    out.mkdir(parents=True, exist_ok=True)
    for lid, files in lists.items():
        s = "".join(f"[MODEL_{i}]\nFILE={f}\nPOSITION=0,0,0\nROTATION=0,0,0\n\n" for i, f in enumerate(files))
        (out / f"models_{lid}.ini").write_text(s, encoding="utf-8")
        for f in files:
            (out / f).write_bytes(b"kn5")
    return out


def test_inis_list_exactly_road_common_own_closure_and_spawns():
    """(g) after track_folder: each race ini = [road, common race, OWN closure, own spawns]; street = [road, spawns];
    no ini lists the other direction's closure (both closures would block both lanes)"""
    from scripts.ac.verify_kn5 import verify_inis
    d = _synthetic()
    good = {"street": ["t.kn5", "t__street.kn5"],
            "race_cw": ["t.kn5", "t_race.kn5", "t_closure_race_cw.kn5", "t__race_cw.kn5"],
            "race_acw": ["t.kn5", "t_race.kn5", "t_closure_race_acw.kn5", "t__race_acw.kn5"]}
    _write_inis(d, good)
    assert verify_inis(d) == []
    bad = dict(good, race_cw=["t.kn5", "t_race.kn5", "t_closure_race_cw.kn5", "t_closure_race_acw.kn5", "t__race_cw.kn5"])
    _write_inis(d, bad)
    fails = verify_inis(d)
    assert _has(fails, "INI: models_race_cw.ini lists another layout's closure ['t_closure_race_acw.kn5']"), fails
    _write_inis(d, dict(good, race_acw=["t.kn5", "t_race.kn5", "t__race_acw.kn5"]))      # closure missing (the 0047 shape)
    assert _has(verify_inis(d), "INI: models_race_acw.ini lists", "expected exactly")
    _write_inis(d, dict(good, street=["t.kn5", "t_race.kn5", "t__street.kn5"]))          # the street loads race furniture
    assert _has(verify_inis(d), "INI: models_street.ini lists")
    _write_inis(d, good)
    (d / "build" / "t" / "t_closure_race_cw.kn5").unlink()
    assert _has(verify_inis(d), "INI: models_race_cw.ini lists t_closure_race_cw.kn5, which is not in")
    (d / "build" / "t" / "models_street.ini").unlink()
    assert _has(verify_inis(d), "INI: no models_street.ini")


def test_parse_keeps_the_two_tuple_api_and_reads_local_z():
    d = _synthetic()
    nodes3, meshes, mats = _parse_full(d / "build" / "t__race_acw.kn5")
    z = dict((n, zax) for n, _p, zax in nodes3)["AC_START_0"]
    assert abs(z[0]) < 1e-6 and abs(z[2] + 1.0) < 1e-6          # reverse: +Z along -z
    from scripts.ac.verify_kn5 import _parse
    n2, m2 = _parse(d / "build" / "t.kn5")
    assert all(len(t) == 2 for t in n2) and m2[0]["name"] == "1ROAD_main"


# ---------------------------------------------------------------- real data: Lake Murray
SD = ROOT / "tracks" / "san-diego-lake-murray"


def _sd_project() -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir(); (d / "build").mkdir()
    cfg = json.loads((SD / "track.config.json").read_text(encoding="utf-8"))
    for lo in cfg["layouts"]:            # the ledger-0049 closure tokens (the repo config may predate them)
        if lo.get("race_furniture"):
            lo.setdefault("closure_token", "cw" if lo.get("direction", "forward") == "forward" else "acw")
    (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    shutil.copyfile(SD / "start_positions.json", d / "start_positions.json")
    for f in ("centerline.local.json", "median_bands.json", "finished_centerline.json", "barrier_bands.json"):
        shutil.copyfile(sd_v0180.DATA / f, d / "data" / f)
    return d


def test_lake_murray_dummies_from_layout_dummies_pass_the_spawn_gate():
    d = _sd_project()
    cfg = json.loads((d / "track.config.json").read_text(encoding="utf-8"))
    assert float(cfg.get("true_north_rotation_deg") or 0.0) == 0.0     # no yaw between the frames here
    assert ld.write_all(d) == 0
    fin = json.loads((d / "data" / "finished_centerline.json").read_text())
    fpts = fin["points_xyz_m"]
    V, T = _ribbon(fpts, 7.0, step=1)                        # a 14 m ribbon under the whole lap
    assert len(V) <= 65535
    write_kn5(d / "build" / "san_diego_lake_murray.kn5", [("1ROAD_main", V, T, 0)], [], ["1ROAD_main_mat"])
    ms, mats = _race_meshes()
    write_kn5(d / "build" / "san_diego_lake_murray_race.kn5", ms, [], mats)
    for lo in cfg["layouts"]:
        if lo.get("race_furniture"):
            ms, mats = _closure_meshes(lo["closure_token"])
            write_kn5(d / "build" / f"san_diego_lake_murray_closure_{lo['id']}.kn5", ms, [], mats)
    # ledger 0055: race.chicanes declares a street-only island -> <slug>_street.kn5 must exist, street-only meshes
    street = d / "build" / "san_diego_lake_murray_street.kn5"
    write_kn5(street, [("1KERB_sidewalk_streetonly_median", _BOX, _BTRIS, 0)], [],
              ["1KERB_sidewalk_streetonly_median_mat"])
    for lo in cfg["layouts"]:
        lid = lo["id"]
        dj = json.loads((d / "data" / f"dummies_{lid}.json").read_text(encoding="utf-8"))
        nodes = []
        for name, pos in dj.items():
            if name.startswith("_"):
                continue
            x, y, z = pos
            psi = math.radians(float(dj["_yaw_deg"].get(name, 0.0)))   # Blender rotation_euler.z
            # exporter: position (x, z, -y)_blender = (x, y, -z)_engine; local +Z = (sin psi, cos psi)
            nodes.append((name, (x, y, -z), psi))
        write_kn5(d / "build" / f"san_diego_lake_murray__{lid}.kn5", [], nodes, [])
    fails = verify(d)
    assert fails == [], fails
    # ...and without it Free Roam would lose the median over the Speedways' chicane: a FAIL
    street.unlink()
    assert any("san_diego_lake_murray_street.kn5 does not exist" in f for f in verify(d))


def test_lake_murray_reflected_yaw_is_caught():
    """the pre-0047 atan2(tx, tz) yaw: kn5 +Z = (tx, tz) while the travel is (tx, -tz) — on
    east-west Alvarado the dot is only ~cos(2*heading) off, so the gate is exercised on a
    north-south vertex (College, v1100) where it reads ~ -1"""
    d = _sd_project()
    cl = json.loads((d / "data" / "centerline.local.json").read_text())
    line = ld.Line(cl["points_xyz_m"], cl["widths_m"])
    ux, uz = line.travel(1100, "forward")
    psi_ok = math.atan2(ux, -uz)
    psi_old = math.atan2(ux, uz)
    fin = json.loads((d / "data" / "finished_centerline.json").read_text())
    fp = fin["points_xyz_m"][1100]
    t = (ux, -uz)                                             # kn5-frame travel
    assert abs(math.sin(psi_ok) * t[0] + math.cos(psi_ok) * t[1] - 1.0) < 1e-6
    assert math.sin(psi_old) * t[0] + math.cos(psi_old) * t[1] < -0.9
    assert abs(fp[0] - cl["points_xyz_m"][1100][0]) < 1e-6 and abs(fp[2] + cl["points_xyz_m"][1100][2]) < 1e-6
