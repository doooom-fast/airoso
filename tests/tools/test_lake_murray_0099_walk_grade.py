"""Ledger 0099 round 1c — Lake Murray's street drops: the walk's back grade (tools/author_walk_grade_blend.py, opt-in
route.walk_back_grade).

The draft's curb + walk (scripts-v021 geometry/ribbon.curb_sidewalk, Lake Murray's EDGE_DEFAULTS) falls 0.34 m over its
1.2 m back grade; drive_test's excursion sweep reads each 0.5 m step of it as a 0.142 m drop (> 0.12). The step raises
every back-grade lip so no edge up to the walk's back edge is steeper than max_slope; nothing else moves. Tested here on
strips the draft's own sweep builds (straight, curved, on a grade, banked), read by drive_test's own TriField, plus the
config, the chain wiring, the holds and the refusals. The Blender half (open, move, read back, save) is exercised by the
Mac rehearsal in the ledger, not here.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LM = ROOT / "tracks" / "san-diego-lake-murray"
CFG = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))
SHIP = json.loads((LM / "ship.json").read_text(encoding="utf-8"))
SH = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8").replace("\r\n", "\n")
OTHER_CONFIGS = sorted(p for p in (ROOT / "tracks").glob("*/track.config.json") if p.parent.name != LM.name)
OTHER_SPECS = sorted(p for p in (ROOT / "tracks").glob("*/ship.json") if p.parent.name != LM.name)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


WG = _load("author_walk_grade_0099", ROOT / "tools" / "author_walk_grade_blend.py")
RB = _load("_v021_ribbon_walk_grade", LM / "scripts-v021" / "geometry" / "ribbon.py")
sys.path.insert(0, str(ROOT))
from scripts.geometry.drive_test import TriField  # noqa: E402

MAIN, CONN = RB.edge_profile(CFG.get("route"))      # Lake Murray declares no route.edge: the draft's own profile
SLOPE = CFG["route"]["walk_back_grade"]["max_slope"]


def _strip(pts, w=13.0, **kw):
    """the draft's strip for a centreline (engine frame) -> (scene co [(x, y, z) z up], edges, engine verts, tris)"""
    s = RB.curb_sidewalk(pts, [w] * len(pts), **dict(MAIN, **kw))
    v = s["vertices"]
    co = [(p[0], p[2], p[1]) for p in v]
    edges = set()
    for a, b, c in s["tris"]:
        for p, q in ((a, b), (b, c), (c, a)):
            edges.add((min(p, q), max(p, q)))
    return co, sorted(edges), v, s["tris"]


def _straight(n=12, step=3.0, grade=0.0):
    return [(i * step, grade * i * step, 0.0) for i in range(n)]


def _arc(n=30, r=40.0, step=3.0):
    return [(r * math.sin(i * step / r), 0.0, r - r * math.cos(i * step / r)) for i in range(n)]


def _apply(co, moves):
    return [(c[0], c[1], moves.get(i, c[2])) for i, c in enumerate(co)]


def _sweep_drops(co, tris, pts, w=13.0, ground=-0.02 + 0.10):
    """drive_test's excursion sweep, both sides of every interior station: the highest surface every 0.5 m from the lane
    edge out 9 m over the strip + a ground sheet at the prep's pin (lane edge - GROUND_CLEAR, the draft's lane edge 0.10
    over the centre line), swept along the line 25 m each side; falls > 0.12 m between samples"""
    eng = [(c[0], c[2], c[1]) for c in co]
    f = TriField()
    for t in tris:
        f.add(eng, t, "1KERB_sidewalk")
    gv, flat = [], TriField()
    for i, p in enumerate(pts):
        tx, tz = RB._horiz_tangent(pts, i, False)
        for o in (w / 2 + 25.0, -(w / 2 + 25.0)):
            gv.append((p[0] - tz * o, p[1] + ground, p[2] + tx * o))
    for i in range(len(pts) - 1):
        a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3
        flat.add(gv, (a, b, d), "1GRASS_0")
        flat.add(gv, (a, d, c), "1GRASS_0")
    drops = []
    for i in range(2, len(pts) - 2):
        tx, tz = RB._horiz_tangent(pts, i, False)
        for sgn in (1.0, -1.0):
            nx, nz = -tz * sgn, tx * sgn
            prev = None
            off = w / 2 - 0.5
            while off <= w / 2 + 9.0:
                x, z = pts[i][0] + nx * off, pts[i][2] + nz * off
                hs = [h for h, _ in (f.top_at(x, z, pts[i][1], 8.0), flat.top_at(x, z, pts[i][1], 8.0)) if h is not None]
                y = max(hs) if hs else None
                if y is not None and prev is not None and prev - y > 0.12:
                    drops.append((i, sgn, round(off, 1), round(prev - y, 3)))
                if y is not None:
                    prev = y
                off += 0.5
    return drops


# --- the draft's grade, found and re-authored -------------------------------------------------------------------
def test_the_lips_are_exactly_the_strips_outer_row_and_the_tops_its_walk_back():
    for pts in (_straight(), _arc(), _straight(grade=0.12)):
        co, edges, _, _ = _strip(pts)
        lips = WG.lip_edges(co, edges)
        rows = len(co) // 8                         # 2 sides x 4 profile points a row
        assert sorted(lips) == [r * 4 + 3 for r in range(2 * rows)]
        assert all(h % 4 == 2 for ups in lips.values() for h, _, _ in ups)
        cross = [dh for ups in lips.values() for h, dh, _ in ups if h == min(u for u, _, _ in ups)]
        assert min(cross) > 1.19 and max(cross) < 1.21


def test_the_draft_grade_reads_a_drop_every_step_and_the_re_authored_one_none():
    for pts in (_straight(), _arc(), _straight(grade=0.12)):
        co, edges, _, tris = _strip(pts)
        before = _sweep_drops(co, tris, pts)
        assert before and all(0.12 < d[3] <= 0.143 for d in before)      # the 0.142 m class of the 96
        p = WG.plan(co, edges, SLOPE)
        after = _sweep_drops(_apply(co, p["moves"]), tris, pts)
        assert after == [], after[:4]


def test_only_lips_move_only_up_and_to_the_declared_slope():
    co, edges, _, _ = _strip(_arc())
    p = WG.plan(co, edges, SLOPE)
    assert set(p["moves"]) == set(p["lips"]) and p["already"] == 0
    for v, z in p["moves"].items():
        assert z > co[v][2]
        assert abs(max(co[h][2] - SLOPE * dh for h, dh, _ in p["lips"][v]) - z) < 1e-9
    new = _apply(co, p["moves"])
    f = WG.falls(new, p["lips"])
    assert f["slope"]["max"] <= SLOPE + 1e-9
    assert abs(f["fall_m"]["p50"] - SLOPE * 1.2) < 0.005
    b = WG.falls(co, p["lips"])
    assert abs(b["fall_m"]["p50"] - 0.34) < 1e-6 and abs(b["slope"]["p50"] - 0.34 / 1.2) < 0.002


def test_the_lip_sits_at_the_centre_line_under_the_pinned_ground():
    """at 0.20 the lip lies 0.24 m under the walk top = the centre line's own height: 0.10 m under the lane edge and
    0.08 m under the prep's pinned ground (lane edge - 0.02), so the grass still covers the strip's outer edge"""
    pts = _straight()
    co, edges, _, _ = _strip(pts)
    p = WG.plan(co, edges, SLOPE)
    for v, z in p["moves"].items():
        assert abs(z - 0.0) < 1e-9


def test_a_second_run_moves_nothing():
    co, edges, _, _ = _strip(_straight(grade=0.08))
    p1 = WG.plan(co, edges, SLOPE)
    co2 = _apply(co, p1["moves"])
    p2 = WG.plan(co2, edges, SLOPE)
    assert p2["moves"] == {} and p2["already"] == len(p1["lips"]) and set(p2["lips"]) == set(p1["lips"])


def test_a_lip_under_pavement_rises_only_to_just_under_it_and_a_red_plan_vertex_stays():
    co, edges, _, _ = _strip(_straight())
    lips = sorted(WG.lip_edges(co, edges))
    a, b = lips[2], lips[3]

    def pave_at(x, y, z_lo, z_hi):                  # a side street's deck between lip a's old height and its target
        return [-0.02] if (abs(x - co[a][0]) < 1e-6 and abs(y - co[a][1]) < 1e-6) else []
    p = WG.plan(co, edges, SLOPE, pave_at, red_xyz=[co[b]])
    assert abs(p["moves"][a] - (-0.02 - WG.PAVE_UNDER_M)) < 1e-9 and a in p["capped"]
    assert b not in p["moves"] and p["held_red"] == [[round(c, 3) for c in co[b]]]
    assert len(p["held_pavement"]) == 1


def test_a_lip_over_released_ground_never_rises_over_it():
    """in a ground-release zone the prep leaves the 3DEP earth unpinned: a lip is raised at most GROUND_UNDER_M under it,
    and where the earth is lower than the lip already the lip stays where the draft put it"""
    co, edges, _, _ = _strip(_straight())
    lips = sorted(WG.lip_edges(co, edges))
    a, b, c = lips[2], lips[3], lips[4]
    earth = {a: -0.05, b: -0.40}                     # a: between the old lip (-0.10) and its target (0.0); b: under both

    def ground_at(x, y, z):
        for v, g in earth.items():
            if abs(x - co[v][0]) < 1e-6 and abs(y - co[v][1]) < 1e-6:
                return g
        return None
    p = WG.plan(co, edges, SLOPE, ground_at=ground_at)
    assert abs(p["moves"][a] - (-0.05 - WG.GROUND_UNDER_M)) < 1e-9 and a in p["capped"]
    assert b not in p["moves"] and len(p["held_ground"]) == 2
    assert abs(p["moves"][c] - 0.0) < 1e-9 and c not in p["capped"]      # outside every zone: the full raise


def test_a_lip_under_furniture_keeps_the_seat_the_draft_gave_it():
    co, edges, _, _ = _strip(_straight())
    lips = sorted(WG.lip_edges(co, edges))
    p = WG.plan(co, edges, SLOPE, furnished={lips[1], lips[5]})
    assert lips[1] not in p["moves"] and lips[5] not in p["moves"] and len(p["held_furniture"]) == 2
    assert all(v in p["moves"] for v in lips if v not in (lips[1], lips[5]))
    assert "1WALL" in WG.FURNITURE and "GUARDRAIL" in WG.FURNITURE and not any(f.startswith("LIGHT") for f in WG.FURNITURE)


def test_the_seat_lowers_a_lip_over_the_ground_onto_it_never_past_the_draft_grade():
    co, edges, _, _ = _strip(_straight())
    p = WG.plan(co, edges, SLOPE)
    raised = _apply(co, p["moves"])
    lips = WG.lip_edges(raised, edges)
    vs = sorted(lips)
    a, b, c = vs[1], vs[2], vs[3]
    ground = {a: -0.02, b: -0.60, c: 0.20}           # a: a little under the raised lip; b: a deep fill; c: over it

    def ground_at(x, y, z):
        for v, g in ground.items():
            if abs(x - raised[v][0]) < 1e-6 and abs(y - raised[v][1]) < 1e-6:
                return g
        return 0.5                                    # everywhere else the ground stands over the lip
    moves, at_floor = WG.seat_plan(raised, lips, ground_at)
    assert set(moves) == {a, b}
    assert abs(moves[a] - (-0.02 - WG.GROUND_UNDER_M)) < 1e-9
    assert abs(moves[b] - co[b][2]) < 1e-9 and at_floor == 1                 # the draft's own lip, no lower
    again, _ = WG.seat_plan(_apply(raised, moves), lips, ground_at)
    assert again == {}                                                         # a second seat moves nothing


def test_the_release_zones_are_the_preps_own():
    """tools/ground_release.Zones over Lake Murray's data/ground_release.json: every zone the file declares is found, on
    the line it names"""
    z = WG.release_zones(LM)
    R = json.loads((LM / "data" / "ground_release.json").read_text(encoding="utf-8"))
    assert z is not None and len([q for q in z.zones if q is not None]) == len(R["zones"])
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "data").mkdir()
        assert WG.release_zones(Path(tmp)) is None


def test_the_curb_face_and_the_walk_are_never_lips():
    co, edges, _, _ = _strip(_straight(grade=0.15, step=1.2))        # rows 1.2 m apart up a 15 % grade
    lips = WG.lip_edges(co, edges)
    assert all(v % 4 == 3 for v in lips)


# --- the opt-in, the refusals, the wiring ------------------------------------------------------------------------
def test_spec_reads_the_key_and_refuses_a_slope_the_gate_would_read_as_a_drop():
    assert WG.spec({}) is None and WG.spec({"route": {}}) is None
    assert WG.spec({"route": {"walk_back_grade": {"max_slope": 0.2}}}) == {"max_slope": 0.2, "objects": ["CURB"]}
    for bad in (0.24, 0.3, 0.05, True, "0.2", None):
        try:
            WG.spec({"route": {"walk_back_grade": {"max_slope": bad}}})
        except SystemExit:
            continue
        raise AssertionError(bad)
    try:
        WG.spec({"route": {"walk_back_grade": 0.2}})
    except SystemExit:
        pass
    else:
        raise AssertionError("a bare number")


def test_lake_murray_opts_in_and_no_other_track_does():
    w = CFG["route"]["walk_back_grade"]
    assert w["max_slope"] == 0.2 and "[invented]" in w["_doc"]
    assert w["objects"] == ["CURB", "1KERB_sidewalk_padJ2", "1KERB_sidewalk_padJ3", "1KERB_sidewalk_padJ4",
                            "1KERB_sidewalk_apAP1"]
    assert WG.spec(CFG) == {"max_slope": 0.2, "objects": w["objects"]}
    for p in OTHER_CONFIGS:
        assert "walk_back_grade" not in (json.loads(p.read_text(encoding="utf-8")).get("route") or {}), p


def test_walk_grade_is_an_author_step_before_the_race_steps_and_lake_murrays_alone():
    au = SHIP["steps"]["author"]
    # (ledger 0055 round 2: college_split first, so the walks it rebuilds are graded here with every other)
    assert au[:5] == ["college_split", "median_rebuild", "median_tops", "lamp_heads", "walk_grade"] and au[-3:] == ["race_author", "signs", "race_verify"]
    assert "author_walk_grade() {" in SH and "tools/author_walk_grade_blend.py" in SH
    assert "data/walk_grade.json" in SHIP["sync_out"]["files"] and "data/walk_grade.seat.json" in SHIP["sync_out"]["files"]
    seat = SH[SH.index("prep_prep() {"):SH.index("prep_split() {")]
    assert "author_walk_grade_blend.py\" -- \"$PROJ/blender/$SLUG.blend\" --project \"$PROJ\" --seat" in seat
    assert seat.index("red_repairs_blend.py") < seat.index("--seat")          # after the red repairs, which match by place
    assert "get('walk_back_grade')" in seat                                    # opt-in: no key, no header
    for p in OTHER_SPECS:
        steps = json.loads(p.read_text(encoding="utf-8"))["steps"]
        assert "walk_grade" not in [n for ph in steps.values() if isinstance(ph, list) for n in ph], p


def test_not_opted_in_the_step_removes_a_stale_report_and_opens_no_blend():
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp)
        (proj / "data").mkdir()
        cfg = json.loads(json.dumps(CFG))
        del cfg["route"]["walk_back_grade"]
        (proj / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
        (proj / "data" / WG.REPORT).write_text("{}", encoding="utf-8")
        assert WG.main([str(proj)]) == 0 and not (proj / "data" / WG.REPORT).exists()


def test_the_gate_is_untouched():
    """the fix is geometry: drive_test's drop line and its lap rule are what they were"""
    src = (ROOT / "scripts" / "geometry" / "drive_test.py").read_text(encoding="utf-8")
    assert "prev_y - ey > 0.12 and off > we - 0.5" in src
    assert 'report["excursion_drops"] > int(report["lap_m"] / 1000)' in src
