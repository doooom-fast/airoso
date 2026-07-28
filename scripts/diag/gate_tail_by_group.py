"""Which group owns the gate's failing tail? Counts samples over the gate thresholds per 1ROAD group.

Mirrors kn5_ground_check's stride-7 sampling of the combined road vertex list so the counts line up
with the number the gate prints.
"""
import sys
from collections import defaultdict

path = sys.argv[1]
verts = []
objs = defaultdict(lambda: {"v": [], "t": []})
cur = None
with open(path) as f:
    for line in f:
        if line.startswith("v "):
            _, x, y, z = line.split()
            verts.append((float(x), float(y), float(z)))
        elif line.startswith("o "):
            cur = line[2:].strip()
            if len(cur) > 2 and cur[-2] == "_" and cur[-1].isalpha():
                cur = cur[:-2]
        elif line.startswith("f "):
            idx = [int(p.split("/")[0]) - 1 for p in line.split()[1:]]
            objs[cur]["t"].append(tuple(idx[:3]))

for name, g in objs.items():
    g["v"] = sorted({v for t in g["t"] for v in t})

CELL = 4.0
grass = defaultdict(list)
for name, g in objs.items():
    if not name.startswith("1GRASS"):
        continue
    for a, b, c in g["t"]:
        A, B, C = verts[a], verts[b], verts[c]
        xs = (A[0], B[0], C[0]); zs = (A[2], B[2], C[2])
        for i in range(int(min(xs) // CELL), int(max(xs) // CELL) + 1):
            for j in range(int(min(zs) // CELL), int(max(zs) // CELL) + 1):
                grass[(i, j)].append((A, B, C))


def surf(px, pz, y_ref):
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


# the gate samples the CONCATENATED road vertex list at stride 7
road_names = sorted(n for n in objs if n.startswith("1ROAD") and "shoulder" not in n)
flat = [(n, vi) for n in road_names for vi in objs[n]["v"]]
per = defaultdict(list)
allg = []
for n, vi in flat[::7]:
    x, y, z = verts[vi]
    s = surf(x, z, y)
    if s is None:
        continue
    per[n].append((y - s, x, z))
    allg.append(y - s)

allg.sort()
print(f"combined: n {len(allg)}  median {allg[len(allg)//2]:+.3f}  "
      f"p95 {allg[19*len(allg)//20]:+.3f}  max {allg[-1]:+.3f}")
print(f"\n{'group':30s} {'n':>6s} {'>0.05':>7s} {'>0.10':>7s} {'p95':>8s} {'max':>8s}")
rows = []
for n, gs in per.items():
    v = sorted(g for g, _, _ in gs)
    rows.append((sum(1 for g in v if g > 0.10), n, len(v), sum(1 for g in v if g > 0.05),
                 v[19 * len(v) // 20], v[-1]))
for over10, n, cnt, over5, p95, mx in sorted(rows, reverse=True):
    print(f"{n:30s} {cnt:6d} {over5:7d} {over10:7d} {p95:8.3f} {mx:8.3f}")

# the worst offenders overall, with location
worst = sorted(((g, n, x, z) for n, gs in per.items() for g, x, z in gs), reverse=True)[:12]
print("\nworst samples:")
for g, n, x, z in worst:
    print(f"  {g:7.3f}  {n:28s} ({x:9.1f},{z:9.1f})")
