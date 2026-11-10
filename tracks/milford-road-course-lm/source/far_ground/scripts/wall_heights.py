"""Every off-terrain block's wall, before and after the far ground (ledger 0082 'Far ground (0.1.11)'): from each build's log line
`[bespoke] block <key>: ..., ground <lo>..<hi>, bottom <b>, eave <e>` (tools/author_bespoke_blend.py: the built ground under the
walls, scene frame), the wall from the lowest built ground to the roof (eave - lo), against the REAL ground: the lidar
product's (data/far_ground.lidar.npy) lowest value on a 1 m lattice over a ring LIDAR_RING_M outside the footprint (the
returns under a roof are none: the ground beside the walls is what the lidar measures), scene frame = NAVD88 - the origin's
elevation.

    python wall_heights.py <before.log> <after.log> <track dir> [--json out.json]
"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "tools"))
import far_ground as fg  # noqa: E402

LINE = re.compile(r"\[bespoke\] block (\S+): .*?walls ([0-9.]+) m, \w+, ground (-?[0-9.]+)\.\.(-?[0-9.]+), bottom (-?[0-9.]+), eave (-?[0-9.]+)")
LIDAR_RING_M = (1.0, 4.0)


def blocks(log):
    out = {}
    for ln in Path(log).read_text(encoding="utf-8", errors="replace").splitlines():
        m = LINE.search(ln)
        if m:
            k = m.group(1)
            out[k] = {"wall_m": float(m.group(2)), "ground_lo": float(m.group(3)), "ground_hi": float(m.group(4)),
                      "bottom": float(m.group(5)), "eave": float(m.group(6))}
    return out


def in_rect(px, py, ring, grow):
    """inside the footprint's quad grown by ``grow`` (convex, either winding)"""
    n = len(ring)
    s = 0
    for k in range(n):
        (x0, y0), (x1, y1) = ring[k], ring[(k + 1) % n]
        ex, ey = x1 - x0, y1 - y0
        L = math.hypot(ex, ey) or 1.0
        c = (ex * (py - y0) - ey * (px - x0)) / L
        s += 1 if c > 0 else 0
    sign = 1 if s * 2 >= n else -1
    for k in range(n):
        (x0, y0), (x1, y1) = ring[k], ring[(k + 1) % n]
        ex, ey = x1 - x0, y1 - y0
        L = math.hypot(ex, ey) or 1.0
        if sign * (ex * (py - y0) - ey * (px - x0)) / L < -grow:
            return False
    return True


def main(argv):
    bef, aft, track = blocks(argv[0]), blocks(argv[1]), Path(argv[2])
    dem = fg.Dem.load(track / "data")
    o = json.loads((track / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
    phi = math.radians(o["lat"])
    m_lon = 111_412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi)
    m_lat = 111_132.92 - 559.82 * math.cos(2 * phi)
    fps = {}
    for f in sorted((track / "source" / "furniture").glob("pass*/blocks.json")):
        for b in json.loads(f.read_text(encoding="utf-8")):
            fps[b["key"]] = [((lo - o["lon"]) * m_lon, (la - o["lat"]) * m_lat) for lo, la in b["footprint_lonlat"]]
    cfg = json.loads((track / "track.config.json").read_text(encoding="utf-8"))
    for g in cfg["scenery"]["bespoke"].get("blocks", []):
        if "footprint_lonlat" in g and "key" in g:
            fps.setdefault(g["key"], [((lo - o["lon"]) * m_lon, (la - o["lat"]) * m_lat) for lo, la in g["footprint_lonlat"]])
    rows = []
    for k in sorted(set(bef) | set(aft)):
        b, a = bef.get(k), aft.get(k)
        r = {"key": k}
        ring = fps.get(k)
        if ring:
            xs, ys = [p[0] for p in ring], [p[1] for p in ring]
            lo_l = None
            for x in np.arange(min(xs) - 5, max(xs) + 5, 1.0):
                for y in np.arange(min(ys) - 5, max(ys) + 5, 1.0):
                    if in_rect(x, y, ring, LIDAR_RING_M[1]) and not in_rect(x, y, ring, LIDAR_RING_M[0]):
                        z = dem.at(x, y) - o["elev_m"]
                        lo_l = z if lo_l is None else min(lo_l, z)
            r["lidar_ground_lo"] = None if lo_l is None else round(lo_l, 2)
        for tag, v in (("before", b), ("after", a)):
            if v:
                r[tag] = {"ground": [v["ground_lo"], v["ground_hi"]], "eave": v["eave"],
                          "wall_lo_to_roof_m": round(v["eave"] - v["ground_lo"], 2),
                          "lo_vs_lidar_m": None if r.get("lidar_ground_lo") is None else round(v["ground_lo"] - r["lidar_ground_lo"], 2)}
        if r.get("lidar_ground_lo") is not None and (a or b):
            r["real_wall_lo_to_roof_m"] = round((a or b)["eave"] - r["lidar_ground_lo"], 2)
        rows.append(r)
    print(f"{'block':22s} {'roof':>7s} | {'0.1.10 lo':>9s} {'wall':>6s} | {'0.1.11 lo':>9s} {'wall':>6s} | {'lidar lo':>8s} {'real':>6s} | {'0.1.11-lidar':>12s}")
    for r in rows:
        b, a = r.get("before") or {}, r.get("after") or {}
        f = lambda v, w=6: (f"{v:{w}.2f}" if isinstance(v, (int, float)) else " " * (w - 1) + "-")
        print(f"{r['key']:22s} {f((a or b).get('eave'), 7)} | {f(b.get('ground', [None])[0], 9)} {f(b.get('wall_lo_to_roof_m'))} | "
              f"{f(a.get('ground', [None])[0], 9)} {f(a.get('wall_lo_to_roof_m'))} | {f(r.get('lidar_ground_lo'), 8)} "
              f"{f(r.get('real_wall_lo_to_roof_m'))} | {f(a.get('lo_vs_lidar_m'), 12)}")
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(json.dumps({"_doc": __doc__.split("\n\n")[0], "rows": rows}, indent=1),
                                                        encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
