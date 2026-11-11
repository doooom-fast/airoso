"""Road wear where tyres run, and the road's large-scale tone from the aerial (ledger 0084).

Kevin, 2026-11-07: "road textures to include wear along where tires run, in a realistic manner" / "sampling the entire
road's texture from aerial data and mapping it directly onto the entire road instead of a repeating pattern" / "For tracks
we'll use racing lines" / "Which will help darken curbs realistically".

THE TWO SCALES. engine-july's prep gives every 1ROAD face u = x / 4, v = y / 4 (``planar_uv``, UV_TILE = 4.0): one
cracked-asphalt picture on a 4 m world grid. This module keeps that picture, at that same 4 m and the same phase, as the
DETAIL layer (txDetail / txNormalDetail of ``ksPerPixelMultiMap_NMDetail``), and adds a MACRO layer under it, one texel
per ``texel_m`` of real ground, that follows the road because it is baked from the road's own world position:

    macro(x, y) = m0 * tone(x, y) * (1 - wear(x, y))         shipped as txDiffuse (RGBA, alpha 0 = full detail)
    detail'     = detail / m0                                 the stock asphalt, pre-brightened so macro x detail' at
                                                              the median road texel is today's look exactly

``tone`` is the aerial's luminance over the road's lit-asphalt median (shadows and paint read off the photo itself and
filled from the lit asphalt round them), ``wear`` the rubber where tyres run. ``m0`` is the headroom an 8-bit texture
needs to carry the lighter patches (measured: the tone's p99.5 maps to 1.0).

THE ATLAS (why not a strip atlas). The road is cut into square world cells; each used cell gets a tile of the atlas
holding the cell plus a margin, baked from the world itself, so a face's UVs are its vertices' world positions shifted
into its cell's tile. Every face takes the cell of its centroid; the margin covers the furthest vertex of any face
(measured on the built mesh, rounded up to the detail tile). A kn5 vertex carries one UV, and the faces are flat-shaded
already (3 vertices per triangle on Milford's 1ROAD), so the cell seams cost no vertex. Because the cell size, the margin
and the tile pitch are all whole detail tiles, ``detailUVMultiplier`` puts the detail on exactly today's 4 m grid with
today's phase across every seam, and junctions, pads and aprons come out right with no centreline to project onto.

WHERE TYRES RUN. A racing line per layout: a recorded ``fast_lane.ai`` when the layout has one (no ``ai_draft.json``
beside it), otherwise a minimum-curvature line inside the BUILT road's edges [model]. Each line paints two tyre tracks
(``track_m`` apart), each a Gaussian of the line's spread (``spread_m``), weighted along the lap by the tyre force a
friction-limited speed model puts through them (corners and braking lay rubber; straights a base share). Kerbs: every
surface listed in ``surfaces`` shares the atlas, so the edge strip the line clips at an apex darkens with it.

Pure numpy (Blender 4.2 bundles it); no scipy, no PIL. ``write_png`` is a minimal encoder so an RGBA texel with alpha 0
keeps its colour (Blender's image saver may premultiply).
"""
from __future__ import annotations

import math
import struct
import zlib

import numpy as np

# --- the spec ---------------------------------------------------------------------------------------------------------
# Every default below is marked: [measured] where a measurement set it, [model] for the physics model of the line,
# [invented] where nothing measured it yet (fleet/GATES-CHANGELOG.md 2026-11-09, ledger 0084).
DEFAULTS = {
    "surfaces": ["1ROAD"],          # mesh prefixes that take the macro atlas (upper-case match)
    "texel_m": 0.25,                # [measured] half the aerial's 0.50 m E-W GSD: the finest tone it carries (Nyquist)
    "detail_tile_m": 4.0,           # engine-july's UV_TILE: the detail keeps today's scale and phase
    "max_atlas_px": 8192,           # L7: power of two; 8192 the per-file ceiling (SATELLITE-ROAD-TEXTURES §4.1)
    "layer_m": 10.0,                # [invented] faces more than this apart in height never share a tile (L4)
    "tone": {
        "shadow_lum": 0.72,         # [measured, Milford NAIP 2022] a shadow texel: under this share of the lit median (the road's
                                    # dark tail sits under 0.6, its lit body 0.97-1.07; 7.5 % of the road)...
        "shadow_blue": 1.06,        # [measured] ...and bluer than this b/r (dark tail median 1.43, lit asphalt 0.93)
        "paint_lum": 1.45,          # [invented] brighter than this share of the median: paint or a paint ghost (Milford: none; p99 1.14)
        "fill_m": 3.0,              # [invented] the lit-asphalt neighbourhood a shadow / paint texel is filled from
        "clip": [0.70, 1.30],       # [invented] the tone ratio kept (outliers are cars, cones, debris)
        "headroom_pct": 99.5,       # [invented] the tone percentile that maps to 1.0 (m0)
    },
    "wear": {
        "amplitude": 0.22,          # [invented] the rubber's darkening at the line's peak. The aerial cannot set it: on Milford's
                                    # NAIP 2022 the model line's tyre band regresses to 0.3 % darker (the centreline 0.7 %),
                                    # so what NAIP sees at 0.5 m is <= ~1 %. Kevin's drive picks it (ledger 0084)
        "track_m": 1.60,            # [measured] a car's track width (front/rear 1.5-1.7 m on the cars AC ships)
        "spread_m": 0.70,           # [invented] the line's lateral scatter, car to car and lap to lap (1 sigma). 0.55 (0.1.7's
                                    # first build) left two tyre stripes with a lighter middle, a lane's look; 0.70 merges
                                    # them into one band ~3 m wide, a circuit's
        "base": 0.35,               # [invented] the share of peak rubber a straight carries
        "smooth_m": 12.0,           # [invented] rubber builds over a stretch, not a point (1 sigma along the lap)
        "margin_m": 0.95,           # [measured] half a 1.9 m car: the line's centre this far inside the road edge
        "lat_g": 1.2, "brake_g": 1.1, "accel_g": 0.45, "v_top_ms": 70.0,   # [model] the speed profile's car
        "edge_reach_m": 1.0,        # [invented] an edge scan reads at most this past the declared half width (junction mouths)
    },
    "lines": [],                    # [{"layout": id, "ai": "ai/<id>/fast_lane.ai", "reverse": false}] (empty: every layout)
    # "kerbs" (opt-in, no default here so a spec without it is unchanged): {"prefix", "levels"}, the race kerbs darkened
    # where the line rides them (KERB_DEFAULTS below; High Plains 0.1.7)
}


def spec_from_config(cfg: dict) -> dict | None:
    """The merged road_wear spec, or None when the config names no ``road_wear`` key (Lake Murray: nothing changes)."""
    rw = cfg.get("road_wear")
    if not rw or not rw.get("enabled", True):
        return None
    out = {k: (dict(v) if isinstance(v, dict) else (list(v) if isinstance(v, list) else v)) for k, v in DEFAULTS.items()}
    for k, v in rw.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update({kk: vv for kk, vv in v.items() if not kk.startswith("_")})
        else:
            out[k] = v
    out["surfaces"] = [str(s).upper() for s in out["surfaces"]]
    return out


def meters_per_degree(lat0: float) -> tuple[float, float]:
    """(m per deg lon, m per deg lat): the WGS84 series of scripts/geometry/projection._meters_per_degree, the one the
    engine projected every centreline with (copied so Blender imports nothing from scripts.config)."""
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    return m_lon, m_lat


# --- the aerial -------------------------------------------------------------------------------------------------------
class Aerial:
    """A north-up lon/lat image (rows top = north) sampled at local (x = E, y = N) metres about the track origin."""

    def __init__(self, rgb: np.ndarray, bbox_lonlat, origin_lonlat):
        self.rgb = np.asarray(rgb, dtype=np.float32)
        if self.rgb.max() > 1.5:
            self.rgb = self.rgb / 255.0
        self.h, self.w = self.rgb.shape[:2]
        self.W, self.S, self.E, self.N = (float(v) for v in bbox_lonlat)
        self.lon0, self.lat0 = float(origin_lonlat[0]), float(origin_lonlat[1])
        self.m_lon, self.m_lat = meters_per_degree(self.lat0)
        self.px_m = ((self.E - self.W) * self.m_lon / self.w, (self.N - self.S) * self.m_lat / self.h)
        self.dx = self.dy = 0.0            # the measured registration (``register``): world p reads the photo at p + d

    def pixel(self, x, y):
        lon = self.lon0 + (np.asarray(x, dtype=np.float64) + self.dx) / self.m_lon
        lat = self.lat0 + (np.asarray(y, dtype=np.float64) + self.dy) / self.m_lat
        return (lon - self.W) / (self.E - self.W) * self.w - 0.5, (self.N - lat) / (self.N - self.S) * self.h - 0.5

    def sample(self, x, y) -> np.ndarray:
        """Bilinear RGB 0..1 at pixel centres; NaN outside the image."""
        u, v = self.pixel(x, y)
        shape = np.shape(u)
        u = np.ravel(u); v = np.ravel(v)
        ok = (u >= 0) & (v >= 0) & (u <= self.w - 1) & (v <= self.h - 1)
        out = np.full((u.size, 3), np.nan, dtype=np.float32)
        if ok.any():
            uu, vv = u[ok], v[ok]
            i0 = np.clip(np.floor(uu).astype(np.int64), 0, self.w - 2)
            j0 = np.clip(np.floor(vv).astype(np.int64), 0, self.h - 2)
            fu = (uu - i0)[:, None].astype(np.float32); fv = (vv - j0)[:, None].astype(np.float32)
            a = self.rgb[j0, i0]; b = self.rgb[j0, i0 + 1]; c = self.rgb[j0 + 1, i0]; d = self.rgb[j0 + 1, i0 + 1]
            out[ok] = (a * (1 - fu) + b * fu) * (1 - fv) + (c * (1 - fu) + d * fu) * fv
        return out.reshape(shape + (3,))


def luminance(rgb: np.ndarray) -> np.ndarray:
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


# --- a world grid (texel-aligned) -------------------------------------------------------------------------------------
class Grid:
    """Square cells of ``res`` metres; cell (i, j) covers x0 + i*res .. +res (east), y0 + j*res .. +res (north)."""

    def __init__(self, x0: float, y0: float, nx: int, ny: int, res: float):
        self.x0, self.y0, self.nx, self.ny, self.res = float(x0), float(y0), int(nx), int(ny), float(res)

    @classmethod
    def around(cls, xmin, ymin, xmax, ymax, res, align, pad):
        x0 = math.floor((xmin - pad) / align) * align
        y0 = math.floor((ymin - pad) / align) * align
        nx = int(math.ceil((xmax + pad - x0) / res)); ny = int(math.ceil((ymax + pad - y0) / res))
        return cls(x0, y0, nx, ny, res)

    def centres(self, i0, j0, ni, nj):
        xs = self.x0 + (np.arange(i0, i0 + ni) + 0.5) * self.res
        ys = self.y0 + (np.arange(j0, j0 + nj) + 0.5) * self.res
        return np.meshgrid(xs, ys)            # [j, i]

    def index(self, x, y):
        return (np.floor((np.asarray(x) - self.x0) / self.res).astype(np.int64),
                np.floor((np.asarray(y) - self.y0) / self.res).astype(np.int64))


def rasterize(grid: Grid, tris: np.ndarray) -> np.ndarray:
    """bool [ny, nx]: the cells whose centre lies in any of ``tris`` (T x 3 x 2, world x / y)."""
    mask = np.zeros((grid.ny, grid.nx), dtype=bool)
    r = grid.res
    for t in np.asarray(tris, dtype=np.float64):
        lo = t.min(axis=0); hi = t.max(axis=0)
        i0 = max(0, int(math.floor((lo[0] - grid.x0) / r - 0.5))); i1 = min(grid.nx - 1, int(math.ceil((hi[0] - grid.x0) / r - 0.5)))
        j0 = max(0, int(math.floor((lo[1] - grid.y0) / r - 0.5))); j1 = min(grid.ny - 1, int(math.ceil((hi[1] - grid.y0) / r - 0.5)))
        if i1 < i0 or j1 < j0:
            continue
        X, Y = grid.centres(i0, j0, i1 - i0 + 1, j1 - j0 + 1)
        (ax, ay), (bx, by), (cx, cy) = t
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-12:
            continue
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / d
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / d
        inside = (l1 >= -1e-9) & (l2 >= -1e-9) & (l1 + l2 <= 1 + 1e-9)
        mask[j0:j1 + 1, i0:i1 + 1] |= inside
    return mask


def box_mean(a: np.ndarray, w: np.ndarray, r: int) -> np.ndarray:
    """Normalised box filter (half width r cells): sum(a*w) / sum(w) over the window; NaN where no weight."""
    def box(z):
        c = np.cumsum(np.cumsum(np.pad(z, ((r + 1, r), (r + 1, r))), axis=0), axis=1)
        return c[2 * r + 1:, 2 * r + 1:] - c[:-2 * r - 1, 2 * r + 1:] - c[2 * r + 1:, :-2 * r - 1] + c[:-2 * r - 1, :-2 * r - 1]
    a = np.nan_to_num(a.astype(np.float64)); w = w.astype(np.float64)
    num = box(a * w); den = box(w)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 1e-9, num / den, np.nan)


def register(aerial: "Aerial", grid: Grid, road: np.ndarray, reach_m: float = 3.0, step_m: float = 0.25,
             ring_m: float = 3.0) -> dict:
    """The aerial's offset from the BUILT road, measured: the (dx, dy) shift of the aerial (within +-reach_m) at which the
    built road reads darkest against a ring_m band of ground round it — the asphalt edge lined up with the photo's.
    Returns {"dx_m", "dy_m", "contrast_at_0", "contrast_best"} (contrast = ring mean - road mean luminance; the Milford
    NAIP's asphalt reads LIGHTER than its grass, so the best shift is the most negative contrast in magnitude)."""
    r = max(1, int(round(ring_m / grid.res)))
    near = box_mean(road.astype(np.float64), np.ones(road.shape), r) > 0
    ring = near & ~road
    jr, ir = np.nonzero(road); jg, ig = np.nonzero(ring)
    rx = grid.x0 + (ir + 0.5) * grid.res; ry = grid.y0 + (jr + 0.5) * grid.res
    gx = grid.x0 + (ig + 0.5) * grid.res; gy = grid.y0 + (jg + 0.5) * grid.res
    d0 = (aerial.dx, aerial.dy)
    aerial.dx = aerial.dy = 0.0

    def contrast(dx, dy):
        return float(np.nanmean(luminance(aerial.sample(gx + dx, gy + dy))) -
                     np.nanmean(luminance(aerial.sample(rx + dx, ry + dy))))
    c0 = contrast(0.0, 0.0)
    sign = 1.0 if c0 >= 0 else -1.0
    best = (abs(c0), 0.0, 0.0)
    # coarse 1 m, then fine step_m round the best
    for dx in np.arange(-reach_m, reach_m + 1e-9, 1.0):
        for dy in np.arange(-reach_m, reach_m + 1e-9, 1.0):
            c = sign * contrast(dx, dy)
            if c > best[0]:
                best = (c, float(dx), float(dy))
    bx, by = best[1], best[2]
    for dx in np.arange(bx - 1.0, bx + 1.0 + 1e-9, step_m):
        for dy in np.arange(by - 1.0, by + 1.0 + 1e-9, step_m):
            c = sign * contrast(dx, dy)
            if c > best[0]:
                best = (c, float(dx), float(dy))
    aerial.dx, aerial.dy = d0
    return {"dx_m": round(best[1], 3), "dy_m": round(best[2], 3), "contrast_at_0": round(c0, 4),
            "contrast_best": round(sign * best[0], 4)}


# --- the tone off the aerial ------------------------------------------------------------------------------------------
def tone_field(aerial: Aerial, grid: Grid, road: np.ndarray, spec_tone: dict, return_lit: bool = False):
    """float32 [ny, nx]: the aerial's luminance over the lit-asphalt median, on the grid; shadow and paint texels filled
    from the lit asphalt within fill_m, everything off the road filled outward from the road (the edge strip, the
    margins). Returns (tone, stats)."""
    X, Y = grid.centres(0, 0, grid.nx, grid.ny)
    rgb = aerial.sample(X, Y)
    lum = luminance(rgb)
    valid = road & np.isfinite(lum)
    ref = float(np.median(lum[valid]))
    br = rgb[..., 2] / np.maximum(rgb[..., 0], 1e-3)
    shadow = valid & (lum < spec_tone["shadow_lum"] * ref) & (br > spec_tone["shadow_blue"])
    paint = valid & (lum > spec_tone["paint_lum"] * ref)
    # a shadow's or a line's edge is a mixed pixel that meets neither rule: both masks grow by one aerial pixel
    rp = max(1, int(math.ceil(max(aerial.px_m) / grid.res)))
    shadow = valid & (box_mean(shadow.astype(np.float64), np.ones(shadow.shape), rp) > 0)
    paint = valid & (box_mean(paint.astype(np.float64), np.ones(paint.shape), rp) > 0)
    lit = valid & ~shadow & ~paint
    ref = float(np.median(lum[lit]))                     # the lit-asphalt median
    t = lum / ref
    lo, hi = spec_tone["clip"]
    t = np.clip(t, lo, hi)
    r = max(1, int(round(spec_tone["fill_m"] / grid.res)))
    fill = box_mean(t, lit, r)
    out = np.where(lit, t, fill)
    # outward from the road (edge strips, margins), widening until every cell has a value
    have = np.isfinite(out) & road
    out = np.where(have, out, np.nan)
    k = r
    for _ in range(12):
        if np.isfinite(out).all():
            break
        k *= 2
        f = box_mean(out, np.isfinite(out), k)
        out = np.where(np.isfinite(out), out, f)
    out = np.where(np.isfinite(out), out, 1.0).astype(np.float32)
    stats = {"lit_median_lum": round(ref, 4), "road_cells": int(valid.sum()),
             "shadow_pct": round(100.0 * shadow.sum() / max(1, valid.sum()), 2),
             "paint_pct": round(100.0 * paint.sum() / max(1, valid.sum()), 2),
             "tone_p01_p50_p99": [round(float(v), 4) for v in np.percentile(out[road], [1, 50, 99])],
             "aerial_px_m": [round(aerial.px_m[0], 3), round(aerial.px_m[1], 3)]}
    if return_lit:
        return out, stats, lit
    return out, stats


# --- the racing line --------------------------------------------------------------------------------------------------
def closed_polyline(pts: np.ndarray) -> np.ndarray:
    """Drop the repeated first vertex of a closed lap (L13)."""
    pts = np.asarray(pts, dtype=np.float64)
    if len(pts) > 2 and np.linalg.norm(pts[0, :2] - pts[-1, :2]) < 1e-6:
        pts = pts[:-1]
    return pts


def resample(pts: np.ndarray, ds: float, closed: bool = True, extra: np.ndarray | None = None):
    """Uniform arc-length resample of an N x D polyline (closed: the wrap segment included). ``extra`` (N x K) is
    resampled with it."""
    P = np.asarray(pts, dtype=np.float64)
    if closed:
        P = np.vstack([P, P[:1]])
        if extra is not None:
            extra = np.vstack([extra, extra[:1]])
    seg = np.linalg.norm(np.diff(P[:, :2], axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    L = s[-1]
    n = max(4, int(round(L / ds)))
    sn = np.linspace(0.0, L, n, endpoint=not closed)
    out = np.stack([np.interp(sn, s, P[:, k]) for k in range(P.shape[1])], axis=1)
    ex = None if extra is None else np.stack([np.interp(sn, s, extra[:, k]) for k in range(extra.shape[1])], axis=1)
    return out, ex, L


def left_normals(P: np.ndarray, closed: bool = True) -> np.ndarray:
    if closed:
        d = np.roll(P[:, :2], -1, axis=0) - np.roll(P[:, :2], 1, axis=0)
    else:
        d = np.gradient(P[:, :2], axis=0)
    d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-12)
    return np.stack([-d[:, 1], d[:, 0]], axis=1)


def scan_edges(C: np.ndarray, n: np.ndarray, road: np.ndarray, grid: Grid, cap_l: np.ndarray, cap_r: np.ndarray,
               step: float = 0.1) -> tuple[np.ndarray, np.ndarray]:
    """The built road's lateral extent at each station: the first uncovered sample left (+n) and right (-n) of the
    centre, read on the rasterised road, at most cap_l / cap_r out (a junction mouth or an apron never widens the line's
    corridor past the declared half width + edge_reach_m)."""
    reach = float(max(cap_l.max(), cap_r.max())) + step
    t = np.arange(0.0, reach, step)
    out = []
    for sign, cap in ((1.0, cap_l), (-1.0, cap_r)):
        X = C[:, None, 0] + sign * n[:, None, 0] * t[None, :]
        Y = C[:, None, 1] + sign * n[:, None, 1] * t[None, :]
        i, j = grid.index(X, Y)
        ok = (i >= 0) & (j >= 0) & (i < grid.nx) & (j < grid.ny)
        cov = np.zeros_like(ok)
        cov[ok] = road[j[ok], i[ok]]
        cov[:, 0] = True
        first_gap = np.argmax(~cov, axis=1)
        first_gap[cov.all(axis=1)] = len(t) - 1
        out.append(np.minimum(t[first_gap], cap))
    return out[0], out[1]


def _lap2(z: np.ndarray, closed: bool) -> np.ndarray:
    if closed:
        return np.roll(z, 1, axis=0) - 2 * z + np.roll(z, -1, axis=0)
    o = np.zeros_like(z)
    o[1:-1] = z[:-2] - 2 * z[1:-1] + z[2:]
    return o


def min_curvature(C: np.ndarray, n: np.ndarray, lo: np.ndarray, hi: np.ndarray, closed: bool = True,
                  iters: int = 100000, tol: float = 1e-7) -> np.ndarray:
    """Lateral offsets a (along the left normal n) in [lo, hi] minimising sum |P[i-1] - 2 P[i] + P[i+1]|^2, P = C + a n:
    the minimum-curvature line [model] (projected FISTA; step 1/32 = 1/Lipschitz of the second-difference squared)."""
    C = np.asarray(C[:, :2], dtype=np.float64); n = np.asarray(n, dtype=np.float64)
    a = np.clip(np.zeros(len(C)), lo, hi); y = a.copy(); t = 1.0
    step = 1.0 / 32.0
    for k in range(iters):
        P = C + y[:, None] * n
        g = 2.0 * np.sum(n * _lap2(_lap2(P, closed), closed), axis=1)
        a_new = np.clip(y - step * g, lo, hi)
        t_new = 0.5 * (1.0 + math.sqrt(1.0 + 4.0 * t * t))
        y = a_new + ((t - 1.0) / t_new) * (a_new - a)
        if k % 500 == 0 and k and np.max(np.abs(a_new - a)) < tol:
            a = a_new
            break
        a, t = a_new, t_new
    return a


def curvature(P: np.ndarray, closed: bool = True, span: int = 3) -> np.ndarray:
    """Signed curvature from the circle through P[i-span], P[i], P[i+span]."""
    A = np.roll(P[:, :2], span, axis=0); B = P[:, :2]; Cc = np.roll(P[:, :2], -span, axis=0)
    ab = B - A; bc = Cc - B; ca = A - Cc
    cross = ab[:, 0] * bc[:, 1] - ab[:, 1] * bc[:, 0]
    den = np.linalg.norm(ab, axis=1) * np.linalg.norm(bc, axis=1) * np.linalg.norm(ca, axis=1)
    k = 2.0 * cross / np.maximum(den, 1e-9)
    if not closed:
        k[:span] = k[span]; k[-span:] = k[-span - 1]
    return k


def speed_profile(P: np.ndarray, ds: float, w: dict, closed: bool = True):
    """[model] friction-limited speed round the line: v <= sqrt(lat_g g / |k|), accelerate at accel_g, brake at brake_g
    (two passes each way on a lap). Returns (v, a_lat, a_long) in m/s and m/s^2."""
    g = 9.81
    k = np.abs(curvature(P, closed))
    vmax = np.minimum(w["v_top_ms"], np.sqrt(w["lat_g"] * g / np.maximum(k, 1e-6)))
    v = vmax.copy()
    n = len(v)
    for _ in range(2 if closed else 1):
        for i in range(n):
            j = i - 1 if (closed or i) else None
            if j is not None:
                v[i] = min(v[i], math.sqrt(v[j] ** 2 + 2 * w["accel_g"] * g * ds))
        for i in range(n - 1, -1, -1):
            j = (i + 1) % n if closed else (i + 1 if i + 1 < n else None)
            if j is not None:
                v[i] = min(v[i], math.sqrt(v[j] ** 2 + 2 * w["brake_g"] * g * ds))
    a_lat = v * v * k
    dv = (np.roll(v, -1) - np.roll(v, 1)) if closed else np.gradient(v) * 2
    a_long = v * dv / (2 * ds)
    return v, a_lat, a_long


def gauss_smooth(z: np.ndarray, sigma_pts: float, closed: bool = True) -> np.ndarray:
    if sigma_pts <= 0:
        return z
    r = int(math.ceil(3 * sigma_pts))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_pts) ** 2); k /= k.sum()
    if closed:
        zz = np.concatenate([z[-r:], z, z[:r]])
    else:
        zz = np.concatenate([np.full(r, z[0]), z, np.full(r, z[-1])])
    return np.convolve(zz, k, mode="valid")


def rubber_intensity(P: np.ndarray, ds: float, w: dict, closed: bool = True) -> tuple[np.ndarray, dict]:
    """0..1 per station: base + (1 - base) * (tyre force / peak), smoothed along the lap."""
    v, a_lat, a_long = speed_profile(P, ds, w, closed)
    f = np.sqrt(a_lat ** 2 + a_long ** 2) / (w["lat_g"] * 9.81)
    f = gauss_smooth(np.clip(f, 0, 1), w["smooth_m"] / ds, closed)
    f = f / max(1e-9, f.max())
    I = w["base"] + (1.0 - w["base"]) * f
    lap_s = float(np.sum(ds / np.maximum(v, 0.5)))
    return I, {"lap_s_model": round(lap_s, 1), "v_min_kmh": round(float(v.min()) * 3.6, 1),
               "v_max_kmh": round(float(v.max()) * 3.6, 1)}


def tyre_profile(u: np.ndarray, track_m: float, spread_m: float) -> np.ndarray:
    """Two tyre tracks at +-track/2, each a Gaussian of the line's spread; 1.0 at the peak."""
    h = 0.5 * track_m; s2 = 2 * spread_m * spread_m
    f = np.exp(-((u - h) ** 2) / s2) + np.exp(-((u + h) ** 2) / s2)
    peak = 1.0 + math.exp(-((2 * h) ** 2) / s2)
    if spread_m > h:                                  # the two merge into one band peaked at the middle
        peak = max(peak, 2 * math.exp(-(h * h) / s2))
    return f / peak


def wear_at(X: np.ndarray, Y: np.ndarray, Z: float | None, line: dict, w: dict, reach: float) -> np.ndarray:
    """Rubber darkening 0..amplitude at world points (X, Y) (same shape) from one line {P (N x 3: x, y, height), I}:
    nearest line segment within reach; a segment more than layer_m off the cell's height band is never near (L4)."""
    P = line["P"]; I = line["I"]
    pts = np.stack([X.ravel(), Y.ravel()], axis=1)
    cx, cy = pts.mean(axis=0)
    half = float(np.max(np.abs(pts - [cx, cy]))) * 1.4143 + reach
    A = P[:, :2]; B = np.roll(P[:, :2], -1, axis=0) if line["closed"] else P[1:, :2]
    if not line["closed"]:
        A = A[:-1]
    IA = I[:len(A)]; IB = (np.roll(I, -1) if line["closed"] else I[1:])[:len(A)]
    near = (np.abs(A[:, 0] - cx) < half) & (np.abs(A[:, 1] - cy) < half)
    if Z is not None and P.shape[1] > 2:
        near &= np.abs(P[:len(A), 2] - Z) < line.get("layer_m", 10.0)
    if not near.any():
        return np.zeros(X.shape, dtype=np.float32)
    A = A[near]; B = B[near]; IA = IA[near]; IB = IB[near]
    AB = B - A
    L2 = np.maximum(np.sum(AB * AB, axis=1), 1e-12)
    best_d = np.full(len(pts), np.inf); best_i = np.zeros(len(pts))
    for s0 in range(0, len(A), 64):                     # chunked: points x segments
        a = A[s0:s0 + 64]; ab = AB[s0:s0 + 64]; l2 = L2[s0:s0 + 64]
        rel = pts[:, None, :] - a[None, :, :]
        tt = np.clip(np.sum(rel * ab[None], axis=2) / l2[None], 0.0, 1.0)
        d = np.linalg.norm(rel - tt[..., None] * ab[None], axis=2)
        k = np.argmin(d, axis=1)
        dk = d[np.arange(len(pts)), k]
        better = dk < best_d
        ik = IA[s0:s0 + 64][k] * (1 - tt[np.arange(len(pts)), k]) + IB[s0:s0 + 64][k] * tt[np.arange(len(pts)), k]
        best_d = np.where(better, dk, best_d); best_i = np.where(better, ik, best_i)
    D = w["amplitude"] * best_i * tyre_profile(best_d, w["track_m"], w["spread_m"])
    D[best_d > reach] = 0.0
    return D.reshape(X.shape).astype(np.float32)


# --- the photo's own rubber (opt-in road_wear.rubber "photo"; High Plains 0.1.7) --------------------------------------
# Kevin, 2026-11-10: "Use the photo's rubber". Where the aerial resolves the rubber (High Plains' NAIP 2023 at 0.3 m: the
# lit asphalt within 0.5 m of the model line reads 0.915 of the lit median, the same distance from its mirror across the
# centreline 1.075), the asphalt gets NO drawn band: the photo's tone carries it. The line is kept to measure that
# darkening (the line against its mirror, which takes out the road's own across-the-road shading) and to say which kerb
# faces it clips; the kerbs, whose paint is synthetic, get the measured profile.
PHOTO = {
    "a_min_m": 2.0,      # [invented] stations where the line runs at least this far off the centre: line and mirror apart
    "interior_m": 1.5,   # [invented] samples at least this far inside the built road (edge paint, kerbs and verge out)
    "u_max_m": 4.0,      # [invented] the measured profile's half width across the line: on High Plains it is still 0.05-0.09
                         # at 2.5 m (a kerb level jump of ~8 there) and ~0.02 by 3-4 m (naip_read.log)
    "du_m": 0.25,        # the profile's step (a texel at 0.25 m; finer than High Plains' 0.3 m pixel needs no more)
    "band_m": 0.75,      # the depth is read over |u| <= this (the drawn mode's rubber row reads the same band)
}


# --- tone only (opt-in road_wear.rubber "none"; Pueblo, Aspen, Grand Junction, Pikes Peak) ------------------------------
# Kevin, 2026-11-10: "Tone only, no rubber". Where the 0.3 m aerial shows no rubber the gate can use (the photo's own depth
# under photo_min_depth 0.03: Pueblo 0.022, Aspen -0.008, Grand Junction 0.002, Pikes Peak -0.008, the PC's overnight
# run), the asphalt takes the photo's tone and nothing else: no drawn band (as photo mode) and no kerb levels (nothing
# measured to level them by, so road_wear.kerbs is refused). The line is still found and the photo measured across it
# against its mirror (photo_rubber, as photo mode), so the gate can show the shipped atlas adds nothing to the photo.
RUBBER_MODES = ("drawn", "photo", "none")


def rubber_mode(spec: dict) -> tuple[str, str | None]:
    """road_wear.rubber, checked: (mode, None), or (mode, the FATAL's text). Absent = "drawn" (Milford, unchanged)."""
    mode = spec.get("rubber", "drawn")
    if mode not in RUBBER_MODES:
        return mode, f"road_wear.rubber {mode!r}: 'drawn', 'photo' or 'none'"
    if mode in ("photo", "none") and not spec.get("aerial"):
        return mode, f"road_wear.rubber {mode!r} needs road_wear.aerial"
    if mode == "none" and kerb_spec(spec) is not None:
        return mode, "road_wear.rubber 'none' draws no rubber, so nothing levels the kerbs: drop road_wear.kerbs"
    return mode, None


def nearest_station(P: np.ndarray, C: np.ndarray) -> np.ndarray:
    """Index of the nearest centreline station (2D) for every point."""
    out = np.empty(len(P), dtype=np.int64)
    for s0 in range(0, len(P), 256):
        d = np.sum((P[s0:s0 + 256, None, :2] - C[None, :, :2]) ** 2, axis=2)
        out[s0:s0 + 256] = np.argmin(d, axis=1)
    return out


def reflect(Q: np.ndarray, C: np.ndarray, nC: np.ndarray, k: np.ndarray) -> np.ndarray:
    """Q (... x 2) reflected across the centreline at station k (its point C[k], left normal nC[k])."""
    q = Q - C[k, :2]
    return C[k, :2] + q - 2.0 * np.sum(q * nC[k], axis=-1, keepdims=True) * nC[k]


def photo_rubber(tone_at, P: np.ndarray, C: np.ndarray, nC: np.ndarray, closed: bool = True, ph: dict | None = None) -> dict:
    """The photo's darkening across the line, measured against its mirror: at every line station at least a_min_m off the
    centre, the tone at u along the line's left normal and at the reflection of that point across the centreline;
    D(u) = 1 - mean tone on the line side / mean tone on the mirror side (pooled over the stations where both are usable).
    ``tone_at(x, y)`` -> tone, NaN where unusable (not lit asphalt at least interior_m inside the road).
    Returns {"u", "D", "depth" (pooled over |u| <= band_m), "centroid_m" (of max(D, 0) over the profile), "peak",
    "stations", "samples"}."""
    ph = dict(PHOTO, **(ph or {}))
    P = np.asarray(P, dtype=np.float64)
    k = nearest_station(P, C)
    a = np.sum((P[:, :2] - C[k, :2]) * nC[k], axis=1)
    nl = left_normals(P, closed)
    sel = np.where(np.abs(a) >= ph["a_min_m"])[0]
    us = np.round(np.arange(-ph["u_max_m"], ph["u_max_m"] + 1e-9, ph["du_m"]), 6)
    Q = P[sel, None, :2] + us[None, :, None] * nl[sel, None, :]
    M = reflect(Q, C, nC, np.repeat(k[sel, None], len(us), axis=1))
    tl = np.asarray(tone_at(Q[..., 0], Q[..., 1]), dtype=np.float64)
    tm = np.asarray(tone_at(M[..., 0], M[..., 1]), dtype=np.float64)
    ok = np.isfinite(tl) & np.isfinite(tm)
    sl = np.where(ok, tl, 0).sum(0); sm = np.where(ok, tm, 0).sum(0); n = ok.sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        D = np.where(n > 0, 1.0 - sl / np.maximum(sm, 1e-12), np.nan)
    band = np.abs(us) <= ph["band_m"] + 1e-9
    depth = float(1.0 - sl[band].sum() / max(1e-12, sm[band].sum())) if n[band].sum() else float("nan")
    Dp = np.where(np.isfinite(D), np.maximum(D, 0.0), 0.0)
    cen = float((us * Dp).sum() / Dp.sum()) if Dp.sum() > 0 else float("nan")
    return {"u": us.tolist(), "D": [None if not np.isfinite(v) else round(float(v), 5) for v in D],
            "depth": round(depth, 5), "centroid_m": round(cen, 4), "peak": round(float(np.nanmax(D)) if np.isfinite(D).any() else 0.0, 5),
            "stations": int(len(sel)), "samples": int(ok.sum()), "params": ph}


def photo_darkness_at(X: np.ndarray, Y: np.ndarray, Z: float | None, line: dict, prof: dict) -> np.ndarray:
    """The measured profile laid on world points: each point's signed offset u from its nearest line segment (left of the
    direction of travel positive, as left_normals), D(u) interpolated from the profile, 0 outside it and where D < 0."""
    P = line["P"]
    pts = np.stack([np.ravel(X), np.ravel(Y)], axis=1)
    A = P[:, :2]; B = np.roll(P[:, :2], -1, axis=0) if line["closed"] else P[1:, :2]
    if not line["closed"]:
        A = A[:-1]
    us = np.array(prof["u"], dtype=np.float64)
    Dv = np.array([0.0 if v is None else max(0.0, float(v)) for v in prof["D"]])
    near = np.ones(len(A), dtype=bool)
    if Z is not None and P.shape[1] > 2:
        near &= np.abs(P[:len(A), 2] - Z) < line.get("layer_m", 10.0)
    A = A[near]; B = B[near]
    AB = B - A
    L2 = np.maximum(np.sum(AB * AB, axis=1), 1e-12)
    best_d = np.full(len(pts), np.inf); best_u = np.zeros(len(pts))
    for s0 in range(0, len(A), 64):
        a = A[s0:s0 + 64]; ab = AB[s0:s0 + 64]; l2 = L2[s0:s0 + 64]
        rel = pts[:, None, :] - a[None, :, :]
        tt = np.clip(np.sum(rel * ab[None], axis=2) / l2[None], 0.0, 1.0)
        d = np.linalg.norm(rel - tt[..., None] * ab[None], axis=2)
        kk = np.argmin(d, axis=1); r = np.arange(len(pts))
        dk = d[r, kk]
        cross = ab[kk, 0] * rel[r, kk, 1] - ab[kk, 1] * rel[r, kk, 0]
        better = dk < best_d
        best_d = np.where(better, dk, best_d); best_u = np.where(better, np.sign(cross) * dk, best_u)
    out = np.interp(best_u, us, Dv, left=0.0, right=0.0)
    out[np.abs(best_u) > us.max() + 1e-9] = 0.0
    return out.reshape(np.shape(X))


# --- the atlas --------------------------------------------------------------------------------------------------------
def plan_atlas(centroids: np.ndarray, heights: np.ndarray, overhang_m: float, spec: dict) -> dict:
    """Cells, margin, pitch and the power-of-two atlas: the smallest atlas side (<= max_atlas_px) whose square tiles hold
    every used cell, trying cell sizes from 2 to 16 detail tiles. Cell size, margin and pitch are whole detail tiles."""
    tex = float(spec["texel_m"]); D = float(spec["detail_tile_m"])
    margin = math.ceil((overhang_m + 2 * tex) / D) * D             # + 2 texels: the bilinear footprint and mip 1
    best = None
    for k in range(2, 17):
        C = k * D
        keys = set(zip(np.floor(centroids[:, 0] / C).astype(int).tolist(), np.floor(centroids[:, 1] / C).astype(int).tolist(),
                       np.round(heights / spec["layer_m"]).astype(int).tolist()))
        pitch_px = int(round((C + 2 * margin) / tex))
        side = 256
        while side <= spec["max_atlas_px"] and (side // pitch_px) ** 2 < len(keys):
            side *= 2
        if side > spec["max_atlas_px"]:
            continue
        used = len(keys) * pitch_px * pitch_px / float(side * side)
        cand = (side, -k)                 # the smallest atlas, then the largest cell (the fewest seams)
        if best is None or cand < best[0]:
            best = (cand, {"cell_m": C, "margin_m": margin, "pitch_px": pitch_px, "atlas_px": side, "cells": len(keys),
                           "tiles_per_row": side // pitch_px, "atlas_fill_pct": round(100 * used, 1)})
    if best is None:
        raise ValueError(f"road_wear: no atlas <= {spec['max_atlas_px']} px holds the road at {tex} m/texel")
    return best[1]


def cell_keys(centroids: np.ndarray, heights: np.ndarray, plan: dict, spec: dict) -> list[tuple[int, int, int]]:
    C = plan["cell_m"]
    return list(zip(np.floor(centroids[:, 0] / C).astype(int).tolist(), np.floor(centroids[:, 1] / C).astype(int).tolist(),
                    np.round(heights / spec["layer_m"]).astype(int).tolist()))


def tile_slots(keys: list[tuple[int, int, int]], plan: dict) -> dict:
    """key -> (col, row) of its atlas tile, in a stable order (sorted keys)."""
    per = plan["tiles_per_row"]
    return {k: (i % per, i // per) for i, k in enumerate(sorted(set(keys)))}


def tile_window(key, plan: dict) -> tuple[float, float]:
    """World (x, y) of the tile window's south-west corner."""
    return key[0] * plan["cell_m"] - plan["margin_m"], key[1] * plan["cell_m"] - plan["margin_m"]


def uv_of(x: np.ndarray, y: np.ndarray, key, slot, plan: dict, tex: float) -> tuple[np.ndarray, np.ndarray]:
    """Blender UVs (v up) of world points in a face of cell ``key`` placed at atlas tile ``slot``."""
    wx, wy = tile_window(key, plan)
    A = float(plan["atlas_px"]); P = plan["pitch_px"]
    return (slot[0] * P + (x - wx) / tex) / A, (slot[1] * P + (y - wy) / tex) / A


def detail_multiplier(plan: dict, spec: dict) -> float:
    """atlas_px x texel_m / detail_tile_m: the detail UV scale. It must be WHOLE (ledger 0084, High Plains 0.1.7): the
    shipped v is flipped, so the detail lands at (1 - v) x mult and any fraction shifts the grain off the prep's 4 m phase
    (texel 0.2 m at 4096 px gave 204.8: road_wear_check detail_phase 0.2 tiles off). Raises ValueError naming the values."""
    m = plan["atlas_px"] * spec["texel_m"] / spec["detail_tile_m"]
    if abs(m - round(m)) > 1e-9:
        raise ValueError(f"road_wear: detailUVMultiplier {m!r} = atlas_px {plan['atlas_px']} x texel_m {spec['texel_m']} / "
                         f"detail_tile_m {spec['detail_tile_m']} is not whole: the grain would land {m - math.floor(m):.3f} tile "
                         "off the prep's phase (choose a texel that makes it whole, e.g. 0.25 m at 4096 px -> 256)")
    return m


# --- the race kerbs (opt-in road_wear.kerbs; High Plains 0.1.7) ---------------------------------------------------------
# A traced race kerb (tools/author_kerbs_blend.py: 1KERB_circuit_<k>) carries its own paint in its own UVs (u across the
# run inside its colour's atlas cell, v = arc / 2 m repeating), so it cannot take the world atlas the road does. It keeps
# its paint and its UVs' v; its u moves into one of ``levels`` copies of its own paint texture laid side by side, copy k
# darkened by k x step, the level each face takes being the rubber the line puts on that face's centroid (the same
# wear_at the road's atlas is baked from, so the kerb and the asphalt beside it darken together).
KERB_DEFAULTS = {
    "prefix": "1KERB_CIRCUIT_",     # tools/author_kerbs_blend.py's PREFIX, upper-cased
    "levels": 16,                   # [invented] copies of the paint: 16 at 0.22 is a 1.5 % step, under what an eye sees
}


def kerb_spec(spec: dict) -> dict | None:
    """The merged road_wear.kerbs block, or None when the config names none (no kerb is touched)."""
    k = spec.get("kerbs")
    if k is None or k is False:
        return None
    out = dict(KERB_DEFAULTS)
    out.update({kk: vv for kk, vv in k.items() if not str(kk).startswith("_")})
    out["prefix"] = str(out["prefix"]).upper()
    out["levels"] = int(out["levels"])
    if out["levels"] < 2 or out["levels"] & (out["levels"] - 1):
        raise ValueError(f"road_wear.kerbs.levels {out['levels']}: a power of two >= 2 (the atlas stays a power of two, L7)")
    return out


def kerb_step(amplitude: float, levels: int) -> float:
    """The darkening between two adjacent kerb levels: level levels-1 is the declared amplitude (one line's peak)."""
    return float(amplitude) / (levels - 1)


def kerb_levels(darkness: np.ndarray, step: float, levels: int) -> np.ndarray:
    """Each face's level: its darkness (1 - prod(1 - wear) over the lines) to the nearest step, clipped to the atlas."""
    return np.clip(np.round(np.asarray(darkness, dtype=np.float64) / step), 0, levels - 1).astype(np.int64)


def kerb_wear_atlas(base: np.ndarray, levels: int, step: float, repeats: int = 1) -> np.ndarray:
    """uint8 H x (W * repeats * levels) x C: ``levels`` copies of the kerb paint side by side, copy k = round(paint x
    (1 - k step)); each copy holds ``repeats`` tiles of the paint side by side (kerb_repeats; 1 = High Plains 0.1.7's
    atlas, unchanged). Copy 0 is the paint byte for byte."""
    b = np.asarray(base, dtype=np.uint8)
    if repeats != 1:
        b = np.tile(b, (1, int(repeats)) + (1,) * (b.ndim - 2))
    out = np.empty((b.shape[0], b.shape[1] * levels) + b.shape[2:], dtype=np.uint8)
    for k in range(levels):
        out[:, k * b.shape[1]:(k + 1) * b.shape[1]] = np.clip(np.round(b.astype(np.float64) * (1.0 - k * step)), 0, 255)
    return out


def kerb_u(u: np.ndarray, level: np.ndarray, levels: int, repeats: int = 1) -> np.ndarray:
    """A kerb UV's u moved into its level's copy (u in [0, repeats] of the paint texture, a face's own u after
    kerb_unwrap -> (level + u / repeats) / levels; repeats 1: (level + u) / levels, High Plains 0.1.7's arithmetic)."""
    if repeats == 1:
        return (np.asarray(level, dtype=np.float64) + np.asarray(u, dtype=np.float64)) / levels
    return (np.asarray(level, dtype=np.float64) + np.asarray(u, dtype=np.float64) / float(repeats)) / levels


# The paint REPEATS (Pueblo / Aspen, PC 2026-11-10: "1KERB_circuit_0: u 0.000..2.111 outside the paint texture"): a kerb
# without a kerb.atlas cell has u = offset / painted width (tools/author_kerbs_blend.py), so the back fall past the
# painted width runs on to u = (w + ramp_out) / w, and the stock exporter's wrap addressing repeats the paint there. A
# level copy is not wrapped (its neighbour copy sits beside it), so:
#   1. every face's u moves back by the whole repeats under it, floor(its smallest u) (kerb_unwrap): frac is what the
#      wrap sampled, so the paint at every point is the same texel as before;
#   2. a face that still spans a repeat boundary (Pueblo's back fall: 1.0 .. 2.111, 1.11 repeats wide) is not split:
#      each copy holds ``repeats`` tiles of the paint side by side (kerb_repeats, kerb_wear_atlas), so u in
#      [0, repeats) inside the copy reads the paint exactly as the wrap did, the tile seam inside the copy being the
#      same column-W-1-to-column-0 seam the wrap had. No face, triangle or vertex changes (the physics, the gate's
#      face join and the writer's vertex count are as before); the cost is a wider atlas (Pueblo: 64 x 16 x 2 = 2048 px).
# High Plains 0.1.7 (cells inside 0.05 .. 0.95) unwraps by 0 and takes repeats 1: its UVs and atlas are byte for byte as
# before.
KERB_U_EPS = 1e-6               # the bake's own tolerance on a kerb's u (its 0..1 check, before): a corner within this
                                # of a whole repeat counts as on it (float32 holds u to ~1e-7)
KERB_ATLAS_MAX_PX = 16384       # the largest 2D texture Direct3D 11 (AC's renderer) creates


def kerb_unwrap(u: np.ndarray, face_of_loop: np.ndarray, n_faces: int) -> tuple[np.ndarray, np.ndarray]:
    """(each loop's u less its face's whole repeats, the repeats per face): face f moves by floor(min u over its loops
    + KERB_U_EPS), so its smallest u lies in [-KERB_U_EPS, 1). A face inside [0, 1] moves by exactly 0."""
    u = np.asarray(u, dtype=np.float64)
    fl = np.asarray(face_of_loop, dtype=np.int64)
    lo = np.full(int(n_faces), np.inf)
    np.minimum.at(lo, fl, u)
    shift = np.floor(lo + KERB_U_EPS)
    shift[~np.isfinite(shift)] = 0.0                       # a face with no loops (none in a built mesh)
    return u - shift[fl], shift


def kerb_repeats(u_max: float, levels: int) -> int:
    """The tiles of paint each level copy holds: the smallest power of two R (the atlas stays a power of two, L7) whose
    copy holds every face's unwrapped u (u_max) with the copy's right edge more than one float32 step (2^-23, its spacing
    just under 1) past the shipped (level + u_max / R) / levels, so no corner of copy k is stored as copy k + 1's first
    column. High Plains 0.1.7: u_max 0.95 -> 1."""
    if not math.isfinite(u_max):
        raise ValueError(f"road_wear.kerbs: a kerb u is not finite ({u_max})")
    R = 1
    while (R - u_max) / (R * levels) < 2.0 ** -23:
        R *= 2
    return R


# --- PNG --------------------------------------------------------------------------------------------------------------
def write_png(path, img: np.ndarray, level: int = 9) -> int:
    """Minimal PNG writer: uint8 H x W x C (C = 3 or 4), row 0 = TOP. Filter 'Up' on every row. Returns bytes written."""
    img = np.ascontiguousarray(img, dtype=np.uint8)
    h, w = img.shape[:2]
    c = 1 if img.ndim == 2 else img.shape[2]
    ctype = {1: 0, 3: 2, 4: 6}[c]
    rows = img.reshape(h, w * c).astype(np.int16)
    up = np.empty_like(rows)
    up[0] = rows[0]
    up[1:] = rows[1:] - rows[:-1]
    raw = np.empty((h, w * c + 1), dtype=np.uint8)
    raw[:, 0] = 2                                   # filter type Up
    raw[:, 1:] = (up & 0xFF).astype(np.uint8)
    raw[0, 0] = 0
    raw[0, 1:] = rows[0].astype(np.uint8)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(raw.tobytes(), level)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def read_png_rgba(path) -> np.ndarray:
    """The inverse of write_png for 8-bit RGB / RGBA (non-interlaced, any filter), row 0 = TOP. For tests and gates."""
    d = open(path, "rb").read()
    assert d[:8] == b"\x89PNG\r\n\x1a\n"
    o = 8; idat = b""; w = h = ctype = None
    while o < len(d):
        n = struct.unpack(">I", d[o:o + 4])[0]; tag = d[o + 4:o + 8]; body = d[o + 8:o + 8 + n]; o += 12 + n
        if tag == b"IHDR":
            w, h, bd, ctype = struct.unpack(">IIBB", body[:10])
            assert bd == 8
        elif tag == b"IDAT":
            idat += body
    c = {0: 1, 2: 3, 6: 4}[ctype]
    raw = np.frombuffer(zlib.decompress(idat), dtype=np.uint8).reshape(h, w * c + 1)
    out = np.zeros((h, w * c), dtype=np.int32)
    for j in range(h):
        f = raw[j, 0]; x = raw[j, 1:].astype(np.int32)
        prev = out[j - 1] if j else np.zeros(w * c, dtype=np.int32)
        if f == 0:
            row = x
        elif f == 2:
            row = (x + prev) & 0xFF
        elif f == 1:
            row = x.copy()
            for i in range(c, w * c):
                row[i] = (row[i] + row[i - c]) & 0xFF
        else:
            row = np.zeros_like(x)
            for i in range(w * c):
                a = row[i - c] if i >= c else 0
                b = prev[i]
                cc = prev[i - c] if i >= c else 0
                if f == 3:
                    row[i] = (x[i] + (a + b) // 2) & 0xFF
                else:
                    p = a + b - cc
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - cc)
                    pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else cc)
                    row[i] = (x[i] + pr) & 0xFF
        out[j] = row
    return out.reshape(h, w, c).astype(np.uint8)
