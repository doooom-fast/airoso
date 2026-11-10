"""Standing objects in a lidar extract (ledger 0089): a 0.5 m grid of the highest return over the 1 m class-2 ground;
cells over LO_M joined 8-connected into objects; each object's top (max height), footprint (area-equivalent diameter of
the joined cells) and centroid (lon, lat). An object of fewer than MIN_PTS returns over LO_M is a speck (a bird, a
multipath echo), not a plant. Objects taller than HI_M or wider than WIDE_M are structures, not plants."""
import json, math, sys
import numpy as np
from scipy import ndimage as ndi
sys.path.insert(0, sys.argv[0].rsplit("/", 1)[0])
import hag
CELL = 0.5
def objects(npz, lat0, LO_M=0.3, HI_M=4.0, WIDE_M=6.0, MIN_PTS=3, inside=None):
    P = hag.load(npz, lat0)
    keep = (P["C"] != 7) & (P["C"] != 18)           # noise / high noise (birds, multipath) out
    X, Y, H = P["X"][keep], P["Y"][keep], P["HAG"][keep]
    nx, ny = int(X.max() / CELL) + 1, int(Y.max() / CELL) + 1
    g = np.zeros((ny, nx))
    cnt = np.zeros((ny, nx), int)
    iy, ix = (Y / CELL).astype(int), (X / CELL).astype(int)
    np.maximum.at(g, (iy, ix), H)
    np.add.at(cnt, (iy[H > LO_M], ix[H > LO_M]), 1)
    lab, n = ndi.label(g > LO_M, structure=np.ones((3, 3)))
    out = []
    for k, sl in enumerate(ndi.find_objects(lab), start=1):
        m = lab[sl] == k
        top = float(g[sl][m].max())
        area = m.sum() * CELL * CELL
        d = 2 * math.sqrt(area / math.pi)
        jj, ii = np.nonzero(m)
        cx, cy = (ii.mean() + sl[1].start + 0.5) * CELL, (jj.mean() + sl[0].start + 0.5) * CELL
        lon, lat = P["to_lonlat"](cx, cy)
        if inside is not None and not inside(lon, lat):
            continue
        npts = int(cnt[sl][m].sum())
        kind = "structure" if (top > HI_M or d > WIDE_M) else ("plant" if npts >= MIN_PTS else "speck")
        out.append({"lon": round(lon, 7), "lat": round(lat, 7), "top_m": round(top, 2), "foot_m": round(d, 2), "cells": int(m.sum()), "points": npts, "kind": kind})
    return out, P
