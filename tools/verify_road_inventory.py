"""Road inventory: the built track carries the lap's road and nothing else that is paved (Lariat Drive-1 gate).

Lookout Lariat V3-PLAN P5 (ledger 0048; Kevin 2026-10-10: "no extra highways (they look like wavy ribbons
now)"). Judged on the BUILT artifact (L5): a gate OBJ (``scripts.modkit.kn5_to_gate_obj`` from the shipped
kn5, or ``--kn5`` here, which decodes it the same way) — never the data that placed the road. A separate tool,
not a ``verify_kn5`` section, so it can land while ``scripts/ac/verify_kn5.py`` is held by the terrain job.

Three checks:

  (a) FORBIDDEN MESHES. Groups named ``HIGHWAY*`` / ``HWYSTRUCT*`` (the engine environment's ~40 km of
      C-470 / I-70 decks, build_env.py) or ``MOUNTAINS*`` (its sine ridge), with or without a physics prefix
      (``1ROAD_HIGHWAY...`` counts): 0. [std: Kevin's "no extra highways", 0048; MOUNTAINS: rule L1 as 0046
      applies it to the sine ridge.]
  (b) PAVEMENT STAYS ON THE ROUTE. Every pavement triangle (a group whose name starts with one of the
      exemption file's ``pavement_prefixes``; default ``1ROAD``) lies within half-width + CORRIDOR_MARGIN_M of
      the route [invented, 0048], or inside a declared exemption polygon. Each triangle is judged at its three
      vertices and its centroid; each of the four points must be in the corridor (the route's lerped half-width
      at its nearest segments, + the margin) or inside an exemption polygon that applies to the triangle's
      group. Exemptions live in ``<project>/pavement_exemptions.json``; each one names the ``AUTH_*`` object it
      covers, and an exemption with an empty polygon exempts nothing (it is listed as unmeasured).
  (c) THE PAVEMENT IS THE LAP. For each declared layout, the pavement under the route (a pavement triangle
      under the line, within ROAD_WINDOW_M of the line's height so a stacked leg or a deck overhead is not
      read for it), walked at 1 m, is within LAP_TOL of the lap's length [invented, 0048]. All Lariat layouts
      share one road (L8; D2 a), so each walks the same route unless the layout names its own
      ``centerline`` file under data/.

    python tools/verify_road_inventory.py <project> [--obj data/track.obj | --kn5 build/<slug>.kn5 ...]
        [--exemptions <json>] [--out data/road_inventory.json]

Exit 0 pass, 1 fail, 2 input error (no OBJ, no route, a malformed exemption file).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import gate_route  # noqa: E402
from scripts.geometry.drive_test import TriField  # noqa: E402

FORBIDDEN_RX = re.compile(r"^(?:\d+[A-Z]*_)?(HIGHWAY|HWYSTRUCT|MOUNTAINS)", re.I)
DEFAULT_PAVEMENT = ("1ROAD",)
CORRIDOR_MARGIN_M = 2.0       # [invented] (V3-PLAN P5, 0048): half-width + this
LAP_TOL = 0.01                # [invented] (V3-PLAN P5, 0048): paved length within 1 % of the lap
ROAD_WINDOW_M = 2.5           # drive_test's deck window (top_at y_ref): the road under the line, not a leg above
WALK_STEP_M = 1.0
SEG_CELL_M = 20.0
WORST_N = 25
THRESHOLDS = {"corridor_margin_m": CORRIDOR_MARGIN_M, "lap_tol": LAP_TOL, "road_window_m": ROAD_WINDOW_M,
              "forbidden": "HIGHWAY* / HWYSTRUCT* / MOUNTAINS* (digit+KEY_ prefix allowed): 0",
              "_tags": "forbidden meshes [std: Kevin 0048 / L1]; corridor margin and lap tolerance [invented] "
                       "2026-10-12 (fleet/GATES-CHANGELOG.md)"}


class InputError(Exception):
    pass


# --- the exemption file --------------------------------------------------------------------------------------

def load_exemptions(path: Path | None, to_frame) -> dict:
    """{'pavement_prefixes': [...], 'polys': [{id, object, match, poly[(x,z)], active}], 'unmeasured': [...]}"""
    if path is None or not Path(path).exists():
        return {"pavement_prefixes": list(DEFAULT_PAVEMENT), "polys": [], "unmeasured": [], "inactive": [],
                "file": None}
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise InputError(f"{path}: not JSON ({e})")
    prefixes = d.get("pavement_prefixes") or list(DEFAULT_PAVEMENT)
    if not all(isinstance(p, str) and p for p in prefixes):
        raise InputError(f"{path}: pavement_prefixes must be non-empty strings")
    polys, unmeasured, inactive, seen = [], [], [], set()
    for e in d.get("exemptions") or []:
        eid, obj = e.get("id"), e.get("object")
        if not eid or eid in seen:
            raise InputError(f"{path}: every exemption needs a unique id (got {eid!r})")
        seen.add(eid)
        if not (isinstance(obj, str) and obj.startswith("AUTH_")):
            raise InputError(f"{path}: exemption {eid!r} must name the AUTH_* object it covers (got {obj!r})")
        match = e.get("match", "footprint")
        if match not in ("footprint", "name_and_footprint"):
            raise InputError(f"{path}: exemption {eid!r} match must be footprint|name_and_footprint")
        if e.get("active") is False:
            inactive.append(eid)
            continue
        poly = []
        if e.get("polygon_xz"):
            poly = [(float(p[0]), float(p[1])) for p in e["polygon_xz"]]
        elif e.get("polygon_lonlat"):
            if to_frame is None:
                raise InputError(f"{path}: exemption {eid!r} is in lon/lat but the project has no "
                                 f"data/centerline.local.json origin to project it with")
            poly = [to_frame(float(p[0]), float(p[1])) for p in e["polygon_lonlat"]]
        if len(poly) < 3:
            unmeasured.append(eid)
            continue
        polys.append({"id": eid, "object": obj, "match": match, "poly": poly,
                      "bbox": (min(p[0] for p in poly), min(p[1] for p in poly),
                               max(p[0] for p in poly), max(p[1] for p in poly))})
    return {"pavement_prefixes": prefixes, "polys": polys, "unmeasured": unmeasured, "inactive": inactive,
            "file": str(path)}


def _exempt_at(x: float, z: float, group: str, polys) -> str | None:
    up = group.upper()
    for e in polys:
        x0, z0, x1, z1 = e["bbox"]
        if not (x0 <= x <= x1 and z0 <= z <= z1):
            continue
        if e["match"] == "name_and_footprint" and e["object"].upper() not in up:
            continue
        if gate_route.point_in_polygon(x, z, e["poly"]):
            return e["id"]
    return None


# --- the corridor --------------------------------------------------------------------------------------------

class Corridor:
    """Plan distance to the route with the half-width lerped along each segment: (beyond_m, station, seg).
    beyond_m <= 0 means inside half-width + margin."""

    def __init__(self, pts, widths, margin: float):
        self.pts, self.widths, self.margin = pts, widths, margin
        self.st = gate_route.stations(pts)
        self.cells: dict = defaultdict(list)
        reach = max(widths) / 2.0 + margin
        for i in range(1, len(pts)):
            a, b = pts[i - 1], pts[i]
            x0, x1 = min(a[0], b[0]) - reach, max(a[0], b[0]) + reach
            z0, z1 = min(a[2], b[2]) - reach, max(a[2], b[2]) + reach
            for ci in range(int(math.floor(x0 / SEG_CELL_M)), int(math.floor(x1 / SEG_CELL_M)) + 1):
                for cj in range(int(math.floor(z0 / SEG_CELL_M)), int(math.floor(z1 / SEG_CELL_M)) + 1):
                    self.cells[(ci, cj)].append(i)

    def beyond(self, x: float, z: float):
        best = None
        for i in self.cells.get((int(math.floor(x / SEG_CELL_M)), int(math.floor(z / SEG_CELL_M))), ()):
            a, b = self.pts[i - 1], self.pts[i]
            dx, dz = b[0] - a[0], b[2] - a[2]
            L2 = dx * dx + dz * dz
            u = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[2]) * dz) / L2))
            d = math.hypot(x - a[0] - u * dx, z - a[2] - u * dz)
            half = (self.widths[i - 1] + (self.widths[i] - self.widths[i - 1]) * u) / 2.0
            v = d - half - self.margin
            if best is None or v < best[0]:
                best = (v, self.st[i - 1] + u * math.sqrt(L2), i)
        return best          # None: no segment within reach at all (far beyond)


# --- the gate ------------------------------------------------------------------------------------------------

def _tri_area(a, b, c) -> float:
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    return 0.5 * math.sqrt((uy * vz - uz * vy) ** 2 + (uz * vx - ux * vz) ** 2 + (ux * vy - uy * vx) ** 2)


def run(project: Path, *, obj: Path | None = None, exemptions: Path | None = None) -> dict:
    project = Path(project)
    cfgp = project / "track.config.json"
    if not cfgp.exists():
        raise InputError(f"{project}: no track.config.json")
    cfg = json.loads(cfgp.read_text(encoding="utf-8"))
    obj = Path(obj) if obj else project / "data" / "track.obj"
    if not obj.exists():
        raise InputError(f"{obj} does not exist: build the gate OBJ from the shipped kn5 first "
                         f"(python -m scripts.modkit.kn5_to_gate_obj {project})")
    try:
        pts, widths, line_src = gate_route.load_route(project, cfg)
    except FileNotFoundError as e:
        raise InputError(str(e))
    exm_path = Path(exemptions) if exemptions else project / "pavement_exemptions.json"
    exm = load_exemptions(exm_path if exm_path.exists() else None, gate_route.lonlat_to_frame(project, cfg))
    prefixes = tuple(p.upper() for p in exm["pavement_prefixes"])

    verts, groups = gate_route._load_obj(obj)
    forbidden = sorted({g["name"] for g in groups if FORBIDDEN_RX.match(g["name"])})
    pave_groups = [g for g in groups if g["name"].upper().startswith(prefixes)]

    corr = Corridor(pts, widths, CORRIDOR_MARGIN_M)
    vcache: dict = {}
    bad_tris, bad_area, n_tris, exempt_hits = [], 0.0, 0, defaultdict(int)
    paved = TriField()

    def judge(x, z, gname):
        b = corr.beyond(x, z)
        if b is not None and b[0] <= 0.0:
            return True, b, None
        ex = _exempt_at(x, z, gname, exm["polys"])
        return (ex is not None), b, ex

    for g in pave_groups:
        gname = g["name"]
        for tri in g["tris"]:
            n_tris += 1
            a, b, c = (verts[k] for k in tri)
            paved.add(verts, tri, gname)
            worst, ok, used_ex = None, True, None
            for key, (x, z) in ((tri[0], (a[0], a[2])), (tri[1], (b[0], b[2])), (tri[2], (c[0], c[2])),
                                (None, ((a[0] + b[0] + c[0]) / 3.0, (a[2] + b[2] + c[2]) / 3.0))):
                ck = (key, gname) if key is not None else None
                r = vcache.get(ck) if ck is not None else None
                if r is None:
                    r = judge(x, z, gname)
                    if ck is not None:
                        vcache[ck] = r
                good, bnd, ex = r
                if ex:
                    used_ex = ex
                if not good:
                    ok = False
                    d = bnd[0] if bnd else float("inf")
                    if worst is None or d > worst[0]:
                        worst = (d, x, z, bnd[1] if bnd else None)
            if used_ex:
                exempt_hits[used_ex] += 1
            if not ok:
                area = _tri_area(a, b, c)
                bad_area += area
                bad_tris.append({"group": gname, "beyond_m": (round(worst[0], 2) if math.isfinite(worst[0]) else None),
                                 "x": round(worst[1], 2), "z": round(worst[2], 2),
                                 "nearest_station_m": (round(worst[3], 1) if worst[3] is not None else None),
                                 "area_m2": round(area, 3)})

    # (c) the pavement under each layout's lap
    layouts = [lo for lo in cfg.get("layouts") or [] if isinstance(lo, dict) and lo.get("id")] or [{"id": None}]
    lap_rows = {}
    for lo in layouts:
        lp, lw, src = pts, widths, line_src
        if lo.get("centerline"):
            p = project / "data" / str(lo["centerline"])
            if not p.exists():
                raise InputError(f"layout {lo['id']!r} names centerline data/{lo['centerline']}, which does not exist")
            lc = json.loads(p.read_text(encoding="utf-8"))
            lp, lw, src = [tuple(map(float, q)) for q in lc["points_xyz_m"]], lc["widths_m"], lo["centerline"]
        rp, _rw, rs = gate_route.resample(lp, lw, WALK_STEP_M)
        lap = rs[-1]
        on, gaps, run_start = 0, [], None
        for (x, y, z), s in zip(rp, rs):
            h, _own = paved.top_at(x, z, y, ROAD_WINDOW_M)
            if h is not None:
                on += 1
                if run_start is not None:
                    gaps.append((round(run_start, 1), round(s, 1)))
                    run_start = None
            elif run_start is None:
                run_start = s
        if run_start is not None:
            gaps.append((round(run_start, 1), round(rs[-1], 1)))
        ratio = on / len(rp) if rp else 0.0          # stations carry both ends: the share, not on * step
        paved_m = ratio * lap
        lap_rows[str(lo["id"])] = {"line": src, "lap_m": round(lap, 1), "paved_m": round(paved_m, 1),
                                   "ratio": round(ratio, 5), "pass": abs(1.0 - ratio) <= LAP_TOL,
                                   "unpaved_runs": sorted(gaps, key=lambda r: r[0] - r[1])[:WORST_N]}

    by_group = defaultdict(int)
    for t in bad_tris:
        by_group[t["group"]] += 1
    fail = bool(forbidden) or bool(bad_tris) or not pave_groups or not all(r["pass"] for r in lap_rows.values())
    report = {
        "_doc": "Lariat Drive-1 road inventory (tools/verify_road_inventory.py; V3-PLAN P5, ledger 0048), on the "
                "built gate OBJ (L5).",
        "obj": str(obj.name), "line": line_src, "exemptions_file": exm["file"],
        "thresholds": THRESHOLDS,
        "forbidden_meshes": len(forbidden), "forbidden_names": forbidden[:50],
        "pavement_prefixes": list(prefixes), "pavement_groups": len(pave_groups), "pavement_tris": n_tris,
        "off_route_tris": len(bad_tris), "off_route_area_m2": round(bad_area, 2),
        "off_route_by_group": dict(sorted(by_group.items(), key=lambda kv: -kv[1])[:WORST_N]),
        "worst_off_route": sorted(bad_tris, key=lambda t: -(t["beyond_m"] if t["beyond_m"] is not None else 1e9))[:WORST_N],
        "exemptions_used": dict(exempt_hits),
        "exemptions_declared": [e["id"] for e in exm["polys"]],
        "exemptions_unmeasured": exm["unmeasured"], "exemptions_inactive": exm["inactive"],
        "lap": lap_rows,
        "fail": fail,
    }
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="road inventory on the built track (Lariat Drive-1 gate)")
    ap.add_argument("project", type=Path)
    ap.add_argument("--obj", type=Path, help="gate OBJ (default <project>/data/track.obj)")
    ap.add_argument("--kn5", type=Path, action="append", help="decode these kn5s into a temporary gate OBJ instead")
    ap.add_argument("--exemptions", type=Path, help="default <project>/pavement_exemptions.json")
    ap.add_argument("--out", type=Path, help="default <project>/data/road_inventory.json")
    a = ap.parse_args(argv)
    try:
        obj = a.obj
        tmp = None
        if a.kn5:
            from scripts.modkit.kn5_to_gate_obj import kn5_to_obj
            for k in a.kn5:
                if not k.exists():
                    raise InputError(f"kn5 not found: {k}")
            tmp = tempfile.TemporaryDirectory()
            obj = Path(tmp.name) / "track.inventory.obj"
            kn5_to_obj(list(a.kn5), obj)
        rep = run(a.project, obj=obj, exemptions=a.exemptions)
        if tmp is not None:
            rep["obj"] = " + ".join(k.name for k in a.kn5) + " (decoded by kn5_to_gate_obj.kn5_to_obj)"
            tmp.cleanup()
    except InputError as e:
        print(f"road inventory: INPUT ERROR: {e}")
        return 2
    out = a.out or (a.project / "data" / "road_inventory.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
    print(f"ROAD INVENTORY {a.project.name}  (OBJ {rep['obj']}, line {rep['line']})")
    print(f"  forbidden meshes (HIGHWAY*/HWYSTRUCT*/MOUNTAINS*): {rep['forbidden_meshes']} {rep['forbidden_names'][:6]}")
    print(f"  pavement: {rep['pavement_groups']} groups, {rep['pavement_tris']} tris ({', '.join(rep['pavement_prefixes'])})")
    print(f"  off the route (> half-width + {CORRIDOR_MARGIN_M} m, no exemption): {rep['off_route_tris']} tris, "
          f"{rep['off_route_area_m2']} m2  {rep['off_route_by_group']}")
    for t in rep["worst_off_route"][:6]:
        print(f"    worst: {t}")
    print(f"  exemptions used {rep['exemptions_used']}; unmeasured (exempt nothing) {rep['exemptions_unmeasured']}")
    for lid, r in rep["lap"].items():
        print(f"  layout {lid}: paved {r['paved_m']} m of {r['lap_m']} m lap ({r['ratio']:.4f}; tol {LAP_TOL:.0%}) "
              f"{'ok' if r['pass'] else 'FAIL'}  {r['unpaved_runs'][:4]}")
    print(f"  => {'FAIL' if rep['fail'] else 'PASS'}   ({out})")
    return 1 if rep["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
