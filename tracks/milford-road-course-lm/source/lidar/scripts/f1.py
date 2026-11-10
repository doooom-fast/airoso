"""F1: the tall linear structure along the NW boundary, measured off the lidar.
Seeds: non-ground returns 1.4-6 m over ground, no canopy-wide spread, within SEED_R of the NAIP F1 line. Fits a line
through them (per BIN_M along, the median position), then per bin: top (p90 / max height of returns within HALF_W of
the line), plan width (p5-p95 perpendicular), the returns' return-number structure, intensity, and the vertical fill.
Writes f1.json (+ the fitted line in lon/lat).   python -I f1.py pts.npz hag.npz inventory.json out.json"""
import json, math, sys
import numpy as np
from scipy.spatial import cKDTree

pts = np.load(sys.argv[1]); hag = np.load(sys.argv[2])["hag"]; inv = json.load(open(sys.argv[3])); OUT = sys.argv[4]
LAT0, LON0 = 42.56999810653583, -83.66362827905016
phi = math.radians(LAT0)
m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
e, n, cls, rn, nr, I = (pts[k] for k in ("e", "n", "cls", "rn", "nr", "inten"))
e = e.astype(float); n = n.astype(float)
ok = ~np.isin(cls, (7, 18)) & np.isfinite(hag)
it = next(i for i in inv["items"] if i["id"] == "F1")
L0 = np.array([[(lo - LON0) * m_lon, (la - LAT0) * m_lat] for lo, la in it["polyline_lonlat"]])
SEED_R, BIN_M, HALF_W = 14.0, 4.0, 0.9


def frame(poly, q):
    best = np.full(len(q), np.inf); al = np.zeros(len(q)); off = np.zeros(len(q)); s0 = 0.0
    for a, b in zip(poly, poly[1:]):
        d = b - a; L = np.hypot(*d); u = d / L
        t = np.clip(((q - a) @ u), -50, L + 50) if False else np.clip(((q - a) @ u), 0, L)
        p = a + t[:, None] * u; dist = np.hypot(*(q - p).T)
        sgn = np.sign(u[0] * (q[:, 1] - a[1]) - u[1] * (q[:, 0] - a[0]))
        bt = dist < best; best[bt] = dist[bt]; al[bt] = s0 + t[bt]; off[bt] = (sgn * dist)[bt]; s0 += L
    return al, off, s0


T = cKDTree(np.c_[e, n])
c0 = L0.mean(0); ids = np.array(T.query_ball_point(c0, r=float(np.max(np.hypot(*(L0 - c0).T)) + SEED_R + 40)))
ids = ids[ok[ids]]
al, off, L = frame(L0, np.c_[e[ids], n[ids]])
seed = (np.abs(off) <= SEED_R) & (cls[ids] != 2) & (hag[ids] >= 2.0) & (hag[ids] <= 4.6)
# no canopy: drop seeds with a return over CANOPY within 1.5 m in plan (trees beside the line), then keep the largest
# chain (link 3 m): the structure, not the shrubs
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
CANOPY = 5.0
hi = ids[(cls[ids] != 2) & (hag[ids] > CANOPY)]
Th = cKDTree(np.c_[e[hi], n[hi]])
sid = np.where(seed)[0]
clear = np.array([len(x) == 0 for x in Th.query_ball_point(np.c_[e[ids[sid]], n[ids[sid]]], r=1.5)])
sid = sid[clear]
Q = np.c_[e[ids[sid]], n[ids[sid]]]
pr = cKDTree(Q).query_pairs(3.0, output_type="ndarray")
nc, lab = connected_components(coo_matrix((np.ones(len(pr)), (pr[:, 0], pr[:, 1])), shape=(len(sid), len(sid))), directed=False)
big = np.bincount(lab).argmax()
seed = np.zeros(len(ids), bool); seed[sid[lab == big]] = True
print("seed chain", int(seed.sum()), "of", len(lab), "components", nc)
# fitted line: per bin the median position of the 2.5-6 m returns, after rejecting the bin's outliers
S = ids[seed]; A = al[seed]
line = []
for b0 in np.arange(-20, L + 20, BIN_M):
    m = (A >= b0) & (A < b0 + BIN_M)
    if m.sum() < 3:
        continue
    q = np.c_[e[S[m]], n[S[m]]]; med = np.median(q, 0)
    k = np.hypot(*(q - med).T) < 3.0
    if k.sum() >= 3:
        line.append(np.median(q[k], 0))
line = np.array(line)
# extend the walk past the NAIP line's ends: follow seeds chained from the fitted ends (none expected; reported)
al2, off2, L2 = frame(line, np.c_[e[ids], n[ids]])
near = np.abs(off2) <= HALF_W
rows = []
for b0 in np.arange(0, L2, BIN_M):
    m = near & (al2 >= b0) & (al2 < b0 + BIN_M)
    st = m & (cls[ids] != 2) & (hag[ids] >= 0.3)
    if st.sum() < 2:
        rows.append({"a": round(b0, 1), "n": int(st.sum())}); continue
    h = hag[ids][st]; o = off2[st]
    top = h[h >= 1.5]
    rows.append({"a": round(b0, 1), "n": int(st.sum()), "top_p90": round(float(np.percentile(top, 90)), 2) if len(top) >= 2 else None,
                 "top_max": round(float(h.max()), 2), "top_med": round(float(np.median(top)), 2) if len(top) else None,
                 "frac_mid_0p3_to_2": round(float(((h >= 0.3) & (h < 2.0)).mean()), 2)})
st = near & (cls[ids] != 2) & (hag[ids] >= 0.3)
h = hag[ids][st]; o = off2[st]; R = rn[ids][st]; NR = nr[ids][st]; II = I[ids][st].astype(float)
top = st.copy(); top[st] = h >= 2.5
gi = I[ids][near & (cls[ids] == 2)].astype(float)
summ = {
    "lidar": "USGS_LPC_MI_31Co_Oakland_2016_LAS_2019 EPT, flown 2017-05-03 (GPS time)",
    "fitted_length_m": round(float(L2), 1), "naip_line_length_m": round(float(L), 1),
    "returns_on_structure_0p3_up": int(st.sum()), "per_m": round(float(st.sum() / L2), 2),
    "top_m": {"p10": round(float(np.percentile(h[h >= 2.5], 10)), 2), "p50": round(float(np.percentile(h[h >= 2.5], 50)), 2),
              "p90": round(float(np.percentile(h[h >= 2.5], 90)), 2), "max": round(float(h.max()), 2)},
    "plan_width_p5_p95_m_of_top_returns": round(float(np.percentile(off2[top], 95) - np.percentile(off2[top], 5)), 2),
    "plan_offset_sd_m_of_top_returns": round(float(off2[top].std()), 2),
    "frac_returns_0p3_to_2m": round(float(((h >= 0.3) & (h < 2.0)).mean()), 3),
    "top_returns_single_pulse_frac": round(float((NR[h >= 2.5] == 1).mean()), 3),
    "top_returns_first_of_many_frac": round(float(((R == 1) & (NR > 1))[h >= 2.5].mean()), 3),
    "top_intensity_median": float(np.median(II[h >= 2.5])), "ground_intensity_median_within_0p9m": float(np.median(gi)),
    "bins_with_a_top": int(sum(1 for r in rows if r.get("top_p90"))), "bins": len(rows),
}
lonlat = [[round(LON0 + p[0] / m_lon, 7), round(LAT0 + p[1] / m_lat, 7)] for p in line]
json.dump({"summary": summ, "line_lonlat": lonlat, "bins": rows}, open(OUT, "w"), indent=1)
print(json.dumps(summ, indent=1))
for r in rows:
    print(r)
