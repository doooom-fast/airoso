"""The road's width (or a lane edge) as a person would lay it out: runs joined by tapers, never a bulge
that swells and comes back (ledger 0103; Kevin 2026-11-24: "Look for primarily bulges during otherwise smooth curves and
straights" / "Dreaded slop, a human would never do it because it's more work, both irl and digitally"). Stdlib only: the
intake (tools/lm_engine_intake.py, lm_intake.width_design) runs it, tools/edge_bulges.py reports with it on any track.

For a series y(s) every SAMPLE_M:
  - layout(y): the road as laid out: a morphological opening (a running minimum, then a running maximum, over
    MAX_LEN_M) takes every swell narrower than MAX_LEN_M down to the run either side of it, then a closing (maximum, then
    minimum) fills every pinch the same way. A step to a new width, or a steady taper, is monotone and comes through
    whole; only what goes out and comes back is taken. (An l1 trend filter was tried first and dropped: at any kink
    cost it still rode a 1.2 m swell 0.4-0.6 m and rounded the real steps into false excursions either side.)
  - excursions(y, x): the stretches where y leaves the layout by over EPS_M and comes back: a bulge when its peak is
    >= MIN_AMP_M and it is MIN_LEN_M..MAX_LEN_M long (longer = a width the layout did not take, reported, not a bulge).
  - verdict(...): a bulge is REAL only when the measured edge makes the same excursion beyond its own noise. The measured
    values' deviation from the same layout, median inside the bulge's core (where it is over half its peak) minus median
    just outside it (OUT_M a side): >= REAL_SHARE of the built peak and >= REAL_T standard errors (MADs). Fewer than
    min_measured values in or out: "unmeasured". Anything not real is ours. (A steady sensor bias and a real taper both
    cancel in the in-minus-out.)
  - designed(y, regions, lay): y with each region replaced by the curve between its two ends that meets the layout's
    layout's slope at both (a cubic Hermite), the change then rounded over JOIN_SMOOTH_M at its joins.
Every number here is [invented] (the Mac, ledger 0103: "a few constant runs joined by straight tapers ... make every number
in the fit [invented] ... a bulge is an excursion ... that goes out and comes back to the same level ... over 15-200 m").
"""
from __future__ import annotations

import math

SAMPLE_M = 1.0        # [invented] the series' spacing
EPS_M = 0.03          # [invented] an excursion starts and ends where it is under this
MIN_AMP_M = 0.10      # [invented] the Mac's "over N cm"
MIN_LEN_M = 15.0      # [invented]
MAX_LEN_M = 200.0     # [invented]
OUT_M = 40.0          # [invented] how far either side the measured "outside" reaches
REAL_SHARE = 0.5      # [invented] the measured excursion must be at least this share of the built one ...
REAL_T = 2.0          # [invented] ... and this many of its standard errors
MIN_MEASURED = 8      # [invented] measured values needed inside and outside (points); bins pass their own
JOIN_SMOOTH_M = 10.0  # [invented] the change rounded over this (a Hann window), so no join is a kink


# ------------------------------------------------------------------------------------------------------- the layout
def _running(y, win, fn, closed):
    """running min (fn=min) or max over a centred window of win samples (odd), O(n) with a monotone deque"""
    from collections import deque
    n = len(y)
    h = win // 2
    if closed and n > win:
        ext = list(y[-h:]) + list(y) + list(y[:h])
    else:
        ext = [y[0]] * h + list(y) + [y[-1]] * h
    keep = (lambda new, old: new <= old) if fn is min else (lambda new, old: new >= old)
    out, q = [], deque()
    for i, v in enumerate(ext):
        while q and keep(v, ext[q[-1]]):
            q.pop()
        q.append(i)
        if q[0] <= i - win:
            q.popleft()
        if i >= win - 1:
            out.append(ext[q[0]])
    return out[:n]


def layout(y, closed, sample_m=SAMPLE_M, max_len_m=None):
    """closing(opening(y)) over max_len_m: every swell, then every pinch, narrower than max_len_m taken out"""
    win = int(round((MAX_LEN_M if max_len_m is None else max_len_m) / sample_m)) | 1
    op = _running(_running(y, win, min, closed), win, max, closed)
    return _running(_running(op, win, max, closed), win, min, closed)


# --------------------------------------------------------------------------------------------------- the excursions
def excursions(y, x, sample_m=SAMPLE_M, eps_m=EPS_M, min_amp_m=MIN_AMP_M, min_len_m=MIN_LEN_M, max_len_m=MAX_LEN_M):
    """[{"i0", "i1", "ipk", "amp_m", "len_m", "dir", "kind"}]: every stretch where y leaves its layout x by over eps_m;
    kind "bulge" when it is big and short enough, "long" when longer than max_len_m"""
    r = [a - b for a, b in zip(y, x)]
    n = len(r)
    out = []
    i = 0
    while i < n:
        if abs(r[i]) <= eps_m:
            i += 1
            continue
        sg = 1 if r[i] > 0 else -1
        j = i
        while j + 1 < n and sg * r[j + 1] > eps_m:
            j += 1
        ipk = max(range(i, j + 1), key=lambda k: sg * r[k])
        amp, ln = sg * r[ipk], (j - i + 1) * sample_m
        if amp >= min_amp_m and ln >= min_len_m:
            out.append({"i0": i, "i1": j, "ipk": ipk, "amp_m": amp, "len_m": ln, "dir": sg,
                        "kind": "bulge" if ln <= max_len_m else "long"})
        i = j + 1
    return out


def _median(v):
    v = sorted(v)
    n = len(v)
    return (v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])) if n else float("nan")


def _se(v):
    m = _median(v)
    mad = 1.4826 * _median([abs(a - m) for a in v])
    return 1.2533 * mad / math.sqrt(len(v)) if v else float("inf")


def _interp(s, x, t):
    """x(s) at t (s increasing, uniform or not), clamped"""
    if t <= s[0]:
        return x[0]
    if t >= s[-1]:
        return x[-1]
    lo, hi = 0, len(s) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if s[mid] <= t:
            lo = mid
        else:
            hi = mid
    f = (t - s[lo]) / (s[hi] - s[lo]) if s[hi] > s[lo] else 0.0
    return x[lo] + (x[hi] - x[lo]) * f


def verdict(ex, s, y, x, measured, out_m=OUT_M, min_measured=MIN_MEASURED):
    """("real" | "ours" | "unmeasured", detail): measured = [(s, value)] of the same quantity as y"""
    i0, i1, ipk, d = ex["i0"], ex["i1"], ex["ipk"], ex["dir"]
    half = 0.5 * ex["amp_m"]
    core = [s[k] for k in range(i0, i1 + 1) if d * (y[k] - x[k]) >= half] or [s[ipk]]
    c0, c1 = min(core), max(core)
    s0, s1 = s[i0], s[i1]
    inside = [v - _interp(s, x, t) for t, v in measured if c0 <= t <= c1]
    outside = [v - _interp(s, x, t) for t, v in measured if (s0 - out_m <= t < s0) or (s1 < t <= s1 + out_m)]
    det = {"measured_in": len(inside), "measured_out": len(outside)}
    if len(inside) < min_measured or len(outside) < min_measured:
        return "unmeasured", det
    exc = d * (_median(inside) - _median(outside))
    se = math.hypot(_se(inside), _se(outside))
    det.update({"measured_excursion_m": round(exc, 3), "measured_se_m": round(se, 3)})
    if exc >= REAL_SHARE * ex["amp_m"] and exc >= REAL_T * se:
        return "real", det
    return "ours", det


def designed(y, regions, lay=None):
    """y with each (i0, i1) replaced by the curve between its two ends y[i0 - 1] and y[i1 + 1]: a cubic Hermite meeting
    each end at the layout's slope there (the road under the bulge; the road's own slope just outside is the bulge's foot
    and rebuilds it), or a straight taper without a layout"""
    out = list(y)
    n = len(y)
    for i0, i1 in regions:
        a, b = max(i0 - 1, 0), min(i1 + 1, n - 1)
        L = max(b - a, 1)
        if lay is not None and 1 <= a and b + 1 < n:
            ma, mb = lay[a] - lay[a - 1], lay[b + 1] - lay[b]           # the layout's slope (the road under the bulge)
        else:
            ma = mb = (y[b] - y[a]) / L
        for k in range(i0, i1 + 1):
            t = (k - a) / L
            h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
            out[k] = h00 * y[a] + h10 * L * ma + h01 * y[b] + h11 * L * mb
    return out


def resample(s_src, y_src, sample_m=SAMPLE_M):
    """(s, y) every sample_m by linear interpolation along s_src (increasing)"""
    n = int(s_src[-1] // sample_m) + 1
    s, y, j = [], [], 0
    for k in range(n):
        t = k * sample_m
        while j + 1 < len(s_src) - 1 and s_src[j + 1] < t:
            j += 1
        a, b = s_src[j], s_src[j + 1]
        f = 0.0 if b <= a else min(max((t - a) / (b - a), 0.0), 1.0)
        s.append(t)
        y.append(y_src[j] + (y_src[j + 1] - y_src[j]) * f)
    return s, y


# ---------------------------------------------------------------------------------------------- measured and the design
def arc(pts) -> list[float]:
    s = [0.0]
    for i in range(1, len(pts)):
        s.append(s[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
    return s


def measured(pts, s, evidence=(), lidar=None, bin_m=5.0, min_side=4, reach_m=20.0):
    """{"left": [(s, |u|)], "right": [...], "width": [(s, w)]} on the line pts (x, y, z; z north) with arc length s:
    the lidar edges (an edges_curves.py read: stations {s, left.u_m, right.u_m}) where they cover, the evidence points
    ([E, N, ...]) on their nearest station elsewhere (the width per bin_m bin with >= min_side points a side)"""
    out = {"left": [], "right": [], "width": []}
    covered = []
    if lidar:
        covered = [list(map(float, sp["s"])) for sp in lidar.get("spans", [])]
        for st in lidar.get("stations", []):
            L, R = (st.get("left") or {}).get("u_m"), (st.get("right") or {}).get("u_m")
            if L is not None:
                out["left"].append((float(st["s"]), abs(L)))
            if R is not None:
                out["right"].append((float(st["s"]), abs(R)))
            if L is not None and R is not None:
                out["width"].append((float(st["s"]), abs(L) + abs(R)))
    cell = 5.0
    grid = {}
    for k, p in enumerate(pts):
        grid.setdefault((int(p[0] // cell), int(p[2] // cell)), []).append(k)
    rc = int(reach_m // cell) + 1
    bins = {}
    for p in evidence:
        ex, ez = float(p[0]), float(p[1])
        gx, gz = int(ex // cell), int(ez // cell)
        best, bd = None, reach_m * reach_m
        for dx in range(-rc, rc + 1):
            for dz in range(-rc, rc + 1):
                for k in grid.get((gx + dx, gz + dz), ()):
                    d = (pts[k][0] - ex) ** 2 + (pts[k][2] - ez) ** 2
                    if d < bd:
                        bd, best = d, k
        if best is None:
            continue
        k = best
        if any(a <= s[k] <= b for a, b in covered):
            continue
        k0, k1 = max(k - 1, 0), min(k + 1, len(pts) - 1)
        tx, tz = pts[k1][0] - pts[k0][0], pts[k1][2] - pts[k0][2]
        tn = math.hypot(tx, tz) or 1.0
        u = (ex - pts[k][0]) * (-tz / tn) + (ez - pts[k][2]) * (tx / tn)
        if abs(u) < 1.0:
            continue
        out["left" if u > 0 else "right"].append((s[k], abs(u)))
        bins.setdefault(int(s[k] // bin_m), {"l": [], "r": []})["l" if u > 0 else "r"].append(abs(u))
    for b, v in sorted(bins.items()):
        if len(v["l"]) >= min_side and len(v["r"]) >= min_side:
            out["width"].append(((b + 0.5) * bin_m, _median(v["l"]) + _median(v["r"])))
    out["width"].sort()
    return out, covered


def _in_spans(a, b, spans, lap):
    """does [a, b] touch any span (a span with s0 > s1 wraps through the lap's start)"""
    for s0, s1 in spans:
        parts = [(s0, s1)] if s0 <= s1 else [(s0, lap), (0.0, s1)]
        if any(a <= q1 and q0 <= b for q0, q1 in parts):
            return True
    return False


def _bulge_rows(sr, wr, lay, meas_w, closed, held, lap):
    rows, regions = [], []
    for ex in excursions(wr, lay):
        v, det = verdict(ex, sr, wr, lay, meas_w, min_measured=3)
        a, b = sr[ex["i0"]], sr[ex["i1"]]
        held_ = _in_spans(a, b, held, lap)
        act = v == "ours" and ex["kind"] == "bulge" and not held_
        rows.append({"s": [round(a, 1), round(b, 1)], "peak_s": round(sr[ex["ipk"]], 1), "amp_m": round(ex["amp_m"], 3),
                     "len_m": round(ex["len_m"], 1), "dir": "out" if ex["dir"] > 0 else "in", "kind": ex["kind"],
                     "verdict": v, "held": held_, "taken_out": act, **det})
        if act:
            regions.append((ex["i0"], ex["i1"]))
    return rows, regions


def design_width(pts, widths, closed, evidence=(), lidar=None, held=()):
    """(widths, report): every bulge in the width that the measured edge does not carry (and that is not inside a held
    span) replaced by the straight taper between its ends; every other width untouched, to the bit"""
    s = arc(pts)
    lap = s[-1]
    sr, wr = resample(s, list(widths))
    lay = layout(wr, closed)
    meas, covered = measured(pts, s, evidence, lidar)
    rows, regions = _bulge_rows(sr, wr, lay, meas["width"], closed, list(held), lap)
    des = designed(wr, regions, lay)
    delta = [d - w for d, w in zip(des, wr)]
    # the change rounded over JOIN_SMOOTH_M (a Hann window): the joins are no kinks; it reaches <= JOIN_SMOOTH_M / 2 past a bulge
    hw = int(round(JOIN_SMOOTH_M / SAMPLE_M / 2))
    if regions and hw > 0:
        win = [0.5 - 0.5 * math.cos(2 * math.pi * (k + 1) / (2 * hw + 2)) for k in range(2 * hw + 1)]
        tot = sum(win)
        nd = len(delta)
        sm = [0.0] * nd
        for k in range(nd):
            if any(delta[(k + j - hw) % nd] for j in range(2 * hw + 1)):
                sm[k] = sum(win[j] * delta[(k + j - hw) % nd if closed else min(max(k + j - hw, 0), nd - 1)]
                            for j in range(2 * hw + 1)) / tot
        delta = sm
    out = [w + (_interp(sr, delta, t) if any(abs(v) > 0 for v in delta) else 0.0) for w, t in zip(widths, s)]
    # self-check: the designed width scanned again
    sr2, wr2 = resample(s, out)
    rows2, regions2 = _bulge_rows(sr2, wr2, layout(wr2, closed), meas["width"], closed, list(held), lap)
    km = lap / 1000.0

    def counts(rs):
        c = {v: sum(1 for r in rs if r["kind"] == "bulge" and not r["held"] and r["verdict"] == v)
             for v in ("ours", "real", "unmeasured")}
        return {**c, "ours_per_km": round(c["ours"] / km, 2)}
    moved = [abs(a - b) / 2 for a, b in zip(out, widths)]
    rep = {"params": {k: globals()[k] for k in ("SAMPLE_M", "MAX_LEN_M", "MIN_LEN_M", "MIN_AMP_M", "EPS_M", "OUT_M",
                                              "REAL_SHARE", "REAL_T")},
           "held": [list(h) for h in held], "lidar_edges_cover": covered,
           "measured_width_values": len(meas["width"]),
           "before": counts(rows), "after": counts(rows2), "bulges": rows, "after_bulges": rows2,
           "taken_out": [r for r in rows if r["taken_out"]],
           "edge_moved_m": {"max": round(max(moved), 3),
                            "points_moved": sum(1 for m in moved if m > 0)}}
    return out, rep
