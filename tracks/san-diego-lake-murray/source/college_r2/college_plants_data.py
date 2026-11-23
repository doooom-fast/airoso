"""College split, step 4d: THE MEDIAN PLANTS (data only, no Blender). STEP-DESIGN.md has the rules.

    python college_plants_data.py <project dir> [--write]

The median's plants are not in the scene: they are TreeFX bushes from data/scatter_positions.json `median_planting`
(the draft's own spots on every island), each drawn at its lidar height where the lidar sees a plant
(source/vegetation/median_heights.lidar.json, the same spots in the same order; Kevin 2026-11-18 "B: lidar height each",
2026-11-22 "Keep all 33 at their lidar heights").

For every spot on rows CUT0-2..CUT1+2 of the built line, within the old island:
  where it stands NOW          the bank / southbound pavement / northbound pavement / fork pavement / an island that stays
  measured (lidar >= min_h_m)  on the bank or an island: KEPT at its place and height, its foot put on the bank's top
                               on pavement: LISTED for the Mac (never moved or dropped here)
  not measured (bare lidar)    on pavement: DROPPED
                               on the bank or an island: kept as on every other median (the Mac, 2026-11-23), its foot
                               on the bank's top
Nothing new is planted here: the bank's real planting comes from the lidar's plant tops (a G10 job).

NEITHER DATA FILE IS REWRITTEN (the Mac, 2026-11-23): the drops and the new foot heights are DECLARED, as
track.config.json scenery.treefx.median_spots {"drop": [...], "foot_y": [...]}, each entry with the spot's index, its
own x / z (tools/make_treefx.py refuses a list made for other spots), its station, where it stands and why. So every
other median spot keeps its index and with it its model, size and angle.

Without --write: the report (college_plants.report.json) and the declaration (college_plants.median_spots.json) beside
this file. With --write: the declaration also goes into the PROJECT's own track.config.json (a scratch workshop)."""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
proj = Path(sys.argv[1])
WRITE = "--write" in sys.argv[2:]
S = json.loads((HERE / "college_split.data.json").read_text(encoding="utf-8"))
R, F = S["rows"], S["frame"]
FV0 = F["from_v"]
A0, A1 = S["mainline"]["from_v"], S["mainline"]["to_v"]
NOSE, TAIL = R["v"][0], R["v"][-1]
K = {v: k for k, v in enumerate(R["v"])}
O = R["offsets_m"]
CUT0, CUT1, NOSE_VERTS = 1116, 1476, 3            # college_middle_blend.py's
ISLAND_HALF, NOSE_HALF = 3.5, 0.25
CURB_H, DECK_INSET = 0.18, 0.22
LIFT = 0.10


def pre(p):
    b = p.with_name(p.name + ".pre-split")
    return b if b.exists() else p


sp_path = proj / "data" / "scatter_positions.json"
mh_path = proj / "source" / "vegetation" / "median_heights.lidar.json"
if not mh_path.exists():
    raise SystemExit(f"{mh_path} is not in the project (the chain syncs it in from airoso)")
SP = json.loads(pre(sp_path).read_text(encoding="utf-8"))
MH = json.loads(pre(mh_path).read_text(encoding="utf-8"))
spots, heights = SP["median_planting"], MH["spots"]
if len(spots) != len(heights):
    raise SystemExit(f"{len(spots)} median spots but {len(heights)} heights")
MIN_H = float(MH["min_h_m"])
TALL_M = 10.0                                      # the 33 "tall median plants" are the lidar bin 10 m and over


def locate(x, z):
    """nearest row of the built line, the offset (+ west), the fraction toward the next row along the road, the distance"""
    i = min(range(len(F["x"])), key=lambda j: (F["x"][j] - x) ** 2 + (F["z"][j] - z) ** 2)
    dx, dz = x - F["x"][i], z - F["z"][i]
    off = dx * F["nx"][i] + dz * F["nz"][i]
    al = dx * F["nz"][i] - dz * F["nx"][i]
    i2 = max(0, min(len(F["x"]) - 1, i + (1 if al >= 0 else -1)))
    seg = math.hypot(F["x"][i2] - F["x"][i], F["z"][i2] - F["z"][i]) or 1.0
    return i + FV0, off, i2 + FV0, min(1.0, abs(al) / seg), math.hypot(dx, dz)


def lerp_row(v, v2, t, f):
    a, b = f(v), f(v2)
    return a if b is None else a + (b - a) * t


def taper_half(v):
    for j in range(NOSE_VERTS):
        if v in (CUT0 - j, CUT1 + j):
            return NOSE_HALF + (ISLAND_HALF - NOSE_HALF) * j / NOSE_VERTS
    return None


rows = []
for n, (e, h) in enumerate(zip(spots, heights)):
    if abs(e["x"] - h[0]) > 0.006 or abs(e["z"] - h[1]) > 0.006:
        raise SystemExit(f"spot {n}: the two files disagree on its place")
    v, off, v2, t, dist = locate(e["x"], e["z"])
    if dist > 30.0 or not CUT0 - NOSE_VERTS + 1 <= v <= CUT1 + NOSE_VERTS - 1 or abs(off) > ISLAND_HALF + 0.1:
        continue
    lidar_h = h[2]
    measured = lidar_h is not None and lidar_h >= MIN_H
    new_y = None
    if v in K and v2 in K and NOSE < v < TAIL:
        sbe = lerp_row(v, v2, t, lambda q: O["sb_east"][K[q]])
        nbw = lerp_row(v, v2, t, lambda q: O["nb_west"][K[q]])
        if off >= sbe:
            where = "southbound pavement"
        elif off <= nbw:
            where = "northbound pavement"
        else:
            where = "the bank"
            ye = lerp_row(v, v2, t, lambda q: R["nb_west"][K[q]][1]) + CURB_H
            yw = lerp_row(v, v2, t, lambda q: R["sb_east"][K[q]][1]) + CURB_H
            lo, hi = nbw + DECK_INSET, sbe - DECK_INSET
            u = 0.5 if hi - lo < 1e-6 else max(0.0, min(1.0, (off - lo) / (hi - lo)))
            new_y = ye + (yw - ye) * u
    elif CUT0 < v < CUT1:
        where = "fork pavement"
    else:
        th = taper_half(v)
        where = "an island that stays" if th is None or abs(off) <= th - DECK_INSET else "pavement beside a new island nose"
    paved = "pavement" in where
    fate = ("LISTED for the Mac" if measured else "dropped") if paved else "kept"
    rows.append({"index": n, "v": v, "station_m": round(F["s_m"][v - FV0], 1), "offset_m": round(off, 2), "x": e["x"], "z": e["z"],
                 "lidar_h_m": lidar_h, "crown_m": h[3], "measured": measured, "tall": bool(measured and lidar_h >= TALL_M),
                 "where": where, "fate": fate, "y_old": e["y"], "y_new": None if new_y is None else round(new_y, 3)})


def count(pred):
    return sum(1 for r in rows if pred(r))


by_where = {}
for r in rows:
    key = f"{r['where']} / {'measured' if r['measured'] else 'not measured'} / {r['fate']}"
    by_where[key] = by_where.get(key, 0) + 1
tall_all = sum(1 for h in heights if h[2] is not None and h[2] >= TALL_M)
rep = {
    "what": "College split: the median plants on rows v%d..v%d (college_plants_data.py)" % (CUT0 - NOSE_VERTS + 1, CUT1 + NOSE_VERTS - 1),
    "spots_on_the_track": len(spots), "spots_on_these_rows": len(rows), "by_place_and_fate": dict(sorted(by_where.items())),
    "dropped": count(lambda r: r["fate"] == "dropped"), "kept": count(lambda r: r["fate"] == "kept"),
    "kept_measured": count(lambda r: r["fate"] == "kept" and r["measured"]),
    "kept_not_measured": count(lambda r: r["fate"] == "kept" and not r["measured"]),
    "listed_for_the_mac": [r for r in rows if r["fate"].startswith("LISTED")],
    "planted_new": 0, "planted_new_why": "the lidar's plant tops (lm_shrub.tops.npz) are on the G10, not on this machine: nothing new is planted",
    "tall_plants": {"on_the_track": tall_all, "on_these_rows": count(lambda r: r["tall"]),
                    "where": sorted({r["where"] for r in rows if r["tall"]}),
                    "list": [{k: r[k] for k in ("index", "v", "station_m", "offset_m", "lidar_h_m", "where", "fate")} for r in rows if r["tall"]]},
    "foot_height_change_of_the_kept_bank_plants_m": (lambda d: {"min": round(min(d), 2), "max": round(max(d), 2)} if d else None)(
        [r["y_new"] - r["y_old"] for r in rows if r["fate"] == "kept" and r["y_new"] is not None]),
    "spots": rows,
}
(HERE / "college_plants.report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in rep.items() if k != "spots"}, indent=1))

decl = {
    "_doc": "ledger 0055 round 2 (the College split), tools/make_treefx.py scenery.treefx.median_spots: median_planting spots of "
            "data/scatter_positions.json by index. drop = not planted: the road under its island is gone and it would stand on "
            "pavement (every one of them is bare on the lidar, under %.1f m). foot_y = planted where it is, its foot on the bank's "
            "top (the island it stood on is the bank now). Written by source/college_r2/college_plants_data.py." % MIN_H,
    "drop": [{"index": r["index"], "x": r["x"], "z": r["z"], "station_m": r["station_m"], "v": r["v"], "where": r["where"],
              "why": "bare on the lidar (%s m); stands on %s since the split" % (r["lidar_h_m"], r["where"])}
             for r in rows if r["fate"] == "dropped"],
    "foot_y": [{"index": r["index"], "x": r["x"], "z": r["z"], "y": r["y_new"], "station_m": r["station_m"], "v": r["v"],
                "why": "on the bank; its foot was at %.2f on the old island" % r["y_old"]}
               for r in rows if r["fate"] == "kept" and r["y_new"] is not None],
}
(HERE / "college_plants.median_spots.json").write_text(json.dumps(decl, indent=1), encoding="utf-8")
print(f"declared: {len(decl['drop'])} drops, {len(decl['foot_y'])} foot heights -> college_plants.median_spots.json")

if WRITE:
    cfg_path = proj / "track.config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg.setdefault("scenery", {}).setdefault("treefx", {})["median_spots"] = decl
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"[written] {cfg_path}: scenery.treefx.median_spots")
