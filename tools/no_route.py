"""NO-ROUTE — the containment gate for the race layouts (ledger 0049, Kevin 2026-10-11).

Kevin's rule for the race versions: "the entire other lane blocked off from access". Every other gate
checks the lane the car is SUPPOSED to drive; nothing checked that the car cannot LEAVE it. The read-only
design run (2026-10-11) flood-filled the installed race_cw build from its grid and reached 750 k m2
outside the corridor — the three bridge spans where the curb strips were gapped but no rail stands, the
centre chain's two free ends, and all ten island noses. This is that fill, as a gate.

  1. DOMAIN   0.25 m cells within w/2 + 25 m of the centreline. Every domain cell is treated as
              drivable: AC lets a car onto 1GRASS and 1KERB, so a gap in the walls is a door whatever
              lies beyond it. Reaching the domain edge = escaping into the open map.
  2. WALLS    BUILT mode: every 1WALL* triangle of the layout's gate OBJ (road kn5 + common race kn5 +
              that layout's closure kn5), rasterised (edges sampled every 0.1 m + interiors) with its
              height range relative to the local deck (the centreline y at the cell's projection
              + 0.10). A cell is a WALL only when the union of the height ranges standing on it (and on
              its 8 neighbours: one jersey face alone never spans the band) covers [deck + 0.20,
              deck + 0.90]. Deliberately strict: the island beam (0.63-0.93 m) alone must NOT seal, or a
              missing island closure would pass; its posts become isolated dots, not a seal.
              Since ledger 0054 step 2e (MEASUREMENT-BUG FIX) the test runs a second time with each wall
              triangle measured from the deck it stands on (the 1ROAD triangle under it whose height is nearest
              its foot; the centreline's where no deck stands) and a cell seals in either frame: a K-rail on a
              junction pad below the line no longer reads short. local_deck_cells counts what that adds.
              PLANNED mode: the declared polylines +- the barrier half base (0.335 m) — both curb
              strips (trimmed corners included) + this layout's closure + the sealed-mouth lines.
              Walls are dilated by PROBE_R 0.5 m: gaps under 1.0 m close, 1.0-1.9 m gaps still read as
              doors (conservative — a 1.9 m car cannot pass a 1.5 m gap, but the gate says door).
  3. SEED     AC_START_0 (data/dummies_<id>.json); planned mode without dummies: the lane centre at the
              layout's grid vertex. A seed in a wall is an input error (exit 2).
  4. FILL     4-connected span fill.
  5. ALLOWED  the declared corridor: per-segment quads between the lane faces (barrier_bands.json v2
              corridors.<id>.lane_by_vertex; box and whole-street vertices are full width), the trimmed
              inside corners' pockets, dilated by TOL 0.75 m.
  6. VERDICT  FAIL on any reached cell outside ALLOWED. Doors (leak cells touching reached+allowed
              ones) are clustered and reported {v0, v1, side, lateral, cells, gap_m, class, escapes}:
              class = where the door leads (opposite = the other carriageway | island | side_street |
              off_road), escapes = the leaked region reaches the domain edge (the open map).
  7. PROBES   the declaration's forbidden probes (pocket centres, island tops, 10 m into each mouth)
              must stay unreached.
  8. LAP      the lane-centre cell at every vertex and every AC_START_n / AC_PIT_n must be reached,
              otherwise FAIL "corridor blocked at v...".

A version-1 declaration (the 0047 centre chain, today's install) is read with ITS corridor semantics
(race-side curb face .. chain / island face, whole street elsewhere) so the gate can be run on today's
installed build to prove it has teeth.

Limits, stated plainly: 2D with a height band. A low car passing under a beam is excluded by the span
rule, not modelled. It assumes no terrain ramp lifts a car over a 1.2 m wall.

Pure Python (no numpy; the system interpreter has none): 64 m tiles of bytearrays, created only where the
domain is, span fills and big-int masks for the per-tile set algebra.

LAPS (ledger 0054): a layout that names a lap (layouts[].lap) is filled on that lap — its line data/lap.<lap>.json,
its declaration data/barrier_bands.<lap>.json; a probe that carries `xz` (a lap's abandoned branch) stands there.

Run:  python tools/no_route.py <project> --layout <id> [--planned] [--obj track.<id>.obj]
                               [--bands data/barrier_bands.json] [--out no_route.<id>.json]
Writes data/no_route.<id>.json (data/no_route.<id>.planned.json with --planned); exit 1 on any leak, a
reached forbidden probe or a blocked lap; exit 2 on an input error.
"""
from __future__ import annotations

import json
import math
import sys
import time
from array import array
from pathlib import Path

CELL_M = 0.25            # INVENTED (GATES-CHANGELOG 2026-10-11): 4 cells per metre
TILE_SHIFT = 8           # 256 x 256 cells = 64 m tiles (INVENTED)
TILE = 1 << TILE_SHIFT
TILE_N = TILE * TILE
DOMAIN_PAD_M = 25.0      # INVENTED: domain = w/2 + this
PROBE_R_M = 0.5          # INVENTED: wall dilation (gaps < 2 x this close)
TOL_M = 0.75             # INVENTED: the allowed corridor's dilation
WALL_LO_M, WALL_HI_M = 0.20, 0.90   # INVENTED: a wall must span this band above the local deck
DECK_LIFT_M = 0.10       # the road ribbon rides +0.10 over the centreline y (race_furniture.LIFT)
HBIN_M = 0.05            # height-bin size of the span test
DECK_BUCKET_M = 2.0      # the deck index's bucket (a lookup grid, not a judgment)
DECK_REACH_M = WALL_HI_M - WALL_LO_M   # 0.70, derived: a deck nearer the line's deck than the band's own height keeps
#                                       the wall's band (from its deck) overlapping the line's band — the same level
EDGE_SAMPLE_M = 0.10     # wall triangle edges sampled this often
BARRIER_HALF_DEFAULT = 0.335
EDGE_INSET_DEFAULT = 0.82
NOSE_HALF, NOSE_VERTS, ISLAND_MIN_VERTS = 0.25, 3, 6   # tools/author_median_blend.py (measured)
ISLAND_MARGIN_M = 0.6    # a door cell within the island half + this is an island door
NB = int(round((WALL_HI_M - WALL_LO_M) / HBIN_M))      # 14 bins
FULL = (1 << NB) - 1
ONES = b"\x01" * TILE
ZEROS = bytes(TILE)
_OPEN_T = bytes([1 if i == 1 else 0 for i in range(256)])     # kind 1 (free) -> 1
_OUT_T = bytes([1 if i == 0 else 0 for i in range(256)])      # kind 0 (outside the domain) -> 1
_ONES_INT = int.from_bytes(b"\x01" * TILE_N, "little")
_COL0 = int.from_bytes((b"\x01" + bytes(TILE - 1)) * TILE, "little")      # cells with lx == 0
_COL_LAST = int.from_bytes((bytes(TILE - 1) + b"\x01") * TILE, "little")  # cells with lx == TILE-1


def _bins(lo: float, hi: float) -> int:
    """the height bins of [WALL_LO, WALL_HI] that [lo, hi] overlaps (relative to the deck)"""
    if hi < WALL_LO_M or lo > WALL_HI_M:
        return 0
    b0 = max(0, int(math.floor((lo - WALL_LO_M) / HBIN_M)))
    b1 = min(NB - 1, int(math.ceil((hi - WALL_LO_M) / HBIN_M)) - 1)
    if b1 < b0:
        b1 = b0
    m = 0
    for b in range(b0, b1 + 1):
        m |= 1 << b
    return m


# ---------------------------------------------------------------------------------------------
# the declaration -> corridor (lanes, walls to plan, probes) in the centreline's own frame
class Corridor:
    """Everything the fill needs from the project, in the frame of data/centerline.local.json
    (x = E, y = up, z = N; +y lateral = LEFT of the increasing-vertex tangent)."""

    def __init__(self, pts, widths, layout: dict, bands: dict, island_w=None, mirror=False):
        n = len(pts)
        self.closed = n > 2 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
        self.m = n - 1 if self.closed else n
        m = self.m
        self.pts = [tuple(p) for p in pts[:m]]
        self.widths = [float(w) for w in widths[:m]]
        self.layout = layout
        self.lid = str(layout.get("id"))
        self.reverse = str(layout.get("direction", "forward")) == "reverse"
        self.bands = bands
        params = bands.get("params") or {}
        self.bhalf = float(params.get("barrier_half_m", BARRIER_HALF_DEFAULT))
        self.edge_c = float(params.get("edge_centre_from_lip_m", -0.485))
        self.inset = float(params.get("edge_inset_m", EDGE_INSET_DEFAULT))
        self.mirror = mirror
        self.normals = []
        for k in range(m):
            if self.closed:
                a, b = self.pts[(k - 1) % m], self.pts[(k + 1) % m]
            else:                                   # an open line: one-sided at its two ends
                a, b = self.pts[max(0, k - 1)], self.pts[min(m - 1, k + 1)]
            tx, tz = b[0] - a[0], b[2] - a[2]
            L = math.hypot(tx, tz) or 1.0
            self.normals.append((-tz / L, tx / L))
        self.st = [0.0]
        for k in range(1, m + (1 if self.closed else 0)):
            a, b = self.pts[k - 1], self.pts[k % m]
            self.st.append(self.st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
        iw = list(island_w or [])
        self.island_half = auth_island_half(iw[:m] if len(iw) >= m else [0.0] * m)
        self.edge_strip = [int(v) for v in (bands.get("edge_strip_by_vertex") or [1] * n)[:m]]
        self.corners = [{"side": str(c["side"]), "i": int(c["in_vertex"]), "j": int(c["out_vertex"]),
                         "removed": set(int(v) for v in c.get("removed", [])),
                         "xz": (float(c["xz"][0]), float(c["xz"][1]))}
                        for c in (bands.get("edge_corners") or [])]
        self.removed = {"L": set(), "R": set()}
        for c in self.corners:
            self.removed[c["side"]] |= c["removed"]
        self.mouths = [[(float(p[0]), float(p[2])) for p in mo.get("polyline_xyz_m", [])]
                       for mo in (bands.get("closed_mouths") or [])]
        self.mouth_rows = [{"side": str(mo.get("side")), "i": int(mo.get("vertex_from", mo.get("host_vertex", 0))),
                            "j": int(mo.get("vertex_to", mo.get("host_vertex", 0)))}
                           for mo in (bands.get("closed_mouths") or [])]
        cor = (bands.get("corridors") or {}).get(self.lid)
        self.version = int(bands.get("version", 1))
        if cor is not None:
            lane = cor["lane_by_vertex"]
            cy = cor.get("closure_y_by_vertex") or [None] * n
            self.lane = [(float(a), float(b)) for a, b in lane[:m]]
            self.closure_y = [None if v is None else float(v) for v in cy[:m]]
            ry = cor.get("race_wall_y_by_vertex") or [None] * n
            self.race_wall_y = [None if v is None else float(v) for v in ry[:m]]
            self.zone = list((cor.get("zone_by_vertex") or ["whole"] * n)[:m])
            # ledger 0054 Phase 2 (opt-in): the K-rails across the far carriageway at the declared median noses
            self.nose_walls = [w for w in cor.get("nose_walls") or [] if len(w.get("polyline_xyz_m") or []) >= 2]
            nr = cor.get("no_route") or {}
            self.probes = [(int(p["vertex"]), float(p["y"]), str(p.get("why", ""))) for p in nr.get("forbidden_probes", [])]
            # a lap's branch probe stands ON the abandoned line (barrier_bands: "xz"), not at a lateral of its vertex
            self.probe_xz = {q: (float(p["xz"][0]), float(p["xz"][1]))
                             for q, p in enumerate(nr.get("forbidden_probes", [])) if p.get("xz") is not None}
            self.semantics = "v2 corridors." + self.lid
        else:
            self.lane, self.closure_y, self.zone = self._lanes_v1()
            self.race_wall_y = [None] * m
            self.nose_walls = []
            self.probes = []
            self.probe_xz = {}
            self.semantics = "v1 (centre chain / islands, the 0047 install)"

    # the 0047 corridor: race-side curb face .. chain face / island face; whole street elsewhere
    def _lanes_v1(self):
        b = self.bands
        m = self.m
        cw = [float(v) for v in (b.get("centre_w_by_vertex") or [0.0] * (m + 1))[:m]]
        ei = [float(v) for v in (b.get("edge_inset_by_vertex") or [self.inset] * (m + 1))[:m]]
        lane, zone = [], []
        for k in range(m):
            face = self.widths[k] / 2.0 - (ei[k] if self.edge_strip[k] else 0.0)
            if cw[k] > 0:
                div = cw[k] / 2.0
            elif self.island_half[k] > 0:
                div = self.island_half[k]
            else:
                div = None
            if div is None:
                lane.append((-face, face))
                zone.append("whole")
            elif not self.reverse:
                lane.append((-face, -div))
                zone.append("closure")
            else:
                lane.append((div, face))
                zone.append("closure")
        return lane, [None] * m, zone

    # ---- frame helpers -----------------------------------------------------------------------
    def at(self, k: int, y: float):
        k %= self.m
        nx, nz = self.normals[k]
        return self.pts[k][0] + nx * y, self.pts[k][2] + nz * y

    def edge_lat(self, k: int) -> float:
        return self.widths[k % self.m] / 2.0 + self.edge_c

    def r_of(self, y: float) -> float:
        """lateral RIGHT of this layout's own travel from a forward-frame lateral"""
        return y if self.reverse else -y

    def lane_centre(self, k: int):
        lo, hi = self.lane[k % self.m]
        return self.at(k, 0.5 * (lo + hi))

    # ---- planned walls: polylines (x, z) to thicken by the barrier half --------------------------
    def wall_polylines(self):
        m = self.m
        out = []
        for side, sgn in (("L", 1.0), ("R", -1.0)):
            has = [bool(self.edge_strip[k]) and k not in self.removed[side] for k in range(m)]
            for k in range(m):
                k1 = (k + 1) % m
                if not self.closed and k1 == 0:
                    continue
                if has[k] and has[k1]:
                    out.append(("edge_" + side, [self.at(k, sgn * self.edge_lat(k)), self.at(k1, sgn * self.edge_lat(k1))]))
            for c in self.corners:
                if c["side"] != side:
                    continue
                a = self.at(c["i"], sgn * self.edge_lat(c["i"]))
                bp = self.at(c["j"], sgn * self.edge_lat(c["j"]))
                out.append(("edge_" + side, [a, c["xz"], bp]))
        cy = self.closure_y
        for k in range(m):
            k1 = (k + 1) % m
            if cy[k] is not None and cy[k1] is not None and (self.closed or k1 != 0):
                out.append(("closure", [self.at(k, cy[k]), self.at(k1, cy[k1])]))
        # ledger 0055: each declared chicane's race-side wall (corridors.<id>.race_wall_y_by_vertex), the same strip
        yw = self.race_wall_y
        for k in range(m):
            k1 = (k + 1) % m
            if yw[k] is not None and yw[k1] is not None and (self.closed or k1 != 0):
                out.append(("chicane", [self.at(k, yw[k]), self.at(k1, yw[k1])]))
        # ledger 0054 Phase 2: each declared nose K-rail, closure race face -> far curb strip, as declared
        for w in self.nose_walls:
            out.append(("nose", [(float(p[0]), float(p[2])) for p in w["polyline_xyz_m"]]))
        cw = [float(v) for v in (self.bands.get("centre_w_by_vertex") or [])[:m]]
        if len(cw) == m and any(v > 0 for v in cw):          # a v1 declaration's centre chain, on the centreline
            for k in range(m):
                k1 = (k + 1) % m
                if cw[k] > 0 and cw[k1] > 0 and (self.closed or k1 != 0):
                    out.append(("chain", [self.at(k, 0.0), self.at(k1, 0.0)]))
        for poly in self.mouths:
            if len(poly) >= 2:
                out.append(("mouth", poly))
        return out


def auth_island_half(iw):
    """the AUTHORED island half-width per vertex (tools/author_median_blend.py: runs of >= 6 vertices,
    0.25 m nose taper over 3 stations at each end) — the island the car meets, not the data width"""
    n = len(iw)
    half = [0.0] * n
    i = 0
    while i < n:
        if iw[i] <= 0:
            i += 1
            continue
        j = i
        while j < n and iw[j] > 0:
            j += 1
        if j - i >= ISLAND_MIN_VERTS:
            L = j - i
            for si, k in enumerate(range(i, j)):
                h = iw[k] / 2.0
                if si < NOSE_VERTS:
                    h = NOSE_HALF + (h - NOSE_HALF) * si / NOSE_VERTS
                if (L - 1 - si) < NOSE_VERTS:
                    h = NOSE_HALF + (h - NOSE_HALF) * (L - 1 - si) / NOSE_VERTS
                half[k] = h
        i = j
    return half


# ---------------------------------------------------------------------------------------------
# the tiled raster
class Raster:
    def __init__(self, x0: float, z0: float, cell: float = CELL_M):
        self.x0, self.z0, self.cell = x0, z0, cell
        self.kind: dict = {}      # 0 outside the domain, 1 free, 2 wall
        self.allowed: dict = {}
        self.open: dict = {}      # the fill's working copy: 1 = free and not yet reached
        self.hmask: dict = {}     # built walls: per-cell height-bin mask (array 'H')
        self.touched: dict = {}   # cells a wall touches (bytearray)

    def ij(self, x: float, z: float):
        return int((x - self.x0) / self.cell), int((z - self.z0) / self.cell)

    def centre(self, ix: int, iz: int):
        return self.x0 + (ix + 0.5) * self.cell, self.z0 + (iz + 0.5) * self.cell

    @staticmethod
    def key(ix, iz):
        return (ix >> TILE_SHIFT, iz >> TILE_SHIFT), ((iz & (TILE - 1)) << TILE_SHIFT) | (ix & (TILE - 1))

    def get(self, store, ix, iz, default=0):
        tk, c = self.key(ix, iz)
        t = store.get(tk)
        return default if t is None else t[c]

    def span(self, store, iz: int, ix0: int, ix1: int, create=True):
        """set cells ix0..ix1 (inclusive) of row iz to 1 in ``store`` (tiles created on demand)"""
        if ix1 < ix0:
            return
        tz = iz >> TILE_SHIFT
        lz = (iz & (TILE - 1)) << TILE_SHIFT
        for tx in range(ix0 >> TILE_SHIFT, (ix1 >> TILE_SHIFT) + 1):
            base = tx << TILE_SHIFT
            a = max(ix0, base) - base
            b = min(ix1, base + TILE - 1) - base
            t = store.get((tx, tz))
            if t is None:
                if not create:
                    continue
                t = store[(tx, tz)] = bytearray(TILE_N)
            t[lz + a: lz + b + 1] = ONES[: b - a + 1]

    def fill_tri(self, store, a, b, c, create=True):
        """scanline-fill the xz triangle (cell centres inside) into ``store``"""
        pts = sorted((a, b, c), key=lambda p: p[1])
        (xa, za), (xb, zb), (xc, zc) = pts
        cell = self.cell
        iz0 = int(math.ceil((za - self.z0) / cell - 0.5))
        iz1 = int(math.floor((zc - self.z0) / cell - 0.5))
        for iz in range(iz0, iz1 + 1):
            z = self.z0 + (iz + 0.5) * cell
            xl = xa + (xc - xa) * ((z - za) / (zc - za)) if zc != za else xa
            if z < zb:
                xr = xa + (xb - xa) * ((z - za) / (zb - za)) if zb != za else xb
            else:
                xr = xb + (xc - xb) * ((z - zb) / (zc - zb)) if zc != zb else xb
            if xl > xr:
                xl, xr = xr, xl
            ix0 = int(math.ceil((xl - self.x0) / cell - 0.5))
            ix1 = int(math.floor((xr - self.x0) / cell - 0.5))
            self.span(store, iz, ix0, ix1, create)

    def fill_quad(self, store, p0, p1, p2, p3, create=True):
        self.fill_tri(store, p0, p1, p2, create)
        self.fill_tri(store, p0, p2, p3, create)

    def tri_cells(self, a, b, c):
        """global cells a triangle touches: its edges sampled every EDGE_SAMPLE_M + its interior rows"""
        out = set()
        x0, z0, cell = self.x0, self.z0, self.cell
        for (p, q) in ((a, b), (b, c), (c, a)):
            L = math.hypot(q[0] - p[0], q[1] - p[1])
            ns = max(1, int(L / EDGE_SAMPLE_M))
            dx, dz = (q[0] - p[0]) / ns, (q[1] - p[1]) / ns
            for s in range(ns + 1):
                out.add((int((p[0] + dx * s - x0) / cell), int((p[1] + dz * s - z0) / cell)))
        pts = sorted((a, b, c), key=lambda p: p[1])
        (xa, za), (xb, zb), (xc, zc) = pts
        iz0 = int(math.ceil((za - z0) / cell - 0.5))
        iz1 = int(math.floor((zc - z0) / cell - 0.5))
        for iz in range(iz0, iz1 + 1):
            z = z0 + (iz + 0.5) * cell
            xl = xa + (xc - xa) * ((z - za) / (zc - za)) if zc != za else xa
            if z < zb:
                xr = xa + (xb - xa) * ((z - za) / (zb - za)) if zb != za else xb
            else:
                xr = xb + (xc - xb) * ((z - zb) / (zc - zb)) if zc != zb else xb
            if xl > xr:
                xl, xr = xr, xl
            for ix in range(int(math.ceil((xl - x0) / cell - 0.5)), int(math.floor((xr - x0) / cell - 0.5)) + 1):
                out.add((ix, iz))
        return out

    def mark_wall_mask(self, cells, mask):
        for ix, iz in cells:
            tk, c = self.key(ix, iz)
            if tk not in self.kind:
                continue                      # beyond the domain: nothing to block there
            hm = self.hmask.get(tk)
            if hm is None:
                hm = self.hmask[tk] = array("H", bytes(2 * TILE_N))
                self.touched[tk] = bytearray(TILE_N)
            hm[c] |= mask
            self.touched[tk][c] = 1

    def wall_cells_from_masks(self):
        """cells whose own mask is non-zero and whose 3x3 neighbourhood's union spans every bin"""
        out = []
        hmask = self.hmask
        for tk, tb in self.touched.items():
            hm = hmask[tk]
            tx, tz = tk
            pos = tb.find(1)
            while pos >= 0:
                lx, lz = pos & (TILE - 1), pos >> TILE_SHIFT
                acc = 0
                if 0 < lx < TILE - 1 and 0 < lz < TILE - 1:
                    for o in (-TILE - 1, -TILE, -TILE + 1, -1, 0, 1, TILE - 1, TILE, TILE + 1):
                        acc |= hm[pos + o]
                else:
                    gx, gz = (tx << TILE_SHIFT) + lx, (tz << TILE_SHIFT) + lz
                    for dz in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            k2, c2 = self.key(gx + dx, gz + dz)
                            h2 = hmask.get(k2)
                            if h2 is not None:
                                acc |= h2[c2]
                if acc == FULL:
                    out.append(((tx << TILE_SHIFT) + lx, (tz << TILE_SHIFT) + lz))
                pos = tb.find(1, pos + 1)
        return out

    def stamp_walls(self, cells, radius_m=PROBE_R_M):
        """dilate wall cells by radius_m into kind (domain cells only)"""
        r = int(round(radius_m / self.cell))
        disc = [(dx, dz) for dz in range(-r, r + 1) for dx in range(-r, r + 1) if dx * dx + dz * dz <= r * r]
        local = [dz * TILE + dx for dx, dz in disc]
        kind = self.kind
        for ix, iz in cells:
            tk, c = self.key(ix, iz)
            t = kind.get(tk)
            lx, lz = c & (TILE - 1), c >> TILE_SHIFT
            if t is not None and r <= lx < TILE - r and r <= lz < TILE - r:
                for o in local:
                    if t[c + o]:
                        t[c + o] = 2
                continue
            for dx, dz in disc:
                k2, c2 = self.key(ix + dx, iz + dz)
                t2 = kind.get(k2)
                if t2 is not None and t2[c2]:
                    t2[c2] = 2

    # ---- the span fill on an `open` store (1 = may enter) ----------------------------------------
    def span_fill(self, opn: dict, seeds, edge_probe=None):
        """4-connected span fill. ``seeds``: [(ix, iz)]. Clears every reached cell of ``opn``. With
        ``edge_probe`` (a dict of kind tiles) returns whether the fill touched a cell outside the domain
        (kind 0 or no tile). Returns (cells_filled, touched_edge)."""
        stack = []
        for ix, iz in seeds:
            tk, c = self.key(ix, iz)
            if tk in opn:
                stack.append((tk, c))
        filled = 0
        edge = False
        T1 = TILE - 1
        while stack:
            tk, c = stack.pop()
            t = opn.get(tk)
            if t is None or not t[c]:
                continue
            row0 = c & ~T1
            rowend = row0 + TILE
            lft = t.rfind(0, row0, c)
            lft = row0 if lft < 0 else lft + 1
            rgt = t.find(0, c, rowend)
            rgt = rowend if rgt < 0 else rgt
            t[lft:rgt] = ZEROS[: rgt - lft]
            filled += rgt - lft
            tx, tz = tk
            a, b = lft - row0, rgt - row0           # local x range [a, b)
            # x neighbours across the tile border
            if a == 0:
                t2 = opn.get((tx - 1, tz))
                if t2 is not None and t2[row0 + T1]:
                    stack.append(((tx - 1, tz), row0 + T1))
            if b == TILE:
                t2 = opn.get((tx + 1, tz))
                if t2 is not None and t2[row0]:
                    stack.append(((tx + 1, tz), row0))
            if edge_probe is not None and not edge:
                edge = self._touches_outside(edge_probe, tk, row0, a, b)
            for dzr in (-TILE, TILE):
                nr = row0 + dzr
                if 0 <= nr < TILE_N:
                    nk, nt = tk, t
                else:
                    nk = (tx, tz - 1) if dzr < 0 else (tx, tz + 1)
                    nt = opn.get(nk)
                    nr = nr % TILE_N
                    if nt is None:
                        continue
                lo_, hi_ = nr + a, nr + b
                p = nt.find(1, lo_, hi_)
                while p >= 0:
                    stack.append((nk, p))
                    q = nt.find(0, p, hi_)
                    if q < 0:
                        break
                    p = nt.find(1, q, hi_)
        return filled, edge

    def _touches_outside(self, kind, tk, row0, a, b):
        """does the span [a, b) of row row0 in tile tk have an outside-the-domain cell 4-adjacent?"""
        tx, tz = tk
        t = kind.get(tk)
        if t is None:
            return True
        # left / right
        if a > 0:
            if t[row0 + a - 1] == 0:
                return True
        else:
            t2 = kind.get((tx - 1, tz))
            if t2 is None or t2[row0 + TILE - 1] == 0:
                return True
        if b < TILE:
            if t[row0 + b] == 0:
                return True
        else:
            t2 = kind.get((tx + 1, tz))
            if t2 is None or t2[row0] == 0:
                return True
        for dzr in (-TILE, TILE):
            nr = row0 + dzr
            if 0 <= nr < TILE_N:
                if t.find(0, nr + a, nr + b) >= 0:
                    return True
            else:
                t2 = kind.get((tx, tz - 1) if dzr < 0 else (tx, tz + 1))
                if t2 is None or t2.find(0, (nr % TILE_N) + a, (nr % TILE_N) + b) >= 0:
                    return True
        return False


# ---------------------------------------------------------------------------------------------
# the centreline lookup (nearest segment: vertex, along fraction, forward lateral)
class Line:
    def __init__(self, pts, cell=8.0):
        self.pts = pts
        self.m = len(pts)
        self.cell = cell
        self.grid: dict = {}
        for k, p in enumerate(pts):
            self.grid.setdefault((int(p[0] // cell), int(p[2] // cell)), []).append(k)

    def nearest_vertex(self, x, z, reach=8):
        cx, cz = int(x // self.cell), int(z // self.cell)
        best, bk = float("inf"), None
        for r in range(reach + 1):
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if max(abs(dx), abs(dz)) != r:
                        continue
                    for k in self.grid.get((cx + dx, cz + dz), ()):
                        p = self.pts[k]
                        d = (p[0] - x) ** 2 + (p[2] - z) ** 2
                        if d < best:
                            best, bk = d, k
            if bk is not None and math.sqrt(best) < r * self.cell:
                break
        return bk

    def project(self, x, z, reach=8):
        """(vertex k, fraction u toward k+1, forward-left lateral, height of the line there)"""
        k0 = self.nearest_vertex(x, z, reach)
        if k0 is None:
            return None
        best = None
        m = self.m
        for k in (k0 - 1, k0):
            a, b = self.pts[k % m], self.pts[(k + 1) % m]
            dx, dz = b[0] - a[0], b[2] - a[2]
            L2 = dx * dx + dz * dz or 1e-12
            u = max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[2]) * dz) / L2))
            px, pz = a[0] + u * dx, a[2] + u * dz
            d2 = (x - px) ** 2 + (z - pz) ** 2
            if best is None or d2 < best[0]:
                lat = ((x - a[0]) * (-dz) + (z - a[2]) * dx) / math.sqrt(L2)
                best = (d2, k % m, u, lat, a[1] + u * (b[1] - a[1]))
        return best[1], best[2], best[3], best[4]


# ---------------------------------------------------------------------------------------------
def _load_lap_module():
    """scripts/geometry/race_lap.py by file (pure; this tool is itself loaded by file path from barrier_bands)"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_race_lap_nr", Path(__file__).resolve().parents[1] / "scripts"
                                                  / "geometry" / "race_lap.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_LAP = _load_lap_module()
_CHICANE = []


def _race_chicane():
    """scripts/geometry/race_chicane.py by file, once (ledger 0055: the race island)"""
    if not _CHICANE:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_race_chicane_nr", Path(__file__).resolve().parents[1] / "scripts"
                                                      / "geometry" / "race_chicane.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _CHICANE.append(mod)
    return _CHICANE[0]


def _read_obj_walls(path: Path, mirror: float, decks: list | None = None):
    """(verts as flat array 'd' x,y,z, [(name, [(i,j,k)])]) — only 1WALL* faces are kept. With ``decks`` (a list)
    every 1ROAD* triangle is appended to it as well: the decks the walls stand on."""
    xs = array("d")
    groups = []
    cur = None
    with path.open(encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            k = ln[:2]
            if k == "v ":
                p = ln.split()
                xs.append(float(p[1]) * mirror)
                xs.append(float(p[2]))
                xs.append(float(p[3]))
            elif k == "f ":
                if cur is not None:
                    p = ln.split()
                    idx = [int(q.partition("/")[0]) - 1 for q in p[1:]]
                    for t in range(1, len(idx) - 1):
                        cur[1].append((idx[0], idx[t], idx[t + 1]))
            elif k == "o " or k == "g ":
                name = ln[2:].strip()
                up = name.upper()
                cur = (name, []) if up.startswith("1WALL") else None
                if cur is not None:
                    groups.append(cur)
                elif decks is not None and up.startswith("1ROAD"):
                    cur = (name, decks)
    return xs, groups


class _Decks:
    """The 1ROAD surfaces under the walls (ledger 0054 step 2e): a wall triangle's band is measured from the deck
    it stands on — the 1ROAD triangle under its xz centroid whose height is nearest the triangle's foot (its
    lowest vertex); since step 2g only among the sheets within DECK_REACH_M of the line's own deck (run()'s deck_of).
    Only the DECK_BUCKET_M buckets the walls stand in are indexed."""

    def __init__(self, verts, tris, need: set):
        self.v = verts
        self.grid: dict = {}
        b = DECK_BUCKET_M
        for t in tris:
            i0, i1, i2 = t
            xa, xb, xc = verts[3 * i0], verts[3 * i1], verts[3 * i2]
            za, zb, zc = verts[3 * i0 + 2], verts[3 * i1 + 2], verts[3 * i2 + 2]
            bx0, bx1 = int(math.floor(min(xa, xb, xc) / b)), int(math.floor(max(xa, xb, xc) / b))
            bz0, bz1 = int(math.floor(min(za, zb, zc) / b)), int(math.floor(max(za, zb, zc) / b))
            for bx in range(bx0, bx1 + 1):
                for bz in range(bz0, bz1 + 1):
                    if (bx, bz) in need:
                        self.grid.setdefault((bx, bz), []).append(t)

    @staticmethod
    def bucket(x, z):
        return int(math.floor(x / DECK_BUCKET_M)), int(math.floor(z / DECK_BUCKET_M))

    def under(self, x, z, foot, lo=-1e30, hi=1e30):
        """the height of the 1ROAD surface at (x, z) nearest ``foot`` among those within [lo, hi], or None where no
        such deck stands"""
        v = self.v
        best = None
        for (i0, i1, i2) in self.grid.get(self.bucket(x, z), ()):
            xa, ya, za = v[3 * i0], v[3 * i0 + 1], v[3 * i0 + 2]
            xb, yb, zb = v[3 * i1], v[3 * i1 + 1], v[3 * i1 + 2]
            xc, yc, zc = v[3 * i2], v[3 * i2 + 1], v[3 * i2 + 2]
            den = (zb - zc) * (xa - xc) + (xc - xb) * (za - zc)
            if abs(den) < 1e-12:
                continue
            wa = ((zb - zc) * (x - xc) + (xc - xb) * (z - zc)) / den
            wb = ((zc - za) * (x - xc) + (xa - xc) * (z - zc)) / den
            wc = 1.0 - wa - wb
            if wa < -1e-9 or wb < -1e-9 or wc < -1e-9:
                continue
            h = wa * ya + wb * yb + wc * yc
            if not lo <= h <= hi:
                continue
            if best is None or abs(h - foot) < abs(best - foot):
                best = h
        return best


def _load_layout(cfg: dict, lid: str) -> dict:
    for lo in cfg.get("layouts", []) or []:
        if isinstance(lo, dict) and str(lo.get("id")) == lid:
            return lo
    raise SystemExit(f"[no_route] layout {lid!r} is not declared in track.config.json layouts[]")


def run(project_dir, layout_id: str, *, planned: bool = False, obj: str | None = None, bands: dict | None = None,
        bands_path=None, out_name: str | None = None, cell: float = CELL_M, write: bool = True,
        cfg: dict | None = None, verbose: bool = True, line=None) -> dict:
    """``line`` = (pts, widths, island_w) of the layout's lap in memory (tools/barrier_bands.py's planned fill on a lap
    whose file is not written yet); default: the line the layout counts along (scripts/geometry/race_lap.line_for:
    data/centerline.local.json + median_bands.json, or data/lap.<id>.json for a layout that names a lap)."""
    t0 = time.time()
    proj = Path(project_dir)
    data = proj / "data"
    cfg = cfg if cfg is not None else json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    lo = _load_layout(cfg, layout_id)
    mirror = bool(cfg.get("mirror_x", False))
    lap = _LAP.lap_of(lo)
    if bands is None:
        bp = Path(bands_path) if bands_path else data / _LAP.bands_file(lap)
        if not bp.exists():
            raise SystemExit(f"[no_route] {bp} does not exist (tools/barrier_bands.py)")
        bands = json.loads(bp.read_text(encoding="utf-8"))
    if line is not None:
        pts, widths, iw = [tuple(p) for p in line[0]], [float(w) for w in line[1]], list(line[2] or [])
    elif lap is None:
        cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
        pts = [tuple(p) for p in cl["points_xyz_m"]]
        widths = [float(w) for w in cl["widths_m"]]
        mb = data / "median_bands.json"
        iw = json.loads(mb.read_text(encoding="utf-8")).get("island_w_by_vertex", []) if mb.exists() else []
        iw = _race_chicane().race_island_w(iw, cfg)       # ledger 0055: a street-only island is not in a race lane
    else:
        ln = _LAP.line_for(proj, cfg, layout_id)
        pts, widths, iw = ln["pts"], ln["widths"], ln["island_w"]
    corr = Corridor(pts, widths, lo, bands, iw, mirror)
    if len(corr.lane) != corr.m:
        raise SystemExit(f"[no_route] lane_by_vertex ({len(corr.lane)}) vs centreline ({corr.m}) length mismatch")
    say = print if verbose else (lambda *a, **k: None)
    mode = "planned" if planned else "built"
    obj_name = None
    if not planned:
        obj_name = obj or (f"track.{layout_id}.obj" if corr.version >= 2 else "track.race.obj")
        if not (data / obj_name).exists():
            raise SystemExit(f"[no_route] data/{obj_name} does not exist — the BUILT fill runs on the gate OBJ of the kn5 "
                             f"set {layout_id} loads (kn5_to_gate_obj --kn5 <slug>.kn5 --kn5 <slug>_race.kn5 "
                             f"--kn5 <slug>_closure_{layout_id}.kn5 --out data/track.{layout_id}.obj)")
    m = corr.m
    pad = max(corr.widths) / 2.0 + DOMAIN_PAD_M + 10.0
    R = Raster(min(p[0] for p in corr.pts) - pad, min(p[2] for p in corr.pts) - pad, cell)
    # 1. domain
    for k in range(m):
        k1 = (k + 1) % m
        if not corr.closed and k1 == 0:
            continue
        h0, h1 = corr.widths[k] / 2.0 + DOMAIN_PAD_M, corr.widths[k1] / 2.0 + DOMAIN_PAD_M
        R.fill_quad(R.kind, corr.at(k, -h0), corr.at(k1, -h1), corr.at(k1, h1), corr.at(k, h0))
    domain_cells = sum(t.count(1) for t in R.kind.values())
    say(f"[no_route] {layout_id} ({mode}, {corr.semantics}): domain {domain_cells * cell * cell / 1e3:.0f} k m2 in "
        f"{len(R.kind)} tiles of {TILE * cell:.0f} m ({time.time() - t0:.1f} s)")
    # 5. allowed (before the walls: independent of them)
    _allowed(R, corr)
    # 2. walls
    wall_tris = 0
    local_cells: list = []
    local_walls: list = []
    if planned:
        raw = set()
        for _kind, poly in corr.wall_polylines():
            for a, b in zip(poly, poly[1:]):
                raw |= _thick_segment_cells(R, a, b, corr.bhalf)
        cells = list(raw)
    else:
        deck_tris: list = []
        verts, groups = _read_obj_walls(data / obj_name, -1.0 if mirror else 1.0, decks=deck_tris)
        line = Line(corr.pts)
        rel_cache: dict = {}
        y_cache: dict = {}

        def rel(vi):
            r = rel_cache.get(vi)
            if r is None:
                x, y, z = verts[3 * vi], verts[3 * vi + 1], verts[3 * vi + 2]
                pr = line.project(x, z)
                r = rel_cache[vi] = (y - (pr[3] + DECK_LIFT_M)) if pr is not None else -99.0
                y_cache[vi] = (x, z)
            return r
        for name, tris in groups:
            for (i0, i1, i2) in tris:
                r0, r1, r2 = rel(i0), rel(i1), rel(i2)
                mask = _bins(min(r0, r1, r2), max(r0, r1, r2))
                if not mask:
                    continue
                wall_tris += 1
                R.mark_wall_mask(R.tri_cells(y_cache[i0], y_cache[i1], y_cache[i2]), mask)
        cells = R.wall_cells_from_masks()
        R.hmask.clear()
        R.touched.clear()
        # MEASUREMENT-BUG FIX (ledger 0054 step 2e): the same span test again, each wall triangle measured from
        # the deck it stands on (the 1ROAD surface under it) instead of the centreline's. A wall on a junction
        # pad 0.21-0.27 m below the line read 3-7 cm short of the band and left a door (north J3, v694-699 L).
        # A cell is a wall when it seals in EITHER frame: every centreline-frame wall stays, so a build whose
        # walls all stand on the line's own deck is unchanged (local_deck_cells counts what the deck frame adds).
        if deck_tris:
            def foot_xz(t):
                i0, i1, i2 = t
                return ((verts[3 * i0] + verts[3 * i1] + verts[3 * i2]) / 3.0,
                        (verts[3 * i0 + 2] + verts[3 * i1 + 2] + verts[3 * i2 + 2]) / 3.0)
            decks = _Decks(verts, deck_tris, {_Decks.bucket(*foot_xz(t)) for _n, tris in groups for t in tris})

            def deck_of(cx, cz, foot):
                """the deck a wall triangle stands on, as a car on THIS line meets it (step 2g): of the 1ROAD sheets
                under it within DECK_REACH_M of the line's own deck there (the wall's band from that deck still
                overlaps the line's band), the one nearest the triangle's foot. A sheet further off is another road
                (the I-8 under a bridge, an overpass above): its barriers are not this line's walls (0.20.2: the
                median guardrail over the I-8 sealed 104 cells on decks -3.8..+7.2 m off the line's). None: the
                line's deck, as the first pass."""
                pr = line.project(cx, cz)
                if pr is None:
                    return None
                ref = pr[3] + DECK_LIFT_M
                return decks.under(cx, cz, foot, ref - DECK_REACH_M, ref + DECK_REACH_M)
            for _name, tris in groups:
                for t in tris:
                    i0, i1, i2 = t
                    ys = (verts[3 * i0 + 1], verts[3 * i1 + 1], verts[3 * i2 + 1])
                    cx, cz = foot_xz(t)
                    h = deck_of(cx, cz, min(ys))
                    r0, r1, r2 = rel(i0), rel(i1), rel(i2)      # (also fills y_cache)
                    lo, hi = (min(r0, r1, r2), max(r0, r1, r2)) if h is None else (min(ys) - h, max(ys) - h)
                    mask = _bins(lo, hi)
                    if mask:
                        R.mark_wall_mask(R.tri_cells(y_cache[i0], y_cache[i1], y_cache[i2]), mask)
            have = set(cells)
            local_cells = [c for c in R.wall_cells_from_masks() if c not in have]
            cells = cells + local_cells
            R.hmask.clear()
            R.touched.clear()
            if local_cells:
                # step 2g: WHAT the deck frame sealed — every wall object with a triangle in band touching a deck-frame
                # cell (or its 8 neighbours, the span test's own reach): its cells, how far the deck under it stands
                # from the line's deck, its base / top over that deck, and the line vertices it stands beside
                near = {(cx_ + dx, cz_ + dz) for cx_, cz_ in local_cells for dx in (-1, 0, 1) for dz in (-1, 0, 1)}
                own = {c: set() for c in local_cells}
                rows: dict = {}
                for name, tris in groups:
                    for t in tris:
                        i0, i1, i2 = t
                        ys = (verts[3 * i0 + 1], verts[3 * i1 + 1], verts[3 * i2 + 1])
                        cx, cz = foot_xz(t)
                        h = deck_of(cx, cz, min(ys))
                        if h is None:
                            continue
                        if not _bins(min(ys) - h, max(ys) - h):
                            continue
                        hit = [c for c in R.tri_cells(y_cache[i0], y_cache[i1], y_cache[i2]) if c in near]
                        if not hit:
                            continue
                        pr = line.project(cx, cz)
                        cl_deck = (pr[3] + DECK_LIFT_M) if pr is not None else h
                        row = rows.setdefault(name, {"object": name, "cells": set(), "deck_minus_line_m": [9e9, -9e9],
                                                     "base_m": 9e9, "top_m": -9e9, "vertices": [10 ** 9, -1]})
                        for c in hit:
                            for dx in (-1, 0, 1):
                                for dz in (-1, 0, 1):
                                    q = (c[0] + dx, c[1] + dz)
                                    if q in own:
                                        own[q].add(name)
                                        row["cells"].add(q)
                        row["deck_minus_line_m"] = [min(row["deck_minus_line_m"][0], h - cl_deck),
                                                    max(row["deck_minus_line_m"][1], h - cl_deck)]
                        row["base_m"] = min(row["base_m"], min(ys) - h)
                        row["top_m"] = max(row["top_m"], max(ys) - h)
                        if pr is not None:
                            row["vertices"] = [min(row["vertices"][0], pr[0]), max(row["vertices"][1], pr[0])]
                local_walls = sorted(({"object": r["object"], "cells": len(r["cells"]),
                                       "deck_minus_line_m": [round(v, 3) for v in r["deck_minus_line_m"]],
                                       "base_m": round(r["base_m"], 3), "top_m": round(r["top_m"], 3),
                                       "vertices": r["vertices"]} for r in rows.values() if r["cells"]),
                                     key=lambda r: (r["vertices"][0], r["object"]))
    R.stamp_walls(cells)
    say(f"[no_route] walls: {wall_tris if not planned else 'declared polylines'} -> {len(cells)} wall cells, dilated "
        f"{PROBE_R_M} m ({time.time() - t0:.1f} s)")
    # 3. seed
    dpath = data / f"dummies_{layout_id}.json"
    dummies = json.loads(dpath.read_text(encoding="utf-8")) if dpath.exists() else {}
    m_sgn = -1.0 if mirror else 1.0
    if dummies.get("AC_START_0"):
        sx, _sy, sz = dummies["AC_START_0"]
        seed_xz = (sx * m_sgn, sz)
        seed_from = "AC_START_0"
    elif planned:
        gv = int(((lo.get("start") or {}).get("grid_vertex", 0))) % m
        seed_xz = corr.lane_centre(gv)
        seed_from = f"lane centre at the grid vertex v{gv}"
    else:
        raise SystemExit(f"[no_route] data/dummies_{layout_id}.json has no AC_START_0 (tools/layout_dummies.py)")
    six, siz = R.ij(*seed_xz)
    if R.get(R.kind, six, siz) != 1:
        what = "a wall" if R.get(R.kind, six, siz) == 2 else "outside the domain"
        raise SystemExit(f"[no_route] {layout_id}: the seed ({seed_from}) stands in {what} — input error")
    # 4. fill
    for tk, t in R.kind.items():
        R.open[tk] = bytearray(t.translate(_OPEN_T))
    reached_n, _ = R.span_fill(R.open, [(six, siz)])
    say(f"[no_route] reached {reached_n * cell * cell / 1e3:.1f} k m2 from {seed_from} ({time.time() - t0:.1f} s)")
    # 6. verdict
    res = _analyse(R, corr, layout_id)
    # 7. probes
    forbidden = []
    for q, (k, y, why) in enumerate(corr.probes):
        px, pz = corr.probe_xz[q] if q in corr.probe_xz else corr.at(k, y)
        if _reached(R, *R.ij(px, pz)):
            forbidden.append({"vertex": k, "y": round(y, 2), "why": why})
    # 8. lap complete
    blocked_v = []
    for k in (range(m) if corr.closed else range(1, m - 1)):     # an open line's two end vertices sit ON the domain edge
        cx, cz = corr.lane_centre(k)
        if not _reached(R, *R.ij(cx, cz)):
            blocked_v.append(k)
    blocked = _ranges(blocked_v)
    spawns_missed = []
    for name, p in sorted(dummies.items()):
        if not (name.startswith("AC_START_") or name.startswith("AC_PIT_")) or not isinstance(p, list):
            continue
        if not _reached(R, *R.ij(p[0] * m_sgn, p[2])):
            spawns_missed.append(name)
    fails = []
    if res["leak_cells"]:
        fails.append(f"{res['leak_cells'] * cell * cell:.0f} m2 reached outside the {layout_id} corridor through "
                     f"{len(res['doors'])} doors ({', '.join(_door_str(d) for d in res['doors'][:6])}"
                     f"{' ...' if len(res['doors']) > 6 else ''})")
    for f in forbidden:
        fails.append(f"forbidden probe reached: v{f['vertex']} y {f['y']:+.2f} ({f['why']})")
    if blocked:
        fails.append("corridor blocked at " + ", ".join(f"v{a}-v{b}" if a != b else f"v{a}" for a, b in blocked[:12]))
    if spawns_missed:
        fails.append(f"spawn dummies not reached from the seed: {spawns_missed[:8]}")
    out = {
        "layout": layout_id, "mode": mode, "obj": obj_name, "declaration": corr.semantics,
        "bands_version": corr.version,
        "params": {"cell_m": cell, "tile_m": TILE * cell, "domain_pad_m": DOMAIN_PAD_M, "probe_r_m": PROBE_R_M,
                   "tol_m": TOL_M, "wall_span_m": [WALL_LO_M, WALL_HI_M], "deck": "centreline y + 0.10",
                   "barrier_half_m": corr.bhalf},
        "seed": seed_from,
        "domain_m2": round(domain_cells * cell * cell),
        "reached_m2": round(reached_n * cell * cell),
        "allowed_m2": round(res["allowed_cells"] * cell * cell),
        "leak_cells": res["leak_cells"],
        "leak_m2": round(res["leak_cells"] * cell * cell),
        "escaped": res["escaped"],
        "wall_cells": len(cells),
        "wall_tris_in_band": wall_tris,
        **({} if planned else {"local_deck_cells": len(local_cells)}),
        **({"local_deck_walls": local_walls} if local_walls else {}),
        "door_clusters": len(res["doors"]),
        "doors": res["doors"],
        "doors_by_class": res["by_class"],
        "forbidden_probes": len(corr.probes),
        "forbidden_reached": forbidden,
        "lap_vertices": m,
        "blocked": [[a, b] for a, b in blocked],
        "spawns_checked": sum(1 for nme in dummies if nme.startswith(("AC_START_", "AC_PIT_"))),
        "spawns_unreached": spawns_missed,
        "fail": bool(fails),
        "fails": fails,
        "seconds": round(time.time() - t0, 1),
    }
    if write:
        name = out_name or (f"no_route.{layout_id}.planned.json" if planned else f"no_route.{layout_id}.json")
        (data / name).write_text(json.dumps(out, indent=1), encoding="utf-8")
        out["_path"] = str(data / name)
    say(f"[no_route] {layout_id}: {'FAIL' if fails else 'PASS'} — leak {out['leak_m2']} m2, {len(res['doors'])} doors, "
        f"{len(forbidden)}/{len(corr.probes)} probes reached, {len(blocked)} blocked spans, {len(spawns_missed)} spawns "
        f"unreached ({out['seconds']} s)")
    if local_cells:
        say(f"[no_route]   the deck frame sealed {len(local_cells)} cells more:")
        for w in local_walls[:40]:
            say(f"[no_route]     {w['object']}: {w['cells']} cells at v{w['vertices'][0]}-v{w['vertices'][1]}, its deck "
                f"{w['deck_minus_line_m'][0]:+.2f}..{w['deck_minus_line_m'][1]:+.2f} m off the line's, standing "
                f"{w['base_m']:+.2f}..{w['top_m']:+.2f} m over it")
    for d in res["doors"][:40]:
        say(f"[no_route]   door {_door_str(d)}: {d['cells']} cells, lat {d['lat'][0]:+.1f}..{d['lat'][1]:+.1f}, "
            f"gap ~{d['gap_m']:.1f} m, {d['class']}{', escapes to the open map' if d['escapes'] else ''}")
    for f in fails:
        say("[no_route]   FAIL:", f)
    return out


def _door_str(d):
    return f"v{d['v0']}-v{d['v1']} {d['side']}" if d["v0"] != d["v1"] else f"v{d['v0']} {d['side']}"


def _reached(R: Raster, ix, iz) -> bool:
    tk, c = R.key(ix, iz)
    k = R.kind.get(tk)
    o = R.open.get(tk)
    return k is not None and o is not None and k[c] == 1 and o[c] == 0


def _ranges(vs):
    out = []
    for v in vs:
        if out and v == out[-1][1] + 1:
            out[-1][1] = v
        else:
            out.append([v, v])
    return [(a, b) for a, b in out]


def _thick_segment_cells(R: Raster, a, b, half):
    """cells of the segment a-b thickened by ``half`` each side (a planned barrier's footprint)"""
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz)
    if L < 1e-9:
        return R.tri_cells((a[0] - half, a[1]), (a[0] + half, a[1] - half), (a[0], a[1] + half))
    nx, nz = -dz / L * half, dx / L * half
    p0, p1 = (a[0] + nx, a[1] + nz), (b[0] + nx, b[1] + nz)
    p2, p3 = (b[0] - nx, b[1] - nz), (a[0] - nx, a[1] - nz)
    return R.tri_cells(p0, p1, p2) | R.tri_cells(p0, p2, p3) | R.tri_cells(a, b, a)


def _allowed(R: Raster, corr: Corridor):
    """per-segment quads between the lane faces (+- TOL); on a trimmed inside corner the strip side of the
    removed vertices is replaced by the corner's own pocket (centreline .. in-band -> X -> out-band)"""
    m = corr.m
    lane = corr.lane

    def lat_lo(k):
        lo_, hi_ = lane[k]
        if lo_ < 0 and k in corr.removed["R"]:
            return min(0.0, hi_) - TOL_M
        return lo_ - TOL_M

    def lat_hi(k):
        lo_, hi_ = lane[k]
        if hi_ > 0 and k in corr.removed["L"]:
            return max(0.0, lo_) + TOL_M
        return hi_ + TOL_M
    for k in range(m):
        k1 = (k + 1) % m
        if not corr.closed and k1 == 0:
            continue
        R.fill_quad(R.allowed, corr.at(k, lat_lo(k)), corr.at(k1, lat_lo(k1)), corr.at(k1, lat_hi(k1)),
                    corr.at(k, lat_hi(k)), create=True)
    # ledger 0054 Phase 2: in front of a nose K-rail (the open walk from its box edge to its pin P) the far carriageway is
    # open up to the K-rail — allowed at the street's full width on every segment of that walk (the declared lane
    # narrows to the closure's one vertex early, barrier_bands._corridor_record; the lane at P is the closure's)
    for w in getattr(corr, "nose_walls", []):
        p, md, e = int(w["vertex"]) % m, int(w["median"]) % m, int(w["end"]) % m
        step = 1 if (md - p) % m == 1 else -1
        ks = [e]
        while ks[-1] != p:
            ks.append((ks[-1] + step) % m)
        # the vertex whose lane barrier_bands narrows (P's box-side neighbour) and the next one: full width too — inside
        # the box when the median runs up to the box edge (P = the box edge itself, Mission Gorge into J4)
        nb = (p - step) % m
        if nb not in ks:
            ks = [nb] + ks
        ks = [(ks[0] - step) % m] + ks          # and the segment before the narrowed vertex
        for a, b in zip(ks, ks[1:]):
            fa, fb = corr.widths[a] / 2.0 - corr.inset + TOL_M, corr.widths[b] / 2.0 - corr.inset + TOL_M
            R.fill_quad(R.allowed, corr.at(a, -fa), corr.at(b, -fb), corr.at(b, fb), corr.at(a, fa), create=True)
    for c in corr.corners:
        sgn = 1.0 if c["side"] == "L" else -1.0
        # only where this layout's lane reaches the strip on that side (a closure lane stops short of it)
        X = c["xz"]
        A = corr.at(c["i"], sgn * corr.edge_lat(c["i"]))
        B = corr.at(c["j"], sgn * corr.edge_lat(c["j"]))
        ks = []
        k = c["i"]
        while True:
            ks.append(k)
            if k == c["j"]:
                break
            k = (k + 1) % m
        reach_ok = all((lane[k][1] > corr.edge_lat(k) - corr.bhalf - corr.inset - 0.5) if sgn > 0 else
                       (lane[k][0] < -(corr.edge_lat(k) - corr.bhalf - corr.inset - 0.5)) for k in ks)
        if not reach_ok:
            continue
        fan = [(corr.pts[k][0], corr.pts[k][2]) for k in ks]
        R.fill_tri(R.allowed, X, A, fan[0])
        for p, q in zip(fan, fan[1:]):
            R.fill_tri(R.allowed, X, p, q)
        R.fill_tri(R.allowed, X, fan[-1], B)
        grow = TOL_M - corr.bhalf
        for p, q in ((A, X), (X, B)):
            dx, dz = q[0] - p[0], q[1] - p[1]
            L = math.hypot(dx, dz) or 1e-9
            nx, nz = -dz / L * grow, dx / L * grow
            R.fill_quad(R.allowed, (p[0] + nx, p[1] + nz), (q[0] + nx, q[1] + nz), (q[0] - nx, q[1] - nz),
                        (p[0] - nx, p[1] - nz))


def _int(b) -> int:
    return int.from_bytes(b, "little")


def _shift_nbrs(v: int) -> int:
    """cells 4-adjacent (inside the tile) to any set cell of v"""
    return (((v << 8) & ~_COL0) | ((v >> 8) & ~_COL_LAST) | (v << (8 * TILE)) | (v >> (8 * TILE))) & _ONES_INT


def _analyse(R: Raster, corr: Corridor, lid: str) -> dict:
    """leak cells, door clusters (classed), whether each leaked region escapes to the domain edge"""
    leak_store: dict = {}
    allowed_cells = 0
    leak_cells = 0
    door_cells = []
    for tk, kt in R.kind.items():
        free = _int(kt.translate(_OPEN_T))
        opn = _int(R.open[tk])
        reached = free ^ opn
        at = R.allowed.get(tk)
        A = _int(at) if at is not None else 0
        allowed_cells += (A & free).bit_count()
        if not reached:
            continue
        L = reached & (A ^ _ONES_INT)
        if not L:
            continue
        lb = bytearray(L.to_bytes(TILE_N, "little"))
        leak_cells += lb.count(1)
        leak_store[tk] = lb
        RA = reached & A
        door = L & _shift_nbrs(RA)
        tx, tz = tk
        if door:
            db = door.to_bytes(TILE_N, "little")
            p = db.find(1)
            while p >= 0:
                door_cells.append(((tx << TILE_SHIFT) + (p & (TILE - 1)), (tz << TILE_SHIFT) + (p >> TILE_SHIFT)))
                p = db.find(1, p + 1)
        # doors across the tile border (a leak cell on the border whose neighbour in the next tile is reached+allowed)
        for (dx, dz) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nk = (tx + dx, tz + dz)
            if nk not in R.kind:
                continue
            for q in range(TILE):
                lx, lz = ((0 if dx < 0 else TILE - 1), q) if dx else (q, (0 if dz < 0 else TILE - 1))
                c = (lz << TILE_SHIFT) | lx
                if not lb[c]:
                    continue
                gx, gz = (tx << TILE_SHIFT) + lx + dx, (tz << TILE_SHIFT) + lz + dz
                if _reached(R, gx, gz) and R.get(R.allowed, gx, gz):
                    door_cells.append(((tx << TILE_SHIFT) + lx, (tz << TILE_SHIFT) + lz))
    clusters = _cluster(door_cells)
    line = Line(corr.pts)
    doors = []
    for cl in clusters:
        doors.append(_describe(R, corr, line, cl))
    # escape: label the leaked regions behind the doors
    if doors:
        for d in doors:
            d["escapes"] = None
        comp = 0
        for d in sorted(doors, key=lambda d: -d["cells"]):
            if d["escapes"] is not None:
                continue
            ix, iz = d["_cell"]
            tk, c = R.key(ix, iz)
            lb = leak_store.get(tk)
            if lb is None or not lb[c]:
                d["escapes"] = False
                continue
            comp += 1
            _n, edge = R.span_fill(leak_store, [(ix, iz)], edge_probe=R.kind)
            d["escapes"] = edge
            for d2 in doors:
                if d2["escapes"] is None:
                    tk2, c2 = R.key(*d2["_cell"])
                    lb2 = leak_store.get(tk2)
                    if lb2 is not None and not lb2[c2]:
                        d2["escapes"] = edge
    escaped = any(d.get("escapes") for d in doors)
    by_class: dict = {}
    for d in doors:
        d.pop("_cell", None)
        by_class[d["class"]] = by_class.get(d["class"], 0) + 1
    doors.sort(key=lambda d: (d["v0"], d["side"]))
    return {"leak_cells": leak_cells, "allowed_cells": allowed_cells, "doors": doors, "by_class": by_class,
            "escaped": escaped}


DOOR_LINK_CELLS = 8      # door cells within 2 m of each other are one door (bridges the island beam's posts)


def _cluster(cells, link=DOOR_LINK_CELLS):
    """door cells -> spatial clusters (cells within ``link`` cells of each other)"""
    cells = list(set(cells))
    idx = {c: i for i, c in enumerate(cells)}
    parent = list(range(len(cells)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for (x, z), i in idx.items():
        for dz in range(-link, link + 1):
            for dx in range(-link, link + 1):
                j = idx.get((x + dx, z + dz))
                if j is not None and j != i:
                    a, b = find(i), find(j)
                    if a != b:
                        parent[a] = b
    groups: dict = {}
    for c, i in idx.items():
        groups.setdefault(find(i), []).append(c)
    return list(groups.values())


def _describe(R: Raster, corr: Corridor, line: Line, cells) -> dict:
    m = corr.m
    rows = []
    for ix, iz in cells:
        x, z = R.centre(ix, iz)
        pr = line.project(x, z)
        if pr is None:
            continue
        k, u, y, _h = pr
        rows.append((k, y, x, z))
    if not rows:
        ix, iz = cells[0]
        return {"v0": -1, "v1": -1, "side": "?", "lat": [0.0, 0.0], "cells": len(cells), "gap_m": 0.0,
                "class": "escaped", "_cell": cells[0], "escapes": True}
    ks = sorted(r[0] for r in rows)
    # a cluster across the seam of a closed lap
    if corr.closed and ks[-1] - ks[0] > m // 2:
        shifted = sorted((k + m // 2) % m for k in ks)
        v0, v1 = (shifted[0] - m // 2) % m, (shifted[-1] - m // 2) % m
        kmid = (shifted[len(shifted) // 2] - m // 2) % m
    else:
        v0, v1 = ks[0], ks[-1]
        kmid = ks[len(ks) // 2]
    lats = [r[1] for r in rows]
    ymed = sorted(lats)[len(lats) // 2]
    side = "L" if ymed > 0 else "R"
    tx, tz = -corr.normals[kmid][1], corr.normals[kmid][0]
    along = [r[2] * tx + r[3] * tz for r in rows]
    gap = max(along) - min(along) + R.cell + 2 * PROBE_R_M      # the door cells see the gap minus both dilations
    votes: dict = {}
    for k, y, _x, _z in rows:
        votes[_door_class(corr, k, y)] = votes.get(_door_class(corr, k, y), 0) + 1
    cls = max(votes.items(), key=lambda kv: kv[1])[0]
    return {"v0": v0, "v1": v1, "side": side, "lat": [round(min(lats), 2), round(max(lats), 2)],
            "cells": len(cells), "gap_m": round(gap, 1), "class": cls, "_cell": cells[0]}


def _door_class(corr: Corridor, k: int, y: float) -> str:
    w2 = corr.widths[k] / 2.0
    face = w2 - corr.inset
    if abs(y) >= face - 0.3:
        side = "L" if y > 0 else "R"
        for mo in corr.mouth_rows:
            lo_, hi_ = mo["i"], mo["j"]
            if mo["side"] == side and lo_ - 2 <= k <= hi_ + 2:
                return "side_street"
        return "off_road"
    if corr.island_half[k] > 0 and abs(y) <= corr.island_half[k] + ISLAND_MARGIN_M:
        return "island"
    return "opposite"


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    proj = argv[0]
    layouts, planned, obj, bands_path, out_name, cell = [], False, None, None, None, CELL_M
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--layout":
            layouts.append(argv[i + 1]); i += 2
        elif a == "--planned":
            planned = True; i += 1
        elif a == "--obj":
            obj = Path(argv[i + 1]).name; i += 2
        elif a == "--bands":
            bands_path = argv[i + 1]; i += 2
        elif a == "--out":
            out_name = Path(argv[i + 1]).name; i += 2
        elif a == "--cell":
            cell = float(argv[i + 1]); i += 2
        else:
            print(f"[no_route] unknown argument {a!r}")
            return 2
    cfg = json.loads((Path(proj) / "track.config.json").read_text(encoding="utf-8"))
    if not layouts:
        layouts = [str(lo["id"]) for lo in cfg.get("layouts", []) if lo.get("race_furniture")]
    if not layouts:
        print("[no_route] no race layout declared (layouts[].race_furniture) — nothing to contain")
        return 2
    if out_name and len(layouts) > 1:
        print("[no_route] --out names one file: give one --layout")
        return 2
    rc = 0
    for lid in layouts:
        try:
            r = run(proj, lid, planned=planned, obj=obj, bands_path=bands_path, out_name=out_name, cell=cell, cfg=cfg)
        except SystemExit as e:
            print(e)
            return 2
        if r["fail"]:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
