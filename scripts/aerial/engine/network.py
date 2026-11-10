"""Measured pieces and the layouts assembled from them.

Every layout's guide (route.py) is a closed line. The FIRST layout is measured whole, as one closed strip (edges.py).
A later layout's stations that run within SHARE_M of an earlier layout's guide, parallel to it, are that layout's
pavement and take its measurement; only its own stretches are measured, as open strips extended EXT_M into the shared
road on each side for context and trimmed back. A layout is then the ordered concatenation of measured stretches; every
join's gap is reported. Pieces (the report's unit, and what a later build welds) are the stretches between the points
where layouts part or meet.

Open pavement (a lot, an apron): where one side of a strip finds no edge (an opening) for OPEN_MIN_M or more, the route
crosses open pavement, and the line there is the DRIVEN BAND (band.py) measured along the guide, bounded by whatever
pavement edge the other side did find. Shorter openings (junction mouths, a diverge) are bridged by the edge fit.
Where the band is not seen (held more than BAND_HOLD_M from a seen section) the centre is a straight bridge between
the nearest seen ones, flagged inferred.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

from . import band as bandm
from . import edges as edg
from . import geom

SHARE_M = 2.5         # [invented] a later layout this far outside an earlier one's measured edge is still its road
SHARE_MAX_M = 10.0
PARALLEL_COS = 0.9
MIN_OWN_M = 10.0
ABSORB_SAME_M = 30.0  # [invented]      # an own stretch shorter than this is junction flicker, absorbed into the shared road
EXT_M = 25.0
OPEN_MIN_M = 80.0     # [invented] an opening longer than this is open pavement, not a junction mouth
GAP_CLOSE_M = 5.0     # single seen stations inside an opening (a crack, a car) do not end it
BAND_HOLD_M = 5.0
BLEND_M = 20.0


def _open_runs(m, s):
    """Runs where one side has no edge (an opening), single seen stations inside closed up (gaps <= GAP_CLOSE_M),
    OPEN_MIN_M or longer, and the OTHER side not a lidar edge: a road bounded by a measured wall is measured edge to
    edge (its mouths bridged), never by wear."""
    out = []
    k = max(1, int(round(GAP_CLOSE_M / edg.STEP_M)))
    for side, other in (("left", "right"), ("right", "left")):
        st = m["sides"][side]["status"]
        op = ndimage.binary_closing(st == "opening", structure=np.ones(2 * k + 1)) | (st == "opening")
        lid = m["sides"][other]["status"] == "lidar"
        for a, b in geom.runs(op):
            if s[b] - s[a] >= OPEN_MIN_M and lid[a:b + 1].mean() < 0.5:
                out.append((a, b, side))
    return out


def _band_splice(ctx, m, summ, closed, band_opts):
    """Replace the centre / width over open-pavement runs with the measured driven band."""
    s = m["s"]
    P, L = m["P"], m["L"]
    C, W = summ["C"].copy(), summ["W"].copy()
    reports = []
    inferred = np.zeros(len(s), bool)
    for a, b, side in _open_runs(m, s):
        pad = int(15 / edg.STEP_M)
        idx = np.arange(a - pad, b + pad + 1)
        idx = idx % len(s) if closed else idx[(idx >= 0) & (idx < len(s))]
        G = P[idx]
        st_l, st_r = m["sides"]["left"]["status"][idx], m["sides"]["right"]["status"][idx]
        bl = np.where(np.isin(st_l, ("seen", "lidar")), summ["dl"][idx], np.nan)
        br = np.where(np.isin(st_r, ("seen", "lidar")), summ["dr"][idx], np.nan)
        B = bandm.measure(ctx, G, bounds=(bl, br), **band_opts)
        rep = bandm.report(B)
        rep["stations_m"] = [round(float(s[a]), 1), round(float(s[b]), 1)]
        rep["open_side"] = side
        # band centre -> offsets on this strip's own normals
        Bc = B["centre"]
        ok = B["held_m"] <= BAND_HOLD_M
        tree = cKDTree(G)
        _, j = tree.query(Bc)
        off = np.full(len(idx), np.nan)
        wid = np.full(len(idx), np.nan)
        for q in np.where(ok)[0]:
            k = j[q]
            off[k] = float(np.dot(Bc[q] - P[idx[k]], L[idx[k]]))
            wid[k] = B["width"][q]
        have = np.isfinite(off)
        if have.sum() < 5:
            rep["used"] = False
            reports.append(rep)
            continue
        hi = np.where(have)[0]
        off = np.interp(np.arange(len(idx)), hi, off[hi])
        wid = np.interp(np.arange(len(idx)), hi, wid[hi])
        # bridged: the strip stations whose nearest band section is held more than BAND_HOLD_M from a seen one (the
        # band's 1 m sections and the strip's 0.5 m stations do not pair one to one, so this is read by position)
        _, q = cKDTree(Bc).query(P[idx])
        bridged = B["held_m"][q] > BAND_HOLD_M
        core = np.zeros(len(idx), bool)
        core[pad:len(idx) - pad] = True
        nb = int(BLEND_M / edg.STEP_M)
        w = np.zeros(len(idx))
        w[pad:len(idx) - pad] = 1.0
        w = np.clip(ndimage.uniform_filter1d(w, 2 * nb + 1, mode="nearest") * 1.0, 0, 1)
        Cb = P[idx] + off[:, None] * L[idx]
        C[idx] = C[idx] * (1 - w[:, None]) + Cb * w[:, None]
        W[idx] = W[idx] * (1 - w) + wid * w
        inferred[idx[core & bridged]] = True
        rep["used"] = True
        rep["bridged_m"] = round(float((core & bridged).sum() * edg.STEP_M), 1)
        reports.append(rep)
    return C, W, inferred, reports


def measure_route(ctx, G, closed, band_opts=None):
    m = edg.measure_strip(ctx, G, closed=closed)
    if m["failed"]:
        return None
    summ = edg.summarise(m, float(ctx.opts.get("centre_smooth_m", 2.0)))
    C, W, inferred, breps = _band_splice(ctx, m, summ, closed, band_opts or {})
    summ["C"] = geom.smooth(C, 1.0, edg.STEP_M, closed=closed)
    summ["W"] = W
    summ["inferred_band"] = inferred
    summ["report"]["band"] = breps
    summ["m"] = m
    return summ


def shared_mask(G, others, widths=None):
    """Per station of G: (index of the earlier layout it shares, its station index there) or (-1, -1). A station
    shares an earlier layout's road when it lies on that road (within its measured half-width + SHARE_M, at most
    SHARE_MAX_M, of its measured centre) running parallel to it: a sketch drawn anywhere across a measured road or a
    lot's measured band is that road."""
    T, _ = geom.normals(G, closed=True)
    who = np.full(len(G), -1)
    at = np.full(len(G), -1)
    for k, H in enumerate(others):
        TH, _ = geom.normals(H, closed=True)
        d, j = cKDTree(H).query(G)
        par = np.abs((T * TH[j]).sum(1)) > PARALLEL_COS
        tol = SHARE_M if widths is None else np.clip(np.asarray(widths[k])[j] / 2 + SHARE_M, SHARE_M, SHARE_MAX_M)
        hit = (d < tol) & par & (who < 0)
        who[hit] = k
        at[hit] = j[hit]
    # own stretches shorter than MIN_OWN_M are flicker, and ones under ABSORB_SAME_M between two stretches of the SAME
    # earlier layout are that layout's road wandering off a sketch's line (a road cannot leave and rejoin another
    # within that): both absorbed. A closed lap wraps.
    n = len(G)
    own = who < 0
    for a, b in geom.runs(own):
        prev = who[a - 1] if a > 0 else who[-1]
        nxt = who[(b + 1) % n]
        ln = (b - a + 1) * edg.STEP_M
        if ln < MIN_OWN_M or (prev >= 0 and prev == nxt and ln < ABSORB_SAME_M):
            who[a:b + 1] = prev
            if prev >= 0:
                at[a:b + 1] = -2
    return who, at
