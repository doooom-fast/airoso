"""Ledger 0054 P2, EXPANSION-PLAN V7 "facets 20-60 m from a new road: longest edge p90 <= 7 m" (0046 criterion 5), on a
rehearsal's planned lattice (data/terrain.tiers.json.gz: the frame, every vertex, every triangle incl. the break-line
cells): each triangle whose centroid lies 20-60 m from the planned north pavement (data/expansion.north.json: the
pieces' wider curb, the pads, the stubs) - and, for the record, the same band beside the loop's own roads.

    python facets_check.py <airoso> <rehearsal project> <out.json>
"""
import gzip
import json
import math
import sys
from pathlib import Path

AIR, PROJ, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(AIR))
from scripts.elevation import terrain_sample as ts  # noqa: E402
from scripts.geometry import terrain_tiers as tt  # noqa: E402

T = json.loads(gzip.decompress((PROJ / "data" / "terrain.tiers.json.gz").read_bytes()))
x0, z0, ux, uz = T["frame"]
xs = [x0 + i * ux for i in T["I"]]
zs = [z0 + j * uz for j in T["J"]]
bk = T.get("break")
if bk:
    q = float(bk["fine"])
    xs += [x0 + i / q * ux for i in bk["I5"]]
    zs += [z0 + j / q * uz for j in bk["J5"]]
tris = T["tris"]
cfg = json.loads((PROJ / "track.config.json").read_text(encoding="utf-8"))
spec = tt.TierSpec(cfg["terrain"], json.loads((PROJ / "data" / "centerline.local.json").read_text())["origin"])
plan, _f = ts.planned_inputs(PROJ, spec)
roads, _o, _f2 = ts.road_inputs(PROJ)


class Pave:
    def __init__(self, lines, closed_first, cell=20.0):
        self.cell, self.b = cell, {}
        for x, z, hw in tt.densify(lines, 2.0, closed_first):
            self.b.setdefault((math.floor(x / cell), math.floor(z / cell)), []).append((x, z, hw))

    def dist(self, x, z, reach=80.0):
        c, n = self.cell, int(math.ceil(reach / self.cell))
        i0, j0 = math.floor(x / c), math.floor(z / c)
        best = reach
        for i in range(i0 - n, i0 + n + 1):
            for j in range(j0 - n, j0 + n + 1):
                for px, pz, hw in self.b.get((i, j), ()):
                    best = min(best, math.hypot(px - x, pz - z) - hw)
        return best


pn, pr = Pave(plan, False), Pave(roads, True)
L_plan, L_road = [], []
for k in range(len(tris) // 3):
    a, b, c = tris[3 * k:3 * k + 3]
    cx, cz = (xs[a] + xs[b] + xs[c]) / 3, (zs[a] + zs[b] + zs[c]) / 3
    longest = max(math.hypot(xs[p] - xs[q_], zs[p] - zs[q_]) for p, q_ in ((a, b), (b, c), (c, a)))
    dp = pn.dist(cx, cz)
    if 20.0 <= dp <= 60.0 and pr.dist(cx, cz) > 60.0:
        L_plan.append(longest)
    dr = pr.dist(cx, cz)
    if 20.0 <= dr <= 60.0:
        L_road.append(longest)


def stats(L):
    L = sorted(L)
    return {"triangles": len(L), "p50": round(L[len(L) // 2], 2), "p90": round(L[int(0.9 * len(L))], 2),
            "max": round(L[-1], 2)} if L else {"triangles": 0}


rep = {"planned_pavement_20_60m": stats(L_plan), "loop_roads_20_60m": stats(L_road), "threshold_p90_m": 7.0}
rep["pass"] = rep["planned_pavement_20_60m"].get("p90", 99) <= 7.0
OUT.write_text(json.dumps(rep, indent=1), encoding="utf-8")
print("[facets]", json.dumps(rep))
