"""Ledger 0082 vegetation pass, step 2: the stands, the planting and the grass zones, from veg_crowns.py's crowns.

    python veg_plan.py <veg.npz> <crowns dir> <built track.obj> <track dir>

Writes into <track dir>/source/vegetation/:
  trees.lm.json     the planted points, make_treefx's `planted` grammar: [lon, lat, zone, h_m, crown_m] per tree
  trunks.json       the trees within COLLIDER_REACH_M of the drivable surface: [lon, lat, h_m, d_paved_m] (colliders)
  grass_classes.png the measured ground class per 2 m cell, north-up on grass_classes.json's bbox, coded for
                    tools/plan_grassfx_aerial.py (C wood floor, B long grass, D no grass: pavement or gravel under the ground)
  inventory.json    the stands, the counts, every flag (lidar vs NAIP), the rules and where each number came from
  overview.jpg      the lot drawn: planted crowns, flags, colliders, grass classes

WHAT IS PLANTED (each rule's source beside it)
  - a crown the 2017 lidar measures at 5 m or more (veg_crowns.TREE_MIN_M, FAO's tree);
  - on the read's resolvable coverage (veg_crowns.COVER_MIN_PER_M2);
  - over the built ground (the 0.1.2 gate OBJ's 1GRASS extent, 5 m in);
  - NOT gone by 2022: NAIP 2022 still shows canopy over it (veg_crowns.GONE_SHARE), where NAIP reaches;
  - its trunk (the crown's top) at least the drive corridor's margin (track.config.json scenery.corridor_margin_m) from
    any paved surface of the build (1ROAD, 1KERB, PADAPRON), plus half a cell's diagonal for the 2 m grid;
  - at least make_treefx's BUILT_BUILDING_CLEAR_M (1.0 m) from any wall or building of the build, plus the same.
Its height is the crown's measured top; its crown width the crown's measured area.
"""
import json, math, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
from veg_common import Frame, naip_features, obj_surfaces  # noqa: E402

COLLIDER_REACH_M = 30.0   # [invented] a car off the road at speed reaches this far before it stops; trees nearer get a trunk
HALF_DIAG_M = math.sqrt(2.0)   # half a 2 m cell's diagonal: the grid's own position error
CLEAR_BUILT_M = 1.0       # tools/make_treefx.py BUILT_BUILDING_CLEAR_M
ZONE_HARDWOOD = 1         # every planted tree: the deciduous hardwood mix (track.config.json scenery.treefx.planted.zones)
STAND_MIN_HA = 0.25
# the grass classes, coded so tools/plan_grassfx_aerial.py's colour rules read them back exactly (track.config.json)
CODE = {"C": (0, 120, 0), "B": (200, 200, 0), "D": (0, 0, 200), "base": (255, 255, 255), "none": (255, 255, 255)}
B_RULE = {"mean": (140, 215), "g_over_r": (0.0, 1.0), "g_over_b": (1.15, 9.0)}    # 0.1.0's own long-grass rule off NAIP


def main():
    veg = np.load(sys.argv[1])
    cdir, obj, track = Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
    outd = track / "source" / "vegetation"
    cfg = json.loads((track / "track.config.json").read_text(encoding="utf-8"))
    corridor = float(cfg["scenery"]["corridor_margin_m"])
    c = np.load(cdir / "crowns.npz")
    rep = json.loads((cdir / "crowns.json").read_text(encoding="utf-8"))
    frame = Frame(json.loads(str(veg["origin"])))
    E0, N0, CELL = float(c["E0"]), float(c["N0"]), float(c["cell"])
    sm, lab, paved, built = c["sm"], c["lab"], c["paved"], c["built"]
    ny, nx = sm.shape
    grass = obj_surfaces(obj, ("1GRASS",))["1GRASS"]
    gx0, gx1 = grass[..., 0].min() + 5, grass[..., 0].max() - 5
    gz0, gz1 = grass[..., 1].min() + 5, grass[..., 1].max() - 5
    cl = json.loads((track / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    lap = [(p[0], p[2]) for p in cl["points_xyz_m"]]

    def in_lap(e, n):
        inside = False
        for i in range(len(lap) - 1):
            (ax, az), (bx, bz) = lap[i], lap[i + 1]
            if (az > n) != (bz > n) and e < ax + (n - az) * (bx - ax) / (bz - az):
                inside = not inside
        return inside

    planted, trunks, flags = [], [], {"gone_by_2022": [], "too_near_paved": [], "too_near_built": [], "off_ground": [],
                                      "uncovered": [], "shrub": []}
    for r in rep["crowns"]:
        why = None
        if r["kind"] != "tree":
            why = "shrub"
        elif not (gx0 <= r["e"] <= gx1 and gz0 <= r["n"] <= gz1):
            why = "off_ground"
        elif r["cover_per_m2"] < 0.1:
            why = "uncovered"
        elif r["naip_share"] is not None and r["naip_share"] < 0.2:
            why = "gone_by_2022"
        elif r["d_paved_m"] < corridor + HALF_DIAG_M:
            why = "too_near_paved"
        elif r["d_built_m"] < CLEAR_BUILT_M + HALF_DIAG_M:
            why = "too_near_built"
        if why:
            flags[why].append(r)
            continue
        planted.append(r)
        if r["d_paved_m"] <= COLLIDER_REACH_M:
            trunks.append(r)

    # stands: connected canopy (one cell of slack), named by where they stand
    woody = ndi.binary_dilation(sm >= 2.0, iterations=1) & (c["cov"] >= 0.1)
    st_lab, n_st = ndi.label(woody)
    st_area = ndi.sum(np.ones_like(st_lab), st_lab, range(1, n_st + 1)) * CELL * CELL / 1e4
    by_stand = {}
    for r in planted:
        k = int(st_lab[int((r["n"] - N0) / CELL), int((r["e"] - E0) / CELL)])
        by_stand.setdefault(k, []).append(r)
    stands = []
    for k, rows in by_stand.items():
        if k == 0 or st_area[k - 1] < STAND_MIN_HA:
            continue
        h = np.array([q["h_m"] for q in rows]); w = np.array([q["crown_m"] for q in rows])
        e_m, n_m = float(np.mean([q["e"] for q in rows])), float(np.mean([q["n"] for q in rows]))
        stands.append({"stand": k, "where": ("infield" if in_lap(e_m, n_m) else "outside the lap"),
                       "centre_en": [round(e_m), round(n_m)], "canopy_ha": round(float(st_area[k - 1]), 2), "trees": len(rows),
                       "trees_per_canopy_ha": round(len(rows) / float(st_area[k - 1]), 1),
                       "h_p10_p50_p90_max_m": [round(float(x), 1) for x in np.percentile(h, [10, 50, 90, 100])],
                       "crown_p50_p90_m": [round(float(x), 1) for x in np.percentile(w, [50, 90])],
                       "nearest_paved_m": round(min(q["d_paved_m"] for q in rows), 1),
                       "read_cover_p50_per_m2": round(float(np.median([q["cover_per_m2"] for q in rows])), 2)})
    stands.sort(key=lambda s: -s["canopy_ha"])

    # the planted file (make_treefx planted grammar)
    pts = [[r["lon"], r["lat"], ZONE_HARDWOOD, r["h_m"], r["crown_m"]] for r in planted]
    (outd / "trees.lm.json").write_text(json.dumps({
        "_source": "ledger 0082 vegetation pass: one tree per crown the USGS 3DEP 2017-05-03 lidar measures (Oakland 2016 project, "
                   "pass 2's 71 EPT nodes), checked against NAIP 2022-08-16; h_m = the crown's measured top over the lidar ground, "
                   "crown_m = the diameter of its measured area (source/vegetation/scripts/veg_crowns.py, veg_plan.py). "
                   "Points are [lon, lat, zone, h_m, crown_m]",
        "cols": 1, "rows": 1, "points": pts}, separators=(",", ":")), encoding="utf-8")
    (outd / "trunks.json").write_text(json.dumps({
        "_source": f"the planted trees within {COLLIDER_REACH_M} m [invented reach] of the build's paved surface: [lon, lat, h_m, d_paved_m]",
        "points": [[r["lon"], r["lat"], r["h_m"], r["d_paved_m"]] for r in trunks]}, separators=(",", ":")), encoding="utf-8")

    # the grass classes
    rgb, sdv = naip_features(frame, E0, N0, nx, ny, CELL)
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mean = (R + G + B) / 3
    gr, gb = G / np.maximum(R, 1), G / np.maximum(B, 1)
    ig1 = veg["inten_g"]
    ig = np.nanmean(ig1[:ny * 2, :nx * 2].reshape(ny, 2, nx, 2), axis=(1, 3))
    have = np.isfinite(mean)
    naip_can = c["naip_can"]
    ip = ig[paved & np.isfinite(ig)]
    int_paved = float(np.percentile(ip, 75))                    # [measured] the build's own pavement, its p75
    cls = np.full((ny, nx), "base", dtype=object)
    Cm = have & naip_can & ~paved
    Dm = have & ~paved & ~built & ~naip_can & np.isfinite(ig) & (ig <= int_paved) & (gr < 1.03) & (mean > 110)
    Dm = ndi.binary_opening(Dm, iterations=1)
    Bm = (have & ~paved & ~naip_can & ~Dm & (mean >= B_RULE["mean"][0]) & (mean <= B_RULE["mean"][1])
          & (gr <= B_RULE["g_over_r"][1]) & (gb >= B_RULE["g_over_b"][0]))
    code = np.zeros((ny, nx, 3), np.uint8)
    code[:] = CODE["base"]
    code[Bm] = CODE["B"]
    code[Dm] = CODE["D"]
    code[Cm] = CODE["C"]
    # crop to NAIP's reach
    J, I = np.nonzero(have)
    j0, j1, i0, i1 = J.min(), J.max() + 1, I.min(), I.max() + 1
    crop = code[j0:j1, i0:i1][::-1]
    Image.fromarray(crop).save(outd / "grass_classes.png", optimize=True)
    w_, s_ = frame.to_lonlat(E0 + i0 * CELL, N0 + j0 * CELL)
    e_, n_ = frame.to_lonlat(E0 + i1 * CELL, N0 + j1 * CELL)
    gcls = {"_doc": "the bbox of grass_classes.png (north-up, one pixel per 2 m cell of the local frame)",
            "bbox_lonlat": [round(float(w_), 8), round(float(s_), 8), round(float(e_), 8), round(float(n_), 8)],
            "lidar_pavement_intensity_p75": round(int_paved, 0)}
    (outd / "grass_classes.json").write_text(json.dumps(gcls, indent=1), encoding="utf-8")
    area = lambda m: round(float(m.sum()) * CELL * CELL / 1e4, 2)
    ground = have & ~paved & ~built

    def lst(rows):
        return [{"e": r["e"], "n": r["n"], "h_m": r["h_m"], "crown_m": r["crown_m"], "d_paved_m": r["d_paved_m"],
                 "naip_share": r["naip_share"]} for r in rows]
    h = np.array([r["h_m"] for r in planted]); w = np.array([r["crown_m"] for r in planted])
    inv = {
        "_doc": "ledger 0082 vegetation pass: what the 2017 lidar and NAIP 2022 show, what is planted, and every flag",
        "read": {"lidar": "USGS 3DEP USGS_LPC_MI_31Co_Oakland_2016_LAS_2019, flown 2017-05-03; pass 2's 71 EPT nodes (no new download)",
                 "classes": "ground (2) and unclassified (1) only: no vegetation classes (3/4/5) in this project",
                 "naip": "NAIP 2022-08-16, tile m_4208327_ne_17_060_20220816 (0.50 x 0.68 m)",
                 "naip_canopy_rule": rep["naip_rule"], "solid_cells_2m": rep["solid_cells"], "spikes_dropped": rep["spikes_dropped"]},
        "crowns_read": len(rep["crowns"]),
        "planted": {"trees": len(planted), "h_p10_p50_p90_max_m": [round(float(x), 1) for x in np.percentile(h, [10, 50, 90, 100])],
                    "crown_p10_p50_p90_m": [round(float(x), 1) for x in np.percentile(w, [10, 50, 90])],
                    "infield": sum(1 for r in planted if in_lap(r["e"], r["n"])),
                    "within_100m_of_paved": sum(1 for r in planted if r["d_paved_m"] <= 100),
                    "trunk_colliders": len(trunks), "collider_reach_m": COLLIDER_REACH_M},
        "not_planted": {k: len(v) for k, v in flags.items()},
        "flags": {"gone_by_2022": lst(flags["gone_by_2022"]), "too_near_paved": lst(flags["too_near_paved"]),
                  "too_near_built": lst(flags["too_near_built"]),
                  "naip_new_since_2017": rep["naip_new"], "naip_canopy_unread_m2": rep["naip_canopy_unread_m2"]},
        "shrubs": "none outside the woods: the lidar's 0.5-5 m returns outside canopy cluster on the parking lots (cars), "
                  "not on the proving ground (veg_crowns: crowns 2-5 m tall)",
        "grass_ha": {"C wood floor (NAIP 2022 canopy)": area(Cm & ground), "B long grass (NAIP 2022, 0.1.0's rule)": area(Bm & ground),
                     "D no grass: pavement / gravel the build carries as ground (lidar intensity <= the build's pavement p75 "
                     f"{int_paved:.0f} AND NAIP grey)": area(Dm & ground),
                     "base (mown)": area(ground & ~Cm & ~Bm & ~Dm)},
        "stands": stands,
    }
    (outd / "inventory.json").write_text(json.dumps(inv, indent=1), encoding="utf-8")

    # the overview: the lap's box + 250 m
    xs, zs = [p[0] for p in lap], [p[1] for p in lap]
    e0, e1, n0, n1 = min(xs) - 250, max(xs) + 250, min(zs) - 250, max(zs) + 250
    sl = (slice(int((n0 - N0) / CELL), int((n1 - N0) / CELL)), slice(int((e0 - E0) / CELL), int((e1 - E0) / CELL)))
    img = code[sl].astype(np.float32)
    img[(code[sl] == CODE["base"]).all(-1)] = (150, 175, 120)
    img[(code[sl] == CODE["B"]).all(-1)] = (215, 200, 140)
    img[(code[sl] == CODE["C"]).all(-1)] = (70, 100, 60)
    img[(code[sl] == CODE["D"]).all(-1)] = (170, 120, 200)
    img[paved[sl]] = (95, 95, 95)
    img[built[sl]] = (240, 220, 0)
    im = Image.fromarray(img[::-1].astype(np.uint8)).resize((int((e1 - e0) / CELL) * 2, int((n1 - n0) / CELL) * 2), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    S = 2 / CELL
    P = lambda e, n: ((e - e0) * S, (n1 - n) * S)
    for r in planted:
        x, y = P(r["e"], r["n"])
        rr = max(1.5, r["crown_m"] / 2 * S)
        dr.ellipse([x - rr, y - rr, x + rr, y + rr], outline=(20, 60, 20))
        dr.point((x, y), fill=(0, 0, 0))
    for r in trunks:
        x, y = P(r["e"], r["n"])
        dr.rectangle([x - 2, y - 2, x + 2, y + 2], fill=(255, 0, 0))
    for r in flags["gone_by_2022"]:
        x, y = P(r["e"], r["n"])
        dr.ellipse([x - 4, y - 4, x + 4, y + 4], outline=(255, 0, 255), width=2)
    for r in rep["naip_new"]:
        x, y = P(r["e"], r["n"])
        dr.ellipse([x - 4, y - 4, x + 4, y + 4], outline=(0, 140, 255), width=2)
    im.save(outd / "overview.jpg", quality=85)
    print(f"[plan] planted {len(planted)} trees ({len(trunks)} trunk colliders within {COLLIDER_REACH_M} m); not planted "
          f"{ {k: len(v) for k, v in flags.items()} }; stands {len(stands)}; grass ha {inv['grass_ha']}")


if __name__ == "__main__":
    main()
