"""Mission Gorge Rd's raised median (Lake Murray piece C): the island's two faces read off the USGS 2024 lidar, station
by station, as an independent, colour-free check of the PC's NAIP readings in this folder (README.md, faces_md.py).
G10 job lm-mg-median-lidar-20261123. Reads only; downloads nothing. Run under nice -n 19 ionice -c3, with -I.

    python -I mg_median_faces_g10.py <tiles dir> <lm tool dir> <airoso dir> <out dir> [--reuse] [--full]

  (default)      s 40-250 and s 980-1215 with check stations -> mg_median_faces.lidar.g10.json
  --full         every station from s 225 to MD13b's end, per 50 m against the declared band, with flags
                 -> mg_median_faces_full.lidar.g10.json

  <tiles dir>    USGS_LPC_CA_SanDiegoCo_D24_*.laz (EPSG read off each header; shrub_heights.tile_list)
  <lm tool dir>  the folder holding the lm-shrub tool, shrub_heights.py (its projection, tile list and LAZ reader)
  <airoso dir>   a checkout (or git archive) of this repository: tools/expansion_pieces.py and Lake Murray's data/ and
                 source/expansion/mg_median/ are read from it
  <out dir>      the JSON; work/corridor.npz or work/corridor_full.npz (the returns read, kept for --reuse)
Each of the four may instead come from the environment: MG_TILES, MG_LM_TOOL, MG_AIROSO, MG_OUT.

FRAME. Piece C's own frame, tools/expansion_pieces.Piece.frame (imported, not copied): the station point by linear
interpolation of pieces[C].stations, the tangent the chord over +-2.5 m, the left normal (-t_z, t_x). Offsets are metres
off piece C's line, + = LEFT of J3 -> J4 travel = north-west (the convention of faces_md.py and fix_mg_median.py).
Lidar E, N (NAD83(2011) / UTM 11N) -> local x east, z north by shrub_heights.Track.to_local (pyproj EPSG 6340 -> 4326,
then the WGS84 metres-per-degree series at data/expansion.north.json's frame.origin, which is centerline.local.json's).

PER STATION (every 2.5 m), the returns within +-HALF_ALONG along the tangent and +-HALF_ACROSS across it:
  sets     G = class 2 (ground). A = every return not withheld and not noise (ASPRS 7 / 18), kept only within
           A_LO..A_HI of a TIN of the corridor's class-2 returns (takes out cars and canopy; keeps a 0.1-0.3 m island).
  grade    the along-tangent slope, off G (each 0.5 m lateral bin's median removed, one least-squares slope), taken out
           of every height (the window is 2.5 m long on a road that climbs up to 6 %).
  bins     medians per BIN_A (A) / BIN_G (G) across.
  coarse   the step detector on the bins: D(x) = median of the bins in (x, x + W] minus in [x - W, x), after a
           trimmed straight line across the whole section is taken out (the road's cross-fall). Face candidates are
           D's local extremes past DET_MIN: a rise (right face b) pairs with the first drop (left face a) at least
           MIN_W further left; the pair with the largest min(D(b), -D(a)) is the island; searched within |x| <= SEARCH_M.
  faces    on the points: a straight road line on each side (GUARD..ROAD_M outside the face) and a top line (the
           inside, GUARD in from each face); a point near a face is "high" when it stands over the halfway height
           between road and top there. The face is put where the fewest points fall on the wrong side; every such
           position between two neighbouring points is kept, and the face is the middle of that interval, its
           uncertainty half the interval (the point spacing across the face). One refit of the lines on the refined
           faces gives the steps (top - road at each face) and the top over the mean road (top median minus the mean
           of the two road lines at their faces).
  verdict  island: the top over the mean road in STEP_LO..STEP_HI, each face's own step in STEP_SIDE_MIN..STEP_HI,
           and at least N_TOP returns on the top; none: no pair, and no |D| >= NONE_MAX anywhere in the search (an
           opening); unclear: anything else (sparse, one face only, out of bounds).
  which    A's reading, unless vegetation sits on the top (VEG_N or more returns VEG_H over the class-2 TIN between the
           faces): then G's alone, and where G shows no plateau there the station is unclear. Where A finds no clean
           plateau and G does, G's. (D24's class 2 holds no return on most of the narrow tops: see the summary.)
  outer    the road's two outer curbs, on the section widened to +-HALF_OUTER: per side, every non-noise return, per
           0.10 m bin its OUT_Q percentile, a trimmed cross-fall line out; the first rise outward past OUTER_FROM of at
           least CURB_DET, refined on the points like an island face (canopy and car returns over the two lines left
           out). curb: step CURB_LO..CURB_HI; edge: a rise over CURB_HI (a wall, bank or hedge where the pavement ends);
           none: no rise (a mouth); unclear: the rest. The real road's middle = the mean of the two faces (curb or edge);
           lane room = outer face to island face.
Every setting below marked [invented] is the method's choice, not a measurement. Numpy, scipy, laspy (lazrs), pyproj.
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
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay, cKDTree

HALF_ALONG = 1.25           # [invented] (the request) +- along the tangent
HALF_ACROSS = 12.0          # the request: +-12 m about piece C's line
BIN_A, BIN_G = 0.10, 0.25   # the request's 0.10-0.25 m bins: A is dense enough for 0.10, G (~3 returns per m2) is not
W_A, W_G = 0.6, 0.75        # [invented] the detector's half-window
MIN_BINS_A, MIN_BINS_G = 3, 2   # [invented] non-empty bins needed each side of x for D(x)
DET_MIN = 0.05              # [invented] a step the detector takes as a face candidate, m (0.06 on the first run)
NONE_MAX = 0.05             # [invented] no |D| this big within the search: no plateau (an opening)
SEARCH_M = 8.0              # [invented] faces searched within this of piece C's line
MIN_W = 0.30                # [invented] narrowest island taken
GUARD = 0.15                # [invented] the lines keep this far off a face
ROAD_M = 2.0                # [invented] the road lines reach this far outside each face
FACE_WIN = 0.5              # [invented] points this close to a coarse face decide it
STEP_LO, STEP_HI = 0.10, 0.30   # [invented] (the request) a plateau 0.10-0.30 m over the road on both sides
STEP_SIDE_MIN = 0.05        # [invented] each face's own step at least this. The first run held each side to STEP_LO and
                            # read 'unclear' at 30 of 85 J3-end stations (mostly where the north-west face is sharp but stands
                            # only 0.05-0.10 m: the top leans toward it): the top over the MEAN road keeps STEP_LO..STEP_HI, and
                            # every station says whether both sides also clear STEP_LO (both_steps_ge_step_lo)
N_TOP_A, N_TOP_G = 8, 3     # [invented] returns needed on the top
N_WIN_A, N_WIN_G = 150, 30  # [invented] returns needed in the central +-SEARCH_M of the window
A_LO, A_HI = -0.25, 0.40    # [invented] set A's band about the class-2 TIN
VEG_H, VEG_N = 0.50, 5      # [invented] vegetation on the top: VEG_N returns over VEG_H above the class-2 TIN
NOISE = (7, 18)             # ASPRS low / high noise
HALF_OUTER = 22.0           # the outer curbs: the section widened to +-22 m (the request; the plan's edges sit 13-17 m out)
OUTER_FROM = 7.0            # [invented] an outer curb is searched from 7 m off the line outward (past every island face)
CURB_DET = 0.05             # [invented] the first rise outward at least this big is the curb candidate
CURB_LO, CURB_HI = 0.05, 0.35   # [invented] a curb: its step (walk - road at the face) within these; over CURB_HI an "edge"
WALK_M = 1.2                # [invented] the walk / verge line reaches this far past the face
N_WALK_BINS = 4             # [invented] 0.10 m bins with a return needed on the walk side
OUT_Q = 20                  # [invented] the outer profile's statistic per bin: this percentile of the returns
ROAD_FIT_IN = 2.0           # [invented] the outer search's cross-fall line: the road from OUTER_FROM to the plan's edge - 2 m
MAIN = [(40.0, 250.0), (980.0, 1215.0)]                 # the request
CHECK = [(25.0, 37.5), (252.5, 300.0), (930.0, 977.5), (1217.5, 1260.0)]   # MD11's start (the J3 pad cuts at s 24.74);
                                                        # MD13 past the J3 range; full-width MD13 beside the crossing stretch
REF = [(930.0, 985.0), (1215.0, 1260.0)]                # faces_md.py REF: "the island fills its band here"
STRIP_A, STRIP_B = (1012.5, 1077.5), (1127.5, 1192.5)   # the PC's 24 and 26 stations (mg_median_correction.json)
GAP_PHOTO = (1087.5, 1117.5)
PHOTO_BIAS_W, PHOTO_BIAS_C = 0.30, 0.49                 # what fix_mg_median.py added back to the photo's numbers
ENGINE_DY = 100.8
FULL_FROM = 225.0           # --full: every station from MD13's first island station (this job's s 40-250 read) to MD13b's end
BIN_SUM_M = 50.0            # --full: the summary's bins (the request)
FLAG_M = 0.30               # --full: a width / middle change worth flagging (the request)
SMOOTH_HALF_M = 5.0         # [invented] --full: running median over island stations within +-5 m ...
CHANGE_OVER_M = 10.0        # [invented] ... compared 10 m apart: |w(s + 5) - w(s - 5)| > FLAG_M flags s
MIN_UNCLEAR_RUN = 3         # [invented] --full: unclear runs this long (7.5 m) are flagged
MIN_BOTH = 5                # [invented] a bin's "reads" wants this many stations with the island and both outer faces


def arg(i, env):
    if len(sys.argv) > i and not sys.argv[i].startswith("--"):
        return Path(sys.argv[i])
    if os.environ.get(env):
        return Path(os.environ[env])
    raise SystemExit(__doc__)


TDIR, TOOL, AIR, OUT = arg(1, "MG_TILES"), arg(2, "MG_LM_TOOL"), arg(3, "MG_AIROSO"), arg(4, "MG_OUT")
REUSE = "--reuse" in sys.argv
FULL = "--full" in sys.argv
sys.path.insert(0, str(TOOL))
sys.path.insert(0, str(AIR / "tools"))
import shrub_heights as SH  # noqa: E402  the lm-shrub tool: tile_list, chunks, Track (projection)
import expansion_pieces as ep  # noqa: E402  piece frame

LM = AIR / "tracks" / "san-diego-lake-murray"
MG = LM / "source" / "expansion" / "mg_median"
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


def med(v):
    v = [x for x in v if x is not None and math.isfinite(x)]
    return float(np.median(v)) if v else None


def stations(ranges):
    out = []
    for a, b in ranges:
        out += [round(a + 2.5 * k, 1) for k in range(int(round((b - a) / 2.5)) + 1)]
    return out


# ------------------------------------------------------------------ the piece, the islands as declared, the photo
doc, pieces = ep.load(LM / "data" / "expansion.north.json")
pc = pieces["C"]
assert pc.rec["name"] == "mission_gorge"
origin = doc["frame"]["origin"]
corr = json.loads((MG / "mg_median_correction.json").read_text(encoding="utf-8"))
declared0 = {float(r["s"]): r for r in corr["rows"]}       # [0] = as declared, [1] = the PC's fit
_fp = json.loads((MG / "md13_faces_s960-1240.json").read_text(encoding="utf-8"))
faces_photo = {float(r["s"]): r for r in _fp["stations"]}
PHOTO_CHECK = _fp["check_on_the_reference_stretches"]
gaps_photo = {float(r["s"]): r for r in json.loads((MG / "md13_gaps.json").read_text(encoding="utf-8"))["rows"]}
medians = {m["id"]: m for m in doc["medians"] if m.get("piece") == "C"}


def declared(s):
    """(as declared: w, off, type), (now in the data: w, off, type)"""
    now = (pc.num(s, "median_w_m"), pc.num(s, "median_off_m"), pc.near(s, "median_type"))
    d = declared0.get(s)
    if d:
        return (d["median_w_m"][0], d["median_off_m"][0], d["median_type"][0]), now
    return now, now


def island_of(s):
    for k, m in medians.items():
        if m["s_from"] - 1e-6 <= s <= m["s_to"] + 1e-6:
            return k
    return None


# ------------------------------------------------------------------ frame checks (no lidar)
S_ALL = (stations([(FULL_FROM, float(medians["MD13b"]["s_to"]))]) if FULL
         else sorted(set(stations(MAIN) + stations(CHECK) + stations(REF))))
fchk = {}
nl = np.array([pc.frame(s)[2] for s in S_ALL])
fchk["left_normal_points_north_west"] = bool(((nl[:, 0] < 0) & (nl[:, 1] > 0)).all())
assert fchk["left_normal_points_north_west"], "piece C's left normal is not north-west everywhere"
# the rings: side A (the first half) must lie at off + w / 2, side B at off - w / 2, in this frame
ring_dev, ring_n = [], 0
for k in ("MD11", "MD13", "MD13b"):
    m = medians[k]
    n = len(m["polygon_xz"]) // 2
    for i in range(n):
        s = m["s_from"] + 2.5 * i
        if s - m["s_from"] < 6.5 or m["s_to"] - s < 6.5:      # the noses taper (author_expansion NOSE_M 6)
            continue
        (px, pz), _t, nn = pc.frame(s)
        a, b = m["polygon_xz"][i], m["polygon_xz"][2 * n - 1 - i]
        la = (a[0] - px) * nn[0] + (a[1] - pz) * nn[1]
        lb = (b[0] - px) * nn[0] + (b[1] - pz) * nn[1]
        w, o = pc.num(s, "median_w_m"), pc.num(s, "median_off_m")
        ring_dev.append(max(abs(la - (o + w / 2)), abs(lb - (o - w / 2))))
        ring_n += 1
fchk["rings_side_a_left"] = {"stations": ring_n, "max_dev_m": r3(max(ring_dev)), "what": "MD11 / MD13 / MD13b rings: side A "
                             "(the first half of polygon_xz) at median_off_m + w / 2, side B at - w / 2, in this frame (noses left out)"}
assert max(ring_dev) < 0.02, ring_dev

# ------------------------------------------------------------------ the corridor's returns (read once)
tiles, epsg = SH.tile_list(TDIR)
to_utm = Transformer.from_crs(4326, epsg, always_xy=True)
to_ll = Transformer.from_crs(epsg, 4326, always_xy=True)
trk = SH.Track(LM / "data", to_utm)
assert abs(trk.origin["lon"] - origin["lon"]) < 1e-12 and abs(trk.origin["lat"] - origin["lat"]) < 1e-12
P = np.array([pc.point(s) for s in S_ALL])
ue, un = (np.asarray(v) for v in trk._utm(P[:, 0], P[:, 1]))
R = math.hypot(HALF_OUTER, HALF_ALONG) + 0.3
ub = (ue.min() - R - 3, un.min() - R - 3, ue.max() + R + 3, un.max() + R + 3)
use = [t for t in tiles if t["maxs"][0] >= ub[0] and t["mins"][0] <= ub[2] and t["maxs"][1] >= ub[1] and t["mins"][1] <= ub[3]]
work = OUT / "work"
work.mkdir(parents=True, exist_ok=True)
cpath = work / ("corridor_full.npz" if FULL else "corridor.npz")
TREAD = work / ("tiles_read_full.json" if FULL else "tiles_read.json")
tiles_rep = []
if REUSE and cpath.exists():
    L = dict(np.load(cpath))
    tiles_rep = json.loads(TREAD.read_text())
    log("corridor reused", len(L["E"]))
else:
    etree = cKDTree(np.c_[ue, un])
    keep = {k: [] for k in ("E", "N", "elev", "cls", "rn", "nr", "wh")}
    for t in use:
        tt = time.time()
        nk = 0
        cls_t = {}
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
            keep["cls"].append(c); keep["rn"].append(np.asarray(p.return_number)[ii])
            keep["nr"].append(np.asarray(p.number_of_returns)[ii]); keep["wh"].append(np.asarray(p.withheld, bool)[ii])
            nk += len(ii)
        tiles_rep.append({"file": t["file"], "bytes": t["bytes"], "points": t["points"], "md5": md5(t["path"]),
                          "kept": nk, "kept_by_class": cls_t, "seconds": round(time.time() - tt, 1)})
        log(f"{t['file']}: {nk:,} kept")
    L = {k: np.concatenate(v) for k, v in keep.items()}
    x, z = trk.to_local(L["E"], L["N"], to_ll)
    L["x"], L["z"] = np.asarray(x, float), np.asarray(z, float)
    np.savez_compressed(cpath, **L)
    TREAD.write_text(json.dumps(tiles_rep, indent=1))
# the projection round trip on the corridor (E, N -> x, z -> E, N)
rE, rN = (np.asarray(v) for v in trk._utm(L["x"][:5000], L["z"][:5000]))
fchk["projection_round_trip_max_m"] = r3(float(np.max(np.hypot(rE - L["E"][:5000], rN - L["N"][:5000]))), 4)
OK = ~L["wh"] & ~np.isin(L["cls"], NOISE)
GND = OK & (L["cls"] == 2)
gx = np.c_[L["x"][GND], L["z"][GND]]
tin = LinearNDInterpolator(Delaunay(gx), L["elev"][GND])
L["h_tin"] = (L["elev"] - tin(L["x"], L["z"])).astype(float)
SETA = OK & (L["h_tin"] >= A_LO) & (L["h_tin"] <= A_HI)
ptree = cKDTree(np.c_[L["x"], L["z"]])
log(f"corridor {len(L['E']):,} returns: class 2 {GND.sum():,}, set A {SETA.sum():,}, withheld {int(L['wh'].sum())}, "
    f"noise {int(np.isin(L['cls'], NOISE).sum())}")


# ------------------------------------------------------------------ the island finder
def linfit(l, z, min_n):
    if len(l) >= min_n and np.ptp(l) > 0.2:
        c = np.polyfit(l, z, 1)
        return (float(c[0]), float(c[1]))
    if len(l):
        return (0.0, float(np.median(z)))
    return None


def ev(line, x):
    return line[0] * x + line[1]


def trimmed_line(l, z):
    k = np.ones(len(l), bool)
    c = np.polyfit(l, z, 1)
    for _ in range(5):
        res = z - np.polyval(c, l)
        mad = np.median(np.abs(res[k] - np.median(res[k])))
        k = np.abs(res) <= max(0.05, 3.0 * 1.4826 * mad)
        if k.sum() < 3:
            break
        c = np.polyfit(l[k], z[k], 1)
    return c


def face_interval(l, high, top_low_side):
    """the face between two neighbouring points with the fewest on the wrong side; top_low_side: the top lies at lower l"""
    o = np.argsort(l)
    l, high = l[o], high[o]
    n = len(l)
    # split after k points (k = 0..n): left part l[:k], right part l[k:]
    hi_c = np.r_[0, np.cumsum(high)]
    lo_c = np.r_[0, np.cumsum(~high)]
    if top_low_side:    # high should be on the left (lower l)
        wrong = lo_c + (hi_c[-1] - hi_c)
    else:               # high on the right
        wrong = hi_c + (lo_c[-1] - lo_c)
    best = int(wrong.min())
    ks = np.flatnonzero(wrong == best)
    k0, k1 = ks.min(), ks.max()
    lo = l[k0 - 1] if k0 > 0 else l[0] - 0.05
    hi = l[k1] if k1 < n else l[-1] + 0.05
    return 0.5 * (lo + hi), 0.5 * (hi - lo), best, n


def find(l, z, binw, W, min_bins, n_top, n_win):
    """the island in one return set: l lateral (+ left), z height (grade out). -> dict"""
    rec = {"n_window": int(len(l)), "n_central": int((np.abs(l) <= SEARCH_M).sum())}
    if rec["n_central"] < n_win:
        rec.update(verdict="unclear", reason="sparse")
        return rec
    c = trimmed_line(l, z)
    res = z - np.polyval(c, l)
    nb = int(round(2 * HALF_ACROSS / binw))
    bi = np.clip(np.floor((l + HALF_ACROSS) / binw).astype(int), 0, nb - 1)
    bm = np.full(nb, np.nan)
    o = np.argsort(bi)
    bs, rs = bi[o], res[o]
    st = np.r_[0, np.flatnonzero(np.diff(bs)) + 1]
    for a_, b_ in zip(st, np.r_[st[1:], len(bs)]):
        bm[bs[a_]] = np.median(rs[a_:b_])
    centres = -HALF_ACROSS + (np.arange(nb) + 0.5) * binw
    rec["profile_bins"] = bm
    # D at bin edges
    edges = -HALF_ACROSS + np.arange(nb + 1) * binw
    k = int(round(W / binw))
    D = np.full(nb + 1, np.nan)
    for e in range(k, nb + 1 - k):
        if abs(edges[e]) > SEARCH_M:
            continue
        lft, rgt = bm[e - k:e], bm[e:e + k]
        lft, rgt = lft[np.isfinite(lft)], rgt[np.isfinite(rgt)]
        if len(lft) >= min_bins and len(rgt) >= min_bins:
            D[e] = np.median(rgt) - np.median(lft)
    fin = np.isfinite(D)
    rec["max_abs_step_detector_m"] = r3(np.nanmax(np.abs(D)) if fin.any() else None)
    span = int(round(0.3 / binw))
    rights = [e for e in np.flatnonzero(fin) if D[e] >= DET_MIN and D[e] >= np.nanmax(D[max(0, e - span):e + span + 1])]
    lefts = [e for e in np.flatnonzero(fin) if D[e] <= -DET_MIN and D[e] <= np.nanmin(D[max(0, e - span):e + span + 1])]
    # each rise pairs with the first drop after it (at least MIN_W on); the pair with the largest min(D(b), -D(a)) wins
    pairs = []
    for b in rights:
        nxt = [a for a in lefts if edges[a] - edges[b] >= MIN_W - 1e-9]
        if nxt:
            a = min(nxt)
            pairs.append((min(D[b], -D[a]), b, a))
    pairs.sort(reverse=True)
    best = pairs[0] if pairs else None
    if best is not None:
        oth = [p for p in pairs[1:] if edges[p[2]] < edges[best[1]] or edges[p[1]] > edges[best[2]]]
        rec["other_raised"] = ([{"right_m": r3(edges[p[1]], 2), "left_m": r3(edges[p[2]], 2), "score_m": r3(p[0])} for p in oth[:2]]
                               or None)
    if best is None:
        mx = rec["max_abs_step_detector_m"]
        if mx is not None and mx < NONE_MAX:
            rec.update(verdict="none", reason=f"no step over {NONE_MAX} m within {SEARCH_M} m of the line")
        else:
            e = int(np.nanargmax(np.abs(D))) if fin.any() else None
            rec.update(verdict="unclear", reason="no raised pair" + (f"; strongest step {D[e]:+.3f} m at {edges[e]:+.2f}" if e is not None else ""))
        return rec
    b_x, a_x = float(edges[best[1]]), float(edges[best[2]])

    def lines(b_x, a_x):
        mr = (l >= b_x - ROAD_M) & (l <= b_x - GUARD)
        ml = (l >= a_x + GUARD) & (l <= a_x + ROAD_M)
        g = GUARD if a_x - b_x > 4 * GUARD else 0.25 * (a_x - b_x)
        mt = (l >= b_x + g) & (l <= a_x - g)
        return linfit(l[mr], z[mr], 5), linfit(l[mt], z[mt], 5 if a_x - b_x > 0.6 else 10 ** 9), linfit(l[ml], z[ml], 5), mt

    ub_ = ua_ = wrong_b = wrong_a = nfb = nfa = None
    for _it in range(2):
        rR, tp, rL, mt = lines(b_x, a_x)
        if rR is None or tp is None or rL is None:
            rec.update(verdict="unclear", reason="no returns on a road side or on the top")
            return rec
        mid = 0.5 * (a_x + b_x)
        wb = (l >= b_x - FACE_WIN) & (l <= min(b_x + FACE_WIN, mid))
        wa = (l >= max(a_x - FACE_WIN, mid)) & (l <= a_x + FACE_WIN)
        hb = z[wb] > 0.5 * (ev(rR, l[wb]) + ev(tp, l[wb]))
        ha = z[wa] > 0.5 * (ev(rL, l[wa]) + ev(tp, l[wa]))
        if wb.sum() < 2 or wa.sum() < 2:
            break
        b_x, ub_, wrong_b, nfb = (float(v) for v in face_interval(l[wb], hb, top_low_side=False))
        a_x, ua_, wrong_a, nfa = (float(v) for v in face_interval(l[wa], ha, top_low_side=True))
        wrong_b, nfb, wrong_a, nfa = int(wrong_b), int(nfb), int(wrong_a), int(nfa)
        if a_x - b_x < 0.05:
            rec.update(verdict="unclear", reason="faces cross on refinement")
            return rec
    rR, tp, rL, mt = lines(b_x, a_x)
    if rR is None or tp is None or rL is None:
        rec.update(verdict="unclear", reason="no returns on a road side or on the top")
        return rec
    h_r = ev(tp, b_x) - ev(rR, b_x)
    h_l = ev(tp, a_x) - ev(rL, a_x)
    top_med = float(np.median(z[mt])) if mt.any() else float("nan")
    top_over = top_med - 0.5 * (ev(rR, b_x) + ev(rL, a_x))
    rec.update(left_m=r3(a_x), right_m=r3(b_x), left_unc_m=r3(ua_), right_unc_m=r3(ub_), width_m=r3(a_x - b_x),
               middle_m=r3(0.5 * (a_x + b_x)), step_left_m=r3(h_l), step_right_m=r3(h_r), top_over_road_m=r3(top_over),
               n_top=int(mt.sum()), top_slope=r3(tp[0], 4), road_left_slope=r3(rL[0], 4), road_right_slope=r3(rR[0], 4),
               face_points={"left": nfa, "right": nfb}, face_wrong_side={"left": wrong_a, "right": wrong_b},
               detector={"right": r3(D[best[1]]), "left": r3(D[best[2]])})
    rec["both_steps_ge_step_lo"] = bool(h_l >= STEP_LO and h_r >= STEP_LO)
    if rec["n_top"] < n_top:
        rec.update(verdict="unclear", reason=f"{rec['n_top']} returns on the top")
    elif (STEP_LO <= top_over <= STEP_HI and STEP_SIDE_MIN <= h_l <= STEP_HI and STEP_SIDE_MIN <= h_r <= STEP_HI):
        rec.update(verdict="island", reason="")
    else:
        rec.update(verdict="unclear", reason=f"step out of bounds: top {top_over:+.3f} (wants {STEP_LO}-{STEP_HI}), "
                                             f"right {h_r:+.3f}, left {h_l:+.3f} (want {STEP_SIDE_MIN}-{STEP_HI})")
    return rec


def outer_face(l, z, side, plan_edge):
    """the road's outer curb face on one side (side +1 left, -1 right): the first rise outward past OUTER_FROM. The
    returns are every non-noise one (no TIN band: past the curb the class-2 TIN is no reference, the walk often holds no
    class 2 and the ground behind it drops or climbs); per 0.10 m bin their OUT_Q percentile, so canopy over the verge
    and the odd car don't lift it. The face is refined on the points as an island face is."""
    u = side * l
    m = (u >= OUTER_FROM) & (u <= HALF_OUTER)
    u, z = u[m], z[m]
    rec = {"n_window": int(len(u))}
    if len(u) < N_WIN_A:
        rec.update(verdict="unclear", reason="sparse")
        return rec
    nb = int(round((HALF_OUTER - OUTER_FROM) / BIN_A))
    bi = np.clip(np.floor((u - OUTER_FROM) / BIN_A).astype(int), 0, nb - 1)
    bq = np.full(nb, np.nan)
    o = np.argsort(bi)
    bs, zs = bi[o], z[o]
    st = np.r_[0, np.flatnonzero(np.diff(bs)) + 1]
    for a_, b_ in zip(st, np.r_[st[1:], len(bs)]):
        bq[bs[a_]] = np.percentile(zs[a_:b_], OUT_Q)
    cen = OUTER_FROM + (np.arange(nb) + 0.5) * BIN_A
    fb = np.isfinite(bq)
    mr = fb & (cen <= max(OUTER_FROM + 4.0, abs(plan_edge) - ROAD_FIT_IN))
    if mr.sum() < 10:
        rec.update(verdict="unclear", reason="sparse road")
        return rec
    c = trimmed_line(cen[mr], bq[mr])
    res = bq - np.polyval(c, cen)
    edges = OUTER_FROM + np.arange(nb + 1) * BIN_A
    k = int(round(W_A / BIN_A))
    D = np.full(nb + 1, np.nan)
    for e in range(k, nb + 1 - k):
        lft, rgt = res[e - k:e], res[e:e + k]
        lft, rgt = lft[np.isfinite(lft)], rgt[np.isfinite(rgt)]
        if len(lft) >= MIN_BINS_A and len(rgt) >= MIN_BINS_A:
            D[e] = np.median(rgt) - np.median(lft)
    fin = np.isfinite(D)
    first = [e for e in np.flatnonzero(fin) if D[e] >= CURB_DET]
    if not first:
        mx = float(np.nanmax(D)) if fin.any() else None
        if mx is not None and mx < NONE_MAX:
            rec.update(verdict="none", reason=f"no rise over {NONE_MAX} m from {OUTER_FROM} to {HALF_OUTER} m out")
        else:
            rec.update(verdict="unclear", reason="no rise past %.2f m%s" % (CURB_DET, "" if mx is None else "; strongest %+.3f" % mx))
        return rec
    e0 = first[0]
    seg = D[e0:e0 + int(round(0.5 / BIN_A)) + 1]
    x0 = float(edges[e0 + int(np.nanargmax(seg))])
    rec["detector_m"] = r3(D[e0 + int(np.nanargmax(seg))])

    def lines(x0):
        mr_ = fb & (cen >= x0 - ROAD_M) & (cen <= x0 - GUARD)
        mw_ = fb & (cen >= x0 + GUARD) & (cen <= x0 + WALK_M)
        return linfit(cen[mr_], bq[mr_], 4), linfit(cen[mw_], bq[mw_], 4), int(mw_.sum())

    unc = wrong = nf = None
    for _it in range(2):
        rl, wl, nw = lines(x0)
        if rl is None or wl is None:
            rec.update(verdict="unclear", reason="no returns on the road or the walk side")
            return rec
        top = max(ev(rl, x0), ev(wl, x0)) + 0.10
        wf = (u >= x0 - FACE_WIN) & (u <= x0 + FACE_WIN) & (z <= top)      # canopy / car returns out of the face
        if wf.sum() < 2:
            break
        hi = z[wf] > 0.5 * (ev(rl, u[wf]) + ev(wl, u[wf]))
        x0, unc, wrong, nf = (float(v) for v in face_interval(u[wf], hi, top_low_side=False))
        wrong, nf = int(wrong), int(nf)
    rl, wl, nw = lines(x0)
    if rl is None or wl is None:
        rec.update(verdict="unclear", reason="no returns on the road or the walk side")
        return rec
    step = ev(wl, x0) - ev(rl, x0)
    rec.update(face_m=r3(side * x0), unc_m=r3(unc), step_m=r3(step), walk_bins=nw, face_points=nf, face_wrong_side=wrong,
               walk_slope=r3(wl[0], 4), road_slope=r3(rl[0], 4))
    if nw < N_WALK_BINS:
        rec.update(verdict="unclear", reason=f"{nw} bins on the walk side")
    elif CURB_LO <= step <= CURB_HI:
        rec.update(verdict="curb", reason="")
    elif step > CURB_HI:
        rec.update(verdict="edge", reason=f"rise {step:+.3f} m over {CURB_HI}: a wall, bank or hedge where the pavement ends")
    else:
        rec.update(verdict="unclear", reason=f"step {step:+.3f} m under {CURB_LO}")
    return rec


def measure(s):
    (px, pz), t, n = pc.frame(s)
    ii = np.array(ptree.query_ball_point([px, pz], R), dtype=np.int64)
    dx, dz = L["x"][ii] - px, L["z"][ii] - pz
    al = dx * t[0] + dz * t[1]
    la = dx * n[0] + dz * n[1]
    w = (np.abs(al) <= HALF_ALONG) & (np.abs(la) <= HALF_OUTER)
    ii, al, la = ii[w], al[w], la[w]
    oi, oal, ola = ii, al, la                      # the wide section, for the outer curbs
    w = np.abs(la) <= HALF_ACROSS                  # the island's section, +-12 m
    ii, al, la = ii[w], al[w], la[w]
    g, a = GND[ii], SETA[ii]
    # grade along the tangent, off class 2
    gsrc = "class 2"
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
        grade = float(np.polyfit(aa[kk], res[kk], 1)[0])
    else:
        grade = (pc.num(s + 2.5, "y_3dep") - pc.num(s - 2.5, "y_3dep")) / 5.0
        gsrc = "y_3dep"
    zc = L["elev"][ii] - grade * al
    RA = find(la[a], zc[a], BIN_A, W_A, MIN_BINS_A, N_TOP_A, N_WIN_A)
    RG = find(la[g], zc[g], BIN_G, W_G, MIN_BINS_G, N_TOP_G, N_WIN_G)
    ok = OK[ii]
    counts = {"all_not_withheld": int((~L["wh"][ii]).sum()), "noise": int(np.isin(L["cls"][ii], NOISE).sum()),
              "class_2": int(g.sum()), "class_1": int((ok & (L["cls"][ii] == 1)).sum()), "set_a": int(a.sum()),
              "over_a_band": int((ok & (L["h_tin"][ii] > A_HI)).sum())}
    # which reading. The top where vegetation is counted: A's faces, else G's, else the declared band
    d0, dnow = declared(s)
    if RA.get("left_m") is not None:
        lo_, hi_, top_from = RA["right_m"], RA["left_m"], "all returns"
    elif RG.get("left_m") is not None:
        lo_, hi_, top_from = RG["right_m"], RG["left_m"], "class 2"
    elif d0[0] > 0:
        lo_, hi_, top_from = d0[1] - d0[0] / 2, d0[1] + d0[0] / 2, "declared band"
    else:
        lo_ = hi_ = top_from = None
    veg = 0
    if lo_ is not None:
        on = ok & (la > lo_ + 0.1) & (la < hi_ - 0.1)
        veg = int((on & (L["h_tin"][ii] > VEG_H)).sum())
        counts["on_top_all"] = int(on.sum())
        counts["on_top_class_2"] = int((g & (la > lo_ + 0.1) & (la < hi_ - 0.1)).sum())
        counts["top_from"] = top_from
    counts["vegetation_on_top"] = veg
    if veg >= VEG_N:
        use_ = "class 2"
        if RG["verdict"] == "island":
            why = f"vegetation on the top ({veg} returns over {VEG_H} m): class 2 alone"
            verdict, reason = "island", ""
        else:
            why = f"vegetation on the top ({veg} returns over {VEG_H} m): class 2 alone, which shows no plateau"
            verdict, reason = "unclear", "vegetation; class 2: " + (RG.get("reason") or RG["verdict"])
    elif RA["verdict"] == "island" or RA["verdict"] == "none" or RG["verdict"] != "island":
        use_, why = "all returns", ""
        verdict, reason = RA["verdict"], RA.get("reason", "")
    else:
        use_ = "class 2"
        why = "all returns: " + (RA.get("reason") or RA["verdict"]) + "; class 2 shows the plateau"
        verdict, reason = "island", ""
    pick = RG if use_ == "class 2" else RA
    row = {"s": s, "verdict": verdict, "reason": reason, "reading": use_, "why": why}
    if verdict == "island" or (verdict == "unclear" and pick.get("left_m") is not None):
        for k in ("left_m", "right_m", "width_m", "middle_m", "left_unc_m", "right_unc_m", "step_left_m", "step_right_m",
                  "top_over_road_m", "both_steps_ge_step_lo"):
            row[k] = pick.get(k)
        if pick.get("left_unc_m") is not None:
            row["width_unc_m"] = r3(math.hypot(pick["left_unc_m"], pick["right_unc_m"]))
            row["middle_unc_m"] = r3(0.5 * math.hypot(pick["left_unc_m"], pick["right_unc_m"]))
    row["counts"] = counts
    row["grade"] = {"along": r3(grade, 4), "from": gsrc}
    row["declared"] = {"island": island_of(s), "type": d0[2], "width_m": r3(d0[0], 2), "middle_m": r3(d0[1], 2),
                       "left_m": r3(d0[1] + d0[0] / 2, 2), "right_m": r3(d0[1] - d0[0] / 2, 2)}
    if d0 != dnow:
        row["pc_fit"] = {"type": dnow[2], "width_m": r3(dnow[0], 2), "middle_m": r3(dnow[1], 2),
                         "left_m": r3(dnow[1] + dnow[0] / 2, 2), "right_m": r3(dnow[1] - dnow[0] / 2, 2)}
    fp = faces_photo.get(s)
    if fp and fp.get("used") and fp.get("width_m"):
        row["photo_raw"] = {"width_m": fp["width_m"], "middle_m": fp["centre_m"], "left_m": fp.get("left_m"), "right_m": fp.get("right_m")}
    gp = gaps_photo.get(s)
    if gp is not None and s < 300:
        row["photo_gaps"] = {"salmon_w_m": gp["salmon_w_m"],
                             "salmon_middle_m": (None if gp["salmon_mid_m"] is None else r3(d0[1] - gp["salmon_mid_m"], 2))}
    if row.get("middle_m") is not None:
        row["d_middle_vs_declared_m"] = r3(row["middle_m"] - d0[1])
        row["d_width_vs_declared_m"] = r3(row["width_m"] - d0[0])
    for nm, R_ in (("all_returns", RA), ("class_2", RG)):
        row[nm] = {k: v for k, v in R_.items() if k != "profile_bins"}
    prof = {"bin_m": 0.25, "from_m": -6.0}
    for nm, R_, bw in (("all_returns", RA, BIN_A), ("class_2", RG, BIN_G)):
        bm = R_.get("profile_bins")
        if bm is None:
            prof[nm] = None
            continue
        cen = -HALF_ACROSS + (np.arange(len(bm)) + 0.5) * bw
        out = []
        for x0 in np.arange(-6.0, 6.0 - 1e-9, 0.25):
            k = (cen >= x0) & (cen < x0 + 0.25) & np.isfinite(bm)
            out.append(r3(np.median(bm[k]), 2) if k.any() else None)
        prof[nm] = out
    prof["_doc"] = ("median height (m, to 0.01) per 0.25 m across, -6 to +6 m, over a trimmed straight line through the "
                    "section (the road's cross-fall out); all_returns from its 0.10 m bins; null = no return")
    row["profile"] = prof
    # the road's two outer curbs, on the +-22 m section (set A, the same grade out)
    zo, ao = L["elev"][oi] - grade * oal, OK[oi]
    pl, pr_ = pc.num(s, "left_m"), pc.num(s, "right_m")
    OLr = outer_face(ola[ao], zo[ao], +1, pl)
    ORr = outer_face(ola[ao], zo[ao], -1, pr_)
    row["outer"] = {"left": OLr, "right": ORr}
    for nm, R_ in (("left", OLr), ("right", ORr)):
        row[f"{nm}_outer_verdict"] = R_["verdict"]
        row[f"{nm}_outer_face_m"] = R_.get("face_m")
        row[f"{nm}_outer_unc_m"] = R_.get("unc_m")
        row[f"{nm}_outer_step_m"] = R_.get("step_m")
    cl, cr = OLr["verdict"] in ("curb", "edge"), ORr["verdict"] in ("curb", "edge")
    isl_ok = verdict == "island"
    if cl and cr:
        row["road_middle_m"] = r3(0.5 * (OLr["face_m"] + ORr["face_m"]))
        row["road_width_m"] = r3(OLr["face_m"] - ORr["face_m"])
        if isl_ok:
            row["island_middle_from_road_middle_m"] = r3(row["middle_m"] - row["road_middle_m"])
    if isl_ok and cl:
        row["lane_room_left_m"] = r3(OLr["face_m"] - row["left_m"])
    if isl_ok and cr:
        row["lane_room_right_m"] = r3(row["right_m"] - ORr["face_m"])
    dmid = 0.5 * (pl + pr_)
    row["declared"].update(road_left_m=r3(pl, 2), road_right_m=r3(pr_, 2), road_middle_m=r3(dmid, 2), road_width_m=r3(pl - pr_, 2))
    if d0[0] > 0:
        row["declared"].update(island_middle_from_road_middle_m=r3(d0[1] - dmid, 2),
                               lane_room_left_m=r3(pl - (d0[1] + d0[0] / 2), 2), lane_room_right_m=r3((d0[1] - d0[0] / 2) - pr_, 2))
    # vertical sanity: the road at the line against the plan's 3DEP profile
    road0 = (np.abs(la) <= 0.5) & a
    row["road_at_line_minus_y3dep_m"] = r3(np.median(zc[road0]) - ENGINE_DY - pc.num(s, "y_3dep")) if road0.sum() >= 5 else None
    return row


# ------------------------------------------------------------------ run
rows = {s: measure(s) for s in S_ALL}
log("stations measured", len(rows))
for s in S_ALL:
    r = rows[s]
    print(f"  {s:7.1f} {r['verdict']:8s} {r['reading'][:3]} "
          + (f"L {r['left_m']:+6.2f}±{r['left_unc_m'] or 0:.2f} R {r['right_m']:+6.2f}±{r['right_unc_m'] or 0:.2f} "
             f"w {r['width_m']:5.2f} mid {r['middle_m']:+5.2f} steps {r['step_left_m']:+.3f}/{r['step_right_m']:+.3f} "
             f"top {r['top_over_road_m']:+.3f}" if r.get("left_m") is not None else " " * 40)
          + f"  decl {r['declared']['middle_m']:+.2f}/{r['declared']['width_m']:.2f}  {r['reason']}"
          + f"  n A{r['counts']['set_a']} G{r['counts']['class_2']} gtop {r['counts'].get('on_top_class_2')} veg {r['counts']['vegetation_on_top']}"
          + "  | outer L %s %s R %s %s decl %+.2f/%+.2f" % (r["left_outer_verdict"][:5], "%+6.2f/%.3f" % (r["left_outer_face_m"], r["left_outer_step_m"]) if r["left_outer_face_m"] is not None else "--",
                                                       r["right_outer_verdict"][:5], "%+6.2f/%.3f" % (r["right_outer_face_m"], r["right_outer_step_m"]) if r["right_outer_face_m"] is not None else "--",
                                                       r["declared"]["road_left_m"], r["declared"]["road_right_m"]),
          flush=True)


# ------------------------------------------------------------------ summaries
def runs_of(ss):
    out = []
    for s in ss:
        v = rows[s]["verdict"]
        if out and out[-1]["verdict"] == v and abs(s - out[-1]["s"][1] - 2.5) < 1e-6:
            out[-1]["s"][1] = s
            out[-1]["stations"] += 1
        else:
            out.append({"verdict": v, "s": [s, s], "stations": 1})
    return out


def stats(ss, key):
    v = [rows[s][key] for s in ss if rows[s]["verdict"] == "island" and rows[s].get(key) is not None]
    if not v:
        return None
    return {"median": r3(np.median(v)), "p10": r3(np.percentile(v, 10)), "p90": r3(np.percentile(v, 90)), "n": len(v)}


def segments(ss):
    """maximal runs of stations that are not 'none' (unclear stations inside them kept), each with its island stations"""
    segs, cur = [], None
    for s in ss:
        if rows[s]["verdict"] == "none":
            if cur:
                segs.append(cur)
            cur = None
            continue
        if cur is None:
            cur = {"s": [s, s], "stations": []}
        cur["s"][1] = s
        cur["stations"].append(s)
    if cur:
        segs.append(cur)
    out = []
    for sg in segs:
        isl = [s for s in sg["stations"] if rows[s]["verdict"] == "island"]
        out.append({"s": sg["s"], "stations": len(sg["stations"]), "island_stations": len(isl),
                    "first_island_s": isl[0] if isl else None, "last_island_s": isl[-1] if isl else None,
                    "unclear_s": [s for s in sg["stations"] if rows[s]["verdict"] == "unclear"],
                    "declared_islands": sorted({rows[s]["declared"]["island"] for s in sg["stations"] if rows[s]["declared"]["island"]}),
                    "width_m": stats(isl, "width_m"), "middle_m": stats(isl, "middle_m"),
                    "left_m": stats(isl, "left_m"), "right_m": stats(isl, "right_m"),
                    "d_middle_vs_declared_m": stats(isl, "d_middle_vs_declared_m"),
                    "d_width_vs_declared_m": stats(isl, "d_width_vs_declared_m"),
                    "top_over_road_m": stats(isl, "top_over_road_m")})
    return out


def ss_in(a, b):
    return [s for s in S_ALL if a - 1e-6 <= s <= b + 1e-6]


def compare_strip(a, b, photo_fit, photo_raw):
    ss = ss_in(a, b)
    isl = [s for s in ss if rows[s]["verdict"] == "island"]
    o0 = med([rows[s]["declared"]["middle_m"] for s in ss])
    w_ = stats(isl, "width_m")
    m_ = stats(isl, "middle_m")
    d_ = med([rows[s]["middle_m"] - rows[s]["declared"]["middle_m"] for s in isl])
    out = {"stations": len(ss), "island": len(isl), "unclear": [s for s in ss if rows[s]["verdict"] == "unclear"],
           "none": [s for s in ss if rows[s]["verdict"] == "none"],
           "width_m": w_, "middle_m": m_, "left_m": stats(isl, "left_m"), "right_m": stats(isl, "right_m"),
           "middle_minus_declared_middle_m": r3(d_), "declared_middle_m_median": r3(o0),
           "top_over_road_m": stats(isl, "top_over_road_m"),
           "face_unc_m_median": r3(med([rows[s]["left_unc_m"] for s in isl] + [rows[s]["right_unc_m"] for s in isl]))}
    if w_:
        pw, pd = photo_fit
        rw, rm = photo_raw
        out["vs_photo"] = {
            "photo_fit": {"width_m": pw, "middle_minus_declared_m": pd, "middle_m": r3(o0 + pd, 2),
                          "lidar_minus_photo": {"width_m": r3(w_["median"] - pw), "middle_m": r3(d_ - pd)}},
            "photo_raw": {"width_m": rw, "middle_m": rm, "what": "faces_md.py's medians before fix_mg_median.py added "
                          f"+{PHOTO_BIAS_W} m width and +{PHOTO_BIAS_C} m to the middle",
                          "lidar_minus_photo": {"width_m": r3(w_["median"] - rw), "middle_m": r3(m_["median"] - rm)}}}
        pr = [(rows[s]["width_m"] - rows[s]["photo_raw"]["width_m"], rows[s]["middle_m"] - rows[s]["photo_raw"]["middle_m"])
              for s in isl if "photo_raw" in rows[s]]
        if pr:
            out["vs_photo"]["per_station_lidar_minus_photo_raw"] = {"stations": len(pr),
                                                                    "width_m": r3(np.median([p[0] for p in pr])),
                                                                    "middle_m": r3(np.median([p[1] for p in pr]))}
        pf = [s for s in isl if "pc_fit" in rows[s]]
        if pf:
            out["vs_photo"]["photo_fit"]["per_station_lidar_minus_pc_fit_faces"] = {
                "stations": len(pf), "left_m": r3(med([rows[s]["left_m"] - rows[s]["pc_fit"]["left_m"] for s in pf])),
                "right_m": r3(med([rows[s]["right_m"] - rows[s]["pc_fit"]["right_m"] for s in pf]))}
    return out


def first_last(ss, verdict):
    v = [s for s in ss if rows[s]["verdict"] == verdict]
    return (v[0], v[-1]) if v else (None, None)




def inputs_md5():
    files = [AIR / "tools" / "expansion_pieces.py", LM / "data" / "expansion.north.json", LM / "data" / "centerline.local.json",
             MG / "mg_median_correction.json", MG / "md13_faces_s960-1240.json", MG / "md13_gaps.json"]
    out_ = {str(p.relative_to(AIR)): md5(p) for p in files}
    out_["lm-shrub tool shrub_heights.py"] = md5(Path(SH.__file__))
    return out_


SETTINGS = ("HALF_ALONG", "HALF_ACROSS", "BIN_A", "BIN_G", "W_A", "W_G", "MIN_BINS_A", "MIN_BINS_G", "DET_MIN", "NONE_MAX",
            "SEARCH_M", "MIN_W", "GUARD", "ROAD_M", "FACE_WIN", "STEP_LO", "STEP_HI", "STEP_SIDE_MIN", "N_TOP_A", "N_TOP_G",
            "N_WIN_A", "N_WIN_G", "A_LO", "A_HI", "VEG_H", "VEG_N", "HALF_OUTER", "OUTER_FROM", "CURB_DET", "CURB_LO",
            "CURB_HI", "WALK_M", "N_WALK_BINS", "OUT_Q", "ROAD_FIT_IN")


def dump(o, **kw):
    return json.dumps(o, ensure_ascii=False, default=lambda v: v.tolist() if hasattr(v, "tolist") else str(v), **kw)


def write(out, name, row_keys):
    """indented, one station per line"""
    head = {k: v for k, v in out.items() if k not in row_keys}
    txt = dump(head, indent=1)[:-2]
    for k in row_keys:
        txt += ',\n "%s": [\n' % k + ",\n".join("  " + dump(r, separators=(",", ":")) for r in out[k]) + "\n ]"
    txt += "\n}\n"
    json.loads(txt)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(txt, encoding="utf-8")
    log("written", OUT / name)


FRAME_DOC = {"piece": "C mission_gorge (tools/expansion_pieces.Piece.frame)", "origin": origin,
             "projection": "shrub_heights.Track.to_local: pyproj EPSG %d -> 4326 ('%s', stated accuracy %s m), then the WGS84 "
                           "metres-per-degree series at the origin" % (epsg, to_ll.description, to_ll.accuracy)}
DOC_ROWS = ("Piece frame: metres off piece C's line, + = left of J3 -> J4 travel = north-west. left_m / right_m = the two faces, "
            "width_m = left - right, middle_m = their mean; *_unc_m = half the interval between the neighbouring points the face "
            "lies between (point spacing); steps = top - road at each face; top_over_road_m = the top's median minus the mean of "
            "the two road lines at the faces. declared = the plan before ledger 0099 item 1b (mg_median_correction.json rows[0] "
            "over s 982.5-1212.5, the data's rows elsewhere); pc_fit = the rows the PC set there (the data now); photo_raw = "
            "faces_md.py's station (before +0.30 / +0.49); photo_gaps = gaps_md.py's terracotta strip (salmon_middle_m turned into "
            "this frame).")


def road_check(ss):
    v = [rows[s]["road_at_line_minus_y3dep_m"] for s in ss if rows[s]["road_at_line_minus_y3dep_m"] is not None]
    return {"what": "the lidar road (set A within 0.5 m of the line) minus the plan's y_3dep, engine y",
            "median": r3(np.median(v)), "p10_p90": [r3(np.percentile(v, 10)), r3(np.percentile(v, 90))], "n": len(v)}


def smooth(ss, key):
    """running median of an island value over the island stations within +-SMOOTH_HALF_M (at least 3), per station"""
    isl = [(s, rows[s][key]) for s in ss if rows[s]["verdict"] == "island" and rows[s].get(key) is not None]
    out_ = {}
    for s in ss:
        v = [x for t, x in isl if abs(t - s) <= SMOOTH_HALF_M + 1e-6]
        out_[s] = float(np.median(v)) if len(v) >= 3 else None
    return out_


def changes(ss, key, dkey):
    """stretches where the smoothed value changes by more than FLAG_M over CHANGE_OVER_M"""
    sm = smooth(ss, key)
    h = CHANGE_OVER_M / 2
    hit = []
    for s in ss:
        a, b = sm.get(round(s - h, 1)), sm.get(round(s + h, 1))
        if a is not None and b is not None and abs(b - a) > FLAG_M:
            hit.append((s, b - a))
    out_ = []
    for s, d in hit:
        if out_ and s - out_[-1]["s"][1] <= 5.0 + 1e-6 and np.sign(d) == np.sign(out_[-1]["_sign"]):
            out_[-1]["s"][1] = s
            out_[-1]["max_change_m"] = r3(d if abs(d) > abs(out_[-1]["max_change_m"]) else out_[-1]["max_change_m"])
        else:
            out_.append({"s": [s, s], "_sign": d, "max_change_m": r3(d)})
    for o in out_:
        a, b = round(o["s"][0] - h, 1), round(o["s"][1] + h, 1)
        o["lidar_before"], o["lidar_after"] = r3(sm.get(a)), r3(sm.get(b))
        o["declared_before"] = r3(rows[a]["declared"][dkey]) if a in rows else None
        o["declared_after"] = r3(rows[b]["declared"][dkey]) if b in rows else None
        o["direction"] = ("wider" if key == "width_m" else "north-west") if o["_sign"] > 0 else ("narrower" if key == "width_m" else "south-east")
        del o["_sign"]
    return out_


FULL_COLUMNS = ["s", "verdict", "reading", "left_m", "right_m", "left_unc_m", "right_unc_m", "width_m", "middle_m",
                "step_left_m", "step_right_m", "top_over_road_m", "both_steps_ge_step_lo", "n_set_a", "n_class_2",
                "class_2_on_top", "vegetation_on_top", "decl_width_m", "decl_middle_m", "now_width_m", "now_middle_m",
                "left_outer_verdict", "left_outer_face_m", "left_outer_unc_m", "left_outer_step_m",
                "right_outer_verdict", "right_outer_face_m", "right_outer_unc_m", "right_outer_step_m",
                "decl_road_left_m", "decl_road_right_m", "road_middle_m", "decl_road_middle_m", "road_width_m",
                "island_middle_from_road_middle_m", "decl_island_middle_from_road_middle_m",
                "lane_room_left_m", "lane_room_right_m", "decl_lane_room_left_m", "decl_lane_room_right_m", "reason"]


def flat(r):
    d, now = r["declared"], r.get("pc_fit") or r["declared"]
    v = {"n_set_a": r["counts"]["set_a"], "n_class_2": r["counts"]["class_2"], "class_2_on_top": r["counts"].get("on_top_class_2"),
         "vegetation_on_top": r["counts"]["vegetation_on_top"], "decl_width_m": d["width_m"], "decl_middle_m": d["middle_m"],
         "now_width_m": now["width_m"], "now_middle_m": now["middle_m"], "decl_road_left_m": d["road_left_m"],
         "decl_road_right_m": d["road_right_m"], "decl_road_middle_m": d["road_middle_m"],
         "decl_island_middle_from_road_middle_m": d.get("island_middle_from_road_middle_m"),
         "decl_lane_room_left_m": d.get("lane_room_left_m"), "decl_lane_room_right_m": d.get("lane_room_right_m")}
    reason = r["reason"]
    for side in ("left", "right"):
        if r["outer"][side].get("reason"):
            reason += ("; " if reason else "") + f"outer {side}: " + r["outer"][side]["reason"]
    v["reason"] = reason
    return [v[c] if c in v else r.get(c) for c in FULL_COLUMNS]


def rng(v):
    v = [x for x in v if x is not None]
    return {"median": r3(np.median(v)), "min": r3(min(v)), "max": r3(max(v))} if v else None


def dmed(pairs):
    v = [a - b for a, b in pairs if a is not None and b is not None]
    return r3(np.median(v)) if v else None


def reads(d_road, d_isl):
    """[invented] FLAG_M as the line between 'off' and 'right'"""
    if d_road is None or d_isl is None:
        return None
    ro, io = abs(d_road) > FLAG_M, abs(d_isl) > FLAG_M
    return {(False, False): "road and island both within %.2f m of the plan" % FLAG_M,
            (True, False): "the plan's road edges are off; the island sits where the plan has it in the road",
            (False, True): "the road edges are where the plan has them; the island is off in the road",
            (True, True): "both off"}[(ro, io)]


def road_block(ss):
    """per station set: the real road (two outer curbs) against the plan's edges, the island measured from the real road"""
    both = [s for s in ss if rows[s].get("road_middle_m") is not None]
    il = [s for s in both if rows[s].get("island_middle_from_road_middle_m") is not None]
    dec = lambda s, k: rows[s]["declared"].get(k)  # noqa: E731
    b = {"stations_with_both_curbs": len(both),
         "curb_left": {v: sum(1 for s in ss if rows[s]["left_outer_verdict"] == v) for v in ("curb", "edge", "none", "unclear")},
         "curb_right": {v: sum(1 for s in ss if rows[s]["right_outer_verdict"] == v) for v in ("curb", "edge", "none", "unclear")},
         "road_middle_m": {"lidar": rng([rows[s]["road_middle_m"] for s in both]),
                           "declared": rng([dec(s, "road_middle_m") for s in both]),
                           "lidar_minus_declared": dmed([(rows[s]["road_middle_m"], dec(s, "road_middle_m")) for s in both])},
         "road_width_m": {"lidar": rng([rows[s]["road_width_m"] for s in both]),
                          "declared": rng([dec(s, "road_width_m") for s in both]),
                          "lidar_minus_declared": dmed([(rows[s]["road_width_m"], dec(s, "road_width_m")) for s in both])},
         "left_outer_face_m": {"lidar": rng([rows[s]["left_outer_face_m"] for s in ss if rows[s]["left_outer_verdict"] in ("curb", "edge")]),
                               "lidar_minus_declared": dmed([(rows[s]["left_outer_face_m"], dec(s, "road_left_m")) for s in ss
                                                             if rows[s]["left_outer_verdict"] in ("curb", "edge")])},
         "right_outer_face_m": {"lidar": rng([rows[s]["right_outer_face_m"] for s in ss if rows[s]["right_outer_verdict"] in ("curb", "edge")]),
                                "lidar_minus_declared": dmed([(rows[s]["right_outer_face_m"], dec(s, "road_right_m")) for s in ss
                                                              if rows[s]["right_outer_verdict"] in ("curb", "edge")])},
         "curb_step_m": {"left": rng([rows[s]["left_outer_step_m"] for s in ss if rows[s]["left_outer_verdict"] == "curb"]),
                         "right": rng([rows[s]["right_outer_step_m"] for s in ss if rows[s]["right_outer_verdict"] == "curb"])},
         "island_middle_from_road_middle_m": {
             "stations": len(il), "lidar": rng([rows[s]["island_middle_from_road_middle_m"] for s in il]),
             "declared": rng([dec(s, "island_middle_from_road_middle_m") for s in il]),
             "lidar_minus_declared": dmed([(rows[s]["island_middle_from_road_middle_m"], dec(s, "island_middle_from_road_middle_m")) for s in il])},
         "lane_room_left_m": {"lidar": rng([rows[s].get("lane_room_left_m") for s in ss]),
                              "declared": rng([dec(s, "lane_room_left_m") for s in ss if rows[s].get("lane_room_left_m") is not None]),
                              "lidar_minus_declared": dmed([(rows[s].get("lane_room_left_m"), dec(s, "lane_room_left_m")) for s in ss])},
         "lane_room_right_m": {"lidar": rng([rows[s].get("lane_room_right_m") for s in ss]),
                               "declared": rng([dec(s, "lane_room_right_m") for s in ss if rows[s].get("lane_room_right_m") is not None]),
                               "lidar_minus_declared": dmed([(rows[s].get("lane_room_right_m"), dec(s, "lane_room_right_m")) for s in ss])}}
    b["reads"] = (reads(b["road_middle_m"]["lidar_minus_declared"], b["island_middle_from_road_middle_m"]["lidar_minus_declared"])
                  if b["island_middle_from_road_middle_m"]["stations"] >= MIN_BOTH else
                  "too few stations (%d) with the island and both outer faces" % b["island_middle_from_road_middle_m"]["stations"])
    return b


def bins_of(ss):
    out_, b0 = [], math.floor(ss[0] / BIN_SUM_M) * BIN_SUM_M
    while b0 <= ss[-1]:
        sb = [s for s in ss if b0 - 1e-6 <= s < b0 + BIN_SUM_M - 1e-6]
        b0 += BIN_SUM_M
        if sb:
            out_.append(sb)
    return out_


def curb_flags(ss):
    out_ = {}
    for side in ("left", "right"):
        rr_, cur = [], None
        for s in ss:
            v = rows[s][f"{side}_outer_verdict"]
            if cur and cur["verdict"] == v and abs(s - cur["s"][1] - 2.5) < 1e-6:
                cur["s"][1] = s
                cur["stations"] += 1
            else:
                cur = {"verdict": v, "s": [s, s], "stations": 1}
                rr_.append(cur)
        out_[side] = {"no_curb_runs": [r_ for r_ in rr_ if r_["verdict"] == "none"],
                      "unclear_runs": [r_ for r_ in rr_ if r_["verdict"] == "unclear" and r_["stations"] >= MIN_UNCLEAR_RUN]}
    return out_


if FULL:
    SS = S_ALL
    bins = []
    b0 = math.floor(SS[0] / BIN_SUM_M) * BIN_SUM_M
    while b0 <= SS[-1]:
        ss = [s for s in SS if b0 - 1e-6 <= s < b0 + BIN_SUM_M - 1e-6]
        b0 += BIN_SUM_M
        if not ss:
            continue
        isl = [s for s in ss if rows[s]["verdict"] == "island"]
        dec = [rows[s]["declared"] for s in ss]
        now = [rows[s].get("pc_fit") or rows[s]["declared"] for s in ss]
        e = {"s": [ss[0], ss[-1]], "stations": len(ss), "island": len(isl),
             "none": sum(1 for s in ss if rows[s]["verdict"] == "none"),
             "unclear": sum(1 for s in ss if rows[s]["verdict"] == "unclear"),
             "lidar": {"width_m": rng([rows[s]["width_m"] for s in isl]), "middle_m": rng([rows[s]["middle_m"] for s in isl]),
                       "left_m": rng([rows[s]["left_m"] for s in isl]), "right_m": rng([rows[s]["right_m"] for s in isl]),
                       "top_over_road_m": rng([rows[s]["top_over_road_m"] for s in isl])},
             "declared": {"width_m": rng([d["width_m"] for d in dec if d["width_m"] > 0]),
                          "middle_m": rng([d["middle_m"] for d in dec if d["width_m"] > 0]),
                          "stations_with_no_island": sum(1 for d in dec if d["width_m"] <= 0)}}
        if any("pc_fit" in rows[s] for s in ss):
            e["in_the_data_now"] = {"width_m": rng([d["width_m"] for d in now if d["width_m"] > 0]),
                                    "middle_m": rng([d["middle_m"] for d in now if d["width_m"] > 0]),
                                    "stations_with_no_island": sum(1 for d in now if d["width_m"] <= 0),
                                    "what": "the PC's fit (ledger 0099 item 1b) on the stations it set"}
        if isl:
            dd = [rows[s]["declared"] for s in isl]
            e["lidar_minus_declared"] = {
                "width_m": r3(np.median([rows[s]["width_m"] - d["width_m"] for s, d in zip(isl, dd)])),
                "middle_m": r3(np.median([rows[s]["middle_m"] - d["middle_m"] for s, d in zip(isl, dd)])),
                "left_m": r3(np.median([rows[s]["left_m"] - d["left_m"] for s, d in zip(isl, dd)])),
                "right_m": r3(np.median([rows[s]["right_m"] - d["right_m"] for s, d in zip(isl, dd)]))}
            if "in_the_data_now" in e:
                nn = [rows[s].get("pc_fit") or rows[s]["declared"] for s in isl]
                e["lidar_minus_data_now"] = {
                    "width_m": r3(np.median([rows[s]["width_m"] - d["width_m"] for s, d in zip(isl, nn)])),
                    "middle_m": r3(np.median([rows[s]["middle_m"] - d["middle_m"] for s, d in zip(isl, nn)]))}
        e["road"] = road_block(ss)
        bins.append(e)
    rr = runs_of(SS)
    openings = []
    for k, r_ in enumerate(rr):
        if r_["verdict"] != "none":
            continue
        before = [s for s in SS if s < r_["s"][0] and rows[s]["verdict"] == "island"]
        after = [s for s in SS if s > r_["s"][1] and rows[s]["verdict"] == "island"]
        dec_no = [s for s in SS if r_["s"][0] <= s <= r_["s"][1] and rows[s]["declared"]["width_m"] <= 0]
        openings.append({"s": r_["s"], "stations": r_["stations"], "last_island_before_s": before[-1] if before else None,
                         "first_island_after_s": after[0] if after else None,
                         "declared_island_stations_there": r_["stations"] - len(dec_no),
                         "median_ids_now": sorted({rows[s]["declared"]["island"] for s in SS if r_["s"][0] <= s <= r_["s"][1]
                                                   and rows[s]["declared"]["island"]})})

    def gaps_of(band):
        out_ = []
        for s in SS:
            if band(s)["width_m"] <= 0:
                if out_ and abs(s - out_[-1][1] - 2.5) < 1e-6:
                    out_[-1][1] = s
                else:
                    out_.append([s, s])
        return out_
    dec_gaps = gaps_of(lambda s: rows[s]["declared"])
    now_gaps = gaps_of(lambda s: rows[s].get("pc_fit") or rows[s]["declared"])
    bw_steps = [{"from_bin_s": a["s"], "to_bin_s": b["s"], "lidar_width_m": [a["lidar"]["width_m"]["median"], b["lidar"]["width_m"]["median"]],
                 "declared_width_m": [(a["declared"]["width_m"] or {}).get("median"), (b["declared"]["width_m"] or {}).get("median")]}
                for a, b in zip(bins, bins[1:]) if a["lidar"]["width_m"] and b["lidar"]["width_m"]
                and abs(b["lidar"]["width_m"]["median"] - a["lidar"]["width_m"]["median"]) > FLAG_M]
    off = [{"s": e["s"], **e["lidar_minus_declared"]} for e in bins if "lidar_minus_declared" in e
           and (abs(e["lidar_minus_declared"]["width_m"]) > FLAG_M or abs(e["lidar_minus_declared"]["middle_m"]) > FLAG_M)]
    isl_all = [s for s in SS if rows[s]["verdict"] == "island"]
    unc_runs = [r_ for r_ in rr if r_["verdict"] == "unclear" and r_["stations"] >= MIN_UNCLEAR_RUN]
    summary = {
        "what": "piece C s %.1f-%.1f, every 2.5 m: per %g m bin the lidar island against the declared band, and the flags"
                % (SS[0], SS[-1], BIN_SUM_M),
        "stations": len(SS), "verdicts": {v: sum(1 for s in SS if rows[s]["verdict"] == v) for v in ("island", "none", "unclear")},
        "overall_lidar_minus_declared": {
            "width_m": stats(isl_all, "d_width_vs_declared_m"), "middle_m": stats(isl_all, "d_middle_vs_declared_m"),
            "left_m": {"median": r3(np.median([rows[s]["left_m"] - rows[s]["declared"]["left_m"] for s in isl_all]))},
            "right_m": {"median": r3(np.median([rows[s]["right_m"] - rows[s]["declared"]["right_m"] for s in isl_all]))}},
        "top_over_road_m": stats(isl_all, "top_over_road_m"),
        "step_left_m": stats(isl_all, "step_left_m"), "step_right_m": stats(isl_all, "step_right_m"),
        "island_with_both_steps_ge_step_lo": sum(1 for s in isl_all if rows[s]["both_steps_ge_step_lo"]),
        "readings": {"all_returns": sum(1 for s in SS if rows[s]["reading"] == "all returns"),
                     "class_2": sum(1 for s in SS if rows[s]["reading"] == "class 2"),
                     "class_2_because_vegetation": sum(1 for s in SS if rows[s]["why"].startswith("vegetation"))},
        "per_50m": bins,
        "flags": {
            "_doc": "openings = runs of 'none' stations (the island ends between last_island_before_s and the run, and starts "
                    "again between the run and first_island_after_s); declared_gaps = runs of stations where the declared band "
                    "has no island (data_now_gaps: the band in the data now); width_changes / middle_shifts = stretches where the running median (island stations within "
                    "+-%g m [invented]) changes by more than %g m over %g m [invented], with the values %g m either side; "
                    "bin_width_steps = consecutive %g m bins whose median widths differ by more than %g m; bins_off_declared = "
                    "bins where the median lidar - declared width or middle passes %g m; unclear_runs = %d+ unclear stations "
                    "running" % (SMOOTH_HALF_M, FLAG_M, CHANGE_OVER_M, CHANGE_OVER_M / 2, BIN_SUM_M, FLAG_M, FLAG_M, MIN_UNCLEAR_RUN),
            "openings": openings, "declared_gaps": dec_gaps, "data_now_gaps": now_gaps,
            "width_changes": changes(SS, "width_m", "width_m"), "middle_shifts": changes(SS, "middle_m", "middle_m"),
            "bin_width_steps": bw_steps, "bins_off_declared": off, "unclear_runs": unc_runs,
            "outer_curbs": curb_flags(SS),
            "bins_reading": [{"s": e["s"], "reads": e["road"]["reads"],
                              "road_middle_minus_declared_m": e["road"]["road_middle_m"]["lidar_minus_declared"],
                              "island_from_road_middle_minus_declared_m": e["road"]["island_middle_from_road_middle_m"]["lidar_minus_declared"]}
                             for e in bins]},
        "road_overall": road_block(SS)}
    fchk["road_at_line_minus_y3dep_m"] = road_check(SS)
    out = {"_doc": "Mission Gorge Rd's raised median (Lake Murray piece C) over its whole MD13 / MD13b run: the island's faces per "
                   "station off the USGS 2024 lidar (mg_median_faces_g10.py --full; the method is its docstring, the same as "
                   "mg_median_faces.lidar.g10.json's). Stations are rows of `columns` (decl_* = the plan before item 1b, now_* = the "
                   "data now; *_outer_* = the road's outer curb faces on the +-22 m section; lane_room = outer face to island face; "
                   "road_middle = the mean of the two outer faces). " + DOC_ROWS,
           "status": "measured", "tool": "mg_median_faces_g10.py --full (G10 job lm-mg-median-lidar-20261123)",
           "date": time.strftime("%Y-%m-%d"),
           "source": {"project": "USGS_LPC_CA_SanDiegoCo_D24", "epsg": epsg, "flown": "2024-11 (lm-shrub tiles.json)",
                      "tiles_read": tiles_rep},
           "inputs_md5": inputs_md5(), "frame": dict(FRAME_DOC, checks=fchk),
           "settings": {k: globals()[k] for k in SETTINGS + ("FULL_FROM", "BIN_SUM_M", "FLAG_M", "SMOOTH_HALF_M", "CHANGE_OVER_M",
                                                             "MIN_UNCLEAR_RUN", "MIN_BOTH")},
           "summary": summary, "columns": FULL_COLUMNS, "stations": [flat(rows[s]) for s in SS]}
    write(out, "mg_median_faces_full.lidar.g10.json", ("stations",))
    sys.exit(0)

J3 = ss_in(*MAIN[0])
MGs = ss_in(*MAIN[1])
seg_j3 = segments(J3)
seg_mg = segments(MGs)
gap = [r for r in runs_of(MGs) if r["verdict"] == "none" and r["s"][1] >= 1075 and r["s"][0] <= 1130]
# the J3 end read off its segments (MD11's start from the check stations s 25-37.5 too)
J3x = ss_in(CHECK[0][0], MAIN[0][1])
segx = segments(J3x)
opn = [r for r in runs_of(J3x) if r["verdict"] == "none"]
j3_read = {"what": "the J3 end as the lidar shows it (s of the first / last island station of each raised run, and of each "
                   "run of 'none' stations): an end lies between its last island station and the next 'none' one",
           "raised_runs": [{"s": sg["s"], "first_island_s": sg["first_island_s"], "last_island_s": sg["last_island_s"],
                            "declared_islands": sg["declared_islands"], "width_m_median": (sg["width_m"] or {}).get("median"),
                            "middle_m_median": (sg["middle_m"] or {}).get("median")} for sg in segx],
           "openings_s": [r["s"] for r in opn]}
tapers = []
for a_, b_ in corr["fit"]["tapers_s"]:
    for s_ in ss_in(a_, b_):
        r_ = rows[s_]
        tapers.append({"s": s_, "verdict": r_["verdict"], "left_m": r_.get("left_m"), "right_m": r_.get("right_m"),
                       "pc_fit_left_m": (r_.get("pc_fit") or r_["declared"])["left_m"],
                       "pc_fit_right_m": (r_.get("pc_fit") or r_["declared"])["right_m"]})
summary = {
    "j3_end_s40_250": {
        "runs": runs_of(J3), "segments_between_openings": seg_j3,
        "openings": [r for r in runs_of(J3) if r["verdict"] == "none"],
        "declared": {k: [medians[k]["s_from"], medians[k]["s_to"]] for k in ("MD11", "MD12", "MD13")},
        "declared_crossovers": "st 174 / 202, 12 m each (tools/author_expansion.py GAPS)", "read": j3_read},
    "crossing_s980_1215": {
        "runs": runs_of(MGs), "segments_between_openings": seg_mg,
        "strip_a": compare_strip(*STRIP_A, (corr["fit"]["strip_a"]["width_m"], corr["fit"]["strip_a"]["d_centre_m"]), (1.66, 0.18)),
        "strip_b": compare_strip(*STRIP_B, (corr["fit"]["strip_b"]["width_m"], corr["fit"]["strip_b"]["d_centre_m"]), (1.54, -2.24)),
        "gap": {"lidar_none_runs": gap, "photo": list(GAP_PHOTO), "photo_noses": corr["fit"]["no_median_s"],
                "strip_a_last_island_s": first_last(ss_in(1040, 1100), "island")[1],
                "strip_b_first_island_s": first_last(ss_in(1100, 1140), "island")[0]},
        "tapers_vs_pc_fit": tapers},
}
ref = [s for s in S_ALL if any(a - 1e-6 <= s <= b + 1e-6 for a, b in REF)]
isl = [s for s in ref if rows[s]["verdict"] == "island"]
pr = [s for s in isl if "photo_raw" in rows[s]]
fchk["reference_stretches"] = {
    "what": "faces_md.py's REF stretches (s 930-985, 1215-1260), where the PC took the island to fill its declared band "
            "and read the photo's bias there (width 0.30 m short, middle 0.49 m right): the lidar against the declared band "
            "and against the photo's own raw readings, station by station",
    "stations": len(ref), "island": len(isl),
    "lidar_minus_declared": {"width_m": stats(isl, "d_width_vs_declared_m"), "middle_m": stats(isl, "d_middle_vs_declared_m")},
    "photo_raw_minus_declared_pc_check": PHOTO_CHECK,
    "lidar_minus_photo_raw": {"stations": len(pr),
                              "width_m": r3(med([rows[s]["width_m"] - rows[s]["photo_raw"]["width_m"] for s in pr])),
                              "middle_m": r3(med([rows[s]["middle_m"] - rows[s]["photo_raw"]["middle_m"] for s in pr]))}}
chk3 = ss_in(*CHECK[1])
i3 = [s for s in chk3 if rows[s]["verdict"] == "island"]
fchk["md13_s252_300"] = {"what": "MD13 just past the J3 range (2.2-2.5 m declared; the terracotta doc's registration slide put "
                         "this piece of MD13 at 0.00 m)", "stations": len(chk3), "island": len(i3),
                         "lidar_minus_declared": {"width_m": stats(i3, "d_width_vs_declared_m"), "middle_m": stats(i3, "d_middle_vs_declared_m")}}
fchk["road_at_line_minus_y3dep_m"] = {"what": "the lidar road (set A within 0.5 m of the line) minus the plan's y_3dep, engine y",
                                     "median": r3(med([rows[s]["road_at_line_minus_y3dep_m"] for s in S_ALL])),
                                     "p10_p90": [r3(np.nanpercentile([rows[s]["road_at_line_minus_y3dep_m"] or np.nan for s in S_ALL], 10)),
                                                 r3(np.nanpercentile([rows[s]["road_at_line_minus_y3dep_m"] or np.nan for s in S_ALL], 90))]}
summary["road_per_50m"] = {"_doc": "the real road (its two outer curbs, the +-22 m section) against the plan's edges, and the "
                                   "island's middle measured from the real road's middle, per 50 m (reads: [invented] %.2f m "
                                   "as the line)" % FLAG_M,
                           "s25_300": [dict(s=[sb[0], sb[-1]], **road_block(sb)) for sb in bins_of(ss_in(25.0, 300.0))],
                           "s930_1260": [dict(s=[sb[0], sb[-1]], **road_block(sb)) for sb in bins_of(ss_in(930.0, 1260.0))],
                           "whole_s40_250": road_block(J3), "whole_s980_1215": road_block(MGs),
                           "outer_curb_flags": {"s40_250": curb_flags(J3), "s980_1215": curb_flags(MGs)}}
isl_all = [s for s in J3 + MGs if rows[s]["verdict"] == "island"]
summary["top_over_road_m"] = {"all_island_stations": stats(isl_all, "top_over_road_m"),
                              "step_left_m": stats(isl_all, "step_left_m"), "step_right_m": stats(isl_all, "step_right_m")}
summary["readings"] = {"all_returns": sum(1 for s in J3 + MGs if rows[s]["reading"] == "all returns"),
                       "class_2": sum(1 for s in J3 + MGs if rows[s]["reading"] == "class 2"),
                       "class_2_because_vegetation": sum(1 for s in J3 + MGs if rows[s]["why"].startswith("vegetation")),
                       "island_with_both_steps_ge_step_lo": sum(1 for s in isl_all if rows[s]["both_steps_ge_step_lo"]),
                       "island_stations": len(isl_all)}
summary["class_2_on_the_top"] = {
    "what": "class-2 returns between the faces at island stations read off all returns: D24's ground class mostly leaves "
            "a narrow raised top out, so class 2 alone shows a hole there, not a plateau",
    "stations_with_none": sum(1 for s in isl_all if rows[s]["reading"] == "all returns" and rows[s]["counts"].get("on_top_class_2") == 0),
    "island_stations_read_off_all_returns": sum(1 for s in isl_all if rows[s]["reading"] == "all returns"),
    "class_2_verdict_island_at_those": sum(1 for s in isl_all if rows[s]["reading"] == "all returns" and rows[s]["class_2"]["verdict"] == "island")}

out = {
    "_doc": "Mission Gorge Rd's raised median (Lake Murray piece C): the island's faces per station off the USGS 2024 lidar "
            "(mg_median_faces_g10.py, its docstring is the method). " + DOC_ROWS,
    "status": "measured", "tool": "mg_median_faces_g10.py (G10 job lm-mg-median-lidar-20261123)", "date": time.strftime("%Y-%m-%d"),
    "source": {"project": "USGS_LPC_CA_SanDiegoCo_D24", "epsg": epsg, "flown": "2024-11 (lm-shrub tiles.json)",
               "tiles_read": tiles_rep},
    "inputs_md5": inputs_md5(),
    "frame": dict(FRAME_DOC, checks=fchk),
    "settings": {k: globals()[k] for k in SETTINGS},
    "summary": summary,
    "stations": [rows[s] for s in J3 + MGs],
    "check_stations": [rows[s] for s in S_ALL if s not in set(J3 + MGs)],
}
write(out, "mg_median_faces.lidar.g10.json", ("stations", "check_stations"))
