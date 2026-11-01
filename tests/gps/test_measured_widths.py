"""scripts/gps/measured_widths.py — measured > published > OSM widths, in the LOCAL frame (Lariat V3, ledger 0048).

- widths_from_osm's per-vertex widths are geojson-indexed; the local ring is rotated by route.start_at: the
  rotation is derived (never assumed) and undone, and a ring that is not the same line is refused;
- per top-level width_overrides stretch: measured points interpolated (edge lines + one 0.10 m stripe; a town
  street's curb-to-curb pavement), else the published width, else OSM; nested published widths lose to measured;
- widths_from_osm's flares are not laid (listed), and width changes are rate-limited ACROSS the seam (L13).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.geometry.projection import _meters_per_degree
from scripts.gps import measured_widths as mw


def test_rotation_is_derived_and_a_different_line_refused():
    ring = [(float(i), 0.0) for i in range(10)] + [(9.0, 5.0), (0.0, 5.0), (0.0, 0.0)]
    m = len(ring) - 1
    k = 3
    local = [ring[(i + k) % m] for i in range(m)]
    local.append(local[0])
    assert mw.local_rotation(ring, local) == k
    assert mw.rotate_ring(list(range(m)) + [0], k)[:3] == [3, 4, 5]
    bad = list(local)
    bad[5] = (bad[5][0] + 1.0, bad[5][1])
    try:
        mw.local_rotation(ring, bad)
    except ValueError:
        pass
    else:
        raise AssertionError("a moved point is not the same ring")


def test_cyclic_slew_ramps_across_the_seam():
    st = [float(i) for i in range(101)]
    w = [12.0] + [6.0] * 99 + [12.0]                   # wide at v0 only (the closing duplicate equal)
    out = mw.cyclic_slew(w, st, rate=0.25, closed=True)
    assert out[0] == out[-1]
    # the vertex before the seam (v99, 1 m from v0) may be at most 0.25 m narrower than v0's ramp allows
    for i in range(100):
        j = (i + 1) % 100
        assert abs(out[j] - out[i]) <= 0.25 + 1e-9, (i, out[i], out[j])


def _project(tmp: Path, k=2):
    lat0, lon0 = 39.74, -105.22
    mlon, mlat = _meters_per_degree(lat0)
    ring = [(float(x), 0.0) for x in range(0, 400)] + [(400.0, float(y)) for y in range(0, 100)]
    ring += [(400.0 - float(x), 100.0) for x in range(0, 400)] + [(0.0, 100.0 - float(y)) for y in range(0, 100)]
    ring.append(ring[0])
    lonlat = [(lon0 + x / mlon, lat0 + y / mlat) for x, y in ring]
    m = len(ring) - 1
    geo_st = [0.0]
    for i in range(1, len(ring)):
        geo_st.append(geo_st[-1] + ((ring[i][0] - ring[i - 1][0]) ** 2 + (ring[i][1] - ring[i - 1][1]) ** 2) ** 0.5)
    (tmp / "data" / "aerial").mkdir(parents=True)
    (tmp / "data" / "centerline.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"kind": "full", "osm_station_m": geo_st},
         "geometry": {"type": "LineString", "coordinates": [list(p) for p in lonlat]}}]}), encoding="utf-8")
    # widths_from_osm's output: geojson-indexed, 6.0 m everywhere, one 14 m flare at geojson v600
    base = [6.0] * len(ring)
    flared = list(base)
    for i in range(595, 606):
        flared[i] = 14.0
    local_pts = [ring[(i + k) % m] for i in range(m)]
    local_pts.append(local_pts[0])
    (tmp / "data" / "centerline.local.json").write_text(json.dumps({
        "origin": {"lon": lon0, "lat": lat0, "elev_m": 0.0},
        "points_xyz_m": [[x, 0.0, y] for x, y in local_pts],
        "widths_m": flared, "widths_base_m": base}), encoding="utf-8")
    aerial = {"widths": {"stations": [
        {"station_m": 100.0, "segment": "Climb", "usable": True, "edge_line_width_m": {"median": 6.4},
         "pavement_width_m": {"median": 8.0}},
        {"station_m": 300.0, "segment": "Climb", "usable": True, "edge_line_width_m": {"median": 6.8},
         "pavement_width_m": {"median": 9.0}},
        {"station_m": 200.0, "segment": "Climb", "usable": False, "note": "tree shadow"},
        {"station_m": 700.0, "segment": "Golden (town)", "usable": True, "edge_line_width_m": None,
         "pavement_width_m": {"median": 11.0}},
        {"station_m": 750.0, "segment": "Paradise", "usable": True, "edge_line_width_m": None,
         "pavement_width_m": {"median": 5.9}}],
        "hairpin_legs": {"C1": {"entry": {"lap_st_range": [190, 210], "edge_line_width_median": 7.0}}},
        "corner_apexes": {"C1": {"edge_line_width": {"median": 9.0}}}},
        "corners": [{"id": "C1", "apex_lap_st_m": 250.0}]}
    (tmp / "data" / "aerial" / "aerial_measurements.json").write_text(json.dumps(aerial), encoding="utf-8")
    cfg = {"loop": True, "route": {"measured_widths": {"aerial": "data/aerial/aerial_measurements.json",
                                                       "town_segments": ["Golden"]}},
           "width_overrides": [
               {"road": "climb", "st_m": [50, 400], "width_m": 6.7},
               {"road": "nested published", "st_m": [120, 160], "width_m": 5.48},
               {"road": "town", "st_m": [650, 800], "width_m": None},
               {"road": "published only", "st_m": [900, 950], "width_m": 7.5}]}
    (tmp / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return tmp, k


def test_build_precedence_frame_and_flares():
    with tempfile.TemporaryDirectory() as d:
        proj, k = _project(Path(d))
        rec = mw.build(proj, log=lambda *a: None)
        assert rec["local_rotation_vertices"] == k
        loc = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
        w = loc["widths_m"]
        assert loc["widths_frame"] == "local" and w[0] == w[-1]

        def at(local_station):            # 1 m ring: local index = station
            return w[int(round(local_station))]
        # measured: geojson station s -> local s - k; edge lines + 0.10 m stripe
        assert abs(at(100 - k) - 6.5) < 0.02
        assert abs(at(300 - k) - 6.9) < 0.02
        assert abs(at(250 - k) - 9.1) < 0.02                       # the apex
        assert abs(at(140 - k) - 6.5 - (7.1 - 6.5) * (140 - 100) / (200 - 100)) < 0.05   # nested 5.48 loses
        assert abs(at(60) - 6.5) < 0.3                             # held flat to the stretch start (then slewed)
        assert abs(at(700 - k) - 11.0) < 0.02                      # town pavement
        assert abs(at(925) - 7.5) < 0.02                           # published only
        assert abs(at(1000) - 6.0) < 0.02                          # OSM elsewhere; the 14 m flare is not laid
        assert any(r["max_width_m"] == 14.0 for r in rec["osm_flares_not_laid"]["runs"])
        ids = {p["id"] for p in rec["points"]}
        assert {"W100", "W300", "W700", "C1.entry", "C1.apex"} <= ids
        refused = {r["id"] for r in rec["refused"]}
        assert {"W200", "W750"} <= refused                         # shadow; non-town pavement-only
        for i in range(len(w) - 1):
            assert abs(w[i + 1] - w[i]) <= 0.25 + 0.011, i          # slew (1 m spacing), rounding to 0.01
        try:
            mw.build(proj, log=lambda *a: None)
        except SystemExit as e:
            assert "already" in str(e)
        else:
            raise AssertionError("a second run would rotate already-local widths again")


def test_touching_measured_stretches_taper_through_their_boundary():
    with tempfile.TemporaryDirectory() as d:
        proj, k = _project(Path(d))
        cfgp = proj / "track.config.json"
        cfg = json.loads(cfgp.read_text(encoding="utf-8"))
        cfg["width_overrides"][2]["st_m"] = [400, 800]           # the town stretch now touches the climb's end
        cfgp.write_text(json.dumps(cfg), encoding="utf-8")
        mw.build(proj, log=lambda *a: None)
        w = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))["widths_m"]
        s = 500 - k                                                # between W300 (6.9) and W700 (11.0), linearly
        assert abs(w[s] - (6.9 + (11.0 - 6.9) * (500 - 300) / 400)) < 0.05, w[s]


def test_widths_already_in_local_order_are_not_rotated_again():
    """widths_from_osm applies projection's recorded permutation itself since 2026-11-01 (widths_order: local); the
    same world written that way must give the same widths as the geojson-ordered file it used to write."""
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        a, _ka = _project(Path(d1), k=2)
        b, _kb = _project(Path(d2), k=2)
        lb = json.loads((b / "data" / "centerline.local.json").read_text(encoding="utf-8"))
        m = len(lb["points_xyz_m"]) - 1
        lb["source_index"] = [(i + 2) % m for i in range(m)] + [2 % m]
        lb["widths_m"] = mw.rotate_ring(lb["widths_m"], 2)
        lb["widths_base_m"] = mw.rotate_ring(lb["widths_base_m"], 2)
        lb["widths_order"] = "local"
        (b / "data" / "centerline.local.json").write_text(json.dumps(lb), encoding="utf-8")
        mw.build(a, log=lambda *x: None)
        mw.build(b, log=lambda *x: None)
        wa = json.loads((a / "data" / "centerline.local.json").read_text(encoding="utf-8"))["widths_m"]
        wb = json.loads((b / "data" / "centerline.local.json").read_text(encoding="utf-8"))["widths_m"]
        assert wa == wb
