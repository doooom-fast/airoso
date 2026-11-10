"""Diagnostic (not a gate): every side-street MOUTH surveyed on the BUILT road, beyond verify_mouths (ledger 0086).

    python tools/mouth_survey.py <project-dir> [--obj data/track.obj] [--json data/mouth_survey.json] [--rog]

verify_mouths judges four lines at a mouth (the mouth line, the host lane, the notch inside the connector's span, the
approach grade) and calls every Sand Creek mouth flush. Kevin, 2026-11-07, on Sand Creek LM 0.2.5: "Doesn't connect,
floats". This measures what verify_mouths does not look at, on the gate OBJ of the shipped kn5 (L5: the triangles that
ship; mouths.json / connectors.local.json only say where to look). Per mouth, in the host frame (s along the host, b out
from the host's pavement edge on the connector's side) and the connector frame (u out from the host edge along the
piece, lateral l):

  CORNERS    the two corners beside the connector, s from the connector's edge outward 0..CORNER_A_M along the host, at
             b in CORNER_B_M past the host edge: the top surface there (any class) against the host's road edge at the
             same s. A flush corner reads ~0 at b <= 0.3 (the edge strip holds the lane edge's height for its first
             0.30 m: route.edge). "bare" = the length of host edge, at b = 0.15, whose top is 1GRASS more than LIP_M
             under the road edge: the road slab's own edge stands exposed over the ground there. "lip" = the worst drop.
  TURNS      the inside wheel of a car turning in or out round each corner: an arc of radius TURN_R_M tangent to both
             roads' wheel lines (TURN_D_M in from each edge); a square corner is left by any r > 3.4 d. The drop below
             the line between the two roads' heights, the length off 1ROAD, the worst rise over 0.10 m.
  TEETH      along the connector's edge strips, TEETH_U_M from the host: the share of samples where the ground stands
             over the strip (1GRASS on top, the 1KERB strip under it within 0.3 m): the "grass teeth" through the skirt.
  CONN EDGES the same along the connector's two edges, u 0..CONN_U_M out from the host edge.
  STRIP GAP  the host's edge strip (1KERB) along b = 0.15: the run of host it is missing around the mouth, against the
             run the connector's pavement covers (the two edge crossings): plan offset = gap centre - pavement centre,
             overhang = gap width - pavement width (> 0: bare host edge beyond the connector's corners).
  WHEELS     the connector's wheel paths (l = 0, +-(w/2 - WHEEL_IN_M), +-(w/2 - 2.5)) from u = -WHEEL_BACK_M (on the
             host) to +WHEEL_OUT_M, every 0.05 m on the topmost drivable sheet (1ROAD / 1KERB) near the running height:
             the largest rise over 0.10 m beyond the grade of the metre before it (0050's FINE step), both directions,
             and holes (no drivable sheet).
  DAYLIGHT   on the overlap (u in [-0.4, 0]) across the span: the connector's sheet against the host's below it (a
             positive number is the connector's cut end standing over the host deck: a lip facing the host); no sheet
             at all = daylight.
  GRASS      1GRASS at or above the connector's road over its deck (|l| < w/2 - 0.1, u 0..WHEEL_OUT_M), a 0.25 m grid.
  MARKINGS   white MARKINGS on the host's mouth-side edge line's own band (b -0.58..-0.52; the line is painted at
             -0.61..-0.49) across the span (an edge line painted across the opening), and MARKINGS / YLINE on the host
             past the overlap along the connector's centre (a centre line run on).

--rog also locates scripts/ac/kn5_ground_check's road_over_ground samples (its exact sampler: every 7th 1ROAD vertex of
the road kn5, grass/kerb/runoff triangle beneath, its span / structure / deck-over-deck exemptions) and names the
street, mouth and offset of each one over ROAD_GAP_M; the gate JSON holds counts only.

Thresholds here are report bands, not gates: LIP_M 0.05 is kn5_ground_check's ROAD_GAP_M (measured: the barycentric
sampling ceiling); the rest are sampling geometry.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_mouths as vm  # noqa: E402

CORNER_A_M = 6.0
CORNER_B_M = (0.05, 0.15, 0.3, 0.6, 1.0, 1.5)
CONN_U_M = 8.0
LIP_M = 0.05
WHEEL_IN_M = 0.9
WHEEL_BACK_M = 5.0
WHEEL_OUT_M = 12.0
STEP_M = 0.05
FINE_M = 0.10
TURN_R_M = (6.0, 9.0, 12.0)    # inside-wheel turning radii [sampling choice: a tight, a normal and a wide turn]
TURN_D_M = 1.0                 # the inside wheel's line, in from each pavement edge
TEETH_U_M = 20.0
TEETH_B_M = (0.45, 0.75, 1.05, 1.35, 1.65)   # across route.edge's graded part (0.30 .. 1.80 m past the lane edge)
CLASSES = (("ROAD", "1ROAD"), ("KERB", "1KERB"), ("GRASS", "1GRASS"), ("MARK", "MARKINGS"), ("YLINE", "YLINE"))
CELL = 2.0
KEEP_M = 40.0


def load(path: Path, centres, keep=KEEP_M):
    hc = defaultdict(list)
    for cx, cz in centres:
        hc[(int(cx // keep), int(cz // keep))].append((cx, cz))
    k2 = keep * keep

    def near(p):
        i, j = int(p[0] // keep), int(p[2] // keep)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for cx, cz in hc.get((i + di, j + dj), ()):
                    if (p[0] - cx) ** 2 + (p[2] - cz) ** 2 <= k2:
                        return True
        return False

    V = []
    tris = {c: [] for c, _ in CLASSES}
    cur = None
    with open(path, "r", encoding="ascii", errors="replace") as f:
        for line in f:
            c2 = line[:2]
            if c2 == "v ":
                q = line.split()
                V.append((float(q[1]), float(q[2]), float(q[3])))
            elif c2 == "o " or c2 == "g ":
                name = line[2:].strip().upper()
                cur = next((c for c, pre in CLASSES if name.startswith(pre)), None)
            elif c2 == "f " and cur is not None:
                idx = [int(t.split("/")[0]) for t in line.split()[1:]]
                pts = [V[i - 1] for i in idx]
                if any(near(p) for p in pts):
                    for k in range(1, len(pts) - 1):
                        tris[cur].append((pts[0], pts[k], pts[k + 1]))
    return tris


class Field:
    def __init__(self, tris):
        self.cells = defaultdict(list)
        for cls, ts in tris.items():
            for t in ts:
                xs = [p[0] for p in t]
                zs = [p[2] for p in t]
                for ix in range(int(math.floor(min(xs) / CELL)), int(math.floor(max(xs) / CELL)) + 1):
                    for iz in range(int(math.floor(min(zs) / CELL)), int(math.floor(max(zs) / CELL)) + 1):
                        self.cells[(ix, iz)].append((cls, t))

    def sheets(self, x, z):
        out = []
        for cls, (a, b, c) in self.cells.get((int(math.floor(x / CELL)), int(math.floor(z / CELL))), ()):
            d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(d) < 1e-12:
                continue
            l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
            l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
            l3 = 1.0 - l1 - l2
            if min(l1, l2, l3) >= -1e-7:
                out.append((l1 * a[1] + l2 * b[1] + l3 * c[1], cls))
        return out

    def top(self, x, z, near_y=None, win=1.0, classes=("ROAD", "KERB", "GRASS")):
        """the highest sheet of `classes` at (x, z) (within `win` of near_y when given): (y, class) or None"""
        best = None
        for y, cls in self.sheets(x, z):
            if cls not in classes or (near_y is not None and abs(y - near_y) > win):
                continue
            if best is None or y > best[0]:
                best = (y, cls)
        return best


def _frames(mo, conns, local):
    piece, end = vm._find_piece(mo, conns)
    if mo["host"] == "MAINLINE":
        hp = vm.Path2(local["points_xyz_m"], local["widths_m"])
    else:
        hc = next(c for c in conns if c["name"] == mo["host"])
        hp = vm.Path2(hc["points_xyz_m"], hc["widths_m"])
    pp = vm.Path2(vm.smooth_xz([tuple(q) for q in piece["points_xyz_m"]]), piece["widths_m"])
    return hp, pp, end


def survey_mouth(mo, F, hp, pp, end):
    cx, cy, cz = mo["cut_xyz"]
    _d, c, _lat = hp.project(cx, cz)
    _p, (htx, htz), (hnx, hnz), hwid = hp.frame(c)
    half = hwid / 2.0
    plen = pp.s[-1]
    s_dir = (lambda u: u) if end == "start" else (lambda u: plen - u)
    q10 = pp.point(s_dir(min(10.0, plen)), 0.0)
    side = 1 if hp.project(q10[0], q10[1])[2] >= 0 else -1
    wc = pp.frame(s_dir(0.0))[3]
    sgn_t = 1.0 if end == "start" else -1.0      # the piece's own tangent points away from the host at a start end

    def hpt(s, b):
        """host frame: arc s, b metres past the host's pavement edge on the connector's side"""
        (x, z), _t, (nx, nz), w = hp.frame(s)
        lat = side * (w / 2.0 + b)
        return x + nx * lat, z + nz * lat

    def road_edge_y(s, ref):
        x, z = hpt(s, -0.3)
        t = F.top(x, z, ref, 1.0, ("ROAD",))
        return t[0] if t else None

    # the host arcs where the connector's two edges cross the host's edge line (b = 0)
    cross = {}
    q0_ = pp.point(s_dir(0.0), 0.0)
    q1_ = pp.point(s_dir(min(6.0, plen)), 0.0)
    ax_, az_ = q1_[0] - q0_[0], q1_[1] - q0_[1]
    La_ = math.hypot(ax_, az_) or 1.0
    for e in (1.0, -1.0):
        prev = None
        for k in range(-int(15.0 / 0.05), int(25.0 / 0.05)):
            u = 0.05 * k
            if u < 0:       # past the cut, straight on into the host (verify_mouths.span_at)
                x0, z0 = pp.point(s_dir(0.0), e * wc / 2.0)
                x, z = x0 + ax_ / La_ * u, z0 + az_ / La_ * u
            else:
                uu = s_dir(min(u, plen))
                x, z = pp.point(uu, e * pp.frame(uu)[3] / 2.0)
            _dd, sh, lat = hp.project(x, z)
            g = side * lat - hp.frame(sh)[3] / 2.0
            if prev is not None and (prev[0] <= 0.0) != (g <= 0.0):
                t = prev[0] / (prev[0] - g)
                cross[e] = prev[1] + (sh - prev[1]) * t
                break
            prev = (g, sh)
    if len(cross) < 2:
        return {"piece": mo["piece"], "end": end, "host": mo["host"], "error": "connector edges never cross the host edge"}
    s_lo, s_hi = min(cross.values()), max(cross.values())
    # which connector lateral sign sits at the low-s corner
    e_lo = min(cross, key=lambda e: cross[e])

    def in_corner(x, z, a_max=CORNER_A_M, b_lo=-1.0, b_hi=2.5):
        """the corner (lo / hi) whose box holds (x, z), or None"""
        dd, sq, lq = hp.project(x, z)
        b = side * lq - hp.frame(sq)[3] / 2.0
        if not (b_lo <= b <= b_hi):
            return None
        if s_lo - a_max <= sq <= s_lo:
            return "lo", round(s_lo - sq, 2), round(b, 2)
        if s_hi <= sq <= s_hi + a_max:
            return "hi", round(sq - s_hi, 2), round(b, 2)
        return None

    out = {"piece": mo["piece"], "end": end, "host": mo["host"], "side": side, "angle_deg": mo.get("angle_deg"),
           "_in_corner": in_corner,
           "cut_xyz": [round(cx, 2), round(cy, 3), round(cz, 2)], "host_half_m": round(half, 2),
           "conn_width_m": round(wc, 2), "pave_span_m": [round(s_lo - c, 2), round(s_hi - c, 2)]}

    # STRIP GAP along b = 0.15: where the host's edge strip (1KERB) is missing around the mouth
    def strip_at(s):
        x, z = hpt(s, 0.15)
        t = F.top(x, z, cy, 1.0, ("KERB",))
        return t is not None
    g_lo = g_hi = None
    s = s_lo
    while s > s_lo - 15.0:
        if strip_at(s):
            g_lo = s
            break
        s -= 0.05
    s = s_hi
    while s < s_hi + 15.0:
        if strip_at(s):
            g_hi = s
            break
        s += 0.05
    if g_lo is not None and g_hi is not None:
        out["strip_gap"] = {"gap_m": [round(g_lo - c, 2), round(g_hi - c, 2)],
                            "bare_before_m": round(s_lo - g_lo, 2), "bare_after_m": round(g_hi - s_hi, 2),
                            "plan_offset_m": round((g_lo + g_hi) / 2.0 - (s_lo + s_hi) / 2.0, 2),
                            "overhang_m": round((g_hi - g_lo) - (s_hi - s_lo), 2)}

    # CORNERS
    corners = {}
    for name, s0, dirn in (("lo", s_lo, -1.0), ("hi", s_hi, 1.0)):
        rows = {}
        bare = 0.0
        lip = 0.0
        lip_at = None
        jumps = 0.0
        prev_top = None
        for k in range(0, int(CORNER_A_M / 0.1) + 1):
            a = 0.1 * k
            s = s0 + dirn * a
            ref = road_edge_y(s, cy)
            if ref is None:
                continue
            for b in CORNER_B_M:
                x, z = hpt(s, b)
                t = F.top(x, z, ref, 1.0)
                d = None if t is None else round(ref - t[0], 3)
                rows.setdefault(f"{b:.2f}", []).append((round(a, 1), d, None if t is None else t[1]))
                if b <= 0.15 and d is not None and d > lip:
                    lip, lip_at = d, (round(a, 1), b, t[1])
                if b == 0.15:
                    if t is not None and t[1] == "GRASS" and d is not None and d > LIP_M:
                        bare += 0.1
                    if prev_top is not None and t is not None:
                        jumps = max(jumps, abs(t[0] - prev_top))
                    prev_top = None if t is None else t[0]
        corners[name] = {"bare_m": round(bare, 1), "lip_m": round(lip, 3), "lip_at": lip_at,
                         "max_jump_along_m": round(jumps, 3),
                         "profile_b015": [r for r in rows.get("0.15", []) if r[0] in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0,
                                                                                      3.5, 4.0, 5.0, 6.0)],
                         "drop_by_b_at_a1": {b: next((r[1] for r in rows[b] if r[0] == 1.0), None) for b in rows}}
    out["corners"] = corners

    # TURNS: the inside wheel of a car turning between the host and the connector round each corner, an arc of radius r
    # tangent to the host's wheel line and the connector's (both TURN_D_M in from their pavement edges), in the corner's
    # own plan frame (K = the connector's edge on the host's edge; h along the host away from the mouth, N out of the
    # host). The arc's nearest point to K is 0.293 r - d past both edges: any r > 3.4 d leaves the square corner's
    # pavement. Topmost sheet (any class) along it every 0.05 m against the straight line between the two roads' heights
    # at its ends: the drop a wheel takes, the length off 1ROAD, the worst rise over 0.10 m.
    turns = {}
    for name, s0, dirn in (("lo", s_lo, -1.0), ("hi", s_hi, 1.0)):
        (kx0, kz0), (tx_, tz_), (nx_, nz_), w_ = hp.frame(s0)
        Kx, Kz = kx0 + nx_ * side * w_ / 2.0, kz0 + nz_ * side * w_ / 2.0
        hx, hz = tx_ * dirn, tz_ * dirn
        Nx, Nz = nx_ * side, nz_ * side
        res = {}
        for r in TURN_R_M:
            d = TURN_D_M
            pts = []
            n = int(math.pi / 2.0 * r / STEP_M)
            for k in range(n + 1):
                th = math.radians(-90.0 - 90.0 * k / n)
                a = (r - d) + r * math.cos(th)
                b = (r - d) + r * math.sin(th)
                pts.append((Kx + hx * a + Nx * b, Kz + hz * a + Nz * b, a, b))
            def _road_near(x, z):
                rs = [y for y, cls in F.sheets(x, z) if cls == "ROAD" and abs(y - cy) < 3.0]
                return (min(rs, key=lambda y: abs(y - cy)), "ROAD") if rs else None
            y0 = _road_near(pts[0][0], pts[0][1])        # graded hosts (Princess View 9.6 %) stand > 1 m off the cut
            y1 = _road_near(pts[-1][0], pts[-1][1])
            if y0 is None or y1 is None:
                continue
            drop = 0.0
            off = 0
            rise = 0.0
            prev = None
            for k, (x, z, a, b) in enumerate(pts):
                ref = y0[0] + (y1[0] - y0[0]) * k / n
                t = F.top(x, z, ref, 0.6)
                if t is None:
                    continue
                if t[1] != "ROAD":
                    off += 1
                drop = max(drop, ref - t[0])
                if prev is not None and k - prev[0] == 2:
                    rise = max(rise, abs(t[0] - prev[1]))
                if k % 2 == 0:
                    prev = (k, t[0])
            res[f"r{r:g}"] = {"cut_past_edges_m": round(0.293 * r - d, 2), "max_drop_m": round(drop, 3),
                              "off_road_m": round(off * STEP_M * 1.0, 2), "max_rise_0p1_m": round(rise, 3)}
        turns[name] = res
    out["turns"] = turns

    # CONNECTOR EDGES: u from the host edge outward along each connector edge, b past it
    cedges = {}
    for e in (1.0, -1.0):
        worst = 0.0
        w_at = None
        bare = 0.0
        for k in range(0, int(CONN_U_M / 0.1) + 1):
            u = 0.1 * k
            uu = s_dir(min(u, plen))
            (x0, z0), _t, (nx, nz), w = pp.frame(uu)
            ex, ez = x0 + nx * e * (w / 2.0 - 0.3), z0 + nz * e * (w / 2.0 - 0.3)
            r = F.top(ex, ez, cy, 1.5, ("ROAD",))
            if r is None:
                continue
            for b in (0.05, 0.15):
                x, z = x0 + nx * e * (w / 2.0 + b), z0 + nz * e * (w / 2.0 + b)
                t = F.top(x, z, r[0], 1.0)
                if t is None:
                    continue
                d = r[0] - t[0]
                if d > worst:
                    worst, w_at = d, (round(u, 1), b, t[1])
                if b == 0.15 and t[1] == "GRASS" and d > LIP_M:
                    bare += 0.1
        cedges["lo" if e == e_lo else "hi"] = {"lip_m": round(worst, 3), "lip_at": w_at, "bare_m": round(bare, 1)}
    out["conn_edges"] = cedges

    # TEETH: along the connector's two edge strips, u 0..TEETH_U_M from the host edge, across the strip: the share of
    # samples where 1GRASS is the top surface with the strip (1KERB) under it within 0.3 m (ground through the strip)
    tot = teeth = 0
    tmax = 0.0
    for e in (1.0, -1.0):
        for k in range(0, int(TEETH_U_M / 0.25) + 1):
            uu = s_dir(min(0.25 * k, plen))
            (x0, z0), _t, (nx, nz), w = pp.frame(uu)
            for b in TEETH_B_M:
                x, z = x0 + nx * e * (w / 2.0 + b), z0 + nz * e * (w / 2.0 + b)
                sh = [(y, cls) for y, cls in F.sheets(x, z) if abs(y - cy) < 1.5]
                ks = [y for y, cls in sh if cls == "KERB"]
                if not ks:
                    continue
                tot += 1
                top = max(sh)
                if top[1] == "GRASS" and top[0] - max(ks) < 0.3:
                    teeth += 1
                    tmax = max(tmax, top[0] - max(ks))
    out["strip_teeth"] = {"samples": tot, "grass_over_strip": teeth,
                          "share": round(teeth / tot, 3) if tot else None, "max_m": round(tmax, 3)}

    # WHEELS (the connector frame; u < 0 runs straight on past the cut into the host)
    q0 = pp.point(s_dir(0.0), 0.0)
    (x00, z00), (tx0, tz0), (nx0, nz0), _w0 = pp.frame(s_dir(0.0))
    tx0, tz0 = tx0 * sgn_t, tz0 * sgn_t                      # away from the host
    # u = 0 at the host edge line: the cut sits ~0.4 m inside it
    u_edge = 0.0
    for k in range(0, 200):
        uu = 0.05 * k
        x, z = q0[0] + tx0 * uu, q0[1] + tz0 * uu
        if side * hp.project(x, z)[2] >= half:
            u_edge = uu
            break
    wheels = {}
    for l in (0.0, wc / 2.0 - WHEEL_IN_M, -(wc / 2.0 - WHEEL_IN_M), wc / 2.0 - 2.5, -(wc / 2.0 - 2.5)):
        ys = []
        yprev = cy
        holes = 0
        for k in range(0, int((WHEEL_BACK_M + WHEEL_OUT_M) / STEP_M) + 1):
            u = -WHEEL_BACK_M + STEP_M * k
            if u + u_edge <= 0.0:
                x = q0[0] + tx0 * (u + u_edge) + nx0 * sgn_t * l
                z = q0[1] + tz0 * (u + u_edge) + nz0 * sgn_t * l
            else:
                uu = s_dir(min(u + u_edge, plen))
                x, z = pp.point(uu, sgn_t * l)
            t = F.top(x, z, yprev, 0.3, ("ROAD", "KERB"))
            if t is None:
                holes += 1
                ys.append(None)
                continue
            yprev = t[0]
            ys.append(t[0])
        n10 = int(round(FINE_M / STEP_M))
        n1m = int(round(1.0 / STEP_M))
        worst = 0.0
        w_at = None
        for i in range(n1m + n10, len(ys)):
            a, b, p = ys[i], ys[i - n10], ys[i - n10 - n1m]
            if a is None or b is None or p is None:
                continue
            grade = (b - p) / 1.0
            step = (a - b) - grade * FINE_M
            if abs(step) > abs(worst):
                worst, w_at = step, round(-WHEEL_BACK_M + STEP_M * i, 2)
        wheels[f"{l:+.2f}"] = {"fine_step_m": round(worst, 3), "at_u_m": w_at, "holes": holes}
    out["wheels"] = wheels
    out["wheels_max_step_m"] = max(abs(w["fine_step_m"]) for w in wheels.values())

    # DAYLIGHT / overlap lip, GRASS on the deck
    over = []
    daylight = 0
    for k in range(-int(wc / 2.0 / 0.25), int(wc / 2.0 / 0.25) + 1):
        l = 0.25 * k
        if abs(l) > wc / 2.0 - 0.3:
            continue
        for u in (-0.3, -0.15, 0.0, 0.15):
            x = q0[0] + tx0 * (u + u_edge) + nx0 * sgn_t * l
            z = q0[1] + tz0 * (u + u_edge) + nz0 * sgn_t * l
            rs = sorted(y for y, cls in F.sheets(x, z) if cls == "ROAD" and abs(y - cy) < 1.5)
            if not rs:
                daylight += 1
            elif len(rs) >= 2:
                over.append(round(rs[-1] - rs[0], 3))
    out["overlap"] = {"samples_two_sheets": len(over), "max_sheet_gap_m": max(over) if over else 0.0,
                      "daylight": daylight}
    grass = 0
    gmax = None
    for k in range(-int(wc / 2.0 / 0.25), int(wc / 2.0 / 0.25) + 1):
        l = 0.25 * k
        if abs(l) > wc / 2.0 - 0.1:
            continue
        for j in range(0, int(WHEEL_OUT_M / 0.25) + 1):
            uu = s_dir(min(0.25 * j + u_edge, plen))
            x, z = pp.point(uu, sgn_t * l)
            r = F.top(x, z, cy, 1.5, ("ROAD",))
            g = F.top(x, z, cy, 1.5, ("GRASS",))
            if r and g and g[0] >= r[0] - 0.005:
                grass += 1
                gmax = max(gmax or -1, g[0] - r[0])
    out["grass_on_deck"] = {"samples": grass, "max_m": None if gmax is None else round(gmax, 3)}

    # MARKINGS across the opening and run on into the host (u < 0 on the centre). The host's EDGE LINE is white
    # (MARKINGS) and lies where the assembler paints it: v021 ribbon.lane_markings edge_inset 0.55 m, line_w 0.12 m, so
    # b in [-0.61, -0.49] (read on the built OBJ 20-25 m either side of the mouth: -0.60..-0.50). It is sampled across
    # its own band only. 0.2.6's first version sampled b -0.5 / -0.3 / -0.15 and counted YLINE too: -0.3 / -0.15 lie
    # off the host's line, where the STREET's own edge lines and centre line reach 0.17-0.31 m past the host edge at
    # the weld, so an opening with no host paint across it still read 0.25-0.5 m (ledger 0086, 0.2.7)
    mk_edge = 0
    s = s_lo
    while s <= s_hi:
        for b in (-0.58, -0.55, -0.52):
            x, z = hpt(s, b)
            if any(cls == "MARK" for _y, cls in F.sheets(x, z)):
                mk_edge += 1
                break
        s += 0.25
    mk_in = 0
    for k in range(1, int(WHEEL_BACK_M / 0.25) + 1):
        u = -0.25 * k
        x = q0[0] + tx0 * (u + u_edge)
        z = q0[1] + tz0 * (u + u_edge)
        if any(cls in ("MARK", "YLINE") for _y, cls in F.sheets(x, z)):
            mk_in += 1
    out["markings"] = {"edge_line_across_opening_m": round(0.25 * mk_edge, 2),
                       "centre_line_into_host_m": round(0.25 * mk_in, 2),
                       "opening_m": round(s_hi - s_lo, 2)}

    lips = [out["corners"]["lo"]["lip_m"], out["corners"]["hi"]["lip_m"],
            out["conn_edges"].get("lo", {}).get("lip_m", 0.0), out["conn_edges"].get("hi", {}).get("lip_m", 0.0)]
    out["score"] = {"max_lip_m": max(lips),
                    "bare_m": round(out["corners"]["lo"]["bare_m"] + out["corners"]["hi"]["bare_m"]
                                    + sum(v["bare_m"] for v in out["conn_edges"].values()), 1),
                    "wheel_step_m": out["wheels_max_step_m"],
                    "turn_r9_drop_m": max((t.get("r9", {}).get("max_drop_m", 0.0) for t in out["turns"].values()), default=0.0),
                    "turn_r9_off_road_m": round(sum(t.get("r9", {}).get("off_road_m", 0.0) for t in out["turns"].values()), 2)}
    return out


def locate_rog(project: Path, conns, local, mouths):
    """kn5_ground_check's road_over_ground, sample by sample, with places (gate-OBJ frame: the kn5's z mirrored)"""
    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo))
    from scripts.ac import kn5_ground_check as K
    from scripts.ac.verify_kn5 import _parse
    from scripts.capture import evidence
    cfg = json.loads((project / "track.config.json").read_text(encoding="utf-8"))
    kn5p = project / "build" / f"{cfg['slug']}.kn5"
    if abs(float(cfg.get("true_north_rotation_deg") or 0.0)) > 1e-9:
        raise SystemExit("[mouth_survey] --rog: a yawed track is not handled (Sand Creek LM: 0)")
    _n, meshes = _parse(kn5p)
    kb = defaultdict(list)
    for m in meshes:
        b = K._bucket(m["name"])
        if b:
            kb[b].extend(m["P"])
    road = kb.get("1ROAD_MAIN", []) + kb.get("1ROAD", [])
    pav, grs, struct = defaultdict(list), defaultdict(list), defaultdict(list)
    for mn, mp, mi in K._parse_tris(kn5p):
        up = mn.upper()
        if up.startswith(("1ROAD", "1GRASS", "1KERB", "1RUNOFF")):
            for t in range(0, len(mi) - 2, 3):
                a, b, c = mp[mi[t]], mp[mi[t + 1]], mp[mi[t + 2]]
                key = (int((a[0] + b[0] + c[0]) / 3 // 8), int((a[2] + b[2] + c[2]) / 3 // 8))
                (pav if up.startswith("1ROAD") else grs)[key].append((a, b, c))
        elif up.startswith("HWYSTRUCT"):
            for t in range(0, len(mi) - 2, 3):
                a, b, c = mp[mi[t]], mp[mi[t + 1]], mp[mi[t + 2]]
                for ci in range(int(min(a[0], b[0], c[0]) // 8), int(max(a[0], b[0], c[0]) // 8) + 1):
                    for cj in range(int(min(a[2], b[2], c[2]) // 8), int(max(a[2], b[2], c[2]) // 8) + 1):
                        struct[(ci, cj)].append((a, b, c))

    def surf(h, x, z, yn, below=None):
        best = None
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for a, b, c in h.get((int(x // 8) + di, int(z // 8) + dj), ()):
                    d0 = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
                    if abs(d0) < 1e-12:
                        continue
                    w0 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d0
                    w1 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d0
                    w2 = 1 - w0 - w1
                    if w0 >= -1e-6 and w1 >= -1e-6 and w2 >= -1e-6:
                        y = w0 * a[1] + w1 * b[1] + w2 * c[1]
                        if abs(y - yn) < 25 and (below is None or y <= below) and (best is None or y > best):
                            best = y
        return best
    spans = list(evidence.bridge_spans(project) or [])
    ap = project / "data" / "bridge.spans.auto.json"
    if ap.exists():
        spans += [((a + b) / 2.0, (b - a)) for a, b in json.loads(ap.read_text(encoding="utf-8"))]
    fcp = project / "data" / "finished_centerline.json"
    span_h = defaultdict(list)
    if spans and fcp.exists():
        fc = json.loads(fcp.read_text(encoding="utf-8"))["points_xyz_m"]
        st = 0.0
        for i in range(1, len(fc)):
            st += math.hypot(fc[i][0] - fc[i - 1][0], fc[i][2] - fc[i - 1][2])
            if any(abs(st - c0) < l0 / 2 + 170.0 for c0, l0 in spans):
                span_h[(int(fc[i][0] // 16), int(fc[i][2] // 16))].append((fc[i][0], fc[i][2]))

    def on_span(x, z):
        ci, cj = int(x // 16), int(z // 16)
        return any((x - a) ** 2 + (z - b) ** 2 <= 256.0 for di in (-1, 0, 1) for dj in (-1, 0, 1)
                   for a, b in span_h.get((ci + di, cj + dj), ()))
    tot = 0
    rows = []
    main = vm.Path2(local["points_xyz_m"], local["widths_m"])
    cpaths = [(c["name"], vm.Path2(c["points_xyz_m"], c["widths_m"])) for c in conns]
    for x, y, z in road[::7]:
        if on_span(x, z):
            continue
        g = surf(grs, x, z, y)
        if g is None or g > y + 0.3:
            continue
        if y - g > K.ROAD_GAP_M:
            s9 = surf(struct, x, z, y, below=y + 0.3)
            if s9 is not None and s9 > g:
                continue
            p9 = surf(pav, x, z, y, below=y - 0.05)
            if p9 is not None and p9 > g:
                continue
        tot += 1
        if y - g <= K.ROAD_GAP_M:
            continue
        X, Z = x, -z                                            # gate-OBJ frame
        d, sm, lat = main.project(X, Z)
        lap = {"s_m": round(sm, 1), "edge_off_m": round(abs(lat) - main.frame(sm)[3] / 2.0, 2)}
        best = None
        for nm, cp in cpaths:
            dd, sc, lc = cp.project(X, Z)
            off = abs(lc) - cp.frame(sc)[3] / 2.0
            if best is None or abs(off) < abs(best[1]):
                best = (nm, off, sc, cp.s[-1])
        mo = min(mouths, key=lambda m: math.hypot(m["cut_xyz"][0] - X, m["cut_xyz"][2] - Z))
        rows.append({"gap_m": round(y - g, 3), "xyz": [round(X, 2), round(y, 3), round(Z, 2)], "lap": lap,
                     "street": best[0], "street_edge_off_m": round(best[1], 2),
                     "street_s_m": [round(best[2], 1), round(best[3], 1)],
                     "mouth": f"{mo['piece']}({mo['end']})->{mo['host']}",
                     "mouth_dist_m": round(math.hypot(mo["cut_xyz"][0] - X, mo["cut_xyz"][2] - Z), 1)})
    rows.sort(key=lambda r: -r["gap_m"])
    return {"samples": tot, "over": len(rows), "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--obj", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--rog", action="store_true")
    a = ap.parse_args(argv)
    proj = Path(a.project)
    data = proj / "data"
    mouths = json.loads((data / "mouths.json").read_text(encoding="utf-8"))["mouths"]
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    obj = Path(a.obj) if a.obj else data / "track.obj"
    F = Field(load(obj, [(m["cut_xyz"][0], m["cut_xyz"][2]) for m in mouths]))
    rows = []
    for mo in mouths:
        hp, pp, end = _frames(mo, conns, local)
        rows.append(survey_mouth(mo, F, hp, pp, end))
    ok = [r for r in rows if "score" in r]
    ok.sort(key=lambda r: (-(r["score"]["bare_m"] > 0), -r["score"]["max_lip_m"], -r["score"]["wheel_step_m"]))
    res = {"obj": str(obj), "mouths": ok, "errors": [r for r in rows if "score" not in r]}
    if a.rog:
        res["road_over_ground"] = locate_rog(proj, conns, local, mouths)
        nc = 0
        for g in res["road_over_ground"]["rows"]:
            for r in ok:
                if math.hypot(r["cut_xyz"][0] - g["xyz"][0], r["cut_xyz"][2] - g["xyz"][2]) > 30.0:
                    continue
                hit = r["_in_corner"](g["xyz"][0], g["xyz"][2])
                if hit:
                    g["corner"] = {"mouth": f"{r['piece']}({r['end']})->{r['host']}", "corner": hit[0],
                                   "a_m": hit[1], "b_m": hit[2]}
                    nc += 1
                    break
        res["road_over_ground"]["in_a_mouth_corner"] = nc
    for r in rows:
        r.pop("_in_corner", None)
    out = Path(a.json) if a.json else data / "mouth_survey.json"
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    for r in ok:
        sg = r.get("strip_gap", {})
        print(f"[mouth_survey] {r['piece']}({r['end']})->{r['host']} w{r['conn_width_m']} ang {r['angle_deg']}: "
              f"lip {r['score']['max_lip_m']:.3f} m, bare {r['score']['bare_m']} m "
              f"(corners lo {r['corners']['lo']['lip_m']}/{r['corners']['lo']['bare_m']} hi {r['corners']['hi']['lip_m']}/"
              f"{r['corners']['hi']['bare_m']}; conn edges {r['conn_edges'].get('lo', {}).get('lip_m')}/"
              f"{r['conn_edges'].get('hi', {}).get('lip_m')}); strip gap overhang {sg.get('overhang_m')} offset "
              f"{sg.get('plan_offset_m')}; wheel step {r['score']['wheel_step_m']:.3f}; overlap gap "
              f"{r['overlap']['max_sheet_gap_m']} daylight {r['overlap']['daylight']}; grass {r['grass_on_deck']['samples']}; "
              f"marks edge {r['markings']['edge_line_across_opening_m']} into {r['markings']['centre_line_into_host_m']}; "
              f"turn r9 drop {r['score']['turn_r9_drop_m']} off-road {r['score']['turn_r9_off_road_m']} m")
    for r in res["errors"]:
        print(f"[mouth_survey] {r['piece']}({r['end']})->{r['host']}: {r['error']}")
    if a.rog:
        g = res["road_over_ground"]
        print(f"[mouth_survey] road_over_ground: {g['over']}/{g['samples']} over 0.05 m, {g['in_a_mouth_corner']} in a "
              f"mouth's corner")
        for r in g["rows"]:
            cn = r.get("corner")
            print(f"  {r['gap_m']:.3f} at {r['xyz']} lap s{r['lap']['s_m']} edge{r['lap']['edge_off_m']:+} | {r['street']} "
                  f"edge{r['street_edge_off_m']:+} s{r['street_s_m']} | {r['mouth']} {r['mouth_dist_m']} m"
                  + (f" | CORNER {cn['corner']} of {cn['mouth']} a {cn['a_m']} b {cn['b_m']}" if cn else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
