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


def main() -> int:
    track = Path(sys.argv[1])
    plan = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
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
