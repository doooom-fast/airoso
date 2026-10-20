"""extract.py <obj> <out.json> x,z,r [x,z,r ...] : every triangle (object name, 3 verts) with a vertex within r of a centre"""
import json, sys
obj, out = sys.argv[1], sys.argv[2]
C = [tuple(map(float, a.split(","))) for a in sys.argv[3:]]
V = []; cur = None; T = []
with open(obj, "r", encoding="ascii", errors="replace") as f:
    for line in f:
        c2 = line[:2]
        if c2 == "v ":
            q = line.split(); V.append((float(q[1]), float(q[2]), float(q[3])))
        elif c2 == "o " or c2 == "g ":
            cur = line[2:].strip()
        elif c2 == "f ":
            idx = [int(t.split("/")[0]) for t in line.split()[1:]]
            pts = [V[i - 1] for i in idx]
            if any((p[0]-cx)**2 + (p[2]-cz)**2 <= r*r for p in pts for cx, cz, r in C):
                for k in range(1, len(pts) - 1):
                    T.append([cur, pts[0], pts[k], pts[k + 1]])
json.dump({"centres": C, "tris": T}, open(out, "w"))
print(len(T), "tris")
