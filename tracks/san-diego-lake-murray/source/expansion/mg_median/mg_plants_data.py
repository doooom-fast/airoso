"""The median plants that stand on pavement since Mission Gorge Rd's island was corrected (ledger 0099 round 3, items 1b
and 2).

    python -I tracks/san-diego-lake-murray/source/expansion/mg_median/mg_plants_data.py [--write]

data/scatter_positions.json's median_planting spots were drawn on the island as it was declared: one unbroken island
4.5-5.4 m wide. fix_mg_median.py set it to the lidar's faces (the crossing: two islands with no median between their
noses and a narrow strip beside each turn pocket; the J3 end: MD11 on its real line, the openings where they are; and
where it is whole, narrower and off the declared place), so some spots now stand on asphalt. No spot is moved (Kevin 2026-11-18, the spots' places; the Mac
2026-11-23: "plants on new asphalt listed and dropped, none moved"). A spot of the changed stretch (the points the
correction changed, by its nearest point of the islands as they were) is:

  kept     on the new island's deck: within the deck's half width of the island's middle at its nearest point
           (tools/median_island.py: the nose-tapered half width less DECK_INSET);
  dropped  anywhere else: between the noses, on the pavement beside a strip, or on a strip's curb ring (a trunk on the
           ring reaches the race curb strip: ledger 0055 round 2's rule for College).

Written as tools/make_treefx.py's scenery.treefx.median_spots list (drop, by index, each with its own x / z), in a file
of its own beside College's. Each entry carries the lidar's height at the spot (source/vegetation/
median_heights.lidar.json).

A SPOT THE LIDAR SAW A PLANT AT (MIN_H_M or more) IS NEVER DROPPED (the Mac, 2026-11-23: "a real plant the lidar saw is
never dropped because the island moved under it"; Kevin, 2026-11-18: "we've reduced lake murrays center bushes far too
much"). The spots are the draft's own (drawn on the island as it was declared); a spot's height is the canopy in a 1.5 m
square at it, so a real tree whose trunk stands on the real island can read tall at a spot the corrected island no
longer reaches. Such a spot is MOVED (tools/make_treefx.py scenery.treefx.median_spots "move"), by the Mac's two rules:
  (3) where an lm-shrub plant top lies within 2 m of it (TOPS_FILE, read off the G10's tops by the Mac), the spot takes
      the top's own place: a measured place. Where the island was set from the plan's road and not at the lidar's own
      place (fix_mg_median.py, the 50 m bins), the top is carried across by the same shift the island was given there,
      so the plant keeps its place ON its island. Only if that place is on the deck; else rule (2);
  (2) otherwise straight across onto its island's deck, the least distance (to TRUNK_R_M inside the deck's edge, the
      trunk radius verify_race gives a plant), its height and crown kept: an [inferred position].
Where there is no island at all (between two noses) such a spot is FATAL: a plant in what this says is open road means
the gap is wrong. The plants of 10 m and more (Kevin's tall ones) are listed apart in the report."""
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
TRUNK_R_M = 0.3        # tools/verify_race.py G: the trunk radius a plant is given against a lane or a wall
TOP_WITHIN_M = 2.0     # the Mac's rule (3): an lm-shrub top this near a spot is the plant the spot's height came from
TALL_M = 10.0          # "Kevin's tall plants": the heights file's 10 m and over bin (33 of 1,102 spots)
TOPS_FILE = HERE / "mg_plant_tops.g10.json"            # the nearest lm-shrub plant top per listed spot (the Mac, off the G10's tops)


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
    drop, kept, off, move = [], [], [], []
    tops = {}
    if TOPS_FILE.exists():
        for t in json.loads(TOPS_FILE.read_text(encoding="utf-8")).get("spots", []):
            tops[int(t["spot"])] = t
    # the shift the island was given at each station of piece C (fix_mg_median.py), and the piece's own frame
    shifts = (((rec.get("lidar") or {}).get("placement") or {}).get("shift_m_by_station")) or []
    if str(ROOT / "tools") not in sys.path:
        sys.path.insert(0, str(ROOT / "tools"))
    import expansion_pieces as ep
    pc = ep.load(data / "expansion.north.json")[1]["C"]

    def shift_at(st):
        """the shift at the piece's station nearest st (0 where no bin placed the island: the J3 end)"""
        if not shifts or st < shifts[0][0] - 1.25 or st > shifts[-1][0] + 1.25:
            return 0.0
        return min(shifts, key=lambda q: abs(q[0] - st))[1]

    def on_deck(x, z):
        """(point k, lateral, deck half width) of a place against the corrected island, or None where there is none"""
        q = min(range(max(0, a - 6), min(len(P), b + 7)), key=lambda j: math.hypot(x - P[j][0], z - P[j][2]))
        tx_, tz_ = MI.tangent(P, q)
        lat_ = (x - P[q][0]) * (-tz_) + (z - P[q][2]) * tx_
        sg = next(((i0, j0) for i0, j0 in segs if i0 <= q < j0), None)
        if sg is None:
            return None
        return q, lat_, max(0.05, MI.half_width(W, sg[0], sg[1], q) - MI.DECK_INSET)

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
        if h >= min_h and not seg:
            raise SystemExit(f"[mg-plants] spot {i} ({s['x']}, {s['z']}) stands where there is no median ({where}) but the lidar "
                             f"saw a plant {h} m tall there: the gap is wrong, not the plant")
        if h >= min_h:
            entry = {"index": i, "x": s["x"], "z": s["z"], "point": k, "lateral_m": round(lat, 2), "deck_half_m": round(deck, 2),
                     "half_m": round(half, 2), "where": where, "lidar_h_m": h, "lidar_crown_m": lidar["spots"][i][3],
                     "off_the_deck_by_m": round(abs(lat) - deck, 2)}
            off.append(entry)
            to, rule = None, None
            top = (tops.get(i) or {}).get("nearest_plant_top")
            if i in tops and (abs(tops[i]["x"] - s["x"]) > 0.006 or abs(tops[i]["z"] - s["z"]) > 0.006):
                raise SystemExit(f"[mg-plants] {TOPS_FILE.name}: spot {i} is listed at ({tops[i]['x']}, {tops[i]['z']}), not where "
                                 f"scatter_positions.json has it")
            entry["top"] = None
            if top and math.hypot(top["x"] - s["x"], top["z"] - s["z"]) <= TOP_WITHIN_M:
                _d, st_top, _lat = pc.project(float(top["x"]), float(top["z"]))
                sh = shift_at(st_top)
                nl = pc.frame(st_top)[2]
                cx, cz = float(top["x"]) - nl[0] * sh, float(top["z"]) - nl[1] * sh
                hit = on_deck(cx, cz)
                entry["top"] = {"index": int(top["top"]), "x": top["x"], "z": top["z"], "from_the_spot_m": round(math.hypot(top["x"] - s["x"], top["z"] - s["z"]), 2),
                                "h_m": top.get("h"), "crown_m": top.get("crown_d"), "carried_across_m": round(-sh, 2),
                                "on_the_deck": bool(hit and abs(hit[1]) <= max(0.0, hit[2] - TRUNK_R_M))}
                if entry["top"]["on_the_deck"]:
                    to, rule = (round(cx, 3), round(cz, 3)), "(3) the lm-shrub top's own place (measured), carried across with its island"
            if to is None:
                along = (s["x"] - P[k][0]) * tx + (s["z"] - P[k][2]) * tz
                lat2 = math.copysign(max(0.0, deck - TRUNK_R_M), lat)
                to = (round(P[k][0] + tx * along - tz * lat2, 3), round(P[k][2] + tz * along + tx * lat2, 3))
                rule = "(2) straight across onto the deck [inferred position]"
            move.append(dict(entry, to_x=to[0], to_z=to[1], rule=rule, moved_m=round(math.hypot(to[0] - s["x"], to[1] - s["z"]), 2),
                             why=f"the lidar saw a plant {h:.2f} m tall at this spot; the corrected island's deck ends "
                                 f"{abs(lat) - deck:.2f} m short of it"))
            continue
        drop.append({"index": i, "x": s["x"], "z": s["z"], "point": k, "lateral_m": round(lat, 2), "half_m": round(half, 2),
                     "where": where, "why": f"bare on the lidar ({h:.2f} m); stands on {where.split(':')[0]} since the island was corrected"})
    by = {}
    for d in drop:
        by[d["where"]] = by.get(d["where"], 0) + 1
    print(f"[mg-plants] {len(drop) + len(kept)} spots on the islands as they were over points {[list(r) for r in runs]}: {len(kept)} kept on the new deck "
          f"(lidar {min(k['lidar_h_m'] for k in kept):.2f}-{max(k['lidar_h_m'] for k in kept):.2f} m), {len(drop)} dropped {by}; "
          f"every dropped spot is bare on the lidar (under {min_h} m); {len(move)} with a plant on the lidar stand off the deck "
          f"and are moved onto it: {[(m['index'], m['rule'][:3], m['moved_m']) for m in move]}; of those, "
          f"{sum(1 for m in move if m['lidar_h_m'] >= TALL_M)} are {TALL_M:.0f} m or taller")
    if "--write" in argv:
        OUT.write_text(json.dumps({
            "_doc": "ledger 0099 round 3, item 1b (Mission Gorge Rd's island corrected), tools/make_treefx.py "
                    "scenery.treefx.median_spots: median_planting spots of data/scatter_positions.json by index. drop = not "
                    "planted: the spot stands on pavement, or on a strip's curb ring, since the island was corrected (no median "
                    "between the two noses, a narrow strip beside each turn pocket). Every one is bare on the lidar. No spot is "
                    "moved; the spots kept stand on the new deck where they were. Written by "
                    "source/expansion/mg_median/mg_plants_data.py.",
            "line": LINE, "points_runs": [list(r) for r in runs], "drop": drop, "kept_on_the_new_deck": kept,
            "move": move,
            "_move_doc": "spots the lidar saw a plant at that the corrected island's deck no longer reaches (the spot is the "
                         "draft's, drawn on the declared island; the real plant stands on the real one). Never dropped (the Mac, "
                         "2026-11-23). Rule (3): the G10's lm-shrub top within 2 m, where it is on the deck: its own place. Rule "
                         "(2): straight across onto the deck, 0.3 m inside its edge: an inferred position",
            "tall_plants_moved": [{"index": m["index"], "lidar_h_m": m["lidar_h_m"], "rule": m["rule"], "moved_m": m["moved_m"]}
                                  for m in move if m["lidar_h_m"] >= TALL_M],
            "tops_file": TOPS_FILE.name if TOPS_FILE.exists() else None},
            indent=1) + "\n", encoding="utf-8")
        print(f"[mg-plants] wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
