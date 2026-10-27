"""Where are the thin lighter triangles at the foot of the Jackson cuts? Read the v0.19.0 gate OBJ (local frame x=E,
y=up, z=N) beside Jackson north (piece D, right side = SW) and list every thin 1GRASS triangle within 30 m of the
pavement edge on that side, with its height over the road, its slope and its thinness. Also a cross-section at a station."""
import json, math, sys
from collections import defaultdict

PROJ = sys.argv[1]
S0, S1 = float(sys.argv[2]), float(sys.argv[3])
SECT = [float(s) for s in sys.argv[4].split(",")] if len(sys.argv) > 4 and sys.argv[4] else []
SIGN = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0   # -1: the connector's LEFT side (= the intermediate piece's right, J4->J5)

C = json.load(open(PROJ + "/data/connectors.local.json", encoding="utf-8"))["connectors"]
D = next(c for c in C if c["name"].startswith("north_J5_jackson_north"))
P = D["points_xyz_m"]; W = D["widths_m"]
# cumulative s
S = [0.0]
for i in range(1, len(P)):
    S.append(S[-1] + math.hypot(P[i][0] - P[i-1][0], P[i][2] - P[i-1][2]))
print("jackson north: pts", len(P), "length", round(S[-1], 1), "start", [round(v, 1) for v in P[0]], "end", [round(v, 1) for v in P[-1]])

def frame(x, z):
    """(s, d) of plan point: d>0 = right of travel"""
    best = None
    for i in range(len(P) - 1):
        ax, az = P[i][0], P[i][2]; bx, bz = P[i+1][0], P[i+1][2]
        ex, ez = bx - ax, bz - az; L2 = ex*ex + ez*ez or 1.0
        t = max(0.0, min(1.0, ((x-ax)*ex + (z-az)*ez) / L2))
        px, pz = ax + t*ex, az + t*ez
        dd = math.hypot(x-px, z-pz)
        if best is None or dd < best[0]:
            L = math.sqrt(L2)
            # right of travel in x=E,z=N frame: travel (ex,ez); right = (ez, -ex)
            side = ((x-px)*ez - (z-pz)*ex) / L
            ys = P[i][1] + t*(P[i+1][1]-P[i][1])
            best = (dd, S[i] + t*L, side, ys, W[i] + t*(W[i+1]-W[i]) if isinstance(W, list) else W)
    return best

# read OBJ
V = []; tris = defaultdict(list); cur = None
with open(PROJ + "/data/track.obj", encoding="utf-8", errors="replace") as f:
    for ln in f:
        if ln.startswith("v "):
            a = ln.split(); V.append((float(a[1]), float(a[2]), float(a[3])))
        elif ln[0] in "og":
            cur = ln.split()[1]
        elif ln.startswith("f ") and cur:
            a = [int(t.split("/")[0]) - 1 for t in ln.split()[1:]]
            for k in range(1, len(a) - 1):
                tris[cur].append((a[0], a[k], a[k+1]))

# bbox prefilter: Jackson stretch
xs = [p[0] for p in P]; zs = [p[2] for p in P]
bx0, bx1, bz0, bz1 = min(xs)-60, max(xs)+60, min(zs)-60, max(zs)+60
thin = []; allt = 0
for name, T in tris.items():
    if not name.startswith("1GRASS"):
        continue
    for (i, j, k) in T:
        a, b, c = V[i], V[j], V[k]
        cx = (a[0]+b[0]+c[0])/3; cz = (a[2]+b[2]+c[2])/3
        if not (bx0 < cx < bx1 and bz0 < cz < bz1):
            continue
        fr = frame(cx, cz)
        if fr is None or not (S0 <= fr[1] <= S1) or not (0 < SIGN*fr[2] < 40):
            continue
        allt += 1
        # geometry
        e = [math.dist(a, b), math.dist(b, c), math.dist(c, a)]
        ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]; vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
        nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
        area2 = math.sqrt(nx*nx+ny*ny+nz*nz)
        if area2 < 1e-9:
            continue
        alt = area2 / max(e)            # min altitude
        slope = math.degrees(math.acos(min(1.0, abs(ny)/area2)))
        hs = [a[1], b[1], c[1]]
        if alt < 0.25 and max(e) > 1.5:
            thin.append((round(fr[1], 1), round(SIGN*fr[2]-fr[4]/2, 2), round(min(hs)-fr[3], 2), round(max(hs)-fr[3], 2),
                         round(alt, 3), round(max(e), 2), round(slope, 1), round(ny/area2, 2), name))
print("1GRASS tris on the right side within 40 m:", allt, " thin (alt<0.25, longest>1.5):", len(thin))
thin.sort()
by_d = defaultdict(int)
for t in thin:
    by_d[round(t[1])] += 1
print("thin by distance past the pavement edge (m):", dict(sorted(by_d.items())))
for t in thin[:80]:
    print(t)
# cross sections
for s in SECT:
    pts = []
    for name, T in tris.items():
        if not name.startswith(("1GRASS", "1KERB", "1ROAD")):
            continue
        seen = set()
        for tri in T:
            for i in tri:
                if i in seen:
                    continue
                seen.add(i)
                x, y, z = V[i]
                if not (bx0 < x < bx1 and bz0 < z < bz1):
                    continue
                fr = frame(x, z)
                if fr and abs(fr[1]-s) < 0.6 and -2 < SIGN*fr[2] < 35:
                    pts.append((round(SIGN*fr[2]-fr[4]/2, 2), round(y-fr[3], 3), name[:14]))
    pts.sort()
    print(f"\n--- section s={s}: (d past pavement edge, h over road centre, mesh)")
    for p in pts:
        print("  ", p)
