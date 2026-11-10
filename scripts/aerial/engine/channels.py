"""Per-pixel scores the edge finders and the route read: pavement, kerb, painted line, wear (luminance).

Defaults are Pikes Peak's (ledger 0085 Re-trace, NAIP 2023 0.3 m, sampled boxes there); every one is [invented]
tuning of a colour reader, overridable per track by ``colours`` in the engine config (data, never code). The image is
the measurement; these only say which pixels are which surface.

  lum        mean of R, G, B
  red        kerb red, fresh or faded:  clip(((r-g) - red_rg) / 20) * clip(((r-b) - red_rb) / 25)
  white      bright and unsaturated:    clip((min - white_min) / 30) * clip((0.12 - sat) / 0.06)
  grey       near-neutral asphalt:      clip((grey_yel - yel) / 14) * clip((lum - grey_lum) / 20),  yel = (r+g)/2 - b
  smooth     old asphalt with dirt's colour but not its texture: local luminance sd (1 px gaussian, averaged 1.5 px)
             under smooth_tex, yel under smooth_yel, lum over smooth_lum
  paint      green run-off paint (paved, not road): g well over r and b
  pave       max(grey, smooth) less paint: the pavement score, 0..1
  kerb       red blocks plus the white blocks within 3 px of red, closed: a kerb, 0..1
  band       a white line or a kerb: the boundary band that takes precedence over the surface edge
  line       a thin bright line on any surface (white top-hat over ``line_width_m``, scaled by ``line_amp``)
  edge_band  only with ``colours.edge_band`` (a colour axis, data): a painted boundary band of a known colour, joined
             with the kerb; a circuit painted on a lot whose pavement does not end at its edge (Exotics' blue-grey bands)
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

DEFAULTS = {
    "red_rg": 20.0, "red_rb": 35.0,
    "white_min": 190.0,
    "grey_yel": 22.0, "grey_lum": 35.0,
    "smooth_tex": 6.5, "smooth_yel": 30.0, "smooth_lum": 60.0,
    "paint_gr": 25.0, "paint_gb": 5.0,
    "line_width_m": 1.5, "line_amp": 25.0,
}


def compute(rgb: np.ndarray, gsd_m: float, colours: dict | None = None) -> dict:
    p = dict(DEFAULTS, **(colours or {}))
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(-1)
    mn = rgb.min(-1)
    lum = rgb.mean(-1)
    sat = (mx - mn) / np.maximum(mx, 1)
    red = np.clip(((r - g) - p["red_rg"]) / 20, 0, 1) * np.clip(((r - b) - p["red_rb"]) / 25, 0, 1)
    white = np.clip((mn - p["white_min"]) / 30, 0, 1) * np.clip((0.12 - sat) / 0.06, 0, 1)
    yel = (r + g) / 2 - b
    grey = np.clip((p["grey_yel"] - yel) / 14, 0, 1) * np.clip((lum - p["grey_lum"]) / 20, 0, 1)
    mu = ndimage.gaussian_filter(lum, 1.0)
    sd = np.sqrt(np.maximum(ndimage.gaussian_filter(lum ** 2, 1.0) - mu ** 2, 0))
    tex = ndimage.gaussian_filter(sd, 1.5)
    smooth = (np.clip((p["smooth_tex"] - tex) / 2.5, 0, 1) * np.clip((p["smooth_yel"] - yel) / 8, 0, 1)
              * np.clip((lum - p["smooth_lum"]) / 20, 0, 1))
    grey_s = ndimage.gaussian_filter(np.maximum(grey, np.maximum(red, white)), 0.7)
    smooth_s = ndimage.gaussian_filter(smooth, 0.7)
    paint = ndimage.gaussian_filter(np.clip(((g - r) - p["paint_gr"]) / 15, 0, 1)
                                    * np.clip(((g - b) - p["paint_gb"]) / 10, 0, 1), 0.7)
    pave = np.maximum(grey_s, smooth_s) * (1 - paint)
    redm = red > 0.5
    near = ndimage.binary_dilation(redm, iterations=3)
    kb = ndimage.binary_closing(redm | (near & (white > 0.5)), iterations=1)
    kerb = ndimage.gaussian_filter(kb.astype(np.float32), 0.7)
    band = ndimage.gaussian_filter(np.maximum(white, kb.astype(np.float32)), 0.5)
    k = max(3, int(round(p["line_width_m"] / max(gsd_m, 1e-6))) | 1)
    top = lum - ndimage.grey_opening(ndimage.gaussian_filter(lum, 0.6), size=(k, k))
    line = np.clip(top / p["line_amp"], 0, 1)
    out = dict(lum=lum, sat=sat, red=red, white=white, yel=yel, grey=grey_s, smooth=smooth_s, tex=tex, paint=paint,
               pave=pave, kerb=kerb, band=band, line=line)
    eb = p.get("edge_band")
    if eb:
        # a track-specific boundary band by colour (data in the config): score = clip((w . rgb - lo) / (hi - lo)),
        # e.g. Exotics' blue-grey edge bands {"weights": [-1, 0, 1], "lo": 0, "hi": 10} (b - r over 0..10), joined
        # with the kerb's red / white blocks
        w = np.asarray(eb["weights"], np.float32)
        v = rgb[..., 0] * w[0] + rgb[..., 1] * w[1] + rgb[..., 2] * w[2]
        sc = np.clip((v - eb["lo"]) / (eb["hi"] - eb["lo"]), 0, 1)
        if "lum_min" in eb:      # and brighter than this (a dark rubbered line can share the band's hue)
            sc = sc * np.clip((lum - eb["lum_min"]) / eb.get("lum_span", 20.0), 0, 1)
        out["edge_band"] = np.maximum(ndimage.gaussian_filter(sc, 0.7), kerb)
    f32 = lambda a: np.asarray(a, np.float32)  # noqa: E731
    return {k_: f32(v) for k_, v in out.items()}


def pavement_mask(pave: np.ndarray, hole_px: int = 60) -> np.ndarray:
    """pave > 0.5, opened once, holes under ``hole_px`` (cars, paint, debris) filled."""
    m = ndimage.binary_opening(pave > 0.5, iterations=1)
    lab, n = ndimage.label(~m)
    if n:
        sizes = ndimage.sum(np.ones_like(lab), lab, range(n + 1))
        small = sizes < hole_px
        small[0] = False
        m = m | small[lab]
    return m


def sample(ch: np.ndarray, px, py, order: int = 1) -> np.ndarray:
    """Bilinear (order 1) samples of a channel at fractional pixel-centre coordinates."""
    px = np.asarray(px, float)
    py = np.asarray(py, float)
    return ndimage.map_coordinates(ch, [py.ravel(), px.ravel()], order=order, mode="nearest").reshape(px.shape)
