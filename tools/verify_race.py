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
  F  spawn clearance — no race-layout spawn overlaps a strip; dummies not synthesised

Reported, never gated: another ROAD sheet above a strip base (a fold / mouth defect for its owner,
0033/0046 class), the worst deck-vs-data height, the soft spawn-clearance notes.

    python tools/verify_race.py <project-dir> [--allow-standin] [--authored <file>] [--bands <file>]

Writes data/race_verify.json. Plain functions so tests/run_tests.py can drive it without Blender.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

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

def verify(authored: dict, bands: dict, pts: list, island_w: list, *, allow_standin: bool = False) -> dict:
    fails: list[str] = []
    warns: list[str] = []
    counts: dict = {}
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

    # F. spawn clearance
    sc = authored.get("spawn_clearance", {}) or {}
    for lid, r in sc.items():
        if r.get("synthesised"):
            fails.append(f"F: {lid}: spawn clearance measured on SYNTHESISED dummies — run tools/layout_dummies.py first")
        if r.get("hard"):
            fails.append(f"F: {lid}: a spawn overlaps a strip: {r['hard'][:4]}")
        for note in r.get("notes", []) or []:
            warns.append(f"F: {lid}: {note}")
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

    return {"ok": not fails, "fails": fails, "warnings": warns, "counts": counts}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("usage: python tools/verify_race.py <project-dir> [--allow-standin] [--authored <file>] [--bands <file>]")
    allow_standin = False
    authored_p = bands_p = None
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--allow-standin":
            allow_standin = True; i += 1
        elif a == "--authored":
            authored_p = Path(argv[i + 1]); i += 2
        elif a == "--bands":
            bands_p = Path(argv[i + 1]); i += 2
        else:
            rest.append(a); i += 1
    proj = Path(rest[0]).resolve()
    data = proj / "data"
    authored_p = authored_p or data / "race_authored.json"
    bands_p = bands_p or data / "barrier_bands.json"
    for p in (authored_p, bands_p, data / "centerline.local.json", data / "median_bands.json"):
        if not p.exists():
            raise SystemExit(f"[verify-race] missing {p}")
    authored = json.loads(authored_p.read_text(encoding="utf-8"))
    bands = json.loads(bands_p.read_text(encoding="utf-8"))
    cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in cl["points_xyz_m"]]
    island_w = json.loads((data / "median_bands.json").read_text(encoding="utf-8"))["island_w_by_vertex"]
    if len(island_w) != len(pts):
        raise SystemExit(f"[verify-race] median_bands {len(island_w)} vs centreline {len(pts)} vertices")
    r = verify(authored, bands, pts, island_w, allow_standin=allow_standin)
    c = r["counts"]
    print(f"[verify-race] {c.get('objects')} objects: chain {c.get('chain_objects')} objects / {c.get('chain_runs')} runs / "
          f"{c.get('chain_rings')} rings (worst gap {c.get('chain_gap_worst_m')} m); edge {c.get('edge_objects')} objects / "
          f"{c.get('edge_rings')} rings on {c.get('edge_declared_vertices')} declared vertices (missing {c.get('edge_missing')}, "
          f"fold-dropped {c.get('edge_fold_dropped')}, worst gap {c.get('edge_gap_worst_m')} m); kerbs {c.get('kerb_objects')} "
          f"at {c.get('corners')} corners; interpolated {c.get('interpolated')}/{c.get('rings_total')}")
    for w in r["warnings"]:
        print(f"[verify-race] note: {w}")
    for f in r["fails"]:
        print(f"[verify-race] FAIL {f}")
    (data / "race_verify.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(f"[verify-race] {'OK' if r['ok'] else 'FAILED'} -> data/race_verify.json")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
