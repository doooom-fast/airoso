"""Text rules on build_mesh's late grass/guard passes (ledger 0060, Sand Creek 2026-10-29).

The passes run inside ``build_mesh.build`` on a whole project and have no unit seam; these pin the two
rules that the committed Sand Creek draft was red on, the way ``tests/ac/test_build_kn5_loop.py`` pins
the prep's conform rule. The measurement behind each is in the ledger: the seam-weld floor lifting the
pinned shoulder band in a cut back to natural (+1.5 .. +2.3 m over a 1ROAD_shoulder at deck height),
and the measured-guard sweep planting a stone lip at the toe of a 6 m retaining wall on a bridge
approach (drive_test "floating furniture" 8).
"""

from pathlib import Path

SRC = (Path(__file__).resolve().parents[2] / "scripts" / "geometry" / "build_mesh.py").read_text(encoding="utf-8")


def _block(start: str, end: str) -> str:
    a = SRC.index(start)
    b = SRC.index(end, a)
    return SRC[a:b]


def test_the_seam_weld_floor_is_capped_under_the_shoulder_too_but_the_cut_edge_keeps_the_deck():
    """The 22 % floor off the ring edge may never raise grass through pavement; the shoulder was the one
    sheet left out of that cap, and in a cut it is the sheet the grass was lifted through. The cut-edge
    excavation asks the same question of the DECK only: with the shoulder in its table it dug 30,048
    nodes along every cut's shoulder edge and the measured-guard fenced the ledge with 467 stone lips."""
    from scripts.geometry.build_mesh import seam_weld_tables      # the tables' unit seam (ledger 0067)
    assert "seam_weld_tables((road, runoff, kerb), shoulder, " in SRC
    road = {"vertices": [(0.0, 10.0, 0.0), (8.0, 10.0, 0.0), (8.0, 10.0, 8.0)], "tris": [(0, 1, 2)]}
    shoulder = {"vertices": [(8.0, 10.0, 0.0), (10.0, 9.8, 0.0), (10.0, 9.8, 8.0), (11.0, 9.0, 0.0)],
                "tris": [(0, 1, 2), (1, 3, 2)], "hem_idx": [3]}
    empty = {"vertices": [], "tris": []}
    deck, cap = seam_weld_tables((road, empty, empty), shoulder)
    in_deck = {t for ts in deck.values() for t in ts}
    in_cap = {t for ts in cap.values() for t in ts}
    road_tri = tuple(road["vertices"])
    face = tuple(shoulder["vertices"][i] for i in (0, 1, 2))
    hem = tuple(shoulder["vertices"][i] for i in (1, 3, 2))
    assert road_tri in in_deck and road_tri in in_cap
    assert face in in_cap and face not in in_deck                  # the shoulder caps the floor; the excavation keeps the deck
    # ... and never the buried hem: counted as pavement it capped the weld's apron under the ground at every toe
    assert hem not in in_cap


def test_the_shoulder_builders_name_their_hem_vertices():
    """ribbon.road_shoulder / curb_sidewalk return ``hem_idx``: the buried-hem vertices, so a pass that treats
    the sheet as pavement can leave the underground quad out."""
    from scripts.geometry import ribbon
    pts = [(0.0, 10.0, float(i) * 3.0) for i in range(12)]
    def ground(x, z):
        return 8.0                                                   # a 2 m fill everywhere

    sh = ribbon.road_shoulder(pts, [8.0] * len(pts), ground=ground)
    n = len(sh["vertices"])
    assert sh["hem_idx"] and len(sh["hem_idx"]) == n // 4, (len(sh["hem_idx"]), n)      # 4 points per station-side
    assert all(sh["vertices"][i][1] < 8.0 for i in sh["hem_idx"]), "the hem sits INTO the dirt"
    cs = ribbon.curb_sidewalk(pts, [8.0] * len(pts), ground=ground)
    assert cs["hem_idx"] and len(cs["hem_idx"]) == len(cs["vertices"]) // 6
    assert all(cs["vertices"][i][1] < 8.0 for i in cs["hem_idx"])
    assert "hem_idx" not in ribbon.road_shoulder(pts, [8.0] * len(pts)) or ribbon.road_shoulder(pts, [8.0] * len(pts))["hem_idx"] == []
    weld = _block("_weldW = 0", "[seam-weld]")
    assert "_pav_below_W(_gxW, _gzW, _floorW, _ptW_shW)" in weld, "the weld's cap uses the shoulder-inclusive table"
    cut = _block("# CUT-EDGE EXCAVATION", "[cut-edge]")
    assert "_pav_below_W(_ixW, _izW, _iyW)" in cut and "_ptW_shW" not in cut, "the excavation keeps the deck table"


def test_the_measured_guard_skips_declared_spans_and_never_sets_a_lip_far_below_the_deck():
    blk = _block("_wmedH = sorted(widths)[len(widths) // 2]", "if _guardH:")
    # the gate's own exemption, mirrored: declared bridge spans ± 20 m
    assert "_spansH = [(c - l / 2.0 - 20.0, c + l / 2.0 + 20.0) for c, l in (_bridges or [])]" in blk
    assert "if any(_aH <= _stp[min(_iH, len(_stp) - 1)] <= _bH for _aH, _bH in _spansH):" in blk
    # a lip is a deck-edge element
    assert "_LIP_MAX_BELOW_DECK_M = 1.5" in blk
    assert "and _prevH >= _yH0 - _LIP_MAX_BELOW_DECK_M" in blk
    # the exemption sits before any probing, inside the station loop, and resets the lip chain
    i_loop = blk.index("for _iH in range(len(centerline)):")
    i_span = blk.index("_spansH):")
    i_probe = blk.index("while _offH <= _weH + 9.0:")
    assert i_loop < i_span < i_probe
