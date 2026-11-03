"""Ledger 0066: tools/lidar_crossfall.py keeps a real road's camber as measured (no deadband, no runoff ramp)."""
import importlib.util
import json
import math
import random
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("lidar_crossfall", ROOT / "tools" / "lidar_crossfall.py")
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)


def _section(tilt_pct, *, n=60, noise=0.01, curb=False, seed=1):
    rnd = random.Random(seed)
    lat = [rnd.uniform(-lc.HALF_M, lc.HALF_M) for _ in range(n)]
    z = [100.0 + tilt_pct / 100.0 * x + rnd.gauss(0, noise) for x in lat]
    if curb:                                   # a few points on a 15 cm curb top at the right edge
        lat += [-4.4, -4.3, -4.2]
        z += [100.0 - tilt_pct / 100.0 * 4.3 + 0.15] * 3
    return lat, z


def test_a_tilted_section_reads_its_tilt_and_drops_the_curb():
    for t in (-5.0, -1.0, 0.0, 2.0, 5.5):
        lat, z = _section(t, curb=True)
        got, sd, kept = lc.fit_tilt(lat, z)
        assert abs(got - t) < 0.3, (t, got)
        assert sd < 0.03 and kept >= 55


def test_too_few_points_is_no_fit():
    lat, z = _section(3.0, n=lc.MIN_POINTS - 1)
    assert lc.fit_tilt(lat, z) is None


def test_compose_keeps_a_fast_real_roll_and_fills_gaps():
    # -1 % to +5.5 % within 21 m: the DEM tool's 0.12 %/m ramp held a roll to 3.6 % per 30 m; this one keeps 6 %
    raw = [-1.0] * 40 + [-1.0 + 6.5 * k / 7 for k in range(8)] + [5.5] * 40 + [None, None] + [5.5] * 10 + [-1.0] * 40
    out = lc.compose(raw)
    assert all(v is not None for v in out)
    st = [3.0 * i for i in range(len(out))]
    worst = lc.roll_worst(st, out, 3.0 * len(out))
    assert 5.0 < worst <= 30.0 * lc.ROLL_RATE + 1e-6, worst
    assert max(out) <= lc.CAP_PCT and abs(out[48 + 41] - 5.5) < 1e-6      # the filled gap reads its neighbours


def test_compose_caps_at_the_legacy_six_percent():
    out = lc.compose([7.5] * 60 + [-7.5] * 60)
    assert max(out) == lc.CAP_PCT and min(out) == -lc.CAP_PCT


def test_a_long_run_without_a_road_fit_is_held_flat():
    gap = int(lc.MAX_GAP_M / lc.STEP_M) + 5
    out = lc.compose([4.0] * 30 + [None] * gap + [4.0] * 30)
    assert abs(out[30 + gap // 2]) < 1e-9
    short = lc.compose([4.0] * 30 + [None] * 3 + [4.0] * 30)
    assert abs(short[31] - 4.0) < 1e-9


def test_a_bank_or_an_overpass_is_not_a_road_fit():
    assert lc.is_road([3.0, 0.03, 50])
    assert not lc.is_road(None)
    assert not lc.is_road([3.0, lc.MAX_SD_M + 0.01, 50])        # a deck overhead mixed in, a median, a curb run
    assert not lc.is_road([lc.MAX_READ_PCT + 1.0, 0.03, 50])    # an embankment's face


def _ring_project(d: Path, bridges=()):
    (d / "data").mkdir()
    pts = [[100.0 * math.cos(2 * math.pi * k / 200), 0.0, 100.0 * math.sin(2 * math.pi * k / 200)] for k in range(200)]
    pts.append(pts[0])
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"origin": {"lon": -104.9, "lat": 39.8, "elev_m": 1500.0}, "points_xyz_m": pts}))
    (d / "track.config.json").write_text(json.dumps({"capture": {"bridges": list(bridges)}}))
    return lc.stations(json.loads((d / "data" / "centerline.local.json").read_text()))[0]


def test_build_from_the_cache_writes_build_meshs_legacy_shape():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        sts = _ring_project(d)
        fits = [[[4.0, 0.01, 50] if i % 2 else None, None] for i in range(len(sts))]
        (d / "data" / "crossfall.lidar.json").write_text(json.dumps(
            {"fingerprint": lc._fingerprint(lc.EPT_DEFAULT, sts), "fits": fits}))
        out = lc.build(d, log=lambda *_: None)
        cf = json.loads((d / "data" / "crossfall.json").read_text())
        assert cf["status"] == "measured" and cf["method"] == "lidar"
        assert len(cf["station_m"]) == len(cf["bank_rad"]) == len(sts)
        assert all(abs(b - math.atan(0.04)) < 1e-4 for b in cf["bank_rad"])
        assert out["summary"]["dropped_stations"] == len(sts) // 2


def test_a_declared_bridge_reads_its_deck_and_never_the_ground_under_it():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        sts = _ring_project(d, bridges=[{"center_m": 300.0, "len_m": 60.0}])
        fits = [[[-2.0, 0.02, 50], [3.0, 0.02, 40]] for _ in sts]     # ground says -2 %, the deck +3 %
        (d / "data" / "crossfall.lidar.json").write_text(json.dumps(
            {"fingerprint": lc._fingerprint(lc.EPT_DEFAULT, sts), "fits": fits}))
        cf = lc.build(d, log=lambda *_: None)
        tilt = dict(zip(cf["station_m"], cf["tilt_pct"]))
        assert abs(tilt[300.0] - 3.0) < 1e-6 and abs(tilt[150.0] + 2.0) < 1e-6


def test_the_dem_tool_leaves_a_lidar_file_alone():
    spec2 = importlib.util.spec_from_file_location("crossfall_0066", ROOT / "scripts" / "elevation" / "crossfall.py")
    cfm = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(cfm)
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "data").mkdir()
        (d / "track.config.json").write_text(json.dumps({"road_profile": {"crossfall": {"method": "lidar"}}}))
        (d / "data" / "crossfall.json").write_text('{"status": "measured"}')
        assert cfm.main([str(d)]) == 0
        assert json.loads((d / "data" / "crossfall.json").read_text()) == {"status": "measured"}
