"""The median ground between two carriageways at different heights, as the lidar shows it (ledger 0080 2a round 4,
the SD freeway port; Kevin 2026-11-05: "I just want real").

Where I 8's two carriageways share one paved width, tools/median_barrier_blend.py stands a Caltrans Type 60 barrier on
the midline with each side's foot on that side's pavement; where the feet differ (WB 1-4.6 m above the line at Morena,
WB s 6,550-7,000 and 3,100-3,300) the low side's face runs down to the low pavement. The ground there was the prep's: its
contact pin and feather take every ground vertex within 3 m of a road to the NEAREST road's height, so under the barrier
and just past the low pavement's edge the ground stood at the HIGH side's height (ws15: the line's daylight probe 0.8 m
past its median edge found no surface from the line's deck down, s 3,496-3,558: the ground was 4.5 m up, inside the
barrier's body).

The lidar (USGS 2014 QL2 EPT, class 2 ground, the cache the deck reader keeps; heights NAVD88 less the origin's elev_m)
reads those sections as a STEP, not a slope: the high pavement runs flat to the barrier, the low pavement runs flat to
the wall's face, 4.0-4.6 m lower at WB s 6,750-6,950, with nothing between but the barrier (no class-2 return over its
0.6 m). Both pavements read within 0.1 m of the model there (tools/median_lidar.py, median_ground.lidar.json). So the
ground is built as the lidar shows it: on the high side the ground runs to the barrier's high foot; from there to the
low pavement it is at the low pavement's height (under the barrier's body and in the clearance beside its low face).
The terrain is cut along the high foot's line and FOOT_STEP_M inside it first (bmesh bisect, vertical planes, per
SAMPLE_M of each run) so the step is at the foot, not spread over the facet between the two pavements' edges; then every
ground vertex on the low side of the foot, inside the gap, and under no pavement, takes the low pavement's height less
the prep's GROUND_CLEAR. Nothing else moves.

A section counts as stepped where its two feet differ by more than STEP_MIN_M (the barrier tool's own retaining-face
threshold). Opt-in by ship.json prep step `median_ground` (after the prep, before the split); Lake Murray never names it.

    blender --background --python tools/median_ground_blend.py -- <prepped.blend> --project <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy  # noqa: provided by Blender
from mathutils import Vector
from mathutils.bvhtree import BVHTree

AIROSO = Path(__file__).resolve().parents[1]
FOOT_PROBE_M = (0.6, 1.2, 2.0)   # median_barrier_blend's own probe (the same feet)
STEP_MIN_M = 0.3                 # median_barrier_blend's retaining-face threshold (its n_retain), reused
GROUND_CLEAR = 0.02              # engine-july's prep: the ground's contact height under a deck
REACH_M = 2.5                    # [invented] how far either side of the barrier line a gap vertex is looked for
SAMPLE_M = 1.0                   # [invented] the feet are read this often along each run
NO_BAR_M = 1.0                   # [invented] a lidar step whose gap midline is this close to a barrier run is that barrier's (its low face)
DECK_PAD_M = 25.0                # [invented] a lidar step within this of a line deck's declared ends is the deck's (2d)
BURY_M = 0.3                     # median_barrier_blend.BURY_M: a face's foot this far under the low ground
RETAIN_NAME = "1WALL_RETAIN"     # engine-july's 1WALL: collidable, double-sided, the concrete barrier's texture
FOOT_STEP_M = 0.05               # [invented] the step's width: a second cut this far inside the high foot takes the low height


def _blend_xy(x, z):
    # the assembler's remap: local (x = E, y = up, z = N) -> Blender (x, z, y)
    return x, z


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    blend = Path(argv[0]).resolve()
    proj = Path(argv[argv.index("--project") + 1]).resolve()
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    li = cfg.get("lm_intake") or {}
    name = li.get("median_barrier_file")
    if not name:
        print("[median-ground] no lm_intake.median_barrier_file: nothing done")
        return
    src = AIROSO / "tracks" / li["source_track"] / (li.get("source_data") or "data") / name
    doc = json.loads(src.read_text(encoding="utf-8"))
    B = float(doc["barrier"]["base_m"])
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    roads = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith("1ROAD")]
    if not roads:
        raise SystemExit("[median-ground] FATAL: no 1ROAD in the prepped scene")
    rv, rf = [], []
    for o in roads:
        mw = o.matrix_world
        b = len(rv)
        rv += [mw @ v.co for v in o.data.vertices]
        rf += [tuple(b + i for i in p.vertices) for p in o.data.polygons]
    bvh = BVHTree.FromPolygons(rv, rf)
    down = Vector((0, 0, -1))

    def road_z(x, y, top=1e4):
        hit = bvh.ray_cast(Vector((x, y, top)), down, 2e4)
        return None if hit[0] is None else hit[0].z

    # 1. the stepped sections: (x, y, nx, ny pointing to the HIGH side, z_high, z_low), every SAMPLE_M along each run
    secs = []
    n_samples = 0
    for run in doc["runs"]:
        xz = run["xz"]
        for a, b in zip(xz, xz[1:]):
            L = math.dist(a, b)
            if L < 1e-6:
                continue
            tx, ty = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            nx, ny = -ty, tx
            for k in range(max(1, int(L / SAMPLE_M))):
                x, y = a[0] + tx * k * SAMPLE_M, a[1] + ty * k * SAMPLE_M
                n_samples += 1
                feet = {}
                for sg in (1.0, -1.0):
                    for d in FOOT_PROBE_M:
                        z = road_z(x + sg * d * nx, y + sg * d * ny)
                        if z is not None:
                            feet[sg] = z
                            break
                if len(feet) < 2 or abs(feet[1.0] - feet[-1.0]) <= STEP_MIN_M:
                    continue
                hs = 1.0 if feet[1.0] > feet[-1.0] else -1.0
                # (foot point, normal toward the high side, z high, z low, along, half the sample's stretch)
                secs.append((x + hs * nx * B / 2.0, y + hs * ny * B / 2.0, hs * nx, hs * ny, feet[hs], feet[-hs],
                             tx, ty, SAMPLE_M * 0.5))
    n_bar = len(secs)
    # 1b. a STEP the lidar reads where no barrier run stands (tools/median_lidar.py: line | connector stations of kind
    #     "step", at a grade no ground holds): the wall face at the high pavement's edge strip (route.edge's curb face +
    #     connector sidewalk, the built strip), the ground from it to the low pavement at the low height, and a
    #     retaining face (1WALL_RETAIN) from the low ground to the high pavement's edge. Not on a deck (the ground under a
    #     deck is 2d's question) and not within NO_BAR_M of a barrier run (the barrier's low face is the retaining face).
    wall_runs, lid_used, lid_skipped = [], 0, {}
    lname = li.get("median_ground_file")
    if lname:
        lid = json.loads((src.parent / lname).read_text(encoding="utf-8"))
        edge = (cfg.get("route") or {}).get("edge") or {}
        strip = float(edge.get("curb_face_w", 0.0)) + float(edge.get("connector_sidewalk_w", edge.get("sidewalk_w", 0.0)))
        bar_pts = []                     # every barrier run's line, at 0.25 m (the distance to the line, not its stations)
        for run in doc["runs"]:
            for a, b in zip(run["xz"], run["xz"][1:]):
                k = max(1, int(math.dist(a, b) / 0.25))
                bar_pts += [(a[0] + (b[0] - a[0]) * q / k, a[1] + (b[1] - a[1]) * q / k) for q in range(k + 1)]
        from mathutils.kdtree import KDTree as _KD
        bkd = _KD(max(1, len(bar_pts)))
        for k, p in enumerate(bar_pts):
            bkd.insert((p[0], p[1], 0.0), k)
        bkd.balance()
        rep_ = json.loads((proj / "data" / "lm_intake.json").read_text(encoding="utf-8"))
        line_decks = [(float(c) - float(ln_) / 2.0 - DECK_PAD_M, float(c) + float(ln_) / 2.0 + DECK_PAD_M)
                      for c, ln_ in rep_.get("bridges_levelled") or []]
        conns = {c["name"]: c for c in json.loads((proj / "data" / "connectors.local.json").read_text(
            encoding="utf-8")).get("connectors") or []}
        cur = []
        for pname, pair in (lid.get("pairs") or {}).items():
            cdecks = (conns.get(pname) or {}).get("decks_all") or []
            for r in pair["rows"]:
                if r["kind"] != "step":
                    continue
                why = None
                if any(a <= r["s"] <= b for a, b in line_decks):
                    why = "line deck"
                elif any(a - 3 <= r["partner_vertex"] <= b + 3 for a, b in cdecks):
                    why = "connector deck"
                else:
                    nx, ny = r["n"]
                    gx = r["x"] + nx * (r["edges"][0] + r["edges"][1]) / 2.0
                    gy = r["z"] + ny * (r["edges"][0] + r["edges"][1]) / 2.0
                    _c, _i, dbar = bkd.find((gx, gy, 0.0))
                    if bar_pts and dbar is not None and dbar <= NO_BAR_M:
                        why = "barrier run"
                if why:
                    lid_skipped[why] = lid_skipped.get(why, 0) + 1
                    if cur:
                        wall_runs.append(cur); cur = []
                    continue
                # the built edges along the station's normal (toward the partner): the line's last pavement, the partner's first
                nx, ny = r["n"]
                hits = []
                o = r["edges"][0] - 0.6
                while o <= r["edges"][1] + 0.6:
                    hits.append((o, road_z(r["x"] + nx * o, r["z"] + ny * o)))
                    o += 0.05
                yl_, yp_ = r["built_y"]
                low_e = [o for o, z in hits if z is not None and abs(z - yl_) < 0.5]
                par_e = [o for o, z in hits if z is not None and abs(z - yp_) < 0.5]
                if not low_e or not par_e or abs(yp_ - yl_) <= STEP_MIN_M:
                    lid_skipped["edges not found"] = lid_skipped.get("edges not found", 0) + 1
                    continue
                el, ep = max(low_e), min(par_e)
                zl_ = road_z(r["x"] + nx * el, r["z"] + ny * el)
                zp_ = road_z(r["x"] + nx * ep, r["z"] + ny * ep)
                if zp_ > zl_:                    # the partner is high: the face at its edge strip, the normal toward it
                    u, hx, hy, zh_, zlo = ep - strip, nx, ny, zp_, zl_
                else:                            # the line is high: the face at the line's edge strip, toward the line
                    u, hx, hy, zh_, zlo = el + strip, -nx, -ny, zl_, zp_
                fx, fy = r["x"] + nx * u, r["z"] + ny * u
                secs.append((fx, fy, hx, hy, zh_, zlo, -hy, hx, 2.5))
                cur.append((fx, fy, zh_, zlo, -hy, hx))
                lid_used += 1
            if cur:
                wall_runs.append(cur); cur = []
    if not secs:
        print(f"[median-ground] {n_samples} barrier samples, none stepped (> {STEP_MIN_M} m), no lidar step: nothing done")
        return
    from mathutils.kdtree import KDTree
    kd = KDTree(len(secs))
    for i, s in enumerate(secs):
        kd.insert((s[0], s[1], 0.0), i)
    kd.balance()
    import bmesh
    n_bis = n_low = 0
    worst = 0.0
    tiles = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith("1GRASS")]
    for ob in tiles:
        mw = ob.matrix_world
        if any(abs(mw[i][j] - (1.0 if i == j else 0.0)) > 1e-9 for i in range(4) for j in range(4)):
            raise SystemExit(f"[median-ground] FATAL: {ob.name} carries a transform (the prep applies them)")
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        # 2. cut along each stepped section's high foot: a vertical plane through (x, y) + n * B / 2, normal n.
        #    Faces are found through a 4 m hash of their bounding boxes, kept current as the cuts split them.
        cell = 4.0
        grid = {}

        def put(f):
            xs = [v.co.x for v in f.verts]; ys = [v.co.y for v in f.verts]
            for ci in range(int(math.floor(min(xs) / cell)), int(math.floor(max(xs) / cell)) + 1):
                for cj in range(int(math.floor(min(ys) / cell)), int(math.floor(max(ys) / cell)) + 1):
                    grid.setdefault((ci, cj), []).append(f)
        for f in bm.faces:
            put(f)
        touched = False
        for (x, y, nx, ny, zh, zl, tx, ty, half), u0 in ((s_, u_) for s_ in secs for u_ in (0.0, -FOOT_STEP_M)):
            fx, fy = x + nx * u0, y + ny * u0
            r = half + REACH_M
            cand = set()
            for ci in range(int(math.floor((fx - r) / cell)), int(math.floor((fx + r) / cell)) + 1):
                for cj in range(int(math.floor((fy - r) / cell)), int(math.floor((fy + r) / cell)) + 1):
                    cand.update(f for f in grid.get((ci, cj), ()) if f.is_valid)
            geom = []
            for f in cand:
                # the plane's own stretch: faces whose span along the run meets this sample's SAMPLE_M
                al = [(v.co.x - fx) * tx + (v.co.y - fy) * ty for v in f.verts]
                ac = [(v.co.x - fx) * nx + (v.co.y - fy) * ny for v in f.verts]
                if max(al) < -half or min(al) > half or min(ac) > 0.0 or max(ac) < 0.0:
                    continue
                geom.append(f)
            if not geom:
                continue
            geom = geom + list({e for f in geom for e in f.edges}) + list({v for f in geom for v in f.verts})
            res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-4, plane_co=Vector((fx, fy, 0.0)),
                                         plane_no=Vector((nx, ny, 0.0)))
            n_bis += len([g for g in res["geom_cut"] if isinstance(g, bmesh.types.BMVert)])
            for g in res["geom"]:
                if isinstance(g, bmesh.types.BMFace) and g.is_valid:
                    put(g)
            touched = True
        if not touched:
            bm.free()
            continue
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        # 3. every vertex on the low side of the high foot, in the gap, under no pavement: the low pavement's height
        for v in bm.verts:
            co, i, d = kd.find((v.co.x, v.co.y, 0.0))
            if d is None:
                continue
            x, y, nx, ny, zh, zl, tx, ty, half = secs[i]
            if d > half + REACH_M:
                continue
            u = (v.co.x - x) * nx + (v.co.y - y) * ny          # from the high foot, + toward the high side
            if u > -1e-3 or u < -REACH_M or abs((v.co.x - x) * tx + (v.co.y - y) * ty) > half + 0.5:
                continue
            rz = road_z(v.co.x, v.co.y, top=zh + 2.0)
            if rz is not None and rz > zl - 1.0:                # under a pavement (either): the prep's pin stands
                continue
            t = zl - GROUND_CLEAR
            if v.co.z > t:
                worst = max(worst, v.co.z - t)
                v.co.z = t
                n_low += 1
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
    # 4. the retaining face where the lidar's step has no barrier: a vertical wall at the high edge strip's outer line,
    #    from BURY_M under the low ground up to the high pavement (no parapet: the lidar's class 2 shows none, and
    #    nothing is built where nothing shows)
    wv, wf = [], []
    for run in wall_runs:
        # each end carried half a station (2.5 m, the lidar's 5 m spacing) along the section's tangent, so a lone
        # station's step has its face too
        f0, f1 = run[0], run[-1]
        s0 = -1.0 if len(run) == 1 else math.copysign(1.0, (f0[0] - run[1][0]) * f0[4] + (f0[1] - run[1][1]) * f0[5])
        s1 = 1.0 if len(run) == 1 else math.copysign(1.0, (f1[0] - run[-2][0]) * f1[4] + (f1[1] - run[-2][1]) * f1[5])
        run = ([(f0[0] + s0 * 2.5 * f0[4], f0[1] + s0 * 2.5 * f0[5]) + tuple(f0[2:])] + list(run)
               + [(f1[0] + s1 * 2.5 * f1[4], f1[1] + s1 * 2.5 * f1[5]) + tuple(f1[2:])])
        if len(run) == 3:
            run = [run[0], run[2]]
        b0 = len(wv)
        for fx, fy, zh_, zlo, _tx, _ty in run:
            wv += [(fx, fy, zlo - BURY_M), (fx, fy, zh_)]
        for k in range(len(run) - 1):
            a = b0 + 2 * k
            wf.append((a, a + 2, a + 3, a + 1))
    if wf:
        if bpy.data.objects.get(RETAIN_NAME) is not None:
            raise SystemExit(f"[median-ground] FATAL: the scene already has {RETAIN_NAME}")
        me = bpy.data.meshes.new(RETAIN_NAME)
        me.from_pydata(wv, [], wf)
        me.update()
        mat = bpy.data.materials.get("1WALL_MEDIAN_mat") or bpy.data.materials.new(RETAIN_NAME + "_mat")
        me.materials.append(mat)
        ob = bpy.data.objects.new(RETAIN_NAME, me)
        bpy.context.scene.collection.objects.link(ob)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    rep = {"tool": "tools/median_ground_blend.py", "ledger": "0080 2a round 4", "barrier_samples": n_samples,
           "stepped_barrier_samples": n_bar, "lidar_step_sections": lid_used, "lidar_steps_skipped": lid_skipped,
           "retaining_face": {"mesh": RETAIN_NAME if wf else None, "faces": len(wf)},
           "step_m_max": round(max(s[4] - s[5] for s in secs), 2),
           "bisect_vertices": n_bis, "vertices_lowered": n_low, "lowered_max_m": round(worst, 2),
           "params": {"STEP_MIN_M": STEP_MIN_M, "REACH_M": REACH_M, "SAMPLE_M": SAMPLE_M, "GROUND_CLEAR": GROUND_CLEAR,
                      "FOOT_STEP_M": FOOT_STEP_M, "NO_BAR_M": NO_BAR_M, "DECK_PAD_M": DECK_PAD_M, "BURY_M": BURY_M}}
    (proj / "data" / "median_ground.built.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"[median-ground] {n_bar} of {n_samples} barrier samples stepped, {lid_used} lidar steps with no barrier "
          f"(skipped {lid_skipped}); max step {rep['step_m_max']} m: the ground cut at the high foot ({n_bis} new "
          f"vertices), {n_low} vertices to the low pavement (max {worst:.2f} m down); retaining face {len(wf)} quads")


if __name__ == "__main__":
    main()
