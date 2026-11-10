"""PPIR's infield ground off the 2018 lidar, against the build's ground grid, and every measured infield piece's
profile (ledger 0085 owed: "the infield ground (40 m 3DEP grid now)").

    python infield_ground.py <workshop> <infield.npz> <out_dir>

  - DEM: class-2 points binned to CELL_M cells (median), holes filled linearly inside the points' hull, then nearest;
    written to <out_dir>/infield_dem.npz (not committed; ~6 MB).
  - Against the build: the workshop's data/heightfield.npy (pikes-peak-lm 0.1.0: 20 m, bilinear from the 40 m 3DEP
    grid) sampled bilinearly at each DEM cell; differences inside the oval's measured inside edge.
  - Each piece in ../../road-course/infield_pieces.naip.json and RC-D's lot band (route_from_maps.naip.json): along its
    centre line every 1 m, the DEM height, grade, the cross-slope (a line through the ground points across the piece's
    own width minus 0.5 m a side, +-1 m along), and the build grid's error under it.
Heights are the build's y (lidar z minus the origin's elev_m 1634.84). Slopes in %; cross + = left of the piece's own
direction higher. Only the measurement; nothing here changes a build.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.interpolate import griddata
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
RC = HERE.parents[1] / "road-course"
ELEV0 = 1634.84
CELL_M = 1.0                # [invented] ~1.9 ground pts/m2: most 1 m cells hold one or two returns
ALONG_M = 1.0               # [invented]
MIN_PTS = 8                 # [invented]


def mpd(lat0):
    import math
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def heightfield_sampler(ws: Path, lon0: float, lat0: float):
    h = np.load(ws / "data/heightfield.npy")
    m = json.loads((ws / "data/heightfield.meta.json").read_text(encoding="utf-8"))
    s, w, n, e = m["bbox_swne"]
    ny, nx = h.shape
    m_lon, m_lat = mpd(lat0)

    def f(E, N):
        lon = lon0 + np.asarray(E) / m_lon; lat = lat0 + np.asarray(N) / m_lat
        fx = (lon - w) / (e - w) * (nx - 1)
        fy = (n - lat) / (n - s) * (ny - 1) if m.get("row0", "north") == "north" else (lat - s) / (n - s) * (ny - 1)
        x0 = np.clip(np.floor(fx).astype(int), 0, nx - 2); y0 = np.clip(np.floor(fy).astype(int), 0, ny - 2)
        tx = np.clip(fx - x0, 0, 1); ty = np.clip(fy - y0, 0, 1)
        v = (h[y0, x0] * (1 - tx) * (1 - ty) + h[y0, x0 + 1] * tx * (1 - ty)
             + h[y0 + 1, x0] * (1 - tx) * ty + h[y0 + 1, x0 + 1] * tx * ty)
        return v - ELEV0
    return f


def resample(P, step=1.0):
    P = np.asarray(P, float)
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    t = np.arange(0, s[-1] + 1e-9, step)
    return np.c_[np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])], t


def fit_line(x, z):
    if len(x) < MIN_PTS or np.ptp(x) < 2.0:
        return None
    A = np.c_[np.ones_like(x), x]
    keep = np.ones(len(x), bool)
    for _ in range(3):
        c, *_ = np.linalg.lstsq(A[keep], z[keep], rcond=None)
        r = z - A @ c; sd = np.std(r[keep])
        nk = np.abs(r) <= max(3 * sd, 0.03)
        if (nk == keep).all():
            break
        keep = nk
    c, *_ = np.linalg.lstsq(A[keep], z[keep], rcond=None)
    return float(c[1]), float(np.std(z[keep] - A[keep] @ c)), int(keep.sum())


def in_poly(poly, X, Y):
    """Even-odd ray test of every (X, Y) against a closed polygon (numpy only)."""
    inside = np.zeros(X.shape, bool)
    xs, ys = poly[:, 0], poly[:, 1]
    xe, ye = np.roll(xs, -1), np.roll(ys, -1)
    for x1, y1, x2, y2 in zip(xs, ys, xe, ye):
        if y1 == y2:
            continue
        c = ((y1 > Y) != (y2 > Y)) & (X < (x2 - x1) * (Y - y1) / (y2 - y1) + x1)
        inside ^= c
    return inside


def pct(v, p):
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    return None if not len(v) else round(float(np.percentile(v, p)), 3)


def main(ws, npz, out_dir):
    ws = Path(ws); out_dir = Path(out_dir)
    loc = json.loads((HERE.parents[2] / "data/centerline.local.json").read_text(encoding="utf-8"))["origin"]
    d = np.load(npz)
    g = d["cls"] == 2
    E, N, Z = d["e"][g], d["n"][g], d["z"][g] - ELEV0
    e0, n0 = np.floor(E.min()), np.floor(N.min())
    nx = int(np.ceil((E.max() - e0) / CELL_M)); ny = int(np.ceil((N.max() - n0) / CELL_M))
    ix = np.clip(((E - e0) / CELL_M).astype(int), 0, nx - 1); iy = np.clip(((N - n0) / CELL_M).astype(int), 0, ny - 1)
    flat = iy * nx + ix
    order = np.argsort(flat, kind="stable"); fs = flat[order]; zs = Z[order]
    uniq, start, count = np.unique(fs, return_index=True, return_counts=True)
    med = np.array([np.median(zs[a:a + c]) for a, c in zip(start, count)])
    dem = np.full(ny * nx, np.nan); dem[uniq] = med; dem = dem.reshape(ny, nx)
    filled_frac = float(np.isnan(dem).mean())
    gy, gx = np.mgrid[0:ny, 0:nx]
    ok = np.isfinite(dem)
    cx = e0 + (gx + 0.5) * CELL_M; cy = n0 + (gy + 0.5) * CELL_M
    lin = griddata(np.c_[cx[ok], cy[ok]], dem[ok], (cx, cy), method="linear")
    hole = ~ok & np.isfinite(lin); dem[hole] = lin[hole]
    rest = np.isnan(dem)
    if rest.any():
        nn = griddata(np.c_[cx[ok], cy[ok]], dem[ok], (cx[rest], cy[rest]), method="nearest"); dem[rest] = nn
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_dir / "infield_dem.npz", dem=dem.astype(np.float32), e0=e0, n0=n0, cell_m=CELL_M,
                        elev0=ELEV0, _doc="build-y metres (lidar z - 1634.84); row = north index from n0, col = east from e0")

    def dem_at(Ex, Nx):
        fx = (np.asarray(Ex) - e0) / CELL_M - 0.5; fy = (np.asarray(Nx) - n0) / CELL_M - 0.5
        x0 = np.clip(np.floor(fx).astype(int), 0, nx - 2); y0 = np.clip(np.floor(fy).astype(int), 0, ny - 2)
        tx = np.clip(fx - x0, 0, 1); ty = np.clip(fy - y0, 0, 1)
        return (dem[y0, x0] * (1 - tx) * (1 - ty) + dem[y0, x0 + 1] * tx * (1 - ty)
                + dem[y0 + 1, x0] * (1 - tx) * ty + dem[y0 + 1, x0 + 1] * tx * ty)
    hf = heightfield_sampler(ws, loc["lon"], loc["lat"])
    # inside the oval's measured inside edge
    ie = json.loads((RC / "inside_edge.naip.json").read_text(encoding="utf-8"))["rows"]
    inside = in_poly(np.array([r["edge_en_m"] for r in ie]), cx, cy)
    diff = hf(cx[inside], cy[inside]) - dem[inside]
    res = {"_doc": __doc__.strip().splitlines()[0], "lidar": str(npz), "workshop": str(ws),
           "dem": {"cell_m": CELL_M, "shape": [ny, nx], "e0": e0, "n0": n0, "empty_cells_before_fill": round(filled_frac, 3),
                   "infield_cells": int(inside.sum()),
                   "infield_relief_m": [round(float(dem[inside].min()), 2), round(float(dem[inside].max()), 2)]},
           "build_grid_minus_lidar_infield_m": {"p5": pct(diff, 5), "p50": pct(diff, 50), "p95": pct(diff, 95),
                                                "abs_p95": pct(np.abs(diff), 95), "abs_max": pct(np.abs(diff), 100)}}
    tree = cKDTree(np.c_[E, N])
    pieces = json.loads((RC / "infield_pieces.naip.json").read_text(encoding="utf-8"))["pieces"]
    rcd = json.loads((RC / "route_from_maps.naip.json").read_text(encoding="utf-8"))["routes"]["RC-D"]
    todo = {k: (v["centre_en_m"], v.get("width_m_per_metre")) for k, v in pieces.items()}
    # the lot band: RC-D's metres between the end of diag_s and the start of bottom (part_m order)
    parts = list(rcd["part_m"].items()); c0 = 0.0
    for name, ln in parts:
        if name == "LOT":
            lot = np.array(rcd["centre_en_m"])[int(round(c0)):int(round(c0 + ln)) + 1]
            todo["LOT (RC-D band)"] = (lot.tolist(), None)
        c0 += ln
    out_p = {}
    for name, (cen, wpm) in todo.items():
        C, t = resample(cen, 1.0)
        if len(C) < 5:
            continue
        T = np.gradient(C, axis=0); T /= np.linalg.norm(T, axis=1)[:, None]; L = np.c_[-T[:, 1], T[:, 0]]
        z = dem_at(C[:, 0], C[:, 1])
        grade = np.gradient(z, t) * 100
        w = np.interp(t, np.linspace(0, t[-1], len(wpm)), np.asarray(wpm, float)) if wpm else np.full(len(t), 9.2)
        cross = []
        for k in range(0, len(C), 2):
            idx = tree.query_ball_point(C[k], w[k] / 2 + 1.5)
            if not idx:
                cross.append(None); continue
            dv = np.c_[E[idx], N[idx]] - C[k]; la = dv @ L[k]; al = dv @ T[k]
            m = (np.abs(al) <= ALONG_M) & (np.abs(la) <= w[k] / 2 - 0.5)
            f = fit_line(la[m], Z[idx][m])
            cross.append(None if f is None else 100 * f[0])
        err = hf(C[:, 0], C[:, 1]) - z
        out_p[name] = {"length_m": round(float(t[-1]), 1), "z_start_end_m": [round(float(z[0]), 2), round(float(z[-1]), 2)],
                       "grade_pct": {"p50_abs": pct(np.abs(grade), 50), "p95_abs": pct(np.abs(grade), 95),
                                     "max_abs": pct(np.abs(grade), 100), "mean": round(float((z[-1] - z[0]) / t[-1] * 100), 2)},
                       "cross_pct": {"p10": pct(cross, 10), "p50": pct(cross, 50), "p90": pct(cross, 90),
                                     "abs_p90": pct(np.abs([c for c in cross if c is not None]), 90), "n": sum(c is not None for c in cross)},
                       "build_grid_error_m": {"p50": pct(err, 50), "abs_p95": pct(np.abs(err), 95), "abs_max": pct(np.abs(err), 100)}}
    res["pieces"] = out_p
    (out_dir / "infield_ground.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])
