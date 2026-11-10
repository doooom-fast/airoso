"""The aerial registered to lidar-measured features, the offset reported (and applied when it is a pixel or more).

Generalised from tracks/pikes-peak/source/road-course/register_wall.py (ledger 0085 Re-trace 1: NAIP 2023 sat 0.42 m off
the 2018 lidar wall face, applied).

Lidar features read here (the fleet's own survey formats, never re-surveyed):
  ``lidar_wall_survey``  tools/lidar_wall.py's wall_<side>.json against the line it was surveyed on (centerline.local.json
                         with its widths): each station's wall FACE (face_past_edge_m past the lane edge) as an ENU point,
                         with its outward normal. The face polyline is also a lidar-measured pavement edge for edges.py.

The registration feature on the image (``wall_top``): the wall's concrete top is the brightest thin band at the outside
of the pavement. Per station, along the outward normal (0.05 m steps, bilinear) within +-SEARCH_M of the lidar face:
the band = the luminance maximum, kept if >= PEAK_MIN and >= PEAK_OVER_ROAD over the road's median 3-6 m inside; its
road-side edge = where luminance crosses half way between that peak and the darkest value within 1.5 m inside it
(sub-pixel). offset_i = image edge - lidar face (+ outward), fitted with iterative 3-sigma trimming:
    offset_i = b + dE nE_i + dN nN_i
(dE, dN) is the image's displacement (the normals turn through 360 deg round a closed facility, so it separates from
b, the constant between the two edge definitions). Spread: block bootstrap (blocks of BLOCK stations) to respect along-
track correlation. Applied when |shift| >= one image pixel (under a pixel: reported, left alone).
Caveat carried from 0085: a wall TOP stands ~1.3 m up and carries relief displacement, a uniform shift indistinguishable
here from registration, so the shift is an upper bound on the ground's misregistration in its direction.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import channels as chn
from . import geom

SEARCH_M = 2.5
PEAK_MIN = 190.0
PEAK_OVER_ROAD = 35.0
BLOCK = 30


def lidar_wall_survey(survey: Path, line_local: Path):
    """(face points ENU, outward normals, stations, line origin lon/lat) from a wall survey and its line."""
    cl = json.loads(Path(line_local).read_text(encoding="utf-8"))
    P = np.array(cl["points_xyz_m"], float)[:, [0, 2]]
    Wd = np.array(cl["widths_m"], float)
    wj = json.loads(Path(survey).read_text(encoding="utf-8"))
    side = wj.get("side", "right")
    f = np.array([np.nan if not r.get("wall") else r["wall"]["face_past_edge_m"] for r in wj["stations"]])
    st = geom.cumlen(P)
    S = np.array([r["s"] for r in wj["stations"]], float)
    j = np.clip(np.searchsorted(st, S, side="left") - 1, 0, len(P) - 2)
    j = np.where(st[j + 1] < S, j + 1, j).clip(0, len(P) - 2)
    t = (S - st[j]) / np.maximum(st[j + 1] - st[j], 1e-9)
    X = P[j] + (P[j + 1] - P[j]) * t[:, None]
    h = np.arctan2(P[j + 1, 1] - P[j, 1], P[j + 1, 0] - P[j, 0])
    Lft = np.c_[-np.sin(h), np.cos(h)]
    hw = (Wd[j] + (Wd[j + 1] - Wd[j]) * t) / 2
    sgn = -1.0 if side == "right" else 1.0
    face = X + sgn * (hw + f)[:, None] * Lft
    out = sgn * Lft
    origin = (float(cl["origin"]["lon"]), float(cl["origin"]["lat"]))
    ok = np.isfinite(f)
    return {"face": face[ok], "outward": out[ok], "s": S[ok], "origin": origin, "side": side,
            "closed": bool(np.hypot(*(P[0] - P[-1])) < 1.0)}


def wall_top(ortho, lum, face, outward):
    """Per station, the image's wall-top road-side edge minus the lidar face (m, + outward), or nan."""
    offs = np.arange(-6.0, SEARCH_M + 1e-9, 0.05)
    rows = np.full(len(face), np.nan)
    for k in range(len(face)):
        e = face[k, 0] + offs * outward[k, 0]
        n = face[k, 1] + offs * outward[k, 1]
        px, py = ortho.en_to_px_raw(e, n)            # the raw image frame: this IS the measurement of its displacement
        v = chn.sample(lum, px, py)
        road = np.median(v[(offs >= -6) & (offs <= -3)])
        iw = np.where((offs >= -SEARCH_M) & (offs <= SEARCH_M))[0]
        ip = iw[np.argmax(v[iw])]
        peak = v[ip]
        if peak < PEAK_MIN or peak - road < PEAK_OVER_ROAD:
            continue
        lo = max(0, ip - int(1.5 / 0.05))
        imn = lo + int(np.argmin(v[lo:ip + 1]))
        half = (peak + v[imn]) / 2
        for j in range(ip, imn, -1):
            if v[j - 1] < half <= v[j]:
                rows[k] = offs[j - 1] + (half - v[j - 1]) / (v[j] - v[j - 1]) * 0.05
                break
    return rows


def fit_shift(off, outward, gsd_m):
    ok = np.isfinite(off)
    A = np.c_[np.ones(len(off)), outward[:, 0], outward[:, 1]]
    keep = ok.copy()
    coef = np.zeros(3)
    for _ in range(6):
        coef = np.linalg.lstsq(A[keep], off[keep], rcond=None)[0]
        res = off - A @ coef
        sd = np.nanstd(res[keep])
        keep = ok & (np.abs(res) <= 3 * sd)
    res = off - A @ coef
    rng = np.random.default_rng(0)
    blocks = [np.arange(i, min(i + BLOCK, len(off))) for i in range(0, len(off), BLOCK)]
    bs = []
    for _ in range(400):
        idx = np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))])
        idx = idx[keep[idx]]
        if len(idx) > 3:
            bs.append(np.linalg.lstsq(A[idx], off[idx], rcond=None)[0])
    bs = np.array(bs)
    shift = coef[1:]
    mag = float(np.hypot(*shift))
    return {"stations": int(len(off)), "with_feature": int(ok.sum()), "used": int(keep.sum()),
            "shift_en_m": [round(float(shift[0]), 3), round(float(shift[1]), 3)], "shift_m": round(mag, 3),
            "shift_sd_en_m": [round(float(bs[:, 1].std()), 3), round(float(bs[:, 2].std()), 3)],
            "edge_definition_bias_m": round(float(coef[0]), 3),
            "residual_m": {"rms": round(float(np.sqrt(np.mean(res[keep] ** 2))), 3),
                           "p50_abs": round(float(np.percentile(np.abs(res[keep]), 50)), 3),
                           "p95_abs": round(float(np.percentile(np.abs(res[keep]), 95)), 3)},
            "pixel_m": round(gsd_m, 3), "apply": bool(mag >= gsd_m)}
