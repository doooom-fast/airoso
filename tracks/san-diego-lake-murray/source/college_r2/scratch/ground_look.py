"""What scripts/ac/kn5_ground_check.py and verify_kn5 check 6 read on a project's road kn5, WITH THE PLACES: no Blender.

    python ground_look.py <airoso> <project> [--out <json>]

  double sheets   every 2 m cell whose ground heights are more than 12 m apart (the gate's own reader, cell and trim),
                  with the mesh that gives the cell its lowest and its highest vertex;
  road over ground  the gate's own pass, run from its own source with one line added so every sample keeps its place;
                  the samples over the gate's gap, and those at College's split placed across the two roads (row, offset,
                  which edge);
  pokes           verify_kn5's check 6 alone (its code, copied and guarded): a scratch workshop has no race or spawn
                  kn5s for the whole of verify_kn5 to run on.

Made after Lake Murray 0.20.5's first rehearsal (2026-11-23, kn5_ground_check: 202 double-sheet cells; the log names
four). Reads only."""
import json
import math
import sys
import types
from collections import defaultdict
from pathlib import Path

args = sys.argv[1:]
OUT = None
if "--out" in args:
    OUT = Path(args[args.index("--out") + 1])
    del args[args.index("--out"):args.index("--out") + 2]
root, proj = Path(args[0]), Path(args[1])
sys.path.insert(0, str(root))
from scripts.ac import kn5_ground_check as K  # noqa: E402
from scripts.ac import verify_kn5 as V  # noqa: E402

cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
kn5p = proj / "build" / (cfg["slug"] + ".kn5")
_nodes, meshes = K._parse(kn5p)
rep = {"kn5": str(kn5p), "version": cfg.get("version")}

# ------------------------------------------------------------------------------------------------- double sheets
g = [(p[0], p[1], p[2], m["name"]) for m in meshes if K._bucket(m["name"]) == "1GRASS" for p in m["P"]]
xs = [p[0] for p in g]
zs = [p[2] for p in g]
bx0, bx1, bz0, bz1 = min(xs), max(xs), min(zs), max(zs)
cells = {}
for x, y, z, n in g:
    if x - bx0 < 520 or bx1 - x < 520 or z - bz0 < 520 or bz1 - z < 520:
        continue                                             # the gate's own border ring
    c = cells.setdefault((int(x // 2), int(z // 2)), [1e18, None, -1e18, None])
    if y < c[0]:
        c[0], c[1] = y, (round(x, 2), round(z, 2), n)
    if y > c[2]:
        c[2], c[3] = y, (round(x, 2), round(z, 2), n)
two = sorted(((k, v) for k, v in cells.items() if v[2] - v[0] > 12.0), key=lambda r: -(r[1][2] - r[1][0]))
rep["double_sheet_cells"] = len(two)
rep["double_sheets"] = [{"cell": [k[0] * 2, k[1] * 2], "spread_m": round(v[2] - v[0], 2), "low": [round(v[0], 2), *v[1]],
                         "high": [round(v[2], 2), *v[3]]} for k, v in two]
print(f"[look] {kn5p.name} ({cfg.get('version')}): ground vertices {len(g)}; double-sheet cells {len(two)} (the gate fails over 20)")
for k, v in two[:4]:
    print(f"[look]    spread {v[2] - v[0]:5.1f} m at ({k[0] * 2}, {k[1] * 2}): low {v[0]:.2f} {v[1][2]}, high {v[2]:.2f} {v[3][2]}")

# ---------------------------------------------------------------------------------------------- road over ground
src = (root / "scripts" / "ac" / "kn5_ground_check.py").read_text(encoding="utf-8")
line = "        gaps_c.append(y - g9)\n"
if src.count(line) != 1:
    raise SystemExit("scripts/ac/kn5_ground_check.py: the road-over-ground pass has changed; this file copies one line of it")
mod = types.ModuleType("kn5_ground_check_with_places")
mod.__file__ = str(root / "scripts" / "ac" / "kn5_ground_check.py")
mod._DUMP = []
exec(compile(src.replace(line, line + "        _DUMP.append((x, z, y, g9))\n"), mod.__file__, "exec"), mod.__dict__)
_print, stats = print, {}
mod.print = lambda *a, **k: None                              # the gate's own lines are the gate's; this prints places
mod.check(proj, stats=stats)
over = sorted(((x, z, y, g9) for x, z, y, g9 in mod._DUMP if y - g9 > mod.ROAD_GAP_M), key=lambda r: -(r[2] - r[3]))
rep["road_over_ground"] = {"samples": len(mod._DUMP), "over_gap": len(over), "gap_m": mod.ROAD_GAP_M,
                           "max_m": round(over[0][2] - over[0][3], 3) if over else 0.0, "gate": stats.get("road_over_ground")}
rep["road_over_ground_samples"] = [[round(x, 2), round(z, 2), round(y - g9, 3)] for x, z, y, g9 in over]
print(f"[look] road over ground: {len(over)} of {len(mod._DUMP)} samples over {mod.ROAD_GAP_M} m, the worst {rep['road_over_ground']['max_m']} m")
split = Path(__file__).resolve().parent.parent / "college_split.data.json"
if split.exists():
    S = json.loads(split.read_text(encoding="utf-8"))
    R, F = S["rows"], S["frame"]
    row_k = {v: k for k, v in enumerate(R["v"])}
    placed = []
    for x, kz, y, g9 in over:
        z = -kz                                               # the data's z is the kn5's, mirrored
        i = min(range(len(F["x"])), key=lambda j: (F["x"][j] - x) ** 2 + (F["z"][j] - z) ** 2)
        if math.hypot(F["x"][i] - x, F["z"][i] - z) > 60.0:
            continue
        off = (x - F["x"][i]) * F["nx"][i] + (z - F["z"][i]) * F["nz"][i]
        v = F["from_v"] + i
        edge = None
        if v in row_k:
            for name in ("sb_west", "sb_east", "nb_west", "nb_east"):
                if abs(R["offsets_m"][name][row_k[v]] - off) <= 0.05:
                    edge = name
        placed.append({"row": v, "offset_m": round(off, 2), "on_edge": edge, "gap_m": round(y - g9, 3)})
    placed.sort(key=lambda r: r["row"])
    rep["road_over_ground_at_the_split"] = placed
    by = defaultdict(list)
    for r in placed:
        by[r["on_edge"] or "not on an edge"].append(r["gap_m"])
    print(f"[look]    at College's split: {len(placed)}; by edge (count, worst m): " + ", ".join(f"{k} {len(v)} / {max(v)}" for k, v in sorted(by.items())))

# --------------------------------------------------------------------------------------------------------- pokes
vsrc = (root / "scripts" / "ac" / "verify_kn5.py").read_text(encoding="utf-8")
for frag in ('if not any(_up6.startswith(p) for p in ("1ROAD", "1KERB")) or "SHOULDER" in _up6:', "if abs(ny) / nl < 0.5:",
             "if abs(y - gy) <= 20.0 and (surf is None or y < surf):", "if surf is not None and gy > surf + POKE_ABOVE_M:"):
    if frag not in vsrc:
        raise SystemExit("scripts/ac/verify_kn5.py check 6 has changed; this file copies it: " + frag)
dtris, cell = {}, 8.0
for m in meshes:
    up = m["name"].upper()
    if not any(up.startswith(p) for p in ("1ROAD", "1KERB")) or "SHOULDER" in up:
        continue
    P, idx = m["P"], m["T"]
    for t in range(0, len(idx) - 2, 3):
        a, b, c = P[idx[t]], P[idx[t + 1]], P[idx[t + 2]]
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        if abs(ny) / (math.sqrt(nx * nx + ny * ny + nz * nz) or 1e-12) < 0.5:
            continue
        for ci in range(int(min(a[0], b[0], c[0]) // cell), int(max(a[0], b[0], c[0]) // cell) + 1):
            for cj in range(int(min(a[2], b[2], c[2]) // cell), int(max(a[2], b[2], c[2]) // cell) + 1):
                dtris.setdefault((ci, cj), []).append((a, b, c))
pokes = []
for gx, gy, gz in [p for m in meshes if m["name"].upper().startswith("1GRASS") for p in m["P"]]:
    surf = None
    for a, b, c in dtris.get((int(gx // cell), int(gz // cell)), ()):
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-12:
            continue
        w0 = ((b[2] - c[2]) * (gx - c[0]) + (c[0] - b[0]) * (gz - c[2])) / d
        w1 = ((c[2] - a[2]) * (gx - c[0]) + (a[0] - c[0]) * (gz - c[2])) / d
        if w0 >= -1e-6 and w1 >= -1e-6 and 1.0 - w0 - w1 >= -1e-6:
            y = w0 * a[1] + w1 * b[1] + (1.0 - w0 - w1) * c[1]
            if abs(y - gy) <= 20.0 and (surf is None or y < surf):
                surf = y
    if surf is not None and gy > surf + V.POKE_ABOVE_M:
        pokes.append([round(gx, 1), round(gz, 1), round(gy - surf, 2)])
pokes.sort(key=lambda r: -r[2])
rep["terrain_pokes"] = {"count": len(pokes), "gate_fails_over": V.POKE_MAX, "worst": pokes[:8]}
print(f"[look] terrain pokes (verify_kn5 check 6): {len(pokes)} (the gate fails over {V.POKE_MAX})" + (f", the worst +{pokes[0][2]} m at ({pokes[0][0]}, {pokes[0][1]})" if pokes else ""))
if OUT is not None:
    OUT.write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"[look] wrote {OUT}")
