"""Geodesy and small 2-D helpers for the aerial measurement.

UTM on GRS80 (NAD83) by the Krueger n-series (3 terms: sub-millimetre inside a zone), so a NAIP pixel's
grid coordinate and an OSM lon/lat meet on one grid with NO datum shift; the registration step measures
what is left. ``ZONE`` is 13 (the Lariat; EPSG:26913). WGS84's flattening differs from GRS80's by 1e-10,
which is irrelevant here.

No thresholds live in this module (the circle fit's iteration limits are numerical, not judgements).
"""
from __future__ import annotations

import copy
import math

A = 6378137.0
F = 1 / 298.257222101  # GRS80
K0 = 0.9996
ZONE = 13
LON0 = math.radians(ZONE * 6 - 183)  # zone 13 central meridian, -105 deg
FE, FN = 500000.0, 0.0

_n = F / (2 - F)
_A = A / (1 + _n) * (1 + _n**2 / 4 + _n**4 / 64)
_alpha = [
    _n / 2 - 2 * _n**2 / 3 + 5 * _n**3 / 16,
    13 * _n**2 / 48 - 3 * _n**3 / 5,
    61 * _n**3 / 240,
]
_beta = [
    _n / 2 - 2 * _n**2 / 3 + 37 * _n**3 / 96,
    _n**2 / 48 + _n**3 / 15,
    17 * _n**3 / 480,
]
_delta = [
    2 * _n - 2 * _n**2 / 3 - 2 * _n**3,
    7 * _n**2 / 3 - 8 * _n**3 / 5,
    56 * _n**3 / 15,
]


def to_utm(lon, lat):
    """(lon, lat) degrees -> (E, N) metres, UTM zone ``ZONE`` on GRS80."""
    phi = math.radians(lat)
    lam = math.radians(lon) - LON0
    e = math.sqrt(F * (2 - F))
    t = math.sinh(math.atanh(math.sin(phi)) - e * math.atanh(e * math.sin(phi)))
    xi_p = math.atan2(t, math.cos(lam))
    eta_p = math.atanh(math.sin(lam) / math.sqrt(1 + t * t))
    xi = xi_p + sum(_alpha[j] * math.sin(2 * (j + 1) * xi_p) * math.cosh(2 * (j + 1) * eta_p) for j in range(3))
    eta = eta_p + sum(_alpha[j] * math.cos(2 * (j + 1) * xi_p) * math.sinh(2 * (j + 1) * eta_p) for j in range(3))
    return FE + K0 * _A * eta, FN + K0 * _A * xi


def from_utm(E, N):
    """(E, N) metres -> (lon, lat) degrees, the inverse of :func:`to_utm`."""
    xi = (N - FN) / (K0 * _A)
    eta = (E - FE) / (K0 * _A)
    xi_p = xi - sum(_beta[j] * math.sin(2 * (j + 1) * xi) * math.cosh(2 * (j + 1) * eta) for j in range(3))
    eta_p = eta - sum(_beta[j] * math.cos(2 * (j + 1) * xi) * math.sinh(2 * (j + 1) * eta) for j in range(3))
    chi = math.asin(math.sin(xi_p) / math.cosh(eta_p))
    phi = chi + sum(_delta[j] * math.sin(2 * (j + 1) * chi) for j in range(3))
    lam = LON0 + math.atan2(math.sinh(eta_p), math.cos(xi_p))
    return math.degrees(lam), math.degrees(phi)


def meters_per_degree(lat0):
    """(m per deg lon, m per deg lat) at lat0: the same series as scripts/geometry/projection.py."""
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    return m_lon, m_lat


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def project_on_polyline(p, pts):
    """Closest point on polyline pts to p: (distance, seg index, t, closest point, signed side)."""
    best = None
    for i in range(len(pts) - 1):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        if L2 == 0:
            continue
        t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
        cx, cy = ax + t * dx, ay + t * dy
        d = math.hypot(p[0] - cx, p[1] - cy)
        if best is None or d < best[0]:
            side = (dx * (p[1] - ay) - dy * (p[0] - ax))
            best = (d, i, t, (cx, cy), 1 if side > 0 else -1)
    return best


def fit_circle(pts):
    """Kasa algebraic start + Gauss-Newton geometric refinement. Returns (cx, cy, r, rms) or None."""
    n = len(pts)
    if n < 3:
        return None
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    u = [(p[0] - mx, p[1] - my) for p in pts]
    Suu = sum(a * a for a, b in u)
    Svv = sum(b * b for a, b in u)
    Suv = sum(a * b for a, b in u)
    Suuu = sum(a**3 for a, b in u)
    Svvv = sum(b**3 for a, b in u)
    Suvv = sum(a * b * b for a, b in u)
    Svuu = sum(b * a * a for a, b in u)
    det = Suu * Svv - Suv * Suv
    if abs(det) < 1e-12:
        return None
    rhs1 = 0.5 * (Suuu + Suvv)
    rhs2 = 0.5 * (Svvv + Svuu)
    uc = (rhs1 * Svv - rhs2 * Suv) / det
    vc = (Suu * rhs2 - Suv * rhs1) / det
    cx, cy = uc + mx, vc + my
    r = sum(math.hypot(p[0] - cx, p[1] - cy) for p in pts) / n
    for _ in range(50):
        JTJ = [[0.0] * 3 for _ in range(3)]
        JTr = [0.0] * 3
        for p in pts:
            dx, dy = p[0] - cx, p[1] - cy
            d = math.hypot(dx, dy) or 1e-9
            res = d - r
            J = (-dx / d, -dy / d, -1.0)
            for a in range(3):
                JTr[a] += J[a] * res
                for b in range(3):
                    JTJ[a][b] += J[a] * J[b]
        delta = solve3(JTJ, [-v for v in JTr])
        if delta is None:
            break
        cx += delta[0]
        cy += delta[1]
        r += delta[2]
        if max(abs(v) for v in delta) < 1e-7:
            break
    rms = math.sqrt(sum((math.hypot(p[0] - cx, p[1] - cy) - r) ** 2 for p in pts) / n)
    return cx, cy, r, rms


def solve3(M, v):
    a = copy.deepcopy(M)
    b = list(v)
    n = 3
    for i in range(n):
        piv = max(range(i, n), key=lambda k: abs(a[k][i]))
        if abs(a[piv][i]) < 1e-15:
            return None
        a[i], a[piv] = a[piv], a[i]
        b[i], b[piv] = b[piv], b[i]
        for k in range(i + 1, n):
            f = a[k][i] / a[i][i]
            for j in range(i, n):
                a[k][j] -= f * a[i][j]
            b[k] -= f * b[i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (b[i] - sum(a[i][j] * x[j] for j in range(i + 1, n))) / a[i][i]
    return x
