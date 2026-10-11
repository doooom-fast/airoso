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


# --- resampling ----------------------------------------------------------------

def _resample(pts: list[list[float]], widths: list[float], spacing: float, closed: bool,
              extra: list[list[float]] | None = None):
    """Linear resample of the polyline (+widths, + any per-vertex channels) to ~spacing metres.

    Returns (pts, widths, ds) — or (pts, widths, ds, extras) when ``extra`` channels are given.
    Every channel is index-aligned with ``pts``. Widths interpolate linearly; the ``extra``
    channels are DECLARATIONS (divider half-width, barrier inset) and take the larger of the two
    bracketing vertices, so a station between an open vertex and a divider vertex is already
    judged as the divider's — the same nearest-vertex reading the write-time check applies."""
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
                out_c[c].append(ca + (cb - ca) * t if c == 0 else max(ca, cb))
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


def build_line(pts, widths, *, closed: bool, spacing: float, lat_g: float, decel_g: float,
               accel_g: float, vmax_kmh: float, margin_m: float,
               dh: list[float] | None = None, inset: list[float] | None = None,
               lane_offset: bool = True, start_xz: tuple[float, float] | None = None) -> dict:
    """Build the line in the ENGINE frame (x=E, y=up, z=N; right of travel = (tz, −tx)).

    ``dh``/``inset`` are per-vertex channels aligned with ``pts`` (divider half-width, kerb-line
    barrier inset); ``lane_offset=False`` keeps the line on the centreline whatever they say (no
    ramps, no smoothing — the pre-0047 line). With the offset on: lane policy -> cosine ramps ->
    offset polyline -> loop trim -> corner fillets + curvature bound inside the lane -> (start rotation) -> resample at
    ``spacing`` -> curvature bound again, normal moves only (spacing kept). ``start_xz`` (engine XZ, closed lines):
    point 0 is that point projected onto the line — the start/finish line; default the first station's
    point. The returned per-point channels (widths, dh, inset, base, off) are the nearest station's,
    and ``geometry`` carries the ramps, folds, smoothing and the audit's measurements."""
    n_in = len(pts)
    dh = list(dh) if dh is not None else [0.0] * n_in
    inset = list(inset) if inset is not None else [0.0] * n_in
    if len(dh) != n_in or len(inset) != n_in:
        raise ValueError(f"channel length mismatch: pts {n_in}, dh {len(dh)}, inset {len(inset)}")
    base, widths_s, ds0, (dh_s, inset_s) = _resample(pts, widths, spacing, closed, extra=[dh, inset])
    n0 = len(base)
    tan_xz = [_unit_xz(t[0], t[2]) for t in _tangents(base, closed, ds0, span=TANGENT_SPAN)]
    lo, hi = lane_corridor(widths_s, dh_s, inset_s, CHECK_CLEAR_M + CORRIDOR_TOL_M)
    lo_c, hi_c = lane_corridor(widths_s, dh_s, inset_s, FILLET_COMFORT_CLEAR_M)
    st = _Stations(base, tan_xz, lo, hi, road_radius(base, closed), closed, ds0, lo_c, hi_c)
    geo: dict = {"ramps": [], "ramp_clamped": 0, "corner_approach": [], "folds": [], "fillets": [],
                 "smoothing": [], "start": None}

    if lane_offset:
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
    n = len(P)
    idx = (lambda i: i % n) if closed else (lambda i: min(max(i, 0), n - 1))
    assoc = st.associate(P)
    if lane_offset:
        for i, p in enumerate(P):
            p[1] = st.y_at(p[0], p[2], assoc[i])
    pts = P
    off = [st.lat(p[0], p[2], assoc[i]) for i, p in enumerate(P)] if lane_offset else [0.0] * n
    widths = [widths_s[k] for k in assoc]
    dh = [dh_s[k] for k in assoc]
    inset = [inset_s[k] for k in assoc]
    geo.update(line_geometry(P, closed, st, assoc, off, ds))

    radius = [_circumradius(pts[idx(i - 1)], pts[i], pts[idx(i + 1)]) for i in range(n)]
    for _ in range(2):                                     # light smooth: min of neighbours window
        radius = [min(radius[idx(i - 1)], radius[i], radius[idx(i + 1)]) for i in range(n)]

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
    side_l, side_r = [], []
    for i in range(n):
        w, d, s, o = widths[i], dh[i], inset[i], off[i]
        left_b = d if d > 0.0 else -(w / 2.0 - s)
        right_b = w / 2.0 - s
        side_l.append(max(0.5, (o - left_b) - margin_m))
        side_r.append(max(0.5, (right_b - o) - margin_m))
    return {"pts": pts, "v": v, "length": length, "radius": radius, "fwd": fwd, "grade": grade,
            "gas": gas, "brake": brake, "side_l": side_l, "side_r": side_r, "off": off,
            "base": [base[k] for k in assoc], "station": assoc, "dh": dh, "inset": inset, "widths": widths,
            "ds": ds, "lap_s": lap_s, "closed": closed, "geometry": geo}


def write_ai(line: dict, out: Path) -> None:
    n = len(line["pts"])
    side_l = line.get("side_l") or line["side"]
    side_r = line.get("side_r") or line["side"]
    buf = bytearray()
    buf += struct.pack("<4i", 7, n, int(line["lap_s"] * 1000), n)
    for i, p in enumerate(line["pts"]):
        buf += struct.pack("<4fi", p[0], p[1], p[2], line["length"][i], i)
    buf += struct.pack("<i", n)
    for i in range(n):
        f = line["fwd"][i]
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
            f"lap {lap / 1000:.1f} s, extras={'yes' if len(d) > 16 + count * 20 + 4 else 'NO'}")


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
                         "(median island; centre chain + kerb-line inset for race layouts); none: "
                         "the centreline, as before")
    ap.add_argument("--race-furniture", choices=("auto", "on", "off"), default="auto",
                    help="consult data/barrier_bands.json: auto = layouts[].race_furniture")
    ap.add_argument("--bands", type=Path, help="barrier bands file (default data/barrier_bands.json)")
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
    if race:
        centre_w = _channel(bands_path, "centre_w_by_vertex", n, "barrier") or zeros
        inset = _channel(bands_path, "edge_inset_by_vertex", n, "barrier") or zeros
    else:
        print("  race furniture OFF for this line: centre chain / kerb-line inset not applied")
    dh = [max(iw / 2.0, cw / 2.0) for iw, cw in zip(island, centre_w)]
    use_offset = args.lane_offset == "auto"
    fwd_order = {"pts": [list(p) for p in pts], "widths": list(widths), "dh": dh, "inset": inset,
                 "island": island}
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
    line = build_line(pts, widths, closed=closed, spacing=args.spacing, lat_g=args.lat_g,
                      decel_g=args.decel_g, accel_g=args.accel_g, vmax_kmh=args.vmax_kmh,
                      margin_m=args.margin_m, dh=dh, inset=inset, lane_offset=use_offset,
                      start_xz=start_xz)
    geo = line["geometry"]
    if geo.get("start") is not None:
        geo["start"]["source"] = start_src or "first station (no AC_TIME_0 declared)"

    # Write-time self-check against the DECLARATION (per-vertex, forward order, engine frame).
    chk = check_lane_clearance(line["pts"], fwd_order["pts"], fwd_order["widths"], fwd_order["dh"],
                               fwd_order["inset"], fwd_order["island"], closed=closed,
                               expect_right=(mode == "forward"))
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
    if geo["backward_steps"] or geo["self_crossings"]:
        raise SystemExit("REFUSED: the line still folds (backward step / self-crossing) — see the geometry line above")
    if use_offset and (geo["turns_over_limit"] or geo["radius_below_floor"]):
        raise SystemExit(f"REFUSED: the line turns more than {TURN_MAX_DEG:g} deg in a step where the road does "
                         f"not, or runs under its radius floor — see the geometry line above")

    # The kn5/AC world is z-MIRRORED relative to the engine local frame (verified against the
    # installed dummies: kn5 z = -engine z). An unflipped line sends the AI down a ghost mirror
    # route through the terrain — they launch and never come back (ledger 0023). Flip once, here.
    for p in line["pts"]:
        p[2] = -p[2]
    for f in line["fwd"]:
        f[2] = -f[2]

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
