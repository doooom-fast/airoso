"""Ledger 0100 item 7 (Kevin 2026-11-22, the verge trees: "Plant them from the photo"): TreeFX trees where NAIP 2022 shows
canopy with no 2017 lidar canopy under it, planted by a measured rule.

    python veg_naip_verge.py <track dir> [--from-npz <crowns.npz>] [--write]

THE BLOBS (measured, ledger 0082 vegetation pass). veg_crowns.py's `new_c`: NAIP 2022's canopy rule (calibrated on the lidar,
TPR 0.962 / TNR 0.976) where the read could have seen canopy (cover >= its dense rule) and saw none (no lidar canopy within
4 m), off the 0.1.2 build's paved and built cells; 4-connected blobs of at least 20 m2 on its 2 m grid. 428 blobs, 4.43 ha
(inventory.json flags.naip_new_since_2017, reproduced cell for cell). --from-npz writes them, once, as the committed
naip_only_canopy.png (one pixel per 2 m cell, white = a blob cell; north up) + .json (its grid), from the read's
crowns.npz (not committed: 9 MB); every later run reads the PNG.

THE PLANTING (each rule's source beside it):
  - the tree's HEIGHT and CROWN are its measured neighbours': the median h_m and crown_m of the lidar's planted crowns
    (trees.lm.json, the points without this script's tag) within NEIGH_M of the blob's centroid, when at least NEIGH_MIN
    stand there. Fewer: Milford's own median measured crown (inventory.json planted: h p50 20.4 m, crown p50 9.0 m), and the
    tree is marked [invented] in naip_verge.json (the height is not a neighbour's);
  - POSITIONS: a hexagonal lattice at the crown's spacing, anchored on the blob's centroid, its points on the blob's own
    cells (crowns tile the canopy NAIP shows, as the lidar's woods do at their measured crown width); a blob no lattice point
    falls in gets one tree on its cell nearest the centroid; a lone tree's crown is the lesser of the neighbours' and the
    blob's own (2 sqrt(area / pi), veg_crowns' crown rule);
  - the lidar planting's own rules (veg_plan.py): a tree (h >= 5 m, FAO's); its trunk at least scenery.corridor_margin_m
    + half a 2 m cell's diagonal off the drivable surface (veg_trunks_reach.drivable_d: the lane + edge strip and every
    pad, the 0.1.13 run-off pads included) and 1.0 m + the same off every building and block footprint the config names;
    over the built ground (the far ground product's extent, 5 m in, as veg_plan's 1GRASS extent);
  - each tree's KEY (the 6th element, make_treefx's hash) is KEY0 + its rank, its 7th element TAG: re-running this script
    replaces exactly its own trees; the lidar's 11,247 keep their keys, models and angles.
--write appends them to trees.lm.json and writes naip_verge.json (every tree, its blob, its neighbours, its source);
run veg_trunks_reach.py --write after it (a verge tree within the reach gets a collider like any other).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import veg_trunks_reach as vtr  # noqa: E402

TAG = "naip_verge"
KEY0 = 1_000_000              # the verge trees' keys start here (the lidar's run 0..12,134)
NEIGH_M = 30.0                # [invented] a blob's measured neighbours stand within this of its centroid
NEIGH_MIN = 3                 # [invented] at least this many, else the read's median (marked [invented] per tree)
MIN_AREA_M2 = 20.0            # veg_crowns.py: a NAIP-only blob of at least this (5 cells of 2 m)
TREE_MIN_M = 5.0              # veg_crowns.TREE_MIN_M, FAO's tree
HALF_DIAG_M = math.sqrt(2.0)  # veg_plan.HALF_DIAG_M: half a 2 m cell's diagonal
CLEAR_BUILT_M = 1.0           # veg_plan.CLEAR_BUILT_M = tools/make_treefx.py BUILT_BUILDING_CLEAR_M
GROUND_IN_M = 5.0             # veg_plan: over the built ground, 5 m in


def write_png(track, npz):
    c = np.load(npz)
    E0, N0, cell = float(c["E0"]), float(c["N0"]), float(c["cell"])
    lab, n = ndi.label(c["new_c"])
    area = ndi.sum(np.ones_like(lab), lab, range(1, n + 1)) * cell * cell
    keep = np.isin(lab, [k + 1 for k in range(n) if area[k] >= MIN_AREA_M2])
    vd = track / "source" / "vegetation"
    Image.fromarray((keep[::-1] * 255).astype(np.uint8), "L").convert("1").save(vd / "naip_only_canopy.png", optimize=True)
    (vd / "naip_only_canopy.json").write_text(json.dumps({
        "_doc": "ledger 0100 item 7 (source/vegetation/scripts/veg_naip_verge.py --from-npz): the NAIP 2022 canopy the 2017 lidar "
                "does not hold (veg_crowns.py new_c, blobs of at least 20 m2: inventory.json flags.naip_new_since_2017), one pixel "
                "per cell, row 0 = NORTH; cell (row r, col i) has its centre at e = e0 + (i + 0.5) cell, n = n0 + (rows - r - 0.5) "
                "cell, local metres about data/centerline.local.json's origin",
        "e0": E0, "n0": N0, "cell_m": cell, "rows": int(keep.shape[0]), "cols": int(keep.shape[1]),
        "cells": int(keep.sum())}, indent=1), encoding="utf-8")


def read_blobs(track):
    vd = track / "source" / "vegetation"
    g = json.loads((vd / "naip_only_canopy.json").read_text(encoding="utf-8"))
    m = np.asarray(Image.open(vd / "naip_only_canopy.png").convert("L"))[::-1] > 127      # row 0 = south again
    lab, n = ndi.label(m)
    return g, lab, n


def footprints(cfg, track, o):
    """every building / block footprint the config names (inline rows and block files), local metres"""
    m_lon, m_lat = vtr.meters_per_degree(o["lat"])
    b = cfg["scenery"]["bespoke"]
    rows = list(b.get("buildings") or [])
    for grp in b.get("blocks") or []:
        rows += json.loads((track / grp["file"]).read_text(encoding="utf-8")) if grp.get("file") else [grp]
    return [np.array([((p[0] - o["lon"]) * m_lon, (p[1] - o["lat"]) * m_lat) for p in r["footprint_lonlat"]], float)
            for r in rows if r.get("footprint_lonlat")]


def hex_points(cx, cz, d, reach):
    """a hexagonal lattice of spacing d anchored on (cx, cz), out to reach"""
    out, dz = [], d * math.sqrt(3.0) / 2.0
    nr = int(reach / dz) + 1
    nc = int(reach / d) + 1
    for r in range(-nr, nr + 1):
        off = (d / 2.0) if r % 2 else 0.0
        for q in range(-nc - 1, nc + 1):
            out.append((cx + q * d + off, cz + r * dz))
    return out


def plan(track):
    cfg = json.loads((track / "track.config.json").read_text(encoding="utf-8"))
    cl = json.loads((track / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    o = cl["origin"]
    m_lon, m_lat = vtr.meters_per_degree(o["lat"])
    trees = json.loads((track / "source" / "vegetation" / "trees.lm.json").read_text(encoding="utf-8"))
    lidar = [p for p in trees["points"] if not (len(p) > 6 and p[6] == TAG)]
    inv = json.loads((track / "source" / "vegetation" / "inventory.json").read_text(encoding="utf-8"))
    h_med = float(inv["planted"]["h_p10_p50_p90_max_m"][1])
    c_med = float(inv["planted"]["crown_p10_p50_p90_m"][1])
    lxz = np.array([((p[0] - o["lon"]) * m_lon, (p[1] - o["lat"]) * m_lat) for p in lidar])
    lh, lc = np.array([p[3] for p in lidar]), np.array([p[4] for p in lidar])
    kd = cKDTree(lxz)
    fg = json.loads((track / "data" / "far_ground.lidar.meta.json").read_text(encoding="utf-8"))
    gx0, gz0 = fg["x0"] + GROUND_IN_M, fg["y0"] + GROUND_IN_M
    gx1, gz1 = fg["x0"] + fg["nx"] * fg["cell_m"] - GROUND_IN_M, fg["y0"] + fg["ny"] * fg["cell_m"] - GROUND_IN_M
    margin = float(cfg["scenery"]["corridor_margin_m"])
    lane = vtr.Lane(cl)
    fps = footprints(cfg, track, o)
    g, lab, n = read_blobs(track)
    e0, n0, cell = g["e0"], g["n0"], g["cell_m"]
    sl = ndi.find_objects(lab)
    cand, why_out, blobs = [], {}, []
    for k in range(1, n + 1):
        sj, si = sl[k - 1]
        jj, ii = np.nonzero(lab[sj, si] == k)
        jj, ii = jj + sj.start, ii + si.start
        area = float(len(jj)) * cell * cell
        ce, cn = e0 + (ii.mean() + 0.5) * cell, n0 + (jj.mean() + 0.5) * cell
        near = kd.query_ball_point((ce, cn), NEIGH_M)
        measured = len(near) >= NEIGH_MIN
        h = float(np.median(lh[near])) if measured else h_med
        d = float(np.median(lc[near])) if measured else c_med
        cells = set(zip(jj.tolist(), ii.tolist()))
        pts = [(x, z) for x, z in hex_points(ce, cn, d, math.sqrt(area) + d)
               if (int(math.floor((z - n0) / cell)), int(math.floor((x - e0) / cell))) in cells]
        lone = False
        if not pts:
            q = int(np.argmin((e0 + (ii + 0.5) * cell - ce) ** 2 + (n0 + (jj + 0.5) * cell - cn) ** 2))
            pts, lone = [(e0 + (ii[q] + 0.5) * cell, n0 + (jj[q] + 0.5) * cell)], True
        crown = min(d, 2.0 * math.sqrt(area / math.pi)) if len(pts) == 1 else d
        blobs.append({"blob": k, "e": round(ce, 1), "n": round(cn, 1), "area_m2": area, "neighbours": len(near),
                      "h_m": round(h, 2), "crown_m": round(crown, 2), "source": "measured neighbours" if measured else "[invented]",
                      "trees": len(pts), "lone_cell": lone})
        for x, z in pts:
            cand.append((k, x, z, h, crown, measured, len(near)))
    x = np.array([c[1] for c in cand])
    z = np.array([c[2] for c in cand])
    dd = vtr.drivable_d(cfg, cl, lane, o["lon"] + x / m_lon, o["lat"] + z / m_lat)
    db = np.full(len(cand), np.inf)
    for ring in fps:
        sel = (np.abs(x - ring[:, 0].mean()) < 400) & (np.abs(z - ring[:, 1].mean()) < 400)
        if sel.any():
            db[sel] = np.minimum(db[sel], vtr.ring_d(ring, x[sel], z[sel]))
    out = []
    for c, xi, zi, dpi, dbi in zip(cand, x, z, dd, db):
        if c[3] < TREE_MIN_M:
            why = "a shrub (under 5 m)"
        elif dpi < margin + HALF_DIAG_M:
            why = "within the corridor margin of the drivable surface"
        elif dbi < CLEAR_BUILT_M + HALF_DIAG_M:
            why = "within 1 m of a building or block"
        elif not (gx0 <= xi <= gx1 and gz0 <= zi <= gz1):
            why = "off the built ground"
        else:
            out.append({"blob": c[0], "e": float(xi), "n": float(zi), "h_m": c[3], "crown_m": c[4], "measured": c[5],
                        "neighbours": c[6], "d_drivable_m": float(dpi)})
            continue
        why_out[why] = why_out.get(why, 0) + 1
    out.sort(key=lambda t: (t["blob"], t["n"], t["e"]))
    pts = []
    for r, t in enumerate(out):
        lon, lat = o["lon"] + t["e"] / m_lon, o["lat"] + t["n"] / m_lat
        t.update(lon=round(lon, 7), lat=round(lat, 7), key=KEY0 + r)
        pts.append([t["lon"], t["lat"], 1, round(t["h_m"], 2), round(t["crown_m"], 2), t["key"], TAG])
    return {"blobs": blobs, "trees": out, "points": pts, "left_out": why_out, "lidar": lidar, "trees_doc": trees}


def main():
    track = Path(sys.argv[1])
    if "--from-npz" in sys.argv:
        write_png(track, Path(sys.argv[sys.argv.index("--from-npz") + 1]))
    res = plan(track)
    b, t = res["blobs"], res["trees"]
    meas = sum(1 for x in t if x["measured"])
    hs = np.array([x["h_m"] for x in t]) if t else np.zeros(1)
    print(f"[verge] {len(b)} blobs, {sum(x['area_m2'] for x in b) / 1e4:.2f} ha; {len(t)} trees planted "
          f"({meas} with measured neighbours' height and crown, {len(t) - meas} [invented]); left out {res['left_out']}; "
          f"h p10/p50/p90 {np.percentile(hs, 10):.1f} / {np.percentile(hs, 50):.1f} / {np.percentile(hs, 90):.1f} m; "
          f"within 30 m of the drivable surface {sum(1 for x in t if x['d_drivable_m'] <= 30)}")
    if "--write" in sys.argv:
        vd = track / "source" / "vegetation"
        doc = res["trees_doc"]
        doc["points"] = res["lidar"] + res["points"]
        tail = (" Ledger 0100 item 7 (veg_naip_verge.py): the points whose 7th element is \"naip_verge\" are NAIP 2022's canopy "
                "the 2017 lidar does not hold, planted at their measured neighbours' height and crown (naip_verge.json)")
        if tail not in doc["_source"]:
            doc["_source"] += tail
        (vd / "trees.lm.json").write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
        rec = {"_doc": "ledger 0100 item 7: every NAIP-only canopy blob (naip_only_canopy.png) and the trees planted in it by "
                       "source/vegetation/scripts/veg_naip_verge.py (its header holds each rule's source). source \"[invented]\": "
                       f"fewer than {NEIGH_MIN} measured crowns within {NEIGH_M:.0f} m [invented], so the read's median crown",
               "rules": {"neigh_m": NEIGH_M, "neigh_min": NEIGH_MIN, "min_area_m2": MIN_AREA_M2, "tree_min_m": TREE_MIN_M,
                         "key0": KEY0, "tag": TAG},
               "left_out": res["left_out"],
               "blobs": res["blobs"],
               "trees": [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in x.items()} for x in t]}
        (vd / "naip_verge.json").write_text(json.dumps(rec, separators=(",", ":")), encoding="utf-8")
        print(f"[verge] wrote trees.lm.json ({len(doc['points'])} points) and naip_verge.json")


if __name__ == "__main__":
    main()
