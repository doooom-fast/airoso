"""Phase 3 Step 0.4 config on a scratch copy of track.config.json (EXPANSION-PHASE3-PLAN "Defaults I will apply").

    python3 p3_config.py <in track.config.json> <out track.config.json> grow|phase3
grow:   terrain.grid_grow.cols_w 26 -> 88 only (the grow tool's project)
phase3: Step 0.4 as the planner reads it: route.bbox west to -117.101; terrain.far_extent west edge -117.14 (D2's
        default); terrain.grid_grow.cols_w 88 with tier_options.frame.pin.cols_w 88 (A14); planned_pavement gains
        data/expansion.west.planned.json (this run's stand-in for Step 1's expansion.west.json).
        route.route_connectors.routes is NOT given 'west' here: data/routes.json has no 'west' route yet and no step
        of this data run reads it.
"""
import json
import sys

cfg = json.load(open(sys.argv[1]))
mode = sys.argv[3]
t = cfg["terrain"]
assert t["grid_grow"]["cols_w"] == 26 and t["tier_options"]["frame"]["pin"]["cols_w"] == 26
t["grid_grow"]["cols_w"] = 88
if mode == "phase3":
    t["tier_options"]["frame"]["pin"]["cols_w"] = 88
    b = cfg["route"]["bbox"]
    assert b[1] == -117.082
    cfg["route"]["bbox"] = [b[0], -117.101, b[2], b[3]]
    fb = t["far_extent"]["bbox_swne"]
    assert fb[1] == -117.108
    t["far_extent"]["bbox_swne"] = [fb[0], -117.14, fb[2], fb[3]]
    t["tier_options"]["planned_pavement"]["files"] = list(t["tier_options"]["planned_pavement"]["files"]) + [
        "data/expansion.west.planned.json"]
cfg["_p3_scratch"] = {"mode": mode, "by": "p3_config.py (Lake Murray round 2 data run, 2026-11-22)"}
json.dump(cfg, open(sys.argv[2], "w"), indent=1)
print(mode, "far", t["far_extent"]["bbox_swne"], "grow", t["grid_grow"], "pin", t["tier_options"]["frame"]["pin"]["cols_w"],
      "planned", t["tier_options"]["planned_pavement"]["files"], "bbox", cfg["route"]["bbox"])
