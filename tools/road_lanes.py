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
        "split_zones": [{"kind": "...", "from": 1130, "to": 1476, "source": "..."}],
                                   # mainline rows whose lanes another reader supplies (SPLIT ZONES)
        "ends": {"fade_m": 8.0},   # opt-in, no default (LANE ENDS): a lane's wear at its two ends
        "dash_gap_rows": 8         # opt-in, no default (DASH GAPS): a dashed divider's short gaps read as painted
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
"source/college_r2/college_split.data.json"}]. IMPLEMENTED (ledger 0099 round 3, item 3): ``read_college_split`` below,
which mirrors the paint section expression for expression (``college_split_bounds``) and adds the two forks, where the
divider base runs from the old line's centre to the yellow at the point where the roads part.

LANE ENDS (opt-in ``ends``; ledger 0099 round 3, item 3, Lake Murray 0.20.7). A lane record is a run of rows, and a
run stops for two different reasons. Measured on Lake Murray (221 lanes, 219 of them open):
  * the lane goes on in another record. College's split zone hands rows 1130-1476 to its reader, so the mainline's
    lanes stop at row 1129 and the reader's start at row 1130: 12 ends 2.98-3.11 m apart, 0.00-0.08 m to the side,
    0.0-1.6 degrees apart in direction. Two authored lanes drop out for two stations and resume (9.0 m, 0.11 and
    0.23 m to the side). Every other pair of ends is a lane and its neighbour, 3.2 m or more to the side;
  * the lane ends: at a junction pad's edge, at the mouth where a side road meets a through road, at a stub's
    barrier, or where the road narrows and the paint gives the lane up.
  Without the key a lane is uniform to its last point, and the bake rounds every open end (road_wear.wear_at: a point
  past the end is as far from the line as from its end point), which draws the two wheel paths round the end as a
  horseshoe and leaves a 3 m hole in College's lanes at both ends of the split. With it:
  * WELDED: a lane's last point (its tail) is welded to another lane's first point (a head) when the head lies no more
    than ``join_gap_m`` ahead of the tail along its direction, no more than ``join_side_m`` to the side, the two
    directions within ``join_angle_deg`` and the heights within 3 m. The tail's record gains ``"bridge_to_xyz_m"``,
    the head's first point, and ``"joined"`` names the other lane at each welded end. The nearest head wins and a
    head is welded once;
  * FADED: every other open end. ``"rubber_share"`` (one number per point, 0..1) rises from 0 at the end to 1 over
    ``fade_m`` of lane, smoothly (smoothstep); a lane shorter than twice that never reaches 1 (a short stub carries
    less: few cars use it). A welded end and a closed lane keep 1.
  ``bake_lines`` hands the share to the bake as the line's rubber along its length, the bridge as one more point, and
  asks for square ends (``"butt_ends"``), so two welded lanes meet in a plane and nothing is drawn past an end.
  WHAT THIS DOES AT A JUNCTION, and what it does not (measured, 2026-11-23): no lane enters a junction pad (the pieces
  stop at its edge) and a side road's lanes stop at the through road's edge, so with the fade a pad and a side road's
  mouth carry the tone only (0084: "Junction boxes and pads get the tone only"), reached over ``fade_m``. A through
  road's own lanes run on through the box, as the wheel paths of a real arterial do past a side street. Lanes of two
  different roads cross at two places only, 6.4 and 3.5 m long (a connector's last points inside the mainline's
  outer lane). The one long overlap was a mistake of the config, not a junction: ``college_nb``, the Speedway lap's
  line along College's northbound road, read as a two-way road on top of the split zone's own lanes (1.0 km, twice);
  Lake Murray's key excludes it.
  Numbers, all [invented]: fade_m 8.0 on Lake Murray (two car lengths: where a driver leaves the lane's wheel paths
  for the turn; and over twice the wear band's 3.0 m reach, so the end reads as a fade, not a blunt stop);
  join_gap_m 10.0 (three stations of 3 m and a little: a lane that drops out for two stations is the same lane);
  join_side_m 0.5 and join_angle_deg 15 (between the measured welds, 0.23 m and 3 degrees at most, and the nearest
  thing that is not one, a neighbouring lane 3.2 m to the side).

DASH GAPS (opt-in ``dash_gap_rows``; ledger 0099 round 3, item 3, found by the first bake's deepest rubber). An
authored piece paints a dashed divider only where the half carriageway holds two lanes of tools/expansion_pieces.py's
LANE_MIN_M. On Princess View the space between the yellow and the edge line is about 5.8-5.9 m, at that limit, so the
divider flickers off for a row or a few as the median's line wanders by a few centimetres: offsets either side of a gap
within 0.0-0.9 m of each other [measured]. Read as painted, lane 1 takes the whole half for those rows (5.7-5.9 m wide,
its centre 1.8 m further out) and lane 2 stops and starts: a jog in lane 1's wheel paths, and where LANE ENDS welded lane
2 across the gap, both lanes' wheel paths over the same space (the bake's deepest rubber, 38.8 %, at Princess View row
207 and Jackson north row 617). With the key, a dashed white line's gap of at most ``dash_gap_rows`` rows, painted on
both sides in the same line record, is read as painted there, its offset drawn straight between the two painted rows.
A longer gap is the divider ending and is read as it is. Solid lines and yellows are never filled. Measured on Lake
Murray's pieces (2026-11-23): 21 dashed-divider gaps bounded on both sides; 11 of them 1-8 rows (3-24 m), the rest 13
rows (39 m) and longer; none at a side street's mouth (the nearest 15-307 m away). 8 [invented]: the measured break, and
two cycles of a 3 m dash and 9 m gap, a gap a driver still reads as one divider. The doc records what was filled.

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
import ast
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
    # "ends" (opt-in, no default here so a spec without it is unchanged): LANE ENDS in the docstring
    # "dash_gap_rows" (opt-in, no default here): DASH GAPS in the docstring
}
ENDS_DEFAULTS = {
    "fade_m": 8.0,              # [invented] LANE ENDS
    "join_gap_m": 10.0,         # [invented]
    "join_side_m": 0.5,         # [invented]
    "join_angle_deg": 15.0,     # [invented]
}
JOIN_HEIGHT_M = 3.0             # [invented] two ends more than this apart in height are on different decks
EPS = 1e-9


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RB = _load("_road_lanes_v021_ribbon", V021 / "geometry" / "ribbon.py")
SM = _load("_road_lanes_v021_smooth", V021 / "geometry" / "smooth.py")
RW_PATH = AIROSO / "scripts" / "aerial" / "road_wear.py"


class _RoadWear:
    """scripts/aerial/road_wear.py, loaded when something of it is first asked for. That module needs numpy; this
    tool needs only two of its DEFAULTS (``rw_defaults`` reads them off its source), so it runs on an interpreter
    without numpy (the PC's, which runs the chain's plain python steps) and loads the module only for whoever calls
    into it (the bake inside Blender, the tests' ``rl.RW.wear_at``)."""
    _mod = None

    def __getattr__(self, name):
        if _RoadWear._mod is None:
            _RoadWear._mod = _load("_road_lanes_road_wear", RW_PATH)
        return getattr(_RoadWear._mod, name)


RW = _RoadWear()


def rw_defaults() -> dict:
    """scripts/aerial/road_wear.DEFAULTS, read off the module's source (a literal dict): the same numbers, no import."""
    tree = ast.parse(RW_PATH.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "DEFAULTS" for t in n.targets))
    return ast.literal_eval(node.value)


def car_width_m() -> float:
    """A car's width [measured]: twice scripts/aerial/road_wear.DEFAULTS wear.margin_m ("half a 1.9 m car")."""
    return 2.0 * float(rw_defaults()["wear"]["margin_m"])


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


def fill_dash_gaps(lines: list[dict], max_rows: int) -> tuple[list[dict], list[dict]]:
    """DASH GAPS (module docstring): the authored paint lines with every dashed white line's gap of at most ``max_rows``
    rows, painted on both sides in the same line, filled straight between the two painted rows. Returns (the lines, a
    shallow copy where filled; the record of each filled gap {line, from, to, rows, off_before, off_after})."""
    out, rec = [], []
    for k, ln in enumerate(lines):
        if ln.get("color", "white") != "white" or not ln.get("dash"):
            out.append(ln)
            continue
        off = list(ln["off"])
        n = len(off)
        i = 0
        changed = False
        while i < n:
            if off[i] is not None:
                i += 1
                continue
            j = i
            while j + 1 < n and off[j + 1] is None:
                j += 1
            if i > 0 and j < n - 1 and off[i - 1] is not None and off[j + 1] is not None and j - i + 1 <= max_rows:
                a, b = float(off[i - 1]), float(off[j + 1])
                for r in range(i, j + 1):
                    t = (r - i + 1) / (j - i + 2)
                    off[r] = round(a + (b - a) * t, 4)
                rec.append({"line": k, "from": i, "to": j, "rows": j - i + 1, "off_before": a, "off_after": b})
                changed = True
            i = j + 1
        out.append(dict(ln, off=off) if changed else ln)
    return out, rec


def lane_ends(lanes: list[dict], e: dict) -> dict:
    """LANE ENDS (module docstring), in place: welds a tail to the head it runs into (``bridge_to_xyz_m``, ``joined``)
    and gives every lane its ``rubber_share``. Returns the summary."""
    def unit(a, b):
        dx, dz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(dx, dz)
        return (dx / L, dz / L) if L > EPS else (0.0, 0.0)

    opens = [i for i, ln in enumerate(lanes) if not ln["closed"] and len(ln["points_xyz_m"]) >= 2]
    cell = max(1.0, e["join_gap_m"])
    heads: dict[tuple[int, int], list[int]] = {}
    for i in opens:
        h = lanes[i]["points_xyz_m"][0]
        heads.setdefault((int(h[0] // cell), int(h[2] // cell)), []).append(i)
    cos_min = math.cos(math.radians(e["join_angle_deg"]))
    cand = []
    for i in opens:
        P = lanes[i]["points_xyz_m"]
        t = P[-1]
        ut = unit(P[-2], P[-1])
        for ci in range(int(t[0] // cell) - 1, int(t[0] // cell) + 2):
            for cj in range(int(t[2] // cell) - 1, int(t[2] // cell) + 2):
                for j in heads.get((ci, cj), ()):
                    if j == i:
                        continue
                    Q = lanes[j]["points_xyz_m"]
                    h = Q[0]
                    dx, dz = h[0] - t[0], h[2] - t[2]
                    along = dx * ut[0] + dz * ut[1]
                    side = -dx * ut[1] + dz * ut[0]
                    uh = unit(Q[0], Q[1])
                    if (EPS < along <= e["join_gap_m"] and abs(side) <= e["join_side_m"] and abs(h[1] - t[1]) <= JOIN_HEIGHT_M
                            and ut[0] * uh[0] + ut[1] * uh[1] >= cos_min):
                        cand.append((math.hypot(dx, dz), i, j, abs(side)))
    tail_of, head_of = {}, {}
    gaps, sides = [], []
    for d, i, j, sd in sorted(cand):                       # the nearest head wins; a head is welded once
        if i in tail_of or j in head_of:
            continue
        tail_of[i] = j
        head_of[j] = i
        gaps.append(d); sides.append(sd)
    fade = e["fade_m"]
    full_m = total_m = 0.0
    n_faded = 0
    for i, ln in enumerate(lanes):
        P = ln["points_xyz_m"]
        n = len(P)
        if ln["closed"]:
            ln["rubber_share"] = [1.0] * n
            total_m += ln["length_m"]; full_m += ln["length_m"]
            continue
        if i in tail_of:
            ln["bridge_to_xyz_m"] = [float(v) for v in lanes[tail_of[i]]["points_xyz_m"][0]]
        ln["joined"] = {"head": lanes[head_of[i]]["id"] if i in head_of else None,
                        "tail": lanes[tail_of[i]]["id"] if i in tail_of else None}
        seg = [math.dist(P[k], P[k + 1]) for k in range(n - 1)]
        s_head = [0.0]
        for d in seg:
            s_head.append(s_head[-1] + d)
        L = s_head[-1]
        share = []
        for k in range(n):
            a = 1.0 if (i in head_of or fade <= 0) else _smoothstep(s_head[k] / fade)
            b = 1.0 if (i in tail_of or fade <= 0) else _smoothstep((L - s_head[k]) / fade)
            share.append(round(min(a, b), 4))
        ln["rubber_share"] = share
        n_faded += (i not in head_of) + (i not in tail_of)
        for k in range(n - 1):
            m = 0.5 * (share[k] + share[k + 1])
            total_m += seg[k]; full_m += seg[k] * m
    return {"fade_m": fade, "join_gap_m": e["join_gap_m"], "join_side_m": e["join_side_m"],
            "join_angle_deg": e["join_angle_deg"], "welds": len(tail_of), "ends_faded": n_faded,
            "weld_gap_m_max": round(max(gaps), 3) if gaps else None, "weld_side_m_max": round(max(sides), 3) if sides else None,
            "lane_km": round(total_m / 1000.0, 2), "rubber_km": round(full_m / 1000.0, 2)}


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
    unknown = sorted(set(out) - set(DEFAULTS) - {"ends", "dash_gap_rows"})
    if unknown:
        raise SystemExit(f"[road_lanes] FATAL: road_wear.lanes.{unknown[0]}: unknown key (known: "
                         f"{sorted(DEFAULTS) + ['dash_gap_rows', 'ends']})")
    if "dash_gap_rows" in out:
        g = out["dash_gap_rows"]
        if g is None or g is False:
            del out["dash_gap_rows"]
        elif isinstance(g, bool) or not isinstance(g, int) or g < 1:
            raise SystemExit("[road_lanes] FATAL: road_wear.lanes.dash_gap_rows: a whole number of rows, at least 1")
    if "ends" in out:
        e = out["ends"]
        if e is None or e is False:
            del out["ends"]
        else:
            e = {} if e is True else {k: v for k, v in dict(e).items() if not str(k).startswith("_")}
            bad = sorted(set(e) - set(ENDS_DEFAULTS))
            if bad:
                raise SystemExit(f"[road_lanes] FATAL: road_wear.lanes.ends.{bad[0]}: unknown key (known: {sorted(ENDS_DEFAULTS)})")
            out["ends"] = {k: float(e.get(k, v)) for k, v in ENDS_DEFAULTS.items()}
            if out["ends"]["fade_m"] < 0 or out["ends"]["join_gap_m"] < 0:
                raise SystemExit("[road_lanes] FATAL: road_wear.lanes.ends: fade_m and join_gap_m are lengths, not negative")
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


# --- College Ave's two one-way roads (ledger 0055 round 2; the reader of split zone "college_split") ---------------------

def _smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def college_split_bounds(S: dict, rule: dict, v: int) -> dict:
    """{+1: (inner, outer), -1: (inner, outer)}: at mainline row v of the zone, each side's inner bound (where its lanes
    start counting: the paint's own divider base) and its edge line, as DISTANCES from the old line on that side (+1 =
    west = the southbound road, -1 = east = the northbound). The paint section of
    source/college_r2/college_middle_blend.py, expression for expression:
      * the two roads (rows NOSE..TAIL, ``rows.v``): the yellow stands edge_inset inside the road's median edge
        (``offsets_m`` sb_east + edge_inset; nb_west - edge_inset) and the dividers count lane_w from it;
      * the forks (rows A0..NOSE and TAIL..A1): the divider base runs from the old line's centre to the yellow at the
        point where the roads part, eased by the same smoothstep (``fork_t(v) * (meet(v) +- edge_inset)``);
      * the edge line stands edge_inset inside the built half width (``frame.half_w``) on both sides, everywhere.
    A base on the far side of the old line is a negative distance (the south fork's west yellow ends 0.72 m east of
    the old line, where the roads part at -1.27 m)."""
    R, F = S["rows"], S["frame"]
    a0, a1 = int(S["mainline"]["from_v"]), int(S["mainline"]["to_v"])
    nose, tail = int(R["v"][0]), int(R["v"][-1])
    ei = rule["edge_inset"]
    off = R["offsets_m"]
    k = v - nose
    if nose <= v <= tail:
        if int(R["v"][k]) != v:
            raise SystemExit(f"[road_lanes] FATAL: college_split rows.v is not one row per station at v {v}")
        west, east = float(off["sb_east"][k]) + ei, float(off["nb_west"][k]) - ei
    else:
        t = _smoothstep((v - a0) / (nose - a0)) if v < nose else _smoothstep((a1 - v) / (a1 - tail))
        meet = float(off["sb_east"][0 if v < nose else tail - nose])
        west, east = t * (meet + ei), t * (meet - ei)
    outer = float(F["half_w"][v - int(F["from_v"])]) - ei
    return {1: (west, outer), -1: (-east, outer)}


def read_college_split(proj: Path, zone: dict, rule: dict) -> list[dict]:
    """The lanes of College Ave's two one-way roads and their two forks (mainline rows ``from``..``to`` of the zone),
    off ``source``: source/college_r2/college_split.data.json, the data the scene's rows were built to. Each side's
    lanes count from its yellow outward by the paint rule's own division (``side_bounds``, the same clip), and pass the
    same two tests as every other lane (``road_lanes``: the edge leftover at least min_edge_lane_m wide, a car fits).
    The mainline runs north on College and + is west, so the southbound road's lanes are "reverse" and the northbound
    road's "forward". A lane's height is its own road's surface at its offset (a row is tilted, west edge to east
    edge); on a fork, the fork row's (west edge, line, east edge). Offsets stay offsets from the OLD line, as every
    mainline lane's are."""
    S = json.loads((proj / zone["source"]).read_text(encoding="utf-8"))
    R, F = S["rows"], S["frame"]
    a0, a1 = int(S["mainline"]["from_v"]), int(S["mainline"]["to_v"])
    nose, tail = int(R["v"][0]), int(R["v"][-1])
    if (a0, a1) != (int(zone["from"]), int(zone["to"])):
        raise SystemExit(f"[road_lanes] FATAL: split zone college_split is rows {zone['from']}-{zone['to']} but "
                         f"{zone['source']} holds rows {a0}-{a1}")
    fv0 = int(F["from_v"])
    fork_y = {int(v): [float(y) for y in ys] for v, ys in zip(R.get("fork_v") or [], R.get("fork_y") or [])}
    off = R["offsets_m"]
    fr, per = [], []
    for v in range(a0, a1 + 1):
        i = v - fv0
        fr.append((float(F["x"][i]), float(F["y"][i]), float(F["z"][i]), float(F["nx"][i]), float(F["nz"][i])))
        b = college_split_bounds(S, rule, v)
        row = []
        for side in (1, -1):
            sp = lanes_between(side_bounds(b[side][0], b[side][1], rule), side)
            row += [(side, k, lo, hi, k == len(sp)) for k, lo, hi in sp]
        per.append(row)
    spec = {"min_edge_lane_m": float(zone.get("min_edge_lane_m", DEFAULTS["min_edge_lane_m"]))}
    stats = {"edge_strip_km": 0.0, "island_trimmed_km": 0.0, "no_car_fits_km": 0.0, "single_station_runs": 0}
    lanes = road_lanes("mainline", "split:college_split", fr, False, per, [None] * len(fr), [False] * len(fr), spec, stats)

    def height(v: int, o: float) -> float:
        if nose <= v <= tail:
            k = v - nose
            w_, e_ = ("sb_west", "sb_east") if o >= float(off["sb_east"][k]) else ("nb_west", "nb_east")
            ow, oe = float(off[w_][k]), float(off[e_][k])
            t = 0.0 if abs(ow - oe) < 1e-9 else max(0.0, min(1.0, (ow - o) / (ow - oe)))
            return float(R[w_][k][1]) + (float(R[e_][k][1]) - float(R[w_][k][1])) * t
        if v in fork_y:
            hw = float(F["half_w"][v - fv0])
            yw, yl, ye = fork_y[v]
            t = max(-1.0, min(1.0, o / hw)) if hw > 0 else 0.0
            return yl + (yw - yl) * t if t >= 0 else yl + (ye - yl) * (-t)
        return float(F["y"][v - fv0])

    for ln in lanes:
        ln["rows"] = [a0 + i for i in ln["rows"]]
        ln["id"] = "mainline/college_split/" + ln["id"].split("/", 1)[1]
        ln["points_xyz_m"] = [[p[0], round(height(v, o), 3), p[2]] for p, v, o in zip(ln["points_xyz_m"], ln["rows"], ln["offset_m"])]
    return lanes


SPLIT_ZONE_READERS["college_split"] = read_college_split


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
    dash_filled: list[dict] = []

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
            if spec.get("dash_gap_rows"):                # DASH GAPS (opt-in)
                lines, filled = fill_dash_gaps(lines, int(spec["dash_gap_rows"]))
                if filled:
                    dash_filled.append({"connector": name, "gaps": filled})
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
    ends = lane_ends(lanes, spec["ends"]) if spec.get("ends") else None
    return {
        **({"ends": ends} if ends is not None else {}),
        **({"dash_gaps": {"max_rows": int(spec["dash_gap_rows"]), "filled": dash_filled,
                          "gaps": sum(len(f["gaps"]) for f in dash_filled),
                          "rows": sum(g["rows"] for f in dash_filled for g in f["gaps"])}}
           if spec.get("dash_gap_rows") else {}),
        "what": "lane centres for road wear on streets (ledger 0084's 'lanes' source): one line per lane, both "
                "directions, the lanes the paint rule paints; tools/road_lanes.py",
        "ledger": ["0084", "0099"],
        "frame": "ENU local meters (X=east, Y=up, Z=north)",
        "rule": dict(rule, source="scripts-v021 geometry/ribbon.py lane_markings / connector_markings"),
        "min_edge_lane_m": float(spec["min_edge_lane_m"]), "car_width_m": car_width_m(), "rubber": float(spec["rubber"]),
        "track_m": float(rw_defaults()["wear"]["track_m"]),
        "excluded": spec["exclude"], "split_zones": zones, "sources": sources,
        "summary": {"lanes": len(lanes), "km": {k: round(v, 2) for k, v in km.items()}, "by_group": by_group, **stats},
        "lanes": lanes,
    }


def bake_lines(doc: dict, layer_m: float = 10.0) -> list[dict]:
    """The output as tools/road_wear_blend.py's ``lines`` (HOW IT FEEDS THE BAKE): per lane {"P" (N x 3, Blender
    x = east, y = north, height), "I" (uniform rubber), "closed", "layer_m", "layout" "lanes", "source" the lane id,
    "lap_m"}, ready for scripts/aerial/road_wear.wear_at. Where the tool was run with ``ends`` (LANE ENDS; the doc
    carries "ends"): "I" is the rubber times the lane's ``rubber_share``, a welded tail has its bridge point as its
    last point, and every line asks for square ends ("butt_ends")."""
    import numpy as np
    out = []
    ends = bool(doc.get("ends"))
    for ln in doc["lanes"]:
        pts, share = lane_line(ln) if ends else (ln["points_xyz_m"], [1.0] * len(ln["points_xyz_m"]))
        P = np.array([[x, z, y] for x, y, z in pts], dtype=np.float64)
        out.append({"P": P, "I": float(doc["rubber"]) * np.array(share, dtype=np.float64), "closed": bool(ln["closed"]),
                    "layer_m": float(layer_m), "layout": "lanes", "source": ln["id"], "lap_m": ln["length_m"],
                    **({"butt_ends": True} if ends else {})})
    return out


def lane_line(ln: dict) -> tuple[list, list]:
    """A lane as it is drawn under LANE ENDS: (points, rubber share per point), the bridge point of a welded tail added
    at full share. The bake (bake_lines) and the gate (tools/road_wear_check.py) both draw this."""
    pts = list(ln["points_xyz_m"]); share = list(ln.get("rubber_share") or [1.0] * len(pts))
    if ln.get("bridge_to_xyz_m"):
        pts.append(list(ln["bridge_to_xyz_m"])); share.append(share[-1])
    return pts, share


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
    if doc.get("dash_gaps"):
        g = doc["dash_gaps"]
        print(f"[road_lanes]   dash gaps: {g['gaps']} gap(s) of at most {g['max_rows']} rows in authored dashed dividers read as "
              f"painted ({g['rows']} rows)")
    if doc.get("ends"):
        e = doc["ends"]
        print(f"[road_lanes]   ends: {e['welds']} welded to the lane they run into (gap <= {e['weld_gap_m_max']} m, "
              f"{e['weld_side_m_max']} m to the side at most), {e['ends_faded']} faded over {e['fade_m']} m; "
              f"{e['rubber_km']} km of rubber on {e['lane_km']} km of lane")
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
