"""eye-check crops of a median island on the NAIP mosaic (pure Python + Pillow; the tool's own pixel mapping).
python -I crop_md.py <airoso> <mosaic.jpg> <georef.json> <island id> <s from> <s to> <out.png> [--scale 6] [--ring]"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

air, mosaic, georef, mid, s0, s1, out = sys.argv[1:8]
scale = int(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 6
ring_on = "--ring" in sys.argv
s0, s1 = float(s0), float(s1)
e = json.loads((Path(air) / "tracks/san-diego-lake-murray/data/expansion.north.json").read_text(encoding="utf-8"))
m = next(x for x in e["medians"] if x["id"] == mid)
ring = m["polygon_xz"]
n = len(ring) // 2
step = (m["s_to"] - m["s_from"]) / (n - 1)
g = json.loads(Path(georef).read_text(encoding="utf-8"))
o = e["frame"]["origin"]
lat0, lon0 = float(o["lat"]), float(o["lon"])
phi = math.radians(lat0)
m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)


def px(E, N):
    lon = lon0 + E / m_lon
    lat = math.radians(lat0 + N / m_lat)
    tx = (lon + 180.0) / 360.0 * 2 ** g["z"]
    ty = (1.0 - math.log(math.tan(lat) + 1.0 / math.cos(lat)) / math.pi) / 2.0 * 2 ** g["z"]
    return (tx - g["x0"]) * 256.0, (ty - g["y0"]) * 256.0


i0 = max(0, int(round((s0 - m["s_from"]) / step)))
i1 = min(n - 1, int(round((s1 - m["s_from"]) / step)))
a = [px(*ring[i]) for i in range(i0, i1 + 1)]
b = [px(*ring[2 * n - 1 - i]) for i in range(i0, i1 + 1)]
w = [math.hypot(ring[i][0] - ring[2 * n - 1 - i][0], ring[i][1] - ring[2 * n - 1 - i][1]) for i in range(i0, i1 + 1)]
us = [p[0] for p in a + b]
vs = [p[1] for p in a + b]
pad = 24
box = (int(min(us)) - pad, int(min(vs)) - pad, int(max(us)) + pad + 1, int(max(vs)) + pad + 1)
Image.MAX_IMAGE_PIXELS = None
im = Image.open(mosaic).convert("RGB").crop(box)
im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
if ring_on:
    d = ImageDraw.Draw(im)
    pts = [((u - box[0]) * scale, (v - box[1]) * scale) for u, v in a + b[::-1]]
    d.line(pts + [pts[0]], fill=(0, 255, 255), width=1)
im.save(out)
print(f"{mid} s {s0:.0f}-{s1:.0f}: stations {i0}-{i1} of {n} (step {step:.3f} m), width {min(w):.2f}-{max(w):.2f} m, "
      f"crop {box} -> {im.size} at x{scale}: {out}")
