"""Lane centres for road wear on streets: one line per lane, both directions (ledger 0084's owed "lanes" source).

    python tools/road_lanes.py <project-dir> [--out <file>]

Ledger 0099 (Kevin, 2026-11-22): "Full road wear at 10 cm" on Lake Murray. Road wear draws tyre wear along lines
(scripts/aerial/road_wear.py, tools/road_wear_blend.py). A circuit's line is its racing line; a street's lines are its
lanes. Ledger 0084: "Owed: a `lines` source "lanes" that builds one line per lane centre from the paint rule ..., both
directions, with the tyre profile on the lane's wheel paths". This tool writes those lines and nothing else: it reads
data files, writes one new data file, touches no mesh and draws nothing (the bake draws; HOW IT FEEDS THE BAKE below).

OPT-IN. track.config.json ``road_wear.lanes`` (no track names it yet). Absent, ``road_wear.lanes.enabled`` false or
``road_wear.enabled`` false: nothing is written, exit 0. Every key is optional; ``"lanes": {}`` runs with the defaults:

    "road_wear": {"lanes": {
        "connectors": true,        # every record of data/connectors.local.json (default); false = none; or a list of
                                   # connector names (a name matches with or without its "#n" suffix)
        "min_edge_lane_m": 2.9,    # NUMBERS
        "rubber": 1.0,             # NUMBERS
        "exclude": [{"from": 1130, "to": 1476, "why": "..."}],
                                   # source rows (inclusive) with no lanes; "road": "mainline" (default) or a connector name
        "split_zones": [{"kind": "...", "from": 1130, "to": 1476, "source": "..."}]
                                   # mainline rows whose lanes another reader supplies (SPLIT ZONES)
    }}

Lake Murray, for the session that turns it on: College Ave's mainline rows v1130-1476 are being rebuilt as two one-way
roads (ledger 0055 round 2), so its key starts as
``{"exclude": [{"from": 1130, "to": 1476, "why": "College Ave round 2: two one-way roads, their lanes come later"}]}``.
Any ``road_wear`` key also makes tools/road_wear_blend.py run where a chain calls it, and
tests/tools/test_lake_murray_0099.py pins that Lake Murray has none: both are that session's to move.

THE RULE: the lanes are the spaces between the painted lines, read from the same rule that paints them.
  * The mainline, data/centerline.local.json (the line the assembler painted: build_loop_blend persists it smoothed and
    narrowed before it paints), is painted by scripts-v021 geometry/ribbon.py ``lane_markings``: the double yellow on
    the centre, a dashed divider every ``lane_w`` 3.65 m out from it wherever the divider and half its line fit inside
    the edge line, the edge line ``edge_inset`` 0.55 m in from the paved edge, at most ``max_lanes_side`` dividers a
    side. The numbers are read off lane_markings' own signature, never restated here. Lane k of a side runs from
    (k - 1) lane_w to k lane_w; the last lane runs from the last divider that fits to the edge line. A width that does
    not divide by 3.65 m therefore leaves a narrower outer lane exactly where the paint leaves one (a 17 m road: lanes
    of 3.65 m and 3.65 m and an outer strip of 0.65 m a side). Per station, the lane's line is the middle of its space.
  * Connectors, data/connectors.local.json, as ribbon.connector_markings paints them, on the points the assembler
    paints them on (smoothed exactly as build_loop_blend smooths a connector, CONNECTOR_SMOOTH):
      - a plain connector: lane_markings with the centre yellow;
      - a phase-5 stub (its ``stub`` record): ``lanes_per_side`` lanes, dividers only between them, ending where its
        paint ends (ribbon's STUB_PAINT_STOP_M short of the barrier's road-side toe);
      - an authored piece (its ``paint`` record; Lake Murray's north network, the four pieces tools/expansion_pieces.py
        decorate painted off the intermediate data/expansion.north.json): the authored lines as painted. Per point, the
        yellow lines together are the median (a double yellow, a raised island's edge lines or a painted median's
        pairs), and the outermost yellow on a side is that side's inner bound (the line itself where a point has no
        yellow); the first solid white beyond it is the edge (bike, parking and buffer lanes lie outside it); the
        dashed whites between are the dividers.
  * Medians, data/median_bands.json: the mainline's island (``island_w_by_vertex``, centred on the line, as
    tools/author_median_blend.py stands it, full width with no nose taper) and the connector islands
    (``connector_islands``, matched to a connector by name; centre and width where the island's line crosses the
    connector's normal). A lane loses whatever an island covers (the wider remaining piece is kept). The paint rule
    knows nothing of islands (on College its first divider stands 0.15 m off a 7 m island's face), so this is the one
    place the lanes part from the paint: no lane runs over a median.
  * Which spaces carry wheel paths. Two tests, both per station:
      - the leftover the width leaves at the edge (the generic rule's last space, from the last divider that fits, or
        from the yellow when none does, to the edge line) is a lane only when it is ``min_edge_lane_m`` wide. Narrower,
        it is a bike lane, parking or a shoulder (0084 on the loop: p10 0.50 / median 1.10 / p90 3.45 m; "the data
        can't say which"). A 13 m street: one 3.65 m lane and a 2.30 m strip a side; 17 m: two lanes and 0.65 m;
        30 m: four lanes, the outer 3.50 m. An authored piece has no such leftover: its bike, parking and buffer lanes
        are painted outside its edge line;
      - every lane must still hold a car (``car_width_m``) once an island has taken its share: on College's 7 m island
        the first lane keeps 0.15 m and is gone, on Navajo's 1.5 m island it keeps 2.90 m and stays.
    The summary counts what each test left out, in km of lane.
  * Direction: right-hand traffic. Lanes right of the source line's vertex order travel with it ("forward"), lanes
    left of it against it ("reverse"); every lane's points run in its direction of travel. ``lane`` counts from the
    centre outward, 1 against the yellow / the median: the paint's own index, so it stays put when the outer lanes
    come and go. A lane the island or the width removes leaves a gap (the line is cut into runs); the lanes outside
    it are never renumbered.
  * Refused (exit 1): a mainline painted with no dividers (``route.lane_dividers`` false: a circuit, which takes
    ``road_wear.lines``) or with no centre yellow (``route.divided_double`` false: a one-way carriageway; its lanes are
    a later reader, as College's). A split zone whose kind has no reader is refused too.

OUTPUT data/road_wear.lanes.json (``--out`` elsewhere): {"frame" (the inputs' ENU: x = east, y = up, z = north),
"rule" (the paint rule's numbers as read), "min_edge_lane_m", "car_width_m", "rubber", "track_m", "excluded",
"split_zones", "sources", "summary" {lanes, km per direction, per group, what was left out}, "lanes": [{"id",
"road" ("mainline" or the connector's name), "group" (mainline | north | stub | connector | split:<kind>),
"direction" (forward | reverse), "lane", "rows" (the source rows it covers, in its order of travel), "closed",
"length_m", "points_xyz_m" (the lane centre, in its order of travel), "offset_m" (from the source line, + = left of
its vertex order), "width_m" (the lane's painted width there, less any island)}]}. Rewritten whole on every run.

HOW IT FEEDS THE BAKE. tools/road_wear_blend.py step 4 builds ``lines``: one dict per line, {"P" (N x 3: Blender
x = east, y = north, height), "I" (the rubber share per point), "closed", "layer_m", "layout", "source", ...}; step 5
darkens every atlas texel by ``road_wear.wear_at(X, Y, Z, line, w, reach)`` for each line: ``tyre_profile``, two tyre
tracks ``wear.track_m`` (1.60 m [measured]) apart, each a Gaussian of ``wear.spread_m``, laid round the line. Laid
round a lane's centre, those two tracks ARE the lane's wheel paths. ``bake_lines(doc, layer_m)`` below returns exactly
that dict per lane (the local (x, y_up, z_north) -> Blender (x, z, y) remap of tools/author_median_blend.py's B), so
the bake's wiring, when it is wanted, is: where ``spec.get("lanes")``, add
``road_lanes.bake_lines(json.loads((proj / "data" / "road_wear.lanes.json").read_text()), spec["layer_m"])`` to
``lines`` (instead of, or beside, the racing line; a lane's "I" is uniform ``rubber``: traffic, not cornering). The
circuit default ``wear.spread_m`` 0.70 [invented, road_wear's] merges the two tracks into one band; the lane look is
the bake spec's own knob (0084: 0.55 [invented, road_wear's first build] left "two tyre stripes with a lighter middle,
a lane's look"). Nothing in the bake is changed here.

SPLIT ZONES (the extension point; College Ave is the first user). A split zone hands mainline rows [from, to] to
another reader: those rows get no paint-rule lanes, and the reader registered for the zone's ``kind`` in
``SPLIT_ZONE_READERS`` supplies their lanes. A reader is ``reader(proj: Path, zone: dict, rule: dict) -> list[dict]``,
each dict a lane in the output's schema (``id``, ``road`` "mainline", ``direction``, ``lane`` >= 1, ``rows`` inside
[from, to], ``closed`` false, ``points_xyz_m``, ``offset_m``, ``width_m``, each with one entry per row); the tool sets
``group`` to "split:<kind>", recomputes ``length_m``, and refuses (exit 1) a lane that breaks the schema or leaves the
zone. ``rule`` is ``paint_rule()``. ``side_bounds(inner, outer, rule, max_k)`` and ``lanes_between(bounds, sign,
...)`` are the paint rule's division, reusable from any inner bound. College's reader, when the two roads are built:
``source/college_r2/college_split.data.json`` holds per station the frame (x, z, nx, nz, half_w by row v) and both
roads' edges (``edges`` sb_west_m, sb_east_m, nb_west_m, nb_east_m); on each one-way road the lanes count from the
median-side yellow outward (the paint section of college_middle_blend.py: the yellow ``edge_inset`` inside the median
edge, dividers every ``lane_w`` counted from the yellow, the white ``edge_inset`` inside the outer edge, the dividers
clipped as lane_markings clips them), so each road is ``side_bounds`` from its yellow, its direction the one-way
road's own (the mainline runs north on College, "+ = left of the vertex order (west on College northbound)" in
route.median_registration's doc, so the southbound road is "reverse" and the northbound "forward"). The reader is
written in this module and registered here, ``SPLIT_ZONE_READERS["college_split"] = read_college_split`` (a kind is
looked up, never imported from the config), and Lake Murray's key moves the rows from ``exclude`` to
``split_zones``: [{"kind": "college_split", "from": 1130, "to": 1476, "source":
"source/college_r2/college_split.data.json"}]. Until then the rows stay excluded. Not implemented here.

NUMBERS. From the paint rule (read, not restated): lane_w 3.65, edge_inset 0.55, line_w 0.12, max_lanes_side 6, and
ribbon's STUB_PAINT_STOP_M / STUB_BARRIER_HALF_BASE_M. From the assembler: CONNECTOR_SMOOTH (sigma 1.5 points, one
pass, height sigma 1.0: build_loop_blend's own call, pinned by a test). Measured, read from
scripts/aerial/road_wear.DEFAULTS: track_m 1.60 (a car's track, 1.5-1.7 m) and car_width_m 1.90 (twice its margin_m,
"half a 1.9 m car"). Invented:
  * min_edge_lane_m 2.9 [invented]: tools/expansion_pieces.py's LANE_MIN_M (itself [invented]), the narrowest lane the
    north network's authored paint divides a carriageway into, so the mainline's edge leftover and the north's lanes
    answer "is this a lane" with one number. Checked, not set, against OSM (2026-11-23, Lake Murray's mainline with
    College excluded, the nearest lane-tagged way within 15 m [invented], a one-way way doubled as scripts-v021
    gps/road_widths.py doubles it): the lanes per station agree with OSM's ``lanes`` at 2,952 of 3,411 tagged
    stations (86.5 %) with 2.9 m, at 2,682 (78.6 %) with the edge leftover kept whenever a car fits;
  * rubber 1.0 [invented]: every lane carries the bake's own ``wear.amplitude`` (itself [invented]) at every point;
    uniform because 0084 asks traffic's rubber, not cornering's; how gentle is the amplitude's, Kevin's eye.
"""
from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
V021 = AIROSO / "tracks" / "san-diego-lake-murray" / "scripts-v021"
OUT_NAME = "road_wear.lanes.json"
# build_loop_blend.py (scripts-v021/blender): ``cpts = smoothmod.smooth_centerline(cpts, sigma_pts=1.5, passes=1,
# sigma_y_pts=1.0)``: every connector is smoothed this way before it is painted (tests pin the call)
CONNECTOR_SMOOTH = {"sigma_pts": 1.5, "passes": 1, "sigma_y_pts": 1.0}
DEFAULTS = {
    "connectors": True,
    "min_edge_lane_m": 2.9,     # [invented] tools/expansion_pieces.py LANE_MIN_M (docstring NUMBERS)
    "rubber": 1.0,              # [invented] the share of the bake's wear.amplitude every lane carries (NUMBERS)
    "exclude": [],
    "split_zones": [],
}
EPS = 1e-9


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RB = _load("_road_lanes_v021_ribbon", V021 / "geometry" / "ribbon.py")
SM = _load("_road_lanes_v021_smooth", V021 / "geometry" / "smooth.py")
RW = _load("_road_lanes_road_wear", AIROSO / "scripts" / "aerial" / "road_wear.py")


def car_width_m() -> float:
    """A car's width [measured]: twice scripts/aerial/road_wear.DEFAULTS wear.margin_m ("half a 1.9 m car")."""
    return 2.0 * float(RW.DEFAULTS["wear"]["margin_m"])


# --- the paint rule ---------------------------------------------------------------------------------------------------
def paint_rule() -> dict:
    """lane_markings' own numbers, read off its signature (the rule is never restated here)."""
    sig = inspect.signature(RB.lane_markings)
    return {k: float(sig.parameters[k].default) if k != "max_lanes_side" else int(sig.parameters[k].default)
            for k in ("lane_w", "edge_inset", "line_w", "max_lanes_side")}


def side_bounds(inner: float, outer: float, rule: dict, max_k: int | None = None) -> list[float]:
    """One side's lane bounds as distances from the centre, inner to outer: ``inner`` (the yellow), a divider every
    lane_w out from ``inner`` wherever it and half its line fit inside ``outer`` (the edge line) — lane_markings'
    clip, ``abs(o) + line_w / 2 > half - edge_inset`` skips it, the same expression with no tolerance, so a knife-edge
    width falls the way the paint falls — at most ``max_k`` of them, then ``outer``. [] when there is no room between
    the yellow and the edge line."""
    if outer <= inner + EPS:
        return []
    kmax = rule["max_lanes_side"] if max_k is None else max_k
    out = [inner]
    for k in range(1, kmax + 1):
        o = inner + k * rule["lane_w"]
        if abs(o) + rule["line_w"] / 2 > outer:
            break
        out.append(o)
    out.append(outer)
    return out


def lanes_between(bounds: list[float], sign: int) -> list[tuple[int, float, float]]:
    """[(lane, lo, hi)] in signed offsets (+ = left of the line's vertex order) from one side's bounds (distances
    from the centre, inner to outer); ``sign`` +1 = the left side, -1 = the right. lane 1 = against the centre."""
    out = []
    for k in range(1, len(bounds)):
        a, b = sign * bounds[k - 1], sign * bounds[k]
        out.append((k, min(a, b), max(a, b)))
    return out


def rule_lanes(half: float, rule: dict, max_k: int | None = None) -> list[tuple[int, int, float, float, bool]]:
    """[(side, lane, lo, hi, edge)] at a station of half width ``half`` painted by lane_markings (centre yellow on);
    ``edge`` marks the space between the last divider (or the yellow) and the edge line: the leftover the width
    leaves, a lane only when it is min_edge_lane_m wide (module docstring)."""
    outer = half - rule["edge_inset"]
    out = []
    for side in (1, -1):
        sp = lanes_between(side_bounds(0.0, outer, rule, max_k), side)
        out += [(side, k, lo, hi, k == len(sp)) for k, lo, hi in sp]
    return out


def authored_lanes(lines: list[tuple[float, str, bool]]) -> list[tuple[int, int, float, float, bool]]:
    """[(side, lane, lo, hi, False)] at one point of an authored piece from its painted lines [(offset, colour, dashed)]:
    the yellows are the median, the first solid white beyond the outermost yellow on a side is that side's edge, the
    dashed whites between are the dividers (module docstring). The bike, parking and buffer lanes are painted outside
    the edge, so every space inside is a travel lane: none is an edge leftover."""
    ys = [o for o, c, _d in lines if c == "yellow"]
    hi_y, lo_y = (max(ys), min(ys)) if ys else (0.0, 0.0)
    out = []
    for side, inner in ((1, hi_y), (-1, lo_y)):
        whites = sorted(((o - inner) * side, d) for o, c, d in lines if c != "yellow" and (o - inner) * side > EPS)
        edge = next((u for u, d in whites if not d), None)
        if edge is None:
            continue
        b = [0.0] + [u for u, d in whites if d and u < edge - EPS] + [edge]
        out += [(side, k, inner + lo, inner + hi, False) for k, lo, hi in lanes_between(b, side)]
    return out


def clip_island(lo: float, hi: float, island: tuple[float, float] | None) -> tuple[float, float]:
    """The lane [lo, hi] less the island [a, b] (signed offsets); the wider remaining piece. (lo, lo) when none."""
    if island is None:
        return lo, hi
    a, b = island
    if b <= lo + EPS or a >= hi - EPS:
        return lo, hi
    left, right = (lo, min(hi, a)), (max(lo, b), hi)
    best = max((p for p in (left, right) if p[1] - p[0] > EPS), key=lambda p: p[1] - p[0], default=None)
    return best if best is not None else (lo, lo)


# --- geometry ---------------------------------------------------------------------------------------------------------
def is_closed(pts) -> bool:
    """lane_markings' own test: the first and last points coincide in plan."""
    return abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6


def frames(pts, closed: bool) -> list[tuple[float, float, float, float, float]]:
    """(x, y, z, nx, nz) per station: the paint's own frame (ribbon._horiz_tangent, left normal (-tz, tx)). A closed
    line drops its repeated last point, as lane_markings does."""
    m = len(pts) - 1 if closed else len(pts)
    out = []
    for i in range(m):
        tx, tz = RB._horiz_tangent(pts, i, closed)
        out.append((pts[i][0], pts[i][1], pts[i][2], -tz, tx))
    return out


def island_crossings(fr, island_pts, island_w) -> list[tuple[float, float] | None]:
    """Per station: the island's lateral extent (signed offsets) where the island's line (its segments with a width)
    crosses the station's normal, or None. Of several crossings the one nearest the station is taken."""
    out = []
    segs = [(island_pts[j], island_pts[j + 1], island_w[j], island_w[j + 1]) for j in range(len(island_pts) - 1)
            if island_w[j] > 0 or island_w[j + 1] > 0]
    for x, _y, z, nx, nz in fr:
        best = None
        for p, q, wp, wq in segs:
            # solve (x, z) + u n = p + t (q - p), t in [0, 1]
            dx, dz = q[0] - p[0], q[2] - p[2]
            den = nx * (-dz) - nz * (-dx)
            if abs(den) < 1e-12:
                continue
            rx, rz = p[0] - x, p[2] - z
            u = (rx * (-dz) - rz * (-dx)) / den
            t = (nx * rz - nz * rx) / den
            if t < -EPS or t > 1 + EPS:
                continue
            w = wp + (wq - wp) * min(1.0, max(0.0, t))
            if w <= 0:
                continue
            if best is None or abs(u) < abs(best[0]):
                best = (u, w)
        out.append(None if best is None else (best[0] - best[1] / 2.0, best[0] + best[1] / 2.0))
    return out


def stub_cut(cpts, cw, stub: dict):
    """connector_markings' stub truncation: the polyline cut where its paint ends (ribbon's own constants)."""
    keep_back = float(stub.get("tail_m") or 0.0) + RB.STUB_BARRIER_HALF_BASE_M + RB.STUB_PAINT_STOP_M
    arc = [0.0]
    for i in range(1, len(cpts)):
        arc.append(arc[-1] + math.hypot(cpts[i][0] - cpts[i - 1][0], cpts[i][2] - cpts[i - 1][2]))
    stop = arc[-1] - keep_back
    pts, ws = [], []
    for i in range(len(cpts)):
        if arc[i] <= stop + 1e-9:
            pts.append(tuple(cpts[i]))
            ws.append(cw[i])
            continue
        if i > 0 and arc[i - 1] < stop:
            f = (stop - arc[i - 1]) / max(1e-12, arc[i] - arc[i - 1])
            pts.append(tuple(cpts[i - 1][k] + (cpts[i][k] - cpts[i - 1][k]) * f for k in range(3)))
            ws.append(cw[i - 1] + (cw[i] - cw[i - 1]) * f)
        break
    return pts, ws


# --- one road -----------------------------------------------------------------------------------------------------------
def road_lanes(name: str, group: str, fr, closed: bool, per_station, islands, excluded, spec: dict,
               stats: dict) -> list[dict]:
    """Lane runs of one road. ``per_station[i]`` = [(side, lane, lo, hi, edge)] (the paint's spaces), ``islands[i]``
    the island's extent or None, ``excluded[i]`` True for a row with no lanes. A space is a lane where it is at least
    min_edge_lane_m wide if it is the edge leftover, and where a car still fits once the island has its share.
    Returns the output's lane records."""
    m = len(fr)
    ds = station_spacing(fr, closed)
    min_edge, car = float(spec["min_edge_lane_m"]), car_width_m()
    keyed: dict[tuple[int, int], list] = {}
    for i in range(m):
        if excluded[i]:
            continue
        for side, k, lo, hi, edge in per_station[i]:
            if edge and hi - lo < min_edge - 1e-6:
                stats["edge_strip_km"] += ds[i] / 1000.0
                continue
            lo2, hi2 = clip_island(lo, hi, islands[i])
            if (lo2, hi2) != (lo, hi):
                stats["island_trimmed_km"] += ds[i] / 1000.0
            if hi2 - lo2 < car - 1e-6:
                stats["no_car_fits_km"] += ds[i] / 1000.0
                continue
            keyed.setdefault((side, k), [None] * m)[i] = (lo2, hi2)
    out = []
    for (side, k), at in sorted(keyed.items(), key=lambda kv: (-kv[0][0], kv[0][1])):
        on = [a is not None for a in at]
        runs = []
        if all(on) and closed:
            runs.append((list(range(m)), True))
        else:
            i = 0
            starts = []
            while i < m:
                if on[i] and (i == 0 or not on[i - 1]):
                    starts.append(i)
                i += 1
            for s in starts:
                j = s
                while j + 1 < m and on[j + 1]:
                    j += 1
                runs.append((list(range(s, j + 1)), False))
            if closed and len(runs) > 1 and on[0] and on[-1]:     # the run across the loop's seam is one run
                last = runs.pop()
                first = runs.pop(0)
                runs.insert(0, (last[0] + first[0], False))
        direction = "reverse" if side > 0 else "forward"
        for r, (rows, rclosed) in enumerate(runs):
            if len(rows) < 2:
                stats["single_station_runs"] += 1
                continue
            if direction == "reverse":
                rows = rows[::-1]
            pts, offs, wids = [], [], []
            for i in rows:
                x, y, z, nx, nz = fr[i]
                lo, hi = at[i]
                o = (lo + hi) / 2.0
                pts.append([round(x + nx * o, 3), round(y, 3), round(z + nz * o, 3)])
                offs.append(round(o, 3))
                wids.append(round(hi - lo, 3))
            out.append({"id": f"{name}/{direction}/{k}/{r}", "road": name, "group": group, "direction": direction,
                        "lane": k, "rows": rows, "closed": rclosed, "length_m": round(polyline_length(pts, rclosed), 1),
                        "points_xyz_m": pts, "offset_m": offs, "width_m": wids})
    return out


def station_spacing(fr, closed: bool) -> list[float]:
    """The length of road each station stands for: half the segment before it plus half the one after."""
    m = len(fr)
    seg = [math.hypot(fr[(i + 1) % m][0] - fr[i][0], fr[(i + 1) % m][2] - fr[i][2]) for i in range(m)]
    if not closed:
        seg[-1] = 0.0
    return [0.5 * (seg[i] + (seg[i - 1] if (i > 0 or closed) else 0.0)) for i in range(m)]


def polyline_length(pts, closed: bool = False) -> float:
    L = sum(math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]) for i in range(1, len(pts)))
    if closed and len(pts) > 2:
        L += math.hypot(pts[0][0] - pts[-1][0], pts[0][2] - pts[-1][2])
    return L


def _rows_excluded(n: int, ranges: list[tuple[int, int]]) -> list[bool]:
    return [any(a <= i <= b for a, b in ranges) for i in range(n)]


# --- the spec ---------------------------------------------------------------------------------------------------------
def spec_from_config(cfg: dict) -> dict | None:
    """The merged road_wear.lanes spec, or None: no road_wear.lanes key (every track today), or either switched off."""
    rw = cfg.get("road_wear")
    if not isinstance(rw, dict) or not rw.get("enabled", True):
        return None
    ln = rw.get("lanes")
    if ln is None or ln is False:
        return None
    ln = {} if ln is True else dict(ln)
    if not ln.get("enabled", True):
        return None
    out = {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULTS.items()}
    out.update({k: v for k, v in ln.items() if not str(k).startswith("_") and k != "enabled"})
    unknown = sorted(set(out) - set(DEFAULTS))
    if unknown:
        raise SystemExit(f"[road_lanes] FATAL: road_wear.lanes.{unknown[0]}: unknown key (known: {sorted(DEFAULTS)})")
    return out


# The extension point (module docstring, SPLIT ZONES): kind -> reader(proj, zone, rule) -> [lane records]
SPLIT_ZONE_READERS: dict = {}
LANE_KEYS = ("id", "road", "direction", "lane", "rows", "closed", "points_xyz_m", "offset_m", "width_m")


def _check_zone_lane(ln: dict, zone: dict) -> str | None:
    missing = [k for k in LANE_KEYS if k not in ln]
    if missing:
        return f"missing {missing}"
    if ln["road"] != "mainline" or ln["direction"] not in ("forward", "reverse") or int(ln["lane"]) < 1 or ln["closed"]:
        return "road / direction / lane / closed"
    n = len(ln["rows"])
    if n < 2 or any(len(ln[k]) != n for k in ("points_xyz_m", "offset_m", "width_m")):
        return "one entry per row, at least two rows"
    if any(not (int(zone["from"]) <= int(r) <= int(zone["to"])) for r in ln["rows"]):
        return f"a row outside {zone['from']}-{zone['to']}"
    return None


# --- the build --------------------------------------------------------------------------------------------------------
def build(proj: Path, cfg: dict, spec: dict) -> dict:
    data = proj / "data"
    rule = paint_rule()
    route = cfg.get("route") or {}
    if route.get("lane_dividers", True) is False:
        raise SystemExit("[road_lanes] FATAL: route.lane_dividers false: the mainline paints no lanes (a circuit's wear "
                         "is road_wear.lines)")
    if route.get("divided_double", True) is False:
        raise SystemExit("[road_lanes] FATAL: route.divided_double false: a one-way mainline has no centre yellow; its "
                         "lanes are not built yet (a split-zone reader, as College's)")
    stats = {"edge_strip_km": 0.0, "island_trimmed_km": 0.0, "no_car_fits_km": 0.0, "single_station_runs": 0}
    bands_p = data / "median_bands.json"
    bands = json.loads(bands_p.read_text(encoding="utf-8")) if bands_p.exists() else {}
    excl_by_road: dict[str, list[tuple[int, int]]] = {}
    for e in spec["exclude"]:
        excl_by_road.setdefault(str(e.get("road", "mainline")), []).append((int(e["from"]), int(e["to"])))
    zones = list(spec["split_zones"])
    for z in zones:
        if z.get("kind") not in SPLIT_ZONE_READERS:
            raise SystemExit(f"[road_lanes] FATAL: split zone {z.get('kind')!r} (rows {z.get('from')}-{z.get('to')}) has "
                             f"no reader (SPLIT_ZONE_READERS: {sorted(SPLIT_ZONE_READERS)}); exclude the rows until it does")
        excl_by_road.setdefault("mainline", []).append((int(z["from"]), int(z["to"])))
    lanes: list[dict] = []
    sources = {}

    # the mainline
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in local["points_xyz_m"]]
    widths = [float(w) for w in local["widths_m"]]
    closed = is_closed(pts)
    fr = frames(pts, closed)
    iw = bands.get("island_w_by_vertex") or [0.0] * len(pts)
    if len(iw) != len(pts):
        raise SystemExit(f"[road_lanes] FATAL: median_bands island_w_by_vertex has {len(iw)} rows, the centreline {len(pts)}")
    isl = [(-iw[i] / 2.0, iw[i] / 2.0) if iw[i] > 0 else None for i in range(len(fr))]
    per = [rule_lanes(widths[i] / 2.0, rule) for i in range(len(fr))]
    ex = _rows_excluded(len(fr), excl_by_road.get("mainline", []))
    lanes += road_lanes("mainline", "mainline", fr, closed, per, isl, ex, spec, stats)
    sources["mainline"] = {"file": "data/centerline.local.json", "rows": len(fr), "closed": closed,
                           "excluded_rows": sum(ex), "island_rows": sum(1 for v in isl if v)}

    # the split zones' readers
    for z in zones:
        got = SPLIT_ZONE_READERS[z["kind"]](proj, dict(z), dict(rule))
        for ln in got:
            err = _check_zone_lane(ln, z)
            if err:
                raise SystemExit(f"[road_lanes] FATAL: split zone {z['kind']!r} lane {ln.get('id')!r}: {err}")
            ln = dict(ln, group=f"split:{z['kind']}", length_m=round(polyline_length(ln["points_xyz_m"]), 1))
            lanes.append(ln)

    # the connectors
    take = spec["connectors"]
    cp = data / "connectors.local.json"
    conns = json.loads(cp.read_text(encoding="utf-8")).get("connectors", []) if (take and cp.exists()) else []
    islands_by_name = {}
    for ci in bands.get("connector_islands", []) or []:
        islands_by_name.setdefault(str(ci["name"]).split("#")[0], []).append(ci)
    sources["connectors"] = []
    for c in conns:
        name = c["name"]
        base = name.split("#")[0]
        if isinstance(take, list) and name not in take and base not in take:
            continue
        cpts = [tuple(p) for p in c["points_xyz_m"]]
        if len(cpts) < 2:
            continue
        cpts = SM.smooth_centerline(cpts, **CONNECTOR_SMOOTH)
        cw = [float(w) for w in c["widths_m"]]
        if c.get("paint"):
            group = "north" if (c.get("expansion") or {}).get("route") == "north" else "authored"
            cl = False                                   # paint_markings: an open frame always
            fr = frames(cpts, cl)
            lines = c["paint"].get("lines") or []
            per = []
            for i in range(len(fr)):
                here = [(float(ln["off"][i]), ln.get("color", "white"), bool(ln.get("dash")))
                        for ln in lines if i < len(ln["off"]) and ln["off"][i] is not None]
                per.append(authored_lanes(here))
        elif c.get("stub"):
            group = "stub"
            cpts, cw = stub_cut(cpts, cw, c["stub"])
            if len(cpts) < 2:
                continue
            cl = is_closed(cpts)
            fr = frames(cpts, cl)
            max_k = max(1, int(c["stub"].get("lanes_per_side") or 1)) - 1
            per = [rule_lanes(cw[i] / 2.0, rule, max_k) for i in range(len(fr))]
        else:
            group = "connector"
            cl = is_closed(cpts)
            fr = frames(cpts, cl)
            per = [rule_lanes(cw[i] / 2.0, rule) for i in range(len(fr))]
        isl = [None] * len(fr)
        for ci in islands_by_name.get(base, []):
            got = island_crossings(fr, ci["points_xyz_m"], ci["island_w_by_point"])
            isl = [a if a is not None else b for a, b in zip(isl, got)]
        ex = _rows_excluded(len(fr), excl_by_road.get(name, []) + excl_by_road.get(base, []))
        got = road_lanes(name, group, fr, cl, per, isl, ex, spec, stats)
        lanes += got
        sources["connectors"].append({"name": name, "group": group, "rows": len(fr), "lanes": len(got),
                                      "island_rows": sum(1 for v in isl if v), "excluded_rows": sum(ex)})

    km = {"forward": 0.0, "reverse": 0.0}
    by_group: dict[str, dict] = {}
    for ln in lanes:
        km[ln["direction"]] += ln["length_m"] / 1000.0
        g = by_group.setdefault(ln["group"], {"lanes": 0, "km_forward": 0.0, "km_reverse": 0.0})
        g["lanes"] += 1
        g["km_" + ln["direction"]] += ln["length_m"] / 1000.0
    for g in by_group.values():
        g["km_forward"] = round(g["km_forward"], 2)
        g["km_reverse"] = round(g["km_reverse"], 2)
    for k in ("edge_strip_km", "island_trimmed_km", "no_car_fits_km"):
        stats[k] = round(stats[k], 2)
    stats["distinct_lanes"] = len({(ln["road"], ln["direction"], ln["lane"]) for ln in lanes})
    return {
        "what": "lane centres for road wear on streets (ledger 0084's 'lanes' source): one line per lane, both "
                "directions, the lanes the paint rule paints; tools/road_lanes.py",
        "ledger": ["0084", "0099"],
        "frame": "ENU local meters (X=east, Y=up, Z=north)",
        "rule": dict(rule, source="scripts-v021 geometry/ribbon.py lane_markings / connector_markings"),
        "min_edge_lane_m": float(spec["min_edge_lane_m"]), "car_width_m": car_width_m(), "rubber": float(spec["rubber"]),
        "track_m": float(RW.DEFAULTS["wear"]["track_m"]),
        "excluded": spec["exclude"], "split_zones": zones, "sources": sources,
        "summary": {"lanes": len(lanes), "km": {k: round(v, 2) for k, v in km.items()}, "by_group": by_group, **stats},
        "lanes": lanes,
    }


def bake_lines(doc: dict, layer_m: float = 10.0) -> list[dict]:
    """The output as tools/road_wear_blend.py's ``lines`` (HOW IT FEEDS THE BAKE): per lane {"P" (N x 3, Blender
    x = east, y = north, height), "I" (uniform rubber), "closed", "layer_m", "layout" "lanes", "source" the lane id,
    "lap_m"}, ready for scripts/aerial/road_wear.wear_at."""
    import numpy as np
    out = []
    for ln in doc["lanes"]:
        P = np.array([[x, z, y] for x, y, z in ln["points_xyz_m"]], dtype=np.float64)
        out.append({"P": P, "I": np.full(len(P), float(doc["rubber"])), "closed": bool(ln["closed"]),
                    "layer_m": float(layer_m), "layout": "lanes", "source": ln["id"], "lap_m": ln["length_m"]})
    return out


def run(proj: Path, out: Path | None = None) -> dict | None:
    proj = Path(proj)
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    out = Path(out) if out else proj / "data" / OUT_NAME
    spec = spec_from_config(cfg)
    if spec is None:
        print("[road_lanes] no road_wear.lanes key in track.config.json: nothing to do, nothing written")
        if out.exists():
            print(f"[road_lanes] note: {out.name} is left from an earlier run; nothing reads it without the key")
        return None
    doc = build(proj, cfg, spec)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8", newline="\n")
    s = doc["summary"]
    print(f"[road_lanes] {s['lanes']} lane lines ({s['distinct_lanes']} lanes by road, direction and index): "
          f"{s['km']['forward']} km forward, {s['km']['reverse']} km reverse; left out: {s['edge_strip_km']} km of edge "
          f"strip under {doc['min_edge_lane_m']} m, {s['no_car_fits_km']} km where no {doc['car_width_m']} m car fits; "
          f"{s['island_trimmed_km']} km trimmed by an island -> {out}")
    for g, v in sorted(s["by_group"].items()):
        print(f"[road_lanes]   {g}: {v['lanes']} lanes, {v['km_forward']} km forward, {v['km_reverse']} km reverse")
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project")
    ap.add_argument("--out", default=None, help=f"write here instead of <project>/data/{OUT_NAME}")
    a = ap.parse_args(argv)
    run(Path(a.project).resolve(), Path(a.out) if a.out else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
