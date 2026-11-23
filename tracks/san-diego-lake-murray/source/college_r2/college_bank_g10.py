"""Lake Murray, College split (rows v1172-1444): the bank between the two carriageways, off USGS CA_SanDiegoCo_D24.
G10 job lm-college-bank-20261123. Reads only; downloads nothing. Run with -I under nice -n 19 ionice -c3.

    python -I college_bank.py <tiles dir> <inputs dir> <shrub out dir> <out dir>

<inputs dir>     college_edges.json, college_design.json, college_xsec.lidar.g10.json, college_plants.report.json (commit
                 f0c35e1f, source/college_r2) and trackdata/centerline.local.json (same commit, data/)
LM_SHRUB_TOOL_DIR (env) the folder holding shrub_heights.py (the lm-shrub tool)
<shrub out dir>  the lm-shrub job's out_24tiles: lm_shrub.tops.npz, lm_shrub.summary.json, work/ground_1m.npy, work/gdist_1m.npy

(a) college_bank_tops.g10.json: every plant top of lm_shrub.tops.npz inside the bank polygon, and a raw-lidar count of
    non-ground returns >= 0.25 m over ground inside the bank per 10 vertex rows.
(b) college_bank_rail.g10.json: a rail at the top of the bank? Non-ground returns 0.5-1.2 m over the local ground within
    1.5 m of the northbound inner edge (rows v1176-1440), per 5-vertex bin; the southbound inner edge as the control.

Frame and projection are the lm-shrub tool's own (shrub_heights.Track: pyproj EPSG 6340 <-> 4326, then the WGS84
metres-per-degree series at the centreline origin), which is also job1_college_lidar.py's. Station / offset convention
is job1's: offset + = LEFT of the line's travel (v increasing) = west on College northbound; cell centre =
(x, z) + offset * (nx, nz), n = (-t_z, t_x), t = central-difference tangent of centerline.local.json.
"""
import hashlib
import os
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from pyproj import Transformer
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay, cKDTree

sys.path.insert(0, os.environ.get("LM_SHRUB_TOOL_DIR", "."))  # the folder holding the lm-shrub tool, shrub_heights.py
import shrub_heights as SH  # noqa: E402  the lm-shrub tool: Track (projection), tile_list, chunks, inside, mpd

V_BANK = (1172, 1444)       # the island rows (README / college_design.json params.ISLAND)
V_RAIL = (1176, 1440)       # the rows the step-3 barrier was authored on (STEP-DESIGN.md)
V_CORR = (1160, 1456)       # rows read off the lidar (a margin of 12 / 12 rows around the island)
OFF_CORR = 30.0             # [invented] lateral half width of the lidar corridor, m
VEG_CLASSES = (1, 3, 4, 5)  # the request's classes (D24 here carries 1, 2, 7, 17, 18, 20 only)
H_VEG = 0.25                # the request's threshold (= shrub_heights' n_hi threshold)
H_TOP_MIN = 0.3             # shrub_heights H_MIN [invented there]
BIN_A = 10                  # rows per coverage bin (the request)
BIN_B = 5                   # rows per rail bin (the request)
CELL_A = 1.0                # [invented] cover cell, m
MISS_R = 3.0                # [invented] a covered cell with no top (any flag) this close counts as "no top nearby"
GROUND_FAR_TIN = 2.0        # [invented] a return further than this from any class-2 return is "ground_far" in (b)
RAIL_BAND = (0.5, 1.2)      # the request's band, m over the local ground
RAIL_WIN = 1.5              # the request's window, m either side of the edge
RAIL_WIDE = (-3.0, 4.0)     # [invented] the wider window whose lateral histogram is reported (+ = toward the bank)
RAIL_HIGH = 1.5             # the request's "above 1.5 m"
SPOT_HALF = 0.5             # [invented] "the same spot" = within this of the bin's lateral median
SLICE_M = 1.0               # [invented] along-edge slice for continuity
N_MIN = 15                  # [invented] fewer band returns in a bin = "nothing" (~1 per m; a W-beam at D24's ~12 first
                            #            returns per m2 would give ~3-4 per m)
RAIL_IQR_D = 0.40           # [invented] rail-like: lateral IQR of band returns at most this
RAIL_IQR_H = 0.30           # [invented] rail-like: height IQR at most this
RAIL_CONT = 0.60            # [invented] rail-like: at least this share of 1 m slices hold a band return at the spot
RAIL_HIGH_RATIO = 0.5       # [invented] rail-like: returns > 1.5 m at the spot at most this share of the band returns
PRESENT_SHARE = 0.5         # [invented] overall "present": at least this share of bins rail-like ...
PRESENT_RUN = 6             # [invented] ... with a run of at least this many consecutive rail-like bins (~90 m)
ABSENT_SHARE = 0.10         # [invented] overall "absent": at most this share rail-like and no run of ABSENT_RUN
ABSENT_RUN = 3              # [invented]
ENGINE_DY = 100.8           # engine y = NAVD88 - origin.elev_m (centerline.local.json origin.elev_m)


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def r(x, nd=3):
    if x is None:
        return None
    x = float(x)
    return None if not math.isfinite(x) else round(x, nd)


def pct(a, ps=(0, 10, 25, 50, 75, 90, 100), nd=2):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    if not len(a):
        return None
    return {f"p{p}": round(float(v), nd) for p, v in zip(ps, np.percentile(a, ps))}


def main():
    tdir, inp, sdir, out = (Path(a) for a in sys.argv[1:5])
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    log = lambda *a: SH.log(f"[{time.time() - t0:6.1f}s]", *a)  # noqa: E731

    # ---------------------------------------------------------------- frame: the lm-shrub tool's own
    tiles, epsg = SH.tile_list(tdir)
    to_utm = Transformer.from_crs(4326, epsg, always_xy=True)
    to_ll = Transformer.from_crs(epsg, 4326, always_xy=True)
    trk = SH.Track(inp / "trackdata", to_utm)
    cl = json.loads((inp / "trackdata" / "centerline.local.json").read_text())
    P = np.asarray(cl["points_xyz_m"], float)
    xz = P[:, [0, 2]]
    nv = len(xz)
    seg = np.hypot(*np.diff(xz, axis=0).T)
    s_lap = np.concatenate([[0.0], np.cumsum(seg)])
    t = np.zeros_like(xz)
    t[1:-1] = xz[2:] - xz[:-2]
    t[0], t[-1] = xz[1] - xz[0], xz[-1] - xz[-2]
    t /= np.linalg.norm(t, axis=1)[:, None]
    nrm = np.stack([-t[:, 1], t[:, 0]], axis=1)  # left of travel (job1_college_lidar.py)

    # the normals against the ones the College cross-sections were read with
    xs = json.loads((inp / "college_xsec.lidar.g10.json").read_text())
    xst = xs["stations"]
    xv = np.array(xst["v"])
    dn = max(float(np.max(np.abs(np.array(xst["nx"]) - nrm[xv, 0]))), float(np.max(np.abs(np.array(xst["nz"]) - nrm[xv, 1]))))
    dp = max(float(np.max(np.abs(np.array(xst["x"]) - xz[xv, 0]))), float(np.max(np.abs(np.array(xst["z"]) - xz[xv, 1]))))
    assert dn < 1e-5 and dp < 2e-3, (dn, dp)
    log(f"EPSG {epsg}; normals match college_xsec to {dn:.2e}, vertices to {dp:.2e} m")

    # ---------------------------------------------------------------- the edges
    ed = json.loads((inp / "college_edges.json").read_text())
    est = {s["v"]: s for s in ed["stations"]}

    def edge(key):
        a = np.full(nv, np.nan)
        for v, s in est.items():
            if s.get(key) is not None:
                a[v] = float(s[key])
        return a

    NB_IN, SB_IN = edge("nb_inner_smooth_m"), edge("sb_inner_smooth_m")
    NB_OUT, SB_OUT = edge("nb_outer_smooth_m"), edge("sb_outer_smooth_m")
    NB_IN_Y, SB_IN_Y = edge("nb_inner_y"), edge("sb_inner_y")
    vb = np.arange(V_BANK[0], V_BANK[1] + 1)
    assert np.isfinite(NB_IN[vb]).all() and np.isfinite(SB_IN[vb]).all()
    assert (SB_IN[vb] > NB_IN[vb]).all()
    dsg = json.loads((inp / "college_design.json").read_text())
    D_NB, D_SB = np.full(nv, np.nan), np.full(nv, np.nan)
    for s in dsg["stations"]:
        D_NB[s["v"]] = s["nb_inner"]["offset_m"]
        D_SB[s["v"]] = s["sb_inner"]["offset_m"]

    def ribbon(a, b, vv):
        Lp = xz[vv] + a[vv][:, None] * nrm[vv]
        Rp = xz[vv] + b[vv][:, None] * nrm[vv]
        return np.vstack([Lp, Rp[::-1]]), Lp, Rp

    poly, PL, PR = ribbon(NB_IN, SB_IN, vb)
    dpoly, _, _ = ribbon(D_NB, D_SB, vb)

    def quad_area(Lp, Rp):
        q = np.stack([Lp[:-1], Lp[1:], Rp[1:], Rp[:-1]], axis=1)
        x_, y_ = q[..., 0], q[..., 1]
        return 0.5 * (x_ * np.roll(y_, -1, axis=1) - np.roll(x_, -1, axis=1) * y_).sum(axis=1)

    qa = quad_area(PL, PR)
    assert (np.sign(qa) == np.sign(qa[0])).all(), "the bank ribbon folds"
    qa = np.abs(qa)                     # quad between row v and v+1, assigned to row v
    bank_area = float(qa.sum())
    log(f"bank polygon {len(poly)} vertices, area {bank_area:.0f} m2")

    # ---------------------------------------------------------------- stations of any (x, z)
    VS = np.arange(V_CORR[0] - 10, V_CORR[1] + 11)
    vtree = cKDTree(xz[VS])

    def station(px, pz):
        q = np.c_[px, pz]
        _, k = vtree.query(q, k=4)
        vv = VS[k]
        w = q[:, None, :] - xz[vv]
        al = (w * t[vv]).sum(-1)
        of = (w * nrm[vv]).sum(-1)
        j = np.argmin(np.abs(al), axis=1)
        rr = np.arange(len(q))
        v, a, o = vv[rr, j], al[rr, j], of[rr, j]
        sl = np.where(a >= 0, seg[np.minimum(v, nv - 2)], seg[np.maximum(v - 1, 0)])
        return v, v + a / sl, a, o

    def at(arr, vf, lo=V_BANK[0], hi=V_BANK[1]):
        vv = np.arange(lo, hi + 1)
        return np.interp(np.clip(vf, lo, hi), vv, arr[vv])

    # ---------------------------------------------------------------- the lidar in the corridor
    vc = np.arange(V_CORR[0], V_CORR[1] + 1)
    cx = np.r_[xz[vc, 0] + OFF_CORR * nrm[vc, 0], xz[vc, 0] - OFF_CORR * nrm[vc, 0]]
    cz = np.r_[xz[vc, 1] + OFF_CORR * nrm[vc, 1], xz[vc, 1] - OFF_CORR * nrm[vc, 1]]
    ue, un = trk._utm(cx, cz)
    ub = (min(ue) - 10, min(un) - 10, max(ue) + 10, max(un) + 10)
    use = [tl for tl in tiles if tl["maxs"][0] >= ub[0] and tl["mins"][0] <= ub[2] and tl["maxs"][1] >= ub[1] and tl["mins"][1] <= ub[3]]
    keep = {k: [] for k in ("E", "N", "x", "z", "elev", "cls", "rn", "nr", "v", "vf", "al", "o")}
    cls_box = {}
    tiles_rep = []
    for tl in use:
        tt = time.time()
        nk = 0
        for p in SH.chunks(tl["path"], 1_000_000):
            c = np.asarray(p.classification)
            X, Y = np.asarray(p.x), np.asarray(p.y)
            box = (X >= ub[0]) & (X <= ub[2]) & (Y >= ub[1]) & (Y <= ub[3])
            for k_, v_ in zip(*np.unique(c[box], return_counts=True)):
                cls_box[int(k_)] = cls_box.get(int(k_), 0) + int(v_)
            m = box & np.isin(c, (2,) + VEG_CLASSES) & ~np.asarray(p.withheld, bool)
            if not m.any():
                continue
            E, N = X[m], Y[m]
            x, z = trk.to_local(E, N, to_ll)
            x, z = np.asarray(x), np.asarray(z)
            dd, _ = vtree.query(np.c_[x, z], k=1)
            k2 = dd <= OFF_CORR + 5
            if not k2.any():
                continue
            v, vf, a, o = station(x[k2], z[k2])
            k3 = (np.abs(o) <= OFF_CORR) & (v >= V_CORR[0]) & (v <= V_CORR[1])
            sel = np.flatnonzero(m)[k2][k3]
            for key, arr in (("E", E[k2][k3]), ("N", N[k2][k3]), ("x", x[k2][k3]), ("z", z[k2][k3]),
                             ("elev", np.asarray(p.z)[sel]), ("cls", c[sel]), ("rn", np.asarray(p.return_number)[sel]),
                             ("nr", np.asarray(p.number_of_returns)[sel]), ("v", v[k3]), ("vf", vf[k3]), ("al", a[k3]),
                             ("o", o[k3])):
                keep[key].append(np.asarray(arr))
            nk += int(k3.sum())
        tiles_rep.append({"file": tl["file"], "bytes": tl["bytes"], "points": tl["points"], "kept_in_corridor": nk,
                          "md5": md5(tl["path"]), "seconds": round(time.time() - tt, 1)})
        log(f"{tl['file']}: {nk:,} kept")
    L = {k: np.concatenate(v) for k, v in keep.items()}
    del keep
    gnd = L["cls"] == 2
    veg = np.isin(L["cls"], VEG_CLASSES)
    log(f"corridor: {gnd.sum():,} ground, {veg.sum():,} non-ground (classes in the box: {cls_box})")

    # ---------------------------------------------------------------- ground: a TIN of class 2, and the shrub mosaic
    gxz = np.c_[L["x"][gnd], L["z"][gnd]]
    tin = LinearNDInterpolator(Delaunay(gxz), L["elev"][gnd])
    gtree = cKDTree(gxz)
    E0 = min(tl["E"] for tl in tiles)
    N0 = min(tl["N"] for tl in tiles)
    gx = int((max(tl["E"] for tl in tiles) + 1000 - E0) / SH.GCELL)
    gy = int((max(tl["N"] for tl in tiles) + 1000 - N0) / SH.GCELL)
    G = np.load(sdir / "work" / "ground_1m.npy", mmap_mode="r")
    assert G.shape == (gy, gx), (G.shape, gy, gx)

    def mosaic_at(e, n):   # shrub_heights.main's ground_at, verbatim
        fx, fy = (e - E0) / SH.GCELL - 0.5, (n - N0) / SH.GCELL - 0.5
        i0 = np.clip(np.floor(fx).astype(np.int64), 0, gx - 2)
        j0 = np.clip(np.floor(fy).astype(np.int64), 0, gy - 2)
        tx, ty = np.clip(fx - i0, 0, 1), np.clip(fy - j0, 0, 1)
        return (G[j0, i0] * (1 - tx) * (1 - ty) + G[j0, i0 + 1] * tx * (1 - ty)
                + G[j0 + 1, i0] * (1 - tx) * ty + G[j0 + 1, i0 + 1] * tx * ty)

    L["h_tin"] = (L["elev"] - tin(L["x"], L["z"])).astype(np.float32)
    L["h_mos"] = (L["elev"] - mosaic_at(L["E"], L["N"])).astype(np.float32)
    L["gd"] = gtree.query(np.c_[L["x"], L["z"]], k=1)[0].astype(np.float32)
    log("heights over ground done")

    # ================================================================ (a) the tops on the bank
    with np.load(sdir / "lm_shrub.tops.npz") as _t:   # decompress each array once (NpzFile re-reads on every access)
        T = {k: _t[k] for k in _t.files}
    tx_, tz_ = T["x"].astype(float), T["z"].astype(float)
    pb = (tx_ >= poly[:, 0].min() - 5) & (tx_ <= poly[:, 0].max() + 5) & (tz_ >= poly[:, 1].min() - 5) & (tz_ <= poly[:, 1].max() + 5)
    ib = np.flatnonzero(pb)
    # frame check: the npz's x, z against its own E, N through the same projection
    rx, rz = trk.to_local(T["E"][ib], T["N"][ib], to_ll)
    frame_err = float(np.max(np.hypot(np.asarray(rx) - tx_[ib], np.asarray(rz) - tz_[ib]))) if len(ib) else None
    inb = SH.inside(poly, tx_[ib], tz_[ib])
    idx = ib[inb]
    in_design = SH.inside(dpoly, tx_[idx], tz_[idx])
    v, vf, a, o = station(tx_[idx], tz_[idx])
    nb_at, sb_at = at(NB_IN, vf), at(SB_IN, vf)
    g_mos = mosaic_at(T["E"][idx], T["N"][idx])
    g_tin = tin(tx_[idx], tz_[idx])
    gfar = T["gdist"][idx] > SH.GROUND_FAR
    order = np.argsort(vf)
    tops = []
    for q in order:
        k = idx[q]
        tops.append({
            "npz_index": int(k), "v": int(v[q]), "v_frac": r(vf[q], 2), "along_m": r(a[q], 2), "offset_m": r(o[q], 2),
            "nb_inner_m": r(nb_at[q], 2), "sb_inner_m": r(sb_at[q], 2),
            "from_nb_inner_m": r(o[q] - nb_at[q], 2), "from_sb_inner_m": r(sb_at[q] - o[q], 2),
            "x": r(tx_[k]), "z": r(tz_[k]), "E": r(T["E"][k], 2), "N": r(T["N"][k], 2),
            "h_m": r(T["h"][k], 2), "hmax_m": r(T["hmax"][k], 2), "crown_d_m": r(T["crown_d"][k], 2),
            "y_ground": r(g_mos[q] - ENGINE_DY, 2), "y_top": r(g_mos[q] - ENGINE_DY + T["h"][k], 2),
            "ground_tin_minus_mosaic_m": r(g_tin[q] - g_mos[q], 2),
            "solid": bool(T["solid"][k]), "ground_far": bool(gfar[q]), "gdist_m": r(T["gdist"][k], 1),
            "plant": bool(T["plant"][k]), "rough": r(T["rough"][k], 3), "multi": r(T["multi"][k], 2),
            "d_bldg_m": r(T["d_bldg"][k], 1), "stratum": str(T["stratum"][k]), "in_design_bank": bool(in_design[q])})
    log(f"tops in the bank: {len(idx)} (frame check {frame_err})")
    H_ = T["h"][idx].astype(float)
    pl = T["plant"][idx]

    # existing bank spots in college_plants.report.json against the tops (a registration check)
    rep = json.loads((inp / "college_plants.report.json").read_text())
    ttree = cKDTree(np.c_[tx_[ib], tz_[ib]])
    spots = []
    for s_ in rep["spots"]:
        if s_.get("where") != "the bank":
            continue
        d_, j_ = ttree.query([s_["x"], s_["z"]], k=1)
        k = ib[j_]
        spots.append({"index": s_["index"], "v": s_["v"], "measured": s_["measured"], "tall": s_.get("tall"),
                      "lidar_h_m": s_.get("lidar_h_m"), "nearest_top": int(k), "dist_m": r(d_, 2),
                      "top_h_m": r(T["h"][k], 2), "top_in_bank": bool(np.isin(k, idx))})
    tall = [s_ for s_ in spots if s_["tall"]]

    # raw lidar inside the bank, per 10 rows
    pre = (L["v"] >= V_BANK[0] - 2) & (L["v"] <= V_BANK[1] + 2)
    pre &= (L["o"] >= at(NB_IN, L["vf"]) - 1.5) & (L["o"] <= at(SB_IN, L["vf"]) + 1.5)
    jj = np.flatnonzero(pre)
    ins = np.zeros(len(L["x"]), bool)
    ins[jj] = SH.inside(poly, L["x"][jj], L["z"][jj])
    # 1 m cells of the bank
    x0, z0 = math.floor(poly[:, 0].min()), math.floor(poly[:, 1].min())
    nx_, nz_ = int(math.ceil(poly[:, 0].max() - x0) / CELL_A) + 1, int(math.ceil(poly[:, 1].max() - z0) / CELL_A) + 1
    CXg, CZg = np.meshgrid(x0 + (np.arange(nx_) + 0.5) * CELL_A, z0 + (np.arange(nz_) + 0.5) * CELL_A)
    cin = SH.inside(poly, CXg.ravel(), CZg.ravel())
    cid = np.flatnonzero(cin)
    cv, _, _, _ = station(CXg.ravel()[cid], CZg.ravel()[cid])
    cell_of = lambda px, pz: (np.floor((pz - z0) / CELL_A).astype(np.int64) * nx_ + np.floor((px - x0) / CELL_A).astype(np.int64))  # noqa: E731
    cpos = {int(c): k for k, c in enumerate(cid)}
    # per bank cell: returns >= H_VEG / >= 0.5 / >= H_TOP_MIN (TIN ground), ground returns
    def cell_counts(mask):
        cc = cell_of(L["x"][mask], L["z"][mask])
        cnt = np.zeros(len(cid), np.int64)
        u, n = np.unique(cc, return_counts=True)
        for c, nn in zip(u, n):
            k = cpos.get(int(c))
            if k is not None:
                cnt[k] += nn
        return cnt
    m_bank_veg = ins & veg
    c025 = cell_counts(m_bank_veg & (L["h_tin"] >= H_VEG))
    c05 = cell_counts(m_bank_veg & (L["h_tin"] >= 0.5))
    c03 = cell_counts(m_bank_veg & (L["h_tin"] >= H_TOP_MIN))
    cg = cell_counts(ins & gnd)
    ctr = np.c_[CXg.ravel()[cid], CZg.ravel()[cid]]
    dtop = cKDTree(np.c_[tx_[ib], tz_[ib]]).query(ctr, k=1)[0]
    bins_a = []
    for b0 in range(V_BANK[0], V_BANK[1] + 1, BIN_A):
        b1 = min(b0 + BIN_A - 1, V_BANK[1])
        m = ins & (L["v"] >= b0) & (L["v"] <= b1)
        mv = m & veg
        hv = L["h_tin"][mv]
        hm = L["h_mos"][mv]
        kc = (cv >= b0) & (cv <= b1)
        kt = (v >= b0) & (v <= b1)
        covered = kc & (c03 >= 2)
        e = {"rows": f"v{b0}-{b1}", "area_m2": round(float(qa[(vb[:-1] >= b0) & (vb[:-1] <= b1)].sum()), 1),
             "width_m_median": r(np.median(SB_IN[b0:b1 + 1] - NB_IN[b0:b1 + 1]), 2),
             "ground_returns": int((m & gnd).sum()), "nonground_returns": int(mv.sum()),
             "ge_0.25m_tin": int((hv >= H_VEG).sum()), "ge_0.25m_mosaic": int((hm >= H_VEG).sum()),
             "ge_0.5m_tin": int((hv >= 0.5).sum()), "ge_1m_tin": int((hv >= 1.0).sum()), "ge_3m_tin": int((hv >= 3.0).sum()),
             "h_max_tin": r(hv.max(), 2) if len(hv) else None,
             "cells_1m": int(kc.sum()),
             "cells_ge_0.25m_share": r((c025[kc] > 0).mean(), 3) if kc.any() else None,
             "cells_ge_0.5m_share": r((c05[kc] > 0).mean(), 3) if kc.any() else None,
             "cells_no_ground_return_share": r((cg[kc] == 0).mean(), 3) if kc.any() else None,
             "cells_covered_no_top_within_3m": int((covered & (dtop > MISS_R)).sum()),
             "tops_all": int(kt.sum()), "tops_plant": int((kt & pl).sum()),
             "tops_h_range_m": [r(H_[kt].min(), 2), r(H_[kt].max(), 2)] if kt.any() else None}
        s05 = e["cells_ge_0.5m_share"] or 0.0
        e["reads"] = ("bare" if (c05[kc] >= 2).sum() == 0 else "sparse" if s05 < 0.10 else
                      "planted" if s05 < 0.50 else "dense")
        bins_a.append(e)
    log("coverage bins done")

    # ================================================================ (b) a rail at the top of the bank?
    sl_at = lambda vfv: np.interp(vfv, np.arange(nv), s_lap)  # noqa: E731

    def rail(which, use_design=False):
        arr, dsn = (NB_IN, D_NB) if which == "nb_inner" else (SB_IN, D_SB)
        if use_design:   # the design's bridged inner edge in place of college_edges.json's (covers the misread rows)
            arr = dsn
        sign = 1.0 if which == "nb_inner" else -1.0
        m0 = veg & (L["v"] >= V_RAIL[0]) & (L["v"] <= V_RAIL[1])
        e_at = at(arr, L["vf"][m0])
        d = sign * (L["o"][m0] - e_at)
        w = (d >= RAIL_WIDE[0]) & (d <= RAIL_WIDE[1])
        ii = np.flatnonzero(m0)[w]
        d = d[w]
        h = L["h_tin"][ii].astype(float)
        vv = L["v"][ii]
        sa = sl_at(L["vf"][ii])
        gfar = L["gd"][ii] > GROUND_FAR_TIN
        np.savez_compressed(out / f"rail_window_{which}{'_design' if use_design else ''}.npz", x=L["x"][ii], z=L["z"][ii], elev=L["elev"][ii], h_tin=h,
                            v=vv, vf=L["vf"][ii], d=d, s=sa, gd=L["gd"][ii])
        rows = []
        for b0 in range(V_RAIL[0], V_RAIL[1] + 1, BIN_B):
            b1 = min(b0 + BIN_B - 1, V_RAIL[1])
            kb = (vv >= b0) & (vv <= b1) & np.isfinite(h)
            W = kb & (np.abs(d) <= RAIL_WIN)
            band = W & (h >= RAIL_BAND[0]) & (h <= RAIL_BAND[1])
            nb = int(band.sum())
            vc_ = (b0 + b1) // 2
            e = {"rows": f"v{b0}-{b1}", "edge_offset_m": r(np.median(arr[b0:b1 + 1]), 2),
                 "edge_minus_design_m": r(np.median(arr[b0:b1 + 1] - dsn[b0:b1 + 1]), 2),
                 "window_returns": int(W.sum()), "band_returns": nb,
                 "band_bank_side": int((band & (d >= 0)).sum()), "band_road_side": int((band & (d < 0)).sum()),
                 "ge_0.25_lt_0.5": int((W & (h >= 0.25) & (h < RAIL_BAND[0])).sum()),
                 "gt_1.2_le_1.5": int((W & (h > RAIL_BAND[1]) & (h <= RAIL_HIGH)).sum()),
                 "gt_1.5": int((W & (h > RAIL_HIGH)).sum()),
                 "band_ground_far": int((band & gfar).sum())}
            # ground across the edge at the bin's middle row (TIN, engine y), d = + toward the bank
            ds = np.array([-1.0, -0.5, 0.0, 0.5, 1.0, 1.5])
            oo = arr[vc_] + sign * ds
            gy_ = tin(xz[vc_, 0] + oo * nrm[vc_, 0], xz[vc_, 1] + oo * nrm[vc_, 1]) - ENGINE_DY
            e["ground_y_across_mid_row"] = {f"{dv:+.1f}": r(g, 2) for dv, g in zip(ds, gy_)}
            # wide lateral histogram of the band returns (all of RAIL_WIDE)
            bw = kb & (h >= RAIL_BAND[0]) & (h <= RAIL_BAND[1])
            hb = np.histogram(d[bw], bins=np.arange(RAIL_WIDE[0], RAIL_WIDE[1] + 1e-9, 0.25))[0]
            pk = int(np.argmax(hb)) if hb.sum() else None
            e["wide_band_returns"] = int(bw.sum())
            e["wide_peak_d_m"] = r(RAIL_WIDE[0] + 0.25 * (pk + 0.5), 3) if pk is not None else None
            e["wide_peak_share_0.75m"] = r(hb[max(0, pk - 1):pk + 2].sum() / hb.sum(), 3) if pk is not None else None
            if nb:
                db, hbv, sb_ = d[band], h[band], sa[band]
                dm = float(np.median(db))
                spot = W & (np.abs(d - dm) <= SPOT_HALF)
                bs = spot & band
                s_lo, s_hi = sl_at(b0 - 0.5), sl_at(b1 + 0.5)
                nsl = max(1, int(round((s_hi - s_lo) / SLICE_M)))
                hit = np.unique(np.clip(((sa[bs] - s_lo) / (s_hi - s_lo) * nsl).astype(int), 0, nsl - 1))
                e.update({"d_median_m": r(dm, 2), "d_p25_m": r(np.percentile(db, 25), 2), "d_p75_m": r(np.percentile(db, 75), 2),
                          "d_iqr_m": r(np.percentile(db, 75) - np.percentile(db, 25), 2),
                          "h_median_m": r(np.median(hbv), 2), "h_iqr_m": r(np.percentile(hbv, 75) - np.percentile(hbv, 25), 2),
                          "spot_band": int(bs.sum()), "spot_gt_1.5": int((spot & (h > RAIL_HIGH)).sum()),
                          "spot_h_p90_m": r(np.percentile(h[spot], 90), 2) if spot.any() else None,
                          "continuity": r(len(hit) / nsl, 2), "slices": nsl})
                if nb >= 4 and np.ptp(sb_) > 1:
                    cf = np.polyfit(sb_, db, 1)
                    e["line_fit_rms_m"] = r(np.sqrt(np.mean((db - np.polyval(cf, sb_)) ** 2)), 2)
            if nb < N_MIN:
                verdict = "nothing"
            else:
                ok = (e["d_iqr_m"] <= RAIL_IQR_D and e["h_iqr_m"] <= RAIL_IQR_H and e["continuity"] >= RAIL_CONT
                      and e["spot_gt_1.5"] <= RAIL_HIGH_RATIO * max(e["spot_band"], 1))
                verdict = "rail-like" if ok else "vegetation"
                if not ok and e["d_median_m"] < -0.5 and e["gt_1.5"] < 0.25 * nb:
                    e["note"] = "mostly on the road side of the edge, little over 1.5 m: vehicles or the curb face, not the bank"
                if (e["d_iqr_m"] <= RAIL_IQR_D and e["continuity"] >= RAIL_CONT and e["spot_gt_1.5"] > RAIL_HIGH_RATIO * e["spot_band"]):
                    e["tall_line"] = True
            e["verdict"] = verdict
            rows.append(e)
        vs_ = [e["verdict"] for e in rows]
        rl = np.array([x == "rail-like" for x in vs_])
        run = best = 0
        for x in rl:
            run = run + 1 if x else 0
            best = max(best, run)
        share = float(rl.mean())
        if share >= PRESENT_SHARE and best >= PRESENT_RUN:
            overall = "present"
        elif share <= ABSENT_SHARE and best < ABSENT_RUN:
            overall = "absent"
        else:
            overall = "cannot tell"
        railb = [e for e in rows if e["verdict"] == "rail-like"]
        summ = {"bins": len(rows), "rail_like": int(rl.sum()), "vegetation": vs_.count("vegetation"),
                "nothing": vs_.count("nothing"), "rail_like_share": round(share, 3), "longest_rail_like_run_bins": int(best),
                "verdict": overall,
                "band_returns_total": int(sum(e["band_returns"] for e in rows)),
                "band_returns_per_m": r(sum(e["band_returns"] for e in rows) / (s_lap[V_RAIL[1]] - s_lap[V_RAIL[0]]), 3),
                "band_returns_per_bin": pct([e["band_returns"] for e in rows], (0, 10, 50, 90, 100), 0),
                "gt_1.5_per_bin": pct([e["gt_1.5"] for e in rows], (0, 10, 50, 90, 100), 0)}
        if railb:
            summ["rail_like_d_median_m"] = r(np.median([e["d_median_m"] for e in railb]), 2)
            summ["rail_like_h_median_m"] = r(np.median([e["h_median_m"] for e in railb]), 2)
            summ["rail_like_rows"] = [e["rows"] for e in railb]
        return summ, rows

    rail_nb = rail("nb_inner")
    rail_sb = rail("sb_inner")
    rail_nbd = rail("nb_inner", use_design=True)
    log(f"rail nb (design edge) {rail_nbd[0]['verdict']} {rail_nbd[0]['rail_like']}/{rail_nbd[0]['bins']}")
    log(f"rail nb {rail_nb[0]['verdict']} {rail_nb[0]['rail_like']}/{rail_nb[0]['bins']}; sb {rail_sb[0]['verdict']} {rail_sb[0]['rail_like']}/{rail_sb[0]['bins']}")

    # ================================================================ write
    inputs = {p.name: md5(p) for p in [inp / "college_edges.json", inp / "college_design.json",
                                       inp / "college_xsec.lidar.g10.json", inp / "college_plants.report.json",
                                       inp / "trackdata" / "centerline.local.json", sdir / "lm_shrub.tops.npz"]}
    frame = {"what": "Lake Murray engine frame = data/centerline.local.json: x east, z north (m); y = NAVD88 - 100.8",
             "origin": cl["origin"],
             "projection": "shrub_heights.Track (the lm-shrub tool's own code, imported): UTM EPSG %d <-> EPSG:4326 by pyproj, "
                           "x = (lon - lon0) * m_lon, z = (lat - lat0) * m_lat, WGS84 series at lat0; the same as "
                           "job1_college_lidar.py" % epsg,
             "tops_npz_frame": "x, z = this frame (shrub_heights.Track.to_local of E, N); E, N = UTM EPSG 6340",
             "tops_npz_xz_vs_EN_max_m": r(frame_err, 4),
             "station_offset": "v = the centreline vertex whose tangent foot is nearest (|along| smallest of the 4 nearest); "
                               "offset_m = (p - P_v) . n_v, + = left of travel (v increasing) = west on College northbound "
                               "(job1_college_lidar.py offset_doc; college_edges.json offset_sign); n_v checked against "
                               "college_xsec.lidar.g10.json nx, nz to %.1e" % dn,
             "centreline_md5_note": "centerline.local.json of f0c35e1f = the lm-shrub job's = lm-round2's (md5 identical)"}
    common_src = {"project": "USGS_LPC_CA_SanDiegoCo_D24", "epsg": epsg, "tiles_read": tiles_rep,
                  "classes_in_read_box": cls_box, "flown": "2024-11 (lm-shrub tiles.json)"}
    method_a = {
        "bank": "[from file] the band between nb_inner_smooth_m and sb_inner_smooth_m (college_edges.json, commit f0c35e1f) "
                "on every row v1172-1444; polygon = the ribbon P_v + nb_inner * n_v (v up) then P_v + sb_inner * n_v "
                "(v down), straight between rows; point-in-polygon = shrub_heights.inside",
        "bank_rows": "[from file] v1172-1444 (README 'the main island reads from v1172 to v1444'; college_design.json ISLAND)",
        "tops": "[measured, from lm_shrub.tops.npz] every top inside the polygon whatever its flags; h = second-highest "
                "return in the 3x3 0.5 m cells over the shrub mosaic ground, crown = 8 rays (the tool's [invented] "
                "H_MIN 0.3, TOP_R 1.0, EDGE_FRAC 0.5, RISE_M 0.15, RAY_MAX_M 6.0, SOLID_ROUGH 0.08, GROUND_FAR 3.0)",
        "flags": "solid / plant / stratum = the npz's own; ground_far = gdist > 3.0 m (shrub_heights GROUND_FAR [invented])",
        "y_ground": "[measured] the shrub mosaic ground (median class 2 per 1 m, gap-filled 1-16 m) at the top, bilinear, "
                    "- 100.8; y_top = y_ground + h",
        "in_design_bank": "[from file] also inside college_design.json's inner edges (smoothed, bridged) on the same rows",
        "raw_counts": "[measured] D24 returns not withheld, class 1 (3/4/5 are not used in D24) inside the polygon, height "
                      "over a TIN (Delaunay, linear) of the corridor's class-2 returns; '_mosaic' = over the shrub mosaic "
                      "ground instead (the ground the tops were found on)",
        "bins": "[from the request] 10 rows by nearest vertex; area = the ribbon's quads from row v to v+1",
        "cells": "[invented] 1 m cells whose centre is inside the polygon; 'covered' = 2+ returns >= 0.3 m (the tool's "
                 "own top rule at 1 m); 'no top within 3 m' = covered cells farther than %.1f m [invented] from any top of "
                 "the npz (any flag): where the tops file may have missed plants" % MISS_R,
        "reads": "[invented] bare = no 1 m cell with 2+ returns >= 0.5 m; sparse = under 10 %% of cells with a return >= 0.5 m; "
                 "planted = under 50 %%; dense = 50 %% or more",
        "corridor": f"[invented] rows v{V_CORR[0]}-{V_CORR[1]}, |offset| <= {OFF_CORR} m",
    }
    bank_tops = {
        "what": "College split: the measured plant tops on the bank between the carriageways (rows v1172-1444), and the raw "
                "lidar's non-ground returns there as a coverage check",
        "status": "measured", "tool": "college_bank.py (G10 job lm-college-bank-20261123)",
        "date": time.strftime("%Y-%m-%d"),
        "source": {**common_src, "tops": "the lm-shrub job's out_24tiles/lm_shrub.tops.npz (lm-shrub, 2026-11-16)"},
        "inputs_md5": inputs, "frame": frame, "method": method_a,
        "bank": {"rows": list(V_BANK), "polygon_vertices": int(len(poly)), "area_m2": round(bank_area, 1),
                 "width_m": pct(SB_IN[vb] - NB_IN[vb], (0, 10, 50, 90, 100), 2),
                 "edges_note": "college_edges.json's inner edges are 9-station medians of 0.5 m cells; README: single "
                               "stations misread under trees (the middle reads up to 17 m at v1297), so the polygon is "
                               "wider than the real bank around v1295-1301 and v1310-1322 (nb_inner -8 to -12.5 m against "
                               "about -6.5 m either side); in_design_bank marks the tops inside the design's bridged edges"},
        "summary": {
            "tops_in_bank": int(len(idx)), "plant": int(pl.sum()), "solid": int(T["solid"][idx].sum()),
            "ground_far": int(gfar.sum()), "near_footprint": int((T["d_bldg"][idx] < SH.BLDG_CLEAR).sum()),
            "in_design_bank": int(in_design.sum()),
            "h_m_all": pct(H_), "h_m_plant": pct(H_[pl]), "crown_d_m_plant": pct(T["crown_d"][idx][pl]),
            "plant_by_height": {"lt_1m": int((pl & (H_ < 1)).sum()), "1_3m": int((pl & (H_ >= 1) & (H_ < 3)).sum()),
                                "3_10m": int((pl & (H_ >= 3) & (H_ < 10)).sum()), "ge_10m": int((pl & (H_ >= 10)).sum())},
            "rows_with_a_plant_top": int(len(np.unique(v[pl]))),
            "bins_reading": {k: [e["rows"] for e in bins_a if e["reads"] == k] for k in ("bare", "sparse", "planted", "dense")}},
        "tops": tops,
        "coverage_per_10_rows": bins_a,
        "existing_bank_spots_vs_tops": {
            "what": "college_plants.report.json's spots on 'the bank' against the nearest top of the npz (a registration "
                    "check: the measured ones came off the same lidar)",
            "spots": len(spots), "tall_14": tall,
            "measured_dist_m": pct([s_["dist_m"] for s_ in spots if s_["measured"]], (0, 50, 90, 100), 2),
            "all": spots},
    }
    (out / "college_bank_tops.g10.json").write_text(json.dumps(bank_tops, indent=1), encoding="utf-8")

    method_b = {
        "edges": "[from file] nb_inner_smooth_m / sb_inner_smooth_m of college_edges.json, linear between rows; d = signed "
                 "distance from the edge, + toward the bank (nb: d = offset - nb_inner; sb: d = sb_inner - offset)",
        "rows": "[from file] v1176-1440, the rows step 3 authored its barrier on (STEP-DESIGN.md)",
        "returns": "[measured] D24 class 1 (all non-ground in D24), not withheld; height over a TIN of the corridor's "
                   "class-2 returns (the local ground under each return, steep bank included)",
        "window": f"[from the request] |d| <= {RAIL_WIN} m; band {RAIL_BAND[0]}-{RAIL_BAND[1]} m; 'high' > {RAIL_HIGH} m",
        "wide": f"[invented] d {RAIL_WIDE[0]} to +{RAIL_WIDE[1]} m: band returns' 0.25 m lateral histogram, its peak and "
                "the share within 0.75 m of it (finds a line that sits off a misread edge)",
        "spot": f"[invented] 'the same spot' = within {SPOT_HALF} m of the bin's lateral median of band returns",
        "continuity": f"[invented] share of {SLICE_M} m along-line slices of the bin holding a band return at the spot",
        "verdict_bin": f"[invented] nothing: under {N_MIN} band returns; rail-like: lateral IQR <= {RAIL_IQR_D} m, height IQR "
                       f"<= {RAIL_IQR_H} m, continuity >= {RAIL_CONT}, returns > 1.5 m at the spot <= {RAIL_HIGH_RATIO} x "
                       "the band's there; vegetation: the rest",
        "verdict_overall": f"[invented] present: >= {PRESENT_SHARE:.0%} of bins rail-like with a run of >= {PRESENT_RUN}; "
                           f"absent: <= {ABSENT_SHARE:.0%} rail-like and no run of {ABSENT_RUN}; else cannot tell",
        "ground_far": f"[invented] band returns more than {GROUND_FAR_TIN} m from any class-2 return are counted apart (TIN "
                      "spans a gap there)",
        "ground_y_across_mid_row": "[measured] TIN ground at d = -1 .. +1.5 m at the bin's middle row, engine y",
    }
    rail_doc = {
        "what": "College split: is there a rail / barrier at the top of the bank along the northbound road's inner edge? "
                "(the southbound inner edge as the control)",
        "status": "measured", "tool": "college_bank.py (G10 job lm-college-bank-20261123)", "date": time.strftime("%Y-%m-%d"),
        "source": common_src, "inputs_md5": inputs, "frame": frame, "method": method_b,
        "northbound_inner": {"summary": rail_nb[0], "bins": rail_nb[1]},
        "southbound_inner_control": {"summary": rail_sb[0], "bins": rail_sb[1]},
        "northbound_inner_vs_design_edge": {"what": "the same test along college_design.json's nb_inner (edges averaged over "
                                           "~33 m, misreads dropped and bridged, v1297-1300 bridged): covers v1296-1300, where "
                                           "college_edges.json's smoothed edge reads -12.5 m against about -7.7 m",
                                           "summary": rail_nbd[0], "bins": rail_nbd[1]},
    }
    (out / "college_bank_rail.g10.json").write_text(json.dumps(rail_doc, indent=1), encoding="utf-8")
    log("written", out)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    main()
