"""tools/place_signs.py + tools/verify_signs.py — the pure-Python pieces of the W1-6 rule that the
2026-10-10 fix rounds added or changed (ledger 0044): the pair merge, the capped curb slide, the
detector knobs wired through cfg, the paired-post polygons, the loud signs.json validation, the
reverse-only corner ids + skipped dedupe, the gated-disc split, and the verifier's own
re-derivations (approach chord, turn sense, base side) on a synthetic L. Plain ``test_*`` functions
for tests/run_tests.py (no pytest, no bpy). The placement itself is exercised by the dry run on the
real data, not here.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import place_signs as ps  # noqa: E402
import verify_signs as vs  # noqa: E402


def _rec(cid, direction, base, face, arrow, slid=0.0):
    f = (math.cos(math.radians(face)), math.sin(math.radians(face)))
    r = (f[1], -f[0])
    return {
        "id": "%s-%s" % (cid, direction), "kind": "W1-6R" if arrow == "right" else "W1-6L", "plate": "W1-6",
        "ribbon": "loop", "direction": direction,
        "corner": {"D_deg": -150.0 if arrow == "right" else 150.0}, "approach": {"t_xz": [-f[0], -f[1]]},
        "ray": {"A_xz": [base[0] + f[0] * 12, base[1] + f[1] * 12], "sC_station": 10},
        "base_xz": list(base), "curb_dir_xz": [r[0], r[1]], "y_road_at_sC": 0.0,
        "y_base": {"analytic": 0.24, "raycast": None, "source": "analytic"},
        "face_dir_xz": [f[0], f[1]], "face_bearing_deg": 0.0, "yaw_deg": 0.0, "right_xz": [r[0], r[1]],
        "arrow": arrow, "expect_arrow": None, "lateral_offset_m": 1.33, "height_m": 2.13, "om1_3": True,
        "checks": {"outside_cross": 1.0, "edge_clear_m": 1.4, "lamp_m": 50.0, "plant_m": 40.0, "plant_zone": "-",
                   "pushed_m": 0.0, "slid_m": slid, "lateral_step_m": 0.0, "gate_margin_m": 0.5, "gate_margin_gated_m": 9.0,
                   "walk_behind_m": -0.25, "mouth_m": 99.0, "spawn_m": 500.0, "spawn": "-", "warnings": []},
        "old_rule": {}, "overrides_applied": [], "exclude_plant": None, "where": "",
    }


def test_merge_pairs_joins_close_fwd_rev_and_keeps_far_ones():
    a = _rec("DCL-2", "fwd", (10.0, 10.0), 100.0, "right")
    b = _rec("DCL-2", "rev", (10.3, 10.3), 130.0, "left")       # 0.42 m apart -> one post
    c = _rec("MED-6", "fwd", (50.0, 50.0), 10.0, "left")
    d = _rec("MED-6", "rev", (52.5, 50.0), 200.0, "right")      # 2.5 m apart -> stays two
    logs = []
    out = ps.merge_pairs([a, b, c, d], log=logs.append)
    assert [s["id"] for s in out] == ["DCL-2", "MED-6-fwd", "MED-6-rev"]
    p = out[0]
    assert p["pair"] and p["kind"] == "W1-6R+W1-6L" and p["direction"] == "both"
    assert [q["direction"] for q in p["plates"]] == ["fwd", "rev"]
    assert all(q["plate"] == "W1-6" for q in p["plates"])
    assert abs(p["base_xz"][0] - 10.15) < 1e-9 and abs(p["base_xz"][1] - 10.15) < 1e-9
    assert abs(p["pair_split_m"] - 0.42) < 0.01
    assert any("paired" in w for w in p["checks"]["warnings"]) and len(logs) == 1
    assert p["checks"]["gate_margin_gated_m"] == 9.0 and p["checks"]["walk_behind_m"] == -0.25
    assert ps.merge_pairs(out) == out                            # idempotent
    assert ps.plates_of(p) == p["plates"] and ps.plates_of(c) == [c]


def test_paired_post_polygons_one_post_two_plates():
    a = _rec("X", "fwd", (0.0, 0.0), 0.0, "right")
    b = _rec("X", "rev", (0.4, 0.0), 30.0, "left")              # facings 30 deg apart -> stacked
    info = []
    single = ps.sign_polygons(a, 0.0, info)
    pair = ps.sign_polygons(ps.merge_pairs([a, b])[0], 0.0)
    assert len(pair["SIGNARROW"]) == 2 * len(single["SIGNARROW"])         # two arrows + two borders
    assert len(pair["SIGNPLATE"]) == 2 * len(single["SIGNPLATE"]) - 1     # the stacked plate has no diamond
    post_faces = 5                                                         # four sides + top
    assert len(single["SIGNPOST"]) == 2 + post_faces                       # plate back + diamond back + post
    assert len(pair["SIGNPOST"]) == 3 + post_faces                         # ONE post, three backs
    top_single = max(v[1] for verts, _ in single["SIGNPOST"] for v in verts)
    top_pair = max(v[1] for verts, _ in pair["SIGNPOST"] for v in verts)
    assert abs(top_pair - top_single - ps.PLATE_H - ps.PAIR_STACK_GAP) < 1e-9   # the post grows by one plate
    # the vertex info the verifier measures: front face 3 mm ahead of the back face along +f,
    # arrow tip to the driver's right of the plate centre for a right arrow, post base sunk 0.30
    plate, post = info[0], info[1]
    fc = [sum(v[i] for v in plate["front_xyz"]) / 4 for i in range(3)]
    bc = [sum(v[i] for v in plate["back_xyz"]) / 4 for i in range(3)]
    assert abs((fc[0] - bc[0]) - ps.PLATE_BACK_GAP) < 1e-6 and abs(fc[2] - bc[2]) < 1e-9     # f = +x here
    assert plate["arrow_xyz"][0][2] - fc[2] < 0                                                # right of travel = -z (r = (0, -1))
    assert min(v[1] for v in plate["front_xyz"]) == 2.13 and min(v[1] for v in post["post_base_xyz"]) == -0.30
    # back-to-back (facings 180 deg apart): same height, both diamonds, post unchanged
    c = _rec("X", "rev", (0.4, 0.0), 180.0, "left")
    merged = ps.merge_pairs([a, c])
    assert len(merged) == 1 and merged[0]["pair"]
    bb = ps.sign_polygons(merged[0], 0.0)
    assert len(bb["SIGNPLATE"]) == 2 * len(single["SIGNPLATE"])
    assert abs(max(v[1] for verts, _ in bb["SIGNPOST"] for v in verts) - top_single) < 1e-9


class _Ctx:
    """the three things choose_slide asks of a Context"""

    def __init__(self, lamps=(), plants=(), margin=1.0):
        self.lamps, self.plants, self.margin = lamps, plants, margin
        self.field = self
        self.asked_names = []

    def nearest_lamp(self, q):
        return min((math.dist(q, b) for b in self.lamps), default=float("inf"))

    def nearest_plant(self, q):
        return min(((math.dist(q, p[:2]), p[2], p[3]) for p in self.plants), default=(float("inf"), "-", -1))

    def footprint_margin(self, base, rights, names=None):
        self.asked_names.append(names)
        return self.margin


CFG = {"lamp_clear_m": 3.0, "plant_clear_m": 2.5}


def test_slide_is_capped_at_one_metre_then_excludes_the_plant():
    S, u = (0.0, 0.0), (1.0, 0.0)
    clear = lambda x, z: 1.5                                     # the edge never objects
    # a palm 2.45 m away, straight along the curb: +0.25 m clears it (smallest move first)
    ctx = _Ctx(plants=[(-2.45, 0.0, "palms", 2)])
    slid, q, lamp, plant, excl, reasons = ps.choose_slide(ctx, CFG, S, u, 1.33, clear, rights=((0.0, 1.0),))
    assert slid == 0.25 and excl is None and reasons == [] and plant[0] >= 2.5
    # a palm 1.0 m off the curb line, right at the post: no slide <= 1.0 m reaches 2.5 m -> excluded, no slide
    ctx = _Ctx(plants=[(0.0, 1.0, "palms", 7)])
    slid, q, lamp, plant, excl, reasons = ps.choose_slide(ctx, CFG, S, u, 1.33, clear, rights=((0.0, 1.0),))
    assert slid == 0.0 and q == S and excl == {"zone": "palms", "index": 7, "dist_m": 1.0} and reasons == []
    assert max(abs(c) for c in ps.slide_candidates()) == ps.SLIDE_MAX_M == 1.0
    # a lamp inside 3 m with no clearing slide is fatal (lamps never move)
    ctx = _Ctx(lamps=[(0.0, 1.0)])
    slid, q, lamp, plant, excl, reasons = ps.choose_slide(ctx, CFG, S, u, 1.33, clear)
    assert slid == 0.0 and reasons and "lamp" in reasons[0]
    # a candidate that would stand inside the GATED disc is skipped; the gated ribbons are passed through
    ctx = _Ctx(plants=[(-2.45, 0.0, "palms", 2)], margin=-0.1)
    slid, q, lamp, plant, excl, reasons = ps.choose_slide(ctx, CFG, S, u, 1.33, clear, rights=((0.0, 1.0),), disc_names=("MAINLINE",))
    assert slid == 0.0 and excl is not None and ctx.asked_names and all(n == ("MAINLINE",) for n in ctx.asked_names)


def test_disc_is_gated_by_ribbon_kind():
    assert ps.disc_names_for("MAINLINE") is None                  # every ribbon's disc is hard
    assert ps.disc_names_for("medium#2+0#0#0") == ("MAINLINE",)   # a connector post: the mainline's only
    # a 10 m connector 3 m from a post: own disc 4.9 m -> inside it; the mainline 100 m away clears
    main = [(x, 0.0, 100.0) for x in (0.0, 50.0, 100.0)]
    side = [(0.0, 0.0, 0.0), (50.0, 0.0, 0.0), (100.0, 0.0, 0.0)]
    field = ps.PavementField([ps.Ribbon("MAINLINE", main + [(100.0, 0.0, 110.0), (0.0, 0.0, 110.0)], [12.0] * 5, True),
                              ps.Ribbon("medium#2+0#0#0", side, [10.0] * 3, False)])
    assert field.gate_margin(50.0, 3.0) < 0 and field.gate_margin(50.0, 3.0, ("MAINLINE",)) > 50
    assert field.footprint_margin((50.0, 3.0), ((1.0, 0.0),), ("MAINLINE",)) > 50


def test_unknown_plate_or_knob_fails_loudly():
    ok_corners = {"M1": {"ribbon": "MAINLINE", "vertex": 0, "plate": "W1-6", "expect_arrow": "right", "where": "", "ship": "first", "note": ""}}
    ps.validate_overrides({"height_m": 2.13}, ok_corners)
    for cfg, corners in (({"skew_deg": 0.0}, ok_corners),
                         ({}, {"M1": {"ribbon": "MAINLINE", "vertex": 0, "plate": "W1-7"}}),
                         ({}, {"M1": {"ribbon": "MAINLINE", "vertex": 0, "skew": 3}}),
                         ({}, {"M1": {"ribbon": "MAINLINE", "vertex": 0, "arrow": "straight"}})):
        try:
            ps.validate_overrides(cfg, corners)
        except ps.SignsConfigError as e:
            assert "skew" in str(e) or "W1-7" in str(e) or "straight" in str(e)
        else:
            raise AssertionError("accepted %r %r" % (cfg, corners))
    assert "skew_deg" not in ps.DEFAULTS and "plate" in ps.CORNER_KEYS


def test_reverse_only_corners_get_their_own_ids_and_skips_dedupe():
    pts = [(float(i), 0.0, 0.0) for i in range(101)]          # 100 m straight: only n / closed / name matter here
    rb = ps.Ribbon("del_cerro_blvd#0", pts, [10.0] * len(pts), False, reverse=True)
    fwd = ps.Ribbon("del_cerro_blvd#0", pts, [10.0] * len(pts), False)
    assert ps.candidate_ids(fwd, [{"apex": 10, "sign": 1}, {"apex": 60, "sign": -1}], []) == ["DC0-c1", "DC0-c2"]
    fwd_ids = [(10, "DC0-c1", 1)]                             # one forward corner: a left at station 10
    corners = [{"apex": 5, "sign": -1},                       # fwd 95: nothing there -> reverse-only
               {"apex": 90, "sign": -1},                      # fwd 10, a right in reverse = that left -> DC0-c1
               {"apex": 95, "sign": 1}]                       # fwd 5, a left in reverse: the other way -> reverse-only
    assert ps.candidate_ids(rb, corners, fwd_ids) == ["DC0-r1", "DC0-c1", "DC0-r2"]
    sk = [{"id": "DC0-c1-rev", "ribbon": "del_cerro_blvd#0(rev)", "apex_station_m": 90, "reasons": ["a"]},
          {"id": "DC0-c1-rev", "ribbon": "del_cerro_blvd#0(rev)", "apex_station_m": 90, "reasons": ["b"]},
          {"id": "DC0-c1-fwd", "ribbon": "del_cerro_blvd#0", "apex_station_m": 10, "reasons": ["a"]}]
    out = ps.dedupe_skipped(sk)
    assert [s["id"] for s in out] == ["DC0-c1-rev", "DC0-c1-fwd"] and out[0]["reasons"] == ["a", "b"]


def _circle_ribbon(R, n=400, kappa_half=ps.KAPPA_HALF_WIN):
    pts = [(R * math.cos(2 * math.pi * i / n), 0.0, R * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return ps.Ribbon("ring", pts, [10.0] * n, True, kappa_half=kappa_half)


def _L_points():
    """straight in along +x, R 10 m quarter turn LEFT, straight out along +z"""
    pts = [(float(i), 0.0, 0.0) for i in range(0, 60)]
    pts += [(60.0 + 10 * math.sin(a), 0.0, 10 - 10 * math.cos(a)) for a in [k * math.pi / 40 for k in range(1, 21)]]
    pts += [(70.0, 0.0, 10.0 + i) for i in range(1, 60)]
    return pts


def test_detector_knobs_wired_through_cfg():
    rb = _circle_ribbon(40.0)
    assert abs(rb.kappa(10) - 1 / 40.0) < 0.002                  # CCW ring: +1/R over the 12 m window
    rb4 = _circle_ribbon(40.0, kappa_half=2)
    assert rb4.kappa_half == 2 and abs(rb4.kappa(10) - 1 / 40.0) < 0.002
    rev = rb.copy(reverse=True)
    assert rev.reverse and rev.kappa_half == rb.kappa_half and abs(rev.kappa(10) + 1 / 40.0) < 0.002
    # an L: straight in, R 10 m quarter turn, straight out — hysteresis sets where the PC lands
    pts = _L_points()
    rbL = ps.Ribbon("L", pts, [10.0] * len(pts), False)
    c6 = ps.detect_corners(rbL, 6)[0]
    c2 = ps.detect_corners(rbL, 2)[0]
    assert c6["sign"] == 1 and 8 < c6["R_apex_m"] < 13 and 80 < c6["D_deg"] < 100
    assert c2["PC"] >= c6["PC"] and c2["PT"] <= c6["PT"]        # a shorter straight run ends the corner sooner
    assert ps.DEFAULTS["kappa_window_m"] == 2 * ps.KAPPA_HALF_WIN and ps.DEFAULTS["hysteresis_stations"] == ps.HYSTERESIS


def test_verifier_rederives_approach_turn_and_side_from_the_centreline():
    line = vs.Line(_L_points(), False)
    A = (57.0, -2.5)                                             # a lane-offset launch point before the bend
    pc, t, dA = vs.approach(line, A)
    assert pc == 57 and abs(t[0] - 1.0) < 1e-6 and abs(t[1]) < 1e-6 and abs(dA - 2.5) < 1e-6
    sense, apex, dh = vs.turn_after(line, pc)
    assert sense == 1 and 62 <= apex <= 74 and dh > 50          # a LEFT turn, apex inside the arc
    # the failed-to-turn point lies right of travel = outside of a left turn
    cross, st, _ = vs.side_of(line, (77.0, -2.5), pc - 5, apex + 80)
    assert cross < 0 and -sense * cross > 0
    # the mirror image (a point on the inside) fails the side test
    cross_in, _, _ = vs.side_of(line, (60.0, 8.0), pc - 5, apex + 80)
    assert -sense * cross_in < 0
    # the reversed line turns RIGHT and the same chord logic finds it
    rline = vs.Line(_L_points(), False, reverse=True)
    pc_r, t_r, _ = vs.approach(rline, (70.0 + 2.5, 70.0))
    assert abs(t_r[1] + 1.0) < 1e-6 and vs.turn_after(rline, pc_r)[0] == -1


def test_spawn_points_union_every_layouts_dummies_with_the_old_file_as_fallback():
    """ledger 0047: a multi-layout build writes data/dummies.json = {} and the spawns ride in
    data/dummies_<id>.json — the sign-vs-spawn check must read every one of them"""
    import json
    import tempfile
    d = Path(tempfile.mkdtemp())
    # only the old single-layout file: it is the source (fallback)
    (d / "dummies.json").write_text(json.dumps({"AC_START_0": [1.0, 0.0, 2.0], "AC_TIME_0_L": [3.0, 0.0, 4.0]}))
    assert sorted(lab for _, lab in ps.spawn_points(d)) == ["AC_START_0@" + d.parent.name, "AC_TIME_0_L@" + d.parent.name]
    # per-layout files present: their UNION, the (now empty) old file ignored, metadata keys skipped
    (d / "dummies.json").write_text("{}")
    (d / "dummies_race_cw.json").write_text(json.dumps({"AC_START_0": [10.0, 0.0, 20.0], "AC_PIT_3": [11.0, 0.0, 21.0],
                                                         "_yaw_deg": {"AC_START_0": 1.0}, "_layout": "race_cw"}))
    (d / "dummies_race_acw.json").write_text(json.dumps({"AC_START_0": [30.0, 0.0, 40.0], "AC_HOTLAP_START_0": [30.0, 0.0, 40.0]}))
    pts = ps.spawn_points(d)
    assert sorted(lab for _, lab in pts) == ["AC_HOTLAP_START_0@race_acw", "AC_PIT_3@race_cw", "AC_START_0@race_acw", "AC_START_0@race_cw"]
    assert ((10.0, 20.0), "AC_START_0@race_cw") in pts and ((11.0, 21.0), "AC_PIT_3@race_cw") in pts
    # a non-empty stale dummies.json beside per-layout files is NOT read (the per-layout set is the truth)
    (d / "dummies.json").write_text(json.dumps({"AC_START_0": [999.0, 0.0, 999.0]}))
    assert all(p != (999.0, 999.0) for p, _ in ps.spawn_points(d))


# --- ledger 0051: arrows for every driven direction --------------------------------------------------------
def _square_loop(side=200.0, R=10.0, step=2.0):
    """a closed CLOCKWISE square, R 10 m rounded corners: increasing index = clockwise = four RIGHT turns;
    the first vertex repeated at the end (L13)"""
    pts = []
    x, z, h = 0.0, 0.0, 0.0                        # start heading east (+x)
    for _ in range(4):
        hx, hz = math.cos(math.radians(h)), math.sin(math.radians(h))
        L = side - 2 * R
        n = int(round(L / step))
        for k in range(n):
            pts.append((x + hx * k * step, 0.0, z + hz * k * step))
        x, z = x + hx * L, z + hz * L
        rx, rz = hz, -hx                           # the driver's right
        ccx, ccz = x + rx * R, z + rz * R
        a0 = math.atan2(z - ccz, x - ccx)
        for k in range(10):                        # quarter turn RIGHT (clockwise about the centre)
            a = a0 - (math.pi / 2) * k / 10
            pts.append((ccx + R * math.cos(a), 0.0, ccz + R * math.sin(a)))
        a = a0 - math.pi / 2
        x, z = ccx + R * math.cos(a), ccz + R * math.sin(a)
        h -= 90.0
    pts.append(pts[0])
    return pts


def _square_proj(tmp, layouts=None):
    import json
    d = Path(tmp)
    (d / "data").mkdir(parents=True, exist_ok=True)
    pts = _square_loop()
    (d / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": [list(p) for p in pts], "widths_m": [10.0] * len(pts)}))
    (d / "track.config.json").write_text(json.dumps({"slug": "zz_no_such_track_0051", "layouts": layouts or []}))
    return d, pts


def test_reverse_scan_mirrors_expect_arrow_and_covers_both_directions():
    import tempfile
    d, pts = _square_proj(tempfile.mkdtemp(), [{"id": "a", "direction": "forward"}, {"id": "b", "direction": "reverse"}])
    # the entry names the corner at (180, 0) for its FORWARD (clockwise) approach: a right-hander
    v1 = min(range(len(pts)), key=lambda i: math.dist((pts[i][0], pts[i][2]), (190.0, -3.0)))
    corners = {"M1": {"ribbon": "MAINLINE", "vertex": v1, "plate": "W1-6", "expect_arrow": "right"}}
    cfg = dict(ps.DEFAULTS, include_connectors=False, both_directions_mainline=True)
    quiet = lambda *a: None
    out, _ = ps.place_all(d, cfg, corners, log=quiet)
    fwd = [s for s in out["signs"] if s["direction"] == "fwd"]
    rev = [s for s in out["signs"] if s["direction"] == "rev"]
    assert len(fwd) == 4 and len(rev) == 4, ([s["id"] for s in out["signs"]], out["skipped"])
    assert all(s["arrow"] == "right" for s in fwd) and all(s["arrow"] == "left" for s in rev)
    by = {s["id"]: s for s in out["signs"]}
    assert by["M1-fwd"]["expect_arrow"] == "right" and by["M1-rev"]["expect_arrow"] == "left"
    assert any("mirrored" in a for a in by["M1-rev"]["overrides_applied"]) and by["M1-fwd"]["overrides_applied"] == []
    assert not any("expect_arrow" in r for s in out["skipped"] for r in s["reasons"])
    assert ps.direction_counts(out)["fwd"] == 4 and ps.direction_counts(out)["rev"] == 4
    # the verifier: (k) passes; (j) re-read from the entries (mirrored on rev) agrees with every plate
    f, rows = vs.direction_coverage(out, vs.driven_directions(d))
    assert f == [] and any("4 fwd" in r and "4 rev" in r for r in rows)
    for s in out["signs"]:
        assert vs.expected_arrow(corners.get(vs.parse_id(s["id"])[0]), s["direction"]) in (None, s["arrow"])
    # the knob OFF (v0.17.1): forward only, ids unsuffixed, and (k) fires for the reverse layout
    out0, _ = ps.place_all(d, dict(cfg, both_directions_mainline=False), corners, log=quiet)
    assert [s["direction"] for s in out0["signs"]] == ["fwd"] * 4 and "M1" in [s["id"] for s in out0["signs"]]
    f0, _ = vs.direction_coverage(out0, vs.driven_directions(d))
    assert len(f0) == 4 and all("never signed" in x for x in f0)
    # the trap 0051 found: a forward-only expect_arrow on the reverse approach skips it -> (k) FAILs, naming expect_arrow
    bad = {"M1": dict(corners["M1"], rev={"expect_arrow": "right"})}
    out1, _ = ps.place_all(d, cfg, bad, log=quiet)
    assert "M1-rev" in [s["id"] for s in out1["skipped"]]
    f1, _ = vs.direction_coverage(out1, vs.driven_directions(d))
    assert len(f1) == 1 and "expect_arrow" in f1[0] and "M1" in f1[0]
    # a per-approach skip with a reason IS coverage (Kevin's call, e.g. the M2 hairpin cross-view)
    skip = {"M1": dict(corners["M1"], rev={"skip": True, "reason": "Kevin: reads wrong from the seat"})}
    out2, _ = ps.place_all(d, cfg, skip, log=quiet)
    ids2 = [s["id"] for s in out2["signs"]]
    assert "M1-rev" not in ids2 and "M1-fwd" in ids2
    f2, rows2 = vs.direction_coverage(out2, vs.driven_directions(d))
    assert f2 == [] and any("Kevin" in r for r in rows2)
    # one driven direction: nothing to cover
    assert vs.direction_coverage(out0, {"fwd": ["street"]})[0] == []


def test_effective_override_and_pins():
    ov = {"ribbon": "MAINLINE", "vertex": 3, "arrow": "right", "expect_arrow": "right", "rev": {"skip": True, "reason": "r"}}
    f = ps.effective_override(ov, False)
    r = ps.effective_override(ov, True)
    assert f["expect_arrow"] == "right" and f["arrow"] == "right" and "skip" not in f and f["_mirrored"] == []
    assert r["expect_arrow"] == "left" and r["arrow"] == "left" and r["skip"] is True and sorted(r["_mirrored"]) == ["arrow", "expect_arrow"]
    assert "rev" not in r and "fwd" not in r and r["_direction_keys"] == ["reason", "skip"]
    # a sub-object's own arrow is that approach's, never mirrored
    r2 = ps.effective_override({"expect_arrow": "right", "rev": {"expect_arrow": "right"}}, True)
    assert r2["expect_arrow"] == "right" and r2["_mirrored"] == []
    assert ps.effective_override({}, True) == {}
    # pins: a top-level pin on a corner signed both ways is refused; inside fwd / rev it is fine
    on = dict(ps.DEFAULTS, both_directions_mainline=True)
    off = dict(ps.DEFAULTS)
    pin = {"M1": {"ribbon": "MAINLINE", "vertex": 0, "base_xz": [1.0, 2.0]}}
    ps.check_pins(off, pin)                                  # forward-only mainline: one plate, one pin
    for cfg, corners in ((on, pin), (off, {"MED-1": {"ribbon": "medium", "vertex": 0, "face_bearing_deg": 10.0}})):
        try:
            ps.check_pins(cfg, corners)
        except ps.SignsConfigError as e:
            assert ".fwd or corners." in str(e)
        else:
            raise AssertionError("accepted a two-way pin %r" % corners)
    ps.check_pins(on, {"M1": {"ribbon": "MAINLINE", "vertex": 0, "rev": {"base_xz": [1.0, 2.0]}}})
    # validation reaches into the sub-objects
    for bad in ({"M1": {"vertex": 0, "rev": {"ribbon": "X"}}}, {"M1": {"vertex": 0, "fwd": {"expect_arrow": "up"}}},
                {"M1": {"vertex": 0, "rev": "skip"}}):
        try:
            ps.validate_overrides({}, bad)
        except ps.SignsConfigError:
            pass
        else:
            raise AssertionError("accepted %r" % bad)


def test_missing_signs_path_is_an_error_but_no_signs_json_is_defaults():
    import json
    import tempfile
    d = Path(tempfile.mkdtemp())
    (d / "track.config.json").write_text(json.dumps({"slug": "zz_no_such_track_0051"}))
    try:
        ps.load_overrides(d, str(d / "nope.json"))
    except ps.SignsConfigError as e:
        assert "nope.json" in str(e)
    else:
        raise AssertionError("a missing --signs ran with no overrides")
    cfg, corners, p = ps.load_overrides(d)                     # the Lariat case: no signs.json at all
    assert cfg == ps.DEFAULTS and corners == {} and not p.exists()
    assert ps.DEFAULTS["both_directions_mainline"] is False   # opt-in per track: DEFAULTS unchanged


def test_race_furniture_is_never_the_signs_ground():
    import signs_mesh as sm                                    # importable outside Blender (the BVH half needs bpy)
    for n in ("1KERB_race_0_in", "1kerb_RACE_770_out", "1WALL_race_edge_L_alvarado_0_0", "1WALL_race_close_cw_3"):
        assert sm.is_race_furniture(n) and sm.surface_class(n) == "race"
    assert sm.surface_class("CURB") == "ground" and sm.surface_class("TERRAIN") == "ground"
    assert sm.surface_class("1KERB_sidewalk") == "ground" and sm.surface_class("ROAD") == "road"
    assert sm.surface_class("CURB_x", ["RACE"]) == "race" and sm.surface_class("TERRAIN_x", ["RACE_CLOSE_ACW"]) == "race"
    assert sm.surface_class("SIGNPOST_0", skip_prefixes=("SIGN",)) is None and sm.surface_class("PALM") is None
    # the verifier's FAIL: a record whose ground list carries a race kerb (the v0.17.1 loop.blend re-authored)
    rec = {"blender": {"ground_objects": ["1KERB_race_0_in", "CURB", "TERRAIN"], "road_objects": ["ROAD"]}}
    assert vs.race_ground(rec, None) == ["authoring ground_objects: 1KERB_race_0_in"]
    assert vs.race_ground({"blender": {"ground_objects": ["CURB", "TERRAIN"]}}, {"ground_objects": ["CURB"]}) == []


def test_verifier_ids_expectations_and_directions():
    assert vs.parse_id("M2-fwd-2") == ("M2", "fwd", True) and vs.parse_id("M2-2") == ("M2", None, True)
    assert vs.parse_id("MED-6-rev") == ("MED-6", "rev", False) and vs.parse_id("M-c5") == ("M-c5", None, False)
    assert vs.parse_id("M1") == ("M1", None, False) and vs.parse_id("M-c12-fwd") == ("M-c12", "fwd", False)
    e = {"expect_arrow": "right"}
    assert vs.expected_arrow(e, "fwd") == "right" and vs.expected_arrow(e, "rev") == "left"
    assert vs.expected_arrow(dict(e, rev={"expect_arrow": "right"}), "rev") == "right"
    assert vs.expected_arrow({}, "rev") is None and vs.expected_arrow(None, "fwd") is None
    import json
    import tempfile
    d = Path(tempfile.mkdtemp())
    (d / "track.config.json").write_text(json.dumps({"layouts": [{"id": "street", "direction": "forward"}, {"id": "full"},
                                                                   {"id": "race_acw", "direction": "reverse"}, {"id": "x", "direction": None}]}))
    assert vs.driven_directions(d) == {"fwd": ["street", "full", "x"], "rev": ["race_acw"]}
    (d / "track.config.json").write_text(json.dumps({"layouts": [{"id": "s", "direction": "sideways"}]}))
    try:
        vs.driven_directions(d)
    except ValueError:
        pass
    else:
        raise AssertionError("an unknown direction word was guessed")
    (d / "track.config.json").write_text("{}")
    assert list(vs.driven_directions(d)) == ["fwd"]


def test_a_skip_without_a_reason_is_refused_at_load():
    # the verifier's plant: M4 "rev": {"skip": true} with no reason dropped race_acw's Jackson/Navajo arrow silently
    for bad in ({"M4": {"ribbon": "MAINLINE", "vertex": 2320, "rev": {"skip": True}}},
                {"M4": {"ribbon": "MAINLINE", "vertex": 2320, "skip": True}},
                {"M4": {"ribbon": "MAINLINE", "vertex": 2320, "skip": True, "reason": "   "}},
                {"M4": {"ribbon": "MAINLINE", "vertex": 2320, "fwd": {"skip": True, "reason": ""}}}):
        try:
            ps.validate_overrides({}, bad)
        except ps.SignsConfigError as e:
            assert "M4" in str(e) and "no reason" in str(e)
        else:
            raise AssertionError("accepted a reasonless skip %r" % bad)
    ps.validate_overrides({}, {"M4": {"vertex": 0, "rev": {"skip": True, "reason": "Kevin: reads wrong"}}})
    ps.validate_overrides({}, {"M4": {"vertex": 0, "reason": "the entry's own", "rev": {"skip": True}}})
    ps.validate_overrides({}, {"M4": {"vertex": 0, "reason": "prose, no skip"}})


def test_direction_coverage_counts_only_the_rules_own_skips():
    def rec(reasons):
        return {"signs": [{"id": "M4-fwd", "ribbon": "MAINLINE", "direction": "fwd", "corner": {"second_arrow": False}}],
                "skipped": [{"id": "M4-rev", "ribbon": "MAINLINE(rev)", "reasons": reasons}]}
    both = {"fwd": ["street", "race_cw"], "rev": ["race_acw"]}
    fail = lambda reasons, entries=None: vs.direction_coverage(rec(reasons), both, entries=entries)[0]
    # the rule finding no arrow corner on that approach: coverage
    for ok in (["R_apex 42.1 > 30 m", "|D| 16.3 < 45 deg"], ["apex 12 m from medium#2 (< 25 m: mouth-flare geometry)"],
               ["ray exits pavement at 3.1 m (want 6-40)"], ["ray never leaves pavement within 40 m (through leg / junction)"],
               ["T-end: ray re-enters DCL within 3 m of the curb (W1-7 candidate, second pass)"],
               ["ray foot at station PC-14 is outside [PC, PT+10] (a curve, not a turn)"]):
        assert fail(ok) == [], ok
    # never coverage: no reason, a failed placement, expect_arrow, nothing at all
    for bad in (["signs.json skip: (no reason given)"], ["signs.json skip:   "], [],
                ["sign base is ON pavement (edge clearance -0.20)"],
                ["OUTSIDE ASSERTION FAILED: C is on the inside of the bend (cross 0.40)"],
                ["plate footprint inside drive_test's obstacle disc by 0.12 m"],
                ["lamp post base 1.1 m from the sign (< 2.0, lamps are never moved; no slide <= 6.0 m clears it)"],
                ["expect_arrow=right (rev) but the rule computed left (D 88.0 deg) — not relocated, see signs.json"],
                ["R_apex 42.1 > 30 m", "sign base is ON pavement (edge clearance -0.20)"]):
        f = fail(bad)
        assert len(f) == 1 and "M4" in f[0] and "race_acw" in f[0], (bad, f)
    # a signs.json skip with its reason: coverage — and, when this gate read signs.json, only if signs.json makes it
    kev = ["signs.json skip: Kevin: the cross-view reads wrong"]
    assert fail(kev) == []
    assert fail(kev, {"M4": {"vertex": 0, "rev": {"skip": True, "reason": "Kevin: the cross-view reads wrong"}}}) == []
    assert fail(kev, {"M4": {"vertex": 0, "skip": True, "reason": "both ways"}}) == []
    assert len(fail(kev, {})) == 1 and len(fail(kev, {"M4": {"vertex": 0, "rev": {"skip": True}}})) == 1
    assert len(fail(kev, {"M4": {"vertex": 0, "fwd": {"skip": True, "reason": "x"}}})) == 1   # skips the other approach
    # no record at all for the reverse approach
    r = rec([])
    r["skipped"] = []
    f = vs.direction_coverage(r, both)[0]
    assert len(f) == 1 and "never signed" in f[0]


def test_parse_id_tells_a_second_arrow_from_a_corner_named_dash_two():
    assert vs.parse_id("DC0-2", False) == ("DC0-2", None, False) and vs.parse_id("DCL-2", False) == ("DCL-2", None, False)
    assert vs.parse_id("DCL-2-rev", False) == ("DCL-2", "rev", False) and vs.parse_id("M2-2", True) == ("M2", None, True)
    assert vs.parse_id("M2-fwd-2", True) == ("M2", "fwd", True) and vs.parse_id("M1-rev", False) == ("M1", "rev", False)
    assert vs.plate_second({"corner": {"second_arrow": True}}) is True and vs.plate_second({}, {"corner": {}}) is None
    assert vs.plate_second({"id": "DC0-2"}, {"corner": {"second_arrow": False}}) is False
    # (k): a skipped "X-2" whose X was placed is X's hairpin extra (never coverage, never a corner of its own) ...
    both = {"fwd": ["a"], "rev": ["b"]}
    d = {"signs": [{"id": "M2-fwd", "ribbon": "MAINLINE", "direction": "fwd", "corner": {"second_arrow": False}},
                   {"id": "M2-rev", "ribbon": "MAINLINE", "direction": "rev", "corner": {"second_arrow": False}}],
         "skipped": [{"id": "M2-rev-2", "ribbon": "MAINLINE(rev)", "reasons": ["second arrow 1.1 m from the first (< 12)"]}]}
    assert vs.direction_coverage(d, both)[0] == []
    # ... but a forward-only corner NAMED "MX-2" (knob off, X never placed) is its own corner
    d = {"signs": [{"id": "MX-2", "ribbon": "MAINLINE", "direction": "fwd", "corner": {"second_arrow": False}}],
         "skipped": [{"id": "MX-2", "ribbon": "MAINLINE(rev)", "reasons": ["R_apex 42.1 > 30 m"]}]}
    f, rows = vs.direction_coverage(d, both)
    assert f == [] and any("MX-2: no plate for rev" in r for r in rows), (f, rows)

