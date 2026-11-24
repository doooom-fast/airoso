"""Ledger 0099 round 3, item 4 (Lake Murray 0.20.8): Jackson Dr north's painted median from the lidar and the photo
(tracks/san-diego-lake-murray/source/expansion/jackson_paint/fix_jackson_median.py), and decorate's opt-in measured
edge lines (tools/expansion_pieces.py EDGE_COLS / Piece.num_opt).

Pure python. Plain ``test_*`` for tests/run_tests.py."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LM = ROOT / "tracks" / "san-diego-lake-murray"
JP = LM / "source" / "expansion" / "jackson_paint"
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
import expansion_pieces as ep  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FIX = _load("fix_jackson_median_0099", JP / "fix_jackson_median.py")
REC = json.loads((JP / "jackson_median_correction.json").read_text(encoding="utf-8"))


def test_no_other_piece_or_connector_changes():
    """the Mac's firm condition: piece D's record alone changes; every other piece's record, the file's own head and every
    other connector are byte for byte as committed (their records hold later corrections decorate does not make)"""
    ep_doc = json.loads((LM / "data" / "expansion.north.json").read_text(encoding="utf-8"))
    cdoc = json.loads((LM / "data" / "connectors.local.json").read_text(encoding="utf-8"))
    now = FIX.others_sha256(ep_doc, cdoc)
    assert now == REC["others_sha256"], {k: (now[k], REC["others_sha256"][k]) for k in now if now[k] != REC["others_sha256"][k]}
    assert sorted(now["pieces"]) == ["A", "B", "C"] and len(now["connectors"]) == len(cdoc["connectors"]) - 1
    # the writer round-trips the file, so nothing but piece D's bytes can move
    text = (LM / "data" / "expansion.north.json").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert json.dumps(json.loads(text), indent=1, ensure_ascii=False) + "\n" == text


def test_piece_d_holds_the_correction_as_recorded():
    doc, pieces = ep.load(LM / "data" / "expansion.north.json")
    D = pieces["D"]
    rows = {round(float(r["s"]), 2): r for r in D.rows}
    assert len(REC["rows"]) == 115
    for c in REC["rows"]:
        r = rows[round(float(c["s"]), 2)]
        for k, v in c["after"].items():
            assert r[k] == v, (c["s"], k, r[k], v)
    band = [c for c in REC["rows"] if c["after"]["median_type"] == "hatched"]
    line = [c for c in REC["rows"] if c["after"]["median_type"] == "line"]
    assert len(band) == 90 and len(line) == 25
    assert min(c["s"] for c in band) == 270.0 and max(c["s"] for c in band) == 492.5
    assert min(c["s"] for c in line) == 1240.0 and max(c["s"] for c in line) == 1300.0
    assert all(c["after"]["median_src"].startswith("0099 r3 item 4: ") for c in REC["rows"])
    assert all(c["after"]["median_w_m"] == 0.0 for c in line)
    # s 225-267.5 held as they were, owed with J4, with the continuity the Mac read
    assert not [c for c in REC["rows"] if 225.0 <= c["s"] <= 267.5]
    assert REC["held"]["from"] == 225.0 and REC["held"]["to"] == 267.5 and "14 of 16" in REC["held"]["why"]
    # the rows under a lane are written as measured and listed, not narrowed
    assert [r["s"] for r in REC["short_rows"]] == [337.5, 352.5, 397.5, 455.0, 457.5]
    assert all(min(r["room_fwd_rev_m"]) < ep.LANE_MIN_M for r in REC["short_rows"])
    for c in band:
        if c["s"] not in {r["s"] for r in REC["short_rows"]}:
            assert min(c["room_fwd_rev_m"]) >= ep.LANE_MIN_M, c["s"]
    # every band edge carried by its own face's curb shift; the photo's edges flagged at +-1 m
    assert all("carried by each face's curb shift" in c["after"]["median_src"] for c in band)
    assert sum("photo line aligned to lidar, +-1 m" in c["after"]["median_src"] for c in band) > 0
    assert REC["photo_minus_lidar"]["median_m"] == -0.61


def test_the_reverse_edge_is_the_innermost_solid_line():
    c = next(c for c in REC["rows"] if c["s"] == 292.5)
    assert c["unexplained_weak_lines_rev"] == [[3.71, 0.58]]                                  # recorded, never taken
    assert c["edge_cols"]["edge_rev_m"] is not None and c["room_fwd_rev_m"][1] > 6.0      # the solid +8.01, not the weak +3.71
    assert FIX.SOLID_MIN == 0.75 and FIX.REV_FROM_BAND_M == 2.5


class _Pc:
    """a straight piece D: curbs at +8 / -10, a hatched median 6 m wide at -1 (just enough of Piece for layout)"""
    id = "D"

    def __init__(self, cols):
        self.cols = cols

    def curbs(self, s):
        return 8.0, -10.0

    def near(self, s, key):
        return {"median_type": "hatched"}[key]

    def num(self, s, key):
        return {"median_w_m": 6.0, "median_off_m": -1.0}[key]

    def num_opt(self, s, key):
        return self.cols.get(key)


def _lines(pc):
    return {k: off for k, off, _c, _d in ep.layout(pc, 100.0, [])}


def test_decorate_takes_measured_edge_lines_and_keeps_its_default_without_them():
    base = _lines(_Pc({}))
    assert abs(base["bike_R"] - (-10.0 + ep.BIKE_LINE_M)) < 1e-9 and abs(base["buf_R"] - (-10.0 + ep.BIKE_LINE_M + ep.BUFFER_M)) < 1e-9
    assert abs(base["bike_L"] - (8.0 - ep.BIKE_LINE_M)) < 1e-9 and abs(base["buf_L"] - (8.0 - ep.BIKE_LINE_M - ep.BUFFER_M)) < 1e-9
    assert (ep.BIKE_LINE_M, ep.BUFFER_M) == (1.80, 0.90)
    one = _lines(_Pc({"edge_fwd_m": 2.3}))                 # one line on the forward side, at 2.3 m from its curb
    assert "bike_R" not in one and abs(one["buf_R"] - (-10.0 + 2.3)) < 1e-9
    assert abs(one["buf_L"] - base["buf_L"]) < 1e-12 and "bike_L" in one          # the other side keeps the default
    two = _lines(_Pc({"edge_rev_m": 3.0, "outer_rev_m": 1.5}))
    assert abs(two["bike_L"] - (8.0 - 1.5)) < 1e-9 and abs(two["buf_L"] - (8.0 - 3.0)) < 1e-9
    assert ep.EDGE_COLS == {-1: ("edge_fwd_m", "outer_fwd_m"), 1: ("edge_rev_m", "outer_rev_m")}


def test_num_opt_is_none_where_the_column_or_a_neighbour_is():
    rec = {"id": "Z", "columns": ["s", "x", "z", "edge_fwd_m"],
           "stations": [[0.0, 0.0, 0.0, 2.0], [2.5, 0.0, 2.5, 3.0], [5.0, 0.0, 5.0, None]]}
    pc = ep.Piece(rec)
    assert abs(pc.num_opt(1.25, "edge_fwd_m") - 2.5) < 1e-12
    assert pc.num_opt(3.75, "edge_fwd_m") is None                  # a neighbour holds none: the default applies there
    assert pc.num_opt(1.25, "outer_fwd_m") is None                 # no such column


# --- the paint-only scene step (tools/author_median_rebuild_blend.py --paint-only) --------------------------------------
RB = _load("author_median_rebuild_paint_0099", ROOT / "tools" / "author_median_rebuild_blend.py")


def test_the_paint_only_key_is_opt_in_and_checked():
    assert RB.paint_spec({}) is None and RB.paint_spec({"route": {}}) is None
    assert RB.paint_spec({"route": {"paint_rebuild": {"line": "L#0", "record": "r.json", "_doc": "x"}}}) == {"line": "L#0", "record": "r.json"}
    for bad in ({"line": "L#0"}, {"record": "r.json"}, {"line": "", "record": "r.json"}):
        try:
            RB.paint_spec({"route": {"paint_rebuild": bad}})
        except SystemExit:
            pass
        else:
            raise AssertionError(bad)


def test_the_strips_taken_out_and_laid_are_the_difference_and_a_shared_strip_stays():
    a = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 1.0, 0.0)]
    b = [(5.0, 0.0, 0.0), (6.0, 0.0, 0.0), (5.0, 1.0, 0.0), (6.0, 1.0, 0.0)]
    c = [(9.0, 0.0, 0.0), (9.5, 0.0, 0.0), (9.0, 1.0, 0.0), (9.5, 1.0, 0.0)]
    near_a = [(x + 2e-5, y, z) for x, y, z in a]                       # the same strip to the key's 0.1 mm
    out, inn = RB.paint_change({"MARKINGS": [a, b], "YLINE": []}, {"MARKINGS": [near_a, c], "YLINE": [b]})
    assert out == {"MARKINGS": [b], "YLINE": []} and inn == {"MARKINGS": [c], "YLINE": [b]}
    s1 = RB.paint_signature("L#0", {"MARKINGS": [a, c], "YLINE": []})
    assert s1 == RB.paint_signature("L#0", {"MARKINGS": [c, a], "YLINE": []}) and len(s1) == 16      # order does not matter
    assert s1 != RB.paint_signature("L#0", {"MARKINGS": [a], "YLINE": []}) and s1 != RB.paint_signature("M#0", {"MARKINGS": [a, c], "YLINE": []})


def test_lake_murray_names_jacksons_paint_and_the_chain_runs_it():
    cfg = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))
    pp = RB.paint_spec(cfg)
    assert pp == {"line": "north_J5_jackson_north#0", "record": "source/expansion/jackson_paint/jackson_median_correction.json"}
    assert RB.spec(cfg)["line"] == "north_mission_gorge"                # the island path's key is as it was
    assert cfg["version"] == "0.20.8"
    conns = json.loads((LM / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    conn = next(c for c in conns if c["name"] == pp["line"])
    before = REC["paint_before"]
    assert before["lines"] and "strokes" in before and before != conn["paint"]       # the step has something to change
    assert len(before["strokes"]) == 8 and len(conn["paint"]["strokes"]) == 51
    ship = json.loads((LM / "ship.json").read_text(encoding="utf-8"))
    assert pp["record"] in ship["sync_in"]["optional"] or pp["record"] in json.dumps(ship["sync_in"])
    assert "data/paint_rebuild.json" in ship["sync_out"]["files"]
    sh = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")
    body = sh.split("author_median_rebuild() {")[1].split("\n}\n")[0]
    i_island = body.index('author_median_rebuild_blend.py" -- "$PROJ" --v021')
    i_paint = body.index('author_median_rebuild_blend.py" -- "$PROJ" --paint-only --v021')
    assert i_island < i_paint                                          # the paint pass after the island path, in the same step
    ps = (LM / "source" / "college_r2" / "scratch" / "run_full.ps1").read_text(encoding="utf-8")
    assert '"--paint-only"' in ps and ps.index('Step "median_rebuild"') < ps.index('"--paint-only"')
