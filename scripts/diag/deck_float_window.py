"""Deck-vs-grass gap for one 1ROAD group, reported per-vertex inside an XZ window,
plus the stacked-carriageway context (is there another leg of the SAME group below?).
"""
import sys, math
from collections import defaultdict

path, group = sys.argv[1], sys.argv[2]
CX, CZ, R = float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])

verts = []
objs = defaultdict(lambda: {"v": set(), "t": []})
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
            objs[cur]["v"].update(idx[:3])

CELL = 4.0
grass = defaultdict(list)
for name, g in objs.items():
    if not name.startswith("1GRASS"):
        continue
    for a, b, c in g["t"]:
        A, B, C = verts[a], verts[b], verts[c]
        xs = (A[0], B[0], C[0]); zs = (A[2], B[2], C[2])
        if max(xs) < CX - R - 20 or min(xs) > CX + R + 20:
            continue
        if max(zs) < CZ - R - 20 or min(zs) > CZ + R + 20:
            continue
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


# every vertex of `group` in the window, and every OTHER 1ROAD deck below it
road_v = [verts[i] for i in objs[group]["v"]]
allroad = defaultdict(list)
for name, g in objs.items():
    if not name.startswith("1ROAD"):
        continue
    for a, b, c in g["t"]:
        A, B, C = verts[a], verts[b], verts[c]
        xs = (A[0], B[0], C[0]); zs = (A[2], B[2], C[2])
        for i in range(int(min(xs) // CELL), int(max(xs) // CELL) + 1):
            for j in range(int(min(zs) // CELL), int(max(zs) // CELL) + 1):
                allroad[(i, j)].append((name, A, B, C))


def decks(px, pz):
    out = []
    for name, A, B, C in allroad.get((int(px // CELL), int(pz // CELL)), ()):
        d = (B[2] - C[2]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[2] - C[2])
        if abs(d) < 1e-12:
            continue
        w0 = ((B[2] - C[2]) * (px - C[0]) + (C[0] - B[0]) * (pz - C[2])) / d
        w1 = ((C[2] - A[2]) * (px - C[0]) + (A[0] - C[0]) * (pz - C[2])) / d
        w2 = 1.0 - w0 - w1
        if w0 >= -1e-6 and w1 >= -1e-6 and w2 >= -1e-6:
            out.append((name, w0 * A[1] + w1 * B[1] + w2 * C[1]))
    return out


rows = []
for x, y, z in road_v:
    if math.hypot(x - CX, z - CZ) > R:
        continue
    s = surf(x, z, y)
    if s is None:
        continue
    other = [(n, dy) for n, dy in decks(x, z) if dy < y - 0.05]
    rows.append((y - s, x, y, z, s, other))
rows.sort(reverse=True)
print(f"{group} — {len(rows)} verts within {R:.0f} m of ({CX:.1f}, {CZ:.1f})")
print(f"{'gap':>8s} {'deck':>9s} {'grass':>9s}   x, z              other deck below")
for gap, x, y, z, s, other in rows[:14]:
    o = ", ".join(f"{n}@{dy:.2f}" for n, dy in sorted(other, key=lambda t: -t[1])[:2]) or "-"
    print(f"{gap:8.3f} {y:9.3f} {s:9.3f}   ({x:8.1f},{z:9.1f})   {o}")
if rows:
    g = sorted(r[0] for r in rows)
    print(f"median {g[len(g)//2]:.3f}  p95 {g[19*len(g)//20]:.3f}  max {g[-1]:.3f}")
