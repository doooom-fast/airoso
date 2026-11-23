"""College Ave v1100-1520: the real road's four pavement edges and their heights at every centreline vertex
(ledger 0055 "Bounded proof" step 2: "Register the real carriageway edges and elevations in the engine frame").

    <blender python> college_edges.py          (after college_sections.py and college_strip.py)

Reads the lidar cells, the NAIP cells college_strip.py sampled (college_naip_rgbn.npy) and the built road
(college_built_y.npy). Per station, in offsets (+ = west on College northbound):
  the MIDDLE = the cells between the carriageways that are not road: bank (cross slope over BANK_SLOPE) or planted
  (NDVI at or over VEG_NDVI), the widest such run within MID_REACH_M of the built road's centre, grown outward;
  SB = pavement west of the middle, NB = pavement east of it; each runs out to its OUTER edge = the last road cell
  before OUT_BREAK_M of planted / steep / no lidar (so shadow, paint and cars do not end the road).
Then every edge is taken as a running median over SMOOTH_ST stations. Nothing here changes the build.
Writes college_edges.json and draws the edges on college_strip_raw.png -> college_edges_raw.png."""
import json
import struct
import zlib
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
VEG_NDVI = 0.12       # tools/naip_carriageways.py's [invented] vegetation threshold
BANK_SLOPE = 0.10     # [invented] steeper than any carriageway crossfall
MID_REACH_M = 9.0     # [invented] the middle is looked for within this of the built road's centre
OUT_BREAK_M = 1.5     # [invented] this much not-road ends a carriageway
MIN_MID_M = 1.0       # [invented] a narrower middle is "no island here"
SMOOTH_ST = 9         # stations (about 27 m) in the running median
V0, V1 = 1100, 1520

L = json.loads((HERE / "college_xsec.lidar.g10.json").read_text(encoding="utf-8"))
off = np.array(L["offsets_m"])
st = L["stations"]
V = np.array(st["v"])
YL = np.array(st["y_line"])
H = np.array([[np.nan if v is None else v for v in row] for row in L["h_navd88_m"]], float) - 100.8
H[(np.array(L["flags"], int) & 17) > 0] = np.nan
B = np.load(HERE / "college_built_y.npy")
N = np.load(HERE / "college_naip_rgbn.npy").astype(np.float32)
ndvi = (N[..., 3] - N[..., 0]) / np.maximum(1.0, N[..., 3] + N[..., 0])
no = len(off)
step = off[1] - off[0]


def slope(h):
    s = np.full(no, np.nan)
    for j in range(no):
        a, b = max(0, j - 2), min(no - 1, j + 2)
        if not (np.isnan(h[a]) or np.isnan(h[b])):
            s[j] = (h[b] - h[a]) / (off[b] - off[a])
    return s


rows = []
for i in np.where((V >= V0) & (V <= V1))[0]:
    h = H[i]
    s = slope(h)
    notroad = (ndvi[i] >= VEG_NDVI) | (np.abs(s) > BANK_SLOPE)
    bm = np.where(~np.isnan(B[i]))[0]
    c = 0.5 * (off[bm[0]] + off[bm[-1]]) if len(bm) else 0.0
    near = np.where((np.abs(off - c) <= MID_REACH_M) & notroad)[0]
    r = {"v": int(V[i]), "y_line": float(YL[i]), "built_from_m": float(off[bm[0]]) if len(bm) else None,
         "built_to_m": float(off[bm[-1]]) if len(bm) else None}
    if len(near):
        runs = []
        a = p = near[0]
        for k in near[1:]:
            if k != p + 1:
                runs.append((a, p))
                a = k
            p = k
        runs.append((a, p))
        a, b = max(runs, key=lambda t: t[1] - t[0])
        while a > 0 and notroad[a - 1]:
            a -= 1
        while b < no - 1 and notroad[b + 1]:
            b += 1
        if off[b] - off[a] >= MIN_MID_M and a > 0 and b < no - 1:
            r["mid_east_m"], r["mid_west_m"] = float(off[a]), float(off[b])

    def outer(start, d):
        last = None
        bad = 0
        k = start
        while 0 <= k < no:
            if notroad[k] or np.isnan(h[k]):
                bad += 1
                if bad * step >= OUT_BREAK_M:
                    break
            else:
                bad = 0
                last = k
            k += d
        return last

    if "mid_east_m" in r:
        ke = int(round((r["mid_east_m"] - off[0]) / step))
        kw = int(round((r["mid_west_m"] - off[0]) / step))
        oe, ow = outer(ke - 1, -1), outer(kw + 1, +1)
        if oe is not None:
            r["nb_outer_m"], r["nb_inner_m"] = float(off[oe]), float(off[ke - 1])
        if ow is not None:
            r["sb_inner_m"], r["sb_outer_m"] = float(off[kw + 1]), float(off[ow])
    rows.append(r)

KEYS = ("nb_outer_m", "nb_inner_m", "sb_inner_m", "sb_outer_m")


def smooth(key):
    vals = np.array([r.get(key, np.nan) for r in rows], float)
    out = vals.copy()
    hw = SMOOTH_ST // 2
    for k in range(len(vals)):
        w = vals[max(0, k - hw):k + hw + 1]
        w = w[~np.isnan(w)]
        out[k] = np.median(w) if len(w) >= 3 else np.nan
    return out


SM = {k: smooth(k) for k in KEYS}
idx = {int(v): i for i, v in enumerate(V)}


def y_at(i, o):
    if np.isnan(o):
        return None
    j = int(round((o - off[0]) / step))
    w = H[i, max(0, j - 1):j + 2]
    w = w[~np.isnan(w)]
    return round(float(np.median(w)), 3) if len(w) else None


for k, r in enumerate(rows):
    i = idx[r["v"]]
    for key in KEYS:
        o = SM[key][k]
        r[key.replace("_m", "_smooth_m")] = None if np.isnan(o) else round(float(o), 2)
        inside = 0.5 if key in ("nb_outer_m", "sb_inner_m") else -0.5        # half a metre inside the pavement
        r[key.replace("_m", "_y")] = y_at(i, o + inside)
    a, b, c, d = (SM[x][k] for x in KEYS)
    if not np.isnan([a, b, c, d]).any():
        r["nb_width_m"] = round(float(b - a), 1)
        r["mid_width_m"] = round(float(c - b), 1)
        r["sb_width_m"] = round(float(d - c), 1)
        if r["nb_inner_y"] is not None and r["sb_inner_y"] is not None:
            r["nb_over_sb_m"] = round(r["nb_inner_y"] - r["sb_inner_y"], 2)

(HERE / "college_edges.json").write_text(json.dumps({
    "what": "College Ave: the real road's pavement edges and heights per centreline vertex (measured; edges smoothed over 9 stations)",
    "offset_sign": "+ = left of travel = west on College northbound; heights = engine y (NAVD88 - 100.8), half a metre inside each edge",
    "params": {"VEG_NDVI": VEG_NDVI, "BANK_SLOPE": BANK_SLOPE, "MID_REACH_M": MID_REACH_M, "OUT_BREAK_M": OUT_BREAK_M,
               "MIN_MID_M": MIN_MID_M, "SMOOTH_ST": SMOOTH_ST, "_doc": "[invented]"},
    "stations": rows}, indent=1), encoding="utf-8")

print("v     NB outer..inner (w) | middle | SB inner..outer (w) | NB over SB | built")
for r in rows[::20]:
    def g(k):
        return "  -  " if r.get(k) is None else f"{r[k]:+5.1f}"
    print(f"{r['v']:5d} {g('nb_outer_smooth_m')}..{g('nb_inner_smooth_m')} ({r.get('nb_width_m', '-')}) | {r.get('mid_width_m', '-')} | "
          f"{g('sb_inner_smooth_m')}..{g('sb_outer_smooth_m')} ({r.get('sb_width_m', '-')}) | {r.get('nb_over_sb_m', '-')} | "
          f"{r['built_from_m']}..{r['built_to_m']}")
has = [r for r in rows if r.get("mid_width_m")]
print(f"stations with all four edges: {len(has)} of {len(rows)}" + (f" (v{has[0]['v']}..v{has[-1]['v']})" if has else ""))

# --- the edges drawn on the strip ----------------------------------------------------------------------------------------
raw = (HERE / "college_strip_raw.png").read_bytes()
pos = 8
ihdr = None
dat = b""
while pos < len(raw):
    n = struct.unpack(">I", raw[pos:pos + 4])[0]
    tag = raw[pos + 4:pos + 8]
    body = raw[pos + 8:pos + 8 + n]
    if tag == b"IHDR":
        ihdr = struct.unpack(">IIBBBBB", body)
    elif tag == b"IDAT":
        dat += body
    pos += 12 + n
w, hgt = ihdr[0], ihdr[1]
px = np.frombuffer(zlib.decompress(dat), np.uint8).reshape(hgt, w * 3 + 1)[:, 1:].reshape(hgt, w, 3).copy()
SX, SY = 2, 4
PAN = no * SY
COL = {"nb_outer_m": (255, 60, 60), "nb_inner_m": (255, 160, 0), "sb_inner_m": (0, 220, 255), "sb_outer_m": (60, 120, 255)}
for k, r in enumerate(rows):
    x = (r["v"] - 800) * SX
    for key, col in COL.items():
        o = SM[key][k]
        if np.isnan(o):
            continue
        yy = int(round((30 - o) / step)) * SY
        for base in (0, PAN + 16):
            px[base + yy:base + yy + 3, x:x + SX] = col
rawb = b"".join(bytes([0]) + px[y].tobytes() for y in range(hgt))


def chunk(tag, body):
    return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xffffffff)


(HERE / "college_edges_raw.png").write_bytes(bytes([0x89]) + b"PNG" + bytes([13, 10, 26, 10]) +
                                             chunk(b"IHDR", struct.pack(">IIBBBBB", w, hgt, 8, 2, 0, 0, 0)) +
                                             chunk(b"IDAT", zlib.compress(rawb, 6)) + chunk(b"IEND", b""))
