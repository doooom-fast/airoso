"""The dividers as things the gates understand: the median ISLAND and the declared BARRIER bands.

Ledger 0037 (2026-08-20) put raised landscaped islands ON the pavement of divided roads — the
professional pattern (docs/JUNCTIONS.md: one continuous slab, the island stands on it). Every
gate written before that assumed "nothing that is not road may stand on the road": audit D read
all 25,896 median-barrier verts as walls on a road, K read the island curb as kerb in the
carriageway, I read it as a sidewalk isolating pavement, and drive_test swept its centre wheel
paths straight over the island (the centreline is the island on a divided road). None of those
are defects; all of them are the island. Gates that cannot tell a median from an intrusion would
either fail every divided street forever or get their thresholds raised until they catch nothing
(the V1 disease, fleet/GATES-CHANGELOG.md).

Ledger 0047 (2026-10-10) adds a second divider KIND with the same discipline: the race layouts'
centre chain (a 0.67 m jersey strip on the centreline of every wide road, between the islands)
and the kerb-line barriers (the same strip on both curb faces), declared per vertex in
data/barrier_bands.json by tools/barrier_bands.py — the file tools/author_race_blend.py builds
from, so the declared band IS the authored line. The kinds load INDEPENDENTLY: a track without
barrier_bands.json gets byte-identical island behaviour, a length mismatch disables THAT kind
only (loudly), and every caller that does not ask for the barrier kind never sees it.

This module is the one place that knows where the dividers are. It reads the band files and
the same centreline the gate itself walks (gate_centerline.json = OBJ/engine frame, else
finished_centerline.json, else centerline.local.json with mirror_x), and answers:

    zone = MedianZone.load(project_dir)           # None when the track declares no divider at all
    zone.contains(x, z)                            # on the island? (default kinds = ('island',))
    zone.contains(x, z, ('island', 'barrier'))     # ... or on a declared barrier band
    zone.island_half_at(i)                         # island half-width at centreline vertex i
    zone.barrier_half_at(i)                        # 0.335 where the centre chain stands, else 0
    zone.edge_inset_at(i)                          # the kerb-line barrier's lane inset (0.82), else 0
    zone.reversed()                                # the same zone walked the other way (reverse layouts)

Exempting a vert from a check because it lies on a divider is NOT a bypass: the island is
authored geometry with its own gates (curb 1KERB, deck 1GRASS — the kn5 rename pass enforces the
prefixes); the strip must be PRESENT (drive_test barrier_missing), SEATED (audit E, floating
furniture) and CLEAR OF THE LANE (the lane disc). What the zone must never do is widen: the
margin is one curb batter + one seam (0.6 m), not a corridor.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

MARGIN_M = 0.6
CELL_M = 8.0
ALONG_M = 2.0
ISLAND_KINDS = ("island",)
ALL_KINDS = ("island", "barrier")


def _load_pts(project: Path):
    data = project / "data"
    gate_cl = data / "gate_centerline.json"      # OBJ frame, from kn5_to_gate_obj
    fin = data / "finished_centerline.json"      # KN5 frame (z mirrored) — only if no gate file
    if gate_cl.exists():
        j = json.loads(gate_cl.read_text(encoding="utf-8"))
        return [tuple(p) for p in j["points_xyz_m"]], [float(w) for w in j.get("widths_m", [])]
    if fin.exists():
        j = json.loads(fin.read_text(encoding="utf-8"))
        return [tuple(p) for p in j["points_xyz_m"]], [float(w) for w in j.get("widths_m", [])]
    cfg = json.loads((project / "track.config.json").read_text(encoding="utf-8"))
    mirror = -1.0 if cfg.get("mirror_x", False) else 1.0
    lc = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    return [(mirror * p[0], p[1], p[2]) for p in lc["points_xyz_m"]], [float(w) for w in lc.get("widths_m", [])]


class MedianZone:
    def __init__(self, pts, island_w, extra=(), *, widths=None, centre_w=None, edge_strip=None,
                 edge_inset=None, barrier_half=0.335, edge_centre_from_lip=-0.485, mouths=()):
        """pts/island_w: the mainline (gate frame). extra: [(pts, island_w), ...] for divided
        connectors' islands (tools/divide_connectors.py), same frame as the gate OBJ.
        Barrier kind (all per mainline vertex, same length as pts, or absent): centre_w (the chain's
        base width where it stands), edge_strip (1 where the kerb-line barrier runs), edge_inset
        (the lane inset it takes from the lip), widths (road width — the edge band sits at
        half_w + edge_centre_from_lip), mouths: polylines (gate frame) the strip follows across
        sealed mouths."""
        n = len(pts)
        self.pts = pts
        # a CLOSED lap repeats vertex 0 as its last point; that duplicate is not a vertex of its own
        # (the ribbon and the race author both stop at n - 1 and wrap): the barrier bands take vertex
        # 0's width and a wrapped tangent there — the duplicate carries the LAST street's width
        # (SD: 27.5 m vs Alvarado's 17.0 m) and a one-sided tangent that is 6.8 deg off at the seam
        self.closed = n > 2 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
        self.island_w = list(island_w) if island_w else [0.0] * n
        self.polys = [(pts, self.island_w)] + list(extra)
        self.widths = list(widths) if widths and len(widths) == n else [0.0] * n
        self.centre_w = list(centre_w) if centre_w and len(centre_w) == n else [0.0] * n
        self.edge_strip = list(edge_strip) if edge_strip and len(edge_strip) == n else [0] * n
        self.edge_inset = list(edge_inset) if edge_inset and len(edge_inset) == n else [0.0] * n
        self.barrier_half = float(barrier_half)
        self.edge_centre_from_lip = float(edge_centre_from_lip)
        self.mouths = [[tuple(p) for p in m] for m in mouths]
        self.cells: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for pi, (pp, ww) in enumerate(self.polys):
            for i, w in enumerate(ww):
                if w <= 0:
                    continue
                x, z = pp[i][0], pp[i][2]
                self.cells.setdefault((int(x // CELL_M), int(z // CELL_M)), []).append((pi, i))
        self.n_island = sum(1 for _, ww in self.polys for w in ww if w > 0)
        # barrier bands are hashed by their own CENTRE point (the edge band stands up to half a
        # road away from the centreline vertex, beyond a one-cell reach on a 30 m arterial)
        self.bcells: dict[tuple[int, int], list[tuple[str, int, float, float]]] = {}
        for i in range(n - 1 if self.closed else n):     # the closure duplicate is vertex 0's band
            if self.centre_w[i] > 0:
                self._bput("centre", i, pts[i][0], pts[i][2])
            if self.edge_strip[i]:
                nx, nz = self._normal(i)
                off = self.widths[i] / 2.0 + self.edge_centre_from_lip
                self._bput("edge_L", i, pts[i][0] + nx * off, pts[i][2] + nz * off)
                self._bput("edge_R", i, pts[i][0] - nx * off, pts[i][2] - nz * off)
        for mi, m in enumerate(self.mouths):
            for k in range(len(m) - 1):
                (ax, _, az), (bx, _, bz) = m[k], m[k + 1]
                for cx in range(int(min(ax, bx) // CELL_M), int(max(ax, bx) // CELL_M) + 1):
                    for cz in range(int(min(az, bz) // CELL_M), int(max(az, bz) // CELL_M) + 1):
                        self.bcells.setdefault((cx, cz), []).append(("mouth", mi * 100000 + k, 0.0, 0.0))
        self.n_barrier = sum(1 for w in self.centre_w if w > 0)
        self.n_edge = sum(1 for e in self.edge_strip if e)

    def _bput(self, kind, i, x, z):
        self.bcells.setdefault((int(x // CELL_M), int(z // CELL_M)), []).append((kind, i, x, z))

    def _normal(self, i):
        """left-hand unit normal (-tz, tx) of the local tangent at mainline vertex i (central
        difference; wrapped across the seam of a closed lap, one-sided at the ends of an open one)"""
        pp = self.pts
        if self.closed:
            m = len(pp) - 1
            a, b = pp[(i - 1) % m], pp[(i + 1) % m]
        else:
            a = pp[max(0, i - 1)]
            b = pp[min(len(pp) - 1, i + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1e-9
        return -tz / L, tx / L

    @classmethod
    def load(cls, project_dir) -> "MedianZone | None":
        project = Path(project_dir)
        data = project / "data"
        bands = data / "median_bands.json"
        bbands = data / "barrier_bands.json"
        if not bands.exists() and not bbands.exists():
            return None
        pts, widths = _load_pts(project)
        iw: list = []
        extra = []
        if bands.exists():
            mj = json.loads(bands.read_text(encoding="utf-8"))
            iw = mj.get("island_w_by_vertex", [])
            if len(iw) != len(pts):
                print(f"  [median-zone] bands ({len(iw)}) vs centreline ({len(pts)}) length mismatch "
                      f"— island exemption DISABLED")
                iw = []
            else:
                # divided connectors' islands are stored in the ENGINE frame (connectors.local.json's
                # frame); the gate OBJ is the engine frame too, so no remap — but if the mainline came
                # from finished_centerline (kn5 frame) they would disagree, hence gate_centerline first.
                for ci in mj.get("connector_islands", []):
                    extra.append(([tuple(p) for p in ci["points_xyz_m"]], ci["island_w_by_point"]))
        kw: dict = {}
        if bbands.exists():
            bj = json.loads(bbands.read_text(encoding="utf-8"))
            cw = bj.get("centre_w_by_vertex", [])
            if len(cw) != len(pts):
                print(f"  [median-zone] barrier_bands ({len(cw)}) vs centreline ({len(pts)}) length mismatch "
                      f"— barrier exemption DISABLED")
            else:
                params = bj.get("params", {})
                kw = {"centre_w": cw, "edge_strip": bj.get("edge_strip_by_vertex", []),
                      "edge_inset": bj.get("edge_inset_by_vertex", []),
                      "barrier_half": float(params.get("barrier_half_m", 0.335)),
                      "edge_centre_from_lip": float(params.get("edge_centre_from_lip_m", -0.485)),
                      "mouths": [m.get("polyline_xyz_m", []) for m in bj.get("closed_mouths", [])]}
                if len(kw["edge_strip"]) != len(pts):
                    kw["edge_strip"] = []
                if len(kw["edge_inset"]) != len(pts):
                    kw["edge_inset"] = []
        zone = cls(pts, iw, extra, widths=widths, **kw)
        if zone.n_island == 0 and zone.n_barrier == 0 and zone.n_edge == 0:
            return None
        return zone

    # ---- per-vertex lookups (index into the mainline the gate walks) -----------------------
    def island_half_at(self, i: int) -> float:
        if 0 <= i < len(self.island_w):
            return self.island_w[i] / 2.0
        return 0.0

    def barrier_half_at(self, i: int) -> float:
        """half-width of the centre chain where the band declares it (0.335), else 0"""
        if 0 <= i < len(self.centre_w) and self.centre_w[i] > 0:
            return self.barrier_half
        return 0.0

    def divider_half_at(self, i: int) -> float:
        return max(self.island_half_at(i), self.barrier_half_at(i))

    def edge_inset_at(self, i: int) -> float:
        """the lane inset the kerb-line barrier takes from the pavement lip (0 where it is gapped,
        and 0 in 'walk' mode where the strip stands on the sidewalk)"""
        if 0 <= i < len(self.edge_strip) and self.edge_strip[i]:
            return self.edge_inset[i]
        return 0.0

    def edge_strip_at(self, i: int) -> bool:
        return 0 <= i < len(self.edge_strip) and bool(self.edge_strip[i])

    @property
    def has_barrier(self) -> bool:
        return self.n_barrier > 0 or self.n_edge > 0

    def reversed(self) -> "MedianZone":
        """The same dividers indexed the other way round (a `direction: reverse` layout walks the
        lap backwards; station 0 stays the seam because a closed lap repeats its first vertex)."""
        return MedianZone(self.pts[::-1], self.island_w[::-1], self.polys[1:],
                          widths=self.widths[::-1], centre_w=self.centre_w[::-1],
                          edge_strip=self.edge_strip[::-1], edge_inset=self.edge_inset[::-1],
                          barrier_half=self.barrier_half, edge_centre_from_lip=self.edge_centre_from_lip,
                          mouths=self.mouths)

    # ---- the band test --------------------------------------------------------------------
    def contains(self, x: float, z: float, kinds=ISLAND_KINDS) -> bool:
        """Mesh-frame point within (band half-width + MARGIN) of a declared divider vertex —
        measured laterally to the local tangent so the test is a band, not a disc."""
        cx, cz = int(x // CELL_M), int(z // CELL_M)
        if "island" in kinds:
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for (pi, i) in self.cells.get((cx + dx, cz + dz), ()):
                        pp, ww = self.polys[pi]
                        px, _, pz = pp[i]
                        a = pp[max(0, i - 1)]
                        b = pp[min(len(pp) - 1, i + 1)]
                        tx, tz = b[0] - a[0], b[2] - a[2]
                        L = math.hypot(tx, tz) or 1e-9
                        tx, tz = tx / L, tz / L
                        vx, vz = x - px, z - pz
                        along = abs(vx * tx + vz * tz)
                        lat = abs(-vx * tz + vz * tx)
                        if along <= ALONG_M and lat <= ww[i] / 2.0 + MARGIN_M:
                            return True
        if "barrier" in kinds and self.bcells:
            reach = self.barrier_half + MARGIN_M
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for (kind, i, bx, bz) in self.bcells.get((cx + dx, cz + dz), ()):
                        if kind == "mouth":
                            m = self.mouths[i // 100000]
                            k = i % 100000
                            if self._seg_dist(x, z, m[k], m[k + 1]) <= reach:
                                return True
                            continue
                        nx, nz = self._normal(i)
                        tx, tz = nz, -nx            # tangent from the left normal (-tz, tx)
                        vx, vz = x - bx, z - bz
                        along = abs(vx * tx + vz * tz)
                        lat = abs(vx * nx + vz * nz)
                        if along <= ALONG_M and lat <= reach:
                            return True
                        # CONTINUOUS between consecutive declared vertices of the same kind (2026-10-11):
                        # on the outside lip of a 10 m corner the edge-band points stand ~7 m apart, so
                        # the +-2 m rectangles left ~3 m gaps the declared strip runs straight through
                        # (race_furniture.densify_rings puts rings there). Same lateral reach, no widening.
                        for j in (i - 1, i + 1):
                            q = self._band_point(kind, j)
                            if q is not None and self._span_dist(x, z, bx, bz, q[0], q[2]) <= reach:
                                return True
        return False

    @staticmethod
    def _span_dist(x, z, ax, az, bx, bz):
        """distance to the segment a-b itself (no along extension: the end rectangles own the ends)"""
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
        return math.hypot(x - (ax + t * dx), z - (az + t * dz))

    def _band_point(self, kind, j):
        """(x, 0, z) of the declared band point of `kind` at mainline vertex j, None where that kind
        is not declared (or j is off the mainline)"""
        if self.closed:
            j %= len(self.pts) - 1                        # across the seam: -1 -> n-2, n-1 -> 0
        elif not 0 <= j < len(self.pts):
            return None
        if kind == "centre":
            return (self.pts[j][0], 0.0, self.pts[j][2]) if self.centre_w[j] > 0 else None
        if kind in ("edge_L", "edge_R") and self.edge_strip[j]:
            nx, nz = self._normal(j)
            off = (self.widths[j] / 2.0 + self.edge_centre_from_lip) * (1.0 if kind == "edge_L" else -1.0)
            return (self.pts[j][0] + nx * off, 0.0, self.pts[j][2] + nz * off)
        return None

    @staticmethod
    def _seg_dist(x, z, a, b):
        ax, az, bx, bz = a[0], a[2], b[0], b[2]
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 < 1e-12 else max(-ALONG_M / math.sqrt(L2), min(1.0 + ALONG_M / math.sqrt(L2),
                                                                      ((x - ax) * dx + (z - az) * dz) / L2))
        return math.hypot(x - (ax + t * dx), z - (az + t * dz))
