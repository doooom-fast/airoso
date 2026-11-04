"""Ledger 0054 Phase 2 (Mission Gorge Speedway): the NOSE closure end and the station smoothing window, opt-in through the
race declaration (race.corridor.noses, race.corridor.smooth_window), across the five tools that carry a closure:
tools/race_corridor.py (the pin on the island's race face), tools/barrier_bands.py (declared, self-gated, the K-rail
across the far carriageway in corridors.<id>.nose_walls), tools/race_furniture.py (+ the Blender author: the K-rail as a
closure object), tools/verify_race.py (C' / J on it) and tools/no_route.py (its polyline in the planned fill).

  * synthetic: nose_open's pin and open walk, the pin at the island face, solve() without noses unchanged, the declared
    refusals, the smooth_window option;
  * Lake Murray v4's north lap with tracks/san-diego-lake-murray/source/expansion/phase2/race.north.declaration.json
    (plan_north.py into a temp dir, once): every self-gate clear, all 34 exits sealed in both layouts, planned no_route
    PASS, three K-rails per layout on the far strip, the pin-zone rates within 2 %, the kerbs clear of the K-rails, the
    mainline declaration unchanged; the K-rails carry the seal (no_route leaks without them); verify_race passes the
    planned furniture laid as the author lays it and refuses a K-rail short of the far strip.

The byte-identity of every tool's output with no nose declared (the existing Lake Murray Speedways) is ledger 0054's
"Phase 2 — the nose end" proof (old tree vs new on v4's project); here the in-process half: solve(nose_pins=None)
is solve(). Plain ``test_*``.
"""
from __future__ import annotations

import copy
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import barrier_bands as bands  # noqa: E402
import no_route as nr  # noqa: E402
import race_corridor as rc  # noqa: E402
import race_furniture as rf  # noqa: E402
import verify_race as vr  # noqa: E402

PHASE2 = ROOT / "tracks" / "san-diego-lake-murray" / "source" / "expansion" / "phase2"
_C: dict = {}


# --- synthetic --------------------------------------------------------------------------------------------------
def _straight(n=120, w=26.0, isl=(40, 80), iw=2.0, step=3.0):
    pts = [(0.0, 0.0, step * k) for k in range(n)]
    pts.append(pts[0])                    # closed for ring_count: a ring of n (the seam is never inside a run here)
    widths = [w] * (n + 1)
    island = [iw if isl[0] <= k <= isl[1] else 0.0 for k in range(n + 1)]
    return pts, widths, island


def test_nose_open_gives_the_pin_beside_the_nose_and_the_open_walk():
    n = 120
    assert rc.nose_open(10, 40, (10, 100), n) == (39, list(range(10, 40)))
    assert rc.nose_open(100, 80, (10, 100), n) == (81, list(range(81, 101)))
    assert rc.nose_open(10, 10, (10, 100), n) is None          # the nose at the box edge itself
    assert rc.nose_open(10, 105, (10, 100), n) is None         # outside the run
    assert rc.nose_open(55, 40, (10, 100), n) is None          # not a run end


def test_solve_without_noses_is_unchanged_and_with_them_pins_on_the_island_face():
    pts, widths, island = _straight()
    n = rc.ring_count(pts)
    p = rc.params_from({})
    ctx = rc.prepare(pts, widths, island, p)

    def free(v):
        return not rc.in_rng(v, 10, 100, n) or v in (10, 100)
    for d in ("cw", "acw"):
        a = rc.solve(pts, widths, island, free, d, p, context=ctx)
        for kw in ({"nose_pins": None}, {"nose_pins": {}}):
            b = rc.solve(pts, widths, island, free, d, p, context=ctx, **kw)
            assert [r["g"] for r in a["runs"]] == [r["g"] for r in b["runs"]], (d, kw)
        # the diagonal from the far strip at v10 to the island's race face at v40 is what the noses replace
        r = a["runs"][0]
        assert abs(r["g"][0] - r["g_far"][0]) < 1e-9

    def free_n(v):
        return free(v) or rc.in_rng(v, 10, 39, n) or rc.in_rng(v, 81, 100, n)
    g_pin = rc.nose_pin_g(ctx, 40)
    assert abs(g_pin - (1.0 + rc.INSET_M - rc.BARRIER_HALF_M)) < 1e-9     # the 2.0 m island's face + the strip centre
    assert abs(rc.nose_pin_g(ctx, 80) - g_pin) < 1e-9
    for d in ("cw", "acw"):
        s = rc.solve(pts, widths, island, free_n, d, p, context=ctx, nose_pins={39: 40, 81: 80})
        assert len(s["runs"]) == 1
        r = s["runs"][0]
        assert {r["vs"][0], r["vs"][-1]} == {39, 81}
        assert abs(r["g"][0] - g_pin) < 1e-9 and abs(r["g"][-1] - g_pin) < 1e-9
        # beside the island the closure stands on its race face (the authored half + the strip centre), never inside
        for v, g, isl in zip(r["vs"], r["g"], r["isl"]):
            if isl is not None:
                assert g >= isl - 1e-6, (d, v, g, isl)


def test_declared_noses_are_refused_unless_they_are_real_noses():
    pts, widths, island = _straight()
    m = rc.ring_count(pts)
    st = rc.stations(pts)
    pinned = [(10, 100)]
    ok, fails = bands._noses([{"end": 10, "median": 40}, {"end": 100, "median": 80}], pinned, island, m, st, 0.335)
    assert not fails and [(x["end"], x["median"], x["pin"]) for x in ok] == [(10, 40, 39), (100, 80, 81)]
    for bad, why in (([{"end": 12, "median": 40}], "not an end"), ([{"end": 10, "median": 41}], "not the first"),
                     ([{"end": 10, "median": 80}], "not the first"),
                     ([{"end": 10, "median": 40}, {"end": 10, "median": 40}], "declared twice"),
                     ([{"end": 10}], "integer end and median"), ({"end": 10}, "must be a list")):
        _ok, f = bands._noses(bad, pinned, island, m, st, 0.335)
        assert any(why in x for x in f), (bad, f)
    _p, _w, at_box = _straight(isl=(11, 80))                                   # a nose right beside the box edge
    _ok, f = bands._noses([{"end": 10, "median": 11}], pinned, at_box, m, st, 0.335)
    assert any("nothing to end" in x for x in f), f
    two = [w if not 20 <= k <= 30 else 1.5 for k, w in enumerate(island)]   # another island between box and nose
    _ok, f = bands._noses([{"end": 10, "median": 40}], pinned, two, m, st, 0.335)
    assert any("not the first" in x or "between the box edge" in x for x in f), f
    assert bands._noses(None, pinned, island, m, st, 0.335) == ([], [])


def test_smooth_window_is_opt_in():
    assert "smooth_window" not in rc.params_from({})
    assert "smooth_window" not in rc.params_from({"smooth_window": "vertices"})
    assert rc.params_from({"smooth_window": "station"})["smooth_window"] == "station"
    try:
        rc.params_from({"smooth_window": "index"})
    except ValueError:
        pass
    else:
        raise AssertionError("an unknown smooth_window must be refused")


# --- Lake Murray v4's north lap ----------------------------------------------------------------------------------
def _plan():
    if "plan" not in _C:
        sys.path.insert(0, str(PHASE2))
        import plan_north  # noqa: E402
        out = Path(tempfile.mkdtemp(prefix="north_noses_"))
        rcode = plan_north.main([str(out)])
        _C["plan"] = (rcode, json.loads((out / "plan_north.json").read_text()), out)
    return _C["plan"]


def _lap(out):
    lap = json.loads((out / "data" / "lap.north.json").read_text())
    return [tuple(p) for p in lap["points_xyz_m"]], [float(w) for w in lap["widths_m"]], lap["island_w_by_vertex"]


def test_the_north_plan_clears_every_self_gate_and_seals_all_34_exits():
    rcode, rep, out = _plan()
    assert rcode == 0 and rep["status"] == "PLANNED" and not rep["fails"], rep["fails"][:6]
    assert rep["exit_counts"] == {"side_street": 26, "pad_arm": 6, "branch": 2}
    for lid in ("north_cw", "north_acw"):
        assert sum(1 for e in rep["exits"] if e[lid]["planned"] == "sealed") == 34, lid
        pl = rep["planned_no_route"][lid]
        assert pl["fail"] is False and pl["leak_m2"] == 0 and not pl["forbidden_reached"] and not pl["blocked"], pl
    assert rep["mainline_declaration_unchanged"] and rep["source_unchanged"]


def test_the_north_k_rails_stand_across_the_far_carriageway_at_the_three_noses():
    _r, _rep, out = _plan()
    b = json.loads((out / "data" / "barrier_bands.north.json").read_text())
    pts, widths, _iw = _lap(out)
    assert [(x["end"], x["median"], x["pin"]) for x in b["zones"]["noses"]] == [(2, 11, 10), (314, 306, 307), (713, 718, 717)]
    sc = b["params"]["edge_inset_m"] - b["params"]["barrier_half_m"]
    for lid, c in b["corridors"].items():
        e = -1.0 if c["race_side"] == "R" else 1.0
        walls = {w["vertex"]: w for w in c["nose_walls"]}
        assert sorted(walls) == [10, 307, 717], lid
        for k, w in walls.items():
            assert c["zone_by_vertex"][k] == "pin" and k in c["pins"]
            assert abs(w["y_to"] - (-e * (widths[k] / 2.0 - sc))) < 1e-3, (lid, k)            # on the far strip
            assert abs(w["y_from"] - (c["closure_y_by_vertex"][k] + e * b["params"]["barrier_half_m"])) < 1e-3
            lo, hi = c["lane_by_vertex"][k]                       # the lane at the pin is the closure's, not the street
            assert hi - lo < widths[k] - 2 * b["params"]["edge_inset_m"] - 1.0, (lid, k, lo, hi)
            assert 14.0 < w["length_m"] < 17.5, (lid, k, w["length_m"])
        ends = [en for r in c["runs"] for en in r["ends"]]
        assert sorted(en["vertex"] for en in ends if en["joins"] == "nose") == [10, 307, 717], lid
        # the box edges the noses replace carry no closure; the open walk to the pin is box-like, its lane the whole
        # street but for the one vertex before the K-rail, which takes the closure's lane (a lerped lane never sweeps
        # the K-rail: drive_test, write_ai_line)
        for v in (2, 5, 9, 308, 313, 713, 716):
            assert c["closure_y_by_vertex"][v] is None and c["zone_by_vertex"][v] == "box", (lid, v)
        for k, nb, far in ((10, 9, 8), (307, 308, 309), (717, 716, 715)):
            assert c["lane_by_vertex"][nb] == c["lane_by_vertex"][k], (lid, nb)
            lo, hi = c["lane_by_vertex"][far]
            assert hi - lo > widths[far] - 2 * b["params"]["edge_inset_m"] - 0.01, (lid, far)
    # each layout's K-rails are declared bands of that layout alone (median_zone: audit D / drive_test exempt them)
    from scripts.geometry.median_zone import MedianZone, ALL_KINDS
    for lid in ("north_cw", "north_acw"):
        z = MedianZone.load(out, layout=lid)              # a layout on a lap is zoned on its lap (race_lap)
        for w in b["corridors"][lid]["nose_walls"]:
            (ax, _a, az), (bx, _b, bz) = w["polyline_xyz_m"]
            assert z.contains((ax + bx) / 2, (az + bz) / 2, ALL_KINDS), (lid, w["vertex"])
    # the pin-zone rates the vertex window broke (v683-685, v1477-1479) hold with the station window
    for lid, c in b["corridors"].items():
        for r in c["runs"]:
            for key in ("pin_in", "pin_out"):
                assert r["max_rate"][key + "_built"] >= r["max_rate"][key] / 1.02 - 1e-6, (lid, r["i"], r["j"], r["max_rate"])


def test_the_kerbs_stand_clear_of_the_k_rails_and_j1_j5_insides_stay_held():
    _r, _rep, out = _plan()
    b = json.loads((out / "data" / "barrier_bands.north.json").read_text())
    pts, widths, iw = _lap(out)
    plans = [p for lid in sorted(b["corridors"]) for p in rf.closure_plans(pts, widths, b, lid)]
    noses = [p for p in plans if p.get("wall") == "nose"]
    assert sorted(rf.object_name(p) for p in noses) == [f"1WALL_race_close_{t}_nose_{k}_0" for t in ("nacw", "ncw")
                                                       for k in (10, 307, 717)]
    for p in noses:
        assert all(math.dist(rf._strip_xz(a), rf._strip_xz(q)) <= rf.NOSE_RING_M + 1e-6 for a, q in zip(p["rings"], p["rings"][1:]))
        assert [x["joins"] for x in p["pins"]] == ["closure", "edge_" + p["side"]]
        assert rf.race_owner(rf.object_name(p)) == p["token"] and rf.race_role(rf.object_name(p)) == "close"
    clips = {(r["apex"], r["kind"]): r for r in rf.kerb_closure_clips(pts, widths, b)}
    assert clips[(320, "outside")]["i"] == 308 and clips[(707, "outside")]["j"] == 716     # stopped short of the K-rails
    assert all((r["min_clear_m"] is None or r["min_clear_m"] >= rf.KERB_CLOSURE_CLEAR_M - 1e-6) for r in clips.values())
    dropped = {(d["apex"], d["kind"]) for d in b["kerbs_dropped"]}
    assert dropped == {(2130, "inside"), (2932, "inside")}                                   # held, as declared


def test_the_k_rails_carry_the_seal():
    _r, _rep, out = _plan()
    b = json.loads((out / "data" / "barrier_bands.north.json").read_text())
    pts, widths, iw = _lap(out)
    cfg = json.loads((out / "track.config.json").read_text())
    from scripts.geometry import race_lap
    view = race_lap.config_view(cfg, "north")
    island_race = iw
    for lid in ("north_cw", "north_acw"):
        bare = copy.deepcopy(b)
        bare["corridors"][lid].pop("nose_walls")
        r = nr.run(out, lid, planned=True, bands=bare, cfg=view, write=False, verbose=False,
                   line=(pts, widths, island_race))
        assert r["fail"] and r["forbidden_reached"], (lid, {k: r[k] for k in ("leak_m2", "door_clusters")})
        ok = nr.run(out, lid, planned=True, bands=b, cfg=view, write=False, verbose=False, line=(pts, widths, island_race))
        assert not ok["fail"] and not ok["forbidden_reached"], lid


def _mock_authored(pts, widths, b, lap):
    """the planned furniture laid the way tools/author_race_furniture_blend.py lays it (ring centres at the plan's xz,
    ends recorded with its rules) — no Blender: verify_race's C' / H / I / J then judge the plan itself"""
    m = rf.unique_count(pts)
    plans = rf.edge_plans(pts, widths, b, "road") + [p for lid in sorted(b["corridors"]) for p in rf.closure_plans(pts, widths, b, lid)]
    objs, centres, frames = [], {}, {}
    for p in plans:
        if p["kind"] == "edge":
            p["lap"] = lap
        name = rf.object_name(p)
        cs = [[round(x, 2), round(r["y_hint"], 2), round(z, 2)] for r in p["rings"] for (x, z) in (rf._strip_xz(r),)]
        centres[name] = cs
        frames[name] = [[round(r["tx"], 5), round(r["tz"], 5), round(r.get("ls", 1.0), 4)] for r in p["rings"]]
        objs.append({"name": name, "kind": p["kind"], "owner": p.get("token") if p["kind"] == "close" else None,
                     "layout": p.get("layout"), "side": p["side"], "run": list(p["run"]), "part": p["part"],
                     "wall": (p.get("wall") or "closure") if p["kind"] == "close" else None,
                     "collection": rf.closure_collection(p["token"]) if p["kind"] == "close" else rf.lap_collection(lap),
                     "caps": [p["cap_start"], p["cap_end"]], "end_kinds": [p["start_kind"], p["end_kind"]],
                     "rings": len(p["rings"]), "_plan": p})
    for o in objs:
        p = o.pop("_plan")
        ends = []
        for idx, cap in enumerate(o["caps"]):
            ring = p["rings"][0 if idx == 0 else -1]
            e = {"vertex": ring["k"], "h": round(ring["h"], 4), "ls": round(ring.get("ls", 1.0), 4)}
            if o["kind"] == "close" and cap:
                e.update(kind="pin", vertex=p["pins"][idx]["vertex"], y=p["pins"][idx]["y"], joins=p["pins"][idx]["joins"])
            elif cap:
                e.update(kind="free")
            else:
                e.update(kind="join")
            ends.append(e)
        o["ends"] = ends
    return {"objects": objs, "ring_centres": centres, "ring_frames": frames}


def test_verify_race_passes_the_planned_k_rails_and_refuses_one_short_of_the_far_strip():
    _r, _rep, out = _plan()
    b = json.loads((out / "data" / "barrier_bands.north.json").read_text())
    pts, widths, iw = _lap(out)
    auth = _mock_authored(pts, widths, b, "north")
    rep = vr.verify(auth, b, pts, iw, widths=widths, lap="north")
    mine = [f for f in rep["fails"] if f.startswith(("C'", "J:", "I:", "H:"))]
    assert not mine, mine[:6]
    rows = rep["counts"]["by_layout"]
    for lid in ("north_cw", "north_acw"):
        assert rows[lid]["nose_walls"] == 3 and rows[lid]["nose_objects"] == 3
        assert all(r["far_line_m"] <= vr.PIN_TOL_M and r["closure_face_m"] <= vr.PIN_TOL_M for r in rows[lid]["nose_pins"])
        assert sum(1 for p in rows[lid]["pins"] if "nose_line_m" in p) == 3
    bad = copy.deepcopy(auth)
    name = "1WALL_race_close_ncw_nose_307_0"
    cs = bad["ring_centres"][name]
    a, z = cs[-2], cs[-1]
    cs[-1] = [z[0] - (z[0] - a[0]) * 0.4, z[1], z[2] - (z[2] - a[2]) * 0.4]   # 0.4 m short of the far strip
    rep2 = vr.verify(bad, b, pts, iw, widths=widths, lap="north")
    assert any(name in f and "far curb-strip line" in f for f in rep2["fails"]), rep2["fails"][:6]
    assert any(f.startswith("J:") and name in f for f in rep2["fails"]), rep2["fails"][:6]
