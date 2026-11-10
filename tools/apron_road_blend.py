"""The mainline's measured APRON as its own drivable road object (ledger 0085, Pikes Peak; opt-in route.edge_apron_file).

The assembler sweeps the apron as the edge strip's sidewalk on one side (scripts-v021 ribbon.curb_sidewalk apron:
4.2-14.9 m wide, falling -2.9..-8.5 %, its lip on the measured ground). In CURB it would ship as 1KERB_sidewalk, and
engine-july's prep (build_kn5_loop._conform_and_reseat) pins the ground under 1ROAD only: past the LANE edge it holds a
3 m band at the lane edge's height and feathers it to the natural ground over 6 m more. With a 6 m apron falling 0.4 m,
that band and feather stand over the apron's low outer lip (up to ~0.2 m, the anti-poke only pushes ground DOWN under a
drivable sheet). As a 1ROAD object the apron is part of the footprint: the ground under it is pinned to it, and the band
starts at its lip, which stands on the measured ground. The aerial shows it paved (a lighter band with its painted line
all round the inside), so ROAD physics is the real surface; it keeps CURB's material (the concrete look).

This step moves the declared side's CURB faces of the MAINLINE (tools/mouth_weld.mesh_layout: CURB is per line two side
blocks, rows x 4 profile points) into a new object 1ROAD_apron with copies of their vertices, UVs and materials, and
deletes the faces from CURB (FACES_ONLY: CURB keeps every vertex, so every later step that reads its layout by index still
can). Connectors' strips are not touched.

Self-checks (exit 1, loop.blend not saved): CURB is not the assembler's layout; the apron file's side is not "left" or
"right"; fewer faces moved than the side's rows. No route.edge_apron_file = no-op (Lake Murray and every other track).
Run after strip_seam (its seam reads the strip's lip off CURB's layout) and BEFORE gap_mouths (which deletes with its
orphaned vertices: CURB is no longer the layout after it). At each mainline mouth on the apron side the apron is cut along
the road's two edges and only the part under the road goes (below); gap_mouths then finds nothing left there.

    blender --background --python-exit-code 1 --python tools/apron_road_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import math

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mouth_weld as mw  # noqa: E402

NAME = "1ROAD_apron"
REACH_M = 25.0      # [invented] a mouth's road rows within this of its cut fit its two edge lines across the apron


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    proj = Path(argv[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    rel = (cfg.get("route") or {}).get("edge_apron_file")
    if not rel:
        print("[apron-road] no route.edge_apron_file: nothing to do")
        return
    ap = json.loads((proj / rel).read_text(encoding="utf-8"))
    if ap.get("side") not in ("left", "right"):
        raise SystemExit(f"[apron-road] FATAL: {rel} side {ap.get('side')!r}; not saved")
    side = 1 if ap["side"] == "left" else -1
    data = proj / "data"
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    cp = data / "connectors.local.json"
    conns = json.loads(cp.read_text(encoding="utf-8"))["connectors"] if cp.exists() else []
    lay = mw.mesh_layout([tuple(p) for p in local["points_xyz_m"]], conns)
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    curb = bpy.data.objects.get("CURB")
    if curb is None:
        raise SystemExit("[apron-road] FATAL: no CURB in loop.blend; not saved")
    if len(curb.data.vertices) != lay["_curb_total"]:
        raise SystemExit(f"[apron-road] FATAL: CURB has {len(curb.data.vertices)} vertices, the assembler's layout "
                         f"{lay['_curb_total']}; not saved")
    rows = lay["MAINLINE"]["rows"]
    lo = mw.curb_index(lay, "MAINLINE", 0, side, 0)
    hi = mw.curb_index(lay, "MAINLINE", rows - 1, side, mw.CURB_P - 1)
    bm = bmesh.new()
    bm.from_mesh(curb.data)
    bm.faces.ensure_lookup_table()
    uv = bm.loops.layers.uv.active
    # THE MOUTHS (ledger 0085): the apron is the real paved band all round, and where an infield road leaves across it
    # only the part UNDER that road goes. Every apron-side face moves to the new object; then, per mainline mouth on the
    # apron side, the apron is cut along the road's two edge lines (bmesh bisect, each line fitted on the road's own ROAD
    # rows within REACH_M of its cut) and the fragments between them go; the road's own edge strip (its CURB faces) that
    # lies on the kept apron goes too (FACES_ONLY, CURB keeps its layout). gap_mouths' whole-row window (it removed the
    # apron up to GAP_CORNER_M past the road's footprint at the cut's station) left an unpaved corner the road course's
    # line crossed (drive_test ground over the lane at s 938-941, pp_b3u). gap_mouths runs after and finds no host face
    # left on this side to delete.
    take = [f for f in bm.faces if all(lo <= v.index <= hi for v in f.verts)]
    if len(take) < rows:
        raise SystemExit(f"[apron-road] FATAL: {len(take)} faces on the apron side for {rows} rows; not saved")
    # the new object: its own vertices (a copy), faces, UVs and material slots
    nb = bmesh.new()
    nuv = nb.loops.layers.uv.new("UVMap")
    vmap = {}
    for f in take:
        for v in f.verts:
            if v.index not in vmap:
                vmap[v.index] = nb.verts.new(v.co)
    for f in take:
        nf = nb.faces.new([vmap[v.index] for v in f.verts])
        nf.material_index = f.material_index
        nf.smooth = f.smooth
        if uv is not None:
            for la, lb in zip(f.loops, nf.loops):
                lb[nuv].uv = la[uv].uv
    n_take = len(take)
    bmesh.ops.delete(bm, geom=take, context="FACES_ONLY")
    road = bpy.data.objects.get("ROAD")
    if road is None:
        raise SystemExit("[apron-road] FATAL: no ROAD in loop.blend; not saved")
    RV = [road.matrix_world @ v.co for v in road.data.vertices]
    if len(RV) < lay["_road_total"]:
        raise SystemExit(f"[apron-road] FATAL: ROAD has {len(RV)} vertices < the layout's {lay['_road_total']}; not saved")
    mp = data / "mouths.json"
    mouths = json.loads(mp.read_text(encoding="utf-8")).get("mouths", []) if mp.exists() else []
    cut_rep, curb_gone, cut_pieces = [], 0, []
    for mo in mouths:
        if mo.get("host") != "MAINLINE" or int(mo.get("side", 0)) != side:
            continue
        piece, end = mo.get("piece"), mo.get("end")
        if piece not in lay:
            raise SystemExit(f"[apron-road] FATAL: mouth piece {piece!r} not in the mesh layout; not saved")
        pr = lay[piece]["rows"]
        order = list(range(pr)) if end == "start" else list(range(pr - 1, -1, -1))
        cx, cz = mo["cut_xyz"][0], mo["cut_xyz"][2]

        def rv(r, lane):
            return RV[mw.road_index(lay, piece, r, lane)]
        near = [r for r in order if (rv(r, 1).x - cx) ** 2 + (rv(r, 1).y - cz) ** 2 <= REACH_M ** 2]
        if len(near) < 3:
            raise SystemExit(f"[apron-road] FATAL: mouth {piece} {end}: {len(near)} road rows within {REACH_M} m; not saved")
        lines = []
        for lane in (0, 2):
            P = [(rv(r, lane).x, rv(r, lane).y) for r in near]
            mx = sum(q[0] for q in P) / len(P)
            my = sum(q[1] for q in P) / len(P)
            sxx = sum((q[0] - mx) ** 2 for q in P)
            syy = sum((q[1] - my) ** 2 for q in P)
            sxy = sum((q[0] - mx) * (q[1] - my) for q in P)
            ang = 0.5 * math.atan2(2 * sxy, sxx - syy)
            lines.append(((mx, my), (math.cos(ang), math.sin(ang))))
        for (pc, d) in lines:
            # only the apron near this mouth (the plane runs on across the oval and would split the ring's far side too)
            fz = [f for f in nb.faces
                  if (f.calc_center_median().x - cx) ** 2 + (f.calc_center_median().y - cz) ** 2 <= (REACH_M + 15.0) ** 2]
            geom = list({e for f in fz for e in f.edges}) + list({v for f in fz for v in f.verts}) + fz
            bmesh.ops.bisect_plane(nb, geom=geom, dist=1e-5, plane_co=Vector((pc[0], pc[1], 0.0)),
                                   plane_no=Vector((-d[1], d[0], 0.0)))
        (pL, dL), (pR, dR) = lines
        c0 = rv(near[0], 1)
        c1 = rv(near[-1], 1)
        ax, ay = c1.x - c0.x, c1.y - c0.y
        La = math.hypot(ax, ay) or 1.0
        ax, ay = ax / La, ay / La

        def under_road(x, y):
            sl = (x - pL[0]) * (-dL[1]) + (y - pL[1]) * dL[0]
            sr = (x - pR[0]) * (-dR[1]) + (y - pR[1]) * dR[0]
            u = (x - c0.x) * ax + (y - c0.y) * ay
            return sl * sr < 0.0 and -REACH_M <= u <= La + 2.0
        gone = []
        for f in nb.faces:
            c = f.calc_center_median()
            if under_road(c.x, c.y):
                gone.append(f)
        bmesh.ops.delete(nb, geom=gone, context="FACES")
        cut_rep.append(f"{piece} {end}: {len(gone)} apron fragments under the road")
        cut_pieces.append(piece)
    me = bpy.data.meshes.new(NAME)
    nb.to_mesh(me)
    nb.free()
    for m in curb.data.materials:
        me.materials.append(m)
    ob = bpy.data.objects.new(NAME, me)
    for c in curb.users_collection:
        c.objects.link(ob)
    ob.matrix_world = curb.matrix_world.copy()
    if cut_pieces:
        # the infield roads' own edge strip where it lies on the kept apron (their CURB faces, FACES_ONLY)
        from mathutils.bvhtree import BVHTree
        av = [ob.matrix_world @ v.co for v in me.vertices]
        tree = BVHTree.FromPolygons(av, [list(q.vertices) for q in me.polygons]) if me.polygons else None
        spans = []
        for pc_ in set(cut_pieces):
            b = lay[pc_]
            spans.append((b["curb"], b["curb"] + 2 * b["rows"] * mw.CURB_P))
        doomed = []
        bm.faces.ensure_lookup_table()
        for f in bm.faces:
            idx = [v.index for v in f.verts]
            if not any(a <= min(idx) and max(idx) < b_ for a, b_ in spans):
                continue
            c = curb.matrix_world @ f.calc_center_median()
            if tree is not None and tree.ray_cast(Vector((c.x, c.y, c.z + 5.0)), Vector((0.0, 0.0, -1.0)), 10.0)[0] is not None:
                doomed.append(f)
        bmesh.ops.delete(bm, geom=doomed, context="FACES_ONLY")
        curb_gone = len(doomed)
    bm.to_mesh(curb.data)
    bm.free()
    curb.data.update()
    if len(curb.data.vertices) != lay["_curb_total"]:
        raise SystemExit("[apron-road] FATAL: CURB lost vertices; not saved")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[apron-road] {ap['side']} apron: {n_take} CURB faces ({rows} rows) -> {NAME}; cut along {len(cut_rep)} "
          f"mouth(s): " + "; ".join(cut_rep) + f"; {curb_gone} infield-road strip faces on the apron gone; CURB keeps "
          f"all {lay['_curb_total']} vertices; saved loop.blend")


main()
