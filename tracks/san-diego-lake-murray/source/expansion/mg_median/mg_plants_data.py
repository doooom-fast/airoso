"""The median plants that stand on pavement since Mission Gorge Rd's island was corrected (ledger 0099 round 3, item 1b).

    python -I tracks/san-diego-lake-murray/source/expansion/mg_median/mg_plants_data.py [--write]

data/scatter_positions.json's median_planting spots were drawn on the island as it was declared: one unbroken island
4.5-5.4 m wide. fix_mg_median.py corrected it in two places (the crossing: two islands with no median between their noses and a narrow
strip beside each turn pocket; the J3 end: MD11 on its real line, the openings where they are), so some spots now stand
on asphalt. No spot is moved (Kevin 2026-11-18, the spots' places; the Mac
2026-11-23: "plants on new asphalt listed and dropped, none moved"). A spot of the changed stretch (the points the
correction changed, by its nearest point of the islands as they were) is:

  kept     on the new island's deck: within the deck's half width of the island's middle at its nearest point
           (tools/median_island.py: the nose-tapered half width less DECK_INSET);
  dropped  anywhere else: between the noses, on the pavement beside a strip, or on a strip's curb ring (a trunk on the
           ring reaches the race curb strip: ledger 0055 round 2's rule for College).

Written as tools/make_treefx.py's scenery.treefx.median_spots list (drop, by index, each with its own x / z), in a file
of its own beside College's. Each entry carries the lidar's height at the spot (source/vegetation/
median_heights.lidar.json): a dropped spot that the lidar saw a plant at (MIN_H_M or more) is FATAL here, because a
real plant standing where this says there is asphalt would mean the island's outline is wrong, not the plant."""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
ROOT = HERE.parents[4]
LINE = "north_mission_gorge"
OUT = HERE / "mg_median.median_spots.json"
RECORD = HERE / "mg_median_correction.json"
REACH_M = 1.0          # [invented] a spot belongs to the island as it was if it lies within its half width + this of a point


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MI = _load("_median_island_mg_plants", ROOT / "tools" / "median_island.py")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    data = PROJECT / "data"
    spots = json.loads((data / "scatter_positions.json").read_text(encoding="utf-8"))["median_planting"]
    isl = next(c for c in json.loads((data / "median_bands.json").read_text(encoding="utf-8"))["connector_islands"] if c["name"] == LINE)
    P, W = isl["points_xyz_m"], [float(w) for w in isl["island_w_by_point"]]
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    P0, W0 = [list(p) for p in P], list(W)
    for k, v in rec["island"]["before"].items():
        P0[int(k)], W0[int(k)] = v["p"], float(v["w"])
    runs = [tuple(r) for r in rec["island"]["points_changed_runs"]]
    a, b = runs[0][0], runs[-1][1]
    lidar = json.loads((PROJECT / "source" / "vegetation" / "median_heights.lidar.json").read_text(encoding="utf-8"))
    min_h = float(lidar["min_h_m"])
    if len(lidar["spots"]) != len(spots):
        raise SystemExit(f"[mg-plants] the lidar file holds {len(lidar['spots'])} spots, scatter_positions.json {len(spots)}")
    segs = MI.segments(W)
    drop, kept = [], []
    for i, s in enumerate(spots):
        k0 = min(range(max(0, a - 6), min(len(P0), b + 7)), key=lambda k: math.hypot(s["x"] - P0[k][0], s["z"] - P0[k][2]))
        if not any(r0 <= k0 <= r1 for r0, r1 in runs) or W0[k0] <= 0 or math.hypot(s["x"] - P0[k0][0], s["z"] - P0[k0][2]) > 0.5 * W0[k0] + REACH_M:
            continue
        k = min(range(max(0, a - 6), min(len(P), b + 7)), key=lambda q: math.hypot(s["x"] - P[q][0], s["z"] - P[q][2]))
        tx, tz = MI.tangent(P, k)
        lat = (s["x"] - P[k][0]) * (-tz) + (s["z"] - P[k][2]) * tx
        seg = next(((i0, j0) for i0, j0 in segs if i0 <= k < j0), None)
        half = MI.half_width(W, seg[0], seg[1], k) if seg else 0.0
        deck = max(0.05, half - MI.DECK_INSET) if seg else 0.0
        h = float(lidar["spots"][i][2])
        if abs(lidar["spots"][i][0] - s["x"]) > 0.006 or abs(lidar["spots"][i][1] - s["z"]) > 0.006:
            raise SystemExit(f"[mg-plants] the lidar file's spot {i} is not scatter_positions.json's spot {i}")
        if seg and abs(lat) <= deck:
            kept.append({"index": i, "point": k, "lateral_m": round(lat, 2), "deck_half_m": round(deck, 2), "lidar_h_m": h})
            continue
        where = "no median: between the two noses" if not seg else \
            ("the strip's curb ring" if abs(lat) <= half else "pavement beside the island")
        if h >= min_h:
            raise SystemExit(f"[mg-plants] spot {i} ({s['x']}, {s['z']}) would be dropped ({where}) but the lidar saw a plant "
                             f"{h} m tall there: the island's outline is wrong, not the plant")
        drop.append({"index": i, "x": s["x"], "z": s["z"], "point": k, "lateral_m": round(lat, 2), "half_m": round(half, 2),
                     "where": where, "why": f"bare on the lidar ({h:.2f} m); stands on {where.split(':')[0]} since the island was corrected"})
    by = {}
    for d in drop:
        by[d["where"]] = by.get(d["where"], 0) + 1
    print(f"[mg-plants] {len(drop) + len(kept)} spots on the islands as they were over points {[list(r) for r in runs]}: {len(kept)} kept on the new deck "
          f"(lidar {min(k['lidar_h_m'] for k in kept):.2f}-{max(k['lidar_h_m'] for k in kept):.2f} m), {len(drop)} dropped {by}; "
          f"every dropped spot is bare on the lidar (under {min_h} m)")
    if "--write" in argv:
        OUT.write_text(json.dumps({
            "_doc": "ledger 0099 round 3, item 1b (Mission Gorge Rd's island corrected), tools/make_treefx.py "
                    "scenery.treefx.median_spots: median_planting spots of data/scatter_positions.json by index. drop = not "
                    "planted: the spot stands on pavement, or on a strip's curb ring, since the island was corrected (no median "
                    "between the two noses, a narrow strip beside each turn pocket). Every one is bare on the lidar. No spot is "
                    "moved; the spots kept stand on the new deck where they were. Written by "
                    "source/expansion/mg_median/mg_plants_data.py.",
            "line": LINE, "points_runs": [list(r) for r in runs], "drop": drop, "kept_on_the_new_deck": kept}, indent=1) + "\n", encoding="utf-8")
        print(f"[mg-plants] wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
