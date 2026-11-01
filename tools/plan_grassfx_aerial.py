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
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plan_bespoke_vegetation import geo  # noqa: E402


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
    all_rects = []
    for k, cells in by_class.items():
        all_rects += [(w * h, k, i, j, w, h) for i, j, w, h in rects(cells)]
    all_rects.sort(reverse=True)
    kept = all_rects[: int(spec.get("max_rects", 48))]
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
