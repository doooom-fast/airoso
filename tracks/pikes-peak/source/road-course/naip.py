"""Shared NAIP readers for the re-trace (ledger 0085 Re-trace): the image as float channels, bilinear sampling in the
track's ENU metres, the registration shift (register_wall.py) applied to every ENU <-> pixel conversion, and the
pavement / kerb scores the edge finders read.

Every coordinate this package writes is ENU about tracks/pikes-peak/data/centerline.local.json's origin AFTER the NAIP
shift is removed: en_true = en_naip - SHIFT. SHIFT comes from registration.json (register_wall.py); absent, zero.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))
from geo import IMG, en_to_px as _en_to_px, px_to_en as _px_to_en  # noqa: E402

import os
# intermediate arrays shared by retrace.py -> routes.py -> stills.py (not committed: pickles of numpy arrays)
CACHE = Path(os.environ.get("PP_CACHE", "/Volumes/Drive/codex/pp_work/retrace/_cache"))

_REG = HERE / "registration.json"
SHIFT = np.zeros(2)
if _REG.exists():
    _r = json.loads(_REG.read_text())
    if _r.get("apply"):
        SHIFT = np.array(_r["shift_en_m"], float)


def en_to_px(e, n):
    """true ENU -> NAIP pixel (the image is displaced by SHIFT)."""
    return _en_to_px(np.asarray(e, float) + SHIFT[0], np.asarray(n, float) + SHIFT[1])


def px_to_en(px, py):
    e, n = _px_to_en(px, py)
    return e - SHIFT[0], n - SHIFT[1]


_cache = {}


def image():
    if "im" not in _cache:
        _cache["im"] = np.asarray(Image.open(IMG).convert("RGB")).astype(np.float32)
    return _cache["im"]


def channels():
    """lum, sat, redness, whiteness, pavement score (0..1), kerb score (0..1)."""
    if "ch" in _cache:
        return _cache["ch"]
    im = image()
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    mx = im.max(-1); mn = im.min(-1)
    lum = im.mean(-1)
    sat = (mx - mn) / np.maximum(mx, 1)
    # red kerb blocks, fresh (r-g ~90) and faded (r-g ~40, r-b ~60); dirt and the tan concrete reach r-g ~15, r-b ~35
    red = np.clip(((r - g) - 20) / 20, 0, 1) * np.clip(((r - b) - 35) / 25, 0, 1)
    white = np.clip((mn - 190) / 30, 0, 1) * np.clip((0.12 - sat) / 0.06, 0, 1)
    # GREY: the newer asphalt is near-neutral; grass / dirt / the tan lot concrete carry yellowness (r+g)/2 - b of
    # 20-36 (sampled: new asphalt 2-7, old asphalt 18-24, dirt 16-34, grass 31-36).
    yel = (r + g) / 2 - b
    grey = np.clip((22 - yel) / 14, 0, 1) * np.clip((lum - 35) / 20, 0, 1)
    # SMOOTH: the older asphalt has dirt's colour but not its texture. Local luminance sd (1 px gaussian window),
    # averaged over 1.5 px: asphalt (old or new) 3.0-4.5, dirt and grass 7.5-12 (sampled boxes, ledger 0085 Re-trace).
    mu = ndimage.gaussian_filter(lum, 1.0)
    sd = np.sqrt(np.maximum(ndimage.gaussian_filter(lum ** 2, 1.0) - mu ** 2, 0))
    tex = ndimage.gaussian_filter(sd, 1.5)
    smooth = np.clip((6.5 - tex) / 2.5, 0, 1) * np.clip((30 - yel) / 8, 0, 1) * np.clip((lum - 60) / 20, 0, 1)
    grey_s = ndimage.gaussian_filter(np.maximum(grey, np.maximum(red, white)), 0.7)
    smooth_s = ndimage.gaussian_filter(smooth, 0.7)
    pave = np.maximum(grey_s, smooth_s)
    # the green-painted run-off beside the bottom road and the west road (g well over r and b): paved, but not the road
    paint = ndimage.gaussian_filter(np.clip(((g - r) - 25) / 15, 0, 1) * np.clip(((g - b) - 5) / 10, 0, 1), 0.7)
    pave = pave * (1 - paint)
    grey_s = grey_s * (1 - paint)
    # a kerb: red blocks, plus the white blocks between them (white within 3 px of red). Painted white lines alone
    # (no red beside them) are not kerb.
    redm = red > 0.5
    near = ndimage.binary_dilation(redm, iterations=3)
    kb = redm | (near & (white > 0.5))
    kb = ndimage.binary_closing(kb, iterations=1)
    kerb = ndimage.gaussian_filter(kb.astype(np.float32), 0.7)
    band = ndimage.gaussian_filter(np.maximum(white, kb.astype(np.float32)), 0.5)   # an edge line or a kerb
    _cache["ch"] = dict(lum=lum, sat=sat, red=red, white=white, band=band, yel=yel, pave=pave, kerb=kerb, grey=grey_s,
                        smooth=smooth_s, tex=tex)
    return _cache["ch"]


def sample(ch, e, n, order=1):
    px, py = en_to_px(e, n)
    return ndimage.map_coordinates(ch, [np.asarray(py), np.asarray(px)], order=order, mode="nearest")


def cumlen(P):
    return np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]


def normals(P, closed=False):
    if closed:
        T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    else:
        T = np.gradient(P, axis=0)
    T = T / np.linalg.norm(T, axis=1)[:, None]
    return T, np.c_[-T[:, 1], T[:, 0]]          # tangent, LEFT normal (E, N)


def resample(P, step, closed=False):
    if closed:
        P = np.vstack([P, P[:1]])
    s = cumlen(P)
    n = max(2, int(round(s[-1] / step)) + 1)
    t = np.linspace(0, s[-1], n)
    Q = np.c_[np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])]
    return Q[:-1] if closed else Q


def oval_line():
    """The port's line (tracks/pikes-peak/data/centerline.local.json), its widths and stations, and the lidar wall face."""
    root = HERE.parents[1]
    cl = json.loads((root / "data/centerline.local.json").read_text())
    P = np.array(cl["points_xyz_m"])[:, [0, 2]]
    Wd = np.array(cl["widths_m"], float)
    wj = json.loads((root / "source/lidar/wall-survey/wall_right.json").read_text())
    f = np.array([np.nan if not r.get("wall") else r["wall"]["face_past_edge_m"] for r in wj["stations"]])
    # the survey's own stations (tools/lidar_wall.py stations(): every 3 m along the open point list, the segment's
    # heading for the normal, the width interpolated), so the face lands exactly where the lidar read it
    st = cumlen(P)
    S = np.array([r["s"] for r in wj["stations"]], float)
    j = np.clip(np.searchsorted(st, S, side="left") - 1, 0, len(P) - 2)
    j = np.where(st[j + 1] < S, j + 1, j).clip(0, len(P) - 2)
    t = (S - st[j]) / np.maximum(st[j + 1] - st[j], 1e-9)
    X = P[j] + (P[j + 1] - P[j]) * t[:, None]
    h = np.arctan2(P[j + 1, 1] - P[j, 1], P[j + 1, 0] - P[j, 0])
    L = np.c_[-np.sin(h), np.cos(h)]
    T = np.c_[np.cos(h), np.sin(h)]
    hw = (Wd[j] + (Wd[j + 1] - Wd[j]) * t) / 2
    face = X - (hw + f)[:, None] * L
    return dict(P=X, W=2 * hw, s=S, T=T, L=L, face_off=hw + f, face=face, line=P)
