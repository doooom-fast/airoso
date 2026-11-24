"""tools/author_expansion.py — the readable intermediate of the Lake Murray north network (ledger 0054 P1).

The committed data/expansion.north.json is reproducible offline from its inputs (routes.json `north`, the aerial
eye readings, the loop centreline, the cached 3DEP samples) and holds what EXPANSION-PLAN P1 asks of it:
  * four pieces, each centreline within 1.5 m (p95) of the raw OSM midline (V1), the 11 % cap binding nowhere,
    Princess View's 10.2-10.4 % and the Mission Gorge crest (114.3 +- 1 m at s ~1460) reproduced from 3DEP;
  * the five junction heights within 0.5 m of revise/measure.json, the three pads within 1 m of V2's;
  * the two weld openings within V3's vertex extents (J1 v1512-1532 running past box end v1521, J5 v2311-2323
    inside box 2311-2328), the weld stubs' swept edges within 0.5 m of their authored curbs; J1's rehearsed stub
    with Waring's straight curbs (opening v1514-v1520.4) and the R 30 return's area as apron AP1 (P3);
  * the medians per A2 as the aerial measured them (repair round 2): Princess View's two raised islands, Jackson's J4
    approach island, the rest flush paint (hatched into J4);
  * every aerial width station built at its eye reading.
Plain ``test_*`` for tests/run_tests.py (the offline build takes ~5 s).
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRACK = ROOT / "tracks" / "san-diego-lake-murray"


def _tool():
    spec = importlib.util.spec_from_file_location("_tool_author_expansion", ROOT / "tools" / "author_expansion.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_DOC = {}


def _doc():
    if "d" not in _DOC:
        _DOC["d"] = json.loads((TRACK / "data" / "expansion.north.json").read_text(encoding="utf-8"))
    return _DOC["d"]


def test_the_committed_intermediate_is_reproduced_offline_byte_for_byte_but_the_stamp():
    mod = _tool()
    fresh = mod.build(TRACK, offline=True)
    want = dict(_doc())
    fresh.pop("written_utc")
    want.pop("written_utc")
    fresh = json.loads(json.dumps(fresh))
    # ledger 0054 Phase 2 step 2c: Princess View's MD7 was corrected at the source from NAIP by
    # source/expansion/phase2/fix_pv_median.py, which records every row it changed ([before, after]). The author builds
    # exactly the BEFORE values; the committed file holds the AFTER values and the corrected MD7 (polygon, width, record).
    md7 = next(m for m in want["medians"] if m["id"] == "MD7")
    rows = {float(r["s"]): r for r in md7.get("correction", {}).get("rows", [])}
    if rows:
        wp, fp = (next(p for p in d["pieces"] if p["id"] == "B") for d in (want, fresh))
        cols = wp["columns"]
        iw, io = cols.index("median_w_m"), cols.index("median_off_m")
        for wr, fr in zip(wp["stations"], fp["stations"]):
            ch = rows.get(float(wr[0]))
            if ch is None:
                continue
            assert (fr[iw], fr[io]) == (ch["median_w_m"][0], ch["median_off_m"][0]), (wr[0], fr[iw], fr[io], ch)
            assert (wr[iw], wr[io]) == (ch["median_w_m"][1], ch["median_off_m"][1]), (wr[0], wr[iw], wr[io], ch)
            fr[iw], fr[io] = wr[iw], wr[io]
        fmd = next(m for m in fresh["medians"] if m["id"] == "MD7")
        for k in ("polygon_xz", "width_m", "correction"):
            fmd.pop(k, None)
            md7_k = md7.pop(k)
            assert k == "correction" or md7_k
    # ledger 0099 round 3, items 1b and 2: Mission Gorge's median was corrected at the source by
    # source/expansion/mg_median/fix_mg_median.py, from the G10's lidar faces (no median across the Margerum Avenue /
    # Mission Vista Drive crossing, a narrow strip beside each turn pocket, the J3 end where it really is). Its record holds
    # every piece-C row it set ([before, after]: type, width, offset). The author builds exactly the BEFORE rows and ONE
    # island MD13; the committed file holds the AFTER rows, MD13 ending at its nose and a new MD13b from the other, whose
    # rings at the stations the lidar does not cover are the author's own.
    rec_p = TRACK / "source" / "expansion" / "mg_median" / "mg_median_correction.json"
    if rec_p.exists():
        rec = json.loads(rec_p.read_text(encoding="utf-8"))
        by = {float(r["s"]): r for r in rec["rows"]}
        wp, fp = (next(p for p in d["pieces"] if p["id"] == "C") for d in (want, fresh))
        cols = wp["columns"]
        it, iw, io = cols.index("median_type"), cols.index("median_w_m"), cols.index("median_off_m")
        seen = 0
        for wr, fr in zip(wp["stations"], fp["stations"]):
            ch = by.get(float(wr[0]))
            if ch is None:
                continue
            seen += 1
            assert (fr[it], fr[iw], fr[io]) == (ch["median_type"][0], ch["median_w_m"][0], ch["median_off_m"][0]), (wr[0], fr[it], fr[iw], fr[io], ch)
            assert (wr[it], wr[iw], wr[io]) == (ch["median_type"][1], ch["median_w_m"][1], ch["median_off_m"][1]), (wr[0], wr[it], wr[iw], wr[io], ch)
            fr[it], fr[iw], fr[io] = wr[it], wr[iw], wr[io]
        assert seen == len(by) > 200                                                    # every row the lidar covers
        assert not [m for m in fresh["medians"] if m["id"] == "MD13b"]
        stretches = rec["lidar"]["covered_s"]                                           # the stations the lidar covers
        own = {}                                                                        # the author's ring points, by station
        for mid, before in rec["rings_before"].items():
            f = next(m for m in fresh["medians"] if m["id"] == mid)
            assert {"s_from": f["s_from"], "s_to": f["s_to"], "points": len(f["polygon_xz"])} == before, mid
            n = len(f["polygon_xz"]) // 2
            for k in range(n):
                own[round(f["s_from"] + 2.5 * k, 1)] = (f["polygon_xz"][k], f["polygon_xz"][2 * n - 1 - k])
        kept = 0
        for mid in ("MD11", "MD12", "MD13", "MD13b"):
            m = next(x for x in want["medians"] if x["id"] == mid)
            nm = len(m["polygon_xz"]) // 2
            for j in range(nm):
                s = round(m["s_from"] + 2.5 * j, 1)
                if not any(lo <= s <= hi for lo, hi in stretches):
                    assert (m["polygon_xz"][j], m["polygon_xz"][2 * nm - 1 - j]) == own[s], (mid, s)
                    kept += 1
        assert kept > 0 or max(hi for _lo, hi in stretches) >= 2245.0                   # every ring station the lidar does not cover
        for mid in ("MD11", "MD12", "MD13"):
            i = next(k for k, m in enumerate(fresh["medians"]) if m["id"] == mid)
            fresh["medians"][i] = next(m for m in want["medians"] if m["id"] == mid)
        i13 = next(k for k, m in enumerate(fresh["medians"]) if m["id"] == "MD13")
        fresh["medians"].insert(i13 + 1, next(m for m in want["medians"] if m["id"] == "MD13b"))
    # ledger 0099 round 3, item 4 (Lake Murray 0.20.8): piece D's painted median and its measured edge lines are corrected at
    # the source (source/expansion/jackson_paint/fix_jackson_median.py); the author reproduces the rows as they were, the
    # record holds them before and after, and the four opt-in edge columns are the correction's (null on every other row)
    jrec_p = ROOT / "tracks" / "san-diego-lake-murray" / "source" / "expansion" / "jackson_paint" / "jackson_median_correction.json"
    if jrec_p.exists():
        jrec = json.loads(jrec_p.read_text(encoding="utf-8"))
        jby = {float(r["s"]): r for r in jrec["rows"]}
        wp, fp = (next(p for p in d["pieces"] if p["id"] == "D") for d in (want, fresh))
        extra = [c for c in wp["columns"] if c not in fp["columns"]]
        assert extra == ["edge_fwd_m", "outer_fwd_m", "edge_rev_m", "outer_rev_m"], extra
        fp["columns"] = fp["columns"] + extra
        for fr in fp["stations"]:
            fr.extend([None] * len(extra))
        cols = wp["columns"]
        seen = 0
        for wr, fr in zip(wp["stations"], fp["stations"]):
            ch = jby.get(float(wr[0]))
            if ch is None:
                assert wr == fr, wr[0]                                                  # a row the correction does not touch
                continue
            seen += 1
            for k, v in ch["before"].items():
                assert fr[cols.index(k)] == v, (wr[0], k, fr[cols.index(k)], v)
            for k, v in ch["after"].items():
                assert wr[cols.index(k)] == v, (wr[0], k, wr[cols.index(k)], v)
            fr[:] = list(wr)
        assert seen == len(jby) == 115
    assert fresh == want


def test_offline_refuses_to_fetch_a_missing_sample():
    mod = _tool()
    with tempfile.TemporaryDirectory() as t:
        tr = Path(t) / "track"
        for sub in ("data", "source/expansion"):
            (tr / sub).mkdir(parents=True)
        for f in ("centerline.local.json", "osm.expansion.json"):
            shutil.copy(TRACK / "data" / f, tr / "data" / f)
        for f in ("aerial__widths_eye.csv", "revise__measure.json", "aerial__paint_north.json"):
            shutil.copy(TRACK / "source" / "expansion" / f, tr / "source" / "expansion" / f)
        try:
            mod.build(tr, offline=True)
        except SystemExit as e:
            assert "--offline" in str(e)
        else:
            raise AssertionError("an empty sample cache built offline")


def test_pieces_follow_osm_and_3dep_and_the_cap_binds_nowhere():
    d = _doc()
    assert [p["id"] for p in d["pieces"]] == ["A", "B", "C", "D"]
    for pid, chk in d["checks"]["midline"].items():
        assert chk["pass"] and chk["p95_m"] <= 1.5, (pid, chk)
    for pid, g in d["checks"]["grade"].items():
        assert g["cap_binds"] is False and abs(g["max_grade_pct_3dep_20m"][0]) < 11.0, (pid, g)
    pv = d["checks"]["grade"]["B"]["max_grade_pct_3dep_20m"][0]
    assert -10.7 <= pv <= -9.7, pv                                          # dossier: 10.2 % down
    mg = d["checks"]["grade"]["C"]
    assert abs(mg["z_max"] - 114.3) <= 1.0 and abs(mg["s_at_max"] - 1460) <= 20, mg   # V2 crest
    for j, h in d["checks"]["junction_heights"].items():
        assert abs(h["diff_m"]) <= 0.5, (j, h)
    for pad, want in (("J2", 103.9), ("J3", 33.4), ("J4", 92.4)):
        p = next(x for x in d["pads"] if x["id"] == pad)
        assert abs(p["z_3dep_m"] - want) <= 1.0, (pad, p["z_3dep_m"])


def test_weld_openings_are_the_a5_extents_and_the_stubs_sweep_onto_their_curbs():
    d = _doc()
    w1 = next(w for w in d["welds"] if w["id"] == "W1")
    w5 = next(w for w in d["welds"] if w["id"] == "W5")
    o1, o5 = w1["opening"], w5["opening"]
    assert 1512 <= o1["vertex_from"] <= 1515 and 1525 <= o1["vertex_to"] <= 1532, o1        # V3: J1 v1512-1532
    assert o1["past_box_end"] >= 4, o1                                     # A5: ~25 m into race_cw's exit funnel
    assert 2311 <= o5["vertex_from"] and o5["vertex_to"] <= 2323, o5                         # V3: J5 v2311-2323
    assert 2311 <= o5["vertex_from"] and o5["vertex_to"] <= 2328                            # inside box 2311-2328
    assert abs(w1["centre_cross"]["vertex"] - 1517.4) <= 1.0 and abs(w5["centre_cross"]["vertex"] - 2317.7) <= 1.0
    assert w1["curbs"]["right"]["return"]["R"] == 30.0 and w5["curbs"]["left"]["return"]["R"] == 10.0
    # the rehearsed J1 stub keeps Waring's straight curbs (the 3-line ribbon cannot end on the corner across the R 30
    # return within the weld's 2 cm); the return's area is the apron P3 authors, the full flare is kept beside it
    r1 = w1["opening_ribbon"]
    assert abs(r1["vertex_from"] - o1["vertex_from"]) < 0.01 and 1519.5 <= r1["vertex_to"] <= 1521.5, r1
    (ap,) = w1["aprons"]
    assert ap["side"] == "right" and abs(ap["loop_edge_vertices"][0] - r1["vertex_to"]) < 0.01
    assert abs(ap["loop_edge_vertices"][1] - o1["vertex_to"]) < 0.01 and ap["area_m2"] > 50.0, ap
    assert w1["connector_full"]["swept_edge_error_max_m"] <= 0.5 and "connector_full" not in w5
    assert w5["aprons"] == [] and w5["opening_ribbon"]["vertex_to"] == o5["vertex_to"]
    for w in (w1, w5):
        c = w["connector"]
        assert c["swept_edge_error_m"]["max"] <= 0.5, (w["id"], c["swept_edge_error_m"])
        assert len(c["points_xyz_m"]) == len(c["widths_m"]) == len(c["part"])
        assert c["part"][:2] == ["inside", "inside"] and c["part"][-1] == "piece"
        assert c["u_out_m"][-1] >= 95.0


def test_pads_are_closed_outlines_with_the_measured_radii():
    d = _doc()
    radii = {p["id"]: sorted(c["R_m"] for c in p["corners"]) for p in d["pads"]}
    assert radii == {"J2": [7.0, 7.0, 7.0, 7.0], "J3": [5.5, 6.0, 6.0, 11.0], "J4": [6.0, 6.0, 9.0, 9.0]}, radii
    for p in d["pads"]:
        o = p["outline_xz"]
        area = 0.5 * sum(o[i][0] * o[(i + 1) % len(o)][1] - o[(i + 1) % len(o)][0] * o[i][1] for i in range(len(o)))
        assert abs(area) > 800.0, (p["id"], area)
        assert sorted(a["kind"] for a in p["arms"]) == ["route", "route", "stub", "stub"]
        for c in p["corners"]:
            assert min(c["tangents_from_node_m"]) > 0.0, (p["id"], c)
    assert [s["id"] for s in d["stubs"]] == ["S1", "S2", "S3", "S4", "S5", "S6"]


def test_medians_per_a2():
    d = _doc()
    by = {}
    for m in d["medians"]:
        by.setdefault(m["piece"], []).append(m)
    # repair round 2: the raised islands where the aerial shows them (MEASURED_ISLANDS), the rest flush paint
    raised_b = [(m["type"], m["s_from"], m["s_to"]) for m in by["B"] if m["raised"]]
    assert [t for t, *_ in raised_b] == ["nose", "planted"]
    assert 398 <= raised_b[0][1] and raised_b[0][2] <= 536 and 611 <= raised_b[1][1] and raised_b[1][2] <= 701
    assert all(m["type"] == "painted" for m in by["B"] if not m["raised"])
    raised_d = [m for m in by["D"] if m["raised"]]
    assert len(raised_d) == 1 and raised_d[0]["type"] == "nose" and raised_d[0]["s_to"] <= 119
    flush_d = [m for m in by["D"] if not m["raised"]]
    assert flush_d[0]["type"] == "hatched" and flush_d[0]["s_to"] <= 185
    assert all(m["type"] == "painted" for m in flush_d[1:])
    assert all(m["type"] == "planted" for m in by["A"]) and all(m["type"] == "terracotta" for m in by["C"])
    # the two openings near J3 stay open, where the lidar has them (ledger 0099 round 3, item 2: the plan stood them at
    # s 174 and s 202, about 13 m short; source/expansion/mg_median/fix_mg_median.py), and so does the crossing (item 1b)
    for m in by["C"]:
        for lo, hi in ((185.0, 192.5), (210.0, 220.0), (1087.5, 1112.5)):
            assert m["s_to"] < lo or m["s_from"] > hi, (m["id"], lo, hi)


def test_width_stations_are_built_at_their_eye_readings():
    d = _doc()
    st = d["width_stations"]
    assert [s["n"] for s in st] == list(range(1, len(st) + 1)) and len(st) == 38
    for s in st:
        assert abs(s["built_width_m"] - s["eye_width_m"]) <= 0.02, s
