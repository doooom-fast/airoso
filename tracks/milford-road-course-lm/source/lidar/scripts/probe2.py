"""Per item: every return (any class but noise) within REACH of the line, its height over a ground plane fitted ONLY to
class-2 returns OUTSIDE the line's corridor (|off| in [CLEAR, CLEAR+2.5] each side, per ALONG_BIN), so returns ON an
object the classifier called ground still stand out. Prints the offset histogram per height band and class.
python -I probe2.py pts.npz inventory.json ids [CLEAR]"""
import json, math, sys
import numpy as np
from scipy.spatial import cKDTree

pts = np.load(sys.argv[1]); inv = json.load(open(sys.argv[2])); want = sys.argv[3].split(",")
CLEAR = float(sys.argv[4]) if len(sys.argv) > 4 else 1.5
LAT0, LON0 = 42.56999810653583, -83.66362827905016
phi = math.radians(LAT0)
m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
e, n, z, cls = pts["e"].astype(float), pts["n"].astype(float), pts["z"].astype(float), pts["cls"]
T = cKDTree(np.c_[e, n]); REACH = float(__import__("os").environ.get("REACH", "5")); ALONG_BIN = 6.0


def local(ll):
    return np.array([[(lo - LON0) * m_lon, (la - LAT0) * m_lat] for lo, la in ll])


def frame(poly, q):
    best = np.full(len(q), np.inf); al = np.zeros(len(q)); off = np.zeros(len(q)); s0 = 0.0
    for a, b in zip(poly, poly[1:]):
        d = b - a; L = np.hypot(*d); u = d / L
        t = np.clip(((q - a) @ u), 0, L); p = a + t[:, None] * u
        dist = np.hypot(*(q - p).T)
        sgn = np.sign(u[0] * (q[:, 1] - a[1]) - u[1] * (q[:, 0] - a[0]))
        bt = dist < best; best[bt] = dist[bt]; al[bt] = s0 + t[bt]; off[bt] = (sgn * dist)[bt]; s0 += L
    return al, off, s0


def run(it):
    poly = local(it["polyline_lonlat"])
    c0 = poly.mean(0); r = np.max(np.hypot(*(poly - c0).T)) + REACH + 1
    ids = np.array(T.query_ball_point(c0, r=r))
    al, off, L = frame(poly, np.c_[e[ids], n[ids]])
    ok = (np.abs(off) <= REACH) & (al > 0.5) & (al < L - 0.5) & ~np.isin(cls[ids], (7, 18))
    ids, al, off = ids[ok], al[ok], off[ok]
    zz, cc = z[ids], cls[ids]
    h = np.full(len(ids), np.nan)
    for b0 in np.arange(0, L, ALONG_BIN):
        m = (al >= b0) & (al < b0 + ALONG_BIN)
        g = m & (cc == 2) & (np.abs(off) >= CLEAR) & (np.abs(off) <= CLEAR + 2.5)
        if g.sum() < 5:
            continue
        A = np.c_[np.ones(g.sum()), al[g] - b0, off[g]]
        co = np.linalg.lstsq(A, zz[g], rcond=None)[0]
        for _ in range(2):
            res = zz[g] - A @ co; k = np.abs(res) < max(0.08, 2.5 * res.std())
            if k.sum() < 5: break
            co = np.linalg.lstsq(A[k], zz[g][k], rcond=None)[0]
        h[m] = zz[m] - (co[0] + co[1] * (al[m] - b0) + co[2] * off[m])
    return ids, al, off, h, cc, L


if __name__ == "__main__":
    for it in inv["items"]:
        if it["id"] not in want or "polyline_lonlat" not in it:
            continue
        ids, al, off, h, cc, L = run(it)
        print(f"\n== {it['id']} L={L:.0f} returns {len(ids)}  (rows: offset bin; cols: height band, g=class2 / o=other)")
        bands = [(-0.15, 0.15), (0.15, 0.35), (0.35, 0.55), (0.55, 0.75), (0.75, 0.95), (0.95, 1.3), (1.3, 2.0), (2.0, 4), (4, 8), (8, 40)]
        print("   off " + "".join(f"{a:>6.2f}+" for a, b in bands))
        for b0 in np.arange(-REACH, REACH, 0.5):
            m = (off >= b0) & (off < b0 + 0.5)
            row = []
            for a, b in bands:
                mm = m & (h >= a) & (h < b)
                row.append(f"{int((mm & (cc == 2)).sum()):3d}/{int((mm & (cc != 2)).sum()):<3d}")
            print(f"  {b0:+4.1f} " + "".join(row))
