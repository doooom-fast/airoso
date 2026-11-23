"""Ledger 0099 round 3, items 1b and 2: Mission Gorge Rd's long median island (MD13) was declared, and built, unbroken
across the real Margerum Avenue / Mission Vista Drive crossing (1b), and the J3 end of the median stood about 13 m from
where it really is (2: MD11's last 60 m, the two openings, MD12, MD13's start). Both are corrected at the source
(source/expansion/mg_median/fix_mg_median.py) and re-authored in the scene by an author step
(tools/author_median_rebuild_blend.py), because Lake Murray's chain never runs its draft again. The numbers were the
photo's first; they are the 2024 lidar's now (the G10's faces, mg_median_faces.lidar.g10.json), because the photo's
readings had been "corrected" against a band the island does not fill.

Held here, without Blender: a row takes the lidar's two faces by a stated rule (on a made-up piece, then on the data);
the correction is idempotent; the scene step's pure parts give, from the record, exactly the islands the committed blend
holds (the counts the scratch run found in the scene) and the islands that replace them; no plant the lidar saw is
dropped; the wiring. The scene work is self-checked in Blender and measured through the chain's own steps on a scratch
workshop. Plain ``test_*`` for tests/run_tests.py."""
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

def _tab(rows):
    return {FIX.key(s): {"s": s, "verdict": v, "left_m": lf, "right_m": rt, "reason": "made up"} for s, v, lf, rt in rows}


def _piece_rows():
    pc = next(p for p in DOC["pieces"] if p["id"] == "C")
    cols = pc["columns"]
    it, iw, io = cols.index("median_type"), cols.index("median_w_m"), cols.index("median_off_m")
    return {FIX.key(r[0]): (r[it], float(r[iw]), float(r[io])) for r in pc["stations"]}


def _declared_of(rows):
    rec_rows = {FIX.key(r["s"]): r for r in REC["rows"]}

    def declared_of(s):
        d = rec_rows.get(FIX.key(s))
        return (d["median_type"][0], float(d["median_w_m"][0]), float(d["median_off_m"][0])) if d else rows[FIX.key(s)]
    return declared_of


def test_a_row_takes_the_lidars_two_faces_by_this_rule():
    """FIX.measure on a made-up piece, s 0-100, whose plan is one island 4 m wide on the line. The lidar covers s 10-90:
    an island 2 m wide to s 37.5, no median s 40-47.5, an island 1.5 m wide from s 50 with its right face 0.5 m in"""
    S = [2.5 * k for k in range(41)]
    rows = []
    for k in range(4, 37):
        st = 2.5 * k
        if 40.0 <= st <= 47.5:
            rows.append((st, "none", None, None))
        elif st == 30.0:
            rows.append((st, "island", 2.0, -1.0))          # one station's left face a metre out
        elif st == 37.5:
            rows.append((st, "unclear", None, None))        # a nose the lidar could not read
        elif st == 60.0:
            rows.append((st, "unclear", 0.9, -0.2))         # an unclear station inside an island, with faces of its own
        else:
            rows.append((st, "island", 1.0, -1.0 + (0.5 if st >= 50 else 0.0)))
    keep = FIX.DECLARED, FIX.HOLD_BEFORE_S
    FIX.DECLARED, FIX.HOLD_BEFORE_S = {"MD11": (0.0, 100.0)}, None
    try:
        got = FIX.measure(S, _tab(rows), lambda st: ("terracotta", 4.0, 0.0))
        FIX.HOLD_BEFORE_S = 20.0
        held = FIX.measure(S, _tab(rows), lambda st: ("terracotta", 4.0, 0.0))
    finally:
        FIX.DECLARED, FIX.HOLD_BEFORE_S = keep
    R = got["rows"]
    assert got["segments"] == [[10.0, 90.0]] and sorted(R) == [2.5 * k for k in range(4, 37)]
    assert got["runs"] == [(0.0, 37.5), (50.0, 100.0)]                  # the unclear nose is the island's last station
    assert R[35.0] == ("terracotta", 2.0, 0.0)
    assert R[30.0] == ("terracotta", 2.0, 0.0)                          # the median of three: one station's face does not kink the curb
    assert R[37.5] == ("terracotta", 2.0, 0.0)                          # the nose takes the clear station beside it
    assert R[60.0] == ("terracotta", 1.5, 0.25)                         # drawn straight between its clear neighbours, not its own reading
    assert R[55.0] == ("terracotta", 1.5, 0.25)
    assert [R[st] for st in (40.0, 42.5, 45.0, 47.5)] == [("none", 0.0, 0.05), ("none", 0.0, 0.1), ("none", 0.0, 0.15), ("none", 0.0, 0.2)]
    # where the coverage ends inside an island the faces go back to the plan's over BLEND_M
    assert FIX.BLEND_M == 20.0 and R[10.0] == ("terracotta", 4.0, 0.0) and R[90.0] == ("terracotta", 4.0, 0.0)
    assert R[20.0] == ("terracotta", 3.0, 0.0) and R[80.0][1] == 2.75 and abs(R[80.0][2] - 0.125) <= 0.0051
    assert got["blended"] == [10.0 + 2.5 * k for k in range(8)] + [72.5 + 2.5 * k for k in range(8)]
    assert [(u["s"], u["taken"].split(":")[0]) for u in got["unclear"]] == [(37.5, "the nearest clear lidar"), (60.0, "the nearest clear lidar")]
    assert "the island's end" in got["unclear"][0]["taken"] and "between s 57.5 and s 62.5" in got["unclear"][1]["taken"]
    # rows before HOLD_BEFORE_S keep the plan's values: the lidar's stations there are not read
    assert held["segments"] == [[20.0, 90.0]] and 17.5 not in held["rows"] and held["rows"][20.0] == ("terracotta", 4.0, 0.0)
    assert FIX.MEDIAN_OF == 3 and FIX.island_id(0) == "MD11" and [FIX.island_id(k) for k in (2, 3, 4)] == ["MD13", "MD13b", "MD13c"]


def test_the_islands_place_follows_each_50_m_bins_verdict():
    """FIX.measure with bins, on a made-up piece s 0-200 whose lidar island is 2 m wide on the line everywhere but a gap
    at s 100-110. Bins: the plan's edges true (s 0-47.5), off by -2 m (50-97.5), too few (100-147.5), off by -1 m (150 on)"""
    S = [2.5 * k for k in range(81)]
    tab = _tab([(st, "none" if 100.0 <= st <= 110.0 else "island", None if 100.0 <= st <= 110.0 else 1.0,
                 None if 100.0 <= st <= 110.0 else -1.0) for st in S])
    bins = [{"s": [0.0, 47.5], "kind": "true", "shift_m": 0.0}, {"s": [50.0, 97.5], "kind": "off", "shift_m": -2.0},
            {"s": [100.0, 147.5], "kind": "too_few", "shift_m": -1.5}, {"s": [150.0, 200.0], "kind": "off", "shift_m": -1.0}]
    keep = FIX.DECLARED, FIX.HOLD_BEFORE_S, FIX.TOO_FEW
    FIX.DECLARED, FIX.HOLD_BEFORE_S = {"MD11": (0.0, 200.0)}, None
    try:
        FIX.TOO_FEW = "between"
        got = FIX.measure(S, tab, lambda st: ("terracotta", 4.0, 0.3), bins)
        FIX.TOO_FEW = "declared"
        lit = FIX.measure(S, tab, lambda st: ("terracotta", 4.0, 0.3), bins)
        plain = FIX.measure(S, tab, lambda st: ("terracotta", 4.0, 0.3))
    finally:
        FIX.DECLARED, FIX.HOLD_BEFORE_S, FIX.TOO_FEW = keep
    R = got["rows"]
    assert got["runs"] == [(0.0, 97.5), (112.5, 200.0)] and not got["blended"]
    assert all(v[1] == 2.0 for v in R.values() if v[0] == "terracotta")            # the width is the lidar's, whatever the place
    assert R[20.0] == ("terracotta", 2.0, 0.0)                                     # edges true: the lidar's own place
    assert R[50.0] == ("terracotta", 2.0, 1.05)                                    # drawn straight from one bin's centre to the next
    assert R[75.0][2] == 2.0 and R[97.5] == ("terracotta", 2.0, 2.0)               # to its nose: nothing is drawn across the gap
    assert R[112.5] == ("terracotta", 2.0, 1.5) and R[122.5][2] == 1.5             # the too-few bin: between its called neighbours
    assert R[125.0][2] == 1.49 and R[175.0] == ("terracotta", 2.0, 1.0) == R[200.0]
    assert got["shift"][75.0] == -2.0 and got["shift"][20.0] == 0.0 and sorted(got["shift"]) == sorted(st for st in S if not 100.0 <= st <= 110.0)
    assert lit["rows"][112.5] == ("terracotta", 2.0, 0.3) and lit["rows"][125.0][2] == 0.32      # the first rule: the plan's own middle there
    assert lit["rows"][75.0] == R[75.0] and plain["rows"][75.0] == ("terracotta", 2.0, 0.0) and plain["shift"] == {}
    # the G10's bins as this script reads them: 41 of 50 m, a too-few bin's shift between its called neighbours
    rb = FIX.road_bins()
    assert FIX.TOO_FEW == "between" and len(rb) == 41 and rb[0]["s"] == [225.0, 247.5] and rb[-1]["s"] == [2200.0, 2245.0]
    assert {k: sum(1 for b in rb if b["kind"] == k) for k in ("true", "off", "too_few")} == {"true": 6, "off": 28, "too_few": 7}
    assert [b["s"][0] for b in rb if b["kind"] == "too_few"] == [400.0, 750.0, 850.0, 900.0, 1500.0, 1850.0, 2000.0]
    for i, b in enumerate(rb):
        if b["kind"] == "true":
            assert b["shift_m"] == 0.0 and abs(b["real_road_middle_minus_plan_m"]) <= 0.30
        elif b["kind"] == "off":
            assert b["shift_m"] == b["real_road_middle_minus_plan_m"]
        else:
            lo = next(rb[j] for j in range(i - 1, -1, -1) if rb[j]["kind"] != "too_few")
            hi = next(rb[j] for j in range(i + 1, len(rb)) if rb[j]["kind"] != "too_few")
            assert min(lo["shift_m"], hi["shift_m"]) - 1e-9 <= b["shift_m"] <= max(lo["shift_m"], hi["shift_m"]) + 1e-9, b
    assert REC["lidar"]["placement"]["bins"] == rb and REC["lidar"]["placement"]["too_few_rule"] == "between"
    tf = REC["lidar"]["placement"]["too_few_bins"]
    assert tf["bins_s"] == [b["s"] for b in rb if b["kind"] == "too_few"] and tf["rule"].startswith("[inferred: interpolated]")
    assert 1.0 < tf["against_the_declared_middle_m"]["max"] < 2.5                  # what the first rule would have swung the island by


def test_piece_cs_rows_are_the_lidars_faces_and_nothing_else():
    rows = _piece_rows()
    tab, files = FIX.lidar_table()
    got = FIX.measure(sorted(rows), tab, _declared_of(rows), FIX.road_bins())
    rec_rows = {FIX.key(r["s"]): r for r in REC["rows"]}
    assert sorted(rec_rows) == got["covered"] and len(got["covered"]) > 200
    for st in got["covered"]:
        assert rows[st] == got["rows"][st], st                                                   # the file holds what the rule gives
        assert tuple(rec_rows[st][k][1] for k in ("median_type", "median_w_m", "median_off_m")) == got["rows"][st], st
    assert REC["lidar"]["files"] == files and [f["file"] for f in files] == ["mg_median_faces.lidar.g10.json", "mg_median_faces_full.lidar.g10.json"]
    assert got["segments"] == [[45.0, 2245.0]] and not got["blended"]                           # the whole island is measured
    assert REC["lidar"]["covered_s"] == got["segments"] and REC["lidar"]["unclear"] == got["unclear"]
    assert (REC["lidar"]["median_of"], REC["lidar"]["blend_m"], REC["lidar"]["hold_before_s"]) == (3, 20.0, 45.0)
    # a clear island station with clear neighbours: the row's WIDTH is the lidar's own (each face the median of three), and
    # where no bin moves it (the J3 end, and a station an edges-true bin leaves alone) so are its two faces, to 0.01 m
    blended, cov, n = set(got["blended"]), set(got["covered"]), 0
    for st in got["covered"]:
        beside = [FIX.key(st + d) for d in (-2.5, 0.0, 2.5)]
        if st in blended or any(q not in cov or tab[q]["verdict"] != "island" for q in beside):
            continue
        trio = [tab[q] for q in beside]
        _ty, w, o = rows[st]
        lf, rt = (sorted(float(t[k]) for t in trio)[1] for k in ("left_m", "right_m"))
        assert abs(w - (lf - rt)) <= 0.0051, st
        if got["shift"].get(st, 0.0) == 0.0:
            assert abs(o + w / 2.0 - lf) <= 0.0101 and abs(o - w / 2.0 - rt) <= 0.0101, st
            n += 1
        else:
            assert abs(o + got["shift"][st] - (lf + rt) / 2.0) <= 0.0061, st                    # its middle: the lidar's less the bin's shift
    assert n > 60 and all(st >= 222.5 for st in got["shift"]) and len(got["shift"]) > 780
    # every station the lidar calls none is a row with no median, and every unclear one is accounted for
    for st in got["covered"]:
        if tab[st]["verdict"] == "none":
            assert rows[st][:2] == ("none", 0.0), st
    assert all(u["taken"].startswith("the nearest clear lidar") for u in got["unclear"]) and len(got["unclear"]) >= 13
    assert sorted(u["s"] for u in got["unclear"]) == sorted(st for st in got["covered"] if tab[st]["verdict"] == "unclear")
    # MD11 is held at its declared start: the lidar has an island before it (s 25-42.5), which is owed
    assert min(got["covered"]) == FIX.HOLD_BEFORE_S == 45.0
    assert all(tab[FIX.key(st)]["verdict"] in ("island", "unclear") for st in (25.0, 27.5, 30.0, 32.5, 35.0, 37.5, 40.0, 42.5))
    assert rows[40.0][:2] == ("none", 0.0)
    # the two strips beside the turn pockets are the lidar's 1.2-1.3 m, not the 1.96 / 1.84 m the photo fit built
    for a_, b_ in ((1012.5, 1077.5), (1127.5, 1190.0)):
        ws = sorted(rows[FIX.key(a_ + 2.5 * k)][1] for k in range(int((b_ - a_) / 2.5) + 1))
        assert 1.15 <= ws[len(ws) // 2] <= 1.40 and ws[-1] < 1.6, (a_, ws[len(ws) // 2], ws[-1])


def test_the_islands_are_the_runs_the_lidar_found():
    meds = DOC["medians"]
    ids = [m["id"] for m in meds]
    assert ids == [f"MD{k}" for k in range(1, 14)] + ["MD13b"] + [f"MD{k}" for k in range(14, 23)]   # no other id moved
    m11, m12, a, b = (next(m for m in meds if m["id"] == i) for i in ("MD11", "MD12", "MD13", "MD13b"))
    assert [(m["s_from"], m["s_to"]) for m in (m11, m12, a, b)] == [(45.0, 182.5), (195.0, 207.5), (222.5, 1085.0), (1115.0, 2245.0)]
    assert REC["lidar"]["islands"] == [{"id": m["id"], "s": [m["s_from"], m["s_to"]]} for m in (m11, m12, a, b)]
    assert REC["lidar"]["no_median_s"] == [[182.5, 195.0], [207.5, 222.5], [1085.0, 1115.0]]
    assert a["piece"] == b["piece"] == "C" and a["raised"] and b["raised"] and a["type"] == b["type"] == "terracotta"
    # one ring point a side per 2.5 m station
    assert [len(m["polygon_xz"]) for m in (m11, m12, a, b)] == [2 * 56, 2 * 6, 2 * 346, 2 * 453]
    assert REC["lidar"]["placement"]["bins_by_kind"] == {"true": 6, "off": 28, "too_few": 7}
    assert REC["rings_before"] == {"MD11": {"s_from": 45.0, "s_to": 167.5, "points": 100}, "MD12": {"s_from": 182.5, "s_to": 195.0, "points": 12},
                                   "MD13": {"s_from": 210.0, "s_to": 2245.0, "points": 1630}}
    for m in (m11, m12, a, b):
        c = m["correction"]
        assert c["ledger"] == "0099 round 3, items 1b and 2"
        assert c["lidar"]["no_median_s"] == REC["lidar"]["no_median_s"] and c["lidar"]["files"] == REC["lidar"]["files"]
        assert c["centre_paint_where_there_is_no_median"]["source"] == "photo"
        assert "owed" in c["not_built"] and "s 25" in c["not_built"]
        # the photo method's error is said plainly, where the data is
        err = c["the_photo_method_and_its_error"]
        assert "0.61 m narrower and 0.86 m right" in err and "+0.30 m of width and +0.49 m of middle" in err
    # the rings' new ends taper to the generator's blunt end (tools/author_expansion.py NOSE_W_M)
    import math
    for m, ends in ((m11, "end"), (a, "both"), (b, "start")):
        n = len(m["polygon_xz"]) // 2
        if ends in ("end", "both"):
            assert abs(math.dist(m["polygon_xz"][n - 1], m["polygon_xz"][n]) - FIX.NOSE_W_M) < 0.01, m["id"]
        if ends in ("start", "both"):
            assert abs(math.dist(m["polygon_xz"][0], m["polygon_xz"][-1]) - FIX.NOSE_W_M) < 0.01, m["id"]
    src = (ROOT / "tools" / "author_expansion.py").read_text(encoding="utf-8")
    assert "NOSE_M = 6.0 " in src and "NOSE_W_M = 0.6 " in src and (FIX.NOSE_M, FIX.NOSE_W_M) == (6.0, 0.6)
    readme = (MG / "README.md").read_text(encoding="utf-8")
    for frag in ("mg_median_faces.lidar.g10.json", "0.61 m narrower", "0.86 m", "owed", "s 182.5", "nearest clear lidar"):
        assert frag in readme, frag


def test_the_island_and_the_paint_are_decorates_and_the_gaps_carry_no_centre_line():
    w = ISLAND["island_w_by_point"]
    assert [(i, j - 1) for i, j in MI.segments(w)] == [(8, 53), (67, 354), (365, 741)]            # MD12's four points are no island
    assert REC["island"]["runs_of_points_with_an_island"] == [[8, 53], [58, 61], [67, 354], [365, 741]]
    assert REC["island"]["points_changed"] == len(REC["island"]["before"]) > 150
    ch = [k for a_, b_ in REC["island"]["points_changed_runs"] for k in range(a_, b_ + 1)]
    assert sorted(int(k) for k in REC["island"]["before"]) == ch
    assert all(1.0 <= w[k] <= 1.6 for k in list(range(331, 352)) + list(range(370, 389)))          # the two strips beside the pockets
    assert all(1.1 <= w[k] <= 3.7 for k in range(58, 62))                                          # MD12, up to 3.6 m wide
    assert REC["island"]["points_with_no_median_runs"] == [[54, 57], [63, 66], [356, 364]]
    gap = [k for a_, b_ in REC["island"]["points_with_no_median_runs"] for k in range(a_, b_ + 1)]
    assert len(gap) == 17 and all(w[k] == 0 for k in gap)
    lines = CONN["paint"]["lines"]
    assert len(lines) == REC["paint"]["lines"] == 14 and REC["paint"]["centre_line_offsets_cleared_where_there_is_no_median"] == 34
    for k in range(58, 62):                                          # MD12: the painted outline, its two edge lines, and no island
        assert len([ln for ln in lines if ln["color"] == "yellow" and not ln["dash"] and ln["off"][k] is not None]) == 2, k
    for k in gap:                                                    # no solid yellow line of any kind where there is no median
        assert not [ln for ln in lines if ln["color"] == "yellow" and not ln["dash"] and ln["off"][k] is not None], k
        assert sum(1 for ln in lines if ln["color"] == "white" and ln["off"][k] is not None) >= 4      # lanes and bike lines run on
    before = REC["paint"]["before"]
    assert set(int(k) for k in before) <= set(range(14)) and {3, 4, 6, 7, 8, 9} <= set(int(k) for k in before)
    near = set(q for k in ch + gap for q in range(k - 3, k + 4))
    assert all(int(i) in near for d in before.values() for i in d)                               # paint changes only where the island did


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
    assert new["runs"] == [[8, 53], [67, 354], [365, 741]]
    assert [len(v) for v, _f in new["curb"]] == [6 * 46, 6 * 288, 6 * 377] and [len(v) for v, _f in new["deck"]] == [2 * 46, 2 * 288, 2 * 377]
    assert len(new["beam"]) == 3 and 220 <= len(new["posts"]) <= 240          # each of the three is over the rule's 120 m
    # away from the points the correction changed, the one point each side whose direction they turn (a ring stands
    # across the line from its neighbours) and an island's own three-point nose, old and new are the same islands,
    # vertex for vertex
    ch = set(int(k) for k in REC["island"]["before"])
    same = 0
    for (o_first, o_last, o_parts), n_idx in (((8, 48, o11), 0), ((63, 741, o13), 1), ((63, 741, o13), 2)):
        n_first, n_last = new["runs"][n_idx]
        for k in range(max(o_first, n_first) + 4, min(o_last, n_last) - 3):
            if any(q in ch for q in range(k - 1, k + 2)):
                continue
            assert o_parts["curb"][0][0][6 * (k - o_first):6 * (k - o_first) + 6] == new["curb"][n_idx][0][6 * (k - n_first):6 * (k - n_first) + 6], k
            assert o_parts["deck"][0][0][2 * (k - o_first):2 * (k - o_first) + 2] == new["deck"][n_idx][0][2 * (k - n_first):2 * (k - n_first) + 2], k
            same += 1
    assert same > 0 or len(ch) > 700                    # (when the whole island is measured no point is left as it was)
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

def test_the_plants_on_pavement_are_dropped_and_no_plant_the_lidar_saw_is():
    sp = json.loads((MG / "mg_median.median_spots.json").read_text(encoding="utf-8"))
    spots = json.loads((LM / "data" / "scatter_positions.json").read_text(encoding="utf-8"))["median_planting"]
    lidar = json.loads((LM / "source" / "vegetation" / "median_heights.lidar.json").read_text(encoding="utf-8"))
    PL = _load("mg_plants_data_0099", MG / "mg_plants_data.py")
    assert sp["points_runs"] == REC["island"]["points_changed_runs"] and len(sp["drop"]) >= 21
    for d in sp["drop"]:
        s = spots[d["index"]]
        assert (s["x"], s["z"]) == (d["x"], d["z"])                                  # the spot's own place: make_treefx checks it too
        assert lidar["spots"][d["index"]][2] < lidar["min_h_m"] == 0.3                # no plant the lidar saw is dropped
        assert d["half_m"] == 0 or abs(d["lateral_m"]) > d["half_m"] - MI.DECK_INSET
        assert d["where"] in ("no median: between the two noses", "pavement beside the island", "the strip's curb ring")
    for k in sp["kept_on_the_new_deck"]:
        assert abs(k["lateral_m"]) <= k["deck_half_m"]
    # a spot the lidar saw a plant at, which the corrected deck no longer reaches, is MOVED onto it (the Mac 2026-11-23:
    # rule (3) the G10's lm-shrub top within 2 m, else rule (2) straight across onto the deck), never dropped
    P, W = ISLAND["points_xyz_m"], [float(x) for x in ISLAND["island_w_by_point"]]
    segs = MI.segments(W)
    mt = _load("make_treefx_mg_move", ROOT / "tools" / "make_treefx.py")
    import math
    for m in sp["move"]:
        s = spots[m["index"]]
        assert (s["x"], s["z"]) == (m["x"], m["z"]) and lidar["spots"][m["index"]][2] >= 0.3
        assert m["rule"].startswith("(2) ") or m["rule"].startswith("(3) ")
        assert ("[inferred position]" in m["rule"]) == m["rule"].startswith("(2) ")
        assert 0 < m["moved_m"] <= mt.MEDIAN_SPOT_MOVE_MAX_M and abs(m["moved_m"] - math.hypot(m["to_x"] - s["x"], m["to_z"] - s["z"])) < 0.011
        k = min(range(len(P)), key=lambda q: math.hypot(m["to_x"] - P[q][0], m["to_z"] - P[q][2]))
        seg = next((i0, j0) for i0, j0 in segs if i0 <= k < j0)                      # its new place is on an island
        tx, tz = MI.tangent(P, k)
        lat = (m["to_x"] - P[k][0]) * (-tz) + (m["to_z"] - P[k][2]) * tx
        assert abs(lat) <= MI.half_width(W, seg[0], seg[1], k) - MI.DECK_INSET - PL.TRUNK_R_M + 0.011, m     # and its trunk on the deck
    assert (PL.TRUNK_R_M, PL.TOP_WITHIN_M, PL.TALL_M) == (0.3, 2.0, 10.0)
    # rule (3) rests on the tops the Mac read off the G10's lm_shrub.tops.npz; a top is carried across by the shift its
    # island was given, and the spot keeps its own lidar height (median_heights.lidar.json stays the one source)
    tops = {t["spot"]: t for t in json.loads((MG / "mg_plant_tops.g10.json").read_text(encoding="utf-8"))["spots"]}
    assert sorted(tops) == sorted(m["index"] for m in sp["move"]) and sp["tops_file"] == "mg_plant_tops.g10.json"
    for m in sp["move"]:
        near = tops[m["index"]]["nearest_plant_top"]
        assert m["lidar_h_m"] == lidar["spots"][m["index"]][2]
        if m["rule"].startswith("(3) "):
            assert m["top"]["index"] == near["top"] and m["top"]["on_the_deck"] and m["top"]["from_the_spot_m"] <= 2.0
            assert abs(math.hypot(m["to_x"] - near["x"], m["to_z"] - near["z"]) - abs(m["top"]["carried_across_m"])) < 0.011
        else:
            assert near is None or (m["top"]["index"] == near["top"] and not m["top"]["on_the_deck"])
    assert sorted(m["rule"][:3] for m in sp["move"]) == ["(2)", "(2)", "(2)", "(3)", "(3)", "(3)"]
    shifts = REC["lidar"]["placement"]["shift_m_by_station"]
    assert len(shifts) == REC["lidar"]["placement"]["stations_placed_by_a_bin"] and shifts[0][0] == 222.5 and shifts[-1][0] == 2245.0
    assert sp["tall_plants_moved"] == [{"index": m["index"], "lidar_h_m": m["lidar_h_m"], "rule": m["rule"], "moved_m": m["moved_m"]}
                                       for m in sp["move"] if m["lidar_h_m"] >= 10.0]
    assert "plant_off_the_deck" not in sp
    lists = [{d["index"] for d in sp[k]} for k in ("drop", "kept_on_the_new_deck", "move")]
    assert not (lists[0] & lists[1] or lists[0] & lists[2] or lists[1] & lists[2])
    src = (MG / "mg_plants_data.py").read_text(encoding="utf-8")
    assert "the gap is wrong, not the plant" in src                                    # a plant where there is no island at all stays fatal
    college = json.loads((LM / "source" / "college_r2" / "college_plants.median_spots.json").read_text(encoding="utf-8"))
    assert not {d["index"] for d in sp["drop"] + sp["move"]} & {d["index"] for d in college["drop"] + college["foot_y"]}
    ms = CFG["scenery"]["treefx"]["median_spots"]
    assert ms["file"] == "source/college_r2/college_plants.median_spots.json"
    assert ms["files"] == ["source/expansion/mg_median/mg_median.median_spots.json"]


def test_make_treefx_reads_every_list_it_is_given():
    mt = _load("make_treefx_mg", ROOT / "tools" / "make_treefx.py")
    src = (ROOT / "tools" / "make_treefx.py").read_text(encoding="utf-8")
    for frag in ('for ms_name_ in ([ms_cfg["file"]] if ms_cfg.get("file") else []) + list(ms_cfg.get("files") or []):',
                 "ms_lists_[kind_] += list(ms_one_.get(kind_) or [])", '"move": list(ms_cfg.get("move") or [])'):
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
    assert paved == [(LINE, [8, 53]), (LINE, [67, 354]), (LINE, [365, 741])]             # the islands the rebuild leaves
    for p in sorted((ROOT / "tracks").glob("*/track.config.json")):
        if p.parent != LM:
            assert "median_rebuild" not in (json.loads(p.read_text(encoding="utf-8")).get("route") or {}), p
    for p in sorted((ROOT / "tracks").glob("*/ship.json")):
        if p.parent != LM:
            assert "median_rebuild" not in (json.loads(p.read_text(encoding="utf-8")).get("steps", {}).get("author") or []), p
