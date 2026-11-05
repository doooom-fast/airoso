"""Gate the JUNCTION PADS on the BUILT road (ledger 0054 P3 step 2; EXPANSION-PLAN V3 "Pads J2-J4", V2 pad heights;
docs/JUNCTIONS.md rules 1, 3, 9 and §4's machine gates). Reads data/track.obj — the triangles the road kn5 ships — and
data/pads.built.json only to know where to look (L5: never the data that placed it).

Per pad:
  P1 PRESENT       the deck (1ROAD_pad_<id>), its curb (1KERB_sidewalk_pad<id>) and one 1WALL_STUB_PAD_<id>_<stub> per
                   stub arm are in the OBJ
  P2 COVERAGE      single coverage (rule 1): on a COVER_STEP_M raster over the pad's outline, no two road sheets
                   within SHEET_DZ_M of each other — multi-coverage 0 m2 [std: JUNCTIONS]
  P3 SEAMS         along every route arm's cut, every SEAM_STEP_M: the pad's surface and the arm's surface 2 cm either
                   side of the seam within SEAM_GAP_M (10 mm [std: EXPANSION-PLAN V3]); the arm row's three vertices
                   each have a pad vertex within 1 mm and none between 1 mm and 5 cm (rule 3's binarity)
  P4 NO GRASS      no ground on top of the pad deck anywhere on the raster (grass over the deck by more than 0.005 m)
  P5 CURBS         no curb / walk triangle centroid over the pad's pavement (rule 9)
  P6 BARRIERS      every stub's barrier stands at least BARRIER_MIN_H_M over the pad deck along its path, and its base
                   no more than SEAT_FLOAT_M over the surface under it (seated, tools/verify_stubs.py's numbers)
  P7 HEIGHT        the deck at the junction node within NODE_TOL_M of the node's 3DEP (EXPANSION-PLAN V2: 103.9 /
                   33.4 / 92.4 +- 1 m)

    python tools/verify_pads.py <project-dir>      -> data/verify_pads.json, exit 1 on any failure
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

COVER_STEP_M = 0.5        # [invented] the coverage / grass raster
RASTER_PHASE_M = 0.137    # the raster's offsets off the whole metre in x / z, unequal (never on the deck's own 1 m
RASTER_PHASE_Z_M = 0.311  # interior grid, its vertices, its edges or its diagonals)
SHEET_DZ_M = 0.25         # [invented] two road sheets closer than this vertically over one point = multi-coverage
SEAM_STEP_M = 0.25        # [invented] seam sampling step
SEAM_GAP_M = 0.010        # EXPANSION-PLAN V3: seam gap <= 10 mm
NEAR_LO_M, NEAR_HI_M = 0.001, 0.05   # JUNCTIONS rule 3: nothing between 1 mm and 5 cm of a seam vertex
GRASS_OVER_M = 0.005      # [invented] grass this far over the deck is on top of it
BARRIER_MIN_H_M = 0.8     # tools/verify_stubs.py BARRIER_MIN_H_M [invented there]
SEAT_FLOAT_M = 0.05       # tools/verify_stubs.py SEAT_FLOAT_M
NODE_TOL_M = 1.0          # EXPANSION-PLAN V2
KEEP_M = 90.0
CELL = 2.0


def load(obj, centres):
    V, out, cur = [], [], None
    k2 = KEEP_M * KEEP_M
    with open(obj, "r", encoding="ascii", errors="replace") as f:
        for line in f:
            c2 = line[:2]
            if c2 == "v ":
                q = line.split()
                V.append((float(q[1]), float(q[2]), float(q[3])))
            elif c2 in ("o ", "g "):
                cur = line[2:].strip()
            elif c2 == "f " and cur is not None:
                u = cur.upper()
                if u.startswith(("MARKINGS", "YLINE", "GRASS_FAR")):
                    continue
                idx = [int(t.split("/")[0]) for t in line.split()[1:]]
                pts = [V[i - 1] for i in idx]
                if not any((p[0] - cx) ** 2 + (p[2] - cz) ** 2 <= k2 for p in pts for cx, cz in centres):
                    continue
                for k in range(1, len(pts) - 1):
                    out.append((pts[0], pts[k], pts[k + 1], u))
    return V, out


class Field:
    def __init__(self, tris):
        self.t = tris
        self.cells = {}
        for k, (a, b, c, _n) in enumerate(tris):
            for ix in range(int(math.floor(min(a[0], b[0], c[0]) / CELL)), int(math.floor(max(a[0], b[0], c[0]) / CELL)) + 1):
                for iz in range(int(math.floor(min(a[2], b[2], c[2]) / CELL)), int(math.floor(max(a[2], b[2], c[2]) / CELL)) + 1):
                    self.cells.setdefault((ix, iz), []).append(k)

    def at(self, x, z):
        """[(height, group name)] of every triangle over (x, z)"""
        out = []
        for k in self.cells.get((int(math.floor(x / CELL)), int(math.floor(z / CELL))), ()):
            a, b, c, n = self.t[k]
            d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(d) < 1e-12:
                continue
            l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
            l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
            l3 = 1.0 - l1 - l2
            if min(l1, l2, l3) >= -1e-7:
                out.append((l1 * a[1] + l2 * b[1] + l3 * c[1], n))
        return out


def pip(poly, x, z):
    inside = False
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (a[1] > z) != (b[1] > z) and x < a[0] + (z - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
            inside = not inside
    return inside


def lm_pads_shape(built, data):
    """tools/lm_pads_blend.py's record (ledger 0078 round 7 / 0079 round D: the lap is both main arms, cut at two of its
    own rows; the deck ends at the measured outline with NO curb or walk, "edge": "shoulder") read as this gate's own
    shape, so every rule judges it unchanged: the outline is outline_en (the track's local x / north = the OBJ's x / z);
    each cut row's vertices are that arm's seam vertices (every one, densify's columns included, in order along the row);
    the K-rails are the stubs; the node height's reference is the lap's own 3DEP profile at the node vertex
    (centerline.local.json), as pads.plan.json's z_3dep_m is for Lake Murray's pads. ``curb`` False: P1 does not ask for a
    1KERB_sidewalk_pad (Kevin: "no sidewalks"); P5 still judges every curb triangle over the pavement.
    Returns (built, plan) or None when the record is not lm_pads' (Lake Murray's pads.built.json: unchanged)."""
    pads = built.get("pads") or []
    if not pads or not all("rows" in p and "outline_en" in p and "seams" not in p for p in pads):
        return None
    loc = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    P = loc["points_xyz_m"]
    elev0 = loc["origin"]["elev_m"]
    out, plan = [], {}
    for p in pads:
        seams = []
        for k, row in zip(p["cuts"], p["rows"]):
            for i, q in enumerate(row):                      # Blender (x, north, up) -> OBJ (x, up, north)
                seams.append({"arm": f"lap_v{k}", "row_vertex": f"v{i}", "order": i, "xyz": [q[0], q[2], q[1]]})
        stubs = [{"stub": b["object"], "barrier": dict(b["barrier"], seat=b["barrier"].get("seat") or [])}
                 for b in p.get("barriers") or []]
        out.append({"id": p["id"], "outline_xz": p["outline_en"], "seams": seams, "stubs": stubs, "curb": False})
        nd = P[p["node"]]
        plan[p["id"]] = {"node_xz": [nd[0], nd[2]], "z_3dep_m": round(nd[1] + elev0, 3),
                         "_from": f"centerline.local.json v{p['node']} (the lap's 3DEP profile)"}
    return {"pads": out}, plan


def verify(project):
    proj = Path(project)
    data = proj / "data"
    bp = data / "pads.built.json"
    if not bp.exists():
        return None
    built = json.loads(bp.read_text(encoding="utf-8"))
    lm = lm_pads_shape(built, data)
    if lm is not None:
        built, plan = lm
    else:
        plan = {p["id"]: p for p in json.loads((data / "pads.plan.json").read_text(encoding="utf-8"))["pads"]}
    centres = []
    for p in built["pads"]:
        o = p["outline_xz"]
        centres.append((sum(q[0] for q in o) / len(o), sum(q[1] for q in o) / len(o)))
    V, tris = load(data / "track.obj", centres)
    F = Field(tris)
    names = {t[3] for t in tris}
    rows = []
    for p, (cx, cz) in zip(built["pads"], centres):
        pid = p["id"]
        fails = []
        deck_n, curb_n = f"1ROAD_PAD_{pid}".upper(), f"1KERB_SIDEWALK_PAD{pid}".upper()
        need = (deck_n,) + ((curb_n,) if p.get("curb", True) else ())   # lm_pads' shoulder edge: no curb asked for
        for n in need + tuple(s["barrier"]["object"].upper() for s in p["stubs"]):
            if not any(m == n or m.startswith(n + "_") or m.startswith(n + ".") for m in names):
                fails.append(f"P1: {n} not in the built OBJ")
        o = [tuple(q) for q in p["outline_xz"]]
        xs, zs = [q[0] for q in o], [q[1] for q in o]
        multi = grass = n_in = 0
        worst_multi = None
        # the raster stands RASTER_PHASE_M off the whole metre: the deck's interior points are a 1 m grid, and a sample
        # exactly on a shared vertex / edge reads every triangle round it (the same sheet several times)
        x = math.floor(min(xs)) - 3.0 + RASTER_PHASE_M
        while x <= max(xs) + 3.0:
            z = math.floor(min(zs)) - 3.0 + RASTER_PHASE_Z_M
            while z <= max(zs) + 3.0:
                if pip(o, x, z):
                    n_in += 1
                    hs = F.at(x, z)
                    road = sorted(h for h, n in hs if n.startswith("1ROAD"))
                    deck = [h for h, n in hs if n.startswith(deck_n)]
                    for a, b in zip(road, road[1:]):
                        if b - a < SHEET_DZ_M:
                            multi += 1
                            worst_multi = worst_multi or (round(x, 2), round(z, 2), round(b - a, 4))
                            break
                    if deck:
                        top_road = max(deck)
                        if any(n.startswith("1GRASS") and h > top_road + GRASS_OVER_M for h, n in hs):
                            grass += 1
                z += COVER_STEP_M
            x += COVER_STEP_M
        multi_m2 = multi * COVER_STEP_M * COVER_STEP_M
        if multi_m2 > 0:
            fails.append(f"P2: {multi_m2:.2f} m2 of multi-coverage (e.g. {worst_multi})")
        if grass:
            fails.append(f"P4: grass over the deck at {grass} raster points")
        # P3 seams
        seam_rows, near_miss, max_gap = [], 0, 0.0
        pad_verts = []
        for a, b, c, n in tris:
            if n.startswith(deck_n):
                pad_verts += [a, b, c]
        by_arm = {}
        for sv in p["seams"]:
            by_arm.setdefault(sv["arm"], []).append(sv)
        for arm, svs in by_arm.items():
            for sv in svs:
                q = sv["xyz"]
                ds = [math.dist(q, v) for v in pad_verts if abs(v[0] - q[0]) < 0.06 and abs(v[2] - q[2]) < 0.06]
                dmin = min(ds) if ds else None
                if dmin is None or dmin > NEAR_LO_M:
                    fails.append(f"P3: {arm} seam vertex {sv['row_vertex']} has no pad vertex within 1 mm "
                                 f"(nearest {dmin})")
                near_miss += sum(1 for d in ds if NEAR_LO_M < d < NEAR_HI_M)
            pts = sorted(svs, key=lambda r: r["order"] if "order" in r else ["L", "C", "R"].index(r["row_vertex"]))
            for (qa, qb) in zip(pts, pts[1:]):
                A, B = qa["xyz"], qb["xyz"]
                L = math.dist((A[0], A[2]), (B[0], B[2]))
                tx, tz = (B[0] - A[0]) / L, (B[2] - A[2]) / L
                nx, nz = -tz, tx
                k = 1
                while k * SEAM_STEP_M < L:
                    u = k * SEAM_STEP_M
                    mx, mz = A[0] + tx * u, A[2] + tz * u
                    hs_l = [h for h, n in F.at(mx + nx * 0.02, mz + nz * 0.02) if n.startswith("1ROAD")]
                    hs_r = [h for h, n in F.at(mx - nx * 0.02, mz - nz * 0.02) if n.startswith("1ROAD")]
                    if hs_l and hs_r:
                        g = min(abs(a_ - b_) for a_ in hs_l for b_ in hs_r)
                        max_gap = max(max_gap, g)
                    else:
                        fails.append(f"P3: {arm}: a hole at the seam ({mx:.2f}, {mz:.2f})")
                        break
                    k += 1
            seam_rows.append(arm)
        if max_gap > SEAM_GAP_M:
            fails.append(f"P3: a seam step of {max_gap:.4f} m (> {SEAM_GAP_M})")
        if near_miss:
            fails.append(f"P3: {near_miss} pad vertices 1 mm-5 cm from a seam vertex (rule 3)")
        # P5 curbs over pavement
        curb_over = 0
        for a, b, c, n in tris:
            if not n.startswith("1KERB"):
                continue
            gx, gz = (a[0] + b[0] + c[0]) / 3, (a[2] + b[2] + c[2]) / 3
            if pip(o, gx, gz):
                hy = (a[1] + b[1] + c[1]) / 3
                deck = [h for h, nn in F.at(gx, gz) if nn.startswith(deck_n)]
                if deck and hy > max(deck) + 0.02:
                    curb_over += 1
        if curb_over:
            fails.append(f"P5: {curb_over} curb triangles over the pad's pavement")
        # P6 barriers
        bars = []
        for s in p["stubs"]:
            bn = s["barrier"]["object"].upper()
            wall = [t for t in tris if t[3].startswith(bn)]
            hmin, fl = None, 0.0
            for q in s["barrier"]["path_xz"]:
                tops = [h for h, n in F.at(q[0], q[1]) if n.startswith(bn)]
                deck = [h for h, n in F.at(q[0], q[1]) if n.startswith(("1ROAD", "1KERB"))]
                if tops and deck:
                    hh = max(tops) - max(deck)
                    hmin = hh if hmin is None else min(hmin, hh)
            base = min((v[1] for t in wall for v in t[:3]), default=None)
            for r in s["barrier"]["seat"]:
                sv = [v for v in r["surface"] if v is not None]
                if sv:
                    fl = max(fl, r["base"] - max(sv))
            bars.append({"stub": s["stub"], "min_height_over_deck_m": None if hmin is None else round(hmin, 3),
                         "max_float_m": round(fl, 4), "tris": len(wall), "base_y": base})
            if hmin is None or hmin < BARRIER_MIN_H_M:
                fails.append(f"P6: {s['stub']} barrier stands {hmin} m over the deck (< {BARRIER_MIN_H_M})")
            if fl > SEAT_FLOAT_M:
                fails.append(f"P6: {s['stub']} barrier floats {fl:.3f} m")
        # P7 node height
        pl = plan[pid]
        nx_, nz_ = pl["node_xz"]
        dk = [h for h, n in F.at(nx_, nz_) if n.startswith(deck_n)]
        elev0 = None
        try:
            elev0 = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))["origin"]["elev_m"]
        except (OSError, KeyError):
            pass
        node_dev = None
        if dk and elev0 is not None and pl.get("z_3dep_m") is not None:
            node_dev = (max(dk) - 0.10 + elev0) - float(pl["z_3dep_m"])
            if abs(node_dev) > NODE_TOL_M:
                fails.append(f"P7: the deck at the node stands {node_dev:+.2f} m off its 3DEP")
        elif not dk:
            fails.append("P7: no deck over the junction node")
        rows.append({"id": pid, "raster_points": n_in, "multi_coverage_m2": multi_m2, "grass_on_deck": grass,
                     "seam_max_gap_m": round(max_gap, 5), "seam_near_misses": near_miss,
                     "curb_over_pavement": curb_over, "barriers": bars,
                     "node_deck_minus_3dep_m": None if node_dev is None else round(node_dev, 3),
                     "node_z_3dep_m": pl.get("z_3dep_m"), "fails": fails, "fail": bool(fails)})
    out = {"_doc": "tools/verify_pads.py (ledger 0054 P3): the junction pads on the BUILT road", "pads": rows,
           "fail": any(r["fail"] for r in rows)}
    (data / "verify_pads.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for r in rows:
        print(f"[verify_pads] {r['id']}: {'FAIL' if r['fail'] else 'PASS'}  multi-coverage {r['multi_coverage_m2']} m2, "
              f"seam max {1000 * r['seam_max_gap_m']:.1f} mm ({r['seam_near_misses']} near misses), grass {r['grass_on_deck']}, "
              f"curb over pavement {r['curb_over_pavement']}, node {r['node_deck_minus_3dep_m']} m vs 3DEP, barriers "
              + ", ".join(f"{b['stub']} {b['min_height_over_deck_m']} m" for b in r["barriers"]))
        for f in r["fails"]:
            print(f"    {f}")
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    r = verify(argv[0] if argv else ".")
    if r is None:
        print("[verify_pads] no data/pads.built.json: no pad to judge")
        return 0
    return 1 if r["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
