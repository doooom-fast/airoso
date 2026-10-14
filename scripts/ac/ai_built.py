"""The BUILT world an AI line is judged against: the gate OBJ's walls and road surface (ledger 0052).

``data/track.<layout>.obj`` (scripts.modkit.kn5_to_gate_obj: the road kn5 + the race kn5 + that layout's
closure kn5, decoded from the SHIPPED files, ENGINE frame x=E, y=up, z=N) is what a car on the layout hits.
The AI line writer (``scripts.ac.write_ai_line``, opt-in ``ai`` block) seats its points on the built ``1ROAD``
surface and clamps its side widths at the built ``1WALL`` faces from it, and the gate
(``tools/verify_ai_line.py``) measures the written line against it — L5: never the declaration that placed
the line.

Pure python (the repo's interpreter has no numpy): an 80 MB race gate OBJ reads in ~10-20 s.

* ``read_gate_obj(path)`` -> ``BuiltObj``: the vertices, every ``1WALL_*`` edge as a horizontal footprint
  segment (projected to XZ, de-duplicated at 1 cm, with the y range it spans), every ``1ROAD_*`` triangle.
* ``WallIndex``: ``nearest(x, y, z)`` = horizontal distance to the nearest wall footprint segment whose y range
  reaches into the point's layer band (L4: a wall on another leg of a stack is never "near"); ``ray(x, y, z,
  dx, dz, reach)`` = distance along a horizontal ray to the first wall footprint it crosses.
* ``RoadSurface``: ``sample(x, y, z)`` = (surface y, unit normal facing up) of the ``1ROAD`` triangle under the
  point nearest its height, within the layer band; None off the road.
"""

from __future__ import annotations

import math
from array import array
from pathlib import Path

WALL_PREFIX = "1WALL_"
ROAD_PREFIX = "1ROAD_"
CELL_M = 4.0               # spatial index cell (walls and road triangles)
LAYER_BELOW_M = 2.0        # a wall / surface counts for a point when it reaches into [y - this, y + LAYER_ABOVE_M]
LAYER_ABOVE_M = 4.0        # (the diagnosis' filter, L4: the other leg of a stack is never near)
SURFACE_BAND_M = 3.0       # a road triangle seats a point only within this height of it
DEDUP_M = 0.01             # wall footprint segments equal to 1 cm are one segment


AI_FIELDS = ("speed", "gas", "brake", "obsolete_lat_g", "radius", "side_left", "side_right", "camber",
             "direction", "nx", "ny", "nz", "length", "fx", "fy", "fz", "tag", "grade")


def read_ai(path: Path | str) -> dict:
    """Decode a ``fast_lane.ai`` v7 (RESEARCH §B6 / actools AiFile): header, points, the 18 extras per point,
    hasGrid. Positions are as written (the kn5 frame)."""
    import struct
    d = Path(path).read_bytes()
    ver, n, lap, samp = struct.unpack_from("<4i", d, 0)
    off = 16
    pos, L, ids = [], [], []
    for i in range(n):
        x, y, z, l, k = struct.unpack_from("<4fi", d, off + i * 20)
        pos.append((x, y, z)); L.append(l); ids.append(k)
    off += 20 * n
    out = {"version": ver, "n": n, "lap_ms": lap, "sample_count": samp, "pos": pos, "point_length": L, "id": ids,
           "has_grid": None}
    if off + 4 <= len(d):
        ne = struct.unpack_from("<i", d, off)[0]
        off += 4
        if ne == n and off + 72 * n <= len(d):
            cols = [[] for _ in AI_FIELDS]
            for i in range(n):
                row = struct.unpack_from("<18f", d, off + 72 * i)
                for c, v in zip(cols, row):
                    c.append(v)
            for name, c in zip(AI_FIELDS, cols):
                out[name] = c
            off += 72 * n
        if off + 4 <= len(d):
            out["has_grid"] = struct.unpack_from("<i", d, off)[0]
    return out


class BuiltObj:
    def __init__(self) -> None:
        self.x = array("d")
        self.y = array("d")
        self.z = array("d")
        self.wall_segs: list[tuple[float, float, float, float, float, float]] = []   # ax, az, bx, bz, ylo, yhi
        self.road_tris: list[tuple[int, int, int]] = []
        self.header = ""
        self.objects: dict[str, int] = {}


def read_gate_obj(path: Path | str, *, walls: bool = True, road: bool = True) -> BuiltObj:
    """Read a gate OBJ: every vertex, the ``1WALL_*`` footprint segments, the ``1ROAD_*`` triangles."""
    ob = BuiltObj()
    xs, ys, zs = ob.x, ob.y, ob.z
    wall_edges: set[tuple[int, int]] = set()
    cls = None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            c = line[:2]
            if c == "v ":
                p = line.split()
                xs.append(float(p[1])); ys.append(float(p[2])); zs.append(float(p[3]))
            elif c == "f ":
                if cls is None:
                    continue
                nv = len(xs)
                idx = []
                for t in line.split()[1:]:
                    i = int(t.split("/", 1)[0])
                    idx.append(i - 1 if i > 0 else nv + i)
                if cls == "w":
                    m = len(idx)
                    for a in range(m):
                        i, j = idx[a], idx[(a + 1) % m]
                        wall_edges.add((i, j) if i < j else (j, i))
                else:
                    for a in range(1, len(idx) - 1):
                        ob.road_tris.append((idx[0], idx[a], idx[a + 1]))
                ob.objects[cur] = ob.objects.get(cur, 0) + 1
            elif c == "o ":
                cur = line[2:].strip()
                cls = "w" if (walls and cur.startswith(WALL_PREFIX)) else "r" if (road and cur.startswith(ROAD_PREFIX)) else None
            elif c == "# " and not ob.header:
                ob.header = line[2:].strip()
    seen: dict[tuple[int, int, int, int], int] = {}
    q = 1.0 / DEDUP_M
    for i, j in wall_edges:
        ax, az, bx, bz = xs[i], zs[i], xs[j], zs[j]
        ka = (round(ax * q), round(az * q))
        kb = (round(bx * q), round(bz * q))
        if ka == kb:                                   # a vertical edge: its footprint is a point (kept by its
            continue                                   # neighbours' segments, which end there)
        key = ka + kb if ka < kb else kb + ka
        ylo, yhi = min(ys[i], ys[j]), max(ys[i], ys[j])
        k = seen.get(key)
        if k is None:
            seen[key] = len(ob.wall_segs)
            ob.wall_segs.append((ax, az, bx, bz, ylo, yhi))
        else:
            s = ob.wall_segs[k]
            ob.wall_segs[k] = (s[0], s[1], s[2], s[3], min(s[4], ylo), max(s[5], yhi))
    return ob


def _cells_along(ax: float, az: float, bx: float, bz: float):
    L = math.hypot(bx - ax, bz - az)
    steps = max(1, int(L / (CELL_M * 0.5)) + 1)
    out = set()
    for s in range(steps + 1):
        t = s / steps
        out.add((int(math.floor((ax + (bx - ax) * t) / CELL_M)), int(math.floor((az + (bz - az) * t) / CELL_M))))
    return out


class WallIndex:
    """Horizontal distance from a point to the built walls, layer-filtered."""

    def __init__(self, segs) -> None:
        self.segs = list(segs)
        self.grid: dict[tuple[int, int], list[int]] = {}
        for k, (ax, az, bx, bz, _, _) in enumerate(self.segs):
            for c in _cells_along(ax, az, bx, bz):
                self.grid.setdefault(c, []).append(k)

    def _layer_ok(self, k: int, y: float) -> bool:
        s = self.segs[k]
        return s[5] > y - LAYER_BELOW_M and s[4] < y + LAYER_ABOVE_M

    def nearest(self, x: float, y: float, z: float, reach_m: float = 24.0) -> tuple[float, int]:
        """(distance, segment index) of the nearest wall footprint in the point's layer; (inf, -1) when
        none lies within ``reach_m``."""
        cx, cz = int(math.floor(x / CELL_M)), int(math.floor(z / CELL_M))
        best, bk = float("inf"), -1
        seen: set[int] = set()
        rmax = int(math.ceil(reach_m / CELL_M))
        for r in range(rmax + 1):
            if r == 0:
                cells = [(cx, cz)]
            else:
                cells = [(gx, gz) for gx in range(cx - r, cx + r + 1)
                         for gz in ((cz - r, cz + r) if abs(gx - cx) < r else range(cz - r, cz + r + 1))]
            for c in cells:
                for k in self.grid.get(c, ()):
                    if k in seen:
                        continue
                    seen.add(k)
                    if not self._layer_ok(k, y):
                        continue
                    ax, az, bx, bz = self.segs[k][:4]
                    vx, vz = bx - ax, bz - az
                    L2 = vx * vx + vz * vz
                    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - ax) * vx + (z - az) * vz) / L2))
                    d = math.hypot(x - ax - t * vx, z - az - t * vz)
                    if d < best:
                        best, bk = d, k
            # every segment not yet seen is at least r cells' worth of distance away
            if bk >= 0 and best <= r * CELL_M:
                break
        return (best if best <= reach_m else float("inf")), (bk if best <= reach_m else -1)

    def ray(self, x: float, y: float, z: float, dx: float, dz: float, reach_m: float) -> float:
        """Distance along the horizontal ray (x, z) + t (dx, dz) (unit) to the first wall footprint in the
        point's layer it crosses; inf when none within ``reach_m``."""
        best = float("inf")
        seen: set[int] = set()
        n = max(1, int(math.ceil(reach_m / (CELL_M * 0.5))))
        for s in range(n + 1):
            t0 = min(reach_m, s * CELL_M * 0.5)
            if t0 > best:
                break
            px, pz = x + dx * t0, z + dz * t0
            cx, cz = int(math.floor(px / CELL_M)), int(math.floor(pz / CELL_M))
            for gx in (cx - 1, cx, cx + 1):
                for gz in (cz - 1, cz, cz + 1):
                    for k in self.grid.get((gx, gz), ()):
                        if k in seen:
                            continue
                        seen.add(k)
                        if not self._layer_ok(k, y):
                            continue
                        ax, az, bx, bz = self.segs[k][:4]
                        ex, ez = bx - ax, bz - az
                        den = dx * ez - dz * ex
                        if abs(den) < 1e-12:
                            continue
                        wx, wz = ax - x, az - z
                        t = (wx * ez - wz * ex) / den
                        u = (wx * dz - wz * dx) / den
                        if 0.0 <= u <= 1.0 and 0.0 <= t < best:
                            best = t
        return best if best <= reach_m else float("inf")


class RoadSurface:
    """The built ``1ROAD`` surface under a point."""

    def __init__(self, ob: BuiltObj) -> None:
        self.ob = ob
        self.grid: dict[tuple[int, int], list[int]] = {}
        xs, zs = ob.x, ob.z
        for k, (a, b, c) in enumerate(ob.road_tris):
            x0, x1 = min(xs[a], xs[b], xs[c]), max(xs[a], xs[b], xs[c])
            z0, z1 = min(zs[a], zs[b], zs[c]), max(zs[a], zs[b], zs[c])
            for gx in range(int(math.floor(x0 / CELL_M)), int(math.floor(x1 / CELL_M)) + 1):
                for gz in range(int(math.floor(z0 / CELL_M)), int(math.floor(z1 / CELL_M)) + 1):
                    self.grid.setdefault((gx, gz), []).append(k)

    def sample(self, x: float, y: float, z: float, band: float = SURFACE_BAND_M):
        """(surface y, (nx, ny, nz) unit, facing up) of the road triangle containing (x, z) whose height there
        is nearest ``y`` (within ``band``); None when no road triangle is under the point."""
        ob = self.ob
        xs, ys, zs = ob.x, ob.y, ob.z
        best = None
        for k in self.grid.get((int(math.floor(x / CELL_M)), int(math.floor(z / CELL_M))), ()):
            a, b, c = ob.road_tris[k]
            ax, az, bx, bz, cx, cz = xs[a], zs[a], xs[b], zs[b], xs[c], zs[c]
            det = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
            if abs(det) < 1e-12:
                continue
            l1 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / det
            l2 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / det
            l3 = 1.0 - l1 - l2
            if l1 < -1e-9 or l2 < -1e-9 or l3 < -1e-9:
                continue
            yy = l1 * ys[a] + l2 * ys[b] + l3 * ys[c]
            if abs(yy - y) > band or (best is not None and abs(yy - y) >= abs(best[0] - y)):
                continue
            ux, uy, uz = bx - ax, ys[b] - ys[a], bz - az
            vx, vy, vz = cx - ax, ys[c] - ys[a], cz - az
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            if ny < 0.0:
                L = -L
            best = (yy, (nx / L, ny / L, nz / L))
        return best
