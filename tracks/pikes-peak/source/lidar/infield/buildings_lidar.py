"""PPIR's buildings off the 2018 lidar already on disk (ledger 0085, furniture pass 1, 0.2.1): every roof standing over
the ground, its footprint, its height and its roof elevation; the NAIP 2023 crop's colour over each, to tell a roof from
a tree. No download: the points are D:/k10-scratch/pp_lidar/infield.npz (CO_Eastern_ElPaso_2018, the box fetched on
Kevin's 2026-11-08 yes), the ground its 1 m DEM (infield_dem.npz, build-y = lidar z - 1634.84).

THE READ, on a CELL_M grid over the box:
  * height over the ground (hag) of every non-ground (class 1) point: its z less the DEM under it;
  * a cell is ROOF when its highest point stands over MIN_HAG_M; ROOF closed over one cell, holes filled;
  * each connected piece of at least MIN_AREA_M2 is a candidate; per candidate:
      footprint   the minimum-area rectangle round its cells (rotating calipers on the hull) when the cells fill at
                  least RECT_FILL of it, else its traced outline simplified to SIMPLIFY_M;
      hag         p10 / p50 / p95 of its points' heights over the ground (p10 near the eaves, p95 the ridge / top);
      roof_z_m    the median roof point's elevation in the scene frame (lidar z - origin elev_m);
      ground_m    the DEM's median in a ring RING_IN_M..RING_OUT_M outside it (scene frame);
      naip        the median saturation and RGB of the crop over it (registration shift applied, as junction_pads.py);
      kind        "roof" when NAIP's saturation is under VEG_SAT and the hag's spread (p95 - p10) is under ROUGH_M
                  or the rectangle fill holds; "tree" otherwise; "pole" for a piece under POLE_AREA_M2 standing
                  over POLE_HAG_M (reported, not built).
Writes <out>.json (one row per candidate, sorted by area) and <out>.png (NAIP with every candidate outlined and numbered).

    python tracks/pikes-peak/source/lidar/infield/buildings_lidar.py <workshop project> --naip <crop png> \
        --lidar D:/k10-scratch/pp_lidar/infield.npz --dem D:/k10-scratch/pp_lidar/infield_dem.npz --out <prefix>

<workshop project>: its data/centerline.local.json gives the origin (the track frame) and the lap (each row's distance
to it, for the report). Numbers marked [invented] are sampling choices (fleet/GATES-CHANGELOG.md, 0085 furniture).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import ConvexHull, cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from junction_pads import Crop  # noqa: E402  (the NAIP crop in the track frame, the registration shift applied)

CELL_M = 0.5          # [invented] the roof grid: about one 2 pts/m2 return per cell
MIN_HAG_M = 2.5       # [invented] a roof stands this far over the ground (the outer wall's 1.27 m and a car are under it)
MIN_AREA_M2 = 12.0    # [invented] the smallest building read (a shed); smaller pieces are poles, signs or noise
POLE_AREA_M2 = 3.0    # [invented] under this a piece is a pole / mast when it stands over POLE_HAG_M
POLE_HAG_M = 6.0
RECT_FILL = 0.80      # [invented] cells filling this share of their minimum rectangle are a rectangular building
SIMPLIFY_M = 0.75     # [invented] the outline's simplification otherwise (about 1.5 cells)
RING_IN_M, RING_OUT_M = 1.5, 5.0   # tools/lidar_buildings.py's ground ring (its 6 m outer bound held to 5 here)
VEG_SAT = 0.20        # junction_pads.py's measured classes: grass 0.27-0.33, roofs and asphalt under 0.14
ROUGH_M = 4.0         # [invented] a canopy's p95 - p10 spread over this reads as a tree, a roof's under it


def min_rect(pts):
    """the minimum-area rectangle round a point set (rotating calipers on its hull): 4 corners, area"""
    hull = pts[ConvexHull(pts).vertices]
    best = None
    for i in range(len(hull)):
        e = hull[(i + 1) % len(hull)] - hull[i]
        L = np.hypot(*e)
        if L < 1e-9:
            continue
        u = e / L
        v = np.array([-u[1], u[0]])
        a, b = hull @ u, hull @ v
        area = (a.max() - a.min()) * (b.max() - b.min())
        if best is None or area < best[0]:
            best = (area, u, v, a.min(), a.max(), b.min(), b.max())
    area, u, v, a0, a1, b0, b1 = best
    corners = [u * a + v * b for a, b in ((a0, b0), (a1, b0), (a1, b1), (a0, b1))]
    return np.array(corners), area


def simplify(ring, tol):
    """Douglas-Peucker on a closed ring"""
    def dp(pts):
        if len(pts) < 3:
            return pts
        a, b = pts[0], pts[-1]
        ab = b - a
        L = np.hypot(*ab) or 1e-9
        d = np.abs(ab[0] * (pts[:, 1] - a[1]) - ab[1] * (pts[:, 0] - a[0])) / L
        i = int(np.argmax(d))
        if d[i] <= tol:
            return np.array([a, b])
        return np.vstack([dp(pts[:i + 1])[:-1], dp(pts[i:])])
    ring = np.asarray(ring)
    k = int(np.argmax(np.hypot(*(ring - ring[0]).T)))
    out = np.vstack([dp(ring[:k + 1])[:-1], dp(np.vstack([ring[k:], ring[:1]]))[:-1]])
    return out


def trace(mask, x0, y0, cell):
    """the outer boundary of a single-component mask as a ring of cell corners (E, N)"""
    import sys as _s
    _s.path.insert(0, str(HERE.parents[4]))
    from tools import draft_pads as dp
    xs = (x0 + (np.arange(mask.shape[1]) + 0.5) * cell).tolist()
    ys = (y0 - (np.arange(mask.shape[0]) + 0.5) * cell).tolist()
    return np.array(dp.trace_boundary(mask.tolist(), xs, ys))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--naip", required=True)
    ap.add_argument("--lidar", required=True)
    ap.add_argument("--dem", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    loc = json.loads((Path(a.project) / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    elev0 = float(loc["origin"]["elev_m"])
    lap = np.array([[p[0], p[2]] for p in loc["points_xyz_m"]])
    crop = Crop(Path(a.naip), loc["origin"])
    L = np.load(a.lidar)
    D = np.load(a.dem)
    dem, e0, n0, dc = D["dem"], float(D["e0"]), float(D["n0"]), float(D["cell_m"])
    if abs(float(D["elev0"]) - elev0) > 1e-6:
        raise SystemExit(f"buildings_lidar: the DEM's datum {float(D['elev0'])} is not the track's {elev0}")

    def dem_at(e, n):
        i = np.clip(((np.asarray(e) - e0) / dc).astype(int), 0, dem.shape[1] - 1)
        j = np.clip(((np.asarray(n) - n0) / dc).astype(int), 0, dem.shape[0] - 1)
        return dem[j, i]
    nong = L["cls"] == 1
    E, N, Z = L["e"][nong], L["n"][nong], L["z"][nong] - elev0
    hag = Z - dem_at(E, N)
    keep = (hag > 0.3) & (hag < 60.0)
    E, N, Z, hag = E[keep], N[keep], Z[keep], hag[keep]
    x0, x1, y0, y1 = E.min(), E.max(), N.min(), N.max()
    nx, ny = int((x1 - x0) / CELL_M) + 1, int((y1 - y0) / CELL_M) + 1
    ci = ((E - x0) / CELL_M).astype(int)
    cj = ((y1 - N) / CELL_M).astype(int)                         # row 0 = north
    top = np.full((ny, nx), -1.0)
    np.maximum.at(top, (cj, ci), hag)
    roof = ndimage.binary_fill_holes(ndimage.binary_closing(top > MIN_HAG_M, iterations=1))
    lab, n = ndimage.label(roof)
    rows = []
    sl = ndimage.find_objects(lab)
    pid = lab[cj, ci]
    for k in range(1, n + 1):
        cells = int((lab[sl[k - 1]] == k).sum())
        area = cells * CELL_M * CELL_M
        sel = pid == k
        if not sel.any():
            continue
        ph = hag[sel]
        if area < MIN_AREA_M2:
            if area < POLE_AREA_M2 and ph.max() > POLE_HAG_M:
                pe, pn = float(np.median(E[sel])), float(np.median(N[sel]))
                rows.append({"kind": "pole", "e": round(pe, 2), "n": round(pn, 2), "hag_max_m": round(float(ph.max()), 2),
                             "points": int(sel.sum())})
            continue
        jj, ii = np.nonzero(lab[sl[k - 1]] == k)
        jj, ii = jj + sl[k - 1][0].start, ii + sl[k - 1][1].start
        cxy = np.c_[x0 + (ii + 0.5) * CELL_M, y1 - (jj + 0.5) * CELL_M]
        corners_pts = np.vstack([cxy + [dx, dy] for dx in (-CELL_M / 2, CELL_M / 2) for dy in (-CELL_M / 2, CELL_M / 2)])
        rect, rect_a = min_rect(corners_pts)
        fill = area / rect_a if rect_a > 0 else 0.0
        if fill >= RECT_FILL:
            ring, shape = rect, "rectangle"
        else:
            sub = (lab[sl[k - 1]] == k)
            ring = simplify(trace(sub, x0 + sl[k - 1][1].start * CELL_M, y1 - sl[k - 1][0].start * CELL_M, CELL_M),
                            SIMPLIFY_M)
            shape = "outline"
        p10, p50, p95 = (float(np.percentile(ph, q)) for q in (10, 50, 95))
        rz = float(np.median(Z[sel][ph >= p10]))
        # the ground ring
        tree = cKDTree(cxy)
        gx, gy = np.meshgrid(np.arange(cxy[:, 0].min() - RING_OUT_M, cxy[:, 0].max() + RING_OUT_M, 1.0),
                             np.arange(cxy[:, 1].min() - RING_OUT_M, cxy[:, 1].max() + RING_OUT_M, 1.0))
        dd, _ = tree.query(np.c_[gx.ravel(), gy.ravel()])
        ringm = (dd >= RING_IN_M) & (dd <= RING_OUT_M)
        ground = float(np.median(dem_at(gx.ravel()[ringm], gy.ravel()[ringm]))) if ringm.any() else None
        j_, i_ = crop.ij(cxy[:, 0], cxy[:, 1])
        sat = float(np.median(crop.sat[j_, i_]))
        rgb = np.median(crop.rgb[j_, i_], axis=0)
        rough = p95 - p10
        kind = "roof" if sat < VEG_SAT and (rough < ROUGH_M or fill >= RECT_FILL) else "tree"
        c = cxy.mean(0)
        d_lap = float(np.min(np.hypot(*(lap - c).T)))
        dims = sorted([float(np.hypot(*(rect[1] - rect[0]))), float(np.hypot(*(rect[2] - rect[1])))])
        rows.append({"kind": kind, "shape": shape, "area_m2": round(area, 1), "rect_m": [round(dims[1], 1), round(dims[0], 1)],
                     "fill": round(fill, 3), "centre_en": [round(float(c[0]), 2), round(float(c[1]), 2)],
                     "footprint_en": [[round(float(x), 2), round(float(y), 2)] for x, y in ring],
                     "hag_m": [round(p10, 2), round(p50, 2), round(p95, 2)], "roof_z_m": round(rz, 2),
                     "ground_m": None if ground is None else round(ground, 2), "points": int(sel.sum()),
                     "naip_sat": round(sat, 3), "naip_rgb": [int(v) for v in rgb], "lap_dist_m": round(d_lap, 1)})
    rows.sort(key=lambda r: -(r.get("area_m2") or 0))
    for i, r in enumerate(rows):
        r["id"] = i
    out = {"_doc": __doc__.split("\n\n")[0], "source": {"lidar": "CO_Eastern_ElPaso_2018 class 1 (infield.npz)",
           "dem": "infield_dem.npz (1 m)", "naip": crop.item, "flight_vs_photo": "lidar 2018, NAIP 2023-09-20"},
           "params": {"CELL_M": CELL_M, "MIN_HAG_M": MIN_HAG_M, "MIN_AREA_M2": MIN_AREA_M2, "RECT_FILL": RECT_FILL,
                      "VEG_SAT": VEG_SAT, "ROUGH_M": ROUGH_M}, "rows": rows}
    Path(a.out + ".json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    # the picture: the whole box at 0.5 m, every candidate outlined (roof yellow, tree green, pole red dot) and numbered
    S = 1.0 / CELL_M
    gx_ = x0 + (np.arange(nx) + 0.5) * CELL_M
    gy_ = y1 - (np.arange(ny) + 0.5) * CELL_M
    GX, GY = np.meshgrid(gx_, gy_)
    j_, i_ = crop.ij(GX, GY)
    img = Image.fromarray((crop.rgb[j_, i_] * 0.75).astype(np.uint8))
    dr = ImageDraw.Draw(img)

    def px(e, n_):
        return ((e - x0) * S, (y1 - n_) * S)
    for r in rows:
        if r["kind"] == "pole":
            p = px(r["e"], r["n"])
            dr.ellipse([p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3], outline=(255, 0, 0))
            continue
        ring = [px(*q) for q in r["footprint_en"]]
        dr.line(ring + [ring[0]], fill=(255, 230, 0) if r["kind"] == "roof" else (0, 255, 0), width=2)
        p = px(*r["centre_en"])
        dr.text((p[0] + 4, p[1] - 6), str(r["id"]), fill=(255, 255, 255))
    lp = [px(*q) for q in lap]
    dr.line(lp + [lp[0]], fill=(0, 200, 255), width=1)
    img.save(a.out + ".png")
    nr = sum(r["kind"] == "roof" for r in rows)
    print(f"[buildings] {n} pieces over {MIN_HAG_M} m: {nr} roofs, {sum(r['kind'] == 'tree' for r in rows)} trees, "
          f"{sum(r['kind'] == 'pole' for r in rows)} poles -> {a.out}.json / .png")
    for r in rows[:40]:
        if r["kind"] != "pole":
            print(f"  #{r['id']:3d} {r['kind']:4s} {r['shape']:9s} {r['area_m2']:7.1f} m2 {r['rect_m'][0]:6.1f} x {r['rect_m'][1]:5.1f} "
                  f"fill {r['fill']:.2f} hag {r['hag_m']} roof_z {r['roof_z_m']:+.2f} ground {r['ground_m']} sat {r['naip_sat']} "
                  f"rgb {r['naip_rgb']} at ({r['centre_en'][0]:.0f}, {r['centre_en'][1]:.0f}) {r['lap_dist_m']} m off the lap")
    return 0


if __name__ == "__main__":
    sys.exit(main())
