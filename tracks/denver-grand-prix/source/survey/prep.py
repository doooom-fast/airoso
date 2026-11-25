"""What the lap's pictures need before the paint reader looks at them (the pilot's stretch had neither problem).

shadow_gain(ortho)   Downtown, a tower's shadow lies over whole junctions. Paint is still there, about 9 luminance steps over
                     asphalt at 32 (noise 1.2). Shadow = dark (smoothed luminance under SH_LUM) with the sky's blue cast
                     (blue / red over SH_BR, after the tile's sunlit pavement is balanced to neutral grey: balance()), in patches of at least SH_MIN_M2. Inside it each channel is multiplied so the
                     local shadowed pavement (a Gaussian mean over shadow pixels only, GAIN_SIGMA_M) comes up to the tile's
                     sunlit pavement colour; gain capped at GAIN_MAX. A band BAND_M wide along the shadow's edge is returned
                     as mask_out: the penumbra becomes a false bright line under the gain.
coloured(rgb, gsd)   Painted surfaces that are not asphalt-coloured: red (bus lanes, brick) and green (bike lanes, boxes),
                     by channel dominance, at least COL_MIN_M2, opened by 0.4 m. A vehicle passes this test too: the lap
                     survey keeps only what two flight years show at one place.
Every threshold is [invented] tuning; each is written into the survey's output.
"""
import numpy as np
from scipy import ndimage

Q = {'SH_LUM': 62.0, 'SH_BR': 1.30, 'BAL_LUM': (85.0, 135.0), 'BAL_CHROMA_MAX': 28.0, 'SH_MIN_M2': 25.0, 'GAIN_SIGMA_M': 2.5, 'GAIN_MAX': 6.0, 'BAND_M': 0.3, 'TARGET_RGB': (104.0, 107.0, 112.0),
     'RED_DOM': 30.0, 'GREEN_DOM': 18.0, 'COL_MIN_M2': 2.0}
LUMW = np.array([0.299, 0.587, 0.114], np.float32)


def balance(rgb):
    """Per-channel gains that make the tile's sunlit pavement neutral grey. The three flight years are balanced differently
    (2018's sunlit asphalt is (117, 111, 104), warm enough to fail the reader's asphalt-colour test on half the roadway;
    its shadows are less blue than 2022's). Returns the gains; (1, 1, 1) when too little grey ground is in the tile."""
    lum = rgb @ LUMW; m = (lum > Q['BAL_LUM'][0]) & (lum < Q['BAL_LUM'][1]) & (rgb.max(-1) - rgb.min(-1) < Q['BAL_CHROMA_MAX'])
    if m.sum() < 50000:
        return np.ones(3, np.float32)
    med = np.median(rgb[m][::11], 0); return (med.mean() / np.maximum(med, 1.0)).astype(np.float32)


def shadow_mask(rgb, gsd):
    k = max(3, int(round(0.7 / gsd)) | 1); sm = ndimage.uniform_filter(rgb, size=(k, k, 1)); lum = sm @ LUMW
    sh = (lum < Q['SH_LUM']) & (sm[..., 2] > Q['SH_BR'] * np.maximum(sm[..., 0], 1.0))
    it = max(1, int(round(0.45 / gsd))); sh = ndimage.binary_closing(ndimage.binary_opening(sh, iterations=it), iterations=it)
    lab, n = ndimage.label(sh)
    if n:
        a = ndimage.sum(np.ones_like(lab, np.float32), lab, range(n + 1)) * gsd * gsd; keep = a >= Q['SH_MIN_M2']; keep[0] = False; sh = keep[lab]
    return sh


def shadow_gain(ortho, gsd=None):
    gsd = gsd or float(np.mean(ortho.gsd)); bal = balance(ortho.rgb); ortho.rgb = np.clip(ortho.rgb * bal, 0, 255).astype(np.float32)
    rgb = ortho.rgb; sh = shadow_mask(rgb, gsd)
    out = {'shadow': sh, 'mask_out': None, 'balance_gains': [float(v) for v in bal]}
    if not sh.any():
        return out
    lum = rgb @ LUMW; sun = (~sh) & (lum > 70) & (lum < 150) & (rgb.max(-1) - rgb.min(-1) < 22)
    target = np.array(Q['TARGET_RGB'], np.float32)
    if sun.sum() > 20000:
        target = np.median(rgb[sun][::7], 0).astype(np.float32)
    f = 4; s = Q['GAIN_SIGMA_M'] / gsd / f; w = ndimage.gaussian_filter(sh[::f, ::f].astype(np.float32), s); g = np.ones_like(rgb)
    for c in range(3):
        lv = ndimage.gaussian_filter((rgb[..., c] * sh)[::f, ::f], s) / np.maximum(w, 1e-3)
        lv = np.kron(lv, np.ones((f, f), np.float32))[:rgb.shape[0], :rgb.shape[1]]
        if lv.shape != sh.shape:
            lv = np.pad(lv, ((0, sh.shape[0] - lv.shape[0]), (0, sh.shape[1] - lv.shape[1])), mode='edge')
        g[..., c] = np.clip(target[c] / np.maximum(lv, 1.0), 1.0, Q['GAIN_MAX'])
    g[~sh] = 1.0
    ortho.rgb = np.clip(rgb * g, 0, 255).astype(np.float32)
    b = max(1, int(round(Q['BAND_M'] / gsd)))
    out['mask_out'] = ndimage.binary_dilation(sh, iterations=b) & ~ndimage.binary_erosion(sh, iterations=b)
    out['target_rgb'] = [float(v) for v in target]
    return out


def coloured(rgb, gsd):
    k = max(3, int(round(0.4 / gsd)) | 1); sm = ndimage.uniform_filter(rgb, size=(k, k, 1)); r, g, b = sm[..., 0], sm[..., 1], sm[..., 2]
    it = max(1, int(round(0.2 / gsd))); out = {}
    for name, m in (('red', (r - np.maximum(g, b) > Q['RED_DOM']) & (r > 90)), ('green', (g - np.maximum(r, b) > Q['GREEN_DOM']) & (g > 80))):
        m = ndimage.binary_opening(ndimage.binary_closing(m, iterations=2 * it), iterations=it); lab, n = ndimage.label(m)     # closed first: white letters cut a red panel up
        if n:
            a = ndimage.sum(np.ones_like(lab, np.float32), lab, range(n + 1)) * gsd * gsd; keep = a >= Q['COL_MIN_M2']; keep[0] = False; m = keep[lab]
        out[name] = m
    return out
