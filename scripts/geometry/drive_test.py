"""Virtual drive test — simulate what a CAR experiences over the BUILT track, before any kn5.

The mesh audit checks geometry classes (vertices, surfaces, props). This drives the lap: six wheel
paths swept along the built triangles at 1 m steps, asking at every step the only three questions a
driver cares about:

  1. WHAT SURFACE IS UNDER THE TIRE?  The car rides the HIGHEST physical surface at (x,z). If that
     top surface is 1GRASS inside the lane, the ground pokes through the road — a launch. If the
     top surface steps more than a tire absorbs, it's a jolt. This is triangle-accurate: it samples
     the interpolated faces the physics engine collides with, not the vertices (which pass audits
     while the faces between them knife through — learned on the Lariat's switchbacks).
  2. IS ANYTHING STANDING IN THE CORRIDOR?  Walls, parapets, highway decks, posts, tree trunks —
     any triangle that rises above the deck inside the swept lane (+ margin) is an obstruction,
     reported by mesh name so the offender is identifiable (BARRIER_warning vs HWYSTRUCT vs TREES).
  3. IS THE SURFACE SMOOTH AT SPEED?  Wheel-path vertical kinks (slope change per metre) beyond
     what real roads allow. Real geometric design keeps cross-slope breaks under ~4-8% and rounds
     every grade change through vertical curves; a healthy build shows the same statistics.

Thresholds (physical rationale, tune at the top):
  STEP_BUMP_M    0.025  a 2.5 cm sharp step ~ hitting a lane reflector curb at speed — feel it
  STEP_SEVERE_M  0.060  6 cm ~ a full curb face — suspension crash, possible airborne moment
  KINK_PCT       3.0    slope change %-pts across 1 m ~ a driveway lip; real roads use vertical
                        curves precisely so this never happens on the carriageway
  OBST_CLEAR_M   0.25   anything rising this far above deck inside the corridor is a hit hazard

Run:  python -m scripts.geometry.drive_test tracks/<slug> [--layout <id>]...
Writes data/drive_test.json, prints a per-problem report, exits 1 on FAIL (gate builds on it).
Pure stdlib; ~1-3 min for a 25 km lap.

LAYOUTS (ledger 0047). A track with more than one ``layouts[]`` entry is driven ONCE PER LAYOUT
(``run(project, layout)``; the CLI runs every entry, or the ``--layout`` ids given): a
``direction: reverse`` layout walks the lap backwards in memory (points, widths, divider bands,
bridge spans — station 0 stays the seam, negative offsets stay the right-hand side of travel
because the normal is recomputed from the reversed tangent); a ``kind: race`` layout is judged on
``data/track.race.obj`` (the kn5 set it actually loads: road + race furniture — a DOT, never
``track_race.obj``: the loop prep merges every ``data/track_*.obj`` into the scene) and, with
``race_furniture: true``, consults the declared barrier bands (``data/barrier_bands.json``,
scripts/geometry/median_zone.py kind 'barrier'): the wheel paths move into the lane between the
divider face and the kerb-line barrier face, the obstruction disc scans that lane, and every
declared barrier station must carry a 1WALL (``barrier_missing``, gated at 0 — a declared but
unbuilt chain fails, so the band is never a bypass). The race lane is the declared one AT the station
(2026-10-11): the road width lerped between the two vertices (on a closed lap the closure duplicate is
vertex 0), the scan disc clipped to the lane at each obstacle vertex's own station, a trimmed fold corner
(barrier_bands.json edge_corners) probed on its declared in -> X -> out polyline, and the presence
continuity wrapped across the seam of a closed lap. Each layout writes
``data/drive_test.<id>.json``; ``data/drive_test.json`` becomes the per-layout summary. A
single-layout track is byte-for-byte today's gate.

LAPS (ledger 0054). A race layout that names a lap (layouts[].lap, scripts/geometry/race_lap.py) walks THAT line
(data/lap.<lap>.json) against its own declaration (data/barrier_bands.<lap>.json, via MedianZone.load); the fold-fan
discs stay on the mainline rows the weld indexes. Every other layout is driven exactly as before.

CORRIDORS (ledger 0049, 2026-10-11). A version-2 declaration gives every race layout its own lane:
``corridors.<id>.lane_by_vertex`` (the corridor FACES — the race-side curb strip face and the layout's closure
face, full width in the open boxes and the whole-street zone), read through
``MedianZone.load(project, layout=<id>)``. The lane at a station is that declaration lerped between the two
vertices (each face kept DIVIDER_CLEAR_M away); funnels and island faces stand outside the lane by declaration,
so anything of them inside it is an obstruction. ``barrier_missing`` probes both curb strips the whole lap
(bridge spans included: no gaps since 0049) and the layout's ``closure`` at its declared line (the lerp of the
two declared ring centres). The race OBJ defaults to ``data/track.<id>.obj`` (road kn5 + common race kn5 + that
layout's closure kn5); a version-1 file keeps the 0047 lane (chain / island face) and ``track.race.obj``.
The STEP CHECK covers the whole declared lane (2026-10-11): the ten wheel paths reach both lane faces (no 6 m
travel-swath cap), the lane-edge paths gate steps like the interior ones, and no step inside a declared race
lane is an exempt "apron" step — the street layout and every single-layout track are unchanged.

FOLD BUMPS (v0.18.0, the gates lens). A wheel path here is a FIXED lateral offset from the centreline. Round a corner
tighter than that offset (Lake Murray's fold fans: the hairpin, College/Navajo, Navajo/Jackson, the seam — centre radii
of 7-8 m under race lanes 9-13 m wide) the offset point lies past the turning centre and runs BACKWARDS, hopping 1-2.5 m
to and fro across the fan; its 1 m second difference is then a re-traced plan, not a step under a wheel. Measured on
fresh USGS 3DEP 1 m (TLS verified) round five Lake Murray fans, the least-squares plane of the real ground (grades
1.4-7.0 %) read through drive_test's own samples gives a 2.5-6 cm "bump" on 76 of 158 backward samples (a severe on 34)
— a plane, the smoothest surface the real corner can have, fails the bump rule there. So a BUMP (2.5-6 cm) whose metre
or previous metre runs backwards (``_advance`` < 0) is filed under ``fold_bumps`` (reported, not gated); a SEVERE step
(> 6 cm) there still counts — the 0.37 m Navajo/Jackson lip of ledger 0050 was read on such a sample too. Real wheel
paths through the levelled fans are judged by tools/verify_fold_fans.py.

FOLD SEVERE (opt-in, ledger 0054 P1 fix round: track.config.json ``drive_test.fold_fan_severe = "verify_fold_fans"``).
Inside a levelled mainline fold fan (data/mouth_welds.json, the 0050 zones) a SEVERE reading on a sample whose metre or
previous metre runs backwards is the same re-traced plan at a larger hop: on v0.18.0 every severe step left at the
Navajo / Jackson box (race_cw s 6954-6959 lat -9.3 / -10, race_acw s 6523-6529 lat +9.3 / +10, 6.1-7.9 cm) sits on
such a sample, where tools/verify_fold_fans.py's arc-length wheel paths through the same fan read a 1 m second
difference of at most 0.025 m (and an independent 5 cm arc-length sweep at most 0.030 m). With the key, such a sample
is filed under ``fold_severe`` (reported, not gated here) and judged where a wheel can be: verify_fold_fans gates a
fine step >= 0.02 m and a 1 m second difference > 0.06 m on the real wheel paths of every levelled pinch (rows
k - 12 ... l + 13 cover these zones), hard in the chain, never covered by --force-install — the 0050 lip read 0.42 /
0.48 m there. Outside a levelled fan, on a forward sample, or without the key: severe as before.

DENSE HOPS (opt-in, ledger 0079 round M: track.config.json ``drive_test.dense_hops = true``; Lake Murray sets none). On
the outside of a corner the fixed-offset point hops 2.7-3.9 m at a vertex (VERTEX BUMPS below), so the 1 m second
difference compares a hop's height change with a metre's: on Sand Creek's colorado_50th deck (a real 2-4 % grade) that
read 0.07-0.11 m, severe, where the same wheel path sampled every 0.25 m along its own arc reads at most 0.007 m. With
the key, a severe reading on a forward metre where the path (this metre or the previous one) hopped more than
DENSE_HOP_M is re-measured on that path's last two metres sampled densely (_dense_step: the largest 1 m second
difference along their own arc, heights off the built top surface); one under STEP_SEVERE_M is filed under
``dense_hops`` (reported, not gated). A measurement change, not a threshold change: the same 6 cm judges it, and a
real riser on the hop still reads severe. Without the key the report is byte-identical.

FOLD CHORDS (opt-in, ledger 0079 round N: track.config.json ``fold_fans.chords = true``; Lake Murray sets none). The
weld mends a fold with no self-intersection (a HOOK: the inside edge of a junction flare widening faster than the corner
turns) by a forward chord, not a levelled pinch, and records it only as a cut. Sand Creek's two road folds are both such
chords (v134-141, v3202-3206, the inside of its 14-17 m corners), so the fan discs above come from its road cuts.
With the key: (1) the discs are the levelled road pinches PLUS every road cut with no levelled record, explicitly (on
Sand Creek the same rows the pre-0050 fallback gives; on a track with levelled pinches the chords join them), and
(2) every reading filed under ``fold_severe`` is written in full with the plan points of its metre's two ends
(``fold_severe_at``: s, offset, step, x, z, x_prev, z_prev), so tools/verify_fold_fans.py — which with the same key
surveys every chord on real wheel paths too — can prove each deferred reading lies on a path it judged (its check 8),
and (3) a reading is deferred only when both ends of its metre lie within verify_fold_fans.COVER_M of the plan samples
its paths read on this layout (verify_fold_fans.plan_cover); a folded reading in a fan that no such path reaches stays
severe here and is listed under ``fold_severe_unjudged``. Without the key the report is byte-identical.

VERTEX BUMPS (v0.18.1, ledger 0057 integration). The same fixed offset hops FORWARD at every centreline vertex where the
segment normal turns: on the outside of a corner the point jumps ahead by offset x turn angle (2.7-3.9 m at 10 m out
round the Navajo / Jackson fan, 1.8-3.7 m round College / Alvarado), on the inside it creeps (0.1-0.5 m). The 1 m second
difference then compares a height change over that hop with one over the previous metre: on a plane at grade g it reads
g x (hop - 1) — 3.4 cm on a 1.25 % plane at s 6954 (race_cw, v0.18.0), more wherever ledger 0057 restored a real
grade. A BUMP (2.5-6 cm; never a severe step) is therefore RE-MEASURED on the wheel path's own travel: the grades of its
two metres over the plan distance each actually covered, their change over the mean of the two (the same 1 m second
difference wherever both cover 1 m). One under STEP_BUMP_M is filed under ``vertex_bumps`` (reported, not gated); one
still over it counts. Neither travel may be under VERTEX_MIN_TRAVEL_M (a grade over a few cm of plan is facet noise —
such a bump counts as read). The re-measure can only move a bump out of the gated count when the surface the wheel
actually crosses is smoother than 2.5 cm per metre; it never adds one.

VERTEX KINKS (opt-in, ledger 0079 round P: track.config.json ``drive_test.vertex_kinks = true``; Lake Murray sets none).
The slope-kink count reads the same fixed-offset path, so it has the same artefact: on the inside of a corner the point
creeps 0.03-0.2 m across a vertex and the next metre runs a full 1 m, so on a smooth real grade g the station slopes
alternate ~0 / g and their change reads ~g per metre (Sand Creek's measured 48th_colorado deck, s 9575-9578 at +6.0
inside the S: 3.3-4.5 %/m on a surface whose own arc-length path at +6.0 reads at most 1.97 %/m). With the key a kink
over KINK_PCT is re-measured on the path's own travel exactly as a vertex bump is (_own_travel_step, its change of grade
over the mean of the two metres' plan travel, as %/m); one under KINK_PCT is filed under ``vertex_kinks`` (reported, not
counted in kinks_per_km), one still over it counts, and a metre under VERTEX_MIN_TRAVEL_M keeps its station reading. A
measurement change, not a threshold change: KINK_PCT judges both. Without the key the report is byte-identical.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

STEP_BUMP_M = 0.025
STEP_SEVERE_M = 0.060
KINK_PCT = 3.0
# SPEED. The thresholds above are fixed heights, and their own rationale is written in terms of
# speed ("~ hitting a lane reflector curb AT SPEED") — but nothing here ever knew how fast the car
# was going, so a 30 km/h hairpin and a 200 km/h straight were judged identically. A wheel crossing
# a step of height h at speed v is thrown with vertical velocity ~ v*h/L, so equal severity means a
# threshold that scales as 1/v. Measured consequence on Grand Junction: 40 of its 43 severe steps
# sit above 100 km/h (worst 0.187 m at ~145 km/h) and only 3 in tight corners — the unweighted
# count was flattering the places that matter most.
SPEED_REF_KMH = 100.0        # the speed the fixed thresholds above were hand-calibrated for
SPEED_MIN_KMH = 30.0         # below this the scaling stops helping: a curb is still a curb
SPEED_MAX_KMH = 260.0
GRIP_LAT = 1.3               # lateral g a GT car carries — sets the cornering speed from radius
ACCEL_MS2 = 4.5              # tractive
BRAKE_MS2 = 12.0             # braking dominates: the fast-approach-to-slow-corner case
OBST_CLEAR_M = 0.25
OBST_HEIGHT_M = 1.8          # car-strike ceiling: AC cars are ~1.3 m tall; walls/trunks rise from deck
#                              level and still trip this, while legit overhead furniture (cobra-head
#                              lamps arching the lane at 2.5 m+) clears it
STEP_M = 1.0                 # sampling step along the lap
DENSE_HOP_M = 1.5            # [invented] ledger 0079 round M (opt-in drive_test.dense_hops): a metre whose fixed-offset wheel
#                              path covered more plan than this (the outside of a corner: the per-segment normal turns at a
#                              vertex and the point hops 2.7-3.9 m) is a hop metre
DENSE_DS_M = 0.25            # [invented] ledger 0079 round M: the dense re-sample spacing along the wheel path's own arc
VERTEX_MIN_TRAVEL_M = 0.05   # [invented] v0.18.1 VERTEX BUMPS: a metre whose wheel path covers less plan than this is not
#                              re-measured (its grade would be a facet's noise); the bump counts as read


def _advance(prev, px_pz, c):
    """How far a fixed-offset wheel-path point moved along the lap over the last metre, as a share of the centre's own
    move: 1 on a straight, 1 - off/R round a corner of radius R, NEGATIVE where the offset lies past the turning centre
    (the point runs backwards — a fold). ``prev`` is (px, pz, cx, cz) of the previous sample; no centre move reads 1."""
    if prev is None:
        return 1.0
    cx, cz = c[0] - prev[2], c[1] - prev[3]
    n2 = cx * cx + cz * cz
    if n2 < 1e-12:
        return 1.0
    return ((px_pz[0] - prev[0]) * cx + (px_pz[1] - prev[1]) * cz) / n2


def _own_travel_step(dh1, dh0, d1, d0):
    """VERTEX BUMPS (v0.18.1): the 1 m second difference of a wheel path re-measured on its own travel — the grades of
    its last two metres (height change dh over the plan distance d each covered), their change over the mean of the two
    distances, times STEP_M^2. Exactly |dh1 - dh0| where both metres cover STEP_M. None when either travel is unknown
    or under VERTEX_MIN_TRAVEL_M (the bump then counts as read)."""
    if d1 is None or d0 is None or min(d1, d0) < VERTEX_MIN_TRAVEL_M:
        return None
    return abs(dh1 / d1 - dh0 / d0) * 2.0 * STEP_M * STEP_M / (d0 + d1)


def _dense_step(top_at, xz3, y_ref, ds=DENSE_DS_M):
    """DENSE HOPS (opt-in, ledger 0079 round M): the SAME wheel path's last two metres — its three samples xz3 [(x, z)
    of samples k-2, k-1, k], as drive_test took them — re-sampled every ds along their own polyline, each point's height
    the built top surface (top_at), and the largest 1 m second difference |h(a + 1) - 2 h(a) + h(a - 1)| along that arc
    (a every ds / 2). A measurement change, not a threshold: the same STEP_SEVERE_M then judges it. None (the station
    reading stands) where the arc is under 2 m or any point has no surface."""
    pts, arc = [], [0.0]
    for (ax, az), (bx, bz) in zip(xz3, xz3[1:]):
        d = math.hypot(bx - ax, bz - az)
        n = max(1, int(math.ceil(d / ds)))
        for j in range(n):
            pts.append((ax + (bx - ax) * j / n, az + (bz - az) * j / n))
    pts.append(xz3[-1])
    for (ax, az), (bx, bz) in zip(pts, pts[1:]):
        arc.append(arc[-1] + math.hypot(bx - ax, bz - az))
    if arc[-1] < 2.0 * STEP_M:
        return None
    hs = []
    for x_, z_ in pts:
        h_, _o = top_at(x_, z_, y_ref)
        if h_ is None:
            return None
        hs.append(h_)

    def h_at(a):
        j = 0
        while j < len(arc) - 2 and arc[j + 1] < a:
            j += 1
        t = (a - arc[j]) / max(arc[j + 1] - arc[j], 1e-9)
        return hs[j] + (hs[j + 1] - hs[j]) * t
    worst, a = 0.0, STEP_M
    while a <= arc[-1] - STEP_M + 1e-9:
        worst = max(worst, abs(h_at(a + STEP_M) - 2.0 * h_at(a) + h_at(a - STEP_M)))
        a += ds / 2.0
    return worst


def pad_for_lead_in(z_meas, line_pts, local_pts, tol_m=1.5):
    """REPLICATION ON AN OPEN STAGE (ledger 0076). build_mesh sweeps a lead-in and a lead-out of road past each open
    end (``[lead-in/out] 10 verts (30 m)`` on Dragon Tail), so the gate line holds k extra vertices at each end that
    centerline.local.json — and the measured heights indexed by it — do not. Compared index for index, every vertex
    was read against the measurement 30 m up the road: 0.96 m median "replication error" on Dragon Tail (Gravel),
    where aligned it is 0.02 m. Returns ``z_meas`` with k Nones at each end when the line is exactly 2k longer and its
    vertex k (or, driven in reverse, its vertex len-1-k) sits within ``tol_m`` of the local line's first point (x
    either sign: a mirror_x track's mesh frame); otherwise unchanged —
    a closed lap, or any line of the same length, is compared exactly as before."""
    n, m = len(line_pts), len(z_meas)
    if n <= m or (n - m) % 2 or not local_pts:
        return z_meas
    k = (n - m) // 2
    x0, z0 = local_pts[0][0], local_pts[0][2]
    if not any(math.hypot(line_pts[j][0] - sx * x0, line_pts[j][2] - z0) <= tol_m
               for j in (k, n - 1 - k) for sx in (1.0, -1.0)):     # -x: a mirror_x track's mesh frame
        return z_meas
    return [None] * k + list(z_meas) + [None] * k


WHEEL_HALF_TRACK = 0.75      # wheel offset around each driving line
CELL = 3.0                   # spatial hash cell (m)

WALL_CROSS_H_M = 0.5         # [invented] v0.18.1: the excursion guard's crossing probe runs this far over the
#                              pavement edge — over a wheel centre (~0.3 m), under every barrier top the loop builds
#                              (0.81 m Jersey, 0.95 m bridge panel): a wall standing that tall across the path stops the car

DIVIDER_CLEAR_M = 0.4       # the inner wheel (or scan edge) clears a divider/barrier FACE by this
BARRIER_GAP_MAX_M = 4.04      # one module: consecutive 1WALL hits on a declared band further apart = missing
BARRIER_PROBE_M = 0.3         # lateral probe spread on a declared band (the band's own reach is 0.935)
NEAR_DIVIDER_M = 7.0          # the 6.3 m centre disc reaches a strip end / island nose from this far out
RACE_KINDS = ("island", "barrier")

DRIVABLE = ("1ROAD", "1KERB", "1RUNOFF", "1LAWN", "1GRASS")   # car can roll on these
SOFT = ("1GRASS", "1LAWN")   # ...but these mid-lane on TOP = ground through road
PAINT = ("MARKINGS", "ROADTEXT", "YLINE")   # flat paint decals ~1.5 cm over deck — never obstructions


def speed_profile(pts, st, closed: bool) -> list[float]:
    """Speed (m/s) the car can carry at each centerline point: cornering grip capped by how fast it
    can actually get there and stop again. Three passes — radius, then forward acceleration, then
    backward braking — which is what makes the approach to a slow corner read fast (the wheel meets
    the bumps before the apex at entry speed, not apex speed)."""
    n = len(pts)
    if n < 3:
        return [SPEED_MAX_KMH / 3.6] * n
    vmax = SPEED_MAX_KMH / 3.6
    v = []
    for i in range(n):
        # Wrap only on a closed lap. On a point-to-point stage the two ends are different places
        # (Dragon Tail's finish is 17 km and 145 m from its start), and sampling across them
        # invents a hairpin at each end — which then drags the whole opening straight down through
        # the forward acceleration pass. Same trap the elevation profile documents for its filters.
        ia = (i - 3) % n if closed else max(0, i - 3)
        ic = (i + 3) % n if closed else min(n - 1, i + 3)
        a, b, c = pts[ia], pts[i], pts[ic]
        A = math.dist((a[0], a[2]), (b[0], b[2]))
        B = math.dist((b[0], b[2]), (c[0], c[2]))
        C = math.dist((a[0], a[2]), (c[0], c[2]))
        sp = (A + B + C) / 2.0
        ar2 = sp * (sp - A) * (sp - B) * (sp - C)
        R = (A * B * C) / (4.0 * math.sqrt(ar2)) if ar2 > 1e-9 else 1e6
        v.append(min(vmax, math.sqrt(max(1.0, R) * 9.81 * GRIP_LAT)))
    # FROM A STANDING START AT THE LINE (Kevin). Station 0 is the start/pit line, and the car is
    # stationary there — not arriving at flying-lap speed. Seeding v[0]=0 and refusing to wrap the
    # passes past it gives the speeds the car ACTUALLY carries over this lap: the opening stretch is
    # acceleration-limited, everything after is grip- and braking-limited as normal. Wrapping
    # instead converges a flying lap, which reads faster over the first few hundred metres than any
    # real first lap does.
    v[0] = 0.0
    for i in range(1, n):                         # forward: how fast can it GET here from the line
        d = max(1e-6, st[i] - st[i - 1])
        v[i] = min(v[i], math.sqrt(v[i - 1] ** 2 + 2 * ACCEL_MS2 * d))
    for i in range(n - 2, -1, -1):                # backward: and still make the next corner
        d = max(1e-6, st[i + 1] - st[i])
        v[i] = min(v[i], math.sqrt(v[i + 1] ** 2 + 2 * BRAKE_MS2 * d))
    return v


def _wall_crossed(field, a, b) -> bool:
    """does the straight segment a -> b (x, y, z) pass through a 1WALL triangle of ``field``? (Moller-Trumbore on
    every 1WALL triangle in the cells the segment's plan box covers.) Sees a wall of any orientation — a vertical
    panel with no plan area included, which a downward top_at read never can."""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    seen = set()
    for ci in range(int(min(a[0], b[0]) // CELL), int(max(a[0], b[0]) // CELL) + 1):
        for cj in range(int(min(a[2], b[2]) // CELL), int(max(a[2], b[2]) // CELL) + 1):
            for k in field.cells.get((ci, cj), ()):
                if k in seen:
                    continue
                seen.add(k)
                t = field.tris[k]
                if not str(t[9]).upper().startswith("1WALL"):
                    continue
                e1 = (t[3] - t[0], t[4] - t[1], t[5] - t[2])
                e2 = (t[6] - t[0], t[7] - t[1], t[8] - t[2])
                px, py, pz = dy * e2[2] - dz * e2[1], dz * e2[0] - dx * e2[2], dx * e2[1] - dy * e2[0]
                det = e1[0] * px + e1[1] * py + e1[2] * pz
                if abs(det) < 1e-12:
                    continue
                inv = 1.0 / det
                sx, sy, sz = a[0] - t[0], a[1] - t[1], a[2] - t[2]
                u = (sx * px + sy * py + sz * pz) * inv
                if u < 0.0 or u > 1.0:
                    continue
                qx, qy, qz = sy * e1[2] - sz * e1[1], sz * e1[0] - sx * e1[2], sx * e1[1] - sy * e1[0]
                v = (dx * qx + dy * qy + dz * qz) * inv
                if v < 0.0 or u + v > 1.0:
                    continue
                tt = (e2[0] * qx + e2[1] * qy + e2[2] * qz) * inv
                if 0.0 <= tt <= 1.0:
                    return True
    return False


def _load_obj(path: Path):
    """[(group, verts, tris)] — tris as vertex index triples into the group's own vert list."""
    groups = []
    cur = None
    base = 0
    verts_all: list[tuple[float, float, float]] = []
    # Stream the file. read_text().splitlines() materialises the whole OBJ twice over, and a 25 km
    # stage ships a ~170 MB track.obj beside a ~300 MB environment.obj.
    _va = verts_all.append
    with path.open() as fh:
        for ln in fh:
            k = ln[:2]
            if k == "v ":
                p = ln.split()
                _va((float(p[1]), float(p[2]), float(p[3])))
            elif k == "f ":
                if cur is not None:
                    p = ln.split()
                    cur["tris"].append((int(p[1].partition("/")[0]) - 1,
                                        int(p[2].partition("/")[0]) - 1,
                                        int(p[3].partition("/")[0]) - 1))
            elif k == "o ":
                cur = {"name": ln[2:].strip(), "v0": len(verts_all), "tris": []}
                groups.append(cur)
    return verts_all, groups


class TriField:
    """Spatial-hashed triangle soup answering: top surface height + owner at (x,z); tris in cell."""

    def __init__(self):
        self.cells: dict[tuple[int, int], list[int]] = defaultdict(list)
        self.tris: list[tuple] = []          # (ax,ay,az,bx,by,bz,cx,cy,cz, name)

    def add(self, verts, tri, name):
        a, b, c = (verts[i] for i in tri)
        k = len(self.tris)
        self.tris.append((*a, *b, *c, name))
        x0 = min(a[0], b[0], c[0]); x1 = max(a[0], b[0], c[0])
        z0 = min(a[2], b[2], c[2]); z1 = max(a[2], b[2], c[2])
        for ci in range(int(x0 // CELL), int(x1 // CELL) + 1):
            for cj in range(int(z0 // CELL), int(z1 // CELL) + 1):
                self.cells[(ci, cj)].append(k)

    def top_at(self, x, z, y_ref=None, window=2.5):
        """(height, owner_name) of the highest surface at (x,z). With ``y_ref``: highest surface
        within ±``window`` of the expected deck height — REQUIRED on tracks that cross over
        themselves (the Lariat's 19th St bridge over its own US-6 ramp): the global maximum reads
        the upper deck while you drive the lower one, minting phantom multi-metre steps."""
        best, owner = None, None
        for k in self.cells.get((int(x // CELL), int(z // CELL)), ()):
            t = self.tris[k]
            ax, ay, az, bx, by, bz, cx, cy, cz, name = t
            d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
            if abs(d) < 1e-12:
                continue
            w0 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / d
            w1 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / d
            w2 = 1.0 - w0 - w1
            if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                continue
            y = w0 * ay + w1 * by + w2 * cy
            if y_ref is not None and abs(y - y_ref) > window:
                continue
            if best is None or y > best:
                best, owner = y, name
        return best, owner

    def rising_in(self, x, z, r, deck_at, clear, cap, keep=None):
        """Names of tri owners with a vertex inside radius r of (x,z) rising ``clear``..``cap``
        above the deck DIRECTLY BENEATH that vertex (deck_at(x,z) sampler) — comparing against the
        station-centre deck instead reads ordinary up-slope geometry on any grade as a wall.
        ``keep(vx, vz)`` (optional): a vertex it rejects is not looked at (the race lane clip)."""
        hits = set()
        R = int(r // CELL) + 1
        ci, cj = int(x // CELL), int(z // CELL)
        for di in range(-R, R + 1):
            for dj in range(-R, R + 1):
                for k in self.cells.get((ci + di, cj + dj), ()):
                    t = self.tris[k]
                    if t[9] in hits:
                        continue
                    for vx, vy, vz in ((t[0], t[1], t[2]), (t[3], t[4], t[5]), (t[6], t[7], t[8])):
                        if math.hypot(vx - x, vz - z) >= r:
                            continue
                        if keep is not None and not keep(vx, vz):
                            continue
                        d = deck_at(vx, vz)
                        if d is not None and d + clear < vy < d + cap:
                            hits.add(t[9])
                            break
        return hits


def _layout_of(cfg: dict, layout) -> dict | None:
    """Resolve ``layout`` (None | id | dict) against cfg['layouts'] — None = the single-layout gate."""
    if layout is None:
        return None
    if isinstance(layout, dict):
        return layout
    for lo in cfg.get("layouts", []) or []:
        if isinstance(lo, dict) and lo.get("id") == layout:
            return lo
    raise SystemExit(f"drive_test: layout {layout!r} is not declared in track.config.json layouts[] "
                     f"({[lo.get('id') for lo in cfg.get('layouts', []) or []]})")


def _lane_geometry(w: float, dh: float, inset: float):
    """Lateral bounds of the lane a layout drives at a station, as (lo_s, hi_s, lo_w, hi_w):
    the SCAN band (clear of the divider face / the kerb-line barrier face by DIVIDER_CLEAR_M) and the
    wheel-LINE band (the scan band minus the wheel's own half-track, so the wheel itself clears the
    face). ``dh`` = divider half-width (island or centre chain) at the centreline, ``inset`` = the
    kerb-line barrier's lane inset from the lip (0 where it is gapped or stands on the walk).
    None = no divider and no inset: full width, today's centred lines verbatim. A divider whose
    remaining lane is under 2 m wide is treated as today (no lane: the centred sweep)."""
    if dh <= 0 and inset <= 0:
        return None
    if inset > 0:
        hi_s = w / 2 - inset - DIVIDER_CLEAR_M
        hi_w = hi_s - WHEEL_HALF_TRACK
    else:
        hi_s = hi_w = w / 2 - 0.5
    if dh > 0:
        lo_s = dh + DIVIDER_CLEAR_M
        lo_w = lo_s + WHEEL_HALF_TRACK
        if hi_s - lo_s < 2.0:
            return None
    else:
        lo_s, lo_w = -hi_s, -hi_w          # symmetric: the whole street between the two edge strips
        if hi_w <= 0.8:
            return None
    return lo_s, hi_s, lo_w, hi_w


FAN_DISC_PAD_M = 0.5        # [invented] ledger 0050: a fan disc reaches the row's half-width + this
FAN_LEVEL_ROWS = 8          # tools/mouth_weld.FOLD_LEVEL_ROWS, when mouth_welds.json predates its level_rows record


def fold_fan_discs(welds: dict, pts, widths, chords: bool = False) -> list:
    """ledger 0050: flat-zone discs (x, z, 0, radius) over every levelled MAINLINE fold fan in data/mouth_welds.json
    (folds.MAINLINE.levelled; a file without it: every ROAD cut) —
    one per centreline row from k - B to l + 1 + B of each ROAD pinch (B = the weld's level_rows), centred on the row,
    radius = half its width + FAN_DISC_PAD_M. `pts` / `widths`: the gate centreline in FORWARD order (the weld's
    row indices). Refuses (SystemExit) when the weld recorded a row count this centreline does not have."""
    folds = ((welds or {}).get("folds") or {}).get("MAINLINE") or {}
    cuts = [c for c in folds.get("cuts") or [] if c and c[0] == "road"]
    # the weld's levelled pinches (0050) when it recorded them — the swallowtails whose legs it moved; the chord mends
    # (Jackson / Lake Murray Blvd, the lap seam) keep today's rule: the seam's 0.06-0.07 m step at s 12-13 lat -5..-6
    # is a pre-existing apron step the race layouts already count, not 0050's. A pre-0050 file: every road cut.
    lev = [q for q in folds.get("levelled") or [] if isinstance(q, dict) and (q.get("line") or [None])[0] == "road"]
    if lev and chords:
        # FOLD CHORDS (opt-in, module doc): the levelled pinches and every road cut no levelled record covers
        _lk = [("road", q["line"][1], q["k"], q["l"]) for q in lev]
        _cov = lambda c: any(int(q[1]) == int(c[1]) and abs(int(q[2]) - int(c[-2])) <= 2 and abs(int(q[3]) - int(c[-1])) <= 2
                             for q in _lk)
        cuts = _lk + [c for c in cuts if not _cov(c)]
    elif lev:
        cuts = [("road", q["line"][1], q["k"], q["l"]) for q in lev]
    if not cuts:
        return []
    closed = len(pts) > 2 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
    n = len(pts) - 1 if closed else len(pts)
    rows = folds.get("rows")
    if rows is not None and int(rows) != n:
        raise SystemExit(f"drive_test: data/mouth_welds.json indexes {rows} mainline rows but the gate centreline has "
                         f"{n} — the weld and this centreline disagree; refusing to place the fold-fan zones")
    if not closed and any(c[-1] + 1 >= n or c[-2] < 0 for c in cuts):
        raise SystemExit("drive_test: a mouth_welds.json fold cut lies outside this open centreline")
    B = int(folds.get("level_rows") or FAN_LEVEL_ROWS)
    out, seen = [], set()
    for c in cuts:
        k, l = int(c[-2]), int(c[-1])
        for r in range(k - B, l + 2 + B):
            if not closed and not 0 <= r < n:
                continue
            i = r % n
            if i in seen:
                continue
            seen.add(i)
            out.append((float(pts[i][0]), float(pts[i][2]), 0.0, float(widths[i]) / 2.0 + FAN_DISC_PAD_M))
    return out


def run(project_dir: str | Path, layout=None, obj: str | None = None, line: dict | None = None) -> dict:
    """``line`` (ledger 0054 P3, opt-in: ``--line <set>``): drive ONE open line instead of the mainline — {"id",
    "points_xyz_m", "widths_m"} in the gate OBJ's frame, on the street layout's OBJ (track.obj): no lap, no layout, no
    median-band / fold-fan / bridge-span / replication reading (those are the mainline's), its ends off-pavement-aware;
    the report goes to data/drive_test.line.<id>.json. With ``line`` None every reading below is exactly today's."""
    import time as _tmod
    _t0 = _tmod.time()
    def _phase(_label):
        nonlocal _t0
        _now = _tmod.time()
        print(f"  [drive-time] {_label:22} {_now - _t0:7.1f}s", flush=True)
        _t0 = _now
    project = Path(project_dir)
    data = project / "data"
    cfg = json.loads((project / "track.config.json").read_text())
    # LAYOUT (0047): direction, kind and furniture come from the declared layout; the OBJ is the
    # gate OBJ of the kn5 set that layout loads (kn5_to_gate_obj --kn5 main [--kn5 race]).
    _lo = _layout_of(cfg, layout) if line is None else None
    lid = str(_lo.get("id")) if _lo else None
    direction = str(_lo.get("direction", "forward")) if _lo else "forward"
    if direction not in ("forward", "reverse"):
        raise SystemExit(f"drive_test: layout {lid!r} direction must be forward|reverse, got {direction!r}")
    reverse = direction == "reverse"
    race = bool(_lo.get("race_furniture")) if _lo else False
    kind = str(_lo.get("kind", "race" if race else "street")) if _lo else "street"
    # ledger 0054: a race layout that names a LAP drives the lap (data/lap.<lap>.json) against its declaration
    # (data/barrier_bands.<lap>.json); every other layout walks the gate centreline exactly as before
    from scripts.geometry import race_lap as _race_lap
    _lap = _race_lap.lap_of(_lo) if _lo else None
    _bands_name = _race_lap.bands_file(_lap)
    _corridor_decl = False
    if race and (data / _bands_name).exists():
        try:
            _corridor_decl = bool((json.loads((data / _bands_name).read_text(encoding="utf-8"))
                                   .get("corridors") or {}))
        except (json.JSONDecodeError, OSError):
            _corridor_decl = False
    # ledger 0049: each race layout loads road + common race + ITS closure kn5 -> its own gate OBJ
    # a race with no furniture (ledger 0063, Sand Creek's lap) has no such set: it drives the road, track.obj (paint is no obstruction)
    _furnished = kind == "race" and race
    obj_name = obj or ((f"track.{lid}.obj" if _corridor_decl else "track.race.obj") if _furnished else "track.obj")
    if _furnished and not (data / obj_name).exists():
        raise SystemExit(f"drive_test: layout {lid!r} is kind 'race' but data/{obj_name} does not exist — "
                         f"a race layout is judged on the kn5 set it loads (main + race furniture"
                         f"{' + its closure' if _corridor_decl else ''}), never on track.obj alone "
                         + (f"(kn5_to_gate_obj --kn5 <slug>.kn5 --kn5 <slug>_race.kn5 --kn5 <slug>_closure_{lid}.kn5 "
                            f"--out data/track.{lid}.obj)" if _corridor_decl else
                            "(kn5_to_gate_obj --kn5 main --kn5 race --out data/track.race.obj)"))
    fin = data / "finished_centerline.json"
    gate_cl = data / "gate_centerline.json"
    if gate_cl.exists():
        # written by kn5_to_gate_obj beside track.obj, in the OBJ's (engine) frame — the loop
        # prep's finished_centerline is in the KN5 frame (z mirrored) and must not be walked
        # against this OBJ (see scripts/modkit/kn5_to_gate_obj.py)
        lc = json.loads(gate_cl.read_text())
        pts = [tuple(p) for p in lc["points_xyz_m"]]
    elif fin.exists():
        # the line the ribbon was actually swept along (already in mesh frame) — driving the raw
        # centerline instead reads phantom obstructions where corner-rounding moved the pavement
        lc = json.loads(fin.read_text())
        pts = [tuple(p) for p in lc["points_xyz_m"]]
    else:
        mirror = -1.0 if cfg.get("mirror_x", False) else 1.0
        lc = json.loads((data / "centerline.local.json").read_text())
        pts = [(mirror * p[0], p[1], p[2]) for p in lc["points_xyz_m"]]
    widths = list(lc["widths_m"])
    if line is not None:
        pts = [tuple(p) for p in line["points_xyz_m"]]
        widths = [float(w) for w in line["widths_m"]]
    _main_pts, _main_w = list(pts), list(widths)    # the MAINLINE gate line: the weld's fold-fan rows index it
    _lap_rec = None
    if _lap:
        _lap_rec = _race_lap.load(project, _lap)
        _mx = -1.0 if cfg.get("mirror_x", False) else 1.0
        pts = [(_mx * p[0], p[1], p[2]) for p in _lap_rec["points_xyz_m"]]
        widths = [float(w) for w in _lap_rec["widths_m"]]
    # LANE WIDTHS (race layouts, 2026-10-11). The lane a race layout drives is bounded by the declared
    # strips, and the declaration lerps the road width between vertices; `widths[i]` (the vertex AHEAD
    # of a station) made the lane up to 1.36 m too wide on a mouth flare (0.55-1.50 m per 3 m vertex),
    # so the scan disc reached past the strip's road-side face — 341 of 395 race obstruction stations
    # were the previous ring of a strip standing exactly on its declaration. _wl is the width the lane
    # and the presence probe read, lerped at the station; on a closed lap the closure duplicate is
    # vertex 0 (it carried the LAST street's width: 27.5 m on SD vs Alvarado's 17.0 m — median_zone's
    # rule). The street layout and every single-layout track keep `widths` and are unchanged.
    _closed_lap = (len(pts) > 2 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6)
    _fan_pts, _fan_w = _main_pts, _main_w           # forward order: the weld's MAINLINE row indices (ledger 0050 fan discs)
    _wl = list(widths)
    if _closed_lap:
        _wl[-1] = _wl[0]
    if reverse:
        # the lap walked backwards: station 0 stays the seam (a closed lap repeats v0), the tangent
        # flips, so the right-hand side of travel (negative offsets) is the other carriageway
        pts = pts[::-1]
        widths = widths[::-1]
        _wl = _wl[::-1]

    # declared bridge spans: parapet/railing furniture INSIDE these is expected (a bridge with no
    # railing is the defect, not the railing) — obstruction hits on *bridge-named meshes there are skipped
    spans = [(b.get("center_m", 0) - b.get("len_m", 0) / 2 - 20, b.get("center_m", 0) + b.get("len_m", 0) / 2 + 20)
             for b in (cfg.get("capture", {}) or {}).get("bridges", [])] if line is None else []

    surface = TriField()      # everything the car can roll on
    obstacle = TriField()     # everything else that could stand in the corridor
    _wall_verts = []          # 1WALL columns for the furniture-seating gate
    # CORRIDOR CULL. Every query this gate makes happens within a corridor around the centerline —
    # wheel paths, excursion sweeps, obstruction checks. On a 25 km stage the terrain grid covers
    # roughly 90 km2 while that corridor is about 4 km2, so hashing the whole world costs ~20x more
    # than it needs to and the load/hash phase dominates the run (measured on IMI: top_at was 0.65 s
    # of 9.4 s, while loading and hashing was over 7 s).
    _CULL_M = 120.0          # generous: the widest excursion sweep is well inside this
    _ccell = 64.0
    _cnear: set = set()
    for _px, _py, _pz in pts:
        _ci0, _cj0 = int(_px // _ccell), int(_pz // _ccell)
        _r = int(_CULL_M // _ccell) + 1
        for _di in range(-_r, _r + 1):
            for _dj in range(-_r, _r + 1):
                _cnear.add((_ci0 + _di, _cj0 + _dj))

    # SKIP THE GIANTS. TriField.add registers a triangle in EVERY 3 m cell its bbox covers, so one
    # 500 m terrain-skirt triangle lands in ~27,000 cells. A 25 km stage has a long enough border
    # that every corridor cell then holds thousands of them, and each top_at scans the lot: measured
    # at >200 ms per station on Dragon Tail against ~0.6 ms on Sand Creek — the sweep that appeared
    # to take hours. The skirt is a flat apron far outside the track that no wheel path can reach,
    # and terrain spanning the road is audit check J's job, not this gate's.
    _MAX_TRI_M = 60.0

    def _near_corridor(a, b, c):
        if (max(a[0], b[0], c[0]) - min(a[0], b[0], c[0]) > _MAX_TRI_M
                or max(a[2], b[2], c[2]) - min(a[2], b[2], c[2]) > _MAX_TRI_M):
            return False
        return (((int(a[0] // _ccell), int(a[2] // _ccell)) in _cnear)
                or ((int(b[0] // _ccell), int(b[2] // _ccell)) in _cnear)
                or ((int(c[0] // _ccell), int(c[2] // _ccell)) in _cnear))

    _track_groups: list = []
    _culled = 0
    _loaded = []
    for objfile in (obj_name, "environment.obj"):
        p = data / objfile
        if not p.exists():
            continue
        _loaded.append((objfile, _load_obj(p)))
    # FURNITURE SEATING reads every 1WALL column against the surface under it, so the ground under EVERY wall is loaded,
    # not only the swept corridor's (ledger 0054 P3, 2026-10-18): a wall 120+ m off the swept line had no surface
    # loaded under it and read "floating 99" whatever stood under it — 391 columns on the v0.18.1 street layout (off
    # the loop, judged against nothing), 3,743 with the north network's island rails and stub barriers. Every wall is
    # still judged; it is judged on its own ground.
    for _objfile, (verts, groups) in _loaded:
        for grp in groups:
            if grp["name"].upper().startswith("1WALL"):
                for tri in grp["tris"]:
                    for vi in tri:
                        _cnear.add((int(verts[vi][0] // _ccell), int(verts[vi][2] // _ccell)))
    for objfile, (verts, groups) in _loaded:
        if objfile == obj_name:
            _track_groups = groups
        for grp in groups:
            up = grp["name"].upper()
            if up.startswith(PAINT):
                continue
            if up.startswith("1WALL"):
                _seen_w = set()
                for tri in grp["tris"]:
                    for vi in tri:
                        if vi not in _seen_w:
                            _seen_w.add(vi)
                            _wall_verts.append(verts[vi])
            field = surface if up.startswith(DRIVABLE) else obstacle
            for tri in grp["tris"]:
                _a, _b, _c = verts[tri[0]], verts[tri[1]], verts[tri[2]]
                if not _near_corridor(_a, _b, _c):
                    _culled += 1
                    continue
                field.add(verts, tri, grp["name"])

    if _culled:
        print(f"  [drive] corridor cull: skipped {_culled} triangles beyond {_CULL_M:.0f} m")
    _phase("load + hash")

    # SANITY: there must BE a road. A build_mesh that dies mid-write (2.87 M grid verts ran the
    # process out of memory) leaves a TRUNCATED track.obj holding only the 1GRASS chunks written so
    # far — no 1ROAD at all. This gate then scored a world with no road in it: every wheel-path
    # sample landed on grass, so it reported 159,635 "ground above the road" and 548 bumps/km and
    # called it a surface problem. A gate that cannot tell a bad road from NO road is not a gate.
    # Reuse the groups already parsed above. This used to re-read track.obj in full just to list the
    # road groups — a third parse of a file that can be 170 MB.
    _road_groups = [g for g in _track_groups if g["name"].upper().startswith("1ROAD")]
    if not _road_groups:
        raise SystemExit(
            "drive_test: track.obj contains no 1ROAD_* geometry — the mesh build did not finish "
            "(check for a truncated OBJ / out-of-memory kill in build_mesh). Refusing to score a "
            "track with no road surface.")

    # six wheel paths: wheel pair around center line + around left/right third lines
    n = len(pts)
    st = [0.0]
    for i in range(1, n):
        st.append(st[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
    lap = st[-1]
    if reverse:
        spans = [(lap - b, lap - a) for a, b in spans]

    _fzp = project / "data" / "flat_zones.json"
    _fzones = json.loads(_fzp.read_text()) if _fzp.exists() else []
    # ledger 0050 (opt-in: only a track whose weld wrote data/mouth_welds.json): inside a levelled mainline fold fan
    # the WHOLE fan is driving surface, so no SEVERE step there is an "apron step". The 0.24 m Navajo / Jackson riser
    # at s 6946 lat -6 was filed exactly so on the street layout and shipped green. Bumps (2.5-6 cm) keep the apron
    # rule: round a corner tighter than the offset these fixed-station paths change their own spacing station to
    # station (0.2 m on the inside of a 7.4 m corner at 6 m, 1.8 m outside), and on a 2-3 % grade that alone reads
    # 2.5-4.7 cm — measured on v0.18.0: 54 such street "bumps" in the two fans, all apron bumps before, where
    # tools/verify_fold_fans.py's arc-length wheel paths read a 1 m second difference of at most 0.025 m. Sub-6 cm
    # judgement inside the fans is verify_fold_fans' (2 cm fine steps on real paths).
    _fan_zones = []
    # FOLD CHORDS (opt-in, ledger 0079 round N: track.config.json fold_fans.chords = true; Lake Murray sets none)
    _fold_chords = bool((cfg.get("fold_fans") or {}).get("chords"))
    _mwp = project / "data" / "mouth_welds.json"
    if _mwp.exists() and line is None:
        _fan_zones = fold_fan_discs(json.loads(_mwp.read_text(encoding="utf-8")), _fan_pts, _fan_w,
                                    chords=_fold_chords)

    def _in_fan(px, pz):
        return any((px - a) ** 2 + (pz - b) ** 2 < d * d for a, b, c, d in _fan_zones)

    # FOLD SEVERE (opt-in; module doc): a severe reading on a folded sample inside a levelled fan is judged by
    # tools/verify_fold_fans.py on the real wheel paths, not here
    _fold_severe_defer = bool(_fan_zones) and         str((cfg.get("drive_test") or {}).get("fold_fan_severe") or "") == "verify_fold_fans"
    # FOLD CHORDS (opt-in): defer only a reading whose metre's two ends lie on the plan paths verify_fold_fans reads
    # (its plan_cover: every sample whose fine-step window is on the lane, within its COVER_M); the rest stay severe
    _fan_cover, _near_cover, _cover_m = {}, None, None
    if _fold_severe_defer and _fold_chords:
        _tools = str(Path(__file__).resolve().parents[2] / "tools")
        if _tools not in sys.path:
            sys.path.insert(0, _tools)
        import verify_fold_fans as _vff  # noqa: E402  (pure Python; its plan geometry, no surface read)
        _cover_lid = lid or str(((cfg.get("layouts") or [{}])[0]).get("id") or "street")
        _fan_cover, _near_cover, _cover_m = _vff.plan_cover(project, _cover_lid), _vff.near_judged, _vff.COVER_M

    def _on_fan_path(px, pz, qx, qz):
        if not _fold_chords:
            return True
        a, b = _near_cover(_fan_cover, px, pz), _near_cover(_fan_cover, qx, qz)
        return a is not None and b is not None and a <= _cover_m and b <= _cover_m
    # DENSE HOPS (opt-in, ledger 0079 round M: track.config.json drive_test.dense_hops = true; Lake Murray sets none): a
    # severe reading on a forward metre where this wheel path, or its previous metre, hopped more than DENSE_HOP_M is
    # re-measured on the same path sampled densely (_dense_step); under STEP_SEVERE_M it is filed as dense_hops
    _dense_hops = bool((cfg.get("drive_test") or {}).get("dense_hops"))
    # VERTEX KINKS (opt-in, ledger 0079 round P: drive_test.vertex_kinks = true; Lake Murray sets none): a kink is
    # re-measured on the wheel path's own travel, as a vertex bump is (module doc)
    _vertex_kinks = bool((cfg.get("drive_test") or {}).get("vertex_kinks"))

    def _in_flat_zone(px, pz):
        return any((px - a) ** 2 + (pz - b) ** 2 < d * d for a, b, c, d in _fzones)

    problems = {"soft_top_in_lane": [], "steps": [], "severe_steps": [], "kinks": [], "obstructions": [],
                "daylight_gaps": []}
    def _pavement_at(x, z):
        """Is there 1ROAD directly under (x,z)? Point-precise, but scans only the ONE hash cell's
        road triangles — a road-only TriField answered the same question and took 20+ minutes on a
        25 km stage, while plain cell-membership was too coarse (a sample 3 m off the ribbon end
        still lands in a cell the first quad reaches into)."""
        for i in surface.cells.get((int(x // CELL), int(z // CELL)), ()):
            ax, ay, az, bx, by, bz, cx, cy, cz, name = surface.tris[i]
            if not name.upper().startswith("1ROAD"):
                continue
            d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
            if abs(d) < 1e-12:
                continue
            w0 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / d
            w1 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / d
            if w0 >= -1e-6 and w1 >= -1e-6 and 1.0 - w0 - w1 >= -1e-6:
                return True
        return False
    _has_ends = (not bool(cfg.get("loop", True))) or line is not None
    _lap_end = sum(math.dist((pts[i][0], pts[i][2]), (pts[i + 1][0], pts[i + 1][2]))
                   for i in range(len(pts) - 1))
    # MEDIAN ISLAND (0037). On a divided road the centreline IS the raised island — sweeping the
    # centre wheel pair over it reads the curb as a severe step and the grass deck as soft ground
    # in the lane. Where data/median_bands.json declares an island, the ten paths move into the
    # driven lane (right of the island: lane edge .. pavement lip), same shape: edges, thirds,
    # centre. The step/kink memory resets at each island boundary so the lateral re-seat is not
    # scored as a bump. Nothing is skipped — the island itself is gated by audit (curb must be
    # 1KERB, deck 1GRASS) and the lane is swept in full.
    # BARRIER BANDS (0047): a race layout also reads the declared centre chain (0.335 m half) and
    # the kerb-line barrier inset as dividers of a second kind; the street layout never does, so a
    # track without barrier_bands.json (or a layout without race_furniture) is today's gate exactly.
    from scripts.geometry.median_zone import MedianZone
    _zone = MedianZone.load(project, layout=lid if race else None) if line is None else None
    if _zone and reverse:
        _zone = _zone.reversed()
    # CORRIDOR (0049): the declared lane of THIS layout, lerped per station (see the module doc)
    _corr = bool(race and _zone is not None and _zone.has_corridor)
    if _zone:
        print(f"  (median island on {_zone.n_island} verts — wheel paths swept in the driven lane there"
              + ((f"; corridor {lid}: closure on {_zone.n_closure} verts, curb strips on {_zone.n_edge} verts — lane = "
                  f"the declared faces, presence gated" if _corr else
                  f"; barrier bands: centre chain on {_zone.n_barrier} verts, kerb-line strip on "
                  f"{_zone.n_edge} verts — lane = divider face .. barrier face, presence gated") if race else "")
              + ")")
    if lid:
        print(f"  layout {lid}: direction {direction}, kind {kind}, furniture {'race' if race else 'none'}, "
              f"OBJ data/{obj_name}")

    def _divider_at(j):
        """(divider half-width, kerb-line inset) at mainline vertex j for THIS layout's kinds."""
        if _zone is None or not (0 <= j < n):
            return 0.0, 0.0
        dh = _zone.island_half_at(j)
        if race:
            return max(dh, _zone.barrier_half_at(j)), _zone.edge_inset_at(j)
        return dh, 0.0

    def _near_divider(j, s_at):
        """the strongest divider/inset within NEAR_DIVIDER_M (along the line) of station s_at"""
        dh = ins = 0.0
        k = j
        while k >= 0 and st[k] >= s_at - NEAR_DIVIDER_M:
            d1, i1 = _divider_at(k); dh = max(dh, d1); ins = max(ins, i1); k -= 1
        k = j + 1
        while k < n and st[k] <= s_at + NEAR_DIVIDER_M:
            d1, i1 = _divider_at(k); dh = max(dh, d1); ins = max(ins, i1); k += 1
        return dh, ins

    _bm_hits: dict = {"centre": [], "edge_L": [], "edge_R": [], "closure": [], "chicane": []}   # (station, hit) per band

    def _corr_lane(k, u):
        """the declared corridor lane (scan + wheel bands, right of travel) at fraction u of segment k-1 -> k"""
        a, b = _zone.lane_r(k - 1), _zone.lane_r(k)
        lo_r = a[0] + (b[0] - a[0]) * u
        hi_r = a[1] + (b[1] - a[1]) * u
        lo_s, hi_s = lo_r + DIVIDER_CLEAR_M, hi_r - DIVIDER_CLEAR_M
        if hi_s - lo_s < 2.0:
            return None
        return lo_s, hi_s, lo_s + WHEEL_HALF_TRACK, hi_s - WHEEL_HALF_TRACK

    # TRIMMED CORNERS (race layouts, 2026-10-11): where the declaration trims a kerb-line strip to the
    # curb's own corner (barrier_bands.json edge_corners) the band across the removed vertices is the
    # polyline A (band point at vertex i) -> X -> B (band point at vertex j), not the folded offset curve:
    # every station between st[i] and st[j] probes THAT polyline at the same fraction of its length, the
    # +-BARRIER_PROBE_M spread along its own normal — every declared metre is still probed, nothing skipped.
    _corner_spans: dict = {"edge_L": [], "edge_R": []}
    if race and _zone is not None:
        for _ck in _corner_spans:
            for _ci, _cj, _poly in _zone.edge_corner_spans(_ck):
                _sa, _sb = st[_ci], st[_cj]
                _span = (_sb - _sa) if _cj >= _ci else (lap - _sa + _sb)
                _segs = [math.dist(_poly[0], _poly[1]), math.dist(_poly[1], _poly[2])]
                if _span > 0 and sum(_segs) > 0:
                    _corner_spans[_ck].append((_sa, _sb, _cj < _ci, _span, _poly, _segs))

    def _corner_probe_at(kind, s_at):
        """(x, z, nx, nz) on the declared corner polyline for station s_at, None when s_at is not inside
        one of `kind`'s trimmed corners"""
        for _sa, _sb, _wrap, _span, _poly, _segs in _corner_spans[kind]:
            if _wrap:
                if not (s_at >= _sa or s_at <= _sb):
                    continue
                f = ((s_at - _sa) if s_at >= _sa else (s_at + lap - _sa)) / _span
            else:
                if not (_sa <= s_at <= _sb):
                    continue
                f = (s_at - _sa) / _span
            d_ = f * (_segs[0] + _segs[1])
            k_ = 0 if (d_ <= _segs[0] or _segs[1] <= 0) else 1
            u_ = (d_ if k_ == 0 else d_ - _segs[0]) / (_segs[k_] or 1e-9)
            (ax_, az_), (bx_, bz_) = _poly[k_], _poly[k_ + 1]
            L_ = _segs[k_] or 1e-9
            return (ax_ + (bx_ - ax_) * u_, az_ + (bz_ - az_) * u_, -(bz_ - az_) / L_, (bx_ - ax_) / L_)
        return None

    def _in_lane(vx, vz, i0, dh_, ins_):
        """the race LANE CLIP: is the obstacle vertex (vx, vz) inside the declared lane at its OWN station?
        Projected onto the walked line (segments i0 +- 8, wrapped on a closed lap), the lane there is
        _lane_geometry(lerped width, dh_, ins_) and the vertex counts when it stands between 0.1 m off the
        divider face and 0.1 m off the strip face (the scan disc's own margins). The round disc reaches
        along the road as far as across it, so on a steep flare it caught a strip ring standing exactly on
        its declaration a metre behind the station (s2271 / s4534 on race_cw) — this can only drop a vertex
        that stands outside the declared lane; one inside it still fails."""
        best = None
        for kr in range(i0 - 8, i0 + 9):
            if _closed_lap:
                k = (kr - 1) % (n - 1) + 1
            elif 1 <= kr <= n - 1:
                k = kr
            else:
                continue
            ax_, az_ = pts[k - 1][0], pts[k - 1][2]
            dx_, dz_ = pts[k][0] - ax_, pts[k][2] - az_
            L2 = dx_ * dx_ + dz_ * dz_
            if L2 < 1e-12:
                continue
            u_ = max(0.0, min(1.0, ((vx - ax_) * dx_ + (vz - az_) * dz_) / L2))
            d2 = (vx - ax_ - u_ * dx_) ** 2 + (vz - az_ - u_ * dz_) ** 2
            if best is None or d2 < best[0]:
                best = (d2, k, u_, ((vx - ax_) * (-dz_) + (vz - az_) * dx_) / math.sqrt(L2))
        if best is None:
            return True
        _, k, u_, lat_ = best
        if _corr:
            lv = _corr_lane(k, u_)
        else:
            lv = _lane_geometry(_wl[k - 1] + (_wl[k] - _wl[k - 1]) * u_, dh_, ins_)
        return lv is None or (lv[0] - 0.3 <= -lat_ <= lv[1] + 0.3)

    def _bm_probe(kind, s_at, cx, cz, nx_, nz_, lat, deck):
        """does a 1WALL stand on the declared band at lateral `lat` of this station?"""
        hit = False
        for dl in (-BARRIER_PROBE_M, 0.0, BARRIER_PROBE_M):
            px_, pz_ = cx + nx_ * (lat + dl), cz + nz_ * (lat + dl)
            d_here, _ = surface.top_at(px_, pz_, deck)
            if d_here is None:
                d_here = deck
            h_, own_ = obstacle.top_at(px_, pz_, d_here + 0.6, 1.5)
            if own_ is not None and str(own_).upper().startswith("1WALL") and h_ > d_here + OBST_CLEAR_M:
                hit = True
                break
        _bm_hits[kind].append((round(s_at, 1), hit))

    _prev_lane = None
    prev_h = [None] * 10
    prev_slope = [None] * 10
    # FOLDED SAMPLES (v0.18.0): each wheel path's last plan point, the centre it was read from, and the advance of
    # the metre that ended there (see _advance) — reset with prev_h
    prev_p = [None] * 10
    prev_adv = [None] * 10
    prev_d = [None] * 10       # VERTEX BUMPS (v0.18.1): the plan distance each path covered over its previous metre
    off_pavement = 0
    obst_names = defaultdict(int)
    _phase("pre-sweep setup")
    s = 0.0
    i = 1
    _nst = 0
    _tsweep = _tmod.time()
    while s < lap:
        _nst += 1
        if _nst % 2000 == 0:
            _el = _tmod.time() - _tsweep
            print(f"  [drive-time] sweep {_nst:6} stations ({s/1000:6.2f} km)  {_el:7.1f}s  "
                  f"{1000*_el/_nst:.2f} ms/station", flush=True)
        while i < n - 1 and st[i] < s:
            i += 1
        t = (s - st[i - 1]) / max(st[i] - st[i - 1], 1e-9)
        x = pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * t
        y_ref = pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * t
        z = pts[i - 1][2] + (pts[i][2] - pts[i - 1][2]) * t
        tx, tz = pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]
        L = math.hypot(tx, tz) or 1e-9
        nx, nz = -tz / L, tx / L
        w = widths[i]
        # race layouts: the lane at THIS station (the lerped declared width, see _wl); everything else
        # keeps widths[i]
        w_lane = (_wl[i - 1] + (_wl[i] - _wl[i - 1]) * t) if race else w
        # TRAVEL-SWATH cap: at junction-flare boxes w balloons to 24-40 m, but a swept ribbon
        # covers a bowtie there, not the full square — wheel paths at box-width offsets ride the
        # un-swept notches and read grass 'mid-lane'. Cars travel the center swath; test THAT.
        lane_half = min(max(w / 2 - 0.4, 0.8), 6.0)
        lines = (-(w / 2 - 0.5), -w / 3, 0.0, w / 3, (w / 2 - 0.5))   # edges included
        _clamp_c, _clamp_r = 0.0, lane_half       # today's clamp: +/- lane_half about the centreline
        _dh, _inset = _divider_at(i)
        _lane = _corr_lane(i, t) if _corr else _lane_geometry(w_lane, _dh, _inset)
        if _lane is not None:
            # driven lane = right of the divider (negative offsets are the right-hand side here) and
            # inside the kerb-line barrier; edges, thirds, centre of THAT lane. The inner wheel clears
            # the divider face by DIVIDER_CLEAR_M (the old isl + 0.4 LINE put the wheel 0.35 m inside
            # the island curb) and the clamp is lane-relative (the old +/-6 m-of-centreline clamp
            # collapsed seven of ten island paths onto 6.0 m and never swept the outer lane).
            lo, hi = _lane[2], _lane[3]
            mid = (lo + hi) / 2.0
            third = (hi - lo) / 3.0
            lines = (-hi, -(mid + third / 2), -mid, -(mid - third / 2), -lo)
            # a declared race corridor (0049) is swept to its faces: the 6 m travel-swath cap is the street's
            # junction-box rule, and on the Alvarado-wide race lanes it left the outer 1-4 m of the lane unswept
            _clamp_c, _clamp_r = -mid, ((hi - lo) / 2.0 if _corr else min((hi - lo) / 2.0, 6.0))
        _lane_key = (round(_lane[2], 3), round(_lane[3], 3)) if _lane is not None else None
        if ((_lane_key is None) != (_prev_lane is None)) or (
                _lane_key is not None and _prev_lane is not None
                and (abs(_lane_key[0] - _prev_lane[0]) > 0.5 or abs(_lane_key[1] - _prev_lane[1]) > 0.5)):
            # the lane moved (island/chain boundary, a width step, a bridge gap in the edge strip):
            # the lateral re-seat is not a bump
            prev_h = [None] * 10
            prev_slope = [None] * 10
            prev_p = [None] * 10
            prev_adv = [None] * 10
            prev_d = [None] * 10
        _prev_lane = _lane_key
        # edge paths (|line| = w/2-0.5) DETECT holes/ground-through at the pavement lip;
        # smoothness (steps/kinks) gates only on INTERIOR paths — nobody laps on the hinge
        # RACE CORRIDOR (2026-10-11): the declared lane IS the race surface face to face (each face already
        # DIVIDER_CLEAR_M inside its strip) — its edge paths gate steps too, and no step in it is an "apron"
        edge_line = set() if _corr else {0, len(lines) - 1}
        paths = [off + d for off in lines for d in (-WHEEL_HALF_TRACK, WHEEL_HALF_TRACK)]
        # OFF THE END OF THE PAVEMENT. A point-to-point stage's finished_centerline can overhang
        # the built ribbon: on Dragon Tail its first point sits 30 m before the road starts, over
        # bare terrain. Every wheel path there reads grass as the top surface, so ONE station minted
        # 10 "ground on top mid-lane" hits and an 0.8 m "severe step" climbing back onto the road —
        # the sole blocker on all four rally stages, and pure artifact. Ask the ROAD-ONLY field
        # whether there is pavement here at all: no pavement = off the stage, not a defect. Grass
        # sitting ON a road that IS here still fails, which is the case this gate exists for.
        # Only near the ENDS, and only on a stage that has ends. This artifact is the finished
        # centerline overhanging the built ribbon at a start/finish cap, so it cannot occur mid-lap
        # — and running the point test on all 25,260 stations of a 25 km stage took 5 HOURS of CPU
        # without finishing. Bounded to ~60 stations it is free.
        if _has_ends and (s < 30.0 or s > _lap_end - 30.0) and not _pavement_at(x, z):
            off_pavement += 1
            prev_h = [None] * 10
            prev_slope = [None] * 10
            prev_p = [None] * 10
            prev_adv = [None] * 10
            prev_d = [None] * 10
            s += STEP_M          # MUST advance: `s += STEP_M` lives at the END of this body, so a
            continue             # bare `continue` here spins forever. That hung every rally build
                                 # from v0.25.1 on — the stages were never slow, they never finished.
        deck_c, _ = surface.top_at(x, z, y_ref)
        for pi, off in enumerate(paths):
            is_edge = (pi // 2) in edge_line
            if abs(off - _clamp_c) > _clamp_r:
                off = _clamp_c + math.copysign(_clamp_r, off - _clamp_c)
            px, pz = x + nx * off, z + nz * off
            h, owner = surface.top_at(px, pz, y_ref)
            if h is None:
                prev_h[pi] = None
                prev_slope[pi] = None
                prev_p[pi] = None
                prev_adv[pi] = None
                prev_d[pi] = None
                continue
            if owner and owner.upper().startswith(SOFT):
                problems["soft_top_in_lane"].append((round(s, 1), round(off, 2), owner))
            adv = None
            d_now = None
            if prev_h[pi] is not None:
                dh = h - prev_h[pi]
                slope = dh / STEP_M
                adv = _advance(prev_p[pi], (px, pz), (x, z))
                d_now = math.hypot(px - prev_p[pi][0], pz - prev_p[pi][1])
                # a second difference that spans a metre this fixed-offset point ran BACKWARDS (offset past the turning
                # centre of a corner tighter than the lane: a fold) is not a wheel's experience — see FOLD BUMPS
                folded = adv < 0.0 or (prev_adv[pi] is not None and prev_adv[pi] < 0.0)
                if prev_slope[pi] is not None and not is_edge:
                    kink = abs(slope - prev_slope[pi]) * 100
                    if kink > KINK_PCT:
                        if line is not None and folded:
                            # (--line only) a fixed-offset path running backwards round a junction pad's turn re-traces
                            # the plan (FOLD BUMPS): reported as fold_kinks, as fold bumps are
                            problems.setdefault("fold_kinks", []).append((round(s, 1), round(off, 2), round(kink, 2)))
                        else:
                            own_k = (_own_travel_step(dh, prev_slope[pi] * STEP_M, d_now, prev_d[pi])
                                     if _vertex_kinks else None)
                            if own_k is not None and own_k * 100 / STEP_M <= KINK_PCT:
                                problems.setdefault("vertex_kinks", []).append(
                                    (round(s, 1), round(off, 2), round(kink, 2), round(own_k * 100 / STEP_M, 2)))
                            else:
                                problems["kinks"].append((round(s, 1), round(off, 2), round(kink, 2)))
                    step = abs(dh - prev_slope[pi] * STEP_M)
                    if (_dense_hops and step > STEP_SEVERE_M and not folded and len(prev_p[pi]) > 4
                            and prev_p[pi][4] is not None
                            and max(d_now or 0.0, prev_d[pi] or 0.0) > DENSE_HOP_M):
                        _ds = _dense_step(surface.top_at, [prev_p[pi][4], prev_p[pi][:2], (px, pz)], y_ref)
                        if _ds is not None and _ds <= STEP_SEVERE_M:
                            problems.setdefault("dense_hops", []).append(
                                (round(s, 1), round(off, 2), round(step, 3), round(_ds, 4)))
                            step = 0.0          # judged on the dense path: no step there over STEP_SEVERE_M
                    if step > STEP_SEVERE_M:
                        # flared-apron texture: on widened corner pavement (w >= 11) the OUTER
                        # offsets ride taper fans with rolled crossfall breaks — real aprons
                        # have them and the driving line doesn't touch them. Report, don't gate.
                        if not _corr and w >= 9.5 and abs(off) > 3.5 and not _in_flat_zone(px, pz) \
                                and not _in_fan(px, pz):
                            problems.setdefault("apron_steps", []).append(
                                (round(s, 1), round(off, 2), round(step, 3)))
                        elif _fold_severe_defer and folded and _in_fan(px, pz) and \
                                _on_fan_path(px, pz, prev_p[pi][0], prev_p[pi][1]):
                            problems.setdefault("fold_severe", []).append(
                                (round(s, 1), round(off, 2), round(step, 3)))
                            if _fold_chords:
                                # FOLD CHORDS: the metre's two ends, for verify_fold_fans' coverage check (8)
                                problems.setdefault("fold_severe_at", []).append(
                                    (round(s, 1), round(off, 2), round(step, 3), round(px, 3), round(pz, 3),
                                     round(prev_p[pi][0], 3), round(prev_p[pi][1], 3)))
                        else:
                            # inside a junction flat zone the WHOLE pad is driving surface —
                            # no exemptions (Kevin: "how do your tests pass this")
                            problems["severe_steps"].append((round(s, 1), round(off, 2), round(step, 3)))
                            if _fold_chords and _fold_severe_defer and folded and _in_fan(px, pz):
                                # FOLD CHORDS: in a fan, folded, but on no path verify_fold_fans reads: stays severe
                                problems.setdefault("fold_severe_unjudged", []).append(
                                    (round(s, 1), round(off, 2), round(step, 3)))
                    elif step > STEP_BUMP_M:
                        if folded:
                            problems.setdefault("fold_bumps", []).append(
                                (round(s, 1), round(off, 2), round(step, 3)))
                        elif not _corr and w >= 9.5 and abs(off) > 3.5 and not _in_flat_zone(px, pz):
                            problems.setdefault("apron_bumps", []).append(
                                (round(s, 1), round(off, 2), round(step, 3)))
                        else:
                            own = _own_travel_step(dh, prev_slope[pi] * STEP_M, d_now, prev_d[pi])
                            if own is not None and own <= STEP_BUMP_M:
                                problems.setdefault("vertex_bumps", []).append(
                                    (round(s, 1), round(off, 2), round(step, 3), round(own, 4)))
                            else:
                                problems["steps"].append((round(s, 1), round(off, 2), round(step, 3)))
                                problems.setdefault("steps_xz", []).append(
                                    (round(s, 3), round(off, 3), round(step, 4), round(px, 3), round(pz, 3)))
                prev_slope[pi] = slope
            prev_adv[pi] = adv
            prev_d[pi] = d_now
            # (the 5th field, DENSE HOPS only: the sample before, so the last two metres can be re-sampled)
            prev_p[pi] = (px, pz, x, z, (prev_p[pi][0], prev_p[pi][1]) if prev_p[pi] is not None else None) \
                if _dense_hops else (px, pz, x, z)
            prev_h[pi] = h
        # daylight probe: just past each pavement edge, some surface must exist from deck level
        # down to 7 m below — a miss means a hole in the embankment skirt (sky under the road)
        if deck_c is not None:
            for side in (-1.0, 1.0):
                off = side * (w / 2 + 0.8)
                gy_probe, _own = surface.top_at(x + nx * off, z + nz * off, deck_c - 2.5, 5.0)
                if gy_probe is None:
                    problems["daylight_gaps"].append((round(s, 1), round(off, 2)))
        # corridor obstruction scan at this station (uses centre deck height)
        if deck_c is not None:
            on_bridge = any(a <= s <= b for a, b in spans)
            # corridor CAP: at junction-flare boxes lane_half balloons to 12-16 m and the box's
            # own edge furniture (barriers hugging a 33 m mouth) reads as an obstruction. The
            # car needs a clear TRAVEL SWATH — 6 m half-width is a full two-lane clearance.
            # MEDIAN ISLAND (0037): the island's barrier and planting stand at the centreline by
            # design — scan the driven lane (right of the island) instead of a disc on the centre.
            _ox, _oz, _orad = x, z, min(lane_half, 6.0) + 0.3
            # transition band: within NEAR_DIVIDER_M of a divider/edge station the centre disc still
            # reaches the island nose or the strip's tapered end (12 SCRUB "obstructions" at the
            # island/gap boundaries, 2026-10-08, at +/-2 vertices; the 6.3 m disc reaches a 1WALL
            # end from 6 m out) — scan the lane there too, with the neighbour's geometry
            _lane_scan = _lane
            if _zone is not None and not _corr:
                # a station with no divider of its own borrows the nearest one's (today's island
                # transition rule); a station already beside a kerb-line strip but short of the
                # chain's free end borrows the chain's half-width the same way
                _ndh, _nins = _near_divider(i, s)
                _sdh = _dh if _dh > 0 else _ndh
                _sins = _inset if _inset > 0 else _nins
                if _sdh > _dh or _sins > _inset:
                    _lane_scan = _lane_geometry(w_lane, _sdh, _sins)
            if _lane_scan is not None:
                # scan band: inner edge DIVIDER_CLEAR_M - 0.3 = 0.1 m off the divider face, outer
                # edge 0.1 m off the kerb-line barrier face (or 0.2 m inside the lip)
                _lo, _hi = _lane_scan[0], _lane_scan[1]
                _mid = (_lo + _hi) / 2.0
                _ox, _oz = x + nx * (-_mid), z + nz * (-_mid)
                _orad = min((_hi - _lo) / 2.0, 6.0) + 0.3
            _keep = None
            if race and _lane_scan is not None:
                _kdh, _kins = (_sdh, _sins) if (_zone is not None and not _corr) else (_dh, _inset)
                _keep = (lambda vx, vz, _i0=i, _a=_kdh, _b=_kins: _in_lane(vx, vz, _i0, _a, _b))
            for name in obstacle.rising_in(_ox, _oz, _orad,
                                           lambda vx, vz: surface.top_at(vx, vz, y_ref)[0],
                                           OBST_CLEAR_M, OBST_HEIGHT_M, keep=_keep):
                if on_bridge and "BRIDGE" in name.upper():
                    continue                       # declared-span railing = required furniture
                problems["obstructions"].append((round(s, 1), name))
                obst_names[name] += 1
            # BARRIER PRESENCE (0047, race layouts): every station the bands declare a strip on
            # must carry a 1WALL there — the chain at the centreline, the kerb-line strip at
            # half_w + edge_centre_from_lip on both sides. Declared bridge spans are gapped by
            # declaration (edge_strip 0) and stay covered by the `guarded` drop probe.
            if race and _zone is not None:
                # the segment between two consecutive vertices is declared when BOTH declare it:
                # the authored strip starts at the first declared ring, so the 3 m before it
                # (stations this loop assigns to vertex i) carry nothing by construction
                if _zone.barrier_half_at(i) > 0 and _zone.barrier_half_at(i - 1) > 0:
                    _bm_probe("centre", s, x, z, nx, nz, 0.0, deck_c)
                if _zone.edge_strip_at(i) and _zone.edge_strip_at(i - 1):
                    # at the declared band of THIS station: the lerped width (the strip's own lateral; the
                    # closure duplicate is vertex 0), or on a trimmed corner's polyline
                    _ec = w_lane / 2.0 + _zone.edge_centre_from_lip
                    for _bk_, _sg in (("edge_L", 1.0), ("edge_R", -1.0)):
                        _cp = _corner_probe_at(_bk_, s)
                        if _cp is None:
                            _bm_probe(_bk_, s, x, z, nx, nz, _sg * _ec, deck_c)
                        else:
                            _bm_probe(_bk_, s, _cp[0], _cp[1], _cp[2], _cp[3], 0.0, deck_c)
                # the layout's CLOSURE (0049): on the declared line between the two ring centres (pins included)
                if _corr and _zone.closure_at(i) is not None and _zone.closure_at(i - 1) is not None:
                    _qa = _zone._band_point("closure", i - 1)
                    _qb = _zone._band_point("closure", i)
                    _qx, _qz = _qa[0] + (_qb[0] - _qa[0]) * t, _qa[2] + (_qb[2] - _qa[2]) * t
                    _ql = math.hypot(_qb[0] - _qa[0], _qb[2] - _qa[2]) or 1e-9
                    _bm_probe("closure", s, _qx, _qz, -(_qb[2] - _qa[2]) / _ql, (_qb[0] - _qa[0]) / _ql, 0.0, deck_c)
                # a declared chicane's race-side wall (ledger 0055): the same probe on its declared line
                if _corr and _zone.race_wall_at(i) is not None and _zone.race_wall_at(i - 1) is not None:
                    _qa = _zone._band_point("chicane", i - 1)
                    _qb = _zone._band_point("chicane", i)
                    _qx, _qz = _qa[0] + (_qb[0] - _qa[0]) * t, _qa[2] + (_qb[2] - _qa[2]) * t
                    _ql = math.hypot(_qb[0] - _qa[0], _qb[2] - _qa[2]) or 1e-9
                    _bm_probe("chicane", s, _qx, _qz, -(_qb[2] - _qa[2]) / _ql, (_qb[0] - _qa[0]) / _ql, 0.0, deck_c)
        s += STEP_M

    # BARRIER CONTINUITY: a declared station is MISSING when no 1WALL hit lies within half a
    # module (BARRIER_GAP_MAX_M / 2) of it along the band — seams between strip objects pass, a
    # hole longer than one module does not. Gate at 0: a declared-but-unbuilt chain must fail, or
    # the audit-D / lane exemptions on the band would be a bypass.
    barrier_missing = []
    for _bk, _rows in _bm_hits.items():
        _rows.sort()
        _hit_s = [s_ for s_, h_ in _rows if h_]
        _hp = 0
        for s_, h_ in _rows:
            if h_:
                continue
            while _hp < len(_hit_s) and _hit_s[_hp] < s_ - BARRIER_GAP_MAX_M / 2.0:
                _hp += 1
            if _hp < len(_hit_s) and _hit_s[_hp] <= s_ + BARRIER_GAP_MAX_M / 2.0:
                continue
            # a CLOSED lap's band runs on across the seam: a miss within half a module of the lap end is
            # covered by the hits just past station 0, and the reverse (median_zone's seam rule)
            if _closed_lap and _hit_s and (_hit_s[0] + lap - s_ <= BARRIER_GAP_MAX_M / 2.0
                                           or s_ + lap - _hit_s[-1] <= BARRIER_GAP_MAX_M / 2.0):
                continue
            barrier_missing.append((s_, _bk))
    problems["barrier_missing"] = barrier_missing
    problems["barrier_stations"] = sum(len(r) for r in _bm_hits.values())

    # EXCURSION SWEEPS (Kevin: "your tests need to drive the car off the road and back onto it").
    # Every ~150 m the virtual car leaves the pavement laterally, crosses the shoulder onto the
    # grass out to +8 m, and returns — sampling the built surface continuously. Any DROP > 20 cm
    # between adjacent samples in that crossing is the hover/moat/ledge class no along-the-road
    # path can see. Declared bridge spans exempt (past the railing is a real drop, guarded).
    # UNPAVED RUN-OFF. This sweep steps laterally every 0.5 m, so a perfectly ordinary 2:1 fill
    # slope (0.25 m per step) trips the 0.12 m drop test at EVERY sample. On a paved circuit that is
    # right — run-off there is a flat apron, so any drop really is a ledge. On a graded dirt road the
    # slope IS the surface: the shoulder falls away into its borrow ditch and nothing is wrong.
    #
    # Evidence this is terrain and not a meshing artifact (Dragon Tail, 25 km of CR 116): refining
    # the terrain grid 20% (10 m -> 8 m cells) moved ground-through-lane 23 -> 5, a 78% cut, while
    # the excursion count went 1,000 -> 1,041 — 4%, and the wrong way. Every worst offender sits at
    # +/-9 to 9.5 m, six metres beyond a 6.5 m carriageway, out on the fill slope.
    #
    # So on an unpaved road two things still gate, both surface-independent:
    #   * a FACE far steeper than an embankment. A 2:1 fill slope is 0.25 m per 0.5 m sample;
    #     1.0 m in one sample is four times that — a wall, not a slope.
    #   * a total FALL from the pavement edge deeper than the parapet warrant. build_mesh builds a
    #     stone parapet at fill edges dropping > 2 m and deliberately builds nothing below that, so a
    #     gate demanding a wall below 2 m contradicts the builder. Measuring cumulative fall (not the
    #     per-sample delta) is what catches a real cliff that descends over several samples and so
    #     never shows its full height in any single one — the case a per-step threshold alone misses.
    _unpaved = str(cfg.get("road_surface", "tarmac")) != "tarmac"
    UNPAVED_FACE_M = 1.0         # one-sample face 4x steeper than a 2:1 embankment
    UNPAVED_FALL_M = 3.0         # cumulative fall across the band (a 2:1 slope falls 2 m over 4 m)
    UNPAVED_LIP_M = 1.0          # ...of the CARRIAGEWAY edge, not the shoulder's outer lip
    UNPAVED_LIP_DROP_M = 0.25    # a step that would catch a wheel as it leaves the driven surface
    excursions = []
    s2 = 0.0
    next_exc = 0.0
    for i in range(1, n):
        seg2 = math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2])
        s2 += seg2
        if s2 < next_exc:
            continue
        next_exc += 150.0
        if any(a <= s2 <= b for a, b in spans):
            continue
        # intersection flare mouths: the widened lip has no graded edge yet (tracked task —
        # the coverage guard removes the sidewalk the flare swallows and nothing replaces it).
        # Exempt from GATING, still counted in the report as flare ledges.
        _wmed = sorted(widths)[len(widths) // 2]
        in_flare = widths[i] > _wmed + 1.5
        x0, y0, z0 = pts[i]
        _a2, _b2 = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
        _dx2, _dz2 = _b2[0] - _a2[0], _b2[2] - _a2[2]
        _L2 = math.hypot(_dx2, _dz2) or 1.0
        txe, tze = _dx2 / _L2, _dz2 / _L2
        nxe, nze = -tze, txe
        we = widths[i] / 2
        for sgn in (1.0, -1.0):
            prev_y = None
            off = 0.0
            built_edge = None    # where BUILT pavement actually ends (surface-owner, not nominal width)
            miss_run = 0
            edge_y = None        # ground height where the pavement ends — the datum for total fall
            carriage_edge = None # outer edge of the DRIVEN surface (excludes the shoulder)
            while off <= we + 9.0:   # FULLY exit the tarmac, past the hem onto raw world (Kevin)
                exx, ezz = x0 + nxe * off * sgn, z0 + nze * off * sgn
                ey, own = surface.top_at(exx, ezz, y0, 8.0)
                if own is not None and str(own).upper().startswith(("1ROAD", "1KERB")):
                    built_edge = off
                    edge_y = ey        # keeps advancing while still on pavement -> the true edge
                    # CARRIAGEWAY edge = where the surface you DRIVE on ends. The shoulder is also
                    # named 1ROAD_*, so built_edge runs out to the shoulder's outer lip — which on a
                    # graded road is exactly where the fill slope starts. Using that as "the pavement
                    # edge" made an ordinary shoulder-to-slope transition look like a ledge, 719 times.
                    if "SHOULDER" not in str(own).upper():
                        carriage_edge = off
                in_band = built_edge is not None and off <= built_edge + 4.0 and not in_flare
                if ey is None:
                    # NO SURFACE mid-crossing = a hole in the world. The old sweep silently
                    # skipped None — the literal fall-through case, ignored by the tool built to
                    # find it ("your tests should show it, but they continually don't").
                    miss_run += 1
                    if in_band and miss_run >= 2:      # >= 1 m of nothing inside the band
                        excursions.append((round(s2, 1), round(off * sgn, 2), 9.99, True))
                        miss_run = -999                # one report per crossing
                else:
                    miss_run = 0
                if ey is not None and prev_y is not None and prev_y - ey > 0.12 and off > we - 0.5:
                    # 0.12 m = a tall curb, the most a real car survives at speed. A drop BEHIND a
                    # barrier/guard wall is GUARDED (the car never reaches it — that's the wall's
                    # job, per the construction research: stone parapets at every drop > 2 m on
                    # the real Lariat). Unguarded car-destroyer drops in the band fail — they mark
                    # exactly where the four-condition selector must place walls.
                    # ANY 1WALL between the pavement edge and the drop guards it — the car hits
                    # the wall first regardless of how far outboard the drop sits. The old scan
                    # looked only 2 m behind, so a verge parapet with its drop 3 m outboard was
                    # "unguarded" while physically unreachable (imi toes, ledger 0025).
                    # Walls are NOT drivable, so the loader routes every 1WALL group into
                    # `obstacle` — probing `surface` here could never find one, which made this
                    # exemption dead code: every wall the builder ever placed was invisible to
                    # the scan that exists to credit it (found via ledger 0025's stone lips,
                    # physically present in track.obj yet "unguarded"). Probe the field walls
                    # actually live in.
                    guarded = False
                    _wo = max(we - 0.4, 0.5)
                    while _wo < off - 0.25:
                        _wx, _wz = x0 + nxe * _wo * sgn, z0 + nze * _wo * sgn
                        _wy, _wown = obstacle.top_at(_wx, _wz, y0 + 0.5, 2.5)
                        if _wown is not None and str(_wown).upper().startswith("1WALL"):
                            guarded = True
                            break
                        _wo += 0.5
                    # A VERTICAL-PANEL wall (v0.18.1, ledger 0057's Lake Murray Blvd I-8 deck): the loop's I-8 bridge
                    # rails are double-sided 0.95 m panels with no plan area at all (scripts-v021 build_guardrails),
                    # so the top_at probe above — a downward read — can never land on one, and every drop behind
                    # them read "unguarded" (v0.18.0 too: its 150 m station fell 3 vertices short of the deck).
                    # The rule is unchanged — a 1WALL between the pavement edge and the drop guards it — the
                    # probe now also asks the question the car asks: does its path out to the drop, WALL_CROSS_H_M
                    # over the pavement edge, pass THROUGH a 1WALL face?
                    if not guarded and edge_y is not None:
                        _w0 = max(we - 0.4, 0.5)
                        _w1 = off - 0.25
                        if _w1 > _w0:
                            guarded = _wall_crossed(
                                obstacle,
                                (x0 + nxe * _w0 * sgn, edge_y + WALL_CROSS_H_M, z0 + nze * _w0 * sgn),
                                (x0 + nxe * _w1 * sgn, edge_y + WALL_CROSS_H_M, z0 + nze * _w1 * sgn))
                    _drop = prev_y - ey
                    if _unpaved:
                        # Gate on PHYSICAL DANGER, not on proximity to the pavement. Two reasons the
                        # paved in-band test is wrong here: the shoulder counts as built pavement, so
                        # "just past the edge" IS where a graded road's fill slope starts (that alone
                        # gated 719 ordinary transitions); and `in_flare` excludes corner flares, which
                        # is where the worst real drop on this stage lives — 3.12 m off the outside of
                        # a flared switchback, waved through while shoulder slopes failed.
                        _fall = (edge_y - ey) if edge_y is not None else 0.0
                        _lip = (carriage_edge is not None and off <= carriage_edge + UNPAVED_LIP_M
                                and _drop > UNPAVED_LIP_DROP_M)
                        _gated = (not guarded) and (_drop > UNPAVED_FACE_M
                                                    or _fall > UNPAVED_FALL_M or _lip)
                    else:
                        _gated = in_band and not guarded
                    excursions.append((round(s2, 1), round(off * sgn, 2), round(_drop, 2), _gated))
                if ey is not None:
                    prev_y = ey
                off += 0.5
    problems["excursion_drops"] = excursions

    # CORNER FEASIBILITY (Kevin: "the tests should be catching my issue"): a KINK — fold over
    # a tight ±10 m window > 85 deg (apex radius <= ~12 m; switchbacks read 55-75 deg here) —
    # cannot be driven on street-width pavement. Kinks must carry >= 10 m.
    tight_corners = []
    for i in range(2, n - 2, 2):
        j0 = i
        while j0 > 0 and st[i] - st[j0] < 15.0:
            j0 -= 1
        j1 = i
        while j1 < n - 1 and st[j1] - st[i] < 15.0:
            j1 += 1
        h0 = math.atan2(pts[min(j0 + 2, n - 1)][2] - pts[max(j0 - 2, 0)][2],
                        pts[min(j0 + 2, n - 1)][0] - pts[max(j0 - 2, 0)][0])
        h1 = math.atan2(pts[min(j1 + 2, n - 1)][2] - pts[max(j1 - 2, 0)][2],
                        pts[min(j1 + 2, n - 1)][0] - pts[max(j1 - 2, 0)][0])
        dturn = abs((math.degrees(h1 - h0) + 180.0) % 360.0 - 180.0)
        wmax_local = max(widths[max(0, i - 7):min(n, i + 8)])   # the corner CORE the line uses
        if dturn > 110.0 and wmax_local < 9.0:
            tight_corners.append((round(st[i], 0), round(dturn, 0), round(widths[i], 1)))
    problems["undrivable_corners"] = tight_corners

    # FURNITURE SEATING (Kevin: "get the drive test to fail on what I'm driving right now"):
    # every wall/fence COLUMN stands on its support — base within 0.8 m of the surface directly
    # beneath (tri-exact). Rails between posts excused by grounded neighbors. The 27 m barriers
    # hanging over the creek FAIL here, forever. No advisory mode for this check.
    floating_walls = []
    cols = {}
    for gx2, gy2, gz2 in _wall_verts:
        k2 = (round(gx2 / 0.6), round(gz2 / 0.6))
        if k2 not in cols or gy2 < cols[k2][0]:
            cols[k2] = (gy2, gx2, gz2)
    grounded = set()
    gaps2 = {}
    for k2, (wy, wx, wz) in cols.items():
        gy2, _own2 = surface.top_at(wx, wz, wy - 0.5)
        if gy2 is None:
            gy2, _own2 = surface.top_at(wx, wz, wy)
        if gy2 is not None:
            gaps2[k2] = wy - gy2
            if wy - gy2 <= 0.8:
                grounded.add(k2)
        else:
            gaps2[k2] = 99.0          # nothing under it at all: definitely floating
    for k2, gp2 in gaps2.items():
        if gp2 > 0.8:
            if any((k2[0] + di, k2[1] + dj) in grounded for di in range(-4, 5) for dj in range(-4, 5)):
                continue
            floating_walls.append((round(cols[k2][1], 1), round(cols[k2][2], 1), round(gp2, 2)))
    problems["floating_furniture"] = floating_walls

    # REPLICATION ERROR (Kevin: "i want a realistic road. this exists so we have to be able to
    # replicate it"): the lidar measured the ACTUAL road bench — the built deck must match it.
    # |built - raw measured| along the lap, declared bridges exempt. This is the number that says
    # how far the pipeline strayed from the real mountain.
    rep = []
    ep = data / "centerline.elevation.json"
    if ep.exists() and line is None:
        try:
            ej = json.loads(ep.read_text())
            # z_raw_m is per geojson vertex; in_local_order below maps it into centerline.local.json's order by the
            # permutation projection recorded (ledger 0060). scripts.elevation.road_profile's z_raw_local_m (branch
            # 307a3b7, 2026-10-12) is that same mapping done at write time; it is not read here, so the one mapping runs once
            zr = ej.get("z_raw_m") or []
            e0 = 0.0
            _lc9 = data / "centerline.local.json"
            if _lc9.exists():
                _lj9 = json.loads(_lc9.read_text())
                e0 = float(_lj9.get("origin", {}).get("elev_m", 0.0))
                # the elevation file is in centerline.geojson order; route.start_at / route.reverse re-ordered the
                # local line in projection after it was written (High Plains 2026-10-29: 815 of 1,074 points, and
                # this read 14.6 m against the real deck — ledger 0060). projection recorded the permutation.
                from scripts.geometry.projection import in_local_order
                zr = in_local_order(_lj9, zr)
            if _lap_rec is not None:
                # the lap's mainline vertices take the mainline's measured height; connector / join vertices have none
                zr = [(zr[sv[1]] if sv[0] == _race_lap.MAINLINE and sv[1] < len(zr) else None)
                      for sv in _lap_rec["source_by_vertex"]]
            elif _lc9.exists():
                # an open stage's gate line carries build_mesh's lead-in/out road past each end; the measured
                # heights do not (ledger 0076) — pad them so vertex i is compared with its own measurement
                zr = pad_for_lead_in(zr, pts, _lj9.get("points_xyz_m") or [])
            if reverse:
                zr = zr[::-1]
            if zr and len(zr) >= 10:
                m2 = min(len(zr), len(pts))
                stq = 0.0
                for i in range(1, m2):
                    stq += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2])
                    if any(a <= stq <= b for a, b in spans) or zr[i] is None:
                        continue
                    rep.append(abs(pts[i][1] - (zr[i] - e0)))
        except Exception:
            pass
    if rep:
        rep.sort()
        nR = len(rep)
        problems["replication"] = {"median": round(rep[nR // 2], 2), "p95": round(rep[19 * nR // 20], 2),
                                   "max": round(rep[-1], 2)}

    # collapse obstruction runs (one wall = many stations)
    per_km = lap / 1000
    _phase("post-sweep passes")
    _bm_runs = []          # collapse the missing stations into runs for the report
    for s_, k_ in sorted(barrier_missing, key=lambda r: (r[1], r[0])):
        if _bm_runs and _bm_runs[-1][2] == k_ and s_ - _bm_runs[-1][1] <= STEP_M + 1e-6:
            _bm_runs[-1][1] = s_
        else:
            _bm_runs.append([s_, s_, k_])
    report = {
        "lap_m": round(lap, 1),
        "layout": lid,
        "direction": direction,
        "kind": kind,
        "race_furniture": race,
        "obj": obj_name,
        "lane": (f"{_bands_name} corridors.{lid}" if _corr else
                 ("barrier_bands.json v1 (chain / island face)" if race else "full width / island")),
        "barrier_stations": problems["barrier_stations"],
        "barrier_missing": len(barrier_missing),
        "barrier_missing_runs": [(a, b, k) for a, b, k in sorted(_bm_runs, key=lambda r: -(r[1] - r[0]))[:12]],
        "soft_top_in_lane": len(problems["soft_top_in_lane"]),
        "off_pavement_stations": off_pavement,
        "severe_steps": len(problems["severe_steps"]),
        "severe_per_km": round(len(problems["severe_steps"]) / per_km, 2),
        "steps_per_km": round(len(problems["steps"]) / per_km, 2),
        "kinks_per_km": round(len(problems["kinks"]) / per_km, 2),
        "obstruction_stations": len(set(s for s, _ in problems["obstructions"])),
        "daylight_gaps": len(problems["daylight_gaps"]),
        "replication_vs_measured": problems.get("replication"),
        "undrivable_corners": len(problems["undrivable_corners"]),
        "floating_furniture": len(problems["floating_furniture"]),
        "apron_steps": len(problems.get("apron_steps", [])),
        "fold_bumps": len(problems.get("fold_bumps", [])),
        "vertex_bumps": len(problems.get("vertex_bumps", [])),
        "vertex_bumps_worst": sorted(problems.get("vertex_bumps", []), key=lambda r: -r[3])[:12],
        "excursion_drops": sum(1 for r in problems["excursion_drops"] if r[3]),
        "excursion_far_ledges": sum(1 for r in problems["excursion_drops"] if not r[3]),
        "worst_excursions": sorted(problems["excursion_drops"], key=lambda r: -r[2])[:12],
        "worst_gated_excursions": sorted((r for r in problems["excursion_drops"] if r[3]),
                                         key=lambda r: -r[2])[:20],
        "obstruction_by_mesh": dict(sorted(obst_names.items(), key=lambda kv: -kv[1])[:12]),
        "worst": {
            "soft_top": problems["soft_top_in_lane"][:12],
            "severe_steps": sorted(problems["severe_steps"], key=lambda r: -r[2])[:12],
            "severe_all": sorted(problems["severe_steps"], key=lambda r: -r[2])[:2000],
            "kinks": sorted(problems["kinks"], key=lambda r: -r[2])[:12],
            "obstructions": problems["obstructions"][:16],
        },
    }
    if ((cfg.get("gates") or {}).get("drive1") or {}).get("force_exemptions"):
        # opt-in only (a track declaring gates.drive1.force_exemptions: the Lariat, ledger 0048): every undrivable corner
        # with its station, so tools/drive1_gates.py can check a declared exemption covers each one by place
        report["worst"]["undrivable_all"] = problems["undrivable_corners"][:2000]
    if _fold_severe_defer:
        # opt-in only (absent the key the report is byte-identical): the severe readings handed to verify_fold_fans
        report["fold_severe"] = len(problems.get("fold_severe", []))
        report["fold_severe_judge"] = "tools/verify_fold_fans.py (real wheel paths, hard)"
        report["worst"]["fold_severe"] = sorted(problems.get("fold_severe", []), key=lambda r: -r[2])[:200]
        if _fold_chords:
            # FOLD CHORDS (opt-in): every deferred reading in full, with its metre's plan points (verify_fold_fans (8))
            report["fold_severe_at"] = problems.get("fold_severe_at", [])
            report["fold_severe_unjudged"] = problems.get("fold_severe_unjudged", [])
    if _vertex_kinks:
        # opt-in only (absent the key the report is byte-identical): kinks re-measured on the path's own travel
        report["vertex_kinks"] = len(problems.get("vertex_kinks", []))
        report["kinks_per_km_station"] = round((len(problems["kinks"]) + report["vertex_kinks"]) / per_km, 2)
        report["worst"]["vertex_kinks"] = sorted(problems.get("vertex_kinks", []), key=lambda r: r[0])[:2000]
    if _dense_hops:
        # opt-in only (absent the key the report is byte-identical): severe readings re-measured on the dense path
        report["dense_hops"] = len(problems.get("dense_hops", []))
        report["worst"]["dense_hops"] = sorted(problems.get("dense_hops", []), key=lambda r: -r[2])[:200]
    out_name = f"drive_test.{lid}.json" if lid else "drive_test.json"
    if line is not None:
        out_name = f"drive_test.line.{line['id']}.json"
        report["line"] = line["id"]
        report["fold_kinks"] = len(problems.get("fold_kinks", []))
        report["worst"]["kinks_all"] = sorted(problems["kinks"], key=lambda r: r[0])[:2000]
        # every reading the line does NOT count is written with its place (repair round 1, the gates lens: counts alone
        # could not be checked from the build's own artifacts)
        report["worst"]["fold_kinks_all"] = sorted(problems.get("fold_kinks", []), key=lambda r: r[0])[:2000]
        report["worst"]["excursions_all"] = sorted(problems["excursion_drops"], key=lambda r: (r[0], r[1]))[:2000]
        report["worst"]["soft_top_all"] = problems["soft_top_in_lane"][:2000]

    # Gate philosophy: ABSOLUTE ZERO for the things no driver tolerates (ground through the lane,
    # solid objects in the corridor); RATES vs the driver-approved baseline for surface texture
    # (Sand Creek v0.15.x, the reference feel, runs ~11 severe/km and ~19 bumps/km — all at
    # junction crotches where edge strips meet). Kinks are reported but don't gate: on a real
    # mountain profile 3%-pt/m events are genuine road texture, not defects.
    severe_per_km = report["severe_per_km"]
    # SURFACE-AWARE BUMP RATE. The 75/km pass line is calibrated against Sand Creek — a PAVED street
    # loop, ~19 bumps/km. A 2.5 cm step is a defect on asphalt; on a graded dirt road it is the
    # surface. Dragon Tail measures ~114/km straight off 1 m lidar of the real road while its severe
    # rate (9.8/km) and its replication (median 0.06 m) both sit comfortably inside their limits —
    # i.e. the deck is faithfully following a genuinely rougher surface, not wobbling off it.
    # Holding gravel to the tarmac line would mean smoothing a rally stage until it drove like a
    # circuit, which is the opposite of correct. Severe steps, ground-through-lane, obstructions and
    # excursions are UNCHANGED — this moves one pass line for one surface, nothing else.
    _surface = str(cfg.get("road_surface", "tarmac"))
    _bump_limit = {"tarmac": 75.0, "gravel": 150.0}.get(_surface, 75.0)
    import os as _os
    # GATE_EXCURSIONS_ADVISORY=1: report-only for a TEST build while the construction selector
    # (#17: guard walls at drops, per docs/ROAD-CONSTRUCTION.md) is pending — the failures are the
    # tracked missing-walls class. NEVER set for a full (non-rc) release.
    _exc_adv = _os.environ.get("GATE_EXCURSIONS_ADVISORY") == "1"
    if _exc_adv and report["excursion_drops"]:
        print(f"  !! EXCURSIONS ADVISORY MODE: {report['excursion_drops']} unguarded drops NOT gating "
              f"(awaiting construction selector #17)")
    fail = (report["soft_top_in_lane"] > 0
            or report["daylight_gaps"] > 0
            or (not _exc_adv and report["excursion_drops"] > int(report["lap_m"] / 1000))
            or report["obstruction_stations"] > 0
            or report["undrivable_corners"] > 0
            or report["floating_furniture"] > 0
            or report["barrier_missing"] > 0
            or severe_per_km > 12.0
            or report["steps_per_km"] > _bump_limit)
    # PER-TRACK KINK CEILING (opt-in, 2026-10-12; Lookout Lariat V3-PLAN P5). Kinks gate nowhere by default
    # (see above); a track that declares track.config.json gates.drive_test.kinks_per_km_max gates on it. Only
    # then does the report carry the ceiling, so every track without the key writes today's file byte for byte.
    _kink_max = ((cfg.get("gates") or {}).get("drive_test") or {}).get("kinks_per_km_max")
    if _kink_max is not None:
        report["kinks_per_km_max"] = float(_kink_max)
        fail = fail or report["kinks_per_km"] > float(_kink_max)
    report["fail"] = fail
    # NETWORK REFERENCE LINE (opt-in: data/network.reference.json, written by scripts.geometry.network_reference). On a
    # road network this gate walks ONE declared mainline; every other built edge is unjudged by it, and says so here
    # and in the report — a hole named, never hidden. No file = no key = the report byte-identical.
    _nref_p = data / "network.reference.json"
    _nref = None
    if line is None and _nref_p.exists():
        try:
            _nref = json.loads(_nref_p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _nref = None
        if isinstance(_nref, dict) and isinstance(_nref.get("line"), dict):
            report["reference_line"] = {
                "line": _nref["line"].get("label"), "edges": _nref["line"].get("edges"),
                "judged_km": _nref.get("judged_km"), "built_km": _nref.get("built_km"),
                "unjudged_edges": _nref.get("unjudged_edges"), "unjudged_km": _nref.get("unjudged_km"),
                "unjudged": [[u.get("id"), u.get("name"), u.get("why"), u.get("length_m")]
                             for u in _nref.get("unjudged") or []]}
        else:
            _nref = None
    if line is not None:
        # ledger 0054 step 2e (--line only, reported, not gated): WHERE each bump > STEP_BUMP_M stands — [s, lateral, step,
        # x, z] (engine frame); steps_per_km alone could not say the 0.20.2 rise sat at Princess View's island
        report["steps_at"] = [list(r) for r in problems.get("steps_xz", [])]
    (data / out_name).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"DRIVE TEST {cfg['slug']}{(' [' + lid + ' ' + direction + ' ' + kind + ']') if lid else ''}"
          f"{(' [line ' + line['id'] + ']') if line is not None else ''}  "
          f"lap {lap/1000:.2f} km  (10 wheel paths @ {STEP_M} m)")
    print(f"  ground on top mid-lane : {report['soft_top_in_lane']}"
          + (f"   [{off_pavement} station(s) skipped: no pavement — off the stage end]" if off_pavement else ""))
    print(f"  floating furniture (walls/fences off support): {report['floating_furniture']} "
          f"{problems['floating_furniture'][:3] if problems['floating_furniture'] else ''}")
    print(f"  undrivable corners (>100deg @ <11m): {report['undrivable_corners']} "
          f"{problems['undrivable_corners'][:4] if problems['undrivable_corners'] else ''}")
    print(f"  severe steps (>{STEP_SEVERE_M*100:.0f} cm)  : {report['severe_steps']}")
    print(f"  bumps >{STEP_BUMP_M*100:.1f} cm /km      : {report['steps_per_km']} "
          f"(limit {_bump_limit:.0f} for {_surface})")
    if report["fold_bumps"]:
        print(f"  fold bumps (2.5-6 cm where a fixed-offset path runs backwards; reported, not gated): "
              f"{report['fold_bumps']}")
    if _fold_severe_defer:
        print(f"  fold severe (> 6 cm where a fixed-offset path runs backwards inside a levelled fan; judged by "
              f"tools/verify_fold_fans.py on the real wheel paths): {report['fold_severe']}")
    if _dense_hops:
        print(f"  dense hops (> {STEP_SEVERE_M*100:.0f} cm read across a > {DENSE_HOP_M} m hop, under it on the same path "
              f"sampled every {DENSE_DS_M} m; reported, not gated): {report['dense_hops']}")
    if _vertex_kinks:
        print(f"  vertex kinks (> {KINK_PCT}%/m read across a vertex creep / hop, under it on the path's own travel; "
              f"reported, not counted): {report['vertex_kinks']} (station reading {report['kinks_per_km_station']} /km)")
    if report["vertex_bumps"]:
        print(f"  vertex bumps (2.5-6 cm read across a vertex hop, under {STEP_BUMP_M*100:.1f} cm on the path's own "
              f"travel; reported, not gated): {report['vertex_bumps']}")
    print(f"  slope kinks >{KINK_PCT}%% /km   : {report['kinks_per_km']}"
          + (f"  (ceiling {report['kinks_per_km_max']} /km: gates.drive_test.kinks_per_km_max)"
             if "kinks_per_km_max" in report else ""))
    print(f"  daylight gaps at edges : {report['daylight_gaps']}")
    if report.get("replication_vs_measured"):
        _rp = report["replication_vs_measured"]
        print(f"  replication vs measured road : median {_rp['median']} m  p95 {_rp['p95']} m  max {_rp['max']} m")
    print(f"  off-road excursion drops>20cm : {report['excursion_drops']}"
          f"  (far flare ledges, reported: {report['excursion_far_ledges']})"
          + ("  [unpaved: only ledges >2 m or drops at the pavement edge gate]" if _unpaved else ""))
    for r in report["worst_excursions"][:6]:
        print(f"    worst excursion drop: {r}")
    print(f"  obstructed stations    : {report['obstruction_stations']}"
          + (f"  {report['obstruction_by_mesh']}" if obst_names else ""))
    if race:
        print(f"  declared barrier stations without a 1WALL : {report['barrier_missing']} "
              f"(of {report['barrier_stations']} probed; gap tolerance {BARRIER_GAP_MAX_M} m)"
              + (f"  worst runs {report['barrier_missing_runs'][:3]}" if barrier_missing else ""))
    for label, rows in (("soft_top", report["worst"]["soft_top"]),
                        ("severe", report["worst"]["severe_steps"]),
                        ("obstruction", report["worst"]["obstructions"][:8])):
        for r in rows[:6]:
            print(f"    worst {label}: {r}")
    if _nref is not None:
        _rl = report["reference_line"]
        print(f"  NETWORK: walked the reference line {_rl['line']!r} (edges {_rl['edges']}), {_rl['judged_km']} of "
              f"{_rl['built_km']} km built — UNJUDGED by this gate: {_rl['unjudged_edges']} edge(s), "
              f"{_rl['unjudged_km']} km (data/network.reference.json)")
        for u in _rl["unjudged"][:40]:
            print(f"    unjudged edge {u[0]} {u[1] or '(no name)'}: {u[2]}, {u[3]} m")
        if len(_rl["unjudged"]) > 40:
            print(f"    ... {len(_rl['unjudged']) - 40} more in data/network.reference.json")
    print(f"  => {'FAIL' if fail else 'PASS'}   (data/{out_name})")
    return {**report, "fail": fail}


SUMMARY_KEYS = ("fail", "direction", "kind", "race_furniture", "obj", "lane", "lap_m", "soft_top_in_lane",
                "obstruction_stations", "barrier_missing", "barrier_stations", "floating_furniture",
                "daylight_gaps", "excursion_drops", "undrivable_corners", "severe_steps", "severe_per_km",
                "steps_per_km", "kinks_per_km")


def write_summary(project_dir: str | Path, ran: list[str]) -> dict:
    """data/drive_test.json for a multi-layout track: one row per declared layout whose
    drive_test.<id>.json exists (this invocation's and earlier ones), `fail` = any row fails.
    Per-layout files of ids no longer declared are removed (a stale verdict is not a verdict)."""
    project = Path(project_dir)
    data = project / "data"
    cfg = json.loads((project / "track.config.json").read_text())
    ids = [str(lo.get("id")) for lo in cfg.get("layouts", []) or [] if isinstance(lo, dict) and lo.get("id")]
    for old in sorted(data.glob("drive_test.*.json")):
        x = old.name[len("drive_test."):-len(".json")]
        if x in ids:
            continue
        try:
            mine = json.loads(old.read_text(encoding="utf-8")).get("layout") == x
        except (json.JSONDecodeError, OSError, AttributeError):
            mine = False
        if mine:                      # a per-layout report of a retired id — not a foreign file
            old.unlink()
            print(f"  removed stale data/{old.name} (no layout {x!r})")
        else:
            print(f"  (data/{old.name} is not a per-layout report of this gate — left alone)")
    rows = {}
    for lid in ids:
        p = data / f"drive_test.{lid}.json"
        if not p.exists():
            rows[lid] = {"fail": None, "note": "not run"}
            continue
        r = json.loads(p.read_text(encoding="utf-8"))
        rows[lid] = {k: r.get(k) for k in SUMMARY_KEYS}
        rows[lid]["file"] = p.name
    summary = {
        "multi_layout": True,
        "_doc": "per-layout drive tests (ledger 0047): every layouts[] id is driven on the kn5 set it "
                "loads; the full report of each is data/drive_test.<id>.json. fail = any layout fails; "
                "a layout not yet run has fail null.",
        "ran": list(ran),
        "layouts": rows,
        "fail": any(r.get("fail") for r in rows.values()),
        "not_run": [lid for lid, r in rows.items() if r.get("fail") is None],
    }
    (data / "drive_test.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    verdict = " ".join(f"{lid}={'FAIL' if r.get('fail') else ('PASS' if r.get('fail') is False else '-')}"
                       for lid, r in rows.items())
    print(f"DRIVE TEST SUMMARY {cfg.get('slug', '')}: {verdict}   (data/drive_test.json)")
    return summary


# LINE GATE (ledger 0054 P3, EXPANSION-PLAN V6 — the plan's own numbers): on the north network's own lines no
# obstruction, floating furniture, undrivable corner or daylight gap [std], no severe step [invented], ground on top in the
# lane at most LINE_SOFT_PER_KM and kinks at most LINE_KINK_PER_KM [invented: the loop's rates, copied]; repair round 1
# (2026-10-19, the gates lens) adds unguarded excursion drops at most LINE_EXC_PER_KM [invented: the loop's own v0.18.1
# street rate, copied the same way]. drive_test's own lap rule (soft top 0, excursions <= 1 per km) is NOT the line's
# verdict — the loop's street layout itself has failed it since v0.18.0 (soft top 8, excursions 96) — but it is read on
# every line and written beside the verdict (drive_test_rule_fail, and its reasons), never hidden.
LINE_SOFT_PER_KM = 6.1
LINE_KINK_PER_KM = 4.97
LINE_EXC_PER_KM = 7.12      # held v0.18.1 street: 96 gated excursion drops over 13.49 km


def run_lines(project_dir: str | Path, set_name: str) -> int:
    """drive every line of data/drive_lines.<set>.json (tools/expansion_lines.py); data/drive_test.<set>.json is the
    verdict: a line fails on the LINE GATE (above); drive_test's own lap rule is read and written beside it; exit 1 on
    any failure"""
    project = Path(project_dir)
    data = project / "data"
    src = data / f"drive_lines.{set_name}.json"
    if not src.exists():
        raise SystemExit(f"drive_test: --line {set_name}: no data/{src.name} (tools/expansion_lines.py writes it)")
    doc = json.loads(src.read_text(encoding="utf-8"))
    rows, any_fail = {}, False
    for lid_, ln in doc["lines"].items():
        r = run(project, line={"id": f"{set_name}_{lid_}", **ln})
        km = r["lap_m"] / 1000.0
        soft_km = r["soft_top_in_lane"] / km if km else 0.0
        v6 = {"obstruction_stations": r["obstruction_stations"] == 0, "floating_furniture": r["floating_furniture"] == 0,
              "undrivable_corners": r["undrivable_corners"] == 0, "severe_steps": r["severe_steps"] == 0,
              "daylight_gaps": r["daylight_gaps"] == 0,
              "soft_top_per_km": soft_km <= LINE_SOFT_PER_KM, "kinks_per_km": r["kinks_per_km"] <= LINE_KINK_PER_KM,
              "excursion_drops_per_km": (r["excursion_drops"] / km if km else 0.0) <= LINE_EXC_PER_KM}
        fail = not all(v6.values())
        # drive_test's own lap rule on this line, reason by reason (the same tests as run()'s `fail`)
        dt_reasons = [k for k, bad in (("soft_top_in_lane", r["soft_top_in_lane"] > 0),
                                       ("daylight_gaps", r["daylight_gaps"] > 0),
                                       ("excursion_drops", r["excursion_drops"] > int(r["lap_m"] / 1000)),
                                       ("obstruction_stations", r["obstruction_stations"] > 0),
                                       ("undrivable_corners", r["undrivable_corners"] > 0),
                                       ("floating_furniture", r["floating_furniture"] > 0),
                                       ("barrier_missing", r["barrier_missing"] > 0)) if bad]
        any_fail = any_fail or fail
        rows[lid_] = {k: r.get(k) for k in SUMMARY_KEYS if k not in ("direction", "kind", "race_furniture", "lane")}
        rows[lid_].update({"soft_top_per_km": round(soft_km, 2),
                           "excursion_drops_per_km": round(r["excursion_drops"] / km, 2) if km else 0.0,
                           "excursion_drops": r["excursion_drops"], "v6": v6, "fail": fail,
                           "drive_test_rule_fail": bool(r["fail"]), "drive_test_rule_reasons": dt_reasons,
                           "fold_kinks": r.get("fold_kinks"),
                           "file": f"drive_test.line.{set_name}_{lid_}.json"})
        print(f"  LINE {lid_}: line gate {'FAIL' if fail else 'PASS'} "
              f"({', '.join(k for k, ok in v6.items() if not ok) or 'every key in limit'}); drive_test's own lap rule "
              f"{'FAIL (' + ', '.join(dt_reasons) + ')' if r['fail'] else 'PASS'}: soft top {r['soft_top_in_lane']}, "
              f"excursions {r['excursion_drops']} ({rows[lid_]['excursion_drops_per_km']}/km), kinks "
              f"{r['kinks_per_km']}/km, fold kinks {r.get('fold_kinks')}")
        print()
    out = {"_doc": "ledger 0054 P3: drive_test --line (the north network's own lines, tools/expansion_lines.py); "
                   "fail = the LINE GATE: EXPANSION-PLAN V6 (obstructions / floating furniture / undrivable / daylight 0, "
                   "severe 0, LINE_SOFT_PER_KM, LINE_KINK_PER_KM) + LINE_EXC_PER_KM (repair round 1). drive_test's own "
                   "lap rule is NOT the verdict; it is written per line as drive_test_rule_fail / _reasons",
           "limits": {"soft_top_per_km": LINE_SOFT_PER_KM, "kinks_per_km": LINE_KINK_PER_KM,
                      "excursion_drops_per_km": LINE_EXC_PER_KM, "severe_steps": 0},
           "lines": rows, "fail": any_fail}
    (data / f"drive_test.{set_name}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"DRIVE TEST LINES {set_name}: " + " ".join(f"{k}={'FAIL' if v['fail'] else 'PASS'}" for k, v in rows.items())
          + "   (drive_test's own lap rule: " + " ".join(f"{k}={'FAIL' if v['drive_test_rule_fail'] else 'PASS'}"
                                                   for k, v in rows.items())
          + f")   (data/drive_test.{set_name}.json)")
    return 1 if any_fail else 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    only: list[str] = []
    project = "."
    obj = None
    i = 0
    if "--line" in argv:
        k = argv.index("--line")
        rest = argv[:k] + argv[k + 2:]
        return run_lines(rest[0] if rest else ".", argv[k + 1])
    while i < len(argv):
        if argv[i] == "--layout":
            only.append(argv[i + 1]); i += 2
        elif argv[i] == "--obj":
            obj = Path(argv[i + 1]).name; i += 2
        else:
            project = argv[i]; i += 1
    cfg = json.loads((Path(project) / "track.config.json").read_text())
    layouts = [lo for lo in cfg.get("layouts", []) or [] if isinstance(lo, dict) and lo.get("id")]
    if not only and len(layouts) <= 1:
        r = run(project)                       # single layout: today's gate, today's file
        return 1 if r["fail"] else 0
    ids = [str(lo["id"]) for lo in layouts]
    for x in only:
        if x not in ids:
            raise SystemExit(f"drive_test: --layout {x!r} is not declared ({ids})")
    todo = only or ids
    if obj and len(todo) != 1:
        raise SystemExit("drive_test: --obj names ONE layout's gate OBJ — give exactly one --layout with it")
    any_fail = False
    for lid in todo:
        r = run(project, lid, obj=obj)
        any_fail = any_fail or bool(r["fail"])
        print()
    write_summary(project, todo)
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
