"""Sightlines over the BUILT terrain — ledger 0046 criterion 2 (and 3's south profile): is Cowles there from Navajo?

READ-ONLY on the gate OBJ (data/track.obj, kn5_to_gate_obj of the shipped road kn5 — L5: the artifact, never
the heightfield that placed it). From a station, the eye EYE_M above the road surface there, it marches the
built terrain (every 1GRASS* and GRASS_FAR* triangle: the far ring is what Kevin sees) toward a target at STEP_M
steps and reports the elevation angle of the ground at every step.

    python tools/sightline_check.py <project> [--obj <gate obj>] [--json <out>]
        default: the ledger-0046 set — Navajo crest (62, 1713), v2240, v1640 -> the Cowles summit (1380, 2700)
    python tools/sightline_check.py <project> --from 62,1713 --to 1380,2700 [--min-deg 9.0]
    python tools/sightline_check.py <project> --from 62,1713 --bearing 192 --range 5000
    python tools/sightline_check.py <project> --from-vertex 2240 --to 1380,2700

A TARGET ray is aimed at the summit's TOP: the highest built terrain vertex within SUMMIT_R_M of the nominal
coordinate (criterion 1's 60 m — the nominal (1380, 2700) is a 20 m-lattice 3DEP probe, ~14 m off the real top,
which fresh 3DEP puts at (1390, 2710)). The summit as seen is the cone's highest elevation angle along the ray (the
top, or its shoulder where the ground near the top is flatter than the sight line). It passes when that is >= --min-deg
AND above every profile step more than SUMMIT_R_M short of the top — nothing in front of the summit cone stands
higher. Steps inside the cone are the summit's own shoulder (the ledger's Evidence: the 3DEP profile's highest intervening
sample, +9.37 deg at 1,638 m, "is the summit's own shoulder"): near the top the ground is flatter than the sight
line, so a point a few metres short of it always reads a hair higher in angle, in the world as in the build. The
nominal point's own angle and the shoulder's maximum are reported beside the verdict, never hidden. A BEARING ray reports the
profile and the first step with no built surface under it (criterion 3: "a built surface to >= 5 km").
Frame: local, x = E, y = up (metres above the origin's elev_m), z = N. Exit 1 when any target ray fails.
"""
from __future__ import annotations

import json
import math
import sys
from array import array
from pathlib import Path

EYE_M = 1.2
STEP_M = 10.0
SUMMIT_R_M = 60.0         # the summit cone: criterion 1's radius about the nominal coordinate
CORRIDOR_M = 60.0          # triangles kept for the march: centroid within this of the ray
TERRAIN = ("1GRASS", "GRASS_FAR")
COWLES = (1380.0, 2700.0)  # 3DEP summit 483.2 m, 32.81277 N 117.03192 W (ledger 0046 Evidence)
# criterion 2 (ledger 0046). Real 3DEP elevation angles: crest 9.35 deg, v2240 8.5, v1640 5.5 (ledger Evidence);
# the crest's 9.0 is the ledger's own threshold; the others take the same 0.35-0.4 deg allowance (invented,
# fleet/GATES-CHANGELOG.md 2026-10-11 — measured, not gated).
DEFAULT_SET = [
    {"name": "navajo_crest", "from": (62.0, 1713.0), "to": COWLES, "min_deg": 9.0},
    {"name": "v2240_0033_navajo_jackson", "from_vertex": 2240, "to": COWLES, "min_deg": 8.1},
    # criterion 2 re-worded for v1640 (ledger 0046, 2026-10-13): fresh 3DEP itself hides Cowles from here — a hill 350 m
    # out stands at 7.23 deg in front of the 5.49 deg summit — so the build must agree with the world: the summit cone
    # at >= min_deg AND something nearer standing at least as high ("hidden": the world's verdict, measured)
    {"name": "v1640_0037_navajo_north", "from_vertex": 1640, "to": COWLES, "min_deg": 5.1, "hidden": True},
]


def _seg_dist(px, pz, ax, az, bx, bz):
    dx, dz = bx - ax, bz - az
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
    return math.hypot(px - ax - t * dx, pz - az - t * dz)


class Surface:
    """triangles of the named groups near the given segments, bucketed for (x, z) -> highest y queries"""

    def __init__(self, obj: Path, segs, prefixes, cell=25.0, reach=CORRIDOR_M):
        self.V = array("d")
        self.cell = cell
        self.b: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
        keep, n = False, 0
        with open(obj, encoding="utf-8", errors="replace") as f:
            for ln in f:
                c = ln[:2]
                if c == "v ":
                    _, x, y, z = ln.split()[:4]
                    self.V.extend((float(x), float(y), float(z)))
                elif c == "o " or ln.startswith("g "):
                    keep = ln[2:].strip().upper().startswith(prefixes)
                elif c == "f " and keep:
                    ids = [int(t.split("/")[0]) - 1 for t in ln.split()[1:]]
                    for k in range(1, len(ids) - 1):
                        tri = (ids[0], ids[k], ids[k + 1])
                        xs = [self.V[3 * i] for i in tri]
                        zs = [self.V[3 * i + 2] for i in tri]
                        cx, cz = sum(xs) / 3.0, sum(zs) / 3.0
                        if not any(_seg_dist(cx, cz, *s) <= reach for s in segs):
                            continue
                        n += 1
                        for i in range(int(min(xs) // cell), int(max(xs) // cell) + 1):
                            for j in range(int(min(zs) // cell), int(max(zs) // cell) + 1):
                                self.b.setdefault((i, j), []).append(tri)
        self.n = n

    def top_near(self, x, z, r):
        """(x, z, y) of the highest vertex of these triangles within ``r`` (plan) of (x, z), or None"""
        best = None
        V = self.V
        seen = set()
        for i in range(int((x - r) // self.cell), int((x + r) // self.cell) + 1):
            for j in range(int((z - r) // self.cell), int((z + r) // self.cell) + 1):
                for tri in self.b.get((i, j), ()):
                    for v in tri:
                        if v in seen:
                            continue
                        seen.add(v)
                        vx, vy, vz = V[3 * v], V[3 * v + 1], V[3 * v + 2]
                        if math.hypot(vx - x, vz - z) <= r and (best is None or vy > best[2]):
                            best = (vx, vz, vy)
        return best

    def height(self, x, z):
        best = None
        V = self.V
        for a, b, c in self.b.get((int(x // self.cell), int(z // self.cell)), ()):
            ax, ay, az = V[3 * a], V[3 * a + 1], V[3 * a + 2]
            bx, by, bz = V[3 * b], V[3 * b + 1], V[3 * b + 2]
            cx, cy, cz = V[3 * c], V[3 * c + 1], V[3 * c + 2]
            det = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
            if abs(det) < 1e-12:
                continue
            l1 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / det
            l2 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / det
            l3 = 1.0 - l1 - l2
            if min(l1, l2, l3) < -1e-9:
                continue
            y = l1 * ay + l2 * by + l3 * cy
            if best is None or y > best:
                best = y
        return best


def march(terrain: Surface, road: Surface, start, end, step=STEP_M, eye=EYE_M):
    """profile [(distance, ground_y | None, angle_deg | None)] from start toward end, every ``step`` m and at the end"""
    sx, sz = start
    ex, ez = end
    L = math.hypot(ex - sx, ez - sz)
    ux, uz = (ex - sx) / L, (ez - sz) / L
    deck = road.height(sx, sz)
    base = deck if deck is not None else terrain.height(sx, sz)
    if base is None:
        raise SystemExit(f"[sightline] no road or terrain under the station {start}")
    eye_y = base + eye
    prof = []
    k = 1
    while k * step <= L + 1e-6:
        d = k * step
        y = terrain.height(sx + ux * d, sz + uz * d)
        prof.append((round(d, 1), None if y is None else round(y, 3),
                     None if y is None else round(math.degrees(math.atan2(y - eye_y, d)), 3)))
        k += 1
    if not prof or abs(prof[-1][0] - L) > 1e-6:                  # the end itself (the summit top) is always a step
        y = terrain.height(ex, ez)
        prof.append((L, None if y is None else round(y, 3),
                     None if y is None else round(math.degrees(math.atan2(y - eye_y, L)), 3)))
    return eye_y, prof


def judge_target(prof, dist, min_deg, cone=SUMMIT_R_M, hidden=False):
    """``prof`` marches to the summit top at ``dist`` (its last step is the top itself). The summit as seen is the summit
    cone's highest elevation angle (``target_deg``: the top, or its own shoulder where the ground near the top is
    flatter than the sight line); it must reach ``min_deg`` and stand above every step outside the cone. The top's own
    angle and the shoulder's are reported beside it. ``hidden``: a station from which the WORLD hides the summit behind a
    nearer rise (fresh 3DEP, recorded in the ledger) passes when the build agrees — the summit cone reaches ``min_deg``
    and a step outside the cone stands at least as high."""
    top = [a for d, _y, a in prof if a is not None and abs(d - dist) < 1e-6]
    before = [a for d, _y, a in prof if a is not None and d < dist - cone]
    shoulder = [a for d, _y, a in prof if a is not None and dist - cone <= d < dist - 1e-6]
    at_top = top[0] if top else None
    in_cone = top + shoulder
    at = max(in_cone) if in_cone else None
    mid = max(before) if before else None
    if hidden:
        ok = at_top is not None and at >= min_deg and mid is not None and mid >= at
    else:
        ok = at_top is not None and at >= min_deg and (mid is None or at > mid)
    return {"target_deg": at, "top_deg": at_top, "max_shoulder_deg": max(shoulder) if shoulder else None,
            "max_intermediate_deg": mid, "min_deg": min_deg, **({"expect": "hidden"} if hidden else {}), "pass": ok}


def run(project, rays, obj=None, out=None):
    proj = Path(project)
    obj = Path(obj) if obj else proj / "data" / "track.obj"
    local = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    pts = local["points_xyz_m"]
    elev0 = float(local["origin"]["elev_m"])
    for r in rays:
        if "from_vertex" in r:
            p = pts[int(r["from_vertex"])]
            r["from"] = (p[0], p[2])
        if "bearing" in r:
            b = math.radians(float(r["bearing"]))
            r["to"] = (r["from"][0] + math.sin(b) * r["range"], r["from"][1] + math.cos(b) * r["range"])
    segs = [(r["from"][0], r["from"][1], r["to"][0], r["to"][1]) for r in rays]
    terrain = Surface(obj, segs, TERRAIN)
    road = Surface(obj, [(s[0], s[1], s[0], s[1]) for s in segs], ("1ROAD",), reach=12.0)
    report, bad = [], 0
    for r in rays:
        nominal = None
        if "bearing" not in r:
            top = terrain.top_near(r["to"][0], r["to"][1], SUMMIT_R_M)
            if top is not None:
                nominal = r["to"]
                r = dict(r, to=(top[0], top[1]))
        eye_y, prof = march(terrain, road, r["from"], r["to"])
        row = {"name": r.get("name"), "from": [round(c, 1) for c in r["from"]], "to": [round(c, 1) for c in r["to"]],
               "eye_abs_m": round(eye_y + elev0, 2), "steps": len(prof),
               "first_gap_m": next((d for d, y, _a in prof if y is None), None)}
        angs = [(a, d) for d, _y, a in prof if a is not None]
        if angs:
            row["max_deg"], row["max_at_m"] = max(angs)
        ys = [(y, d) for d, y, _a in prof if y is not None]
        if ys:
            row["max_ground_abs_m"] = round(max(ys)[0] + elev0, 2)
        if "bearing" in r:
            row["bearing_deg"] = r["bearing"]
            row["built_to_m"] = max((d for d, y, _a in prof if y is not None), default=0.0)
        else:
            dist = math.hypot(r["to"][0] - r["from"][0], r["to"][1] - r["from"][1])
            row["target_dist_m"] = round(dist, 1)
            row.update(judge_target(prof, dist, float(r.get("min_deg", 0.0)), hidden=bool(r.get("hidden"))))
            if nominal is not None:
                row["nominal"] = [round(c, 1) for c in nominal]
                row["top_abs_m"] = round(prof[-1][1] + elev0, 2) if prof[-1][1] is not None else None
                ny = terrain.height(*nominal)
                nd = math.hypot(nominal[0] - r["from"][0], nominal[1] - r["from"][1])
                row["nominal_deg"] = None if ny is None else round(math.degrees(math.atan2(ny - eye_y, nd)), 3)
            bad += 0 if row["pass"] else 1
        row["profile_abs"] = [(d, None if y is None else round(y + elev0, 2), a) for d, y, a in prof]
        report.append(row)
        brief = {k: v for k, v in row.items() if k != "profile_abs"}
        print(f"[sightline] {json.dumps(brief)}")
    if out:
        Path(out).write_text(json.dumps({"obj": str(obj), "eye_m": EYE_M, "step_m": STEP_M, "elev0": elev0,
                                         "rays": report}, indent=1), encoding="utf-8")
    return report, bad


def _xy(s):
    a, b = s.split(",")
    return float(a), float(b)


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or a[0].startswith("--"):
        raise SystemExit(__doc__)
    proj = a.pop(0)

    def opt(name, default=None):
        if name in a:
            i = a.index(name)
            return a[i + 1]
        return default
    if opt("--from") or opt("--from-vertex"):
        r = {"name": "custom", "min_deg": float(opt("--min-deg", "0"))}
        if opt("--from"):
            r["from"] = _xy(opt("--from"))
        else:
            r["from_vertex"] = int(opt("--from-vertex"))
        if opt("--bearing"):
            r["bearing"], r["range"] = float(opt("--bearing")), float(opt("--range", "5000"))
        else:
            r["to"] = _xy(opt("--to", "%f,%f" % COWLES))
        rays = [r]
    else:
        rays = [dict(r) for r in DEFAULT_SET]
    _rep, bad = run(proj, rays, obj=opt("--obj"), out=opt("--json"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
