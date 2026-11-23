#!/usr/bin/env python3
"""Bake a track's far backdrop from the shared Front Range surface (PLAN section 3 of tracks/denver-grand-prix,
ledger 0096). One surveyed surface, placed by each track's own origin; the mesh differs per track, the source and
this tool do not.

    python tools/backdrop_bake.py tracks/_reference/front-range/bake.config.json denver-grand-prix \
        --dem /Volumes/Sundowning/Claude/airoso-data/front-range/dem --out <dir outside git>

Writes <out>/<slug>_backdrop.obj (a readable intermediate destined for <slug>_backdrop.kn5; this tool exports no kn5)
and <out>/<slug>_backdrop.bake.json (what was built, with counts). Needs numpy; rasterio only to read the real tiles.

WHAT IT BUILDS
- A polar lattice about the track origin, bearings arc_deg[0]..arc_deg[1], radii near_m..far_m. A vertex sits at a
  true geodesic bearing and distance from the origin on the WGS84 ellipsoid: x = d sin(az) (east), z = d cos(az) (north).
  Close to the origin that is the engine's own local frame (scripts/geometry/projection.py), so the mountains stand at
  true bearings against the streets.
- Height: y = elevation - origin_elev_m - d^2 (1 - k) / (2 R), d from the ORIGIN. That is Earth curvature with standard
  refraction (k = 0.13), baked per track. From any other point of the lap the error is the tilt of the vertical between
  it and the origin: 0.009 degrees per km.
- Cell size follows distance: the angular step is pixel_rad (0.001 rad: 60 m at 60 km), doubled inward wherever a cell
  would fall under min_cell_m. The radial step is radial_factor cells. Where the step doubles the rows are stitched,
  so there is no crack.
- Elevation is the DEM's own value at the vertex (bilinear between its four cells). Nothing is smoothed, exaggerated,
  invented or filled (LAWS L3). Normals are the real surface's slope (central differences on the DEM), not the mesh's.
- Summits are kept (keep_summits): a 60 m lattice can step over a sharp summit and read it 20 m low. Each kept vertex
  owns the ground half a cell around it; where the highest DEM point of that ground (searched every summit_sample_m)
  is higher than the highest point of all eight neighbours' ground, the vertex is moved onto it. It stays inside its
  own cell, and its position and height are the DEM's. No other vertex moves.
- Only what the track's roads can see is kept: a vertex is kept if it is visible from any viewpoint on the road line
  (eye viewshed_eye_m over the DEM ground there), within viewshed_margin_deg of being visible, or within
  viewshed_margin_cells cells of such a vertex. Ground nearer a viewpoint than blocker_min_m never hides anything (the
  track rebuilds its own near ground). Everything else, the far side of every ridge, is dropped.
- Visual only: every object is named <mesh_prefix>_<nnn>, no digit prefix, at most max_verts_per_object vertices.

The peak gate that judges the result is tools/backdrop_peak_gate.py; it reads the OBJ this writes, nothing else of ours.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

WGS84_A = 6378137.0
WGS84_F = 1.0 / 298.257223563
WGS84_B = WGS84_A * (1.0 - WGS84_F)
EARTH_R = 6371000.0          # the curvature radius the horizon study uses (horizon_3dep.py)

DEFAULTS = {
    "arc_deg": [180.0, 335.0],
    "near_m": 2000.0,
    "far_m": 112000.0,
    "pixel_rad": 0.001,
    "min_cell_m": 20.0,
    "radial_factor": 2.0,
    "refraction_k": 0.13,
    "viewshed_eye_m": 12.0,
    "viewshed_margin_deg": 0.1,
    "viewshed_margin_cells": 2,
    "viewpoint_spacing_m": 100.0,
    "blocker_min_m": 2000.0,
    "max_verts_per_object": 60000,
    "mesh_prefix": "BACKDROP_FR",
    "uv_tile_m": 1000.0,
    "keep_summits": True,
    "summit_sample_m": 8.0,
}


# --- geodesy on the WGS84 ellipsoid (Vincenty; vectorised) ------------------------------------------------------------

def geod_direct(lon1, lat1, az_deg, s):
    """(lon, lat) reached from (lon1, lat1) along true azimuth az_deg (deg) after s metres. az_deg and s broadcast."""
    a1 = np.radians(np.asarray(az_deg, float)); s = np.asarray(s, float)
    f, b = WGS84_F, WGS84_B
    tan_u1 = (1 - f) * math.tan(math.radians(lat1)); cos_u1 = 1 / math.sqrt(1 + tan_u1 ** 2); sin_u1 = tan_u1 * cos_u1
    sig1 = np.arctan2(tan_u1, np.cos(a1)); sin_al = cos_u1 * np.sin(a1); cos2_al = 1 - sin_al ** 2
    u2 = cos2_al * (WGS84_A ** 2 - b ** 2) / b ** 2
    A = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    B = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    sig = s / (b * A)
    for _ in range(8):
        cos2sm = np.cos(2 * sig1 + sig); sin_s = np.sin(sig); cos_s = np.cos(sig)
        dsig = B * sin_s * (cos2sm + B / 4 * (cos_s * (-1 + 2 * cos2sm ** 2)
                                             - B / 6 * cos2sm * (-3 + 4 * sin_s ** 2) * (-3 + 4 * cos2sm ** 2)))
        sig = s / (b * A) + dsig
    cos2sm = np.cos(2 * sig1 + sig); sin_s = np.sin(sig); cos_s = np.cos(sig)
    t = sin_u1 * sin_s - cos_u1 * cos_s * np.cos(a1)
    lat2 = np.arctan2(sin_u1 * cos_s + cos_u1 * sin_s * np.cos(a1), (1 - f) * np.sqrt(sin_al ** 2 + t ** 2))
    lam = np.arctan2(sin_s * np.sin(a1), cos_u1 * cos_s - sin_u1 * sin_s * np.cos(a1))
    C = f / 16 * cos2_al * (4 + f * (4 - 3 * cos2_al))
    L = lam - (1 - C) * f * sin_al * (sig + C * sin_s * (cos2sm + C * cos_s * (-1 + 2 * cos2sm ** 2)))
    return lon1 + np.degrees(L), np.degrees(lat2)


def geod_inverse(lon1, lat1, lon2, lat2):
    """(true azimuth deg at point 1, geodesic distance m) from (lon1, lat1) to arrays (lon2, lat2)."""
    lon2 = np.atleast_1d(np.asarray(lon2, float)); lat2 = np.atleast_1d(np.asarray(lat2, float))
    f, b = WGS84_F, WGS84_B
    L = np.radians(lon2 - lon1)
    u1 = math.atan((1 - f) * math.tan(math.radians(lat1))); u2 = np.arctan((1 - f) * np.tan(np.radians(lat2)))
    su1, cu1 = math.sin(u1), math.cos(u1); su2, cu2 = np.sin(u2), np.cos(u2)
    lam = L.copy()
    for _ in range(30):
        sl, cl = np.sin(lam), np.cos(lam)
        sin_s = np.sqrt((cu2 * sl) ** 2 + (cu1 * su2 - su1 * cu2 * cl) ** 2)
        cos_s = su1 * su2 + cu1 * cu2 * cl
        sig = np.arctan2(sin_s, cos_s)
        with np.errstate(invalid="ignore", divide="ignore"):
            sin_al = np.where(sin_s > 0, cu1 * cu2 * sl / sin_s, 0.0)
            cos2_al = 1 - sin_al ** 2
            cos2sm = np.where(cos2_al > 0, cos_s - 2 * su1 * su2 / cos2_al, 0.0)
        C = f / 16 * cos2_al * (4 + f * (4 - 3 * cos2_al))
        lam = L + (1 - C) * f * sin_al * (sig + C * sin_s * (cos2sm + C * cos_s * (-1 + 2 * cos2sm ** 2)))
    sl, cl = np.sin(lam), np.cos(lam)
    uu = cos2_al * (WGS84_A ** 2 - b ** 2) / b ** 2
    A = 1 + uu / 16384 * (4096 + uu * (-768 + uu * (320 - 175 * uu)))
    B = uu / 1024 * (256 + uu * (-128 + uu * (74 - 47 * uu)))
    dsig = B * sin_s * (cos2sm + B / 4 * (cos_s * (-1 + 2 * cos2sm ** 2)
                                         - B / 6 * cos2sm * (-3 + 4 * sin_s ** 2) * (-3 + 4 * cos2sm ** 2)))
    s = b * A * (sig - dsig)
    az = np.degrees(np.arctan2(cu2 * sl, cu1 * su2 - su1 * cu2 * cl)) % 360.0
    return az, s


def to_local(origin_lon, origin_lat, lon, lat):
    """Local east (x) and north (z) metres of (lon, lat): true azimuth and geodesic distance from the origin."""
    az, s = geod_inverse(origin_lon, origin_lat, lon, lat)
    a = np.radians(az)
    return s * np.sin(a), s * np.cos(a)


def curvature_drop(d, k):
    """How far the ground at distance d sits below the observer's flat plane, with refraction k."""
    return np.asarray(d, float) ** 2 * (1.0 - k) / (2.0 * EARTH_R)


# --- the DEM ----------------------------------------------------------------------------------------------------------

class TileDem:
    """USGS 3DEP 1/3 arc-second staged tiles (USGS_13_nXXwYYY.tif, 1 x 1 degree, named by their NW corner), read as they
    are needed. elev(lon, lat) is bilinear between the four cell centres around the point; NaN where there is no data."""

    def __init__(self, directory):
        self.dir = Path(directory); self.t = {}; self.used = {}

    def _tile(self, n, w):
        key = (int(n), int(w))
        if key not in self.t:
            p = self.dir / f"USGS_13_n{key[0]:02d}w{key[1]:03d}.tif"
            if not p.exists():
                self.t[key] = None
            else:
                import rasterio
                with rasterio.open(p) as src:
                    a = src.read(1).astype(np.float32); tr = src.transform
                a[a < -1000] = np.nan
                self.t[key] = (a, tr.c, tr.f, tr.a, -tr.e)
                self.used[p.name] = p.stat().st_size
        return self.t[key]

    def elev(self, lon, lat):
        lon = np.asarray(lon, float); lat = np.asarray(lat, float); shape = lon.shape
        lon = lon.ravel(); lat = lat.ravel()
        out = np.full(lon.shape, np.nan)
        kn = np.ceil(lat).astype(int); kw = np.ceil(-lon).astype(int)
        for n, w in {(int(a), int(b)) for a, b in np.unique(np.stack([kn, kw], 1), axis=0)}:
            tile = self._tile(n, w)
            if tile is None:
                continue
            a, x0, y0, dx, dy = tile
            m = (kn == n) & (kw == w)
            fx = (lon[m] - x0) / dx - 0.5; fy = (y0 - lat[m]) / dy - 0.5
            ix = np.clip(np.floor(fx).astype(int), 0, a.shape[1] - 2); iy = np.clip(np.floor(fy).astype(int), 0, a.shape[0] - 2)
            tx = fx - ix; ty = fy - iy
            out[m] = (a[iy, ix] * (1 - tx) * (1 - ty) + a[iy, ix + 1] * tx * (1 - ty)
                      + a[iy + 1, ix] * (1 - tx) * ty + a[iy + 1, ix + 1] * tx * ty)
        return out.reshape(shape)


# --- the lattice ------------------------------------------------------------------------------------------------------

def lattice(p):
    """The rings, near to far: [{'r': radius, 'k': band, 'n': columns}], and the finest column count n0. Band k has an
    angular step of (arc / n0) * 2^k; a ring's radial step is radial_factor cells; every band edge is a ring both bands
    share, owned by the finer (outer) band."""
    b0, b1 = p["arc_deg"]; arc = math.radians(b1 - b0)
    r_fine = p["min_cell_m"] / p["pixel_rad"]                      # outside this the step is pixel_rad
    kmax = 0
    while p["near_m"] < r_fine / 2 ** kmax:
        kmax += 1
    n0 = int(math.ceil(arc / p["pixel_rad"] / 2 ** kmax)) * 2 ** kmax
    dth0 = arc / n0
    rings = []
    for k in range(kmax, -1, -1):
        r_in = max(p["near_m"], r_fine / 2 ** k) if k else max(p["near_m"], r_fine)
        r_out = p["far_m"] if k == 0 else min(p["far_m"], r_fine / 2 ** (k - 1))
        if r_out <= r_in:
            continue
        m = max(1, int(math.ceil(math.log(r_out / r_in) / math.log(1 + p["radial_factor"] * dth0 * 2 ** k))))
        for j in range(m + (1 if k == 0 else 0)):                  # the outer edge ring belongs to the next band
            rings.append({"r": r_in * (r_out / r_in) ** (j / m), "k": k, "n": n0 // 2 ** k})
    return rings, n0


def triangles(rings):
    """Triangles over the rings (vertex index = ring offset + column), wound so the face normal points up (+y in
    x east, y up, z north: the y of (b - a) x (c - a) is positive). Where the next ring has twice the columns the row
    is stitched with three triangles per cell."""
    off = np.cumsum([0] + [r["n"] + 1 for r in rings])
    out = []
    for i in range(len(rings) - 1):
        n = rings[i]["n"]; c = np.arange(n); a = off[i] + c; b = off[i] + c + 1
        if rings[i + 1]["n"] == n:
            d = off[i + 1] + c; e = off[i + 1] + c + 1
            out += [np.stack([a, d, e], 1), np.stack([a, e, b], 1)]
        else:                                                       # outer ring is twice as fine
            f0 = off[i + 1] + 2 * c; f1 = f0 + 1; f2 = f0 + 2
            out += [np.stack([a, f0, f1], 1), np.stack([a, f1, b], 1), np.stack([b, f1, f2], 1)]
    return np.concatenate(out).astype(np.int64), off


# --- the viewshed -----------------------------------------------------------------------------------------------------

def _upsample(a, factor):
    """One ring's values resampled linearly to `factor` times the columns (the end column kept)."""
    if factor == 1:
        return a
    t = np.arange(factor) / factor
    body = (a[:-1, None] * (1 - t) + a[1:, None] * t).ravel()
    return np.concatenate([body, a[-1:]])


def viewshed(rings, off, x, y, z, views, p):
    """True for every lattice vertex that some viewpoint sees, or misses by less than viewshed_margin_deg.

    The surface is taken at the finest angular step on every ring (coarser rings interpolated along the ring), so a
    near ridge blocks every bearing it spans. From a viewpoint, the surface points are binned by bearing (one bin =
    the finest step) and walked outward; a point is seen if nothing nearer in its bin stands higher. Points nearer
    the viewpoint than blocker_min_m hide nothing."""
    n0 = max(r["n"] for r in rings)
    bx, by, bz, own = [], [], [], []
    for i, r in enumerate(rings):
        f = n0 // r["n"]; s = slice(off[i], off[i + 1])
        bx.append(_upsample(x[s], f)); by.append(_upsample(y[s], f)); bz.append(_upsample(z[s], f))
        o = np.full(n0 + 1, -1, np.int64); o[::f] = np.arange(off[i], off[i + 1]); own.append(o)
    bx = np.concatenate(bx); by = np.concatenate(by); bz = np.concatenate(bz); own = np.concatenate(own)
    ok = ~np.isnan(by)
    bx, by, bz, own = bx[ok], by[ok], bz[ok], own[ok]
    bin_rad = math.radians(p["arc_deg"][1] - p["arc_deg"][0]) / n0
    margin = math.tan(math.radians(p["viewshed_margin_deg"]))
    seen = np.zeros(len(x), bool)
    mid = math.radians((p["arc_deg"][0] + p["arc_deg"][1]) / 2)
    for vx, vy, vz in views:
        dx = bx - vx; dz = bz - vz
        dist = np.hypot(dx, dz); dist[dist < 1.0] = 1.0
        tan_alt = (by - vy) / dist
        brg = (np.arctan2(dx, dz) - mid + math.pi) % (2 * math.pi)      # measured from opposite the arc's middle: no wrap
        bins = np.floor((brg - brg.min()) / bin_rad).astype(np.int64)
        order = np.lexsort((dist, bins))
        sb = bins[order]; st = tan_alt[order]
        block = np.where(dist[order] < p["blocker_min_m"], -1e3, st)
        # running maximum inside each bin: lift every bin onto its own level, accumulate, drop back
        lift = sb.astype(float) * 4e3
        run = np.maximum.accumulate(block + lift) - lift
        before = np.empty_like(run); before[0] = -np.inf; before[1:] = run[:-1]
        before[np.r_[True, sb[1:] != sb[:-1]]] = -np.inf
        vis = st >= before - margin
        hit = own[order][vis]
        seen[hit[hit >= 0]] = True
    return seen


# --- summits ----------------------------------------------------------------------------------------------------------

def keep_summits(rings, off, n0, arc_rad, origin, dem, usedmask, az, rad, lon, lat, elev, sample_m):
    """Move each used vertex that owns a summit onto it (see the module text). Edits az, rad, lon, lat, elev in place;
    returns how many moved. A vertex owns the ground within half a step of it along its ring and half-way to the rings
    either side; rings on a band edge and the arc's end columns are left alone."""
    best = np.full(len(az), -np.inf)
    b_az = az.copy(); b_rad = rad.copy(); b_lon = lon.copy(); b_lat = lat.copy()
    for i in range(1, len(rings) - 1):
        k = rings[i]["k"]; n = rings[i]["n"]
        if rings[i - 1]["k"] != k or rings[i + 1]["k"] != k:
            continue
        cols = np.flatnonzero(usedmask[off[i]:off[i + 1]]); cols = cols[(cols > 0) & (cols < n)]
        if not len(cols):
            continue
        idx = off[i] + cols; r = rings[i]["r"]; dth = math.degrees(arc_rad / n0 * 2 ** k)
        r_lo = math.sqrt(rings[i - 1]["r"] * r); r_hi = math.sqrt(r * rings[i + 1]["r"])
        na = max(1, int(math.ceil(r * math.radians(dth) / sample_m))); nr = max(1, int(math.ceil((r_hi - r_lo) / sample_m)))
        u = (np.arange(na) + 0.5) / na; w = (np.arange(nr) + 0.5) / nr
        a0 = az[idx]
        c00 = geod_direct(origin[0], origin[1], a0 - dth / 2, r_lo); c10 = geod_direct(origin[0], origin[1], a0 + dth / 2, r_lo)
        c01 = geod_direct(origin[0], origin[1], a0 - dth / 2, r_hi); c11 = geod_direct(origin[0], origin[1], a0 + dth / 2, r_hi)
        U = u[None, :, None]; W = w[None, None, :]

        def blend(q):                                                # the cell's corners blended: exact to millimetres at this size
            return (c00[q][:, None, None] * (1 - U) * (1 - W) + c10[q][:, None, None] * U * (1 - W)
                    + c01[q][:, None, None] * (1 - U) * W + c11[q][:, None, None] * U * W)
        slon = blend(0); slat = blend(1)
        e = dem.elev(slon, slat).reshape(len(cols), -1)
        e = np.where(np.isnan(e), -np.inf, e)
        j = e.argmax(1); rows = np.arange(len(cols))
        best[idx] = e[rows, j]
        ja, jr = np.divmod(j, nr)
        b_az[idx] = a0 + (u[ja] - 0.5) * dth; b_rad[idx] = r_lo + w[jr] * (r_hi - r_lo)
        b_lon[idx] = slon.reshape(len(cols), -1)[rows, j]; b_lat[idx] = slat.reshape(len(cols), -1)[rows, j]
    moved = 0
    for i in range(1, len(rings) - 1):
        k = rings[i]["k"]
        if rings[i - 1]["k"] != k or rings[i + 1]["k"] != k:
            continue
        here = best[off[i]:off[i + 1]]
        if not np.isfinite(here).any():
            continue
        nb = np.full(len(here), -np.inf)
        for ring in (i - 1, i, i + 1):
            row = best[off[ring]:off[ring + 1]]
            for shift in (-1, 0, 1):
                if ring == i and shift == 0:
                    continue
                sh = np.full(len(row), -np.inf)
                if shift == -1:
                    sh[1:] = row[:-1]
                elif shift == 1:
                    sh[:-1] = row[1:]
                else:
                    sh = row
                nb = np.maximum(nb, sh)
        top = np.flatnonzero(np.isfinite(here) & (here > nb) & (here > elev[off[i]:off[i + 1]]))
        g = off[i] + top
        az[g] = b_az[g]; rad[g] = b_rad[g]; lon[g] = b_lon[g]; lat[g] = b_lat[g]; elev[g] = best[g]
        moved += len(g)
    return moved


# --- the bake ---------------------------------------------------------------------------------------------------------

def road_viewpoints(road_lonlat, spacing_m, origin):
    """Points along the road line about spacing_m apart (the first always), as (lon, lat)."""
    lon = np.array([q[0] for q in road_lonlat], float); lat = np.array([q[1] for q in road_lonlat], float)
    x, z = to_local(origin[0], origin[1], lon, lat)
    s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(z)))])
    keep = [0]
    for i in range(1, len(s)):
        if s[i] - s[keep[-1]] >= spacing_m:
            keep.append(i)
    return lon[keep], lat[keep], float(s[-1])


def bake(params, origin, road_lonlat, dem, origin_elev_m=None, log=lambda *_: None):
    """Build the backdrop mesh. origin = (lon, lat); road_lonlat = [(lon, lat), ...]; dem.elev(lon, lat) -> metres.
    Returns {'objects': [{'name', 'v', 'vn', 'vt', 'tris'}], 'meta': {...}}."""
    p = dict(DEFAULTS); p.update(params or {})
    k = p["refraction_k"]
    if origin_elev_m is None:
        origin_elev_m = float(dem.elev(np.array([origin[0]]), np.array([origin[1]]))[0])
    rings, n0 = lattice(p)
    tris, off = triangles(rings)
    b0, b1 = p["arc_deg"]
    az = np.concatenate([np.linspace(b0, b1, r["n"] + 1) for r in rings])
    rad = np.concatenate([np.full(r["n"] + 1, r["r"]) for r in rings])
    band = np.concatenate([np.full(r["n"] + 1, r["k"]) for r in rings])
    log(f"lattice: {len(rings)} rings, {len(az):,} vertices, {len(tris):,} triangles before the viewshed")
    lon, lat = geod_direct(origin[0], origin[1], az, rad)
    elev = dem.elev(lon, lat)
    a = np.radians(az)
    x = rad * np.sin(a); z = rad * np.cos(a); y = elev - origin_elev_m - curvature_drop(rad, k)
    nodata = np.isnan(elev)

    # viewpoints: the road line, eye viewshed_eye_m over the DEM ground, in the baked frame
    vlon, vlat, road_len = road_viewpoints(road_lonlat, p["viewpoint_spacing_m"], origin)
    vx, vz = to_local(origin[0], origin[1], vlon, vlat)
    vy = dem.elev(vlon, vlat) - origin_elev_m - curvature_drop(np.hypot(vx, vz), k) + p["viewshed_eye_m"]
    if np.isnan(vy).any():
        raise SystemExit("backdrop_bake: the DEM has no ground under part of the road line")
    log(f"viewshed: {len(vx)} viewpoints along {road_len:.0f} m of road")
    seen = viewshed(rings, off, x, y, z, list(zip(vx, vy, vz)), p)
    seen &= ~nodata
    mark = seen.copy()
    good = ~nodata[tris].any(1)
    tris = tris[good]
    for _ in range(int(p["viewshed_margin_cells"])):
        touched = mark[tris].any(1)
        mark[tris[touched].ravel()] = True
    keep = mark[tris].any(1)
    tris = tris[keep]
    used = np.unique(tris)
    log(f"kept: {len(used):,} vertices, {len(tris):,} triangles ({int(seen.sum()):,} vertices seen directly)")

    summits = 0
    if p["keep_summits"]:
        usedmask = np.zeros(len(az), bool); usedmask[used] = True
        summits = keep_summits(rings, off, n0, math.radians(b1 - b0), origin, dem, usedmask, az, rad, lon, lat, elev,
                               p["summit_sample_m"])
        a = np.radians(az)
        x = rad * np.sin(a); z = rad * np.cos(a); y = elev - origin_elev_m - curvature_drop(rad, k)
        log(f"summits kept: {summits:,} vertices moved onto the DEM's own high point")

    # real normals: the DEM's own slope at each kept vertex, east and north, over about one cell
    ring_r = np.concatenate([np.full(r["n"] + 1, r["r"]) for r in rings])        # the lattice's own radii (summits moved)
    cell = ring_r[used] * (math.radians(b1 - b0) / n0) * 2.0 ** band[used]
    h = np.maximum(15.0, cell / 2)
    la = np.radians(lat[used])
    m_lat = 111132.92 - 559.82 * np.cos(2 * la); m_lon = 111412.84 * np.cos(la) - 93.5 * np.cos(3 * la)
    dlon = h / m_lon; dlat = h / m_lat
    e_e = dem.elev(lon[used] + dlon, lat[used]); e_w = dem.elev(lon[used] - dlon, lat[used])
    e_n = dem.elev(lon[used], lat[used] + dlat); e_s = dem.elev(lon[used], lat[used] - dlat)
    gx = np.where(np.isnan(e_e) | np.isnan(e_w), 0.0, (np.nan_to_num(e_e, nan=0) - np.nan_to_num(e_w, nan=0)) / (2 * h))
    gz = np.where(np.isnan(e_n) | np.isnan(e_s), 0.0, (np.nan_to_num(e_n, nan=0) - np.nan_to_num(e_s, nan=0)) / (2 * h))
    nrm = np.stack([-gx, np.ones_like(gx), -gz], 1); nrm /= np.linalg.norm(nrm, axis=1)[:, None]

    remap = np.full(len(az), -1, np.int64); remap[used] = np.arange(len(used))
    V = np.stack([x[used], y[used], z[used]], 1); T = remap[tris]
    UV = np.stack([x[used], z[used]], 1) / p["uv_tile_m"]

    # objects: by 10-degree sector and band, then cut at max_verts_per_object
    cen_az = az[used][T[:, 0]]; cen_k = band[used][T[:, 0]]
    sector = np.floor((cen_az - b0) / 10.0).astype(int)
    key = sector * 100 + cen_k
    objects = []
    cap = int(p["max_verts_per_object"])
    for kk in np.unique(key):
        tk = T[key == kk]
        tk = tk[np.lexsort((tk[:, 0],))]
        start = 0
        while start < len(tk):
            lo, hi = 1, len(tk) - start                            # the most triangles whose vertices fit under cap
            if len(np.unique(tk[start:])) <= cap:
                lo = hi
            else:
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if len(np.unique(tk[start:start + mid])) <= cap:
                        lo = mid
                    else:
                        hi = mid - 1
            part = tk[start:start + lo]; start += lo
            vid, inv = np.unique(part, return_inverse=True)
            objects.append({"name": f"{p['mesh_prefix']}_{len(objects):03d}", "v": V[vid], "vn": nrm[vid], "vt": UV[vid],
                            "tris": inv.reshape(-1, 3)})

    dist_used = rad[used]
    cellsz = cell
    meta = {
        "params": p, "origin_lon_lat": [origin[0], origin[1]], "origin_elev_m": round(origin_elev_m, 3),
        "frame": "x east, y up, z north, metres; origin at origin_lon_lat, y = 0 at origin_elev_m; vertex at true geodesic "
                 "azimuth and distance from the origin (WGS84); y = elevation - origin_elev_m - d^2 (1 - k) / (2 * 6371000)",
        "lattice": {"rings": len(rings), "finest_columns": n0, "finest_step_rad": math.radians(b1 - b0) / n0,
                    "bands": sorted({r["k"] for r in rings}), "vertices": int(len(az)), "nodata_vertices": int(nodata.sum())},
        "viewshed": {"viewpoints": int(len(vx)), "road_length_m": round(road_len, 1), "seen_vertices": int(seen.sum())},
        "vertices": int(len(used)), "triangles": int(len(T)), "objects": len(objects), "summits_kept": int(summits),
        "max_object_vertices": max((len(o["v"]) for o in objects), default=0),
        "extent": {"x_m": [round(float(V[:, 0].min()), 1), round(float(V[:, 0].max()), 1)],
                   "y_m": [round(float(V[:, 1].min()), 1), round(float(V[:, 1].max()), 1)],
                   "z_m": [round(float(V[:, 2].min()), 1), round(float(V[:, 2].max()), 1)],
                   "distance_km": [round(float(dist_used.min()) / 1000, 2), round(float(dist_used.max()) / 1000, 2)],
                   "bearing_deg": [round(float(az[used].min()), 2), round(float(az[used].max()), 2)],
                   "elevation_m": [round(float(elev[used].min()), 1), round(float(elev[used].max()), 1)]},
        "cell_m": {"min": round(float(cellsz.min()), 1), "max": round(float(cellsz.max()), 1),
                   "at_60km": round(60000 * math.radians(b1 - b0) / n0, 1)},
    } if len(used) else {"params": p, "vertices": 0, "triangles": 0, "objects": 0}
    return {"objects": objects, "meta": meta}


def write_obj(path, objects):
    """v / vt / vn per vertex with one shared index (f a/a/a), one `o` per object. Returns the file's sha256."""
    path = Path(path); base = 0
    with open(path, "w", encoding="utf-8") as f:
        f.write("# backdrop: x east, y up, z north, metres. tools/backdrop_bake.py\n")
        for o in objects:
            f.write(f"o {o['name']}\nusemtl {o['name'].rsplit('_', 1)[0]}_mat\n")
            f.write("".join(f"v {a:.2f} {b:.2f} {c:.2f}\n" for a, b, c in o["v"].tolist()))
            f.write("".join(f"vt {a:.4f} {b:.4f}\n" for a, b in o["vt"].tolist()))
            f.write("".join(f"vn {a:.4f} {b:.4f} {c:.4f}\n" for a, b, c in o["vn"].tolist()))
            t = o["tris"] + base + 1
            f.write("".join(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n" for a, b, c in t.tolist()))
            base += len(o["v"])
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def load_road(path):
    """A road line as [(lon, lat)]: lap_line.plan.json's {"nodes": [{"lon", "lat"}]}, a GeoJSON LineString / Feature /
    FeatureCollection (every line in it), or a bare list of [lon, lat]."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(d, dict) and "nodes" in d:
        return [(n["lon"], n["lat"]) for n in d["nodes"]]
    if isinstance(d, list):
        return [(q[0], q[1]) for q in d]
    out = []

    def walk(g):
        if g.get("type") == "FeatureCollection":
            for ft in g["features"]:
                walk(ft)
        elif g.get("type") == "Feature":
            walk(g["geometry"])
        elif g.get("type") == "LineString":
            out.extend((q[0], q[1]) for q in g["coordinates"])
        elif g.get("type") == "MultiLineString":
            for ln in g["coordinates"]:
                out.extend((q[0], q[1]) for q in ln)
    walk(d)
    if not out:
        raise SystemExit(f"backdrop_bake: no road line in {path}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("config", help="the shared bake config (tracks/_reference/front-range/bake.config.json)")
    ap.add_argument("track", help="a key of the config's tracks")
    ap.add_argument("--dem", required=True, help="directory holding the USGS_13_*.tif tiles (outside git)")
    ap.add_argument("--out", required=True, help="output directory (outside git: the OBJ is large)")
    a = ap.parse_args(argv)
    cfg_path = Path(a.config).resolve(); cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    if a.track not in cfg["tracks"]:
        raise SystemExit(f"backdrop_bake: {a.track} is not in {cfg_path.name} (has: {', '.join(cfg['tracks'])})")
    t = cfg["tracks"][a.track]
    root = cfg_path.parents[3]                                      # tracks/_reference/front-range/<config> -> repo root
    params = dict(cfg.get("params", {})); params.update(t.get("params", {}))
    road = load_road(root / t["road_line"])
    dem = TileDem(a.dem)
    res = bake(params, tuple(t["origin_lon_lat"]), road, dem, t.get("origin_elev_m"), log=lambda s: print(s, flush=True))
    if not res["objects"]:
        raise SystemExit("backdrop_bake: nothing to write (no visible terrain)")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    obj = out / f"{t.get('slug', a.track)}_backdrop.obj"
    sha = write_obj(obj, res["objects"])
    meta = res["meta"]
    meta.update({"track": a.track, "obj": obj.name, "obj_sha256": sha, "obj_bytes": obj.stat().st_size,
                 "road_line": t["road_line"], "dem_tiles": dem.used, "config": str(cfg_path.relative_to(root))})
    (out / f"{t.get('slug', a.track)}_backdrop.bake.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    e = meta["extent"]
    print(f"{obj}: {meta['triangles']:,} triangles, {meta['vertices']:,} vertices, {meta['objects']} objects; "
          f"{e['distance_km'][0]}-{e['distance_km'][1]} km, bearing {e['bearing_deg'][0]}-{e['bearing_deg'][1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
