"""Ledger 0082 pass 4, download b: the 2017 lidar roofs west of the NAIP crop on disk against NAIP 2022's strip west of it.
Per candidate: the strip's median green excess and luminance over its roof cells, and a crop (strip left, lidar right).
    python -I strip_check.py <strip.png> <bldAll.json> <tiers.json> <veg.npz> <out_dir>"""
import json, math, sys
import numpy as np
from PIL import Image, ImageDraw
strip, bld, tiers, veg, out = sys.argv[1:6]
O = dict(lon=-83.66362827905016, lat=42.56999810653583); MLON, MLAT = 82107.23577351798, 111084.36697075465
W0, S0, E0_, N0_ = -83.6720, 42.56050328638498, -83.6700, 42.57949671361502
A = np.asarray(Image.open(strip).convert("RGB")).astype(float); H, Wd = A.shape[:2]
def px(e, n):
    lon = O["lon"] + e / MLON; lat = O["lat"] + n / MLAT
    return (lon - W0) / (E0_ - W0) * Wd, (N0_ - lat) / (N0_ - S0) * H
d = np.load(veg); chm = d["chm"]; GE = -1400
B = {b["id"]: b for b in json.load(open(bld))}; lab = np.load(bld.replace(".json", "_lab.npy"))
T = json.load(open(tiers))
cands = [(i, f"roof {i}", None) for i in (21, 53, 57, 58, 59, 77, 79, 81)] + [(40, "hall b annex", next(t for t in T if t["src"] == 40 and t["area_m2"] == 1480))]
def inside(poly, x, y):
    c = np.zeros(len(x), bool)
    for (ax, ay), (bx, by) in zip(poly, np.roll(poly, -1, 0)):
        m = (ay > y) != (by > y)
        c ^= m & (x < (bx - ax) * (y - ay) / np.where(by - ay == 0, 1e-12, by - ay) + ax)
    return c


rows = []
for i, name, tier in cands:
    jj, ii = np.nonzero(lab == i); ee = GE + 2 * ii + 1.0; nn = GE + 2 * jj + 1.0
    if tier:
        k = inside(np.array(tier["corners_en"]), ee, nn); ee, nn = ee[k], nn[k]
    x, y = px(ee, nn); ok = (x >= 0) & (x < Wd) & (y >= 0) & (y < H)
    r = {"id": i, "name": name, "cells": int(len(ee)), "in_strip": round(float(ok.mean()), 2), "e": round(float(ee.mean()), 1), "n": round(float(nn.mean()), 1)}
    if ok.sum():
        rgb = A[y[ok].astype(int), x[ok].astype(int)]
        r["green_excess_p50"] = round(float(np.median(rgb[:, 1] - (rgb[:, 0] + rgb[:, 2]) / 2)), 1)
        r["lum_p50"] = round(float(np.median(rgb.mean(1))), 0)
        r["lum_sd"] = round(float(np.std(rgb.mean(1))), 1)
    # crop
    e0, e1, n0, n1 = ee.min() - 25, ee.max() + 25, nn.min() - 25, nn.max() + 25; sc = 3
    w, h = int((e1 - e0) * sc), int((n1 - n0) * sc)
    E, N = np.meshgrid(np.linspace(e0, e1, w), np.linspace(n1, n0, h)); X, Y = px(E, N)
    inn = (X >= 0) & (X < Wd) & (Y >= 0) & (Y < H)
    L = np.zeros((h, w, 3), np.uint8); L[inn] = A[Y[inn].astype(int), X[inn].astype(int)]
    hc = chm[np.clip((N - GE).astype(int), 0, chm.shape[0] - 1), np.clip((E - GE).astype(int), 0, chm.shape[1] - 1)]
    R = np.clip(hc * 15, 0, 255).astype(np.uint8); R = np.stack([R, R, R], -1)
    im = Image.fromarray(np.concatenate([L, R], 1)); dr = ImageDraw.Draw(im)
    if tier:
        for off in (0, w):
            dr.polygon([(off + (a - e0) * sc, (n1 - b) * sc) for a, b in tier["corners_en"]], outline=(255, 0, 255))
    im.save(f"{out}/strip_{i}_{name.replace(' ', '_')}.jpg", quality=85)
    rows.append(r); print(r)
json.dump(rows, open(f"{out}/strip_check.json", "w"), indent=1)
