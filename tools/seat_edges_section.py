"""The fold rule for tools/seat_edges_blend.py's opt-in route.seat_edges_section (ledger 0102, Milford round 2; stdlib).

GM's inner turn is a measured bowl (route.densify.section: tools/densify_ribbon_blend.py cuts each row into ~1 m columns
and lifts them onto tools/measured_surface.py's section product), so across the lane the road folds at every column line:
at s 953 -47 / -41 / -22 / -7 % at u -2.9 / -1.9 / -0.9 m. engine-july's prep pins every TERRAIN vertex under the pavement
to the deck - 0.02 m; a grass face is flat, so over a fold between its vertices it stands as high over the road as the
road sags under the face's chord: 0.1.15's first rehearsal (milford_0115_reh, 2026-11-23) read 61 lane points of grass up
to 2.1 cm OVER the road on s 925-962 (u -2.0..+1.9; 0.85 m faces across 16-19 % folds), drive_test's soft_top 1 at s 947.

So each TERRAIN face under the road on the section's stretch (its spans, + taper_m and seat_edges_blend.PAD_M either side)
is read on a barycentric grid against the built road (ROAD and CURB, ray cast from above): the fold excess is the most the
face's chord, laid through the road's height at its own vertices (where the prep will pin them), stands over the road at
any sample. A face whose excess is over FOLD_TOL_M is cut so its legs shrink by ceil(excess / FOLD_TOL_M): a fold's excess
falls with the leg (a bend's with its square, so this cuts it at least enough). Nothing moves: the subdivision interpolates
on the faces it splits and the prep's pin seats the new vertices. Opt-in; a track without the key is untouched.
"""
from __future__ import annotations

import math

FOLD_TOL_M = 0.01   # half the prep's 0.02 m clearance, seat_edges_blend's CHORD rule (tan x leg / 4 <= 1 cm)
CLEAR_M = 0.02      # engine-july's build_kn5_loop.GROUND_CLEAR: a face whose excess is over this stands over the road
SAMPLE_N = 4        # [invented] each face read on the barycentric grid of step 1/SAMPLE_N (15 points, its corners included)
MAX_CUTS = 16       # seat_edges_blend's own cap


def stretch(route: dict, pad_m: float):
    """(s0, s1) of the line the section's rows touch, + taper_m and pad_m either side; None without the key"""
    if not route.get("seat_edges_section"):
        return None
    sec = (route.get("densify") or {}).get("section")
    if not sec or not sec.get("spans"):
        raise SystemExit("[seat-edges] route.seat_edges_section needs route.densify.section with its spans (ledger 0102)")
    taper = float(sec.get("taper_m", 15.0))
    return (min(float(a) for a, _ in sec["spans"]) - taper - pad_m,
            max(float(b) for _, b in sec["spans"]) + taper + pad_m)


def stations(points_xyz, s0: float, s1: float):
    """indices of the line's points whose plan-view station (from point 0) lies in [s0, s1]"""
    out, s = [], 0.0
    for i, p in enumerate(points_xyz):
        if i:
            q = points_xyz[i - 1]
            s += math.hypot(p[0] - q[0], p[2] - q[2])
        if s0 <= s <= s1:
            out.append(i)
    return out


def bary(n: int = SAMPLE_N):
    """the barycentric grid of step 1/n over a triangle, its corners included"""
    return [(i / n, j / n, (n - i - j) / n) for i in range(n + 1) for j in range(n + 1 - i)]


def fold_excess(corner_road, samples):
    """corner_road: the road's height under the face's three corners; samples: [(w0, w1, w2, road height there)].
    The most the chord through the corners' road heights stands over the road at a sample (<= 0: the road bulges)"""
    a, b, c = corner_road
    return max(w0 * a + w1 * b + w2 * c - h for w0, w1, w2, h in samples)


def cuts_for(excess: float, tol: float = FOLD_TOL_M) -> int:
    """cuts per edge so a fold's excess (linear in the leg) comes under tol; 0 when it already is"""
    if excess <= tol:
        return 0
    return min(MAX_CUTS, math.ceil(excess / tol) - 1)
