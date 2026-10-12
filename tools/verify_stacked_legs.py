"""Stacked-leg check (L4): on the BUILT track, nothing between two stacked legs is seated to the wrong leg.

Lookout Lariat V3-PLAN P5 (ledger 0048). The Lariat's climb stacks hairpin legs 20-40 m apart in plan and
6.5-14.7 m apart in height; the July build pulled ground, kerbs and furniture between them to whichever road
was nearest in 3D or highest in a window, so the lower leg's verge stood on the upper leg's fill (L4). This
gate reads the built gate OBJ (L5) and asks, at every stacked pair, whether each ground / edge / sign / closure
vertex belongs to the road it stands beside.

PAIRS. The route (drive_test's line: gate_centerline > finished_centerline > centerline.local.json) is walked
at 1 m. Two lap points form a pair when they are < PAIR_PLAN_M apart in plan [invented] and > PAIR_ALONG_M apart
along the lap [invented] (cyclic on a closed lap). Reported: the pair count, the plan distance of the nearest
pair, and the vertical gap between the two legs' BUILT road (the highest pavement within ROAD_WINDOW_M of the
line's height, drive_test's deck window) — min / median / max over the pairs.

THE TEST. A vertex is "at a pair" when its own leg point (the lap point nearest it in plan, within PAIR_PLAN_M:
the station it is seated to) has a partner, and the nearest lap point to the vertex that is > PAIR_ALONG_M
along the lap from its own point lies within PAIR_PLAN_M of the vertex and of its own point (the other leg).
It FAILS when it sits closer in height to the other leg's built road than to its own:
``|y - road(other)| < |y - road(own)|``. Failures allowed: 0 [invented]. A stacked lap point with no built road
under it cannot be judged, and fails the gate (it is never a skip).

Classes (group-name prefixes, case-insensitive; a track can override them in track.config.json
``gates.stacked_legs.classes``): ground (1GRASS, GRASS, GEN_terrain, TERRAIN, 1DIRT, 1SAND, 1GRAVEL,
AUTH_cut / AUTH_fill / AUTH_terrain), edge (1WALL, 1KERB, 1RUNOFF, GEN_verge, AUTH_wall / AUTH_edge / AUTH_stone /
AUTH_rail / AUTH_guardrail; 1RUNOFF since 2026-10-12: GEN_verge is a Blender collection name that never reaches a
built OBJ, so the built D4 verge, 1RUNOFF_verge_*, went untested — L4's July failure was exactly a lower leg's
verge on the upper leg's fill), sign (SIGN, AUTH_sign), closure (CLOSURE, AUTH_closure, 1WALL_closure). Closure is
matched first (a 1WALL_closure is a closure). The road itself (1ROAD) is the reference, never tested.

CROSSINGS. Where the lap crosses over itself (a bridge: the two legs' segments intersect in plan) the legs are
not stacked but crossed, and "nearest in plan" names neither road. Vertices whose own point and other-leg point
are both within CROSSING_ZONE_M along the lap of a crossing [invented] are not tested; they are counted and
listed (`crossing_skipped`) and every crossing is reported with its two stations. A lap that never crosses itself
skips nothing.

    python tools/verify_stacked_legs.py <project> [--obj data/track.obj] [--out data/stacked_legs.json]
    python tools/verify_stacked_legs.py <project> --line-only     # pairs + gaps on the line's own heights

Exit 0 pass, 1 fail, 2 input error. ``--line-only`` measures (exit 0, never a pass: the gate needs a build).
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import gate_route  # noqa: E402
from scripts.geometry.drive_test import TriField  # noqa: E402

PAIR_PLAN_M = 40.0        # [invented] (V3-PLAN P5, 0048)
PAIR_ALONG_M = 150.0      # [invented] (V3-PLAN P5, 0048)
MAX_FAILURES = 0          # [invented] (V3-PLAN P5, 0048)
CROSSING_ZONE_M = 40.0    # [invented] 2026-10-12: a crossing's own footprint, along the lap on each leg
ROAD_WINDOW_M = 2.5       # drive_test's deck window
STEP_M = 1.0
CELL_M = 10.0
WORST_N = 25
DEFAULT_CLASSES = {
    "closure": ["1WALL_CLOSURE", "CLOSURE", "AUTH_CLOSURE"],
    "ground": ["1GRASS", "GRASS", "GEN_TERRAIN", "TERRAIN", "1DIRT", "1SAND", "1GRAVEL",
               "AUTH_CUT", "AUTH_FILL", "AUTH_TERRAIN"],
    "edge": ["1WALL", "1KERB", "1RUNOFF", "GEN_VERGE", "AUTH_WALL", "AUTH_EDGE", "AUTH_STONE", "AUTH_RAIL",
             "AUTH_GUARDRAIL"],
    "sign": ["SIGN", "AUTH_SIGN"],
}
CLASS_ORDER = ("closure", "ground", "edge", "sign")
THRESHOLDS = {"pair_plan_m": PAIR_PLAN_M, "pair_along_m": PAIR_ALONG_M, "max_failures": MAX_FAILURES,
              "crossing_zone_m": CROSSING_ZONE_M, "road_window_m": ROAD_WINDOW_M,
              "_tags": "all [invented] (V3-PLAN P5, ledger 0048; crossing zone 2026-10-12) — fleet/GATES-CHANGELOG.md"}


class InputError(Exception):
    pass


def classify(name: str, classes: dict) -> str | None:
    up = name.upper()
    for c in CLASS_ORDER:
        if any(up.startswith(p.upper()) for p in classes.get(c, ())):
            return c
    return None


class Lap:
    """The route at 1 m with a plan hash: nearest point, along-lap distance (cyclic when closed)."""

    def __init__(self, pts, widths):
        self.closed = gate_route.is_closed(pts)
        self.p, self.w, self.s = gate_route.resample(pts, widths, STEP_M)
        if self.closed and len(self.p) > 1:      # the closing duplicate of v0 is v0
            self.p, self.w, self.s = self.p[:-1], self.w[:-1], self.s[:-1]
        self.lap = gate_route.stations(pts)[-1]
        self.cells = defaultdict(list)
        for i, (x, _y, z) in enumerate(self.p):
            self.cells[(int(math.floor(x / CELL_M)), int(math.floor(z / CELL_M)))].append(i)
        self.road = [q[1] for q in self.p]       # replaced by the built road's height in build mode

    def along(self, i: int, j: int) -> float:
        d = abs(self.s[i] - self.s[j])
        return min(d, self.lap - d) if self.closed else d

    def near(self, x: float, z: float, r: float):
        R = int(math.ceil(r / CELL_M))
        ci, cj = int(math.floor(x / CELL_M)), int(math.floor(z / CELL_M))
        for di in range(-R, R + 1):
            for dj in range(-R, R + 1):
                for k in self.cells.get((ci + di, cj + dj), ()):
                    d = math.hypot(self.p[k][0] - x, self.p[k][2] - z)
                    if d < r:
                        yield k, d

    def candidates(self, ci: int, cj: int, cache: dict, stacked: list) -> list:
        """Lap points that can lie within PAIR_PLAN_M of any point of cell (ci, cj), as (k, x, z); an empty list
        when none of them is a stacked point (nothing in that cell can be at a pair)."""
        key = (ci, cj)
        got = cache.get(key)
        if got is None:
            R = int(math.ceil(PAIR_PLAN_M / CELL_M)) + 1
            got = [(k, self.p[k][0], self.p[k][2]) for di in range(-R, R + 1) for dj in range(-R, R + 1)
                   for k in self.cells.get((ci + di, cj + dj), ())]
            if not any(stacked[k] for k, _x, _z in got):
                got = []
            cache[key] = got
        return got


def find_pairs(lap: Lap):
    """[(i, j, plan_m)] with i < j; plus partner[i] = the nearest-in-plan partner of i (or -1)."""
    pairs = []
    partner = [-1] * len(lap.p)
    pd = [math.inf] * len(lap.p)
    for i, (x, _y, z) in enumerate(lap.p):
        for j, d in lap.near(x, z, PAIR_PLAN_M):
            if j <= i or lap.along(i, j) <= PAIR_ALONG_M:
                continue
            pairs.append((i, j, d))
            if d < pd[i]:
                pd[i], partner[i] = d, j
            if d < pd[j]:
                pd[j], partner[j] = d, i
    return pairs, partner


def _seg_cross(a, b, c, d) -> bool:
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[2] - p[2]) - (q[2] - p[2]) * (r[0] - p[0])
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    if o1 == o2 == 0:                       # collinear: legs running along each other are a pair, not a crossing
        return False
    return o1 * o2 <= 0 and o3 * o4 <= 0    # touching counts (a vertex exactly on the other leg)


def find_crossings(lap: Lap):
    """[(station_i, station_j)] where two lap segments > PAIR_ALONG_M apart along the lap cross in plan."""
    n = len(lap.p)
    out = []
    segs = range(n if lap.closed else n - 1)
    for i in segs:
        a, b = lap.p[i], lap.p[(i + 1) % n]
        for j, _d in lap.near(a[0], a[2], 2.5 * STEP_M):
            if j <= i or lap.along(i, j) <= PAIR_ALONG_M or (not lap.closed and j >= n - 1):
                continue
            c, d = lap.p[j], lap.p[(j + 1) % n]
            if _seg_cross(a, b, c, d):
                out.append((i, j))
    # one crossing touches a few segment pairs: keep one per (i, j) neighbourhood
    merged = []
    for i, j in sorted(out):
        if merged and lap.along(merged[-1][0], i) < 5 and lap.along(merged[-1][1], j) < 5:
            continue
        merged.append((i, j))
    return merged


def _stats(vals):
    if not vals:
        return None
    v = sorted(vals)
    return {"min": round(v[0], 2), "median": round(statistics.median(v), 2), "max": round(v[-1], 2)}


def pair_summary(lap: Lap, pairs) -> dict:
    gaps = [abs(lap.road[i] - lap.road[j]) for i, j, _ in pairs]
    stacked = sorted({i for i, _, _ in pairs} | {j for _, j, _ in pairs})
    runs, start, prev = [], None, None
    for k in stacked:
        if start is None:
            start = prev = k
        elif k == prev + 1:
            prev = k
        else:
            runs.append((round(lap.s[start], 1), round(lap.s[prev], 1)))
            start = prev = k
    if start is not None:
        runs.append((round(lap.s[start], 1), round(lap.s[prev], 1)))
    return {"pairs": len(pairs), "stacked_points": len(stacked), "stacked_runs": runs,
            "nearest_plan_m": round(min(d for _, _, d in pairs), 2) if pairs else None,
            "vertical_gap_m": _stats(gaps)}


def run(project: Path, *, obj: Path | None = None, line_only: bool = False) -> dict:
    project = Path(project)
    cfgp = project / "track.config.json"
    if not cfgp.exists():
        raise InputError(f"{project}: no track.config.json")
    cfg = json.loads(cfgp.read_text(encoding="utf-8"))
    try:
        pts, widths, line_src = gate_route.load_route(project, cfg)
    except FileNotFoundError as e:
        raise InputError(str(e))
    classes = dict(DEFAULT_CLASSES)
    classes.update(((cfg.get("gates") or {}).get("stacked_legs") or {}).get("classes") or {})
    lap = Lap(pts, widths)
    report = {"_doc": "Lariat Drive-1 stacked-leg check (tools/verify_stacked_legs.py; V3-PLAN P5, L4, ledger 0048).",
              "line": line_src, "lap_m": round(lap.lap, 1), "closed": lap.closed, "thresholds": THRESHOLDS}
    if line_only:
        pairs, _partner = find_pairs(lap)
        cross = find_crossings(lap)
        report.update({"mode": "line-only (heights from the line itself, not a build: a measurement, never a pass)",
                       "heights": f"{line_src} y", **pair_summary(lap, pairs),
                       "crossings": [(round(lap.s[i], 1), round(lap.s[j], 1)) for i, j in cross], "fail": None})
        return report

    obj = Path(obj) if obj else project / "data" / "track.obj"
    if not obj.exists():
        raise InputError(f"{obj} does not exist: build the gate OBJ from the shipped kn5 first")
    verts, groups = gate_route._load_obj(obj)
    road = TriField()
    n_road = 0
    for g in groups:
        if g["name"].upper().startswith("1ROAD"):
            for t in g["tris"]:
                road.add(verts, t, g["name"])
                n_road += 1
    if not n_road:
        raise InputError(f"{obj}: no 1ROAD geometry — refusing to judge legs against no road")
    no_road = []
    for k, (x, y, z) in enumerate(lap.p):
        h, _ = road.top_at(x, z, y, ROAD_WINDOW_M)
        if h is None:
            no_road.append(k)
        else:
            lap.road[k] = h
    pairs, partner = find_pairs(lap)
    stacked = [q >= 0 for q in partner]
    # a stacked point with no built road under it cannot be judged: that is a failure, not a skip
    missing = [round(lap.s[k], 1) for k in no_road if stacked[k]]
    cross = find_crossings(lap)
    cross_st = [(lap.s[i], lap.s[j]) for i, j in cross]

    def near_crossing(k: int) -> bool:
        return any(min(abs(lap.s[k] - a), lap.lap - abs(lap.s[k] - a)) <= CROSSING_ZONE_M
                   or min(abs(lap.s[k] - b), lap.lap - abs(lap.s[k] - b)) <= CROSSING_ZONE_M for a, b in cross_st)

    tested = defaultdict(int)
    fails = []
    skipped_cross = 0
    by_class_fail = defaultdict(int)
    cache: dict = {}
    for g in groups:
        c = classify(g["name"], classes)
        if c is None:
            continue
        seen = set()
        for t in g["tris"]:
            for vi in t:
                if vi in seen:
                    continue
                seen.add(vi)
                x, y, z = verts[vi]
                cand = lap.candidates(int(math.floor(x / CELL_M)), int(math.floor(z / CELL_M)), cache, stacked)
                if not cand:
                    continue
                own, dmin = -1, PAIR_PLAN_M
                near = []
                for k, px, pz in cand:
                    d = math.hypot(px - x, pz - z)
                    if d < PAIR_PLAN_M:
                        near.append((k, d))
                        if d < dmin:
                            own, dmin = k, d
                if own < 0 or not stacked[own]:
                    continue
                other, dother = -1, math.inf
                for k, d in near:
                    if d < dother and lap.along(own, k) > PAIR_ALONG_M:
                        other, dother = k, d
                if other < 0:
                    continue
                if math.hypot(lap.p[own][0] - lap.p[other][0], lap.p[own][2] - lap.p[other][2]) >= PAIR_PLAN_M:
                    continue
                if cross_st and near_crossing(own) and near_crossing(other):
                    skipped_cross += 1
                    continue
                tested[c] += 1
                d_own, d_other = abs(y - lap.road[own]), abs(y - lap.road[other])
                if d_other < d_own:
                    by_class_fail[c] += 1
                    fails.append({"class": c, "group": g["name"], "x": round(x, 2), "y": round(y, 2), "z": round(z, 2),
                                  "own_station_m": round(lap.s[own], 1), "other_station_m": round(lap.s[other], 1),
                                  "dy_own_m": round(d_own, 2), "dy_other_m": round(d_other, 2),
                                  "plan_own_m": round(dmin, 2), "plan_other_m": round(dother, 2)})
    report.update({
        "mode": "built", "obj": obj.name, "heights": "the built 1ROAD under each lap point",
        "lap_points_without_road": len(no_road),
        "stacked_points_without_road": len(missing), "stacked_points_without_road_st": missing[:WORST_N],
        **pair_summary(lap, pairs),
        "crossings": [(round(a, 1), round(b, 1)) for a, b in cross_st],
        "crossing_skipped": skipped_cross,
        "tested": dict(tested), "tested_total": sum(tested.values()),
        "failures": len(fails), "failures_by_class": dict(by_class_fail),
        "worst": sorted(fails, key=lambda f: -(f["dy_own_m"] - f["dy_other_m"]))[:WORST_N],
        "fail": len(fails) > MAX_FAILURES or bool(missing),
    })
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="stacked-leg check on the built track (L4; Lariat Drive-1 gate)")
    ap.add_argument("project", type=Path)
    ap.add_argument("--obj", type=Path)
    ap.add_argument("--out", type=Path, help="default <project>/data/stacked_legs.json "
                                             "(--line-only: data/stacked_legs.line.json)")
    ap.add_argument("--line-only", action="store_true", help="pairs and gaps on the line's own heights (no build)")
    a = ap.parse_args(argv)
    try:
        rep = run(a.project, obj=a.obj, line_only=a.line_only)
    except InputError as e:
        print(f"stacked legs: INPUT ERROR: {e}")
        return 2
    out = a.out or (a.project / "data" / ("stacked_legs.line.json" if a.line_only else "stacked_legs.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
    print(f"STACKED LEGS {a.project.name}  ({rep['mode']}; line {rep['line']}, lap {rep['lap_m']} m)")
    print(f"  pairs (< {PAIR_PLAN_M:g} m in plan, > {PAIR_ALONG_M:g} m along): {rep['pairs']} on "
          f"{rep['stacked_points']} lap points; nearest {rep['nearest_plan_m']} m; vertical gap {rep['vertical_gap_m']}")
    print(f"  crossings: {rep['crossings']}")
    if a.line_only:
        print(f"  (line only: no build judged)  ({out})")
        return 0
    print(f"  tested {rep['tested_total']} vertices {rep['tested']}; skipped at crossings {rep['crossing_skipped']}; "
          f"lap points with no road under them {rep['lap_points_without_road']} "
          f"(stacked, so unjudgeable — fails: {rep['stacked_points_without_road']})")
    print(f"  closer in height to the other leg: {rep['failures']} {rep['failures_by_class']}")
    for f in rep["worst"][:6]:
        print(f"    worst: {f}")
    print(f"  => {'FAIL' if rep['fail'] else 'PASS'}   ({out})")
    return 1 if rep["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
