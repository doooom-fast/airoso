"""The real faces of Mission Gorge Rd's raised median over a stretch, read off the NAIP mosaic (item 1b; reads only).

    python -I faces_md.py <airoso> <mosaic.jpg> <georef.json> [--from 960] [--to 1240] [--out <json>]

The island is narrower than the photo resolves in places (a 2 m strip is four pixels, and the mosaic's JPEG stores one
colour sample per about 1 m), so a face is NOT read off a threshold here. Two quantities survive the blur, and the
faces are built from them:

  * the EQUIVALENT WIDTH: the sum of (R - G over the asphalt's own value) across the island, divided by what a full
    island reads over the asphalt (the plateau). A blurred strip spreads its colour but keeps its sum;
  * the CENTROID of the same excess: where the island's middle is.

Per station of piece C (2.5 m, the stations of data/expansion.north.json's MD13 ring), across the declared band and
REACH_M past each edge, every 0.25 m:
  base     the asphalt: the median R - G of the samples from GUARD_M to FAR_M past the band's two edges;
  plateau  what a full island reads: the median R - G of the samples at least CORE_IN_M inside the band, over the two
           reference stretches REF (where the island fills its band); one number for the whole run;
  core     the contiguous run of samples around the strongest one that stand CUT of the way from base to plateau
           (the island; the rest is noise and is not summed);
  width    sum over the core of (R - G - base) x 0.25 m / (plateau - base);   centre: the same excess's centroid.
A station is not used where canopy (G - R > 5) or shadow (luminance under 0.72 x the island's median, the two rules of
tools/measure_median_tone.py) takes more than MASK_SHARE of the band's samples. The method is CHECKED on the reference
stretches themselves: there the width it returns must be the declared band's (printed, and written to the record).

The faces are then the station values' medians in WINDOW_M windows, joined linearly. Offsets are in the PIECE frame
(tools/expansion_pieces.Piece: + = left of J3 -> J4 travel = north-west), metres off piece C's line.
Pillow only. CUT, GUARD_M, FAR_M, CORE_IN_M, REACH_M, MASK_SHARE and WINDOW_M are [invented]: the method's settings,
not gates."""
import json
import math
import sys
from pathlib import Path

from PIL import Image

air, mosaic, georef = Path(sys.argv[1]), sys.argv[2], sys.argv[3]


def opt(name, default):
    return float(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


S_FROM, S_TO = opt("--from", 960.0), opt("--to", 1240.0)
outp = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
sys.path.insert(0, str(air / "tools"))
import expansion_pieces as ep  # noqa: E402

ISLAND = "MD13"
REF = [(930.0, 985.0), (1215.0, 1260.0)]   # the island fills its band here (md13_gaps.json: no narrow run, no gap)
STEP_M, REACH_M = 0.25, 3.0
GUARD_M, FAR_M = 1.5, 5.0
CORE_IN_M = 1.0
CUT = 0.25
MASK_SHARE = 0.25
WINDOW_M = 10.0
CANOPY_G_MINUS_R, SHADOW_SHARE, SHADOW_REF_LUM = 5.0, 0.72, 131.7   # tools/measure_median_tone.py; md_bins_50m.json

LM = air / "tracks" / "san-diego-lake-murray"
doc, pieces = ep.load(LM / "data" / "expansion.north.json")
pc = pieces["C"]
m = next(x for x in doc["medians"] if x["id"] == ISLAND)
ring = m["polygon_xz"]
n = len(ring) // 2
step = (m["s_to"] - m["s_from"]) / (n - 1)
g = json.loads(Path(georef).read_text(encoding="utf-8"))
o = doc["frame"]["origin"]
lat0, lon0 = float(o["lat"]), float(o["lon"])
phi = math.radians(lat0)
m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
Image.MAX_IMAGE_PIXELS = None
PX = Image.open(mosaic).convert("RGB").load()


def pixel(E, N):
    lon = lon0 + E / m_lon
    lat = math.radians(lat0 + N / m_lat)
    tx = (lon + 180.0) / 360.0 * 2 ** g["z"]
    ty = (1.0 - math.log(math.tan(lat) + 1.0 / math.cos(lat)) / math.pi) / 2.0 * 2 ** g["z"]
    return PX[int((tx - g["x0"]) * 256.0), int((ty - g["y0"]) * 256.0)]


def median(v):
    v = sorted(v)
    return v[len(v) // 2] if len(v) % 2 else 0.5 * (v[len(v) // 2 - 1] + v[len(v) // 2])


def station(k):
    """the samples across station k: [(piece-frame offset, R - G, masked)], the band's two faces in the piece frame"""
    a, b = ring[k], ring[2 * n - 1 - k]
    s = m["s_from"] + k * step
    (px_, pz_), _t, nl = pc.frame(s)
    la = (a[0] - px_) * nl[0] + (a[1] - pz_) * nl[1]          # lateral of each ring side, + = left
    lb = (b[0] - px_) * nl[0] + (b[1] - pz_) * nl[1]
    lo, hi = min(la, lb), max(la, lb)
    out = []
    x = lo - REACH_M - FAR_M
    while x <= hi + REACH_M + FAR_M + 1e-9:
        r, gg, bb = pixel(px_ + nl[0] * x, pz_ + nl[1] * x)
        lum = 0.2126 * r + 0.7152 * gg + 0.0722 * bb
        out.append((round(x, 3), r - gg, (gg - r > CANOPY_G_MINUS_R) or (lum < SHADOW_SHARE * SHADOW_REF_LUM)))
        x += STEP_M
    return s, lo, hi, out


def base_of(lo, hi, samples):
    v = [d for x, d, mk in samples if not mk and (lo - FAR_M <= x <= lo - GUARD_M or hi + GUARD_M <= x <= hi + FAR_M)]
    return median(v) if len(v) >= 8 else None


# the plateau: one number, off the reference stretches
core_vals, ref_rows = [], []
for k in range(n):
    s, lo, hi, smp = station(k)
    if not any(a <= s <= b for a, b in REF):
        continue
    core_vals += [d for x, d, mk in smp if not mk and lo + CORE_IN_M <= x <= hi - CORE_IN_M]
    ref_rows.append(k)
PLATEAU = median(core_vals)
ref_base = median([b for b in (base_of(*station(k)[1:]) for k in ref_rows) if b is not None])
print(f"plateau R - G {PLATEAU:+.1f} over {len(core_vals)} core samples of {len(ref_rows)} reference stations; "
      f"the asphalt beside them {ref_base:+.1f}")


def measure(k):
    s, lo, hi, smp = station(k)
    band = [t for t in smp if lo <= t[0] <= hi]
    masked = sum(1 for t in band if t[2]) / max(1, len(band))
    base = base_of(lo, hi, smp)
    rec = {"s": round(s, 1), "band_left_m": round(hi, 3), "band_right_m": round(lo, 3), "masked_share": round(masked, 2),
           "base": None if base is None else round(base, 1)}
    if base is None or masked > MASK_SHARE:
        rec["used"] = False
        return rec
    win = [(x, d - base) for x, d, mk in smp if lo - REACH_M <= x <= hi + REACH_M]
    need = CUT * (PLATEAU - base)
    peak = max(range(len(win)), key=lambda i: win[i][1])
    if win[peak][1] < need:
        rec.update(used=True, width_m=0.0, centre_m=None, peak=round(win[peak][1], 1))
        return rec
    i0 = i1 = peak
    while i0 > 0 and win[i0 - 1][1] >= need:
        i0 -= 1
    while i1 < len(win) - 1 and win[i1 + 1][1] >= need:
        i1 += 1
    core = win[i0:i1 + 1]
    tot = sum(e for _x, e in core)
    w = tot * STEP_M / (PLATEAU - base)
    c = sum(x * e for x, e in core) / tot
    rec.update(used=True, width_m=round(w, 2), centre_m=round(c, 2), peak=round(win[peak][1], 1),
               left_m=round(c + 0.5 * w, 2), right_m=round(c - 0.5 * w, 2))
    return rec


rows = [measure(k) for k in range(n) if S_FROM - 1e-6 <= m["s_from"] + k * step <= S_TO + 1e-6]
ref = [measure(k) for k in ref_rows]
ref_ok = [r for r in ref if r.get("used") and r.get("width_m")]
dw = sorted(r["width_m"] - (r["band_left_m"] - r["band_right_m"]) for r in ref_ok)
dc = sorted(r["centre_m"] - 0.5 * (r["band_left_m"] + r["band_right_m"]) for r in ref_ok)
check = {"stations": len(ref_ok), "width_minus_declared_m": {"p10": round(dw[len(dw) // 10], 2), "median": round(median(dw), 2),
                                                             "p90": round(dw[(9 * len(dw)) // 10], 2)},
         "centre_minus_declared_m": {"p10": round(dc[len(dc) // 10], 2), "median": round(median(dc), 2),
                                     "p90": round(dc[(9 * len(dc)) // 10], 2)}}
print("the method on the reference stretches (where the island fills its band): " + json.dumps(check))

# windows: the medians of the used stations, every WINDOW_M / 2
knots = []
s = S_FROM
while s <= S_TO + 1e-6:
    near = [r for r in rows if r.get("used") and abs(r["s"] - s) <= 0.5 * WINDOW_M]
    if len(near) >= 2:
        ws = [r["width_m"] for r in near]
        cs = [r["centre_m"] for r in near if r.get("centre_m") is not None]
        knots.append({"s": round(s, 1), "stations": len(near), "width_m": round(median(ws), 2),
                      "centre_m": round(median(cs), 2) if cs else None,
                      "band_centre_m": round(median([0.5 * (r["band_left_m"] + r["band_right_m"]) for r in near]), 2),
                      "band_width_m": round(median([r["band_left_m"] - r["band_right_m"] for r in near]), 2)})
    s += 0.5 * WINDOW_M
print("  s      band (centre, width)   island (centre, width)   stations")
for kn in knots:
    c = "  none" if kn["centre_m"] is None else "%+6.2f" % kn["centre_m"]
    print("  %6.1f   %+6.2f  %5.2f         %s  %5.2f             %d" % (kn["s"], kn["band_centre_m"], kn["band_width_m"], c, kn["width_m"], kn["stations"]))
if outp:
    Path(outp).write_text(json.dumps({
        "_doc": "faces_md.py: " + ISLAND + "'s real width and centre per station of piece C, NAIP 2022 z18 mosaic; piece frame, "
                "+ = left of J3 -> J4 travel (north-west). width = the equivalent width (the excess R - G summed across the "
                "island over the plateau's); centre = the excess's centroid. Settings [invented]: see the script.",
        "settings": {"STEP_M": STEP_M, "REACH_M": REACH_M, "GUARD_M": GUARD_M, "FAR_M": FAR_M, "CORE_IN_M": CORE_IN_M, "CUT": CUT,
                     "MASK_SHARE": MASK_SHARE, "WINDOW_M": WINDOW_M, "REF": REF},
        "plateau_r_minus_g": round(PLATEAU, 1), "asphalt_beside_the_reference_r_minus_g": round(ref_base, 1),
        "check_on_the_reference_stretches": check, "stations": rows, "windows": knots}, indent=0), encoding="utf-8")
