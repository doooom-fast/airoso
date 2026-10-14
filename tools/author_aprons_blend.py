"""Author every declared corner APRON and MOUTH FILL into loop.blend (ledger 0054 P1 fix round; EXPANSION-PLAN A5 /
P3). Opt-in: track.config.json route.aprons = {apron id: authored file} (e.g. {"AP1": "data/expansion.north.json"}) and
route.mouth_fill = [connector-name prefixes]; both absent, this prints one line and touches nothing (loop.blend is not
even saved).

MOUTH FILL (tools/apron.mouth_fill has the reasons): for each mouth of a listed connector the connector's ROAD strips
from its end out to its first row wholly outside the host are taken out (faces only — the assembler's vertex order is
a contract later passes read) and one piece, 1ROAD_mouthfill_<k>, takes their place: its outline the host's own edge
between the connector's two road-edge crossings, those edges out to that row, and the row; every outline vertex an
existing vertex (or a point on an existing edge), the inside the soap film between them. No road then lies over the
host's pavement but the host's. The paint over it is laid on it again (+ the markings' lift), and paint the fill left
standing inside the host on the host's deck.

The geometry and its reasons are in tools/apron.py. In the scene, after weld_mouths_blend + seat_terrain_blend (it
reads the WELDED rows and seats the ground the seat pass left) and before triangulate_terrain_blend / gap_mouths_blend:

  1ROAD_apron_<id>       the apron deck: the outline (P0, the stub's edge rows, the return arc, the host's edge rows)
                         + interior points every 1 m, triangulated by Blender's constrained Delaunay
                         (mathutils.geometry.delaunay_2d_cdt, the outline as constraint edges, inside only); heights:
                         the existing edge vertices exactly on both seams, the rest the cotangent-Laplace film between
                         them (tools/apron.harmonic_heights)
  1KERB_sidewalk_ap<id>  the return curb + walk along the arc (build_loop_blend's curb_sidewalk profile), first
                         station = the stub's own curb profile at T, last = the host's at E_row
  CURB                   the stub's curb + sidewalk faces on the apron side from its cut out to T are deleted (they
                         stood on the new pavement); the vertices stay (the assembler's layout is a contract)
  MARKINGS / YLINE       paint faces lying wholly inside the apron are deleted (the stub's edge line ran there)
  TERRAIN                halved to <= SEAT_EDGE_M under the apron and the return's walk + blend band, then seated by
                         tools/seat_terrain_blend.py's verge rule (pinned edge - 0.16 m under the pavement and walk,
                         blended back to its own height across 8 m: pulled down where it stood over the verge, lifted
                         only from a deep dip) — the kn5 prep then pins it under the deck as everywhere else

Writes data/aprons.json (per apron: the piece / host / sides, P0 / T / E, the return's R and its entry angle,
the arc, the outline, the host rows the apron opens [P0's row .. E's row], what was deleted). gap_mouths_blend opens
the host's walk over those rows, barrier_bands declares the mouth over them, verify_mouths judges the apron's seams,
make_treefx keeps plants off it and author_lamps_blend moves a post standing in it behind the return curb.

Self-check (exit 1, loop.blend NOT saved): every outline vertex on a seam equals the existing vertex; no apron vertex
above the host deck (+0.01 m) within 0.5 m of the host edge; no deck triangle steeper than the steeper of the two
roads it joins (their steepest grade along the seams) + 2 % [invented]; the CDT covering the outline; the curb's ends on
the road edges at T / E_row (the layout contract); the return's R in the dossier's 20-40 m and its end within one vertex
of the design's apron end.

    blender --background --python-exit-code 1 --python tools/author_aprons_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import geometry as mgeo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apron as ap_  # noqa: E402
import mouth_weld as mw  # noqa: E402

SEAT_EDGE_M = 1.5          # tools/seat_terrain_blend.py FINE_EDGE_M: terrain edges under the apron + its walk band
SIDEWALK_M = 3.1           # tools/seat_terrain_blend.py SIDEWALK_M
BAND_M = 8.0               # tools/seat_terrain_blend.py BAND_M
GRADE_OVER_SEAMS = 0.02    # [invented] self-check: no deck triangle steeper than the steeper seam's grade + this


def _read(ob):
    return [(v.co.x, v.co.z, v.co.y) for v in ob.data.vertices]          # Blender (x, z_north, y_up) -> local


def B(p):
    return (p[0], p[2], p[1])


def film_deck(outline, heights, fixed_flags, guess_fn, what):
    """the deck over an outline: its segments densified ON their straight 3-D seams (tools/apron.densify), a 1 m grid
    inside, Blender's constrained Delaunay (inside only), the fixed outline points held and the rest the cotangent film.
    Returns (verts [(x, y, z)], tris, where: original outline index -> vertex index)"""
    dout, dh, dfx, where = ap_.densify(outline, heights, fixed_flags)
    nO = len(dout)
    pts2 = list(dout) + ap_.interior_points(outline)
    res = mgeo.delaunay_2d_cdt([(x, z) for x, z in pts2], [(i, (i + 1) % nO) for i in range(nO)],
                               [list(range(nO))], 1, 1e-6)
    vco, faces, orig = res[0], res[2], res[3]
    tris = [tuple(t) for t in faces if len(t) == 3]
    if len(tris) != len(faces):
        raise SystemExit(f"[apron] FATAL: {what}: the CDT returned non-triangles")
    out_of, fixed = {}, {}
    for i, src_ids in enumerate(orig):
        for k in src_ids:
            if k < nO:
                out_of[k] = i
                if dfx[k]:
                    fixed[i] = dh[k]
    if len(out_of) != nO:
        raise SystemExit(f"[apron] FATAL: {what}: the CDT lost outline points ({len(out_of)} of {nO})")
    guess = [guess_fn(float(v[0]), float(v[1])) for v in vco]
    for k, i in out_of.items():
        guess[i] = dh[k]
    hs = ap_.harmonic_heights(len(vco), tris, fixed, guess, xz=[(float(v[0]), float(v[1])) for v in vco])
    verts = [(float(v[0]), hs[i], float(v[1])) for i, v in enumerate(vco)]
    return verts, tris, [out_of[w] for w in where]


def deck_checks(verts, tris):
    """(steepest well-shaped triangle, steepest of all, its corners, plan area)"""
    g_all, t = ap_.steepest(verts, tris)
    at = [[round(c_, 3) for c_ in verts[q]] for q in t] if t else None
    area = sum(0.5 * abs((verts[b][0] - verts[a][0]) * (verts[c][2] - verts[a][2]) -
                         (verts[b][2] - verts[a][2]) * (verts[c][0] - verts[a][0])) for a, b, c in tris)
    return ap_.robust_grade(verts, tris), g_all, at, area


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    decl = (cfg.get("route") or {}).get("aprons") or {}
    fill_px = [str(x) for x in ((cfg.get("route") or {}).get("mouth_fill") or [])]
    out_p = data / "aprons.json"
    if not decl and not fill_px:
        if out_p.exists():
            out_p.unlink()
        print("[apron] none declared (track.config.json route.aprons / route.mouth_fill): nothing authored")
        return
    mouths = json.loads((data / "mouths.json").read_text(encoding="utf-8"))["mouths"]
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    main_pts = [tuple(p) for p in local["points_xyz_m"]]
    lay = mw.mesh_layout(main_pts, conns)

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    road, curb = bpy.data.objects.get("ROAD"), bpy.data.objects.get("CURB")
    terrain = bpy.data.objects.get("TERRAIN")
    if road is None or curb is None or terrain is None:
        raise SystemExit("[apron] FATAL: loop.blend lacks ROAD / CURB / TERRAIN")
    if "mouth_weld" not in road.keys():
        raise SystemExit("[apron] FATAL: loop.blend is not welded (ROAD carries no mouth_weld stamp) — the apron reads "
                         "the welded rows; run tools/weld_mouths_blend.py first")
    for ob in list(bpy.data.objects):
        if ob.name.startswith(("1ROAD_apron_", "1KERB_sidewalk_ap", "1ROAD_mouthfill_")):
            raise SystemExit(f"[apron] FATAL: {ob.name} already in loop.blend — rebuild it first (the apron runs once)")
    RV = _read(road)
    CV = _read(curb)
    if len(RV) != lay["_road_total"] or len(CV) < lay["_curb_total"]:
        raise SystemExit(f"[apron] FATAL: ROAD {len(RV)} / CURB {len(CV)} verts vs the assembler's layout "
                         f"{lay['_road_total']} / {lay['_curb_total']} — the row order changed; not authoring")

    def rows_of(name):
        b = lay[name]
        return [(RV[b["road"] + 3 * r], RV[b["road"] + 3 * r + 1], RV[b["road"] + 3 * r + 2]) for r in range(b["rows"])]

    records, fails, decks = [], [], []
    curb_doomed = {}             # CURB side-block base -> (rows, {stations whose strip faces go})
    new_objs = []
    fills, road_doomed, paint_fix = [], {}, []    # road_doomed: piece -> rows whose strips go
    for mo in mouths:
        if not mo.get("piece") or not any(str(mo["connector"]).startswith(px) for px in fill_px):
            continue
        piece, host, side = mo["piece"], mo["host"], int(mo["side"])
        prow = rows_of(piece)
        order = list(range(len(prow))) if mo.get("end") == "start" else list(range(len(prow) - 1, -1, -1))
        L = [prow[r][0] for r in order]
        Cc = [prow[r][1] for r in order]
        Rr = [prow[r][2] for r in order]
        hrows = rows_of(host)
        hm, hclosed = lay[host]["rows"], lay[host]["closed"]
        hv = int(mo["host_vertex"])
        win = [(hv + k) % hm if hclosed else hv + k for k in range(-25, 26)]
        win = [r for r in win if 0 <= r < hm]
        lane = 0 if side == 1 else 2
        host_edge = {r: hrows[r][lane] for r in win}
        hdeck = mw.ExactHostDeck(hrows, mw.host_window(hrows, hclosed, mo["cut_xyz"][0], mo["cut_xyz"][2]))
        try:
            f = ap_.mouth_fill(host_edge, win, L, Cc, Rr,
                               lambda x, z: hdeck.edge_gap(x, z, side, 0.0) > ap_.FILL_OUT_M)
        except ap_.ApronError as e:
            raise SystemExit(f"[apron] FATAL: mouth fill {piece}: {e}")
        outline = f["outline"]
        mean_h = sum(f["outline_h"]) / len(outline)
        fverts, tris, _w = film_deck(outline, f["outline_h"], [True] * len(outline), lambda x, z: mean_h,
                                     f"mouth fill {piece}")
        steep, steep_all, st_at, area = deck_checks(fverts, tris)
        if steep > f["seam_grade"] + GRADE_OVER_SEAMS:
            fails.append(f"mouth fill {piece}: a well-shaped triangle at {100 * steep:.1f} % (its seams' steepest "
                         f"{100 * f['seam_grade']:.1f} % + {100 * GRADE_OVER_SEAMS:.0f}) at {st_at}")
        if abs(area - f["area_m2"]) > 0.02 * f["area_m2"] + 0.5:
            fails.append(f"mouth fill {piece}: the CDT covers {area:.1f} m2 of the outline's {f['area_m2']:.1f} m2")
        name = f"1ROAD_mouthfill_{len(fills)}"
        fme = bpy.data.meshes.new(name)
        fme.from_pydata([B(q) for q in fverts], [], tris)
        fme.validate()
        fob = bpy.data.objects.new(name, fme)
        bpy.context.scene.collection.objects.link(fob)
        new_objs.append(name)
        road_doomed.setdefault(piece, set()).update(order[: f["k_star"] + 1])
        paint_fix.append((outline, ap_.TriSurface(fverts, tris), hdeck))
        fills.append({"piece": piece, "host": host, "side": side, "object": name, "k_star": f["k_star"],
                      "rows_replaced": [order[0], order[f["k_star"]]],
                      "host_edge_crossings": {t_: [round(v, 4) for v in f["crossings"][t_]["xyz"]] for t_ in ("L", "R")},
                      "outline_xz": [[round(x, 4), round(z, 4)] for x, z in outline], "area_m2": round(area, 2),
                      "steepest_pct": round(100 * steep, 2), "steepest_any_pct": round(100 * steep_all, 2),
                      "seam_grade_pct": round(100 * f["seam_grade"], 2),
                      "vertices": len(fverts), "triangles": len(tris)})
        print(f"[apron] mouth fill {piece} -> {host} side {side:+d}: strips 0..{f['k_star']} replaced by {name} "
              f"({len(fverts)} v / {len(tris)} tris, {area:.1f} m2, steepest {100 * steep:.2f} %, seams "
              f"{100 * f['seam_grade']:.2f} %); its outline meets the host's edge at "
              f"{f['crossings']['L']['xyz'][0]:.2f},{f['crossings']['L']['xyz'][2]:.2f} / "
              f"{f['crossings']['R']['xyz'][0]:.2f},{f['crossings']['R']['xyz'][2]:.2f}")
    for apron_id, src in sorted(decl.items()):
        spec = json.loads((proj / src).read_text(encoding="utf-8"))
        weld = next((w for w in spec.get("welds", []) for a in (w.get("aprons") or []) if a.get("id") == apron_id), None)
        if weld is None:
            raise SystemExit(f"[apron] FATAL: apron {apron_id} is not in {src} welds[].aprons")
        apd = next(a for a in weld["aprons"] if a["id"] == apron_id)
        cname = weld["connector"]["name"]
        mo = next((m for m in mouths if m["connector"] == cname and m.get("piece")), None)
        if mo is None:
            raise SystemExit(f"[apron] FATAL: apron {apron_id}: no mouths.json record for connector {cname}")
        piece, host, side = mo["piece"], mo["host"], int(mo["side"])
        if mo.get("end") != "start":
            raise SystemExit(f"[apron] FATAL: apron {apron_id}: piece {piece} ends at the cut ({mo.get('end')}); only a "
                             "piece that STARTS at its cut is supported")
        ret = (weld["curbs"].get(apd["side"]) or {}).get("return") or {}
        if not ret.get("centre_xz") or ret.get("true_end_vertex") is None:
            raise SystemExit(f"[apron] FATAL: apron {apron_id}: {src} carries no {apd['side']} curb return")
        # the design tangent point: the return circle's foot on the stub's apron-side curb line
        design_T = tuple(apd["polygon_xz"][0])
        hrows = rows_of(host)
        srows = rows_of(piece)
        host_lane = 0 if side == 1 else 2
        # the stub's apron-side edge: the lane whose vertex near the design T is nearer it
        kq = min(range(len(srows)), key=lambda r: math.hypot(srows[r][1][0] - design_T[0], srows[r][1][2] - design_T[1]))
        stub_lane = min((0, 2), key=lambda ln: math.hypot(srows[kq][ln][0] - design_T[0], srows[kq][ln][2] - design_T[1]))
        stub_curb_side = 1 if stub_lane == 0 else -1
        E_design = int(math.ceil(float(ret["true_end_vertex"])))
        hm = lay[host]["rows"]
        c_row = int(mo["host_vertex"])
        win = [(c_row + k) % hm if lay[host]["closed"] else c_row + k for k in range(-15, max(16, E_design - c_row + 6))]
        win = [r for r in win if 0 <= r < hm]
        host_edge = {r: hrows[r][host_lane] for r in win}
        stub_edge = [r[stub_lane] for r in srows]
        stub_centre = [r[1] for r in srows]
        try:
            # the design's own apron end on the loop edge (author_expansion built it on this stub's swept edge; the
            # A5 true end of the return's curb line, ret["true_end_vertex"], is reported beside it)
            a = ap_.build(host_edge, win, stub_edge, stub_centre, design_T, float(ret.get("R") or 30.0),
                          (apd.get("loop_edge_vertices") or [None, ret["true_end_vertex"]])[1])
        except ap_.ApronError as e:
            raise SystemExit(f"[apron] FATAL: apron {apron_id}: {e}")
        # ---- the deck: CDT over the outline + interior points; the two seams' vertices fixed, the rest a soap film
        outline = a["outline"]
        dverts, tris, where = film_deck(outline, a["outline_h"], a["outline_fixed"], a["height"], f"apron {apron_id}")
        n_stub = a["n_stub"]
        arc_idx = [where[k] for k in range(n_stub, n_stub + len(a["arc"]))]     # T (the last stub vertex) .. E
        arc_h = [dverts[i][1] for i in arc_idx]
        a["arc_h"] = arc_h
        deck = ap_.TriSurface(dverts, tris)
        # self-checks on the deck
        hdeck = mw.ExactHostDeck(hrows, mw.host_window(hrows, lay[host]["closed"], a["P0"][0], a["P0"][2]))
        above = []
        for (x, y, z) in dverts:
            if abs(hdeck.edge_gap(x, z, side, 0.0)) <= 0.5 and y > hdeck.at(x, z) + 0.01:
                above.append((round(x, 2), round(z, 2), round(y - hdeck.at(x, z), 3)))
        steep, steep_all, steep_at, area = deck_checks(dverts, tris)
        if above:
            fails.append(f"{apron_id}: {len(above)} deck vertices over the host deck by > 0.01 m near its edge {above[:3]}")
        if steep > a["seam_grade"] + GRADE_OVER_SEAMS:
            fails.append(f"{apron_id}: a well-shaped deck triangle at {100 * steep:.1f} % (the seams' steepest "
                         f"{100 * a['seam_grade']:.1f} % + {100 * GRADE_OVER_SEAMS:.0f}) at {steep_at}")
        if abs(area - a["area_m2"]) > 0.02 * a["area_m2"] + 0.5:
            fails.append(f"{apron_id}: the CDT covers {area:.1f} m2 of the outline's {a['area_m2']:.1f} m2")
        me = bpy.data.meshes.new(f"1ROAD_apron_{apron_id}")
        me.from_pydata([B(p) for p in dverts], [], tris)
        me.validate()
        ob = bpy.data.objects.new(f"1ROAD_apron_{apron_id}", me)
        bpy.context.scene.collection.objects.link(ob)
        new_objs.append(ob.name)
        decks.append(deck)
        # ---- the return curb + walk
        first = [CV[mw.curb_index(lay, piece, a["T_row"], stub_curb_side, p)] for p in range(mw.CURB_P)]
        E_row = a["E_row"]
        last = [CV[mw.curb_index(lay, host, E_row, side, p)] for p in range(mw.CURB_P)]
        dT_ = math.dist((first[0][0], first[0][2]), (a["T"][0], a["T"][2]))
        dE_ = math.dist((last[0][0], last[0][2]), (host_edge[E_row][0], host_edge[E_row][2]))
        if dT_ > 2e-3 or dE_ > 2e-3:
            fails.append(f"{apron_id}: the curb's lane-edge points are off the road edge at T / E by {dT_:.4f} / "
                         f"{dE_:.4f} m (layout contract)")
        # the station at E swept along the host's outward normal (its curb's own direction at E_row), so the last
        # metre-and-a-half of the return lies on the host's curb line
        e_n = (last[3][0] - last[0][0], last[3][2] - last[0][2])
        e_n = (e_n[0] / math.hypot(*e_n), e_n[1] / math.hypot(*e_n))
        st = ap_.curb_stations(a["arc"], a["centre"], arc_h, first, last, e_normal=e_n)
        cverts = [p for row in st for p in row]
        cme = bpy.data.meshes.new(f"1KERB_sidewalk_ap{apron_id}")
        cme.from_pydata([B(p) for p in cverts], [], ap_.curb_faces(len(st)))
        cme.validate()
        cob = bpy.data.objects.new(f"1KERB_sidewalk_ap{apron_id}", cme)
        bpy.context.scene.collection.objects.link(cob)
        new_objs.append(cob.name)
        # ---- the stub's curb faces from its cut out to T on the apron side
        b = lay[piece]
        base = b["curb"] + (0 if stub_curb_side == 1 else b["rows"] * mw.CURB_P)
        curb_doomed.setdefault(base, (b["rows"], set()))[1].update(range(0, a["T_row"] + 1))
        records.append({"id": apron_id, "source": src, "piece": piece, "connector": cname, "host": host, "side": side,
                        "host_lane": host_lane, "stub_lane": stub_lane, "stub_curb_side": stub_curb_side,
                        "P0_xyz": [round(v, 4) for v in a["P0"]],
                        "P0_host_vertex": round(a["P0_host"][0] + a["P0_host"][1], 3),
                        "P0_stub_row": round(a["P0_stub"][0] + a["P0_stub"][1], 3),
                        "T_row": a["T_row"], "T_xyz": [round(v, 4) for v in a["T"]],
                        "E_row": E_row, "E_xyz": [round(v, 4) for v in a["E"]],
                        "design_true_end_vertex": ret["true_end_vertex"], "design_R_m": ret.get("R"),
                        "R_m": round(a["R"], 3), "centre_xz": [round(v, 4) for v in a["centre"]],
                        "entry_deg": round(a["entry_deg"], 2), "arc_len_m": round(a["arc_len_m"], 2),
                        "arc_xyz": [[round(x, 4), round(h, 4), round(z, 4)] for (x, z), h in zip(a["arc"], arc_h)],
                        "outline_xz": [[round(x, 4), round(z, 4)] for x, z in outline],
                        "seam_stub_xyz": [[round(v, 4) for v in p_] for p_ in
                                          [a["P0"]] + [stub_edge[j] for j in range(a["P0_stub"][0] + 1, a["T_row"] + 1)]],
                        "area_m2": round(area, 2), "deck_vertices": len(dverts), "deck_triangles": len(tris),
                        "steepest_deck_pct": round(100 * steep, 2), "steepest_any_pct": round(100 * steep_all, 2),
                        "seam_grade_pct": round(100 * a["seam_grade"], 2),
                        "E_vertex": round(a["E_vertex"], 3),
                        "host_rows_opened": [a["P0_host"][0], E_row],
                        "objects": [f"1ROAD_apron_{apron_id}", f"1KERB_sidewalk_ap{apron_id}"]})
        print(f"[apron] {apron_id} ({piece} -> {host} side {side:+d}): P0 at host v{a['P0_host'][0] + a['P0_host'][1]:.2f}, "
              f"T stub row {a['T_row']}, E host row {E_row}; return R {a['R']:.2f} m (design {ret.get('R')}), entry "
              f"{a['entry_deg']:.1f} deg, arc {a['arc_len_m']:.1f} m; deck {len(dverts)} v / {len(tris)} tris, "
              f"{area:.1f} m2, steepest {100 * steep:.2f} % (seams {100 * a['seam_grade']:.2f} %); E at "
              f"v{a['E_vertex']:.2f} (design apron v{(apd.get('loop_edge_vertices') or [0, 0])[1]}, A5 curb line v{float(ret['true_end_vertex']):.2f}); curb {len(st)} stations")
    if fails:
        for f in fails:
            print(f"[apron] SELF-CHECK FAIL: {f}")
        raise SystemExit(f"[apron] FATAL: {len(fails)} self-check failure(s) — loop.blend NOT saved")

    # ---- CURB faces on the stub's apron side, cut -> T
    bm = bmesh.new()
    bm.from_mesh(curb.data)
    doomed = []
    for f in bm.faces:
        idx = [v.index for v in f.verts]
        lo, hi = min(idx), max(idx)
        for base, (rows, stations) in curb_doomed.items():
            if base <= lo and hi < base + rows * mw.CURB_P:
                if {(i - base) // mw.CURB_P for i in idx} <= stations:
                    doomed.append(f)
                break
    n_curb = len(doomed)
    # FACES_ONLY: the vertices stay — gap_mouths_blend (later) finds the host's strip by the assembler's vertex order
    bmesh.ops.delete(bm, geom=doomed, context="FACES_ONLY")
    bm.to_mesh(curb.data)
    bm.free()
    curb.data.update()

    # ---- ROAD strips the mouth fills replaced (faces only: the vertex order is the assembler's contract)
    n_road = n_paint_seated = 0
    if road_doomed:
        bm = bmesh.new()
        bm.from_mesh(road.data)
        doomed = []
        blocks = {pc: (lay[pc]["road"], lay[pc]["rows"], rows_) for pc, rows_ in road_doomed.items()}
        for fa in bm.faces:
            idx = [v.index for v in fa.verts]
            for base, nrows, rows_ in blocks.values():
                if base <= min(idx) and max(idx) < base + 3 * nrows:
                    if {(i - base) // 3 for i in idx} <= rows_:
                        doomed.append(fa)
                    break
        n_road = len(doomed)
        bmesh.ops.delete(bm, geom=doomed, context="FACES_ONLY")
        bm.to_mesh(road.data)
        bm.free()
        road.data.update()
        # the paint over a fill laid on it again; the connector's paint left inside the host on the host's deck
        n_paint_seated = 0
        for nm in ("MARKINGS", "YLINE"):
            ob = bpy.data.objects.get(nm)
            if ob is None:
                continue
            for v in ob.data.vertices:
                x, z, y = v.co.x, v.co.y, v.co.z
                for outline, surf, hdeck in paint_fix:
                    h = surf.at(x, z) if ap_.point_in_polygon(outline, x, z) else None
                    if h is None and hdeck.inside(x, z) and ap_.dist_to_outline(outline, x, z) < 3.0:
                        h = hdeck.at(x, z)
                    if h is not None and abs(h + mw.MARK_LIFT_M - y) > 1e-4:
                        v.co.z = h + mw.MARK_LIFT_M
                        n_paint_seated += 1
                        break
            ob.data.update()

    # ---- paint lying wholly inside an apron
    n_paint = 0
    for nm in ("MARKINGS", "YLINE"):
        ob = bpy.data.objects.get(nm)
        if ob is None:
            continue
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        doomed = []
        for f in bm.faces:
            if all(any(ap_.point_in_polygon(r["outline_xz"], v.co.x, v.co.y) for r in records) for v in f.verts):
                doomed.append(f)
        n_paint += len(doomed)
        bmesh.ops.delete(bm, geom=doomed, context="FACES")
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()

    # ---- TERRAIN under the apron + the return's walk and blend band
    seats = []
    for r in records:
        rec = dict(r)
        rec["outline"] = [tuple(p) for p in r["outline_xz"]]
        rec["centre"] = tuple(r["centre_xz"])
        rec["R"] = r["R_m"]
        rec["arc"] = [(p[0], p[2]) for p in r["arc_xyz"]]
        rec["arc_h"] = [p[1] for p in r["arc_xyz"]]
        seats.append(rec)
    for rec, surf in zip(seats, decks):
        rec["height"] = (lambda x, z, surf=surf, fb=rec["arc_h"][0]: surf.at(x, z) if surf.at(x, z) is not None else fb)
    bm = bmesh.new()
    bm.from_mesh(terrain.data)
    reach = SIDEWALK_M + BAND_M + 1.0
    n_sub = 0
    for _round in range(8):
        todo = []
        for e in bm.edges:
            if e.calc_length() <= SEAT_EDGE_M:
                continue
            mx = 0.5 * (e.verts[0].co.x + e.verts[1].co.x)
            mz = 0.5 * (e.verts[0].co.y + e.verts[1].co.y)
            for rec in seats:
                C, R = rec["centre"], rec["R"]
                if ap_.point_in_polygon(rec["outline"], mx, mz) or \
                        (R - reach <= math.hypot(mx - C[0], mz - C[1]) <= R + 1.0
                         and ap_.seat_target(rec, mx, mz, sidewalk_m=SIDEWALK_M + 1.0, band_m=BAND_M) is not None):
                    todo.append(e)
                    break
        if not todo:
            break
        n_sub += len(todo)
        bmesh.ops.subdivide_edges(bm, edges=todo, cuts=1, use_grid_fill=True)
    moved = 0
    for v in bm.verts:
        for rec in seats:
            st = ap_.seat_target(rec, v.co.x, v.co.y, sidewalk_m=SIDEWALK_M, band_m=BAND_M)
            if st is None:
                continue
            t, target = st
            if t <= 0.0:
                v.co.z = target
                moved += 1
            else:
                goal = target * (1 - t) + v.co.z * t
                if v.co.z > goal or target - v.co.z > 2.5 * (1 - t):
                    v.co.z = goal
                    moved += 1
            break
    bm.to_mesh(terrain.data)
    bm.free()
    terrain.data.update()

    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    for r in records:
        r["stub_curb_faces_deleted"] = n_curb
        r["paint_faces_deleted"] = n_paint
        r["terrain"] = {"edges_halved": n_sub, "verts_seated": moved}
    for fl in fills:
        fl["road_faces_deleted"] = n_road
    out_p.write_text(json.dumps({"mouth_fills": fills, "_doc": "tools/author_aprons_blend.py (ledger 0054 P1 fix round): the corner aprons as "
                                         "built; host_rows_opened = [P0's row, E's row] on the mouth side",
                                 "aprons": records}, indent=1), encoding="utf-8")
    if fills:
        print(f"[apron] {len(fills)} mouth fill(s): {n_road} connector ROAD faces replaced, {n_paint_seated} paint "
              f"vertices laid on the fill / the host deck")
    print(f"[apron] {len(records)} apron(s) -> {new_objs}; {n_curb} stub curb faces and {n_paint} paint faces under them "
          f"deleted; TERRAIN {n_sub} edges halved, {moved} verts seated; saved loop.blend + data/aprons.json")


main()
