"""What stands on the paved islands, and did it move? Two built road kn5s compared over the islands
track.config.json route.median_tops.paver lists (ledger 0099 round 3, item 1; reads only).

    python -I props_on_islands.py <airoso> <project before> <project after> [--out <json>]

The prep seats props on 1GRASS / 1ROAD / 1KERB (engine-july build_kn5_loop.py, ground_bvh). A grass top is 1LAWN, so
before this item whatever stood on a Mission Gorge island was seated on the slab under it or on its curb; a paved top
is 1KERB, so the same prop may now stand 0.185 m higher, on the top. This lists, for every mesh that is not ground,
road, kerb or paint, its vertices inside the paved islands' bands (data/median_bands.json, half the band + EDGE_M),
matched between the two builds by plan position (1 mm), and how far each matched vertex moved in height.
kn5 frame: x east, y up, z = minus the data's north."""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

air, pa, pb = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
outp = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
sys.path.insert(0, str(air))
from scripts.ac import kn5_ground_check as K  # noqa: E402

EDGE_M = 0.6                       # scripts/geometry/median_zone.py: the declared island is its band + 0.6 m
SKIP = ("1GRASS", "1ROAD", "1KERB", "1LAWN", "1RUNOFF", "MARKINGS", "YLINE", "ROADTEXT", "GRASS_FAR")
cfg = json.loads((pb / "track.config.json").read_text(encoding="utf-8"))
listed = [(i["line"], i["rows"][0], i["rows"][1]) for i in cfg["route"]["median_tops"]["paver"]["islands"]]
mb = json.loads((pb / "data" / "median_bands.json").read_text(encoding="utf-8"))
rows = []                          # (x, kn5 z, half width + edge)
for line, first, last in listed:
    ci = next(c for c in mb["connector_islands"] if c["name"] == line)
    for r in range(first, last + 1):
        p = ci["points_xyz_m"][r]
        rows.append((p[0], -p[2], 0.5 * ci["island_w_by_point"][r] + EDGE_M))
cell = 8.0
grid = defaultdict(list)
for x, z, h in rows:
    grid[(int(x // cell), int(z // cell))].append((x, z, h))


def on_island(x, z):
    cx, cz = int(x // cell), int(z // cell)
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            for (rx, rz, h) in grid.get((cx + i, cz + j), ()):
                if math.hypot(x - rx, z - rz) <= h:
                    return True
    return False


def inside(proj):
    slug = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))["slug"].replace("-", "_")
    kn5 = proj / "build" / f"{slug}.kn5"
    _nodes, meshes = K._parse(kn5)
    out = defaultdict(dict)
    for m in meshes:
        if m["name"].upper().startswith(SKIP):
            continue
        for p in m["P"]:
            if on_island(p[0], p[2]):
                out[m["name"]].setdefault((round(p[0], 3), round(p[2], 3)), []).append(p[1])
    return kn5, out


ka, A = inside(pa)
kb, B = inside(pb)
rep = {"_doc": "props_on_islands.py: meshes with vertices inside the paved islands' bands (+%.1f m), before and after" % EDGE_M,
       "before": str(ka), "after": str(kb), "islands": listed, "rows": len(rows), "meshes": []}
print(f"paved islands: {listed}, {len(rows)} rows")
for name in sorted(set(A) | set(B)):
    a, b = A.get(name, {}), B.get(name, {})
    both = sorted(set(a) & set(b))
    dy = sorted(min(b[k]) - min(a[k]) for k in both)
    rec = {"mesh": name, "plan_positions_before": len(a), "after": len(b), "matched": len(both),
           "dy_m": None if not dy else {"min": round(dy[0], 4), "median": round(dy[len(dy) // 2], 4), "max": round(dy[-1], 4),
                                        "moved_over_1_mm": sum(1 for d in dy if abs(d) > 0.001)}}
    rep["meshes"].append(rec)
    print("  " + json.dumps(rec))
if not rep["meshes"]:
    print("  nothing but ground, road, kerb and paint stands inside the paved islands' bands")
if outp:
    Path(outp).write_text(json.dumps(rep, indent=1), encoding="utf-8")
