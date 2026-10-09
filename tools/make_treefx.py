"""Emit CSP TreeFX for the track: real palm / street-tree / scrub models, GPU-instanced, zero kn5 cost.

Positions come from data/scatter_positions.json (tools/export_scatter_blend.py — the draft's own
palm/tree/scrub placement). Species are the .bin models the user dropped into
<project>/source/trees/ (personal-use mod content, gitignored, never committed — docs/TREEFX-FORMAT.md).
Writes build/<slug>/extension/trees/trees.txt (+ copies the .bins beside it) and a [TREES]
block in build/<slug>/extension/ext_config.ini between V3 markers (idempotent). Grammar per
docs/TREEFX-FORMAT.md: `tree: <model>.bin; pos=X, Y, Z; angle = deg; size = mult`, positions in
the kn5 world (x, y, -z of the engine frame), trees snap vertically onto SURFACE_MATERIALS.

Corridor guard: TreeFX trees are invisible to drive_test/audit (not in the kn5), so nothing
downstream can catch a tree in the lane — every entry is rejected if it stands within
(half-width + 1 m) of the mainline or any connector centreline.

    python tools/make_treefx.py <project-dir>
"""
from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

SURFACE_MATERIALS = "1GRASS_0_mat, 1GRASS_1_mat, 1ROAD_road_mat"
# species, size multiplier range, weight — palms: nohesi V1 20 m / V2 25 m / V3 28 m native;
# residential San Diego fan palms run 10-20 m, so they are scaled down
ZONES = {
    "palms": {"species": [("PalmV1.bin", 0.65, 0.95, 6), ("PalmV2.bin", 0.55, 0.8, 3), ("PalmV3.bin", 0.5, 0.7, 1)],
              "angle_var": (0, 360)},
    "trees": {"species": [("PepperV1.bin", 0.8, 1.1, 3), ("SycamoreV1.bin", 0.7, 1.0, 2), ("SycamoreV2.bin", 0.7, 1.0, 2),
                          ("Gum.bin", 0.6, 0.9, 2), ("Pine_Aleppo.bin", 0.7, 1.0, 1)], "angle_var": (0, 360)},
    "scrub": {"species": [("Sage.bin", 0.8, 1.2, 4), ("Yucca.bin", 0.7, 1.1, 2), ("Bush.bin", 0.6, 1.0, 2),
                          ("Bush3.bin", 0.5, 0.9, 1), ("Agave.bin", 0.6, 1.0, 1)], "angle_var": (0, 360)},
    "median_planting": {"species": [("Bush.bin", 0.35, 0.6, 3), ("Sage.bin", 0.5, 0.8, 2)], "angle_var": (0, 360)},
}
MARK_BEGIN, MARK_END = "; --- V3 TREEFX BEGIN (tools/make_treefx.py) ---", "; --- V3 TREEFX END ---"


def _hash(i, salt):
    h = (i * 2654435761 + salt * 40503) & 0xFFFFFFFF
    return (h % 10007) / 10007.0


def build(project_dir):
    proj = Path(project_dir)
    data = proj / "data"
    slug = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))["slug"]
    pos = json.loads((data / "scatter_positions.json").read_text(encoding="utf-8"))
    src = proj / "source" / "trees"
    available = {p.name for p in src.glob("*.bin")}

    # corridor guard polylines: (points, half-widths)
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    lines = [([(p[0], p[2]) for p in local["points_xyz_m"]], [w / 2.0 for w in local["widths_m"]])]
    cp = data / "connectors.local.json"
    if cp.exists():
        for c in json.loads(cp.read_text(encoding="utf-8")).get("connectors", []):
            lines.append(([(p[0], p[2]) for p in c["points_xyz_m"]], [w / 2.0 for w in c["widths_m"]]))
    cells = {}
    for li, (pts, halves) in enumerate(lines):
        for i in range(len(pts) - 1):
            for (x, z) in (pts[i], pts[i + 1]):
                cells.setdefault((int(x // 20), int(z // 20)), set()).add((li, i))

    def in_corridor(x, z):
        cx, cz = int(x // 20), int(z // 20)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for (li, i) in cells.get((cx + dx, cz + dz), ()):
                    pts, halves = lines[li]
                    ax, az = pts[i]
                    bx, bz = pts[i + 1]
                    ddx, ddz = bx - ax, bz - az
                    L2 = ddx * ddx + ddz * ddz
                    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * ddx + (z - az) * ddz) / L2))
                    d = math.hypot(x - (ax + t * ddx), z - (az + t * ddz))
                    if d < halves[i] * (1 - t) + halves[min(i + 1, len(halves) - 1)] * t + 1.0:
                        return True
        return False

    # NO comment lines: CSP parses a non-directive first line as a manifest filename —
    # "Failed to load trees: Tree manifest is missing: ...\san_diego_lake_murray — V" (2026-10-08,
    # zero trees rendered). The working packs (nohesi, algarve) carry no comments at all.
    out = []
    used = set()
    rejected = 0
    total = 0
    for zone, spec in ZONES.items():
        entries = pos.get(zone, [])
        species = [s for s in spec["species"] if s[0] in available]
        if not entries or not species:
            print(f"[treefx] zone {zone}: {len(entries)} positions, {len(species)} species available — skipped")
            continue
        wsum = sum(s[3] for s in species)
        out.append(f"configure: seed = {20261008 + len(zone)}")
        out.append("configure: size variance = 1, 1")
        out.append(f"configure: angle variance = {spec['angle_var'][0]}, {spec['angle_var'][1]}")
        n = 0
        for i, e in enumerate(entries):
            if zone != "median_planting" and in_corridor(e["x"], e["z"]):
                rejected += 1
                continue
            r = _hash(i, 1) * wsum
            acc = 0.0
            pick = species[-1]
            for s in species:
                acc += s[3]
                if r <= acc:
                    pick = s
                    break
            size = pick[1] + (pick[2] - pick[1]) * _hash(i, 2)
            angle = int(360 * _hash(i, 3))
            out.append(f"tree: {pick[0]}; pos={e['x']:.2f}, {e['y']:.2f}, {-e['z']:.2f}; angle = {angle}; size = {size:.2f}")
            used.add(pick[0])
            n += 1
        total += n
        print(f"[treefx] zone {zone}: {n} trees from {len(entries)} positions")

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
    block = (f"\n{MARK_BEGIN}\n[TREES]\nLIST_0 = trees/trees.txt\nSURFACE_MATERIALS = {SURFACE_MATERIALS}\n"
             f"; {total} trees, {len(used)} species, personal-use TreeFX models — never redistribute\n{MARK_END}\n")
    ini_path.write_text(ini.rstrip() + "\n" + block, encoding="utf-8")
    print(f"[treefx] {total} trees, {rejected} rejected in the corridor, species {sorted(used)} -> "
          f"{tdir / 'trees.txt'} + [TREES] in ext_config.ini")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/make_treefx.py <project-dir>")
    build(sys.argv[1])
