"""Ledger 0099 round 3, items 1b and 2: Mission Gorge Rd's long median island (MD13) was declared, and built, unbroken
across the real Margerum Avenue / Mission Vista Drive crossing (1b), and the J3 end of the median stood about 13 m from
where the photo has it (2: MD11's last 60 m, the two openings, MD12, MD13's start). Both are corrected at the source from
the photo (source/expansion/mg_median/fix_mg_median.py) and re-authored in the scene by an author step
(tools/author_median_rebuild_blend.py), because Lake Murray's chain never runs its draft again.

Held here, without Blender: the corrected data is the fit applied to the declared values and nothing else; the
correction is idempotent; the scene step's pure parts give, from the record, exactly the island the committed blend
holds (the counts the scratch run found in the scene) and the two islands that replace it; the plants dropped are the
ones on pavement, every one bare on the lidar; the wiring. The scene work is self-checked in Blender and measured
through the chain's own steps on a scratch workshop. Plain ``test_*`` for tests/run_tests.py."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LM = ROOT / "tracks" / "san-diego-lake-murray"
MG = LM / "source" / "expansion" / "mg_median"
LINE = "north_mission_gorge"
CFG = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))
SHIP = json.loads((LM / "ship.json").read_text(encoding="utf-8"))
REC = json.loads((MG / "mg_median_correction.json").read_text(encoding="utf-8"))
DOC = json.loads((LM / "data" / "expansion.north.json").read_text(encoding="utf-8"))
BANDS = json.loads((LM / "data" / "median_bands.json").read_text(encoding="utf-8"))
ISLAND = next(c for c in BANDS["connector_islands"] if c["name"] == LINE)
CONN = next(c for c in json.loads((LM / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"] if c["name"] == LINE)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
FIX = _load("fix_mg_median_0099", MG / "fix_mg_median.py")
RB = _load("author_median_rebuild_0099", ROOT / "tools" / "author_median_rebuild_blend.py")
MI = _load("median_island_0099", ROOT / "tools" / "median_island.py")


# ---- the data -------------------------------------------------------------------------------------------------------

def test_the_fit_is_what_the_photo_measured():
    """the README's table: strip A 1.96 m with its middle 0.43 m left, strip B 1.84 m with its middle 1.50 m right, no
    median between the noses at s 1085 and s 1120, tapers from s 982.5 and to s 1212.5"""
    assert FIX.STRIP_A == (0.43, 1.96) and FIX.STRIP_B == (-1.50, 1.84)
    assert (FIX.JOIN_A, FIX.STRIP_A_FROM, FIX.NOSE_A, FIX.NOSE_B, FIX.STRIP_B_TO, FIX.JOIN_B) == (982.5, 1010.0, 1085.0, 1120.0, 1192.5, 1212.5)
    t = "terracotta"
    assert FIX.fit(900.0, t, 4.4, 0.4) == (t, 4.4, 0.4) and FIX.fit(1300.0, t, 5.5, -0.6) == (t, 5.5, -0.6)
    assert FIX.fit(982.5, t, 4.5, 0.5) == (t, 4.5, 0.5) and FIX.fit(1212.5, t, 5.4, -0.5) == (t, 5.4, -0.5)
    ty, w, o = FIX.fit(1050.0, t, 4.74, 0.23)
    assert ty == t and w == 1.96 and abs(o - 0.66) < 1e-9
    assert FIX.fit(1085.0, t, 4.87, 0.08)[1] == 1.96 and FIX.fit(1120.0, t, 5.01, -0.07)[1] == 1.84
    for s in (1087.5, 1100.0, 1117.5):
        assert FIX.fit(s, t, 4.9, 0.0) == ("none", 0.0, 0.0)
    ty, w, o = FIX.fit(1150.0, t, 5.12, -0.2)
    assert w == 1.84 and abs(o + 1.70) < 1e-9
    w_mid = FIX.fit(996.25, t, 4.5, 0.5)[1]                                  # half way down the first taper
    assert abs(w_mid - (4.5 + 1.96) / 2) < 1e-9
    # the J3 end (item 2): MD11 leaves its declared line from s 100, 3.6 m left by s 136, and ends at s 177.5; the two
    # openings; MD12 where it stands, 3.40 m wide, its middle 1.0 m left at s 195 and 2.3 m at s 207.5; MD13 from s 225
    assert (FIX.VEER_FROM, FIX.VEER_TO, FIX.VEER_M, FIX.MD11_TO) == (100.0, 136.0, 3.6, 177.5)
    assert (FIX.MD12_FROM, FIX.MD12_TO, FIX.MD12_W, FIX.MD12_MID, FIX.MD13_FROM) == (195.0, 207.5, 3.40, (1.0, 2.3), 225.0)
    assert FIX.fit(40.0, "none", 0.0, -0.2) == ("none", 0.0, -0.2) and FIX.fit(100.0, t, 1.24, -0.5) == (t, 1.24, -0.5)
    v118, v150 = FIX.fit(118.0, t, 1.3, -0.5), FIX.fit(150.0, t, 1.52, -0.5)
    assert v118[1] == 1.3 and abs(v118[2] - 1.3) < 1e-9 and v150[1] == 1.52 and abs(v150[2] - 3.1) < 1e-9   # half way up the veer; on it
    assert abs(FIX.fit(177.5, t, 1.67, -0.5)[2] - 3.1) < 1e-9
    for s in (180.0, 192.5, 210.0, 222.5):
        assert FIX.fit(s, t, 1.8, -0.5) == ("none", 0.0, -0.5)
    a195, a207 = FIX.fit(195.0, t, 1.77, -0.5), FIX.fit(207.5, t, 1.84, -0.5)
    assert a195[:2] == (t, 3.40) and abs(a195[2] - 0.5) < 1e-9 and a207[:2] == (t, 3.40) and abs(a207[2] - 1.8) < 1e-9
    assert FIX.fit(225.0, t, 1.94, -0.5) == (t, 1.94, -0.5) and FIX.fit(600.0, t, 4.0, 0.1) == (t, 4.0, 0.1)
    assert FIX.STRETCHES == [(100.0, 231.0), (982.5, 1212.5)]
    assert FIX.ISLANDS == [("MD11", 45.0, 177.5), ("MD12", 195.0, 207.5), ("MD13", 225.0, 1085.0), ("MD13b", 1120.0, 2245.0)]
    readme = (MG / "README.md").read_text(encoding="utf-8")
    for frag in ("1.96 m", "1.84 m", "0.43 m", "1.50 m", "[inferred]", "3.6 m", "3.40 m", "s 177.5", "owed"):
        assert frag in readme, frag


def test_piece_cs_rows_are_the_fit_on_the_declared_values_and_nothing_else():
    pc = next(p for p in DOC["pieces"] if p["id"] == "C")
    cols = pc["columns"]
    it, iw, io = cols.index("median_type"), cols.index("median_w_m"), cols.index("median_off_m")
    rows = {float(r[0]): r for r in pc["stations"]}
    rec_rows = {float(r["s"]): r for r in REC["rows"]}
    assert len(rec_rows) == 146 and min(rec_rows) == 100.0 and max(rec_rows) == 1212.5      # 53 at the J3 end, 93 at the crossing
    changed = 0
    for s, r in rec_rows.items():
        ty, w, o = FIX.fit(s, r["median_type"][0], r["median_w_m"][0], r["median_off_m"][0])
        assert (r["median_type"][1], r["median_w_m"][1], r["median_off_m"][1]) == (ty, round(w, 2), round(o, 2)), s
        assert (rows[s][it], rows[s][iw], rows[s][io]) == (ty, round(w, 2), round(o, 2)), s      # the file holds the fit
        assert r["median_type"][0] == "terracotta"
        changed += (r["median_w_m"][0], r["median_off_m"][0]) != (r["median_w_m"][1], r["median_off_m"][1])
    assert changed == 91 + 49                                                                    # the join rows hold
    gap = [s for s, r in rows.items() if r[it] == "none" and s > 100]
    assert gap == [180.0 + 2.5 * k for k in range(6)] + [210.0 + 2.5 * k for k in range(6)] + [1087.5 + 2.5 * k for k in range(13)]
    assert all(rows[s][iw] == 0 for s in gap)


def test_md13_ends_at_its_nose_and_md13b_begins_at_the_other():
    meds = DOC["medians"]
    ids = [m["id"] for m in meds]
    assert ids == [f"MD{k}" for k in range(1, 14)] + ["MD13b"] + [f"MD{k}" for k in range(14, 23)]   # no other id moved
    a, b = (next(m for m in meds if m["id"] == i) for i in ("MD13", "MD13b"))
    m11, m12 = (next(m for m in meds if m["id"] == i) for i in ("MD11", "MD12"))
    assert (a["s_from"], a["s_to"], b["s_from"], b["s_to"]) == (225.0, 1085.0, 1120.0, 2245.0)
    assert (m11["s_from"], m11["s_to"], m12["s_from"], m12["s_to"], m12["width_m"]) == (45.0, 177.5, 195.0, 207.5, [3.4, 3.4])
    assert a["piece"] == b["piece"] == "C" and a["raised"] and b["raised"] and a["type"] == b["type"] == "terracotta"
    # one ring point a side per 2.5 m station
    assert [len(m["polygon_xz"]) for m in (m11, m12, a, b)] == [2 * 54, 2 * 6, 2 * 345, 2 * 451]
    assert REC["rings_before"] == {"MD11": {"s_from": 45.0, "s_to": 167.5, "points": 100}, "MD12": {"s_from": 182.5, "s_to": 195.0, "points": 12},
                                   "MD13": {"s_from": 210.0, "s_to": 2245.0, "points": 1630}}
    for m in (m11, m12, a, b):
        c = m["correction"]
        assert c["ledger"] == "0099 round 3, items 1b and 2"
        assert c["fit"]["no_median_s"] == [[177.5, 195.0], [207.5, 225.0], [1085.0, 1120.0]]
        assert c["fit"]["stretches_s"] == [[100.0, 231.0], [982.5, 1212.5]]
        assert c["centre_paint_where_there_is_no_median"]["source"] == "photo" and "[inferred]" in c["inferred"]
        assert "owed" in c["not_built"]
    # the ring's new noses taper to the generator's blunt end (tools/author_expansion.py NOSE_W_M)
    import math
    na, nb = len(a["polygon_xz"]) // 2, len(b["polygon_xz"]) // 2
    end_a = math.dist(a["polygon_xz"][na - 1], a["polygon_xz"][na])
    start_b = math.dist(b["polygon_xz"][0], b["polygon_xz"][-1])
    assert abs(end_a - FIX.NOSE_W_M) < 0.01 and abs(start_b - FIX.NOSE_W_M) < 0.01
    n11 = len(m11["polygon_xz"]) // 2
    assert abs(math.dist(m11["polygon_xz"][n11 - 1], m11["polygon_xz"][n11]) - FIX.NOSE_W_M) < 0.01       # MD11's new end, s 177.5
    assert abs(math.dist(a["polygon_xz"][0], a["polygon_xz"][-1]) - FIX.NOSE_W_M) < 0.01                 # MD13's new start, s 225
    src = (ROOT / "tools" / "author_expansion.py").read_text(encoding="utf-8")
    assert "NOSE_M = 6.0 " in src and "NOSE_W_M = 0.6 " in src and (FIX.NOSE_M, FIX.NOSE_W_M) == (6.0, 0.6)


def test_the_island_and_the_paint_are_decorates_and_the_crossing_carries_no_centre_line():
    w = ISLAND["island_w_by_point"]
    assert [(i, j - 1) for i, j in MI.segments(w)] == [(8, 51), (68, 354), (367, 741)]            # MD12's four points are no island
    assert REC["island"]["runs_of_points_with_an_island"] == [[8, 51], [58, 61], [68, 354], [367, 741]]
    assert REC["island"]["points_changed_runs"] == [[26, 51], [54, 61], [63, 67], [321, 397]]
    assert REC["island"]["points_changed"] == len(REC["island"]["before"]) == 116
    assert all(w[k] == 1.96 for k in range(331, 352)) and all(w[k] == 1.84 for k in range(370, 389))
    assert all(w[k] == 3.4 for k in range(58, 62))
    assert REC["island"]["points_with_no_median_runs"] == [[53, 57], [63, 67], [356, 365]]
    gap = [k for a_, b_ in REC["island"]["points_with_no_median_runs"] for k in range(a_, b_ + 1)]
    assert len(gap) == 20 and all(w[k] == 0 for k in gap)
    lines = CONN["paint"]["lines"]
    assert len(lines) == REC["paint"]["lines"] == 14 and REC["paint"]["centre_line_offsets_cleared_where_there_is_no_median"] == 40
    for k in range(58, 62):                                          # MD12: the painted outline, its two edge lines, and no island
        assert len([ln for ln in lines if ln["color"] == "yellow" and not ln["dash"] and ln["off"][k] is not None]) == 2, k
    for k in gap:                                                    # no solid yellow line of any kind between the noses
        assert not [ln for ln in lines if ln["color"] == "yellow" and not ln["dash"] and ln["off"][k] is not None], k
        assert sum(1 for ln in lines if ln["color"] == "white" and ln["off"][k] is not None) >= 4      # lanes and bike lines run on
    before = REC["paint"]["before"]
    assert set(int(k) for k in before) <= set(range(14)) and {3, 4, 6, 7, 8, 9} <= set(int(k) for k in before)
    assert all(26 <= int(i) <= 67 or 321 <= int(i) <= 397 for d in before.values() for i in d)


def test_the_correction_changes_nothing_on_a_second_run():
    files = [LM / "data" / "expansion.north.json", LM / "data" / "median_bands.json", LM / "data" / "connectors.local.json",
             MG / "mg_median_correction.json"]
    was = [hashlib.md5(f.read_bytes()).hexdigest() for f in files]
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        assert FIX.main([]) == 0                                      # the table only: nothing written
    assert [hashlib.md5(f.read_bytes()).hexdigest() for f in files] == was
    src = (MG / "fix_mg_median.py").read_text(encoding="utf-8")
    for frag in ("neither the declared", "ep.decorate(tmp)", 'if conn["points_xyz_m"] != conn_t["points_xyz_m"]:',
                 "centre lines found where decorate's rule draws two; refused"):
        assert frag in src, frag


# ---- the scene step's pure parts ------------------------------------------------------------------------------------

def test_the_record_gives_back_the_island_the_committed_blend_holds():
    sp = RB.spec(CFG)
    assert sp == {"line": LINE, "was": [(8, 48), (63, 741)], "record": "source/expansion/mg_median/mg_median_correction.json"}
    assert RB.spec({}) is None and RB.spec({"route": {}}) is None
    assert RB.spec({"route": {"median_rebuild": {"line": LINE, "was_rows": [63, 741], "record": "x"}}})["was"] == [(63, 741)]   # one pair
    pts0, iw0 = RB.old_data(ISLAND, REC)
    assert [(i, j - 1) for i, j in MI.segments(iw0)] == [(8, 48), (63, 741)]            # the line as the committed blend holds it
    o11, o13 = RB.island_parts(pts0, iw0, 8, 48), RB.island_parts(pts0, iw0, 63, 741)
    # what the scratch run found in the committed blend, part for part (2026-11-23)
    assert [len(v) for v, _f in o11["curb"]] == [246] and [len(v) for v, _f in o11["deck"]] == [82]
    assert [len(v) for v, _f in o11["beam"]] == [140] and len(o11["posts"]) == 11
    assert [len(v) for v, _f in o13["curb"]] == [4074] and [len(f) for _v, f in o13["curb"]] == [2716]
    assert [len(v) for v, _f in o13["deck"]] == [1358] and [len(v) for v, _f in o13["beam"]] == [2692] and len(o13["posts"]) == 224
    pts1, iw1 = [list(p) for p in ISLAND["points_xyz_m"]], [float(x) for x in ISLAND["island_w_by_point"]]
    new = RB.island_parts(pts1, iw1, 8, 741)
    assert new["runs"] == [[8, 51], [68, 354], [367, 741]]
    assert [len(v) for v, _f in new["curb"]] == [264, 1722, 2250] and [len(v) for v, _f in new["deck"]] == [88, 574, 750]
    assert [len(v) for v, _f in new["beam"]] == [152, 1124, 1476] and len(new["posts"]) == 228
    # outside the points the corrections changed (26-67, 321-397), the one point each side whose direction they turn (a
    # ring stands across the line from its neighbours) and a new island's own three-point nose, old and new are the same
    # islands, vertex for vertex
    assert o11["curb"][0][0][:6 * (25 - 8)] == new["curb"][0][0][:6 * (25 - 8)]
    assert o13["curb"][0][0][6 * (71 - 63):6 * (320 - 63)] == new["curb"][1][0][6 * (71 - 68):6 * (320 - 68)]
    assert o13["curb"][0][0][6 * (399 - 63):] == new["curb"][2][0][6 * (399 - 367):]
    assert o13["deck"][0][0][2 * (399 - 63):] == new["deck"][2][0][2 * (399 - 367):]
    for bad in ({"line": LINE}, {"line": LINE, "was_rows": [63], "record": "x"}, {"was_rows": [63, 741], "record": "x"},
                {"line": LINE, "was_rows": [[8, 70], [63, 741]], "record": "x"}, {"line": LINE, "was_rows": [[48, 8]], "record": "x"}):
        try:
            RB.spec({"route": {"median_rebuild": bad}})
        except SystemExit:
            continue
        raise AssertionError(bad)


def test_the_old_paint_is_the_new_with_the_records_offsets_put_back():
    old = RB.old_paint(CONN["paint"], REC)
    n_diff = sum(1 for a, b in zip(old["lines"], CONN["paint"]["lines"]) for x, y in zip(a["off"], b["off"]) if x != y)
    assert n_diff == sum(len(d) for d in REC["paint"]["before"].values()) and n_diff > 600
    assert CONN["paint"]["lines"][3]["off"][340] != old["lines"][3]["off"][340]            # and the file's own is not touched
    assert CONN["paint"]["lines"][8]["off"][45] != old["lines"][8]["off"][45]              # MD11's edge line where it veers


def test_the_step_refuses_an_island_that_is_not_exactly_the_one_recorded():
    src = (ROOT / "tools" / "author_median_rebuild_blend.py").read_text(encoding="utf-8")
    for frag in ("the scene does not hold the island exactly as rows",                    # the Mac's refusal, 2026-11-23
                 "if self.size[r] != len(want):",                                         # a part of another size is not it
                 "if max((self.co[i] - w).length for i, w in zip(idx, want)) <= TOL_M:",  # every vertex where the rule puts it
                 "the scene carries a median_rebuild stamp of other data",
                 "nothing to do, nothing saved",
                 "an old {kind} part is still in the scene",
                 "new deck vertices do not stand",
                 "wr.connector_markings(cpts, list(conn[\"widths_m\"]), conn.get(\"stub\"), paint)"):
        assert frag in src, frag
    assert RB.TOL_M == 2e-3 and "LAYOUT_TOL_M = 2e-3" in (ROOT / "tools" / "weld_mouths_blend.py").read_text(encoding="utf-8")
    mt = _load("author_median_tops_mg", ROOT / "tools" / "author_median_tops_blend.py")
    assert (RB.DECK_OVER_M, RB.DECK_TOL_M) == (mt.DECK_OVER_M, mt.DECK_TOL_M)
    weld = (ROOT / "tools" / "weld_mouths_blend.py").read_text(encoding="utf-8")
    assert "(x, y + 0.115, z)" in weld and RB.PAINT_LIFT_M == 0.115                       # the assembler's paint lift, as the weld reads it
    try:
        RB.island_parts([[0.0, 0.0, float(k)] for k in range(30)], [2.0] * 30, 5, 20)
    except SystemExit:
        pass
    else:
        raise AssertionError("an island reaching outside the rows given was taken")


def test_the_step_takes_every_island_named_and_refuses_one_left_out():
    """item 2: two built islands change (MD11 rows 8-48, MD13 rows 63-741), each found on its own or refused"""
    one = RB.spec({"route": {"median_rebuild": {"line": "L", "was_rows": [63, 741], "record": "r.json"}}})
    assert one["was"] == [(63, 741)]                                                      # item 1b's form still reads
    two = RB.spec({"route": {"median_rebuild": {"line": "L", "was_rows": [[63, 741], [8, 48]], "record": "r.json"}}})
    assert two["was"] == [(8, 48), (63, 741)]                                             # in the line's order
    assert RB.spec(CFG)["was"] == [(8, 48), (63, 741)]
    for bad in ([[8, 48], [48, 741]], [[8, 80], [63, 741]], [[48, 8]], [[8, 48, 63]], []):
        try:
            RB.spec({"route": {"median_rebuild": {"line": "L", "was_rows": bad, "record": "r.json"}}})
        except SystemExit:
            continue
        raise AssertionError(f"was_rows {bad} was taken")
    src = (ROOT / "tools" / "author_median_rebuild_blend.py").read_text(encoding="utf-8")
    for frag in ("between the rows given: name every built island the step re-authors",   # an island left out is not skipped
                 "the old islands' decks lie in two objects",
                 "on the ring of the old island rows {rows_}",                            # each island is found on its own
                 "json.dumps([sp[\"line\"], sp[\"was\"],"):                               # the stamp's checksum covers the list
        assert frag in src, frag
    # the record's data holds exactly the two islands named, and none between them
    _pts, iw_old = RB.old_data(ISLAND, REC)
    segs = [(i, j - 1) for i, j in MI.segments(iw_old)]
    assert [g for g in segs if 8 <= g[0] and g[1] <= 741] == [(8, 48), (63, 741)], segs


# ---- the plants -----------------------------------------------------------------------------------------------------

def test_the_plants_on_pavement_are_dropped_and_every_one_is_bare_on_the_lidar():
    sp = json.loads((MG / "mg_median.median_spots.json").read_text(encoding="utf-8"))
    spots = json.loads((LM / "data" / "scatter_positions.json").read_text(encoding="utf-8"))["median_planting"]
    lidar = json.loads((LM / "source" / "vegetation" / "median_heights.lidar.json").read_text(encoding="utf-8"))
    assert len(sp["drop"]) == 21 and len(sp["kept_on_the_new_deck"]) == 18
    assert sp["points_runs"] == [[26, 51], [54, 61], [63, 67], [321, 397]]              # no spot stands on the J3 end's narrow islands
    where = {}
    for d in sp["drop"]:
        s = spots[d["index"]]
        assert (s["x"], s["z"]) == (d["x"], d["z"])                                  # the spot's own place: make_treefx checks it too
        assert lidar["spots"][d["index"]][2] < lidar["min_h_m"] == 0.3                # no plant the lidar saw is dropped
        assert d["half_m"] == 0 or abs(d["lateral_m"]) > d["half_m"] - MI.DECK_INSET
        where[d["where"]] = where.get(d["where"], 0) + 1
    assert where == {"no median: between the two noses": 6, "pavement beside the island": 14, "the strip's curb ring": 1}
    for k in sp["kept_on_the_new_deck"]:
        assert abs(k["lateral_m"]) <= k["deck_half_m"]
    assert not {d["index"] for d in sp["drop"]} & {k["index"] for k in sp["kept_on_the_new_deck"]}
    college = json.loads((LM / "source" / "college_r2" / "college_plants.median_spots.json").read_text(encoding="utf-8"))
    assert not {d["index"] for d in sp["drop"]} & {d["index"] for d in college["drop"] + college["foot_y"]}
    ms = CFG["scenery"]["treefx"]["median_spots"]
    assert ms["file"] == "source/college_r2/college_plants.median_spots.json"
    assert ms["files"] == ["source/expansion/mg_median/mg_median.median_spots.json"]


def test_make_treefx_reads_every_list_it_is_given():
    mt = _load("make_treefx_mg", ROOT / "tools" / "make_treefx.py")
    src = (ROOT / "tools" / "make_treefx.py").read_text(encoding="utf-8")
    for frag in ('for ms_name_ in ([ms_cfg["file"]] if ms_cfg.get("file") else []) + list(ms_cfg.get("files") or []):',
                 "ms_lists_[kind_] += list(ms_one_.get(kind_) or [])"):
        assert frag in src, frag
    assert hasattr(mt, "plan")


# ---- the wiring -----------------------------------------------------------------------------------------------------

def test_median_rebuild_is_lake_murrays_alone_and_runs_before_the_tops():
    au = SHIP["steps"]["author"]
    assert au[:3] == ["college_split", "median_rebuild", "median_tops"]
    sh = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")
    assert "author_median_rebuild() {" in sh
    assert 'tools/author_median_rebuild_blend.py" -- "$PROJ" --v021 "$V021"' in sh
    for f in ("source/expansion/mg_median/mg_median_correction.json", "source/expansion/mg_median/mg_median.median_spots.json"):
        assert f in SHIP["sync_in"]["optional"] and (LM / f).is_file(), f
    assert "data/median_rebuild.json" in SHIP["sync_out"]["files"]
    mr = CFG["route"]["median_rebuild"]
    assert (mr["line"], mr["was_rows"], mr["record"]) == (LINE, [[8, 48], [63, 741]], "source/expansion/mg_median/mg_median_correction.json")
    paved = [(i["line"], i["rows"]) for i in CFG["route"]["median_tops"]["paver"]["islands"]]
    assert paved == [(LINE, [8, 51]), (LINE, [68, 354]), (LINE, [367, 741])]             # the islands the rebuild leaves
    for p in sorted((ROOT / "tracks").glob("*/track.config.json")):
        if p.parent != LM:
            assert "median_rebuild" not in (json.loads(p.read_text(encoding="utf-8")).get("route") or {}), p
    for p in sorted((ROOT / "tracks").glob("*/ship.json")):
        if p.parent != LM:
            assert "median_rebuild" not in (json.loads(p.read_text(encoding="utf-8")).get("steps", {}).get("author") or []), p
