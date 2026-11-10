"""The far ground's pure parts (ledger 0083 pass 4b; tools/far_ground_blend.py meshes it): the lidar product's sampler, the
seam's feather, the lattice beyond a track's 3DEP grid. No bpy; numpy only.

THE SEAM. The 3DEP grid's border vertices are kept exactly (the ring's inner edge IS the grid's border: one vertex, no
step). Each border vertex's residual r = lidar - grid is feathered out: a ring node at distance d past the grid's edge takes
lidar - w(d) r(nearest border node), w = 1 - smoothstep(d / feather_m), so the ground runs from the grid's own height at
the border to the lidar's own by feather_m, with no step and a grade change of at most 1.5 |r| / feather_m.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np


class Dem:
    """tools/lidar_ground.py's product: bilinear at local (x east, y north) metres, NAVD88; edges clamp"""

    def __init__(self, z, meta, fill=None, reach=None):
        self.z = np.asarray(z, np.float64)
        self.fill = fill
        self.reach = None if reach is None else np.asarray(reach, np.float64)
        self.x0, self.y0, self.c = float(meta["x0"]), float(meta["y0"]), float(meta["cell_m"])
        self.ny, self.nx = self.z.shape

    @classmethod
    def load(cls, data_dir: Path):
        meta = json.loads((data_dir / "far_ground.lidar.meta.json").read_text(encoding="utf-8"))
        fp = data_dir / "far_ground.lidar.fill.npy"
        rp = data_dir / "far_ground.lidar.reach.npy"     # ledger 0082 'Far ground (0.1.11)', opt-in: absent = None
        return cls(np.load(data_dir / "far_ground.lidar.npy"), meta, np.load(fp) if fp.exists() else None,
                   np.load(rp) if rp.exists() else None)

    def _f(self, x, y):
        fx = min(max((x - self.x0) / self.c - 0.5, 0.0), self.nx - 1.0)
        fy = min(max((y - self.y0) / self.c - 0.5, 0.0), self.ny - 1.0)
        return fx, fy

    def at(self, x, y):
        return self._bilinear(self.z, x, y)

    def _bilinear(self, z, x, y):
        fx, fy = self._f(x, y)
        i, j = int(fx), int(fy)
        i, j = min(i, self.nx - 2), min(j, self.ny - 2)
        tx, ty = fx - i, fy - j
        return float(z[j, i] * (1 - tx) * (1 - ty) + z[j, i + 1] * tx * (1 - ty) + z[j + 1, i] * (1 - tx) * ty
                     + z[j + 1, i + 1] * tx * ty)

    def reach_at(self, x, y):
        """ledger 0082 'Far ground (0.1.11)': metres in from the lidar's reach (data/far_ground.lidar.reach.npy; 0 where
        the lidar reaches, bilinear), None when the product has no reach grid"""
        return None if self.reach is None else self._bilinear(self.reach, x, y)

    def fill_at(self, x, y):
        """0 measured, 1 filled under cover, 2 filled past the tiles (the nearest cell's flag)"""
        if self.fill is None:
            return 0
        fx, fy = self._f(x, y)
        return int(self.fill[int(round(fy)), int(round(fx))])

    def inside(self, x, y):
        return self.x0 <= x <= self.x0 + self.nx * self.c and self.y0 <= y <= self.y0 + self.ny * self.c


def feather_w(d, feather_m):
    """1 at the grid's edge, smoothstep to 0 at feather_m"""
    if feather_m <= 0.0 or d >= feather_m:
        return 0.0
    if d <= 0.0:
        return 1.0
    t = d / feather_m
    return 1.0 - t * t * (3.0 - 2.0 * t)


def is_border(i, j, NX, NY):
    return 0 <= i <= NX - 1 and 0 <= j <= NY - 1 and (i in (0, NX - 1) or j in (0, NY - 1))


def ring_plan(NX, NY, reach_i, reach_j, step=1):
    """the lattice past a grid of NX x NY nodes (indices 0..NX-1, 0..NY-1), on every ``step``-th node of the grid's own
    lattice (a coarser tier: the grid's (NX - 1) and (NY - 1) must be multiples of it), reach_i / reach_j nodes out each
    side (whole steps). Returns (nodes, polygons): the new nodes [(i, j)] outside the grid, and each ring
    cell's outline counter-clockwise [(i, j), ...]: its four corners, and on a side that lies on the grid's border every
    border node between them, so the ring meets the finer grid with no T-junction"""
    if (NX - 1) % step or (NY - 1) % step:
        raise ValueError(f"a {NX} x {NY} grid has no {step}-node tier")
    ri, rj = reach_i // step * step, reach_j // step * step     # the caller rounds reach to whole steps
    nodes = [(i, j) for j in range(-rj, NY + rj, step) for i in range(-ri, NX + ri, step)
             if not (0 <= i <= NX - 1 and 0 <= j <= NY - 1)]
    polys = []
    for j in range(-rj, NY - 1 + rj, step):
        for i in range(-ri, NX - 1 + ri, step):
            if 0 <= i and i + step <= NX - 1 and 0 <= j and j + step <= NY - 1:
                continue                                       # the grid's own
            out = []
            for a, b, da, db in ((i, j, 1, 0), (i + step, j, 0, 1), (i + step, j + step, -1, 0), (i, j + step, 0, -1)):
                out.append((a, b))
                for k in range(1, step):
                    q = (a + da * k, b + db * k)
                    if is_border(q[0], q[1], NX, NY) and is_border(a, b, NX, NY) and is_border(a + da * step, b + db * step, NX, NY):
                        out.append(q)
            polys.append(out)
    return nodes, polys


def clamp_node(i, j, NX, NY):
    """the grid's border node nearest a ring node (the lattice is the grid's own, so this is its nearest border point)"""
    return min(max(i, 0), NX - 1), min(max(j, 0), NY - 1)


def ring_height(lidar_z, r_border, d, feather_m):
    """a ring node's height: the lidar's, less the border residual feathered over feather_m"""
    return lidar_z - feather_w(d, feather_m) * r_border


def keep_today(z_lidar, z_today, d_beyond, keep_feather_m):
    """ledger 0082 'Far ground (0.1.11)' (terrain.far_ground "beyond": "keep"): a node past the lidar's reach keeps TODAY's
    ground, feathered from the lidar's fill at the reach (d_beyond 0) to today's by keep_feather_m in (no step). Today's
    ground absent there (the old skirt's empty corners): the fill while the feather still holds it, else None (no ground,
    as today)"""
    w = feather_w(d_beyond, keep_feather_m)
    if z_today is None:
        return z_lidar if w > 0.0 else None
    return z_today + w * (z_lidar - z_today)

