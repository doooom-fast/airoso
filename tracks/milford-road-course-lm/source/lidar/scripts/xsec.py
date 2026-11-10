"""Cross-section + plan picture of the returns about one inventory line.
Top: every return, offset (x) vs height over its class-2 ground (y), all along-stations stacked; ground grey, other red.
Bottom: plan, along (x) vs offset (y), non-ground returns over 0.3 m coloured by height (blue 0.3 -> red 6 m).
python -I xsec.py pts.npz hag.npz inventory.json ID out.png [reach] [a0 a1]"""
import json, math, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
_argv = sys.argv; sys.argv = [_argv[0], _argv[1], _argv[3], "-"]
import probe2  # noqa: E402  (loads pts + the tree)
from probe2 import local, frame  # noqa: E402
sys.argv = _argv

hag = np.load(sys.argv[2])["hag"]; inv = json.load(open(sys.argv[3])); ID = sys.argv[4]; out = sys.argv[5]
R = float(sys.argv[6]) if len(sys.argv) > 6 else 8.0
it = next(i for i in inv["items"] if i["id"] == ID)
poly = local(it.get("polyline_lonlat") or it["footprint_lonlat"])
e, n, cls = probe2.e, probe2.n, probe2.cls
c0 = poly.mean(0); r = np.max(np.hypot(*(poly - c0).T)) + R + 1
ids = np.array(probe2.T.query_ball_point(c0, r=r))
al, off, L = frame(poly, np.c_[e[ids], n[ids]])
a0, a1 = (float(sys.argv[7]), float(sys.argv[8])) if len(sys.argv) > 8 else (0.5, L - 0.5)
ok = (np.abs(off) <= R) & (al >= a0) & (al <= a1) & ~np.isin(cls[ids], (7, 18)) & np.isfinite(hag[ids])
ids, al, off = ids[ok], al[ok], off[ok]; h = hag[ids]; c = cls[ids]
W, H1, H2 = 1000, 420, 360
im = Image.new("RGB", (W, H1 + H2 + 20), (255, 255, 255)); d = ImageDraw.Draw(im)
HMAX = 8.0
X = lambda o: (o + R) / (2 * R) * (W - 60) + 40
Y = lambda hh: H1 - 20 - (hh + 0.5) / (HMAX + 0.5) * (H1 - 40)
for hh in range(0, int(HMAX) + 1):
    d.line([(40, Y(hh)), (W - 20, Y(hh))], fill=(225, 225, 225)); d.text((5, Y(hh) - 6), f"{hh} m", fill=(0, 0, 0))
for oo in range(-int(R), int(R) + 1, 2):
    d.line([(X(oo), 20), (X(oo), H1 - 20)], fill=(235, 235, 235)); d.text((X(oo) - 8, H1 - 16), f"{oo:+d}", fill=(0, 0, 0))
for o_, h_, c_ in zip(off, h, c):
    col = (150, 150, 150) if c_ == 2 else (220, 30, 30)
    d.point((X(o_), Y(min(h_, HMAX))), fill=col)
d.text((45, 4), f"{ID}: {it['kind']}  along {a0:.0f}-{a1:.0f} of {L:.0f} m, {len(ids)} returns; x = offset from the NAIP line (m, + left of its drawing order), y = height over ground", fill=(0, 0, 0))
# plan
Y0 = H1 + 20
PX = lambda a: (a - a0) / max(a1 - a0, 1) * (W - 60) + 40
PY = lambda o: Y0 + (R - o) / (2 * R) * (H2 - 20)
d.line([(40, PY(0)), (W - 20, PY(0))], fill=(0, 120, 255))
m = (c != 2) & (h > 0.3)
for a_, o_, h_ in zip(al[m], off[m], h[m]):
    t = min(max((h_ - 0.3) / 5.7, 0), 1)
    d.rectangle([PX(a_) - 1, PY(o_) - 1, PX(a_) + 1, PY(o_) + 1], fill=(int(255 * t), 60, int(255 * (1 - t))))
d.text((45, Y0 + 2), "plan: along (x) vs offset (y); non-ground returns > 0.3 m, blue low -> red 6 m; blue line = the NAIP line", fill=(0, 0, 0))
im.save(out)
print(ID, "returns", len(ids), "->", out)
