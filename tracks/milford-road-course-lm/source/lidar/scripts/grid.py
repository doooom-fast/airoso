"""Rasterise the kept returns to a CELL grid in the local frame: ground intensity (mean), ground z (mean), and counts of
non-ground returns per height-over-ground band. Writes grid.npz and an overview PNG with the inventory drawn on it.
python -I grid.py pts.npz hag.npz inventory.json out_prefix [cell]"""
import json, math, sys
import numpy as np
from PIL import Image, ImageDraw

pts = np.load(sys.argv[1]); hag = np.load(sys.argv[2])["hag"]; inv = json.load(open(sys.argv[3])); outp = sys.argv[4]
CELL = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
LAT0, LON0 = 42.56999810653583, -83.66362827905016
phi = math.radians(LAT0)
m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
e, n, z, cls, I = pts["e"], pts["n"], pts["z"], pts["cls"], pts["inten"].astype(float)
ok = ~np.isin(cls, (7, 18))
e0, n0 = math.floor(e.min()), math.floor(n.min())
nx, ny = int((e.max() - e0) / CELL) + 1, int((n.max() - n0) / CELL) + 1
ix = ((e - e0) / CELL).astype(int); iy = ((n - n0) / CELL).astype(int)
lin = iy * nx + ix
g = ok & (cls == 2)
cnt_g = np.bincount(lin[g], minlength=nx * ny)
gi = np.bincount(lin[g], I[g], minlength=nx * ny) / np.maximum(cnt_g, 1)
gz = np.bincount(lin[g], z[g], minlength=nx * ny) / np.maximum(cnt_g, 1)
ng = ok & (cls != 2)
bands = {"b035_130": (0.35, 1.3), "b130_300": (1.3, 3.0), "b300_800": (3.0, 8.0), "b800": (8.0, 99)}
out = {"e0": e0, "n0": n0, "cell": CELL, "nx": nx, "ny": ny,
       "ground_n": cnt_g.reshape(ny, nx).astype(np.uint16), "ground_int": gi.reshape(ny, nx).astype(np.float32),
       "ground_z": np.where(cnt_g > 0, gz, np.nan).reshape(ny, nx).astype(np.float32)}
for k, (a, b) in bands.items():
    m = ng & (hag >= a) & (hag < b)
    out[k] = np.bincount(lin[m], minlength=nx * ny).reshape(ny, nx).astype(np.uint16)
np.savez_compressed(outp + "_grid.npz", **out)
# picture: grey = ground intensity, red = 0.35-1.3, orange = 1.3-3, yellow = 3-8, green = >8 m
gi2 = out["ground_int"]; v = gi2[cnt_g.reshape(ny, nx) > 0]
lo, hi = np.percentile(v, 2), np.percentile(v, 98)
grey = np.clip((gi2 - lo) / (hi - lo + 1e-9), 0, 1) * 200
img = np.stack([grey] * 3, -1)
for k, col in (("b800", (40, 140, 40)), ("b300_800", (230, 220, 0)), ("b130_300", (255, 140, 0)), ("b035_130", (255, 0, 0))):
    img[out[k] > 0] = col
img = img[::-1].astype(np.uint8)
im = Image.fromarray(img); d = ImageDraw.Draw(im)
for it in inv["items"]:
    ll = it.get("polyline_lonlat") or it.get("footprint_lonlat")
    xy = [(((lo_ - LON0) * m_lon - e0) / CELL, ny - 1 - ((la_ - LAT0) * m_lat - n0) / CELL) for lo_, la_ in ll]
    if "footprint_lonlat" in it:
        xy.append(xy[0])
    d.line(xy, fill=(0, 160, 255), width=1)
    d.text((xy[0][0] + 4, xy[0][1]), it["id"], fill=(0, 200, 255))
im.save(outp + "_overview.png")
print("grid", nx, ny, "cells", nx * ny, "->", outp + "_overview.png")
