"""The driven dark band, measured where a route crosses open pavement (a lot, an apron, a paddock) and has no edge.

Pikes Peak's lot_band (tracks/pikes-peak/source/road-course/maps_route.py, ledger 0085 "Route from the published
maps" 3), generalised: Kevin 2026-11-07, "how are you missing the dark areas that cars drive on? It's right there".
The route line (a published map's, or a sketch's) says WHERE on the open pavement to look; the band's limits are the
measurement.

Cross-sections every 1 m along the line (its normals off a +-5 m running mean of it), luminance:
  - samples past a measured pavement boundary on that side (``bounds``: offsets per section, nan = none) read as the
    section's own in-pavement 80th percentile, so grass or dirt (darker than concrete, never driven) is not a band;
  - smoothed SMOOTH_ACROSS_M (sigma) across and +-SMOOTH_ALONG_M along: cracks, joint sealant and kerb gaps are
    0.3-1 m wide, the band 4-12 m;
  - the floor: the darkest point within +-``valley`` m of the line;
  - each side's own surface: the 80th percentile ``nb`` m beyond the floor on that side (each side normalised against
    its own surface: a paddock is brighter than a lot's interior);
  - each limit: where the profile, going out from the floor, rises half way to that side's surface (sub-sample);
  - [unseen], never filled: band not ``min_depth`` grey levels below BOTH sides; width outside ``width``; a limit
    > JUMP_M off its running median of ``med_m`` m.
Both limits are running medians over ``med_m`` m of the seen sections (>= 5 in the window); a section with none holds
the nearest one and is flagged ``held_m`` (its distance to that one). Every number is Pikes Peak's [invented] tuning.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from . import channels as chn
from . import geom

SMOOTH_ACROSS_M = 1.0
SMOOTH_ALONG_M = 4.0
JUMP_M = 1.5


def measure(ctx, line, bounds=None, valley=6.0, nb=(3.0, 12.0), min_depth=6.0, med_m=15, width=(3.0, 20.0)):
    lum = ctx.ch["lum"]
    E = geom.resample(np.asarray(line, float), 1.0)
    Es = np.c_[ndimage.uniform_filter1d(E[:, 0], 11, mode="nearest"), ndimage.uniform_filter1d(E[:, 1], 11, mode="nearest")]
    _, L = geom.normals(Es)
    reach = valley + nb[1] + 2.0
    offs = np.arange(-reach, reach + 0.01, 0.25)
    X = Es[:, None, :] + offs[None, :, None] * L[:, None, :]
    px, py = ctx.o.en_to_px(X[..., 0], X[..., 1])
    raw = chn.sample(lum, px, py)
    n = len(Es)
    if bounds is not None:
        bl, br = bounds
        bl = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(bl)), bl) if len(bl) != n else np.asarray(bl, float)
        br = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(br)), br) if len(br) != n else np.asarray(br, float)
        for i in range(n):
            out = np.zeros(len(offs), bool)
            if np.isfinite(bl[i]):
                out |= offs > bl[i]
            if np.isfinite(br[i]):
                out |= offs < -br[i]
            if out.any() and (~out).sum() > 4:
                raw[i, out] = np.percentile(raw[i, ~out], 80)
    prof = ndimage.uniform_filter1d(ndimage.gaussian_filter1d(raw, SMOOTH_ACROSS_M / 0.25, axis=1),
                                    int(2 * SMOOTH_ALONG_M) + 1, axis=0)
    lo = np.full(n, np.nan)
    hi = np.full(n, np.nan)
    depth_lo = np.full(n, np.nan)
    depth_hi = np.full(n, np.nan)
    why = [""] * n
    core = np.abs(offs) <= valley
    for i in range(n):
        p = prof[i]
        k0 = np.where(core)[0][np.argmin(p[core])]
        f0 = offs[k0]
        side_lo = (offs <= f0 - nb[0]) & (offs >= f0 - nb[1])
        side_hi = (offs >= f0 + nb[0]) & (offs <= f0 + nb[1])
        lv_lo = np.percentile(p[side_lo], 80)
        lv_hi = np.percentile(p[side_hi], 80)
        depth_lo[i] = lv_lo - p[k0]
        depth_hi[i] = lv_hi - p[k0]
        if depth_lo[i] < min_depth or depth_hi[i] < min_depth:
            why[i] = f"unseen: band not {min_depth:g} grey levels below both sides"
            continue
        tl = p[k0] + depth_lo[i] / 2
        th = p[k0] + depth_hi[i] / 2
        k = k0
        while k + 1 < len(offs) and p[k + 1] < th:
            k += 1
        if k + 1 < len(offs):
            hi[i] = offs[k] + (th - p[k]) / max(p[k + 1] - p[k], 1e-6) * (offs[k + 1] - offs[k])
        k = k0
        while k - 1 >= 0 and p[k - 1] < tl:
            k -= 1
        if k - 1 >= 0:
            lo[i] = offs[k] - (tl - p[k]) / max(p[k - 1] - p[k], 1e-6) * (offs[k] - offs[k - 1])
    w = hi - lo
    seen = np.isfinite(w) & (w > width[0]) & (w < width[1])
    for i in np.where(~seen & np.isfinite(w))[0]:
        why[i] = f"unseen: width {w[i]:.1f} m outside {width[0]:g}-{width[1]:g} m"
    h = med_m // 2

    def smooth(v):
        out = np.full(n, np.nan)
        for i in range(n):
            ww = v[max(0, i - h):i + h + 1]
            ww = ww[np.isfinite(ww)]
            if len(ww) >= 5:
                out[i] = np.median(ww)
        return out
    vlo, vhi = np.where(seen, lo, np.nan), np.where(seen, hi, np.nan)
    slo, shi = smooth(vlo), smooth(vhi)
    jump = seen & ((np.abs(vlo - slo) > JUMP_M) | (np.abs(vhi - shi) > JUMP_M) | ~np.isfinite(slo) | ~np.isfinite(shi))
    for i in np.where(jump)[0]:
        why[i] = f"unseen: band jumps > {JUMP_M:g} m off its neighbours'"
    seen = seen & ~jump
    vlo, vhi = np.where(seen, lo, np.nan), np.where(seen, hi, np.nan)
    slo, shi = smooth(vlo), smooth(vhi)
    have = np.isfinite(slo) & np.isfinite(shi)
    if not have.any():
        return {"line": Es, "left": L, "seen": seen, "have": have, "why": why, "centre": Es.copy(),
                "width": np.full(n, np.nan), "held_m": np.full(n, np.inf), "residual_abs": np.array([]),
                "depth_lo": depth_lo, "depth_hi": depth_hi, "lo": lo, "hi": hi}
    idx = np.where(have)[0]
    near = idx[np.abs(np.arange(n)[:, None] - idx[None, :]).argmin(1)]
    gap = np.abs(np.arange(n) - near).astype(float)
    lo_f, hi_f = slo[near], shi[near]
    centre_off = (lo_f + hi_f) / 2
    res = np.r_[(vlo - slo)[seen & have], (vhi - shi)[seen & have]]
    return {"line": Es, "left": L, "lo": lo_f, "hi": hi_f, "centre": Es + centre_off[:, None] * L,
            "centre_off": centre_off, "seen": seen, "have": have, "held_m": gap, "why": why,
            "depth_lo": depth_lo, "depth_hi": depth_hi, "residual_abs": np.abs(res), "width": hi_f - lo_f}


def report(b: dict) -> dict:
    run = b["held_m"] <= 5
    w = b["width"][run & np.isfinite(b["width"])]
    reasons = {}
    for r in b["why"]:
        if r:
            reasons[r] = reasons.get(r, 0) + 1
    return {"sections": int(len(b["line"])), "seen": int(b["seen"].sum()),
            "within_5m_of_seen": int(run.sum()),
            "width_m": ({"p10": round(float(np.percentile(w, 10)), 2), "p50": round(float(np.median(w)), 2),
                         "p90": round(float(np.percentile(w, 90)), 2)} if len(w) else None),
            "limit_residual_m": geom.pct(b["residual_abs"], 2),
            "depth_grey_p50": [round(float(np.nanmedian(b["depth_lo"])), 1), round(float(np.nanmedian(b["depth_hi"])), 1)],
            "unseen_reasons": reasons}
