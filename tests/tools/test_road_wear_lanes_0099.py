"""Ledger 0099 round 3, item 3: road wear on a street. The bake takes the lanes as its lines (opt-in road_wear.lanes) and
a flat tone on named stretches (opt-in road_wear.tone.flat); the gate tools/road_wear_check.py judges a lanes bake by a
row of its own (lane_rubber), takes the declared lanes off the atlas before its tone row compares it with the photo, and
leaves flat-tone stretches out of that row. No threshold moved.

Held here without numpy and without Blender: the gate's three new pure pieces on made-up roads, the thresholds as they
were, and the bake's wiring by its source. scripts/aerial/road_wear.flat_alpha has its own test beside the module's
(tests/aerial/, numpy). Plain ``test_*`` for tests/run_tests.py."""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RC = _load("road_wear_check_lanes_0099", ROOT / "tools" / "road_wear_check.py")
W = {"track_m": 1.60, "spread_m": 0.55}
AMP = 0.22
# a straight street along x, 200 m long: two lanes a side, their centres 1.825 and 5.475 m off the line
LANES = [([(float(x), y) for x in range(0, 201, 3)], False) for y in (-5.475, -1.825, 1.825, 5.475)]
HALF = 8.0


def test_the_gates_reading_of_the_lanes_is_the_product_over_the_lanes_in_reach():
    dark = RC.make_lane_darkness(LANES, W, AMP)
    reach = 0.5 * W["track_m"] + 4 * W["spread_m"]
    for y in (1.825, 1.825 + 0.8, 0.0, 3.65, 7.0):
        want = 1.0
        for ly in (-5.475, -1.825, 1.825, 5.475):
            d = abs(y - ly)
            if d <= reach:
                want *= 1.0 - AMP * RC.tyre_profile(d, W["track_m"], W["spread_m"])
        assert abs(dark(100.0, y) - (1.0 - want)) < 1e-12, y
    assert dark(100.0, 1.825 + 0.8) > dark(100.0, 3.65) > 0.0            # a wheel path is darker than the divider between two lanes
    assert dark(100.0, 40.0) == 0.0 and dark(-20.0, 1.825) == 0.0        # nothing far off the road or past a lane's end
    # a closed lane's last segment is read too
    ring = [(10.0 * math.cos(a), 10.0 * math.sin(a)) for a in [k * math.pi / 18 for k in range(36)]]
    closed = RC.make_lane_darkness([(ring, True)], W, AMP)
    opened = RC.make_lane_darkness([(ring, False)], W, AMP)
    mid = (10.0 * math.cos(-math.pi / 36), 10.0 * math.sin(-math.pi / 36))      # on the segment that closes the ring
    twin = (10.0 * math.cos(math.pi / 36), 10.0 * math.sin(math.pi / 36))       # the same place on the ring's first segment
    assert abs(closed(*mid) - closed(*twin)) < 1e-12 and closed(*mid) > 0.1
    assert abs(opened(*mid) - closed(*mid)) > 0.01 and abs(opened(*twin) - closed(*twin)) < 1e-12


def test_a_flat_tone_stretch_is_its_line_and_its_half_widths():
    in_flat = RC.make_flat_test([{"line_xy": [[0.0, 0.0], [50.0, 0.0], [50.0, 40.0]], "half_m": [6.0, 10.0, 10.0]}])
    assert in_flat(10.0, 6.5) and not in_flat(10.0, 7.0)                 # the half width is drawn along the segment: 6.8 m at x 10
    assert in_flat(45.0, -9.5) and in_flat(58.0, 20.0) and not in_flat(61.0, 20.0)
    assert in_flat(-3.0, 0.0) and not in_flat(-7.0, 0.0)                 # its ends are round, as the bake's weight reaches them
    assert not RC.make_flat_test([])(0.0, 0.0) and not RC.make_flat_test(None)(0.0, 0.0)


def _road(shipped):
    return lambda x, y: (shipped(x, y) if (0.0 <= x <= 200.0 and abs(y) <= HALF) else None)


def test_lane_rubber_passes_the_bake_it_is_given_and_fails_three_wrong_ones():
    dark = RC.make_lane_darkness(LANES, W, AMP)
    good = RC.lane_rubber_row(LANES, _road(lambda x, y: 0.5 * (1.0 - dark(x, y))), dark)
    assert good["pass"] and good["stations"] == 28                        # every tenth point of four lanes of 67
    assert abs(good["centroid_m"] - good["declared_centroid_m"]) < 1e-9 and abs(good["depth_on_wheel_paths"] - good["declared_depth"]) < 1e-9
    assert good["declared_depth"] > 0.03                                  # the row has something to stand on
    # the photo's tone under it changes nothing the row reads, as long as it is slow across a lane
    toned = RC.lane_rubber_row(LANES, _road(lambda x, y: (0.4 + 0.001 * x) * (1.0 - dark(x, y))), dark)
    assert toned["pass"] and abs(toned["depth_on_wheel_paths"] - good["depth_on_wheel_paths"]) < 1e-6
    # no band at all; a band half a metre off its lanes; a band twice as deep as declared
    none = RC.lane_rubber_row(LANES, _road(lambda x, y: 0.5), dark)
    assert not none["pass"] and none["depth_on_wheel_paths"] == 0.0
    off = RC.lane_rubber_row(LANES, _road(lambda x, y: 0.5 * (1.0 - dark(x, y - 0.5))), dark)
    assert not off["pass"] and abs(off["centroid_m"] - off["declared_centroid_m"]) > RC.GATE["line_offset_max_m"]
    deep = RC.make_lane_darkness(LANES, W, 2.0 * AMP)
    twice = RC.lane_rubber_row(LANES, _road(lambda x, y: 0.5 * (1.0 - deep(x, y))), dark)
    assert not twice["pass"] and twice["depth_on_wheel_paths"] > RC.GATE["depth_max_frac"] * twice["declared_depth"]
    # a road too narrow to hold a lane's section is not judged on nothing
    thin = RC.lane_rubber_row(LANES, lambda x, y: (0.5 if abs(y) < 0.5 else None), dark)
    assert not thin["pass"] and thin["stations"] == 0 and "too few" in thin["note"]


def test_no_threshold_moved_and_the_rows_are_wired_as_the_docstring_says():
    g = RC.GATE
    assert (g["tone_r_min"], g["line_offset_max_m"], g["depth_min_frac"], g["depth_max_frac"]) == (0.60, 0.15, 0.5, 1.5)
    assert (g["density_tol"], g["repeat_m"], g["phase_tol"]) == (0.005, 0.75, 0.002)
    src = (ROOT / "tools" / "road_wear_check.py").read_text(encoding="utf-8")
    for frag in ('lanes_decl = decl.get("lanes")',                                       # the bake's record names the lanes
                 'lane_dark = make_lane_darkness(lane_lines, w, amp * float(ldoc["rubber"]))',
                 "if flats and in_flat(x, y):",                                          # a flat stretch is left out of tone, and counted
                 '"samples_left_out_on_flat_tone_stretches": on_flat',
                 "if line_pts and near_line(x, y) < reach + 0.5:",                       # the racing line's exclusion only where one is declared
                 "atlas_lum(s_[1], s_[2], f) / s_[3]",                                   # the lanes taken off before the comparison
                 'rows["lane_rubber"] = dict(lane_rubber_row(lane_lines, uv_lum, lane_dark)',
                 'abs(c_s - c_d) <= GATE["line_offset_max_m"]',
                 'GATE["depth_min_frac"] * want <= depth <= GATE["depth_max_frac"] * want'):
        assert frag in src, frag
    # with no lanes declared the tone row divides by 1 and the rubber row is the racing line's, as before
    assert "left = (1.0 - lane_dark(x, y)) if lane_dark is not None else 1.0" in src
    assert "if not line_pts:\n            rows.pop(\"rubber\", None)" in src


def test_the_bake_takes_lanes_and_a_flat_tone_only_when_the_config_names_them():
    bake = (ROOT / "tools" / "road_wear_blend.py").read_text(encoding="utf-8")
    for frag in ('lane_spec = spec.get("lanes")',
                 'lanes_on = isinstance(lane_spec, dict) and bool(lane_spec.get("enabled", True))',
                 "road_wear.lanes draws the lanes' wheel paths",                         # drawn mode only
                 'lane_lines = rl.bake_lines(doc, spec["layer_m"])',
                 'line_specs = spec.get("lines") or ([] if lanes_on else',               # no racing line unless one is named
                 '**({"lanes": lanes_rec} if lanes_rec is not None else {})',            # the gate's declaration
                 'flat_rec = _flat_tone(proj, spec["tone"].get("flat"), grid, tone, road)',
                 "road_wear.tone.flat without road_wear.aerial",
                 "sub[...] = (1.0 + (sub - 1.0) * (1.0 - al)).astype(sub.dtype)",        # the lit-asphalt ratio, eased
                 'stats["flat_tone"] = flat_rec'):
        assert frag in bake, frag
    rw = (ROOT / "scripts" / "aerial" / "road_wear.py").read_text(encoding="utf-8")
    assert "def flat_alpha(X: np.ndarray, Y: np.ndarray, P: np.ndarray, half: np.ndarray, ease_m: float) -> np.ndarray:" in rw
    assert "FLAT_SKIRT_M = 2.0 " in rw and "FLAT_EASE_M = 25.0 " in rw and '"flat"' not in rw.split("DEFAULTS = {")[1].split("\n}\n")[0]
