"""Route one-way check — does a layout's lap drive against the arrows of a one-way OSM way?

Lookout Lariat V3 plan, P0 step 8 (ledger 0048, dossier §2d). The July route list made the Lariat's lap
drive ~100 m the wrong way up a one-way at the US-6 ramp end and 84 m the wrong way at I-70 exit 259,
and no gate could see either: every gate measures the built road, none asks which way the real road
runs. This is that question, asked of the route itself before any geometry exists.

How it works (pure Python, no network):

1. The centreline (``data/centerline.geojson``, the ``kind: full`` feature, lon/lat) is projected to
   local ENU metres about its own centroid (the WGS84 metres-per-degree series that
   ``scripts/geometry/projection.py`` uses).
2. Each centreline segment is matched to the OSM way it runs ALONG, from an Overpass snapshot
   (``data/osm.cache.json`` by default: the route stage's own snapshot, which keeps both carriageways of
   every divided road and any ``route.exclude_ids`` way). A way is a candidate when both segment ends lie
   within ``--snap-m`` of it and its local direction is parallel (``|cos| >= --min-cos``); the candidate
   with the smallest summed end distance wins, so a segment on one carriageway never matches the other
   one. A segment straddling a junction corner matches no single way and is reported as unmatched
   (never as a run).
3. One-way semantics from the way's tags: ``oneway=yes|true|1`` (node order), ``oneway=-1`` (against
   node order), ``junction=roundabout|circular`` (implied node order). ``reversible`` / ``alternating`` are
   listed, never judged. Everything else is two-way.
4. Per layout (``layouts[]`` in ``track.config.json``): ``direction: forward`` drives increasing vertex
   order, ``reverse`` the opposite. Consecutive segments on one way are merged into runs.

The verdict, per **street** layout (race layouts are closed roads and are not checked):

* every run against a one-way way must lie on a stretch the layout DECLARES it drives against
  (``layouts[].against_oneway`` -> ids in ``divided.stretches[].ways``), otherwise FAIL;
* every declared stretch must actually be driven against by that layout (a declaration that matches
  nothing is stale), otherwise FAIL;
* a layout that declares nothing must drive against nothing (the Full direction's rule: 0).

The threshold is [std]: the real road's direction, from its OSM ``oneway`` tags. ``--snap-m 3.0`` and
``--min-cos 0.7`` are matching parameters [invented], not thresholds.

Writes ``data/oneway_check.json`` (``--out``) and exits 1 on any FAIL, 2 on a usage/config error.

    python tools/route_oneway_check.py <project-dir> [--centerline <geojson>] [--snapshot <json>]
                                       [--layout <id>]... [--out <json>] [--snap-m 3.0] [--min-cos 0.7]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

SNAP_M = 3.0          # [invented] both segment ends within this of the way
MIN_COS = 0.7         # [invented] |cos| between the segment and the way's local direction (~45 deg)
CELL_M = 25.0         # spatial hash cell (performance only)
ONEWAY_FWD = {"yes", "true", "1"}
ONEWAY_REV = {"-1", "reverse"}
ONEWAY_UNJUDGED = {"reversible", "alternating"}
ROUNDABOUT = {"roundabout", "circular"}


# --------------------------------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------------------------------
def load_centerline(path: Path) -> list[tuple[float, float]]:
    gj = json.loads(Path(path).read_text(encoding="utf-8"))
    feats = gj.get("features", [gj])
    full = next((f for f in feats if (f.get("properties") or {}).get("kind") == "full"), None)
    if full is None:
        full = next((f for f in feats if (f.get("geometry") or {}).get("type") == "LineString"), None)
    if full is None:
        raise SystemExit(f"[oneway] no centreline LineString in {path}")
    return [(float(c[0]), float(c[1])) for c in full["geometry"]["coordinates"]]


def load_snapshot(path: Path) -> tuple[list[dict], dict]:
    """Ways (id, tags, geometry) from an Overpass snapshot: the route stage's cache
    ({query_fingerprint, fetched_utc, payload}), the widths stage's cache (same shape) or a raw
    Overpass payload ({elements})."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    payload = d.get("payload", d)
    ways = []
    for el in payload.get("elements", []):
        if el.get("type") != "way" or len(el.get("geometry") or []) < 2:
            continue
        ways.append({"id": int(el["id"]), "tags": el.get("tags", {}) or {},
                     "geom": [(float(g["lon"]), float(g["lat"])) for g in el["geometry"]]})
    meta = {"path": str(path), "query_fingerprint": d.get("query_fingerprint"),
            "fetched_utc": d.get("fetched_utc"),
            "osm_base": (payload.get("osm3s") or {}).get("timestamp_osm_base"), "ways": len(ways)}
    return ways, meta


def oneway_sense(tags: dict) -> int | None:
    """+1 = legal in node order, -1 = legal against node order, 0 = two-way, None = not judged."""
    ow = str(tags.get("oneway", "")).strip().lower()
    if ow in ONEWAY_FWD:
        return 1
    if ow in ONEWAY_REV:
        return -1
    if ow in ONEWAY_UNJUDGED:
        return None
    if ow in ("no", "false", "0"):
        return 0
    if str(tags.get("junction", "")).strip().lower() in ROUNDABOUT:
        return 1
    return 0


# --------------------------------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------------------------------
def meters_per_degree(lat0: float) -> tuple[float, float]:
    """WGS84 series, the one scripts/geometry/projection.py uses (sub-metre over a few km)."""
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    return m_lon, m_lat


class Frame:
    def __init__(self, pts):
        self.lon0 = sum(p[0] for p in pts) / len(pts)
        self.lat0 = sum(p[1] for p in pts) / len(pts)
        self.mlon, self.mlat = meters_per_degree(self.lat0)

    def xy(self, p):
        return ((p[0] - self.lon0) * self.mlon, (p[1] - self.lat0) * self.mlat)


def _closest(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)


class WayIndex:
    def __init__(self, ways, frame: Frame):
        self.ways = ways
        self.xy = [[frame.xy(p) for p in w["geom"]] for w in ways]
        self.grid: dict = {}
        for wi, pts in enumerate(self.xy):
            for si in range(len(pts) - 1):
                (ax, ay), (bx, by) = pts[si], pts[si + 1]
                x0, x1 = sorted((ax, bx))
                y0, y1 = sorted((ay, by))
                for cx in range(int(math.floor(x0 / CELL_M)), int(math.floor(x1 / CELL_M)) + 1):
                    for cy in range(int(math.floor(y0 / CELL_M)), int(math.floor(y1 / CELL_M)) + 1):
                        self.grid.setdefault((cx, cy), set()).add((wi, si))

    def near(self, p, reach_m):
        r = int(math.ceil(reach_m / CELL_M))
        cx, cy = int(math.floor(p[0] / CELL_M)), int(math.floor(p[1] / CELL_M))
        out = set()
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                out |= self.grid.get((cx + dx, cy + dy), set())
        return out

    def dist_to_way(self, p, wi):
        pts = self.xy[wi]
        best = (math.inf, 0)
        for si in range(len(pts) - 1):
            d = _closest(p, pts[si], pts[si + 1])
            if d < best[0]:
                best = (d, si)
        return best


def match_segments(line_xy, index: WayIndex, snap_m=SNAP_M, min_cos=MIN_COS):
    """Per centreline segment i -> (way index, sense) or None. sense +1 = travelling in the way's node
    order when the line is driven in increasing vertex order."""
    out = []
    for i in range(len(line_xy) - 1):
        a, b = line_xy[i], line_xy[i + 1]
        sx, sy = b[0] - a[0], b[1] - a[1]
        sl = math.hypot(sx, sy)
        if sl < 1e-9:
            out.append(None)
            continue
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        cands = {wi for wi, _ in index.near(mid, snap_m + sl)}
        best = None
        for wi in cands:
            da, _ = index.dist_to_way(a, wi)
            db, _ = index.dist_to_way(b, wi)
            if da > snap_m or db > snap_m:
                continue
            dm, si = index.dist_to_way(mid, wi)
            pts = index.xy[wi]
            wx, wy = pts[si + 1][0] - pts[si][0], pts[si + 1][1] - pts[si][1]
            wl = math.hypot(wx, wy) or 1e-12
            c = (sx * wx + sy * wy) / (sl * wl)
            if abs(c) < min_cos:
                continue
            score = da + db + dm
            if best is None or score < best[0]:
                best = (score, wi, 1 if c > 0 else -1)
        out.append(None if best is None else (best[1], best[2]))
    return out


# --------------------------------------------------------------------------------------------------
# runs and verdicts
# --------------------------------------------------------------------------------------------------
def _tag_summary(tags):
    keep = ("highway", "name", "ref", "oneway", "junction", "lanes", "destination", "turn:lanes")
    return {k: tags[k] for k in keep if k in tags}


def build_runs(matches, seg_len, stations, ways, direction):
    """Merge consecutive segments on one way (in the layout's driving order) into runs."""
    n = len(matches)
    order = range(n) if direction == "forward" else range(n - 1, -1, -1)
    lap = stations[-1]
    runs = []
    cur = None
    for i in order:
        m = matches[i]
        key = None if m is None else (m[0], m[1] if direction == "forward" else -m[1])
        if cur is not None and key == cur["key"]:
            cur["segs"].append(i)
            continue
        if cur is not None:
            runs.append(cur)
        cur = {"key": key, "segs": [i]}
    if cur is not None:
        runs.append(cur)
    # a closed lap: a run that wraps the seam is one run
    closed = len(runs) > 1 and runs[0]["key"] == runs[-1]["key"] and runs[0]["key"] is not None
    if closed:
        runs[0]["segs"] = runs[-1]["segs"] + runs[0]["segs"]
        runs.pop()
    out = []
    for r in runs:
        segs = r["segs"]
        length = sum(seg_len[i] for i in segs)
        lo, hi = min(segs), max(segs)
        first, last = segs[0], segs[-1]
        # forward stations of the run's two ends (wrap-aware: the run's own first/last segment)
        if direction == "forward":
            st_from, st_to = stations[first], stations[last + 1]
        else:
            st_from, st_to = stations[first + 1], stations[last]
        rec = {"segments": len(segs), "length_m": round(length, 1),
               "vertex_from": first if direction == "forward" else first + 1,
               "vertex_to": last + 1 if direction == "forward" else last,
               "st_from_m": round(st_from, 1), "st_to_m": round(st_to, 1),
               "drive_st_from_m": round(st_from if direction == "forward" else (lap - st_from) % lap, 1)}
        if r["key"] is None:
            rec["matched"] = False
        else:
            wi, sense_travel = r["key"]
            w = ways[wi]
            legal = oneway_sense(w["tags"])
            rec.update({"matched": True, "way": w["id"], "tags": _tag_summary(w["tags"]),
                        "travel_vs_nodes": sense_travel, "oneway": legal,
                        "against": bool(legal) and legal * sense_travel < 0,
                        "with_arrows": bool(legal) and legal * sense_travel > 0,
                        "unjudged": legal is None})
        out.append(rec)
    return out


def check_layout(layout, runs, stretches):
    lid = layout.get("id", "?")
    kind = layout.get("kind", "street")
    res = {"id": lid, "kind": kind, "direction": layout.get("direction", "forward")}
    if kind == "race":
        res.update({"checked": False, "verdict": "SKIP",
                    "why": "race layouts are closed roads; one-way rules do not apply (V3-PLAN P0 step 8)"})
        return res, []
    declared = list(layout.get("against_oneway") or [])
    fails = []
    unknown = [d for d in declared if d not in stretches]
    if unknown:
        fails.append(f"{lid}: against_oneway names stretch(es) {unknown} not declared in divided.stretches")
    declared_ways = {w: s for s in declared if s in stretches for w in stretches[s]}
    against = [r for r in runs if r.get("against")]
    undeclared = [r for r in against if r["way"] not in declared_ways]
    for r in undeclared:
        fails.append(f"{lid}: drives {r['length_m']} m AGAINST oneway way {r['way']} "
                     f"({r['tags'].get('name') or r['tags'].get('ref') or r['tags'].get('highway')}) "
                     f"at st {r['st_from_m']}-{r['st_to_m']} - not a declared stretch")
    driven = {}
    for r in against:
        s = declared_ways.get(r["way"])
        if s:
            driven[s] = driven.get(s, 0.0) + r["length_m"]
    for s in declared:
        if s in stretches and driven.get(s, 0.0) <= 0.0:
            fails.append(f"{lid}: declares it drives stretch {s!r} against the arrows, but no run does - "
                         f"stale declaration")
    unjudged = [r for r in runs if r.get("unjudged")]
    res.update({
        "checked": True,
        "verdict": "FAIL" if fails else "PASS",
        "declared_stretches": declared,
        "against_runs": against,
        "against_total_m": round(sum(r["length_m"] for r in against), 1),
        "against_by_stretch_m": {k: round(v, 1) for k, v in sorted(driven.items())},
        "undeclared_against_m": round(sum(r["length_m"] for r in undeclared), 1),
        "with_arrows_runs": [r for r in runs if r.get("with_arrows")],
        "unjudged_runs": unjudged,
    })
    return res, fails


def run_check(project, *, centerline=None, snapshot=None, only=None, snap_m=SNAP_M, min_cos=MIN_COS,
              config=None):
    project = Path(project)
    cfg = config if config is not None else json.loads((project / "track.config.json").read_text(encoding="utf-8"))
    cl_path = Path(centerline) if centerline else project / "data" / "centerline.geojson"
    snap_path = Path(snapshot) if snapshot else project / "data" / "osm.cache.json"
    line = load_centerline(cl_path)
    ways, meta = load_snapshot(snap_path)
    frame = Frame(line)
    lxy = [frame.xy(p) for p in line]
    seg_len = [math.dist(lxy[i], lxy[i + 1]) for i in range(len(lxy) - 1)]
    stations = [0.0]
    for s in seg_len:
        stations.append(stations[-1] + s)
    index = WayIndex(ways, frame)
    matches = match_segments(lxy, index, snap_m, min_cos)

    stretches = {}
    for s in ((cfg.get("divided") or {}).get("stretches") or []):
        stretches[s["id"]] = {int(w) for w in s.get("ways") or []}
    layouts = [lo for lo in (cfg.get("layouts") or []) if isinstance(lo, dict)]
    if only:
        stale = [o for o in only if o not in {lo.get("id") for lo in layouts}]
        if stale:
            raise SystemExit(f"[oneway] --layout {stale} not in layouts[]")
        layouts = [lo for lo in layouts if lo.get("id") in only]
    if not layouts:
        layouts = [{"id": "forward", "kind": "street", "direction": "forward"}]

    fwd_runs = build_runs(matches, seg_len, stations, ways, "forward")
    unmatched = [r for r in fwd_runs if not r["matched"]]
    driven = {}
    for r in fwd_runs:
        if r["matched"]:
            e = driven.setdefault(r["way"], {"way": r["way"], "tags": r["tags"], "length_m": 0.0,
                                             "first_st_m": r["st_from_m"], "travel_vs_nodes": r["travel_vs_nodes"]})
            e["length_m"] = round(e["length_m"] + r["length_m"], 1)
    report = {
        "tool": "tools/route_oneway_check.py",
        "frame": ("input lon/lat (WGS84); matching in local ENU metres (x=E, y=N) about the centreline's own "
                  "centroid, WGS84 metres-per-degree series; stations = metres along the centreline in "
                  "increasing-vertex (forward) order from v0"),
        "centerline": {"path": str(cl_path), "points": len(line), "length_m": round(stations[-1], 1),
                       "closed": line[0] == line[-1]},
        "snapshot": meta,
        "params": {"snap_m": snap_m, "min_cos": min_cos},
        "matched_m": round(sum(r["length_m"] for r in fwd_runs if r["matched"]), 1),
        "unmatched_m": round(sum(r["length_m"] for r in unmatched), 1),
        "unmatched_runs": unmatched,
        "ways_driven_forward": sorted(driven.values(), key=lambda e: e["first_st_m"]),
        "layouts": [],
    }
    fails = []
    for lo in layouts:
        runs = fwd_runs if lo.get("direction", "forward") == "forward" else \
            build_runs(matches, seg_len, stations, ways, "reverse")
        res, lf = check_layout(lo, runs, stretches)
        report["layouts"].append(res)
        fails += lf
    report["fails"] = fails
    report["verdict"] = "FAIL" if fails else "PASS"
    return report


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith("-"):
        print("usage: python tools/route_oneway_check.py <project-dir> [--centerline <geojson>] [--snapshot <json>] "
              "[--layout <id>]... [--out <json>] [--snap-m 3.0] [--min-cos 0.7]")
        return 2
    project = Path(argv[0])
    opts = {"centerline": None, "snapshot": None, "out": None}
    only: list[str] = []
    snap_m, min_cos = SNAP_M, MIN_COS
    i = 1
    try:
        while i < len(argv):
            a = argv[i]
            if a in ("--centerline", "--snapshot", "--out"):
                opts[a[2:]] = argv[i + 1]
                i += 2
            elif a == "--layout":
                only.append(argv[i + 1])
                i += 2
            elif a == "--snap-m":
                snap_m = float(argv[i + 1])
                i += 2
            elif a == "--min-cos":
                min_cos = float(argv[i + 1])
                i += 2
            else:
                print(f"[oneway] unknown argument {a!r}")
                return 2
    except IndexError:
        print("[oneway] missing value for the last option")
        return 2
    report = run_check(project, centerline=opts["centerline"], snapshot=opts["snapshot"], only=only or None,
                       snap_m=snap_m, min_cos=min_cos)
    out = Path(opts["out"]) if opts["out"] else project / "data" / "oneway_check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")

    sm = report["snapshot"]
    print(f"[oneway] centreline {report['centerline']['points']} pts, {report['centerline']['length_m'] / 1000:.2f} km; "
          f"snapshot {Path(sm['path']).name} ({sm['ways']} ways, OSM {sm.get('osm_base') or '?'})")
    print(f"[oneway] matched {report['matched_m']:.0f} m, unmatched {report['unmatched_m']:.0f} m "
          f"in {len(report['unmatched_runs'])} junction gap(s)")
    for res in report["layouts"]:
        if not res["checked"]:
            print(f"[oneway] {res['id']:15} {res['direction']:7} SKIP ({res['why']})")
            continue
        print(f"[oneway] {res['id']:15} {res['direction']:7} {res['verdict']}: against one-ways "
              f"{res['against_total_m']:.0f} m in {len(res['against_runs'])} run(s), undeclared "
              f"{res['undeclared_against_m']:.0f} m; declared {res['declared_stretches'] or 'none'}")
        for r in res["against_runs"]:
            t = r["tags"]
            print(f"           against way {r['way']} {t.get('highway')} "
                  f"{t.get('name') or t.get('ref') or ''} lanes={t.get('lanes', '-')}: "
                  f"st {r['st_from_m']:.0f}-{r['st_to_m']:.0f} ({r['length_m']:.0f} m)")
    for f in report["fails"]:
        print(f"[oneway] FAIL {f}")
    print(f"[oneway] {report['verdict']} -> {out}")
    return 1 if report["fails"] else 0


if __name__ == "__main__":
    sys.exit(main())
