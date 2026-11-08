"""Ledger 0082 vegetation pass: read EVERY return in the 71 EPT nodes already on disk (pass 2's fetch; nothing is
downloaded here) into the port's local frame, and write 1 m grids for the vegetation inventory. Run with -I.

    python -I veg_read.py <centerline.local.json> <DL dir> <OUT.npz>

Pass 2 kept only the returns within the lane edge + 45 m. The shallower nodes it fetched cover far more ground at a
lower density, so this read keeps everything inside HALF_M of the origin and records the density per cell, so every
measurement downstream can say how many returns it rests on.

Grids (1 m, local E / N metres about the centreline's origin; cell (j, i) is e = E0 + i + 0.5, n = N0 + j + 0.5):
  g_med    median class-2 (ground) height per cell, NaN where none
  g_fill   g_med with the holes filled (linear from the cells that have ground, nearest at the rim)
  gdist    metres to the nearest cell holding a ground return
  n_g      ground returns per cell
  n_all    all returns per cell (noise and water excluded)
  n_first  first returns per cell
  chm      max height over g_fill of the non-ground returns (class 1 and any 3/4/5) per cell, 0 where none
  chm_p95  ... the p95 of the cell's non-ground returns over 0.5 m
  n_veg    non-ground returns over 0.5 m per cell
  multi    share of the cell's FIRST returns over 2 m that have more returns after them (nr > 1): a crown lets the pulse
           through, a roof or a wall top does not
  inten_g  mean intensity of the ground returns per cell (paved / gravel / grass differ)
  low      non-ground returns 0.15-0.5 m over the ground per cell (tall grass, stubble, low scrub)
  h_band   counts per band 0.5-2 / 2-5 / 5-10 / 10-20 / 20+ m
Also <OUT>_canopy.npz: every non-ground return over 2 m (e, n, hag, rn, nr), for per-crown statistics.
"""
import json, math, sys
from pathlib import Path

import laspy
import numpy as np
from pyproj import Transformer
from scipy.interpolate import griddata
from scipy.ndimage import distance_transform_edt

cl_path, DL, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
HALF_M = 1400.0
plan = json.loads((DL / "plan.json").read_text())


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


o = json.loads(cl_path.read_text())["origin"]
m_lon, m_lat = mpd(o["lat"])
to_ll = Transformer.from_crs(3857, 4326, always_xy=True)
chunks, per_node = [], []
for key, npts, size in plan["nodes"]:
    f = DL / "ept-data" / f"{key}.laz"
    if not f.exists() or f.stat().st_size != size:
        raise SystemExit(f"{f} missing or not {size} B: this read never downloads")
    las = laspy.read(str(f))
    lon, lat = to_ll.transform(np.asarray(las.x), np.asarray(las.y))
    e = (lon - o["lon"]) * m_lon
    n = (lat - o["lat"]) * m_lat
    k = (np.abs(e) < HALF_M) & (np.abs(n) < HALF_M)
    cls = np.asarray(las.classification)
    chunks.append(np.c_[e[k], n[k], np.asarray(las.z)[k], cls[k], np.asarray(las.return_number)[k],
                        np.asarray(las.number_of_returns)[k], np.asarray(las.intensity)[k]].astype(np.float64))
    per_node.append([key, int(len(e)), int(k.sum())])
A = np.concatenate(chunks)
del chunks
e, n, z, cls, rn, nr, it = (A[:, c] for c in range(7))
print(f"returns kept: {len(e):,}; classes {dict(zip(*[x.tolist() for x in np.unique(cls, return_counts=True)]))}", flush=True)
ok = (cls != 7) & (cls != 9) & (cls != 18)
E0, N0 = math.floor(e.min()), math.floor(n.min())
nx, ny = int(math.ceil(e.max() - E0)) + 1, int(math.ceil(n.max() - N0)) + 1
ii = np.clip((e - E0).astype(int), 0, nx - 1)
jj = np.clip((n - N0).astype(int), 0, ny - 1)
flat = jj * nx + ii
NC = nx * ny


def count(mask):
    return np.bincount(flat[mask], minlength=NC).reshape(ny, nx).astype(np.int32)


gm = ok & (cls == 2)
# median ground per cell: sort by (cell, z) and take the middle element(s)
order = np.lexsort((z[gm], flat[gm]))
fc, zc = flat[gm][order], z[gm][order]
g_med = np.full(NC, np.nan)
starts = np.r_[0, np.flatnonzero(np.diff(fc)) + 1]
ends = np.r_[starts[1:], len(fc)]
g_med[fc[starts]] = 0.5 * (zc[(starts + ends - 1) // 2] + zc[(starts + ends) // 2])
g_med = g_med.reshape(ny, nx)
have = np.isfinite(g_med)
print(f"grid {nx} x {ny}, cells with ground {have.sum():,} ({100 * have.mean():.1f} %)", flush=True)
# fill: linear over every second known cell (fast), the exact cells kept, nearest at the rim
J, I = np.nonzero(have)
sel = ((J % 2) == 0) & ((I % 2) == 0)
gy, gx = np.mgrid[0:ny, 0:nx]
lin = griddata(np.c_[I[sel], J[sel]], g_med[J[sel], I[sel]], (gx, gy), method="linear")
g_fill = np.where(have, g_med, lin)
hole = ~np.isfinite(g_fill)
if hole.any():
    _, (nj, ni) = distance_transform_edt(hole, return_indices=True)
    g_fill = g_fill[nj, ni]
gdist = distance_transform_edt(~have)
# height over ground of every return, bilinear on g_fill
fx, fy = e - E0 - 0.5, n - N0 - 0.5
i0 = np.clip(np.floor(fx).astype(int), 0, nx - 2)
j0 = np.clip(np.floor(fy).astype(int), 0, ny - 2)
tx, ty = np.clip(fx - i0, 0, 1), np.clip(fy - j0, 0, 1)
gz = (g_fill[j0, i0] * (1 - tx) * (1 - ty) + g_fill[j0, i0 + 1] * tx * (1 - ty)
      + g_fill[j0 + 1, i0] * (1 - tx) * ty + g_fill[j0 + 1, i0 + 1] * tx * ty)
hag = z - gz
veg = ok & (cls != 2)
chm = np.zeros(NC)
np.maximum.at(chm, flat[veg], np.maximum(hag[veg], 0.0))
chm = chm.reshape(ny, nx)
vm = veg & (hag > 0.5)
order = np.lexsort((hag[vm], flat[vm]))
fc, hc = flat[vm][order], hag[vm][order]
chm_p95 = np.zeros(NC)
if len(fc):
    starts = np.r_[0, np.flatnonzero(np.diff(fc)) + 1]
    ends = np.r_[starts[1:], len(fc)]
    chm_p95[fc[starts]] = hc[starts + np.floor(0.95 * (ends - starts - 1)).astype(int)]
chm_p95 = chm_p95.reshape(ny, nx)
first_hi = ok & (rn == 1) & (hag > 2.0) & (cls != 2)
n_fhi = count(first_hi)
n_fhi_multi = count(first_hi & (nr > 1))
multi = np.where(n_fhi > 0, n_fhi_multi / np.maximum(n_fhi, 1), np.nan).astype(np.float32)
n_g = count(gm)
isum = np.bincount(flat[gm], weights=it[gm], minlength=NC).reshape(ny, nx)
inten_g = np.where(n_g > 0, isum / np.maximum(n_g, 1), np.nan).astype(np.float32)
bands = [0.5, 2, 5, 10, 20, 1e9]
h_band = np.stack([count(veg & (hag >= a) & (hag < b)) for a, b in zip(bands, bands[1:])])
np.savez_compressed(OUT, E0=E0, N0=N0, origin=json.dumps(o),
                    g_med=g_med.astype(np.float32), g_fill=g_fill.astype(np.float32), gdist=gdist.astype(np.float32),
                    n_g=n_g, n_all=count(ok), n_first=count(ok & (rn == 1)), chm=chm.astype(np.float32),
                    chm_p95=chm_p95.astype(np.float32), n_veg=count(veg & (hag > 0.5)), multi=multi, inten_g=inten_g,
                    low=count(veg & (hag >= 0.15) & (hag < 0.5)), h_band=h_band.astype(np.int32),
                    per_node=json.dumps(per_node))
cm = veg & (hag > 2.0)
np.savez_compressed(OUT.with_name(OUT.stem + "_canopy.npz"), e=e[cm].astype(np.float32), n=n[cm].astype(np.float32),
                    hag=hag[cm].astype(np.float32), rn=rn[cm].astype(np.uint8), nr=nr[cm].astype(np.uint8),
                    E0=E0, N0=N0)
summ = {"nodes": len(plan["nodes"]), "returns_kept": int(len(e)), "half_m": HALF_M, "grid": [nx, ny], "E0": E0, "N0": N0,
        "cells_with_ground_pct": round(100 * float(have.mean()), 2), "canopy_returns_over_2m": int(cm.sum()),
        "classes": {int(c): int(k) for c, k in zip(*np.unique(cls, return_counts=True))}}
print(json.dumps(summ, indent=1))
OUT.with_suffix(".summary.json").write_text(json.dumps(summ, indent=1))
