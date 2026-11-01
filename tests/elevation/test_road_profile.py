"""scripts/elevation/road_profile.py — the road profile smoothed by STATION (Lariat V3, ledger 0048, P2 step 1).

- on a uniformly 3 m line it IS heightfield.snap_to_ground (closed and open), so only the windows' units changed;
- on a 1 m line its windows still span 33 m / 9 m (heightfield's shrink to 11 m / 3 m there);
- a closed lap is rotation-invariant (L13: no seam in the filters) and keeps its closing duplicate equal;
- a declared deck is found from its footprint way, held straight (the trench never enters the filters), refused
  across the seam, and written as capture.bridges in local stations with --write.
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

from scripts.elevation import heightfield
from scripts.elevation import road_profile as rp
from scripts.geometry.projection import _meters_per_degree


def _wavy(n, seed=7):
    """deterministic rough terrain: a climb, a wave, and spikes (pseudo-random, no RNG module state)"""
    z = []
    x = seed
    for i in range(n):
        x = (x * 1103515245 + 12345) % 2 ** 31
        noise = (x / 2 ** 31 - 0.5) * 0.6
        spike = 4.0 if i % 97 == 13 else 0.0
        z.append(100.0 + 0.05 * i + 3.0 * math.sin(i / 25.0) + noise + spike)
    return z


def test_uniform_3m_open_line_equals_heightfield():
    n = 400
    st = [3.0 * i for i in range(n)]
    z = _wavy(n)
    a = heightfield.snap_to_ground(list(z), spacing_m=3.0, grade_cap_pct=6.0, closed=False)
    b = rp.snap_to_ground_stations(list(z), st, grade_cap_pct=6.0, closed=False)
    assert max(abs(p - q) for p, q in zip(a, b)) < 1e-9


def test_uniform_3m_closed_lap_equals_heightfield():
    n = 300
    z = _wavy(n)
    z[-1] = z[0]                          # the closing duplicate
    st = [3.0 * i for i in range(n)]
    a = heightfield.snap_to_ground(list(z), spacing_m=3.0, grade_cap_pct=9.0, closed=True)
    b = rp.snap_to_ground_stations(list(z), st, grade_cap_pct=9.0, closed=True)
    assert max(abs(p - q) for p, q in zip(a, b)) < 1e-9
    assert b[0] == b[-1]


def test_windows_are_metres_on_a_1m_line():
    st = [float(i) for i in range(200)]
    wins = list(rp._window_iter(st, 200.0, 33.0 / 2, closed=False))
    assert len(wins[100]) == 33                       # +-16 m at 1 m: 33 samples, heightfield would take 11
    wins9 = list(rp._window_iter(st, 200.0, 9.0 / 2, closed=False))
    assert len(wins9[100]) == 9


def test_mixed_spacing_does_not_bias_the_filters():
    # a straight 8 % ramp sampled at 1 m, then 3 m: weighted by length, the median and mean return the ramp itself
    # (by vertex count the window would hold 3x more samples on the 1 m side and pull the value toward it)
    st = [float(i) for i in range(0, 200)] + [200.0 + 3.0 * i for i in range(0, 70)]
    z = [0.08 * s for s in st]
    out = rp.snap_to_ground_stations(z, st, grade_cap_pct=16.0, closed=False)
    worst = max(abs(a - b) for a, b, s in zip(out, z, st) if 40.0 <= s <= 360.0)
    assert worst < 0.13, worst                    # within half a 3 m cell of grade (0.08 x 1.5 = 0.12 m)
    naive = [sorted(z[k] for k in idx)[len(idx) // 2] for idx in rp._window_iter(st, st[-1], 16.5, False)]
    assert max(abs(a - b) for a, b, s in zip(naive, z, st) if 40.0 <= s <= 360.0) > 0.5   # the bias it removes


def test_closed_lap_is_rotation_invariant_and_seam_free():
    m = 240                                           # unique vertices, 1 m apart round a circle-ish ring
    z = _wavy(m, seed=3)
    st = [float(i) for i in range(m + 1)]
    # the filters (median, mean) wrap: a non-binding cap isolates them (the cut-only limiter is heightfield's
    # sequential two-wrap clamp, kept as it is)
    out = rp.snap_to_ground_stations(z + [z[0]], st, grade_cap_pct=500.0, closed=True)
    k = 57
    zr = z[k:] + z[:k]
    out_r = rp.snap_to_ground_stations(zr + [zr[0]], st, grade_cap_pct=500.0, closed=True)
    rot = out[k:-1] + out[:k]
    assert max(abs(p - q) for p, q in zip(rot, out_r[:-1])) < 1e-9
    assert out[0] == out[-1]


def test_grade_cap_uses_the_real_segment_length():
    # a 1 m line rising 0.5 m per vertex (50 %) must be cut to the 16 % cap per metre, not per 3 m
    st = [float(i) for i in range(60)]
    z = [0.0] * 30 + [0.5 * (i - 29) for i in range(30, 60)]
    out = rp.snap_to_ground_stations(z, st, grade_cap_pct=16.0, median_m=1.0, mean_m=1.0, closed=False)
    g = max(out[i] - out[i - 1] for i in range(1, 60))
    assert g <= 0.16 + 1e-9, g


def test_deck_span_from_a_footprint_and_held_straight():
    # lap: a straight east-west line, 1 m points; footprint: a north-south way at x = 100, half width 4.5 m
    xy = [(float(i), 0.0) for i in range(201)]
    st = rp.stations(xy)
    span = rp.deck_span(xy, st, [([(100.0, -50.0), (100.0, 50.0)], 4.5)], abutment_m=8.0, closed=False)
    assert abs(span["footprint_a_m"] - 95.5) < 0.3 and abs(span["footprint_b_m"] - 104.5) < 0.3
    assert abs(span["a_m"] - 87.5) < 0.3 and abs(span["b_m"] - 112.5) < 0.3
    assert span["crossings"] and abs(span["crossings"][0]["angle_deg"] - 90.0) < 1e-6
    z = [10.0 + 0.05 * s for s in st]
    for i, s in enumerate(st):                        # a 6 m trench under the deck (bare earth)
        if 96 <= s <= 104:
            z[i] -= 6.0
    held, hs = rp.hold_straight(z, st, span["a_m"], span["b_m"])
    assert hs["max_dip_removed_m"] > 5.9
    for i, s in enumerate(st):
        assert abs(held[i] - (10.0 + 0.05 * s)) < 1e-6


def test_a_deck_across_the_seam_is_refused():
    xy = [(float(i), 0.0) for i in range(101)] + [(100.0, float(j)) for j in range(1, 11)]
    xy += [(100.0 - float(i), 10.0) for i in range(1, 101)] + [(0.0, 10.0 - float(j)) for j in range(1, 11)]
    assert xy[0] == xy[-1]
    st = rp.stations(xy)
    try:
        rp.deck_span(xy, st, [([(2.0, -20.0), (2.0, 20.0)], 4.0)], abutment_m=8.0, closed=True)
    except ValueError as e:
        assert "seam" in str(e)
    else:
        raise AssertionError("a deck straddling the seam must be refused (L13)")


def _project(tmp: Path):
    """A closed rectangular lap in lon/lat crossing a 'tunnel' way, with a trench in the raw samples."""
    lat0, lon0 = 39.74, -105.22
    mlon, mlat = _meters_per_degree(lat0)
    ring = [(float(i), 0.0) for i in range(0, 300, 3)] + [(300.0, float(j)) for j in range(0, 60, 3)]
    ring += [(300.0 - float(i), 60.0) for i in range(0, 300, 3)] + [(0.0, 60.0 - float(j)) for j in range(0, 60, 3)]
    ring.append(ring[0])
    lonlat = [(lon0 + x / mlon, lat0 + y / mlat) for x, y in ring]
    (tmp / "data").mkdir(parents=True)
    (tmp / "data" / "centerline.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"kind": "full", "closed": True},
         "geometry": {"type": "LineString", "coordinates": [list(p) for p in lonlat]}}]}), encoding="utf-8")
    z = []
    for x, y in ring:
        v = 1800.0 + 0.02 * x
        if y == 0.0 and 147.0 <= x <= 153.0:
            v -= 5.0                                   # the bare-earth trench under the lid
        z.append(v)
    (tmp / "data" / "centerline.elevation.json").write_text(json.dumps({"z_raw_m": z, "z_smooth_m": z}),
                                                             encoding="utf-8")
    tunnel = [{"lat": lat0 + y / mlat, "lon": lon0 + 150.0 / mlon} for y in (-40.0, 40.0)]
    (tmp / "data" / "osm.cache.json").write_text(json.dumps({"payload": {"elements": [
        {"type": "way", "id": 11, "tags": {"highway": "trunk", "lanes": "2", "tunnel": "yes"}, "geometry": tunnel}]}}),
        encoding="utf-8")
    cfg = {"loop": True, "route": {"width_profile": "mountain", "start_at": [lat0, lon0 + 30.0 / mlon]},
           "road_profile": {"max_grade_pct": 16.0},
           "bridges": {"declared": [{"id": "lid", "footprint_ways": [11], "abutment_m": 8.0}]}}
    (tmp / "track.config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return tmp


def test_build_holds_the_lid_and_writes_capture_bridges_in_local_stations():
    with tempfile.TemporaryDirectory() as d:
        proj = _project(Path(d))
        r = rp.build(proj, write=True, log=lambda *a: None)
        deck = r["decks"][0]
        # trunk, 2 lanes, mountain profile = 9.0 m pavement: 9 m over the footprint + 2 x 8 m abutments
        assert abs(deck["len_m"] - 25.0) < 0.5, deck
        # start_at is 30 m along: local stations = geojson stations - 30 (the lid at x = 150 -> local ~120)
        assert abs(deck["center_m"] - 120.0) < 0.5, deck
        ej = json.loads((proj / "data" / "centerline.elevation.json").read_text(encoding="utf-8"))
        assert min(ej["z_smooth_m"]) > 1799.9          # the trench never reached the smoothed road
        assert ej["z_raw_m"][50] < 1800.0 + 0.02 * 150 - 4.0   # the raw samples are untouched
        # the raw samples in local index space: projection's ring starts 10 vertices (30 m) along
        assert ej["road_profile"]["local_rotation_vertices"] == 10
        # no second, pre-rotated copy of the raw samples: main's readers map z_raw_m once through projection's
        # recorded permutation (in_local_order; tests/geometry/test_drive_test_raw_local.py)
        assert "z_raw_local_m" not in ej and len(ej["z_raw_m"]) == len(ej["z_smooth_m"])
        cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
        assert cfg["capture"]["bridges"] == [{"id": "lid", "center_m": deck["center_m"], "len_m": deck["len_m"]}]
        rec = json.loads((proj / "data" / "bridge.spans.json").read_text(encoding="utf-8"))
        assert rec["declared"][0]["local_m"][0] > 0 and rec["lap_osm_bridge_ways"] == []
