"""Author every declared JUNCTION PAD into loop.blend (ledger 0054 P3 step 2; EXPANSION-PLAN A4; docs/JUNCTIONS.md
topology B, rules 1-6, 9-10, 18(d)). The geometry and its reasons are tools/junction_pad.py; the plan (which pieces end on
which arm, the stubs' far-edge 3DEP) is data/pads.plan.json (`python tools/junction_pad.py plan`). Opt-in: no plan file =
one line printed, loop.blend not even opened.

In the scene, after weld_mouths_blend + seat_terrain_blend + author_aprons_blend (it reads the arms' WELDED, seated rows)
and before triangulate_terrain_blend / ground_release / the median / gap_mouths, per pad:

  1ROAD_pad_<id>            the pad deck: its outline (tools/junction_pad.outline_as_built: every route arm's LAST ROW as
                            the mesh has it — its left edge, centre and right edge vertices, position-identical, JUNCTIONS
                            rule 3 — every corner a true arc at the measured radius, every stub arm's pavement out to its
                            barrier and 1 m past it) + interior points every 1 m, Blender's constrained Delaunay
                            (mathutils.geometry.delaunay_2d_cdt, inside only); heights: the arm rows exactly, the stubs'
                            far edges at 3DEP + the road's 0.10 m, every other vertex the cotangent-Laplace soap film
                            between them (tools/apron.harmonic_heights) — one single-coverage sheet (rule 1)
  1KERB_sidewalk_pad<id>    the curb + walk round every corner (build_loop_blend's curb_sidewalk profile: lane edge,
                            +0.14 m curb top over 0.08 m, 1.5 m walk, 1.2 m grade to 0.20 m under the edge) along the
                            outline between the arm cuts, swept to the outside; its first / last station the route arm's
                            own curb row (rule 9: the curb follows the pad's outline round the arc into the next street);
                            on a stub arm it runs on along both stub sides to the stub's far end
  1WALL_STUB_PAD_<id>_<stub> Phase 5's barrier (JUNCTIONS 18(d)): Kevin's 4.04 m K-rail module (tools/stub_geom:
                            the jersey profile, its V-groove joints every module) across the stub 15 m from its mouth
                            line, grass meet to grass meet over both walks, each ring seated on the lowest pad surface
                            under its footprint less 0.02 m (collection STUBS)
  TERRAIN                   halved to <= SEAT_EDGE_M under the pad, its curb band and the 8 m blend past it, then seated
                            by seat_terrain's verge rule (deck - 0.16 under the pad and the walk, blended back over 8 m);
                            a vertex under a connector's ROAD is left to the seat / the kn5 prep, as everywhere

Writes data/pads.built.json (per pad: the objects, the outline, every seam vertex with its arm vertex, the deck's
steepest triangles, the curb runs, and per stub its barrier in tools/author_stubs_blend.py's stubs.built.json shape —
scripts/geometry/audit_mesh.py's D exemption and tools/verify_pads.py read it).

Self-check (exit 1, loop.blend NOT saved): every route arm's row vertices ARE outline vertices of the deck, bit for bit;
the CDT covers the outline (area within 2 % + 0.5 m2); no well-shaped deck triangle steeper than the steepest of the
arms' and stubs' own grades and the chords between two different seams + 2 % [tools/author_aprons_blend.py
GRADE_OVER_SEAMS]; every barrier ring on a pad surface; the
curb's end stations ON the arm's curb rows.

    blender --background --python-exit-code 1 --python tools/author_junction_pad_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils import geometry as mgeo
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apron as ap_  # noqa: E402
import junction_pad as jp  # noqa: E402
import mouth_weld as mw  # noqa: E402
import race_furniture as rf  # noqa: E402
import stub_geom as sg  # noqa: E402

SEAT_EDGE_M = 1.5          # tools/author_aprons_blend.py SEAT_EDGE_M (seat_terrain FINE_EDGE_M)
SIDEWALK_M = 3.1           # tools/seat_terrain_blend.py SIDEWALK_M
BAND_M = 8.0               # tools/seat_terrain_blend.py BAND_M
LIFT = 0.10                # tools/seat_terrain_blend.py LIFT
CLEAR = 0.06               # tools/seat_terrain_blend.py CLEAR_M
GRADE_OVER_SEAMS = 0.02    # tools/author_aprons_blend.py GRADE_OVER_SEAMS [invented there]
ARM_GRADE_REACH_M = 30.0   # [invented] an arm's own grade is read over its last this many metres
COLLECTION = "STUBS"       # tools/author_stubs_blend.py COLLECTION
WALL_PREFIX = "1WALL_STUB_PAD_"


def _read(ob):
    return [(v.co.x, v.co.z, v.co.y) for v in ob.data.vertices]          # Blender (x, z_north, y_up) -> local


def B(p):
    return (p[0], p[2], p[1])


def film(outline, heights, fixed, what):
    """the deck: Blender's CDT over the (already densified) outline + a 1 m interior grid, the fixed outline heights
    held, the rest the cotangent film. Returns (verts [(x, y, z)], tris, where[outline index] -> vertex index)"""
    nO = len(outline)
    pts2 = list(outline) + ap_.interior_points(outline)
    res = mgeo.delaunay_2d_cdt([(x, z) for x, z in pts2], [(i, (i + 1) % nO) for i in range(nO)],
                               [list(range(nO))], 1, 1e-6)
    vco, faces, orig = res[0], res[2], res[3]
    tris = [tuple(t) for t in faces if len(t) == 3]
    if len(tris) != len(faces):
        raise SystemExit(f"[pads] FATAL: {what}: the CDT returned non-triangles")
    out_of, fx = {}, {}
    for i, src_ids in enumerate(orig):
        for k in src_ids:
            if k < nO:
                out_of[k] = i
                if fixed[k]:
                    fx[i] = heights[k]
    if len(out_of) != nO:
        raise SystemExit(f"[pads] FATAL: {what}: the CDT lost outline points ({len(out_of)} of {nO})")
    fixed_pts = [(outline[k][0], outline[k][1], heights[k]) for k in range(nO) if fixed[k]]

    def guess_at(x, z):
        num = den = 0.0
        for px, pz, h in fixed_pts:
            w = 1.0 / (1e-3 + (px - x) ** 2 + (pz - z) ** 2)
            num += w * h
            den += w
        return num / den
    guess = [guess_at(float(v[0]), float(v[1])) for v in vco]
    for i, h in fx.items():
        guess[i] = h
    hs = ap_.harmonic_heights(len(vco), tris, fx, guess, xz=[(float(v[0]), float(v[1])) for v in vco])
    verts = [(float(v[0]), hs[i], float(v[1])) for i, v in enumerate(vco)]
    return verts, tris, [out_of[k] for k in range(nO)]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    plan_p = data / "pads.plan.json"
    out_p = data / "pads.built.json"
    if not plan_p.exists():
        if out_p.exists():
            out_p.unlink()
        print("[pads] no data/pads.plan.json (route.junction_pads declares none): nothing authored")
        return
    plan = json.loads(plan_p.read_text(encoding="utf-8"))
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    lay = mw.mesh_layout([tuple(p) for p in local["points_xyz_m"]], conns)

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    road, curb, terrain = (bpy.data.objects.get(n) for n in ("ROAD", "CURB", "TERRAIN"))
    if road is None or curb is None or terrain is None:
        raise SystemExit("[pads] FATAL: loop.blend lacks ROAD / CURB / TERRAIN")
    if "mouth_weld" not in road.keys():
        raise SystemExit("[pads] FATAL: loop.blend is not welded — the pads read the welded rows")
    for ob in bpy.data.objects:
        if ob.name.startswith(("1ROAD_pad_", "1KERB_sidewalk_pad", WALL_PREFIX)):
            raise SystemExit(f"[pads] FATAL: {ob.name} already in loop.blend — rebuild it first (the pads run once)")
    RV, CV = _read(road), _read(curb)
    if len(RV) != lay["_road_total"] or len(CV) < lay["_curb_total"]:
        raise SystemExit(f"[pads] FATAL: ROAD {len(RV)} / CURB {len(CV)} vs the layout {lay['_road_total']} / "
                         f"{lay['_curb_total']} — the row order changed; not authoring")
    road_bvh = BVHTree.FromPolygons([B(p) for p in RV], [tuple(p.vertices) for p in road.data.polygons])

    built, fails, seat_specs = [], [], []
    col = bpy.data.collections.get(COLLECTION) or bpy.data.collections.new(COLLECTION)
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    for pad in plan["pads"]:
        pid = pad["id"]
        prec = pad["design"]                     # tools/junction_pad.design_pads: the pad on the roads as they are
        stubs = prec["stubs"]
        arm_rows, arm_curb, arm_grade = {}, {}, {}
        for a in pad["arms"]:
            if a["kind"] != "route":
                continue
            name, end = a["connector"], a["end"]
            b = lay[name]
            r = 0 if end == "start" else b["rows"] - 1
            L = RV[mw.road_index(lay, name, r, 0)]
            C = RV[mw.road_index(lay, name, r, 1)]
            R = RV[mw.road_index(lay, name, r, 2)]
            arm_rows[a["name"]] = {"L": L, "C": C, "R": R}
            arm_curb[(a["name"], "L")] = [CV[mw.curb_index(lay, name, r, 1, p)] for p in range(mw.CURB_P)]
            arm_curb[(a["name"], "R")] = [CV[mw.curb_index(lay, name, r, -1, p)] for p in range(mw.CURB_P)]
            for key, e in (("L", L), ("R", R)):
                d = math.dist(arm_curb[(a["name"], key)][0], e)
                if d > 2e-3:
                    fails.append(f"{pid} {a['name']}: the curb's lane edge is {d:.4f} m off the road edge (layout)")
            # the arm's own grade over its last ARM_GRADE_REACH_M (its centre rows)
            order = list(range(b["rows"])) if end == "start" else list(range(b["rows"] - 1, -1, -1))
            g, acc = 0.0, 0.0
            for q0, q1 in zip(order, order[1:]):
                p0, p1 = RV[mw.road_index(lay, name, q0, 1)], RV[mw.road_index(lay, name, q1, 1)]
                Lh = math.hypot(p1[0] - p0[0], p1[2] - p0[2])
                if Lh > 1e-6:
                    g = max(g, abs(p1[1] - p0[1]) / Lh)
                acc += Lh
                if acc >= ARM_GRADE_REACH_M:
                    break
            arm_grade[a["name"]] = g
        sh = {sid: s["far_deck_y"] for sid, s in pad["stubs"].items()}
        try:
            ob_ = jp.outline_as_built(prec, stubs, arm_rows, sh)
        except jp.PadError as e:
            raise SystemExit(f"[pads] FATAL: {pid}: {e}")
        outline, heights, fixed = ob_["outline"], ob_["heights"], ob_["fixed"]
        verts, tris, where = film(outline, heights, fixed, f"pad {pid}")
        # seams: the arm row vertices must BE deck vertices, bit for bit
        seams = []
        for a in pad["arms"]:
            if a["kind"] != "route":
                continue
            info = ob_["arms"][a["name"]]
            for i_o, key in zip(info["idx"], ("p", "C", "q")):
                vi = where[i_o]
                v = verts[vi]
                tag = ob_["tags"][i_o]
                ref = arm_rows[a["name"]][tag[2]]
                d = max(abs(v[0] - ref[0]), abs(v[1] - ref[1]), abs(v[2] - ref[2]))
                seams.append({"arm": a["name"], "connector": a["connector"], "row_vertex": tag[2], "pad_vertex": vi,
                              "xyz": [round(c, 4) for c in v], "max_abs_diff_m": d})
                if d > 0.0:
                    # the film's heights are float64; the arm's are its float32 mesh values: write them exactly
                    verts[vi] = tuple(ref)
        # steepness vs the seams' own grades (+ GRADE_OVER_SEAMS)
        stub_g = []
        for sid, s in pad["stubs"].items():
            info = next(v for v in ob_["arms"].values() if v["kind"] == "stub" and v["stub"] == sid)
            m0, m1 = (verts[where[i]] for i in info["mouth"])
            mouth_y = (m0[1] + m1[1]) / 2
            stub_g.append(abs(s["far_deck_y"][1] - mouth_y) / (jp.STUB_LENGTH_M + jp.TAIL_M))
        # ... and the steepest CHORD between two different seams (an arm row, a stub's far edge): the film can be no
        # gentler than the straight line between two edges it must meet (J2: Waring's end stands 0.6 m over Princess
        # View's start, ~12 m away round the corner)
        groups = []
        for i_o, (fxd, tag) in enumerate(zip(fixed, ob_["tags"])):
            if fxd and tag is not None:
                groups.append((tag[:2], outline[i_o], verts[where[i_o]][1]))
        chord = 0.0
        for gi in range(len(groups)):
            for gj in range(gi + 1, len(groups)):
                if groups[gi][0] == groups[gj][0]:
                    continue
                dd = math.dist(groups[gi][1], groups[gj][1])
                if dd >= 1.0:
                    chord = max(chord, abs(groups[gi][2] - groups[gj][2]) / dd)
        seam_grade = max(list(arm_grade.values()) + stub_g + [chord])
        steep = ap_.robust_grade(verts, tris)
        steep_all, st_t = ap_.steepest(verts, tris)
        area = sum(0.5 * abs((verts[b][0] - verts[a][0]) * (verts[c][2] - verts[a][2]) -
                             (verts[b][2] - verts[a][2]) * (verts[c][0] - verts[a][0])) for a, b, c in tris)
        oarea = abs(jp._area(outline))
        if abs(area - oarea) > 0.02 * oarea + 0.5:
            fails.append(f"{pid}: the CDT covers {area:.1f} m2 of the outline's {oarea:.1f} m2")
        if steep > seam_grade + GRADE_OVER_SEAMS:
            worst = None
            for t in tris:
                g1 = ap_.robust_grade(verts, [t])
                if worst is None or g1 > worst[0]:
                    worst = (g1, t)
            fails.append(f"{pid}: a well-shaped deck triangle at {100 * steep:.1f} % (the arms' / stubs' steepest "
                         f"{100 * seam_grade:.1f} % + {100 * GRADE_OVER_SEAMS:.0f}) at "
                         f"{[[round(c_, 3) for c_ in verts[q]] for q in worst[1]]}")
        me = bpy.data.meshes.new(f"1ROAD_{jp.PREFIX}_{pid}")
        me.from_pydata([B(p) for p in verts], [], tris)
        me.validate()
        dob = bpy.data.objects.new(f"1ROAD_{jp.PREFIX}_{pid}", me)
        bpy.context.scene.collection.objects.link(dob)
        deck_h = [verts[where[i]][1] for i in range(len(outline))]
        # the curb runs
        cverts, cfaces, run_recs, station_of = [], [], [], {}
        for run, (t0, t1) in zip(ob_["runs"], ob_["run_ends"]):
            first = arm_curb[(t0[1], t0[2])] if t0[0] == "arm" else None
            last = arm_curb[(t1[1], t1[2])] if t1[0] == "arm" else None
            if first is not None and math.dist((first[0][0], first[0][2]), outline[run[0]]) > 2e-3:
                fails.append(f"{pid}: a curb run starts {math.dist((first[0][0], first[0][2]), outline[run[0]]):.4f} m "
                             f"off its arm's curb row ({t0})")
            if last is not None and math.dist((last[0][0], last[0][2]), outline[run[-1]]) > 2e-3:
                fails.append(f"{pid}: a curb run ends {math.dist((last[0][0], last[0][2]), outline[run[-1]]):.4f} m "
                             f"off its arm's curb row ({t1})")
            rows = jp.run_stations(outline, deck_h, run, ap_.PROFILE, first=first, last=last)
            base = len(cverts)
            for k, (i_o, row) in enumerate(zip(run, rows)):
                station_of[i_o] = row
                cverts += list(row)
            cfaces += [tuple(base + v for v in f) for f in ap_.curb_faces(len(rows))]
            run_recs.append({"from": list(t0), "to": list(t1), "stations": len(rows)})
        cme = bpy.data.meshes.new(f"1KERB_sidewalk_{jp.PREFIX}{pid}")
        cme.from_pydata([B(p) for p in cverts], [], cfaces)
        cme.validate()
        cob = bpy.data.objects.new(f"1KERB_sidewalk_{jp.PREFIX}{pid}", cme)
        bpy.context.scene.collection.objects.link(cob)
        # barriers across the stubs
        surf = BVHTree.FromPolygons([B(p) for p in verts] + [B(p) for p in cverts],
                                    [tuple(t) for t in tris] + [tuple(len(verts) + v for v in f) for f in cfaces])

        def top_at(x, z, near_y):
            hit = surf.ray_cast(Vector((x, z, near_y + 4.0)), Vector((0.0, 0.0, -1.0)), 12.0)
            return None if hit[0] is None else hit[0].z
        bar_recs = []
        for sid, (i_r, i_l) in ob_["barriers"].items():
            right, left = station_of.get(i_r), station_of.get(i_l)
            if right is None or left is None:
                fails.append(f"{pid} {sid}: no curb station at the barrier")
                continue
            path = sg.barrier_path(right, left)
            yref = deck_h[i_r]

            def base_of(x, z, ax, az, yref=yref):
                samples = [top_at(px, pz, yref) for px, pz in sg.footprint_samples(x, z, ax, az)]
                got = [s for s in samples if s is not None]
                return (min(got) if got else None), samples
            try:
                rings, seat = sg.barrier_rings(path, base_of)
            except sg.GeomError as ex:
                raise SystemExit(f"[pads] FATAL: {pid} {sid}: {ex}")
            bv_, bf_, uvs = sg.barrier_mesh(rings)
            sharp = rf.sharp_edges(bv_, bf_)
            bv, bf = rf.to_blender(bv_, bf_)
            name = f"{WALL_PREFIX}{pid}_{sid}"
            wme = bpy.data.meshes.new(name)
            wme.from_pydata(bv, [], bf)
            wme.validate()
            uvl = wme.uv_layers.new(name="UVMap")
            for poly in wme.polygons:
                for li in poly.loop_indices:
                    uvl.data[li].uv = uvs[wme.loops[li].vertex_index]
            wme.shade_smooth()
            key = {(a, c) if a < c else (c, a) for a, c in sharp}
            wme.edges.foreach_set("use_edge_sharp", [tuple(sorted(e.vertices)) in key for e in wme.edges])
            wme.update()
            wob = bpy.data.objects.new(name, wme)
            col.objects.link(wob)
            sinks = [max(s for s in r["surface"] if s is not None) - r["base"] for r in seat]
            bar_recs.append({"id": f"{pid}_{sid}", "stub": sid, "road": stubs[sid].get("road"),
                             "barrier": {"object": name, "style": "krail", "half_base_m": sg.BARRIER_HALF_BASE,
                                         "height_m": sg.BARRIER_H, "rings": len(rings),
                                         "path_xz": [[r["x"], r["z"]] for r in seat], "kinds": [r["kind"] for r in seat],
                                         "seat": seat, "max_sink_m": round(max(sinks), 4),
                                         "span_m": round(sum(math.hypot(seat[i + 1]["x"] - seat[i]["x"],
                                                                        seat[i + 1]["z"] - seat[i]["z"])
                                                             for i in range(len(seat) - 1)), 3)}})
        seat_specs.append((outline, verts, tris, deck_h))
        built.append({"id": pid, "objects": [dob.name, cob.name] + [b_["barrier"]["object"] for b_ in bar_recs],
                      "deck": {"vertices": len(verts), "triangles": len(tris), "area_m2": round(area, 2),
                               "outline_area_m2": round(oarea, 2), "steepest_pct": round(100 * steep, 2),
                               "steepest_any_pct": round(100 * steep_all, 2),
                               "seam_grade_pct": round(100 * seam_grade, 2),
                               "arm_grades_pct": {k: round(100 * v, 2) for k, v in arm_grade.items()}},
                      "outline_xz": [[round(x, 4), round(z, 4)] for x, z in outline],
                      "outline_deck_y": [round(h, 4) for h in deck_h], "kind": ob_["kind"],
                      "seams": seams, "curb_runs": run_recs, "stubs": bar_recs})
        print(f"[pads] {pid}: deck {len(verts)} v / {len(tris)} tris, {area:.1f} m2 (outline {oarea:.1f}), steepest "
              f"{100 * steep:.2f} % (arms / stubs {100 * seam_grade:.2f} %); {len(seams)} seam vertices welded to "
              f"{sum(1 for a in pad['arms'] if a['kind'] == 'route')} arm row(s); curb {len(run_recs)} run(s), "
              f"{len(cverts) // 4} stations; {len(bar_recs)} K-rail barrier(s) "
              f"({', '.join(b_['stub'] + ' %.2f m' % b_['barrier']['span_m'] for b_ in bar_recs)})")
    if fails:
        for f in fails:
            print(f"[pads] SELF-CHECK FAIL: {f}")
        raise SystemExit(f"[pads] FATAL: {len(fails)} self-check failure(s) — loop.blend NOT saved")

    # ---- TERRAIN under the pads, their walks and the blend band
    def seat_target(spec, x, z):
        outline, verts, tris, deck_h = spec
        inside = ap_.point_in_polygon(outline, x, z)
        if inside:
            surfh = None
            return 0.0, None
        d = ap_.dist_to_outline(outline, x, z)
        if d > SIDEWALK_M + BAND_M:
            return None
        k = min(range(len(outline)), key=lambda i: (outline[i][0] - x) ** 2 + (outline[i][1] - z) ** 2)
        target = deck_h[k] - LIFT - CLEAR
        if d <= SIDEWALK_M:
            return 0.0, target
        return (d - SIDEWALK_M) / BAND_M, target
    surfs = [ap_.TriSurface(s[1], s[2]) for s in seat_specs]
    boxes = []
    for outline, *_ in seat_specs:
        xs, zs = [p[0] for p in outline], [p[1] for p in outline]
        r = SIDEWALK_M + BAND_M + 2.0
        boxes.append((min(xs) - r, max(xs) + r, min(zs) - r, max(zs) + r))

    def which(x, z):
        return [k for k, b in enumerate(boxes) if b[0] <= x <= b[1] and b[2] <= z <= b[3]]
    bm = bmesh.new()
    bm.from_mesh(terrain.data)
    n_sub = 0
    for _round in range(8):
        todo = []
        for e in bm.edges:
            if e.calc_length() <= SEAT_EDGE_M:
                continue
            mx = 0.5 * (e.verts[0].co.x + e.verts[1].co.x)
            mz = 0.5 * (e.verts[0].co.y + e.verts[1].co.y)
            for k in which(mx, mz):
                if seat_target(seat_specs[k], mx, mz) is not None:
                    todo.append(e)
                    break
        if not todo:
            break
        n_sub += len(todo)
        bmesh.ops.subdivide_edges(bm, edges=todo, cuts=1, use_grid_fill=True)
    moved = under_road = 0
    for v in bm.verts:
        x, z = v.co.x, v.co.y
        ks = which(x, z)
        if not ks:
            continue
        if road_bvh.ray_cast(Vector((x, z, v.co.z + 50.0)), Vector((0.0, 0.0, -1.0)), 100.0)[0] is not None:
            under_road += 1
            continue
        for k in ks:
            st = seat_target(seat_specs[k], x, z)
            if st is None:
                continue
            t, target = st
            if target is None:                                  # under the pad: the deck there
                h = surfs[k].at(x, z)
                if h is None:
                    continue
                v.co.z = h - LIFT - CLEAR
                moved += 1
            elif t <= 0.0:
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
    road["junction_pads"] = json.dumps([p["id"] for p in built])
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    out_p.write_text(json.dumps({"_doc": "tools/author_junction_pad_blend.py (ledger 0054 P3 step 2): the junction "
                                         "pads as built; stubs[] per pad in stubs.built.json's barrier shape",
                                 "terrain": {"edges_halved": n_sub, "verts_seated": moved,
                                             "left_under_road": under_road},
                                 "pads": built,
                                 "stubs": [s for p in built for s in p["stubs"]]}, indent=1), encoding="utf-8")
    print(f"[pads] {len(built)} pad(s) authored; TERRAIN {n_sub} edges halved, {moved} verts seated "
          f"({under_road} under a connector's road left to the seat); saved loop.blend + data/pads.built.json")


main()
