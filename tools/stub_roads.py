"""PHASE 5 (ledger 0054, Kevin 2026-10-14): "We are going to change intersections, such that a road we are not
completing gets a barrier, not a curve." — the DECLARATION and the DRAFT of every unbuilt side road's STUB.

Today an unbuilt side street does not exist: the host's curb and sidewalk run straight past where it would join, so
the road is erased. Phase 5 gives every unbuilt PUBLIC side road its real mouth (curb returns, the host sidewalk
gapped), a short STUB of real road (drivable 1ROAD at its real width, heading and 3DEP grade, with lane paint), and
a visible, physical BARRIER across the stub (Kevin's owned 4.04 m K-rail jersey module, the race walls' own
profile). A stub IS a connector: it rides the whole existing side-street chain (trim_connectors cuts it at the host
edge and records its mouth, build_loop_blend sweeps its road / curb / sidewalk / paint, weld_mouths_blend welds it,
seat_terrain seats the ground, gap_mouths gaps the host sidewalk, verify_mouths gates the mouth); what is new is
in tools/author_stubs_blend.py (the curb RETURNS, the corner pavement and the barrier) and tools/verify_stubs.py
(the gate on the BUILT road).

DRIVEWAYS / SERVICE WAYS (the lighter treatment, decided here): a `highway=service` mouth (driveways, parking aisles,
utility roads) gets NO stub and NO barrier — only a CURB CUT: the host's curb stays continuous (no sidewalk gap) and
its curb top drops to CURB_CUT_LIP_M over the driveway width, flaring back to full height over CURB_CUT_FLARE_M
each side, so the sidewalk slab ramps down to the gutter like a real driveway apron. Freeway ramps (`*_link`,
`motorway`) are declared `skip` (phase 4 builds the ramps); Kevin can override any entry.

Two subcommands:

  declare  python tools/stub_roads.py declare <project> --osm <osm.json> --out <stubs.json>
                 [--host MAINLINE] [--streets "College Avenue,Navajo Road"] [--only <id,id>] [--merge <old stubs.json>]
           Every junction between a PUBLIC OSM way and the host (the built mainline, or a named connector piece):
           one entry per branch that LEAVES the host, with way id, junction node, name, highway class, host
           vertex / station, side, heading, junction angle, width (OSM `width`, else `lanes`, else the class
           default — `width_source` says which), length, barrier style and a treatment: `stub` (public, unbuilt),
           `curb_cut` (service), or `skip` with a `skip_reason` (already built as a connector / a freeway ramp /
           parallel to the host). --merge keeps the hand overrides of an older declaration (every key listed in
           an entry's `hand` list). With --only, every other entry is written as `skip` ("not selected").
  apply    python tools/stub_roads.py apply <project> [--decl <stubs.json>]
           The draft step (tools/ship_sd.sh: after divide_connectors, before trim_connectors). With NO declaration
           (default <project>/data/stubs.json absent) it prints that and touches nothing — opt-in, byte-identical.
           Otherwise each `stub` entry becomes a connector `STUB_<id>` APPENDED to data/connectors.local.json and
           its .pre-trim (every existing block keeps its vertex range): the OSM branch from inside the host out
           to the barrier + TAIL_M, resampled every SPACING_M, at a height profile anchored on the host
           centreline at the cut (trim_connectors.host_height, the same interpolation trim lands the cut on):
               y(u) = host_y + g0 u + (g - g0) F(u),   F' = smoothstep(u / T)        (the FINISHED stub)
           drafted as y(u) - g0 u smoothstep(1 - u / 30): weld_mouths_blend warps every row of a stub (it is shorter
           than the weld's 30 m blend) onto the host deck extended along it, which lays in that very term itself —
           the draft leaves it out so the host's grade is never counted twice.
           g = the 3DEP grade (least squares over the stub, data/stubs.3dep.json caches the samples), g0 = the
           host's own grade along the stub direction (no grade kink at the mouth line), T = the vertical-curve
           length: max(RAMP_MIN_M, 1.5 |g - g0| / RAMP_DG_PER_M). The connector carries `blend_m: 0` (trim's
           30 m height blend would halve a 15 m stub's real rise) and `stub` (trim never extends a stub end to a
           host). Writes data/stubs.plan.json (everything the Blender pass and the gate read).

All numbers marked [INVENTED] are in fleet/GATES-CHANGELOG.md (2026-10-14, phase 5).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AIROSO = HERE.parent

STUB_PREFIX = "STUB_"
STUB_LENGTH_M = 15.0      # [INVENTED] mouth line (host pavement edge) -> barrier centre, along the stub
TAIL_M = 1.0              # [INVENTED] road behind the barrier centre: the 0.67 m jersey base stands wholly on the stub
SPACING_M = 1.0           # stub polyline spacing (the ribbon rows; the loop's own rows are ~3 m — never coarser)
OVERLAP_M = 0.4           # tools/trim_connectors.py OVERLAP_M (the cut stands this far inside the host edge)
MIN_PIECE_M = 15.0        # tools/trim_connectors.py MIN_PIECE_M: a shorter piece is dropped there
MIN_LENGTH_M = MIN_PIECE_M - OVERLAP_M - TAIL_M + 0.05   # the shortest declarable stub that survives the trim
RAMP_DG_PER_M = 0.015     # [INVENTED] the stub's vertical curve changes grade at most this per metre (half of
#                           verify_mouths' APPROACH_DG_PER_M 0.03, measured over its 2.5 m wheelbase)
RAMP_MIN_M = 4.0          # [INVENTED] the shortest vertical curve, even on a level stub
WELD_BLEND_M = 30.0       # tools/mouth_weld.py BLEND_M: the weld warps a stub's every row (it is shorter than this)
GRADE_CAP = 0.15          # [INVENTED] a 3DEP grade steeper than this is capped (and reported) — a DEM artefact guard
HOST_REACH_M = 3.0        # an OSM node within half-width + this of the BUILT centreline is "on the host" (the median
#                           tool moves the built line up to 12 m off OSM on College / Navajo; the half-width absorbs it)
PARALLEL_DEG = 25.0       # a branch leaving the host at less than this is a carriageway / slip lane, not a side road
BUILT_TOL_M = 6.0         # a connector point within this of the branch 5-25 m out: the side road is already built
BRANCH_OUT_M = 40.0       # the OSM branch geometry kept per entry
CURB_CUT_LIP_M = 0.03     # [INVENTED] a driveway curb cut's lip over the gutter (the curb is 0.14 m)
CURB_CUT_FLARE_M = 1.5    # [INVENTED] ... flaring back to full height over this each side
SERVICE_WIDTH_M = 4.0     # [INVENTED] a driveway / service mouth's apron width when OSM gives none
# [INVENTED] class widths when OSM carries neither `width` nor `lanes` (residential = route_connectors.WIDTH_M, the
# width every built Lake Murray side street has)
CLASS_WIDTH_M = {"residential": 10.0, "unclassified": 10.0, "living_street": 8.0, "tertiary": 12.0,
                 "secondary": 14.0, "primary": 16.0}
LANE_W_M = 3.6            # [INVENTED] per OSM lane ...
GUTTER_W_M = 1.2          # [INVENTED] ... plus a gutter / parking strip each side
PUBLIC = ("residential", "unclassified", "living_street", "tertiary", "secondary", "primary")
SKIP_CLASSES = {"motorway": "freeway — phase 4 builds the I-8", "motorway_link": "freeway ramp — phase 4 builds the ramps",
                "trunk": "trunk road", "trunk_link": "trunk ramp", "primary_link": "slip / ramp link",
                "secondary_link": "slip / ramp link", "tertiary_link": "slip / ramp link"}
BARRIERS = ("krail", "type3")
TREATMENTS = ("stub", "curb_cut", "skip")


def _load_tool(stem, alias):
    spec = importlib.util.spec_from_file_location(alias, HERE / f"{stem}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TRIM = _load_tool("trim_connectors", "_trim_connectors_ro")


# ------------------------------------------------------------------------------------------------ frames

def mpd(lat0):
    """metres per degree (lon, lat) — tools/route_connectors.py's projection of the project origin"""
    r = 6371000.0
    return r * math.cos(math.radians(lat0)) * math.pi / 180.0, r * math.pi / 180.0


def to_local(lon, lat, origin):
    mx, mz = mpd(origin["lat"])
    return (lon - origin["lon"]) * mx, (lat - origin["lat"]) * mz


def to_lonlat(x, z, origin):
    mx, mz = mpd(origin["lat"])
    return origin["lon"] + x / mx, origin["lat"] + z / mz


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s or "unnamed").lower()).strip("_") or "unnamed"


def smoothstep(x):
    x = 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)
    return x * x * (3.0 - 2.0 * x)


def ramp_F(u, T):
    """integral of smoothstep(t / T) dt from 0 to u (u >= 0): the vertical curve's unit-rise shape"""
    if u <= 0.0:
        return 0.0
    if u >= T:
        return u - T / 2.0
    x = u / T
    return T * (x ** 3 - 0.5 * x ** 4)


def profile_y(u, host_y, g0, g, T):
    """the stub's FINISHED height at u metres from the cut (u < 0: inside the host, on the host's own grade):
    on the host's grade along the stub at the mouth, into the 3DEP grade through the vertical curve"""
    if u <= 0.0:
        return host_y + g0 * u
    return host_y + g0 * u + (g - g0) * ramp_F(u, T)


def weld_warp(u, g0, blend_m=WELD_BLEND_M):
    """what tools/weld_mouths_blend.py will ADD at u: it warps every row within its blend onto the host deck extended
    level across (mouth_weld.weld_end: (host deck under the point - the level end) x smoothstep(1 - s / blend)), and
    beyond a host's edge that deck rises on the host's own grade along the stub: g0 u"""
    if u <= 0.0:
        return 0.0
    return g0 * u * smoothstep(1.0 - u / blend_m)


def draft_y(u, host_y, g0, g, T):
    """the height the DRAFT carries (connectors.local.json): the finished profile less the weld's warp, so the welded
    stub is profile_y — the host-grade term is laid in by the weld, never twice"""
    return profile_y(u, host_y, g0, g, T) - weld_warp(u, g0)


def ramp_length(g, g0):
    return max(RAMP_MIN_M, 1.5 * abs(g - g0) / RAMP_DG_PER_M)


def fit_grade(us, ds):
    """least-squares slope of ds over us"""
    n = len(us)
    if n < 2:
        return 0.0, 0.0
    mu, md = sum(us) / n, sum(ds) / n
    suu = sum((u - mu) ** 2 for u in us)
    if suu < 1e-9:
        return 0.0, 0.0
    g = sum((u - mu) * (d - md) for u, d in zip(us, ds)) / suu
    res = [d - (md + g * (u - mu)) for u, d in zip(us, ds)]
    return g, math.sqrt(sum(r * r for r in res) / n)


# ------------------------------------------------------------------------------------------------ polylines

class Line:
    """a host polyline in plan with widths: projection (distance, seg, t, signed lateral +left, arc s)"""

    def __init__(self, pts, widths, closed=None):
        self.p = [tuple(q) for q in pts]
        self.w = list(widths)
        self.closed = (abs(self.p[0][0] - self.p[-1][0]) < 1e-6 and abs(self.p[0][2] - self.p[-1][2]) < 1e-6) \
            if closed is None else closed
        self.s = [0.0]
        for i in range(1, len(self.p)):
            self.s.append(self.s[-1] + math.hypot(self.p[i][0] - self.p[i - 1][0], self.p[i][2] - self.p[i - 1][2]))
        self.cells = {}
        for i in range(len(self.p) - 1):
            a, b = self.p[i], self.p[i + 1]
            for cx in range(int(math.floor(min(a[0], b[0]) / 50.0)) - 1, int(math.floor(max(a[0], b[0]) / 50.0)) + 2):
                for cz in range(int(math.floor(min(a[2], b[2]) / 50.0)) - 1, int(math.floor(max(a[2], b[2]) / 50.0)) + 2):
                    self.cells.setdefault((cx, cz), []).append(i)

    def project(self, x, z):
        segs = self.cells.get((int(math.floor(x / 50.0)), int(math.floor(z / 50.0))))
        rng = segs if segs else range(len(self.p) - 1)
        best = None
        for i in rng:
            a, b = self.p[i], self.p[i + 1]
            dx, dz = b[0] - a[0], b[2] - a[2]
            L2 = dx * dx + dz * dz
            if L2 < 1e-12:
                continue
            t = max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[2]) * dz) / L2))
            d = math.hypot(x - (a[0] + dx * t), z - (a[2] + dz * t))
            if best is None or d < best[0]:
                lat = (-dz * (x - a[0]) + dx * (z - a[2])) / math.sqrt(L2)
                best = (d, i, t, lat, self.s[i] + (self.s[i + 1] - self.s[i]) * t)
        return best

    def half(self, i, t):
        j = min(len(self.w) - 1, i + 1)
        return (self.w[i] * (1 - t) + self.w[j] * t) / 2.0

    def tangent(self, i):
        a, b = self.p[i], self.p[min(len(self.p) - 1, i + 1)]
        dx, dz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(dx, dz) or 1.0
        return dx / L, dz / L

    def grade(self, i):
        a, b = self.p[i], self.p[min(len(self.p) - 1, i + 1)]
        run = math.hypot(b[0] - a[0], b[2] - a[2])
        return 0.0 if run < 1e-9 else (b[1] - a[1]) / run


def resample(pts, step):
    """[(x, z)] at `step` along the polyline (last point kept)"""
    out = [pts[0]]
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if seg == 0:
            continue
        while acc + step <= seg + 1e-9:
            acc += step
            t = acc / seg
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        acc -= seg
    if math.hypot(out[-1][0] - pts[-1][0], out[-1][1] - pts[-1][1]) > 1e-6:
        out.append(pts[-1])
    return out


def point_at(pts, u):
    """(x, z, tx, tz) at arc u along [(x, z)] (extrapolated past either end on the end segment)"""
    acc = 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if seg < 1e-12:
            continue
        if u <= acc + seg or i == len(pts) - 2:
            t = (u - acc) / seg
            tx, tz = (b[0] - a[0]) / seg, (b[1] - a[1]) / seg
            if u < 0 and i == 0:
                t = u / seg
            return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, tx, tz
        acc += seg
    a = pts[0]
    return a[0], a[1], 1.0, 0.0


def polyline_length(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


# ------------------------------------------------------------------------------------------------ declare

def width_of(tags):
    """(width_m, source) — OSM width, else lanes, else the class default"""
    w = tags.get("width")
    if w:
        try:
            v = float(str(w).split()[0].replace("m", ""))
            if 3.0 <= v <= 40.0:
                return v, f"osm width={w}"
        except ValueError:
            pass
    ln = tags.get("lanes")
    if ln:
        try:
            n = int(str(ln).split(";")[0])
            if 1 <= n <= 8:
                return round(n * LANE_W_M + 2 * GUTTER_W_M, 2), f"osm lanes={n} x {LANE_W_M} + 2 x {GUTTER_W_M} [invented]"
        except ValueError:
            pass
    hw = tags.get("highway", "")
    if hw == "service":
        return SERVICE_WIDTH_M, "service apron default [invented]"
    return CLASS_WIDTH_M.get(hw, 10.0), f"class default {hw} [invented]"


def _branches(way_nodes, nodes_xz, host, reach=HOST_REACH_M):
    """[(i_on_host, direction, [(x, z)...])] — every walk from an on-host node of the way that leaves the host"""
    out = []
    n = len(way_nodes)
    on = []
    for nid in way_nodes:
        x, z = nodes_xz[nid]
        d, i, t, _lat, _s = host.project(x, z)
        on.append(d <= host.half(i, t) + reach)
    for k in range(n):
        if not on[k]:
            continue
        for step in (1, -1):
            j = k + step
            if not (0 <= j < n) or on[j]:
                continue
            geo = [nodes_xz[way_nodes[k]]]
            q = j
            while 0 <= q < n and polyline_length(geo) < BRANCH_OUT_M + 20.0:
                geo.append(nodes_xz[way_nodes[q]])
                q += step
            out.append((k, step, geo))
    return out


def find_cut(host, geo, overlap=OVERLAP_M):
    """walk the branch from its on-host start outward: (u_cut, x, z, tx, tz, seg, t, lat) where the branch's
    distance from the host centreline crosses half - overlap (trim_connectors' cut); the start is pulled back along
    the first segment until it is inside. None when the branch never leaves."""
    pts = resample(geo, 0.05)
    x0, z0 = pts[0]
    tx0, tz0 = point_at(pts, 0.0)[2:]
    back = 0.0
    while back < 15.0:
        d, i, t, _lat, _s = host.project(x0 - tx0 * back, z0 - tz0 * back)
        if d < host.half(i, t) - overlap - 0.5:
            break
        back += 0.25
    u = -back
    total = polyline_length(pts)
    prev = None
    while u <= total:
        x, z, tx, tz = point_at(pts, u)
        d, i, t, lat, _s = host.project(x, z)
        g = d - (host.half(i, t) - overlap)
        if prev is not None and prev[0] < 0.0 <= g:
            f = prev[0] / (prev[0] - g)
            uc = prev[1] + (u - prev[1]) * f
            x, z, tx, tz = point_at(pts, uc)
            d, i, t, lat, _s = host.project(x, z)
            return uc, x, z, tx, tz, i, t, lat, pts
        prev = (g, u)
        u += 0.05
    return None


def mouths_ways(mouths_path, leg):
    """the way ids one leg of an expansion mouths file lists ({"mouths": {leg: [{"way": id, ...}]}}, the shape of
    tracks/san-diego-lake-murray/source/expansion/routes__mouths.json on the expansion branch)"""
    doc = json.loads(Path(mouths_path).read_text(encoding="utf-8"))
    rows = (doc.get("mouths") or {}).get(leg)
    if rows is None:
        raise SystemExit(f"[stubs] {mouths_path}: no leg {leg!r} (has {sorted((doc.get('mouths') or {}))})")
    return {int(r["way"]) for r in rows}


def declare(project, osm_path, host_name="MAINLINE", streets=None, only=None, merge=None, length_m=STUB_LENGTH_M,
            mouths_path=None, legs=None):
    """the declaration for one host or several: host_name may be a comma list; legs ({host: leg}) with mouths_path
    restricts each host to the ways that leg of the mouths file lists"""
    hosts = [h.strip() for h in str(host_name).split(",") if h.strip()]
    entries = []
    for h in hosts:
        wf = mouths_ways(mouths_path, legs[h]) if (mouths_path and legs and h in legs) else None
        entries += _host_entries(project, osm_path, h, streets, length_m, wf)
    # one entry per (host, way, side, host vertex)
    seen, uniq = {}, []
    for e in sorted(entries, key=lambda e: (hosts.index(e["host"]), e["station_m"], e["id"])):
        key = (e["host"], e["way"], e["side"], e["host_vertex"] // 3)
        if key in seen:
            continue
        seen[key] = True
        if any(u["id"] == e["id"] for u in uniq):
            e["id"] = f"{e['id']}_{e['host_vertex']}"
        uniq.append(e)
    if only:
        for e in uniq:
            if e["id"] not in only and e["treatment"] != "skip":
                e["treatment"], e["skip_reason"] = "skip", "not selected (--only)"
    if merge:
        old = {e["id"]: e for e in json.loads(Path(merge).read_text(encoding="utf-8")).get("stubs", [])}
        for e in uniq:
            o = old.get(e["id"])
            if o and o.get("hand"):
                for k in o["hand"]:
                    if k in o:
                        e[k] = o[k]
                e["hand"] = list(o["hand"])
    return {"version": 1,
            "_doc": "Phase 5 stub declaration (tools/stub_roads.py declare). Edit by hand: set treatment "
                    "stub|curb_cut|skip (+ skip_reason), width_m, length_m (>= %.2f), barrier krail|type3, and list "
                    "every hand-edited key in `hand` so a re-declare (--merge) keeps it." % MIN_LENGTH_M,
            "host": ",".join(hosts), "osm": str(Path(osm_path).name),
            **({"mouths": str(Path(mouths_path).name), "legs": legs} if mouths_path else {}),
            "defaults": {"length_m": length_m, "tail_m": TAIL_M, "barrier": "krail"},
            "stubs": uniq}


def _host_entries(project, osm_path, host_name, streets, length_m, ways_filter=None):
    proj = Path(project)
    data = proj / "data"
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    origin = local["origin"]
    conn_doc = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))
    conns = [c for c in conn_doc.get("connectors", []) if not c["name"].startswith(STUB_PREFIX)
             and c["name"] != host_name and not c["name"].startswith(host_name + "#")]
    if host_name == "MAINLINE":
        host = Line(local["points_xyz_m"], local["widths_m"])
    else:
        hc = next((c for c in conn_doc.get("connectors", []) if c["name"] == host_name), None)
        if hc is None:
            raise SystemExit(f"[stubs] host {host_name!r} is not a connector piece")
        host = Line(hc["points_xyz_m"], hc["widths_m"])
    osm = json.loads(Path(osm_path).read_text(encoding="utf-8"))
    nodes = osm["nodes"]
    ways = osm["ways"]
    nodes_xz = {}
    for nid, (lon, lat) in nodes.items():
        nodes_xz[int(nid)] = to_local(lon, lat, origin)
    # host ways: most of their nodes on the built host (both carriageways of a divided host included)
    host_way_names = {}
    hostish = set()
    for w in ways:
        ns = [n for n in w["nodes"] if n in nodes_xz]
        if len(ns) < 2:
            continue
        on = 0
        for n in ns:
            x, z = nodes_xz[n]
            d, i, t, _l, _s = host.project(x, z)
            on += d <= host.half(i, t) + HOST_REACH_M
        L = polyline_length([nodes_xz[n] for n in ns])
        if on >= 0.6 * len(ns) and L > 20.0:
            hostish.add(w["id"])
            for n in ns:
                host_way_names.setdefault(n, (w.get("tags") or {}).get("name"))
    conn_lines = [[(p[0], p[2]) for p in c["points_xyz_m"]] for c in conns]
    mp = data / "mouths.json"
    mouths = [mo for mo in (json.loads(mp.read_text(encoding="utf-8")).get("mouths", []) if mp.exists() else [])
              if not str(mo.get("connector", "")).startswith(STUB_PREFIX)]
    entries = []
    for w in ways:
        tags = w.get("tags") or {}
        hw = tags.get("highway")
        if w["id"] in hostish or hw not in PUBLIC + tuple(SKIP_CLASSES) + ("service",):
            continue
        if ways_filter is not None and int(w["id"]) not in ways_filter:
            continue
        ns = [n for n in w["nodes"] if n in nodes_xz]
        for k, step, geo in _branches(ns, nodes_xz, host):
            cut = find_cut(host, geo)
            if cut is None:
                continue
            uc, cx, cz, tx, tz, seg, t, lat, pts = cut
            htx, htz = host.tangent(seg)
            ang = math.degrees(math.acos(min(1.0, abs(tx * htx + tz * htz))))
            side = 1 if lat >= 0 else -1
            junction = ns[k]
            hname = host_way_names.get(junction)
            if hname is None:
                x, z = nodes_xz[junction]
                best = min(host_way_names, key=lambda n: (nodes_xz[n][0] - x) ** 2 + (nodes_xz[n][1] - z) ** 2,
                           default=None)
                hname = host_way_names.get(best)
            width, wsrc = width_of(tags)
            sid = f"{slug(tags.get('name') or hw)}_{w['id']}_{'L' if side > 0 else 'R'}"
            treatment, why = "stub", None
            if hw in SKIP_CLASSES:
                treatment, why = "skip", SKIP_CLASSES[hw]
            elif hw == "service":
                treatment = "curb_cut"
            elif ang < PARALLEL_DEG:
                treatment, why = "skip", f"leaves the host at {ang:.0f} deg — a carriageway / slip lane, not a side road"
            if treatment != "skip":
                _d, _i, _t, _l, s_cut = host.project(cx, cz)
                for mo in mouths:
                    if mo.get("host") != host_name or int(mo.get("side", 0)) != side:
                        continue
                    mx, mz = mo["cut_xyz"][0], mo["cut_xyz"][2]
                    _md, _mi, _mt, _ml, s_mo = host.project(mx, mz)
                    if abs(s_mo - s_cut) <= float(mo.get("connector_width_m", 10.0)) / 2.0 + width / 2.0 + 6.0:
                        treatment, why = "skip", f"already built: mouth of {mo.get('piece') or mo['connector']}"
                        break
            if treatment != "skip":
                for name_c, cl in zip([c["name"] for c in conns], conn_lines):
                    near = 0
                    for uu in (5.0, 10.0, 15.0, 20.0, 25.0):
                        px, pz, _a, _b = point_at(pts, uc + uu)
                        if any(math.hypot(px - qx, pz - qz) <= BUILT_TOL_M for qx, qz in cl):
                            near += 1
                    if near >= 3:
                        treatment, why = "skip", f"already built: connector {name_c}"
                        break
            if streets and hname not in streets and treatment != "skip":
                treatment, why = "skip", f"host street {hname!r} not in --streets"
            _d, _i, _t, _l, s_host = host.project(cx, cz)
            k_host = seg if t < 0.5 else min(len(host.p) - 1, seg + 1)
            lonlat = [list(map(lambda v: round(v, 7), to_lonlat(x, z, origin))) for x, z in geo]
            entries.append({
                "id": sid, "way": w["id"], "node": junction, "name": tags.get("name"), "highway": hw,
                "service": tags.get("service"), "host": host_name, "host_street": hname, "host_vertex": k_host,
                "station_m": round(s_host, 1), "side": side, "angle_deg": round(ang, 1),
                "heading_deg": round(math.degrees(math.atan2(tx, tz)) % 360.0, 1),
                "width_m": width, "width_source": wsrc, "lanes": tags.get("lanes"),
                "length_m": length_m, "barrier": "krail", "treatment": treatment,
                **({"skip_reason": why} if why else {}),
                "branch_lonlat": lonlat})
    return entries


# ------------------------------------------------------------------------------------------------ apply

def validate_declaration(decl):
    fails = []
    ids = set()
    for e in decl.get("stubs", []):
        sid = e.get("id")
        if not sid or not re.match(r"^[a-z0-9_]+$", str(sid), re.I):
            fails.append(f"bad id {sid!r}")
        if sid in ids:
            fails.append(f"duplicate id {sid}")
        ids.add(sid)
        tr = e.get("treatment")
        if tr not in TREATMENTS:
            fails.append(f"{sid}: treatment {tr!r} not in {TREATMENTS}")
        if tr == "skip" and not e.get("skip_reason"):
            fails.append(f"{sid}: skip without a skip_reason")
        if tr == "stub":
            if float(e.get("length_m", STUB_LENGTH_M)) < MIN_LENGTH_M:
                fails.append(f"{sid}: length_m {e.get('length_m')} < {MIN_LENGTH_M:.2f} (trim_connectors would drop it)")
            if e.get("barrier", "krail") not in BARRIERS:
                fails.append(f"{sid}: barrier {e.get('barrier')!r} not in {BARRIERS}")
            if e.get("barrier", "krail") == "type3":
                fails.append(f"{sid}: barrier type3 is a PREVIEW option (no textures, no shipped model yet) — "
                             f"tools/stub_stills_blend.py renders it; ship krail until Kevin picks it")
            if not (3.0 <= float(e.get("width_m", 0)) <= 40.0):
                fails.append(f"{sid}: width_m {e.get('width_m')} outside 3-40 m")
        if tr in ("stub", "curb_cut") and len(e.get("branch_lonlat") or []) < 2:
            fails.append(f"{sid}: no branch geometry")
    return fails


class Dem:
    """3DEP point samples with a json cache (data/stubs.3dep.json): {"lon,lat": elev}"""

    def __init__(self, path, sampler=None):
        self.path = Path(path)
        self.cache = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.sampler = sampler
        self.fetched = 0

    @staticmethod
    def key(lon, lat):
        return f"{lon:.7f},{lat:.7f}"

    def sample(self, lonlat):
        miss = [(lo, la) for lo, la in lonlat if self.key(lo, la) not in self.cache]
        if miss:
            if self.sampler is None:
                sys.path.insert(0, str(AIROSO))
                from scripts.elevation import usgs_3dep
                self.sampler = usgs_3dep.sample_points
            vals = self.sampler(miss)
            for (lo, la), v in zip(miss, vals):
                self.cache[self.key(lo, la)] = None if v is None else round(float(v), 3)
            self.fetched += len(miss)
        return [self.cache[self.key(lo, la)] for lo, la in lonlat]

    def save(self):
        if self.fetched:
            self.path.write_text(json.dumps(self.cache, sort_keys=True), encoding="utf-8")


def build_stub(e, local, conns, dem, origin):
    """(connector record, plan record) for one `stub` entry"""
    if e.get("host", "MAINLINE") == "MAINLINE":
        hpts, hw = local["points_xyz_m"], local["widths_m"]
    else:
        hc = next((c for c in conns if c["name"] == e["host"]), None)
        if hc is None:
            raise SystemExit(f"[stubs] {e['id']}: host {e['host']!r} not in connectors.local.json")
        hpts, hw = hc["points_xyz_m"], hc["widths_m"]
    host = Line(hpts, hw)
    geo = [to_local(lo, la, origin) for lo, la in e["branch_lonlat"]]
    cut = find_cut(host, geo)
    if cut is None:
        raise SystemExit(f"[stubs] {e['id']}: the OSM branch never leaves the host's pavement")
    uc, cx, cz, tx, tz, seg, t, lat, pts = cut
    side = 1 if lat >= 0 else -1
    if side != int(e["side"]):
        raise SystemExit(f"[stubs] {e['id']}: the branch leaves on side {side:+d}, declared {e['side']:+d}")
    htx, htz = host.tangent(seg)
    ang = math.degrees(math.acos(min(1.0, abs(tx * htx + tz * htz))))
    sin_a = max(0.2, math.sin(math.radians(ang)))
    L = float(e.get("length_m", STUB_LENGTH_M))
    u_mouth = OVERLAP_M / sin_a                       # cut -> the host edge line, along the stub
    u_bar = u_mouth + L
    u_end = u_bar + TAIL_M
    width = float(e["width_m"])
    host_y, hseg, ht = TRIM.host_height([tuple(p) for p in hpts], cx, cz)
    g0 = host.grade(hseg) * (htx * tx + htz * tz)
    # 3DEP along the branch, every metre from the mouth line to the end
    us = [u_mouth + k * 1.0 for k in range(int(math.floor((u_end - u_mouth) / 1.0)) + 1)]
    xz = [point_at(pts, uc + u)[:2] for u in us]
    ll = [to_lonlat(x, z, origin) for x, z in xz]
    ds = dem.sample(ll)
    okk = [(u, d) for u, d in zip(us, ds) if d is not None]
    if len(okk) < 5:
        raise SystemExit(f"[stubs] {e['id']}: 3DEP returned {len(okk)} samples on the stub")
    g_raw, rmse = fit_grade([u for u, _ in okk], [d for _, d in okk])
    g = max(-GRADE_CAP, min(GRADE_CAP, g_raw))
    T = ramp_length(g, g0)
    # the polyline: one point 1 m inside the cut (trim drops it), then every SPACING_M from the cut
    upts = [-1.0] + [SPACING_M * k for k in range(1, int(math.floor(u_end / SPACING_M)) + 1)]
    if u_end - upts[-1] > 0.05:
        upts.append(u_end)
    elif upts[-1] != u_end:
        upts[-1] = u_end
    P = []
    for u in upts:
        x, z, _a, _b = point_at(pts, uc + u)
        P.append([round(x, 3), round(draft_y(u, host_y, g0, g, T), 3), round(z, 3)])
    name = STUB_PREFIX + e["id"]
    stub_meta = {"id": e["id"], "host": e.get("host", "MAINLINE"), "length_m": L, "tail_m": TAIL_M,
                 "lanes_per_side": lanes_per_side(e.get("lanes")),
                 "barrier": e.get("barrier", "krail"),
                 "u_mouth_from_cut_m": round(u_mouth, 3), "u_barrier_from_cut_m": round(u_bar, 3)}
    conn = {"name": name, "kind": "connector", "points_xyz_m": P, "widths_m": [width] * len(P),
            "blend_m": 0.0, "stub": stub_meta}
    plan = {**stub_meta, "connector": name, "way": e.get("way"), "street": e.get("name"), "highway": e.get("highway"),
            "host": e.get("host", "MAINLINE"), "host_street": e.get("host_street"), "side": side,
            "width_m": width, "width_source": e.get("width_source"), "angle_deg": round(ang, 2),
            "cut_xz": [round(cx, 3), round(cz, 3)], "dir_xz": [round(tx, 5), round(tz, 5)],
            "host_y": round(host_y, 4), "host_seg": hseg, "host_t": round(ht, 4),
            "grade_3dep": round(g_raw, 5), "grade_used": round(g, 5), "grade_capped": g != g_raw,
            "grade_host_along": round(g0, 5), "vcurve_m": round(T, 2), "dem_rmse_m": round(rmse, 3),
            "dem_offset_m": round(host_y + local["origin"]["elev_m"] - okk[0][1], 3),
            "dem_samples": [[round(u, 2), d] for u, d in okk]}
    return conn, plan


def lanes_per_side(lanes) -> int:
    """the stub's lanes each way from its OSM `lanes` (both directions; a side street is two-way): half, at least 1
    — the assembler paints lanes_per_side - 1 dividers a side (scripts-v021 ribbon.connector_markings)"""
    try:
        n = int(float(str(lanes).split(";")[0]))
    except (TypeError, ValueError):
        return 1
    return max(1, n // 2)


def curb_cut_plan(e, local, origin):
    host = Line(local["points_xyz_m"], local["widths_m"])
    geo = [to_local(lo, la, origin) for lo, la in e["branch_lonlat"]]
    cut = find_cut(host, geo, overlap=0.0)
    if cut is None:
        raise SystemExit(f"[stubs] {e['id']}: the service branch never leaves the host's pavement")
    uc, cx, cz, tx, tz, seg, t, lat, _pts = cut
    _d, _i, _t, _l, s = host.project(cx, cz)
    htx, htz = host.tangent(seg)
    ang = math.degrees(math.acos(min(1.0, abs(tx * htx + tz * htz))))
    w = float(e.get("width_m", SERVICE_WIDTH_M))
    half_span = w / 2.0 / max(0.3, math.sin(math.radians(ang)))
    return {"id": e["id"], "host": "MAINLINE", "side": 1 if lat >= 0 else -1, "station_m": round(s, 2),
            "half_span_m": round(half_span, 2), "flare_m": CURB_CUT_FLARE_M, "lip_m": CURB_CUT_LIP_M,
            "width_m": w, "angle_deg": round(ang, 2), "cut_xz": [round(cx, 3), round(cz, 3)]}


def apply(project, decl_path=None, sampler=None) -> int:
    proj = Path(project)
    data = proj / "data"
    dp = Path(decl_path) if decl_path else data / "stubs.json"
    if not dp.exists():
        print(f"[stubs] no stub declaration ({dp}) — nothing to do (every output untouched)")
        return 0
    decl = json.loads(dp.read_text(encoding="utf-8"))
    fails = validate_declaration(decl)
    if fails:
        for f in fails:
            print(f"[stubs] DECLARATION FAIL {f}")
        return 1
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    origin = local["origin"]
    src = data / "connectors.local.json"
    pre = data / "connectors.local.json.pre-trim"
    docs = {p: json.loads(p.read_text(encoding="utf-8")) for p in (src, pre) if p.exists()}
    base = [c for c in docs[src]["connectors"] if not c["name"].startswith(STUB_PREFIX)]
    dem = Dem(data / "stubs.3dep.json", sampler)
    conns, plans, cuts = [], [], []
    for e in decl.get("stubs", []):
        if e["treatment"] == "stub":
            c, p = build_stub(e, local, base, dem, origin)
            conns.append(c)
            plans.append(p)
        elif e["treatment"] == "curb_cut":
            cuts.append(curb_cut_plan(e, local, origin))
    dem.save()
    for p, doc in docs.items():
        doc["connectors"] = [c for c in doc["connectors"] if not c["name"].startswith(STUB_PREFIX)] + conns
        p.write_text(json.dumps(doc), encoding="utf-8")
    plan = {"version": 1, "declaration": dp.name, "stubs": plans, "curb_cuts": cuts,
            "skipped": [{"id": e["id"], "why": e.get("skip_reason")} for e in decl.get("stubs", [])
                        if e["treatment"] == "skip"],
            "constants": {"stub_length_m": STUB_LENGTH_M, "tail_m": TAIL_M, "spacing_m": SPACING_M,
                          "ramp_dg_per_m_invented": RAMP_DG_PER_M, "ramp_min_m_invented": RAMP_MIN_M,
                          "grade_cap_invented": GRADE_CAP, "curb_cut_lip_m_invented": CURB_CUT_LIP_M,
                          "curb_cut_flare_m_invented": CURB_CUT_FLARE_M}}
    (data / "stubs.plan.json").write_text(json.dumps(plan, indent=1), encoding="utf-8")
    for p in plans:
        print(f"[stubs] {p['connector']}: {p['street']} ({p['highway']}) off {p['host_street']} side {p['side']:+d} at "
              f"{p['angle_deg']} deg, {p['width_m']} m wide, barrier {p['barrier']} {p['length_m']} m out; 3DEP grade "
              f"{100 * p['grade_3dep']:+.2f} % (rmse {p['dem_rmse_m']} m), host along {100 * p['grade_host_along']:+.2f} %, "
              f"vertical curve {p['vcurve_m']} m")
    print(f"[stubs] {len(plans)} stub(s) appended to connectors.local.json (+ .pre-trim), {len(cuts)} curb cut(s), "
          f"{len(plan['skipped'])} skipped; 3DEP {dem.fetched} new sample(s) -> stubs.plan.json")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("declare")
    d.add_argument("project")
    d.add_argument("--osm", required=True)
    d.add_argument("--out", required=True)
    d.add_argument("--host", default="MAINLINE")
    d.add_argument("--streets", default=None)
    d.add_argument("--only", default=None)
    d.add_argument("--merge", default=None)
    d.add_argument("--length", type=float, default=STUB_LENGTH_M)
    d.add_argument("--mouths", default=None, help="an expansion mouths file ({mouths: {leg: [{way, ...}]}})")
    d.add_argument("--legs", default=None, help="host=leg,... : each host keeps only its leg's ways")
    a = sub.add_parser("apply")
    a.add_argument("project")
    a.add_argument("--decl", default=None)
    args = ap.parse_args(argv)
    if args.cmd == "declare":
        streets = [s.strip() for s in args.streets.split(",")] if args.streets else None
        only = set(s.strip() for s in args.only.split(",")) if args.only else None
        legs = dict(kv.split("=", 1) for kv in args.legs.split(",")) if args.legs else None
        doc = declare(args.project, args.osm, args.host, streets, only, args.merge, args.length, args.mouths, legs)
        Path(args.out).write_text(json.dumps(doc, indent=1), encoding="utf-8")
        from collections import Counter
        c = Counter(e["treatment"] for e in doc["stubs"])
        print(f"[stubs] declared {len(doc['stubs'])} branch(es) on {args.host}: {dict(c)} -> {args.out}")
        for e in doc["stubs"]:
            print(f"  {e['treatment']:8s} {e['id']:44s} {str(e['host_street'])[:22]:22s} v{e['host_vertex']:<5d} "
                  f"s {e['station_m']:7.1f} side {e['side']:+d} {e['angle_deg']:5.1f} deg {e['width_m']:5.1f} m "
                  f"{e.get('skip_reason') or ''}")
        return 0
    return apply(args.project, args.decl)


if __name__ == "__main__":
    sys.exit(main())
