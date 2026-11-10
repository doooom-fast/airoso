"""The lane edges re-fitted to measured evidence, outliers cut and logged (ledger 0087; lm_intake.edge_fit, opt-in).

Kevin, 2026-11-07: "we need to figure out how to cut inaccurate outliers out of the data set, but keep accurate ones."

The assembler sweeps the lane +-width/2 about the smoothed line (scripts-v021/geometry/ribbon.py), so a built edge is exactly
the width series: every notch in a traced width is a notch in both edges. This replaces the width series with a fit, per side,
through every measurement of that edge:
  trace     the source's own half width at each row (weight W_TRACE: the prior, decisive only where nothing else measured)
  evidence  measured pavement-edge points (world E/N; e.g. NAIP and lidar, tracks/<t>/source/edges/edge_evidence.json), each
            owned by the nearest row of the smoothed line, its lateral offset read on that row's normal (weight 1)
The fit: a robust local quadratic (LOESS) of the edge offset along the line, half window FIT_HALF_M, tricube in station,
Tukey bisquare on the residual (c = 4.685 sigma, sigma = 1.4826 x the MAD of the evidence residuals, floor SIGMA_FLOOR_M),
ROBUST_ITERS times. Then every sample with |residual| > K_HAMPEL sigma is REJECTED and logged with its reason, and the final
fit is the kept samples' (no down-weighting left):
  spike             a run of 1-2 rows of one source off the fit: contradicted by its neighbours (and the other sensor)
  sustained-contra  a run of 3+ trace rows off the fit where the evidence is dense: the trace disagrees with the imagery /
                    lidar over a sustained stretch (a mis-scan), so the measured edge wins
  outlier           an evidence point off the fit (a painted line, a shadow, an apron): contradicted by its neighbours
A real change stays: a widening the evidence shows over several rows is the fit (it is the population); where the evidence
is sparse (fewer than MIN_SUPPORT points in the window: aprons, gores, shadow) the trace alone carries the fit, so its own
sustained changes (a gore flare, a taper) stand and only its 1-2 row spikes go.
The width at each row is fit_left + fit_right; the line is not moved (the road stays where it is apart from its edges).
Pure Python (the intake is stdlib only).
"""
from __future__ import annotations

import math

W_TRACE = 0.15            # [invented] the trace's weight per row against ~3 measured points per row at weight 1
FIT_HALF_M = 15.0         # [invented] the window: the two sensors' per-station scatter (sd ~0.45 m, ledger 0087 §3) averages to
#                           ~0.1 m over +-15 m; a real width change on a circuit (corner exit, gore) runs 20-50 m
ROBUST_ITERS = 3
SIGMA_FLOOR_M = 0.05      # [invented] no rejection inside 3 x 5 cm, whatever the MAD says
K_HAMPEL = 3.0            # the textbook Hampel cut (3 scaled MADs)
SPIKE_MAX_ROWS = 2        # Kevin's rule: a spike is one or two samples
MIN_SUPPORT = 12          # [invented] evidence points in the window before they count (fewer: the trace alone)
AGREE_M = 0.6             # [invented] the two sensors' window medians must agree this well (their registration fitted out)
SPREAD_MAX_M = 0.5        # [invented] and the window's points scatter less than this (1.4826 MAD): tree shadow, aprons, paint fail
SEARCH_M = 3.5           # an evidence point within +-3.5 m of the trace's edge belongs to that edge (measure_edges.py)
ALONG_M = 1.0             # and within 1 m of its row along the line
BUCKET = 8.0


def _normals(pts, closed):
    n = len(pts)
    out = []
    for i in range(n):
        a = pts[(i - 1) % n] if closed else pts[max(0, i - 1)]
        b = pts[(i + 1) % n] if closed else pts[min(n - 1, i + 1)]
        if closed and i == n - 1:
            a, b = pts[n - 2], pts[1]
        if closed and i == 0:
            a, b = pts[n - 2], pts[1]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        out.append((tx / L, tz / L))
    return out


class _Win:
    """the samples sorted by station, padded by +-half across the seam of a closed line, for windowed LOESS"""

    def __init__(self, S, half, lap):
        import bisect
        self._bisect = bisect
        idx = sorted(range(len(S)), key=lambda k: S[k])
        ext = [(S[k], k) for k in idx]
        if lap:
            ext = [(S[k] - lap, k) for k in idx if S[k] >= lap - half] + ext + [(S[k] + lap, k) for k in idx if S[k] < half]
        self.s = [e[0] for e in ext]
        self.k = [e[1] for e in ext]
        self.half = half

    def at(self, si, Y, Wb):
        b = self._bisect
        lo, hi = b.bisect_left(self.s, si - self.half), b.bisect_right(self.s, si + self.half)
        s0 = s1 = s2 = s3 = s4 = t0 = t1 = t2 = 0.0
        for q in range(lo, hi):
            k = self.k[q]
            wj = Wb[k]
            if wj <= 0:
                continue
            x = self.s[q] - si
            u = abs(x) / self.half
            if u >= 1:
                continue
            w = wj * (1 - u ** 3) ** 3
            yj = Y[k]
            x2 = x * x
            s0 += w; s1 += w * x; s2 += w * x2; s3 += w * x2 * x; s4 += w * x2 * x2
            t0 += w * yj; t1 += w * x * yj; t2 += w * x2 * yj
        if s0 <= 0:
            return None
        det = (s0 * (s2 * s4 - s3 * s3) - s1 * (s1 * s4 - s3 * s2) + s2 * (s1 * s3 - s2 * s2))
        if abs(det) < 1e-9 * max(1.0, s0 ** 3):
            d2 = s0 * s2 - s1 * s1             # too few distinct stations for a quadratic: local linear, then the mean
            if abs(d2) > 1e-9 * max(1.0, s0 ** 2):
                return (t0 * s2 - s1 * t1) / d2
            return t0 / s0
        d0 = (t0 * (s2 * s4 - s3 * s3) - s1 * (t1 * s4 - s3 * t2) + s2 * (t1 * s3 - s2 * t2))
        return d0 / det


def fit_widths(pts, widths, closed, evidence, *, mode="judge", w_trace=W_TRACE, half=FIT_HALF_M,
               min_support=MIN_SUPPORT, require_two=True, log_limit=4000):
    """pts: the smoothed line [(x, y, z)] (closed: last == first); widths: per point; evidence: [[E, N, src, contrast]].
    Returns (new widths, report). The report carries every rejection (station, side, source, value, fit, residual, reason)."""
    n = len(pts)
    m = n - 1 if closed else n                      # unique rows
    P = pts[:m]
    st = [0.0]
    for a, b in zip(P, P[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    lap = (st[-1] + math.hypot(P[0][0] - P[-1][0], P[0][2] - P[-1][2])) if closed else None
    T = _normals(P, closed)
    hw = [w / 2.0 for w in widths[:m]]
    # bucket the rows; each evidence point is owned by its nearest row
    rb: dict = {}
    for i, p in enumerate(P):
        rb.setdefault((int(p[0] // BUCKET), int(p[2] // BUCKET)), []).append(i)
    per = {"left": [[] for _ in range(m)], "right": [[] for _ in range(m)]}
    unowned = 0
    for e, nn, src, _c in evidence:
        bx, bz = int(e // BUCKET), int(nn // BUCKET)
        best, bi = None, None
        for dx in (-2, -1, 0, 1, 2):
            for dz in (-2, -1, 0, 1, 2):
                for i in rb.get((bx + dx, bz + dz), ()):
                    d = (P[i][0] - e) ** 2 + (P[i][2] - nn) ** 2
                    if best is None or d < best:
                        best, bi = d, i
        if bi is None:
            unowned += 1
            continue
        tx, tz = T[bi]
        ex, ez = e - P[bi][0], nn - P[bi][2]
        v = ex * tx + ez * tz
        u = ex * (-tz) + ez * tx                    # + = left of travel
        side = "left" if u > 0 else "right"
        if abs(v) > ALONG_M or abs(abs(u) - hw[bi]) > SEARCH_M:
            unowned += 1
            continue
        per[side][bi].append((abs(u), src))
    if mode not in ("judge", "fit"):
        raise ValueError(f"edge_fit mode {mode!r}: judge or fit")
    rep = {"mode": mode, "runs": [], "rows": m, "fit_half_m": half, "w_trace": w_trace, "min_support": min_support, "evidence_points": len(evidence),
           "evidence_unowned": unowned, "sides": {}, "rejections": []}
    fits = {}
    for side in ("left", "right"):
        # support: evidence points within +-half of each row
        cnt = [len(per[side][i]) for i in range(m)]
        sup = [0] * m
        why_unrel = [None] * m
        rows_in_half = max(1, int(round(half / max(1e-6, (st[-1] / max(1, m - 1))))))
        for i in range(m):
            vals = {}
            for d in range(-rows_in_half, rows_in_half + 1):
                j = i + d
                if closed:
                    j %= m
                elif j < 0 or j >= m:
                    continue
                for u, src in per[side][j]:
                    vals.setdefault(src, []).append(u - hw[j])      # each point against its own row's trace edge
            sup[i] = sum(len(v) for v in vals.values())
            # THE EVIDENCE IS TRUSTED HERE only when it is dense, both sensors read it, they agree, and it is tight
            if sup[i] < min_support:
                why_unrel[i] = "sparse"
                continue
            if len(vals) >= 2:
                meds = [sorted(v)[len(v) // 2] for v in vals.values() if len(v) >= max(3, min_support // 4)]
                if len(meds) < 2:
                    why_unrel[i] = "one sensor"
                    continue
                if max(meds) - min(meds) > AGREE_M:
                    why_unrel[i] = "sensors disagree"
                    continue
            elif require_two:
                why_unrel[i] = "one sensor"
                continue
            allv = sorted(x for v in vals.values() for x in v)
            med = allv[len(allv) // 2]
            mad = sorted(abs(x - med) for x in allv)[len(allv) // 2]
            if 1.4826 * mad > SPREAD_MAX_M:
                why_unrel[i] = "scattered"
        S, Y, B, R, SRC = [], [], [], [], []
        sparse_dropped = 0
        unrel = {}
        for i in range(m):
            S.append(st[i]); Y.append(hw[i]); B.append(1.0 if mode == "judge" else w_trace); R.append(i); SRC.append("trace")
            if mode == "judge":
                continue
            if why_unrel[i] is not None:
                unrel[why_unrel[i]] = unrel.get(why_unrel[i], 0) + 1
                sparse_dropped += len(per[side][i])
                continue
            for u, src in per[side][i]:
                S.append(st[i]); Y.append(u); B.append(1.0); R.append(i); SRC.append(src)
        win = _Win(S, half, lap)
        rw = [1.0] * len(S)
        f = list(hw)
        sigma = SIGMA_FLOOR_M
        for it in range(ROBUST_ITERS + 1):
            Wb = [b * r for b, r in zip(B, rw)]
            f = [win.at(st[i], Y, Wb) for i in range(m)]
            f = [hw[i] if v is None else v for i, v in enumerate(f)]
            res = [y - f[r] for y, r in zip(Y, R)]
            ev = sorted(abs(x) for x, s_ in zip(res, SRC) if s_ != "trace") or sorted(abs(x) for x in res)
            sigma = max(SIGMA_FLOOR_M, 1.4826 * ev[len(ev) // 2])
            c = 4.685 * sigma
            rw = [(1 - (x / c) ** 2) ** 2 if abs(x) < c else 0.0 for x in res]
        res = [y - f[r] for y, r in zip(Y, R)]
        cand = [abs(x) > K_HAMPEL * sigma for x in res]
        # the evidence's own reading of this edge near each row (the median of the points owned by rows i-2..i+2)
        ev_at = []
        for i in range(m):
            vals = []
            for d in range(-2, 3):
                j = i + d
                if closed:
                    j %= m
                elif j < 0 or j >= m:
                    continue
                vals.extend(u for u, _s in per[side][j])
            vals.sort()
            ev_at.append(vals[len(vals) // 2] if len(vals) >= 3 else None)
        # runs of candidate trace rows (consecutive row indices): a spike (<= SPIKE_MAX_ROWS) or a sustained change
        trace_c = sorted(R[k] for k in range(len(S)) if cand[k] and SRC[k] == "trace")
        runs, cur = [], []
        for r in trace_c:
            if cur and r == cur[-1] + 1:
                cur.append(r)
            else:
                if cur:
                    runs.append(cur)
                cur = [r]
        if cur:
            runs.append(cur)
        if closed and len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] == m - 1:
            runs[0] = runs[-1] + runs[0]
            runs.pop()
        verdict = {}                                    # row -> (reason, run length, rejected?)
        nrej = {"trace_spike": 0, "trace_sustained_contra": 0, "evidence_outlier": 0, "kept_spike_supported": 0,
                "kept_sustained_supported": 0, "kept_sustained_unsupported": 0, "kept_sustained_no_evidence": 0}
        runs_rep = []
        for run in runs:
            # does the evidence side with the trace's value or with the fit? (a majority over the run)
            vote = [ev_at[r] is not None and abs(ev_at[r] - hw[r]) < abs(ev_at[r] - f[r]) for r in run]
            have = sum(1 for r in run if ev_at[r] is not None)
            supported = have > 0 and sum(vote) * 2 > have
            if len(run) <= SPIKE_MAX_ROWS:
                why, rejd = ("kept_spike_supported", False) if supported else ("spike", True)
            elif mode == "fit" and not supported and have * 2 > len(run):
                why, rejd = "sustained-contra", True
            elif not have:
                why, rejd = "kept_sustained_no_evidence", False
            else:
                why, rejd = ("kept_sustained_supported" if supported else "kept_sustained_unsupported"), False
            for r in run:
                verdict[r] = (why, len(run), rejd)
            key = {"spike": "trace_spike", "sustained-contra": "trace_sustained_contra"}.get(why, why)
            nrej[key] += 1
            runs_rep.append({"side": side, "s0": round(st[run[0]], 1), "s1": round(st[run[-1]], 1), "rows": len(run),
                             "verdict": why, "rejected": rejd,
                             "trace_minus_fit_m": round(max((hw[r] - f[r] for r in run), key=abs), 3),
                             "evidence_votes": f"{sum(vote)}/{have}"})
        rej = []
        for k in range(len(S)):
            if not cand[k]:
                rej.append(False)
            elif SRC[k] == "trace":
                rej.append(verdict[R[k]][2])
            else:
                rej.append(True)
        keep_w = [0.0 if rj else b for b, rj in zip(B, rej)]
        f2 = [win.at(st[i], Y, keep_w) for i in range(m)]
        f2 = [f[i] if v is None else v for i, v in enumerate(f2)]
        for k in range(len(S)):
            if not cand[k]:
                continue
            if SRC[k] == "trace":
                why, ln, rejd = verdict[R[k]]
                e_ = ev_at[R[k]]
                detail = (f"{why}: a run of {ln} trace row(s), {res[k]:+.2f} m off the fit (sigma {sigma:.3f}); the evidence "
                          + ("reads none here" if e_ is None else f"reads {e_:.2f} m (trace {Y[k]:.2f}, fit {f[R[k]]:.2f})"))
            else:
                why, rejd = "outlier", True
                nrej["evidence_outlier"] += 1
                detail = f"outlier: {SRC[k]} point {res[k]:+.2f} m off the fit (sigma {sigma:.3f})"
            if len(rep["rejections"]) < log_limit:
                rep["rejections"].append({"s": round(st[R[k]], 1), "row": R[k], "side": side, "src": SRC[k],
                                          "value_m": round(Y[k], 3), "fit_m": round(f[R[k]], 3),
                                          "resid_m": round(res[k], 3), "reason": why, "rejected": rejd, "detail": detail})
        rep["runs"].extend(runs_rep)
        # before / after against the measured edge (every owned evidence point; in "judge" mode none of them built the fit)
        bef, aft = [], []
        for i in range(m):
            for u, _s in per[side][i]:
                bef.append(abs(u - hw[i])); aft.append(abs(u - f2[i]))

        def _q(v, p):
            v = sorted(v)
            return round(v[min(len(v) - 1, int(p * len(v)))], 3) if v else None
        moved = [f2[i] - hw[i] for i in range(m)]
        rep["sides"][side] = {
            "sigma_m": round(sigma, 3), "evidence_owned": sum(cnt), "evidence_sparse_dropped": sparse_dropped,
            "rows_evidence_trusted": sum(1 for x in why_unrel if x is None) if mode == "fit" else 0,
            "rows_evidence_not_trusted": unrel, "verdicts": nrej,
            "edge_to_evidence_m": {"before": {"median": _q(bef, .5), "mean": round(sum(bef) / len(bef), 3) if bef else None,
                                              "p90": _q(bef, .9)},
                                   "after": {"median": _q(aft, .5), "mean": round(sum(aft) / len(aft), 3) if aft else None,
                                             "p90": _q(aft, .9)}},
            "edge_moved_m": {"min": round(min(moved), 3), "median": round(sorted(moved)[m // 2], 3),
                             "max": round(max(moved), 3)}}
        fits[side] = f2
    new = [round(fits["left"][i] + fits["right"][i], 3) for i in range(m)]
    if closed:
        new.append(new[0])
    rep["widths_m"] = {"before": [round(min(widths), 2), round(max(widths), 2)], "after": [round(min(new), 2), round(max(new), 2)]}
    rep["rejections_logged"] = len(rep["rejections"])
    return new, rep
