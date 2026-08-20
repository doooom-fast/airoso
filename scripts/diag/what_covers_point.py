"""Every mesh group with a triangle covering a given XZ, and its height there."""
import sys
from collections import defaultdict

path, PX, PZ = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
RAD = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0

verts = []
tris = defaultdict(list)
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
            A, B, C = verts[idx[0]], verts[idx[1]], verts[idx[2]]
            if min(A[0], B[0], C[0]) > PX + 6 or max(A[0], B[0], C[0]) < PX - 6:
                continue
            if min(A[2], B[2], C[2]) > PZ + 6 or max(A[2], B[2], C[2]) < PZ - 6:
                continue
            tris[cur].append((A, B, C))

pts = [(PX, PZ)]
if RAD:
    pts += [(PX + dx, PZ + dz) for dx in (-RAD, 0, RAD) for dz in (-RAD, 0, RAD) if (dx or dz)]

for px, pz in pts:
    print(f"\n--- at ({px:.3f}, {pz:.3f}) ---")
    found = []
    for name, ts in tris.items():
        for A, B, C in ts:
            d = (B[2] - C[2]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[2] - C[2])
            if abs(d) < 1e-12:
                continue
            w0 = ((B[2] - C[2]) * (px - C[0]) + (C[0] - B[0]) * (pz - C[2])) / d
            w1 = ((C[2] - A[2]) * (px - C[0]) + (A[0] - C[0]) * (pz - C[2])) / d
            w2 = 1.0 - w0 - w1
            if w0 >= -1e-6 and w1 >= -1e-6 and w2 >= -1e-6:
                found.append((w0 * A[1] + w1 * B[1] + w2 * C[1], name))
    for y, name in sorted(found, reverse=True):
        print(f"   {y:9.3f}  {name}")
    if not found:
        print("   (nothing covers this point)")
