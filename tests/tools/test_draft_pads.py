"""tools/draft_pads.py, the pure half of the engine-draft pads (ledger 0048 P3b): the traced outline, the cut barriers, the
deck heights and the seam weld. Stdlib only."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools import draft_pads as dp  # noqa: E402


def _grid(rows):
    g = [[ch == "#" for ch in r] for r in rows]
    return g, [float(c) for c in range(len(rows[0]))], [float(-r) for r in range(len(rows))]


def test_the_traced_outline_is_closed_counter_clockwise_and_on_the_region():
    g, xs, ys = _grid(["........", "..####..", ".######.", ".######.", "...##...", "........"])
    ring = dp.trace_boundary(g, xs, ys)
    assert dp.ring_area(ring) > 0                                             # counter-clockwise in E/N
    cells = {(int(x), int(-y)) for x, y in ring}
    assert all(g[r][c] for c, r in cells)                                     # every outline point is a region cell
    outer = {(c, r) for r in range(len(g)) for c in range(len(g[0])) if g[r][c] and any(
        not g[r + dr][c + dc] for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)))}
    assert outer <= cells                                                     # and every border cell is on it


def test_smoothing_keeps_a_cut_edge_exactly_straight_and_only_near_its_segment():
    sq = [(float(x), 0.0) for x in range(0, 20)] + [(20.0, float(y)) for y in range(0, 20)] + \
         [(float(x), 20.0) for x in range(20, 0, -1)] + [(0.0, float(y)) for y in range(20, 0, -1)]
    cut = dp.sealed_cut(((5.0, -0.3), (15.0, -0.3)), (10.0, 10.0))           # a cut along the bottom edge's middle
    out = dp.smooth_ring(sq, 1.0, keep_on=[cut])
    on = [p for p in out if 6.0 <= p[0] <= 14.0 and p[1] < 1.0]
    assert on and all(abs(p[1] + 0.3) < 1e-9 for p in on)                    # snapped exactly onto the cut line
    corner = [p for p in out if p[0] < 2.0 and p[1] < 2.0]
    assert corner and all(abs(p[1] + 0.3) > 1e-6 for p in corner)           # outside the segment: left alone


def test_resampling_spaces_the_ring_evenly():
    ring = [(0.0, 0.0), (30.0, 0.0), (30.0, 10.0), (0.0, 10.0)]
    out = dp.resample_ring(ring, 0.75)
    steps = [math.dist(out[i - 1], out[i]) for i in range(len(out))]
    assert len(out) == round(80 / 0.75) and max(steps) <= 80 / len(out) + 1e-9      # equal along the ring;
    assert sum(1 for d in steps if abs(d - 80 / len(out)) < 1e-9) >= len(out) - 4      # a chord across a corner is shorter


def test_the_deck_is_the_ground_plane_with_one_trim():
    pts = [(dx, dy, 2.0 + 0.03 * dx - 0.01 * dy) for dx in (-1.5, -0.5, 0.5, 1.5) for dy in (-1.5, -0.5, 0.5, 1.5)]
    pts.append((0.2, 0.1, 2.6))                                              # a car roof / a curb top: trimmed
    assert abs(dp.plane_height(pts) - 2.0) < 1e-9
    assert dp.plane_height(pts[:5]) is None                                  # too few ground points: no plane


def test_deck_lookup_and_its_fallback_near_the_asphalt_edge():
    deck = {"e0": 0.0, "n0": 0.0, "cell_m": 0.5, "nx": 4, "ny": 4,
            "y": [[1.0, 1.0, None, None], [1.0, 1.0, None, None], [None] * 4, [None] * 4]}
    assert dp.deck_at(deck, 0.25, 0.25) == pytest.approx(1.0)
    assert dp.deck_at(deck, 1.5, 1.5) is None
    assert dp.deck_near(deck, 1.5, 1.5) == pytest.approx(1.0)               # the nearest measured node within 3 m
    assert dp.deck_near(deck, 40.0, 40.0) is None


def test_the_seam_blend_is_exact_on_a_seam_vertex_and_smooth_between():
    seams = [(0.0, 0.0, 0.3), (10.0, 0.0, -0.1)]
    assert dp.seam_blend(0.0, 0.0, seams) == 0.3 and dp.seam_blend(10.0, 0.0, seams) == -0.1
    mid = dp.seam_blend(5.0, 0.0, seams)
    assert -0.1 < mid < 0.3 and abs(mid - 0.1) < 1e-9


def test_a_cut_is_a_barrier_segment_not_a_half_plane():
    assert dp.segment_band((0.0, 0.0), (10.0, 0.0), 5.0, 0.2, 0.3)
    assert not dp.segment_band((0.0, 0.0), (10.0, 0.0), 15.0, 0.0, 0.3)    # past the segment's end: no barrier
    box = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert dp.in_ring_grid(box, 5.0, 5.0) and not dp.in_ring_grid(box, 15.0, 5.0)


def test_the_lap_cut_keeps_the_node_side():
    pts = [(float(i), 0.0, 0.0) for i in range(20)]                         # a straight lap along +E
    c_in, c_out = dp.lap_cut(pts, 5, 10), dp.lap_cut(pts, 15, 10)
    assert dp.side(c_in, 8.0, 0.0) > 0 and dp.side(c_in, 2.0, 0.0) < 0
    assert dp.side(c_out, 12.0, 0.0) > 0 and dp.side(c_out, 18.0, 0.0) < 0


def test_declarations_are_checked():
    ok = {"route": {"draft_pads": [{"id": "C14", "node": 10, "cuts": [5, 15]}]}}
    assert dp.declaration(ok, "C14")["node"] == 10
    for bad in ({"id": "X", "node": 3, "cuts": [5, 15]}, {"id": "X", "node": 10, "cuts": [5]},
                {"id": "X", "node": 10, "cuts": [5, 15], "sealed": [[[0, 0]]]}):
        with pytest.raises(SystemExit):
            dp.declarations({"route": {"draft_pads": [bad]}})
    assert dp.declarations({}) == []


def test_the_chain_carries_the_author_step():
    # the Lariat V3 WIP's author step (claude/lariat-pads-wip), kept beside the LM port's draft_lm_pads step
    src = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")
    assert "author_draft_pads() {" in src and "tools/author_draft_pads_blend.py" in src


def test_the_chain_carries_the_lm_pads_step():
    src = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")
    assert "draft_lm_pads() {" in src and "tools/lm_pads_blend.py" in src
    assert "draft_cutfill() {" in src and "tools/cutfill_blend.py" in src


def _bash():
    import shutil
    import subprocess
    sh = shutil.which("bash")
    if not sh:
        return None
    try:
        ok = subprocess.run([sh, "-c", "echo ok"], capture_output=True, text=True, timeout=30).stdout.strip() == "ok"
    except (OSError, subprocess.SubprocessError):
        ok = False
    return sh if ok else None


def test_the_lm_pads_step_shows_a_refusal_on_failure():
    """2026-11-23 (Sand Creek 0.2.9's rehearsal at 903c3436): the step's `2>&1 | grep "^\\[lm-pads\\]..."` hid draft_pads'
    "[pads] the outline crosses itself through a seam row: measure again" (stderr, ahead of the buffered stdout), so the log
    ended on the last [lm-pads] line with EXIT 1. ship_track.sh's bl_filtered keeps the filter on success and prints the
    error output on a failure, Blender's start-up noise left out; the step's status is Blender's"""
    import subprocess
    sh = _bash()
    if sh is None:
        pytest.skip("no working bash")
    src = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert 'bl_filtered "^\\[lm-pads\\]' in src.split("draft_lm_pads() {", 1)[1].split("\n}\n", 1)[0]
    fn = "bl_filtered() {" + src.split("bl_filtered() {", 1)[1].split("\n}\n", 1)[0] + "\n}\n"
    script = "set -euo pipefail\n" + fn + r"""
refuse() {
  echo "[lm-pads] colorado_50th: deck ok"; echo "Read prefs: /x/userpref.blend"; echo "noise on stdout"
  echo "register_class(...):" >&2; echo "Warning: 'ACPanelMixamo' does not contain '_PT_' with prefix and suffix" >&2
  echo "[pads] the outline crosses itself through a seam row: measure again" >&2
  return 1
}
fine() { echo "[lm-pads] 6 pad(s) built"; echo "noise on stdout"; echo "chatter on stderr" >&2; return 0; }
BL=refuse; ( bl_filtered "^\[lm-pads\]\|FATAL" --background ) && echo "RC 0" || echo "RC $?"
echo "---"
BL=fine; ( bl_filtered "^\[lm-pads\]\|FATAL" --background ) && echo "RC 0" || echo "RC $?"
"""
    out = subprocess.run([sh, "-s"], input=script, capture_output=True, text=True, timeout=60).stdout
    bad, good = out.split("---\n")
    assert "[lm-pads] colorado_50th: deck ok" in bad and "RC 1" in bad
    assert "[step] FAILED (exit 1)" in bad and "[pads] the outline crosses itself through a seam row" in bad
    assert "register_class" not in bad and "ACPanelMixamo" not in bad and "Read prefs" not in bad
    assert "noise on stdout" not in bad
    assert good.strip().splitlines() == ["[lm-pads] 6 pad(s) built", "RC 0"]


def test_the_seam_offset_is_exact_on_the_row_linear_along_it_and_faded_in():
    c = {"p": (0.0, 0.0), "n": (0.0, 1.0)}                                  # a row along x, the pad on +y
    row = [(-4.0, 0.0, 10.10), (4.0, 0.0, 9.90)]
    prof = dp.seam_profile([(c, row)], lambda x, y: 10.0)                    # flat measured ground at 10.0
    assert dp.seam_offset(prof, -4.0, 0.0) == pytest.approx(0.10)
    assert dp.seam_offset(prof, 4.0, 0.0) == pytest.approx(-0.10)
    assert dp.seam_offset(prof, 0.0, 0.0) == pytest.approx(0.0)              # linear between the row's vertices
    assert dp.seam_offset(prof, -4.0, dp.SEAM_FADE_M / 2) == pytest.approx(0.05)
    assert dp.seam_offset(prof, -4.0, dp.SEAM_FADE_M + 1.0) == 0.0          # the measured ground beyond the fade
    steps = [dp.seam_offset(prof, -4.0, y * 1.0) for y in range(0, 14)]
    assert max(abs(b - a) for a, b in zip(steps, steps[1:])) < 0.06 * 0.1 / 0.06   # a smooth fade, no step


def test_the_row_splice_puts_the_row_into_the_ring_and_unties_it():
    # a square pad 0..10 x 0..10, the lap entering from the south (row along y = 0 from x = 3 to x = 7)
    ring = [(0.0, 0.0), (3.0, 0.0), (7.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    c = {"p": (5.0, 0.0), "n": (0.0, 1.0), "a": (-30.0, 0.0), "b": (30.0, 0.0), "vertex": 0}
    row = [(2.0, 0.0, 1.0), (5.0, 0.0, 1.1), (8.0, 0.0, 1.0)]
    cr = dp.row_cut(row, (5.0, 5.0))
    out = dp.splice_rows(ring, [(c, cr, row)])
    keys = {(round(q[0], 6), round(q[1], 6)) for q in out}
    assert {(2.0, 0.0), (5.0, 0.0), (8.0, 0.0)} <= keys                     # the row's vertices are the weld
    assert abs(dp.ring_area(out)) == pytest.approx(100.0, rel=1e-6)


def test_untie_cuts_a_folded_spur_out():
    bow = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (5.0, -1.0), (6.0, -1.0), (0.0, 4.0)]
    simple = dp.untie(bow)
    for i in range(len(simple)):
        for j in range(i + 2, len(simple)):
            if (j + 1) % len(simple) == i:
                continue
            assert dp._seg_x(simple[i], simple[(i + 1) % len(simple)], simple[j], simple[(j + 1) % len(simple)]) is None


def test_pad_boxes_cut_m_pair_is_opt_in():
    """2026-11-22 (dahlia_56th): lm_pads.plan cut_m may be [in_m, out_m]; a number is both cuts, as before"""
    from tools import pad_boxes as pb
    assert pb.cut_pair(30.0) == (30.0, 30.0) and pb.cut_pair(30) == (30.0, 30.0)
    assert pb.cut_pair([30.0, 17.0]) == (30.0, 17.0)
    for bad in (True, [30.0], [30.0, 0.0], [-1.0, 5.0], "30", [30.0, True]):
        with pytest.raises(SystemExit):
            pb.cut_pair(bad)


def test_pad_boxes_asymmetric_cuts_on_a_straight_lap(tmp_path):
    import json
    from tools import pad_boxes as pb
    pts = [[0.0, 0.0, 2.0 * k] for k in range(60)]            # a straight lap north, a vertex every 2 m
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": pts, "widths_m": [10.0] * 60}))
    plan = {"id": "p", "node_xz": [0.0, 60.0], "curb_return_m": 3}
    for cut, want in ((30.0, [15, 45]), ([30.0, 17.0], [15, 39])):
        (tmp_path / "track.config.json").write_text(json.dumps({"lm_pads": {"plan": [dict(plan, cut_m=cut)]}}))
        _, out = pb.build(tmp_path)
        assert out[0]["node"] == 30 and out[0]["cuts"] == want
    assert "either side" not in out[0]["_by"] and "30 m of arc before and 17 m after" in out[0]["_by"]


def test_deck_floor_leaves_a_dark_creek_bank_out_of_the_deck(tmp_path):
    """2026-11-22 (dahlia_56th's 6.833 m seam): a wet bank reads as dark as asphalt; with deck_floor_m a class-2 point more
    than that under the nearest lap vertex is not the road. Absent = every point, as before"""
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    pytest.importorskip("PIL")
    import json
    from tools import draft_pad_outline as dpo
    pts = [[0.0, 10.0, 2.0 * k - 60.0] for k in range(61)]       # the lap north along x = 0 at y 10, node v30 at (0, 0)
    rng = np.random.default_rng(1)
    E = rng.uniform(-30, 30, 9000)
    N = rng.uniform(-30, 30, 9000)
    bank = (E > 8.0) & (E < 16.0)                                  # x 8..16: a creek bank 4 m down, as dark as the road
    Z = np.where(bank, 6.0, 10.0) + 1000.0
    I = np.where((np.abs(E) < 8.0) | bank, 0.0, 900.0)             # the verges (x < -8, x > 16) bright
    (tmp_path / "data").mkdir()
    (tmp_path / "source" / "pads").mkdir(parents=True)
    (tmp_path / "data" / "centerline.local.json").write_text(json.dumps(
        {"origin": {"lat": 39.0, "lon": -104.0, "elev_m": 1000.0}, "points_xyz_m": pts, "widths_m": [12.0] * 61}))
    np.savez(tmp_path / "source" / "pads" / "p.lidar.npz", E=E, N=N, Z=Z, I=I, half=30.0, cE=0.0, cN=0.0)
    decl = {"id": "p", "node": 30, "cuts": [20, 40], "box": [[-12, -22], [12, -22], [12, 22], [-12, 22]],
            "half_m": 30.0, "source": {"kind": "lidar_ept", "ept": "https://example.invalid/ept.json"}}
    deck_at = {}
    for floor in (None, 0.75):
        d = dict(decl, **({"deck_floor_m": floor} if floor else {}))
        (tmp_path / "track.config.json").write_text(json.dumps({"lm_pads": {"pads": [d]}}))
        dpo.main([str(tmp_path), "p"])
        rec = json.loads((tmp_path / "source" / "pads" / "p.json").read_text(encoding="utf-8"))
        dk = rec["deck"]
        i = int(round((10.5 - dk["e0"]) / dk["cell_m"]))
        j = int(round((0.0 - dk["n0"]) / dk["cell_m"]))
        deck_at[floor] = dk["y"][j][i]
        assert ("deck_floor_m" in rec) == (floor is not None)
    assert abs(deck_at[None] - 6.0) < 0.05                        # without the floor the bank is "road"
    assert deck_at[0.75] is None                                   # with it the node carries none: filled from the road
