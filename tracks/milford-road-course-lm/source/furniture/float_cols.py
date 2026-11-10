"""float_cols.py <track.obj>: audit_mesh's E rule (walls floating over ground) re-run, naming the wall object of each hit"""
import sys
from collections import defaultdict
verts, owner_v = [], {}
cur = None
groups = defaultdict(set)
for ln in open(sys.argv[1]):
    if ln.startswith("o "):
        cur = ln[2:].strip()
    elif ln.startswith("v "):
        q = ln.split(); verts.append((float(q[1]), float(q[2]), float(q[3])))
    elif ln.startswith("f ") and cur:
        for t in ln.split()[1:]:
            groups[cur].add(int(t.split("/")[0]) - 1)
def pts(prefix):
    return [(verts[i], n) for n, ids in groups.items() if n.upper().startswith(prefix) for i in ids]
def hsh(ps, c):
    h = defaultdict(list)
    for (x, y, z), _ in ps:
        h[(int(x // c), int(z // c))].append((x, y, z))
    return h
grass, road = hsh(pts("1GRASS"), 4.0), hsh(pts("1ROAD"), 4.0)
def near(h, x, z, R=4.5, c=4.0):
    ci, cj = int(x // c), int(z // c); ys = []
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for rx, ry, rz in h.get((ci + di, cj + dj), ()):
                if (x - rx) ** 2 + (z - rz) ** 2 <= R * R:
                    ys.append(ry)
    return ys
col = defaultdict(lambda: (1e9, None))
for (x, y, z), n in pts("1WALL"):
    k = (round(x / 0.6), round(z / 0.6))
    if y < col[k][0]:
        col[k] = (y, n)
gaps = {}
for (kx, kz), (by, n) in col.items():
    g = near(grass, kx * 0.6, kz * 0.6) + near(road, kx * 0.6, kz * 0.6)
    if g:
        gaps[(kx, kz)] = (by - max(g), n)
sup = {k for k, (gp, _) in gaps.items() if gp <= 0.6}
for (kx, kz), (gap, n) in sorted(gaps.items()):
    if gap > 1.4 and not any((kx + a, kz + b) in sup for a in range(-4, 5) for b in range(-4, 5)):
        print(f"float {gap:.2f} m at x {kx * 0.6:.1f} z {kz * 0.6:.1f}: {n}")
