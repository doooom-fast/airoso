"""Paint centreline: put the lap on the painted road where the aerial traced the paint, keep OSM where it
did not, blend smoothly between, and resample the climb as one curvature-continuous line.

Lookout Lariat V3 (ledger 0048, P2). The aerial pass (NAIP 2019, ``data/aerial/``) found the OSM line off the
painted road by ~7 m at C4, 2-5 m at C10, ~3.9 m at the undeclared st ~6,809 bend and 1-2.6 m in places on
straight road (st ~3,250, Paradise Rd), while tools/fit_hairpins.py judged its fits against OSM within 1.5 m.
Here the paint is the reference and OSM is what remains where nothing is painted or the paint is in shadow
(C11's apex and exit, C7's apex, the upper climb st ~6,200-6,800).

Inputs:
- the OSM centreline, the gps stage's output kept as a source file: ``data/centerline.osm.geojson``
  (``--osm``). When ``data/centerline.geojson`` is a plain gps output (no ``paint_centreline`` property:
  the gps stage was re-run), it is first copied over the source file byte for byte, so a fresh OSM route
  always becomes the new source;
- ``data/aerial/paint_traces.json`` (tools/aerial_measure.py): per window the paint ``reference`` (the traced
  double-yellow centre line, continuous, with ``supported`` flags) and, at a hairpin, the ``core``'s
  yellow-line circle;
- ``track.config.json``: ``hairpin_fit.climb_st_m`` (the climb, stations on the OSM source line) and
  ``hairpin_fit.corners[].radius_m`` (the measured radii; the report compares each hairpin's tightest radius
  on the new line with them; the line itself follows the paint, whose yellow circle carries the radius).

Method (all in the plan frame of the OSM line: local ENU metres about its centroid, as
scripts/geometry/projection.py; stations from its v0):
1. **Targets.** Each window's reference, cut to its supported stretches; an unsupported gap shorter than
   ``GAP_BRIDGE_M`` is bridged ("ref_gap" points) by a cubic Hermite between the supported points either side on
   their own directions (2026-10-12; it was the reference's own unsupported guess), a longer one ends the stretch. At a
   hairpin whose yellow circle is good (>= 45 % of the core traced, rms <= 0.35 m) the reference points over
   the core (within ``CORE_CAPTURE_M`` of the circle) are moved radially onto it. Two windows tracing the
   same leg are crossfaded (smootherstep) across their overlap.
2. **Composite.** OSM vertices inside a target's stations are replaced by the target's points. Every other
   OSM vertex is translated by an offset vector: the neighbouring targets' end offsets (target end minus the
   OSM point there) carried across the gap with a smootherstep (gaps up to ``GAP_INTERP_M``) or tapered to
   zero over ``TAPER_M`` each side (longer gaps), plus a quintic Hermite term over ``TANGENT_M`` at each
   target end that turns the OSM line onto the paint's own direction. The composite is therefore continuous
   in position AND direction at every join: it drifts from OSM onto the paint and back.
3. **Resample + smooth.** The climb (``hairpin_fit.climb_st_m`` + ``CLIMB_PAD_M``, wrapping ``SEAM_PAD_M``
   back across the seam so the closing vertex is smoothed too, L13) and every other stretch the composite
   moved (+ ``REGION_PAD_M``) are resampled at ``SPACING_M`` and smoothed: each point moves along its normal,
   minimising sum w_i d_i^2 + LAM x sum (n . third difference of positions)^2 (a penalty on curvature CHANGE,
   so a steady bend is not pulled straight and a hairpin is not cut), with weights raised wherever |d|
   exceeds its tolerance: ``TOL_PAINT_M`` on paint and ref_gap points, ``TOL_FREE_M`` elsewhere. Region ends,
   v0 (kept a vertex) and the points within ``KINK_PIN_M`` of a junction node outside the climb (one OSM step
   > ``KINK_DEG``: C12, C13, whose arcs belong to P3b's junction mouths; see the report) are fixed. Each piece
   is then re-spaced evenly along the smoothed line. Where the climb still fails the paint gate's curvature
   rules, the tolerance around each failure is loosened (non-paint by ``ADAPT_FREE_STEP_M`` up to
   ``TOL_FREE_MAX_M``, paint by ``ADAPT_PAINT_STEP_M`` up to ``TOL_PAINT_MAX_M``, +-``ADAPT_REACH`` points)
   and the region smoothed again, at most ``ADAPT_ROUNDS`` times.
4. **Output.** Untouched OSM vertices are copied byte for byte; the closing vertex repeats v0 exactly.
   ``widths_m`` are carried from the OSM line by station (an untouched vertex keeps its own);
   ``osm_station_m`` gives every vertex's station on the OSM line, the key tools/remap_centreline_config.py
   and the paint gate use.

Thresholds, all **[invented]** (2026-10-11): ``GAP_BRIDGE_M`` 15 m, ``GAP_INTERP_M`` 400 m, ``TAPER_M`` 80 m,
``TANGENT_M`` 25 m, ``SPACING_M`` 1.0 m, ``LAM`` 1e4, ``TOL_PAINT_M`` 0.25 m, ``TOL_FREE_M`` 0.5 m,
``SEAM_PAD_M`` 60 m, ``CLIMB_PAD_M`` 60 m, ``REGION_PAD_M`` 20 m, ``KINK_DEG`` 30 deg, ``KINK_PIN_M`` 3 m,
``CORE_CAPTURE_M`` 4 m, ``ADAPT_ROUNDS`` 6, ``ADAPT_REACH`` 8 points, ``ADAPT_FREE_STEP_M`` 0.25 m,
``ADAPT_PAINT_STEP_M`` 0.05 m, ``TOL_FREE_MAX_M`` 1.5 m, ``TOL_PAINT_MAX_M`` 0.4 m. They shape the line; they
judge nothing. The judge is tools/verify_centreline_paint.py.

Writes ``--out`` (default ``data/centerline.geojson``: the file every later build stage reads, elevation,
projection and widths; a paint centreline it replaces is kept as ``data/centerline.previous.geojson`` so the
config can be remapped from it) and ``--report`` (default ``data/aerial/paint_centreline.json``). Build order for
the Lariat: ``gps`` -> this tool -> ``tools/remap_centreline_config.py --write`` -> ``elev`` and on. Exit 0,
or 2 on a usage / input error.

    python tools/paint_centreline.py <project-dir> [--osm F] [--traces F] [--out F] [--report F]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import statistics as stt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)
import fit_hairpins as fh  # noqa: E402  (geometry helpers: stations, signed steps, heading)
from scripts.geometry.projection import _meters_per_degree, centroid  # noqa: E402
from scripts.gps.centerline import polyline_length  # noqa: E402

DEG = 180.0 / math.pi
GAP_BRIDGE_M = 15.0
GAP_ARM_PTS = 4
GAP_INTERP_M = 400.0
TAPER_M = 80.0
TANGENT_M = 25.0
SPACING_M = 1.0
LAM = 1e4
TOL_PAINT_M = 0.25
TOL_FREE_M = 0.5
SEAM_PAD_M = 60.0
CLIMB_PAD_M = 60.0
REGION_PAD_M = 20.0
KINK_DEG = 30.0
KINK_PIN_M = 3.0
ADAPT_ROUNDS = 6
ADAPT_REACH = 8
ADAPT_FREE_STEP_M = 0.25
ADAPT_PAINT_STEP_M = 0.05
TOL_FREE_MAX_M = 1.5
TOL_PAINT_MAX_M = 0.4
CORE_CAPTURE_M = 4.0
# junction fillets (2026-10-12, ledger 0048 "P2 fixed"): off the climb, a corner OSM draws as one node or a few
# facets becomes an arc tangent to both arms, before the smoothing
FILLET_STEP_DEG = 20.0
FILLET_R_FACET_M = 6.0
FILLET_CLUSTER_M = 15.0
FILLET_ARM_M = 10.0
FILLET_R_M = 12.0
FILLET_R_MIN_M = 4.0
FILLET_DEPART_M = 3.0
FILLET_ON_ARM_M = 0.5
FILLET_MIN_TURN_DEG = 15.0
FILLET_MATCH_M = 40.0
FILLET_PAINT_M = 0.5
PARAMS = {k: globals()[k] for k in ("GAP_BRIDGE_M", "GAP_INTERP_M", "TAPER_M", "TANGENT_M", "SPACING_M", "LAM", "TOL_PAINT_M",
                                     "TOL_FREE_M", "SEAM_PAD_M", "CLIMB_PAD_M", "REGION_PAD_M", "KINK_DEG",
                                     "KINK_PIN_M", "CORE_CAPTURE_M", "ADAPT_ROUNDS", "ADAPT_REACH",
                                     "ADAPT_FREE_STEP_M", "ADAPT_PAINT_STEP_M", "TOL_FREE_MAX_M", "TOL_PAINT_MAX_M",
                                     "FILLET_STEP_DEG", "FILLET_R_FACET_M", "FILLET_CLUSTER_M", "FILLET_ARM_M",
                                     "FILLET_R_M", "FILLET_R_MIN_M", "FILLET_DEPART_M", "FILLET_ON_ARM_M",
                                     "FILLET_MIN_TURN_DEG", "FILLET_MATCH_M", "FILLET_PAINT_M")}


# --------------------------------------------------------------------------------------------------
# frames and small geometry
# --------------------------------------------------------------------------------------------------
class Frame:
    def __init__(self, lonlat):
        self.lon0, self.lat0 = centroid(lonlat)
        self.mlon, self.mlat = _meters_per_degree(self.lat0)

    def xy(self, lon, lat):
        return ((lon - self.lon0) * self.mlon, (lat - self.lat0) * self.mlat)

    def ll(self, x, y):
        return [self.lon0 + x / self.mlon, self.lat0 + y / self.mlat]


def resample_poly(P, ds):
    """Points every ~ds along polyline P (first and last kept); returns (points, fraction along each)."""
    st = fh.stations(P)
    L = st[-1]
    n = max(1, int(round(L / ds)))
    out, frac = [], []
    j = 0
    for k in range(n + 1):
        s = L * k / n
        while j < len(P) - 2 and st[j + 1] < s:
            j += 1
        seg = st[j + 1] - st[j]
        t = 0.0 if seg <= 0 else (s - st[j]) / seg
        out.append((P[j][0] + t * (P[j + 1][0] - P[j][0]), P[j][1] + t * (P[j + 1][1] - P[j][1])))
        frac.append((j, t))
    return out, frac


def normals(Q):
    N = []
    for i in range(len(Q)):
        a = Q[max(0, i - 1)]
        b = Q[min(len(Q) - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1.0
        N.append((-ty / L, tx / L))
    return N


def project(p, P, st, i0, i1):
    """Nearest point on P[i0..i1]: (distance, station, segment index, t)."""
    best = None
    for i in range(max(0, i0), min(len(P) - 1, i1)):
        a, b = P[i], P[i + 1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        if L2 <= 0:
            continue
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        d = math.hypot(a[0] + t * dx - p[0], a[1] + t * dy - p[1])
        if best is None or d < best[0]:
            best = (d, st[i] + t * (st[i + 1] - st[i]), i, t)
    return best


def idx_at(st, s):
    lo, hi = 0, len(st) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if st[mid] <= s:
            lo = mid
        else:
            hi = mid
    return lo


def point_at(P, st, s):
    i = idx_at(st, s)
    j = min(i + 1, len(P) - 1)
    seg = st[j] - st[i]
    t = 0.0 if seg <= 0 else (s - st[i]) / seg
    return (P[i][0] + t * (P[j][0] - P[i][0]), P[i][1] + t * (P[j][1] - P[i][1]))


# --------------------------------------------------------------------------------------------------
# the smoother (banded normal equations, pure Python)
# --------------------------------------------------------------------------------------------------
def banded_cholesky_solve(diag, off, rhs):
    """Solve M d = rhs for symmetric positive definite banded M: diag[i] = M[i][i], off[k][i] = M[i][i+k+1]."""
    n = len(diag)
    bw = len(off)
    Ld = [0.0] * n
    Lo = [[0.0] * n for _ in range(bw)]
    for i in range(n):
        s = diag[i]
        for k in range(1, bw + 1):
            j = i - k
            if j < 0:
                break
            s -= Lo[k - 1][j] ** 2
        if s <= 0:
            raise ValueError("not positive definite")
        Ld[i] = math.sqrt(s)
        for k in range(1, bw + 1):
            r = i + k
            if r >= n:
                break
            v = off[k - 1][i]
            for m in range(max(0, r - bw), i):
                kr, ki = r - m, i - m
                if kr <= bw and 1 <= ki <= bw:
                    v -= Lo[kr - 1][m] * Lo[ki - 1][m]
            Lo[k - 1][i] = v / Ld[i]
    y = [0.0] * n
    for i in range(n):
        s = rhs[i]
        for k in range(1, bw + 1):
            j = i - k
            if j < 0:
                break
            s -= Lo[k - 1][j] * y[j]
        y[i] = s / Ld[i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = y[i]
        for k in range(1, bw + 1):
            r = i + k
            if r >= n:
                break
            s -= Lo[k - 1][i] * x[r]
        x[i] = s / Ld[i]
    return x


def smooth(Q, pinned, tol, lam=LAM, iters=60):
    """Lateral (normal) moves d_i minimising sum w d^2 + lam sum (n . D3 x)^2, IRLS-raising w where |d| > tol_i.
    Returns (points, d, iterations)."""
    n = len(Q)
    N = normals(Q)
    W = [1e8 if pinned[i] else 1.0 for i in range(n)]
    AtA_d = [0.0] * n
    AtA_o = [[0.0] * n for _ in range(3)]
    Atb = [0.0] * n
    for i in range(1, n - 2):
        nx, ny = N[i][0] + N[i + 1][0], N[i][1] + N[i + 1][1]
        L = math.hypot(nx, ny) or 1.0
        nx, ny = nx / L, ny / L
        cols = (i - 1, i, i + 1, i + 2)
        coef = (-1.0, 3.0, -3.0, 1.0)
        b = sum(c * (Q[k][0] * nx + Q[k][1] * ny) for c, k in zip(coef, cols))
        a = [c * (N[k][0] * nx + N[k][1] * ny) for c, k in zip(coef, cols)]
        for p_ in range(4):
            cp = cols[p_]
            AtA_d[cp] += a[p_] * a[p_]
            Atb[cp] += a[p_] * b
            for q in range(p_ + 1, 4):
                AtA_o[q - p_ - 1][cp] += a[p_] * a[q]
    d = [0.0] * n
    it = 0
    for it in range(iters):
        diag = [W[i] + lam * AtA_d[i] for i in range(n)]
        off = [[lam * v for v in AtA_o[k]] for k in range(3)]
        rhs = [-lam * Atb[i] for i in range(n)]
        d = banded_cholesky_solve(diag, off, rhs)
        worst = max((abs(x) / tol[i] for i, x in enumerate(d) if not pinned[i]), default=0.0)
        if worst <= 1.02:
            break
        for i in range(n):
            if not pinned[i] and abs(d[i]) > tol[i]:
                W[i] *= 4.0 * (abs(d[i]) / tol[i]) ** 2
    X = [(Q[i][0] + d[i] * N[i][0], Q[i][1] + d[i] * N[i][1]) for i in range(n)]
    return X, d, it + 1


# --------------------------------------------------------------------------------------------------
# targets from the paint traces
# --------------------------------------------------------------------------------------------------
def smootherstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (6.0 * t - 15.0) + 10.0)


def h1(u):
    """Quintic Hermite basis: H(0) = 0, H'(0) = 1, H''(0) = 0, H = H' = H'' = 0 at 1."""
    if u <= 0.0 or u >= 1.0:
        return 0.0
    return u - 6.0 * u ** 3 + 8.0 * u ** 4 - 3.0 * u ** 5


def _unit(v):
    L = math.hypot(*v) or 1.0
    return (v[0] / L, v[1] / L)


def _end_tangent(pts, at_end, arm=2.0):
    """Unit direction of travel over the first / last ``arm`` metres of a polyline."""
    if at_end:
        acc, k = 0.0, len(pts) - 1
        while k > 0 and acc < arm:
            acc += math.dist(pts[k], pts[k - 1])
            k -= 1
        return _unit((pts[-1][0] - pts[k][0], pts[-1][1] - pts[k][1]))
    acc, k = 0.0, 0
    while k < len(pts) - 1 and acc < arm:
        acc += math.dist(pts[k], pts[k + 1])
        k += 1
    return _unit((pts[k][0] - pts[0][0], pts[k][1] - pts[0][1]))


def osm_tangent(P, st, s, arm=1.5):
    a = point_at(P, st, max(0.0, s - arm))
    b = point_at(P, st, min(st[-1], s + arm))
    return _unit((b[0] - a[0], b[1] - a[1]))


def _finish(T, P, st):
    """(Re)compute a target's end offsets and tangent mismatches against the OSM line."""
    win = (idx_at(st, T["s_a"] - 40), idx_at(st, T["s_b"] + 40) + 2)
    pa = project(T["pts"][0], P, st, *win)
    pb = project(T["pts"][-1], P, st, *win)
    T["s_a"], T["s_b"] = pa[1], pb[1]
    qa, qb = point_at(P, st, T["s_a"]), point_at(P, st, T["s_b"])
    T["D_a"] = (T["pts"][0][0] - qa[0], T["pts"][0][1] - qa[1])
    T["D_b"] = (T["pts"][-1][0] - qb[0], T["pts"][-1][1] - qb[1])
    ta, tb = _end_tangent(T["pts"], False), _end_tangent(T["pts"], True)
    oa, ob = osm_tangent(P, st, T["s_a"]), osm_tangent(P, st, T["s_b"])
    T["G_a"] = (ta[0] - oa[0], ta[1] - oa[1])
    T["G_b"] = (tb[0] - ob[0], tb[1] - ob[1])
    return T


def _bridge_gaps(R, sup, a, b, arm=GAP_ARM_PTS):
    """Every unsupported run inside R[a..b] (shorter than GAP_BRIDGE_M: the caller split at longer ones) is
    replaced IN PLACE by a cubic Hermite between the supported points either side, on their own directions
    (each over ``arm`` supported points). The reference's own points in a gap are the tracer's guess where it
    lost the paint (unsupported), not evidence: 2026-10-12 at C13's approach (OSM st 10,580-10,589) the guess
    jogged ~2 m sideways over 9 m (heading -12 -> -27 -> -1 -> -13 deg), and the smoothing, holding ref_gap
    points to TOL_PAINT_M, kept it: R 3.7-5 m on a straight, grass over the full lane width in the built road."""
    k = a
    while k <= b:
        if sup[k]:
            k += 1
            continue
        u0 = k
        while k <= b and not sup[k]:
            k += 1
        u1 = k - 1
        i0, i1 = u0 - 1, u1 + 1
        if i0 < a or i1 > b:
            continue
        p0, p1 = R[i0], R[i1]
        j0 = max(a, i0 - arm)
        while j0 < i0 and not sup[j0]:
            j0 += 1
        j1 = min(b, i1 + arm)
        while j1 > i1 and not sup[j1]:
            j1 -= 1
        chord = math.dist(p0, p1)
        t0 = _unit((p0[0] - R[j0][0], p0[1] - R[j0][1])) if j0 < i0 else _unit((p1[0] - p0[0], p1[1] - p0[1]))
        t1 = _unit((R[j1][0] - p1[0], R[j1][1] - p1[1])) if j1 > i1 else _unit((p1[0] - p0[0], p1[1] - p0[1]))
        m = i1 - i0
        for q in range(1, m):
            t = q / m
            h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
            R[i0 + q] = (h00 * p0[0] + h10 * chord * t0[0] + h01 * p1[0] + h11 * chord * t1[0],
                         h00 * p0[1] + h10 * chord * t0[1] + h01 * p1[1] + h11 * chord * t1[1])


def load_targets(traces, F, P, st):
    """The paint as targets, in the base plan frame and travel order: per window, its reference's
    supported stretches (gaps shorter than GAP_BRIDGE_M bridged by a Hermite curve, ``_bridge_gaps``), the core moved
    onto a good yellow circle; windows tracing the same leg crossfaded. Sorted by s_a."""
    fr = traces["frame"]
    lon0, lat0 = fr["origin_lonlat"]
    mlon, mlat = _meters_per_degree(lat0)

    def tr_xy(x, z):
        return F.xy(lon0 + x / mlon, lat0 + z / mlat)
    out = []
    for w in traces["windows"]:
        ref = w.get("reference")
        if not ref or not any(ref["supported"]):
            continue
        R = [tr_xy(*q) for q in ref["xz_m"]]
        sup = list(ref["supported"])
        core = w.get("core") or {}
        yc = core.get("yellow_circle")
        n_core = 0
        if yc and yc.get("good") and len(core.get("core_ends_on_yellow_circle") or []) == 2:
            c = tr_xy(*yc["centre_xz_m"])
            Rr = yc["R_m"]
            e0, e1 = [tr_xy(*e["xz_m"]) for e in core["core_ends_on_yellow_circle"]]
            a0 = math.atan2(e0[1] - c[1], e0[0] - c[0])
            a1 = math.atan2(e1[1] - c[1], e1[0] - c[0])
            sgn = 1 if core["direction"] == "left" else -1
            span = (a1 - a0) * sgn % (2 * math.pi)
            for i, p in enumerate(R):
                a = math.atan2(p[1] - c[1], p[0] - c[0])
                r = math.hypot(p[0] - c[0], p[1] - c[1])
                if (a - a0) * sgn % (2 * math.pi) <= span and abs(r - Rr) < CORE_CAPTURE_M and r > 0:
                    R[i] = (c[0] + Rr * (p[0] - c[0]) / r, c[1] + Rr * (p[1] - c[1]) / r)
                    sup[i] = True
                    n_core += 1
        step = 0.5
        i, n = 0, len(R)
        while i < n:
            if not sup[i]:
                i += 1
                continue
            last, gap, k = i, 0, i + 1
            while k < n:
                if sup[k]:
                    last, gap = k, 0
                else:
                    gap += 1
                    if gap * step >= GAP_BRIDGE_M:
                        break
                k += 1
            a, b = i, last
            i = last + 1
            if b <= a:
                continue
            _bridge_gaps(R, sup, a, b)
            ref_st = ref["lap_st_m"]
            sa_est = next((ref_st[k] for k in range(a, b + 1) if ref_st[k] is not None), None)
            sb_est = next((ref_st[k] for k in range(b, a - 1, -1) if ref_st[k] is not None), None)
            if sa_est is None or sb_est is None or sb_est <= sa_est:
                continue
            T = {"id": f"{w['id']}#{len(out)}", "window": w["id"], "kind": w["kind"], "pts": R[a:b + 1],
                 "kinds": ["paint" if sup[k] else "ref_gap" for k in range(a, b + 1)],
                 "s_a": sa_est, "s_b": sb_est, "n_core_on_circle": n_core}
            _finish(T, P, st)
            if T["s_b"] > T["s_a"]:
                out.append(T)
    out.sort(key=lambda t: t["s_a"])
    merged = []
    for T in out:
        if merged and T["s_a"] < merged[-1]["s_b"]:
            merged[-1] = _crossfade(merged[-1], T, P, st)
        else:
            merged.append(T)
    return merged


def _target_stations(T):
    """Base stations of a target's points: linear in its own arc length between s_a and s_b."""
    s = fh.stations(T["pts"])
    L = s[-1] or 1.0
    return [T["s_a"] + (T["s_b"] - T["s_a"]) * v / L for v in s]


def _at_station(T, sts, s):
    i = idx_at(sts, s)
    j = min(i + 1, len(sts) - 1)
    t = 0.0 if sts[j] == sts[i] else max(0.0, min(1.0, (s - sts[i]) / (sts[j] - sts[i])))
    p, q = T["pts"][i], T["pts"][j]
    kd = "paint" if "paint" in (T["kinds"][i], T["kinds"][j]) else "ref_gap"
    return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])), kd


def _crossfade(A, B, P, st):
    """Two targets tracing the same leg (overlapping stations): A before the overlap, a smootherstep blend
    from A to B across it, B after it. A target inside the other is dropped."""
    if B["s_b"] <= A["s_b"]:
        return A
    sa, sb = _target_stations(A), _target_stations(B)
    o0, o1 = B["s_a"], A["s_b"]
    pts, kinds = [], []
    for p, s, k in zip(A["pts"], sa, A["kinds"]):
        if s < o0:
            pts.append(p)
            kinds.append(k)
    n = max(2, int((o1 - o0) / 0.5) + 1)
    for m in range(n):
        s = o0 + (o1 - o0) * m / (n - 1)
        pa, ka = _at_station(A, sa, s)
        pb, kb = _at_station(B, sb, s)
        w = smootherstep((s - o0) / (o1 - o0)) if o1 > o0 else 1.0
        pts.append(((1 - w) * pa[0] + w * pb[0], (1 - w) * pa[1] + w * pb[1]))
        kinds.append("paint" if "paint" in (ka, kb) else "ref_gap")
    for p, s, k in zip(B["pts"], sb, B["kinds"]):
        if s > o1:
            pts.append(p)
            kinds.append(k)
    T = {"id": A["id"] + "+" + B["id"], "window": A["window"] + "+" + B["window"], "kind": A["kind"],
         "pts": pts, "kinds": kinds, "s_a": A["s_a"], "s_b": B["s_b"],
         "n_core_on_circle": A["n_core_on_circle"] + B["n_core_on_circle"]}
    return _finish(T, P, st)


# --------------------------------------------------------------------------------------------------
# composite: the OSM line moved onto the targets (position AND direction continuous) + the targets
# --------------------------------------------------------------------------------------------------
def _neighbours(s, targets, lap, closed):
    prev = nxt = None
    for t in targets:
        if t["s_b"] <= s:
            prev = t
        elif t["s_a"] >= s and nxt is None:
            nxt = t
    if closed and targets:
        if prev is None:
            prev = dict(targets[-1], s_a=targets[-1]["s_a"] - lap, s_b=targets[-1]["s_b"] - lap)
        if nxt is None:
            nxt = dict(targets[0], s_a=targets[0]["s_a"] + lap, s_b=targets[0]["s_b"] + lap)
    return prev, nxt


def offset_at(s, targets, lap, closed=True):
    """Translation of the OSM point at station s (outside every target): the neighbouring targets' end
    offsets carried across the gap (smootherstep, or tapered to zero over TAPER_M on a long gap), plus a
    term that turns the OSM line onto each target's direction at its end over TANGENT_M (quintic Hermite),
    so the composite is continuous in position and direction at every join."""
    prev, nxt = _neighbours(s, targets, lap, closed)
    D = [0.0, 0.0]
    if prev is not None and nxt is not None:
        g = nxt["s_a"] - prev["s_b"]
        if g <= GAP_INTERP_M:
            w = smootherstep((s - prev["s_b"]) / g) if g > 0 else 0.0
            for k in (0, 1):
                D[k] = prev["D_b"][k] + (nxt["D_a"][k] - prev["D_b"][k]) * w
        else:
            w1 = 1.0 - smootherstep((s - prev["s_b"]) / TAPER_M)
            w2 = smootherstep((s - (nxt["s_a"] - TAPER_M)) / TAPER_M)
            for k in (0, 1):
                D[k] = prev["D_b"][k] * w1 + nxt["D_a"][k] * w2
        LT = min(TANGENT_M, 0.5 * g)
        if LT > 0:
            u0 = (s - prev["s_b"]) / LT
            u1 = (nxt["s_a"] - s) / LT
            for k in (0, 1):
                D[k] += prev["G_b"][k] * LT * h1(u0) - nxt["G_a"][k] * LT * h1(u1)
    elif prev is not None:
        w1 = 1.0 - smootherstep((s - prev["s_b"]) / TAPER_M)
        LT = TANGENT_M
        for k in (0, 1):
            D[k] = prev["D_b"][k] * w1 + prev["G_b"][k] * LT * h1((s - prev["s_b"]) / LT)
    elif nxt is not None:
        w2 = smootherstep((s - (nxt["s_a"] - TAPER_M)) / TAPER_M)
        LT = TANGENT_M
        for k in (0, 1):
            D[k] = nxt["D_a"][k] * w2 - nxt["G_a"][k] * LT * h1((nxt["s_a"] - s) / LT)
    return (D[0], D[1])


def composite(P, st, targets, closed=True):
    """[(point, base station, kind, raw OSM index or None)] along the lap: kind 'paint' (a supported target
    point), 'ref_gap' (a target point bridging a short unsupported gap), 'moved' (an OSM vertex translated),
    'osm' (an OSM vertex untouched)."""
    lap = st[-1]
    out = []
    ti = 0
    n = len(P)
    tsts = [_target_stations(t) for t in targets]
    k = 0
    while k < n:
        s = st[k]
        while ti < len(targets) and targets[ti]["s_b"] < s:
            ti += 1
        if ti < len(targets) and targets[ti]["s_a"] <= s <= targets[ti]["s_b"]:
            t = targets[ti]
            for p, sp, kd in zip(t["pts"], tsts[ti], t["kinds"]):
                out.append((p, sp, kd, None))
            while k < n and st[k] <= t["s_b"]:
                k += 1
            ti += 1
            continue
        D = offset_at(s, targets, lap, closed)
        moved = abs(D[0]) + abs(D[1]) > 1e-9
        out.append(((P[k][0] + D[0], P[k][1] + D[1]), s, "moved" if moved else "osm", k))
        k += 1
    return out


# --------------------------------------------------------------------------------------------------
# the whole build
# --------------------------------------------------------------------------------------------------
def respace(X, srcs, bounds):
    """Each piece re-spaced evenly by arc length along the smoothed polyline (its ends fixed), so smoothing's
    lateral moves never leave the climb's points unevenly spaced; srcs follow by arc length."""
    X2, S2 = list(X), list(srcs)
    for qa, qb in bounds:
        seg = X[qa:qb + 1]
        sv = fh.stations(seg)
        L = sv[-1]
        m = qb - qa
        if m < 2 or L <= 0:
            continue
        j = 0
        for k in range(1, m):
            target = L * k / m
            while j < m - 1 and sv[j + 1] < target:
                j += 1
            t = 0.0 if sv[j + 1] == sv[j] else (target - sv[j]) / (sv[j + 1] - sv[j])
            X2[qa + k] = (seg[j][0] + t * (seg[j + 1][0] - seg[j][0]), seg[j][1] + t * (seg[j + 1][1] - seg[j][1]))
            S2[qa + k] = srcs[qa + j] + t * (srcs[qa + j + 1] - srcs[qa + j])
    return X2, S2


def curvature_fails(X, judged, edge=6):
    """Indices failing the paint gate's curvature rules (verify_centreline_paint (b)) on an open piece of line
    at its own spacing: |step| <= spacing x |k_local| x 57.3 + 1 deg, neighbour steps within 1.5 deg."""
    import verify_centreline_paint as vp  # noqa: E402  (the judge's own numbers)
    n = len(X)
    S = fh.signed_steps(X)
    seg = [math.dist(X[i], X[i + 1]) for i in range(n - 1)]
    sp = [0.0] + [0.5 * (seg[i - 1] + seg[i]) for i in range(1, n - 1)] + [0.0]
    fails = []
    for k in range(edge, n - edge):
        if not judged[k]:
            continue
        turn, length = S[k], sp[k]
        acc = 0.0
        j = k
        while j > 1:
            acc += seg[j - 1]
            if acc > vp.LOCAL_M:
                break
            j -= 1
            turn += S[j]
            length += sp[j]
        acc = 0.0
        j = k
        while j < n - 2:
            acc += seg[j]
            if acc > vp.LOCAL_M:
                break
            j += 1
            turn += S[j]
            length += sp[j]
        lim = sp[k] * abs(turn / max(length, 1e-9)) * DEG + vp.STEP_SLACK_DEG
        if abs(S[k]) * DEG > lim or (judged[k - 1] and abs(S[k] - S[k - 1]) * DEG > vp.ADJ_STEP_DEG):
            fails.append(k)
    return fails


def smooth_region(Q, srcs, pinned, tol, kinds, bounds, judged):
    """Smooth, re-space, and where the climb still fails the curvature rules loosen the tolerance of the
    points around each failure (non-paint by ADAPT_FREE_STEP_M up to TOL_FREE_MAX_M, paint by
    ADAPT_PAINT_STEP_M up to TOL_PAINT_MAX_M) and smooth again, at most ADAPT_ROUNDS times."""
    tol = list(tol)
    rounds = []
    X, S2, d = Q, srcs, [0.0] * len(Q)
    for rnd in range(ADAPT_ROUNDS + 1):
        X, d, its = smooth(Q, pinned, tol)
        X, S2 = respace(X, srcs, bounds)
        fails = curvature_fails(X, judged) if any(judged) else []
        rounds.append({"round": rnd, "irls_iterations": its, "curvature_fails": len(fails)})
        if not fails or rnd == ADAPT_ROUNDS:
            break
        for k in fails:
            for j in range(max(0, k - ADAPT_REACH), min(len(Q), k + ADAPT_REACH + 1)):
                if pinned[j]:
                    continue
                if kinds[j] == "paint":
                    tol[j] = min(TOL_PAINT_MAX_M, tol[j] + ADAPT_PAINT_STEP_M)
                else:
                    tol[j] = min(TOL_FREE_MAX_M, tol[j] + ADAPT_FREE_STEP_M)
    free = [abs(x) for x, p_ in zip(d, pinned) if not p_]
    loosened = sum(1 for t, kd in zip(tol, kinds) if t > (TOL_PAINT_M if kd in ("paint", "ref_gap") else TOL_FREE_M) + 1e-9)
    return X, S2, {"smoothing_move_max_m": round(max(free), 3) if free else 0.0, "rounds": rounds,
                   "points_with_loosened_tolerance": loosened,
                   "spacing_m": [round(min(math.dist(X[i], X[i + 1]) for i in range(len(X) - 1)), 4),
                                 round(max(math.dist(X[i], X[i + 1]) for i in range(len(X) - 1)), 4)]}


class _Poly:
    """A polyline with geometric stations, for the fillet pass."""

    def __init__(self, P):
        self.P = P
        self.g = fh.stations(P)

    def at(self, g):
        return point_at(self.P, self.g, min(max(g, 0.0), self.g[-1]))

    def nearest(self, p, g0, g1):
        """(distance, station) of the nearest point on the stretch [g0, g1]."""
        i0 = max(0, idx_at(self.g, max(g0, 0.0)))
        i1 = min(len(self.P) - 1, idx_at(self.g, min(g1, self.g[-1])) + 1)
        best = project(p, self.P, self.g, i0, i1)
        return (best[0], best[1]) if best else (float("inf"), g0)


def junction_fillets(seq, climb, corners, lap, closed=True):
    """Off the climb, every corner OSM draws as one junction node or a few facets (C12, C13, C14 Paradise ->
    US-40, C15 exit 259, C16 Colfax -> US-6, C18 the ramp -> 19th St, and the few jogs beside them) becomes an
    arc tangent to both arms, so the smoothing that follows has a curve to smooth instead of a chevron.

    Measured 2026-10-12 on the built Drive-1 road (ledger 0048 "P2 integrated", the drive lens): C12 / C13 were
    single-vertex chevrons of 70.8 / 71.7 deg (built R 3.4 / 3.3 m against the aerial's 14.9 / 16.08 m, inner
    edge R 0.3 / 0.1 m: the ribbon folded, a 0.61 m step and grass across half the lane at C13), and US-40 at
    exit 259, C14, the lid's east end and the Colfax turn-back turned 37-72 deg at single vertices.

    A **facet** is a vertex off the climb (``climb_st_m``; its smoothing pads included) that turns more than
    ``FILLET_STEP_DEG`` or tighter than ``FILLET_R_FACET_M`` over its own spacing; facets within
    ``FILLET_CLUSTER_M`` of each other are one corner. Its arms are the lines through the first / last facet along
    the ``FILLET_ARM_M`` of line before / after it. The arc's radius is the corner's measured ``radius_m``
    (hairpin_fit.corners, matched within ``FILLET_MATCH_M``: C12 and C13); elsewhere ``FILLET_R_M``, reduced in
    0.25 m steps (not below ``FILLET_R_MIN_M``) until the arc stays within ``FILLET_DEPART_M`` of the OSM line
    (a junction box's pavement). Either way both tangent points must lie on their arms (within
    ``FILLET_ON_ARM_M``) and clear of the neighbouring corners, and every traced paint point the arc replaces
    stays within ``FILLET_PAINT_M`` of it (the paint outranks a radius: a measured radius is reduced, and reported
    so, until the arc keeps the painted arms). Returns (seq with each corner's stretch replaced
    by arc points, kind ``fillet``; the regions to resample + smooth; the per-corner report)."""
    P = [e[0] for e in seq]
    S = [e[1] for e in seq]
    poly = _Poly(P)
    g = poly.g
    steps = fh.signed_steps(P)
    c0, c1 = climb

    def free(s):            # off the JUDGED climb (its pads and the seam pad are judged by the gate's (e) too)
        return not (c0 <= s <= c1) and S[0] + FILLET_ARM_M < s < S[-1] - FILLET_ARM_M

    facets = []
    for i in range(1, len(P) - 1):
        if not free(S[i]):
            continue
        sp = 0.5 * (g[i + 1] - g[i - 1])
        a = abs(steps[i])
        if a * DEG > FILLET_STEP_DEG or (a * DEG > 3.0 and sp / a < FILLET_R_FACET_M):
            facets.append(i)
    clusters = []
    for i in facets:
        if clusters and g[i] - g[clusters[-1][-1]] <= FILLET_CLUSTER_M:
            clusters[-1].append(i)
        else:
            clusters.append([i])
    reps, cuts = [], []        # cuts: (gA, gB, arc points, sA, sB)
    for k, cl in enumerate(clusters):
        ia, ib = cl[0], cl[-1]
        ga, gb = g[ia], g[ib]
        s_mid = 0.5 * (S[ia] + S[ib])
        pa, pb = P[ia], P[ib]
        qa, qb = poly.at(ga - FILLET_ARM_M), poly.at(gb + FILLET_ARM_M)
        ua = _unit((pa[0] - qa[0], pa[1] - qa[1]))
        ub = _unit((qb[0] - pb[0], qb[1] - pb[1]))
        delta = fh._wrap(math.atan2(ub[1], ub[0]) - math.atan2(ua[1], ua[0]))
        rep = {"osm_st_m": [round(S[ia], 1), round(S[ib], 1)], "facets": len(cl),
               "facet_steps_deg": [round(steps[i] * DEG, 1) for i in cl], "turn_deg": round(delta * DEG, 1)}
        if abs(delta) * DEG < FILLET_MIN_TURN_DEG:
            reps.append({**rep, "result": "skipped: turns less than FILLET_MIN_TURN_DEG"})
            continue
        den = ua[0] * ub[1] - ua[1] * ub[0]
        if abs(den) < 1e-9:
            reps.append({**rep, "result": "FAILED: parallel arms"})
            continue
        t = ((pb[0] - pa[0]) * ub[1] - (pb[1] - pa[1]) * ub[0]) / den
        X = (pa[0] + t * ua[0], pa[1] + t * ua[1])
        meas = None
        for c in corners or []:
            if c.get("radius_m") and c.get("st_m") is not None and abs(float(c["st_m"]) - s_mid) <= FILLET_MATCH_M:
                meas = c
        r_list = [float(meas["radius_m"])] if meas else []
        r = FILLET_R_M if not meas else float(meas["radius_m"]) - 0.25
        while r >= FILLET_R_MIN_M - 1e-9:
            r_list.append(round(r, 2))
            r -= 0.25
        g_prev = cuts[-1][1] + 1.0 if cuts else g[0] + 1.0
        g_next = g[clusters[k + 1][0]] - 1.0 if k + 1 < len(clusters) else g[-1] - 1.0
        sign = 1.0 if delta > 0 else -1.0
        got = None
        tried = []
        for R in r_list:
            T = R * math.tan(abs(delta) / 2.0)
            A = (X[0] - T * ua[0], X[1] - T * ua[1])
            B = (X[0] + T * ub[0], X[1] + T * ub[1])
            dA, gA = poly.nearest(A, ga - T - 3 * FILLET_ARM_M, ga + FILLET_ARM_M)
            dB, gB = poly.nearest(B, gb - FILLET_ARM_M, gb + T + 3 * FILLET_ARM_M)
            why = []
            if dA > FILLET_ON_ARM_M or dB > FILLET_ON_ARM_M:
                why.append(f"tangent point off its arm ({dA:.2f} / {dB:.2f} m)")
            if gA <= g_prev or gB >= g_next or not (free(S[idx_at(g, gA)]) and free(S[idx_at(g, gB)])):
                why.append("tangent point past a neighbouring corner, the climb or the seam")
            Cc = (A[0] - sign * R * ua[1], A[1] + sign * R * ua[0])
            a0 = math.atan2(A[1] - Cc[1], A[0] - Cc[0])
            n = max(2, math.ceil(abs(delta) * R / SPACING_M))
            arc = [(Cc[0] + R * math.cos(a0 + delta * j / n), Cc[1] + R * math.sin(a0 + delta * j / n)) for j in range(n + 1)]
            dep = max(poly.nearest(q, gA - 1.0, gB + 1.0)[0] for q in arc) if not why else None
            if dep is not None and not meas and dep > FILLET_DEPART_M:
                why.append(f"leaves the OSM line by {dep:.2f} m")
            if not why:                     # traced paint the arc replaces stays on it: the paint outranks a radius
                arc_poly = _Poly(arc)
                off = [arc_poly.nearest(P[j], 0.0, arc_poly.g[-1])[0] for j in range(len(P))
                       if seq[j][2] == "paint" and gA < g[j] < gB]
                if off and max(off) > FILLET_PAINT_M:
                    why.append(f"cuts the traced paint by {max(off):.2f} m")
            tried.append(R)
            if not why:
                got = (R, T, gA, gB, arc, dep)
                break
            if meas and R == r_list[0]:
                rep["measured_radius_failed"] = "; ".join(why)
        if got is None:
            reps.append({**rep, "result": "FAILED: no radius fits", "radii_tried_m": [tried[0], tried[-1]] if tried else []})
            continue
        R, T, gA, gB, arc, dep = got
        sA = S[idx_at(g, gA)] + (gA - g[idx_at(g, gA)])
        sB = S[idx_at(g, gB)] + (gB - g[idx_at(g, gB)])
        cuts.append((gA, gB, arc, sA, sB))
        reps.append({**rep, "result": "filleted", "radius_m": R,
                     "radius_from": (f"measured ({meas['id']})" if meas and R == float(meas["radius_m"]) else
                                     "measured, reduced to keep the arms / the paint" if meas else
                                     "FILLET_R_M, reduced to fit" if R < FILLET_R_M else "FILLET_R_M"),
                     "corner": meas["id"] if meas else None, "tangent_m": round(T, 2),
                     "replaced_osm_st_m": [round(sA, 1), round(sB, 1)], "arc_points": len(arc),
                     "max_departure_from_osm_m": round(dep, 2)})
    if not cuts:
        return seq, [], reps
    out, regions = [], []
    j = 0
    for gA, gB, arc, sA, sB in cuts:
        while j < len(seq) and g[j] < gA - 1e-6:
            out.append(seq[j])
            j += 1
        n = len(arc) - 1
        for m, q in enumerate(arc):
            out.append((q, sA + (sB - sA) * m / n, "fillet", None))
        while j < len(seq) and g[j] <= gB + 1e-6:
            j += 1
        regions.append(("fillet", sA - REGION_PAD_M, sB + REGION_PAD_M))
    out.extend(seq[j:])
    return out, regions, reps


def build(osm_path, traces, climb_st, log=print, corners=None):
    """The paint centreline as a GeoJSON dict (the OSM file's schema) + an info dict."""
    gj = json.loads(Path(osm_path).read_text(encoding="utf-8"))
    feats = gj["features"]
    fidx = next(i for i, f in enumerate(feats) if (f.get("properties") or {}).get("kind") == "full")
    feat = feats[fidx]
    coords = feat["geometry"]["coordinates"]
    lonlat = [(float(c[0]), float(c[1])) for c in coords]
    closed = len(lonlat) > 2 and math.dist(lonlat[0], lonlat[-1]) < 1e-9
    F = Frame(lonlat)
    P = [F.xy(*c) for c in lonlat]
    st = fh.stations(P)
    S_osm = fh.signed_steps(P)
    lap = st[-1]
    widths = list((feat.get("properties") or {}).get("widths_m") or [])
    targets = load_targets(traces, F, P, st)
    comp = composite(P, st, targets, closed)
    seq = _unwrap_seq(comp, lap) if closed else comp
    seq, fillet_regions, fillet_reports = junction_fillets(seq, climb_st, corners, lap, closed)
    for fr in fillet_reports:
        log(f"[paint] junction fillet at OSM st {fr['osm_st_m']}: {fr['result']}"
            + (f", R {fr['radius_m']} m ({fr['radius_from']})" if fr.get("radius_m") else ""))
    c0, c1 = climb_st
    wrap = closed and c0 <= 1.0
    regions = [("climb", (c0 - SEAM_PAD_M) if wrap else max(0.0, c0 - CLIMB_PAD_M), min(c1 + CLIMB_PAD_M, lap - SEAM_PAD_M - 2.0))]
    run = None
    for e in seq:
        if e[2] in ("osm", "fillet"):
            continue
        if run is not None and e[1] - run[1] <= 2 * REGION_PAD_M:
            run[1] = e[1]
        else:
            if run is not None:
                regions.append(("moved", run[0] - REGION_PAD_M, run[1] + REGION_PAD_M))
            run = [e[1], e[1]]
    if run is not None:
        regions.append(("moved", run[0] - REGION_PAD_M, run[1] + REGION_PAD_M))
    regions = _merge_regions(regions + fillet_regions)
    out = []  # (point, osm station, kind, raw index or None)
    region_reports = []
    pos = 0
    for name, ra, rb in regions:
        ia = next(i for i in range(pos, len(seq)) if seq[i][1] >= ra)
        ib = max(i for i in range(ia, len(seq)) if seq[i][1] <= rb)
        out.extend(seq[pos:ia])
        # resample in pieces split at v0 (station 0 stays a vertex) and at junction kinks
        cuts = [ia] + [i for i in range(ia + 1, ib) if seq[i][1] == 0.0 or
                       (seq[i][3] is not None and seq[i][2] != "paint" and abs(S_osm[seq[i][3]]) * DEG > KINK_DEG
                        and not (c0 <= seq[i][1] <= c1))] + [ib]
        Q, srcs, kinds, bounds = [], [], [], []
        for a, b in zip(cuts, cuts[1:]):
            piece = [e[0] for e in seq[a:b + 1]]
            q, frac = resample_poly(piece, SPACING_M)
            qa = max(0, len(Q) - 1)
            for m, (j, t) in enumerate(frac):
                if Q and m == 0:
                    continue
                Q.append(q[m])
                srcs.append(seq[a + j][1] + t * (seq[a + min(j + 1, b - a)][1] - seq[a + j][1]))
                kinds.append(seq[a + (j if t < 0.5 else min(j + 1, b - a))][2])
            bounds.append((qa, len(Q) - 1))
        kink_s = [seq[i][1] for i in cuts[1:-1] if seq[i][1] != 0.0]
        pinned = [k < 3 or k >= len(Q) - 3 or any(abs(srcs[k] - ks) <= KINK_PIN_M for ks in kink_s) for k in range(len(Q))]
        tol = [TOL_PAINT_M if kd in ("paint", "ref_gap") else TOL_FREE_M for kd in kinds]
        judged = [c0 <= sq <= c1 for sq in srcs] if name == "climb" else [False] * len(Q)
        X, srcs, rep = smooth_region(Q, srcs, pinned, tol, kinds, bounds, judged)
        region_reports.append({"name": name, "osm_st_m": [round(seq[ia][1], 1), round(seq[ib][1], 1)], "points": len(X),
                               "pinned_kinks_osm_st_m": [round(k, 1) for k in kink_s], **rep})
        for k in range(len(X)):
            out.append((X[k], srcs[k], kinds[k], None))
        pos = ib + 1
    out.extend(seq[pos:])
    if closed:  # one lap from v0 (station 0), then the closing vertex repeats v0 exactly
        k0 = min(range(len(out)), key=lambda i: abs(out[i][1]))
        out = out[k0:] + [(e[0], e[1] + lap, e[2], e[3]) for e in out[:k0]]
    new_coords = [list(coords[e[3]]) if (e[3] is not None and e[2] == "osm") else [round(v, 9) for v in F.ll(*e[0])] for e in out]
    srcs = [e[1] for e in out]
    kinds = [e[2] for e in out]
    raws = [e[3] if e[2] == "osm" else None for e in out]
    if closed:
        new_coords.append(list(new_coords[0]))
        srcs.append(srcs[0] + lap)
        kinds.append(kinds[0])
        raws.append(raws[0])
    new_w = []
    if widths:
        for s, raw in zip(srcs, raws):
            if raw is not None:
                new_w.append(widths[raw])
                continue
            s = s % lap if closed else min(max(s, 0.0), lap)
            i = idx_at(st, s)
            j = min(i + 1, len(st) - 1)
            t = 0.0 if st[j] == st[i] else (s - st[i]) / (st[j] - st[i])
            new_w.append(round(widths[i] + t * (widths[j] - widths[i]), 2))
    props = dict(feat.get("properties") or {})
    props["point_count"] = len(new_coords)
    props["length_m"] = round(polyline_length([tuple(c) for c in new_coords]), 1)
    if widths:
        props["widths_m"] = new_w
    props["osm_station_m"] = [round(s, 3) for s in srcs]
    new_feat = dict(feat, properties=props, geometry={"type": "LineString", "coordinates": new_coords})
    out_gj = dict(gj)
    out_gj["features"] = list(feats)
    out_gj["features"][fidx] = new_feat
    info = {"targets": [{"id": t["id"], "window": t["window"], "kind": t["kind"], "osm_st_m": [round(t["s_a"], 1), round(t["s_b"], 1)],
                         "points": len(t["pts"]), "offset_at_ends_m": [round(math.hypot(*t["D_a"]), 2), round(math.hypot(*t["D_b"]), 2)],
                         "core_points_on_yellow_circle": t["n_core_on_circle"]} for t in targets],
            "regions": region_reports, "junction_fillets": fillet_reports,
            "frame": {"origin_lonlat": [F.lon0, F.lat0]}, "kinds": kinds}
    return out_gj, info


def _merge_regions(regions):
    rs = sorted(regions, key=lambda r: r[1])
    out = []
    for name, a, b in rs:
        if out and a <= out[-1][2]:
            out[-1] = ("climb" if "climb" in (out[-1][0], name) else name, out[-1][1], max(out[-1][2], b))
        else:
            out.append((name, a, b))
    return out


def _unwrap_seq(comp, lap):
    """The composite as a station-ordered sequence that starts SEAM_PAD_M before v0 (the lap's last stretch
    at negative stations), so the climb region can run across the seam. The closing vertex is dropped: v0
    stands for it."""
    body = [e for e in comp if e[1] < lap - 1e-9]
    cut = lap - SEAM_PAD_M - 1.0
    tail = [(e[0], e[1] - lap, e[2], e[3]) for e in body if e[1] > cut]
    head = [e for e in body if e[1] <= cut]
    return tail + head


# --------------------------------------------------------------------------------------------------
def report(gj, info, osm_path, traces, radii, climb_st):
    """Per window: medium+ paint to the new line and to OSM; per corner: the line's tightest radius vs the
    measured one."""
    import verify_centreline_paint as vp  # noqa: E402  (the judge's own distance measure)
    new = vp.Line.from_geojson(gj)
    osm = vp.Line.from_geojson(json.loads(Path(osm_path).read_text(encoding="utf-8")))
    per = []
    for w in traces["windows"]:
        pts = vp.paint_points(traces, w)
        if not pts:
            continue
        dn = [new.distance(*p) for p in pts]
        do = [osm.distance(*p) for p in pts]
        per.append({"window": w["id"], "medium_plus_points": len(pts),
                    "new_max_m": round(max(dn), 2), "new_median_m": round(stt.median(dn), 2),
                    "osm_max_m": round(max(do), 2), "osm_median_m": round(stt.median(do), 2)})
    corners = []
    for cid, R in (radii or {}).items():
        w = next((x for x in traces["windows"] if x["id"] == cid), None)
        if not w or not w.get("core") or not w["core"].get("yellow_circle"):
            continue
        yc = w["core"]["yellow_circle"]
        c = new.frame_xy_from_traces(traces, *yc["centre_xz_m"])
        rr = new.min_radius_near(c, yc["R_m"] + 6.0)
        corners.append({"id": cid, "measured_radius_m": R, "yellow_circle_R_m": yc["R_m"], "yellow_circle_good": yc["good"],
                        "line_tightest_radius_10m_chord_m": rr})
    return {"windows": per, "corners": corners}


def text_md5(path) -> str:
    """md5 of a text file's content with LF line ends (as git stores it), so a Windows checkout's CRLF copy
    hashes the same as the committed file."""
    return hashlib.md5(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _rel(path, base):
    try:
        return str(Path(path).resolve().relative_to(base)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def run(project_dir, osm=None, traces_path=None, out=None, report_path=None, log=print) -> dict:
    project_dir = Path(project_dir).resolve()
    data = project_dir / "data"
    cfg = json.loads((project_dir / "track.config.json").read_text(encoding="utf-8"))
    osm_path = Path(osm) if osm else data / "centerline.osm.geojson"
    cl_path = data / "centerline.geojson"
    if not osm_path.exists():
        if not cl_path.exists():
            raise SystemExit(f"[paint] no OSM centreline: {osm_path}")
        props = next(f for f in json.loads(cl_path.read_text(encoding="utf-8"))["features"]
                     if (f.get("properties") or {}).get("kind") == "full").get("properties") or {}
        if "paint_centreline" in props:
            raise SystemExit(f"[paint] {cl_path} is already a paint centreline and {osm_path} is missing")
        shutil.copyfile(cl_path, osm_path)
        log(f"[paint] kept the gps stage's line as {osm_path}")
    else:
        # a fresh gps run rewrites data/centerline.geojson with OSM: that is the new source
        if cl_path.exists() and cl_path != osm_path:
            props = next(f for f in json.loads(cl_path.read_text(encoding="utf-8"))["features"]
                         if (f.get("properties") or {}).get("kind") == "full").get("properties") or {}
            if "paint_centreline" not in props and cl_path.read_bytes() != osm_path.read_bytes():
                shutil.copyfile(cl_path, osm_path)
                log(f"[paint] data/centerline.geojson is a new gps output: it replaces {osm_path}")
    traces_path = Path(traces_path) if traces_path else data / "aerial" / "paint_traces.json"
    traces = json.loads(traces_path.read_text(encoding="utf-8"))
    climb = (cfg.get("hairpin_fit") or {}).get("climb_st_m") or [0, 0]
    radii = {c["id"]: c.get("radius_m") for c in (cfg.get("hairpin_fit") or {}).get("corners") or []}
    gj, info = build(osm_path, traces, climb, log, corners=(cfg.get("hairpin_fit") or {}).get("corners") or [])
    feat = next(f for f in gj["features"] if (f.get("properties") or {}).get("kind") == "full")
    md5 = text_md5(osm_path)
    feat["properties"]["paint_centreline"] = {
        "tool": "tools/paint_centreline.py", "osm_source": _rel(osm_path, project_dir),
        "osm_source_md5": md5, "traces": _rel(traces_path, project_dir),
        "traces_md5": text_md5(traces_path),
        "climb_st_m": climb, "params": PARAMS,
        "frame": "lon/lat WGS84 (the OSM frame); computed in local ENU metres about the OSM line's centroid "
                 "(scripts/geometry/projection.py series); osm_station_m = each vertex's station on the OSM line "
                 "(geojson frame, metres from its v0)",
        "_doc": "the OSM line moved onto the traced paint (data/aerial/paint_traces.json) and resampled; judged by "
                "tools/verify_centreline_paint.py. The OSM line itself is the source file osm_source.",
    }
    out_path = Path(out) if out else cl_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(gj)
    if out_path == cl_path and cl_path.exists():
        prev = next((f for f in json.loads(cl_path.read_text(encoding="utf-8"))["features"]
                     if (f.get("properties") or {}).get("kind") == "full"), {}).get("properties") or {}
        if "paint_centreline" in prev and cl_path.read_text(encoding="utf-8") != text:
            shutil.copyfile(cl_path, data / "centerline.previous.geojson")
            log("[paint] kept the paint centreline it replaces as data/centerline.previous.geojson "
                "(tools/remap_centreline_config.py maps the config from it)")
    out_path.write_text(text, encoding="utf-8", newline="\n")
    rep = report(gj, info, osm_path, traces, radii, climb)
    rep_path = Path(report_path) if report_path else data / "aerial" / "paint_centreline.json"
    full = {"tool": "tools/paint_centreline.py", "osm_source": feat["properties"]["paint_centreline"]["osm_source"],
            "osm_source_md5": md5, "out": _rel(out_path, project_dir), "out_md5": text_md5(out_path),
            "points": feat["properties"]["point_count"], "length_m": feat["properties"]["length_m"],
            "osm_points": len(json.loads(osm_path.read_text(encoding="utf-8"))["features"][0]["geometry"]["coordinates"]),
            "params": PARAMS, "targets": info["targets"], "regions": info["regions"],
            "junction_fillets": info["junction_fillets"], **rep}
    rep_path.parent.mkdir(parents=True, exist_ok=True)
    rep_path.write_text(json.dumps(full, indent=1), encoding="utf-8", newline="\n")
    log(f"[paint] wrote {out_path} ({full['points']} points, {full['length_m']} m) and {rep_path}")
    return full


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_dir")
    ap.add_argument("--osm")
    ap.add_argument("--traces")
    ap.add_argument("--out")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    try:
        run(a.project_dir, a.osm, a.traces, a.out, a.report)
    except (SystemExit, FileNotFoundError) as e:
        print(f"[paint] {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
