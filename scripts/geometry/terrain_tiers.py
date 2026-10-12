"""Tiered terrain: ONE multi-resolution lattice mesh, fine at the verge and coarse far out, with a
visual-only far ring, every vertex sampled from the DEM AT that vertex (no bilinear upsample).

Ledger 0046 (E1 tiered sampling + far ring, E3 tiling by tier, E2's distance-weighted band clamp).
OPT-IN per track: a track whose ``track.config.json`` ``terrain`` block carries no ``tiers`` list never
reaches this module, and every engine path it does not call is byte-identical (Colorado circuits,
flat circuits, rally stages and Lookout Lariat keep their exact output until they opt in).

Pure stdlib, no package-relative imports: the sampler CLI (``scripts.elevation.terrain_sample``)
imports it as a module and a Blender assembler loads it BY FILE PATH (Blender's ``scripts`` package
is the track's own, so this file must stand alone).

THE LATTICE. Every tier's cell is an integer multiple of the next finer one (``levels`` coarse ->
fine, e.g. 40 / 20 / 5 m: ratios 2, 4). A vertex is an integer pair (I, J) on the BASE lattice
(finest cell / 2 — cell centres are vertices too) placed by the FRAME: x = x0 + I * ux, z = z0 + J * uz
in the local frame (x = E, y = up, z = N, metres). The default frame is anchored at the local origin
(ux = uz = base); ``tier_options.frame = {"kind": "heightfield", "upsample": f}`` anchors it on the track's
own heightfield grid (data/heightfield.meta.json, upsampled f times — the grid an assembler grades), so
that grid's cells ARE lattice cells (its x / z spacing, ~20.07 x 19.98 m at Lake Murray, is the nominal
cell they stand for).

WHICH CELL IS WHICH. Each tier ``{"within_m": W, "cell_m": c}`` refines every cell within W of a road's
PAVEMENT (centreline distance minus half-width) down to c (marked on c's parent cells); the last tier
(no ``within_m``) is the coarse ground; ``"x_split": true`` splits that tier's cells in four around
their centre (longest edge = the cell side). A ``corridor`` (an OSM centreline, e.g. I-8) refines within
its ``half_width_m`` to its ``cell_m``; an ``include`` box refines to its ``cell_m`` (Cowles' cone).
Neighbouring cells differ by at most one level (balanced), so a coarse cell beside a finer one gets the
finer one's edge nodes as hanging nodes and is fanned from its own centre vertex — no crack.

KEPT CELLS (``tier_options.keep_cells = {"cell_m": c, "within_m": W}``): every cell of that size within
W of a pavement stays a leaf with the grid's OWN two triangles (the NW->SE diagonal of ribbon.grass_terrain),
so the passes that later reshape the ground under and beside the roads (the seat, the kn5 prep's
subdivide / pin / feather) meet exactly the topology they always met and give exactly the ground they
always gave. A finer neighbour leaves its edge nodes ON a kept cell's edge (a T-junction, collinear on the
kept surface); the kn5 prep welds them after those passes (``build_kn5_loop._weld_t_junctions``).

PHYSICAL vs FAR. Cells within ``physical_within_m`` of a pavement (and any pocket of other cells
enclosed by them) are physical ground (``1GRASS``); everything else is the FAR RING: visual-only,
named without a digit prefix, never scanned by the gates, never listed for GrassFX or occlusion.
"""
from __future__ import annotations

import json
import math
from collections import deque
from pathlib import Path

# --- small numeric helpers (shared with the assembler's height pass) ------------------------------


def smoothstep(t: float) -> float:
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return t * t * (3.0 - 2.0 * t)


def clamp_weight(d: float, full_m: float, release_m: float) -> float:
    """Distance-weighted band clamp (fleet/LAWS.md L3 as amended 2026-10-11: near-road relief is
    clamped, far relief is data). 1 within ``full_m`` of a pavement, smoothstep down to 0 at
    ``release_m``; beyond that the DEM stands uncapped."""
    if d <= full_m:
        return 1.0
    if d >= release_m or release_m <= full_m:
        return 0.0
    return 1.0 - smoothstep((d - full_m) / (release_m - full_m))


def band_clamp_value(y: float, road_y: float, band: float, w: float) -> float:
    """``y`` pulled toward ``road_y ± band`` by weight ``w`` (w = 1: the old hard clamp)."""
    c = road_y - band if y < road_y - band else (road_y + band if y > road_y + band else y)
    return y + w * (c - y)


def keep_weight(d: float, keep_m: float, feather_m: float) -> float:
    """Weight of a kept (already graded) surface: 1 within ``keep_m`` of a pavement, smoothstep to 0
    at ``keep_m + feather_m``."""
    if d <= keep_m:
        return 1.0
    if feather_m <= 0.0 or d >= keep_m + feather_m:
        return 0.0
    return 1.0 - smoothstep((d - keep_m) / feather_m)


def meters_per_degree(lat0: float) -> tuple[float, float]:
    """(m per deg lon, m per deg lat) — the projection every Lake Murray grid already uses."""
    m_lat = 111_132.92 - 559.82 * math.cos(2 * math.radians(lat0))
    m_lon = 111_412.84 * math.cos(math.radians(lat0)) - 93.5 * math.cos(3 * math.radians(lat0))
    return m_lon, m_lat


# --- the spec -------------------------------------------------------------------------------------


class TierSpec:
    """The parsed ``terrain`` block. ``enabled`` is False for every track without ``tiers``."""

    def __init__(self, terrain: dict | None, origin: dict | None = None, mirror_x: bool = False):
        t = terrain or {}
        tiers = t.get("tiers")
        self.enabled = bool(tiers)
        if not self.enabled:
            return
        self.tiers = [dict(x) for x in tiers]
        if any("cell_m" not in x for x in self.tiers):
            raise ValueError("terrain.tiers: every tier needs cell_m")
        if "within_m" in self.tiers[-1]:
            raise ValueError("terrain.tiers: the last tier is the coarse ground (no within_m)")
        opt = t.get("tier_options") or {}
        self.frame_cfg = dict(opt.get("frame") or {})
        kc = opt.get("keep_cells") or {}
        self.keep_cell_m = float(kc["cell_m"]) if kc else None
        self.keep_within_m = float(kc.get("within_m", 0.0)) if kc else 0.0
        self.physical_m = float(opt.get("physical_within_m", 250.0))
        self.keep_m = float(opt.get("keep_surface_m", 0.0))
        self.keep_feather_m = float(opt.get("keep_feather_m", 0.0))
        self.band_m = float(t.get("terrain_band_m", 22.0))
        self.clamp_full_m = float(t.get("clamp_corridor_m", 80.0))
        self.clamp_release_m = float(t.get("clamp_blend_m", 250.0))
        self.corridors = [dict(c) for c in (t.get("corridors") or [])]
        self.includes = [dict(c) for c in (t.get("include") or [])]
        far = t.get("far_extent") or {}
        self.far_bbox_swne = far.get("bbox_swne")
        if not self.far_bbox_swne:
            raise ValueError("terrain.tiers needs terrain.far_extent.bbox_swne (the dossier's landmark box)")
        cells = {float(x["cell_m"]) for x in self.tiers}
        cells |= {float(c["cell_m"]) for c in self.corridors}
        cells |= {float(c["cell_m"]) for c in self.includes}
        if self.keep_cell_m:
            cells.add(self.keep_cell_m)
        self.levels = sorted(cells, reverse=True)                 # coarse -> fine (nominal metres)
        self.ratios = []
        for a, b in zip(self.levels, self.levels[1:]):
            r = a / b
            if abs(r - round(r)) > 1e-6 or round(r) < 2:
                raise ValueError(f"terrain tiers must nest by integer ratios: {a} / {b} = {r:.4f}")
            self.ratios.append(int(round(r)))
        self.base_m = self.levels[-1] / 2.0
        # cell size of each level in BASE units (even integers: a cell centre is a base node)
        self.r = [int(round(c / self.base_m)) for c in self.levels]
        self.origin = dict(origin or {})
        self.sx = -1.0 if mirror_x else 1.0

    def level_of(self, cell_m: float) -> int:
        for k, c in enumerate(self.levels):
            if abs(c - float(cell_m)) < 1e-6:
                return k
        raise ValueError(cell_m)

    # local metres <-> lon/lat (the assembler's projection; mirror-aware)
    def to_local(self, lon: float, lat: float) -> tuple[float, float]:
        m_lon, m_lat = meters_per_degree(self.origin["lat"])
        return self.sx * (lon - self.origin["lon"]) * m_lon, (lat - self.origin["lat"]) * m_lat

    def to_lonlat(self, x: float, z: float) -> tuple[float, float]:
        m_lon, m_lat = meters_per_degree(self.origin["lat"])
        return self.origin["lon"] + self.sx * x / m_lon, self.origin["lat"] + z / m_lat

    def far_box_local(self) -> tuple[float, float, float, float]:
        s, w, n, e = self.far_bbox_swne
        xa, za = self.to_local(w, s)
        xb, zb = self.to_local(e, n)
        return min(xa, xb), min(za, zb), max(xa, xb), max(za, zb)

    def frame(self, heightfield_meta: dict | None = None) -> "Frame":
        if self.frame_cfg.get("kind", "origin") == "origin":
            return Frame(0.0, 0.0, self.base_m, self.base_m)
        if self.frame_cfg["kind"] != "heightfield":
            raise ValueError(f"tier_options.frame.kind {self.frame_cfg['kind']!r}")
        if heightfield_meta is None:
            raise ValueError("a heightfield frame needs data/heightfield.meta.json")
        if self.sx < 0:
            raise ValueError("a heightfield frame on a mirror_x track is not supported")
        return Frame.heightfield(heightfield_meta, self.origin, int(self.frame_cfg.get("upsample", 1)),
                                 self.levels, self.base_m)


class Frame:
    """where the base lattice sits: (I, J) -> (x0 + I * ux, z0 + J * uz)"""

    def __init__(self, x0, z0, ux, uz):
        self.x0, self.z0, self.ux, self.uz = float(x0), float(z0), float(ux), float(uz)

    @classmethod
    def heightfield(cls, meta, origin, upsample, levels, base_m):
        """the frame whose nominal-``sp`` cells are the heightfield grid's own cells, exactly as the v021
        assembler projects it (build_loop_blend.project_grid): node (row j, col i) at
        x = (w + i*gx - lon0) * m_lon, z = (n - j*gy - lat0) * m_lat, gx/gy from the grid's mid latitude"""
        s, w, n, e = meta["bbox_swne"]
        sp = float(meta["spacing_m"]) / max(1, upsample)
        midlat = (s + n) / 2
        gy = sp / 111_000.0
        gx = sp / (111_000.0 * math.cos(math.radians(midlat)))
        m_lon, m_lat = meters_per_degree(origin["lat"])
        per = sp / base_m                                    # base units per grid cell
        if abs(per - round(per)) > 1e-6 or not any(abs(sp - c) < 1e-6 for c in levels):
            raise ValueError(f"the heightfield's {sp} m cell must be one of the tier cells {levels}")
        per = int(round(per))
        # row 0 is NORTH and rows run south: lattice J = -per * row so J grows northward
        return cls((w - origin["lon"]) * m_lon, (n - origin["lat"]) * m_lat, gx * m_lon / per, gy * m_lat / per)

    def to_json(self):
        return [self.x0, self.z0, self.ux, self.uz]


def load_heightfield_meta(project_dir) -> dict | None:
    p = Path(project_dir) / "data" / "heightfield.meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# --- road points ----------------------------------------------------------------------------------


def densify(lines, spacing: float, closed_first: bool = False):
    """[(x, z, half_width)] along each polyline at <= ``spacing`` m. ``lines`` = [(pts_xyz, widths)];
    the first line is closed when ``closed_first`` (the loop)."""
    out = []
    for li, (pts, widths) in enumerate(lines):
        n = len(pts)
        if n == 0:
            continue
        segs = list(range(n - 1))
        if closed_first and li == 0 and n > 2:
            segs.append(n - 1)
        for k in segs:
            a, b = pts[k], pts[(k + 1) % n]
            wa, wb = widths[k] / 2.0, widths[(k + 1) % n] / 2.0
            L = math.hypot(b[0] - a[0], b[2] - a[2])
            m = max(1, int(math.ceil(L / spacing)))
            for s in range(m):
                t = s / m
                out.append((a[0] + (b[0] - a[0]) * t, a[2] + (b[2] - a[2]) * t, wa + (wb - wa) * t))
        if not (closed_first and li == 0):
            p = pts[-1]
            out.append((p[0], p[2], widths[-1] / 2.0))
    return out


def mark_cells(points, within: float, cx: float, cz: float | None = None, x0: float = 0.0, z0: float = 0.0) -> set:
    """Every (i, j) cell (size cx by cz, anchored at x0, z0) whose rectangle lies within ``within`` of a
    point's pavement edge (point distance − its half-width). Points carry (x, z, half_width)."""
    cz = cx if cz is None else cz
    out = set()
    for x, z, hw in points:
        R = within + hw
        if R < 0:
            continue
        R2 = R * R
        i0, i1 = math.floor((x - R - x0) / cx), math.floor((x + R - x0) / cx)
        for i in range(i0, i1 + 1):
            xa = x0 + i * cx
            xb = xa + cx
            dx = xa - x if x < xa else (x - xb if x > xb else 0.0)
            if dx > R:
                continue
            h = math.sqrt(max(0.0, R2 - dx * dx))
            j0, j1 = math.floor((z - h - z0) / cz), math.floor((z + h - z0) / cz)
            for j in range(j0, j1 + 1):
                out.add((i, j))
    return out


def mark_box(box, cx: float, cz: float | None = None, x0: float = 0.0, z0: float = 0.0) -> set:
    cz = cx if cz is None else cz
    bx0, bz0, bx1, bz1 = box
    return {(i, j) for i in range(math.floor((bx0 - x0) / cx), math.floor((bx1 - x0) / cx) + 1)
            for j in range(math.floor((bz0 - z0) / cz), math.floor((bz1 - z0) / cz) + 1)}


# --- the tree -------------------------------------------------------------------------------------


class Topology:
    """Leaves, vertices (base-lattice keys), triangles and the physical/far split. Deterministic:
    the same inputs give the same vertex order and triangle list, byte for byte."""

    def __init__(self, spec: TierSpec, road_lines, corridor_lines=(), *, closed_first=True, frame: Frame | None = None):
        self.spec = spec
        self.f = frame or spec.frame(None)
        self.r = spec.r
        nlev = len(spec.levels)
        self.nlev = nlev
        f = self.f

        def csz(L):
            return self.r[L] * f.ux, self.r[L] * f.uz

        def mark(points, within, L):
            cx, cz = csz(L)
            return mark_cells(points, within, cx, cz, f.x0, f.z0)

        marks = []                     # (level, cellset, target_level)
        self.xsplit = {}               # level -> parent cells whose children are split in four
        pts_cache = {}

        def pts(sp):
            if sp not in pts_cache:
                pts_cache[sp] = densify(road_lines, sp, closed_first)
            return pts_cache[sp]

        for t in spec.tiers[:-1]:
            L = spec.level_of(t["cell_m"])
            if L == 0:
                continue
            W = float(t["within_m"])
            sp = max(2.0, min(10.0, W / 50.0))
            cells = mark(pts(sp), W, L - 1)
            marks.append((L - 1, cells, L))
            if t.get("x_split"):
                self.xsplit.setdefault(L, set()).update(cells)
        for c, line in zip(spec.corridors, corridor_lines):
            L = spec.level_of(c["cell_m"])
            if L == 0 or not line:
                continue
            cpts = densify([(line, [0.0] * len(line))], 2.0)
            marks.append((L - 1, mark(cpts, float(c["half_width_m"]), L - 1), L))
        for inc in spec.includes:
            L = spec.level_of(inc["cell_m"])
            if L == 0:
                continue
            s, w, n, e = inc["bbox_swne"]
            xa, za = spec.to_local(w, s)
            xb, zb = spec.to_local(e, n)
            cx, cz = csz(L - 1)
            marks.append((L - 1, mark_box((min(xa, xb), min(za, zb), max(xa, xb), max(za, zb)), cx, cz, f.x0, f.z0), L))
        self.keep_level = None
        self.keep = set()
        if spec.keep_cell_m:
            self.keep_level = spec.level_of(spec.keep_cell_m)
            self.keep = mark(pts(2.0), spec.keep_within_m, self.keep_level)
            if self.keep_level > 0:
                marks.append((self.keep_level, self.keep, self.keep_level))
        # physical marks at the finest tier level that is not the coarse ground's
        self.phys_level = min(1, nlev - 1)
        self.phys = mark(pts(5.0), spec.physical_m, self.phys_level)

        # ancestors of every mark (a coarse cell wants to split when any descendant is marked)
        self._marks = []
        for m, cells, tgt in marks:
            anc = {}
            for L in range(m):
                fac = self.r[L] // self.r[m]
                anc[L] = {(i // fac, j // fac) for i, j in cells}
            self._marks.append((m, cells, tgt, anc))

        # the domain: every coarse cell touching the far box
        x0, z0, x1, z1 = spec.far_box_local()
        c0x, c0z = csz(0)
        self.dom = (math.floor((x0 - f.x0) / c0x), math.floor((z0 - f.z0) / c0z),
                    math.floor((x1 - f.x0) / c0x), math.floor((z1 - f.z0) / c0z))
        leaves = set()
        stack = [(0, i, j) for i in range(self.dom[0], self.dom[2] + 1) for j in range(self.dom[1], self.dom[3] + 1)]
        while stack:
            L, i, j = stack.pop()
            frozen = L == self.keep_level and (i, j) in self.keep
            if not frozen and L < nlev - 1 and self._want(L, i, j) > L:
                fac = self.r[L] // self.r[L + 1]
                stack.extend((L + 1, i * fac + a, j * fac + b) for a in range(fac) for b in range(fac))
            else:
                leaves.add((L, i, j))
        self.leaves = leaves
        self._balance()
        self._triangulate()

    # wanted level of a cell = the finest target any mark asks of it
    def _want(self, L, i, j):
        w = L
        for m, cells, tgt, anc in self._marks:
            if tgt <= w:
                continue
            if m == L:
                hit = (i, j) in cells
            elif m > L:
                hit = (i, j) in anc[L]
            else:
                fac = self.r[m] // self.r[L]
                hit = (i // fac, j // fac) in cells
            if hit:
                w = tgt
        return w

    def is_keep(self, key):
        return key[0] == self.keep_level and (key[1], key[2]) in self.keep

    def locate2(self, X2, Z2):
        """the leaf containing the point (X2, Z2) given in HALF base units (exact integer location)"""
        for L in range(self.nlev):
            k = (L, X2 // (2 * self.r[L]), Z2 // (2 * self.r[L]))
            if k in self.leaves:
                return k
        return None

    def _edge_probes(self, L, i, j):
        """(direction, X2, Z2) half-unit points just outside each edge's midpoint"""
        r = self.r[L]
        x0, z0, x1, z1 = 2 * i * r, 2 * j * r, 2 * (i + 1) * r, 2 * (j + 1) * r
        xm, zm = (x0 + x1) // 2, (z0 + z1) // 2
        return (("S", xm, z0 - 1), ("E", x1 + 1, zm), ("N", xm, z1 + 1), ("W", x0 - 1, zm))

    def _split(self, key):
        if self.is_keep(key):
            raise ValueError(f"a kept cell {key} would need splitting: its neighbours are two levels finer — "
                             f"widen the tier gap or narrow keep_cells.within_m")
        L, i, j = key
        self.leaves.discard(key)
        fac = self.r[L] // self.r[L + 1]
        kids = [(L + 1, i * fac + a, j * fac + b) for a in range(fac) for b in range(fac)]
        self.leaves.update(kids)
        return kids

    def _balance(self):
        q = deque(sorted(self.leaves))
        while q:
            k = q.popleft()
            if k not in self.leaves:
                continue
            L = k[0]
            for _d, X2, Z2 in self._edge_probes(*k):
                nb = self.locate2(X2, Z2)
                if nb is not None and nb[0] < L - 1:
                    q.extend(self._split(nb))
                    q.append(k)
                    break

    def _hanging(self, L, i, j, d):
        """base-unit nodes strictly inside edge ``d`` of leaf (L, i, j), from a neighbour one level
        finer (balanced: never more), in the edge's CCW walking order"""
        if L + 1 >= self.nlev:
            return []
        r, rf = self.r[L], self.r[L + 1]
        fac = r // rf
        x0, z0, x1, z1 = i * r, j * r, (i + 1) * r, (j + 1) * r
        if d == "S":
            probe = (L + 1, i * fac, j * fac - 1)
            pts = [(x0 + k * rf, z0) for k in range(1, fac)]
        elif d == "E":
            probe = (L + 1, (i + 1) * fac, j * fac)
            pts = [(x1, z0 + k * rf) for k in range(1, fac)]
        elif d == "N":
            probe = (L + 1, i * fac, (j + 1) * fac)
            pts = [(x1 - k * rf, z1) for k in range(1, fac)]
        else:
            probe = (L + 1, i * fac - 1, j * fac)
            pts = [(x0, z1 - k * rf) for k in range(1, fac)]
        return pts if probe in self.leaves else []

    def _xsplit(self, L, i, j):
        par = self.xsplit.get(L)
        if not par or L == 0:
            return False
        fac = self.r[L - 1] // self.r[L]
        return (i // fac, j // fac) in par

    def _triangulate(self):
        """vertices (sorted base keys), triangles (index triples, face-UP in the left-handed local
        frame: n_y > 0), per-triangle physical flag, per-vertex kept flag"""
        leaves = sorted(self.leaves)
        phys_leaf = self._physical(leaves)
        tri_keys, tri_phys = [], []
        keep_keys = set()
        for key in leaves:
            L, i, j = key
            r = self.r[L]
            sw, se, ne, nw = (i * r, j * r), ((i + 1) * r, j * r), ((i + 1) * r, (j + 1) * r), (i * r, (j + 1) * r)
            ph = key in phys_leaf
            if self.is_keep(key):
                # the graded grid's own triangles (ribbon.grass_terrain): a = NW, b = NE, c = SE, d = SW,
                # (a, b, c) + (a, c, d) — a finer neighbour's nodes on these edges stay T-junctions
                for t in ((nw, ne, se), (nw, se, sw)):
                    tri_keys.append(_face_up(*t)); tri_phys.append(ph)
                keep_keys.update((sw, se, ne, nw))
                for d in "SENW":
                    keep_keys.update(self._hanging(L, i, j, d))
                continue
            ring = [sw] + self._hanging(L, i, j, "S") + [se] + self._hanging(L, i, j, "E") + [ne] \
                + self._hanging(L, i, j, "N") + [nw] + self._hanging(L, i, j, "W")
            if len(ring) == 4 and not self._xsplit(L, i, j):
                for t in ((sw, se, ne), (sw, ne, nw)):
                    tri_keys.append(_face_up(*t)); tri_phys.append(ph)
            else:
                c = (i * r + r // 2, j * r + r // 2)
                for a in range(len(ring)):
                    tri_keys.append(_face_up(c, ring[a], ring[(a + 1) % len(ring)])); tri_phys.append(ph)
        keys = sorted({k for t in tri_keys for k in t})
        index = {k: n for n, k in enumerate(keys)}
        self.vkeys = keys
        self.tris = [(index[a], index[b], index[c]) for a, b, c in tri_keys]
        self.tri_phys = tri_phys
        self.phys_leaves = phys_leaf
        self.vkeep = [k in keep_keys for k in keys]

    def _physical(self, leaves):
        """physical = leaves whose phys-level ancestor is marked, plus every pocket of other leaves
        the far ring cannot reach from the domain's edge (the lake, the hill inside the loop)"""
        P = self.phys_level
        phys = set()
        for key in leaves:
            L, i, j = key
            if L >= P:
                fac = self.r[P] // self.r[L]
                if (i // fac, j // fac) in self.phys:
                    phys.add(key)
        far = [k for k in leaves if k not in phys]
        far_set = set(far)
        d0, e0, d1, e1 = self.dom
        R0 = self.r[0]
        bx0, bz0, bx1, bz1 = d0 * R0, e0 * R0, (d1 + 1) * R0, (e1 + 1) * R0

        def on_edge(k):
            L, i, j = k
            r = self.r[L]
            return i * r == bx0 or j * r == bz0 or (i + 1) * r == bx1 or (j + 1) * r == bz1

        seen = {k for k in far if on_edge(k)}
        q = deque(sorted(seen))
        while q:
            k = q.popleft()
            for nb in self._neighbours(k):
                if nb in far_set and nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        phys |= far_set - seen
        return phys

    def _neighbours(self, key):
        L, i, j = key
        r = self.r[L]
        rf = self.r[L + 1] if L + 1 < self.nlev else r
        x0, z0, x1, z1 = 2 * i * r, 2 * j * r, 2 * (i + 1) * r, 2 * (j + 1) * r
        out = set()
        for k in range(r // rf):
            m = 2 * k * rf + rf
            for X2, Z2 in ((x0 + m, z0 - 1), (x1 + 1, z0 + m), (x0 + m, z1 + 1), (x0 - 1, z0 + m)):
                nb = self.locate2(X2, Z2)
                if nb is not None:
                    out.add(nb)
        return out

    # --- convenience -----------------------------------------------------------------------------
    def xz(self, n: int) -> tuple[float, float]:
        I, J = self.vkeys[n]
        return self.f.x0 + I * self.f.ux, self.f.z0 + J * self.f.uz

    def stats(self) -> dict:
        by = {}
        for L, _i, _j in self.leaves:
            by[self.spec.levels[L]] = by.get(self.spec.levels[L], 0) + 1
        used_p, used_f = set(), set()
        for t, p in zip(self.tris, self.tri_phys):
            (used_p if p else used_f).update(t)
        return {"vertices": len(self.vkeys), "triangles": len(self.tris),
                "leaves_by_cell_m": {str(k): v for k, v in sorted(by.items())},
                "kept_cells": sum(1 for k in self.leaves if self.is_keep(k)), "kept_vertices": sum(self.vkeep),
                "physical_vertices": len(used_p), "far_vertices": len(used_f),
                "physical_triangles": sum(1 for p in self.tri_phys if p),
                "far_triangles": sum(1 for p in self.tri_phys if not p)}


def _face_up(a, b, c):
    """order a base-unit triangle so its normal points UP in the local frame (x = E, y = up, z = N
    is LEFT-handed: n_y = dz1*dx2 - dx1*dz2 > 0 is clockwise seen from above; the frame's positive
    axis scales keep the sign). The assembler's make_mesh reflection (x, y, z) -> (x, z, y) + winding
    reversal keeps it face-up in Blender. An already face-up triangle keeps its vertex order."""
    dx1, dz1 = b[0] - a[0], b[1] - a[1]
    dx2, dz2 = c[0] - a[0], c[1] - a[1]
    return (a, b, c) if dz1 * dx2 - dx1 * dz2 > 0 else (a, c, b)


def split_mesh(tris, tri_flags):
    """[(indices of tris with flag True), (... False)] — the physical / far partition"""
    a = [t for t, f in zip(tris, tri_flags) if f]
    b = [t for t, f in zip(tris, tri_flags) if not f]
    return a, b


def balanced_tiles(tris, xz, cap: int):
    """Partition triangles into tiles of at most ``cap`` unique vertices by recursive MEDIAN
    bisection along the tile's longer horizontal extent (palm.chunk_mesh's rule; equal-width bands
    leave one band over the cap on clustered density — the PALMFROND 82,797 failure). Returns
    [[tri, ...], ...] in a deterministic order. ``xz(i)`` -> (x, z) of vertex i."""
    out = []

    def nverts(ts):
        return len({v for t in ts for v in t})

    def rec(ts):
        if nverts(ts) <= cap or len(ts) < 2:
            out.append(ts)
            return
        cs = []
        for t in ts:
            p = [xz(v) for v in t]
            cs.append(((p[0][0] + p[1][0] + p[2][0]) / 3.0, (p[0][1] + p[1][1] + p[2][1]) / 3.0))
        xs = [c[0] for c in cs]
        zs = [c[1] for c in cs]
        ax = 0 if (max(xs) - min(xs)) >= (max(zs) - min(zs)) else 1
        order = sorted(range(len(ts)), key=lambda k: (cs[k][ax], cs[k][1 - ax], k))
        h = len(order) // 2
        rec([ts[k] for k in order[:h]])
        rec([ts[k] for k in order[h:]])

    rec(list(tris))
    return out
