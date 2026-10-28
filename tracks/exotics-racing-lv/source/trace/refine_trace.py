"""Snap a hand-seeded closed centerline onto a track's painted edge lines in an ortho, measuring width.

    python refine_trace.py IMG SEEDS.json OUT_PREFIX [m_per_px]

SEEDS.json: {"pts": [[x, y], ...]  (orig px, in driving order, closed loop),
             "search_px": 28, "min_half_px": 8,
             "zones": [{"from": i, "to": j, "search_px": 12}]}   # seed-index ranges with a tighter search
Writes OUT_PREFIX.json (centre px every ~2 px, widths in px and m, per-station edge strength) and
OUT_PREFIX_overlay.png (centre red, edges cyan, seeds yellow). Pure stdlib + Pillow.
"""
import json, math, sys
from PIL import Image, ImageDraw

img_path, seeds_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
mpp = float(sys.argv[4]) if len(sys.argv) > 4 else 0.4815
cfg = json.load(open(seeds_path))
seeds = [tuple(p) for p in cfg["pts"]]
S0 = cfg.get("search_px", 28); MINH = cfg.get("min_half_px", 8)
WMIN, WMAX = cfg.get("width_min_m", 8.0) / mpp, cfg.get("width_max_m", 22.0) / mpp   # plausible edge-line spacing
TH = cfg.get("ridge_min", 8.0)                                                        # min line brightness over its flanks

im = Image.open(img_path).convert("L"); W, H = im.size; LUM = im.tobytes()


def lum(x, y):
    if not (0 <= x < W - 1 and 0 <= y < H - 1):
        return 0.0
    x0, y0 = int(x), int(y); fx, fy = x - x0, y - y0; i = y0 * W + x0
    a, b, c, d = LUM[i], LUM[i + 1], LUM[i + W], LUM[i + W + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def catmull_closed(P, step=2.0):
    n = len(P); out_pts = []; src = []
    for i in range(n):
        p0, p1, p2, p3 = P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]
        seg = math.dist(p1, p2); k = max(2, int(seg / step))
        for j in range(k):
            t = j / k; t2, t3 = t * t, t * t * t
            out_pts.append(tuple(0.5 * ((2 * p1[a]) + (-p0[a] + p2[a]) * t + (2 * p0[a] - 5 * p1[a] + 4 * p2[a] - p3[a]) * t2
                                        + (-p0[a] + 3 * p1[a] - 3 * p2[a] + p3[a]) * t3) for a in (0, 1)))
            src.append(i)
    return out_pts, src


def resample_closed(P, step=2.0):
    ring = P + [P[0]]; d = [0.0]
    for a, b in zip(ring, ring[1:]):
        d.append(d[-1] + math.dist(a, b))
    L = d[-1]; n = max(8, int(L / step)); out_pts = []; j = 0
    for k in range(n):
        s = k * L / n
        while d[j + 1] < s:
            j += 1
        t = (s - d[j]) / max(1e-9, d[j + 1] - d[j])
        out_pts.append((ring[j][0] + (ring[j + 1][0] - ring[j][0]) * t, ring[j][1] + (ring[j + 1][1] - ring[j][1]) * t))
    return out_pts, L


def smooth(v, half, closed=True, med=False):
    n = len(v); o = []
    for i in range(n):
        w = [v[(i + k) % n] for k in range(-half, half + 1)]
        o.append(sorted(w)[len(w) // 2] if med else sum(w) / len(w))
    return o


def fill_nan(v):
    n = len(v); good = [i for i in range(n) if v[i] == v[i]]
    if not good:
        return [0.0] * n
    out = list(v)
    for i in range(n):
        if v[i] != v[i]:
            j = min(good, key=lambda g: min(abs(g - i), n - abs(g - i)))
            out[i] = v[j]
    return out


def line_response(prof, ds):
    """Thin-bright-line ridge: centre minus the mean of both flanks 3-6 px out."""
    n = len(prof); r = [0.0] * n; a, b = int(3 / ds), int(6 / ds)
    for i in range(b, n - b):
        fl = [prof[i - k] for k in range(a, b + 1)] + [prof[i + k] for k in range(a, b + 1)]
        r[i] = prof[i] - sum(fl) / len(fl)
    return r


C, src = catmull_closed(seeds)
search = [S0] * len(seeds)
for z in cfg.get("zones", []):
    i = z["from"]
    while True:
        search[i % len(seeds)] = z["search_px"]
        if i % len(seeds) == z["to"] % len(seeds):
            break
        i += 1
srch = [search[s] for s in src]

ds = 0.5
for it in range(4):
    n = len(C); offs, wid, strength = [], [], []
    for i in range(n):
        a, b = C[(i - 2) % n], C[(i + 2) % n]
        tx, ty = b[0] - a[0], b[1] - a[1]; tl = math.hypot(tx, ty) or 1; tx, ty = tx / tl, ty / tl
        nx, ny = -ty, tx                      # left normal in image coords (y down) -> points to driver's right
        S = srch[i] if it < 2 else min(srch[i], 10)       # S bounds how far the pair's MIDPOINT may move
        R = S + WMAX / 2 + 8
        ss = [k * ds for k in range(int(-R / ds), int(R / ds) + 1)]
        prof = [lum(C[i][0] + s * nx, C[i][1] + s * ny) for s in ss]
        r = line_response(prof, ds)
        pk = [k for k in range(1, len(r) - 1) if r[k] >= r[k - 1] and r[k] >= r[k + 1] and r[k] > TH]
        best = None
        for ia, ka in enumerate(pk):
            for kb in pk[ia + 1:]:
                w = ss[kb] - ss[ka]; mid = (ss[ka] + ss[kb]) / 2
                if not (WMIN <= w <= WMAX) or abs(mid) > S:
                    continue
                g = int(3 / ds)
                inner = prof[ka + g:kb - g + 1]
                outer = prof[max(0, ka - 2 * g):ka - g + 1] + prof[kb + g:kb + 2 * g + 1]
                if not inner or not outer:
                    continue
                contrast = sum(outer) / len(outer) - sum(inner) / len(inner)
                score = min(r[ka], r[kb]) + 0.5 * contrast - 0.4 * abs(mid)
                if best is None or score > best[0]:
                    best = (score, mid, w, min(r[ka], r[kb]))
        if best is None:
            offs.append(float("nan")); wid.append(float("nan")); strength.append(0.0)
        else:
            offs.append(best[1]); wid.append(best[2]); strength.append(best[3])
    # stations with no valid pair inherit their neighbours' values before smoothing
    offs, wid = fill_nan(offs), fill_nan(wid)
    o = smooth(smooth(offs, 8, med=True), 4)
    C = [(C[i][0] + o[i] * (-(C[(i + 2) % n][1] - C[(i - 2) % n][1]) / (math.dist(C[(i + 2) % n], C[(i - 2) % n]) or 1)),
          C[i][1] + o[i] * ((C[(i + 2) % n][0] - C[(i - 2) % n][0]) / (math.dist(C[(i + 2) % n], C[(i - 2) % n]) or 1)))
         for i in range(n)]
    # light smoothing of the centre itself, then even resample; carry the search radius along by nearest index
    C = [((C[(i - 1) % n][0] + 2 * C[i][0] + C[(i + 1) % n][0]) / 4, (C[(i - 1) % n][1] + 2 * C[i][1] + C[(i + 1) % n][1]) / 4) for i in range(n)]
    oldC, oldS = C, srch
    C, L = resample_closed(C, 2.0)
    srch = [oldS[int(k * len(oldS) / len(C))] for k in range(len(C))]
    print(f"iter {it}: lap {L * mpp:.1f} m, mean |offset| {sum(abs(x) for x in offs) / n * mpp:.2f} m, "
          f"width median {sorted(wid)[n // 2] * mpp:.1f} m")

wsm = smooth(smooth(wid, 6, med=True), 4)
res = {"m_per_px": mpp, "lap_m": round(L * mpp, 1), "centre_px": [[round(x, 1), round(y, 1)] for x, y in C],
       "width_px_raw": [round(w, 1) for w in wid], "width_m": [round(w * mpp, 2) for w in wsm][:len(C)],
       "edge_strength": [round(s, 1) for s in strength]}
json.dump(res, open(out + ".json", "w"))

ov = Image.open(img_path).convert("RGB"); d = ImageDraw.Draw(ov); n = len(C)
for i in range(n):
    a, b = C[(i - 2) % n], C[(i + 2) % n]; tl = math.dist(a, b) or 1
    nx, ny = -(b[1] - a[1]) / tl, (b[0] - a[0]) / tl; hw = wsm[min(i, len(wsm) - 1)] / 2
    d.point((C[i][0] + hw * nx, C[i][1] + hw * ny), fill=(0, 255, 255)); d.point((C[i][0] - hw * nx, C[i][1] - hw * ny), fill=(0, 255, 255))
d.line(C + [C[0]], fill=(255, 0, 0), width=1)
for k, p in enumerate(seeds):
    d.ellipse((p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3), outline=(255, 255, 0)); d.text((p[0] + 4, p[1] - 4), str(k), fill=(255, 255, 0))
ov.save(out + "_overlay.png")
ws = sorted(wsm)
print(f"lap {L * mpp:.1f} m  width min/med/max {ws[0] * mpp:.1f}/{ws[len(ws) // 2] * mpp:.1f}/{ws[-1] * mpp:.1f} m  stations {n}")
