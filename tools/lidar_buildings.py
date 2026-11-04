"""Building heights from 3DEP lidar: every planned footprint's roof and the ground round it (ledger 0079; run on the PC).

tools/plan_buildings.py takes a building's height from OSM's tags, Microsoft's ML estimate, a NAIP shadow or a class default.
Where USGS's public lidar covers the track, the roof is MEASURED: this script reads the point cloud (an EPT store, the
octree walked only to the depth whose cell is --res metres, so a few points per square metre: a roof needs tens, not
thousands) over every footprint of the plan's "out" file, and writes, per footprint key,

    ground_m  median class-2 height in a ring RING_IN_M..RING_OUT_M outside the footprint (the street, the yard)
    roof_p10 / roof_p50 / roof_p95   heights of the non-ground first returns inside the footprint shrunk by SHRINK_M
                                     (walls, eaves and a neighbour's tree kept out) — p10 near the eaves, p95 the ridge
    n_roof / n_ground                the point counts (a footprint with fewer than MIN_ROOF_PTS roof points has no row)

in metres above the ellipsoid-free vertical of the store (only differences are used). The planner's "lidar" key reads the
file and puts it FIRST: a measured roof beats every other source. Classes taken as roof: everything but ground (2), noise
(7, 18), water (9) and overlap / withheld bits. A roof's own tree cover reads as roof here: p50 for a flat roof, p95 for a
pitched one's ridge (tree tops over a house raise p95; the planner caps a lidar height at the class cap and says so).

Needs laspy (with a LAZ backend: lazrs or laszip), pyproj and numpy: the PC's environment (tools/lidar_turns.py's). The Mac
has no LAZ reader and installs nothing.

    python tools/lidar_buildings.py tracks/<track> [--plan source/bespoke/buildings.plan.json] [--ept <ept.json url>]
                                    [--trees source/bespoke/trees.plan.json [--trees-out source/bespoke/lidar_trees.json]]
                                    [--res 1.0] [--out source/bespoke/lidar_roofs.json]
"""
from __future__ import annotations

import argparse
import io
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))

EPT = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_DRCOG_2_2020/ept.json"
SHRINK_M = 0.6          # [invented] roof points this far inside the footprint: the eave overhang and the wall line kept out
RING_IN_M, RING_OUT_M = 1.5, 6.0   # [invented] the ground ring round the footprint
MIN_ROOF_PTS = 8        # [invented] fewer roof points than this: no measurement
TREE_MIN_R_M = 1.5      # [invented] the smallest crown radius read for canopy returns
TREE_RING_M = 3.0       # [invented] the ground read this far past the crown radius
MIN_CANOPY_PTS = 4      # [invented] fewer canopy returns than this: no measurement
NOT_ROOF = {2, 7, 9, 18}


def _get(url):
    from scripts.tls import https_context
    for k in range(6):
        try:
            with urllib.request.urlopen(url, timeout=180, context=https_context()) as r:
                return r.read()
        except Exception:                                   # noqa: BLE001
            time.sleep(4 * (k + 1))
    raise SystemExit(f"[lidar_buildings] refused: {url}")


def node_keys(ept, base, box, res):
    """every EPT node over ``box`` (EPSG:3857 x0, y0, x1, y1) down to the depth whose voxel is <= res metres"""
    b = ept["bounds"]
    span = int(ept.get("span", 128))
    max_d = max(0, math.ceil(math.log2((b[3] - b[0]) / (span * res))))
    hier, keys = {}, []

    def h_of(key):
        if key not in hier:
            hier[key] = json.loads(_get(f"{base}/ept-hierarchy/{key}.json"))
        return hier[key]

    def walk(d, x, y, z, h):
        k = f"{d}-{x}-{y}-{z}"
        if k not in h or d > max_d:
            return
        if h[k] == -1:
            h = h_of(k)
        sz = (b[3] - b[0]) / 2 ** d
        bx, by = b[0] + x * sz, b[1] + y * sz
        if bx > box[2] or bx + sz < box[0] or by > box[3] or by + sz < box[1]:
            return
        if h[k] > 0:
            keys.append(k)
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    walk(d + 1, 2 * x + dx, 2 * y + dy, 2 * z + dz, h)
    walk(0, 0, 0, 0, h_of("0-0-0-0"))
    return keys, max_d


def shrink(ring, d):
    """the ring moved inward by d (each vertex along its corner's bisector; a convex-enough footprint is all this needs)"""
    n = len(ring)
    area = sum(ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1] for i in range(n)) / 2.0
    s = 1.0 if area > 0 else -1.0                     # CCW: inward is to the left
    out = []
    for i in range(n):
        p0, p1, p2 = ring[i - 1], ring[i], ring[(i + 1) % n]
        e0 = (p1[0] - p0[0], p1[1] - p0[1]); e1 = (p2[0] - p1[0], p2[1] - p1[1])
        l0 = math.hypot(*e0) or 1.0; l1 = math.hypot(*e1) or 1.0
        n0 = (-e0[1] / l0 * s, e0[0] / l0 * s); n1 = (-e1[1] / l1 * s, e1[0] / l1 * s)
        bx, by = n0[0] + n1[0], n0[1] + n1[1]
        bl = math.hypot(bx, by) or 1.0
        cos_half = max(0.3, (bx * n0[0] + by * n0[1]) / bl)
        out.append((p1[0] + bx / bl * d / cos_half, p1[1] + by / bl * d / cos_half))
    return out


def pip(ring, pts):
    """points (N x 2 numpy) inside the ring: even-odd ray cast, vectorised over the points"""
    import numpy as np
    x, y = pts[:, 0], pts[:, 1]
    inside = np.zeros(len(pts), bool)
    n = len(ring)
    for i in range(n):
        (x1, y1), (x2, y2) = ring[i], ring[(i + 1) % n]
        if y1 == y2:
            continue
        inside ^= ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1)
    return inside


def main(argv=None) -> int:
    import numpy as np
    from pyproj import Transformer
    from scipy.spatial import cKDTree
    import laspy
    ap = argparse.ArgumentParser()
    ap.add_argument("track")
    ap.add_argument("--plan", default="source/bespoke/buildings.plan.json")
    ap.add_argument("--ept", default=EPT)
    ap.add_argument("--res", type=float, default=1.0)
    ap.add_argument("--out", default="source/bespoke/lidar_roofs.json")
    ap.add_argument("--trees", default=None, help="a crowns plan (source/bespoke/trees.plan.json): canopy heights too, same read")
    ap.add_argument("--trees-out", default="source/bespoke/lidar_trees.json")
    a = ap.parse_args(argv)
    track = Path(a.track)
    plan = json.loads((track / a.plan).read_text(encoding="utf-8"))
    rows = json.loads((track / plan["out"]).read_text(encoding="utf-8"))
    to_merc = Transformer.from_crs(4326, 3857, always_xy=True)
    crowns = []
    if a.trees:
        tplan = json.loads((track / a.trees).read_text(encoding="utf-8"))
        tpts = json.loads((track / tplan["out"]).read_text(encoding="utf-8"))["points"]
        cx_, cy_ = to_merc.transform([p[0] for p in tpts], [p[1] for p in tpts])
        crowns = [(p, x, y) for p, x, y in zip(tpts, cx_, cy_)]
    rings = []
    for r in rows:
        xs, ys = to_merc.transform([p[0] for p in r["footprint_lonlat"]], [p[1] for p in r["footprint_lonlat"]])
        ring = list(zip(xs, ys))
        if ring[0] == ring[-1]:
            ring = ring[:-1]
        rings.append(ring)
    allx = [p[0] for g in rings for p in g] + [c[1] for c in crowns]
    ally = [p[1] for g in rings for p in g] + [c[2] for c in crowns]
    pad = RING_OUT_M + 2.0
    box = (min(allx) - pad, min(ally) - pad, max(allx) + pad, max(ally) + pad)
    ept = json.loads(_get(a.ept))
    base = a.ept.rsplit("/", 1)[0]
    keys, depth = node_keys(ept, base, box, a.res)
    print(f"[lidar_buildings] {len(rows)} footprints; {len(keys)} EPT nodes to depth {depth} (voxel <= {a.res} m) over "
          f"{(box[2] - box[0]) / 1000:.1f} x {(box[3] - box[1]) / 1000:.1f} km of {a.ept}")
    gX, gY, gZ, rX, rY, rZ = [], [], [], [], [], []
    t0 = time.time()
    for i, k in enumerate(keys):
        las = laspy.read(io.BytesIO(_get(f"{base}/ept-data/{k}.laz")))
        x, y, z = np.asarray(las.x), np.asarray(las.y), np.asarray(las.z)
        c = np.asarray(las.classification)
        inb = (x >= box[0]) & (x <= box[2]) & (y >= box[1]) & (y <= box[3])
        try:
            first = np.asarray(las.return_number) == 1
        except Exception:                                   # noqa: BLE001
            first = np.ones_like(inb)
        g = inb & (c == 2)
        rf = inb & first & ~np.isin(c, list(NOT_ROOF))
        gX.append(x[g]); gY.append(y[g]); gZ.append(z[g])
        rX.append(x[rf]); rY.append(y[rf]); rZ.append(z[rf])
        if (i + 1) % 50 == 0:
            print(f"  {i + 1} / {len(keys)} nodes, {time.time() - t0:.0f} s")
    gX, gY, gZ = (np.concatenate(v) for v in (gX, gY, gZ))
    rX, rY, rZ = (np.concatenate(v) for v in (rX, rY, rZ))
    print(f"[lidar_buildings] ground points {len(gZ):,}, non-ground first returns {len(rZ):,}")
    gt, rt = cKDTree(np.c_[gX, gY]), cKDTree(np.c_[rX, rY])
    out, n_none = {}, 0
    for r, ring in zip(rows, rings):
        cx = sum(p[0] for p in ring) / len(ring); cy = sum(p[1] for p in ring) / len(ring)
        rad = max(math.hypot(p[0] - cx, p[1] - cy) for p in ring)
        inner = shrink(ring, SHRINK_M)
        idx = rt.query_ball_point((cx, cy), rad)
        if idx:
            pts = np.c_[rX[idx], rY[idx]]
            m = pip(inner, pts)
            roof = rZ[idx][m]
        else:
            roof = np.zeros(0)
        gi = gt.query_ball_point((cx, cy), rad + RING_OUT_M)
        gr = np.zeros(0)
        if gi:
            pts = np.c_[gX[gi], gY[gi]]
            outer = pip(shrink(ring, -RING_OUT_M), pts)
            near = pip(shrink(ring, -RING_IN_M), pts)
            gr = gZ[gi][outer & ~near]
        if len(roof) < MIN_ROOF_PTS or not len(gr):
            n_none += 1
            continue
        out[r["key"]] = {"ground_m": round(float(np.median(gr)), 2), "roof_p10": round(float(np.percentile(roof, 10)), 2),
                         "roof_p50": round(float(np.percentile(roof, 50)), 2), "roof_p95": round(float(np.percentile(roof, 95)), 2),
                         "n_roof": int(len(roof)), "n_ground": int(len(gr))}
    rep = {"_source": f"USGS 3DEP lidar, {a.ept} (EPT, nodes to depth {depth}: voxel <= {a.res} m), read by tools/lidar_buildings.py "
                      f"{time.strftime('%Y-%m-%d')}; roof = non-ground first returns inside the footprint shrunk {SHRINK_M} m, ground = "
                      f"class 2 in a {RING_IN_M}-{RING_OUT_M} m ring",
           "footprints": len(rows), "measured": len(out), "unmeasured": n_none, "roofs": out}
    (track / a.out).write_text(json.dumps(rep, separators=(",", ":")), encoding="utf-8")
    print(f"[lidar_buildings] {len(out)} of {len(rows)} footprints measured ({n_none} with < {MIN_ROOF_PTS} roof points or no "
          f"ground) -> {a.out}")
    if crowns:
        # THE TREES (--trees; ledger 0079 round B): each NAIP crown's canopy top = the p95 of the non-ground first returns
        # within its crown radius (at least TREE_MIN_R_M), its ground = the median class-2 return within that radius +
        # TREE_RING_M; height = the difference. The planner's crowns mode takes it before its [invented] width ratio
        trees, t_none = {}, 0
        for p, x, y in crowns:
            rad = max(TREE_MIN_R_M, p[4] / 2.0)
            idx = rt.query_ball_point((x, y), rad)
            gi = gt.query_ball_point((x, y), rad + TREE_RING_M)
            if len(idx) < MIN_CANOPY_PTS or not gi:
                t_none += 1
                continue
            top = float(np.percentile(rZ[idx], 95)); gnd = float(np.median(gZ[gi]))
            trees[f"{p[0]:.7f},{p[1]:.7f}"] = {"h_m": round(top - gnd, 2), "n_canopy": len(idx), "n_ground": len(gi)}
        trep = {"_source": f"USGS 3DEP lidar, {a.ept}, read by tools/lidar_buildings.py --trees {time.strftime('%Y-%m-%d')}: "
                           f"canopy = p95 of non-ground first returns within the crown radius (>= {TREE_MIN_R_M} m), ground = "
                           f"median class 2 within the radius + {TREE_RING_M} m; keyed 'lon,lat' as the crowns file writes them",
                "crowns": len(crowns), "measured": len(trees), "unmeasured": t_none, "trees": trees}
        (track / a.trees_out).write_text(json.dumps(trep, separators=(",", ":")), encoding="utf-8")
        hs = sorted(v["h_m"] for v in trees.values())
        print(f"[lidar_buildings] trees: {len(trees)} of {len(crowns)} crowns measured ({t_none} with < {MIN_CANOPY_PTS} canopy "
              f"points or no ground); height p10 / p50 / p90 "
              f"{[hs[int(f * (len(hs) - 1))] for f in (0.1, 0.5, 0.9)] if hs else []} m -> {a.trees_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
