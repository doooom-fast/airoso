"""A ROAD UNDER A ROOF: declared covered spans, and what the gates set aside over them (Denver Grand Prix PLAN 4
item 1; ledger 0096). Stout St runs 344 m under the Colorado Convention Center (OSM tunnel=building_passage,
covered=yes, maxheight=5).

A bridge span is declared so the gates accept what is BELOW a deck: the ground far under it, a railing with air
beneath (track.config.json capture.bridges). A covered span is the same declaration the other way up: it is declared
so the gates accept what is ABOVE the road, and only there.

    track.config.json
    "capture": {
      "covered_spans": [
        {"name": "Stout St under the Colorado Convention Center",
         "center_m": 1712.0, "len_m": 344.0,     # stations along the track's centreline, as capture.bridges
         "clear_m": 5.0,                          # the real clearance over the road (OSM maxheight, a survey)
         "source": "OSM way 12345 tunnel=building_passage maxheight=5"}
      ]
    }

Optional per span: ``min_clear_m`` (default 2.5 [invented]: the height over the road from which geometry is the
roof's and not something a car meets; never under 2.0, so nothing inside drive_test's 1.8 m strike ceiling is ever
set aside) and ``reach_m`` (default 6.0 [invented]: how far beyond the road's own half-width the roof is taken to run).

WHAT A GATE SETS ASIDE. Inside a span's plan footprint (the centreline between its two stations, squared off at both
ends, the road's half-width + reach_m to each side), a triangle whose every vertex is at least min_clear_m above the
road's own height there is OVERHEAD: the roof, its soffit, whatever stands on top of it, a light hung from it. The
gates that look for a surface under a wheel, ground under a deck, a foot under a post or a mast under a lamp head do
not read it. Everything that rises from the road (a wall, a column, a kerb) has a vertex at the road and is read as
before. Outside a declared span nothing changes, and a track that declares none never builds a zone.

WHAT A DECLARATION OWES. With ``clear_m`` written, overhead geometry directly over the road's own width that hangs
lower than clear_m - CLEAR_TOL_M (and above the 1.8 m strike ceiling, below which it is an obstruction already) fails
drive_test: a roof modelled lower than the surveyed clearance is a defect only a covered span can have. A span with no
roof built over it yet is reported, not failed (Denver's Drive 1 declares the span before the building stands).

Pure Python. The frame is the caller's: each gate passes the centreline it already walks (drive_test the gate OBJ's,
kn5_ground_check the kn5's), y up, and asks about points in that same frame.
"""
from __future__ import annotations

import math
from collections import defaultdict

MIN_CLEAR_M = 2.5        # [invented] 2026-11-23: over this height above the road, geometry in a covered span is the roof's
MIN_CLEAR_FLOOR_M = 2.0  # a declared min_clear_m under this is refused (drive_test.OBST_HEIGHT_M is 1.8)
REACH_M = 6.0            # [invented] 2026-11-23: the roof is taken to run this far beyond the road's half-width
CLEAR_TOL_M = 0.5        # [invented] 2026-11-23: a built roof may hang this far under its declared clear_m
STRIKE_CEILING_M = 1.8   # drive_test.OBST_HEIGHT_M, restated: below it an overhang is an obstruction already
_CELL = 8.0


def declared(cfg: dict) -> list[dict]:
    """capture.covered_spans as written, checked; [] when the track declares none"""
    rows = ((cfg.get("capture") or {}).get("covered_spans")) or []
    out = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict) or "center_m" not in r or "len_m" not in r:
            raise SystemExit(f"capture.covered_spans[{i}]: needs center_m and len_m (stations along the centreline)")
        L = float(r["len_m"])
        if L <= 0:
            raise SystemExit(f"capture.covered_spans[{i}]: len_m {L} is not a length")
        mc = float(r.get("min_clear_m", MIN_CLEAR_M))
        if mc < MIN_CLEAR_FLOOR_M:
            raise SystemExit(f"capture.covered_spans[{i}]: min_clear_m {mc} is under {MIN_CLEAR_FLOOR_M} m; a covered span "
                             "never sets aside what a car can strike")
        clear = r.get("clear_m")
        if clear is not None and float(clear) < mc:
            raise SystemExit(f"capture.covered_spans[{i}]: clear_m {clear} is under min_clear_m {mc}")
        out.append({"name": str(r.get("name") or f"covered span {i}"), "center_m": float(r["center_m"]), "len_m": L,
                    "clear_m": None if clear is None else float(clear), "min_clear_m": mc,
                    "reach_m": float(r.get("reach_m", REACH_M))})
    return out


class Zones:
    """the declared spans laid on a centreline: is a point over the covered road, and how high over it"""

    def __init__(self, pts, widths, spans):
        self.spans = spans
        pts = [tuple(float(v) for v in p[:3]) for p in pts]
        n = len(pts)
        closed = n > 3 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6   # L13: derived
        st = [0.0]
        for i in range(1, n):
            st.append(st[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
        lap = st[-1]
        w = [float(v) for v in widths]
        if closed and len(w) == n:
            w[-1] = w[0]                         # the closure duplicate carries vertex 0's width (median_zone's rule)
        self.lap, self.closed = lap, closed
        self.segs = []                           # (ax, ay, az, bx, by, bz, half_a, half_b, span index)
        self.grid = defaultdict(list)
        self.max_reach = 0.0
        for k, sp in enumerate(spans):
            a, b = sp["center_m"] - sp["len_m"] / 2.0, sp["center_m"] + sp["len_m"] / 2.0
            pieces = [(max(a, 0.0), min(b, lap))]
            if closed:                           # L13: a span across the seam wraps, in stations as well as indices
                if a < 0.0:
                    pieces.append((a + lap, lap))
                if b > lap:
                    pieces.append((0.0, b - lap))
            for s0, s1 in pieces:
                if s1 <= s0:
                    continue
                for i in range(n - 1):
                    lo, hi = max(s0, st[i]), min(s1, st[i + 1])
                    if hi - lo <= 1e-9:
                        continue
                    seg = st[i + 1] - st[i]
                    row = []
                    for s in (lo, hi):
                        t = (s - st[i]) / seg
                        row.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t,
                                    pts[i][2] + (pts[i + 1][2] - pts[i][2]) * t, (w[i] + (w[i + 1] - w[i]) * t) / 2.0))
                    j = len(self.segs)
                    self.segs.append((*row[0][:3], *row[1][:3], row[0][3], row[1][3], k))
                    reach = max(row[0][3], row[1][3]) + sp["reach_m"]
                    self.max_reach = max(self.max_reach, reach)
                    for ci in range(int((min(row[0][0], row[1][0]) - reach) // _CELL),
                                    int((max(row[0][0], row[1][0]) + reach) // _CELL) + 1):
                        for cj in range(int((min(row[0][2], row[1][2]) - reach) // _CELL),
                                        int((max(row[0][2], row[1][2]) + reach) // _CELL) + 1):
                            self.grid[(ci, cj)].append(j)
        self.set_aside = [0] * len(spans)        # triangles / points read as overhead, per span
        self.lowest = [None] * len(spans)        # lowest overhead height over the road's own width, per span
        self.low = [0] * len(spans)              # overhead triangles under the declared clearance, per span

    def __bool__(self):
        return bool(self.segs)

    def under(self, x: float, z: float):
        """(road height, lateral distance, half-width, span index) where (x, z) lies in a span's footprint, else None.
        Square ends: a point beyond a span's end, however near its last metre, is outside it."""
        best = None
        for j in self.grid.get((int(x // _CELL), int(z // _CELL)), ()):
            ax, ay, az, bx, by, bz, ha, hb, k = self.segs[j]
            dx, dz = bx - ax, bz - az
            L2 = dx * dx + dz * dz
            if L2 <= 1e-18:
                continue
            t = ((x - ax) * dx + (z - az) * dz) / L2
            if t < -1e-9 or t > 1.0 + 1e-9:
                continue
            d = math.hypot(x - (ax + dx * t), z - (az + dz * t))
            half = ha + (hb - ha) * t
            if d <= half + self.spans[k]["reach_m"] and (best is None or d < best[1]):
                best = (ay + (by - ay) * t, d, half, k)
        return best

    def point_overhead(self, x: float, y: float, z: float, count: bool = True) -> bool:
        u = self.under(x, z)
        if u is None or y - u[0] < self.spans[u[3]]["min_clear_m"]:
            return False
        if count:
            self.set_aside[u[3]] += 1
        return True

    def tri_overhead(self, a, b, c) -> bool:
        """a triangle of the roof: it reaches a span's footprint, and its lowest vertex is min_clear_m or more above
        the road everywhere it does. Also keeps, per span, the lowest such height over the road's own width."""
        ymin = min(a[1], b[1], c[1])
        cen = ((a[0] + b[0] + c[0]) / 3.0, 0.0, (a[2] + b[2] + c[2]) / 3.0)
        hits = [u for u in (self.under(p[0], p[2]) for p in (a, b, c, cen)) if u is not None]
        if not hits:
            return False
        over_road = [(ymin - deck, k) for deck, d, half, k in hits if d <= half and ymin - deck >= STRIKE_CEILING_M]
        if over_road:                            # it hangs over the road's own width, clear of the strike ceiling
            h, k = min(over_road)
            if self.lowest[k] is None or h < self.lowest[k]:
                self.lowest[k] = h
            clear = self.spans[k]["clear_m"]
            if clear is not None and h < clear - CLEAR_TOL_M:
                self.low[k] += 1
        if any(ymin - deck < self.spans[k]["min_clear_m"] for deck, _d, _h, k in hits):
            return False
        self.set_aside[hits[0][3]] += 1
        return True

    def report(self) -> list[dict]:
        return [{"name": sp["name"], "from_m": round(sp["center_m"] - sp["len_m"] / 2.0, 1),
                 "to_m": round(sp["center_m"] + sp["len_m"] / 2.0, 1), "clear_m": sp["clear_m"],
                 "min_clear_m": sp["min_clear_m"], "reach_m": sp["reach_m"], "overhead_set_aside": self.set_aside[k],
                 "lowest_overhead_m": None if self.lowest[k] is None else round(self.lowest[k], 2),
                 "under_declared_clearance": self.low[k]} for k, sp in enumerate(self.spans)]


def zones_for(cfg: dict, pts, widths):
    """the track's covered zones on this centreline, or None when it declares no covered span"""
    spans = declared(cfg)
    if not spans:
        return None
    z = Zones(pts, widths, spans)
    return z if z else None
