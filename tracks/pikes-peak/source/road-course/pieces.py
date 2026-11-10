"""The PPIR infield's paved pieces, measured edge to edge off NAIP 2023 0.3 m (ledger 0085 Re-trace).

WHAT IS HAND-GIVEN AND WHAT IS MEASURED
  - Hand-given: only WHICH piece. Each piece is named by a chain of 2-5 "via" pixels (junction to junction) that say
    which paved road it is. They place no geometry.
  - Measured:
    1. A guide through the pavement: the least-cost path between the vias over the pavement mask, cost falling with
       the distance to the nearest non-pavement (it seeks the medial axis); smoothed (sigma 3 m). The guide only orients
       the cross-sections.
    2. Every 0.5 m along it, both pavement edges along the normal, with sub-pixel localisation (below).
    3. A smoothing spline per edge through the accepted edge points, with a curvature limit.
    4. The centre: the midline of the two fitted edges; the width: their distance; the guide re-made on that centre and
       steps 2-3 run a second time.

EDGE FINDING along one normal (pavement score: naip.channels()["pave"], 0..1, grey asphalt / kerb high, grass, dirt and
the tan concrete low):
  - from the guide outwards, the first place the score stays below 0.5 for >= 2.0 m; the edge is the 0.5 crossing,
    linear between the two 0.1 m samples bracketing it (the score is a 0.7 px gaussian of the per-pixel class, so the
    crossing is a sub-pixel edge);
  - a KERB is red / white blocks (naip.channels()["kerb"]); where the kerb score passes 0.4 within 2 m inside the
    crossing, the edge is a kerb edge: the pavement (asphalt) edge is moved to the kerb's INNER face (its 0.5 crossing
    coming from the road), and the kerb's outer face (the grass crossing) is kept beside it;
  - rejected (marked inferred, the spline bridges them):
      * weak: the score changes by < 0.45 across +-0.6 m of the crossing;
      * shadow: luminance < 70 on the road side within 1 m of the crossing;
      * outlier: > 1.0 m off the running median (21 stations, 10 m) of that edge's accepted offsets (cars, paint,
        patches, a gore's tip);
  - OPENING: no crossing within (running-median offset + 4 m), with pavement continuing there: another piece, the oval,
    or the lot joins. Labelled, bridged by the spline, never followed.
SPLINE: scipy UnivariateSpline of offset vs station, weights 1, smoothing s = n * 0.12^2 (the edge noise), doubled until
the fitted edge's radius is >= 4 m everywhere [the 4 m limit is invented; the tightest infield corner's inner edge reads
~8 m]. Residual = accepted edge point minus the fitted edge, along the normal.

WEAR (Kevin 2026-11-07: "Follow curbs and road wear, it's easy for human eye"): across each cross-section, luminance
between the two asphalt edges, 0.5 m in from each; the clean reference is that section's 80th percentile; darkening =
(ref - lum) / ref, smoothed 1.5 m across. Per section: the band's peak darkening and its position u (0 = right edge,
1 = left edge, facing the piece's own direction). Per piece: the median section peak (the wear index) and the median
profile in 20 bins of u.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.interpolate import UnivariateSpline
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import naip  # noqa: E402

BBOX = (180, 200, 1320, 1260)          # x0, y0, x1, y1 pixels: the infield and the oval's inside around it
STEP = 0.5
SEARCH = 30.0
DS = 0.1

# piece id -> (description, via pixels). Vias are junction to junction; the order is the piece's own direction.
PIECES = {
    "ne_lane": ("the lane off the back stretch, oval diverge to the hairpin top (newest pavement)",
                [(1170, 520), (1000, 392), (870, 300), (800, 283), (745, 288)]),
    "hairpin_w": ("the hairpin's west leg, down island B's west side to the C road junction",
                  [(745, 288), (716, 360), (722, 440), (735, 490)]),
    "diag_n": ("the wide road south-east from the C junction to the parallel lane's mouth",
               [(735, 490), (815, 543)]),
    "diag_s": ("the wide road on south-east to the lot's north end",
               [(815, 543), (900, 640), (975, 745)]),
    "n_road": ("the road inside the grass lens, NW oval junction to the hairpin top",
               [(300, 405), (400, 338), (550, 292), (680, 268), (745, 288)]),
    "arc_nw": ("the kerbed sweeper, the oval's inside at the NW junction to the west road's top",
               [(250, 458), (330, 425), (420, 440), (470, 490), (485, 525)]),
    "c_road": ("the C road, the west road's top to the C junction (the S-curve's north mouth opens off it)",
               [(488, 545), (520, 542), (560, 525), (620, 510), (695, 500), (735, 490)]),
    "west_n": ("the west road, its top junction to the S-curve's west mouth",
               [(485, 525), (480, 580), (485, 625)]),
    "bottom": ("the west road on south, round the SW bend and east along the bottom to the lot's west side",
               [(485, 625), (472, 700), (500, 790), (560, 830), (680, 840), (785, 862)]),
    "s_curve": ("the older S-curve, C road mouth down, round its hairpin, west to the west road",
                [(690, 503), (690, 560), (712, 640), (705, 690), (650, 680), (600, 640), (530, 625), (485, 625)]),
    "par_lane": ("the narrow parallel lane, the diag road east and south-east to the lot ring's north-east corner",
                 [(815, 543), (960, 535), (1050, 570), (1150, 650), (1195, 780), (1225, 900)]),
    # the lot ring: the skidpad lot's perimeter. The lot inside it is paved too, so the ring has ONE edge (the lot's
    # outer boundary, its LEFT: the vias run clockwise) and its inner side is open lot; its driven width is the wear
    # band. A polyline guide through the vias (the lot's open pavement would pull a least-cost path to its middle).
    "ring_nw": ("the lot ring's north-west side, the bottom road's mouth to the diag road's (clockwise)",
                [(790, 870), (812, 815), (860, 772), (950, 742)], "ring"),
    "ring_ne": ("the lot ring's north-east side (the diag road continued) past the parallel lane's mouth to the east side",
                [(950, 742), (1080, 805), (1180, 860), (1240, 905), (1257, 960)], "ring"),
    "ring_s": ("the lot ring's east, south and west sides, round to the bottom road's mouth",
               [(1257, 960), (1262, 1050), (1250, 1140), (1210, 1195), (1100, 1215), (980, 1212), (880, 1190),
                (820, 1130), (800, 1040), (795, 950), (790, 870)], "ring"),
}


def mask():
    ch = naip.channels()
    m = ch["pave"] > 0.5
    m = ndimage.binary_opening(m, iterations=1)
    lab, n = ndimage.label(~m)
    sizes = ndimage.sum(np.ones_like(lab), lab, range(n + 1))
    small = sizes < 60                       # holes < 60 px (5.4 m2): cars, paint, debris -> pavement
    small[0] = False
    m = m | small[lab]
    return m


_G = {}


def graph(m):
    if "G" in _G:
        return _G["G"]
    x0, y0, x1, y1 = BBOX
    sub = m[y0:y1, x0:x1]
    dt = ndimage.distance_transform_edt(sub)
    H, W = sub.shape
    cost = np.where(sub, 1.0 / (0.5 + np.minimum(dt, 40)) ** 1.5, 3.0)   # off the mask: allowed, dear (a guide only orients sections)
    idx = np.arange(H * W).reshape(H, W)
    rows, cols, vals = [], [], []
    for dy, dx in [(0, 1), (1, 0), (1, 1), (1, -1)]:
        ys = slice(0, H - dy); ye = slice(dy, H)
        if dx >= 0:
            xs = slice(0, W - dx); xe = slice(dx, W)
        else:
            xs = slice(-dx, W); xe = slice(0, W + dx)
        a = idx[ys, xs].ravel(); b = idx[ye, xe].ravel()
        w = 0.5 * (cost.ravel()[a] + cost.ravel()[b]) * (1.4142 if dx and dy else 1.0)
        ok = np.isfinite(w)
        rows += [a[ok], b[ok]]; cols += [b[ok], a[ok]]; vals += [w[ok], w[ok]]
    G = csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(H * W, H * W))
    _G["G"] = (G, W)
    return _G["G"]


def guide(m, vias, mode="road"):
    if mode == "ring":
        e, n = naip.px_to_en(np.array([v[0] for v in vias], float), np.array([v[1] for v in vias], float))
        from scipy.interpolate import splprep, splev
        V = np.c_[e, n]
        tck, _ = splprep([V[:, 0], V[:, 1]], s=len(V) * 4.0, k=min(3, len(V) - 1))
        Q = np.array(splev(np.linspace(0, 1, 2000), tck)).T
        return naip.resample(Q, STEP)
    G, W = graph(m)
    x0, y0, _, _ = BBOX
    sub = m[y0:y0 + G.shape[0] // W, x0:x0 + W]
    dt = ndimage.distance_transform_edt(sub)

    def snap(x, y):                       # a via names a road; put it on that road's pavement (max clearance within 8 px)
        r = 8
        win = dt[y - y0 - r:y - y0 + r + 1, x - x0 - r:x - x0 + r + 1]
        j = np.unravel_index(np.argmax(win), win.shape)
        return x - r + j[1], y - r + j[0]
    vias = [snap(*v) for v in vias]
    path = []
    for (ax, ay), (bx, by) in zip(vias, vias[1:]):
        a = (ay - y0) * W + (ax - x0); b = (by - y0) * W + (bx - x0)
        _, pred = dijkstra(G, indices=a, return_predecessors=True)
        seg = [b]
        while seg[-1] != a:
            p = pred[seg[-1]]
            if p < 0:
                raise SystemExit(f"no pavement path {(ax, ay)} -> {(bx, by)}")
            seg.append(p)
        seg = seg[::-1]
        path += seg if not path else seg[1:]
    path = np.array(path)
    px = np.c_[path % W + x0, path // W + y0].astype(float)
    e, n = naip.px_to_en(px[:, 0], px[:, 1])
    P = naip.resample(np.c_[e, n], 0.25)
    sig = 3.0 / 0.25
    P = np.c_[ndimage.gaussian_filter1d(P[:, 0], sig, mode="nearest"), ndimage.gaussian_filter1d(P[:, 1], sig, mode="nearest")]
    return naip.resample(P, STEP)


def find_edge(score, kerb, lum, offs, band=None):
    """Walk from the guide (offset 0) outwards on one side; offs ascending >= 0 (metres along that side's normal).

    1. j: the first sample from which the score (smoothed 0.2 m along the normal) stays off-road for 2 m: >= 80 % of
       that run below 0.5 and its mean below 0.35.
    2. The edge: the steepest fall of the score within +-0.8 m of j (parabolic sub-sample) -- the boundary's own
       gradient along the normal.
    3. A BOUNDARY BAND within 1.5 m inside j -- a kerb (red / white blocks) or a white edge line (the older pieces are
       edged with one) -- takes precedence: the asphalt edge is the band's inner face (its 0.5 crossing coming from the
       road, linear sub-sample); the band's outer side is kept (kerb width)."""
    n = len(offs)
    sc = ndimage.gaussian_filter1d(score, 2.0, mode="nearest")
    run = int(round(2.0 / DS))
    below = sc < 0.5
    j = None
    for i in range(1, n - run):
        if below[i] and below[i:i + run].mean() >= 0.8 and sc[i:i + run].mean() < 0.35:
            j = i; break
    if j is None:
        return None
    w8 = int(round(0.8 / DS))
    lo_, hi_ = max(1, j - w8), min(n - 2, j + w8)
    g = -np.gradient(sc)
    i0 = lo_ + int(np.argmax(g[lo_:hi_ + 1]))
    gm, g0, gp = g[i0 - 1], g[i0], g[i0 + 1]
    den = gm - 2 * g0 + gp
    frac = 0.5 * (gm - gp) / den if den < -1e-9 else 0.0
    x = offs[i0] + float(np.clip(frac, -0.5, 0.5)) * DS
    k6 = int(round(0.6 / DS))
    strength = float(np.mean(sc[max(0, i0 - k6):i0]) - np.mean(sc[i0 + 1:i0 + 1 + k6]))
    road_lum = float(np.mean(lum[max(0, i0 - int(1 / DS)):i0]))
    out = {"edge": x, "strength": strength, "road_lum": road_lum, "kerb": None, "type": "surface"}
    k15 = int(round(1.5 / DS))
    lo = max(1, i0 - k15)
    for name, prof_ in (("kerb", kerb), ("line", band)):
        if prof_ is None:
            continue
        seg = prof_[lo:i0 + 3]
        if seg.max() <= 0.5:
            continue
        lo2 = lo
        while lo2 > 1 and prof_[lo2 - 1] >= 0.5 and i0 - lo2 < int(round(3.0 / DS)):   # a kerb wider than 1.5 m
            lo2 -= 1
        for i in range(max(1, lo2 - 1), i0 + 3):
            if prof_[i - 1] < 0.5 <= prof_[i]:
                xi = offs[i - 1] + (0.5 - prof_[i - 1]) / max(prof_[i] - prof_[i - 1], 1e-6) * DS
                out["kerb"] = {"inner": xi, "outer": x, "width": x - xi}
                out["type"] = name
                out["strength"] = max(strength, 0.5)
                break
        if out["kerb"] is not None:
            break
    return out


def profiles(P, L, half=SEARCH, score="pave"):
    ch = naip.channels()
    offs = np.arange(0, half + 1e-9, DS)
    res = {}
    for side, sgn in (("left", 1.0), ("right", -1.0)):
        E = P[:, 0][:, None] + sgn * offs[None, :] * L[:, 0][:, None]
        N = P[:, 1][:, None] + sgn * offs[None, :] * L[:, 1][:, None]
        res[side] = {k: naip.sample(ch[k], E, N) for k in ("kerb", "lum", "band")}
        res[side]["pave"] = naip.sample(ch[score], E, N)
    return offs, res


def running_median(x, ok, w=21):
    out = np.full(len(x), np.nan)
    idx = np.where(ok)[0]
    if len(idx) == 0:
        return out
    for i in range(len(x)):
        sel = idx[np.abs(idx - i) <= w // 2]
        if len(sel) >= 3:
            out[i] = np.median(x[sel])
    # fill from nearest
    good = np.isfinite(out)
    if good.any():
        out[~good] = np.interp(np.where(~good)[0], np.where(good)[0], out[good])
    return out


def measure_side(P, L, side, offs, prof, min_dist=0.0, weak=0.30):
    n = len(P)
    raw = []
    for k in range(n):
        o = offs >= min_dist
        r = find_edge(prof[side]["pave"][k][o], prof[side]["kerb"][k][o], prof[side]["lum"][k][o], offs[o],
                      prof[side]["band"][k][o])
        raw.append(r)
    x = np.array([np.nan if r is None else (r["kerb"]["inner"] if r["kerb"] else r["edge"]) for r in raw])
    status = np.array(["seen"] * n, dtype=object)
    for k, r in enumerate(raw):
        if r is None:
            status[k] = "opening"
        elif r["strength"] < weak:
            status[k] = "weak"
        elif r["road_lum"] < 70:
            status[k] = "shadow"
    ok = status == "seen"
    # the piece's own half-width on this side: the median seen offset over its middle 60 %; a crossing past 2x it is
    # another pavement's edge (an opening: a junction mouth), one inside 0.4x it is paint / a car / a patch
    mid = np.zeros(n, bool); mid[int(0.2 * n):int(0.8 * n) + 1] = True
    hw = np.median(x[ok & mid]) if (ok & mid).sum() >= 5 else (np.median(x[ok]) if ok.any() else np.nan)
    if np.isfinite(hw):
        far = ok & (x > 2.0 * hw); near = ok & (x < 0.4 * hw)
        status[far] = "opening"; status[near] = "outlier"
        ok = status == "seen"
    for _ in range(2):
        med = running_median(x, ok)
        dev = np.abs(x - med)
        newbad = ok & (dev > 1.0)
        ok = ok & ~newbad
        status[newbad] = "outlier"
    med = running_median(x, ok)
    # a crossing far beyond the median with pavement continuing at the median + 1 m: an opening
    for k in range(n):
        if status[k] in ("outlier",) and np.isfinite(x[k]) and x[k] > med[k] + 4:
            status[k] = "opening"
        if status[k] == "opening" and not np.isfinite(x[k]):
            pass
    return raw, x, status


def edge_min_radius(E):
    """The tightest radius of a polyline over 2 m of its own arc length (turning angle per metre)."""
    if len(E) < 6:
        return np.inf
    Q = naip.resample(E, 0.5)
    if len(Q) < 6:
        return np.inf
    T = np.diff(Q, axis=0)
    h = np.unwrap(np.arctan2(T[:, 1], T[:, 0]))
    dh = np.abs(h[4:] - h[:-4]) / 2.0          # over 2 m
    return float(1 / max(dh.max(), 1e-9))


def fit_edge(s, x, status, noise=0.12, rmin=4.0, guideP=None, L=None, sgn=1.0):
    """Robust smoothing spline of the edge offset vs station. Points > max(0.35 m, 3 x the MAD sigma) off the fit are
    rejected (status 'outlier') and the fit repeated; then the smoothing is doubled until the fitted edge's radius is
    >= rmin over the seen range (2 m in from its ends)."""
    ok = status == "seen"
    if ok.sum() < 6:
        return None, None
    for _ in range(5):
        ss = noise ** 2 * ok.sum()
        sp = UnivariateSpline(s[ok], x[ok], k=3, s=ss)
        r = x - sp(s)
        sig = 1.4826 * np.median(np.abs(r[ok]))
        bad = ok & (np.abs(r) > max(0.35, 3 * sig))
        if not bad.any():
            break
        status[bad] = "outlier"
        ok = status == "seen"
        if ok.sum() < 6:
            return None, None
    idx = np.where(ok)[0]
    lo = np.searchsorted(s, s[idx[0]] + 2.0); hi = np.searchsorted(s, s[idx[-1]] - 2.0)
    for _ in range(4):                      # at most 8x the noise smoothing; the radius left is reported, not hidden
        sp = UnivariateSpline(s[ok], x[ok], k=3, s=ss)
        if hi <= lo or edge_min_radius(guideP[lo:hi] + (sgn * sp(s[lo:hi]))[:, None] * L[lo:hi]) >= rmin:
            break
        ss *= 2
    return sp, ss


def measure_piece(name, P, mode="road"):
    for it in range(2 if mode == "road" else 1):
        T, L = naip.normals(P)
        s = naip.cumlen(P)
        offs, prof = profiles(P, L, score="grey" if mode == "ring" else "pave")   # the lot ring: grey asphalt against the tan paddock concrete
        out = {}
        for side, sgn in (("left", 1.0), ("right", -1.0)):
            raw, x, status = measure_side(P, L, side, offs, prof, weak=0.15 if mode == "ring" else 0.30)
            sp, ss = fit_edge(s, x, status, guideP=P, L=L, sgn=sgn)
            out[side] = dict(raw=raw, x=x, status=status, sp=sp, ss=ss)
        if out["left"]["sp"] is None and out["right"]["sp"] is None:
            raise SystemExit(f"{name}: too few edge points")
        if mode == "road" and (out["left"]["sp"] is None or out["right"]["sp"] is None):
            raise SystemExit(f"{name}: a road piece with one edge")
        if it == 0 and mode == "road":
            dl = out["left"]["sp"](s); dr = out["right"]["sp"](s)
            cov = np.ones(len(s), bool)
            for side in ("left", "right"):
                idx = np.where(out[side]["status"] == "seen")[0]
                cv = np.zeros(len(s), bool); cv[idx[0]:idx[-1] + 1] = True
                cov &= cv
            c = (dl - dr) / 2
            if cov.any():
                c = np.interp(s, s[cov], c[cov])
            c = np.clip(c, -3, 3)
            C = P + c[:, None] * L
            C = naip.resample(C, 0.25)
            sig = 1.5 / 0.25
            C = np.c_[ndimage.gaussian_filter1d(C[:, 0], sig, mode="nearest"), ndimage.gaussian_filter1d(C[:, 1], sig, mode="nearest")]
            P = naip.resample(C, STEP)
    return P, L, s, out, offs, prof


def wear(P, L, dl, dr):
    ch = naip.channels()
    n = len(P)
    rows = []
    prof_bins = []
    for k in range(n):
        a, b = -dr[k] + 0.5, dl[k] - 0.5          # right asphalt edge to left asphalt edge, 0.5 m in from each
        if b - a < 2.0:
            rows.append(None); prof_bins.append(None); continue
        o = np.arange(a, b + 1e-9, 0.1)
        E = P[k, 0] + o * L[k, 0]; N = P[k, 1] + o * L[k, 1]
        lum = naip.sample(ch["lum"], E, N)
        ref = np.percentile(lum, 80)
        dk = np.clip((ref - lum) / max(ref, 1), 0, None)
        dk = ndimage.gaussian_filter1d(dk, 1.5 / 0.1 / 2.355, mode="nearest")
        u = (o - o[0]) / max(o[-1] - o[0], 1e-6)
        i = int(np.argmax(dk))
        rows.append({"peak": float(dk[i]), "u": float(u[i]), "off": float(o[i])})
        bins = np.full(20, np.nan)
        for q in range(20):
            sel = (u >= q / 20) & (u < (q + 1) / 20 + (1e-9 if q == 19 else 0))
            if sel.any():
                bins[q] = dk[sel].mean()
        prof_bins.append(bins)
    return rows, prof_bins
