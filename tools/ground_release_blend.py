"""Apply data/ground_release.json to loop.blend's TERRAIN, and rail every new drop a car could reach (ledger 0046,
v0.18.0 integration fix round; the plan, the zones and the WHY are in tools/ground_release.py).

Runs INSIDE Blender in the author stage, after the seat and the BEAUTY triangulation (the near-road ground every gate
was tuned on is that triangulation's: nothing outside a zone is touched) and before the median island and the bridge
bodies (which read the ground under each deck):

  1. every TERRAIN edge whose midpoint is in a zone and is longer than SUBDIV_M is halved (rounds), the new faces
     triangulated (BEAUTY) — the creek channel's walls are 7-16 m apart;
  2. every TERRAIN vertex in a zone takes the released height, blended by the zone weight (1 inside, smoothstep to 0
     over ground_release.RAMP_M at the zone's ends and outer edge):
       bank zone: under a ROAD / CURB surface -> unchanged (the prep pins it to the deck, as before);
                  beside it -> 3DEP, never above the nearest pavement edge - CLEAR_M within EDGE_CAP_M of it;
       span zone: under the deck -> min(3DEP, lowest deck over it - CLEAR_M);
                  beside it -> min(3DEP, nearest pavement height - CLEAR_M) (a span zone only ever opens the ground
                  under and beside a bridge; it never raises it over the road);
  3. RAILS: along every zone side, every RAIL_STEP_M, the outer edge of the built pavement (ROAD + CURB, marched out
     from the centreline) and the NEW ground over the next EXC_BAND_M are read exactly as drive_test's excursion sweep
     reads them; where it would file an unguarded drop (a > EXC_DROP_M fall between 0.5 m samples, or the ground more
     than RAIL_FALL_M under the pavement edge) a concrete barrier (a Jersey profile, RAIL_BASE_M wide at the foot,
     RAIL_H_M tall) stands on the outer lip of the curb, padded RAIL_PAD_M past each run. It is appended to GUARDRAIL
     (the prep's 1WALL_guard: physical, double-sided, the loop's own I-8 bridge rail material), never where GUARDRAIL
     already stands within RAIL_DUP_M.
Self-checks (exit 1, loop.blend NOT saved): a zone that moved nothing; a released vertex left above the deck over it;
a rail vertex over a ROAD surface. Writes data/ground_release.report.json.

    blender --background --python-exit-code 1 --python tools/ground_release_blend.py -- <project-dir>
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

AIROSO = Path(__file__).resolve().parents[1]

SUBDIV_M = 2.5        # [invented] zone terrain edges are halved down to this
CLEAR_M = 0.02        # build_kn5_loop.GROUND_CLEAR: ground stands this far under the deck
EDGE_CAP_M = 1.0      # [invented] a bank zone's ground within this of the pavement never rises above its edge
DECK_WIN_M = 3.0      # a deck hit counts within this of the centreline deck height (author_bridges_blend)
XS_STEP_M = 0.25      # cross-section march for the pavement's outer edge
XS_MAX_M = 6.0        # ...at most this far past the nominal half-width (a mouth's side street is not the edge)
RAIL_STEP_M = 1.0     # rail stations along a zone
EXC_BAND_M = 4.0      # drive_test: the excursion band past the BUILT pavement edge
EXC_STEP_M = 0.5      # drive_test: lateral sample step
EXC_SCAN_M = 0.125    # read at a quarter of it, every 0.5 m pair compared (drive_test's phase is its own centreline's)
EXC_DROP_M = 0.12     # drive_test: a fall between samples larger than this is an excursion drop
RAIL_FALL_M = 0.5     # [invented] ...and a total fall under the pavement edge larger than this gets a rail too
RAIL_PAD_M = 3.0      # [invented] a rail runs this far past its run at each end
RAIL_GAP_M = 4.0      # [invented] runs closer than this merge
RAIL_MIN_M = 6.0      # [invented] no rail shorter than this
RAIL_DUP_M = 2.0      # [invented] no new rail within this of an existing GUARDRAIL vertex (the I-8 bridge rails)
RAIL_IN_M = 0.30      # the rail's centre stands this far inside the pavement's outer edge (on the curb's lip)
RAIL_BASE_M = 0.60    # Jersey barrier: foot width (drive_test probes every 0.5 m: a thinner one could fall between)
RAIL_TOP_M = 0.20     # ...top width
RAIL_H_M = 0.81       # ...height above its base (the standard 32 in)
RAIL_SINK_M = 0.30    # ...and its foot runs this far into the curb


def _release_module():
    spec = importlib.util.spec_from_file_location("_airoso_ground_release", AIROSO / "tools" / "ground_release.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bvh(objs):
    vs, fs = [], []
    for ob in objs:
        me = ob.data
        base = len(vs)
        vs += [tuple(ob.matrix_world @ v.co) for v in me.vertices]
        fs += [tuple(base + i for i in p.vertices) for p in me.polygons]
    return BVHTree.FromPolygons(vs, fs) if fs else None


def _hits(tree, x, y, top, bottom):
    out = []
    z = top
    for _ in range(12):
        h = tree.ray_cast(Vector((x, y, z)), Vector((0, 0, -1)), z - bottom)
        if h[0] is None:
            break
        out.append(h[0].z)
        z = h[0].z - 1e-4
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    rp = data / "ground_release.json"
    if not rp.exists():
        print("[release] no data/ground_release.json (no zones declared) — nothing to do")
        return
    GR = _release_module()
    R = json.loads(rp.read_text(encoding="utf-8"))
    cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in cl["points_xyz_m"]]
    Z = GR.Zones(pts, cl["widths_m"], R["zones"])
    L = GR.Lattice(R["cell_m"], R["I"], R["J"], R["h"])

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    ob = bpy.data.objects.get("TERRAIN")
    if ob is None:
        raise SystemExit("[release] no TERRAIN object")
    deck_objs = [o for o in (bpy.data.objects.get("ROAD"), bpy.data.objects.get("CURB")) if o is not None]
    road_obj = bpy.data.objects.get("ROAD")
    deck = _bvh(deck_objs)
    road_only = _bvh([road_obj]) if road_obj is not None else None
    if deck is None:
        raise SystemExit("[release] no ROAD/CURB deck")
    pv = [tuple(o.matrix_world @ v.co) for o in deck_objs for v in o.data.vertices]
    kd = KDTree(len(pv))
    for i, v in enumerate(pv):
        kd.insert((v[0], v[1], 0.0), i)
    kd.balance()

    def near_pave(x, y):
        co, i, d = kd.find((x, y, 0.0))
        return (d, pv[i][2]) if co is not None else (None, None)

    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    v0 = len(bm.verts)
    # 1. subdivide inside the zones
    n_sub = 0
    for _round in range(6):
        todo = []
        for e in bm.edges:
            if e.calc_length() <= SUBDIV_M:
                continue
            a, b = e.verts[0].co, e.verts[1].co
            if Z.weight((a.x + b.x) / 2, (a.y + b.y) / 2)[0] > 0.0 or Z.weight(a.x, a.y)[0] > 0.0 \
                    or Z.weight(b.x, b.y)[0] > 0.0:
                todo.append(e)
        if not todo:
            break
        new = bmesh.ops.subdivide_edges(bm, edges=todo, cuts=1, use_grid_fill=True)
        n_sub += len(todo)
        faces = {f for g in new.get("geom", []) if isinstance(g, bmesh.types.BMVert) for f in g.link_faces}
        faces = [f for f in faces if len(f.verts) > 3]
        if faces:
            bmesh.ops.triangulate(bm, faces=faces, quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.faces.ensure_lookup_table()
    leftover = [f for f in bm.faces if len(f.verts) > 3]
    if leftover:
        bmesh.ops.triangulate(bm, faces=leftover, quad_method="BEAUTY", ngon_method="BEAUTY")
    # 2. released heights
    per_zone = {z["name"]: {"moved": 0, "max_down_m": 0.0, "max_up_m": 0.0, "under_deck": 0} for z in R["zones"]}
    bad_poke = []
    n_nodata = 0
    for v in bm.verts:
        x, y, z = v.co.x, v.co.y, v.co.z
        w, zone = Z.weight(x, y)
        if w <= 0.0:
            continue
        D = L.at(x, y)
        if D is None:
            n_nodata += 1
            continue
        hs = _hits(deck, x, y, 10000.0, -1000.0)
        under = bool(hs)
        if zone["kind"] == "bank":
            if under:
                continue
            t = D
            d, ph = near_pave(x, y)
            if d is not None and d <= EDGE_CAP_M:
                t = min(t, ph - CLEAR_M)
        else:
            if under:
                t = min(D, min(hs) - CLEAR_M)
                per_zone[zone["name"]]["under_deck"] += 1
            else:
                d, ph = near_pave(x, y)
                t = min(D, ph - CLEAR_M) if ph is not None else D
        nz = z + w * (t - z)
        if abs(nz - z) < 1e-4:
            continue
        rec = per_zone[zone["name"]]
        rec["moved"] += 1
        rec["max_down_m"] = round(max(rec["max_down_m"], z - nz), 3)
        rec["max_up_m"] = round(max(rec["max_up_m"], nz - z), 3)
        v.co.z = nz
        if under and nz > min(hs) - CLEAR_M + 1e-4:
            bad_poke.append((round(x, 1), round(y, 1), round(nz, 2), round(min(hs), 2)))
    bm.to_mesh(me)
    bm.free()
    me.update()
    idle = [n for n, r in per_zone.items() if r["moved"] == 0]
    if idle or bad_poke:
        raise SystemExit(f"[release] FATAL: zones that moved nothing {idle}; {len(bad_poke)} released vertices over the "
                         f"deck {bad_poke[:4]} — loop.blend NOT saved")

    # 3. rails
    ground = _bvh([ob])
    grd = bpy.data.objects.get("GUARDRAIL")
    gv = [tuple(grd.matrix_world @ v.co) for v in grd.data.vertices] if grd is not None else []
    gkd = KDTree(max(1, len(gv)))
    for i, p in enumerate(gv):
        gkd.insert((p[0], p[1], 0.0), i)
    gkd.balance()

    def deck_at(x, y, yref):
        hs = _hits(deck, x, y, yref + DECK_WIN_M, yref - DECK_WIN_M)
        return max(hs) if hs else None

    def ground_at(x, y, top):
        hs = _hits(ground, x, y, top, top - 200.0)
        return hs[0] if hs else None

    rails = []
    for zone in R["zones"]:
        a, b = float(zone["s_m"][0]), float(zone["s_m"][1])
        for side in zone["sides"]:
            st = []
            s = a
            while s <= b + 1e-6:
                k = max(0, min(len(Z.s) - 2, next((i for i in range(len(Z.s) - 1) if Z.s[i + 1] >= s), len(Z.s) - 2)))
                u = (s - Z.s[k]) / max(1e-9, Z.s[k + 1] - Z.s[k])
                cx = Z.P[k][0] + (Z.P[k + 1][0] - Z.P[k][0]) * u
                cy = Z.P[k][1] + (Z.P[k + 1][1] - Z.P[k][1]) * u
                cz = pts[k][1] + (pts[k + 1][1] - pts[k][1]) * u
                tx, ty = Z.T[k]
                nx, ny = -ty * side, tx * side
                hw = Z.W[k] / 2.0
                o, e, ye, ylast = 0.0, None, None, cz
                ended = False
                while o < hw + XS_MAX_M:
                    o += XS_STEP_M
                    yh = deck_at(cx + nx * o, cy + ny * o, ylast)
                    if yh is None:
                        if o > hw:
                            ended = True
                            break
                        continue
                    e, ye, ylast = o, yh, yh
                if not ended:
                    e = None                 # still on pavement XS_MAX_M past the half-width (a junction): no edge here
                need = False
                if e is not None:
                    # drive_test's excursion rule, read finer than it reads it (it steps 0.5 m from its own centreline,
                    # this every EXC_SCAN_M from this one, any 0.5 m pair): the highest surface (pavement or the NEW
                    # ground), a fall of more than EXC_DROP_M between two points 0.5 m apart from the nominal edge
                    # less 0.5 m out to EXC_BAND_M past the built edge, or the ground RAIL_FALL_M under the edge
                    prof = []
                    off = max(0.0, hw - 0.5)
                    while off <= e + EXC_BAND_M + 0.5 + 1e-6:
                        x, y = cx + nx * off, cy + ny * off
                        d = deck_at(x, y, ye) if off <= e + 1e-6 else None
                        g = ground_at(x, y, ye + 30.0)
                        top = max(v for v in (d, g, ye - 50.0) if v is not None)
                        prof.append((off, top))
                        off += EXC_SCAN_M
                    k = int(round(EXC_STEP_M / EXC_SCAN_M))
                    for j in range(len(prof) - k):
                        if prof[j][0] <= e + EXC_BAND_M and prof[j][1] - prof[j + k][1] > EXC_DROP_M:
                            need = True
                            break
                    gs = [t for o2, t in prof if o2 > e]
                    if gs and ye - min(gs) > RAIL_FALL_M:
                        need = True
                st.append({"s": s, "c": (cx, cy), "n": (nx, ny), "t": (tx * side, ty * side), "e": e, "ye": ye,
                           "need": need and e is not None})
                s += RAIL_STEP_M
            runs = []
            for i, r in enumerate(st):
                if not r["need"]:
                    continue
                if runs and (r["s"] - st[runs[-1][1]]["s"]) <= RAIL_GAP_M:
                    runs[-1][1] = i
                else:
                    runs.append([i, i])
            pad = int(round(RAIL_PAD_M / RAIL_STEP_M))
            for i0, i1 in runs:
                i0, i1 = max(0, i0 - pad), min(len(st) - 1, i1 + pad)
                seg = [r for r in st[i0:i1 + 1] if r["e"] is not None]
                # never on top of an existing rail (the I-8 bridge rails)
                keep = []
                for r in seg:
                    px = r["c"][0] + r["n"][0] * (r["e"] - RAIL_IN_M)
                    py = r["c"][1] + r["n"][1] * (r["e"] - RAIL_IN_M)
                    if gv and gkd.find((px, py, 0.0))[2] <= RAIL_DUP_M:
                        keep.append(None)
                    else:
                        keep.append(r)
                cur = []
                for r in keep + [None]:
                    if r is not None:
                        cur.append(r)
                        continue
                    if len(cur) >= 2 and cur[-1]["s"] - cur[0]["s"] >= RAIL_MIN_M:
                        rails.append({"zone": zone["name"], "side": side, "rows": cur})
                    cur = []

    bmr = bmesh.new()
    if grd is not None:
        bmr.from_mesh(grd.data)
    n_rail_v0 = len(bmr.verts)
    prof = [(-RAIL_BASE_M / 2, -RAIL_SINK_M), (-RAIL_BASE_M / 2, 0.0), (-RAIL_TOP_M / 2, RAIL_H_M),
            (RAIL_TOP_M / 2, RAIL_H_M), (RAIL_BASE_M / 2, 0.0), (RAIL_BASE_M / 2, -RAIL_SINK_M)]
    bad_rail = []
    rail_rep = []
    for rl in rails:
        rings = []
        for r in rl["rows"]:
            (cx, cy), (nx, ny) = r["c"], r["n"]
            o = r["e"] - RAIL_IN_M
            bx, by = cx + nx * o, cy + ny * o
            base = deck_at(bx, by, r["ye"])
            base = (r["ye"] if base is None else base) - 0.05
            ring = []
            for lat, h in prof:
                ring.append(bmr.verts.new((bx + nx * lat, by + ny * lat, base + h)))
            rings.append(ring)
        for ra, rb in zip(rings, rings[1:]):
            for k in range(len(prof) - 1):
                bmr.faces.new((ra[k], ra[k + 1], rb[k + 1], rb[k]))
        for ring in (rings[0], rings[-1]):
            bmr.faces.new(ring[1:5])
        for ring in rings:
            for v in ring:
                if road_only is not None:
                    h = road_only.ray_cast(Vector((v.co.x, v.co.y, v.co.z + 2.0)), Vector((0, 0, -1)), 3.5)
                    if h[0] is not None:
                        bad_rail.append((round(v.co.x, 1), round(v.co.y, 1)))
        rail_rep.append({"zone": rl["zone"], "side": "left" if rl["side"] > 0 else "right",
                         "s_m": [round(rl["rows"][0]["s"], 1), round(rl["rows"][-1]["s"], 1)],
                         "length_m": round(rl["rows"][-1]["s"] - rl["rows"][0]["s"], 1)})
    if bad_rail:
        bmr.free()
        raise SystemExit(f"[release] FATAL: {len(bad_rail)} rail vertices over a ROAD surface {bad_rail[:4]} — "
                         f"loop.blend NOT saved")
    if rails:
        if grd is None:
            gme = bpy.data.meshes.new("GUARDRAIL")
            grd = bpy.data.objects.new("GUARDRAIL", gme)
            bpy.context.scene.collection.objects.link(grd)
        bmr.normal_update()
        bmr.to_mesh(grd.data)
        grd.data.update()
    bmr.free()
    rep = {"_doc": "tools/ground_release_blend.py (ledger 0046 v0.18.0 integration fix round)",
           "terrain_vertices": [v0, len(me.vertices)], "edges_halved": n_sub, "no_data_vertices": n_nodata,
           "zones": per_zone, "rails": rail_rep}
    (data / "ground_release.report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[release] TERRAIN {v0} -> {len(me.vertices)} verts ({n_sub} edges halved in the zones); " + "; ".join(
        f"{n}: {r['moved']} moved (down <= {r['max_down_m']} m, up <= {r['max_up_m']} m, {r['under_deck']} under a deck)"
        for n, r in per_zone.items()) + f"; {len(rail_rep)} rail(s) "
        f"{[(r['zone'], r['side'], r['s_m']) for r in rail_rep]} on the curb lip; saved loop.blend")


main()
