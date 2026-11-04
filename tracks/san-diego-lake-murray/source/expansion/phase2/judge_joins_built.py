"""Judge the north loop's five joins on the BUILT road (ledger 0054 Phase 2 step 1). A PC step: the gate OBJs exist only there.
Stdlib only; reads, never writes, the workshop.

L5: the artifact, never the data that placed it. For each join (J1..J5) and APPROACH_M of road either side, every STEP_M along
the lap and every LAT_STEP_M across each held layout's race LANE there (barrier_bands.north.json corridors.<id>.lane_by_vertex,
shrunk by EDGE_KEEP_M off each face; the full street inside the junction boxes), read the gate OBJ straight down:

  road      the top drivable surface is 1ROAD / 1KERB (drive_test DRIVABLE minus SOFT); none = a hole, SOFT on top = ground
            through the road (soft top)
  steps     along every lateral path, |dh| between consecutive samples at least MIN_ADVANCE_M apart along the travel > drive_test STEP_SEVERE_M = severe (fail),
            > STEP_BUMP_M = a bump (reported)
  kinks     the grade change per metre along the reference line > drive_test KINK_PCT (reported)
  clear     no non-drivable, non-paint triangle (walls, posts, signs, buildings) within drive_test OBST_CLEAR_M of a sample, from
            0.05 m over the deck to drive_test OBST_HEIGHT_M (fail)

drive_test's constants are READ from scripts/geometry/drive_test.py (never restated). PASS per join when holes, soft top,
severe steps and obstructions are all 0. The frame is checked first: data/gate_centerline.json against the repo's
data/centerline.local.json (engine frame, x = E, y = up, z = N), max plan offset FRAME_TOL_M, else exit 2.

    python tracks/san-diego-lake-murray/source/expansion/phase2/judge_joins_built.py \\
        --obj D:/k10-scratch/lm_v4/data/track.obj --gate-centerline D:/k10-scratch/lm_v4/data/gate_centerline.json \\
        --plan build/phase2/north-plan [--also D:/k10-scratch/lm_v4/data/track.race_cw.obj ...] [--json <out>]

--plan is plan_north.py's out dir (data/lap.north.json, data/barrier_bands.north.json). --also OBJs are read for
obstructions only and reported apart (the Lake Murray Speedways' furniture: the north layouts will not load it, but a
shared object in a join is worth knowing). Exit 0 all PASS, 1 any FAIL, 2 input error.
"""
from __future__ import annotations

import json
import math
import re
import sys
from array import array
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
ROOT = HERE.parents[4]
STEP_M = 0.5
LAT_STEP_M = 0.5
APPROACH_M = 10.0
MIN_ADVANCE_M = 0.25       # [invented] a lateral path inside a tight corner barely moves (or runs backwards past the
#                            corner's centre): its step is read only once it has advanced this far along the travel
EDGE_KEEP_M = 0.5          # [invented] a sample stays this far inside each lane face (the strip / closure stands on it)
FRAME_TOL_M = 0.05
ZONE_PAD_M = 30.0
CELL_M = 1.0
NAMES = {0: "J2", 1: "J3", 2: "J4", 3: "J5", 4: "J1"}


def drive_test_constants():
    src = (ROOT / "scripts" / "geometry" / "drive_test.py").read_text(encoding="utf-8")
    out = {}
    for k in ("STEP_BUMP_M", "STEP_SEVERE_M", "KINK_PCT", "OBST_CLEAR_M", "OBST_HEIGHT_M"):
        out[k] = float(re.search(rf"^{k} = ([0-9.]+)", src, re.M).group(1))
    for k in ("DRIVABLE", "SOFT", "PAINT"):
        out[k] = tuple(re.findall(r'"([A-Z0-9_]+)"', re.search(rf"^{k} = \(([^)]*)\)", src, re.M).group(1)))
    return out


def _args(argv):
    a = {"obj": None, "gate": None, "plan": ROOT / "build" / "phase2" / "north-plan", "also": [], "json": None}
    i = 0
    while i < len(argv):
        k = argv[i]
        if k in ("--obj", "--gate-centerline", "--plan", "--json"):
            a[{"--obj": "obj", "--gate-centerline": "gate", "--plan": "plan", "--json": "json"}[k]] = Path(argv[i + 1]); i += 2
        elif k == "--also":
            a["also"].append(Path(argv[i + 1])); i += 2
        else:
            raise SystemExit(f"unknown argument {k}")
    if not a["obj"] or not a["gate"]:
        print(__doc__); sys.exit(2)
    return a


def frame_check(gate_p):
    g = json.loads(gate_p.read_text(encoding="utf-8"))
    c = json.loads((PROJECT / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    gp, cp = g["points_xyz_m"], c["points_xyz_m"]
    if len(gp) != len(cp):
        return None, f"gate centreline has {len(gp)} points, the repo's {len(cp)}"
    worst = max(math.hypot(a[0] - b[0], a[2] - b[2]) for a, b in zip(gp, cp))
    return worst, None


def read_obj(path, boxes, cons):
    """triangles inside any box, by class: road / soft / obst; each (xs, ys, zs) of three vertices"""
    V = array("d")
    cls = None
    tris = {"road": [], "soft": [], "obst": []}

    def inbox(x, z):
        return any(b[0] <= x <= b[2] and b[1] <= z <= b[3] for b in boxes)

    def klass(name):
        u = name.upper()
        if u.startswith(cons["PAINT"]):
            return None
        if u.startswith(cons["SOFT"]):
            return "soft"
        if u.startswith(cons["DRIVABLE"]):
            return "road"
        if u.startswith(("GRASS_FAR", "TERRAIN", "SKY", "SHADOW")):
            return None
        return "obst"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            c0 = ln[:2]
            if c0 == "v ":
                _, x, y, z = ln.split()[:4]
                V.extend((float(x), float(y), float(z)))
            elif c0 == "o ":
                cls = klass(ln[2:].strip())
            elif c0 == "f " and cls is not None:
                ids = [int(t.split("/")[0]) - 1 for t in ln.split()[1:4]]
                pts = [(V[3 * i], V[3 * i + 1], V[3 * i + 2]) for i in ids]
                if any(inbox(p[0], p[2]) for p in pts) or inbox(sum(p[0] for p in pts) / 3, sum(p[2] for p in pts) / 3):
                    tris[cls].append(pts)
    return tris


class Grid:
    def __init__(self, tris):
        self.t = tris
        self.g = {}
        for i, t in enumerate(tris):
            xs, zs = [p[0] for p in t], [p[2] for p in t]
            for gx in range(int(math.floor(min(xs) / CELL_M)), int(math.floor(max(xs) / CELL_M)) + 1):
                for gz in range(int(math.floor(min(zs) / CELL_M)), int(math.floor(max(zs) / CELL_M)) + 1):
                    self.g.setdefault((gx, gz), []).append(i)

    def heights(self, x, z):
        out = []
        for i in self.g.get((int(math.floor(x / CELL_M)), int(math.floor(z / CELL_M))), ()):
            (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = self.t[i]
            d = (z2 - z3) * (x1 - x3) + (x3 - x2) * (z1 - z3)
            if abs(d) < 1e-12:
                continue
            a = ((z2 - z3) * (x - x3) + (x3 - x2) * (z - z3)) / d
            b = ((z3 - z1) * (x - x3) + (x1 - x3) * (z - z3)) / d
            c = 1 - a - b
            if a >= -1e-9 and b >= -1e-9 and c >= -1e-9:
                out.append(a * y1 + b * y2 + c * y3)
        return out

    def near(self, x, z, r):
        seen = set()
        for gx in range(int(math.floor((x - r) / CELL_M)), int(math.floor((x + r) / CELL_M)) + 1):
            for gz in range(int(math.floor((z - r) / CELL_M)), int(math.floor((z + r) / CELL_M)) + 1):
                for i in self.g.get((gx, gz), ()):
                    if i not in seen:
                        seen.add(i)
                        yield self.t[i]


def _dist_tri_plan(x, z, t):
    """plan distance from (x, z) to a triangle (0 inside)"""
    (x1, _, z1), (x2, _, z2), (x3, _, z3) = t
    d = (z2 - z3) * (x1 - x3) + (x3 - x2) * (z1 - z3)
    if abs(d) > 1e-12:
        a = ((z2 - z3) * (x - x3) + (x3 - x2) * (z - z3)) / d
        b = ((z3 - z1) * (x - x3) + (x1 - x3) * (z - z3)) / d
        if a >= 0 and b >= 0 and a + b <= 1:
            return 0.0
    best = 1e9
    for (ax, _, az), (bx, _, bz) in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        s = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
        best = min(best, math.hypot(x - ax - dx * s, z - az - dz * s))
    return best


def main(argv=None):
    a = _args(sys.argv[1:] if argv is None else argv)
    cons = drive_test_constants()
    worst, err = frame_check(a["gate"])
    if err or worst > FRAME_TOL_M:
        print(f"FRAME: {err or f'gate centreline {worst:.3f} m off the repo centreline (> {FRAME_TOL_M})'} — wrong workshop or frame"); return 2
    lap = json.loads((a["plan"] / "data" / "lap.north.json").read_text(encoding="utf-8"))
    bands = json.loads((a["plan"] / "data" / "barrier_bands.north.json").read_text(encoding="utf-8"))
    P = lap["points_xyz_m"]
    m = len(P) - 1
    st = [0.0]
    for k in range(1, m + 1):
        st.append(st[-1] + math.hypot(P[k][0] - P[k - 1][0], P[k][2] - P[k - 1][2]))
    zones = []
    for j, _jn in enumerate(lap["joins"]):
        ks = [k for k in range(m) if lap["source_by_vertex"][k] == ["join", j]]
        k0, k1 = ks[0] - 1, (ks[-1] + 1) % m
        s0 = st[k0] - APPROACH_M
        s1 = (st[k1] if k1 > k0 else st[k1] + st[-1]) + APPROACH_M
        zones.append((NAMES.get(j, str(j)), s0, s1))
    boxes = []
    for _n, s0, s1 in zones:
        ks = [k for k in range(m) if s0 <= st[k] <= s1 or s0 <= st[k] + st[-1] <= s1]
        xs, zs = [P[k][0] for k in ks], [P[k][2] for k in ks]
        boxes.append((min(xs) - ZONE_PAD_M, min(zs) - ZONE_PAD_M, max(xs) + ZONE_PAD_M, max(zs) + ZONE_PAD_M))
    tris = read_obj(a["obj"], boxes, cons)
    road, soft, obst = Grid(tris["road"]), Grid(tris["soft"]), Grid(tris["obst"])
    also = [(p, Grid(read_obj(p, boxes, cons)["obst"])) for p in a["also"]]
    rows, bad = [], 0
    for name, s0, s1 in zones:
        row = {"join": name, "s_from": round(s0 % st[-1], 1), "s_to": round(s1 % st[-1], 1), "layouts": {}}
        for lid, cor in sorted(bands["corridors"].items()):
            lanes = cor["lane_by_vertex"]
            holes, softs, severe, bumps, obsts, also_hits = [], [], [], [], [], []
            prev = {}
            ref_h = []
            s = s0
            while s <= s1 + 1e-9:
                ss = s % st[-1]
                k = next(i for i in range(m) if st[i + 1] >= ss)
                t = (ss - st[k]) / max(1e-9, st[k + 1] - st[k])
                x = P[k][0] + (P[k + 1][0] - P[k][0]) * t
                y0 = P[k][1] + (P[k + 1][1] - P[k][1]) * t
                z = P[k][2] + (P[k + 1][2] - P[k][2]) * t
                tx, tz = P[k + 1][0] - P[k][0], P[k + 1][2] - P[k][2]
                L = math.hypot(tx, tz) or 1.0
                nx, nz = -tz / L, tx / L
                lo, hi = lanes[k]
                lat = lo + EDGE_KEEP_M
                while lat <= hi - EDGE_KEEP_M + 1e-9:
                    px, pz = x + nx * lat, z + nz * lat
                    hr = [h for h in road.heights(px, pz) if abs(h - y0) < 3.0]
                    hs = [h for h in soft.heights(px, pz) if abs(h - y0) < 3.0]
                    key = round(lat, 2)
                    if not hr:
                        holes.append([round(ss, 1), key])
                        prev.pop(key, None)
                    else:
                        top = max(hr)
                        if hs and max(hs) > top + 0.01:
                            softs.append([round(ss, 1), key, round(max(hs) - top, 3)])
                        pv = prev.get(key)
                        moved = pv is not None and ((px - pv[1]) * tx + (pz - pv[2]) * tz) / L >= MIN_ADVANCE_M
                        if moved:
                            dh = abs(top - pv[0])
                            if dh > cons["STEP_SEVERE_M"]:
                                severe.append([round(ss, 1), key, round(dh, 3)])
                            elif dh > cons["STEP_BUMP_M"]:
                                bumps.append([round(ss, 1), key, round(dh, 3)])
                        if pv is None or moved:
                            prev[key] = (top, px, pz)
                        lo_y, hi_y = top + 0.05, top + cons["OBST_HEIGHT_M"]
                        for g, sink in [(obst, obsts)] + [(gg, also_hits) for _p, gg in also]:
                            for tri in g.near(px, pz, cons["OBST_CLEAR_M"] + 0.5):
                                ys = [q[1] for q in tri]
                                if max(ys) < lo_y or min(ys) > hi_y:
                                    continue
                                if _dist_tri_plan(px, pz, tri) <= cons["OBST_CLEAR_M"]:
                                    sink.append([round(ss, 1), key])
                                    break
                    lat += LAT_STEP_M
                hr0 = [h for h in road.heights(x, z) if abs(h - y0) < 3.0]
                ref_h.append(max(hr0) if hr0 else None)
                s += STEP_M
            kinks = 0
            per_m = int(round(1.0 / STEP_M))
            for i in range(2 * per_m, len(ref_h)):
                h0, h1, h2 = ref_h[i - 2 * per_m], ref_h[i - per_m], ref_h[i]
                if None not in (h0, h1, h2) and abs((h2 - h1) - (h1 - h0)) * 100.0 > cons["KINK_PCT"]:
                    kinks += 1
            fail = bool(holes or softs or severe or obsts)
            bad += fail
            row["layouts"][lid] = {"fail": fail, "holes": len(holes), "soft_top": len(softs), "severe_steps": len(severe),
                                   "bumps": len(bumps), "kinks": kinks, "obstructed": len(obsts),
                                   "also_obstructed": len(also_hits), "worst": {"holes": holes[:8], "soft": softs[:8],
                                   "severe": sorted(severe, key=lambda r: -r[2])[:8], "obst": obsts[:8]}}
            v = row["layouts"][lid]
            print(f"{name} {lid:9s} {'FAIL' if fail else 'PASS'}  holes {v['holes']} soft-top {v['soft_top']} severe {v['severe_steps']} "
                  f"obstructed {v['obstructed']} | bumps {v['bumps']} kinks {v['kinks']} also-obstructed {v['also_obstructed']}")
        rows.append(row)
    rep = {"_doc": "judge_joins_built.py (ledger 0054 Phase 2 step 1)", "obj": str(a["obj"]), "frame_offset_m": round(worst, 4),
           "constants": {k: v for k, v in cons.items()}, "rows": rows, "fail": bool(bad)}
    out = a["json"] or (a["plan"] / "joins_built.json")
    Path(out).write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print("wrote", out)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
