"""The real edge: ground beside the road built as a road builder would cut and fill it, on real 3DEP ground.

Lookout Lariat V3 (ledger 0048, V3-PLAN P3a ``terrain_cutfill`` + "the station-matched seat"), opt-in per track
(``track.config.json`` ``underlay.terrain`` = ``"cutfill"``; read by scripts/geometry/underlay_draft.py, which only
the Lariat runs). Pure stdlib, no ``bpy``: it returns meshes the underlay writes into ``GEN_terrain``.

WHY (2026-10-12, the verifiers of the integrated Drive-1 build). The underlay's placeholder terrain was the 40 m
3DEP raster (upsampled to 20 m), pinned under the pavement on 2.5 m sub-cells and held at road height within one
sub-cell diagonal (3.5 m) of it, and the prep then held a 3 m band past the pavement edge at road height and
feathered it over 6 m. Measured on both builds: the ground 1-2 m past the verge sat within +-0.2 / 0.3 m of the road
on ~100 % of the lap, so D4 A ("real width, then the real edge: rock cut, ditch or drop") drove as 6.6 m of road +
0.4 m of gravel + 2-3 m of flat grass, and Drive 1 could not answer D4. Between stacked legs the raw survey left 137
ground vertices closer in height to the other leg's road (the L4 gate), and grass triangles straddling a crossfalling
pavement edge stood millimetres over the lane (400 soft-top samples a layout).

WHAT IT BUILDS (two meshes, both ``1GRASS``):

1. ``edge`` — an EDGE-ALIGNED strip per side, station by station, so no ground triangle ever straddles the pavement
   or the verge edge:
   - under the pavement: the road's own cross-section points (left edge, centre, right edge), ``GROUND_CLEAR_M``
     below the road at every station (contact everywhere, exactly the road's shape: no grass can stand in the lane);
   - the verge's outer edge (every station, welded in plan to the D4 verge's outer edge), ``GROUND_CLEAR_M`` below it;
   - the cross-section beyond it, every ``SPARSE_M`` along the road, at ``STRIP_L`` metres past the verge edge: the
     ROAD-CONSTRUCTION section on the real ground ``g`` (below):
       upper (cut)  = a 0.4 x 1.2 m toe ditch (foreslope 0.6 m, bottom to 1.2 m) then a 1:1 back-slope
       lower (fill) = 1.5:1 down from the verge edge
       ground       = clamp(g, lower, upper)
     (docs/ROAD-CONSTRUCTION.md: "toe ditch 0.4x1.2 m", "soil 1-1.5:1", "fill 1.5:1" [std]); where the real ground
     sits between the two lines it stays as surveyed, so a bench, a drop or a cut bank is the real one;
   - ``BAND_L`` rows past ``L_STRIP``: the strip's hidden overlap under the retained grid (``BAND_DROP_M`` below the
     grid's own triangles), so the hole cut in the grid is always covered.
2. ``grid`` — the 3DEP raster as before (``ribbon.grass_terrain``), every node within the 3DEP corridor re-heighted
   from the near-native corridor samples (``data/corridor.elev.json``, 5 m lateral) through the same section, the
   quads within ``REFINE_REACH_M`` of a verge edge refined to ``REFINE_CELL_M``; every triangle with a vertex
   closer than ``L_STRIP`` to its own verge edge is removed (the edge strip owns that ground).

STACKED LEGS (L4, A3). A point whose nearest lap point on ANOTHER leg (more than ``PAIR_ALONG_M`` along the lap,
within ``PAIR_PLAN_M`` in plan: verify_stacked_legs' own pair rule) exists is held on its own leg's side of the
mid-height between the two roads, ``STACK_MARGIN_M`` short of it: below it beside the lower leg (the cut), above it
beside the upper leg (the fill). The surface crosses the mid-height between grid nodes, at the plan midline, where
nearest-in-plan changes leg; no vertex is ever closer in height to the other leg's road. Strip rows stop
``CLIP_BACK_M`` short of the plan midline and of the centre of a hairpin (where the point is nearer another part of
the lap than its own station).

Every value is tagged: [std] = docs/ROAD-CONSTRUCTION.md; [invented] = new here, logged in fleet/GATES-CHANGELOG.md
(2026-10-12 "P2 fixed"); none of them judges anything (the gates do).
"""

from __future__ import annotations

import bisect
import json
import math
from pathlib import Path

from scripts.geometry import ribbon

GROUND_CLEAR_M = 0.02        # the prep's GROUND_CLEAR: ground 2 cm under the deck
DITCH_DEPTH_M = 0.4          # [std] ROAD-CONSTRUCTION "toe ditch 0.4x1.2 m"
DITCH_WIDTH_M = 1.2          # [std]
DITCH_FORE_M = 0.6           # [invented] the ditch's foreslope run (0.4 m in 0.6 m = 1.5:1, the fill slope)
CUT_SLOPE = 1.0              # [std] rise per metre: "soil 1-1.5:1" (weathered / hardpan 0.75-1:1), the steep end
FILL_SLOPE = 1.0 / 1.5       # [std] drop per metre: "fill 1.5:1"
STRIP_L = (0.6, 1.2, 2.0, 3.0)   # [invented] strip rows past the verge edge (the ditch, its back-slope toe)
L_STRIP = 3.0                # [invented] the strip owns the ground to here; the grid is cut back to it
BAND_L = (4.0, 5.5, 7.0)     # [invented] hidden overlap rows (>= L_STRIP + one refined sub-cell diagonal, 3.5 m)
BAND_DROP_M = 0.03           # [invented] the overlap sits this far under the retained grid
SPARSE_M = 2.5               # [invented] strip rows past the verge edge every >= this along the road
REFINE_CELL_M = 2.5          # the underlay's corridor sub-cell (V3-PLAN P3a: corridor tier <= 3 m)
REFINE_REACH_M = 12.0        # [invented] refine the grid quads with a node this close to a verge edge (+ a cell)
CORRIDOR_BLEND_M = 10.0      # build_mesh's corridor splice: the 3DEP corridor blends into the raster over 10 m
PAIR_PLAN_M = 40.0           # verify_stacked_legs.PAIR_PLAN_M (its pair rule, so both agree on what is stacked)
PAIR_ALONG_M = 150.0         # verify_stacked_legs.PAIR_ALONG_M
STACK_MARGIN_M = 0.10        # [invented] held this far on its own side of the mid-height
CLIP_BACK_M = 0.3            # [invented] strip rows stop this short of where the point stops being its station's
OWN_STATION_M = 3.0          # [invented] "its own station": the nearest lap point within this along the lap
LAP_CELL_M = 10.0

PARAMS = {k: globals()[k] for k in (
    "GROUND_CLEAR_M", "DITCH_DEPTH_M", "DITCH_WIDTH_M", "DITCH_FORE_M", "CUT_SLOPE", "FILL_SLOPE", "STRIP_L",
    "L_STRIP", "BAND_L", "BAND_DROP_M", "SPARSE_M", "REFINE_CELL_M", "REFINE_REACH_M", "CORRIDOR_BLEND_M",
    "PAIR_PLAN_M", "PAIR_ALONG_M", "STACK_MARGIN_M", "CLIP_BACK_M", "OWN_STATION_M")}


# --- the section ----------------------------------------------------------------------------------------------------

def upper_line(l: float, z_e: float) -> float:
    """The cut line at l metres past the verge edge: the toe ditch, then the 1:1 back-slope."""
    if l <= DITCH_FORE_M:
        return z_e - DITCH_DEPTH_M * max(0.0, l) / DITCH_FORE_M
    if l <= DITCH_WIDTH_M:
        return z_e - DITCH_DEPTH_M
    return z_e - DITCH_DEPTH_M + CUT_SLOPE * (l - DITCH_WIDTH_M)


def lower_line(l: float, z_e: float) -> float:
    """The fill line: 1.5:1 down from the verge edge."""
    return z_e - FILL_SLOPE * max(0.0, l)


def section(l: float, z_e: float, g: float) -> float:
    """Ground at l metres past the verge edge (edge height z_e) over real ground g."""
    return min(max(g, lower_line(l, z_e)), upper_line(l, z_e))


# --- the lap ---------------------------------------------------------------------------------------------------------

class Lap:
    """The centreline (local frame: x = E, y = up, z = N) with its cross-section offsets, for nearest-point queries
    in plan: (segment, t, plan distance, side +1 left / -1 right, station)."""

    def __init__(self, pts, secs, closed):
        self.closed = closed
        m = len(secs)
        self.m = m
        self.P = [pts[i] for i in range(m)]
        self.st = [0.0]
        for i in range(1, m):
            self.st.append(self.st[-1] + math.hypot(self.P[i][0] - self.P[i - 1][0], self.P[i][2] - self.P[i - 1][2]))
        self.lap = self.st[-1] + (math.hypot(self.P[0][0] - self.P[-1][0], self.P[0][2] - self.P[-1][2]) if closed else 0.0)
        # per station: left / right offset of the VERGE edge (capped, as the verge mesh) and edge heights
        self.off_l, self.off_r, self.ze_l, self.ze_r = [], [], [], []
        for i, (left, centre, right, vl, vr) in enumerate(secs):
            x, y, z = centre
            vl_, vr_ = (vl or left), (vr or right)
            self.off_l.append(math.hypot(vl_[0] - x, vl_[2] - z))
            self.off_r.append(math.hypot(vr_[0] - x, vr_[2] - z))
            self.ze_l.append(vl_[1])
            self.ze_r.append(vr_[1])
        self.nseg = m if closed else m - 1
        self.cells: dict = {}
        for k in range(self.nseg):
            a, b = self.P[k], self.P[(k + 1) % m]
            for ci in range(int(math.floor(min(a[0], b[0]) / LAP_CELL_M)), int(math.floor(max(a[0], b[0]) / LAP_CELL_M)) + 1):
                for cj in range(int(math.floor(min(a[2], b[2]) / LAP_CELL_M)), int(math.floor(max(a[2], b[2]) / LAP_CELL_M)) + 1):
                    self.cells.setdefault((ci, cj), []).append(k)

    def along(self, s1: float, s2: float) -> float:
        d = abs(s1 - s2)
        return min(d, self.lap - d) if self.closed else d

    def _seg(self, k, x, z):
        a, b = self.P[k], self.P[(k + 1) % self.m]
        dx, dz = b[0] - a[0], b[2] - a[2]
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[2]) * dz) / L2))
        px, pz = a[0] + t * dx, a[2] + t * dz
        d = math.hypot(x - px, z - pz)
        side = 1.0 if (dx * (z - a[2]) - dz * (x - a[0])) > 0 else -1.0     # + = left of travel
        L = math.sqrt(L2)
        s = self.st[k] + t * L
        return d, k, t, side, s

    def candidates(self, x, z, r):
        R = int(math.ceil(r / LAP_CELL_M))
        ci, cj = int(math.floor(x / LAP_CELL_M)), int(math.floor(z / LAP_CELL_M))
        seen = set()
        for di in range(-R, R + 1):
            for dj in range(-R, R + 1):
                for k in self.cells.get((ci + di, cj + dj), ()):
                    if k not in seen:
                        seen.add(k)
                        yield k

    def nearest(self, x, z, r=60.0):
        best = None
        for k in self.candidates(x, z, r):
            q = self._seg(k, x, z)
            if best is None or q[0] < best[0]:
                best = q
        return best

    def nearest_far(self, x, z, s_own, r=PAIR_PLAN_M, min_along=PAIR_ALONG_M):
        """the nearest lap point more than min_along from s_own along the lap and within r in plan, or None"""
        best = None
        for k in self.candidates(x, z, r):
            q = self._seg(k, x, z)
            if q[0] < r and self.along(q[4], s_own) > min_along and (best is None or q[0] < best[0]):
                best = q
        return best

    def interp(self, vals, k, t):
        return vals[k] * (1.0 - t) + vals[(k + 1) % self.m] * t

    def y_at(self, k, t):
        return self.P[k][1] * (1.0 - t) + self.P[(k + 1) % self.m][1] * t

    def describe(self, x, z):
        """(l past its own verge edge, edge height, nearest tuple) for a plan point, or None if no lap within 60 m"""
        q = self.nearest(x, z)
        if q is None:
            return None
        d, k, t, side, s = q
        off = self.interp(self.off_l if side > 0 else self.off_r, k, t)
        ze = self.interp(self.ze_l if side > 0 else self.ze_r, k, t)
        return d - off, ze, q


# --- natural ground -------------------------------------------------------------------------------------------------

class Natural:
    """3DEP ground in the local frame: the near-native corridor samples (data/corridor.elev.json: stations every 6 m,
    offsets every 5 m to +-60 m) where they reach, blended over their outer CORRIDOR_BLEND_M into the raster
    (data/heightfield.npy as projected), the raster elsewhere."""

    def __init__(self, grid_xyz, corridor: dict | None, origin_lonlat, elev0, mlon_mlat, mirror_x=False):
        self.g = grid_xyz
        self.ny, self.nx = len(grid_xyz), len(grid_xyz[0])
        self.x0, self.z0 = grid_xyz[0][0][0], grid_xyz[0][0][2]
        self.dx = grid_xyz[0][1][0] - self.x0
        self.dz = grid_xyz[1][0][2] - self.z0
        self.cor = None
        if corridor:
            lon0, lat0 = origin_lonlat
            mlon, mlat = mlon_mlat
            sx = -1.0 if mirror_x else 1.0
            pts = [(sx * (lo - lon0) * mlon, (la - lat0) * mlat) for lo, la in corridor["stations_lonlat"]]
            offs = [float(o) for o in corridor["offsets"]]
            rows = [[(None if v is None else float(v) - elev0) for v in row] for row in corridor["z"]]
            n = len(pts)
            tans = []
            for i in range(n):
                a, b = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
                tx, tz = b[0] - a[0], b[1] - a[1]
                L = math.hypot(tx, tz) or 1.0
                tans.append((tx / L, tz / L))
            cells: dict = {}
            for i, (x, z) in enumerate(pts):
                cells.setdefault((int(x // 30.0), int(z // 30.0)), []).append(i)
            self.cor = {"pts": pts, "tans": tans, "offs": offs, "rows": rows, "cells": cells,
                        "half": float(corridor["half_l"]), "step_l": float(corridor["step_l"]),
                        "step_s": float(corridor["step_s"]), "sx": sx}

    def raster(self, x, z):
        fi = (x - self.x0) / self.dx
        fj = (z - self.z0) / self.dz
        i0 = max(0, min(self.nx - 2, int(math.floor(fi))))
        j0 = max(0, min(self.ny - 2, int(math.floor(fj))))
        ti = max(0.0, min(1.0, fi - i0))
        tj = max(0.0, min(1.0, fj - j0))
        g = self.g
        a = g[j0][i0][1] * (1 - ti) + g[j0][i0 + 1][1] * ti
        b = g[j0 + 1][i0][1] * (1 - ti) + g[j0 + 1][i0 + 1][1] * ti
        return a * (1 - tj) + b * tj

    def _row(self, i, lat):
        c = self.cor
        fo = (lat + c["half"]) / c["step_l"]
        io = max(0, min(len(c["offs"]) - 2, int(math.floor(fo))))
        to = max(0.0, min(1.0, fo - io))
        z1, z2 = c["rows"][i][io], c["rows"][i][io + 1]
        if z1 is None or z2 is None:
            return None
        return z1 * (1 - to) + z2 * to

    def at(self, x, z):
        base = self.raster(x, z)
        c = self.cor
        if c is None:
            return base
        best = None
        ci, cj = int(x // 30.0), int(z // 30.0)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for i in c["cells"].get((ci + di, cj + dj), ()):
                    px, pz = c["pts"][i]
                    d2 = (px - x) ** 2 + (pz - z) ** 2
                    if best is None or d2 < best[0]:
                        best = (d2, i)
        if best is None:
            return base
        i = best[1]
        px, pz = c["pts"][i]
        tx, tz = c["tans"][i]
        dxn, dzn = x - px, z - pz
        lat = (-tz * dxn + tx * dzn) * c["sx"]            # signed lateral, left +, as heightfield sampled it
        alo = dxn * tx + dzn * tz
        if abs(lat) > c["half"] or abs(alo) > c["step_s"] * 1.5:
            return base
        v = self._row(i, lat)
        j = i + (1 if alo > 0 else -1)
        if 0 <= j < len(c["pts"]):
            qx, qz = c["pts"][j]
            dj_ = math.hypot(qx - px, qz - pz)
            if dj_ > 1e-6:
                t = max(0.0, min(1.0, abs(alo) / dj_))
                tx2, tz2 = c["tans"][j]
                lat2 = (-tz2 * (x - qx) + tx2 * (z - qz)) * c["sx"]
                v2 = self._row(j, lat2)
                if v is not None and v2 is not None:
                    v = v * (1 - t) + v2 * t
        if v is None:
            return base
        w = max(0.0, min(1.0, (c["half"] - abs(lat)) / CORRIDOR_BLEND_M))
        return w * v + (1.0 - w) * base


# --- the ground function ----------------------------------------------------------------------------------------------

class Ground:
    """H(x, z): the ground a node or strip point gets."""

    def __init__(self, lap: Lap, natural: Natural):
        self.lap = lap
        self.nat = natural
        self.stats = {"stacked_held": 0, "cut": 0, "fill": 0, "natural": 0}

    def stacked(self, x, z, q, h):
        lap = self.lap
        far = lap.nearest_far(x, z, q[4])
        if far is None:
            return h
        y_own = lap.y_at(q[1], q[2])
        y_oth = lap.y_at(far[1], far[2])
        mid = 0.5 * (y_own + y_oth)
        if y_oth >= y_own:
            if h > mid - STACK_MARGIN_M:
                self.stats["stacked_held"] += 1
                return mid - STACK_MARGIN_M
        elif h < mid + STACK_MARGIN_M:
            self.stats["stacked_held"] += 1
            return mid + STACK_MARGIN_M
        return h

    def height(self, x, z, fallback=None):
        """(height, l) — l past the own verge edge; fallback (the raster) beyond 60 m of any lap point"""
        dsc = self.lap.describe(x, z)
        g = self.nat.at(x, z)
        if dsc is None:
            return g, None
        l, ze, q = dsc
        if l < 0.0:                                   # under the pavement / verge: the strip owns it
            return min(g, ze - GROUND_CLEAR_M), l
        h = section(l, ze, g)
        k = "cut" if h < g - 1e-6 else ("fill" if h > g + 1e-6 else "natural")
        self.stats[k] += 1
        return self.stacked(x, z, q, h), l


# --- the edge strip ---------------------------------------------------------------------------------------------------

def _fan(tris, dense, sparse, sparse_at):
    """Triangles between a dense row (one vertex per station: ``dense[i]``) and a sparse row (``sparse[k]`` at station
    ``sparse_at[k]``, ascending, closing back to sparse[0] on a closed lap is the caller's last pair)."""
    for k in range(len(sparse) - 1):
        a, b = sparse_at[k], sparse_at[k + 1]
        mid = (a + b) // 2
        for i in range(a, b):
            tris.append((dense[i], dense[i + 1], sparse[k] if i < mid else sparse[k + 1]))
        tris.append((sparse[k], dense[mid], sparse[k + 1]))


def _quads(tris, row_a, row_b):
    for k in range(len(row_a) - 1):
        tris.append((row_a[k], row_a[k + 1], row_b[k + 1]))
        tris.append((row_a[k], row_b[k + 1], row_b[k]))


def edge_strip(pts, secs, closed, lap: Lap, ground: Ground, grid_surface):
    """The edge-aligned strip (local frame vertices, triangles; winding fixed by the caller)."""
    m = len(secs)
    st = lap.st
    # sparse stations: every >= SPARSE_M (always 0; on a closed lap the wrap returns to 0)
    sp = [0]
    for i in range(1, m):
        if st[i] - st[sp[-1]] >= SPARSE_M - 1e-9:
            sp.append(i)
    if not closed and sp[-1] != m - 1:
        sp.append(m - 1)
    if closed and lap.lap - st[sp[-1]] < 0.5 * SPARSE_M and len(sp) > 2:
        sp.pop()
    verts, tris = [], []

    def add(p):
        verts.append(p)
        return len(verts) - 1

    # dense rows: left verge edge, left road edge, centre, right road edge, right verge edge (all 2 cm down)
    dense = {k: [] for k in ("vl", "l", "c", "r", "vr")}
    for left, centre, right, vl, vr in secs:
        vl_, vr_ = (vl or left), (vr or right)
        for key, p in (("vl", vl_), ("l", left), ("c", centre), ("r", right), ("vr", vr_)):
            dense[key].append(add((p[0], p[1] - GROUND_CLEAR_M, p[2])))
    clipped = 0
    rows = {}                                         # (side, row) -> [vertex per sparse station]
    lat_rows = list(STRIP_L) + list(BAND_L)
    for side in (1, -1):
        for r in range(len(lat_rows)):
            rows[(side, r)] = []
        for i in sp:
            x, y, z = pts[i]
            tx, tz = ribbon._horiz_tangent(pts, i, closed)
            nx, nz = -tz, tx
            kcur = ribbon._signed_curvature(pts, i, closed)
            o_v = lap.off_l[i] if side > 0 else lap.off_r[i]
            z_e = lap.ze_l[i] if side > 0 else lap.ze_r[i]
            s_i = st[i]

            def pos(l):
                o = o_v + l
                oc = ribbon._cap_offset(side * o, kcur)
                o = abs(oc)
                return (x + side * nx * o, z + side * nz * o)

            def own(l):
                px, pz = pos(l)
                q = lap.nearest(px, pz, r=o_v + l + 5.0)
                return q is not None and lap.along(q[4], s_i) <= OWN_STATION_M + 1e-9

            # the reach: the last offset still its own station's (plan midline of a stacked pair, a hairpin's centre)
            reach = lat_rows[-1]
            if not own(reach):
                lo, hi = 0.0, reach
                if not own(lo):
                    hi = 0.0
                else:
                    for _ in range(18):
                        mid = 0.5 * (lo + hi)
                        if own(mid):
                            lo = mid
                        else:
                            hi = mid
                reach = max(0.0, lo - CLIP_BACK_M)
                clipped += 1
            for r, l in enumerate(lat_rows):
                ll = min(l, reach)
                px, pz = pos(ll)
                if l in BAND_L:
                    h = grid_surface(px, pz) - BAND_DROP_M      # hidden under the retained grid
                else:
                    h = section(ll, z_e, ground.nat.at(px, pz))
                q = lap.nearest(px, pz)
                if q is not None:
                    h = ground.stacked(px, pz, q, h)
                if ll <= 1e-6:
                    h = min(h, z_e - GROUND_CLEAR_M)
                rows[(side, r)].append(add((px, h, pz)))
    # triangles: dense under-road / under-verge strips (quads), then fan dense verge edge -> first sparse row,
    # then quads between sparse rows
    def ring(lst):
        return lst + [lst[0]] if closed else lst
    for a_, b_ in (("vl", "l"), ("l", "c"), ("c", "r"), ("r", "vr")):
        _quads(tris, ring(dense[a_]), ring(dense[b_]))
    sp_at = sp + ([m] if closed else [])
    dense_ext = {k: ring(v) for k, v in dense.items()}
    for side, key in ((1, "vl"), (-1, "vr")):
        first = rows[(side, 0)]
        _fan(tris, dense_ext[key], ring(first), sp_at)
        for r in range(len(lat_rows) - 1):
            _quads(tris, ring(rows[(side, r)]), ring(rows[(side, r + 1)]))
    return verts, tris, {"sparse_stations": len(sp), "rows_clipped": clipped}


# --- the grid ---------------------------------------------------------------------------------------------------------

def build(pts, secs, closed, grid_xyz, cell_m, corridor, origin_lonlat, elev0, mlon_mlat, *, mirror_x=False,
          skirt_m=500.0):
    """Both meshes in the LOCAL frame: {"edge": {vertices, tris}, "grid": {vertices, tris}, "report": {...}}."""
    lap = Lap(pts, secs, closed)
    nat = Natural(grid_xyz, corridor, origin_lonlat, elev0, mlon_mlat, mirror_x=mirror_x)
    ground = Ground(lap, nat)
    nyg, nxg = len(grid_xyz), len(grid_xyz[0])
    # 1. coarse nodes: re-height within the corridor's reach, and their l for the refine / cut decisions
    l_of = {}
    g2 = [list(row) for row in grid_xyz]
    near_reach = (nat.cor["half"] if nat.cor else 60.0)
    for j in range(nyg):
        for i in range(nxg):
            x, y, z = g2[j][i]
            h, l = ground.height(x, z)
            if l is None or l > near_reach:
                continue
            g2[j][i] = (x, h, z)
            l_of[(i, j)] = l
    N = max(1, int(math.ceil(cell_m / REFINE_CELL_M)))
    refine = set()
    for (i, j), l in l_of.items():
        if l is not None and l < REFINE_REACH_M + 0.45 * cell_m:
            for qi in (i - 1, i):
                for qj in (j - 1, j):
                    if 0 <= qi < nxg - 1 and 0 <= qj < nyg - 1:
                        refine.add((qi, qj))
    l_cache: dict = {}

    def height_at(x, z, base_y):
        h, l = ground.height(x, z)
        l_cache[(round(x, 3), round(z, 3))] = l
        return h

    g = ribbon.grass_terrain(g2, skirt_m=skirt_m, refine_quads=refine, refine_factor=N, height_at=height_at)
    gv, gt = g["vertices"], g["tris"]
    # 2. cut the grid back to L_STRIP from every verge edge
    lv = []
    for v in gv:
        key = (round(v[0], 3), round(v[2], 3))
        if key in l_cache:
            lv.append(l_cache[key])
            continue
        dsc = lap.describe(v[0], v[2])
        lv.append(dsc[0] if dsc is not None else None)
    keep = [t for t in gt if all(lv[k] is None or lv[k] >= L_STRIP for k in t)]
    used = sorted({k for t in keep for k in t})
    remap = {k: n for n, k in enumerate(used)}
    grid_v = [gv[k] for k in used]
    grid_t = [(remap[a], remap[b], remap[c]) for a, b, c in keep]
    # 3. the grid's own surface, for the strip's hidden overlap (exact: the retained triangles themselves)
    cell = 4.0
    th: dict = {}
    for n_, (a, b, c) in enumerate(grid_t):
        A, B, C = grid_v[a], grid_v[b], grid_v[c]
        for ci in range(int(min(A[0], B[0], C[0]) // cell), int(max(A[0], B[0], C[0]) // cell) + 1):
            for cj in range(int(min(A[2], B[2], C[2]) // cell), int(max(A[2], B[2], C[2]) // cell) + 1):
                th.setdefault((ci, cj), []).append(n_)

    def grid_surface(x, z):
        best = None
        for n_ in th.get((int(x // cell), int(z // cell)), ()):
            a, b, c = grid_t[n_]
            A, B, C = grid_v[a], grid_v[b], grid_v[c]
            d = (B[2] - C[2]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[2] - C[2])
            if abs(d) < 1e-12:
                continue
            w0 = ((B[2] - C[2]) * (x - C[0]) + (C[0] - B[0]) * (z - C[2])) / d
            w1 = ((C[2] - A[2]) * (x - C[0]) + (A[0] - C[0]) * (z - C[2])) / d
            w2 = 1.0 - w0 - w1
            if w0 >= -1e-6 and w1 >= -1e-6 and w2 >= -1e-6:
                y = w0 * A[1] + w1 * B[1] + w2 * C[1]
                if best is None or y > best:
                    best = y
        if best is not None:
            return best
        h, _l = ground.height(x, z)                    # in the hole: what the grid would have been
        return h
    ev, et, srep = edge_strip(pts, secs, closed, lap, ground, grid_surface)
    report = {"method": "terrain_cutfill (scripts/geometry/terrain_cutfill.py)", "params": PARAMS,
              "corridor_samples": bool(nat.cor), "grid_cell_m": round(cell_m, 2), "refined_quads": len(refine),
              "refine_factor": N, "grid_verts": len(grid_v), "grid_tris": len(grid_t),
              "grid_tris_removed_under_strip": len(gt) - len(keep),
              "edge_verts": len(ev), "edge_tris": len(et), **srep, "section_counts": dict(ground.stats)}
    return {"edge": {"vertices": ev, "tris": et}, "grid": {"vertices": grid_v, "tris": grid_t}, "report": report}


def load_corridor(proj: Path, n_src: int | None = None):
    """data/corridor.elev.json when it exists and was sampled on this centreline (its n_src), else None"""
    p = Path(proj) / "data" / "corridor.elev.json"
    if not p.is_file():
        return None
    c = json.loads(p.read_text(encoding="utf-8"))
    if n_src is not None and c.get("n_src") != n_src:
        return None
    return c
