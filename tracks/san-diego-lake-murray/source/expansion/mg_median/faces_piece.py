"""The median's real width and middle per station of a piece, off the piece's DECLARED centre (item 2; reads only).

    python -I faces_piece.py <airoso> <mosaic.jpg> <georef.json> <piece> <s from> <s to> <expansion json> [--out <json>]

faces_md.py follows a median's declared ring; this follows the piece's rows instead, so it also reads where the plan
has an opening. The same two quantities: the equivalent width (the excess R - G over the asphalt's, summed across
the island, over a full island's plateau, +24.0: faces_md.py's, measured where MD13 fills its band) and that
excess's centroid. Per 2.5 m station, across REACH m either side of the declared centre every STEP m; the asphalt
is the lower quartile of the unmasked samples (the island may stand anywhere in the reach, so no fixed side band is
taken for it); the core is the contiguous run round the strongest sample that stands CUT of the way from the asphalt
to the plateau. Canopy and shadow are masked by tools/measure_median_tone.py's two rules. Printed in 10 m windows
(the medians of the stations within 5 m). Centres are off the declared centre, + = left of the piece's travel.
NO registration correction is applied: read lateral figures to about +-0.75 m. Run it on the data as DECLARED
(git 366a5a4c: data/expansion.north.json before fix_mg_median.py) to reproduce pieceC_faces_s40-250.json.
Pillow only. PLATEAU is measured (faces_md.py); STEP, REACH and CUT are [invented]: the method's settings, not gates."""
import json, math, sys
from pathlib import Path
from PIL import Image
air, mosaic, georef, pid, s0, s1, exp = sys.argv[1:8]
outp = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
sys.path.insert(0, str(Path(air) / "tools"))
import expansion_pieces as ep
doc, pieces = ep.load(exp)
pc = pieces[pid]
g = json.loads(Path(georef).read_text(encoding="utf-8"))
o = doc["frame"]["origin"]; lat0, lon0 = float(o["lat"]), float(o["lon"])
phi = math.radians(lat0)
m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
Image.MAX_IMAGE_PIXELS = None
PX = Image.open(mosaic).convert("RGB").load()
PLATEAU, STEP, REACH, CUT = 24.0, 0.25, 8.0, 0.25      # the plateau measured on MD13's full stretches (faces_md.py)
def pixel(E, N):
    lon = lon0 + E / m_lon; lat = math.radians(lat0 + N / m_lat)
    tx = (lon + 180.0) / 360.0 * 2 ** g["z"]; ty = (1.0 - math.log(math.tan(lat) + 1.0 / math.cos(lat)) / math.pi) / 2.0 * 2 ** g["z"]
    return PX[int((tx - g["x0"]) * 256.0), int((ty - g["y0"]) * 256.0)]
rows = []
s = float(s0)
while s <= float(s1) + 1e-9:
    (px, pz), _t, nl = pc.frame(s)
    c = pc.num(s, "median_off_m")
    smp, masked = [], 0
    x = -REACH
    while x <= REACH + 1e-9:
        r, gg, b = pixel(px + nl[0] * (c + x), pz + nl[1] * (c + x))
        lum = 0.2126 * r + 0.7152 * gg + 0.0722 * b
        mk = (gg - r > 5.0) or (lum < 0.72 * 131.7)
        masked += mk
        smp.append((x, r - gg, mk))
        x += STEP
    ok = sorted(d for _x, d, mk in smp if not mk)
    rec = {"s": s, "declared_w": round(pc.num(s, "median_w_m"), 2), "declared_off": round(c, 2), "masked_share": round(masked / len(smp), 2)}
    if len(ok) < 30:
        rec["used"] = False
    else:
        base = ok[len(ok) // 4]                       # the asphalt: the lower quartile across 16 m
        win = [(x_, d - base) for x_, d, mk in smp if not mk]
        need = CUT * (PLATEAU - base)
        peak = max(range(len(win)), key=lambda i: win[i][1])
        if win[peak][1] < need:
            rec.update(used=True, width=0.0, centre=None, peak=round(win[peak][1], 1), base=base)
        else:
            i0 = i1 = peak
            while i0 > 0 and win[i0 - 1][1] >= need and win[i0][0] - win[i0 - 1][0] <= 2 * STEP + 1e-9: i0 -= 1
            while i1 < len(win) - 1 and win[i1 + 1][1] >= need and win[i1 + 1][0] - win[i1][0] <= 2 * STEP + 1e-9: i1 += 1
            core = win[i0:i1 + 1]
            tot = sum(e for _x, e in core)
            rec.update(used=True, width=round(tot * STEP / (PLATEAU - base), 2), centre=round(sum(x_ * e for x_, e in core) / tot, 2),
                       peak=round(win[peak][1], 1), base=base)
    rows.append(rec)
    s += 2.5
def med(v):
    v = sorted(v); return v[len(v) // 2] if len(v) % 2 else 0.5 * (v[len(v) // 2 - 1] + v[len(v) // 2])
print("   s      declared w / off | stations used | equivalent width | centre off the DECLARED centre (+ = left)")
s = float(s0)
while s <= float(s1) + 1e-9:
    near = [r for r in rows if r.get("used") and abs(r["s"] - s) <= 5.0]
    if near:
        ws = [r["width"] for r in near]; cs = [r["centre"] for r in near if r.get("centre") is not None]
        d = min(rows, key=lambda r: abs(r["s"] - s))
        print("  %6.1f   %4.2f / %+5.2f        %d             %4.2f              %s   (with terracotta: %d of %d)" % (
            s, d["declared_w"], d["declared_off"], len(near), med(ws), ("%+5.2f" % med(cs)) if cs else " none", len(cs), len(near)))
    s += 10.0
if outp:
    Path(outp).write_text(json.dumps({"stations": rows}, indent=0), encoding="utf-8")
