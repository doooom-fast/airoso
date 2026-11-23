"""Ledger 0102 (read-only): ground poking through the built lane on a stretch of the gate centreline (the first 0.1.15
rehearsal's red). Samples every STEP m along and every 0.25 m across the lane (+/- w/2 - 0.1), the highest 1ROAD/1KERB and
the highest 1GRASS/1LAWN face over each point; prints how many points have the ground above the road (and within 5 mm
under it), the worst, and the inner edge (u > +5) apart from the rest.
usage: python -I lane_poke_0102.py <workshop> <s0> <s1> [step] [obj]   (numpy; <workshop>/data/gate_centerline.json + track.obj)"""
import json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

ws = Path(sys.argv[1]); S0, S1 = float(sys.argv[2]), float(sys.argv[3])
STEP = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
obj = sys.argv[5] if len(sys.argv) > 5 else "track.obj"
gl = json.loads((ws / "data" / "gate_centerline.json").read_text())
P = np.array(gl["points_xyz_m"], float); W = np.array(gl["widths_m"], float)
d = np.r_[0, np.cumsum(np.hypot(np.diff(P[:, 0]), np.diff(P[:, 2])))]
sel = (d >= S0 - 25) & (d <= S1 + 25); C = P[sel]
x0, x1 = C[:, 0].min() - 15, C[:, 0].max() + 15; z0, z1 = C[:, 2].min() - 15, C[:, 2].max() + 15
verts = []; faces = []; grp = "?"
with open(ws / "data" / obj, encoding="utf-8", errors="replace") as f:
    for ln in f:
        if ln.startswith("v "):
            a = ln.split(); verts.append((float(a[1]), float(a[2]), float(a[3])))
        elif ln.startswith(("g ", "o ")):
            grp = ln.split(maxsplit=1)[1].strip()
        elif ln.startswith("f "):
            faces.append(([int(p.split("/")[0]) - 1 for p in ln.split()[1:]], grp))
V = np.array(verts)
CELL = 1.0
road = defaultdict(list); grass = defaultdict(list)
for q, g in faces:
    G = g.upper()
    tgt = road if G.startswith(("1ROAD", "1KERB")) else grass if G.startswith(("1GRASS", "1LAWN")) else None
    if tgt is None:
        continue
    Q = V[q]
    if Q[:, 0].max() < x0 or Q[:, 0].min() > x1 or Q[:, 2].max() < z0 or Q[:, 2].min() > z1:
        continue
    for j in range(1, len(q) - 1):
        a, b, c = V[q[0]], V[q[j]], V[q[j + 1]]
        for ci in range(int(min(a[0], b[0], c[0]) // CELL), int(max(a[0], b[0], c[0]) // CELL) + 1):
            for cj in range(int(min(a[2], b[2], c[2]) // CELL), int(max(a[2], b[2], c[2]) // CELL) + 1):
                tgt[(ci, cj)].append((a, b, c, g))
def top(field, px, pz, yref):
    best = None; own = None
    for a, b, c, g in field.get((int(px // CELL), int(pz // CELL)), ()):
        dd = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(dd) < 1e-12: continue
        w0 = ((b[2] - c[2]) * (px - c[0]) + (c[0] - b[0]) * (pz - c[2])) / dd
        w1 = ((c[2] - a[2]) * (px - c[0]) + (a[0] - c[0]) * (pz - c[2])) / dd
        w2 = 1 - w0 - w1
        if min(w0, w1, w2) < -1e-6: continue
        y = w0 * a[1] + w1 * b[1] + w2 * c[1]
        if abs(y - yref) > 2.5: continue
        if best is None or y > best: best, own = y, g
    return best, own
n = 0; poke = []; near = 0
s = S0
while s <= S1:
    i = max(1, min(int(np.searchsorted(d, s)), len(P) - 1)); t = (s - d[i - 1]) / (d[i] - d[i - 1])
    x = P[i - 1, 0] + t * (P[i, 0] - P[i - 1, 0]); z = P[i - 1, 2] + t * (P[i, 2] - P[i - 1, 2]); y = P[i - 1, 1] + t * (P[i, 1] - P[i - 1, 1])
    tx, tz = P[i, 0] - P[i - 1, 0], P[i, 2] - P[i - 1, 2]; L = float(np.hypot(tx, tz)); nx, nz = -tz / L, tx / L
    half = W[i] / 2 - 0.1
    for off in np.arange(-half, half + 1e-9, 0.25):
        px, pz = x + nx * off, z + nz * off
        ry, _ = top(road, px, pz, y)
        if ry is None: continue
        gy, go = top(grass, px, pz, ry)
        n += 1
        if gy is None: continue
        if gy > ry: poke.append((gy - ry, round(s, 2), round(float(off), 2), go))
        elif gy > ry - 0.005: near += 1
    s += STEP
poke.sort(reverse=True)
print(f"s {S0}-{S1} every {STEP} m x 0.25 m: {n} lane points; ground ABOVE the road at {len(poke)}, within 5 mm under at {near}")
if poke:
    a = np.array([p[0] for p in poke]); ss = np.array([p[1] for p in poke])
    print(f"  above by: max {a.max():.4f} p50 {np.median(a):.4f}; stations {ss.min()}-{ss.max()}")
    for p in poke[:10]:
        print(f"  +{p[0]:.4f} at s {p[1]} off {p[2]} {p[3]}")
inner = [p for p in poke if p[2] > 5.0]; toe = [p for p in poke if p[2] <= 5.0]
for name, rows in (("u > +5 (inner edge)", inner), ("u <= +5 (bank toe / centre)", toe)):
    if rows:
        print(f"  {name}: {len(rows)} points, max +{max(r[0] for r in rows):.4f}, s {min(r[1] for r in rows)}-{max(r[1] for r in rows)}, "
              f"u {min(r[2] for r in rows)}..{max(r[2] for r in rows)}")
