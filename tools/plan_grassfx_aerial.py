"""GrassFX zones read off the track's aerial: where the photograph shows long grass, bare ground or a wood floor, CSP gets a world
rectangle bound to that look (docs/TREEFX-FORMAT.md, [GRASS_FX_ADJUSTMENT_<name>] CENTER, SIZE, FADE + MAP).

    python tools/plan_grassfx_aerial.py <project-dir>

The project's track.config.json lighting.grassfx holds the looks ("configurations": {"A": {...}, ...}, the fleet's own grammar) and
scenery.bespoke.grassfx_zones the reading:
  {"image", "bbox_lonlat" | "webmerc", "cell_m": 40, "max_rects": 48, "fade_m": 12,
   "classes": [{"map": "B", "mean": [lo, hi], "g_over_r": [lo, hi], "g_over_b": [lo, hi]}, ...]}     first class that fits wins
A grid cell takes the class most of its pixels fit, if at least half do; everything else keeps the track's base look. Neighbouring
cells of a class are merged into rectangles, largest first, up to max_rects. Writes data/grassfx.aerial.json, which
scripts/ac/ext_config.py adds to the block. The rule's bounds are per track and [invented] by reading that photograph; the
rectangles are what it says. Frame: kn5 = the local frame with z mirrored. VERIFY IN-GAME.

Opt-in keys (ledger 0092, Milford; a reading without them is byte for byte what it was):
  "frame": "projection"   the cells read the image through scripts.geometry.projection's metres per degree (the frame the
                          draft, the pads and the lidar use) instead of 111,320 m per degree of latitude
  "near": {"cell_m": 6, "reach_m": 30}   every cell_m cell with a part within reach_m of the lane edge is read as fine cells
                          of near.cell_m (cell_m a whole multiple of it), merged into rectangles of their own
  "pad_looks": [{"prefix": "ride_pad", "map": "D"}, {"prefix": "runoff_", "map": null}]   a cell (fine or not) whose samples lie
                          mostly inside a scenery.bespoke.pads footprint whose key starts with prefix takes that look (null:
                          the base look, no rectangle); the first rule that holds wins
  "fade_by_map": {"B": 12}  a look's own fade (else fade_m)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plan_bespoke_vegetation import geo  # noqa: E402

FINE_SAMPLES = 6     # a fine cell is read as the base one is: 6 x 6 samples, the class at least half of them fit


def fits(cl, mean, gr, gb):
    return (cl.get("mean", [0, 999])[0] <= mean <= cl.get("mean", [0, 999])[1] and cl.get("g_over_r", [0, 99])[0] <= gr <= cl.get("g_over_r", [0, 99])[1]
            and cl.get("g_over_b", [0, 99])[0] <= gb <= cl.get("g_over_b", [0, 99])[1])


def rects(cells):
    """greedy: the biggest rectangle of a set of (i, j), repeatedly"""
    left = set(cells)
    out = []
    while left:
        best = None
        for (i, j) in left:
            w = 1
            while (i + w, j) in left:
                w += 1
            h = 1
            cur = w
            while True:
                row = 0
                while row < cur and (i + row, j + h) in left:
                    row += 1
                if row == 0:
                    break
                if row * (h + 1) >= cur * h:
                    cur = row
                    h += 1
                else:
                    break
            if best is None or cur * h > best[2] * best[3]:
                best = (i, j, cur, h)
        i, j, w, h = best
        for a in range(i, i + w):
            for b in range(j, j + h):
                left.discard((a, b))
        out.append(best)
    return out


def read_cell(spec, src, o, xl, zb, size):
    """the class index most of a cell's FINE_SAMPLES x FINE_SAMPLES samples fit, if at least half do, else None"""
    px, to_px, img, m_lon, m_lat = src
    counts = [0] * len(spec["classes"])
    n = 0
    for a in range(FINE_SAMPLES):
        for b in range(FINE_SAMPLES):
            x, z = xl + (a + 0.5) / FINE_SAMPLES * size, zb + (b + 0.5) / FINE_SAMPLES * size
            u, v = to_px(o["lon"] + x / m_lon, o["lat"] + z / m_lat)
            if not (0 <= u < img.width and 0 <= v < img.height):
                continue
            r, g, bl = px[int(u), int(v)]
            n += 1
            mean, gr, gb = (r + g + bl) / 3, g / max(1, r), g / max(1, bl)
            for k, c in enumerate(spec["classes"]):
                if fits(c, mean, gr, gb):
                    counts[k] += 1
                    break
    return counts.index(max(counts)) if n and max(counts) * 2 >= n else None


def point_in(poly, x, z):
    c = False
    for k in range(len(poly)):
        (x1, z1), (x2, z2) = poly[k - 1], poly[k]
        if (z1 > z) != (z2 > z) and x < x1 + (z - z1) * (x2 - x1) / (z2 - z1):
            c = not c
    return c


def pad_rings(cfg, o, m_lon, m_lat):
    """(key, ring in local metres, bbox) per scenery.bespoke.pads entry: a quad, or a strip's inner + outer reversed"""
    out = []
    for p in (cfg.get("scenery", {}).get("bespoke") or {}).get("pads") or []:
        if "strip_lonlat" in p:
            ll = list(p["strip_lonlat"]["inner"]) + list(p["strip_lonlat"]["outer"])[::-1]
        elif "quad_lonlat" in p:
            ll = list(p["quad_lonlat"])
        else:
            continue
        ring = [((lon - o["lon"]) * m_lon, (lat - o["lat"]) * m_lat) for lon, lat in ll]
        xs, zs = [q[0] for q in ring], [q[1] for q in ring]
        out.append((p["key"], ring, (min(xs), max(xs), min(zs), max(zs))))
    return out


def pad_look(rules, rings, xl, zb, size, spec):
    """the first pad_looks rule whose pads hold at least half the cell's samples: (True, class index or None), else (False, None)"""
    for rule in rules:
        mine = [(ring, bb) for key, ring, bb in rings if key.startswith(rule["prefix"])
                and bb[0] <= xl + size and bb[1] >= xl and bb[2] <= zb + size and bb[3] >= zb]
        if not mine:
            continue
        n_in = 0
        for a in range(FINE_SAMPLES):
            for b in range(FINE_SAMPLES):
                x, z = xl + (a + 0.5) / FINE_SAMPLES * size, zb + (b + 0.5) / FINE_SAMPLES * size
                if any(bb[0] <= x <= bb[1] and bb[2] <= z <= bb[3] and point_in(ring, x, z) for ring, bb in mine):
                    n_in += 1
        if n_in * 2 >= FINE_SAMPLES * FINE_SAMPLES:
            m = rule.get("map")
            if m is None:
                return True, None
            ks = [k for k, c in enumerate(spec["classes"]) if c["map"] == m]
            if not ks:
                raise SystemExit(f"[grassfx] pad_looks: no class maps {m!r}")
            return True, ks[0]
    return False, None


def lane_edge_distance(cl, qx, qz):
    """distance of each query point to the lane edge (centreline +- width / 2), numpy, chunked"""
    import numpy as np
    P = np.array(cl["points_xyz_m"], float)[:, [0, 2]]
    half = np.array(cl["widths_m"], float) / 2.0
    ax, az, bx, bz = P[:-1, 0], P[:-1, 1], P[1:, 0], P[1:, 1]
    dx, dz = bx - ax, bz - az
    L2 = np.where(dx * dx + dz * dz == 0, 1.0, dx * dx + dz * dz)
    qx, qz = np.asarray(qx, float), np.asarray(qz, float)
    out = np.empty(len(qx))
    for k in range(0, len(qx), 256):
        x, z = qx[k:k + 256, None], qz[k:k + 256, None]
        t = np.clip(((x - ax) * dx + (z - az) * dz) / L2, 0, 1)
        out[k:k + 256] = (np.hypot(x - ax - t * dx, z - az - t * dz) - (half[:-1] * (1 - t) + half[1:] * t)).min(1)
    return out


def refined(proj, cfg, spec, cl, out, by_class, grid, src):
    """opt-in near / pad_looks (ledger 0092): the base cells beside the road read again as fine cells, the pads' own looks,
    each set merged into rectangles of its own size"""
    x0, z0, cell, nx, nz = grid
    o = cl["origin"]
    near, rules = spec.get("near"), spec.get("pad_looks") or []
    rings = pad_rings(cfg, o, src[3], src[4]) if rules else []
    base = {(i, j): k for k, cells in by_class.items() for i, j in cells}
    fine_of, fcell, r = set(), cell, 1
    if near:
        fcell = float(near["cell_m"])
        r = int(round(cell / fcell))
        if r < 1 or abs(r * fcell - cell) > 1e-6:
            raise SystemExit(f"[grassfx] near.cell_m {fcell} must divide cell_m {cell}")
        cen = [(i, j, x0 + (i * r + a + 0.5) * fcell, z0 + (j * r + b + 0.5) * fcell)
               for i in range(nx) for j in range(nz) for a in range(r) for b in range(r)]
        d = lane_edge_distance(cl, [c[2] for c in cen], [c[3] for c in cen])
        reach = float(near["reach_m"])
        fine_of = {(c[0], c[1]) for c, dd in zip(cen, d) if dd < reach}
    coarse, fine = {}, {}
    for i in range(nx):
        for j in range(nz):
            if (i, j) in fine_of:
                for a in range(r):
                    for b in range(r):
                        fi, fj = i * r + a, j * r + b
                        xl, zb = x0 + fi * fcell, z0 + fj * fcell
                        hit, k = pad_look(rules, rings, xl, zb, fcell, spec) if rules else (False, None)
                        if not hit:
                            k = read_cell(spec, src, o, xl, zb, fcell)
                        if k is not None:
                            fine.setdefault(k, []).append((fi, fj))
                continue
            hit, k = pad_look(rules, rings, x0 + i * cell, z0 + j * cell, cell, spec) if rules else (False, None)
            if not hit:
                k = base.get((i, j))
            if k is not None:
                coarse.setdefault(k, []).append((i, j))
    all_rects = []
    for cells, size in ((coarse, cell), (fine, fcell)):
        for k, cs in cells.items():
            all_rects += [(w * h * size * size, k, x0 + i * size, z0 + j * size, w * size, h * size) for i, j, w, h in rects(cs)]
    all_rects.sort(reverse=True)
    cap = spec.get("max_rects", 48)
    kept = all_rects if cap is None else all_rects[: int(cap)]
    fade = float(spec.get("fade_m", 12.0))
    fade_by = spec.get("fade_by_map") or {}
    ys = [p[1] for p in cl["points_xyz_m"]]
    mid_y = (min(ys) + max(ys)) / 2
    adj = []
    for area, k, xl, zb, w, h in kept:
        m = spec["classes"][k]["map"]
        cx, cz = xl + w / 2, zb + h / 2
        adj.append({"map": m, "rect": {"center": [round(cx, 1), round(mid_y, 1), round(-cz, 1)], "size": [round(w, 1), round(h, 1)],
                                       "fade": float(fade_by.get(m, fade))}})
    out.write_text(json.dumps({"adjustments": adj}, indent=0), encoding="utf-8", newline="\n")
    area = {spec["classes"][k]["map"]: round(sum(a[0] for a in all_rects if a[1] == k)) for k in {a[1] for a in all_rects}}
    print(f"[grassfx] {nx} x {nz} cells of {cell:.0f} m, {len(fine_of)} of them read as {r * r} cells of {fcell:.0f} m "
          f"(within {float(near['reach_m']) if near else 0:.0f} m of the lane edge); pad looks {[q['prefix'] for q in rules]}; "
          f"m2 per look {area}; {len(all_rects)} rectangles, {len(kept)} kept -> {out.name}")
    return 0


def main() -> int:
    proj = Path(sys.argv[1])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    spec = (cfg.get("scenery", {}).get("bespoke") or {}).get("grassfx_zones")
    out = proj / "data" / "grassfx.aerial.json"
    if not spec:
        print("[grassfx] no scenery.bespoke.grassfx_zones: nothing to read")
        out.unlink(missing_ok=True)
        return 0
    cl = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    o = cl["origin"]
    xs = [p[0] for p in cl["points_xyz_m"]]
    zs = [p[2] for p in cl["points_xyz_m"]]
    margin = float(spec.get("margin_m", 150.0))
    x0, x1, z0, z1 = min(xs) - margin, max(xs) + margin, min(zs) - margin, max(zs) + margin
    img = Image.open(proj / spec["image"]).convert("RGB")
    px = img.load()
    to_px = geo(spec, img.width, img.height)
    m_lat = 111320.0
    m_lon = m_lat * math.cos(math.radians(o["lat"]))
    if spec.get("frame") == "projection":          # opt-in (ledger 0092): the draft's own frame
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from scripts.geometry.projection import _meters_per_degree
        m_lon, m_lat = _meters_per_degree(o["lat"])
    cell = float(spec.get("cell_m", 40.0))
    nx, nz = int((x1 - x0) / cell) + 1, int((z1 - z0) / cell) + 1
    by_class = {}
    for i in range(nx):
        for j in range(nz):
            counts = [0] * len(spec["classes"])
            n = 0
            for a in range(6):
                for b in range(6):
                    x, z = x0 + (i + (a + 0.5) / 6) * cell, z0 + (j + (b + 0.5) / 6) * cell
                    u, v = to_px(o["lon"] + x / m_lon, o["lat"] + z / m_lat)
                    if not (0 <= u < img.width and 0 <= v < img.height):
                        continue
                    r, g, bl = px[int(u), int(v)]
                    n += 1
                    mean, gr, gb = (r + g + bl) / 3, g / max(1, r), g / max(1, bl)
                    for k, c in enumerate(spec["classes"]):
                        if fits(c, mean, gr, gb):
                            counts[k] += 1
                            break
            if n and max(counts) * 2 >= n:
                by_class.setdefault(counts.index(max(counts)), []).append((i, j))
    near, pad_looks = spec.get("near"), spec.get("pad_looks")
    if near or pad_looks:                           # opt-in (ledger 0092): fine cells near the road, the pads' own looks
        return refined(proj, cfg, spec, cl, out, by_class, (x0, z0, cell, nx, nz), (px, to_px, img, m_lon, m_lat))
    all_rects = []
    for k, cells in by_class.items():
        all_rects += [(w * h, k, i, j, w, h) for i, j, w, h in rects(cells)]
    all_rects.sort(reverse=True)
    # max_rects: 48 when absent [invented, the first track's]; null = every rectangle the reading makes (Milford 0.1.5,
    # ledger 0082 Owed 4: the cap is this planner's, not CSP's — no limit on [GRASS_FX_ADJUSTMENT_...] sections is known)
    cap = spec.get("max_rects", 48)
    kept = all_rects if cap is None else all_rects[: int(cap)]
    fade = float(spec.get("fade_m", 12.0))
    ys = [p[1] for p in cl["points_xyz_m"]]
    mid_y = (min(ys) + max(ys)) / 2         # the grammar wants a height; a rectangle's reach is its size on the ground [unverified in CSP]
    adj = []
    for area, k, i, j, w, h in kept:
        cx, cz = x0 + (i + w / 2) * cell, z0 + (j + h / 2) * cell
        adj.append({"map": spec["classes"][k]["map"], "rect": {"center": [round(cx, 1), round(mid_y, 1), round(-cz, 1)], "size": [round(w * cell, 1), round(h * cell, 1)], "fade": fade}})
    out.write_text(json.dumps({"adjustments": adj}, indent=0), encoding="utf-8", newline="\n")
    sums = {spec["classes"][k]["map"]: sum(r[0] for r in all_rects if r[1] == k) for k in by_class}
    print(f"[grassfx] {nx} x {nz} cells of {cell:.0f} m; cells per look {sums}; {len(all_rects)} rectangles, {len(kept)} kept -> {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
