"""Rehearse the HELD north corridor in build/phase2/north-rehearsal, never in the track.

From the repo root: .venv/bin/python tracks/san-diego-lake-murray/source/expansion/rehearse_north.py
Exit 1 records a refused draft, not permission to author past it. No Blender save, AI, export or install.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PROJECT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/phase2/north-rehearsal"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import barrier_bands as bands
import layout_dummies as dummies
from scripts.geometry import race_lap

INPUTS = ("centerline.local.json", "connectors.local.json", "median_bands.json", "mouths.json",
          "pads.plan.json", "bridge.spans.auto.json", "aprons.json")


def compose(base, held):
    """Copy only authored lap-local draft choices; never mainline vertex declarations or chicanes."""
    cfg = copy.deepcopy(base)
    spec = copy.deepcopy(held["spec"])
    corridor = copy.deepcopy(base["race"]["corridor"])
    for key in ("_doc", "_boxes_apex_doc", "clear_width_source"):
        corridor.pop(key, None)
    corridor.update(copy.deepcopy(held["rehearsal"]["corridor"]))
    spec["corridor"] = corridor
    cfg["race"].setdefault("laps", {})[held["lap"]] = spec
    cfg["layouts"] += copy.deepcopy(held["rehearsal"]["layouts"])
    return cfg


def main():
    held = json.loads((Path(__file__).parent / "race.north.held.json").read_text())
    base = json.loads((PROJECT / "track.config.json").read_text())
    cfg = compose(base, held)
    data = OUT / "data"
    data.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in INPUTS:
        src = PROJECT / "data" / name
        hashes[name] = hashlib.sha256(src.read_bytes()).hexdigest()
        shutil.copyfile(src, data / name)
    joins_path = Path(held["spec"]["joins_file"])
    (OUT / joins_path).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PROJECT / joins_path, OUT / joins_path)
    (OUT / "track.config.json").write_text(json.dumps(cfg, indent=2) + "\n")
    rec = race_lap.stitch(OUT, cfg, held["lap"])
    race_lap.write(OUT, rec)
    line = dummies.Line(rec["points_xyz_m"], rec["widths_m"])
    dummy_fails = []
    for lo in held["rehearsal"]["layouts"]:
        dd, problems = dummies.layout_dummies(line, lo, cfg["race"], rec["island_w_by_vertex"])
        dd["_lap"] = held["lap"]
        (data / f"dummies_{lo['id']}.json").write_text(json.dumps(dd, indent=2) + "\n")
        dummy_fails += problems
    # All planner self-gates stay enabled. It refuses invalid zones before planned flood fill.
    try:
        result = bands.build(OUT, lap=held["lap"])
    except SystemExit as exc:
        result = {"fails": [str(exc)], "corners": bands._corners(
            bands._load_place_signs(), rec["points_xyz_m"], rec["widths_m"],
            cfg["race"]["kerbs"].get("min_turn_deg", 45.0)), "corridors": {}}
    fails = dummy_fails + result["fails"]
    report = {
        "status": "REFUSED" if fails else "PLANNED_ONLY",
        "built_artifact_gates_run": False,
        "source_sha256": hashes,
        "lap_m": rec["lap_m"], "unique_vertices": rec["point_count"] - 1,
        "detected_corners": result["corners"],
        "declared_boxes": held["rehearsal"]["corridor"]["boxes"],
        "dummy_fails": dummy_fails, "fails": fails,
        "planned_no_route": {lid: c["no_route"].get("planned", "not run: declaration refused")
                             for lid, c in result["corridors"].items()},
        "source_unchanged": all(hashlib.sha256((PROJECT / "data" / n).read_bytes()).hexdigest() == h
                                for n, h in hashes.items()),
    }
    (OUT / "rehearsal.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "lap_m", "dummy_fails", "fails", "source_unchanged")}, indent=2))
    return int(bool(fails) or not report["source_unchanged"])


if __name__ == "__main__":
    raise SystemExit(main())
