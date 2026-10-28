"""Traced pixel path -> centred, measured centreline (lon/lat + paved width per station).

Perpendicular scans of the paved mask re-centre the line and measure the width at every station.
in : <name>.path.json, mask.raw (mrc_wide frame)   out: <name>.final.json
"""
import json, math, sys
from statistics import median

W, H, MPP = 2130, 3112, 0.5
B = (-83.6700, 42.5630, -83.6570, 42.5770)  # mrc_wide.png bbox, EPSG:4326 north-up
name = sys.argv[1]
mask = open('mask.raw', 'rb').read()
M = lambda x, y: 0 <= int(x) < W and 0 <= int(y) < H and mask[int(y) * W + int(x)] == 1


def smooth(P, k):
    n = len(P)
    return [(sum(P[(i + j) % n][0] for j in range(-k, k + 1)) / (2 * k + 1),
             sum(P[(i + j) % n][1] for j in range(-k, k + 1)) / (2 * k + 1)) for i in range(n)]


def resample(P, step):
    Q = P + [P[0]]; out = [Q[0]]; acc = 0.0
    for a, b in zip(Q, Q[1:]):
        d = math.dist(a, b); t = step - acc
        while t <= d:
            f = t / d; out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)); t += step
        acc = (acc + d) % step
    return out[:-1] if math.dist(out[-1], out[0]) < step / 2 else out


def scan(P):
    """Per station: (left, right) paved extent along the normal, in px (None if off the pavement)."""
    n = len(P); res = []
    for i in range(n):
        a, b = P[i - 1], P[(i + 1) % n]
        tx, ty = b[0] - a[0], b[1] - a[1]; L = math.hypot(tx, ty)
        nx, ny = -ty / L, tx / L
        s = [M(P[i][0] + nx * t * 0.5, P[i][1] + ny * t * 0.5) for t in range(-90, 91)]  # +-22.5 m
        c = 90
        if not s[c]:
            near = [j for j in range(181) if s[j] and abs(j - c) <= 8]
            if not near:
                res.append(None); continue
            c = min(near, key=lambda j: abs(j - c))
        l = c
        while l > 0 and s[l - 1]: l -= 1
        r = c
        while r < 180 and s[r + 1]: r += 1
        res.append(((l - 90) * 0.5, (r - 90) * 0.5, nx, ny))
    return res


px = [tuple(map(float, q)) for q in json.load(open(name + '.path.json'))['px']]
if px[0] == px[-1]:
    px = px[:-1]
P = resample(smooth(smooth(px, 8), 8), 4.0)  # 4 px = 2 m
for it in range(3):
    S = scan(P)
    off = []
    for s in S:
        if s is None or (s[1] - s[0]) * MPP > 18:  # off-mask, an apron or a merge: don't trust the centre
            off.append(0.0)
        else:
            off.append((s[0] + s[1]) / 2)
    k = 6
    off = [sum(off[(i + j) % len(off)] for j in range(-k, k + 1)) / (2 * k + 1) for i in range(len(off))]
    P = [(p[0] + s[2] * o, p[1] + s[3] * o) if s else p for p, s, o in zip(P, S, off)]
    P = resample(smooth(P, 3), 4.0)
# merges: where a branch joins a road the doubled pavement drags the centre sideways; the racing
# line runs straight through, so smooth wide there, blended out to the zone edge
ZONES = [(1290, 882, 140, 30),   # (x, y, radius px, half-window stations): serpentine exit -> top straight
         (1803, 1770, 220, 30)]  # east side past the back-section gore and the cross-connector
for zx, zy, zr, zk in ZONES:
    for _ in range(3):
        n = len(P)
        Q = []
        for i, p in enumerate(P):
            dd = math.dist(p, (zx, zy))
            if dd >= zr:
                Q.append(p); continue
            a = sum(P[(i + j) % n][0] for j in range(-zk, zk + 1)) / (2 * zk + 1)
            b = sum(P[(i + j) % n][1] for j in range(-zk, zk + 1)) / (2 * zk + 1)
            t = 1.0 - (dd / zr) ** 2
            Q.append((p[0] + (a - p[0]) * t, p[1] + (b - p[1]) * t))
        P = Q
S = scan(P)
wid =[((s[1] - s[0]) * MPP if s else None) for s in S]
good = [w for w in wid if w and w <= 22]
med = median(good)
# width per station: measured where it reads as one carriageway, else the course median
wf = [w if (w and 7.0 <= w <= 18.0) else med for w in wid]
k = 10
wf = [sorted(wf[(i + j) % len(wf)] for j in range(-k, k + 1))[k] for i in range(len(wf))]  # running median
ll = [(B[0] + (x + 0.5) / W * (B[2] - B[0]), B[3] - (y + 0.5) / H * (B[3] - B[1])) for x, y in P]
lat0 = 42.57
Lm = sum(math.hypot((b[0] - a[0]) * 111320 * math.cos(math.radians(lat0)), (b[1] - a[1]) * 110950)
         for a, b in zip(ll, ll[1:] + ll[:1]))
q = sorted(good)
print(f'{name}: stations {len(P)}  length {Lm:.0f} m  width median {med:.1f} m  p10 {q[len(q)//10]:.1f}  p90 {q[9*len(q)//10]:.1f}'
      f'  off-pavement stations {sum(1 for s in S if s is None)}  apron stations {sum(1 for w in wid if w and w > 18)}')
json.dump({'lonlat': ll, 'width_m': [round(w, 2) for w in wf], 'raw_width_m': wid, 'px': P, 'length_m': round(Lm, 1)},
          open(name + '.final.json', 'w'))
