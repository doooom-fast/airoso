"""Milford's REAL asphalt edges on six stretches, both sides, every 0.5 m of s, from the 2017 lidar (the PC builder's
"blooms", Kevin: width swells on s 1114-1270 and 1557-1857 its NAIP-mask edges do not support, and the pavement's centre
0.3-0.8 m inside the line on the tight curves). Measures only. numpy + scipy (+ laspy/lazrs + pyproj for `read`).

The frame, the registration and the stations are road_profile_lidar.py's (beside this file): the lidar moved by
terrain.lidar_shift_m (SHIFT_M), z + DATUM_M - origin.elev_m, stations every 0.5 m of s on data/centerline.local.json
(n = round(lap / 0.5)), + = left of travel.

  read     every class 1 / 2 return within KEEP_EXTRA_M of the lane edge of the stretches' stations, with its intensity.
  edges    each return put on the line by its nearest point of a 0.1 m resampling of it: (s, u) exactly, so a point
           inside a tight curve is not misplaced by a station's straight normal. Per station and side, over the class-2
           returns with |u - built half width| <= SEARCH_M and |u| >= MIN_U_M:
             intensity  the two-level step (dark inside, bright outside) that minimises the within-level variance
                        (source/edges/measure_edges.py's lidar rule, |s - station| <= ALONG_I_M); strength = the level
                        contrast (intensity units) and its t (contrast over its standard error). Kept: contrast >=
                        LIDAR_CONTRAST_MIN (measure_edges' measured threshold) and >= LIDAR_MIN_RETURNS returns.
             height     a line each side of a breakpoint (each side >= H_MIN_SIDE returns, |s - station| <= ALONG_H_M),
                        the breakpoint minimising the two lines' squared residuals; step = outer line - inner line at
                        the breakpoint (+ = verge higher), its t. Kept: |step| >= H_STEP_MIN_M and t >= H_T_MIN.
           The edge is the intensity step where it is kept ("both" where the height agrees within AGREE_M), else none
           (a gap): on these stretches the height break lands 1.5-3 m (IQR) either side of the intensity step (the
           verge's ditches and cut slopes, not the pavement's lip), so it is reported, never used. Then the width
           (left - right), the pavement centre ((left + right) / 2)
           against the line, toward the curve's inside (+) or outside (-) by the line's own curvature, the built width
           (the line file's widths_m) and built minus real; per 5 m bin the medians and their scatter; per stretch a
           straight line through the real width (its residual RMS: steady or swelling) and the centre's median / range.
           The centre is also given in the alternative registration (ALT_SHIFT_M: ledger 0087's NAIP - lidar fit of
           the edges, the frame the line was traced in, in place of terrain.lidar_shift_m): the two differ by 0.66 m
           in plan, so a centre offset under ~0.6 m is inside the registration's own uncertainty.

    python edges_curves.py read --line centerline.local.json --lidar DIR [--lidar DIR] --out edge_points.npz
    python edges_curves.py edges --line centerline.local.json --points edge_points.npz --out milford_edges_curves.lidar.g10.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import road_profile_lidar as R           # noqa: E402

SPANS = ((1114.0, 1270.0), (1557.0, 1857.0), (580.0, 660.0), (750.0, 1015.0), (1275.0, 1335.0), (1625.0, 1695.0))
KEEP_EXTRA_M = 5.0       # read: returns within the built lane edge + this (past SEARCH_M)
KEEP_CLASSES = (1, 2)
SEARCH_M = 3.5           # measure_edges' [invented]: the search reaches this far either side of the built lane edge
MIN_U_M = 1.0            # [invented] the search never comes nearer the line than this (a centre line's paint)
ALONG_I_M = 0.5          # measure_edges' ALONG_LIDAR_M
LIDAR_CONTRAST_MIN = 3000.0   # measure_edges' [measured]: p10 of the contrast 1,400-2,800 (aprons, paint), median ~12,000
LIDAR_MIN_RETURNS = 8    # measure_edges'
ALONG_H_M = 1.0          # [invented] the height fit takes 2 m along (two lines need more returns than a level step)
H_MIN_SIDE = 4           # [invented]
H_STEP_MIN_M = 0.03      # [invented] a "small height step": 3 cm
H_T_MIN = 3.0            # [invented]
AGREE_M = 0.5            # [invented] the two signals agree within this
BIN_M = 5.0              # as asked
ALT_SHIFT_M = (-0.119, 0.329)   # ledger 0087 (source/edges/edge_evidence.json): NAIP - lidar, lap-wide, from the edges
NAIP_OUTWARD_M = 0.257   # the same fit: NAIP's edge sits this much further out than the lidar's, per side (mean)
INSIDE_R_MAX_M = 150.0   # [invented] inside / outside is read only where the line's radius is under this
TIGHT_R_M = 50.0         # [invented] "the tight curves": the line's radius under this
KAPPA_SMOOTH_M = 5.0     # [invented] the curvature read over +-5 m of the line


def dense_line(P, step=0.1):
    s = np.r_[0, np.cumsum(np.hypot(np.diff(P[:, 0]), np.diff(P[:, 2])))]
    lap = s[-1]; n = int(round(lap / step)); su = np.arange(n) * lap / n
    X, Z = np.interp(su, s, P[:, 0]), np.interp(su, s, P[:, 2])
    tx = np.roll(X, -1) - np.roll(X, 1); tz = np.roll(Z, -1) - np.roll(Z, 1)
    L = np.hypot(tx, tz)
    return su, X, Z, tx / L, tz / L, lap


def in_spans(s, spans, pad=0.0):
    m = np.zeros(len(s), bool)
    for a, b in spans:
        m |= (s >= a - pad) & (s <= b + pad)
    return m


# ---------------------------------------------------------------- read
def cmd_read(a):
    import laspy
    from pyproj import CRS, Transformer
    from scipy.spatial import cKDTree
    t0 = time.time()
    P, W, origin = R.load_line(a.line)
    st = R.stations(P, W)
    sel = in_spans(st["s"], SPANS, pad=5.0)
    X, Z, HW = st["X"][sel], st["Z"][sel], st["HW"][sel]
    keep_r = float(HW.max()) + KEEP_EXTRA_M
    tree = cKDTree(np.c_[X, Z])
    m_lon, m_lat = R.mpd(origin["lat"])
    lo_e, hi_e, lo_n, hi_n = X.min() - keep_r - 5, X.max() + keep_r + 5, Z.min() - keep_r - 5, Z.max() + keep_r + 5
    nodes, src = R.node_files(a.lidar)
    keys = sorted(nodes, key=lambda k: os.path.basename(nodes[k]))
    out = {k: [] for k in ("e", "n", "z", "cls", "psid", "inten", "ret", "nret")}
    tcache = {}; nread = skipped = pts_read = 0; cls_near = {}
    for k in keys:
        with laspy.open(nodes[k]) as r:
            h = r.header
            crs = h.parse_crs()
            ck = crs.to_wkt() if crs is not None else "EPSG:3857"
            if ck not in tcache:
                if crs is None:
                    hcrs, zf = CRS.from_epsg(3857), 1.0
                else:
                    subs = crs.sub_crs_list if crs.is_compound else [crs]
                    hcrs = subs[0]; v = subs[1] if len(subs) > 1 else None
                    u = (v.axis_info[0].unit_conversion_factor if v is not None and v.axis_info else 1.0)
                    zf = float(u) if u else 1.0
                tcache[ck] = (Transformer.from_crs(hcrs, 4326, always_xy=True), zf)
            to_ll, zf = tcache[ck]
            lon_c, lat_c = to_ll.transform([h.mins[0], h.maxs[0], h.mins[0], h.maxs[0]],
                                           [h.mins[1], h.mins[1], h.maxs[1], h.maxs[1]])
            ec = (np.asarray(lon_c) - origin["lon"]) * m_lon + R.SHIFT_M[0]
            nc = (np.asarray(lat_c) - origin["lat"]) * m_lat + R.SHIFT_M[1]
            e0, e1, n0, n1 = ec.min(), ec.max(), nc.min(), nc.max()
            if e1 < lo_e or e0 > hi_e or n1 < lo_n or n0 > hi_n or not tree.query_ball_point(
                    [(e0 + e1) / 2, (n0 + n1) / 2], 0.5 * math.hypot(e1 - e0, n1 - n0) + keep_r + 1.0):
                skipped += 1; continue
            nread += 1
            for ch in r.chunk_iterator(a.chunk):
                pts_read += len(ch)
                lon, lat = to_ll.transform(np.asarray(ch.x), np.asarray(ch.y))
                e = (lon - origin["lon"]) * m_lon + R.SHIFT_M[0]
                nn = (lat - origin["lat"]) * m_lat + R.SHIFT_M[1]
                idx = np.flatnonzero((e > lo_e) & (e < hi_e) & (nn > lo_n) & (nn < hi_n))
                if not len(idx):
                    continue
                dd, j = tree.query(np.c_[e[idx], nn[idx]], distance_upper_bound=keep_r)
                ok = np.isfinite(dd)
                idx, j = idx[ok], j[ok]
                ok = dd[ok] <= HW[j] + KEEP_EXTRA_M
                idx = idx[ok]
                if not len(idx):
                    continue
                cl = np.asarray(ch.classification)[idx]
                for c_, n_ in zip(*np.unique(cl, return_counts=True)):
                    cls_near[int(c_)] = cls_near.get(int(c_), 0) + int(n_)
                g = np.isin(cl, KEEP_CLASSES)
                idx = idx[g]
                out["e"].append(e[idx]); out["n"].append(nn[idx])
                out["z"].append(np.asarray(ch.z)[idx] * zf + R.DATUM_M - float(origin["elev_m"]))
                out["cls"].append(cl[g].astype(np.uint8)); out["psid"].append(np.asarray(ch.point_source_id)[idx].astype(np.int32))
                out["inten"].append(np.asarray(ch.intensity)[idx].astype(np.int32))
                out["ret"].append(np.asarray(ch.return_number)[idx].astype(np.uint8))
                out["nret"].append(np.asarray(ch.number_of_returns)[idx].astype(np.uint8))
    arr = {k: np.concatenate(v) for k, v in out.items()}
    rep = {"what": "edges_curves.py read", "line_md5": R.md5(a.line), "spans": [list(x) for x in SPANS],
           "shift_m": list(R.SHIFT_M), "datum_m": R.DATUM_M, "keep": f"within the built lane edge + {KEEP_EXTRA_M} m",
           "nodes_read": nread, "nodes_skipped": skipped, "points_in_nodes_read": pts_read,
           "classes_near": {str(k): v for k, v in sorted(cls_near.items())}, "kept": int(len(arr["e"])),
           "kept_per_point_source_id": {str(int(p)): int((arr["psid"] == p).sum()) for p in np.unique(arr["psid"])},
           "wall_s": round(time.time() - t0, 1)}
    np.savez_compressed(a.out, **arr)
    Path(str(a.out) + ".report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


# ---------------------------------------------------------------- the two signals
def intensity_step(u, it):
    """measure_edges' two-level step (dark inside, bright outside): (edge u, contrast, t, n) or None"""
    n = len(u)
    if n < LIDAR_MIN_RETURNS:
        return None
    o = np.argsort(u); u, it = u[o], it[o]
    c1 = np.cumsum(it); c2 = np.cumsum(it ** 2)
    kk = np.arange(3, n - 3)
    if not len(kk):
        return None
    l1 = c1[kk - 1] / kk; l2 = (c1[-1] - c1[kk - 1]) / (n - kk)
    sse = (c2[kk - 1] - kk * l1 ** 2) + (c2[-1] - c2[kk - 1] - (n - kk) * l2 ** 2)
    sse = np.where(l2 > l1, sse, np.inf)
    b = int(np.argmin(sse))
    if not np.isfinite(sse[b]):
        return None
    kb = kk[b]
    sd = math.sqrt(max(sse[b], 1e-9) / max(n - 2, 1))
    con = float(l2[b] - l1[b])
    t = con / (sd * math.sqrt(1.0 / kb + 1.0 / (n - kb)))
    return float(0.5 * (u[kb - 1] + u[kb])), con, float(t), int(n)


def height_step(u, h):
    """two lines either side of a breakpoint: (edge u, step m (+ = outside higher), t, slope change, n) or None"""
    n = len(u)
    if n < 2 * H_MIN_SIDE:
        return None
    o = np.argsort(u); u, h = u[o], h[o]
    best = None
    for k in range(H_MIN_SIDE, n - H_MIN_SIDE + 1):
        a1 = np.polyfit(u[:k], h[:k], 1); a2 = np.polyfit(u[k:], h[k:], 1)
        r1 = h[:k] - np.polyval(a1, u[:k]); r2 = h[k:] - np.polyval(a2, u[k:])
        sse = float(r1 @ r1 + r2 @ r2)
        if best is None or sse < best[0]:
            best = (sse, k, a1, a2)
    sse, k, a1, a2 = best
    u0 = 0.5 * (u[k - 1] + u[k])
    step = float(np.polyval(a2, u0) - np.polyval(a1, u0))
    sd = math.sqrt(max(sse, 1e-12) / max(n - 4, 1))
    t = abs(step) / (sd * math.sqrt(1.0 / k + 1.0 / (n - k)))
    return float(u0), step, float(t), float(a2[0] - a1[0]), int(n)


def mad_sd(v):
    v = v[np.isfinite(v)]
    return float(1.4826 * np.median(np.abs(v - np.median(v)))) if len(v) >= 3 else None


def r_(v, nd=3):
    return None if v is None or not np.isfinite(v) else round(float(v), nd)


# ---------------------------------------------------------------- edges
def cmd_edges(a):
    from scipy.spatial import cKDTree
    t0 = time.time()
    P, W, origin = R.load_line(a.line)
    st = R.stations(P, W); n = st["n"]
    sd_, Xd, Zd, txd, tzd, lap = dense_line(P)
    D = np.load(a.points)
    E, N, Zp, C, I = D["e"], D["n"], D["z"], D["cls"], D["inten"].astype(float)
    # every return on the line: its nearest 0.1 m point, then along / across exactly
    dt = cKDTree(np.c_[Xd, Zd])
    _, j = dt.query(np.c_[E, N])
    ex, ez = E - Xd[j], N - Zd[j]
    sp = (sd_[j] + ex * txd[j] + ez * tzd[j]) % lap
    up = ex * (-tzd[j]) + ez * txd[j]
    g = C == 2
    # the line's signed curvature at the stations (+ = turning left, the inside on the left), over +-KAPPA_SMOOTH_M
    k_ = int(round(KAPPA_SMOOTH_M / R.STEP_M))
    th = np.unwrap(np.arctan2(st["tz"], st["tx"]))
    kap = (np.roll(th, -k_) - np.roll(th, k_))
    kap = (kap + np.pi) % (2 * np.pi) - np.pi
    kap = kap / (2 * KAPPA_SMOOTH_M)
    s = st["s"]; HW = st["HW"]
    order = np.argsort(sp[g]); sg_, ug_, zg_, ig_ = sp[g][order], up[g][order], Zp[g][order], I[g][order]
    rows = []
    sel = np.flatnonzero(in_spans(s, SPANS))
    for i in sel:
        rec = {"i": int(i), "s": round(float(s[i]), 2), "built_half_width_m": round(float(HW[i]), 3),
               "curvature_1pm": round(float(kap[i]), 5)}
        for side, sgn in (("left", 1.0), ("right", -1.0)):
            lo = np.searchsorted(sg_, s[i] - ALONG_H_M); hi = np.searchsorted(sg_, s[i] + ALONG_H_M)
            ss, uu, zz, ii = sg_[lo:hi], sgn * ug_[lo:hi], zg_[lo:hi], ig_[lo:hi]      # uu: outward offset on this side
            win = (np.abs(uu - HW[i]) <= SEARCH_M) & (uu >= MIN_U_M)
            mi = win & (np.abs(ss - s[i]) <= ALONG_I_M)
            Ii = intensity_step(uu[mi], ii[mi])
            Hh = height_step(uu[win], zz[win])
            okI = Ii is not None and Ii[1] >= LIDAR_CONTRAST_MIN
            okH = Hh is not None and abs(Hh[1]) >= H_STEP_MIN_M and Hh[2] >= H_T_MIN
            if okI and okH and abs(Ii[0] - Hh[0]) <= AGREE_M:
                sig, ue = "both", Ii[0]
            elif okI:
                sig, ue = ("intensity (height disagrees)" if okH else "intensity"), Ii[0]
            else:
                sig, ue = ("none (height only: not used)" if okH else None), None
            rec[side] = {"u_m": r_(sgn * ue) if ue is not None else None, "signal": sig,
                         "intensity": ({"u_m": r_(sgn * Ii[0]), "contrast": round(Ii[1]), "t": round(Ii[2], 1), "n": Ii[3]}
                                       if Ii is not None else None),
                         "height": ({"u_m": r_(sgn * Hh[0]), "step_m": r_(Hh[1]), "t": round(Hh[2], 1),
                                     "slope_change": r_(Hh[3]), "n": Hh[4]} if Hh is not None else None),
                         "returns_in_window": int(win.sum())}
        L, Rr = rec["left"]["u_m"], rec["right"]["u_m"]
        if L is not None and Rr is not None:
            du = (ALT_SHIFT_M[0] - R.SHIFT_M[0]) * st["nx"][i] + (ALT_SHIFT_M[1] - R.SHIFT_M[1]) * st["nz"][i]
            insd = abs(kap[i]) >= 1.0 / INSIDE_R_MAX_M
            rec["width_m"] = round(L - Rr, 3); rec["centre_m"] = round(0.5 * (L + Rr), 3)
            rec["centre_toward_inside_m"] = round(0.5 * (L + Rr) * (1 if kap[i] >= 0 else -1), 3) if insd else None
            rec["centre_alt_registration_m"] = round(0.5 * (L + Rr) + du, 3)
            rec["centre_alt_toward_inside_m"] = round((0.5 * (L + Rr) + du) * (1 if kap[i] >= 0 else -1), 3) if insd else None
            rec["built_minus_real_width_m"] = round(2 * HW[i] - (L - Rr), 3)
        rows.append(rec)
    by_i = {r["i"]: r for r in rows}

    def col(idx, f, sub=None):
        out = []
        for i in idx:
            r = by_i[i]
            v = r.get(f) if sub is None else (r.get(f) or {}).get(sub)
            out.append(np.nan if v is None else float(v))
        return np.array(out)

    spans_out = []
    for a0, b0 in SPANS:
        idx = [i for i in sel if a0 <= s[i] <= b0]
        ss = s[idx]
        wid, cen, cin = col(idx, "width_m"), col(idx, "centre_m"), col(idx, "centre_toward_inside_m")
        cal, cail = col(idx, "centre_alt_registration_m"), col(idx, "centre_alt_toward_inside_m")
        def contrast(side):
            return np.array([float((by_i[i][side]["intensity"] or {}).get("contrast", np.nan)) for i in idx])
        conL, conR = contrast("left"), contrast("right")
        hmi = {}
        for side, sgn in (("left", 1.0), ("right", -1.0)):
            v = [sgn * (by_i[i][side]["height"]["u_m"] - by_i[i][side]["intensity"]["u_m"]) for i in idx
                 if by_i[i][side]["height"] and by_i[i][side]["intensity"] and abs(by_i[i][side]["height"]["step_m"]) >= H_STEP_MIN_M
                 and by_i[i][side]["height"]["t"] >= H_T_MIN]
            hmi[side] = ({"n": len(v), "p25_m": r_(np.percentile(v, 25), 2), "p50_m": r_(np.percentile(v, 50), 2),
                          "p75_m": r_(np.percentile(v, 75), 2)} if v else None)
        uL, uR = col(idx, "left", "u_m"), col(idx, "right", "u_m")
        bw = 2 * HW[idx]
        kp = kap[idx]
        sigs = {}
        for side in ("left", "right"):
            cnt = {}
            for i in idx:
                k2 = by_i[i][side]["signal"] or "none"
                cnt[k2] = cnt.get(k2, 0) + 1
            sigs[side] = cnt
        okw = np.isfinite(wid)
        rec = {"s": [a0, b0], "stations": len(idx), "stations_with_both_edges": int(okw.sum()),
               "signals": sigs,
               "intensity_contrast_p10_p50_p90": {"left": [r_(np.nanpercentile(conL, q), 0) for q in (10, 50, 90)],
                                                  "right": [r_(np.nanpercentile(conR, q), 0) for q in (10, 50, 90)]},
               "height_break_minus_intensity_edge_outward": hmi,
               "curve": {"curvature_median_1pm": r_(np.median(kp), 5),
                         "radius_median_m": r_(1 / abs(np.median(kp)), 1) if abs(np.median(kp)) > 1e-6 else None,
                         "radius_min_m": r_(1 / np.max(np.abs(kp)), 1),
                         "turn": "left" if np.median(kp) > 0 else "right",
                         "inside_side": "left (+u)" if np.median(kp) > 0 else "right (-u)"}}
        # 5 m bins
        bins = []
        for b in np.arange(a0, b0, BIN_M):
            m = (ss >= b) & (ss < min(b + BIN_M, b0 + 1e-9))
            if not m.any():
                continue
            def med(v):
                v = v[m & np.isfinite(v)]
                return float(np.median(v)) if len(v) else np.nan
            nW = int((m & okw).sum())
            sw = mad_sd(wid[m])
            bins.append({"s": [round(float(b), 1), round(float(min(b + BIN_M, b0)), 1)], "n_width": nW,
                         "left_u_m": r_(med(uL)), "right_u_m": r_(med(uR)),
                         "width_m": r_(med(wid)), "width_scatter_m": r_(sw) if sw is not None else None,
                         "centre_m": r_(med(cen)), "centre_scatter_m": r_(mad_sd(cen[m])),
                         "centre_toward_inside_m": r_(med(cin)), "centre_alt_registration_m": r_(med(cal)),
                         "contrast_left": r_(med(conL), 0), "contrast_right": r_(med(conR), 0),
                         "built_width_m": r_(float(np.mean(bw[m]))),
                         "built_minus_real_width_m": r_(float(np.mean(bw[m])) - med(wid)) if np.isfinite(med(wid)) else None})
        rec["bins_5m"] = bins
        if okw.sum() >= 10:
            cf = np.polyfit(ss[okw], wid[okw], 1); res = wid[okw] - np.polyval(cf, ss[okw])
            cfb = np.polyfit(ss, bw, 1); resb = bw - np.polyval(cfb, ss)
            bs = np.array([0.5 * (x["s"][0] + x["s"][1]) for x in bins if x["width_m"] is not None])
            bv = np.array([x["width_m"] for x in bins if x["width_m"] is not None])
            bn = np.array([x["n_width"] for x in bins if x["width_m"] is not None])
            bsc = np.array([x["width_scatter_m"] if x["width_scatter_m"] is not None else np.nan for x in bins if x["width_m"] is not None])
            bres = bv - np.polyval(cf, bs)
            # a bin median's own noise [model]: the stations' scatter over sqrt(n / 2) (each return sits in ~2 stations)
            bnoise = bsc * 1.2533 / np.sqrt(np.maximum(bn / 2.0, 1.0))
            bbuilt = np.array([x["built_width_m"] for x in bins if x["width_m"] is not None])
            bres_b = bbuilt - np.polyval(cfb, bs)
            big = np.abs(bres) > 2 * np.nan_to_num(bnoise, nan=np.inf)
            run, best, where = 0, 0, None
            for q in range(len(big)):
                same = q > 0 and big[q] and big[q - 1] and np.sign(bres[q]) == np.sign(bres[q - 1])
                run = run + 1 if same else (1 if big[q] else 0)
                if run > best:
                    best, where = run, q
            rec["width"] = {
                "real_line_fit": {"at_start_m": r_(np.polyval(cf, a0)), "at_end_m": r_(np.polyval(cf, b0)),
                                  "slope_m_per_100m": r_(100 * cf[0]), "station_resid_rms_m": r_(np.sqrt(np.mean(res ** 2))),
                                  "bin_resid_rms_m": r_(np.sqrt(np.mean(bres ** 2))),
                                  "bin_resid_max_m": r_(bres[np.argmax(np.abs(bres))]),
                                  "bin_resid_max_at_s": r_(bs[np.argmax(np.abs(bres))], 1),
                                  "bin_noise_p50_m [model]": r_(np.nanmedian(bnoise)),
                                  "longest_run_of_bins_beyond_2_noise_same_sign": int(best),
                                  "that_run_ends_at_s": r_(bs[where], 1) if where is not None and best > 0 else None},
                "built": {"mean_m": r_(np.mean(bw)), "min_m": r_(np.min(bw)), "max_m": r_(np.max(bw)),
                          "line_fit_resid_rms_m": r_(np.sqrt(np.mean(resb ** 2))),
                          "bin_resid_rms_m": r_(np.sqrt(np.mean(bres_b ** 2))),
                          "bin_resid_max_m": r_(bres_b[np.argmax(np.abs(bres_b))]),
                          "bin_resid_max_at_s": r_(bs[np.argmax(np.abs(bres_b))], 1)},
                "real": {"median_m": r_(np.median(wid[okw])), "p10_m": r_(np.percentile(wid[okw], 10)),
                         "p90_m": r_(np.percentile(wid[okw], 90))},
                "built_minus_real_m": {"median": r_(np.median((bw - wid)[okw])),
                                       "bin_p10": r_(np.nanpercentile([x["built_minus_real_width_m"] for x in bins if x["built_minus_real_width_m"] is not None], 10)),
                                       "bin_p90": r_(np.nanpercentile([x["built_minus_real_width_m"] for x in bins if x["built_minus_real_width_m"] is not None], 90)),
                                       "bin_max": r_(np.nanmax([x["built_minus_real_width_m"] for x in bins if x["built_minus_real_width_m"] is not None]))},
                "steady": bool(best < 3),
                "steady_rule": "[invented] steady unless 3 or more consecutive 5 m bins sit off the real width's straight "
                               "line by more than 2 x their own noise, on the same side"}
            okc = np.isfinite(cen); oki = np.isfinite(cin)
            kk_ = np.abs(kp) >= 1.0 / TIGHT_R_M
            tight = (kk_ & np.isfinite(cin))
            tight_rec = ({"stations": int(tight.sum()),
                          "s_range": [r_(ss[tight].min(), 1), r_(ss[tight].max(), 1)],
                          "toward_inside_median_m": r_(np.median(cin[tight])),
                          "toward_inside_p10_p90_m": [r_(np.percentile(cin[tight], 10)), r_(np.percentile(cin[tight], 90))],
                          "alt_registration_toward_inside_median_m": r_(np.median(cail[tight])),
                          "width_median_m": r_(np.nanmedian(wid[tight])), "built_width_median_m": r_(np.median(bw[tight]))}
                         if tight.sum() >= 5 else None)
            rec["centre"] = {"median_m": r_(np.median(cen[okc])), "p10_m": r_(np.percentile(cen[okc], 10)),
                             "p90_m": r_(np.percentile(cen[okc], 90)), "min_m": r_(np.min(cen[okc])),
                             "max_m": r_(np.max(cen[okc])),
                             "curved_stations (R < INSIDE_R_MAX_M)": int(oki.sum()),
                             "toward_inside_median_m": r_(np.median(cin[oki])) if oki.any() else None,
                             "toward_inside_p10_p90_m": [r_(np.percentile(cin[oki], 10)), r_(np.percentile(cin[oki], 90))] if oki.any() else None,
                             "share_toward_inside": r_(float(np.mean(cin[oki] > 0)), 2) if oki.any() else None,
                             "alt_registration": {"median_m": r_(np.nanmedian(cal)),
                                                  "toward_inside_median_m": r_(np.nanmedian(cail)) if np.isfinite(cail).any() else None,
                                                  "share_toward_inside": r_(float(np.mean(cail[np.isfinite(cail)] > 0)), 2) if np.isfinite(cail).any() else None},
                             "bin_scatter_p50_m": r_(np.nanmedian([x["centre_scatter_m"] for x in bins if x["centre_scatter_m"] is not None])),
                             "tight_curve (R < TIGHT_R_M)": tight_rec}
        spans_out.append(rec)
    doc = {"_doc": "Milford's real asphalt edges on six stretches from the 2017 lidar (edges_curves.py). u in metres off "
                   "the lap line (data/centerline.local.json, the build's swept line), + = left of travel; width = left "
                   "- right; centre = (left + right) / 2; toward_inside = the centre's offset toward the curve's inside "
                   "(by the line's own curvature, + = left turn). Built width = the line file's widths_m (the ribbon is "
                   "+-w/2 about the line). Measured unless marked [invented] / [model].",
           "inputs": {"line": {"file": "data/centerline.local.json", "md5": R.md5(a.line)},
                      "points": {"md5": R.md5(a.points), "returns": int(len(E)), "class_2": int(g.sum())},
                      "read": json.loads(Path(str(a.points) + ".report.json").read_text())
                      if Path(str(a.points) + ".report.json").exists() else None},
           "registration": {"shift_m": list(R.SHIFT_M), "datum_m": R.DATUM_M,
                            "source": "terrain.lidar_shift_m, as road_profile.lidar.g10.json",
                            "alt_shift_m": list(ALT_SHIFT_M),
                            "alt_source": "ledger 0087's NAIP - lidar fit of the pavement edges (source/edges/"
                                          "edge_evidence.json registration.naip_minus_lidar_m, lap-wide): the frame the "
                                          "line was traced in. Moves a centre by (alt - shift) . n; widths unchanged",
                            "naip_outward_m": NAIP_OUTWARD_M,
                            "naip_outward_doc": "the same fit's mean outward difference: NAIP's edge 0.257 m further out "
                                                "per side than the lidar's intensity step, so NAIP reads ~0.51 m wider; "
                                                "which reads the true edge was left unresolved (ledger 0087)"},
           "constants": {"SEARCH_M": SEARCH_M, "MIN_U_M [invented]": MIN_U_M, "ALONG_I_M": ALONG_I_M,
                         "LIDAR_CONTRAST_MIN [measured, measure_edges]": LIDAR_CONTRAST_MIN,
                         "LIDAR_MIN_RETURNS": LIDAR_MIN_RETURNS, "ALONG_H_M [invented]": ALONG_H_M,
                         "H_MIN_SIDE [invented]": H_MIN_SIDE, "H_STEP_MIN_M [invented]": H_STEP_MIN_M,
                         "H_T_MIN [invented]": H_T_MIN, "AGREE_M [invented]": AGREE_M, "BIN_M": BIN_M,
                         "KAPPA_SMOOTH_M [invented]": KAPPA_SMOOTH_M, "INSIDE_R_MAX_M [invented]": INSIDE_R_MAX_M,
                         "TIGHT_R_M [invented]": TIGHT_R_M},
           "spans": spans_out, "stations": rows, "wall_s": round(time.time() - t0, 1)}
    Path(a.out).write_text(json.dumps(doc, separators=(",", ":")))
    print(json.dumps([{k: v for k, v in sp_.items() if k != "bins_5m"} for sp_ in spans_out], indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("read"); r.add_argument("--line", required=True); r.add_argument("--lidar", action="append", required=True)
    r.add_argument("--out", required=True); r.add_argument("--chunk", type=int, default=400_000)
    e = sub.add_parser("edges"); e.add_argument("--line", required=True); e.add_argument("--points", required=True)
    e.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    {"read": cmd_read, "edges": cmd_edges}[a.cmd](a)


if __name__ == "__main__":
    main()
