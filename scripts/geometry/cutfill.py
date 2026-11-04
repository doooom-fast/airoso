"""The road-building cross-section as a ground function: cut and fill by station, stacked legs seated to their own leg.

Lookout Lariat V3-PLAN P3a ("new terrain_cutfill"), ledger 0048. OPT-IN: ``track.config.json`` ``terrain.cross_section``
with ``"build": true``; every track without it never imports this module and builds byte-identically.

THE SECTION (docs/ROAD-CONSTRUCTION.md, the Lariat's cross_section block), uphill to downhill, at each station of the line
the road is swept over (data/finished_centerline.json, the build's own ``centerline``):

- the pavement, then the verge (``road_profile.verge_m``: D4 A 0.4 m, B 1.25 m) carrying the road edge's height;
- CUT, where the natural ground stands above that edge: a bench at the edge's height (``cut_bench_m``, the toe ditch's
  footprint), then a face rising at ``cut`` H:V (0.25:1, rock) until it meets the natural ground, which then stands;
- FILL, where the natural ground lies below: the hinge held at the edge's height (``fill_bench_m``), then a face falling
  at ``fill`` H:V (1.5:1, hand-placed rock) until it meets the natural ground.

The two benches are what a regular terrain grid needs to represent the edge (a cell can only follow a cut it is smaller
than, L3b) and what audit H's sample 2 m off the pavement accepts; the Lariat's values and why are in its config.

Not modelled in the draft (said, not hidden): the 0.4 x 1.2 m toe ditch and the fill -> wall trigger (both edge work,
P3d); the soil-cut slope (1-1.5:1), since nothing in the data says where the cut is soil rather than rock.

STATION MATCHING (L4). A ground point belongs to the lap point nearest it in plan (its OWN leg), and only that leg's
section shapes it. For the stacked hold below, ownership is read exactly as the stacked-leg gate reads it
(tools/verify_stacked_legs.py: the line cm-rounded and resampled at 1 m; ``_Owners``), so a point near the medial line
is held to the side the gate will judge it by. Where another leg (more than
``pair_along_m`` along the lap) lies within ``pair_plan_m`` of the point and of its own lap point, the two legs are
STACKED: the point is held on its own leg's side of the height between the two roads (an upper leg's ground no lower
than the midpoint, a lower leg's no higher), which is what "seated to its own leg" means between legs 6.5-15 m apart in
height (V3-PLAN P3a: "rock cut above and rock fill below, the way the 1913 crews built it"). The hold moves ground only
between stacked legs, inside the road's own construction zone (L3: near-road relief is shaped within ~20-40 m).

Pure stdlib (no numpy): the engine's stdlib-only test rule.
"""
from __future__ import annotations

import math
from collections import defaultdict

CELL_M = 10.0


def parse_ratio(v, default: float) -> float:
    """'0.25:1' -> 0.25 (H per V); a number is taken as is; anything else -> default."""
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and ":" in v:
        try:
            h, vv = v.split(":", 1)
            return float(h) / float(vv)
        except ValueError:
            return default
    return default


def section_enabled(cfg: dict) -> bool:
    """``terrain.cross_section.build: true`` (explicit) turns the section on."""
    return bool((((cfg.get("terrain") or {}).get("cross_section") or {}).get("build")) is True)


class _Owners:
    """The lap as the stacked-leg gate reads it (tools/verify_stacked_legs.py over tools/gate_route.resample): the
    line rounded to the centimetre (data/finished_centerline.json's precision), resampled every 1 m from v0 with the
    last point kept, the closing duplicate dropped; a point is "stacked" when another point more than ``pair_along``
    along the lap lies within ``pair_plan`` in plan."""

    def __init__(self, line, pair_plan: float, pair_along: float):
        pts = [(round(p[0], 2), round(p[1], 2), round(p[2], 2)) for p in line]
        st = [0.0]
        for i in range(1, len(pts)):
            st.append(st[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
        lap = st[-1]
        q, qs = [], []
        i, s = 1, 0.0
        while s < lap - 1e-9:
            while i < len(pts) - 1 and st[i] < s:
                i += 1
            t = min(1.0, max(0.0, (s - st[i - 1]) / max(st[i] - st[i - 1], 1e-12)))
            a, b = pts[i - 1], pts[i]
            q.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t))
            qs.append(s)
            s += 1.0
        q.append(pts[-1])
        qs.append(lap)
        self.closed = len(pts) > 2 and math.hypot(pts[0][0] - pts[-1][0], pts[0][2] - pts[-1][2]) < 1e-6
        if self.closed:
            q, qs = q[:-1], qs[:-1]
        self.q, self.s, self.lap = q, qs, lap
        self.pair_plan, self.pair_along = pair_plan, pair_along
        self.cells = defaultdict(list)
        for k, (x, _y, z) in enumerate(q):
            self.cells[(int(math.floor(x / CELL_M)), int(math.floor(z / CELL_M)))].append(k)
        self.stacked = [False] * len(q)
        for k, (x, _y, z) in enumerate(q):
            for j in self._near(x, z, pair_plan):
                if j > k and self.along(k, j) > pair_along and \
                        math.hypot(q[j][0] - x, q[j][2] - z) < pair_plan:
                    self.stacked[k] = self.stacked[j] = True

    def along(self, i: int, j: int) -> float:
        d = abs(self.s[i] - self.s[j])
        return min(d, self.lap - d) if self.closed else d

    def _near(self, x: float, z: float, r: float):
        R = int(math.ceil(r / CELL_M))
        ci, cj = int(math.floor(x / CELL_M)), int(math.floor(z / CELL_M))
        for di in range(-R, R + 1):
            for dj in range(-R, R + 1):
                yield from self.cells.get((ci + di, cj + dj), ())

    def nearest(self, x: float, z: float, r: float):
        best = None
        for k in self._near(x, z, r):
            d2 = (self.q[k][0] - x) ** 2 + (self.q[k][2] - z) ** 2
            if d2 < r * r and (best is None or d2 < best[0]):
                best = (d2, k)
        return (best[1], math.sqrt(best[0])) if best else None

    def partner(self, x: float, z: float, k: int):
        """The gate's other leg: the nearest point > pair_along along from k, within pair_plan of the point and of k."""
        best = None
        for j in self._near(x, z, self.pair_plan):
            if self.along(j, k) <= self.pair_along:
                continue
            d2 = (self.q[j][0] - x) ** 2 + (self.q[j][2] - z) ** 2
            if d2 >= self.pair_plan ** 2 or (best is not None and d2 >= best[0]):
                continue
            best = (d2, j)
        if best is None:
            return None
        j = best[1]
        if math.hypot(self.q[j][0] - self.q[k][0], self.q[j][2] - self.q[k][2]) >= self.pair_plan:
            return None
        return j


class CrossSection:
    """``height(x, z, natural)`` -> the constructed ground height there, or ``natural`` where the section leaves it.

    ``line``: [(x, y, z)] the swept centreline (closed when first == last); ``widths``: pavement width per point;
    ``bank_at(station) -> radians`` (the crossfall) or None; ``clearance``: the ground sits this far under the edge."""

    def __init__(self, line, widths, *, verge_m: float, fill_bench_m: float = 0.0, cut_bench_m: float = 0.0,
                 cut_hv: float = 0.25, fill_hv: float = 1.5,
                 clearance: float = 0.01, bank_at=None, bridge_of=None, reach_m: float = 60.0,
                 pair_plan_m: float = 40.0, pair_along_m: float = 150.0, stack_min_dy: float = 2.0,
                 stack_margin: float = 0.3):
        pts = [tuple(p) for p in line]
        self.closed = len(pts) > 2 and math.hypot(pts[0][0] - pts[-1][0], pts[0][2] - pts[-1][2]) < 1e-6
        if self.closed:                                 # L13: the closing duplicate of v0 is v0
            pts = pts[:-1]
            widths = list(widths[:len(pts)])
        self.p = pts
        self.w = [float(w) for w in widths]
        n = len(pts)
        st = [0.0]
        for i in range(1, n):
            st.append(st[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
        self.s = st
        self.lap = st[-1] + (math.hypot(pts[0][0] - pts[-1][0], pts[0][2] - pts[-1][2]) if self.closed else 0.0)
        self.verge = float(verge_m)
        self.fill_bench = max(0.0, float(fill_bench_m))
        self.cut_bench = max(0.0, float(cut_bench_m))
        self.cut_slope = 1.0 / max(1e-3, float(cut_hv))     # metres up per metre out
        self.fill_slope = 1.0 / max(1e-3, float(fill_hv))
        self.clear = float(clearance)
        self.bank_at = bank_at
        self.bridge_of = bridge_of
        self.reach = float(reach_m)
        self.pair_plan = float(pair_plan_m)
        self.pair_along = float(pair_along_m)
        self.stack_min_dy = float(stack_min_dy)
        self.margin = float(stack_margin)
        self.cells = defaultdict(list)
        for i, (x, _y, z) in enumerate(pts):
            self.cells[(int(math.floor(x / CELL_M)), int(math.floor(z / CELL_M)))].append(i)
        self.stats = {"graded": 0, "cut": 0, "fill": 0, "held_up": 0, "held_down": 0}
        self.owners = _Owners(line, self.pair_plan, self.pair_along)
        # which lap points have a stacked partner at all (the gate's pair rule), and how close the nearest OTHER
        # stretch of the lap comes to each point (anything more than 10 m along): both bound the per-point searches
        self.stacked = [False] * n
        self.other_d = [math.inf] * n
        for i in range(n):
            x, _y, z = pts[i]
            for j in self._near(x, z, max(self.pair_plan, self.reach)):
                d = math.hypot(pts[j][0] - x, pts[j][2] - z)
                a = self.along(i, j)
                if a > 10.0 and d < self.other_d[i] and a > 2.0 * d:
                    self.other_d[i] = d
                if a > self.pair_along and d < self.pair_plan:
                    self.stacked[i] = True

    # ---- the line ------------------------------------------------------------------------------------------------
    def along(self, i: int, j: int) -> float:
        d = abs(self.s[i] - self.s[j])
        return min(d, self.lap - d) if self.closed else d

    def _near(self, x: float, z: float, r: float):
        R = int(math.ceil(r / CELL_M))
        ci, cj = int(math.floor(x / CELL_M)), int(math.floor(z / CELL_M))
        for di in range(-R, R + 1):
            for dj in range(-R, R + 1):
                for k in self.cells.get((ci + di, cj + dj), ()):
                    yield k

    def nearest(self, x: float, z: float, r: float):
        """(index, distance) of the lap point nearest (x, z) in plan within r, or None. Searches outward ring by ring
        of cells and stops once the best found is closer than the next ring can be."""
        ci, cj = int(math.floor(x / CELL_M)), int(math.floor(z / CELL_M))
        Rmax = int(math.ceil(r / CELL_M))
        best = None
        for R in range(0, Rmax + 1):
            if best is not None and best[0] <= ((R - 1) * CELL_M) ** 2:
                break
            for di in range(-R, R + 1):
                for dj in ((-R, R) if abs(di) != R else range(-R, R + 1)):
                    for k in self.cells.get((ci + di, cj + dj), ()):
                        d2 = (self.p[k][0] - x) ** 2 + (self.p[k][2] - z) ** 2
                        if best is None or d2 < best[0]:
                            best = (d2, k)
        return (best[1], math.sqrt(best[0])) if best and best[0] <= r * r else None

    def _foot(self, x: float, z: float, k: int):
        """(lateral distance to the line, signed side +1 left / -1 right, height of the centre there) on the segment
        pair around vertex k: the foot of the perpendicular, so the edge is where the swept ribbon puts it."""
        n = len(self.p)
        best = None
        for a, b in ((k - 1, k), (k, k + 1)):
            if not self.closed and (a < 0 or b >= n):
                continue
            pa, pb = self.p[a % n], self.p[b % n]
            ex, ez = pb[0] - pa[0], pb[2] - pa[2]
            L2 = ex * ex + ez * ez
            if L2 < 1e-12:
                continue
            t = max(0.0, min(1.0, ((x - pa[0]) * ex + (z - pa[2]) * ez) / L2))
            fx, fz = pa[0] + ex * t, pa[2] + ez * t
            d = math.hypot(x - fx, z - fz)
            if best is None or d < best[0]:
                cross = ex * (z - pa[2]) - ez * (x - pa[0])
                best = (d, 1.0 if cross > 0 else -1.0, pa[1] + (pb[1] - pa[1]) * t,
                        self.w[a % n] + (self.w[b % n] - self.w[a % n]) * t, a % n, t)
        return best

    # ---- the ground ----------------------------------------------------------------------------------------------
    def height(self, x: float, z: float, natural: float, *, count: bool = False) -> float:
        hit = self.nearest(x, z, self.reach)
        if hit is None:
            return natural
        k, _d = hit
        foot = self._foot(x, z, k)
        if foot is None:
            return natural
        d, side, yc, w, a, t = foot
        half = w / 2.0
        station = self.s[a] + t * ((self.s[(a + 1) % len(self.p)] if (a + 1) < len(self.p) else self.lap) - self.s[a])
        tb = math.tan(self.bank_at(station)) if self.bank_at else 0.0
        # bank_at's sign: +ve = the left edge up (ribbon._road_surface_samples); left is side +1 here
        edge = yc + side * half * tb - self.clear
        o = d - half - self.verge
        g = natural
        if o <= 0.0:
            g = edge if d >= half else natural          # the verge carries the edge; under the deck: the pins' job
        elif natural > edge:                            # CUT: the bench (the toe ditch's footprint), then the face
            g = edge if o <= self.cut_bench else min(natural, edge + (o - self.cut_bench) * self.cut_slope)
            if count and g < natural:
                self.stats["cut"] += 1
        else:                                           # FILL: the hinge held at grade, then the face
            on_bridge = self.bridge_of is not None and self.bridge_of(station)
            if not on_bridge:
                g = edge if o <= self.fill_bench else max(natural, edge - (o - self.fill_bench) * self.fill_slope)
                if count and g > natural:
                    self.stats["fill"] += 1
        return self.hold(x, z, g, count=count)

    def hold(self, x: float, z: float, g: float, k=None, *, count: bool = False) -> float:
        """Between stacked legs, keep ``g`` on its own leg's side of the midpoint height (by ``margin``). Ownership is
        read the way the stacked-leg gate reads it (``_Owners``: the line resampled at 1 m, nearest in plan; the other
        leg = the nearest point > pair_along along the lap), so a point near the medial line is held to the side the
        gate will judge it by. ``k`` (a vertex of the swept line) is accepted for the callers' convenience and unused."""
        o = self.owners
        hit = o.nearest(x, z, self.pair_plan)
        if hit is None or not o.stacked[hit[0]]:
            return g
        ko = hit[0]
        j = o.partner(x, z, ko)
        if j is None:
            return g
        yo, yt = o.q[ko][1], o.q[j][1]
        if abs(yo - yt) < self.stack_min_dy:
            return g
        mid = 0.5 * (yo + yt)
        if yo > yt and g < mid + self.margin:
            if count:
                self.stats["held_up"] += 1
            return mid + self.margin
        if yo < yt and g > mid - self.margin:
            if count:
                self.stats["held_down"] += 1
            return mid - self.margin
        return g

    def hold_at(self, x: float, z: float, g: float) -> float:
        """``hold`` for a point whose own leg is not known yet (a pinned node, a sheet vertex)."""
        return self.hold(x, z, g)

    def grade_grid(self, grid_xyz) -> dict:
        """Grade every node of the regular grid (rows of (x, y, z), y = natural) in place; returns the counts."""
        for row in grid_xyz:
            for k in range(len(row)):
                gx, gy, gz = row[k]
                ny = self.height(gx, gz, gy, count=True)
                if ny != gy:
                    row[k] = (gx, ny, gz)
                    self.stats["graded"] += 1
        return dict(self.stats)

    def hold_grid(self, grid_xyz) -> int:
        """The stacked-leg hold alone, re-applied after passes that move nodes (pins, clamps, bends)."""
        moved = 0
        for row in grid_xyz:
            for k in range(len(row)):
                gx, gy, gz = row[k]
                ny = self.hold(gx, gz, gy)
                if ny != gy:
                    row[k] = (gx, ny, gz)
                    moved += 1
        return moved

    def lateral_cap(self, i: int, side: float, nx: float, nz: float, *, step: float = 0.5, max_m: float = 60.0):
        """How far out from line point ``i`` along the outward normal (nx, nz) the point stays nearest to its own leg:
        the medial line toward any other stretch of the lap (another stacked leg, or the far arm of a hairpin). The
        road_shoulder face is capped here so it never drapes across another leg."""
        if self.closed:
            i = i % len(self.p)
        if self.other_d[i] > 2.0 * max_m + 2.0 * step:
            return max_m                                # nothing else of the lap within reach of this point
        x0, z0 = self.p[i][0], self.p[i][2]
        o = step
        while o <= max_m:
            x, z = x0 + nx * o, z0 + nz * o
            hit = self.nearest(x, z, o + step)
            if hit is not None and self.along(hit[0], i) > max(10.0, 2.0 * o):
                return max(0.0, o - step)
            o += step
        return max_m
