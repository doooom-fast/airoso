"""Polyline helpers in the local ENU frame (x = E, y = N, metres). No thresholds live here."""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def cumlen(P) -> np.ndarray:
    P = np.asarray(P, float)
    return np.r_[0.0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]


def closed_len(P) -> float:
    P = np.asarray(P, float)
    return float(cumlen(np.vstack([P, P[:1]]))[-1])


def resample(P, step: float, closed: bool = False) -> np.ndarray:
    """Even spacing by arc length. A closed loop does not repeat its first point."""
    P = np.asarray(P, float)
    if closed:
        P = np.vstack([P, P[:1]])
    s = cumlen(P)
    n = max(2, int(round(s[-1] / step)) + 1)
    t = np.linspace(0, s[-1], n)
    Q = np.c_[np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])]
    return Q[:-1] if closed else Q


def normals(P, closed: bool = False):
    """Unit tangent and LEFT normal (E, N) per vertex."""
    P = np.asarray(P, float)
    if closed:
        T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    else:
        T = np.gradient(P, axis=0)
    T = T / np.maximum(np.linalg.norm(T, axis=1)[:, None], 1e-12)
    return T, np.c_[-T[:, 1], T[:, 0]]


def smooth(P, sigma_m: float, step: float, closed: bool = False) -> np.ndarray:
    """Gaussian smoothing along the line (sigma in metres at the line's spacing ``step``)."""
    P = np.asarray(P, float)
    mode = "wrap" if closed else "nearest"
    s = sigma_m / step
    return np.c_[ndimage.gaussian_filter1d(P[:, 0], s, mode=mode), ndimage.gaussian_filter1d(P[:, 1], s, mode=mode)]


def running_median(x, ok, w: int = 21, closed: bool = False) -> np.ndarray:
    """Median of the ``ok`` samples within +-w//2 indices (wrapping if closed); gaps filled from the nearest value."""
    x = np.asarray(x, float)
    n = len(x)
    out = np.full(n, np.nan)
    idx = np.where(ok)[0]
    if len(idx) == 0:
        return out
    h = w // 2
    for i in range(n):
        d = np.abs(idx - i)
        if closed:
            d = np.minimum(d, n - d)
        sel = idx[d <= h]
        if len(sel) >= 3:
            out[i] = np.median(x[sel])
    good = np.isfinite(out)
    if good.any() and not good.all():
        gi = np.where(good)[0]
        if closed:
            xp = np.r_[gi - n, gi, gi + n]
            fp = np.r_[out[gi], out[gi], out[gi]]
        else:
            xp, fp = gi, out[gi]
        out[~good] = np.interp(np.where(~good)[0], xp, fp)
    return out


def runs(mask) -> list[tuple[int, int]]:
    """Index runs (inclusive) where mask is true."""
    out, a = [], None
    m = list(np.asarray(mask, bool)) + [False]
    for i, v in enumerate(m):
        if v and a is None:
            a = i
        if not v and a is not None:
            out.append((a, i - 1))
            a = None
    return out


def nearest(P, q):
    """(index, distance) of the vertex of P nearest q."""
    d = np.hypot(*(np.asarray(P, float) - np.asarray(q, float)).T)
    i = int(np.argmin(d))
    return i, float(d[i])


def min_radius(E, step: float = 0.5, over_m: float = 2.0) -> float:
    """The tightest radius of a polyline over ``over_m`` of its own arc length (turning per metre)."""
    E = np.asarray(E, float)
    if len(E) < 6:
        return float("inf")
    Q = resample(E, step)
    k = max(1, int(round(over_m / step)))
    if len(Q) < k + 3:
        return float("inf")
    T = np.diff(Q, axis=0)
    h = np.unwrap(np.arctan2(T[:, 1], T[:, 0]))
    dh = np.abs(h[k:] - h[:-k]) / over_m
    return float(1 / max(dh.max(), 1e-9))


def signed_area(P) -> float:
    P = np.asarray(P, float)
    return 0.5 * float(np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]))


def pct(x, nd: int = 3):
    x = np.abs(np.asarray(x, float))
    x = x[np.isfinite(x)]
    if not len(x):
        return None
    return {"p50": round(float(np.percentile(x, 50)), nd), "p95": round(float(np.percentile(x, 95)), nd),
            "max": round(float(x.max()), nd), "n": int(len(x))}
