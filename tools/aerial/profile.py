"""Profiles across the road: the painted double-yellow centre line, the white edge lines and the pavement
edges, traced on cached NAIP windows (imagery frame, NAD83 / UTM 13N metres).

A profile is a line of samples every ``DS`` m along a normal to a reference polyline. Per sample:
NDVI = (NIR - R) / (NIR + R), brightness = mean(R, G, B), yellowness Y = (R + G) / 2 - B and chroma =
Y / brightness, each lightly smoothed (+-1 sample). The double-yellow line anchors each profile; the white
edge lines are found from it; the pavement edge is found by walking outward from the edge line until the
surface stops looking like THIS window's own asphalt.

Every threshold below is **[invented]** for the aerial pass (2026-10-11); none is a gate. They decide what
counts as paint or as an edge, and every overlay shows each traced point so a reader can disagree:

- ``DS = 0.15`` m: profile sample step (NAIP is 0.6 m native, served at 0.3 m) [invented].
- ``SHADOW_BRI = 45``: a sample darker than this mean RGB is shadow, class unknown [invented].
- ``Z_THR = 3.0``: the pavement edge is where the asphalt-model distance z first exceeds 3 [invented].
- ``EDGE_RUN_M = 0.45``: ...and stays above it for at least 0.45 m [invented].
- ``EDGE_MAX_OUT_M = 8.0``: the edge is searched at most 8 m beyond the start point [invented].
- yellow line (``find_yellow``): a Y peak with prominence >= ``YELLOW_PROM = 10`` over +-1.5 m, and asphalt
  on both sides 0.9-2.0 m out (median NDVI < -0.12, chroma < 0.24, brightness > SHADOW_BRI) [invented];
  scored as prominence - 2 x distance from the expected offset [invented].
- white edge lines (``find_fog``): a brightness ridge 2.0-5.2 m from the yellow line, prominence >=
  ``FOG_PROM = 7`` over +-1.2 m, chroma <= ``FOG_CHROMA = 0.22`` [invented]; scored prominence - distance.
- asphalt model (``Model``): robust median / MAD of (NDVI, chroma, brightness) sampled 0.9-2.2 m either side
  of the yellow line where brightness > SHADOW_BRI + 15, MAD floors (0.03, 0.03, 12), brightness weighted
  0.5 against 1 for the others, at least 50 samples [invented].
- edge appearance (``find_edge``): a dark band right outside the edge is samples darker than 0.6 x the
  asphalt brightness; "dark then bright" (a line standing at the edge, or its shadow) is a 0.25-1.5 m band
  followed by ground brighter than 0.75 x asphalt 2-3 m out; outside brighter than SHADOW_BRI and than
  0.55 x asphalt or the edge is "shadow" [invented].
- ``despike``: a value more than 0.6 m (configurable) from the median of its +-4 neighbours is dropped
  [invented].
- ``refine_from_yellow``: the reference is moved onto the median-filtered (+-3 m) yellow offsets, values
  more than 0.8 m off that median dropped, gaps interpolated, then smoothed over +-2 m [invented].
- ``robust_circle``: circle refits trimming points beyond max(0.3 m, 2.5 rms), at least 8 points
  [invented].
"""
from __future__ import annotations

import math
import statistics as stt

from . import geo

DS = 0.15
SHADOW_BRI = 45
Z_THR = 3.0
EDGE_RUN_M = 0.45
EDGE_MAX_OUT_M = 8.0
YELLOW_PROM = 10
FOG_PROM = 7
FOG_CHROMA = 0.22


# ---------------------------------------------------------------- polylines
class Poly:
    def __init__(self, pts):
        q = [pts[0]]
        for p in pts[1:]:
            if geo.dist(p, q[-1]) > 1e-6:
                q.append(p)
        self.p = q
        self.s = [0.0]
        for i in range(1, len(q)):
            self.s.append(self.s[-1] + geo.dist(q[i], q[i - 1]))
        self.L = self.s[-1]

    def _seg(self, s):
        lo, hi = 0, len(self.s) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.s[mid] <= s:
                lo = mid
            else:
                hi = mid
        return lo

    def pos(self, s):
        s = max(0.0, min(self.L, s))
        i = self._seg(s)
        j = min(i + 1, len(self.p) - 1)
        if self.s[j] == self.s[i]:
            return self.p[i]
        t = (s - self.s[i]) / (self.s[j] - self.s[i])
        a, b = self.p[i], self.p[j]
        return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))

    def tan(self, s, h=1.5):
        a = self.pos(s - h)
        b = self.pos(s + h)
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        return (dx / L, dy / L)

    def resample(self, step):
        n = max(2, int(self.L / step) + 1)
        return Poly([self.pos(self.L * k / (n - 1)) for k in range(n)])

    def smooth(self, half_m, iters=1):
        """Moving average of positions over +-half_m (on a 0.5 m resampled copy); ends held."""
        P = self.resample(0.5)
        pts = P.p
        h = max(1, int(half_m / 0.5))
        for _ in range(iters):
            out = []
            for i in range(len(pts)):
                a, b = max(0, i - h), min(len(pts) - 1, i + h)
                k = min(i - a, b - i)
                a, b = i - k, i + k
                xs = [pts[j][0] for j in range(a, b + 1)]
                ys = [pts[j][1] for j in range(a, b + 1)]
                out.append((sum(xs) / len(xs), sum(ys) / len(ys)))
            pts = out
        return Poly(pts)

    def heading(self, s, h=1.5):
        t = self.tan(s, h)
        return math.atan2(t[1], t[0])


def left_normal(t):
    return (-t[1], t[0])


def pt_at(rec, off):
    p, n = rec["p"], rec["n"]
    return (p[0] + n[0] * off, p[1] + n[1] * off)


def unwrap(angles):
    out = [angles[0]]
    for a in angles[1:]:
        d = a - out[-1]
        while d > math.pi:
            d -= 2 * math.pi
        while d < -math.pi:
            d += 2 * math.pi
        out.append(out[-1] + d)
    return out


# ---------------------------------------------------------------- profiles
def sample_profile(W, p, n, half=14.0, ds=DS):
    K = int(round(half / ds))
    offs, nd, br, Y, ch = [], [], [], [], []
    for k in range(-K, K + 1):
        o = k * ds
        s = W.sample(p[0] + n[0] * o, p[1] + n[1] * o)
        offs.append(o)
        if s is None:
            nd.append(None)
            br.append(None)
            Y.append(None)
            ch.append(None)
        else:
            r, g, b, nir = s
            bb = (r + g + b) / 3.0
            nd.append((nir - r) / (nir + r + 1e-6))
            br.append(bb)
            Y.append((r + g) / 2.0 - b)
            ch.append(((r + g) / 2.0 - b) / max(bb, 1.0))
    return {"o": offs, "nd": _ma(nd, 1), "br": _ma(br, 1), "Y": _ma(Y, 1), "ch": _ma(ch, 1),
            "nd_raw": nd, "br_raw": br}


def _ma(v, h):
    out = []
    for i in range(len(v)):
        w = [v[j] for j in range(max(0, i - h), min(len(v), i + h + 1)) if v[j] is not None]
        out.append(sum(w) / len(w) if (w and v[i] is not None) else None)
    return out


def _peak(o, v, i):
    if 0 < i < len(v) - 1 and v[i - 1] is not None and v[i + 1] is not None:
        den = v[i - 1] - 2 * v[i] + v[i + 1]
        d = 0.5 * (v[i - 1] - v[i + 1]) / den if den != 0 else 0.0
        return o[i] + max(-0.5, min(0.5, d)) * (o[1] - o[0])
    return o[i]


def _idx(o, off):
    ds = o[1] - o[0]
    return int(round((off - o[0]) / ds))


def find_yellow(pr, prefer=0.0, search=4.0):
    """The double-yellow centre line's offset on this profile (sub-sample peak), and its prominence."""
    o, Y, nd, ch, br = pr["o"], pr["Y"], pr["nd"], pr["ch"], pr["br"]
    n = len(o)
    best = None
    for i in range(1, n - 1):
        if abs(o[i] - prefer) > search or Y[i] is None or Y[i - 1] is None or Y[i + 1] is None:
            continue
        if not (Y[i] >= Y[i - 1] and Y[i] >= Y[i + 1]):
            continue
        w = _idx(o, o[i] + 1.5) - i
        lo = [Y[j] for j in range(max(0, i - w), min(n, i + w + 1)) if Y[j] is not None]
        prom = Y[i] - min(lo)
        if prom < YELLOW_PROM:
            continue
        ok = 0
        for sgn in (-1, 1):
            js = range(_idx(o, o[i] + sgn * 0.9), _idx(o, o[i] + sgn * 2.0) + sgn, sgn)
            vals = [(nd[j], ch[j], br[j]) for j in js if 0 <= j < n and nd[j] is not None]
            if vals and stt.median([v[0] for v in vals]) < -0.12 and stt.median([v[1] for v in vals]) < 0.24 \
                    and stt.median([v[2] for v in vals]) > SHADOW_BRI:
                ok += 1
        if ok < 2:
            continue
        score = prom - 2.0 * abs(o[i] - prefer)
        if best is None or score > best[0]:
            best = (score, i, prom)
    if best is None:
        return None, None
    return _peak(o, Y, best[1]), best[2]


def find_fog(pr, yel, sgn, rng=(2.0, 5.2)):
    """White edge line on side sgn: a brightness ridge, low chroma, rng metres from the yellow line."""
    o, br, ch = pr["o"], pr["br"], pr["ch"]
    n = len(o)
    best = None
    for i in range(1, n - 1):
        d = (o[i] - yel) * sgn
        if d < rng[0] or d > rng[1] or br[i] is None or br[i - 1] is None or br[i + 1] is None:
            continue
        if not (br[i] >= br[i - 1] and br[i] >= br[i + 1]):
            continue
        w = _idx(o, o[i] + 1.2) - i
        neigh = [br[j] for j in range(max(0, i - w), min(n, i + w + 1)) if br[j] is not None]
        prom = br[i] - min(neigh)
        if prom < FOG_PROM or ch[i] is None or ch[i] > FOG_CHROMA:
            continue
        score = prom - 1.0 * d
        if best is None or score > best[0]:
            best = (score, i, prom)
    if best is None:
        return None, None
    return _peak(o, br, best[1]), best[2]


class Model:
    """Per-window asphalt appearance: robust centre/scale of (ndvi, chroma, brightness)."""

    W = (1.0, 1.0, 0.5)   # brightness down-weighted (sun/shade, paint)

    def __init__(self, samples):
        self.c, self.s = [], []
        floors = (0.03, 0.03, 12.0)
        for k in range(3):
            v = sorted(x[k] for x in samples)
            med = stt.median(v)
            mad = stt.median([abs(x - med) for x in v]) * 1.4826
            self.c.append(med)
            self.s.append(max(mad, floors[k]))
        self.n = len(samples)

    def z(self, nd, ch, br):
        t = [(nd - self.c[0]) / self.s[0], (ch - self.c[1]) / self.s[1], (br - self.c[2]) / self.s[2]]
        w = self.W
        return math.sqrt(sum((w[k] * t[k]) ** 2 for k in range(3)) / sum(x * x for x in w))

    def as_dict(self):
        return {"ndvi": [round(self.c[0], 3), round(self.s[0], 3)], "chroma": [round(self.c[1], 3), round(self.s[1], 3)],
                "bri": [round(self.c[2], 1), round(self.s[2], 1)], "n": self.n}


def lane_samples(pr, yel):
    o = pr["o"]
    out = []
    for sgn in (-1, 1):
        for j in range(_idx(o, yel + sgn * 0.9), _idx(o, yel + sgn * 2.2) + sgn, sgn):
            if 0 <= j < len(o) and pr["nd"][j] is not None and pr["br"][j] > SHADOW_BRI + 15:
                out.append((pr["nd"][j], pr["ch"][j], pr["br"][j]))
    return out


def find_edge(pr, model, start, sgn, max_out=EDGE_MAX_OUT_M, run_m=EDGE_RUN_M):
    """Walk outward from offset ``start`` on side sgn; the pavement edge is the z = Z_THR crossing before
    the first sustained (>= run_m) exceedance. Returns (offset, quality, outside appearance)."""
    o, nd, ch, br = pr["o"], pr["nd"], pr["ch"], pr["br"]
    n = len(o)
    ds = o[1] - o[0]
    i0 = _idx(o, start)
    need = max(1, int(round(run_m / ds)))
    zs = {}

    def z(j):
        if j not in zs:
            zs[j] = None if (j < 0 or j >= n or nd[j] is None) else model.z(nd[j], ch[j], br[j])
        return zs[j]
    j = i0
    cnt = 0
    first = None
    lim = _idx(o, start + sgn * max_out)
    found = False
    while (j - lim) * sgn <= 0:
        zj = z(j)
        if zj is None:
            return None, "profile_end", None
        if zj > Z_THR:
            cnt += 1
            if first is None:
                first = j
            if cnt >= need:
                found = True
                break
        else:
            cnt = 0
            first = None
        j += sgn
    if not found:
        return None, "open", None
    a, b = first - sgn, first
    za, zb = z(a), z(b)
    if za is None or zb is None or zb == za:
        e = o[b]
    else:
        e = o[a] + (Z_THR - za) / (zb - za) * (o[b] - o[a])
    outs = [k for k in range(_idx(o, e + sgn * 0.3), _idx(o, e + sgn * 2.5), sgn) if 0 <= k < n and br[k] is not None]
    bout = stt.median([br[k] for k in outs]) if outs else None
    ndout = stt.median([nd[k] for k in outs]) if outs else None
    chout = stt.median([ch[k] for k in outs]) if outs else None
    dark_lim = 0.6 * model.c[2]
    band = [k for k in range(_idx(o, e), _idx(o, e + sgn * 2.0), sgn) if 0 <= k < n and br[k] is not None]
    dk = [k for k in band if br[k] < dark_lim]
    dark_w = len(dk) * ds
    after = [br[k] for k in range(_idx(o, e + sgn * 2.0), _idx(o, e + sgn * 3.0), sgn) if 0 <= k < n and br[k] is not None]
    recover = bool(after) and stt.median(after) > 0.75 * model.c[2]
    q = "ok"
    if bout is None or bout < SHADOW_BRI or bout < 0.55 * model.c[2]:
        q = "shadow"
    return e, q, {"bri": bout, "ndvi": ndout, "chroma": chout, "dark_band_m": round(dark_w, 2),
                  "dark_then_bright": bool(0.25 <= dark_w <= 1.5 and recover)}


def analyze2(pr, model, prefer=0.0, search=4.0):
    res = {}
    yel, prom = find_yellow(pr, prefer, search)
    if yel is None:
        return None
    res["yellow"] = yel
    res["yellow_prom"] = round(prom, 1)
    for side, sgn in (("lo", -1), ("hi", 1)):
        f, fp = find_fog(pr, yel, sgn)
        if f is not None:
            res["fog_" + side] = f
            res["fog_prom_" + side] = round(fp, 1)
        if model is None:
            continue
        start = (f + sgn * 0.45) if f is not None else (yel + sgn * 2.2)
        e, q, outside = find_edge(pr, model, start, sgn)
        res["e_" + side] = e
        res["q_" + side] = q
        res["out_" + side] = outside
    return res


def trace2(W, ref, s0, s1, model=None, step=0.5, half=14.0, search=4.0, keep_pr=True):
    """Profiles every ``step`` m along ``ref`` from s0 to s1 (left normal: lo = right of travel)."""
    out = []
    s = max(0.0, s0)
    while s <= min(ref.L, s1) + 1e-9:
        p = ref.pos(s)
        t = ref.tan(s)
        n = left_normal(t)
        pr = sample_profile(W, p, n, half)
        r = analyze2(pr, model, 0.0, search)
        out.append({"s": s, "p": p, "n": n, "t": t, "r": r, "pr": pr if keep_pr else None})
        s += step
    return out


def build_model(recs):
    smp = []
    for r in recs:
        if r["r"] and r["r"].get("yellow") is not None and r.get("pr"):
            smp.extend(lane_samples(r["pr"], r["r"]["yellow"]))
    return Model(smp) if len(smp) > 50 else None


def despike(recs, key, half=4, tol=0.6):
    """Null out r[key] values deviating > tol m from the running median of their neighbours."""
    vals = [(r["r"] or {}).get(key) for r in recs]
    for i, v in enumerate(vals):
        if v is None:
            continue
        nb = [vals[j] for j in range(max(0, i - half), min(len(vals), i + half + 1)) if j != i and vals[j] is not None]
        if len(nb) >= 3 and abs(v - stt.median(nb)) > tol:
            recs[i]["r"][key + "_spike"] = v
            recs[i]["r"][key] = None
            if key.startswith("e_"):
                recs[i]["r"]["q_" + key[2:]] = "spike"


def refine_from_yellow(ref, recs, half_m=3.0, tol=0.8):
    """Shift ref laterally onto the (median-filtered) yellow line; interpolate gaps; smooth lightly."""
    cs = [(r["r"] or {}).get("yellow") for r in recs]
    h = max(1, int(half_m / 0.5))
    med = []
    for i in range(len(cs)):
        w = [cs[j] for j in range(max(0, i - h), min(len(cs), i + h + 1)) if cs[j] is not None]
        m = stt.median(w) if len(w) >= 3 else None
        if m is not None and cs[i] is not None and abs(cs[i] - m) > tol:
            m = None if len(w) < 5 else m
        med.append(m)
    known = [i for i, v in enumerate(med) if v is not None]
    if not known:
        return ref, 0
    full = []
    for i in range(len(med)):
        if med[i] is not None:
            full.append(med[i])
            continue
        lo = max([k for k in known if k < i], default=None)
        hi = min([k for k in known if k > i], default=None)
        if lo is None:
            full.append(med[hi])
        elif hi is None:
            full.append(med[lo])
        else:
            t = (i - lo) / (hi - lo)
            full.append(med[lo] + t * (med[hi] - med[lo]))
    pts = [pt_at(r, c) for r, c in zip(recs, full)]
    return Poly(pts).smooth(2.0), len(known)
