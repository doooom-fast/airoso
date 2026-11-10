"""tools/make_treefx.py's gate (ledger 0089): a fresh workshop without the gitignored TreeFX models planted 0 trees on the
PC and every gate stayed green. build() now fails when fewer trees are written than the plan places with every model
present, when a model trees.txt names is not beside it, or when a planted track's native sizes are still placeholders
while the copied models are real. The gate only reads: what build() writes is unchanged."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import make_treefx as mt  # noqa: E402


def _project(bins=("PalmV1.bin", "PalmV2.bin", "PalmV3.bin"), planted=None, size=3):
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "source" / "trees").mkdir(parents=True)
    for b in bins:
        (d / "source" / "trees" / b).write_bytes(b"b" * size)
    cfg = {"slug": "tiny"}
    if planted:
        cfg["scenery"] = {"treefx": {"planted": planted}}
    (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    o = {"lon": -115.0, "lat": 36.28, "elev_m": 600.0}
    pts = [[float(x), 0.0, 0.0] for x in range(0, 201, 5)]
    (d / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": pts, "widths_m": [10.0] * len(pts),
                                                                  "origin": o}))
    palms = [{"x": 20.0, "y": 0.0, "z": 9.0}, {"x": 60.0, "y": 0.0, "z": -12.0}, {"x": 140.0, "y": 0.5, "z": 30.0}]
    (d / "data" / "scatter_positions.json").write_text(json.dumps({"palms": [] if planted else palms, "trees": [],
                                                                   "scrub": [], "median_planting": []}))
    (d / "data" / "track.obj").write_text("o 1GRASS_0\nusemtl 1GRASS_0_mat\nv 0 0 0\no 1ROAD_road\nusemtl 1ROAD_road_mat\n",
                                          encoding="utf-8")
    if planted:
        # a 3 x 3 heightfield around the origin (the planted path reads the ground under each point off it)
        (d / "data" / "heightfield.meta.json").write_text(json.dumps({"bbox_swne": [36.27, -115.01, 36.29, -114.99]}))
        import struct
        hdr = "{'descr': '<f8', 'fortran_order': False, 'shape': (3, 3), }"
        hdr += " " * (118 - len(hdr)) + "\n"
        (d / "data" / "heightfield.npy").write_bytes(b"\x93NUMPY\x01\x00" + struct.pack("<H", len(hdr)) + hdr.encode()
                                                    + struct.pack("<9d", *([600.0] * 9)))
    return d


def _fails(d):
    try:
        mt.build(d)
    except SystemExit as e:
        return str(e)
    return None


def test_every_model_present_passes_and_writes_the_plan():
    d = _project()
    p = mt.plan(d)
    assert _fails(d) is None
    written = (d / "build" / "tiny" / "extension" / "trees" / "trees.txt").read_text(encoding="utf-8")
    assert written == "\n".join(p["lines"]) + "\n"
    g = mt.treefx_gate(d, p, d / "build" / "tiny" / "extension" / "trees")
    assert g["planned"] == g["written"] == 3 and not g["problems"] and not g["absent"]


def test_no_models_plants_nothing_and_fails():
    """the PC's fresh worktree: no .bin at all -> 0 written of 3 planned -> the chain stops"""
    why = _fails(_project(bins=()))
    assert why and "GATE FAIL" in why and "0 trees written, 3 planned" in why


def test_a_zone_short_of_one_model_still_plants_every_spot_and_warns():
    """PalmV2 / V3 absent: every palm spot takes PalmV1 (the count is the plan's), so the gate passes and names them"""
    d = _project(bins=("PalmV1.bin",))
    assert _fails(d) is None
    g = mt.treefx_gate(d, mt.plan(d), d / "build" / "tiny" / "extension" / "trees")
    assert g["written"] == g["planned"] == 3 and not g["problems"]
    assert set(g["mix_missing"]) <= {"PalmV2.bin", "PalmV3.bin"}       # whichever the full mix would have picked here


def test_a_named_model_missing_beside_trees_txt_fails():
    d = _project()
    mt.build(d)
    tdir = d / "build" / "tiny" / "extension" / "trees"
    p = mt.plan(d)
    victim = sorted(p["used"])[0]
    (tdir / victim).unlink()
    g = mt.treefx_gate(d, p, tdir)
    assert g["absent"] == [victim] and g["problems"]


def _planted(native_placeholder):
    pl = {"file": "source/pts.json", "clear_m": 4.0, "zones": {"0": "planted_desert_scrub"},
          "native_h_m": {"Bush.bin": 2.0, "Bush3.bin": 2.0}, "native_w_m": {"Bush.bin": 2.0, "Bush3.bin": 2.0}}
    if native_placeholder:
        pl["native_h_m"]["_placeholder"] = "read on the PC"
    return pl


def _with_points(d):
    # two shrubs 30 m off the road, one ON it (dropped by clear_m, in the plan and the build alike)
    m_lat = 111_132.92 - 559.82 * __import__("math").cos(2 * __import__("math").radians(36.28))
    pts = [[-115.0, 36.28 + 30 / m_lat, 0, 1.5, 2.0, 0], [-115.0 + 0.0003, 36.28 + 35 / m_lat, 0, 1.0, 1.2, 1],
           [-115.0 + 0.0005, 36.28, 0, 1.2, 1.4, 2]]
    (d / "source" / "pts.json").write_text(json.dumps({"cols": 1, "rows": 1, "points": pts}))
    return d


def test_planted_sizes_by_measured_height_and_crown():
    d = _with_points(_project(bins=("Bush.bin", "Bush3.bin"), planted=_planted(False)))
    assert _fails(d) is None
    lines = [ln for ln in (d / "build" / "tiny" / "extension" / "trees" / "trees.txt").read_text().splitlines()
             if ln.startswith("tree:")]
    assert len(lines) == 2
    sizes = sorted(float(ln.split("size = ")[1].split(";")[0]) for ln in lines)
    assert sizes == [0.5, 0.75]                    # 1.0 m / 2.0 and 1.5 m / 2.0: the measured height, absolute
    assert all("; width = " in ln for ln in lines)


def test_placeholder_native_sizes_refuse_real_models_only():
    """the Mac's 82 B stand-ins pass; a real model (> PLACEHOLDER_MAX_B) with the placeholder still in the config fails"""
    small = _with_points(_project(bins=("Bush.bin", "Bush3.bin"), planted=_planted(True)))
    assert _fails(small) is None
    real = _with_points(_project(bins=("Bush.bin", "Bush3.bin"), planted=_planted(True), size=mt.PLACEHOLDER_MAX_B + 1))
    why = _fails(real)
    assert why and "placeholders" in why
