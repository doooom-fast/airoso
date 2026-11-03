"""Declared corners swept as transition-arc-transition curves at a measured radius, on the line the road is swept over.

Lookout Lariat V3-PLAN A2 / P2 step 2 (ledger 0048): "each corner of >= 90 deg on the climb and at C12-C13 is replaced
by a curvature-continuous arc with transition curves. The radius is the one measured on the aerial." The climb's hairpins
are already curves in the paint centreline (tools/paint_centreline.py, judged by tools/verify_centreline_paint.py); C12
and C13 are not: each is a junction NODE that holds most of a 76-79 deg turn (the arc at the aerial radius overruns the
traced arm paint, so the paint line kept the node). The engine's own corner rounding leaves such a node at a ~2.4 m
centreline radius, and a 7-14 m ribbon folds through it (drive_test: severe steps at C13, st 10,617-10,625).

OPT-IN: ``hairpin_fit.mesh_fit`` lists corner ids of ``hairpin_fit.corners`` (each with ``st_m`` and ``radius_m``);
build_mesh's finished_centerline() fits them after its own rounding, so the fit is on the line that is swept, before any
ribbon exists. Every track without the key is untouched.

THE FIT, per corner: the apex is the vertex within ``search_m`` of ``st_m`` whose +-15 m window turns most; each arm is a
least-squares straight line through the line's points ``arm_m`` = [near, far] metres before / after the apex; the curve
is a clothoid (curvature 0 -> 1/R over ``transition_m``), an arc of radius R, and a clothoid back to 0, starting on the
entry arm on its heading and ending on the exit arm on its heading (one free parameter, solved exactly). The vertices
between the curve's ends are replaced by points spread evenly along it (the vertex COUNT is kept: widths, indices and
heights stay paired), heights kept by index; the arm vertices from ``arm_m[1]`` to the curve's ends are eased onto the
fitted arm lines (smoothstep), so the joins carry no kink. The plan's step gate (P2 step 2) is then measured on the result:
every heading change <= spacing / R x 57.3 deg + 1 deg, adjacent changes differ by <= 1.5 deg [both invented, the plan's].

Pure stdlib.
"""
from __future__ import annotations

import math

DEG = 180.0 / math.pi
DEFAULTS = {"search_m": 40.0, "arm_m": [16.0, 40.0], "transition_m": 8.0, "window_m": 15.0,
            "step_slack_deg": 1.0, "adjacent_step_deg": 1.5, "gate_margin": 5}


def _stations(P):
    s = [0.0]
    for i in range(1, len(P)):
        s.append(s[-1] + math.hypot(P[i][0] - P[i - 1][0], P[i][2] - P[i - 1][2]))
    return s


def _heading(P, i, j):
    return math.atan2(P[j][2] - P[i][2], P[j][0] - P[i][0])


def _wrap(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def _fit_line(pts):
    """Least-squares line through (x, z) points: (centroid, unit direction along the points' order)."""
    n = len(pts)
    cx = sum(p[0] for p in pts) / n
    cz = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - cx) ** 2 for p in pts)
    szz = sum((p[1] - cz) ** 2 for p in pts)
    sxz = sum((p[0] - cx) * (p[1] - cz) for p in pts)
    ang = 0.5 * math.atan2(2.0 * sxz, sxx - szz)
    u = (math.cos(ang), math.sin(ang))
    if (pts[-1][0] - pts[0][0]) * u[0] + (pts[-1][1] - pts[0][1]) * u[1] < 0:
        u = (-u[0], -u[1])
    return (cx, cz), u


def clothoid_arc(R: float, delta: float, Lt: float, ds: float = 0.02):
    """Points (x, z) and the length of a 0 -> 1/R -> 0 curvature curve turning ``delta`` (signed, rad), starting at the
    origin heading +x. Raises ValueError when the turn is too small for two transitions at this radius."""
    Lc = R * abs(delta) - Lt
    if Lc < 0.0:
        raise ValueError(f"turn {abs(delta) * DEG:.1f} deg is shorter than two {Lt} m transitions at R {R} m")
    sgn = 1.0 if delta > 0 else -1.0
    L = 2.0 * Lt + Lc
    n = max(2, int(math.ceil(L / ds)))
    h = L / n
    x = z = th = 0.0
    out = [(0.0, 0.0)]

    def kappa(s):
        if s < Lt:
            return sgn * (s / Lt) / R
        if s <= Lt + Lc:
            return sgn / R
        return sgn * max(0.0, (L - s) / Lt) / R
    for k in range(n):
        s0 = k * h
        # midpoint rule on the heading, exact enough at 2 cm steps
        th_mid = th + kappa(s0 + 0.25 * h) * 0.5 * h
        x += math.cos(th_mid) * h
        z += math.sin(th_mid) * h
        th += 0.5 * h * (kappa(s0) + kappa(s0 + h))
        out.append((x, z))
    return out, L


def _resample(poly, n):
    """``n`` points spread evenly by length along polyline ``poly`` (first and last kept)."""
    s = [0.0]
    for i in range(1, len(poly)):
        s.append(s[-1] + math.hypot(poly[i][0] - poly[i - 1][0], poly[i][1] - poly[i - 1][1]))
    L = s[-1]
    out = []
    j = 0
    for k in range(n):
        t = L * k / (n - 1)
        while j < len(s) - 2 and s[j + 1] < t:
            j += 1
        seg = s[j + 1] - s[j] or 1e-12
        f = (t - s[j]) / seg
        out.append((poly[j][0] + (poly[j + 1][0] - poly[j][0]) * f, poly[j][1] + (poly[j + 1][1] - poly[j][1]) * f))
    return out


def step_gate(P, lo, hi, R, slack_deg, adj_deg):
    """The plan's step gate on P[lo..hi]: per-vertex heading change and its change between neighbours."""
    steps = []
    for i in range(max(1, lo), min(len(P) - 1, hi + 1)):
        d = _wrap(_heading(P, i, i + 1) - _heading(P, i - 1, i))
        sp = 0.5 * (math.hypot(P[i][0] - P[i - 1][0], P[i][2] - P[i - 1][2])
                    + math.hypot(P[i + 1][0] - P[i][0], P[i + 1][2] - P[i][2]))
        steps.append((i, d * DEG, sp))
    fails = []
    for k, (i, d, sp) in enumerate(steps):
        lim = sp / R * DEG + slack_deg
        if abs(d) > lim:
            fails.append({"v": i, "step_deg": round(d, 2), "limit_deg": round(lim, 2)})
        if k and abs(d - steps[k - 1][1]) > adj_deg:
            fails.append({"v": i, "adjacent_diff_deg": round(abs(d - steps[k - 1][1]), 2), "limit_deg": adj_deg})
    return {"max_step_deg": round(max((abs(d) for _i, d, _s in steps), default=0.0), 2),
            "max_adjacent_diff_deg": round(max((abs(steps[k][1] - steps[k - 1][1]) for k in range(1, len(steps))),
                                               default=0.0), 2),
            "fails": fails, "pass": not fails}


def fit_corners(line, corners, prm=None):
    """``line``: [(x, y, z)] (closed when first == last). ``corners``: [{"id", "st_m", "radius_m"}]. Returns (new line,
    report). Vertex count, order and heights are kept; only x / z move, inside each corner's arms."""
    prm = dict(DEFAULTS, **(prm or {}))
    P = [list(p) for p in line]
    closed = len(P) > 2 and math.hypot(P[0][0] - P[-1][0], P[0][2] - P[-1][2]) < 1e-6
    report = []
    for c in corners:
        st = _stations(P)
        n = len(P)
        R = float(c["radius_m"])
        win = float(prm["window_m"])

        def idx_at(s):
            return min(range(n), key=lambda k: abs(st[k] - s))
        lo_s, hi_s = c["st_m"] - prm["search_m"], c["st_m"] + prm["search_m"]
        best = None
        for i in range(n):
            if not (lo_s <= st[i] <= hi_s):
                continue
            a, b = idx_at(st[i] - win), idx_at(st[i] + win)
            if a < 1 or b > n - 2:
                continue
            t = _wrap(_heading(P, b, b + 1) - _heading(P, a - 1, a))
            if best is None or abs(t) > abs(best[1]):
                best = (i, t)
        if best is None:
            report.append({"id": c["id"], "status": "SKIPPED", "why": "no apex found near st_m"})
            continue
        apex = best[0]
        near, far = prm["arm_m"]
        ia0, ia1 = idx_at(st[apex] - far), idx_at(st[apex] - near)
        ib0, ib1 = idx_at(st[apex] + near), idx_at(st[apex] + far)
        if ia0 < 1 or ib1 > n - 2 or ia1 - ia0 < 3 or ib1 - ib0 < 3:
            report.append({"id": c["id"], "status": "SKIPPED", "why": "arms run off the line"})
            continue
        pin, uin = _fit_line([(P[k][0], P[k][2]) for k in range(ia0, ia1 + 1)])
        pout, uout = _fit_line([(P[k][0], P[k][2]) for k in range(ib0, ib1 + 1)])
        delta = _wrap(math.atan2(uout[1], uout[0]) - math.atan2(uin[1], uin[0]))
        Lt = float(c.get("transition_m", prm["transition_m"]))
        curve, Lcurve = clothoid_arc(R, delta, Lt)
        # place: start on the entry arm at pin + a * uin with the arm's heading; the end must lie on the exit arm
        ca, sa = uin
        E0 = curve[-1]
        Ex, Ez = pin[0] + ca * E0[0] - sa * E0[1], pin[1] + sa * E0[0] + ca * E0[1]
        nout = (-uout[1], uout[0])
        den = nout[0] * uin[0] + nout[1] * uin[1]
        a = -(nout[0] * (Ex - pout[0]) + nout[1] * (Ez - pout[1])) / den
        A = (pin[0] + a * uin[0], pin[1] + a * uin[1])
        placed = [(A[0] + ca * x - sa * z, A[1] + sa * x + ca * z) for x, z in curve]
        E = placed[-1]

        def proj_st(p, i0, i1):
            k = min(range(i0, i1 + 1), key=lambda j: (P[j][0] - p[0]) ** 2 + (P[j][2] - p[1]) ** 2)
            return k
        iA = proj_st(A, ia0, apex)
        iB = proj_st(E, apex, ib1)
        if not (ia0 < iA < apex < iB < ib1):
            report.append({"id": c["id"], "status": "SKIPPED",
                           "why": f"curve ends fall outside the arms (iA {iA}, apex {apex}, iB {iB}); R {R} too large"})
            continue
        before = [(P[k][0], P[k][2]) for k in range(ia0, ib1 + 1)]
        # the curve between its ends, the same vertex count
        pts = _resample(placed, iB - iA + 1)
        for k, (x, z) in zip(range(iA, iB + 1), pts):
            P[k][0], P[k][2] = x, z
        # ease the arms onto their fitted lines: 0 at the far end of each arm, 1 at the curve's end
        for k0, k1, p0, u in ((ia0, iA, pin, uin), (iB, ib1, pout, uout)):
            for k in range(k0, k1 + 1):
                if k in (iA, iB):
                    continue
                t = (k - k0) / max(1, k1 - k0)
                w = t if k0 == ia0 else 1.0 - t
                w = w * w * (3.0 - 2.0 * w)
                dx, dz = P[k][0] - p0[0], P[k][2] - p0[1]
                along = dx * u[0] + dz * u[1]
                qx, qz = p0[0] + along * u[0], p0[1] + along * u[1]
                P[k][0] = P[k][0] * (1.0 - w) + qx * w
                P[k][2] = P[k][2] * (1.0 - w) + qz * w
        move = 0.0
        for (x0, z0), k in zip(before, range(ia0, ib1 + 1)):
            move = max(move, math.hypot(P[k][0] - x0, P[k][2] - z0))
        m = int(prm["gate_margin"])
        g = step_gate(P, ia0 - m, ib1 + m, R, prm["step_slack_deg"], prm["adjacent_step_deg"])
        report.append({"id": c["id"], "status": "PASS" if g["pass"] else "FAIL", "radius_m": R,
                       "turn_deg": round(delta * DEG, 1), "apex_st_m": round(st[apex], 1),
                       "transition_m": Lt, "arc_m": round(Lcurve - 2.0 * Lt, 1), "span_v": [iA, iB],
                       "span_st_m": [round(st[iA], 1), round(st[iB], 1)],
                       "max_move_m": round(move, 2), "gate": g})
    if closed:
        P[-1] = list(P[0])
    return [tuple(p) for p in P], report
