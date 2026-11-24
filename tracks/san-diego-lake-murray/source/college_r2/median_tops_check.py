"""Do the built medians show their top (grass, or pavers) or asphalt between their curbs? Measured on a BUILT gate OBJ
(read-only).

    <python with numpy> median_tops_check.py <workshop project dir> [--out <json>]

Reads the workshop's data/track.obj (the street layout's kn5 set as one OBJ: scripts/modkit/kn5_to_gate_obj),
data/centerline.local.json and data/median_bands.json. For every row of every island (the mainline's
island_w_by_vertex, each connector island's points) that is at least MIN_W wide, at the island's centre and at a
quarter of its width to each side (where the island tapers to its nose, its last three rows: half the BUILT deck's own
half width, tools/author_median_blend.py's taper; 2026-11-23, before that a nose row's two side points stood outside
the island as built): the highest grass surface and the highest 1ROAD surface straight above / below. Grass = 1GRASS,
and the medians' own top object where a build has one (1LAWN_median: tools/author_median_tops_blend.py). Pavers = the
paved tops' object (1KERB_PAVER...: the same tool, ledger 0099 round 3), read first.

  pavers over the road by OVER_M or more  -> the island's top is paved
  grass over the road by OVER_M or more   -> the island's top is grass
  grass under the road, or no grass       -> the island shows the road's asphalt between its curbs
  no road under the point                 -> no slab under the island there (not this defect)

The median tool (tools/author_median_blend.py) joins the island's grass top into TERRAIN, 0.185 m over the slab; the
prep (engine-july scripts/ac/build_kn5_loop.py _conform_and_reseat) sets every grass vertex that has pavement above
or below it to the deck less 0.02 m. This counts where that happened. Frames: engine x east, y up, z north."""
import json
import math
import sys
from pathlib import Path

import numpy as np

proj = Path(sys.argv[1])
OUT = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None
MIN_W = 1.2          # rows narrower than this are a nose's taper (the tool's top is under 0.8 m wide there)
OVER_M = 0.05        # grass this far over the road is a grass top (the tool's stands 0.185 m over it)

# --- the OBJ: every vertex, the triangles of 1GRASS* and 1ROAD* ------------------------------------------------------------
verts = []
tris = {"1GRASS": [], "1ROAD": [], "1PAVER": []}
names = {"1GRASS": set(), "1ROAD": set(), "1PAVER": set()}
GRASS_NAMES = ("1GRASS", "1LAWN_MEDIAN")
PAVER_NAMES = ("1KERB_PAVER",)   # scripts/ac/pbr.py: the paved tops' own row
NOSE_VERTS, NOSE_HALF, DECK_INSET = 3, 0.25, 0.22      # tools/author_median_blend.py
END_IN = 0.3         # an island's end row is measured this far inside it, along its line (the row is the deck's own edge)
MIN_ISLAND_ROWS = 6  # tools/author_median_blend.py _segments: a run of the band under six rows is not built as an island (no
#                      curb, no top). Its rows are counted apart ("short_run"), never as asphalt between curbs (2026-11-23:
#                      Mission Gorge v54-57 was first read as an island of four asphalt rows; the scene has only paint there)
kind = None
with open(proj / "data" / "track.obj", "r", encoding="utf-8", errors="replace") as fh:
    for line in fh:
        c = line[:2]
        if c == "v ":
            p = line.split()
            verts.append((float(p[1]), float(p[2]), float(p[3])))
        elif c in ("o ", "g "):
            nm = line[2:].strip()
            up = nm.upper()
            kind = "1GRASS" if up.startswith(GRASS_NAMES) else ("1ROAD" if up.startswith("1ROAD") else
                                                                 ("1PAVER" if up.startswith(PAVER_NAMES) else None))
            if kind:
                names[kind].add(nm)
        elif c == "f " and kind:
            ids = [int(t.split("/")[0]) - 1 for t in line.split()[1:]]
            for k in range(1, len(ids) - 1):
                tris[kind].append((ids[0], ids[k], ids[k + 1]))
V = np.array(verts)
T = {k: np.array(v, dtype=np.int64).reshape(-1, 3) for k, v in tris.items()}
print(f"[tops] {len(V)} vertices; 1GRASS {len(T['1GRASS'])} triangles in {len(names['1GRASS'])} objects; 1ROAD {len(T['1ROAD'])} in {len(names['1ROAD'])}; "
      f"paved tops {len(T['1PAVER'])} in {sorted(names['1PAVER'])}")
BOX = {}
for k, t in T.items():
    x, z = V[t][:, :, 0], V[t][:, :, 2]
    BOX[k] = (x.min(axis=1), x.max(axis=1), z.min(axis=1), z.max(axis=1))


def top(kind_, x, z):
    """the highest surface of that kind at (x, z), or None"""
    x0, x1, z0, z1 = BOX[kind_]
    cand = np.nonzero((x0 <= x) & (x1 >= x) & (z0 <= z) & (z1 >= z))[0]
    best = None
    for i in cand:
        a, b, c = V[T[kind_][i]]
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
        l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
        l3 = 1.0 - l1 - l2
        if l1 >= -1e-9 and l2 >= -1e-9 and l3 >= -1e-9:
            y = l1 * a[1] + l2 * b[1] + l3 * c[1]
            best = y if best is None or y > best else best
    return best


cl = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
P = cl["points_xyz_m"]
n = len(P) - 1
S = [0.0]
for k in range(1, len(P)):
    S.append(S[-1] + math.hypot(P[k][0] - P[k - 1][0], P[k][2] - P[k - 1][2]))
mb = json.loads((proj / "data" / "median_bands.json").read_text(encoding="utf-8"))
lines = [("MAINLINE", P, mb["island_w_by_vertex"], S)]
for ci in mb.get("connector_islands") or []:
    pts = ci["points_xyz_m"]
    s = [0.0]
    for k in range(1, len(pts)):
        s.append(s[-1] + math.hypot(pts[k][0] - pts[k - 1][0], pts[k][2] - pts[k - 1][2]))
    lines.append((ci["name"], pts, ci["island_w_by_point"], s))
runs_named = {(r["i"], r["j"]): r["road"] for r in mb.get("runs") or []}
out = []
for name, pts, iw, s in lines:
    m = len(pts)
    k = 0
    while k < m:
        if iw[k] <= 0:
            k += 1
            continue
        j = k
        while j < m and iw[j] > 0:
            j += 1
        rows = {"grass": 0, "paver": 0, "asphalt": 0, "no_slab": 0, "nose": 0, "short_run": 0}
        diffs = []
        is_island = j - k >= MIN_ISLAND_ROWS
        if not is_island:
            rows["short_run"] = j - k
        for r in (range(k, j) if is_island else ()):
            if iw[r] < MIN_W:
                rows["nose"] += 1
                continue
            a, b = pts[max(0, r - 1)], pts[min(m - 1, r + 1)]
            tx, tz = b[0] - a[0], b[2] - a[2]
            L = math.hypot(tx, tz) or 1.0
            nx, nz = -tz / L, tx / L
            votes = []
            half = iw[r] / 2.0
            for si in (r - k, j - 1 - r):
                if si < NOSE_VERTS:
                    half = min(half, NOSE_HALF + (iw[r] / 2.0 - NOSE_HALF) * si / NOSE_VERTS)
            q = min(iw[r] / 4.0, max(0.05, half - DECK_INSET) / 2.0)
            sx = sz = 0.0                      # an island's first and last row is the deck's end edge: END_IN inside it
            if j - k > 1 and r in (k, j - 1):
                o_ = pts[k + 1] if r == k else pts[j - 2]
                L_ = math.hypot(o_[0] - pts[r][0], o_[2] - pts[r][2]) or 1.0
                sx, sz = (o_[0] - pts[r][0]) / L_ * END_IN, (o_[2] - pts[r][2]) / L_ * END_IN
            for o in (0.0, q, -q):
                x, z = pts[r][0] + sx + nx * o, pts[r][2] + sz + nz * o
                yr = top("1ROAD", x, z)
                if yr is None:
                    votes.append("no_slab")
                    continue
                yg = top("1GRASS", x, z)
                yp = top("1PAVER", x, z)
                if yp is not None and yp - yr >= OVER_M:
                    votes.append("paver")
                elif yg is not None and yg - yr >= OVER_M:
                    votes.append("grass")
                else:
                    votes.append("asphalt")
                    if yg is not None:
                        diffs.append(yg - yr)
            v = max(set(votes), key=votes.count)
            rows[v] += 1
        road = next((nm for (i0, j0), nm in runs_named.items() if name == "MAINLINE" and i0 <= k and j - 1 <= j0), None)
        rec = {"line": name, "road": road, "island": is_island, "rows": [k, j - 1], "station_m": [round(s[k], 1), round(s[j - 1], 1)],
               "length_m": round(s[j - 1] - s[k], 1), "width_m": [round(min(iw[k:j]), 2), round(max(iw[k:j]), 2)], **rows,
               "grass_under_the_road_m_median": round(float(np.median(diffs)), 3) if diffs else None}
        out.append(rec)
        print("[tops] " + json.dumps(rec))
        k = j
tot = {key: sum(r[key] for r in out) for key in ("grass", "paver", "asphalt", "no_slab", "nose", "short_run")}
print(f"[tops] {sum(1 for r in out if r['island'])} islands, {sum(1 for r in out if not r['island'])} band runs too short to be one; rows: {tot}")
if OUT:
    OUT.write_text(json.dumps({"what": "built medians: grass, pavers or asphalt between the curbs (median_tops_check.py)", "workshop": str(proj),
                               "params": {"MIN_W": MIN_W, "OVER_M": OVER_M, "_doc": "[invented]"},
                               "totals_rows": tot, "islands": out}, indent=1), encoding="utf-8")
