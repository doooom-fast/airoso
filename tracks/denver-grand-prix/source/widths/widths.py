"""Denver Grand Prix: the lap's carriageway edges, medians, kerbs, bridge decks and the covered Stout portals.

    PY=/Volumes/Sundowning/Claude/airoso-data/venv/bin/python
    $PY tracks/denver-grand-prix/source/widths/widths.py [--data <airoso-data/denver-grand-prix>] [--step 2.5]

Writes, beside this file: widths.json (every station), stretches.json (per OSM way), bridges.json, stout_portals.json.
Data stays outside git (DATA.md); a corridor cache of the lidar is written to <data>/widths-cache/.

FRAME: ENU metres about the Colfax / Sherman crosswalk (-104.9849, 39.7401) by the aerial engine's metres-per-degree
series (scripts.aerial.engine.ortho.mpd) - the survey's frame (PR 66, lapgeo.py). Station s runs along OSM's lap line
(data/lap_line.plan.json) in driving order from the S/F crosswalk. Offsets are across that line: + is the driver's LEFT.

WHY NOT scripts/aerial/engine/edges.py AS IT IS: its surface edge is where the pavement score (near-neutral, smooth,
not dark) falls off for 2 m. Downtown the asphalt meets a concrete gutter pan, a kerb and a concrete sidewalk: all
three pass the same near-neutral test, so its score does not fall at the kerb and the reader runs on to the building
line. Its colour tuning has a lower luminance bound only (channels.DEFAULTS, no upper bound to configure). So the two
readings here use the engine's frame, geometry and sampling (geom.cumlen / normals / running_median, channels.sample)
with a section rule that fits a city street:

  LIDAR (first reading, CO_DRCOG_2_2020, flown 2020-05-27): class 2 ground returns within +-WIN_M along the station,
     binned BIN_M across. A KERB FACE is the first outward place where the ground steps UP by >= STEP_MIN_M (and
     <= STEP_MAX_M) between the BAND_M either side, and stays up (the next 1.5 m). Steps nearer the line than
     MIN_HALF_M are a median or island ON the line (recorded, searched past). Beyond the face, a step back DOWN to
     within 0.06 m of road level inside MEDIAN_MAX_M, with road-flat ground past it, is a raised median's far face.
     Parked cars do not matter: they are not class 2.
  AERIAL (second reading, DRCOG DRAPP 2022, 3 inch): luminance on 7 parallel sections over +-1.5 m, their median. The
     ASPHALT EDGE is the first outward place past MIN_HALF_M where it rises past halfway from the road's own luminance
     to the bright ground beyond and stays there for STAY_M (a lane dash or a crosswalk bar does not). No edge where
     the contrast is under CONTRAST_MIN (concrete streets, deep shadow). The asphalt edge is the gutter pan's road
     side, not the kerb face: the two readings differ by the pan's width, which is MEASURED per stretch (their median
     difference) and is reported, not assumed.

EDGE OF RECORD per station and side: the lidar face (grade measured); else the aerial edge plus the stretch's measured
pan (grade detected); else interpolated from neighbours (inferred, with the reason: mouth, no_return, no_contrast,
covered). A face more than MOUTH_X past the side's running median is another road's (a junction mouth): inferred.
Disagreement: |aerial + pan - lidar| > 0.3 m, per station, summarised per stretch.

Every threshold below is [invented] tuning of a reader and is written into the output.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
import time

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, *[os.pardir] * 4))
T = os.path.join(ROOT, 'tracks', 'denver-grand-prix')
sys.path.insert(0, ROOT)
from scripts.aerial.engine import geom  # noqa: E402
from scripts.aerial.engine.ortho import mpd  # noqa: E402

ORIGIN = (-104.9849, 39.7401)
MLON, MLAT = mpd(ORIGIN[1])
RM = 6378137.0

Q = dict(  # [invented] reader tuning, every value written into the output
    WIN_M=2.5, BIN_M=0.25, REACH_M=30.0, BAND_M=0.75, STEP_MIN_M=0.06, STEP_MAX_M=0.40, STAY_M=1.5,
    MIN_HALF_M=1.5, MEDIAN_MAX_M=14.0, MOUTH_X=1.6, CONTRAST_MIN=30.0, AER_STAY_M=0.5, AER_SPREAD_M=1.5,
    DISAGREE_M=0.3, SMOOTH_N=5, I_CONTRAST_MIN=400.0, I_ASPHALT_MAX=250.0, KERB_SEARCH_M=1.5, EDGE_OUTLIER_M=1.0)


# --- frame ---------------------------------------------------------------------------------------------------------

def en(lon, lat):
    return (np.asarray(lon, float) - ORIGIN[0]) * MLON, (np.asarray(lat, float) - ORIGIN[1]) * MLAT


def lonlat(E, N):
    return np.asarray(E, float) / MLON + ORIGIN[0], np.asarray(N, float) / MLAT + ORIGIN[1]


def lap(step):
    nodes = json.load(open(os.path.join(T, 'data', 'lap_line.plan.json')))['nodes']
    E, N = en([n['lon'] for n in nodes], [n['lat'] for n in nodes])
    P = np.stack([E, N], 1)
    P = np.vstack([P, P[:1]])
    sv = geom.cumlen(P)
    way = [n['way'] for n in nodes] + [nodes[-1]['way']]
    leg = [n['leg'] for n in nodes] + [nodes[-1]['leg']]
    s = np.arange(0.0, sv[-1], step)
    X = np.stack([np.interp(s, sv, P[:, 0]), np.interp(s, sv, P[:, 1])], 1)
    k = np.clip(np.searchsorted(sv, s, side='right'), 1, len(sv) - 1)   # the node that ENDS the segment: its way
    T_, L = geom.normals(X, closed=True)
    return {'s': s, 'P': X, 'L': L, 'T': T_, 'way': [way[i] for i in k], 'leg': [leg[i] for i in k], 'length': float(sv[-1])}


def osm_ways():
    o = json.load(open(os.path.join(T, 'source', 'osm.json')))
    return {w['id']: w for w in o['ways']}


# --- lidar ---------------------------------------------------------------------------------------------------------

def lidar_corridor(data, LP, pad=40.0):
    cache = os.path.join(data, 'widths-cache')
    os.makedirs(cache, exist_ok=True)
    f = os.path.join(cache, 'lidar_corridor.npz')
    if os.path.exists(f):
        return dict(np.load(f))
    import laspy
    tree = cKDTree(LP['P'])
    parts = []
    for p in sorted(glob.glob(os.path.join(data, 'lidar', '*.laz'))):
        las = laspy.read(p)
        x, y = np.asarray(las.x), np.asarray(las.y)
        lon = np.degrees(x / RM)
        lat = np.degrees(2 * np.arctan(np.exp(y / RM)) - np.pi / 2)
        E, N = en(lon, lat)
        d, _ = tree.query(np.stack([E, N], 1), distance_upper_bound=pad)
        m = np.isfinite(d)
        parts.append((E[m], N[m], np.asarray(las.z)[m], np.asarray(las.classification)[m], np.asarray(las.intensity)[m]))
    out = {k: np.concatenate([q[i] for q in parts]) for i, k in enumerate(('E', 'N', 'z', 'cls', 'I'))}
    # EPT nodes overlap across depths only by containment, never by duplicate points; keep as is
    np.savez(f, **out)
    return out


def lidar_section(Pk, Lk, Tk, tree, Lg):
    """Ground profile across the station: bin centres, median z per bin (nan where empty), median intensity."""
    r = Q['REACH_M'] + 1
    idx = tree.query_ball_point(Pk, math.hypot(r, Q['WIN_M']))
    if not idx:
        return None
    idx = np.asarray(idx)
    d = np.stack([Lg['E'][idx] - Pk[0], Lg['N'][idx] - Pk[1]], 1)
    a = d @ Tk
    o = d @ Lk
    m = (np.abs(a) <= Q['WIN_M']) & (np.abs(o) <= Q['REACH_M'])
    if m.sum() < 20:
        return None
    o, z, I = o[m], Lg['z'][idx][m], Lg['I'][idx][m]
    nb = int(round(2 * Q['REACH_M'] / Q['BIN_M']))
    b = np.clip(((o + Q['REACH_M']) / Q['BIN_M']).astype(int), 0, nb - 1)
    order = np.argsort(b, kind='stable')
    b, z, I = b[order], z[order], I[order]
    cuts = np.searchsorted(b, np.arange(nb + 1))
    zm = np.full(nb, np.nan)
    Im = np.full(nb, np.nan)
    for i in range(nb):
        if cuts[i + 1] > cuts[i]:
            zm[i] = np.median(z[cuts[i]:cuts[i + 1]])
            Im[i] = np.median(I[cuts[i]:cuts[i + 1]])
    c = -Q['REACH_M'] + (np.arange(nb) + 0.5) * Q['BIN_M']
    return c, zm, Im


def _nanmed(v):
    v = v[np.isfinite(v)]
    return float(np.median(v)) if len(v) else np.nan


def sgn_i(sgn):
    return 1 if sgn > 0 else -1


def kerb_faces(c, zm, sgn, start=None, limit=None):
    """Outward from the line on one side: faces found. Returns dict(face, step, median_far, on_line) or None."""
    bw = int(round(Q['BAND_M'] / Q['BIN_M']))
    sw = int(round(Q['STAY_M'] / Q['BIN_M']))
    i0 = int(np.argmin(np.abs(c)))
    order = range(i0, len(c) - bw - sw) if sgn > 0 else range(i0, bw + sw, -1)
    on_line = None
    road_z = None
    for i in order:
        off = abs(c[i])
        if limit is not None and off > limit:
            break
        if start is not None and off < start:
            continue
        inner = zm[i - bw:i] if sgn > 0 else zm[i + 1:i + 1 + bw]
        outer = zm[i:i + bw] if sgn > 0 else zm[i - bw + 1:i + 1]
        stay = zm[i:i + sw] if sgn > 0 else zm[i - sw + 1:i + 1]
        zi, zo, zs = _nanmed(inner), _nanmed(outer), _nanmed(stay)
        if not (np.isfinite(zi) and np.isfinite(zo) and np.isfinite(zs)):
            continue
        if road_z is None and off >= 0.5:
            road_z = zi
        st = zo - zi
        if Q['STEP_MIN_M'] <= st <= Q['STEP_MAX_M'] and zs - zi >= Q['STEP_MIN_M'] - 0.01:
            # locate: the boundary (between two bins) of the largest step over the next band's worth of positions
            best, bi = st, i
            for jx in range(1, bw + 1):
                ii_ = i + sgn_i(sgn) * jx
                if not (bw <= ii_ < len(c) - bw):
                    break
                a_ = zm[ii_ - bw:ii_] if sgn > 0 else zm[ii_ + 1:ii_ + 1 + bw]
                b_ = zm[ii_:ii_ + bw] if sgn > 0 else zm[ii_ - bw + 1:ii_ + 1]
                v = _nanmed(b_) - _nanmed(a_)
                if np.isfinite(v) and v > best:
                    best, bi = v, ii_
            face = abs(c[bi]) - 0.5 * Q['BIN_M']
            st = best
            if off < Q['MIN_HALF_M'] and start is None:
                on_line = on_line or {'face': round(face, 2), 'step': round(st, 3)}
                continue
            # raised median? a step back down to road level within MEDIAN_MAX_M, flat road past it
            far = None
            ii = i + sw if sgn > 0 else i - sw
            top = zs
            mm = int(Q['MEDIAN_MAX_M'] / Q['BIN_M'])
            rng_ = range(ii, min(len(c) - bw, i + mm)) if sgn > 0 else range(ii, max(bw, i - mm), -1)
            for jx in rng_:
                a_ = zm[jx - bw:jx] if sgn > 0 else zm[jx + 1:jx + 1 + bw]
                b_ = zm[jx:jx + 3 * bw] if sgn > 0 else zm[jx - 3 * bw + 1:jx + 1]
                za, zb = _nanmed(a_), _nanmed(b_)
                if np.isfinite(za) and np.isfinite(zb) and za - zb >= Q['STEP_MIN_M'] and abs(zb - zi) <= 0.12 \
                        and abs(za - top) <= 0.15:
                    far = round(abs(c[jx]), 2)
                    break
            return {'face': round(float(face), 2), 'step': round(float(st), 3), 'median_far': far, 'on_line': on_line,
                    'road_z': None if road_z is None else round(float(road_z), 2)}
    return {'face': None, 'on_line': on_line, 'road_z': None if road_z is None else round(float(road_z), 2)}


# --- aerial --------------------------------------------------------------------------------------------------------

class Drapp:
    """The year's DRAPP tiles as memory maps, EPSG:2232 (US ft), 0.25 ft pixels; tfw = upper-left pixel centre."""

    def __init__(self, data, year):
        import tifffile
        from pyproj import Transformer
        self.tr = Transformer.from_crs('EPSG:4326', 'EPSG:2232', always_xy=True)
        self.tiles = []
        for p in sorted(glob.glob(os.path.join(data, 'drapp', str(year), '*.tif'))):
            t = [float(v) for v in open(p[:-4] + '.tfw').read().split()]
            a = tifffile.memmap(p)
            self.tiles.append((t[0], t[4], t[5], a))

    def lum(self, E, N):
        lon, lat = lonlat(E, N)
        X, Y = self.tr.transform(lon, lat)
        out = np.full(np.shape(E), np.nan, np.float32)
        for px, x0, y0, a in self.tiles:
            col = (X - x0) / px
            row = (y0 - Y) / px
            m = (col >= 0) & (row >= 0) & (col < a.shape[1] - 1) & (row < a.shape[0] - 1)
            if not m.any():
                continue
            r0, r1 = int(row[m].min()), int(row[m].max()) + 2
            c0, c1 = int(col[m].min()), int(col[m].max()) + 2
            w = np.asarray(a[r0:r1, c0:c1, :3], np.float32).mean(-1)
            out[m] = ndimage.map_coordinates(w, [row[m] - r0, col[m] - c0], order=1, mode='nearest')
        return out


def aerial_section(dr, Pk, Lk, Tk):
    ds = 0.1
    offs = np.arange(-Q['REACH_M'], Q['REACH_M'] + 1e-9, ds)
    al = np.linspace(-Q['AER_SPREAD_M'], Q['AER_SPREAD_M'], 7)
    E = Pk[0] + offs[None, :] * Lk[0] + al[:, None] * Tk[0]
    N = Pk[1] + offs[None, :] * Lk[1] + al[:, None] * Tk[1]
    v = dr.lum(E, N)
    if np.isnan(v).mean() > 0.2:
        return None
    prof = ndimage.gaussian_filter1d(np.nanmedian(v, 0), 1.5)
    return offs, prof


def rise_edge(offs, prof, sgn, contrast_min, stay_m):
    """The first outward place past MIN_HALF_M where the profile rises contrast_min over the road's own level (median
    within +-MIN_HALF_M) and stays there for stay_m (90 % of samples). A fixed rise, not halfway to the far side: the
    far side is often another asphalt road, a dark tree lawn or a shadow, so its level says nothing about the edge."""
    ds = offs[1] - offs[0]
    i0 = int(np.argmin(np.abs(offs)))
    core = np.abs(offs) <= Q['MIN_HALF_M']
    road = float(np.median(prof[core]))
    side = prof[(offs * sgn) > Q['MIN_HALF_M']]
    if len(side) < 10:
        return None, 'no_data', road
    if float(np.percentile(side, 95)) - road < contrast_min:
        return None, 'no_contrast', road
    thr = road + contrast_min
    stay = max(2, int(round(stay_m / ds)))
    idx = range(i0, len(offs) - stay) if sgn > 0 else range(i0, stay, -1)
    for i in idx:
        if abs(offs[i]) < Q['MIN_HALF_M']:
            continue
        seg = prof[i:i + stay] if sgn > 0 else prof[i - stay + 1:i + 1]
        if prof[i] >= thr and (seg >= thr).mean() >= 0.9:
            j = i - 1 if sgn > 0 else i + 1
            a, b = prof[j], prof[i]
            frac = (thr - a) / max(b - a, 1e-6)
            return abs(offs[j]) + frac * abs(offs[i] - offs[j]), 'seen', road
    return None, 'none', road


def intensity_edge(c, Im, sgn):
    ok = np.isfinite(Im)
    if ok.sum() < 20:
        return None, 'no_data'
    v = np.interp(c, c[ok], Im[ok])
    v = ndimage.gaussian_filter1d(v, 1.0)
    x, why, road = rise_edge(c, v, sgn, Q['I_CONTRAST_MIN'], Q['AER_STAY_M'])
    if road > Q['I_ASPHALT_MAX']:
        return None, 'concrete_road'
    return x, why


def aerial_edge(offs, prof, sgn):
    x, why, _ = rise_edge(offs, prof, sgn, Q['CONTRAST_MIN'], Q['AER_STAY_M'])
    return x, why


def _unused_aerial_edge(offs, prof, sgn):
    ds = offs[1] - offs[0]
    i0 = int(np.argmin(np.abs(offs)))
    core = np.abs(offs) <= Q['MIN_HALF_M']
    road = float(np.median(prof[core]))
    side = prof[(offs * sgn) > Q['MIN_HALF_M']]
    side = side[:int(Q['REACH_M'] / ds)]
    if len(side) < 10:
        return None, 'no_image'
    bright = float(np.percentile(side, 85))
    if bright - road < Q['CONTRAST_MIN']:
        return None, 'no_contrast'
    thr = road + 0.5 * (bright - road)
    stay = int(Q['AER_STAY_M'] / ds)
    idx = range(i0, len(offs) - stay) if sgn > 0 else range(i0, stay, -1)
    for i in idx:
        if abs(offs[i]) < Q['MIN_HALF_M']:
            continue
        seg = prof[i:i + stay] if sgn > 0 else prof[i - stay + 1:i + 1]
        if prof[i] >= thr and (seg >= thr).mean() >= 0.9:
            j = i - 1 if sgn > 0 else i + 1
            a, b = prof[j], prof[i]
            frac = (thr - a) / max(b - a, 1e-6)
            return abs(offs[j]) + frac * ds, 'seen'
    return None, 'none'


# --- run -----------------------------------------------------------------------------------------------------------

def run(data, step):
    t0 = time.time()
    LP = lap(step)
    n = len(LP['s'])
    Lall = lidar_corridor(data, LP)
    g = Lall['cls'] == 2
    Lg = {k: Lall[k][g] for k in ('E', 'N', 'z', 'I')}
    tree = cKDTree(np.stack([Lg['E'], Lg['N']], 1))
    print(f'lap {LP["length"]:.1f} m, {n} stations; ground returns {g.sum():,} of {len(g):,}  ({time.time()-t0:.0f}s)', flush=True)
    dr = Drapp(data, 2022)
    W = osm_ways()
    covered = np.array([bool(W.get(w, {}).get('tags', {}).get('covered') == 'yes'
                             or 'tunnel' in W.get(w, {}).get('tags', {})) for w in LP['way']])
    rows = []
    for k in range(n):
        Pk, Lk, Tk = LP['P'][k], LP['L'][k], LP['T'][k]
        row = {'s': round(float(LP['s'][k]), 1), 'way': LP['way'][k], 'covered': bool(covered[k])}
        sec = None if covered[k] else lidar_section(Pk, Lk, Tk, tree, Lg)
        aer = None if covered[k] else aerial_section(dr, Pk, Lk, Tk)
        for side, sgn in (('left', 1.0), ('right', -1.0)):
            li, li_why = intensity_edge(sec[0], sec[2], sgn) if sec is not None else (None, 'no_data')
            ae, why = aerial_edge(aer[0], aer[1], sgn) if aer is not None else (None, 'no_image')
            # the kerb search runs free from the line: tying it to an asphalt reading let bike-lane paint, a concrete
            # lane or a tower's shadow carry it off the kerb (checked on stills at 14th Ave and 15th St, 2026-11-24)
            lid = kerb_faces(sec[0], sec[1], sgn) if sec is not None else None
            row[side] = {'lidar': lid, 'intensity': None if li is None else round(float(li), 2), 'intensity_why': li_why,
                         'aerial': None if ae is None else round(float(ae), 2), 'aerial_why': why}
        rows.append(row)
        if k % 250 == 0:
            print(f'  station {k}/{n}  s={LP["s"][k]:.0f}  ({time.time()-t0:.0f}s)', flush=True)
    return LP, rows, Lall, W, covered


def decide(LP, rows, covered):
    """Edges of record per side. ASPHALT EDGE: lidar intensity (first) or aerial; measured when both agree within
    DISAGREE_M. KERB FACE: the lidar ground step searched from the asphalt edge outward. PAN: per way, the median of
    kerb face - asphalt edge. RECORD: the kerb face (measured); else the asphalt edge plus the way's pan (measured when
    the two asphalt readings agree, detected from one); else inferred (filled linearly along s)."""
    n = len(rows)
    ways = [r['way'] for r in rows]
    s = LP['s']
    out = {}
    def arr(side, key):
        return np.array([r[side][key] if r[side][key] is not None else np.nan for r in rows], float)
    for side in ('left', 'right'):
        li, ae = arr(side, 'intensity'), arr(side, 'aerial')
        K = np.array([r[side]['lidar']['face'] if r[side]['lidar'] and r[side]['lidar'].get('face') is not None
                      else np.nan for r in rows], float)
        # cars, crosswalk bars, a patch: an asphalt reading more than EDGE_OUTLIER_M off its own running median is dropped
        for v in (li, ae):
            okv = np.isfinite(v)
            mv = geom.running_median(v, okv, 21, closed=True)
            v[okv & np.isfinite(mv) & (np.abs(v - mv) > Q['EDGE_OUTLIER_M'])] = np.nan
        A = np.where(np.isfinite(li), li, ae)
        both = np.isfinite(li) & np.isfinite(ae)
        agree = both & (np.abs(li - ae) <= Q['DISAGREE_M'])
        dis = both & ~agree
        pan = {}
        # an asphalt reading well inside the kerb is paint, a bike lane or a concrete lane, not the gutter's edge
        A[np.isfinite(K) & np.isfinite(A) & ((A < K - Q['KERB_SEARCH_M']) | (A > K + 0.3))] = np.nan
        for w in set(ways):
            m = np.array([x == w for x in ways]) & np.isfinite(K) & np.isfinite(A)
            d = (K - A)[m]
            d = d[(d >= -0.3) & (d <= Q['KERB_SEARCH_M'])]
            pan[w] = float(np.median(d)) if len(d) >= 5 else np.nan
        allp = [v for v in pan.values() if np.isfinite(v)]
        pan_all = float(np.median(allp)) if allp else 0.0
        panv = np.array([pan[w] if np.isfinite(pan[w]) else pan_all for w in ways])
        x = np.full(n, np.nan)
        grade = np.array(['inferred'] * n, dtype=object)
        src = np.array([''] * n, dtype=object)
        mK = np.isfinite(K)
        x[mK] = K[mK]; grade[mK] = 'measured'; src[mK] = 'kerb_step'
        mA = ~mK & np.isfinite(A)
        x[mA] = (A + panv)[mA]
        grade[mA & agree] = 'measured'; grade[mA & ~agree] = 'detected'
        src[mA & np.isfinite(li)] = 'intensity+pan'; src[mA & ~np.isfinite(li)] = 'aerial+pan'
        # a mouth: an edge far past the side's running median is another road's
        ok = np.isfinite(x)
        med = geom.running_median(x, ok, 41, closed=True)
        mouth = ok & np.isfinite(med) & (x > Q['MOUTH_X'] * med) & (x - med > 2.0)
        x[mouth] = np.nan; grade[mouth] = 'inferred'; src[mouth] = 'mouth'
        rest = ~np.isfinite(x)
        src[rest & covered] = 'covered: between measured portals [invented]'
        src[rest & ~covered & (src == '')] = 'no_reading'
        good = np.isfinite(x)
        S2 = np.r_[s[good] - LP['length'], s[good], s[good] + LP['length']]
        X2 = np.r_[x[good], x[good], x[good]]
        xr = np.where(good, x, np.interp(s, S2, X2))
        xs = geom.running_median(xr, np.ones(n, bool), Q['SMOOTH_N'], closed=True)
        xs = np.where(covered, xr, xs)
        # TWO SOURCES (the brief): the aerial (2022) against the lidar (2020). Where the lidar has a kerb face, the
        # aerial's asphalt edge plus the way's measured pan is compared with it; else the aerial with the lidar's
        # intensity edge (both asphalt edges). Disagreement: more than DISAGREE_M apart.
        aeF = ae + panv
        vsK = np.isfinite(aeF) & np.isfinite(K) & ~mouth
        vsI = np.isfinite(ae) & np.isfinite(li) & ~np.isfinite(K)
        both = vsK | vsI
        dis = (vsK & (np.abs(aeF - K) > Q['DISAGREE_M'])) | (vsI & (np.abs(ae - li) > Q['DISAGREE_M']))
        delta = np.where(vsK, aeF - K, np.where(vsI, ae - li, np.nan))
        out[side] = dict(x=xs, raw=xr, grade=grade, src=src, K=K, li=li, ae=ae, pan=pan, pan_all=pan_all,
                         disagree=dis, both=both, mouth=mouth, delta=delta)
    return out


def opposing_lines(LP, W):
    """OSM carriageways that are not the lap's, densified to 0.5 m, for the 'spans the opposing carriageway' flag:
    where the two kerbs measured hold another OSM carriageway's line between them, the street is divided by paint
    only (or not at all) and the width is the whole street's."""
    o = json.load(open(os.path.join(T, 'source', 'osm.json')))
    lapw = set(LP['way'])
    major = {'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential',
             'primary_link', 'secondary_link', 'tertiary_link', 'trunk_link'}
    pts, ids = [], []
    for w in o['ways']:
        if w['id'] in lapw or w['tags'].get('highway') not in major:
            continue
        ll = [o['nodes'][str(n)] for n in w['nodes'] if str(n) in o['nodes']]
        if len(ll) < 2:
            continue
        E, N = en([a[0] for a in ll], [a[1] for a in ll])
        P = geom.resample(np.stack([E, N], 1), 0.5)
        pts.append(P)
        ids += [w['id']] * len(P)
    return cKDTree(np.vstack(pts)), np.array(ids), {w['id']: w for w in o['ways']}


def medians(rows):
    out = []
    for r in rows:
        md = []
        for side, sgn in (('left', 1), ('right', -1)):
            l = r[side]['lidar']
            if l and l.get('on_line'):
                md.append({'side': 'on_line', 'face': l['on_line']['face'] * sgn, 'raised': True})
            if l and l.get('median_far') and l.get('face') is not None:
                md.append({'side': side, 'inner': l['face'] * sgn, 'outer': l['median_far'] * sgn, 'raised': True})
        out.append(md)
    return out


def bridges(LP, Lall):
    m = Lall['cls'] == 17
    if not m.any():
        return []
    B = np.stack([Lall['E'][m], Lall['N'][m]], 1)
    z = Lall['z'][m]
    tree = cKDTree(LP['P'])
    d, i = tree.query(B)
    near = d <= 12
    if not near.any():
        return []
    s_of = LP['s'][i[near]]
    o_of = ((B[near] - LP['P'][i[near]]) * LP['L'][i[near]]).sum(1)
    zb = z[near]
    order = np.argsort(s_of)
    s_of, o_of, zb = s_of[order], o_of[order], zb[order]
    spans = []
    a = 0
    for j in range(1, len(s_of) + 1):
        if j == len(s_of) or s_of[j] - s_of[j - 1] > 15:
            if s_of[j - 1] - s_of[a] >= 10:
                spans.append((a, j))
            a = j
    G = Lall['cls'] == 2
    gt = cKDTree(np.stack([Lall['E'][G], Lall['N'][G]], 1))
    gz = Lall['z'][G]
    out = []
    for a, j in spans:
        ss, oo, zz = s_of[a:j], o_of[a:j], zb[a:j]
        s0, s1 = float(ss.min()), float(ss.max())
        k = int(np.argmin(np.abs(LP['s'] - (s0 + s1) / 2)))
        along = []
        for sb in np.arange(math.floor(s0), s1 + 2, 2.0):
            mm = (np.abs(ss - sb) <= 1.0) & (np.abs(oo) <= 4.0)
            if mm.sum() >= 3:
                along.append([round(float(sb), 1), round(float(np.median(zz[mm])), 3), int(mm.sum())])
        mid = (s0 + s1) / 2
        mm = np.abs(ss - mid) <= 5
        across = []
        for ob in np.arange(-15, 15.01, 0.5):
            q = mm & (np.abs(oo - ob) <= 0.25)
            if q.sum() >= 2:
                across.append([round(float(ob), 2), round(float(np.median(zz[q])), 3), int(q.sum())])

        def abut(sv):
            kk = int(np.argmin(np.abs(LP['s'] - sv)))
            idx = gt.query_ball_point(LP['P'][kk], 4.0)
            return round(float(np.median(gz[idx])), 3) if idx else None
        E, N = LP['P'][k]
        lo, la = lonlat(E, N)
        out.append({'s_from': round(s0, 1), 's_to': round(s1, 1), 'length_m': round(s1 - s0, 1),
                    'way': LP['way'][k], 'leg': LP['leg'][k], 'mid_lonlat': [round(float(lo), 7), round(float(la), 7)],
                    'deck_points': int(j - a), 'deck_z_p50': round(float(np.median(zz)), 3),
                    'abutment_ground_z': {'before': abut(s0 - 6), 'after': abut(s1 + 6)},
                    'profile_along': {'cols': ['s', 'z', 'n'], 'rows': along},
                    'profile_across_mid': {'cols': ['offset_left+', 'z', 'n'], 'rows': across},
                    'deck_edges_from_class17': [round(float(np.percentile(oo[mm], 2)), 2), round(float(np.percentile(oo[mm], 98)), 2)] if mm.sum() > 10 else None})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='/Volumes/Sundowning/Claude/airoso-data/denver-grand-prix')
    ap.add_argument('--step', type=float, default=2.5)
    a = ap.parse_args()
    LP, rows, Lall, W, covered = run(a.data, a.step)
    D = decide(LP, rows, covered)
    MD = medians(rows)
    OT, OI, OW = opposing_lines(LP, W)
    stations = []
    for k, r in enumerate(rows):
        P, L = LP['P'][k], LP['L'][k]
        st = {'s': r['s'], 'way': r['way'], 'leg': LP['leg'][k], 'covered': r['covered']}
        lo, la = lonlat(*P)
        st['line_EN'] = [round(float(P[0]), 2), round(float(P[1]), 2)]
        st['line_lonlat'] = [round(float(lo), 7), round(float(la), 7)]
        for side, sgn in (('left', 1.0), ('right', -1.0)):
            d = D[side]
            x = float(d['x'][k])
            Ee = P + sgn * x * L
            elo, ela = lonlat(*Ee)
            lid = r[side]['lidar'] or {}
            st[side] = {'offset': round(x, 2), 'EN': [round(float(Ee[0]), 2), round(float(Ee[1]), 2)],
                        'lonlat': [round(float(elo), 7), round(float(ela), 7)], 'grade': d['grade'][k],
                        'source': d['src'][k],
                        'kerb_face': None if not np.isfinite(d['K'][k]) else round(float(d['K'][k]), 2),
                        'kerb_step_m': lid.get('step') if np.isfinite(d['K'][k]) else None,
                        'asphalt_edge_intensity': r[side]['intensity'], 'intensity_why': r[side]['intensity_why'],
                        'asphalt_edge_aerial': r[side]['aerial'], 'aerial_why': r[side]['aerial_why'],
                        'aerial_minus_lidar_m': None if not np.isfinite(d['delta'][k]) else round(float(d['delta'][k]), 2),
                        'disagree': bool(d['disagree'][k])}
        st['width'] = round(float(D['left']['x'][k] + D['right']['x'][k]), 2)
        # another OSM carriageway between the two kerbs (crossing it at right angles at a junction does not count:
        # the way must run within 30 degrees of the lap's own direction)
        offs = np.arange(-D['right']['x'][k] + 0.5, D['left']['x'][k] - 0.5, 0.5)
        Q_ = P[None, :] + offs[:, None] * L[None, :]
        dd, ii = OT.query(Q_, distance_upper_bound=0.75)
        hit = []
        for o_, d_, i_ in zip(offs, dd, ii):
            if np.isfinite(d_) and abs(o_) > 1.0:
                wid = int(OI[i_])
                j = OT.query(OT.data[i_] + 0.0, k=2)[1][1]
                tv = OT.data[j] - OT.data[i_]
                if np.linalg.norm(tv) > 0 and abs(np.dot(tv / np.linalg.norm(tv), LP['T'][k])) > math.cos(math.radians(30)):
                    hit.append((round(float(o_), 1), wid))
        st['opposing_carriageway_within'] = None if not hit else {'offset': hit[0][0], 'way': hit[0][1],
                                                                  'name': OW[hit[0][1]]['tags'].get('name')}
        st['medians'] = MD[k]
        stations.append(st)
    # per stretch (OSM way, in lap order)
    runs_ = []                               # contiguous runs of one way, in lap order (the start/finish way runs twice)
    for k, r in enumerate(rows):
        if runs_ and runs_[-1][0] == r['way']:
            runs_[-1][1].append(k)
        else:
            runs_.append((r['way'], [k]))
    stretches = []
    for w, idx in runs_:
        wv = np.array([stations[k]['width'] for k in idx])
        tg = W.get(w, {}).get('tags', {})
        g = {side: {gr: int(sum(1 for k in idx if stations[k][side]['grade'] == gr)) for gr in ('measured', 'detected', 'inferred')}
             for side in ('left', 'right')}
        both = sum(int(D[sd]['both'][k]) for sd in ('left', 'right') for k in idx)
        dis = sum(int(D[sd]['disagree'][k]) for sd in ('left', 'right') for k in idx)
        dis_runs = []
        for sd in ('left', 'right'):
            msk = np.array([bool(D[sd]['disagree'][k]) for k in idx])
            for a_, b_ in geom.runs(msk):
                dis_runs.append({'side': sd, 's_from': rows[idx[a_]]['s'], 's_to': rows[idx[b_]]['s']})
        meas = (g['left']['measured'] + g['right']['measured']) / (2 * len(idx))
        det = (g['left']['detected'] + g['right']['detected']) / (2 * len(idx))
        conf = 'high' if meas >= 0.7 else ('medium' if meas + det >= 0.6 else 'low')
        if all(rows[k]['covered'] for k in idx):
            conf = 'none (covered: between measured portals)'
        stretches.append({
            'way': w, 'name': tg.get('name'), 'leg': LP['leg'][idx[0]], 's_from': rows[idx[0]]['s'], 's_to': rows[idx[-1]]['s'],
            'stations': len(idx), 'osm_lanes': tg.get('lanes'), 'osm_oneway': tg.get('oneway'), 'surface': tg.get('surface'),
            'width_m': {'p10': round(float(np.percentile(wv, 10)), 2), 'p50': round(float(np.median(wv)), 2),
                        'p90': round(float(np.percentile(wv, 90)), 2)},
            'grades': g, 'confidence': conf,
            'gutter_pan_m': {sd: (None if not np.isfinite(D[sd]['pan'].get(w, np.nan)) else round(float(D[sd]['pan'][w]), 2))
                             for sd in ('left', 'right')},
            'two_readings': both, 'disagree_over_0.3m': dis,
            'disagree_share': None if not both else round(dis / both, 3), 'disagree_runs': dis_runs[:40],
            'aerial_minus_lidar_m_p50': (lambda v: round(float(np.median(v)), 2) if len(v) else None)(
                [D[sd]['delta'][k] for sd in ('left', 'right') for k in idx if np.isfinite(D[sd]['delta'][k])]),
            'spans_opposing_carriageway_share': round(sum(1 for k in idx if stations[k]['opposing_carriageway_within']) / len(idx), 2),
            'raised_median_stations': sum(1 for k in idx if any(m['raised'] and m['side'] != 'on_line' for m in MD[k])),
            'kerb_step_m_p50': (lambda v: round(float(np.median(v)), 3) if v else None)(
                [stations[k][sd]['kerb_step_m'] for k in idx for sd in ('left', 'right') if stations[k][sd]['kerb_step_m']])})
    # Stout portals
    cov = np.where(covered)[0]
    portals = None
    if len(cov):
        k0, k1 = int(cov[0]), int(cov[-1])
        Gm = Lall['cls'] != 2
        nt = cKDTree(np.stack([Lall['E'][Gm], Lall['N'][Gm]], 1))
        def portal(k_out, k_edge, name):
            ks = [k for k in range(k_out - 4, k_out + 1)] if k_out < k_edge else [k for k in range(k_out, k_out + 5)]
            ks = [k % len(rows) for k in ks]
            wl = [stations[k]['left']['offset'] for k in ks]
            wr = [stations[k]['right']['offset'] for k in ks]
            P = LP['P'][k_edge]
            idx = nt.query_ball_point(P, 8.0)
            zr = Lall['z'][Gm][idx] if idx else np.array([])
            road = [rows[k]['left']['lidar'].get('road_z') for k in ks if rows[k]['left']['lidar']]
            road = [v for v in road if v is not None]
            return {'name': name, 's': rows[k_edge]['s'], 'measured_at_s': [rows[k]['s'] for k in ks],
                    'left_offset_m': round(float(np.median(wl)), 2), 'right_offset_m': round(float(np.median(wr)), 2),
                    'width_m': round(float(np.median(wl) + np.median(wr)), 2),
                    'grades': [stations[k]['left']['grade'] + '/' + stations[k]['right']['grade'] for k in ks],
                    'road_z': round(float(np.median(road)), 2) if road else None,
                    'structure_top_z_p95_within_8m': round(float(np.percentile(zr, 95)), 2) if len(zr) else None,
                    'clear_height_m': 5.0, 'clear_height_source': 'OSM maxheight=5 (tagged; not measured: the lidar sees the roof, not the soffit)'}
        wt = W.get(rows[k0]['way'], {}).get('tags', {})
        portals = {'way': rows[k0]['way'], 'tags': {k: wt[k] for k in ('name', 'tunnel', 'covered', 'maxheight', 'lanes', 'layer') if k in wt},
                   's_from': rows[k0]['s'], 's_to': rows[k1]['s'], 'length_m': round(rows[k1]['s'] - rows[k0]['s'] + LP['s'][1], 1),
                   'entry': portal(k0 - 1, k0, 'entry (south-west)'), 'exit': portal(k1 + 1, k1, 'exit (north-east)'),
                   'inside': 'between measured portals [invented]: edges interpolated linearly from entry to exit; no source sees under the roof',
                   'covered_ways': sorted({rows[k]['way'] for k in cov})}
    meta = {'generated': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'script': 'tracks/denver-grand-prix/source/widths/widths.py',
            'frame': {'origin_lonlat': ORIGIN, 'series': 'scripts.aerial.engine.ortho.mpd', 'offset_sign': '+ = driver left'},
            'lap_length_m': round(LP['length'], 1), 'step_m': a.step, 'tuning_invented': Q,
            'sources': {'lidar': 'USGS 3DEP CO_DRCOG_2_2020 (flown 2020-05-27), class 2 ground; class 17 bridge deck',
                        'aerial': 'DRCOG DRAPP 2022 3-inch (EPSG:2232), luminance', 'line': 'data/lap_line.plan.json (OSM 2026-11-23)'},
            'state': 'Colfax and every street as the 2022 aerial / 2020 lidar show them (D8); OSM present-day bus lanes not built'}
    for side in ('left', 'right'):
        meta[f'pan_all_{side}_m'] = round(D[side]['pan_all'], 2)
    tot = {gr: sum(1 for st in stations for sd in ('left', 'right') if st[sd]['grade'] == gr) for gr in ('measured', 'detected', 'inferred')}
    meta['grades_all_edges'] = tot
    json.dump({'meta': meta, 'stations': stations}, open(os.path.join(HERE, 'widths.json'), 'w'), separators=(',', ':'))
    json.dump({'meta': meta, 'stretches': stretches}, open(os.path.join(HERE, 'stretches.json'), 'w'), indent=1)
    json.dump({'meta': meta, 'bridges': bridges(LP, Lall)}, open(os.path.join(HERE, 'bridges.json'), 'w'), indent=1)
    json.dump({'meta': meta, 'stout': portals}, open(os.path.join(HERE, 'stout_portals.json'), 'w'), indent=1)
    print(json.dumps(tot), 'pan', meta.get('pan_all_left_m'), meta.get('pan_all_right_m'))


if __name__ == '__main__':
    main()
