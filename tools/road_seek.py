"""THE ROAD WHERE THE GROUND AND THE AERIAL SAY IT IS: a mapped line's lateral offset and height from 3DEP 1 m and
NAIP cross-sections (ledger 0078 round 8).

A mapped line (OSM) can sit off the graded road it names, by a few metres or, where the county realigned the road and
the map kept the old track, by 30-40 m (Dragon Tail at s ~20,700-21,000: the NAIP shows the graded road below the
mapped line across the hillside). There 3DEP read ALONG the mapped line reads the hillside, not the road: on Dragon
Tail's descents 30-73 % "grades" over 10 m. airoso's elevation stage hid them under an 18 % grade cap; Kevin's rule
("I just want real": no caps, fix the artefact with better data) asks for the road itself.

The better data: 3DEP's 1 m bare-earth DEM and NAIP's aerial, both fetched as rasters over the line's corridor (the
3DEPElevation and USGSNAIPImagery ImageServers' exportImage, cached as .npz tiles), read ACROSS the line at every
station, SEEK_HALF_M either side. A graded county road is smooth and nearly level across its own width in the DEM, and
it does not climb a cliff: every candidate centre is scored on the DEM's departure from a straight cross-section over
the road's width and its cross-slope beyond CROSS_SLOPE_OK, plus a small cost for leaving the mapped line; a Viterbi
pass along the line picks the centres, a lateral shift between stations costing SHIFT_COST per metre and a grade
between the chosen heights beyond GRADE_FREE costing GRADE_W per (grade over it) squared (an old track's bench and the
realigned road are both flat across; only the realigned road is drivable along). The aerial is fetched with the DEM
but not scored (Dragon Tail's graded road is darker than the white soil beside it in one stretch and lighter than the
scrub in the next): it is the check, tools drawing the result on it. The centres are smoothed along the line (a Gaussian of SMOOTH_STATIONS) and the road's
height at each is the DEM's straight fit there. Nothing is capped: a road that really climbs 17 % reads 17 %.

    python tools/road_seek.py <port-track-dir> --cache <dir> [--workers 3]

Reads the port's lm_intake.source_track line (data/centerline.local.json), writes the port's data/road_seek.json: per
LOCAL station {offset_m (+ = left of travel), z_m (absolute), rms_m, cross_slope, contrast}, the parameters, a summary.
tools/lm_engine_intake.py applies it (lm_intake.road_seek) before the profile's own despike and mean.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))

DEM_SERVICE = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage"
NAIP_SERVICE = "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer/exportImage"
TILE_M = 400.0           # raster tiles along the corridor, this square
PX_M = 1.0               # 3DEP's own 1 m; NAIP read at the same grid
SEEK_HALF_M = 40.0       # [invented] the road's centre sought within this of the mapped line
SEEK_STEP_M = 0.5
SHOULDER_M = 4.0         # [invented] the aerial band's shoulders: this wide either side of the road
ROUGH_M = 0.05           # [invented] a graded road's departure from a straight DEM cross-section (RMS)
CROSS_SLOPE_OK = 0.04    # [invented] cross-slope a graded road carries without cost (crown / superelevation)
CROSS_SLOPE_UNIT = 0.02  # [invented] each further 2 % of cross-slope costs as much as ROUGH_M of roughness
OFF_COST = 0.05          # [invented] per metre of the centre off the mapped line
GRADE_FREE = 0.20        # [invented] a station-to-station grade up to this costs nothing (the stages' real pitches
                         # reach ~17 %); beyond it the road the DEM reads there is not the road
GRADE_SPAN_M = 10.0      # the grade the mapped line's DEM profile is read over (the intake's own steepest-10 m)
FLAG_MEDIAN_M = 33.0     # heightfield.MEDIAN_WINDOW_M: the line's DEM profile made as the intake makes the profile
REGION_PAD_M = 300.0     # [invented] a seek region runs this far past the stations whose line profile is not a road
GRADE_W = 400.0          # [invented] the cost of each further grade, squared (0.05 more = 1, a 10 m cliff in 3 m = ~4,000)
SHIFT_COST = 1.0         # [invented] per metre the centre moves between neighbouring stations
MAX_SHIFT_M = 1.5        # [invented] the most the centre moves between neighbouring (3 m) stations
BENCH_CORE_M = 2.0       # [invented] the road's own plane is fitted this far either side of its centre
BENCH_TOL_M = 0.25       # [invented] the graded bench: the DEM within this of that plane
FACE_RUN_M = 2.0         # [invented] a bench's end is an edge when the DEM this far past it ...
FACE_DROP_M = 0.5        # [invented] ... stands this far off the road's plane (a face steeper than ~1:4)
BENCH_MAX_M = 15.0       # [invented] a bench running on past this either way is level ground, not a measured edge
SMOOTH_STATIONS = 4.0    # [invented] Gaussian sigma (stations) of the chosen offsets


def _mpd(lat0):
    from scripts.geometry.projection import _meters_per_degree
    return _meters_per_degree(float(lat0))


def _get(url, tries=8):
    from scripts.tls import https_context
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=180, context=https_context()) as r:
                return r.read()
        except Exception:                                   # noqa: BLE001  (502 / 504 under load: back off)
            time.sleep(4 * (k + 1))
    raise SystemExit(f"[road_seek] refused {tries} times: {url[:120]}")


def tiles_for(P, margin):
    keys = set()
    for p in P:
        for dx in (-margin, 0.0, margin):
            for dz in (-margin, 0.0, margin):
                keys.add((math.floor((p[0] + dx) / TILE_M), math.floor((p[2] + dz) / TILE_M)))
    return sorted(keys)


def fetch_tile(key, origin, cache: Path):
    """(dem[ny][nx] float32, naip luminance) for one tile, local frame, row 0 = north; cached .npz"""
    import numpy as np
    from PIL import Image
    f = cache / f"t_{key[0]}_{key[1]}.npz"
    if f.exists():
        d = np.load(f)
        return d["dem"], d["img"]
    m_lon, m_lat = _mpd(origin["lat"])
    x0, z0 = key[0] * TILE_M, key[1] * TILE_M
    W, E = origin["lon"] + x0 / m_lon, origin["lon"] + (x0 + TILE_M) / m_lon
    S, N = origin["lat"] + z0 / m_lat, origin["lat"] + (z0 + TILE_M) / m_lat
    # square-DEGREE pixels (the ImageServer widens a box whose pixels are not, ledger 0062): ny = 400 m of latitude
    # at PX_M, nx in the same degree step (a degree of longitude is shorter here, so nx > ny pixels of < PX_M)
    ny = int(TILE_M / PX_M)
    nx = int(round(ny * (E - W) / (N - S)))
    base = {"bbox": f"{W},{S},{E},{N}", "bboxSR": 4326, "imageSR": 4326, "size": f"{nx},{ny}", "f": "image"}
    dem = Image.open(io.BytesIO(_get(DEM_SERVICE + "?" + urllib.parse.urlencode(
        {**base, "format": "tiff", "pixelType": "F32", "interpolation": "RSP_BilinearInterpolation"}))))
    img = Image.open(io.BytesIO(_get(NAIP_SERVICE + "?" + urllib.parse.urlencode(
        {**base, "format": "png", "interpolation": "RSP_BilinearInterpolation"})))).convert("L")
    dem = np.asarray(dem, dtype=np.float32)
    if dem.shape != (ny, nx):
        raise SystemExit(f"[road_seek] the DEM tile came back {dem.shape}, asked ({ny}, {nx})")
    img = np.asarray(img.resize((nx, ny)), dtype=np.float32)
    np.savez_compressed(f, dem=dem, img=img)
    return dem, img


class Raster:
    def __init__(self, tiles):
        self.t = tiles

    def at(self, x, z):
        """(dem, img) bilinear at local (x, z), or (None, None)"""
        kx, kz = math.floor(x / TILE_M), math.floor(z / TILE_M)
        t = self.t.get((kx, kz))
        if t is None:
            return None, None
        ny, nx = t[0].shape
        fx = (x - kx * TILE_M) / (TILE_M / nx) - 0.5
        fy = (ny - (z - kz * TILE_M) / (TILE_M / ny)) - 0.5
        i0, j0 = int(math.floor(fx)), int(math.floor(fy))
        i0, j0 = max(0, min(nx - 2, i0)), max(0, min(ny - 2, j0))
        ax, ay = min(1.0, max(0.0, fx - i0)), min(1.0, max(0.0, fy - j0))
        out = []
        for g in t:
            v = ((1 - ax) * (1 - ay) * g[j0, i0] + ax * (1 - ay) * g[j0, i0 + 1] + (1 - ax) * ay * g[j0 + 1, i0]
                 + ax * ay * g[j0 + 1, i0 + 1])
            out.append(float(v))
        if not (-500.0 < out[0] < 9000.0):
            return None, out[1]
        return out[0], out[1]


def _fit(ts, hs):
    n = len(ts)
    mt, mh = sum(ts) / n, sum(hs) / n
    stt = sum((t - mt) ** 2 for t in ts) or 1e-9
    b = sum((t - mt) * (h - mh) for t, h in zip(ts, hs)) / stt
    a = mh - b * mt
    rms = math.sqrt(sum((h - (a + b * t)) ** 2 for t, h in zip(ts, hs)) / n)
    return a, b, rms


def _std(v):
    if len(v) < 2:
        return 0.0
    m = sum(v) / len(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / len(v))


def seek(P, W, R):
    import numpy as np
    m = len(P)
    K = int(round(SEEK_HALF_M / SEEK_STEP_M))
    cands = np.array([k * SEEK_STEP_M for k in range(-K, K + 1)])
    reach = SEEK_HALF_M + max(W) / 2.0 + SHOULDER_M + 1.0
    nr = int(math.ceil(reach / PX_M))
    offs = np.arange(-nr, nr + 1) * PX_M
    k = len(cands)
    costs = np.full((m, k), 1e6)
    fits = np.zeros((m, k, 4))                     # height at c, rms, cross-slope, contrast
    normals = []
    for i in range(m):
        a, b = P[max(i - 1, 0)], P[min(i + 1, m - 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / L, tx / L
        normals.append((nx, nz))
        sec = [R.at(P[i][0] + nx * t, P[i][2] + nz * t) for t in offs]
        d = np.array([np.nan if v[0] is None else v[0] for v in sec])
        g = np.array([np.nan if v[1] is None else v[1] for v in sec])
        okd, okg = ~np.isnan(d), ~np.isnan(g)
        d0, g0 = np.where(okd, d, 0.0), np.where(okg, g, 0.0)
        t = offs

        def cs(v):
            return np.concatenate([[0.0], np.cumsum(v)])
        Cn, Ct, Ctt, Cd, Ctd = cs(okd * 1.0), cs(okd * t), cs(okd * t * t), cs(d0), cs(d0 * t)
        Cdd = cs(d0 * d0)
        Gn, Gs, Gss = cs(okg * 1.0), cs(g0), cs(g0 * g0)
        half = max(W[i] / 2.0 - 0.25, 1.5)
        lo = np.searchsorted(t, cands - half - 1e-9)
        hi = np.searchsorted(t, cands + half + 1e-9)
        n = Cn[hi] - Cn[lo]
        st, stt, sd, std_, sdd = Ct[hi] - Ct[lo], Ctt[hi] - Ctt[lo], Cd[hi] - Cd[lo], Ctd[hi] - Ctd[lo], Cdd[hi] - Cdd[lo]
        with np.errstate(divide="ignore", invalid="ignore"):
            den = n * stt - st * st
            bb = np.where(den > 1e-9, (n * std_ - st * sd) / den, 0.0)
            aa = np.where(n > 0, (sd - bb * st) / n, 0.0)
            sse = sdd - 2 * aa * sd - 2 * bb * std_ + aa * aa * n + 2 * aa * bb * st + bb * bb * stt
            rms = np.sqrt(np.maximum(sse, 0.0) / np.maximum(n, 1))
            gn, gs, gss = Gn[hi] - Gn[lo], Gs[hi] - Gs[lo], Gss[hi] - Gss[lo]
            l0 = np.searchsorted(t, cands - half - SHOULDER_M - 1e-9)
            h1 = np.searchsorted(t, cands + half + SHOULDER_M + 1e-9)
            sn = (Gn[lo] - Gn[l0]) + (Gn[h1] - Gn[hi])
            ss = (Gs[lo] - Gs[l0]) + (Gs[h1] - Gs[hi])
            sss = (Gss[lo] - Gss[l0]) + (Gss[h1] - Gss[hi])
            sm_ = ss / np.maximum(sn, 1)
            ssd = np.sqrt(np.maximum(sss / np.maximum(sn, 1) - sm_ * sm_, 0.0))
            ssd = np.where(ssd > 1e-6, ssd, 1.0)
            bm = gs / np.maximum(gn, 1)
            bsd = np.sqrt(np.maximum(gss / np.maximum(gn, 1) - bm * bm, 0.0))
            contrast = (bm - sm_) / ssd
            cost = (rms / ROUGH_M + np.maximum(0.0, np.abs(bb) - CROSS_SLOPE_OK) / CROSS_SLOPE_UNIT
                    + OFF_COST * np.abs(cands))
        bad = (n < 3) | (gn < 3) | (sn < 3)
        costs[i] = np.where(bad, 1e6, cost)
        fits[i, :, 0] = aa + bb * cands
        fits[i, :, 1] = rms
        fits[i, :, 2] = bb
        fits[i, :, 3] = contrast
    # WHERE TO SEEK: only where the mapped line's own DEM profile is not a road (a grade over GRADE_FREE over
    # GRADE_SPAN_M), REGION_PAD_M either side. On level ground every strip is flat and the road's own crown and ditches
    # make it the LEAST flat one, so a seek there wanders; where the mapped line reads a road, it stays the road.
    k0 = int(np.argmin(np.abs(cands)))
    st = [0.0]
    for i in range(1, m):
        st.append(st[-1] + math.hypot(P[i][0] - P[i - 1][0], P[i][2] - P[i - 1][2]))
    zl = fits[:, k0, 0]
    # the line's DEM profile as the intake makes a profile (heightfield.profile_along: the 33 m despike and the mean,
    # cap off), then graded: a mapped line whose own profile reads as a road is left where it is
    from scripts.elevation import heightfield as hf
    seg = [max(1e-3, st[i] - st[i - 1]) for i in range(1, m)]
    z0 = np.array(hf.profile_along([float(v) for v in zl], seg, grade_cap_pct=1e9, median_m=FLAG_MEDIAN_M,
                                   closed=False)[0])
    flag = np.zeros(m, dtype=bool)
    j = 0
    for i in range(m):
        while j < m - 1 and st[j] - st[i] < GRADE_SPAN_M:
            j += 1
        if st[j] - st[i] >= 0.5 * GRADE_SPAN_M and abs(z0[j] - z0[i]) / (st[j] - st[i]) > GRADE_FREE:
            flag[i:j + 1] = True
    regions = []
    i = 0
    while i < m:
        if not flag[i]:
            i += 1
            continue
        a_ = i
        while i < m and flag[i]:
            i += 1
        lo_, hi_ = a_, i - 1
        while lo_ > 0 and st[a_] - st[lo_] < REGION_PAD_M:
            lo_ -= 1
        while hi_ < m - 1 and st[hi_] - st[i - 1] < REGION_PAD_M:
            hi_ += 1
        if regions and st[lo_] - st[regions[-1][1]] <= REGION_PAD_M:
            regions[-1][1] = max(regions[-1][1], hi_)
        else:
            regions.append([lo_, hi_])
    js = int(round(MAX_SHIFT_M / SEEK_STEP_M))
    idx = np.arange(k)
    path = np.full(m, k0, dtype=np.int64)
    for lo_, hi_ in regions:
        acc = np.full(k, np.inf)
        acc[k0] = costs[lo_][k0]                     # a region starts and ends on the mapped line
        back = np.zeros((hi_ - lo_ + 1, k), dtype=np.int32)
        for i in range(lo_ + 1, hi_ + 1):
            best = np.full(k, np.inf)
            arg = idx.copy()
            ds = math.hypot(P[i][0] - P[i - 1][0], P[i][2] - P[i - 1][2]) or 1.0
            for sft in range(-js, js + 1):
                src = idx + sft
                ok = (src >= 0) & (src < k)
                v = np.full(k, np.inf)
                gr = np.abs(fits[i, idx[ok], 0] - fits[i - 1, src[ok], 0]) / ds
                v[ok] = (acc[src[ok]] + SHIFT_COST * abs(sft) * SEEK_STEP_M
                         + GRADE_W * np.maximum(0.0, gr - GRADE_FREE) ** 2)
                better = v < best
                best[better] = v[better]
                arg[better] = src[better]
            acc = best + costs[i]
            back[i - lo_] = arg
        jj = k0 if np.isfinite(acc[k0]) else int(np.argmin(acc))
        for i in range(hi_, lo_, -1):
            path[i] = jj
            jj = int(back[i - lo_][jj])
        path[lo_] = jj
    raw = cands[path]
    s = SMOOTH_STATIONS
    r = int(3 * s)
    ker = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2)
    num = np.convolve(raw, ker, mode="same")
    den = np.convolve(np.ones(m), ker, mode="same")
    sm = num / den
    out = []
    for i in range(m):
        c = float(sm[i])
        nx, nz = normals[i]
        half = max(W[i] / 2.0 - 0.25, 1.5)
        ts, hs = [], []
        tt = c - half
        while tt <= c + half + 1e-9:
            dd, _g = R.at(P[i][0] + nx * tt, P[i][2] + nz * tt)
            if dd is not None:
                ts.append(tt); hs.append(dd)
            tt += PX_M
        aa, bb, rms = _fit(ts, hs)
        # THE GRADED BENCH: from the road's own plane (fitted BENCH_CORE_M either side of the centre), how far each
        # way the DEM stays within BENCH_TOL_M of it. On a hillside it ends at the cut and the fill (the graded
        # surface's measured width: Dragon Tail's straights 7-8 m, its switchback platforms 11-12.5 m); on level
        # ground it runs on past BENCH_MAX_M and says nothing (bounded false).
        ct, ch = [], []
        tt = c - BENCH_CORE_M
        while tt <= c + BENCH_CORE_M + 1e-9:
            dd, _g = R.at(P[i][0] + nx * tt, P[i][2] + nz * tt)
            if dd is not None:
                ct.append(tt); ch.append(dd)
            tt += 0.5
        ba, bs, _r = _fit(ct, ch) if len(ct) >= 3 else (aa, bb, rms)
        ext = []
        for sgn in (-1.0, 1.0):
            e = 0.0
            while e < BENCH_MAX_M:
                q = c + sgn * (e + 0.5)
                dd, _g = R.at(P[i][0] + nx * q, P[i][2] + nz * q)
                if dd is None or abs(dd - (ba + bs * q)) >= BENCH_TOL_M:
                    break
                e += 0.5
            # an edge is MEASURED only where it is a face (the cut bank, the fill slope, a ditch): FACE_RUN_M past the
            # bench's end the DEM stands FACE_DROP_M off the road's plane. Level ground's gentle undulations end a bench
            # too, at any width: that end measures nothing
            q = c + sgn * (e + FACE_RUN_M)
            dd, _g = R.at(P[i][0] + nx * q, P[i][2] + nz * q)
            if e >= BENCH_MAX_M or dd is None or abs(dd - (ba + bs * q)) < FACE_DROP_M:
                e = BENCH_MAX_M
            ext.append(e)
        out.append({"offset_m": round(c, 3), "z_m": round(aa + bb * c, 3), "rms_m": round(rms, 3),
                    "cross_slope": round(bb, 4), "contrast": round(float(fits[i, path[i], 3]), 2),
                    "bench_m": [round(-ext[0], 2), round(ext[1], 2)],
                    "bench_bounded": ext[0] < BENCH_MAX_M and ext[1] < BENCH_MAX_M})
    return out, regions, st


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    ap.add_argument("--cache", required=True)
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args(argv)
    port = Path(a.port)
    cache = Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((port / "track.config.json").read_text(encoding="utf-8"))
    src = AIROSO / "tracks" / cfg["lm_intake"]["source_track"]
    local = json.loads((src / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    P = [tuple(p) for p in local["points_xyz_m"]]
    W = local.get("widths_m") or [6.5] * len(P)
    origin = local["origin"]
    keys = tiles_for(P, SEEK_HALF_M + max(W) / 2.0 + SHOULDER_M + 2.0)
    print(f"[road_seek] {len(keys)} tiles of {TILE_M:.0f} m (3DEP 1 m + NAIP) over the corridor", flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        tiles = dict(zip(keys, ex.map(lambda k: fetch_tile(k, origin, cache), keys)))
    res, regions, st = seek(P, W, Raster(tiles))
    elev0 = float(origin["elev_m"])
    moved = sorted(abs(r["offset_m"]) for r in res)
    rec = {
        "_doc": "tools/road_seek.py (ledger 0078 round 8): per station of the source's centerline.local.json (local order), "
                "the graded road's centre off the mapped line (offset_m, + = left of travel) and its height (z_m, absolute, "
                "3DEP 1 m's straight fit across the road there), found in 3DEP 1 m and NAIP cross-sections (USGS "
                "3DEPElevation / USGSNAIPImagery ImageServers, exportImage)",
        "source_track": cfg["lm_intake"]["source_track"],
        "params": {k: globals()[k] for k in ("TILE_M", "PX_M", "SEEK_HALF_M", "SEEK_STEP_M", "SHOULDER_M", "ROUGH_M",
                                             "CROSS_SLOPE_OK", "CROSS_SLOPE_UNIT", "OFF_COST", "GRADE_FREE", "GRADE_W", "GRADE_SPAN_M", "FLAG_MEDIAN_M", "REGION_PAD_M", "SHIFT_COST",
                                             "MAX_SHIFT_M", "SMOOTH_STATIONS", "BENCH_CORE_M", "BENCH_TOL_M", "FACE_RUN_M", "FACE_DROP_M", "BENCH_MAX_M")},
        "summary": {"stations": len(res),
                    "offset_abs_m": {"median": round(moved[len(moved) // 2], 2),
                                     "p95": round(moved[int(0.95 * (len(moved) - 1))], 2), "max": round(moved[-1], 2)},
                    "height_vs_source_profile_m": {"max": round(max(abs(r["z_m"] - (elev0 + p[1]))
                                                                    for r, p in zip(res, P)), 2)}},
        "regions_m": [[round(st[a_], 1), round(st[b_], 1)] for a_, b_ in regions],
        "stations": res,
    }
    (port / "data").mkdir(parents=True, exist_ok=True)
    (port / "data" / "road_seek.json").write_text(json.dumps(rec, separators=(",", ":")), encoding="utf-8")
    print(f"[road_seek] {len(res)} stations: centre off the mapped line median {rec['summary']['offset_abs_m']['median']} "
          f"m, p95 {rec['summary']['offset_abs_m']['p95']} m, max {rec['summary']['offset_abs_m']['max']} m in "
          f"{len(regions)} region(s) {rec['regions_m']}; "
          f"-> {port / 'data' / 'road_seek.json'}")


if __name__ == "__main__":
    main()
