"""Lake Murray, Jackson Dr north (piece D): the road's two outer edges per station off the USGS 2024 lidar, and the real
road's middle against the built one. G10 job lm-jackson-curbs-20261123. Reads only; downloads nothing. Run under
nice -n 19 ionice -c3, with -I. The method is the outer-curb reading of source/expansion/mg_median/mg_median_faces_g10.py
(Mission Gorge), with three changes for D's hillside and canopy: the returns are the LAST returns (as jackson_paint's
intensity work: class 2 is thin under the trees, and the first returns are canopy up to 30 m over the verge); the
detector measures each step against the road's own local trend (a line through the 1.2 m just inside), not one
cross-fall line for the whole side (D's shoulders bend); and an edge that DROPS (a bank falling away) is read as well
as one that rises.

    python -I jackson_curbs_g10.py <tiles dir> <lm tool dir> <airoso dir> <out json>

  <tiles dir>    USGS_LPC_CA_SanDiegoCo_D24_*.laz (EPSG read off each header; shrub_heights.tile_list)
  <lm tool dir>  the folder holding the lm-shrub tool, shrub_heights.py (its projection, tile list and LAZ reader)
  <airoso dir>   a checkout (or git archive) of this repository: tools/expansion_pieces.py and Lake Murray's data/
  <out json>     jackson_curbs_D.lidar.g10.json
Each may instead come from the environment: JC_TILES, JC_LM_TOOL, JC_AIROSO, JC_OUT.

FRAME. Piece D's own frame, tools/expansion_pieces.Piece.frame (imported): the station point by linear interpolation of
pieces[D].stations, the tangent the chord over +-2.5 m, the left normal (-t_z, t_x). u = metres off D's line, + = LEFT
of D's travel along increasing s (J4 -> J5), as jackson_intensity_full.py has it. Lidar E, N -> local x, z by
shrub_heights.Track.to_local (pyproj EPSG 6340 -> 4326, then the WGS84 metres-per-degree series at the origin).

PER STATION (every 2.5 m over s 225-492.5 and s 1240-1300), the returns within +-HALF_ALONG along and +-HALF_ACROSS
across; every LAST return not withheld and not ASPRS noise (7 / 18); the along-road grade (off class 2) taken out. Per
side:
  profile  per BIN m bin across, the OUT_Q percentile of the returns (what canopy is left, and the odd car, don't lift it);
  detector D(x) = the median over the bins in (x, x + W] of their height over a straight line fitted to the bins in
           [x - TREND_M, x) (at least TREND_MIN of them), outward;
  face     the first place outward past OUTER_FROM where D rises past CURB_DET or drops past -DROP_DET; refined on the
           points: a road line inside (GUARD..ROAD_M), an outer line outside (GUARD..WALK_M), a point "high" over the
           halfway height; the face where the fewest points fall on the wrong side, every such position between two
           neighbouring points kept, the face their middle and its uncertainty half the interval (the point spacing);
           returns over the two lines + 0.10 m (canopy, cars) left out of that; a candidate that gives no face hands on
           to the next within CONT_M outward (a gutter's lip before its curb); a face whose road side stands more than
           ROAD_TOL off the road near the line is unclear (canopy the last returns did not get under);
  type     curb: a rise of CURB_LO..CURB_HI; edge (rise): over CURB_HI (a wall, bank or hedge where the asphalt ends);
           edge (drop): the ground falls DROP_DET or more past the asphalt (a bank down); none: no rise or drop (a
           driveway or street mouth, or a flush edge); unclear: the rest.
The real road's middle = the mean of the two faces (curb or edge); the built road's middle = (left_m + right_m) / 2 of
D's own row. Each face also carries the median intensity of the last returns within 1 m inside and outside it (asphalt
reads dark): a cue, not a test. Every setting below marked [invented] is the method's choice, not a measurement.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from pyproj import Transformer
from scipy.spatial import cKDTree

RANGES = [(225.0, 492.5), (1240.0, 1300.0)]   # the request
BIN_SUM_M = 25.0            # the request: the summary per 25 m
HALF_ALONG = 1.25           # [invented] +- along the tangent (as on Mission Gorge)
HALF_ACROSS = 18.0          # the request: +-18 m (D's built edges sit about +7.5..+9.8 / -9.5..-12)
OUTER_FROM = 4.0            # [invented] an edge is searched from 4 m off the line outward (D has no raised island here)
BIN = 0.10                  # [invented] the profile's bins
W, MIN_BINS = 0.6, 3        # [invented] the detector's half-window, and the non-empty bins it needs each side
OUT_Q = 20                  # [invented] the profile's statistic per bin: this percentile of the returns
CURB_DET = 0.05             # [invented] a rise outward at least this big is a face candidate
DROP_DET = 0.10             # [invented] a drop outward at least this big is a face candidate (a gutter's dip stays under)
NONE_MAX = 0.05             # [invented] no |D| this big from OUTER_FROM out: "none"
CURB_LO, CURB_HI = 0.05, 0.35   # [invented] a curb's step; over CURB_HI an edge (rise)
GUARD, ROAD_M, WALK_M = 0.15, 2.0, 1.2   # [invented] the lines keep GUARD off the face; road ROAD_M inside, outer WALK_M out
FACE_WIN = 0.5              # [invented] points this close to a coarse face decide it
N_WIN = 150                 # [invented] returns needed on a side
N_WALK_BINS = 4             # [invented] bins with a return needed on the outer side
TREND_M, TREND_MIN = 1.2, 6   # [invented] the detector's local trend: a line through the bins 1.2 m inside x (6+ of them)
INT_M = 1.0                 # [invented] the intensity cue: last returns within this inside / outside the face
ROAD_TOL = 0.6              # [invented] a face's road side must stand within this of the road near the line (else canopy)
CONT_M = 1.0                # [invented] a candidate that gives no face hands on to the next within 1 m outward
MIN_BOTH = 5                # [invented] a 25 m bin's middle wants this many stations with both faces ...
MAX_IQR = 1.0               # [invented] ... and their differences' IQR at most this
NOISE = (7, 18)


def arg(i, env):
    if len(sys.argv) > i and not sys.argv[i].startswith("--"):
        return Path(sys.argv[i])
    if os.environ.get(env):
        return Path(os.environ[env])
    raise SystemExit(__doc__)


TDIR, TOOL, AIR, OUTP = arg(1, "JC_TILES"), arg(2, "JC_LM_TOOL"), arg(3, "JC_AIROSO"), arg(4, "JC_OUT")
sys.path.insert(0, str(TOOL))
sys.path.insert(0, str(AIR / "tools"))
import shrub_heights as SH  # noqa: E402  the lm-shrub tool: tile_list, chunks, Track (projection)
import expansion_pieces as ep  # noqa: E402  piece frame

LM = AIR / "tracks" / "san-diego-lake-murray"
T0 = time.time()


def log(*a):
    SH.log(f"[{time.time() - T0:6.1f}s]", *a)


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def r3(x, nd=3):
    if x is None:
        return None
    x = float(x)
    return round(x, nd) if math.isfinite(x) else None


def rng(v):
    v = [x for x in v if x is not None]
    if not v:
        return None
    return {"median": r3(np.median(v)), "min": r3(min(v)), "max": r3(max(v)), "iqr": r3(np.percentile(v, 75) - np.percentile(v, 25)),
            "n": len(v)}


doc, pieces = ep.load(LM / "data" / "expansion.north.json")
pc = pieces["D"]
assert pc.rec["name"] == "jackson_north"
origin = doc["frame"]["origin"]
S_ALL = [round(a + 2.5 * k, 1) for a, b in RANGES for k in range(int(round((b - a) / 2.5)) + 1)]
fchk = {}
nl = np.array([pc.frame(s)[2] for s in S_ALL])
tl = np.array([pc.frame(s)[1] for s in S_ALL])
fchk["travel_bearing_deg"] = {"min": r3(min(math.degrees(math.atan2(t[0], t[1])) % 360 for t in tl), 1),
                              "max": r3(max(math.degrees(math.atan2(t[0], t[1])) % 360 for t in tl), 1),
                              "what": "D's tangent along increasing s, degrees from north"}
fchk["left_normal_is_left"] = bool(np.allclose(nl[:, 0], -tl[:, 1]) and np.allclose(nl[:, 1], tl[:, 0]))
assert fchk["left_normal_is_left"]

# ------------------------------------------------------------------ the corridor's returns
tiles, epsg = SH.tile_list(TDIR)
to_utm = Transformer.from_crs(4326, epsg, always_xy=True)
to_ll = Transformer.from_crs(epsg, 4326, always_xy=True)
trk = SH.Track(LM / "data", to_utm)
assert abs(trk.origin["lon"] - origin["lon"]) < 1e-12 and abs(trk.origin["lat"] - origin["lat"]) < 1e-12
P = np.array([pc.point(s) for s in S_ALL])
ue, un = (np.asarray(v) for v in trk._utm(P[:, 0], P[:, 1]))
R = math.hypot(HALF_ACROSS, HALF_ALONG) + 0.3
ub = (ue.min() - R - 3, un.min() - R - 3, ue.max() + R + 3, un.max() + R + 3)
use = [t for t in tiles if t["maxs"][0] >= ub[0] and t["mins"][0] <= ub[2] and t["maxs"][1] >= ub[1] and t["mins"][1] <= ub[3]]
etree = cKDTree(np.c_[ue, un])
keep = {k: [] for k in ("E", "N", "elev", "cls", "wh", "last", "inten")}
tiles_rep = []
for t in use:
    tt = time.time()
    nk, cls_t = 0, {}
    for p in SH.chunks(t["path"], 1_000_000):
        X, Y = np.asarray(p.x), np.asarray(p.y)
        ii = np.flatnonzero((X >= ub[0]) & (X <= ub[2]) & (Y >= ub[1]) & (Y <= ub[3]))
        if not len(ii):
            continue
        d, _ = etree.query(np.c_[X[ii], Y[ii]], k=1, distance_upper_bound=R)
        ii = ii[np.isfinite(d)]
        if not len(ii):
            continue
        c = np.asarray(p.classification)[ii]
        for k_, v_ in zip(*np.unique(c, return_counts=True)):
            cls_t[int(k_)] = cls_t.get(int(k_), 0) + int(v_)
        keep["E"].append(X[ii]); keep["N"].append(Y[ii]); keep["elev"].append(np.asarray(p.z)[ii])
        keep["cls"].append(c); keep["wh"].append(np.asarray(p.withheld, bool)[ii])
        keep["last"].append(np.asarray(p.return_number)[ii] == np.asarray(p.number_of_returns)[ii])
        keep["inten"].append(np.asarray(p.intensity)[ii])
        nk += len(ii)
    tiles_rep.append({"file": t["file"], "bytes": t["bytes"], "points": t["points"], "md5": md5(t["path"]), "kept": nk,
                      "kept_by_class": cls_t, "seconds": round(time.time() - tt, 1)})
    log(f"{t['file']}: {nk:,} kept")
L = {k: np.concatenate(v) for k, v in keep.items()}
x, z = trk.to_local(L["E"], L["N"], to_ll)
L["x"], L["z"] = np.asarray(x, float), np.asarray(z, float)
rE, rN = (np.asarray(v) for v in trk._utm(L["x"][:5000], L["z"][:5000]))
fchk["projection_round_trip_max_m"] = r3(float(np.max(np.hypot(rE - L["E"][:5000], rN - L["N"][:5000]))), 4)
OK = ~L["wh"] & ~np.isin(L["cls"], NOISE)
GND = OK & (L["cls"] == 2)
LAST = OK & L["last"]
ptree = cKDTree(np.c_[L["x"], L["z"]])
log(f"corridor {len(L['E']):,} returns: class 2 {int(GND.sum()):,}, last {int(LAST.sum()):,}, withheld {int(L['wh'].sum())}")


# ------------------------------------------------------------------ the edge finder
def linfit(l, z, min_n):
    if len(l) >= min_n and np.ptp(l) > 0.2:
        c = np.polyfit(l, z, 1)
        return (float(c[0]), float(c[1]))
    if len(l):
        return (0.0, float(np.median(z)))
    return None


def ev(line, x):
    return line[0] * x + line[1]


def face_interval(l, high, high_inside):
    """the face between two neighbouring points with the fewest on the wrong side; high_inside: the high side is the
    lower u (a drop outward), else the higher u (a rise outward)"""
    o = np.argsort(l)
    l, high = l[o], high[o]
    n = len(l)
    hi_c = np.r_[0, np.cumsum(high)]
    lo_c = np.r_[0, np.cumsum(~high)]
    wrong = (lo_c + (hi_c[-1] - hi_c)) if high_inside else (hi_c + (lo_c[-1] - lo_c))
    best = int(wrong.min())
    ks = np.flatnonzero(wrong == best)
    k0, k1 = ks.min(), ks.max()
    lo = l[k0 - 1] if k0 > 0 else l[0] - 0.05
    hi = l[k1] if k1 < n else l[-1] + 0.05
    return 0.5 * (lo + hi), 0.5 * (hi - lo), best, n


def edge(l, z, inten, side):
    """one side's outer face (side +1 left, -1 right)"""
    u = side * l
    m = (u >= OUTER_FROM) & (u <= HALF_ACROSS)
    u, z, inten = u[m], z[m], inten[m]
    rec = {"n_window": int(len(u))}
    if len(u) < N_WIN:
        rec.update(verdict="unclear", type=None, reason="sparse")
        return rec
    nb = int(round((HALF_ACROSS - OUTER_FROM) / BIN))
    bi = np.clip(np.floor((u - OUTER_FROM) / BIN).astype(int), 0, nb - 1)
    bq = np.full(nb, np.nan)
    o = np.argsort(bi)
    bs, zs = bi[o], z[o]
    st = np.r_[0, np.flatnonzero(np.diff(bs)) + 1]
    for a_, b_ in zip(st, np.r_[st[1:], len(bs)]):
        bq[bs[a_]] = np.percentile(zs[a_:b_], OUT_Q)
    cen = OUTER_FROM + (np.arange(nb) + 0.5) * BIN
    fb = np.isfinite(bq)
    edges = OUTER_FROM + np.arange(nb + 1) * BIN
    k = int(round(W / BIN))
    kt = int(round(TREND_M / BIN))
    D = np.full(nb + 1, np.nan)
    for e in range(kt, nb + 1 - k):
        ti = np.arange(e - kt, e)
        ti = ti[fb[ti]]
        oi = np.arange(e, e + k)
        oi = oi[fb[oi]]
        if len(ti) >= TREND_MIN and len(oi) >= MIN_BINS:
            cf = np.polyfit(cen[ti], bq[ti], 1)
            D[e] = float(np.median(bq[oi] - np.polyval(cf, cen[oi])))
    fin = np.isfinite(D)
    cand = [e for e in np.flatnonzero(fin) if D[e] >= CURB_DET or D[e] <= -DROP_DET]
    if not cand:
        mx = float(np.nanmax(np.abs(D))) if fin.any() else None
        if mx is not None and mx < NONE_MAX:
            rec.update(verdict="none", type=None, reason=f"no rise or drop over {NONE_MAX} m from {OUTER_FROM} to {HALF_ACROSS} m out")
        else:
            rec.update(verdict="unclear", type=None, reason="no rise past %.2f m or drop past %.2f m%s" % (
                CURB_DET, DROP_DET, "" if mx is None else "; largest |D| %.3f" % mx))
        return rec
    road0 = float(np.median(bq[fb & (cen <= OUTER_FROM + 1.5)])) if (fb & (cen <= OUTER_FROM + 1.5)).sum() >= 5 else None

    def lines(x0):
        mr_ = fb & (cen >= x0 - ROAD_M) & (cen <= x0 - GUARD)
        mw_ = fb & (cen >= x0 + GUARD) & (cen <= x0 + WALK_M)
        return linfit(cen[mr_], bq[mr_], 4), linfit(cen[mw_], bq[mw_], 4), int(mw_.sum())

    def try_face(e0):
        r = {}
        rise = D[e0] > 0
        seg = D[e0:e0 + int(round(0.5 / BIN)) + 1]
        j = int(np.nanargmax(seg)) if rise else int(np.nanargmin(seg))
        x0 = float(edges[e0 + j])
        r["detector_m"] = r3(D[e0 + j])
        unc = wrong = nf = None
        for _it in range(2):
            rl, wl, nw = lines(x0)
            if rl is None or wl is None:
                r.update(verdict="unclear", type=None, reason="no returns on the road or the outer side")
                return r
            top = max(ev(rl, x0), ev(wl, x0)) + 0.10
            wf = (u >= x0 - FACE_WIN) & (u <= x0 + FACE_WIN) & (z <= top)
            if wf.sum() < 2:
                break
            hi = z[wf] > 0.5 * (ev(rl, u[wf]) + ev(wl, u[wf]))
            x0, unc, wrong, nf = (float(v) for v in face_interval(u[wf], hi, high_inside=not rise))
            wrong, nf = int(wrong), int(nf)
        rl, wl, nw = lines(x0)
        if rl is None or wl is None:
            r.update(verdict="unclear", type=None, reason="no returns on the road or the outer side")
            return r
        step = ev(wl, x0) - ev(rl, x0)
        ii_, io_ = (u >= x0 - INT_M) & (u < x0), (u > x0) & (u <= x0 + INT_M)
        r.update(face_u_m=r3(side * x0), unc_m=r3(unc), step_m=r3(step), outer_bins=nw, face_points=nf, face_wrong_side=wrong,
                 outer_slope=r3(wl[0], 4), road_slope=r3(rl[0], 4),
                 road_side_over_road_near_line_m=(None if road0 is None else r3(ev(rl, x0) - road0)),
                 intensity_inside=r3(np.median(inten[ii_]), 0) if ii_.any() else None,
                 intensity_outside=r3(np.median(inten[io_]), 0) if io_.any() else None)
        if road0 is not None and abs(ev(rl, x0) - road0) > ROAD_TOL:
            r.update(verdict="unclear", type=None, reason="the road side stands %+.2f m off the road near the line (canopy)" % (ev(rl, x0) - road0))
        elif nw < N_WALK_BINS:
            r.update(verdict="unclear", type=None, reason=f"{nw} bins on the outer side")
        elif rise and CURB_LO <= step <= CURB_HI:
            r.update(verdict="face", type="curb", reason="")
        elif rise and step > CURB_HI:
            r.update(verdict="face", type="edge (rise)", reason="a wall, bank or hedge where the asphalt ends")
        elif not rise and step <= -DROP_DET:
            r.update(verdict="face", type="edge (drop)", reason="the ground falls away past the asphalt")
        else:
            r.update(verdict="unclear", type=None, reason=f"step {step:+.3f} m ({'rise' if rise else 'drop'}) out of bounds")
        return r

    # the first candidate outward; if it gives no face, the next ones within CONT_M of it (a gutter's lip before its curb)
    first = None
    tried = []
    for e0 in cand:
        if tried and edges[e0] - edges[tried[0]] > CONT_M:
            break
        if tried and edges[e0] - edges[tried[-1]] < 0.3:
            continue
        tried.append(e0)
        r = try_face(e0)
        if first is None:
            first = r
        if r["verdict"] == "face":
            if len(tried) > 1:
                r["note"] = "the first candidate (%.2f m) gave no face: %s" % (side * edges[tried[0]], first.get("reason"))
            rec.update(r)
            return rec
    rec.update(first)
    return rec


def measure(s):
    (px, pz), t, n = pc.frame(s)
    ii = np.array(ptree.query_ball_point([px, pz], R), dtype=np.int64)
    dx, dz = L["x"][ii] - px, L["z"][ii] - pz
    al = dx * t[0] + dz * t[1]
    la = dx * n[0] + dz * n[1]
    w = (np.abs(al) <= HALF_ALONG) & (np.abs(la) <= HALF_ACROSS)
    ii, al, la = ii[w], al[w], la[w]
    g, ok, lr = GND[ii], OK[ii], LAST[ii]
    if g.sum() >= 30:
        zz, aa, ll = L["elev"][ii][g], al[g], la[g]
        b = np.floor(ll / 0.5).astype(int)
        res = zz.copy()
        for kb in np.unique(b):
            m = b == kb
            res[m] -= np.median(zz[m])
        c = np.polyfit(aa, res, 1)
        rr = res - np.polyval(c, aa)
        kk = np.abs(rr) <= max(0.05, 3 * 1.4826 * np.median(np.abs(rr)))
        grade, gsrc = float(np.polyfit(aa[kk], res[kk], 1)[0]), "class 2"
    else:
        grade, gsrc = (pc.num(s + 2.5, "y_3dep") - pc.num(s - 2.5, "y_3dep")) / 5.0, "y_3dep"
    zc = L["elev"][ii] - grade * al
    bl, br = pc.num(s, "left_m"), pc.num(s, "right_m")
    inten = L["inten"][ii].astype(float)
    left = edge(la[lr], zc[lr], inten[lr], +1)
    right = edge(la[lr], zc[lr], inten[lr], -1)
    row = {"s": s, "left": left, "right": right,
           "built": {"left_m": r3(bl, 2), "right_m": r3(br, 2), "middle_m": r3(0.5 * (bl + br), 3), "width_m": r3(bl - br, 2)},
           "counts": {"returns": int(ok.sum()), "last_returns": int(lr.sum()), "class_2": int(g.sum())}, "grade": {"along": r3(grade, 4), "from": gsrc}}
    if left["verdict"] == "face":
        row["left_minus_built_m"] = r3(left["face_u_m"] - bl)
    if right["verdict"] == "face":
        row["right_minus_built_m"] = r3(right["face_u_m"] - br)
    if left["verdict"] == "face" and right["verdict"] == "face":
        row["real_middle_m"] = r3(0.5 * (left["face_u_m"] + right["face_u_m"]))
        row["real_width_m"] = r3(left["face_u_m"] - right["face_u_m"])
        row["real_minus_built_middle_m"] = r3(row["real_middle_m"] - row["built"]["middle_m"])
        row["real_minus_built_width_m"] = r3(row["real_width_m"] - row["built"]["width_m"])
    road0 = lr & (np.abs(la) <= 0.5)
    row["road_at_line_minus_y3dep_m"] = r3(float(np.percentile(zc[road0], OUT_Q)) - float(origin["elev_m"]) - pc.num(s, "y_3dep")) if road0.sum() >= 5 else None
    return row


rows = {s: measure(s) for s in S_ALL}
log("stations measured", len(rows))
for s in S_ALL:
    r = rows[s]
    f = lambda e: "%-11s %s" % (e["type"] or e["verdict"], ("%+6.2f/%+.3f" % (e["face_u_m"], e["step_m"])) if e.get("face_u_m") is not None else "--")  # noqa: E731
    print(f"  {s:7.1f} L {f(r['left'])}  R {f(r['right'])}  built {r['built']['left_m']:+.2f}/{r['built']['right_m']:+.2f}"
          f"  real-built middle {r.get('real_minus_built_middle_m')}", flush=True)


# ------------------------------------------------------------------ summary
def bins_of(a, b):
    out, b0 = [], a
    while b0 <= b + 1e-6:
        sb = [s for s in S_ALL if b0 - 1e-6 <= s < b0 + BIN_SUM_M - 1e-6 and s <= b + 1e-6]
        if sb:
            out.append(sb)
        b0 += BIN_SUM_M
    return out


def runs(ss, pred):
    out, cur = [], None
    for s in ss:
        if pred(rows[s]):
            if cur and abs(s - cur[1] - 2.5) < 1e-6:
                cur[1] = s
            else:
                cur = [s, s]
                out.append(cur)
        else:
            cur = None
    return out


def types(ss, side):
    out = {}
    for s in ss:
        e = rows[s][side]
        k = e["type"] or e["verdict"]
        out[k] = out.get(k, 0) + 1
    return out


per = []
for a, b in RANGES:
    for sb in bins_of(a, b):
        both = [s for s in sb if rows[s].get("real_minus_built_middle_m") is not None]
        curbs = [s for s in both if rows[s]["left"]["type"] == "curb" and rows[s]["right"]["type"] == "curb"]
        e = {"s": [sb[0], sb[-1]], "stations": len(sb), "stations_with_both_faces": len(both),
             "real_minus_built_middle_m": rng([rows[s]["real_minus_built_middle_m"] for s in both]),
             "real_minus_built_middle_m_curbs_both_sides": rng([rows[s]["real_minus_built_middle_m"] for s in curbs]),
             "real_middle_m": rng([rows[s]["real_middle_m"] for s in both]),
             "built_middle_m": rng([rows[s]["built"]["middle_m"] for s in sb]),
             "real_minus_built_width_m": rng([rows[s]["real_minus_built_width_m"] for s in both]),
             "left_minus_built_m": rng([rows[s].get("left_minus_built_m") for s in sb]),
             "right_minus_built_m": rng([rows[s].get("right_minus_built_m") for s in sb]),
             "left_types": types(sb, "left"), "right_types": types(sb, "right")}
        iqr = (e["real_minus_built_middle_m"] or {}).get("iqr")
        if len(both) < MIN_BOTH:
            e["call"] = f"can't call: {len(both)} stations with both faces (wants {MIN_BOTH})"
        elif iqr is not None and iqr > MAX_IQR:
            e["call"] = f"can't call: the stations disagree (IQR {iqr:.2f} m over {MAX_IQR})"
        else:
            e["call"] = "ok"
        per.append(e)
cant = {"stations_without_both_faces": runs(S_ALL, lambda r: r.get("real_minus_built_middle_m") is None),
        "left_side": runs(S_ALL, lambda r: r["left"]["verdict"] != "face"),
        "right_side": runs(S_ALL, lambda r: r["right"]["verdict"] != "face")}
both_all = [s for s in S_ALL if rows[s].get("real_minus_built_middle_m") is not None]
v3 = [rows[s]["road_at_line_minus_y3dep_m"] for s in S_ALL if rows[s]["road_at_line_minus_y3dep_m"] is not None]
fchk["road_at_line_minus_y3dep_m"] = {"what": "the lidar road within 0.5 m of D's line (last returns, OUT_Q percentile, grade out) minus D's "
                                      "y_3dep, engine y", "median": r3(np.median(v3)), "n": len(v3)}
summary = {
    "stations": len(S_ALL), "stations_with_both_faces": len(both_all),
    "left_types": types(S_ALL, "left"), "right_types": types(S_ALL, "right"),
    "per_range": {f"s{a:g}_{b:g}": {"real_minus_built_middle_m": rng([rows[s]["real_minus_built_middle_m"] for s in both_all if a <= s <= b]),
                                    "real_minus_built_width_m": rng([rows[s]["real_minus_built_width_m"] for s in both_all if a <= s <= b]),
                                    "left_minus_built_m": rng([rows[s].get("left_minus_built_m") for s in S_ALL if a <= s <= b]),
                                    "right_minus_built_m": rng([rows[s].get("right_minus_built_m") for s in S_ALL if a <= s <= b])}
                  for a, b in RANGES},
    "per_25m": per,
    "cant_call": cant,
    "curb_step_m": {"left": rng([rows[s]["left"]["step_m"] for s in S_ALL if rows[s]["left"].get("type") == "curb"]),
                    "right": rng([rows[s]["right"]["step_m"] for s in S_ALL if rows[s]["right"].get("type") == "curb"])},
}
settings = {k: globals()[k] for k in ("RANGES", "BIN_SUM_M", "HALF_ALONG", "HALF_ACROSS", "OUTER_FROM", "BIN", "W", "MIN_BINS",
                                      "OUT_Q", "CURB_DET", "DROP_DET", "NONE_MAX", "CURB_LO", "CURB_HI", "GUARD", "ROAD_M",
                                      "WALK_M", "FACE_WIN", "N_WIN", "N_WALK_BINS", "TREND_M", "TREND_MIN", "INT_M",
                                      "ROAD_TOL", "CONT_M", "MIN_BOTH", "MAX_IQR")}
inputs = {str(p.relative_to(AIR)): md5(p) for p in (AIR / "tools" / "expansion_pieces.py", LM / "data" / "expansion.north.json",
                                                   LM / "data" / "centerline.local.json")}
inputs["lm-shrub tool shrub_heights.py"] = md5(Path(SH.__file__))
out = {
    "_doc": "Jackson Dr north (Lake Murray piece D): the road's two outer edges per station off the USGS 2024 lidar "
            "(jackson_curbs_g10.py; the method is its docstring). u = metres off D's line, + = left of D's travel along "
            "increasing s (J4 -> J5). left / right: verdict face / none / unclear; type curb, edge (rise) or edge (drop); "
            "face_u_m, unc_m (half the interval between the neighbouring points the face lies between), step_m (outer - "
            "road at the face; negative for a drop). built = D's own row (left_m, right_m; middle = their mean). "
            "real_middle_m = the mean of the two faces; real_minus_built_middle_m its difference. Settings marked "
            "[invented] in the script are the method's choices.",
    "status": "measured", "tool": "jackson_curbs_g10.py (G10 job lm-jackson-curbs-20261123)", "date": time.strftime("%Y-%m-%d"),
    "source": {"project": "USGS_LPC_CA_SanDiegoCo_D24", "epsg": epsg, "flown": "2024-11 (lm-shrub tiles.json)", "tiles_read": tiles_rep},
    "inputs_md5": inputs,
    "frame": {"piece": "D jackson_north (tools/expansion_pieces.Piece.frame)", "origin": origin,
              "projection": "shrub_heights.Track.to_local: pyproj EPSG %d -> 4326 ('%s', stated accuracy %s m), then the "
                            "WGS84 metres-per-degree series at the origin" % (epsg, to_ll.description, to_ll.accuracy),
              "checks": fchk},
    "settings": settings, "summary": summary, "stations": [rows[s] for s in S_ALL]}


def dump(o, **kw):
    return json.dumps(o, ensure_ascii=False, default=lambda v: v.tolist() if hasattr(v, "tolist") else str(v), **kw)


head = {k: v for k, v in out.items() if k != "stations"}
txt = dump(head, indent=1)[:-2] + ',\n "stations": [\n' + ",\n".join("  " + dump(r, separators=(",", ":")) for r in out["stations"]) + "\n ]\n}\n"
json.loads(txt)
OUTP.parent.mkdir(parents=True, exist_ok=True)
OUTP.write_text(txt, encoding="utf-8")
log("written", OUTP)
