"""Read where plants stand off a georeferenced aerial and write the file tools/author_bespoke_blend.py "cards" stands them from.

The plants' POSITIONS and the wood's edge are measured: a pixel is vegetation when it passes the track's own colour rule on the
photograph. Species share and heights are [invented] within the ranges declared in the plan (regional knowledge, cited in
each track's README). Interior trees are thinned, as a car only ever sees the wood's edge.

    python tools/plan_bespoke_vegetation.py <track-dir> <plan.json>

plan.json = {
  "image": "source/naip_2022_mrc.jpg",
  "bbox_lonlat": [w, s, e, n]                  north-up raster corners; or "webmerc": {"z", "x0", "y0"} for a tiles.py stitch
  "track_box_lonlat": [w, s, e, n],            only plants here
  "rule": {"max_mean": 96, "g_over_r": 1.02, "g_over_b": 1.10, "min_mean": 20}
  "step_m": 9, "jitter_m": 3,
  "edge_m": 40, "interior_keep": 0.25,         keep every plant within edge_m of the patch's edge, this share past it
  "min_patch_px": 40,                          a smaller blob is a shadow or a bush
  "species": [[cell, share, h_lo, h_hi, w_over_h], ...], "cols": 2, "rows": 2, "seed": 1, "out": "source/bespoke/trees.json"
}
Prints how many plants, the mean colour of the non-plant ground the photograph shows (the number a ground tile takes), and the
share of the box the rule called plant, so the rule can be laid beside the picture.
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

from PIL import Image


def geo(plan, w, h):
    """(lon, lat) -> pixel, and the metres per pixel at the box's middle"""
    if "bbox_lonlat" in plan:
        W, S, E, N = plan["bbox_lonlat"]
        return (lambda lon, lat: ((lon - W) / (E - W) * w, (N - lat) / (N - S) * h))
    z, x0, y0 = plan["webmerc"]["z"], plan["webmerc"]["x0"], plan["webmerc"]["y0"]

    def f(lon, lat):
        tx = (lon + 180) / 360 * 2 ** z
        r = math.radians(lat)
        ty = (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * 2 ** z
        return ((tx - x0) * 256, (ty - y0) * 256)
    return f


LIDAR_TREE_H = (2.0, 35.0)   # [invented] a canopy "height" outside this is a roof, a wire or noise, not a tree top


def crowns(track: Path, plan: dict) -> int:
    """plan "place": "crowns" (ledger 0079, Sand Creek on Lake Murray's engine; Kevin 2026-11-04: trees from measured
    positions, no invented scatter). ONE TREE PER CROWN READ OFF THE PHOTOGRAPH, no grid, no jitter, no thinning, no
    random draw:

      mask    a pixel is canopy when its 3x3 mean passes the plan's colour rule (the same rule as the grid mode);
              blobs under "min_crown_m2" are dropped (a bush, a shadow);
      tops    a crown top is a local maximum of the canopy's brightness, Gaussian-smoothed at "smooth_m", inside the
              mask and at least "edge_m_min" in from its edge (the sunlit top of a crown is its brightest part), no two
              closer than "min_sep_m" (a maximum filter of that radius);
      crown   each top's crown radius = min(its distance to the canopy edge + "edge_m_min", half the distance to the
              nearest other top, "max_radius_m"); the crown WIDTH is measured, so the size is;
      species "wood_m2": a top on a canopy patch larger than this is the plan's "wood" cell (Sand Creek's cottonwood
              bottoms), else its "single" cell (street and yard trees) [the threshold is invented];
      height  width / the cell's w_over_h [invented ratio: NAIP has no height in it].

    Writes the same points file as the grid mode ([lon, lat, cell, h, w]) and, with "overview", a JPEG of the box with
    every crown drawn on the photograph (the proof, L12)."""
    import numpy as np
    from scipy import ndimage as ndi
    from PIL import ImageDraw
    c = plan["crowns"]
    img = Image.open(track / plan["image"]).convert("RGB")
    w, h = img.size
    to_px = geo(plan, w, h)
    W, S, E, N = plan["track_box_lonlat"]
    lat_mid = (S + N) / 2
    m_lat = 111320.0
    m_lon = 111320.0 * math.cos(math.radians(lat_mid))
    x0, y0 = (int(math.floor(v)) for v in to_px(W, N))
    x1, y1 = (int(math.ceil(v)) for v in to_px(E, S))
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    m_per_px = (E - W) * m_lon / max(1.0, (to_px(E, S)[0] - to_px(W, N)[0]))
    a = np.asarray(img.crop((x0, y0, x1, y1)), dtype=np.float32)
    r, g, b = (ndi.uniform_filter(a[..., k], 3) for k in range(3))
    mean = (r + g + b) / 3.0
    rule = plan["rule"]
    valid = a.sum(axis=2) > 0                                  # a missing tile reads black: never canopy, never ground
    mask = valid & (mean >= rule.get("min_mean", 0)) & (mean <= rule["max_mean"]) & (g >= r * rule["g_over_r"]) & (g >= b * rule["g_over_b"])
    if "min_exg" in rule:                                      # excess green 2g - r - b: a sunlit crown, not a lawn, a lot or a shadow
        mask &= (2 * g - r - b) >= float(rule["min_exg"])
    lab, n = ndi.label(mask)
    areas = ndi.sum(np.ones_like(mean), lab, index=np.arange(1, n + 1)) * m_per_px ** 2
    keep_lab = np.zeros(n + 1, bool)
    keep_lab[1:] = areas >= float(c["min_crown_m2"])
    mask = keep_lab[lab]
    patch_m2 = np.zeros(n + 1)
    patch_m2[1:] = areas
    edt = ndi.distance_transform_edt(mask) * m_per_px
    bright = ndi.gaussian_filter(np.where(mask, mean, 0.0), float(c["smooth_m"]) / m_per_px)
    sep_px = max(1, int(round(float(c["min_sep_m"]) / m_per_px)))
    peaks = (bright == ndi.maximum_filter(bright, size=2 * sep_px + 1)) & mask & (edt >= float(c["edge_m_min"]))
    py, px_ = np.nonzero(peaks)
    order = np.argsort(-bright[py, px_])
    py, px_ = py[order], px_[order]
    # plateaus: a flat maximum yields several equal pixels; keep the first of any within min_sep
    from scipy.spatial import cKDTree
    kept = []
    tree = None
    pts_px = np.stack([px_, py], axis=1).astype(float)
    taken = np.zeros(len(pts_px), bool)
    if len(pts_px):
        tree = cKDTree(pts_px)
        for i in range(len(pts_px)):
            if taken[i]:
                continue
            kept.append(i)
            for j in tree.query_ball_point(pts_px[i], sep_px - 0.5):
                taken[j] = True
    tops = pts_px[kept] if kept else np.zeros((0, 2))
    nn = np.full(len(tops), np.inf)
    if len(tops) > 1:
        dd, _ = cKDTree(tops).query(tops, k=2)
        nn = dd[:, 1] * m_per_px
    cells = {"wood": int(c["wood_cell"]), "single": int(c["single_cell"])}
    w_over_h = {int(k): float(v) for k, v in c["w_over_h"].items()}
    # "wood_near": {"file": <OSM waterway lines {"ways": [{"lonlat": [...]}]}>, "within_m": d}: a crown within d of a
    # mapped creek is the wood cell (the riparian bottoms), whatever its patch size
    wood_segs = None
    if c.get("wood_near"):
        ways = json.loads((track / c["wood_near"]["file"]).read_text(encoding="utf-8"))["ways"]
        segs = [((p[0] - W) * m_lon, (p[1] - S) * m_lat, (q[0] - W) * m_lon, (q[1] - S) * m_lat)
                for wy in ways for p, q in zip(wy["lonlat"], wy["lonlat"][1:])]
        wood_segs = tuple(np.array(v) for v in zip(*segs)) if segs else None
    # "lidar": {"file": <tools/lidar_buildings.py --trees output>} (ledger 0079 round B): each crown's canopy height measured
    # off the lidar, keyed "lon,lat" as written here, taken before the [invented] width ratio; absent = the ratio for all.
    # The crown positions are the photograph's either way, so the keys match the file the lidar step read
    lidar_h, n_lidar = {}, 0
    if plan.get("lidar") and (track / plan["lidar"]["file"]).exists():
        lidar_h = json.loads((track / plan["lidar"]["file"]).read_text(encoding="utf-8"))["trees"]
    points, by_cell, drawn = [], {}, []
    for k, (tx, ty) in enumerate(tops):
        ix, iy = int(tx), int(ty)
        rad = min(float(edt[iy, ix]) + float(c["edge_m_min"]), nn[k] / 2.0, float(c["max_radius_m"]))
        cell = cells["wood"] if patch_m2[lab[iy, ix]] > float(c.get("wood_m2", float("inf"))) else cells["single"]
        wd = 2.0 * rad
        hh = wd / w_over_h[cell]
        gx, gy = x0 + tx + 0.5, y0 + ty + 0.5
        # pixel -> lon / lat (the inverse of geo(): linear in a north-up box, web mercator otherwise)
        if "bbox_lonlat" in plan:
            BW, BS, BE, BN = plan["bbox_lonlat"]
            lon, lat = BW + gx / w * (BE - BW), BN - gy / h * (BN - BS)
        else:
            z, X0, Y0 = plan["webmerc"]["z"], plan["webmerc"]["x0"], plan["webmerc"]["y0"]
            txf, tyf = X0 + gx / 256.0, Y0 + gy / 256.0
            lon = txf / 2 ** z * 360.0 - 180.0
            lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * tyf / 2 ** z))))
        if not (W <= lon <= E and S <= lat <= N):
            continue
        if wood_segs is not None and cell != cells["wood"]:
            qx, qy = (lon - W) * m_lon, (lat - S) * m_lat
            ax, ay, bx, by = wood_segs
            dx, dy = bx - ax, by - ay
            t = np.clip(((qx - ax) * dx + (qy - ay) * dy) / np.maximum(dx * dx + dy * dy, 1e-9), 0.0, 1.0)
            if float(np.min(np.hypot(ax + t * dx - qx, ay + t * dy - qy))) <= float(c["wood_near"]["within_m"]):
                cell = cells["wood"]
        lt = lidar_h.get(f"{round(lon, 7):.7f},{round(lat, 7):.7f}")
        if lt is not None and LIDAR_TREE_H[0] <= lt["h_m"] <= LIDAR_TREE_H[1]:
            hh = lt["h_m"]                          # measured canopy over the ground (tools/lidar_buildings.py --trees)
            n_lidar += 1
        points.append([round(lon, 7), round(lat, 7), cell, round(hh, 2), round(wd, 2)])
        drawn.append((tx, ty))
        by_cell[cell] = by_cell.get(cell, 0) + 1
    out = track / plan["out"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"_source": plan.get("_source", ""), "cols": plan["cols"], "rows": plan["rows"], "points": points},
                              separators=(",", ":")), encoding="utf-8", newline="\n")
    share = float(mask[valid].mean()) if valid.any() else 0.0
    print(f"{track.name}: {len(points)} crowns read ({by_cell} by cell), {share:.1%} of the box is canopy by the rule, "
          f"{m_per_px:.2f} m/px; heights off the lidar {n_lidar} (the rest by the ratio); crown width p10/p50/p90 "
          f"{np.percentile([p[4] for p in points], [10, 50, 90]).round(1).tolist() if points else []} m -> {out.relative_to(track)}")
    if plan.get("overview"):
        crop = img.crop((x0, y0, x1, y1))
        scale = min(1.0, float(plan.get("overview_px", 6000)) / max(crop.size))
        ov = crop.resize((max(1, int(crop.size[0] * scale)), max(1, int(crop.size[1] * scale))), Image.LANCZOS)
        dr = ImageDraw.Draw(ov)
        for (tx, ty), p in zip(drawn, points):
            rr = max(1.0, p[4] / 2.0 / m_per_px * scale)
            cx, cy = (tx + 0.5) * scale, (ty + 0.5) * scale
            col = (255, 60, 40) if p[2] == cells["wood"] else (40, 200, 255)
            dr.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=col, width=1)
            dr.point((cx, cy), fill=(255, 255, 0))
        ovp = track / plan["overview"]
        ovp.parent.mkdir(parents=True, exist_ok=True)
        ov.save(ovp, quality=85)
        print(f"  overview: every crown on the photograph (red = {cells['wood']} wood, blue = {cells['single']} single) -> {ovp.relative_to(track)}")
    return 0


def main() -> int:
    track = Path(sys.argv[1])
    plan = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    if plan.get("place") == "crowns":
        return crowns(track, plan)
    img = Image.open(track / plan["image"]).convert("RGB")
    w, h = img.size
    px = img.load()
    to_px = geo(plan, w, h)
    W, S, E, N = plan["track_box_lonlat"]
    lat_mid = (S + N) / 2
    m_lat = 111320.0
    m_lon = 111320.0 * math.cos(math.radians(lat_mid))
    step = float(plan["step_m"])
    rule = plan["rule"]
    x0, y0 = to_px(W, N)
    x1, y1 = to_px(E, S)
    m_per_px = (E - W) * m_lon / max(1.0, x1 - x0)
    # the mask on a coarse grid, a blur's worth of pixels averaged per cell: one crown, not one leaf
    cell_m = max(2.0, step / 3.0)
    nx, ny = int((E - W) * m_lon / cell_m), int((N - S) * m_lat / cell_m)
    r_px = max(1, int(cell_m / m_per_px / 2))
    mask = [[False] * nx for _ in range(ny)]
    ground = [0, 0, 0, 0]
    for j in range(ny):
        lat = N - (j + 0.5) * cell_m / m_lat
        for i in range(nx):
            lon = W + (i + 0.5) * cell_m / m_lon
            cx, cy = to_px(lon, lat)
            cx, cy = int(cx), int(cy)
            if not (r_px <= cx < w - r_px and r_px <= cy < h - r_px):
                continue
            rr = gg = bb = 0
            n = 0
            for yy in range(cy - r_px, cy + r_px + 1, max(1, r_px)):
                for xx in range(cx - r_px, cx + r_px + 1, max(1, r_px)):
                    a = px[xx, yy]
                    rr += a[0]; gg += a[1]; bb += a[2]; n += 1
            rr /= n; gg /= n; bb /= n
            mean = (rr + gg + bb) / 3
            hit = (rule.get("min_mean", 0) <= mean <= rule["max_mean"] and gg >= rr * rule["g_over_r"] and gg >= bb * rule["g_over_b"])
            mask[j][i] = hit
            if not hit:
                ground[0] += rr; ground[1] += gg; ground[2] += bb; ground[3] += 1
    # patches: drop the small ones, measure each kept cell's distance to the edge in cells
    seen = [[False] * nx for _ in range(ny)]
    keep = [[False] * nx for _ in range(ny)]
    patches = 0
    for j in range(ny):
        for i in range(nx):
            if not mask[j][i] or seen[j][i]:
                continue
            stack, blob = [(i, j)], []
            seen[j][i] = True
            while stack:
                a, b = stack.pop()
                blob.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    c, d = a + da, b + db
                    if 0 <= c < nx and 0 <= d < ny and mask[d][c] and not seen[d][c]:
                        seen[d][c] = True
                        stack.append((c, d))
            if len(blob) >= plan.get("min_patch_px", 4):
                patches += 1
                for a, b in blob:
                    keep[b][a] = True
    edge_cells = max(1, int(plan.get("edge_m", 40) / cell_m))
    dist = [[0 if keep[j][i] else -1 for i in range(nx)] for j in range(ny)]
    frontier = [(i, j) for j in range(ny) for i in range(nx) if not keep[j][i]]
    d = 0
    near = set(frontier)
    # distance from outside, walked inward up to edge_cells
    for d in range(1, edge_cells + 1):
        nxt = []
        for a, b in frontier:
            for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                c, e = a + da, b + db
                if 0 <= c < nx and 0 <= e < ny and keep[e][c] and dist[e][c] == 0:
                    dist[e][c] = d
                    nxt.append((c, e))
        frontier = nxt
    rng = random.Random(int(plan["seed"]))
    species = plan["species"]
    total = sum(s[1] for s in species)
    points = []
    gx, gy = int(round((E - W) * m_lon / step)), int(round((N - S) * m_lat / step))
    for gj in range(gy):
        for gi in range(gx):
            ex = gi * step + (step / 2 if gj % 2 else 0) + rng.uniform(-plan["jitter_m"], plan["jitter_m"])
            ey = gj * step + rng.uniform(-plan["jitter_m"], plan["jitter_m"])
            i, j = int(ex / cell_m), int(ey / cell_m)
            pick, inner = rng.random(), rng.random()
            sp = rng.random() * total
            hrand, wrand = rng.random(), rng.uniform(0.85, 1.15)
            if not (0 <= i < nx and 0 <= j < ny) or not keep[j][i]:
                continue
            if dist[j][i] == 0 and inner > plan.get("interior_keep", 1.0):          # dist 0 = further in than edge_cells
                continue
            for s in species:
                sp -= s[1]
                if sp <= 0:
                    break
            hh = s[2] + (s[3] - s[2]) * hrand
            points.append([round(W + ex / m_lon, 7), round(N - ey / m_lat, 7), s[0], round(hh, 2), round(hh * s[4] * wrand, 2)])
    out = track / plan["out"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"_source": plan.get("_source", ""), "cols": plan["cols"], "rows": plan["rows"], "points": points}, separators=(",", ":")),
                   encoding="utf-8", newline="\n")
    share = sum(sum(1 for v in row if v) for row in keep) / float(nx * ny)
    g = [round(v / max(1, ground[3])) for v in ground[:3]]
    print(f"{track.name}: {len(points)} plants in {patches} patches, {share:.1%} of the box is plant by the rule, "
          f"{m_per_px:.2f} m/px; ground (not plant) mean RGB {g}; -> {out.relative_to(track)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
