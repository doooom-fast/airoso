"""College split, step 4d: THE PLANTS BETWEEN THE TWO ROADS (data only, no Blender). STEP-DESIGN.md has the rules.

    python college_plants_data.py <project dir> [--write]

Two layers, both TreeFX data (nothing here is in the scene):

1. THE MEDIAN SPOTS the draft planted on the old island: data/scatter_positions.json `median_planting`, each drawn at
   its lidar height where the lidar sees a plant (source/vegetation/median_heights.lidar.json, the same spots in the
   same order; Kevin 2026-11-18 "B: lidar height each", 2026-11-22 "Keep all 33 at their lidar heights").
   For every spot on rows CUT0-2..CUT1+2 of the built line, within the old island:
     where it stands NOW          the bank / southbound pavement / northbound pavement / fork pavement / an island that stays
     measured (lidar >= min_h_m)  on the bank or an island: KEPT at its place and height, its foot put on the bank's top
                                  on pavement: LISTED for the Mac (never moved or dropped here)
     not measured (bare lidar)    on pavement: DROPPED
                                  on the bank: DROPPED (the Mac, 2026-11-23, once the bank had measured plants: "the bank
                                  planted from measured tops"); on an island that stays: kept as on every other median
   NEITHER DATA FILE IS REWRITTEN (the Mac, 2026-11-23): the drops and the new foot heights are DECLARED, as
   track.config.json scenery.treefx.median_spots {"drop": [...], "foot_y": [...]}, each entry with the spot's index, its
   own x / z (tools/make_treefx.py refuses a list made for other spots), its station, where it stands and why.

2. THE BANK'S OWN PLANTS, off the 2024 lidar: college_bank_tops.g10.json (the G10, 2026-11-23: every plant top of the
   lm-shrub job between the two carriageways, rows v1172-1444). Per top, in this order:
     not a plant (the job's own `solid` flag)                       -> not planted, listed
     not on the bank's grass top as BUILT (the built inner edges are smoother than the lidar's: on a road, on the
       curb ring, or off the rows that have a bank)                 -> not planted, LISTED (never moved)
     within SAME_PLANT_M of a kept measured median spot             -> it IS that plant: not planted twice
     a tree (h >= SPLIT_H_M) with a tree of the planner's within its crown radius -> already planted: stays as it is
     else                                                           -> PLANTED where it stands, at its own height and crown
   A top under SPLIT_H_M is a shrub (the median's bush mix), one at or over it a tree (Lake Murray's `trees` mix): the
   lidar cannot tell species. Declared as scenery.treefx.lidar_plants (tools/make_treefx.py), the list in
   college_bank_plants.json beside this file.

Without --write: the report, the two lists and the lidar_plants config entry beside this file. With --write the two
lists are also copied to <project>/source/college_r2/ (a scratch workshop; in the chain ship.json's sync_in brings them).
The config's own keys are written by college_race_config.py."""
import json
import math
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
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
SAME_PLANT_M = 2.0                                # the Mac, 2026-11-23: "a measured top within 2 m of one ... IS that plant"
SPLIT_H_M = 4.0                                   # [invented] see SPLIT_DOC: written into the config entry, never a default
SPLIT_DOC = ("[invented] the lm-shrub tool's own fallback (shrub_heights.py: `cut = split if split is not None else 4.0`). The 2024 "
             "lidar shows no shrub / tree valley at Lake Murray: the job's out_24tiles/lm_shrub.summary.json (md5 "
             "5d9e08b708e591e1b67c7ffe7fbbae41, written 2026-11-16; tops npz md5 e722d5daa98c540f05ded2f854a1ca92) has "
             "shrub_tree_split_m.antimode_natural = null: the natural tops' log10 histogram runs flat at 6,000-10,000 a bin "
             "from 1.5 to 8 m, peaking near 3.8 m, and the tool's antimode() wants a valley under 0.8 of both peaks. Every "
             "trees_over_split count in that summary uses 4.0, so the bank is split as the summary's strata are (read on the "
             "G10 by the Mac, 2026-11-23).")
PLANTS_FILE = "source/college_r2/college_bank_plants.json"      # project-relative: where the planner reads the list
TREE_ZONE_WORDS = ("tree", "palm", "gum_belt")    # the planner's zones that stand trees (tools/make_treefx.py ZONES)


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


def on_the_split(v, v2, t, off):
    """(where, the bank top's height there or None) for a point on rows that have two roads, else (None, None)"""
    if not (v in K and v2 in K and NOSE < v < TAIL):
        return None, None
    sbe = lerp_row(v, v2, t, lambda q: O["sb_east"][K[q]])
    nbw = lerp_row(v, v2, t, lambda q: O["nb_west"][K[q]])
    if off >= sbe:
        return "southbound pavement", None
    if off <= nbw:
        return "northbound pavement", None
    lo, hi = nbw + DECK_INSET, sbe - DECK_INSET
    if not lo < off < hi:
        return "the bank's curb", None
    ye = lerp_row(v, v2, t, lambda q: R["nb_west"][K[q]][1]) + CURB_H
    yw = lerp_row(v, v2, t, lambda q: R["sb_east"][K[q]][1]) + CURB_H
    return "the bank", ye + (yw - ye) * (off - lo) / (hi - lo)


# ============================================================================================ 1. the median spots
rows = []
for n, (e, h) in enumerate(zip(spots, heights)):
    if abs(e["x"] - h[0]) > 0.006 or abs(e["z"] - h[1]) > 0.006:
        raise SystemExit(f"spot {n}: the two files disagree on its place")
    v, off, v2, t, dist = locate(e["x"], e["z"])
    if dist > 30.0 or not CUT0 - NOSE_VERTS + 1 <= v <= CUT1 + NOSE_VERTS - 1 or abs(off) > ISLAND_HALF + 0.1:
        continue
    lidar_h = h[2]
    measured = lidar_h is not None and lidar_h >= MIN_H
    where, new_y = on_the_split(v, v2, t, off)
    on_curb = None
    if where == "the bank's curb":                 # a spot inside the curb ring's width stands on the bank (as step 4d had it)
        where = "the bank"
        sbe = lerp_row(v, v2, t, lambda q: O["sb_east"][K[q]])
        nbw = lerp_row(v, v2, t, lambda q: O["nb_west"][K[q]])
        ye = lerp_row(v, v2, t, lambda q: R["nb_west"][K[q]][1]) + CURB_H
        yw = lerp_row(v, v2, t, lambda q: R["sb_east"][K[q]][1]) + CURB_H
        lo, hi = nbw + DECK_INSET, sbe - DECK_INSET
        u = 0.5 if hi - lo < 1e-6 else max(0.0, min(1.0, (off - lo) / (hi - lo)))
        new_y = ye + (yw - ye) * u
        on_curb = {"edge": "southbound" if sbe - off < off - nbw else "northbound", "from_the_edge_m": round(min(sbe - off, off - nbw), 2)}
    if where is None:
        if CUT0 < v < CUT1:
            where = "fork pavement"
        else:
            th = taper_half(v)
            where = "an island that stays" if th is None or abs(off) <= th - DECK_INSET else "pavement beside a new island nose"
    paved = "pavement" in where
    why = None
    if paved:
        fate = "LISTED for the Mac" if measured else "dropped"
        why = None if measured else "bare on the lidar (%s m); stands on %s since the split" % (lidar_h, where)
    elif where == "the bank" and not measured:
        fate, why = "dropped", "bare on the lidar (%s m); the bank planted from measured tops (ledger 0055)" % (lidar_h,)
    else:
        fate = "kept"
    rows.append({"index": n, "v": v, "station_m": round(F["s_m"][v - FV0], 1), "offset_m": round(off, 2), "x": e["x"], "z": e["z"],
                 "lidar_h_m": lidar_h, "crown_m": h[3], "measured": measured, "tall": bool(measured and lidar_h >= TALL_M),
                 "where": where, "fate": fate, "why": why, "on_curb": on_curb, "y_old": e["y"],
                 "y_new": None if new_y is None else round(new_y, 3)})

# A MEASURED spot on the bank's CURB RING (inside DECK_INSET of a built inner edge): nothing grows out of a curb, and its
# trunk reaches into the race curb strip along that edge (tools/verify_race.py G refused spot 208 by 0.03 m on the
# scratch workshop, 2026-11-23). Where the lidar's own top of that plant (within SAME_PLANT_M) stands on the bank's
# grass top, the TOP is planted (section 2) and the spot is dropped. One of Kevin's tall plants is never dropped here,
# and a spot with no such top stays: both are listed (on_the_curb_ring) for the Mac.
TJ = json.loads((HERE / "college_bank_tops.g10.json").read_text(encoding="utf-8"))


def top_on_the_bank(q):
    v_, off_, v2_, t_, _d = locate(q["x"], q["z"])
    return on_the_split(v_, v2_, t_, off_)[0] == "the bank"


curb_listed = []
for r in rows:
    if not (r["on_curb"] and r["fate"] == "kept" and r["measured"]):
        continue
    own = sorted((math.hypot(q["x"] - r["x"], q["z"] - r["z"]), q["npz_index"]) for q in TJ["tops"]
                 if q["plant"] and math.hypot(q["x"] - r["x"], q["z"] - r["z"]) <= SAME_PLANT_M and top_on_the_bank(q))
    if r["tall"] or not own:
        curb_listed.append({k: r[k] for k in ("index", "v", "station_m", "offset_m", "lidar_h_m", "tall", "on_curb")})
        continue
    r["fate"] = "dropped"
    r["why"] = ("on the bank's curb ring, %.2f m from the %s road's inner edge (its trunk would reach into the race curb strip "
                "there: tools/verify_race.py G); the lidar's own top %d, %.2f m away on the bank's grass, is planted in its place"
                % (r["on_curb"]["from_the_edge_m"], r["on_curb"]["edge"], own[0][1], own[0][0]))


def count(pred):
    return sum(1 for r in rows if pred(r))


by_where = {}
for r in rows:
    key = f"{r['where']} / {'measured' if r['measured'] else 'not measured'} / {r['fate']}"
    by_where[key] = by_where.get(key, 0) + 1
tall_all = sum(1 for h in heights if h[2] is not None and h[2] >= TALL_M)
decl = {
    "_doc": "ledger 0055 round 2 (the College split), tools/make_treefx.py scenery.treefx.median_spots: median_planting spots of "
            "data/scatter_positions.json by index. drop = not planted: either the road under its island is gone and it would stand "
            "on pavement (every one of those is bare on the lidar, under %.1f m), or it is a bare spot on the bank, which is "
            "planted from the lidar's measured tops instead (scenery.treefx.lidar_plants), or it is a measured spot on the "
            "bank's curb ring whose own measured top is planted in its place. foot_y = planted where it is, its "
            "foot on the bank's top (the island it stood on is the bank now). Written by source/college_r2/college_plants_data.py." % MIN_H,
    "drop": [{"index": r["index"], "x": r["x"], "z": r["z"], "station_m": r["station_m"], "v": r["v"], "where": r["where"],
              "why": r["why"]}
             for r in rows if r["fate"] == "dropped"],
    "foot_y": [{"index": r["index"], "x": r["x"], "z": r["z"], "y": r["y_new"], "station_m": r["station_m"], "v": r["v"],
                "why": "on the bank; its foot was at %.2f on the old island" % r["y_old"]}
               for r in rows if r["fate"] == "kept" and r["y_new"] is not None],
}

# ====================================================================================== 2. the bank's measured tops
kept_spots = [r for r in rows if r["fate"] == "kept" and r["measured"] and r["where"] == "the bank"]

# the trees the planner places today (the lidar_plants entry left out: it is what this writes)
sys.path.insert(0, str(ROOT / "tools"))
import make_treefx as MT  # noqa: E402
import patch_median_measured as PM  # noqa: E402

cfg_path = proj / "track.config.json"
cfg_now = json.loads(cfg_path.read_text(encoding="utf-8"))
had = (cfg_now.get("scenery", {}).get("treefx") or {}).pop("lidar_plants", None)
if had is not None:                                 # plan the trees as they are without this tool's own list
    cfg_path.write_text(json.dumps(cfg_now, indent=2), encoding="utf-8")
try:
    planned = MT.plan(proj)["entries"]
finally:
    if had is not None:
        cfg_now["scenery"]["treefx"]["lidar_plants"] = had
        cfg_path.write_text(json.dumps(cfg_now, indent=2), encoding="utf-8")
planner_trees = [e for e in planned if any(w in e["zone"] for w in TREE_ZONE_WORDS)]

tops, plants = [], []
for q in TJ["tops"]:
    v, off, v2, t, dist = locate(q["x"], q["z"])
    rec = {"key": q["npz_index"], "v": v, "station_m": round(F["s_m"][v - FV0], 1), "offset_m": round(off, 2), "x": q["x"], "z": q["z"],
           "h_m": q["h_m"], "crown_m": q["crown_d_m"], "kind": "tree" if q["h_m"] >= SPLIT_H_M else "shrub"}
    where, y = on_the_split(v, v2, t, off)
    rec["where"] = where or "off the rows that have a bank (a nose)"
    if not q["plant"]:
        rec["fate"] = "not a plant (solid on the lidar)"
    elif where != "the bank":
        rec["fate"] = "LISTED: not on the bank's grass top as built"
    else:
        near = min(kept_spots, key=lambda r: math.hypot(r["x"] - q["x"], r["z"] - q["z"]), default=None)
        d_spot = math.hypot(near["x"] - q["x"], near["z"] - q["z"]) if near else None
        tree_hit = None
        if rec["kind"] == "tree":
            for e in planner_trees:
                d = math.hypot(e["x"] - q["x"], e["z"] - q["z"])
                if d <= q["crown_d_m"] / 2.0 and (tree_hit is None or d < tree_hit[0]):
                    tree_hit = (d, e)
        if d_spot is not None and d_spot <= SAME_PLANT_M:
            rec["fate"] = "is median spot %d (%s)" % (near["index"], "one of Kevin's 14 tall" if near["tall"] else "measured, under 10 m")
            rec["spot"], rec["spot_dist_m"], rec["spot_tall"] = near["index"], round(d_spot, 2), near["tall"]
        elif tree_hit is not None:
            rec["fate"] = "already planted: %s %s %.2f m away" % (tree_hit[1]["zone"], tree_hit[1]["model"], tree_hit[0])
        else:
            rec["fate"] = "planted"
            rec["y"] = round(y, 3)
            plants.append({"key": q["npz_index"], "x": q["x"], "z": q["z"], "y": round(y, 3), "h_m": q["h_m"], "crown_m": q["crown_d_m"],
                           "v": v, "station_m": rec["station_m"], "offset_m": rec["offset_m"]})
    tops.append(rec)

spot_tops = {}
for r in tops:
    if "spot" in r:
        spot_tops.setdefault(r["spot"], []).append(r["key"])
no_top = [{"index": r["index"], "v": r["v"], "tall": r["tall"], "lidar_h_m": r["lidar_h_m"],
           "nearest_top_m": round(min(math.hypot(q["x"] - r["x"], q["z"] - r["z"]) for q in TJ["tops"]), 2)}
          for r in kept_spots if r["index"] not in spot_tops]


def tcount(pred):
    return sum(1 for r in tops if pred(r))


native = {}
models_dir = proj / "source" / "trees"
for zone in ("median_planting", "trees"):
    for s in MT.ZONES[zone]:
        if (models_dir / s[0]).exists() or (models_dir / s[0][:-4]).is_dir():
            native[s[0]] = PM.tree_ini(models_dir, s[0])
missing = sorted({s[0] for zone in ("median_planting", "trees") for s in MT.ZONES[zone]} - set(native))
entry = {
    "_doc": "ledger 0055 round 2 (the College split), tools/make_treefx.py scenery.treefx.lidar_plants: the plants the 2024 lidar "
            "measured on the bank between College's two roads (source/college_r2/college_bank_tops.g10.json, the G10's job "
            "lm-college-bank-20261123), each where it stands at its own height and crown. The list is written by "
            "source/college_r2/college_plants_data.py, which leaves out a top that is no plant, one not on the bank's grass top as "
            "built, one within %.1f m of a kept measured median spot (it IS that plant) and a tree the planner already stands within "
            "its crown radius. The lidar cannot tell species: a shrub takes the median's bush mix, a tree Lake Murray's `trees` mix." % SAME_PLANT_M,
    "file": PLANTS_FILE,
    "split_h_m": SPLIT_H_M,
    "_split_doc": SPLIT_DOC,
    "shrubs": "median_planting",
    "trees": "trees",
    "native_h_m": {m: native[m]["HEIGHT"] for m in sorted(native)},
    "native_w_m": {m: native[m]["WIDTH"] for m in sorted(native)},
    "_native_doc": "each model's tree.ini [BASIC] HEIGHT / WIDTH, read off the models in <project>/source/trees by "
                   "source/college_r2/college_plants_data.py (tools/patch_median_measured.tree_ini) on the PC, 2026-11-23",
}
plist = {"_doc": "ledger 0055 round 2: the College bank's plants, read by tools/make_treefx.py (scenery.treefx.lidar_plants). key = the "
                 "top's index in the lm-shrub job's lm_shrub.tops.npz; x, z = the engine frame; y = the bank top's height there as "
                 "built (TreeFX seats each plant on the ground under it); h_m, crown_m = measured (college_bank_tops.g10.json). "
                 "Written by college_plants_data.py: do not edit by hand.",
         "plants": plants}

rep = {
    "what": "College split: the plants between the two roads on rows v%d..v%d (college_plants_data.py)" % (CUT0 - NOSE_VERTS + 1, CUT1 + NOSE_VERTS - 1),
    "median_spots": {
        "spots_on_the_track": len(spots), "spots_on_these_rows": len(rows), "by_place_and_fate": dict(sorted(by_where.items())),
        "dropped": count(lambda r: r["fate"] == "dropped"),
        "dropped_on_pavement": count(lambda r: r["fate"] == "dropped" and "pavement" in r["where"]),
        "dropped_bare_on_the_bank": count(lambda r: r["fate"] == "dropped" and r["where"] == "the bank" and not r["measured"]),
        "dropped_measured_on_the_curb_ring": [{"index": r["index"], "v": r["v"], "lidar_h_m": r["lidar_h_m"], "why": r["why"]}
                                              for r in rows if r["fate"] == "dropped" and r["measured"]],
        "on_the_curb_ring_listed": curb_listed,
        "kept": count(lambda r: r["fate"] == "kept"),
        "kept_measured": count(lambda r: r["fate"] == "kept" and r["measured"]),
        "kept_not_measured": count(lambda r: r["fate"] == "kept" and not r["measured"]),
        "listed_for_the_mac": [r for r in rows if r["fate"].startswith("LISTED")],
        "tall_plants": {"on_the_track": tall_all, "on_these_rows": count(lambda r: r["tall"]),
                        "where": sorted({r["where"] for r in rows if r["tall"]}),
                        "list": [{k: r[k] for k in ("index", "v", "station_m", "offset_m", "lidar_h_m", "where", "fate")} for r in rows if r["tall"]]},
        "foot_height_change_of_the_kept_bank_plants_m": (lambda d: {"min": round(min(d), 2), "max": round(max(d), 2)} if d else None)(
            [r["y_new"] - r["y_old"] for r in rows if r["fate"] == "kept" and r["y_new"] is not None]),
    },
    "bank_tops": {
        "source": "college_bank_tops.g10.json (%d tops, %s)" % (len(TJ["tops"]), TJ["source"]["flown"]),
        "split_h_m": SPLIT_H_M, "split": SPLIT_DOC, "same_plant_m": SAME_PLANT_M,
        "tops": len(tops),
        "planted": len(plants),
        "planted_as_trees": sum(1 for p in plants if p["h_m"] >= SPLIT_H_M),
        "planted_as_shrubs": sum(1 for p in plants if p["h_m"] < SPLIT_H_M),
        "planted_h_m": (lambda hs: {"min": min(hs), "median": sorted(hs)[len(hs) // 2], "max": max(hs)} if hs else None)([p["h_m"] for p in plants]),
        "matched_to_a_tree_the_planner_places": tcount(lambda r: r["fate"].startswith("already planted")),
        "planner_trees_compared": len(planner_trees),
        "matched_to_kevins_14_tall": {"tops": tcount(lambda r: r.get("spot_tall") is True),
                                      "spots_with_a_top": sum(1 for r in kept_spots if r["tall"] and r["index"] in spot_tops),
                                      "spots": sum(1 for r in kept_spots if r["tall"])},
        "matched_to_the_other_measured_spots": {"tops": tcount(lambda r: r.get("spot_tall") is False),
                                                "spots_with_a_top": sum(1 for r in kept_spots if not r["tall"] and r["index"] in spot_tops),
                                                "spots": sum(1 for r in kept_spots if not r["tall"])},
        "kept_spots_with_no_top_within_reach": no_top,
        "not_a_plant": [{k: r[k] for k in ("key", "v", "offset_m", "h_m")} for r in tops if r["fate"].startswith("not a plant")],
        "listed_not_on_the_bank_as_built": {
            "count": tcount(lambda r: r["fate"].startswith("LISTED")),
            "by_place": (lambda c: dict(sorted(c.items())))(
                {w: tcount(lambda r, w=w: r["fate"].startswith("LISTED") and r["where"] == w) for w in {r["where"] for r in tops if r["fate"].startswith("LISTED")}}),
            "of_them_trees": tcount(lambda r: r["fate"].startswith("LISTED") and r["kind"] == "tree"),
            "list": [{k: r[k] for k in ("key", "v", "station_m", "offset_m", "h_m", "crown_m", "kind", "where")} for r in tops if r["fate"].startswith("LISTED")]},
        "models_with_no_tree_ini_here": missing,
    },
    "exclusion_list": {"drop": len(decl["drop"]), "foot_y": len(decl["foot_y"])},
    "spots": rows,
    "tops": tops,
}
(HERE / "college_plants.report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
short = {"median_spots": {k: v for k, v in rep["median_spots"].items() if k not in ("listed_for_the_mac", "tall_plants")},
         "bank_tops": {k: (v if k != "listed_not_on_the_bank_as_built" else {kk: vv for kk, vv in v.items() if kk != "list"})
                       for k, v in rep["bank_tops"].items() if k != "split"},
         "exclusion_list": rep["exclusion_list"]}
print(json.dumps(short, indent=1))
(HERE / "college_plants.median_spots.json").write_text(json.dumps(decl, indent=1), encoding="utf-8")
(HERE / "college_bank_plants.json").write_text(json.dumps(plist, indent=1), encoding="utf-8")
if missing:
    print(f"NOT WRITTEN: the config entry (college_bank_plants.lidar_plants.json): no tree.ini here for {missing}")
else:
    (HERE / "college_bank_plants.lidar_plants.json").write_text(json.dumps(entry, indent=1), encoding="utf-8")
print(f"declared: {len(decl['drop'])} drops, {len(decl['foot_y'])} foot heights -> college_plants.median_spots.json; "
      f"{len(plants)} plants -> college_bank_plants.json")

if WRITE:
    # the two lists go beside the project's other sources, where the planner reads them; the config's own keys
    # (scenery.treefx.median_spots / lidar_plants) are college_race_config.py's to write
    for name in ("college_plants.median_spots.json", "college_bank_plants.json"):
        dst = proj / "source" / "college_r2" / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HERE / name, dst)
        print(f"[written] {dst}")
