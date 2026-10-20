"""render.py <tris.json> <out.png> cx cz half_m [px_m] : top view, top-most surface per pixel, class colour x lambert"""
import json, math, sys
from PIL import Image
T = json.load(open(sys.argv[1]))["tris"]
out = sys.argv[2]; cx, cz, half = map(float, sys.argv[3:6]); pm = float(sys.argv[6]) if len(sys.argv) > 6 else 0.04
N = int(2 * half / pm)
COL = [("1WALL_STUB", (230, 228, 215)), ("MARKINGS", (255, 255, 255)), ("YLINE", (240, 190, 20)), ("1ROAD", (90, 90, 95)),
       ("1KERB", (175, 175, 170)), ("1GRASS", (80, 125, 50)), ("GRASS", (100, 110, 70)), ("LIGHT", (40, 40, 40))]
def col(n):
    u = n.upper()
    for p, c in COL:
        if u.startswith(p): return c
    return (200, 80, 200)
zb = [[-1e9] * N for _ in range(N)]; img = Image.new("RGB", (N, N), (0, 0, 0)); px = img.load()
L = (-0.5, 0.75, 0.43); ln = math.sqrt(sum(v*v for v in L)); L = tuple(v/ln for v in L)
for name, a, b, c in T:
    xs = [a[0], b[0], c[0]]; zs = [a[2], b[2], c[2]]
    if max(xs) < cx-half or min(xs) > cx+half or max(zs) < cz-half or min(zs) > cz+half: continue
    ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]; vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
    nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
    nl = math.sqrt(nx*nx+ny*ny+nz*nz) or 1
    if ny < 0: nx, ny, nz = -nx, -ny, -nz
    sh = max(0.15, (nx*L[0]+ny*L[1]+nz*L[2])/nl)
    base = col(name); cc = tuple(int(min(255, k*(0.35+0.75*sh))) for k in base)
    i0 = max(0, int((min(xs)-(cx-half))/pm)); i1 = min(N-1, int((max(xs)-(cx-half))/pm)+1)
    j0 = max(0, int(((cz+half)-max(zs))/pm)); j1 = min(N-1, int(((cz+half)-min(zs))/pm)+1)
    d = (b[2]-c[2])*(a[0]-c[0]) + (c[0]-b[0])*(a[2]-c[2])
    if abs(d) < 1e-12: continue
    for j in range(j0, j1+1):
        z = (cz+half) - (j+0.5)*pm
        for i in range(i0, i1+1):
            x = (cx-half) + (i+0.5)*pm
            l1 = ((b[2]-c[2])*(x-c[0]) + (c[0]-b[0])*(z-c[2]))/d
            l2 = ((c[2]-a[2])*(x-c[0]) + (a[0]-c[0])*(z-c[2]))/d
            l3 = 1-l1-l2
            if min(l1, l2, l3) < -1e-6: continue
            y = l1*a[1]+l2*b[1]+l3*c[1]
            if y > zb[j][i]:
                zb[j][i] = y; px[i, j] = cc
img.save(out); print("wrote", out, N)
