"""Write AC ``fast_lane.ai`` (v7) offline from the engine's racing line — R2's keystone.

No k10 track ships an AI line, so nothing can drive them but a human, so no automated in-game
test exists (REALISM.md §7). This retires that: the engine already holds the line in world metres
(``data/finished_centerline.json``: ``points_xyz_m`` + ``widths_m``, the BUILT swept line), and
the .ai binary is documented (fleet/reference/RESEARCH.md §B6, verified against gro-ove/actools
AcTools/AiFile):

    header  : 4×i32   version=7, pointCount, lapTime_ms, sampleCount
    points  : N×20 B  position 3×f32, cumulative length f32, id i32
    extras  : i32 N, then N×18×f32: speed, gas, brake, obsoleteLatG, radius, sideLeft, sideRight,
              camber, direction, normal xyz, length, forwardVector xyz, tag, grade
    trailer : i32 hasGrid (0 — AC/ksEditor rebuilds derived data; see the re-save caveat in B6)

Measured floor (fleet/reference/MEASURED.md §2): every reference ships ~1.5 m point spacing; the
freeroam/traffic trick is ``pit_lane.ai`` = copy of ``fast_lane.ai`` (how point-to-point roads get
working AI). Speed profile is physics-derived from curvature (lat-g cap + braking/accel passes) —
a hypothesis generator: whether the AI actually laps is decided in game, by the harness (rule 0).

    python -m scripts.ac.write_ai_line <project-dir>                    # -> <project>/ai/
    python -m scripts.ac.write_ai_line <project-dir> --layout race_cw   # -> <project>/ai/race_cw/
    python -m scripts.ac.write_ai_line <project-dir> --install <AC-track-dir>
    python -m scripts.ac.write_ai_line <centerline.json> --out <dir> --spacing 1.5

STATUS — READ THIS BEFORE TRUSTING A FILE THIS WRITES (docs/HANDOFF.md:250-255, :284; V3-PLAN:297).
HANDOFF bans *generating AI splines from GPS data* and says to record them in-game. Every line this
module writes is a GENERATED DRAFT from the BUILT centreline (the mesh-frame line the ribbon was
swept along — not lat/lon), with exactly the provenance of the line every V3 install ships today.
It sits under OPEN ledger 0023 (a generated line launches but has never been proven to lap). It
exists so a layout is testable on first load (CSP auto-drive, Race mode reachable). The end state
per HANDOFF is one in-game recording per layout — CSP's recorder writes ``fast_lane.ai.candidate``
into the SELECTED layout's ``<id>/ai/`` — replacing the draft file-for-file. No DoD tier is claimed
on a draft; every draft dir carries an ``ai_draft.json`` saying so.

FRAMES (measured 2026-10-10 on the SD workshop, see ``_to_engine_frame``): the loop prep writes
``finished_centerline.json`` in the KN5 frame (z = −engine z; v0 at z=+1662 while
``centerline.local.json`` has −1662), the July writer's input was the ENGINE frame, and this writer
flips z exactly once at the end. Reading a kn5-frame line and flipping it would ship the ghost
mirror route of ledger 0023, so the input is normalised to the ENGINE frame (x=E, y=up, z=N) first
by comparing it against ``centerline.local.json``; every lane offset and side distance is computed
there (right of travel = (tz, −tx)), then the whole line is mirrored to the kn5 frame once.

LAYOUTS (ledger 0047, three versions of Lake Murray): ``--layout <id>`` takes the direction and the
race-furniture flag from ``track.config.json`` ``layouts[]``, writes ``<project>/ai/<id>/``, and —
with ``--lane-offset auto`` (default) — moves the line into the right-hand carriageway wherever a
divider is declared: a median island (``data/median_bands.json`` ``island_w_by_vertex``) in every
layout, plus the centre barrier chain and the kerb-line barrier inset (``data/barrier_bands.json``
``centre_w_by_vertex`` / ``edge_inset_by_vertex``, written by tools/barrier_bands.py) only for
layouts that load the race kn5 (``race_furniture: true``). The lane POLICY (GEOMETRY below shapes the
line from it) = the centre of the lane between the
divider face + 0.4 m and the outer barrier face − 0.4 m (17 m road beside the 0.67 m chain with
0.82 m inset: (0.735 + 7.28) / 2 = 4.0 m); 0 where no divider stands (Alvarado: the whole street in
both directions). sideLeft/sideRight become the asymmetric distances to the nearer boundary minus
the margin. A reverse layout is the reversed traversal with its OWN right-of-travel offset — a
distinct file, never a byte-reversed one (every reference's reverse line is a distinct file).
A write-time self-check refuses any line point within 0.6 m of a declared barrier face (or, with no
inset declared, the pavement edge) or on an island, measured against the per-vertex declaration (the
nearest declared segment, not the resampled channels).

GEOMETRY (ledger 0047 fix round, 2026-10-11 — the audit of the installed three-version build). The
lane-offset line is post-processed in the ENGINE frame, before the single kn5 flip:
  1. RAMPS (``ramp_offsets``): every change of the lane offset is a cosine taper of
     ``ramp_length_m`` (>= 40 m, 10 m per metre of change) — the street draft stepped sideways
     21-27 deg in one 1.5 m station at twelve island noses. Into / out of a divider the taper lies
     wholly on the undivided side; an undivided gap too short for both tapers holds the lane across it.
     ``corner_approach``: a divided-lane line deep on the inside of a corner tighter than CORNER_R_M
     (race_cw's three chained right-handers, lane 5.8-7.3 m inside R 7.4-8.2 m) moves to the outside
     of its comfort lane through the corner, with the same tapers either side (outside, apex, outside).
  2. LOOPS (``trim_loops``): where the offset exceeds the centreline's local radius the offset curve
     swallowtails — race_cw shipped a 0.09 m step with a 67 deg turn at College -> Navajo, R 0.3 m,
     7 km/h. The backward points are dropped and the entry and exit legs joined at their crossing (or
     their extensions' meeting point) — the logic of tools/race_furniture._trim_folds, which trims the
     curb barrier at the same corners. (Lane normals now come from a ±3 m chord, TANGENT_SPAN, which
     with the corner approach leaves Lake Murray nothing to trim; the trim stays as the guarantee.)
  3. CURVATURE: every point stays inside its lane — race: divider face + 0.6 m .. curb-strip face −
     0.6 m; street: off every island, inside the pavement − 0.6 m (plus CORRIDOR_TOL_M inside both) —
     and the radius through any three consecutive points is >= its floor, min(the road's own centreline
     radius at that place, RADIUS_FLOOR_M = 12 m). ``fillet_corners`` replaces each violating corner
     with straight-arc-straight, the largest radius <= 12 m (x 1.05) that keeps every new point in the
     comfort lane (FILLET_COMFORT_CLEAR_M off every face: the line is a ~1.9 m car's centre), else the
     hard lane; ``bound_curvature`` (Taubin smoothing, best state kept) cleans up what is left. At
     1.5 m spacing the floor is also "no turn > 10 deg between consecutive points" wherever the road is
     wider than R 8.6 m; only where the road itself is that tight may a step turn more. Then the line is
     resampled at the spacing (and cleaned once more, normal moves only) and speeds/sides recomputed.
  4. START (``_rotate_to``): a closed line starts AT the start/finish line — point 0 is the AC_TIME_0
     midpoint (``data/dummies_<layout>.json``, else ``dummies.json``) projected onto the line, and the
     lap-length field restarts at 0 there (every install shipped point 0 at the lap seam v0, 300 m
     before the line: race_cw's line sat at spline index 598, race_acw's at 8394).
The write-time self-check also refuses a backward step, a self-crossing, a turn over TURN_MAX_DEG where
the road is not that tight, or a radius under the floor. None of this makes the line a recording: it is
still a GENERATED DRAFT, and whether the AI laps on it is decided in game.

RACE CORRIDORS (ledger 0049, 2026-10-11 — Kevin: "the entire other lane blocked off", "an Alvarado's width
for the entire track", full intersections open at the corners the race turns at). When the bands file is
version 2 it declares ``corridors.<layout id>`` and a race layout drafts inside THAT, not the retired centre
chain (a version-1 file keeps the 0047 lane above, byte for byte; a version-2 file without the layout
refuses):
  * LANE: ``lane_by_vertex`` = [y_lo, y_hi], the two wall FACES (forward-left metres) — the race-side curb
    strip and this direction's closure, the whole street in ``whole`` / ``box`` / ``pin`` zones —
    stopped at an authored median island (author_median_blend's outline, nose taper included). The target
    is the lane centre (~2 m right of the centreline on a 17 m road, 0 on Alvarado, the I-8 deck and in a
    box), smoothed by corridor_offsets (bounded least squares, CORRIDOR_MU_M) so funnels and convergences
    are tapers.
  * OPEN CORNERS (the declared ``corners`` whose apex zone is open, turning <= BOX_TURN_MAX_DEG — on SD the
    seam and the three boxes; the 177 deg hairpin keeps the floor fillet): box_targets holds the corridor's
    OUTSIDE comfort edge from BOX_APPROACH_M before the corner's arc (PC − 2 .. PT + 2) to its end, as a
    slope-limited envelope (BOX_EDGE_SLOPE: a funnel face is not chased); box_fillets then lays the LARGEST
    straight-arc-straight the box allows, every point of it (walked every CHECK_STEP_M) FILLET_COMFORT_
    CLEAR_M off every face — the apex lands that far off the trimmed inside corner X. RADIUS_FLOOR_M stays
    the floor everywhere else.
  * REFUSALS (on top of the ones above): any point of the line — walked every CHECK_STEP_M, not only at its
    points — past a face (beyond a closure, in a side street), on an authored island, or < CHECK_CLEAR_M
    from a face (funnels, island faces, the trimmed inside corners) or a sealed mouth line
    (check_corridor, on CorridorFaces: the faces as fold-trimmed polylines on the walls' own vertex frame).
  * sideLeft / sideRight are the distances to the two faces minus the margin; ai_draft.json carries a
    ``corridor`` block: wall clearance minimum and where, island and mouth minima, points in an open box,
    per corner the arc radius / speed / approach speed, min radius, min target speed, start index 0 and
    the grid's index behind it. Still GENERATED DRAFTS: ledger 0023 stays open, no tier is claimed,
    pit_lane.ai stays a copy, the street layout's line is unchanged.

AC'S PAYLOAD, OFF THE K-RAIL, NO PHANTOM BENDS (ledger 0052, 2026-10-12 — Kevin: "ai races need tuning, they tend
to crash and slow down weirdlu"). OPT-IN per track and layout: ``track.config.json`` ``ai`` (load_ai_opts; absent,
or the layout not in ``ai.layouts`` = every line above, byte for byte — tests/ac/test_write_ai_line_payload.py):
  * ``payload: "kunos"`` — the per-point extras mean what they mean on every Kunos / third-party line on this PC
    (186 measured): ``length`` = the 3D segment from the previous point (not the lap distance), ``direction`` = +-1
    (-sign of the LOCAL heading change, +-DIRECTION_WINDOW_PTS = 1 point, kn5 frame; never 0), ``normal`` = the
    BUILT road's normal under the point, ``camber`` = its tilt measured toward the bend: -direction x
    asin(normal . right) (the sign rule every reference line follows, 0.95-1.00 of tilted points), ``radius`` = the
    plain 3-point circumradius of the float32 points; header lapTime = sampleCount = 0 (kunos_payload, write_ai).
    The point record keeps the cumulative lap distance.
  * ``wall_clear_m`` — a corridor line's comfort clearance (box approach, box arcs, floor fillets) instead of
    FILLET_COMFORT_CLEAR_M 1.5: the v0.17.1 lines passed 1.50 m from the K-rail three times per box.
  * ``fair`` — fair_line on the final line: least change of curvature plus a minimum-curvature pull, every point moved
    only along its normal, inside bounds that keep it wall_clear + FAIR_CLEAR_EXTRA_M off every face (never closer
    than it stood), then a light polish. The approach S-wiggles, the straight-to-arc steps and the resample's point
    jitter were the 160 / 875 places the AI was told to brake for a bend the line does not have.
  * ``surface: "gate_obj"`` (or ``--surface-obj``) — the layout's BUILT gate OBJ (data/track.<layout>.obj,
    scripts.ac.ai_built): every point seated on the 1ROAD surface (its height and normal), and sideLeft / sideRight
    clamped at the first built 1WALL a perpendicular ray meets, minus the margin. A missing OBJ, or one older than a
    kn5 its header names, refuses the line.
The written line is then judged by tools/verify_ai_line.py against the same BUILT OBJ (L5). Still a GENERATED DRAFT
(0023): an in-game recording replaces it file-for-file.

L13 applies: a closed lap repeats its first vertex — detect, drop the duplicate, and wrap every
neighbour/distance computation; an open stage wraps nothing.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
from pathlib import Path

G = 9.81
DIVIDER_MARGIN_M = 0.4      # the lane starts this far off a divider face (drive_test's lane margin)
EDGE_MARGIN_M = 0.4         # ... and ends this far off the kerb-line barrier face
LINE_MIN_CLEAR_M = 1.0      # the line itself is never authored closer than this to either face
CHECK_CLEAR_M = 0.6         # write-time self-check: refuse a point closer than this to a face
CORRIDOR_TOL_M = 0.1        # the curvature smoother's lane sits this much inside the self-check's
RAMP_MIN_M = 40.0           # every lane-offset change is a cosine taper at least this long ...
RAMP_M_PER_M = 10.0         # ... and this many metres per metre of change (max heading change ~9 deg)
RAMP_STEP_M = 0.3           # a lane-target jump bigger than this between stations is a step to taper
TANGENT_SPAN = 2            # lane normals from base[i-2] -> base[i+2]: a vertex kink no longer jumps them
FOLD_SEARCH_PTS = 40        # a swallowtail's legs are searched this many points either side of it
FOLD_MERGE_PTS = 6          # backward steps this close together are one fold
FOLD_EXTEND_MAX_M = 12.0    # legs that never cross are extended to meet within this reach (each)
TURN_MAX_DEG = 10.0         # no step turns more than this, except where the road itself is that tight
RADIUS_FLOOR_M = 12.0       # the line's radius floor is min(the road's centreline radius there, this)
RADIUS_TOL = 0.02           # fillets + the first smoothing pass treat a radius under (1 + this) x floor as a violation
RADIUS_TOL_FINAL = 0.0      # ... the pass on the resampled line, under the floor itself
FILLET_MARGIN = 0.05        # a fillet's radius is >= (1 + this) x the floor (never re-flagged), <= (1 + this) x 12 m
CORNER_R_M = 20.0           # a divided-lane line on the inside of a corner tighter than this ...
CORNER_FRAC = 0.35          # ... and deeper than this fraction of its radius takes it from the lane's outside
FILLET_COMFORT_CLEAR_M = 1.5  # a fillet first tries to stay this far off every face (a car is ~1.9 m wide: the
                              # line is its centre); only when no radius >= the floor fits does it use the lane's
                              # hard CHECK_CLEAR_M + CORRIDOR_TOL_M
RADIUS_CHECK = 0.95         # the self-check refuses a radius under this fraction of the floor
ROAD_R_SPAN = 2             # road radius through base[i-2], base[i], base[i+2] (~6 m chord) ...
ROAD_R_WIN = 3              # ... and its minimum over +-3 stations + the point's lateral offset (the apex)
SMOOTH_DILATE = 5           # points either side of a violation that the smoother moves with it
SMOOTH_LAMBDA = 0.5         # Taubin pair: a Laplacian step toward the neighbours' midpoint ...
SMOOTH_MU = -0.53           # ... then one back (|mu| > lambda): kinks are removed, bends are not shrunk
SMOOTH_MAX_ITERS = 4000
SMOOTH_STALL_ITERS = 200    # stop when the violations have not improved for this many iterations
RACE_PREFIXES_DOC = "1WALL_RACE / 1KERB_RACE (the race-furniture kn5 the race layouts load)"
# --- race corridors (ledger 0049: an Alvarado-wide lane per direction, open boxes at the corners) -----
CORRIDOR_MU_M = 25.0        # INVENTED: the lane-centre target is pulled toward the lane centre over this length
                            # (bounded least squares; a lateral change of d metres tapers over ~2-3 x this)
CORRIDOR_SOR_OMEGA = 1.8    # over-relaxation of that solve (the corridor solver's own value)
CORRIDOR_SOR_TOL_M = 1e-5
CORRIDOR_SOR_MAX = 6000
FACE_STEP_M = 1.0           # the wall faces are densified on the declared curve to this spacing before the trim
FACE_CELL_M = 4.0           # spatial index cell of the face segments
FACE_REACH_CELLS = 12       # a point with no face within 48 m is outside the corridor
ISLAND_REACH_CELLS = 2      # ... and one with no island edge within the widest island's half-width + 8 m is outside
                            # every island
BOX_TURN_MAX_DEG = 170.0    # a corner turning more than this (the hairpin, 177 deg) keeps the floor fillet
BOX_APPROACH_M = 60.0       # INVENTED: the target holds the corridor's OUTSIDE comfort edge from this far before
                            # the corner's arc (PC - 2) to its end (PT + 2) — turn in from outside, exit wide in the box
BOX_EDGE_IN_M = 0.25        # ... that far inside the comfort edge, so a fillet's end point stands in the comfort lane
                            # measured on the faces too (the line's station normals and the walls' vertex normals
                            # differ by centimetres)
BOX_EDGE_SLOPE = 0.10       # INVENTED: the held outside edge never moves sideways faster than this per metre — a
                            # funnel face diverging 1:3.3 into a box is not chased (that flick was a 58 km/h bend
                            # before an 88 km/h corner); the envelope only ever moves the target INTO the lane
BOX_R_MAX_M = 150.0         # the box arc search: the largest radius tried, then down a geometric ladder ...
BOX_R_LADDER = 0.92         # ... of this ratio to the floor fillet (feasibility is NOT monotone in R: a small arc
                            # hugs the box's outside corner, a big one cuts toward the inside corner X) ...
BOX_R_BISECT = 8            # ... then bisected between the largest feasible rung and the one above it
CHECK_STEP_M = 0.25         # a line is judged against the faces every this many metres ALONG it, not only at its
                            # points: the binding constraint of a box arc is the trimmed inside corner X, a sharp
                            # convex vertex the chord between two 1.5 m points can pass much closer than either
BOX_WINDOW_PTS = (3, 6, 10, 15, 21, 28, 36, 45, 55, 66, 78, 92, 108)   # fillet ends this many points before /
                                                                       # after the corner's arc, independently
BOX_PAD = 2                 # the corner's arc = the declared corner PC - 2 .. PT + 2 (the spec's box rule)
OPEN_ZONES = ("whole", "box", "pin")   # zone_by_vertex values where the lane is the whole street
# --- ledger 0052 (opt-in per track: track.config.json "ai"; absent = every line above, byte for byte) ------
FAIR_W = 1e-6               # INVENTED: fair_line's hold on the input line (swept on SD race_cw: 1e-4 kept every
                            # gentle road S — 1.49 bend flips / km; 1e-5 alone left 15 spurious dips)
FAIR_ALPHA = 1e-2           # INVENTED: fair_line's weight on curvature itself — a minimum-curvature pull inside the
                            # bounds (swept: 1e-3 left 0.82 flips / km; 3e-2 pressed the line onto its bounds, 32 dips)
FAIR_U_MAX_M = 3.0          # INVENTED: fair_line never moves a point further than this along its normal
FAIR_PAD_PTS = 120          # a closed lap is faired as an open chain padded this far round the seam each way
FAIR_PIN_W = 1e6            # a point held at its bound (the active set) is held with this weight
FAIR_ACTIVE_ITERS = 60      # active-set iterations per solve
FAIR_RADIUS_ROUNDS = 24     # re-solves after pulling back the bounds around a radius the fairing tightened. INVENTED;
                            # was 12, which v0.18.0's race_acw outran (ledger 0046 integration fix round: 12 rounds left 9
                            # box points tightened, the polish 4, and a 5-point kink at the v1514 box exit that
                            # verify_ai_line V3 filed as a 12.9 % phantom dip); it converges at 18. race_cw: 5 rounds
FAIR_PROBE_M = 0.25         # a point's bound along its normal: marched at this step, then bisected ...
FAIR_BOUND_SMOOTH_PTS = 4   # ... then made a smooth conservative envelope over +-this many points (min, mean, x2)
FAIR_POLISH_W = 1e-4        # INVENTED: the polish after the fairing (point-scale only: wiggles under ~30 m) ...
FAIR_POLISH_U_M = 0.3       # ... on a 0.3 m leash
FAIR_CLEAR_EXTRA_M = 0.5    # INVENTED: the fairing keeps wall_clear + this off every face (it never moves a point
                            # closer than that unless it already was): the band the gate counts stays empty
BOX_RULE_KEEP = 0.85        # INVENTED (the 0052 diagnosis' pre-declared box rule): the writer REFUSES a faired line
                            # whose box corner falls under this x the v0.17.1-rule arc (FAIR_BOX_KEEP is the target)
FAIR_BOX_KEEP = 0.86        # INVENTED (the 0052 diagnosis' box rule, 0.85, + 1 % margin): every point within a box
                            # corner's stations +- FAIR_BOX_GUARD_PTS (30 m) keeps its car-scale radius (through the
FAIR_BOX_GUARD_PTS = 20     # points +- FAIR_CAR_PTS, +-6 m) >= this x the arc the v0.17.1 rule (comfort
FAIR_CAR_PTS = 4            # FILLET_COMFORT_CLEAR_M) lays at that corner (or the faired line's own, if already tighter)
DIRECTION_WINDOW_PTS = 1    # payload direction = -sign(heading change over +-1 point) — MEASURED: the 33 Kunos lines
DIRECTION_MIN_DEG = 0.5     # agree on 99.77-100 % of points turning > 0.5 deg there (at +-10 only 96.8-99.5 %)


# --- resampling ----------------------------------------------------------------

def _resample(pts: list[list[float]], widths: list[float], spacing: float, closed: bool,
              extra: list[list[float]] | None = None, lerp_extra: tuple[int, ...] = ()):
    """Linear resample of the polyline (+widths, + any per-vertex channels) to ~spacing metres.

    Returns (pts, widths, ds) — or (pts, widths, ds, extras) when ``extra`` channels are given.
    Every channel is index-aligned with ``pts``. Widths interpolate linearly; the ``extra``
    channels are DECLARATIONS (divider half-width, barrier inset) and take the larger of the two
    bracketing vertices, so a station between an open vertex and a divider vertex is already
    judged as the divider's — the same nearest-vertex reading the write-time check applies.
    ``lerp_extra`` lists the extra channels (by index into ``extra``) that interpolate linearly
    instead: a race corridor's face laterals (ledger 0049), because the walls themselves are authored
    on the lerp of the declared laterals between two vertices (tools/race_furniture.offset_xz)."""
    n = len(pts)
    seg = []
    total = 0.0
    m = n if not closed else n  # closed input arrives WITHOUT the duplicate vertex
    for i in range(m - (0 if closed else 1)):
        a, b = pts[i], pts[(i + 1) % n]
        d = math.dist(a, b)
        seg.append(d)
        total += d
    count = max(8, round(total / spacing))
    step = total / count
    chans = [widths] + list(extra or [])
    out_p = []
    out_c: list[list[float]] = [[] for _ in chans]
    i, acc = 0, 0.0
    tgt = 0.0
    steps = count if closed else count + 1
    for _ in range(steps):
        while i < len(seg) and acc + seg[i] < tgt - 1e-9:
            acc += seg[i]; i += 1
        if i >= len(seg):
            out_p.append(list(pts[-1] if not closed else pts[0]))
            for c, ch in enumerate(chans):
                out_c[c].append(ch[-1] if not closed else ch[0])
        else:
            t = (tgt - acc) / seg[i] if seg[i] > 1e-12 else 0.0
            a, b = pts[i], pts[(i + 1) % n]
            out_p.append([a[k] + (b[k] - a[k]) * t for k in range(3)])
            for c, ch in enumerate(chans):
                ca, cb = ch[i], ch[(i + 1) % n]
                out_c[c].append(ca + (cb - ca) * t if (c == 0 or (c - 1) in lerp_extra) else max(ca, cb))
        tgt += step
    if extra is None:
        return out_p, out_c[0], step
    return out_p, out_c[0], step, out_c[1:]


def _circumradius(a, b, c) -> float:
    """Radius through three XZ points (planar — banking/grade handled separately)."""
    ax, az, bx, bz, cx, cz = a[0], a[2], b[0], b[2], c[0], c[2]
    d = 2.0 * (ax * (bz - cz) + bx * (cz - az) + cx * (az - bz))
    if abs(d) < 1e-9:
        return 10000.0
    ux = ((ax * ax + az * az) * (bz - cz) + (bx * bx + bz * bz) * (cz - az)
          + (cx * cx + cz * cz) * (az - bz)) / d
    uz = ((ax * ax + az * az) * (cx - bx) + (bx * bx + bz * bz) * (ax - cx)
          + (cx * cx + cz * cz) * (bx - ax)) / d
    return min(10000.0, math.hypot(ax - ux, az - uz))


# --- lane policy -----------------------------------------------------------------

def lane_offsets(widths: list[float], dh: list[float], inset: list[float]) -> list[float]:
    """Right-of-travel offset of the line at each station, from the declared divider half-width
    ``dh`` (island half or centre-chain half, 0 = none) and the kerb-line barrier ``inset``.

    With a divider the line runs down the centre of the right-hand lane — between the divider face
    + DIVIDER_MARGIN and the outer face − EDGE_MARGIN — and is never authored closer than
    LINE_MIN_CLEAR_M to either face (a lane too narrow for both clearances gets its midpoint).
    Without one the line stays on the centreline (0): a 13 m street is driven whole both ways."""
    out = []
    for w, d, s in zip(widths, dh, inset):
        if d <= 0.0:
            out.append(0.0)
            continue
        face_in, face_out = d, w / 2.0 - s
        o = ((face_in + DIVIDER_MARGIN_M) + (face_out - EDGE_MARGIN_M)) / 2.0
        lo, hi = face_in + LINE_MIN_CLEAR_M, face_out - LINE_MIN_CLEAR_M
        o = (face_in + face_out) / 2.0 if lo > hi else min(max(o, lo), hi)
        out.append(o)
    return out


def lane_corridor(widths, dh, inset, clear: float) -> tuple[list[float], list[float]]:
    """(lo, hi): the right-of-travel bounds of the line's lane at every station, ``clear`` metres inside
    its faces. Beside a divider: divider face + clear .. kerb-line barrier face (the pavement edge when
    no inset is declared) − clear. Without one: the whole street, between the two barrier faces /
    pavement edges − clear. A lane too narrow for both clearances collapses to its midpoint."""
    lo, hi = [], []
    for w, d, s in zip(widths, dh, inset):
        face_out = w / 2.0 - s
        face_in = d if d > 0.0 else -face_out
        a, b = face_in + clear, face_out - clear
        if a > b:
            a = b = (face_in + face_out) / 2.0
        lo.append(a)
        hi.append(b)
    return lo, hi


# --- ramps (finding B: the lane offset stepped sideways at island noses / chain ends) ----------------

def _taper(u: float) -> float:
    """Cosine taper 0 -> 1 over u in [0, 1]: zero slope at both ends."""
    u = 0.0 if u < 0.0 else 1.0 if u > 1.0 else u
    return 0.5 - 0.5 * math.cos(math.pi * u)


def ramp_length_m(delta: float) -> float:
    """Length of the taper that moves the line ``delta`` metres sideways: RAMP_MIN_M, or RAMP_M_PER_M per
    metre of change when that is longer (a cosine taper's steepest heading change is then atan(pi / 20)
    ~ 9 deg, at any size)."""
    return max(RAMP_MIN_M, RAMP_M_PER_M * abs(delta))


def ramp_offsets(target: list[float], divided: list[bool], lo: list[float], hi: list[float], ds: float,
                 closed: bool) -> tuple[list[float], list[dict], int]:
    """Every change of the lane offset as a cosine taper (ledger 0047 fix round, finding B).

    ``target`` is the per-station lane policy (``lane_offsets``: the lane centre beside a divider, 0
    without one). It STEPS where a divider starts or ends (island noses, chain ends) and where a divider
    changes width at a butt joint (chain <-> island) — stepping the line sideways in one 1.5 m station
    was the 21-27 deg jog the street draft had at twelve island noses (26-36 km/h targets). Here:
      * into / out of a divider: a taper of ramp_length_m(lane value) lying wholly on the UNDIVIDED side,
        so the line is in its lane at the nose and stays in it until the divider ends;
      * an undivided gap too short for both tapers (a connector mouth between two islands): the line
        HOLDS its lane across it — one taper from the lane value before to the lane value after (wider
        than the gap only when that change needs it, then into both divided runs);
      * a step inside a divided run (a butt joint): a taper centred on the joint, shifted toward
        whichever side keeps every station inside [lo, hi].
    Width changes inside a run (gradual tapers in the declared widths) are left to the curvature pass.
    Returns (offsets, ramps, n_clamped): ``ramps`` describes each taper for ai_draft.json; n_clamped
    counts stations the result had to be clamped into [lo, hi] (0 on every layout measured)."""
    n = len(target)
    o = [float(v) for v in target]
    ramps: list[dict] = []
    if n < 3 or not any(divided):
        return o, ramps, 0
    wrap = (lambda i: i % n) if closed else (lambda i: min(max(i, 0), n - 1))

    def steps_for(delta: float) -> int:
        return max(2, int(math.ceil(ramp_length_m(delta) / ds)))

    def blend(k: int, r0: int, N: int, a: float, b: float, cur: list[float]) -> list[tuple[int, float]]:
        """Values over the unwrapped stations r0 .. r0 + N: the run left of the joint k (held at a past
        it) blended into the run right of it (held at b before it)."""
        out = []
        for j in range(N + 1):
            i = r0 + j
            if not closed and not 0 <= i < n:
                continue
            w = _taper(j / N)
            A = cur[wrap(i)] if i < k else a
            B = cur[wrap(i)] if i >= k else b
            out.append((i, (1.0 - w) * A + w * B))
        return out

    def feasible(win) -> bool:
        return all(lo[wrap(i)] - 1e-9 <= v <= hi[wrap(i)] + 1e-9 for i, v in win)

    # 1. butt joints inside divided runs
    ks = range(n) if closed else range(1, n)
    joints = [k for k in ks if divided[wrap(k - 1)] and divided[k]
              and abs(target[k] - target[wrap(k - 1)]) > RAMP_STEP_M]
    for k in joints:
        a, b = o[wrap(k - 1)], o[k]
        N = steps_for(b - a)
        cands = [k - N // 2]
        for sft in range(1, N // 2 + 1):
            cands += [k - N // 2 - sft, k - N // 2 + sft]
        snap = list(o)
        chosen = None
        for r0 in (r for r in cands if r <= k - 1 and r + N >= k):
            win = blend(k, r0, N, a, b, snap)
            if feasible(win):
                chosen = win
                break
        if chosen is None:
            chosen = blend(k, k - N // 2, N, a, b, snap)
        for i, v in chosen:
            o[wrap(i)] = v
        ramps.append({"kind": "joint", "station": k, "from_m": round(a, 2), "to_m": round(b, 2),
                      "len_m": round(N * ds, 1)})

    # 2. undivided runs (unwrapped start, length), scanned from a divided station on a closed lap
    runs: list[tuple[int, int]] = []
    s0 = next(i for i in range(n) if divided[i]) if closed else 0
    j = 0
    while j < n:
        if divided[(s0 + j) % n]:
            j += 1
            continue
        u0 = j
        while j < n and not divided[(s0 + j) % n]:
            j += 1
        runs.append((s0 + u0, j - u0))
    for u0, L in runs:
        p, q = u0 - 1, u0 + L
        has_p, has_q = closed or p >= 0, closed or q <= n - 1
        a = o[wrap(p)] if has_p else 0.0
        b = o[wrap(q)] if has_q else 0.0
        Na = steps_for(a) if has_p and abs(a) > 1e-9 else 0
        Nb = steps_for(b) if has_q and abs(b) > 1e-9 else 0
        if L >= Na + Nb:
            for jj in range(L):
                i = wrap(u0 + jj)
                if jj < Na:
                    w = _taper((jj + 1) / Na)
                    o[i] = (1.0 - w) * a + w * target[i]
                elif jj >= L - Nb:
                    w = _taper((L - jj) / Nb)
                    o[i] = (1.0 - w) * b + w * target[i]
            if Na:
                ramps.append({"kind": "leave", "station": wrap(u0), "from_m": round(a, 2), "to_m": 0.0,
                              "len_m": round(Na * ds, 1)})
            if Nb:
                ramps.append({"kind": "enter", "station": wrap(q), "from_m": 0.0, "to_m": round(b, 2),
                              "len_m": round(Nb * ds, 1)})
            continue
        # too short for both tapers: hold the lane across the gap
        N = steps_for(b - a)
        snap = list(o)
        win = None
        if N > L + 1:
            e = (N - (L + 1) + 1) // 2
            cand = []
            for jj in range(L + 1 + 2 * e + 1):
                i = p - e + jj
                if not closed and not 0 <= i < n:
                    continue
                w = _taper(jj / (L + 1 + 2 * e))
                A = snap[wrap(i)] if i <= p else a
                B = snap[wrap(i)] if i >= q else b
                cand.append((i, (1.0 - w) * A + w * B))
            if feasible(cand):
                win = cand
        if win is None:
            win = [(u0 + jj, a + (b - a) * _taper((jj + 1) / (L + 1))) for jj in range(L)]
        for i, v in win:
            o[wrap(i)] = v
        ramps.append({"kind": "hold", "station": wrap(u0), "from_m": round(a, 2), "to_m": round(b, 2),
                      "gap_m": round(L * ds, 1), "len_m": round(max(L + 1, len(win) - 1) * ds, 1)})

    clamped = 0
    for i in range(n):
        v = min(max(o[i], lo[i]), hi[i])
        if abs(v - o[i]) > 1e-9:
            clamped += 1
            o[i] = v
    return o, ramps, clamped


def corner_approach(off: list[float], base, tan_xz, rraw: list[float], divided: list[bool], lo_c: list[float],
                    hi_c: list[float], ds: float, closed: bool) -> tuple[list[float], list[dict]]:
    """Take a tight corner on the INSIDE of a divided lane from the outside of that lane.

    Where the road is tighter than CORNER_R_M and the lane-centre line sits on the corner's inside
    deeper than CORNER_FRAC of the radius (the chained right-handers for race_cw: lane 5.8-7.3 m inside
    R 7.4-8.2 m), the line would reach the inside curb-strip before a 12 m fillet fits — at Navajo ->
    Jackson only the hard lane (0.78 m off the strip face, a car's half-width is ~0.95 m) took it.
    Here the offset moves to the outside of the comfort lane (divider face + FILLET_COMFORT_CLEAR_M)
    through the corner, with ramp_length_m cosine tapers either side — outside, apex, outside —
    and fillet_corners then rounds it inside the comfort lane. Only where every station of the taper
    is divided (never across a two-way street's centreline). Returns (offsets, corners)."""
    n = len(off)
    out = list(off)
    corners: list[dict] = []
    if n < 10 or not any(divided):
        return out, corners
    wrap = (lambda i: i % n) if closed else (lambda i: min(max(i, 0), n - 1))
    core = []
    for i in range(n):
        if not divided[i] or rraw[i] >= CORNER_R_M or abs(off[i]) < 1e-6:
            continue
        a, b = tan_xz[wrap(i - TANGENT_SPAN)], tan_xz[wrap(i + TANGENT_SPAN)]
        turn = a[0] * b[1] - a[1] * b[0]                  # > 0: turning left (toward −lateral)
        inside = (off[i] > 0.0 and turn < 0.0) or (off[i] < 0.0 and turn > 0.0)
        if inside and abs(off[i]) > CORNER_FRAC * rraw[i]:
            core.append(i)
    runs: list[list[int]] = []
    for i in core:
        if runs and i - runs[-1][1] <= 10:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    for c0, c1 in runs:
        to = [(lo_c[wrap(i)] if off[wrap(i)] > 0.0 else hi_c[wrap(i)]) for i in range(c0, c1 + 1)]
        delta = max(abs(off[wrap(i)] - t) for i, t in zip(range(c0, c1 + 1), to))
        if delta < RAMP_STEP_M:
            continue
        N = max(2, int(math.ceil(ramp_length_m(delta) / ds)))
        span = range(c0 - N, c1 + N + 1)
        if not closed and (c0 - N < 0 or c1 + N > n - 1):
            continue
        if not all(divided[wrap(i)] for i in span):
            continue
        for i in span:
            k = wrap(i)
            wgt = 1.0 if c0 <= i <= c1 else _taper((i - (c0 - N)) / N) if i < c0 else _taper((c1 + N - i) / N)
            tgt = lo_c[k] if off[k] > 0.0 else hi_c[k]
            if (off[k] > 0.0 and tgt < off[k]) or (off[k] < 0.0 and tgt > off[k]):
                out[k] = off[k] + (tgt - off[k]) * wgt
        corners.append({"station": wrap((c0 + c1) // 2), "xz": [round(base[wrap((c0 + c1) // 2)][0], 2),
                        round(base[wrap((c0 + c1) // 2)][2], 2)], "road_radius_m": round(min(rraw[wrap(i)] for i in range(c0, c1 + 1)), 2),
                        "shift_m": round(delta, 2), "taper_m": round(N * ds, 1)})
    return out, corners


# --- loops (finding A: the offset curve swallowtails inside the chained right-handers) ---------------

def _seg_cross(p1, p2, p3, p4):
    """(t, s) where p1 + t (p2 − p1) meets p3 + s (p4 − p3) in XZ; None if parallel
    (tools/race_furniture._seg_cross, on [x, y, z] points)."""
    d = (p2[0] - p1[0]) * (p4[2] - p3[2]) - (p2[2] - p1[2]) * (p4[0] - p3[0])
    if abs(d) < 1e-12:
        return None
    t = ((p3[0] - p1[0]) * (p4[2] - p3[2]) - (p3[2] - p1[2]) * (p4[0] - p3[0])) / d
    s = ((p3[0] - p1[0]) * (p2[2] - p1[2]) - (p3[2] - p1[2]) * (p2[0] - p1[0])) / d
    return t, s


def _unit_xz(dx: float, dz: float) -> tuple[float, float]:
    L = math.hypot(dx, dz) or 1.0
    return dx / L, dz / L


def _backward_step(P, T, i: int) -> bool:
    """The step P[i-1] -> P[i] runs against the base tangent of EITHER end (the two-sided test of
    tools/race_furniture._trim_folds)."""
    dx, dz = P[i][0] - P[i - 1][0], P[i][2] - P[i - 1][2]
    return dx * T[i - 1][0] + dz * T[i - 1][1] < 0.0 or dx * T[i][0] + dz * T[i][1] < 0.0


def _fold_cut(P, T, f0: int, f1: int, ds: float):
    """How to cut the fold whose backward steps run f0 .. f1: ('loop', a, b, X) when the in-leg segment
    (a, a+1) crosses the out-leg segment (b-1, b) at X (fewest points removed), else ('extend', a, b, X)
    when the last real in-leg step and the first real out-leg step, extended <= FOLD_EXTEND_MAX_M each,
    meet at X; None when neither exists. The cut keeps P[:a+1], X, P[b:]."""
    m = len(P)
    best = None
    for a in range(f0 - 2, max(-1, f0 - 2 - FOLD_SEARCH_PTS), -1):
        for bb in range(f1, min(m - 1, f1 + FOLD_SEARCH_PTS)):
            r = _seg_cross(P[a], P[a + 1], P[bb], P[bb + 1])
            if r and 0.0 <= r[0] <= 1.0 and 0.0 <= r[1] <= 1.0 and (best is None or bb + 1 - a < best[2] - best[1]):
                X = [P[a][k] + r[0] * (P[a + 1][k] - P[a][k]) for k in range(3)]
                best = ("loop", a, bb + 1, X)
    if best:
        return best

    def real(i: int) -> bool:          # step i -> i+1 is a real forward leg, not the curl into a cusp
        return (0 <= i < m - 1 and math.hypot(P[i + 1][0] - P[i][0], P[i + 1][2] - P[i][2]) >= 0.5 * ds
                and not _backward_step(P, T, i + 1))

    ext = None
    for a in range(f0 - 1, max(0, f0 - 1 - FOLD_SEARCH_PTS), -1):
        if not real(a - 1):
            continue
        din = _unit_xz(P[a][0] - P[a - 1][0], P[a][2] - P[a - 1][2])
        for bb in range(f1, min(m - 1, f1 + FOLD_SEARCH_PTS)):
            if not real(bb):
                continue
            dout = _unit_xz(P[bb + 1][0] - P[bb][0], P[bb + 1][2] - P[bb][2])
            r = _seg_cross(P[a], [P[a][0] + din[0], 0.0, P[a][2] + din[1]],
                           [P[bb][0] - dout[0], 0.0, P[bb][2] - dout[1]], P[bb])
            if not r:
                continue
            ra, rb = r[0], 1.0 - r[1]          # metres ahead of P[a], metres behind P[bb]
            if 0.0 <= ra <= FOLD_EXTEND_MAX_M and 0.0 <= rb <= FOLD_EXTEND_MAX_M:
                cost = (bb - a, ra + rb)
                if ext is None or cost < ext[4]:
                    ext = ("extend", a, bb, [P[a][0] + din[0] * ra, P[a][1], P[a][2] + din[1] * ra], cost)
    return ext[:4] if ext else None


def trim_loops(P, T, closed: bool, ds: float) -> tuple[list[list[float]], list[dict]]:
    """Offset-curve LOOP REMOVAL on the lane-offset polyline (ledger 0047 fix round, finding A).

    Where the offset exceeds the centreline's local radius — the inside of the three chained
    right-handers (R 7.4-8.2 m at v1514 / v2319 / v3296-3297) with the race_cw lane 6-7 m right of the
    chain, and the hairpin the chain-start taper runs through — the offset curve runs forward through
    a self-intersection X to a cusp, BACKWARDS to a second cusp, and forward through X again (a
    swallowtail). race_cw shipped it: a 0.09 m step with a 67 deg turn at College -> Navajo (R 0.3 m,
    7 km/h) and R 1.1 m / 15 km/h at Navajo -> Jackson and Jackson -> Lake Murray. This is the logic of
    tools/race_furniture._trim_folds, which trims the curb barrier at the same corners:
      1. a backward step: point i behind point i-1 along EITHER point's base tangent ``T`` (unit XZ);
         backward steps within FOLD_MERGE_PTS of each other are one fold;
      2. the fold is cut between the in-leg segment and the out-leg segment that CROSS, removing the
         fewest points (kind 'loop'); where the legs never cross (the offset flares while it folds)
         the last real in-leg step and the first real out-leg step are extended to meet (kind 'extend');
      3. one point stands AT the crossing X — a sharp corner that bound_curvature then rounds.
    A fold with neither cut drops its backward points (kind 'drop', reported). A closed lap is worked
    from the point farthest from every fold, so the seam is never inside one. Returns (points, folds)."""
    P = [list(p) for p in P]
    T = [tuple(t) for t in T]
    n = len(P)
    folds: list[dict] = []
    if n < 4:
        return P, folds
    if closed:
        back = sorted(i for i in range(n) if _backward_step(P, T, i))   # i = 0: the closing step
        if back:
            gaps = [(((back[(j + 1) % len(back)] - back[j]) % n) or n, back[j]) for j in range(len(back))]
            g, b0 = max(gaps)
            s = (b0 + g // 2) % n
            P, T = P[s:] + P[:s], T[s:] + T[:s]
        P.append(list(P[0]))
        T.append(T[0])
    for _ in range(500):
        m = len(P)
        f0 = next((i for i in range(1, m) if _backward_step(P, T, i)), None)
        if f0 is None:
            break
        f1, j = f0, f0 + 1
        while j < m and j - f1 <= FOLD_MERGE_PTS:
            if _backward_step(P, T, j):
                f1 = j
            j += 1
        cut = _fold_cut(P, T, f0, f1, ds)
        if cut is None:
            a, b = max(0, f0 - 2), min(m - 1, f1 + 1)
            folds.append({"kind": "drop", "xz": [round(P[f0][0], 2), round(P[f0][2], 2)], "removed": b - a - 1})
            P, T = P[:a + 1] + P[b:], T[:a + 1] + T[b:]
            continue
        kind, a, b, X = cut
        din = _unit_xz(P[a + 1][0] - P[a][0], P[a + 1][2] - P[a][2]) if kind == "loop" else \
            _unit_xz(P[a][0] - P[a - 1][0], P[a][2] - P[a - 1][2])
        dout = _unit_xz(P[b][0] - P[b - 1][0], P[b][2] - P[b - 1][2]) if kind == "loop" else \
            _unit_xz(P[b + 1][0] - P[b][0], P[b + 1][2] - P[b][2])
        turn = math.degrees(math.atan2(din[0] * dout[1] - din[1] * dout[0], din[0] * dout[0] + din[1] * dout[1]))
        folds.append({"kind": kind, "xz": [round(X[0], 2), round(X[2], 2)], "removed": b - a - 1,
                      "corner_turn_deg": round(turn, 1)})
        tx = _unit_xz(T[a][0] + T[b][0], T[a][1] + T[b][1])
        P = P[:a + 1] + [X] + P[b:]
        T = T[:a + 1] + [tx] + T[b:]
    if closed:
        P.pop()
    return P, folds


# --- curvature (the smoother and its ruler) ---------------------------------------------------------

class _Stations:
    """The resampled base as the smoother's ruler: per station XZ, height, unit tangent, travel-right
    normal (tz, −tx), lane corridor [lo, hi] and the radius floor; nearest-station lookups."""

    CELL = 10.0

    def __init__(self, base, tan_xz, lo, hi, rraw, closed: bool, ds: float, lo_c=None, hi_c=None):
        self.n, self.closed, self.ds = len(base), closed, ds
        self.lo_c, self.hi_c = (lo_c or lo), (hi_c or hi)     # the comfort corridor (fillets try it first)
        self.bx = [p[0] for p in base]
        self.by = [p[1] for p in base]
        self.bz = [p[2] for p in base]
        self.tx = [t[0] for t in tan_xz]
        self.tz = [t[1] for t in tan_xz]
        self.lo, self.hi, self.rraw = lo, hi, rraw
        self.grid: dict[tuple[int, int], list[int]] = {}
        for k in range(self.n):
            self.grid.setdefault((int(self.bx[k] // self.CELL), int(self.bz[k] // self.CELL)), []).append(k)

    def wrap(self, k: int) -> int:
        return k % self.n if self.closed else min(max(k, 0), self.n - 1)

    def nearest_global(self, x: float, z: float) -> int:
        cx, cz = int(x // self.CELL), int(z // self.CELL)
        for reach in (1, 3, 8, 30):
            best, bk = float("inf"), -1
            for dx in range(-reach, reach + 1):
                for dz in range(-reach, reach + 1):
                    for k in self.grid.get((cx + dx, cz + dz), ()):
                        d = (self.bx[k] - x) ** 2 + (self.bz[k] - z) ** 2
                        if d < best:
                            best, bk = d, k
            if bk >= 0:
                return bk
        return min(range(self.n), key=lambda k: (self.bx[k] - x) ** 2 + (self.bz[k] - z) ** 2)

    def nearest_near(self, x: float, z: float, k0: int, back: int, ahead: int) -> int:
        best, bk = float("inf"), k0
        for kk in range(k0 - back, k0 + ahead + 1):
            if not self.closed and not 0 <= kk < self.n:
                continue
            k = kk % self.n
            d = (self.bx[k] - x) ** 2 + (self.bz[k] - z) ** 2
            if d < best:
                best, bk = d, k
        return bk

    def associate(self, pts) -> list[int]:
        """Nearest station of every point, progress-constrained (never a station across a hairpin)."""
        if not pts:
            return []
        k = self.nearest_global(pts[0][0], pts[0][2])
        out = [k]
        for p in pts[1:]:
            k = self.nearest_near(p[0], p[2], k, 8, 60)
            out.append(k)
        return out

    def lat(self, x: float, z: float, k: int) -> float:
        return (x - self.bx[k]) * self.tz[k] - (z - self.bz[k]) * self.tx[k]

    def road_r(self, k: int, lat: float = 0.0) -> float:
        """The road's centreline radius "at the place" of a point beside station k at lateral ``lat``:
        the tightest raw radius within ROAD_R_WIN stations plus the lateral offset. A point in a lane
        o metres inside a corner tighter than o sits ~o metres along the leg from the apex station."""
        w = ROAD_R_WIN + int(math.ceil(abs(lat) / self.ds))
        return min(self.rraw[self.wrap(k + d)] for d in range(-w, w + 1))

    def floor(self, k: int, lat: float = 0.0) -> float:
        """The line's radius floor there: min(the road's radius, RADIUS_FLOOR_M)."""
        return min(self.road_r(k, lat), RADIUS_FLOOR_M)

    def y_at(self, x: float, z: float, k: int) -> float:
        s = (x - self.bx[k]) * self.tx[k] + (z - self.bz[k]) * self.tz[k]
        if not self.closed and ((s >= 0 and k == self.n - 1) or (s < 0 and k == 0)):
            return self.by[k]
        k2 = self.wrap(k + 1) if s >= 0 else self.wrap(k - 1)
        d = math.hypot(self.bx[k2] - self.bx[k], self.bz[k2] - self.bz[k]) or 1.0
        f = min(1.0, abs(s) / d)
        return self.by[k] + (self.by[k2] - self.by[k]) * f


def road_radius(base, closed: bool) -> list[float]:
    """The road's own centreline radius at every station, through base[i ± ROAD_R_SPAN] (~6 m chord at
    1.5 m — the original vertex scale). _Stations.road_r takes the minimum around a point, so a point
    anywhere on a corner is judged by the corner's apex."""
    n = len(base)
    raw = []
    for i in range(n):
        if closed:
            a, c = base[(i - ROAD_R_SPAN) % n], base[(i + ROAD_R_SPAN) % n]
        elif ROAD_R_SPAN <= i < n - ROAD_R_SPAN:
            a, c = base[i - ROAD_R_SPAN], base[i + ROAD_R_SPAN]
        else:
            raw.append(10000.0)
            continue
        raw.append(_circumradius(a, base[i], c))
    return raw


def _signed_turn(din, dout) -> float:
    """Signed angle (radians) from unit XZ direction din to dout."""
    return math.atan2(din[0] * dout[1] - din[1] * dout[0], din[0] * dout[0] + din[1] * dout[1])


def _fillet_path(Ps, Pe, din, dout, R: float, h: float):
    """Straight from Ps along din to the tangent point, a circular arc of radius R, straight into Pe
    along dout — sampled every ~h, Ps and Pe excluded. None when the two rays do not meet ahead of Ps /
    behind Pe or the tangent points do not fit between them."""
    r = _seg_cross(Ps, [Ps[0] + din[0], 0.0, Ps[2] + din[1]], [Pe[0] - dout[0], 0.0, Pe[2] - dout[1]], Pe)
    if r is None:
        return None
    t, u = r[0], 1.0 - r[1]                     # metres from Ps to X along din, from X to Pe along dout
    th = _signed_turn(din, dout)
    if t <= 0.0 or u <= 0.0 or abs(th) < 1e-6 or abs(th) > math.radians(170.0):
        return None
    dT = R * math.tan(abs(th) / 2.0)
    if dT > t or dT > u:
        return None
    X = (Ps[0] + din[0] * t, Ps[2] + din[1] * t)
    T1 = (X[0] - din[0] * dT, X[1] - din[1] * dT)
    T2 = (X[0] + dout[0] * dT, X[1] + dout[1] * dT)
    sg = 1.0 if th > 0 else -1.0                # +: turning toward the left normal (-z of din's right)
    nx, nz = -din[1] * sg, din[0] * sg          # from T1 toward the arc centre
    C = (T1[0] + nx * R, T1[1] + nz * R)
    out = []

    def straight(a, b):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        k = max(1, int(round(L / h)))
        return [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(1, k)] + ([b] if L > 1e-9 else [])

    out += straight((Ps[0], Ps[2]), T1)
    arc = abs(th) * R
    k = max(1, int(round(arc / h)))
    a0 = math.atan2(T1[1] - C[1], T1[0] - C[0])
    for j in range(1, k):
        a = a0 + th * j / k
        out.append((C[0] + R * math.cos(a), C[1] + R * math.sin(a)))
    out.append(T2)
    out += straight(T2, (Pe[0], Pe[2]))[:-1]
    return out


def fillet_corners(P, closed: bool, st: _Stations, ds: float, tol: float = RADIUS_TOL) -> tuple[list, list[dict]]:
    """Round every corner tighter than its floor with a circular FILLET, inside the lane.

    A violation cluster (radius through three consecutive points under (1 + tol) x the floor) is
    replaced over a window [s, e] by: straight from P[s] along the heading arriving there, an arc of
    radius R, straight into P[e] along the heading leaving there — G1 at both ends. R is the largest of
    RADIUS_FLOOR_M (12 m), shrinking by 7 % steps toward the cluster's floor, that keeps every new point
    inside its station's lane corridor; the window grows until one fits (<= FOLD_SEARCH_PTS either side).
    This is what the trimmed corner of a swallowtail needs: the Laplacian flow alone cuts a 90 deg corner
    to ~R deep (a fillet: 0.41 R), into the inside curb before the radius reaches its floor. A cluster
    no window/radius fits is left to bound_curvature (and the self-check). Returns (points, fillets)."""
    n = len(P)
    fillets: list[dict] = []
    if n < 12:
        return P, fillets
    P = [list(p) for p in P]

    def floor_at(i, k):
        return st.floor(k, st.lat(P[i][0], P[i][2], k))

    for _sweep in range(8):
        n = len(P)
        assoc = st.associate(P)
        wrap = (lambda i: i % n) if closed else (lambda i: i)
        rng = range(n) if closed else range(1, n - 1)
        bad = [i for i in rng if _circumradius(P[wrap(i - 1)], P[i], P[wrap(i + 1)]) < floor_at(i, assoc[i]) * (1.0 + tol)]
        if not bad:
            break
        clusters = []
        for i in bad:
            if clusters and i - clusters[-1][1] <= 6:
                clusters[-1][1] = i
            else:
                clusters.append([i, i])
        if closed and len(clusters) > 1 and clusters[0][0] + n - clusters[-1][1] <= 6:
            clusters[0][0] = clusters[-1][0] - n          # the seam cluster, unwrapped
            clusters.pop()
        done = 0
        limit_hi = None                                   # windows are replaced from the last one back
        for c0, c1 in reversed(clusters):
            need = max(floor_at(wrap(i), assoc[wrap(i)]) for i in range(c0, c1 + 1)) * (1.0 + tol)
            windows = []
            for K in range(3, FOLD_SEARCH_PTS + 1, 2):
                s, e = c0 - K, c1 + K
                if (not closed and (s < 2 or e > n - 3)) or e - s >= n - 4 \
                        or (limit_hi is not None and e >= limit_hi) \
                        or (closed and done and (s < 0 or e >= n)):   # a seam window only as a sweep's first
                    break
                Ps, Pe = P[wrap(s)], P[wrap(e)]
                windows.append((s, e, Ps, Pe,
                                _unit_xz(Ps[0] - P[wrap(s - 2)][0], Ps[2] - P[wrap(s - 2)][2]),
                                _unit_xz(P[wrap(e + 2)][0] - Pe[0], P[wrap(e + 2)][2] - Pe[2])))
            best = None
            r_min = need / (1.0 + tol) * (1.0 + FILLET_MARGIN)
            for lo_b, hi_b, lane in ((st.lo_c, st.hi_c, "comfort"), (st.lo, st.hi, "hard")):
                R = RADIUS_FLOOR_M * (1.0 + FILLET_MARGIN)
                while R >= r_min - 1e-9 and best is None:     # the largest radius, in the smallest window
                    for s, e, Ps, Pe, din, dout in windows:
                        path = _fillet_path(Ps, Pe, din, dout, R, ds)
                        if path is None:
                            continue
                        k = assoc[wrap(s)]
                        ok = True
                        for x, z in path:
                            k = st.nearest_near(x, z, k, 8, 40)
                            lat = st.lat(x, z, k)
                            # inside the lane, and the arc is no tighter than the floor of ANY point it
                            # makes (an arc's ends sit on the straight legs, where the floor is 12 m)
                            if not lo_b[k] - 1e-9 <= lat <= hi_b[k] + 1e-9 \
                                    or R < st.floor(k, lat) * (1.0 + tol):
                                ok = False
                                break
                        if ok:
                            best = (s, e, path, R, lane)
                            break
                    R *= 0.93
                if best is not None:
                    break
            if best is None:
                continue
            s, e, path, R, lane = best
            ys = [P[wrap(s)][1] + (P[wrap(e)][1] - P[wrap(s)][1]) * (j + 1) / (len(path) + 1) for j in range(len(path))]
            new = [[x, y, z] for (x, z), y in zip(path, ys)]
            fillets.append({"xz": [round(P[wrap((c0 + c1) // 2)][0], 2), round(P[wrap((c0 + c1) // 2)][2], 2)],
                            "radius_m": round(R, 2), "floor_m": round(need / (1.0 + tol), 2), "lane": lane,
                            "window_pts": e - s, "turn_deg": round(math.degrees(_signed_turn(
                                _unit_xz(P[wrap(s)][0] - P[wrap(s - 2)][0], P[wrap(s)][2] - P[wrap(s - 2)][2]),
                                _unit_xz(P[wrap(e + 2)][0] - P[wrap(e)][0], P[wrap(e + 2)][2] - P[wrap(e)][2]))), 1)})
            done += 1
            if closed and (s < 0 or e >= n):
                # the window straddles the seam: rotate it to the front, splice, and re-measure (every
                # other cluster's index moved)
                P = P[wrap(s):] + P[:wrap(s)]
                P = P[:1] + new + P[e - s:]
                break
            P = P[:s + 1] + new + P[e:]
            limit_hi = s
        if not done:
            break
    return P, fillets


def bound_curvature(P, closed: bool, st: _Stations, *, pinned=(), max_iter: int = SMOOTH_MAX_ITERS,
                    tol: float = RADIUS_TOL, normal_only: bool = False):
    """Bound the line's curvature, inside its lane (ledger 0047 fix round, finding A+B step 3) — the
    clean-up after fillet_corners, for the kinks it leaves (polyline vertices, fillet joins).

    A point violates where the radius through it and its two neighbours is under (1 + tol) x its floor
    (min(the road's centreline radius at its place, RADIUS_FLOOR_M), _Stations.floor). Each iteration
    moves every violating point and SMOOTH_DILATE points either side by a TAUBIN pair of Laplacian steps
    (SMOOTH_LAMBDA toward its neighbours' midpoint, then SMOOTH_MU away): a kink is spread over more
    points, but a whole bend is not shrunk toward its inside — plain Laplacian flow dragged Dragon
    Tail's R 10.5 m bends onto the inside lane edge, tighter still. A move that would leave the station's
    lane corridor [lo, hi] is truncated at the boundary. Points away from any violation never move, so
    the line keeps its lane centre wherever the curvature is already fine. Stops when nothing violates,
    or when the violations have not improved for SMOOTH_STALL_ITERS iterations; returns the BEST state
    seen (never one worse than its input), with what still violates reported.
    ``normal_only`` drops each step's component along the chord (P[i-1] -> P[i+1]): the spacing of an
    already-resampled line is kept, and point 0 slides along the start/finish line instead of off it.
    Returns (points, report)."""
    n = len(P)
    rep = {"iterations": 0, "violations_before": 0, "violations_after": 0, "moved_points": 0,
           "corridor_clamps": 0}
    if n < 5:
        return P, rep
    wrap = (lambda i: i % n) if closed else (lambda i: i)
    pinned = set(pinned) | (set() if closed else {0, n - 1})
    assoc = st.associate(P)

    def rad(i: int) -> float:
        if not closed and (i == 0 or i == n - 1):
            return 10000.0
        return _circumradius(P[wrap(i - 1)], P[i], P[wrap(i + 1)])

    def need(i: int) -> float:
        k = assoc[i]
        return st.floor(k, st.lat(P[i][0], P[i][2], k)) * (1.0 + tol)

    def score() -> tuple[int, float]:
        return len(viol), round(sum(1.0 - R[i] / need(i) for i in viol), 4)

    def step(active, lam: float) -> None:
        new = {}
        for i in active:
            a, b, c = P[wrap(i - 1)], P[i], P[wrap(i + 1)]
            dx = lam * ((a[0] + c[0]) * 0.5 - b[0])
            dz = lam * ((a[2] + c[2]) * 0.5 - b[2])
            if normal_only:
                ux, uz = _unit_xz(c[0] - a[0], c[2] - a[2])
                along = dx * ux + dz * uz
                dx, dz = dx - along * ux, dz - along * uz
            new[i] = (b[0] + dx, b[2] + dz)
        for i, (x, z) in new.items():
            k = st.nearest_near(x, z, assoc[i], 20, 20)
            lat = st.lat(x, z, k)
            if not st.lo[k] <= lat <= st.hi[k]:
                # the move would leave the lane: TRUNCATE it at the boundary (a point is never dragged
                # along the line by a projection, so the spacing survives); a point already outside
                # (a resample chord across the lane's inside corner) is put back along the normal
                rep["corridor_clamps"] += 1
                x0, z0 = P[i][0], P[i][2]
                lat0 = st.lat(x0, z0, k)
                bound = st.lo[k] if lat < st.lo[k] else st.hi[k]
                if st.lo[k] <= lat0 <= st.hi[k] and abs(lat - lat0) > 1e-12:
                    f = max(0.0, min(1.0, (bound - lat0) / (lat - lat0)))
                    x, z = x0 + (x - x0) * f, z0 + (z - z0) * f
                else:
                    x += st.tz[k] * (bound - lat)
                    z -= st.tx[k] * (bound - lat)
            P[i][0], P[i][2] = x, z
            assoc[i] = k

    R = [rad(i) for i in range(n)]
    viol = {i for i in range(n) if R[i] < need(i)}
    rep["violations_before"] = len(viol)
    moved: set[int] = set()
    best = score()
    best_state = None                       # None = the input itself
    best_it = it = 0
    while viol and it < max_iter:
        active = set()
        for i in viol:
            for d in range(-SMOOTH_DILATE, SMOOTH_DILATE + 1):
                j = i + d
                if closed:
                    active.add(j % n)
                elif 0 <= j < n:
                    active.add(j)
        active -= pinned
        if best_state is None:
            best_state = {}
        for i in active:                    # remember the pre-move position of anything about to move
            if i not in best_state:
                best_state[i] = (P[i][0], P[i][2], assoc[i])
        step(active, SMOOTH_LAMBDA)
        step(active, SMOOTH_MU)
        moved |= active
        touched = set()
        for i in active:
            for d in (-1, 0, 1):
                j = i + d
                if closed:
                    touched.add(j % n)
                elif 0 <= j < n:
                    touched.add(j)
        for i in touched:
            R[i] = rad(i)
            if R[i] < need(i):
                viol.add(i)
            else:
                viol.discard(i)
        it += 1
        if it % 25 == 0 or not viol:
            sc = score()
            if sc < best:
                best, best_it = sc, it
                best_state = {}             # the current state is the best: nothing to restore
            elif it - best_it >= SMOOTH_STALL_ITERS:
                break
    if best_state and score() > best:
        for i, (x, z, k) in best_state.items():     # roll back to the best state seen
            P[i][0], P[i][2] = x, z
            assoc[i] = k
        R = [rad(i) for i in range(n)]
        viol = {i for i in range(n) if R[i] < need(i)}
        rep["rolled_back_to_iteration"] = best_it
    rep.update(iterations=it, violations_after=len(viol), moved_points=len(moved))
    if viol:
        worst = min(viol, key=lambda i: R[i] / need(i))
        rep["worst_after"] = {"xz": [round(P[worst][0], 2), round(P[worst][2], 2)],
                              "radius_m": round(R[worst], 2), "floor_m": round(need(worst) / (1.0 + tol), 2)}
    return P, rep


# --- fairing (ledger 0052 F3: no bends that are not there) ------------------------------------------------

def _band_solve(A: list[list[float]], b: list[float]) -> list[float]:
    """Solve the symmetric positive-definite system with half-bandwidth 3 (``A[i][d]`` = a(i, i + d), d = 0..3)
    by banded Cholesky — O(n), pure python."""
    m = len(b)
    L = [[0.0, 0.0, 0.0, 0.0] for _ in range(m)]        # L[i][t] = l(i, i - 3 + t)
    for i in range(m):
        for j in range(max(0, i - 3), i + 1):
            s = A[j][i - j] if i - j <= 3 else 0.0
            for t in range(max(0, i - 3, j - 3), j):
                s -= L[i][t - i + 3] * L[j][t - j + 3]
            if j == i:
                L[i][3] = math.sqrt(max(s, 1e-18))
            else:
                L[i][j - i + 3] = s / L[j][3]
    y = [0.0] * m
    for i in range(m):
        s = b[i]
        for j in range(max(0, i - 3), i):
            s -= L[i][j - i + 3] * y[j]
        y[i] = s / L[i][3]
    x = [0.0] * m
    for i in range(m - 1, -1, -1):
        s = y[i]
        for j in range(i + 1, min(m, i + 4)):
            s -= L[j][i - j + 3] * x[j]
        x[i] = s / L[i][3]
    return x


def _band_matvec(A: list[list[float]], x: list[float]) -> list[float]:
    """y = A x for the symmetric half-bandwidth-3 storage of _band_solve."""
    m = len(x)
    y = [0.0] * m
    for i in range(m):
        row = A[i]
        y[i] += row[0] * x[i]
        for d in range(1, 4):
            j = i + d
            if j < m and row[d]:
                y[i] += row[d] * x[j]
                y[j] += row[d] * x[i]
    return y


def fair_line(P, closed: bool, ok, *, w: float | None = None, u_max: float | None = None,
              alpha: float | None = None, pad: int | None = None,
              floor_car: list[float] | None = None) -> tuple[list[list[float]], dict]:
    """Fair the line: no wiggle, kink or S the road does not make the car drive (ledger 0052, F3).

    The v0.17.1 race drafts braked 60-100 m before every box for bends that were not there: a slope-limited
    piecewise-linear approach envelope joined straight-arc-straight left kinks and S-wiggles that
    bound_curvature (a radius FLOOR) never sees, and a resample across two 1.5 m grids left curvature noise at
    the point scale. Each point moves along its own normal by u (metres, right of travel), minimising

        sum_j |X[j+2] - 3 X[j+1] + 3 X[j] - X[j-1]|^2  +  w sum_i u_i^2,     X_i = P_i + u_i n_i

    — the third difference is the change of curvature along the line: a curvature STEP (a straight meeting an
    arc) becomes a transition, a wiggle shorter than ~2 pi / (2 asin(w^(1/6) / 2)) points is taken out, and a
    long bend is kept (the u term holds the line where it is). Bounds: each point may move only as far along its
    normal as ``ok(i, x, z)`` allows (its clearance from the walls — bisected per point, monotone along the
    normal) and never more than ``u_max``; the bounded problem is solved by a primal-dual active set over the
    banded system (O(n) per solve). A radius tighter than min(RADIUS_FLOOR_M, the input's own) through three
    faired points halves the bounds of the five points around it and re-solves; so does a car-scale radius
    (through the points +-FAIR_CAR_PTS) tighter than min(``floor_car[i]``, the input's own) — a box arc is not
    tightened by its transitions (``floor_car`` 0 = no floor; the points +-FAIR_CAR_PTS + 2 are pulled back).
    A closed lap is solved as an
    open chain padded ``pad`` points round the seam each way; the middle is the lap. y is untouched (the
    caller seats the line). Returns (points, report)."""
    w = FAIR_W if w is None else w
    u_max = FAIR_U_MAX_M if u_max is None else u_max
    alpha = FAIR_ALPHA if alpha is None else alpha
    n = len(P)
    rep = {"w": w, "alpha": alpha, "u_max_m": u_max, "solves": 0, "active_at_bound": 0, "radius_rounds": 0, "refused_after": 0}
    if floor_car is not None:
        rep["box_floor_pts"] = sum(1 for f in floor_car if f > 0.0)
    if n < 12:
        return [list(p) for p in P], rep
    pad = (FAIR_PAD_PTS if pad is None else pad) if closed else 0
    pad = min(pad, n)
    wrap = (lambda i: i % n) if closed else (lambda i: min(max(i, 0), n - 1))
    nrm = []
    for i in range(n):
        a, b = P[wrap(i - 2)], P[wrap(i + 2)]
        tx, tz = _unit_xz(b[0] - a[0], b[2] - a[2])
        nrm.append((tz, -tx))                                 # right of travel

    def at(i: int, ui: float) -> list[float]:
        return [P[i][0] + nrm[i][0] * ui, P[i][1], P[i][2] + nrm[i][1] * ui]

    # per-point bounds along the normal: the farthest move ok() allows each way (coarse march, then bisection)
    lo_b, hi_b = [0.0] * n, [0.0] * n
    for i in range(n):
        for sgn, store in ((1.0, hi_b), (-1.0, lo_b)):
            good, t = 0.0, 0.0
            bad_t = None
            while t < u_max - 1e-9:
                t = min(u_max, t + FAIR_PROBE_M)
                q = at(i, sgn * t)
                if ok(i, q[0], q[2]):
                    good = t
                else:
                    bad_t = t
                    break
            if bad_t is not None:
                a_t, b_t = good, bad_t
                for _ in range(8):
                    mid = 0.5 * (a_t + b_t)
                    q = at(i, sgn * mid)
                    if ok(i, q[0], q[2]):
                        a_t = mid
                    else:
                        b_t = mid
                good = a_t
            store[i] = sgn * good
    # the bounds as a SMOOTH conservative envelope: a min filter then a box mean over the same +-k never exceeds
    # a point's own bound (every value averaged is a minimum over a window holding that point), twice — so a
    # line pressed against them follows a curve, not the millimetre steps of a per-point bisection
    k = FAIR_BOUND_SMOOTH_PTS

    def smooth_room(room: list[float]) -> list[float]:
        for _ in range(2):
            mn = [min(room[wrap(i + d)] for d in range(-k, k + 1)) for i in range(n)]
            room = [sum(mn[wrap(i + d)] for d in range(-k, k + 1)) / (2 * k + 1) for i in range(n)]
        return room

    hi_b = smooth_room(hi_b)
    lo_b = [-r for r in smooth_room([-x for x in lo_b])]
    m = n + 2 * pad
    pt = [(k - pad) % n if closed else k for k in range(m)]   # chain variable -> line point
    A0 = [[0.0, 0.0, 0.0, 0.0] for _ in range(m)]
    b0 = [0.0] * m
    # third differences (change of curvature) at weight 1, second differences (curvature) at weight ``alpha``
    for C, wt in (((-1.0, 3.0, -3.0, 1.0), 1.0), ((1.0, -2.0, 1.0), alpha)):
        if wt <= 0.0:
            continue
        L = len(C)
        for j in range(1, m - L + 2):
            q = tuple(j - 1 + t for t in range(L))
            ax = sum(C[t] * P[pt[q[t]]][0] for t in range(L))
            az = sum(C[t] * P[pt[q[t]]][2] for t in range(L))
            for t1 in range(L):
                p1 = q[t1]
                n1 = nrm[pt[p1]]
                b0[p1] -= wt * C[t1] * (n1[0] * ax + n1[1] * az)
                for t2 in range(t1, L):
                    n2 = nrm[pt[q[t2]]]
                    A0[p1][t2 - t1] += wt * C[t1] * C[t2] * (n1[0] * n2[0] + n1[1] * n2[1])
    for k in range(m):
        A0[k][0] += w

    def rad(Q, i: int) -> float:
        if not closed and (i == 0 or i == n - 1):
            return 10000.0
        return _circumradius(Q[wrap(i - 1)], Q[i], Q[wrap(i + 1)])

    r_in = [rad(P, i) for i in range(n)]
    kc = FAIR_CAR_PTS

    def rad_car(Q, i: int) -> float:
        if not closed and (i < kc or i > n - 1 - kc):
            return 10000.0
        return _circumradius(Q[wrap(i - kc)], Q[i], Q[wrap(i + kc)])

    fl = [f if f > 0.0 else 0.0 for f in floor_car] if floor_car is not None else [0.0] * n
    r_car_in = [rad_car(P, i) if fl[i] else 0.0 for i in range(n)]

    def tight_points(Q) -> tuple[list[int], list[int]]:
        t3 = [i for i in range(n) if rad(Q, i) < min(RADIUS_FLOOR_M, r_in[i]) * (1.0 - 1e-3)]
        tc = [i for i in range(n) if fl[i] and rad_car(Q, i) < min(fl[i], r_car_in[i]) * (1.0 - 1e-3)]
        return t3, tc
    active: dict[int, float] = {}                             # chain variable -> the bound it is held at
    u = [0.0] * m
    for rr in range(FAIR_RADIUS_ROUNDS + 1):
        rep["radius_rounds"] = rr
        it = 0
        while True:
            A = [row[:] for row in A0]
            bb = b0[:]
            for k, v in active.items():
                A[k][0] += FAIR_PIN_W
                bb[k] += FAIR_PIN_W * v
            u = _band_solve(A, bb)
            rep["solves"] += 1
            it += 1
            g = _band_matvec(A0, u)                           # the objective's gradient (without the holds)
            releasing = it <= FAIR_ACTIVE_ITERS               # after that only holds are added: it terminates
            changed = False
            for k in range(m):
                i = pt[k]
                lo, hi = lo_b[i], hi_b[i]
                if k in active:
                    held = active[k]
                    if not lo - 1e-12 <= held <= hi + 1e-12:  # a bound pulled in by a radius round
                        active[k] = min(max(held, lo), hi)
                        changed = True
                    # release a hold the objective no longer pushes against (KKT sign of the gradient)
                    elif releasing and ((held <= lo + 1e-12 and g[k] - b0[k] < -1e-9)
                                        or (held >= hi - 1e-12 and g[k] - b0[k] > 1e-9)):
                        del active[k]
                        changed = True
                elif u[k] < lo - 1e-6:
                    active[k] = lo
                    changed = True
                elif u[k] > hi + 1e-6:
                    active[k] = hi
                    changed = True
            if not changed or it > FAIR_ACTIVE_ITERS + m:
                break
        for k, v in list(active.items()):                     # a held variable sits exactly on its bound
            u[k] = v
        for k in range(m):
            i = pt[k]
            u[k] = min(max(u[k], lo_b[i]), hi_b[i])
        Q = [at(i, u[pad + i]) for i in range(n)]
        tight, tight_car = tight_points(Q)
        if not tight and not tight_car:
            break
        pull = set()
        for i in tight:                                       # pull the move back around a radius it tightened
            pull.update(wrap(i + d) for d in range(-2, 3))
        for i in tight_car:                                   # ... and around a box arc it tightened
            pull.update(wrap(i + d) for d in range(-kc - 2, kc + 3))
        for j in sorted(pull):
            lo_b[j] *= 0.5
            hi_b[j] *= 0.5
        for k in list(active):
            i = pt[k]
            active[k] = min(max(active[k], lo_b[i]), hi_b[i])
    out = []
    refused = 0
    for i in range(n):
        q = at(i, u[pad + i])
        if not ok(i, q[0], q[2]):                             # never ship a refused move: keep the input point
            refused += 1
            q = [P[i][0], P[i][1], P[i][2]]
        out.append(q)
    us = [abs(u[pad + i]) for i in range(n)]
    rep.update(active_at_bound=len([k for k in active if pad <= k < pad + n]), refused_after=refused,
               max_move_m=round(max(us), 3), mean_move_m=round(sum(us) / n, 4),
               tight_after=sum(1 for i in range(n) if rad(out, i) < min(RADIUS_FLOOR_M, r_in[i]) * (1.0 - 1e-3)))
    if floor_car is not None:
        rep["box_tight_after"] = len(tight_points(out)[1])
    return out, rep


def _rotate_to(P, x: float, z: float) -> tuple[list[list[float]], dict]:
    """The closed polyline re-started at its point nearest (x, z) — the start/finish line's midpoint
    projected onto the line (finding C). Returns (points, info)."""
    n = len(P)
    best = (float("inf"), 0, 0.0)
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        vx, vz = b[0] - a[0], b[2] - a[2]
        L2 = vx * vx + vz * vz
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - a[0]) * vx + (z - a[2]) * vz) / L2))
        d = math.hypot(a[0] + t * vx - x, a[2] + t * vz - z)
        if d < best[0]:
            best = (d, i, t)
    d, i, t = best
    a, b = P[i], P[(i + 1) % n]
    X = [a[k] + t * (b[k] - a[k]) for k in range(3)]
    rest = P[i + 1:] + P[:i + 1]
    if math.dist(X, rest[0]) < 1e-6:
        out = [list(p) for p in rest]
    elif math.dist(X, rest[-1]) < 1e-6:
        out = [list(p) for p in [rest[-1]] + rest[:-1]]
    else:
        out = [X] + [list(p) for p in rest]
    return out, {"xz": [round(X[0], 3), round(X[2], 3)], "dist_m": round(d, 3)}


def _tangents(pts, closed: bool, ds: float, span: int = 1):
    n = len(pts)
    idx = (lambda i: i % n) if closed else (lambda i: min(max(i, 0), n - 1))
    fwd = []
    for i in range(n):
        a, b = pts[idx(i - span)], pts[idx(i + span)]
        t = [b[k] - a[k] for k in range(3)]
        norm = math.sqrt(sum(x * x for x in t)) or 1.0
        fwd.append([x / norm for x in t])
    return fwd


def line_geometry(pts, closed: bool, st: _Stations, assoc: list[int], off: list[float], ds: float) -> dict:
    """What the audit measures, on the final line: min radius (3 consecutive points) against the floor,
    steps turning more than TURN_MAX_DEG (and how many of those sit where the road itself is that tight:
    road radius under the radius a TURN_MAX_DEG step at this spacing means), the largest lateral jump
    between consecutive points, backward steps against the base tangent, and self-crossings."""
    n = len(pts)
    wrap = (lambda i: i % n) if closed else (lambda i: i)
    r_tight = ds / (2.0 * math.sin(math.radians(TURN_MAX_DEG) / 2.0))
    rng = range(n) if closed else range(1, n - 1)
    turns, below, rmin, rmin_at = [], 0, 10000.0, 0
    over = over_tight = 0
    for i in rng:
        a, b, c = pts[wrap(i - 1)], pts[i], pts[wrap(i + 1)]
        t1 = math.atan2(b[2] - a[2], b[0] - a[0])
        t2 = math.atan2(c[2] - b[2], c[0] - b[0])
        tu = abs(math.degrees((t2 - t1 + math.pi) % (2 * math.pi) - math.pi))
        turns.append(tu)
        r = _circumradius(a, b, c)
        if r < rmin:
            rmin, rmin_at = r, i
        k = assoc[i]
        lat = st.lat(b[0], b[2], k)
        if r < RADIUS_CHECK * st.floor(k, lat):
            below += 1
        if tu > TURN_MAX_DEG:
            if st.road_r(k, lat) < r_tight:
                over_tight += 1
            else:
                over += 1
    jumps = [abs(off[i] - off[i - 1]) for i in (range(n) if closed else range(1, n))]
    backward = 0
    for i in (range(n) if closed else range(1, n)):
        a, b = pts[wrap(i - 1)], pts[i]
        k = assoc[i]
        if (b[0] - a[0]) * st.tx[k] + (b[2] - a[2]) * st.tz[k] < 0.0:
            backward += 1
    return {"min_radius_m": round(rmin, 2), "min_radius_at": rmin_at,
            "radius_below_floor": below, "max_turn_deg": round(max(turns) if turns else 0.0, 1),
            "turns_over_limit": over, "turns_over_limit_road_tight": over_tight,
            "max_lateral_jump_m": round(max(jumps) if jumps else 0.0, 3),
            "backward_steps": backward, "self_crossings": self_crossings(pts, closed)}


def self_crossings(pts, closed: bool, window: int = 200) -> int:
    """Pairs of non-adjacent segments (index distance 2 .. window) of the line that cross — a loop the
    backward-step test could miss. 0 on every line this writes."""
    n = len(pts)
    m = n if closed else n - 1
    cell = 6.0
    grid: dict[tuple[int, int], list[int]] = {}
    for i in range(m):
        a, b = pts[i], pts[(i + 1) % n]
        for gx in range(int(min(a[0], b[0]) // cell), int(max(a[0], b[0]) // cell) + 1):
            for gz in range(int(min(a[2], b[2]) // cell), int(max(a[2], b[2]) // cell) + 1):
                grid.setdefault((gx, gz), []).append(i)
    seen = set()
    count = 0
    for segs in grid.values():
        for x in range(len(segs)):
            for y in range(x + 1, len(segs)):
                i, j = segs[x], segs[y]
                d = abs(i - j)
                if closed:
                    d = min(d, n - d)
                if d < 2 or d > window or (i, j) in seen:
                    continue
                seen.add((i, j))
                r = _seg_cross(pts[i], pts[(i + 1) % n], pts[j], pts[(j + 1) % n])
                if r and 0.0 < r[0] < 1.0 and 0.0 < r[1] < 1.0:
                    count += 1
    return count


# --- race corridors (ledger 0049) ------------------------------------------------------------------

def corridor_offsets(lo: list[float], hi: list[float], ds: float, closed: bool,
                     mu_m: float = CORRIDOR_MU_M) -> tuple[list[float], dict]:
    """The race line's lane target inside a declared corridor (ledger 0049): the lane CENTRE between the
    two wall faces ``lo`` / ``hi`` (metres right of travel), with every change of it a taper, never a step.

    Minimises  sum (o[i+1] − o[i])² / ds  +  sum ds (o[i] − centre[i])² / mu_m²  with o held inside
    [lo + LINE_MIN_CLEAR_M, hi − LINE_MIN_CLEAR_M] (projected SOR — the method of the corridor solver
    that placed the walls). Where the lane centre moves — a funnel out of a box, a convergence onto an
    island face, the whole street (centre 0) meeting a closure run (centre ~2 m right on a 17 m road) —
    the line moves over a few mu_m; only a wall that moves faster drags it, because the bound is hard. A
    lane narrower than both clearances holds its midpoint. Returns (offsets, report)."""
    n = len(lo)
    alo, ahi, t = [], [], []
    for a, b in zip(lo, hi):
        c = (a + b) / 2.0
        x, y = a + LINE_MIN_CLEAR_M, b - LINE_MIN_CLEAR_M
        if x > y:
            x = y = c
        alo.append(x)
        ahi.append(y)
        t.append(c)
    o = [min(max(t[i], alo[i]), ahi[i]) for i in range(n)]
    if n < 3:
        return o, {"sweeps": 0}
    k = (ds / mu_m) ** 2
    rho = 2.0 / (2.0 + k)                                  # Jacobi radius of the screened chain
    omega = min(CORRIDOR_SOR_OMEGA if rho >= 1.0 else 2.0 / (1.0 + math.sqrt(1.0 - rho * rho)), 1.95)
    rng = range(n) if closed else range(1, n - 1)
    sweeps, mx = 0, 0.0
    for sweeps in range(1, CORRIDOR_SOR_MAX + 1):
        mx = 0.0
        for i in rng:
            b = o[i + 1] if i + 1 < n else o[0]
            new = (o[i - 1] + b + k * t[i]) / (2.0 + k)
            new = o[i] + omega * (new - o[i])
            new = alo[i] if new < alo[i] else ahi[i] if new > ahi[i] else new
            d = abs(new - o[i])
            if d > mx:
                mx = d
            o[i] = new
        if mx < CORRIDOR_SOR_TOL_M:
            break
    m = n if closed else n - 1
    slope = max(abs(o[(i + 1) % n] - o[i]) for i in range(m)) / ds
    at_limit = sum(1 for i in range(n) if alo[i] < ahi[i] and (o[i] <= alo[i] + 1e-6 or o[i] >= ahi[i] - 1e-6))
    return o, {"mu_m": mu_m, "sweeps": sweeps, "omega": round(omega, 3), "last_change_m": mx,
               "max_lateral_slope": round(slope, 4), "stations_at_lane_limit": at_limit}


class _SegSet:
    """Directed segments of one or more polylines with a spatial index: ``signed(x, z)`` is the distance
    to the nearest segment, positive on the side ``pos_left`` names (the pseudo-normal of the two segments
    decides when the nearest point is a shared vertex), ``far`` when nothing lies within reach."""

    def __init__(self, loops, closed: bool, pos_left: bool, far: float, reach_cells: int = FACE_REACH_CELLS):
        self.ax, self.az, self.bx, self.bz, self.nl, self.prev, self.nxt = [], [], [], [], [], [], []
        self.grid: dict[tuple[int, int], list[int]] = {}
        self.sign, self.far, self.reach = (1.0 if pos_left else -1.0), far, reach_cells
        for loop in loops:
            N = len(loop)
            nseg = N if closed else N - 1
            base = len(self.ax)
            for i in range(max(0, nseg)):
                a, b = loop[i], loop[(i + 1) % N]
                ux, uz = _unit_xz(b[0] - a[0], b[1] - a[1])
                s = len(self.ax)
                self.ax.append(a[0]); self.az.append(a[1]); self.bx.append(b[0]); self.bz.append(b[1])
                self.nl.append((-uz, ux))                          # left normal, the loop's own order
                self.prev.append(base + (i - 1) % nseg if (closed or i > 0) else -1)
                self.nxt.append(base + (i + 1) % nseg if (closed or i < nseg - 1) else -1)
                for gx in range(int(math.floor(min(a[0], b[0]) / FACE_CELL_M)),
                                int(math.floor(max(a[0], b[0]) / FACE_CELL_M)) + 1):
                    for gz in range(int(math.floor(min(a[1], b[1]) / FACE_CELL_M)),
                                    int(math.floor(max(a[1], b[1]) / FACE_CELL_M)) + 1):
                        self.grid.setdefault((gx, gz), []).append(s)

    def signed(self, x: float, z: float) -> float:
        cx, cz = int(math.floor(x / FACE_CELL_M)), int(math.floor(z / FACE_CELL_M))
        ax, az, bx, bz, grid = self.ax, self.az, self.bx, self.bz, self.grid
        best_d2, bi, bt = float("inf"), -1, 0.0
        for r in range(self.reach + 1):
            if r == 0:
                cells = [(cx, cz)]
            else:
                cells = [(gx, gz) for gx in range(cx - r, cx + r + 1)
                         for gz in ((cz - r, cz + r) if abs(gx - cx) < r else range(cz - r, cz + r + 1))]
            for cell in cells:
                segs = grid.get(cell)
                if not segs:
                    continue
                for i in segs:
                    vx, vz = bx[i] - ax[i], bz[i] - az[i]
                    L2 = vx * vx + vz * vz
                    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - ax[i]) * vx + (z - az[i]) * vz) / L2))
                    dx, dz = x - ax[i] - t * vx, z - az[i] - t * vz
                    d2 = dx * dx + dz * dz
                    if d2 < best_d2:
                        best_d2, bi, bt = d2, i, t
            if bi >= 0 and math.sqrt(best_d2) <= r * FACE_CELL_M:
                break
        if bi < 0:
            return self.far
        px, pz = ax[bi] + bt * (bx[bi] - ax[bi]), az[bi] + bt * (bz[bi] - az[bi])
        nx, nz = self.nl[bi]
        if bt <= 1e-9 and self.prev[bi] >= 0:                  # nearest = the segment's start vertex
            ox, oz = self.nl[self.prev[bi]]
            nx, nz = nx + ox, nz + oz
        elif bt >= 1.0 - 1e-9 and self.nxt[bi] >= 0:           # ... its end vertex
            ox, oz = self.nl[self.nxt[bi]]
            nx, nz = nx + ox, nz + oz
        d = math.sqrt(best_d2)
        return d if ((x - px) * nx + (z - pz) * nz) * self.sign >= 0.0 else -d


def authored_island_half(island_w: list[float]) -> list[float]:
    """The median island as tools/author_median_blend.py AUTHORS it, per vertex: runs of >= 6 vertices
    with a declared width, each end tapered to NOSE_HALF 0.25 m over NOSE_VERTS 3 vertices (MEASURED
    constants of that tool) — the outline the corridor's island faces are declared against (spec §5)."""
    n = len(island_w)
    half = [0.0] * n
    i = 0
    while i < n:
        if island_w[i] <= 0:
            i += 1
            continue
        j = i
        while j < n and island_w[j] > 0:
            j += 1
        ks = list(range(i, j))
        if len(ks) >= 6:
            for si, k in enumerate(ks):
                h = island_w[k] / 2.0
                if si < 3:
                    h = 0.25 + (h - 0.25) * si / 3
                if len(ks) - 1 - si < 3:
                    h = 0.25 + (h - 0.25) * (len(ks) - 1 - si) / 3
                half[k] = h
        i = j
    return half


class CorridorFaces:
    """The two wall faces of a race layout's corridor, and the islands inside it, as polylines in the
    ENGINE frame (ledger 0049).

    ``lane[k] = [y_lo, y_hi]`` is the declaration's ``lane_by_vertex``: metres forward-LEFT of the
    increasing-vertex tangent, y_hi the forward-left face, y_lo the forward-right one. Each face point is
    vertex + left_normal(tangent v−1 → v+1) × lateral — tools/race_furniture's ring frame. The faces are
    fold-trimmed at the VERTEX rings with trim_loops (an inside face tighter than its offset swallowtails
    exactly like the strip it belongs to and is cut at its legs' crossing — the trimmed corner the
    authored strip stands on, edge_corners), then densified to FACE_STEP_M ON the declared curve (centre
    lerp, normalised lerp of the two vertex tangents, lerp of the lateral: race_furniture.offset_xz, the
    curve the walls are authored on) and straight through a trimmed corner.

    ``island_half`` (authored_island_half, forward vertex order) adds every authored median island as a
    closed outline: an obstacle of its own, whatever the closure does (pavement mode stands the closure
    0.15 m off it; island-top mode on its curb).

    ``dists(x, z)`` = signed distance to (the y_hi face, the y_lo face), positive on the corridor side
    (right of the y_hi face, left of the y_lo face, in forward order); ``island(x, z)`` = signed distance
    to the nearest island outline, positive outside it; ``clearance`` = the smallest of the three."""

    def __init__(self, cl_pts, lane, closed: bool = True, island_half: list[float] | None = None):
        m = len(cl_pts)
        if len(lane) < m:
            raise ValueError(f"lane_by_vertex has {len(lane)} rows for {m} vertices")
        self.closed = closed
        T = []
        for k in range(m):
            a = cl_pts[(k - 1) % m] if closed else cl_pts[max(k - 1, 0)]
            b = cl_pts[(k + 1) % m] if closed else cl_pts[min(k + 1, m - 1)]
            T.append(_unit_xz(b[0] - a[0], b[2] - a[2]))
        self.folds: dict[str, list] = {}
        self.lines: dict[str, list[tuple[float, float]]] = {}

        def on_curve(k: int, u: float, col: int) -> tuple[float, float]:
            j = (k + 1) % m
            ca, cb = cl_pts[k], cl_pts[j]
            tx, tz = _unit_xz(T[k][0] + (T[j][0] - T[k][0]) * u, T[k][1] + (T[j][1] - T[k][1]) * u)
            lat = float(lane[k][col]) + (float(lane[j][col]) - float(lane[k][col])) * u
            return ca[0] + (cb[0] - ca[0]) * u - tz * lat, ca[2] + (cb[2] - ca[2]) * u + tx * lat

        for name, col in (("hi", 1), ("lo", 0)):
            # 1. the face at the VERTEX rings (the strips' own ring spacing), the vertex index carried in y
            #    through the trim (a 'loop' corner lands at a fractional index, an 'extend' corner at its
            #    in-leg vertex): trim_loops' leg search is sized for ~1.5-3 m steps
            V = [[cl_pts[k][0] - T[k][1] * float(lane[k][col]), float(k), cl_pts[k][2] + T[k][0] * float(lane[k][col])]
                 for k in range(m)]
            V, folds = trim_loops(V, list(T), closed, 3.0)
            self.folds[name] = folds
            # 2. densified ON the declared curve between two consecutive kept vertices, straight through a
            #    trimmed corner (the authored strip's chords: in-leg ring -> corner X -> out-leg ring)
            P = []
            nv = len(V)
            for q in range(nv if closed else nv - 1):
                a, b = V[q], V[(q + 1) % nv]
                ka, kb = a[1], b[1]
                whole = ka == int(ka) and kb == int(kb) and int(kb) == (int(ka) + 1) % m
                steps = max(1, int(math.ceil(math.hypot(b[0] - a[0], b[2] - a[2]) / FACE_STEP_M)))
                for s in range(steps):
                    u = s / steps
                    P.append(on_curve(int(ka), u, col) if whole else
                             (a[0] + (b[0] - a[0]) * u, a[2] + (b[2] - a[2]) * u))
            if not closed:
                P.append((V[-1][0], V[-1][2]))
            self.lines[name] = P
        self._hi = _SegSet([self.lines["hi"]], closed, pos_left=False, far=-1e9)   # corridor = right of it
        self._lo = _SegSet([self.lines["lo"]], closed, pos_left=True, far=-1e9)    # corridor = left of it
        # islands: left edge forward, right edge back — the interior is RIGHT of every edge
        loops = []
        if island_half:
            k = 0
            while k < m:
                if island_half[k] <= 0.0:
                    k += 1
                    continue
                j = k
                while j < m and island_half[j] > 0.0:
                    j += 1
                ks = list(range(k, j))
                left = [(cl_pts[q][0] - T[q][1] * island_half[q], cl_pts[q][2] + T[q][0] * island_half[q]) for q in ks]
                right = [(cl_pts[q][0] + T[q][1] * island_half[q], cl_pts[q][2] - T[q][0] * island_half[q]) for q in ks]
                loops.append(left + right[::-1])
                k = j
        self.island_loops = loops
        # a point inside an island is at most its half-width from an edge, so a reach of the widest island's
        # half-width + ISLAND_REACH_CELLS cells classifies every point; one farther than that from every edge
        # is outside every island and at least that far clear (the queries stay local: a full 48 m reach
        # from every probe of a lap was 2/3 of the writer's run time)
        reach = ISLAND_REACH_CELLS + int(math.ceil(max(island_half or [0.0]) / FACE_CELL_M))
        self._isl = _SegSet(loops, True, pos_left=True, far=reach * FACE_CELL_M, reach_cells=reach) if loops else None

    def polyline(self, which: str) -> list[tuple[float, float]]:
        return list(self.lines[which])

    def dists(self, x: float, z: float) -> tuple[float, float]:
        return self._hi.signed(x, z), self._lo.signed(x, z)

    def island(self, x: float, z: float) -> float:
        return self._isl.signed(x, z) if self._isl is not None else 1e9

    def clearance(self, x: float, z: float) -> float:
        a, b = self.dists(x, z)
        c = a if a < b else b
        d = self.island(x, z)
        return c if c < d else d


def _faces_lane(lo_face: list[float], hi_face: list[float], clear: float) -> tuple[list[float], list[float]]:
    """(lo, hi): the line's lane ``clear`` metres inside a corridor's two faces (right of travel); a lane
    narrower than both clearances collapses to its midpoint (lane_corridor's rule)."""
    lo, hi = [], []
    for a, b in zip(lo_face, hi_face):
        x, y = a + clear, b - clear
        if x > y:
            x = y = (a + b) / 2.0
        lo.append(x)
        hi.append(y)
    return lo, hi


def _corner_stations(pts, closed: bool, ds: float, n_st: int, tan_xz, corners: list[dict]) -> list[dict]:
    """The open corners (``corners``: travel-order vertex indices ``a`` .. ``b`` = the arc PC − 2 ..
    PT + 2 and ``apex``) as resampled stations, with the turn's hand measured on the stations' tangents
    15 stations outside the arc (``right`` = a right turn: its outside is left of travel)."""
    if not corners:
        return []
    m = len(pts)
    S = [0.0]
    for j in range(1, m):
        S.append(S[-1] + math.dist(pts[j - 1], pts[j]))

    def stn(j: int) -> int:
        k = int(round(S[j % m] / ds))
        return k % n_st if closed else min(max(k, 0), n_st - 1)

    out = []
    wrap = (lambda i: i % n_st) if closed else (lambda i: min(max(i, 0), n_st - 1))
    for c in corners:
        a, b, ap = stn(c["a"]), stn(c["b"]), stn(c["apex"])
        ta, tb = tan_xz[wrap(a - 15)], tan_xz[wrap(b + 15)]
        turn = ta[0] * tb[1] - ta[1] * tb[0]                 # > 0: turning left (corner_approach's sign)
        out.append({"apex_vertex": c["apex_vertex"], "zone": c.get("zone"), "D_deg": c.get("D_deg"),
                    "a_st": a, "b_st": b, "apex_st": ap, "right": turn < 0.0})
    return out


def corridor_for_layout(bands: dict, layout_id: str, pts_fwd, *, reverse: bool, closed: bool = True,
                        island_w: list[float] | None = None) -> dict | None:
    """A race layout's corridor from a ledger-0049 declaration (``data/barrier_bands.json`` version 2,
    ``corridors.<layout id>``), ready for build_line: the two faces right of THIS travel per travel-order
    vertex, the zone codes, the open corners, the CorridorFaces (built on ``pts_fwd``, the forward-order
    ENGINE-frame centreline the declaration indexes). ``island_w`` (median_bands island_w_by_vertex):
    the authored islands become obstacles in the faces, and the lane stops at an island's outline on
    whichever side the lane is (always right of travel on SD: each direction's own carriageway). None
    when the file declares no corridors at all (a version-1 file: the legacy centre-chain lane). A
    version-2 file without this layout is an error — a race layout is never silently driven down a lane
    its walls do not have."""
    cors = bands.get("corridors")
    if not cors:
        if int(bands.get("version", 1) or 1) >= 2:
            raise SystemExit(f"barrier_bands.json is version {bands.get('version')} but declares no corridors — "
                             f"refusing to draft {layout_id} on the retired centre-chain lane")
        return None
    cor = cors.get(layout_id)
    if cor is None:
        raise SystemExit(f"barrier_bands.json declares corridors {sorted(cors)} but none for layout {layout_id!r}")
    m = len(pts_fwd)
    lane, zone = cor.get("lane_by_vertex"), cor.get("zone_by_vertex")
    if not lane or not zone or len(lane) not in (m, m + 1) or len(zone) not in (m, m + 1):
        raise SystemExit(f"corridors.{layout_id}: lane_by_vertex / zone_by_vertex must have {m} (or {m + 1}) rows, "
                         f"got {len(lane or [])} / {len(zone or [])}")
    lane = [(float(a), float(b)) for a, b in lane[:m]]
    bad = [k for k, (a, b) in enumerate(lane) if not a < b]
    if bad:
        raise SystemExit(f"corridors.{layout_id}: lane_by_vertex y_lo >= y_hi at {len(bad)} vertices (first v{bad[0]})")
    codes = {"box": 2, "whole": 1, "pin": 1, "closure": 0, "island": 0}
    unknown = sorted({z for z in zone[:m] if z not in codes})
    if unknown:
        raise SystemExit(f"corridors.{layout_id}: unknown zone(s) {unknown}")
    zcode = [float(codes[z]) for z in zone[:m]]
    ih = authored_island_half(list(island_w[:m])) if island_w else [0.0] * m
    faces = CorridorFaces(pts_fwd, lane, closed, island_half=ih)
    # the lane in the forward frame, stopped at an authored island's outline (a no-op in pavement mode,
    # where the closure face already stands 0.82 m off it)
    lane_c, island_clipped = [], 0
    for (a, b), h in zip(lane, ih):
        if h > 0.0:
            if (a + b) / 2.0 <= 0.0 and b > -h:
                b, island_clipped = -h, island_clipped + 1
            elif (a + b) / 2.0 > 0.0 and a < h:
                a, island_clipped = h, island_clipped + 1
        lane_c.append((a, b))
    if reverse:
        lo = [lane_c[m - 1 - j][0] for j in range(m)]        # r = +y for the reverse travel
        hi = [lane_c[m - 1 - j][1] for j in range(m)]
        zc = [zcode[m - 1 - j] for j in range(m)]
    else:
        lo = [-lane_c[j][1] for j in range(m)]               # r = −y
        hi = [-lane_c[j][0] for j in range(m)]
        zc = zcode
    corners, skipped = [], []
    for c in bands.get("corners") or []:
        v, z = int(c["apex"]) % m, zone[int(c["apex"]) % m]
        d = float(c.get("D_deg", 0.0))
        if z not in OPEN_ZONES or abs(d) > BOX_TURN_MAX_DEG:
            skipped.append({"apex_vertex": v, "zone": z, "D_deg": d,
                            "why": "closure zone" if z not in OPEN_ZONES else f"turns > {BOX_TURN_MAX_DEG:g} deg"})
            continue
        a, b = (int(c["PC"]) - BOX_PAD) % m, (int(c["PT"]) + BOX_PAD) % m
        if reverse:
            a, b, ap = (m - 1 - b) % m, (m - 1 - a) % m, (m - 1 - v) % m
        else:
            ap = v
        corners.append({"apex_vertex": v, "zone": z, "D_deg": d, "a": a, "b": b, "apex": ap})
    zcount: dict[str, int] = {}
    for z in zone[:m]:
        zcount[z] = zcount.get(z, 0) + 1
    mouths = [[(p[0], p[2]) for p in mo.get("polyline_xyz_m") or []] for mo in bands.get("closed_mouths") or []]
    return {"lo": lo, "hi": hi, "zone": zc, "corners": corners, "corners_skipped": skipped, "faces": faces,
            "forward": not reverse, "token": cor.get("token"), "zones": zcount, "mouths": [p for p in mouths if p],
            "face_folds": {k: [f["kind"] for f in v] for k, v in faces.folds.items()},
            "islands": len(faces.island_loops), "lane_vertices_island_clipped": island_clipped}


def _unwrapped_range(a: int, b: int, n: int) -> tuple[int, int]:
    """(a, b) with b >= a: a closed lap's range that wraps the seam gets b + n."""
    return (a, b) if b >= a else (a, b + n)


def box_targets(off: list[float], lo_c: list[float], hi_c: list[float], corners: list[dict], ds: float,
                closed: bool) -> tuple[list[float], list[dict]]:
    """Turn in from the corridor's OUTSIDE edge at every open corner (ledger 0049 spec §12).

    For each corner (``a_st`` .. ``b_st`` = its arc PC − 2 .. PT + 2 in stations, ``right`` = a right
    turn, whose outside is the low, left-of-travel side) the target holds the OUTSIDE comfort edge from
    BOX_APPROACH_M before the arc to the arc's end — exit wide, inside the box — with ramp_length_m cosine
    tapers either side. box_fillets then lays the largest arc the box allows from those legs. Returns
    (offsets, report)."""
    n = len(off)
    out = list(off)
    rep: list[dict] = []
    wrap = (lambda i: i % n) if closed else (lambda i: i)
    for c in corners:
        a, b = _unwrapped_range(c["a_st"], c["b_st"], n) if closed else (c["a_st"], c["b_st"])
        H = int(math.ceil(BOX_APPROACH_M / ds))
        h0, h1 = a - H, b

        def edge(k: int) -> float:
            return lo_c[k] + BOX_EDGE_IN_M if c["right"] else hi_c[k] - BOX_EDGE_IN_M

        N0 = max(2, int(math.ceil(ramp_length_m(edge(wrap(h0)) - off[wrap(h0)]) / ds)))
        N1 = max(2, int(math.ceil(ramp_length_m(edge(wrap(h1)) - off[wrap(h1)]) / ds)))
        if not closed and (h0 - N0 < 0 or h1 + N1 > n - 1):
            rep.append({"apex_vertex": c["apex_vertex"], "skipped": "too near an end of an open line"})
            continue
        # the outside edge as a slope-limited envelope, BOX_EDGE_SLOPE per metre: dilated toward the lane
        # (a right turn's outside is the low side: the envelope is the max of edge_j − slope·|i − j|·ds)
        span = list(range(h0 - N0, h1 + N1 + 1))
        env = [edge(wrap(i)) for i in span]
        step = BOX_EDGE_SLOPE * ds
        sgn = 1.0 if c["right"] else -1.0
        for q in range(1, len(env)):
            env[q] = sgn * max(sgn * env[q], sgn * env[q - 1] - step)
        for q in range(len(env) - 2, -1, -1):
            env[q] = sgn * max(sgn * env[q], sgn * env[q + 1] - step)
        moved_in = 0
        for q, i in enumerate(span):
            k = wrap(i)
            tgt = min(max(env[q], lo_c[k]), hi_c[k])          # never past the comfort lane either way
            if abs(tgt - edge(k)) > 1e-6:
                moved_in += 1
            w = 1.0 if h0 <= i <= h1 else _taper((i - (h0 - N0)) / N0) if i < h0 else _taper((h1 + N1 - i) / N1)
            out[k] = out[k] + (tgt - out[k]) * w            # composed: two corners' tapers may overlap
        rep.append({"apex_vertex": c["apex_vertex"], "side": "outside-left" if c["right"] else "outside-right",
                    "hold_m": round((h1 - h0) * ds, 1), "ramp_in_m": round(N0 * ds, 1), "ramp_out_m": round(N1 * ds, 1),
                    "stations_eased_off_the_edge": moved_in})
    return out, rep


def _densify_xz(pts, step: float, closed: bool = False) -> list[tuple[float, float]]:
    """XZ points every <= ``step`` along the polyline (its own points kept): what a check of a LINE, not
    of its samples, walks (CHECK_STEP_M). ``pts`` are (x, z) pairs, or [x, y, z] when they have 3 items."""
    xz = [(p[0], p[2]) if len(p) == 3 else (p[0], p[1]) for p in pts]
    n = len(xz)
    out = []
    for i in range(n if closed else n - 1):
        a, b = xz[i], xz[(i + 1) % n]
        k = max(1, int(math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / step)))
        for j in range(k):
            out.append((a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k))
    if not closed and xz:
        out.append(xz[-1])
    return out


def _path_radius_min(P, i0: int, i1: int, closed: bool) -> float:
    n = len(P)
    r = 10000.0
    for i in range(max(i0, 1 if not closed else i0), min(i1, n - 2 if not closed else i1) + 1):
        r = min(r, _circumradius(P[(i - 1) % n], P[i % n], P[(i + 1) % n]))
    return r


def box_fillets(P, closed: bool, st: _Stations, faces: CorridorFaces, corners: list[dict],
                ds: float, comfort_m: float = FILLET_COMFORT_CLEAR_M) -> tuple[list, list[dict]]:
    """The largest circular arc each open corner allows (ledger 0049 spec §12: "the fillet targets the
    largest radius that keeps FILLET_COMFORT_CLEAR_M off every face").

    For each corner the line is replaced, between a point s on the entry leg and a point e on the exit leg
    (BOX_WINDOW_PTS before / after the corner's arc, independently), by straight-arc-straight from P[s]
    along the heading arriving there to P[e] along the heading leaving there (_fillet_path: G1 at both
    ends). The radius is bisected between the floor fillet (RADIUS_FLOOR_M × (1 + FILLET_MARGIN)) and
    BOX_R_MAX_M; a candidate fits when every point of it stands FILLET_COMFORT_CLEAR_M inside the
    corridor's wall FACES (CorridorFaces — the trimmed inside corner X included), else the hard
    CHECK_CLEAR_M + CORRIDOR_TOL_M. The smallest window that fits the largest radius is taken. A window
    never reaches into another corner's arc, nor into a window already replaced (corners closer than two
    windows apart share the straight between them). A corner nothing fits is left to fillet_corners
    (reported). ``comfort_m`` replaces FILLET_COMFORT_CLEAR_M as the comfort clearance (ledger 0052's
    ``ai.wall_clear_m``: 2.5 m off the K-rail; absent = 1.5 m, today's arcs). Returns (points, report)."""
    rep: list[dict] = []
    P = [list(p) for p in P]
    claimed = {id(c): (c["a_st"], c["b_st"]) for c in corners}      # station ranges, per corner

    def owned_by_other(k: int, me) -> bool:
        for key, (ra, rb) in claimed.items():
            if key == me:
                continue
            if ((k - ra) % st.n if closed else k - ra) <= ((rb - ra) % st.n if closed else rb - ra) and (closed or k >= ra):
                return True
        return False

    for c in corners:
        n = len(P)
        if n < 30:
            break
        assoc = st.associate(P)
        a, b = c["a_st"], c["b_st"]
        span = (b - a) % st.n if closed else b - a
        inside = [i for i in range(n) if ((assoc[i] - a) % st.n if closed else assoc[i] - a) <= span
                  and (closed or assoc[i] >= a)]
        if not inside:
            rep.append({"apex_vertex": c["apex_vertex"], "skipped": "no line point on the corner's arc"})
            continue
        if closed:                                         # put the corner mid-line: the seam may cut it
            apex = min(inside, key=lambda i: min((assoc[i] - c["apex_st"]) % st.n, (c["apex_st"] - assoc[i]) % st.n))
            shift = (apex - n // 2) % n
            P = P[shift:] + P[:shift]
            assoc = assoc[shift:] + assoc[:shift]
            inside = sorted((i - shift) % n for i in inside)
            mid = n // 2
            # the contiguous run of arc points around the apex
            c0 = c1 = mid
            S = set(inside)
            while c0 - 1 in S:
                c0 -= 1
            while c1 + 1 in S:
                c1 += 1
        else:
            c0, c1 = inside[0], inside[-1]
        before = _path_radius_min(P, c0, c1, False)
        k1_max = 0                                         # how far each way before another corner's claim
        while c0 - k1_max - 3 >= 0 and k1_max < BOX_WINDOW_PTS[-1] and not owned_by_other(assoc[c0 - k1_max - 3], id(c)):
            k1_max += 1
        k2_max = 0
        while c1 + k2_max + 3 < n and k2_max < BOX_WINDOW_PTS[-1] and not owned_by_other(assoc[c1 + k2_max + 3], id(c)):
            k2_max += 1
        windows = []
        for K1 in BOX_WINDOW_PTS:
            for K2 in BOX_WINDOW_PTS:
                s, e = c0 - K1, c1 + K2
                if s < 2 or e > n - 3 or K1 > k1_max or K2 > k2_max:
                    continue
                Ps, Pe = P[s], P[e]
                din = _unit_xz(Ps[0] - P[s - 2][0], Ps[2] - P[s - 2][2])
                dout = _unit_xz(P[e + 2][0] - Pe[0], P[e + 2][2] - Pe[2])
                r = _seg_cross(Ps, [Ps[0] + din[0], 0.0, Ps[2] + din[1]], [Pe[0] - dout[0], 0.0, Pe[2] - dout[1]], Pe)
                if r is None:
                    continue
                t, u = r[0], 1.0 - r[1]
                th = _signed_turn(din, dout)
                if t <= 0.0 or u <= 0.0 or abs(th) < 1e-3 or abs(th) > math.radians(BOX_TURN_MAX_DEG):
                    continue
                windows.append((e - s, s, e, Ps, Pe, din, dout, t, u, th))
        windows.sort(key=lambda w: w[0])

        def fits(R: float, need: float):
            for w in windows:
                _, s, e, Ps, Pe, din, dout, t, u, th = w
                dT = R * math.tan(abs(th) / 2.0)
                if dT > t or dT > u:
                    continue
                path = _fillet_path(Ps, Pe, din, dout, R, ds)
                if not path:
                    continue
                probe = _densify_xz([(Ps[0], Ps[2])] + path + [(Pe[0], Pe[2])], CHECK_STEP_M)
                m = len(probe)
                order = sorted(range(m), key=lambda q: abs(q - m // 2))     # the apex first: fail fast
                if all(faces.clearance(probe[q][0], probe[q][1]) >= need for q in order):
                    return w, path
            return None

        best = None
        r_floor = RADIUS_FLOOR_M * (1.0 + FILLET_MARGIN)
        ladder = []
        R = BOX_R_MAX_M
        while R > r_floor:
            ladder.append(R)
            R *= BOX_R_LADDER
        ladder.append(r_floor)
        for lane, need in (("comfort", comfort_m), ("hard", CHECK_CLEAR_M + CORRIDOR_TOL_M)):
            above, got = None, None
            for R in ladder:                               # the largest rung that fits ...
                got = fits(R, need)
                if got is not None:
                    break
                above = R
            if got is None:
                continue
            r_ok = R
            if above is not None:                          # ... refined toward the rung above it
                r_bad = above
                for _ in range(BOX_R_BISECT):
                    mid = 0.5 * (r_ok + r_bad)
                    g = fits(mid, need)
                    if g is None:
                        r_bad = mid
                    else:
                        r_ok, got = mid, g
            best = (r_ok, got, lane, need)
            break
        if best is None:
            rep.append({"apex_vertex": c["apex_vertex"], "skipped": "no arc >= the floor fits the corridor",
                        "radius_before_m": round(before, 2)})
            continue
        R, (win, path), lane, need = best
        wlen, s, e, Ps, Pe, din, dout, t, u, th = win
        ys = [Ps[1] + (Pe[1] - Ps[1]) * (j + 1) / (len(path) + 1) for j in range(len(path))]
        clear = min(faces.clearance(x, z) for x, z in _densify_xz([(Ps[0], Ps[2])] + path + [(Pe[0], Pe[2])],
                                                                   CHECK_STEP_M))
        claimed[id(c)] = (assoc[s], assoc[e])             # the whole replaced window is this corner's now
        P = P[:s + 1] + [[x, y, z] for (x, z), y in zip(path, ys)] + P[e:]
        rep.append({"apex_vertex": c["apex_vertex"], "zone": c.get("zone"), "turn_deg": round(math.degrees(th), 1),
                    "radius_m": round(R, 2), "lane": lane, "radius_before_m": round(before, 2),
                    "window_m": round(wlen * ds, 1), "entry_m": round((c0 - s) * ds, 1),
                    "exit_m": round((e - c1) * ds, 1), "path_clear_min_m": round(clear, 2)})
    return P, rep


def check_corridor(line_pts, faces: CorridorFaces, *, clear_m: float = CHECK_CLEAR_M, closed: bool = True,
                   mouths: list[list[tuple[float, float]]] | None = None) -> dict:
    """The race line against its corridor's wall FACES (ledger 0049): every point of the LINE — walked
    every CHECK_STEP_M along each segment, not only at its points — inside the corridor and >= clear_m
    off both faces (funnels, island faces and the trimmed inside corners included), off every authored
    island, and >= clear_m off every sealed mouth line (``mouths``: xz polylines). The minimum is reported
    with the line point it follows. Counts are of probes: a probe past a face (beyond a closure, in a
    side street) is ``outside``; on an island, an ``island_hit``."""
    res = {"points": len(line_pts), "probes": 0, "outside": 0, "too_close": 0, "min_clear_m": None,
           "min_clear_at": None, "min_clear_face": None, "island_hits": 0, "island_too_close": 0,
           "island_min_m": None, "mouth_min_m": None, "mouth_hits": 0}
    best, ibest = float("inf"), float("inf")
    n = len(line_pts)
    for i in range(n):
        a = line_pts[i]
        if closed or i < n - 1:
            b = line_pts[(i + 1) % n]
            k = max(1, int(math.ceil(math.hypot(b[0] - a[0], b[2] - a[2]) / CHECK_STEP_M)))
        else:
            b, k = a, 1
        for j in range(k):
            x, z = a[0] + (b[0] - a[0]) * j / k, a[2] + (b[2] - a[2]) * j / k
            res["probes"] += 1
            dh, dl = faces.dists(x, z)
            d = min(dh, dl)
            if d < best:
                best = d
                res["min_clear_at"] = i
                res["min_clear_face"] = "y_hi (forward-left)" if dh <= dl else "y_lo (forward-right)"
            if d < 0.0:
                res["outside"] += 1
            if d < clear_m:
                res["too_close"] += 1
            di = faces.island(x, z)
            ibest = min(ibest, di)
            if di < 0.0:
                res["island_hits"] += 1
            if di < clear_m:
                res["island_too_close"] += 1
    res["min_clear_m"] = round(best, 3) if line_pts else None
    res["island_min_m"] = round(ibest, 3) if ibest < 1e8 else None
    if mouths:
        mm = float("inf")
        for poly in mouths:
            if len(poly) < 2:
                continue
            xs0 = min(p[0] for p in poly) - 20.0
            xs1 = max(p[0] for p in poly) + 20.0
            zs0 = min(p[1] for p in poly) - 20.0
            zs1 = max(p[1] for p in poly) + 20.0
            for q in line_pts:
                if not (xs0 <= q[0] <= xs1 and zs0 <= q[2] <= zs1):
                    continue
                for a, b in zip(poly, poly[1:]):
                    vx, vz = b[0] - a[0], b[1] - a[1]
                    L2 = vx * vx + vz * vz
                    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((q[0] - a[0]) * vx + (q[2] - a[1]) * vz) / L2))
                    d = math.hypot(q[0] - a[0] - t * vx, q[2] - a[1] - t * vz)
                    mm = min(mm, d)
                    if d < clear_m:
                        res["mouth_hits"] += 1
        res["mouth_min_m"] = round(mm, 3) if mm < float("inf") else None
    res["ok"] = (res["outside"] == 0 and res["too_close"] == 0 and res["mouth_hits"] == 0
                 and res["island_hits"] == 0 and res["island_too_close"] == 0 and bool(line_pts))
    return res


def build_line(pts, widths, *, closed: bool, spacing: float, lat_g: float, decel_g: float,
               accel_g: float, vmax_kmh: float, margin_m: float,
               dh: list[float] | None = None, inset: list[float] | None = None,
               lane_offset: bool = True, start_xz: tuple[float, float] | None = None,
               corridor: dict | None = None, opts: dict | None = None, built: dict | None = None) -> dict:
    """Build the line in the ENGINE frame (x=E, y=up, z=N; right of travel = (tz, −tx)).

    ``dh``/``inset`` are per-vertex channels aligned with ``pts`` (divider half-width, kerb-line
    barrier inset); ``lane_offset=False`` keeps the line on the centreline whatever they say (no
    ramps, no smoothing — the pre-0047 line). With the offset on: lane policy -> cosine ramps ->
    offset polyline -> loop trim -> corner fillets + curvature bound inside the lane -> (start rotation) -> resample at
    ``spacing`` -> curvature bound again, normal moves only (spacing kept). ``start_xz`` (engine XZ, closed lines):
    point 0 is that point projected onto the line — the start/finish line; default the first station's
    point. The returned per-point channels (widths, dh, inset, base, off) are the nearest station's,
    and ``geometry`` carries the ramps, folds, smoothing and the audit's measurements.

    ``corridor`` (a race layout with a ledger-0049 declaration; see _corridor_for_layout) replaces the
    divider/inset lane: ``lo``/``hi`` = the two wall faces per vertex, metres right of THIS travel
    (aligned with ``pts``), ``zone`` = 0 closure / 1 whole street / 2 open box per vertex, ``corners`` =
    the open corners (travel-order vertex indices), ``faces`` = the CorridorFaces the line is judged
    against. Then: lane-centre target (corridor_offsets) -> outside approach at every open corner
    (box_targets) -> offset polyline -> loop trim -> the largest arc each corner allows (box_fillets) ->
    floor fillets + curvature bound as above; sideLeft/sideRight are the distances to the faces.

    ``opts`` (ledger 0052, the track's ``ai`` block for this layout — see load_ai_opts; None = today's line,
    byte for byte): ``wall_clear_m`` is the comfort clearance of a corridor line (box approach, box arcs,
    floor fillets: 2.5 m off the K-rail instead of FILLET_COMFORT_CLEAR_M); ``fair`` runs fair_line on the
    final line (no bends that are not there); ``payload == "kunos"`` makes the radius field the plain 3-point
    circumradius (no min-of-neighbours window). ``built`` (``{"surface": RoadSurface, "walls": WallIndex}``
    from the layout's gate OBJ, scripts.ac.ai_built): every point is seated on the BUILT 1ROAD surface (its y
    and the surface normal, for the payload's normal / camber) and sideLeft / sideRight never reach past the
    first BUILT wall a perpendicular ray meets, minus the margin."""
    opts = dict(opts or {})
    comfort = float(opts.get("wall_clear_m", FILLET_COMFORT_CLEAR_M)) if corridor is not None else FILLET_COMFORT_CLEAR_M
    n_in = len(pts)
    dh = list(dh) if dh is not None else [0.0] * n_in
    inset = list(inset) if inset is not None else [0.0] * n_in
    if len(dh) != n_in or len(inset) != n_in:
        raise ValueError(f"channel length mismatch: pts {n_in}, dh {len(dh)}, inset {len(inset)}")
    if corridor is not None:
        for key in ("lo", "hi", "zone"):
            if len(corridor[key]) != n_in:
                raise ValueError(f"corridor {key}: {len(corridor[key])} values vs {n_in} vertices")
        base, widths_s, ds0, (dh_s, inset_s, clo_s, chi_s, zone_s) = _resample(
            pts, widths, spacing, closed, extra=[dh, inset, corridor["lo"], corridor["hi"], corridor["zone"]],
            lerp_extra=(2, 3))
    else:
        base, widths_s, ds0, (dh_s, inset_s) = _resample(pts, widths, spacing, closed, extra=[dh, inset])
        clo_s = chi_s = zone_s = None
    n0 = len(base)
    tan_xz = [_unit_xz(t[0], t[2]) for t in _tangents(base, closed, ds0, span=TANGENT_SPAN)]
    if corridor is not None:
        lo, hi = _faces_lane(clo_s, chi_s, CHECK_CLEAR_M + CORRIDOR_TOL_M)
        lo_c, hi_c = _faces_lane(clo_s, chi_s, comfort)
    else:
        lo, hi = lane_corridor(widths_s, dh_s, inset_s, CHECK_CLEAR_M + CORRIDOR_TOL_M)
        lo_c, hi_c = lane_corridor(widths_s, dh_s, inset_s, FILLET_COMFORT_CLEAR_M)
    st = _Stations(base, tan_xz, lo, hi, road_radius(base, closed), closed, ds0, lo_c, hi_c)
    geo: dict = {"ramps": [], "ramp_clamped": 0, "corner_approach": [], "folds": [], "fillets": [],
                 "smoothing": [], "start": None}
    corners_st = _corner_stations(pts, closed, ds0, n0, tan_xz, corridor.get("corners") or []) \
        if corridor is not None else []

    if lane_offset and corridor is not None:
        off_raw, geo["corridor_offsets"] = corridor_offsets(clo_s, chi_s, ds0, closed)
        off0, geo["box_approach"] = box_targets(off_raw, lo_c, hi_c, corners_st, ds0, closed)
        P = [[base[i][0] + tan_xz[i][1] * off0[i], base[i][1], base[i][2] - tan_xz[i][0] * off0[i]]
             for i in range(n0)]
        first = (P[0][0], P[0][2])
        P, geo["folds"] = trim_loops(P, tan_xz, closed, ds0)
        P, _, _ = _resample(P, [0.0] * len(P), ds0, closed)
        P, geo["box_arcs"] = box_fillets(P, closed, st, corridor["faces"], corners_st, ds0, comfort_m=comfort)
        if opts.get("fair"):
            # ledger 0052: the arcs the v0.17.1 rule (comfort FILLET_COMFORT_CLEAR_M) lays at these corners — the
            # fairing keeps every box >= FAIR_BOX_KEEP x them (the box rule the 0052 diagnosis declared)
            lo_c1, hi_c1 = _faces_lane(clo_s, chi_s, FILLET_COMFORT_CLEAR_M)
            off1, _ = box_targets(list(off_raw), lo_c1, hi_c1, corners_st, ds0, closed)
            P1 = [[base[i][0] + tan_xz[i][1] * off1[i], base[i][1], base[i][2] - tan_xz[i][0] * off1[i]]
                  for i in range(n0)]
            P1, _ = trim_loops(P1, tan_xz, closed, ds0)
            P1, _, _ = _resample(P1, [0.0] * len(P1), ds0, closed)
            _, arcs1 = box_fillets(P1, closed, st, corridor["faces"], corners_st, ds0)
            r1 = {a["apex_vertex"]: a["radius_m"] for a in arcs1 if "radius_m" in a}
            for arc in geo["box_arcs"]:
                if arc["apex_vertex"] in r1:
                    arc["radius_v0171_rule_m"] = r1[arc["apex_vertex"]]
                    arc["keep_floor_m"] = round(FAIR_BOX_KEEP * r1[arc["apex_vertex"]], 2)
        P, _, _ = _resample(P, [0.0] * len(P), ds0, closed)
        P, geo["fillets"] = fillet_corners(P, closed, st, ds0)
        P, _, _ = _resample(P, [0.0] * len(P), ds0, closed)
        P, rep = bound_curvature(P, closed, st)
        geo["smoothing"].append(rep)
    elif lane_offset:
        target = lane_offsets(widths_s, dh_s, inset_s)
        alo, ahi = lane_corridor(widths_s, dh_s, inset_s, LINE_MIN_CLEAR_M)
        off0, geo["ramps"], geo["ramp_clamped"] = ramp_offsets(target, [d > 0.0 for d in dh_s], alo, ahi,
                                                               ds0, closed)
        off0, geo["corner_approach"] = corner_approach(off0, base, tan_xz, st.rraw, [d > 0.0 for d in dh_s],
                                                       lo_c, hi_c, ds0, closed)
        P = [[base[i][0] + tan_xz[i][1] * off0[i], base[i][1], base[i][2] - tan_xz[i][0] * off0[i]]
             for i in range(n0)]
        first = (P[0][0], P[0][2])
        P, geo["folds"] = trim_loops(P, tan_xz, closed, ds0)
        P, _, _ = _resample(P, [0.0] * len(P), ds0, closed)
        P, geo["fillets"] = fillet_corners(P, closed, st, ds0)
        P, _, _ = _resample(P, [0.0] * len(P), ds0, closed)
        P, rep = bound_curvature(P, closed, st)
        geo["smoothing"].append(rep)
    else:
        P = [list(p) for p in base]
        first = (P[0][0], P[0][2])
    if closed:
        sx, sz = start_xz if start_xz is not None else first
        P, geo["start"] = _rotate_to(P, sx, sz)
        geo["start"]["requested_xz"] = [round(sx, 3), round(sz, 3)]
    P, _, ds = _resample(P, [0.0] * len(P), spacing, closed)
    if lane_offset:
        P, rep = bound_curvature(P, closed, st, tol=RADIUS_TOL_FINAL, normal_only=True)
        geo["smoothing"].append(rep)
    if lane_offset and opts.get("fair"):
        def make_ok(Q):
            """A moved point is fine when it stands >= min(wall_clear + FAIR_CLEAR_EXTRA_M, where it stood) off
            every corridor face (island outlines included) — never closer to a wall than the line it fairs — or,
            with no corridor, inside its station's hard lane."""
            if corridor is not None:
                faces = corridor["faces"]
                need = [min(comfort + FAIR_CLEAR_EXTRA_M, faces.clearance(p[0], p[2])) - 1e-3 for p in Q]
                return lambda i, x, z: faces.clearance(x, z) >= need[i]
            a0 = st.associate(Q)

            def ok(i, x, z):
                k = st.nearest_near(x, z, a0[i], 20, 20)
                return st.lo[k] <= st.lat(x, z, k) <= st.hi[k]
            return ok
        def box_floor(Q):
            """Per point: FAIR_BOX_KEEP x the v0.17.1-rule arc of the box corner it belongs to (the corner's stations
            +- FAIR_BOX_GUARD_PTS), else 0 — the fairing rounds a box's entry and exit, never below that."""
            if corridor is None or not geo.get("box_arcs"):
                return None
            aq = st.associate(Q)
            fl = [0.0] * len(Q)
            for arc in geo["box_arcs"]:
                c = next((c for c in corners_st if c["apex_vertex"] == arc["apex_vertex"]), None)
                if c is None or "keep_floor_m" not in arc:
                    continue
                a = c["a_st"] - FAIR_BOX_GUARD_PTS
                span = ((c["b_st"] - c["a_st"]) % n0 if closed else c["b_st"] - c["a_st"]) + 2 * FAIR_BOX_GUARD_PTS
                for i in range(len(Q)):
                    d = (aq[i] - a) % n0 if closed else aq[i] - a
                    if 0 <= d <= span:
                        fl[i] = max(fl[i], float(arc["keep_floor_m"]))
            return fl
        # the fairing proper (minimum change of curvature + a minimum-curvature pull, inside the bounds), then a
        # light polish (no curvature pull, a short leash) that takes out what an active bound left at the point scale
        P, geo["fairing"] = fair_line(P, closed, make_ok(P), w=opts.get("fair_w"), u_max=opts.get("fair_u_max_m"),
                                       alpha=opts.get("fair_alpha"), floor_car=box_floor(P))
        P, geo["fairing_polish"] = fair_line(P, closed, make_ok(P), w=FAIR_POLISH_W, u_max=FAIR_POLISH_U_M, alpha=0.0,
                                             floor_car=box_floor(P))
    n = len(P)
    idx = (lambda i: i % n) if closed else (lambda i: min(max(i, 0), n - 1))
    assoc = st.associate(P)
    if lane_offset:
        for i, p in enumerate(P):
            p[1] = st.y_at(p[0], p[2], assoc[i])
    normal = None
    if built and built.get("surface") is not None:
        # seated on the BUILT road (ledger 0052 F1): its height, and its normal for the payload's normal / camber
        surf, normal, off_road = built["surface"], [], 0
        for p in P:
            s = surf.sample(p[0], p[1], p[2])
            if s is None:
                off_road += 1
                normal.append([0.0, 1.0, 0.0])
                continue
            p[1] = s[0]
            normal.append(list(s[1]))
        geo["seated"] = {"points": n, "off_road": off_road}
    pts = P
    off = [st.lat(p[0], p[2], assoc[i]) for i, p in enumerate(P)] if lane_offset else [0.0] * n
    widths = [widths_s[k] for k in assoc]
    dh = [dh_s[k] for k in assoc]
    inset = [inset_s[k] for k in assoc]
    geo.update(line_geometry(P, closed, st, assoc, off, ds))

    radius = [_circumradius(pts[idx(i - 1)], pts[i], pts[idx(i + 1)]) for i in range(n)]
    kunos = opts.get("payload") == "kunos"
    if not kunos:
        for _ in range(2):                                 # light smooth: min of neighbours window
            radius = [min(radius[idx(i - 1)], radius[i], radius[idx(i + 1)]) for i in range(n)]
    # (kunos: the plain 3-point circumradius, as every reference line on this PC carries — ledger 0052)

    vmax = vmax_kmh / 3.6
    v = [min(vmax, math.sqrt(lat_g * G * r)) for r in radius]
    passes = 2 if closed else 1
    for _ in range(passes):                                # backward: braking limit
        for i in range(n - 1, -1, -1):
            vn = v[idx(i + 1)] if (closed or i < n - 1) else v[i]
            v[i] = min(v[i], math.sqrt(vn * vn + 2 * decel_g * G * ds))
    for _ in range(passes):                                # forward: acceleration limit
        for i in range(n):
            vp = v[idx(i - 1)] if (closed or i > 0) else v[i]
            v[i] = min(v[i], math.sqrt(vp * vp + 2 * accel_g * G * ds))

    if kunos:                                              # cumulative along the line as it now stands (3D)
        length = [0.0]
        for i in range(1, n):
            length.append(length[-1] + math.dist(pts[i - 1], pts[i]))
    else:
        length = [i * ds for i in range(n)]
    lap_s = sum(ds / max(v[i], 1.0) for i in range(n if closed else n - 1))

    fwd = _tangents(pts, closed, ds)
    grade, gas, brake = [], [], []
    for i in range(n):
        grade.append(fwd[i][1])
        vn = v[idx(i + 1)] if (closed or i < n - 1) else v[i]
        acc = (vn * vn - v[i] * v[i]) / (2 * ds)
        brake.append(max(0.0, min(1.0, -acc / (decel_g * G))))
        gas.append(0.0 if brake[-1] > 0.05 else max(0.25, min(1.0, acc / (accel_g * G) + 0.55)))

    # asymmetric sides: distance from the line to the nearer boundary each way, minus the margin.
    # Boundaries (lateral, right positive): divider face / −(w/2 − inset) on the left, w/2 − inset
    # on the right. With no divider and no inset both read w/2 − margin, exactly as before.
    # A race corridor: the distances to its two wall FACES (the forward-left face is the travel-left
    # one for a forward layout, the travel-right one for a reverse layout).
    side_l, side_r = [], []
    if corridor is not None:
        faces, fwd_travel = corridor["faces"], bool(corridor.get("forward", True))
        for p in pts:
            dhi, dlo = faces.dists(p[0], p[2])
            dl, dr = (dhi, dlo) if fwd_travel else (dlo, dhi)
            side_l.append(max(0.5, dl - margin_m))
            side_r.append(max(0.5, dr - margin_m))
        zone = [int(round(zone_s[k])) for k in assoc]
        geo["corridor"] = {"points_in_open_box": sum(1 for z in zone if z == 2),
                           "points_whole_street": sum(1 for z in zone if z == 1),
                           "points_in_closure_lane": sum(1 for z in zone if z == 0)}
        for arc in geo.get("box_arcs", []):
            c = next((c for c in corners_st if c["apex_vertex"] == arc["apex_vertex"]), None)
            if c is None:
                continue
            a, b = c["a_st"], c["b_st"]
            span = (b - a) % n0 if closed else b - a
            on = [i for i in range(n) if ((assoc[i] - a) % n0 if closed else assoc[i] - a) <= span
                  and (closed or assoc[i] >= a)]
            arc["points_on_arc"] = len(on)
            if opts:                                       # ledger 0052: the arc as finally written (faired)
                arc["line_radius_min_m"] = round(min(_circumradius(pts[idx(i - 4)], pts[i], pts[idx(i + 4)])
                                                     for i in on), 2) if on else None
            arc["min_speed_kmh"] = round(min(v[i] for i in on) * 3.6, 1) if on else None
            # the slowest point within 150 m either side of the arc: an approach that dips below the
            # corner's own speed (a flick before it) shows here
            reach = int(round(150.0 / ds0))
            near = [i for i in range(n) if ((assoc[i] - (a - reach)) % n0 if closed else assoc[i] - (a - reach))
                    <= span + 2 * reach and (closed or assoc[i] >= a - reach)]
            arc["approach_min_speed_kmh"] = round(min(v[i] for i in near) * 3.6, 1) if near else None
    else:
        for i in range(n):
            w, d, s, o = widths[i], dh[i], inset[i], off[i]
            left_b = d if d > 0.0 else -(w / 2.0 - s)
            right_b = w / 2.0 - s
            side_l.append(max(0.5, (o - left_b) - margin_m))
            side_r.append(max(0.5, (right_b - o) - margin_m))
    if built and built.get("walls") is not None:
        # never past the first BUILT wall a perpendicular ray meets (ledger 0052 F4), minus the margin
        walls, cut = built["walls"], []
        for i, p in enumerate(pts):
            tx, tz = _unit_xz(fwd[i][0], fwd[i][2])
            rx, rz = tz, -tx                               # right of travel, ENGINE frame
            for sides, sx, sz in ((side_l, -rx, -rz), (side_r, rx, rz)):
                hit = walls.ray(p[0], p[1], p[2], sx, sz, sides[i] + margin_m)
                if hit - margin_m < sides[i]:
                    new = max(0.5, hit - margin_m)
                    cut.append(sides[i] - new)
                    sides[i] = new
        cut.sort()
        geo["sides_clamped_at_built_walls"] = {"sides": len(cut), "median_cut_m": round(cut[len(cut) // 2], 3) if cut else 0.0,
                                               "max_cut_m": round(cut[-1], 3) if cut else 0.0}
    geo["min_speed_kmh"] = round(min(v) * 3.6, 1) if v else None
    geo["min_speed_at"] = min(range(n), key=lambda i: v[i]) if v else None
    return {"pts": pts, "v": v, "length": length, "radius": radius, "fwd": fwd, "grade": grade,
            "gas": gas, "brake": brake, "side_l": side_l, "side_r": side_r, "off": off,
            "base": [base[k] for k in assoc], "station": assoc, "dh": dh, "inset": inset, "widths": widths,
            "ds": ds, "lap_s": lap_s, "closed": closed, "geometry": geo,
            **({"payload": "kunos", "normal": normal or [[0.0, 1.0, 0.0] for _ in range(n)]} if kunos else {})}


def kunos_payload(line: dict) -> dict:
    """The payload fields AC's own lines carry (ledger 0052 F1, measured on 186 Kunos / third-party lines on
    this PC), on a line ALREADY in the kn5 frame: per point the 3D distance to the previous point (point 0: the
    seam segment of a closed lap), the side the bend turns toward as +-1 (-sign of the heading change over
    +-DIRECTION_WINDOW_PTS points, heading = atan2(fz, fx) in the kn5 frame; a straight holds the last bend's
    sign, never 0), and the camber of the surface under it measured toward the bend: -direction x
    asin(normal . right) (right = (-fz, 0, fx), the driver's right in the kn5 frame — write_sides). That sign
    rule is AC's: on every reference line on this PC camber = -direction x asin(normal . right) on 0.95-1.00 of
    the tilted points, plain asin(normal . right) on ~0.5 (a coin toss). Returns the measured summary."""
    P, closed = line["pts"], line["closed"]
    n = len(P)
    # the points as AC will read them (float32): the radius field is the 3-point circumradius OF THOSE — on a
    # near-straight at x ~ 2 km a float32 step (0.12 mm) is a fifth of a 1.5 m chord's sagitta at R 2 km
    P = [list(struct.unpack("<3f", struct.pack("<3f", *p))) for p in P]
    wrap = (lambda i: i % n) if closed else (lambda i: min(max(i, 0), n - 1))
    line["radius"] = [10000.0 if (not closed and i in (0, n - 1)) else
                      _circumradius(P[wrap(i - 1)], P[i], P[wrap(i + 1)]) for i in range(n)]
    seg = [math.dist(P[i], P[i - 1]) if (closed or i > 0) else (math.dist(P[1], P[0]) if n > 1 else 0.0)
           for i in range(n)]
    h = []
    for i in range(n):
        j = (i + 1) % n if closed else min(i + 1, n - 1)
        a, b = (P[i], P[j]) if j != i else (P[i - 1], P[i])
        h.append(math.atan2(b[2] - a[2], b[0] - a[0]))
    t = [0.0] + [((h[i] - h[i - 1] + math.pi) % (2.0 * math.pi)) - math.pi for i in range(1, n)]
    if closed:
        t[0] = ((h[0] - h[-1] + math.pi) % (2.0 * math.pi)) - math.pi
    k = DIRECTION_WINDOW_PTS
    tk = [sum(t[(i + d) % n] if closed else t[min(max(i + d, 0), n - 1)] for d in range(-k, k + 1))
          for i in range(n)]
    thr = math.radians(DIRECTION_MIN_DEG)
    first = next((i for i in range(n) if abs(tk[i]) > thr), None)
    direction = [1.0] * n
    if first is not None:
        last = -math.copysign(1.0, tk[first])
        order = [(first + q) % n for q in range(n)] if closed else list(range(n))
        if not closed:
            for i in range(first):
                direction[i] = last
        for i in order:
            if abs(tk[i]) > thr:
                last = -math.copysign(1.0, tk[i])
            direction[i] = last
    camber = []
    for i in range(n):
        nx, ny, nz = line["normal"][i]
        f = line["fwd"][i]
        rl = math.hypot(f[0], f[2]) or 1.0
        camber.append(-direction[i] * math.asin(max(-1.0, min(1.0, (nx * -f[2] + nz * f[0]) / rl))))
    line["seglen"], line["direction"], line["camber"] = seg, direction, camber
    return {"camber_min_rad": round(min(camber), 4) if camber else None,
            "camber_max_rad": round(max(camber), 4) if camber else None,
            "direction_plus_pts": sum(1 for d in direction if d > 0), "seg_max_m": round(max(seg), 3) if seg else None}


def write_ai(line: dict, out: Path) -> None:
    """The v7 binary. A ``payload == "kunos"`` line (ledger 0052; kunos_payload() run on it in the kn5 frame)
    carries what AC's own lines carry: header lapTime = sampleCount = 0 (actools: "usually zeroes"), the
    per-point extras ``length`` = the segment to the previous point (not the lap distance), ``direction`` +-1,
    the built surface's ``camber`` and ``normal``. Any other line: today's bytes."""
    n = len(line["pts"])
    side_l = line.get("side_l") or line["side"]
    side_r = line.get("side_r") or line["side"]
    kunos = line.get("payload") == "kunos"
    buf = bytearray()
    buf += struct.pack("<4i", 7, n, 0, 0) if kunos else struct.pack("<4i", 7, n, int(line["lap_s"] * 1000), n)
    for i, p in enumerate(line["pts"]):
        buf += struct.pack("<4fi", p[0], p[1], p[2], line["length"][i], i)
    buf += struct.pack("<i", n)
    for i in range(n):
        f = line["fwd"][i]
        if kunos:
            nm = line["normal"][i]
            buf += struct.pack("<18f", line["v"][i], line["gas"][i], line["brake"][i], 0.0,
                               line["radius"][i], side_l[i], side_r[i],
                               line["camber"][i], line["direction"][i], nm[0], nm[1], nm[2],
                               line["seglen"][i], f[0], f[1], f[2], 0.0, line["grade"][i])
            continue
        buf += struct.pack(
            "<18f",
            line["v"][i], line["gas"][i], line["brake"][i], 0.0,
            line["radius"][i], side_l[i], side_r[i],
            0.0, 0.0,                                  # camber, direction
            0.0, 1.0, 0.0,                             # normal (up)
            line["length"][i],
            f[0], f[1], f[2],
            0.0, line["grade"][i],
        )
    buf += struct.pack("<i", 0)                        # hasGrid = 0
    out.write_bytes(bytes(buf))


def write_sides(line: dict, out_dir: Path) -> None:
    """side_l/side_r.csv — lateral offsets of the drivable edge (the Shift-rebuild inputs).

    Written in the frame ``line`` is in at call time (main calls it after the kn5 flip). In the kn5
    frame (−fz, fx) is the driver's RIGHT, so side_l takes the negative sign."""
    side_l = line.get("side_l") or line["side"]
    side_r = line.get("side_r") or line["side"]
    for name, sign, dist in (("side_l.csv", -1.0, side_l), ("side_r.csv", 1.0, side_r)):
        rows = []
        for i, p in enumerate(line["pts"]):
            f = line["fwd"][i]
            px, pz = -f[2], f[0]
            nrm = math.hypot(px, pz) or 1.0
            o = dist[i] * sign
            rows.append(f"{p[0] + px / nrm * o:.3f},{p[1]:.3f},{p[2] + pz / nrm * o:.3f}")
        (out_dir / name).write_text("\n".join(rows) + "\n", encoding="ascii")


# --- measurement -----------------------------------------------------------------

def grid_alignment(pts: list[list[float]], dummies: dict, closed: bool) -> tuple[float, str] | None:
    """Measure which way the grid faces, against the line's own order (ledger 0026).

    A track's direction is a contract: the grid faces one way and the spline must run the same
    way, or AC's spline-based direction logic contradicts its dummy-based grid and the field
    launches into a ghost route (0023) or is told it is going the wrong way in both directions
    (0026, IMI measured at −0.93). Everything is read in the ENGINE frame — the frame
    ``dummies.json`` / ``dummies_<layout>.json`` are written in, before the kn5 z-mirror; the
    caller normalises ``pts`` to that frame first (``_to_engine_frame``).

    The two track kinds need different rulers, and using the loop's ruler on a stage is wrong:

    * **closed loop** — AC_TIME_0 sits within metres of the grid, so the grid→timing chord IS the
      local heading. Dot it against the tangent at the start. If the timing line turns out to be
      far away the chord is a straight line across a curve and means nothing, so we refuse it
      rather than report a confident-looking number.
    * **point-to-point** — AC_TIME_0 is the *finish*, up to 18 km away (under-the-dragon), and the
      chord is not a heading at all. Direction is instead unambiguous from where the grid sits
      along the line: near index 0 means forward, near the end means reverse.

    Returns (score in [−1, 1], how it was measured), or None when nothing can be measured.
    """
    start = dummies.get("AC_START_0")
    if not start:
        return None
    n = len(pts)
    i = min(range(n), key=lambda k: (pts[k][0] - start[0]) ** 2 + (pts[k][2] - start[2]) ** 2)

    if not closed:
        frac = i / max(1, n - 1)                       # 0 = line starts at the grid, 1 = ends there
        return (1.0 - 2.0 * frac, f"grid at {frac * 100:.0f}% along the stage")

    tl, tr = dummies.get("AC_TIME_0_L"), dummies.get("AC_TIME_0_R")
    if not (tl and tr):
        return None
    mx, mz = (tl[0] + tr[0]) / 2, (tl[2] + tr[2]) / 2
    gx, gz = mx - start[0], mz - start[2]
    gn = math.hypot(gx, gz)
    if gn < 1e-6 or gn > 250.0:                        # on top of the grid, or too far to be a heading
        return None
    a, b = pts[i], pts[(i + 1) % n]
    tx, tz = b[0] - a[0], b[2] - a[2]
    tn = math.hypot(tx, tz)
    if tn < 1e-6:
        return None
    return ((gx / gn) * (tx / tn) + (gz / gn) * (tz / tn), f"grid→timing chord over {gn:.0f} m")


def detect_frame(fin_pts, local_pts, mirror_x: bool = False) -> tuple[str, float, float]:
    """Which frame is the finished line in — 'engine' (as centerline.local.json, x mirrored per
    mirror_x) or 'kn5' (z negated)? Returns (frame, median_dist_engine, median_dist_kn5).

    Decided by the median nearest distance of ~60 sampled local vertices under each hypothesis.
    A tie (a z-symmetric loop) or a line that matches neither keeps today's assumption: engine."""
    sx = -1.0 if mirror_x else 1.0
    n = len(local_pts)
    if n == 0 or not fin_pts:
        return "engine", 0.0, 0.0
    step = max(1, n // 60)
    sample = [local_pts[i] for i in range(0, n, step)]
    fx = [p[0] for p in fin_pts]
    fz = [p[2] for p in fin_pts]
    cell = 25.0
    grid: dict[tuple[int, int], list[int]] = {}
    for i in range(len(fin_pts)):
        grid.setdefault((int(fx[i] // cell), int(fz[i] // cell)), []).append(i)

    def nearest(x, z):
        best = float("inf")
        cx, cz = int(x // cell), int(z // cell)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for i in grid.get((cx + dx, cz + dz), ()):
                    d = (fx[i] - x) ** 2 + (fz[i] - z) ** 2
                    if d < best:
                        best = d
        return math.sqrt(best) if best < float("inf") else cell * 2

    def median(vals):
        s = sorted(vals)
        return s[len(s) // 2]

    d_eng = median([nearest(sx * p[0], p[2]) for p in sample])
    d_kn5 = median([nearest(sx * p[0], -p[2]) for p in sample])
    frame = "kn5" if (d_kn5 < d_eng and d_eng > 5.0 and d_kn5 < d_eng / 4.0) else "engine"
    return frame, d_eng, d_kn5


def _to_engine_frame(pts, project: Path | None, mirror_x: bool) -> tuple[list[list[float]], str]:
    """Normalise the finished line to the ENGINE frame by measuring it against
    centerline.local.json (always written in that frame). No local file → assume engine."""
    lc = (project / "data" / "centerline.local.json") if project else None
    if lc is None or not lc.exists():
        return [list(p) for p in pts], "engine (unverified: no centerline.local.json)"
    local = json.loads(lc.read_text(encoding="utf-8"))["points_xyz_m"]
    frame, d_eng, d_kn5 = detect_frame(pts, local, mirror_x)
    how = f"{frame} frame (median dist to centerline.local: engine {d_eng:.1f} m / kn5 {d_kn5:.1f} m)"
    if frame == "kn5":
        return [[p[0], p[1], -p[2]] for p in pts], how
    return [list(p) for p in pts], how


def check_lane_clearance(line_pts, cl_pts, widths, dh, inset, island_w, *, closed: bool,
                         expect_right: bool, clear_m: float = CHECK_CLEAR_M) -> dict:
    """Judge the finished line (engine frame) against the PER-VERTEX declaration, not the resampled
    channels: the nearest declared SEGMENT, the point's signed distance from it (positive = right of
    the declared forward order), the width interpolated along it and the larger divider / island /
    barrier inset of its two vertices, then: on an island? on a divider (island or chain)?
    inside a divider face + clear_m? past the kerb-line barrier face − clear_m — or, where no inset is
    declared, past the pavement edge − clear_m? on the expected side wherever a divider stands?

    The segment, not the vertex (ledger 0047 fix round): a line that rounds the inside of a corner
    tighter than its own offset runs beside the corner's LEGS, past the corner's centre of curvature,
    and the apex vertex's diagonal normal overstated its lateral by up to (1 − 1/sqrt 2) of it."""
    n = len(cl_pts)
    cell = 16.0
    grid: dict[tuple[int, int], list[int]] = {}
    for i, p in enumerate(cl_pts):
        grid.setdefault((int(p[0] // cell), int(p[2] // cell)), []).append(i)
    idx = (lambda i: i % n) if closed else (lambda i: min(max(i, 0), n - 1))
    res = {"points": len(line_pts), "unmatched": 0, "divider_stations": 0, "right_side": 0,
           "island_hits": 0, "divider_hits": 0, "divider_too_close": 0, "edge_too_close": 0,
           "min_divider_clear_m": None, "min_edge_clear_m": None, "max_lat_m": 0.0}
    for q in line_pts:
        cx, cz = int(q[0] // cell), int(q[2] // cell)
        cands = []
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for i in grid.get((cx + dx, cz + dz), ()):
                    cands.append(((cl_pts[i][0] - q[0]) ** 2 + (cl_pts[i][2] - q[2]) ** 2, i))
        if not cands:
            res["unmatched"] += 1
            continue
        reach = (math.sqrt(min(cands)[0]) + 4.0) ** 2
        seg = None
        for d2, i in cands:
            if d2 > reach:
                continue
            for j0 in (i - 1, i):
                if not closed and (j0 < 0 or j0 + 1 > n - 1):
                    continue
                a, b = cl_pts[idx(j0)], cl_pts[idx(j0 + 1)]
                vx, vz = b[0] - a[0], b[2] - a[2]
                L2 = vx * vx + vz * vz
                t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((q[0] - a[0]) * vx + (q[2] - a[2]) * vz) / L2))
                dist = math.hypot(q[0] - a[0] - t * vx, q[2] - a[2] - t * vz)
                if seg is None or dist < seg[0]:
                    seg = (dist, j0, vx, vz, t)
        dist, j0, vx, vz, t = seg
        a = cl_pts[idx(j0)]
        side = (q[0] - a[0]) * vz - (q[2] - a[2]) * vx          # right of forward order = positive
        lat = dist if side >= 0.0 else -dist
        res["max_lat_m"] = max(res["max_lat_m"], abs(lat))
        i0, i1 = idx(j0), idx(j0 + 1)
        # the ribbon edge runs straight between edge vertices: the width interpolates along the segment;
        # the divider, island and barrier inset are DECLARATIONS and take the larger end (as _resample)
        w = widths[i0] + (widths[i1] - widths[i0]) * t
        s = max(inset[i0], inset[i1])
        d, iw = max(dh[i0], dh[i1]), max(island_w[i0], island_w[i1])
        if iw > 0.0 and abs(lat) <= iw / 2.0:
            res["island_hits"] += 1
        if d > 0.0:
            res["divider_stations"] += 1
            on_right = lat > 0.0
            if on_right == expect_right:
                res["right_side"] += 1
            c = abs(lat) - d
            if c <= 0.0:
                res["divider_hits"] += 1
            res["min_divider_clear_m"] = c if res["min_divider_clear_m"] is None else min(res["min_divider_clear_m"], c)
            if c < clear_m:
                res["divider_too_close"] += 1
        e = (w / 2.0 - s) - abs(lat)
        res["min_edge_clear_m"] = e if res["min_edge_clear_m"] is None else min(res["min_edge_clear_m"], e)
        if e < clear_m:                              # kerb-line barrier face, or the pavement edge
            res["edge_too_close"] += 1
    res["right_side_frac"] = (res["right_side"] / res["divider_stations"]) if res["divider_stations"] else None
    res["ok"] = (res["island_hits"] == 0 and res["divider_too_close"] == 0
                 and res["edge_too_close"] == 0 and res["unmatched"] == 0
                 and (res["right_side_frac"] in (None, 1.0)))
    return res


def verify(path: Path) -> str:
    d = path.read_bytes()
    ver, count, lap, _ = struct.unpack_from("<4i", d, 0)
    first = struct.unpack_from("<f", d, 16 + 12)[0]
    last = struct.unpack_from("<f", d, 16 + (count - 1) * 20 + 12)[0]
    sp = (last - first) / (count - 1) if count > 1 else 0
    return (f"{path.name}: v{ver}, {count:,} pts, {sp:.2f} m spacing over {last - first:,.0f} m, "
            + (f"lap {lap / 1000:.1f} s, " if lap else "header lap 0 (as Kunos), ")
            + f"extras={'yes' if len(d) > 16 + count * 20 + 4 else 'NO'}")


# --- per-vertex channels ---------------------------------------------------------------

def _channel(path: Path, key: str, n: int, label: str) -> list[float] | None:
    """A per-vertex float channel from a bands file, or None (missing file/key/length mismatch —
    printed loud, never silently zero)."""
    if not path.exists():
        print(f"  [{label}] {path.name} absent — {key} = 0 everywhere")
        return None
    vals = json.loads(path.read_text(encoding="utf-8")).get(key)
    if vals is None:
        print(f"  [{label}] {path.name} has no {key} — treated as 0 everywhere")
        return None
    if len(vals) not in (n, n + 1):
        print(f"  [{label}] {path.name} {key}: {len(vals)} values vs {n} vertices — DISABLED")
        return None
    return [float(v) for v in vals[:n]]


AI_OPT_KEYS = {"layouts", "payload", "wall_clear_m", "fair", "fair_w", "fair_alpha", "fair_u_max_m", "surface", "verify"}


def load_ai_opts(cfg: dict, layout_id: str | None) -> dict | None:
    """The track's ledger-0052 opt-in for this line: ``track.config.json`` ``ai`` (keys starting ``_`` are notes),
    limited to ``ai.layouts`` when that is given. None — no block, or this layout not listed — writes today's
    line byte for byte. ``payload: "kunos"`` (the payload fields AC's own lines carry), ``wall_clear_m`` (the
    corridor line's comfort clearance), ``fair`` (+ ``fair_w``), ``surface: "gate_obj"`` (seat on / clamp at the
    layout's BUILT gate OBJ, data/track.<layout>.obj), ``verify`` (tools/verify_ai_line.py's thresholds)."""
    block = cfg.get("ai")
    if not block:
        return None
    opts = {k: v for k, v in block.items() if not str(k).startswith("_")}
    unknown = sorted(set(opts) - AI_OPT_KEYS)
    if unknown:
        raise SystemExit(f"track.config.json ai: unknown key(s) {unknown} (known: {sorted(AI_OPT_KEYS)})")
    if opts.get("payload") not in (None, "kunos"):
        raise SystemExit(f"track.config.json ai.payload {opts['payload']!r}: only \"kunos\"")
    if opts.get("surface") not in (None, "gate_obj"):
        raise SystemExit(f"track.config.json ai.surface {opts['surface']!r}: only \"gate_obj\"")
    lays = opts.pop("layouts", None)
    if lays is not None and layout_id not in lays:
        return None
    return opts


def stale_gate_obj(obj: Path, build_dir: Path) -> list[str]:
    """The kn5s a gate OBJ's header names (kn5_to_gate_obj: "gate OBJ extracted from a.kn5 + b.kn5 ...") that
    exist in ``build_dir`` and are NEWER than the OBJ: a line seated on it would be seated on the last ship's
    world. Empty when nothing is newer (or the header names nothing found)."""
    try:
        with open(obj, "r", encoding="utf-8", errors="replace") as f:
            head = f.readline()
    except OSError:
        return []
    if "extracted from" not in head:
        return []
    names = head.split("extracted from", 1)[1].split("(", 1)[0]
    t = obj.stat().st_mtime
    out = []
    for nm in (s.strip() for s in names.split("+")):
        p = build_dir / nm
        if nm and p.exists() and p.stat().st_mtime > t:
            out.append(nm)
    return out


def load_layout(project: Path, layout_id: str) -> dict | None:
    cfg = json.loads((project / "track.config.json").read_text(encoding="utf-8"))
    return next((lo for lo in (cfg.get("layouts") or []) if lo.get("id") == layout_id), None)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Generate fast_lane.ai (v7) from the racing line.")
    ap.add_argument("src", type=Path, help="project dir (reads data/finished_centerline.json) or a json path")
    ap.add_argument("--out", type=Path, help="output dir (default <project>/ai or <project>/ai/<layout>)")
    ap.add_argument("--install", type=Path, help="AC track dir to copy ai/ into")
    ap.add_argument("--spacing", type=float, default=1.5, help="point spacing m (measured ref floor)")
    ap.add_argument("--lat-g", type=float, default=1.6)
    ap.add_argument("--decel-g", type=float, default=1.0)
    ap.add_argument("--accel-g", type=float, default=0.4)
    ap.add_argument("--vmax-kmh", type=float, default=250.0)
    ap.add_argument("--margin-m", type=float, default=1.2, help="kept clear of each road edge")
    ap.add_argument("--no-pit-copy", action="store_true", help="skip pit_lane.ai = fast_lane.ai")
    ap.add_argument("--reverse", action="store_true",
                    help="force the line opposite the centerline order (same as --direction reverse)")
    ap.add_argument("--direction", choices=("auto", "forward", "reverse"), default="auto",
                    help="auto (default): with --layout the layout's declared direction, else the "
                         "grid heading measured in data/dummies.json (ledger 0026); forward/reverse "
                         "override it (with --layout an override that contradicts the config fails)")
    ap.add_argument("--layout", help="layout id from track.config.json layouts[] (ledger 0047): "
                                     "direction + race_furniture from the config, output ai/<id>/, "
                                     "grid check against data/dummies_<id>.json")
    ap.add_argument("--lane-offset", choices=("auto", "none"), default="auto",
                    help="auto (default): right-hand carriageway wherever a divider is declared "
                         "(median island; for race layouts the corridor of a version-2 barrier_bands.json, "
                         "else the 0047 centre chain + kerb-line inset); none: the centreline, as before")
    ap.add_argument("--race-furniture", choices=("auto", "on", "off"), default="auto",
                    help="consult data/barrier_bands.json: auto = layouts[].race_furniture")
    ap.add_argument("--bands", type=Path, help="barrier bands file (default data/barrier_bands.json)")
    ap.add_argument("--surface-obj", type=Path,
                    help="the layout's BUILT gate OBJ to seat the line on and clamp its sides at (ledger 0052; "
                         "default with ai.surface = \"gate_obj\": data/track.<layout>.obj)")
    args = ap.parse_args(argv)

    project = args.src if args.src.is_dir() else None
    src = args.src / "data" / "finished_centerline.json" if args.src.is_dir() else args.src
    data_dir = src.parent
    j = json.loads(src.read_text(encoding="utf-8"))
    pts, widths = j["points_xyz_m"], j["widths_m"]
    closed = math.dist(pts[0], pts[-1]) < 1e-6
    if closed:
        pts, widths = pts[:-1], widths[:-1]            # L13: drop the duplicate, wrap everything
    n = len(pts)

    cfg = json.loads((project / "track.config.json").read_text(encoding="utf-8")) if project else {}
    pts, how_frame = _to_engine_frame(pts, project, bool(cfg.get("mirror_x", False)))
    print(f"frame: finished_centerline read as {how_frame}")

    # Layout (0047): direction + furniture from the config; an undeclared id needs explicit flags.
    layout = load_layout(project, args.layout) if (project and args.layout) else None
    if args.layout and layout is None:
        if args.direction == "auto" and not args.reverse:
            raise SystemExit(f"--layout {args.layout}: not declared in track.config.json layouts[] "
                             f"— pass --direction forward|reverse explicitly for an undeclared id")
        print(f"layout {args.layout}: NOT declared in track.config.json — direction/furniture from flags")
    mode = "reverse" if args.reverse else args.direction
    if layout is not None:
        declared = str(layout.get("direction", "forward"))
        if declared not in ("forward", "reverse"):
            raise SystemExit(f"layout {args.layout}: direction {declared!r} must be forward|reverse")
        if mode == "auto":
            mode = declared
            print(f"direction: {mode.upper()} (layouts[{args.layout}].direction)")
        elif mode != declared:
            raise SystemExit(f"--direction {mode} contradicts layouts[{args.layout}].direction={declared}")
    elif mode == "auto":
        # Direction, measured rather than assumed (0026). The grid is the contract; the spline obeys.
        dpath = data_dir / "dummies.json"
        dums = {}
        if dpath.exists():
            dums = {k: v for k, v in json.loads(dpath.read_text(encoding="utf-8")).items()
                    if not k.startswith("_")}
        m = grid_alignment(pts, dums, closed) if dums else None
        if m is None:
            mode = "forward"
            print("direction: nothing measurable in dummies.json — running FORWARD unverified")
        else:
            dot, how = m
            mode = "reverse" if dot < 0 else "forward"
            flag = "" if abs(dot) >= 0.5 else "  ** WEAK — verify in game **"
            print(f"direction: {dot:+.2f} ({how}) -> {mode.upper()}{flag}")
    # With a layout the declared direction is re-measured against ITS grid when the dummies exist
    # (the chord is 27-30 m on Alvarado): a contradiction is a build error, not a warning.
    if args.layout:
        dpath = data_dir / f"dummies_{args.layout}.json"
        if dpath.exists():
            dums = {k: v for k, v in json.loads(dpath.read_text(encoding="utf-8")).items()
                    if not k.startswith("_")}
            m = grid_alignment(pts, dums, closed)
            if m is None:
                print(f"  grid check: dummies_{args.layout}.json carries nothing measurable")
            else:
                dot, how = m
                measured = "reverse" if dot < 0 else "forward"
                print(f"  grid check: {dot:+.2f} ({how}) -> {measured.upper()}")
                if measured != mode:
                    raise SystemExit(f"layout {args.layout}: grid faces {measured.upper()} but the "
                                     f"line is declared {mode.upper()} — the grid is the contract")
        else:
            print(f"  grid check: no dummies_{args.layout}.json — declared direction unverified against the grid")

    race = {"auto": bool(layout.get("race_furniture", False)) if layout else False,
            "on": True, "off": False}[args.race_furniture]

    # Per-vertex divider channels, ENGINE frame, index-aligned with the forward vertex order.
    zeros = [0.0] * n
    island = _channel(data_dir / "median_bands.json", "island_w_by_vertex", n, "island") or zeros
    bands_path = args.bands or (data_dir / "barrier_bands.json")
    centre_w = inset = zeros
    corridor = None
    if race:
        # A ledger-0049 declaration (version 2) gives the race layout its own corridor: the lane is the
        # space between its two wall faces, the whole street on Alvarado / the I-8 deck / the open boxes.
        # A version-1 file keeps the 0047 centre-chain lane below (legacy, until barrier_bands v2 lands).
        bands = json.loads(bands_path.read_text(encoding="utf-8")) if bands_path.exists() else {}
        corridor = corridor_for_layout(bands, args.layout or "", [list(p) for p in pts],
                                       reverse=(mode == "reverse"), closed=closed, island_w=island) if bands else None
        if corridor is None:
            centre_w = _channel(bands_path, "centre_w_by_vertex", n, "barrier") or zeros
            inset = _channel(bands_path, "edge_inset_by_vertex", n, "barrier") or zeros
        else:
            print(f"  corridor: {args.layout} (token {corridor['token']}) from {bands_path.name} v{bands.get('version')}"
                  f" — zones {corridor['zones']}; open corners "
                  f"{[c['apex_vertex'] for c in corridor['corners']]}, kept on the floor fillet "
                  f"{[c['apex_vertex'] for c in corridor['corners_skipped']]}; face folds trimmed "
                  f"{corridor['face_folds']}")
    else:
        print("  race furniture OFF for this line: centre chain / kerb-line inset not applied")
    dh = [max(iw / 2.0, cw / 2.0) for iw, cw in zip(island, centre_w)] if corridor is None else zeros
    use_offset = args.lane_offset == "auto"
    fwd_order = {"pts": [list(p) for p in pts], "widths": list(widths), "dh": dh, "inset": inset,
                 # a corridor is judged against the island as AUTHORED (nose taper), like its own faces
                 "island": island if corridor is None else [2.0 * h for h in authored_island_half(island)]}
    if mode == "reverse":
        pts, widths = list(reversed(pts)), list(reversed(widths))
        dh, inset = list(reversed(dh)), list(reversed(inset))
    # Start/finish (finding C): a closed line starts AT the timing line, never at the lap seam — the
    # AC_TIME_0 midpoint of this layout's spawn set (engine frame), else of dummies.json.
    start_xz, start_src = None, None
    if closed:
        cands = ([data_dir / f"dummies_{args.layout}.json"] if args.layout else []) + [data_dir / "dummies.json"]
        for dp in cands:
            if not dp.exists():
                continue
            dm = json.loads(dp.read_text(encoding="utf-8"))
            tl, tr = dm.get("AC_TIME_0_L"), dm.get("AC_TIME_0_R")
            if tl and tr:
                start_xz = ((tl[0] + tr[0]) / 2.0, (tl[2] + tr[2]) / 2.0)
                start_src = f"{dp.name} AC_TIME_0 midpoint"
                break
        if start_xz is None:
            print("  start: no AC_TIME_0_L/R in the dummies — point 0 stays at the first station (lap seam)")
    # Ledger 0052 (opt-in per track / layout; None = today's bytes): payload semantics, wall clearance, fairing,
    # and the BUILT gate OBJ the line is seated on and its sides clamped at.
    opts = load_ai_opts(cfg, args.layout) if cfg else None
    built, built_src = None, None
    if opts is not None or args.surface_obj:
        opts = opts or {}
        objp = args.surface_obj or ((data_dir / f"track.{args.layout}.obj") if opts.get("surface") == "gate_obj"
                                    and args.layout else None)
        if objp is not None:
            if not objp.exists():
                raise SystemExit(f"ai.surface: the BUILT gate OBJ {objp} is missing — run scripts.modkit.kn5_to_gate_obj "
                                 f"for this layout before writing its line (ledger 0052)")
            stale = stale_gate_obj(objp, (project / "build") if project else objp.parent)
            if stale:
                raise SystemExit(f"ai.surface: {objp.name} is older than {stale} — a line seated on it would be "
                                 f"seated on the last ship's world; re-extract it first")
            from .ai_built import RoadSurface, WallIndex, read_gate_obj
            ob = read_gate_obj(objp)
            built = {"surface": RoadSurface(ob), "walls": WallIndex(ob.wall_segs)}
            built_src = {"obj": objp.name, "header": ob.header, "wall_segments": len(ob.wall_segs),
                         "road_tris": len(ob.road_tris)}
        print(f"  ai (ledger 0052): {json.dumps({k: v for k, v in opts.items() if k != 'verify'})}"
              + (f"; built surface + walls from {objp.name} ({len(ob.road_tris):,} road tris, "
                 f"{len(ob.wall_segs):,} wall segments)" if built else "; no built OBJ"))
        if opts.get("payload") == "kunos" and built is None:
            print("  WARNING ai.payload kunos without a built surface: normal (0,1,0) and camber 0 on every point")
    line = build_line(pts, widths, closed=closed, spacing=args.spacing, lat_g=args.lat_g,
                      decel_g=args.decel_g, accel_g=args.accel_g, vmax_kmh=args.vmax_kmh,
                      margin_m=args.margin_m, dh=dh, inset=inset, lane_offset=use_offset,
                      start_xz=start_xz, corridor=corridor, opts=opts, built=built)
    geo = line["geometry"]
    if geo.get("start") is not None:
        geo["start"]["source"] = start_src or "first station (no AC_TIME_0 declared)"
        geo["start"]["index"] = 0                      # point 0 IS the start/finish line (finding C)
        grid = None
        for dp in ([data_dir / f"dummies_{args.layout}.json"] if args.layout else []) + [data_dir / "dummies.json"]:
            if dp.exists():
                grid = json.loads(dp.read_text(encoding="utf-8")).get("AC_START_0")
                if grid:
                    break
        if grid:
            ln = line["pts"]
            gi = min(range(len(ln)), key=lambda i: (ln[i][0] - grid[0]) ** 2 + (ln[i][2] - grid[2]) ** 2)
            behind = (len(ln) - gi) * line["ds"] if gi > len(ln) // 2 else -gi * line["ds"]
            geo["start"]["grid_index"] = gi
            geo["start"]["grid_behind_line_m"] = round(behind, 1)
            geo["start"]["grid_off_line_m"] = round(math.hypot(ln[gi][0] - grid[0], ln[gi][2] - grid[2]), 2)

    # Write-time self-check against the DECLARATION (per-vertex, forward order, engine frame).
    chk = check_lane_clearance(line["pts"], fwd_order["pts"], fwd_order["widths"], fwd_order["dh"],
                               fwd_order["inset"], fwd_order["island"], closed=closed,
                               expect_right=(mode == "forward"))
    chk_c = None
    if corridor is not None:
        # the race line against its corridor's wall FACES (funnels, island faces, the trimmed inside corners)
        chk_c = check_corridor(line["pts"], corridor["faces"], mouths=corridor["mouths"], closed=closed)
        arcs = geo.get("box_arcs", [])
        print(f"corridor: min clear {chk_c['min_clear_m']} m off a wall face (point {chk_c['min_clear_at']}, "
              f"{chk_c['min_clear_face']}); outside {chk_c['outside']}, within {CHECK_CLEAR_M} m {chk_c['too_close']}; "
              f"sealed mouths min {chk_c['mouth_min_m']} m; points in an open box "
              f"{geo['corridor']['points_in_open_box']}; corner arcs "
              + ", ".join(f"v{a['apex_vertex']} R {a['radius_m']} m ({a['lane']}, was {a['radius_before_m']})"
                          if "radius_m" in a else f"v{a['apex_vertex']} {a.get('skipped')}" for a in arcs)
              + f"; min speed {geo['min_speed_kmh']} km/h")
    n_off = sum(1 for o in line["off"] if abs(o) > 0.05)      # measured lateral, so a 5 cm floor
    print(f"lane: {n_off:,}/{len(line['off']):,} pts offset into the right-hand carriageway "
          f"(max {max(line['off']) if line['off'] else 0:.2f} m); divider stations {chk['divider_stations']:,}, "
          f"on the correct side {chk['right_side_frac'] if chk['right_side_frac'] is not None else 'n/a'}; "
          f"island hits {chk['island_hits']}, within {CHECK_CLEAR_M} m of a divider face "
          f"{chk['divider_too_close']}, of a kerb-line barrier face / pavement edge {chk['edge_too_close']}"
          + (f"; min clear divider {chk['min_divider_clear_m']:.2f} m" if chk['min_divider_clear_m'] is not None else "")
          + (f", edge {chk['min_edge_clear_m']:.2f} m" if chk['min_edge_clear_m'] is not None else ""))
    sm = geo["smoothing"]
    print(f"geometry: {len(geo['ramps'])} offset tapers (clamped {geo['ramp_clamped']}), "
          f"{len(geo['corner_approach'])} inside corners taken from the lane's outside, "
          f"{len(geo['folds'])} folds trimmed {[f['kind'] for f in geo['folds']]}, {len(geo['fillets'])} corners "
          f"filleted (R {min((f['radius_m'] for f in geo['fillets']), default=0):.1f}-"
          f"{max((f['radius_m'] for f in geo['fillets']), default=0):.1f} m), smoothing "
          f"{'+'.join(str(r['iterations']) for r in sm) or '-'} iterations moved "
          f"{'+'.join(str(r['moved_points']) for r in sm) or '-'} pts; min radius {geo['min_radius_m']} m, "
          f"max turn {geo['max_turn_deg']} deg, turns > {TURN_MAX_DEG:g} deg: {geo['turns_over_limit']} "
          f"(+{geo['turns_over_limit_road_tight']} where the road is that tight), radius under the floor "
          f"{geo['radius_below_floor']}, max lateral jump {geo['max_lateral_jump_m']} m, backward steps "
          f"{geo['backward_steps']}, self-crossings {geo['self_crossings']}"
          + (f"; start {geo['start']['dist_m']} m from the {geo['start']['source']}" if geo.get("start") else ""))
    if not chk["ok"]:
        raise SystemExit("REFUSED: the line crosses a declared island/barrier band — see the lane line above")
    if chk_c is not None and not chk_c["ok"]:
        raise SystemExit(f"REFUSED: the line leaves its race corridor or stands within {CHECK_CLEAR_M} m of a wall "
                         f"face / sealed mouth — see the corridor line above")
    if geo["backward_steps"] or geo["self_crossings"]:
        raise SystemExit("REFUSED: the line still folds (backward step / self-crossing) — see the geometry line above")
    if use_offset and (geo["turns_over_limit"] or geo["radius_below_floor"]):
        raise SystemExit(f"REFUSED: the line turns more than {TURN_MAX_DEG:g} deg in a step where the road does "
                         f"not, or runs under its radius floor — see the geometry line above")
    # ledger 0052, the box rule the diagnosis declared BEFORE the fix, on the line AS WRITTEN: every box corner's
    # car-scale minimum >= BOX_RULE_KEEP x the arc the v0.17.1 rule lays at that corner in this same world
    short = [a for a in geo.get("box_arcs", []) if a.get("line_radius_min_m") is not None
             and a.get("radius_v0171_rule_m") and a["line_radius_min_m"] < BOX_RULE_KEEP * a["radius_v0171_rule_m"]]
    if opts and opts.get("fair"):
        print("  box rule (ledger 0052, >= %.2f x the v0.17.1-rule arc): " % BOX_RULE_KEEP
              + ", ".join(f"v{a['apex_vertex']} {a.get('line_radius_min_m')}/{a.get('radius_v0171_rule_m')} m"
                          for a in geo.get("box_arcs", [])))
    if short:
        raise SystemExit("REFUSED: a box corner is tighter than %.2f x the arc the v0.17.1 rule lays there (ledger "
                         "0052's declared box rule): %s" % (BOX_RULE_KEEP, ", ".join(
                             f"v{a['apex_vertex']} {a['line_radius_min_m']} < {BOX_RULE_KEEP} x {a['radius_v0171_rule_m']} m"
                             for a in short)))

    # The kn5/AC world is z-MIRRORED relative to the engine local frame (verified against the
    # installed dummies: kn5 z = -engine z). An unflipped line sends the AI down a ghost mirror
    # route through the terrain — they launch and never come back (ledger 0023). Flip once, here.
    for p in line["pts"]:
        p[2] = -p[2]
    for f in line["fwd"]:
        f[2] = -f[2]
    payload = None
    if line.get("payload") == "kunos":
        for nm in line["normal"]:
            nm[2] = -nm[2]
        payload = kunos_payload(line)

    if args.out:
        out = args.out
    else:
        base_dir = (args.src if args.src.is_dir() else src.parent.parent) / "ai"
        out = base_dir / args.layout if args.layout else base_dir
    out.mkdir(parents=True, exist_ok=True)
    write_ai(line, out / "fast_lane.ai")
    if not args.no_pit_copy:
        shutil.copyfile(out / "fast_lane.ai", out / "pit_lane.ai")
    write_sides(line, out)
    lap_m = line["length"][-1] + (line["ds"] if closed else 0.0)
    kind = "closed loop" if closed else "point-to-point"
    report = {
        "status": "GENERATED DRAFT from the built centreline — not an in-game recording (docs/HANDOFF.md "
                  ":284, ledger 0023). Replace file-for-file with CSP's fast_lane.ai.candidate recorded "
                  "in this layout.",
        "layout": args.layout, "direction": mode, "race_furniture": race, "lane_offset": use_offset,
        "frame": how_frame, "points": len(line["pts"]), "spacing_m": round(line["ds"], 3),
        "lap_m": round(lap_m, 1), "lap_s_est": round(line["lap_s"], 1),
        "offset_points": n_off, "offset_max_m": round(max(line["off"]) if line["off"] else 0.0, 3),
        "clearance": chk,
        "geometry": geo,
    }
    if opts is not None:
        report["ai_0052"] = {"opts": {k: v for k, v in opts.items() if k != "verify"}, "built": built_src,
                             "payload": payload}
    if corridor is not None:
        report["corridor"] = {
            "declaration": f"{bands_path.name} corridors.{args.layout} (token {corridor['token']})",
            "zones": corridor["zones"], "check": chk_c,
            "open_corners": [{k: c[k] for k in ("apex_vertex", "zone", "D_deg")} for c in corridor["corners"]],
            "corners_on_the_floor_fillet": corridor["corners_skipped"],
            "face_folds_trimmed": corridor["face_folds"],
            "min_radius_m": geo["min_radius_m"], "min_speed_kmh": geo["min_speed_kmh"],
            "wall_clear_min_m": chk_c["min_clear_m"],
            "points_in_open_box": geo["corridor"]["points_in_open_box"],
            "start_index": (geo.get("start") or {}).get("index"),
        }
    (out / "ai_draft.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"{kind}, {len(line['pts']):,} pts at {line['ds']:.2f} m over {lap_m:,.1f} m; "
          f"est lap {line['lap_s']:.1f} s ({max(line['v']) * 3.6:.0f} km/h peak) -> {out}")
    print("  " + verify(out / "fast_lane.ai"))
    if args.install:
        dst = args.install / "ai"
        dst.mkdir(parents=True, exist_ok=True)
        for f in ("fast_lane.ai", "pit_lane.ai", "side_l.csv", "side_r.csv"):
            if (out / f).exists():
                shutil.copyfile(out / f, dst / f)
        print(f"  -> installed to {dst}")


if __name__ == "__main__":
    main()
