"""college_strip.png: College Ave straightened, v800 (left) to v1560 (right), west on top.
Top: the NAIP 2022 aerial (0.6 m) sampled at every lidar cell. Bottom: measured height minus the line's, with the
edges of the road as built in black. Run with Blender's python (numpy) after college_sections.py; labels need Pillow
(college_strip_labels.py). NAIP crops: tools/naip_carriageways.py's cache in the Lake Murray frame."""
import json, struct, sys, zlib
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
CACHE = Path(sys.argv[1])
L = json.loads((HERE / "college_xsec.lidar.g10.json").read_text(encoding="utf-8"))
off = np.array(L["offsets_m"]); st = L["stations"]
H = np.array([[np.nan if v is None else v for v in row] for row in L["h_navd88_m"]], float) - 100.8
H[(np.array(L["flags"], int) & 17) > 0] = np.nan
B = np.load(HERE / "college_built_y.npy")
X = np.array(st["x"]); Z = np.array(st["z"]); NX = np.array(st["nx"]); NZ = np.array(st["nz"]); YL = np.array(st["y_line"])
T, PX = 600.0, 1000
tiles = {}
def tile(i, j):
    if (i, j) not in tiles:
        f = CACHE / f"naip_{i}_{j}.npy"
        tiles[(i, j)] = np.load(f) if f.exists() else None
    return tiles[(i, j)]
ns, no = H.shape
rgb = np.zeros((ns, no, 3), np.uint8); nir = np.zeros((ns, no), np.float32)
for i in range(ns):
    for j in range(no):
        x, z = X[i] + off[j] * NX[i], Z[i] + off[j] * NZ[i]
        ti, tj = int(np.floor(x / T)), int(np.floor(z / T)); a = tile(ti, tj)
        if a is None: continue
        c = min(PX - 1, max(0, int((x - ti * T) / 0.6))); r = min(PX - 1, max(0, int((tj * T + T - z) / 0.6)))
        rgb[i, j] = a[:3, r, c]; nir[i, j] = a[3, r, c]
np.save(HERE / "college_naip_rgbn.npy", np.dstack([rgb, nir[..., None].astype(np.uint8)]))
dh = H - YL[:, None]
def ramp(v):                      # -2 m blue .. 0 white .. +6 m red
    out = np.zeros(v.shape + (3,), np.uint8)
    t = np.clip(v, -2, 6)
    neg = t < 0; pos = ~neg
    out[neg] = np.stack([255 + t[neg] / 2 * 215, 255 + t[neg] / 2 * 150, np.full(neg.sum(), 255)], 1).astype(np.uint8)
    out[pos] = np.stack([np.full(pos.sum(), 255), 255 - t[pos] / 6 * 215, 255 - t[pos] / 6 * 215], 1).astype(np.uint8)
    out[np.isnan(v)] = (120, 120, 120)
    return out
hm = ramp(dh)
bm = ~np.isnan(B)
for i in range(ns):                # the built road's edges and the line
    k = np.where(bm[i])[0]
    if len(k):
        hm[i, k[0]] = (0, 0, 0); hm[i, k[-1]] = (0, 0, 0); rgb[i, k[0]] = (255, 255, 0); rgb[i, k[-1]] = (255, 255, 0)
SX, SY = 2, 4
def panel(a):                      # stations along x, + offset (west) on top
    p = np.transpose(a, (1, 0, 2))[::-1]
    return np.repeat(np.repeat(p, SY, axis=0), SX, axis=1)
img = np.vstack([panel(rgb), np.full((16, ns * SX, 3), 255, np.uint8), panel(hm)])
def png(path, a):
    h, w, _ = a.shape
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(h))
    def ch(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw, 6)) + ch(b"IEND", b""))
png(HERE / "college_strip_raw.png", img)
print("strip", img.shape, "| NAIP cells without image:", int((rgb.sum(axis=2) == 0).sum()))
