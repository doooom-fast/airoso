"""Loop front-end: prep a Blender-FIRST project's loop.blend for AC and save blender/<slug>.blend.

This is the San Diego (k10-san-diego) build philosophy, ported as an alternate front-end: the
project's ``loop.blend`` is the source of truth (Kevin shapes it in Blender), and this pass CONSUMES
it — renames the working meshes to AC surface conventions, gives them tiling UVs + PBR materials,
welds/holes-fills the grass, drops the AC_START/PIT/TIME/HOTLAP dummies (a single layout: the engine
draft's data/dummies.json, else computed from the real centreline; more than one layout: none — they
ride in the per-layout spawn kn5s), packs textures, and saves ``blender/<slug>.blend``. ``export_kn5_addon`` then binds
shaders + exports the real kn5 (tools/ship_track.sh runs this as its `prep` step; scripts/build_loop.sh
is retired, 2026-10-28).

THIS IS A DIFFERENT PROGRAM from scripts/ac/build_kn5.py (the OBJ-import pipeline). The two must
never be merged: this one edits an existing hand-authored scene; that one assembles a scene from
generated, audited OBJs. (docs: k10-colorado ENGINE-MIGRATION.md — "build_kn5.py is two programs".)

    blender --background --python scripts/ac/build_kn5_loop.py -- <project-dir>

The project dir is EXTERNAL to this repo (a consumer repo like k10-san-diego passes its own
project path); everything engine-side resolves against this file's location, never the project's.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# engine repo root — for `from scripts.ac import pbr` / `from scripts.geometry import dummies`
# regardless of where Blender was launched from or where the project dir lives.
_REPO = Path(__file__).resolve().parents[2]

# working mesh name (in loop.blend) -> AC-convention name. `1` prefix = physical surface keyed to
# surfaces.ini (ROAD/KERB/GRASS); 1WALL = physical collision barrier (guardrail).
AC_NAME = {
    "ROAD": "1ROAD_road",
    "KERB": "1KERB_kerb",
    # The street curb+sidewalk ships as the working mesh "CURB". Remap it to a 1KERB_ physical
    # surface so (a) it's collidable — the car can't fall through the road-edge/grass gap it
    # bridges — and (b) it gets the face-up flip below. Without this it stayed "CURB":
    # non-physical AND textureless=black.
    "CURB": "1KERB_sidewalk",
    "TERRAIN": "1GRASS",
    "GUARDRAIL": "1WALL_guard",
}
UV_TILE = 4.0  # metres per texture tile (top-down planar projection)

# AC/ksEditor hard per-mesh vertex cap (16-bit indices). Meshes over PIECE_CAP positions are tiled by
# balanced halving (balanced_tiles); anything STILL over VERT_CAP after split+weld is FATAL — AC silently
# drops over-cap meshes, and a dropped PHYSICAL mesh means the car falls through (the invisible-forest /
# fall-through bug class). PIECE_CAP (V3-PLAN P1, Lariat; [invented]) leaves 15,535 of headroom under the
# hard cap for the weld / smooth-shading changes after the split.
VERT_CAP = 65535
PIECE_CAP = 50000

# freeway groups whose winding must not matter: after the loop's local->Blender reflection their
# faces would point inward, so double-side them (append reversed faces) — a barrier/structure must
# render AND collide from both sides. Drivable surfaces are handled by the face-up flip pass.
DOUBLE_SIDE = ("1WALL", "HWYSTRUCT")

# --- terrain contact conform (the CO road-grounding pattern, loop-path edition) -------------------
# The hand-authored TERRAIN follows the DEM; the hand-shaped ROAD does not follow it back — on the
# western hills the deck ended up 1.8–6.7 m over the grass DIRECTLY beneath it (203+ red samples on
# the kn5 ground gate). Construction pins the world to the road: under the pavement footprint the
# terrain is PINNED to deck−GROUND_CLEAR (up or down), a FEATHER band blends back to natural ground,
# and the corridor is SUBDIVIDED first so coarse terrain triangles can hug the deck instead of
# chording (the adaptive-fine-grid move). Declared bridge spans (the real I-8 crossings) are spared:
# there the pin may only push DOWN — a bridge keeps its trench.
GROUND_CLEAR = 0.02        # m below the deck (the ground gate's ceiling is 0.05)
BAND_M = 3.0               # full-contact shelf past the pavement edge (CO grade_embankment's band)
FEATHER_M = 6.0            # smoothstep blend band beyond the shelf
CORRIDOR_EDGE_M = 4.5      # subdivide terrain edges near the road down to about this length
# STACKED LEGS (fleet/LAWS.md L4; V3-PLAN P1 precondition 3). The deck a ground point seats on is found by
# STATION MATCHING, not by a vertical window: every point carries the arc station of the road leg it belongs
# to (LegIndex.locate: the nearest centreline / connector segment in plan) and seats only on road triangles of
# that leg within STATION_WIN_M of its own station. On the Lariat's switchbacks the stacked legs stand 6.5-14.7 m
# apart vertically and 20.5 m apart in plan at the closest: a vertical window under 6 m leaves under 1 m of
# margin and misreads ground on a ~30 % side slope. With the lap's steepest 20 m at -11.5 %, a same-leg seat can
# be off by at most 0.115 x 40 = 4.6 m of grade, under the smallest stacked gap, and stacked legs differ by at
# least 6.5 / 0.115 = 57 m of station; a hairpin's own arc (pi x R <= 38 m for R <= 12 m) stays one stretch.
STATION_WIN_M = 40.0       # [invented] same-leg station window (cyclic on a closed lap)
BRIDGE_MATCH_M = 14.0      # centerline pt within this of an OSM bridge way = on the span
BRIDGE_PAD_M = 8.0         # widen each detected span a touch onto the abutments


def _mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def detect_bridge_spans(pts_xyz, origin_lonlat, bridge_ways, *, mirror_x=False,
                        match_m=BRIDGE_MATCH_M, pad_m=BRIDGE_PAD_M):
    """Station ranges [(a_m, b_m), ...] where the loop rides an OSM-declared bridge (its own deck —
    motorway/motorway_link ways are excluded so a freeway bridge crossing OVER the loop can't mark a
    phantom span on the road below). Pure function (no bpy) so it is unit-testable.

    pts_xyz: local (E, up, N) centerline; bridge_ways: [{'hw': ..., 'geom': [[lon, lat], ...]}, ...]."""
    lon0, lat0 = origin_lonlat
    m_lon, m_lat = _mpd(lat0)
    sx = -1.0 if mirror_x else 1.0
    segs = []
    for w in bridge_ways or []:
        if (w.get("hw") or "") in ("motorway", "motorway_link"):
            continue                      # the freeway's own bridges, not the loop's deck
        g = [(sx * (lon - lon0) * m_lon, (lat - lat0) * m_lat) for lon, lat in w.get("geom", [])]
        segs += [(g[i][0], g[i][1], g[i + 1][0], g[i + 1][1]) for i in range(len(g) - 1)]
    if not segs:
        return []

    def near_bridge(x, z):
        for ax, az, bx, bz in segs:
            dx, dz = bx - ax, bz - az
            L2 = dx * dx + dz * dz
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
            px, pz = ax + t * dx, az + t * dz
            if (x - px) ** 2 + (z - pz) ** 2 <= match_m * match_m:
                return True
        return False

    spans = []
    raw_heads = []                                   # each span's unclamped head (open_a - pad_m), for the seam wrap
    st = 0.0
    open_a = None
    prev = pts_xyz[0]
    for i, p in enumerate(pts_xyz):
        if i:
            st += math.hypot(p[0] - prev[0], p[2] - prev[2])
            prev = p
        if near_bridge(p[0], p[2]):
            if open_a is None:
                open_a = st
            open_b = st
        elif open_a is not None:
            spans.append((max(0.0, open_a - pad_m), open_b + pad_m))
            raw_heads.append(open_a - pad_m)
            open_a = None
    if open_a is not None:
        spans.append((max(0.0, open_a - pad_m), open_b + pad_m))
        raw_heads.append(open_a - pad_m)
    # L13 (V3-PLAN P2 step 5): on a CLOSED lap the closing vertex is vertex 0, so a span reaching it always
    # continues from vertex 0 (the same point is near the same bridge). The pads must wrap the same way: a pad past
    # either end of the lap continues on the other side of the seam, never past the lap's length or below 0
    # (before: the last span ran pad_m past the lap and the first span's pad was cut off at 0). Open roads unchanged.
    closed = (len(pts_xyz) > 2 and abs(pts_xyz[0][0] - pts_xyz[-1][0]) < 1e-6
              and abs(pts_xyz[0][2] - pts_xyz[-1][2]) < 1e-6)
    if closed and spans:
        lap = st
        pieces = list(spans)
        if near_bridge(pts_xyz[0][0], pts_xyz[0][2]) and pieces[0][0] <= 0.0:
            pieces.append((lap - pad_m, lap))             # vertex 0's pad, continued before the seam
        for h in raw_heads:
            if h < 0.0:                                   # a head pad cut off at 0: it continues before the seam
                pieces.append((max(0.0, lap + h), lap))
        wrapped = []
        for a, b in pieces:
            if b > lap:
                wrapped += [(a, lap), (0.0, b - lap)]
            else:
                wrapped.append((a, b))
        wrapped.sort()
        spans = []
        for a, b in wrapped:
            if spans and a <= spans[-1][1]:
                spans[-1] = (spans[-1][0], max(spans[-1][1], b))
            else:
                spans.append((a, b))
    return spans


FC_FRAME_KN5 = "kn5 (x, y, -z of the engine/OBJ frame) — the line the gates walk"


def declare_bridge_spans(proj: Path) -> list[tuple[float, float]]:
    """Declare the loop's bridge spans and the GATE LINE — write data/bridge.spans.auto.json +
    data/finished_centerline.json, the two files kn5_ground_check's declared-span exemption reads and
    the line drive_test walks (via kn5_to_gate_obj's data/gate_centerline.json), verify_kn5 judges the
    spawns against and write_ai_line draws from. finished_centerline is written in the KN5 frame (x, y,
    -z of the local/OBJ frame): the Blender-first path has no OBJ stage, so the shipped-binary frame IS
    the reference frame the gate samples in. Returns the spans (local stations, metres).

    THE LINE IS THE ENGINE'S WHEN THERE IS ONE (ledger 0060, Sand Creek 2026-10-29). build_mesh persists
    the line it actually swept the road along — corner-rounded, smoothed, its declared bridge decks
    LEVELLED crest to crest (evidence.level_bridge_decks, up to 7.9 m above the bare-earth profile over
    Sand Creek's creek) — as data/finished_centerline.json, frame "mesh …", with its auto-detected spans
    in data/bridge.spans.auto.json. This prep used to overwrite both with the RAW centerline.local.json
    line and an OSM-way span scan: drive_test's top_at(y_ref, window=2.5) then lost the deck wherever it
    rode > 2.5 m above the raw line (the middle of every span: 127 "severe steps" of up to 1.75 m where
    the deck left and re-entered the window, 12 "ground on top" + 12 "daylight gaps" at the one band
    where the creek bed was inside it), and on Milford the raw corners put the wheel paths beside the
    swept esses (15 lane steps on the chain against 8 on the draft). The engine's line is converted to
    the KN5 frame and its spans kept; this prep's own earlier write (frame "kn5 …", a `--from prep`
    re-run) is kept as it stands; without either (San Diego's assembler, whose prep IS the first stage)
    the raw line is written as before, now marked. An unmarked finished_centerline beside an engine
    draft is an earlier prep's raw line — the engine's is gone until the draft is rebuilt; said so."""
    local = json.loads((proj / "data" / "centerline.local.json").read_text())
    pts = [tuple(p) for p in local["points_xyz_m"]]
    widths = local.get("widths_m") or [7.0] * len(pts)
    cfg = json.loads((proj / "track.config.json").read_text())
    fcp = proj / "data" / "finished_centerline.json"
    autop = proj / "data" / "bridge.spans.auto.json"
    prev, prev_frame = None, ""
    if fcp.exists():
        try:
            prev = json.loads(fcp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prev = None
        if isinstance(prev, dict) and prev.get("points_xyz_m"):
            prev_frame = str(prev.get("frame") or "")
        else:
            prev = None
    if prev is not None and prev_frame.startswith(("mesh", "kn5")):
        if prev_frame.startswith("mesh"):
            # build_mesh's swept line, OBJ frame (x=E, y=up, z=N; x already mirrored when mirror_x) -> KN5 frame
            # (a road NETWORK's reference line, scripts.geometry.network_reference, is the same contract: the swept
            # decks of the declared mainline's edges, frame "mesh (network reference line) …" — said so, same move)
            _net = "network reference line" in prev_frame
            fc = {"frame": FC_FRAME_KN5,
                  "source": (f"{prev.get('source')} — the network draft's reference line "
                             f"(scripts.geometry.network_reference)" if _net else
                             "build_mesh finished_centerline (the swept line: corner-rounded, smoothed, bridge decks "
                             "levelled) — the engine draft's"),
                  "points_xyz_m": [[round(p[0], 3), round(p[1], 3), round(-p[2], 3)] for p in prev["points_xyz_m"]],
                  "widths_m": list(prev.get("widths_m") or widths)}
            fcp.write_text(json.dumps(fc), encoding="utf-8")
            how = ("the network's reference line (scripts.geometry.network_reference: the declared mainline's swept "
                   "edges) -> KN5 frame" if _net else
                   "the engine's swept line (build_mesh finished_centerline) -> KN5 frame")
        else:
            how = "kept this prep's earlier line (a re-run from the prep)"
        spans = []
        if autop.exists():
            try:
                spans = [(float(a), float(b)) for a, b in json.loads(autop.read_text(encoding="utf-8"))]
            except (OSError, ValueError, TypeError):
                spans = []
        else:
            autop.write_text("[]", encoding="utf-8")
        print(f"[build_kn5_loop] gate line: {how}; {len(spans)} bridge span(s) as the builder detected them: "
              f"{[(round(a), round(b)) for a, b in spans]}")
        return spans
    if prev is not None and (proj / "data" / "underlay.report.json").exists():
        print("[build_kn5_loop] WARNING gate line: data/finished_centerline.json beside an engine draft carries no frame "
              "— an earlier prep's raw line; the engine's swept line is gone until the draft is rebuilt (run the chain "
              "from the draft, not --from prep). The gates walk the raw centerline.local.json line this run.")
    bridges_p = proj / "data" / "bridges.cache.json"
    ways = json.loads(bridges_p.read_text()) if bridges_p.exists() else []
    o = local.get("origin") or {}
    spans = []
    if ways and "lon" in o:
        spans = detect_bridge_spans(pts, (o["lon"], o["lat"]), ways,
                                    mirror_x=bool(cfg.get("mirror_x", False)))
    autop.write_text(json.dumps([[round(a, 1), round(b, 1)] for a, b in spans]), encoding="utf-8")
    fcp.write_text(json.dumps({
        "frame": FC_FRAME_KN5,
        "source": "centerline.local.json (the raw line; no engine swept line in data/)",
        "points_xyz_m": [[round(x, 3), round(y, 3), round(-z, 3)] for x, y, z in pts],
        "widths_m": widths}), encoding="utf-8")
    print(f"[build_kn5_loop] declared {len(spans)} bridge span(s): "
          f"{[(round(a), round(b)) for a, b in spans]}")
    return spans


def balanced_tiles(centres, faces, cap=PIECE_CAP):
    """Tile a mesh by BALANCED HALVING: a face set over ``cap`` positions (distinct vertices) is cut at the
    median face centre along the longer horizontal side of its bounding box, and each half again, until every
    piece holds <= ``cap`` positions. Equal-width bands (the old split) put a whole switchback knot into one
    band and overflowed; halving at the median follows the faces wherever they bunch. Pure function (no bpy):
    ``centres`` = face centres (x, y, z), ``faces`` = vertex-index tuples; returns face-index lists, sorted,
    in a deterministic order (low half first)."""
    out = []

    def rec(idx):
        if len(idx) < 2 or len({v for i in idx for v in faces[i]}) <= cap:
            out.append(sorted(idx))
            return
        xs = [centres[i][0] for i in idx]
        ys = [centres[i][1] for i in idx]
        ax = 0 if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else 1
        s = sorted(idx, key=lambda i: (centres[i][ax], centres[i][1 - ax], i))
        h = len(s) // 2
        rec(s[:h])
        rec(s[h:])

    rec(list(range(len(faces))))
    return out


class LegIndex:
    """Station matching for stacked legs (fleet/LAWS.md L4; V3-PLAN P1 precondition 3). Every road polyline is a
    LEG with its own arc stations: the mainline (``data/centerline.local.json``, closed when the track is a loop)
    and each connector (``data/connectors.local.json``). ``locate(east, north)`` gives a plan point the leg and
    station of the nearest segment; two located points (or a point and a road triangle) are on the same stretch
    of road when ``same_leg`` holds: the same leg and stations within ``STATION_WIN_M`` (cyclic on a closed leg).
    Pure Python (no bpy). Input points are local (east, up, north); queries are plan (east, north), which is
    Blender's (x, y)."""

    def __init__(self, lines, cell=8.0, win=STATION_WIN_M):
        self.cell = float(cell)
        self.win = float(win)
        self.length = {}
        self.closed = {}
        self.grid = {}
        c = self.cell
        for lid, pts, closed in lines:
            pts = [(float(p[0]), float(p[2])) for p in pts]
            if closed and len(pts) > 2 and pts[0] != pts[-1]:
                pts.append(pts[0])
            s = 0.0
            for i in range(len(pts) - 1):
                (ax, ay), (bx, by) = pts[i], pts[i + 1]
                L = math.hypot(bx - ax, by - ay)
                if L <= 1e-9:
                    continue
                seg = (lid, ax, ay, bx, by, s, L)
                for gx in range(int(math.floor(min(ax, bx) / c)), int(math.floor(max(ax, bx) / c)) + 1):
                    for gy in range(int(math.floor(min(ay, by) / c)), int(math.floor(max(ay, by) / c)) + 1):
                        self.grid.setdefault((gx, gy), []).append(seg)
                s += L
            self.length[lid] = s
            self.closed[lid] = bool(closed)

    @classmethod
    def from_project(cls, proj: Path, closed=None):
        local = json.loads((proj / "data" / "centerline.local.json").read_text())
        if closed is None:
            cfg_p = proj / "track.config.json"
            cfg = json.loads(cfg_p.read_text()) if cfg_p.exists() else {}
            closed = bool(cfg.get("loop", True))
        lines = [("main", local["points_xyz_m"], closed)]
        cj = proj / "data" / "connectors.local.json"
        if cj.exists():
            for k, con in enumerate(json.loads(cj.read_text()).get("connectors", [])):
                if con.get("points_xyz_m"):
                    lines.append((f"c{k}", con["points_xyz_m"], False))
        return cls(lines)

    def locate(self, x, y, max_m=250.0):
        """(leg id, station m, plan distance m) of the nearest road segment to plan point (x, y), or None."""
        c = self.cell
        ix, iy = int(math.floor(x / c)), int(math.floor(y / c))
        best = None
        r = 0
        while r * c <= max_m:
            cells = [(ix + dx, iy + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1)
                     if max(abs(dx), abs(dy)) == r]
            for key in cells:
                for lid, ax, ay, bx, by, s0, L in self.grid.get(key, ()):
                    t = max(0.0, min(1.0, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / (L * L)))
                    d = math.hypot(x - (ax + t * (bx - ax)), y - (ay + t * (by - ay)))
                    if best is None or d < best[2] - 1e-12:
                        best = (lid, s0 + t * L, d)
            if best is not None and best[2] <= r * c:
                break                          # every unseen segment is at least r cells away
            r += 1
        return best

    def station_gap(self, a, b):
        ds = abs(a[1] - b[1])
        if self.closed.get(a[0]):
            ds = min(ds, self.length[a[0]] - ds)
        return ds

    def same_leg(self, a, b):
        return a is not None and b is not None and a[0] == b[0] and self.station_gap(a, b) <= self.win

    def chunk_key(self, leg):
        """the station chunk (STATION_WIN_M long) a located point falls in; the prep builds one BVH per chunk and
        its two neighbours, which holds every same-leg triangle of any point in the chunk"""
        k = int(leg[1] // self.win)
        if self.closed.get(leg[0]):
            k %= max(1, int(math.ceil(self.length[leg[0]] / self.win)))
        return (leg[0], k)

    def neighbour_keys(self, key):
        """Every chunk holding a station within ``win`` of some point of chunk ``key``. On an open leg that is
        k-1, k, k+1. On a closed lap the last chunk is usually SHORTER than ``win`` (lap length not a multiple of
        it), so near the seam the window reaches two chunks back across it: on a 1,010 m lap a point at station 5
        is same-leg with station 985 (chunk 24), which (25, 0, 1) would miss. So the closed case walks the
        station interval [start - win, end + win] round the lap and collects every chunk it touches."""
        lid, k = key
        if not self.closed.get(lid):
            return [(lid, k - 1), (lid, k), (lid, k + 1)]
        L, w = self.length[lid], self.win
        n = max(1, int(math.ceil(L / w)))
        if L <= 3 * w:
            return [(lid, j) for j in range(n)]
        lo, hi = k * w - w, min((k + 1) * w, L) + w
        keys = set()
        for period in (-1, 0, 1):                       # the interval crosses the seam at most once each way
            a, b = max(lo - period * L, 0.0), min(hi - period * L, L)
            if a < b:
                keys.update(range(int(a // w), min(int((b - 1e-9) // w), n - 1) + 1))
        return sorted((lid, j) for j in keys)


def pick_same_leg(hits, leg, legs):
    """The deck a point seats on: the first of ``hits`` (``(z, hit_leg)`` in ray order, highest first) whose leg is
    the point's own stretch of road (``legs.same_leg``); None when no hit is — never another leg's deck."""
    for z, hl in hits:
        if legs.same_leg(hl, leg):
            return z
    return None


def _project_dir(argv):
    if "--" not in argv:
        raise SystemExit("usage: blender --background --python build_kn5_loop.py -- <project-dir>")
    rest = argv[argv.index("--") + 1:]
    if not rest:
        raise SystemExit("missing <project-dir>")
    return Path(rest[0]).resolve()


def assert_under_cap(name: str, nverts: int) -> None:
    """Loop-path over-cap guard (the OBJ program's guard lives in build_kn5.py step 2b; this path
    needs its own). FATAL, not a warning: AC silently drops over-cap meshes from render AND
    collision, so a warned-and-shipped over-cap 1ROAD/1GRASS is a guaranteed fall-through."""
    if nverts > VERT_CAP:
        raise SystemExit(f"[build_kn5_loop] FATAL: '{name}' has {nverts} positions (> {VERT_CAP}) "
                         f"even after the split pass — AC silently drops over-cap meshes. "
                         f"Raise the split factor or slim the source mesh. Refusing to export.")


def _split_large(ob, cap=PIECE_CAP):
    """Split a mesh over ``cap`` positions into UNIQUELY-named spatial tiles (base_0, base_1, ...). The
    exporter otherwise auto-splits into DUPLICATE-named meshes, and AC drops dup-named PHYSICAL meshes
    from collision -> the car falls through (a 46 km freeway terrain is ~268k verts). Tiles come from
    balanced_tiles (halving at the median face centre until every piece is <= cap positions; equal-width
    bands overflowed where switchbacks bunch); pbr/surfaces still key off the shared name prefix
    (1GRASS_0 -> GRASS)."""
    import bpy

    me = ob.data
    if len(me.vertices) <= cap:
        return
    co = [(v.co.x, v.co.y, v.co.z) for v in me.vertices]
    polys = list(me.polygons)
    tiles = balanced_tiles([tuple(p.center) for p in polys], [tuple(p.vertices) for p in polys], cap)
    bands = [[polys[i] for i in t] for t in tiles]
    base = ob.name
    mat = me.materials[0] if me.materials else None
    # carry authored per-vertex UVs across the split (palm cards etc. are single UV per vertex) —
    # without this the tiles have NO UVs and an alpha-cutout texture samples (0,0) and vanishes.
    vert_uv = None
    if me.uv_layers.active:
        uvl = me.uv_layers.active
        vert_uv = [(0.0, 0.0)] * len(me.vertices)
        for loop in me.loops:
            vert_uv[loop.vertex_index] = tuple(uvl.data[loop.index].uv)
    for k, polys in enumerate(bands):
        if not polys:
            continue
        used, nv, nf, orig = {}, [], [], []
        for poly in polys:
            idx = []
            for vi in poly.vertices:
                if vi not in used:
                    used[vi] = len(nv); nv.append(co[vi]); orig.append(vi)
                idx.append(used[vi])
            nf.append(idx)
        nm = bpy.data.meshes.new(f"{base}_{k}")
        nm.from_pydata(nv, [], nf); nm.update()
        if vert_uv is not None:
            nuv = nm.uv_layers.new(name="UVMap")
            for loop in nm.loops:
                nuv.data[loop.index].uv = vert_uv[orig[loop.vertex_index]]
        if mat:
            nm.materials.append(mat)
        bpy.context.scene.collection.objects.link(bpy.data.objects.new(f"{base}_{k}", nm))
    print(f"[build_kn5_loop] split {base} ({len(me.vertices)} verts) -> {len(tiles)} balanced tiles of <= {cap} positions")
    bpy.data.objects.remove(ob, do_unlink=True)


def planar_uv(me):
    """Top-down planar UVs (u=x/tile, v=y/tile) — tiles asphalt/grass/kerb consistently at world
    scale."""
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (co.x / UV_TILE, co.y / UV_TILE)


def _add_obj_meshes(obj_path):
    """Import a merged OBJ (e.g. a freeway network already translated to the loop frame) using the
    SAME local->Blender remap as the loop authoring — (x,y,z)->(x,z,y) with reversed winding — so
    it lands in the loop's frame and the existing rename/flip/material pass handles it. Keeps AC
    group names + authored UVs."""
    import bpy

    verts = []; uvs = []; groups = []; cur = None
    for ln in obj_path.read_text().splitlines():
        s = ln.split()
        if not s:
            continue
        if s[0] == "v":
            verts.append((float(s[1]), float(s[2]), float(s[3])))
        elif s[0] == "vt":
            uvs.append((float(s[1]), float(s[2])))
        elif s[0] == "o":
            cur = (ln[2:].strip(), []); groups.append(cur)
        elif s[0] == "f" and cur is not None:
            face = []
            for tok in s[1:]:
                p = tok.split("/")
                face.append((int(p[0]) - 1, int(p[1]) - 1 if len(p) > 1 and p[1] else None))
            cur[1].append(face)
    n = 0
    for name, faces in groups:
        if not faces:
            continue
        has_uv = all(t is not None for fc in faces for _, t in fc)
        idx = {}; bverts = []; buvs = []; bfaces = []
        for fc in faces:
            bf = []
            for vi, ti in fc:
                if vi not in idx:
                    idx[vi] = len(bverts)
                    x, y, z = verts[vi]; bverts.append((x, z, y))     # local (E,up,N) -> Blender (E,N,up)
                    buvs.append(uvs[ti] if (has_uv and ti is not None) else (0.0, 0.0))
                bf.append(idx[vi])
            bfaces.append(tuple(reversed(bf)))                        # reverse winding (cancels the reflection)
        if name.upper().startswith(DOUBLE_SIDE):
            bfaces += [tuple(reversed(f)) for f in bfaces]            # render + collide from both sides
        me = bpy.data.meshes.new(name); me.from_pydata(bverts, [], bfaces); me.validate(); me.update()
        if has_uv:
            uvl = me.uv_layers.new(name="UVMap")
            for loop in me.loops:
                uvl.data[loop.index].uv = buvs[loop.vertex_index]
        bpy.context.scene.collection.objects.link(bpy.data.objects.new(name, me))
        n += 1
    print(f"[build_kn5_loop] merged {n} groups ({len(verts)} verts) from {obj_path.name}")
    return n


def _conform_and_reseat(proj: Path, spans):
    """Terrain contact conform for the Blender-first loop + prop re-seat, run INSIDE the open scene
    (after the AC renames, before the split pass). Three moves, all engine-owned so every future
    rebuild stays fixed (no hand surgery baked into loop.blend):

      1. SUBDIVIDE the terrain corridor: coarse DEM triangles cannot hug a hand-shaped deck — edges
         near the road are split to ~CORRIDOR_EDGE_M so the pin has vertices to work with
         (the adaptive-fine-grid move).
      2. PIN under the footprint: every 1GRASS vert under 1ROAD pavement is SET to deck−GROUND_CLEAR
         (up or down — contact, not a clamp), with a smoothstep FEATHER band blending back to natural
         ground past the edge. Under a DECLARED bridge span the pin may only push DOWN: the I-8
         trench stays a trench and the deck keeps riding it.
      3. RE-SEAT props on the moved ground: trees are seated absolutely (their floats predate this
         pass); palms/scrub/buildings/lights ride the terrain DELTA so today's good seats stay good.
    """
    import bpy
    from mathutils import kdtree
    from mathutils.bvhtree import BVHTree

    def _world_tris(name_pred):
        tris = []
        for ob in bpy.data.objects:
            if ob.type != "MESH" or not name_pred(ob.name.upper()):
                continue
            mw = ob.matrix_world
            me = ob.data
            vs = [mw @ v.co for v in me.vertices]
            for p in me.polygons:
                idx = list(p.vertices)
                for k in range(1, len(idx) - 1):
                    tris.append(((vs[idx[0]].x, vs[idx[0]].y, vs[idx[0]].z),
                                 (vs[idx[k]].x, vs[idx[k]].y, vs[idx[k]].z),
                                 (vs[idx[k + 1]].x, vs[idx[k + 1]].y, vs[idx[k + 1]].z)))
        return tris

    def _bvh(tris):
        return BVHTree.FromPolygons([v for t in tris for v in t],
                                    [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tris))]) if tris else None

    def _surf_z(bvh, x, y, zref=None, win=None):
        """Highest surface z at (x, y) via a downward ray from far above (Blender z = up); with zref and win,
        None when that surface is more than win off zref (the props' terrain-delta ride only — the road seat
        is station-matched, never windowed)."""
        if bvh is None:
            return None
        hit = bvh.ray_cast((x, y, 4000.0), (0.0, 0.0, -1.0))
        if hit[0] is None:
            return None
        z = hit[0].z
        if zref is not None and win is not None and abs(z - zref) > win:
            return None
        return z

    # 0. BURY-CULL: drivable faces (road/kerb) sandwiched >=0.3 m UNDER other pavement are junction
    #    apron slop that slid beneath the main deck when the junctions were shaped — dead geometry
    #    no wheel can reach. Left in, they poison every "lowest drivable sheet" lens: the poke gate
    #    reads contact-pinned grass as floating grass ABOVE the buried sliver, and clamping the
    #    grass down to the sliver instead re-opens metre-deep holes under the driven road. Cull the
    #    fully-buried faces (all verts covered) before anything measures against them.
    import bmesh
    _pre_bvh = _bvh(_world_tris(lambda n: n.startswith(("1ROAD", "1KERB")) and not n.endswith("_FW")))
    n_cull = 0
    if _pre_bvh is not None:
        for ob in [o for o in bpy.data.objects if o.type == "MESH"
                   and o.name.upper().startswith(("1ROAD", "1KERB"))
                   and not o.name.upper().endswith("_FW")]:
            me = ob.data
            bm = bmesh.new(); bm.from_mesh(me)
            drop = []
            for f in bm.faces:
                buried = True
                for v in f.verts:
                    hit = _pre_bvh.ray_cast((v.co.x, v.co.y, v.co.z + 0.3), (0.0, 0.0, 1.0), 20.0)
                    if hit[0] is None:
                        buried = False
                        break
                if buried:
                    drop.append(f)
            if drop:
                n_cull += len(drop)
                bmesh.ops.delete(bm, geom=drop, context="FACES")
                bm.to_mesh(me); me.update()
            bm.free()
    if n_cull:
        print(f"[build_kn5_loop] bury-cull: {n_cull} drivable faces removed from under other pavement")

    road_tris = _world_tris(lambda n: n.startswith("1ROAD"))
    road_bvh = _bvh(road_tris)
    if road_bvh is None:
        print("[build_kn5_loop] conform skipped: no 1ROAD mesh")
        return
    # drivable = road + kerb/sidewalk: the anti-poke pass below must use the same surface set the
    # verify poke lens measures against (grass over a LOW sidewalk apron is a poke too).
    driv_bvh = _bvh(_world_tris(lambda n: n.startswith(("1ROAD", "1KERB"))))

    # HORIZONTAL road-vert KD-tree for the feather + subdivision predicate. Distance must be 2D: on
    # a bench cut the ground beside the road is legitimately metres LOW, so a 3D nearest-distance
    # reads 6+ m and never feathers exactly the band the contact pin exists for (the CO lesson —
    # "real ground under the outer half of a bench-cut road is legitimately metres low").
    _rverts = sorted({(round(v[0], 4), round(v[1], 4), round(v[2], 4)) for t in road_tris for v in t})
    road_kd = kdtree.KDTree(len(_rverts))
    for _i, (_x, _y, _z) in enumerate(_rverts):
        road_kd.insert((_x, _y, 0.0), _i)
    road_kd.balance()

    def _near2d(x, y):
        co, idx, d = road_kd.find((x, y, 0.0))
        return (d, _rverts[idx][2]) if co is not None else (None, None)

    # STATION MATCHING (L4; STATION_WIN_M above): every road triangle carries the leg + station of its centroid,
    # every ground vertex the leg + station of its own plan position, and a vertex seats only on triangles of its
    # own stretch. One BVH per station chunk and its two neighbours (built on first use) holds every candidate.
    legs = LegIndex.from_project(proj)
    tri_leg = [legs.locate((a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0) for a, b, c in road_tris]
    _chunks: dict = {}
    for _i, _lg in enumerate(tri_leg):
        if _lg is not None:
            _chunks.setdefault(legs.chunk_key(_lg), []).append(_i)
    _leg_bvhs: dict = {}

    def _leg_bvh(vleg):
        key = legs.chunk_key(vleg)
        if key not in _leg_bvhs:
            idx = [i for kk in legs.neighbour_keys(key) for i in _chunks.get(kk, ())]
            _leg_bvhs[key] = (_bvh([road_tris[i] for i in idx]), idx)
        return _leg_bvhs[key]

    def _deck_same_leg(x, y, vleg, max_hits=6):
        """the deck of the vertex's OWN leg straight above / below it (multi-hit ray walk, highest first), or None"""
        bvh, idx = _leg_bvh(vleg)
        if bvh is None:
            return None
        hits, z0 = [], 4000.0
        for _ in range(max_hits):
            h = bvh.ray_cast((x, y, z0), (0.0, 0.0, -1.0))
            if h[0] is None:
                break
            hits.append((h[0].z, tri_leg[idx[h[2]]]))
            z0 = h[0].z - 0.01
        return pick_same_leg(hits, vleg, legs)

    def _near_same_leg(x, y, z, vleg):
        """the closest footprint point of the vertex's OWN leg, or None"""
        bvh, idx = _leg_bvh(vleg)
        if bvh is None:
            return None
        co, _n, i, _d = bvh.find_nearest((x, y, z))
        if co is None or not legs.same_leg(tri_leg[idx[i]], vleg):
            return None
        return co

    def _lowest_surf(bvh, x, y, zref, win=20.0):
        """LOWEST drivable surface at (x, y) within ±win of zref — multi-hit downward ray walk
        (the verify poke lens takes the lowest sheet; on a crowned/sloped section the highest one
        is the wrong reference)."""
        z0 = zref + win
        best = None
        for _ in range(6):
            hit = bvh.ray_cast((x, y, z0), (0.0, 0.0, -1.0), z0 - (zref - win))
            if hit[0] is None:
                break
            best = hit[0].z
            z0 = hit[0].z - 0.02
        return best

    # span mask: centerline stations inside a declared span -> XY discs (deck may only push DOWN)
    span_pts = []
    try:
        local = json.loads((proj / "data" / "centerline.local.json").read_text())
        pts = local["points_xyz_m"]
        wid = local.get("widths_m") or [7.0] * len(pts)
        st = 0.0
        for i, p in enumerate(pts):
            if i:
                st += math.hypot(p[0] - pts[i - 1][0], p[2] - pts[i - 1][2])
            if any(a <= st <= b for a, b in spans):
                span_pts.append((p[0], p[2], wid[i] / 2.0 + 12.0))   # Blender XY = (E, N)
    except Exception as e:  # noqa: BLE001
        print(f"[build_kn5_loop] span mask skipped: {e}")

    def on_span(x, y):
        return any((x - sx) ** 2 + (y - sy) ** 2 <= r * r for sx, sy, r in span_pts)

    terrain = [ob for ob in bpy.data.objects
               if ob.type == "MESH" and ob.name.upper().startswith("1GRASS")]
    old_grass_bvh = _bvh(_world_tris(lambda n: n.startswith("1GRASS")))   # pre-pin ground, for deltas

    import bmesh
    n_pin = n_feather = n_sub = 0
    for ob in terrain:
        me = ob.data
        bm = bmesh.new(); bm.from_mesh(me)
        # 1. corridor subdivision (repeat: each round halves qualifying edges)
        for _round in range(4):
            todo = []
            for e in bm.edges:
                if e.calc_length() <= CORRIDOR_EDGE_M:
                    continue
                mx = (e.verts[0].co + e.verts[1].co) / 2
                d2d, _rz = _near2d(mx.x, mx.y)
                if d2d is not None and d2d <= FEATHER_M + 10.0:
                    todo.append(e)
            if not todo:
                break
            bmesh.ops.subdivide_edges(bm, edges=todo, cuts=1)
            n_sub += len(todo)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        # 2. pin + feather (all distances HORIZONTAL — bench-cut ground is legitimately metres low)
        for v in bm.verts:
            x, y, z = v.co.x, v.co.y, v.co.z
            d2d, _rz = _near2d(x, y)
            if d2d is None or d2d > FEATHER_M + 10.0:
                continue
            vleg = legs.locate(x, y)                   # the vertex's own leg + station (L4: station matching)
            if vleg is None:
                continue
            deck = _deck_same_leg(x, y, vleg)
            if deck is not None:                       # under its own leg's pavement footprint
                tgt = deck - GROUND_CLEAR
                if on_span(x, y):
                    if z > tgt:
                        v.co.z = tgt; n_pin += 1       # bridge span: contact may only push DOWN
                else:
                    v.co.z = tgt; n_pin += 1
            else:                                      # contact band + feather past the edge
                # target = deck at the CLOSEST FOOTPRINT POINT OF ITS OWN LEG (BVH), not the nearest road
                # VERT's height — on a 7% grade the vert-snap target was ±0.3 off between stations and
                # printed that error into the contact band (the 0.05–0.35 residual tail) — and never the
                # stacked leg above or below (L4), however close it is in 3D.
                near3 = _near_same_leg(x, y, z, vleg)
                if near3 is None:
                    continue
                d_own = math.hypot(near3.x - x, near3.y - y)
                # full-contact BAND (CO's "gentle shelf"): every triangle covering pavement has all
                # verts within ~2.6 m of the edge, so holding the first 3 m at contact height makes
                # the surface under the deck edge gate-proof; then smoothstep back to natural.
                if d_own <= BAND_M:
                    w = 1.0
                elif d_own < BAND_M + FEATHER_M:
                    w = 1.0 - (d_own - BAND_M) / FEATHER_M
                    w = w * w * (3 - 2 * w)
                else:
                    continue
                tgt = near3.z - GROUND_CLEAR
                nz = tgt * w + z * (1.0 - w)
                if on_span(x, y) and nz > z:
                    continue
                v.co.z = nz; n_feather += 1
        # 2c. ANTI-POKE vs the LOWEST drivable sheet (road + kerb): the pin/feather reference the
        # nearest/highest deck — on crowned or sloping sections, and over the sidewalk's outer
        # apron, that left grass 0.15–1.2 m over the LOWER surface the verify lens measures
        # against (217 pokes). One-sided: only pushes DOWN, so spans/trenches are untouched.
        # (Blanket clamp is safe now that the bury-cull removed the sandwiched apron slivers.)
        n_anti = 0
        for v in bm.verts:
            low = _lowest_surf(driv_bvh, v.co.x, v.co.y, v.co.z)
            if low is not None and v.co.z > low - GROUND_CLEAR:
                v.co.z = low - GROUND_CLEAR; n_anti += 1
        if n_anti:
            print(f"[build_kn5_loop] anti-poke: {n_anti} verts clamped under the lowest drivable sheet")
        bm.to_mesh(me); bm.free(); me.update()
    print(f"[build_kn5_loop] terrain conform: {n_sub} corridor edges split, "
          f"{n_pin} verts pinned to deck-{GROUND_CLEAR}, {n_feather} feathered")

    # 3. prop re-seat on the moved ground
    ground_bvh = _bvh(_world_tris(lambda n: n.startswith(("1GRASS", "1ROAD", "1KERB"))))

    def _islands(ob):
        """Connected vert islands of a mesh object (index lists), via union-find over edges."""
        me = ob.data
        parent = list(range(len(me.vertices)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]; a = parent[a]
            return a
        for e in me.edges:
            a, b = find(e.vertices[0]), find(e.vertices[1])
            if a != b:
                parent[a] = b
        groups: dict[int, list[int]] = {}
        for i in range(len(me.vertices)):
            groups.setdefault(find(i), []).append(i)
        return list(groups.values())

    def _shift(ob, isl, dz):
        me = ob.data
        for i in isl:
            me.vertices[i].co.z += dz

    trunk_dz = []                                    # (x, y, dz) for canopy matching
    n_trees = n_rel = 0
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.name.upper().startswith("TREETRUNK"):
            continue
        me = ob.data
        for isl in _islands(ob):
            fi = min(isl, key=lambda i: me.vertices[i].co.z)
            f = ob.matrix_world @ me.vertices[fi].co
            g = _surf_z(ground_bvh, f.x, f.y, zref=None)
            if g is None:
                continue
            dz = g - f.z
            cx = sum(me.vertices[i].co.x for i in isl) / len(isl)
            cy = sum(me.vertices[i].co.y for i in isl) / len(isl)
            if abs(dz) > 0.03:
                _shift(ob, isl, dz); n_trees += 1
            trunk_dz.append((cx, cy, dz if abs(dz) > 0.03 else 0.0))
        me.update()
    for ob in bpy.data.objects:                      # canopies follow their trunk
        if ob.type != "MESH" or not ob.name.upper().startswith("TREECANOPY"):
            continue
        me = ob.data
        for isl in _islands(ob):
            cx = sum(me.vertices[i].co.x for i in isl) / len(isl)
            cy = sum(me.vertices[i].co.y for i in isl) / len(isl)
            best = None
            for tx, ty, dz in trunk_dz:
                d2 = (cx - tx) ** 2 + (cy - ty) ** 2
                if best is None or d2 < best[0]:
                    best = (d2, dz)
            if best is not None and best[0] < 16.0 and abs(best[1]) > 0.0:
                _shift(ob, isl, best[1])
        me.update()
    # palms / scrub / buildings / lights ride the terrain delta (their seats were already green)
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.name.upper().startswith(
                ("PALMTRUNK", "PALMFROND", "SCRUB", "BUILDING", "HOUSE", "LIGHTS")):
            continue
        me = ob.data
        for isl in _islands(ob):
            fi = min(isl, key=lambda i: me.vertices[i].co.z)
            f = ob.matrix_world @ me.vertices[fi].co
            zo = _surf_z(old_grass_bvh, f.x, f.y, zref=f.z, win=40.0)
            zn = _surf_z(ground_bvh, f.x, f.y, zref=f.z, win=40.0)
            if zo is None or zn is None:
                continue
            dz = zn - zo
            if abs(dz) > 0.02:
                _shift(ob, isl, dz); n_rel += 1
        me.update()
    print(f"[build_kn5_loop] re-seat: {n_trees} trees seated on the conformed ground, "
          f"{n_rel} props rode the terrain delta")


def _corridor_hash(proj):
    """0020's corridor discipline needs 'is this point inside ANY carriageway, and how high is the
    deck there' answered ~200k times. Spatial hash over every road polyline (mainline + the
    connectors from connectors.local.json), sampled ~2 m, cell 8 m. Engine frame is x=E, y=up,
    z=N; the .blend is (x, z, y) — so hash keys are (east, north) and deck height is Blender z.

    FRAME (V3-PLAN P1 precondition 1, 2026-10-11): data/finished_centerline.json is the KN5 frame
    (x, y, -north; declare_bridge_spans writes it that way for kn5_ground_check), so its points are
    un-negated here before hashing. Until then the mainline was hashed north-south mirrored while the
    queries (and the connectors, local frame) were not: the 0020 cull ran at the mirror image of the
    road and the real mainline had no corridor (tests/ac/test_build_kn5_loop_prep.py)."""
    cell = 8.0
    grid = {}
    def add_line(pts, widths):
        import math as _m
        prev = None
        for i, p in enumerate(pts):
            if prev is not None:
                d = _m.dist(prev, p)
                steps = max(1, int(d / 2.0))
                for s in range(steps):
                    t = (s + 1) / steps
                    q = [prev[k] + (p[k] - prev[k]) * t for k in range(3)]
                    w = widths[i - 1] + (widths[i] - widths[i - 1]) * t
                    key = (int(q[0] // cell), int(q[2] // cell))
                    grid.setdefault(key, []).append((q[0], q[2], q[1], w / 2.0))
            prev = p
    fc = json.loads((proj / "data" / "finished_centerline.json").read_text())
    add_line([(p[0], p[1], -p[2]) for p in fc["points_xyz_m"]], fc["widths_m"])   # KN5 frame -> local (E, up, N)
    cj = proj / "data" / "connectors.local.json"
    if cj.exists():
        for c in json.loads(cj.read_text()).get("connectors", []):
            if c.get("points_xyz_m"):
                add_line(c["points_xyz_m"], c["widths_m"])

    def query(east, north, height, vwin=3.5):
        """(signed clearance to nearest carriageway edge, deck z there). Negative = inside the
        road. Only samples within ``vwin`` vertically count — a deck BELOW a bridge you are on is
        not your layer (L4). Sidewalk checks use the tight default; canopy clearance checks pass
        a taller window (the offending crown hangs ~5 m over the deck)."""
        ix, iy = int(east // cell), int(north // cell)
        best = (1e9, 0.0)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for (sx, sy, sz, half) in grid.get((ix + dx, iy + dy), ()):
                    if abs(height - sz) > vwin:
                        continue
                    d = ((east - sx) ** 2 + (north - sy) ** 2) ** 0.5 - half
                    if d < best[0]:
                        best = (d, sz)
        return best
    return query


def main():
    import bpy

    proj = _project_dir(sys.argv)
    if str(_REPO) not in sys.path:
        sys.path.insert(0, str(_REPO))
    cfg = json.loads((proj / "track.config.json").read_text())
    slug = cfg["slug"]
    (proj / "blender").mkdir(exist_ok=True)
    (proj / "build").mkdir(exist_ok=True)

    # 1. open the working scene
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))

    # 1b. merge pre-built network OBJs (translated to the loop frame, e.g. by a merge_freeway step)
    #     into ONE kn5. Skipped when the project has none.
    for mobj in sorted(list((proj / "data").glob("track_*.obj")) + list((proj / "data").glob("env_*.obj"))):
        _add_obj_meshes(mobj)

    # 2. drop non-exported helpers (markers/cameras), rename meshes to AC convention
    for ob in list(bpy.data.objects):
        if ob.type != "MESH":
            bpy.data.objects.remove(ob, do_unlink=True); continue
        ob.name = AC_NAME.get(ob.name, ob.name)

    # 2b. terrain contact conform: declare the real bridge spans, pin the terrain to the deck under
    #     the footprint (subdividing the corridor first), spare the declared spans, and re-seat the
    #     props on the moved ground. Engine-owned so every future rebuild stays fixed.
    spans = declare_bridge_spans(proj)
    # An ENGINE DRAFT's ground is already conformed to its road (L3: build_mesh grades the embankment and drapes
    # the shoulder; scripts/blender/underlay.py drops it in as GEN_terrain and records data/underlay.report.json).
    # This conform was written for the SD assembler's independent terrain grid; on an engine draft its FEATHER
    # pulls the fill slope up toward deck height for BAND_M + FEATHER_M and leaves a cliff at the end of it —
    # Milford 2026-10-29: 2.45 M verts moved, 75 excursion drops > 20 cm at 10-12.5 m lateral where the V1 build
    # had 1; High Plains 103 (ledger 0060). So: auto = skip when the underlay report exists; track.config.json
    # prep.terrain_conform true / false overrides (an authored deck on an engine draft is the case for true).
    _tc = (cfg.get("prep") or {}).get("terrain_conform", "auto")
    if _tc == "auto":
        _tc = not (proj / "data" / "underlay.report.json").exists()
    if _tc:
        _conform_and_reseat(proj, spans)
    else:
        print("[build_kn5_loop] terrain conform skipped: the ground is the engine draft's, conformed to the road by "
              "build_mesh (data/underlay.report.json; track.config.json prep.terrain_conform forces it)")

    # split any mesh over the AC per-mesh vertex cap into uniquely-named tiles (big tracks: freeway terrain)
    for ob in list(o for o in bpy.data.objects if o.type == "MESH"):
        _split_large(ob)

    import bmesh
    corr = _corridor_hash(proj)
    for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
        me = ob.data
        # props / billboards carry authored UVs — don't flatten (freeway BUSHES/CHAINLINK too)
        # ...and the race furniture (ledger 0047): the strips carry u = arc / 4.04 m along the
        # vertical faces and the kerbs v = arc / 1 m — a top-down projection would smear them
        if not ob.name.upper().startswith(("PALM", "TREE", "SCRUB", "BUSHES", "CHAINLINK", "ROADTEXT",
                                           "1WALL_RACE", "1KERB_RACE", "BRIDGESTRUCT", "BUILDING_FABRIC", "1WALL_FABRIC", "PROPCONE",
                                           "BUILDING_TILTUP", "BUILDING_METAL", "BUILDING_STUCCO", "BUILDING_SIDING", "ROOFTOP", "1WALL_TILTUP", "1WALL_TECPRO", "1WALL_KRAILBW",
                                           "GUARDRAIL", "PADAPRON", "BUILDING_DRYSTONE", "FARBLOCK")):
            planar_uv(me)
        bm = bmesh.new(); bm.from_mesh(me)
        # NEVER weld foliage/prop groups: their double-sided shells are duplicated face pairs at
        # IDENTICAL positions with opposite winding, and remove_doubles collapses each pair into
        # one face keeping a random side — salt-and-pepper inverted triangles all over trunks and
        # bushes (measured 15-16% on PALMTRUNK, 8% on SCRUB; ledger 0024, Kevin: "points are
        # closing with the wrong vectors"). Weld exists to clean GENERATED seams, not authored props.
        if not ob.name.upper().startswith(("PALM", "TREE", "SCRUB", "BUSHES", "CHAINLINK",
                                           "1WALL", "RETWALL", "BUILDING_FABRIC", "PROPCONE", "BUILDING_TILTUP", "BUILDING_METAL", "BUILDING_STUCCO", "BUILDING_SIDING",
                                           "ROOFTOP", "GUARDRAIL", "BUILDING_DRYSTONE", "FARBLOCK")):
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
        else:
            # REPAIR damage already baked into the source .blend (earlier welds): a lone inverted
            # face's VERTEX normals are dominated by its coherent neighbours, so flipping any face
            # that opposes its own vertices' consensus heals salt-and-pepper inversion (0024's
            # residue, PALMTRUNK 13%) deterministically — and leaves true double-sided shells
            # alone, because their duplicated verts vote for their own side.
            bm.normal_update()
            for _ in range(3):
                flip = []
                for f in bm.faces:
                    cx = cy = cz = 0.0
                    for v in f.verts:
                        cx += v.normal.x; cy += v.normal.y; cz += v.normal.z
                    if (cx * cx + cy * cy + cz * cz) > 1e-12 and \
                       (f.normal.x * cx + f.normal.y * cy + f.normal.z * cz) < -1e-4:
                        flip.append(f)
                if not flip:
                    break
                bmesh.ops.reverse_faces(bm, faces=flip)
                bm.normal_update()
                print(f"[build_kn5_loop] {ob.name}: consensus-flipped {len(flip)} inverted faces")
        # CORRIDOR DISCIPLINE (ledger 0020, Kevin: "messy" = junctions & sidewalks + edges).
        # Rule 1: no sidewalk/kerb face inside ANY carriageway — this is 0013's sweep-through-
        # junction mechanism killed at the artifact: the sweep may run, the mouth gets carved.
        # Rule 2: no vegetation in the driving corridor below 5.2 m clearance (the canopy that
        # stood at station 10,545). Both use the same layered corridor query (deck-height guarded).
        upname = ob.name.upper()
        if upname.startswith("1KERB"):
            doomed = []
            for f in bm.faces:
                c = f.calc_center_median()
                d, deck = corr(c.x, c.y, c.z)
                if d < -0.15 and abs(c.z - deck) < 3.0:
                    doomed.append(f)
            if doomed:
                bmesh.ops.delete(bm, geom=doomed, context="FACES")
                print(f"[build_kn5_loop] {ob.name}: carved {len(doomed)} faces out of carriageways (0020)")
        elif upname.startswith(("TREETRUNK", "PALMTRUNK")):
            # Trunks are COLUMNS: band-cutting severs them and the ground gate flags the floating
            # tops (it did, twice — 2.0% then 1.5% hovering). Remove whole face-islands instead,
            # and only when the island's BASE stands in the road; a verge palm keeps every face.
            seen = set()
            doomed = []
            removed = 0
            for f0 in bm.faces:
                if f0.index in seen:
                    continue
                island, stack = [], [f0]
                seen.add(f0.index)
                while stack:
                    f = stack.pop()
                    island.append(f)
                    for e in f.edges:
                        for lf in e.link_faces:
                            if lf.index not in seen:
                                seen.add(lf.index)
                                stack.append(lf)
                lowz = min(v.co.z for f in island for v in f.verts)
                base = [f for f in island if f.calc_center_median().z < lowz + 1.0]
                bx = sum(f.calc_center_median().x for f in base) / len(base)
                by = sum(f.calc_center_median().y for f in base) / len(base)
                d, _deck = corr(bx, by, lowz + 0.5)
                if d < -0.3:
                    doomed.extend(island)
                    removed += 1
            if doomed:
                bmesh.ops.delete(bm, geom=doomed, context="FACES")
                print(f"[build_kn5_loop] {ob.name}: removed {removed} whole trunks standing in a road (0020)")
        elif upname.startswith(("TREECANOPY", "SCRUB", "PALMFROND", "BUSHES")):
            doomed = []
            for f in bm.faces:
                # big leaf cards span metres — a centroid test leaves their tips hanging in the
                # corridor (drive_test still counted 14 canopy stations). Any VERT inside dooms it.
                for v in f.verts:
                    d, deck = corr(v.co.x, v.co.y, v.co.z, vwin=7.0)
                    if d < 0.2 and 0.2 < (v.co.z - deck) < 5.2:
                        doomed.append(f)
                        break
            if doomed:
                bmesh.ops.delete(bm, geom=doomed, context="FACES")
                print(f"[build_kn5_loop] {ob.name}: trimmed {len(doomed)} leaf faces from the clearance envelope (0020)")
        if ob.name.upper().startswith("1GRASS"):
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.05)   # terrain must be watertight
            try:
                bmesh.ops.holes_fill(bm, edges=bm.edges, sides=16)
            except Exception as e:
                print(f"[build_kn5_loop] holes_fill skipped: {e}")
        # DRIVABLE surfaces must face UP or AC has no top collision and the car falls through. The
        # local->Blender axis remap (x,y,z)->(x,z,y) is a reflection that flipped every face down.
        # Fix DETERMINISTICALLY: reverse only the faces whose normal points down (normal.z<0). This
        # is NOT recalc_face_normals (which guesses "outward" from shape and picks DOWN on big
        # terrain); for a near-horizontal drivable surface "up" is unambiguous, so this can't guess
        # wrong or split the mesh. ...plus flat painted markings (MARKINGS/YLINE) — decals that
        # must face up to be seen from the car.
        if ob.name.upper().startswith(("1ROAD", "1GRASS", "1KERB", "MARKINGS", "YLINE")):
            bm.normal_update()
            down = [f for f in bm.faces if f.normal.z < 0]
            if down:
                bmesh.ops.reverse_faces(bm, faces=down)
            print(f"[build_kn5_loop] {ob.name}: flipped {len(down)}/{len(bm.faces)} faces up")
        bm.to_mesh(me); bm.free(); me.update()
        if len(me.loops) > VERT_CAP:         # smooth-shade big meshes so render-verts fit the 16-bit cap
            for poly in me.polygons:
                poly.use_smooth = True
            me.update()
        # loop-path over-cap guard: FATAL (the OBJ program guards in build_kn5.py; this path is its
        # own program and needs its own gate — a WARNING here shipped over-cap meshes before).
        assert_under_cap(ob.name, len(me.vertices))

    # 3. AC dummies from the real centreline (local frame x=E,y=up,z=N -> Blender x=E,y=N,z=up = (x,z,y))
    #    MULTI-LAYOUT (ledger 0047; fleet/LAWS.md L8 as amended): with more than one layouts[] entry
    #    the road kn5 carries NO AC_* nodes — every layout's grid / pits / timing gates ride in its
    #    own nodes-only spawn kn5 (tools/layout_dummies.py -> data/dummies_<id>.json ->
    #    scripts/ac/build_spawn_kn5.py), so no empties are created here and data/dummies.json is
    #    written EMPTY. The exporter writes every object it finds, so nothing can bake what is not
    #    there; verify_kn5 (a) fails a multi-layout road kn5 that carries a spawn node.
    FACING = ("AC_START", "AC_PIT", "AC_HOTLAP")
    dummies_out = {}
    _layouts = cfg.get("layouts", []) or []
    if len(_layouts) > 1:
        print(f"[build_kn5_loop] multi-layout ({len(_layouts)} layouts): spawns ride in per-layout kn5s — "
              f"no AC_* empties in the road scene, data/dummies.json = {{}}")
    else:
        from scripts.geometry import dummies as dmod
        local = json.loads((proj / "data" / "centerline.local.json").read_text())
        cl = [tuple(p) for p in local["points_xyz_m"]]
        widths = local["widths_m"]
        mirror_x = bool(cfg.get("mirror_x", False))
        # The engine draft's own placement first (scripts/geometry/build_mesh.py -> place_dummies on the
        # FINISHED centreline: the pits on the road that mesh has, the loop's start). Recomputed here from
        # centerline.local.json, Exotics Racing's 8 pits walked 14-45 m off the road (verify_kn5,
        # 2026-10-29; ledger 0060). The recomputation stays for a scene with no draft (the assembler's path).
        placed = dmod.load_draft(proj / "data" / "dummies.json")
        from_draft = bool(placed)
        if from_draft:
            print(f"[build_kn5_loop] AC dummies: the draft's data/dummies.json ({len(placed)} placements)")
        else:
            n_pits = 8
            # The start is a CONTRACT (0026): when the config declares start_arc_m, the grid goes there —
            # Kevin: "i prefer starting on alvarado toward college" (station 3,467 on the Lake Murray
            # loop); the straightest-window heuristic had parked it on Navajo. Declared beats derived.
            placed = dmod.place_dummies(cl, widths, n_sectors=3, n_pits=n_pits,
                                        start_arc_m=cfg.get("start_arc_m"))
            print(f"[build_kn5_loop] AC dummies: placed from centerline.local.json ({len(placed)}; no draft dummies.json)")
        # facing = the travel direction at AC_START_0, as a yaw about Blender Z(up): atan2(tx, -tz), the measured
        # convention of the per-layout spawn scenes (tools/layout_dummies.yaw_deg, ledger 0047; the exporter's
        # (x, z, -y) puts north at kn5 -Z, so an unrotated node faces south). The atan2(tx, tz) that stood here
        # faced a north-bound grid backwards. A mirrored draft's tangent is mirrored with it (the chain refuses
        # mirror_x: tools/ship_track.sh THE FRAME).
        start_at = placed.get("AC_START_0") or placed.get("AC_HOTLAP_START_0") or cl[0]
        start_yaw = dmod.facing_yaw(cl, start_at, mirror_x=mirror_x and from_draft)
        for name, (x, y, z) in placed.items():
            e = bpy.data.objects.new(name, None)
            e.empty_display_type = "ARROWS"; e.empty_display_size = 4.0
            e.location = (x, z, y)                                  # local (E,up,N) -> Blender (E,N,up)
            if any(name.startswith(p) for p in FACING):
                e.rotation_euler = (0.0, 0.0, start_yaw)
            bpy.context.scene.collection.objects.link(e)
            dummies_out[name] = [round(x, 3), round(y, 3), round(z, 3)]
    (proj / "data" / "dummies.json").write_text(json.dumps(dummies_out, indent=1))

    # 4. PBR materials (prefix -> texture set); export_kn5_addon re-derives shader from the same
    #    prefix. Reconciled to the ENGINE pbr: config/capture texture_overrides apply here AND at
    #    export (load_overrides), so a loop project can e.g. swap 1GRASS dry dirt for green turf
    #    via track.config.json without renaming meshes.
    from scripts.ac import pbr
    overrides = pbr.load_overrides(proj)
    if overrides:
        print(f"[build_kn5_loop] texture overrides: {sorted(overrides)}")
    for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
        pbr.setup_material(bpy, ob, overrides=overrides)

    # 5. pack textures + save the AC-ready .blend for the export pass
    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        print(f"[build_kn5_loop] pack_all warning: {e}")
    out = proj / "blender" / f"{slug}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    meshes = [o.name for o in bpy.data.objects if o.type == "MESH"]
    print(f"[build_kn5_loop] prepped {meshes}  + {len(dummies_out)} dummies -> {out}")


if __name__ == "__main__":
    main()
