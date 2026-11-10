"""NAIP 2022 tone across the lidar F1 line: mean RGB in 0.5 m offset bins from -6 to +6 m, every vertex (sun side = SE)."""
import json, math, sys
import numpy as np
from PIL import Image
A = np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(float)
f = json.load(open(sys.argv[2]))
LON0, LON1, LAT0, LAT1, W, H = -83.6700, -83.6570, 42.56050, 42.57950, 2130, 3112
LATc = 42.57; MLON = 111320.0 * math.cos(math.radians(LATc)); MLAT = 110540.0
L = np.array(f["line_lonlat"])
xy = np.c_[(L[:, 0] - LON0) * MLON, (L[:, 1] - LAT0) * MLAT]
prof = {}
for i in range(1, len(xy) - 1):
    d = xy[i + 1] - xy[i - 1]; d /= np.hypot(*d); nrm = np.array([d[1], -d[0]])   # + = right of the line's order
    for o in np.arange(-6, 6.01, 0.5):
        p = xy[i] + nrm * o
        px = p[0] / MLON / (LON1 - LON0) * W - 0.5; py = H - p[1] / MLAT / (LAT1 - LAT0) * H - 0.5
        v = A[int(round(py)), int(round(px))]
        prof.setdefault(round(float(o), 1), []).append(v)
print("line order runs", "NE->SW" if xy[0][1] > xy[-1][1] else "SW->NE", "; + offset = right of it")
for o in sorted(prof):
    m = np.mean(prof[o], 0)
    print(f"{o:+5.1f} R {m[0]:5.1f} G {m[1]:5.1f} B {m[2]:5.1f}  b/r {m[2]/max(m[0],1):.2f}")
