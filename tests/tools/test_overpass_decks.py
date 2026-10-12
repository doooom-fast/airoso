"""tools/overpass_decks.py — the C-470 bridges over the Lariat lap (V3-PLAN P3a overpass_decks, D5; 2026-10-12).

On a synthetic crossing whose truth is known: a bridge way crossing the lap at right angles, its 3DEP profile the
lap road in a dip between two approach fills 8 m higher. The deck runs between the fill tops (the first points either
side of the crossing ABUTMENT_RISE_M over the ground there), at their heights, measured width, DECK_DEPTH_M deep;
the clearance under it over the lap is reported against 4.9 m; piers stand clear of the lap's pavement; a way whose
fill is past its own end takes the structure's height at the lap. Scenery only: every name is AUTH_overpass_*.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import overpass_decks as od  # noqa: E402
from scripts.geometry.projection import _meters_per_degree  # noqa: E402

LON0, LAT0 = -105.2, 39.72
MLON, MLAT = _meters_per_degree(LAT0)


def ll(x, z):
    return LON0 + x / MLON, LAT0 + z / MLAT


def _project(ways, crossings, width=20.0):
    p = Path(tempfile.mkdtemp())
    (p / "data" / "aerial").mkdir(parents=True)
    lap = [[float(x), 0.0, 0.0] for x in range(-200, 201)]                  # the lap: east along z = 0 at y = 0
    (p / "data" / "centerline.local.json").write_text(json.dumps({
        "origin": {"lon": LON0, "lat": LAT0, "elev_m": 1800.0}, "points_xyz_m": lap, "widths_m": [9.0] * len(lap)}))
    els = [{"type": "way", "id": wid, "tags": {"ref": "CO 470", "lanes": str(lanes), "bridge": "yes", "layer": "1"},
            "geometry": [{"lon": a, "lat": b} for a, b in (ll(x0, z0), ll(x1, z1))]}
           for wid, lanes, (x0, z0, x1, z1) in ways]
    (p / "data" / "osm.widths.cache.json").write_text(json.dumps({"payload": {"elements": els}}))
    (p / "data" / "aerial" / "aerial_measurements.json").write_text(json.dumps({"c470": {
        "osm_crossings": [{"way": w, "crossing_at_m_along_way": at} for w, at in crossings],
        "crossings": [{"window": "X1", "osm_ways_all_on_structure": [w for w, _l, _g in ways],
                       "deck_width_m": {"median": width}}]}}))
    return p


def _sampler(points):
    """3DEP: the lap road at 1800 m in a 40 m-wide dip, the approach fills at 1808 m"""
    out = []
    for lon, lat in points:
        z = (lat - LAT0) * MLAT
        out.append(1800.0 if abs(z) < 20.0 else 1808.0)
    return out


def test_a_deck_between_its_fills_with_its_clearance_reported():
    p = _project([(1, 2, (10.0, -100.0, 10.0, 100.0))], [(1, 100.0)])
    rep = od.build(p, sampler=_sampler)
    assert rep["problems"] == [] and len(rep["decks"]) == 1
    d = rep["decks"][0]
    assert d["name"] == "AUTH_overpass_X1_1" and d["plateaus"] == [True, True] and d["width_m"] == 20.0
    tops = [y for _x, y, _z, _g in d["line_xyz_ground"]]
    assert max(abs(t - 8.0) for t in tops) < 1e-6                           # level between two 8 m fills
    assert 40.0 <= d["length_m"] <= 52.0, d["length_m"]                      # the 40 m gap + a seat each side
    assert d["clearance_over_lap_m"] == round(8.0 - od.DECK_DEPTH_M, 2) and d["clearance_ok_vs_std"]
    for x, y0, z, y1 in d["piers"]:                                            # never on the lap's pavement
        assert abs(z) >= 4.5 + od.PIER_CLEAR_M - 1e-6
    assert (p / "data" / "overpass.elev.json").exists()                       # the samples are cached


def test_a_way_whose_fill_is_past_its_end_takes_the_structures_height():
    ways = [(1, 2, (10.0, -100.0, 10.0, 100.0)), (2, 1, (30.0, -100.0, 30.0, 10.0))]   # 2 ends on the deck
    rep = od.build(_project(ways, [(1, 100.0), (2, 100.0)], width=30.0), sampler=_sampler)
    d2 = next(d for d in rep["decks"] if d["way"] == 2)
    assert d2["plateaus"] == [True, False]
    assert abs(d2["line_xyz_ground"][-1][1] - 8.0) < 1e-6                   # level at the structure's 8 m
    assert {d["way"]: d["width_m"] for d in rep["decks"]} == {1: 20.0, 2: 10.0}    # shared by lane count


def test_no_fill_on_either_side_is_a_problem():
    def flat(points):
        return [1800.0] * len(points)
    rep = od.build(_project([(1, 2, (10.0, -100.0, 10.0, 100.0))], [(1, 100.0)]), sampler=flat)
    assert rep["decks"] == [] and rep["problems"], rep
