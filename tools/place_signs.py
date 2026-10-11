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
  mainline  driven direction only (increasing index = clockwise lap); connectors both approaches.
  slide     lamps (>= 3.0 m) and plants (>= 2.5 m) are cleared by sliding S along the local curb
            direction u (station sC), the smallest |slide| first, 0.25 m steps, capped at 1.0 m;
            beyond the cap the sign stays on the ray and the plant is excluded from TreeFX
            (lamps never move: a lamp inside 3.0 m is fatal). The slide is the ONLY lateral
            deviation from the ray; the plate stays square to it. The record carries u
            (curb_dir_xz) and slid_m so tools/author_signs_blend.py re-chooses the slide on the
            built mesh and tools/verify_signs.py tests the un-slid point against the ray.
  disc      drive_test's obstacle disc, min(lane_half, 6) + 0.3 m of EVERY centreline (its own
            street included: 4.9 m on a 10 m street), must clear every SIGN* vertex: the plate's
            footprint base +- 0.61 m along the right vector. Fatal on every ribbon.
  pair      a two-way connector corner whose -fwd and -rev points land < 2.0 m apart becomes ONE
            post at the mean base carrying both plates (W1-6R + W1-6L), each still facing its own
            approach (merge_pairs; re-run after the mesh march, which is where DCL-2's pair met).
  expect    signs.json expect_arrow names the arrow the corner must get; a computed arrow that
            differs is a skip with a logged reason, never a silent relocation (and a ship FAIL in
            tools/verify_signs.py check (j)).

Overrides: tracks/<slug>/signs.json {defaults{...}, corners{<id>: {ribbon, vertex, skip, reason,
slide_along_curb_m, base_xz, face_bearing_deg, plate, arrow, expect_arrow, height_m, om1_3,
second_arrow, force}}}. defaults.kappa_window_m / hysteresis_stations drive the detector (12 m /
6 stations). An entry whose vertex has no detected corner within 30 m is refused with a WARN
(stale after a centreline regen).

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
# --- the old rule, for the comparison picture ---------------------------------------------------
OLD_REV1_LEAD_M = 52.0          # kerbs lead 28 m + 8 stations ~ 24 m before the first curved vertex
OLD_REV1_LATERAL = 2.2
OLD_REV2_LATERAL = 2.8

DEFAULTS = {
    "r_sign_max_m": R_SIGN_MAX_M, "defl_min_deg": DEFL_MIN_DEG, "hairpin_deg": HAIRPIN_DEG,
    "lateral_offset_m": CURB_FACE_W + SIDEWALK_W["MAINLINE"] - BACK_OF_WALK_SETBACK,
    "lateral_offset_connector_m": CURB_FACE_W + SIDEWALK_W["CONNECTOR"] - BACK_OF_WALK_SETBACK,
    "height_m": HEIGHT_M, "om1_3": True, "skew_deg": 0.0, "include_connectors": True,
    "both_directions_mainline": False, "lamp_clear_m": LAMP_CLEAR_M, "plant_clear_m": PLANT_CLEAR_M,
    "kappa_window_m": 2 * KAPPA_HALF_WIN, "hysteresis_stations": HYSTERESIS,
}
RIBBON_PREFIX = {"MAINLINE": "M", "del_cerro_blvd#0": "DC0", "del_cerro_blvd#1": "DC1",
                 "del_cerro_blvd_loop": "DCL", "medium#2+0#0#0": "MED"}


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


class PavementField:
    """signed distance to the nearest pavement edge over every ribbon (negative = on pavement)"""

    def __init__(self, ribbons, cell=60.0):
        self.cell = cell
        self.segs = []
        self.cells = {}
        for rb in ribbons:
            if rb.reverse:
                continue
            P, W = rb.raw, rb.raw_w
            idx = list(range(len(P))) + ([0] if rb.closed else [])
            for a, b in zip(idx[:-1], idx[1:]):
                k = len(self.segs)
                self.segs.append((rb.name, P[a], P[b], W[a] / 2, W[b] / 2))
                for (x, _, z) in (P[a], P[b]):
                    self.cells.setdefault((int(x // cell), int(z // cell)), set()).add(k)

    def query(self, x, z, exclude=None):
        best = (float("inf"), None, 0.0, 0.0)   # (signed edge distance, ribbon, half-width, road y)
        cx, cz = int(x // self.cell), int(z // self.cell)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for k in self.cells.get((cx + dx, cz + dz), ()):
                    name, a, b, ha, hb = self.segs[k]
                    if name == exclude:
                        continue
                    ddx, ddz = b[0] - a[0], b[2] - a[2]
                    L2 = ddx * ddx + ddz * ddz
                    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - a[0]) * ddx + (z - a[2]) * ddz) / L2))
                    d = math.hypot(x - (a[0] + t * ddx), z - (a[2] + t * ddz))
                    hw = ha * (1 - t) + hb * t
                    if d - hw < best[0]:
                        best = (d - hw, name, hw, a[1] + (b[1] - a[1]) * t)
        return best

    def gate_margin(self, x, z):
        """distance beyond drive_test's obstacle disc min(max(w/2-0.4,0.8),6)+0.3 of EVERY ribbon"""
        worst = float("inf")
        cx, cz = int(x // self.cell), int(z // self.cell)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for k in self.cells.get((cx + dx, cz + dz), ()):
                    name, a, b, ha, hb = self.segs[k]
                    ddx, ddz = b[0] - a[0], b[2] - a[2]
                    L2 = ddx * ddx + ddz * ddz
                    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - a[0]) * ddx + (z - a[2]) * ddz) / L2))
                    d = math.hypot(x - (a[0] + t * ddx), z - (a[2] + t * ddz))
                    w = 2 * (ha * (1 - t) + hb * t)
                    worst = min(worst, d - (min(max(w / 2 - 0.4, 0.8), 6.0) + 0.3))
        return worst

    def footprint_margin(self, base, rights):
        """gate_margin over the sign's footprint: the base and both plate ends (+-HALF_PLATE along
        every plate's right vector) — no SIGN* vertex may stand inside drive_test's disc"""
        pts = [tuple(base)]
        for r in rights:
            pts.append((base[0] + r[0] * HALF_PLATE, base[1] + r[1] * HALF_PLATE))
            pts.append((base[0] - r[0] * HALF_PLATE, base[1] - r[1] * HALF_PLATE))
        return min(self.gate_margin(p[0], p[1]) for p in pts)


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
        mp = data / "mouths.json"
        mouths = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {"mouths": []}
        mouths = mouths["mouths"] if isinstance(mouths, dict) else mouths
        self.mouth_pts = [((m["cut_xyz"][0], m["cut_xyz"][2]), f"mouth {m.get('connector')}@{m.get('host')}:{m.get('host_vertex')}")
                          for m in mouths if m.get("cut_xyz")]
        for rb in self.ribbons[1:]:
            if not rb.closed:
                self.mouth_pts.append((rb.xz(0), f"{rb.name} start"))
                self.mouth_pts.append((rb.xz(rb.n - 1), f"{rb.name} end"))
        mb = data / "median_bands.json"
        isl = json.loads(mb.read_text(encoding="utf-8")).get("island_w_by_vertex", []) if mb.exists() else []
        self.island = {int(k): v for k, v in isl.items()} if isinstance(isl, dict) else {i: v for i, v in enumerate(isl) if v}
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
        self.spawn_pts = []
        for dp in (data / "dummies.json", AIROSO / "tracks" / track_dir_name(self.proj) / "data" / "dummies.json"):
            if dp.exists():
                try:
                    for k, v in json.loads(dp.read_text(encoding="utf-8")).items():
                        if k.startswith(("AC_START", "AC_HOTLAP", "AC_TIME")):
                            self.spawn_pts.append(((v[0], v[2]), f"{k}@{dp.parent.parent.name}"))
                except Exception:
                    pass

    def nearest_mouth(self, q):
        return min(((math.hypot(q[0] - p[0], q[1] - p[1]), lab) for p, lab in self.mouth_pts), default=(float("inf"), "-"))

    def nearest_lamp(self, q):
        return min((math.hypot(q[0] - b[0], q[1] - b[1]) for b in self.lamp_bases), default=float("inf"))

    def nearest_plant(self, q):
        return min(((math.hypot(q[0] - p[0], q[1] - p[1]), p[2], p[3]) for p in self.plants), default=(float("inf"), "-", -1))

    def nearest_spawn(self, q):
        return min(((math.hypot(q[0] - p[0], q[1] - p[1]), lab) for p, lab in self.spawn_pts), default=(float("inf"), "-"))


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


def load_overrides(proj, signs_path=None):
    p = Path(signs_path) if signs_path else AIROSO / "tracks" / track_dir_name(proj) / "signs.json"
    cfg = dict(DEFAULTS)
    corners = {}
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        cfg.update({k: v for k, v in (d.get("defaults") or {}).items() if not k.startswith("_")})
        corners = {k: v for k, v in (d.get("corners") or {}).items() if not k.startswith("_")}
    return cfg, corners, p


# ----------------------------------------------------------------------------------------------
def march(ctx, rb, A, t, d_clear):
    """the failed-to-turn ray: returns dict(C, s_C, exit_ribbon, hw_at_exit, t_end, S, s_S, pushed,
    lateral) or None when the ray never leaves pavement within RAY_MAX_M"""
    s = 0.0
    C = None
    res = {}
    while s <= RAY_MAX_M + RAY_EXTRA_CAP_M + 1:
        q = (A[0] + t[0] * s, A[1] + t[1] * s)
        d, name, hw, _ = ctx.field.query(q[0], q[1])
        if C is None:
            if d > 0:
                C = q
                res.update(C=q, s_C=s, exit_ribbon=name, hw_at_exit=hw)
                # T-end: back on ANOTHER ribbon within 3 m of C
                t_end = False
                for k in range(1, int(T_END_PROBE_M / RAY_STEP) + 1):
                    q2 = (q[0] + t[0] * k * RAY_STEP, q[1] + t[1] * k * RAY_STEP)
                    d2, name2, _, _ = ctx.field.query(q2[0], q2[1])
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
                    if ctx.field.query(A[0] + t[0] * mid, A[1] + t[1] * mid)[0] >= d_clear:
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


def choose_slide(ctx, cfg, S, u, d_clear, clear_fn, rights=()):
    """clear lamps (>= lamp_clear_m) and plants (>= plant_clear_m) by sliding S along the curb
    direction u, smallest |slide| first, never beyond SLIDE_MAX_M; a candidate must also keep the
    edge clearance clear_fn(x, z) >= d_clear - 0.05 and the disc footprint margin >= 0. When no
    candidate clears: stay on the ray, flag a lamp (fatal), exclude the plant (TreeFX drops it).
    -> (slid_m, S, lamp_m, plant(dist, zone, idx), exclude_plant | None, reasons[])"""
    for sl in slide_candidates():
        q = (S[0] + u[0] * sl, S[1] + u[1] * sl)
        if clear_fn(q[0], q[1]) < d_clear - 0.05:
            continue
        if rights and ctx.field.footprint_margin(q, rights) < 0:
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


def place_corner(ctx, rb, corner, cid, ov, cfg, second=False):
    """one approach of one corner -> (record | None, reasons[])"""
    n = rb.n
    sg = corner["sign"]
    reasons = []
    D = corner["D_deg"]
    pc = corner["PC"] if not second else corner["PC2"]
    apex = corner["apex"]
    thr = 1.0 / R_STRAIGHT_M
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
    island = ctx.island.get(rb.vertex(pc), 0.0) if rb.name == "MAINLINE" else 0.0
    lane_off = island / 2 + (w_app - island) / 4
    P_pc = rb.xz(pc)
    A = (P_pc[0] + nR[0] * lane_off, P_pc[1] + nR[1] * lane_off)
    d_clear = cfg["lateral_offset_m"] if rb.name == "MAINLINE" else cfg["lateral_offset_connector_m"]
    # 3) the ray
    m = march(ctx, rb, A, t, d_clear)
    if m is None:
        return None, ["ray never leaves pavement within %.0f m (through leg / junction)" % RAY_MAX_M]
    if m["s_C"] < RAY_MIN_M or m["s_C"] > RAY_MAX_M:
        reasons.append("ray exits pavement at %.1f m (want %.0f-%.0f)" % (m["s_C"], RAY_MIN_M, RAY_MAX_M))
    if m.get("t_end"):
        reasons.append("T-end: ray re-enters %s within 3 m of the curb (W1-7 candidate, second pass)" % m["t_end_ribbon"])
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
    if not (0 <= rel_pc <= arc + RAY_PAST_PT_M):
        reasons.append("ray foot at station PC%+d is outside [PC, PT+%d] (a curve, not a turn)" % (rel_pc, RAY_PAST_PT_M))
    # 4) sign point
    if "S" not in m:
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
        reasons.append("expect_arrow=%s but the rule computed %s (D %.1f deg) — not relocated, see signs.json" % (expect, arrow, D))
    # 7) clearances: lamps never move; plants are excluded from TreeFX; the sign may slide along
    #    the curb (u at sC), <= SLIDE_MAX_M, the smallest move first — the only lateral deviation
    u = unit((rb.xz(sC + 1)[0] - rb.xz(sC - 1)[0], rb.xz(sC + 1)[1] - rb.xz(sC - 1)[1]))
    slid, S, lamp, plant, excl_plant, slide_reasons = choose_slide(
        ctx, cfg, S, u, d_clear, lambda x, z: ctx.field.query(x, z)[0], rights=(nR,))
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
    # 9) the rest of the checks
    y_road = rb.y(sC)
    gate_margin = ctx.field.footprint_margin(S, (nR,))
    edge_clear = ctx.field.query(S[0], S[1])[0]
    spawn = ctx.nearest_spawn(S)
    warns = []
    if abs(pca_vs_chord) > 5:
        warns.append("approach heading: 10 m chord %.1f deg vs PCA fit %.1f deg (differ by %.1f deg; the chord is used)"
                     % (bearing(t[0], t[1]), bearing(math.cos(th_pca), math.sin(th_pca)), abs(pca_vs_chord)))
    if spawn[0] < SPAWN_CLEAR_M:
        warns.append("%.0f m from %s (< %.0f m spawn/gate exclusion, placed anyway)" % (spawn[0], spawn[1], SPAWN_CLEAR_M))
    if gate_margin < 0:     # drive_test's disc on EVERY centreline, the sign's own street included
        reasons.append("plate footprint inside drive_test's obstacle disc by %.2f m" % -gate_margin)
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
        "id": cid if not second else cid + "-2",
        "kind": "W1-6R" if arrow == "right" else "W1-6L",
        "plate": "W1-6",
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
        "skew_deg": cfg.get("skew_deg", 0.0),
        "checks": {"outside_cross": round(outside_cross, 2), "edge_clear_m": round(edge_clear, 2),
                   "lamp_m": round(lamp, 2), "plant_m": round(plant[0], 2), "plant_zone": plant[1],
                   "pushed_m": m["pushed_m"], "slid_m": round(slid, 2), "lateral_step_m": m.get("lateral_m", 0.0),
                   "gate_margin_m": round(gate_margin, 2), "mouth_m": round(ctx.nearest_mouth(S)[0], 1),
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


PLATE_KEYS = ("id", "kind", "direction", "corner", "approach", "ray", "face_dir_xz", "face_bearing_deg",
              "yaw_deg", "right_xz", "arrow", "expect_arrow", "old_rule", "where", "base_xz", "curb_dir_xz")


def merge_pairs(signs, thr=PAIR_MERGE_M, log=None):
    """a two-way connector corner whose -fwd and -rev posts stand < thr apart becomes ONE record:
    one post at the mean base, both plates on it (each keeps its own approach, facing, arrow and
    checks under "plates"); the top-level facing/arrow/ray are the -fwd plate's so every reader
    that knows one plate still draws something sensible. Idempotent; stable order."""
    by_corner = {}
    for s in signs:
        if "plates" in s or not s["id"].endswith(("-fwd", "-rev")):
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
        for k in ("edge_clear_m", "mesh_clear_m", "lamp_m", "plant_m", "gate_margin_m", "mouth_m", "spawn_m"):
            if k in ca and k in cb:
                rec["checks"][k] = min(ca[k], cb[k])
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
    fwd_ids = {}
    fwd_rbs = {r.name: r for r in ctx.ribbons}
    for rb in ribbons:
        corners = detect_corners(rb, ctx.hyst)
        if not rb.reverse:
            corners.sort(key=lambda c: c["apex"])
            fwd_ids[rb.name] = [(c["apex"], corner_id(rb, k + 1)) for k, c in enumerate(corners)]
        named = assign_overrides(rb, fwd_rbs[rb.name], corners, corners_cfg)
        for ci, c in enumerate(corners):
            # id: forward numbering in station order; a reversed ribbon reuses the forward id
            apex_fwd = c["apex"] if not rb.reverse else (rb.n - 1 - c["apex"] if not rb.closed else (-c["apex"]) % rb.n)
            cid = min(fwd_ids[rb.name], key=lambda e: abs(e[0] - apex_fwd))[1]
            ov_id, ov = named.get(ci, (None, {}))
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
                reasons.append("signs.json skip: %s" % ov.get("reason", "(no reason given)"))
            if not ov.get("force"):
                if c["R_apex_m"] > cfg["r_sign_max_m"]:
                    reasons.append("R_apex %.1f > %.0f m" % (c["R_apex_m"], cfg["r_sign_max_m"]))
                if abs(c["D_deg"]) < cfg["defl_min_deg"]:
                    reasons.append("|D| %.1f < %.0f deg" % (abs(c["D_deg"]), cfg["defl_min_deg"]))
            dm = ctx.nearest_mouth(rb.xz(c["apex"]))
            if dm[0] < MOUTH_CLEAR_M and not ov.get("force"):
                reasons.append("apex %.0f m from %s (< %.0f m: mouth-flare geometry)" % (dm[0], dm[1], MOUTH_CLEAR_M))
            if reasons:
                skipped.append(dict(base, reasons=reasons))
                continue
            rec, reasons = place_corner(ctx, rb, c, cid_dir, ov, cfg)
            if reasons and not ov.get("force"):
                skipped.append(dict(base, reasons=reasons, would_be=rec and rec["base_xz"]))
                continue
            if reasons:
                rec["checks"]["warnings"] += ["FORCED past: " + r for r in reasons]
            signs.append(rec)
            if rec["exclude_plant"]:
                excl.append(dict(rec["exclude_plant"], sign=rec["id"]))
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
    out = {
        "frame": "engine ENU local metres: x = East, y = up, z = North (data/centerline.local.json); Blender = (x, z, y)",
        "rule": "W1-6 at the corner, outside of the bend, in line with and facing the approach (tools/place_signs.py)",
        "defaults": cfg,
        "signs": signs,
        "skipped": skipped,
        "exclude_plants": excl,
        "stale_overrides": stale,
        "pairs": [s["id"] for s in signs if s.get("pair")],
        "counts": {"placed": len(signs), "plates": sum(len(plates_of(s)) for s in signs), "skipped": len(skipped)},
    }
    return out, ctx


# ----------------------------------------------------------------------------------------------
def plate_polygons(out, sx, sz, f, r, h0, arrow, om, y_base):
    """one plate (+ border, arrow, optional OM1-3 diamond) on the post at (sx, sz), facing f,
    bottom edge at h0; returns the plate top height"""
    h1 = h0 + PLATE_H
    mirror = -1.0 if arrow == "left" else 1.0

    def P(u, v, w):
        return (sx + r[0] * u + f[0] * w, v, sz + r[1] * u + f[1] * w)

    nf = (f[0], 0.0, f[1])
    nb = (-f[0], 0.0, -f[1])
    wf, wb = PLATE_FRONT_OFF, PLATE_FRONT_OFF - PLATE_BACK_GAP
    hw = PLATE_W / 2
    out["SIGNPLATE"].append(([P(-hw, h0, wf), P(hw, h0, wf), P(hw, h1, wf), P(-hw, h1, wf)], nf))
    out["SIGNPOST"].append(([P(-hw, h0, wb), P(hw, h0, wb), P(hw, h1, wb), P(-hw, h1, wb)], nb))
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


def sign_polygons(rec, y_base):
    """the sign as engine-frame polygons: {kind: [(verts[(x, y, z)...], normal(x, y, z)), ...]}.
    Winding is NOT meaningful here — the emitter orders each polygon to its normal. A paired
    record (merge_pairs) gets ONE post and both plates: back-to-back at the same height when
    their facings are >= 90 deg apart, else the second plate stacks above the first (two plates
    30 deg apart at one height would cut through each other) and carries no diamond."""
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
        h_top = max(h_top, plate_polygons(out, sx, sz, f, r, hk, p["arrow"], om, y_base))
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
        for rb in ctx.ribbons:
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
    return "%d placed (%s%s), %d skipped" % (len(out["signs"]), ", ".join("%d %s" % (v, k) for k, v in sorted(kinds.items())) or "-",
                                             ("; %d paired post%s" % (pairs, "s" if pairs != 1 else "")) if pairs else "", len(out["skipped"]))


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
