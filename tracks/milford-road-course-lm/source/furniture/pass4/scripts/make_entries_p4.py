"""Ledger 0082 pass 4 (Milford 0.1.10): the 2017-lidar roofs west of the NAIP crop that NAIP 2022's west strip (download b)
shows still standing, as far blocks at their measured roof elevation, into ../blocks.json; the config names the file once
(scenery.bespoke.blocks [{"file": ...}]) and its version becomes 0.1.10. Re-runnable.

    python make_entries_p4.py <airoso>
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
P4 = HERE.parent
AIROSO = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[5]
CFG = AIROSO / "tracks/milford-road-course-lm/track.config.json"
MIN_AREA_M2, MIN_FILL = 100, 0.55     # [invented] a smaller or emptier piece is a rooftop unit or a split's sliver, not a block
LIDAR = "3DEP USGS_LPC_MI_31Co_Oakland_2016_LAS_2019, flown 2017-05-03"
SEEN = {r["id"]: r for r in json.loads((P4 / "strip_check.json").read_text())}
VIS = {21: 22, 77: 22, 81: 12}         # pass 3's scripts/vis.py: lap points of 467 with a clear sight line (source/furniture/pass3/cand.json)
NAME = {21: "mpg_far_sw", 77: "mpg_far_w_small", 81: "mpg_nw_complex"}
WHAT = {21: "the building 375 m south-west of the lap (NAIP 2022 west strip: a two-level flat-roofed building)",
        77: "the small building west of the far-west hall (NAIP 2022 west strip: a light-roofed block)",
        81: "the multi-level complex north-west of the employee lot (NAIP 2022 west strip: flat roofs at several levels)"}
TREES = json.loads((AIROSO / "tracks/milford-road-course-lm/source/vegetation/trees.lm.json").read_text())["points"]
LAT0, LON0, ML, MT = 42.56999810653583, -83.66362827905016, 82107.23577351798, 111084.36697075465
TXY = [((p[0] - LON0) * ML, (p[1] - LAT0) * MT) for p in TREES]


def tree_within_1m(ring):
    """a planted TreeFX tree (the vegetation pass's) within 1.0 m of the footprint: tools/make_treefx.py BUILT_BUILDING_CLEAR_M,
    which veg_verify gates. The rectangle overfills its roof there, or the crown is a roof unit: the piece is not built"""
    R = [((a - LON0) * ML, (b - LAT0) * MT) for a, b in ring]
    cx, cy = sum(p[0] for p in R) / 4, sum(p[1] for p in R) / 4
    for x, y in TXY:
        if abs(x - cx) > 80 or abs(y - cy) > 80:
            continue
        inside = False
        for (ax, ay), (bx, by) in zip(R, R[1:] + R[:1]):
            if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
                inside = not inside
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
            if ((x - ax - t * dx) ** 2 + (y - ay - t * dy) ** 2) ** 0.5 < 1.0:
                return True
        if inside:
            return True
    return False


blocks, dropped = [], []
for t in json.loads((P4 / "tiers_p4.json").read_text()):
    if t["area_m2"] < MIN_AREA_M2 or t["fill"] < MIN_FILL:
        dropped.append((t["src"], t["tier"], t["area_m2"], t["fill"], "small or empty"))
        continue
    if tree_within_1m(t["footprint_lonlat"]):
        dropped.append((t["src"], t["tier"], t["area_m2"], t["fill"], "a planted tree within 1 m"))
        continue
    k = sum(1 for b in blocks if b["key"].startswith(NAME[t["src"]]))
    s = SEEN[t["src"]]
    blocks.append({
        "key": f"{NAME[t['src']]}_{k}", "footprint_lonlat": t["footprint_lonlat"], "wall_h_m": t["h50"], "skin": "tiltup",
        "roof": "white", "form": "flat", "off_terrain": True, "roof_z_m": t["roof_z_local_m"],
        "_source": (f"source/furniture/pass4/tiers_p4.json (ledger 0082 pass 4): {WHAT[t['src']]}; roof piece {k} at level {t['tier']}. "
                    f"Footprint = the minimum-area rectangle of its roof cells ({t['area_m2']} m2 of 2 m cells, fill {t['fill']}; +-2 m), off "
                    f"{LIDAR}; roof_z_m {t['roof_z_local_m']} m = its median roof elevation in the scene frame [measured]; wall {t['h50']} m "
                    f"over the lidar ground [measured]. NAIP 2022's strip west of the crop (download b, 2026-11-09) shows it standing "
                    f"(green excess {s.get('green_excess_p50')}, luminance {s.get('lum_p50')}, and by eye). Seen from {VIS[t['src']]} of 467 lap "
                    "points. Skin [invented: no wall is seen from above]; past the built ground: a far block")})
(P4 / "blocks.json").write_text(json.dumps(blocks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
cfg = json.loads(CFG.read_text(encoding="utf-8"))
b = cfg["scenery"]["bespoke"]
FILE = "source/furniture/pass4/blocks.json"
b["blocks"] = [g for g in b["blocks"] if g.get("file") != FILE] + [{"file": FILE, "_source": (
    "ledger 0082 pass 4: the 2017-lidar roofs west of the NAIP crop that NAIP 2022's west strip (Kevin's yes, 2026-11-09) "
    "shows standing; each entry's _source says how (source/furniture/pass4/)")}]
cfg["version"] = "0.1.10"
CFG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
(P4 / "blocks_dropped.json").write_text(json.dumps([dict(zip(("src", "tier", "area_m2", "fill", "why"), d)) for d in dropped], indent=1) + "\n")
print(f"{len(blocks)} blocks -> {FILE}; dropped {len(dropped)}: {dropped}")
