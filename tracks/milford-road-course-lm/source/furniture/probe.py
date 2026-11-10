"""probe.py <track.obj> x z [x z ...]: every triangle of every group covering (x, z) (Y-up OBJ), its height there, and the
group's vertices within 4.5 m (min / max y)"""
import sys
from collections import defaultdict
verts = []
cur = None
tris = defaultdict(list)
P = [(float(a), float(b)) for a, b in zip(sys.argv[2::2], sys.argv[3::2])]
for ln in open(sys.argv[1]):
    if ln.startswith("o "):
        cur = ln[2:].strip()
    elif ln.startswith("v "):
        q = ln.split(); verts.append((float(q[1]), float(q[2]), float(q[3])))
    elif ln.startswith("f "):
        ix = [int(t.split("/")[0]) - 1 for t in ln.split()[1:]]
        for k in range(1, len(ix) - 1):
            tri = (ix[0], ix[k], ix[k + 1])
            xs = [verts[i][0] for i in tri]; zs = [verts[i][2] for i in tri]
            for x, z in P:
                if min(xs) - 0.01 <= x <= max(xs) + 0.01 and min(zs) - 0.01 <= z <= max(zs) + 0.01:
                    tris[(x, z)].append((cur, tri))
for x, z in P:
    print(f"== ({x}, {z})")
    for n, tri in tris[(x, z)]:
        (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = [verts[i] for i in tri]
        d = (z2 - z3) * (x1 - x3) + (x3 - x2) * (z1 - z3)
        if abs(d) < 1e-12:
            continue
        a = ((z2 - z3) * (x - x3) + (x3 - x2) * (z - z3)) / d
        b = ((z3 - z1) * (x - x3) + (x1 - x3) * (z - z3)) / d
        c = 1 - a - b
        if min(a, b, c) < -1e-6:
            continue
        span = max(((verts[i][0] - verts[j][0]) ** 2 + (verts[i][2] - verts[j][2]) ** 2) ** 0.5 for i in tri for j in tri)
        print(f"  {n:28s} y {a * y1 + b * y2 + c * y3:8.3f}  tri span {span:6.1f} m  vert y {y1:.2f} {y2:.2f} {y3:.2f}")
