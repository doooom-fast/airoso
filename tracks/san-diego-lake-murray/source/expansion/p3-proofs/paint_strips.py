"""Ledger 0054 P3 repair round 2: a straightened NAIP strip of a north piece between s_a and s_b (x = station at 4 px/m,
y = the offset across the road at 10 px/m, about the station line smoothed as tools/aerial_paint_north.py reads it), with
the paint the intermediate takes from the aerial (source/expansion/aerial__paint_north.json `use`: red = a painted median's
two faces or an island's outline, orange = a double yellow) — what the measurement read, over what the aerial shows.

    python paint_strips.py <track-dir> <piece> <s_a> <s_b> <out.png>
"""
import json, math, sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tools"))
import aerial_paint_north as apn
from author_expansion import Frame
track, pid, sa, sb, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
X = json.load(open(track + "/data/expansion.north.json", encoding="utf-8"))
cl = json.load(open(track + "/data/centerline.local.json", encoding="utf-8"))
fr = Frame(cl["origin"])
pc = next(p for p in X["pieces"] if p["id"] == pid)
rows = [dict(zip(pc["columns"], r)) for r in pc["stations"]]
delta = apn.smooth_frame(rows, apn.FRAME_SIGMA_M)
cache = apn.default_cache()
wins = []
for f in sorted(cache.glob(f"sd_{pid}_*.json")):
    wins.append(apn.Window(json.loads(f.read_text()), cache))
PXM, PYM = 4, 10
idx = [i for i, r in enumerate(rows) if sa <= r["s"] <= sb]
W = len(idx) * 10
H = 24 * PYM
im = Image.new("RGB", (W, H))
px = im.load()
for c, i in enumerate(idx):
    r = rows[i]
    a, b = rows[max(0, i - 1)], rows[min(len(rows) - 1, i + 1)]
    tx, tz = b["x"] - a["x"], b["z"] - a["z"]
    L = math.hypot(tx, tz)
    tx, tz = tx / L, tz / L
    nx, nz = -tz, tx
    for xx in range(10):
        al = (xx - 5) * 0.25
        for yy in range(H):
            o = 12 - yy / PYM + delta[i]
            x, z = r["x"] + nx * o + tx * al, r["z"] + nz * o + tz * al
            lon, lat = fr.lonlat(x, z)
            mx, my = apn.merc(lon, lat)
            v = None
            for w in wins:
                v = w.sample(mx, my)
                if v is not None:
                    break
            if v:
                px[c * 10 + xx, yy] = tuple(int(t) for t in v)
d = ImageDraw.Draw(im)
meas = {q["s"]: q for q in json.load(open(track + "/source/expansion/aerial__paint_north.json"))["pieces"][pid]}
def Yo(o, i):
    return int((12 - (o - delta[i])) * PYM)
for c, i in enumerate(idx):
    r = rows[i]
    x = c * 10 + 5
    for o in (r["left_m"], r["right_m"]):
        d.point((x, Yo(o, i)), fill=(0, 255, 0))
    mt, mo, mw = r["median_type"], float(r["median_off_m"] or 0), float(r["median_w_m"] or 0)
    if mt in ("none", "line") or mw < 1.0:
        d.point((x, Yo(mo, i)), fill=(60, 120, 255))
    else:
        for o in (mo + mw / 2 - 0.18, mo - mw / 2 + 0.18):
            d.point((x, Yo(o, i)), fill=(60, 120, 255))
    q = meas.get(r["s"])
    q = (q or {}).get("use")
    if q:
        if q["kind"] == "median":
            for o in (q["centre_off_m"] + q["width_m"] / 2 - 0.18, q["centre_off_m"] - q["width_m"] / 2 + 0.18):
                d.rectangle((x - 1, Yo(o, i) - 1, x + 1, Yo(o, i) + 1), fill=(255, 0, 0))
        else:
            d.rectangle((x - 1, Yo(q["centre_off_m"], i) - 1, x + 1, Yo(q["centre_off_m"], i) + 1), fill=(255, 140, 0))
for c, i in enumerate(idx):
    if rows[i]["s"] % 50 == 0:
        d.text((c * 10, 0), str(int(rows[i]["s"])), fill=(255, 0, 255))
im.save(out)
print(out, im.size)
