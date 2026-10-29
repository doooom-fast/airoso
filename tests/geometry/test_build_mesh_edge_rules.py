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
    blk = _block("_ptW: dict = {}", "def _pav_below_W(")
    assert "for _sheetW in (road, runoff, kerb, shoulder):" in blk, blk
    assert "if _sheetW is not shoulder:" in blk and "_ptW_shW.setdefault" in blk
    assert "NOT the shoulder" not in blk
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
