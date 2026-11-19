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

THE COMMITTED 1 m GRID INSTEAD OF THE EPT (opt-in, ledger 0092, Milford): --npz PATH (or terrain.lidar_patches_npz in the
config, relative to the project) reads a track's committed lidar grid (Milford's source/lidar/milford_lidar_1m.npz, ledger
0082 pass 2: e0, n0 the SW corner of cell 0 in local metres, cell, ground_z_cm_over_z0 int16 with -1 = no ground return,
z0_m NAVD88; row 0 = south) and never touches the network. The lattice nodes are that grid's own cell centres and each
node's ground is its cell's (the grid's mean of the class-2 returns in the cell); the origin and the line are the
project's own data/centerline.local.json. A patch may name "corridor": {"full_m", "zero_m", "in0_m", "in1_m"}: the lattice
then carries a weight per node ("w"), off the node's distance d to the lane edge (the line +- widths_m / 2): 0 within in0_m,
rising linearly to 1 at in1_m, 1 to full_m, falling linearly to 0 at zero_m; only nodes with w > 0 are filled and written
(the rest null), and tools/ground_patch_blend.py moves a vertex by that weight. The default --out is then
terrain.lidar_patches_file (a build product: the chain measures it in its draft step ground_patch).
The corridor's lane edge is the one the assembler builds (ledger 0091): data/centerline.local.json through the route's own
smoothing (scripts-v021 geometry/smooth.py, route.smooth_*). With lm_intake.line_precomp the intake's line is not the built
one (Milford 0.1.13: 0.21 m p50, up to 4.25 m off it at the s 1,000 hairpin), and in0_m read off it weighted lattice nodes
as close as 6.18 m to the built lane edge (1,305 inside 9 m: drive_test's excursion reach); on 0.1.12's line 8.08 m (730).
Off the assembler's line: 9.00 m, none inside.
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


def points_in(poly, X, Z):
    """point_in over arrays (the even-odd rule, vectorised)"""
    import numpy as np
    c = np.zeros(np.shape(X), bool)
    for k in range(len(poly)):
        (x1, z1), (x2, z2) = poly[k - 1], poly[k]
        if z1 == z2:
            continue
        c ^= ((z1 > Z) != (z2 > Z)) & (X < x1 + (Z - z1) * (x2 - x1) / (z2 - z1))
    return c


def load_grid(path, elev0):
    """the committed 1 m lidar grid (ledger 0082 pass 2's milford_lidar_1m.npz): heights in the local frame, nan = no reading"""
    import numpy as np
    z = np.load(path)
    g = z["ground_z_cm_over_z0"]
    return {"e0": float(z["e0"]), "n0": float(z["n0"]), "cell": float(z["cell"]),
            "y": np.where(g != -1, float(z["z0_m"]) + g.astype(float) / 100.0 - float(elev0), np.nan)}


def lane_edge_distance(line, X, Z, reach=None):
    """distance of each (X, Z) to the lane edge (centreline +- widths_m / 2; + outside), per centre point within reach"""
    import numpy as np
    P = np.array(line["points_xyz_m"], float)[:, [0, 2]]
    half = np.array(line["widths_m"], float) / 2.0
    X, Z = np.asarray(X, float), np.asarray(Z, float)
    D = np.full(X.shape, np.inf)
    ax, az, bx, bz = P[:-1, 0], P[:-1, 1], P[1:, 0], P[1:, 1]
    dx, dz = bx - ax, bz - az
    L2 = np.where(dx * dx + dz * dz == 0, 1.0, dx * dx + dz * dz)
    lim = reach if reach is not None else np.inf
    for k in range(len(ax)):
        hw = max(half[k], half[k + 1])
        m = ((X >= min(ax[k], bx[k]) - lim - hw) & (X <= max(ax[k], bx[k]) + lim + hw)
             & (Z >= min(az[k], bz[k]) - lim - hw) & (Z <= max(az[k], bz[k]) + lim + hw))
        if not m.any():
            continue
        x, z = X[m], Z[m]
        t = np.clip(((x - ax[k]) * dx[k] + (z - az[k]) * dz[k]) / L2[k], 0, 1)
        d = np.hypot(x - ax[k] - t * dx[k], z - az[k] - t * dz[k]) - (half[k] * (1 - t) + half[k + 1] * t)
        D[m] = np.minimum(D[m], d)
    return D


def corridor_weight(d, c):
    """the corridor's weight off the distance to the lane edge: 0 to in0_m, up to 1 at in1_m, 1 to full_m, 0 at zero_m"""
    import numpy as np
    full, zero = float(c["full_m"]), float(c["zero_m"])
    in0, in1 = float(c.get("in0_m", -1e9)), float(c.get("in1_m", -1e9))
    w = np.where(d <= full, 1.0, np.clip((zero - d) / max(zero - full, 1e-9), 0.0, 1.0))
    if in1 > in0:
        w = w * np.clip((d - in0) / (in1 - in0), 0.0, 1.0)
    return np.where(np.isfinite(d), w, 0.0)


def measure_grid(grid, poly, feather, corridor=None, line=None):
    """the patch's lattice off the committed grid: the grid's own cell centres over the polygon's box grown by feather_m"""
    import numpy as np
    c = grid["cell"]
    ox, oz = grid["e0"] + c / 2, grid["n0"] + c / 2            # the grid's first cell centre
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    i0, i1 = math.floor((min(xs) - feather - ox) / c), math.ceil((max(xs) + feather - ox) / c)
    j0, j1 = math.floor((min(zs) - feather - oz) / c), math.ceil((max(zs) + feather - oz) / c)
    nx, nz = i1 - i0 + 1, j1 - j0 + 1
    G = grid["y"]
    y = np.full((nz, nx), np.nan)
    a0, a1 = max(i0, 0), min(i1, G.shape[1] - 1)
    b0, b1 = max(j0, 0), min(j1, G.shape[0] - 1)
    if a0 <= a1 and b0 <= b1:
        y[b0 - j0:b1 - j0 + 1, a0 - i0:a1 - i0 + 1] = G[b0:b1 + 1, a0:a1 + 1]
    x0, z0 = ox + i0 * c, oz + j0 * c
    gx, gz = np.meshgrid(x0 + np.arange(nx) * c, z0 + np.arange(nz) * c)
    inside = points_in(poly, gx, gz)
    w = None
    if corridor is not None:
        d = lane_edge_distance(line, gx, gz, reach=float(corridor["zero_m"]) + 2 * c)
        w = np.round(corridor_weight(d, corridor), 3)      # as written: a node the file weighs 0 holds no ground
        inside &= w > 0
    read = ~np.isnan(y)
    filled = 0
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
    out = {"x0": round(float(x0), 3), "z0": round(float(z0), 3), "cell_m": c, "nx": int(nx), "nz": int(nz)}
    if w is not None:
        y = np.where(w > 0, y, np.nan)
        out["w"] = [float(v) for v in w.ravel()]
        out["corridor"] = corridor
    out["y"] = [None if math.isnan(v) else round(float(v), 3) for v in y.ravel()]
    out["read"] = int((read & ~np.isnan(y)).sum())
    out["filled"] = filled
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project")
    ap.add_argument("--ept", default=lcp.EPT_DEFAULT)
    ap.add_argument("--out")
    ap.add_argument("--cache")
    ap.add_argument("--npz", help="the committed 1 m lidar grid (opt-in, ledger 0092; default terrain.lidar_patches_npz)")
    a = ap.parse_args(argv)
    proj = Path(a.project).resolve()
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    ter = cfg.get("terrain") or {}
    patches = ter.get("lidar_patches") or []
    if not patches:
        raise SystemExit("lidar_ground_patch: no terrain.lidar_patches declared")
    npz = a.npz or (str(proj / ter["lidar_patches_npz"]) if ter.get("lidar_patches_npz") else None)
    if npz:
        return main_grid(a, proj, ter, patches, Path(npz))
    if any(p.get("corridor") for p in patches):
        raise SystemExit("lidar_ground_patch: a corridor patch is read off a committed grid (--npz / terrain.lidar_patches_npz)")
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


def assembler_line(line, route):
    """the intake's line as the assembler builds it (scripts-v021 geometry/smooth.py with route.smooth_*, horizontal only;
    widths and origin kept): the lane a corridor's distances are read off (ledger 0091)"""
    import importlib.util
    f = Path(__file__).resolve().parents[1] / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "smooth.py"
    sp = importlib.util.spec_from_file_location("_lm_smooth", f)
    sm = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(sm)
    pts = sm.smooth_centerline([tuple(p) for p in line["points_xyz_m"]], sigma_pts=float(route.get("smooth_sigma_pts", 2.0)),
                               passes=int(route.get("smooth_passes", 2)), sigma_y_pts=0.0)
    return dict(line, points_xyz_m=[list(p) for p in pts])


def main_grid(a, proj, ter, patches, npz) -> int:
    """opt-in (ledger 0092): every patch off the committed grid, no network"""
    line = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    if any(p.get("corridor") for p in patches):
        route = json.loads((proj / "track.config.json").read_text(encoding="utf-8")).get("route") or {}
        line = assembler_line(line, route)
    grid = load_grid(npz, line["origin"]["elev_m"])
    out = {}
    for p in patches:
        r = measure_grid(grid, [tuple(q) for q in p["polygon"]], float(p.get("feather_m", 0.0)), p.get("corridor"), line)
        r["polygon"] = p["polygon"]
        out[p["id"]] = r
        ys = [v for v in r["y"] if v is not None]
        print(f"[lidar_patch] {p['id']}: {r['nx']} x {r['nz']} nodes of the {grid['cell']:.0f} m grid, {r['read']} read, "
              f"{r['filled']} filled from their neighbours" + (f", {len(ys)} weighted (corridor {p['corridor']})" if p.get("corridor") else "")
              + f"; ground {min(ys):.2f} .. {max(ys):.2f} m")
    rel = ter.get("lidar_patches_file") or "source/ground_patches.lidar.json"
    out_p = Path(a.out) if a.out else proj / rel
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps({
        "_doc": "tools/lidar_ground_patch.py --npz (ledger 0092): each terrain.lidar_patches polygon's lattice on the committed "
                "lidar grid's own cell centres (the grid's mean class-2 ground per cell); nodes with no reading inside the "
                "polygon (and, for a corridor patch, with weight > 0) filled from their neighbours; a corridor patch's "
                "per-node weight w off the distance to the lane edge; local frame (z - origin.elev_m); applied by "
                "tools/ground_patch_blend.py",
        "npz": npz.name, "patches": out}, separators=(",", ":")), encoding="utf-8")
    print(f"[lidar_patch] -> {out_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
