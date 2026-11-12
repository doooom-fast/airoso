"""Measure the real ground of a declared patch off USGS 3DEP source lidar, on a lattice (ledger 0079 round I).

Kevin, 2026-11-03: "I just want real". The assembler's terrain is the 3DEP grid (40 m, read at 20 m) held to the road's
height for terrain_band_m beside every road: where the real ground steps at a retaining wall inside that band, the
built ground is a plateau at the road's height and then one long facet down. Sand Creek (round I): beside
grid_primary_49 the lidar has a 2-4.5 m retaining wall 15-28 m off the street (x -1574 .. -1552, z -865 .. -1045);
the built ground stands at the street's 31.3 m for 20 m past it and then falls one 28 m facet through
osm_buildings1182's footprint (relief 3.16 m: the house dropped). This measures the ground there; tools/
ground_patch_blend.py seats loop.blend's TERRAIN on it.

track.config.json terrain.lidar_patches = [{"id": .., "polygon": [[x, z], ...], "feather_m": F, "feather_side": ..}]
(local metres). For each patch: a CELL_M lattice over the polygon's box grown by feather_m; at each node the median of
the lidar ground (class 2) returns within RADIUS_M, MIN_RETURNS or more, else no reading. Nodes with no
reading inside the polygon (under a roof: a building's footprint has roof returns, not ground) are filled from their
neighbours (each pass, every empty node next to read ones takes their mean, until none is left): the ground under a roof
read from the ground around it. Heights in the track's local frame (z - origin.elev_m).

Writes <out> (default <project>/source/ground_patches.lidar.json): {"patches": {id: {"x0", "z0", "cell_m", "nx", "nz",
"y" (row-major, z then x; null = no reading), "filled", "polygon"}}}.

    python tools/lidar_ground_patch.py <project-dir> [--ept URL] [--out PATH] [--cache DIR]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import lidar_connector_profile as lcp  # noqa: E402

CELL_M = 1.0          # [invented] the lattice step
RADIUS_M = 1.0        # [invented] returns within this of a node (as lidar_connector_profile: 10-25 ground returns here)
MIN_RETURNS = 3       # [invented] fewer than this is no reading (as lidar_connector_profile)


def measure(ept, poly, feather):
    import numpy as np
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    x0, x1 = math.floor(min(xs) - feather), math.ceil(max(xs) + feather)
    z0, z1 = math.floor(min(zs) - feather), math.ceil(max(zs) + feather)
    nx, nz = int(round((x1 - x0) / CELL_M)) + 1, int(round((z1 - z0) / CELL_M)) + 1
    tiles = {}
    for i in range(int(math.floor(x0 / lcp.TILE_M)), int(math.floor(x1 / lcp.TILE_M)) + 1):
        for j in range(int(math.floor(z0 / lcp.TILE_M)), int(math.floor(z1 / lcp.TILE_M)) + 1):
            tiles[(i, j)] = ept.tile(i, j)
    E = np.concatenate([t[0] for t in tiles.values()])
    N = np.concatenate([t[1] for t in tiles.values()])
    Z = np.concatenate([t[2] for t in tiles.values()])
    C = np.concatenate([t[3] for t in tiles.values()])
    k = (C == 2) & (E >= x0 - CELL_M) & (E <= x1 + CELL_M) & (N >= z0 - CELL_M) & (N <= z1 + CELL_M)
    E, N, Z = E[k], N[k], Z[k]
    from scipy.spatial import cKDTree
    tree = cKDTree(np.column_stack([E, N]))
    y = np.full((nz, nx), np.nan)
    gx, gz = np.meshgrid(x0 + np.arange(nx) * CELL_M, z0 + np.arange(nz) * CELL_M)
    hits = tree.query_ball_point(np.column_stack([gx.ravel(), gz.ravel()]), RADIUS_M)
    for k, h in enumerate(hits):
        if len(h) >= MIN_RETURNS:
            y.flat[k] = float(np.median(Z[h]))
    read = ~np.isnan(y)
    filled = 0
    inside = np.zeros_like(read)
    for j in range(nz):
        for i in range(nx):
            inside[j, i] = point_in(poly, x0 + i * CELL_M, z0 + j * CELL_M)
    while True:
        hole = np.isnan(y) & inside
        if not hole.any():
            break
        pad = np.pad(y, 1, constant_values=np.nan)
        nb = np.stack([pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]])
        cnt = (~np.isnan(nb)).sum(0)
        take = hole & (cnt > 0)
        if not take.any():
            raise SystemExit("lidar_ground_patch: a hole inside the polygon with no reading around it")
        y[take] = np.nansum(nb, 0)[take] / cnt[take]
        filled += int(take.sum())
    return {"x0": x0, "z0": z0, "cell_m": CELL_M, "nx": nx, "nz": nz,
            "y": [None if math.isnan(v) else round(float(v), 3) for v in y.ravel()],
            "read": int(read.sum()), "filled": filled}


def point_in(poly, x, z):
    c = False
    for k in range(len(poly)):
        (x1, z1), (x2, z2) = poly[k - 1], poly[k]
        if (z1 > z) != (z2 > z) and x < x1 + (z - z1) * (x2 - x1) / (z2 - z1):
            c = not c
    return c


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project")
    ap.add_argument("--ept", default=lcp.EPT_DEFAULT)
    ap.add_argument("--out")
    ap.add_argument("--cache")
    a = ap.parse_args(argv)
    proj = Path(a.project).resolve()
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    patches = (cfg.get("terrain") or {}).get("lidar_patches") or []
    if not patches:
        raise SystemExit("lidar_ground_patch: no terrain.lidar_patches declared")
    src = proj.parent / str((cfg.get("lm_intake") or {}).get("source_track") or proj.name)
    origin = json.loads((src / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
    cache = Path(a.cache) if a.cache else Path(tempfile.mkdtemp(prefix="lidar_patch_"))
    ept = lcp.Ept(a.ept, origin, cache)
    out = {}
    for p in patches:
        r = measure(ept, [tuple(q) for q in p["polygon"]], float(p.get("feather_m", 0.0)))
        r["polygon"] = p["polygon"]
        out[p["id"]] = r
        ys = [v for v in r["y"] if v is not None]
        print(f"[lidar_patch] {p['id']}: {r['nx']} x {r['nz']} nodes at {CELL_M} m, {r['read']} read, {r['filled']} filled "
              f"under roofs; ground {min(ys):.2f} .. {max(ys):.2f} m")
    out_p = Path(a.out) if a.out else proj / "source" / "ground_patches.lidar.json"
    out_p.write_text(json.dumps({
        "_doc": "tools/lidar_ground_patch.py (ledger 0079 round I): the lidar ground (class 2 median within "
                f"{RADIUS_M} m [invented] of each {CELL_M} m lattice node [invented], min {MIN_RETURNS} returns) over each terrain.lidar_patches polygon; nodes "
                "under a roof filled from their neighbours; local frame (z - origin.elev_m); applied by "
                "tools/ground_patch_blend.py",
        "ept": a.ept, "patches": out}, separators=(",", ":")), encoding="utf-8")
    print(f"[lidar_patch] -> {out_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
