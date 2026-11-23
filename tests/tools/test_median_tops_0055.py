"""Ledger 0055, the medians: every Lake Murray median showed the road's asphalt between its curbs (2,486 of 2,486
island rows on 0.20.3), because its grass top was part of TERRAIN and the prep pins every 1GRASS vertex under the
pavement it stands on. tools/author_median_tops_blend.py (author step median_tops, opt-in route.median_tops) moves each
top into its own object; the pure parts and the wiring are pinned here (the scene work is self-checked in Blender and
measured through the build's prep: source/college_r2/median_tops_r2_scratch.json).
Plain ``test_*`` for tests/run_tests.py."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LM = ROOT / "tracks" / "san-diego-lake-murray"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MT = _load("author_median_tops_0055", ROOT / "tools" / "author_median_tops_blend.py")
CFG = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))
SHIP = json.loads((LM / "ship.json").read_text(encoding="utf-8"))
SH = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")


def test_the_key_names_the_object_and_the_name_must_be_a_lawn_name():
    assert MT.spec({}) is None and MT.spec({"route": {}}) is None                    # not opted in: nothing to do
    assert MT.spec(CFG)["object"] == "1LAWN_median"      # + "paver" since 0.20.6: tests/tools/test_terracotta_median_0099.py
    assert MT.spec({"route": {"median_tops": {"object": "1LAWN_median"}}}) == {"object": "1LAWN_median"}
    for bad in ("1GRASS_median", "MEDIAN_TOP", "1KERB_median", ""):
        try:
            MT.spec({"route": {"median_tops": {"object": bad}}})
        except SystemExit:
            pass
        else:
            raise AssertionError(f"{bad!r} was taken: a 1GRASS name is pinned by the prep, any other has no material row")


def test_the_deck_half_width_is_the_median_tools_own_taper():
    """tools/author_median_blend.py: the last three rows of an island taper to a 0.25 m half width, the deck stands
    0.22 m inside the curb line and is never narrower than 0.05 m"""
    w, n = 5.0, 40
    assert abs(MT.deck_half(w, 10, n) - (2.5 - 0.22)) < 1e-9                         # mid island
    assert abs(MT.deck_half(w, 0, n) - 0.05) < 1e-9 and abs(MT.deck_half(w, n - 1, n) - 0.05) < 1e-9   # the end rows
    assert abs(MT.deck_half(w, 1, n) - (0.25 + (2.5 - 0.25) / 3 - 0.22)) < 1e-9
    assert abs(MT.deck_half(w, 2, n) - (0.25 + (2.5 - 0.25) * 2 / 3 - 0.22)) < 1e-9
    assert MT.deck_half(w, 3, n) == MT.deck_half(w, 10, n) and MT.deck_half(w, n - 3, n) == MT.deck_half(w, 2, n)
    src = (ROOT / "tools" / "median_island.py").read_text(encoding="utf-8")       # the rule, lifted out of the draft tool (0099 r3)
    for frag in ("half = NOSE_HALF + (half - NOSE_HALF) * si / NOSE_VERTS", "di = max(0.05, half - DECK_INSET)",
                 "return curb, [P(-di, CURB_H + 0.005), P(di, CURB_H + 0.005)]"):
        assert frag in src, frag                                                     # the rule this file copies
    assert (MT.NOSE_VERTS, MT.NOSE_HALF_M, MT.DECK_INSET_M, MT.DECK_OVER_M) == (3, 0.25, 0.22, 0.185)


def test_lake_murrays_islands_are_read_off_its_own_data():
    isl = MT.islands(LM)
    got = [(s["line"], s["first"], s["last"]) for s in isl]
    # College's island is two short ones since the split (ledger 0055 round 2): the bank between the two roads is ground
    assert ("MAINLINE", 846, 1073) in got and ("MAINLINE", 1096, 1116) in got and ("MAINLINE", 1476, 1487) in got
    # Mission Gorge's long island is two since ledger 0099 round 3, item 1b: no median across the Margerum Avenue /
    # Mission Vista Drive crossing (source/expansion/mg_median/)
    assert ("MAINLINE", 1540, 1739) in got and len(got) == 15
    assert ("north_mission_gorge", 68, 354) in got and ("north_mission_gorge", 367, 741) in got
    assert ("north_mission_gorge", 8, 51) in got                                  # MD11 on its real line, to its real end (item 2)
    # a run of the band under six rows is not an island: the median tool builds nothing for it (its _segments rule)
    # MD12, where the photo has it since item 2: four points, owed
    assert [(s["line"], s["first"], s["last"]) for s in MT.islands(LM, short=True)] == [("north_mission_gorge", 58, 61)]
    rule = (ROOT / "tools" / "median_island.py").read_text(encoding="utf-8")
    assert "if j - i >= MIN_ISLAND_VERTS:" in rule and "MIN_ISLAND_VERTS = 6" in rule and MT.MIN_ISLAND_ROWS == 6
    assert not any(line == "MAINLINE" and first <= 1300 <= last for line, first, last in got)
    for s in isl:
        assert len(s["rows"]) == s["last"] - s["first"] + 1 and all(r[4] > 0 for r in s["rows"])
        for (_x, _z, nx, nz, _w) in s["rows"]:
            assert abs(nx * nx + nz * nz - 1.0) < 1e-9


def test_median_tops_is_lake_murrays_alone_and_the_second_author_step():
    au = SHIP["steps"]["author"]
    # after College's islands and the one island item 1b re-authors (ledger 0099 round 3), before any reader
    assert au[:4] == ["college_split", "median_rebuild", "median_tops", "lamp_heads"]
    assert "author_median_tops() {" in SH and "tools/author_median_tops_blend.py" in SH
    assert "data/median_tops.json" in SHIP["sync_out"]["files"]
    assert CFG["lawn_as_grass"] is True and CFG["route"]["median_tops"]["object"] == "1LAWN_median"
    for p in sorted((ROOT / "tracks").glob("*/track.config.json")):
        if p.parent == LM:
            continue
        other = json.loads(p.read_text(encoding="utf-8"))
        assert "median_tops" not in (other.get("route") or {}) and not other.get("lawn_as_grass"), p
    for p in sorted((ROOT / "tracks").glob("*/ship.json")):
        if p.parent != LM:
            assert "median_tops" not in (json.loads(p.read_text(encoding="utf-8")).get("steps", {}).get("author") or []), p
