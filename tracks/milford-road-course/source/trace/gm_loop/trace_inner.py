"""Milford round 2: GM's inner hairpin (OSM 72577413 nodes 41-59, 2010) traced off NAIP 2022 the way
tracks/milford-road-course/source/trace/ traced the lap (net_extract's colour rule, a centre-seeking shortest path between
waypoints, perpendicular scans re-centring the line and measuring the paved width every 2 m), in metres on the corrected
frame (unsquash_frame.py: lat 42.56050..42.57950 over the 3,112 rows, so a pixel is 0.500 m E x 0.678 m N).

python -I trace_inner.py <naip_2022_mrc.jpg> <mrc_fixes.json> <osm.json> <out.json> <overlay.jpg> [i0=337] [i1=518]
"""
import heapq
import json
import math
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

IMG, FIX, OSM, OUT, OVL = sys.argv[1:6]
I0 = int(sys.argv[6]) if len(sys.argv) > 6 else 337
I1 = int(sys.argv[7]) if len(sys.argv) > 7 else 518
LON0, LON1, LAT0, LAT1 = -83.6700, -83.6570, 42.56050, 42.57950
im = Image.open(IMG).convert("RGB")
Wpx, Hpx = im.size
DLON, DLAT = (LON1 - LON0) / Wpx, (LAT1 - LAT0) / Hpx
LATR = 42.57
KX, KY = 111320 * math.cos(math.radians(LATR)), 111132.0
MX, MY = DLON * KX, DLAT * KY          # metres per pixel east, north
R0, R1, C0, C1 = 1250, 1800, 400, 850   # crop (rows, cols)


def ll2px(lon, lat):
    return (lon - LON0) / DLON - 0.5 - C0, (LAT1 - lat) / DLAT - 0.5 - R0      # crop col, row (float)


def px2ll(c, r):
    return LON0 + (c + C0 + 0.5) * DLON, LAT1 - (r + R0 + 0.5) * DLAT


def ll2m(lon, lat):
    return (lon + 83.667) * KX, (lat - LATR) * KY


def m2ll(e, n):
    return e / KX - 83.667, n / KY + LATR


a = np.asarray(im, np.int16)[R0:R1, C0:C1]
R, G, B = a[..., 0], a[..., 1], a[..., 2]
mx, mn = a.max(-1), a.min(-1)
lum = (R + G + B) / 3
mask = ((mx - mn) < 28) & (lum > 125) & (lum < 215) & ((G - R) < 12) & ((G - B) < 22)
disk = np.hypot(*np.mgrid[-2:3, -2:3]) <= 2
mask = ndimage.binary_opening(ndimage.binary_closing(mask, disk), disk)
lab, nlab = ndimage.label(mask)
area = ndimage.sum(mask, lab, range(1, nlab + 1)) * MX * MY
keep = np.isin(lab, [i + 1 for i, s in enumerate(area) if s > 3000.0])
mask = keep
dt = ndimage.distance_transform_edt(mask, sampling=(MY, MX))
H, W = mask.shape
# asphalt only for the scans (the centre and the width): the concrete aprons and strips read 209-213 here (std 1-2), the
# asphalt 181-200; ASPH_MAX 205 [measured: the PC's samples of this crop]. The path search keeps the whole pavement.
ASPH_MAX = 205.0
lum_s = ndimage.uniform_filter(lum.astype(float), 3)
asph = ndimage.binary_opening(mask & (lum_s < ASPH_MAX), disk)

fx = json.load(open(FIX, encoding="utf-8"))
osm = json.load(open(OSM, encoding="utf-8"))
ways = {e["id"]: e for e in osm["elements"] if e["type"] == "way"}
inf, hp = ways[72577413], ways[1030539760]["nodes"]
ia, ib = inf["nodes"].index(hp[0]), inf["nodes"].index(hp[-1])
inner = inf["geometry"][ia:ib + 1]
# the via point: the inner path's node farthest from both splice fixes (its turn)
pa, pb = ll2m(fx[I0]["lon"], fx[I0]["lat"]), ll2m(fx[I1]["lon"], fx[I1]["lat"])
via = max(inner, key=lambda n: min(math.dist(ll2m(n["lon"], n["lat"]), pa), math.dist(ll2m(n["lon"], n["lat"]), pb)))


def dijkstra(src, dst):
    cost = np.where(mask, 1.0 + 30.0 / (dt + 0.3) ** 2, 1e4)
    dist = np.full(mask.shape, np.inf)
    prev = -np.ones(mask.shape, np.int64)
    sr, sc = src
    dist[sr, sc] = 0.0
    hq = [(0.0, sr, sc)]
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    stepm = {(dr, dc): math.hypot(dr * MY, dc * MX) for dr, dc in nb}
    while hq:
        d0, r, c = heapq.heappop(hq)
        if (r, c) == dst:
            break
        if d0 > dist[r, c]:
            continue
        for dr, dc in nb:
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W:
                nd = d0 + stepm[(dr, dc)] * 0.5 * (cost[r, c] + cost[rr, cc])
                if nd < dist[rr, cc]:
                    dist[rr, cc] = nd
                    prev[rr, cc] = r * W + c
                    heapq.heappush(hq, (nd, rr, cc))
    out, k = [], dst[0] * W + dst[1]
    while k >= 0:
        out.append((k // W, k % W))
        if (k // W, k % W) == src:
            break
        k = prev[k // W, k % W]
    return out[::-1]


def rc(lon, lat):
    c, r = ll2px(lon, lat)
    return int(round(r)), int(round(c))


wps = [rc(fx[I0]["lon"], fx[I0]["lat"]), rc(via["lon"], via["lat"]), rc(fx[I1]["lon"], fx[I1]["lat"])]
path = []
for s, t in zip(wps, wps[1:]):
    seg = dijkstra(s, t)
    path += seg if not path else seg[1:]
P = np.array([ll2m(*px2ll(c, r)) for r, c in path])


def resample(P, step):
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    t = np.arange(0, s[-1] + 1e-9, step)
    return np.c_[np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])]


def smooth(P, k):
    Q = P.copy()
    for i in range(k, len(P) - k):
        Q[i] = P[i - k:i + k + 1].mean(0)
    return Q


def onmask(e, n):
    lon, lat = m2ll(e, n)
    c, r = ll2px(lon, lat)
    r, c = int(round(r)), int(round(c))
    return 0 <= r < H and 0 <= c < W and bool(asph[r, c])


def scan(P):
    res = []
    for i in range(len(P)):
        a_, b_ = P[max(0, i - 1)], P[min(len(P) - 1, i + 1)]
        t = b_ - a_
        t = t / (np.hypot(*t) or 1.0)
        nrm = np.array([-t[1], t[0]])
        s = [onmask(*(P[i] + nrm * k * 0.25)) for k in range(-90, 91)]      # +-22.5 m every 0.25 m
        c = 90
        if not s[c]:
            near = [j for j in range(181) if s[j] and abs(j - c) <= 16]
            if not near:
                res.append(None)
                continue
            c = min(near, key=lambda j: abs(j - c))
        l_ = c
        while l_ > 0 and s[l_ - 1]:
            l_ -= 1
        r_ = c
        while r_ < 180 and s[r_ + 1]:
            r_ += 1
        res.append(((l_ - 90) * 0.25, (r_ - 90) * 0.25, nrm))
    return res


P = resample(smooth(smooth(P, 8), 8), 2.0)
for _ in range(3):
    S = scan(P)
    off = np.array([0.0 if (q is None or q[1] - q[0] > 18.0) else (q[0] + q[1]) / 2 for q in S])
    off = np.convolve(np.pad(off, 6, mode="edge"), np.ones(13) / 13, mode="valid")
    P = np.array([p + q[2] * o if q else p for p, q, o in zip(P, S, off)])
    P = resample(smooth(P, 3), 2.0)
S = scan(P)
wid = [((q[1] - q[0]) if q else None) for q in S]
good = sorted(w for w in wid if w and w <= 22)
med = good[len(good) // 2]
wf = [w if (w and 7.0 <= w <= 18.0) else med for w in wid]
k = 10
wf = [sorted(wf[max(0, i - k):i + k + 1])[len(wf[max(0, i - k):i + k + 1]) // 2] for i in range(len(wf))]
L = float(np.hypot(*np.diff(P, axis=0).T).sum())
out = {"_doc": "GM's inner hairpin (OSM 72577413 nodes %d-%d) traced off NAIP 2022 between mrc_fixes %d and %d" % (ia, ib, I0, I1),
       "via_osm_node": via, "length_m": round(L, 1), "width_median_m": round(med, 2),
       "width_p10_p90": [good[len(good) // 10], good[9 * len(good) // 10]],
       "off_pavement_stations": sum(1 for q in S if q is None), "apron_stations": sum(1 for w in wid if w and w > 18),
       "lonlat": [list(m2ll(*p)) for p in P], "width_m": [round(w, 2) for w in wf], "raw_width_m": wid}
json.dump(out, open(OUT, "w"))
print({k_: v for k_, v in out.items() if k_ not in ("lonlat", "width_m", "raw_width_m")})
# overlay
ov = im.crop((C0, R0, C1, R1)).resize(((C1 - C0) * 2, (R1 - R0) * 2))
dr = ImageDraw.Draw(ov)
mk = Image.fromarray((mask * 90).astype(np.uint8))
old = [ll2px(f["lon"], f["lat"]) for f in fx[I0 - 40:I1 + 40]]
dr.line([(c * 2, r * 2) for c, r in old], fill=(255, 255, 0), width=3)
newp = [ll2px(*m2ll(*p)) for p in P]
dr.line([(c * 2, r * 2) for c, r in newp], fill=(255, 0, 0), width=3)
for p, q in zip(P[::5], S[::5]):
    if q:
        a1 = ll2px(*m2ll(*(p + q[2] * q[0])))
        b1 = ll2px(*m2ll(*(p + q[2] * q[1])))
        dr.line([(a1[0] * 2, a1[1] * 2), (b1[0] * 2, b1[1] * 2)], fill=(0, 255, 255), width=1)
ov.save(OVL, quality=90)
