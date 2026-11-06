"""tools/kn5_equiv.py: the identity rule for "unchanged" kn5s -- bytes, or tangents only within 1e-6 (fleet/GATES-CHANGELOG)."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools import kn5_equiv as ke  # noqa: E402


def _s(t: str) -> bytes:
    b = t.encode()
    return struct.pack("<I", len(b)) + b


def _kn5(textures=(("a.png", b"PNG1"),), tangent=(1.0, 0.0, 0.0), pos=(0.0, 0.0, 0.0), mat="M_0", split=False) -> bytes:
    """a minimal kn5: version 5, the textures, one material, a root node holding one 3-vertex mesh"""
    out = b"sc6969" + struct.pack("<i", 5) + struct.pack("<i", len(textures))
    for name, data in textures:
        out += struct.pack("<i", 1) + _s(name) + struct.pack("<I", len(data)) + data
    out += struct.pack("<I", 1) + _s(mat) + _s("ksPerPixel") + b"\x00\x00" + struct.pack("<i", 0)
    out += struct.pack("<I", 0) + struct.pack("<I", 1) + _s("txDiffuse") + struct.pack("<i", 0) + _s(textures[0][0])
    verts = b""
    pts = [(pos[0] + k, pos[1], pos[2]) for k in range(4)]                  # a quad: two triangles sharing 0 and 2
    tris = [0, 1, 2, 0, 2, 3]
    tans = [tangent] * 4
    if split:                                     # vertex 2 left unmerged for the 2nd triangle by a 5e-8 tangent
        pts.append(pts[2]); tans.append((tangent[0], tangent[1] + 5e-8, tangent[2])); tris = [0, 1, 2, 0, 4, 3]
    for p, t in zip(pts, tans):
        verts += struct.pack("<11f", *p, 0.0, 1.0, 0.0, 0.0, 0.0, *t)
    mesh = struct.pack("<I", 2) + _s("MESH_0") + struct.pack("<I", 0) + b"\x01" + b"\x01\x01\x01"
    mesh += struct.pack("<I", len(pts)) + verts + struct.pack("<I", len(tris)) + struct.pack(f"<{len(tris)}H", *tris)
    mesh += struct.pack("<IIff", 0, 0, 0.0, 0.0) + b"\x00" * 16 + b"\x00"
    root = struct.pack("<I", 1) + _s("root") + struct.pack("<I", 1) + b"\x01" + struct.pack("<16f", *[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
    return out + root + mesh


def test_identical_and_tangent_noise_are_the_same_build():
    a = _kn5()
    assert ke.compare(a, a)["equivalent"]
    r = ke.compare(a, _kn5(tangent=(1.0, 4e-7, 0.0)))
    assert r["equivalent"] and r["tangent_values"] == 4 and r["tangent_max"] < 1e-6


def test_a_real_tangent_or_position_change_is_not():
    assert not ke.compare(_kn5(), _kn5(tangent=(1.0, 0.01, 0.0)))["equivalent"]
    r = ke.compare(_kn5(), _kn5(pos=(0.0, 0.0, 1e-3)))
    assert not r["equivalent"] and "pz" in r["first"]


def test_added_textures_are_named_and_the_rest_still_compared():
    r = ke.compare(_kn5(), _kn5(textures=(("a.png", b"PNG1"), ("stucco.jpg", b"JPG"))))
    assert not r["equivalent"] and r["textures_added"] == ["stucco.jpg"] and r["first"].startswith("textures only")
    r = ke.compare(_kn5(), _kn5(textures=(("a.png", b"PNG1"), ("stucco.jpg", b"JPG")), mat="M_1"))
    assert not r["equivalent"] and r["first"].startswith("materials")


def test_a_vertex_left_unmerged_by_tangent_noise_is_the_same_build_corner_by_corner():
    r = ke.compare(_kn5(), _kn5(split=True))
    assert r["equivalent"] and r["merge_differs"] == ["MESH_0 4 -> 5 vertices"]
    r = ke.compare(_kn5(), _kn5(split=True, pos=(0.0, 0.0, 1e-3)))
    assert not r["equivalent"] and "pz" in r["first"]


def test_list_names_every_mesh_that_moved_and_where():
    """--list (ledger 0054 Phase 2 step 4): the meshes that differ, each with the plan box of what moved"""
    assert ke.mesh_diffs(_kn5(), _kn5()) == [] and ke.mesh_diffs(_kn5(), _kn5(tangent=(1.0, 4e-7, 0.0))) == []
    d = ke.mesh_diffs(_kn5(), _kn5(pos=(0.0, 0.0, 2.0)))
    assert len(d) == 1 and d[0]["mesh"] == "MESH_0" and d[0]["why"] == "4 of 4 vertices moved"
    assert d[0]["box_xz"] == [0.0, 2.0, 3.0, 2.0]
    d = ke.mesh_diffs(_kn5(), _kn5(split=True))
    assert d[0]["why"] == "vertex count 4 -> 5"
