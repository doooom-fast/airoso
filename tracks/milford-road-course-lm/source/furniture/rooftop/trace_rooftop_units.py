"""Milford's rooftop units, traced off NAIP 2022 (ledger 0094; the audit's "light rooftop boxes of about 5-10 m").

    /path/to/venv/python source/furniture/rooftop/trace_rooftop_units.py <track-dir>      (numpy, scipy, Pillow)

Reads the track's own photograph (source/road_wear/naip_2022_mrc.jpg on its true extent, data/road_wear.json's aerial bbox)
and the footprints of the blocks it covers (track.config.json's inline blocks, source/furniture/pass3/blocks.json; pass 4's
roofs lie west of the photograph). Inside each footprint, 4 px clear of its edge:

  (both)  a blob longer than MAX_ASPECT times its width along the footprint's axes is a roof line, not a unit
  bright  a unit is a blob BRIGHTER than the roof round it (its 21 px median) by MIN_BRIGHT, MIN_AREA_PX..MAX_AREA_PX, its
          bounding box no more than 4:1, with a shadow (MIN_SHADOW darker than the roof) within SHADOW_PX of it on the
          shadow side (north-west on this photograph: the units' and the walls' shadows fall there)
  blue    on a white membrane roof the big units read darker and bluer than the roof (their tops are not white): blue - red
          over the roof's median by MIN_BLUE and luminance under it by MIN_DARK but not by MAX_DARK (that is their shadow),
          closed by 2 px, MIN_AREA_BLUE..MAX_AREA_BLUE

Each unit is the blob's extent along the footprint's own axes (the minimum-area box's long side), in metres; its HEIGHT is
[invented] (H_BIG_M for a blue unit, H_SMALL_M for a bright one: a packaged rooftop unit stands 1-2 m, cited from memory);
the 2017 lidar the G10 read could measure it (pass 3's 2 m roof cells do not resolve a unit). Writes rooftop_units.json
(per block key, the author's "rooftop_units" rows) and rooftop_units_on_naip.jpg (every unit drawn on the photograph, L12).
Every threshold here is [invented], tuned by eye on these five roofs.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

MIN_BRIGHT, MIN_AREA_PX, MAX_AREA_PX = 16.0, 6, 120
MIN_SHADOW, SHADOW_PX = 18.0, 4
MIN_BLUE, MIN_DARK, MAX_DARK, MIN_AREA_BLUE, MAX_AREA_BLUE = 9.0, 8.0, 70.0, 40, 900
H_BIG_M, H_SMALL_M = 1.5, 1.0
MIN_SIDE_M = 1.5
MAX_ASPECT = 3.0                 # a longer blob is a roof line, not a unit
SHEET_BOX = (0, 300, 1000, 2300)  # the photograph's pixels the evidence sheet keeps: the five roofs
MODE = {"mpg_plant_a": "blue", "mpg_plant_b": "bright", "mpg_west_bldg_a": "bright", "mpg_west_bldg_c": "bright",
        "mpg_nw_small": "bright", "pad_shed_north": None, "pad_shed_south": None}


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def inpoly(r, X, Y):
    c = np.zeros(X.shape, bool)
    for i in range(len(r)):
        (ax, ay), (bx, by) = r[i], r[(i + 1) % len(r)]
        cond = (ay > Y) != (by > Y)
        xi = ax + (Y - ay) * (bx - ax) / ((by - ay) if by != ay else 1e-9)
        c ^= cond & (X < xi)
    return c


def main(track: Path) -> int:
    cfg = json.loads((track / "track.config.json").read_text(encoding="utf-8"))
    aer = json.loads((track / "data" / "road_wear.json").read_text(encoding="utf-8"))["spec"]["aerial"]
    img = np.asarray(Image.open(track / aer["image"]).convert("RGB")).astype(float)
    W, S, E, N = aer["bbox_lonlat"]
    h, w = img.shape[:2]
    lum = img.mean(axis=2)
    rows = [g for g in cfg["scenery"]["bespoke"]["blocks"] if not g.get("file")]
    rows += json.loads((track / "source/furniture/pass3/blocks.json").read_text(encoding="utf-8"))
    out, sheet = {}, Image.fromarray(img.astype(np.uint8))
    dr = ImageDraw.Draw(sheet)
    for b in rows:
        mode = MODE.get(b["key"])
        ring = b["footprint_lonlat"]
        r = [((lo - W) / (E - W) * w, (N - la) / (N - S) * h) for lo, la in ring]
        if mode is None or min(p[0] for p in r) < 0 or max(p[0] for p in r) > w or min(p[1] for p in r) < 0 or max(p[1] for p in r) > h:
            continue
        lat0 = sum(p[1] for p in ring) / len(ring)
        mlon, mlat = mpd(lat0)
        # the footprint's long axis, in metres east / north
        best = None
        for i in range(len(ring)):
            a, c = ring[i], ring[(i + 1) % len(ring)]
            ex, ey = (c[0] - a[0]) * mlon, (c[1] - a[1]) * mlat
            ln = math.hypot(ex, ey)
            if best is None or ln > best[0]:
                best = (ln, ex / ln, ey / ln)
        _, ux, uy = best
        yaw = math.degrees(math.atan2(uy, ux))
        x0, x1 = int(min(p[0] for p in r)), int(max(p[0] for p in r)) + 1
        y0, y1 = int(min(p[1] for p in r)), int(max(p[1] for p in r)) + 1
        yy, xx = np.mgrid[y0:y1, x0:x1]
        m = ndi.binary_erosion(inpoly(r, xx + 0.5, yy + 0.5), iterations=4)
        C, L = img[y0:y1, x0:x1], lum[y0:y1, x0:x1]
        bg = ndi.median_filter(L, size=21)
        if mode == "blue":
            bl = C[..., 2] - C[..., 0]
            cand = (m & (bl > np.median(bl[m]) + MIN_BLUE) & (L < np.median(L[m]) - MIN_DARK)
                    & (L > np.median(L[m]) - MAX_DARK))
            cand = ndi.binary_opening(ndi.binary_closing(cand, iterations=2), iterations=1)
            amin, amax = MIN_AREA_BLUE, MAX_AREA_BLUE
        else:
            cand = m & (L - bg > MIN_BRIGHT)
            amin, amax = MIN_AREA_PX, MAX_AREA_PX
        dark = (L - bg) < -MIN_SHADOW
        lab, k = ndi.label(cand)
        units = []
        for i in range(1, k + 1):
            q = lab == i
            a = int(q.sum())
            if a < amin or a > amax:
                continue
            yi, xi = np.nonzero(q)
            bw, bh = xi.max() - xi.min() + 1, yi.max() - yi.min() + 1
            if max(bw, bh) / min(bw, bh) > 4:
                continue
            if mode == "bright":
                sx0, sy0 = max(0, xi.min() - SHADOW_PX), max(0, yi.min() - SHADOW_PX)
                if not dark[sy0:yi.min() + 1, sx0:xi.max() + 1].any() and not dark[sy0:yi.max() + 1, sx0:xi.min() + 1].any():
                    continue
            # the blob in metres east / north of its own centre, along the footprint's axes
            lon = W + (xi + x0 + 0.5) / w * (E - W)
            lat = N - (yi + y0 + 0.5) / h * (N - S)
            clon, clat = float(lon.mean()), float(lat.mean())
            ex, ey = (lon - clon) * mlon, (lat - clat) * mlat
            pu, pv = ex * ux + ey * uy, -ex * uy + ey * ux
            px_m = 0.5 * ((E - W) / w * mlon + (N - S) / h * mlat)
            # the 5-95 % spread (a blob's tail along a roof line is not the unit), one pixel wider
            wu = max(MIN_SIDE_M, float(np.percentile(pu, 95) - np.percentile(pu, 5)) + px_m)
            dv = max(MIN_SIDE_M, float(np.percentile(pv, 95) - np.percentile(pv, 5)) + px_m)
            if max(wu, dv) / min(wu, dv) > MAX_ASPECT:
                continue
            units.append({"lonlat": [round(clon, 7), round(clat, 7)], "w_m": round(wu, 1), "d_m": round(dv, 1),
                          "h_m": H_BIG_M if mode == "blue" else H_SMALL_M, "yaw_deg": round(yaw, 1),
                          "_source": f"NAIP 2022 ({mode} blob, {a} px); height [invented]"})
            for x_, y_ in zip(xi + x0, yi + y0):
                dr.point((int(x_), int(y_)), fill=(255, 0, 255) if mode == "blue" else (0, 220, 255))
        out[b["key"]] = units
        print(f"[rtu] {b['key']}: {len(units)} units ({mode})")
    (track / "source/furniture/rooftop").mkdir(parents=True, exist_ok=True)
    (track / "source/furniture/rooftop/rooftop_units.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    sheet.crop(SHEET_BOX).save(track / "source/furniture/rooftop/rooftop_units_on_naip.jpg", quality=85)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
