"""Milford's REAL road surface along the lap, from the 2017 lidar (Kevin 2026-11-24 on 0.1.15: "Road still wavy";
"I just want real"). Measures only; builds nothing. numpy + scipy (+ laspy/lazrs + pyproj for `read`).

Four subcommands:

  read     the raw LAZ returns near the lap -> one small npz (every return within KEEP_R_M of the line's stations, of
           the classes in KEEP_CLASSES, with its flight strip (point_source_id), GPS time and return numbers) and a
           table of every class found near the line. The frame is the G10 surface read's (the read the build's
           measured surface came from): each file's CRS from its header (none = EPSG:3857), to lon / lat by pyproj,
           to the port frame by mpd() about the line file's origin, then the plan shift the build applies
           (track.config.json terrain.lidar_shift_m = the measured surface's registration_lidar_shift_m, measured on
           0.1.11's built OBJ), and z + DATUM_M - origin.elev_m (the datum the same read carries: built - lidar on the
           centre path, the deck's +0.10 inside it). The lidar's node directories are a UNION by EPT node key, first
           directory wins, read in file-name order (the G10 read's order).
  control  this script's plane at the G10 surface read's own centre-path points (that read's y_m): the frame, the
           shift, the datum and the plane reproduced, or not.
  profile  per 0.5 m station of the line (wavy_survey's stations(): n = round(lap / 0.5), equal steps) and per path
           (the lane centre and two wheel paths, +-WHEEL_M), a robust plane through the returns within LIDAR_R_M
           (wavy_survey's _plane(): two trimming passes at TRIM_SIGMA, >= LIDAR_MIN_N returns; its constant term is the
           height): the merged profile, its noise, the strips in the disc. Per strip, its level (the merged plane +
           its mean residual about it, >= STRIP_MIN_N of its kept returns: the strip's own profile used below; where
           it covers alone, the merged profile itself) and its independent plane (>= LIDAR_MIN_N of its returns, kept
           only where the returns' geometry pins its height); where two strips share a disc, their offset (the
           difference of their levels: wavy_survey's strip_spread, signed). Then the strips are levelled (a constant
           per strip, least squares over every overlap station, the strips' point-weighted mean held at 0; and a
           variant linear in GPS time per strip [invented: the low-order fit]) and the merged planes refit on the
           levelled returns. Then the metrics (below) per 100 m of s and per path.
  built    the same metrics on the build's own road profile, read from the committed files only (no mesh): the
           measured-surface fit product (c + u b, tools/measured_surface.py's Product.at by position, the deck inside
           c) plus the banked turn's section (delta at the path's offset, densify's taper over its spans), and as a
           cross-check the line file's own heights (Y + DECK_M + u tan(bank), the bank from the crossfall file).

The metrics, per 100 m of s and per path (every one a choice, marked [invented] where it is):
  2-30 m     r = z - its 30 m centred moving average [invented, as asked], then band-limited to 2 <= wavelength < 30 m
             (FFT on the closed lap; gaps filled linearly first and counted per window, the RMS over measured
             stations only); its RMS and peak-to-peak; the dominant wavelength (the largest Hann-windowed spectral
             maximum of r in the window, 2-30 m; flagged at_band_edge where it sits on a band limit: no peak inside);
             the noise floor [model]: wavy_survey's noise model (each station's cal x fit_sd / sqrt(kept returns), cal
             measured on this read's split halves, K draws correlated over the disc) through the same band.
  grade      the steepest 5 m grade change [invented, as asked]: max |(z(s+5) - z(s)) / 5 - (z(s) - z(s-5)) / 5|, %,
             on the raw z(s) (no filter), with its s and its noise (the same formula on the per-station noise).
  30-60 / 60-120 m   the band RMS of z(s) itself (FFT band, closed lap), the band the PC builder's measurements point
             at: merged, per strip (band(merged + the strip's level offset) on the closed lap, reported on the
             strip's runs at least 2 x the band's long end, not within the long end of a run's end), and levelled;
             and the overlap offset series' own band against its noise [model].

    python road_profile_lidar.py read --line centerline.local.json --lidar DIR [--lidar DIR ...] --out points.npz
    python road_profile_lidar.py control --line centerline.local.json --points points.npz --g10-read READ.json
    python road_profile_lidar.py profile --line centerline.local.json --points points.npz --out profile.json
    python road_profile_lidar.py built --profile profile.json --fit road_surface_gm.fit.json \
        --section road_section_gm.json --crossfall crossfall.lm.json --line centerline.local.json \
        --measured-surface measured_surface.py [--section-spans 870,1030] [--section-taper 15] --out OUT.json
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------- constants
STEP_M = 0.5            # station spacing (wavy_survey's STEP_M)
WHEEL_M = 0.8           # [invented, as asked] the wheel paths' offset from the lane centre
LIDAR_R_M = 1.25        # wavy_survey's plane radius [invented there; 1.2-2.9 ground returns / m2 measured]
LIDAR_MIN_N = 6         # wavy_survey's [invented]
TRIM_SIGMA = 2.5        # wavy_survey's [invented]
STRIP_MIN_N = 3         # wavy_survey's strip_spread: >= 3 returns of each strip in the disc
OWN_PLANE_SE_M = 0.015  # [invented] a strip's independent plane is kept where its constant's SE (geometry) is under this
KEEP_R_M = 3.0          # read: keep returns within this of a centre-line station (paths +-0.8 + the 1.25 m disc)
KEEP_CLASSES = (2, 11)  # ground; 11 = ASPRS road surface (kept if the cloud has it: the class table says)
SHIFT_M = (-0.375, 0.938)   # terrain.lidar_shift_m (dE, dN): the measured surface's registration
DATUM_M = 0.1058        # the G10 read's built - lidar on the centre path (the deck's +0.10 inside)
NOISE_CAL = 1.435       # the G10 GM read's split-half / standard-error calibration (noise.cal_split_half_over_se)
DECK_M = 0.10           # lm_intake.measured_surface.deck_m
WIN_M = 100.0           # [as asked] the reporting window
MA_M = 30.0             # [invented, as asked] the trend removed before the 2-30 m band
BAND_LO_M, BAND_HI_M = 2.0, 30.0
GRADE_BASE_M = 5.0      # [invented, as asked]
LONG_BANDS = ((30.0, 60.0), (60.0, 120.0))


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def mpd(lat0):
    """metres per degree (lon, lat) at lat0: wavy_survey's / ept_fetch's"""
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


# ---------------------------------------------------------------- the line
def load_line(path):
    d = json.loads(Path(path).read_text())
    P = np.asarray(d["points_xyz_m"], float)
    W = np.asarray(d.get("widths_m") or [11.0] * len(P), float)
    if math.hypot(P[-1, 0] - P[0, 0], P[-1, 2] - P[0, 2]) > 1e-6:      # close the lap
        P = np.vstack([P, P[:1]]); W = np.r_[W, W[0]]
    seg = np.hypot(np.diff(P[:, 0]), np.diff(P[:, 2]))
    keep = np.r_[True, seg > 1e-6]
    return P[keep], W[keep], d["origin"]


def stations(P, W, step=STEP_M):
    """wavy_survey.stations(): equal steps on the closed lap, the normal + = left of travel"""
    s = np.r_[0, np.cumsum(np.hypot(np.diff(P[:, 0]), np.diff(P[:, 2])))]
    lap = s[-1]; n = int(round(lap / step)); su = np.arange(n) * lap / n
    X, Y, Z = [np.interp(su, s, P[:, k]) for k in (0, 1, 2)]
    HW = np.interp(su, s, W) / 2
    tx = np.roll(X, -1) - np.roll(X, 1); tz = np.roll(Z, -1) - np.roll(Z, 1)
    L = np.hypot(tx, tz); tx /= L; tz /= L
    return dict(s=su, lap=float(lap), n=n, X=X, Y=Y, Z=Z, HW=HW, tx=tx, tz=tz, nx=-tz, nz=tx)


# ---------------------------------------------------------------- read
def node_files(dirs):
    nodes, src = {}, {}
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, "**", "*.laz"), recursive=True)):
            k = Path(f).stem
            if k not in nodes:
                nodes[k], src[k] = f, d
    return nodes, src


def cmd_read(a):
    import laspy
    from pyproj import CRS, Transformer
    from scipy.spatial import cKDTree
    t0 = time.time()
    P, W, origin = load_line(a.line)
    st = stations(P, W)
    tree = cKDTree(np.c_[st["X"], st["Z"]])
    m_lon, m_lat = mpd(origin["lat"])
    to_ll_3857 = Transformer.from_crs(3857, 4326, always_xy=True)
    lo_e, hi_e = st["X"].min() - KEEP_R_M - 5, st["X"].max() + KEEP_R_M + 5
    lo_n, hi_n = st["Z"].min() - KEEP_R_M - 5, st["Z"].max() + KEEP_R_M + 5
    nodes, src = node_files(a.lidar)
    keys = sorted(nodes, key=lambda k: os.path.basename(nodes[k]))
    out = {k: [] for k in ("e", "n", "z", "cls", "psid", "t", "ret", "nret", "node")}
    cls_near = {}
    psid_near = {}
    used = {d: 0 for d in a.lidar}; skipped = 0; read_pts = 0; tcache = {}; fmt = set(); key_list = []
    for k in keys:
        f = nodes[k]
        with laspy.open(f) as r:
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
                tcache[ck] = (Transformer.from_crs(hcrs, 4326, always_xy=True), zf, hcrs.name)
            to_ll, zf, hname = tcache[ck]
            # the node's box in the port frame (corners through the header's CRS): skip one that cannot reach the line
            lon_c, lat_c = to_ll.transform([h.mins[0], h.maxs[0], h.mins[0], h.maxs[0]],
                                           [h.mins[1], h.mins[1], h.maxs[1], h.maxs[1]])
            ec = (np.asarray(lon_c) - origin["lon"]) * m_lon + SHIFT_M[0]
            nc = (np.asarray(lat_c) - origin["lat"]) * m_lat + SHIFT_M[1]
            e0, e1, n0, n1 = ec.min(), ec.max(), nc.min(), nc.max()
            if e1 < lo_e or e0 > hi_e or n1 < lo_n or n0 > hi_n:
                skipped += 1; continue
            rad = 0.5 * math.hypot(e1 - e0, n1 - n0) + KEEP_R_M + 1.0
            if not tree.query_ball_point([(e0 + e1) / 2, (n0 + n1) / 2], rad):
                skipped += 1; continue
            used[src[k]] += 1
            fmt.add(int(h.point_format.id))
            ki = len(key_list); key_list.append(k)
            for ch in r.chunk_iterator(a.chunk):
                read_pts += len(ch)
                lon, lat = to_ll.transform(np.asarray(ch.x), np.asarray(ch.y))
                e = (lon - origin["lon"]) * m_lon + SHIFT_M[0]
                nn = (lat - origin["lat"]) * m_lat + SHIFT_M[1]
                box = (e > lo_e) & (e < hi_e) & (nn > lo_n) & (nn < hi_n)
                if not box.any():
                    continue
                idx = np.flatnonzero(box)
                dd, _ = tree.query(np.c_[e[idx], nn[idx]], distance_upper_bound=KEEP_R_M)
                idx = idx[np.isfinite(dd)]
                if not len(idx):
                    continue
                cl = np.asarray(ch.classification)[idx]
                ps = np.asarray(ch.point_source_id)[idx]
                for c_, n_ in zip(*np.unique(cl, return_counts=True)):
                    cls_near[int(c_)] = cls_near.get(int(c_), 0) + int(n_)
                g = np.isin(cl, KEEP_CLASSES)
                for p_, n_ in zip(*np.unique(ps[g], return_counts=True)):
                    psid_near[int(p_)] = psid_near.get(int(p_), 0) + int(n_)
                idx = idx[g]
                if not len(idx):
                    continue
                out["e"].append(e[idx]); out["n"].append(nn[idx])
                out["z"].append(np.asarray(ch.z)[idx] * zf + DATUM_M - float(origin["elev_m"]))
                out["cls"].append(cl[g].astype(np.uint8)); out["psid"].append(ps[g].astype(np.int32))
                gt = np.asarray(ch.gps_time)[idx] if "gps_time" in ch.point_format.dimension_names else np.zeros(len(idx))
                out["t"].append(gt.astype(np.float64))
                out["ret"].append(np.asarray(ch.return_number)[idx].astype(np.uint8))
                out["nret"].append(np.asarray(ch.number_of_returns)[idx].astype(np.uint8))
                out["node"].append(np.full(len(idx), ki, np.int16))
    arr = {k: (np.concatenate(v) if v else np.zeros(0)) for k, v in out.items()}
    rep = {"what": "road_profile_lidar.py read", "line": {"file": Path(a.line).name, "md5": md5(a.line),
                                                          "lap_m": round(st["lap"], 2), "stations": st["n"]},
           "origin": origin, "shift_m": list(SHIFT_M), "datum_m": DATUM_M, "keep_r_m": KEEP_R_M,
           "keep_classes": list(KEEP_CLASSES), "nodes_read": len(key_list), "nodes_skipped": skipped,
           "nodes_read_per_dir_index": [used[d] for d in a.lidar], "points_in_nodes_read": int(read_pts),
           "point_formats": sorted(fmt), "crs": sorted({v[2] for v in tcache.values()}),
           "classes_within_keep_r": {str(k): v for k, v in sorted(cls_near.items())},
           "kept_points": int(len(arr["e"])),
           "kept_per_point_source_id": {str(k): v for k, v in sorted(psid_near.items())},
           "wall_s": round(time.time() - t0, 1)}
    np.savez_compressed(a.out, **arr, node_keys=np.array(key_list))
    Path(str(a.out) + ".report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


# ---------------------------------------------------------------- planes
def _plane(dx, dz, h, nmin):
    """wavy_survey._plane(): least squares, two trimming passes at TRIM_SIGMA x 1.4826 MAD (floor 1 cm)"""
    keep = np.ones(len(h), bool); coef = None
    for _ in range(2):
        if keep.sum() < nmin:
            return None, None, keep
        A = np.c_[np.ones(keep.sum()), dx[keep], dz[keep]]
        coef = np.linalg.lstsq(A, h[keep], rcond=None)[0]
        res = h - (coef[0] + coef[1] * dx + coef[2] * dz)
        s_ = max(0.01, 1.4826 * np.median(np.abs(res[keep])))
        keep = np.abs(res) <= TRIM_SIGMA * s_
    if keep.sum() < nmin:
        return None, None, keep
    return coef, res, keep




def disc_fit(E, N, Z, S, T, idx, x, z):
    """the merged plane at (x, z) through the returns idx, its split halves and its strips"""
    out = {"h": np.nan, "n": 0, "nd": len(idx), "sd": np.nan, "ha": np.nan, "hb": np.nan, "strips": {}}
    if len(idx) < LIDAR_MIN_N:
        out["strips"] = {int(u): {"nd": int((S[idx] == u).sum())} for u in np.unique(S[idx])} if len(idx) else {}
        return out
    c = np.asarray(sorted(idx)); dx, dz, h = E[c] - x, N[c] - z, Z[c]
    coef, res, keep = _plane(dx, dz, h, LIDAR_MIN_N)
    ss = S[c]
    strips = {}
    for u in np.unique(ss):
        m = ss == u
        rec = {"nd": int(m.sum())}
        if coef is not None:
            mk = m & keep
            rec["nk"] = int(mk.sum())
            if mk.sum() >= STRIP_MIN_N:
                rec["r"] = float(res[mk].mean()); rec["rse"] = float(res[mk].std() / math.sqrt(mk.sum()))
                rec["t"] = float(T[c][mk].mean())
        if m.sum() >= LIDAR_MIN_N:                                  # the strip's own, independent plane
            cs, rs, ks = _plane(dx[m], dz[m], h[m], LIDAR_MIN_N)
            if cs is not None:
                # its constant's standard error from the returns' geometry: at a swath's edge 6-8 returns can lie
                # along one scan line and the plane's tilt across it (so its height at the disc's centre) runs away
                A = np.c_[np.ones(ks.sum()), dx[m][ks], dz[m][ks]]
                try:
                    c00 = float(np.linalg.inv(A.T @ A)[0, 0])
                except np.linalg.LinAlgError:
                    c00 = np.inf
                se0 = max(0.01, float(np.std(rs[ks]))) * math.sqrt(max(c00, 0.0))
                if se0 <= OWN_PLANE_SE_M:
                    rec["h"] = float(cs[0]); rec["hn"] = int(ks.sum()); rec["hse"] = se0
        strips[int(u)] = rec
    out["strips"] = strips
    if coef is None:
        return out
    out["h"], out["n"], out["sd"] = float(coef[0]), int(keep.sum()), float(np.std(res[keep]))
    for half, key in ((slice(0, None, 2), "ha"), (slice(1, None, 2), "hb")):
        ch, _, _ = _plane(dx[half], dz[half], h[half], LIDAR_MIN_N)
        if ch is not None:
            out[key] = float(ch[0])
    return out


# ---------------------------------------------------------------- signal tools (the closed lap)
def fill(v):
    ok = np.isfinite(v)
    if ok.all() or not ok.any():
        return v.copy(), ok
    i = np.arange(len(v))
    return np.interp(i, i[ok], v[ok], period=len(v)), ok


def band_fft(v, lo_m, hi_m, step=STEP_M):
    """lo_m <= wavelength < hi_m, FFT on the closed lap (measured_surface._bands' mask)"""
    n = len(v); f = np.fft.rfftfreq(n, d=step); F = np.fft.rfft(v - v.mean())
    lam = np.where(f > 0, 1.0 / np.maximum(f, 1e-12), np.inf)
    F[(lam < lo_m) | (lam >= hi_m)] = 0
    return np.fft.irfft(F, n)


def moving_average(v, win_m, step=STEP_M):
    k = int(round(win_m / step)) | 1                                   # odd, centred
    h = k // 2
    ext = np.r_[v[-h:], v, v[:h]]
    c = np.cumsum(np.r_[0.0, ext])
    return (c[k:] - c[:-k]) / k


def short_band(v):
    """the 2-30 m waviness: z less its 30 m moving average, then 2 <= wavelength < 30 m"""
    return band_fft(v - moving_average(v, MA_M), BAND_LO_M, BAND_HI_M)


def band_run(v, lo_m, hi_m, step=STEP_M):
    """a band of one open run (a strip's own profile): mirrored at both ends first (measured_surface.section's way)"""
    n = len(v)
    ext = np.concatenate([v[::-1], v, v[::-1]])
    f = np.fft.rfftfreq(3 * n, d=step); F = np.fft.rfft(ext - ext.mean())
    lam = np.where(f > 0, 1.0 / np.maximum(f, 1e-12), np.inf)
    F[(lam < lo_m) | (lam >= hi_m)] = 0
    return np.fft.irfft(F, 3 * n)[n:2 * n]


def peak_wavelength(v, lo_m, hi_m, step=STEP_M, pad=16):
    """the wavelength of the largest Hann-windowed spectral peak of v (one window), lo..hi m. A maximum on the band's
    edge (within EDGE_FRAC) is no peak: the spectrum keeps rising past the band (a road's height spectrum is red);
    returned as the edge with the flag."""
    v = v[np.isfinite(v)]
    if len(v) < 8:
        return None, None
    x = (v - v.mean()) * np.hanning(len(v))
    F = np.abs(np.fft.rfft(x, pad * len(v))); f = np.fft.rfftfreq(pad * len(v), d=step)
    m = (f >= 1 / hi_m) & (f <= 1 / lo_m)
    if not m.any():
        return None, None
    lam = float(1 / f[m][np.argmax(F[m])])
    edge = lam >= hi_m * (1 - EDGE_FRAC) or lam <= lo_m * (1 + EDGE_FRAC)
    return round(lam, 1), bool(edge)


EDGE_FRAC = 0.03        # [invented] a spectral maximum within 3 % of a band's limit is the edge, not a peak


def grade_change(v, base_m=GRADE_BASE_M, step=STEP_M):
    """(z(s+b) - z(s)) / b - (z(s) - z(s-b)) / b, the closed lap, NaN where any of the three is a gap"""
    k = int(round(base_m / step))
    return ((np.roll(v, -k) - v) - (v - np.roll(v, k))) / base_m


def r4(v, nd=4):
    return None if v is None or not np.isfinite(v) else round(float(v), nd)


def arr(v, nd=4):
    return [None if not np.isfinite(x) else round(float(x), nd) for x in v]


def runs_of(ok, max_gap):
    """contiguous runs of True (gaps up to max_gap stations bridged), open (no wrap); [(i0, i1)] inclusive"""
    idx = np.flatnonzero(ok)
    if not len(idx):
        return []
    out, a, b = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - b - 1 <= max_gap:
            b = i
        else:
            out.append((int(a), int(b))); a = b = i
    out.append((int(a), int(b)))
    return out


# ---------------------------------------------------------------- profile
NOISE_DRAWS = 12        # wavy_survey's noise_model: K draws [model]
NOISE_SEED = 20261124
STRIP_RUN_GAP = 4       # [invented] a strip's own profile bridges gaps up to 4 stations (2 m) inside a run
OFFSET_RUN_GAP = 40     # [invented] the overlap offset series bridges gaps up to 40 stations (20 m) inside a zone
COVER_MIN = 0.5         # [invented] a window reports a strip's band where the strip covers half its stations
RIDGE = 1e-3            # [invented] the time-linear levelling: a tiny ridge on the slopes (the min-norm answer)


def noise_draws(sigma, rng, K=NOISE_DRAWS):
    """K draws of N(0, sigma) per station, correlated over the disc's diameter (wavy_survey's noise_model) [model]"""
    n = len(sigma); L = max(1, int(round(2 * LIDAR_R_M / STEP_M)))
    sig = np.nan_to_num(sigma, nan=0.0)
    out = []
    for _ in range(K):
        w = rng.standard_normal(n)
        w = np.convolve(np.r_[w[-(L - 1):], w] if L > 1 else w, np.ones(L) / L, "valid") * math.sqrt(L)
        out.append(w * sig)
    return out


def win_index(s, lap):
    nw = int(math.ceil(lap / WIN_M - 1e-9))
    return np.minimum((s // WIN_M).astype(int), nw - 1), nw


def rms(v):
    v = v[np.isfinite(v)]
    return float(np.sqrt(np.mean(v ** 2))) if len(v) else np.nan


def longest_gap_start(ok):
    """the first index of the longest run of False on the closed lap"""
    n = len(ok); best, start, run = 0, 0, 0
    for i in range(2 * n):
        if not ok[i % n]:
            run += 1
            if best < run <= n:
                best, start = run, i - run + 1
        else:
            run = 0
    return start % n


def strip_band(Hf, r, lo, hi, max_gap):
    """a strip's own profile is the merged profile plus its level about the merged plane (r, NaN off the strip), so
    its band is band(Hf + r filled with 0) on the closed lap: no mirrored ends (a brick-wall band leaks a run end's
    slope kink centimetres deep into the run). Reported only on the strip's runs (gaps <= max_gap bridged) at least
    2 x hi long, and not within hi of a run's end (there the band reads the merged profile past the strip's end)."""
    n = len(Hf); ok = np.isfinite(r)
    out = np.full(n, np.nan)
    if not ok.any():
        return out, []
    full = band_fft(Hf + np.where(ok, r, 0.0), lo, hi)
    if ok.all():
        return full, [[0, n - 1]]
    g = longest_gap_start(ok)                    # the array opened in the strip's longest gap: no run split at its ends
    okr = np.roll(ok, -g)
    mask = np.zeros(n, bool); used = []
    e = int(round(hi / STEP_M))
    for i0, i1 in runs_of(okr, max_gap):
        if (i1 - i0 + 1) * STEP_M < 2 * hi:
            continue
        mask[i0 + e:i1 - e + 1] = True
        used.append([int((i0 + g) % n), int((i1 + g) % n)])
    mask = np.roll(mask, g)
    return np.where(mask & ok, full, np.nan), used


def cmd_profile(a):
    from scipy.spatial import cKDTree
    t0 = time.time()
    P, W, origin = load_line(a.line)
    st = stations(P, W); n = st["n"]; s = st["s"]; lap = st["lap"]
    D = np.load(a.points)
    E, N, Z, S, T = D["e"], D["n"], D["z"], D["psid"].astype(int), D["t"]
    tree = cKDTree(np.c_[E, N])
    offs = (-WHEEL_M, 0.0, WHEEL_M); keys = [f"{u:+.1f}" for u in offs]
    strips = [int(u) for u in np.unique(S)]
    w_strip = {k: float((S == k).sum()) for k in strips}
    tbar = {k: float(T[S == k].mean()) for k in strips}
    PX = {k: st["X"] + u * st["nx"] for u, k in zip(offs, keys)}
    PZ = {k: st["Z"] + u * st["nz"] for u, k in zip(offs, keys)}
    lists = {k: tree.query_ball_point(np.c_[PX[k], PZ[k]], LIDAR_R_M) for k in keys}

    # pass 1: the merged planes, the halves, the strips
    F = {k: [disc_fit(E, N, Z, S, T, lists[k][i], PX[k][i], PZ[k][i]) for i in range(n)] for k in keys}
    col = lambda k, f: np.array([x[f] for x in F[k]], float)                                   # noqa: E731
    H = {k: col(k, "h") for k in keys}
    NR = {k: col(k, "n") for k in keys}
    ND = {k: col(k, "nd") for k in keys}
    SD = {k: col(k, "sd") for k in keys}
    HS = {k: np.abs(col(k, "ha") - col(k, "hb")) / 2 for k in keys}
    SE = {k: np.where(NR[k] >= 1, SD[k] / np.sqrt(np.maximum(NR[k], 1)), np.nan) for k in keys}
    both = np.concatenate([np.isfinite(HS[k]) & np.isfinite(SE[k]) for k in keys])
    A_ = np.concatenate([HS[k] for k in keys])[both]; B_ = np.concatenate([SE[k] for k in keys])[both]
    cal = float(np.sqrt(np.mean(A_ ** 2)) / np.sqrt(np.mean(B_ ** 2)))
    SIG = {k: cal * SE[k] for k in keys}

    def strip_col(k, sid, f):
        return np.array([x["strips"].get(sid, {}).get(f, np.nan) for x in F[k]], float)
    SC = {k: {sid: strip_col(k, sid, "nd") for sid in strips} for k in keys}          # returns of each strip in the disc
    SH = {k: {sid: strip_col(k, sid, "h") for sid in strips} for k in keys}           # the strip's own plane
    SHE = {k: {sid: strip_col(k, sid, "hse") for sid in strips} for k in keys}
    SR = {k: {sid: strip_col(k, sid, "r") for sid in strips} for k in keys}           # mean residual about the merged
    SRE = {k: {sid: strip_col(k, sid, "rse") for sid in strips} for k in keys}
    STm = {k: {sid: strip_col(k, sid, "t") for sid in strips} for k in keys}

    # the overlap offsets: later strip minus earlier (by id), per station, where both have >= STRIP_MIN_N kept returns
    pairs = [(strips[i], strips[j]) for i in range(len(strips)) for j in range(i + 1, len(strips))]
    OFF = {k: {} for k in keys}; OFFE = {k: {} for k in keys}
    obs_c, obs_l = [], []
    for k in keys:
        for sa, sb in pairs:
            d = SR[k][sb] - SR[k][sa]
            e = np.sqrt(SRE[k][sa] ** 2 + SRE[k][sb] ** 2)
            OFF[k][(sa, sb)] = d; OFFE[k][(sa, sb)] = e
            for i in np.flatnonzero(np.isfinite(d)):
                obs_c.append((sa, sb, d[i]))
                obs_l.append((sa, sb, d[i], STm[k][sa][i] - tbar[sa], STm[k][sb][i] - tbar[sb]))
    si = {sid: j for j, sid in enumerate(strips)}
    m = len(strips)
    lev = {"constant": None, "linear_gps_time": None}
    if obs_c:
        A = np.zeros((len(obs_c) + 1, m)); y = np.zeros(len(obs_c) + 1)
        for r_, (sa, sb, d) in enumerate(obs_c):
            A[r_, si[sb]] += 1; A[r_, si[sa]] -= 1; y[r_] = d
        wsum = sum(w_strip.values())
        A[-1] = [1e3 * w_strip[sid] / wsum for sid in strips]
        oc = np.linalg.lstsq(A, y, rcond=None)[0]
        res_c = A[:-1] @ oc - y[:-1]
        lev["constant"] = {"offset_m": {str(sid): round(float(oc[si[sid]]), 4) for sid in strips},
                           "held": "the strips' point-weighted mean at 0 (weights: each strip's returns near the lap)",
                           "observations": len(obs_c), "residual_rms_m": round(float(np.sqrt(np.mean(res_c ** 2))), 4)}
        A2 = np.zeros((len(obs_l) + 1 + m, 2 * m)); y2 = np.zeros(len(obs_l) + 1 + m)
        for r_, (sa, sb, d, ta, tb) in enumerate(obs_l):
            A2[r_, si[sb]] += 1; A2[r_, si[sa]] -= 1
            A2[r_, m + si[sb]] += tb; A2[r_, m + si[sa]] -= ta; y2[r_] = d
        A2[len(obs_l), :m] = [1e3 * w_strip[sid] / wsum for sid in strips]
        for j in range(m):
            A2[len(obs_l) + 1 + j, m + j] = RIDGE
        ol = np.linalg.lstsq(A2, y2, rcond=None)[0]
        res_l = A2[:len(obs_l)] @ ol - y2[:len(obs_l)]
        lev["linear_gps_time"] = {"offset_m_at_strip_mean_time": {str(sid): round(float(ol[si[sid]]), 4) for sid in strips},
                                  "slope_m_per_s": {str(sid): round(float(ol[m + si[sid]]), 5) for sid in strips},
                                  "strip_mean_gps_time": {str(sid): round(tbar[sid], 2) for sid in strips},
                                  "observations": len(obs_l), "residual_rms_m": round(float(np.sqrt(np.mean(res_l ** 2))), 4),
                                  "note": "a = offset at the strip's mean GPS time near the lap, b = its drift per second; "
                                          "a tiny ridge on b [invented] picks the min-norm answer where two slopes trade"}
        Zc = Z - np.array([oc[si[sid]] for sid in strips])[np.searchsorted(strips, S)]
        jj = np.searchsorted(strips, S)
        Zl = Z - (ol[jj] + ol[m + jj] * (T - np.array([tbar[sid] for sid in strips])[jj]))
    else:
        Zc = Zl = Z

    def refit(Zv):
        out = {}
        for k in keys:
            h = np.full(n, np.nan)
            for i in range(n):
                c = lists[k][i]
                if len(c) < LIDAR_MIN_N:
                    continue
                c = np.asarray(sorted(c))
                coef, _, _ = _plane(E[c] - PX[k][i], N[c] - PZ[k][i], Zv[c], LIDAR_MIN_N)
                if coef is not None:
                    h[i] = coef[0]
            out[k] = h
        return out
    HC = refit(Zc) if obs_c else H
    HL = refit(Zl) if obs_c else H

    # ------------------------------------------------ metrics
    wi, nw = win_index(s, lap)
    rng = np.random.default_rng(NOISE_SEED)
    variants = {"merged": H, "levelled_constant": HC, "levelled_linear_gps_time": HL}
    sig_draws = {k: noise_draws(SIG[k], rng) for k in keys}
    windows = [{"s0": round(j * WIN_M, 1), "s1": round(min(lap, (j + 1) * WIN_M), 1), "paths": {k: {} for k in keys}}
               for j in range(nw)]
    lapwide = {}
    for k in keys:
        ok = np.isfinite(H[k])
        vf, _ = fill(H[k])
        r30 = vf - moving_average(vf, MA_M)
        sb = short_band(vf)
        gc = grade_change(H[k])
        sgc = np.sqrt(np.roll(SIG[k], -10) ** 2 + 4 * SIG[k] ** 2 + np.roll(SIG[k], 10) ** 2) / GRADE_BASE_M
        nsb = [short_band(d) for d in sig_draws[k]]
        bands = {}
        for name, Hv in variants.items():
            hf, _ = fill(Hv[k])
            bands[name] = {f"{int(lo)}-{int(hi)}": band_fft(hf, lo, hi) for lo, hi in LONG_BANDS}
        nlong = {f"{int(lo)}-{int(hi)}": [band_fft(d, lo, hi) for d in sig_draws[k]] for lo, hi in LONG_BANDS}
        sband = {sid: {f"{int(lo)}-{int(hi)}": strip_band(vf, SR[k][sid], lo, hi, STRIP_RUN_GAP)[0] for lo, hi in LONG_BANDS}
                 for sid in strips}
        lapwide[k] = {"2-30 m_rms_cm": round(100 * rms(np.where(ok, sb, np.nan)), 2),
                      "2-30 m_noise_rms_cm [model]": round(100 * math.sqrt(np.mean([np.mean(x ** 2) for x in nsb])), 2),
                      **{f"{b}_m_rms_cm_{name}": round(100 * rms(np.where(ok, bands[name][b], np.nan)), 2)
                         for name in variants for b in bands[name]},
                      **{f"{b}_m_noise_rms_cm [model]": round(100 * math.sqrt(np.mean([np.mean(x ** 2) for x in nlong[b]])), 2)
                         for b in nlong},
                      **{f"{b}_m_removed_by_levelling_cm_{name}": round(100 * rms(np.where(ok, bands["merged"][b] - bands[name][b], np.nan)), 3)
                         for name in variants if name != "merged" for b in bands[name]}}
        for j in range(nw):
            m_ = wi == j; mo = m_ & ok
            rec = {"stations": int(m_.sum()), "gaps": int((m_ & ~ok).sum()),
                   "returns_p50": int(np.median(ND[k][m_])) if m_.any() else 0}
            if mo.sum() >= 10:
                v = sb[mo]
                rec["2-30 m"] = {"rms_cm": r4(100 * rms(v), 2), "p2p_cm": r4(100 * (v.max() - v.min()), 2),
                                 **dict(zip(("dominant_wavelength_m", "dominant_at_band_edge"),
                                            peak_wavelength(r30[m_], BAND_LO_M, BAND_HI_M))),
                                 "noise_rms_cm [model]": r4(100 * math.sqrt(np.mean([np.mean(x[m_] ** 2) for x in nsb])), 2)}
                g_ = np.where(m_, gc, np.nan)
                if np.isfinite(g_).any():
                    ig = int(np.nanargmax(np.abs(g_)))
                    rec["grade_change_5m"] = {"max_abs_pct": r4(100 * abs(gc[ig]), 2), "signed_pct": r4(100 * gc[ig], 2),
                                              "at_s": round(float(s[ig]), 1), "noise_pct_there": r4(100 * sgc[ig], 2),
                                              "noise_pct_p50": r4(100 * float(np.nanmedian(np.where(m_, sgc, np.nan))), 2)}
                c0 = int(np.flatnonzero(m_)[len(np.flatnonzero(m_)) // 2])
                span = int(240 / STEP_M); idx = (np.arange(span) - span // 2 + c0) % n
                seg = vf[idx]; tt = np.arange(span); seg = seg - np.polyval(np.polyfit(tt, seg, 1), tt)
                lam_, edge_ = peak_wavelength(seg, 30.0, 120.0)
                rec["30-120 m dominant (240 m span)"] = {"wavelength_m": lam_, "at_band_edge": edge_}
                for b in bands["merged"]:
                    bm_, bc_, bl_ = (bands[x][b][mo] for x in variants)
                    rr = {"merged_cm": r4(100 * rms(bm_), 2), "levelled_constant_cm": r4(100 * rms(bc_), 2),
                          "levelled_linear_gps_time_cm": r4(100 * rms(bl_), 2),
                          "removed_by_levelling_cm": r4(100 * rms(bm_ - bc_), 2),
                          "removed_by_levelling_linear_cm": r4(100 * rms(bm_ - bl_), 2),
                          "survives_levelling_pct": r4(100 * rms(bc_) / rms(bm_), 1) if rms(bm_) > 0 else None,
                          "survives_levelling_linear_pct": r4(100 * rms(bl_) / rms(bm_), 1) if rms(bm_) > 0 else None,
                          "noise_rms_cm [model]": r4(100 * math.sqrt(np.mean([np.mean(x[m_] ** 2) for x in nlong[b]])), 2)}
                    for sid in strips:
                        sv = sband[sid][b][m_]
                        cov = float(np.isfinite(sv).mean())
                        rr[f"strip_{sid}_cm"] = r4(100 * rms(sv), 2) if cov >= COVER_MIN else None
                        rr[f"strip_{sid}_cover"] = round(cov, 2)
                    rec[f"{b} m"] = rr
            rec["strip_returns"] = {str(sid): int(np.nansum(SC[k][sid][m_])) for sid in strips}
            if pairs:
                sa, sb2 = pairs[0]
                d = OFF[k][(sa, sb2)][m_]
                rec["overlap_stations"] = int(np.isfinite(d).sum())
                if np.isfinite(d).sum() >= 5:
                    rec["overlap_offset_cm"] = {"pair": f"{sb2}-{sa}", "mean": r4(100 * np.nanmean(d), 2),
                                                "sd": r4(100 * np.nanstd(d), 2),
                                                "noise_p50 (2 strips' mean-residual SE)": r4(100 * np.nanmedian(OFFE[k][(sa, sb2)][m_]), 2)}
            windows[j]["paths"][k] = rec

    # ------------------------------------------------ the overlap offset series, zone by zone
    zones = {}
    for k in keys:
        zl = []
        for (sa, sb2), d in OFF[k].items():
            e = OFFE[k][(sa, sb2)]
            for i0, i1 in runs_of(np.isfinite(d), OFFSET_RUN_GAP):
                L = i1 - i0 + 1
                if L < 40:                                           # [invented] under 20 m: not a zone
                    continue
                seg = d[i0:i1 + 1]; sok = np.isfinite(seg); segf = np.interp(np.arange(L), np.flatnonzero(sok), seg[sok])
                es = e[i0:i1 + 1]
                rec = {"pair": f"{sb2}-{sa}", "s": [round(float(s[i0]), 1), round(float(s[i1]), 1)],
                       "length_m": round(L * STEP_M, 1), "stations_with_both": int(sok.sum()),
                       "mean_cm": round(100 * float(np.mean(seg[sok])), 2), "sd_cm": round(100 * float(np.std(seg[sok])), 2),
                       "abs_p50_cm": round(100 * float(np.percentile(np.abs(seg[sok]), 50)), 2),
                       "abs_p90_cm": round(100 * float(np.percentile(np.abs(seg[sok]), 90)), 2),
                       "abs_max_cm": round(100 * float(np.max(np.abs(seg[sok]))), 2),
                       "noise_p50_cm": round(100 * float(np.nanmedian(es)), 2),
                       "trend_cm_per_100m": round(100 * 100 * float(np.polyfit(np.flatnonzero(sok) * STEP_M, seg[sok], 1)[0]), 2)}
                for lo, hi in LONG_BANDS:
                    bn = f"{int(lo)}-{int(hi)} m"
                    if L * STEP_M >= 2 * hi:
                        bb = band_run(segf, lo, hi)
                        # the noise of the offset in the same band [model]: white draws of each station's SE, the
                        # stations' own (correlated over the disc, as the profiles' noise)
                        ed = np.interp(np.arange(L), np.flatnonzero(np.isfinite(es)), es[np.isfinite(es)]) if np.isfinite(es).any() else np.zeros(L)
                        nd_ = [band_run(x, lo, hi) for x in noise_draws(ed, rng)]
                        nr = math.sqrt(np.mean([np.mean(x ** 2) for x in nd_]))
                        br = rms(bb[sok])
                        rec[bn] = {"offset_rms_cm": round(100 * br, 2), "noise_rms_cm [model]": round(100 * nr, 2),
                                   "per_strip_systematic_cm [inferred: sqrt((offset^2 - noise^2) / 2), two independent strips]":
                                       round(100 * math.sqrt(max(0.0, br ** 2 - nr ** 2) / 2), 2)}
                    else:
                        rec[bn] = f"zone shorter than 2 x {int(hi)} m: not measured"
                zl.append(rec)
        zones[k] = zl

    # ------------------------------------------------ ranking (the mean of the three paths)
    def wmean(j, path_key):
        vals = [windows[j]["paths"][k].get(path_key[0], {}).get(path_key[1]) for k in keys]
        vals = [v for v in vals if v is not None]
        return float(np.mean(vals)) if vals else None
    for j in range(nw):
        for k in keys:
            r_ = windows[j]["paths"][k].get("2-30 m")
            if r_ and r_.get("rms_cm") is not None and r_.get("noise_rms_cm [model]") is not None:
                r_["above_noise_rms_cm [model]"] = round(math.sqrt(max(0.0, r_["rms_cm"] ** 2 - r_["noise_rms_cm [model]"] ** 2)), 2)
    rank = {}
    for label, pk in (("2-30 m rms_cm", ("2-30 m", "rms_cm")),
                      ("2-30 m above_noise_rms_cm [model]", ("2-30 m", "above_noise_rms_cm [model]")),
                      ("30-60 m merged_cm", ("30-60 m", "merged_cm")),
                      ("60-120 m merged_cm", ("60-120 m", "merged_cm"))):
        rows = [(wmean(j, pk), j) for j in range(nw) if windows[j]["s1"] - windows[j]["s0"] >= 50]
        rows = sorted([r_ for r_ in rows if r_[0] is not None], reverse=True)
        fmt_ = lambda r_: {"s": [windows[r_[1]]["s0"], windows[r_[1]]["s1"]], "mean_of_paths_cm": round(r_[0], 2)}  # noqa: E731
        rank[label] = {"worst5": [fmt_(r_) for r_ in rows[:5]], "quietest3": [fmt_(r_) for r_ in rows[-3:][::-1]]}

    # ------------------------------------------------ the strips' own profiles (sparse: runs)
    sprof = {}
    for sid in strips:
        rec = {"returns_near_lap": int(w_strip[sid]), "gps_time": [round(float(T[S == sid].min()), 2), round(float(T[S == sid].max()), 2)],
               "paths": {}}
        for k in keys:
            h = H[k] + SR[k][sid]; ok = np.isfinite(h)
            own = SH[k][sid]; both_ = ok & np.isfinite(own)
            rr = [[int(i0), int(i1)] for i0, i1 in runs_of(ok, 0)]
            rec["paths"][k] = {"covered_stations": int(ok.sum()),
                               "covered_s_ranges (gaps <= 2 m bridged)": [[round(float(s[i0]), 1), round(float(s[i1]), 1)] for i0, i1 in runs_of(ok, STRIP_RUN_GAP) if i1 - i0 >= 20],
                               "own_plane_minus_level_m": ({"stations": int(both_.sum()),
                                                            "p50_abs": round(float(np.median(np.abs(own - h)[both_])), 4),
                                                            "p90_abs": round(float(np.percentile(np.abs(own - h)[both_], 90)), 4),
                                                            "max_abs": round(float(np.max(np.abs(own - h)[both_])), 4)}
                                                           if both_.any() else None),
                               "runs": [{"i0": i0, "z_m": arr(h[i0:i1 + 1]), "se_m": arr(SRE[k][sid][i0:i1 + 1]),
                                         "own_plane_z_m": arr(own[i0:i1 + 1])} for i0, i1 in rr]}
        sprof[str(sid)] = rec

    allo = np.concatenate([d for k in keys for d in OFF[k].values()]) if pairs else np.zeros(0)
    allo = allo[np.isfinite(allo)]

    # ------------------------------------------------ the verdict (numbers; the words say only what they show)
    verdict = {}
    for lo, hi in LONG_BANDS:
        b = f"{int(lo)}-{int(hi)}"
        rows = {}
        for k in keys:
            lw = lapwide[k]
            sv = [windows[j]["paths"][k].get(f"{b} m", {}).get("survives_levelling_linear_pct") for j in range(nw)]
            sv = [v for v in sv if v is not None]
            sysd = [z_[f"{b} m"] for z_ in zones[k] if isinstance(z_.get(f"{b} m"), dict)]
            rows[k] = {"merged_cm": lw[f"{b}_m_rms_cm_merged"],
                       "levelled_linear_cm": lw[f"{b}_m_rms_cm_levelled_linear_gps_time"],
                       "removed_cm (constant / linear)": [lw[f"{b}_m_removed_by_levelling_cm_levelled_constant"],
                                                           lw[f"{b}_m_removed_by_levelling_cm_levelled_linear_gps_time"]],
                       "survives_pct_per_window_min_max": [min(sv), max(sv)] if sv else None,
                       "overlap_offset_rms_cm (per zone)": [z_["offset_rms_cm"] for z_ in sysd],
                       "overlap_offset_noise_cm [model] (per zone)": [z_["noise_rms_cm [model]"] for z_ in sysd],
                       "per_strip_systematic_cm [inferred] (per zone)":
                           [z_["per_strip_systematic_cm [inferred: sqrt((offset^2 - noise^2) / 2), two independent strips]"] for z_ in sysd]}
        verdict[f"{b} m"] = rows
    verdict["_doc"] = ("survives = the levelled profile's band RMS over the merged's, per 100 m window (100 % = the strip "
                       "offsets carry none of it); removed = the RMS of (merged - levelled) in the band. The strips' own "
                       "along-track errors that do NOT differ between the two strips cannot be seen here; those that do "
                       "show in the overlap offset's band, against its noise [model]. Away from the overlaps one strip "
                       "covers the road alone, and levelling cannot change its band at all (a constant per strip)")
    doc = {
        "_doc": "Milford's real road surface along the lap from the 2017 lidar (road_profile_lidar.py profile). Every height "
                "is a robust plane's constant term through the class-2 returns within the disc (wavy_survey's read). "
                "z_m in the built frame: lidar z + datum_m - origin.elev_m (the G10 surface read's y_m datum, the deck's "
                "+0.10 inside). Measured unless marked [invented] / [model] / [inferred].",
        "inputs": {"line": {"file": "data/centerline.local.json", "md5": md5(a.line), "points": int(len(P) - 1),
                            "what": "the build's swept line (the assembler's line; the ribbon is +-w/2 about it). The driven "
                                    "lane is this centre line: ai/full/ai_draft.json is a generated centreline draft "
                                    "(offset_max 0.016 m), not a racing line"},
                   "points": {"file": Path(a.points).name, "md5": md5(a.points), "returns": int(len(E))},
                   "read": json.loads(Path(str(a.points) + ".report.json").read_text()) if Path(str(a.points) + ".report.json").exists() else None,
                   "lidar": "USGS 3DEP USGS_LPC_MI_31Co_Oakland_2016_LAS_2019 (flown 2017), EPT nodes at full depth: the "
                            "ring read (2026-11-22) then the lap corridor read (mf_lidar), union by node key"},
        "frame": {"xz": "ENU local metres (x east, z north) about origin; the lidar moved by shift_m (dE, dN) into it",
                  "origin": origin, "s": "metres along the line from its first point, n = round(lap / 0.5) equal steps",
                  "offset_sign": "+ = left of travel: point = (x, z) + offset * (nx, nz)"},
        "registration": {"shift_m": list(SHIFT_M), "datum_m": DATUM_M,
                         "source": "track.config.json terrain.lidar_shift_m (ledger 0102) = the measured surface's "
                                   "registration_lidar_shift_m (source/surface/road_surface_gm.fit.json), measured by the "
                                   "G10 on 0.1.11's built OBJ (2026-11-13) and carried by the GM read; datum_m = that "
                                   "read's built - lidar on the centre path"},
        "constants": {"STEP_M": STEP_M, "WHEEL_M [invented, as asked]": WHEEL_M, "LIDAR_R_M": LIDAR_R_M,
                      "LIDAR_MIN_N": LIDAR_MIN_N, "TRIM_SIGMA": TRIM_SIGMA, "STRIP_MIN_N": STRIP_MIN_N,
                      "KEEP_CLASSES": list(KEEP_CLASSES), "WIN_M": WIN_M, "MA_M [invented, as asked]": MA_M,
                      "band_m": [BAND_LO_M, BAND_HI_M], "GRADE_BASE_M [invented, as asked]": GRADE_BASE_M,
                      "LONG_BANDS_M": [list(b) for b in LONG_BANDS], "NOISE_DRAWS": NOISE_DRAWS,
                      "STRIP_RUN_GAP [invented]": STRIP_RUN_GAP, "OFFSET_RUN_GAP [invented]": OFFSET_RUN_GAP,
                      "COVER_MIN [invented]": COVER_MIN, "RIDGE [invented]": RIDGE,
                      "OWN_PLANE_SE_M [invented]": OWN_PLANE_SE_M, "EDGE_FRAC [invented]": EDGE_FRAC,
                      "disc_note": "the 1.25 m disc averages the surface over ~2.5 m: the 2-30 m band's short end is "
                                   "attenuated (a 2.5 m wave reads about half its height) [model]"},
        "lap_m": round(lap, 2), "stations": n, "step_m": STEP_M,
        "noise": {"cal_split_half_over_se": round(cal, 3), "cal_stations": int(both.sum()),
                  "noise_m": "cal x fit_sd / sqrt(kept returns) (the G10 read's model; its GM read measured cal 1.435)",
                  "split_half_m": "|A - B| / 2, A and B planes through alternate returns (each >= 6), where measurable"},
        "s": arr(s, 2), "x": arr(st["X"], 3), "z": arr(st["Z"], 3), "nx": arr(st["nx"], 5), "nz": arr(st["nz"], 5),
        "half_width_m": arr(st["HW"], 3),
        "paths": {k: {"z_m": arr(H[k]), "n_returns_in_disc": [int(v) for v in ND[k]], "n_returns_kept": [int(v) for v in NR[k]],
                      "gap": [bool(not np.isfinite(v)) for v in H[k]], "noise_m": arr(SIG[k]),
                      "strip_returns": {str(sid): [int(v) if np.isfinite(v) else 0 for v in SC[k][sid]] for sid in strips},
                      "strip_offset_m": {f"{sb2}-{sa}": arr(OFF[k][(sa, sb2)]) for sa, sb2 in pairs},
                      "z_levelled_constant_m": arr(HC[k]), "z_levelled_linear_gps_time_m": arr(HL[k])} for k in keys},
        "strips": {"by": "point_source_id (each a single pass: its GPS times span ~13 s)", "ids": strips,
                   "own_profiles_doc": "per strip and path, where the disc holds >= STRIP_MIN_N of its kept returns: "
                                       "z_m = the merged plane + the strip's mean residual about it (its level, on the "
                                       "merged plane's tilt; where it covers alone, the merged profile itself); se_m its "
                                       "standard error; own_plane_z_m = the strip's independent plane (>= 6 of its "
                                       "returns) where its constant's SE from the returns' geometry is <= "
                                       "OWN_PLANE_SE_M [invented] (at the swath's edge 6-8 returns can lie along one "
                                       "scan line, and the independent plane runs away: up to 0.42 m seen before this "
                                       "gate)",
                   "levelling": lev, "overlap_zones": zones,
                   "overlap_offset_all_paths_cm": ({"stations": int(len(allo)), "mean": round(100 * float(allo.mean()), 2),
                                                    "abs_p50": round(100 * float(np.percentile(np.abs(allo), 50)), 2),
                                                    "abs_p90": round(100 * float(np.percentile(np.abs(allo), 90)), 2),
                                                    "abs_max": round(100 * float(np.abs(allo).max()), 2)} if len(allo) else None),
                   "own_profiles": sprof},
        "lap_wide": lapwide,
        "verdict_strips": verdict,
        "windows": windows,
        "ranking": rank,
        "wall_s": round(time.time() - t0, 1),
    }
    Path(a.out).write_text(json.dumps(doc, separators=(",", ":")))
    print(json.dumps({"out": a.out, "stations": n, "lap_m": round(lap, 1), "cal": round(cal, 3), "levelling": lev,
                      "lap_wide": lapwide, "verdict": verdict, "offset_all": doc["strips"]["overlap_offset_all_paths_cm"],
                      "zones": zones, "ranking": rank, "wall_s": doc["wall_s"]}, indent=1))



# ---------------------------------------------------------------- built: the build's own road profile, from files
class SectionDelta:
    """tools/densify_ribbon_blend.py's Section (route.densify.section), outside Blender: the row's nearest section
    station by position (a 6 m grid, +-1 cell), full weight on the spans of the product's s, a smoothstep to nothing
    over taper_m outside them, delta linear in the lateral offset (reach 3 m past the outermost offsets)"""

    def __init__(self, d, spans, taper, reach=3.0):
        self.d, self.spans, self.taper, self.reach = d, spans, taper, reach
        self.offs = [float(o) for o in d["offsets_m"]]
        self.grid = {}
        for i in range(len(d["s"])):
            self.grid.setdefault((int(d["x"][i] // 6), int(d["z"][i] // 6)), []).append(i)

    def nearest(self, x, y):
        bx, by = int(x // 6), int(y // 6)
        best, bi = None, None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for i in self.grid.get((bx + dx, by + dy), ()):
                    dd = (self.d["x"][i] - x) ** 2 + (self.d["z"][i] - y) ** 2
                    if best is None or dd < best:
                        best, bi = dd, i
        return bi

    def weight(self, s):
        w = 0.0
        for a, b in self.spans:
            if a <= s <= b:
                return 1.0
            g = (a - s) if s < a else (s - b)
            if g < self.taper:
                t = 1.0 - g / self.taper
                w = max(w, t * t * (3 - 2 * t))
        return w

    def delta(self, i, u):
        pts = [(o, v) for o, v in zip(self.offs, self.d["delta"][i]) if v is not None]
        if len(pts) < 2:
            return 0.0
        if u <= pts[0][0]:
            return pts[0][1] if pts[0][0] - u <= self.reach else 0.0
        if u >= pts[-1][0]:
            return pts[-1][1] if u - pts[-1][0] <= self.reach else 0.0
        for (o0, v0), (o1, v1) in zip(pts, pts[1:]):
            if o0 <= u <= o1:
                return v0 + (v1 - v0) * (u - o0) / (o1 - o0)
        return 0.0

    def at(self, x, z, u):
        i = self.nearest(x, z)
        if i is None:
            return 0.0
        w = self.weight(self.d["s"][i])
        return w * self.delta(i, u) if w > 0 else 0.0


def window_metrics(v, s, lap):
    """the 2-30 m and long-band metrics of one profile (NaN = gap), per window; and its band signals"""
    wi, nw = win_index(s, lap)
    ok = np.isfinite(v); vf, _ = fill(v)
    r30 = vf - moving_average(vf, MA_M); sb = short_band(vf); gc = grade_change(v)
    lb = {f"{int(lo)}-{int(hi)}": band_fft(vf, lo, hi) for lo, hi in LONG_BANDS}
    out = []
    for j in range(nw):
        m_ = wi == j; mo = m_ & ok
        rec = {}
        if mo.sum() >= 10:
            g_ = np.where(m_, gc, np.nan)
            ig = int(np.nanargmax(np.abs(g_))) if np.isfinite(g_).any() else None
            rec = {"2-30 m rms_cm": 100 * rms(sb[mo]), "2-30 m p2p_cm": 100 * float(sb[mo].max() - sb[mo].min()),
                   "2-30 m dominant_wavelength_m": peak_wavelength(r30[m_], BAND_LO_M, BAND_HI_M)[0],
                   "grade_change_5m max_abs_pct": (100 * abs(gc[ig])) if ig is not None else np.nan,
                   **{f"{b} m rms_cm": 100 * rms(lb[b][mo]) for b in lb}}
        out.append(rec)
    return out, {"2-30": sb, **lb}, ok


def cmd_built(a):
    import importlib.util
    doc = json.loads(Path(a.profile).read_text())
    spec = importlib.util.spec_from_file_location("measured_surface", a.measured_surface)
    ms = importlib.util.module_from_spec(spec); spec.loader.exec_module(ms)
    fit = json.loads(Path(a.fit).read_text())
    Pr = ms.Product(fit)
    sec_d = json.loads(Path(a.section).read_text())
    spans = [tuple(float(v) for v in a.section_spans.split(","))]
    sec = SectionDelta(sec_d, spans, a.section_taper)
    cf = json.loads(Path(a.crossfall).read_text())
    Pl, Wl, origin = load_line(a.line)
    sl = np.r_[0, np.cumsum(np.hypot(np.diff(Pl[:, 0]), np.diff(Pl[:, 2])))]
    cxz = np.asarray(cf["points_xz"], float)
    if np.abs(cxz - Pl[:len(cxz), [0, 2]]).max() > 0.01:
        raise SystemExit("[built] the crossfall file's points are not the line's")
    bank = np.r_[np.asarray(cf["bank_rad"], float), cf["bank_rad"][0]]
    if len(bank) != len(sl):
        bank = np.interp(np.arange(len(sl)), np.arange(len(bank)), bank)
    s = np.asarray(doc["s"], float); lap = float(doc["lap_m"]); n = len(s)
    X, Zz, NX, NZ = (np.asarray(doc[q], float) for q in ("x", "z", "nx", "nz"))
    Yline = np.interp(s, sl, Pl[:, 1]); Bline = np.interp(s, sl, bank)
    keys = list(doc["paths"].keys())
    built = {"_doc": "the build's own road profile on the same paths, from committed files only (no mesh): fit = the "
                     "measured-surface product's plane c + u b (tools/measured_surface.py Product.at by position; the "
                     "deck's +0.10 inside c, the lidar profiles' datum) + the banked turn's section delta "
                     "(route.densify.section: spans of the product's s, smoothstep taper); line = the line file's own "
                     "Y + deck + u tan(bank) (crossfall file) + the same delta: the intake wrote Y = the fit at the "
                     "assembler's smoothed points - the deck, so the two should agree (lap_wide.fit_minus_line_m; "
                     "z_m is the fit's). built minus real per window: "
                     "each metric's difference, and the RMS of (built - real) in the band",
             "files": {"fit": {"file": "source/surface/road_surface_gm.fit.json", "md5": md5(a.fit)},
                       "section": {"file": "source/surface/road_section_gm.json", "md5": md5(a.section),
                                   "spans": [list(x) for x in spans], "taper_m": a.section_taper},
                       "crossfall": {"file": "data/crossfall.lm.json", "md5": md5(a.crossfall)},
                       "line": {"file": "data/centerline.local.json", "md5": md5(a.line)},
                       "measured_surface_py_md5": md5(a.measured_surface)},
             "deck_m": DECK_M, "paths": {}, "windows": [], "lap_wide": {}}
    real_w = {}
    for k in keys:
        u = float(k)
        px, pz = X + u * NX, Zz + u * NZ
        hf = np.full(n, np.nan); dsec = np.zeros(n); uoff = np.full(n, np.nan)
        for i in range(n):
            r_ = Pr.at(px[i], pz[i])
            if r_ is not None:
                hf[i] = r_[0]; uoff[i] = r_[2]
            dsec[i] = sec.at(X[i], Zz[i], u)
        hfit = hf + dsec
        hline = Yline + DECK_M + u * np.tan(Bline) + dsec
        real = np.array([np.nan if v is None else v for v in doc["paths"][k]["z_m"]], float)
        lev = np.array([np.nan if v is None else v for v in doc["paths"][k]["z_levelled_constant_m"]], float)
        wb, bb, _ = window_metrics(hfit, s, lap)
        wl, _, _ = window_metrics(hline, s, lap)
        wr, br, okr = window_metrics(real, s, lap)
        wv, bv, _ = window_metrics(lev, s, lap)
        real_w[k] = (wr, wv)
        built["paths"][k] = {"z_m": arr(hfit), "section_delta_m": arr(dsec)}
        lw = {"station_off_fit_line_m": {"p50_abs": round(float(np.nanmedian(np.abs(uoff - u))), 3),
                                         "max_abs": round(float(np.nanmax(np.abs(uoff - u))), 3)},
              "fit_minus_line_m": {"p50_abs": round(float(np.nanmedian(np.abs(hfit - hline))), 4),
                                   "max_abs": round(float(np.nanmax(np.abs(hfit - hline))), 4)},
              "built_minus_real_m": {"median": round(float(np.nanmedian(hfit - real)), 4),
                                     "p90_abs": round(float(np.nanpercentile(np.abs(hfit - real), 90)), 4)}}
        for b in bb:
            Bv, Lv, Vv = bb[b][okr], br[b][okr], bv[b][okr]
            lw[f"{b} m"] = {"built_cm": round(100 * rms(Bv), 2), "real_cm": round(100 * rms(Lv), 2),
                            "real_levelled_cm": round(100 * rms(Vv), 2),
                            "built_minus_real_rms_cm": round(100 * rms(Bv - Lv), 2),
                            "gain_built_on_real": round(float(np.dot(Bv, Lv) / np.dot(Lv, Lv)), 2),
                            "gain_built_on_levelled": round(float(np.dot(Bv, Vv) / np.dot(Vv, Vv)), 2)}
        built["lap_wide"][k] = lw
        for j in range(len(wb)):
            if len(built["windows"]) <= j:
                built["windows"].append({"s0": round(j * WIN_M, 1), "s1": round(min(lap, (j + 1) * WIN_M), 1), "paths": {}})
            if not wb[j] or not wr[j]:
                built["windows"][j]["paths"][k] = None
                continue
            m_ = (np.minimum((s // WIN_M).astype(int), len(wb) - 1) == j) & okr
            rec = {"built": {q: r4(v, 2) for q, v in wb[j].items() if v is not None},
                   "built_minus_real": {q: r4(wb[j][q] - wr[j][q], 2) for q in wb[j]
                                        if wb[j][q] is not None and wr[j].get(q) is not None},
                   "built_minus_levelled": {q: r4(wb[j][q] - wv[j][q], 2) for q in ("30-60 m rms_cm", "60-120 m rms_cm")
                                            if wv[j]},
                   "rms_of_built_minus_real_cm": {f"{b} m": r4(100 * rms(bb[b][m_] - br[b][m_]), 2) for b in bb},
                   "mean_built_minus_real_cm": r4(100 * float(np.mean(hfit[m_] - real[m_])), 2),
                   "line_check_30-60 m rms_cm": r4(wl[j].get("30-60 m rms_cm"), 2) if wl[j] else None}
            built["windows"][j]["paths"][k] = rec
    doc["built"] = built
    if a.control:
        doc["control"] = {"_doc": "road_profile_lidar.py control: this script's plane at the G10 GM surface read's own "
                                  "centre-path points (that read is board asset 7da6810244a541615b95aced5f6e5290, the "
                                  "one tools/measured_surface.py fit made road_surface_gm.fit.json from), within 1.5 m "
                                  "of this line", **json.loads(Path(a.control).read_text())}
    Path(a.out).write_text(json.dumps(doc, separators=(",", ":")))
    print(json.dumps(built["lap_wide"], indent=1))


# ---------------------------------------------------------------- control: the G10 GM read's centre path, re-read
def cmd_control(a):
    """this script's plane against the G10 surface read the build's measured surface came from, at that read's own
    centre-path points that lie within 1.5 m of this line (so every return of their disc is in the points file)"""
    from scipy.spatial import cKDTree
    g = json.loads(Path(a.g10_read).read_text())
    P, W, origin = load_line(a.line)
    st = stations(P, W)
    D = np.load(a.points)
    E, N, Z, S, T = D["e"], D["n"], D["z"], D["psid"].astype(int), D["t"]
    tree = cKDTree(np.c_[E, N]); lt = cKDTree(np.c_[st["X"], st["Z"]])
    X, Zz = np.asarray(g["x"], float), np.asarray(g["z"], float)
    y = np.array([np.nan if v is None else v for v in g["paths"]["+0.0"]["y_m"]], float)
    dl, _ = lt.query(np.c_[X, Zz])
    sel = np.flatnonzero((dl <= KEEP_R_M - LIDAR_R_M - 0.25) & np.isfinite(y))
    lists = tree.query_ball_point(np.c_[X[sel], Zz[sel]], LIDAR_R_M)
    mine = np.array([disc_fit(E, N, Z, S, T, lists[j], X[i], Zz[i])["h"] for j, i in enumerate(sel)])
    d = mine - y[sel]; ok = np.isfinite(d)
    rep = {"g10_read_md5": md5(a.g10_read), "points_compared": int(ok.sum()), "of_g10_planes": int(np.isfinite(y).sum()),
           "line_to_g10_line_m": {"p50": round(float(np.median(dl)), 3), "p90": round(float(np.percentile(dl, 90)), 3),
                                  "max": round(float(dl.max()), 3)},
           "mine_minus_g10_m": {"p50_abs": round(float(np.median(np.abs(d[ok]))), 5),
                                "p99_abs": round(float(np.percentile(np.abs(d[ok]), 99)), 5),
                                "max_abs": round(float(np.abs(d[ok]).max()), 5),
                                "exact_to_0.1mm_share": round(float(np.mean(np.abs(d[ok]) < 1e-4)), 4)}}
    print(json.dumps(rep, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("read"); r.add_argument("--line", required=True); r.add_argument("--lidar", action="append", required=True)
    r.add_argument("--out", required=True); r.add_argument("--chunk", type=int, default=400_000)
    p = sub.add_parser("profile"); p.add_argument("--line", required=True); p.add_argument("--points", required=True)
    p.add_argument("--out", required=True)
    c = sub.add_parser("control"); c.add_argument("--line", required=True); c.add_argument("--points", required=True)
    c.add_argument("--g10-read", required=True); c.add_argument("--out")
    b = sub.add_parser("built"); b.add_argument("--profile", required=True); b.add_argument("--fit", required=True)
    b.add_argument("--section", required=True); b.add_argument("--crossfall", required=True)
    b.add_argument("--line", required=True); b.add_argument("--measured-surface", required=True)
    b.add_argument("--section-spans", default="870,1030"); b.add_argument("--section-taper", type=float, default=15.0)
    b.add_argument("--control", help="the control subcommand's JSON, embedded")
    b.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    {"read": cmd_read, "profile": cmd_profile, "control": cmd_control, "built": lambda a_: cmd_built(a_)}[a.cmd](a)


if __name__ == "__main__":
    main()
