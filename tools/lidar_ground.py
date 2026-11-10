"""The bare ground MEASURED from USGS 3DEP lidar (ledger 0083 pass 4b, "far ground from the lidar"): a track's ground past
its 3DEP grid read off the tiles' own ground points, for tools/far_ground_blend.py to mesh.

Two stages, so the heavy read runs once (the G10, under its cap) and the product is re-made anywhere:

    python -I tools/lidar_ground.py extract <centerline.local.json> <out.npz> <tile.laz> [<tile.laz> ...]
    python tools/lidar_ground.py grid <in.npz> <track-dir> <x0> <y0> <x1> <y1>

extract (laspy + lazrs + pyproj + numpy: the lidar venv, python -I: it reads downloaded data) reads every tile in chunks and
bins its GROUND points (class 2, and class 9, water: the lagoon's surface is the ground a driver sees) into EXTRACT_CELL_M
cells of the track's local frame (x east, y north, metres from the origin of centerline.local.json, the author's own
lon/lat -> metres): per cell the sum of heights (NAVD88, as the tile), the count, and the tile cover (any point of any
class). The .npz never enters the repo.

grid (numpy only) block-sums the cells to CELL_M over the box [x0, x1] x [y0, y1] and writes the derived product the
author reads, data/far_ground.lidar.npy (float32, NAVD88 metres, row 0 = SOUTH, column 0 = WEST, each value its cell's
centre) + data/far_ground.lidar.meta.json (the box, the cell, the origin, what each value is, the fill counts):
  measured  the mean of the cell's ground points (MIN_PTS or more)
  filled    a cell with too few ground points inside the tiles (a building's footprint, a dense tree) or past them takes the
            harmonic fill of its measured neighbours (each such cell the mean of its four, solved coarse to fine): the ground
            under a building is the surface its surroundings span; past the tiles' edge the fill only continues it, flagged
            (data/far_ground.lidar.fill.npy: 0 measured, 1 under cover, 2 off the tiles)
Every constant is an [invented] threshold; every measured value is a mean of points.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
EXTRACT_CELL_M = 1.0
CELL_M = 5.0               # [invented] the product's cell: finer than the 10 m mesh that samples it
MIN_PTS = 3                # [invented] fewer ground points than this in a product cell is no measurement
GROUND_CLASSES = (2, 9)
FILL_ITERS = 400           # Jacobi sweeps of the fill at each level of its coarse-to-fine solve
CHUNK_POINTS = 2_000_000


def extract_main(argv):
    import laspy
    from pyproj import CRS, Transformer
    cfile, outp = Path(argv[0]), Path(argv[1])
    tiles = [Path(a) for a in argv[2:]]
    origin = json.loads(cfile.read_text(encoding="utf-8"))["origin"]
    sys.path.insert(0, str(HERE.parent))
    from scripts.geometry.projection import _meters_per_degree
    mlon, mlat = _meters_per_degree(origin["lat"])
    with laspy.open(tiles[0]) as f:
        crs = f.header.parse_crs()
    hcrs = crs.sub_crs_list[0] if crs.is_compound else crs
    to_ll = Transformer.from_crs(hcrs, CRS.from_epsg(4326), always_xy=True)
    # the local box of every tile (its corners through the transform), the grid over all of them
    corners = []
    heads = []
    for tp in tiles:
        with laspy.open(tp) as f:
            x0, y0, x1, y1 = float(f.header.mins[0]), float(f.header.mins[1]), float(f.header.maxs[0]), float(f.header.maxs[1])
        heads.append({"file": tp.name, "bytes": tp.stat().st_size, "bbox": [x0, y0, x1, y1]})
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            lon, lat = to_ll.transform(x, y)
            corners.append(((lon - origin["lon"]) * mlon, (lat - origin["lat"]) * mlat))
    C = EXTRACT_CELL_M
    gx0 = math.floor(min(c[0] for c in corners) / C) * C - C
    gy0 = math.floor(min(c[1] for c in corners) / C) * C - C
    nx = int(math.ceil((max(c[0] for c in corners) - gx0) / C)) + 2
    ny = int(math.ceil((max(c[1] for c in corners) - gy0) / C)) + 2
    zsum = np.zeros(ny * nx, np.float64)
    zcnt = np.zeros(ny * nx, np.int32)
    cover = np.zeros(ny * nx, np.int32)
    n_all = n_ground = 0
    for tp in tiles:
        with laspy.open(tp) as f:
            for ch in f.chunk_iterator(CHUNK_POINTS):
                cls = np.asarray(ch.classification, dtype=np.uint8)
                lon, lat = to_ll.transform(np.asarray(ch.x), np.asarray(ch.y))
                lx = (np.asarray(lon) - origin["lon"]) * mlon
                ly = (np.asarray(lat) - origin["lat"]) * mlat
                i = np.clip(((lx - gx0) // C).astype(np.int64), 0, nx - 1)
                j = np.clip(((ly - gy0) // C).astype(np.int64), 0, ny - 1)
                k = j * nx + i
                cover += np.bincount(k, minlength=ny * nx).astype(np.int32)
                g = np.isin(cls, GROUND_CLASSES)
                zsum += np.bincount(k[g], weights=np.asarray(ch.z)[g], minlength=ny * nx)
                zcnt += np.bincount(k[g], minlength=ny * nx).astype(np.int32)
                n_all += len(cls)
                n_ground += int(g.sum())
    meta = {"origin": origin, "x0": gx0, "y0": gy0, "cell_m": C, "nx": nx, "ny": ny, "crs": hcrs.name, "tiles": heads,
            "classes": list(GROUND_CLASSES), "points": n_all, "ground_points": n_ground}
    np.savez_compressed(outp, zsum=zsum.reshape(ny, nx), zcnt=zcnt.reshape(ny, nx), cover=cover.reshape(ny, nx),
                        meta=np.frombuffer(json.dumps(meta).encode("utf-8"), dtype=np.uint8))
    print(f"[ground] {n_all:,} points from {len(tiles)} tiles, {n_ground:,} ground; {nx} x {ny} cells of {C} m -> {outp}")
    return 0


def harmonic_fill(z, known, iters=FILL_ITERS):
    """Pure: every unknown cell the mean of its four neighbours (edges reflect), the known cells held. Solved coarse to
    fine (each level starts from the half-resolution solution, then FILL_ITERS Jacobi sweeps), so a wide unknown region
    converges and is not left near its starting value"""
    known = np.asarray(known, bool)
    if known.all() or not known.any():
        return np.where(known, z, float(np.mean(z[known])) if known.any() else 0.0).astype(np.float64)
    ny, nx = z.shape
    if min(ny, nx) > 8:
        # the half-resolution problem: a coarse cell is known where any of its fine cells is, at their mean
        py, px = ny % 2, nx % 2
        zz = np.pad(np.where(known, z, 0.0), ((0, py), (0, px)), mode="edge")
        kk = np.pad(known, ((0, py), (0, px)), mode="edge").astype(np.float64)
        S = (zz * kk).reshape(zz.shape[0] // 2, 2, zz.shape[1] // 2, 2).sum(axis=(1, 3))
        K = kk.reshape(kk.shape[0] // 2, 2, kk.shape[1] // 2, 2).sum(axis=(1, 3))
        coarse = harmonic_fill(np.where(K > 0, S / np.maximum(K, 1), 0.0), K > 0, iters)
        start = np.repeat(np.repeat(coarse, 2, axis=0), 2, axis=1)[:ny, :nx]
    else:
        start = np.full(z.shape, float(np.mean(z[known])))
    out = np.where(known, z, start).astype(np.float64)
    for _ in range(iters):
        p = np.pad(out, 1, mode="edge")
        avg = (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 4.0
        out = np.where(known, out, avg)
    return out


def block(a, f):
    ny, nx = a.shape[0] // f * f, a.shape[1] // f * f
    return a[:ny, :nx].reshape(ny // f, f, nx // f, f).sum(axis=(1, 3))


def grid_main(argv):
    src, track = Path(argv[0]), Path(argv[1])
    bx0, by0, bx1, by1 = (float(v) for v in argv[2:6])
    d = np.load(src)
    meta = json.loads(bytes(d["meta"]).decode("utf-8"))
    C, f = meta["cell_m"], int(round(CELL_M / meta["cell_m"]))
    # the product's box on the extract's lattice: whole product cells
    i0 = int(math.floor((bx0 - meta["x0"]) / CELL_M)) * f
    j0 = int(math.floor((by0 - meta["y0"]) / CELL_M)) * f
    nxp = int(math.ceil((bx1 - (meta["x0"] + i0 * C)) / CELL_M))
    nyp = int(math.ceil((by1 - (meta["y0"] + j0 * C)) / CELL_M))
    full = np.zeros((nyp * f, nxp * f)), np.zeros((nyp * f, nxp * f), np.int64), np.zeros((nyp * f, nxp * f), np.int64)
    zs, zc, cv = full
    # copy the overlap of the extract's arrays into the box (cells past the extract stay empty: off the tiles)
    sj0, si0 = max(0, j0), max(0, i0)
    sj1, si1 = min(meta["ny"], j0 + nyp * f), min(meta["nx"], i0 + nxp * f)
    if sj1 > sj0 and si1 > si0:
        zs[sj0 - j0:sj1 - j0, si0 - i0:si1 - i0] = d["zsum"][sj0:sj1, si0:si1]
        zc[sj0 - j0:sj1 - j0, si0 - i0:si1 - i0] = d["zcnt"][sj0:sj1, si0:si1]
        cv[sj0 - j0:sj1 - j0, si0 - i0:si1 - i0] = d["cover"][sj0:sj1, si0:si1]
    S, N, V = block(zs, f), block(zc, f), block(cv, f)
    known = N >= MIN_PTS
    z = np.where(known, S / np.maximum(N, 1), 0.0)
    filled = harmonic_fill(z, known)
    fill = np.where(known, 0, np.where(V > 0, 1, 2)).astype(np.uint8)
    x0, y0 = meta["x0"] + i0 * C, meta["y0"] + j0 * C
    out = track / "data"
    np.save(out / "far_ground.lidar.npy", filled.astype(np.float32))
    np.save(out / "far_ground.lidar.fill.npy", fill)
    doc = {"_doc": "ledger 0083 pass 4b: the bare ground off the 2024 USGS 3DEP lidar (CA_SanDiegoCo_D24) by tools/lidar_ground.py "
                   "(its header says how): far_ground.lidar.npy row 0 = SOUTH, column 0 = WEST, each value the NAVD88 metres at its "
                   "cell's centre (x0 + (i + 0.5) cell, y0 + (j + 0.5) cell, local metres east / north of the origin); "
                   "far_ground.lidar.fill.npy 0 measured, 1 filled under cover (a building, a dense tree), 2 filled past the tiles.",
           "origin": meta["origin"], "x0": round(x0, 3), "y0": round(y0, 3), "cell_m": CELL_M, "nx": int(nxp), "ny": int(nyp),
           "classes": meta["classes"], "tiles": meta["tiles"], "crs": meta["crs"],
           "cells": {"measured": int((fill == 0).sum()), "filled_under_cover": int((fill == 1).sum()),
                     "filled_off_the_tiles": int((fill == 2).sum())},
           "params": {"CELL_M": CELL_M, "MIN_PTS": MIN_PTS, "FILL_ITERS": FILL_ITERS, "EXTRACT_CELL_M": C}}
    (out / "far_ground.lidar.meta.json").write_text(json.dumps(doc, indent=1), encoding="utf-8", newline="\n")
    print(f"[ground] {nxp} x {nyp} cells of {CELL_M} m over [{x0:.0f}, {x0 + nxp * CELL_M:.0f}] x [{y0:.0f}, "
          f"{y0 + nyp * CELL_M:.0f}]: {doc['cells']}")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("extract", "grid"):
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(extract_main(a[1:]) if a[0] == "extract" else grid_main(a[1:]))
