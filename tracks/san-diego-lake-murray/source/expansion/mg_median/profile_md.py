"""across-the-band colour profile of a median island on the NAIP mosaic, station by station (pure Python + Pillow).
python -I profile_md.py <airoso> <mosaic.jpg> <georef.json> <island id> <s from> <s to> [--every 5] [--out json]
Per station: R - G at offsets -6..+6 m (0.5 m) from the declared band's centre, + toward the ring's second side;
'salmon' = R - G >= SALMON (the Mac's bins: terracotta +13..+27, asphalt beside the median about -2..-4 here)."""
import json
import math
import sys
from pathlib import Path

from PIL import Image

SALMON = 10.0      # [invented] between the asphalt's own value and the terracotta's; a look, not a gate
air, mosaic, georef, mid, s0, s1 = sys.argv[1:7]
every = float(sys.argv[sys.argv.index("--every") + 1]) if "--every" in sys.argv else 5.0
outp = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
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


Image.MAX_IMAGE_PIXELS = None
im = Image.open(mosaic).convert("RGB")
P = im.load()
offs = [0.5 * k for k in range(-12, 13)]
rows = []
k = max(0, int(round((s0 - m["s_from"]) / step)))
k1 = min(n - 1, int(round((s1 - m["s_from"]) / step)))
stride = max(1, int(round(every / step)))
print("offsets -6 .. +6 m; '#' R-G >= %d, '+' >= 5, '.' else; | = the declared band's edges" % SALMON)
while k <= k1:
    a, b = ring[k], ring[2 * n - 1 - k]
    w = math.hypot(b[0] - a[0], b[1] - a[1])
    ux, uz = (b[0] - a[0]) / w, (b[1] - a[1]) / w
    cx, cz = 0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1])
    vals = []
    for of in offs:
        u, v = px(cx + ux * of, cz + uz * of)
        r, gg, bb = P[int(u), int(v)]
        vals.append((of, r - gg, r, gg, bb))
    sal = [of for of, d, *_ in vals if d >= SALMON and abs(of) <= 0.5 * w + 1.0]
    line = ""
    for of, d, *_ in vals:
        ch = "#" if d >= SALMON else ("+" if d >= 5 else ".")
        if abs(abs(of) - 0.5 * w) < 0.25:
            ch = "|" if ch == "." else ch
        line += ch
    s = m["s_from"] + k * step
    row = {"s": round(s, 1), "band_w_m": round(w, 2), "salmon_samples_in_band": len(sal),
           "salmon_from_m": min(sal) if sal else None, "salmon_to_m": max(sal) if sal else None,
           "r_minus_g": [d for _, d, *_ in vals]}
    rows.append(row)
    print("s %6.1f  w %4.2f  %s  salmon %s" % (s, w, line, ("%+.1f..%+.1f m" % (min(sal), max(sal))) if sal else "none"))
    k += stride
if outp:
    Path(outp).write_text(json.dumps({"_doc": "profile_md.py: R - G across " + mid + "'s declared band, NAIP 2022 z18 mosaic; "
                                      "salmon = R - G >= %g [invented]" % SALMON, "offsets_m": offs, "rows": rows}, indent=0),
                          encoding="utf-8")
