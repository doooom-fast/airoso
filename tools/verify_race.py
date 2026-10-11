"""Verify the authored race furniture against its declaration — a ship gate (ledger 0047).

Runs after tools/author_race_furniture_blend.py, pure Python, exit 1 on any miss. Reads
data/race_authored.json (the author tool's per-object counts, seating and the SEATED ring centres)
and data/barrier_bands.json (tools/barrier_bands.py — the declared bands the gates consult), plus
data/centerline.local.json and data/median_bands.json. The declaration IS the authored line
(the 2026-10-08 median_zone precedent); this file proves the two agree BEFORE a kn5 exists, and
drive_test's ``barrier_missing`` then proves the strips are in the BUILT OBJ (L5).

  A  provenance — the authored file was built from this declaration: not a stand-in, same
     edge_mode and barrier height as the bands, the RACE prefixes the export split keys on; no run
     failed to seat; interpolated rings <= 1 %
  B  budgets — every object stays ONE AC mesh: rings <= 900 (the author tool's own cap is 800),
     positions < 60,000, flat-shaded render verts (loops x 1.5) < 65,535, a unique RACE-prefixed
     name, seating gap <= 0.05 m
  C  centre chain — at least one object per declared centre run; every chain ring stands on a
     vertex the band declares (centre_w > 0), never on a median island beyond the shared nose
     vertex, never on Alvarado or inside the hairpin arc; the run's first / last ring within
     END_TOL_M of the declared end vertices; consecutive PARTS of a run share their boundary ring
  D  kerb-line strips — every declared edge vertex has a ring on each side, except the
     fold-dropped rings the author reports (the inside lip of the five right-handers); no ring
     stands inside a declared gap (the three bridge spans); every `join` end meets the neighbouring
     object's end (JOIN_TOL_M) and every `free` end stands at a declared gap edge — a free end in
     the middle of a declared stretch is a hole in the wall
  A swept strip is continuous between ANY two consecutive rings (the mesh spans them), so ring
  spacing is reported, not gated: on the outside lip of a 10 m corner the 3 m centreline spacing
  stretches to 5-7 m and the strip chords up to ~0.4 m inside the arc (noted for the author tool).
  E  race kerbs — the declared (apex, in|out) set == the authored set, every kerb has stations,
     nothing declared-but-unmatched, as many corners as the declaration
  F  spawn clearance — HARD (2026-10-11): every grid / pit / hotlap slot of every race layout, re-measured
     HERE from data/dummies_<id>.json (what build_spawn_kn5 ships) against the declared strip faces
     (bands params: face = half_w + edge_centre_from_lip_m -/+ barrier_half_m; chain = centre_w / 2):
     a 1.9 m car stands >= SPAWN_MARGIN_M = 0.30 m off every face, else FAIL (it was a soft note at
     0.08 m with the 1.4 m stagger). The author tool's own record still fails on its `hard` list and on
     synthesised dummies. Every slot's clearance lands in race_verify.json counts.spawn_slots.
  G  lamp posts vs the strips — every lamp mast (data/lights.local.json heads set back road-ward by
     tools/author_lamps_blend.py's ARM_M, the footprint radius measured from assets/models/lamp_post.obj
     at its POST_H scale) stands OUTSIDE every kerb-line strip and centre-chain footprint; FAIL on any
     overlap, the minimum margin reported (counts.lamp_min_margin_m). Q6 `walk` puts the strip on the
     sidewalk top, where the masts are — this is the check that would catch it.

Reported, never gated: another ROAD sheet above a strip base (a fold / mouth defect for its owner,
0033/0046 class), the worst deck-vs-data height, the minimum spawn clearance.

    python tools/verify_race.py <project-dir> [--allow-standin] [--authored <file>] [--bands <file>]
                                [--config <track.config.json>] [--pre-author] [--out <file>]

--pre-author runs F (disk) and G only — no data/race_authored.json needed, so it can judge a
workshop's dummies and lamps before (or without) the Blender author step; it writes
data/race_verify.pre.json, never the full report's file. --config reads another
config for the race-layout ids (a dummies file's own `_kind: race` also counts). Writes
data/race_verify.json (or --out). Plain functions so tests/run_tests.py can drive it without Blender.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
RACE_PREFIXES = ("1WALL_RACE", "1KERB_RACE")
MAX_RINGS = 900
MAX_POSITIONS = 60_000
RENDER_VERT_CAP = 65_535
SEAT_GAP_M = 0.05
INTERP_MAX_FRAC = 0.01
JOIN_TOL_M = 0.05       # a `join` end and its neighbour's end are the SAME ring (split_plan shares boundary rings)
END_TOL_M = 1.5         # a run's first/last ring vs the declared end vertex (the ring sits ON the vertex)
VERTEX_TOL = 1          # edge rings sit ~6 m off the centreline: on a tight curve the nearest vertex may be k+-1
FREE_END_VERTEX_TOL = 3 # a `free` edge end must stand within this many vertices of a declared gap vertex
SPACING_NOTE_M = 6.0    # ring spacing above this is reported (the strip chords the arc), never gated
CAR_HALF_W_M = 0.95     # a 1.9 m car on a grid / pit slot
SPAWN_MARGIN_M = 0.30   # F: HARD floor between a slot's car and any strip face (GATES-CHANGELOG 2026-10-11)
FACING = ("AC_START", "AC_PIT", "AC_HOTLAP")   # the slots a car sits on (AC_TIME_* are timing planes)
LAMP_ARM_FALLBACK_M = 1.8      # author_lamps_blend.ARM_M when its source cannot be read
LAMP_POST_H_FALLBACK_M = 11.5  # author_lamps_blend.POST_H
MAST_R_FALLBACK_M = 0.60       # lamp_post.obj base plate corner radius at 11.5 m (measured 0.585 m)
LAMP_CELL_M = 30.0             # author_lamps_blend's nearest-centreline cell (its fallback is vertex 0)


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


def _dist_xz(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def _max_consecutive_gap(centres):
    worst = 0.0
    for a, b in zip(centres, centres[1:]):
        worst = max(worst, _dist_xz(a, b))
    return worst


def _unique_count(pts):
    return len(pts) - 1 if len(pts) > 1 and _dist_xz(pts[0], pts[-1]) < 1e-6 else len(pts)


# --- the checks ----------------------------------------------------------------------------------

def verify(authored: dict | None, bands: dict, pts: list, island_w: list, *, allow_standin: bool = False,
           widths: list | None = None, spawns: dict | None = None, lamps: list | None = None,
           pre_author: bool = False, lamp_arm_m: float | None = None, mast_r_m: float | None = None) -> dict:
    """A-E (+ the author's own F record) on the authored file unless ``pre_author``; F re-measured from
    ``spawns`` ({race layout id: dummies dict, or None when its file is missing}) and G from ``lamps``
    (lights.local.json heads) whenever they and ``widths`` are given (main always gives them)."""
    fails: list[str] = []
    warns: list[str] = []
    counts: dict = {}
    if not pre_author:
        _verify_authored(authored or {}, bands, pts, island_w, allow_standin, fails, warns, counts)
    m = _unique_count(pts)
    grid = VertexGrid(pts[:m])
    if spawns is not None and widths is not None:
        _verify_spawns(spawns, bands, pts, widths, grid, fails, warns, counts)
    if lamps is not None and widths is not None:
        _verify_lamps(lamps, bands, pts, widths, grid, fails, warns, counts, lamp_arm_m, mast_r_m)
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


def strip_footprint(bands: dict, widths: list, k: int):
    """(edge, centre_half) at vertex k from the declaration alone: edge = (inner, outer) |lateral| of the
    kerb-line strip (both curb faces) where edge_strip_by_vertex > 0, else None — inner = the road-side
    face = half_w + edge_centre_from_lip_m - barrier_half_m (road mode: half_w - 0.82; walk: half_w + 0.11);
    centre_half = centre_w / 2 where the chain stands, else None."""
    params = bands.get("params", {}) or {}
    bh = float(params.get("barrier_half_m", 0.335))
    c = params.get("edge_centre_from_lip_m")
    c = float(c) if c is not None else (-0.485 if str(params.get("edge_mode", "road")) == "road" else 0.445)
    es = bands.get("edge_strip_by_vertex") or bands.get("edge_inset_by_vertex") or []
    cw = bands.get("centre_w_by_vertex") or []
    half = float(widths[k]) / 2.0
    edge = (half + c - bh, half + c + bh) if (k < len(es) and es[k] > 0) else None
    centre = float(cw[k]) / 2.0 if (k < len(cw) and cw[k] > 0) else None
    return edge, centre


def spawn_slots(dummies: dict, pts: list, widths: list, bands: dict, grid=None) -> list[dict]:
    """every FACING slot's car clearance to the edge-strip face and (where it stands) the centre chain"""
    m = _unique_count(pts)
    grid = grid or VertexGrid(pts[:m])
    rows = []
    for name, p in sorted(dummies.items()):
        if name.startswith("_") or not name.startswith(FACING) or not isinstance(p, (list, tuple)) or len(p) < 3:
            continue
        x, z = float(p[0]), float(p[2])
        k = grid.nearest(x, z)
        lat = _lateral(pts, m, k, x, z)
        edge, centre = strip_footprint(bands, widths, k)
        a = abs(lat)
        rows.append({"name": name, "vertex": k, "lat_m": round(lat, 3),
                     "edge_face_m": round(edge[0], 3) if edge else None,
                     "clear_edge_m": round(edge[0] - (a + CAR_HALF_W_M), 3) if edge else None,
                     "clear_centre_m": round(a - CAR_HALF_W_M - centre, 3) if centre is not None else None})
    return rows


def _verify_spawns(spawns, bands, pts, widths, grid, fails, warns, counts):
    mins, slots = {}, {}
    for lid, d in sorted(spawns.items()):
        if d is None:
            fails.append(f"F: {lid}: no data/dummies_{lid}.json — run tools/layout_dummies.py (the spawn kn5 is built from it)")
            continue
        if d.get("_synthesised"):
            fails.append(f"F: {lid}: dummies_{lid}.json is SYNTHESISED — run tools/layout_dummies.py first")
        rows = spawn_slots(d, pts, widths, bands, grid)
        if not rows:
            fails.append(f"F: {lid}: dummies_{lid}.json holds no grid / pit slot")
            continue
        for r in rows:
            for key, what in (("clear_edge_m", "edge-strip face"), ("clear_centre_m", "centre chain")):
                v = r[key]
                if v is not None and v < SPAWN_MARGIN_M:
                    fails.append(f"F: {lid}: {r['name']} at v{r['vertex']} lat {r['lat_m']:+.2f}: {v:.2f} m clear of the "
                                 f"{what} (< {SPAWN_MARGIN_M:.2f} m{'; the car OVERLAPS it' if v < 0 else ''})")
        vals = [r[k] for r in rows for k in ("clear_edge_m", "clear_centre_m") if r[k] is not None]
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


def lamp_margins(bases: list, pts: list, widths: list, bands: dict, mast_r: float, grid=None) -> list[dict]:
    """per mast: the clearance from its base footprint (radius mast_r) to the nearest strip footprint at
    its nearest vertex; negative = the mast stands IN the strip. Masts at a vertex with no strip (the
    bridge gaps) are not listed."""
    m = _unique_count(pts)
    grid = grid or VertexGrid(pts[:m])
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
        if not cand:
            continue
        kind, mg = min(cand, key=lambda t: t[1])
        rows.append({"lamp": i, "vertex": k, "lat_m": round(lat, 3), "base_xz": [round(b["x"], 2), round(b["z"], 2)],
                     "against": kind, "margin_m": round(mg, 3), "fallback": b["fallback"]})
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
    counts.update({"lamps": len(bases), "lamps_checked": len(rows), "lamp_arm_m": arm, "lamp_post_h_m": post_h,
                   "mast_r_m": round(r_m, 3), "lamp_min_margin_m": worst["margin_m"] if worst else None,
                   "lamp_min": worst, "lamps_inside": len(bad)})


def _verify_authored(authored, bands, pts, island_w, allow_standin, fails, warns, counts):
    m = _unique_count(pts)
    grid = VertexGrid(pts[:m])
    objects = authored.get("objects", [])
    rc = authored.get("ring_centres", {})
    params = bands.get("params", {})

    # A. provenance
    if authored.get("standin_bands") and not allow_standin:
        fails.append("A: race_authored.json was built from STAND-IN bands (--standin-bands) — author from tools/barrier_bands.py's file")
    if bands.get("_standin") and not allow_standin:
        fails.append("A: barrier_bands.json is a stand-in (_standin) — run tools/barrier_bands.py")
    if str(authored.get("edge_mode")) != str(params.get("edge_mode")):
        fails.append(f"A: edge_mode authored {authored.get('edge_mode')!r} != declared {params.get('edge_mode')!r}")
    ah, bh = authored.get("barrier_height_m"), params.get("barrier_height_m")
    if ah is None or bh is None or abs(float(ah) - float(bh)) > 1e-6:
        fails.append(f"A: barrier_height_m authored {ah} != declared {bh}")
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

    # C. centre chain
    cw = bands.get("centre_w_by_vertex") or []
    noses = set(int(v) for v in (bands.get("summary", {}) or {}).get("nose_vertices", []))
    alv_to = -1
    for st in bands.get("streets", []) or []:
        if str(st.get("street", "")).lower().startswith("alvarado"):
            alv_to = int(st.get("vertex_to", -1))
    hairpin = set()
    for c in bands.get("corners", []) or []:
        if abs(float(c.get("D_deg", 0.0))) >= 135.0:
            pc, pt = int(c["PC"]), int(c["PT"])
            hairpin |= set(range(pc, pt + 1)) if pt >= pc else set(range(pc, m)) | set(range(0, pt + 1))
    centre_runs = [(int(r["i"]), int(r["j"])) for r in bands.get("runs", []) if r.get("kind") == "centre"]
    chain_objs = [o for o in objects if o.get("kind") == "chain"]
    by_run: dict[tuple[int, int], list] = {}
    for o in chain_objs:
        by_run.setdefault((int(o["run"][0]), int(o["run"][1])), []).append(o)
    for run in centre_runs:
        if run not in by_run:
            fails.append(f"C: declared centre run v{run[0]}-{run[1]} has no chain object")
    for run in by_run:
        if run not in centre_runs:
            fails.append(f"C: chain object run v{run[0]}-{run[1]} is not a declared centre run")
    chain_gap_worst = 0.0
    off_band = island_hits = alvarado_hits = hairpin_hits = 0
    for run, objs in sorted(by_run.items()):
        objs = sorted(objs, key=lambda o: int(o.get("part", 0)))
        for prev, nxt in zip(objs, objs[1:]):          # parts of one run share their boundary ring
            a, b = rc.get(prev["name"], []), rc.get(nxt["name"], [])
            if a and b and _dist_xz(a[-1], b[0]) > JOIN_TOL_M:
                fails.append(f"C: {prev['name']} -> {nxt['name']}: parts {_dist_xz(a[-1], b[0]):.2f} m apart (not joined)")
        for o in objs:
            cs = rc.get(o["name"], [])
            chain_gap_worst = max(chain_gap_worst, _max_consecutive_gap(cs))
            for c in cs:
                k = grid.nearest(c[0], c[2])
                if k < len(cw) and not cw[k] > 0:
                    off_band += 1
                if island_w[k] > 0 and k not in noses:
                    island_hits += 1
                if k <= alv_to:
                    alvarado_hits += 1
                if k in hairpin:
                    hairpin_hits += 1
        if run in centre_runs and objs:
            first = rc.get(objs[0]["name"], [[0, 0, 0]])[0]
            last = rc.get(objs[-1]["name"], [[0, 0, 0]])[-1]
            d0 = _dist_xz(first, pts[run[0]])
            d1 = _dist_xz(last, pts[run[1]])
            if d0 > END_TOL_M or d1 > END_TOL_M:
                fails.append(f"C: run v{run[0]}-{run[1]} ends {d0:.2f} / {d1:.2f} m from the declared end vertices (> {END_TOL_M})")
    if off_band:
        fails.append(f"C: {off_band} chain rings stand on vertices the band does not declare")
    if island_hits:
        fails.append(f"C: {island_hits} chain rings on a median island beyond the nose vertex")
    if alvarado_hits:
        fails.append(f"C: {alvarado_hits} chain rings on Alvarado (v0-{alv_to})")
    if hairpin_hits:
        fails.append(f"C: {hairpin_hits} chain rings inside the hairpin arc")
    counts.update({"chain_objects": len(chain_objs), "chain_runs": len(by_run), "chain_gap_worst_m": round(chain_gap_worst, 3),
                   "chain_rings": sum(len(rc.get(o["name"], [])) for o in chain_objs)})

    # D. kerb-line strips
    es = bands.get("edge_strip_by_vertex") or bands.get("edge_inset_by_vertex") or []
    edge_objs = [o for o in objects if o.get("kind") == "edge"]
    covered: dict[str, set] = {"L": set(), "R": set()}
    on_gap: dict[str, int] = {"L": 0, "R": 0}
    edge_gap_worst = 0.0
    gap_vertices = {k for k in range(min(m, len(es))) if not es[k] > 0}
    for o in edge_objs:
        side = str(o.get("side"))
        cs = rc.get(o["name"], [])
        if not cs:
            continue
        edge_gap_worst = max(edge_gap_worst, _max_consecutive_gap(cs))
        # ends: a `join` meets the neighbouring object's opposite end exactly; a `free` end stands
        # at the edge of a declared gap (bridge span) — anywhere else it is a hole in the wall.
        # `ends` are the RUN's end kinds; `caps` says whether THIS object holds the run's true end
        # (split_plan: parts share their boundary ring and carry no cap) — a capless end is a join.
        ends = list(o.get("ends", []))
        caps = list(o.get("caps", [True, True]))
        for idx in range(min(2, len(ends))):
            end_kind = ends[idx] if (idx >= len(caps) or caps[idx]) else "join"
            pt = cs[0] if idx == 0 else cs[-1]
            if end_kind == "join":
                met = False
                for q in edge_objs:
                    if q is o or str(q.get("side")) != side:
                        continue
                    qs = rc.get(q["name"], [])
                    if qs and _dist_xz(pt, qs[-1] if idx == 0 else qs[0]) <= JOIN_TOL_M:
                        met = True
                        break
                if not met:
                    fails.append(f"D: {o['name']}: {'start' if idx == 0 else 'end'} is a `join` but no same-side object meets it")
            elif end_kind == "free":
                k = grid.nearest(pt[0], pt[2])
                near_gap = any(((k + d) % m) in gap_vertices for d in range(-FREE_END_VERTEX_TOL, FREE_END_VERTEX_TOL + 1))
                if gap_vertices and not near_gap:
                    fails.append(f"D: {o['name']}: free {'start' if idx == 0 else 'end'} at v{k} is not at a declared gap — a hole in the strip")
            else:
                fails.append(f"D: {o['name']}: unknown end kind {end_kind!r}")
        for c in cs:
            k = grid.nearest(c[0], c[2])
            covered.setdefault(side, set()).add(k)
            if k < len(es) and not es[k] > 0 and all(not es[(k + d) % m] > 0 for d in (-1, 1)):
                on_gap[side] = on_gap.get(side, 0) + 1
    allowed = {"L": 0, "R": 0}
    for o in edge_objs:
        if int(o.get("part", 0)) == 0:
            allowed[str(o.get("side"))] = allowed.get(str(o.get("side")), 0) + int(o.get("fold_skipped_run", 0) or 0)
    missing: dict[str, list] = {"L": [], "R": []}
    declared_edge = [k for k in range(min(m, len(es))) if es[k] > 0]
    for side in ("L", "R"):
        cov = covered.get(side, set())
        for k in declared_edge:
            if not any(((k + d) % m) in cov for d in range(-VERTEX_TOL, VERTEX_TOL + 1)):
                missing[side].append(k)
        if len(missing[side]) > allowed.get(side, 0):
            fails.append(f"D: edge {side}: {len(missing[side])} declared vertices without a ring "
                         f"(author reports {allowed.get(side, 0)} fold-dropped): {missing[side][:12]}")
        if on_gap.get(side, 0):
            fails.append(f"D: edge {side}: {on_gap[side]} rings stand inside a declared gap (bridge span)")
    counts.update({"edge_objects": len(edge_objs), "edge_declared_vertices": len(declared_edge),
                   "edge_missing": {s: len(v) for s, v in missing.items()}, "edge_fold_dropped": allowed,
                   "edge_gap_worst_m": round(edge_gap_worst, 3),
                   "edge_rings": sum(len(rc.get(o["name"], [])) for o in edge_objs)})

    # E. race kerbs
    kerb_objs = [o for o in objects if o.get("kind") == "kerb"]
    sub_of = {"inside": "in", "outside": "out", "in": "in", "out": "out"}
    declared = {(int(k["apex"]), sub_of.get(str(k.get("kind")), str(k.get("kind")))) for k in bands.get("kerbs", []) or []}
    authored_set = {(int(o["apex"]), str(o.get("sub"))) for o in kerb_objs}
    if declared != authored_set:
        fails.append(f"E: declared kerbs {sorted(declared)} != authored {sorted(authored_set)}")
    for o in kerb_objs:
        if int(o.get("stations", 0) or 0) <= 0:
            fails.append(f"E: {o['name']}: no stations")
    if authored.get("kerbs_declared_unmatched"):
        fails.append(f"E: declared kerbs matching no detected corner: {authored['kerbs_declared_unmatched']}")
    n_corners_decl = len(bands.get("corners", []) or [])
    n_corners_auth = len(authored.get("corners", []) or [])
    if n_corners_decl and n_corners_auth != n_corners_decl:
        fails.append(f"E: {n_corners_auth} corners authored vs {n_corners_decl} declared")
    counts.update({"kerb_objects": len(kerb_objs), "corners": n_corners_auth,
                   "kerb_fold_dropped": sum(int(o.get("fold_skipped", 0) or 0) for o in kerb_objs)})

    # F. spawn clearance — the AUTHOR's record (author time); the HARD re-measure of the dummies that
    #    actually ship is _verify_spawns (from data/dummies_<id>.json), run by verify() for every call
    sc = authored.get("spawn_clearance", {}) or {}
    for lid, r in sc.items():
        if r.get("synthesised"):
            fails.append(f"F: {lid}: spawn clearance measured on SYNTHESISED dummies — run tools/layout_dummies.py first")
        if r.get("hard"):
            fails.append(f"F: {lid}: a spawn overlaps a strip or stands < {SPAWN_MARGIN_M:.2f} m off it "
                         f"(author-time record): {r['hard'][:4]}")
        for note in r.get("notes", []) or []:
            warns.append(f"F: {lid}: author-time: {note}")
    if not sc:
        warns.append("F: no spawn_clearance recorded (no dummies_<id>.json at authoring time)")

    # reported, not gated
    if edge_gap_worst > SPACING_NOTE_M:
        warns.append(f"edge strip ring spacing reaches {edge_gap_worst:.2f} m on an outside lip (3 m at the centreline): "
                     f"the strip chords the arc there by up to ~{edge_gap_worst ** 2 / (8 * 16.0):.2f} m — denser rings at "
                     f"corners would be the author tool's fix; the mesh itself is continuous")
    oda = authored.get("other_deck_above", []) or []
    if oda:
        warns.append(f"{len(oda)} rings have another ROAD sheet > 0.15 m above the strip base (max "
                     f"{tot.get('other_deck_above_max_m')} m) — a fold / mouth defect for the ribbon's owner, e.g. {oda[0]}")
    if tot.get("deck_vs_data_max_m") is not None:
        warns.append(f"built deck vs data height, worst {tot.get('deck_vs_data_max_m')} m")


def race_layout_spawns(data: Path, cfg: dict | None) -> dict:
    """{race layout id: its data/dummies_<id>.json dict, or None when the file is missing}. A race layout
    is one the config marks race_furniture: true OR whose dummies file says `_kind: race` (so a workshop
    whose own track.config.json predates the layouts is still judged on the dummies it holds)."""
    ids = {str(lo["id"]) for lo in ((cfg or {}).get("layouts") or []) if isinstance(lo, dict) and lo.get("race_furniture")}
    found = {}
    for f in sorted(data.glob("dummies_*.json")):
        lid = f.stem[len("dummies_"):]
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
                         "[--config <track.config.json>] [--pre-author] [--out <file>]")
    allow_standin = pre_author = False
    authored_p = bands_p = config_p = out_p = None
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--allow-standin":
            allow_standin = True; i += 1
        elif a == "--pre-author":
            pre_author = True; i += 1
        elif a == "--authored":
            authored_p = Path(argv[i + 1]); i += 2
        elif a == "--bands":
            bands_p = Path(argv[i + 1]); i += 2
        elif a == "--config":
            config_p = Path(argv[i + 1]); i += 2
        elif a == "--out":
            out_p = Path(argv[i + 1]); i += 2
        else:
            rest.append(a); i += 1
    proj = Path(rest[0]).resolve()
    data = proj / "data"
    authored_p = authored_p or data / "race_authored.json"
    bands_p = bands_p or data / "barrier_bands.json"
    config_p = config_p or proj / "track.config.json"
    out_p = out_p or data / ("race_verify.pre.json" if pre_author else "race_verify.json")   # a partial run never overwrites the full report
    need = [bands_p, data / "centerline.local.json", data / "median_bands.json"]
    if not pre_author:
        need.insert(0, authored_p)
    for p in need:
        if not p.exists():
            raise SystemExit(f"[verify-race] missing {p}")
    authored = None if pre_author else json.loads(authored_p.read_text(encoding="utf-8"))
    bands = json.loads(bands_p.read_text(encoding="utf-8"))
    cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in cl["points_xyz_m"]]
    widths = [float(w) for w in cl["widths_m"]]
    island_w = json.loads((data / "median_bands.json").read_text(encoding="utf-8"))["island_w_by_vertex"]
    if len(island_w) != len(pts) or len(widths) != len(pts):
        raise SystemExit(f"[verify-race] median_bands {len(island_w)} / widths {len(widths)} vs centreline {len(pts)} vertices")
    cfg = json.loads(config_p.read_text(encoding="utf-8")) if config_p.exists() else None
    spawns = race_layout_spawns(data, cfg)
    lp = data / "lights.local.json"
    lamps = json.loads(lp.read_text(encoding="utf-8")).get("lampheads", []) if lp.exists() else None
    r = verify(authored, bands, pts, island_w, allow_standin=allow_standin, widths=widths, spawns=spawns,
               lamps=lamps, pre_author=pre_author)
    if lamps is None:
        r["warnings"].append("G: no data/lights.local.json — no lamps authored, nothing to check")
    c = r["counts"]
    if not pre_author:
        print(f"[verify-race] {c.get('objects')} objects: chain {c.get('chain_objects')} objects / {c.get('chain_runs')} runs / "
              f"{c.get('chain_rings')} rings (worst gap {c.get('chain_gap_worst_m')} m); edge {c.get('edge_objects')} objects / "
              f"{c.get('edge_rings')} rings on {c.get('edge_declared_vertices')} declared vertices (missing {c.get('edge_missing')}, "
              f"fold-dropped {c.get('edge_fold_dropped')}, worst gap {c.get('edge_gap_worst_m')} m); kerbs {c.get('kerb_objects')} "
              f"at {c.get('corners')} corners; interpolated {c.get('interpolated')}/{c.get('rings_total')}")
    for lid, rows in (c.get("spawn_slots") or {}).items():
        cells = ", ".join(f"{q['name'].replace('AC_', '')} {q['clear_edge_m']:+.2f}" if q["clear_centre_m"] is None
                          else f"{q['name'].replace('AC_', '')} {q['clear_edge_m']:+.2f}/c{q['clear_centre_m']:+.2f}" for q in rows)
        print(f"[verify-race] F {lid}: min clearance {c['spawn_min_clear_m'].get(lid)} m (hard floor {SPAWN_MARGIN_M} m): {cells}")
    lm = c.get("lamp_min")
    if lm is not None:
        print(f"[verify-race] G lamps: {c.get('lamps_checked')}/{c.get('lamps')} masts beside a strip (arm {c.get('lamp_arm_m')} m, "
              f"mast r {c.get('mast_r_m')} m); minimum margin {c.get('lamp_min_margin_m')} m at lamp {lm['lamp']} v{lm['vertex']} "
              f"lat {lm['lat_m']:+.2f} vs the {lm['against']} strip; {c.get('lamps_inside')} inside")
    for w in r["warnings"]:
        print(f"[verify-race] note: {w}")
    for f in r["fails"]:
        print(f"[verify-race] FAIL {f}")
    out_p.write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(f"[verify-race] {'OK' if r['ok'] else 'FAILED'}{' (pre-author: F + G only)' if pre_author else ''} -> {out_p}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
