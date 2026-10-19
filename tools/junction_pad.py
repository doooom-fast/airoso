"""JUNCTION PADS (ledger 0054 P3 step 2; EXPANSION-PLAN A4; docs/JUNCTIONS.md §2.0 topology B, rules 1-6, 9-10, 18(d)):
the north network's three new crossroads J2 (Waring / Princess View / Mound Ave), J3 (Princess View / Mission Gorge /
Mission Gorge west / the quarry drive) and J4 (Mission Gorge / Jackson / Mission Gorge east / the visitor-centre
entrance) as ONE pad each — "one rug of asphalt poured under the whole crossroads, instead of two strips of tape laid
over each other" (EXPANSION-PLAN A4): a 23-33 m road cannot bend 74-84 deg round a 6-12 m curb corner as a swept
ribbon without its inside edge folding over itself.

This module is the pure geometry (no bpy; tests/tools/test_junction_pad.py runs it in plain Python) plus the plan step;
tools/author_junction_pad_blend.py builds it in Blender, tools/verify_pads.py gates it on the BUILT road.

THE PLAN (`python tools/junction_pad.py plan <project>`; draft stage, after trim_connectors): opt-in by
track.config.json route.junction_pads = {pad id: authored intermediate} (e.g. {"J2": "data/expansion.north.json"});
none declared = data/pads.plan.json removed, nothing else happens. Per pad, from the intermediate's pads[]:
  * the DESIGN OUTLINE (pads[].outline_xz: every arm cut straight, every corner a true circular arc at the measured
    curb-return radius with a point every 0.75 m — JUNCTIONS rule 5's 0.6-0.8 m), turned counter-clockwise;
  * each ROUTE arm: the north connector piece whose end stands on its cut (tools/expansion_pieces.py ends every pad
    end exactly there) — the Blender pass welds the pad onto that piece's last row as the mesh has it;
  * each STUB arm (an unbuilt road at the crossroads): Phase 5's closed stub (JUNCTIONS 18(d), Kevin 2026-10-14: "a road
    we are not completing gets a barrier, not a curve") — the stub's pavement runs on STUB_LENGTH_M from its mouth line
    to the barrier's centre and TAIL_M past it (tools/stub_roads.py's own numbers), its far edge at the real ground:
    3DEP 1 m under its two corners and its middle (data/pads.3dep.json, cached; fetched with TLS verified, never gap
    filled) + the road's LIFT_M; the K-rail across it at STUB_LENGTH_M, back of walk to back of walk.

THE OUTLINE AS BUILT (outline_as_built, pure): the design outline with every route arm's cut replaced by the arm's own
last row (left edge, centre, right edge: the very vertices — JUNCTIONS rule 3, seams 0.000 m) and every stub arm's
mouth line replaced by its pavement (mouth corner -> barrier station -> far corner -> far middle -> far corner ->
barrier station -> mouth corner); every segment then carries a point every BOUNDARY_STEP_M (a point ON a seam's
straight 3-D edge leaves no crack). Fixed heights: the arm rows' own, the stub far edges' 3DEP; everything else is the
soap film between them (tools/apron.harmonic_heights). The CURB RUNS: the outline minus the route arm cuts and the
stub far edges — each run a curb + sidewalk strip (build_loop_blend's curb_sidewalk profile, swept toward the outside)
whose first / last station is the route arm's own curb row where it starts / ends at one (rule 9: the strip follows
the pad's outline round the corner arc into the next street and never crosses pavement).
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))

BOUNDARY_STEP_M = 1.0       # tools/apron.py BOUNDARY_STEP_M: outline segments get a point at least this often
STUB_LENGTH_M = 15.0        # tools/stub_roads.py STUB_LENGTH_M [invented there]: mouth line -> barrier centre
TAIL_M = 1.0                # tools/stub_roads.py TAIL_M [invented there]: road behind the barrier centre
LIFT_M = 0.10               # build_loop_blend: the road deck stands this over the profile it was swept on
SNAP_MAX_M = 0.6            # [invented] a route arm's built end row must lie within this of the design cut, or stop
CUT_MATCH_M = 1e-3          # a design cut point IS an outline vertex within this
PREFIX = "pad"              # object names: 1ROAD_pad_<id>, 1KERB_sidewalk_pad<id>, 1WALL_STUB_PAD_<id>_<stub>


class PadError(RuntimeError):
    """a pad that cannot be built honestly — the caller stops loudly"""


DESIGN_ITER = 12            # the arm-line / cut fixed point converges in 2-4 rounds (1e-3 m)


def design_pads(doc, pieces):
    """THE PADS ON THE ROADS AS THEY ARE (P3). The intermediate drew each route arm as a straight line through its piece
    30 m from the node, along the piece's direction from 30 to 70 m (author_expansion.arm_lines); where the real road
    still curves into the junction that line ends up to 4 m off the piece's own pavement at the cut (Jackson at J4: 4.08
    m; Princess View at J3 1.46 m; Waring at J2 0.73 m — measured on the intermediate). Here each route arm is the line
    TANGENT to its piece at the pad cut (through the piece's pavement midline there, the piece's own curb-to-curb width),
    the corners re-filleted by the very same author_expansion.build_pad (true arcs at the same measured radii, a point
    every 0.7 m, every cut PAD_CUT_PAD_M past its farther tangent point) and the cut found as the fixed point where the
    piece's own station lands on its arm's cut line; the stub arms keep the intermediate's lines. Returns {pad id:
    {"arms": [...], "corners": [...], "outline_xz": [...], "stubs": {stub id: author_expansion.build_stub record}}} —
    every route arm with its piece, piece end and cut station `cut_s`."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import author_expansion as ae
    stubs_in = {s["id"]: s for s in doc.get("stubs", [])}
    out = {}
    for pad in doc.get("pads", []):
        J = pad["id"]
        node = (float(pad["node_xz"][0]), float(pad["node_xz"][1]))
        arms = []
        for a in pad["arms"]:
            if a["kind"] == "stub":
                d = ae.unit_from_bearing(float(a["bearing_out_deg"]))
                nA = ae.left_normal(d)
                (ax, az), (bx, bz) = a["cut_line_xz"]
                c = (float(a["left_m"]) + float(a["right_m"])) / 2.0
                p = ((ax + bx) / 2.0 - nA[0] * c, (az + bz) / 2.0 - nA[1] * c)
                arms.append({"name": a["name"], "kind": "stub", "stub_id": a["stub"], "out": d, "p": p,
                             "left": float(a["left_m"]), "right": float(a["right_m"]), "bearing": ae.bearing(d),
                             "src": stubs_in[a["stub"]]["src"]})
            else:
                pc = pieces[a["piece"]]
                arms.append({"name": a["name"], "kind": "route", "piece": a["piece"], "piece_end": a["piece_end"],
                             "s": float(pc.cuts[a["piece_end"]]["s"])})
        corners = outline = None
        for _it in range(DESIGN_ITER):
            for A in arms:
                if A["kind"] != "route":
                    continue
                pc = pieces[A["piece"]]
                pnt, t, nrm = pc.frame(A["s"])
                L, R = pc.curbs(A["s"])
                sgn = 1.0 if A["piece_end"] == "start" else -1.0
                A["out"] = (t[0] * sgn, t[1] * sgn)
                c = (L + R) / 2.0
                A["p"] = (pnt[0] + nrm[0] * c, pnt[1] + nrm[1] * c)
                A["left"], A["right"] = (L - R) / 2.0, -(L - R) / 2.0
                A["bearing"] = ae.bearing(A["out"])
            arms.sort(key=lambda q: q["bearing"])
            corners, outline = ae.build_pad(J, node, arms)
            moved = 0.0
            for A in arms:
                if A["kind"] != "route":
                    continue
                dist_ = (A["p"][0] - node[0]) * A["out"][0] + (A["p"][1] - node[1]) * A["out"][1]
                ds = A["cut_m"] - dist_
                moved = max(moved, abs(ds))
                A["s"] += ds if A["piece_end"] == "start" else -ds
            if moved < 1e-3:
                break
        else:
            raise PadError(f"{J}: the arm cuts did not converge ({moved:.4f} m)")
        arms_out, stubs_out = [], {}
        for A in arms:
            rec = {"name": A["name"], "kind": A["kind"], "bearing_out_deg": round(A["bearing"], 3),
                   "left_m": round(A["left"], 4), "right_m": round(A["right"], 4), "cut_from_node_m": round(A["cut_m"], 4),
                   "cut_line_xz": [[round(v, 4) for v in q] for q in A["cut_line"]]}
            if A["kind"] == "route":
                rec.update({"piece": A["piece"], "piece_end": A["piece_end"], "cut_s": round(A["s"], 4),
                            "stub": None})
            else:
                rec["stub"] = A["stub_id"]
                st = ae.build_stub(A, J)
                stubs_out[A["stub_id"]] = st
            arms_out.append(rec)
        out[J] = {"id": J, "node_xz": [node[0], node[1]], "arms": arms_out,
                  "corners": [{"between": [arms[c["a"]]["name"], arms[c["b"]]["name"]], "R_m": c["R"],
                               "R_source": c["R_source"], "centre_xz": [round(v, 4) for v in c["C"]],
                               "tangents_from_node_m": [round(c["dA"], 3), round(c["dB"], 3)]} for c in corners],
                  "outline_xz": [[round(q[0], 4), round(q[1], 4)] for q in outline], "stubs": stubs_out}
    return out


def _area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                     for i in range(len(poly)))


def ccw(poly):
    """the polygon counter-clockwise (x east, z north: positive signed area)"""
    return list(poly) if _area(poly) > 0 else list(reversed(poly))


def _find(poly, pt, tol=CUT_MATCH_M):
    for i, q in enumerate(poly):
        if math.hypot(q[0] - pt[0], q[1] - pt[1]) <= tol:
            return i
    raise PadError(f"design cut point {pt} is not an outline vertex")


def arm_cut_order(poly, arm):
    """(i, j): the outline indices of the arm's two cut points, j == i + 1 (cyclic) — the CCW traversal crosses the cut
    from i to j, the arm itself lying to the RIGHT of i -> j"""
    a = _find(poly, arm["cut_line_xz"][0])
    b = _find(poly, arm["cut_line_xz"][1])
    n = len(poly)
    if (a + 1) % n == b:
        return a, b
    if (b + 1) % n == a:
        return b, a
    raise PadError(f"arm {arm['name']}: its cut points are not neighbours on the outline ({a}, {b})")


def stub_dir(stub):
    """unit plan vector out along a stub (its pavement's mouth corner -> far corner)"""
    m0, _m1, _f1, f0 = stub["pavement_xz"]
    d = (f0[0] - m0[0], f0[1] - m0[1])
    L = math.hypot(*d)
    if L < 1e-6:
        raise PadError(f"stub {stub['id']}: degenerate pavement")
    return (d[0] / L, d[1] / L)


def stub_far_points(pad, stubs):
    """{stub id: [(x, z) far corner at the CCW-first cut point, far middle, far corner at the second]} — where 3DEP is
    read (plan step)"""
    poly = ccw(pad["outline_xz"])
    out = {}
    for arm in pad["arms"]:
        if arm["kind"] != "stub":
            continue
        st = stubs[arm["stub"]]
        i, j = arm_cut_order(poly, arm)
        d = stub_dir(st)
        L = STUB_LENGTH_M + TAIL_M
        p, q = poly[i], poly[j]
        fp = (p[0] + d[0] * L, p[1] + d[1] * L)
        fq = (q[0] + d[0] * L, q[1] + d[1] * L)
        out[st["id"]] = [fp, ((fp[0] + fq[0]) / 2, (fp[1] + fq[1]) / 2), fq]
    return out


def outline_as_built(pad, stubs, arm_rows, stub_heights, step=BOUNDARY_STEP_M):
    """The pad's outline with the route arms' built rows and the stubs' pavements (module doc).

    pad          the intermediate's pads[] record
    stubs        {stub id: the intermediate's stubs[] record}
    arm_rows     {arm name: {"L": (x, y, z), "C": ..., "R": ...}} the route arm's LAST row as the mesh has it (L / R
                 = the row's two edge vertices in the connector's own sense — matched here to the cut's two points)
    stub_heights {stub id: [y far corner 1, y far middle, y far corner 2]} (deck heights: 3DEP + LIFT_M)

    Returns {"outline": [(x, z)], "heights": [y or None], "fixed": [bool], "kind": [str], "runs": [[indices]],
    "run_ends": [(start tag, end tag)], "arms": {arm name: {...}}, "barriers": {stub id: (i_right, i_left)}} — kind per
    vertex: 'cut' (a route arm's row vertex), 'stub_far', 'stub_bar' (a barrier station on a stub side), 'edge'; a run
    end tag is ('arm', arm name, row key) at a route arm's row end or ('stub', stub id) at a stub far corner."""
    poly = ccw(pad["outline_xz"])
    n = len(poly)
    arms = {a["name"]: a for a in pad["arms"]}
    cut_at = {}
    for a in pad["arms"]:
        i, j = arm_cut_order(poly, a)
        cut_at[i] = (a, j)
    out, hs, fx, kind, tags = [], [], [], [], []
    arm_info = {}
    barriers = {}

    def add(p, h, f, k, tag=None):
        out.append((float(p[0]), float(p[1])))
        hs.append(h)
        fx.append(f)
        kind.append(k)
        tags.append(tag)
        return len(out) - 1

    k = 0
    # start the walk on a vertex that begins no cut, so every cut is handled whole
    start = next(s for s in range(n) if s not in cut_at and all(j != s for _a, j in cut_at.values()))
    order = [(start + t) % n for t in range(n)]
    skip_next = set()
    for idx in order:
        if idx in skip_next:
            continue
        if idx not in cut_at:
            add(poly[idx], None, False, "edge")
            continue
        a, j = cut_at[idx]
        p, q = poly[idx], poly[j]
        skip_next.add(j)
        if a["kind"] == "route":
            rows = arm_rows.get(a["name"])
            if rows is None:
                raise PadError(f"arm {a['name']}: no built row")
            ends = [rows["L"], rows["R"]]
            e_p = min(ends, key=lambda r: math.hypot(r[0] - p[0], r[2] - p[1]))
            e_q = rows["R"] if e_p is rows["L"] else rows["L"]
            for e, d in ((e_p, p), (e_q, q)):
                off = math.hypot(e[0] - d[0], e[2] - d[1])
                if off > SNAP_MAX_M:
                    raise PadError(f"arm {a['name']}: the built row's edge stands {off:.2f} m off the design cut "
                                   f"(> {SNAP_MAX_M} m)")
            key_p = "L" if e_p is rows["L"] else "R"
            key_q = "R" if key_p == "L" else "L"
            i0 = add((e_p[0], e_p[2]), e_p[1], True, "cut", ("arm", a["name"], key_p))
            add((rows["C"][0], rows["C"][2]), rows["C"][1], True, "cut", ("arm", a["name"], "C"))
            i2 = add((e_q[0], e_q[2]), e_q[1], True, "cut", ("arm", a["name"], key_q))
            arm_info[a["name"]] = {"kind": "route", "idx": [i0, i0 + 1, i2]}
        else:
            st = stubs[a["stub"]]
            d = stub_dir(st)
            # the arm lies to the RIGHT of p -> q on a CCW outline: check it (a design error would fold the pad)
            cr = (q[0] - p[0]) * d[1] - (q[1] - p[1]) * d[0]
            if cr >= 0:
                raise PadError(f"stub {st['id']}: its direction does not leave the pad on the outside")
            h = stub_heights[st["id"]]
            Lb, Lf = STUB_LENGTH_M, STUB_LENGTH_M + TAIL_M
            i_mouth_p = add(p, None, False, "edge")
            ib_p = add((p[0] + d[0] * Lb, p[1] + d[1] * Lb), None, False, "stub_bar")
            add((p[0] + d[0] * Lf, p[1] + d[1] * Lf), h[0], True, "stub_far", ("stub", st["id"], 0))
            fp = out[-1]
            fq = (q[0] + d[0] * Lf, q[1] + d[1] * Lf)
            add(((fp[0] + fq[0]) / 2, (fp[1] + fq[1]) / 2), h[1], True, "stub_far", ("stub", st["id"], 1))
            add(fq, h[2], True, "stub_far", ("stub", st["id"], 2))
            ib_q = add((q[0] + d[0] * Lb, q[1] + d[1] * Lb), None, False, "stub_bar")
            i_mouth_q = add(q, None, False, "edge")
            arm_info[a["name"]] = {"kind": "stub", "stub": st["id"], "mouth": [i_mouth_p, i_mouth_q],
                                   "bar": [ib_p, ib_q], "dir": d}
        k += 1
    # densify every segment (a point every `step`; a point between two fixed vertices is fixed at the linear height)
    D, Dh, Df, Dk, Dt, where = [], [], [], [], [], []
    m = len(out)
    for i in range(m):
        a, b = out[i], out[(i + 1) % m]
        where.append(len(D))
        D.append(a)
        Dh.append(hs[i])
        Df.append(fx[i])
        Dk.append(kind[i])
        Dt.append(tags[i])
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        nseg = int(math.ceil(L / step - 1e-9)) if L > step else 1
        for t_ in range(1, nseg):
            f = t_ / nseg
            D.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            both = fx[i] and fx[(i + 1) % m]
            Dh.append(hs[i] + (hs[(i + 1) % m] - hs[i]) * f if both else None)
            Df.append(both)
            seam = kind[i] in ("cut", "stub_far") and kind[(i + 1) % m] in ("cut", "stub_far") and \
                tags[i] is not None and tags[(i + 1) % m] is not None and tags[i][:2] == tags[(i + 1) % m][:2]
            Dk.append(("seam_" + kind[i]) if seam else "edge")
            Dt.append(None)
    for info in arm_info.values():
        for key in ("idx", "mouth", "bar"):
            if key in info:
                info[key] = [where[i] for i in info[key]]
    for name, info in arm_info.items():
        if info["kind"] == "stub":
            barriers[info["stub"]] = tuple(info["bar"])
    # the curb runs: maximal stretches that cross no route arm cut and no stub far edge
    N = len(D)
    excluded_edge = [False] * N            # edge i -> i+1 excluded from the curb
    for i in range(N):
        j = (i + 1) % N
        a_t, b_t = Dk[i], Dk[j]
        cutlike = ("cut", "seam_cut")
        farlike = ("stub_far", "seam_stub_far")
        if (a_t in cutlike and b_t in cutlike) or (a_t in farlike and b_t in farlike):
            excluded_edge[i] = True
    runs, ends = [], []
    s0 = next(i for i in range(N) if excluded_edge[(i - 1) % N] and not excluded_edge[i])
    i = s0
    cur = [i]
    for _ in range(N):
        if excluded_edge[i]:
            if len(cur) > 1:
                runs.append(cur)
            cur = []
        nxt = (i + 1) % N
        if not excluded_edge[i]:
            if not cur:
                cur = [i]
            cur.append(nxt)
        i = nxt
        if i == s0:
            break
    if len(cur) > 1:
        runs.append(cur)
    for r in runs:
        ends.append((Dt[r[0]], Dt[r[-1]]))
        for e in (Dt[r[0]], Dt[r[-1]]):
            if e is None or e[0] not in ("arm", "stub") or (e[0] == "arm" and e[2] == "C") or \
                    (e[0] == "stub" and e[2] == 1):
                raise PadError(f"a curb run ends on {e}, not on an arm's edge or a stub's far corner")
    return {"outline": D, "heights": Dh, "fixed": Df, "kind": Dk, "tags": Dt, "runs": runs, "run_ends": ends,
            "arms": arm_info, "barriers": barriers}


def outward_normals(outline):
    """per outline vertex the unit plan normal pointing OUT of a CCW polygon (right of the traversal), from the two
    adjacent segments' directions"""
    n = len(outline)
    out = []
    for i in range(n):
        a, b, c = outline[(i - 1) % n], outline[i], outline[(i + 1) % n]
        d1 = (b[0] - a[0], b[1] - a[1])
        d2 = (c[0] - b[0], c[1] - b[1])
        L1, L2 = math.hypot(*d1) or 1.0, math.hypot(*d2) or 1.0
        t = (d1[0] / L1 + d2[0] / L2, d1[1] / L1 + d2[1] / L2)
        Lt = math.hypot(*t)
        if Lt < 1e-9:
            t = (d2[0] / L2, d2[1] / L2)
            Lt = 1.0
        t = (t[0] / Lt, t[1] / Lt)
        out.append((t[1], -t[0]))
    return out


def run_stations(outline, deck_h, run, profile, first=None, last=None):
    """the curb + walk profile rows along one curb run (outline indices `run`): each station (p0..p3) at the outline
    vertex's deck height, swept along the outward normal; `first` / `last` (a route arm's own curb row, 4 points) replace
    the run's end stations exactly where the run starts / ends at a route arm"""
    nrm = outward_normals(outline)
    rows = []
    for k, i in enumerate(run):
        if k == 0 and first is not None:
            rows.append(tuple(tuple(p) for p in first))
            continue
        if k == len(run) - 1 and last is not None:
            rows.append(tuple(tuple(p) for p in last))
            continue
        x, z = outline[i]
        w = nrm[i]
        if k in (0, len(run) - 1):
            # a free run end (a stub's far corner): square to the run's own end segment, never splayed by the far edge
            a, b = (outline[run[0]], outline[run[1]]) if k == 0 else (outline[run[-2]], outline[run[-1]])
            d = (b[0] - a[0], b[1] - a[1])
            Ld = math.hypot(*d) or 1.0
            w = (d[1] / Ld, -d[0] / Ld)
        h = deck_h[i]
        rows.append(tuple((x + w[0] * o, h + dy, z + w[1] * o) for o, dy in profile))
    return rows


def fetch_heights(points_lonlat, cache_path, what):
    """3DEP 1 m at each (lon, lat), cached in cache_path ({key "lon,lat" (7 dp): metres}, with provenance); missing ones
    fetched (TLS verified, scripts.elevation.terrain_sample.sample_lonlat), never gap filled"""
    cache = {}
    prov = {"source": "USGS 3DEP 1 m bare earth (scripts.elevation.terrain_sample.sample_lonlat, TLS verified)",
            "units": "metres above NAVD88", "fetches": []}
    if cache_path.exists():
        d = json.loads(cache_path.read_text(encoding="utf-8"))
        cache = dict(d.get("h", {}))
        prov = d.get("_provenance", prov)

    def key(ll):
        return f"{ll[0]:.7f},{ll[1]:.7f}"
    need = [ll for ll in points_lonlat if key(ll) not in cache]
    if need:
        from scripts.elevation import terrain_sample as ts_mod
        vals = ts_mod.sample_lonlat(need, what)
        for ll, v in zip(need, vals):
            if v is None:
                raise PadError(f"3DEP returned no value at {ll} — never gap filled")
            cache[key(ll)] = round(float(v), 3)
        prov["fetches"].append({"utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "points": len(need), "what": what})
        cache_path.write_text(json.dumps({"_provenance": prov, "h": dict(sorted(cache.items()))}, indent=1),
                              encoding="utf-8")
    return [cache[key(ll)] for ll in points_lonlat], len(need)


def plan(project, offline=False):
    proj = Path(project)
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    decl = (cfg.get("route") or {}).get("junction_pads") or {}
    out_p = data / "pads.plan.json"
    if not decl:
        if out_p.exists():
            out_p.unlink()
        print("[pads] none declared (track.config.json route.junction_pads): nothing planned")
        return None
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import author_expansion as ae
    import expansion_pieces as ep
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    docs, designs = {}, {}
    pads = []
    for pid_, src in sorted(decl.items()):
        if src not in docs:
            docs[src], pcs = ep.load(proj / src)
            designs[src] = design_pads(docs[src], pcs)
        doc = docs[src]
        frame = ae.Frame(doc["frame"]["origin"])
        pad = designs[src].get(pid_)
        if pad is None:
            raise SystemExit(f"[pads] FATAL: {pid_} is not a pad of {src}")
        stubs = pad["stubs"]
        far = stub_far_points(pad, stubs)
        ll, keys = [], []
        for sid, pts in sorted(far.items()):
            for k, (x, z) in enumerate(pts):
                ll.append(frame.lonlat(x, z))
                keys.append((sid, k))
        if offline:
            hp = data / "pads.3dep.json"
            cache = json.loads(hp.read_text(encoding="utf-8"))["h"] if hp.exists() else {}
            vals = [cache.get(f"{a:.7f},{b:.7f}") for a, b in ll]
            if any(v is None for v in vals):
                raise SystemExit(f"[pads] FATAL: {pid_}: 3DEP not cached and --offline")
            nf = 0
        else:
            vals, nf = fetch_heights(ll, data / "pads.3dep.json", f"junction pad {pid_} stub far edges")
        elev0 = float(doc["frame"]["origin"]["elev_m"])
        sh = {}
        for (sid, k), v in zip(keys, vals):
            sh.setdefault(sid, [None, None, None])[k] = round(v - elev0 + LIFT_M, 3)
        # the far edge is held LEVEL across, at the 3DEP of its middle (on the stub's centre line): the two corners
        # stand on the curb lines, where 3DEP reads the gutter, the kerb or the verge — 0.9 m apart across the visitor-
        # centre entrance's 12 m (a 15 % cross-fall, a 25 % facet beside it on the first build)
        raw = {sid: list(v) for sid, v in sh.items()}
        sh = {sid: [v[1], v[1], v[1]] for sid, v in sh.items()}
        # each route arm's connector piece and which end stands on the cut
        arms = []
        for a in pad["arms"]:
            rec = {"name": a["name"], "kind": a["kind"], "cut_line_xz": a["cut_line_xz"]}
            if a["kind"] == "route":
                base = ep.PIECE_CONN[a["piece"]]
                cx = (a["cut_line_xz"][0][0] + a["cut_line_xz"][1][0]) / 2
                cz = (a["cut_line_xz"][0][1] + a["cut_line_xz"][1][1]) / 2
                best = None
                for c in conns:
                    if c["name"] != base and not c["name"].startswith(base + "#"):
                        continue
                    P = c["points_xyz_m"]
                    for end, q in (("start", P[0]), ("end", P[-1])):
                        d = math.hypot(q[0] - cx, q[2] - cz)
                        if best is None or d < best[0]:
                            best = (d, c["name"], end)
                if best is None or best[0] > SNAP_MAX_M:
                    raise SystemExit(f"[pads] FATAL: {pid_} arm {a['name']}: no {base} piece ends on its cut "
                                     f"(nearest {best})")
                rec.update({"connector": best[1], "end": best[2], "end_off_m": round(best[0], 4)})
            else:
                rec["stub"] = a["stub"]
            arms.append(rec)
        src_pad = next(p for p in doc["pads"] if p["id"] == pid_)
        pads.append({"id": pid_, "source": src, "node_xz": pad["node_xz"], "z_3dep_m": src_pad.get("z_3dep_m"),
                     "y_3dep_m": src_pad.get("y_3dep_m"), "arms": arms,
                     "stubs": {sid: dict(stubs[sid], far_xz=[list(map(lambda v: round(v, 4), p)) for p in far[sid]],
                                         far_deck_y=sh[sid], far_3dep_deck_y=raw[sid]) for sid in far},
                     "design": pad, "corners": pad["corners"],
                     "stub_length_m": STUB_LENGTH_M, "tail_m": TAIL_M})
        print(f"[pads] {pid_}: {sum(1 for a in arms if a['kind'] == 'route')} route arm(s) "
              f"({', '.join(a['connector'] + ' ' + a['end'] for a in arms if a['kind'] == 'route')}), "
              f"{len(far)} stub arm(s); 3DEP at the stub far edges ({nf} fetched)")
    out_p.write_text(json.dumps({"_doc": "tools/junction_pad.py plan (ledger 0054 P3 step 2): the junction pads to "
                                         "author (tools/author_junction_pad_blend.py)", "pads": pads}, indent=1),
                     encoding="utf-8")
    print(f"[pads] {len(pads)} pad(s) planned -> data/pads.plan.json")
    return pads


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) >= 2 and argv[0] == "plan":
        plan(argv[1], offline="--offline" in argv)
        return 0
    raise SystemExit("usage: python tools/junction_pad.py plan <project> [--offline]")


if __name__ == "__main__":
    raise SystemExit(main())
