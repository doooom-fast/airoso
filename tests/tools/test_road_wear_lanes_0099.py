"""Ledger 0099 round 3, item 3: road wear on a street. The bake takes the lanes as its lines (opt-in road_wear.lanes) and
a flat tone on named stretches (opt-in road_wear.tone.flat); the gate tools/road_wear_check.py judges a lanes bake by a
row of its own (lane_rubber), takes the declared lanes off the atlas before its tone row compares it with the photo, and
leaves flat-tone stretches out of that row. No threshold moved.

Held here without numpy and without Blender: the gate's three new pure pieces on made-up roads, the thresholds as they
were, and the bake's wiring by its source. scripts/aerial/road_wear.flat_alpha has its own test beside the module's
(tests/aerial/, numpy). Plain ``test_*`` for tests/run_tests.py."""
from __future__ import annotations

import importlib.util
import json
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


# ---- Lake Murray's own key (0.20.7) --------------------------------------------------------------------------------------

def test_lake_murrays_road_wear_is_lanes_at_half_a_metre_with_the_flat_tone_on_the_measured_bins():
    import json
    lm = ROOT / "tracks" / "san-diego-lake-murray"
    cfg = json.loads((lm / "track.config.json").read_text(encoding="utf-8"))
    ship = json.loads((lm / "ship.json").read_text(encoding="utf-8"))
    rw = cfg["road_wear"]
    assert cfg["version"] == "0.20.7" and rw["surfaces"] == ["1ROAD"] and "lines" not in rw and "rubber" not in rw   # lanes only, drawn
    # Kevin 2026-11-23: "50 cm now". One 8192 atlas: the detail's phase and a tile's pitch are both whole
    assert rw["texel_m"] == 0.5 and "50 cm now" in rw["_texel_doc"]
    assert (8192 * rw["texel_m"] / 4.0) == 1024.0 and ((64 + 2 * 16) / rw["texel_m"]) == 192.0
    assert rw["wear"] == {k: v for k, v in rw["wear"].items() if k.startswith("_") or k == "spread_m"} and rw["wear"]["spread_m"] == 0.55
    assert rw["lanes"]["split_zones"] == [{"kind": "college_split", "from": 1130, "to": 1476,
                                           "source": "source/college_r2/college_split.data.json"}]
    # the aerial: the whole-box mosaic, its box off its own georef (62 x 41 tiles of z18)
    g = json.loads((lm / "source" / "naip_2022_lm_full_z18.georef.json").read_text(encoding="utf-8"))
    n = 2 ** g["z"]
    nx, ny = g["w"] // 256, g["h"] // 256

    def lon(tx):
        return tx / n * 360.0 - 180.0

    def lat(ty):
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ty / n))))
    box = [lon(g["x0"]), lat(g["y0"] + ny), lon(g["x0"] + nx), lat(g["y0"])]
    assert rw["aerial"]["image"] == "source/naip_2022_lm_full_z18.jpg" and (nx, ny) == (62, 41)
    assert all(abs(a - b) < 1e-8 for a, b in zip(rw["aerial"]["bbox_lonlat"], box)), box
    # read as linear in latitude (the bake's Aerial), the Mercator mosaic is off by under a texel
    worst = max(abs(lat(g["y0"] + ny * k / 400.0) - (box[3] + (box[1] - box[3]) * k / 400.0)) for k in range(401)) * 111132.0
    assert 0.30 < worst < 0.40 and worst < rw["texel_m"]
    # the flat tone: exactly the bins of piece C whose built road reads non-asphalt on the photo at over 0.12
    tone = json.loads((lm / "source" / "road_wear" / "tone_piece_C.json").read_text(encoding="utf-8"))
    over = [b["s"][0] for b in tone["bins"] if b["samples"] > 500 and b["off_share_of_lit"] > 0.12]
    good = [b["off_share_of_lit"] for b in tone["bins"] if 100 <= b["s"][0] < 600 or 1100 <= b["s"][0] < 1200]
    assert len(over) == 19 and max(good) < 0.08 < 0.12 < min(b["off_share_of_lit"] for b in tone["bins"] if b["s"][0] in over)
    if str(ROOT / "tools") not in sys.path:
        sys.path.insert(0, str(ROOT / "tools"))
    import expansion_pieces as ep
    pc = ep.load(lm / "data" / "expansion.north.json")[1]["C"]
    conn = next(c for c in json.loads((lm / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
                if c["name"] == "north_mission_gorge")
    st = [pc.project(p[0], p[2])[1] for p in conn["points_xyz_m"]]
    rows = sorted(i for i, s in enumerate(st) if any(a <= s < a + 50.0 for a in over))
    flat = rw["tone"]["flat"]
    assert all(f["road"] == "north_mission_gorge" and f["why"] for f in flat)
    assert sorted(i for f in flat for i in range(f["from"], f["to"] + 1)) == rows
    assert [(f["from"], f["to"]) for f in flat] == [(193, 209), (410, 659), (677, 710), (727, 743)]
    # the chain: the aerial and College's data sync in, the gate runs, the records sync out
    for f in ("source/naip_2022_lm_full_z18.jpg", "source/college_r2/college_split.data.json"):
        assert f in ship["sync_in"]["optional"] and (lm / f).is_file(), f
    assert ship["steps"]["gate"][-1] == "road_wear"
    for f in ("data/road_wear.json", "data/road_wear.lanes.json", "data/road_wear_check.json"):
        assert f in ship["sync_out"]["files"], f
    for p in sorted((ROOT / "tracks").glob("*/track.config.json")):       # no other track names lanes or a flat tone
        if p.parent != lm:
            other = json.loads(p.read_text(encoding="utf-8")).get("road_wear") or {}
            assert "lanes" not in other and "flat" not in (other.get("tone") or {}), p


# --- after the first trial bake's look (2026-11-23): lane ends, and the tone smoothed -----------------------------------
def test_the_gate_reads_a_lanes_share_and_lays_nothing_past_a_square_end():
    pts = [(float(x), 0.0) for x in range(0, 31, 3)]
    whole = RC.make_lane_darkness([(pts, False)], W, AMP)                       # as before: uniform, round ends
    share = [0.0, 0.5] + [1.0] * 9
    ends = RC.make_lane_darkness([(pts, False, share, True)], W, AMP)
    peak = AMP * RC.tyre_profile(0.8, W["track_m"], W["spread_m"])
    assert abs(whole(15.0, 0.8) - peak) < 1e-12 and abs(ends(15.0, 0.8) - peak) < 1e-12
    # the share is drawn straight along a segment: 0.25 half way along the first, 0.75 half way along the second
    assert abs(ends(1.5, 0.8) - 0.25 * peak) < 1e-12 and abs(ends(4.5, 0.8) - 0.75 * peak) < 1e-12
    # a round end draws the wheel paths round it; a square end lays nothing past the first and the last point
    assert whole(-0.5, 0.6) > 0.1 and whole(30.5, 0.6) > 0.1
    assert ends(-0.5, 0.6) == 0.0 and ends(30.5, 0.6) == 0.0 and ends(29.9, 0.8) == whole(29.9, 0.8)
    # two welded lanes meet in a plane: together they are the one line
    a = (pts[:6], False, [1.0] * 6, True)
    b = (pts[5:], False, [1.0] * 6, True)
    one = RC.make_lane_darkness([(pts, False, [1.0] * 11, True)], W, AMP)
    two = RC.make_lane_darkness([a, b], W, AMP)
    for x in (13.0, 14.9, 15.0, 15.1, 17.0):
        for y in (0.8, 0.2, -1.3):
            assert abs(two(x, y) - one(x, y)) < 1e-12, (x, y)
    # the row takes lanes that carry a share
    assert RC.lane_rubber_row([(pts, False, [1.0] * 11, True)], lambda x, y: None, one)["pass"] is False


def test_the_tone_row_reads_the_photo_smoothed_only_where_the_bake_smoothed_it():
    src = (ROOT / "tools" / "road_wear_check.py").read_text(encoding="utf-8")
    assert RC.SMOOTH_MIN_SHARE == 0.375 and RC.GATE["tone_r_min"] == 0.60
    assert 'smooth_m = float(spec["tone"].get("smooth_m") or 0.0)' in src
    # without the key the samples are filtered as they always were
    assert "samples = [s_ for s_ in samples if max(0.8, lo) * med <= s_[0] <= hi * med]" in src
    assert '"photo": "smoothed as declared: the median lit-asphalt ratio within +- smooth_m of each sample"' in src
    # the gate's lit asphalt is the bake's rule: a shadow is dark AND blue, paint is bright; the ratio clipped as the bake clips
    assert 'if (a2[0] < tn["shadow_lum"] * med and a2[1] > tn["shadow_blue"]) or a2[0] > tn["paint_lum"] * med:' in src
    assert "vals.append(min(hi, max(lo, a2[0] / med)))" in src
    bake = (ROOT / "scripts" / "aerial" / "road_wear.py").read_text(encoding="utf-8")
    assert "SMOOTH_MIN_LIT_SHARE = 0.375" in bake and 'if spec_tone.get("smooth_m"):' in bake
    assert '"smooth_m":' not in bake.split('    "tone": {')[1].split("    },")[0]                    # no default: opt-in
    cfg = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json").read_text(encoding="utf-8"))
    assert cfg["road_wear"]["tone"]["smooth_m"] == 8.0 and "[invented]" in cfg["road_wear"]["tone"]["_smooth_doc"]
