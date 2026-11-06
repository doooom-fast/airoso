"""tools/kerb_section.py: a traced kerb at its MEASURED place across the port ribbon's lane edge (ledger 0081, round 2)."""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import kerb_section as ks  # noqa: E402


def test_the_measured_edge_is_read_as_an_offset_from_this_ribbons_edge():
    # the ribbon's left edge at (0, 6), outward +y; the live (measured) edge runs 0.9 m INSIDE it (y = 5.1)
    live = [(-10.0, 5.1), (10.0, 5.1)]
    d = ks.edge_delta((0.0, 6.0), (0.0, 1.0), live)
    assert abs(d + 0.9) < 1e-9
    # paint measured -2.05 .. -0.4 across the live edge sits -2.95 .. -1.3 across this ribbon's edge
    assert abs((-2.05 + d) + 2.95) < 1e-9 and abs((-0.4 + d) + 1.3) < 1e-9


def test_a_kerb_rises_over_its_measured_width_and_paint_stays_flat():
    k = ks.section(-2.0, -0.5, 0.08, False, 0.003, 0.25, 1.0, 0.05)
    assert k == [(-2.0, 0.003), (-1.75, 0.08), (-0.5, 0.08), (0.5, -0.05)]
    p = ks.section(-1.0, 0.05, 0.08, True, 0.003, 0.25, 1.0, 0.05)
    assert p == [(-1.0, 0.003), (0.05, 0.003), (1.05, -0.05)]
    # narrower than its ramp: the top still lies inside the paint
    n = ks.section(0.0, 0.1, 0.08, False, 0.003, 0.25, 1.0, 0.05)
    assert n[0][0] < n[1][0] < n[2][0] == 0.1


def test_the_end_ramp_is_opt_in_and_linear():
    assert ks.end_scale(0.0, 20.0, None) == 1.0 and ks.end_scale(0.0, 20.0, 0.0) == 1.0
    assert ks.end_scale(0.0, 20.0, 4.0) == 0.0 and ks.end_scale(2.0, 20.0, 4.0) == 0.5
    assert ks.end_scale(10.0, 20.0, 4.0) == 1.0 and ks.end_scale(19.0, 20.0, 4.0) == 0.25


def test_a_run_is_clipped_to_its_measured_ends_not_to_the_nearest_rows():
    assert abs(ks.arc_of([(0, 0), (3, 0), (6, 0)], (4.5, 0.7)) - 4.5) < 1e-9
    picks = ks.clipped_rows([0.0, 3.0, 6.0, 9.0], 1.5, 7.0)
    assert picks[0] == (0, 1, 0.5) and picks[1:3] == [(1, 1, 0.0), (2, 2, 0.0)]
    assert picks[-1][:2] == (2, 3) and abs(picks[-1][2] - 1 / 3) < 1e-9


def test_measured_placement_is_opt_in_and_lake_murray_sets_no_kerbs():
    """Absent kerb.placement the author lays every run outside the lane edge as before; Lake Murray names no kerbs file,
    so the kerbs step is a no-op there."""
    src = (ROOT / "tools" / "author_kerbs_blend.py").read_text(encoding="utf-8")
    assert '.get("placement") == "measured"' in src
    tree = ast.parse(src)
    consts = {t.id: n.value.value for n in tree.body if isinstance(n, ast.Assign) for t in n.targets
              if isinstance(t, ast.Name) and isinstance(n.value, ast.Constant)}
    assert consts["LAYER_M"] <= 4.0                       # L4: the ROAD surface read within a layer gap of the edge
    lm = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json").read_text(encoding="utf-8"))
    assert not (lm.get("route") or {}).get("kerbs_file") and "placement" not in (lm.get("kerb") or {})


def test_the_pad_seat_runs_only_where_a_config_asks_for_it():
    """tools/seat_pads_blend.py (round 2, Nevada's apron) runs inside prep only for scenery.bespoke.pads_seat "ground";
    Lake Murray sets no bespoke pads, so its chain is unchanged."""
    sh = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")
    assert "get('pads_seat') == 'ground'" in sh and "tools/seat_pads_blend.py" in sh
    src = (ROOT / "tools" / "seat_pads_blend.py").read_text(encoding="utf-8")
    assert 'bes.get("pads_seat") != "ground"' in src
    lm = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json").read_text(encoding="utf-8"))
    assert "pads_seat" not in (((lm.get("scenery") or {}).get("bespoke")) or {})
    nv = json.loads((ROOT / "tracks" / "exotics-racing-lv-lm" / "track.config.json").read_text(encoding="utf-8"))
    b = nv["scenery"]["bespoke"]
    assert b["pads_seat"] == "ground" and b["pads_surface"] == "1RUNOFF" and "1RUNOFF" in nv["texture_overrides"]


def test_a_ground_triangle_is_cut_to_the_pad_cell_on_its_own_plane():
    import pad_clip as pc
    tri = [(0.0, 0.0, 0.0), (4.0, 0.0, 4.0), (0.0, 4.0, 0.0)]          # z = x
    piece = pc.clip(tri, [(1.0, -1.0), (3.0, -1.0), (3.0, 5.0), (1.0, 5.0)])
    assert len(piece) >= 3 and all(1.0 - 1e-9 <= p[0] <= 3.0 + 1e-9 for p in piece)
    assert all(abs(p[2] - p[0]) < 1e-9 for p in piece)                  # on the triangle's plane
    assert pc.clip(tri, [(10.0, 10.0), (11.0, 10.0), (11.0, 11.0)]) == []
