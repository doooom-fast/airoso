"""terrain.tier_options.planned_pavement (ledger 0054 P2, 2026-10-14): pavement a later phase builds, read from an
authored intermediate, marks the TIERS and the PHYSICAL ground (with its pockets) as a built pavement does - never
the kept cells or their refinement.

- absent: the spec has no planned files and Topology(plan_lines=()) is the topology the roads alone give, byte for byte;
- a planned line far from the road refines its own 5 m band and makes the ground within physical_within_m of it
  physical; the kept cells (and the refine sub-cells) are the road's alone;
- a planned loop off the road encloses a pocket: the far cells inside it become physical (the pocket rule);
- terrain_sample.planned_inputs: pieces at their wider curb, pad outlines and stub pavements as closed zero-width rings;
  a missing file stops the planner; a planned_pavement block without files is refused.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.elevation import terrain_sample as ts  # noqa: E402
from scripts.geometry import terrain_tiers as tt  # noqa: E402

ORIGIN = {"lon": -117.0, "lat": 32.8, "elev_m": 100.0}


def _terrain(planned=None, far=(32.789, -117.013, 32.811, -116.987)):
    t = {"tiers": [{"within_m": 30.0, "cell_m": 5.0, "x_split": True}, {"within_m": 200.0, "cell_m": 20.0},
                   {"cell_m": 40.0}],
         "tier_options": {"keep_cells": {"cell_m": 20.0, "within_m": 10.0,
                                         "refine": {"cell_m": 5.0, "beyond_m": 10.0, "edge_m": 5.5,
                                                    "move_beyond_m": 20.0, "min_face_d_m": 12.0}},
                          "physical_within_m": 120.0},
         "far_extent": {"bbox_swne": list(far)}}
    if planned is not None:
        t["tier_options"]["planned_pavement"] = planned
    return t


def _line(x0, z0, x1, z1, w, n=40):
    pts = [(x0 + (x1 - x0) * k / n, 0.0, z0 + (z1 - z0) * k / n) for k in range(n + 1)]
    return pts, [w] * len(pts)


ROAD = [_line(-600.0, -400.0, 600.0, -400.0, 12.0)]


def _phys_area(topo):
    return sum(1 for p in topo.tri_phys if p)


def test_absent_is_byte_identical():
    spec = tt.TierSpec(_terrain(), ORIGIN)
    assert spec.planned_files == []
    a = tt.Topology(spec, ROAD, closed_first=False)
    b = tt.Topology(spec, ROAD, closed_first=False, plan_lines=())
    assert (a.vkeys, a.tris, a.tri_phys, a.vkeep, a.refine_cells) == (b.vkeys, b.tris, b.tri_phys, b.vkeep, b.refine_cells)


def test_planned_line_marks_tiers_and_physical_never_kept_cells():
    spec = tt.TierSpec(_terrain({"files": ["data/x.json"]}), ORIGIN)
    assert spec.planned_files == ["data/x.json"]
    plan = [_line(-500.0, 600.0, 500.0, 600.0, 20.0)]
    a = tt.Topology(spec, ROAD, closed_first=False)
    b = tt.Topology(spec, ROAD, closed_first=False, plan_lines=plan)
    assert b.n_plan_lines == 1
    # the kept cells and their refinement follow the BUILT road only
    assert a.keep == b.keep and a.refine_cells == b.refine_cells
    assert sum(b.vkeep) == sum(a.vkeep)
    # the planned line's 5 m band: a point on it now lies in a finest leaf (5 m), in a.(40 m) it did not
    f = b.f
    probe = (0.0, 600.0)
    X2 = int(round(2 * (probe[0] - f.x0) / f.ux))
    Z2 = int(round(2 * (probe[1] - f.z0) / f.uz))
    la, lb = a.locate2(X2, Z2), b.locate2(X2, Z2)
    assert lb[0] == len(spec.levels) - 1 and la[0] < lb[0]
    # physical within physical_within_m of it: that leaf is physical now, far before
    assert lb in b.phys_leaves and la not in a.phys_leaves
    assert _phys_area(b) > _phys_area(a)


def test_planned_loop_makes_its_pocket_physical():
    spec = tt.TierSpec(_terrain({"files": ["data/x.json"]}), ORIGIN)
    ring = [(-450.0, 0.0, 100.0), (450.0, 0.0, 100.0), (450.0, 0.0, 900.0), (-450.0, 0.0, 900.0), (-450.0, 0.0, 100.0)]
    plan = [(ring, [20.0] * len(ring))]
    b = tt.Topology(spec, ROAD, closed_first=False, plan_lines=plan)
    f = b.f
    centre = (0.0, 500.0)                      # 400 m from every side: past physical_within_m 120, inside the loop
    lf = b.locate2(int(round(2 * (centre[0] - f.x0) / f.ux)), int(round(2 * (centre[1] - f.z0) / f.uz)))
    assert lf in b.phys_leaves
    outside = (0.0, 1150.0)                    # 250 m beyond the loop, inside the far box: still the far ring
    lo = b.locate2(int(round(2 * (outside[0] - f.x0) / f.ux)), int(round(2 * (outside[1] - f.z0) / f.uz)))
    assert lo is not None and lo not in b.phys_leaves


def test_planned_inputs_reads_pieces_pads_and_stubs():
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    inter = {"pieces": [{"columns": ["s", "x", "z", "y_3dep", "left_m", "right_m"],
                         "stations": [[0.0, 0.0, 0.0, 1.0, 12.0, -9.0], [2.5, 0.0, 2.5, 1.0, 11.0, -13.5]]}],
             "pads": [{"outline_xz": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0]]}],
             "stubs": [{"pavement_xz": [[20.0, 0.0], [30.0, 0.0], [30.0, 5.0], [20.0, 5.0]]}]}
    (d / "data" / "x.json").write_text(json.dumps(inter), encoding="utf-8")
    spec = tt.TierSpec(_terrain({"files": ["data/x.json"]}), ORIGIN)
    lines, files = ts.planned_inputs(d, spec)
    assert files == [d / "data" / "x.json"]
    assert len(lines) == 3
    pts, w = lines[0]
    assert pts == [(0.0, 0.0, 0.0), (0.0, 0.0, 2.5)] and w == [24.0, 27.0]
    pad, wp = lines[1]
    assert pad[0] == pad[-1] and len(pad) == 4 and wp == [0.0] * 4
    stub, _ws = lines[2]
    assert stub[0] == stub[-1] and len(stub) == 5
    # none declared: nothing read
    assert ts.planned_inputs(d, tt.TierSpec(_terrain(), ORIGIN)) == ([], [])
    # a missing file stops the planner (never a silent plan without it)
    try:
        ts.planned_inputs(d, tt.TierSpec(_terrain({"files": ["data/missing.json"]}), ORIGIN))
    except SystemExit as e:
        assert "missing.json" in str(e)
    else:
        raise AssertionError("a missing planned-pavement file must stop the planner")
    try:
        tt.TierSpec(_terrain({"files": []}), ORIGIN)
    except ValueError as e:
        assert "planned_pavement" in str(e)
    else:
        raise AssertionError("a planned_pavement block without files must be refused")


def test_committed_config_plans_the_north_network():
    """the San Diego config declares the authored intermediate the plan reads (the file the ship syncs in)"""
    track = ROOT / "tracks" / "san-diego-lake-murray"
    cfg = json.loads((track / "track.config.json").read_text(encoding="utf-8"))
    pp = cfg["terrain"]["tier_options"]["planned_pavement"]
    assert pp["files"] == ["data/expansion.north.json"] and (track / "data" / "expansion.north.json").exists()
    spec = tt.TierSpec(cfg["terrain"], json.loads((track / "data" / "centerline.local.json").read_text())["origin"])
    lines, _files = ts.planned_inputs(track, spec)
    assert len(lines) == 4 + 3 + 6                    # four pieces, the J2-J4 pads, the six see-only stubs
