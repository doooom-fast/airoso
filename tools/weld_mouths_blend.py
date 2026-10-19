"""Weld every side-street MOUTH onto its host — mitre the connector's end onto the host's edge line and warp
its last BLEND_M onto the host deck (road, curb/sidewalk and markings). The geometry and its reasons are in
tools/mouth_weld.py; this is the Blender half.

Runs INSIDE Blender, right after build_loop_blend rebuilt loop.blend with the trimmed connectors and BEFORE
seat_terrain (which seats the terrain under the WELDED deck) / median / gap_mouths:

    blender --background --python-exit-code 1 --python-expr "$V021_SHIM" \\
        --python tools/weld_mouths_blend.py -- <project-dir>

The assembler's package must be importable as `scripts` (tools/ship_sd.sh's V021_SHIM registers airoso's
tracks/san-diego-lake-murray/scripts-v021 under that name, as for build_loop_blend): its own ribbon + smooth modules
rebuild every connector's ROAD / CURB / MARKINGS / YLINE block, and the mesh must match them vertex for vertex
before anything moves — the assembler's vertex order is the contract (as gap_mouths_blend relies on for CURB).
Any mismatch stops loudly: never weld a mesh whose layout we only assume.

RIDGES: every warped ROAD quad keeps the diagonal whose ends stand higher (see _ridge_diagonals) — the grass under a
twisted quad stays under it.

FOLDS first (2026-10-11, the Navajo v2314 "other deck above the strip" 0.458 m): the assembler sweeps every lateral
line at its offset whatever the corner's radius, so on the inside of a corner tighter than the half-width the edge
runs backwards and the ribbon overlaps itself. Every ribbon (mainline + connectors) has each lateral line (ROAD edges,
the four CURB profile lines a side, the white paint) cut at its own self-intersection (tools/mouth_weld.unfold_line);
the inside of the corner becomes a fan from the centre rows to that point (its apex at the higher leg's height: a
cone, every crease from a centre row a ridge); the paint near a fold is laid back onto the deck it now has. A line
still running backwards after it stops the weld.

Self-check before saving (exit 1 on any): every end row within mouth_weld.SELF_TOL_M of the host deck; no
connector vertex inside the host's pavement above the host deck (+ the markings' lift) by more than that; no
ribbon quad of the welded rows folded or collapsed. A second run on a welded scene is refused (the ROAD object
carries the `mouth_weld` stamp); rebuild loop.blend first.

Writes loop.blend, data/mouth_welds.json (per mouth: cut arcs, rows re-spread / touched, the end row's height
change and its deviation from the host deck before / after) and data/median_bands.json (a divided trunk's
connector island follows the warped centre line).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mouth_weld as mw  # noqa: E402

LAYOUT_TOL_M = 2e-3
STAMP = "mouth_weld"


def _read(ob):
    me = ob.data
    a = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", a)
    a = a.reshape(-1, 3)
    return np.stack([a[:, 0], a[:, 2], a[:, 1]], axis=1)      # Blender (x, z_north, y_up) -> local (x, y, z)


def _write(ob, loc):
    me = ob.data
    b = np.stack([loc[:, 0], loc[:, 2], loc[:, 1]], axis=1).reshape(-1)
    me.vertices.foreach_set("co", b.astype(np.float32))
    me.update()


def _ridge_diagonals(ob, quads):
    """RIDGE, NOT VALLEY. The warp twists the connector's quads (the cross-fall eases from the host's to level over
    BLEND_M: 0.05-0.08 m per 3 m row on Del Cerro's 23 m trunk), and a twisted quad's diagonal is a crease: a valley
    when it joins the two LOWER corners. The kn5 prep pins every grass vertex under the road 0.02 m under it; between
    those vertices the grass is a plane, and over a valley crease that plane came through the road (+0.008 m, 6-12 m
    up the Del Cerro W approach, measured on the built road). Each quad (A, B on row j; D, C on row j+1) keeps the
    diagonal whose ends stand higher, so every crease of the warped rows is a ridge the grass stays under.
    Returns the number of diagonals turned."""
    import bmesh
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    turn = []
    for A, B, Cc, D in quads:
        vA, vB, vC, vD = (bm.verts[i] for i in (A, B, Cc, D))
        eAC, eBD = bm.edges.get((vA, vC)), bm.edges.get((vB, vD))
        if eAC is not None and eBD is None:
            e, cur, other = eAC, vA.co.z + vC.co.z, vB.co.z + vD.co.z
        elif eBD is not None and eAC is None:
            e, cur, other = eBD, vB.co.z + vD.co.z, vA.co.z + vC.co.z
        else:
            continue
        if other > cur + 2e-4 and len(e.link_faces) == 2 and all(len(f.verts) == 3 for f in e.link_faces):
            turn.append(e)
    if turn:
        bmesh.ops.rotate_edges(bm, edges=list(dict.fromkeys(turn)), use_ccw=False)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return len(turn)


def _dev(mesh_block, ref):
    r = np.asarray(ref, dtype=np.float64)
    if r.shape != mesh_block.shape:
        return float("inf")
    return float(np.max(np.abs(mesh_block - r))) if len(r) else 0.0


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    try:
        from scripts.geometry import ribbon as wr, smooth as ws   # the assembler's (registered by the caller)
    except ImportError as e:
        raise SystemExit(f"[weld] FATAL: the assembler's scripts.geometry is not importable ({e}) — run with "
                         "tools/ship_sd.sh's --python-expr \"$V021_SHIM\"")
    mouths = json.loads((data / "mouths.json").read_text(encoding="utf-8"))["mouths"]
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    # ledger 0054 P1 (opt-in): route.weld_exact_deck — connector-name prefixes whose mouths read the host deck off the
    # host's triangles (mouth_weld.ExactHostDeck), for wide mouths on a corner's fanned outer edge; absent = as before
    cfgp = proj / "track.config.json"
    exact_prefixes = []
    if cfgp.exists():
        exact_prefixes = [str(x) for x in (json.loads(cfgp.read_text(encoding="utf-8")).get("route", {})
                                           .get("weld_exact_deck") or [])]
    main_pts = [tuple(p) for p in local["points_xyz_m"]]
    lay = mw.mesh_layout(main_pts, conns)
    cdict = {c["name"]: c for c in conns}

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    obs = {n: bpy.data.objects.get(n) for n in ("ROAD", "CURB", "MARKINGS", "YLINE")}
    for n, ob in obs.items():
        if ob is None:
            raise SystemExit(f"[weld] FATAL: no {n} object in loop.blend")
    if STAMP in obs["ROAD"].keys():
        raise SystemExit("[weld] FATAL: loop.blend is already welded (ROAD carries the mouth_weld stamp) — rebuild "
                         "it with build_loop_blend first; the weld runs once per rebuild")
    V = {n: _read(ob) for n, ob in obs.items()}
    if len(V["ROAD"]) != lay["_road_total"] or len(V["CURB"]) != lay["_curb_total"]:
        raise SystemExit(f"[weld] FATAL: ROAD {len(V['ROAD'])} / CURB {len(V['CURB'])} verts, the assembler's layout "
                         f"says {lay['_road_total']} / {lay['_curb_total']} — the row order changed; not welding")

    # ---- the layout contract: every connector block equals the assembler's own sweep of it, vertex for vertex
    mk_total = {"MARKINGS": 0, "YLINE": 0}
    recon = {}
    for c in conns:
        cpts = [tuple(p) for p in c["points_xyz_m"]]
        if len(cpts) < 2:
            raise SystemExit(f"[weld] FATAL: connector {c['name']} has < 2 points (the assembler skips it; "
                             "the layout would shift)")
        cpts = ws.smooth_centerline(cpts, sigma_pts=1.5, passes=1, sigma_y_pts=1.0)
        cw = list(c["widths_m"])
        rib = [(x, y + 0.10, z) for (x, y, z) in wr.road_ribbon(cpts, cw)["vertices"]]
        ker = wr.curb_sidewalk(cpts, cw, lift=0.10, curb_h=0.14, curb_face_w=0.08, sidewalk_w=1.5, grade_w=1.2,
                               grass_clearance=0.10)["vertices"]
        cmk = wr.connector_markings(cpts, cw, c.get("stub"))     # the assembler's own call (a phase-5 stub: its street's paint)
        mk = {"MARKINGS": [(x, y + 0.115, z) for (x, y, z) in cmk["white"]["vertices"]],
              "YLINE": [(x, y + 0.115, z) for (x, y, z) in cmk["yellow"]["vertices"]]}
        recon[c["name"]] = mk
        b = lay[c["name"]]
        d_road = _dev(V["ROAD"][b["road"]:b["road"] + 3 * b["rows"]], rib)
        d_curb = _dev(V["CURB"][b["curb"]:b["curb"] + 2 * mw.CURB_P * b["rows"]], ker)
        if d_road > LAYOUT_TOL_M or d_curb > LAYOUT_TOL_M:
            raise SystemExit(f"[weld] FATAL: connector {c['name']}: the mesh block differs from the assembler's sweep "
                             f"(ROAD {d_road:.4f} m, CURB {d_curb:.4f} m) — the row order changed; not welding")
        for n in mk_total:
            mk_total[n] += len(mk[n])
    mk_start = {}
    for n in ("MARKINGS", "YLINE"):
        s = len(V[n]) - mk_total[n]
        if s < 0:
            raise SystemExit(f"[weld] FATAL: {n} holds {len(V[n])} verts < the connectors' {mk_total[n]}")
        for c in conns:
            blk = V[n][s:s + len(recon[c["name"]][n])]
            d = _dev(blk, recon[c["name"]][n])
            if d > LAYOUT_TOL_M:
                raise SystemExit(f"[weld] FATAL: {n} block of {c['name']} differs from the assembler's markings by "
                                 f"{d:.4f} m — the append order changed; not welding")
            mk_start[(n, c["name"])] = s
            s += len(recon[c["name"]][n])
    # the mainline: ROAD centre rows on the persisted smoothed centreline, CURB lane edges ON the ROAD edges
    mb = lay["MAINLINE"]
    cen = V["ROAD"][1:3 * mb["rows"]:3]
    ref = np.array([(p[0], p[1] + 0.10, p[2]) for p in main_pts[:mb["rows"]]])
    if _dev(cen, ref) > LAYOUT_TOL_M:
        raise SystemExit(f"[weld] FATAL: mainline ROAD centre rows are off centerline.local.json by {_dev(cen, ref):.4f} m")
    for name in ["MAINLINE"] + [c["name"] for c in conns]:
        b = lay[name]
        for side, lane in ((1, 0), (-1, 2)):
            e = V["ROAD"][[mw.road_index(lay, name, r, lane) for r in range(b["rows"])]]
            p0 = V["CURB"][[mw.curb_index(lay, name, r, side, 0) for r in range(b["rows"])]]
            if _dev(e, p0) > LAYOUT_TOL_M:
                raise SystemExit(f"[weld] FATAL: {name}: CURB side {side:+d} lane edge is off the ROAD edge by "
                                 f"{_dev(e, p0):.4f} m — the curb block order changed; not welding")
    print(f"[weld] layout contract holds: mainline {mb['rows']} rows + {len(conns)} connector blocks in ROAD / CURB / "
          f"MARKINGS / YLINE")

    def rows_of(name):
        b = lay[name]
        R = V["ROAD"]
        return [tuple(tuple(R[b["road"] + 3 * r + k]) for k in range(3)) for r in range(b["rows"])]

    # ---- FOLDS (before the mouths: a mouth's host deck is read off the unfolded rows). The assembler sweeps every
    # lateral line at its offset whatever the corner's radius, so the inside of a corner tighter than the offset
    # runs backwards and the ribbon overlaps itself: two ROAD sheets up to 0.46 m apart (Navajo / Jackson v2317-2320
    # under the race strip at v2314; College / Navajo v1512-1515; the hairpin v767-771; v3295-3297; the seam). Each
    # line (ROAD edges, the four CURB profile lines a side, the white paint) is cut at its own self-intersection.
    fold_report = {}
    mk_main_end = {n: len(V[n]) - mk_total[n] for n in ("MARKINGS",)}
    for name in ["MAINLINE"] + [c["name"] for c in conns]:
        b = lay[name]
        rows = rows_of(name)
        Crow = [r[1] for r in rows]
        closed = b["closed"]
        cols, left, levelled = [], [], []
        strict = name == "MAINLINE"      # the race strips + kerbs sit on it: every mainline fold must be mended
        # ledger 0050: the MAINLINE's swallowtail pinches are LEVELLED — X at the midpoint of its legs, each leg's last
        # mw.FOLD_LEVEL_ROWS rows eased to it (heights only). Connectors keep the 2026-10-11 rule (higher leg, nothing
        # eased). The half-jump cap (no_route's wall band) applies to the lines that carry walls and the curb face:
        # the ROAD edges and curb p0 (lane edge) / p1 (curb top); p2 (sidewalk back) / p3 (grass meet) level uncapped
        # (measured at Navajo / Jackson 0.317 / 0.359 > 0.28 — capped, they stopped the build: the review's BLOCKER 1)
        level = name == "MAINLINE"

        def _unfold(E, cap, tag):
            rep = []
            newE, col, lf = mw.unfold_line(E, Crow, closed, strict=strict, level=level,
                                           half_jump_max=mw.FOLD_HALF_JUMP_MAX_M if cap else None, report=rep)
            if level:
                bad = mw.check_levelled(E, newE, Crow, closed, col)
                if bad:
                    raise SystemExit(f"[weld] FATAL: {name} {tag}: the levelled fold fails its self-check: {bad[:3]}")
            for q in rep:
                levelled.append({"line": list(tag), "k": q["k"], "l": q["l"],
                                 "X": [round(float(c_), 4) for c_ in q["X"]], "y_k": round(q["y_k"], 4),
                                 "y_l": round(q["y_l"], 4), "half_jump": round(q["half_jump"], 4), "capped": bool(cap),
                                 "max_ease_m": round(max((abs(d) for _j, d in q["eased"]), default=0.0), 4)})
                print(f"[weld] LEVEL {name} {tag[0]} {' '.join(str(x) for x in tag[1:])}: pinch rows {q['k'] % b['rows']}.."
                      f"{(q['l'] + 1) % b['rows']} legs {q['y_k']:.3f} / {q['y_l']:.3f} -> X {q['h']:.3f} "
                      f"(half-jump {q['half_jump']:.3f}{'' if cap else ', uncapped'}; {len(q['eased'])} rows eased, "
                      f"max {max((abs(d) for _j, d in q['eased']), default=0.0):.3f} m)")
            return newE, col, lf

        for lane in (0, 2):
            E = [r[lane] for r in rows]
            newE, col, lf = _unfold(E, True, ("road", lane))
            left += [("road", lane, a, b_) for a, b_ in lf]
            for r in range(b["rows"]):
                if newE[r] != E[r]:
                    V["ROAD"][mw.road_index(lay, name, r, lane)] = newE[r]
            cols += [("road", lane, k, l) for k, l, _x in col]
        for s in (1, -1):
            for p in range(mw.CURB_P):
                ids = [mw.curb_index(lay, name, r, s, p) for r in range(b["rows"])]
                E = [tuple(V["CURB"][i]) for i in ids]
                newE, col, lf = _unfold(E, p <= 1, ("curb", s, p))
                left += [("curb", s, p, a, b_) for a, b_ in lf]
                for r, i in enumerate(ids):
                    if newE[r] != E[r]:
                        V["CURB"][i] = newE[r]
                cols += [("curb", s, p, k, l) for k, l, _x in col]
        if left:
            print(f"[weld] FOLDS {name}: {len(left)} run(s) left as built (no cut mends them — the line overlaps itself "
                  f"across a hairpin narrower than the ribbon): {left[:6]}")
        if not cols:
            fold_report[name] = {"cuts": [], "left": [list(x) for x in left], "paint_verts_moved": 0}
            continue
        # the white paint near the folds: each painted vertex on its row's cross line, its own line unfolded
        fold_rows = sorted({r % b['rows'] for c in cols for r in range(c[-2], c[-1] + 2)})
        lo_, hi_ = (0, mk_main_end["MARKINGS"]) if name == "MAINLINE" else \
            (mk_start[("MARKINGS", name)], mk_start[("MARKINGS", name)] + len(recon[name]["MARKINGS"]))
        near = {}
        for r in fold_rows:
            for q in range(r - 12, r + 13):
                if closed or 0 <= q < b["rows"]:
                    near[q % b["rows"]] = True
        cell = {}
        for q in near:
            c = Crow[q]
            cell.setdefault((int(c[0] // 20.0), int(c[2] // 20.0)), []).append(q)
        nl = [None] * b["rows"]
        for q in range(b["rows"]):
            L_, C_ = rows[q][0], rows[q][1]
            h = math.hypot(L_[0] - C_[0], L_[2] - C_[2]) or 1e-9
            nl[q] = ((L_[0] - C_[0]) / h, (L_[2] - C_[2]) / h, h, math.hypot(rows[q][2][0] - C_[0], rows[q][2][2] - C_[2]))
        cache = {}
        moved_paint = 0
        # this ribbon's ROAD as it now stands (unfolded + re-graded), for the paint heights
        rb0, rb1 = lay[name]["road"], lay[name]["road"] + 3 * b["rows"]
        rpolys = [tuple(pg.vertices) for pg in obs["ROAD"].data.polygons
                  if rb0 <= min(pg.vertices) and max(pg.vertices) < rb1]
        rbvh = BVHTree.FromPolygons([(float(q_[0]), float(q_[2]), float(q_[1])) for q_ in V["ROAD"]], rpolys)

        def paint_deck(x, z):
            hit = rbvh.ray_cast((x, z, 10000.0), (0.0, 0.0, -1.0))
            return None if hit[0] is None else float(hit[0].z)
        for vi in range(lo_, hi_):
            v = V["MARKINGS"][vi]
            ck = (int(v[0] // 20.0), int(v[2] // 20.0))
            cand = [q for dx in (-1, 0, 1) for dz in (-1, 0, 1) for q in cell.get((ck[0] + dx, ck[1] + dz), ())]
            hit = None
            for q in cand:
                nx, nz, hl, hr = nl[q]
                dx, dz = v[0] - Crow[q][0], v[2] - Crow[q][2]
                if abs(dx * nz - dz * nx) < 2e-3:
                    o = dx * nx + dz * nz
                    if -hr - 0.5 <= o <= hl + 0.5:
                        hit = (q, o)
                        break
            if hit is None:
                continue
            q, o = hit
            half = nl[q][2] if o >= 0 else nl[q][3]
            dlt = half - abs(o)
            key = ("edge", round(dlt, 3), o >= 0) if abs(dlt - 0.55) <= 0.07 else ("fixed", round(o, 3))
            if key not in cache:
                pts = []
                for r in range(b["rows"]):
                    nx, nz, hl, hr = nl[r]
                    oo = o if key[0] == "fixed" else ((hl - dlt) if o >= 0 else -(hr - dlt))
                    pts.append((Crow[r][0] + nx * oo, Crow[r][1] + float(v[1] - rows[q][1][1]), Crow[r][2] + nz * oo))
                newP, col, _lf = mw.unfold_line(pts, Crow, closed, strict=False)
                mm = b["rows"]
                cache[key] = {r % mm: newP[r % mm] for kk, ll, _x in col for r in range(kk + 1, ll + 1)}
            nv = cache[key].get(q, tuple(v))
            hy = paint_deck(nv[0], nv[2])               # the paint lies on the re-graded deck, wherever it moved
            nv = (nv[0], (hy + mw.MARK_LIFT_M) if hy is not None else nv[1], nv[2])
            if any(abs(float(a_) - float(b_)) > 1e-6 for a_, b_ in zip(nv, v)):
                V["MARKINGS"][vi] = nv
                moved_paint += 1
        # self-check: no lateral line of this ribbon still runs backwards
        rows2 = rows_of(name)
        for lane in (0, 2):
            still = mw.backward_segments([r[lane] for r in rows2], Crow, closed)
            known = {j % b["rows"] for x in left if x[0] == "road" and x[1] == lane for j in range(x[-2], x[-1] + 1)}
            if [j for j in still if j not in known]:
                raise SystemExit(f"[weld] FATAL: {name} ROAD lane {lane} still folds after the unfold at segments "
                                 f"{[j for j in still if j not in known][:8]}")
        fold_report[name] = {"cuts": [list(c) for c in cols], "left": [list(x) for x in left],
                             "paint_verts_moved": moved_paint,
                             # ledger 0050: one record per levelled pinch (line, k, l, X, legs, half-jump, cap)
                             "levelled": levelled, "level_rows": mw.FOLD_LEVEL_ROWS if level else 0,
                             "rows": b["rows"]}
        print(f"[weld] FOLDS {name}: {len(cols)} line cut(s) at rows "
              f"{sorted({(c[-2] % b['rows'], c[-1] % b['rows']) for c in cols if c[0] == 'road'})} (ROAD) + CURB; "
              f"{moved_paint} paint verts")

    report, fails = [], []
    island_dy = {}           # piece -> [(old C line end-first, dy per row, K, halves)]
    ridge_quads = []         # ROAD quads (A, B, C, D) of every warped row pair
    for mo in mouths:
        piece, end, host, side = mo.get("piece"), mo.get("end"), mo["host"], int(mo["side"])
        tag = f"{mo['connector']} -> {host} v{mo['host_vertex']}"
        if piece is None or end not in ("start", "end"):
            raise SystemExit(f"[weld] FATAL: mouth {tag}: no piece/end in mouths.json (re-run tools/trim_connectors.py)")
        if piece not in lay or host not in lay:
            raise SystemExit(f"[weld] FATAL: mouth {tag}: piece {piece!r} or host {host!r} not in the mesh layout")
        b = lay[piece]
        order = list(range(b["rows"])) if end == "start" else list(range(b["rows"] - 1, -1, -1))
        rows_old = [rows_of(piece)[r] for r in order]
        hrows = rows_of(host)
        cx, _cy, cz = mo["cut_xyz"]
        Deck = mw.ExactHostDeck if any(str(mo["connector"]).startswith(px) for px in exact_prefixes) else mw.HostDeck
        deck = Deck(hrows, mw.host_window(hrows, lay[host]["closed"], cx, cz))
        far = rows_old[min(len(rows_old) - 1, 6)][1]
        if (1 if deck.project(far[0], far[2])[3] >= 0 else -1) != side:
            raise SystemExit(f"[weld] FATAL: mouth {tag}: the piece approaches from side "
                             f"{-side:+d}, mouths.json says {side:+d}")
        lines, inset, h = {}, {}, {}
        for lane in range(3):
            lines[("road", lane)] = [r[lane] for r in rows_old]
            inset[("road", lane)] = mw.OVERLAP_M
            h[("road", lane)] = 0.0
        C = V["CURB"]
        for s in (1, -1):
            edge_lane = 0 if s == 1 else 2
            for p in range(mw.CURB_P):
                pts = [tuple(C[mw.curb_index(lay, piece, r, s, p)]) for r in order]
                lines[("curb", s, p)] = pts
                inset[("curb", s, p)] = mw.CURB_INSET_M
                h[("curb", s, p)] = pts[0][1] - rows_old[0][edge_lane][1]
        before = []
        for lane in range(3):
            q = rows_old[0][lane]
            if deck.inside(q[0], q[2]):
                before.append(q[1] - deck.at(q[0], q[2]))
        try:
            res = mw.weld_end(lines, deck, side, inset, h)
        except mw.WeldError as e:
            raise SystemExit(f"[weld] FATAL: mouth {tag}: {e}")
        new, K, J = res["new"], res["K"], res["J"]
        rows_new = [tuple(new[("road", lane)][j] for lane in range(3)) for j in range(len(order))]
        # write ROAD + CURB
        for j, r in enumerate(order[:K]):
            for lane in range(3):
                V["ROAD"][mw.road_index(lay, piece, r, lane)] = new[("road", lane)][j]
            for s in (1, -1):
                for p in range(mw.CURB_P):
                    C[mw.curb_index(lay, piece, r, s, p)] = new[("curb", s, p)][j]
        # markings ride along (their rows are the ribbon's rows)
        moved_mk = 0
        reach = max(mw.arc_lengths([r[1] for r in rows_old[:K + 1]])[-1], 1.0) + 25.0
        for n in ("MARKINGS", "YLINE"):
            s0 = mk_start[(n, piece)]
            for vi in range(s0, s0 + len(recon[piece][n])):
                v = tuple(V[n][vi])
                if math.hypot(v[0] - cx, v[2] - cz) > reach:
                    continue
                nv = mw.map_marking(v, rows_old, rows_new, K)
                if nv is not None:
                    V[n][vi] = nv
                    moved_mk += 1
        # self-check (on what was written)
        end_dev = max(abs(rows_new[0][lane][1] - deck.at(rows_new[0][lane][0], rows_new[0][lane][2]))
                      for lane in range(3))
        above = []
        for j, r in enumerate(order[:K]):
            for lane in range(3):
                q = V["ROAD"][mw.road_index(lay, piece, r, lane)]
                if deck.inside(q[0], q[2], 0.01) and q[1] > deck.at(q[0], q[2]) + mw.SELF_TOL_M:
                    above.append(("ROAD", j, lane, round(float(q[1] - deck.at(q[0], q[2])), 3)))
            for s in (1, -1):
                for p in range(mw.CURB_P):
                    q = C[mw.curb_index(lay, piece, r, s, p)]
                    if deck.inside(q[0], q[2], 0.01) and q[1] > deck.at(q[0], q[2]) + mw.SELF_TOL_M:
                        above.append(("CURB", j, s, p, round(float(q[1] - deck.at(q[0], q[2])), 3)))
        for n in ("MARKINGS", "YLINE"):
            s0 = mk_start[(n, piece)]
            for vi in range(s0, s0 + len(recon[piece][n])):
                q = V[n][vi]
                if math.hypot(q[0] - cx, q[2] - cz) <= reach and deck.inside(q[0], q[2], 0.01) and \
                        q[1] > deck.at(q[0], q[2]) + mw.MARK_LIFT_M + mw.SELF_TOL_M:
                    above.append((n, vi, round(float(q[1] - deck.at(q[0], q[2])), 3)))
        a_old, a_new = mw.quad_areas(rows_old[:K + 1]), mw.quad_areas(rows_new[:K + 1])
        # a quad already collapsed by the unfold (zero area) is not a new fold
        folds = [i for i, (p, q) in enumerate(zip(a_old, a_new)) if abs(p) >= 1e-4 and (p * q <= 0 or abs(q) < 1e-4)]
        rec = {"connector": mo["connector"], "piece": piece, "end": end, "host": host, "side": side,
               "host_vertex": mo["host_vertex"], "angle_deg": mo.get("angle_deg"), "host_grade": mo.get("host_grade"),
               "rows_respread": J, "rows_touched": K, "markings_moved": moved_mk,
               **({"deck": "exact (route.weld_exact_deck)"} if Deck is mw.ExactHostDeck else {}),
               "cut_arc_m": {f"{k[0]}{''.join('%+d' % v for v in k[1:])}": round(v, 3) for k, v in res["u_x"].items()},
               "end_dy_m": [round(res["dy_end"][("road", lane)], 3) for lane in range(3)],
               "end_vs_host_before_m": [round(v, 3) for v in before],
               "end_vs_host_after_max_m": round(end_dev, 4),
               "above_host_after": above[:12], "folds": folds[:12]}
        report.append(rec)
        print(f"[weld] {piece} ({end}) -> {host} side {side:+d}: angle {mo.get('angle_deg')} deg, grade "
              f"{100 * (mo.get('host_grade') or 0):+.2f} %; road cut arcs L/C/R "
              f"{res['u_x'][('road', 0)]:+.2f}/{res['u_x'][('road', 1)]:+.2f}/{res['u_x'][('road', 2)]:+.2f} m, "
              f"curb ends {res['u_x'][('curb', 1, 3)]:+.2f}/{res['u_x'][('curb', -1, 3)]:+.2f} m; {J} rows re-spread, "
              f"{K} warped; end row L/C/R dy {rec['end_dy_m']}; end vs host before "
              f"{rec['end_vs_host_before_m']} -> after max {end_dev:.4f} m; {moved_mk} marking verts")
        if end_dev > mw.SELF_TOL_M:
            fails.append(f"{tag}: end row {end_dev:.3f} m off the host deck")
        if above:
            fails.append(f"{tag}: {len(above)} connector verts above the host deck inside its pavement, e.g. {above[:3]}")
        if folds:
            fails.append(f"{tag}: {len(folds)} ribbon quads folded/collapsed in the welded rows {folds[:6]}")
        for j in range(min(K, len(order) - 1)):
            r0, r1 = order[j], order[j + 1]
            for a, bb in ((0, 1), (1, 2)):
                ridge_quads.append((mw.road_index(lay, piece, r0, a), mw.road_index(lay, piece, r0, bb),
                                    mw.road_index(lay, piece, r1, bb), mw.road_index(lay, piece, r1, a)))
        # (a piece shorter than the warp — a phase-5 stub, ledger 0054 — has every row warped: K == its row count)
        island_dy.setdefault(piece, []).append(
            ([r[1] for r in rows_old[:K + 1]], [rows_new[j][1][1] - rows_old[j][1][1] for j in range(min(K + 1, len(rows_new)))],
             [math.hypot(r[0][0] - r[1][0], r[0][2] - r[1][2]) for r in rows_old[:K + 1]]))

    if fails:
        for f in fails:
            print(f"[weld] SELF-CHECK FAIL: {f}")
        raise SystemExit(f"[weld] FATAL: {len(fails)} mouth(s) failed the weld self-check — loop.blend NOT saved")

    for n, ob in obs.items():
        _write(ob, V[n])
    turned = _ridge_diagonals(obs["ROAD"], ridge_quads)
    print(f"[weld] {turned} of {len(ridge_quads)} warped ROAD quads turned to their ridge diagonal")
    obs["ROAD"][STAMP] = json.dumps({"mouths": len(report), "ridge_diagonals_turned": turned})
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))

    # the divided trunk's island follows its warped centre line (median_bands.json connector_islands)
    bp = data / "median_bands.json"
    lifted = 0
    if bp.exists():
        bands = json.loads(bp.read_text(encoding="utf-8"))
        for ci in bands.get("connector_islands", []):
            hits = [z for pn, zs in island_dy.items() if pn == ci["name"] or pn.startswith(ci["name"] + "#") for z in zs]
            if not hits:
                continue
            pts = ci["points_xyz_m"]
            for q, p in enumerate(pts):
                for cl, dys, halves in hits:
                    best = None
                    for j in range(len(cl) - 1):
                        a, bb = cl[j], cl[j + 1]
                        dx, dz = bb[0] - a[0], bb[2] - a[2]
                        L2 = dx * dx + dz * dz
                        if L2 < 1e-12:
                            continue
                        t = ((p[0] - a[0]) * dx + (p[2] - a[2]) * dz) / L2
                        if t < 0.0 or t > 1.0:
                            continue
                        d = math.hypot(p[0] - (a[0] + t * dx), p[2] - (a[2] + t * dz))
                        if d <= halves[j] and (best is None or d < best[0]):
                            best = (d, dys[j] * (1 - t) + dys[j + 1] * t)
                    if best is not None and abs(best[1]) > 1e-4:
                        pts[q] = [p[0], round(p[1] + best[1], 4), p[2]]
                        lifted += 1
                        break
        bp.write_text(json.dumps(bands), encoding="utf-8")
    (data / "mouth_welds.json").write_text(json.dumps({"mouths": report, "folds": fold_report,
                                                       "ridge_diagonals_turned": turned,
                                                       "island_points_moved": lifted}, indent=1), encoding="utf-8")
    print(f"[weld] {len(report)} mouth(s) welded, self-check clean; {lifted} connector-island point(s) follow the "
          f"warped centre; saved loop.blend + data/mouth_welds.json")


main()
