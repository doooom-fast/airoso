"""verify_kn5 on a multi-layout track (ledger 0047): spawn-free road kn5, one nodes-only spawn kn5
per layout facing its travel on the right side of the road, AC_TIME_0 at the declared line with the
sectors in driving order, and the race-furniture kn5 carrying only RACE-named meshes/materials.

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


def _race_meshes(ok_names=True, ok_mats=True):
    box = [(-0.3, 0.0, 10.0), (0.3, 0.0, 10.0), (0.3, 1.2, 10.0), (-0.3, 1.2, 10.0),
           (-0.3, 0.0, 20.0), (0.3, 0.0, 20.0), (0.3, 1.2, 20.0), (-0.3, 1.2, 20.0)]
    btris = [(3, 2, 6), (3, 6, 7), (1, 2, 6), (1, 6, 5)]
    kerb = [(2.0, 0.0, 30.0), (3.0, 0.0, 30.0), (3.0, 0.05, 40.0), (2.0, 0.05, 40.0)]
    ktris = [_face_up(kerb, (0, 1, 2)), _face_up(kerb, (0, 2, 3))]
    names = ("1WALL_race_c0_0", "1KERB_race_40_out") if ok_names else ("1WALL_guard_0", "1KERB_race_40_out")
    mats = ["1WALL_race_mat", "1KERB_race_mat"] if ok_mats else ["1WALL_race_mat", "1ROAD_main_mat"]
    return [(names[0], box, btris, 0), (names[1], kerb, ktris, 1)], mats


# ---------------------------------------------------------------- the synthetic project
N_PTS = 81                      # z = 0..400 at 5 m, open line, kn5 frame


def _synthetic(*, spawn_in_main=False, drop_spawn_kn5=None, flip_heading=None, wrong_side=None,
               bad_sectors=None, race_kn5="ok", stray_spawn=False) -> Path:
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
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "loop": False, "layouts": layouts,
                                                      "race": {"grid_slots": 8, "pit_slots": 8}}))
    (d / "data" / "finished_centerline.json").write_text(json.dumps({"points_xyz_m": pts, "widths_m": [8.0] * N_PTS}))
    V, T = _ribbon(pts, 4.0)
    main_nodes = []
    if spawn_in_main:
        main_nodes.append(("AC_START_0", (0.0, 0.3, 100.0), 0.0))
    write_kn5(d / "build" / "t.kn5", [("1ROAD_main", V, T, 0)], main_nodes, ["1ROAD_main_mat"])
    if race_kn5:
        ms, mats = _race_meshes(ok_names=(race_kn5 != "bad_name"), ok_mats=(race_kn5 != "bad_mat"))
        write_kn5(d / "build" / "t_race.kn5", ms, [], mats)
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
    shutil.copyfile(SD / "track.config.json", d / "track.config.json")
    shutil.copyfile(SD / "start_positions.json", d / "start_positions.json")
    for f in ("centerline.local.json", "median_bands.json", "finished_centerline.json", "barrier_bands.json"):
        shutil.copyfile(SD / "data" / f, d / "data" / f)
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
