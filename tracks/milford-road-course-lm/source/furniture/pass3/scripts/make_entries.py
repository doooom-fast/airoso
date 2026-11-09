"""Ledger 0082 furniture pass 3 (Milford 0.1.8): write what this pass builds, from the measurements beside this script
(../f1ne_bins.json, ../tiers.json; each written by the scripts here off the vegetation read of the 71 EPT nodes already on
disk, nothing downloaded), into

  ../blocks.json             the site buildings the 2017 lidar measures AND NAIP 2022 still shows (track.config.json names
                             it once: scenery.bespoke.blocks [{"file": ...}], read by tools/author_bespoke_blend.py blocks)
  track.config.json          scenery.bespoke.rails += F1's north-east end (kind screen, its measured height); mpg_plant_a's
                             wall_h_m 11.0 [invented] -> the lidar's roof; version 0.1.8

Re-runnable: the entries it owns are replaced, never duplicated.   python make_entries.py <airoso>
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
P3 = HERE.parent
AIROSO = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[5]
CFG = AIROSO / "tracks/milford-road-course-lm/track.config.json"
LAT0, LON0 = 42.56999810653583, -83.66362827905016          # the centreline's origin (data/centerline.local.json)
phi = math.radians(LAT0)
M_LON = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
M_LAT = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
LIDAR = "3DEP USGS_LPC_MI_31Co_Oakland_2016_LAS_2019, flown 2017-05-03 (the vegetation read of pass 2's 71 EPT nodes)"
F1_NE_END = (-83.6656378, 42.5741073)       # the built f1_nw_screen_ne's first vertex: its north-east end


def ll(e, n):
    return [round(LON0 + e / M_LON, 7), round(LAT0 + n / M_LAT, 7)]


def en(p):
    return ((p[0] - LON0) * M_LON, (p[1] - LAT0) * M_LAT)


# ---- F1's north-east end -------------------------------------------------------------------------------------------
bins = json.loads((P3 / "f1ne_bins.json").read_text())
e0, n0 = en(F1_NE_END)
ne = [b for b in bins if "top90" in b and b["e"] > e0 + 0.5 and b["al"] <= 104]     # past the built end, to the last bin with a structure
assert len(ne) >= 12 and all(b["sd"] < 0.6 for b in ne), ne
pts = [(b["e"], b["nn"]) for b in ne]
sm = [pts[0]] + [tuple(sum(p[k] for p in pts[i - 1:i + 2]) / 3 for k in (0, 1)) for i in range(1, len(pts) - 1)] + [pts[-1]]
line = [list(F1_NE_END)] + [ll(*p) for p in sm]
tops = sorted(b["top90"] for b in ne)
h = round(tops[len(tops) // 2] if len(tops) % 2 else (tops[len(tops) // 2 - 1] + tops[len(tops) // 2]) / 2, 2)
length = sum(math.dist(en(a), en(b)) for a, b in zip(line, line[1:]))
f1_end = {
    "key": "f1_nw_screen_ne_end", "kind": "screen", "auto": True, "height_m": h, "polyline_lonlat": line,
    "_source": (f"source/furniture/pass3/f1ne_bins.json (ledger 0082 pass 3): F1's north-east {length:.0f} m, past pass 2's "
                f"45 m read: the canopy-free 2-6 m returns along F1's own line ({LIDAR}), per 4 m bin the median plan position "
                f"(sd {min(b['sd'] for b in ne):.2f}-{max(b['sd'] for b in ne):.2f} m) and the p90 top; height {h} m = the median of "
                f"{len(ne)} bins' p90 ({tops[0]}-{tops[-1]} m) [measured]; single-pulse tops "
                f"{min(b['single'] for b in ne):.2f}-{max(b['single'] for b in ne):.2f} (opaque, as the built 197 m). NAIP 2022 shows "
                "the light line and its shadow to the same end (e -112, n 485). Panel and thickness as the kind's [invented]"),
}

# ---- the site buildings --------------------------------------------------------------------------------------------
tiers = {(t["src"], t["tier"], t["area_m2"]): t for t in json.loads((P3 / "tiers.json").read_text())}
cand = {c["id"]: c for c in json.loads((P3 / "cand.json").read_text())}


def tier(src, t, area):
    return tiers[(src, t, area)]


BUILD = [
    # key, (src, tier, area), what
    ("mpg_west_bldg_a", (63, 0, 1032), "the white building west of the front straight (NAIP 2022: white roof, a stack at its north end)"),
    ("mpg_west_bldg_b", (40, 1, 6944), "the long plant hall south-west of it, its high main roof (NAIP 2022: white roof, a tank yard to its south-east)"),
    ("mpg_west_bldg_c", (34, 0, 572), "the block south of the hall (NAIP 2022: white roof)"),
    ("mpg_nw_small", (113, 0, 64), "a small white-roofed building north of the employee lot"),
]
blocks = []
for key, k, what in BUILD:
    t = tier(*k)
    c = cand[k[0]]
    sloped = t["h90"] - t["h10"] > 2.0
    blocks.append({
        "key": key, "footprint_lonlat": t["footprint_lonlat"], "wall_h_m": round(t["h50"], 2), "skin": "tiltup", "roof": "white",
        "form": "flat", "off_terrain": True,
        "_source": (f"source/furniture/pass3/tiers.json (ledger 0082 pass 3): {what}. Footprint = the minimum-area rectangle of its "
                    f"roof cells ({t['area_m2']} m2 of 2 m cells, fill {t['fill']}; +-2 m), off {LIDAR}; wall {t['h50']} m = the roof's "
                    f"median height over the lidar ground [measured] (p10 {t['h10']} / p90 {t['h90']} m"
                    + ("; the roof slopes over that range and is built flat at its median [simplified form]" if sloped else "") +
                    f"). NAIP 2022 shows it standing (median green excess {c.get('naip_green')}, luminance {c.get('naip_lum')}: a roof). "
                    f"Seen from {c['vis_lap_pts']} of {c['vis_of']} lap points (scripts/vis.py, the 2017 surface). Walls' skin "
                    "[invented: no wall is seen from above]; roof white as NAIP shows it; past the built ground: a far block")})
(P3 / "blocks.json").write_text(json.dumps(blocks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# ---- the config ----------------------------------------------------------------------------------------------------
cfg = json.loads(CFG.read_text(encoding="utf-8"))
b = cfg["scenery"]["bespoke"]
b["rails"] = [r for r in b["rails"] if r["key"] != f1_end["key"]] + [f1_end]
FILE = "source/furniture/pass3/blocks.json"
b["blocks"] = [g for g in b["blocks"] if g.get("file") != FILE]
plant = next(g for g in b["blocks"] if g.get("key") == "mpg_plant_a")
pa = tier(104, 0, 5748)
plant["wall_h_m"] = round(pa["h50"], 1)
plant["_source"] = ("footprint off NAIP 2022 (source/naip_2022_mrc.jpg on its true extent), read by eye to about 5 m, ground-level "
                    f"backdrop past the built ground; height {plant['wall_h_m']} m = the median roof height over the lidar ground of "
                    f"its southern {pa['area_m2']} m2 that the read reaches (p10 {pa['h10']} / p90 {pa['h90']} m; {LIDAR}) "
                    "[measured, ledger 0082 pass 3; was 11.0 m invented]")
b["blocks"].append({"file": FILE, "_source": "ledger 0082 pass 3: the site buildings west of the front straight the 2017 lidar measures "
                    "and NAIP 2022 still shows, each entry's _source says how (source/furniture/pass3/)"})
cfg["version"] = "0.1.8"
CFG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"F1 NE end: {len(line)} vertices, {length:.1f} m, height {h} m; {len(blocks)} blocks -> {FILE}; plant_a {plant['wall_h_m']} m")
