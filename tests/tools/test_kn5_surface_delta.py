"""tools/kn5_surface_delta.py — the ground compared as a SURFACE (ledger 0054 Phase 2 step 2e).

Pins: the same plane cut into different tiles and triangulated the other way reads 0 everywhere (the re-tiling and
re-thinning kn5_equiv --list reports as "moved"); a 3 cm bump in one tile reads 3 cm there, in that tile and inside its
box, and nowhere else; a rock mesh is reported on its own; a hole is counted, not differenced. Plain ``test_*``.
"""
from __future__ import annotations

import json
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools import kn5_surface_delta as sd  # noqa: E402


def _s(t: str) -> bytes:
    b = t.encode()
    return struct.pack("<I", len(b)) + b


def _mesh(name, pts, tris) -> bytes:
    verts = b"".join(struct.pack("<11f", *p, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0) for p in pts)
    m = struct.pack("<I", 2) + _s(name) + struct.pack("<I", 0) + b"\x01" + b"\x01\x01\x01"
    m += struct.pack("<I", len(pts)) + verts + struct.pack("<I", len(tris)) + struct.pack(f"<{len(tris)}H", *tris)
    return m + struct.pack("<IIff", 0, 0, 0.0, 0.0) + b"\x00" * 16 + b"\x00"


def _kn5(meshes) -> bytes:
    out = b"sc6969" + struct.pack("<i", 5) + struct.pack("<i", 1)
    out += struct.pack("<i", 1) + _s("a.png") + struct.pack("<I", 4) + b"PNG1"
    out += struct.pack("<I", 1) + _s("M_0") + _s("ksPerPixel") + b"\x00\x00" + struct.pack("<i", 0)
    out += struct.pack("<I", 0) + struct.pack("<I", 1) + _s("txDiffuse") + struct.pack("<i", 0) + _s("a.png")
    root = (struct.pack("<I", 1) + _s("root") + struct.pack("<I", len(meshes)) + b"\x01"
            + struct.pack("<16f", *[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]))
    return out + root + b"".join(_mesh(*m) for m in meshes)


def _h(x, z):
    return 100.0 + 0.05 * x - 0.02 * z            # a plane: any triangulation of it is the same surface


def _tile(name, xa, xb, za, zb, *, flip=False, bump=None):
    """a 1 m quad grid over [xa, xb] x [za, zb] on the plane (+ a bump (x, z, dy) at one vertex)"""
    nx, nz = int(xb - xa), int(zb - za)
    pts = []
    for j in range(nz + 1):
        for i in range(nx + 1):
            x, z = xa + i, za + j
            y = _h(x, z) + (bump[2] if bump and (x, z) == bump[:2] else 0.0)
            pts.append((float(x), y, float(z)))
    tris = []
    for j in range(nz):
        for i in range(nx):
            a, b, c, d = j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i
            tris += [a, b, c, a, c, d] if not flip else [a, b, d, b, c, d]
    return name, pts, tris


def _write(meshes) -> Path:
    p = Path(tempfile.mkdtemp()) / "t.kn5"
    p.write_bytes(_kn5(meshes))
    return p


def test_a_retiled_retriangulated_plane_does_not_move():
    a = _write([_tile("1GRASS_0", 0, 10, 0, 20), _tile("1GRASS_1", 10, 20, 0, 20)])
    b = _write([_tile("1GRASS_0", 0, 13, 0, 20, flip=True), _tile("1GRASS_1", 13, 20, 0, 20, flip=True)])
    r = sd.delta(a, b, step=0.5)
    assert r["points_compared"] > 1500 and r["points_only_in_a"] == 0 and r["points_only_in_b"] == 0
    assert r["overall"]["max_abs_m"] < 1e-6 and r["overall"]["n_gt_1mm"] == 0, r["overall"]


def test_a_bump_reads_where_it_is_and_nowhere_else():
    a = _write([_tile("1GRASS_0", 0, 10, 0, 20), _tile("1GRASS_1", 10, 20, 0, 20)])
    b = _write([_tile("1GRASS_0", 0, 10, 0, 20), _tile("1GRASS_1", 10, 20, 0, 20, bump=(15, 8, 0.03))])
    r = sd.delta(a, b, step=0.25)
    assert abs(r["overall"]["max_abs_m"] - 0.03) < 1e-4
    assert r["by_tile_a"]["1GRASS_0"]["n_gt_1mm"] == 0 and r["by_tile_a"]["1GRASS_1"]["n_gt_10mm"] > 0
    x0, z0, x1, z1 = r["by_tile_a"]["1GRASS_1"]["box_gt_10mm_xz"]
    assert 14.0 <= x0 <= 15.0 <= x1 <= 16.0 and 7.0 <= z0 <= 8.0 <= z1 <= 9.0
    assert r["worst"][0]["tile_a"] == "1GRASS_1" and abs(r["worst"][0]["d_m"] - 0.03) < 1e-4


def test_rock_is_reported_on_its_own_and_a_hole_is_counted():
    a = _write([_tile("1GRASS_0", 0, 10, 0, 10), _tile("1GRASS_ROCK_0", 10, 14, 0, 10)])
    b = _write([_tile("1GRASS_0", 0, 10, 0, 10), _tile("1GRASS_ROCK_3", 10, 14, 0, 5, bump=(12, 3, -0.08))])
    r = sd.delta(a, b, step=0.5)
    assert r["points_only_in_a"] > 0                       # the rock's far half is gone in b: a hole, not a delta
    assert abs(r["rock"]["max_abs_m"] - 0.08) < 1e-4 and r["rock"]["n_gt_50mm"] > 0
    assert r["by_tile_a"]["1GRASS_0"]["max_abs_m"] < 1e-6


def test_the_cli_writes_json_and_bins_by_distance_to_a_line():
    a = _write([_tile("1GRASS_0", 0, 20, 0, 20)])
    b = _write([_tile("1GRASS_0", 0, 20, 0, 20, bump=(2, 2, 0.05))])
    d = Path(tempfile.mkdtemp())
    line = d / "lap.json"                                 # engine frame: kn5 z = -engine z
    line.write_text(json.dumps({"points_xyz_m": [[2.0, 0.0, -2.0], [2.0, 0.0, -3.0]]}))
    out = d / "r.json"
    assert sd.main([str(a), str(b), "--step", "0.5", "--line", str(line), "--json", str(out)]) == 0
    r = json.loads(out.read_text())
    assert r["by_distance_to_line"]["<20 m"]["n_gt_10mm"] > 0
    assert all(s.get("n_gt_1mm", 0) == 0 for k, s in r["by_distance_to_line"].items() if k != "<20 m")
    assert sd.main([str(a)]) == 2


def test_exclude_reports_the_rest_and_box_limits_the_grid():
    a = _write([_tile("1GRASS_0", 0, 20, 0, 20)])
    b = _write([_tile("1GRASS_0", 0, 20, 0, 20, bump=(5, 5, 0.05))])
    r = sd.delta(a, b, step=0.5, exclude=[3.0, 3.0, 7.0, 7.0])
    assert r["overall"]["n_gt_10mm"] > 0 and r["outside_exclude"]["n_gt_1mm"] == 0
    rb = sd.delta(a, b, step=0.5, box=[10.0, 10.0, 20.0, 20.0])
    assert rb["points_compared"] == 21 * 21 and rb["overall"]["max_abs_m"] < 1e-6
