"""scratch, read-only: on a north piece, the share of the BUILT carriageway's photo pixels that do not read as asphalt,
per 50 m of station (ledger 0099 round 3, item 3: the road-wear bake reads its tone at the built road's world place).

    python -I tone_piece.py <airoso> <mosaic.jpg> <georef.json> <piece id> [--bin 50] [--out <json>]

Per 2.5 m station, samples every STEP m across the built carriageway: from the plan's right curb to its left curb, less
EDGE_M at each curb and less the built median (its faces +- EDGE_M). A sample is
  shadow     luminance under SHADOW_LUM x the piece's lit-asphalt median and bluer than SHADOW_BLUE (the bake's own two
             numbers, scripts/aerial/road_wear.DEFAULTS tone: it fills these from lit asphalt, so they are not counted);
  asphalt    grey: max(R, G, B) - min(R, G, B) under GREY_SPREAD, and its luminance inside the bake's own clip
             [0.70, 1.30] of the lit median;
  off        anything else: coloured (terracotta, vegetation, dirt), or brighter / darker than the clip (concrete, paint).
The lit median is found by iterating twice from the grey samples. GREY_SPREAD is [invented]."""
import json
import math
import sys
from pathlib import Path
from statistics import median

from PIL import Image

air, mosaic, georef, pid = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
BIN = float(sys.argv[sys.argv.index("--bin") + 1]) if "--bin" in sys.argv else 50.0
STEP, EDGE_M, GREY_SPREAD = 0.5, 0.75, 18
SHADOW_LUM, SHADOW_BLUE, CLIP = 0.72, 1.06, (0.70, 1.30)
sys.path.insert(0, str(air / "tools"))
import expansion_pieces as ep  # noqa: E402

doc, pieces = ep.load(air / "tracks/san-diego-lake-murray/data/expansion.north.json")
pc = pieces[pid]
g = json.loads(Path(georef).read_text(encoding="utf-8"))
o = doc["frame"]["origin"]
lat0, lon0 = float(o["lat"]), float(o["lon"])
phi = math.radians(lat0)
m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
Image.MAX_IMAGE_PIXELS = None
px = Image.open(mosaic).convert("RGB").load()


def pix(E, N):
    lat = math.radians(lat0 + N / m_lat)
    ty = (1.0 - math.log(math.tan(lat) + 1.0 / math.cos(lat)) / math.pi) / 2.0 * 2 ** g["z"]
    tx = (lon0 + E / m_lon + 180.0) / 360.0 * 2 ** g["z"]
    return px[int((tx - g["x0"]) * 256.0), int((ty - g["y0"]) * 256.0)]


s0, s1 = pc.cuts.get("start", {}).get("s", pc.s[0]), pc.cuts.get("end", {}).get("s", pc.s[-1])
samples = []                                   # (s, lateral, r, g, b)
for s in pc.s:
    if not s0 <= s <= s1:
        continue
    (x, z), _t, nl = pc.frame(s)
    L, R = pc.curbs(s)
    w, off = pc.num(s, "median_w_m"), pc.num(s, "median_off_m")
    raised = pc.near(s, "median_type") in ep.RAISED and w > 0
    m = R + EDGE_M
    while m <= L - EDGE_M + 1e-9:
        if not (raised and off - w / 2.0 - EDGE_M <= m <= off + w / 2.0 + EDGE_M):
            samples.append((s, m) + tuple(pix(x + nl[0] * m, z + nl[1] * m)))
        m += STEP


def lum(c):
    return (c[0] + c[1] + c[2]) / 3.0


grey = [c for c in samples if max(c[2:]) - min(c[2:]) < GREY_SPREAD]
ref = median(lum(c[2:]) for c in grey)
for _ in range(2):                             # the lit median: the grey samples inside the clip of the last estimate
    ref = median(lum(c[2:]) for c in grey if CLIP[0] * ref <= lum(c[2:]) <= CLIP[1] * ref)


def kind(c):
    r, gg, b = c[2:]
    v = lum(c[2:])
    if v < SHADOW_LUM * ref and b / max(1.0, r) > SHADOW_BLUE:
        return "shadow"
    if max(r, gg, b) - min(r, gg, b) < GREY_SPREAD and CLIP[0] * ref <= v <= CLIP[1] * ref:
        return "asphalt"
    return "off"


bins = {}
for c in samples:
    k = int(c[0] // BIN)
    d = bins.setdefault(k, {"asphalt": 0, "shadow": 0, "off": 0, "off_left": 0, "off_right": 0, "n_left": 0, "n_right": 0})
    kd = kind(c)
    d[kd] += 1
    side = "left" if c[1] > pc.num(c[0], "median_off_m") else "right"
    d["n_" + side] += 1
    if kd == "off":
        d["off_" + side] += 1
out = []
print(f"piece {pid}: {len(samples)} samples, lit-asphalt median luminance {ref:.1f}; per {BIN:.0f} m: share of the built carriageway's lit samples that do not read as asphalt")
print("   s        samples  shadow   off (of lit)   off left / right (of the side's samples)")
for k in sorted(bins):
    d = bins[k]
    lit = d["asphalt"] + d["off"]
    row = {"s": [k * BIN, (k + 1) * BIN - 2.5], "samples": lit + d["shadow"], "shadow_share": round(d["shadow"] / max(1, lit + d["shadow"]), 3),
           "off_share_of_lit": round(d["off"] / max(1, lit), 3), "off_left": round(d["off_left"] / max(1, d["n_left"]), 3),
           "off_right": round(d["off_right"] / max(1, d["n_right"]), 3)}
    out.append(row)
    print(f"  {row['s'][0]:6.0f}-{row['s'][1]:6.1f}  {row['samples']:5d}   {row['shadow_share']:5.2f}    {row['off_share_of_lit']:5.2f}          {row['off_left']:5.2f} / {row['off_right']:5.2f}")
if "--out" in sys.argv:
    Path(sys.argv[sys.argv.index("--out") + 1]).write_text(json.dumps({
        "_doc": "tone_piece.py: the built carriageway's photo samples that do not read as asphalt, per bin of station",
        "piece": pid, "bin_m": BIN, "params": {"STEP": STEP, "EDGE_M": EDGE_M, "GREY_SPREAD": GREY_SPREAD, "SHADOW_LUM": SHADOW_LUM,
                                               "SHADOW_BLUE": SHADOW_BLUE, "CLIP": list(CLIP), "_doc": "GREY_SPREAD and EDGE_M [invented]; the rest are the bake's"},
        "lit_asphalt_median_luminance": round(ref, 1), "bins": out}, indent=1) + "\n", encoding="utf-8")
