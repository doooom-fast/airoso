"""Lake Murray's north network (pieces A-D of data/expansion.north.json): the road's two outer edges per 2.5 m station
off the USGS 2024 lidar, against the built edges, for the "road edges re-fit" round. G10 job lm-north-curbs-20261124.
Reads only; downloads nothing. Run under nice -n 19 ionice -c3, with -I, one piece per run.

    python -I north_curbs_g10.py <tiles dir> <lm tool dir> <airoso dir> <out dir> --piece A|B|C|D [--prior <json>]...

  <tiles dir>    USGS_LPC_CA_SanDiegoCo_D24_*.laz (EPSG read off each header; shrub_heights.tile_list)
  <lm tool dir>  the folder holding the lm-shrub tool, shrub_heights.py (its projection, tile list and LAZ reader)
  <airoso dir>   a checkout (or git archive) of this repository: tools/expansion_pieces.py and Lake Murray's
                 data/expansion.north.json, data/centerline.local.json and data/osm.expansion.json
  <out dir>      north_curbs_<piece>.lidar.g10.json is written here
  --prior        an earlier lidar file of the same piece (jackson_curbs_D.lidar.g10.json, or mg_median_faces*.lidar.g10.json),
                 compared at the stations both read (the overlap check); may be given more than once
Each of the four dirs may instead come from the environment: NC_TILES, NC_LM_TOOL, NC_AIROSO, NC_OUT.

WHICH STATIONS. Every station row of the piece (2.5 m apart, and its last row), less what earlier lidar files already
read (COVERED: piece C s 40-250 and s 225-2245, mg_median/; piece D s 225-492.5 and s 1240-1300, jackson_paint/). CHECK
stations inside those are read again with this method and kept apart, in "overlap_check", against the earlier file.

METHOD. jackson_paint/jackson_curbs_g10.py's (piece D, G10 job lm-jackson-curbs-20261123), itself the outer-curb reading
of mg_median/mg_median_faces_g10.py (Mission Gorge). Its code is kept as it was (the LAST returns, not withheld and not
noise; the along-road grade out; per BIN the OUT_Q percentile; the detector D(x) = the median over (x, x + W] of the bins'
height over a line through the bins in [x - TREND_M, x); the first rise past CURB_DET or drop past -DROP_DET outward,
refined on the points; curb / edge (rise) / edge (drop) / none / unclear; ROAD_TOL against canopy). Changed:
  window   +-HALF_ACROSS 22 m (Mission Gorge's HALF_OUTER; jackson's was 18): the built edges run out to +17.1 / -16.3
           and the real ones have been found up to 3.6 m off them.
  start    the search starts OUTER_FROM (4 m) off the line, or where a raised median is declared (medians[].raised),
           ISLAND_CLEAR past that side's declared island face if that is further: a raised island's outer face is a
           "drop" to the detector. ISLAND_CLEAR 3 m is under one lane, so the search still starts inside the lane.
  objects  a rise of OBJ_H or more whose outer side holds under GROUND_MIN class-2 returns is not ground: if the profile
           comes back to within BACK_H of the road line within OBJ_W_MAX, it is a vehicle or object (a parked car, mostly).
           If road (ROAD_RESUME of TREND_M at the road line's height) follows it, the search goes on past it (traffic
           in a lane) and a face found there says so; if not (a car parked at the curb), the side is "can't call:
           vehicle". A non-ground rise that does not come back stays an edge (rise), its "what" non-ground (a wall,
           hedge, fence or building); one with class 2 on its outer side is "ground (bank)".
  islands  any rise that comes back down to within DIV_BACK of the road line within DIV_W_MAX, with road (ROAD_RESUME
           of the next LANE_M within DIV_ROAD of the road line) past it, stands inside the road: a raised divider or
           island the data does not declare (curb height; piece D s 880-1010 has a narrow one from 8.5 m to 4.4 m right
           of the line), a post line or a car in a lane (taller). It is passed, and the search goes on past it. And where the first 0.3 m of the search stands START_H or more over
           the road just inside it (START_IN), the search began on such a thing: it starts again where the profile is
           back at the road, within START_MAX ("search_from_moved").
  labels   every side that gives no face is put in one can't-call category: outside the tiles, junction (the piece's own
           pad / weld past cuts.start / cuts.end), junction mouth (an OSM road or service way meeting that side within
           MOUTH_HALF of the station), vehicle, canopy (the ROAD_TOL test, or CANOPY_SHARE of the returns within 3 m of
           the built edge not last returns: partly penetrable cover), no rise or drop (a flush edge or an unmapped
           driveway), or step out of bounds.
The real road's middle = the mean of the two faces (curb or edge); the built road's middle = (left_m + right_m) / 2 of
the piece's own row; built width = left_m - right_m.

SUMMARY (over the stations measured here, not the check stations). Per 25 m bin of s (0-25, 25-50, ...): the station
counts, and for each face, the middle and the width the median / min / max / IQR / n of real minus built, a call ("ok"
with MIN_N+ readings and IQR <= MAX_IQR, else can't call and why), the face types, and the runs of stations each side
can't call, by category. Per piece: runs of consecutive called bins built off by over OFF_M and within CLOSE_M; the same
from a running median per station (RUN_HALF_M, RUN_MIN; runs of 3+ stations); and the unmeasured stations per side by
category. Each face also carries minus_neighbours_m, its offset from the median of the other faces read on that side within
NB_HALF_M (a face more than NB_OFF off is counted "apart": a mouth, a bus bay, a curb return or a misread; it is kept).
Every setting marked [invented] is the method's choice, not a measurement. Numpy, scipy, laspy (lazrs), pyproj.

FRAME. The piece's own frame, tools/expansion_pieces.Piece.frame (imported): the station point by linear interpolation of
pieces[].stations, the tangent the chord over +-2.5 m, the left normal (-t_z, t_x). u = metres off the piece's line,
+ = LEFT of travel along increasing s. Lidar E, N -> local x, z by shrub_heights.Track.to_local (pyproj EPSG 6340 ->
4326, then the WGS84 metres-per-degree series at the origin); OSM lon / lat -> x, z by the same series.
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

# ------------------------------------------------------------------ the request
COVERED = {"C": {"s": [(40.0, 250.0), (225.0, 2245.0)],
                 "files": "source/expansion/mg_median/mg_median_faces.lidar.g10.json (s 40-250) and "
                          "mg_median_faces_full.lidar.g10.json (s 225-2245), G10 job lm-mg-median-lidar-20261123"},
           "D": {"s": [(225.0, 492.5), (1240.0, 1300.0)],
                 "files": "source/expansion/jackson_paint/jackson_curbs_D.lidar.g10.json (s 225-492.5, s 1240-1300), "
                          "G10 job lm-jackson-curbs-20261123"}}
CHECK = {"C": [(40.0, 62.5), (2222.5, 2245.0)], "D": [(225.0, 247.5), (1240.0, 1260.0)]}   # [invented] overlap stations
BIN_SUM_M = 25.0            # the request: the summary per 25 m
OFF_M, CLOSE_M = 1.0, 0.3   # the request: built off by more than 1 m; within 0.3 m
# ------------------------------------------------------------------ jackson_curbs_g10.py's settings (unchanged unless said)
HALF_ALONG = 1.25           # [invented] +- along the tangent (as on Mission Gorge)
HALF_ACROSS = 22.0          # [invented] +-22 m (Mission Gorge's HALF_OUTER; jackson's 18 m is short of A-D's built edges + 3.6)
OUTER_FROM = 4.0            # [invented] an edge is searched from 4 m off the line outward
ISLAND_CLEAR = 3.0          # [invented] ... or from this past a declared raised island's face on that side
BIN = 0.10                  # [invented] the profile's bins
W, MIN_BINS = 0.6, 3        # [invented] the detector's half-window, and the non-empty bins it needs each side
OUT_Q = 20                  # [invented] the profile's statistic per bin: this percentile of the returns
CURB_DET = 0.05             # [invented] a rise outward at least this big is a face candidate
DROP_DET = 0.10             # [invented] a drop outward at least this big is a face candidate (a gutter's dip stays under)
NONE_MAX = 0.05             # [invented] no |D| this big from the search start out: "none"
CURB_LO, CURB_HI = 0.05, 0.35   # [invented] a curb's step; over CURB_HI an edge (rise)
GUARD, ROAD_M, WALK_M = 0.15, 2.0, 1.2   # [invented] the lines keep GUARD off the face; road ROAD_M inside, outer WALK_M out
FACE_WIN = 0.5              # [invented] points this close to a coarse face decide it
N_WIN = 150                 # [invented] returns needed on a side
N_WALK_BINS = 4             # [invented] bins with a return needed on the outer side
TREND_M, TREND_MIN = 1.2, 6   # [invented] the detector's local trend: a line through the bins 1.2 m inside x (6+ of them)
INT_M = 1.0                 # [invented] the intensity cue: last returns within this inside / outside the face
ROAD_TOL = 0.6              # [invented] a face's road side must stand within this of the road near the line (else canopy)
CONT_M = 1.0                # [invented] a candidate that gives no face hands on to the next within 1 m outward (1.5 and 3 m
                            # were tried: the faces they add mostly disagree with their neighbours' by over 0.3 m; README)
NOISE = (7, 18)
# ------------------------------------------------------------------ added here
OBJ_H = 0.50                # [invented] a rise this tall or more is tested for an object
GROUND_MIN = 0.30           # [invented] ... and is ground (a bank) if this share of its outer side's returns is class 2
OBJ_W_MAX = 3.0             # [invented] a non-ground rise that comes back down within this is a vehicle or object
BACK_H = 0.30               # [invented] "back down": three bins in a row within this of the road line (walk level passes)
ROAD_RESUME = 0.8           # [invented] road follows an object: this share of the TREND_M past it within ROAD_LVL ...
ROAD_LVL = 0.08             # [invented] ... of the road line, with TREND_MIN bins or more
MAX_SKIP = 2                # [invented] objects (and islands) passed on one side at most
DIV_W_MAX = 2.5             # [invented] a rise that comes back down within this ...
DIV_BACK = 0.05             # [invented] ... to within this of the road line (three bins in a row) ...
LANE_M, DIV_ROAD = 3.0, 0.20   # [invented] ... with ROAD_RESUME of the next 3 m within 0.20 m of the road line (a carriageway
                            # with its own cross-fall): a raised divider or island inside the road (not declared), passed like
                            # an object with road behind it
START_IN = 2.0              # [invented] the road inside the search start: the bins START_IN..0.2 m inside it ...
START_H = 0.10              # [invented] ... if the first 0.3 m of the search stands this much over that road, the search began
START_MAX = 3.0             # [invented] on something raised: it moves out to where the profile is back at the road, within this
CANOPY_SHARE = 0.25         # [invented] canopy: this share of the returns within 3 m of the built edge are not last returns
MOUTH_HALF = {"service": 7.0, "other": 15.0}   # [invented] an OSM way meeting a side flags stations within this of it
MOUTH_ANGLE_DEG = 25.0      # [invented] ... if it meets the edge line at this angle or more (a carriageway runs along it)
MIN_N, MAX_IQR = 5, 1.0     # [invented] a 25 m bin is called with this many stations reading the quantity, IQR at most this
RUN_HALF_M, RUN_MIN = 12.5, 3   # [invented] station runs: the running median over readings within +-12.5 m, 3+ of them
NB_HALF_M, NB_MIN, NB_OFF = 12.5, 2, 0.5   # [invented] a face against its neighbours: the median of the other faces read
                            # on that side within +-12.5 m (2+ of them); "apart" if more than 0.5 m off it (a mouth, a bay, a misread)


def arg(i, env):
    if len(sys.argv) > i and not sys.argv[i].startswith("--"):
        return Path(sys.argv[i])
    if os.environ.get(env):
        return Path(os.environ[env])
    raise SystemExit(__doc__)


def opt(name, many=False):
    v = [sys.argv[i + 1] for i, a in enumerate(sys.argv[:-1]) if a == name]
    return v if many else (v[0] if v else None)


TDIR, TOOL, AIR, OUTD = arg(1, "NC_TILES"), arg(2, "NC_LM_TOOL"), arg(3, "NC_AIROSO"), arg(4, "NC_OUT")
PID = opt("--piece")
PRIORS = [Path(p) for p in opt("--prior", many=True)]
if PID not in ("A", "B", "C", "D"):
    raise SystemExit(__doc__)
sys.path.insert(0, str(TOOL))
sys.path.insert(0, str(AIR / "tools"))
import shrub_heights as SH  # noqa: E402  the lm-shrub tool: tile_list, chunks, Track (projection), mpd
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


def inr(s, ranges):
    return any(a - 1e-6 <= s <= b + 1e-6 for a, b in ranges)


doc, pieces = ep.load(LM / "data" / "expansion.north.json")
pc = pieces[PID]
origin = doc["frame"]["origin"]
S_PIECE = [round(float(v), 2) for v in pc.s]
cov = COVERED.get(PID, {}).get("s", [])
S_MAIN = [s for s in S_PIECE if not inr(s, cov)]
S_CHECK = [s for s in S_PIECE if inr(s, CHECK.get(PID, [])) and inr(s, cov)]
S_ALL = sorted(set(S_MAIN) | set(S_CHECK))
fchk = {}
nl = np.array([pc.frame(s)[2] for s in S_ALL])
tl = np.array([pc.frame(s)[1] for s in S_ALL])
fchk["travel_bearing_deg"] = {"min": r3(min(math.degrees(math.atan2(t[0], t[1])) % 360 for t in tl), 1),
                              "max": r3(max(math.degrees(math.atan2(t[0], t[1])) % 360 for t in tl), 1),
                              "what": "the piece's tangent along increasing s, degrees from north"}
fchk["left_normal_is_left"] = bool(np.allclose(nl[:, 0], -tl[:, 1]) and np.allclose(nl[:, 1], tl[:, 0]))
assert fchk["left_normal_is_left"]
RAISED = [m for m in doc["medians"] if m.get("piece") == PID and str(m.get("raised")) == "True"]


def search_from(s):
    """per side (+1 left, -1 right): where the outward search starts, and the raised island that set it"""
    of, why = {+1: OUTER_FROM, -1: OUTER_FROM}, {+1: None, -1: None}
    for m in RAISED:
        if m["s_from"] - 1e-6 <= s <= m["s_to"] + 1e-6:
            w, off = pc.num(s, "median_w_m"), pc.num(s, "median_off_m")
            if w <= 0:
                continue
            for side, face in ((+1, off + w / 2), (-1, off - w / 2)):
                if side * face + ISLAND_CLEAR > of[side]:
                    of[side], why[side] = side * face + ISLAND_CLEAR, m["id"]
    return of, why


# ------------------------------------------------------------------ junctions: the piece's pads / welds, OSM ways meeting a side
cuts = pc.cuts or {}


def junction_of(s):
    a, b = cuts.get("start"), cuts.get("end")
    if a and s < a["s"] - 1e-6:
        return f"{a['at']} ({a['kind']}, s < {a['s']})"
    if b and s > b["s"] + 1e-6:
        return f"{b['at']} ({b['kind']}, s > {b['s']})"
    return None


osm = json.loads((LM / "data" / "osm.expansion.json").read_text(encoding="utf-8"))
m_lon, m_lat = SH.mpd(origin["lat"])
PP = np.array(pc.P)
ptr = cKDTree(PP)
nid = list(osm["nodes"].keys())
nll = np.array([osm["nodes"][k] for k in nid], float)
nxz = np.c_[(nll[:, 0] - origin["lon"]) * m_lon, (nll[:, 1] - origin["lat"]) * m_lat]
dn, _ = ptr.query(nxz, k=1, distance_upper_bound=60.0)
near = {nid[i]: nxz[i] for i in np.flatnonzero(np.isfinite(dn))}
proj = {k: pc.project(*v) for k, v in near.items()}          # (distance, s, u)
MOUTHS = []
for wy in osm["ways"]:
    nds = [str(n) for n in wy["nodes"]]
    if not any(n in proj for n in nds):
        continue
    hw = wy.get("tags", {}).get("highway", "")
    for a, b in zip(nds[:-1], nds[1:]):
        if a not in proj or b not in proj:
            continue
        (_da, sa, ua), (_db, sb, ub) = proj[a], proj[b]
        if not (0.0 < sa < pc.length and 0.0 < sb < pc.length):
            continue
        for side, key in ((+1, "left_m"), (-1, "right_m")):
            fa, fb = ua - pc.num(sa, key), ub - pc.num(sb, key)
            if fa == fb or fa * fb > 0:
                continue
            t = fa / (fa - fb)
            sc = sa + (sb - sa) * t
            seg = math.hypot(sb - sa, ub - ua)
            ang = math.degrees(math.asin(min(1.0, abs(ub - ua) / seg))) if seg > 0 else 0.0
            if ang < MOUTH_ANGLE_DEG:
                continue
            MOUTHS.append({"side": "left" if side > 0 else "right", "s": r3(sc, 1), "angle_deg": r3(ang, 0), "way": wy["id"],
                           "name": wy.get("tags", {}).get("name"), "highway": hw,
                           "service": wy.get("tags", {}).get("service"),
                           "half_m": MOUTH_HALF["service" if hw == "service" else "other"]})
MOUTHS.sort(key=lambda m: (m["side"], m["s"]))


def mouths_at(s, side):
    return [m for m in MOUTHS if m["side"] == side and abs(m["s"] - s) <= m["half_m"]]


# ------------------------------------------------------------------ the corridor's returns (piece by piece, chunked, bbox first)
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
keep = {k: [] for k in ("x", "z", "elev", "cls", "wh", "last", "inten")}
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
        x, z = trk.to_local(X[ii], Y[ii], to_ll)
        keep["x"].append(np.asarray(x, float)); keep["z"].append(np.asarray(z, float))
        keep["elev"].append(np.asarray(p.z)[ii].astype(np.float64))
        keep["cls"].append(c.astype(np.uint8)); keep["wh"].append(np.asarray(p.withheld, bool)[ii])
        keep["last"].append(np.asarray(p.return_number)[ii] == np.asarray(p.number_of_returns)[ii])
        keep["inten"].append(np.asarray(p.intensity)[ii].astype(np.uint16))
        nk += len(ii)
        if "projection_round_trip_max_m" not in fchk:
            rE, rN = (np.asarray(v) for v in trk._utm(np.asarray(x[:5000]), np.asarray(z[:5000])))
            fchk["projection_round_trip_max_m"] = r3(float(np.max(np.hypot(rE - X[ii][:5000], rN - Y[ii][:5000]))), 4)
        del X, Y, p
    tiles_rep.append({"file": t["file"], "bytes": t["bytes"], "points": t["points"], "md5": md5(t["path"]), "kept": nk,
                      "kept_by_class": cls_t, "seconds": round(time.time() - tt, 1)})
    log(f"{t['file']}: {nk:,} kept")
L = {k: (np.concatenate(v) if v else np.zeros(0)) for k, v in keep.items()}
del keep
OK = ~L["wh"].astype(bool) & ~np.isin(L["cls"], NOISE)
GND = OK & (L["cls"] == 2)
LAST = OK & L["last"].astype(bool)
ptree = cKDTree(np.c_[L["x"], L["z"]]) if len(L["x"]) else None
log(f"piece {PID}: {len(S_MAIN)} stations + {len(S_CHECK)} check; corridor {len(L['x']):,} returns: class 2 {int(GND.sum()):,}, "
    f"last {int(LAST.sum()):,}, withheld {int(L['wh'].sum())}; {len(MOUTHS)} OSM mouths")


# ------------------------------------------------------------------ the edge finder (jackson_curbs_g10.py's, extended)
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


def start_on_raised(u, z, ofrom):
    """if the search would begin on something raised (an undeclared divider straddling ofrom, or an island off its
    declared place), the u where the profile is back at the road inside it; else None"""
    def prof(a, b):
        m = (u >= a) & (u < b)
        if m.sum() < 20:
            return None, None
        bi = np.floor((u[m] - a) / BIN).astype(int)
        cen_, q_ = [], []
        for k_ in np.unique(bi):
            zz_ = z[m][bi == k_]
            cen_.append(a + (k_ + 0.5) * BIN)
            q_.append(np.percentile(zz_, OUT_Q))
        return np.array(cen_), np.array(q_)
    ci, qi = prof(max(0.0, ofrom - START_IN), ofrom - 0.2)
    co, qo = prof(ofrom, ofrom + START_MAX + 0.5)
    if ci is None or co is None or len(ci) < 6:
        return None
    rl = np.polyfit(ci, qi, 1) if np.ptp(ci) > 0.5 else (0.0, float(np.median(qi)))
    first = co < ofrom + 0.3
    if first.sum() < 2 or np.median(qo[first] - np.polyval(rl, co[first])) < START_H:
        return None
    back = (qo - np.polyval(rl, co)) <= 0.05
    for j in range(len(co) - 2):
        if co[j] >= ofrom + 0.3 and back[j] and back[j + 1] and back[j + 2] and co[j + 2] - co[j] <= 0.5:
            return float(co[j] - BIN / 2)
    return None


def edge(l, z, inten, g2, side, ofrom):
    """one side's outer face (side +1 left, -1 right), searched outward from ofrom"""
    u = side * l
    moved = start_on_raised(u, z, ofrom)
    if moved is not None:
        ofrom0, ofrom = ofrom, moved
    m = (u >= ofrom) & (u <= HALF_ACROSS)
    u, z, inten, g2 = u[m], z[m], inten[m], g2[m]
    rec = {"n_window": int(len(u)), "search_from_m": r3(ofrom, 2)}
    if moved is not None:
        rec["search_from_moved"] = {"from_m": r3(ofrom0, 2), "to_m": r3(ofrom, 2),
                                    "why": "the search began on something raised (a divider or island); moved to where the road resumes"}
    if len(u) < N_WIN:
        rec.update(verdict="unclear", type=None, reason="sparse" if len(u) else "no returns")
        return rec
    nb = int(round((HALF_ACROSS - ofrom) / BIN))
    bi = np.clip(np.floor((u - ofrom) / BIN).astype(int), 0, nb - 1)
    bq = np.full(nb, np.nan)
    o = np.argsort(bi)
    bs, zs = bi[o], z[o]
    st = np.r_[0, np.flatnonzero(np.diff(bs)) + 1]
    for a_, b_ in zip(st, np.r_[st[1:], len(bs)]):
        bq[bs[a_]] = np.percentile(zs[a_:b_], OUT_Q)
    cen = ofrom + (np.arange(nb) + 0.5) * BIN
    fb = np.isfinite(bq)
    edges = ofrom + np.arange(nb + 1) * BIN
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
            rec.update(verdict="none", type=None, reason=f"no rise or drop over {NONE_MAX} m from {ofrom:.2f} to {HALF_ACROSS} m out")
        else:
            rec.update(verdict="unclear", type=None, reason="no rise past %.2f m or drop past %.2f m%s" % (
                CURB_DET, DROP_DET, "" if mx is None else "; largest |D| %.3f" % mx))
        return rec
    road0 = float(np.median(bq[fb & (cen <= ofrom + 1.5)])) if (fb & (cen <= ofrom + 1.5)).sum() >= 5 else None

    def lines(x0, floor_):
        mr_ = fb & (cen >= max(x0 - ROAD_M, floor_)) & (cen <= x0 - GUARD)
        mw_ = fb & (cen >= x0 + GUARD) & (cen <= x0 + WALK_M)
        return linfit(cen[mr_], bq[mr_], 4), linfit(cen[mw_], bq[mw_], 4), int(mw_.sum())

    def object_end(x0, rl, back=BACK_H, wmax=OBJ_W_MAX):
        """a rise that comes back down: the u where three bins in a row stand within back of the road line, within wmax"""
        idx = np.flatnonzero(fb & (cen > x0 + 0.2) & (cen <= x0 + wmax + 0.3))
        lowb = (bq[idx] - ev(rl, cen[idx])) <= back
        for j in range(len(idx) - 2):
            if lowb[j] and lowb[j + 1] and lowb[j + 2] and cen[idx[j + 2]] - cen[idx[j]] <= 0.5:
                return float(cen[idx[j]] - BIN / 2)
        return None

    def try_face(e0, floor_):
        r = {}
        rise = D[e0] > 0
        seg = D[e0:e0 + int(round(0.5 / BIN)) + 1]
        j = int(np.nanargmax(seg)) if rise else int(np.nanargmin(seg))
        x0 = float(edges[e0 + j])
        r["detector_m"] = r3(D[e0 + j])
        unc = wrong = nf = None
        for _it in range(2):
            rl, wl, nw = lines(x0, floor_)
            if rl is None or wl is None:
                r.update(verdict="unclear", type=None, reason="no returns on the road or the outer side")
                return r
            top = max(ev(rl, x0), ev(wl, x0)) + 0.10
            wf = (u >= max(x0 - FACE_WIN, floor_)) & (u <= x0 + FACE_WIN) & (z <= top)
            if wf.sum() < 2:
                break
            hi = z[wf] > 0.5 * (ev(rl, u[wf]) + ev(wl, u[wf]))
            x0, unc, wrong, nf = (float(v) for v in face_interval(u[wf], hi, high_inside=not rise))
            wrong, nf = int(wrong), int(nf)
        rl, wl, nw = lines(x0, floor_)
        if rl is None or wl is None:
            r.update(verdict="unclear", type=None, reason="no returns on the road or the outer side")
            return r
        step = ev(wl, x0) - ev(rl, x0)
        ii_, io_ = (u >= x0 - INT_M) & (u < x0), (u > x0) & (u <= x0 + INT_M)
        ow = (u >= x0 + GUARD) & (u <= x0 + WALK_M)
        gshare = float(g2[ow].mean()) if ow.any() else None
        r.update(face_u_m=r3(side * x0), unc_m=r3(unc), step_m=r3(step), outer_bins=nw, face_points=nf, face_wrong_side=wrong,
                 outer_slope=r3(wl[0], 4), road_slope=r3(rl[0], 4), outer_class2_share=r3(gshare, 2),
                 road_side_over_road_near_line_m=(None if road0 is None else r3(ev(rl, x0) - road0)),
                 intensity_inside=r3(np.median(inten[ii_]), 0) if ii_.any() else None,
                 intensity_outside=r3(np.median(inten[io_]), 0) if io_.any() else None)
        if road0 is not None and abs(ev(rl, x0) - road0) > ROAD_TOL:
            r.update(verdict="unclear", type=None, reason="the road side stands %+.2f m off the road near the line (canopy)" % (ev(rl, x0) - road0),
                     cant="canopy")
            return r
        if rise and step >= CURB_LO:
            # anything raised that comes back down to the road within DIV_W_MAX, with a lane's worth of road past it, stands
            # inside the road (an undeclared divider or island, a narrow post line, a car in a lane): passed
            far = object_end(x0, rl, DIV_BACK, DIV_W_MAX)
            if far is not None:
                pi = fb & (cen >= far) & (cen < far + LANE_M)
                lane = np.abs(bq[pi] - ev(rl, cen[pi])) <= DIV_ROAD
                if pi.sum() >= int(0.6 * LANE_M / BIN) and lane.mean() >= ROAD_RESUME:
                    kind = "raised divider or island" if step <= CURB_HI else "vehicle or object"
                    r.update(verdict="object", type=None, cant="island" if step <= CURB_HI else "vehicle",
                             object={"kind": kind, "u_from_m": r3(side * x0, 2), "u_to_m": r3(side * far, 2),
                                     "across_m": r3(far - x0, 2), "height_m": r3(step, 2), "class2_share": r3(gshare, 2),
                                     "road_follows": True},
                             reason="a rise (%.2f m) that comes back down to the road within %.1f m, road past it: %s"
                                    % (step, far - x0, kind))
                    r["_far"], r["_resumes"] = far, True
                    return r
        if rise and step >= OBJ_H and gshare is not None and gshare < GROUND_MIN:
            far = object_end(x0, rl)
            if far is not None:
                pi = fb & (cen >= far) & (cen < far + TREND_M)
                at_road = np.abs(bq[pi] - ev(rl, cen[pi])) <= ROAD_LVL
                resumes = bool(pi.sum() >= TREND_MIN and at_road.mean() >= ROAD_RESUME)
                r.update(verdict="object", type=None, cant="vehicle",
                         object={"kind": "vehicle or object", "u_from_m": r3(side * x0, 2), "u_to_m": r3(side * far, 2), "across_m": r3(far - x0, 2),
                                 "height_m": r3(step, 2), "class2_share": r3(gshare, 2), "road_follows": resumes},
                         reason="a non-ground rise %.2f m tall, %.1f m across (a parked car, vehicle or object)" % (step, far - x0))
                r["_far"], r["_resumes"] = far, resumes
                return r
        if nw < N_WALK_BINS:
            r.update(verdict="unclear", type=None, reason=f"{nw} bins on the outer side")
        elif rise and CURB_LO <= step <= CURB_HI:
            r.update(verdict="face", type="curb", reason="")
        elif rise and step > CURB_HI:
            what = ("ground (bank)" if gshare is not None and gshare >= GROUND_MIN else
                    "non-ground (a wall, hedge, fence or building)")
            r.update(verdict="face", type="edge (rise)", what=what, reason="a wall, bank or hedge where the asphalt ends")
        elif not rise and step <= -DROP_DET:
            r.update(verdict="face", type="edge (drop)", reason="the ground falls away past the asphalt")
        else:
            r.update(verdict="unclear", type=None, reason=f"step {step:+.3f} m ({'rise' if rise else 'drop'}) out of bounds")
        return r

    # the first candidate outward; if it gives no face, the next ones within CONT_M of it (a gutter's lip before its curb);
    # past an object with road behind it, the search starts again (its trend window wholly past the object)
    first, tried, floor_, objects = None, [], ofrom, []
    for e0 in cand:
        if edges[e0] - TREND_M < floor_ - 1e-9 and floor_ > ofrom:
            continue
        if tried and edges[e0] - edges[tried[0]] > CONT_M:
            break
        if tried and edges[e0] - edges[tried[-1]] < 0.3:
            continue
        tried.append(e0)
        r = try_face(e0, floor_)
        if r["verdict"] == "object":
            objects.append(r["object"])
            if r["_resumes"] and len(objects) <= MAX_SKIP:
                floor_, tried, first = r["_far"], [], None
                continue
            if first is not None:        # a candidate before it (within CONT_M) gave no face: that one's reason stands
                rec.update(first, objects=objects)
                return rec
            r = {k: v for k, v in r.items() if not k.startswith("_")}
            r["verdict"] = "unclear"
            rec.update(r, objects=objects)
            return rec
        if first is None:
            first = r
        if r["verdict"] == "face":
            if len(tried) > 1:
                r["note"] = "the first candidate (%.2f m) gave no face: %s" % (side * edges[tried[0]], first.get("reason"))
            if objects:
                r["past_objects"] = True
            rec.update(r)
            if objects:
                rec["objects"] = objects
            return rec
    if first is None:     # past an object, no candidate left
        isl = all(o_.get("kind") == "raised divider or island" for o_ in objects)
        rec.update(verdict="unclear", type=None, cant="island" if isl else "vehicle", objects=objects,
                   reason="a raised divider or island" if isl else "a non-ground object with road behind it, and no face past it")
        return rec
    rec.update(first)
    if objects:
        rec["objects"] = objects
    return rec


def category(e, s, side, canopy_share):
    """the one can't-call category of a side that gives no face"""
    if e["verdict"] == "face":
        return None
    if e.get("n_window", 0) == 0:
        return "outside the tiles"
    j = junction_of(s)
    if j:
        return "junction " + j
    mo = mouths_at(s, side)
    if mo:
        return "junction mouth (OSM %s)" % ", ".join(sorted({(m["name"] or (m["highway"] + (" " + m["service"] if m["service"] else ""))) for m in mo}))
    if e.get("cant") == "vehicle":
        return "vehicle (parked car, traffic or object)"
    if e.get("cant") == "island":
        return "raised divider or island, no face past it"
    if e.get("cant") == "canopy" or (canopy_share is not None and canopy_share >= CANOPY_SHARE):
        return "canopy"
    if e["verdict"] == "none":
        return "no rise or drop (flush edge or unmapped driveway)"
    if e.get("reason") in ("sparse", "no returns"):
        return "sparse"
    return "step out of bounds"


def measure(s):
    (px, pz), t, n = pc.frame(s)
    bl, br = pc.num(s, "left_m"), pc.num(s, "right_m")
    of, ofwhy = search_from(s)
    row = {"s": s, "built": {"left_m": r3(bl, 2), "right_m": r3(br, 2), "middle_m": r3(0.5 * (bl + br), 3), "width_m": r3(bl - br, 2)}}
    ii = np.array(ptree.query_ball_point([px, pz], R), dtype=np.int64) if ptree is not None else np.zeros(0, np.int64)
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
    inten = L["inten"][ii].astype(float)
    g2 = (L["cls"][ii] == 2).astype(float)
    for nm, side, be in (("left", +1, bl), ("right", -1, br)):
        e = edge(la[lr], zc[lr], inten[lr], g2[lr], side, of[side])
        if ofwhy[side]:
            e["search_from_set_by"] = f"raised median {ofwhy[side]} (declared face + {ISLAND_CLEAR} m)"
        near_e = ok & (np.abs(side * la - side * be) <= 3.0)
        cs = float((~L["last"][ii][near_e].astype(bool)).mean()) if near_e.sum() >= 20 else None
        e["not_last_share_near_built_edge"] = r3(cs, 2)
        mo = mouths_at(s, nm)
        if mo:
            e["osm_mouths"] = [{k: m_[k] for k in ("way", "name", "highway", "service", "s")} for m_ in mo]
        e["cant_call"] = category(e, s, nm, cs)
        row[nm] = e
    left, right = row["left"], row["right"]
    if junction_of(s):
        row["junction"] = junction_of(s)
    row["counts"] = {"returns": int(ok.sum()), "last_returns": int(lr.sum()), "class_2": int(g.sum())}
    row["grade"] = {"along": r3(grade, 4), "from": gsrc}
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
    row["road_at_line_minus_y3dep_m"] = (r3(float(np.percentile(zc[road0], OUT_Q)) - float(origin["elev_m"]) - pc.num(s, "y_3dep"))
                                         if road0.sum() >= 5 else None)
    return row


rows = {s: measure(s) for s in S_ALL}
log("stations measured", len(rows))
for _sd in ("left", "right"):
    _f = [(s, rows[s][_sd]["face_u_m"]) for s in S_ALL if rows[s][_sd]["verdict"] == "face"]
    for s, fu in _f:
        nb_ = [v for s2, v in _f if s2 != s and abs(s2 - s) <= NB_HALF_M + 1e-6]
        if len(nb_) >= NB_MIN:
            rows[s][_sd]["minus_neighbours_m"] = r3(fu - float(np.median(nb_)))
for s in S_ALL:
    r = rows[s]
    f = lambda e: "%-11s %s" % ((e["type"] or e["verdict"])[:11], ("%+6.2f/%+.3f" % (e["face_u_m"], e["step_m"])) if e.get("face_u_m") is not None else "--")  # noqa: E731
    print(f"  {s:7.1f}{'*' if s in S_CHECK else ' '} L {f(r['left'])}  R {f(r['right'])}  built {r['built']['left_m']:+.2f}/{r['built']['right_m']:+.2f}"
          f"  real-built L {r.get('left_minus_built_m')} R {r.get('right_minus_built_m')} mid {r.get('real_minus_built_middle_m')}"
          f"  | {r['left']['cant_call'] or ''} / {r['right']['cant_call'] or ''}", flush=True)


# ------------------------------------------------------------------ summaries (over S_MAIN; the check stations apart)
QTY = {"left": "left_minus_built_m", "right": "right_minus_built_m", "middle": "real_minus_built_middle_m",
       "width": "real_minus_built_width_m"}


def runs(ss, pred):
    out, cur = [], None
    for s in ss:
        if pred(rows[s]):
            if cur and 0 < s - cur[1] <= 2.5 + 1e-6:
                cur[1] = s
            else:
                cur = [s, s]
                out.append(cur)
        else:
            cur = None
    return out


def runs_by(ss, key):
    """runs of consecutive stations with the same non-None key(row)"""
    out = []
    for s in ss:
        v = key(rows[s])
        if v is None:
            continue
        if out and out[-1]["what"] == v and 0 < s - out[-1]["s"][1] <= 2.5 + 1e-6:
            out[-1]["s"][1] = s
            out[-1]["stations"] += 1
        else:
            out.append({"what": v, "s": [s, s], "stations": 1})
    return out


def types(ss, side):
    out = {}
    for s in ss:
        e = rows[s][side]
        k = e["type"] or e["verdict"]
        out[k] = out.get(k, 0) + 1
    return out


def bins_of(ss):
    out = {}
    for s in ss:
        out.setdefault(int(math.floor(s / BIN_SUM_M + 1e-9)), []).append(s)
    return [out[k] for k in sorted(out)]


per = []
for sb in bins_of(S_MAIN):
    b0 = math.floor(sb[0] / BIN_SUM_M + 1e-9) * BIN_SUM_M
    both = [s for s in sb if rows[s].get("real_minus_built_middle_m") is not None]
    e = {"bin": [b0, b0 + BIN_SUM_M], "s": [sb[0], sb[-1]], "stations": len(sb),
         "stations_left_face": sum(1 for s in sb if rows[s]["left"]["verdict"] == "face"),
         "stations_right_face": sum(1 for s in sb if rows[s]["right"]["verdict"] == "face"),
         "stations_both_faces": len(both)}
    for q, key in QTY.items():
        e[key] = rng([rows[s].get(key) for s in sb])
        v = e[key]
        if v is None or v["n"] < MIN_N:
            e[f"{q}_call"] = f"can't call: {0 if v is None else v['n']} stations (wants {MIN_N})"
        elif v["iqr"] > MAX_IQR:
            e[f"{q}_call"] = f"can't call: the stations disagree (IQR {v['iqr']:.2f} m over {MAX_IQR})"
        else:
            e[f"{q}_call"] = "ok"
    e["built_middle_m"] = rng([rows[s]["built"]["middle_m"] for s in sb])
    e["built_width_m"] = rng([rows[s]["built"]["width_m"] for s in sb])
    e["real_width_m"] = rng([rows[s].get("real_width_m") for s in sb])
    e["left_types"], e["right_types"] = types(sb, "left"), types(sb, "right")
    e["cant_call"] = {side: runs_by(sb, lambda r, side=side: r[side]["cant_call"]) for side in ("left", "right")}
    per.append(e)


def bin_runs(q, pred):
    """consecutive called 25 m bins whose median satisfies pred: s range, the bins' medians' range, the stations' median"""
    key = QTY[q]
    out = []
    for e in per:
        ok_ = e[f"{q}_call"] == "ok" and pred(e[key]["median"])
        if not ok_:
            continue
        if out and abs(e["bin"][0] - out[-1]["bin"][1]) < 1e-6:
            o_ = out[-1]
            o_["bin"][1] = e["bin"][1]
            o_["s"][1] = e["s"][1]
            o_["bins"] += 1
            o_["_med"].append(e[key]["median"])
            o_["_ss"] += [s for s in S_MAIN if e["s"][0] <= s <= e["s"][1]]
        else:
            out.append({"bin": list(e["bin"]), "s": list(e["s"]), "bins": 1, "_med": [e[key]["median"]],
                        "_ss": [s for s in S_MAIN if e["s"][0] <= s <= e["s"][1]]})
    for o_ in out:
        v = [rows[s].get(key) for s in o_.pop("_ss")]
        m_ = o_.pop("_med")
        o_["bin_medians_m"] = [r3(min(m_)), r3(max(m_))]
        o_["stations_median_m"] = r3(np.median([x for x in v if x is not None]))
        o_["stations_n"] = sum(1 for x in v if x is not None)
    return out


def station_runs(q, pred):
    """per station the running median of the quantity over readings within +-RUN_HALF_M (RUN_MIN+ of them); runs of
    consecutive stations where it satisfies pred. Finer than the 25 m bins, and blind to their edges"""
    key = QTY[q]
    sv = [(s, rows[s].get(key)) for s in S_MAIN]
    rd = [(s, v) for s, v in sv if v is not None]
    out, cur = [], None
    for s, _v in sv:
        w_ = [v for s2, v in rd if abs(s2 - s) <= RUN_HALF_M + 1e-6]
        rm = float(np.median(w_)) if len(w_) >= RUN_MIN else None
        if rm is not None and pred(rm):
            if cur and 0 < s - cur["s"][1] <= 2.5 + 1e-6:
                cur["s"][1] = s
                cur["_rm"].append(rm)
            else:
                cur = {"s": [s, s], "_rm": [rm]}
                out.append(cur)
        else:
            cur = None
    keep_ = []
    for o_ in out:
        rm = o_.pop("_rm")
        v = [x for s2, x in rd if o_["s"][0] - 1e-6 <= s2 <= o_["s"][1] + 1e-6]
        o_.update(stations=len(rm), readings=len(v), readings_median_m=r3(np.median(v)) if v else None,
                  running_median_m=[r3(min(rm)), r3(max(rm))])
        if len(rm) >= 3 and len(v) >= RUN_MIN:
            keep_.append(o_)
    return keep_


def tally(ss, side):
    out = {}
    for s in ss:
        c = rows[s][side]["cant_call"]
        if c:
            c = c.split(" (")[0] if c.startswith("junction mouth") else c
            out[c] = out.get(c, 0) + 1
    return out


summary = {
    "stations": len(S_MAIN), "s": [S_MAIN[0], S_MAIN[-1]] if S_MAIN else None,
    "stations_left_face": sum(1 for s in S_MAIN if rows[s]["left"]["verdict"] == "face"),
    "stations_right_face": sum(1 for s in S_MAIN if rows[s]["right"]["verdict"] == "face"),
    "stations_both_faces": sum(1 for s in S_MAIN if rows[s].get("real_minus_built_middle_m") is not None),
    "left_types": types(S_MAIN, "left"), "right_types": types(S_MAIN, "right"),
    "whole": {key: rng([rows[s].get(key) for s in S_MAIN]) for key in QTY.values()},
    "built_off_over_1m": {q: bin_runs(q, lambda v: abs(v) > OFF_M) for q in QTY},
    "built_within_0_3m": {q: bin_runs(q, lambda v: abs(v) < CLOSE_M) for q in QTY},
    "station_runs_off_over_1m": {q: station_runs(q, lambda v: abs(v) > OFF_M) for q in QTY},
    "station_runs_within_0_3m": {q: station_runs(q, lambda v: abs(v) < CLOSE_M) for q in QTY},
    "bins": {"total": len(per), **{f"{q}_called": sum(1 for e in per if e[f"{q}_call"] == "ok") for q in QTY}},
    "unmeasured": {side: {"stations": sum(1 for s in S_MAIN if rows[s][side]["verdict"] != "face"),
                          "share": r3(sum(1 for s in S_MAIN if rows[s][side]["verdict"] != "face") / max(1, len(S_MAIN)), 3),
                          "by_category": tally(S_MAIN, side)} for side in ("left", "right")},
    "cant_call_runs": {side: [x for x in runs_by(S_MAIN, lambda r, side=side: r[side]["cant_call"]) if x["stations"] >= 2]
                       for side in ("left", "right")},
    "objects_passed": {k: sum(1 for s in S_MAIN for sd in ("left", "right") if rows[s][sd].get("past_objects")
                              and any(o_.get("kind") == k for o_ in rows[s][sd].get("objects", [])))
                       for k in ("vehicle or object", "raised divider or island")},
    "faces_apart_from_neighbours": {sd: {"apart": sum(1 for s in S_MAIN if abs(rows[s][sd].get("minus_neighbours_m") or 0) > NB_OFF),
                                         "checked": sum(1 for s in S_MAIN if rows[s][sd].get("minus_neighbours_m") is not None),
                                         "s": [s for s in S_MAIN if abs(rows[s][sd].get("minus_neighbours_m") or 0) > NB_OFF]}
                                    for sd in ("left", "right")},
    "search_starts_moved": {sd: sum(1 for s in S_MAIN if rows[s][sd].get("search_from_moved")) for sd in ("left", "right")},
    "curb_step_m": {sd: rng([rows[s][sd]["step_m"] for s in S_MAIN if rows[s][sd].get("type") == "curb"]) for sd in ("left", "right")},
    "_doc": ("over the stations this file measured (not the check stations). A 25 m bin is called for a quantity with "
             f"{MIN_N}+ stations reading it and their IQR at most {MAX_IQR} m. built_off_over_1m / built_within_0_3m: runs of "
             "consecutive called bins whose median real-minus-built is over 1 m / under 0.3 m in size; bin_medians_m the "
             "range of those bins' medians, stations_median_m the median over the run's stations. station_runs_*: per "
             f"station the running median of the readings within +-{RUN_HALF_M} m ({RUN_MIN}+ of them), runs of consecutive "
             "stations where it is over 1 m / under 0.3 m in size (finer than the bins). unmeasured: stations "
             "whose side gives no face, by can't-call category (junction mouth names in the stations and per_25m)."),
}
v3 = [rows[s]["road_at_line_minus_y3dep_m"] for s in S_ALL if rows[s]["road_at_line_minus_y3dep_m"] is not None]
fchk["road_at_line_minus_y3dep_m"] = {"what": "the lidar road within 0.5 m of the piece's line (last returns, OUT_Q percentile, "
                                      "grade out) minus the row's y_3dep, engine y", "median": r3(np.median(v3)) if v3 else None,
                                      "n": len(v3)}


# ------------------------------------------------------------------ the overlap check against earlier files
def prior_faces(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    lists = [d.get("stations", [])] + [d.get("check_stations", [])]
    for lst in lists:
        for r in lst:
            if isinstance(r, list):
                r = dict(zip(d["columns"], r))
            s = float(r["s"])
            if "left" in r and isinstance(r["left"], dict):          # jackson_curbs_g10.py
                f = {sd: (r[sd]["face_u_m"] if r[sd]["verdict"] == "face" else None, r[sd].get("type") or r[sd]["verdict"])
                     for sd in ("left", "right")}
            else:                                                    # mg_median_faces_g10.py (outer curbs)
                f = {sd: (r.get(f"{sd}_outer_face_m") if r.get(f"{sd}_outer_verdict") in ("curb", "edge") else None,
                          r.get(f"{sd}_outer_verdict")) for sd in ("left", "right")}
            out.setdefault(s, f)
    return d.get("tool", Path(path).name), out


overlap = []
for p in PRIORS:
    tool, pf = prior_faces(p)
    cmp_ = []
    for s in S_ALL:
        if s not in pf:
            continue
        for sd in ("left", "right"):
            a, (b, bt) = rows[s][sd], pf[s][sd]
            cmp_.append({"s": s, "side": sd, "this": a.get("face_u_m") if a["verdict"] == "face" else None,
                         "this_type": a["type"] or a["verdict"], "earlier": b, "earlier_type": bt,
                         "this_minus_earlier_m": (r3(a["face_u_m"] - b) if a["verdict"] == "face" and b is not None else None)})
    dd = [c["this_minus_earlier_m"] for c in cmp_ if c["this_minus_earlier_m"] is not None]
    overlap.append({"file": Path(p).name, "tool": tool, "sides_compared": len(cmp_), "both_read": len(dd),
                    "this_minus_earlier_m": rng(dd),
                    "within_0_10_m": sum(1 for x in dd if abs(x) <= 0.10),
                    "only_this_reads": sum(1 for c in cmp_ if c["this"] is not None and c["earlier"] is None),
                    "only_earlier_reads": sum(1 for c in cmp_ if c["this"] is None and c["earlier"] is not None),
                    "rows": cmp_})

settings = {k: globals()[k] for k in ("BIN_SUM_M", "OFF_M", "CLOSE_M", "HALF_ALONG", "HALF_ACROSS", "OUTER_FROM", "ISLAND_CLEAR",
                                      "BIN", "W", "MIN_BINS", "OUT_Q", "CURB_DET", "DROP_DET", "NONE_MAX", "CURB_LO", "CURB_HI",
                                      "GUARD", "ROAD_M", "WALK_M", "FACE_WIN", "N_WIN", "N_WALK_BINS", "TREND_M", "TREND_MIN",
                                      "INT_M", "ROAD_TOL", "CONT_M", "OBJ_H", "GROUND_MIN", "OBJ_W_MAX", "BACK_H", "ROAD_RESUME",
                                      "ROAD_LVL", "MAX_SKIP", "DIV_W_MAX", "DIV_BACK", "LANE_M", "DIV_ROAD", "START_IN", "START_H", "START_MAX", "NB_HALF_M", "NB_MIN", "NB_OFF", "CANOPY_SHARE", "MOUTH_HALF", "MOUTH_ANGLE_DEG", "MIN_N", "MAX_IQR",
                                      "RUN_HALF_M", "RUN_MIN")}
inputs = {str(p.relative_to(AIR)): md5(p) for p in (AIR / "tools" / "expansion_pieces.py", LM / "data" / "expansion.north.json",
                                                   LM / "data" / "centerline.local.json", LM / "data" / "osm.expansion.json")}
inputs["lm-shrub tool shrub_heights.py"] = md5(Path(SH.__file__))
for p in PRIORS:
    inputs["prior " + p.name] = md5(p)
out = {
    "_doc": (f"Lake Murray north piece {PID} ({pc.rec['name']}, {pc.rec['road']}): the road's two outer edges per station off "
             "the USGS 2024 lidar (north_curbs_g10.py; the method is its docstring), against the built edges. u = metres off "
             "the piece's line, + = left of travel along increasing s. left / right: verdict face / none / unclear; type curb, "
             "edge (rise) or edge (drop); face_u_m, unc_m (half the interval between the neighbouring returns the face lies "
             "between), step_m (outer - road at the face; negative for a drop); cant_call: why a side gives no face. built = "
             "the piece's own row (left_m, right_m; middle their mean, width their difference). real_middle_m / real_width_m "
             "from the two faces; *_minus_built_m = real minus built. Settings marked [invented] in the script are the "
             "method's choices, not measurements."),
    "status": "measured", "tool": "north_curbs_g10.py (G10 job lm-north-curbs-20261124)", "date": time.strftime("%Y-%m-%d"),
    "piece": {"id": PID, "name": pc.rec["name"], "road": pc.rec["road"], "from": pc.rec["from"], "to": pc.rec["to"],
              "length_m": pc.rec["length_m"], "cuts": cuts},
    "coverage": {"stations_in_piece": len(S_PIECE), "measured_here": len(S_MAIN),
                 "measured_here_s": runs(S_MAIN, lambda r: True) if S_MAIN else [],
                 "already_measured_s": cov, "already_measured_in": COVERED.get(PID, {}).get("files"),
                 "check_stations": len(S_CHECK), "check_s": runs(S_CHECK, lambda r: True) if S_CHECK else []},
    "source": {"project": "USGS_LPC_CA_SanDiegoCo_D24", "epsg": epsg, "flown": "2024-11 (lm-shrub tiles.json)", "tiles_read": tiles_rep},
    "inputs_md5": inputs,
    "frame": {"piece": f"{PID} {pc.rec['name']} (tools/expansion_pieces.Piece.frame)", "origin": origin,
              "projection": "shrub_heights.Track.to_local: pyproj EPSG %d -> 4326 ('%s', stated accuracy %s m), then the "
                            "WGS84 metres-per-degree series at the origin" % (epsg, to_ll.description, to_ll.accuracy),
              "checks": fchk},
    "raised_medians": [{"id": m["id"], "s": [m["s_from"], m["s_to"]], "type": m["type"]} for m in RAISED],
    "osm_mouths": MOUTHS,
    "settings": settings, "summary": summary, "per_25m": per, "overlap_check": overlap,
    "stations": [rows[s] for s in S_MAIN],
    "check_stations": [rows[s] for s in S_CHECK]}


def dump(o, **kw):
    return json.dumps(o, ensure_ascii=False, default=lambda v: v.tolist() if hasattr(v, "tolist") else str(v), **kw)


def rows_txt(lst):
    return "[\n" + ",\n".join("  " + dump(r, separators=(",", ":")) for r in lst) + "\n ]" if lst else "[]"


head = {k: v for k, v in out.items() if k not in ("stations", "check_stations")}
txt = (dump(head, indent=1)[:-2] + ',\n "stations": ' + rows_txt(out["stations"]) + ',\n "check_stations": '
       + rows_txt(out["check_stations"]) + "\n}\n")
json.loads(txt)
OUTP = OUTD / f"north_curbs_{PID}.lidar.g10.json"
OUTD.mkdir(parents=True, exist_ok=True)
OUTP.write_text(txt, encoding="utf-8")
log("written", OUTP)
