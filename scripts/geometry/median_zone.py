"""The median island as a thing the gates understand.

Ledger 0037 (2026-08-20) put raised landscaped islands ON the pavement of divided roads — the
professional pattern (docs/JUNCTIONS.md: one continuous slab, the island stands on it). Every
gate written before that assumed "nothing that is not road may stand on the road": audit D read
all 25,896 median-barrier verts as walls on a road, K read the island curb as kerb in the
carriageway, I read it as a sidewalk isolating pavement, and drive_test swept its centre wheel
paths straight over the island (the centreline is the island on a divided road). None of those
are defects; all of them are the island. Gates that cannot tell a median from an intrusion would
either fail every divided street forever or get their thresholds raised until they catch nothing
(the V1 disease, fleet/GATES-CHANGELOG.md).

This module is the one place that knows where the island is. It reads data/median_bands.json
(written by tools/median_envelope.py: per-centreline-vertex island width, 0 = no island) and the
same centreline the gate itself walks (finished_centerline.json = mesh frame, else
centerline.local.json with mirror_x), and answers two questions:

    zone = MedianZone.load(project_dir)           # None when the track declares no island
    zone.contains(x, z)                            # is this mesh-frame point on the island?
    zone.island_half_at(i)                         # island half-width at centreline vertex i

Exempting a vert from a check because it lies on the island is NOT a bypass: the island is
authored geometry with its own gates (the curb must be collidable 1KERB, the deck 1GRASS — the
kn5 rename pass enforces the prefixes). What it must never do is widen: the margin is one curb
batter + one seam (0.6 m), not a corridor.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

MARGIN_M = 0.6
CELL_M = 8.0


class MedianZone:
    def __init__(self, pts, island_w, extra=()):
        """pts/island_w: the mainline (gate frame). extra: [(pts, island_w), ...] for divided
        connectors' islands (tools/divide_connectors.py), same frame as the gate OBJ."""
        self.pts = pts
        self.island_w = island_w
        self.polys = [(pts, island_w)] + list(extra)
        self.cells: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for pi, (pp, ww) in enumerate(self.polys):
            for i, w in enumerate(ww):
                if w <= 0:
                    continue
                x, z = pp[i][0], pp[i][2]
                self.cells.setdefault((int(x // CELL_M), int(z // CELL_M)), []).append((pi, i))
        self.n_island = sum(1 for _, ww in self.polys for w in ww if w > 0)

    @classmethod
    def load(cls, project_dir) -> "MedianZone | None":
        project = Path(project_dir)
        data = project / "data"
        bands = data / "median_bands.json"
        if not bands.exists():
            return None
        iw = json.loads(bands.read_text(encoding="utf-8")).get("island_w_by_vertex", [])
        gate_cl = data / "gate_centerline.json"      # OBJ frame, from kn5_to_gate_obj
        fin = data / "finished_centerline.json"      # KN5 frame (z mirrored) — only if no gate file
        if gate_cl.exists():
            pts = [tuple(p) for p in json.loads(gate_cl.read_text(encoding="utf-8"))["points_xyz_m"]]
        elif fin.exists():
            pts = [tuple(p) for p in json.loads(fin.read_text(encoding="utf-8"))["points_xyz_m"]]
        else:
            cfg = json.loads((project / "track.config.json").read_text(encoding="utf-8"))
            mirror = -1.0 if cfg.get("mirror_x", False) else 1.0
            lc = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
            pts = [(mirror * p[0], p[1], p[2]) for p in lc["points_xyz_m"]]
        if len(iw) != len(pts):
            print(f"  [median-zone] bands ({len(iw)}) vs centreline ({len(pts)}) length mismatch "
                  f"— island exemption DISABLED")
            return None
        # divided connectors' islands are stored in the ENGINE frame (connectors.local.json's
        # frame); the gate OBJ is the engine frame too, so no remap — but if the mainline came
        # from finished_centerline (kn5 frame) they would disagree, hence gate_centerline first.
        extra = []
        for ci in json.loads(bands.read_text(encoding="utf-8")).get("connector_islands", []):
            extra.append(([tuple(p) for p in ci["points_xyz_m"]], ci["island_w_by_point"]))
        zone = cls(pts, iw, extra)
        if zone.n_island == 0:
            return None
        return zone

    def island_half_at(self, i: int) -> float:
        if 0 <= i < len(self.island_w):
            return self.island_w[i] / 2.0
        return 0.0

    def contains(self, x: float, z: float) -> bool:
        """Mesh-frame point within (island half-width + MARGIN) of an island centreline vertex —
        measured laterally to the local tangent so the test is a band, not a disc."""
        cx, cz = int(x // CELL_M), int(z // CELL_M)
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
                    if along <= 2.0 and lat <= ww[i] / 2.0 + MARGIN_M:
                        return True
        return False
