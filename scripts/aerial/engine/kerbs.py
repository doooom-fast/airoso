"""Racing kerbs read off the aerial: by their alternating blocks (colour-blind), and by colour along a fitted edge.

Generalised from tools/kerb_blocks.py + tools/kerb_offsets.py (branch claude/circuit-kerbs-lm, ledger 0081 rounds 1-3)
and Pikes Peak's kerb_trace (retrace.py, ledger 0085). NAIP's faded kerb red reads pink or grey, the white like pale
sand; what every painted kerb still shows is its BLOCKS, light and dark alternating ALONG the edge, in phase across
the kerb's width. Kevin 2026-11-07: "Follow curbs and road wear, it's easy for human eye".

``Line``: an ENU polyline with half-widths (a gate line, or a measured strip's centre and width): ``at(s)`` gives the
lane edge's station frame, ``grid(s, side, offs)`` the luminance there.

``scan``    candidates: every SCAN_STEP along a side, in a SCAN_WIN window, each column OFF_LO..OFF_HI past the edge
            detrended; flagged where some column's strongest sine at a block period reaches SCAN_AMP on a light mean
            (SCAN_MEAN); runs < SCAN_MIN_RUN dropped, gaps <= SCAN_GAP joined (kerb_blocks.py's rules).
``measure`` a run's paint across the edge (kerb_offsets.py's rules, every number as calibrated there): a 0.25 x 0.075 m
            grid -3.5..+3.5 m; per 1 m station a 6 m window, columns detrended; the reference waveform = the column
            with the most block energy, then the band's mean (2 refinements); each column's matched-filter coefficient
            on it; the band = the contiguous columns over HALF its peak; its crossings are the paint's inner / outer edge;
            a station counts when the reference's block amplitude >= MIN_AMP; in / out = medians; the extent walked out
            while the band's amplitude (3 m window) stays over half its median, gaps <= 3 m, <= 15 m past the span.
``colour``  per station along a fitted edge: the strip 0.15-0.6 m outside it, red on >= 15 % of a 4 m window, or white
            blocks in a ~1 m rhythm, is kerb; white on > 80 % with no rhythm is an edge line (retrace.py kerb_trace).
Every threshold is [invented] tuning (GATES-CHANGELOG 2026-11-05 round 3 for the block reader).
"""
from __future__ import annotations

import math

import numpy as np

from . import channels as chn
from . import geom

DS_M = 0.25
DO_M = 0.075
O_LO_M, O_HI_M = -3.5, 3.5
STEP_M = 1.0
WIN_M = 6.0
PERIOD_M = (1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 3.0)
REFINE = 2
HALF = 0.5
MIN_AMP = 8.0
EXT_WIN_M = 3.0
EXT_FRAC = 0.5
GAP_M = 3.0
GROW_M = 15.0

SCAN_STEP = 0.25
SCAN_OFF = (-2.0, 1.5, 0.15)
SCAN_WIN = 6.0
SCAN_PERIODS = (1.5, 1.75, 2.0, 2.25, 2.5)
SCAN_AMP = 22.0
SCAN_MEAN = 125.0
SCAN_MIN_RUN = 5.0
SCAN_GAP = 4.0


def luma(rgb):
    """Pillow's ``convert("L")`` (ITU-R 601, integer): the luminance the block reader was calibrated on."""
    r = rgb[..., 0].astype(np.int64)
    g = rgb[..., 1].astype(np.int64)
    b = rgb[..., 2].astype(np.int64)
    return ((r * 19595 + g * 38470 + b * 7471 + 0x8000) >> 16).astype(np.float64)


class Line:
    def __init__(self, ortho, P_en, widths, lum=None):
        self.o = ortho
        self.P = np.asarray(P_en, float)
        self.Wd = np.asarray(widths, float)
        self.st = geom.cumlen(self.P)
        self.lum = lum if lum is not None else luma(ortho.rgb)

    def at(self, s):
        P, st = self.P, self.st
        s = np.clip(np.asarray(s, float), 0.0, st[-1])
        j = np.clip(np.searchsorted(st, s, side="right") - 1, 0, len(P) - 2)
        t = (s - st[j]) / np.where(st[j + 1] - st[j] > 0, st[j + 1] - st[j], 1.0)
        x = P[j, 0] + (P[j + 1, 0] - P[j, 0]) * t
        n = P[j, 1] + (P[j + 1, 1] - P[j, 1]) * t
        a, b = P[np.maximum(0, j - 1)], P[np.minimum(len(P) - 1, j + 2)]
        tx, tz = b[:, 0] - a[:, 0], b[:, 1] - a[:, 1]
        L = np.hypot(tx, tz)
        L = np.where(L > 0, L, 1.0)
        return x, n, -tz / L, tx / L, (self.Wd[j] + (self.Wd[j + 1] - self.Wd[j]) * t) / 2.0

    def en(self, s, side, o):
        x, n, lx, lz, hw = self.at(np.atleast_1d(np.asarray(s, float)))
        d = side * (hw[:, None] + np.atleast_1d(o)[None, :])
        return x[:, None] + lx[:, None] * d, n[:, None] + lz[:, None] * d

    def grid(self, s, side, offs):
        E, N = self.en(s, side, offs)
        px, py = self.o.en_to_px(E, N)
        ok = (px >= 0) & (py >= 0) & (px <= self.o.W - 1.001) & (py <= self.o.H - 1.001)
        return np.where(ok, chn.sample(self.lum, px, py), np.nan)


def detrend(v):
    n = v.shape[0]
    t = np.arange(n) - (n - 1) / 2.0
    v = v - v.mean(axis=0)
    slope = (t[:, None] * v).sum(axis=0) / max((t * t).sum(), 1e-9)
    return v - slope[None, :] * t[:, None]


def block_amp(v, periods=PERIOD_M, ds=DS_M):
    n = v.shape[0]
    q = np.arange(n) * ds
    best = np.zeros(v.shape[1:]) if v.ndim > 1 else 0.0
    for per in periods:
        w = 2 * math.pi / per
        a = np.tensordot(np.cos(w * q), v, axes=(0, 0))
        b = np.tensordot(np.sin(w * q), v, axes=(0, 0))
        best = np.maximum(best, 2 * np.hypot(a, b) / n)
    return best


def crossings(k, offs, half=HALF):
    c = int(np.argmax(k))
    pk = k[c]
    if pk <= 0:
        return None
    thr = half * pk
    lo = c
    while lo > 0 and k[lo - 1] > thr:
        lo -= 1
    hi = c
    while hi < len(k) - 1 and k[hi + 1] > thr:
        hi += 1
    if lo == 0 or hi == len(k) - 1:
        return None
    o_in = offs[lo - 1] + (thr - k[lo - 1]) / (k[lo] - k[lo - 1]) * (offs[lo] - offs[lo - 1])
    o_out = offs[hi] + (k[hi] - thr) / (k[hi] - k[hi + 1]) * (offs[hi + 1] - offs[hi])
    return o_in, o_out, lo, hi


def station(G, offs):
    if np.isnan(G).any():
        return None
    D = detrend(G)
    amp = block_amp(D)
    ref = D[:, int(np.argmax(amp))]
    band = None
    for _ in range(REFINE + 1):
        rr = float((ref * ref).sum())
        if rr <= 0:
            return None
        k = (D * ref[:, None]).sum(axis=0) / rr
        band = crossings(k, offs)
        if band is None:
            return None
        ref = D[:, band[2]:band[3] + 1].mean(axis=1)
    return band[0], band[1], float(block_amp(ref)), k


def measure(line: Line, side: int, s0: float, s1: float):
    """One run's paint across the edge and its extent (kerb_offsets.py measure())."""
    offs = np.arange(O_LO_M, O_HI_M + 1e-9, DO_M)
    half = int(round(WIN_M / 2 / DS_M))
    lo_s, hi_s = s0 - GROW_M - WIN_M, s1 + GROW_M + WIN_M
    ss = np.arange(lo_s, hi_s + 1e-9, DS_M)
    G = line.grid(ss, side, offs)
    rows = []
    s = s0
    while s <= s1 + 1e-6:
        i = int(round((s - lo_s) / DS_M))
        r = station(G[i - half:i + half + 1], offs)
        if r is not None and r[2] >= MIN_AMP:
            rows.append((s, r[0], r[1], r[2]))
        s += STEP_M
    if not rows:
        return None
    ins = sorted(r[1] for r in rows)
    outs = sorted(r[2] for r in rows)
    o_in, o_out = ins[len(ins) // 2], outs[len(outs) // 2]
    amp_med = float(np.median([r[3] for r in rows]))
    cols = (offs >= o_in) & (offs <= o_out)
    if not cols.any():
        cols = np.abs(offs - (o_in + o_out) / 2) <= DO_M
    b = np.nanmean(G[:, cols], axis=1)
    hw = int(round(EXT_WIN_M / 2 / DS_M))
    a = np.zeros(len(ss))
    for i in range(hw, len(ss) - hw):
        v = b[i - hw:i + hw + 1]
        if not np.isnan(v).any():
            a[i] = block_amp(detrend(v[:, None]))[0]
    i0, i1 = int(round((s0 - lo_s) / DS_M)), int(round((s1 - lo_s) / DS_M))
    ok = a >= EXT_FRAC * float(np.median(a[i0:i1 + 1]))
    inside = np.where(ok[i0:i1 + 1])[0] + i0
    if not len(inside):
        return None
    gap = int(round(GAP_M / DS_M))
    g0, g1 = int(round((s0 - GROW_M - lo_s) / DS_M)), int(round((s1 + GROW_M - lo_s) / DS_M))
    lo, hi = int(inside[0]), int(inside[-1])
    while True:
        nxt = [q for q in range(lo - 1, max(g0, lo - gap) - 1, -1) if ok[q]]
        if not nxt:
            break
        lo = nxt[0]
    while True:
        nxt = [q for q in range(hi + 1, min(g1, hi + gap) + 1) if ok[q]]
        if not nxt:
            break
        hi = nxt[0]
    return {"in_m": round(o_in, 2), "out_m": round(o_out, 2), "s0": round(float(ss[lo]), 2), "s1": round(float(ss[hi]), 2),
            "stations_measured": len(rows), "stations_tried": int(round((s1 - s0) / STEP_M)) + 1,
            "block_amp_median": round(amp_med, 1)}


def scan(line: Line, side: int, s_from: float = 0.0, s_to: float | None = None):
    """Candidate kerb runs along one side by their block rhythm (kerb_blocks.py's rules, vectorised)."""
    s_to = line.st[-1] if s_to is None else s_to
    lo, hi, st = SCAN_OFF
    offs = np.arange(lo, hi + 1e-9, st)
    ss = np.arange(s_from, s_to, SCAN_STEP)
    G = line.grid(ss, side, offs)
    win = int(SCAN_WIN / SCAN_STEP)
    flag = np.zeros(len(ss), bool)
    for i in range(len(ss) - win):
        V = G[i:i + win]
        if np.isnan(V).any():
            continue
        mean = V.mean(axis=0)
        amp = block_amp(detrend(V), SCAN_PERIODS, SCAN_STEP)
        if ((amp >= SCAN_AMP) & (mean >= SCAN_MEAN)).any():
            flag[i + win // 2] = True
    out = []
    i = 0
    n = len(ss)
    while i < n:
        if not flag[i]:
            i += 1
            continue
        j, last = i, i
        while j + 1 < n and (j + 1 - last) * SCAN_STEP <= SCAN_GAP:
            j += 1
            if flag[j]:
                last = j
        if (last - i) * SCAN_STEP >= SCAN_MIN_RUN:
            out.append((float(ss[i]), float(ss[last])))
        i = last + 1
    return out


def colour_runs(ctx, E, out_n, s):
    """Per-station labels along a fitted edge E (ENU) with outward normals: 'kerb', 'edge_line' or 'none'."""
    n = len(E)
    lab = np.array(["none"] * n, dtype=object)
    if n < 4:
        return lab
    sE = geom.cumlen(E)
    t_ = np.arange(0, sE[-1], 0.15)
    Q = np.c_[np.interp(t_, sE, E[:, 0]), np.interp(t_, sE, E[:, 1])]
    No = np.c_[np.interp(t_, sE, out_n[:, 0]), np.interp(t_, sE, out_n[:, 1])]
    red = np.zeros(len(t_))
    wh = np.zeros(len(t_))
    for o in (0.15, 0.3, 0.45, 0.6):
        red = np.maximum(red, ctx.sample("red", Q[:, 0] + o * No[:, 0], Q[:, 1] + o * No[:, 1]))
        wh = np.maximum(wh, ctx.sample("white", Q[:, 0] + o * No[:, 0], Q[:, 1] + o * No[:, 1]))
    rb, wb = red > 0.5, wh > 0.5
    for k in range(n):
        sel = np.abs(t_ - sE[k]) <= 2.0
        if sel.sum() < 10:
            continue
        fr, fw = rb[sel].mean(), wb[sel].mean()
        chg = np.abs(np.diff(wb[sel].astype(int))).sum() / 4.0
        if fr >= 0.15 or (0.25 <= fw <= 0.8 and chg >= 0.8):
            lab[k] = "kerb"
        elif fw > 0.8:
            lab[k] = "edge_line"
    return lab
