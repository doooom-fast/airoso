"""The readable intermediate of the Lake Murray north network (ledger 0054, EXPANSION-PLAN P1 steps 1-2).

Kevin, 2026-10-12: "we're going to expand college down waring to princess view, princess view to mission gorge,
and mission gorge to jackson, then extend jackson down to mission gorge" / "the new loop will connect to the old
one". This tool writes what Claude authors BEFORE any mesh: a plain-text description of the new roads that the map
(tools/plot_expansion_plan.py), the weld rehearsal and P3's route_connectors read. Nothing here is a mesh.

    python tools/author_expansion.py [--track <tracks/san-diego-lake-murray>] [--offline]

Writes <track>/data/expansion.north.json and caches every 3DEP sample it reads in
<track>/data/expansion.north.samples.json.gz (provenance inside; --offline refuses to fetch).

WHAT IT DESCRIBES (local frame of data/centerline.local.json: x east, y up over origin.elev_m, z north; stations s in
metres from the junction node at the start of each leg along the OSM forward leg — EXPANSION-PLAN "Stations"):

  pieces    A Waring (J1->J2), B Princess View (J2->J3), C Mission Gorge (J3->J4), D Jackson north (J4->J5): a
            centreline every SPACING_M m — on the divided stretches the midline between the two OSM carriageways
            (airoso data/routes.json `north`, fwd and rev), smoothed (SMOOTH_SIGMA_M) and checked against the raw
            midline (V1: p95 <= 1.5 m); per station the left / right curb offsets (+ = left of the forward direction)
            interpolated between the aerial eye readings (source/expansion/aerial__widths_eye.csv, A3), the median
            (width, offset, type: planted / terracotta / nose / painted / hatched / line / none) and the lanes OSM
            tags, plus the 3DEP height at the station and the profile the connector smoothing would give it
  medians   one polygon per run of a raised or painted type (numbered MD1..), noses NOSE_M long, gapped at the
            two Mission Gorge crossovers, clear of every pad and weld by NOSE_CLEAR_M
  pads      J2, J3, J4 (A4): every arm (the two route pieces + the see-only stubs, A1) as a straight curb pair, every
            corner a true arc at the measured curb-return radius, every arm cut straight PAD_CUT_PAD_M past its
            farther tangent point; the outline is one closed polygon
  welds     J1 and J5 (A4/A5): ribbon-through, the loop untouched; the new road's two curb lines carried onto the
            loop's OUTER (L) edge, with the measured curb returns (J1 NE R 30, J5 SW R 10) and J5's NE curb eased
            onto the loop edge where it runs on as Jackson south's east curb; the opening on the loop edge as
            fractional mainline vertices (A5: J1 v1513.5-~1528.5, J5 v2312-~2322); and `connector`, the weld stub
            in route_connectors' connector form (centre + width per point, flared to the returns) that the P1
            rehearsal feeds the chain and P3 extends to the whole piece
  stubs     S1..S6, the see-only arms at J2-J4 (A1, JUNCTIONS rule 18c): the mouth line on the pad cut, a short
            pavement and an invisible wall across the mouth line
  stations  the aerial width stations (numbered 1..), with the built-width the interpolation gives there
  checks    V1 midline deviation; the 11 % grade cap (route_connectors MAX_GRADE) must bind nowhere; junction
            heights vs revise/measure.json; cross-sections (3DEP ground minus the road centre) every 10 m over the
            first / last 100 m of every leg end (P1 step 2: the terrain lens measured only the mid-legs)

Numbers marked [authored] are Claude's choices where no measurement exists (fleet/GATES-CHANGELOG.md 2026-10-14 P1);
everything else is read from the data named beside it. TLS verification is always on (scripts.tls via usgs_3dep).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import sys
import time
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))

TRACK_DEFAULT = AIROSO / "tracks" / "san-diego-lake-murray"
VERSION = 1

SPACING_M = 2.5            # P1: "a centreline at 2-3 m spacing"
SMOOTH_SIGMA_M = 4.0       # [authored] Gaussian plan smoothing of the raw OSM midline (OSM polylines kink at nodes)
MIDLINE_P95_MAX_M = 1.5    # V1 (EXPANSION-PLAN Verification, invented there)
DIVIDED_SEP_M = 3.0        # [authored] fwd / rev OSM lines further apart than this = two carriageways
NOSE_M = 6.0               # [authored] a median island tapers to its nose over this
NOSE_CLEAR_M = 6.0         # [authored] a median stops this far short of a pad cut / weld opening
NOSE_W_M = 0.6             # [authored] the nose's blunt end width
CROSSOVER_W_M = 12.0       # [authored] the Mission Gorge median crossovers' opening (dossier: st 174 / 202)
PAD_CUT_PAD_M = 2.0        # [authored] an arm is cut this far past its farther curb-return tangent point
STUB_LEN_M = 15.0          # [authored] a see-only stub's pavement beyond its mouth line (JUNCTIONS 18c)
WELD_STUB_OUT_M = 100.0    # [authored] the weld connector's reach out of the loop edge (rehearsal; P3 = whole piece)
WELD_IN_M = 6.0            # the weld connector starts this far inside the loop edge (trim_connectors drops it)
ENTRY_MIN_DEG = 15.0       # [authored] a curb RETURN meets the loop edge at no shallower angle (the weld mitres it)
ENTRY_EASE_M = 3.0         # [authored] J5's NE curb leaves its line this far off the loop edge to ease onto it ...
EASE_ENTRY_DEG = 30.0      # [authored] ... meeting the loop edge at this angle
MAX_GRADE = 0.11           # tools/route_connectors.py MAX_GRADE (checked here, never applied blind)
XS_EVERY_M = 10.0          # cross-sections every 10 m ...
XS_REACH_M = 100.0         # ... over the first / last 100 m of every leg end
XS_HALF_M = 40.0           # ... out to 40 m either side, every 2 m
XS_STEP_M = 2.0
RESAMPLE_CONNECTOR_M = 3.0  # tools/route_connectors.py RESAMPLE_M (the connector form)

PIECES = [  # id, road, from, to, csv letter
    ("A", "Waring Road", "J1", "J2"),
    ("B", "Princess View Drive", "J2", "J3"),
    ("C", "Mission Gorge Road", "J3", "J4"),
    ("D", "Jackson Drive", "J4", "J5"),
]
PIECE_NAME = {"A": "waring", "B": "princess_view", "C": "mission_gorge", "D": "jackson_north"}

# the aerial arm rows that belong to a piece end: (junction, road, bearing) -> (piece, end); the reading's left /
# right are relative to the arm's OUTWARD direction, so an arm read at a piece's END is mirrored
ARM_ENDS = {("J1", "Waring Road"): ("A", "start"), ("J2", "Waring Road", "052"): ("A", "end"),
            ("J2", "Princess View Drive"): ("B", "start"), ("J3", "Princess View Drive"): ("B", "end"),
            ("J3", "Mission Gorge Road", "057"): ("C", "start"), ("J4", "Mission Gorge Road", "244"): ("C", "end"),
            ("J4", "Jackson Drive"): ("D", "start"), ("J5", "Jackson Drive", "321"): ("D", "end")}

# the see-only arms (A1): junction, label, csv arm key (road, bearing) or OSM way, width when unmeasured
STUB_ARMS = [
    ("S1", "J2", "Mound Avenue", ("Mound Avenue", "140"), None),
    ("S2", "J2", "Waring Road (south-west, off route)", ("Waring Road", "228"), None),
    ("S3", "J3", "Mission Gorge Road (west, off route)", ("Mission Gorge Road", "252"), None),
    ("S4", "J3", "quarry drive (OSM 'Tierrasanta Boulevard (Proposed)')", ("Tierrasanta Boulevard (Proposed)", "342"), None),
    ("S5", "J4", "Mission Gorge Road (east, the gorge; Phase 2)", ("Mission Gorge Road", "080"), None),
    ("S6", "J4", "MTRP visitor-centre entrance (OSM service way 60516202)", None, {"way": 60516202, "width_m": 12.0}),
]

# corner radii (dossier junction table + A4): junction -> {(arm bearing a, arm bearing b clockwise): R}; a missing
# pair takes the junction default. J3's north corners and J4's north side are the dossier's "~6"
CORNER_R = {
    "J2": {"default": 7.0},                                   # "6-8 m"
    "J3": {"default": 6.0, ("170", "252"): 11.0, ("057", "170"): 5.5},   # SW 10-12, SE 5-6; north [authored] 6
    "J4": {"default": 6.0, ("080", "144"): 9.0, ("144", "244"): 9.0},    # south side 8-10; north ~6
}
CORNER_R_SOURCE = "dossier §2 junction table: J2 6-8 m, J3 SW 10-12 / SE 5-6, J4 south 8-10 / north ~6 (mid-values; " \
                  "J3's two north corners unmeasured: [authored] 6 m)"

# the welds (A5): which piece end meets the loop, the box, and the curb returns (dossier §2 / revise/measure.json)
WELDS = [
    {"id": "W1", "junction": "J1", "piece": "A", "end": "start", "box": [1506, 1521], "apex": 1514,
     "returns": {"right": {"R": 30.0, "src": "J1 NE free-flow return R ~30 +- 10 m (dossier §2; revise/measure.json "
                                              "NE_return_R30 ends at v1528.46)"}},
     "ribbon": {"returns": {}, "ease": {},
                "why": "P1 rehearsal, measured: a 3-line connector ribbon cannot end on the convex, graded outer edge "
                       "of the College/Navajo corner across the R 30 return: its end row hovers 2.9-4.0 cm over the "
                       "loop deck between its three points wherever the centre stands (the weld self-check and "
                       "verify_mouths allow 2 cm), and the mitre's straight run-on lands the NE end at ~v1523, not at "
                       "the return's v1527.5. The stub is welded with Waring's straight curbs (1.7-1.8 cm); the "
                       "return's area is this apron, a P3 authored piece (EXPANSION-PLAN P1 note)"},
     "a5_opening": [1513.5, 1528.5], "a5_centre_vertex": 1517.4, "v_window": [1490, 1550]},
    {"id": "W5", "junction": "J5", "piece": "D", "end": "end", "box": [2311, 2328], "apex": 2319,
     "returns": {"left": {"R": 10.0, "src": "J5 returns 8-12 m (dossier §2; mid-value)"}},
     "ease": {"right": "Jackson north's NE curb runs on as Jackson south's east curb (within 1 m of the loop edge "
                       "v2321-2323, revise/mouth_sides.py): eased onto the loop edge, no corner"},
     "a5_opening": [2312.0, 2322.0], "a5_centre_vertex": 2317.7, "v_window": [2290, 2350]},
]

MEDIAN_KIND = [  # (substring of the eye reading's median_kind, type)
    ("terracotta nose", "terracotta"), ("narrow terracotta", "terracotta"), ("terracotta", "terracotta"),
    ("painted hatch", "hatched"), ("painted", "painted"), ("raised nose begins", "nose"), ("raised nose", "planted"),
    ("raised planted", "planted"), ("raised, one tree", "planted"), ("raised", "planted"),
    ("double yellow", "line"), ("double-double yellow", "painted"), ("none", "none"),
]
RAISED = {"planted", "terracotta", "nose"}
FLUSH = {"painted", "hatched"}

# per-piece overrides from the plan / dossier where the eye readings are too sparse (A2)
MEDIAN_OVERRIDES = {
    # Princess View: undivided (A2). Its raised islands are MEASURED_ISLANDS below (repair round 2: the dossier's
    # "raised nose at Fontaine St, st ~500-557" stood on the Fontaine crosswalk; the real island is st 399-535)
    "B": [{"from": 0.0, "to": 1e9, "type": "line"}],
    # Jackson north: the hatched painted median on the last ~180 m into J4 = where OSM maps two one-way ways (A2)
    "D": [{"from": 0.0, "to": "osm_divided_end", "type": "hatched"}],
}

# ledger 0054 P3 repair round 2: the centre paint MEASURED off NAIP (tools/aerial_paint_north.py ->
# source/expansion/aerial__paint_north.json). Where it reads, it replaces the eye-interpolated centre of every
# undivided station: a painted median's offset and width (its two faces), or a plain double yellow's offset. Raised
# medians (Waring, Mission Gorge) are curbs, never re-read here.
PAINT_MEASURED = "source/expansion/aerial__paint_north.json"
PAINT_MEASURED_PIECES = ("B", "D")   # the undivided roads; Waring and Mission Gorge keep their raised medians' paint
# raised islands the aerial shows (NAIP straightened strips, p3-proofs/paint_strips) that the eye readings and the
# dossier missed or misplaced: (piece, from s, to s, type). Each island's outline is the measured yellow edge paint;
# the island's face stands ISLAND_EDGE_M inside that paint (expansion_pieces.MEDIAN_EDGE_M) and its yellow is centred
# FACE_IN_M inside the outer edge the measurement reports (aerial_paint_north.FACE_IN_M)
MEASURED_ISLANDS = {
    "B": [(399.0, 535.0, "nose"),       # the Fontaine St island: lighter concrete, two trees, the turn pocket st ~480
          (612.0, 700.0, "planted")],   # the island with two trees past Fontaine (none in OSM / the dossier)
    "D": [(32.0, 118.0, "nose")],       # the J4 approach: stamped concrete inside the yellow (the hatched teardrop
                                        # beyond it, st 118-158, is paint)
}
ISLAND_EDGE_M = 0.30
FACE_IN_M = 0.18
GAPS = {"C": [(174.0, CROSSOVER_W_M), (202.0, CROSSOVER_W_M)]}     # Mission Gorge median crossovers (dossier §2)


# ------------------------------------------------------------------------------------------------ geometry helpers

def mpd(lat0):
    """(m per deg lon, m per deg lat) — the series scripts-v021/geometry/projection.py projected the loop with"""
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    return m_lon, m_lat


class Frame:
    def __init__(self, origin):
        self.lon0, self.lat0, self.elev0 = origin["lon"], origin["lat"], origin["elev_m"]
        self.mlon, self.mlat = mpd(self.lat0)

    def xz(self, lon, lat):
        return ((lon - self.lon0) * self.mlon, (lat - self.lat0) * self.mlat)

    def lonlat(self, x, z):
        return (self.lon0 + x / self.mlon, self.lat0 + z / self.mlat)


def dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def arc(pts):
    s = [0.0]
    for a, b in zip(pts, pts[1:]):
        s.append(s[-1] + dist(a, b))
    return s


def at_arc(pts, s_list, s):
    s = max(s_list[0], min(s_list[-1], s))
    lo, hi = 0, len(s_list) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if s_list[mid] <= s:
            lo = mid
        else:
            hi = mid
    seg = s_list[hi] - s_list[lo]
    t = 0.0 if seg < 1e-12 else (s - s_list[lo]) / seg
    a, b = pts[lo], pts[hi]
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def resample(pts, step):
    s = arc(pts)
    n = max(1, int(math.floor(s[-1] / step)))
    out = [at_arc(pts, s, k * step) for k in range(n + 1)]
    if s[-1] - n * step > 1e-6:
        out.append(tuple(pts[-1]))
    return out


def project(pt, line):
    """(distance, arc position, signed lateral (+ = left), segment) of pt onto a polyline"""
    best = None
    acc = 0.0
    for i in range(len(line) - 1):
        a, b = line[i], line[i + 1]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        L = math.sqrt(L2)
        if L2 < 1e-12:
            continue
        t = max(0.0, min(1.0, ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dz) / L2))
        q = (a[0] + t * dx, a[1] + t * dz)
        d = dist(pt, q)
        if best is None or d < best[0]:
            lat = (-dz * (pt[0] - a[0]) + dx * (pt[1] - a[1])) / L
            best = (d, acc + t * L, lat, i)
        acc += L
    return best


def project_index(pt, line):
    """(distance, fractional index) of pt onto a polyline — for a midline sampled every 1 m of the forward leg
    the fractional index IS the station"""
    best = None
    for i in range(len(line) - 1):
        a, b = line[i], line[i + 1]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        if L2 < 1e-12:
            continue
        t = max(0.0, min(1.0, ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dz) / L2))
        d = dist(pt, (a[0] + t * dx, a[1] + t * dz))
        if best is None or d < best[0]:
            best = (d, i + t)
    return best


def tangent(pts, i):
    a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz) or 1.0
    return (dx / L, dz / L)


def left_normal(t):
    return (-t[1], t[0])


def offset_pt(p, t, off):
    n = left_normal(t)
    return (p[0] + n[0] * off, p[1] + n[1] * off)


def assembler_smooth(pts, sigma_pts=1.5):
    """scripts-v021/geometry/smooth.py smooth_centerline(sigma_pts=1.5, passes=1) in plan: the connector centre
    build_loop_blend sweeps (normalised Gaussian, radius ceil(3 sigma), clamped ends, endpoints pinned)"""
    n = len(pts)
    if n < 5:
        return [tuple(p) for p in pts]
    r = max(1, int(round(3.0 * sigma_pts)))
    ker = [math.exp(-(k * k) / (2.0 * sigma_pts * sigma_pts)) for k in range(-r, r + 1)]
    sk = sum(ker)
    ker = [k / sk for k in ker]
    out = []
    for i in range(n):
        if i == 0 or i == n - 1:
            out.append(tuple(pts[i]))
            continue
        x = z = 0.0
        for k in range(-r, r + 1):
            j = min(n - 1, max(0, i + k))
            x += ker[k + r] * pts[j][0]
            z += ker[k + r] * pts[j][1]
        out.append((x, z))
    return out


def gauss_smooth(pts, sigma_pts):
    n = len(pts)
    r = max(1, int(round(3 * sigma_pts)))
    ker = [math.exp(-0.5 * (k / sigma_pts) ** 2) for k in range(-r, r + 1)]
    out = []
    for i in range(n):
        if i == 0 or i == n - 1:
            out.append(tuple(pts[i]))
            continue
        sx = sz = sw = 0.0
        for k in range(-r, r + 1):
            j = min(n - 1, max(0, i + k))
            w = ker[k + r]
            sx += pts[j][0] * w
            sz += pts[j][1] * w
            sw += w
        out.append((sx / sw, sz / sw))
    return out


def seg_intersect(a, b, c, d):
    """(t, u, point) where segments a->b and c->d cross, else None"""
    r = (b[0] - a[0], b[1] - a[1])
    s = (d[0] - c[0], d[1] - c[1])
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-12:
        return None
    t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / den
    u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return t, u, (a[0] + r[0] * t, a[1] + r[1] * t)
    return None


def line_intersect(p, d, q, e):
    """intersection of infinite lines p + t d and q + u e: (t, u, point) or None"""
    den = d[0] * e[1] - d[1] * e[0]
    if abs(den) < 1e-12:
        return None
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    u = ((q[0] - p[0]) * d[1] - (q[1] - p[1]) * d[0]) / den
    return t, u, (p[0] + d[0] * t, p[1] + d[1] * t)


def polyline_cross(line, poly):
    """first crossing (walking `line` from its start) with polyline `poly`: (line arc, poly segment k, u, point, angle)"""
    sl = arc(line)
    for i in range(len(line) - 1):
        best = None
        for k in range(len(poly) - 1):
            x = seg_intersect(line[i], line[i + 1], poly[k], poly[k + 1])
            if x and (best is None or x[0] < best[0][0]):
                best = (x, k)
        if best:
            (t, u, p), k = best
            da = (line[i + 1][0] - line[i][0], line[i + 1][1] - line[i][1])
            de = (poly[k + 1][0] - poly[k][0], poly[k + 1][1] - poly[k][1])
            c = abs(da[0] * de[0] + da[1] * de[1]) / ((math.hypot(*da) * math.hypot(*de)) or 1.0)
            return sl[i] + t * (sl[i + 1] - sl[i]), k, u, p, math.degrees(math.acos(min(1.0, c)))
    return None


def bearing(d):
    return math.degrees(math.atan2(d[0], d[1])) % 360.0


def unit_from_bearing(b):
    r = math.radians(b)
    return (math.sin(r), math.cos(r))


def r3(v):
    return round(v, 3)


def r2(v):
    return round(v, 2)


# ------------------------------------------------------------------------------------------------ 3DEP with a cache

class Samples:
    """3DEP 1 m samples keyed on (lon, lat) rounded to 1e-7 deg, cached gzipped beside the intermediate"""

    def __init__(self, path: Path, offline: bool):
        self.path = path
        self.offline = offline
        self.data = {}
        self.meta = {}
        self.fetched = 0
        if path.exists():
            d = json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))
            self.meta = d.get("provenance", {})
            self.data = {k: v for k, v in d["samples"].items()}

    @staticmethod
    def key(lon, lat):
        return f"{lon:.7f},{lat:.7f}"

    def get(self, lonlats):
        missing = []
        seen = set()
        for lon, lat in lonlats:
            k = self.key(lon, lat)
            if k not in self.data and k not in seen:
                missing.append((round(lon, 7), round(lat, 7)))
                seen.add(k)
        if missing:
            if self.offline:
                raise SystemExit(f"[expansion] --offline: {len(missing)} 3DEP samples are not cached in {self.path}")
            from scripts.elevation import usgs_3dep
            print(f"[expansion] 3DEP: fetching {len(missing)} samples (TLS verified, {usgs_3dep.GET_SAMPLES})")
            vals = usgs_3dep.sample_points(missing)
            for (lon, lat), v in zip(missing, vals):
                self.data[self.key(lon, lat)] = round(float(v), 3)
            self.fetched += len(missing)
            self.meta = {"source": usgs_3dep.GET_SAMPLES, "tls": "verified (scripts.tls.https_context)",
                         "last_fetch_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                         "resolution": "3DEP best available (1 m here), returnFirstValueOnly"}
        return [self.data[self.key(lon, lat)] for lon, lat in lonlats]

    def save(self):
        if not self.fetched and self.path.exists():
            return
        payload = {"provenance": dict(self.meta, n=len(self.data), key="lon,lat rounded to 1e-7 deg -> metres"),
                   "samples": dict(sorted(self.data.items()))}
        self.path.write_bytes(gzip.compress(json.dumps(payload, separators=(",", ":")).encode("utf-8"), mtime=0))


# ------------------------------------------------------------------------------------------------ inputs

def sha16(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(AIROSO.resolve())).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def load_inputs(track: Path):
    routes_p = AIROSO / "data" / "routes.json"
    north = json.loads(routes_p.read_text(encoding="utf-8"))["north"]
    cl_p = track / "data" / "centerline.local.json"
    cl = json.loads(cl_p.read_text(encoding="utf-8"))
    osm_p = track / "data" / "osm.expansion.json"
    osm = json.loads(osm_p.read_text(encoding="utf-8"))
    eye_p = track / "source" / "expansion" / "aerial__widths_eye.csv"
    eye = list(csv.DictReader(eye_p.open(encoding="utf-8")))
    meas_p = track / "source" / "expansion" / "revise__measure.json"
    meas = json.loads(meas_p.read_text(encoding="utf-8"))
    prov = {"routes.json north": {"path": "data/routes.json", "sha256_16": sha16(routes_p),
                                  "osm_base": (north.get("provenance") or {}).get("osm_base")},
            "centerline.local.json": {"path": _rel(cl_p), "sha256_16": sha16(cl_p)},
            "osm.expansion.json": {"path": _rel(osm_p), "sha256_16": sha16(osm_p),
                                   "osm_base": osm.get("osm_base"), "source": osm.get("source")},
            "aerial__widths_eye.csv": {"path": _rel(eye_p), "sha256_16": sha16(eye_p),
                                       "what": "NAIP 2022-04-25 eye readings (A3)"},
            "revise__measure.json": {"path": _rel(meas_p), "sha256_16": sha16(meas_p)}}
    return north, cl, osm, eye, meas, prov


def split_legs(north, frame):
    """the fwd legs J1..J5 and the rev legs (reversed into fwd order), each as local (x, z) + node ids"""
    jf, jr = north["junctions"]["fwd"], north["junctions"]["rev"]
    fn, fc = north["nodes"], north["coords"]
    rn, rc = north["rev"]["nodes"], north["rev"]["coords"]
    order = ["J1", "J2", "J3", "J4", "J5"]
    fi = [fn.index(jf[j]) for j in order]
    ri = [rn.index(jr[j]) for j in order[::-1]]
    legs = {}
    for k, (pid, road, a, b) in enumerate(PIECES):
        f0, f1 = fi[k], fi[k + 1]
        r_lo, r_hi = ri[3 - k], ri[4 - k]           # rev runs J5..J1: the piece's rev leg is J(b) -> J(a)
        fwd = [frame.xz(*c) for c in fc[f0:f1 + 1]]
        rev = [frame.xz(*c) for c in rc[r_lo:r_hi + 1]][::-1]
        legs[pid] = {"fwd": fwd, "rev": rev, "fwd_nodes": fn[f0:f1 + 1], "rev_nodes": rn[r_lo:r_hi + 1][::-1]}
    return legs


def way_lanes(osm):
    """(node a, node b) -> way tags, for every consecutive node pair of every way"""
    pair = {}
    for w in osm["ways"]:
        t = w.get("tags", {})
        ns = w["nodes"]
        for a, b in zip(ns, ns[1:]):
            pair[(a, b)] = (w["id"], t)
            pair[(b, a)] = (w["id"], t)
    return pair


# ------------------------------------------------------------------------------------------------ pieces

def build_midline(leg):
    """1 m fwd samples, the rev carriageway's nearest point, the raw midline and the separation"""
    f1 = resample(leg["fwd"], 1.0)
    rev = leg["rev"]
    raw, sep = [], []
    for p in f1:
        d, _s, _lat, _i = project(p, rev)
        if d <= DIVIDED_SEP_M:
            raw.append(p)
        else:
            q = None
            best = None
            for i in range(len(rev) - 1):
                a, b = rev[i], rev[i + 1]
                dx, dz = b[0] - a[0], b[1] - a[1]
                L2 = dx * dx + dz * dz
                if L2 < 1e-12:
                    continue
                t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
                qq = (a[0] + t * dx, a[1] + t * dz)
                dd = dist(p, qq)
                if best is None or dd < best:
                    best, q = dd, qq
            raw.append(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2))
        sep.append(d)
    return f1, raw, sep


def eye_readings(eye, frame, midlines):
    """per piece: [(s, row dict, mirrored)] — the A/B/C/D station rows and the arm rows at piece ends"""
    out = {pid: [] for pid, *_ in PIECES}
    stations = []
    for row in eye:
        lab = row["label"].strip()
        lat, lon = float(row["lat"]), float(row["lon"])
        p = frame.xz(lon, lat)
        pid, mirrored, kind = None, False, None
        if lab[:1] in "ABCD" and " st " in lab:
            pid, kind = lab[0], "station"
        elif " arm " in lab:
            j = lab.split()[0]
            road = lab.split(" arm ")[1].rsplit(" brg ", 1)[0]
            brg = lab.rsplit(" brg ", 1)[1]
            hit = ARM_ENDS.get((j, road, brg)) or ARM_ENDS.get((j, road))
            if hit:
                pid, end = hit
                mirrored, kind = end == "end", "arm"
        if pid is None:
            continue
        mid = midlines[pid]
        d, s_st = project_index(p, mid["pts"])       # the midline is indexed by fwd metres: index = station
        rec = {"s": s_st, "row": row, "mirrored": mirrored, "kind": kind, "off_line_m": d}
        out[pid].append(rec)
        stations.append((pid, rec))
    for pid in out:
        out[pid].sort(key=lambda r: r["s"])
    return out, stations


def median_type(kind):
    k = (kind or "none").lower()
    for sub, t in MEDIAN_KIND:
        if sub in k:
            return t
    return "none"


def reading_offsets(rec, divided):
    """(left curb, right curb, median width, median offset) about the midline, + = left of the forward direction"""
    row = rec["row"]
    W = float(row["eye_curb_to_curb_m"])
    m = float(row["median_m"] or 0.0)
    cl = float(row["cw_left_m"]) if row["cw_left_m"] else None
    cr = float(row["cw_right_m"]) if row["cw_right_m"] else None
    if rec["mirrored"] and cl is not None:
        cl, cr = cr, cl
    if cl is None or cr is None:
        return W / 2.0, -W / 2.0, 0.0, 0.0
    tot = cl + m + cr
    if abs(tot - W) > 0.25:                           # the eye's parts do not add up: scale the carriageways
        k = (W - m) / (cl + cr)
        cl, cr = cl * k, cr * k
    shift = (cl - cr) / 4.0 if divided else 0.0       # divided: the OSM midline sits between carriageway centres
    return m / 2.0 + cl - shift, -(m / 2.0 + cr) - shift, m, -shift


def interp_rows(rows, s, key):
    if s <= rows[0]["s"]:
        return rows[0][key]
    if s >= rows[-1]["s"]:
        return rows[-1][key]
    for a, b in zip(rows, rows[1:]):
        if a["s"] <= s <= b["s"]:
            t = (s - a["s"]) / ((b["s"] - a["s"]) or 1.0)
            return a[key] + (b[key] - a[key]) * t
    return rows[-1][key]


def nearest_row(rows, s):
    return min(rows, key=lambda r: abs(r["s"] - s))


def load_paint_measured(track: Path):
    """{pid: {round(s, 2): use}} from aerial__paint_north.json (empty when the file is absent)"""
    p = track / PAINT_MEASURED
    if not p.exists():
        return {}, None
    doc = json.loads(p.read_text(encoding="utf-8"))
    out = {pid: {round(float(q["s"]), 2): q["use"] for q in recs if q.get("use")} for pid, recs in doc["pieces"].items()}
    return out, {"path": _rel(p), "sha256_16": sha16(p), "written_utc": doc.get("written_utc"),
                 "intermediate_sha256_12": doc.get("intermediate_sha256_12"), "what": "NAIP centre paint, measured"}


def apply_paint_measured(pid, recs, measured):
    """the measured centre paint into a piece's station records (see PAINT_MEASURED / MEASURED_ISLANDS)"""
    if pid not in PAINT_MEASURED_PIECES:
        return 0, 0
    mp = measured.get(pid) or {}
    islands = MEASURED_ISLANDS.get(pid, [])
    n_paint = n_island = 0
    last_isl = None
    for r in recs:
        u = mp.get(round(r["s"], 2))
        isl = next((t for a, b, t in islands if a <= r["s"] <= b), None)
        if isl is not None:
            if u is not None and u["kind"] == "median":
                last_isl = (u["centre_off_m"], max(NOSE_W_M, u["width_m"] - 2 * FACE_IN_M - 2 * ISLAND_EDGE_M))
            if last_isl is None:
                continue
            r["mtype"], r["moff"], r["m"] = isl, last_isl[0], last_isl[1]
            r["paint_src"] = "aerial island"
            n_island += 1
            continue
        last_isl = None
        if r["mtype"] in RAISED or u is None:
            continue
        if u["kind"] == "median":
            r["mtype"] = "hatched" if r["mtype"] == "hatched" else "painted"
            r["m"], r["moff"] = u["width_m"], u["centre_off_m"]
        else:
            r["mtype"], r["m"], r["moff"] = "line", 0.0, u["centre_off_m"]
        r["paint_src"] = "aerial " + u["how"]
        n_paint += 1
    return n_paint, n_island


def build_pieces(legs, frame, eye, osm, measured=None):
    pairs = way_lanes(osm)
    nodes = osm["nodes"]
    midlines = {}
    for pid, road, a, b in PIECES:
        f1, raw, sep = build_midline(legs[pid])
        sm = gauss_smooth(raw, SMOOTH_SIGMA_M)
        midlines[pid] = {"pts": sm, "raw": raw, "sep": sep, "fwd": f1, "s": [float(k) for k in range(len(sm))]}
    readings, stations = eye_readings(eye, frame, {k: {"pts": v["pts"], "s": v["s"]} for k, v in midlines.items()})
    pieces = {}
    for pid, road, a, b in PIECES:
        ml = midlines[pid]
        n1 = len(ml["pts"])
        length = float(n1 - 1)
        rows = []
        for rec in readings[pid]:
            i = min(n1 - 1, max(0, int(round(rec["s"]))))
            divided = ml["sep"][i] > DIVIDED_SEP_M
            Lo, Ro, m, moff = reading_offsets(rec, divided)
            rows.append({"s": rec["s"], "L": Lo, "R": Ro, "m": m, "moff": moff,
                         "type": median_type(rec["row"]["median_kind"]), "label": rec["row"]["label"],
                         "kind": rec["kind"], "eye_w": float(rec["row"]["eye_curb_to_curb_m"]),
                         "conf": float(rec["row"]["eye_conf_m"] or 1.0), "divided": divided})
        # lanes from the OSM ways under the fwd / rev legs (node pairs)
        def lanes_along(nodes_list, coords):
            out = []
            sl = arc(coords)
            for i in range(len(nodes_list) - 1):
                wid, t = pairs.get((nodes_list[i], nodes_list[i + 1]), (None, {}))
                out.append((sl[i], sl[i + 1], wid, t))
            return out
        fl = lanes_along(legs[pid]["fwd_nodes"], legs[pid]["fwd"])
        rl = lanes_along(legs[pid]["rev_nodes"], legs[pid]["rev"])
        rl_len = arc(legs[pid]["rev"])[-1]
        # stations every SPACING_M
        n = int(math.floor(length / SPACING_M))
        st = [k * SPACING_M for k in range(n + 1)]
        if length - st[-1] > 0.5:
            st.append(length)
        pts = [at_arc(ml["pts"], ml["s"], s) for s in st]
        raw_pts = ml["raw"]
        devs = [project(p, raw_pts)[0] for p in pts]
        # median overrides (A2)
        ov = MEDIAN_OVERRIDES.get(pid, [])
        osm_div_end = None
        if pid == "D":
            k = 0
            while k < len(ml["sep"]) and (ml["sep"][k] > DIVIDED_SEP_M or k < 20):
                k += 1
            osm_div_end = float(k)
        recs = []
        for s, p in zip(st, pts):
            i = min(n1 - 1, int(round(s)))
            t = tangent(ml["pts"], i)
            Lo = interp_rows(rows, s, "L")
            Ro = interp_rows(rows, s, "R")
            m = interp_rows(rows, s, "m")
            moff = interp_rows(rows, s, "moff")
            mtype = nearest_row(rows, s)["type"]
            for o in ov:
                to = osm_div_end if o["to"] == "osm_divided_end" else o["to"]
                if o["from"] <= s < to:
                    mtype = o["type"]
                    if "w" in o:
                        m = o["w"]
            if mtype in ("none", "line"):
                m_eff = 0.0
            else:
                m_eff = m
            fw = next((x for x in fl if x[0] <= s <= x[1]), fl[-1] if fl else None)
            s_rev = rl_len - s * rl_len / length
            rw = next((x for x in rl if x[0] <= s_rev <= x[1]), rl[-1] if rl else None)
            recs.append({"s": s, "p": p, "t": t, "L": Lo, "R": Ro, "m": m_eff, "moff": moff, "mtype": mtype, "paint_src": "eye",
                         "sep": ml["sep"][i], "lanes_fwd": (fw[3].get("lanes") if fw else None),
                         "lanes_rev": (rw[3].get("lanes") if rw else None),
                         "way_fwd": fw[2] if fw else None, "way_rev": rw[2] if rw else None,
                         "maxspeed": (fw[3].get("maxspeed") if fw else None)})
        n_paint, n_island = apply_paint_measured(pid, recs, measured or {})
        pieces[pid] = {"id": pid, "name": PIECE_NAME[pid], "road": road, "from": a, "to": b, "length_m": length,
                       "recs": recs, "rows": rows, "dev": devs, "midline": ml, "osm_divided_end": osm_div_end,
                       "paint_measured": {"stations_paint": n_paint, "stations_island": n_island}}
    return pieces, stations


# ------------------------------------------------------------------------------------------------ the loop edge

def loop_edge(cl, v0, v1, side=1):
    """the loop's pavement edge on `side` (+1 = L, left of increasing vertex) for vertices v0..v1, as (x, z), plus
    the vertex numbers"""
    P, W = cl["points_xyz_m"], cl["widths_m"]
    out = []
    for v in range(v0, v1 + 1):
        a, b = P[v - 1], P[v + 1]
        dx, dz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(dx, dz)
        out.append((P[v][0] - dz / L * W[v] / 2 * side, P[v][2] + dx / L * W[v] / 2 * side))
    return out, list(range(v0, v1 + 1))


def edge_vertex(k, u, verts):
    return verts[k] + u


def edge_point_at(edge, verts, vf):
    k = max(0, min(len(verts) - 2, int(math.floor(vf - verts[0]))))
    u = vf - verts[k]
    a, b = edge[k], edge[k + 1]
    return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)


def offset_poly(poly, off):
    """a polyline offset sideways (+ = left of its direction)"""
    return [offset_pt(poly[i], tangent(poly, i), off) for i in range(len(poly))]


def fillet_on_edge(curb_p, curb_d, curb_side_sign, edge, edge_out_sign, R):
    """the arc of radius R tangent to the straight curb (point curb_p, unit direction curb_d pointing TOWARD the
    loop) on its outer side (curb_side_sign: +1 = the fillet lies left of curb_d) and to the loop edge polyline on
    its outer side (edge_out_sign: +1 = left of the edge's direction). Returns (centre, T1 on the curb, T2 on the
    edge) or None."""
    n = left_normal(curb_d)
    q = (curb_p[0] + n[0] * R * curb_side_sign, curb_p[1] + n[1] * R * curb_side_sign)   # curb line moved by R
    eoff = offset_poly(edge, R * edge_out_sign)
    far = (q[0] - curb_d[0] * 400.0, q[1] - curb_d[1] * 400.0)
    near = (q[0] + curb_d[0] * 400.0, q[1] + curb_d[1] * 400.0)
    hits = []
    for k in range(len(eoff) - 1):
        x = seg_intersect(far, near, eoff[k], eoff[k + 1])
        if x:
            hits.append(x)
    if not hits:
        return None
    t, u, C = min(hits, key=lambda h: h[0])        # the first met coming in from far out
    t1 = ((C[0] - curb_p[0]) * curb_d[0] + (C[1] - curb_p[1]) * curb_d[1])
    T1 = (curb_p[0] + curb_d[0] * t1, curb_p[1] + curb_d[1] * t1)
    _d, _s, _lat, k = project(C, edge)
    a, b = edge[k], edge[k + 1]
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    tt = max(0.0, min(1.0, ((C[0] - a[0]) * dx + (C[1] - a[1]) * dz) / L2))
    T2 = (a[0] + dx * tt, a[1] + dz * tt)
    return C, T1, T2


def arc_points(C, A, B, step=0.75):
    """points from A to B around C, the short way"""
    a0 = math.atan2(A[1] - C[1], A[0] - C[0])
    a1 = math.atan2(B[1] - C[1], B[0] - C[0])
    d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    R = dist(C, A)
    n = max(2, int(math.ceil(abs(d) * R / step)))
    return [(C[0] + R * math.cos(a0 + d * k / n), C[1] + R * math.sin(a0 + d * k / n)) for k in range(n + 1)]


def entry_truncate(arcpts, edge):
    """walk an arc toward the loop edge; where its direction is within ENTRY_MIN_DEG of the edge's, leave it on a
    straight line at ENTRY_MIN_DEG and run that to the edge. Returns (polyline ending ON the edge, entry angle)"""
    for i in range(1, len(arcpts)):
        d = (arcpts[i][0] - arcpts[i - 1][0], arcpts[i][1] - arcpts[i - 1][1])
        _dd, _s, _lat, k = project(arcpts[i], edge)
        e = (edge[k + 1][0] - edge[k][0], edge[k + 1][1] - edge[k][1])
        c = abs(d[0] * e[0] + d[1] * e[1]) / ((math.hypot(*d) * math.hypot(*e)) or 1.0)
        ang = math.degrees(math.acos(min(1.0, c)))
        if ang <= ENTRY_MIN_DEG:
            p = arcpts[i - 1]
            L = math.hypot(*d) or 1.0
            dd = (d[0] / L, d[1] / L)
            far = (p[0] + dd[0] * 200.0, p[1] + dd[1] * 200.0)
            x = polyline_cross([p, far], edge)
            if x:
                return arcpts[:i] + [x[3]], ang
            return arcpts[:i], ang
    return arcpts, 0.0


# ------------------------------------------------------------------------------------------------ welds

def piece_frame_at(piece, s):
    """(point, unit tangent, left curb offset, right curb offset) of a piece at station s"""
    ml = piece["midline"]
    p = at_arc(ml["pts"], ml["s"], s)
    i = min(len(ml["pts"]) - 1, max(0, int(round(s))))
    t = tangent(ml["pts"], i)
    Lo = interp_rows(piece["rows"], s, "L")
    Ro = interp_rows(piece["rows"], s, "R")
    return p, t, Lo, Ro


def build_weld(wd, piece, cl, frame, samples):
    v0, v1 = wd["v_window"]
    edge, verts = loop_edge(cl, v0, v1, side=1)
    L = piece["length_m"]
    # the piece walked FROM the loop outward: s_out(u) maps distance out to the piece station
    outward = (lambda u: u) if wd["end"] == "start" else (lambda u: L - u)
    sgn_dir = 1.0 if wd["end"] == "start" else -1.0
    # the straight axis near the loop: the midline direction from 15 to 60 m out, as an OUTWARD unit vector
    pa, _ta, _l, _r = piece_frame_at(piece, outward(15.0))
    pb, _tb, _l2, _r2 = piece_frame_at(piece, outward(60.0))
    ax = (pb[0] - pa[0], pb[1] - pa[1])
    La = math.hypot(*ax)
    ax = (ax[0] / La, ax[1] / La)
    # the curbs as straight lines along the axis, offsets read at 40 m out, in the OUTWARD frame (+ = left of out)
    _p40, _t40, Lo40, Ro40 = piece_frame_at(piece, outward(40.0))
    if wd["end"] == "start":
        out_left, out_right = Lo40, Ro40
    else:                                               # walking the piece backwards swaps its sides
        out_left, out_right = -Ro40, -Lo40
    nrm = left_normal(ax)
    # the centre line extended into the loop: find its crossing with the loop edge
    base = pa
    cline = [(base[0] - ax[0] * 60.0, base[1] - ax[1] * 60.0), (base[0] + ax[0] * 200.0, base[1] + ax[1] * 200.0)]
    cx = polyline_cross(cline, edge)
    if cx is None:
        raise SystemExit(f"[expansion] {wd['id']}: the piece's axis never meets the loop edge")
    X0 = cx[3]
    centre_v = edge_vertex(cx[1], cx[2], verts)
    centre_angle = cx[4]
    # the piece station of X0: u out of the loop edge maps to s = s_X0 + u (start) or s_X0 - u (end)
    _dx0, s_x0 = project_index(X0, piece["midline"]["pts"])
    s_of_u = (lambda u: s_x0 + u) if wd["end"] == "start" else (lambda u: s_x0 - u)

    def curb_line(off):
        p0 = (X0[0] + nrm[0] * off - ax[0] * 40.0, X0[1] + nrm[1] * off - ax[1] * 40.0)
        p1 = (X0[0] + nrm[0] * off + ax[0] * 220.0, X0[1] + nrm[1] * off + ax[1] * 220.0)
        return p0, p1

    def make_sides(returns, ease):
        """the two curb polylines carried onto the loop edge: straight, a true-arc return, or an ease"""
        sides = {}
        for side, off in (("left", out_left), ("right", out_right)):
            p0, p1 = curb_line(off)
            x = polyline_cross([p0, p1], edge)
            rec = {"offset_m": r2(off), "cross": None, "return": None, "ease": None}
            if x:
                rec["cross"] = {"vertex": r2(edge_vertex(x[1], x[2], verts)), "angle_deg": r2(x[4]),
                                "xz": [r3(x[3][0]), r3(x[3][1])]}
            # straight curb toward the loop: direction INTO the loop is -ax; the fillet lies away from the road
            ret = returns.get(side)
            far_pt = (X0[0] + nrm[0] * off + ax[0] * WELD_STUB_OUT_M * 1.6, X0[1] + nrm[1] * off + ax[1] * WELD_STUB_OUT_M * 1.6)
            if ret:
                into = (-ax[0], -ax[1])
                # fillet outside the road: left curb -> further left of OUT = right of INTO
                side_sign = -1.0 if side == "left" else 1.0
                f = fillet_on_edge(far_pt, into, side_sign, edge, 1.0, ret["R"])
                if f is None:
                    raise SystemExit(f"[expansion] {wd['id']} {side}: no R {ret['R']} return fits")
                C, T1, T2 = f
                arcp = arc_points(C, T1, T2)
                line_pts, ang = entry_truncate(arcp, edge)
                endp = line_pts[-1]
                de, ds_, dlat, k = project(endp, edge)
                e_v = edge_vertex(k, 0.0, verts) + (ds_ - arc(edge)[k]) / max(1e-9, dist(edge[k], edge[k + 1]))
                t2d, t2s, _l3, k2 = project(T2, edge)
                t2v = edge_vertex(k2, 0.0, verts) + (t2s - arc(edge)[k2]) / max(1e-9, dist(edge[k2], edge[k2 + 1]))
                t1_out = (T1[0] - X0[0]) * ax[0] + (T1[1] - X0[1]) * ax[1]
                rec["return"] = {"R": ret["R"], "src": ret["src"], "tangent_out_m": r2(t1_out),
                                 "true_end_vertex": r2(t2v), "entry_deg": r2(ang),
                                 "built_end_vertex": r2(e_v), "centre_xz": [r3(C[0]), r3(C[1])]}
                poly = [far_pt, T1] + line_pts[1:]
            elif ease.get(side):
                # ease onto the loop edge: the curb runs on until it is ENTRY_EASE_M off the edge, then meets it at
                # ENTRY_MIN_DEG (the real curb runs on as the loop's own edge — no corner to model)
                into = (-ax[0], -ax[1])
                q = far_pt
                step = 0.25
                prev = None
                closest = None
                for k in range(int(260 / step)):
                    pt = (far_pt[0] + into[0] * step * k, far_pt[1] + into[1] * step * k)
                    d, _s, lat, _i = project(pt, edge)
                    if closest is None or d < closest[0]:
                        closest = (d, pt)
                    if d <= ENTRY_EASE_M and lat > 0:
                        q = pt
                        break
                    prev = pt
                else:
                    q = closest[1]
                _d, _s, lat, k = project(q, edge)
                e = (edge[k + 1][0] - edge[k][0], edge[k + 1][1] - edge[k][1])
                Le = math.hypot(*e)
                e = (e[0] / Le, e[1] / Le)
                # turn from the curb's direction toward the edge by ENTRY_MIN_DEG relative to the edge direction,
                # heading the way the curb was going along the edge
                along = 1.0 if (into[0] * e[0] + into[1] * e[1]) >= 0 else -1.0
                ea = (e[0] * along, e[1] * along)
                # rotate ea toward the edge (the edge lies to the right of the loop's L side = toward -left normal)
                inward = (-left_normal(e)[0], -left_normal(e)[1])
                c, s_ = math.cos(math.radians(EASE_ENTRY_DEG)), math.sin(math.radians(EASE_ENTRY_DEG))
                dirv = (ea[0] * c + inward[0] * s_, ea[1] * c + inward[1] * s_)
                far2 = (q[0] + dirv[0] * 60.0, q[1] + dirv[1] * 60.0)
                x = polyline_cross([q, far2], edge)
                endp = x[3] if x else q
                de, ds_, dlat, k3 = project(endp, edge)
                e_v = edge_vertex(k3, 0.0, verts) + (ds_ - arc(edge)[k3]) / max(1e-9, dist(edge[k3], edge[k3 + 1]))
                dmin, pmin = closest
                _d2, s_min, _l4, kmin = project(pmin, edge)
                vmin = edge_vertex(kmin, 0.0, verts) + (s_min - arc(edge)[kmin]) / max(1e-9, dist(edge[kmin], edge[kmin + 1]))
                rec["ease"] = {"why": ease[side], "leaves_curb_off_edge_m": ENTRY_EASE_M,
                               "entry_deg": EASE_ENTRY_DEG, "built_end_vertex": r2(e_v),
                               "curb_closest_to_edge_m": r2(dmin), "at_vertex": r2(vmin)}
                poly = [far_pt, q, endp]
            else:
                if not x:
                    raise SystemExit(f"[expansion] {wd['id']} {side}: the straight curb never meets the loop edge")
                poly = [far_pt, x[3]]
                rec["built_end_vertex"] = rec["cross"]["vertex"]
            sides[side] = {"rec": rec, "poly": poly}
        ends = []
        for side in ("left", "right"):
            r = sides[side]["rec"]
            ev = (r.get("return") or r.get("ease") or {}).get("built_end_vertex", r.get("built_end_vertex"))
            if ev is None and r["cross"]:
                ev = r["cross"]["vertex"]
            r["built_end_vertex"] = ev
            ends.append(ev)
        return sides, [min(ends), max(ends)]

    true_sides, opening = make_sides(wd.get("returns", {}), wd.get("ease", {}))
    rib = wd.get("ribbon")
    if rib is None:
        sides, opening_rib = true_sides, list(opening)
    else:
        sides, opening_rib = make_sides(rib.get("returns", {}), rib.get("ease", {}))
    # the APRON: what the true curbs open beyond what the ribbon stub can weld (a return the 3-line ribbon end cannot
    # follow within the weld's 2 cm — measured, EXPANSION-PLAN P1 rehearsal): the area between the stub's straight
    # curb, the loop edge and the true return arc, for P3 to author as its own piece
    aprons = []
    for side in ("left", "right"):
        tr, rr = true_sides[side]["rec"], sides[side]["rec"]
        if tr.get("return") and not rr.get("return"):
            tp, rp = true_sides[side]["poly"], sides[side]["poly"]
            e_true, e_rib = tr["return"]["built_end_vertex"], rr["built_end_vertex"]
            lo_v, hi_v = sorted((e_true, e_rib))
            ks = [k for k in range(len(verts)) if lo_v < verts[k] < hi_v]
            along = [edge[k] for k in ks]
            if e_true < e_rib:
                along = along[::-1]
            poly = list(tp[1:]) + along + [rp[-1]]
            area = 0.5 * abs(sum(poly[q][0] * poly[(q + 1) % len(poly)][1] - poly[(q + 1) % len(poly)][0] * poly[q][1]
                                 for q in range(len(poly))))
            aprons.append({"id": f"AP{wd['id'][1:]}", "side": side, "why": rib.get("why", ""),
                           "loop_edge_vertices": [r2(lo_v), r2(hi_v)], "area_m2": r2(area),
                           "polygon_xz": [[r3(q[0]), r3(q[1])] for q in poly]})

    def connector_of(sides):
        # ---- the connector form: chords perpendicular to the axis, centre + width, flared onto the returns ----
        polyL, polyR = sides["left"]["poly"], sides["right"]["poly"]

        def ext_in(poly):
            # extend the edge polyline past its loop-edge end along its last direction (the weld re-cuts it there)
            a, b = poly[-2], poly[-1]
            d = (b[0] - a[0], b[1] - a[1])
            Ld = math.hypot(*d) or 1.0
            return poly + [(b[0] + d[0] / Ld * 60.0, b[1] + d[1] / Ld * 60.0)]
        eL, eR = ext_in(polyL), ext_in(polyR)

        def chord_hit(poly, u):
            o = (X0[0] + ax[0] * u, X0[1] + ax[1] * u)
            a = (o[0] - nrm[0] * 120.0, o[1] - nrm[1] * 120.0)
            b = (o[0] + nrm[0] * 120.0, o[1] + nrm[1] * 120.0)
            best = None
            for k in range(len(poly) - 1):
                x = seg_intersect(a, b, poly[k], poly[k + 1])
                if x:
                    lat = (x[2][0] - o[0]) * nrm[0] + (x[2][1] - o[1]) * nrm[1]
                    if best is None or abs(lat) < abs(best[1]):
                        best = (x[2], lat)
            return best
        flare_end = max([sides[s_]["rec"]["return"]["tangent_out_m"] for s_ in sides if sides[s_]["rec"].get("return")]
                        + [((sides[s_]["poly"][1][0] - X0[0]) * ax[0] + (sides[s_]["poly"][1][1] - X0[1]) * ax[1])
                           for s_ in sides if sides[s_]["rec"].get("ease")] + [12.0]) + 6.0
        # THE FLARE, where the curbs leave their straight lines for the returns / the ease: a ruled strip between the two
        # authored curb polylines, from the regular section at u = flare_end (square to the axis) to the MOUTH CHORD (the
        # two opening ends, both ON the loop edge), each chord joining the points at the same FRACTION of each curb's
        # length; then a fixed point re-cuts every inner chord square to the centre the ASSEMBLER sweeps (its 1.5-point
        # smoothing, its centred tangent), the chord ends sliding along the curb polylines and never past their ends.
        # (Chords square to the straight axis landed 4-9 m off the curbs once the centre bent into the flare.)
        def sub_from(poly, u_cut):
            o = (X0[0] + ax[0] * u_cut, X0[1] + ax[1] * u_cut)
            a_ = (o[0] - nrm[0] * 150.0, o[1] - nrm[1] * 150.0)
            b_ = (o[0] + nrm[0] * 150.0, o[1] + nrm[1] * 150.0)
            for k in range(len(poly) - 1):
                x = seg_intersect(poly[k], poly[k + 1], a_, b_)
                if x:
                    return [x[2]] + list(poly[k + 1:])
            raise SystemExit(f"[expansion] {wd['id']}: the regular section at u {u_cut:.1f} misses a curb")
        subL, subR = sub_from(polyL, flare_end), sub_from(polyR, flare_end)
        aL, aR = arc(subL), arc(subR)
        nfl = max(3, int(round(((aL[-1] + aR[-1]) / 2.0) / RESAMPLE_CONNECTOR_M)))
        chords = []
        for k in range(nfl + 1):
            f_ = k / nfl
            chords.append([at_arc(subL, aL, f_ * aL[-1]), at_arc(subR, aR, f_ * aR[-1])])

        def mid_w(ch):
            return ((ch[0][0] + ch[1][0]) / 2, (ch[0][1] + ch[1][1]) / 2), dist(ch[0], ch[1])
        tail = []
        u = flare_end + RESAMPLE_CONNECTOR_M
        while u <= WELD_STUB_OUT_M + 1e-9:
            p, t, Lo, Ro = piece_frame_at(piece, s_of_u(u))
            tail.append((offset_pt(p, t, (Lo + Ro) / 2.0), Lo - Ro, u))
            u += RESAMPLE_CONNECTOR_M

        def inside_pts():
            # past the mouth chord, into the loop (trim_connectors drops them; they set the end's direction)
            (c1, w1), (c2, _w2) = mid_w(chords[-1]), mid_w(chords[-2])
            d_ = (c1[0] - c2[0], c1[1] - c2[1])
            Ld_ = math.hypot(*d_) or 1.0
            return [((c1[0] + d_[0] / Ld_ * q * RESAMPLE_CONNECTOR_M, c1[1] + d_[1] / Ld_ * q * RESAMPLE_CONNECTOR_M), w1)
                    for q in (2, 1)]

        def assemble():
            ins = inside_pts()
            flare_pts = [mid_w(ch) for ch in chords[::-1]]           # the mouth chord first, outward
            return ins + flare_pts, len(ins)
        for _it in range(80):
            seq, nin = assemble()
            raw = [c for c, _w in seq] + [c for c, _w, _u in tail]
            sm = assembler_smooth(raw)
            moved = 0.0
            for k in range(1, nfl + 1):                              # every chord but the regular section
                i = nin + (nfl - k)
                t = tangent(sm, i)
                n_ = left_normal(t)
                a_ = (sm[i][0] - n_[0] * 150.0, sm[i][1] - n_[1] * 150.0)
                b_ = (sm[i][0] + n_[0] * 150.0, sm[i][1] + n_[1] * 150.0)
                hits = []
                for poly in (subL, subR):
                    best = None
                    for q in range(len(poly) - 1):
                        x = seg_intersect(a_, b_, poly[q], poly[q + 1])
                        if x and (best is None or dist(x[2], sm[i]) < dist(best, sm[i])):
                            best = x[2]
                    if best is None:                                 # past the curb's end: clamp to it
                        best = min((poly[0], poly[-1]), key=lambda e: abs((e[0] - sm[i][0]) * t[0] + (e[1] - sm[i][1]) * t[1]))
                    hits.append(best)
                if not (hits[0] and hits[1]):
                    continue
                target = ((hits[0][0] + hits[1][0]) / 2, (hits[0][1] + hits[1][1]) / 2)
                dx, dz = target[0] - sm[i][0], target[1] - sm[i][1]
                # move the chord: its ends slide along their curbs toward the square cut, half way per pass
                for e_, poly in ((0, subL), (1, subR)):
                    cur = chords[k][e_]
                    hit = hits[e_]
                    chords[k][e_] = (cur[0] + 0.5 * (hit[0] - cur[0]), cur[1] + 0.5 * (hit[1] - cur[1]))
                moved = max(moved, math.hypot(dx, dz))
            if moved < 0.005:
                break
        seq, nin = assemble()
        us_ = [-(nin - q) * RESAMPLE_CONNECTOR_M for q in range(nin)]
        flare_u = []
        for ch in chords[::-1]:
            c_, _w = mid_w(ch)
            flare_u.append((c_[0] - X0[0]) * ax[0] + (c_[1] - X0[1]) * ax[1])
        flare = [list(x) for x in seq]
        us = us_ + flare_u
        conn = ([(c, w, ("inside" if q < nin else "flare"), uu) for q, ((c, w), uu) in enumerate(zip(flare, us))]
                + [(c, w, "piece", uu) for c, w, uu in tail])
        # swept-edge check, as the assembler sweeps it: smoothed centre, centred tangent, +- width / 2
        cpts = [c for c, _w, _k, _u in conn]
        sm = assembler_smooth(cpts)
        swept_err = []
        min_r_over_half = None
        for i, (c, w, kind, uu) in enumerate(conn):
            t = tangent(sm, i)
            for off, poly in ((w / 2.0, eL), (-w / 2.0, eR)):
                q = offset_pt(sm[i], t, off)
                if kind == "flare":
                    swept_err.append(project(q, poly)[0])
            if 0 < i < len(sm) - 1:
                a_, b_, c_ = sm[i - 1], sm[i], sm[i + 1]
                ab, bc, ca = dist(a_, b_), dist(b_, c_), dist(c_, a_)
                cr = abs((b_[0] - a_[0]) * (c_[1] - a_[1]) - (b_[1] - a_[1]) * (c_[0] - a_[0]))
                R_ = (ab * bc * ca) / (2 * cr) if cr > 1e-9 else float("inf")
                q_ = R_ / (w / 2.0)
                min_r_over_half = q_ if min_r_over_half is None else min(min_r_over_half, q_)
        swept_err.sort()
        lonlat = [frame.lonlat(*c) for c in cpts]
        z = samples.get(lonlat)
        y = [v - frame.elev0 for v in z]
        return conn, y, swept_err, min_r_over_half, flare_end, polyL, polyR

    conn, y, swept_err, min_r_over_half, flare_end, polyL, polyR = connector_of(sides)
    full = None
    if rib is not None:
        # the TRUE flare (returns included) as a connector too: what the opening is, for P3's apron and for the
        # race declaration tests; NOT weldable by the 3-line ribbon (see ribbon.why)
        fc, fy, ferr, _fm, ffe, _pl, _pr = connector_of(true_sides)
        full = {"name": f"north_{wd['junction']}_{PIECE_NAME[wd['piece']]}", "kind": "connector",
                "points_xyz_m": [[r3(c[0]), r3(yy), r3(c[1])] for (c, _w, _k, _u), yy in zip(fc, fy)],
                "widths_m": [r3(w) for _c, w, _k, _u in fc],
                "swept_edge_error_max_m": r2(ferr[-1]) if ferr else None,
                "what": "the full opening incl. the true returns (design geometry for P3's apron; the weld "
                        "rehearsal uses `connector`)"}

    out = {
        "id": wd["id"], "junction": wd["junction"], "piece": wd["piece"], "piece_end": wd["end"],
        "host": "MAINLINE", "host_side": "L", "box": wd["box"], "apex": wd["apex"],
        "kind": "ribbon-through weld (A4: the loop runs through unchanged; this road is welded onto its OUTER edge)",
        "centre_cross": {"vertex": r2(centre_v), "angle_deg": r2(centre_angle), "xz": [r3(X0[0]), r3(X0[1])],
                         "a5_vertex": wd["a5_centre_vertex"]},
        "axis_out_deg": r2(bearing(ax)),
        "curbs": {s_: true_sides[s_]["rec"] for s_ in true_sides},
        "curbs_ribbon": ({s_: sides[s_]["rec"] for s_ in sides} if rib is not None else "= curbs"),
        "ribbon": ({k: v for k, v in rib.items()} if rib is not None else None),
        "aprons": aprons,
        "opening_ribbon": {"vertex_from": r2(opening_rib[0]), "vertex_to": r2(opening_rib[1]),
                           "length_m": r2(arc_len_on_edge(edge, verts, opening_rib[0], opening_rib[1])),
                           "past_box_end": r2(max(0.0, opening_rib[1] - wd["box"][1])),
                           "what": "what the welded stub (the connector below) opens on the loop edge"},
        "opening": {"vertex_from": r2(opening[0]), "vertex_to": r2(opening[1]),
                    "length_m": r2(arc_len_on_edge(edge, verts, opening[0], opening[1])),
                    "a5": wd["a5_opening"],
                    "past_box_end": r2(max(0.0, opening[1] - wd["box"][1])),
                    "before_box_start": r2(max(0.0, wd["box"][0] - opening[0]))},
        "edges_xz": {s_: [[r3(p[0]), r3(p[1])] for p in true_sides[s_]["poly"]] for s_ in ("left", "right")},
        "edges_ribbon_xz": {"left": [[r3(p[0]), r3(p[1])] for p in polyL], "right": [[r3(p[0]), r3(p[1])] for p in polyR]},
        "connector": {"name": f"north_{wd['junction']}_{PIECE_NAME[wd['piece']]}", "kind": "connector",
                      "points_xyz_m": [[r3(c[0]), r3(yy), r3(c[1])] for (c, _w, _k, _u), yy in zip(conn, y)],
                      "widths_m": [r3(w) for _c, w, _k, _u in conn],
                      "part": [k for _c, _w, k, _u in conn],
                      "u_out_m": [r2(uu) for _c, _w, _k, uu in conn],
                      "y_note": "3DEP at each point minus origin.elev_m; tools/route_connectors.py smooths it as a "
                                "route piece (despike + 2 x 75 m mean + the 11 % cap) and trim_connectors blends "
                                "its last 30 m onto the loop deck",
                      "flare_end_out_m": r2(flare_end),
                      "swept_edge_error_m": {"p50": r2(swept_err[len(swept_err) // 2]) if swept_err else None,
                                             "p95": r2(swept_err[int(0.95 * (len(swept_err) - 1))]) if swept_err else None,
                                             "max": r2(swept_err[-1]) if swept_err else None,
                                             "what": "authored curb line vs the edge the ASSEMBLER's sweep of this "
                                                     "centre + width lands on (its 1.5-point smoothing, centred "
                                                     "tangent), every flare point (the piece part follows "
                                                     "the piece's own curbs)"},
                      "fold_margin_min": r2(min_r_over_half) if min_r_over_half is not None else None,
                      "fold_margin_what": "min over the stub of (smoothed centre's plan radius / half width): < 1 = "
                                          "the inside of the sweep runs backwards (the weld's unfold mends it)"},
    }
    if full is not None:
        out["connector_full"] = full
    return out


def arc_len_on_edge(edge, verts, va, vb):
    pa = edge_point_at(edge, verts, va)
    k0 = int(math.floor(va - verts[0])) + 1
    k1 = int(math.floor(vb - verts[0]))
    pts = [pa] + [edge[k] for k in range(k0, k1 + 1)] + [edge_point_at(edge, verts, vb)]
    return arc(pts)[-1]


# ------------------------------------------------------------------------------------------------ pads + stubs

def arm_lines(junction, pieces, eye_rows, frame, osm, legs):
    """every arm of a pad junction: outward unit, axis point, left / right curb offsets, width, kind"""
    arms = []
    for pid, road, a, b in PIECES:
        pc = pieces[pid]
        L = pc["length_m"]
        if a == junction or b == junction:
            end = "start" if a == junction else "end"
            out = (lambda u, L=L, end=end: u if end == "start" else L - u)
            p1, _t, Lo, Ro = piece_frame_at(pc, out(30.0))
            p2, _t2, _Lo2, _Ro2 = piece_frame_at(pc, out(70.0))
            d = (p2[0] - p1[0], p2[1] - p1[1])
            Ld = math.hypot(*d)
            d = (d[0] / Ld, d[1] / Ld)
            if end == "start":
                lo, ro = Lo, Ro
            else:
                lo, ro = -Ro, -Lo
            arms.append({"name": road, "kind": "route", "piece": pid, "piece_end": end, "out": d,
                         "p": p1, "left": lo, "right": ro, "bearing": bearing(d)})
    for sid, j, label, key, alt in STUB_ARMS:
        if j != junction:
            continue
        if key:
            road, brg = key
            row = next(r for r in eye_rows if r["label"].startswith(f"{j} arm {road} brg {brg}"))
            p = frame.xz(float(row["lon"]), float(row["lat"]))
            d = unit_from_bearing(float(brg))
            W = float(row["eye_curb_to_curb_m"])
            m = float(row["median_m"] or 0.0)
            if row["cw_left_m"] and row["cw_right_m"]:
                cl, cr = float(row["cw_left_m"]), float(row["cw_right_m"])
                lo, ro = m / 2 + cl, -(m / 2 + cr)
                # the reading point is the median centre (the eye read across the whole road there)
            else:
                lo, ro = W / 2, -W / 2
            src = f"eye reading '{row['label']}' ({W} m)"
        else:
            w = next(x for x in osm["ways"] if x["id"] == alt["way"])
            pts = [frame.xz(*osm["nodes"][str(n)]) for n in w["nodes"]]
            s = arc(pts)
            p = at_arc(pts, s, min(40.0, s[-1]))
            p0 = pts[0]
            d = (p[0] - p0[0], p[1] - p0[1])
            Ld = math.hypot(*d)
            d = (d[0] / Ld, d[1] / Ld)
            lo, ro = alt["width_m"] / 2, -alt["width_m"] / 2
            src = f"OSM way {alt['way']} first 40 m; width [authored] {alt['width_m']} m (no reading)"
        arms.append({"name": label, "kind": "stub", "stub_id": sid, "out": d, "p": p, "left": lo, "right": ro,
                     "bearing": bearing(d), "src": src})
    arms.sort(key=lambda a: a["bearing"])
    return arms


def corner_radius(junction, ba, bb):
    tab = CORNER_R[junction]
    for (x, y), R in ((k, v) for k, v in tab.items() if k != "default"):
        if abs((ba - float(x) + 180) % 360 - 180) < 25 and abs((bb - float(y) + 180) % 360 - 180) < 25:
            return R, "measured"
    return tab["default"], ("measured" if junction == "J2" else "authored")


def build_pad(junction, node_xz, arms):
    n = len(arms)
    corners = []
    for i in range(n):
        A, B = arms[i], arms[(i + 1) % n]
        R, rsrc = corner_radius(junction, A["bearing"], B["bearing"])
        # A's right curb and B's left curb, both as lines; the fillet centre is R further out on each
        nA, nB = left_normal(A["out"]), left_normal(B["out"])
        pA = (A["p"][0] + nA[0] * (A["right"] - R), A["p"][1] + nA[1] * (A["right"] - R))
        pB = (B["p"][0] + nB[0] * (B["left"] + R), B["p"][1] + nB[1] * (B["left"] + R))
        x = line_intersect(pA, A["out"], pB, B["out"])
        if x is None:
            raise SystemExit(f"[expansion] {junction}: arms {A['name']} / {B['name']} are parallel")
        C = x[2]
        cA = (A["p"][0] + nA[0] * A["right"], A["p"][1] + nA[1] * A["right"])
        cB = (B["p"][0] + nB[0] * B["left"], B["p"][1] + nB[1] * B["left"])
        tA = (C[0] - cA[0]) * A["out"][0] + (C[1] - cA[1]) * A["out"][1]
        tB = (C[0] - cB[0]) * B["out"][0] + (C[1] - cB[1]) * B["out"][1]
        TA = (cA[0] + A["out"][0] * tA, cA[1] + A["out"][1] * tA)
        TB = (cB[0] + B["out"][0] * tB, cB[1] + B["out"][1] * tB)
        # tangent distance measured from the junction node along each arm
        dA = (TA[0] - node_xz[0]) * A["out"][0] + (TA[1] - node_xz[1]) * A["out"][1]
        dB = (TB[0] - node_xz[0]) * B["out"][0] + (TB[1] - node_xz[1]) * B["out"][1]
        corners.append({"a": i, "b": (i + 1) % n, "R": R, "R_source": rsrc, "C": C, "TA": TA, "TB": TB,
                        "dA": dA, "dB": dB, "arc": arc_points(C, TA, TB, step=0.7)})
    cut = []
    for i in range(n):
        prev = corners[(i - 1) % n]
        nxt = corners[i]
        cut.append(max(prev["dB"], nxt["dA"]) + PAD_CUT_PAD_M)
    outline = []
    for i in range(n):
        A = arms[i]
        nA = left_normal(A["out"])
        # the arm's cut line at distance cut[i] from the node, from its left curb to its right curb
        base = (node_xz[0] + A["out"][0] * cut[i], node_xz[1] + A["out"][1] * cut[i])
        # the axis passes through A["p"]: the lateral of the node off the axis
        lat_node = (node_xz[0] - A["p"][0]) * nA[0] + (node_xz[1] - A["p"][1]) * nA[1]
        Lc = (base[0] + nA[0] * (A["left"] - lat_node), base[1] + nA[1] * (A["left"] - lat_node))
        Rc = (base[0] + nA[0] * (A["right"] - lat_node), base[1] + nA[1] * (A["right"] - lat_node))
        A["cut_m"] = cut[i]
        A["cut_line"] = [Lc, Rc]
        c = corners[i]
        outline += [Lc, Rc] + c["arc"]
    return corners, outline


def build_stub(arm, junction):
    nA = left_normal(arm["out"])
    Lc, Rc = arm["cut_line"]
    Lf = (Lc[0] + arm["out"][0] * STUB_LEN_M, Lc[1] + arm["out"][1] * STUB_LEN_M)
    Rf = (Rc[0] + arm["out"][0] * STUB_LEN_M, Rc[1] + arm["out"][1] * STUB_LEN_M)
    return {"id": arm["stub_id"], "junction": junction, "road": arm["name"], "bearing_out_deg": r2(arm["bearing"]),
            "width_m": r2(arm["left"] - arm["right"]), "src": arm["src"],
            "mouth_line_xz": [[r3(Lc[0]), r3(Lc[1])], [r3(Rc[0]), r3(Rc[1])]],
            "pavement_xz": [[r3(p[0]), r3(p[1])] for p in (Lc, Rc, Rf, Lf)],
            "wall": "invisible wall across the mouth line (JUNCTIONS rule 18c): see-only, never drivable (A1)",
            "length_m": STUB_LEN_M}


# ------------------------------------------------------------------------------------------------ medians

def build_medians(pieces, clear):
    """runs of raised / flush medians per piece -> numbered polygons. clear: pid -> [(s0, s1)] keep-out spans"""
    out = []
    k = 0
    for pid, *_ in PIECES:
        pc = pieces[pid]
        recs = pc["recs"]
        gaps = GAPS.get(pid, [])

        def blocked(s):
            if any(a <= s <= b for a, b in clear.get(pid, [])):
                return True
            return any(abs(s - g) <= w / 2.0 for g, w in gaps)
        i = 0
        while i < len(recs):
            r = recs[i]
            if r["mtype"] in ("none", "line") or r["m"] <= 0.05 or blocked(r["s"]):
                i += 1
                continue
            j = i
            while j < len(recs) and recs[j]["mtype"] == r["mtype"] and recs[j]["m"] > 0.05 and not blocked(recs[j]["s"]):
                j += 1
            run = recs[i:j]
            if len(run) >= 3:
                k += 1
                s0, s1 = run[0]["s"], run[-1]["s"]
                left, right = [], []
                for q in run:
                    w = q["m"]
                    taper = min(1.0, (q["s"] - s0) / NOSE_M, (s1 - q["s"]) / NOSE_M)
                    w = max(NOSE_W_M, w * max(0.0, taper)) if q["mtype"] in RAISED else w * max(0.0, min(1.0, taper * 2))
                    c = offset_pt(q["p"], q["t"], q["moff"])
                    left.append(offset_pt(c, q["t"], w / 2.0))
                    right.append(offset_pt(c, q["t"], -w / 2.0))
                poly = left + right[::-1]
                ws = [q["m"] for q in run]
                out.append({"id": f"MD{k}", "piece": pid, "type": run[0]["mtype"],
                            "raised": run[0]["mtype"] in RAISED, "s_from": r2(s0), "s_to": r2(s1),
                            "width_m": [r2(min(ws)), r2(max(ws))],
                            "polygon_xz": [[r3(p[0]), r3(p[1])] for p in poly]})
            i = max(j, i + 1)
    return out


# ------------------------------------------------------------------------------------------------ profile + checks

def smooth_profile(z, spacing, cap=None):
    """tools/route_connectors.py _despike_smooth_cap, with the cap optional (checked, never applied blind)"""
    n = len(z)
    med = [z[0]] + [sorted(z[i - 1:i + 2])[1] for i in range(1, n - 1)] + [z[-1]]
    k = max(3, round(75.0 / spacing)) | 1
    h = k // 2
    sm = list(med)
    for _ in range(2):
        sm = [sum(sm[max(0, i - h):min(n, i + h + 1)]) / len(sm[max(0, i - h):min(n, i + h + 1)]) for i in range(n)]
    if cap is not None:
        c = cap * spacing
        for i in range(1, n):
            sm[i] = max(sm[i - 1] - c, min(sm[i - 1] + c, sm[i]))
        for i in range(n - 2, -1, -1):
            sm[i] = max(sm[i + 1] - c, min(sm[i + 1] + c, sm[i]))
    return sm


def max_grade(s, y, chord=20.0):
    best = (0.0, None)
    j = 0
    for i in range(len(s)):
        while j < len(s) and s[j] - s[i] < chord:
            j += 1
        if j >= len(s):
            break
        g = (y[j] - y[i]) / (s[j] - s[i])
        if abs(g) > abs(best[0]):
            best = (g, (s[i] + s[j]) / 2.0)
    return best


def cross_sections(pieces, frame, samples):
    out = []
    for pid, *_ in PIECES:
        pc = pieces[pid]
        L = pc["length_m"]
        for end in ("start", "end"):
            secs = []
            u = 0.0
            while u <= XS_REACH_M + 1e-9:
                s = u if end == "start" else L - u
                p, t, Lo, Ro = piece_frame_at(pc, s)
                offs = [-XS_HALF_M + XS_STEP_M * k for k in range(int(2 * XS_HALF_M / XS_STEP_M) + 1)]
                pts = [offset_pt(p, t, o) for o in offs]
                z = samples.get([frame.lonlat(*q) for q in pts])
                zc = z[offs.index(0.0)]
                rel = [r2(v - zc) for v in z]

                def at(o):
                    k = min(range(len(offs)), key=lambda i: abs(offs[i] - o))
                    return rel[k]
                secs.append({"s": r2(s), "u_from_end": r2(u), "curb_L_m": r2(Lo), "curb_R_m": r2(Ro),
                             "ground_minus_centre": {"curb_L": at(Lo), "curb_R": at(Ro), "+20": at(20.0), "-20": at(-20.0),
                                                     "+40": at(40.0), "-40": at(-40.0)},
                             "max_cut_m": max(rel), "max_fill_m": -min(rel)})
                u += XS_EVERY_M
            out.append({"piece": pid, "end": end, "junction": pc["from"] if end == "start" else pc["to"],
                        "offsets_m": [-XS_HALF_M, XS_HALF_M, XS_STEP_M], "sections": secs})
    return out


# ------------------------------------------------------------------------------------------------ main

def build(track: Path, offline: bool = False) -> dict:
    north, cl, osm, eye, meas, prov = load_inputs(track)
    measured, mprov = load_paint_measured(track)
    if mprov:
        prov["aerial__paint_north.json"] = mprov
    frame = Frame(cl["origin"])
    samples = Samples(track / "data" / "expansion.north.samples.json.gz", offline)
    legs = split_legs(north, frame)
    pieces, stations = build_pieces(legs, frame, eye, osm, measured)

    # junctions
    jf = north["junctions"]["fwd"]
    node_ll = {}
    for nid, c in zip(north["nodes"], north["coords"]):
        node_ll[nid] = c
    junctions = {}
    jz = samples.get([tuple(node_ll[jf[j]]) for j in ("J1", "J2", "J3", "J4", "J5")])
    for (j, z) in zip(("J1", "J2", "J3", "J4", "J5"), jz):
        ll = node_ll[jf[j]]
        x, zz = frame.xz(*ll)
        junctions[j] = {"node": jf[j], "lonlat": [ll[0], ll[1]], "xz": [r3(x), r3(zz)], "y_3dep_m": r3(z - frame.elev0),
                        "z_3dep_m": r2(z), "measure_json_m": meas.get("junction_3dep_m", {}).get(j),
                        "kind": "weld" if j in ("J1", "J5") else "pad"}

    # profiles
    for pid, *_ in PIECES:
        pc = pieces[pid]
        ll = [frame.lonlat(*r["p"]) for r in pc["recs"]]
        z = samples.get(ll)
        for r, v in zip(pc["recs"], z):
            r["z3"] = v
        s = [r["s"] for r in pc["recs"]]
        zc = smooth_profile(z, SPACING_M)
        zcap = smooth_profile(z, SPACING_M, cap=MAX_GRADE)
        binds = max(abs(a - b) for a, b in zip(zc, zcap))
        g_raw = max_grade(s, smooth_profile_light(z))
        g_sm = max_grade(s, zc)
        pc["profile"] = {"z_start": r2(z[0]), "z_end": r2(z[-1]), "z_min": r2(min(z)), "z_max": r2(max(z)),
                         "s_at_max": r2(s[z.index(max(z))]),
                         "max_grade_pct_3dep_20m": [r2(100 * g_raw[0]), r2(g_raw[1]) if g_raw[1] is not None else None],
                         "max_grade_pct_connector_smoothed": [r2(100 * g_sm[0]), r2(g_sm[1]) if g_sm[1] is not None else None],
                         "cap_pct": 100 * MAX_GRADE, "cap_binds_m": r3(binds), "cap_binds": binds > 1e-6}
        for r, a in zip(pc["recs"], zc):
            r["zs"] = a

    # welds
    welds = [build_weld(wd, pieces[wd["piece"]], cl, frame, samples) for wd in WELDS]

    # pads + stubs
    pads, stubs = [], []
    for j in ("J2", "J3", "J4"):
        node = tuple(junctions[j]["xz"])
        arms = arm_lines(j, pieces, eye, frame, osm, legs)
        corners, outline = build_pad(j, node, arms)
        pads.append({"id": j, "y_3dep_m": junctions[j]["y_3dep_m"], "z_3dep_m": junctions[j]["z_3dep_m"],
                     "node_xz": [r3(node[0]), r3(node[1])],
                     "arms": [{"name": a["name"], "kind": a["kind"], "piece": a.get("piece"), "piece_end": a.get("piece_end"),
                               "stub": a.get("stub_id"), "bearing_out_deg": r2(a["bearing"]), "width_m": r2(a["left"] - a["right"]),
                               "left_m": r2(a["left"]), "right_m": r2(a["right"]), "cut_from_node_m": r2(a["cut_m"]),
                               "cut_line_xz": [[r3(p[0]), r3(p[1])] for p in a["cut_line"]]} for a in arms],
                     "corners": [{"between": [arms[c["a"]]["name"], arms[c["b"]]["name"]], "R_m": c["R"],
                                  "R_source": c["R_source"], "centre_xz": [r3(c["C"][0]), r3(c["C"][1])],
                                  "tangents_from_node_m": [r2(c["dA"]), r2(c["dB"])]} for c in corners],
                     "outline_xz": [[r3(p[0]), r3(p[1])] for p in outline],
                     "radii_source": CORNER_R_SOURCE})
        for a in arms:
            if a["kind"] == "stub":
                stubs.append(build_stub(a, j))
            else:
                pc = pieces[a["piece"]]
                L = pc["length_m"]
                cut_s = a["cut_m"] if a["piece_end"] == "start" else L - a["cut_m"]
                pc.setdefault("cuts", {})[a["piece_end"]] = {"at": j, "s": r2(cut_s), "kind": "pad"}
    for w in welds:
        pc = pieces[w["piece"]]
        L = pc["length_m"]
        # the piece's first station clear of the loop edge (the centre crossing, along the piece)
        d = project_index(tuple(w["centre_cross"]["xz"]), pc["midline"]["pts"])[1]
        pc.setdefault("cuts", {})[w["piece_end"]] = {"at": w["junction"], "s": r2(d), "kind": "weld"}

    # medians, clear of every pad cut / weld opening
    clear = {}
    for pid, *_ in PIECES:
        pc = pieces[pid]
        L = pc["length_m"]
        c = pc.get("cuts", {})
        s0 = c.get("start", {}).get("s", 0.0) + NOSE_CLEAR_M
        s1 = c.get("end", {}).get("s", L) - NOSE_CLEAR_M
        if c.get("start", {}).get("kind") == "weld":
            s0 = c["start"]["s"] + max(NOSE_CLEAR_M, welds[0]["connector"]["flare_end_out_m"])
        if c.get("end", {}).get("kind") == "weld":
            s1 = c["end"]["s"] - max(NOSE_CLEAR_M, welds[1]["connector"]["flare_end_out_m"])
        clear[pid] = [(-1.0, s0), (s1, L + 1.0)]
    medians = build_medians(pieces, clear)

    # aerial width stations, numbered
    st_out = []
    for k, (pid, rec) in enumerate(sorted(stations, key=lambda x: ("ABCD".index(x[0]), x[1]["s"])), start=1):
        pc = pieces[pid]
        s = rec["s"]
        Lo = interp_rows(pc["rows"], s, "L")
        Ro = interp_rows(pc["rows"], s, "R")
        p, t, _l, _r = piece_frame_at(pc, s)
        st_out.append({"n": k, "label": rec["row"]["label"], "piece": pid, "s": r2(s), "kind": rec["kind"],
                       "eye_width_m": float(rec["row"]["eye_curb_to_curb_m"]), "eye_conf_m": float(rec["row"]["eye_conf_m"] or 1.0),
                       "built_width_m": r2(Lo - Ro), "median_m": float(rec["row"]["median_m"] or 0.0),
                       "median_kind": rec["row"]["median_kind"], "reading_off_line_m": r2(rec["off_line_m"]),
                       "left_xz": [r3(v) for v in offset_pt(p, t, Lo)], "right_xz": [r3(v) for v in offset_pt(p, t, Ro)]})

    xs = cross_sections(pieces, frame, samples)
    samples.save()

    # pieces out
    pieces_out = []
    checks = {"midline": {}, "grade": {}, "junction_heights": {}, "welds": {}}
    for pid, *_ in PIECES:
        pc = pieces[pid]
        recs = pc["recs"]
        dv = sorted(pc["dev"])
        p95 = dv[int(0.95 * (len(dv) - 1))]
        checks["midline"][pid] = {"p95_m": r2(p95), "max_m": r2(dv[-1]), "limit_p95_m": MIDLINE_P95_MAX_M,
                                  "pass": p95 <= MIDLINE_P95_MAX_M,
                                  "what": "smoothed centreline vs the raw OSM midline (two carriageways) / OSM line (one)"}
        checks["grade"][pid] = dict(pc["profile"])
        pieces_out.append({
            "id": pid, "name": pc["name"], "road": pc["road"], "from": pc["from"], "to": pc["to"],
            "length_m": r2(pc["length_m"]), "spacing_m": SPACING_M, "n": len(recs),
            "cuts": pc.get("cuts", {}), "osm_divided_end_s": pc["osm_divided_end"],
            "columns": ["s", "x", "z", "y_3dep", "y_smooth", "left_m", "right_m", "median_w_m", "median_off_m",
                        "median_type", "osm_sep_m", "lanes_fwd", "lanes_rev", "median_src"],
            "stations": [[r2(r["s"]), r3(r["p"][0]), r3(r["p"][1]), r3(r["z3"] - frame.elev0), r3(r["zs"] - frame.elev0),
                          r2(r["L"]), r2(r["R"]), r2(r["m"]), r2(r["moff"]), r["mtype"], r2(r["sep"]),
                          r["lanes_fwd"], r["lanes_rev"], r["paint_src"]] for r in recs],
            "paint_measured": pc["paint_measured"],
            "maxspeed": sorted({r["maxspeed"] for r in recs if r["maxspeed"]}),
            "width_readings": [{"label": r["label"], "s": r2(r["s"]), "left_m": r2(r["L"]), "right_m": r2(r["R"]),
                                "median_m": r2(r["m"]), "type": r["type"], "divided_osm": r["divided"]} for r in pc["rows"]],
            "paint": PAINT[pid],
        })
    for j, rec in junctions.items():
        mj = rec["measure_json_m"]
        checks["junction_heights"][j] = {"z_3dep_m": rec["z_3dep_m"], "measure_json_m": mj,
                                         "diff_m": r2(rec["z_3dep_m"] - mj) if mj is not None else None}
    for w in welds:
        checks["welds"][w["id"]] = {"opening": w["opening"], "centre_cross_vertex": w["centre_cross"]["vertex"],
                                    "a5_centre_vertex": w["centre_cross"]["a5_vertex"],
                                    "swept_edge_error_m": w["connector"]["swept_edge_error_m"]}
    doc = {
        "version": VERSION,
        "_doc": __doc__.split("\n\n")[0] + " Written by tools/author_expansion.py; read by tools/plot_expansion_plan.py, "
                "tools/route_connectors.py (route_connectors.authored_take) and P3's builders. Nothing here is a mesh.",
        "ledger": "0054", "plan": "tracks/san-diego-lake-murray/EXPANSION-PLAN.md P1",
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "frame": {"what": "local ENU metres of data/centerline.local.json (x east, z north, y = height over origin.elev_m)",
                  "origin": cl["origin"], "projection": "scripts-v021/geometry/projection.py series"},
        "stations_frame": "s = metres from the junction node at the start of each leg, along the OSM forward leg "
                          "(EXPANSION-PLAN 'Stations'); left / right offsets + = left of the forward direction",
        "provenance": prov,
        "parameters": {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float))},
        "junctions": junctions,
        "pieces": pieces_out,
        "medians": medians,
        "pads": pads,
        "welds": welds,
        "stubs": stubs,
        "width_stations": st_out,
        "cross_sections": xs,
        "checks": checks,
    }
    return doc


def smooth_profile_light(z):
    """a 25 m mean (revise/measure.json's 'grades over a 20 m chord after a 25 m smooth')"""
    n = len(z)
    h = int(round(12.5 / SPACING_M))
    return [sum(z[max(0, i - h):min(n, i + h + 1)]) / len(z[max(0, i - h):min(n, i + h + 1)]) for i in range(n)]


PAINT = {  # per piece, from the dossier §2 (aerial + OSM); a Street View pass confirms before P3 (Risk 7)
    "A": {"centre": "raised planted median (MD runs); left-turn pockets at Eldridge (st ~415-440)",
          "lanes": "2 + 2 (3 at the turn pockets), white dashed lane lines", "edges": "bike lanes both sides",
          "crosswalks": ["J1 yellow school ladder across College", "Eldridge St signal st ~415-446", "J2 yellow ladders"]},
    "B": {"centre": "measured off NAIP (repair round 2): double yellow st 0-399 (narrow painted tapers st ~100-140, "
                    "~190-220); raised island st 399-535 with the Fontaine left-turn pocket (~480); a painted median "
                    "st 560-610; a raised planted island st 612-700; turn-pocket paint st ~720-805; a painted centre "
                    "lane 5-6 m wide st ~840-1010",
          "lanes": "2 + 2, then 3 + 2 on the last 614 m", "edges": "parking lanes both sides",
          "crosswalks": ["J2 yellow school ladder", "Glenroy St signal st 79-88 yellow ladder"]},
    "C": {"centre": "terracotta raised median (MD runs); crossovers st 174 / 202; turn pockets at Margerum (st 1099-1108)",
          "lanes": "3 + 3, white dashed", "edges": "bike lanes both sides",
          "crosswalks": ["J3 ladders", "J4 white ladders"]},
    "D": {"centre": "measured off NAIP (repair round 2): a raised concrete island st 32-118 then the hatched teardrop "
                    "to ~172 on the J4 approach; the painted double-double-yellow median 1.7-6.6 m wide, ~1.6 m LEFT of "
                    "the road's middle on the 1 km climb (the lanes are uneven: one down, two up), opening into left-turn "
                    "pockets at the side streets; a plain double yellow where it narrows (Hemingway st ~380-520, "
                    "st ~1500-1545, Park Ridge st ~1620-1710)",
          "lanes": "2 + 2 (1 down / 2 up on the 763 m way)", "edges": "buffered bike lanes both sides",
          "crosswalks": ["J4 ladders", "Park Ridge Blvd signal st 1623-1635", "J5 crosswalks"]},
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--track", default=str(TRACK_DEFAULT))
    ap.add_argument("--offline", action="store_true", help="refuse to fetch 3DEP (every sample must be cached)")
    a = ap.parse_args(argv)
    track = Path(a.track)
    doc = build(track, offline=a.offline)
    out = track / "data" / "expansion.north.json"
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    c = doc["checks"]
    for pid in "ABCD":
        p = next(x for x in doc["pieces"] if x["id"] == pid)
        g = c["grade"][pid]
        print(f"[expansion] {pid} {p['road']}: {p['length_m']} m, {p['n']} stations; midline p95 "
              f"{c['midline'][pid]['p95_m']} m (max {c['midline'][pid]['max_m']}); 3DEP {g['z_start']} -> {g['z_end']} m, "
              f"max grade {g['max_grade_pct_3dep_20m'][0]} % at s {g['max_grade_pct_3dep_20m'][1]}; cap binds "
              f"{g['cap_binds_m']} m; cuts {p['cuts']}")
    for w in doc["welds"]:
        o = w["opening"]
        print(f"[expansion] {w['id']} {w['junction']}: centre crosses the loop edge at v{w['centre_cross']['vertex']} "
              f"({w['centre_cross']['angle_deg']} deg; A5 ~v{w['centre_cross']['a5_vertex']}); opening v{o['vertex_from']} -> "
              f"v{o['vertex_to']} ({o['length_m']} m; A5 {o['a5']}), {o['past_box_end']} vertices past box end "
              f"v{w['box'][1]}; stub {len(w['connector']['widths_m'])} pts, width {min(w['connector']['widths_m'])}.."
              f"{max(w['connector']['widths_m'])} m, swept-edge error {w['connector']['swept_edge_error_m']}")
        for side, r in w["curbs"].items():
            print(f"            {side}: {json.dumps(r)}")
    for p in doc["pads"]:
        print(f"[expansion] pad {p['id']}: y {p['z_3dep_m']} m, arms " +
              ", ".join(f"{a['name'][:18]} {a['bearing_out_deg']:.0f} deg w {a['width_m']} cut {a['cut_from_node_m']} m"
                        for a in p["arms"]) + "; corners R " + "/".join(str(c["R_m"]) for c in p["corners"]))
    print(f"[expansion] {len(doc['medians'])} median runs, {len(doc['stubs'])} stubs, {len(doc['width_stations'])} "
          f"width stations; junction heights {json.dumps(c['junction_heights'])}")
    print(f"[expansion] wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
