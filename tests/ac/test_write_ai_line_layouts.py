"""The AI writer's lane policy and frame handling for per-layout drafts (ledger 0047).

Pinned here, on a synthetic 200 m square loop in the ENGINE frame (x=E, z=N, counter-clockwise:
east along the south edge, so right of forward travel on that edge is SOUTH, −z):

* the lane policy numbers from the spec (17 m road beside the 0.67 m chain with 0.82 m inset →
  4.0 m; no divider → 0),
* a forward line beside a divider runs RIGHT of it; the reverse layout runs right of ITS travel
  (the other carriageway) — a distinct line, never the forward one reversed,
* without any divider the line is the centreline with symmetric sides — the pre-0047 behaviour,
* the write-time clearance check refuses a line on an island or on the wrong side,
* the finished line's frame is detected (the loop prep writes it in the kn5 frame, z negated),
* main() writes ai/<layout>/ with the honest ai_draft.json, refuses a contradicting --direction,
  and refuses a declared direction the layout's own grid contradicts.

Plain ``test_*`` for tests/run_tests.py (no pytest fixtures).
"""

from __future__ import annotations

import json
import math
import struct
import tempfile
from pathlib import Path

from scripts.ac import write_ai_line as w

SIDE = 200


def _square(side: int = SIDE) -> list[list[float]]:
    """Counter-clockwise square loop sampled every 1 m, WITHOUT the closing duplicate."""
    return ([[float(x), 0.0, 0.0] for x in range(0, side)]
            + [[float(side), 0.0, float(z)] for z in range(0, side)]
            + [[float(side - x), 0.0, float(side)] for x in range(0, side)]
            + [[0.0, 0.0, float(side - z)] for z in range(0, side)])


def _channels(n: int, *, chain_on_south: bool, island_on_north: bool, inset: float):
    dh = [0.0] * n
    island = [0.0] * n
    for i in range(10, SIDE - 10):                    # south edge, clear of the corners
        if chain_on_south:
            dh[i] = 0.335
    for i in range(2 * SIDE + 10, 3 * SIDE - 10):     # north edge
        if island_on_north:
            island[i] = 6.0
            dh[i] = 3.0
    return dh, [inset] * n, island


def _south_edge_points(line_pts):
    """Line points over the middle of the south edge (x in 60..140, |z| < 12)."""
    return [p for p in line_pts if 60 <= p[0] <= 140 and abs(p[2]) < 12]


def test_lane_policy_numbers_from_the_spec():
    # 17 m road beside the chain: (0.335+0.4 + 8.5−0.82−0.4)/2 = 4.0075
    assert math.isclose(w.lane_offsets([17.0], [0.335], [0.82])[0], 4.0075, abs_tol=1e-6)
    # no divider: the whole street (Alvarado)
    assert w.lane_offsets([13.0], [0.0], [0.82])[0] == 0.0
    # a lane too narrow for both clearances gets its midpoint, never a negative lane
    assert math.isclose(w.lane_offsets([4.0], [0.5], [0.5])[0], (0.5 + 1.5) / 2, abs_tol=1e-9)
    # the line never sits closer than LINE_MIN_CLEAR_M to a face (8 m road: lane 1.335..2.18)
    o = w.lane_offsets([8.0], [0.335], [0.82])[0]
    assert o >= 0.335 + w.LINE_MIN_CLEAR_M - 1e-9 and o <= 4.0 - 0.82 - w.LINE_MIN_CLEAR_M + 1e-9


def _build(pts, widths, dh, inset, **kw):
    return w.build_line(pts, widths, closed=True, spacing=1.5, lat_g=1.6, decel_g=1.0, accel_g=0.4,
                        vmax_kmh=250.0, margin_m=1.2, dh=dh, inset=inset, **kw)


def test_forward_line_runs_right_of_the_divider_with_asymmetric_sides():
    pts = _square()
    n = len(pts)
    widths = [20.0] * n
    dh, inset, island = _channels(n, chain_on_south=True, island_on_north=False, inset=0.82)
    line = _build(pts, widths, dh, inset)
    south = _south_edge_points(line["pts"])
    assert south, "no points on the south edge"
    expect = ((0.335 + 0.4) + (10.0 - 0.82 - 0.4)) / 2          # lane centre = 4.7575 m right (south)
    for p in south:
        assert math.isclose(p[2], -expect, abs_tol=0.05), p    # right of eastbound travel = −z
    # sides measured from the line: left to the divider face, right to the kerb-line barrier face
    i = next(i for i, p in enumerate(line["pts"]) if 90 <= p[0] <= 110 and abs(p[2]) < 12)
    assert math.isclose(line["side_l"][i], expect - 0.335 - 1.2, abs_tol=0.05)
    assert math.isclose(line["side_r"][i], (10.0 - 0.82) - expect - 1.2, abs_tol=0.05)
    chk = w.check_lane_clearance(line["pts"], pts, widths, dh, inset, island, closed=True, expect_right=True)
    assert chk["ok"], chk
    assert chk["right_side_frac"] == 1.0 and chk["island_hits"] == 0


def test_reverse_layout_runs_right_of_its_own_travel():
    pts = _square()
    n = len(pts)
    widths = [20.0] * n
    dh, inset, island = _channels(n, chain_on_south=True, island_on_north=False, inset=0.82)
    rpts, rw, rdh, rin = list(reversed(pts)), list(reversed(widths)), list(reversed(dh)), list(reversed(inset))
    line = _build(rpts, rw, rdh, rin)
    south = _south_edge_points(line["pts"])
    assert south
    for p in south:
        assert p[2] > 4.0, p                                    # westbound: right of travel = +z (north)
    chk = w.check_lane_clearance(line["pts"], pts, widths, dh, inset, island, closed=True, expect_right=False)
    assert chk["ok"], chk
    # the two directions are distinct lines, not one reversed
    fwd = _build(pts, widths, dh, inset)
    assert [round(p[2], 2) for p in _south_edge_points(fwd["pts"])] != \
        [round(p[2], 2) for p in reversed(_south_edge_points(line["pts"]))]


def test_island_lane_and_no_divider_centreline():
    pts = _square()
    n = len(pts)
    widths = [26.0] * n
    dh, inset, island = _channels(n, chain_on_south=False, island_on_north=True, inset=0.0)
    line = _build(pts, widths, dh, inset)
    north = [p for p in line["pts"] if 60 <= p[0] <= 140 and abs(p[2] - SIDE) < 14]
    assert north
    expect = ((3.0 + 0.4) + (13.0 - 0.4)) / 2                   # 8.0 m right of westbound = +z
    for p in north:
        assert math.isclose(p[2] - SIDE, expect, abs_tol=0.05), p
    # east edge (no divider at all): the centreline, symmetric sides = w/2 − margin (as before 0047)
    east = [(i, p) for i, p in enumerate(line["pts"]) if abs(p[0] - SIDE) < 0.01 and 60 <= p[2] <= 140]
    assert east
    for i, p in east:
        assert math.isclose(line["off"][i], 0.0, abs_tol=1e-9)
        assert math.isclose(line["side_l"][i], 13.0 - 1.2, abs_tol=1e-6)
        assert math.isclose(line["side_r"][i], 13.0 - 1.2, abs_tol=1e-6)
    chk = w.check_lane_clearance(line["pts"], pts, widths, dh, inset, island, closed=True, expect_right=True)
    assert chk["ok"] and chk["island_hits"] == 0, chk


def test_lane_offset_off_keeps_the_centreline():
    pts = _square()
    n = len(pts)
    dh, inset, _ = _channels(n, chain_on_south=True, island_on_north=True, inset=0.82)
    line = _build(pts, [20.0] * n, dh, inset, lane_offset=False)
    assert all(o == 0.0 for o in line["off"])
    assert all(abs(p[2]) < 0.01 for p in _south_edge_points(line["pts"]))


def test_clearance_check_refuses_island_and_wrong_side():
    pts = _square()
    n = len(pts)
    widths = [26.0] * n
    dh, inset, island = _channels(n, chain_on_south=True, island_on_north=True, inset=0.82)
    centre = w.check_lane_clearance(pts, pts, widths, dh, inset, island, closed=True, expect_right=True)
    assert centre["island_hits"] > 0 and centre["divider_too_close"] > 0 and not centre["ok"]
    # a line on the LEFT of the south-edge chain (north of it): clear of the face, wrong side
    left = [[p[0], p[1], p[2] + 4.0] if 10 <= i < SIDE - 10 else p for i, p in enumerate(pts)]
    chk = w.check_lane_clearance(left, pts, widths, dh, inset, island, closed=True, expect_right=True)
    assert chk["right_side_frac"] is not None and chk["right_side_frac"] < 0.5 and not chk["ok"]
    # the same line is the correct side for the reverse layout (its right)
    assert w.check_lane_clearance(left, pts, widths, dh, inset, island, closed=True, expect_right=False)["right_side"] > 0


def test_detect_frame_engine_vs_kn5():
    local = [[float(x), 0.0, 100.0 + 3.0 * x] for x in range(0, 300)]        # not z-symmetric
    assert w.detect_frame(local, local)[0] == "engine"
    kn5 = [[p[0], p[1], -p[2]] for p in local]
    assert w.detect_frame(kn5, local)[0] == "kn5"
    sym = _square()                                                           # z-symmetric about 100? no — shift it
    sym = [[p[0], p[1], p[2] - SIDE / 2] for p in sym]                        # symmetric about z=0: a tie
    assert w.detect_frame([[p[0], p[1], -p[2]] for p in sym], sym)[0] == "engine"


def test_resample_keeps_channels_aligned():
    pts = _square()
    n = len(pts)
    dh = [1.0 if 10 <= i < 50 else 0.0 for i in range(n)]
    rp, rw, ds, (rdh,) = w._resample(pts, [9.0] * n, 1.5, True, extra=[dh])
    assert len(rp) == len(rw) == len(rdh)
    assert all(abs(x - 9.0) < 1e-9 for x in rw)
    assert max(rdh) == 1.0 and min(rdh) == 0.0


# --- main() end to end ---------------------------------------------------------------

def _project(d: Path, *, layouts: list[dict], dummies: dict[str, dict] | None = None) -> Path:
    pts = _square()
    n = len(pts)
    closed = pts + [pts[0]]
    widths = [20.0] * (n + 1)
    data = d / "data"
    data.mkdir(parents=True)
    (d / "track.config.json").write_text(json.dumps({"slug": "sq", "mirror_x": False, "layouts": layouts}))
    (data / "centerline.local.json").write_text(json.dumps({"points_xyz_m": closed, "widths_m": widths}))
    # the loop prep writes the finished line in the KN5 frame (z negated) — as measured on SD
    (data / "finished_centerline.json").write_text(json.dumps(
        {"points_xyz_m": [[p[0], p[1], -p[2]] for p in closed], "widths_m": widths}))
    dh, inset, island = _channels(n, chain_on_south=True, island_on_north=True, inset=0.82)
    (data / "median_bands.json").write_text(json.dumps({"island_w_by_vertex": island + [island[0]]}))
    (data / "barrier_bands.json").write_text(json.dumps(
        {"centre_w_by_vertex": [2 * x if x < 1.0 else 0.0 for x in dh] + [0.0],
         "edge_inset_by_vertex": inset + [inset[0]]}))
    for lid, dm in (dummies or {}).items():
        (data / f"dummies_{lid}.json").write_text(json.dumps(dm))
    return d


def _first_point(ai: Path):
    b = ai.read_bytes()
    _, n, _, _ = struct.unpack_from("<4i", b, 0)
    return struct.unpack_from("<4fi", b, 16)[:3], n


_LAYOUTS = [{"id": "race_cw", "direction": "forward", "race_furniture": True},
            {"id": "race_acw", "direction": "reverse", "race_furniture": True},
            {"id": "street", "direction": "forward", "race_furniture": False}]


def test_main_writes_per_layout_drafts_in_the_kn5_frame():
    with tempfile.TemporaryDirectory() as td:
        d = _project(Path(td), layouts=_LAYOUTS)
        w.main([str(d), "--layout", "race_cw"])
        w.main([str(d), "--layout", "race_acw"])
        w.main([str(d), "--layout", "street"])
        for lid in ("race_cw", "race_acw", "street"):
            out = d / "ai" / lid
            assert (out / "fast_lane.ai").exists() and (out / "pit_lane.ai").exists()
            assert (out / "side_l.csv").exists() and (out / "side_r.csv").exists()
            rep = json.loads((out / "ai_draft.json").read_text())
            assert "GENERATED DRAFT" in rep["status"] and rep["clearance"]["ok"]
        cw = json.loads((d / "ai" / "race_cw" / "ai_draft.json").read_text())
        acw = json.loads((d / "ai" / "race_acw" / "ai_draft.json").read_text())
        st = json.loads((d / "ai" / "street" / "ai_draft.json").read_text())
        assert cw["direction"] == "forward" and cw["race_furniture"] is True
        assert acw["direction"] == "reverse" and acw["race_furniture"] is True
        assert st["direction"] == "forward" and st["race_furniture"] is False
        assert "kn5 frame" in cw["frame"]
        # race layouts see chain + island (south + north edges), the street layout the island only
        assert cw["clearance"]["divider_stations"] > st["clearance"]["divider_stations"] > 0
        # output is in the kn5 frame: a south-edge point of the forward race line sits right of
        # eastbound travel (engine z ≈ −4.76) → kn5 z ≈ +4.76
        b = (d / "ai" / "race_cw" / "fast_lane.ai").read_bytes()
        _, n, _, _ = struct.unpack_from("<4i", b, 0)
        pts = [struct.unpack_from("<4fi", b, 16 + i * 20)[:3] for i in range(n)]
        south = [p for p in pts if 60 <= p[0] <= 140 and abs(p[2]) < 12]
        assert south and all(p[2] > 4.0 for p in south), south[:3]
        # the two race lines differ (distinct files, not a byte-reverse)
        assert (d / "ai" / "race_cw" / "fast_lane.ai").read_bytes() != (d / "ai" / "race_acw" / "fast_lane.ai").read_bytes()


def test_main_refuses_a_contradicting_direction_and_an_undeclared_layout_without_one():
    with tempfile.TemporaryDirectory() as td:
        d = _project(Path(td), layouts=_LAYOUTS)
        for argv in ([str(d), "--layout", "race_acw", "--direction", "forward"],
                     [str(d), "--layout", "nope"]):
            try:
                w.main(argv)
            except SystemExit as e:
                assert ("nope" in str(e.code)) or ("contradicts" in str(e.code)), e.code
            else:
                raise AssertionError(f"{argv} must fail")
        # an undeclared id with an explicit direction is allowed (dry runs before the config lands)
        w.main([str(d), "--layout", "nope", "--direction", "reverse", "--race-furniture", "on"])
        assert json.loads((d / "ai" / "nope" / "ai_draft.json").read_text())["direction"] == "reverse"


def test_main_grid_check_refuses_a_grid_facing_the_other_way():
    # grid on the south edge: AC_START_0 at x=50, timing line at x=80 → faces +x = forward
    fwd = {"AC_START_0": [50.0, 0.0, -4.0], "AC_TIME_0_L": [80.0, 0.0, 4.0], "AC_TIME_0_R": [80.0, 0.0, -9.0],
           "_layout": "race_cw", "_yaw_deg": {"AC_START_0": 0.0}}      # underscore keys are skipped
    with tempfile.TemporaryDirectory() as td:
        # the SAME forward-facing grid handed to both layouts: agrees with race_cw, contradicts race_acw
        d = _project(Path(td), layouts=_LAYOUTS, dummies={"race_cw": fwd, "race_acw": fwd})
        w.main([str(d), "--layout", "race_cw"])                 # grid agrees: forward
        try:
            w.main([str(d), "--layout", "race_acw"])            # declared reverse, grid faces forward
        except SystemExit as e:
            assert "grid faces" in str(e.code), e.code
        else:
            raise AssertionError("a grid contradicting the declared direction must fail the write")
