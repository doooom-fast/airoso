"""tools/median_island.py: the raised median island's shape as ONE rule (ledger 0099 round 3, item 1b).

The rule was lifted, line for line, out of tools/author_median_blend.py (the draft step) so that
tools/author_median_rebuild_blend.py (the author step that re-authors one island in a scene whose draft is never run
again) builds with the same code. Two things are held here, without Blender:
  * the draft tool's OUTPUT did not change: it is run against a stand-in bpy and what it hands to Blender (every mesh's
    vertices and faces, in order) is held to the checksums taken with the tool as it stood before the lift
    (2026-11-23, main 366a5a4c), on the 0.20.4 fixture and on the same fixture with a street-only span declared;
  * the rule itself, on small cases.
Plain ``test_*`` for tests/run_tests.py."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import runpy
import shutil
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures" / "lake_murray_v0204" / "data"
TOOL = ROOT / "tools" / "author_median_blend.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MI = _load("median_island_rule", ROOT / "tools" / "median_island.py")
# the draft tool's output before the lift (sha256 of json.dumps of [(mesh name, vertices, faces)] in the order made)
BEFORE_THE_LIFT = {
    "fixture": "a872da96d512b461a6e49d4be6d465e4bbc520341f916992b0e61479c0a3ae59",
    "fixture + a street-only span": "a3ec2944ad7a0f39ecb5f232583f7ac9f049444692eff0320dd3e41293d312db",
}
CHICANE_CFG = {"slug": "t", "layouts": [{"id": "street"}, {"id": "race_cw", "race_furniture": True},
                                        {"id": "race_acw", "race_furniture": True}],
               "race": {"chicanes": [{"name": "test_college", "out_leg": [900, 930], "back_leg": [990, 1020],
                                      "layouts": ["race_cw", "race_acw"], "street_only_island": True, "why": "test"}]}}


def _draft_output(proj: Path):
    """[(mesh name, vertices, faces)] the draft tool hands to Blender, captured with a stand-in bpy"""
    made = []

    class Mesh:
        def __init__(self, name):
            self.name, self.vertices = name, []

        def from_pydata(self, verts, _edges, faces):
            self.vertices = list(verts)
            made.append((self.name, [list(map(float, v)) for v in verts], [list(map(int, f)) for f in faces]))

        def validate(self):
            return False

    class Obj:
        def __init__(self, name, data=None):
            self.name, self.data = name, data or Mesh(name)

        def select_set(self, _v):
            pass

    class Objects:
        def new(self, name, me):
            return Obj(name, me)

        def get(self, name):
            return Obj(name) if name in ("CURB", "TERRAIN", "GUARDRAIL", "SCRUB") else None

        def remove(self, *_a, **_k):
            pass

        def link(self, _ob):
            pass

    ns = types.SimpleNamespace
    bpy = types.ModuleType("bpy")
    objects = Objects()
    bpy.data = ns(meshes=ns(new=lambda name: Mesh(name)), objects=objects)
    bpy.context = ns(scene=ns(collection=ns(objects=objects)), view_layer=ns(objects=ns(active=None)))
    bpy.ops = ns(wm=ns(open_mainfile=lambda **_k: None, save_mainfile=lambda **_k: None),
                 object=ns(select_all=lambda **_k: None, join=lambda **_k: None))
    had, argv = sys.modules.get("bpy"), sys.argv
    sys.modules["bpy"] = bpy
    sys.argv = ["blender", "--", str(proj)]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(TOOL), run_name="__main__")
    finally:
        sys.argv = argv
        if had is None:
            del sys.modules["bpy"]
        else:
            sys.modules["bpy"] = had
    return made


def _project(cfg=None):
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    for f in ("median_bands.json", "centerline.local.json"):
        shutil.copyfile(FIX / f, d / "data" / f)
    if cfg is not None:
        (d / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return d


def test_the_draft_tool_builds_exactly_what_it_built_before_the_lift():
    made = _draft_output(_project())
    assert {n: (len(v), len(f)) for n, v, f in made} == {"MEDIAN_CURB": (15000, 10000), "MEDIAN_DECK": (5000, 2487),
                                                         "MEDIAN_RAIL": (15792, 12604), "MEDIAN_SHRUB": (9320, 2330)}
    assert hashlib.sha256(json.dumps(made).encode("utf-8")).hexdigest() == BEFORE_THE_LIFT["fixture"]


def test_and_with_a_street_only_span_cutting_an_island():
    made = _draft_output(_project(CHICANE_CFG))
    sizes = {n: (len(v), len(f)) for n, v, f in made}
    assert sizes["1KERB_sidewalk_streetonly_median"] == (726, 480) and sizes["1WALL_guard_streetonly_median"] == (804, 640)
    assert hashlib.sha256(json.dumps(made).encode("utf-8")).hexdigest() == BEFORE_THE_LIFT["fixture + a street-only span"]


def test_the_draft_tool_takes_its_shape_from_the_rule_and_holds_no_copy():
    src = TOOL.read_text(encoding="utf-8")
    # the calls carry the OFFSET ISLAND keywords (tools/median_island.py; None on every island but an offset one)
    for frag in ('_MI = _load("_median_island_med", "tools/median_island.py")', "_MI.ring(pts, iw, i, j, k, off=ioff, ys=iys)",
                 "_MI.curb_span_faces(base + si * 6)", "_MI.beam_ring(pts, k, off=ioff, ys=iys)", "_MI.post_points(pts, bks)",
                 "half_here = _MI.half_width(iw, i, j, k)", "_segments = _MI.segments"):
        assert frag in src, frag
    for gone in ("NOSE_HALF + (half - NOSE_HALF)", "CURB_H = 0.18", "if j - i >= 6:", "0.45), (-0.12, 0.75)"):
        assert gone not in src, gone                                          # the numbers live in the rule alone


def test_a_run_shorter_than_six_points_is_no_island():
    assert MI.segments([0, 1, 1, 1, 1, 1, 0, 2, 2, 2, 2, 2, 2, 0]) == [(7, 13)]
    assert MI.segments([1.0] * 6) == [(0, 6)] and MI.segments([1.0] * 5) == [] and MI.MIN_ISLAND_VERTS == 6


def test_the_island_tapers_to_its_nose_over_three_points_at_each_end():
    iw = [5.0] * 40
    assert abs(MI.half_width(iw, 0, 40, 10) - 2.5) < 1e-12
    assert abs(MI.half_width(iw, 0, 40, 0) - 0.25) < 1e-12 and abs(MI.half_width(iw, 0, 40, 39) - 0.25) < 1e-12
    assert abs(MI.half_width(iw, 0, 40, 1) - (0.25 + 2.25 / 3)) < 1e-12 and abs(MI.half_width(iw, 0, 40, 38) - (0.25 + 2.25 / 3)) < 1e-12
    assert MI.half_width(iw, 0, 40, 3) == 2.5 and MI.half_width(iw, 0, 40, 36) == 2.5
    # a run that starts mid-list tapers from ITS first point
    assert abs(MI.half_width([0.0] * 10 + iw, 10, 50, 10) - 0.25) < 1e-12


def test_a_ring_is_the_curb_across_the_island_and_the_deck_inside_it():
    pts = [(0.0, 10.0, float(k)) for k in range(20)]                          # a line due north at y 10
    curb, deck = MI.ring(pts, [4.0] * 20, 0, 20, 10)
    # Blender frame (x, north, up); left of north is -x. Lbase LtopO LtopI RtopI RtopO Rbase
    xs, ups = [round(p[0], 6) for p in curb], [round(p[2], 6) for p in curb]
    assert xs == [2.0, 1.96, 1.85, -1.85, -1.96, -2.0]
    assert ups == [10.08, 10.28, 10.28, 10.28, 10.28, 10.08]                  # the base 0.02 under the ribbon, the top 0.18 over it
    assert all(abs(p[1] - 10.0) < 1e-12 for p in curb + deck)
    assert [round(p[0], 6) for p in deck] == [1.78, -1.78] and all(abs(p[2] - 10.285) < 1e-9 for p in deck)
    nose, nose_deck = MI.ring(pts, [4.0] * 20, 0, 20, 0)
    assert round(nose[0][0], 6) == 0.25 and round(nose_deck[0][0], 6) == 0.05  # the deck is never narrower than 0.05 a side
    assert MI.curb_span_faces(0) == [(0, 1, 7, 6), (1, 2, 8, 7), (3, 4, 10, 9), (4, 5, 11, 10)]
    assert MI.curb_start_cap(0) == [(0, 1, 2, 3), (0, 3, 4, 5)] and MI.curb_end_cap(6) == [(9, 8, 7, 6), (11, 10, 9, 6)]
    assert MI.deck_face(4) == (4, 5, 7, 6)


def test_the_beam_runs_between_the_noses_and_a_post_stands_every_eight_metres():
    pts = [(0.0, 0.0, 3.0 * k) for k in range(60)]                            # 3 m apart, 177 m: a barrier's island
    assert MI.seg_length(pts, 0, 60) == 177.0 and MI.BARRIER_MIN_M == 120.0
    bks = MI.beam_points(0, 60)
    assert bks == list(range(3, 57))
    assert len(MI.beam_ring(pts, 10)) == 4 and MI.beam_span_faces(0) == [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    posts = MI.post_points(pts, bks)
    assert posts[:3] == [5, 8, 11] and all(b - a == 3 for a, b in zip(posts, posts[1:]))   # 3 points = 9 m, the first step over 8
    verts, faces = MI.post(pts, 5)
    assert len(verts) == 8 and faces == [(0, 2, 3, 1), (2, 4, 5, 3), (4, 6, 7, 5), (6, 0, 1, 7)]
    assert abs(max(v[2] for v in verts) - min(v[2] for v in verts) - 0.45) < 1e-12 and MI.POST_H == 0.45


def test_the_tops_tool_copies_the_rules_numbers():
    mt = _load("author_median_tops_rule", ROOT / "tools" / "author_median_tops_blend.py")
    assert (mt.NOSE_VERTS, mt.NOSE_HALF_M, mt.DECK_INSET_M) == (MI.NOSE_VERTS, MI.NOSE_HALF, MI.DECK_INSET)
    assert abs(mt.DECK_OVER_M - (MI.CURB_H + 0.005)) < 1e-12 and mt.MIN_ISLAND_ROWS == MI.MIN_ISLAND_VERTS
    for k in (0, 1, 2, 3, 20, 37, 38, 39):                                    # its deck half width is the rule's
        assert abs(mt.deck_half(5.0, k, 40) - max(0.05, MI.half_width([5.0] * 40, 0, 40, k) - MI.DECK_INSET)) < 1e-12
