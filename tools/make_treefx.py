"""Emit CSP TreeFX for the track: real palm / street-tree / scrub models, GPU-instanced, zero kn5 cost.

Positions: the draft's own palm/tree/scrub/median-plant placement (data/scatter_positions.json,
tools/export_scatter_blend.py) PLUS a density fill over the terrain grid (Kevin 2026-10-09: "fill in
with lots more trees and bushes") — yards 6-40 m past the pavement, slopes 40-120 m, far ground to
200 m, each with its own tree/bush mix and probability, hash-deterministic per 10 m sub-cell, never
in a road corridor, never in the lake basin (cells > 8 m below the nearest road). Species are the
.bin models in <project>/source/trees/ (personal-use mod content, gitignored, never committed —
docs/TREEFX-FORMAT.md).

Writes build/<slug>/extension/trees/trees.txt (+ copies the .bins beside it) and a [TREES] block in
build/<slug>/extension/ext_config.ini between V3 markers (idempotent). Grammar per
docs/TREEFX-FORMAT.md: `tree: <model>.bin; pos=X, Y, Z; angle = deg; size = mult`, positions in the
kn5 world (x, y, -z of the engine frame), trees snap vertically onto SURFACE_MATERIALS.
NO comment lines: CSP parses a non-directive first line as a manifest filename (2026-10-08).

Corridor guard: TreeFX trees are invisible to drive_test/audit, so every entry is rejected if it
stands within (half-width + 1 m) of the mainline or any connector centreline — or of an I-8 carriageway
(data/freeway_i8.json, the visual freeway pavement: ledger 0046 v0.18.0 integration fix round).

THE NORTH NETWORK (ledger 0054 P4 step 3, EXPANSION-PLAN A9 "trees by zone, not one uniform mix"), opt-in by
track.config.json scenery.treefx: the heightfield cells the P2 growth added (heightfield.meta.json grid_grow) are
planted here — the loop's own cells keep their numbering and their trees, byte for byte. Each added 10 m sub-cell
beside a north piece is zoned by the piece, the side and the station (scenery.treefx.zones, first match wins) and
gets its density from the aerial lens's vegetation bins (source/expansion/aerial__veg_bins.json: per piece, per
250 m, per side, the canopy and scrub shares of the 10-40 m band off NAIP 2022 CIR). The caps scale with planted
AREA: the loop's own density per m2 (its caps over its in-band sub-cells) is the north's cap, and both are printed
before anything is written. Nothing stands on a junction pad (data/pads.built.json outlines), on a rock cut face
(scenery.treefx.rock_walls: P3's measurement of the real walls 3 m or more, 12-20 m off Jackson north and Mission
Gorge — bare from the curb to NORTH_ROCK_REACH_M along each one; a lower bank is soil and gets its scrub), within
the 6 m yard setback of any pavement (curbs, sidewalks, stubs, K-rail), or on a
terracotta / painted / hatched median. The raised islands' low planting is the assembler's (author_median_blend ->
scatter_positions.json median_planting, every island, v0.19.0 shipped it); Waring's planted median gets its real
trees on top at st 250-550 (A2; scenery.treefx.median_trees).

THE BUILT-SURFACE GUARD (ledger 0054 P4 integration fix round): the planner above reads plans — centrelines, pad
outlines, P3's wall measurement. The gate OBJ (data/track.obj, the road kn5 the chain just exported) is the truth, so
every guarded plant is judged against it last: the spot is dropped when the triangle under it is a road (1ROAD*), a
walk (1KERB*), a rock cut face (1GRASS_ROCK*, tools/rock_faces_blend.py — 10 of the 16 cut bands, not only P3's 16
measured walls), or when it stands inside a HOUSE / BUILDING footprint or within BUILT_BUILDING_CLEAR_M of one (TreeFX
snaps a trunk onto whatever ground it finds, so a tree planted inside a footprint grows up through the roof). The
loop's lines keep their numbering (every hash is the same); only the dropped lines go. The raised islands' plantings
(median_planting, north_median_trees) stand on the pavement under their island by design and are not guarded.

    python tools/make_treefx.py <project-dir>
"""
from __future__ import annotations

import ast
import json
import math
import shutil
import struct
import sys
from pathlib import Path

ROAD_SURFACE_MATERIAL = "1ROAD_road_mat"
# Trees snap onto EVERY physical grass tile + the road. The tile count follows the terrain (ledger 0046: the
# tiered ground tiles 1GRASS by balanced bisection into as many tiles as it needs), so the names are read off
# the BUILT road kn5's gate OBJ (data/track.obj, written before the track folder) — never hard-coded (it was
# "1GRASS_0_mat, 1GRASS_1_mat, 1ROAD_road_mat"). The far ring GRASS_FAR is not physical and is not listed.


def surface_materials(project_dir) -> str:
    obj = Path(project_dir) / "data" / "track.obj"
    if not obj.exists():
        raise SystemExit(f"[treefx] {obj} missing — the SURFACE_MATERIALS tile names come from the built road kn5's "
                         f"gate OBJ (python -m scripts.modkit.kn5_to_gate_obj <project>)")
    mats = set()
    with open(obj, encoding="utf-8", errors="replace") as f:
        for ln in f:
            if ln.startswith("usemtl ") and ln[7:].strip().upper().startswith("1GRASS"):
                mats.add(ln[7:].strip())
    if not mats:
        raise SystemExit(f"[treefx] {obj} holds no 1GRASS material — nothing for the trees to stand on")

    def natural(m):
        import re
        return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", m)]
    return ", ".join(sorted(mats, key=natural) + [ROAD_SURFACE_MATERIAL])
# species, size multiplier range, weight — palms: nohesi V1 20 m / V2 25 m / V3 28 m native;
# residential San Diego fan palms run 10-20 m, so they are scaled down
ZONES = {
    "palms": [("PalmV1.bin", 0.65, 0.95, 6), ("PalmV2.bin", 0.55, 0.8, 3), ("PalmV3.bin", 0.5, 0.7, 1)],
    "trees": [("PepperV1.bin", 0.8, 1.1, 3), ("SycamoreV1.bin", 0.7, 1.0, 2), ("SycamoreV2.bin", 0.7, 1.0, 2),
              ("Gum.bin", 0.6, 0.9, 2), ("Pine_Aleppo.bin", 0.7, 1.0, 1), ("Oak3.bin", 0.6, 0.9, 2)],
    "scrub": [("Sage.bin", 0.8, 1.2, 4), ("Yucca.bin", 0.7, 1.1, 2), ("Bush.bin", 0.6, 1.0, 2),
              ("Bush3.bin", 0.5, 0.9, 1), ("Agave.bin", 0.6, 1.0, 1)],
    # Kevin 2026-10-09: "median bushes are a little too tall" — was Bush 0.35-0.6 / Sage 0.5-0.8
    "median_planting": [("Bush.bin", 0.24, 0.40, 3), ("Sage.bin", 0.34, 0.52, 2)],
    # density fill (2026-10-09)
    "fill_yard_trees": [("PepperV1.bin", 0.8, 1.1, 3), ("SycamoreV1.bin", 0.7, 1.0, 2), ("Oak3.bin", 0.6, 0.9, 2),
                        ("Gum.bin", 0.6, 0.9, 1), ("Pine_Aleppo.bin", 0.7, 1.0, 1), ("PalmV1.bin", 0.6, 0.9, 1)],
    "fill_yard_bushes": [("Bush.bin", 0.6, 1.0, 3), ("Bush3.bin", 0.5, 0.9, 2), ("Sage.bin", 0.7, 1.1, 2)],
    "fill_slope_trees": [("Gum.bin", 0.6, 1.0, 3), ("Pine_Aleppo.bin", 0.7, 1.1, 2), ("Oak3.bin", 0.6, 0.9, 1)],
    "fill_slope_bushes": [("Sage.bin", 0.8, 1.3, 4), ("Yucca.bin", 0.7, 1.1, 2), ("Agave.bin", 0.6, 1.0, 1),
                          ("Bush.bin", 0.6, 1.0, 2), ("Bush3.bin", 0.5, 0.9, 1)],
    # --- the north network (ledger 0054 P4, EXPANSION-PLAN A9 / DOSSIER-EXPANSION-NORTH §6), chosen per zone by
    #     track.config.json scenery.treefx.zones; no palms in the canyon (A9) ---
    "north_suburb_trees": [("PepperV1.bin", 0.8, 1.1, 3), ("SycamoreV1.bin", 0.7, 1.0, 2), ("Oak3.bin", 0.6, 0.9, 2),
                           ("Gum.bin", 0.6, 0.9, 1), ("Pine_Aleppo.bin", 0.7, 1.0, 1), ("PalmV1.bin", 0.6, 0.9, 1)],
    "north_suburb_bushes": [("Bush.bin", 0.6, 1.0, 3), ("Bush3.bin", 0.5, 0.9, 2), ("Sage.bin", 0.7, 1.1, 2)],
    # open slopes: chaparral / coastal sage scrub, with the natives that stand over it
    "north_canyon_trees": [("Oak3.bin", 0.6, 0.9, 3), ("Pine_Aleppo.bin", 0.7, 1.0, 2), ("Gum.bin", 0.6, 0.9, 1)],
    "north_scrub": [("Sage.bin", 0.8, 1.3, 4), ("Yucca.bin", 0.7, 1.1, 2), ("Bush.bin", 0.6, 1.0, 2),
                    ("Bush3.bin", 0.5, 0.9, 1), ("Agave.bin", 0.6, 1.0, 1)],
    # the river belt north of Mission Gorge: willow / cottonwood / sycamore stand-ins (A9)
    "north_riparian_trees": [("SycamoreV1.bin", 0.8, 1.1, 3), ("SycamoreV2.bin", 0.8, 1.1, 2), ("Oak3.bin", 0.6, 0.9, 2)],
    # the apartment frontage on Mission Gorge: street trees
    "north_street_trees": [("PepperV1.bin", 0.8, 1.1, 3), ("SycamoreV1.bin", 0.7, 1.0, 2), ("Oak3.bin", 0.6, 0.9, 1),
                           ("PalmV1.bin", 0.6, 0.9, 1)],
    # E1, the tall grey-green belt on the NE side of Jackson's canyon (0040; Street View confirms the species)
    "north_gum_belt": [("Gum.bin", 0.8, 1.1, 5), ("Oak3.bin", 0.6, 0.9, 1)],
    # PLANTED (ledger 0063, scenery.treefx.planted): a track's own measured points, each mix sized by the point's height.
    # Sand Creek's cottonwoods off NAIP: there is no cottonwood model, so the sycamores, the riparian stand-in north_riparian_trees uses
    "planted_cottonwood": [("SycamoreV1.bin", 0.8, 1.1, 3), ("SycamoreV2.bin", 0.8, 1.1, 2), ("SycamoreV3.bin", 0.8, 1.1, 2)],
    "planted_neighbourhood": [("Oak3.bin", 0.6, 0.9, 3), ("SycamoreV2.bin", 0.6, 0.9, 1)],
    # Waring's planted median: small median trees (A2, st 250-550). The islands' LOW planting is not here: the
    # assembler (author_median_blend) already plants every raised island, north pieces included, and exports it as
    # scatter_positions.json median_planting (v0.19.0 shipped it)
    "north_median_trees": [("PepperV1.bin", 0.45, 0.65, 2), ("Oak3.bin", 0.40, 0.55, 1)],
}
NORTH_ZONE_ORDER = ("north_suburb_trees", "north_suburb_bushes", "north_canyon_trees", "north_scrub",
                    "north_riparian_trees", "north_street_trees", "north_gum_belt", "north_median_trees")
NORTH_IDX_BASE = 500000            # emit_zone index bases continue past the loop's four fill zones (100000..400000)
NORTH_CELL_BASE = 50_000_000       # hash keys of the ADDED cells: the grown grid's own cell index, far above the loop's keys
NORTH_BIN_M = 250.0                # the aerial lens's vegetation bins: one per 250 m of each piece, per side
NORTH_TREE_PER_CANOPY = 2.5        # [invented] p(tree per 10 m sub-cell) = this x the bin's canopy share: one ~50 m2 crown per
                                   # 100 m2 at a 40 % canopy; Waring's 5-14 % lands at 0.13-0.35, the loop's own yard rate (0.30)
NORTH_BUSH_PER_SCRUB = 2.0         # [invented] p(bush) = this x the bin's scrub share (+ NORTH_BUSH_FLOOR under any canopy)
NORTH_BUSH_FLOOR = 0.05
NORTH_P_TREE_MAX = 0.85            # one plant per sub-cell at most (the loop's rule); a few cells left open even in a woodland
NORTH_P_SUM_MAX = 0.95
NORTH_FAR_FROM_M = 120.0           # past this from the pavement the rate halves, as the loop's own far band (120-200 m) halves
NORTH_FAR_FACTOR = 0.5
NORTH_ROCK_RISE_M = 3.0            # a measured real wall this high or more (scenery.treefx.rock_walls: the P3 measurement of
                                   # record, EXPANSION-PLAN V7 "a real wall of 3 m or more", 12-20 m off the pavement) is bare rock
NORTH_ROCK_REACH_M = 20.0          # nothing stands between the curb and this far out along it (the face itself, V7's 12-20 m)
NORTH_ROCK_PAD_M = 5.0             # the measurement's station spacing, added to each end of a wall stretch
NORTH_MEDIAN_TREE_STEP_M = 12.0    # [invented] one median tree every 12 m where the island is NORTH_MEDIAN_TREE_MIN_W_M wide
NORTH_MEDIAN_TREE_MIN_W_M = 2.5
NORTH_MEDIAN_INSET_M = 0.5         # a median tree stands this far inside the island's outline
NORTH_MEDIAN_END_CLEAR_M = 6.0     # and this far from each nose (author_expansion NOSE_M)
FILL_BANDS = [   # (off_min, off_max, tree zone, p_tree, bush zone, p_bush) per 10 m sub-cell
    (6.0, 40.0, "fill_yard_trees", 0.30, "fill_yard_bushes", 0.28),
    (40.0, 120.0, "fill_slope_trees", 0.14, "fill_slope_bushes", 0.50),
    (120.0, 200.0, "fill_slope_trees", 0.06, "fill_slope_bushes", 0.28),
]
FILL_STEP_M = 10.0
LAKE_DROP_M = 8.0
APRON_PLANT_CLEAR_M = 1.0   # [invented] ledger 0054 P1 fix round: no plant within this of a corner apron's outline
BUILT_BUILDING_CLEAR_M = 1.0   # [invented] ledger 0054 P4 integration fix round: no plant inside a built HOUSE / BUILDING
                               # footprint or within this of its walls (the apron rule's own margin; a bush against a wall
                               # is a hedge, a trunk inside the wall is a tree through the roof)
BUILT_SURFACE_KINDS = (("1GRASS_ROCK", "rock"), ("1ROAD", "road"), ("1KERB", "walk"), ("HOUSE", "building"),
                       ("BUILDING", "building"))   # gate OBJ object prefixes the guard reads (first match wins)
BUILT_CELL_M = 12.0
CAP_TREES, CAP_BUSHES = 3500, 9000
MARK_BEGIN, MARK_END = "; --- V3 TREEFX BEGIN (tools/make_treefx.py) ---", "; --- V3 TREEFX END ---"


def _hash(i, salt):
    """deterministic, decorrelated across salts (the first version was affine in the salt, so a
    'keep' draw tracked the 'place' draw and the thinning under-thinned 2x)"""
    h = (i ^ (salt * 0x9E3779B1)) & 0xFFFFFFFF
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 4294967296.0


def _read_npy(path):
    with open(path, "rb") as f:
        assert f.read(6) == b"\x93NUMPY"
        f.read(2)
        hlen = struct.unpack("<H", f.read(2))[0]
        header = ast.literal_eval(f.read(hlen).decode())
        ny, nx = header["shape"]
        data = struct.unpack(f"<{ny * nx}d", f.read(8 * ny * nx))
    return [list(data[j * nx:(j + 1) * nx]) for j in range(ny)], ny, nx


def _mpd(lat0):
    m_lat = 111_132.92 - 559.82 * math.cos(2 * math.radians(lat0))
    m_lon = 111_412.84 * math.cos(math.radians(lat0)) - 93.5 * math.cos(3 * math.radians(lat0))
    return m_lon, m_lat


class RoadField:
    """nearest pavement edge distance (+ nearest road height) from any road centreline"""

    def __init__(self, lines, cell=60.0):
        self.lines = lines
        self.cell = cell
        self.cells = {}
        for li, (pts, halves) in enumerate(lines):
            for i in range(len(pts) - 1):
                for (x, _, z) in (pts[i], pts[i + 1]):
                    self.cells.setdefault((int(x // cell), int(z // cell)), set()).add((li, i))

    def query(self, x, z, reach=1):
        best = (float("inf"), 0.0, 0.0)   # (edge distance, road y, half)
        cx, cz = int(x // self.cell), int(z // self.cell)
        for dx in range(-reach, reach + 1):
            for dz in range(-reach, reach + 1):
                for (li, i) in self.cells.get((cx + dx, cz + dz), ()):
                    pts, halves = self.lines[li]
                    ax, ay, az = pts[i]
                    bx, by, bz = pts[i + 1]
                    ddx, ddz = bx - ax, bz - az
                    L2 = ddx * ddx + ddz * ddz
                    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * ddx + (z - az) * ddz) / L2))
                    d = math.hypot(x - (ax + t * ddx), z - (az + t * ddz))
                    half = halves[i] * (1 - t) + halves[min(i + 1, len(halves) - 1)] * t
                    if d - half < best[0]:
                        best = (d - half, ay + (by - ay) * t, half)
        return best


def _in_poly(poly, x, z):
    inside = False
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (a[1] > z) != (b[1] > z) and x < a[0] + (z - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
            inside = not inside
    return inside


def _edge_dist(poly, x, z):
    best = float("inf")
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / L2))
        best = min(best, math.hypot(x - (a[0] + t * dx), z - (a[1] + t * dz)))
    return best


class North:
    """The north network's planting rules (ledger 0054 P4 / A9), read from track.config.json scenery.treefx and the
    files it names (project-relative): the readable intermediate (pieces, medians), the aerial vegetation bins, the
    built junction pads and the ground-release cut zones. None of it exists for a project without the config."""

    def __init__(self, proj: Path, cfg: dict):
        self.cfg = cfg
        self.bin_m = float(cfg.get("bin_m", NORTH_BIN_M))
        exp = json.loads((proj / cfg.get("pieces", "data/expansion.north.json")).read_text(encoding="utf-8"))
        self.pieces = {}
        self.cell = 50.0
        self.cells = {}
        for p in exp["pieces"]:
            cols = p["columns"]
            rows = [{c: r[k] for k, c in enumerate(cols)} for r in p["stations"]]
            self.pieces[p["id"]] = rows
            for i, r in enumerate(rows):
                self.cells.setdefault((int(r["x"] // self.cell), int(r["z"] // self.cell)), []).append((p["id"], i))
        self.medians = exp.get("medians", [])
        vb = proj / cfg["veg_bins"]
        self.bins = json.loads(vb.read_text(encoding="utf-8"))
        self.zones = cfg.get("zones", [])
        self.median_trees = cfg.get("median_trees", [])
        self.median_tree_types = set(cfg.get("median_tree_types", ["planted"]))
        self.pads = []
        pb = proj / "data" / "pads.built.json"
        if pb.exists():
            self.pads = [[tuple(q) for q in p["outline_xz"]] for p in json.loads(pb.read_text(encoding="utf-8")).get("pads", [])]
        self.rock = []     # (piece, side, s_from, s_to): the measured real walls of NORTH_ROCK_RISE_M or more
        if cfg.get("rock_walls"):
            rw = json.loads((proj / cfg["rock_walls"]).read_text(encoding="utf-8"))
            walls = rw if isinstance(rw, list) else ((rw.get("walls") or {}).get("real_walls_ge_3m") or rw.get("real_walls_ge_3m") or [])
            for w in walls:
                if float(w.get("max_real_m", NORTH_ROCK_RISE_M)) < NORTH_ROCK_RISE_M:
                    continue
                self.rock.append((w["piece"], 1 if str(w["side"]).lower().startswith("l") else -1,
                                  float(w["s_from"]) - NORTH_ROCK_PAD_M, float(w["s_to"]) + NORTH_ROCK_PAD_M))
        self.drops = {"pad": 0, "rock": 0}

    def locate(self, x, z, reach_m=220.0):
        """(piece, s, side, off_curb) of the nearest piece station within reach_m of the point, else None. side +1 =
        left of the forward direction (the intermediate's own sign); off_curb = metres past that side's curb"""
        best = None
        cx, cz = int(x // self.cell), int(z // self.cell)
        n = int(reach_m // self.cell) + 1
        for dx in range(-n, n + 1):
            for dz in range(-n, n + 1):
                for pid, i in self.cells.get((cx + dx, cz + dz), ()):
                    r = self.pieces[pid][i]
                    d = math.hypot(x - r["x"], z - r["z"])
                    if d <= reach_m and (best is None or d < best[0]):
                        best = (d, pid, i)
        if best is None:
            return None
        d, pid, i = best
        rows = self.pieces[pid]
        a = rows[max(0, i - 1)]
        b = rows[min(len(rows) - 1, i + 1)]
        tx, tz = b["x"] - a["x"], b["z"] - a["z"]
        L = math.hypot(tx, tz) or 1.0
        lat = (-tz * (x - rows[i]["x"]) + tx * (z - rows[i]["z"])) / L     # + = left of forward
        side = 1 if lat >= 0 else -1
        curb = float(rows[i]["left_m"]) if side > 0 else -float(rows[i]["right_m"])
        return pid, float(rows[i]["s"]), side, abs(lat) - abs(curb)

    def shares(self, piece, side, s):
        """(canopy share, scrub share) of the aerial bin at that station and side: [other, canopy, water, scrub] pixels of
        the 10-40 m band; past the last bin, the last bin"""
        bins = self.bins.get(piece) or {}
        tag = "L" if side > 0 else "R"
        keys = sorted((int(k[:-1]) for k in bins if k.endswith(tag)), key=int)
        if not keys:
            return 0.0, 0.0
        k = min(int(s // self.bin_m), keys[-1])
        while k not in keys and k > 0:
            k -= 1
        c = bins.get(f"{k}{tag}") or [0, 0, 0, 0]
        tot = float(sum(c)) or 1.0
        return c[1] / tot, c[3] / tot

    def zone(self, piece, side, s):
        """(tree zone, bush zone) by scenery.treefx.zones: first rule naming the piece whose side / s (if given) match"""
        for r in self.zones:
            if r.get("piece") != piece:
                continue
            if "side" in r and (1 if str(r["side"]).upper().startswith("L") else -1) != side:
                continue
            if "s" in r and not (float(r["s"][0]) <= s < float(r["s"][1])):
                continue
            return r["trees"], r["bushes"]
        return None

    def on_pad(self, x, z):
        for poly in self.pads:
            if _in_poly(poly, x, z) or _edge_dist(poly, x, z) < APRON_PLANT_CLEAR_M:
                self.drops["pad"] += 1
                return True
        return False

    def on_rock(self, piece, side, s, off_curb):
        for (p, sd, s0, s1) in self.rock:
            if p == piece and sd == side and s0 <= s <= s1 and off_curb <= NORTH_ROCK_REACH_M:
                self.drops["rock"] += 1
                return True
        return False

    def median_entries(self, field):
        """{zone: [entries]}: the declared trees (scenery.treefx.median_trees) down the middle of a raised PLANTED
        median of a north piece, every one inside the island's outline. (The islands' low planting is the assembler's:
        author_median_blend plants every raised island and export_scatter_blend ships it as median_planting.)"""
        out = {"north_median_trees": []}
        for m in self.medians:
            if not m.get("raised") or m.get("type") not in self.median_tree_types:
                continue
            rows = self.pieces.get(m["piece"]) or []
            poly = [tuple(q) for q in m.get("polygon_xz") or []]
            if not rows or len(poly) < 3:
                continue
            s0, s1 = float(m["s_from"]) + NORTH_MEDIAN_END_CLEAR_M, float(m["s_to"]) - NORTH_MEDIAN_END_CLEAR_M
            mid = int((s0 + s1) * 10)

            def at(s, across):
                """(x, z) on the median at station s (interpolated between the intermediate's rows), `across` in
                [-1, 1] of its half width inside the inset"""
                i = min(range(len(rows) - 1), key=lambda k: abs(float(rows[k]["s"]) - s))
                if float(rows[i]["s"]) > s and i > 0:
                    i -= 1
                a, b = rows[i], rows[i + 1]
                sa, sb = float(a["s"]), float(b["s"])
                t = 0.0 if sb <= sa else max(0.0, min(1.0, (s - sa) / (sb - sa)))

                def lerp(k):
                    return float(a.get(k) or 0.0) * (1 - t) + float(b.get(k) or 0.0) * t
                tx, tz = b["x"] - a["x"], b["z"] - a["z"]
                L = math.hypot(tx, tz) or 1.0
                nx_, nz_ = -tz / L, tx / L
                w = lerp("median_w_m")
                off = lerp("median_off_m") + across * max(0.0, w / 2 - NORTH_MEDIAN_INSET_M)
                return lerp("x") + nx_ * off, lerp("z") + nz_ * off, w

            def seat(x, z):
                off, ry, _ = field.query(x, z, reach=1)
                return ry + 0.15 if off != float("inf") else 0.0

            for rule in self.median_trees:
                if rule.get("piece") != m["piece"]:
                    continue
                t0, t1 = max(s0, float(rule["s"][0])), min(s1, float(rule["s"][1]))
                s = t0
                n = 0
                while s <= t1:
                    x, z, w = at(s, 0.0)
                    if w >= NORTH_MEDIAN_TREE_MIN_W_M and _in_poly(poly, x, z) and _edge_dist(poly, x, z) >= NORTH_MEDIAN_INSET_M:
                        out.setdefault(rule.get("zone", "north_median_trees"), []).append(
                            {"x": x, "y": seat(x, z), "z": z, "_k": mid * 7927 + n, "_piece": m["piece"]})
                    s += NORTH_MEDIAN_TREE_STEP_M
                    n += 1
        return out


class BuiltSurfaces:
    """The gate OBJ's roads, walks, rock cut faces and buildings as plan triangles (engine frame x, z), bucketed, for
    the built-surface guard. ``reject(x, z)`` -> the kind standing under the spot (rock / road / walk / building) or
    None. A building counts from BUILT_BUILDING_CLEAR_M away (the spot and eight ring samples)."""

    def __init__(self, obj_path):
        self.cells = {}
        self.counts = {k: 0 for _p, k in BUILT_SURFACE_KINDS}
        V = []
        kind = None
        with open(obj_path, encoding="utf-8", errors="replace") as f:
            for ln in f:
                c = ln[:2]
                if c == "v ":
                    p = ln.split()
                    V.append((float(p[1]), float(p[3])))
                elif c in ("o ", "g "):
                    nm = ln[2:].strip().upper()
                    kind = next((k for pfx, k in BUILT_SURFACE_KINDS if nm.startswith(pfx)), None)
                elif c == "f " and kind is not None:
                    idx = [int(q.split("/")[0]) - 1 for q in ln.split()[1:]]
                    for i in range(1, len(idx) - 1):          # fan: every face, triangles and quads alike
                        a, b, cc = V[idx[0]], V[idx[i]], V[idx[i + 1]]
                        if abs((b[0] - a[0]) * (cc[1] - a[1]) - (cc[0] - a[0]) * (b[1] - a[1])) < 1e-6:
                            continue                           # a wall: no plan area
                        self._add(kind, a, b, cc)
                        self.counts[kind] += 1

    def _add(self, kind, a, b, c):
        xs, zs = (a[0], b[0], c[0]), (a[1], b[1], c[1])
        for ix in range(int(min(xs) // BUILT_CELL_M), int(max(xs) // BUILT_CELL_M) + 1):
            for iz in range(int(min(zs) // BUILT_CELL_M), int(max(zs) // BUILT_CELL_M) + 1):
                self.cells.setdefault((ix, iz), []).append((kind, a, b, c))

    @staticmethod
    def _inside(p, a, b, c):
        d1 = (b[0] - a[0]) * (p[1] - a[1]) - (p[0] - a[0]) * (b[1] - a[1])
        d2 = (c[0] - b[0]) * (p[1] - b[1]) - (p[0] - b[0]) * (c[1] - b[1])
        d3 = (a[0] - c[0]) * (p[1] - c[1]) - (p[0] - c[0]) * (a[1] - c[1])
        return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))

    def kinds_at(self, x, z):
        out = set()
        for kind, a, b, c in self.cells.get((int(x // BUILT_CELL_M), int(z // BUILT_CELL_M)), ()):
            if kind not in out and self._inside((x, z), a, b, c):
                out.add(kind)
        return out

    def reject(self, x, z):
        k = self.kinds_at(x, z)
        for want in ("building", "rock", "road", "walk"):
            if want in k:
                return want
        r = BUILT_BUILDING_CLEAR_M
        for i in range(8):
            ang = i * math.pi / 4
            if "building" in self.kinds_at(x + r * math.cos(ang), z + r * math.sin(ang)):
                return "building"
        return None


def _pick(species, i):
    wsum = sum(s[3] for s in species)
    r = _hash(i, 1) * wsum
    acc = 0.0
    for s in species:
        acc += s[3]
        if r <= acc:
            return s
    return species[-1]


def plan(project_dir, all_species=False, verbose=False):
    """Every TreeFX placement build() writes, computed WITHOUT writing anything: {lines, entries, counts, used,
    rejected}. entries = [{zone, model, x, y, z}] in the ENGINE frame (x = E, y = up, z = N; trees.txt carries
    x, y, -z). all_species=True plans as if every species of every zone were in source/trees/ — positions only:
    tools/verify_race.py G checks them against the race lanes and walls before the models are copied (a missing
    .bin changes which model a position gets, or drops a whole zone, never moves a position)."""
    proj = Path(project_dir)
    data = proj / "data"
    sp_ = data / "scatter_positions.json"
    pos = json.loads(sp_.read_text(encoding="utf-8")) if sp_.exists() else {}
    # W1-6 signs (tools/place_signs.py): a plant inside 2.5 m of a sign post is dropped here, the sign never moves
    sp = data / "signs.local.json"
    excluded = {(e["zone"], e["index"]) for e in (json.loads(sp.read_text(encoding="utf-8")).get("exclude_plants", []) if sp.exists() else [])}
    src = proj / "source" / "trees"
    available = {p.name for p in src.glob("*.bin")}
    if all_species:
        available = {s[0] for zone in ZONES.values() for s in zone}

    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    lines = [([tuple(p) for p in local["points_xyz_m"]], [w / 2.0 for w in local["widths_m"]])]
    cp = data / "connectors.local.json"
    if cp.exists():
        for c in json.loads(cp.read_text(encoding="utf-8")).get("connectors", []):
            lines.append(([tuple(p) for p in c["points_xyz_m"]], [w / 2.0 for w in c["widths_m"]]))
    field = RoadField(lines, cell=60.0)
    # ledger 0054 P4 (A9): the north network's planting rules, opt-in by track.config.json scenery.treefx; the files it
    # names must exist (a declared zoning with no bins / no intermediate is an error, never a silent bare network)
    north = None
    cfg_p = proj / "track.config.json"
    tcfg = ((json.loads(cfg_p.read_text(encoding="utf-8")).get("scenery") or {}).get("treefx") or {}) if cfg_p.exists() else {}
    if tcfg.get("veg_bins"):
        for f in (tcfg["veg_bins"], tcfg.get("pieces", "data/expansion.north.json")):
            if not (proj / f).exists():
                raise SystemExit(f"[treefx] scenery.treefx names {f}, which {proj} lacks (the ship chain syncs it in)")
        north = North(proj, tcfg)
    # ledger 0054 P1 fix round (opt-in: data/aprons.json, tools/author_aprons_blend.py): a corner apron is pavement the
    # connector centrelines above do not describe — nothing planted on it or within APRON_PLANT_CLEAR_M of its outline
    apron_polys = []
    app = data / "aprons.json"
    if app.exists():
        apron_polys = [[tuple(q) for q in a["outline_xz"]] for a in json.loads(app.read_text(encoding="utf-8")).get("aprons", [])]

    def on_apron(x, z):
        for poly in apron_polys:
            inside = False
            for i in range(len(poly)):
                a, b = poly[i], poly[(i + 1) % len(poly)]
                if (a[1] > z) != (b[1] > z) and x < a[0] + (z - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
                    inside = not inside
            if inside:
                return True
            for i in range(len(poly)):
                a, b = poly[i], poly[(i + 1) % len(poly)]
                dx, dz = b[0] - a[0], b[1] - a[1]
                L2 = dx * dx + dz * dz
                t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / L2))
                if math.hypot(x - (a[0] + t * dx), z - (a[1] + t * dz)) < APRON_PLANT_CLEAR_M:
                    return True
        return False
    # the I-8's own carriageways (tools/freeway_i8.py, ledger 0046 v0.18.0 integration fix round): visual pavement, but
    # a tree standing on a freeway lane is as wrong as one on the loop's — the same guard, a field of its own (the fill
    # bands and the basin rule above stay measured from the LOOP's roads)
    fwy = None
    fp = data / "freeway_i8.json"
    if fp.exists():
        flines = []
        for ch in json.loads(fp.read_text(encoding="utf-8")).get("chains", []):
            run = []
            for st in ch + [None]:
                if st is None:
                    if len(run) >= 2:
                        flines.append(([(r["x"], 0.0, r["z"]) for r in run], [max(r["wl"], r["wr"]) for r in run]))
                    run = []
                else:
                    run.append(st)
        fwy = RoadField(flines, cell=60.0) if flines else None

    # the built-surface guard (ledger 0054 P4 integration fix round): the gate OBJ, when the chain has exported it
    # (verify_race G judges the plan before Blender, without it — the written file is re-judged after it, with it)
    built = None
    rejected_built = {"rock": 0, "road": 0, "walk": 0, "building": 0}
    rejected_built_loop = dict(rejected_built)
    obj_p = data / "track.obj"
    if obj_p.exists():
        built = BuiltSurfaces(obj_p)
        if verbose:
            print(f"[treefx] built-surface guard on {obj_p.name}: plan triangles " +
                  ", ".join(f"{k} {n}" for k, n in built.counts.items()))

    out = []
    entries_out = []
    used = set()
    counts = {}
    rejected = 0
    # ledger 0082 (Milford's vegetation pass, opt-in): scenery.treefx.planted.native_h_m {model: its height at size 1, m}
    # sizes a planted point by its MEASURED height (size = h_m / native) instead of its rank between the file's shortest
    # and tallest; a model it does not name keeps the rank rule. Absent (every other track) = nothing changes
    native_h = {k: float(v) for k, v in ((tcfg.get("planted") or {}).get("native_h_m") or {}).items() if not k.startswith("_")}
    # ... and planted.native_w_m {model: its crown width at size 1, m} (opt-in, beside native_h_m) writes `width = crown_m /
    # (native width * size)`: TreeFX's width-only multiplier, so a tree keeps its MEASURED crown at its measured height (a
    # uniform size alone scales the crown with the height). A model it does not name gets no width
    native_w = {k: float(v) for k, v in ((tcfg.get("planted") or {}).get("native_w_m") or {}).items() if not k.startswith("_")}

    def emit_zone(zone_key, entries, idx_base=0, guard=True):
        species = [s for s in ZONES[zone_key] if s[0] in available]
        if not entries or not species:
            return 0
        out.append(f"configure: seed = {20261008 + len(zone_key)}")
        out.append("configure: size variance = 1, 1")
        out.append("configure: angle variance = 0, 360")
        n = 0
        nonlocal rejected
        for i, e in enumerate(entries, start=idx_base):
            if (zone_key, i - idx_base) in excluded:
                continue
            # every guard judges the spot AS WRITTEN: trees.txt carries centimetres, and a plan spot a few millimetres
            # clear of a guard's edge (the building ring at exactly BUILT_BUILDING_CLEAR_M) lands inside it once rounded
            # (ledger 0054 P4 integration fix round, run 2: one loop Sage at (-1358.81, -1172.46) survived the guard that way)
            e["x"], e["y"], e["z"] = round(e["x"], 2), round(e["y"], 2), round(e["z"], 2)
            if guard and (field.query(e["x"], e["z"])[0] < 1.0
                          or (fwy is not None and fwy.query(e["x"], e["z"])[0] < 1.0)):
                rejected += 1
                continue
            if apron_polys and on_apron(e["x"], e["z"]):
                rejected += 1
                continue
            if guard and built is not None:
                why = built.reject(e["x"], e["z"])
                if why:
                    rejected_built[why] += 1
                    if not zone_key.startswith("north_"):
                        rejected_built_loop[why] += 1
                    continue
            hk = idx_base + e["_key"] if "_key" in e else i   # a planted point's own key (opt-in, above), else its place
            s = _pick(species, hk)
            size = s[1] + (s[2] - s[1]) * e.get("_size01", _hash(hk, 2))
            if "_h" in e and s[0] in native_h:   # ledger 0082 (opt-in planted.native_h_m): the measured height, absolute
                size = e["_h"] / native_h[s[0]]
            angle = int(360 * _hash(hk, 3))
            line = f"tree: {s[0]}; pos={e['x']:.2f}, {e['y']:.2f}, {-e['z']:.2f}; angle = {angle}; size = {size:.2f}"
            if "_w" in e and s[0] in native_w:   # ledger 0082 (opt-in planted.native_w_m): the measured crown, absolute
                line += f"; width = {e['_w'] / (native_w[s[0]] * round(size, 2)):.2f}"
            out.append(line)
            entries_out.append({"zone": zone_key, "model": s[0], "x": e["x"], "y": e["y"], "z": e["z"]})
            used.add(s[0])
            n += 1
        counts[zone_key] = n
        return n

    for zone in ("palms", "trees", "scrub", "median_planting"):
        emit_zone(zone, pos.get(zone, []), guard=(zone != "median_planting"))

    # PLANTED (ledger 0063): the track's own points replace the scatter and the fill. Points are [lon, lat, cell, h, w]
    # (tools/plan_bespoke_vegetation.py); y is only where the snap starts: TreeFX seats each tree on SURFACE_MATERIALS
    planted = tcfg.get("planted")
    hf, meta_p = data / "heightfield.npy", data / "heightfield.meta.json"
    if planted:
        d = json.loads((proj / planted["file"]).read_text(encoding="utf-8"))
        o = local["origin"]
        m_lon, m_lat = _mpd(o["lat"])
        clear = float(planted.get("clear_m", 5.0))
        hs = [p[3] for p in d["points"]]
        h0, h1 = min(hs), max(hs)
        by_zone, too_near = {}, 0
        grid, ny, nx = _read_npy(hf)
        s_, w_, n_, e_ = json.loads(meta_p.read_text(encoding="utf-8"))["bbox_swne"]

        def ground_y(lon, lat):
            j = min(ny - 1, max(0, round((n_ - lat) / (n_ - s_) * (ny - 1))))
            i = min(nx - 1, max(0, round((lon - w_) / (e_ - w_) * (nx - 1))))
            return float(grid[j][i]) - o["elev_m"]
        # ledger 0082 / 0087, Milford 0.1.5 (opt-in by the point's shape): a 6th element is the point's KEY, the index its
        # model / angle hashes use instead of its place in the file, so a re-segmented crown file keeps every untouched
        # tree's model and angle (a removed or added point no longer renumbers every tree after it). Absent = the place
        for pt in d["points"]:
            lon, lat, cell, h, _w = pt[:5]
            x, z = (lon - o["lon"]) * m_lon, (lat - o["lat"]) * m_lat
            if field.query(x, z)[0] < clear:
                too_near += 1
                continue
            by_zone.setdefault(planted["zones"][str(cell)], []).append(
                {"x": x, "y": ground_y(lon, lat), "z": z, "_size01": (h - h0) / max(h1 - h0, 1e-6),
                 **({"_h": float(h)} if native_h else {}), **({"_w": float(_w)} if native_w else {}),
                 **({"_key": int(pt[5])} if len(pt) > 5 else {})})
        for k, zone in enumerate(sorted(by_zone)):
            emit_zone(zone, by_zone[zone], idx_base=k * 100000)
        rejected += too_near
        if verbose:
            print(f"[treefx] planted {planted['file']}: {sum(len(v) for v in by_zone.values())} of {len(d['points'])} points "
                  f"clear of the roads by {clear} m -> {counts}")

    # density fill over the terrain grid
    north_stats = None
    if hf.exists() and meta_p.exists() and not planted:
        grid, ny, nx = _read_npy(hf)
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        s_, w_, n_, e_ = meta["bbox_swne"]
        sp = meta["spacing_m"]
        midlat = (s_ + n_) / 2
        gy, gx = sp / 111_000.0, sp / (111_000.0 * math.cos(math.radians(midlat)))
        o = local["origin"]
        m_lon, m_lat = _mpd(o["lat"])
        elev0 = o["elev_m"]

        def grid_xyz(j, i):
            lat = n_ - j * gy
            return ((w_ + i * gx - o["lon"]) * m_lon, grid[j][i] - elev0, (lat - o["lat"]) * m_lat)

        sub = int(sp // FILL_STEP_M)
        fill = {z: [] for z in ("fill_yard_trees", "fill_yard_bushes", "fill_slope_trees", "fill_slope_bushes")}
        n_tree = n_bush = 0
        # a grid grown by whole cells (heightfield grid_grow, ledger 0054 P2) fills the loop's OWN cells only, numbered
        # exactly as the ungrown grid numbered them: every hash - jitter, pick, thinning - and the candidate count the
        # caps thin by are the ones they always were, so the loop's trees do not move. The added cells get their planting
        # with the north roads (EXPANSION-PLAN P4 / A9: zones, caps scaled by area). No grid_grow: today's loop, bit for bit.
        gg = meta.get("grid_grow") or {}
        rn, cw = int(gg.get("rows_n", 0)), int(gg.get("cols_w", 0))
        ny0, nx0 = ny - rn - int(gg.get("rows_s", 0)), nx - cw - int(gg.get("cols_e", 0))
        # the ADDED cells (ledger 0054 P4 / A9): zoned by the north pieces, their rate from the aerial bins; an added
        # cell beside no north piece (the 150-200 m ring the growth added around the loop's own roads) follows the
        # loop's own bands with its suburb mixes. Separate lists, separate keys: the loop's thinning never sees them.
        nfill = {z: [] for z in NORTH_ZONE_ORDER if not z.startswith("north_median")}
        n_cells_loop = n_cells_north = 0        # in-band sub-cells = the planted AREA each side of the caps
        north_piece_cells = {}
        for j in range(ny - 1):
            for i in range(nx - 1):
                jb, ib = j - rn, i - cw
                added = not (0 <= jb < ny0 - 1 and 0 <= ib < nx0 - 1)
                if added and north is None:
                    continue
                cell_no = (NORTH_CELL_BASE + j * (nx - 1) + i) if added else (jb * (nx0 - 1) + ib)
                p00, p10, p01, p11 = grid_xyz(j, i), grid_xyz(j, i + 1), grid_xyz(j + 1, i), grid_xyz(j + 1, i + 1)
                for a in range(sub):
                    for b in range(sub):
                        k = cell_no * sub * sub + a * sub + b + 1
                        u = (a + 0.2 + 0.6 * _hash(k, 5)) / sub
                        v = (b + 0.2 + 0.6 * _hash(k, 6)) / sub
                        x = p00[0] + (p10[0] - p00[0]) * u + (p01[0] - p00[0]) * v
                        z = p00[2] + (p10[2] - p00[2]) * u + (p01[2] - p00[2]) * v
                        y = ((p00[1] * (1 - u) + p10[1] * u) * (1 - v) + (p01[1] * (1 - u) + p11[1] * u) * v)
                        off, road_y, _ = field.query(x, z, reach=2)
                        if off == float("inf") or off < FILL_BANDS[0][0] or off > FILL_BANDS[-1][1]:
                            continue
                        if added:
                            loc = north.locate(x, z)
                            if north.on_pad(x, z):
                                continue
                            if loc is None:
                                if road_y - y > LAKE_DROP_M:
                                    continue
                                for (lo, hi, _tz, pt, _bz, pb) in FILL_BANDS:
                                    if lo <= off < hi:
                                        break
                                tz, bz = "north_suburb_trees", "north_suburb_bushes"
                                piece = "ring"
                            else:
                                piece, s, side, off_curb = loc
                                zn = north.zone(piece, side, s)
                                if zn is None or north.on_rock(piece, side, s, off_curb):
                                    continue
                                tz, bz = zn
                                fc, fs = north.shares(piece, side, s)
                                f = NORTH_FAR_FACTOR if off >= NORTH_FAR_FROM_M else 1.0
                                pt = min(NORTH_P_TREE_MAX, NORTH_TREE_PER_CANOPY * fc) * f
                                pb = min(NORTH_P_SUM_MAX - pt / f, NORTH_BUSH_PER_SCRUB * fs + (NORTH_BUSH_FLOOR if fc > 0 else 0.0)) * f
                            n_cells_north += 1
                            r = _hash(k, 7)
                            if r < pt:
                                nfill[tz].append({"x": x, "y": y, "z": z, "_k": k, "_piece": piece})
                            elif r < pt + pb:
                                nfill[bz].append({"x": x, "y": y, "z": z, "_k": k, "_piece": piece})
                            continue
                        if road_y - y > LAKE_DROP_M:
                            continue                       # the reservoir basin / deep cut
                        n_cells_loop += 1
                        for (lo, hi, tz, pt, bz, pb) in FILL_BANDS:
                            if lo <= off < hi:
                                r = _hash(k, 7)
                                if r < pt:
                                    fill[tz].append({"x": x, "y": y, "z": z, "_k": k})
                                    n_tree += 1
                                elif r < pt + pb:
                                    fill[bz].append({"x": x, "y": y, "z": z, "_k": k})
                                    n_bush += 1
                                break
        # thin UNIFORMLY to the caps (a running cap stopped the fill mid-grid and left the south bare)
        loop_keep = {}
        for cap, zones in ((CAP_TREES, ("fill_yard_trees", "fill_slope_trees")),
                           (CAP_BUSHES, ("fill_yard_bushes", "fill_slope_bushes"))):
            tot = sum(len(fill[z]) for z in zones)
            loop_keep[zones[0]] = (tot, min(1.0, cap / tot) if tot else 1.0)
            if tot > cap:
                keep = cap / tot
                for z in zones:
                    fill[z] = [e for e in fill[z] if _hash(e["_k"], 9) < keep]
        n_tree = sum(len(fill[z]) for z in ("fill_yard_trees", "fill_slope_trees"))
        n_bush = sum(len(fill[z]) for z in ("fill_yard_bushes", "fill_slope_bushes"))
        base = 100000
        for zone, entries in fill.items():
            emit_zone(zone, entries, idx_base=base)
            base += 100000
        cell_m2 = (sp / sub) ** 2
        area_loop, area_north = n_cells_loop * cell_m2, n_cells_north * cell_m2
        if verbose:
            print(f"[treefx] fill: {n_tree} trees + {n_bush} bushes from the terrain grid ({sub}x{sub} sub-cells per {sp:.0f} m)")
            print(f"[treefx] loop planted area {area_loop / 1e4:.1f} ha ({n_cells_loop} in-band sub-cells): candidates "
                  f"{loop_keep['fill_yard_trees'][0]} trees / {loop_keep['fill_yard_bushes'][0]} bushes, caps {CAP_TREES} / {CAP_BUSHES} "
                  f"(kept {loop_keep['fill_yard_trees'][1]:.3f} / {loop_keep['fill_yard_bushes'][1]:.3f}) -> "
                  f"density {n_tree / max(area_loop, 1) * 1e4:.2f} trees/ha, {n_bush / max(area_loop, 1) * 1e4:.2f} bushes/ha")
        if north is not None:
            # the caps scale with planted AREA (EXPANSION-PLAN A9 / Risk 14): the north's cap is the loop's density x the
            # north's own in-band area, never a share of the loop's caps (that would thin the loop's verges)
            tzs = tuple(z for z in nfill if "tree" in z or z == "north_gum_belt")
            bzs = tuple(z for z in nfill if z not in tzs)
            north_stats = {"area_loop_m2": round(area_loop), "area_north_m2": round(area_north),
                           "loop_density_per_ha": {"trees": round(n_tree / max(area_loop, 1) * 1e4, 3),
                                                   "bushes": round(n_bush / max(area_loop, 1) * 1e4, 3)},
                           "caps": {}, "aerial_implied": {}, "kept": {}, "drops": None, "per_piece": {}}
            cap_scale = float(north.cfg.get("cap_scale", 1.0))     # Kevin's lever after Drive 2: 1.0 = the loop's density
            north_stats["cap_scale"] = cap_scale
            for name, cap, zones in (("trees", CAP_TREES, tzs), ("bushes", CAP_BUSHES, bzs)):
                ncap = int(round(cap * cap_scale * area_north / area_loop)) if area_loop else 0
                tot = sum(len(nfill[z]) for z in zones)
                north_stats["aerial_implied"][name] = tot
                north_stats["caps"][name] = ncap
                if tot > ncap:
                    keep = ncap / tot
                    for z in zones:
                        nfill[z] = [e for e in nfill[z] if _hash(e["_k"], 9) < keep]
                north_stats["kept"][name] = sum(len(nfill[z]) for z in zones)
            for zone, entries in north.median_entries(field).items():
                nfill.setdefault(zone, []).extend(entries)
            base = NORTH_IDX_BASE
            before = len(entries_out)
            for zone in NORTH_ZONE_ORDER:
                emit_zone(zone, nfill.get(zone, []), idx_base=base, guard=not zone.startswith("north_median"))
                base += 100000
            # per piece, per species: what the north got (the report Kevin reads)
            placed = entries_out[before:]
            src_by_zone = {z: [e for e in nfill.get(z, [])] for z in NORTH_ZONE_ORDER}
            for zone in NORTH_ZONE_ORDER:
                kept_xy = {(round(e["x"], 2), round(e["z"], 2)): e.get("_piece", "?") for e in src_by_zone[zone]}
                for e in placed:
                    if e["zone"] != zone:
                        continue
                    pc = kept_xy.get((round(e["x"], 2), round(e["z"], 2)), "?")
                    d = north_stats["per_piece"].setdefault(pc, {})
                    d[e["model"]] = d.get(e["model"], 0) + 1
            north_stats["drops"] = dict(north.drops)
            north_stats["per_piece_total"] = {p: sum(v.values()) for p, v in north_stats["per_piece"].items()}
            if verbose:
                print(f"[treefx] north (ledger 0054 P4 / A9): planted area {area_north / 1e4:.1f} ha ({n_cells_north} sub-cells); "
                      f"the aerial bins imply {north_stats['aerial_implied']['trees']} trees / {north_stats['aerial_implied']['bushes']} bushes; "
                      f"caps at the loop's density {north_stats['caps']['trees']} / {north_stats['caps']['bushes']}; "
                      f"kept {north_stats['kept']['trees']} / {north_stats['kept']['bushes']}; "
                      f"median trees {len(nfill.get('north_median_trees', []))}; "
                      f"dropped on a pad {north.drops['pad']}, on a rock face {north.drops['rock']}")
                for pc in sorted(north_stats["per_piece"]):
                    print(f"[treefx]   piece {pc}: {north_stats['per_piece_total'][pc]} -> "
                          + ", ".join(f"{m} {n}" for m, n in sorted(north_stats["per_piece"][pc].items())))
    if verbose and built is not None:
        print(f"[treefx] built-surface guard: dropped " + ", ".join(f"{k} {n}" for k, n in rejected_built.items())
              + " (of them on the loop's own zones: " + ", ".join(f"{k} {n}" for k, n in rejected_built_loop.items()) + ")")
    return {"lines": out, "entries": entries_out, "counts": counts, "used": used, "rejected": rejected,
            "rejected_built": rejected_built, "rejected_built_loop": rejected_built_loop, "north": north_stats}


def build(project_dir):
    proj = Path(project_dir)
    slug = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))["slug"]
    src = proj / "source" / "trees"
    p = plan(proj, verbose=True)
    out, used, counts, rejected = p["lines"], p["used"], p["counts"], p["rejected"]
    total = sum(counts.values())
    build = proj / "build" / slug
    tdir = build / "extension" / "trees"
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / "trees.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    for name in sorted(used):
        shutil.copy2(src / name, tdir / name)
    ini_path = build / "extension" / "ext_config.ini"
    ini = ini_path.read_text(encoding="utf-8") if ini_path.exists() else ""
    if MARK_BEGIN in ini:
        ini = ini[:ini.index(MARK_BEGIN)] + ini[ini.index(MARK_END) + len(MARK_END):]
    block = (f"\n{MARK_BEGIN}\n[TREES]\nLIST_0 = trees/trees.txt\nSURFACE_MATERIALS = {surface_materials(proj)}\n"
             f"; {total} trees, {len(used)} species, personal-use TreeFX models — never redistribute\n{MARK_END}\n")
    ini_path.write_text(ini.rstrip() + "\n" + block, encoding="utf-8")
    print(f"[treefx] {total} trees ({counts}), {rejected} rejected in the corridor, "
          f"species {sorted(used)} -> {tdir / 'trees.txt'} + [TREES] in ext_config.ini")
    # the record of what was planted (ledger 0054 P4): per zone, and the north network per piece per species
    by_model = {}
    for e in p["entries"]:
        by_model[e["model"]] = by_model.get(e["model"], 0) + 1
    rep = {"_doc": "tools/make_treefx.py: what trees.txt holds (counts per zone and per species; the north network per "
                   "piece per species, its planted area, the loop's density and the area-scaled caps — ledger 0054 P4 / A9)",
           "total": total, "per_zone": counts, "per_species": dict(sorted(by_model.items())), "rejected_in_corridor": rejected,
           "rejected_on_built_surface": p["rejected_built"], "rejected_on_built_surface_loop_zones": p["rejected_built_loop"],
           "surface_materials": surface_materials(proj), "north": p["north"]}
    (proj / "data" / "treefx.report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/make_treefx.py <project-dir>")
    build(sys.argv[1])
