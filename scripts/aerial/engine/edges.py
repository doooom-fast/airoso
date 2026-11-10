"""Both pavement edges along a guide, measured on cross-sections, fitted, with residuals and inferred stretches logged.

Generalised from Pikes Peak's re-trace (tracks/pikes-peak/source/road-course/pieces.py + retrace.py, ledger 0085) and
Exotics' line snap (tracks/exotics-racing-lv/source/trace/refine_trace.py). The guide only ORIENTS the sections; every
coordinate written is an edge found in the image (or a lidar-measured edge), or a fit through those.

Per section (every STEP_M along the guide), per side, outward from the guide along the normal, DS_M samples:

  surface edges (``edge_kind: "surface"``, the default): the first place the pavement score (channels ``pave``, or
     ``grey`` with ``score: "grey"``) stays off-road for RUN_M (>= 80 % of the run below 0.5, its mean below 0.35); the
     edge is the score's steepest fall within +-0.8 m of that place (parabolic sub-sample). A BOUNDARY BAND (a kerb, or
     a white edge line) within 1.5 m inside it takes precedence: the asphalt edge is the band's inner face (its 0.5
     crossing coming from the road), the band's outer side is kept (its width);
  line edges (``edge_kind: "lines"``: painted boundary bands on a lot whose pavement does not end): the bands
     (channels ``edge_band`` when the config defines its colour, else ``line``) past ``min_half_m``, peak over
     ``ridge_min``; the edge is the band's inner face (its 0.5 crossing from the road, sub-sampled), the band nearest
     the running half-width (first pass: the first band); its outer face is kept (the band's width);
  lidar edges: where a lidar-measured edge polyline crosses the section's ray within reach, THAT is the edge
     (status "lidar"), ahead of anything the image says.

Rejected stations (inferred; the fit bridges them, never follows them):
  opening   no edge within reach, or one past 2x the side's median half-width: another road joins (a junction mouth);
  weak      the score changes by less than ``weak`` across +-0.6 m of the edge;
  shadow    luminance under SHADOW_LUM on the road side within 1 m;
  outlier   inside 0.4x the side's median, or > OUTLIER_M off the running median (cars, paint, patches), or later
            > max(0.35 m, 3 MAD-sigma) off the fitted spline.

FIT: a smoothing spline of offset vs station through the accepted points, s = n * noise^2 (noise = NOISE_M), doubled
until the fitted edge's radius is >= ``rmin_m`` everywhere [RMIN_M is invented; Pikes Peak's tightest inner edge reads
~8 m]; the radius left is reported, not hidden. A closed loop is fitted on a wrapped copy (a third of the lap each
side). Residual = accepted edge point minus the fitted edge, along the normal.

Then the guide is re-made on the two edges' midline (smoothed 1.5 m) and everything runs again (``passes``).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from scipy.interpolate import UnivariateSpline

from . import channels as chn
from . import geom

STEP_M = 0.5
DS_M = 0.1
RUN_M = 2.0
SHADOW_LUM = 70.0
OUTLIER_M = 1.0
NOISE_M = 0.12
RMIN_M = 4.0          # [invented] tightest fitted edge radius allowed before the smoothing is raised
LIDAR_TOL_M = 2.0     # [invented] an image edge this close inside a lidar edge is the same boundary
MOUTH_WIN_M = 200.0   # [invented] the baseline a mouth stands out from: the side's median edge over this
MOUTH_EXCESS_M = 3.0  # [invented] a surface edge this far past its baseline is another road's


class Ctx:
    """What the edge finder reads: the ortho, its channels, lidar edges (ENU polylines) and the track's settings."""

    def __init__(self, ortho, ch: dict, lidar_edges=None, opts: dict | None = None):
        self.o = ortho
        self.ch = ch
        self.lidar = [np.asarray(e, float) for e in (lidar_edges or [])]
        self.opts = dict(opts or {})

    def sample(self, name, E, N):
        px, py = self.o.en_to_px(E, N)
        return chn.sample(self.ch[name], px, py)


def _profiles(ctx: Ctx, P, L, reach, score):
    offs = np.arange(0, reach + 1e-9, DS_M)
    res = {}
    for side, sgn in (("left", 1.0), ("right", -1.0)):
        E = P[:, 0][:, None] + sgn * offs[None, :] * L[:, 0][:, None]
        N = P[:, 1][:, None] + sgn * offs[None, :] * L[:, 1][:, None]
        px, py = ctx.o.en_to_px(E, N)
        d = {k: chn.sample(ctx.ch[k], px, py) for k in ("kerb", "lum", "band")}
        d["line"] = chn.sample(ctx.ch["edge_band"] if "edge_band" in ctx.ch else ctx.ch["line"], px, py)
        d["pave"] = chn.sample(ctx.ch[score], px, py)
        res[side] = d
    return offs, res


def find_surface_edge(score, kerb, lum, offs, band=None):
    """Pikes Peak's find_edge (pieces.py), unchanged in its rules."""
    n = len(offs)
    sc = ndimage.gaussian_filter1d(score, 2.0, mode="nearest")
    run = int(round(RUN_M / DS_M))
    below = sc < 0.5
    j = None
    for i in range(1, n - run):
        if below[i] and below[i:i + run].mean() >= 0.8 and sc[i:i + run].mean() < 0.35:
            j = i
            break
    if j is None:
        return None
    w8 = int(round(0.8 / DS_M))
    lo_, hi_ = max(1, j - w8), min(n - 2, j + w8)
    g = -np.gradient(sc)
    i0 = lo_ + int(np.argmax(g[lo_:hi_ + 1]))
    gm, g0, gp = g[i0 - 1], g[i0], g[i0 + 1]
    den = gm - 2 * g0 + gp
    frac = 0.5 * (gm - gp) / den if den < -1e-9 else 0.0
    x = offs[i0] + float(np.clip(frac, -0.5, 0.5)) * DS_M
    k6 = int(round(0.6 / DS_M))
    strength = float(np.mean(sc[max(0, i0 - k6):i0]) - np.mean(sc[i0 + 1:i0 + 1 + k6]))
    road_lum = float(np.mean(lum[max(0, i0 - int(1 / DS_M)):i0])) if i0 > 0 else float(lum[0])
    out = {"edge": x, "strength": strength, "road_lum": road_lum, "kerb": None, "type": "surface"}
    k15 = int(round(1.5 / DS_M))
    lo = max(1, i0 - k15)
    for name, prof_ in (("kerb", kerb), ("line", band)):
        if prof_ is None:
            continue
        if prof_[lo:i0 + 3].max() <= 0.5:
            continue
        lo2 = lo
        while lo2 > 1 and prof_[lo2 - 1] >= 0.5 and i0 - lo2 < int(round(3.0 / DS_M)):
            lo2 -= 1
        for i in range(max(1, lo2 - 1), i0 + 3):
            if prof_[i - 1] < 0.5 <= prof_[i]:
                xi = offs[i - 1] + (0.5 - prof_[i - 1]) / max(prof_[i] - prof_[i - 1], 1e-6) * DS_M
                out["kerb"] = {"inner": xi, "outer": x, "width": x - xi}
                out["type"] = name
                out["strength"] = max(strength, 0.5)
                break
        if out["kerb"] is not None:
            break
    return out


def find_line_edges(line, lum, offs, min_half, ridge_min):
    """Every painted boundary band past ``min_half`` whose score passes 0.5 (its peak at least ``ridge_min``):
    [(inner face, peak, road_lum, outer face)], nearest first. The faces are the 0.5 crossings, linear sub-sample;
    the asphalt edge is the inner face (as a kerb's, find_surface_edge)."""
    v = ndimage.gaussian_filter1d(line, 1.0, mode="nearest")
    out = []
    n = len(v)
    i = 1
    while i < n:
        if offs[i] >= min_half and v[i - 1] < 0.5 <= v[i]:
            xi = offs[i - 1] + (0.5 - v[i - 1]) / max(v[i] - v[i - 1], 1e-6) * DS_M
            j = i
            while j + 1 < n and v[j + 1] >= 0.5:
                j += 1
            xo = offs[j] if j + 1 >= n else offs[j] + (v[j] - 0.5) / max(v[j] - v[j + 1], 1e-6) * DS_M
            pk = float(v[i:j + 1].max())
            if pk >= ridge_min and xo - xi >= 2 * DS_M:
                rl = float(np.mean(lum[max(0, i - int(1.5 / DS_M)):max(1, i - int(0.5 / DS_M))]))
                out.append((xi, pk, rl, xo))
            i = j + 1
        i += 1
    return out


def _lidar_hits(ctx: Ctx, P, L, sgn, reach):
    """Per section, the offset (along sgn * L) at which a lidar edge polyline crosses the ray, or nan."""
    out = np.full(len(P), np.nan)
    for E in ctx.lidar:
        a, b = E[:-1], E[1:]
        for k in range(len(P)):
            o = P[k]
            d = sgn * L[k]
            # segment / ray intersection: o + t d = a + u (b - a)
            ab = b - a
            den = d[0] * ab[:, 1] - d[1] * ab[:, 0]
            ok = np.abs(den) > 1e-12
            ao = a - o
            t = np.where(ok, (ao[:, 0] * ab[:, 1] - ao[:, 1] * ab[:, 0]) / np.where(ok, den, 1), np.nan)
            u = np.where(ok, (ao[:, 0] * d[1] - ao[:, 1] * d[0]) / np.where(ok, den, 1), np.nan)
            hit = ok & (t >= 0) & (t <= reach) & (u >= 0) & (u <= 1)
            if hit.any():
                tt = float(np.min(t[hit]))
                out[k] = tt if not np.isfinite(out[k]) else min(out[k], tt)
    return out


def pair_lines(prof, offs, opts, hw_ref=None):
    """Lines mode: per section, the pair of boundary bands (one each side) that bound the road. First pass: of the
    pairs whose inner-face width lies in ``width_m`` [lo, hi], the one most centred on the guide (refine_trace.py's
    rule: the road lies between two bands, the guide near its middle); later passes: the pair nearest the running
    half-width on both sides. Returns per side a list of the chosen candidate (or None)."""
    lo, hi = opts.get("width_m", (8.0, 22.0))
    mh, rm = opts.get("min_half_m", 2.5), opts.get("ridge_min", 0.6)
    n = len(prof["left"]["line"])
    picks = {"left": [None] * n, "right": [None] * n}
    for k in range(n):
        cl = find_line_edges(prof["left"]["line"][k], prof["left"]["lum"][k], offs, mh, rm)
        cr = find_line_edges(prof["right"]["line"][k], prof["right"]["lum"][k], offs, mh, rm)
        best = None
        for a in cl:
            for b in cr:
                w = a[0] + b[0]
                if not (lo <= w <= hi):
                    continue
                if hw_ref is not None and np.isfinite(hw_ref[k]):
                    sc = abs(a[0] - hw_ref[k]) + abs(b[0] - hw_ref[k])
                else:
                    sc = abs(a[0] - b[0])
                if best is None or sc < best[0]:
                    best = (sc, a, b)
        if best is not None:
            picks["left"][k], picks["right"][k] = best[1], best[2]
    return picks


def _mouth_openings(x, ok, types, closed):
    """A junction mouth (a side road, a pit lane, a service road) tapers the surface edge OUT and back over tens of
    metres, too gradually for the running median to call it an outlier. Against the side's own baseline (the median
    of its seen edge over MOUTH_WIN_M), a SURFACE edge more than MOUTH_EXCESS_M further out is an opening: the far
    edge of another road, bridged by the fit and never followed. An edge at a kerb or a painted line is a road
    boundary however far out it stands (a circuit widens at a corner exit between its kerbs) and is kept."""
    w = int(round(MOUTH_WIN_M / STEP_M)) | 1
    base = geom.running_median(x, ok, w, closed)
    return ok & (types == "surface") & (x > base + MOUTH_EXCESS_M)


def measure_side(ctx: Ctx, P, L, side, offs, prof, opts, hw_ref=None, closed=False, picks=None):
    n = len(P)
    kind = opts.get("edge_kind", "surface")
    weak = opts.get("weak", 0.30)
    raw = []
    x = np.full(n, np.nan)
    status = np.array(["opening"] * n, dtype=object)
    pr = prof[side]
    for k in range(n):
        if kind == "lines":
            e = picks[side][k] if picks is not None else None
            if e is None:
                raw.append(None)
                continue
            r = {"edge": e[0], "strength": e[1], "road_lum": e[2], "type": "line",
                 "kerb": {"inner": e[0], "outer": e[3], "width": e[3] - e[0]}}
            raw.append(r)
            x[k] = e[0]
            status[k] = "seen"
        else:
            r = find_surface_edge(pr["pave"][k], pr["kerb"][k], pr["lum"][k], offs, pr["band"][k])
            raw.append(r)
            if r is None:
                continue
            x[k] = r["kerb"]["inner"] if r["kerb"] else r["edge"]
            status[k] = "weak" if r["strength"] < weak else ("shadow" if r["road_lum"] < SHADOW_LUM else "seen")
    ok = status == "seen"
    mid = np.zeros(n, bool)
    mid[int(0.2 * n):int(0.8 * n) + 1] = True
    if closed:
        mid[:] = True
    hw = np.median(x[ok & mid]) if (ok & mid).sum() >= 5 else (np.median(x[ok]) if ok.any() else np.nan)
    if np.isfinite(hw):
        status[ok & (x > 2.0 * hw)] = "opening"
        status[ok & (x < 0.4 * hw)] = "outlier"
        ok = status == "seen"
    if kind != "lines":
        types = np.array([None if r is None else r["type"] for r in raw], dtype=object)
        jo = _mouth_openings(x, ok, types, closed)
        status[jo] = "opening"
        ok = status == "seen"
    for _ in range(2):
        med = geom.running_median(x, ok, 21, closed)
        bad = ok & (np.abs(x - med) > OUTLIER_M)
        status[bad] = "outlier"
        ok = status == "seen"
    med = geom.running_median(x, ok, 21, closed)
    far = (status == "outlier") & np.isfinite(x) & (x > med + 4)
    status[far] = "opening"
    if ctx.lidar:
        # a lidar edge is THE edge where the image found none before it (no edge, an opening, or one at most
        # LIDAR_TOL_M short of it: the wall's own top reads as pavement); an image edge well inside it is a nearer
        # road's edge and stands
        sgn = 1.0 if side == "left" else -1.0
        lh = _lidar_hits(ctx, P, L, sgn, offs[-1])
        hit = np.isfinite(lh) & ((status != "seen") | ~np.isfinite(x) | (x >= lh - LIDAR_TOL_M))
        x[hit] = lh[hit]
        status[hit] = "lidar"
    return raw, x, status


def _wrap_fit(s, x, ok, ss, period):
    """A smoothing spline over a closed loop: fitted on the samples with a third of the lap copied each side."""
    idx = np.where(ok)[0]
    S, X = s[idx], x[idx]
    pad = period / 3
    lo = S >= period - pad
    hi = S <= pad
    S2 = np.r_[S[lo] - period, S, S[hi] + period]
    X2 = np.r_[X[lo], X, X[hi]]
    o = np.argsort(S2, kind="stable")
    S2, X2 = S2[o], X2[o]
    keep = np.r_[True, np.diff(S2) > 1e-9]
    return UnivariateSpline(S2[keep], X2[keep], k=3, s=ss * keep.sum() / max(len(idx), 1))


def fit_edge(s, x, status, P, L, sgn, closed=False, period=None, noise=NOISE_M, rmin=RMIN_M):
    use = np.isin(status, ("seen", "lidar"))
    if use.sum() < 6:
        return None, None
    sp = None
    ss = noise ** 2 * use.sum()
    for _ in range(5):
        ss = noise ** 2 * use.sum()
        sp = _wrap_fit(s, x, use, ss, period) if closed else UnivariateSpline(s[use], x[use], k=3, s=ss)
        r = x - sp(s)
        sig = 1.4826 * np.median(np.abs(r[use]))
        bad = use & (status != "lidar") & (np.abs(r) > max(0.35, 3 * sig))
        if not bad.any():
            break
        status[bad] = "outlier"
        use = np.isin(status, ("seen", "lidar"))
        if use.sum() < 6:
            return None, None
    idx = np.where(use)[0]
    lo = int(np.searchsorted(s, s[idx[0]] + 2.0))
    hi = int(np.searchsorted(s, s[idx[-1]] - 2.0))
    for _ in range(4):
        sp = _wrap_fit(s, x, use, ss, period) if closed else UnivariateSpline(s[use], x[use], k=3, s=ss)
        if hi <= lo or geom.min_radius(P[lo:hi] + (sgn * sp(s[lo:hi]))[:, None] * L[lo:hi]) >= rmin:
            break
        ss *= 2
    return sp, ss


def measure_strip(ctx: Ctx, G, closed=False, opts: dict | None = None):
    """Measure a strip of road along guide G (ENU, any spacing). Returns a dict (see the module docstring)."""
    opts = dict(ctx.opts, **(opts or {}))
    passes = int(opts.get("passes", 2))
    reach = float(opts.get("reach_m", 30.0))
    score = opts.get("score", "pave")
    rmin = float(opts.get("rmin_m", RMIN_M))
    P = geom.resample(G, STEP_M, closed=closed)
    hw_ref = {"left": None, "right": None}
    out = None
    for it in range(passes):
        T, L = geom.normals(P, closed=closed)
        s = geom.cumlen(P)
        period = geom.closed_len(P) if closed else None
        offs, prof = _profiles(ctx, P, L, reach, score)
        picks = pair_lines(prof, offs, opts, hw_ref["left"]) if opts.get("edge_kind") == "lines" else None
        out = {}
        for side, sgn in (("left", 1.0), ("right", -1.0)):
            raw, x, status = measure_side(ctx, P, L, side, offs, prof, opts, hw_ref[side], closed, picks)
            sp, ss = fit_edge(s, x, status, P, L, sgn, closed, period, noise=float(opts.get("noise_m", NOISE_M)), rmin=rmin)
            out[side] = dict(raw=raw, x=x, status=status, sp=sp, ss=ss)
        if out["left"]["sp"] is None or out["right"]["sp"] is None:
            return {"P": P, "L": L, "s": s, "closed": closed, "sides": out, "failed": True}
        if it < passes - 1:
            dl, dr = _held(out["left"], s, closed), _held(out["right"], s, closed)
            # on the recentred guide each edge sits half the width out: that is the next pass's reference
            half = geom.running_median((dl + dr) / 2, np.ones(len(dl), bool), 41, closed)
            c = np.clip((dl - dr) / 2, -3, 3)
            C = P + c[:, None] * L
            C = geom.resample(C, 0.25, closed=closed)
            C = geom.smooth(C, 1.5, 0.25, closed=closed)
            P = geom.resample(C, STEP_M, closed=closed)
            f = np.linspace(0, 1, len(half))
            hw_ref["left"] = hw_ref["right"] = np.interp(np.linspace(0, 1, len(P)), f, half)
    T, L = geom.normals(P, closed=closed)
    s = geom.cumlen(P)
    return {"P": P, "L": L, "s": s, "closed": closed, "sides": out, "offs_max": reach, "failed": False}


def _held(o, s, closed):
    """The fitted offset per station; for an open strip held flat past the first / last accepted point."""
    d = o["sp"](s)
    if closed:
        return d
    use = np.where(np.isin(o["status"], ("seen", "lidar")))[0]
    d = d.copy()
    d[:use[0]] = d[use[0]]
    d[use[-1] + 1:] = d[use[-1]]
    return d


def summarise(m: dict, centre_smooth_m: float = 2.0) -> dict:
    """Edges, centre, width and the diagnostics of a measured strip (ENU arrays plus a JSON-able report)."""
    P, L, s, closed = m["P"], m["L"], m["s"], m["closed"]
    rep, d = {}, {}
    for side, sgn in (("left", 1.0), ("right", -1.0)):
        o = m["sides"][side]
        st = o["status"]
        use = np.isin(st, ("seen", "lidar"))
        dd = _held(o, s, closed)
        d[side] = dd
        res = (o["x"] - o["sp"](s))[use & (st != "lidar")]
        E = P + (sgn * dd)[:, None] * L
        inferred = {}
        for why in ("opening", "weak", "shadow", "outlier"):
            rr = [(s[a], s[b]) for a, b in geom.runs(st == why) if s[b] - s[a] >= 1.0]
            if rr:
                inferred[why] = [[round(float(a), 1), round(float(b), 1)] for a, b in rr]
        kinds = {}
        for r, u in zip(o["raw"], use):
            if u and r is not None:
                kinds[r["type"]] = kinds.get(r["type"], 0) + 1
        nl = int((st == "lidar").sum())
        if nl:
            kinds["lidar"] = nl
        kw = [r["kerb"]["width"] for r, u in zip(o["raw"], use) if u and r is not None and r.get("kerb")]
        rep[side] = {"seen_fraction": round(float(use.mean()), 3), "residual_m": geom.pct(res),
                     "smoothing": round(float(o["ss"]), 4),
                     "min_radius_m": round(float(min(geom.min_radius(E), 9999.0)), 1),
                     "inferred_m": inferred, "edge_evidence": kinds,
                     "kerb_or_line_width_m_p50": round(float(np.median(kw)), 2) if kw else None}
        d[side + "_E"] = E
    C = P + ((d["left"] - d["right"]) / 2)[:, None] * L
    C = geom.smooth(C, centre_smooth_m, STEP_M, closed=closed)
    W = d["left"] + d["right"]
    rep["width_m"] = {"min": round(float(W.min()), 2), "p50": round(float(np.median(W)), 2), "max": round(float(W.max()), 2)}
    rep["length_m"] = round(float(geom.closed_len(C) if closed else geom.cumlen(C)[-1]), 1)
    return {"C": C, "W": W, "left_E": d["left_E"], "right_E": d["right_E"], "dl": d["left"], "dr": d["right"], "report": rep}
