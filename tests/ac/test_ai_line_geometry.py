"""The AI draft's geometry post-processing (ledger 0047 fix round, 2026-10-11): what the audit of the
installed Lake Murray V3 found, pinned on synthetic roads in the ENGINE frame (x=E, z=N; right of
travel = (tz, −tx)).

* A — the lane-offset curve swallowtails where the offset exceeds the corner's radius: trim_loops cuts
  the loop (crossing legs) or joins the legs' extensions; build_line never ships a backward step.
* B — the offset STEPPED sideways at island noses / chain ends: every change is a cosine taper of
  ramp_length_m (>= 40 m, 10 m per metre), on the undivided side; a short gap holds the lane.
* curvature — min radius >= min(road radius, 12 m), no step over TURN_MAX_DEG where the road is
  not that tight, every point inside its lane; the smoother never drags a bend onto the lane edge.
* C — a closed line starts at the start/finish line (AC_TIME_0 midpoint projected onto it), the
  lap-length field restarts at 0 there and the lap keeps its length.

Plain ``test_*`` for tests/run_tests.py (no pytest fixtures).
"""

from __future__ import annotations

import json
import math
import struct
import tempfile
from pathlib import Path

from scripts.ac import write_ai_line as w


# --- roads ---------------------------------------------------------------------------------------

def _corner_road(R: float, turn_deg: float, leg: float = 120.0, step: float = 1.0) -> list[list[float]]:
    """Open centreline: east along z=0 to the origin, a RIGHT-hand arc of radius R (centre (0, −R)),
    then straight on. Right of travel is the corner's inside."""
    pts = [[x, 0.0, 0.0] for x in [-leg + i * step for i in range(int(leg / step))]]
    n_arc = max(2, int(R * math.radians(turn_deg) / step))
    for j in range(n_arc + 1):
        a = math.radians(90.0 - turn_deg * j / n_arc)
        pts.append([R * math.cos(a), 0.0, -R + R * math.sin(a)])
    a = math.radians(90.0 - turn_deg)
    hx, hz = math.sin(a), -math.cos(a)                  # heading leaving the arc
    ex, ez = pts[-1][0], pts[-1][2]
    for i in range(1, int(leg / step) + 1):
        pts.append([ex + hx * i * step, 0.0, ez + hz * i * step])
    return pts


def _build(pts, widths, dh, inset, *, closed=False, **kw):
    return w.build_line(pts, widths, closed=closed, spacing=1.5, lat_g=1.6, decel_g=1.0, accel_g=0.4,
                        vmax_kmh=250.0, margin_m=1.2, dh=dh, inset=inset, **kw)


def _raw_offset_min_radius(pts, widths, dh, inset) -> float:
    """What the pre-fix writer did: the lane policy as a straight offset along each station's normal."""
    base, ws, ds, (dhs, ins) = w._resample(pts, widths, 1.5, False, extra=[dh, inset])
    off = w.lane_offsets(ws, dhs, ins)
    tan = w._tangents(base, False, ds)
    P = []
    for i, b in enumerate(base):
        L = math.hypot(tan[i][0], tan[i][2]) or 1.0
        P.append([b[0] + tan[i][2] / L * off[i], 0.0, b[2] - tan[i][0] / L * off[i]])
    return min(w._circumradius(P[i - 1], P[i], P[i + 1]) for i in range(1, len(P) - 1))


# --- A: loops ------------------------------------------------------------------------------------

def test_trim_loops_cuts_a_swallowtail_at_the_legs_crossing():
    # base: east to the origin, a tight right-hand arc (R 2 m) through 90 deg, then south; the lane
    # offset 5 m to the RIGHT (inside) is deeper than the radius -> the offset curve swallowtails
    base = _corner_road(2.0, 90.0, leg=30.0, step=0.5)
    T = []
    for i in range(len(base)):
        a, b = base[max(0, i - 1)], base[min(len(base) - 1, i + 1)]
        T.append(w._unit_xz(b[0] - a[0], b[2] - a[2]))
    P = [[p[0] + t[1] * 5.0, 0.0, p[2] - t[0] * 5.0] for p, t in zip(base, T)]
    assert any(w._backward_step(P, T, i) for i in range(1, len(P))), "the fixture must fold"
    out, folds = w.trim_loops(P, T, False, 0.5)
    assert [f["kind"] for f in folds] == ["loop"], folds
    # the in-leg offset line is z = −5, the out-leg's x = 2 − 5 = −3: the corner is their crossing
    X = folds[0]["xz"]
    assert math.isclose(X[0], -3.0, abs_tol=0.3) and math.isclose(X[1], -5.0, abs_tol=0.3), X
    assert w.self_crossings(out, False) == 0
    # every remaining step runs forward along the in-leg (+x) or the out-leg (−z)
    for a, b in zip(out, out[1:]):
        assert (b[0] - a[0]) > -1e-9 or (b[2] - a[2]) < 1e-9, (a, b)
    assert len(out) < len(P)


def test_trim_loops_joins_legs_that_never_cross_by_their_extensions():
    # in-leg east along z=0 to the origin, a 2-point backward curl, then an out-leg south along x=1
    # starting at z=−2: the legs never cross; extended they meet at (1, 0) — kind 'extend'
    P = [[float(x), 0.0, 0.0] for x in range(-10, 1)] + [[-0.5, 0.0, -0.3], [-1.0, 0.0, -0.6]] \
        + [[1.0, 0.0, -float(z)] for z in range(2, 14)]
    T = [(1.0, 0.0)] * 13 + [(0.0, -1.0)] * 12
    out, folds = w.trim_loops(P, T, False, 1.0)
    assert [f["kind"] for f in folds] == ["extend"], folds
    assert math.isclose(folds[0]["xz"][0], 1.0, abs_tol=1e-6) and math.isclose(folds[0]["xz"][1], 0.0, abs_tol=1e-6)
    assert [-0.5, 0.0, -0.3] not in out and [-1.0, 0.0, -0.6] not in out
    assert w.self_crossings(out, False) == 0


def test_inside_lane_of_a_corner_tighter_than_its_offset_ships_no_fold():
    # College -> Navajo in miniature: a 30 m road turning right through 90 deg at R 7.8 m, the centre
    # chain on the centreline and the 0.82 m kerb-line inset: the lane centre (7.26 m) sits inside a
    # 7.8 m radius. The pre-fix offset line turned on a sub-metre radius (race_cw shipped R 0.3 m).
    pts = _corner_road(7.8, 90.0)
    n = len(pts)
    widths, dh, inset = [30.0] * n, [0.335] * n, [0.82] * n
    assert _raw_offset_min_radius(pts, widths, dh, inset) < 2.0
    line = _build(pts, widths, dh, inset)
    g = line["geometry"]
    assert g["backward_steps"] == 0 and g["self_crossings"] == 0, g
    assert g["turns_over_limit"] == 0 and g["radius_below_floor"] == 0, g
    assert g["min_radius_m"] >= w.RADIUS_CHECK * 7.8, g["min_radius_m"]
    chk = w.check_lane_clearance(line["pts"], pts, widths, dh, inset, [0.0] * n, closed=False, expect_right=True)
    assert chk["ok"] and chk["right_side_frac"] == 1.0, chk
    assert chk["min_divider_clear_m"] >= w.CHECK_CLEAR_M and chk["min_edge_clear_m"] >= w.CHECK_CLEAR_M, chk


# --- B: ramps ------------------------------------------------------------------------------------

def test_entering_and_leaving_a_divider_is_a_cosine_taper_on_the_undivided_side():
    n, ds = 400, 1.5
    divided = [150 <= i < 300 for i in range(n)]
    target = [6.0 if d else 0.0 for d in divided]
    lo, hi = [-10.0] * n, [10.0] * n
    o, ramps, clamped = w.ramp_offsets(target, divided, lo, hi, ds, False)
    N = math.ceil(w.ramp_length_m(6.0) / ds)               # 60 m -> 40 stations
    assert w.ramp_length_m(6.0) == 60.0 and w.ramp_length_m(1.0) == w.RAMP_MIN_M
    assert clamped == 0
    assert o[150] == 6.0 and o[299] == 6.0                  # in the lane at both noses
    assert all(v == 0.0 for v in o[:150 - N]) and all(v == 0.0 for v in o[300 + N:])
    assert all(b >= a - 1e-12 for a, b in zip(o[150 - N:151], o[151 - N:152]))      # monotonic in
    steepest = max(abs(o[i + 1] - o[i]) for i in range(n - 1))
    assert steepest <= math.pi * 6.0 / (2 * N) + 1e-9, steepest                         # cosine slope bound
    kinds = sorted(r["kind"] for r in ramps)
    assert kinds == ["enter", "leave"] and all(r["len_m"] >= 60.0 for r in ramps), ramps


def test_a_short_gap_between_two_dividers_holds_the_lane():
    n, ds = 400, 1.5
    divided = [(100 <= i < 200) or (215 <= i < 300) for i in range(n)]
    target = [8.0 if 100 <= i < 200 else 7.4 if 215 <= i < 300 else 0.0 for i in range(n)]
    o, ramps, _ = w.ramp_offsets(target, divided, [-12.0] * n, [12.0] * n, ds, False)
    assert all(7.4 - 1e-9 <= v <= 8.0 + 1e-9 for v in o[200:215]), o[200:215]          # never back to 0
    assert any(r["kind"] == "hold" for r in ramps), ramps


def test_a_butt_joint_is_tapered_inside_the_lane():
    # chain (lane centre 7.26) butting onto an island (8.6) and back, every station divided (closed lap)
    n, ds = 600, 1.5
    target = [8.6 if 200 <= i < 400 else 7.26 for i in range(n)]
    lo, hi = [1.0] * n, [13.6] * n
    o, ramps, clamped = w.ramp_offsets(target, [True] * n, lo, hi, ds, True)
    assert clamped == 0 and sorted(r["kind"] for r in ramps) == ["joint", "joint"]
    N = math.ceil(w.RAMP_MIN_M / ds)
    assert max(abs(o[(i + 1) % n] - o[i]) for i in range(n)) <= math.pi * 1.34 / (2 * N) + 1e-9
    assert all(lo[i] <= o[i] <= hi[i] for i in range(n))


# --- curvature -----------------------------------------------------------------------------------

def test_a_bend_at_its_own_floor_is_not_dragged_onto_the_lane_edge():
    # Dragon Tail's regression: a 10 m road bending at R 10 m (floor = its own radius). Plain Laplacian
    # flow shrank the bend onto the inside lane edge (4.3 m in, R 6 m: refused). Now the bend gets one
    # fillet — the largest radius <= 12 m that fits the COMFORT lane (1.5 m off the edge) — and the
    # clean-up never drags it further.
    pts = _corner_road(10.0, 120.0)
    n = len(pts)
    line = _build(pts, [10.0] * n, [0.0] * n, [0.0] * n)
    g = line["geometry"]
    assert g["turns_over_limit"] == 0 and g["radius_below_floor"] == 0, g
    assert g["min_radius_m"] >= w.RADIUS_CHECK * 10.0, g["min_radius_m"]
    assert all(f["lane"] == "comfort" for f in g["fillets"]), g["fillets"]
    assert max(abs(o) for o in line["off"]) <= 5.0 - w.FILLET_COMFORT_CLEAR_M + 1e-6, max(abs(o) for o in line["off"])


def test_bound_curvature_never_returns_a_worse_line():
    pts = _corner_road(10.0, 120.0)
    n = len(pts)
    base, ws, ds, (dhs, ins) = w._resample(pts, [10.0] * n, 1.5, False, extra=[[0.0] * n, [0.0] * n])
    tan = [w._unit_xz(t[0], t[2]) for t in w._tangents(base, False, ds, span=w.TANGENT_SPAN)]
    lo, hi = w.lane_corridor(ws, dhs, ins, 0.7)
    st = w._Stations(base, tan, lo, hi, w.road_radius(base, False), False, ds)
    zig = [list(p) for p in base]
    for i in range(40, 60, 2):                               # a saw-tooth kink train on the straight
        zig[i][2] += 0.6
    out, rep = w.bound_curvature([list(p) for p in zig], False, st, max_iter=300)
    assert rep["violations_after"] <= rep["violations_before"], rep
    assert all(lo[k] - 1e-6 <= st.lat(p[0], p[2], k) <= hi[k] + 1e-6 for p, k in zip(out, st.associate(out)))


# --- C: start / finish ---------------------------------------------------------------------------

SIDE = 200


def _square() -> list[list[float]]:
    return ([[float(x), 0.0, 0.0] for x in range(0, SIDE)] + [[float(SIDE), 0.0, float(z)] for z in range(0, SIDE)]
            + [[float(SIDE - x), 0.0, float(SIDE)] for x in range(0, SIDE)] + [[0.0, 0.0, float(SIDE - z)] for z in range(0, SIDE)])


def _project(d: Path, dummies: dict | None) -> Path:
    pts = _square()
    closed = pts + [pts[0]]
    widths = [20.0] * len(closed)
    (d / "data").mkdir(parents=True)
    (d / "track.config.json").write_text(json.dumps({"slug": "sq", "mirror_x": False, "layouts": [
        {"id": "race_cw", "direction": "forward", "race_furniture": False}]}))
    (d / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": closed, "widths_m": widths}))
    (d / "data" / "finished_centerline.json").write_text(json.dumps({"points_xyz_m": closed, "widths_m": widths}))
    if dummies:
        (d / "data" / "dummies_race_cw.json").write_text(json.dumps(dummies))
    return d


def _read(ai: Path):
    b = ai.read_bytes()
    _, n, _, _ = struct.unpack_from("<4i", b, 0)
    rows = [struct.unpack_from("<4fi", b, 16 + i * 20) for i in range(n)]
    return [(r[0], r[1], -r[2]) for r in rows], [r[3] for r in rows]       # engine frame, length field


def test_closed_line_starts_at_the_start_finish_line():
    # the timing line crosses the south edge at x = 80 (the lap seam is the corner at the origin)
    dm = {"AC_START_0": [50.0, 0.0, 0.0], "AC_TIME_0_L": [80.0, 0.0, 10.0], "AC_TIME_0_R": [80.0, 0.0, -10.0]}
    with tempfile.TemporaryDirectory() as td:
        rot = _project(Path(td) / "rot", dm)
        plain = _project(Path(td) / "plain", None)
        w.main([str(rot), "--layout", "race_cw"])
        w.main([str(plain), "--layout", "race_cw"])
        P, L = _read(rot / "ai" / "race_cw" / "fast_lane.ai")
        Q, M = _read(plain / "ai" / "race_cw" / "fast_lane.ai")
        # point 0 is ON the timing line (the midpoint projected onto the line), and the nearest point
        assert math.isclose(P[0][0], 80.0, abs_tol=1e-3) and abs(P[0][2]) < 1e-3, P[0]
        assert min(range(len(P)), key=lambda i: (P[i][0] - 80.0) ** 2 + P[i][2] ** 2) == 0
        assert L[0] == 0.0 and all(b > a for a, b in zip(L, L[1:]))                  # restarts at 0 there
        # the same closed loop, only rotated: its length is kept
        lap_rot = sum(math.dist((P[i][0], P[i][2]), (P[(i + 1) % len(P)][0], P[(i + 1) % len(P)][2])) for i in range(len(P)))
        lap_plain = sum(math.dist((Q[i][0], Q[i][2]), (Q[(i + 1) % len(Q)][0], Q[(i + 1) % len(Q)][2])) for i in range(len(Q)))
        assert abs(lap_rot - lap_plain) < 1.0, (lap_rot, lap_plain)
        rep = json.loads((rot / "ai" / "race_cw" / "ai_draft.json").read_text())
        assert rep["geometry"]["start"]["source"].startswith("dummies_race_cw.json")
        assert rep["geometry"]["start"]["dist_m"] < 1e-3
        # without a timing line point 0 stays at the seam (the corner at the origin, filleted ~5 m in)
        assert min(range(len(Q)), key=lambda i: Q[i][0] ** 2 + Q[i][2] ** 2) == 0, Q[0]
