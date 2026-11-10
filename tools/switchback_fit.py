"""A switchback built as measured: its line on the measured circle, joined to the legs as they are (ledger 0078 round 10).

tools/switchback_measure.py fits each switchback's graded platform in the 1 m DEM: a centre, the centre arc's radius and
the platform's width. The Lariat's scripts/geometry/corner_arcs.fit_corners (arms fitted 16-40 m out, a 1.5 deg step
rule) refuses these turns: Dragon Tail's switchback 2 turns 168 deg on legs of ~15 m. This fit takes the circle as given:

  * on each side of the apex, the leg point nearest the apex (at least LEG_MIN_M out) whose tangent to the circle, on
    the turn's side, leaves it within JOIN_TOL_DEG of the leg's own heading there (the leg as it is, LEG_DIR_M of it);
  * the new line: the leg to that point, the tangent to the circle, the circle round to the exit tangent, the tangent
    to the exit leg point; the original vertices between the two leg points are re-spaced evenly along it (count kept),
    their heights carried by fraction of length (the profile as road_seek read it);
  * the width there is the measured platform's (tapered into the legs later, lm_intake.width_taper).

Proved on the result (FAIL = the turn is left as it was, and reported): every step runs forward (the next point ahead
of the last along the line's own direction); the swept road's inside edge stays at least INSIDE_MARGIN_M outside the
circle's centre (R - width / 2), so nothing folds; every new point on the arc stands on the measured platform (between
the inside and outside circles). Pure Python; tools/lm_engine_intake.py applies it (lm_intake.switchback_fit).
"""
from __future__ import annotations

import math

LEG_MIN_M = 4.0          # [invented] a join never closer to the apex than this
LEG_MAX_M = 80.0         # [invented] nor further than this
LEG_DIR_M = 6.0          # the leg's own heading read over this much of it
JOIN_TOL_DEG = 12.0      # [invented] the tangent leaves the leg within this of the leg's heading (the assembler's own curve
                         # smoothing takes the join's kink out: its "smoothed curves: max kink" pass)
INSIDE_MARGIN_M = 1.0    # [invented] the swept inside edge stays this far outside the circle's centre


def _st(P):
    s = [0.0]
    for a, b in zip(P, P[1:]):
        s.append(s[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    return s


def _tangent_point(px, pz, cx, cz, R, side):
    """the tangent point on the circle from (px, pz): side +1 = the circle on the path's left (a left turn)"""
    dx, dz = cx - px, cz - pz
    d = math.hypot(dx, dz)
    if d <= R:
        return None
    a = math.atan2(dz, dx)
    b = math.asin(R / d)
    ang = a + (-b if side > 0 else b)               # the direction from p to the tangent point
    L = math.sqrt(d * d - R * R)
    return px + L * math.cos(ang), pz + L * math.sin(ang), ang


def fit_one(P, W, c):
    """fit corner c {"st_m", "radius_m", "width_m", "centre_xz", "r_inside_m", "r_outside_m"} into P (list of (x, y, z))
    and W (widths). Returns (P2, W2, report)."""
    n = len(P)
    st = _st(P)
    cx, cz = c["centre_xz"]
    R = float(c["radius_m"])
    width = float(c["width_m"])
    apex = min(range(n), key=lambda k: abs(st[k] - c["st_m"]))
    # the turn's side: + = left (the centre on the left of travel at the apex)
    a, b = P[max(apex - 2, 0)], P[min(apex + 2, n - 1)]
    tx, tz = b[0] - a[0], b[2] - a[2]
    side = 1.0 if (tx * (cz - P[apex][2]) - tz * (cx - P[apex][0])) > 0 else -1.0
    rep = {"id": c["id"], "st_m": c["st_m"], "radius_m": R, "width_m": width, "side": "left" if side > 0 else "right"}

    def leg_heading(i, back):
        j = i
        while 0 < j < n - 1 and abs(st[j] - st[i]) < LEG_DIR_M:
            j += -1 if back else 1
        p, q = (P[j], P[i]) if back else (P[i], P[j])
        return math.atan2(q[2] - p[2], q[0] - p[0])

    def wrap(t):
        return (t + math.pi) % (2 * math.pi) - math.pi
    # entry: walking back from the apex, the first leg point whose tangent leaves along the leg's heading
    i_in = None
    best_in = best_out = None
    for i in range(apex, -1, -1):
        if st[apex] - st[i] < LEG_MIN_M:
            continue
        if st[apex] - st[i] > LEG_MAX_M:
            break
        tp = _tangent_point(P[i][0], P[i][2], cx, cz, R, side)
        if tp:
            mis = abs(math.degrees(wrap(tp[2] - leg_heading(i, True))))
            best_in = mis if best_in is None else min(best_in, mis)
        if tp and abs(math.degrees(wrap(tp[2] - leg_heading(i, True)))) <= JOIN_TOL_DEG:
            i_in, T_in = i, tp
            break
    # exit: walking on from the apex, a leg point the circle leaves toward along the leg's heading (the reverse tangent)
    i_out = None
    for j in range(apex, n):
        if st[j] - st[apex] < LEG_MIN_M:
            continue
        if st[j] - st[apex] > LEG_MAX_M:
            break
        tp = _tangent_point(P[j][0], P[j][2], cx, cz, R, -side)     # seen from the exit point, the circle is behind
        if tp:
            back = wrap(tp[2] + math.pi)                            # travel from the tangent point to the leg point
            mis = abs(math.degrees(wrap(back - leg_heading(j, False))))
            best_out = mis if best_out is None else min(best_out, mis)
            if abs(math.degrees(wrap(back - leg_heading(j, False)))) <= JOIN_TOL_DEG:
                i_out, T_out = j, tp
                break
    if i_in is None or i_out is None:
        rep.update({"status": "FAIL", "why": f"no leg point whose tangent to the measured circle runs along the leg "
                                             f"(closest: entry {None if best_in is None else round(best_in, 1)} deg, exit "
                                             f"{None if best_out is None else round(best_out, 1)} deg; found entry "
                                             f"{i_in is not None}, exit {i_out is not None})"})
        return P, W, rep
    # the new path: P[i_in] -> T_in -> arc -> T_out -> P[i_out]
    a0 = math.atan2(T_in[1] - cz, T_in[0] - cx)
    a1 = math.atan2(T_out[1] - cz, T_out[0] - cx)
    sweep = a1 - a0
    if side > 0:
        while sweep <= 0:
            sweep += 2 * math.pi
    else:
        while sweep >= 0:
            sweep -= 2 * math.pi
    path = [(P[i_in][0], P[i_in][2]), (T_in[0], T_in[1])]
    k = max(2, int(abs(sweep) * R / 0.5))
    path += [(cx + R * math.cos(a0 + sweep * q / k), cz + R * math.sin(a0 + sweep * q / k)) for q in range(1, k)]
    path += [(T_out[0], T_out[1]), (P[i_out][0], P[i_out][2])]
    ps = _st([(p[0], 0.0, p[1]) for p in path])
    m = i_out - i_in
    old_s = [st[i] - st[i_in] for i in range(i_in, i_out + 1)]
    newP = list(P)
    newW = list(W)
    for q in range(1, m):
        f = q / m
        s = f * ps[-1]
        h = max(0, min(len(path) - 2, next((r for r in range(len(path) - 1) if ps[r + 1] >= s), len(path) - 2)))
        u = (s - ps[h]) / max(1e-9, ps[h + 1] - ps[h])
        x = path[h][0] + (path[h + 1][0] - path[h][0]) * u
        z = path[h][1] + (path[h + 1][1] - path[h][1]) * u
        so = f * old_s[-1]                                     # the height at the same fraction of the old length
        g = max(0, min(m - 1, next((r for r in range(m) if old_s[r + 1] >= so), m - 1)))
        v = (so - old_s[g]) / max(1e-9, old_s[g + 1] - old_s[g])
        y = P[i_in + g][1] + (P[i_in + g + 1][1] - P[i_in + g][1]) * v
        newP[i_in + q] = (x, y, z)
        on_arc = abs(math.hypot(x - cx, z - cz) - R) < 0.05
        newW[i_in + q] = width if on_arc else max(W[i_in + q], width)
    # the proofs
    back_steps = 0
    for i in range(i_in + 1, i_out + 1):
        d0 = (newP[i - 1][0] - newP[max(i - 2, 0)][0], newP[i - 1][2] - newP[max(i - 2, 0)][2])
        d1 = (newP[i][0] - newP[i - 1][0], newP[i][2] - newP[i - 1][2])
        if d0[0] * d1[0] + d0[1] * d1[1] <= 0:
            back_steps += 1
    inside = R - width / 2.0
    off = [abs(math.hypot(newP[i][0] - cx, newP[i][2] - cz) - R) for i in range(i_in + 1, i_out)
           if abs(math.hypot(newP[i][0] - cx, newP[i][2] - cz) - R) < 0.05]
    r_in, r_out = float(c.get("r_inside_m", 0)), float(c.get("r_outside_m", 1e9))
    on_platform = r_in <= R <= r_out
    rep.update({"span_i": [i_in, i_out], "join_m": [round(st[apex] - st[i_in], 1), round(st[i_out] - st[apex], 1)],
                "points": m - 1,
                "arc_deg": round(abs(math.degrees(sweep)), 1), "back_steps": back_steps,
                "inside_edge_r_m": round(inside, 2), "arc_points": len(off), "on_platform": on_platform})
    ok = back_steps == 0 and inside >= INSIDE_MARGIN_M and on_platform
    rep["status"] = "PASS" if ok else "FAIL"
    if not ok:
        rep["why"] = ("a step back" if back_steps else "") + (" the inside edge folds" if inside < INSIDE_MARGIN_M else "") \
            + ("" if on_platform else " the arc leaves the platform")
        return P, W, rep
    return newP, newW, rep


def fit_all(P, W, corners):
    reps = []
    for c in sorted(corners, key=lambda q: q["st_m"]):
        P, W, r = fit_one(P, W, c)
        reps.append(r)
    return P, W, reps
