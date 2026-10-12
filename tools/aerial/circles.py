"""Robust fits for the aerial measurement: one circle, one centre with two radii (concentric edge pair),
and a straight line.

Thresholds, all **[invented]** for the aerial pass (2026-10-11), none a gate:

- ``robust_circle``: refit, trimming points beyond max(``floor`` 0.3 m, ``k`` 2.5 x rms) of the circle, at
  most 6 rounds, at least ``min_n`` 8 points [invented].
- ``concentric``: one centre, two radii (the inner and outer edge sets of a hairpin), the same trimming
  (max(0.3 m, 2.5 rms) per set), at least 10 points per set [invented].
- ``robust_line``: total-least-squares line refit trimming beyond max(0.25 m, 2.5 rms), at least 6 points
  [invented].
"""
from __future__ import annotations

import math

from . import geo


def robust_circle(pts, k=2.5, floor=0.3, iters=6, min_n=8):
    pts = [p for p in pts if p is not None]
    if len(pts) < min_n:
        return None
    use = list(pts)
    f = geo.fit_circle(use)
    for _ in range(iters):
        if f is None:
            return None
        cx, cy, R, rms = f
        lim = max(floor, k * rms)
        keep = [p for p in pts if abs(math.hypot(p[0] - cx, p[1] - cy) - R) <= lim]
        if len(keep) < min_n:
            break
        if len(keep) == len(use):
            break
        use = keep
        f = geo.fit_circle(use)
    if f is None:
        return None
    cx, cy, R, rms = f
    angs = sorted(math.atan2(p[1] - cy, p[0] - cx) for p in use)
    gaps = [angs[i + 1] - angs[i] for i in range(len(angs) - 1)] + [angs[0] + 2 * math.pi - angs[-1]]
    return {"cx": cx, "cy": cy, "R": R, "rms": rms, "n": len(use), "n_in": len(pts),
            "span_deg": math.degrees(2 * math.pi - max(gaps)), "used": use}


# ---------------------------------------------------------------- concentric pair
def _solve(A, b):
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for i in range(n):
        piv = max(range(i, n), key=lambda k: abs(M[k][i]))
        if abs(M[piv][i]) < 1e-12:
            return None
        M[i], M[piv] = M[piv], M[i]
        for k in range(i + 1, n):
            f = M[k][i] / M[i][i]
            for j in range(i, n + 1):
                M[k][j] -= f * M[i][j]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))) / M[i][i]
    return x


def concentric_fit(P, Q, c0, iters=60):
    """Gauss-Newton: one centre (cx, cy), radius R_in for P and R_out for Q."""
    cx, cy = c0
    R1 = sum(math.hypot(p[0] - cx, p[1] - cy) for p in P) / len(P)
    R2 = sum(math.hypot(q[0] - cx, q[1] - cy) for q in Q) / len(Q)
    for _ in range(iters):
        JTJ = [[0.0] * 4 for _ in range(4)]
        JTr = [0.0] * 4
        for pts, k in ((P, 2), (Q, 3)):
            for p in pts:
                dx, dy = p[0] - cx, p[1] - cy
                d = math.hypot(dx, dy) or 1e-9
                res = d - (R1 if k == 2 else R2)
                J = [-dx / d, -dy / d, 0.0, 0.0]
                J[k] = -1.0
                for a in range(4):
                    JTr[a] += J[a] * res
                    for b in range(4):
                        JTJ[a][b] += J[a] * J[b]
        dlt = _solve(JTJ, [-v for v in JTr])
        if dlt is None:
            return None
        cx += dlt[0]
        cy += dlt[1]
        R1 += dlt[2]
        R2 += dlt[3]
        if max(abs(v) for v in dlt) < 1e-7:
            break
    r1 = [math.hypot(p[0] - cx, p[1] - cy) - R1 for p in P]
    r2 = [math.hypot(q[0] - cx, q[1] - cy) - R2 for q in Q]
    rms1 = math.sqrt(sum(v * v for v in r1) / len(r1))
    rms2 = math.sqrt(sum(v * v for v in r2) / len(r2))
    return {"cx": cx, "cy": cy, "R_in": R1, "R_out": R2, "rms_in": rms1, "rms_out": rms2,
            "n_in": len(P), "n_out": len(Q)}


def concentric(P, Q, c0, k=2.5, floor=0.3, min_n=10):
    """Robust concentric fit (trimming each set at max(floor, k x its rms)); None with too few points."""
    P = list(P)
    Q = list(Q)
    if len(P) < min_n or len(Q) < min_n:
        return None
    f = concentric_fit(P, Q, c0)
    for _ in range(6):
        if f is None:
            return None
        l1 = max(floor, k * f["rms_in"])
        l2 = max(floor, k * f["rms_out"])
        P2 = [p for p in P if abs(math.hypot(p[0] - f["cx"], p[1] - f["cy"]) - f["R_in"]) <= l1]
        Q2 = [q for q in Q if abs(math.hypot(q[0] - f["cx"], q[1] - f["cy"]) - f["R_out"]) <= l2]
        if len(P2) < min_n or len(Q2) < min_n:
            break
        if len(P2) == f["n_in"] and len(Q2) == f["n_out"]:
            break
        f = concentric_fit(P2, Q2, (f["cx"], f["cy"]))
    if f is None:
        return None
    f["n_in_all"] = len(P)
    f["n_out_all"] = len(Q)
    f["R_mean"] = 0.5 * (f["R_in"] + f["R_out"])
    return f


# ---------------------------------------------------------------- lines
def line_fit(pts):
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    syy = sum((p[1] - my) ** 2 for p in pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    th = 0.5 * math.atan2(2 * sxy, sxx - syy)
    d = (math.cos(th), math.sin(th))
    res = [(p[0] - mx) * -d[1] + (p[1] - my) * d[0] for p in pts]
    rms = math.sqrt(sum(r * r for r in res) / n)
    return (mx, my), d, rms


def robust_line(pts, k=2.5, floor=0.25):
    use = list(pts)
    for _ in range(5):
        c, d, rms = line_fit(use)
        lim = max(floor, k * rms)
        keep = [p for p in pts if abs((p[0] - c[0]) * -d[1] + (p[1] - c[1]) * d[0]) <= lim]
        if len(keep) == len(use) or len(keep) < 6:
            break
        use = keep
    c, d, rms = line_fit(use)
    return {"c": c, "d": d, "rms": rms, "n": len(use), "n_all": len(pts)}
