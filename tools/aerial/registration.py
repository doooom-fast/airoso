"""Registration check: the traced double-yellow centre line (NAIP, NAD83 / UTM 13N) against the raw OSM way
geometry (WGS84 put on the same grid with no datum shift).

Model per point: d = n . (Q_osm - P_paint) = n . v + noise, with n the road's left normal at the paint point
and Q_osm the nearest point on any OSM highway way. v (OSM minus imagery, metres E, N) is solved per window
and over all windows, each window weighted equally. Straight road only: OSM chords cut hairpins, which
would bias v toward the inside of every bend.

Thresholds, all **[invented]** for the aerial pass (2026-10-11), none a gate:
- straight = the reference's radius over +-6 m is >= 120 m (``STRAIGHT_R_M``) [invented];
- every 2nd profile; >= 3 m from the reference ends [invented];
- the nearest OSM way within 8 m and parallel (|cos| >= 0.95) [invented];
- a window needs >= 6 points; its own v is reported only when its directions spread (det / n^2 > 0.02)
  [invented].
"""
from __future__ import annotations

import math
import statistics as stt

from . import geo, profile as pf

STRAIGHT_R_M = 120.0


def nearest_on_ways(ways, p, maxd=10.0):
    best = None
    for w in ways:
        u = w["utm"]
        for i in range(len(u) - 1):
            a, b = u[i], u[i + 1]
            if min(a[0], b[0]) - maxd > p[0] or max(a[0], b[0]) + maxd < p[0] or \
                    min(a[1], b[1]) - maxd > p[1] or max(a[1], b[1]) + maxd < p[1]:
                continue
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy
            if L2 == 0:
                continue
            t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
            q = (a[0] + t * dx, a[1] + t * dy)
            d = math.hypot(q[0] - p[0], q[1] - p[1])
            if best is None or d < best[0]:
                best = (d, q, w["id"], (dx / math.sqrt(L2), dy / math.sqrt(L2)))
    return best


def samples_from(ways, ref_pts, rows, key="yellow", every=2):
    ref = pf.Poly(ref_pts)
    out = []
    for i, r in enumerate(rows):
        if i % every:
            continue
        y = r.get(key) if isinstance(r, dict) and key in r else (r.get("r") or {}).get(key)
        if y is None:
            continue
        s = r["s"]
        if s < 3 or s > ref.L - 3:
            continue
        f = geo.fit_circle([ref.pos(s + k) for k in range(-6, 7)])
        if f and f[2] < STRAIGHT_R_M:
            continue
        p = ref.pos(s)
        n = pf.left_normal(ref.tan(s))
        P = (p[0] + n[0] * y, p[1] + n[1] * y)
        nb = nearest_on_ways(ways, P)
        if nb is None or nb[0] > 8:
            continue
        t = ref.tan(s)
        if abs(t[0] * nb[3][0] + t[1] * nb[3][1]) < 0.95:
            continue
        d = n[0] * (nb[1][0] - P[0]) + n[1] * (nb[1][1] - P[1])
        out.append({"P": P, "n": n, "d": d, "way": nb[2]})
    return out


def solve(samples):
    a = b = c = r1 = r2 = 0.0
    for s in samples:
        nx, ny = s["n"]
        d = s["d"]
        a += nx * nx
        b += nx * ny
        c += ny * ny
        r1 += nx * d
        r2 += ny * d
    det = a * c - b * b
    if abs(det) < 1e-6 * max(1, len(samples)):
        return None, det
    vx = (c * r1 - b * r2) / det
    vy = (a * r2 - b * r1) / det
    return (vx, vy), det


def register(ways, groups):
    """``groups``: {window id: samples}. Returns the registration record (per window + global)."""
    res = {"per_window": {}}
    allS = []
    for k, S in groups.items():
        if len(S) < 6:
            res["per_window"][k] = {"n": len(S)}
            continue
        v, det = solve(S)
        ds = [s["d"] for s in S]
        cond = det / (len(S) ** 2)
        res["per_window"][k] = {"n": len(S), "median_cross_offset_m": round(stt.median(ds), 2),
                                "mean_abs_cross_offset_m": round(sum(abs(x) for x in ds) / len(ds), 2),
                                "v_osm_minus_paint_EN_m": [round(v[0], 2), round(v[1], 2)] if v and cond > 0.02 else None,
                                "direction_spread": round(cond, 3), "ways": sorted(set(s["way"] for s in S))}
        for s in S:
            allS.append(dict(s, w=1.0 / len(S)))
    a = b = c = r1 = r2 = 0.0
    for s in allS:
        nx, ny = s["n"]
        d = s["d"]
        w = s["w"]
        a += w * nx * nx
        b += w * nx * ny
        c += w * ny * ny
        r1 += w * nx * d
        r2 += w * ny * d
    det = a * c - b * b
    vx = (c * r1 - b * r2) / det
    vy = (a * r2 - b * r1) / det
    resid = [s["d"] - (s["n"][0] * vx + s["n"][1] * vy) for s in allS]
    res["global"] = {"v_osm_minus_paint_EN_m": [round(vx, 2), round(vy, 2)], "magnitude_m": round(math.hypot(vx, vy), 2),
                     "bearing_deg": round((math.degrees(math.atan2(vx, vy)) + 360) % 360, 1),
                     "n_points": len(allS), "n_windows": sum(1 for k, v in res["per_window"].items() if v.get("n", 0) >= 6),
                     "resid_rms_m": round(math.sqrt(sum(r * r for r in resid) / len(resid)), 2),
                     "resid_p90_abs_m": round(sorted(abs(r) for r in resid)[int(0.9 * (len(resid) - 1))], 2),
                     "raw_cross_offset_abs_median_m": round(stt.median([abs(s["d"]) for s in allS]), 2)}
    return res
