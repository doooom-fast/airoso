"""v0.18.1 — named streetlight relocations (tools/streetlight_relocate.py, the pure half of author_lamps_blend's
RELOCATIONS): an entry moves exactly the post it names, to the base it gives, under the author's own arm rule."""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("streetlight_relocate", ROOT / "tools" / "streetlight_relocate.py")
SR = importlib.util.module_from_spec(spec)
sys.modules["streetlight_relocate"] = SR
spec.loader.exec_module(SR)

ARM = 1.8
CL = [(float(x), 0.0, 0.0) for x in range(-300, 301)]          # a straight road along +x


def nearest_cl(x, z):
    return min(CL, key=lambda p: (p[0] - x) ** 2 + (p[2] - z) ** 2)


def _raises(match, fn, *a):
    try:
        fn(*a)
    except ValueError as e:
        assert match in str(e), str(e)
        return
    raise AssertionError(f"no ValueError matching {match!r}")


def _cfg(*ents):
    return {"scenery": {"streetlights": {"relocate": list(ents)}}}


def _ent(frm, to, seat="ground", name="t"):
    return {"name": name, "from_base_xz": list(frm), "to_base_xz": list(to), "seat": seat, "why": "test"}


HEADS = [[0.0, 9.0, 8.2], [55.0, 9.0, -8.2], [110.0, 9.0, 8.2]]   # bases at z = +-10 (head 1.8 m road-ward)


def test_base_of_matches_the_author_rule():
    assert all(abs(a - b) < 1e-9 for a, b in zip(SR.base_of(HEADS[0], nearest_cl, ARM), (0.0, 10.0)))
    assert all(abs(a - b) < 1e-9 for a, b in zip(SR.base_of(HEADS[1], nearest_cl, ARM), (55.0, -10.0)))


def test_plan_moves_exactly_the_named_post_and_round_trips():
    rows = SR.plan(HEADS, nearest_cl, SR.entries(_cfg(_ent((55.0, -10.0), (57.0, -11.5)))), ARM, 1.0, 15.0)
    assert len(rows) == 1 and rows[0]["lamp"] == 1
    hx, hz = rows[0]["head_xz"]
    b = SR.base_of((hx, 9.0, hz), nearest_cl, ARM)
    assert math.dist(b, (57.0, -11.5)) < 1e-6                         # the author stands the post where asked
    assert abs(rows[0]["move_m"] - math.dist((55.0, -10.0), (57.0, -11.5))) < 1e-3


def test_plan_refuses_a_missing_post_a_double_entry_and_a_long_move():
    _raises("0 posts", SR.plan, HEADS, nearest_cl, SR.entries(_cfg(_ent((30.0, 10.0), (31.0, 10.0)))), ARM, 1.0, 15.0)
    _raises("already moved", SR.plan, HEADS, nearest_cl, SR.entries(_cfg(_ent((0.0, 10.0), (1.0, 11.0), name="a"),
                                                                          _ent((0.2, 10.1), (2.0, 11.0), name="b"))),
            ARM, 1.0, 15.0)
    _raises("new lamp", SR.plan, HEADS, nearest_cl, SR.entries(_cfg(_ent((0.0, 10.0), (30.0, 10.0)))), ARM, 1.0, 15.0)


def test_entries_validate_shape_seat_and_why():
    assert SR.entries({}) == []
    _raises("to_base_xz", SR.entries, _cfg({"name": "x", "from_base_xz": [0, 0], "to_base_xz": [1], "why": "w"}))
    _raises("seat", SR.entries, _cfg(_ent((0, 0), (1, 1), seat="float")))
    _raises("why", SR.entries, _cfg({"name": "x", "from_base_xz": [0, 0], "to_base_xz": [1, 1]}))


def test_lake_murray_relocations_are_well_formed():
    cfg = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json").read_text(encoding="utf-8"))
    ents = SR.entries(cfg)
    assert all(math.dist(e["from"], e["to"]) <= 15.0 for e in ents)
    assert len({e["from"] for e in ents}) == len(ents)


# --- ledger 0054 P4 step 2: the seat rule and the one-light-per-lamp spacing (pure halves of reseat_and_check) ---
def test_needs_reseat_measures_the_pole_base_not_the_footing():
    # the base 0.14 m under the walk it stands in (the design seat): no; 1.41 m under (lamps 113 / 143 of v0.19.0): yes;
    # 1.01 m over a released slope (lamp 32): yes; 0.91 over (lamp 34): no; no ground at all: yes
    assert not SR.needs_reseat(88.0, 87.856, 1.0)
    assert SR.needs_reseat(88.887, 87.474, 1.0)
    assert SR.needs_reseat(0.669, 1.683, 1.0)
    assert not SR.needs_reseat(-0.346, 0.568, 1.0)
    assert SR.needs_reseat(None, 5.0, 1.0)
    assert abs(SR.reseat_head_y(88.887, 8.8) - 97.687) < 1e-9


def test_heads_too_close_finds_every_pair_under_the_cluster_link():
    heads = [[0.0, 9.0, 0.0], [1.5, 9.0, 0.0], [60.0, 9.0, 0.0], [60.0, 9.0, 1.9], [120.0, 9.0, 0.0], [122.5, 9.0, 0.0]]
    pairs = SR.heads_too_close(heads, 2.0)
    assert [(i, j) for i, j, _d in pairs] == [(0, 1), (2, 3)]
    assert SR.heads_too_close([[0.0, 9.0, 0.0], [25.0, 9.0, 0.0]], 2.0) == []
    assert SR.heads_too_close([], 2.0) == []
