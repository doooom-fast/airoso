"""Every piece of furniture against the BUILT ground it stands on (L5; ledger 0082 pass 3). The bespoke tool seats furniture
on the AUTHOR scene's ground; engine-july's prep then re-conforms the ground near the road (a 3 m contact band at the lane
edge, a 6 m feather: ledger 0087 0.1.6). The PC found Pikes Peak's rails buried on banking that way, so this reads the
shipped geometry, the gate OBJ (data/track.obj, the road kn5 in the engine frame), and asks of every 0.5 m plan cell a
furniture object covers:

  exposed = its top - the built ground under it      (a rail whose ground rose round it shows less than it was built)
  gap     = its lowest vertex - the built ground     (> 5 cm, kn5_ground_check's tolerance: it floats)

The built ground under a cell is the HIGHEST of the 1GRASS / 1KERB / 1ROAD / PADAPRON triangles over the cell centre.
The intended top per class: the config's height_m for the line the cell is nearest (rails, tyre walls, screens), a block's
wall_h_m (buildings: reported, not judged: a footprint over relief shows more wall on its low side by design).
Exit 1 if any rail / tyre wall / screen shows less than its intended top - TOL_M over more than BURIED_SHARE of its
cells, or any of its cells floats. Not a chain gate: a report the pass runs on its build (and on 0.1.6's, for the column).

    python seat_built.py <workshop> [--json out.json]
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

GROUND = ("1GRASS", "1KERB", "1ROAD", "PADAPRON")
CLASSES = {"GUARDRAIL_W": "wbeam", "1WALL_TECPRO_TYRES": "tyres", "1WALL_TILTUP_SCREEN": "screen",
           "FARBLOCK": "block", "BUILDING_": "block", "ROOFTOP_": "roof"}
CELL = 0.5
TOL_M = 0.10            # [invented] a top this much under its intended height counts as buried
BURIED_SHARE = 0.02     # [invented] more than this share of an object's cells buried fails it
FLOAT_M = 0.05          # tools/kn5_ground_check.py's hover tolerance


def read(obj):
    V, cur, ground, furn = [], None, [], {}
    with open(obj, encoding="utf-8", errors="replace") as f:
        for ln in f:
            c = ln[:2]
            if c == "v ":
                p = ln.split()
                V.append((float(p[1]), float(p[2]), float(p[3])))
            elif ln.startswith("usemtl ") or c in ("o ", "g "):
                nm = ln.split(None, 1)[1].strip()
                up = nm.upper()
                if any(up.startswith(g) for g in GROUND):
                    cur = ("g", nm)
                else:
                    cls = next((v for k, v in CLASSES.items() if up.startswith(k)), None)
                    cur = ("f", nm, cls) if cls else None
            elif c == "f " and cur is not None:
                idx = [int(q.split("/")[0]) - 1 for q in ln.split()[1:]]
                if cur[0] == "g":
                    for i in range(1, len(idx) - 1):
                        ground.append((idx[0], idx[i], idx[i + 1]))
                else:
                    furn.setdefault(cur[1], (cur[2], set()))[1].update(idx)
    return np.array(V), np.array(ground, int), furn


class Ground:
    def __init__(self, V, T, cell=4.0):
        self.V, self.T, self.cell = V, T, cell
        P = V[T]                                         # (n, 3, 3)
        self.P = P
        lo, hi = P[:, :, [0, 2]].min(1), P[:, :, [0, 2]].max(1)
        self.grid = {}
        for k, (a, b) in enumerate(zip(np.floor(lo / cell).astype(int), np.floor(hi / cell).astype(int))):
            for i in range(a[0], b[0] + 1):
                for j in range(a[1], b[1] + 1):
                    self.grid.setdefault((i, j), []).append(k)

    def height(self, x, z):
        best = None
        for k in self.grid.get((int(math.floor(x / self.cell)), int(math.floor(z / self.cell))), ()):
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = self.P[k]
            den = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
            if abs(den) < 1e-12:
                continue
            l1 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / den
            l2 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / den
            l3 = 1 - l1 - l2
            if min(l1, l2, l3) >= -1e-9:
                y = l1 * ay + l2 * by + l3 * cy
                best = y if best is None else max(best, y)
        return best


def main():
    ws = Path(sys.argv[1])
    out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    cl = json.loads((ws / "data/centerline.local.json").read_text())
    o = cl["origin"]
    phi = math.radians(o["lat"])
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    cfg = json.loads((ws / "track.config.json").read_text())
    lines = []
    for r in cfg["scenery"]["bespoke"].get("rails", []):
        kind = r.get("kind")
        h = r.get("height_m") or {"wbeam": 0.70, "tyres": 1.0}.get(kind)
        pts = np.array([((p[0] - o["lon"]) * m_lon, (p[1] - o["lat"]) * m_lat) for p in r["polyline_lonlat"]])
        lines.append((r["key"], kind, float(h), pts))

    def nearest_line(x, z, kind):
        best = None
        for key, k, h, P in lines:
            if k != kind:
                continue
            a, b = P[:-1], P[1:]
            d = b - a
            L2 = (d * d).sum(1)
            t = np.clip(((np.array([x, z]) - a) * d).sum(1) / np.where(L2 > 0, L2, 1), 0, 1)
            q = a + t[:, None] * d
            dist = float(np.hypot(*(q - [x, z]).T).min())
            if best is None or dist < best[0]:
                best = (dist, key, h)
        return best

    V, T, furn = read(ws / "data/track.obj")
    G = Ground(V, T)
    rows, fails = [], []
    for name, (cls, idx) in sorted(furn.items()):
        if cls == "roof":
            continue
        P = V[sorted(idx)]
        cells = {}
        for x, y, z in P:
            k = (int(math.floor(x / CELL)), int(math.floor(z / CELL)))
            lo, hi = cells.get(k, (y, y))
            cells[k] = (min(lo, y), max(hi, y))
        ex, gap, buried, nog, keys = [], [], 0, 0, {}
        for (i, j), (lo, hi) in cells.items():
            x, z = (i + 0.5) * CELL, (j + 0.5) * CELL
            g = G.height(x, z)
            if g is None:
                nog += 1
                continue
            ex.append(hi - g)
            gap.append(lo - g)
            if cls in ("wbeam", "tyres", "screen"):
                nl = nearest_line(x, z, cls)
                if nl:
                    keys[nl[1]] = nl[2]
                    if hi - g < nl[2] - TOL_M:
                        buried += 1
        ex, gap = np.array(ex), np.array(gap)
        row = {"object": name, "class": cls, "cells": len(cells), "cells_no_ground": nog}
        if len(ex):
            row.update({"exposed_p5_p50_p95_m": [round(float(np.percentile(ex, q)), 3) for q in (5, 50, 95)],
                        "foot_gap_max_m": round(float(gap.max()), 3), "floating_cells": int((gap > FLOAT_M).sum())})
        if cls in ("wbeam", "tyres", "screen"):
            row.update({"lines": keys, "buried_cells": buried})
            share = buried / max(1, len(ex))
            if share > BURIED_SHARE or row.get("floating_cells", 0):
                fails.append(f"{name}: {buried} of {len(ex)} cells under the intended top by > {TOL_M} m, "
                             f"{row.get('floating_cells', 0)} floating")
        rows.append(row)
        print(f"[seat_built] {name:32s} {cls:7s} cells {len(cells):5d}  exposed p5/p50/p95 {row.get('exposed_p5_p50_p95_m')}  "
              f"gap max {row.get('foot_gap_max_m')}  floating {row.get('floating_cells')}  buried {row.get('buried_cells', '-')}"
              f"  no ground {nog}")
    verdict = "FAIL" if fails else "PASS"
    for f in fails:
        print("[seat_built]   " + f)
    print(f"[seat_built] {verdict}: {len(rows)} furniture objects read against the built ground ({len(T):,} ground triangles)")
    if out:
        Path(out).write_text(json.dumps({"verdict": verdict, "fails": fails, "objects": rows}, indent=1) + "\n")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
