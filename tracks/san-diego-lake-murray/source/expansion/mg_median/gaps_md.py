"""where a declared median band shows no terracotta on the NAIP mosaic, and where it shows a strip much narrower than
the band: runs along the island (pure Python + Pillow; the profile of profile_md.py, summarised).
python -I gaps_md.py <airoso> <mosaic.jpg> <georef.json> <island id> <shadow ref lum> [--out json]"""
import json
import math
import sys
from pathlib import Path

from PIL import Image

SALMON, CANOPY, SHADOW_SHARE = 10.0, 5.0, 0.72   # SALMON [invented]; the other two are tools/measure_median_tone.py's
air, mosaic, georef, mid, ref = sys.argv[1:6]
ref = float(ref)
outp = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
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
P = Image.open(mosaic).convert("RGB").load()
rows = []
for k in range(n):
    a, b = ring[k], ring[2 * n - 1 - k]
    w = math.hypot(b[0] - a[0], b[1] - a[1])
    ux, uz = (b[0] - a[0]) / w, (b[1] - a[1]) / w
    cx, cz = 0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1])
    sal = can = sha = tot = 0
    wide = []                                   # salmon anywhere within the band + 2 m (a strip beside the band counts)
    of = -0.5 * w - 2.0
    while of <= 0.5 * w + 2.0 + 1e-9:
        u, v = px(cx + ux * of, cz + uz * of)
        r, gg, bb = P[int(u), int(v)]
        lum = 0.2126 * r + 0.7152 * gg + 0.0722 * bb
        inside = abs(of) <= 0.5 * w
        if r - gg >= SALMON:
            wide.append(of)
        if inside:
            tot += 1
            if gg - r > CANOPY:
                can += 1
            elif lum < SHADOW_SHARE * ref:
                sha += 1
            elif r - gg >= SALMON:
                sal += 1
        of += 0.25
    rows.append({"s": round(m["s_from"] + k * step, 1), "w": round(w, 2), "in_band": tot, "salmon": sal, "canopy": can, "shadow": sha,
                 "salmon_w_m": round(0.25 * len(wide), 2), "salmon_mid_m": round(sum(wide) / len(wide), 2) if wide else None})


def runs(pred, min_len):
    out, i = [], 0
    while i < len(rows):
        if pred(rows[i]):
            j = i
            while j + 1 < len(rows) and pred(rows[j + 1]):
                j += 1
            if j - i + 1 >= min_len:
                out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


lit = lambda r: r["in_band"] - r["canopy"] - r["shadow"]                      # noqa: E731
none = runs(lambda r: lit(r) >= 0.6 * r["in_band"] and r["salmon_w_m"] <= 0.25, 3)
narrow = runs(lambda r: lit(r) >= 0.6 * r["in_band"] and 0.25 < r["salmon_w_m"] <= 0.6 * r["w"], 4)
print(f"{mid}: {n} stations, step {step} m; band width {min(r['w'] for r in rows)}-{max(r['w'] for r in rows)} m")
print("NO terracotta in or beside the band (lit stations, 7.5 m or longer):")
for i, j in none:
    print(f"  s {rows[i]['s']:.1f}-{rows[j]['s']:.1f}  ({rows[j]['s'] - rows[i]['s'] + step:.1f} m)  band {rows[i]['w']}-{rows[j]['w']} m")
print("terracotta strip no wider than 0.6 of the band (lit stations, 10 m or longer):")
for i, j in narrow:
    ws = sorted(r["salmon_w_m"] for r in rows[i:j + 1])
    mids = sorted(r["salmon_mid_m"] for r in rows[i:j + 1] if r["salmon_mid_m"] is not None)
    print(f"  s {rows[i]['s']:.1f}-{rows[j]['s']:.1f}  ({rows[j]['s'] - rows[i]['s'] + step:.1f} m)  band {rows[i]['w']}-{rows[j]['w']} m, "
          f"strip median {ws[len(ws) // 2]} m, its middle {mids[len(mids) // 2]:+.2f} m off the band's centre")
if outp:
    Path(outp).write_text(json.dumps({"_doc": "gaps_md.py on " + mid + ": per station, samples every 0.25 m across the declared band "
                                      "(+2 m each side for the strip's own width); salmon R - G >= 10 [invented], canopy G - R > 5, "
                                      "shadow lum < 0.72 x " + str(ref), "rows": rows,
                                      "no_terracotta_runs_s": [[rows[i]["s"], rows[j]["s"]] for i, j in none],
                                      "narrow_runs_s": [[rows[i]["s"], rows[j]["s"]] for i, j in narrow]}), encoding="utf-8")
