"""Scan NAIP beside the traced lap for edge-parallel narrow lines (rails, walls, fences): a ridge (bright or dark)
narrower than ~2 m standing out of the profile at a steady offset over consecutive stations.

edge_lines.py <repo> <out.json> <out.jpg>
"""
import json, math, sys
import numpy as np
from PIL import Image, ImageDraw

REPO, OUT, OUTIMG = sys.argv[1:4]
img = Image.open(f"{REPO}/tracks/milford-road-course/source/naip_2022_mrc.jpg").convert("RGB")
A = np.asarray(img).astype(np.float32)
G = A.mean(axis=2)
H, W = G.shape
LON0, LAT0, LON1, LAT1 = -83.67, 42.56050328638498, -83.657, 42.57949671361502
lat_c = (LAT0 + LAT1) / 2
MLON = 111320.0 * math.cos(math.radians(lat_c)); MLAT = 110540.0
# local metres about the frame's centre
X0 = (LON0 + LON1) / 2; Y0 = lat_c
def to_m(lon, lat): return ((lon - X0) * MLON, (lat - Y0) * MLAT)
def to_ll(x, y): return (X0 + x / MLON, Y0 + y / MLAT)
def to_px(x, y):
    lon, lat = to_ll(x, y)
    return ((lon - LON0) / (LON1 - LON0) * W - 0.5, (LAT1 - lat) / (LAT1 - LAT0) * H - 0.5)
def sample(xs, ys):
    px, py = to_px(xs, ys)
    px = np.clip(px, 0, W - 1.001); py = np.clip(py, 0, H - 1.001)
    i, j = np.floor(px).astype(int), np.floor(py).astype(int)
    fx, fy = px - i, py - j
    return (G[j, i] * (1 - fx) * (1 - fy) + G[j, i + 1] * fx * (1 - fy) + G[j + 1, i] * (1 - fx) * fy + G[j + 1, i + 1] * fx * fy)

g = json.load(open(f"{REPO}/tracks/milford-road-course/data/centerline.geojson"))["features"][0]
co = g["geometry"]["coordinates"]; wd = g["properties"]["widths_m"]
P = np.array([to_m(c[0], c[1]) for c in co])
# resample every 2 m
seg = np.hypot(*np.diff(P, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)])
S = np.arange(0, s[-1], 2.0)
X = np.interp(S, s, P[:, 0]); Y = np.interp(S, s, P[:, 1]); WD = np.interp(S, s, wd[:len(s)])
T = np.gradient(np.stack([X, Y], 1), axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
N = np.stack([-T[:, 1], T[:, 0]], 1)  # left of travel

OFF = np.arange(0.5, 30.01, 0.5)      # metres past the traced edge
rows = []
for side, sg in (("L", 1.0), ("R", -1.0)):
    hits = []   # (station index, offset, sign, contrast)
    for k in range(len(S)):
        d = WD[k] / 2 + OFF
        xs = X[k] + sg * N[k, 0] * d; ys = Y[k] + sg * N[k, 1] * d
        # average along-track +-1 m to beat noise
        prof = np.zeros_like(OFF)
        for a in (-1.0, 0.0, 1.0):
            prof += sample(xs + T[k, 0] * a, ys + T[k, 1] * a)
        prof /= 3
        for m in range(4, len(OFF) - 4):
            nb = (prof[m - 3] + prof[m + 3]) / 2            # 1.5 m either side
            c = prof[m] - nb
            near = max(abs(prof[m] - prof[m - 3]), abs(prof[m] - prof[m + 3]))
            if abs(c) >= 18 and min(abs(prof[m] - prof[m - 3]), abs(prof[m] - prof[m + 3])) >= 10:
                if abs(c) >= abs(prof[m - 1] - (prof[m - 4] + prof[m + 2]) / 2) and abs(c) >= abs(prof[m + 1] - (prof[m - 2] + prof[m + 4]) / 2):
                    hits.append((k, float(OFF[m]), 1 if c > 0 else -1, float(c)))
    # link into runs: same sign, offset within 0.75 m, station gap <= 2 (4 m)
    hits.sort()
    runs = []
    open_ = []
    for h in hits:
        best = None
        for r in open_:
            lk, lo, ls = r[-1][0], r[-1][1], r[-1][2]
            if ls == h[2] and 0 < h[0] - lk <= 2 and abs(lo - h[1]) <= 0.75:
                if best is None or abs(lo - h[1]) < abs(best[-1][1] - h[1]):
                    best = r
        if best is not None:
            best.append(h)
        else:
            r = [h]; open_.append(r); runs.append(r)
        open_ = [r for r in open_ if h[0] - r[-1][0] <= 2]
    for r in runs:
        L = (r[-1][0] - r[0][0]) * 2.0
        if L < 20:
            continue
        offs = [h[1] for h in r]
        pts = []
        for h in r:
            k = h[0]; d = WD[k] / 2 + h[1]
            pts.append(to_ll(X[k] + sg * N[k, 0] * d, Y[k] + sg * N[k, 1] * d))
        rows.append({"side": side, "s0": float(S[r[0][0]]), "s1": float(S[r[-1][0]]), "length_m": L,
                     "tone": "bright" if r[0][2] > 0 else "dark", "offset_med_m": float(np.median(offs)),
                     "offset_range_m": [float(min(offs)), float(max(offs))], "contrast_med": float(np.median([abs(h[3]) for h in r])),
                     "n": len(r), "polyline_lonlat": [[round(p[0], 7), round(p[1], 7)] for p in pts[::3] + [pts[-1]]]})
rows.sort(key=lambda r: (r["s0"], r["side"]))
json.dump({"lap_m": float(S[-1]), "runs": rows}, open(OUT, "w"), indent=1)
im = img.copy(); d = ImageDraw.Draw(im)
for i, r in enumerate(rows):
    pts = []
    for lon, lat in r["polyline_lonlat"]:
        pts.append(((lon - LON0) / (LON1 - LON0) * W, (LAT1 - lat) / (LAT1 - LAT0) * H))
    col = (255, 60, 255) if r["tone"] == "bright" else (0, 255, 255)
    d.line(pts, fill=col, width=2)
    d.text(pts[0], str(i), fill=(255, 255, 0))
im.save(OUTIMG, quality=88)
print(len(rows), "runs >= 20 m")
for i, r in enumerate(rows):
    print(i, r["side"], int(r["s0"]), int(r["s1"]), r["length_m"], r["tone"], round(r["offset_med_m"], 1), r["offset_range_m"], round(r["contrast_med"]))
