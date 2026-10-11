"""tools/make_treefx.py — plan() is exactly what build() writes (ledger 0049 fix round: tools/verify_race.py G judges
the TreeFX trunks against the race lanes and walls from the planner, before the models are copied, and the ship
re-judges the written trees.txt). A tiny project: a straight 200 m road, palms beside it and one on it."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import make_treefx as mt  # noqa: E402
import verify_race as vr  # noqa: E402


def _project(bins=("PalmV1.bin",)):
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "source" / "trees").mkdir(parents=True)
    for b in bins:
        (d / "source" / "trees" / b).write_bytes(b"bin")
    (d / "track.config.json").write_text(json.dumps({"slug": "tiny"}), encoding="utf-8")
    pts = [[float(x), 0.0, 0.0] for x in range(0, 201, 5)]
    (d / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": pts, "widths_m": [10.0] * len(pts)}))
    palms = [{"x": 20.0, "y": 0.0, "z": 9.0}, {"x": 60.0, "y": 0.0, "z": -12.0},
             {"x": 100.0, "y": 0.0, "z": 2.0},                      # ON the road: make_treefx's corridor guard drops it
             {"x": 140.0, "y": 0.5, "z": 30.0}]
    (d / "data" / "scatter_positions.json").write_text(json.dumps({"palms": palms, "trees": [], "scrub": [],
                                                                   "median_planting": []}))
    return d


def test_plan_is_what_build_writes():
    d = _project()
    p = mt.plan(d)
    mt.build(d)
    written = (d / "build" / "tiny" / "extension" / "trees" / "trees.txt").read_text(encoding="utf-8")
    assert written == "\n".join(p["lines"]) + "\n"
    assert p["rejected"] == 1 and p["counts"] == {"palms": 3} and p["used"] == {"PalmV1.bin"}
    assert [(e["x"], e["z"]) for e in p["entries"]] == [(20.0, 9.0), (60.0, -12.0), (140.0, 30.0)]
    # the written file read back in the engine frame (trees.txt carries x, y, -z) is the plan's positions
    back = vr.tree_items_from_txt(written)
    assert [(i["x"], i["z"]) for i in back] == [(20.0, 9.0), (60.0, -12.0), (140.0, 30.0)]


def test_all_species_plans_positions_even_without_the_models():
    d = _project(bins=())
    assert mt.plan(d)["entries"] == []                              # no .bin: build() would write no palm at all
    e = mt.plan(d, all_species=True)["entries"]
    assert [(x["x"], x["z"]) for x in e] == [(20.0, 9.0), (60.0, -12.0), (140.0, 30.0)] and all(x["zone"] == "palms" for x in e)
