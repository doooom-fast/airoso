"""Milford's far ground off the 2017 lidar (ledger 0082 "Far ground (0.1.11)"): the product tools/far_ground_blend.py meshes
(data/far_ground.lidar.npy + .fill.npy + .meta.json, tools/far_ground.py's Dem), plus data/far_ground.lidar.reach.npy, made from
the vegetation pass's read of pass 2's 71 EPT nodes (USGS 3DEP USGS_LPC_MI_31Co_Oakland_2016_LAS_2019, flown 2017-05-03;
source/vegetation/scripts/veg_read.py -> veg.npz). No download: the read is already on disk.

    python -I far_ground_product.py <veg.npz> <track dir> [--report <out.json>]

WHY NOT tools/lidar_ground.py's grid stage as it stands. Del Mar's tiles are full density everywhere (5 m cells of 3 ground
points cover its box); Milford's read is EPT nodes: full density only within the lane edge + 45 m, the shallower nodes cover
the rest at falling density (0.05-1 ground return per m2). 5 m cells with 3 ground points cover only 26 % of the ring past
Milford's 3DEP grid; the rest would be the harmonic fill, which ignores every sparse return. So the cell's ground is read at
the smallest radius that holds MIN_PTS ground points:

  samples   the read's 1 m cells holding class-2 returns: (e, n) the cell's centre, z its median ground return (g_med), weight
            its ground-return count (n_g). veg_read's own lon/lat -> metres differs from the author's (build_loop_blend's
            meters_per_degree) by under 1.5 cm at 1.4 km: below the 1 m cell
  measured  per 5 m product cell, the first radius of R_LEVELS around its centre holding MIN_PTS ground returns over 3 or
            more samples: a weighted least-squares plane through them, evaluated at the centre (on planar ground the plane
            is the ground; a mean would be biased wherever the returns sit to one side), one pass dropping the samples
            more than max(0.5 m, 3 robust sigma) off it; near-collinear samples (smallest spread under 0.5 m) take their
            weighted mean; the value is held inside the samples' own range +-1 m (no extrapolated slope)
  filled    every other cell, the harmonic fill of the measured ones (tools/lidar_ground.py harmonic_fill, coarse to fine):
            .fill.npy 1 = within REACH_M of a measured cell, or enclosed by measured ground (a lake, a roof, a wood)
  beyond    .fill.npy 2 = farther than REACH_M from any measured cell and open to the product's edge: the lidar does not
            reach it. reach.npy holds each such cell's distance in from the reach (0 elsewhere): with terrain.far_ground
            "beyond": "keep" the mesher keeps TODAY's ground there (the assembler's skirt), feathered to the fill over
            keep_feather_m from the reach

Every constant is an [invented] threshold; every measured value is a fit to ground returns.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, label
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "tools"))
from lidar_ground import harmonic_fill  # noqa: E402

CELL_M = 5.0                          # [invented] the product's cell (Del Mar's): finer than the 10 m ring that samples it
R_LEVELS = (3.5, 7.5, 15.0, 30.0)     # [invented] the radii tried in turn: the cell's own, then 2x, 4x, 8x
MIN_PTS = 3                           # [invented] (Del Mar's) fewer ground returns than this is no measurement
REACH_M = 30.0                        # [invented] a fill farther than the widest radius from a measured cell is not the lidar's
MARGIN_M = 20.0                       # the product box past the ring's own reach (bilinear needs a cell beyond the last node)
COLLINEAR_M2 = 0.25                   # [invented] a sample spread under 0.5 m across: no slope to fit


def mpd(lat0):
    """build_loop_blend.py's meters_per_degree (the author's own frame)"""
    return (111_412.84 * math.cos(math.radians(lat0)) - 93.5 * math.cos(3 * math.radians(lat0)),
            111_132.92 - 559.82 * math.cos(2 * math.radians(lat0)))


def grid_bbox(track: Path):
    """the 3DEP grid's local box as build_loop_blend.project_grid lays it out (heightfield.meta.json, the source track's)"""
    cfg = json.loads((track / "track.config.json").read_text(encoding="utf-8"))
    src = track.parent / cfg["lm_intake"]["source_track"]
    meta = json.loads((src / "data" / "heightfield.meta.json").read_text(encoding="utf-8"))
    o = json.loads((track / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
    m_lon, m_lat = mpd(o["lat"])
    s, w, n, e = meta["bbox_swne"]
    gy = meta["spacing_m"] / 111_000.0
    gx = meta["spacing_m"] / (111_000.0 * math.cos(math.radians((s + n) / 2)))
    x0 = (w - o["lon"]) * m_lon
    x1 = (w + (meta["nx"] - 1) * gx - o["lon"]) * m_lon
    y1 = (n - o["lat"]) * m_lat
    y0 = (n - (meta["ny"] - 1) * gy - o["lat"]) * m_lat
    return (x0, y0, x1, y1), o, cfg


def fit_cell(cx, cy, E, N, Z, Wt):
    """the plane through one cell's samples at its centre (the header's 'measured'); None when too few"""
    if len(Z) < 3 or Wt.sum() < MIN_PTS:
        return None
    for _ in range(2):
        w = Wt / Wt.sum()
        mx, my = float((w * E).sum()), float((w * N).sum())
        dx, dy = E - mx, N - my
        cxx, cyy, cxy = float((w * dx * dx).sum()), float((w * dy * dy).sum()), float((w * dx * dy).sum())
        lam_min = 0.5 * (cxx + cyy - math.sqrt((cxx - cyy) ** 2 + 4 * cxy * cxy))
        if lam_min < COLLINEAR_M2:
            zc = float((w * Z).sum())
            res = Z - zc
            val = zc
        else:
            A = np.c_[np.ones_like(E), E - cx, N - cy]
            sw = np.sqrt(Wt)
            coef = np.linalg.lstsq(A * sw[:, None], Z * sw, rcond=None)[0]
            res = Z - A @ coef
            val = float(coef[0])
        mad = float(np.median(np.abs(res - np.median(res))))
        keep = np.abs(res) <= max(0.5, 3.0 * 1.4826 * mad)
        if keep.all() or keep.sum() < 3 or Wt[keep].sum() < MIN_PTS:
            break
        E, N, Z, Wt = E[keep], N[keep], Z[keep], Wt[keep]
    return min(max(val, float(Z.min()) - 1.0), float(Z.max()) + 1.0)


def main(argv):
    npz, track = Path(argv[0]), Path(argv[1]).resolve()
    rep_path = Path(argv[argv.index("--report") + 1]) if "--report" in argv else None
    (gx0, gy0, gx1, gy1), origin, cfg = grid_bbox(track)
    reach = float(cfg["terrain"]["far_ground"]["reach_m"])
    d = np.load(npz)
    E0, N0 = int(d["E0"]), int(d["N0"])
    g, ng = d["g_med"], d["n_g"]
    # the product box: the ring's reach + a margin, on whole 5 m cells of the read's own 1 m lattice
    bx0 = math.floor((gx0 - reach - MARGIN_M - E0) / CELL_M) * CELL_M + E0
    by0 = math.floor((gy0 - reach - MARGIN_M - N0) / CELL_M) * CELL_M + N0
    nx = int(math.ceil((gx1 + reach + MARGIN_M - bx0) / CELL_M))
    ny = int(math.ceil((gy1 + reach + MARGIN_M - by0) / CELL_M))
    pad = R_LEVELS[-1] + 2
    i0, i1 = max(0, int(bx0 - pad - E0)), min(g.shape[1], int(bx0 + nx * CELL_M + pad - E0))
    j0, j1 = max(0, int(by0 - pad - N0)), min(g.shape[0], int(by0 + ny * CELL_M + pad - N0))
    sub_n = ng[j0:j1, i0:i1]
    jj, ii = np.nonzero(sub_n > 0)
    E = E0 + i0 + ii + 0.5
    N = N0 + j0 + jj + 0.5
    Z = g[j0:j1, i0:i1][jj, ii].astype(np.float64)
    Wt = sub_n[jj, ii].astype(np.float64)
    tree = cKDTree(np.c_[E, N])
    yy, xx = np.mgrid[0:ny, 0:nx]
    CX = bx0 + (xx + 0.5) * CELL_M
    CY = by0 + (yy + 0.5) * CELL_M
    z = np.zeros((ny, nx))
    level = np.zeros((ny, nx), np.uint8)            # 0 not measured, k = measured at R_LEVELS[k - 1]
    todo = np.ones((ny, nx), bool)
    for k, r in enumerate(R_LEVELS, start=1):
        js, is_ = np.nonzero(todo)
        if not len(js):
            break
        cand = np.c_[CX[js, is_], CY[js, is_]]
        lists = tree.query_ball_point(cand, r)
        for (j, i), idx in zip(zip(js, is_), lists):
            if len(idx) < 3:
                continue
            idx = np.asarray(idx)
            if Wt[idx].sum() < MIN_PTS:
                continue
            v = fit_cell(CX[j, i], CY[j, i], E[idx], N[idx], Z[idx], Wt[idx])
            if v is None:
                continue
            z[j, i], level[j, i], todo[j, i] = v, k, False
        print(f"[far-ground product] radius {r:>4} m: {int((level == k).sum()):,} cells measured", flush=True)
    known = level > 0
    filled = harmonic_fill(z, known)
    dist = distance_transform_edt(~known) * CELL_M
    far = ~known & (dist > REACH_M)
    lab, nlab = label(far)
    edge_labels = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]).tolist()) - {0}
    beyond = np.isin(lab, list(edge_labels)) if edge_labels else np.zeros_like(far)
    fill = np.where(known, 0, np.where(beyond, 2, 1)).astype(np.uint8)
    reach_d = (distance_transform_edt(beyond) * CELL_M).astype(np.float32)
    out = track / "data"
    np.save(out / "far_ground.lidar.npy", filled.astype(np.float32))
    np.save(out / "far_ground.lidar.fill.npy", fill)
    np.save(out / "far_ground.lidar.reach.npy", reach_d)
    ring = ~((CX >= gx0) & (CX <= gx1) & (CY >= gy0) & (CY <= gy1)) & (CX >= gx0 - reach) & (CX <= gx1 + reach) \
        & (CY >= gy0 - reach) & (CY <= gy1 + reach)
    nr = int(ring.sum())
    cov = {"ring_cells": nr,
           "measured_by_radius_pct": {f"{r} m": round(100.0 * int(((level == k) & ring).sum()) / nr, 1)
                                      for k, r in enumerate(R_LEVELS, start=1)},
           "measured_pct": round(100.0 * int((known & ring).sum()) / nr, 1),
           "filled_within_reach_pct": round(100.0 * int(((fill == 1) & ring).sum()) / nr, 1),
           "beyond_reach_pct": round(100.0 * int(((fill == 2) & ring).sum()) / nr, 1)}
    doc = {"_doc": "ledger 0082 'Far ground (0.1.11)': Milford's bare ground off the 2017 USGS 3DEP lidar "
                   "(USGS_LPC_MI_31Co_Oakland_2016_LAS_2019, flown 2017-05-03; pass 2's 71 EPT nodes as the vegetation pass read "
                   "them) by tracks/milford-road-course-lm/source/far_ground/scripts/far_ground_product.py (its header says how): "
                   "far_ground.lidar.npy row 0 = SOUTH, column 0 = WEST, each value the NAVD88 metres at its cell's centre "
                   "(x0 + (i + 0.5) cell, y0 + (j + 0.5) cell, local metres east / north of the origin); far_ground.lidar.fill.npy "
                   "0 measured (a plane through the ground returns within the first radius holding 3), 1 filled within reach or "
                   "enclosed, 2 beyond the lidar's reach; far_ground.lidar.reach.npy each beyond cell's distance in from the reach, m.",
           "origin": origin, "x0": round(bx0, 3), "y0": round(by0, 3), "cell_m": CELL_M, "nx": nx, "ny": ny,
           "classes": [2], "source": {"project": "USGS_LPC_MI_31Co_Oakland_2016_LAS_2019", "flown": "2017-05-03",
                                      "nodes": 71, "read": "source/vegetation/scripts/veg_read.py -> veg.npz (g_med, n_g)",
                                      "crs": "EPSG:3857 EPT, z NAVD88 m"},
           "grid_bbox_xy": [round(gx0, 2), round(gy0, 2), round(gx1, 2), round(gy1, 2)],
           "cells": {"measured": int(known.sum()), "filled_within_reach": int((fill == 1).sum()),
                     "beyond_reach": int((fill == 2).sum()),
                     "measured_by_radius": {f"{r} m": int((level == k).sum()) for k, r in enumerate(R_LEVELS, start=1)}},
           "ring_coverage": cov,
           "params": {"CELL_M": CELL_M, "R_LEVELS": list(R_LEVELS), "MIN_PTS": MIN_PTS, "REACH_M": REACH_M,
                      "COLLINEAR_M2": COLLINEAR_M2, "FILL": "tools/lidar_ground.py harmonic_fill"}}
    (out / "far_ground.lidar.meta.json").write_text(json.dumps(doc, indent=1), encoding="utf-8", newline="\n")
    print(f"[far-ground product] {nx} x {ny} cells of {CELL_M} m over [{bx0:.0f}, {bx0 + nx * CELL_M:.0f}] x "
          f"[{by0:.0f}, {by0 + ny * CELL_M:.0f}]: {doc['cells']}; the ring past the grid: {cov}")
    if rep_path:
        np.savez_compressed(rep_path, level=level, fill=fill)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
