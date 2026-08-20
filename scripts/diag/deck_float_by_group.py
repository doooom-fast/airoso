"""Measure the connector deck's gap over the GRASS surface in a built track.obj.

Mirrors kn5_ground_check's deck-vs-mountain test: for every Nth 1ROAD_* vertex, find the
triangle-exact 1GRASS height directly beneath and report the gap. Per-group, so a single
connector's float is separable from the loop's.
"""
import sys
from collections import defaultdict

path = sys.argv[1]
STRIDE = int(sys.argv[2]) if len(sys.argv) > 2 else 3

verts = []
groups = defaultdict(lambda: {"v": set(), "t": []})
cur = None
with open(path) as f:
    for line in f:
        if line.startswith("v "):
            _, x, y, z = line.split()
            verts.append((float(x), float(y), float(z)))
        elif line.startswith("o ") or line.startswith("g "):
            # write_obj emits `o <name>`; strip the _a/_b split suffix so a mesh that was
            # chunked under the 30k vertex cap reports as one group.
            cur = line[2:].strip()
            if len(cur) > 2 and cur[-2] == "_" and cur[-1].isalpha():
                cur = cur[:-2]
        elif line.startswith("f "):
            idx = [int(p.split("/")[0]) - 1 for p in line.split()[1:]]
            g = groups[cur]
            g["t"].append(tuple(idx[:3]))
            g["v"].update(idx[:3])

print(f"{len(verts):,} verts, {len(groups)} groups")

# hash every GRASS triangle by 4 m cell
CELL = 4.0
grass = defaultdict(list)
ng = 0
for name, g in groups.items():
    if not name.startswith("1GRASS") and not name.startswith("GRASS"):
        continue
    for a, b, c in g["t"]:
        A, B, C = verts[a], verts[b], verts[c]
        xs = (A[0], B[0], C[0]); zs = (A[2], B[2], C[2])
        for i in range(int(min(xs) // CELL), int(max(xs) // CELL) + 1):
            for j in range(int(min(zs) // CELL), int(max(zs) // CELL) + 1):
                grass[(i, j)].append((A, B, C))
        ng += 1
print(f"{ng:,} grass tris hashed into {len(grass):,} cells")


def surf(px, pz, y_ref):
    """Highest grass surface at or below y_ref + 0.3 directly under (px,pz)."""
    best = None
    for A, B, C in grass.get((int(px // CELL), int(pz // CELL)), ()):
        d = (B[2] - C[2]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[2] - C[2])
        if abs(d) < 1e-12:
            continue
        w0 = ((B[2] - C[2]) * (px - C[0]) + (C[0] - B[0]) * (pz - C[2])) / d
        w1 = ((C[2] - A[2]) * (px - C[0]) + (A[0] - C[0]) * (pz - C[2])) / d
        w2 = 1.0 - w0 - w1
        if w0 >= -1e-6 and w1 >= -1e-6 and w2 >= -1e-6:
            y = w0 * A[1] + w1 * B[1] + w2 * C[1]
            if y <= y_ref + 0.3 and (best is None or y > best):
                best = y
    return best


rows = []
for name, g in sorted(groups.items()):
    if not name.startswith("1ROAD"):
        continue
    gaps = []
    worst = None
    for vi in sorted(g["v"])[::STRIDE]:
        x, y, z = verts[vi]
        s = surf(x, z, y)
        if s is None:
            continue
        gaps.append(y - s)
        if worst is None or y - s > worst[0]:
            worst = (y - s, x, y, z, s)
    if not gaps:
        continue
    gaps.sort()
    n = len(gaps)
    rows.append((worst[0], name, n, gaps[n // 2], gaps[19 * n // 20], worst))

rows.sort(reverse=True)
print(f"\n{'group':32s} {'n':>7s} {'median':>8s} {'p95':>8s} {'max':>8s}   worst at (x, z)")
for mx, name, n, med, p95, worst in rows:
    print(f"{name:32s} {n:7d} {med:8.3f} {p95:8.3f} {mx:8.3f}   "
          f"({worst[1]:.1f}, {worst[3]:.1f})  deck {worst[2]:.3f} over grass {worst[4]:.3f}")
