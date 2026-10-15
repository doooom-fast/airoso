"""The race AI draft inside a declared corridor (ledger 0049: an Alvarado-wide lane per direction, the
other lanes closed off, the whole intersection open at the corners the race turns at).

Pinned on synthetic roads in the ENGINE frame (x=E, z=N; forward-left = +y of the declaration):

* the wall FACES are the declared laterals on the vertex frame, fold-trimmed at a tight inside corner like
  the strip they belong to (one cut, at the legs' crossing), and the authored islands are obstacles;
* the lane target is the lane centre with every change of it a taper (never a step), inside the lane;
* an open corner gets the largest arc the box allows, from the corridor's outside edge, never closer than
  the comfort clearance to a face — wider than the line the corridor would otherwise take;
* main() reads corridors.<layout> of a version-2 barrier_bands.json, writes a draft that stays inside it in
  both directions (each on its own side), reports the metrics, refuses a v2 file without the layout,
  and keeps the legacy lane for a version-1 file.

Plain ``test_*`` for tests/run_tests.py (no pytest fixtures).
"""

from __future__ import annotations

import json
import math
import struct
import tempfile
from pathlib import Path

from scripts.ac import write_ai_line as w


def _corner_road(R: float, turn_deg: float, leg: float = 80.0, step: float = 1.0) -> list[list[float]]:
    """Open centreline: east along z=0 to the origin, a RIGHT-hand arc of radius R, then straight on."""
    pts = [[x, 0.0, 0.0] for x in [-leg + i * step for i in range(int(leg / step))]]
    n_arc = max(2, int(R * math.radians(turn_deg) / step))
    for j in range(n_arc + 1):
        a = math.radians(90.0 - turn_deg * j / n_arc)
        pts.append([R * math.cos(a), 0.0, -R + R * math.sin(a)])
    a = math.radians(90.0 - turn_deg)
    hx, hz = math.sin(a), -math.cos(a)
    ex, ez = pts[-1][0], pts[-1][2]
    for i in range(1, int(leg / step) + 1):
        pts.append([ex + hx * i * step, 0.0, ez + hz * i * step])
    return pts


def _rounded_square(half: float = 100.0, r: float = 20.0, step: float = 1.0) -> tuple[list[list[float]], list[tuple]]:
    """Closed counter-clockwise loop (east along the south edge first), straights joined by quarter arcs
    of radius r. Returns (points without the closing duplicate, corners [(apex, PC, PT)] as indices)."""
    pts, corners = [], []
    s = half - r
    legs = [((-s, -half), (s, -half), (s, -s), -90.0), ((half, -s), (half, s), (s, s), 0.0),
            ((s, half), (-s, half), (-s, s), 90.0), ((-half, s), (-half, -s), (-s, -s), 180.0)]
    for (x0, z0), (x1, z1), (cx, cz), a0 in legs:
        L = math.hypot(x1 - x0, z1 - z0)
        k = int(round(L / step))
        for i in range(k):
            pts.append([x0 + (x1 - x0) * i / k, 0.0, z0 + (z1 - z0) * i / k])
        n_arc = int(round(r * math.pi / 2 / step))
        pc = len(pts)
        for j in range(n_arc):
            a = math.radians(a0 + 90.0 * j / n_arc)
            pts.append([cx + r * math.cos(a), 0.0, cz + r * math.sin(a)])
        corners.append(((pc + len(pts) - 1) // 2, pc, len(pts) - 1))
    return pts, corners


# --- faces ----------------------------------------------------------------------------------------

def test_inside_face_of_a_tight_corner_is_trimmed_at_the_legs_crossing():
    # a 30 m road turning right at R 8 m: the inside (right, y < 0) face at 14.18 m swallowtails
    pts = _corner_road(8.0, 90.0)
    lane = [(-14.18, 14.18)] * len(pts)
    faces = w.CorridorFaces(pts, lane, closed=False)
    assert faces.folds["hi"] == [] and len(faces.folds["lo"]) == 1, faces.folds
    lo = [[x, 0.0, z] for x, z in faces.polyline("lo")]
    assert w.self_crossings(lo, False) == 0
    # in-leg offset line z = −14.18, out-leg (southbound along x = 8) offset line x = 8 − 14.18
    X = (8.0 - 14.18, -14.18)
    assert min(math.hypot(x - X[0], z - X[1]) for x, z in faces.polyline("lo")) < 0.3
    # inside the corner, short of the crossing: in the corridor; past it (beyond the wall): outside
    assert faces.clearance(X[0] + 2.0, X[1] + 2.0) > 0.0
    assert faces.dists(X[0] - 2.0, X[1] - 2.0)[1] < 0.0


def test_an_authored_island_is_an_obstacle_with_its_nose_taper():
    cl = [[float(x), 0.0, 0.0] for x in range(0, 101)]
    iw = [6.0 if 30 <= k <= 70 else 0.0 for k in range(len(cl))]
    half = w.authored_island_half(iw)
    assert half[30] == 0.25 and half[70] == 0.25 and abs(half[50] - 3.0) < 1e-9     # the nose taper
    assert abs(half[31] - (0.25 + (3.0 - 0.25) / 3)) < 1e-9
    faces = w.CorridorFaces(cl, [(-10.0, 10.0)] * len(cl), closed=False, island_half=half)
    assert faces.island(50.0, 0.0) < 0.0 and abs(faces.island(50.0, 5.0) - 2.0) < 1e-6
    line = [[float(x), 0.0, 0.0] for x in range(5, 96)]                  # straight through the island
    chk = w.check_corridor(line, faces, closed=False)
    assert chk["island_hits"] > 0 and not chk["ok"], chk
    beside = [[float(x), 0.0, -5.0] for x in range(5, 96)]
    chk = w.check_corridor(beside, faces, closed=False)
    assert chk["ok"] and abs(chk["island_min_m"] - 2.0) < 1e-6, chk


# --- the lane target ------------------------------------------------------------------------------

def test_lane_centre_target_tapers_and_stays_in_the_lane():
    # the whole street (13 m, centre 0) meets a closure run (17 m road, centre 2.0 m right) in one step
    n, ds = 400, 1.5
    lo = [-5.68 if i < 200 else -3.68 for i in range(n)]
    hi = [5.68 if i < 200 else 7.68 for i in range(n)]
    o, rep = w.corridor_offsets(lo, hi, ds, False)
    assert abs(o[20]) < 0.01 and abs(o[380] - 2.0) < 0.01, (o[20], o[380])
    assert all(lo[i] + w.LINE_MIN_CLEAR_M - 1e-9 <= o[i] <= hi[i] - w.LINE_MIN_CLEAR_M + 1e-9 for i in range(n))
    steepest = max(abs(o[i + 1] - o[i]) for i in range(n - 1)) / ds
    assert steepest < 2.0 / (2 * w.CORRIDOR_MU_M) * 1.05, steepest        # an exponential taper, ~mu_m long
    assert rep["max_lateral_slope"] == round(steepest, 4)
    # a wall that moves faster than the taper drags the line: the bound is hard
    lo2 = [-5.68 if i < 200 else 1.0 for i in range(n)]
    o2, _ = w.corridor_offsets(lo2, [5.68] * n, ds, False)
    assert all(o2[i] >= lo2[i] + w.LINE_MIN_CLEAR_M - 1e-9 for i in range(n))


def test_a_chicane_holds_the_comfort_clearance_where_the_plain_bound_lets_the_line_cut_the_s():
    # ledger 0055 round 2: a 9.6 m walled lane that sweeps 20 m sideways over ~55 m and back (College's chicane);
    # with the 1 m bound the lane-centre target cuts each bend toward its inside wall, with the chicane's hold it
    # stays comfort + FAIR_CLEAR_EXTRA_M off both walls
    n, ds = 600, 1.5
    def sweep(i):
        t = min(1.0, max(0.0, (i - 200) / 36.0)) - min(1.0, max(0.0, (i - 360) / 36.0))
        return 20.0 * (0.5 - 0.5 * math.cos(math.pi * t)) if 0.0 < t < 1.0 else 20.0 * t
    lo = [sweep(i) - 4.8 for i in range(n)]
    hi = [sweep(i) + 4.8 for i in range(n)]
    o, _ = w.corridor_offsets(lo, hi, ds, False)
    plain = min(min(o[i] - lo[i], hi[i] - o[i]) for i in range(n))
    hold = 2.5 + w.FAIR_CLEAR_EXTRA_M
    clear = [hold if 190 <= i <= 410 else w.LINE_MIN_CLEAR_M for i in range(n)]
    o3, _ = w.corridor_offsets(lo, hi, ds, False, clear=clear)
    held = min(min(o3[i] - lo[i], hi[i] - o3[i]) for i in range(190, 411))
    assert plain < 2.5 <= hold - 1e-9 <= held, (plain, held)
    assert max(abs(o3[i + 1] - o3[i]) for i in range(n - 1)) < 1.0                 # still a taper, never a step


# --- open corners ---------------------------------------------------------------------------------

def _square_corridor(open_corners: bool):
    pts, corners = _rounded_square()
    m = len(pts)
    lane = [(-11.18, 11.18)] * m                                       # a 24 m road, the whole street
    faces = w.CorridorFaces(pts, lane, closed=True)
    cs = [{"apex_vertex": ap, "zone": "box", "D_deg": 90.0, "a": pc - 2, "b": pt + 2, "apex": ap}
          for ap, pc, pt in corners] if open_corners else []
    return pts, {"lo": [-b for a, b in lane], "hi": [-a for a, b in lane], "zone": [2.0] * m, "corners": cs,
                 "faces": faces, "forward": True}


def test_an_open_corner_gets_the_largest_arc_the_box_allows():
    pts, cor = _square_corridor(True)
    line = w.build_line(pts, [24.0] * len(pts), closed=True, spacing=1.5, lat_g=1.6, decel_g=1.0, accel_g=0.4,
                        vmax_kmh=250.0, margin_m=1.2, corridor=cor)
    arcs = line["geometry"]["box_arcs"]
    assert len(arcs) == 4 and all(a["lane"] == "comfort" for a in arcs), arcs
    # the centreline turns at R 20 m; from the outside edge the 24 m box allows well over 30 m
    assert all(a["radius_m"] > 30.0 for a in arcs), [a["radius_m"] for a in arcs]
    assert all(a["path_clear_min_m"] >= w.FILLET_COMFORT_CLEAR_M - 1e-6 for a in arcs), arcs
    chk = w.check_corridor(line["pts"], cor["faces"])
    assert chk["ok"] and chk["min_clear_m"] >= w.FILLET_COMFORT_CLEAR_M - 0.05, chk
    g = line["geometry"]
    assert g["backward_steps"] == 0 and g["self_crossings"] == 0 and g["radius_below_floor"] == 0, g
    # the same corridor without its corners declared open: the line keeps the 20 m centreline radius
    pts2, cor2 = _square_corridor(False)
    line2 = w.build_line(pts2, [24.0] * len(pts2), closed=True, spacing=1.5, lat_g=1.6, decel_g=1.0, accel_g=0.4,
                         vmax_kmh=250.0, margin_m=1.2, corridor=cor2)
    assert line2["geometry"]["box_arcs"] == []
    assert line2["geometry"]["min_radius_m"] < 22.0 < min(a["radius_m"] for a in arcs)
    assert min(line["v"]) > min(line2["v"]) + 2.0                     # a faster corner, not just a wider one


# --- main() end to end ----------------------------------------------------------------------------

HALF = 200.0       # the end-to-end square: 360 m straights, so every closure reaches its full depth


def _v2_project(d: Path, *, with_acw: bool = True) -> Path:
    """The rounded square as a race track: a closure on the middle of every straight (at y = -1.0 at full
    depth: the lane centre ~6 m right of the centreline for race_cw, mirrored for race_acw), pinned on the
    far face with 1:6 funnels, the four corners open boxes, a timing line across the south straight."""
    pts, corners = _rounded_square(half=HALF)
    m = len(pts)
    closed = pts + [pts[0]]
    data = d / "data"
    data.mkdir(parents=True)
    layouts = [{"id": "race_cw", "kind": "race", "direction": "forward", "race_furniture": True, "closure_token": "cw"},
               {"id": "race_acw", "kind": "race", "direction": "reverse", "race_furniture": True, "closure_token": "acw"}]
    (d / "track.config.json").write_text(json.dumps({"slug": "sq", "mirror_x": False, "layouts": layouts}))
    (data / "centerline.local.json").write_text(json.dumps({"points_xyz_m": closed, "widths_m": [24.0] * (m + 1)}))
    # the ENGINE frame: this loop is z-symmetric, so a kn5-frame copy could not be told apart (detect_frame
    # keeps "engine" on a tie — test_write_ai_line_layouts pins the frame handling on a loop that is not)
    (data / "finished_centerline.json").write_text(json.dumps({"points_xyz_m": closed, "widths_m": [24.0] * (m + 1)}))
    (data / "median_bands.json").write_text(json.dumps({"island_w_by_vertex": [0.0] * (m + 1)}))
    face = 11.18
    zone, y_close = ["whole"] * m, [None] * m
    in_box = set()
    for ap, pc, pt in corners:
        for k in range(pc - 2, pt + 3):
            in_box.add(k % m)
    for k in range(m):
        if k in in_box:
            zone[k] = "box"
    runs = []
    k = 0
    while k < m:                                   # closure runs = the straights' middles, 30 m off each box
        if zone[k] == "box" or zone[k - 1] != "box":
            k += 1
            continue
        j = k
        while zone[j % m] != "box":
            j += 1
        i0, i1 = k + 30, j - 31
        runs.append((i0, i1))
        k = j
    for i0, i1 in runs:
        for q in range(i0, i1 + 1):
            dist = min(q - i0, i1 - q)                 # 1 m steps: 1:6 funnel from the far face to y = -1.0
            y = max(-1.0, face - dist / 6.0)
            zone[q % m] = "pin" if q in (i0, i1) else "closure"
            y_close[q % m] = y
    cw_lane = [(-face, face) if y_close[k] is None else (-face, y_close[k]) for k in range(m)]
    acw_lane = [(-face, face) if y_close[k] is None else (-y_close[k], face) for k in range(m)]
    cors = {"race_cw": {"token": "cw", "zone_by_vertex": zone, "lane_by_vertex": cw_lane}}
    if with_acw:
        cors["race_acw"] = {"token": "acw", "zone_by_vertex": zone, "lane_by_vertex": acw_lane}
    bands = {"version": 2, "corners": [{"apex": ap, "PC": pc, "PT": pt, "D_deg": 90.0} for ap, pc, pt in corners],
             "edge_inset_by_vertex": [0.82] * (m + 1), "centre_w_by_vertex": [0.0] * (m + 1), "corridors": cors}
    (data / "barrier_bands.json").write_text(json.dumps(bands))
    # timing line across the south straight at x = 0; grids behind it in each direction
    (data / "dummies_race_cw.json").write_text(json.dumps(
        {"AC_START_0": [-27.0, 0.0, -HALF - 5.0], "AC_TIME_0_L": [0.0, 0.0, -HALF + 12.0], "AC_TIME_0_R": [0.0, 0.0, -HALF - 12.0]}))
    (data / "dummies_race_acw.json").write_text(json.dumps(
        {"AC_START_0": [27.0, 0.0, -HALF + 5.0], "AC_TIME_0_L": [0.0, 0.0, -HALF - 12.0], "AC_TIME_0_R": [0.0, 0.0, -HALF + 12.0]}))
    return d


def _read(ai: Path):
    b = ai.read_bytes()
    _, n, _, _ = struct.unpack_from("<4i", b, 0)
    return [(r[0], -r[2]) for r in (struct.unpack_from("<3f", b, 16 + i * 20) for i in range(n))]   # engine xz


def test_main_drafts_both_directions_inside_their_corridors():
    with tempfile.TemporaryDirectory() as td:
        d = _v2_project(Path(td))
        w.main([str(d), "--layout", "race_cw"])
        w.main([str(d), "--layout", "race_acw"])
        cw = json.loads((d / "ai" / "race_cw" / "ai_draft.json").read_text())
        acw = json.loads((d / "ai" / "race_acw" / "ai_draft.json").read_text())
        for rep in (cw, acw):
            c = rep["corridor"]
            assert c["check"]["ok"] and c["check"]["outside"] == 0, c["check"]
            assert c["wall_clear_min_m"] >= w.CHECK_CLEAR_M and c["points_in_open_box"] > 0, c
            assert c["start_index"] == 0 and rep["geometry"]["start"]["dist_m"] < 12.0
            assert c["min_speed_kmh"] == rep["geometry"]["min_speed_kmh"] > 0
            assert len(rep["geometry"]["box_arcs"]) == 4 and all("radius_m" in a for a in rep["geometry"]["box_arcs"])
            assert "GENERATED DRAFT" in rep["status"]
        assert cw["geometry"]["start"]["grid_behind_line_m"] > 0 and acw["geometry"]["start"]["grid_behind_line_m"] > 0
        # mid south straight: race_cw (eastbound) runs south of the closure (right of travel), race_acw
        # (westbound) north of it — each in its own lane, at its centre, distinct files
        for lid, sign in (("race_cw", -1.0), ("race_acw", 1.0)):
            line = _read(d / "ai" / lid / "fast_lane.ai")
            mid = [p for p in line if -20.0 <= p[0] <= 20.0 and abs(p[1] + HALF) < 13.0]
            assert mid and all(sign * (p[1] + HALF) > 1.0 + w.CHECK_CLEAR_M for p in mid), (lid, mid[:3])
            assert all(abs(sign * (p[1] + HALF) - (1.0 + 11.18) / 2) < 0.3 for p in mid), (lid, mid[:3])
            # point 0 is the start/finish line's midpoint projected onto the line: the line's nearest point to it
            dist = [math.hypot(p[0], p[1] + HALF) for p in line]
            assert dist[0] <= min(dist) + 1e-3, (dist[0], min(dist))
        assert (d / "ai" / "race_cw" / "fast_lane.ai").read_bytes() != (d / "ai" / "race_acw" / "fast_lane.ai").read_bytes()


def test_main_refuses_a_v2_declaration_without_the_layout_and_keeps_the_legacy_lane_for_v1():
    with tempfile.TemporaryDirectory() as td:
        d = _v2_project(Path(td), with_acw=False)
        try:
            w.main([str(d), "--layout", "race_acw"])
        except SystemExit as e:
            assert "none for layout 'race_acw'" in str(e.code), e.code
        else:
            raise AssertionError("a v2 declaration without the layout's corridor must refuse the draft")
        # a version-2 file with no corridors at all is not silently the retired centre-chain lane either
        bp = d / "data" / "barrier_bands.json"
        b = json.loads(bp.read_text())
        b.pop("corridors")
        bp.write_text(json.dumps(b))
        try:
            w.main([str(d), "--layout", "race_cw"])
        except SystemExit as e:
            assert "declares no corridors" in str(e.code), e.code
        else:
            raise AssertionError("v2 without corridors must refuse")
        # version 1 (today's file): the 0047 lane, no corridor block
        b["version"] = 1
        bp.write_text(json.dumps(b))
        w.main([str(d), "--layout", "race_cw"])
        rep = json.loads((d / "ai" / "race_cw" / "ai_draft.json").read_text())
        assert "corridor" not in rep and rep["race_furniture"] is True
