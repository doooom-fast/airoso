"""tools/kn5_textures.py (ledger 0082 pass 2): every texture a kn5's materials name must be embedded in it.

A synthetic kn5 (the sections the check reads: textures, materials, then any bytes) is built here; the check passes it
whole, and fails it with a texture dropped (the PC's 0082-1 run 1), an empty map or a zero-byte texture. The gate is
opt-in: only Milford's ship.json names it.
"""

from __future__ import annotations

import importlib.util
import json
import struct
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("kn5_textures", ROOT / "tools" / "kn5_textures.py")
kt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kt)


def _s(x: str) -> bytes:
    b = x.encode()
    return struct.pack("<I", len(b)) + b


def _kn5(textures, materials, version=5) -> bytes:
    """textures: [(name, data)]; materials: [(name, [(sampler, texname)])]"""
    out = b"sc6969" + struct.pack("<I", version) + (struct.pack("<i", 0) if version > 5 else b"")
    out += struct.pack("<I", len(textures))
    for name, data in textures:
        out += struct.pack("<i", 1) + _s(name) + struct.pack("<I", len(data)) + data
    out += struct.pack("<I", len(materials))
    for name, maps in materials:
        out += _s(name) + _s("ksPerPixel") + bytes([0]) + bytes([0]) + struct.pack("<i", 0)
        out += struct.pack("<I", 1) + _s("ksDiffuse") + struct.pack("<f", 0.4) + b"\0" * 36
        out += struct.pack("<I", len(maps))
        for slot, (sampler, tex) in enumerate(maps):
            out += _s(sampler) + struct.pack("<I", slot) + _s(tex)
    return out + b"\x01\0\0\0nodes follow"


WHOLE = ([("ghost_alpha.png", b"PNG1"), ("wbeam_rail_diffuse.png", b"PNG22"), ("unused.dds", b"D")],
         [("1WALL_GHOST_RAIL_0_mat", [("txDiffuse", "ghost_alpha.png")]),
          ("GUARDRAIL_W_0_mat", [("txDiffuse", "wbeam_rail_diffuse.png")])])


def _test_a_whole_kn5_passes(tmp_path):
    p = tmp_path / "t.kn5"
    p.write_bytes(_kn5(*WHOLE))
    r = kt.check(p)
    assert r["ok"] and r["textures_embedded"] == 3 and r["maps"] == 2 and r["unused"] == ["unused.dds"]
    assert kt.main([str(tmp_path), "--json", str(tmp_path / "o.json")]) == 0
    assert json.loads((tmp_path / "o.json").read_text())["ok"] is True


def _test_a_texture_named_and_not_embedded_fails(tmp_path):
    """the PC's 0082-1 run 1: the materials name ghost_alpha.png, the texture section lacks it"""
    p = tmp_path / "t.kn5"
    p.write_bytes(_kn5(WHOLE[0][1:], WHOLE[1]))
    r = kt.check(p)
    assert not r["ok"] and r["missing_textures"] == ["ghost_alpha.png"]
    assert r["missing"][0]["material"] == "1WALL_GHOST_RAIL_0_mat" and r["missing"][0]["case_only"] is False
    assert kt.main([str(p)]) == 1


def _test_case_only_match_is_still_missing(tmp_path):
    p = tmp_path / "t.kn5"
    p.write_bytes(_kn5([("Ghost_Alpha.png", b"x")], [("m", [("txDiffuse", "ghost_alpha.png")])]))
    r = kt.check(p)
    assert not r["ok"] and r["missing"][0]["case_only"] is True


def _test_empty_map_and_zero_byte_texture_fail(tmp_path):
    p = tmp_path / "a.kn5"
    p.write_bytes(_kn5([("a.png", b"x")], [("m", [("txDiffuse", "a.png"), ("txNormal", "")])]))
    assert kt.check(p)["empty"] == [{"material": "m", "sampler": "txNormal"}]
    q = tmp_path / "b.kn5"
    q.write_bytes(_kn5([("a.png", b"")], [("m", [("txDiffuse", "a.png")])]))
    assert kt.check(q)["zero_bytes"] == ["a.png"]
    assert kt.main([str(tmp_path)]) == 1


def _test_version_6_and_input_errors(tmp_path):
    p = tmp_path / "v6.kn5"
    p.write_bytes(_kn5(*WHOLE, version=6))
    assert kt.check(p)["ok"]
    bad = tmp_path / "bad" / "x.kn5"
    bad.parent.mkdir()
    bad.write_bytes(b"not a kn5 at all")
    assert kt.main([str(bad)]) == 2
    assert kt.main([str(tmp_path / "nothing_here")]) == 2
    assert kt.main([str(tmp_path / "bad"), "--recursive"]) == 2


def test_the_gate_is_opt_in():
    """only a ship.json that names kn5_textures runs it; Milford's is the only one so far (ledger 0082 pass 2)"""
    named = sorted(p.parent.name for p in (ROOT / "tracks").glob("*/ship.json")
                   if "kn5_textures" in json.loads(p.read_text(encoding="utf-8"))["steps"].get("gate", []))
    assert named == ["milford-road-course-lm"]
    text = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")
    assert "gate_kn5_textures() {" in text and "python tools/kn5_textures.py \"$PROJ/build\"" in text


# the repo's runner (tests/run_tests.py) calls plain functions: no pytest fixtures, a tempfile directory each
def test_a_whole_kn5_passes():
    with tempfile.TemporaryDirectory() as t:
        _test_a_whole_kn5_passes(Path(t))


def test_a_texture_named_and_not_embedded_fails():
    with tempfile.TemporaryDirectory() as t:
        _test_a_texture_named_and_not_embedded_fails(Path(t))


def test_case_only_match_is_still_missing():
    with tempfile.TemporaryDirectory() as t:
        _test_case_only_match_is_still_missing(Path(t))


def test_empty_map_and_zero_byte_texture_fail():
    with tempfile.TemporaryDirectory() as t:
        _test_empty_map_and_zero_byte_texture_fail(Path(t))


def test_version_6_and_input_errors():
    with tempfile.TemporaryDirectory() as t:
        _test_version_6_and_input_errors(Path(t))
