"""Ground over the run-off aprons on a BUILT gate OBJ (ledger 0081; report only, no exit code).

Samples each 1RUNOFF_apron_* triangle at four interior points, finds the 1GRASS surface at the same x / z (the lowest hit:
on Nevada's port there is one ground sheet, so lowest and highest agree), and prints the share of samples where the ground
stands over the apron, and its median / p95 / max.

    python tools/apron_seat_check.py <workshop>/data/track.obj [<object prefix, default 1RUNOFF_apron; PADAPRON for the visual pads>]
"""
import sys
from collections import defaultdict
V = []; groups = defaultdict(list); cur = None
for ln in open(sys.argv[1], encoding="utf-8", errors="replace"):
    if ln.startswith("v "):
        p = ln.split(); V.append((float(p[1]), float(p[2]), float(p[3])))
    elif ln.startswith("o "):
        n = ln[2:].strip(); cur = "A" if n.startswith(sys.argv[2] if len(sys.argv) > 2 else "1RUNOFF_apron") else "G" if n.startswith("1GRASS") else None
    elif cur and ln.startswith("f "):
        ids = [int(t.split("/")[0]) - 1 for t in ln.split()[1:]]
        for k in range(1, len(ids) - 1):
            groups[cur].append((ids[0], ids[k], ids[k + 1]))
C = 2.0
grid = defaultdict(list)
for t in groups["G"]:
    xs = [V[i][0] for i in t]; zs = [V[i][2] for i in t]
    for gx in range(int(min(xs) // C), int(max(xs) // C) + 1):
        for gz in range(int(min(zs) // C), int(max(zs) // C) + 1):
            grid[(gx, gz)].append(t)
def bary(t, x, z):
    (x1, _, z1), (x2, _, z2), (x3, _, z3) = (V[i] for i in t)
    d = (z2 - z3) * (x1 - x3) + (x3 - x2) * (z1 - z3)
    if abs(d) < 1e-12: return None
    a = ((z2 - z3) * (x - x3) + (x3 - x2) * (z - z3)) / d
    b = ((z3 - z1) * (x - x3) + (x1 - x3) * (z - z3)) / d
    c = 1 - a - b
    if min(a, b, c) < -1e-6: return None
    return a * V[t[0]][1] + b * V[t[1]][1] + c * V[t[2]][1]
diffs = []
for t in groups["A"]:
    for (a, b) in [(1/3, 1/3), (0.6, 0.2), (0.2, 0.6), (0.2, 0.2)]:
        c = 1 - a - b
        x = a * V[t[0]][0] + b * V[t[1]][0] + c * V[t[2]][0]
        z = a * V[t[0]][2] + b * V[t[1]][2] + c * V[t[2]][2]
        y = a * V[t[0]][1] + b * V[t[1]][1] + c * V[t[2]][1]
        g = [h for h in (bary(q, x, z) for q in grid[(int(x // C), int(z // C))]) if h is not None]
        if g:
            diffs.append(min(g) - y)
diffs.sort()
n = len(diffs)
over = [d for d in diffs if d > 0]
print(f"apron tris {len(groups['A'])}, samples {n}, ground over apron {len(over)} ({100*len(over)/max(1,n):.1f} %), "
      f"over 2 cm {sum(d > 0.02 for d in diffs)}, p95 {diffs[int(0.95*(n-1))]:+.3f} m, max {diffs[-1]:+.3f} m, median {diffs[n//2]:+.3f} m")
