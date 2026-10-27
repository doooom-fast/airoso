"""W1-6 Large Arrow signs AT every tight corner — the placement rule, pure Python (no bpy).

Kevin, 2026-10-10: "we need arrow signs on TIGHT corners, where they actually go. You've been trying
to place them as warnings before a corner but they go AT the corner, just past the outside edge.
It's hard to describe but very easy to see when it's right or wrong."

The old engine rule (scripts/environment/build_env.py ~1070, never run on V3) stood a diamond
50-95 m UPSTREAM of the bend on the straight — an advance-warning device. This rule stands a MUTCD
W1-6 One-Direction Large Arrow where MUTCD 2C.10 puts it: on the outside of the turn, in line with
and at a right angle to approaching traffic — the spot a car that did not turn would arrive at.

THE RULE (all maths in the engine frame x = E, y = up, z = N of data/centerline.local.json):
  detector  every ribbon resampled to 1 m stations (mainline closed/modular, connectors evaluated
            in BOTH point orders because they are two-way); heading from the 4 m chord; signed
            curvature k over a 12 m window (+ = left/CCW); a corner is a run of |k| > 1/60 of one
            sign (gaps <= 10 m merged, apexes < 40 m apart merged); apex = max |k|; PC/PT = the
            R = 60 m crossings with 6-station hysteresis; D = integrated turn (D < 0 = right).
  qualifies R_apex <= 30 m AND |D| >= 45 deg AND the failed-to-turn ray leaves ALL pavement with
            5 <= s_C <= 80 m and its foot station in [PC, PT + 10 m] AND the apex is >= 15 m from
            every mouth cut / connector end (else mouth-flare geometry, skipped).
  ray       approach tangent t = unit(P[PC-2] - P[PC-12]) (the car's heading over the last 10 m
            before the hard turn); driver's right nR = (t_z, -t_x); launch A = P[PC] + nR *
            (island/2 + (w_app - island)/4) with w_app = min width over [PC-40, PC] (the UN-FLARED
            approach — never widths_m at the apex, which is the junction flare); Q(s) = A + t*s;
            C = first Q off every pavement ribbon (the outside curb face); S = keep marching the
            SAME ray until the perpendicular clearance to every ribbon edge >= d (1.63 m mainline,
            1.33 m connectors: curb face 0.08 + sidewalk 1.8/1.5 - 0.25 back-of-walk set-back),
            capped at +6 m past C (then step perpendicular instead, logged).
  outside   geometric assertion, never a side convention: cross(t_local(sC), C - P[sC]) > 0 for a
            right turn (left of travel), < 0 for a left turn. A failure aborts that corner, loudly.
  facing    plate normal f = -t exactly; arrow head toward +nR for D < 0 (W1-6R), -nR for D > 0.
  hairpin   |D| >= 135 AND arc >= 50 m -> a SECOND W1-6 from PC2 = the R = 20 m crossing, kept if
            the two bases are >= 12 m apart.
  mainline  the forward approach (increasing index = clockwise lap) always; the REVERSE approach too
            when signs.json defaults.both_directions_mainline is true (ledger 0051: a layout drives the
            lap anticlockwise, and the signs ship in the one road kn5 every layout loads). Connectors
            are always scanned in both approaches (two-way streets).
  mirror    a signs.json entry names the corner once, for its FORWARD approach: on a reversed scan its
            arrow / expect_arrow are mirrored (right <-> left; the same bend driven the other way turns
            the other way) and the record carries the mirrored value. A per-approach sub-object
            ("fwd": {...} / "rev": {...}) adds or replaces keys for that approach only and is never
            mirrored; on a corner scanned both ways a pin key (base_xz, face_bearing_deg,
            slide_along_curb_m) must sit inside one of them (SignsConfigError otherwise: one pin cannot
            serve two plates that face opposite approaches).
  slide     lamps (>= 3.0 m) and plants (>= 2.5 m) are cleared by sliding S along the local curb
            direction u (station sC), the smallest |slide| first, 0.25 m steps, capped at 1.0 m;
            beyond the cap the sign stays on the ray and the plant is excluded from TreeFX
            (lamps never move: a lamp inside 3.0 m is fatal). The slide is the ONLY lateral
            deviation from the ray; the plate stays square to it. The record carries u
            (curb_dir_xz) and slid_m so tools/author_signs_blend.py re-chooses the slide on the
            built mesh and tools/verify_signs.py tests the un-slid point against the ray.
  disc      drive_test's obstacle disc, min(lane_half, 6) + 0.3 m of a centreline, must clear every
            SIGN* vertex: the plate's footprint base +- 0.61 m along the right vector. drive_test
            sweeps the MAINLINE only (scripts/geometry/drive_test.py reads centerline.local.json),
            so the mainline disc is fatal for every post; a mainline post must also clear every
            connector's disc (hard). A CONNECTOR post is gated by the mainline disc alone — its own
            street's disc (4.9 m on a 10 m street) is logged as gate_margin_m and a negative margin
            is a WARN, never a march criterion: fleet/REALISM.md, a real sign stands at the back of
            the sidewalk, never marched into a front yard to satisfy a disc nothing gates.
  pair      a two-way connector corner whose -fwd and -rev points land < 2.0 m apart becomes ONE
            post at the mean base carrying both plates (W1-6R + W1-6L), each still facing its own
            approach (merge_pairs; re-run after the mesh march, which is where DCL-2's pair met).
  expect    signs.json expect_arrow names the arrow the corner must get; a computed arrow that
            differs is a skip with a logged reason, never a silent relocation (and a ship FAIL in
            tools/verify_signs.py check (j)).
  north     (ledger 0054 P4, EXPANSION-PLAN A8) the north network's tight corners are the turns made
            ACROSS the junction pads J2 / J3 / J4, which no single piece carries: each piece ends at its
            pad's cut, so its own scan only ever finds the mouth-flare stubs at its ends. The rule
            therefore also scans ONE stitched centre ribbon, "north" (tools/expansion_lines.centre_ribbon:
            the four pieces strung J1 -> J5 through the pads on the drive lines' own cubic), in both
            directions, with the BUILT pad decks (data/pads.built.json outlines, their stub arms included)
            as pavement in the field — the failed-to-turn ray crosses the deck and leaves pavement at the
            pad's far curb return or down a stub arm, behind its K-rail (A8: "where the outside of a turn
            is a stub, the plate stands behind the stub's wall"). For a ray that leaves through a pad the
            foot window grows by the stub arms' reach (pads.plan.json stub_length_m + tail_m, 16 m on
            Lake Murray): a foot 16 m down a stub is still the turn's own outside. The pieces' ends at
            the pads are not mouths for the stitched ribbon (the J1 / J5 cuts stay); for the pieces' own
            scans they still are. A north post is gated by the discs of the MAINLINE and of the two
            north DRIVE LINES (expansion_lines.compute_lines, the carriageways drive_test --line sweeps),
            the pieces' own centreline discs logged as a connector's are. Ids N-c<k>; signs.json names
            the three corners (ribbon "north", vertex = the stitched point index).
  through   (ledger 0054 P4) a failed-to-turn ray that runs THROUGH_ROAD_M (8 m) or more along ANOTHER
            road's pavement before it leaves pavement is a ray down a real road (Navajo westbound across
            the Waring opening at J1): the corner is skipped on that approach — in Free Roam the arrow
            would point away from a road a driver may take. A pad deck ("pad J2") and a declared stub
            (STUB_*, closed by its K-rail) are never a through road.
  layout    (ledger 0054 A7 / P4) a MAINLINE corner marked per_layout in signs.json is one whose
            shared plate the rule cannot place because straight on is now a real road (M3 at J1:
            College runs on into Waring; M4 at J5: Navajo on into Jackson north) — in Free Roam the
            arrow would point away from a road, and the road kn5 is loaded by every layout. The shared
            attempt still runs (Free Roam gets whichever plate its own geometry warrants, if any); then,
            for each RACE layout that drives the approach and got no shared plate, a LAYOUT PLATE is
            placed against that layout's own pavement: the field is the MAINLINE alone (every side
            street is sealed in a race layout) and the post stands behind the layout's sealing wall —
            data/barrier_bands.json params: the curb strip's centre edge_centre_from_lip_m inside the
            lip, its barrier_half_m, then the same lateral_offset_m the curb rule uses, so the wall's far
            face stands in for the curb face (1.48 m past the lip on Lake Murray). The mouth-flare rule
            does not apply (the mouth IS the sealed opening the plate stands on). Its id is
            <corner>-<dir>@<layout id>, it records "layout", and tools/author_signs_blend.py builds it
            into the RACE_CLOSE_<TOKEN> collection as SIGN*_<token>_<k>, so it ships in that layout's
            closure kn5 and no other layout ever sees it.

Overrides: tracks/<slug>/signs.json {defaults{...}, corners{<id>: {ribbon, vertex, skip, reason,
slide_along_curb_m, base_xz, face_bearing_deg, plate, arrow, expect_arrow, height_m, om1_3,
second_arrow, force, per_layout, fwd{...}, rev{...}}}} — arrow / expect_arrow name the FORWARD approach's arrow
(mirrored on a reversed scan); fwd / rev hold keys for one approach only (e.g. rev: {skip, reason}).
A skip with no non-empty reason (its own or the entry's) is refused at load.
An explicit --signs path that does not exist is an error, never "no overrides". defaults.kappa_window_m / hysteresis_stations drive the detector (12 m /
6 stations). An entry whose vertex has no detected corner within 30 m is refused with a WARN
(stale after a centreline regen). `plate` selects the geometry; only W1-6 exists (PLATE_GEOMETRY)
and any other value is a loud failure at load (never a silent W1-6). Every key in DEFAULTS is
read; a key signs.json carries that DEFAULTS does not know is refused the same way.

Ids: a corner a signs.json entry names carries that id; every other corner is <prefix>-c<k> in
forward station order. A reversed connector reuses the forward id only when a forward corner of
the same turn sense lies within MERGE_APEX_M of it (the same bend seen from the other side); a
corner only the reverse scan finds (the mouth stubs at a ribbon's ends) is <prefix>-r<k>, so no two
records of one (ribbon, direction) ever share an id, and the skipped list is deduplicated by
(ribbon, direction, apex station).

    PYTHONUTF8=1 python tools/place_signs.py <project-dir> [--signs PATH] [--no-connectors]

Writes data/signs.local.json (one record per sign + every skip with its reasons, analytic ground —
tools/author_signs_blend.py re-runs this in Blender, ray-casts the real ground and emits the
meshes) and data/signs_preview.svg (one 60 m top-down window per sign).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import expansion_lines as el  # noqa: E402  (the stitched north ribbon, the pad decks, the drive lines)

# --- detector ---------------------------------------------------------------------------------
STATION_M = 1.0
HEADING_HALF_CHORD = 2          # heading from the 4 m chord
KAPPA_HALF_WIN = 6              # signed curvature over a 12 m window
R_STRAIGHT_M = 60.0             # a corner is |k| > 1/60; PC/PT are the R = 60 crossings
HYSTERESIS = 6                  # consecutive straight stations that end a run
MERGE_GAP_M = 10
MERGE_APEX_M = 40
SEARCH_MAX = 250                # longest half-arc walked from an apex
# --- qualification -----------------------------------------------------------------------------
R_SIGN_MAX_M = 30.0
DEFL_MIN_DEG = 45.0
HAIRPIN_DEG = 135.0
HAIRPIN_ARC_M = 50.0
HAIRPIN_R_PC2 = 20.0
HAIRPIN_SPLIT_M = 12.0
MOUTH_CLEAR_M = 15.0
RAY_MIN_M, RAY_MAX_M = 5.0, 80.0
RAY_PAST_PT_M = 10
RAY_STEP = 0.25
RAY_EXTRA_CAP_M = 6.0
T_END_PROBE_M = 3.0
# --- the furniture (MUTCD 11th Ed. Table 2C-1 / 2A.15 / 2A.16; San Diego SDM-104 post) ----------
CURB_FACE_W = 0.08              # assembler ribbon.curb_sidewalk (build_loop_blend.py:658/677)
SIDEWALK_W = {"MAINLINE": 1.8, "CONNECTOR": 1.5}
BACK_OF_WALK_SETBACK = 0.25
WALK_ABOVE_ROAD = 0.10 + 0.14   # lift + curb_h: the walk top relative to the road centreline height
HEIGHT_M = 2.13                 # 7 ft bottom-of-plate over a sidewalk (2A.15 pedestrian areas)
PLATE_W, PLATE_H = 1.219, 0.610  # W1-6 48 x 24 in
PLATE_BORDER_INSET, PLATE_BORDER_W, PLATE_CORNER_R = 0.0127, 0.01905, 0.0476   # 0.5 / 0.75 / 1.875 in
OM13_SIDE = 0.457               # 18 in diamond, Type N-1(CA)
OM13_GAP = 0.05
POST_W = 0.05                   # 2 in square tube
POST_SINK = 0.30                # the prep's conform pass never re-seats SIGNPOST; sink the base
POST_OVER_TOP = 0.05
PLATE_FRONT_OFF = POST_W / 2 + 0.005   # plate face proud of the post face
PLATE_BACK_GAP = 0.003          # own verts, > the prep's 1e-4 weld
BORDER_PROUD, ARROW_PROUD = 0.002, 0.004
# W1-6R arrow, inches on the 48 x 24 plate, origin bottom-left, y up (FHWA SHS 2004 sheet 2-7 /
# the PD Commons master). Vertex 0 is the tip — the fan triangulation hangs off it.
ARROW_IN = [(43.5, 12.0), (29.4, 21.0), (30.0, 15.33), (4.5, 15.33), (4.5, 8.67), (30.0, 8.67), (29.4, 3.0)]
# --- clearances / gates -------------------------------------------------------------------------
LAMP_CLEAR_M = 3.0
PLANT_CLEAR_M = 2.5
LAMP_ARM_M = 1.8                # lights.local.json stores the HEAD; the post is 1.8 m away from the road
SLIDE_MAX_M, SLIDE_STEP_M = 1.0, 0.25   # along the curb only; beyond the cap the plant is excluded instead
HALF_PLATE = PLATE_W / 2        # the disc footprint: every SIGN* vertex lies within +-0.61 m of the base
PAIR_MERGE_M = 2.0              # -fwd/-rev points of one two-way corner closer than this share ONE post
SIGN_SPACING_M = 2.0            # verify (i): no two posts closer than this
PAIR_STACK_GAP = 0.05           # a paired plate whose facing is < 90 deg from the first stacks above it
SPAWN_CLEAR_M = 200.0           # WARN only: AC_TIME_1 sits 30 m from M1, which the plan places
GROUND_WARN_M = 0.30
OVERRIDE_STALE_M = 30.0
# --- ledger 0054 P4: the north ribbon and the per-layout plates --------------------------------------
NORTH_RIBBON = el.NORTH_RIBBON      # "north": the stitched centre ribbon through the pads (expansion_lines.centre_ribbon)
LINE_PREFIX = "expansion_"          # the north drive lines in the field: disc-only ribbons expansion_fwd / expansion_rev
PAD_PREFIX = "pad "                 # a pad deck in the field: "pad J2" (its outline polygon, stub arms included)
LAYOUT_SEP = "@"                    # a layout plate's id: <corner>-<dir>@<layout id>
WALL_CLEAR_M = 0.5                  # the mesh stage: a post stands at least this far from every 1WALL* face (the lamp
#                                     rule's number, tools/author_lamps_blend.py WALL_CLEAR_M)
THROUGH_ROAD_M = 8.0                # [invented] the failed-to-turn ray running this far along ANOTHER road's pavement
#                                     before it leaves pavement means straight on IS a road (M3-rev: Navajo westbound
#                                     runs across the Waring opening): no shared plate — the arrow would point away
#                                     from a real road in Free Roam. A pad deck and a declared stub (STUB_*) are the
#                                     corner itself / a closed arm, never a through road.
STUB_PREFIX = "STUB_"
SIDE_STEP_MAX_M = 2.5               # [invented] the mesh stage's fallback for a grazing exit (the ray leaves the pavement
#                                     at so flat an angle that no point on it within the cap is clear of the curb): the
#                                     post steps square off the ray, to the outside, at most this far
# --- the old rule, for the comparison picture ---------------------------------------------------
OLD_REV1_LEAD_M = 52.0          # kerbs lead 28 m + 8 stations ~ 24 m before the first curved vertex
OLD_REV1_LATERAL = 2.2
OLD_REV2_LATERAL = 2.8

DEFAULTS = {
    "r_sign_max_m": R_SIGN_MAX_M, "defl_min_deg": DEFL_MIN_DEG, "hairpin_deg": HAIRPIN_DEG,
    "lateral_offset_m": CURB_FACE_W + SIDEWALK_W["MAINLINE"] - BACK_OF_WALK_SETBACK,
    "lateral_offset_connector_m": CURB_FACE_W + SIDEWALK_W["CONNECTOR"] - BACK_OF_WALK_SETBACK,
    "height_m": HEIGHT_M, "om1_3": True, "include_connectors": True,
    "both_directions_mainline": False, "lamp_clear_m": LAMP_CLEAR_M, "plant_clear_m": PLANT_CLEAR_M,
    "kappa_window_m": 2 * KAPPA_HALF_WIN, "hysteresis_stations": HYSTERESIS,
}
PLATE_GEOMETRY = ("W1-6",)      # the plates sign_polygons can build; W1-7 / W1-8 are second-pass devices
CORNER_KEYS = ("ribbon", "vertex", "skip", "reason", "slide_along_curb_m", "base_xz", "face_bearing_deg",
               "plate", "arrow", "expect_arrow", "height_m", "om1_3", "second_arrow", "force",
               "per_layout",                 # a MAINLINE corner whose unplaceable shared plate becomes race-layout plates (P4)
               "where", "ship", "note",      # where/ship/note are prose for the pictures and for Kevin
               "fwd", "rev")                 # per-approach sub-objects (ledger 0051), see the module doc
DIRECTION_KEYS = ("fwd", "rev")
PIN_KEYS = ("base_xz", "face_bearing_deg", "slide_along_curb_m")   # one approach only (ledger 0051)
GATED_RIBBONS = ("MAINLINE",)   # the centrelines drive_test sweeps: its disc is the only one a gate enforces (+ the
#                                 north drive lines expansion_fwd / expansion_rev when the track has them: Context.gated)
RIBBON_PREFIX = {"MAINLINE": "M", "del_cerro_blvd#0": "DC0", "del_cerro_blvd#1": "DC1",
                 "del_cerro_blvd_loop": "DCL", "medium#2+0#0#0": "MED", NORTH_RIBBON: "N"}


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def unit(v):
    L = math.hypot(v[0], v[1]) or 1e-12
    return (v[0] / L, v[1] / L)


def bearing(vx, vz):
    """compass bearing (0 = N, 90 = E) of an engine-frame (x = E, z = N) direction"""
    return (90.0 - math.degrees(math.atan2(vz, vx))) % 360.0


class Ribbon:
    """one road centreline resampled to 1 m stations: (x, z, y, w, vfrac)"""

    def __init__(self, name, pts3, widths, closed, reverse=False, kappa_half=KAPPA_HALF_WIN):
        self.name = name
        self.closed = closed
        self.reverse = reverse
        self.kappa_half = max(1, int(kappa_half))   # signs.json defaults.kappa_window_m / 2
        P = [tuple(p) for p in pts3]
        W = list(widths)
        if closed and math.dist(P[0][::2], P[-1][::2]) < 1e-6:   # L13: drop the repeated seam vertex
            P, W = P[:-1], W[:-1]
        if reverse:
            P, W = P[::-1], W[::-1]
        self.raw, self.raw_w = P, W
        idx = list(range(len(P))) + ([0] if closed else [])
        cum = [0.0]
        for a, b in zip(idx[:-1], idx[1:]):
            cum.append(cum[-1] + math.hypot(P[b][0] - P[a][0], P[b][2] - P[a][2]))
        self.cum, self.L = cum, cum[-1]
        self.n = int(self.L) if closed else int(self.L) + 1
        self.S = [self._interp(s) for s in range(self.n)]
        self.cells = {}
        for i in range(self.n if closed else self.n - 1):
            x, z = self.S[i][0], self.S[i][1]
            self.cells.setdefault((int(x // 30), int(z // 30)), []).append(i)

    def _interp(self, s):
        P, cum = self.raw, self.cum
        m = len(P)
        s = s % self.L if self.closed else min(max(s, 0.0), self.L)
        lo, hi = 0, len(cum) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if cum[mid] <= s:
                lo = mid
            else:
                hi = mid
        a, b = P[lo % m], P[(lo + 1) % m]
        t = (s - cum[lo]) / max(1e-9, cum[lo + 1] - cum[lo])
        w = self.raw_w[lo % m] * (1 - t) + self.raw_w[(lo + 1) % m] * t
        return (a[0] + (b[0] - a[0]) * t, a[2] + (b[2] - a[2]) * t, a[1] + (b[1] - a[1]) * t, w, lo + t)

    def st(self, i):
        return i % self.n if self.closed else min(max(i, 0), self.n - 1)

    def xz(self, i):
        s = self.S[self.st(i)]
        return (s[0], s[1])

    def y(self, i):
        return self.S[self.st(i)][2]

    def w(self, i):
        return self.S[self.st(i)][3]

    def vertex(self, i):
        """raw vertex index (forward point order) nearest the station"""
        v = int(round(self.S[self.st(i)][4])) % len(self.raw)
        return (len(self.raw) - 1 - v) if self.reverse else v

    def heading(self, i):
        a, b = self.xz(i - HEADING_HALF_CHORD), self.xz(i + HEADING_HALF_CHORD)
        return math.atan2(b[1] - a[1], b[0] - a[0])

    def tangent(self, i):
        h = self.heading(i)
        return (math.cos(h), math.sin(h))

    def kappa(self, i):
        kh = self.kappa_half
        return wrap(self.heading(i + kh) - self.heading(i - kh)) / (2 * kh)

    def copy(self, reverse):
        return Ribbon(self.name, self.raw if not self.reverse else self.raw[::-1],
                      self.raw_w if not self.reverse else self.raw_w[::-1], self.closed,
                      reverse=reverse, kappa_half=self.kappa_half)

    def dist_stations(self, a, b):
        d = abs(b - a)
        return min(d, self.n - d) if self.closed else d

    def nearest(self, q, lo=None, hi=None):
        """(distance, fractional station) to the polyline; whole ribbon via the hash, or a window"""
        best = (float("inf"), 0.0)
        if lo is None:
            cx, cz = int(q[0] // 30), int(q[1] // 30)
            cand = [i for dx in (-1, 0, 1) for dz in (-1, 0, 1) for i in self.cells.get((cx + dx, cz + dz), ())]
        else:
            cand = range(lo, hi + 1)
        for i in cand:
            a, b = self.xz(i), self.xz(i + 1)
            if not self.closed and self.st(i + 1) == self.st(i):
                continue
            dx, dz = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dz * dz
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dz) / L2))
            d = math.hypot(q[0] - (a[0] + t * dx), q[1] - (a[1] + t * dz))
            if d < best[0]:
                best = (d, i + t)
        return best

    def label(self):
        return self.name + ("(rev)" if self.reverse else "")


def point_in_polygon(x, z, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        ax, az = poly[i][0], poly[i][1]
        bx, bz = poly[(i + 1) % n][0], poly[(i + 1) % n][1]
        if (az > z) != (bz > z):
            if ax + (z - az) * (bx - ax) / (bz - az) > x:
                inside = not inside
    return inside


def polygon_edge_dist(x, z, poly):
    n = len(poly)
    best = float("inf")
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / L2))
        best = min(best, math.hypot(x - (a[0] + t * dx), z - (a[1] + t * dz)))
    return best


class PavementField:
    """signed distance to the nearest pavement edge over every ribbon (negative = on pavement) — plus, since ledger
    0054 P4, pavement POLYGONS (the junction pads' built decks: add_polygon) and DISC-ONLY lines (the north drive
    lines: add_line — never pavement, only drive_test's obstacle disc, so gate_margin reads them and query never does)"""

    def __init__(self, ribbons, cell=60.0):
        self.cell = cell
        self.segs = []
        self.cells = {}
        self.polys = []          # (name, [(x, z)...], (minx, minz, maxx, maxz))
        for rb in ribbons:
            if rb.reverse:
                continue
            self._add_segs(rb.name, rb.raw, rb.raw_w, rb.closed, False)

    def _add_segs(self, name, P, W, closed, disc_only):
        idx = list(range(len(P))) + ([0] if closed else [])
        for a, b in zip(idx[:-1], idx[1:]):
            k = len(self.segs)
            self.segs.append((name, P[a], P[b], W[a] / 2, W[b] / 2, disc_only))
            for (x, _, z) in (P[a], P[b]):
                self.cells.setdefault((int(x // self.cell), int(z // self.cell)), set()).add(k)

    def add_line(self, name, P, W):
        """a disc-only ribbon (a swept drive line): gated, never pavement"""
        self._add_segs(name, [tuple(p) for p in P], list(W), False, True)

    def add_polygon(self, name, poly):
        """a pavement polygon (a pad deck's built outline, xz): on it = negative distance to its edge"""
        xs, zs = [p[0] for p in poly], [p[1] for p in poly]
        self.polys.append((name, [tuple(p) for p in poly], (min(xs), min(zs), max(xs), max(zs))))

    def query(self, x, z, exclude=None, only=None):
        """(signed edge distance, ribbon, half-width, road y) of the nearest PAVEMENT (segments + polygons; a disc-only
        line never counts); exclude = one ribbon left out, only = these ribbon names alone (a race layout's pavement is
        the MAINLINE alone — every side street is sealed)"""
        best = (float("inf"), None, 0.0, 0.0)
        cx, cz = int(x // self.cell), int(z // self.cell)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for k in self.cells.get((cx + dx, cz + dz), ()):
                    name, a, b, ha, hb, disc_only = self.segs[k]
                    if disc_only or name == exclude or (only is not None and name not in only):
                        continue
                    ddx, ddz = b[0] - a[0], b[2] - a[2]
                    L2 = ddx * ddx + ddz * ddz
                    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - a[0]) * ddx + (z - a[2]) * ddz) / L2))
                    d = math.hypot(x - (a[0] + t * ddx), z - (a[2] + t * ddz))
                    hw = ha * (1 - t) + hb * t
                    if d - hw < best[0]:
                        best = (d - hw, name, hw, a[1] + (b[1] - a[1]) * t)
        if only is None:
            for name, poly, (x0, z0, x1, z1) in self.polys:
                if name == exclude or x < x0 - best[0] or x > x1 + best[0] or z < z0 - best[0] or z > z1 + best[0]:
                    continue
                d = polygon_edge_dist(x, z, poly)
                sd = -d if point_in_polygon(x, z, poly) else d
                if sd < best[0]:
                    best = (sd, name, 0.0, best[3])
        return best

    def gate_margin(self, x, z, names=None):
        """distance beyond drive_test's obstacle disc min(max(w/2-0.4,0.8),6)+0.3 of EVERY ribbon
        (names=None) or of the named ribbons only (Context.gated: the ones drive_test sweeps — the
        MAINLINE and the north drive lines)"""
        worst = float("inf")
        cx, cz = int(x // self.cell), int(z // self.cell)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for k in self.cells.get((cx + dx, cz + dz), ()):
                    name, a, b, ha, hb, _disc_only = self.segs[k]
                    if names is not None and name not in names:
                        continue
                    ddx, ddz = b[0] - a[0], b[2] - a[2]
                    L2 = ddx * ddx + ddz * ddz
                    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - a[0]) * ddx + (z - a[2]) * ddz) / L2))
                    d = math.hypot(x - (a[0] + t * ddx), z - (a[2] + t * ddz))
                    w = 2 * (ha * (1 - t) + hb * t)
                    worst = min(worst, d - (min(max(w / 2 - 0.4, 0.8), 6.0) + 0.3))
        return worst

    def footprint_margin(self, base, rights, names=None):
        """gate_margin over the sign's footprint: the base and both plate ends (+-HALF_PLATE along
        every plate's right vector) — no SIGN* vertex may stand inside drive_test's disc"""
        pts = [tuple(base)]
        for r in rights:
            pts.append((base[0] + r[0] * HALF_PLATE, base[1] + r[1] * HALF_PLATE))
            pts.append((base[0] - r[0] * HALF_PLATE, base[1] - r[1] * HALF_PLATE))
        return min(self.gate_margin(p[0], p[1], names) for p in pts)


def disc_names_for(ribbon_name, gated=GATED_RIBBONS):
    """the ribbons whose disc is a HARD requirement for a post on `ribbon_name`: every ribbon for a
    mainline post (it must not stand in a side street's corridor either), the gated ribbons only
    for a connector / north post (its own street's disc is logged + WARN, see the module doc).
    gated = Context.gated: the MAINLINE plus the north drive lines when the track has them."""
    return None if ribbon_name == "MAINLINE" else tuple(gated)


def gate_label(names):
    return "all" if names is None else "+".join(names)


# ----------------------------------------------------------------------------------------------
def detect_corners(rb, hyst=HYSTERESIS):
    """runs of |k| > 1/R_STRAIGHT of one sign -> [{apex, sign, R_apex, PC, PT, arc, D_deg}]"""
    thr = 1.0 / R_STRAIGHT_M
    n = rb.n
    k = [rb.kappa(i) for i in range(n)]
    if rb.closed:   # start the modular scan on a straight station so the seam never splits a run
        s0 = next((i for i in range(n) if abs(k[i]) <= thr), 0)
        order = [(s0 + i) % n for i in range(n)]
    else:
        order = list(range(n))
    runs = []
    cur = None
    for i in order:
        sg = 1 if k[i] > thr else (-1 if k[i] < -thr else 0)
        if sg and cur and cur[2] == sg and rb.dist_stations(cur[1], i) <= 1:
            cur[1] = i
        elif sg:
            if cur:
                runs.append(cur)
            cur = [i, i, sg]
        else:
            if cur:
                runs.append(cur)
            cur = None
    if cur:
        runs.append(cur)

    def apex_of(run):
        a, b, sg = run
        length = (b - a) % n if rb.closed else b - a
        return max(((a + j) % n if rb.closed else a + j for j in range(length + 1)), key=lambda i: abs(k[i]))

    merged = []
    for run in runs:
        if merged and merged[-1][2] == run[2]:
            gap = rb.dist_stations(merged[-1][1], run[0])
            if gap <= MERGE_GAP_M or rb.dist_stations(apex_of(merged[-1]), apex_of(run)) < MERGE_APEX_M:
                merged[-1][1] = run[1]
                continue
        merged.append(list(run))
    out = []
    for run in merged:
        apex = apex_of(run)
        sg = run[2]
        pc = walk_to_straight(rb, apex, -1, thr, hyst)
        pt = walk_to_straight(rb, apex, +1, thr, hyst)
        arc = (pt - pc) % n if rb.closed else pt - pc
        D = math.degrees(sum(k[(pc + j) % n if rb.closed else min(pc + j, n - 1)] for j in range(arc + 1)))
        out.append({"apex": apex, "sign": sg, "R_apex_m": 1.0 / max(abs(k[apex]), 1e-9),
                    "PC": pc, "PT": pt, "arc_m": arc, "D_deg": D})
    return out


def walk_to_straight(rb, apex, step, thr, hyst=HYSTERESIS):
    """walk from the apex until `hyst` consecutive stations have |k| < thr (the station just
    before that straight stretch is the PC (step -1) / PT (step +1)) — or until the curvature
    changes sign: an S-bend's two halves are two corners, never one arc (Wisconsin v10/v16)"""
    sg = 1 if rb.kappa(apex) > 0 else -1
    hyst = max(1, int(hyst))
    s, n_ok, walked = apex, 0, 0
    while walked < SEARCH_MAX:
        nxt = s + step
        if not rb.closed and (nxt < 0 or nxt >= rb.n):
            return s
        nxt = nxt % rb.n if rb.closed else nxt
        k = rb.kappa(nxt)
        if abs(k) >= thr and (k > 0) != (sg > 0):
            return s
        s = nxt
        walked += 1
        n_ok = n_ok + 1 if abs(k) < thr else 0
        if n_ok >= hyst:
            return (s - step * (hyst - 1)) % rb.n if rb.closed else s - step * (hyst - 1)
    return s


def pca_heading(rb, pc, back=8, fwd=4):
    win = [rb.xz(pc - j) for j in range(back, -fwd - 1, -1)]
    mx = sum(p[0] for p in win) / len(win)
    mz = sum(p[1] for p in win) / len(win)
    sxx = sum((p[0] - mx) ** 2 for p in win)
    szz = sum((p[1] - mz) ** 2 for p in win)
    sxz = sum((p[0] - mx) * (p[1] - mz) for p in win)
    th = 0.5 * math.atan2(2 * sxz, sxx - szz)
    if math.cos(th) * (win[-1][0] - win[0][0]) + math.sin(th) * (win[-1][1] - win[0][1]) < 0:
        th += math.pi
    return th


# ----------------------------------------------------------------------------------------------
class Context:
    def __init__(self, proj, cfg):
        self.proj = Path(proj)
        data = self.proj / "data"
        self.cfg = cfg
        # the two detector knobs signs.json may tune (defaults.kappa_window_m / hysteresis_stations)
        self.kappa_half = max(1, int(round(float(cfg.get("kappa_window_m", 2 * KAPPA_HALF_WIN)) / 2)))
        self.hyst = max(1, int(cfg.get("hysteresis_stations", HYSTERESIS)))
        cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
        self.origin = cl.get("origin")
        self.mainline = Ribbon("MAINLINE", cl["points_xyz_m"], cl["widths_m"], True, kappa_half=self.kappa_half)
        self.ribbons = [self.mainline]
        cp = data / "connectors.local.json"
        self.connectors = json.loads(cp.read_text(encoding="utf-8")).get("connectors", []) if cp.exists() else []
        for c in self.connectors:
            P = c["points_xyz_m"]
            closed = math.dist(P[0][::2], P[-1][::2]) < 1e-6
            self.ribbons.append(Ribbon(c["name"], P, c["widths_m"], closed, kappa_half=self.kappa_half))
        self.field = PavementField(self.ribbons)
        mb = data / "median_bands.json"
        isl = json.loads(mb.read_text(encoding="utf-8")).get("island_w_by_vertex", []) if mb.exists() else []
        self.island = {int(k): v for k, v in isl.items()} if isinstance(isl, dict) else {i: v for i, v in enumerate(isl) if v}
        self.island_by_ribbon = {"MAINLINE": self.island}
        # --- ledger 0054 P4: the north network ------------------------------------------------------------
        # the stitched centre ribbon "north" (the J2 / J3 / J4 turns), the BUILT pad decks as pavement, the two drive
        # lines as gated discs. The ribbon is scanned like a connector but NOT added to the field (its pieces are
        # already there); without built pads the stitched turns would be judged on a deck the field cannot see,
        # so the ribbon is left out and said so (self.north_note).
        self.north = None
        self.north_note = None
        self.gated = tuple(GATED_RIBBONS)
        self.stub_reach_m = 0.0
        nr = el.centre_ribbon(self.proj)
        pads = el.pad_polygons(self.proj) if nr else []
        if nr and not pads:
            self.north_note = "north route declared but no data/pads.built.json: the stitched north ribbon is not scanned"
        elif nr:
            self.north = Ribbon(nr["name"], nr["points_xyz_m"], nr["widths_m"], False, kappa_half=self.kappa_half)
            self.north_pieces = list(nr["pieces"])
            self.ribbons.append(self.north)
            self.island_by_ribbon[nr["name"]] = {i: v for i, v in enumerate(nr["island_w_by_vertex"]) if v}
            for pid, poly, _kinds in pads:
                self.field.add_polygon(PAD_PREFIX + pid, poly)
            self.stub_reach_m = el.pad_stub_reach_m(self.proj)
            lines = el.compute_lines(self.proj) or {}
            for lname, ln in sorted(lines.items()):
                self.field.add_line(LINE_PREFIX + lname, ln["points_xyz_m"], ln["widths_m"])
            self.gated = tuple(GATED_RIBBONS) + tuple(LINE_PREFIX + k for k in sorted(lines))
        mp = data / "mouths.json"
        mouths = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {"mouths": []}
        mouths = mouths["mouths"] if isinstance(mouths, dict) else mouths
        self.mouth_pts = [((m["cut_xyz"][0], m["cut_xyz"][2]), f"mouth {m.get('connector')}@{m.get('host')}:{m.get('host_vertex')}")
                          for m in mouths if m.get("cut_xyz")]
        for rb in self.ribbons[1:]:
            if not rb.closed and rb is not self.north:
                self.mouth_pts.append((rb.xz(0), f"{rb.name} start"))
                self.mouth_pts.append((rb.xz(rb.n - 1), f"{rb.name} end"))
        # the layouts (ledger 0054 P4 layout plates): id, approach direction, race furniture, closure token; and the
        # race declaration's wall geometry (data/barrier_bands.json params) the per-layout rule stands behind
        try:
            cfg_t = json.loads((self.proj / "track.config.json").read_text(encoding="utf-8"))
        except Exception:
            cfg_t = {}
        self.layouts = [{"id": str(lo.get("id")), "direction": "rev" if str(lo.get("direction") or "forward").lower() == "reverse" else "fwd",
                         "race": bool(lo.get("race_furniture")), "token": str(lo.get("closure_token") or "").lower()}
                        for lo in (cfg_t.get("layouts") or []) if isinstance(lo, dict)]
        bb = data / "barrier_bands.json"
        self.walls = None
        if bb.exists():
            prm = (json.loads(bb.read_text(encoding="utf-8")).get("params") or {})
            if prm.get("edge_centre_from_lip_m") is not None and prm.get("barrier_half_m") is not None:
                self.walls = {"edge_centre_from_lip_m": float(prm["edge_centre_from_lip_m"]),
                              "barrier_half_m": float(prm["barrier_half_m"])}
        lp = data / "lights.local.json"
        heads = json.loads(lp.read_text(encoding="utf-8")).get("lampheads", []) if lp.exists() else []
        self.lamp_bases = []
        for (hx, hy, hz) in heads:   # the post stands 1.8 m away from the road (author_lamps_blend)
            d, s = self.mainline.nearest((hx, hz))
            c = self.mainline.xz(int(round(s)))
            rx, rz = unit((c[0] - hx, c[1] - hz))
            self.lamp_bases.append((hx - rx * LAMP_ARM_M, hz - rz * LAMP_ARM_M))
        sp = data / "scatter_positions.json"
        scat = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
        self.plants = [(e["x"], e["z"], zone, i) for zone, lst in scat.items() for i, e in enumerate(lst)]
        # the project's spawns and the repo's synced copy of them — every layout's (warning only: a
        # spawn never moves a sign, see SPAWN_CLEAR_M)
        self.spawn_pts = []
        for d in (data, AIROSO / "tracks" / track_dir_name(self.proj) / "data"):
            for p in spawn_points(d):
                if p not in self.spawn_pts:
                    self.spawn_pts.append(p)

    def race_layouts(self, direction):
        """the race layouts that drive `direction` ('fwd' / 'rev')"""
        return [lo for lo in self.layouts if lo["race"] and lo["direction"] == direction]

    def layout_behind_lip_m(self, cfg):
        """how far past the MAINLINE lip a layout plate stands: the sealing curb strip's centre (edge_centre_from_lip_m,
        negative = inside the lip) + its half width + the curb rule's lateral_offset_m — None without a declaration"""
        if not self.walls:
            return None
        return self.walls["edge_centre_from_lip_m"] + self.walls["barrier_half_m"] + float(cfg["lateral_offset_m"])

    def own_names(self, rb):
        """the pavement that is a ribbon's OWN for the through-road rule: itself, and for the stitched north ribbon
        its four pieces (the road the driver turns onto is never a through road)"""
        if self.north is not None and rb.name == self.north.name:
            return {rb.name, *self.north_pieces}
        return {rb.name}

    def mouth_excludes(self, rb):
        """the mouth labels a ribbon's scan ignores: the stitched north ribbon is not cut at its pieces' pad ends (they
        are its own interior), only at the J1 / J5 mouths the pieces start from"""
        if rb is not self.north and (self.north is None or rb.name != self.north.name):
            return ()
        return {f"{nm} {end}" for nm in self.north_pieces for end in ("start", "end")}

    def nearest_mouth(self, q, exclude=()):
        return min(((math.hypot(q[0] - p[0], q[1] - p[1]), lab) for p, lab in self.mouth_pts if lab not in exclude),
                   default=(float("inf"), "-"))

    def nearest_lamp(self, q):
        return min((math.hypot(q[0] - b[0], q[1] - b[1]) for b in self.lamp_bases), default=float("inf"))

    def nearest_plant(self, q):
        return min(((math.hypot(q[0] - p[0], q[1] - p[1]), p[2], p[3]) for p in self.plants), default=(float("inf"), "-", -1))

    def nearest_spawn(self, q):
        return min(((math.hypot(q[0] - p[0], q[1] - p[1]), lab) for p, lab in self.spawn_pts), default=(float("inf"), "-"))


SPAWN_PREFIXES = ("AC_START", "AC_HOTLAP", "AC_PIT", "AC_TIME")


def spawn_points(data_dir):
    """[((x, z), label)] for every grid / pit / hotlap / timing node in ``data_dir``: the UNION of every
    per-layout data/dummies_<id>.json (tools/layout_dummies.py; ledger 0047 — in a multi-layout build the
    prep writes data/dummies.json = {}), falling back to the single-layout data/dummies.json only when
    no per-layout file exists. Underscore keys are metadata and are skipped."""
    data_dir = Path(data_dir)
    files = sorted(data_dir.glob("dummies_*.json"))
    single = data_dir / "dummies.json"
    if not files and single.exists():
        files = [single]
    out = []
    for dp in files:
        try:
            d = json.loads(dp.read_text(encoding="utf-8"))
        except Exception:
            continue
        tag = dp.stem[len("dummies_"):] if dp.stem.startswith("dummies_") else dp.parent.parent.name
        for k, v in (d.items() if isinstance(d, dict) else ()):
            if k.startswith(SPAWN_PREFIXES) and isinstance(v, (list, tuple)) and len(v) >= 3:
                out.append(((float(v[0]), float(v[2])), f"{k}@{tag}"))
    return out


def track_dir_name(proj):
    """tracks/<slug-with-dashes>/ for the project's slug (san_diego_lake_murray -> san-diego-lake-murray)"""
    try:
        slug = json.loads((Path(proj) / "track.config.json").read_text(encoding="utf-8")).get("slug", "")
    except Exception:
        slug = ""
    cands = [c for c in (slug.replace("_", "-"), slug) if c]
    for cand in cands:                                   # the one that carries the overrides wins
        if (AIROSO / "tracks" / cand / "signs.json").exists():
            return cand
    for cand in cands:                                   # else the dashed repo convention
        if (AIROSO / "tracks" / cand).is_dir():
            return cand
    return slug.replace("_", "-")


class SignsConfigError(ValueError):
    """signs.json carries a knob nothing reads or a plate nothing can build — loud, never silent"""


def validate_overrides(cfg, corners, src="signs.json"):
    """every defaults key must be one DEFAULTS knows (= one the tools read), every corner key one of
    CORNER_KEYS, every plate one of PLATE_GEOMETRY. Raises SignsConfigError."""
    bad = []
    for k in cfg:
        if k not in DEFAULTS:
            bad.append("defaults.%s is not a knob any tool reads (known: %s)" % (k, ", ".join(DEFAULTS)))
    for cid, ov in corners.items():
        if not isinstance(ov, dict):
            bad.append("corners.%s is not an object" % cid)
            continue
        for k in ov:
            if not k.startswith("_") and k not in CORNER_KEYS:
                bad.append("corners.%s.%s is not a key any tool reads (known: %s)" % (cid, k, ", ".join(CORNER_KEYS)))
        subs = [("corners.%s" % cid, ov)]
        for dk in DIRECTION_KEYS:
            sub = ov.get(dk)
            if sub is None:
                continue
            if not isinstance(sub, dict):
                bad.append("corners.%s.%s is not an object" % (cid, dk))
                continue
            for k in sub:
                if not k.startswith("_") and (k not in CORNER_KEYS or k in DIRECTION_KEYS + ("ribbon", "vertex")):
                    bad.append("corners.%s.%s.%s is not a per-approach key (ribbon / vertex / fwd / rev name the corner, once)" % (cid, dk, k))
            subs.append(("corners.%s.%s" % (cid, dk), sub))
        for where, o in subs:
            plate = o.get("plate", PLATE_GEOMETRY[0])
            if plate not in PLATE_GEOMETRY:
                bad.append("%s.plate = %r: no geometry for it (sign_polygons builds %s only)" % (where, plate, "/".join(PLATE_GEOMETRY)))
            if o.get("arrow") is not None and o["arrow"] not in ("left", "right"):
                bad.append("%s.arrow = %r (left|right)" % (where, o["arrow"]))
            if o.get("expect_arrow") is not None and o["expect_arrow"] not in ("left", "right"):
                bad.append("%s.expect_arrow = %r (left|right)" % (where, o["expect_arrow"]))
        if ov.get("per_layout") is not None:
            if not isinstance(ov["per_layout"], bool):
                bad.append("corners.%s.per_layout = %r (true|false)" % (cid, ov["per_layout"]))
            elif ov["per_layout"] and ov.get("ribbon", "MAINLINE") != "MAINLINE":
                bad.append("corners.%s.per_layout: only a MAINLINE corner has race-layout plates (its ribbon is %r)" % (cid, ov.get("ribbon")))
            elif ov["per_layout"] and ov.get("skip"):
                bad.append("corners.%s: per_layout and skip together — a skipped corner has no plates in any layout" % cid)
        # a skip removes a driver's arrow: it carries its reason (the entry's own, or its approach
        # sub-object's), never a silent drop (ledger 0051: a bare rev skip at M4 once passed verify_signs
        # (k) with race_acw's Jackson/Navajo arrow gone)
        for dk in DIRECTION_KEYS if all(isinstance(ov.get(k), (dict, type(None))) for k in DIRECTION_KEYS) else ():
            eff = effective_override(ov, dk == "rev")
            if eff.get("skip") and not (isinstance(eff.get("reason"), str) and eff["reason"].strip()):
                bad.append("corners.%s skips the %s approach with no reason (add \"reason\": \"<why>\" beside the skip)" % (cid, dk))
    if bad:
        raise SignsConfigError("%s: %s" % (src, "; ".join(bad)))


def check_pins(cfg, corners, src="signs.json"):
    """a pin key at the top level of an entry whose corner is scanned in BOTH approaches (every
    connector entry; a mainline entry when both_directions_mainline) would put two plates facing
    opposite approaches on one pin -> SignsConfigError naming the per-approach sub-object to use"""
    bad = []
    for cid, ov in corners.items():
        both = ov.get("ribbon", "MAINLINE") != "MAINLINE" or bool(cfg.get("both_directions_mainline"))
        pins = [k for k in PIN_KEYS if ov.get(k) not in (None, 0, 0.0, [], "")]
        if both and pins:
            bad.append("corners.%s: %s pins ONE approach but this corner is signed in both; move it into "
                       "corners.%s.fwd or corners.%s.rev" % (cid, "/".join(pins), cid, cid))
    if bad:
        raise SignsConfigError("%s: %s" % (src, "; ".join(bad)))


def mirror_arrow(a):
    return {"left": "right", "right": "left"}.get(a, a)


def effective_override(ov, reverse):
    """the keys one approach of a named corner sees: the entry's own keys (arrow / expect_arrow
    mirrored on a reversed scan — the entry speaks for the FORWARD approach) with that approach's
    sub-object laid over them unmirrored (ledger 0051). Two bookkeeping keys ride along:
    _mirrored (the keys that were flipped) and _direction_keys (the keys the sub-object set)."""
    if not ov:
        return {}
    eff = {k: v for k, v in ov.items() if k not in DIRECTION_KEYS}
    mirrored = []
    if reverse:
        for k in ("arrow", "expect_arrow"):
            if eff.get(k) in ("left", "right"):
                eff[k] = mirror_arrow(eff[k])
                mirrored.append(k)
    sub = ov.get("rev" if reverse else "fwd") or {}
    for k, v in sub.items():
        if k.startswith("_"):
            continue
        eff[k] = v
        if k in mirrored:
            mirrored.remove(k)
    eff["_mirrored"] = mirrored
    eff["_direction_keys"] = sorted(k for k in sub if not k.startswith("_"))
    return eff


def load_overrides(proj, signs_path=None):
    """(cfg, corners, path). An EXPLICIT signs_path that does not exist is an error (ledger 0051: a
    mis-pathed --signs once ran with no overrides and placed DCL-2's pair against Kevin's 'keep the
    cul-de-sac sign off'); the default path missing means DEFAULTS (a track with no signs.json)."""
    p = Path(signs_path) if signs_path else AIROSO / "tracks" / track_dir_name(proj) / "signs.json"
    if signs_path and not p.exists():
        raise SignsConfigError("--signs %s: no such file (refusing to run with no overrides)" % p)
    cfg = dict(DEFAULTS)
    corners = {}
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        given = {k: v for k, v in (d.get("defaults") or {}).items() if not k.startswith("_")}
        corners = {k: v for k, v in (d.get("corners") or {}).items() if not k.startswith("_")}
        validate_overrides(given, corners, str(p))
        cfg.update(given)
        check_pins(cfg, corners, str(p))
    return cfg, corners, p


# ----------------------------------------------------------------------------------------------
def march(ctx, rb, A, t, d_clear, only=None):
    """the failed-to-turn ray: returns dict(C, s_C, exit_ribbon, hw_at_exit, t_end, S, s_S, pushed,
    lateral) or None when the ray never leaves pavement within RAY_MAX_M. only = the ribbons that are
    pavement for this ray (a layout plate: the MAINLINE alone), else every ribbon and pad deck."""
    s = 0.0
    C = None
    res = {}
    through = {}          # ANOTHER road's pavement the ray runs along before it leaves pavement: {ribbon: metres}
    own = ctx.own_names(rb)
    while s <= RAY_MAX_M + RAY_EXTRA_CAP_M + 1:
        q = (A[0] + t[0] * s, A[1] + t[1] * s)
        d, name, hw, _ = ctx.field.query(q[0], q[1], only=only)
        if C is None:
            if d <= 0 and name is not None and name not in own and not str(name).startswith((PAD_PREFIX, STUB_PREFIX)):
                through[name] = through.get(name, 0.0) + RAY_STEP
            if d > 0:
                C = q
                res.update(C=q, s_C=s, exit_ribbon=name, hw_at_exit=hw, through=through)
                # T-end: back on ANOTHER ribbon within 3 m of C
                t_end = False
                for k in range(1, int(T_END_PROBE_M / RAY_STEP) + 1):
                    q2 = (q[0] + t[0] * k * RAY_STEP, q[1] + t[1] * k * RAY_STEP)
                    d2, name2, _, _ = ctx.field.query(q2[0], q2[1], only=only)
                    if d2 <= 0 and name2 != name:
                        t_end = True
                        res["t_end_ribbon"] = name2
                        break
                res["t_end"] = t_end
                if s > RAY_MAX_M:
                    return res
        else:
            if d >= d_clear:
                # bisect back to the exact clearance: the 0.25 m step overshoots on oblique exits
                lo, hi = s - RAY_STEP, s
                for _ in range(12):
                    mid = (lo + hi) / 2
                    if ctx.field.query(A[0] + t[0] * mid, A[1] + t[1] * mid, only=only)[0] >= d_clear:
                        hi = mid
                    else:
                        lo = mid
                q = (A[0] + t[0] * hi, A[1] + t[1] * hi)
                res.update(S=q, s_S=hi, pushed_m=round(hi - res["s_C"], 2), lateral_m=0.0)
                return res
            if s - res["s_C"] >= RAY_EXTRA_CAP_M:
                break
        s += RAY_STEP
    if C is None:
        return None
    return res


def slide_candidates():
    """0, +0.25, -0.25, +0.5, ... up to +-SLIDE_MAX_M: the smallest move off the ray first"""
    return [0.0] + [s * k for k in range(1, int(round(SLIDE_MAX_M / SLIDE_STEP_M)) + 1) for s in (SLIDE_STEP_M, -SLIDE_STEP_M)]


def choose_slide(ctx, cfg, S, u, d_clear, clear_fn, rights=(), disc_names=None):
    """clear lamps (>= lamp_clear_m) and plants (>= plant_clear_m) by sliding S along the curb
    direction u, smallest |slide| first, never beyond SLIDE_MAX_M; a candidate must also keep the
    edge clearance clear_fn(x, z) >= d_clear - 0.05 and the HARD disc footprint margin >= 0
    (disc_names: the ribbons whose disc gates this post, see disc_names_for). When no candidate
    clears: stay on the ray, flag a lamp (fatal), exclude the plant (TreeFX drops it).
    -> (slid_m, S, lamp_m, plant(dist, zone, idx), exclude_plant | None, reasons[])"""
    for sl in slide_candidates():
        q = (S[0] + u[0] * sl, S[1] + u[1] * sl)
        if clear_fn(q[0], q[1]) < d_clear - 0.05:
            continue
        if rights and ctx.field.footprint_margin(q, rights, disc_names) < 0:
            continue
        lamp = ctx.nearest_lamp(q)
        plant = ctx.nearest_plant(q)
        if lamp >= cfg["lamp_clear_m"] and plant[0] >= cfg["plant_clear_m"]:
            return sl, q, lamp, plant, None, []
    lamp = ctx.nearest_lamp(S)
    plant = ctx.nearest_plant(S)
    reasons, excl = [], None
    if lamp < cfg["lamp_clear_m"]:
        reasons.append("lamp post base %.1f m from the sign (< %.1f, lamps are never moved; no slide <= %.1f m clears it)"
                       % (lamp, cfg["lamp_clear_m"], SLIDE_MAX_M))
    if plant[0] < cfg["plant_clear_m"]:
        excl = {"zone": plant[1], "index": plant[2], "dist_m": round(plant[0], 2)}
    return 0.0, S, lamp, plant, excl, reasons


def place_corner(ctx, rb, corner, cid, ov, cfg, second=False, layout=None):
    """one approach of one corner -> (record | None, reasons[]). layout = a race layout record
    (Context.layouts) for a LAYOUT PLATE (module doc): the ray is judged against the MAINLINE's pavement
    alone and the post stands behind that layout's sealing wall, Context.layout_behind_lip_m past the lip."""
    n = rb.n
    sg = corner["sign"]
    reasons = []
    D = corner["D_deg"]
    pc = corner["PC"] if not second else corner["PC2"]
    apex = corner["apex"]
    thr = 1.0 / R_STRAIGHT_M
    only = ("MAINLINE",) if layout else None
    # 1) approach tangent: the car's heading over the last 10 m before the hard turn
    a0, a1 = rb.xz(pc - 12), rb.xz(pc - 2)
    if math.hypot(a1[0] - a0[0], a1[1] - a0[1]) < 1.0:    # open ribbon, PC at its very start
        a0, a1 = rb.xz(pc), rb.xz(pc + 6)
    t = unit((a1[0] - a0[0], a1[1] - a0[1]))
    th_pca = pca_heading(rb, pc)
    pca_vs_chord = math.degrees(wrap(th_pca - math.atan2(t[1], t[0])))
    nR = (t[1], -t[0])
    # 2) launch point on the approach lane (un-flared width)
    lo_st = max(pc - 40, 0) if not rb.closed else pc - 40
    w_app = min(rb.w(i) for i in range(lo_st, pc + 1))
    island = ctx.island_by_ribbon.get(rb.name, {}).get(rb.vertex(pc), 0.0)
    lane_off = island / 2 + (w_app - island) / 4
    P_pc = rb.xz(pc)
    A = (P_pc[0] + nR[0] * lane_off, P_pc[1] + nR[1] * lane_off)
    d_clear = cfg["lateral_offset_m"] if rb.name == "MAINLINE" else cfg["lateral_offset_connector_m"]
    d_march = d_clear
    if layout:
        d_march = ctx.layout_behind_lip_m(cfg)
        if d_march is None:
            return None, ["no race declaration (data/barrier_bands.json params): a layout plate stands behind the sealing wall it describes"]
    # 3) the ray
    m = march(ctx, rb, A, t, d_march, only=only)
    if m is None:
        return None, ["ray never leaves pavement within %.0f m (through leg / junction)" % RAY_MAX_M]
    if m["s_C"] < RAY_MIN_M or m["s_C"] > RAY_MAX_M:
        reasons.append("ray exits pavement at %.1f m (want %.0f-%.0f)" % (m["s_C"], RAY_MIN_M, RAY_MAX_M))
    if m.get("t_end"):
        reasons.append("T-end: ray re-enters %s within 3 m of the curb (W1-7 candidate, second pass)" % m["t_end_ribbon"])
    thr_name, thr_run = max(m.get("through", {}).items(), key=lambda kv: kv[1], default=(None, 0.0))
    if thr_run >= THROUGH_ROAD_M:
        reasons.append("ray runs %.0f m down %s before leaving pavement (a through road)" % (thr_run, thr_name))
    C = m["C"]
    pt = corner["PT"]
    arc = corner["arc_m"]
    lo = pc - 10 if rb.closed else max(pc - 10, 0)
    hi = pc - 10 + arc + 90 if rb.closed else min(pt + 80, n - 1)
    _, sC_f = rb.nearest(C, lo, hi)
    sC = int(round(sC_f)) % n if rb.closed else min(int(round(sC_f)), n - 1)
    rel_pc = (sC - pc) % n if rb.closed else sC - pc
    if rb.closed and rel_pc > n // 2:
        rel_pc -= n
    # a ray that leaves through a pad (its deck or down a stub arm) has its foot that much further on (module doc)
    past_pt = RAY_PAST_PT_M + (ctx.stub_reach_m if str(m["exit_ribbon"] or "").startswith(PAD_PREFIX) else 0.0)
    if not (0 <= rel_pc <= arc + past_pt):
        reasons.append("ray foot at station PC%+d is outside [PC, PT+%d] (a curve, not a turn)" % (rel_pc, past_pt))
    # 4) sign point
    if "S" not in m:
        if layout:
            return None, ["the ray is still within %.2f m of the lip %.0f m past it: no room behind the sealing wall" % (d_march, RAY_EXTRA_CAP_M)]
        n_out = (-t[1], t[0]) if D < 0 else (t[1], -t[0])
        m["S"] = (C[0] + n_out[0] * d_clear, C[1] + n_out[1] * d_clear)
        m["s_S"] = m["s_C"]
        m["pushed_m"] = 0.0
        m["lateral_m"] = d_clear
        reasons.append("perpendicular-clearance march capped at +%.0f m; stepped sideways" % RAY_EXTRA_CAP_M)
        reasons = [r for r in reasons if not r.startswith("perpendicular")]   # logged, not fatal
        m["note"] = "perpendicular-clearance march capped; stepped %.2f m sideways" % d_clear
    S = m["S"]
    # 5) outside assertion at the local station nearest C — geometric, never a side convention
    tl = rb.tangent(sC)
    Pc = rb.xz(sC)
    cross = tl[0] * (C[1] - Pc[1]) - tl[1] * (C[0] - Pc[0])     # + = C left of local travel
    outside_cross = cross if D < 0 else -cross
    if outside_cross <= 0:
        reasons.append("OUTSIDE ASSERTION FAILED: C is on the inside of the bend (cross %.2f)" % outside_cross)
    # 6) facing + arrow first (the disc footprint needs the right vector)
    f = (-t[0], -t[1])
    applied = []
    if ov.get("face_bearing_deg") is not None:
        b = math.radians(90.0 - float(ov["face_bearing_deg"]))
        f = (math.cos(b), math.sin(b))
        nR = (-f[1], f[0])      # the approach is t = -f, so the driver's right (t_z, -t_x) = (-f_z, f_x)
        applied.append("face_bearing_deg=%.1f" % float(ov["face_bearing_deg"]))
    arrow = "right" if D < 0 else "left"
    if ov.get("arrow") in ("left", "right"):
        arrow = ov["arrow"]
        applied.append("arrow=%s" % arrow)
    expect = ov.get("expect_arrow")
    if expect in ("left", "right") and expect != arrow:
        reasons.append("expect_arrow=%s%s but the rule computed %s (D %.1f deg) — not relocated, see signs.json"
                       % (expect, " (mirrored for the reverse approach)" if "expect_arrow" in ov.get("_mirrored", ()) else "", arrow, D))
    for k in ov.get("_mirrored", ()):
        applied.append("%s mirrored for the reverse approach (%s -> %s)" % (k, mirror_arrow(ov[k]), ov[k]))
    for k in ov.get("_direction_keys", ()):
        applied.append("%s.%s" % ("rev" if rb.reverse else "fwd", k))
    # 7) clearances: lamps never move; plants are excluded from TreeFX; the sign may slide along
    #    the curb (u at sC), <= SLIDE_MAX_M, the smallest move first — the only lateral deviation
    u = unit((rb.xz(sC + 1)[0] - rb.xz(sC - 1)[0], rb.xz(sC + 1)[1] - rb.xz(sC - 1)[1]))
    disc_names = GATED_RIBBONS if layout else disc_names_for(rb.name, ctx.gated)   # a race layout sweeps the mainline alone
    slid, S, lamp, plant, excl_plant, slide_reasons = choose_slide(
        ctx, cfg, S, u, d_march, lambda x, z: ctx.field.query(x, z, only=only)[0], rights=(nR,), disc_names=disc_names)
    reasons += slide_reasons
    # 8) manual overrides
    if ov.get("slide_along_curb_m"):
        sl = float(ov["slide_along_curb_m"])
        S = (S[0] + u[0] * sl, S[1] + u[1] * sl)
        slid += sl
        applied.append("slide_along_curb_m=%.2f" % sl)
    if ov.get("base_xz"):
        S = (float(ov["base_xz"][0]), float(ov["base_xz"][1]))
        applied.append("base_xz")
    if ov.get("force"):
        applied.append("force")
    height = float(ov.get("height_m", cfg["height_m"]))
    om = bool(ov.get("om1_3", cfg["om1_3"]))
    plate = ov.get("plate", PLATE_GEOMETRY[0])
    if plate not in PLATE_GEOMETRY:
        raise SignsConfigError("corner %s: plate %r has no geometry (only %s)" % (cid, plate, "/".join(PLATE_GEOMETRY)))
    # 9) the rest of the checks
    y_road = rb.y(sC)
    gate_margin = ctx.field.footprint_margin(S, (nR,))                 # every centreline, logged
    gate_margin_gated = ctx.field.footprint_margin(S, (nR,), disc_names)   # the discs a gate enforces
    edge_clear = ctx.field.query(S[0], S[1], only=only)[0]
    edge_clear_all = ctx.field.query(S[0], S[1])[0] if layout else edge_clear   # a layout plate stands on the sealed opening's deck
    spawn = ctx.nearest_spawn(S)
    warns = []
    if layout:
        warns.append("layout plate for %s: stands %.2f m past the MAINLINE lip, behind its sealing wall (strip centre %+.3f m "
                     "from the lip, half width %.3f m, + lateral_offset_m %.2f); every other pavement %+.2f m away"
                     % (layout["id"], d_march, ctx.walls["edge_centre_from_lip_m"], ctx.walls["barrier_half_m"], d_clear, edge_clear_all))
    if abs(pca_vs_chord) > 5:
        warns.append("approach heading: 10 m chord %.1f deg vs PCA fit %.1f deg (differ by %.1f deg; the chord is used)"
                     % (bearing(t[0], t[1]), bearing(math.cos(th_pca), math.sin(th_pca)), abs(pca_vs_chord)))
    if spawn[0] < SPAWN_CLEAR_M:
        warns.append("%.0f m from %s (< %.0f m spawn/gate exclusion, placed anyway)" % (spawn[0], spawn[1], SPAWN_CLEAR_M))
    if gate_margin_gated < 0:   # the disc drive_test enforces (mainline post: every ribbon's)
        reasons.append("plate footprint inside drive_test's obstacle disc by %.2f m" % -gate_margin_gated)
    elif gate_margin < 0:       # a connector post inside its own street's disc: logged, not gated
        warns.append("plate footprint %.2f m inside the obstacle disc of a connector centreline (not gated: drive_test sweeps the mainline only; the post stays at the back of the walk)" % -gate_margin)
    if edge_clear < 0:
        reasons.append("sign base is ON pavement (edge clearance %.2f)" % edge_clear)
    if "note" in m:
        warns.append(m["note"])
    # old rule, for the comparison picture: rev1 = advance diamond ~52 m before the bend on the
    # outside; rev2 = apex, side FLIPPED (inside on SD), flare width/2 + 2.8
    o_st = pc - int(OLD_REV1_LEAD_M)
    o_t = rb.tangent(o_st)
    o_n = (-o_t[1], o_t[0]) if D < 0 else (o_t[1], -o_t[0])
    o_p = rb.xz(o_st)
    o_off = rb.w(o_st) / 2 + OLD_REV1_LATERAL
    a_t = rb.tangent(apex)
    a_n = (a_t[1], -a_t[0]) if D < 0 else (-a_t[1], a_t[0])     # the flipped (= inside) side
    a_p = rb.xz(apex)
    a_off = rb.w(apex) / 2 + OLD_REV2_LATERAL
    rec = {
        "id": (cid if not second else cid + "-2") + ((LAYOUT_SEP + layout["id"]) if layout else ""),
        "kind": plate + ("R" if arrow == "right" else "L"),
        "plate": plate,
        "layout": layout["id"] if layout else None,
        "ribbon": rb.name, "direction": "rev" if rb.reverse else "fwd",
        "corner": {"apex_vertex": rb.vertex(apex), "apex_station_m": apex, "PC": pc, "PT": pt, "arc_m": arc,
                   "R_apex_m": round(corner["R_apex_m"], 1), "D_deg": round(D, 1),
                   "turn": "right" if D < 0 else "left", "apex_xz": [round(a_p[0], 2), round(a_p[1], 2)],
                   "second_arrow": second, "R_at_PC_m": round(1.0 / max(abs(rb.kappa(pc)), 1e-9), 1)},
        "approach": {"t_xz": [round(t[0], 4), round(t[1], 4)], "bearing_deg": round(bearing(t[0], t[1]), 1),
                     "pca_vs_chord_deg": round(pca_vs_chord, 2), "w_app_m": round(w_app, 2),
                     "w_at_apex_m": round(rb.w(apex), 2), "island_m": island, "lane_off_m": round(lane_off, 2)},
        "ray": {"A_xz": [round(A[0], 2), round(A[1], 2)], "len_m": round(m["s_C"], 2),
                "C_xz": [round(C[0], 2), round(C[1], 2)], "exit_ribbon": m["exit_ribbon"],
                "hw_at_exit_m": round(m["hw_at_exit"], 2), "sC_station": sC, "sC_rel_PC_m": rel_pc,
                "sC_rel_apex_m": rel_pc - ((apex - pc) % n if rb.closed else apex - pc),
                "s_S_m": round(m["s_S"], 2)},
        "base_xz": [round(S[0], 3), round(S[1], 3)],
        "curb_dir_xz": [round(u[0], 4), round(u[1], 4)],
        "y_road_at_sC": round(y_road, 3),
        "y_base": {"analytic": round(y_road + WALK_ABOVE_ROAD, 3), "raycast": None, "source": "analytic"},
        "face_dir_xz": [round(f[0], 4), round(f[1], 4)],
        "face_bearing_deg": round(bearing(f[0], f[1]), 1),
        "yaw_deg": round(math.degrees(math.atan2(f[1], f[0])), 2),
        "right_xz": [round(nR[0], 4), round(nR[1], 4)],
        "arrow": arrow, "expect_arrow": expect if expect in ("left", "right") else None,
        "lateral_offset_m": d_clear, "height_m": height, "om1_3": om,
        **({"wall": {"behind_lip_m": round(d_march, 3), "edge_centre_from_lip_m": ctx.walls["edge_centre_from_lip_m"],
                     "barrier_half_m": ctx.walls["barrier_half_m"], "token": layout.get("token"),
                     "rule": "the layout's sealing curb strip: its far face stands in for the curb face, lateral_offset_m behind it"}}
           if layout else {}),
        "checks": {"outside_cross": round(outside_cross, 2), "edge_clear_m": round(edge_clear, 2),
                   **({"edge_clear_all_m": round(edge_clear_all, 2)} if layout else {}),
                   "lamp_m": round(lamp, 2), "plant_m": round(plant[0], 2), "plant_zone": plant[1],
                   "pushed_m": m["pushed_m"], "slid_m": round(slid, 2), "lateral_step_m": m.get("lateral_m", 0.0),
                   "gate_margin_m": round(gate_margin, 2), "gate_margin_gated_m": round(gate_margin_gated, 2),
                   "gate_ribbons": gate_label(disc_names),
                   "mouth_m": round(ctx.nearest_mouth(S)[0], 1),
                   "spawn_m": round(spawn[0], 1), "spawn": spawn[1], "warnings": warns},
        "old_rule": {"rev1_xz": [round(o_p[0] + o_n[0] * o_off, 2), round(o_p[1] + o_n[1] * o_off, 2)],
                     "rev1": "k10-colorado 5b38b59: advance diamond ~%.0f m BEFORE the bend, outside, w/2+%.1f" % (OLD_REV1_LEAD_M, OLD_REV1_LATERAL),
                     "rev2_xz": [round(a_p[0] + a_n[0] * a_off, 2), round(a_p[1] + a_n[1] * a_off, 2)],
                     "rev2": "k10-colorado e2334c9: at the apex, side flipped (= INSIDE on SD), flare w/2+%.1f" % OLD_REV2_LATERAL},
        "overrides_applied": applied,
        "exclude_plant": excl_plant,
        "where": ov.get("where", ""),
    }
    return rec, reasons


def corner_id(rb, k):
    """candidate id for a corner no signs.json entry names: <ribbon prefix>-c<k> in station order
    (the survey ids M1..M5 / MED-k / DCL-k come from signs.json, matched by vertex)"""
    return "%s-c%d" % (RIBBON_PREFIX.get(rb.name, rb.name.replace("#", "_").replace("+", "_").upper()), k)


PLATE_KEYS = ("id", "kind", "plate", "layout", "direction", "corner", "approach", "ray", "face_dir_xz", "face_bearing_deg",
              "yaw_deg", "right_xz", "arrow", "expect_arrow", "old_rule", "where", "base_xz", "curb_dir_xz",
              "overrides_applied")


def split_layout_id(cid):
    """('M3-fwd', 'race_cw') for a layout plate's id, (cid, None) otherwise"""
    if LAYOUT_SEP in cid:
        core, lid = cid.split(LAYOUT_SEP, 1)
        return core, lid
    return cid, None


def merge_pairs(signs, thr=PAIR_MERGE_M, log=None):
    """a two-way connector corner whose -fwd and -rev posts stand < thr apart becomes ONE record:
    one post at the mean base, both plates on it (each keeps its own approach, facing, arrow and
    checks under "plates"); the top-level facing/arrow/ray are the -fwd plate's so every reader
    that knows one plate still draws something sensible. Idempotent; stable order."""
    by_corner = {}
    for s in signs:
        if "plates" in s or not s["id"].endswith(("-fwd", "-rev")) or s.get("layout"):   # a layout plate never pairs
            continue
        by_corner.setdefault(s["id"].rsplit("-", 1)[0], []).append(s)
    merged, drop = {}, set()
    for cid, lst in by_corner.items():
        if len(lst) != 2:
            continue
        a, b = sorted(lst, key=lambda s: s["direction"])          # fwd first
        dist = math.dist(a["base_xz"], b["base_xz"])
        if dist >= thr:
            continue
        base = [round((a["base_xz"][0] + b["base_xz"][0]) / 2, 3), round((a["base_xz"][1] + b["base_xz"][1]) / 2, 3)]
        rec = {k: a[k] for k in a if k not in ("checks", "exclude_plant")}
        rec.update(id=cid, kind=a["kind"] + "+" + b["kind"], direction="both", pair=True,
                   pair_split_m=round(dist, 2), base_xz=base,
                   plates=[{k: s[k] for k in PLATE_KEYS if k in s} for s in (a, b)])
        for p, s in zip(rec["plates"], (a, b)):
            p["checks"] = {k: s["checks"][k] for k in ("outside_cross", "slid_m", "pushed_m", "lateral_step_m") if k in s["checks"]}
        ca, cb = a["checks"], b["checks"]
        rec["checks"] = dict(ca)
        for k in ("edge_clear_m", "mesh_clear_m", "lamp_m", "plant_m", "gate_margin_m", "gate_margin_gated_m", "mouth_m", "spawn_m"):
            if k in ca and k in cb:
                rec["checks"][k] = min(ca[k], cb[k])
        if ca.get("walk_behind_m") is not None and cb.get("walk_behind_m") is not None:
            rec["checks"]["walk_behind_m"] = max(ca["walk_behind_m"], cb["walk_behind_m"])
        rec["checks"]["warnings"] = list(ca.get("warnings", [])) + list(cb.get("warnings", [])) + [
            "paired: -fwd and -rev posts were %.2f m apart (< %.1f) -> one post, two plates" % (dist, thr)]
        rec["exclude_plant"] = a.get("exclude_plant") or b.get("exclude_plant")
        merged[id(a)] = rec
        drop.add(id(b))
        if log:
            log("[signs] pair %s: -fwd/-rev bases %.2f m apart (< %.1f) -> one post at (%.2f, %.2f) with %s" % (cid, dist, thr, base[0], base[1], rec["kind"]))
    out = []
    for s in signs:
        if id(s) in drop:
            continue
        out.append(merged.get(id(s), s))
    return out


def plates_of(rec):
    """the plates a record carries: itself, or the pair's two"""
    return rec.get("plates") or [rec]


def fwd_station(rb, apex):
    """a corner's apex station in the FORWARD point order of its ribbon"""
    if not rb.reverse:
        return apex
    return (-apex) % rb.n if rb.closed else rb.n - 1 - apex


def candidate_ids(rb, corners, fwd_ids):
    """[id per corner]: a forward ribbon numbers its corners <prefix>-c<k> in station order; a
    reversed ribbon reuses the forward id of the nearest forward corner within MERGE_APEX_M that
    turns the SAME way (a forward right turn is a reverse left turn), else the corner is one only
    the reverse scan sees (a mouth stub at a ribbon end) and gets <prefix>-r<k>. Unique per ribbon
    + direction by construction (ties: the closer corner keeps the id)."""
    if not rb.reverse:
        return [corner_id(rb, k + 1) for k in range(len(corners))]
    claims = {}
    for ci, c in enumerate(corners):
        st = fwd_station(rb, c["apex"])
        near = [(rb.dist_stations(st, e[0]), e[1]) for e in fwd_ids if e[2] == -c["sign"]]
        near = [e for e in near if e[0] < MERGE_APEX_M]
        if near:
            d, cid = min(near)
            if cid not in claims or claims[cid][0] > d:
                claims[cid] = (d, ci)
    out = [None] * len(corners)
    for cid, (_, ci) in claims.items():
        out[ci] = cid
    k = 0
    for ci in sorted(range(len(corners)), key=lambda i: corners[i]["apex"]):
        if out[ci] is None:
            k += 1
            out[ci] = "%s-r%d" % (RIBBON_PREFIX.get(rb.name, rb.name.replace("#", "_").replace("+", "_").upper()), k)
    return out


def dedupe_skipped(skipped):
    """one entry per (ribbon label, direction suffix, apex station); the first wins, its reasons
    gain any the duplicate carried"""
    seen, out = {}, []
    for s in skipped:
        core, lid = split_layout_id(s["id"])
        key = (s["ribbon"], core.rsplit("-", 1)[-1] if core.endswith(("-fwd", "-rev")) else "", s.get("apex_station_m"), core.endswith("-2"), lid)
        if key in seen:
            for r in s["reasons"]:
                if r not in seen[key]["reasons"]:
                    seen[key]["reasons"].append(r)
            continue
        seen[key] = s
        out.append(s)
    return out


def assign_overrides(rb, fwd_rb, corners, corners_cfg):
    """{corner index: (id, entry)} — each signs.json entry names the ONE detected corner nearest
    its vertex (within 30 m, forward stations), so a mouth stub 9 m from a real corner cannot
    steal its id"""
    fwd_st = [c["apex"] if not rb.reverse else ((-c["apex"]) % rb.n if rb.closed else rb.n - 1 - c["apex"]) for c in corners]
    out = {}
    for cid, ov in corners_cfg.items():
        if ov.get("ribbon", "MAINLINE") != rb.name or ov.get("vertex") is None:
            continue
        v_st = fwd_rb.cum[min(int(ov["vertex"]), len(fwd_rb.cum) - 1)]
        if fwd_rb.closed:
            v_st %= fwd_rb.L
        cand = [(fwd_rb.dist_stations(int(v_st), fwd_st[i]), i) for i in range(len(corners)) if i not in out]
        cand = [c for c in cand if c[0] <= OVERRIDE_STALE_M]
        if cand:
            out[min(cand)[1]] = (cid, ov)
    return out


def place_all(proj, cfg=None, corners_cfg=None, signs_path=None, log=print, merge=True):
    """every sign on the polyline data -> (out, ctx). merge=False leaves -fwd/-rev pairs separate
    (tools/author_signs_blend.py marches each plate on the built mesh first, then merges)"""
    if cfg is None:
        cfg, corners_cfg, _ = load_overrides(proj, signs_path)
    corners_cfg = corners_cfg or {}
    ctx = Context(proj, cfg)
    signs, skipped, excl = [], [], []
    seen_ids = set()
    ribbons = [ctx.mainline]
    if cfg.get("include_connectors", True):
        for rb in ctx.ribbons[1:]:
            ribbons.append(rb)
            ribbons.append(rb.copy(reverse=True))
    if cfg.get("both_directions_mainline"):
        ribbons.insert(1, ctx.mainline.copy(reverse=True))
    if ctx.north_note:
        log("[signs] WARN %s" % ctx.north_note)
    fwd_ids = {}
    fwd_rbs = {r.name: r for r in ctx.ribbons}
    layout_plates = []        # ledger 0054 P4: the race-layout plates of per_layout corners
    for rb in ribbons:
        corners = detect_corners(rb, ctx.hyst)
        corners.sort(key=lambda c: c["apex"])
        if not rb.reverse:
            fwd_ids[rb.name] = [(c["apex"], corner_id(rb, k + 1), c["sign"]) for k, c in enumerate(corners)]
        cids = candidate_ids(rb, corners, fwd_ids.get(rb.name, []))
        named = assign_overrides(rb, fwd_rbs[rb.name], corners, corners_cfg)
        mouth_ex = ctx.mouth_excludes(rb)
        direction = "rev" if rb.reverse else "fwd"
        for ci, c in enumerate(corners):
            # id: forward numbering in station order; a reversed ribbon reuses the forward id of
            # the same bend, else a reverse-only id (candidate_ids) — never two records of one
            # ribbon + direction under one id
            cid = cids[ci]
            ov_id, ov = named.get(ci, (None, {}))
            ov = effective_override(ov, rb.reverse)
            if ov_id:
                cid = ov_id
                seen_ids.add(ov_id)
            if rb.name != "MAINLINE" or cfg.get("both_directions_mainline"):
                cid_dir = cid + ("-rev" if rb.reverse else "-fwd")
            else:
                cid_dir = cid
            base = {"id": cid_dir, "ribbon": rb.label(), "apex_vertex": rb.vertex(c["apex"]),
                    "apex_station_m": c["apex"], "R_apex_m": round(c["R_apex_m"], 1), "D_deg": round(c["D_deg"], 1),
                    "arc_m": c["arc_m"], "apex_xz": [round(v, 1) for v in rb.xz(c["apex"])]}
            reasons = []
            if ov.get("skip"):
                reasons.append("signs.json skip: %s" % ov["reason"].strip())      # validate_overrides refused a bare skip
            rule_reasons = []
            if not ov.get("force"):
                if c["R_apex_m"] > cfg["r_sign_max_m"]:
                    rule_reasons.append("R_apex %.1f > %.0f m" % (c["R_apex_m"], cfg["r_sign_max_m"]))
                if abs(c["D_deg"]) < cfg["defl_min_deg"]:
                    rule_reasons.append("|D| %.1f < %.0f deg" % (abs(c["D_deg"]), cfg["defl_min_deg"]))
            reasons += rule_reasons
            dm = ctx.nearest_mouth(rb.xz(c["apex"]), mouth_ex)
            if dm[0] < MOUTH_CLEAR_M and not ov.get("force"):
                reasons.append("apex %.0f m from %s (< %.0f m: mouth-flare geometry)" % (dm[0], dm[1], MOUTH_CLEAR_M))
            placed_shared = False
            if reasons:
                skipped.append(dict(base, reasons=reasons))
            else:
                rec, reasons = place_corner(ctx, rb, c, cid_dir, ov, cfg)
                if reasons and not ov.get("force"):
                    skipped.append(dict(base, reasons=reasons, would_be=rec and rec["base_xz"]))
                else:
                    if reasons:
                        rec["checks"]["warnings"] += ["FORCED past: " + r for r in reasons]
                    signs.append(rec)
                    placed_shared = True
                    if rec["exclude_plant"]:
                        excl.append(dict(rec["exclude_plant"], sign=rec["id"]))
            # a per_layout MAINLINE corner (module doc "layout"): every race layout that drives this approach and
            # got no shared plate gets its own plate behind its sealing wall — or a skip record of its own
            if ov.get("per_layout") and rb.name == "MAINLINE" and not ov.get("skip") and not placed_shared:
                for lo in ctx.race_layouts(direction):
                    lid_dir = cid_dir + LAYOUT_SEP + lo["id"]
                    lbase = dict(base, id=lid_dir, layout=lo["id"])
                    if rule_reasons:
                        skipped.append(dict(lbase, reasons=list(rule_reasons)))
                        continue
                    rec, lreasons = place_corner(ctx, rb, c, cid_dir, ov, cfg, layout=lo)
                    if lreasons and not ov.get("force"):
                        skipped.append(dict(lbase, reasons=lreasons, would_be=rec and rec["base_xz"]))
                        continue
                    if lreasons:
                        rec["checks"]["warnings"] += ["FORCED past: " + r for r in lreasons]
                    signs.append(rec)
                    layout_plates.append(rec["id"])
                    if rec["exclude_plant"]:
                        excl.append(dict(rec["exclude_plant"], sign=rec["id"]))
            if not placed_shared:
                continue
            # hairpin: a second arrow from the R = 20 m crossing
            want2 = abs(c["D_deg"]) >= cfg["hairpin_deg"] and c["arc_m"] >= HAIRPIN_ARC_M
            if ov.get("second_arrow") is not None:
                want2 = bool(ov["second_arrow"])
            if want2:
                pc2 = walk_to_straight(rb, c["apex"], -1, 1.0 / HAIRPIN_R_PC2, ctx.hyst)
                c2 = dict(c, PC2=pc2)
                rec2, reasons2 = place_corner(ctx, rb, c2, cid_dir, ov, cfg, second=True)
                if rec2 is None:
                    skipped.append(dict(base, id=cid_dir + "-2", reasons=reasons2))
                elif math.dist(rec2["base_xz"], rec["base_xz"]) < HAIRPIN_SPLIT_M:
                    skipped.append(dict(base, id=cid_dir + "-2", reasons=["second arrow %.1f m from the first (< %.0f)" % (math.dist(rec2["base_xz"], rec["base_xz"]), HAIRPIN_SPLIT_M)]))
                elif reasons2 and not ov.get("force"):
                    skipped.append(dict(base, id=cid_dir + "-2", reasons=reasons2, would_be=rec2["base_xz"]))
                else:
                    rec2["corner"]["PC"] = pc2
                    signs.append(rec2)
                    if rec2["exclude_plant"]:
                        excl.append(dict(rec2["exclude_plant"], sign=rec2["id"]))
    stale = [cid for cid in corners_cfg if cid not in seen_ids and corners_cfg[cid].get("vertex") is not None]
    for cid in stale:
        log("[signs] WARN signs.json corner %s: no detected corner within %.0f m of vertex %s (stale override, refused)"
            % (cid, OVERRIDE_STALE_M, corners_cfg[cid].get("vertex")))
    if merge:
        signs = merge_pairs(signs, log=log)
    skipped = dedupe_skipped(skipped)
    dup = [i for i in {s["id"] for s in skipped} if sum(1 for s in skipped if s["id"] == i) > 1]
    if dup:
        raise RuntimeError("skipped ids repeat after candidate_ids/dedupe: %s" % ", ".join(sorted(dup)))
    out = {
        "frame": "engine ENU local metres: x = East, y = up, z = North (data/centerline.local.json); Blender = (x, z, y)",
        "rule": "W1-6 at the corner, outside of the bend, in line with and facing the approach (tools/place_signs.py)",
        "defaults": cfg,
        "signs": signs,
        "skipped": skipped,
        "exclude_plants": excl,
        "stale_overrides": stale,
        "pairs": [s["id"] for s in signs if s.get("pair")],
        # ledger 0054 P4: the stitched north ribbon (its pieces, so the verifier rebuilds the same line), the gated discs,
        # the race layouts and the plates that ship in a layout's closure kn5 rather than the road kn5
        "north": ({"ribbon": ctx.north.name, "pieces": ctx.north_pieces, "points": len(ctx.north.raw),
                   "pads": [n for n, _p, _b in ctx.field.polys], "stub_reach_m": ctx.stub_reach_m}
                  if ctx.north is not None else None),
        "north_note": ctx.north_note,
        "gated_ribbons": list(ctx.gated),
        "layouts": ctx.layouts,
        "layout_plates": layout_plates,
        "counts": {"placed": len(signs), "plates": sum(len(plates_of(s)) for s in signs), "skipped": len(skipped),
                   "layout_plates": len(layout_plates)},
    }
    return out, ctx


# ----------------------------------------------------------------------------------------------
def plate_polygons(out, sx, sz, f, r, h0, arrow, om, y_base, info=None):
    """one plate (+ border, arrow, optional OM1-3 diamond) on the post at (sx, sz), facing f,
    bottom edge at h0; returns the plate top height. info (a list) receives the plate's own
    vertices — front face, back face, arrow glyph — so tools/verify_signs.py can measure the
    built facing, height and arrow from GEOMETRY rather than read them back from this record."""
    h1 = h0 + PLATE_H
    mirror = -1.0 if arrow == "left" else 1.0

    def P(u, v, w):
        return (sx + r[0] * u + f[0] * w, v, sz + r[1] * u + f[1] * w)

    nf = (f[0], 0.0, f[1])
    nb = (-f[0], 0.0, -f[1])
    wf, wb = PLATE_FRONT_OFF, PLATE_FRONT_OFF - PLATE_BACK_GAP
    hw = PLATE_W / 2
    front = [P(-hw, h0, wf), P(hw, h0, wf), P(hw, h1, wf), P(-hw, h1, wf)]
    back = [P(-hw, h0, wb), P(hw, h0, wb), P(hw, h1, wb), P(-hw, h1, wb)]
    out["SIGNPLATE"].append((front, nf))
    out["SIGNPOST"].append((back, nb))
    if info is not None:
        arrow_v = [P(mirror * (x - 24.0) * 0.0254, h0 + y * 0.0254, wf + ARROW_PROUD) for (x, y) in ARROW_IN]
        info.append({"front_xyz": [[round(c, 4) for c in v] for v in front],
                     "back_xyz": [[round(c, 4) for c in v] for v in back],
                     "arrow_xyz": [[round(c, 4) for c in v] for v in arrow_v]})
    # black border: 0.75 in band inset 0.5 in (four strips, 2 mm proud)
    i0, i1 = PLATE_BORDER_INSET, PLATE_BORDER_INSET + PLATE_BORDER_W
    wbd = wf + BORDER_PROUD
    for (ua, ub, va, vb) in ((-hw + i0, hw - i0, h0 + i0, h0 + i1), (-hw + i0, hw - i0, h1 - i1, h1 - i0),
                             (-hw + i0, -hw + i1, h0 + i1, h1 - i1), (hw - i1, hw - i0, h0 + i1, h1 - i1)):
        out["SIGNARROW"].append(([P(ua, va, wbd), P(ub, va, wbd), P(ub, vb, wbd), P(ua, vb, wbd)], nf))
    # the arrow, 4 mm proud, tip first (fan triangulation hangs off vertex 0)
    wa = wf + ARROW_PROUD
    out["SIGNARROW"].append(([P(mirror * (x - 24.0) * 0.0254, h0 + y * 0.0254, wa) for (x, y) in ARROW_IN], nf))
    # OM1-3 all-yellow diamond under the plate
    if om:
        hd = OM13_SIDE * math.sqrt(0.5)
        vc = h0 - OM13_GAP - hd
        out["SIGNPLATE"].append(([P(0, vc + hd, wf), P(-hd, vc, wf), P(0, vc - hd, wf), P(hd, vc, wf)], nf))
        out["SIGNPOST"].append(([P(0, vc + hd, wb), P(-hd, vc, wb), P(0, vc - hd, wb), P(hd, vc, wb)], nb))
    return h1


def sign_polygons(rec, y_base, info=None):
    """the sign as engine-frame polygons: {kind: [(verts[(x, y, z)...], normal(x, y, z)), ...]}.
    Winding is NOT meaningful here — the emitter orders each polygon to its normal. A paired
    record (merge_pairs) gets ONE post and both plates: back-to-back at the same height when
    their facings are >= 90 deg apart, else the second plate stacks above the first (two plates
    30 deg apart at one height would cut through each other) and carries no diamond. info (a
    list) receives one entry per plate (plate_polygons) plus the post's base corners."""
    sx, sz = rec["base_xz"]
    out = {"SIGNPLATE": [], "SIGNARROW": [], "SIGNPOST": []}
    plates = plates_of(rec)
    h0 = y_base + rec["height_m"]
    h_top = h0
    f0 = plates[0]["face_dir_xz"]
    for k, p in enumerate(plates):
        f, r = p["face_dir_xz"], p["right_xz"]
        om = rec.get("om1_3", True)
        hk = h0
        if k > 0 and f[0] * f0[0] + f[1] * f0[1] > 0:       # same-side facings: stack, no diamond
            hk, om = h_top + PAIR_STACK_GAP, False
        h_top = max(h_top, plate_polygons(out, sx, sz, f, r, hk, p["arrow"], om, y_base, info))
    h1 = h_top
    f, r = plates[0]["face_dir_xz"], plates[0]["right_xz"]

    def P(u, v, w):
        return (sx + r[0] * u + f[0] * w, v, sz + r[1] * u + f[1] * w)

    nf = (f[0], 0.0, f[1])
    nb = (-f[0], 0.0, -f[1])
    # the post: 2 in square tube, sunk 0.30 m, 5 cm over the (highest) plate top
    hp = POST_W / 2
    v0, v1 = y_base - POST_SINK, h1 + POST_OVER_TOP
    nr = (r[0], 0.0, r[1])
    nl = (-r[0], 0.0, -r[1])
    out["SIGNPOST"] += [
        ([P(hp, v0, -hp), P(hp, v0, hp), P(hp, v1, hp), P(hp, v1, -hp)], nr),
        ([P(-hp, v0, hp), P(-hp, v0, -hp), P(-hp, v1, -hp), P(-hp, v1, hp)], nl),
        ([P(-hp, v0, hp), P(hp, v0, hp), P(hp, v1, hp), P(-hp, v1, hp)], nf),
        ([P(hp, v0, -hp), P(-hp, v0, -hp), P(-hp, v1, -hp), P(hp, v1, -hp)], nb),
        ([P(-hp, v1, -hp), P(hp, v1, -hp), P(hp, v1, hp), P(-hp, v1, hp)], (0.0, 1.0, 0.0)),
    ]
    if info is not None:
        info.append({"post_base_xyz": [[round(c, 4) for c in v] for v in (P(hp, v0, -hp), P(hp, v0, hp), P(-hp, v0, hp), P(-hp, v0, -hp))],
                     "post_top_y": round(v1, 4)})
    return out


# ----------------------------------------------------------------------------------------------
def write_svg(path, out, ctx, win_m=60.0, px_per_m=6.0):
    """one top-down window per sign: pavement, walk band, lane line, A->C ray, post, plate, facing"""
    signs = out["signs"]
    if not signs:
        Path(path).write_text('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="60"><text x="10" y="30">no signs placed</text></svg>', encoding="utf-8")
        return
    W = int(win_m * px_per_m)
    cols = 3
    rows = (len(signs) + cols - 1) // cols
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif" font-size="11">' % (cols * (W + 10), rows * (W + 10))]
    parts.append('<rect width="100%" height="100%" fill="#2e4a2a"/>')
    for k, s in enumerate(signs):
        cx, cz = s["base_xz"]
        ox, oy = (k % cols) * (W + 10), (k // cols) * (W + 10)

        def px(p):
            return (ox + (p[0] - cx + win_m / 2) * px_per_m, oy + (win_m / 2 - (p[1] - cz)) * px_per_m)

        g = ['<g><clipPath id="c%d"><rect x="%d" y="%d" width="%d" height="%d"/></clipPath><g clip-path="url(#c%d)">' % (k, ox, oy, W, W, k)]
        g.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#3a5a34"/>' % (ox, oy, W, W))
        # the junction pads' built decks (ledger 0054 P4): the pavement the north ribbon's ray crosses
        for pname, poly, (x0, z0, x1, z1) in ctx.field.polys:
            if x1 < cx - win_m or x0 > cx + win_m or z1 < cz - win_m or z0 > cz + win_m:
                continue
            g.append('<polygon points="%s" fill="#55555a" stroke="#b9b7ad" stroke-width="1"/>'
                     % " ".join("%.1f,%.1f" % px(p) for p in poly))
        for rb in ctx.ribbons:
            if ctx.north is not None and rb.name == ctx.north.name:
                continue                                   # its pieces are drawn; the stitched line would double them
            near = [i for i in range(rb.n) if abs(rb.xz(i)[0] - cx) < win_m and abs(rb.xz(i)[1] - cz) < win_m]
            if not near:
                continue
            walk = CURB_FACE_W + SIDEWALK_W["MAINLINE" if rb.name == "MAINLINE" else "CONNECTOR"]
            for layer, extra, col in (("walk", walk, "#b9b7ad"), ("road", 0.0, "#55555a")):
                for i in near:
                    a, b = px(rb.xz(i)), px(rb.xz(i + 1))
                    if rb.st(i + 1) == rb.st(i):
                        continue
                    g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f" stroke-linecap="round"/>'
                             % (a[0], a[1], b[0], b[1], col, (rb.w(i) + 2 * extra) * px_per_m))
            for i in near:
                a, b = px(rb.xz(i)), px(rb.xz(i + 1))
                g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#e8c84a" stroke-width="1"/>' % (a[0], a[1], b[0], b[1]))
        A, C = px(s["ray"]["A_xz"]), px(s["ray"]["C_xz"])
        g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#ff4040" stroke-width="2" stroke-dasharray="6,3"/>' % (A[0], A[1], C[0], C[1]))
        t = s["approach"]["t_xz"]
        tail = px((s["ray"]["A_xz"][0] - t[0] * 25, s["ray"]["A_xz"][1] - t[1] * 25))
        g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#ffffff" stroke-width="2"/>' % (tail[0], tail[1], A[0], A[1]))
        g.append('<text x="%.1f" y="%.1f" fill="#fff">driver comes from here</text>' % (tail[0] + 4, tail[1] - 4))
        o = px(s["old_rule"]["rev1_xz"])
        g.append('<circle cx="%.1f" cy="%.1f" r="5" fill="#999" stroke="#333"/><text x="%.1f" y="%.1f" fill="#ddd">old rule (advance, ~52 m early)</text>' % (o[0], o[1], o[0] + 7, o[1] + 4))
        b0 = px((cx, cz))
        for p in plates_of(s):
            r = p["right_xz"]
            p1 = px((cx + r[0] * PLATE_W / 2, cz + r[1] * PLATE_W / 2))
            p2 = px((cx - r[0] * PLATE_W / 2, cz - r[1] * PLATE_W / 2))
            g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#ffcc00" stroke-width="5"/>' % (p1[0], p1[1], p2[0], p2[1]))
            f = p["face_dir_xz"]
            fp = px((cx + f[0] * 6, cz + f[1] * 6))
            g.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#ffcc00" stroke-width="2"/>' % (b0[0], b0[1], fp[0], fp[1]))
        g.append('<circle cx="%.1f" cy="%.1f" r="4" fill="#111" stroke="#ffcc00" stroke-width="2"/>' % (b0[0], b0[1]))
        g.append('<text x="%d" y="%d" fill="#fff" font-weight="bold">%s  %s  R %.0f m  D %.0f deg  faces %s deg  arrow %s</text>'
                 % (ox + 6, oy + 14, s["id"], s["kind"], s["corner"]["R_apex_m"], s["corner"]["D_deg"],
                    "/".join("%.0f" % p["face_bearing_deg"] for p in plates_of(s)), "/".join(p["arrow"].upper() for p in plates_of(s))))
        g.append('<text x="%d" y="%d" fill="#ddd">ray %.0f m, curb clear %.2f m, lamp %.1f m, gate margin %.1f m</text>'
                 % (ox + 6, oy + 28, s["ray"]["len_m"], s["checks"].get("mesh_clear_m", s["checks"]["edge_clear_m"]), s["checks"]["lamp_m"], s["checks"]["gate_margin_m"]))
        if s.get("layout"):
            g.append('<text x="%d" y="%d" fill="#ffcc00">%s only: behind its sealing wall, %.2f m past the loop\'s lip (ships in its closure kn5)</text>'
                     % (ox + 6, oy + 42, s["layout"], (s.get("wall") or {}).get("behind_lip_m", 0.0)))
        g.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#fff" stroke-width="3"/><text x="%d" y="%d" fill="#fff">10 m</text>'
                 % (ox + 8, oy + W - 10, ox + 8 + int(10 * px_per_m), oy + W - 10, ox + 8, oy + W - 14))
        g.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#fff" stroke-width="2"/><text x="%d" y="%d" fill="#fff">N</text>'
                 % (ox + W - 16, oy + 40, ox + W - 16, oy + 12, ox + W - 20, oy + 52))
        g.append('</g></g>')
        parts.append("".join(g))
    parts.append("</svg>")
    Path(path).write_text("\n".join(parts), encoding="utf-8")


def write_outputs(proj, out, ctx):
    data = Path(proj) / "data"
    (data / "signs.local.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    write_svg(data / "signs_preview.svg", out, ctx)


def summary_line(out):
    kinds = {}
    for s in out["signs"]:
        for p in plates_of(s):
            kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1
    pairs = sum(1 for s in out["signs"] if s.get("pair"))
    md = direction_counts(out)
    main = ("; mainline plates %d fwd / %d rev" % (md["fwd"], md["rev"])) if md["rev"] else ""
    lay = [s["id"] for s in out["signs"] if s.get("layout")]
    layout = ("; %d layout plate%s (%s)" % (len(lay), "s" if len(lay) != 1 else "", ", ".join(lay))) if lay else ""
    north = sum(1 for s in out["signs"] if s["ribbon"] == NORTH_RIBBON)
    northtxt = ("; %d on the north ribbon" % north) if north else ""
    return "%d placed (%s%s%s%s%s), %d skipped" % (len(out["signs"]), ", ".join("%d %s" % (v, k) for k, v in sorted(kinds.items())) or "-",
                                                   ("; %d paired post%s" % (pairs, "s" if pairs != 1 else "")) if pairs else "", main, layout, northtxt, len(out["skipped"]))


def direction_counts(out):
    """mainline plates per approach (fwd = increasing vertex index, rev = the other way) and posts
    carrying a pair"""
    c = {"fwd": 0, "rev": 0, "paired_posts": sum(1 for s in out["signs"] if s.get("pair"))}
    for s in out["signs"]:
        if s["ribbon"] != "MAINLINE":
            continue
        for p in plates_of(s):
            c[p["direction"]] = c.get(p["direction"], 0) + 1
    return c


def main():
    argv = sys.argv[1:]
    if not argv:
        raise SystemExit(__doc__)
    proj = Path(argv[0])
    signs_path = argv[argv.index("--signs") + 1] if "--signs" in argv else None
    cfg, corners_cfg, p = load_overrides(proj, signs_path)
    if "--no-connectors" in argv:
        cfg["include_connectors"] = False
    if "--connectors" in argv:
        cfg["include_connectors"] = True
    out, ctx = place_all(proj, cfg, corners_cfg)
    write_outputs(proj, out, ctx)
    for s in out["signs"]:
        print("[signs] %-12s %s %-22s apex v%-5d R %5.1f D %7.1f  base (%8.1f, %8.1f) faces %s deg  ray %5.1f m  clear %.2f  lamp %4.1f  plant %4.1f  gate %+.1f  slid %+.2f%s"
              % (s["id"], s["kind"], s["ribbon"] + "/" + s["direction"], s["corner"]["apex_vertex"], s["corner"]["R_apex_m"], s["corner"]["D_deg"],
                 s["base_xz"][0], s["base_xz"][1], "/".join("%.1f" % p["face_bearing_deg"] for p in plates_of(s)), s["ray"]["len_m"], s["checks"]["edge_clear_m"],
                 s["checks"]["lamp_m"], s["checks"]["plant_m"], s["checks"]["gate_margin_m"], s["checks"]["slid_m"],
                 ("  WARN " + "; ".join(s["checks"]["warnings"])) if s["checks"]["warnings"] else ""))
    for s in out["skipped"]:
        print("[signs] skip %-12s %-22s apex v%-5d R %5.1f D %7.1f  %s" % (s["id"], s["ribbon"], s["apex_vertex"], s["R_apex_m"], s["D_deg"], "; ".join(s["reasons"])))
    print("[signs] %s; overrides %s; wrote %s" % (summary_line(out), p if p.exists() else "(none)", Path(proj) / "data" / "signs.local.json"))


if __name__ == "__main__":
    main()
