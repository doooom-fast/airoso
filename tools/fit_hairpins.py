"""Hairpin fit: replace each faceted hairpin of an OSM centreline with a curvature-continuous curve.

Lookout Lariat V3 plan A2 / P2 step 2 (ledger 0048, dossier section 4). The OSM hairpin ways have a node
every 4-5 m that turns 17-27 deg, and the engine's OSM path never smooths in plan (Catmull-Rom runs only
for KML, ``scripts/gps/centerline.py``), so the 3 m centreline keeps the facets: the base hairpin steps
0, 9, 17, 14, 12, 20, 9, 16, 16, 5 and 25 deg between consecutive points, where a smooth R 12 m arc would
step an even 14. A driver feels each facet as a steering jolt. This tool runs BEFORE any ribbon exists.

What it does, per declared corner (``hairpin_fit.corners`` in ``track.config.json``):

1. **Find it.** Within ``search_m`` of the declared ``st_m`` (stations from v0 of
   ``data/centerline.geojson``), the vertex whose ``window_m`` window turns most; the apex is where that
   window's turn is half done. Two declared neighbours split the line between them at its straightest
   point (the middle of the straight leg between them), which neither crosses, and a corner reaches no
   more than ``reach_m`` from its apex, so stacked hairpins never share a vertex.
2. **Measure the radius** from the centreline's own geometry: a least-squares circle (algebraic start,
   geometric refinement) through the vertices of the corner's core, the stretch between ``core[0]`` and
   ``core[1]`` of its cumulative turn. When no arc at that radius passes the step gate, the nearest
   radius that does is used, scanned outward in ``radius_step_m`` steps within ``radius_search`` x the
   measurement; failing that, the best attempt is written and the corner FAILS. A corner whose turn
   is concentrated at one vertex (a single vertex holds more than ``kink_share`` of it, or the core has
   fewer than 4 vertices) is a **kink**: the centreline has no radius there (a junction node, or one OSM
   facet), so it is left alone and reported as pending until the config gives it a radius.
   ``radius_m`` in the corner's config entry (or ``--radius ID=R``) overrides the measurement; that is the
   hook the aerial pass fills (dossier section 12). A declared corner whose window turns less than
   ``min_turn_deg`` is a stale declaration (exit 2).
3. **Fit.** Between two anchor points on the original straights either side of the corner, a clothoid
   (curvature 0 -> 1/R), an arc of radius R, and a clothoid (1/R -> 0). The curve starts on the straight
   arriving at vertex A, on its heading, and ends exactly on the straight leaving vertex B, on its
   heading, so position and heading are continuous at both joins and curvature runs 0 -> 1/R -> 0. With
   R fixed, the turn and the two end coordinates fix the three lengths (L1, Lc, L2), solved by Newton.
   Every pair of anchor vertices whose untouched neighbours are smooth enough to join is tried; around
   the three best, both ends then slide along their straights (``slide_m`` steps, then quarter steps),
   so the fit is not tied to where the 3 m resample put a vertex. The fit that passes the gate with the
   smallest lateral move from the original line wins (ties within ``tie_m``: the shorter span).
4. **Resample** the fitted span at <= ``max_spacing_m`` (1 m), evenly.
5. **Gate** (plan P2 step 2 / P5; both thresholds [invented]) on the fitted span plus ``join_margin``
   untouched vertices each side:
   - every heading change between consecutive points <= (spacing / R_fit) x 57.3 deg + ``step_slack_deg``
     (spacing = the mean of the two segments meeting at the point; the first term is the fitted arc's
     own turn per point, the slack is [invented]);
   - adjacent heading changes differ by <= ``adjacent_step_deg`` [invented].
   The lateral move from the original line (both ways: fitted points to the original polyline, original
   vertices to the fitted polyline) is REPORTED per corner and judges nothing. Where a line runs is judged
   against the road's painted centre line by ``tools/verify_centreline_paint.py`` (2026-10-11, ledger 0048):
   the former ``max_move_m`` 1.5 m-from-OSM ceiling [invented] passed fits 7.3 m and 4.4 m off the paint at
   C4 and C10 (OSM itself cuts those hairpins) and failed C9, where OSM was right. The Lariat's centreline
   is now built by ``tools/paint_centreline.py``; this tool remains the clothoid-arc-clothoid library
   (``Curve``, ``solve_transitions``, ``gate``, ``stations``, ``signed_steps``) and a corner-by-corner
   radius check.

Outputs (``--out-dir``, required; this prototype refuses to write into the track's ``data/``):
``centerline.fitted.geojson`` (the whole lap, the same schema as ``data/centerline.geojson``, with the
PASSING corners spliced in, untouched vertices copied byte-for-byte, widths carried; a failing corner's
best attempt is plotted and reported but never spliced), ``hairpin_fit.json`` (per corner: facet steps before,
radius, transitions, max step after, lateral move, gate verdict; the climb-wide facet counts before and
after; the vertex-index shift the fitted line would cause), and ``<ID>.svg`` (a before/after plot per
corner: plan view and turn-rate profile).

Exit: 0 every declared corner fitted and passing; 1 any corner FAILS (the step gate);
2 usage/config error; 3 nothing failed but some corner is pending a radius (a kink).

    python tools/fit_hairpins.py <project-dir> --out-dir <dir> [--centerline <geojson>]
                                 [--corner ID]... [--radius ID=R]... [--detect-deg 90]
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.geometry.projection import _meters_per_degree, centroid  # noqa: E402  (read-only)
from scripts.gps.centerline import polyline_length  # noqa: E402  (read-only: the route stage's length)

DEG = 180.0 / math.pi

JUDGE = ("tools/verify_centreline_paint.py: the line's position is judged against the road's traced paint, "
         "not against OSM (the 1.5 m-from-OSM ceiling was removed 2026-10-11, ledger 0048)")

DEFAULTS = {
    "max_spacing_m": 1.0,       # plan P2 step 2: resampled at <= 1 m through the corner
    "step_slack_deg": 1.0,      # [invented] plan P2 step 2 gate: the + 1 deg of slack
    "adjacent_step_deg": 1.5,   # [invented] plan P2 step 2 gate
    "join_margin": 2,           # [invented] untouched original vertices each side that the gate also checks
    "window_m": 60.0,           # [invented] apex finder: turn summed over this window
    "search_m": 40.0,           # [invented] apex searched within this of the declared station
    "reach_m": 60.0,            # [invented] an anchor sits at most this far (along the line) from the apex
    "core": [0.2, 0.8],         # [invented] the measured core: this fraction of the corner's turn
    "kink_share": 0.5,          # [invented] one vertex holding more than this share of the turn = a kink
    "tie_m": 0.05,              # [invented] lateral moves within this are a tie; the shorter span wins
    "radius_search": [0.7, 1.3],  # [invented] a failing corner's radius is re-tried within this x the measured
    "radius_step_m": 0.25,      # the re-try scan's resolution (not a threshold)
    "slide_m": 1.0,             # anchor slide along the straights: search resolution, not a threshold
    "climb_st_m": None,         # optional [from, to] station range for the climb-wide facet counts
    "min_turn_deg": 45.0,       # [invented] a declared corner whose window turns less is a stale declaration
}


# --------------------------------------------------------------------------------------------------
# geometry helpers (local plan metres, x = east, y = north)
# --------------------------------------------------------------------------------------------------
def _wrap(a: float) -> float:
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def heading(a, b) -> float:
    return math.atan2(b[1] - a[1], b[0] - a[0])


def signed_steps(pts) -> list[float]:
    """Signed heading change (radians, + = left) at every vertex; 0 at the two ends."""
    n = len(pts)
    out = [0.0] * n
    for i in range(1, n - 1):
        out[i] = _wrap(heading(pts[i], pts[i + 1]) - heading(pts[i - 1], pts[i]))
    return out


def stations(pts) -> list[float]:
    st = [0.0]
    for i in range(1, len(pts)):
        st.append(st[-1] + math.dist(pts[i - 1], pts[i]))
    return st


def _seg_dist(p, a, b) -> float:
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    L2 = dx * dx + dy * dy
    if L2 <= 0.0:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def dist_to_polyline(p, poly) -> float:
    return min(_seg_dist(p, poly[i], poly[i + 1]) for i in range(len(poly) - 1))


def circle_fit(pts) -> tuple[float, float, float, float]:
    """Least-squares circle (cx, cy, R, rms residual): Kasa algebraic fit, then Gauss-Newton on the
    geometric distance."""
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    q = [(p[0] - mx, p[1] - my) for p in pts]
    # minimise sum (x^2 + y^2 + D x + E y + F)^2  ->  3x3 normal equations
    Sxx = sum(x * x for x, _ in q)
    Syy = sum(y * y for _, y in q)
    Sxy = sum(x * y for x, y in q)
    Sx = sum(x for x, _ in q)
    Sy = sum(y for _, y in q)
    Sz = [x * x + y * y for x, y in q]
    b = [-sum(z * x for z, (x, _) in zip(Sz, q)), -sum(z * y for z, (_, y) in zip(Sz, q)), -sum(Sz)]
    M = [[Sxx, Sxy, Sx], [Sxy, Syy, Sy], [Sx, Sy, float(n)]]
    D, E, F = _solve3(M, b)
    cx, cy = -D / 2.0, -E / 2.0
    R = math.sqrt(max(cx * cx + cy * cy - F, 1e-12))
    for _ in range(50):  # geometric refinement
        JtJ = [[0.0] * 3 for _ in range(3)]
        Jtr = [0.0] * 3
        for x, y in q:
            d = math.hypot(x - cx, y - cy) or 1e-12
            r = d - R
            J = ((cx - x) / d, (cy - y) / d, -1.0)
            for i in range(3):
                Jtr[i] += J[i] * r
                for j in range(3):
                    JtJ[i][j] += J[i] * J[j]
        try:
            dcx, dcy, dR = _solve3(JtJ, [-v for v in Jtr])
        except ZeroDivisionError:
            break
        cx, cy, R = cx + dcx, cy + dcy, R + dR
        if abs(dcx) + abs(dcy) + abs(dR) < 1e-10:
            break
    rms = math.sqrt(sum((math.hypot(x - cx, y - cy) - R) ** 2 for x, y in q) / n)
    return cx + mx, cy + my, abs(R), rms


def _solve3(M, b):
    """Gaussian elimination with partial pivoting for a 3x3 system."""
    A = [list(M[i]) + [b[i]] for i in range(3)]
    for c in range(3):
        p = max(range(c, 3), key=lambda r: abs(A[r][c]))
        if abs(A[p][c]) < 1e-14:
            raise ZeroDivisionError("singular")
        A[c], A[p] = A[p], A[c]
        for r in range(c + 1, 3):
            f = A[r][c] / A[c][c]
            for k in range(c, 4):
                A[r][k] -= f * A[c][k]
    x = [0.0] * 3
    for r in (2, 1, 0):
        x[r] = (A[r][3] - sum(A[r][k] * x[k] for k in range(r + 1, 3))) / A[r][r]
    return x


# --------------------------------------------------------------------------------------------------
# the curve: clothoid (0 -> 1/R), arc (1/R), clothoid (1/R -> 0)
# --------------------------------------------------------------------------------------------------
def _gauss_legendre(n: int):
    xs, ws = [], []
    for i in range(1, n + 1):
        x = math.cos(math.pi * (i - 0.25) / (n + 0.5))
        for _ in range(100):
            p0, p1 = 1.0, x
            for k in range(2, n + 1):
                p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
            dp = n * (x * p1 - p0) / (x * x - 1.0)
            dx = p1 / dp
            x -= dx
            if abs(dx) < 1e-15:
                break
        p0, p1 = 1.0, x
        for k in range(2, n + 1):
            p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
        dp = n * (x * p1 - p0) / (x * x - 1.0)
        xs.append(x)
        ws.append(2.0 / ((1.0 - x * x) * dp * dp))
    return xs, ws


_GL_X, _GL_W = _gauss_legendre(10)


def piece_at(x, y, th, L, k0, k1, s):
    """(x, y, heading) after travelling s (0 <= s <= L) along a piece whose curvature runs linearly
    from k0 to k1 over its length L. Arcs and straights in closed form, clothoids by Gauss-Legendre."""
    if s == 0.0:
        return x, y, th
    dk = (k1 - k0) / L if L > 0 else 0.0
    th_s = th + k0 * s + 0.5 * dk * s * s
    if abs(dk) < 1e-15:
        if abs(k0) < 1e-12:
            return x + s * math.cos(th), y + s * math.sin(th), th_s
        return x + (math.sin(th_s) - math.sin(th)) / k0, y + (math.cos(th) - math.cos(th_s)) / k0, th_s
    turn = abs(k0 * s) + abs(0.5 * dk * s * s)
    m = 1 + int(turn / 0.5)
    h = s / m
    cx = cy = 0.0
    for j in range(m):
        a = j * h
        for gx, gw in zip(_GL_X, _GL_W):
            u = a + 0.5 * h * (gx + 1.0)
            t = th + k0 * u + 0.5 * dk * u * u
            cx += 0.5 * h * gw * math.cos(t)
            cy += 0.5 * h * gw * math.sin(t)
    return x + cx, y + cy, th_s


@dataclass
class Curve:
    x0: float
    y0: float
    th0: float
    sign: int
    R: float
    L1: float
    Lc: float
    L2: float

    @property
    def length(self) -> float:
        return self.L1 + self.Lc + self.L2

    def pieces(self):
        kc = self.sign / self.R
        return [(self.L1, 0.0, kc), (self.Lc, kc, kc), (self.L2, kc, 0.0)]

    def at(self, s: float):
        x, y, th = self.x0, self.y0, self.th0
        pcs = self.pieces()
        for idx, (L, k0, k1) in enumerate(pcs):
            if s <= L or idx == len(pcs) - 1:
                return piece_at(x, y, th, L, k0, k1, min(max(s, 0.0), L))
            x, y, th = piece_at(x, y, th, L, k0, k1, L)
            s -= L
        return x, y, th

    def end(self):
        x, y, th = self.x0, self.y0, self.th0
        for L, k0, k1 in self.pieces():
            x, y, th = piece_at(x, y, th, L, k0, k1, L)
        return x, y, th

    def sample(self, max_spacing: float):
        """Interior points at an even spacing <= max_spacing (the two ends are the anchors)."""
        n = max(2, math.ceil(self.length / max_spacing - 1e-9))
        ds = self.length / n
        return [self.at(k * ds)[:2] for k in range(1, n)], ds

    def centre(self):
        """Centre of the fitted arc."""
        x, y, th = piece_at(self.x0, self.y0, self.th0, self.L1, 0.0, self.sign / self.R, self.L1)
        return (x - self.sign * self.R * math.sin(th), y + self.sign * self.R * math.cos(th))


def solve_transitions(A, thA, B, delta, R, min_len=0.1, warm=None):
    """Clothoid lengths (L1, Lc, L2) such that the curve from A on heading thA, turning ``delta``
    radians at radius R, ends exactly at B. None when no such curve exists (or Newton fails).
    ``warm`` = an (L1, L2) guess tried first (the same anchors' solution at a nearby radius)."""
    sign = 1 if delta > 0 else -1
    Leff = abs(delta) * R  # = L1/2 + Lc + L2/2 (the turn is fixed by the anchors)

    def resid(L1, L2):
        c = Curve(A[0], A[1], thA, sign, R, L1, Leff - 0.5 * (L1 + L2), L2)
        x, y, _ = c.end()
        return x - B[0], y - B[1]

    starts = [(f1 * Leff, f2 * Leff) for f1, f2 in
              ((0.3, 0.3), (0.15, 0.15), (0.5, 0.5), (0.2, 0.6), (0.6, 0.2), (0.05, 0.05), (0.8, 0.8))]
    if warm:
        starts.insert(0, warm)
    for L1, L2 in starts:
        r = resid(L1, L2)
        nr = math.hypot(*r)
        ok = False
        for _ in range(40):
            if nr < 1e-7:
                ok = True
                break
            h = 1e-6 * max(1.0, Leff)
            ra = resid(L1 + h, L2)
            rb = resid(L1, L2 + h)
            j11, j21 = (ra[0] - r[0]) / h, (ra[1] - r[1]) / h
            j12, j22 = (rb[0] - r[0]) / h, (rb[1] - r[1]) / h
            det = j11 * j22 - j12 * j21
            if abs(det) < 1e-12:
                break
            d1 = (j22 * r[0] - j12 * r[1]) / det
            d2 = (-j21 * r[0] + j11 * r[1]) / det
            t = 1.0
            improved = False
            while t > 1e-4:
                n1 = min(max(1e-3, L1 - t * d1), 2.0 * Leff)
                n2 = min(max(1e-3, L2 - t * d2), 2.0 * Leff)
                rn = resid(n1, n2)
                if math.hypot(*rn) < nr:
                    L1, L2, r, nr = n1, n2, rn, math.hypot(*rn)
                    improved = True
                    break
                t *= 0.5
            if not improved:
                break
        Lc = Leff - 0.5 * (L1 + L2)
        if ok and L1 >= min_len and L2 >= min_len and Lc >= 0.0:
            return L1, Lc, L2
    return None


# --------------------------------------------------------------------------------------------------
# the gate
# --------------------------------------------------------------------------------------------------
def gate(pts, lo: int, hi: int, R: float, slack_deg: float, adj_deg: float) -> dict:
    """Heading-step gate on vertices lo..hi of ``pts`` (plan P2 step 2): |step| <= mean spacing / R x
    57.3 + slack, and |step_k - step_k-1| <= adj for k in lo+1..hi. Steps in degrees."""
    lo = max(1, lo)
    hi = min(len(pts) - 2, hi)
    fails = []
    max_step = max_ratio = max_adj = 0.0
    prev = None
    for k in range(lo, hi + 1):
        stp = _wrap(heading(pts[k], pts[k + 1]) - heading(pts[k - 1], pts[k])) * DEG
        sp = 0.5 * (math.dist(pts[k - 1], pts[k]) + math.dist(pts[k], pts[k + 1]))
        lim = sp / R * DEG + slack_deg
        max_step = max(max_step, abs(stp))
        max_ratio = max(max_ratio, abs(stp) / lim)
        if abs(stp) > lim:
            fails.append({"v": k, "rule": "step", "step_deg": round(stp, 2), "limit_deg": round(lim, 2)})
        if prev is not None:
            d = abs(stp - prev)
            max_adj = max(max_adj, d)
            if d > adj_deg:
                fails.append({"v": k, "rule": "adjacent", "diff_deg": round(d, 2), "limit_deg": adj_deg})
        prev = stp
    return {"pass": not fails, "fails": fails, "max_step_deg": max_step, "max_ratio": max_ratio,
            "max_adjacent_diff_deg": max_adj}


# --------------------------------------------------------------------------------------------------
# corners
# --------------------------------------------------------------------------------------------------
def windowed_turn(st, S, i, half_m):
    j0 = j1 = i
    n = len(S)
    while j0 > 1 and st[i] - st[j0 - 1] <= half_m:
        j0 -= 1
    while j1 < n - 2 and st[j1 + 1] - st[i] <= half_m:
        j1 += 1
    return sum(S[j0:j1 + 1])


def find_apex(st, S, st_m, prm) -> tuple[int, float]:
    cand = [i for i in range(1, len(S) - 1) if abs(st[i] - st_m) <= prm["search_m"]]
    if not cand:
        raise ValueError(f"no vertex within {prm['search_m']} m of st {st_m}")
    half = prm["window_m"] / 2.0
    best = max(cand, key=lambda i: abs(windowed_turn(st, S, i, half)))
    total = windowed_turn(st, S, best, half)
    # Many vertices see the whole turn inside their window (a kink is seen from 30 m either side);
    # the apex is where that window's turn is half done.
    lo = hi = best
    while lo > 1 and st[best] - st[lo - 1] <= half:
        lo -= 1
    while hi < len(S) - 2 and st[hi + 1] - st[best] <= half:
        hi += 1
    cum = 0.0
    for k in range(lo, hi + 1):
        cum += S[k]
        if abs(cum) >= 0.5 * abs(total) and cum * total > 0:
            return k, total
    return best, total


def split_between(st, S, i: int, j: int, half_m: float = 6.0) -> int:
    """The vertex between apexes i and j where the line is straightest: least turn within +/- half_m,
    and among equals the middle one of them (the middle of the straight leg). Two corners never
    reach past it."""
    if j - i < 2:
        return i
    turn = {k: round(abs(windowed_turn(st, S, k, half_m)), 6) for k in range(i + 1, j)}
    least = min(turn.values())
    flat = [k for k in sorted(turn) if turn[k] == least]
    return flat[len(flat) // 2]


def measure_radius(P, S, lo, hi, prm) -> dict:
    """Circle fit through the core of the turn between vertices lo..hi."""
    total = sum(S[lo:hi + 1])
    sign = 1 if total > 0 else -1
    f0, f1 = prm["core"]
    cum = 0.0
    k0 = k1 = None
    for k in range(lo, hi + 1):
        cum += S[k] * sign
        if k0 is None and cum >= f0 * abs(total):
            k0 = k
        if k1 is None and cum >= f1 * abs(total):
            k1 = k
            break
    k0 = lo if k0 is None else k0
    k1 = hi if k1 is None else k1
    biggest = max(range(lo, hi + 1), key=lambda k: abs(S[k]))
    share = abs(S[biggest]) / abs(total) if total else 1.0
    out = {"turn_deg": round(total * DEG, 1), "sign": sign, "core_v": [k0, k1],
           "biggest_step_deg": round(S[biggest] * DEG, 1), "biggest_step_v": biggest,
           "biggest_share": round(share, 2)}
    if share > prm["kink_share"] or k1 - k0 + 1 < 4:
        out.update(kind="kink", radius_m=None,
                   why=(f"one vertex (v{biggest}) holds {share:.0%} of the turn" if share > prm["kink_share"]
                        else f"the core has {k1 - k0 + 1} vertices"))
        return out
    cx, cy, R, rms = circle_fit(P[k0:k1 + 1])
    core_len = sum(math.dist(P[k], P[k + 1]) for k in range(k0, k1))
    core_turn = abs(sum(S[k0 + 1:k1 + 1]))
    out.update(kind="hairpin", radius_m=R, circle_rms_m=rms, centre=(cx, cy),
               radius_turn_rate_m=(core_len / core_turn) if core_turn else None)
    return out


def _clean_left(S, k, m, adj):
    """True when the untouched line ending at anchor k can join a curve that starts with ~0 step."""
    if k - m < 1:
        return False
    if abs(S[k - 1]) * DEG > adj:
        return False
    return all(abs(S[j] - S[j - 1]) * DEG <= adj for j in range(k - m + 1, k))


def _clean_right(S, k, m, adj):
    n = len(S)
    if k + m > n - 2:
        return False
    if abs(S[k + 1]) * DEG > adj:
        return False
    return all(abs(S[j] - S[j - 1]) * DEG <= adj for j in range(k + 2, k + m + 1))


@dataclass
class Fit:
    """One candidate fit. The curve starts on the straight segment arriving at vertex A, ``a`` metres
    before A (a <= 0), and ends on the segment leaving vertex B, ``b`` metres after B (b >= 0); both
    ends lie on the original line, so position and heading are continuous at the joins. ``pts`` =
    [start] + interior points + [end] replaces vertices A..B inclusive (start is P[A] itself when
    a == 0, end is P[B] when b == 0)."""
    key: tuple
    A: int
    a: float
    B: int
    b: float
    delta: float
    curve: Curve
    pts: list
    ds: float
    gate: dict
    move: float
    where: tuple


def _evaluate(P, st, S, A, a, B, b, R, prm, warm, bar):
    """Fit one anchor candidate at radius R. None when no curve exists, or when it cannot beat ``bar``
    (a Fit; the distance work is skipped or abandoned as soon as that is certain)."""
    m, adj = int(prm["join_margin"]), float(prm["adjacent_step_deg"])
    delta = sum(S[A:B + 1])
    thA = heading(P[A - 1], P[A])
    thB = heading(P[B], P[B + 1])
    start = P[A] if a == 0.0 else (P[A][0] + a * math.cos(thA), P[A][1] + a * math.sin(thA))
    end = P[B] if b == 0.0 else (P[B][0] + b * math.cos(thB), P[B][1] + b * math.sin(thB))
    sol = solve_transitions(start, thA, end, delta, R, warm=warm.get((A, B)))
    if sol is None:
        return None
    L1, Lc, L2 = sol
    warm[(A, B)] = (L1, L2)
    curve = Curve(start[0], start[1], thA, 1 if delta > 0 else -1, R, L1, Lc, L2)
    inner, ds = curve.sample(prm["max_spacing_m"])
    pts = [start] + inner + [end]
    new = P[A - m - 1:A] + pts + P[B + 1:B + m + 2]
    g = gate(new, 1, len(new) - 2, R, prm["step_slack_deg"], adj)
    head = (0 if g["pass"] else 1, len(g["fails"]))
    abandon = None
    if bar is not None:
        if head > bar.key[:2]:
            return None  # a worse gate verdict can never win: skip the distance work
        if head == bar.key[:2]:
            abandon = (bar.key[2] + 0.5) * prm["tie_m"]
    mv = lateral_move(P, A, B, pts, abandon)
    if mv is None:
        return None
    move, where = mv
    key = head + (round(move / prm["tie_m"]), (st[B] + b) - (st[A] + a))
    return Fit(key, A, a, B, b, delta, curve, pts, ds, g, move, where)


def _anchor_search(P, st, S, As, Bs, R, sign, prm, warm):
    """Best fit at radius R (or None) and [pairs tried, pairs solved].

    Coarse: every pair of clean anchor vertices. Fine: around the three best pairs, both ends slide
    along the original straights (a 5 x 5 grid of ``slide_m`` steps, then of a quarter of that about
    the best), so the fit is not tied to where the 3 m resample happened to put a vertex.
    ``warm`` maps (A, B) -> (L1, L2), the last solution for that pair, and is updated in place."""
    stats = [0, 0]
    top: list = []
    for A in As:
        for B in Bs:
            if sum(S[A:B + 1]) * sign <= 0:
                continue
            stats[0] += 1
            f = _evaluate(P, st, S, A, 0.0, B, 0.0, R, prm, warm, top[-1] if len(top) == 3 else None)
            if f is None:
                continue
            stats[1] += 1
            top = sorted(top + [f], key=lambda x: x.key)[:3]
    if not top:
        return None, stats
    best = top[0]
    As_set, Bs_set = set(As), set(Bs)
    n = len(P)

    def place(sA, sB):
        """(A, a, B, b) for anchor stations sA, sB; None when an end leaves the clean straights."""
        A = bisect.bisect_left(st, sA - 1e-9)
        B = bisect.bisect_right(st, sB + 1e-9) - 1
        if not (1 <= A < B - 1 < n - 2) or A not in As_set or B not in Bs_set:
            return None
        a = 0.0 if abs(sA - st[A]) < 1e-9 else sA - st[A]
        b = 0.0 if abs(sB - st[B]) < 1e-9 else sB - st[B]
        if a < -0.95 * math.dist(P[A - 1], P[A]) or b > 0.95 * math.dist(P[B], P[B + 1]):
            return None
        return A, a, B, b

    step = float(prm["slide_m"])
    seen = set()
    for parent in list(top):
        local = parent
        for scale in (step, step / 4.0):
            cA, cB = st[local.A] + local.a, st[local.B] + local.b
            for i in (-2, -1, 0, 1, 2):
                for j in (-2, -1, 0, 1, 2):
                    sA, sB = cA + i * scale, cB + j * scale
                    tag = (round(sA, 3), round(sB, 3))
                    if tag in seen:
                        continue
                    seen.add(tag)
                    pl = place(sA, sB)
                    if pl is None:
                        continue
                    f = _evaluate(P, st, S, *pl, R, prm, warm, best)
                    if f is not None and f.key < best.key:
                        best = local = f
    return best, stats


def lateral_move(P, A, B, pts, abandon_at=None):
    """Largest sideways distance between a fitted span and the original line, both ways: fitted points
    to the original polyline (A-1..B+1) and original vertices A..B to the fitted polyline.
    Returns (metres, where) or None as soon as it exceeds ``abandon_at``."""
    orig = P[A - 1:B + 2]
    worst, where = -1.0, None
    for p in pts[1:-1]:
        d = dist_to_polyline(p, orig)
        if d > worst:
            worst, where = d, p
            if abandon_at is not None and worst > abandon_at:
                return None
    for k in range(A, B + 1):
        d = dist_to_polyline(P[k], pts)
        if d > worst:
            worst, where = d, P[k]
            if abandon_at is not None and worst > abandon_at:
                return None
    return worst, where


def fit_corner(P, st, S, corner: dict, lim: tuple[int, int], prm: dict) -> dict:
    apex, wturn = corner["_apex"], corner["_wturn"]
    lo, hi = lim
    res = {"id": corner["id"], "name": corner.get("name", ""), "declared_st_m": corner["st_m"],
           "apex_v": apex, "apex_st_m": round(st[apex], 1), "window_turn_deg": round(wturn * DEG, 1),
           "search_v": [lo, hi]}
    meas = measure_radius(P, S, lo, hi, prm)
    res["measured"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in meas.items()
                       if k != "centre"}
    fixed = corner.get("radius_m")
    if fixed is None and meas.get("radius_m") is None:
        res.update(status="PENDING", radius_source="none",
                   why=(f"kink ({meas['why']}): the centreline has no radius here; "
                        "set hairpin_fit.corners[].radius_m from the aerial"))
        return res
    m, adj = int(prm["join_margin"]), float(prm["adjacent_step_deg"])
    span = corner.get("span_st_m")
    if span:
        As = [min(range(lo, apex), key=lambda k: abs(st[k] - span[0]))]
        Bs = [min(range(apex + 1, hi + 1), key=lambda k: abs(st[k] - span[1]))]
    else:
        As = [k for k in range(lo, apex - 1) if _clean_left(S, k, m, adj)]
        Bs = [k for k in range(apex + 2, hi + 1) if _clean_right(S, k, m, adj)]
    warm: dict = {}
    tried: dict = {}

    def at_radius(R):
        R = round(R, 2)
        if R not in tried:
            tried[R] = _anchor_search(P, st, S, As, Bs, R, meas["sign"], prm, warm)
        return tried[R][0]

    def ok(f):
        return f is not None and f.gate["pass"]

    if fixed is not None:
        R_best = round(float(fixed), 2)
        best = at_radius(R_best)
        res["radius_source"] = corner.get("_radius_src", "config: hairpin_fit.corners[].radius_m")
        res["radius_kind"] = "override"
    else:
        # The radius measured from the centreline: the circle through the core of the turn. When no
        # arc of that radius passes the step gate, the nearest radius that does is used instead,
        # scanned outward from the measurement; failing that, the best attempt.
        Rc = round(meas["radius_m"], 2)
        f0, f1 = prm["radius_search"]
        step = float(prm["radius_step_m"])
        R_best, best = Rc, at_radius(Rc)
        kind, how = "measured", "measured: circle fit through the core of the turn"
        if not ok(best):
            scan = []
            for i in range(1, int(Rc * max(1.0 - f0, f1 - 1.0) / step) + 1):
                for R in (Rc - i * step, Rc + i * step):
                    if Rc * f0 <= R <= Rc * f1:
                        scan.append(round(R, 2))
            hit = next((R for R in scan if ok(at_radius(R))), None)
            if hit is not None:
                R_best, best = hit, at_radius(hit)
                kind = "adjusted"
                how = (f"adjusted from the measured {Rc:.2f} m (core circle fit) to the nearest radius "
                       f"that passes the step gate")
            else:
                pool = [(R, at_radius(R)) for R in [Rc] + scan]
                pool = [(R, f) for R, f in pool if f is not None]
                if pool:
                    R_best, best = min(pool, key=lambda rf: (rf[1].key[0], rf[1].key[1], round(rf[1].move, 2),
                                                             abs(rf[0] - Rc)))
                    kind = "best-attempt"
                    how = (f"best attempt: no radius within {f0:g}-{f1:g} x the measured {Rc:.2f} m "
                           f"passes the step gate; smallest move shown")
        res["radius_source"] = how
        res["radius_kind"] = kind
        res["radius_search"] = {"measured_core_circle_m": Rc, "radii_tried": len(tried),
                                "range_m": [round(Rc * f0, 2), round(Rc * f1, 2)], "step_m": step}
    R = R_best
    stats = tried[R][1]
    res["anchors_tried"] = {"A": len(As), "B": len(Bs), "pairs": stats[0], "solved": stats[1]}
    if best is None:
        if not As or not Bs:
            side = "entry" if not As else "exit"
            why = (f"no smooth stretch to join on the {side} side within reach_m of the apex "
                   "(every candidate anchor sits next to a facet)")
        else:
            why = f"no anchor pair admits a clothoid-arc-clothoid at R {R} m"
        res.update(status="FAIL", why=why)
        return res
    A, B, curve = best.A, best.B, best.curve
    before = [S[k] * DEG for k in range(A, B + 1)]
    spac = [0.5 * (math.dist(P[k - 1], P[k]) + math.dist(P[k], P[k + 1])) for k in range(A, B + 1)]
    g_before = gate(P, A - m, B + m, R, prm["step_slack_deg"], adj)
    g = best.gate
    res.update({
        "radius_fit_m": R,
        "turn_deg": round(best.delta * DEG, 1),
        "span": {"v": [A, B], "slide_m": [round(best.a, 2), round(best.b, 2)],
                 "st_m": [round(st[A] + best.a, 1), round(st[B] + best.b, 1)],
                 "original_len_m": round((st[B] + best.b) - (st[A] + best.a), 1),
                 "fitted_len_m": round(curve.length, 1),
                 "replaced_points": B - A + 1, "new_points": len(best.pts)},
        "transitions_m": {"L1": round(curve.L1, 1), "arc": round(curve.Lc, 1), "L2": round(curve.L2, 1)},
        "before": {"steps_deg": [round(x, 1) for x in before],
                   "max_step_deg": round(max(abs(x) for x in before), 1),
                   "max_turn_rate_deg_per_m": round(max(abs(x) / s for x, s in zip(before, spac)), 2),
                   "steps_ge_10deg": sum(1 for x in before if abs(x) >= 10.0),
                   "max_adjacent_diff_deg": round(g_before["max_adjacent_diff_deg"], 1),
                   "gate_fails": len(g_before["fails"])},
        "after": {"spacing_m": round(best.ds, 3), "max_step_deg": round(g["max_step_deg"], 2),
                  "arc_step_deg": round(best.ds / R * DEG, 2),
                  "step_limit_deg": round(best.ds / R * DEG + prm["step_slack_deg"], 2),
                  "max_turn_rate_deg_per_m": round(DEG / R, 2),
                  "max_adjacent_diff_deg": round(g["max_adjacent_diff_deg"], 2),
                  "gate_fails": g["fails"]},
        "lateral_move_m": {"max": round(best.move, 2), "at": best.where, "judged_by": JUDGE},
        "_fit": best,
    })
    res["gate"] = "PASS" if g["pass"] else "FAIL"
    res["status"] = "PASS" if g["pass"] else "FAIL"
    if not g["pass"]:
        res["why"] = f"{len(g['fails'])} gate failure(s) at the best anchors"
    return res


def detect_corners(st, S, min_deg, window_m, st_range=None):
    """Every windowed turn >= min_deg (local maxima, separated by half a window)."""
    half = window_m / 2.0
    T = [windowed_turn(st, S, i, half) if (st_range is None or st_range[0] <= st[i] <= st_range[1]) else 0.0
         for i in range(len(S))]
    peaks = []
    for i, t in enumerate(T):
        if abs(t) * DEG < min_deg:
            continue
        if peaks and st[i] - st[peaks[-1]] < half:
            if abs(t) > abs(T[peaks[-1]]):
                peaks[-1] = i
        else:
            peaks.append(i)
    return [(i, T[i]) for i in peaks]


# --------------------------------------------------------------------------------------------------
# I/O
# --------------------------------------------------------------------------------------------------
def load_feature(path: Path) -> tuple[dict, dict, int]:
    gj = json.loads(Path(path).read_text(encoding="utf-8"))
    feats = gj.get("features", [])
    idx = next((i for i, f in enumerate(feats) if (f.get("properties") or {}).get("kind") == "full"), None)
    if idx is None:
        idx = next((i for i, f in enumerate(feats) if (f.get("geometry") or {}).get("type") == "LineString"),
                   None)
    if idx is None:
        raise SystemExit(f"[hairpins] no centreline LineString in {path}")
    return gj, feats[idx], idx


def corners_from_config(cfg: dict) -> tuple[list[dict], dict]:
    block = cfg.get("hairpin_fit") or {}
    prm = dict(DEFAULTS)
    for k in DEFAULTS:
        if k in block:
            prm[k] = block[k]
    for k, v in (block.get("gate") or {}).items():
        if k in ("step_slack_deg", "adjacent_step_deg"):
            prm[k] = v
    corners = [dict(c) for c in block.get("corners") or []]
    for c in corners:
        if "id" not in c or "st_m" not in c:
            raise SystemExit(f"[hairpins] hairpin_fit.corners entry needs id and st_m: {c}")
    return corners, prm


def run(project_dir: Path, out_dir: Path, centerline: Path | None = None, only: list[str] | None = None,
        radius_cli: dict | None = None, detect_deg: float | None = 90.0, prm_over: dict | None = None,
        corners: list[dict] | None = None) -> dict:
    project_dir = Path(project_dir).resolve()
    out_dir = Path(out_dir).resolve()
    data_dir = project_dir / "data"
    if out_dir == data_dir or data_dir in out_dir.parents:
        raise SystemExit(f"[hairpins] refusing to write into {data_dir}: this prototype writes only to "
                         "--out-dir outside the track's data (the fitted line replaces data/ in P2)")
    cfg = json.loads((project_dir / "track.config.json").read_text(encoding="utf-8"))
    cfg_corners, prm = corners_from_config(cfg)
    corners = [dict(c) for c in (cfg_corners if corners is None else corners)]
    if prm_over:
        prm.update(prm_over)
    if not corners:
        raise SystemExit("[hairpins] no corners declared (hairpin_fit.corners in track.config.json)")
    ids = [c["id"] for c in corners]
    if len(set(ids)) != len(ids):
        raise SystemExit(f"[hairpins] duplicate corner ids: {ids}")
    for cid, R in (radius_cli or {}).items():
        hit = [c for c in corners if c["id"] == cid]
        if not hit:
            raise SystemExit(f"[hairpins] --radius names an undeclared corner {cid}")
        hit[0]["radius_m"] = float(R)
        hit[0]["_radius_src"] = "command line --radius (experiment; not in config)"
    cl_path = Path(centerline) if centerline else data_dir / "centerline.geojson"
    gj, feat, fidx = load_feature(cl_path)
    lonlat = [(float(c[0]), float(c[1])) for c in feat["geometry"]["coordinates"]]
    lon0, lat0 = centroid(lonlat)
    mlon, mlat = _meters_per_degree(lat0)
    P = [((lo - lon0) * mlon, (la - lat0) * mlat) for lo, la in lonlat]
    st = stations(P)
    S = signed_steps(P)
    n = len(P)

    # apexes first, then each corner's share of the line
    for c in corners:
        try:
            c["_apex"], c["_wturn"] = find_apex(st, S, float(c["st_m"]), prm)
        except ValueError as e:
            raise SystemExit(f"[hairpins] {c['id']}: {e}")
        if abs(c["_wturn"]) * DEG < prm["min_turn_deg"]:
            raise SystemExit(f"[hairpins] {c['id']}: the line turns only {abs(c['_wturn']) * DEG:.0f} deg within "
                             f"{prm['search_m']:g} m of st {c['st_m']}; the corner list no longer matches the "
                             "centreline (re-derive hairpin_fit.corners[].st_m)")
    order = sorted(corners, key=lambda c: c["_apex"])
    for a, b in zip(order, order[1:]):
        if a["_apex"] == b["_apex"]:
            raise SystemExit(f"[hairpins] {a['id']} and {b['id']} resolve to the same apex v{a['_apex']}")
    m = int(prm["join_margin"])
    results = []
    # Neighbouring corners split the line between them at its straightest point; the split vertex
    # itself stays untouched. (The joined line is re-gated after splicing.)
    splits = [split_between(st, S, a["_apex"], b["_apex"]) for a, b in zip(order, order[1:])]
    for j, c in enumerate(order):
        lo_st = st[c["_apex"]] - prm["reach_m"]
        hi_st = st[c["_apex"]] + prm["reach_m"]
        lo = bisect.bisect_left(st, lo_st)
        hi = bisect.bisect_right(st, hi_st) - 1
        if j > 0:
            lo = max(lo, splits[j - 1] + 1)
        if j + 1 < len(order):
            hi = min(hi, splits[j] - 1)
        c["_limits_v"] = [lo, hi]
        if lo < m + 2 or hi > n - m - 3:
            raise SystemExit(f"[hairpins] {c['id']} reaches the lap seam (v0 / v{n - 1}); a fit across the "
                             "closing vertex is not supported (L13): move the start or narrow reach_m")
        if only and c["id"] not in only:
            continue
        results.append(fit_corner(P, st, S, c, (lo, hi), prm))

    # splice: untouched vertices are copied byte-for-byte; spans in increasing order
    # only PASSING corners go into the fitted line; a failing corner's best attempt is plotted and
    # reported, never spliced (a human decides it)
    fitted = [r for r in results if "_fit" in r and r["status"] == "PASS"]
    fitted.sort(key=lambda r: r["_fit"].A)
    out_ll, out_P, out_w, src_index = [], [], [], []
    widths = list((feat.get("properties") or {}).get("widths_m") or [])
    coords = feat["geometry"]["coordinates"]
    cursor = 0
    shift = []
    for r in fitted:
        f = r["_fit"]
        A, B = f.A, f.B
        for k in range(cursor, A):
            out_ll.append(coords[k]); out_P.append(P[k]); src_index.append(k)
            if widths:
                out_w.append(widths[k])
        first = len(out_ll)
        acc, prev, Ln = 0.0, f.pts[0], max(f.curve.length, 1e-9)
        for i, q in enumerate(f.pts):
            if i == 0 and f.a == 0.0:  # the start is vertex A itself: keep its bytes
                out_ll.append(coords[A]); src_index.append(A)
            elif i == len(f.pts) - 1 and f.b == 0.0:  # the end is vertex B itself
                out_ll.append(coords[B]); src_index.append(B)
            else:
                out_ll.append([lon0 + q[0] / mlon, lat0 + q[1] / mlat]); src_index.append(None)
            out_P.append(q)
            if widths:
                acc += math.dist(prev, q)
                out_w.append(round(widths[A] + min(acc / Ln, 1.0) * (widths[B] - widths[A]), 2))
            prev = q
        r["fitted_v"] = [first, len(out_ll) - 1]
        shift.append({"from_v": B, "add": len(f.pts) - (B - A + 1)})
        cursor = B + 1
    for k in range(cursor, n):
        out_ll.append(coords[k]); out_P.append(P[k]); src_index.append(k)
        if widths:
            out_w.append(widths[k])

    # the joined line, re-gated: each spliced span plus join_margin points either side, as written
    for r in fitted:
        a, b = r["fitted_v"]
        g = gate(out_P, a - m, b + m, r["radius_fit_m"], prm["step_slack_deg"], prm["adjacent_step_deg"])
        r["final_gate"] = {"pass": g["pass"], "max_step_deg": round(g["max_step_deg"], 2),
                           "max_adjacent_diff_deg": round(g["max_adjacent_diff_deg"], 2), "fails": g["fails"]}
        if not g["pass"]:  # never expected: the per-corner gate already covered these points
            r["status"] = "FAIL"
            r["why"] = f"the joined line fails the gate ({len(g['fails'])} point(s)) although spliced"

    # climb-wide counts before / after
    climb = prm.get("climb_st_m")
    S2 = signed_steps(out_P)
    st2 = stations(out_P)

    def counts(SS, stt, rng, src=None):
        sel = [i for i in range(1, len(SS) - 1) if rng is None or rng[0] <= stt[i] <= rng[1]]
        big = [i for i in sel if abs(SS[i]) * DEG >= 10.0]
        return {"points_step_ge_10deg": len(big),
                "points_adjacent_diff_gt_limit": sum(1 for i in sel
                                                     if abs(SS[i] - SS[i - 1]) * DEG > prm["adjacent_step_deg"]),
                "max_step_deg": round(max(abs(SS[i]) * DEG for i in sel), 1) if sel else 0.0,
                "source_st_m_of_steps_ge_10deg": [
                    round(st[i if src is None else src[i]]) if (src is None or src[i] is not None) else None
                    for i in big]}

    def climb_range_after():
        if not climb:
            return None
        new_of = {k: i for i, k in enumerate(src_index) if k is not None}
        lo_v = next(k for k in range(n) if st[k] >= climb[0] and k in new_of)
        hi_v = max(k for k in range(n) if st[k] <= climb[1] and k in new_of)
        return [st2[new_of[lo_v]], st2[new_of[hi_v]]]

    summary = {"before": counts(S, st, climb), "after": counts(S2, st2, climb_range_after(), src_index),
               "range_st_m": climb}

    undeclared = []
    if detect_deg:
        spans = [(r["span"]["v"][0], r["span"]["v"][1]) for r in fitted]
        apexes = [c["_apex"] for c in corners]
        for i, t in detect_corners(st, S, detect_deg, prm["window_m"] * 4.0 / 3.0, climb):
            if any(abs(st[i] - st[a]) < prm["window_m"] for a in apexes) or any(a <= i <= b for a, b in spans):
                continue
            k0 = max(1, i - 15)
            k1 = min(n - 2, i + 15)
            undeclared.append({"apex_v": i, "st_m": round(st[i], 1), "window_m": round(prm["window_m"] * 4 / 3),
                               "turn_deg": round(t * DEG, 1),
                               "max_step_deg_pm45m": round(max(abs(S[k]) for k in range(k0, k1 + 1)) * DEG, 1)})

    out_dir.mkdir(parents=True, exist_ok=True)
    src_md5 = hashlib.md5(cl_path.read_bytes()).hexdigest()
    props = dict(feat.get("properties") or {})
    props["point_count"] = len(out_ll)
    props["length_m"] = round(polyline_length([tuple(c) for c in out_ll]), 1)
    if widths:
        props["widths_m"] = out_w
    props["hairpin_fit"] = {
        "tool": "tools/fit_hairpins.py", "source": str(cl_path), "source_md5": src_md5,
        "corners": [{"id": r["id"], "v": r["fitted_v"], "radius_m": r["radius_fit_m"],
                     "st_m_source": r["span"]["st_m"]} for r in fitted],
        "not_spliced": [{"id": r["id"], "status": r["status"], "why": r.get("why", "")}
                        for r in results if r["status"] != "PASS"],
        "_doc": "PROTOTYPE output (plan P2 step 2); not the track's data. Vertex indices after each fitted "
                "corner are shifted: see hairpin_fit.json index_shift.",
    }
    new_feat = dict(feat)
    new_feat["properties"] = props
    new_feat["geometry"] = {"type": "LineString", "coordinates": out_ll}
    out_gj = dict(gj)
    out_gj["features"] = list(gj["features"])
    out_gj["features"][fidx] = new_feat
    (out_dir / "centerline.fitted.geojson").write_text(json.dumps(out_gj), encoding="utf-8")

    for r in results:
        if "_fit" in r:
            write_svg(out_dir / f"{r['id']}.svg", r, P, st, S, prm)
            r["plot"] = str(out_dir / f"{r['id']}.svg")
    clean = []
    for r in results:
        rr = {k: v for k, v in r.items() if not k.startswith("_")}
        if "lateral_move_m" in rr:
            x, y = rr["lateral_move_m"]["at"]
            rr["lateral_move_m"] = dict(rr["lateral_move_m"], at=[round(x, 2), round(y, 2)],
                                        at_lonlat=[round(lon0 + x / mlon, 7), round(lat0 + y / mlat, 7)])
        rr["spliced"] = any(r is f for f in fitted)
        clean.append(rr)
    status = ("FAIL" if any(r["status"] == "FAIL" for r in results)
              else "PENDING" if any(r["status"] == "PENDING" for r in results) else "PASS")
    report = {
        "status": status,
        "centerline": str(cl_path), "centerline_md5": src_md5,
        "frame": "local ENU plan metres about the centreline centroid (scripts/geometry/projection.py "
                 "series); stations from v0 of the source centreline",
        "params": {k: v for k, v in prm.items()},
        "corners": clean,
        "climb": summary,
        "undeclared_bends": undeclared,
        "index_shift": {"_doc": "a source vertex v > from_v moves by the sum of add over every entry with "
                                "from_v <= v (this is why P2 must re-derive every vertex the config declares)",
                        "entries": shift, "total_points": len(out_ll), "source_points": n},
        "length_m": {"source": (feat.get("properties") or {}).get("length_m"), "fitted": props["length_m"]},
    }
    (out_dir / "hairpin_fit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


# --------------------------------------------------------------------------------------------------
# the before/after plot
# --------------------------------------------------------------------------------------------------
def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_svg(path: Path, r: dict, P, st, S, prm) -> None:
    f = r["_fit"]
    A, B, curve, fit = f.A, f.B, f.curve, f.pts
    m = 6
    k0, k1 = max(0, A - m), min(len(P) - 1, B + m)
    orig = P[k0:k1 + 1]
    cx, cy = curve.centre()
    xs = [p[0] for p in orig + fit] + [cx]
    ys = [p[1] for p in orig + fit] + [cy]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    span = max(x1 - x0, y1 - y0) * 1.08 + 4.0
    mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    W, H = 1180, 630
    pw = 500  # plan panel size
    ox, oy = 30, 40
    sc = pw / span

    def tp(p):
        return (ox + (p[0] - (mx - span / 2.0)) * sc, oy + ((my + span / 2.0) - p[1]) * sc)

    def path_d(pts):
        return "M " + " L ".join(f"{tp(p)[0]:.2f},{tp(p)[1]:.2f}" for p in pts)

    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
             'font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="13">')
    o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    title = (f"{r['id']} {r.get('name', '')}: st {r['span']['st_m'][0]:,.0f}-{r['span']['st_m'][1]:,.0f}, "
             f"turn {abs(r['turn_deg']):.0f} deg, fitted R {r['radius_fit_m']:.1f} m  [{r['status']}]")
    o.append(f'<text x="{ox}" y="24" font-size="16" font-weight="600" fill="#1d1d1f">{_esc(title)}</text>')
    # plan panel
    o.append(f'<rect x="{ox}" y="{oy}" width="{pw}" height="{pw}" fill="#f7f7f5" stroke="#d0d0cc"/>')
    # road band (6.7 m-ish) around the fitted line, faint, for scale
    o.append(f'<path d="{path_d(fit)}" fill="none" stroke="#1c7ed6" stroke-opacity="0.10" '
             f'stroke-width="{6.7 * sc:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
    o.append(f'<path d="{path_d(orig)}" fill="none" stroke="#d9480f" stroke-width="2"/>')
    for p in orig:
        q = tp(p)
        o.append(f'<circle cx="{q[0]:.2f}" cy="{q[1]:.2f}" r="2.6" fill="#d9480f"/>')
    o.append(f'<path d="{path_d(fit)}" fill="none" stroke="#1c7ed6" stroke-width="2.2"/>')
    for p in (fit[0], fit[-1]):
        q = tp(p)
        o.append(f'<rect x="{q[0] - 4:.2f}" y="{q[1] - 4:.2f}" width="8" height="8" fill="none" '
                 'stroke="#1d1d1f" stroke-width="1.5"/>')
    qa, qb = tp(fit[0]), tp(fit[-1])
    o.append(f'<text x="{qa[0] + 7:.1f}" y="{qa[1] - 6:.1f}" fill="#1d1d1f">start (v{A})</text>')
    o.append(f'<text x="{qb[0] + 7:.1f}" y="{qb[1] - 6:.1f}" fill="#1d1d1f">end (v{B})</text>')
    qc = tp((cx, cy))
    mid = curve.at(curve.L1 + curve.Lc / 2.0)
    qm = tp(mid)
    o.append(f'<path d="M {qc[0] - 5:.1f},{qc[1]:.1f} L {qc[0] + 5:.1f},{qc[1]:.1f} M {qc[0]:.1f},{qc[1] - 5:.1f} '
             f'L {qc[0]:.1f},{qc[1] + 5:.1f}" stroke="#555" stroke-width="1.2"/>')
    o.append(f'<path d="M {qc[0]:.1f},{qc[1]:.1f} L {qm[0]:.1f},{qm[1]:.1f}" stroke="#555" '
             'stroke-dasharray="4 3" stroke-width="1"/>')
    o.append(f'<text x="{(qc[0] + qm[0]) / 2 + 5:.1f}" y="{(qc[1] + qm[1]) / 2:.1f}" fill="#555">'
             f'R {r["radius_fit_m"]:.1f} m</text>')
    # where the fitted line sits furthest from the OSM line
    wx, wy = r["lateral_move_m"]["at"]
    qw = tp((wx, wy))
    o.append(f'<circle cx="{qw[0]:.1f}" cy="{qw[1]:.1f}" r="7" fill="none" stroke="#1d1d1f" stroke-width="1.2"/>')
    o.append(f'<text x="{qw[0] + 10:.1f}" y="{qw[1] + 16:.1f}" fill="#1d1d1f">'
             f'{r["lateral_move_m"]["max"]:.2f} m</text>')
    # scale bar + north
    bar = 10.0 if span < 120 else 20.0
    o.append(f'<path d="M {ox + 14},{oy + pw - 16} L {ox + 14 + bar * sc:.1f},{oy + pw - 16}" '
             'stroke="#1d1d1f" stroke-width="2"/>')
    o.append(f'<text x="{ox + 14}" y="{oy + pw - 22}" fill="#1d1d1f">{bar:.0f} m</text>')
    o.append(f'<path d="M {ox + pw - 20},{oy + 34} L {ox + pw - 20},{oy + 12} M {ox + pw - 25},{oy + 18} '
             f'L {ox + pw - 20},{oy + 12} L {ox + pw - 15},{oy + 18}" stroke="#1d1d1f" fill="none" '
             'stroke-width="1.5"/>')
    o.append(f'<text x="{ox + pw - 24}" y="{oy + 48}" fill="#1d1d1f">N</text>')
    # legend
    ly = oy + pw + 22
    o.append(f'<path d="M {ox},{ly} L {ox + 24},{ly}" stroke="#d9480f" stroke-width="2"/>')
    o.append(f'<text x="{ox + 30}" y="{ly + 4}" fill="#1d1d1f">before: OSM centreline, 3 m points</text>')
    o.append(f'<path d="M {ox + 270},{ly} L {ox + 294},{ly}" stroke="#1c7ed6" stroke-width="2.2"/>')
    o.append(f'<text x="{ox + 300}" y="{ly + 4}" fill="#1d1d1f">after: fitted, {r["after"]["spacing_m"]:.2f} m '
             'points (band = 6.7 m road)</text>')

    # turn-rate panel: degrees of heading per metre travelled (= curvature), sign-normalised
    gx, gy, gw, gh = 600, oy, 550, 300
    sign = 1 if r["turn_deg"] > 0 else -1
    bx = []  # before: (distance from A, rate)
    for k in range(max(1, A - m), min(len(P) - 2, B + m) + 1):
        sp = 0.5 * (math.dist(P[k - 1], P[k]) + math.dist(P[k], P[k + 1]))
        bx.append((st[k] - (st[A] + f.a), sign * S[k] * DEG / sp))
    fit_ext = P[max(0, A - m):A] + fit + P[B + 1:B + m + 1]
    stf = stations(fit_ext)
    a_off = stf[min(m, A)]
    ax_ = []
    for k in range(1, len(fit_ext) - 1):
        sp = 0.5 * (math.dist(fit_ext[k - 1], fit_ext[k]) + math.dist(fit_ext[k], fit_ext[k + 1]))
        stp = _wrap(heading(fit_ext[k], fit_ext[k + 1]) - heading(fit_ext[k - 1], fit_ext[k])) * DEG
        ax_.append((stf[k] - a_off, sign * stp / sp))
    smin = min(v[0] for v in bx + ax_)
    smax = max(v[0] for v in bx + ax_)
    vmax = max(max(abs(v[1]) for v in bx + ax_), DEG / r["radius_fit_m"]) * 1.12
    vmin = min(0.0, min(v[1] for v in bx + ax_)) * 1.12

    def gp(s, v):
        return (gx + (s - smin) / (smax - smin) * gw, gy + gh - (v - vmin) / (vmax - vmin) * gh)

    o.append(f'<rect x="{gx}" y="{gy}" width="{gw}" height="{gh}" fill="#fbfbfa" stroke="#d0d0cc"/>')
    o.append(f'<text x="{gx}" y="{gy - 8}" font-weight="600" fill="#1d1d1f">How hard the road turns, '
             'point by point (degrees of heading per metre)</text>')
    z0 = gp(smin, 0.0)
    z1 = gp(smax, 0.0)
    o.append(f'<path d="M {z0[0]:.1f},{z0[1]:.1f} L {z1[0]:.1f},{z1[1]:.1f}" stroke="#999" stroke-width="1"/>')
    rate = DEG / r["radius_fit_m"]
    q0, q1 = gp(smin, rate), gp(smax, rate)
    o.append(f'<path d="M {q0[0]:.1f},{q0[1]:.1f} L {q1[0]:.1f},{q1[1]:.1f}" stroke="#555" '
             'stroke-dasharray="5 4" stroke-width="1"/>')
    o.append(f'<text x="{q1[0] - 4:.1f}" y="{q1[1] - 5:.1f}" text-anchor="end" fill="#555">'
             f'R {r["radius_fit_m"]:.1f} m arc = {rate:.2f} deg/m</text>')
    for s, v in bx:
        p0, p1 = gp(s, 0.0), gp(s, v)
        o.append(f'<path d="M {p0[0]:.1f},{p0[1]:.1f} L {p1[0]:.1f},{p1[1]:.1f}" stroke="#d9480f" '
                 'stroke-width="3" stroke-opacity="0.75"/>')
    o.append('<path d="M ' + " L ".join(f"{gp(s, v)[0]:.1f},{gp(s, v)[1]:.1f}" for s, v in ax_) +
             '" fill="none" stroke="#1c7ed6" stroke-width="2.2"/>')
    for s in (0.0, r["span"]["fitted_len_m"]):
        p0, p1 = gp(s, vmin), gp(s, vmax)
        o.append(f'<path d="M {p0[0]:.1f},{p0[1]:.1f} L {p1[0]:.1f},{p1[1]:.1f}" stroke="#1d1d1f" '
                 'stroke-opacity="0.35" stroke-dasharray="2 3"/>')
    o.append(f'<text x="{gx}" y="{gy + gh + 16}" fill="#555">0 = where the curve starts; metres along each '
             'line</text>')
    o.append(f'<text x="{gx + gw}" y="{gy + gh + 16}" text-anchor="end" fill="#555">'
             f'{smax - smin:.0f} m shown</text>')
    # numbers
    bf, af, lm = r["before"], r["after"], r["lateral_move_m"]
    lines = [
        f"Before: steps up to {bf['max_step_deg']:.1f} deg between 3 m points "
        f"({bf['max_turn_rate_deg_per_m']:.1f} deg/m); {bf['steps_ge_10deg']} of {len(bf['steps_deg'])} "
        f"points step 10 deg or more; neighbours differ by up to {bf['max_adjacent_diff_deg']:.1f} deg.",
        f"After: steps up to {af['max_step_deg']:.2f} deg between {af['spacing_m']:.2f} m points "
        f"(limit {af['step_limit_deg']:.2f}); neighbours differ by up to {af['max_adjacent_diff_deg']:.2f} deg "
        f"(limit {prm['adjacent_step_deg']}).",
        f"Curve: {r['transitions_m']['L1']:.1f} m easing in, {r['transitions_m']['arc']:.1f} m at "
        f"R {r['radius_fit_m']:.1f} m, {r['transitions_m']['L2']:.1f} m easing out "
        f"({r['radius_kind']} radius).",
        f"Largest sideways move from the OSM line: {lm['max']:.2f} m (reported; the paint judges position). "
        f"Gate: {r['gate']}.",
    ]
    lines.insert(1, "Facet steps before, deg (A to B): " + ", ".join(f"{abs(x):.0f}" for x in bf["steps_deg"]))
    ty = gy + gh + 46
    for line in lines:
        for part in textwrap.wrap(line, 82):
            o.append(f'<text x="{gx}" y="{ty}" fill="#1d1d1f">{_esc(part)}</text>')
            ty += 18
        ty += 6
    o.append("</svg>")
    path.write_text("\n".join(o), encoding="utf-8")


# --------------------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_dir")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--centerline")
    ap.add_argument("--corner", action="append", help="fit only these corner ids")
    ap.add_argument("--radius", action="append", default=[], help="ID=R experiment override (not saved)")
    ap.add_argument("--detect-deg", type=float, default=90.0,
                    help="also list undeclared bends turning >= this over 80 m (0 = off)")
    a = ap.parse_args(argv)
    rad = {}
    for item in a.radius:
        try:
            cid, val = item.split("=", 1)
            rad[cid.strip()] = float(val)
        except ValueError:
            print(f"[hairpins] bad --radius {item!r} (want ID=R)", file=sys.stderr)
            return 2
    try:
        rep = run(Path(a.project_dir), Path(a.out_dir), a.centerline, a.corner, rad, a.detect_deg or None)
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 2
    print(f"{'id':5} {'status':8} {'R m':>6} {'span st':>15} {'before max':>10} {'after max':>9} "
          f"{'adj':>5} {'move m':>6}")
    for r in rep["corners"]:
        if r["status"] == "PENDING" or "span" not in r:
            print(f"{r['id']:5} {r['status']:8} {'-':>6} {'-':>15} {'-':>10} {'-':>9} {'-':>5} {'-':>6}  "
                  f"{r.get('why', '')}")
            continue
        sp = r["span"]["st_m"]
        print(f"{r['id']:5} {r['status']:8} {r['radius_fit_m']:6.1f} {sp[0]:7.0f}-{sp[1]:<7.0f} "
              f"{r['before']['max_step_deg']:9.1f}d {r['after']['max_step_deg']:8.2f}d "
              f"{r['after']['max_adjacent_diff_deg']:5.2f} {r['lateral_move_m']['max']:6.2f}"
              + (f"  {r['why']}" if r.get("why") else ""))
    c = rep["climb"]
    if c["range_st_m"]:
        print(f"climb st {c['range_st_m']}: points stepping >= 10 deg {c['before']['points_step_ge_10deg']} -> "
              f"{c['after']['points_step_ge_10deg']}; adjacent-step failures "
              f"{c['before']['points_adjacent_diff_gt_limit']} -> {c['after']['points_adjacent_diff_gt_limit']}")
    if rep["undeclared_bends"]:
        print("undeclared bends (not fitted): " + ", ".join(
            f"st {u['st_m']:.0f} ({u['turn_deg']:+.0f} deg)" for u in rep["undeclared_bends"]))
    print(f"[hairpins] {rep['status']}: wrote {Path(a.out_dir) / 'hairpin_fit.json'}")
    return {"PASS": 0, "FAIL": 1, "PENDING": 3}[rep["status"]]


if __name__ == "__main__":
    sys.exit(main())
