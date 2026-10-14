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
}
FILL_BANDS = [   # (off_min, off_max, tree zone, p_tree, bush zone, p_bush) per 10 m sub-cell
    (6.0, 40.0, "fill_yard_trees", 0.30, "fill_yard_bushes", 0.28),
    (40.0, 120.0, "fill_slope_trees", 0.14, "fill_slope_bushes", 0.50),
    (120.0, 200.0, "fill_slope_trees", 0.06, "fill_slope_bushes", 0.28),
]
FILL_STEP_M = 10.0
LAKE_DROP_M = 8.0
APRON_PLANT_CLEAR_M = 1.0   # [invented] ledger 0054 P1 fix round: no plant within this of a corner apron's outline
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
    pos = json.loads((data / "scatter_positions.json").read_text(encoding="utf-8"))
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

    out = []
    entries_out = []
    used = set()
    counts = {}
    rejected = 0

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
            if guard and (field.query(e["x"], e["z"])[0] < 1.0
                          or (fwy is not None and fwy.query(e["x"], e["z"])[0] < 1.0)):
                rejected += 1
                continue
            if apron_polys and on_apron(e["x"], e["z"]):
                rejected += 1
                continue
            s = _pick(species, i)
            size = s[1] + (s[2] - s[1]) * _hash(i, 2)
            angle = int(360 * _hash(i, 3))
            out.append(f"tree: {s[0]}; pos={e['x']:.2f}, {e['y']:.2f}, {-e['z']:.2f}; angle = {angle}; size = {size:.2f}")
            entries_out.append({"zone": zone_key, "model": s[0], "x": e["x"], "y": e["y"], "z": e["z"]})
            used.add(s[0])
            n += 1
        counts[zone_key] = n
        return n

    for zone in ("palms", "trees", "scrub", "median_planting"):
        emit_zone(zone, pos.get(zone, []), guard=(zone != "median_planting"))

    # density fill over the terrain grid
    hf, meta_p = data / "heightfield.npy", data / "heightfield.meta.json"
    if hf.exists() and meta_p.exists():
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
        k = 0
        for j in range(ny - 1):
            for i in range(nx - 1):
                p00, p10, p01, p11 = grid_xyz(j, i), grid_xyz(j, i + 1), grid_xyz(j + 1, i), grid_xyz(j + 1, i + 1)
                for a in range(sub):
                    for b in range(sub):
                        k += 1
                        u = (a + 0.2 + 0.6 * _hash(k, 5)) / sub
                        v = (b + 0.2 + 0.6 * _hash(k, 6)) / sub
                        x = p00[0] + (p10[0] - p00[0]) * u + (p01[0] - p00[0]) * v
                        z = p00[2] + (p10[2] - p00[2]) * u + (p01[2] - p00[2]) * v
                        y = ((p00[1] * (1 - u) + p10[1] * u) * (1 - v) + (p01[1] * (1 - u) + p11[1] * u) * v)
                        off, road_y, _ = field.query(x, z, reach=2)
                        if off == float("inf") or off < FILL_BANDS[0][0] or off > FILL_BANDS[-1][1]:
                            continue
                        if road_y - y > LAKE_DROP_M:
                            continue                       # the reservoir basin / deep cut
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
        for cap, zones in ((CAP_TREES, ("fill_yard_trees", "fill_slope_trees")),
                           (CAP_BUSHES, ("fill_yard_bushes", "fill_slope_bushes"))):
            tot = sum(len(fill[z]) for z in zones)
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
        if verbose:
            print(f"[treefx] fill: {n_tree} trees + {n_bush} bushes from the terrain grid ({sub}x{sub} sub-cells per {sp:.0f} m)")
    return {"lines": out, "entries": entries_out, "counts": counts, "used": used, "rejected": rejected}


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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/make_treefx.py <project-dir>")
    build(sys.argv[1])
