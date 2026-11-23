"""College split, order of work step 1: THE DATA (no Blender, no scene). STEP-DESIGN.md has the why.

    python college_split_data.py <project dir> [--write]

Computes, from college_design.json (the measured section) and the centreline's own widths (the built outer edges):

  the MAINLINE through the split = the southbound carriageway. Vertex NUMBERS are kept; v1131..v1475 move sideways.
      two roads   v1172..v1444   west edge = the built west edge, east edge = the island's west side (measured)
      south fork  v1130..v1172   the east edge runs from the built east edge (v1130, the whole road) to the island's
                                 nose; inside a fork the line is a reference only (the fork deck paves it)
      north fork  v1444..v1476   the same, from the island's tail out to the built east edge
      line = the midline of [east edge, west edge], width = west - east; height = the built road's, plus the measured
      crossfall from the built west edge (which keeps its place and height) to the line
  the NORTHBOUND PIECE `college_nb` (a connectors.local.json record), one point per mainline station v1172..v1444:
      east edge = the built east edge, west edge = the island's east side; midline, width; height = the built road's
      plus the measured rise of the northbound road over the built west edge
  the island: `median_bands.json` island_w_by_vertex = 0 for v1117..v1475 (the real road has none in the two forks,
      and through the split the bank is plain ground between two roads)
  the SPEEDWAY LAP `race.laps.college`: MAINLINE 0..1130, college_nb 0..346, MAINLINE 1476..4497. The piece's record runs
      the whole zone (its fork rows carry the Speedway's lane through the fork), so the three pieces meet end to end,
      the lap's vertex k IS the mainline's vertex k, and every vertex-keyed race declaration carries over unchanged
  the metre-keyed entries of track.config.json after the split, each with its old and new station.

Without --write it only reports and writes college_split.data.json beside this file. With --write it rewrites the
project's data (each file kept once as <name>.pre-split) and adds race.laps.college to the PROJECT's
track.config.json: a scratch workshop only, never airoso's own config."""
import json
import math
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIFT = 0.10                       # the road rides this far over the centreline's y (tools/race_furniture.py LIFT)
A0, NOSE, TAIL, A1 = 1130, 1172, 1444, 1476
ISLAND_OFF = (1117, 1475)         # island width 0 on the mainline, inclusive
FRAME = (1090, 1500)              # the built line's frame is written for these vertices (the zone and its surroundings)
PIECE = "college_nb"
LAP = "college"

proj = Path(sys.argv[1])
WRITE = "--write" in sys.argv[2:]
D = {r["v"]: r for r in json.loads((HERE / "college_design.json").read_text(encoding="utf-8"))["stations"]}
data = proj / "data"
src_cl = data / ("centerline.local.json.pre-split" if (data / "centerline.local.json.pre-split").exists() else "centerline.local.json")
cl = json.loads(src_cl.read_text(encoding="utf-8"))
P0 = [tuple(p) for p in cl["points_xyz_m"]]
W0 = list(cl["widths_m"])
n_all = len(P0)
closed = math.dist(P0[0], P0[-1]) < 1e-6
m = n_all - 1 if closed else n_all


def frame(v):
    """the OLD line's left normal at v (x east, z north): n = (-tz, tx) of the central difference"""
    a, b = P0[(v - 1) % m], P0[(v + 1) % m]
    tx, tz = b[0] - a[0], b[2] - a[2]
    L = math.hypot(tx, tz) or 1.0
    return -tz / L, tx / L


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def west(v):
    """the built road's west edge, as an offset from the OLD line: ROAD's edge column, half the centreline's width.
    (college_edges.json's built_to_m / built_from_m are the same edge floored to the lidar's 0.5 m cells: they step
    by half a metre from station to station and put a 6 degree kink in a midline taken from them.)"""
    return 0.5 * W0[v]


def east(v):
    return -0.5 * W0[v]


def surface(v, off):
    """the design's surface height at (v, offset): linear through its four control points, flat outside them"""
    r = D[v]
    pts = sorted((r[k]["offset_m"], r[k]["y"]) for k in ("nb_outer", "nb_inner", "sb_inner", "sb_outer"))
    if off <= pts[0][0]:
        return pts[0][1]
    for (o0, y0), (o1, y1) in zip(pts, pts[1:]):
        if off <= o1:
            return y0 if o1 - o0 < 1e-9 else y0 + (y1 - y0) * (off - o0) / (o1 - o0)
    return pts[-1][1]


def at(v, off, y):
    nx, nz = frame(v)
    return (P0[v][0] + off * nx, y, P0[v][2] + off * nz)


SMOOTH_PASSES = 24                # [invented] 1-2-1 passes over an edge's sideways offset (about +-15 m), ends held


def relax(vals, passes=SMOOTH_PASSES):
    """an edge's sideways offset per station, smoothed with its two ends held: the measured edges step by decimetres
    from station to station, and a road edge must not. A convex average, so a series that is never negative stays so."""
    a = list(vals)
    for _ in range(passes):
        b = a[:]
        for k in range(1, len(a) - 1):
            b[k] = 0.25 * a[k - 1] + 0.5 * a[k] + 0.25 * a[k + 1]
        a = b
    return a


def grade(pts):
    """a polyline's grades in percent: [steepest down, steepest up, largest step between consecutive segments]"""
    g = [100.0 * (b[1] - a[1]) / math.hypot(b[0] - a[0], b[2] - a[2]) for a, b in zip(pts, pts[1:])]
    return [round(min(g), 2), round(max(g), 2), round(max(abs(y - x) for x, y in zip(g, g[1:])), 2)]


def turn_deg(pts):
    """the largest change of heading between consecutive segments of a polyline, degrees"""
    worst = 0.0
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        h0 = math.atan2(b[0] - a[0], b[2] - a[2])
        h1 = math.atan2(c[0] - b[0], c[2] - b[2])
        worst = max(worst, abs((h1 - h0 + math.pi) % (2 * math.pi) - math.pi))
    return math.degrees(worst)


def fork_offsets(v_out, v_in, c_in, slope_in):
    """a line's sideways offset through a fork, per station from the untouched row v_out (offset 0, running straight on)
    to the row v_in where a carriageway begins (offset c_in, drifting by slope_in per station INTO the carriageway): a
    cubic that meets both ends in place and in direction. Inside a fork the line is a reference only (the deck paves
    it), so it takes nothing from the built edges there: the built road's edge has a 6 degree corner at v1171 and a
    midline taken from it carried half of that."""
    L = abs(v_in - v_out)
    step = 1 if v_in > v_out else -1
    out = {}
    for k in range(L + 1):
        s = k / L
        out[v_out + step * k] = c_in * (3.0 * s * s - 2.0 * s ** 3) + L * slope_in * (s ** 3 - s * s)
    return out


# --- the mainline -----------------------------------------------------------------------------------------------------
# Through the two roads EDGES are smoothed, not centrelines. The WEST edge is the built one exactly as it stands (its
# column in ROAD does not move sideways, the built walk keeps its place); the EAST edge is the measured island side,
# relaxed with its two ends (the nose, the tail) held; the line is their midline. Smoothing the midline instead moved
# the inner edge by twice the correction and laid the two roads over each other by 0.24 m at the nose.
ZONE = range(A0, A1 + 1)
sb_east = dict(zip(range(NOSE, TAIL + 1), relax([D[v]["sb_inner"]["offset_m"] for v in range(NOSE, TAIL + 1)])))
main_off = {v: 0.5 * (west(v) + sb_east[v]) for v in range(NOSE, TAIL + 1)}
main_off.update(fork_offsets(A0, NOSE, main_off[NOSE], main_off[NOSE + 1] - main_off[NOSE]))
main_off.update(fork_offsets(A1, TAIL, main_off[TAIL], main_off[TAIL - 1] - main_off[TAIL]))
blend_t = {v: 1.0 if NOSE <= v <= TAIL else smooth((v - A0) / (NOSE - A0)) if v < NOSE else smooth((A1 - v) / (A1 - TAIL))
           for v in ZONE}


def tilt(v, off):
    """the measured cross-section at (v, off) RELATIVE to its own height at the built west edge, eased in over the forks"""
    return blend_t[v] * (surface(v, off) - surface(v, west(v)))


def heights(off):
    """SURFACE heights per station of the zone along a column `off` (v -> offset): the built road's height (the built
    line + LIFT: the built rows are flat across) plus the relaxed tilt there.

    The datum is the BUILT WEST EDGE: it keeps its place and its height, so the west walk, the house lots and the
    ground behind them stay put (stage A's decision). What is taken from the lidar is the SHAPE across the road: each
    carriageway's crossfall and the northbound road's rise over the southbound one. Absolute heights are therefore off
    the lidar by what the built west edge is off it (report: datum_shift_m), smoothly along the road.

    The tilt is smoothed, never the road: sampled raw, the measured section puts 2 cm of noise on every station (grade
    steps of 2 points between segments against the built line's 0.6), and smoothing heights themselves would shave
    the crest."""
    dep = [tilt(v, off[v]) for v in ZONE]
    dep[0] = dep[-1] = 0.0
    return {v: P0[v][1] + LIFT + d for v, d in zip(ZONE, relax(dep))}


main_y = {v: y - LIFT for v, y in heights(main_off).items()}        # a line rides LIFT under its surface
main_pts, main_w = {}, {}
for v in ZONE:
    if v in (A0, A1):                            # the two outer rows are the untouched road
        main_pts[v], main_w[v] = P0[v], W0[v]
    else:                                        # width = twice (built west edge - line): the west edge never moves
        main_pts[v], main_w[v] = at(v, main_off[v], main_y[v]), 2.0 * (west(v) - main_off[v])
P1 = list(P0)
W1 = list(W0)
for v in range(A0 + 1, A1):                     # nothing outside the zone is written, the closing point included
    P1[v], W1[v] = main_pts[v], main_w[v]

# --- the northbound piece and the Speedway lap's two joins -------------------------------------------------------------------
# The piece's EAST edge is the built east edge as it stands; its WEST edge is the mainline's east edge less the bank's
# width, and the bank's width (measured, never negative) is relaxed with its two ends held at ZERO: so the roads cannot
# overlap, and at the nose and the tail they meet in one point (the island begins and ends with no width). The design
# tapered the island over three stations to 0.35 m / 0.30 m at those rows [invented]; a 0.35 m strip with an 0.18 m
# step between two carriageways is a 52 % sliver of pavement in the fork, so the taper runs to nothing instead.
# The lap through the zone is ONE line: the south join (one point per mainline station), the piece, the north join. Its
# sideways offset is the piece's midline between the nose and the tail and the same cubic as the mainline's fork line
# outside them; its heights are one relaxed departure from the built line over the whole zone.
raw_b = [D[v]["sb_inner"]["offset_m"] - D[v]["nb_inner"]["offset_m"] for v in range(NOSE, TAIL + 1)]
if min(raw_b) < -1e-9:
    raise SystemExit(f"college_design.json: the two inner edges cross (bank {min(raw_b):.3f} m)")
raw_b[0] = raw_b[-1] = 0.0
bank_w = relax(raw_b)
nb_west = {v: sb_east[v] - bank_w[k] for k, v in enumerate(range(NOSE, TAIL + 1))}
lap_off = {v: 0.5 * (nb_west[v] + east(v)) for v in range(NOSE, TAIL + 1)}
lap_off.update(fork_offsets(A0, NOSE, lap_off[NOSE], lap_off[NOSE + 1] - lap_off[NOSE]))
lap_off.update(fork_offsets(A1, TAIL, lap_off[TAIL], lap_off[TAIL - 1] - lap_off[TAIL]))
lap_y = {v: y - LIFT for v, y in heights(lap_off).items()}
# the four edges' surface heights. In a fork an inner edge is notional (the mirror of the outer edge about the line), so
# each series runs the whole zone and is relaxed as one; the rows of the two roads take its NOSE..TAIL part.
sb_east_z = {v: sb_east[v] if NOSE <= v <= TAIL else 2.0 * main_off[v] - west(v) for v in ZONE}
nb_west_z = {v: nb_west[v] if NOSE <= v <= TAIL else 2.0 * lap_off[v] - east(v) for v in ZONE}
edge_y = {"sb_west": heights({v: west(v) for v in ZONE}), "sb_east": heights(sb_east_z),
          "nb_west": heights(nb_west_z), "nb_east": heights({v: east(v) for v in ZONE})}
# across the bank: the northbound inner edge stands over the southbound one by the relaxed measured step, which is zero
# at the nose and the tail (the same point there), so the two roads meet with no step
rise_in = relax([tilt(v, nb_west[v]) - tilt(v, sb_east[v]) for v in range(NOSE, TAIL + 1)])
if abs(rise_in[0]) > 1e-9 or abs(rise_in[-1]) > 1e-9:
    raise SystemExit("the two inner edges do not meet at the nose / the tail")
for k, v in enumerate(range(NOSE, TAIL + 1)):
    edge_y["nb_west"][v] = edge_y["sb_east"][v] + rise_in[k]
centre_y = heights({v: 0.0 for v in ZONE})          # the built line's own column: the fork rows' centre vertex
if max(abs(edge_y["sb_west"][v] - (P0[v][1] + LIFT)) for v in ZONE) > 1e-9:
    raise SystemExit("the built west edge moved in height")


# Where the two roads part and meet again (the nose row, the tail row) their two rows and the fork's row are ONE
# straight section: the point the roads share is put on the chord from the built west edge to the east edge, and
# that correction is eased out over the next EASE_ROWS rows of the two inner edges. Left where the smoothed section
# had it, the shared point stood about 0.1 m under that chord: a pocket in the fork's pavement, and a step in both
# lines' heights where they leave the fork's row for their own road's (grade steps of 2.4 and 3.8 points).
EASE_ROWS = 20                    # [invented] about 60 m (10 rows left a twist of 0.06 m per row at the tail: near the prep's 0.02 m ground clearance)
meet_corr = {}
for end, sgn in ((NOSE, 1), (TAIL, -1)):
    for j in range(EASE_ROWS + 1):
        v = end + sgn * j
        wgt = 1.0 - smooth(j / EASE_ROWS)
        yw_, ye_ = edge_y["sb_west"][v], edge_y["nb_east"][v]
        for key, offs in (("sb_east", sb_east), ("nb_west", nb_west)):
            # each row's own distance to the chord, weighted: the correction then keeps its slope across the nose row
            # (the same constant on every row left a grade step of 1.2 to 1.3 points in both lines there)
            on_chord = yw_ + (ye_ - yw_) * (west(v) - offs[v]) / (west(v) - east(v))
            d_ = (on_chord - edge_y[key][v]) * wgt
            edge_y[key][v] += d_
            if j == 0 and key == "sb_east":
                meet_corr[end] = d_

# Rows are PLANAR across: a line rides on the straight chord between its own road's two edges, it does not carry a
# height of its own. Sampled on its own the line stood up to 0.06 m under that chord on the southbound road (83 rows
# by more than 0.02 m) and 0.10 m in the forks: a shallow valley along the line. The prep pins the ground 0.02 m under
# the pavement at the ground's own vertices only, so ground facets bridged the valley and stood through the asphalt
# (measured on the scratch scene's prep run: 148 samples on the southbound road, 16 in the forks).
def chord(v, off, road):
    if NOSE <= v <= TAIL and road == "sb":
        (o0, y0), (o1, y1) = (west(v), edge_y["sb_west"][v]), (sb_east[v], edge_y["sb_east"][v])
    elif NOSE <= v <= TAIL:
        (o0, y0), (o1, y1) = (nb_west[v], edge_y["nb_west"][v]), (east(v), edge_y["nb_east"][v])
    else:                                        # a fork row: one road, the built west edge to the built east edge
        (o0, y0), (o1, y1) = (west(v), edge_y["sb_west"][v]), (east(v), edge_y["nb_east"][v])
    return y0 + (y1 - y0) * (o0 - off) / (o0 - o1)


main_y = {v: chord(v, main_off[v], "sb") - LIFT for v in ZONE}
lap_y = {v: chord(v, lap_off[v], "nb") - LIFT for v in ZONE}
centre_y = {v: chord(v, 0.0, "sb") for v in ZONE}        # used on the fork rows only
for v in range(A0 + 1, A1):
    main_pts[v] = at(v, main_off[v], main_y[v])
    P1[v] = main_pts[v]
lap_zone = {v: P0[v] if v in (A0, A1) else at(v, lap_off[v], lap_y[v]) for v in ZONE}
# The piece's RECORD runs the whole zone, v1130..v1476, forks included (one point per mainline station), so the lap
# is three pieces that meet end to end and needs no declared join. A declared join takes its widths by straight
# interpolation between its two ends, which put the Speedway's lane up to 1.2 m outside the pavement mid-fork; a
# piece carries its own width per point. In a fork that width is twice (the lap's line - the built east edge): the
# lane's right face is the built east curb, and its left face runs from the west curb at the outer row to the point
# where the roads part: the diagonal that keeps the Speedway off the southbound road. The mainline's own fork rows
# mirror it (width = twice (the built west edge - its line)): the Reverse's lane is sealed off the northbound road.
piece_off = [lap_off[v] for v in range(NOSE, TAIL + 1)]            # the two roads' rows only (the report's numbers)
piece_pts = [lap_zone[v] for v in range(NOSE, TAIL + 1)]
piece_w = [nb_west[v] - east(v) for v in range(NOSE, TAIL + 1)]
# ...and it STOPS one row short of the north outer row (v1475): where two piece ends coincide the lap keeps the earlier
# piece's vertex, and at v1476 that must be the mainline's own, which carries the island that begins there (taken from
# the piece, lap vertex 1476 read island 0 and the lap's island nose came out one row late). The 3 m step from v1475
# to the mainline's v1476 is a plain join with no point of its own (join_spacing_m 4).
REC = range(A0, A1)
rec_pts = [lap_zone[v] for v in REC]
rec_w = [(nb_west[v] - east(v)) if NOSE <= v <= TAIL else 2.0 * (lap_off[v] - east(v)) for v in REC]
rec_w[0] = W0[A0]                                                   # its first point is the mainline's own row
edge_dev = {"sb_inner_max_m": max(abs(sb_east[v] - D[v]["sb_inner"]["offset_m"]) for v in range(NOSE, TAIL + 1)),
            "nb_inner_max_m": max(abs(nb_west[v] - D[v]["nb_inner"]["offset_m"]) for v in range(NOSE, TAIL + 1))}
TWO = range(NOSE, TAIL + 1)
shift = [P0[v][1] + LIFT - surface(v, west(v)) for v in TWO]
xf_sb = [100.0 * (edge_y["sb_east"][v] - edge_y["sb_west"][v]) / (west(v) - sb_east[v]) for v in TWO]      # + = rises to the east
xf_nb = [100.0 * (edge_y["nb_east"][v] - edge_y["nb_west"][v]) / (nb_west[v] - east(v)) for v in TWO]
step_in = [edge_y["nb_west"][v] - edge_y["sb_east"][v] for v in TWO]                                       # across the bank
height_rep = {"rows": "planar across: a line rides on the chord of its own road's two edges", "shared_point_put_on_the_fork_rows_chord_m": {"nose": round(meet_corr[NOSE], 3), "tail": round(meet_corr[TAIL], 3), "eased_out_over_rows": EASE_ROWS}, "datum": "the built west edge: its place and height are kept; the measured shape across the road is laid onto it",
              "datum_shift_m": {"_doc": "built west edge minus the lidar there: how far every height here stands off the lidar",
                                "min": round(min(shift), 2), "max": round(max(shift), 2)},
              "crossfall_pct_rising_east": {"southbound": [round(min(xf_sb), 2), round(max(xf_sb), 2)],
                                            "northbound": [round(min(xf_nb), 2), round(max(xf_nb), 2)]},
              "northbound_inner_edge_over_southbound_inner_edge_m": {"at_nose": round(step_in[0], 2), "max": round(max(step_in), 2),
                                                                     "at_tail": round(step_in[-1], 2)},
              "bank_slope_pct_max": round(max(100.0 * d / b for d, b in zip(step_in, bank_w) if b > 1.0), 1)}
lap = {"pieces": [{"line": "MAINLINE", "from": 0, "to": A0}, {"line": PIECE, "from": 0, "to": len(rec_pts) - 1},
                  {"line": "MAINLINE", "from": A1, "to": m - 1}], "join_spacing_m": 4.0}


# --- stations: old and new ----------------------------------------------------------------------------------------------
def stations(P):
    s = [0.0]
    for k in range(1, m):
        s.append(s[-1] + math.hypot(P[k][0] - P[k - 1][0], P[k][2] - P[k - 1][2]))
    return s


S0, S1 = stations(P0), stations(P1)


def remap(s_old):
    """an old station (m along the old line) -> the same place along the new line"""
    lo, hi = 0, m - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if S0[mid] <= s_old:
            lo = mid
        else:
            hi = mid
    f = 0.0 if S0[hi] == S0[lo] else (s_old - S0[lo]) / (S0[hi] - S0[lo])
    return S1[lo] + f * (S1[hi] - S1[lo])


cfg_path = proj / "track.config.json"
cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
keyed = []


def walk(o, path):
    if isinstance(o, dict):
        for k, v in o.items():
            if not k.startswith("_"):
                walk(v, path + "." + k)
    elif isinstance(o, list):
        nums = [x for x in o if isinstance(x, (int, float)) and not isinstance(x, bool)]
        key = path.rsplit(".", 1)[-1]
        if nums and len(nums) == len(o) and len(o) <= 4 and (key.endswith("_m") or key == "s_m"):
            if any(x > S0[A0] for x in nums) and max(nums) <= S0[-1] + 50:
                keyed.append((path, o))
        else:
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")


for top in ("terrain", "road_datum"):
    walk(cfg.get(top) or {}, "." + top)
shift = [{"path": p, "old": o, "new": [round(remap(x), 1) if x > S0[A0] else x for x in o]} for p, o in keyed]

lat = [abs(main_off[v]) for v in range(A0, A1 + 1)]
step_max = max(math.hypot(P1[v][0] - P1[v - 1][0], P1[v][2] - P1[v - 1][2]) for v in range(A0, A1 + 1))
step_min = min(math.hypot(P1[v][0] - P1[v - 1][0], P1[v][2] - P1[v - 1][2]) for v in range(A0, A1 + 1))
kink = turn_deg(P1[A0 - 3:A1 + 4])
kink_old = turn_deg(P0[A0 - 3:A1 + 4])
lap_pts = P1[:A0] + rec_pts + P1[A1:m]
lap_len = sum(math.hypot(b[0] - a[0], b[2] - a[2]) for a, b in zip(lap_pts, lap_pts[1:] + lap_pts[:1]))
lap_seg = [math.hypot(b[0] - a[0], b[2] - a[2]) for a, b in zip(lap_pts[A0 - 1:A1 + 1], lap_pts[A0:A1 + 2])]
report = {
    "rows": {"south_fork": [A0, NOSE], "two_roads": [NOSE, TAIL], "north_fork": [TAIL, A1]},
    "smoothing": {"passes_121": SMOOTH_PASSES, "what": "the two inner edges and the bank's width; the outer edges are the built ones, unmoved",
                  "inner_edge_off_the_measured_edge_max_m": {k: round(x, 2) for k, x in edge_dev.items()},
                  "built_road_middle_off_the_line_at_outer_rows_m": [round(0.5 * (west(A0) + east(A0)), 3), round(0.5 * (west(A1) + east(A1)), 3)]},
    "heights": {**height_rep,
                "grade_pct_min_max_and_largest_step_between_segments": {
                    "built_line": grade(P0[A0 - 3:A1 + 4]), "mainline": grade(P1[A0 - 3:A1 + 4]),
                    "lap": grade(lap_pts[A0 - 3:A1 + 4])}},
    "mainline": {"vertices_moved": A1 - A0 - 1, "lateral_max_m": round(max(lat), 2),
                 "width_m": {"at_nose": round(main_w[NOSE], 2), "at_tail": round(main_w[TAIL], 2),
                             "two_roads_min": round(min(main_w[v] for v in range(NOSE, TAIL + 1)), 2),
                             "two_roads_max": round(max(main_w[v] for v in range(NOSE, TAIL + 1)), 2)},
                 "segment_m": {"min": round(step_min, 2), "max": round(step_max, 2)},
                 "largest_turn_between_segments_deg": {"new": round(kink, 2), "old": round(kink_old, 2)},
                 "lap_length_m": {"old": round(S0[-1], 1), "new": round(S1[-1], 1), "change": round(S1[-1] - S0[-1], 2)}},
    "bank_between_the_roads_m": {"min": round(min(bank_w), 2), "at_nose": round(bank_w[0], 2), "at_tail": round(bank_w[-1], 2),
                                 "max": round(max(bank_w), 2)},
    "piece": {"name": PIECE, "points": len(piece_pts), "width_m": {"min": round(min(piece_w), 2), "max": round(max(piece_w), 2),
                                                                     "at_nose": round(piece_w[0], 2), "at_tail": round(piece_w[-1], 2)},
              "largest_turn_between_segments_deg": round(turn_deg(piece_pts), 2),
              "over_mainline_m": {"max": round(max(piece_pts[k][1] - main_pts[NOSE + k][1] for k in range(len(piece_pts))), 2),
                                  "at_nose": round(piece_pts[0][1] - main_pts[NOSE][1], 2),
                                  "at_tail": round(piece_pts[-1][1] - main_pts[TAIL][1], 2)}},
    "lap": {"id": LAP, "pieces": "MAINLINE 0..%d, %s 0..%d, MAINLINE %d..%d; no declared join" % (A0, PIECE, len(rec_pts) - 1, A1, m - 1),
            "vertices": len(lap_pts), "mainline_vertices": m,
            "largest_turn_between_segments_deg": round(turn_deg(lap_pts[A0 - 3:A1 + 4]), 2),
            "segment_m": {"min": round(min(lap_seg), 2), "max": round(max(lap_seg), 2)},
            "length_m": round(lap_len, 1), "against_the_mainline_m": round(lap_len - S1[-1] - math.hypot(P1[0][0] - P1[m - 1][0], P1[0][2] - P1[m - 1][2]), 2),
            "piece_start_off_the_mainline_m": round(math.dist(rec_pts[0], P1[A0]), 4), "piece_end_to_mainline_v%d_m" % A1: round(math.dist(rec_pts[-1], P1[A1]), 3),
            "fork_width_m": {"min": round(min(rec_w[:NOSE - A0] + rec_w[TAIL - A0 + 1:]), 2), "max": round(max(rec_w), 2)}},
    "island_w_zero": list(ISLAND_OFF), "station_keyed": shift,
}
out = {"what": "College split, the data (college_split_data.py)", "report": report, "lap": lap,
       "piece": {"name": PIECE, "kind": "connector", "points_xyz_m": [[round(c, 4) for c in q] for q in rec_pts],
                 "widths_m": [round(w, 3) for w in rec_w]},
       "edges": {"_doc": "offsets from the OLD line per station of the two roads, + = west: what the scene rows are built to "
                         "(the mainline row = sb_west, its line, sb_east; the piece row = nb_west, its line, nb_east)",
                 "v": list(range(NOSE, TAIL + 1)),
                 "sb_west_m": [round(west(v), 3) for v in range(NOSE, TAIL + 1)], "sb_east_m": [round(sb_east[v], 3) for v in range(NOSE, TAIL + 1)],
                 "nb_west_m": [round(nb_west[v], 3) for v in range(NOSE, TAIL + 1)], "nb_east_m": [round(east(v), 3) for v in range(NOSE, TAIL + 1)],
                 "_doc_y": "SURFACE heights of the same four edges (a row is west edge, line + LIFT, east edge: tilted, not flat)",
                 "sb_west_y": [round(edge_y["sb_west"][v], 4) for v in range(NOSE, TAIL + 1)],
                 "sb_east_y": [round(edge_y["sb_east"][v], 4) for v in range(NOSE, TAIL + 1)],
                 "nb_west_y": [round(edge_y["nb_west"][v], 4) for v in range(NOSE, TAIL + 1)],
                 "nb_east_y": [round(edge_y["nb_east"][v], 4) for v in range(NOSE, TAIL + 1)]},
       "rows": {"_doc": "the SCENE's rows, engine xyz (x east, y up = the SURFACE, z north). Two roads, v = NOSE..TAIL: the mainline's "
                        "row is sb_west (ROAD's own west vertex, unmoved), sb_line, sb_east; the piece's row is nb_west, nb_line, nb_east "
                        "(nb_east = where ROAD's east vertex stood, raised). Forks, v = A0+1..NOSE-1 and TAIL+1..A1-1: ROAD's three "
                        "vertices keep their place and take fork_y (west, centre, east): the tilt easing in from the flat outer row.",
                "v": list(TWO),
                "sb_west": [[round(c, 4) for c in at(v, west(v), edge_y["sb_west"][v])] for v in TWO],
                "sb_line": [[round(c, 4) for c in at(v, main_off[v], main_y[v] + LIFT)] for v in TWO],
                "sb_east": [[round(c, 4) for c in at(v, sb_east[v], edge_y["sb_east"][v])] for v in TWO],
                "nb_west": [[round(c, 4) for c in at(v, nb_west[v], edge_y["nb_west"][v])] for v in TWO],
                "nb_line": [[round(c, 4) for c in at(v, lap_off[v], lap_y[v] + LIFT)] for v in TWO],
                "nb_east": [[round(c, 4) for c in at(v, east(v), edge_y["nb_east"][v])] for v in TWO],
                "offsets_m": {"sb_west": [round(west(v), 4) for v in TWO], "sb_line": [round(main_off[v], 4) for v in TWO],
                              "sb_east": [round(sb_east[v], 4) for v in TWO], "nb_west": [round(nb_west[v], 4) for v in TWO],
                              "nb_line": [round(lap_off[v], 4) for v in TWO], "nb_east": [round(east(v), 4) for v in TWO]},
                "fork_v": [v for v in ZONE if not NOSE <= v <= TAIL and v not in (A0, A1)],
                "fork_y": [[round(edge_y["sb_west"][v], 4), round(centre_y[v], 4), round(edge_y["nb_east"][v], 4)]
                           for v in ZONE if not NOSE <= v <= TAIL and v not in (A0, A1)]},
       "built_line_y": [round(P0[v][1], 4) for v in ZONE],
       "frame": {"_doc": "the BUILT line around the zone, per centreline vertex: its point (engine x, y, z), its left normal "
                         "(nx, nz: + = west on College), half the built width and the station. Scene vertices are told apart "
                         "by station and offset in THIS frame (the built objects were swept in it).",
                 "from_v": FRAME[0], "to_v": FRAME[1],
                 "x": [round(P0[v][0], 4) for v in range(FRAME[0], FRAME[1] + 1)],
                 "y": [round(P0[v][1], 4) for v in range(FRAME[0], FRAME[1] + 1)],
                 "z": [round(P0[v][2], 4) for v in range(FRAME[0], FRAME[1] + 1)],
                 "nx": [round(frame(v)[0], 6) for v in range(FRAME[0], FRAME[1] + 1)],
                 "nz": [round(frame(v)[1], 6) for v in range(FRAME[0], FRAME[1] + 1)],
                 "half_w": [round(0.5 * W0[v], 4) for v in range(FRAME[0], FRAME[1] + 1)],
                 "s_m": [round(S0[v], 3) for v in range(FRAME[0], FRAME[1] + 1)]},
       "lap_zone": {"_doc": "the Speedway lap through the zone, one point per mainline station (south join, the piece, north join)",
                    "from_v": A0, "to_v": A1, "offset_m": [round(lap_off[v], 3) for v in ZONE],
                    "points_xyz_m": [[round(c, 4) for c in lap_zone[v]] for v in ZONE]},
       "mainline": {"from_v": A0, "to_v": A1, "points_xyz_m": [[round(c, 4) for c in P1[v]] for v in range(A0, A1 + 1)],
                    "widths_m": [round(W1[v], 3) for v in range(A0, A1 + 1)], "offset_m": [round(main_off[v], 3) for v in range(A0, A1 + 1)]}}
(HERE / "college_split.data.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
# the datum's offset from the lidar, station by station (the Mac, 2026-11-23): the heights here are NOT measured heights
datum = {"what": "College split: how far the height datum (the BUILT west pavement edge, kept in place and height) stands off the "
                 "lidar, per centreline vertex. Every height the split builds carries this offset; only the SHAPE across the "
                 "road (each carriageway's crossfall, the northbound road's rise) is measured.",
         "lidar_there": "college_design.json's section at the built west edge: the lidar averaged over about 15 m, read half a "
                        "metre inside the measured southbound outer edge and held flat outside it (the built edge stands about "
                        "2 m outside the measured one)",
         "built_height_from": "not established. The built line is within 0.4 m of data/centerline.elevation.json's profile (3DEP "
                              "on the raw centreline of the one slab, 33 m median, smoothed twice over 39 m) through this zone but "
                              "is not that profile; which later step set it is unknown. The built rows are flat across at the "
                              "line + 0.10.",
         "follow_up": "on the list for after College, not part of this round",
         "columns": ["v", "s_m (along the built line)", "built_west_edge_y", "lidar_y_there", "built_minus_lidar_m"],
         "rows": [[v, round(S0[v], 1), round(P0[v][1] + LIFT, 3), round(surface(v, west(v)), 3),
                   round(P0[v][1] + LIFT - surface(v, west(v)), 3)] for v in ZONE]}
dd = [r[4] for r in datum["rows"]]
datum["summary"] = {"min_m": min(dd), "max_m": max(dd), "median_m": sorted(dd)[len(dd) // 2],
                    "at_the_two_outer_rows_m": [dd[0], dd[-1]]}
(HERE / "college_datum_offset.json").write_text(json.dumps(datum, indent=1), encoding="utf-8")
print(json.dumps(report, indent=1))

if WRITE:
    def keep(p):
        b = p.with_name(p.name + ".pre-split")
        if not b.exists():
            shutil.copy2(p, b)

    def load(name):
        p = data / name
        b = p.with_name(p.name + ".pre-split")
        return p, json.loads((b if b.exists() else p).read_text(encoding="utf-8"))

    p, j = load("centerline.local.json")
    keep(p)
    j["points_xyz_m"] = [[round(c, 4) for c in q] for q in P1]
    j["widths_m"] = [round(w, 3) for w in W1]
    p.write_text(json.dumps(j), encoding="utf-8")
    for name in ("finished_centerline.json", "gate_centerline.json"):
        p, j = load(name)
        keep(p)
        old = j["points_xyz_m"]
        sgn = 1.0 if abs(old[A0][2] - P0[A0][2]) < 1e-3 else -1.0          # finished carries z negated, gate does not
        if abs(old[A0][2] - sgn * P0[A0][2]) > 1e-3 or abs(old[A0][0] - P0[A0][0]) > 1e-3:
            raise SystemExit(f"{name}: v{A0} is not the centreline's point in either z sign")
        for v in range(A0 + 1, A1):
            old[v] = [round(P1[v][0], 4), round(P1[v][1], 4), round(sgn * P1[v][2], 4)]
            j["widths_m"][v] = round(W1[v], 3)
        p.write_text(json.dumps(j), encoding="utf-8")
    p, j = load("median_bands.json")
    keep(p)
    for v in range(ISLAND_OFF[0], ISLAND_OFF[1] + 1):
        j["island_w_by_vertex"][v] = 0.0
    runs = []                                    # the record of island runs follows: the College run is two runs now
    for r in j.get("runs") or []:
        if r["i"] < ISLAND_OFF[0] and r["j"] > ISLAND_OFF[1]:
            runs += [dict(r, j=ISLAND_OFF[0] - 1), dict(r, i=ISLAND_OFF[1] + 1)]
        else:
            runs.append(r)
    j["runs"] = runs
    p.write_text(json.dumps(j), encoding="utf-8")
    p, j = load("connectors.local.json")
    keep(p)
    conns = j["connectors"] if isinstance(j, dict) and "connectors" in j else j
    conns[:] = [c for c in conns if c.get("name") != PIECE] + [out["piece"]]
    p.write_text(json.dumps(j), encoding="utf-8")
    # the east lamps: the scene step (college_ground_blend.py) raised every lamp part east of the built line by what the
    # road's east edge rose at its place; the lamp data follows by the same rule, per lamp, or tools/check_lights_ini.py
    # finds no light at a recorded lens
    lp = data / "lights.local.json"
    if lp.exists():
        _p, LJ = load("lights.local.json")
        keep(lp)
        rise_row = {v: (edge_y["nb_east"][v] - (P0[v][1] + LIFT)) for v in ZONE}

        def rise_at(x, z):
            """(row, offset from the built line, the east edge's rise interpolated along the road) at a plan point"""
            v = min(range(FRAME[0], FRAME[1] + 1), key=lambda q: (P0[q][0] - x) ** 2 + (P0[q][2] - z) ** 2)
            nx, nz = frame(v)
            dx, dz = x - P0[v][0], z - P0[v][2]
            off, al = dx * nx + dz * nz, dx * nz - dz * nx
            v2 = v + (1 if al >= 0 else -1)
            seg = math.hypot(P0[v2][0] - P0[v][0], P0[v2][2] - P0[v][2]) or 1.0
            t = min(1.0, abs(al) / seg)
            return v, off, rise_row.get(v, 0.0) * (1.0 - t) + rise_row.get(v2, 0.0) * t

        lens = LJ.get("provenance", {}).get("lens_xyz") or []
        raised = []
        for i, head in enumerate(LJ.get("lampheads") or []):
            base = (LJ.get("lamp_bases_xz") or [])[i] if i < len(LJ.get("lamp_bases_xz") or []) else (head[0], head[2])
            v, off, _r = rise_at(base[0], base[1])
            if not A0 < v < A1 or off >= 0.0 or math.hypot(base[0] - P0[v][0], base[1] - P0[v][2]) > 40.0:
                continue                           # only lamps whose foot stands east of the built line on the zone's rows
            rec = {"lamp": i, "v": v, "base_offset_m": round(off, 2)}
            r_head = rise_at(head[0], head[2])[2]
            rec["head_y_was"], head[1] = head[1], round(head[1] + r_head, 4)
            rec["head_y"] = head[1]
            if i < len(lens):
                r_lens = rise_at(lens[i][0], lens[i][2])[2]
                rec["lens_y_was"], lens[i][1] = lens[i][1], round(lens[i][1] + r_lens, 4)
                rec["lens_y"], rec["rise_m"] = lens[i][1], round(r_lens, 3)
            for row in (LJ.get("seat_check") or {}).get("rows") or []:
                if row.get("lamp") == i:
                    r_base = rise_at(base[0], base[1])[2]
                    for key in ("base_y", "ground_y", "foot_y"):
                        if isinstance(row.get(key), (int, float)):
                            row[key] = round(row[key] + r_base, 3)
            raised.append(rec)
        LJ["college_split"] = {"_doc": "the east lamps on College rose with the walk they stand on (ledger 0055 round 2; "
                                       "source/college_r2/college_split_data.py): head, lens and the seat check's heights",
                               "raised": raised}
        lp.write_text(json.dumps(LJ), encoding="utf-8")
        print(f"[lights] {len(raised)} east lamps raised in data/lights.local.json, by {min(r['rise_m'] for r in raised):.2f} to {max(r['rise_m'] for r in raised):.2f} m")
    # the released ground: the zone that held the old cut now holds the whole split (the prep leaves released ground as
    # the scene has it: the bank's top and the east shelf are authored, not feathered)
    gp = data / "ground_release.json"
    if gp.exists():
        _p, GJ = load("ground_release.json")
        keep(gp)
        for z_ in GJ.get("zones") or []:
            if z_.get("name") == "college_split_cut":
                z_["s_m"] = [round(S1[A0], 1), round(S1[A1], 1)]
                if "v" in z_:
                    z_["v"] = [float(A0), float(A1)]
                print(f"[release] zone college_split_cut -> s {z_['s_m']} (rows v{A0}..v{A1}), sides {z_.get('sides')}, reach {z_.get('reach_m')} m")
        gp.write_text(json.dumps(GJ), encoding="utf-8")
    keep(cfg_path)
    c2 = json.loads(cfg_path.with_name(cfg_path.name + ".pre-split").read_text(encoding="utf-8"))
    c2.setdefault("race", {}).setdefault("laps", {})[LAP] = lap
    cfg_path.write_text(json.dumps(c2, indent=2), encoding="utf-8")
    print("[written]", proj)
