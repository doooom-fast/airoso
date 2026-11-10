"""Nevada Nights' native scrub as measured plants (ledger 0089): every shrub clump NAIP shows inside the scrub polygon in
BOTH 2019 and 2022, at its 2019 position, with its crown. Writes source/vegetation/scrub.naip.json, the points
tools/make_treefx.py plants (scenery.treefx.planted): [lon, lat, cell, h_m, crown_m, key].

  python tracks/exotics-racing-lv-lm/source/vegetation/scripts/plan_scrub_naip.py tracks/exotics-racing-lv-lm

THE IMAGES: USDA NAIP 0.6 m, EPSG:4326 crops off the Microsoft Planetary Computer data API (public domain), saved beside
this script: naip_2019_060.png (nv_m_3611548_se_11_060_20190706) and naip_2022_060.png (nv_m_3611548_se_11_060_20220611),
the same box. THE POLYGON: the strip north of the lap that 0.1.3's SCRUBCARD scatter used (DOSSIER section 6: native
scrub only beyond the campus edge), kept as written: only the cards' own ground is planted.

MEASURED, per year: luminance under a 9 m median background; a clump = a connected run of pixels darker than that by
K_MAD robust spreads, 2 px to 12 m2. A clump is a PLANT only when the other year has one within MATCH_M of it after the
two years' registration shift (the median nearest-clump offset over the whole crop): JPEG noise, cars and shadows do
not repeat; shrubs do. Crown = the mean of the two years' area-equivalent diameters (the blob holds the plant and part
of its shadow: an upper bound). NOT MEASURED: height. Creosote here stands about 1-2 m (DOSSIER section 6, USDA ESD
R030XB005NV; the species is 1-3 m): each clump takes a height in H_RANGE_M by its crown's rank (the widest the tallest).
White bursage (low, pale, 0.3-0.8 m) is below what 0.6 m NAIP separates from the caliche: none is planted.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

K_MAD = 4.0            # [invented] darker than the 9 m background by this many robust spreads
BG_M = 9.0             # the background window
AREA_MAX_M2 = 12.0     # a clump bigger than this is not one shrub
MATCH_M = 1.0          # the two years' clumps agree within this (one 0.6 m pixel plus the residual)
H_RANGE_M = (1.0, 2.0) # creosote's height here (DOSSIER section 6): NOT measured, ranked by the measured crown


def blobs(png: Path, meta: dict):
    im = np.asarray(Image.open(png).convert("RGB")).astype(float)
    mpp = meta["m_per_px"][0]
    L = im.mean(axis=2)
    win = max(5, int(round(BG_M / mpp)) | 1)
    d = ndi.median_filter(L, size=win) - L
    mad = ndi.median_filter(np.abs(d), size=win) * 1.4826 + 1e-6
    mask = d > K_MAD * mad
    lab, n = ndi.label(mask)
    idx = np.arange(1, n + 1)
    area = ndi.sum(mask, lab, idx)
    com = ndi.center_of_mass(mask, lab, idx)
    w0, n0, e0, s0 = meta["corners"]
    H, W = L.shape
    out = []
    for a, (cy, cx) in zip(area, com):
        if a < 2 or a * mpp * mpp > AREA_MAX_M2:
            continue
        out.append((w0 + (cx + 0.5) / W * (e0 - w0), n0 - (cy + 0.5) / H * (n0 - s0), 2 * math.sqrt(a / math.pi) * mpp))
    return out


def inside(poly, lon, lat):
    ins = False
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (a[1] > lat) != (b[1] > lat) and lon < a[0] + (lat - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
            ins = not ins
    return ins


def main(proj: Path):
    here = Path(__file__).resolve().parents[1]
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    poly = cfg["scenery"]["treefx"]["planted"]["polygon_lonlat"]
    yrs = {}
    for y in ("2019", "2022"):
        meta = json.loads((here / f"naip_{y}_060.json").read_text(encoding="utf-8"))
        yrs[y] = blobs(here / f"naip_{y}_060.png", meta)
    lat0 = sum(p[1] for p in poly) / len(poly)
    mx = 111_412.84 * math.cos(math.radians(lat0)) - 93.5 * math.cos(3 * math.radians(lat0))
    my = 111_132.92 - 559.82 * math.cos(2 * math.radians(lat0))
    A = np.array([[b[0] * mx, b[1] * my] for b in yrs["2019"]])
    B = np.array([[b[0] * mx, b[1] * my] for b in yrs["2022"]])
    offs = []
    for p in A:
        v = B[np.argmin(((B - p) ** 2).sum(1))] - p
        if math.hypot(*v) < 3.0:
            offs.append(v)
    shift = np.median(np.array(offs), axis=0)
    a_in = [i for i, b in enumerate(yrs["2019"]) if inside(poly, b[0], b[1])]
    b_in = [j for j, b in enumerate(yrs["2022"]) if inside(poly, b[0], b[1])]
    used, pairs = set(), []
    for i in a_in:
        best = None
        for j in b_in:
            if j in used:
                continue
            dd = math.hypot(*(B[j] - A[i] - shift))
            if dd <= MATCH_M and (best is None or dd < best[0]):
                best = (dd, j)
        if best:
            used.add(best[1])
            pairs.append((i, best[1], best[0]))
    crowns = [(yrs["2019"][i][2] + yrs["2022"][j][2]) / 2 for i, j, _ in pairs]
    order = sorted(range(len(pairs)), key=lambda k: crowns[k])
    rank = {k: r for r, k in enumerate(order)}
    lo, hi = H_RANGE_M
    pts = []
    for k, (i, j, dd) in enumerate(pairs):
        lon, lat, _ = yrs["2019"][i]
        h = lo + (hi - lo) * rank[k] / max(len(pairs) - 1, 1)
        pts.append([round(lon, 7), round(lat, 7), 0, round(h, 2), round(crowns[k], 2), k])
    doc = {
        "_source": ("USDA NAIP 0.6 m 2019-07-06 + 2022-06-11 (source/vegetation/naip_{2019,2022}_060.png, Planetary Computer, "
                    "public domain); scripts/plan_scrub_naip.py. POSITIONS and CROWNS MEASURED: a dark clump inside the "
                    "scrub polygon that both years show within %.1f m (after the years' registration shift E %.2f / N %.2f m). "
                    "HEIGHTS NOT MEASURED: creosote's %.1f-%.1f m here (DOSSIER section 6), ranked by the measured crown. "
                    "Bursage below NAIP's resolution: not planted." % (MATCH_M, shift[0], shift[1], lo, hi)),
        "counts": {"clumps_2019_in_polygon": len(a_in), "clumps_2022_in_polygon": len(b_in), "in_both": len(pairs)},
        "crown_m_p10_p50_p90": [round(float(np.percentile(crowns, q)), 2) for q in (10, 50, 90)] if crowns else [],
        "cols": 1, "rows": 1,
        "points": pts,
    }
    out = here / "scrub.naip.json"
    out.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"[scrub] 2019 {len(a_in)} / 2022 {len(b_in)} clumps in the polygon; {len(pairs)} in both -> {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
