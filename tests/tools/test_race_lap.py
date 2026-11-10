"""Ledger 0054 phase 2 groundwork: a race layout may name its own LAP (layouts[].lap -> race.laps.<lap>), and every
race tool counts along THAT line. Driven on tests/tools/lap_world.py — a synthetic world whose second lap runs partly
on the mainline (its west half) and partly on a connector (cross#0, straight up the middle):

  * the lap representation (scripts/geometry/race_lap.py): pieces taken verbatim, joins resampled, closed, a
    per-vertex source map, the lap's mouths (its own junctions skipped, the abandoned BRANCH at each junction probed
    on the branch), a piece walked backwards flips its side streets, the declaration validated;
  * tools/barrier_bands.py: one declaration per group — the mainline's byte-identical with or without the lap
    declared, the lap's own data/barrier_bands.<lap>.json (corridor, closures, kerbs, branch probes, PLANNED fill);
  * tools/race_furniture.py: the lap's common set named lap<lap> (race_lap reads it back), its closures per token;
  * tools/no_route.py: the lap's seal, planned and BUILT, and a gap across a branch caught;
  * tools/layout_dummies.py, scripts/ac/write_ai_line.py + tools/verify_ai_line.py, scripts/geometry/drive_test.py
    (the lane), tools/verify_race.py --lap, tools/check_race_kn5.py --lap, scripts/ac/track_folder.py + verify_kn5
    --inis (the lap's own common kn5 in its ini), scripts/geometry/median_zone.py, tools/verify_fold_fans.py's lap
    lane mapping.
Plain ``test_*`` for tests/run_tests.py.
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

from tests.tools import lap_world as lw  # noqa: E402
import barrier_bands as bb  # noqa: E402
import check_race_kn5 as ck  # noqa: E402
import layout_dummies as ld  # noqa: E402
import no_route as nr  # noqa: E402
import race_furniture as rf  # noqa: E402
import verify_race as vr  # noqa: E402
from scripts.geometry import race_lap  # noqa: E402

_W = {}


def _world():
    """(project, facts, mainline declaration, lap declaration) — built once per module"""
    if "d" not in _W:
        d, facts = lw.build()
        _W.update(d=d, facts=facts, main=bb.build(d), lap=bb.build(d, lap=lw.LAP))
    return _W["d"], _W["facts"], _W["main"], _W["lap"]


def _cfg(d):
    return json.loads((d / "track.config.json").read_text(encoding="utf-8"))


def _strip_timing(o):
    if isinstance(o, dict):
        return {k: _strip_timing(v) for k, v in o.items() if k not in ("seconds", "_path", "_ctx")}
    if isinstance(o, list):
        return [_strip_timing(v) for v in o]
    return o


# --------------------------------------------------------------------------------- the lap representation
def test_the_lap_is_stitched_verbatim_bridged_closed_and_mapped():
    d, f, _m, _l = _world()
    rec = json.loads((d / "data" / "lap.w.json").read_text(encoding="utf-8"))
    cl = json.loads((d / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    conn = json.loads((d / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"][0]
    P, src = rec["points_xyz_m"], rec["source_by_vertex"]
    m = len(P) - 1
    assert P[-1] == P[0] and src[-1] == src[0] and m == f["lap_n"]
    # every non-join vertex IS its source vertex (verbatim), in the piece's walk order
    for k in range(m):
        if src[k][0] == "MAINLINE":
            assert P[k] == [round(c, 4) for c in cl["points_xyz_m"][src[k][1]]]
        elif src[k][0] == "cross#0":
            assert P[k] == [round(c, 4) for c in conn["points_xyz_m"][src[k][1]]]
    assert src[0] == ["MAINLINE", f["top"]] and [sv for sv in src[:m] if sv[0] == "MAINLINE"][-1] == ["MAINLINE", f["bot"]]
    assert [p["line"] for p in rec["pieces"]] == ["MAINLINE", "cross#0"]
    # the two junction gaps (the connector is trimmed at the mainline curb) are bridged on the straight join, no
    # step longer than the pieces' own spacing
    assert [(j["from"], j["to"], j["points"]) for j in rec["joins"]] == [
        (["MAINLINE", f["bot"]], ["cross#0", 0], 3), (["cross#0", len(conn["points_xyz_m"]) - 1], ["MAINLINE", f["top"]], 3)]
    steps = [math.dist(P[k][::2], P[k + 1][::2]) for k in range(m)]
    joined = [k for k in range(m) if src[k][0] == "join" or src[(k + 1) % m][0] == "join"]
    assert len(joined) == 8 and all(steps[k] <= rec["spacing_m"] + 1e-6 for k in joined)
    assert max(steps) < 3.05 and min(steps) > 2.0
    assert abs(rec["lap_m"] - sum(steps)) < 0.2 and 1630 < rec["lap_m"] < 1660
    assert rec["island_w_by_vertex"] == [0.0] * (m + 1) and rec["widths_m"] == [lw.W] * (m + 1)


def test_the_laps_mouths_are_its_branches_and_never_its_own_junctions():
    d, f, _m, _l = _world()
    rec = json.loads((d / "data" / "lap.w.json").read_text(encoding="utf-8"))
    # the connector's two mouths onto the mainline ARE the lap's path: skipped, with the reason
    assert sorted((s["lap_vertex"], s["why"]) for s in rec["mouths_skipped"]) == [
        (0, "the lap's own junction"), (f["bot"] - f["top"], "the lap's own junction")]
    # the abandoned east halves of the top and bottom edges are its branches: probed ON the branch, 10 m past the curb
    br = {(r["connector"], r["host_vertex"], r["side"], tuple(r["probe_xz"])) for r in rec["mouths"]}
    assert br == {(f"MAINLINE before v{f['top']}", 0, -1, (20.0, lw.ZH)),
                  (f"MAINLINE beyond v{f['bot']}", f["bot"] - f["top"], -1, (20.0, -lw.ZH))}, br
    assert all(r["kind"] == "branch" for r in rec["mouths"])


def test_a_piece_walked_backwards_flips_its_side_streets_and_the_declaration_is_validated():
    d, f, _m, _l = _world()
    cfg = _cfg(d)
    conn_n = len(lw.connector_xz())
    # the same west half walked the other way round, with a spur on the LEFT of cross#0 (its increasing direction)
    cfg["race"]["laps"]["v"] = {"pieces": [{"line": "cross#0", "from": conn_n - 1, "to": 0},
                                           {"line": "MAINLINE", "from": f["bot"], "to": f["top"], "reverse": True}]}
    spur = {"connector": "spur", "host": "cross#0", "host_vertex": 30, "side": 1, "connector_width_m": 8.0,
            "piece": "spur#0", "end": "start"}
    rec = race_lap.stitch(d, cfg, "v", mouths=[spur])
    row = next(r for r in rec["mouths"] if r["connector"] == "spur")
    assert row["side"] == -1 and rec["source_by_vertex"][row["host_vertex"]] == ["cross#0", 30]
    fwd = race_lap.stitch(d, _cfg(d), lw.LAP, mouths=[spur])
    assert next(r for r in fwd["mouths"] if r["connector"] == "spur")["side"] == 1
    # the declaration's own shape
    bad = copy.deepcopy(_cfg(d))
    bad["layouts"][0]["lap"] = lw.LAP                                 # the street layout
    bad["layouts"][-1]["lap"] = "nope"
    bad["race"]["laps"]["Bad_Id"] = {"pieces": []}
    probs = " | ".join(race_lap.validate(bad))
    for frag in ("layout street: lap 'w' on a layout that is neither a race layout with race_furniture nor a bare race",
                 "lap 'nope' is not declared in race.laps",
                 "race.laps: id 'Bad_Id' must be", "race.laps.Bad_Id: needs pieces"):
        assert frag in probs, (frag, probs)
    try:
        race_lap.stitch(d, dict(cfg, race=dict(cfg["race"], laps={"x": {"pieces": [
            {"line": "cross#0", "from": 0, "to": 5, "reverse": True}]}})), "x")
        raise AssertionError("an open piece whose reverse contradicts from / to must be refused")
    except SystemExit as e:
        assert "contradicts" in str(e)


def test_groups_and_the_config_view():
    d, _f, _m, _l = _world()
    cfg = _cfg(d)
    assert race_lap.groups(cfg) == [None, "w"] and race_lap.lap_ids(cfg) == ["w"]
    main_view = race_lap.config_view(cfg, None)
    assert [lo["id"] for lo in main_view["layouts"]] == ["street", "race_cw"]
    lap_view = race_lap.config_view(cfg, "w")
    assert [lo["id"] for lo in lap_view["layouts"]] == ["lap_f", "lap_r"]
    assert lap_view["race"]["corridor"] == cfg["race"]["laps"]["w"]["corridor"] and "laps" not in lap_view["race"]
    assert lap_view["race"]["kerbs"]["trims"] == cfg["race"]["laps"]["w"]["kerbs"]["trims"]
    assert lap_view["race"]["kerbs"]["min_turn_deg"] == 45                  # the rest of race.kerbs is inherited
    # no lap declared anywhere: the config comes back as it is (every mainline consumer reads exactly what it did)
    plain = copy.deepcopy(cfg)
    plain["layouts"] = plain["layouts"][:2]
    plain["race"].pop("laps")
    assert race_lap.config_view(plain, None) is plain and race_lap.groups(plain) == [None]
    ln = race_lap.line_for(d, cfg, "lap_f")
    assert ln["lap"] == "w" and ln["bands_path"].name == "barrier_bands.w.json" and len(ln["pts"]) == len(ln["widths"])
    assert race_lap.line_for(d, cfg, "race_cw")["bands_path"].name == "barrier_bands.json"


# --------------------------------------------------------------------------------- barrier_bands
def test_the_mainline_declaration_is_byte_identical_with_or_without_the_lap():
    d, _f, main, _l = _world()
    d0, _f0 = lw.build(with_lap=False)
    plain = bb.build(d0)
    assert plain["fails"] == [] and main["fails"] == []
    a = json.loads((d / "data" / "barrier_bands.json").read_text(encoding="utf-8"))
    b = json.loads((d0 / "data" / "barrier_bands.json").read_text(encoding="utf-8"))
    assert _strip_timing(a) == _strip_timing(b)
    assert "lap" not in a and sorted(a["corridors"]) == ["race_cw"]
    assert not (d0 / "data" / "lap.w.json").exists() and not list((d0 / "data").glob("barrier_bands.*.json"))


def test_the_lap_declares_its_own_corridor_closures_kerbs_probes_and_planned_fill():
    d, f, _m, lap = _world()
    assert lap["fails"] == [], lap["fails"]
    j = json.loads((d / "data" / "barrier_bands.w.json").read_text(encoding="utf-8"))
    m = f["lap_n"]
    assert j["n"] == m + 1 and j["lap"]["id"] == "w" and j["lap"]["line"] == "data/lap.w.json"
    assert sorted(j["corridors"]) == ["lap_f", "lap_r"]
    assert j["zones"]["whole"] == f["lap_whole"] and j["zones"]["closure_runs"] == f["lap_runs"]
    assert f["lap_whole"][0] > f["lap_whole"][1]                       # the whole street wraps the lap's seam
    for lid, side in (("lap_f", "L"), ("lap_r", "R")):
        c = j["corridors"][lid]
        assert c["closure_side"] == side and len(c["zone_by_vertex"]) == m + 1
        # the connector is the whole street, the closure stands on the mainline part of the lap only
        k0, k1 = f["lap_conn"]
        assert all(c["zone_by_vertex"][k] == "whole" for k in range(k0, k1 + 1))
        assert all(c["closure_y_by_vertex"][k] is None for k in range(k0, k1 + 1))
        assert sorted((r["i"], r["j"]) for r in c["runs"]) == [tuple(r) for r in f["lap_runs"]]
        lane = c["lane_by_vertex"]
        mid_run = (f["lap_runs"][1][0] + f["lap_runs"][1][1]) // 2
        # mid-run the closure stands ~Alvarado-wide (11.36 m; on a 360 m run the solver's smoothness term keeps it
        # 0.2 m wider), never under the floor
        assert 10.86 <= lane[mid_run][1] - lane[mid_run][0] < 11.7
        assert abs((lane[f["lap_mid"]][1] - lane[f["lap_mid"]][0]) - (lw.W - 2 * 0.82)) < 1e-3   # full on cross#0
        probes = c["no_route"]["forbidden_probes"]
        br = [p for p in probes if p.get("xz")]
        assert sorted(tuple(p["xz"]) for p in br) == [(20.0, -lw.ZH), (20.0, lw.ZH)]
        assert all(p["why"].startswith("branch MAINLINE") for p in br)
        pl = c["no_route"]["planned"]
        assert pl["fail"] is False and pl["leak_m2"] == 0 and pl["forbidden_reached"] == [] and pl["blocked"] == []
        assert (d / "data" / f"no_route.{lid}.planned.json").exists()
    assert [(cm["kind"], cm["side"]) for cm in j["closed_mouths"]] == [("branch", "R"), ("branch", "R")]
    # the stitched junctions' inside kerbs are DECLARED dropped, every other kerb declared
    on_conn = [a for a in f["lap_corners"] if all(not (b["i"] <= a <= b["j"]) for b in f["lap_boxes"])]
    assert len(on_conn) == 2
    assert sorted((k["apex"], k["kind"]) for k in j["kerbs_dropped"]) == sorted((a, "inside") for a in on_conn)
    assert len(j["kerbs"]) + len(j["kerbs_dropped"]) == 2 * len(f["lap_corners"])
    assert len(j["edge_corners"]) == 2 and all(c["side"] == "L" for c in j["edge_corners"])


def test_the_cli_writes_one_declaration_per_group():
    d, f = lw.build()
    for p in (d / "data").glob("barrier_bands*.json"):
        p.unlink()
    assert bb.main([str(d)]) == 0
    assert (d / "data" / "barrier_bands.json").exists() and (d / "data" / "barrier_bands.w.json").exists()
    assert (d / "data" / "lap.w.json").exists()


# --------------------------------------------------------------------------------- the furniture
def test_the_laps_common_set_is_named_for_its_lap_and_its_closures_for_their_tokens():
    d, _f, _m, _l = _world()
    _p, _w, _i, plans, corners = rf.plan_all(d, rf.load_bands(d, "w"), lap="w")
    names = [rf.object_name(p) for p in plans]
    edges = [n for n, p in zip(names, plans) if p["kind"] == "edge"]
    kerbs = [n for n, p in zip(names, plans) if p["kind"] == "kerb"]
    closes = [n for n, p in zip(names, plans) if p["kind"] == "close"]
    assert edges and all(n.startswith("1WALL_race_edge_lapw_") for n in edges)
    assert len(kerbs) == 6 and all(n.startswith("1KERB_race_lapw_") for n in kerbs)
    assert {rf.race_owner(n) for n in closes} == {"lf", "lr"}
    for n in edges + kerbs:
        assert rf.race_lap(n) == "w" and rf.race_role(n) in ("edge", "kerb") and rf.is_race_name(n)
    assert all(rf.race_lap(n) is None for n in closes)
    _p, _w, _i, mplans, _c = rf.plan_all(d, rf.load_bands(d))
    mnames = [rf.object_name(p) for p in mplans]
    assert all(rf.race_lap(n) is None for n in mnames) and not set(mnames) & set(names)
    assert rf.lap_collection("w") == "RACE_LAP_W" and rf.lap_collection(None) == rf.COMMON_COLLECTION
    # check_race_kn5's own reading of the names (the content guard after each export)
    assert ck.race_lap("1WALL_RACE_EDGE_LAPW_L_street0_6_0") == "w" and ck.race_lap("1WALL_RACE_EDGE_L_x_1_0") is None


def test_check_race_kn5_routes_the_lap_common_set():
    tex = {"1WALL_RACE": ("a.png", None), "1KERB_RACE": ("b.png", None)}
    textures = [{"name": "a.png", "bytes": 10}, {"name": "b.png", "bytes": 10}]

    def parsed(names):
        return {"meshes": [{"name": n, "verts": 10, "tris": 8} for n in names], "textures": textures, "nodes": []}
    lap_names = ["1WALL_race_edge_lapw_L_s_0_0", "1WALL_race_edge_lapw_R_s_0_0", "1KERB_race_lapw_66_out"]
    main_names = ["1WALL_race_edge_L_s_0_0", "1KERB_race_24_out"]
    ok = ck.check(parsed(lap_names), {"a.png", "b.png"}, role="common", lap="w", expect_kerbs=1, textures=tex)
    assert ok["ok"], ok["fails"]
    r = ck.check(parsed(lap_names), {"a.png", "b.png"}, role="common", expect_kerbs=1, textures=tex)
    assert not r["ok"] and any("of a LAP" in x for x in r["fails"])
    r = ck.check(parsed(main_names), {"a.png", "b.png"}, role="common", lap="w", expect_kerbs=1, textures=tex)
    assert not r["ok"] and any("another lap or the mainline" in x for x in r["fails"])
    assert ck.check(parsed(main_names), {"a.png", "b.png"}, role="common", expect_kerbs=1, textures=tex)["ok"]


def _authored(d, lap):
    """race_authored.<lap>.json as the author writes it, from race_furniture's own plans of that group (flat deck)"""
    bands = rf.load_bands(d, lap)
    _p, _w, _i, plans, corners = rf.plan_all(d, bands, lap=lap)
    objects, centres, frames = [], {}, {}
    tokens = {lid: c["token"] for lid, c in rf.corridors(bands).items()}
    for p in plans:
        name = rf.object_name(p)
        if p["kind"] == "kerb":
            sgn = 1.0 if p["side"] == "L" else -1.0
            centres[name] = [[round(x, 2), 0.1, round(z, 2)] for (x, z) in (rf.kerb_mid_xz(s, sgn) for s in p["stations"])]
            frames[name] = [[round(s["tx"], 5), round(s["tz"], 5), round(s.get("ls", 1.0), 4)] for s in p["stations"]]
            objects.append({"name": name, "kind": "kerb", "owner": None, "layout": None,
                            "collection": rf.lap_collection(lap), "side": p["side"], "sub": p["sub"], "apex": p["apex"],
                            "run": [p["stations"][0]["k"], p["stations"][-1]["k"]], "stations": len(p["stations"]),
                            "clip": p.get("clip"), "seated": {"hit": len(p["stations"]), "near": 0, "interpolated": 0},
                            "seat_gap_max_m": 0.0, "positions": 4 * len(p["stations"]), "faces": 3 * len(p["stations"]),
                            "loops": 12 * len(p["stations"]), "under_road": {"stations": 0, "max_m": 0.0, "vertices": []}})
            continue
        tok = p.get("token") if p["kind"] == "close" else None
        centres[name] = [[round(x, 2), 0.1, round(z, 2)] for (x, z) in (rf._strip_xz(r) for r in p["rings"])]
        frames[name] = [[round(r["tx"], 5), round(r["tz"], 5), round(r.get("ls", 1.0), 4)] for r in p["rings"]]
        ends = []
        for idx, cap in enumerate((p["cap_start"], p["cap_end"])):
            ring = p["rings"][0 if idx == 0 else -1]
            e = {"vertex": ring["k"], "h": ring["h"], "ls": ring.get("ls", 1.0)}
            if p["kind"] == "close" and cap:
                e.update(kind="pin", joins=p["pins"][idx]["joins"], gap_m=0.0)
            else:
                e.update(kind="join" if not cap else "free", joins=None, gap_m=0.0)
            ends.append(e)
        objects.append({"name": name, "kind": p["kind"], "owner": tok, "layout": p.get("layout"),
                        "collection": rf.closure_collection(tok) if tok else rf.lap_collection(lap), "side": p["side"],
                        "street": p["street"], "run": list(p["run"]), "part": p["part"], "rings": len(p["rings"]),
                        "seated": {"hit": len(p["rings"]), "near": 0, "interpolated": 0}, "seat_gap_max_m": 0.0,
                        "caps": [p["cap_start"], p["cap_end"]], "end_kinds": [p["start_kind"], p["end_kind"]],
                        "ends": ends, "fold_skipped_run": 0, "positions": 10 * len(p["rings"]),
                        "faces": 10 * len(p["rings"]), "loops": 40 * len(p["rings"]), "fold_corners": p.get("fold_corners", [])})
    rings = sum(len(p["rings"]) for p in plans if p["kind"] != "kerb")
    kst = sum(len(p["stations"]) for p in plans if p["kind"] == "kerb")
    return {"standin_bands": False, "edge_mode": "road", "barrier_height_m": 1.2,
            "race_prefixes": ["1WALL_RACE", "1KERB_RACE"], "max_rings_per_object": 800, "tokens": tokens,
            "totals": {"objects": len(objects), "rings": rings, "kerb_stations": kst, "seated_interpolated": 0,
                       "deck_vs_data_max_m": 0.0, "other_deck_above_max_m": 0.0, "other_deck_threshold_m": 0.05,
                       "other_deck_above_rings": 0},
            "corners": [{k: v for k, v in c.items() if k != "kerbs"} | {"kerbs": [
                {"side": kb["side"], "kind": kb["kind"], "i": kb["i"], "j": kb["j"], "declared": bool(kb.get("declared"))}
                for kb in c["kerbs"]]} for c in corners],
            "kerbs_declared_unmatched": [], "failed_runs": [], "spawn_clearance": {},
            "bridge_seating": {"hit": 0, "near": 0, "interpolated": 0, "by_span": []}, "other_deck_above": [],
            "objects": objects, "ring_centres": centres, "ring_frames": frames}


def test_verify_race_judges_the_lap_group_on_its_own_line_and_names():
    d, _f, _m, _l = _world()
    rec = race_lap.load(d, "w")
    pts = [tuple(p) for p in rec["points_xyz_m"]]
    bands = rf.load_bands(d, "w")
    a = _authored(d, "w")
    r = vr.verify(a, bands, pts, rec["island_w_by_vertex"], widths=rec["widths_m"], lap="w")
    assert r["ok"], r["fails"]
    assert sorted(r["counts"]["by_layout"]) == ["lap_f", "lap_r"]
    # the same set judged as the mainline's: every common name carries the wrong lap and the wrong collection
    r2 = vr.verify(a, bands, pts, rec["island_w_by_vertex"], widths=rec["widths_m"])
    assert not r2["ok"] and any(f.startswith("K:") and "carries lap 'w'" in f for f in r2["fails"])
    # a lap strip that lost its token would ship in the mainline's common kn5
    b = copy.deepcopy(a)
    o = next(o for o in b["objects"] if o["kind"] == "edge")
    new = o["name"].replace("_lapw_", "_")
    b["ring_centres"][new] = b["ring_centres"].pop(o["name"])
    b["ring_frames"][new] = b["ring_frames"].pop(o["name"])
    o["name"] = new
    r3 = vr.verify(b, bands, pts, rec["island_w_by_vertex"], widths=rec["widths_m"], lap="w")
    assert any(f.startswith(f"K: {new}") and "carries lap None" in f for f in r3["fails"]), r3["fails"]
    # the CLI: --lap reads race_authored.w.json + barrier_bands.w.json + lap.w.json, writes race_verify.w.json
    (d / "data" / "race_authored.w.json").write_text(json.dumps(a), encoding="utf-8")
    ld.write_all(d)                                         # F: the lap layouts' spawns, judged on the lap's lane
    assert vr.main([str(d), "--lap", "w"]) == 0 and (d / "data" / "race_verify.w.json").exists()
    rv = json.loads((d / "data" / "race_verify.w.json").read_text(encoding="utf-8"))
    assert sorted(rv["counts"]["spawn_min_clear_m"]) == ["lap_f", "lap_r"]   # never race_cw (the mainline's group)


# --------------------------------------------------------------------------------- no_route: the seal
def test_no_route_seals_the_lap_planned_and_a_gap_across_a_branch_is_caught():
    d, f, _m, _l = _world()
    for lid in ("lap_f", "lap_r"):
        r = nr.run(d, lid, planned=True, write=False, verbose=False)
        assert r["fail"] is False and r["leak_cells"] == 0 and r["blocked"] == [], (lid, r["fails"])
        assert r["forbidden_probes"] >= 2
    # knock both curb strips out across the bottom junction: the abandoned east half is a door
    bands = json.loads((d / "data" / "barrier_bands.w.json").read_text(encoding="utf-8"))
    kb = f["bot"] - f["top"]
    for k in range(kb - 8, kb + 9):
        bands["edge_strip_by_vertex"][k] = 0
    r = nr.run(d, "lap_f", planned=True, bands=bands, write=False, verbose=False)
    assert r["fail"] is True and r["leak_cells"] > 0
    assert any("branch MAINLINE beyond" in x["why"] for x in r["forbidden_reached"]), r["forbidden_reached"]


def test_no_route_built_reads_the_laps_gate_obj_and_finds_a_missing_strip():
    d, f, _m, _l = _world()
    ld.write_all(d)
    _p, _w, _i, plans, _c = rf.plan_all(d, rf.load_bands(d, "w"), lap="w")
    mine = [p for p in plans if p["kind"] != "close" or p.get("layout") == "lap_f"]
    lw.gate_obj(d, "lap_f", mine)
    r = nr.run(d, "lap_f", write=False, verbose=False)
    assert r["fail"] is False and r["obj"] == "track.lap_f.obj" and r["leak_cells"] == 0, r["fails"]
    assert r["spawns_checked"] > 0 and r["forbidden_reached"] == []
    # the right-hand curb strip across the bottom junction (the one standing across the branch) not built
    kb = f["bot"] - f["top"]
    gone = {rf.object_name(p) for p in mine if p["kind"] == "edge" and p["side"] == "R"
            and any(abs(rg["k"] - kb) <= 2 for rg in p["rings"])}
    assert gone
    lw.gate_obj(d, "lap_f", mine, drop=gone)
    r = nr.run(d, "lap_f", write=False, verbose=False)
    assert r["fail"] is True and r["leak_cells"] > 0, r["fails"]
    lw.gate_obj(d, "lap_f", mine)                                       # leave the world built for the next tests


# --------------------------------------------------------------------------------- spawns, AI, drive_test
def test_layout_dummies_place_each_lap_layout_on_its_lap():
    d, f, _m, _l = _world()
    assert ld.write_all(d) == 0
    rec = race_lap.load(d, "w")
    for lid, east in (("lap_f", +1.0), ("lap_r", -1.0)):
        dm = json.loads((d / "data" / f"dummies_{lid}.json").read_text(encoding="utf-8"))
        assert dm["_lap"] == "w" and dm["_layout"] == lid
        x, _y, z = dm["AC_START_0"]
        k = dm["_vertex"]["AC_START_0"]
        assert rec["source_by_vertex"][k][0] == "cross#0"                 # on the connector, a lap vertex
        # heading north (forward) the right of travel is east; south (reverse) it is west
        assert abs(x - east * 3.25) < 0.05 and -lw.ZH < z < lw.ZH
        assert abs(dm["_yaw_deg"]["AC_START_0"] - (180.0 if lid == "lap_f" else 0.0)) % 360 < 0.5
        assert dm["_line"]["vertex"] == _cfg(d)["layouts"][2 if lid == "lap_f" else 3]["start"]["line_vertex"]
    assert "_lap" not in json.loads((d / "data" / "dummies_race_cw.json").read_text(encoding="utf-8"))


def _ai_world():
    d, f, _m, _l = _world()
    if not (d / "ai" / "lap_f" / "fast_lane.ai").exists():
        cfg = _cfg(d)
        cfg["ai"] = {"layouts": ["lap_f", "lap_r"], "payload": "kunos", "wall_clear_m": 2.5, "fair": True,
                     "surface": "gate_obj"}
        (d / "track.config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
        ld.write_all(d)
        _p, _w, _i, plans, _c = rf.plan_all(d, rf.load_bands(d, "w"), lap="w")
        from scripts.ac import write_ai_line as wal
        for lid in ("lap_f", "lap_r"):
            lw.gate_obj(d, lid, [p for p in plans if p["kind"] != "close" or p.get("layout") == lid])
            wal.main([str(d), "--layout", lid])
    return d, f


def test_the_ai_line_is_drafted_on_the_lap_inside_its_corridor_and_verified_on_the_built_walls():
    d, f = _ai_world()
    import verify_ai_line as va
    for lid in ("lap_f", "lap_r"):
        rep = json.loads((d / "ai" / lid / "ai_draft.json").read_text(encoding="utf-8"))
        assert rep["frame"].startswith("engine frame (the lap line data/lap.w.json")
        assert rep["corridor"]["declaration"].startswith(f"barrier_bands.w.json corridors.{lid}")
        assert rep["corridor"]["check"]["outside"] == 0 and rep["direction"] == ("forward" if lid == "lap_f" else "reverse")
        assert abs(rep["lap_m"] - race_lap.load(d, "w")["lap_m"]) < 120.0      # the LAP's length, not the mainline's
        assert va.main([str(d), "--layout", lid]) == 0, json.loads(
            (d / "data" / f"ai_verify.{lid}.json").read_text(encoding="utf-8"))["fail"]


def test_drive_test_drives_the_lap_lane_and_a_missing_closure_is_barrier_missing():
    d, f = _ai_world()
    from scripts.geometry.drive_test import run as drive_run
    r = drive_run(d, "lap_f")
    assert r["lane"] == "barrier_bands.w.json corridors.lap_f" and r["obj"] == "track.lap_f.obj"
    assert r["barrier_missing"] == 0, r["barrier_missing_runs"]
    assert r["obstruction_stations"] == 0, r.get("obstruction_by_mesh")
    assert abs(r["lap_m"] - race_lap.load(d, "w")["lap_m"]) < 1.0
    _p, _w, _i, plans, _c = rf.plan_all(d, rf.load_bands(d, "w"), lap="w")
    mine = [p for p in plans if p["kind"] != "close" or p.get("layout") == "lap_f"]
    lw.gate_obj(d, "lap_f", mine, drop={rf.object_name(p) for p in mine if p["kind"] == "close"})
    r2 = drive_run(d, "lap_f")
    assert r2["barrier_missing"] > 0 and {k for _a, _b, k in r2["barrier_missing_runs"]} == {"closure"}
    lw.gate_obj(d, "lap_f", mine)


def test_median_zone_and_fold_fans_read_the_lap():
    d, f, _m, _l = _world()
    from scripts.geometry.median_zone import MedianZone
    z = MedianZone.load(d, layout="lap_f")
    assert z is not None and z.has_corridor and len(z.pts) == f["lap_n"] + 1 and z.layout == "lap_f"
    zm = MedianZone.load(d, layout="race_cw")
    assert len(zm.pts) == f["mainline_n"] + 1
    import verify_fold_fans as ff
    lane_of, covered = ff._lap_lane(d / "data", "w", "lap_f", f["mainline_n"])
    assert covered == set(range(f["top"], f["bot"] + 1))
    lane = json.loads((d / "data" / "barrier_bands.w.json").read_text(encoding="utf-8"))["corridors"]["lap_f"]["lane_by_vertex"]
    W = [lw.W] * (f["mainline_n"] + 1)
    assert lane_of(f["top"] + 40, W) == (float(lane[40][0]), float(lane[40][1]))
    assert lane_of(f["bot"] + 5, W) == (-(lw.W / 2 - 0.5), lw.W / 2 - 0.5)   # a row off the lap: never surveyed


# --------------------------------------------------------------------------------- the track folder
def test_track_folder_gives_each_lap_layout_its_laps_common_kn5_and_verify_kn5_agrees():
    d, f, _m, _l = _world()
    ld.write_all(d)
    cfg = _cfg(d)
    cfg.update({"ui_series": "", "version": "0.1", "default_width_m": 20.0, "origin": "centroid",
                "location": {"lat": 32.78, "lon": -117.04, "timezone": "America/Los_Angeles", "city": "San Diego",
                             "country": "United States"}, "source": {"type": "osm"}, "surfaces": {"road": "1ROAD"},
                "lighting": {}, "road_markings": {"center_yellow": False}})   # ledger 0063: no t_street.kn5
    (d / "track.config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    (d / "data" / "centerline.geojson").write_text(json.dumps({"features": [{"geometry": {
        "type": "LineString", "coordinates": [[-117.04, 32.78], [-117.03, 32.78]]}, "properties": {"length_m": 2411.0}}]}))
    (d / "build").mkdir(exist_ok=True)
    names = ["t.kn5", "t_race.kn5", "t_race_w.kn5", "t_closure_race_cw.kn5", "t_closure_lap_f.kn5", "t_closure_lap_r.kn5"]
    names += [f"t__{lo['id']}.kn5" for lo in cfg["layouts"]] + ["t_race_old.kn5"]
    for n in names:
        (d / "build" / n).write_bytes(b"sc6969" + n.encode())
    (d / "build" / "t").mkdir(exist_ok=True)
    (d / "build" / "t" / "t_race_old.kn5").write_bytes(b"stale")          # a retired lap's common kn5 in the folder
    from scripts.ac import track_folder as tf
    from scripts.ac import verify_kn5 as vk
    out = tf.generate(d)
    models = out["models"]
    assert models["lap_f"] == ["t.kn5", "t_race_w.kn5", "t_closure_lap_f.kn5", "t__lap_f.kn5"]
    assert models["lap_r"] == ["t.kn5", "t_race_w.kn5", "t_closure_lap_r.kn5", "t__lap_r.kn5"]
    assert models["race_cw"] == ["t.kn5", "t_race.kn5", "t_closure_race_cw.kn5", "t__race_cw.kn5"]
    assert models["street"] == ["t.kn5", "t__street.kn5"]
    folder = d / "build" / "t"
    assert (folder / "t_race_w.kn5").exists() and not (folder / "t_race_old.kn5").exists()
    ui = json.loads((folder / "ui" / "lap_f" / "ui_track.json").read_text(encoding="utf-8"))
    assert ui["length"] == str(round(race_lap.load(d, "w")["lap_m"]))       # the LAP's length
    assert json.loads((folder / "ui" / "race_cw" / "ui_track.json").read_text(encoding="utf-8"))["length"] == "2411"
    import shutil
    shutil.copyfile(d / "build" / "t.kn5", folder / "t.kn5")
    assert vk.verify_inis(d) == []
    # an ini that loads the MAINLINE's common set on a lap layout is caught
    ini = folder / "models_lap_f.ini"
    ini.write_text(ini.read_text(encoding="utf-8").replace("t_race_w.kn5", "t_race.kn5"), encoding="utf-8")
    assert any("models_lap_f.ini" in x for x in vk.verify_inis(d))
    assert vk.race_kn5_name("t", {"lap": "w"}) == "t_race_w.kn5" and vk.race_kn5_name("t", {}) == "t_race.kn5"


def test_a_bare_race_layout_may_drive_a_lap_and_a_street_layout_still_may_not():
    """ledger 0085 (Pikes Peak's road course and infield): kind "race" with no race_furniture names a lap; a street
    layout (any other kind, no furniture) is refused as before"""
    cfg = {"layouts": [{"id": "rc", "kind": "race", "race_furniture": False, "lap": "rc"},
                       {"id": "free", "kind": "street", "race_furniture": False, "lap": "rc"}],
           "race": {"laps": {"rc": {"pieces": [{"line": "MAINLINE", "from": 0, "to": 3}]}}}}
    probs = race_lap.validate(cfg)
    assert not any(p.startswith("layout rc:") for p in probs), probs
    assert any(p.startswith("layout free:") and "neither a race layout" in p for p in probs), probs
