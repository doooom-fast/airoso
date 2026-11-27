"""Declared raised medians -> data/median_bands.json: an island whose centre line is DECLARED (a design drawing read into
the track's source), not measured off a divided road's two OSM carriageways (tools/median_envelope.py) — and which need
not stand in the middle of the line it is indexed on.

    python tools/declared_medians.py <project-dir>

Opt-in: track.config.json route.declared_medians {"file": <project-relative JSON>}; key absent = exit 0, nothing read or
written. The file holds {"islands": [{"name", "width_m", "centre_EN": [[E, N], ...]}]} in the lap's local frame (x = E,
z = N, the frame of data/centerline.local.json). First use: Denver Grand Prix's Colfax bus-lane median, Sherman to Grant
(tracks/denver-grand-prix/source/colfax_median: the DOTI 100% design, Aug 2024, section A-A, on the measured north kerb).

Per mainline vertex (data/centerline.local.json, the closed lap's last point repeating the first): the vertex's left
normal (central difference, one-sided at the ends, as tools/median_island.tangent) is intersected with each island's
centre polyline; where it meets it within REACH_M, the vertex takes the island's width (island_w_by_vertex) and the
crossing's signed lateral (island_off_by_vertex, + = forward-left: a lap's island_off_by_vertex frame, read by
tools/median_island.py, tools/author_median_blend.py, tools/author_median_tops_blend.py, scripts/geometry/median_zone.py,
scripts/ac/write_ai_line.py, tools/barrier_bands.py, tools/no_route.py and tools/road_lanes.py). The island then stands
exactly on its declared centre at every vertex, whatever the line does between its two kerbs.

Self-gates (exit 1, nothing written): every island is met by at least MIN_ISLAND_VERTS vertices in one run (the median
tool builds no shorter island); the offset steps by at most MAX_STEP_M between consecutive island vertices (the
envelope tool's own rule); no two islands claim one vertex; an island run may not cross a closed lap's seam (no
consumer joins a run across it). Writes data/median_bands.json (the mainline channels; any connector_islands already in
the file are kept) and prints a one-line report per island.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REACH_M = 15.0            # [invented] a declared centre further than this off the line is not this line's island
MAX_STEP_M = 1.2          # tools/median_envelope.py MAX_STEP_M: the offset may not step more than this vertex to vertex
MIN_ISLAND_VERTS = 6      # tools/median_island.py MIN_ISLAND_VERTS


def _tangent(pts, k):
    a, b = pts[max(0, k - 1)], pts[min(len(pts) - 1, k + 1)]
    dx, dz = b[0] - a[0], b[2] - a[2]
    d = math.hypot(dx, dz) or 1.0
    return dx / d, dz / d


def _cross(p, nl, poly):
    """the signed lateral u (along the left normal nl from p) where the line p + u nl meets the polyline, |u| <= REACH_M,
    nearest the line; None when it does not"""
    best = None
    for (ax, az), (bx, bz) in zip(poly, poly[1:]):
        dx, dz = bx - ax, bz - az
        den = nl[0] * (-dz) - nl[1] * (-dx)
        if abs(den) < 1e-12:
            continue
        rx, rz = ax - p[0], az - p[2]
        u = (rx * (-dz) - rz * (-dx)) / den
        t = (nl[0] * rz - nl[1] * rx) / den
        if -1e-9 <= t <= 1.0 + 1e-9 and abs(u) <= REACH_M and (best is None or abs(u) < abs(best)):
            best = u
    return best


def plan(pts, islands):
    """(island_w_by_vertex, island_off_by_vertex, report, fails) for the declared islands on the line pts"""
    n = len(pts)
    closed = n > 2 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
    m = n - 1 if closed else n
    iw, off = [0.0] * n, [0.0] * n
    owner = [None] * n
    report, fails = [], []
    for isl in islands:
        name = str(isl["name"])
        w = float(isl["width_m"])
        poly = [(float(e), float(nn)) for e, nn in isl["centre_EN"]]
        hit = []
        for k in range(m):
            tx, tz = _tangent(pts, k)
            u = _cross(pts[k], (-tz, tx), poly)
            if u is None:
                continue
            if owner[k] is not None:
                fails.append(f"{name}: v{k} is also {owner[k]}'s")
                continue
            owner[k] = name
            iw[k], off[k] = round(w, 3), round(u, 3)
            hit.append(k)
        runs, cur = [], []
        for k in hit:
            if cur and k != cur[-1] + 1:
                runs.append(cur)
                cur = []
            cur.append(k)
        if cur:
            runs.append(cur)
        if closed and len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] == m - 1:
            fails.append(f"{name}: its run crosses the closed lap's seam (v{runs[-1][0]}..v{m - 1}, v0..v{runs[0][-1]})")
        if len(runs) != 1 or len(runs[0]) < MIN_ISLAND_VERTS:
            fails.append(f"{name}: met by {len(hit)} vertices in {len(runs)} run(s) — one run of >= {MIN_ISLAND_VERTS} wanted")
            continue
        r = runs[0]
        steps = [abs(off[b] - off[a]) for a, b in zip(r, r[1:])]
        if steps and max(steps) > MAX_STEP_M:
            fails.append(f"{name}: the offset steps {max(steps):.2f} m between consecutive vertices (> {MAX_STEP_M})")
        report.append({"name": name, "vertices": [r[0], r[-1]], "count": len(r), "width_m": round(w, 3),
                       "offset_m": [round(min(off[k] for k in r), 3), round(max(off[k] for k in r), 3)],
                       "max_step_m": round(max(steps), 3) if steps else 0.0})
    if closed:
        iw[n - 1], off[n - 1] = iw[0], off[0]        # the closing point repeats vertex 0
    return iw, off, report, fails


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print(__doc__)
        return 2
    proj = Path(argv[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    spec = (cfg.get("route") or {}).get("declared_medians")
    if not spec:
        print("[declared-medians] route.declared_medians not declared: nothing to do")
        return 0
    src = proj / str(spec["file"])
    islands = json.loads(src.read_text(encoding="utf-8"))["islands"]
    data = proj / "data"
    pts = [tuple(p) for p in json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))["points_xyz_m"]]
    iw, off, report, fails = plan(pts, islands)
    for r in report:
        print(f"[declared-medians] {r['name']}: v{r['vertices'][0]}-v{r['vertices'][1]} ({r['count']} vertices), "
              f"{r['width_m']} m wide, centre {r['offset_m'][0]:+.2f} .. {r['offset_m'][1]:+.2f} m forward-left of the "
              f"line, max step {r['max_step_m']:.2f} m")
    if fails:
        for f in fails:
            print(f"[declared-medians] FAIL {f}")
        return 1
    bp = data / "median_bands.json"
    old = json.loads(bp.read_text(encoding="utf-8")) if bp.exists() else {}
    if any(float(w) > 0 for w in old.get("island_w_by_vertex") or []):
        print("[declared-medians] FAIL data/median_bands.json already declares a mainline island (tools/median_envelope.py?) "
              "— one source per line")
        return 1
    out = {"_doc": f"declared raised medians ({spec['file']}, tools/declared_medians.py): island_off_by_vertex = the "
                   f"island centre's lateral, + = forward-left of the line",
           "island_w_by_vertex": iw, "island_off_by_vertex": off, "declared": report}
    if old.get("connector_islands"):
        out["connector_islands"] = old["connector_islands"]
    bp.write_text(json.dumps(out), encoding="utf-8")
    print(f"[declared-medians] wrote {bp} ({sum(1 for w in iw if w > 0)} island vertices)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
