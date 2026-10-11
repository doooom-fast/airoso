"""tools/verify_race.py — the authored race furniture vs its declaration (ledger 0047).

A synthetic ring loop (200 vertices, R 100 m, 20 m wide) with one median island, one declared
centre run ending on the island nose, kerb-line strips on both sides gapped at one declared span,
one outside kerb and one race layout's spawn clearance. The authored file is synthesised from the
same declaration (ring centres = the vertices / the lip offsets), then mutated one defect at a
time: each mutation must fail exactly where the gate says it does.
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import verify_race as vr  # noqa: E402

N = 200
R = 100.0
W = 20.0
ISLAND = range(50, 61)          # island_w > 0 here; nose vertex 61 is the chain's end
CENTRE_RUN = (61, 100)
GAP = range(120, 131)           # edge strips absent here (a declared bridge span)
KERB = (150, "outside")


def _pts():
    pts = []
    for k in range(N):
        a = 2 * math.pi * k / N
        pts.append((R * math.cos(a), 5.0, R * math.sin(a)))
    pts.append(pts[0])
    return pts


def _bands():
    es = [0.0 if k in GAP else 0.82 for k in range(N + 1)]
    cw = [0.67 if CENTRE_RUN[0] <= k <= CENTRE_RUN[1] else 0.0 for k in range(N + 1)]
    return {
        "params": {"edge_mode": "road", "barrier_height_m": 1.2},
        "centre_w_by_vertex": cw, "edge_strip_by_vertex": es, "edge_inset_by_vertex": es,
        "runs": [{"kind": "centre", "i": CENTRE_RUN[0], "j": CENTRE_RUN[1]}],
        "streets": [{"street": "Alvarado Road", "vertex_from": 0, "vertex_to": 19}],
        "corners": [{"apex": 150, "PC": 145, "PT": 155, "D_deg": -60.0}],
        "kerbs": [{"apex": 150, "side": "L", "kind": "outside", "i": 140, "j": 160}],
        "summary": {"nose_vertices": [61]},
    }


def _lip(pts, k, side):
    """ring centre on the kerb-line strip: lateral (w/2 - 0.485) left (+) or right (-) of travel"""
    m = N
    a, b = pts[(k - 1) % m], pts[(k + 1) % m]
    tx, tz = b[0] - a[0], b[2] - a[2]
    L = math.hypot(tx, tz) or 1.0
    nx, nz = -tz / L, tx / L               # left normal (-tz, tx)
    s = 1.0 if side == "L" else -1.0
    off = W / 2 - 0.485
    p = pts[k]
    return [round(p[0] + s * off * nx, 3), p[1], round(p[2] + s * off * nz, 3)]


def _edge_obj(pts, side, ks, ends, part=0, fold=0):
    name = f"1WALL_race_edge_{side}_t_{ks[0]}_{part}"
    return ({"name": name, "kind": "edge", "side": side, "run": [ks[0], ks[-1]], "part": part, "rings": len(ks),
             "seated": {"hit": len(ks), "near": 0, "interpolated": 0}, "seat_gap_max_m": 0.0, "ends": ends,
             "caps": [ends[0] == "free", ends[1] == "free"], "fold_skipped_run": fold,
             "positions": 10 * len(ks), "faces": 9 * len(ks), "loops": 36 * len(ks)},
            [_lip(pts, k, side) for k in ks])


def _authored(pts):
    objs, centres = [], {}
    ks = list(range(CENTRE_RUN[0], CENTRE_RUN[1] + 1))
    chain = {"name": "1WALL_race_kbar_t_61_0", "kind": "chain", "side": "C", "street": "t", "run": list(CENTRE_RUN),
             "part": 0, "rings": len(ks), "seated": {"hit": len(ks), "near": 0, "interpolated": 0},
             "seat_gap_max_m": 0.0, "ends": ["nose", "free"], "caps": [True, True], "fold_skipped_run": 0,
             "positions": 10 * len(ks), "faces": 9 * len(ks), "loops": 36 * len(ks)}
    objs.append(chain)
    centres[chain["name"]] = [list(pts[k]) for k in ks]
    for side in ("L", "R"):
        # two objects per side: B wraps the seam (131..199 + 0) and A (0..119) starts on B's last ring
        b_ks = list(range(131, 200)) + [0]
        a_ks = list(range(0, 120))
        ob, cb = _edge_obj(pts, side, b_ks, ["free", "join"])
        oa, ca = _edge_obj(pts, side, a_ks, ["join", "free"])
        objs += [ob, oa]
        centres[ob["name"]] = cb
        centres[oa["name"]] = ca
    kerb = {"name": "1KERB_race_150_out", "kind": "kerb", "side": "L", "sub": "out", "apex": 150, "run": [140, 160],
            "stations": 60, "length_m": 20.0, "fold_skipped": 0, "seated": {"hit": 60, "near": 0, "interpolated": 0},
            "seat_gap_max_m": 0.0, "positions": 240, "faces": 180, "loops": 720}
    objs.append(kerb)
    centres[kerb["name"]] = [_lip(pts, k, "L") for k in range(140, 161)]
    return {
        "standin_bands": False, "edge_mode": "road", "barrier_height_m": 1.2,
        "race_prefixes": ["1WALL_RACE", "1KERB_RACE"], "max_rings_per_object": 800,
        "totals": {"objects": len(objs), "rings": sum(o.get("rings", 0) for o in objs), "kerb_stations": 60,
                   "seated_interpolated": 0, "deck_vs_data_max_m": 0.02, "other_deck_above_max_m": 0.0},
        "corners": [{"apex_vertex": 150}], "kerbs_declared_unmatched": [], "failed_runs": [],
        "spawn_clearance": {"race_cw": {"hard": [], "notes": [], "synthesised": False}},
        "other_deck_above": [], "objects": objs, "ring_centres": centres,
    }


def _island_w():
    return [6.0 if k in ISLAND else 0.0 for k in range(N + 1)]


def _run(authored, bands=None, **kw):
    pts = _pts()
    return vr.verify(authored, bands or _bands(), pts, _island_w(), **kw)


def test_consistent_authoring_passes_and_counts():
    r = _run(_authored(_pts()))
    assert r["ok"], r["fails"]
    c = r["counts"]
    assert c["chain_objects"] == 1 and c["chain_runs"] == 1 and c["edge_objects"] == 4 and c["kerb_objects"] == 1
    assert c["edge_missing"] == {"L": 0, "R": 0}
    assert c["edge_declared_vertices"] == N - len(GAP)


def test_chain_ring_on_an_island_or_on_alvarado_fails():
    pts = _pts()
    a = _authored(pts)
    a["ring_centres"]["1WALL_race_kbar_t_61_0"][5] = list(pts[55])       # onto the island
    r = _run(a)
    assert not r["ok"] and any("median island" in f for f in r["fails"]), r["fails"]
    a = _authored(pts)
    a["ring_centres"]["1WALL_race_kbar_t_61_0"][5] = list(pts[10])       # onto Alvarado (also off-band)
    r = _run(a)
    assert any("Alvarado" in f for f in r["fails"]) and any("does not declare" in f for f in r["fails"]), r["fails"]


def test_chain_run_end_off_the_declared_vertex_fails():
    pts = _pts()
    a = _authored(pts)
    a["ring_centres"]["1WALL_race_kbar_t_61_0"] = a["ring_centres"]["1WALL_race_kbar_t_61_0"][:-3]   # ends 3 verts short
    r = _run(a)
    assert any("ends" in f and "declared end vertices" in f for f in r["fails"]), r["fails"]


def test_missing_edge_rings_beyond_the_reported_fold_drop_fail():
    pts = _pts()
    a = _authored(pts)
    name = "1WALL_race_edge_R_t_0_0"
    a["ring_centres"][name] = a["ring_centres"][name][:100]     # rings 100..119 gone, end still 'free' -> hole
    r = _run(a)
    assert any(f.startswith("D: edge R") and "without a ring" in f for f in r["fails"]), r["fails"]
    assert any("free end" in f and "not at a declared gap" in f for f in r["fails"]), r["fails"]
    # the same loss, declared as fold-dropped by the author, is accepted (the inside-apex rule)
    for o in a["objects"]:
        if o["name"] == name:
            o["fold_skipped_run"] = 20
            o["ends"] = ["join", "join"]            # ...but a join that nothing meets is still a miss
    r = _run(a)
    assert not any("without a ring" in f for f in r["fails"]), r["fails"]
    assert any("no same-side object meets it" in f for f in r["fails"]), r["fails"]


def test_edge_ring_inside_a_declared_gap_fails():
    pts = _pts()
    a = _authored(pts)
    a["ring_centres"]["1WALL_race_edge_L_t_0_0"].append(_lip(pts, 125, "L"))    # inside the span
    r = _run(a)
    assert any("inside a declared gap" in f for f in r["fails"]), r["fails"]


def test_budgets_and_seating_gate():
    pts = _pts()
    a = _authored(pts)
    a["objects"][0]["seat_gap_max_m"] = 0.2
    a["objects"][1]["rings"] = 901
    a["objects"][2]["loops"] = 50_000
    a["objects"][3]["name"] = "WALL_strip"      # not RACE-prefixed
    r = _run(a)
    f = " | ".join(r["fails"])
    assert "seating gap" in f and "901 rings" in f and "flat render verts" in f and "not RACE-prefixed" in f, f


def test_kerb_set_spawn_overlap_and_provenance():
    pts = _pts()
    a = _authored(pts)
    a["objects"][-1]["sub"] = "in"
    r = _run(a)
    assert any(f.startswith("E: declared kerbs") for f in r["fails"]), r["fails"]
    a = _authored(pts)
    a["spawn_clearance"]["race_cw"]["hard"] = ["AC_START_1 overlaps 1WALL_race_edge_R"]
    r = _run(a)
    assert any(f.startswith("F: race_cw: a spawn overlaps") for f in r["fails"]), r["fails"]
    a = _authored(pts)
    a["standin_bands"] = True
    assert not _run(a)["ok"] and _run(a, allow_standin=True)["ok"]
    a = _authored(pts)
    a["edge_mode"] = "walk"
    assert any("edge_mode" in f for f in _run(a)["fails"])
    a = _authored(pts)
    a["totals"]["seated_interpolated"] = 50        # > 1 % of ~ 419 rings
    assert any("interpolation" in f for f in _run(a)["fails"])


def test_cli_writes_the_report_and_exits_nonzero_on_a_miss():
    import tempfile
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    pts = _pts()
    (d / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": [list(p) for p in pts], "widths_m": [W] * (N + 1)}))
    (d / "data" / "median_bands.json").write_text(json.dumps({"island_w_by_vertex": _island_w()}))
    (d / "data" / "barrier_bands.json").write_text(json.dumps(_bands()))
    (d / "data" / "race_authored.json").write_text(json.dumps(_authored(pts)))
    assert vr.main([str(d)]) == 0
    rep = json.loads((d / "data" / "race_verify.json").read_text(encoding="utf-8"))
    assert rep["ok"] is True
    bad = _authored(pts)
    bad["failed_runs"] = ["1WALL_race_kbar_t_61_0"]
    (d / "data" / "race_authored.json").write_text(json.dumps(bad))
    assert vr.main([str(d)]) == 1
    assert json.loads((d / "data" / "race_verify.json").read_text(encoding="utf-8"))["ok"] is False


# --- F (re-measured from the dummies that ship) and G (lamp masts vs the strips) ------------------
# On the synthetic ring the forward travel is anticlockwise, so + lateral (left) points at the centre;
# the kerb-line strip's road-side face is at |lat| = W/2 - 0.82 = 9.18 m, its back at W/2 - 0.15 = 9.85 m.

def _radial(k, r):
    """a point r metres OUTWARD (right of forward travel) from vertex k"""
    a = 2 * math.pi * k / N
    return [round((R + r) * math.cos(a), 4), 5.4, round((R + r) * math.sin(a), 4)]


def _dummies(slots, kind="race"):
    d = {"_layout": "race_cw", "_kind": kind, "_yaw_deg": {}, "AC_TIME_0_L": _radial(20, -9.7)}
    d.update(slots)
    return d


def _run_fg(spawns=None, lamps=None, **kw):
    pts = _pts()
    return vr.verify(None, _bands(), pts, _island_w(), pre_author=True, widths=[W] * (N + 1),
                     spawns=spawns, lamps=lamps, **kw)


def test_spawn_clearance_is_remeasured_from_the_dummies_and_hard_below_030():
    ok = _dummies({"AC_START_0": _radial(10, 7.0), "AC_START_1": _radial(12, 7.5), "AC_PIT_0": _radial(30, 7.0)})
    r = _run_fg({"race_cw": ok})
    assert r["ok"], r["fails"]
    assert abs(r["counts"]["spawn_min_clear_m"]["race_cw"] - 0.73) < 1e-3          # 9.18 - (7.5 + 0.95)
    assert [s["name"] for s in r["counts"]["spawn_slots"]["race_cw"]] == ["AC_PIT_0", "AC_START_0", "AC_START_1"]
    tight = _dummies({"AC_START_1": _radial(12, 8.0)})                              # 0.23 m: was legal, now hard
    r = _run_fg({"race_cw": tight})
    assert any(f.startswith("F: race_cw: AC_START_1") and "0.23 m clear of the edge-strip face" in f for f in r["fails"]), r["fails"]
    over = _dummies({"AC_START_1": _radial(12, 8.5)})
    assert any("OVERLAPS" in f for f in _run_fg({"race_cw": over})["fails"])
    chain = _dummies({"AC_START_0": _radial(80, -1.4)})                            # 1.4 - 0.95 - 0.335 = 0.115 m
    assert any("centre chain" in f for f in _run_fg({"race_cw": chain})["fails"])
    assert any("no data/dummies_race_acw.json" in f for f in _run_fg({"race_acw": None})["fails"])
    synth = dict(ok, _synthesised=True)
    assert any("SYNTHESISED" in f for f in _run_fg({"race_cw": synth})["fails"])
    # the authored path still runs F from disk too: a clean authored file with a tight dummy fails
    pts = _pts()
    r = vr.verify(_authored(pts), _bands(), pts, _island_w(), widths=[W] * (N + 1), spawns={"race_cw": tight})
    assert not r["ok"] and any(f.startswith("F: race_cw: AC_START_1") for f in r["fails"])


def test_lamp_masts_must_stand_outside_every_strip_footprint():
    # heads 1.8 m road-ward of the mast (author_lamps_blend ARM_M): head at R + 11.0 -> mast at R + 12.8
    clear = [_radial(30, 11.0), _radial(170, 11.0)]
    r = _run_fg(lamps=clear, mast_r_m=0.5)
    assert r["ok"], r["fails"]
    c = r["counts"]
    assert c["lamps"] == 2 and c["lamps_checked"] == 2 and c["lamp_arm_m"] == 1.8
    assert abs(c["lamp_min_margin_m"] - (12.8 - 9.85 - 0.5)) < 1e-3, c["lamp_min_margin_m"]
    inside = clear + [_radial(60, 7.8)]                    # mast at R + 9.6: inside [9.18, 9.85]
    r = _run_fg(lamps=inside, mast_r_m=0.5)
    assert not r["ok"] and any(f.startswith("G: lamp 2 at v60") and "inside the edge strip footprint" in f for f in r["fails"]), r["fails"]
    assert r["counts"]["lamps_inside"] == 1
    touching = clear + [_radial(60, 8.6)]                  # mast at R + 10.4: 0.55 m behind the strip, r 0.6 -> -0.05
    assert not _run_fg(lamps=touching, mast_r_m=0.6)["ok"]
    gap = [_radial(125, 7.8)]                              # inside a declared bridge gap: no strip there
    r = _run_fg(lamps=gap, mast_r_m=0.5)
    assert r["ok"] and r["counts"]["lamps_checked"] == 0


def test_lamp_constants_come_from_the_author_tool_and_the_model():
    assert vr._author_lamps_constant("ARM_M", -1.0) == 1.8
    assert vr._author_lamps_constant("POST_H", -1.0) == 11.5
    assert vr._author_lamps_constant("NOT_THERE", -1.0) == -1.0
    r = vr.mast_radius_m(11.5)
    assert 0.5 < r < 0.7, r                                # the base plate corner, 0.585 m at 11.5 m


def test_race_layout_spawns_reads_every_race_dummies_file():
    import tempfile
    d = Path(tempfile.mkdtemp())
    (d / "dummies_race_cw.json").write_text(json.dumps({"_kind": "race", "AC_START_0": [0, 0, 0]}))
    (d / "dummies_street.json").write_text(json.dumps({"_kind": "street", "AC_START_0": [0, 0, 0]}))
    cfg = {"layouts": [{"id": "street"}, {"id": "race_cw", "race_furniture": True}, {"id": "race_acw", "race_furniture": True}]}
    sp = vr.race_layout_spawns(d, cfg)
    assert set(sp) == {"race_cw", "race_acw"} and sp["race_acw"] is None and sp["race_cw"]["_kind"] == "race"
    # a workshop whose config predates the layouts is judged on the files' own _kind
    assert set(vr.race_layout_spawns(d, {"layouts": [{"id": "full"}]})) == {"race_cw"}


def test_cli_pre_author_needs_no_authored_file():
    import tempfile
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    pts = _pts()
    (d / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": [list(p) for p in pts], "widths_m": [W] * (N + 1)}))
    (d / "data" / "median_bands.json").write_text(json.dumps({"island_w_by_vertex": _island_w()}))
    (d / "data" / "barrier_bands.json").write_text(json.dumps(_bands()))
    (d / "data" / "lights.local.json").write_text(json.dumps({"lampheads": [_radial(30, 11.0)]}))
    (d / "data" / "dummies_race_cw.json").write_text(json.dumps(_dummies({"AC_START_1": _radial(12, 7.5)})))
    out = d / "pre.json"
    assert vr.main([str(d), "--pre-author", "--out", str(out)]) == 0
    rep = json.loads(out.read_text(encoding="utf-8"))
    assert rep["ok"] and "race_cw" in rep["counts"]["spawn_slots"] and rep["counts"]["lamps_checked"] == 1
    assert not (d / "data" / "race_verify.json").exists()
    (d / "data" / "dummies_race_cw.json").write_text(json.dumps(_dummies({"AC_START_1": _radial(12, 8.0)})))
    assert vr.main([str(d), "--pre-author", "--out", str(out)]) == 1
