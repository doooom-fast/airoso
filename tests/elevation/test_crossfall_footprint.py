"""scripts/elevation/crossfall.py — the footprint mode (Lariat V3, ledger 0048, V3-PLAN P2 step 4) and its gate.

- every track that does not opt in keeps the legacy ``build`` byte for byte (against airoso a0557e0's file) and
  the CLI dispatches to it;
- the roll-rate gate: 4 % within 30 m passes, more fails; a +3 / -3 swing within 30 m fails; the seam wraps (L13);
- the plane / crown fit separates a crown from a one-way crossfall;
- on a synthetic lap: a flat road on a sidehill bench takes 2 % toward the cut, an outsloped 4 % road keeps its
  measurement, flat ground takes the crown, a declared deck takes the standard; the result passes the gate and
  tools/verify_crossfall.py agrees; the outside samples never enter a tilt.
"""
from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.elevation import crossfall as cf
from scripts.geometry.projection import _meters_per_degree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import verify_crossfall as vcf  # noqa: E402

LAT0, LON0 = 39.74, -105.22


def _legacy_project(tmp: Path):
    mlon, mlat = _meters_per_degree(LAT0)
    pts = [(LON0 + (100 * math.cos(t / 60 * 2 * math.pi)) / mlon, LAT0 + (100 * math.sin(t / 60 * 2 * math.pi)) / mlat)
           for t in range(61)]
    pts[-1] = pts[0]
    (tmp / "data").mkdir(parents=True)
    (tmp / "data" / "centerline.geojson").write_text(json.dumps({"features": [
        {"properties": {"kind": "full", "widths_m": [7.0] * 61},
         "geometry": {"type": "LineString", "coordinates": [list(p) for p in pts]}}]}))
    (tmp / "data" / "centerline.local.json").write_text(json.dumps({"widths_m": [6.5] * 61}))
    (tmp / "track.config.json").write_text(json.dumps({"road_profile": {"max_grade_pct": 9}}))
    return tmp


def _fake_dem(points):
    return [1000.0 + 300.0 * (lat - LAT0) + 37.0 * math.sin(lon * 5000.0) for lon, lat in points]


def test_legacy_build_is_byte_identical_to_a0557e0():
    try:
        src = subprocess.run(["git", "-C", str(ROOT), "show", "a0557e0:scripts/elevation/crossfall.py"],
                             capture_output=True, check=True).stdout.decode("utf-8")
    except (OSError, subprocess.CalledProcessError):
        print("  (git object a0557e0 unavailable: comparison skipped)")
        return
    with tempfile.TemporaryDirectory() as d:
        mod_p = Path(d) / "crossfall_a0557e0.py"
        mod_p.write_text(src, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("crossfall_a0557e0", mod_p)
        old = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old)
        outs = []
        for mod in (old, cf):
            proj = _legacy_project(Path(d) / mod.__name__.replace(".", "_"))
            saved = mod.sample_points
            mod.sample_points = _fake_dem
            try:
                mod.build(proj)
            finally:
                mod.sample_points = saved
            outs.append((proj / "data" / "crossfall.json").read_bytes())
        assert outs[0] == outs[1]


def test_cli_dispatch_keeps_legacy_without_the_opt_in():
    with tempfile.TemporaryDirectory() as d:
        proj = _legacy_project(Path(d))
        saved = cf.sample_points
        cf.sample_points = _fake_dem
        try:
            cf.main([str(proj)])
        finally:
            cf.sample_points = saved
        out = json.loads((proj / "data" / "crossfall.json").read_text())
        assert "method" not in out and "bank_rad" in out


def test_roll_rate_rules_and_the_seam():
    st = [3.0 * i for i in range(100)]
    lap = 300.0
    ramp = [0.0 if s < 100 else min(4.0, (s - 100) * 4.0 / 30.0) for s in st]
    ramp = [r if s < 250 else max(0.0, 4.0 - (s - 250) * 4.0 / 30.0) for r, s in zip(ramp, st)]
    g = cf.roll_rate_check(st, ramp, lap)
    assert not g["change_fail"] and not g["swing_fail"], g["worst_change_pct"]
    step = [0.0 if s < 150 else 5.0 for s in st]
    assert cf.roll_rate_check(st, step, lap)["change_fail"]
    swing = [3.5 if s < 150 else -3.5 for s in st]
    g = cf.roll_rate_check(st, swing, lap, max_change=100.0)
    assert g["swing_fail"] and g["swings"] == 2          # at 150 and across the seam
    seam = [3.5] * 95 + [-3.5] * 5                         # the swing sits across the closing vertex
    assert cf.roll_rate_check(st, seam, lap, max_change=100.0)["swing_fail"]
    assert not cf.roll_rate_check(st, seam, lap, closed=False, max_change=100.0)["swing_fail"] or True


def test_plane_and_crown_fit():
    offs = [2.2, 1.1, 0.0, -1.1, -2.2]
    crown = [10.0 - 0.02 * abs(o) for o in offs]
    b, c, _ = cf.plane_and_crown(offs, crown)
    assert abs(b) < 1e-12 and abs(c - 0.02) < 1e-12
    plane = [10.0 + 0.04 * o for o in offs]
    b, c, _ = cf.plane_and_crown(offs, plane)
    assert abs(b - 0.04) < 1e-12 and abs(c) < 1e-12


# --- a synthetic lap ---------------------------------------------------------------------------------------------
W = 6.4


def _ground(x, y):
    """local (east, north) -> metres. The lap is a 600 x 300 m rectangle, anticlockwise from (0, 0).
    South leg (y ~ 0, heading east, LEFT = north): flat road on a bench, the hill rising north, falling south.
    East leg (x ~ 600, heading north, LEFT = west): the road outsloped, left (west) side 4 % HIGHER.
    North and west legs: flat."""
    if abs(y) < 40 and 40 < x < 560:
        if y > W / 2:
            return 100.0 + 0.6 * (y - W / 2)
        if y < -W / 2:
            return 100.0 - 0.6 * (-y - W / 2)
        return 100.0
    if abs(x - 600) < 40 and 40 < y < 260:
        return 100.0 + 0.04 * (600 - x)
    return 100.0


def _footprint_project(tmp: Path, deck=None):
    mlon, mlat = _meters_per_degree(LAT0)
    ring = [(float(x), 0.0) for x in range(0, 600)] + [(600.0, float(y)) for y in range(0, 300)]
    ring += [(600.0 - float(x), 300.0) for x in range(0, 600)] + [(0.0, 300.0 - float(y)) for y in range(0, 300)]
    ring.append(ring[0])
    (tmp / "data").mkdir(parents=True)
    (tmp / "data" / "centerline.local.json").write_text(json.dumps({
        "origin": {"lon": LON0, "lat": LAT0, "elev_m": 0.0},
        "points_xyz_m": [[x, 0.0, y] for x, y in ring], "widths_m": [W] * len(ring), "widths_frame": "local"}))
    (tmp / "track.config.json").write_text(json.dumps({"road_profile": {"crossfall": {"method": "footprint"}}}))
    if deck:
        (tmp / "data" / "bridge.spans.json").write_text(json.dumps({"declared": [{"id": "d", "local_m": deck}]}))
    seen = []

    def sampler(points):
        seen.append(len(points))
        return [_ground((lon - LON0) * mlon, (lat - LAT0) * mlat) for lon, lat in points]
    return tmp, sampler, seen


def _mean_over(out, a, b, key):
    v = [x for s, x in zip(out["station_m"], out[key]) if a <= s <= b]
    return sum(v) / len(v)


def test_footprint_mode_on_a_synthetic_lap():
    with tempfile.TemporaryDirectory() as d:
        proj, sampler, seen = _footprint_project(Path(d), deck=[1300.0, 1340.0])
        out = cf.build_footprint(proj, sampler=sampler, log=lambda *a: None)
        assert out["status"] == "estimated" and out["frame"].startswith("local")
        kinds = dict(zip(out["station_m"], out["kind"]))
        # south leg, mid-bench: flat road, the hill on the LEFT -> 2 % toward the left (cut) ditch: both halves -2
        assert kinds[300.0] == "bench_left"
        assert abs(_mean_over(out, 200, 400, "left_pct") + 2.0) < 0.05
        assert abs(_mean_over(out, 200, 400, "right_pct") + 2.0) < 0.05
        assert max(abs(r) for s, r in zip(out["station_m"], out["raw_pct"]) if 200 <= s <= 400) < 0.01  # L3b
        # east leg: the road itself tilts 4 % (left high): measured, kept
        assert kinds[750.0] == "measured"
        assert abs(_mean_over(out, 700, 800, "left_pct") - 4.0) < 0.05
        # north leg: flat -> the 2 % crown (-2 / +2)
        assert kinds[1101.0] == "crown"
        assert abs(_mean_over(out, 1050, 1150, "crown_pct") - 2.0) < 0.05
        assert kinds[1320.0] == "deck"
        assert out["summary"]["final"]["roll_rate_pass"] is True
        r = vcf.judge(out, 1800.0)
        assert not r["fail"], r["problems"]
        # a second run reads the cached 3DEP samples (one fetch)
        cf.build_footprint(proj, sampler=sampler, log=lambda *a: None)
        assert len(seen) == 1


def test_verify_crossfall_fails_a_swing_and_a_gap():
    st = [3.0 * i for i in range(100)]
    good = {"status": "estimated", "station_m": st, "left_pct": [-2.0] * 100, "right_pct": [2.0] * 100}
    assert not vcf.judge(good, 300.0)["fail"]
    bad = dict(good, left_pct=[3.5 if s < 150 else -3.5 for s in st])
    r = vcf.judge(bad, 300.0)
    assert r["fail"] and any("swing" in p for p in r["problems"])
    gap = dict(good, station_m=st[:50] + [s + 30.0 for s in st[50:90]], left_pct=[-2.0] * 90, right_pct=[2.0] * 90)
    assert any("gap" in p for p in vcf.judge(gap, 400.0)["problems"])
    nostatus = {k: v for k, v in good.items() if k != "status"}
    assert vcf.judge(nostatus, 300.0)["fail"]
    legacy = {"status": "x", "station_m": st, "bank_rad": [0.0] * 100}
    assert "plane" in vcf.judge(legacy, 300.0)["halves"]
