"""Judge the north loop's five joins on v4's COMMITTED records (Mac side; ledger 0054 Phase 2 step 1). Stdlib only.

The joins (J1 14.6 m, J2 28.0, J3 46.0, J4 42.0, J5 11.6 m chord) are accounting lines of the lap, not corners anyone
built. This asks, from the records alone, how much of an 8 m driving band round each join (the reference line +-4 m, every
0.5 m, plus 10 m of each approach) lies over pavement the records say exists: the road ribbons (data/centerline.local.json,
data/connectors.local.json, each at its own half width), the junction pads as built (data/pads.built.json outline_xz) and
the mouth aprons (data/aprons.json outline_xz). It is NOT the built-road judgement (judge_joins_built.py, on the PC's gate
OBJs, is): a ribbon at half width ignores curb returns, flares and the welds, so "uncovered" here means "look there".

    .venv/bin/python tracks/san-diego-lake-murray/source/expansion/phase2/judge_joins_records.py [<lap.north.json>] [<out json>]

<lap.north.json> defaults to <repo>/build/phase2/north-plan/data/lap.north.json (plan_north.py writes it).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
ROOT = HERE.parents[4]
BAND_M = 4.0
LAT_STEP_M = 1.0
STEP_M = 0.5
APPROACH_M = 10.0
NAMES = {0: "J2", 1: "J3", 2: "J4", 3: "J5", 4: "J1"}


def _pip(poly, x, z):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
            inside = not inside
    return inside


def _seg(px, pz, a, b):
    dx, dz = b[0] - a[0], b[2] - a[2]
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - a[0]) * dx + (pz - a[2]) * dz) / L2))
    return math.hypot(px - (a[0] + dx * t), pz - (a[2] + dz * t)), t


class Pavement:
    def __init__(self, data: Path):
        self.ribbons = []
        cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
        self.ribbons.append(("MAINLINE", cl["points_xyz_m"], cl["widths_m"]))
        for c in json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]:
            self.ribbons.append((c["name"], c["points_xyz_m"], c.get("widths_m") or [10.0] * len(c["points_xyz_m"])))
        self.polys = []
        for p in json.loads((data / "pads.built.json").read_text(encoding="utf-8")).get("pads") or []:
            self.polys.append((f"pad {p['id']}", [tuple(q) for q in p["outline_xz"]]))
        ap = data / "aprons.json"
        if ap.exists():
            for a in json.loads(ap.read_text(encoding="utf-8")).get("aprons") or []:
                self.polys.append((f"apron {a['id']}", [tuple(q) for q in a["outline_xz"]]))
        self.cell = 25.0
        self.grid = {}
        for ri, (_n, pts, _w) in enumerate(self.ribbons):
            for k in range(len(pts) - 1):
                a, b = pts[k], pts[k + 1]
                for gx in range(int(math.floor(min(a[0], b[0]) / self.cell)) - 1, int(math.floor(max(a[0], b[0]) / self.cell)) + 2):
                    for gz in range(int(math.floor(min(a[2], b[2]) / self.cell)) - 1, int(math.floor(max(a[2], b[2]) / self.cell)) + 2):
                        self.grid.setdefault((gx, gz), []).append((ri, k))

    def under(self, x, z):
        """the first pavement record covering (x, z): (kind, name) or None"""
        for name, poly in self.polys:
            if _pip(poly, x, z):
                return ("poly", name)
        for ri, k in self.grid.get((int(math.floor(x / self.cell)), int(math.floor(z / self.cell))), ()):
            name, pts, w = self.ribbons[ri]
            d, t = _seg(x, z, pts[k], pts[k + 1])
            if d <= (w[k] + (w[k + 1] - w[k]) * t) / 2.0:
                return ("ribbon", name)
        return None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    lap_p = Path(argv[0]) if argv else ROOT / "build" / "phase2" / "north-plan" / "data" / "lap.north.json"
    out_p = Path(argv[1]) if len(argv) > 1 else HERE / "joins_records.json"
    lap = json.loads(lap_p.read_text(encoding="utf-8"))
    pav = Pavement(PROJECT / "data")
    P = lap["points_xyz_m"]
    m = len(P) - 1
    st = [0.0]
    for k in range(1, m + 1):
        st.append(st[-1] + math.hypot(P[k][0] - P[k - 1][0], P[k][2] - P[k - 1][2]))
    rows = []
    for j, jn in enumerate(lap["joins"]):
        ks = [k for k in range(m) if lap["source_by_vertex"][k] == ["join", j]]
        a, b = ks[0] - 1, (ks[-1] + 1) % m
        s0, s1 = st[a] - APPROACH_M, st[a] + ((st[b] if b > a else st[b] + st[-1]) - st[a]) + APPROACH_M
        tot = unc = 0
        holes = []
        s = s0
        while s <= s1:
            ss = s % st[-1]
            k = max(0, min(m - 1, next(i for i in range(m) if st[i + 1] >= ss)))
            t = (ss - st[k]) / max(1e-9, st[k + 1] - st[k])
            x = P[k][0] + (P[k + 1][0] - P[k][0]) * t
            z = P[k][2] + (P[k + 1][2] - P[k][2]) * t
            tx, tz = P[k + 1][0] - P[k][0], P[k + 1][2] - P[k][2]
            L = math.hypot(tx, tz) or 1.0
            nx, nz = -tz / L, tx / L
            lat = -BAND_M
            while lat <= BAND_M + 1e-9:
                tot += 1
                if pav.under(x + nx * lat, z + nz * lat) is None:
                    unc += 1
                    holes.append([round(ss, 1), lat, round(x + nx * lat, 2), round(z + nz * lat, 2)])
                lat += LAT_STEP_M
            s += STEP_M
        lefts = [h for h in holes if h[1] > 0]
        rights = [h for h in holes if h[1] < 0]
        rows.append({"join": NAMES.get(j, str(j)), "from": jn["from"], "to": jn["to"], "chord_m": jn.get("chord_m", jn["length_m"]),
                     "length_m": jn["length_m"], "declared": jn.get("declared"), "samples": tot, "uncovered": unc,
                     "uncovered_share": round(unc / tot, 4), "uncovered_left": len(lefts), "uncovered_right": len(rights),
                     "worst": holes[:: max(1, len(holes) // 12)][:12]})
    json.dump({"_doc": __doc__.split("\n")[0], "band_m": BAND_M, "rows": rows}, open(out_p, "w"), indent=1)
    for r in rows:
        print(f"{r['join']}: chord {r['chord_m']} m, line {r['length_m']} m ({r['declared'] or 'straight'}): "
              f"{r['uncovered']} of {r['samples']} band samples off the recorded pavement "
              f"(left {r['uncovered_left']}, right {r['uncovered_right']})")
    print("wrote", out_p)


if __name__ == "__main__":
    main()
