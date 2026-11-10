"""f1.json -> the config's F1 rails entries: the fitted line smoothed (3-point mean, ends kept), split where the top steps
(the bins' p90 top), each piece's height = the median of its bins' p90 tops. Prints JSON."""
import json, math, sys
import numpy as np
f = json.load(open(sys.argv[1]))
L = np.array(f["line_lonlat"], float)
S = L.copy(); S[1:-1] = (L[:-2] + L[1:-1] + L[2:]) / 3
LAT0 = 42.57; mlon = 111320 * math.cos(math.radians(LAT0)); mlat = 110540
xy = np.c_[S[:, 0] * mlon, S[:, 1] * mlat]
s = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
bins = [b for b in f["bins"] if b.get("top_p90") is not None]
cuts = [(0.0, 112.0, "ne"), (112.0, 132.0, "step"), (132.0, 1e9, "sw")]
out = []
for a0, a1, tag in cuts:
    idx = [i for i in range(len(S)) if a0 - 2.1 <= s[i] <= a1 + 2.1]
    tops = [b["top_p90"] for b in bins if a0 <= b["a"] < a1]
    h = round(float(np.median(tops)), 2)
    out.append({"tag": tag, "a": [a0, min(a1, float(s[-1]))], "len_m": round(float(s[idx[-1]] - s[idx[0]]), 1), "bins": len(tops),
                "top_p90_range": [min(tops), max(tops)], "height_m": h,
                "polyline_lonlat": [[round(float(x), 7), round(float(y), 7)] for x, y in S[idx]]})
for o in out:
    print(o["tag"], o["a"], o["len_m"], o["bins"], o["top_p90_range"], o["height_m"], len(o["polyline_lonlat"]))
json.dump(out, open(sys.argv[2], "w"))
