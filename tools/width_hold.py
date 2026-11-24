"""lm_intake.width_hold (ledger 0103; Kevin 2026-11-24, to the Mac: "Long smooth curves get weird blooms" / "Look at the
side lines"): across a declared span the trace's width is replaced by the measured pavement's, held to a straight line,
where the measured edges say the pavement keeps its width and the trace swells.

Why: the assembler sweeps the lane +-w/2 about its smoothed line, so a swell in the width series blooms both side lines
(the road edge, the paint, the edge strip) together. On Milford's two longest smooth curves (the GM line's s 1,114-1,270
and 1,557-1,857, R 92-93 m) the trace's width (the 0.6.0 tracer's NAIP-mask perpendicular scans, carried by data_gm)
swells 0.9-1.4 m over 50-150 m while the measured edges (source/edges/edge_evidence_gm.json: NAIP 2022 + the 2017
lidar's intensity step) hold their width; edge_fit cuts only 1-2 row spikes and width_smooth's 10 m Gaussian cannot reach
a 50-150 m swell. A straight fit through the trace's own widths was tried first: on s 1,114-1,270 it leans with the
trace's late rise (built minus measured +0.31 m median, 0.50 m RMS; through the measured width -0.05 / 0.28).

What: per span [a, b] (metres along the assembler's line, the line width_smooth reads):
  - the measured width: every evidence point within REACH_M of a station of the span on its nearest station (its lateral
    offset u off the line, its side by sign); per BIN_M bin with >= MIN_PTS points a side, the two sides' median |u|;
  - the fit: a straight line through those bins (least squares, refitted FIT_PASSES times without the bins further than
    TRIM_K MADs + TRIM_M off it [invented]); at least COVER of the span's bins must be measured, or the span is refused;
  - the width over the span is the fit, blended in and out over blend_m by a raised cosine (the fit carried on as its
    straight line through the blend). The line is not moved.
Self-check: the built width minus the measured, less its median over the span (a steady offset is not a bloom), RMS,
before and after; a span the hold fits worse than the trace is refused (exit 1).

Stdlib only (the intake is).
"""
from __future__ import annotations

import math

BIN_M = 5.0            # [invented] the measured width's bin
MIN_PTS = 4            # [invented] points a side a bin needs
REACH_M = 20.0         # an evidence point further than this off every station of the span is not the span's
COVER = 0.60           # [invented] the share of the span's bins that must be measured
TRIM_K = 2.5           # [invented] the robust fit drops bins further than TRIM_K MADs ...
TRIM_M = 0.02          # ... + this off it
FIT_PASSES = 4


def arc(pts) -> list[float]:
    s = [0.0]
    for i in range(1, len(pts)):
        s.append(s[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
    return s


def _lsq(t, y):
    n = len(t)
    mt, my = sum(t) / n, sum(y) / n
    sxx = sum((a - mt) ** 2 for a in t)
    b = sum((a - mt) * (c - my) for a, c in zip(t, y)) / sxx if sxx > 0 else 0.0
    return my - b * mt, b


def _quantile(v, q):
    v = sorted(v)
    if not v:
        return float("nan")
    k = (len(v) - 1) * q
    f = math.floor(k)
    c = min(f + 1, len(v) - 1)
    return v[f] + (v[c] - v[f]) * (k - f)


def _median(v):
    return _quantile(v, 0.5)


def robust_line(t, w):
    """(a, b): w ~ a + b t, refitted without the points further than TRIM_K MADs + TRIM_M off it"""
    a, b = _lsq(t, w)
    for _ in range(FIT_PASSES):
        r = [y - (a + b * x) for x, y in zip(t, w)]
        mr = _median(r)
        mad = 1.4826 * _median([abs(v - mr) for v in r])
        keep = [i for i, v in enumerate(r) if abs(v - mr) <= TRIM_K * mad + TRIM_M]
        if len(keep) < 2:
            break
        a, b = _lsq([t[i] for i in keep], [w[i] for i in keep])
    return a, b


def weight(s, a, b, blend):
    """1 over [a, b], a raised cosine to 0 over blend either side"""
    if a <= s <= b:
        return 1.0
    d = a - s if s < a else s - b
    if d >= blend:
        return 0.0
    return 0.5 + 0.5 * math.cos(math.pi * d / blend)


def measured_bins(pts, s, rows, evidence):
    """{bin: measured width} over the span's rows: each evidence point on its nearest station (within REACH_M)"""
    cell = 5.0
    grid = {}
    for k in rows:
        grid.setdefault((int(pts[k][0] // cell), int(pts[k][2] // cell)), []).append(k)
    reach_cells = int(REACH_M // cell) + 1
    sides = {}
    for p in evidence:
        ex, ez = float(p[0]), float(p[1])
        gx, gz = int(ex // cell), int(ez // cell)
        best, bd = None, REACH_M * REACH_M
        for dx in range(-reach_cells, reach_cells + 1):
            for dz in range(-reach_cells, reach_cells + 1):
                for k in grid.get((gx + dx, gz + dz), ()):
                    d = (pts[k][0] - ex) ** 2 + (pts[k][2] - ez) ** 2
                    if d < bd:
                        bd, best = d, k
        if best is None:
            continue
        k = best
        k0, k1 = max(k - 1, 0), min(k + 1, len(pts) - 1)
        tx, tz = pts[k1][0] - pts[k0][0], pts[k1][2] - pts[k0][2]
        tn = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / tn, tx / tn
        u = (ex - pts[k][0]) * nx + (ez - pts[k][2]) * nz
        if abs(u) < 1.0:
            continue
        sides.setdefault((int(s[k] // BIN_M), u > 0), []).append(abs(u))
    out = {}
    for (bn, left), v in sides.items():
        if left and len(v) >= MIN_PTS and len(sides.get((bn, False), ())) >= MIN_PTS:
            out[bn] = _median(v) + _median(sides[(bn, False)])
    return out


def _rms_vs_measured(s, rows, widths, mbins):
    per = {}
    for k in rows:
        per.setdefault(int(s[k] // BIN_M), []).append(widths[k])
    d = [sum(per[bn]) / len(per[bn]) - wm for bn, wm in mbins.items() if bn in per]
    if len(d) < 3:
        return None, None, len(d)
    off = _median(d)
    return math.sqrt(sum((x - off) ** 2 for x in d) / len(d)), off, len(d)


def hold(s_pts, widths, closed, spans, blend_m, evidence):
    """(widths, report): every span held to its measured width; SystemExit on a span too thinly measured, or one the
    hold fits worse than the trace"""
    s = arc(s_pts)
    lap = s[-1]
    w = list(widths)
    rep = {"blend_m": blend_m, "bin_m": BIN_M, "min_pts": MIN_PTS, "cover": COVER, "trim": [TRIM_K, TRIM_M],
           "fit": "a straight line through the measured width's bins", "spans": []}
    for a, b in spans:
        if not (0.0 <= a < b <= lap):
            raise SystemExit(f"[width_hold] span [{a}, {b}]: 0 <= a < b <= the lap {lap:.1f} m")
        rows = [k for k in range(len(s)) if a <= s[k] <= b]
        if len(rows) < 10:
            raise SystemExit(f"[width_hold] span [{a}, {b}]: {len(rows)} rows")
        mb = measured_bins(s_pts, s, rows, evidence)
        n_bins = len({int(s[k] // BIN_M) for k in rows})
        if len(mb) < max(3, COVER * n_bins):
            raise SystemExit(f"[width_hold] span [{a}, {b}]: {len(mb)} of {n_bins} bins measured (>= {COVER:.0%} needed): "
                             "cannot hold it to the measured width")
        tb = sorted(mb)
        fa, fb = robust_line([(bn + 0.5) * BIN_M for bn in tb], [mb[bn] for bn in tb])
        new = list(w)
        touched = []
        for k in range(len(s)):
            g = weight(s[k], a, b, blend_m)
            if g > 0.0:
                new[k] = w[k] + g * ((fa + fb * s[k]) - w[k])
                touched.append(k)
        r_now, off_now, n_now = _rms_vs_measured(s, rows, w, mb)
        r_held, off_held, _ = _rms_vs_measured(s, rows, new, mb)
        if r_held > r_now:
            raise SystemExit(f"[width_hold] span [{a}, {b}]: the hold fits the measured width WORSE than the trace "
                             f"({r_held:.3f} > {r_now:.3f} m RMS over {n_now} bins): refused")
        dep = [abs(new[k] - w[k]) / 2 for k in touched]
        k_a, k_b = rows[0], rows[-1]
        rep["spans"].append({
            "s": [a, b], "rows": len(rows), "rows_touched": len(touched),
            "fit_w_m": [round(fa + fb * a, 3), round(fa + fb * b, 3)],
            "width_before_m": [round(min(w[k] for k in rows), 3), round(max(w[k] for k in rows), 3)],
            "width_after_m": [round(min(new[k] for k in rows), 3), round(max(new[k] for k in rows), 3)],
            "step_to_the_trace_at_the_ends_m": [round(fa + fb * s[k_a] - w[k_a], 3), round(fa + fb * s[k_b] - w[k_b], 3)],
            "edge_moved_m": {"p50": round(_median(dep), 3), "max": round(max(dep), 3)},
            "measured_bins": n_now, "span_bins": n_bins,
            "built_minus_measured_width_m": {"before": {"median": round(off_now, 3), "rms_about_it": round(r_now, 3)},
                                             "after": {"median": round(off_held, 3), "rms_about_it": round(r_held, 3)}}})
        w = new
    return w, rep
