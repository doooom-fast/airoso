"""Centre-seeking path along the paved mask between hand-placed waypoints (Blender python: numpy).

usage: tracer.py <route.json>   route.json: {"name":..., "closed":true, "wp":[[x,y],...]} in mrc_wide px
out  : <name>.path.json  {"px": [[x,y],...] (1 px steps), "len_m": ..., "half_w_px": [...]}
"""
import heapq, json, sys
import numpy as np

W, H, MPP = 2130, 3112, 0.5
route = json.load(open(sys.argv[1]))
mask = np.frombuffer(open('mask.raw', 'rb').read(), np.uint8).reshape(H, W).astype(bool)
rgb = np.frombuffer(open('mrc_wide.rgb', 'rb').read(), np.uint8).reshape(H, W, 3).astype(np.int16)
R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
lum = (R + G + B) / 3
grey = ((rgb.max(-1) - rgb.min(-1)) < 32) & (lum > 85) & (lum < 225) & ((G - R) < 14)

try:
    D = np.load('dist.npy')
except Exception:
    # chessboard-ish distance to the mask edge by repeated erosion
    D = np.zeros((H, W), np.float32)
    cur = mask.copy()
    k = 0
    while cur.any() and k < 80:
        D[cur] += 1
        nxt = cur.copy()
        for ax, s in ((0, 1), (0, -1), (1, 1), (1, -1)):
            nxt &= np.roll(cur, s, ax)
        cur = nxt; k += 1
    np.save('dist.npy', D)

cost = np.where(mask, 1.0 + 12.0 / (1.0 + D), np.where(grey, 6.0, 60.0)).astype(np.float32)


def dijkstra(a, b, pad=90):
    x0, x1 = max(0, min(a[0], b[0]) - pad), min(W - 1, max(a[0], b[0]) + pad)
    y0, y1 = max(0, min(a[1], b[1]) - pad), min(H - 1, max(a[1], b[1]) + pad)
    sub = cost[y0:y1 + 1, x0:x1 + 1].tolist()
    h, w = len(sub), len(sub[0])
    sx, sy, tx, ty = a[0] - x0, a[1] - y0, b[0] - x0, b[1] - y0
    dist = {(sx, sy): 0.0}; prev = {}
    pq = [(0.0, sx, sy)]
    nb = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    while pq:
        d, x, y = heapq.heappop(pq)
        if (x, y) == (tx, ty):
            break
        if d > dist.get((x, y), 1e18):
            continue
        for dx, dy, s in nb:
            xx, yy = x + dx, y + dy
            if 0 <= xx < w and 0 <= yy < h:
                nd = d + s * 0.5 * (sub[y][x] + sub[yy][xx])
                if nd < dist.get((xx, yy), 1e18):
                    dist[(xx, yy)] = nd; prev[(xx, yy)] = (x, y)
                    heapq.heappush(pq, (nd, xx, yy))
    path = [(tx, ty)]
    while path[-1] != (sx, sy):
        path.append(prev[path[-1]])
    return [(x + x0, y + y0) for x, y in reversed(path)]


def snap(p, r=25):
    """Move a waypoint to the most central mask pixel within r px."""
    x, y = p
    win = D[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1]
    yy, xx = np.unravel_index(np.argmax(win), win.shape)
    return (int(xx + max(0, x - r)), int(yy + max(0, y - r)))


wp = [snap(tuple(p)) for p in route['wp']]
if route.get('closed', True):
    wp.append(wp[0])
full = []
for a, b in zip(wp, wp[1:]):
    seg = dijkstra(a, b)
    full.extend(seg if not full else seg[1:])
L = sum(np.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(full, full[1:])) * MPP
hw = [float(D[y, x]) for x, y in full]
off = sum(1 for x, y in full if not mask[y, x])
json.dump({'name': route['name'], 'px': full, 'len_m': round(float(L), 1), 'half_w_px': hw, 'wp_snapped': wp},
          open(route['name'] + '.path.json', 'w'))
print(route['name'], 'len_m %.0f' % L, 'px', len(full), 'off-mask px', off)
