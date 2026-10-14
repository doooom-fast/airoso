"""Verify the authored race furniture against its declaration — a ship gate (ledgers 0047 + 0049).

Runs after tools/author_race_furniture_blend.py, pure Python, exit 1 on any miss. Reads
data/race_authored.json (the author tool's per-object counts, seating and the SEATED ring centres)
and data/barrier_bands.json (tools/barrier_bands.py, version 2 — the declared bands and, per race
layout, `corridors.<id>`: the closure line, zones, lane, mouths), plus data/centerline.local.json and
data/median_bands.json. The declaration IS the authored line (the 2026-10-08 median_zone precedent);
this file proves the two agree BEFORE a kn5 exists, and the built gates (drive_test barrier_missing,
no_route) then prove it on the BUILT OBJ (L5). Every check below runs on the COMMON set (curb strips,
kerbs) and on EACH race layout's closure (counts.by_layout).

  A  provenance — the authored file was built from this declaration: not a stand-in, same
     edge_mode and barrier height as the bands, the RACE prefixes the export split keys on; no run
     failed to seat; interpolated rings <= 1 %
  B  budgets — every object stays ONE AC mesh: rings <= 900 (the author tool's own cap is 800),
     positions < 60,000, flat-shaded render verts (loops x 1.5) < 65,535, a unique RACE-prefixed
     name, seating gap <= 0.05 m
  C' closures (ledger 0049) — per race layout: one object chain per declared closure run, consecutive
     parts joined on a shared ring (JOIN_TOL_M); EVERY ring within CLOSE_TOL_M of the declared curve
     (corridors.<id>.closure_y_by_vertex, lerped between vertices the way the author densifies);
     the declaration itself puts no closure vertex in a BOX or WHOLE zone; each run's first and last
     ring stands AT its pin: within PIN_TOL_M of the declared far curb-strip line, at the pin vertex
  D  kerb-line strips — EVERY centreline vertex has a ring on EACH side, bridge spans included (C1 —
     this inverts ledger 0047's "no ring inside a span"), except the vertices the DECLARATION trims
     (barrier_bands.json `edge_corners[].removed`, a SET check); every declared corner has an authored
     ring AT its X (CORNER_TOL_M)
  E  race kerbs — the declared (apex, in|out) set == the authored set (8 on SD since the 0049 fix round: the
     1514 / 2319 inside kerbs are declared DROPPED, `kerbs_dropped`, and none of those may be authored), each
     with the declared (clipped / pulled-back) i/j; every kerb's footprint stands >= KERB_CLEAR_M off EVERY
     race layout's AUTHORED closure footprint (re-measured here; the author's own clip is reported); and NO
     kerb station under another ROAD sheet (race_authored objects[].under_road, measured by the author on the
     real deck at the kerb's lip, mid-line and outer edge — a kerb laid across a ribbon fold is invisible from
     the seat; the fix is track.config.json race.kerbs.trims)
  F  spawn clearance — HARD: every grid / pit / hotlap slot of every race layout, re-measured HERE from
     data/dummies_<id>.json against the declared strip faces AND (0049) that layout's declared lane
     (corridors.<id>.lane_by_vertex): a 1.9 m car stands >= SPAWN_MARGIN_M = 0.30 m off every face
  G  lamp posts — every lamp mast stands OUTSIDE every kerb-line strip footprint and every race
     layout's closure footprint (lerped at the mast); FAIL on any overlap, the minimum margin reported.
     Scenery (0049 fix round): every CSP TreeFX trunk (radius TREE_TRUNK_R_M) and every W1-6 sign post
     (data/signs.local.json base_xz, SIGN_POST_R_M) stands OUTSIDE each race layout's LANE
     (corridors.<id>.lane_by_vertex) and outside both curb strips and that layout's closure — none of them is
     physical in AC, so a trunk in the lane is a car driving through a palm. The trees are the WRITTEN
     trees.txt with --trees (the ship re-checks the packed file after tools/make_treefx.py), else
     make_treefx's own plan of it (make_treefx.plan, every species assumed present)
  H  ring density — every consecutive pair of curb-strip / closure ring centres vs the DECLARED offset
     curve rebuilt here from the bands + centreline alone: a chord error > CHORD_FAIL_M = 0.15 m FAILS
  I  inside-out — no span of any strip / closure / kerb has a profile column running backwards
  J  zero free ends — every curb-strip end is a `join` met by a same-side neighbour's end (the strips
     are closed loops); every closure end is either a join with its own run's next part or a PIN:
     its centre within PIN_TOL_M of the AUTHORED far curb strip's centre polyline (re-measured), the
     end ring full height (h == barrier_height_m) and full width (ls == 1)
  K  ownership — every closure's name token is a declared corridor token and its object records that
     owner / layout / collection (RACE_CLOSE_<TOKEN>); the common furniture owns no token and sits in RACE;
     no RACE object of an unknown kind
  L  bridges — 0 interpolated rings inside the declared bridge spans (race_authored bridge_seating), and
     the strips do stand on the decks
  M  mouths — every sealed mouth line (closed_mouths) lies ON the authored curb strip of its side
     (MOUTH_TOL_M) — both strips are common, so this holds in both race layouts; every mouth has a declared
     policy per layout (sealed_race_strip / sealed_far_strip / behind_closure), and where it is
     `behind_closure` that layout's own authored closure runs past the whole mouth, between lane and mouth
  N  retired — no `1WALL_race_kbar_*` object anywhere; centre_w_by_vertex all 0; no centre run
  O  another deck — HARD since 2026-10-11 (was reported only): no strip / kerb ring with another ROAD sheet more
     than OTHER_DECK_FAIL_M (0.05 m) over its base (a side-street mouth or a ribbon fold — the ribbon owner's
     defect, 0033/0046 class), measured by the author at that threshold or tighter

Reported, never gated: the worst deck-vs-data height, the minimum spawn clearance, the author's kerb clips.

    python tools/verify_race.py <project-dir> [--allow-standin] [--authored <file>] [--bands <file>]
                                [--config <track.config.json>] [--pre-author | --scenery-only] [--lap <id>]
                                [--trees <trees.txt>] [--out <file>]

--pre-author runs F (disk) and G only — no data/race_authored.json needed; it writes
data/race_verify.pre.json, never the full report's file. --scenery-only runs G's trunks + posts only (no
authored file, no spawns, no lamps) and writes data/race_verify.scenery.json; `--trees <trees.txt>` reads the
TreeFX placements from a written file (kn5 frame x, y, -z) instead of planning them. Writes
data/race_verify.json (or --out).
Plain functions so tests/run_tests.py can drive it without Blender. Independent of tools/race_furniture.py
by design (it re-derives every declared curve itself).
"""
from __future__ import annotations

import importlib.util
import json
import math
import re
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
RACE_PREFIXES = ("1WALL_RACE", "1KERB_RACE")
EDGE_TAG, CLOSE_TAG, KBAR_TAG, KERB_TAG = "1WALL_RACE_EDGE_", "1WALL_RACE_CLOSE_", "1WALL_RACE_KBAR_", "1KERB_RACE_"
COMMON_COLLECTION = "RACE"
LAP_FIELD = "lap"       # ledger 0054: a lap's common set is 1WALL_race_edge_lap<lap>_* / 1KERB_race_lap<lap>_* in RACE_LAP_<LAP>
MAX_RINGS = 900
MAX_POSITIONS = 60_000
RENDER_VERT_CAP = 65_535
SEAT_GAP_M = 0.05
OTHER_DECK_FAIL_M = 0.05  # O: another ROAD sheet over a strip ring by more than this FAILS (author OTHER_DECK_M)
INTERP_MAX_FRAC = 0.01
JOIN_TOL_M = 0.05       # a `join` end and its neighbour's end are the SAME ring (split_plan shares boundary rings)
CLOSE_TOL_M = 0.05      # C': every closure ring within this of the declared curve
PIN_TOL_M = 0.05        # C' / J: a closure's end ring vs the far curb strip's line (declared and authored)
KERB_CLEAR_M = 0.05     # E: a kerb's footprint vs every closure footprint (race_furniture.KERB_CLOSURE_CLEAR_M)
ROUND_M = 0.01          # ring_centres are rounded to 0.01 m
MOUTH_TOL_M = 0.10      # M: a sealed mouth line's points vs the authored strip centre polyline
VERTEX_TOL = 1          # edge rings sit ~6 m off the centreline: on a tight curve the nearest vertex may be k+-1
CHORD_FAIL_M = 0.15     # H: a strip span chording the declared offset curve by more than this FAILS (2026-10-11)
CHORD_TARGET_M = 0.10   # H: race_furniture.CHORD_MAX_M, the author's own target (quoted in the message)
SPACING_TARGET_M = 3.5  # H: race_furniture.RING_SPACING_MAX_M — ring spacing above it is reported, never gated
SPACING_ROUND_M = 0.015 # H: ring_centres are rounded to 0.01 m, so a 3.500 m span can read 3.507 m
DENSE_PER_VERTEX = 32   # H / C': declared-curve samples per centreline interval
OFF_CURVE_M = 0.5       # H: a ring centre farther than this from every declared sample is not measured (C' / D judge it)
SPAN_MAX_VERTICES = 40  # H: a span covering more centreline intervals than this (~120 m) is not measured (D judges holes)
CORNER_TOL_M = 0.05     # D: a declared trimmed corner's X vs the nearest authored ring centre of that side
CAR_HALF_W_M = 0.95     # a 1.9 m car on a grid / pit slot
SPAWN_MARGIN_M = 0.30   # F: HARD floor between a slot's car and any strip / lane face (GATES-CHANGELOG 2026-10-11)
FACING = ("AC_START", "AC_PIT", "AC_HOTLAP")   # the slots a car sits on (AC_TIME_* are timing planes)
LAMP_ARM_FALLBACK_M = 1.8      # author_lamps_blend.ARM_M when its source cannot be read
LAMP_POST_H_FALLBACK_M = 11.5  # author_lamps_blend.POST_H
MAST_R_FALLBACK_M = 0.60       # lamp_post.obj base plate corner radius at 11.5 m (measured 0.585 m)
LAMP_CELL_M = 30.0             # author_lamps_blend's nearest-centreline cell (its fallback is vertex 0)
KNOWN_KINDS = ("edge", "close", "kerb")
TREE_TRUNK_R_M = 0.30   # G scenery: a TreeFX trunk's radius (INVENTED, 0049 fix round: palm trunks 0.3-0.5 m across)
SIGN_POST_R_M = 0.03    # G scenery: the W1-6 sign's 2 in post (tools/author_signs_blend.py), rounded up
SCENERY_REACH_M = 2.0   # G scenery: farther than half-width + this from the centreline = not beside the race road


# --- geometry helpers ------------------------------------------------------------------------

class VertexGrid:
    """nearest centreline vertex to (x, z) — a 20 m cell hash, brute force as the fallback"""

    CELL = 20.0

    def __init__(self, pts):
        self.pts = pts
        self.cells: dict[tuple[int, int], list[int]] = {}
        for k, p in enumerate(pts):
            self.cells.setdefault((int(math.floor(p[0] / self.CELL)), int(math.floor(p[2] / self.CELL))), []).append(k)

    def nearest(self, x, z):
        cx, cz = int(math.floor(x / self.CELL)), int(math.floor(z / self.CELL))
        best, bk = float("inf"), -1
        for radius in (1, 2, 4):
            for i in range(cx - radius, cx + radius + 1):
                for j in range(cz - radius, cz + radius + 1):
                    for k in self.cells.get((i, j), ()):
                        d = (self.pts[k][0] - x) ** 2 + (self.pts[k][2] - z) ** 2
                        if d < best:
                            best, bk = d, k
            if bk >= 0 and math.sqrt(best) <= radius * self.CELL:
                return bk
        if bk >= 0:
            return bk
        for k, p in enumerate(self.pts):
            d = (p[0] - x) ** 2 + (p[2] - z) ** 2
            if d < best:
                best, bk = d, k
        return bk


class SegGrid:
    """xz segments in a 4 m cell hash: dist(p) = the distance from p to the nearest one (inf beyond `reach` cells)"""

    CELL = 4.0

    def __init__(self, polylines):
        self.segs = []
        self.cells: dict[tuple[int, int], list[int]] = {}
        for cs in polylines:
            for a, b in zip(cs, cs[1:]):
                a2, b2 = (a[0], a[-1]) if len(a) == 2 else (a[0], a[2]), (b[0], b[-1]) if len(b) == 2 else (b[0], b[2])
                si = len(self.segs)
                self.segs.append((a2, b2))
                for i in range(int(math.floor(min(a2[0], b2[0]) / self.CELL)), int(math.floor(max(a2[0], b2[0]) / self.CELL)) + 1):
                    for j in range(int(math.floor(min(a2[1], b2[1]) / self.CELL)), int(math.floor(max(a2[1], b2[1]) / self.CELL)) + 1):
                        self.cells.setdefault((i, j), []).append(si)

    def near(self, p, reach=2):
        cx, cz = int(math.floor(p[0] / self.CELL)), int(math.floor(p[1] / self.CELL))
        seen = set()
        for i in range(cx - reach, cx + reach + 1):
            for j in range(cz - reach, cz + reach + 1):
                for si in self.cells.get((i, j), ()):
                    if si not in seen:
                        seen.add(si)
                        yield self.segs[si]

    def dist(self, p, reach=2):
        return min((_seg_dist(p, a, b) for a, b in self.near(p, reach)), default=float("inf"))


def _dist_xz(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def _max_consecutive_gap(centres):
    worst = 0.0
    for a, b in zip(centres, centres[1:]):
        worst = max(worst, _dist_xz(a, b))
    return worst


def _unique_count(pts):
    return len(pts) - 1 if len(pts) > 1 and _dist_xz(pts[0], pts[-1]) < 1e-6 else len(pts)


def _seg_dist(p, a, b):
    ax, az = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + az * az
    t = 0.0 if L2 <= 0 else max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * az) / L2))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * az)


def _seg_seg_dist(p1, p2, q1, q2):
    d = (p2[0] - p1[0]) * (q2[1] - q1[1]) - (p2[1] - p1[1]) * (q2[0] - q1[0])
    if abs(d) > 1e-12:
        t = ((q1[0] - p1[0]) * (q2[1] - q1[1]) - (q1[1] - p1[1]) * (q2[0] - q1[0])) / d
        s = ((q1[0] - p1[0]) * (p2[1] - p1[1]) - (q1[1] - p1[1]) * (p2[0] - p1[0])) / d
        if 0.0 <= t <= 1.0 and 0.0 <= s <= 1.0:
            return 0.0
    return min(_seg_dist(p1, q1, q2), _seg_dist(p2, q1, q2), _seg_dist(q1, p1, p2), _seg_dist(q2, p1, p2))


def _walk(i, j, m):
    return list(range(i, j + 1)) if j >= i else list(range(i, m)) + list(range(0, j + 1))


def race_owner(name):
    """the token of `1WALL_race_close_<token>_...` (lower case), else None — race_furniture.race_owner, restated
    so this gate stays independent of the module it judges"""
    if not str(name).upper().startswith(CLOSE_TAG):
        return None
    return str(name)[len(CLOSE_TAG):].split("_", 1)[0].lower() or None


def race_lap(name):
    """the lap token of a lap's common furniture name (`1WALL_race_edge_lap<tok>_...` / `1KERB_race_lap<tok>_...`),
    else None — race_furniture.race_lap, restated so this gate stays independent of the module it judges"""
    u = str(name).upper()
    for tag in (EDGE_TAG, KERB_TAG):
        if u.startswith(tag):
            field = str(name)[len(tag):].split("_", 1)[0]
            tok = field[len(LAP_FIELD):].lower() if field.lower().startswith(LAP_FIELD) else ""
            return tok if re.match(r"^[a-z0-9]+$", tok) else None
    return None


def common_collection(lap=None):
    """RACE (the mainline's common set) or RACE_LAP_<LAP>"""
    return COMMON_COLLECTION if not lap else f"{COMMON_COLLECTION}_LAP_{str(lap).upper()}"


def race_kind(name):
    u = str(name).upper()
    for tag, kind in ((CLOSE_TAG, "close"), (EDGE_TAG, "edge"), (KERB_TAG, "kerb"), (KBAR_TAG, "kbar")):
        if u.startswith(tag):
            return kind
    return "other" if u.startswith(RACE_PREFIXES) else None


def _corridors(bands):
    return (bands or {}).get("corridors") or {}


def _token(bands, lid):
    return str((_corridors(bands).get(lid) or {}).get("token") or "").lower()


def _forward_runs(c, m):
    """[(i, j, record)] — a corridor's closure runs in FORWARD vertex order (the walk on which closure_y is declared
    everywhere; a run declared in reverse travel order is turned round)"""
    y = c.get("closure_y_by_vertex") or []
    out = []
    for r in c.get("runs") or []:
        i, j = int(r["i"]) % m, int(r["j"]) % m
        fw, bw = _walk(i, j, m), _walk(j, i, m)
        ok_f = all(k < len(y) and y[k] is not None for k in fw)
        ok_b = all(k < len(y) and y[k] is not None for k in bw)
        if ok_f and (not ok_b or len(fw) <= len(bw)):
            out.append((i, j, r))
        elif ok_b:
            out.append((j, i, r))
        else:
            out.append((i, j, dict(r, _broken=True)))
    return out


def _closure_side(c):
    s = str(c.get("closure_side") or "").upper()
    if s in ("L", "R"):
        return s
    return "R" if str(c.get("direction", "forward")) == "reverse" else "L"


# --- the checks ----------------------------------------------------------------------------------

def verify(authored: dict | None, bands: dict, pts: list, island_w: list, *, allow_standin: bool = False,
           widths: list | None = None, spawns: dict | None = None, lamps: list | None = None,
           pre_author: bool = False, lamp_arm_m: float | None = None, mast_r_m: float | None = None,
           scenery: list | None = None, scenery_source: str | None = None, lap: str | None = None) -> dict:
    """A-E and J-N (+ the author's own F record) on the authored file unless ``pre_author``; H and I too; F
    re-measured from ``spawns`` ({race layout id: dummies dict, or None when its file is missing}), G from
    ``lamps`` (lights.local.json heads) and G-scenery from ``scenery`` (TreeFX trunks + sign posts, scenery_items)
    whenever they and ``widths`` are given (main always gives them). ``lap`` (ledger 0054): the group is a lap's —
    ``pts`` / ``island_w`` / ``widths`` its line (data/lap.<lap>.json), ``bands`` its declaration, and its common
    set must carry the lap token in its names and stand in RACE_LAP_<LAP>; None = the mainline's group, whose
    common set must carry none."""
    fails: list[str] = []
    warns: list[str] = []
    counts: dict = {"by_layout": {}}
    if not pre_author:
        _verify_authored(authored or {}, bands, pts, island_w, allow_standin, fails, warns, counts, widths, lap=lap)
        _verify_inside_out(authored or {}, bands, fails, warns, counts)
        if widths is not None:
            _verify_density(authored or {}, bands, pts, widths, fails, warns, counts)
        else:
            warns.append("H / C' pin line / M: no centreline widths given — the declared strip curve cannot be rebuilt")
    m = _unique_count(pts)
    grid = VertexGrid(pts[:m])
    if spawns is not None and widths is not None:
        _verify_spawns(spawns, bands, pts, widths, grid, fails, warns, counts)
    if lamps is not None and widths is not None:
        _verify_lamps(lamps, bands, pts, widths, grid, fails, warns, counts, lamp_arm_m, mast_r_m)
    if scenery is not None and widths is not None:
        _verify_scenery(scenery, bands, pts, widths, grid, fails, warns, counts, scenery_source)
    return {"ok": not fails, "fails": fails, "warnings": warns, "counts": counts}


# --- F (disk) / G: the strips where the DECLARATION puts them — independent of race_furniture.py -------

def _left_normal_at(pts, k, m):
    a, b = pts[(k - 1) % m], pts[(k + 1) % m]
    tx, tz = b[0] - a[0], b[2] - a[2]
    L = math.hypot(tx, tz) or 1.0
    return -tz / L, tx / L


def _lateral(pts, m, k, x, z):
    """signed lateral of (x, z) at vertex k: + = left of FORWARD travel"""
    lx, lz = _left_normal_at(pts, k, m)
    return (x - pts[k][0]) * lx + (z - pts[k][2]) * lz


def _edge_c(bands):
    params = bands.get("params", {}) or {}
    c = params.get("edge_centre_from_lip_m")
    return float(c) if c is not None else (-0.485 if str(params.get("edge_mode", "road")) == "road" else 0.445)


def strip_footprint(bands: dict, widths: list, k: int):
    """(edge, centre_half) at vertex k from the declaration alone: edge = (inner, outer) |lateral| of the
    kerb-line strip (both curb faces) where edge_strip_by_vertex > 0, else None — inner = the road-side
    face = half_w + edge_centre_from_lip_m - barrier_half_m (road mode: half_w - 0.82; walk: half_w + 0.11);
    centre_half = centre_w / 2 where a (RETIRED, N fails it) centre chain is declared, else None."""
    params = bands.get("params", {}) or {}
    bh = float(params.get("barrier_half_m", 0.335))
    c = _edge_c(bands)
    es = bands.get("edge_strip_by_vertex") or bands.get("edge_inset_by_vertex") or []
    cw = bands.get("centre_w_by_vertex") or []
    half = float(widths[k]) / 2.0
    edge = (half + c - bh, half + c + bh) if (k < len(es) and es[k] > 0) else None
    centre = float(cw[k]) / 2.0 if (k < len(cw) and cw[k] > 0) else None
    return edge, centre


def spawn_slots(dummies: dict, pts: list, widths: list, bands: dict, grid=None, layout_id: str | None = None) -> list[dict]:
    """every FACING slot's car clearance to the edge-strip face and, for a race layout with a declared corridor
    (ledger 0049), to the nearer face of its lane (corridors.<id>.lane_by_vertex, forward frame)"""
    m = _unique_count(pts)
    grid = grid or VertexGrid(pts[:m])
    lane = (_corridors(bands).get(layout_id) or {}).get("lane_by_vertex") if layout_id else None
    rows = []
    for name, p in sorted(dummies.items()):
        if name.startswith("_") or not name.startswith(FACING) or not isinstance(p, (list, tuple)) or len(p) < 3:
            continue
        x, z = float(p[0]), float(p[2])
        k = grid.nearest(x, z)
        lat = _lateral(pts, m, k, x, z)
        edge, centre = strip_footprint(bands, widths, k)
        a = abs(lat)
        row = {"name": name, "vertex": k, "lat_m": round(lat, 3),
               "edge_face_m": round(edge[0], 3) if edge else None,
               "clear_edge_m": round(edge[0] - (a + CAR_HALF_W_M), 3) if edge else None,
               "clear_centre_m": round(a - CAR_HALF_W_M - centre, 3) if centre is not None else None,
               "lane_m": None, "clear_lane_m": None}
        if lane and k < len(lane) and lane[k]:
            lo, hi = float(lane[k][0]), float(lane[k][1])
            row["lane_m"] = [round(lo, 3), round(hi, 3)]
            row["clear_lane_m"] = round(min(lat - CAR_HALF_W_M - lo, hi - (lat + CAR_HALF_W_M)), 3)
        rows.append(row)
    return rows


def _verify_spawns(spawns, bands, pts, widths, grid, fails, warns, counts):
    mins, slots = {}, {}
    for lid, d in sorted(spawns.items()):
        if d is None:
            fails.append(f"F: {lid}: no data/dummies_{lid}.json — run tools/layout_dummies.py (the spawn kn5 is built from it)")
            continue
        if d.get("_synthesised"):
            fails.append(f"F: {lid}: dummies_{lid}.json is SYNTHESISED — run tools/layout_dummies.py first")
        if _corridors(bands) and lid not in _corridors(bands):
            fails.append(f"F: {lid}: no corridors.{lid} declared — its lane cannot be checked (re-run tools/barrier_bands.py)")
        rows = spawn_slots(d, pts, widths, bands, grid, layout_id=lid)
        if not rows:
            fails.append(f"F: {lid}: dummies_{lid}.json holds no grid / pit slot")
            continue
        for r in rows:
            for key, what in (("clear_edge_m", "edge-strip face"), ("clear_centre_m", "centre chain"),
                              ("clear_lane_m", f"lane face {r['lane_m']}")):
                v = r[key]
                if v is not None and v < SPAWN_MARGIN_M:
                    fails.append(f"F: {lid}: {r['name']} at v{r['vertex']} lat {r['lat_m']:+.2f}: {v:.2f} m clear of the "
                                 f"{what} (< {SPAWN_MARGIN_M:.2f} m{'; the car OVERLAPS it' if v < 0 else ''})")
        vals = [r[k] for r in rows for k in ("clear_edge_m", "clear_centre_m", "clear_lane_m") if r[k] is not None]
        mins[lid] = min(vals) if vals else None
        slots[lid] = rows
    counts["spawn_margin_m"] = SPAWN_MARGIN_M
    counts["spawn_min_clear_m"] = mins
    counts["spawn_slots"] = slots
    if not spawns:
        warns.append("F: no race layout declared — spawn clearance not measured")


def _author_lamps_constant(name: str, fallback: float, path: Path | None = None) -> float:
    """`NAME = <float>` from tools/author_lamps_blend.py — a bpy script, so PARSED, never imported: the
    check uses the author tool's own number and cannot drift from it"""
    p = path or (AIROSO / "tools" / "author_lamps_blend.py")
    try:
        mt = re.search(rf"^{name}\s*=\s*([0-9]+(?:\.[0-9]+)?)", p.read_text(encoding="utf-8"), re.M)
    except OSError:
        return fallback
    return float(mt.group(1)) if mt else fallback


def mast_radius_m(post_h: float, obj: Path | None = None) -> float:
    """circumscribed radius of the lamp model's base (vertices within 5 % of its height of the ground),
    at the author tool's scale POST_H / model height"""
    obj = obj or (AIROSO / "assets" / "models" / "lamp_post.obj")
    try:
        verts = []
        for ln in obj.read_text(encoding="utf-8", errors="ignore").splitlines():
            if ln.startswith("v "):
                q = ln.split()
                verts.append((float(q[1]), float(q[2]), float(q[3])))
    except OSError:
        return MAST_R_FALLBACK_M
    if not verts:
        return MAST_R_FALLBACK_M
    lo, top = min(v[1] for v in verts), max(v[1] for v in verts)
    base = [math.hypot(v[0], v[2]) for v in verts if v[1] - lo <= 0.05 * (top - lo)]
    return max(base) * (post_h / top) if base and top > 0 else MAST_R_FALLBACK_M


def lamp_bases(heads: list, pts: list, arm_m: float) -> list[dict]:
    """tools/author_lamps_blend.py's base rule, replicated: road-ward = head -> the nearest centreline
    point in the 3 x 3 30 m cells around the head (point 0 when none — that tool's own fallback, flagged
    here), base = head - arm_m * road-ward"""
    cells: dict[tuple[int, int], list[int]] = {}
    for i, p in enumerate(pts):
        cells.setdefault((int(p[0] // LAMP_CELL_M), int(p[2] // LAMP_CELL_M)), []).append(i)
    out = []
    for h in heads:
        hx, hz = float(h[0]), float(h[2])
        best, bi = float("inf"), 0
        cx, cz = int(hx // LAMP_CELL_M), int(hz // LAMP_CELL_M)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for i in cells.get((cx + dx, cz + dz), ()):
                    d = (pts[i][0] - hx) ** 2 + (pts[i][2] - hz) ** 2
                    if d < best:
                        best, bi = d, i
        c = pts[bi]
        L = math.hypot(c[0] - hx, c[2] - hz) or 1e-9
        rx, rz = (c[0] - hx) / L, (c[2] - hz) / L
        out.append({"x": hx - rx * arm_m, "z": hz - rz * arm_m, "fallback": best == float("inf")})
    return out


def _closure_y_at(y, pts, m, k, x, z):
    """the declared closure lateral at (x, z), lerped along the centreline segment the point projects onto (either
    side of its nearest vertex k); None where no closure is declared"""
    best = None
    for a, b in ((k - 1) % m, k), (k, (k + 1) % m):
        if a >= len(y) or b >= len(y):
            continue
        dx, dz = pts[b][0] - pts[a][0], pts[b][2] - pts[a][2]
        L2 = dx * dx + dz * dz or 1.0
        t = max(0.0, min(1.0, ((x - pts[a][0]) * dx + (z - pts[a][2]) * dz) / L2))
        d = math.hypot(x - pts[a][0] - t * dx, z - pts[a][2] - t * dz)
        ya, yb = y[a], y[b]
        if ya is None and yb is None:
            continue
        yy = ya if yb is None else (yb if ya is None else ya + (yb - ya) * t)
        if best is None or d < best[0]:
            best = (d, yy)
    return None if best is None else float(best[1])


def lamp_margins(bases: list, pts: list, widths: list, bands: dict, mast_r: float, grid=None) -> list[dict]:
    """per mast: the clearance from its base footprint (radius mast_r) to the nearest strip footprint at its
    nearest vertex — the curb strips and (ledger 0049) every race layout's closure, lerped at the mast; negative =
    the mast stands IN it. Masts beside no strip are not listed."""
    m = _unique_count(pts)
    grid = grid or VertexGrid(pts[:m])
    bh = float((bands.get("params") or {}).get("barrier_half_m", 0.335))
    rows = []
    for i, b in enumerate(bases):
        k = grid.nearest(b["x"], b["z"])
        lat = _lateral(pts, m, k, b["x"], b["z"])
        a = abs(lat)
        edge, centre = strip_footprint(bands, widths, k)
        cand = []
        if edge:
            inner, outer = edge
            d = (a - outer) if a >= outer else ((inner - a) if a <= inner else -min(a - inner, outer - a))
            cand.append(("edge", d - mast_r))
        if centre is not None:
            cand.append(("centre", a - centre - mast_r))
        closure = []
        for lid, c in sorted(_corridors(bands).items()):
            yy = _closure_y_at(c.get("closure_y_by_vertex") or [], pts, m, k, b["x"], b["z"])
            if yy is not None:
                closure.append((f"closure_{lid}", abs(lat - yy) - bh - mast_r))
        cand += closure
        if not cand:
            continue
        kind, mg = min(cand, key=lambda t: t[1])
        ck, cm = min(closure, key=lambda t: t[1]) if closure else (None, None)
        rows.append({"lamp": i, "vertex": k, "lat_m": round(lat, 3), "base_xz": [round(b["x"], 2), round(b["z"], 2)],
                     "against": kind, "margin_m": round(mg, 3), "fallback": b["fallback"],
                     "closure": ck, "closure_margin_m": None if cm is None else round(cm, 3)})
    return rows


def _verify_lamps(heads, bands, pts, widths, grid, fails, warns, counts, arm_m=None, mast_r=None):
    arm = arm_m if arm_m is not None else _author_lamps_constant("ARM_M", LAMP_ARM_FALLBACK_M)
    post_h = _author_lamps_constant("POST_H", LAMP_POST_H_FALLBACK_M)
    r_m = mast_r if mast_r is not None else mast_radius_m(post_h)
    bases = lamp_bases(heads, pts, arm)
    rows = lamp_margins(bases, pts, widths, bands, r_m, grid)
    bad = sorted((r for r in rows if r["margin_m"] < 0), key=lambda r: r["margin_m"])
    for r in bad[:10]:
        fails.append(f"G: lamp {r['lamp']} at v{r['vertex']} lat {r['lat_m']:+.2f} ({r['base_xz'][0]}, {r['base_xz'][1]}): "
                     f"its mast stands {-r['margin_m']:.2f} m inside the {r['against']} strip footprint")
    if len(bad) > 10:
        fails.append(f"G: ... and {len(bad) - 10} more lamp masts inside a strip footprint")
    worst = min(rows, key=lambda r: r["margin_m"]) if rows else None
    nfb = sum(1 for b in bases if b["fallback"])
    if nfb:
        warns.append(f"G: {nfb} lamp heads have no centreline point within the 30 m cells around them — "
                     f"author_lamps_blend aims those at vertex 0 (measured as authored)")
    closure_rows = [r for r in rows if r.get("closure_margin_m") is not None]
    counts.update({"lamps": len(bases), "lamps_checked": len(rows), "lamp_arm_m": arm, "lamp_post_h_m": post_h,
                   "mast_r_m": round(r_m, 3), "lamp_min_margin_m": worst["margin_m"] if worst else None,
                   "lamp_min": worst, "lamps_inside": len(bad),
                   "lamp_min_vs_closure": min(closure_rows, key=lambda r: r["closure_margin_m"]) if closure_rows else None})


# --- G (scenery): TreeFX trunks and sign posts vs every race layout's lane and walls -------------------

_TREE_RE = re.compile(r"^\s*tree:\s*([^;]+);\s*pos\s*=\s*([-0-9.eE+]+)\s*,\s*([-0-9.eE+]+)\s*,\s*([-0-9.eE+]+)")


def tree_items_from_txt(text: str) -> list[dict]:
    """the `tree: <model>.bin; pos=X, Y, Z; ...` lines of a TreeFX trees.txt (tools/make_treefx.py) as scenery
    items. trees.txt is in the kn5 world (x, y, -z of the engine frame): z is flipped back here."""
    out = []
    for ln in text.splitlines():
        mt = _TREE_RE.match(ln)
        if mt:
            out.append({"kind": "tree", "id": f"{mt.group(1).strip()}#{len(out)}", "x": float(mt.group(2)),
                        "z": -float(mt.group(4)), "r": TREE_TRUNK_R_M})
    return out


def tree_items_planned(proj: Path) -> list[dict]:
    """what tools/make_treefx.py WILL write, from its own planner (make_treefx.plan, every species assumed present:
    positions only) — G runs before the models are copied; the ship re-checks the written trees.txt (--trees)"""
    spec = importlib.util.spec_from_file_location("_make_treefx_ro", AIROSO / "tools" / "make_treefx.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [{"kind": "tree", "id": f"{e['model']}@{e['zone']}#{i}", "x": float(e["x"]), "z": float(e["z"]),
             "r": TREE_TRUNK_R_M} for i, e in enumerate(mod.plan(proj, all_species=True)["entries"])]


def sign_items(signs: dict) -> list[dict]:
    """every W1-6 sign post of data/signs.local.json (tools/place_signs.py: `base_xz`, engine frame)"""
    out = []
    for s in (signs or {}).get("signs", []) or []:
        b = s.get("base_xz")
        if isinstance(b, (list, tuple)) and len(b) >= 2:
            out.append({"kind": "sign", "id": str(s.get("id")), "x": float(b[0]), "z": float(b[1]), "r": SIGN_POST_R_M})
    return out


def _lane_at(lane, pts, m, k, x, z):
    """the declared lane [lo, hi] at (x, z), lerped along the centreline segment the point projects onto (either side
    of its nearest vertex k, the _closure_y_at rule); None where no lane is declared"""
    best = None
    for a, b in ((k - 1) % m, k), (k, (k + 1) % m):
        if a >= len(lane) or b >= len(lane) or not lane[a] or not lane[b]:
            continue
        dx, dz = pts[b][0] - pts[a][0], pts[b][2] - pts[a][2]
        L2 = dx * dx + dz * dz or 1.0
        t = max(0.0, min(1.0, ((x - pts[a][0]) * dx + (z - pts[a][2]) * dz) / L2))
        d = math.hypot(x - pts[a][0] - t * dx, z - pts[a][2] - t * dz)
        lo = float(lane[a][0]) + (float(lane[b][0]) - float(lane[a][0])) * t
        hi = float(lane[a][1]) + (float(lane[b][1]) - float(lane[a][1])) * t
        if best is None or d < best[0]:
            best = (d, lo, hi)
    if best is None:
        return (float(lane[k][0]), float(lane[k][1])) if k < len(lane) and lane[k] else None
    return best[1], best[2]


def scenery_margins(items: list, bands: dict, pts: list, widths: list, grid=None) -> dict:
    """G (scenery, ledger 0049 fix round): every item (a TreeFX trunk or a sign post: {kind, id, x, z, r}) against
    EACH race layout's lane (corridors.<id>.lane_by_vertex) and wall footprints (both curb strips — common — and
    that layout's closure), all lerped at the item's nearest centreline vertex. margin = the clear distance from
    the item's disk (radius r) to the nearest of them; < 0 = the trunk / post stands IN the lane or INSIDE a
    wall. TreeFX trees and sign posts are not physical in AC — nothing else would ever see one there. Items
    farther than half-width + SCENERY_REACH_M from the centreline are not beside the race road (counted, never
    measured). Returns {checked, beside, hits [rows], min {layout: row}}."""
    m = _unique_count(pts)
    grid = grid or VertexGrid(pts[:m])
    bh = float((bands.get("params") or {}).get("barrier_half_m", 0.335))
    cors = _corridors(bands)
    hits, mins, beside = [], {lid: None for lid in cors}, 0
    for it in items:
        x, z, r = float(it["x"]), float(it["z"]), float(it.get("r", 0.0))
        k = grid.nearest(x, z)
        lat = _lateral(pts, m, k, x, z)
        a = abs(lat)
        if a - r > float(widths[k]) / 2.0 + SCENERY_REACH_M:
            continue
        beside += 1
        edge, _centre = strip_footprint(bands, widths, k)
        strip = None
        if edge:
            inner, outer = edge
            strip = ((a - outer) if a >= outer else ((inner - a) if a <= inner else -min(a - inner, outer - a))) - r
        for lid, c in sorted(cors.items()):
            cand = [] if strip is None else [("curb strip", strip)]
            ln = _lane_at(c.get("lane_by_vertex") or [], pts, m, k, x, z)
            if ln is not None:
                cand.append(("lane", max(ln[0] - lat, lat - ln[1]) - r))
            yy = _closure_y_at(c.get("closure_y_by_vertex") or [], pts, m, k, x, z)
            if yy is not None:
                cand.append(("closure", abs(lat - yy) - bh - r))
            if not cand:
                continue
            what, mg = min(cand, key=lambda t: t[1])
            row = {"layout": lid, "kind": it.get("kind"), "id": it.get("id"), "vertex": k, "lat_m": round(lat, 3),
                   "xz": [round(x, 2), round(z, 2)], "against": what, "margin_m": round(mg, 3)}
            if mins[lid] is None or mg < mins[lid]["margin_m"]:
                mins[lid] = row
            if mg < 0.0:
                hits.append(row)
    return {"checked": len(items), "beside": beside, "hits": hits, "min": mins}


def _verify_scenery(items, bands, pts, widths, grid, fails, warns, counts, source=None):
    res = scenery_margins(items, bands, pts, widths, grid)
    bad = sorted(res["hits"], key=lambda r: r["margin_m"])
    for r in bad[:12]:
        where = "in the lane" if r["against"] == "lane" else f"inside the {r['against']}"
        fails.append(f"G: scenery: {r['layout']}: {r['kind']} {r['id']} at v{r['vertex']} lat {r['lat_m']:+.2f} "
                     f"({r['xz'][0]}, {r['xz'][1]}) stands {where} ({-r['margin_m']:.2f} m over) — a non-physical "
                     f"trunk / post on the race road")
    if len(bad) > 12:
        fails.append(f"G: scenery: ... and {len(bad) - 12} more trunks / posts in a lane or a wall")
    if not _corridors(bands):
        warns.append("G: scenery: no corridors declared — no race lane to check against")
    by_kind = {}
    for it in items:
        by_kind[it.get("kind")] = by_kind.get(it.get("kind"), 0) + 1
    counts.update({"scenery_source": source, "scenery_items": by_kind, "scenery_beside": res["beside"],
                   "scenery_hits": len(bad), "scenery_min": res["min"],
                   "scenery_r_m": {"tree": TREE_TRUNK_R_M, "sign": SIGN_POST_R_M}})


# --- H: ring density — the authored strip polyline vs the DECLARED offset curve ---------------------

def declared_curve(bands: dict, pts: list, widths: list | None, side: str, per_vertex: int = DENSE_PER_VERTEX) -> dict:
    """{sample index i = k * per_vertex + j: (x, z, tx, tz)} — the strip-centre curve the declaration
    implies: side 'L' / 'R' = the kerb-line strip at |lat| = half_w + edge_centre_from_lip_m (across a declared
    trimmed corner the polyline in_vertex -> X -> out_vertex); side 'close:<layout id>' = that layout's closure
    at corridors.<id>.closure_y_by_vertex (signed, + = forward-left); sampled over every centreline interval
    [k, k+1] declared at both ends: the centre lerped along the segment, the left normal of the normalised lerp of
    the two vertex tangents (central differences), the lateral lerped. Built from the declaration and the
    centreline only."""
    m = _unique_count(pts)
    corners = []
    if side.startswith("close:"):
        y = (_corridors(bands).get(side[len("close:"):]) or {}).get("closure_y_by_vertex") or []
        flags = [1 if q is not None else 0 for q in y]
        lat_of = lambda k: float(y[k])  # noqa: E731
    else:
        c = _edge_c(bands)
        flags = bands.get("edge_strip_by_vertex") or bands.get("edge_inset_by_vertex") or []
        sgn = 1.0 if side == "L" else -1.0
        lat_of = lambda k: sgn * (float(widths[k]) / 2.0 + c)  # noqa: E731
        corners = [cn for cn in (bands.get("edge_corners") or []) if str(cn.get("side")) == side]

    def tangent(k):
        a, b = pts[(k - 1) % m], pts[(k + 1) % m]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        return tx / L, tz / L
    removed = {int(v) % m for cn in corners for v in cn.get("removed", [])}
    out = {}
    for k in range(min(m, len(flags))):
        k1 = (k + 1) % m
        if not (flags[k] > 0 and k1 < len(flags) and flags[k1] > 0):
            if flags[k] > 0 and not (flags[(k - 1) % m] > 0) and k not in removed:
                t = tangent(k)                    # an isolated run start (a pin): its own sample
                out.setdefault(k * per_vertex, (pts[k][0] - t[1] * lat_of(k), pts[k][2] + t[0] * lat_of(k), t[0], t[1]))
            continue
        if k in removed or k1 in removed:
            continue                      # a trimmed corner's interval: laid below as in -> X -> out
        (t0x, t0z), (t1x, t1z) = tangent(k), tangent(k1)
        la, lb = lat_of(k), lat_of(k1)
        for j in range(per_vertex):
            u = j / per_vertex
            cx = pts[k][0] + (pts[k1][0] - pts[k][0]) * u
            cz = pts[k][2] + (pts[k1][2] - pts[k][2]) * u
            tx, tz = t0x + (t1x - t0x) * u, t0z + (t1z - t0z) * u
            L = math.hypot(tx, tz) or 1.0
            tx, tz = tx / L, tz / L
            lat = la + (lb - la) * u
            out[k * per_vertex + j] = (cx - tz * lat, cz + tx * lat, tx, tz)     # left normal (-tz, tx)
        # the interval's far end (sample k1 * per_vertex) is laid by interval k1, or added here when k1 ends the run
        if not flags[(k1 + 1) % m] > 0:
            t = tangent(k1)
            lat = lat_of(k1)
            out[k1 * per_vertex] = (pts[k1][0] - t[1] * lat, pts[k1][2] + t[0] * lat, t[0], t[1])
    # trimmed corners: the band runs straight from the in_vertex's band point to X and on to the out_vertex's,
    # sampled over the same index range (in * per_vertex .. out * per_vertex), X itself one of the samples
    n_samples = m * per_vertex
    for cn in corners:
        i, j = int(cn["in_vertex"]) % m, int(cn["out_vertex"]) % m
        ti, tj = tangent(i), tangent(j)
        A = (pts[i][0] - ti[1] * lat_of(i), pts[i][2] + ti[0] * lat_of(i))
        B = (pts[j][0] - tj[1] * lat_of(j), pts[j][2] + tj[0] * lat_of(j))
        X = (float(cn["xz"][0]), float(cn["xz"][1]))
        l0, l1 = math.dist(A, X), math.dist(X, B)
        N = ((j - i) % m) * per_vertex
        if N <= 0 or l0 + l1 <= 0:
            continue
        din = ((X[0] - A[0]) / (l0 or 1.0), (X[1] - A[1]) / (l0 or 1.0))
        dout = ((B[0] - X[0]) / (l1 or 1.0), (B[1] - X[1]) / (l1 or 1.0))
        qx = min(N - 1, max(1, round(N * l0 / (l0 + l1))))
        for q in range(N):
            if q < qx:
                f = q / qx
                pt, t = (A[0] + (X[0] - A[0]) * f, A[1] + (X[1] - A[1]) * f), din
            elif q == qx:
                pt, t = X, din            # X closes the in-leg: the step onto it runs along din
            else:
                f = (q - qx) / (N - qx)
                pt, t = (X[0] + (B[0] - X[0]) * f, X[1] + (B[1] - X[1]) * f), dout
            out[(i * per_vertex + q) % n_samples] = (pt[0], pt[1], t[0], t[1])
    return out


class _SampleGrid:
    CELL = 2.0

    def __init__(self, samples):
        self.s = samples
        self.cells: dict[tuple[int, int], list[int]] = {}
        for i, (x, z, _, _) in samples.items():
            self.cells.setdefault((int(math.floor(x / self.CELL)), int(math.floor(z / self.CELL))), []).append(i)

    def nearest(self, x, z, reach=3):
        cx, cz = int(math.floor(x / self.CELL)), int(math.floor(z / self.CELL))
        best, bi = float("inf"), None
        for r in range(1, reach + 1):
            for i in range(cx - r, cx + r + 1):
                for j in range(cz - r, cz + r + 1):
                    for q in self.cells.get((i, j), ()):
                        s = self.s[q]
                        d = (s[0] - x) ** 2 + (s[1] - z) ** 2
                        if d < best:
                            best, bi = d, q
            if bi is not None:
                return bi, math.sqrt(best)
        return None, None


def curve_distance(p, samples: dict, grid: _SampleGrid, n_samples: int):
    """(distance from p to the declared curve's sample polyline near its nearest sample, that sample's index);
    (inf, None) when no sample lies within the grid's reach"""
    i, d = grid.nearest(p[0], p[1])
    if i is None:
        return float("inf"), None
    s = samples[i]
    best = d
    for j in ((i - 1) % n_samples, (i + 1) % n_samples):
        q = samples.get(j)
        if q is not None:
            best = min(best, _seg_dist(p, (s[0], s[1]), (q[0], q[1])))
    return best, i


def span_chords(centres: list, samples: dict, grid: _SampleGrid, n_samples: int, per_vertex: int = DENSE_PER_VERTEX):
    """per consecutive ring pair: ('ok', chord_m, spacing_m, ring index) where the declared curve runs
    forward between them, ('fold', None, spacing, idx) where it folds back (an inside lip tighter than its
    offset — the author chords it on purpose) and ('off', None, spacing, idx) where a ring is off the
    declared curve / the span leaves the declaration"""
    out = []
    params = []
    for c in centres:
        i, d = grid.nearest(c[0], c[2])
        params.append(i if (i is not None and d <= OFF_CURVE_M) else None)
    for idx, (a, b) in enumerate(zip(centres, centres[1:])):
        sp = math.hypot(b[0] - a[0], b[2] - a[2])
        i0, i1 = params[idx], params[idx + 1]
        if i0 is None or i1 is None:
            out.append(("off", None, sp, idx))
            continue
        di = (i1 - i0) % n_samples
        if di > SPAN_MAX_VERTICES * per_vertex:
            out.append(("off", None, sp, idx))
            continue
        pa, pb = (a[0], a[2]), (b[0], b[2])
        worst, kind, prev = 0.0, "ok", samples.get(i0)
        for q in range(1, di + 1):
            s = samples.get((i0 + q) % n_samples)
            if s is None:
                kind = "off"
                break
            if prev is not None and (s[0] - prev[0]) * s[2] + (s[1] - prev[1]) * s[3] <= 0.0:
                kind = "fold"
                break
            prev = s
            if q < di:
                worst = max(worst, _seg_dist((s[0], s[1]), pa, pb))
        out.append((kind, worst if kind == "ok" else None, sp, idx))
    return out


def _curve_side(o):
    """the declared curve an object is judged against: its curb side, or 'close:<layout>' for a closure"""
    if o.get("kind") == "close":
        return f"close:{o.get('layout')}"
    return str(o.get("side"))


def _verify_density(authored, bands, pts, widths, fails, warns, counts):
    """H: every curb-strip / closure span within CHORD_FAIL_M of the declared offset curve"""
    m = _unique_count(pts)
    n_samples = m * DENSE_PER_VERTEX
    objects = authored.get("objects", [])
    rc = authored.get("ring_centres", {})
    curves, grids = {}, {}
    worst = {"chord_m": 0.0}
    sp_all = sp_ok = 0.0
    n_ok = n_fold = n_off = 0
    over = []
    for o in objects:
        if o.get("kind") not in ("edge", "close"):
            continue
        side = _curve_side(o)
        if side not in curves:
            curves[side] = declared_curve(bands, pts, widths, side)
            grids[side] = _SampleGrid(curves[side])
        cs = rc.get(o["name"], [])
        for kind, ch, sp, idx in span_chords(cs, curves[side], grids[side], n_samples):
            sp_all = max(sp_all, sp)
            if kind == "fold":
                n_fold += 1
                continue
            if kind == "off":
                n_off += 1
                continue
            n_ok += 1
            sp_ok = max(sp_ok, sp)
            if ch > worst["chord_m"]:
                worst = {"chord_m": round(ch, 4), "object": o["name"], "ring": idx, "at_xz": [cs[idx][0], cs[idx][2]]}
            if ch > CHORD_FAIL_M:
                over.append((ch, o["name"], idx))
    over.sort(reverse=True)
    if over:
        fails.append(f"H: {len(over)} strip spans chord the declared offset curve by > {CHORD_FAIL_M} m (worst "
                     f"{over[0][0]:.3f} m at {over[0][1]} ring {over[0][2]}) — the rings are too sparse there "
                     f"(race_furniture.densify_rings keeps them within {CHORD_TARGET_M} m)")
    if sp_all > SPACING_TARGET_M + SPACING_ROUND_M:
        warns.append(f"H: ring spacing reaches {sp_all:.2f} m (author target {SPACING_TARGET_M} m)")
    if n_off:
        warns.append(f"H: {n_off} strip spans not measured (a ring > {OFF_CURVE_M} m off the declared curve or the "
                     f"span leaves the declaration) — C' / D judge where the rings stand")
    counts.update({"chord_max_m": worst["chord_m"], "chord_worst": worst, "chord_fail_m": CHORD_FAIL_M,
                   "chord_spans_measured": n_ok, "chord_spans_fold": n_fold, "chord_spans_unmeasured": n_off,
                   "chord_spans_over": len(over), "ring_spacing_max_m": round(sp_all, 3),
                   "ring_spacing_max_measured_m": round(sp_ok, 3)})


def inside_out_spans(centres: list, frames: list, half: float) -> list[int]:
    """span indices i (rings i -> i+1) where one of the two extreme profile columns — the ring centre +-
    half x ls along the ring's left normal (-tz, tx) — moves BACKWARDS (or not at all) along the span's mean
    tangent: the swept solid is inside-out there. The test is affine in the column offset, so the two
    extremes bound every column of the profile. centres: [[x, y, z], ...]; frames: [[tx, tz, ls], ...]."""
    bad = []
    for i in range(min(len(centres), len(frames)) - 1):
        (ax, _, az), (bx, _, bz) = centres[i][:3], centres[i + 1][:3]
        ta, tb = frames[i], frames[i + 1]
        tmx, tmz = ta[0] + tb[0], ta[1] + tb[1]
        for o in (-1.0, 1.0):
            sa, sb = o * half * float(ta[2]), o * half * float(tb[2])
            dx = (bx - tb[1] * sb) - (ax - ta[1] * sa)
            dz = (bz + tb[0] * sb) - (az + ta[0] * sa)
            if dx * tmx + dz * tmz <= 0.0:
                bad.append(i)
                break
    return bad


def _verify_inside_out(authored, bands, fails, warns, counts):
    """I: no span of any curb strip / closure / race kerb is inside-out (ring_centres + ring_frames)"""
    params = bands.get("params", {}) or {}
    bh = float(params.get("barrier_half_m", 0.335))
    kh = float(params.get("kerb_width_m", 1.0)) / 2.0
    rc = authored.get("ring_centres", {}) or {}
    rf_ = authored.get("ring_frames", {}) or {}
    total, per, unmeasured = 0, {}, []
    for o in authored.get("objects", []):
        if o.get("kind") not in ("edge", "close", "kerb", "chain"):
            continue
        cs, fr = rc.get(o["name"], []), rf_.get(o["name"])
        if not fr or len(fr) != len(cs):
            unmeasured.append(o["name"])
            continue
        bad = inside_out_spans(cs, fr, kh if o.get("kind") == "kerb" else bh)
        if bad:
            per[o["name"]] = bad[:12]
            total += len(bad)
    if unmeasured:
        fails.append(f"I: {len(unmeasured)} objects carry no ring_frames matching their ring_centres — inside-out not "
                     f"measurable (re-author with tools/author_race_furniture_blend.py): {unmeasured[:6]}")
    if total:
        worst = sorted(per.items(), key=lambda kv: -len(kv[1]))
        fails.append(f"I: {total} inside-out spans (a profile column runs backwards between two rings): "
                     + "; ".join(f"{n} spans {v}" for n, v in worst[:6]))
    counts.update({"inside_out_spans": total, "inside_out_by_object": per, "inside_out_unmeasured": len(unmeasured)})


# --- A, B, C', D, E, J, K, L, M, N: the authored file vs the declaration ---------------------------

def _end_kinds(o):
    """each end of an object as authored: 'join' / 'pin' / 'free' (from `ends` dicts; a legacy string list + caps
    read the old way: a capless end is a join)"""
    ends = o.get("ends") or []
    caps = list(o.get("caps", [True, True]))
    out = []
    for idx in range(2):
        e = ends[idx] if idx < len(ends) else None
        if isinstance(e, dict):
            out.append(str(e.get("kind")))
        elif isinstance(e, str):
            out.append(e if (idx >= len(caps) or caps[idx]) else "join")
        else:
            out.append("unknown")
    return out


def _verify_authored(authored, bands, pts, island_w, allow_standin, fails, warns, counts, widths=None, lap=None):
    m = _unique_count(pts)
    grid = VertexGrid(pts[:m])
    objects = authored.get("objects", [])
    rc = authored.get("ring_centres", {})
    params = bands.get("params", {})
    bh = float(params.get("barrier_half_m", 0.335))
    cors = _corridors(bands)
    tokens = {lid: _token(bands, lid) for lid in cors}

    # A. provenance
    if authored.get("standin_bands") and not allow_standin:
        fails.append("A: race_authored.json was built from a STAND-IN declaration — author from tools/barrier_bands.py's file")
    if bands.get("_standin") and not allow_standin:
        fails.append("A: barrier_bands.json is a stand-in (_standin) — run tools/barrier_bands.py")
    if str(authored.get("edge_mode")) != str(params.get("edge_mode")):
        fails.append(f"A: edge_mode authored {authored.get('edge_mode')!r} != declared {params.get('edge_mode')!r}")
    ah, bh_ = authored.get("barrier_height_m"), params.get("barrier_height_m")
    if ah is None or bh_ is None or abs(float(ah) - float(bh_)) > 1e-6:
        fails.append(f"A: barrier_height_m authored {ah} != declared {bh_}")
    if tuple(authored.get("race_prefixes", ())) != RACE_PREFIXES:
        fails.append(f"A: race_prefixes {authored.get('race_prefixes')} != {list(RACE_PREFIXES)} (the export split, verify_kn5 and audit --race key on these)")
    if authored.get("failed_runs"):
        fails.append(f"A: runs with no seated ring: {authored['failed_runs']}")
    tot = authored.get("totals", {})
    rings_total = int(tot.get("rings", 0) or 0) + int(tot.get("kerb_stations", 0) or 0)
    interp = int(tot.get("seated_interpolated", 0) or 0)
    if rings_total == 0:
        fails.append("A: no rings authored")
    elif interp / rings_total > INTERP_MAX_FRAC:
        fails.append(f"A: {interp} of {rings_total} rings seated by interpolation ({100 * interp / rings_total:.1f} % > {100 * INTERP_MAX_FRAC:.0f} %)")
    counts["rings_total"] = rings_total
    counts["interpolated"] = interp

    # B. budgets per object
    names = [o["name"] for o in objects]
    if len(names) != len(set(names)):
        fails.append("B: duplicate object names (AC drops dup-named meshes from collision)")
    for o in objects:
        n = o["name"]
        if not n.upper().startswith(RACE_PREFIXES):
            fails.append(f"B: {n}: not RACE-prefixed")
        rings = int(o.get("rings", o.get("stations", 0)) or 0)
        if rings <= 0:
            fails.append(f"B: {n}: no rings/stations")
        if rings > MAX_RINGS:
            fails.append(f"B: {n}: {rings} rings > {MAX_RINGS}")
        if int(o.get("positions", 0)) >= MAX_POSITIONS:
            fails.append(f"B: {n}: {o.get('positions')} positions >= {MAX_POSITIONS}")
        rv = int(o.get("loops", 0)) * 1.5
        if rv >= RENDER_VERT_CAP:
            fails.append(f"B: {n}: {rv:.0f} flat render verts >= {RENDER_VERT_CAP} (the add-on splits into DUP-named meshes)")
        if float(o.get("seat_gap_max_m", 0.0) or 0.0) > SEAT_GAP_M + 1e-9:
            fails.append(f"B: {n}: seating gap {o.get('seat_gap_max_m')} m > {SEAT_GAP_M}")
        if n not in rc or not rc[n]:
            fails.append(f"B: {n}: no ring_centres recorded")
    counts["objects"] = len(objects)

    # N. the retired centre chain
    kbar = sorted({n for n in names + list(rc) if race_kind(n) == "kbar"} |
                  {o["name"] for o in objects if o.get("kind") == "chain"})
    if kbar:
        fails.append(f"N: {len(kbar)} centre-chain objects (1WALL_race_kbar_*, retired by ledger 0049): {kbar[:4]}")
    if any(float(w or 0.0) > 0.0 for w in (bands.get("centre_w_by_vertex") or [])):
        fails.append("N: barrier_bands.json still declares centre_w_by_vertex > 0 (the retired centre chain)")
    if any(str(r.get("kind")) == "centre" for r in (bands.get("runs") or [])):
        fails.append("N: barrier_bands.json still declares a centre run")
    counts["kbar_objects"] = len(kbar)

    # K. ownership: names, owners, layouts, collections
    if not cors:
        fails.append("K: barrier_bands.json declares no corridors.<layout id> — a ledger-0047 (v1) declaration")
    tok_to_lid = {}
    for lid, t in sorted(tokens.items()):
        if not re.match(r"^[a-z0-9]+$", t):
            fails.append(f"K: corridors.{lid}.token {t!r} is not a [a-z0-9]+ name token")
        elif t in tok_to_lid:
            fails.append(f"K: corridors.{lid} and corridors.{tok_to_lid[t]} share the token {t!r}")
        tok_to_lid[t] = lid
    if authored.get("tokens") is not None and dict(authored.get("tokens")) != tokens:
        fails.append(f"K: authored tokens {authored.get('tokens')} != declared {tokens}")
    for o in objects:
        n, kind = o["name"], race_kind(o["name"])
        if kind not in KNOWN_KINDS:
            if kind != "kbar":
                fails.append(f"K: {n}: a RACE object of no known kind (edge / close / kerb) — the export split cannot route it")
            continue
        if kind != o.get("kind"):
            fails.append(f"K: {n}: its name says {kind}, its record says {o.get('kind')}")
        tok = race_owner(n)
        if kind == "close":
            if tok not in tok_to_lid:
                fails.append(f"K: {n}: closure token {tok!r} is not declared (corridors tokens {sorted(tok_to_lid)})")
                continue
            lid = tok_to_lid[tok]
            if o.get("owner") != tok or o.get("layout") != lid:
                fails.append(f"K: {n}: record owner {o.get('owner')!r} / layout {o.get('layout')!r} != {tok!r} / {lid!r}")
            if "collection" in o and o["collection"] != f"{COMMON_COLLECTION}_CLOSE_{tok.upper()}":
                fails.append(f"K: {n}: in collection {o['collection']!r}, not {COMMON_COLLECTION}_CLOSE_{tok.upper()}")
        else:
            if o.get("owner") not in (None, "", "common"):
                fails.append(f"K: {n}: common furniture records an owner {o.get('owner')!r}")
            want_col = common_collection(lap)
            if "collection" in o and o["collection"] != want_col:
                fails.append(f"K: {n}: common furniture in collection {o['collection']!r}, not {want_col}")
            if race_lap(n) != (lap or None):
                # ledger 0054: the export split routes the common set on this field — a mainline strip named for a
                # lap (or a lap's without its token) would ship in the other common kn5
                fails.append(f"K: {n}: its name carries lap {race_lap(n)!r}, this group is "
                             f"{'lap ' + repr(lap) if lap else 'the mainline'}")

    # C'. closures, per race layout
    n_samples = m * DENSE_PER_VERTEX
    close_polys: dict[str, list] = {}
    for lid, c in sorted(cors.items()):
        tok = tokens[lid]
        row = counts["by_layout"].setdefault(lid, {"token": tok})
        objs = [o for o in objects if o.get("kind") == "close" and race_owner(o["name"]) == tok]
        close_polys[lid] = [[(q[0], q[2]) for q in rc.get(o["name"], [])] for o in objs]
        y = c.get("closure_y_by_vertex") or []
        zone = c.get("zone_by_vertex") or []
        bad_zone = [k for k in range(min(m, len(y), len(zone))) if y[k] is not None and str(zone[k]) in ("box", "whole")]
        if bad_zone:
            fails.append(f"C': {lid}: the declaration puts closure vertices in a BOX / WHOLE zone: {bad_zone[:8]}")
        runs = _forward_runs(c, m)
        for i, j, r in runs:
            if r.get("_broken"):
                fails.append(f"C': {lid}: declared run v{r['i']}-v{r['j']} has no closure_y on its walk — broken declaration")
        by_run: dict[tuple, list] = {}
        for o in objs:
            by_run.setdefault((int(o["run"][0]) % m, int(o["run"][1]) % m), []).append(o)
        declared = [(i, j) for i, j, _r in runs]
        for run in declared:
            if run not in by_run:
                fails.append(f"C': {lid}: declared closure run v{run[0]}-v{run[1]} has no closure object")
        for run in by_run:
            if run not in declared:
                fails.append(f"C': {lid}: closure objects for run v{run[0]}-v{run[1]}, which is not declared")
        curve = declared_curve(bands, pts, widths, f"close:{lid}")
        cgrid = _SampleGrid(curve)
        far_side = _closure_side(c)
        far_curve = declared_curve(bands, pts, widths, far_side) if widths is not None else None
        fgrid = _SampleGrid(far_curve) if far_curve is not None else None
        off, worst_off = 0, 0.0
        pin_rows = []
        for run in declared:
            parts = sorted(by_run.get(run, []), key=lambda o: int(o.get("part", 0)))
            for prev, nxt in zip(parts, parts[1:]):
                a, b = rc.get(prev["name"], []), rc.get(nxt["name"], [])
                if a and b and _dist_xz(a[-1], b[0]) > JOIN_TOL_M:
                    fails.append(f"C': {prev['name']} -> {nxt['name']}: parts {_dist_xz(a[-1], b[0]):.2f} m apart (not joined)")
            for o in parts:
                for q in rc.get(o["name"], []):
                    d, _si = curve_distance((q[0], q[2]), curve, cgrid, n_samples)
                    worst_off = max(worst_off, d if d < float("inf") else 99.0)
                    if d > CLOSE_TOL_M + ROUND_M:
                        off += 1
            if not parts:
                continue
            for idx, (o, end_c, v) in enumerate(((parts[0], rc.get(parts[0]["name"], [[0, 0, 0]])[0], run[0]),
                                                 (parts[-1], rc.get(parts[-1]["name"], [[0, 0, 0]])[-1], run[1]))):
                p2 = (end_c[0], end_c[2])
                d_decl = curve_distance(p2, far_curve, fgrid, n_samples)[0] if far_curve is not None else None
                _d, si = curve_distance(p2, curve, cgrid, n_samples)
                kv = (si // DENSE_PER_VERTEX) if si is not None else None
                pin_rows.append({"object": o["name"], "end": "start" if idx == 0 else "end", "vertex": v,
                                 "ring_vertex": kv, "far_line_m": None if d_decl is None else round(d_decl, 3)})
                if d_decl is not None and d_decl > PIN_TOL_M + ROUND_M:
                    fails.append(f"C': {o['name']}: its {'first' if idx == 0 else 'last'} ring is {d_decl:.2f} m off the "
                                 f"declared far curb-strip line ({far_side}) at pin v{v} (> {PIN_TOL_M} m) — not pinned")
                if kv is None or min((kv - v) % m, (v - kv) % m) > VERTEX_TOL:
                    fails.append(f"C': {o['name']}: its {'first' if idx == 0 else 'last'} ring stands at v{kv}, not at "
                                 f"the declared pin v{v}")
        if off:
            fails.append(f"C': {lid}: {off} closure rings stand more than {CLOSE_TOL_M} m off the declared closure line "
                         f"(worst {worst_off:.2f} m)")
        row.update({"closure_objects": len(objs), "closure_runs": len(declared),
                    "closure_rings": sum(len(rc.get(o["name"], [])) for o in objs),
                    "closure_off_curve_max_m": round(worst_off, 3), "pins": pin_rows})

    # D. kerb-line strips: every vertex, both sides (bridges included), except the declared trims
    edge_objs = [o for o in objects if o.get("kind") == "edge"]
    covered: dict[str, set] = {"L": set(), "R": set()}
    edge_gap_worst = 0.0
    for o in edge_objs:
        side = str(o.get("side"))
        cs = rc.get(o["name"], [])
        edge_gap_worst = max(edge_gap_worst, _max_consecutive_gap(cs))
        for c_ in cs:
            covered.setdefault(side, set()).add(grid.nearest(c_[0], c_[2]))
    decl_corners = list(bands.get("edge_corners") or [])
    trimmed: dict[str, set] = {"L": set(), "R": set()}
    for c_ in decl_corners:
        trimmed.setdefault(str(c_.get("side")), set()).update(int(v) % m for v in c_.get("removed", []))
    missing: dict[str, list] = {"L": [], "R": []}
    undeclared: dict[str, list] = {"L": [], "R": []}
    # a ring AT a vertex's declared band point covers it too: inside a tight corner the inside lip's offset
    # (up to 14.5 m) stands nearer to the other leg's vertices than to its own
    by_cell: dict[tuple, list] = {}
    c_lip = _edge_c(bands)
    if widths is not None:
        for o in edge_objs:
            for q in rc.get(o["name"], []):
                by_cell.setdefault((str(o.get("side")), int(math.floor(q[0])), int(math.floor(q[2]))), []).append(q)

    def at_band_point(side, k):
        if widths is None:
            return False
        lx, lz = _left_normal_at(pts, k, m)
        lat = (1.0 if side == "L" else -1.0) * (float(widths[k]) / 2.0 + c_lip)
        bx, bz = pts[k][0] + lx * lat, pts[k][2] + lz * lat
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for q in by_cell.get((side, int(math.floor(bx)) + i, int(math.floor(bz)) + j), ()):
                    if math.hypot(q[0] - bx, q[2] - bz) <= CORNER_TOL_M:
                        return True
        return False
    for side in ("L", "R"):
        cov = covered.get(side, set())
        for k in range(m):
            if not any(((k + d) % m) in cov for d in range(-VERTEX_TOL, VERTEX_TOL + 1)) and not at_band_point(side, k):
                missing[side].append(k)
        undeclared[side] = [k for k in missing[side] if k not in trimmed.get(side, set())]
        if undeclared[side]:
            fails.append(f"D: edge {side}: {len(undeclared[side])} centreline vertices without a ring that no declared "
                         f"edge corner trims (bridge spans included — C1): {undeclared[side][:12]}")
    corner_rows = []
    for c_ in decl_corners:
        side = str(c_.get("side"))
        X = (float(c_["xz"][0]), 0.0, float(c_["xz"][1]))
        near = min((_dist_xz(X, q) for o in edge_objs if str(o.get("side")) == side for q in rc.get(o["name"], [])),
                   default=float("inf"))
        corner_rows.append({"side": side, "in_vertex": c_.get("in_vertex"), "out_vertex": c_.get("out_vertex"),
                            "xz": c_["xz"], "nearest_ring_m": round(near, 3) if near < float("inf") else None})
        if near > CORNER_TOL_M:
            fails.append(f"D: declared edge corner {side} v{c_.get('in_vertex')}->v{c_.get('out_vertex')} at "
                         f"({X[0]:.2f}, {X[2]:.2f}): the nearest authored {side} ring is {near:.2f} m away "
                         f"(> {CORNER_TOL_M} m) — the corner is declared but not built")
    reported = {"L": 0, "R": 0}
    for o in edge_objs:
        reported[str(o.get("side"))] = reported.get(str(o.get("side")), 0) + int(o.get("fold_skipped_run", 0) or 0)
    counts.update({"edge_objects": len(edge_objs), "edge_declared_vertices": m,
                   "edge_missing": {s: len(v) for s, v in missing.items()},
                   "edge_missing_undeclared": {s: len(v) for s, v in undeclared.items()},
                   "edge_trimmed_declared": {s: len(v) for s, v in trimmed.items()},
                   "edge_corners_declared": len(decl_corners), "edge_corners": corner_rows,
                   "edge_fold_dropped": reported,
                   "edge_gap_worst_m": round(edge_gap_worst, 3),
                   "edge_rings": sum(len(rc.get(o["name"], [])) for o in edge_objs)})

    # J. zero free ends: strips join, closures join or pin (re-measured on the ring centres)
    edge_side_polys = {s: [[(q[0], q[2]) for q in rc.get(o["name"], [])] for o in edge_objs if str(o.get("side")) == s]
                       for s in ("L", "R")}
    edge_side_grid = {s: SegGrid(p) for s, p in edge_side_polys.items()}
    free, pin_gap_worst, pins_seen = [], 0.0, 0
    for o in [o for o in objects if o.get("kind") in ("edge", "close")]:
        cs = rc.get(o["name"], [])
        if not cs:
            continue
        kinds = _end_kinds(o)
        ends = o.get("ends") or []
        for idx in range(2):
            kind = kinds[idx]
            pt = cs[0] if idx == 0 else cs[-1]
            where = "start" if idx == 0 else "end"
            if kind == "join":
                met = False
                for q in objects:
                    if q is o or q.get("kind") != o.get("kind") or str(q.get("side")) != str(o.get("side")) \
                            or race_owner(q["name"]) != race_owner(o["name"]):
                        continue
                    qs = rc.get(q["name"], [])
                    if qs and _dist_xz(pt, qs[-1] if idx == 0 else qs[0]) <= JOIN_TOL_M:
                        met = True
                        break
                if not met:
                    fails.append(f"J: {o['name']}: {where} is a `join` but no neighbour of its kind and side meets it — a free end")
            elif kind == "pin" and o.get("kind") == "close":
                pins_seen += 1
                e = ends[idx] if idx < len(ends) and isinstance(ends[idx], dict) else {}
                far = str(e.get("joins") or ("edge_" + _closure_side(cors.get(o.get("layout"), {}))))
                g = edge_side_grid.get(far[-1])
                gap = g.dist((pt[0], pt[2]), reach=3) if g is not None else float("inf")
                pin_gap_worst = max(pin_gap_worst, gap if gap < float("inf") else 99.0)
                if gap > PIN_TOL_M + ROUND_M:
                    fails.append(f"J: {o['name']}: pinned {where} stands {gap:.2f} m off the authored {far} strip "
                                 f"(> {PIN_TOL_M} m) — a gap beside the wall end")
                h, ls = e.get("h"), e.get("ls")
                if h is None or ls is None:
                    fails.append(f"J: {o['name']}: pinned {where} records no h / ls (re-author)")
                elif abs(float(h) - float(params.get("barrier_height_m", 1.2))) > 1e-3 or abs(float(ls) - 1.0) > 1e-3:
                    fails.append(f"J: {o['name']}: pinned {where} is not full height / width (h {h}, ls {ls}) — a "
                                 f"tapered closure end is a ramp past the wall")
            else:
                free.append(f"{o['name']} {where} ({kind})")
    if free:
        fails.append(f"J: {len(free)} free strip / closure ends (every end must join a neighbour or pin a closure on the "
                     f"far curb strip): {free[:6]}")
    counts.update({"free_ends": len(free), "pins": pins_seen, "pin_gap_max_m": round(pin_gap_worst, 3)})

    # L. bridges: the strips seated ON every declared deck, nothing interpolated there
    spans = bands.get("bridge_spans_m") or []
    bs = authored.get("bridge_seating")
    if spans:
        if not isinstance(bs, dict):
            fails.append("L: race_authored.json carries no bridge_seating — not measurable (re-author)")
        else:
            if int(bs.get("interpolated", 0) or 0) > 0:
                fails.append(f"L: {bs['interpolated']} rings inside the declared bridge spans were seated by "
                             f"interpolation — the deck rows under them were not found ({bs.get('by_object')})")
            for row in bs.get("by_span") or []:
                if int(row.get("hit", 0) or 0) + int(row.get("near", 0) or 0) == 0:
                    fails.append(f"L: no strip ring seated on the declared bridge span {row.get('span_m')} — the "
                                 f"curb strips must run over every deck (C1)")
            counts["bridge_seating"] = {k: bs.get(k) for k in ("hit", "near", "interpolated")}

    # E. race kerbs: the declared set with the declared (clipped) i/j, clear of every closure
    kerb_objs = [o for o in objects if o.get("kind") == "kerb"]
    sub_of = {"inside": "in", "outside": "out", "in": "in", "out": "out"}
    decl_k = {(int(k["apex"]), sub_of.get(str(k.get("kind")), str(k.get("kind")))): k for k in bands.get("kerbs", []) or []}
    authored_set = {(int(o["apex"]), str(o.get("sub"))) for o in kerb_objs}
    if set(decl_k) != authored_set:
        fails.append(f"E: declared kerbs {sorted(decl_k)} != authored {sorted(authored_set)}")
    for o in kerb_objs:
        if int(o.get("stations", 0) or 0) <= 0:
            fails.append(f"E: {o['name']}: no stations")
        d = decl_k.get((int(o["apex"]), str(o.get("sub"))))
        if d is not None and [int(d["i"]), int(d["j"])] != [int(v) for v in (o.get("run") or [-1, -1])]:
            fails.append(f"E: {o['name']}: authored run {o.get('run')} != the declared (clipped) v{d['i']}-v{d['j']}")
        clip = o.get("clip") or {}
        if clip.get("stations_removed") and clip["stations_removed"] != [0, 0]:
            warns.append(f"E: {o['name']}: the author clipped {clip['stations_removed']} stations (start, end) for "
                         f"{clip.get('by')} that the declaration's i/j still held — re-run tools/barrier_bands.py so the "
                         f"declared i/j are the clipped ones (race_furniture.kerb_closure_clips)")
    # a kerb under another ROAD sheet (laid across a ribbon fold — invisible from the seat; ledger 0049 fix round):
    # the author measures it on the real deck (race_authored objects[].under_road), the fix is the declaration's
    under, unmeasured = {}, []
    for o in kerb_objs:
        ur = o.get("under_road")
        if not isinstance(ur, dict) or ur.get("unmeasured"):
            unmeasured.append(o["name"])
            continue
        under[o["name"]] = int(ur.get("stations", 0) or 0)
        if under[o["name"]] > 0:
            fails.append(f"E: {o['name']}: {under[o['name']]} stations sit UNDER another ROAD sheet (up to "
                         f"{ur.get('max_m')} m over the kerb's top, at v{ur.get('vertices')}) — a kerb laid across a "
                         f"ribbon fold; pull its run back or drop it (track.config.json race.kerbs.trims)")
    if unmeasured:
        warns.append(f"E: {len(unmeasured)} kerbs carry no under_road measure (an author run before the 0049 fix "
                     f"round) — kerb-under-a-road-sheet not checked: {unmeasured[:4]}")
    dropped = bands.get("kerbs_dropped") or []
    for d in dropped:
        if (int(d.get("apex", -1)), sub_of.get(str(d.get("kind")), str(d.get("kind")))) in authored_set:
            fails.append(f"E: the {d.get('kind')} kerb at v{d.get('apex')} is declared DROPPED but was authored")
    if authored.get("kerbs_declared_unmatched"):
        fails.append(f"E: declared kerbs matching no detected corner: {authored['kerbs_declared_unmatched']}")
    n_corners_decl = len(bands.get("corners", []) or [])
    n_corners_auth = len(authored.get("corners", []) or [])
    if n_corners_decl and n_corners_auth != n_corners_decl:
        fails.append(f"E: {n_corners_auth} corners authored vs {n_corners_decl} declared")
    frames = authored.get("ring_frames", {}) or {}
    kw = float(params.get("kerb_width_m", 1.0))
    kerb_clear = {}
    for lid, polys in close_polys.items():
        sg = SegGrid(polys)
        for o in kerb_objs:
            cs, fr = rc.get(o["name"], []), frames.get(o["name"], [])
            worst = float("inf")
            for c_, f_ in zip(cs, fr):
                lx, lz = -f_[1], f_[0]
                h = kw / 2.0 * float(f_[2])
                a, b = (c_[0] - lx * h, c_[2] - lz * h), (c_[0] + lx * h, c_[2] + lz * h)
                for p, q in sg.near(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), reach=2):
                    worst = min(worst, _seg_seg_dist(a, b, p, q) - bh)
            prev = kerb_clear.get(o["name"])
            if prev is None or worst < prev[0]:
                kerb_clear[o["name"]] = (worst, lid)
    for name, (w, lid) in sorted(kerb_clear.items()):
        if w < KERB_CLEAR_M - ROUND_M:
            fails.append(f"E: {name}: stands {w:.2f} m off {lid}'s authored closure (< {KERB_CLEAR_M} m) — a kerb under a wall")
    counts.update({"kerb_objects": len(kerb_objs), "corners": n_corners_auth,
                   "kerbs_dropped": [[d.get("apex"), d.get("kind")] for d in dropped],
                   "kerb_under_road": under,
                   "kerb_fold_dropped": sum(int(o.get("fold_skipped", 0) or 0) for o in kerb_objs),
                   "kerb_closure_clear_m": {n: (round(w, 3) if w < float("inf") else None, lid) for n, (w, lid) in kerb_clear.items()},
                   "kerb_clips": {o["name"]: (o.get("clip") or {}).get("stations_removed") for o in kerb_objs}})

    # M. mouths: every sealed mouth line ON its side's strip; behind_closure mouths behind that layout's closure
    mouth_rows = []
    cm = {(int(mo["host_vertex"]), str(mo["side"])): mo for mo in (bands.get("closed_mouths") or [])}
    for (host, side), mo in sorted(cm.items()):
        poly = mo.get("polyline_xyz_m") or []
        g = edge_side_grid.get(side)
        worst = max((g.dist((p[0], p[2]), reach=3) for p in poly), default=None) if g is not None else None
        mouth_rows.append({"host_vertex": host, "side": side, "strip_off_m": None if worst is None else round(worst, 3)})
        if worst is None or worst > MOUTH_TOL_M + ROUND_M:
            fails.append(f"M: mouth {mo.get('connector')} at v{host} ({side}): the sealing {side} strip stands "
                         f"{'nowhere near' if worst is None else f'{worst:.2f} m off'} the mouth line — the mouth is open")
    for lid, c in sorted(cors.items()):
        pol = c.get("mouths")
        if pol is None:
            warns.append(f"M: corridors.{lid} declares no mouth policies — only the strips' seal was checked")
            continue
        listed = {(int(x["host_vertex"]), str(x["side"])) for x in pol}
        for key in cm:
            if key not in listed:
                fails.append(f"M: {lid}: mouth at v{key[0]} ({key[1]}) has no declared policy")
        y = c.get("closure_y_by_vertex") or []
        lane = c.get("lane_by_vertex") or []
        polys = close_polys.get(lid, [])
        sg = SegGrid(polys)
        for x in pol:
            host, side, policy = int(x["host_vertex"]), str(x["side"]), str(x.get("policy"))
            if policy in ("sealed_race_strip", "sealed_far_strip"):
                continue                      # sealed by a curb strip: the strip check above holds for every mouth
            if policy != "behind_closure":
                fails.append(f"M: {lid}: mouth v{host} ({side}): unknown policy {policy!r}")
                continue
            mo = cm.get((host, side)) or {}
            vf, vt = int(mo.get("vertex_from", host - 2)), int(mo.get("vertex_to", host + 2))
            for k in _walk(vf % m, vt % m, m):
                yy = y[k] if k < len(y) else None
                if yy is None:
                    fails.append(f"M: {lid}: mouth v{host} ({side}) is declared behind the closure, but no closure is "
                                 f"declared at v{k}")
                    break
                lx, lz = _left_normal_at(pts, k, m)
                d = sg.dist((pts[k][0] + lx * yy, pts[k][2] + lz * yy), reach=2)
                if d > CLOSE_TOL_M + ROUND_M:
                    fails.append(f"M: {lid}: mouth v{host} ({side}): the authored closure is {d:.2f} m off its line at v{k}")
                    break
                lo_hi = lane[k] if k < len(lane) else None
                if lo_hi and ((side == "L" and float(lo_hi[1]) > yy - bh + 1e-3) or
                              (side == "R" and float(lo_hi[0]) < yy + bh - 1e-3)):
                    fails.append(f"M: {lid}: mouth v{host} ({side}): the lane {lo_hi} reaches past the closure at v{k} — "
                                 f"the mouth is not behind it")
                    break
    counts["mouths"] = mouth_rows

    # F. spawn clearance — the AUTHOR's record (author time); the HARD re-measure of the dummies that
    #    actually ship is _verify_spawns (from data/dummies_<id>.json), run by verify() for every call
    sc = authored.get("spawn_clearance", {}) or {}
    for lid, r in sc.items():
        if r.get("synthesised"):
            fails.append(f"F: {lid}: spawn clearance measured on SYNTHESISED dummies — run tools/layout_dummies.py first")
        if r.get("hard"):
            fails.append(f"F: {lid}: a spawn overlaps a strip / its lane or stands < {SPAWN_MARGIN_M:.2f} m off it "
                         f"(author-time record): {r['hard'][:4]}")
        for note in r.get("notes", []) or []:
            warns.append(f"F: {lid}: author-time: {note}")
    if not sc:
        warns.append("F: no spawn_clearance recorded (no dummies_<id>.json at authoring time)")

    # O. another deck over the strip (2026-10-11: HARD, was a warning). The author lists every ring where another
    #    ROAD sheet — a connector's mouth, or the ribbon's own fold — stands more than its threshold over the strip
    #    base. The Del Cerro W mouth stood +0.51 m over College 2.33 m past the race_acw lane face while this only
    #    warned; a mouth / fold defect is the ribbon owner's to fix, and the race layout is never shipped over it.
    oda = authored.get("other_deck_above", []) or []
    n_oda = int(tot.get("other_deck_above_rings", len(oda)) or 0)
    thr = tot.get("other_deck_threshold_m")
    if thr is None or float(thr) > OTHER_DECK_FAIL_M + 1e-9:
        fails.append(f"O: the author measured 'another deck above the strip' at {thr!r} m, looser than the gate's "
                     f"{OTHER_DECK_FAIL_M} m — re-run tools/author_race_furniture_blend.py")
    if n_oda or oda:
        fails.append(f"O: {max(n_oda, len(oda))} rings have another ROAD sheet > {OTHER_DECK_FAIL_M} m above the strip "
                     f"base (max {tot.get('other_deck_above_max_m')} m) — a mouth / fold defect for the ribbon's owner, "
                     f"e.g. {oda[:3]}")
    counts["other_deck_above"] = max(n_oda, len(oda))
    if tot.get("deck_vs_data_max_m") is not None:
        warns.append(f"built deck vs data height, worst {tot.get('deck_vs_data_max_m')} m")


def race_layout_spawns(data: Path, cfg: dict | None, exclude=()) -> dict:
    """{race layout id: its data/dummies_<id>.json dict, or None when the file is missing}. A race layout
    is one the config marks race_furniture: true OR whose dummies file says `_kind: race` (so a workshop
    whose own track.config.json predates the layouts is still judged on the dummies it holds). ``exclude``: the
    race layouts of OTHER lap groups (ledger 0054) — their spawns are judged against their own lap's lane."""
    ids = {str(lo["id"]) for lo in ((cfg or {}).get("layouts") or []) if isinstance(lo, dict) and lo.get("race_furniture")}
    found = {}
    for f in sorted(data.glob("dummies_*.json")):
        lid = f.stem[len("dummies_"):]
        if lid in exclude:
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if lid in ids or d.get("_kind") == "race":
            found[lid] = d
    return {lid: found.get(lid) for lid in sorted(ids | set(found))}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("usage: python tools/verify_race.py <project-dir> [--allow-standin] [--authored <file>] [--bands <file>] "
                         "[--config <track.config.json>] [--pre-author | --scenery-only] [--trees <trees.txt>] [--out <file>] [--lap <id>]")
    allow_standin = pre_author = scenery_only = False
    authored_p = bands_p = config_p = out_p = trees_p = None
    lap = None
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--allow-standin":
            allow_standin = True; i += 1
        elif a == "--pre-author":
            pre_author = True; i += 1
        elif a == "--scenery-only":
            scenery_only = True; i += 1
        elif a == "--trees":
            trees_p = Path(argv[i + 1]); i += 2
        elif a == "--authored":
            authored_p = Path(argv[i + 1]); i += 2
        elif a == "--bands":
            bands_p = Path(argv[i + 1]); i += 2
        elif a == "--config":
            config_p = Path(argv[i + 1]); i += 2
        elif a == "--out":
            out_p = Path(argv[i + 1]); i += 2
        elif a == "--lap":
            lap = argv[i + 1]; i += 2
        else:
            rest.append(a); i += 1
    proj = Path(rest[0]).resolve()
    data = proj / "data"
    # ledger 0054: --lap <id> judges one LAP group — its line (data/lap.<id>.json), its declaration
    # (barrier_bands.<id>.json), its authored set (race_authored.<id>.json) and its layouts; every report name
    # carries the lap. Without --lap: the mainline group, exactly as before.
    sfx = f".{lap}" if lap else ""
    authored_p = authored_p or data / f"race_authored{sfx}.json"
    bands_p = bands_p or data / f"barrier_bands{sfx}.json"
    config_p = config_p or proj / "track.config.json"
    if scenery_only:
        pre_author = True                                             # no authored file needed; F and lamp G are skipped below
    out_p = out_p or data / (f"race_verify.scenery{sfx}.json" if scenery_only else
                             f"race_verify.pre{sfx}.json" if pre_author else f"race_verify{sfx}.json")   # a partial run never overwrites the full report
    line_files = [data / f"lap.{lap}.json"] if lap else [data / "centerline.local.json", data / "median_bands.json"]
    need = [bands_p] + line_files + ([trees_p] if trees_p else [])
    if not pre_author:
        need.insert(0, authored_p)
    for p in need:
        if not p.exists():
            raise SystemExit(f"[verify-race] missing {p}")
    authored = None if pre_author else json.loads(authored_p.read_text(encoding="utf-8"))
    bands = json.loads(bands_p.read_text(encoding="utf-8"))
    if lap:
        cl = json.loads((data / f"lap.{lap}.json").read_text(encoding="utf-8"))
        pts = [tuple(p) for p in cl["points_xyz_m"]]
        widths = [float(w) for w in cl["widths_m"]]
        island_w = [float(w) for w in cl["island_w_by_vertex"]]
    else:
        cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
        pts = [tuple(p) for p in cl["points_xyz_m"]]
        widths = [float(w) for w in cl["widths_m"]]
        island_w = json.loads((data / "median_bands.json").read_text(encoding="utf-8"))["island_w_by_vertex"]
    if len(island_w) != len(pts) or len(widths) != len(pts):
        raise SystemExit(f"[verify-race] median_bands {len(island_w)} / widths {len(widths)} vs centreline {len(pts)} vertices")
    cfg = json.loads(config_p.read_text(encoding="utf-8")) if config_p.exists() else None
    # the race layouts of every OTHER group (another lap, or the mainline when judging a lap) are not this group's
    others = {str(lo.get("id")) for lo in ((cfg or {}).get("layouts") or [])
              if isinstance(lo, dict) and lo.get("race_furniture") and (lo.get("lap") or None) != (lap or None)}
    view = dict(cfg, layouts=[lo for lo in (cfg.get("layouts") or []) if str(lo.get("id")) not in others]) \
        if (cfg and others) else cfg
    spawns = None if scenery_only else race_layout_spawns(data, view, exclude=others)
    lp = data / "lights.local.json"
    lamps = json.loads(lp.read_text(encoding="utf-8")).get("lampheads", []) if (lp.exists() and not scenery_only) else None
    # G scenery: the TreeFX trunks (the WRITTEN trees.txt with --trees, else make_treefx's own plan of it) and the
    # W1-6 sign posts, against every race layout's lane and walls
    scenery, src_note = [], []
    if trees_p:
        scenery += tree_items_from_txt(trees_p.read_text(encoding="utf-8"))
        src_note.append(f"trees: {trees_p.name} (written)")
    elif (data / "scatter_positions.json").exists():
        scenery += tree_items_planned(proj)
        src_note.append("trees: tools/make_treefx.py plan (every species)")
    else:
        src_note.append("trees: none (no data/scatter_positions.json)")
    sgp = data / "signs.local.json"
    if sgp.exists():
        scenery += sign_items(json.loads(sgp.read_text(encoding="utf-8")))
        src_note.append("signs: data/signs.local.json")
    r = verify(authored, bands, pts, island_w, allow_standin=allow_standin, widths=widths, spawns=spawns,
               lamps=lamps, pre_author=pre_author, scenery=scenery, scenery_source="; ".join(src_note), lap=lap)
    if lamps is None and not scenery_only:
        r["warnings"].append("G: no data/lights.local.json — no lamps authored, nothing to check")
    c = r["counts"]
    if not pre_author:
        print(f"[verify-race] {c.get('objects')} objects. COMMON: curb strips {c.get('edge_objects')} objects / "
              f"{c.get('edge_rings')} rings on all {c.get('edge_declared_vertices')} vertices x 2 sides (missing "
              f"{c.get('edge_missing')}, declared trimmed {c.get('edge_trimmed_declared')} at {c.get('edge_corners_declared')} "
              f"corners, missing undeclared {c.get('edge_missing_undeclared')}, worst gap {c.get('edge_gap_worst_m')} m); "
              f"kerbs {c.get('kerb_objects')} at {c.get('corners')} corners; free ends {c.get('free_ends')}; interpolated "
              f"{c.get('interpolated')}/{c.get('rings_total')}; bridge seating {c.get('bridge_seating')}")
        for lid, row in sorted((c.get("by_layout") or {}).items()):
            print(f"[verify-race] {lid} (token {row.get('token')}): closure {row.get('closure_objects')} objects / "
                  f"{row.get('closure_runs')} runs / {row.get('closure_rings')} rings, off the declared line max "
                  f"{row.get('closure_off_curve_max_m')} m; pins vs the far strip line "
                  f"{[p['far_line_m'] for p in row.get('pins', [])]}")
        print(f"[verify-race] J pins {c.get('pins')} (gap to the authored far strip max {c.get('pin_gap_max_m')} m); "
              f"E kerb clearance to the closures {c.get('kerb_closure_clear_m')}")
    if not pre_author and "chord_max_m" in c:
        cw = c.get("chord_worst") or {}
        where = f" at {cw['object']} ring {cw['ring']}" if cw.get("object") else ""
        print(f"[verify-race] H density: {c['chord_spans_measured']} spans vs the declared offset curve, chord max "
              f"{c['chord_max_m']} m{where} (FAIL > {CHORD_FAIL_M} m, {c['chord_spans_over']} over); ring spacing max "
              f"{c['ring_spacing_max_m']} m (measured spans {c['ring_spacing_max_measured_m']} m); "
              f"{c['chord_spans_fold']} fold spans, {c['chord_spans_unmeasured']} unmeasured")
    if not pre_author and "inside_out_spans" in c:
        print(f"[verify-race] I inside-out: {c['inside_out_spans']} spans over every strip / closure / kerb object "
              f"({c['inside_out_unmeasured']} objects unmeasured)")
    for lid, rows in (c.get("spawn_slots") or {}).items():
        cells = ", ".join(f"{q['name'].replace('AC_', '')} {q['clear_edge_m']:+.2f}"
                          + (f"/lane{q['clear_lane_m']:+.2f}" if q.get("clear_lane_m") is not None else "") for q in rows)
        print(f"[verify-race] F {lid}: min clearance {c['spawn_min_clear_m'].get(lid)} m (hard floor {SPAWN_MARGIN_M} m): {cells}")
    lm = c.get("lamp_min")
    if lm is not None:
        lc = c.get("lamp_min_vs_closure")
        print(f"[verify-race] G lamps: {c.get('lamps_checked')}/{c.get('lamps')} masts beside a strip (arm {c.get('lamp_arm_m')} m, "
              f"mast r {c.get('mast_r_m')} m); minimum margin {c.get('lamp_min_margin_m')} m at lamp {lm['lamp']} v{lm['vertex']} "
              f"lat {lm['lat_m']:+.2f} vs the {lm['against']} strip; {c.get('lamps_inside')} inside"
              + (f"; nearest to a closure {lc['closure_margin_m']} m (lamp {lc['lamp']} v{lc['vertex']}, {lc['closure']})" if lc else ""))
    if "scenery_beside" in c:
        mins = c.get("scenery_min") or {}
        print(f"[verify-race] G scenery ({c.get('scenery_source')}): {c.get('scenery_items')} items, {c.get('scenery_beside')} "
              f"beside the race road; {c.get('scenery_hits')} in a lane or a wall (trunk r {TREE_TRUNK_R_M} m, post r "
              f"{SIGN_POST_R_M} m); nearest per layout: "
              + ", ".join(f"{lid} {row['margin_m']} m ({row['kind']} {row['id']} v{row['vertex']} vs the {row['against']})"
                          for lid, row in sorted(mins.items()) if row))
    for w in r["warnings"]:
        print(f"[verify-race] note: {w}")
    for f in r["fails"]:
        print(f"[verify-race] FAIL {f}")
    out_p.write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(f"[verify-race] {'OK' if r['ok'] else 'FAILED'}"
          f"{' (scenery only: G trunks + posts)' if scenery_only else ' (pre-author: F + G only)' if pre_author else ''} -> {out_p}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
