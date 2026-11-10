"""The real pavement edge beside Milford's lap, measured twice: NAIP 2022 and the 2017 lidar's ground intensity (ledger 0087).

    <lidar venv>/bin/python -I measure_edges.py <workshop>/data/gate_centerline.json <workshop>/data/centerline.local.json \
        <pts.npz> <repo>/tracks/milford-road-course/source/naip_2022_mrc.jpg edge_evidence.json

pts.npz is the lidar read of ledger 0082 (source/lidar/README.md: ept_fetch.py; the raw tiles stay on the Mac). Every 1 m along
the built line and on both sides, within +-SEARCH_M of the built lane edge:
  naip   the steepest outward rise of excess green (2G - R - B; grass is green, asphalt / paint / concrete are not), bilinear,
         the profile smoothed 0.3 m, the peak refined by a parabola. Kept when the ExG contrast 0.6-2.0 m either side of it is
         over NAIP_CONTRAST_MIN.
  lidar  the class-2 returns within +-0.5 m along the line: the two-level step in intensity (dark inside, bright outside)
         that minimises the within-level variance. Kept when the level contrast is over LIDAR_CONTRAST_MIN and >= 8 returns.
The two sensors are put in ONE frame, the line's (the lap was traced off this NAIP): fitted over every station where both read
an edge within 1.5 m of each other, naip - lidar = a*nE + b*nN + c (n the outward normal) gives the image's registration
offset (a, b) against the lidar and a mean outward difference c. The lidar points are moved by (a, b) and the difference c is
split between the sensors (+c/2 to the lidar, -c/2 to NAIP): which one reads the true edge at 0.6 m GSD is unresolved.
Written as WORLD points (E, N in the port's local frame), so the intake reads them against whatever line it builds.
"""
import json
import math
import sys

import numpy as np

SEARCH_M = 3.5                 # [invented] the trace's widths sit within ~1 m of the edge (ledger 0087 §2); 3.5 m reaches past
NAIP_CONTRAST_MIN = 15.0       # [measured] ExG units: p10 of the contrast along the lap is 7-10 (shadow, aprons), median ~30
LIDAR_CONTRAST_MIN = 3000.0    # [measured] intensity units: p10 1,400-2,800 (aprons, paint), median ~12,000
LIDAR_MIN_RETURNS = 8
ALONG_LIDAR_M = 0.5


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def stations(line, step=1.0):
    P = np.array(line["points_xyz_m"]); W = np.array(line["widths_m"])
    seg = np.hypot(np.diff(P[:, 0]), np.diff(P[:, 2]))
    st = np.r_[0, np.cumsum(seg)]
    s = np.arange(0, st[-1], step)
    x = np.interp(s, st, P[:, 0]); z = np.interp(s, st, P[:, 2]); w = np.interp(s, st, W)
    tx = np.gradient(x); tz = np.gradient(z); L = np.hypot(tx, tz)
    return s, x, z, w / 2, tx / L, tz / L


def naip_edges(x, z, hw, tx, tz, org, jpg):
    from PIL import Image
    A = np.asarray(Image.open(jpg).convert("RGB")).astype(np.float32)
    H, Wd = A.shape[:2]
    # the export's true extent (tracks/milford-road-course/source/trace/unsquash_frame.py, ledger 0062)
    lon0, lon1, lat0, lat1 = -83.6700, -83.6570, 42.56050, 42.57950
    exg = 2 * A[..., 1] - A[..., 0] - A[..., 2]
    m_lon, m_lat = mpd(org["lat"])

    def samp(e, n):
        lon = org["lon"] + e / m_lon; lat = org["lat"] + n / m_lat
        px = (lon - lon0) / (lon1 - lon0) * Wd - 0.5; py = (lat1 - lat) / (lat1 - lat0) * H - 0.5
        x0 = np.clip(np.floor(px).astype(int), 0, Wd - 2); y0 = np.clip(np.floor(py).astype(int), 0, H - 2)
        fx = np.clip(px - x0, 0, 1); fy = np.clip(py - y0, 0, 1)
        return (exg[y0, x0] * (1 - fx) * (1 - fy) + exg[y0, x0 + 1] * fx * (1 - fy) + exg[y0 + 1, x0] * (1 - fx) * fy
                + exg[y0 + 1, x0 + 1] * fx * fy)
    offs = np.arange(-SEARCH_M, SEARCH_M + 1e-9, 0.1)
    k = np.exp(-0.5 * (np.arange(-4, 5) * 0.1 / 0.3) ** 2); k /= k.sum()
    out = {}
    for side, sg in (("left", 1), ("right", -1)):
        nx, nz = -tz * sg, tx * sg
        D = hw[:, None] + offs[None, :]
        prof = samp(x[:, None] + nx[:, None] * D, z[:, None] + nz[:, None] * D)
        prof = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 1, prof)
        g = np.gradient(prof, axis=1)
        g[:, :5] = -1e9; g[:, -5:] = -1e9
        j = np.clip(np.argmax(g, axis=1), 1, len(offs) - 2)
        r = np.arange(len(j))
        y0, y1, y2 = g[r, j - 1], g[r, j], g[r, j + 1]
        den = y0 - 2 * y1 + y2
        frac = np.where(np.abs(den) > 1e-9, 0.5 * (y0 - y2) / den, 0.0).clip(-0.5, 0.5)
        d = hw + offs[j] + frac * 0.1
        ring = np.linspace(0.6, 2.0, 8)[None, :]
        inn = samp(x[:, None] + nx[:, None] * (d[:, None] - ring), z[:, None] + nz[:, None] * (d[:, None] - ring)).mean(1)
        outv = samp(x[:, None] + nx[:, None] * (d[:, None] + ring), z[:, None] + nz[:, None] * (d[:, None] + ring)).mean(1)
        out[side] = (d, outv - inn)
    return out


def lidar_edges(x, z, hw, tx, tz, pts_npz):
    from scipy.spatial import cKDTree
    P = np.load(pts_npz)
    g = P["cls"] == 2
    E, N, I = P["e"][g].astype(float), P["n"][g].astype(float), P["inten"][g].astype(float)
    tree = cKDTree(np.c_[E, N])
    out = {}
    for side, sg in (("left", 1), ("right", -1)):
        nx, nz = -tz * sg, tx * sg
        d_, c_ = np.full(len(x), np.nan), np.zeros(len(x))
        for i in range(len(x)):
            idx = tree.query_ball_point([x[i] + nx[i] * hw[i], z[i] + nz[i] * hw[i]], SEARCH_M + 1.0)
            if len(idx) < LIDAR_MIN_RETURNS:
                continue
            ex, ez, it = E[idx] - x[i], N[idx] - z[i], I[idx]
            u = ex * nx[i] + ez * nz[i]; v = ex * tx[i] + ez * tz[i]
            m = (np.abs(v) <= ALONG_LIDAR_M) & (np.abs(u - hw[i]) <= SEARCH_M)
            u, it = u[m], it[m]
            n = len(u)
            if n < LIDAR_MIN_RETURNS:
                continue
            o = np.argsort(u); u, it = u[o], it[o]
            c1 = np.cumsum(it); c2 = np.cumsum(it ** 2)
            kk = np.arange(3, n - 3)
            if not len(kk):
                continue
            l1 = c1[kk - 1] / kk; l2 = (c1[-1] - c1[kk - 1]) / (n - kk)
            sse = (c2[kk - 1] - kk * l1 ** 2) + (c2[-1] - c2[kk - 1] - (n - kk) * l2 ** 2)
            sse = np.where(l2 > l1, sse, np.inf)
            b = int(np.argmin(sse))
            if not np.isfinite(sse[b]):
                continue
            kb = kk[b]
            d_[i] = 0.5 * (u[kb - 1] + u[kb]); c_[i] = l2[b] - l1[b]
        out[side] = (d_, c_)
    return out


def main():
    line_p, org_p, pts_p, jpg, out_p = sys.argv[1:6]
    line = json.load(open(line_p)); org = json.load(open(org_p))["origin"]
    s, x, z, hw, tx, tz = stations(line)
    NA = naip_edges(x, z, hw, tx, tz, org, jpg)
    LI = lidar_edges(x, z, hw, tx, tz, pts_p)
    # one frame: the image's registration offset against the lidar, and the sensors' mean outward difference
    rows = []
    for side, sg in (("left", 1), ("right", -1)):
        nx, nz = -tz * sg, tx * sg
        dn, cn = NA[side]; dl, cl = LI[side]
        ok = np.isfinite(dl) & (cn > NAIP_CONTRAST_MIN) & (cl > LIDAR_CONTRAST_MIN) & (np.abs(dn - dl) < 1.5)
        rows.append(np.c_[nx[ok], nz[ok], np.ones(ok.sum()), (dn - dl)[ok]])
    A = np.vstack(rows)
    (a, b, c), *_ = np.linalg.lstsq(A[:, :3], A[:, 3], rcond=None)
    pts, counts = [], {"naip": 0, "lidar": 0}
    for side, sg in (("left", 1), ("right", -1)):
        nx, nz = -tz * sg, tx * sg
        dn, cn = NA[side]; dl, cl = LI[side]
        for i in range(len(s)):
            if cn[i] > NAIP_CONTRAST_MIN:
                d = dn[i] - c / 2
                pts.append([round(float(x[i] + nx[i] * d), 2), round(float(z[i] + nz[i] * d), 2), "naip", round(float(cn[i]), 1)])
                counts["naip"] += 1
            if np.isfinite(dl[i]) and cl[i] > LIDAR_CONTRAST_MIN:
                d = dl[i] + c / 2
                pts.append([round(float(x[i] + nx[i] * d + a), 2), round(float(z[i] + nz[i] * d + b), 2), "lidar",
                            round(float(cl[i]))])
                counts["lidar"] += 1
    rep = {"_doc": "ledger 0087: measured pavement-edge points beside Milford's lap (source/edges/measure_edges.py); world E/N "
                   "in the port's local frame (the line's origin), NAIP's frame",
           "origin": org, "search_m": SEARCH_M,
           "contrast_min": {"naip_exg": NAIP_CONTRAST_MIN, "lidar_intensity": LIDAR_CONTRAST_MIN},
           "registration": {"naip_minus_lidar_m": {"east": round(float(a), 3), "north": round(float(b), 3),
                                                   "outward": round(float(c), 3)},
                            "stations_fitted": int(len(A)),
                            "applied": "lidar points moved by (east, north); the outward difference split, +c/2 lidar, -c/2 naip"},
           "counts": counts, "points": pts}
    json.dump(rep, open(out_p, "w"), separators=(",", ":"))
    print(json.dumps({k: rep[k] for k in ("registration", "counts")}))


if __name__ == "__main__":
    main()
