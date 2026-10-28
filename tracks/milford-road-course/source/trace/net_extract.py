"""Paved-surface network off the NAIP clip (run with Blender's python: numpy, no PIL).

in : mrc_wide.rgb (raw RGB, W x H)   out: mask.raw, skel.raw, graph.json (edges in px, lengths in m)
"""
import json, sys
import numpy as np

W, H, MPP = 2130, 3112, 0.5
rgb = np.frombuffer(open('mrc_wide.rgb', 'rb').read(), np.uint8).reshape(H, W, 3).astype(np.int16)
R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
mx, mn = rgb.max(-1), rgb.min(-1)
lum = (R + G + B) / 3
# the course is light grey: low chroma, bright, not green-dominant (grass/trees), not white (roofs)
mask = ((mx - mn) < 28) & (lum > 125) & (lum < 215) & ((G - R) < 12) & ((G - B) < 22)


def shift_or(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def dilate(m, r): return shift_or(m, r)
def erode(m, r): return ~shift_or(~m, r)


# close kerb paint gaps / cars, then open away speckle
mask = erode(dilate(mask, 2), 2)
mask = dilate(erode(mask, 2), 2)

# keep big components (flood fill by label propagation)
lab = np.zeros(mask.shape, np.int32)
ys, xs = np.nonzero(mask)
lab[ys, xs] = np.arange(1, len(ys) + 1)
for _ in range(4000):
    prev = lab
    m = lab.copy()
    for ax, s in ((0, 1), (0, -1), (1, 1), (1, -1)):
        m = np.maximum(m, np.roll(lab, s, ax))
    lab = np.where(mask, m, 0)
    if np.array_equal(lab, prev):
        break
ids, counts = np.unique(lab[lab > 0], return_counts=True)
keep = ids[counts * MPP * MPP > 3000]  # > 3000 m^2
mask = np.isin(lab, keep)
print('components kept', len(keep), 'areas m2', sorted((counts[np.isin(ids, keep)] * MPP * MPP).astype(int))[::-1][:8])

# Zhang-Suen thinning
img = mask.astype(np.uint8)


def nbrs(a):
    p = np.pad(a, 1)
    return [p[0:-2, 1:-1], p[0:-2, 2:], p[1:-1, 2:], p[2:, 2:], p[2:, 1:-1], p[2:, 0:-2], p[1:-1, 0:-2], p[0:-2, 0:-2]]


while True:
    changed = 0
    for step in (0, 1):
        P2, P3, P4, P5, P6, P7, P8, P9 = nbrs(img)
        Bn = P2 + P3 + P4 + P5 + P6 + P7 + P8 + P9
        seq = [P2, P3, P4, P5, P6, P7, P8, P9, P2]
        A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.uint8) for i in range(8))
        if step == 0:
            c = (P2 * P4 * P6 == 0) & (P4 * P6 * P8 == 0)
        else:
            c = (P2 * P4 * P8 == 0) & (P2 * P6 * P8 == 0)
        rm = (img == 1) & (Bn >= 2) & (Bn <= 6) & (A == 1) & c
        changed += int(rm.sum())
        img[rm] = 0
    if not changed:
        break
skel = img.astype(bool)

# graph: junctions (>=3 nbrs) and ends (1 nbr)
P = nbrs(skel.astype(np.uint8))
deg = sum(P) * skel
node_px = set(zip(*np.nonzero(skel & ((deg >= 3) | (deg == 1)))))
OFF = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
sk = skel


def nb(y, x):
    for dy, dx in OFF:
        yy, xx = y + dy, x + dx
        if 0 <= yy < H and 0 <= xx < W and sk[yy, xx]:
            yield yy, xx


# cluster adjacent node pixels into one node
node_id = {}
nodes = []
for p in sorted(node_px):
    if p in node_id:
        continue
    stack, comp = [p], []
    node_id[p] = len(nodes)
    while stack:
        q = stack.pop(); comp.append(q)
        for r in nb(*q):
            if r in node_px and r not in node_id:
                node_id[r] = len(nodes); stack.append(r)
    nodes.append(comp)

visited = set()
edges = []
for p in node_px:
    for r in nb(*p):
        if r in node_px or (p, r) in visited:
            continue
        path = [p, r]; visited.add((p, r))
        prev, cur = p, r
        while cur not in node_px:
            nxt = [s for s in nb(*cur) if s != prev and s not in path[-3:]]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            path.append(cur)
        if cur in node_px:
            visited.add((cur, prev))
        a, b = node_id[p], node_id.get(cur, -1)
        L = sum(np.hypot(y1 - y0, x1 - x0) for (y0, x0), (y1, x1) in zip(path, path[1:])) * MPP
        if L < 4 and a != b:
            pass
        edges.append({'a': a, 'b': b, 'len_m': round(float(L), 1), 'px': [[int(x), int(y)] for y, x in path[::2] + [path[-1]]]})

# dedupe edges walked from both ends
seen, uniq = set(), []
for e in edges:
    k = (min(e['a'], e['b']), max(e['a'], e['b']), round(e['len_m']))
    if k in seen:
        continue
    seen.add(k); uniq.append(e)
node_xy = [[float(np.mean([q[1] for q in c])), float(np.mean([q[0] for q in c]))] for c in nodes]
json.dump({'W': W, 'H': H, 'mpp': MPP, 'nodes': node_xy, 'edges': uniq}, open('graph.json', 'w'))
open('mask.raw', 'wb').write(mask.astype(np.uint8).tobytes())
open('skel.raw', 'wb').write(skel.astype(np.uint8).tobytes())
print('nodes', len(nodes), 'edges', len(uniq), 'edges>30m', sum(e['len_m'] > 30 for e in uniq))
