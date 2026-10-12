"""Centreline paint gate: is the lap on the painted road, smooth on the climb, never folding, closed at the seam,
and free of junction facets off the climb?

Lookout Lariat V3 (ledger 0048, P2). Replaces tools/fit_hairpins.py's 1.5 m-from-OSM criterion as the judge
of WHERE the line runs: the aerial pass showed that criterion passing lines 7 m off the real road (C4, where
OSM itself cuts the hairpin) and failing a line OSM had right (C9). The reference is the paint traced on
public-domain NAIP imagery (``data/aerial/paint_traces.json``, tools/aerial_measure.py).

Checks, on a centreline GeoJSON (default ``data/centerline.geojson``, the ``kind: full`` LineString):

(a) **paint**: every high- or medium-confidence point of the traced double-yellow centre line, in every
    window, lies within ``PAINT_MAX_M`` = 0.75 m [invented] of the line. Distance is to the nearest segment
    running the same way (|angle| < 60 deg to the paint's direction of travel), so a stacked hairpin's other
    leg (20-27 m away, running the opposite way) can never stand in for this one.
(b) **curvature** on the climb (``track.config.json`` ``hairpin_fit.climb_st_m``, stations on the OSM line;
    a paint centreline maps them through its ``osm_station_m``): at every vertex, the heading change
    <= spacing x |k_local| x 57.3 + ``STEP_SLACK_DEG`` 1 deg [invented], where spacing is the mean of the two
    segments at the vertex and k_local the line's own curvature over +-``LOCAL_M`` 5 m [invented] (its turn
    over that window divided by the window's length, i.e. 1 / R_local), so a facet (one point holding a
    window's turn) fails and a steady curve or a clothoid passes; and neighbouring heading changes differ by
    <= ``ADJ_STEP_DEG`` 1.5 deg [invented]. Both rules are defined at the climb's 1 m spacing, so every climb
    segment must be ``SPACING_RANGE_M`` 0.95-1.05 m long [invented] (denser points would make the neighbour
    rule trivially easy, sparser would fail any real spiral).
(c) **no reversal, no self-intersection**: no vertex turns ``REVERSAL_DEG`` 120 deg or more [invented] (the
    OSM line's largest single step is a 78.5 deg junction node), no segment is shorter than 1 mm, and no two
    non-adjacent segments of the lap cross.
(d) **closure** (a closed lap): the closing vertex equals v0 exactly (seam step 0.000 m), and the seam
    vertex, measured across the wrap (v[-2] -> v0 -> v1, skipping the duplicate, L13), passes (b) when the
    climb starts at the seam.

(e) **no facets off the climb** (2026-10-12, ledger 0048 "P2 fixed"): no vertex off the climb turns more than
    ``FACET_STEP_DEG`` 20 deg [invented], or tighter than ``FACET_R_MIN_M`` 6 m over its own spacing (its heading
    change divided into the mean of its two segments) while turning more than 3 deg [invented]. The integrated
    Drive-1 build passed (a)-(d) with single-vertex chevrons of 52-72 deg at C12, C13, C14, exit 259 and the lid's
    east end (built R 3.3-8.4 m, the ribbon folded at C13); tools/paint_centreline.py's junction fillets remove
    them, and this check is what proves it.

Writes ``--out`` (default ``data/aerial/paint_gate.json``) and exits 1 on any failure, 2 on a usage error.

    python tools/verify_centreline_paint.py <project-dir> [--centerline F] [--traces F] [--out F]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.geometry.projection import _meters_per_degree, centroid  # noqa: E402

DEG = 180.0 / math.pi
PAINT_MAX_M = 0.75
STEP_SLACK_DEG = 1.0
ADJ_STEP_DEG = 1.5
LOCAL_M = 5.0
SPACING_RANGE_M = (0.95, 1.05)
REVERSAL_DEG = 120.0
MIN_SEG_M = 0.001
SAME_WAY_COS = 0.5
CELL_M = 25.0
FACET_STEP_DEG = 20.0
FACET_R_MIN_M = 6.0
FACET_MIN_DEG = 3.0
THRESHOLDS = {"paint_max_m": PAINT_MAX_M, "step_slack_deg": STEP_SLACK_DEG, "adjacent_step_deg": ADJ_STEP_DEG,
              "local_window_m": LOCAL_M, "climb_spacing_m": list(SPACING_RANGE_M), "reversal_deg": REVERSAL_DEG,
              "min_segment_m": MIN_SEG_M, "same_way_cos": SAME_WAY_COS, "facet_step_deg": FACET_STEP_DEG,
              "facet_radius_min_m": FACET_R_MIN_M, "facet_min_deg": FACET_MIN_DEG,
              "_tags": "every value [invented] 2026-10-11 (ledger 0048); see fleet/GATES-CHANGELOG.md"}


def _wrap(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


class Line:
    """A centreline in its own plan frame (local ENU metres about its centroid, projection's series)."""

    def __init__(self, lonlat, props=None):
        self.lonlat = lonlat
        self.props = props or {}
        self.lon0, self.lat0 = centroid(lonlat)
        self.mlon, self.mlat = _meters_per_degree(self.lat0)
        self.P = [self.xy(*c) for c in lonlat]
        n = len(self.P)
        self.n = n
        self.closed = n > 2 and math.dist(lonlat[0], lonlat[-1]) < 1e-12
        self.st = [0.0]
        for i in range(1, n):
            self.st.append(self.st[-1] + math.dist(self.P[i - 1], self.P[i]))
        self.cells = {}
        for i in range(n - 1):
            a, b = self.P[i], self.P[i + 1]
            for cx in range(int(math.floor(min(a[0], b[0]) / CELL_M)), int(math.floor(max(a[0], b[0]) / CELL_M)) + 1):
                for cy in range(int(math.floor(min(a[1], b[1]) / CELL_M)), int(math.floor(max(a[1], b[1]) / CELL_M)) + 1):
                    self.cells.setdefault((cx, cy), []).append(i)

    @classmethod
    def from_geojson(cls, gj):
        feats = gj.get("features", [gj])
        f = next((x for x in feats if (x.get("properties") or {}).get("kind") == "full"), None)
        if f is None:
            f = next(x for x in feats if (x.get("geometry") or {}).get("type") == "LineString")
        return cls([(float(c[0]), float(c[1])) for c in f["geometry"]["coordinates"]], f.get("properties") or {})

    def xy(self, lon, lat):
        return ((lon - self.lon0) * self.mlon, (lat - self.lat0) * self.mlat)

    def frame_xy_from_traces(self, traces, x, z):
        lon0, lat0 = traces["frame"]["origin_lonlat"]
        mlon, mlat = _meters_per_degree(lat0)
        return self.xy(lon0 + x / mlon, lat0 + z / mlat)

    def distance(self, lon, lat, lon2, lat2):
        """Distance from (lon, lat) to the nearest segment running the same way as (lon, lat) -> (lon2, lat2)."""
        q = self.xy(lon, lat)
        q2 = self.xy(lon2, lat2)
        hx, hy = q2[0] - q[0], q2[1] - q[1]
        hl = math.hypot(hx, hy) or 1.0
        hx, hy = hx / hl, hy / hl
        cx, cy = int(math.floor(q[0] / CELL_M)), int(math.floor(q[1] / CELL_M))
        for r in (1, 2, 4):
            best = None
            seen = set()
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    for i in self.cells.get((cx + dx, cy + dy), ()):
                        if i in seen:
                            continue
                        seen.add(i)
                        a, b = self.P[i], self.P[i + 1]
                        vx, vy = b[0] - a[0], b[1] - a[1]
                        L = math.hypot(vx, vy)
                        if L <= 0 or (vx * hx + vy * hy) / L < SAME_WAY_COS:
                            continue
                        t = max(0.0, min(1.0, ((q[0] - a[0]) * vx + (q[1] - a[1]) * vy) / (L * L)))
                        d = math.hypot(a[0] + t * vx - q[0], a[1] + t * vy - q[1])
                        if best is None or d < best:
                            best = d
            if best is not None and best <= r * CELL_M:
                return best
        return float("inf")

    def steps(self):
        """Signed heading change at every vertex (radians); on a closed lap v0 (and the closing vertex) is
        measured across the wrap, v[-2] -> v0 -> v1 (L13)."""
        P, n = self.P, self.n
        S = [0.0] * n

        def h(a, b):
            return math.atan2(b[1] - a[1], b[0] - a[0])
        for i in range(1, n - 1):
            S[i] = _wrap(h(P[i], P[i + 1]) - h(P[i - 1], P[i]))
        if self.closed:
            S[0] = _wrap(h(P[0], P[1]) - h(P[n - 2], P[0]))
            S[n - 1] = S[0]
        return S

    def min_radius_near(self, c, within, arm=5.0):
        """Tightest 3-point radius (chords of +-arm metres) among vertices within ``within`` of c."""
        best = None
        for i in range(self.n):
            if math.dist(self.P[i], c) > within:
                continue
            j0 = self._index_at(self.st[i] - arm)
            j1 = self._index_at(self.st[i] + arm) + 1
            if j0 < 0 or j1 >= self.n or j0 == i or j1 == i:
                continue
            a, b, cc = self.P[j0], self.P[i], self.P[j1]
            ab, bc, ca = math.dist(a, b), math.dist(b, cc), math.dist(cc, a)
            cross = abs((b[0] - a[0]) * (cc[1] - a[1]) - (b[1] - a[1]) * (cc[0] - a[0]))
            if cross < 1e-9:
                continue
            r = ab * bc * ca / (2.0 * cross)
            best = r if best is None or r < best else best
        return None if best is None else round(best, 2)

    def _index_at(self, s):
        lo, hi = 0, self.n - 1
        if s < 0 or s > self.st[-1]:
            return -1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.st[mid] <= s:
                lo = mid
            else:
                hi = mid
        return lo


def paint_points(traces, w, levels=("high", "medium")):
    """A window's yellow points of the given confidence as (lon, lat, lon2, lat2): (lon2, lat2) is 1 m ahead in
    the paint's direction of Full travel."""
    lon0, lat0 = traces["frame"]["origin_lonlat"]
    mlon, mlat = _meters_per_degree(lat0)
    y = w["yellow"]
    out = []
    for (x, z), c, h in zip(y["xz_m"], y["confidence"], y["heading_deg"]):
        if c not in levels:
            continue
        hr = math.radians(h)
        out.append((lon0 + x / mlon, lat0 + z / mlat, lon0 + (x + math.cos(hr)) / mlon, lat0 + (z + math.sin(hr)) / mlat))
    return out


def climb_mask(line: Line, climb):
    """Vertices on the climb: by their OSM station (``osm_station_m``) when the line carries it, else by
    the line's own stations."""
    c0, c1 = climb
    src = line.props.get("osm_station_m")
    if src and len(src) == line.n:
        return [c0 <= s <= c1 for s in src], "osm_station_m"
    return [c0 <= s <= c1 for s in line.st], "own stations"


def gate(line: Line, traces, climb, loop=True) -> dict:
    res = {"thresholds": THRESHOLDS}
    # (a) paint
    windows, a_fail = [], []
    for w in traces["windows"]:
        pts = paint_points(traces, w)
        if not pts:
            continue
        ds = [line.distance(*p) for p in pts]
        bad = [(d, p) for d, p in zip(ds, pts) if d > PAINT_MAX_M]
        windows.append({"window": w["id"], "points": len(pts), "max_m": round(max(ds), 3),
                        "median_m": round(sorted(ds)[len(ds) // 2], 3), "over": len(bad)})
        for d, p in sorted(bad, key=lambda x: -x[0])[:5]:
            a_fail.append({"window": w["id"], "distance_m": round(d, 3), "lonlat": [round(p[0], 7), round(p[1], 7)]})
    res["a_paint"] = {"pass": not any(w["over"] for w in windows), "points": sum(w["points"] for w in windows),
                      "over_limit": sum(w["over"] for w in windows),
                      "max_m": max((w["max_m"] for w in windows), default=None), "windows": windows, "worst": a_fail[:40]}
    # (b) curvature on the climb
    S = line.steps()
    mask, how = climb_mask(line, climb)
    n = line.n
    m = n - 1 if line.closed else n            # unique vertices (L13: the closing vertex repeats v0)
    seg = [math.dist(line.P[i], line.P[i + 1]) for i in range(n - 1)]
    seg_u = seg[:m] if line.closed else seg

    def nxt(i):
        return (i + 1) % m if line.closed else (i + 1 if i + 1 < n else None)

    def prv(i):
        return (i - 1) % m if line.closed else (i - 1 if i >= 1 else None)

    def spacing(i):
        a_, b_ = prv(i), nxt(i)
        if a_ is None or b_ is None:
            return None
        return 0.5 * (seg_u[a_] + seg_u[i])

    def local_k(i):
        """The line's curvature at vertex i: its turn over +-LOCAL_M divided by that window's length."""
        turn, length = S[i], spacing(i)
        for step in (prv, nxt):
            j, acc = i, 0.0
            while True:
                k = step(j)
                if k is None or k == i:
                    break
                acc += seg_u[k] if step is prv else seg_u[j]
                if acc > LOCAL_M or spacing(k) is None:
                    break
                turn += S[k]
                length += spacing(k)
                j = k
        return turn / max(length, 1e-9)
    fails_step, fails_adj, fails_sp = [], [], []
    max_ratio = max_adj = 0.0
    climb_idx = [i for i in range(m) if mask[i] and spacing(i) is not None]
    for i in climb_idx:
        lim = spacing(i) * abs(local_k(i)) * DEG + STEP_SLACK_DEG
        stp = abs(S[i]) * DEG
        max_ratio = max(max_ratio, stp / lim)
        if stp > lim:
            fails_step.append({"v": i, "osm_st_m": _osm_st(line, i), "step_deg": round(stp, 2), "limit_deg": round(lim, 2)})
        j = prv(i)
        if j is not None and mask[j]:
            d = abs(S[i] - S[j]) * DEG
            max_adj = max(max_adj, d)
            if d > ADJ_STEP_DEG:
                fails_adj.append({"v": i, "osm_st_m": _osm_st(line, i), "diff_deg": round(d, 2)})
        j = nxt(i)
        if j is not None and mask[j] and not (SPACING_RANGE_M[0] <= seg_u[i] <= SPACING_RANGE_M[1]):
            fails_sp.append({"v": i, "osm_st_m": _osm_st(line, i), "segment_m": round(seg_u[i], 3)})
    sps = [seg_u[i] for i in climb_idx if nxt(i) is not None and mask[nxt(i)]]
    res["b_curvature"] = {"pass": not (fails_step or fails_adj or fails_sp), "climb_osm_st_m": list(climb), "climb_by": how,
                          "points": len(climb_idx), "step_fails": len(fails_step), "adjacent_fails": len(fails_adj),
                          "spacing_fails": len(fails_sp), "max_step_ratio": round(max_ratio, 3), "max_adjacent_diff_deg": round(max_adj, 3),
                          "spacing_m": [round(min(sps), 3), round(max(sps), 3)] if sps else None,
                          "worst": (fails_step[:15] + fails_adj[:15] + fails_sp[:15])}
    # (c) no reversal, no self-intersection
    rev = [{"v": i, "osm_st_m": _osm_st(line, i), "step_deg": round(abs(S[i]) * DEG, 1)}
           for i in range(n) if abs(S[i]) * DEG >= REVERSAL_DEG]
    short = [{"v": i, "segment_m": round(seg[i], 5)} for i in range(n - 1) if seg[i] < MIN_SEG_M]
    crossings = _self_intersections(line)
    res["c_topology"] = {"pass": not (rev or short or crossings), "max_step_deg": round(max(abs(s) for s in S) * DEG, 2),
                         "reversals": rev[:20], "short_segments": short[:20], "self_intersections": crossings[:20]}
    # (d) closure
    if loop:
        exact = list(line.lonlat[0]) == list(line.lonlat[-1])
        seam = None
        seam_ok = True
        if line.closed:
            lim = spacing(0) * abs(local_k(0)) * DEG + STEP_SLACK_DEG
            adj = [abs(S[0] - S[m - 1]) * DEG, abs(S[1] - S[0]) * DEG]
            seam = {"step_deg": round(abs(S[0]) * DEG, 3), "limit_deg": round(lim, 3),
                    "adjacent_diff_deg": [round(x, 3) for x in adj]}
            if mask[0]:
                seam_ok = abs(S[0]) * DEG <= lim and max(adj) <= ADJ_STEP_DEG
        res["d_closure"] = {"pass": bool(exact and seam_ok), "closed_exactly": exact,
                            "seam_gap_m": math.dist(line.P[0], line.P[-1]), "seam": seam, "seam_on_climb": bool(mask[0])}
    else:
        res["d_closure"] = {"pass": True, "note": "point-to-point (loop false): no seam"}
    # (e) no facets off the climb
    facets = []
    worst_r, worst_step = None, 0.0
    for i in range(m):
        if mask[i]:
            continue
        sp = spacing(i)
        if sp is None:
            continue
        a = abs(S[i]) * DEG
        r = sp / abs(S[i]) if abs(S[i]) > 1e-12 else float("inf")
        worst_step = max(worst_step, a)
        if a > FACET_MIN_DEG and (worst_r is None or r < worst_r):
            worst_r = r
        if a > FACET_STEP_DEG or (a > FACET_MIN_DEG and r < FACET_R_MIN_M):
            facets.append({"v": i, "osm_st_m": _osm_st(line, i), "step_deg": round(a, 2), "radius_m": round(r, 2)})
    res["e_facets"] = {"pass": not facets, "points_off_climb": sum(1 for i in range(m) if not mask[i]),
                       "max_step_deg": round(worst_step, 2),
                       "tightest_radius_m": round(worst_r, 2) if worst_r is not None else None,
                       "facets": len(facets), "worst": sorted(facets, key=lambda f: -f["step_deg"])[:20]}
    res["pass"] = all(res[k]["pass"] for k in ("a_paint", "b_curvature", "c_topology", "d_closure", "e_facets"))
    return res


def _osm_st(line, i):
    src = line.props.get("osm_station_m")
    if src and len(src) == line.n:
        return round(src[i], 1)
    return round(line.st[i], 1)


def _self_intersections(line):
    P, n = line.P, line.n
    hits = []
    checked = set()
    for segs in line.cells.values():
        for x in range(len(segs)):
            for y in range(x + 1, len(segs)):
                i, j = min(segs[x], segs[y]), max(segs[x], segs[y])
                if (i, j) in checked or j - i <= 1:
                    continue
                if line.closed and i == 0 and j == n - 2:
                    continue
                checked.add((i, j))
                p1, p2, p3, p4 = P[i], P[i + 1], P[j], P[j + 1]
                d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
                if abs(d) < 1e-12:
                    continue
                t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
                u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
                if 0 < t < 1 and 0 < u < 1:
                    hits.append({"segments": [i, j], "osm_st_m": [_osm_st(line, i), _osm_st(line, j)]})
    return hits


def run(project_dir, centerline=None, traces_path=None, out=None) -> dict:
    project_dir = Path(project_dir).resolve()
    data = project_dir / "data"
    cfg = json.loads((project_dir / "track.config.json").read_text(encoding="utf-8"))
    cl = Path(centerline) if centerline else data / "centerline.geojson"
    tp = Path(traces_path) if traces_path else data / "aerial" / "paint_traces.json"
    line = Line.from_geojson(json.loads(cl.read_text(encoding="utf-8")))
    traces = json.loads(tp.read_text(encoding="utf-8"))
    climb = (cfg.get("hairpin_fit") or {}).get("climb_st_m")
    if not climb:
        raise SystemExit("[paint-gate] no hairpin_fit.climb_st_m in track.config.json")
    res = gate(line, traces, climb, bool(cfg.get("loop", True)))
    res = {"gate": "tools/verify_centreline_paint.py", "centerline": str(cl), "traces": str(tp), **res}
    outp = Path(out) if out else data / "aerial" / "paint_gate.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(res, indent=1), encoding="utf-8", newline="\n")
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_dir")
    ap.add_argument("--centerline")
    ap.add_argument("--traces")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        r = run(a.project_dir, a.centerline, a.traces, a.out)
    except (SystemExit, FileNotFoundError, KeyError) as e:
        print(f"[paint-gate] {e}", file=sys.stderr)
        return 2
    a_, b_, c_, d_ = r["a_paint"], r["b_curvature"], r["c_topology"], r["d_closure"]
    print(f"(a) paint      {'PASS' if a_['pass'] else 'FAIL'}: {a_['points']} medium+ points, {a_['over_limit']} over "
          f"{PAINT_MAX_M} m, max {a_['max_m']} m")
    print(f"(b) curvature  {'PASS' if b_['pass'] else 'FAIL'}: {b_['points']} climb points, step fails {b_['step_fails']}, "
          f"neighbour fails {b_['adjacent_fails']}, spacing fails {b_['spacing_fails']} (spacing {b_['spacing_m']} m)")
    print(f"(c) topology   {'PASS' if c_['pass'] else 'FAIL'}: max step {c_['max_step_deg']} deg, reversals {len(c_['reversals'])}, "
          f"self-intersections {len(c_['self_intersections'])}, short segments {len(c_['short_segments'])}")
    print(f"(d) closure    {'PASS' if d_['pass'] else 'FAIL'}: {d_}")
    e_ = r["e_facets"]
    print(f"(e) facets     {'PASS' if e_['pass'] else 'FAIL'}: {e_['points_off_climb']} points off the climb, max step "
          f"{e_['max_step_deg']} deg, tightest {e_['tightest_radius_m']} m, facets {e_['facets']}"
          + (f" (worst {e_['worst'][:3]})" if e_["facets"] else ""))
    print(f"[paint-gate] {'PASS' if r['pass'] else 'FAIL'}")
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
