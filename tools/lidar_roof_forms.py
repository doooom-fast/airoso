"""Roof FORMS measured from USGS 3DEP lidar (ledger 0083, buildings pass 4): each footprint's roof planes fitted to the 2024
points, in place of a form chosen by building class.

Two stages, so the heavy read runs once (the G10, under its cap) and the fit is re-run anywhere:

    python -I tools/lidar_roof_forms.py extract <buildings.json> <points.npz> <centerline.local.json> <tile.laz> [<tile.laz> ...]
    python tools/lidar_roof_forms.py fit <points.npz> <buildings.json> <out.json> [--stepped <key> ...]

extract (laspy + lazrs + pyproj + numpy: the lidar venv, python -I: it reads downloaded data) reads the tiles exactly as
tools/lidar_building_heights.py does (its chunked keep mask, its measure(): the SAME roof points, the same ground) and keeps,
per footprint of <buildings.json> (the planner's output WITHOUT the "lidar" key), its roof points and its edge-band points
(EDGE_BAND_M inside the walls, which measure() leaves out) as heights over that ground, in the track's local frame (x east,
y north, metres; the origin of centerline.local.json, the author's own lon/lat -> metres). The .npz never enters the repo.

fit (numpy only) reads the .npz and writes the derived product the planner reads (tools/plan_buildings.py, the plan's opt-in
"roof_forms" key). PER FOOTPRINT, on its roof points in its oriented box (u the long axis, v the short; a, b the points'
coordinates along them):
  forms    flat         h = k
           gable_long   h = r - s |b|                   (ridge along the long axis, over the box's centre line)
           gable_short  h = r - s |a|                   (ridge along the short axis)
           hip          h = r - s max(|b|, |a| - (hw - hh))   (four planes of one pitch, the author's hip)
           shed         h = k + gx x + gy y             (one plane, any direction)
           each a least-squares fit, trimmed: points further than TRIM_K x 1.4826 x MAD (at least TRIM_MIN_M) from the
           plane leave it, TRIM_ITERS times (rooftop units, a stray wall return, a tree over the eave). The residual is the
           RMS of the kept points; "kept" their share. The pitched forms only on a ring filling RECT_FILL of its box (the
           author roofs any other ring flat) and only with a rise of MIN_RISE_M or more.
  choice   the simplest form (flat, gable_long, gable_short, hip, shed) within SIMPLER_M (or SIMPLER_SHARE) of the best
  levels   a roof with two or more levels (tools/lidar_building_heights.levels_of) is also cut into PARTS: its 1 m cells
           labelled by their nearest level, the box split along its axes (a guillotine cut, at most PART_DEPTH deep) where
           a split makes the labels purer, each leaf a flat part at its points' median, the footprint clipped to the leaf.
           The parts win where their residual is under PARTS_GAIN of the best single form's.
  poor     a chosen residual over GOOD_RMS_M: the measured median stands (flat), flagged
  parapet  a flat roof's edge band, p75 over the roof's median, per side of its box, the sides' low median: a parapet
           where it is MIN_PARAPET_M or more (measured, in place of the planner's 0.7 m [invented])
  stepped  (--stepped <key>) the footprint's profile across its short axis (SLICE_M slices, their medians) cut into the
           fewest straight runs whose fit is within SEG_TOL_M: each run a flat part, or a sloped (shed) part where its rise
           is MIN_RISE_M or more (the Grand Stand's seating rise as a slope, not as steps)
  hillside a footprint lidar_building_heights calls no_roof only because its roof's median stands under the median ground of
           its ring (a parking deck built into a hill: little ground inside its walls, a ring spanning HILLSIDE_SPREAD_M or
           more) is read over the ring's LOW ground (its p10) instead: the downhill face, the deck levels over it
Every constant below is an [invented] threshold; every number in the output is a statistic of the points.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lidar_building_heights as lh  # noqa: E402  (the same roof points, ground, levels and clip as the heights)

EDGE_BAND_M = (0.1, lh.INSET_M)   # the band inside the walls measure() leaves out: a parapet's top returns here
TRIM_K = 3.0               # [invented] a point further than this many robust sigmas from the plane is not the roof
TRIM_MIN_M = 0.25          # [invented] ... and never closer than this
TRIM_ITERS = 3
CLIP_M = 1.0               # [invented] a point's miss counts at most this much in the residual (score)
RECT_FILL = 0.82           # tools/author_bespoke_blend.py RECT_FILL: a pitched roof only on a ring filling its box
MIN_RISE_M = 0.3           # [invented] a pitch (or a shed's fall, or a slope run's) rising less than this is flat
SIMPLER_M = 0.05           # [invented] a simpler form within this of the best residual (or SIMPLER_SHARE of it) is taken
SIMPLER_SHARE = 0.10
GOOD_RMS_M = 0.5           # [invented] a chosen residual over this is a poor fit: the median stands, flagged
PARTS_GAIN = 0.7           # [invented] parts stand only where their residual is under this share of the best single form's
CELL_M = 1.0               # the parts' raster cell
PURE = 0.85                # [invented] a box region whose labels agree this much is one part
PART_DEPTH = 3             # [invented] the guillotine's depth
MIN_RUN_M = 3.0            # [invented] a run of slices narrower than this joins its neighbour (a part is at least this wide)
PART_MIN_PTS = 20
TREE_DEPTH = 3             # [invented] the split-and-fit's depth (at most 8 parts)
SPLIT_STEP_M = 1.0         # the split-and-fit's candidate cuts
SPLIT_GAIN = 0.8           # [invented] a cut stands only where its two sides score under this share of the whole
MIN_PARAPET_M = 0.25       # [invented] an edge band standing less than this over the roof's median is no parapet
EDGE_MIN_PTS = 30          # [invented]
SLICE_M = lh.SLICE_M       # the stepped profile's slices (2 m, as pass 2)
SEG_TOL_M = 0.5            # [invented] a straight run of the stepped profile fits its slice medians within this (RMS)
HILLSIDE_SPREAD_M = 3.0    # [invented] a ring ground spanning this (p10..p90) is a hillside
HILLSIDE_GROUND_SHARE = 0.1  # [invented] ... and its first returns are this little ground (a deck, not a vacant lot)
FORMS = ("flat", "gable_long", "gable_short", "hip", "shed")


# --------------------------------------------------------------------------------------------- the fit (numpy, pure)
def obox(ring):
    """tools/author_bespoke_blend.py oriented_box: centre, u (long), v (short), half long, half short, fill"""
    n = len(ring)
    area = abs(sum(ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1] for i in range(n))) / 2
    best = None
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(ex, ey)
        if ln < 1e-6:
            continue
        ux, uy = ex / ln, ey / ln
        vx, vy = -uy, ux
        us = [p[0] * ux + p[1] * uy for p in ring]
        vs = [p[0] * vx + p[1] * vy for p in ring]
        w, h = max(us) - min(us), max(vs) - min(vs)
        if best is None or w * h < best[0]:
            cu, cv = (max(us) + min(us)) / 2, (max(vs) + min(vs)) / 2
            best = (w * h, (cu * ux + cv * vx, cu * uy + cv * vy), (ux, uy), (vx, vy), w / 2, h / 2)
    _, c, u, v, hw, hh = best
    if hw < hh:
        u, v, hw, hh = v, (-u[0], -u[1]), hh, hw
    return np.array(c), np.array(u), np.array(v), hw, hh, area / max(1e-9, 4 * hw * hh)


def robust_fit(A, h):
    """trimmed least squares: (coef, rms of the kept points, kept share, residuals)"""
    keep = np.ones(len(h), dtype=bool)
    coef = np.zeros(A.shape[1])
    for _ in range(TRIM_ITERS):
        if keep.sum() < A.shape[1] + 2:
            break
        coef = np.linalg.lstsq(A[keep], h[keep], rcond=None)[0]
        r = h - A @ coef
        # trimmed about the kept residuals' MEDIAN, not about zero: a least-squares level pulled off a roof by a low wing
        # (or a tree) sits between the two, and a band about zero would keep neither and lock onto the few points there
        med = float(np.median(r[keep]))
        mad = float(np.median(np.abs(r[keep] - med)))
        keep = np.abs(r - med) <= max(TRIM_K * 1.4826 * mad, TRIM_MIN_M)
    r = h - A @ coef
    return coef, score(r), float(keep.mean()), r


def score(r):
    """the residual a form is judged by: the RMS over EVERY roof point, each point's miss clipped at CLIP_M — a few rooftop
    units cost every form alike, and a form cannot win by trimming away the part of the roof it does not fit (a gable
    reading a hip's two end planes as outliers)"""
    return float(np.sqrt(np.mean(np.minimum(r * r, CLIP_M * CLIP_M)))) if len(r) else 0.0


def design(form, x, y, a, b, hw, hh):
    one = np.ones(len(x))
    if form == "flat":
        return np.c_[one]
    if form == "gable_long":
        return np.c_[one, -np.abs(b)]
    if form == "gable_short":
        return np.c_[one, -np.abs(a)]
    if form == "hip":
        return np.c_[one, -np.maximum(np.abs(b), np.abs(a) - (hw - hh))]
    return np.c_[one, x, y]                                    # shed, about the footprint's centroid


def fit_forms(ring, x, y, h):
    """every form on one footprint's roof points (local x, y; h over the ground). Returns {form: record}"""
    c, u, v, hw, hh, fill = obox(ring)
    cx, cy = float(np.mean([p[0] for p in ring])), float(np.mean([p[1] for p in ring]))
    a = (x - c[0]) * u[0] + (y - c[1]) * u[1]
    b = (x - c[0]) * v[0] + (y - c[1]) * v[1]
    out = {}
    for form in FORMS:
        if form in ("gable_long", "gable_short", "hip") and fill < RECT_FILL:
            continue
        coef, rms, kept, _ = robust_fit(design(form, x - cx, y - cy, a, b, hw, hh), h)
        rec = {"rms_m": round(rms, 3), "kept": round(kept, 3)}
        if form == "flat":
            rec["h_m"] = round(float(coef[0]), 2)
        elif form == "shed":
            gx, gy = float(coef[1]), float(coef[2])
            hs = [coef[0] + gx * (p[0] - cx) + gy * (p[1] - cy) for p in ring]
            rec.update(h_c_m=round(float(coef[0]), 2), gx=round(gx, 4), gy=round(gy, 4), centroid_xy=[round(cx, 2), round(cy, 2)],
                       low_m=round(min(hs), 2), high_m=round(max(hs), 2), valid=bool(max(hs) - min(hs) >= MIN_RISE_M))
        else:
            r_, s = float(coef[0]), float(coef[1])
            half = hw if form == "gable_short" else hh
            rec.update(ridge_m=round(r_, 2), eave_m=round(r_ - s * half, 2), pitch=round(s, 3),
                       valid=bool(s > 0 and s * half >= MIN_RISE_M))
        out[form] = rec
    return out, {"fill": round(fill, 3), "long_m": round(2 * hw, 1), "short_m": round(2 * hh, 1)}


def choose(fits):
    """the simplest valid form within SIMPLER_M / SIMPLER_SHARE of the best residual"""
    ok = {f: r for f, r in fits.items() if r.get("valid", True)}
    best = min(r["rms_m"] for r in ok.values())
    tol = best + max(SIMPLER_M, SIMPLER_SHARE * best)
    for f in FORMS:
        if f in ok and ok[f]["rms_m"] <= tol:
            return f, ok[f]["rms_m"]
    return "flat", ok["flat"]["rms_m"]


def clip_box(ring, c, u, v, a0, a1, b0, b1):
    """the ring clipped to a0 <= a <= a1, b0 <= b <= b1 of the box frame"""
    poly = [tuple(p) for p in ring]
    for n, d in (((u[0], u[1]), float(c @ u) + a0), ((-u[0], -u[1]), -(float(c @ u) + a1)),
                 ((v[0], v[1]), float(c @ v) + b0), ((-v[0], -v[1]), -(float(c @ v) + b1))):
        if len(poly) < 3:
            return []
        poly = lh.clip_halfplane(poly, n, d)
    return poly if len(poly) >= 3 and lh.ring_area(poly) >= 0.5 else []


def _runs(labels, min_cells):
    """runs of equal slice labels (None joins its neighbour), short runs merged into the longer neighbour"""
    lab = list(labels)
    for i in range(len(lab)):                     # an empty slice takes the label before it (or after it)
        if lab[i] is None:
            lab[i] = next((lab[j] for j in range(i - 1, -1, -1) if lab[j] is not None),
                          next((lab[j] for j in range(i + 1, len(lab)) if lab[j] is not None), None))
    runs = []
    for i, l in enumerate(lab):
        if runs and runs[-1][2] == l:
            runs[-1][1] = i + 1
        else:
            runs.append([i, i + 1, l])
    changed = True
    while changed and len(runs) > 1:
        changed = False
        for k, (s, e, l) in enumerate(runs):
            if e - s < min_cells:
                nb = [j for j in (k - 1, k + 1) if 0 <= j < len(runs)]
                j = max(nb, key=lambda q: runs[q][1] - runs[q][0])
                lo, hi = min(k, j), max(k, j)
                runs[lo:hi + 1] = [[runs[lo][0], runs[hi][1], runs[j][2]]]
                changed = True
                break
    out = []                                       # neighbours that now agree, joined
    for r in runs:
        if out and out[-1][2] == r[2]:
            out[-1][1] = r[1]
        else:
            out.append(list(r))
    return out


def level_parts(ring, x, y, h, levels):
    """the guillotine cut of a multi-level roof (see the header): [(a0, a1, b0, b1, label)] in the box frame, the labels"""
    c, u, v, hw, hh, _ = obox(ring)
    a = (x - c[0]) * u[0] + (y - c[1]) * u[1]
    b = (x - c[0]) * v[0] + (y - c[1]) * v[1]
    lv = np.array([l["h_m"] for l in levels])
    lab_pt = np.argmin(np.abs(h[:, None] - lv[None, :]), axis=1)
    na, nb = max(1, int(math.ceil(2 * hw / CELL_M))), max(1, int(math.ceil(2 * hh / CELL_M)))
    ia = np.clip(((a + hw) / CELL_M).astype(int), 0, na - 1)
    ib = np.clip(((b + hh) / CELL_M).astype(int), 0, nb - 1)
    grid = np.full((na, nb), -1, dtype=int)
    key = ia * nb + ib
    order = np.argsort(key, kind="stable")
    ks, hs = key[order], h[order]
    starts = np.flatnonzero(np.r_[True, ks[1:] != ks[:-1]])
    ends = np.r_[starts[1:], len(ks)]
    for s, e in zip(starts, ends):
        med = float(np.median(hs[s:e]))
        grid[ks[s] // nb, ks[s] % nb] = int(np.argmin(np.abs(lv - med)))
    sm = grid.copy()                               # 3 x 3 mode filter: a cell takes its neighbourhood's majority
    for i in range(na):
        for j in range(nb):
            w = grid[max(0, i - 1):i + 2, max(0, j - 1):j + 2].ravel()
            w = w[w >= 0]
            if len(w):
                sm[i, j] = int(np.bincount(w).argmax())
    min_cells = max(1, int(round(MIN_RUN_M / CELL_M)))
    leaves = []

    def purity(g):
        w = g[g >= 0]
        return (float(np.bincount(w).max()) / len(w), int(np.bincount(w).argmax())) if len(w) else (1.0, 0)

    def split(i0, i1, j0, j1, depth):
        g = sm[i0:i1, j0:j1]
        p, maj = purity(g)
        if p >= PURE or depth >= PART_DEPTH:
            leaves.append((i0, i1, j0, j1, maj))
            return
        best = None
        for axis in (0, 1):
            n = g.shape[axis]
            if n < 2 * min_cells:
                continue
            labels = []
            for k in range(n):
                w = (g[k, :] if axis == 0 else g[:, k])
                w = w[w >= 0]
                labels.append(int(np.bincount(w).argmax()) if len(w) else None)
            runs = _runs(labels, min_cells)
            if len(runs) < 2:
                continue
            tot = max(1, int((g >= 0).sum()))
            agree = 0
            for s, e, _ in runs:
                w = (g[s:e, :] if axis == 0 else g[:, s:e]).ravel()
                w = w[w >= 0]
                agree += int(np.bincount(w).max()) if len(w) else 0
            score = agree / tot
            if best is None or score > best[0]:
                best = (score, axis, runs)
        if best is None or best[0] < p + 0.05:
            leaves.append((i0, i1, j0, j1, maj))
            return
        _, axis, runs = best
        for s, e, _ in runs:
            if axis == 0:
                split(i0 + s, i0 + e, j0, j1, depth + 1)
            else:
                split(i0, i1, j0 + s, j0 + e, depth + 1)

    split(0, na, 0, nb, 0)
    out = []
    for i0, i1, j0, j1, l in leaves:
        a0, a1 = -hw + i0 * CELL_M, -hw + i1 * CELL_M
        b0, b1 = -hh + j0 * CELL_M, -hh + j1 * CELL_M
        out.append([a0 if i0 > 0 else -hw - 1.0, a1 if i1 < na else hw + 1.0,
                    b0 if j0 > 0 else -hh - 1.0, b1 if j1 < nb else hh + 1.0, l])
    return out, (c, u, v), a, b, lab_pt


def parts_model(ring, x, y, h, levels):
    """the multi-level roof as flat parts: (parts, rms, kept) — each part {"ring", "h_m", "n", "rms_m", "level"}"""
    leaves, (c, u, v), a, b, lab_pt = level_parts(ring, x, y, h, levels)
    resid = np.zeros(len(h))
    parts = []
    for a0, a1, b0, b1, l in leaves:
        poly = clip_box(ring, c, u, v, a0, a1, b0, b1)
        sel = (a >= a0) & (a < a1) & (b >= b0) & (b < b1)
        if not poly:
            continue
        own = sel & (lab_pt == l)
        src = own if own.sum() >= PART_MIN_PTS else sel
        if src.sum() == 0:
            continue
        hm = float(np.median(h[src]))
        resid[sel] = h[sel] - hm
        parts.append({"ring": poly, "form": "flat", "h_m": round(hm, 2), "n": int(sel.sum()), "level": int(l),
                      "rms_m": round(score(h[sel] - hm), 3) if sel.any() else None})
    _, rms, kept, _ = robust_fit(np.zeros((len(h), 1)), resid)      # the trimmed RMS of the parts' residuals
    return parts, rms, kept


def stepped_runs(ring, x, y, h):
    """the stepped profile as straight runs (see the header): (parts, profile, rms)"""
    c, u, v, hw, hh, _ = obox(ring)
    t = (x - c[0]) * v[0] + (y - c[1]) * v[1]
    edges = np.arange(-hh, hh + SLICE_M, SLICE_M)
    sl = []
    for a, b in zip(edges[:-1], edges[1:]):
        s = (t >= a) & (t < b)
        if s.sum() >= 5:
            sl.append(((a + b) / 2, float(np.median(h[s])), int(s.sum()), a, b))
    n = len(sl)
    tm = np.array([s[0] for s in sl]); hm = np.array([s[1] for s in sl])

    def seg_fit(i, j):                          # slices i..j-1, a straight line: (rms, p, q)
        if j - i == 1:
            return 0.0, hm[i], 0.0
        q, p = np.polyfit(tm[i:j], hm[i:j], 1)
        return float(np.sqrt(np.mean((hm[i:j] - (p + q * tm[i:j])) ** 2))), float(p), float(q)

    best = [0] + [10 ** 9] * n                   # the fewest runs within SEG_TOL_M
    back = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(j):
            if best[i] + 1 < best[j] and seg_fit(i, j)[0] <= SEG_TOL_M:
                best[j], back[j] = best[i] + 1, i
    cuts, j = [], n
    while j > 0:
        cuts.append((back[j], j)); j = back[j]
    cuts.reverse()
    parts, resid = [], np.zeros(len(h))
    for k, (i, j) in enumerate(cuts):
        a = sl[i][3] if k > 0 else -hh - 1.0
        b = sl[j - 1][4] if k < len(cuts) - 1 else hh + 1.0
        poly = clip_box(ring, c, u, v, -2 * hw - 2.0, 2 * hw + 2.0, a, b)
        sel = (t >= a) & (t < b)
        _, p, q = seg_fit(i, j)
        rise = abs(q) * (min(b, hh) - max(a, -hh))
        const_rms = float(np.sqrt(np.mean((hm[i:j] - np.median(hm[i:j])) ** 2)))
        if rise < MIN_RISE_M or const_rms <= SEG_TOL_M:          # a level run fits the same tolerance: flat, the simpler
            hmed = float(np.median(h[sel]))
            resid[sel] = h[sel] - hmed
            part = {"form": "flat", "h_m": round(hmed, 2)}
        else:
            # the run's plane: q per metre along v, through the box's centre line at the band's middle
            tmid = (max(a, -hh) + min(b, hh)) / 2
            ref = c + v * tmid
            resid[sel] = h[sel] - (p + q * t[sel])
            lo, hi = p + q * max(a, -hh), p + q * min(b, hh)
            part = {"form": "shed", "ref_xy": [round(float(ref[0]), 2), round(float(ref[1]), 2)], "h_m": round(p + q * tmid, 2),
                    "gx": round(q * float(v[0]), 4), "gy": round(q * float(v[1]), 4),
                    "low_m": round(min(lo, hi), 2), "high_m": round(max(lo, hi), 2)}
        part.update(ring=poly, band_m=[round(max(a, -hh), 1), round(min(b, hh), 1)], n=int(sel.sum()),
                    rms_m=round(score(resid[sel]), 3) if sel.any() else None)
        if poly:
            parts.append(part)
    _, rms, kept, _ = robust_fit(np.zeros((len(h), 1)), resid)
    profile = [{"t_m": round(float(s[0]), 1), "h_p50": round(s[1], 2), "n": s[2]} for s in sl]
    return parts, profile, rms, kept


def hillside_shift(rec):
    """a parking deck in a hill (see the header): the metres to add to its heights (median ground -> the ring's p10), else None"""
    if not rec or rec.get("status") != "no_roof" or "h_pct" not in rec or "ground_p10_p90" not in rec:
        return None
    lo, hi = rec["ground_p10_p90"]
    if hi - lo < HILLSIDE_SPREAD_M or rec.get("ground_share", 1.0) > HILLSIDE_GROUND_SHARE:
        return None
    shift = rec["ground_m"] - lo
    return shift if rec["h_pct"]["p50"] + shift >= lh.NO_ROOF_M else None


def fit_one(ring, x, y, h, ex, ey, eh, rec, stepped=False):
    """one footprint -> its record (see the header)"""
    out = {"n_roof": int(len(h))}
    shift = hillside_shift(rec)
    if shift is not None:
        h, eh = h + shift, eh + shift
        out["hillside"] = {"shift_m": round(shift, 2), "ground_p10_p90_navd88": rec["ground_p10_p90"],
                           "ground_median_navd88": rec["ground_m"],
                           "_doc": "heights over the ring's low (p10) ground: the downhill face"}
    elif not rec or rec.get("status") != "measured":
        out["form"] = None
        return out
    if len(h) < lh.ROOF_MIN:
        out["form"] = None
        return out
    fits, box = fit_forms(ring, x, y, h)
    out.update(box=box, fits=fits)
    form, rms = choose(fits)
    levels = lh.levels_of(h)
    out["levels"] = levels
    out["median_m"] = round(float(np.median(h)), 2)
    if stepped:
        parts, profile, prms, pkept = stepped_runs(ring, x, y, h)
        out.update(form="parts", rms_m=round(prms, 3), kept=round(pkept, 3), parts=parts, profile=profile,
                   single=[form, rms], _how="stepped: straight runs across the short axis")
        return out
    if rms > GOOD_RMS_M or len(levels) > 1:
        # one form does not hold it (or it has levels): cut it into parts, each its own fitted form
        cands = []
        tparts, trms = tree_fit(ring, x, y, h, ex, ey, eh)
        if len(tparts) > 1:
            cands.append((trms, tparts, "split: a guillotine cut where it lowers the residual, each part its own fitted form"))
        if len(levels) > 1:
            lparts, lrms, _ = parts_model(ring, x, y, h, levels)
            if len(lparts) > 1:
                cands.append((lrms, lparts, "levels: a guillotine cut of the level labels, each part flat"))
        if cands:
            prms, parts, how = min(cands, key=lambda t: t[0])
            out["parts_fit"] = {"rms_m": round(prms, 3), "n_parts": len(parts), "_how": how}
            if prms < PARTS_GAIN * rms or (rms > GOOD_RMS_M and prms <= GOOD_RMS_M):
                if prms > GOOD_RMS_M:
                    out.update(form="poor", rms_m=round(prms, 3), _poor="parts", single=[form, rms])
                else:
                    out.update(form="parts", rms_m=round(prms, 3), parts=parts, single=[form, rms], _how=how)
                return out
    if rms > GOOD_RMS_M:
        out.update(form="poor", rms_m=round(rms, 3), _poor=form)
        return out
    out.update(form=form, rms_m=round(rms, 3))
    if form == "flat":
        out["parapet_m"], edge = parapet(h, eh, ring, ex, ey)
        if edge:
            out["edge"] = edge
    return out


def parapet(h, eh, ring, ex, ey):
    """a flat roof's parapet off its edge band (see the header): (metres, the edge record) — 0.0 none, None not read.
    Read per SIDE of the footprint's box (each edge-band point to the side it is nearest), each side read with
    EDGE_MIN_PTS / 4 points: the parapet is the low median of the sides' p75 over the roof's median, so a wall that stands
    round the roof reads as one and a taller neighbour's eave or a tree over ONE side does not (pass 4's first fit read
    6.0 m on a 41 m2 kiosk off one side)"""
    if len(eh) < EDGE_MIN_PTS or len(h) == 0:
        return None, None
    c, u, v, hw, hh, _ = obox(ring)
    a = ((ex - c[0]) * u[0] + (ey - c[1]) * u[1]) / max(hw, 1e-6)
    b = ((ex - c[0]) * v[0] + (ey - c[1]) * v[1]) / max(hh, 1e-6)
    side = np.argmax(np.c_[a, -a, b, -b], axis=1)
    med = float(np.median(h))
    per = [float(np.percentile(eh[side == k], 75)) - med for k in range(4) if (side == k).sum() >= EDGE_MIN_PTS / 4]
    if not per:
        return None, None
    per.sort()
    par = per[(len(per) - 1) // 2]
    return (round(par, 2) if par >= MIN_PARAPET_M else 0.0), {"n": int(len(eh)), "sides_p75_over_median_m": [round(q, 2) for q in per],
                                                              "p75_over_median_m": round(par, 2)}


def _plane_score(x, y, h):
    if len(h) < 4:
        return 0.0
    A = np.c_[np.ones(len(h)), x - x.mean(), y - y.mean()]
    return robust_fit(A, h)[1]


def part_record(poly, x, y, h, ex, ey, eh):
    """one part: its best form (as a footprint's), its residual; flat parts their parapet"""
    fits, box = fit_forms(poly, x, y, h)
    form, sc = choose(fits)
    p = {"ring": poly, "form": form, "fit": fits[form], "rms_m": round(sc, 3), "n": int(len(h)), "box": box,
         "median_m": round(float(np.median(h)), 2)}
    if form == "flat":
        p["h_m"] = round(float(np.median(h)), 2)
        p["parapet_m"], _ = parapet(h, eh, poly, ex, ey)
    return p, sc


def tree_fit(ring, x, y, h, ex, ey, eh, depth=0):
    """split and fit (see the header): ([part], residual). A region whose best form scores GOOD_RMS_M is a leaf; else the
    straight cut across its box (along either axis, every SPLIT_STEP_M, both sides MIN_RUN_M wide) that lowers the two
    sides' plane residual most, kept where the two sides' best forms score under SPLIT_GAIN of the whole's"""
    leaf, sc = part_record(ring, x, y, h, ex, ey, eh)
    if sc <= GOOD_RMS_M or depth >= TREE_DEPTH or len(h) < 2 * PART_MIN_PTS:
        return [leaf], sc
    c, u, v, hw, hh, _ = obox(ring)
    a = (x - c[0]) * u[0] + (y - c[1]) * u[1]
    b = (x - c[0]) * v[0] + (y - c[1]) * v[1]
    best = None
    for axis, coord, half in ((0, a, hw), (1, b, hh)):
        for cut in np.arange(-half + MIN_RUN_M, half - MIN_RUN_M + 1e-9, SPLIT_STEP_M):
            m = coord < cut
            na_, nb_ = int(m.sum()), int((~m).sum())
            if na_ < PART_MIN_PTS or nb_ < PART_MIN_PTS:
                continue
            s = math.sqrt((_plane_score(x[m], y[m], h[m]) ** 2 * na_ + _plane_score(x[~m], y[~m], h[~m]) ** 2 * nb_) / len(h))
            if best is None or s < best[0]:
                best = (s, axis, float(cut))
    if best is None:
        return [leaf], sc
    _, axis, cut = best
    ax = u if axis == 0 else v
    d = float(c @ ax) + cut
    lo = lh.clip_halfplane([tuple(p) for p in ring], (-ax[0], -ax[1]), -d)
    hi = lh.clip_halfplane([tuple(p) for p in ring], (ax[0], ax[1]), d)
    if len(lo) < 3 or len(hi) < 3:
        return [leaf], sc
    coord = a if axis == 0 else b
    m = coord < cut
    ecoord = ((ex - c[0]) * ax[0] + (ey - c[1]) * ax[1]) if len(ex) else np.zeros(0)
    em = ecoord < cut
    pl, sl_ = tree_fit(lo, x[m], y[m], h[m], ex[em], ey[em], eh[em], depth + 1)
    ph, sh_ = tree_fit(hi, x[~m], y[~m], h[~m], ex[~em], ey[~em], eh[~em], depth + 1)
    tot = math.sqrt((sl_ ** 2 * m.sum() + sh_ ** 2 * (~m).sum()) / len(h))
    if tot < SPLIT_GAIN * sc:
        return pl + ph, tot
    return [leaf], sc


def fit_main(argv):
    npz, bfile, outp = Path(argv[0]), Path(argv[1]), Path(argv[2])
    stepped_keys = [argv[i + 1] for i in range(3, len(argv) - 1) if argv[i] == "--stepped"]
    d = np.load(npz)
    meta = json.loads(bytes(d["meta"]).decode("utf-8"))
    sys.path.insert(0, str(HERE.parent))
    from scripts.geometry.projection import _meters_per_degree
    o = meta["origin"]
    mlon, mlat = _meters_per_degree(o["lat"])
    rows = {r["key"]: r for r in json.loads(bfile.read_text(encoding="utf-8"))}
    keys, recs = meta["keys"], meta["recs"]
    ro, eo = d["roof_off"], d["edge_off"]
    roof, edge = d["roof"].astype(np.float64), d["edge"].astype(np.float64)
    out, tally = {}, {}
    for i, k in enumerate(keys):
        ring = [((p[0] - o["lon"]) * mlon, (p[1] - o["lat"]) * mlat) for p in rows[k]["footprint_lonlat"]]
        if ring[0] == ring[-1]:
            ring = ring[:-1]
        R, E = roof[ro[i]:ro[i + 1]], edge[eo[i]:eo[i + 1]]
        rec = fit_one(ring, R[:, 0], R[:, 1], R[:, 2], E[:, 0], E[:, 1], E[:, 2], recs.get(k), k in stepped_keys)
        for p in rec.get("parts", []):            # the parts' rings back to lon / lat (the planner's frame), one schema
            p["footprint_lonlat"] = [[round(o["lon"] + q[0] / mlon, 7), round(o["lat"] + q[1] / mlat, 7)] for q in p.pop("ring")]
            p.setdefault("form", "flat")
            f = p.pop("fit", None)
            if f is not None and p["form"] == "shed":
                p.update(ref_xy=f["centroid_xy"], h_m=f["h_c_m"], gx=f["gx"], gy=f["gy"], low_m=f["low_m"], high_m=f["high_m"])
            elif f is not None and p["form"] != "flat":
                p.update(eave_m=f["eave_m"], ridge_m=f["ridge_m"], pitch=f["pitch"])
            if "ref_xy" in p:
                p["ref_lonlat"] = [round(o["lon"] + p["ref_xy"][0] / mlon, 7), round(o["lat"] + p["ref_xy"][1] / mlat, 7)]
        if rec.get("form") == "shed":
            f = rec["fits"]["shed"]
            cx, cy = f["centroid_xy"]
            f["ref_lonlat"] = [round(o["lon"] + cx / mlon, 7), round(o["lat"] + cy / mlat, 7)]
        out[k] = rec
        tally[str(rec.get("form"))] = tally.get(str(rec.get("form")), 0) + 1
    rms = sorted(r["rms_m"] for r in out.values() if r.get("rms_m") is not None)
    doc = {"_doc": "ledger 0083 buildings pass 4: each footprint's roof form fitted to the 2024 lidar points "
                   "(tools/lidar_roof_forms.py; the header says how). Heights in metres over the lidar ground of "
                   "buildings.lidar.json (a hillside deck: over its ring's p10 ground); x / y local metres (east, north) of "
                   "the track's origin; rms_m the chosen form's trimmed residual.",
           "origin": o, "tiles": meta.get("tiles"),
           "params": {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float, list, tuple))},
           "forms": tally,
           "rms_m": {"n": len(rms), "p50": rms[len(rms) // 2] if rms else None, "p90": rms[int(len(rms) * 0.9)] if rms else None,
                     "max": rms[-1] if rms else None},
           "buildings": out}
    outp.write_text(json.dumps(doc, indent=1), encoding="utf-8", newline="\n")
    print(f"[roofs] {len(out)} footprints: {tally}; residual p50 {doc['rms_m']['p50']} m, p90 {doc['rms_m']['p90']} m, "
          f"max {doc['rms_m']['max']} m")
    return 0


# --------------------------------------------------------------------------------------------- the read (laspy, heavy)
def extract_main(argv):
    import laspy
    from pyproj import CRS, Transformer
    bfile, outp, cfile = Path(argv[0]), Path(argv[1]), Path(argv[2])
    tiles = [Path(a) for a in argv[3:]]
    rows = json.loads(bfile.read_text(encoding="utf-8"))
    origin = json.loads(cfile.read_text(encoding="utf-8"))["origin"]
    sys.path.insert(0, str(HERE.parent))
    from scripts.geometry.projection import _meters_per_degree
    mlon, mlat = _meters_per_degree(origin["lat"])
    with laspy.open(tiles[0]) as f:
        crs = f.header.parse_crs()
    hcrs = crs.sub_crs_list[0] if crs.is_compound else crs
    to_m = Transformer.from_crs(CRS.from_epsg(4326), hcrs, always_xy=True)
    to_ll = Transformer.from_crs(hcrs, CRS.from_epsg(4326), always_xy=True)
    rings = {}
    for r in rows:
        xy = [to_m.transform(p[0], p[1]) for p in r["footprint_lonlat"]]
        if xy[0] == xy[-1]:
            xy = xy[:-1]
        rings[r["key"]] = xy
    # the keep mask and the chunked read of tools/lidar_building_heights.py main(), as there
    pad = lh.GROUND_RING_M[-1][1] + 1.0 + lh.KEEP_MARGIN_M
    boxes = [(min(p[0] for p in v) - pad, min(p[1] for p in v) - pad, max(p[0] for p in v) + pad, max(p[1] for p in v) + pad)
             for v in rings.values()]
    heads = []
    for tp in tiles:
        with laspy.open(tp) as f:
            heads.append((float(f.header.mins[0]), float(f.header.mins[1]), float(f.header.maxs[0]), float(f.header.maxs[1])))
    C = lh.KEEP_CELL_M
    gx0, gy0 = min(h[0] for h in heads), min(h[1] for h in heads)
    gnx = int((max(h[2] for h in heads) - gx0) // C) + 1
    gny = int((max(h[3] for h in heads) - gy0) // C) + 1
    mask = np.zeros((gny, gnx), dtype=bool)
    for x0, y0, x1, y1 in boxes:
        i0, i1 = max(0, int((x0 - gx0) // C)), min(gnx - 1, int((x1 - gx0) // C))
        j0, j1 = max(0, int((y0 - gy0) // C)), min(gny - 1, int((y1 - gy0) // C))
        if i1 >= i0 and j1 >= j0:
            mask[j0:j1 + 1, i0:i1 + 1] = True
    xs_, ys_, zs_, cs_, rns_, nrs_ = [], [], [], [], [], []
    for tp in tiles:
        with laspy.open(tp) as f:
            for ch in f.chunk_iterator(lh.CHUNK_POINTS):
                cls = np.asarray(ch.classification, dtype=np.uint8)
                x, y = np.asarray(ch.x), np.asarray(ch.y)
                ci = np.clip(((x - gx0) // C).astype(np.int64), 0, gnx - 1)
                cj = np.clip(((y - gy0) // C).astype(np.int64), 0, gny - 1)
                keep = mask[cj, ci] & (cls != 7) & (cls != 18)
                xs_.append(x[keep]); ys_.append(y[keep]); zs_.append(np.asarray(ch.z)[keep])
                cs_.append(cls[keep]); rns_.append(np.asarray(ch.return_number, dtype=np.uint8)[keep])
                nrs_.append(np.asarray(ch.number_of_returns, dtype=np.uint8)[keep])
    cloud = lh.Cloud(np.concatenate(xs_), np.concatenate(ys_), np.concatenate(zs_), np.concatenate(cs_), np.concatenate(rns_),
                     np.concatenate(nrs_))
    del xs_, ys_, zs_, cs_, rns_, nrs_
    cent = {k: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for k, v in rings.items()}

    def local(xu, yu):
        lon, lat = to_ll.transform(xu, yu)
        return (np.asarray(lon) - origin["lon"]) * mlon, (np.asarray(lat) - origin["lat"]) * mlat

    keys, recs, roofs, edges = [], {}, [], []
    for r in rows:
        k = r["key"]
        ring = rings[k]
        rad = max(math.dist(cent[k], p) for p in ring) + lh.GROUND_RING_M[-1][1] + 60
        others = [rings[o] for o in rings if o != k and math.dist(cent[k], cent[o]) < rad]
        rec, roof = lh.measure(cloud, ring, others)
        keys.append(k)
        recs[k] = rec
        if roof is None:
            roofs.append(np.zeros((0, 3), np.float32)); edges.append(np.zeros((0, 3), np.float32))
            continue
        lx, ly = local(roof[0], roof[1])
        roofs.append(np.c_[lx, ly, roof[2]].astype(np.float32))
        # the edge band: single returns, not ground / noise / water / vegetation, EDGE_BAND_M inside the walls
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        idx = cloud.box(min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1)
        x, y, z, c, rn, nr = cloud.x[idx], cloud.y[idx], cloud.z[idx], cloud.cls[idx], cloud.rn[idx], cloud.nr[idx]
        d = lh.dist_to_ring(ring, x, y)
        band = (lh.point_in_ring(ring, x, y) & (d >= EDGE_BAND_M[0]) & (d < EDGE_BAND_M[1]) & (rn == 1) & (nr == 1)
                & ~np.isin(c, lh.NOT_ROOF) & ~np.isin(c, (3, 4, 5)))
        ex, ey = local(x[band], y[band])
        edges.append(np.c_[ex, ey, z[band] - rec["ground_m"]].astype(np.float32))
    ro = np.cumsum([0] + [len(a) for a in roofs])
    eo = np.cumsum([0] + [len(a) for a in edges])
    meta = {"origin": origin, "keys": keys, "recs": recs, "crs": hcrs.name,
            "tiles": [{"file": t.name, "bytes": t.stat().st_size} for t in tiles]}
    np.savez_compressed(outp, roof=np.concatenate(roofs), edge=np.concatenate(edges), roof_off=ro, edge_off=eo,
                        meta=np.frombuffer(json.dumps(meta).encode("utf-8"), dtype=np.uint8))
    print(f"[roofs] {len(cloud.x):,} points kept from {len(tiles)} tiles; {len(keys)} footprints; {int(ro[-1]):,} roof points, "
          f"{int(eo[-1]):,} edge-band points -> {outp}")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("extract", "fit"):
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(extract_main(a[1:]) if a[0] == "extract" else fit_main(a[1:]))
