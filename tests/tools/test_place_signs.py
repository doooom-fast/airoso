"""tools/place_signs.py — the pure-Python pieces of the W1-6 rule that the 2026-10-10 fix round
added or changed (ledger 0044): the pair merge, the capped curb slide, the detector knobs wired
through cfg, the paired-post polygons. Plain ``test_*`` functions for tests/run_tests.py (no
pytest, no bpy). The placement itself is exercised by the dry run on the real data, not here.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import place_signs as ps  # noqa: E402


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
        "arrow": arrow, "expect_arrow": None, "lateral_offset_m": 1.33, "height_m": 2.13, "om1_3": True, "skew_deg": 0.0,
        "checks": {"outside_cross": 1.0, "edge_clear_m": 1.4, "lamp_m": 50.0, "plant_m": 40.0, "plant_zone": "-",
                   "pushed_m": 0.0, "slid_m": slid, "lateral_step_m": 0.0, "gate_margin_m": 0.5, "mouth_m": 99.0,
                   "spawn_m": 500.0, "spawn": "-", "warnings": []},
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
    assert abs(p["base_xz"][0] - 10.15) < 1e-9 and abs(p["base_xz"][1] - 10.15) < 1e-9
    assert abs(p["pair_split_m"] - 0.42) < 0.01
    assert any("paired" in w for w in p["checks"]["warnings"]) and len(logs) == 1
    assert ps.merge_pairs(out) == out                            # idempotent
    assert ps.plates_of(p) == p["plates"] and ps.plates_of(c) == [c]


def test_paired_post_polygons_one_post_two_plates():
    a = _rec("X", "fwd", (0.0, 0.0), 0.0, "right")
    b = _rec("X", "rev", (0.4, 0.0), 30.0, "left")              # facings 30 deg apart -> stacked
    single = ps.sign_polygons(a, 0.0)
    pair = ps.sign_polygons(ps.merge_pairs([a, b])[0], 0.0)
    assert len(pair["SIGNARROW"]) == 2 * len(single["SIGNARROW"])         # two arrows + two borders
    assert len(pair["SIGNPLATE"]) == 2 * len(single["SIGNPLATE"]) - 1     # the stacked plate has no diamond
    post_faces = 5                                                         # four sides + top
    assert len(single["SIGNPOST"]) == 2 + post_faces                       # plate back + diamond back + post
    assert len(pair["SIGNPOST"]) == 3 + post_faces                         # ONE post, three backs
    top_single = max(v[1] for verts, _ in single["SIGNPOST"] for v in verts)
    top_pair = max(v[1] for verts, _ in pair["SIGNPOST"] for v in verts)
    assert abs(top_pair - top_single - ps.PLATE_H - ps.PAIR_STACK_GAP) < 1e-9   # the post grows by one plate
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

    def nearest_lamp(self, q):
        return min((math.dist(q, b) for b in self.lamps), default=float("inf"))

    def nearest_plant(self, q):
        return min(((math.dist(q, p[:2]), p[2], p[3]) for p in self.plants), default=(float("inf"), "-", -1))

    def footprint_margin(self, base, rights):
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
    # a candidate that would stand inside the disc is skipped
    ctx = _Ctx(plants=[(-2.45, 0.0, "palms", 2)], margin=-0.1)
    slid, q, lamp, plant, excl, reasons = ps.choose_slide(ctx, CFG, S, u, 1.33, clear, rights=((0.0, 1.0),))
    assert slid == 0.0 and excl is not None


def _circle_ribbon(R, n=400, kappa_half=ps.KAPPA_HALF_WIN):
    pts = [(R * math.cos(2 * math.pi * i / n), 0.0, R * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return ps.Ribbon("ring", pts, [10.0] * n, True, kappa_half=kappa_half)


def test_detector_knobs_wired_through_cfg():
    rb = _circle_ribbon(40.0)
    assert abs(rb.kappa(10) - 1 / 40.0) < 0.002                  # CCW ring: +1/R over the 12 m window
    rb4 = _circle_ribbon(40.0, kappa_half=2)
    assert rb4.kappa_half == 2 and abs(rb4.kappa(10) - 1 / 40.0) < 0.002
    rev = rb.copy(reverse=True)
    assert rev.reverse and rev.kappa_half == rb.kappa_half and abs(rev.kappa(10) + 1 / 40.0) < 0.002
    # an L: straight in, R 10 m quarter turn, straight out — hysteresis sets where the PC lands
    pts = [(float(i), 0.0, 0.0) for i in range(0, 60)]
    pts += [(60.0 + 10 * math.sin(a), 0.0, 10 - 10 * math.cos(a)) for a in [k * math.pi / 40 for k in range(1, 21)]]
    pts += [(70.0, 0.0, 10.0 + i) for i in range(1, 60)]
    rbL = ps.Ribbon("L", pts, [10.0] * len(pts), False)
    c6 = ps.detect_corners(rbL, 6)[0]
    c2 = ps.detect_corners(rbL, 2)[0]
    assert c6["sign"] == 1 and 8 < c6["R_apex_m"] < 13 and 80 < c6["D_deg"] < 100
    assert c2["PC"] >= c6["PC"] and c2["PT"] <= c6["PT"]        # a shorter straight run ends the corner sooner
    assert ps.DEFAULTS["kappa_window_m"] == 2 * ps.KAPPA_HALF_WIN and ps.DEFAULTS["hysteresis_stations"] == ps.HYSTERESIS
