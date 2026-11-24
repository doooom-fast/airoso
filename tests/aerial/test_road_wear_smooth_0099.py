"""Ledger 0099 round 3, item 3 (after the first trial bake's look), scripts/aerial/road_wear.py:

* ``smooth_tone`` (opt-in ``road_wear.tone.smooth_m``): the photo's tone without what is smaller than smooth_m. A car, a
  crosswalk and a shadow's ragged edge go; a whole-width patch of older asphalt stays;
* ``tone_field`` samples the photo in bands of rows: the same numbers as one call, bit for bit;
* ``wear_at`` lays nothing past the ends of a line that asks for square ends (``butt_ends``: tools/road_lanes.py
  bake_lines under LANE ENDS), and a line that does not ask is as it was.

numpy, as the module."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.aerial import road_wear as rw  # noqa: E402

RES = 0.5


def _road():
    """A 40 m wide road along x, 240 m long, on a 300 x 80 m grid at 0.5 m: the first 120 m at tone 1.0, the rest an
    older patch at 0.85; a car, a crosswalk and a row of parked cars on it."""
    ny, nx = 160, 600
    y = (np.arange(ny) + 0.5) * RES; x = (np.arange(nx) + 0.5) * RES
    X, Y = np.meshgrid(x, y)
    road = (Y >= 20) & (Y < 60) & (X >= 30) & (X < 270)
    t = np.where(X < 150, 1.0, 0.85).astype(np.float32)
    car = (X >= 80) & (X < 85) & (Y >= 38) & (Y < 40)                    # 5 x 2 m, dark
    walk = (X >= 100) & (X < 103.5) & road                               # 3.5 m of crosswalk and stop bar across the road
    parked = (X >= 180) & (X < 240) & (Y >= 20) & (Y < 22)               # 60 m of parked cars along one edge
    t[car] = 0.70; t[walk] = 1.30; t[parked] = 0.70
    return X, Y, road, t, car, walk, parked


def test_a_car_and_a_crosswalk_go_and_a_patch_of_older_asphalt_stays():
    X, Y, road, t, car, walk, parked = _road()
    out, st = rw.smooth_tone(t, road, RES, 8.0)
    assert out.shape == t.shape and out.dtype == np.float32
    assert (st["smooth_m"], st["window_m"], st["node_m"], st["min_lit_share"], st["min_lit_m2"]) == (8.0, 16.0, 4.0, 0.375, 96.0)
    assert rw.SMOOTH_MIN_LIT_SHARE == 0.375
    assert np.abs(out[car] - 1.0).max() < 1e-6                           # the car is gone entirely: never half a window
    assert np.abs(out[walk] - 1.0).max() < 1e-6                          # so is the crosswalk (3.5 m of a 16 m window)
    mid = road & (Y >= 30) & (Y < 50)
    assert np.abs(out[mid & (X < 135)] - 1.0).max() < 1e-6 and np.abs(out[mid & (X >= 165)] - 0.85).max() < 1e-6
    step = out[int(40 / RES), int(135 / RES):int(165 / RES)]             # the patch's edge: one smooth step, nothing sharper
    assert np.all(np.diff(step) <= 1e-7) and np.abs(np.diff(step)).max() < 0.15 * RES / 4.0 + 1e-6
    # a row of parked cars 2 m wide along the edge: a quarter of what a node on the edge reads, and a node far enough outside
    # to read mostly parked cars is under the share and filled from the road: the edge keeps the road's tone
    assert np.abs(out[parked] - 0.85).max() < 1e-6
    # off the road the field is filled from the road, never left at the photo's own value or at nothing
    assert np.isfinite(out).all() and 0.85 - 1e-6 <= out.min() and out.max() <= 1.0 + 1e-6
    assert st["nodes_measured"] > 0 and st["nodes_under_min_lit"] >= 0
    assert st["nodes_measured"] + st["nodes_under_min_lit"] == st["nodes_with_lit_asphalt"]
    # what is not lit asphalt is not read: the same road with a shadow masked out of ``lit`` gives the lit asphalt's tone
    shadow = road & (X >= 200) & (X < 212)
    t2 = t.copy(); t2[shadow] = 0.70
    out2, _ = rw.smooth_tone(t2, road & ~shadow, RES, 8.0)
    assert np.abs(out2[shadow & (Y >= 30) & (Y < 50)] - 0.85).max() < 1e-6


def test_a_thing_as_big_as_the_scale_is_kept_and_a_smaller_scale_keeps_more():
    X, Y, road, t, car, walk, parked = _road()
    patch = road & (X >= 50) & (X < 62)                                  # 12 m of the whole width: over smooth_m
    t = np.where(patch, 0.80, t).astype(np.float32)
    out, _ = rw.smooth_tone(t, road, RES, 8.0)
    assert abs(float(out[int(40 / RES), int(56 / RES)]) - 0.80) < 0.03   # its middle keeps its tone
    fine, _ = rw.smooth_tone(t, road, RES, 2.0)                          # a 4 m window: the 3.5 m crosswalk is most of it
    assert float(fine[int(40 / RES), int(101.75 / RES)]) > 1.2 and float(out[int(40 / RES), int(101.75 / RES)]) < 1.01


def test_the_photo_sampled_in_bands_is_the_photo_sampled_at_once():
    rng = np.random.default_rng(84)
    img = (rng.random((90, 130, 3)) * 255).astype(np.uint8)
    aer = rw.Aerial(img, (-105.001, 39.999, -104.999, 40.001), (-105.0, 40.0))
    grid = rw.Grid(-60.0, -70.0, 250, 300, 0.5)
    road = np.zeros((300, 250), dtype=bool); road[40:260, 90:160] = True
    spec = dict(rw.DEFAULTS["tone"])
    keep = rw.TONE_BAND_ROWS
    try:
        rw.TONE_BAND_ROWS = 10 ** 9
        whole, s_whole = rw.tone_field(aer, grid, road, spec)
        rw.TONE_BAND_ROWS = 7
        bands, s_bands = rw.tone_field(aer, grid, road, spec)
    finally:
        rw.TONE_BAND_ROWS = keep
    assert np.array_equal(whole, bands) and s_whole == s_bands and "smooth" not in s_whole
    # and one call of the sampler over the whole grid is what a band holds
    X, Y = grid.centres(0, 0, grid.nx, grid.ny)
    one = aer.sample(X, Y)
    Xb, Yb = grid.centres(0, 21, grid.nx, 7)
    assert np.array_equal(one[21:28], aer.sample(Xb, Yb), equal_nan=True)
    # the opt-in key is read off the tone spec and recorded
    sm, s_sm = rw.tone_field(aer, grid, road, dict(spec, smooth_m=8.0))
    assert s_sm["smooth"]["smooth_m"] == 8.0 and sm.shape == whole.shape and float(np.ptp(sm[road])) < float(np.ptp(whole[road]))


def test_a_line_with_square_ends_lays_nothing_past_them():
    w = dict(rw.DEFAULTS["wear"], spread_m=0.55)
    reach = 0.5 * w["track_m"] + 4 * w["spread_m"]
    P = np.array([[x, 0.0, 0.0] for x in np.arange(0.0, 30.1, 3.0)])
    I = np.ones(len(P))
    xs = np.array([-2.0, -0.5, 0.0, 0.5, 15.0, 29.5, 30.0, 30.5, 32.0])
    X, Y = np.meshgrid(xs, np.array([0.8, -0.8, 0.0]))
    round_ = rw.wear_at(X, Y, None, {"P": P, "I": I, "closed": False}, w, reach)
    square = rw.wear_at(X, Y, None, {"P": P, "I": I, "closed": False, "butt_ends": True}, w, reach)
    inside = (xs >= 0.0) & (xs < 30.0)            # the plane through the last point belongs to whatever starts there
    assert np.array_equal(round_[:, inside], square[:, inside]) and (square[:, inside] > 0).all()
    assert not square[:, ~inside].any() and (round_[:, ~inside] > 0).all()        # the horseshoe a round end draws
    assert abs(float(square[0, 4]) - w["amplitude"]) < 1e-6                       # a wheel path at full rubber
    # the share runs along the line as the rubber does: half the rubber, half the darkening; nothing where it is nothing
    half = rw.wear_at(X, Y, None, {"P": P, "I": 0.5 * I, "closed": False, "butt_ends": True}, w, reach)
    assert np.allclose(half, 0.5 * square)
    ramp = np.linspace(0.0, 1.0, len(P))
    faded = rw.wear_at(X, Y, None, {"P": P, "I": ramp, "closed": False, "butt_ends": True}, w, reach)
    assert float(faded[0, 2]) == 0.0 and abs(float(faded[0, 4]) - 0.5 * w["amplitude"]) < 1e-6
    # two lanes welded end to end meet in a plane: together they are one line
    A = {"P": P[:6], "I": I[:6], "closed": False, "butt_ends": True}
    B = {"P": P[5:], "I": I[5:], "closed": False, "butt_ends": True}
    Xj, Yj = np.meshgrid(np.arange(12.0, 18.01, 0.25) + 0.125, np.array([0.8, 0.3, -1.1]))
    both = 1.0 - (1.0 - rw.wear_at(Xj, Yj, None, A, w, reach)) * (1.0 - rw.wear_at(Xj, Yj, None, B, w, reach))
    one = rw.wear_at(Xj, Yj, None, {"P": P, "I": I, "closed": False, "butt_ends": True}, w, reach)
    assert np.allclose(both, one, atol=1e-7)
    # a closed line has no end: the flag changes nothing
    ring = np.array([[10 * np.cos(a), 10 * np.sin(a), 0.0] for a in np.arange(0, 2 * np.pi, np.pi / 18)])
    Xr, Yr = np.meshgrid(np.linspace(-12, 12, 25), np.linspace(-12, 12, 25))
    assert np.array_equal(rw.wear_at(Xr, Yr, None, {"P": ring, "I": np.ones(len(ring)), "closed": True}, w, reach),
                          rw.wear_at(Xr, Yr, None, {"P": ring, "I": np.ones(len(ring)), "closed": True, "butt_ends": True}, w, reach))


def test_bake_lines_hand_the_bake_the_share_the_bridge_and_square_ends():
    spec = importlib.util.spec_from_file_location("road_lanes_smooth_0099", ROOT / "tools" / "road_lanes.py")
    rl = importlib.util.module_from_spec(spec); spec.loader.exec_module(rl)
    a = {"id": "a/forward/1/0", "road": "a", "closed": False, "length_m": 60.0,
         "points_xyz_m": [[float(x), 2.0, 5.0] for x in range(0, 61, 3)]}
    b = {"id": "b/forward/1/0", "road": "b", "closed": False, "length_m": 60.0,
         "points_xyz_m": [[float(x), 2.0, 5.0] for x in range(63, 124, 3)]}
    doc = {"rubber": 0.5, "lanes": [a, b]}
    plain = rl.bake_lines(doc, 10.0)
    assert [len(ln["P"]) for ln in plain] == [21, 21] and all("butt_ends" not in ln for ln in plain)
    assert all(np.array_equal(ln["I"], np.full(21, 0.5)) for ln in plain)
    doc["ends"] = rl.lane_ends(doc["lanes"], dict(rl.ENDS_DEFAULTS))
    got = rl.bake_lines(doc, 10.0)
    assert all(ln["butt_ends"] is True and not ln["closed"] for ln in got)
    assert len(got[0]["P"]) == 22 and got[0]["P"][-1].tolist() == [63.0, 5.0, 2.0]        # Blender x, y = north, height
    assert got[0]["I"][0] == 0.0 and got[0]["I"][-1] == 0.5 and got[0]["I"][-2] == 0.5
    assert got[1]["I"][0] == 0.5 and got[1]["I"][-1] == 0.0 and len(got[1]["P"]) == 21
