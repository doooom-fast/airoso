"""Milford round 2: the inner hairpin's asphalt, re-centred and measured every 2 m on Oakland County's 2025 ortho
(0.25 ft = 7.62 cm, EPSG:2253, the Mac's crop). Classes [measured: the PC's samples of this crop]: grass / soil lum
149-156 chroma 34-35; asphalt lum 193-196 chroma 13-15; concrete (aprons, strips) lum 206-222 chroma 14-16. Pavement =
chroma < 24 and lum > 170; asphalt = pavement with the profile's lum (0.25 m mean) under 202.

python -I ortho_width.py <ortho.jpg> <georef.json> <inner_trace.json> <out.json> <overlay.jpg>
"""
import json
import math
import sys

import numpy as np
from PIL import Image, ImageDraw
from pyproj import Transformer

Image.MAX_IMAGE_PIXELS = None
ORTHO, GEO, TRACE, OUT, OVL = sys.argv[1:6]
geo = json.load(open(GEO, encoding="utf-8"))
wf = [float(v) for v in geo["world_file_text"].split()]
PX, X0, Y0 = wf[0], wf[4], wf[5]                       # ft per px, centre of the top-left pixel
img = np.asarray(Image.open(ORTHO).convert("RGB"), np.int16)
Hh, Ww = img.shape[:2]
lum_i = img.mean(-1)
chr_i = img.max(-1) - img.min(-1)
fwd = Transformer.from_crs("EPSG:4326", "EPSG:2253", always_xy=True)
inv = Transformer.from_crs("EPSG:2253", "EPSG:4326", always_xy=True)
FT = 0.3048

tr = json.load(open(TRACE, encoding="utf-8"))
ll = np.array(tr["lonlat"])
X, Y = fwd.transform(ll[:, 0], ll[:, 1])
P = np.c_[np.asarray(X) * FT, np.asarray(Y) * FT]       # metres in the state plane


def px(xm, ym):
    return (xm / FT - X0) / PX, (Y0 - ym / FT) / PX       # col, row (float)


def sample(xm, ym):
    c, r = px(xm, ym)
    c, r = int(round(c)), int(round(r))
    if 0 <= r < Hh and 0 <= c < Ww:
        return lum_i[r, c], chr_i[r, c]
    return None


STEP, REACH = 0.05, 15.0
K = int(REACH / STEP)
SMOOTH = int(0.25 / STEP)
GAP = int(0.40 / STEP)


def scan(P):
    out = []
    for i in range(len(P)):
        a, b = P[max(0, i - 1)], P[min(len(P) - 1, i + 1)]
        t = b - a
        t = t / (np.hypot(*t) or 1.0)
        n = np.array([-t[1], t[0]])
        prof = [sample(*(P[i] + n * k * STEP)) for k in range(-K, K + 1)]
        if any(q is None for q in prof):
            out.append(None)
            continue
        lum = np.array([q[0] for q in prof], float)
        chm = np.array([q[1] for q in prof], float)
        lum_s = np.convolve(lum, np.ones(2 * SMOOTH + 1) / (2 * SMOOTH + 1), mode="same")
        chm_s = np.convolve(chm, np.ones(2 * SMOOTH + 1) / (2 * SMOOTH + 1), mode="same")
        pave = (chm_s < 24) & (lum_s > 170)
        asph = pave & (lum_s < 202)

        def run(mask, c):
            if not mask[c]:
                near = [j for j in range(len(mask)) if mask[j] and abs(j - c) <= int(3.0 / STEP)]
                if not near:
                    return None
                c = min(near, key=lambda j: abs(j - c))
            l, gap = c, 0
            j = c
            while j > 0:
                j -= 1
                if mask[j]:
                    l, gap = j, 0
                else:
                    gap += 1
                    if gap > GAP:
                        break
            r, gap = c, 0
            j = c
            while j < len(mask) - 1:
                j += 1
                if mask[j]:
                    r, gap = j, 0
                else:
                    gap += 1
                    if gap > GAP:
                        break
            return (l - K) * STEP, (r - K) * STEP
        ra, rp = run(asph, K), run(pave, K)
        out.append({"n": n, "asph": ra, "pave": rp})
    return out


def resample(P, step):
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    t = np.arange(0, s[-1] + 1e-9, step)
    return np.c_[np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])]


CENTRE = sys.argv[6] if len(sys.argv) > 6 else "pave"   # the branch is concrete: centre on the whole pavement
P = resample(P, 2.0)
n_end = 6                      # the first / last 12 m stay on the trace: they join our fixes there
for _ in range(3):
    S = scan(P)
    off = np.array([0.0 if (q is None or q[CENTRE] is None or q[CENTRE][1] - q[CENTRE][0] > 18.0)
                    else 0.5 * (q[CENTRE][0] + q[CENTRE][1]) for q in S])
    off[:n_end] = 0.0
    off[-n_end:] = 0.0
    off = np.convolve(np.pad(off, 4, mode="edge"), np.ones(9) / 9, mode="valid")
    P = np.array([p + q["n"] * o if q else p for p, q, o in zip(P, S, off)])
    P = resample(P, 2.0)
S = scan(P)
wa = [None if (q is None or q["asph"] is None) else q["asph"][1] - q["asph"][0] for q in S]
wp = [None if (q is None or q["pave"] is None) else q["pave"][1] - q["pave"][0] for q in S]
lon, lat = inv.transform(P[:, 0] / FT, P[:, 1] / FT)
L = float(np.hypot(*np.diff(P, axis=0).T).sum())
good = sorted(w for w in wa if w)
out = {"_doc": "the inner hairpin's asphalt on the 2025 Oakland ortho (7.62 cm): re-centred 3 rounds, measured every 2 m",
       "length_m": round(L, 1), "asphalt_width_m": [None if w is None else round(w, 2) for w in wa],
       "pavement_width_m": [None if w is None else round(w, 2) for w in wp],
       "asphalt_p10_p50_p90": [good[len(good) // 10], good[len(good) // 2], good[9 * len(good) // 10]],
       "lonlat": [[round(a, 8), round(b, 8)] for a, b in zip(lon, lat)]}
json.dump(out, open(OUT, "w"))
print({k: v for k, v in out.items() if k in ("length_m", "asphalt_p10_p50_p90")})
print("asphalt widths every 8 m:", [None if w is None else round(w, 1) for w in wa[::4]])
print("pavement widths every 8 m:", [None if w is None else round(w, 1) for w in wp[::4]])
# overlay at 1/4 scale
sc = 4
im = Image.open(ORTHO).convert("RGB").resize((Ww // sc, Hh // sc))
dr = ImageDraw.Draw(im)
dr.line([tuple(v / sc for v in px(*p)) for p in P], fill=(255, 0, 0), width=2)
for p, q in zip(P, S):
    if q and q["asph"]:
        a1, b1 = px(*(p + q["n"] * q["asph"][0])), px(*(p + q["n"] * q["asph"][1]))
        dr.line([(a1[0] / sc, a1[1] / sc), (b1[0] / sc, b1[1] / sc)], fill=(0, 255, 255), width=1)
im.save(OVL, quality=88)
