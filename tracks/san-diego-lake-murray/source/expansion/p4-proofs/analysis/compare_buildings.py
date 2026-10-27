"""Old band identical to v0.19.0? Read both gate OBJs' HOUSE / BUILDING groups (local frame x=E, y=up, z=N), join each
building's faces into islands by shared vertices, and compare the islands within 120 m of the mainline (centreline of the
NEW project, same lap) by centroid, footprint vertex count and bottom height. Also list the new band's islands."""
import json, math, sys
from collections import defaultdict

OLD, NEW, PROJ = sys.argv[1], sys.argv[2], sys.argv[3]
cl = json.load(open(PROJ + "/data/centerline.local.json", encoding="utf-8"))
C = cl["points_xyz_m"]
B = 60.0
rb = defaultdict(list)
for i in range(0, len(C), 2):
    rb[(int(C[i][0] // B), int(C[i][2] // B))].append((C[i][0], C[i][2]))
def d_main(x, z):
    bx, bz = int(x // B), int(z // B); best = 1e18
    for dx in (-2, -1, 0, 1, 2):
        for dz in (-2, -1, 0, 1, 2):
            for (rx, rz) in rb.get((bx + dx, bz + dz), ()):
                best = min(best, (x - rx) ** 2 + (z - rz) ** 2)
    return math.sqrt(best)

def islands(path):
    V = []; faces = []; cur = None; nverts = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            if ln.startswith("v "):
                a = ln.split(); V.append((float(a[1]), float(a[2]), float(a[3])))
            elif ln[0] in "og":
                cur = ln.split()[1]
            elif ln.startswith("f ") and cur and cur.startswith(("HOUSE", "BUILDING")):
                faces.append((cur, [int(t.split("/")[0]) - 1 for t in ln.split()[1:]]))
                nverts[cur] = nverts.get(cur, 0)
    # union-find over vertices by POSITION (the exporter splits by normal)
    key = {}
    parent = {}
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def union(a, b):
        ra, rb_ = find(a), find(b)
        if ra != rb_:
            parent[ra] = rb_
    for grp, idx in faces:
        ks = []
        for i in idx:
            k = (round(V[i][0], 3), round(V[i][1], 3), round(V[i][2], 3))
            if k not in parent:
                parent[k] = k
            ks.append(k)
        for k in ks[1:]:
            union(ks[0], k)
    comp = defaultdict(set)
    grp_of = {}
    for grp, idx in faces:
        k = (round(V[idx[0]][0], 3), round(V[idx[0]][1], 3), round(V[idx[0]][2], 3))
        r = find(k)
        for i in idx:
            comp[r].add((round(V[i][0], 3), round(V[i][1], 3), round(V[i][2], 3)))
        grp_of[r] = grp.split("_")[0]
    out = []
    for r, vs in comp.items():
        xs = [v[0] for v in vs]; zs = [v[2] for v in vs]; ys = [v[1] for v in vs]
        out.append({"grp": grp_of[r], "cx": round(sum(xs) / len(xs), 2), "cz": round(sum(zs) / len(zs), 2),
                    "ymin": round(min(ys), 3), "ymax": round(max(ys), 3), "n": len(vs)})
    return out

old = islands(OLD); new = islands(NEW)
def key(b):
    return (b["grp"], round(b["cx"], 1), round(b["cz"], 1))
old_band_old = {key(b): b for b in old if d_main(b["cx"], b["cz"]) <= 120}
old_band_new = {key(b): b for b in new if d_main(b["cx"], b["cz"]) <= 120}
print("v0.19.0 islands", len(old), "(old band", len(old_band_old), ") | new build islands", len(new), "(old band", len(old_band_new), ")")
same = sum(1 for k, b in old_band_old.items() if k in old_band_new and old_band_new[k]["n"] == b["n"] and abs(old_band_new[k]["ymin"] - b["ymin"]) < 0.02)
moved = [(k, round(old_band_new[k]["ymin"] - b["ymin"], 3)) for k, b in old_band_old.items() if k in old_band_new and abs(old_band_new[k]["ymin"] - b["ymin"]) >= 0.02]
missing = [k for k in old_band_old if k not in old_band_new]
extra = [k for k in old_band_new if k not in old_band_old]
print("old band: identical", same, "| re-seated by >= 2 cm", len(moved), moved[:8], "| missing", len(missing), missing[:5], "| extra", len(extra), extra[:5])
newband = [b for b in new if d_main(b["cx"], b["cz"]) > 120]
from collections import Counter
print("new band islands", len(newband), Counter(b["grp"] for b in newband))
print("total verts (positions) old", sum(b["n"] for b in old), "new", sum(b["n"] for b in new))
