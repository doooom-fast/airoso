"""tools/calibrate_kinks.py — drive_test's kink metric on a reference road (Lariat V3-PLAN P5), and the two engine
seams it rests on: scripts.modkit.extract_kn5.parse(keep=, textures=) and drive_test's opt-in per-track ceiling.

A synthetic "reference track" folder is built the way AC lays one out (models_<layout>.ini, <layout>/data/
surfaces.ini, <layout>/ai/fast_lane.ai v7 with the sideLeft / sideRight extras) around a kn5 written by the
engine's native writer (the fixture pattern of tests/modkit/test_kn5_to_gate_obj_multi.py):
- a road on one steady grade reads 0 kinks; the same road with two slope breaks of 8 %-points reads them;
- the racing line 2 m off centre is moved back to the lane centre under either side convention;
- the reference folder is never written to, and a --work inside airoso is refused;
- parse(keep=) returns exactly the kept meshes of a full parse; textures=False steps over the blobs;
- drive_test without gates.drive_test.kinks_per_km_max writes the same report as before (no ceiling key, kinks
  never gate); with it, the ceiling gates and is recorded.
Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import json
import os
import shutil
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import calibrate_kinks as ck  # noqa: E402
from scripts.ac.kn5_write import build  # noqa: E402
from scripts.geometry import drive_test, ribbon  # noqa: E402
from scripts.modkit.extract_kn5 import parse  # noqa: E402

W = 8.0
Z0, Z1 = -150, 150


def _profile(kinky: bool):
    if not kinky:
        return lambda z: 0.03 * (z - Z0)                       # one steady 3 % grade: no kink anywhere
    def y(z):                                                  # flat, +8 % from z = -40 to z = 40, flat
        return 0.08 * (min(max(z, -40.0), 40.0) + 40.0)
    return y


def _write_obj(path: Path, groups) -> None:
    lines, base = [], 1
    for name, mesh in groups:
        lines.append(f"o {name}")
        for x, y, z in mesh["vertices"]:
            lines.append(f"v {x:.4f} {y:.4f} {z:.4f}")
        for _ in mesh["vertices"]:
            lines.append("vt 0 0")
        for a, b, c in mesh["tris"]:
            lines.append(f"f {base+a}/{base+a} {base+b}/{base+b} {base+c}/{base+c}")
        base += len(mesh["vertices"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _road_project(kinky: bool) -> Path:
    y = _profile(kinky)
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "ref", "mirror_x": False}))
    cl = [(0.0, y(float(z)), float(z)) for z in range(Z0, Z1 + 1)]
    road = ribbon.road_ribbon(cl, [W] * len(cl))
    grass = {"vertices": [(-60, -5, Z0 - 10), (60, -5, Z0 - 10), (60, -5, Z1 + 10), (-60, -5, Z1 + 10)],
             "tris": [(0, 1, 2), (0, 2, 3)]}
    _write_obj(d / "data" / "track.obj", [("1ROAD_main", road), ("1GRASS_far", grass)])
    return d


def _ai_bytes(points, sides) -> bytes:
    out = bytearray(struct.pack("<4i", 7, len(points), 0, 0))
    s = 0.0
    for k, (x, y, z) in enumerate(points):
        if k:
            px, _py, pz = points[k - 1]
            s += ((x - px) ** 2 + (z - pz) ** 2) ** 0.5
        out += struct.pack("<3ffi", x, y, z, s, k)
    if sides is not None:
        out += struct.pack("<i", len(points))
        for sl, sr in sides:
            out += struct.pack("<18f", 100.0, 1, 0, 0, 50.0, sl, sr, 0, 0, 0, 1, 0, 1.5, 0, 0, 1, 0, 0)
    return bytes(out)


def _reference(kinky: bool, side_left: float = 6.0, side_right: float = 2.0, extras: bool = True) -> Path:
    """an AC-shaped track folder holding the synthetic road; the AI line runs 2 m off centre (x = +2)"""
    proj = _road_project(kinky)
    kn5 = build(proj)
    ref = Path(tempfile.mkdtemp()) / "ref_track"
    (ref / "lay" / "ai").mkdir(parents=True)
    (ref / "lay" / "data").mkdir(parents=True)
    shutil.copyfile(kn5, ref / "ref.kn5")
    (ref / "models_lay.ini").write_text("[MODEL_0]\nFILE=ref.kn5\nPOSITION=0,0,0\n\n"
                                        "[DYNAMIC_OBJECT_0]\nFILE=balloon.kn5\n", encoding="utf-8")
    (ref / "lay" / "data" / "surfaces.ini").write_text("[SURFACE_0]\nKEY=ROAD\nFRICTION=0.98\nIS_VALID_TRACK=1\n"
                                                       "[SURFACE_1]\nKEY=GRASS\nFRICTION=0.6\n", encoding="utf-8")
    y = _profile(kinky)
    pts = []
    z = Z0 + 2.0
    while z <= Z1 - 2.0:
        pts.append((2.0, y(z), z))
        z += 1.5
    sides = [(0.0, 0.0)] + [(side_left, side_right)] * (len(pts) - 1)   # the recorder's zero first point
    (ref / "lay" / "ai" / "fast_lane.ai").write_bytes(_ai_bytes(pts, sides if extras else None))
    return ref


def _snapshot(folder: Path):
    return sorted((str(p.relative_to(folder)), p.stat().st_size, p.stat().st_mtime_ns)
                  for p in folder.rglob("*") if p.is_file())


def test_read_ai_reads_positions_and_sides():
    ref = _reference(False)
    ai = ck.read_ai(ref / "lay" / "ai" / "fast_lane.ai")
    assert ai[0][4:] == (0.0, 0.0) and ai[1][4:] == (6.0, 2.0)
    assert abs(ai[1][0] - 2.0) < 1e-6 and abs(ai[1][3] - 1.5) < 1e-5
    bare = _reference(False, extras=False)
    assert all(p[4] == p[5] == 0.0 for p in ck.read_ai(bare / "lay" / "ai" / "fast_lane.ai"))


def test_the_racing_line_moves_to_the_lane_centre_under_either_side_convention():
    for sl, sr, sign in ((6.0, 2.0, 1), (2.0, 6.0, -1)):
        ref = _reference(False, sl, sr)
        ai = ck.read_ai(ref / "lay" / "ai" / "fast_lane.ai")
        groups, _ = ck.road_groups([ref / "ref.kn5"], ck.surface_keys(ref), r"^ROAD", ai)
        field = drive_test.TriField()
        for g in groups:
            for t in g["tris"]:
                field.add(g["verts"], t, g["name"])
        pts, widths, notes = ck.lane_centre(ai, field)
        assert notes["sign"] == sign, notes
        assert notes["points_used"] == len(ai) - 1                 # the zero-width first point is dropped
        assert max(abs(p[0]) for p in pts[ck.SMOOTH_PTS:-ck.SMOOTH_PTS]) < 0.05
        assert abs(widths[len(widths) // 2] - 8.0) < 1e-6 and notes["centre_on_road_frac"] == 1.0
    bare = _reference(False, extras=False)
    try:
        ck.lane_centre(ck.read_ai(bare / "lay" / "ai" / "fast_lane.ai"), drive_test.TriField())
    except SystemExit as e:
        assert "no lane to centre on" in str(e)
    else:
        raise AssertionError("an AI line without sides was centred")


def test_a_steady_grade_reads_no_kinks_and_slope_breaks_read_as_kinks():
    smooth = _reference(False)
    before = _snapshot(smooth)
    row = ck.calibrate(smooth, "lay", Path(tempfile.mkdtemp()) / "work")
    assert row["kinks"] == 0 and row["kinks_per_km"] == 0.0, row
    assert row["kn5"] == ["ref.kn5"] and row["road"]["meshes"] == 1 and row["lane"]["sign"] == 1
    assert _snapshot(smooth) == before, "the reference track folder was written to"
    kinky = _reference(True)
    row = ck.calibrate(kinky, "lay", Path(tempfile.mkdtemp()) / "work")
    # two 8 %-point breaks met by the six interior wheel paths. The lane starts at z = -146.5 (the AI's first
    # point is dropped), so each break falls half-way between two 1 m stations and reads as two 4-point kinks:
    # 2 breaks x 2 x 6 paths = 24, at lane stations ~106.5 (z = -40) and ~186.5 (z = +40)
    assert row["kinks"] == 24 and row["kinks_per_km"] > 60, row
    assert all(abs(k[0] - 106.5) <= 1.5 or abs(k[0] - 186.5) <= 1.5 for k in row["worst_kinks"]), row["worst_kinks"]


def test_work_inside_airoso_is_refused():
    ref = _reference(False)
    for bad in (ROOT / "scratch_kinks", ROOT):
        try:
            ck.main(["--track", str(ref), "--layout", "lay", "--work", str(bad)])
        except SystemExit as e:
            assert "inside airoso" in str(e)
        else:
            raise AssertionError(f"--work {bad} was accepted")
        assert not (ROOT / "scratch_kinks").exists()


def test_parse_keep_returns_exactly_the_kept_meshes():
    proj = _road_project(False)
    kn5 = build(proj)
    full = parse(kn5)
    assert {m["name"] for m in full["meshes"]} == {"1ROAD_main", "1GRASS_far"} and full["textures"]
    same = parse(kn5, keep=lambda n: True)
    assert same == full
    road = parse(kn5, keep=lambda n: n.startswith("1ROAD"), textures=False)
    assert road["textures"] == {} and road["materials"] == full["materials"]
    assert road["meshes"] == [m for m in full["meshes"] if m["name"].startswith("1ROAD")]
    assert parse(kn5, keep=lambda n: False)["meshes"] == []


def _drive_project(ceiling=None) -> Path:
    """test_drive_test's 200 m straight, with two 3.5 %-point slope breaks (kinks, but under every other gate)"""
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    cfg = {"slug": "t", "mirror_x": False}
    if ceiling is not None:
        cfg["gates"] = {"drive_test": {"kinks_per_km_max": ceiling}}
    (d / "track.config.json").write_text(json.dumps(cfg))
    def y(z):
        return 0.035 * (min(max(z, 60.0), 140.0) - 60.0)
    cl = [(0.0, y(float(z)), float(z)) for z in range(0, 201)]
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": [list(p) for p in cl], "widths_m": [W] * len(cl), "origin": {"lon": 0, "lat": 0, "elev_m": 0}}))
    road = ribbon.road_ribbon(cl, [W] * len(cl))
    ground = ribbon.road_ribbon([(x, yy - 0.02, z) for x, yy, z in cl], [40.0] * len(cl))   # seated grass apron
    _write_obj(d / "data" / "track.obj", [("1ROAD_main", road), ("1GRASS_apron", ground)])
    return d


def test_drive_test_kink_ceiling_is_opt_in_per_track():
    base = _drive_project()
    r0 = drive_test.run(base)
    assert r0["kinks_per_km"] > 30 and "kinks_per_km_max" not in r0
    assert r0["fail"] is False, r0          # kinks alone never gate without the key (every other track today)
    written0 = json.loads((base / "data" / "drive_test.json").read_text(encoding="utf-8"))
    assert "kinks_per_km_max" not in written0
    tight = _drive_project(ceiling=10.0)
    r1 = drive_test.run(tight)
    assert r1["fail"] is True and r1["kinks_per_km_max"] == 10.0
    loose = _drive_project(ceiling=1000.0)
    r2 = drive_test.run(loose)
    assert r2["fail"] is False and r2["kinks_per_km_max"] == 1000.0
    # the ceiling is the only thing the key adds: the reports are otherwise the same, key for key
    written2 = json.loads((loose / "data" / "drive_test.json").read_text(encoding="utf-8"))
    written2.pop("kinks_per_km_max")
    assert written2 == written0
