"""College Ave, real against built (ledger 0055 "Bounded proof" step 2): the measured cross-section at every centreline
vertex v800-1560 (college_xsec.lidar.g10.json: USGS D24 lidar, class 2, read by the G10) beside the road AS BUILT in
Lake Murray 0.20.2 (the gate OBJ of the installed kn5s).

    <blender python> college_sections.py <gate track.obj> [out dir]

Writes college_sections.json: per station the BENCHES (runs of measured ground at least BENCH_MIN_M wide whose
cross slope stays under BENCH_SLOPE: the paved carriageways and any other flat strip), the built road's extent and
height, and built minus measured across the built road. Nothing is smoothed or filled: an empty lidar cell breaks a run.
Offsets: + = left of the line's travel (west on College northbound). Heights: engine y = NAVD88 - 100.8."""
import json, sys, collections
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
BENCH_SLOPE = 0.08     # [invented] |cross slope| a paved lane stays under (8 % = the steepest superelevation expected)
BENCH_MIN_M = 6.0      # [invented] narrower than two lanes is not a carriageway
SLOPE_WIN = 3          # cells (1.5 m) the cross slope is taken over
ELEV0 = 100.8

L = json.loads((HERE / "college_xsec.lidar.g10.json").read_text(encoding="utf-8"))
off = np.array(L["offsets_m"]); st = L["stations"]
H = np.array([[np.nan if v is None else v for v in row] for row in L["h_navd88_m"]], float) - ELEV0
FL = np.array(L["flags"], int)
H[(FL & (1 | 16)) > 0] = np.nan                      # empty or spike cells are no data
V = np.array(st["v"]); X = np.array(st["x"]); Z = np.array(st["z"]); NX = np.array(st["nx"]); NZ = np.array(st["nz"])
YL = np.array(st["y_line"])

# --- the built road at the same cells ---------------------------------------------------------------------------------
obj = Path(sys.argv[1]); verts = []; faces = []; cur = None
for line in obj.open(encoding="ascii", errors="replace"):
    if line.startswith("o "): cur = line[2:].strip()
    elif line.startswith("v "): verts.append(tuple(map(float, line.split()[1:4])))
    elif line.startswith("f ") and cur and cur.startswith("1ROAD"):
        faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:4]])
verts = np.array(verts)
bx0, bx1, bz0, bz1 = X.min() - 80, X.max() + 80, Z.min() - 80, Z.max() + 80
cell = 8.0; grid = collections.defaultdict(list); tris = []
for f in faces:
    t = verts[f]
    if t[:, 0].max() < bx0 or t[:, 0].min() > bx1 or t[:, 2].max() < bz0 or t[:, 2].min() > bz1: continue
    k = len(tris); tris.append(t)
    for i in range(int(t[:, 0].min() // cell), int(t[:, 0].max() // cell) + 1):
        for j in range(int(t[:, 2].min() // cell), int(t[:, 2].max() // cell) + 1):
            grid[(i, j)].append(k)
def built_y(x, z):
    best = np.nan
    for k in grid.get((int(x // cell), int(z // cell)), ()):
        (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = tris[k]
        d = (z2 - z3) * (x1 - x3) + (x3 - x2) * (z1 - z3)
        if abs(d) < 1e-12: continue
        a = ((z2 - z3) * (x - x3) + (x3 - x2) * (z - z3)) / d
        b = ((z3 - z1) * (x - x3) + (x1 - x3) * (z - z3)) / d
        if a >= -1e-6 and b >= -1e-6 and a + b <= 1 + 1e-6:
            y = a * y1 + b * y2 + (1 - a - b) * y3
            best = y if np.isnan(best) else max(best, y)
    return best
B = np.full(H.shape, np.nan)
for i in range(len(V)):
    for j, o in enumerate(off):
        B[i, j] = built_y(X[i] + o * NX[i], Z[i] + o * NZ[i])

# --- benches ----------------------------------------------------------------------------------------------------------
def benches(h):
    out = []; n = len(h); ok = np.zeros(n, bool)
    for j in range(n):
        a, b = max(0, j - SLOPE_WIN), min(n - 1, j + SLOPE_WIN)
        if np.isnan(h[j]) or np.isnan(h[a]) or np.isnan(h[b]): continue
        ok[j] = abs((h[b] - h[a]) / (off[b] - off[a])) <= BENCH_SLOPE
    j = 0
    while j < n:
        if not ok[j]: j += 1; continue
        k = j
        while k + 1 < n and ok[k + 1]: k += 1
        if off[k] - off[j] >= BENCH_MIN_M:
            p = np.polyfit(off[j:k + 1], h[j:k + 1], 1)
            out.append({"from_m": float(off[j]), "to_m": float(off[k]), "width_m": float(off[k] - off[j]),
                        "y_mid": round(float(np.polyval(p, (off[j] + off[k]) / 2)), 3), "cross_slope": round(float(p[0]), 4)})
        j = k + 1
    return out

rows = []
for i in range(len(V)):
    bm = ~np.isnan(B[i])
    bl = benches(H[i])
    d = (B[i] - H[i])[bm & ~np.isnan(H[i])]
    row = {"v": int(V[i]), "s_m": st["s_m"][i], "y_line": float(YL[i]), "benches": bl,
           "built": None if not bm.any() else {"from_m": float(off[bm][0]), "to_m": float(off[bm][-1]),
                                               "y_min": round(float(np.nanmin(B[i])), 3), "y_max": round(float(np.nanmax(B[i])), 3)},
           "built_minus_measured_m": None if not len(d) else {"min": round(float(d.min()), 2), "median": round(float(np.median(d)), 2),
                                                              "max": round(float(d.max()), 2), "cells": int(len(d))}}
    if len(bl) >= 2:
        hi = max(bl, key=lambda b: b["y_mid"]); lo = min(bl, key=lambda b: b["y_mid"])
        row["bench_step_m"] = round(hi["y_mid"] - lo["y_mid"], 2)
    rows.append(row)
out = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE
(out / "college_sections.json").write_text(json.dumps({
    "what": "College Ave v800-1560: measured benches against the road as built in 0.20.2", "obj": obj.name,
    "params": {"BENCH_SLOPE": BENCH_SLOPE, "BENCH_MIN_M": BENCH_MIN_M, "SLOPE_WIN_cells": SLOPE_WIN, "_doc": "[invented]"},
    "offset_sign": "+ = left of travel (west on College northbound)", "stations": rows}, indent=1), encoding="utf-8")
np.save(out / "college_built_y.npy", B.astype(np.float32))
print("v     benches (from..to m @ y - y_line) | built from..to | built - measured min/med/max | step")
for r in rows[::20]:
    bt = "; ".join(f"{b['from_m']:+.0f}..{b['to_m']:+.0f} @ {b['y_mid'] - r['y_line']:+.1f}" for b in r["benches"]) or "-"
    bu = r["built"]; dm = r["built_minus_measured_m"]
    print(f"{r['v']:5d} {bt:58} | " + (f"{bu['from_m']:+.0f}..{bu['to_m']:+.0f}" if bu else "   -   ") + " | " +
          (f"{dm['min']:+.1f} / {dm['median']:+.1f} / {dm['max']:+.1f}" if dm else "-") + f" | {r.get('bench_step_m', '')}")
st2 = [r for r in rows if r.get("bench_step_m", 0) >= 1.0]
print(f"stations with two benches >= 1.0 m apart in height: {len(st2)} of {len(rows)}" + (f" (v{st2[0]['v']}..v{st2[-1]['v']})" if st2 else ""))
