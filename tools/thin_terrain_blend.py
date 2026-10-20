"""Thin the prepped scene's terrain (1GRASS_* and GRASS_FAR_* tiles) without moving any vertex — ledger 0054 P3 repair
round 3 (the road kn5 grew from v0.18.1's 73.6 MB to 116-123 MB; 1GRASS 818-942k vertices on r2run3 / r2run2, 55 %).

WHERE THE VERTICES CAME FROM (r2run2 vs v0.18.1, TERRAIN through the chain): the assembler's tiers 163k -> 229.8k (the
new roads' 5 m band); the seat 174k -> 372.6k (137,015 edges halved under the welded approaches and the host edges, 37,707
of them to 0.75 m under the host lanes at 28 exact-deck mouths); the ground release 200k -> 732.8k (44 zones, 35 of them
round 1's auto cuts, halved to 2.5 m and to 1 m at the pavement edge; round 2's 1 m cut toe, ~120k, dropped again in
273b116); the stubs and pads ~32k; the prep's corridor subdivision (80k edges) and kept-cell refinement (106k) on top. Each
pass halves edges so the next has vertices to move; most of the vertices it made were never moved: 268k of the 555k within
20 m of a pavement lay in their neighbours' plane to 2 mm.

WHAT. Runs INSIDE Blender on the PREPPED scene (blender/<slug>.blend, after scripts/ac/build_kn5_loop.py: the ground is
final — pinned, feathered, refined, houses seated — and tiled), before the freeway drape and the split. Each terrain tile
is thinned by tools/terrain_thin.py (greedy half-edge collapse, the deviation from the chain's own surface bounded exactly
over every star, accumulated per triangle; its module doc) in parallel worker processes, then rebuilt with the prep's own
planar UVs, material and smooth shading. No vertex moves, no vertex is made: every vertex that ships is one the chain
placed (3DEP, the graded or released ground — real ridges kept, L3).

HOW FAR THE SURFACE MAY MOVE (the plan distance to the pavement — 1ROAD / 1KERB, the race kerbs left out as
data/track.obj leaves them — read exactly on the flattened pavement):
  * under the pavement: up UNDER_UP_M, down UNDER_DOWN_M;  beside it to NEAR_EXACT_M (the drive gates' excursion band):
    +- TOL_NEAR_M;  to NEAR_ROAD_M: +- TOL_M;  beyond: +- FAR_TOL_M, from FAR_EDGE_FROM_M out +- FAR_TOL_OUT_M;
  * within HOUSE_CLEAR_M of a building, at a hole-fill n-gon, on a near-vertical face, on a tile seam: nothing changes.
WHAT tools/rib_check.py READS STAYS ITS OWN (it gates the ground past its NEAR_M, 20 m, to the nearest pavement VERTEX):
  * its lattice: every removed vertex that lay ON the lattice (a node, or a vertex on a lattice line) is written to
    data/terrain_thin.nodes.json.gz and rib_check reads it as it read the vertex — a node's height off the BUILT surface;
  * its cross-grain cells: a fold (a plain cell's diagonal leaning across the grain by more than terrain_thin.HALF_CELL_EX)
    whose centre is past CELL_LOCK_M keeps its corners, and no new plain cell leans across the grain;
  * its step jogs (risers of 35 deg+ on finest-tier triangles, <= 7.6 m): from JOG_ZONE_M out, a star with a triangle
    steeper than terrain_thin.NZ_FINE keeps every new edge under FINE_CAP_M.
Self-checks (exit 1, the blend NOT saved): at every removed vertex the thinned surface lies within that vertex's own
tolerance of where the vertex stood; every face the thinning made faces up, and no tile has more faces not facing up than
before; every tile kept its material. Writes data/terrain_thin.json (per tile, the parameters) and the nodes file.

    blender --background --python-exit-code 1 --python tools/thin_terrain_blend.py -- <prepped.blend> --project <proj>
            [--jobs N]
"""
from __future__ import annotations

import gzip
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import terrain_thin as TT  # noqa: E402

UNDER_UP_M = 0.005      # [invented] under the pavement's own footprint the ground may rise this much (the prep pins it
#                         0.02 under the deck; verify_fold_fans fails grass 0.02 over the pavement, the worst today 0.003)...
UNDER_DOWN_M = 0.015    # [invented] ...and fall this much (0.035 under the deck: the ground gate's contact line is 0.05)
NEAR_EXACT_M = 6.0      # [invented] beside the pavement out to the drive gates' 4 m excursion band (+2 m)...
TOL_NEAR_M = 0.005      # [invented] ...+- this (an excursion is a 0.12 m fall between 0.5 m samples)
NEAR_ROAD_M = 22.0      # [invented] the task's near-road band (20 m) + 2 m: inside it...
TOL_M = 0.03            # [invented] ...+- this (the near-road ground may not move more than 0.05 m)
FAR_TOL_M = 0.10        # [invented] beyond it: +- this — every vertex kept is still the chain's 3DEP / graded height,
#                         and the surface between them stays within 10 cm of the one the chain built (ridges kept)...
FAR_TOL_OUT_M = 0.15    # [invented] ...+- this from FAR_EDGE_FROM_M out (the 20 / 40 m tiers, the far ring)
JOG_ZONE_M = 12.0       # [invented] from this far out (to the nearest pavement VERTEX, as rib_check reads it) a star
FINE_CAP_M = 7.5        #   with a triangle steeper than terrain_thin.NZ_FINE (old or new) gets no edge longer than this:
#                         rib_check's step-jog measure reads risers (35 deg+) on finest-tier triangles (JOG_CELL_MAX_M
#                         7.6) beyond its NEAR_M — a triangle that could carry a riser never grows out of its reach
CELL_LOCK_M = 18.0      # [invented] a half lattice cell whose centre is this far out stays (the cross-grain measure,
#                         gated past 20 m); no new half cell is ever made
HOUSE_CLEAR_M = 2.0     # [invented] the ground within this of a building's plan stays (the prep seated it there)
MAX_EDGE_NEAR_M = 8.0   # [invented] the longest new edge within NEAR_EXACT_M of the pavement
MAX_EDGE_M = 20.0       # [invented] ...and elsewhere within FAR_EDGE_FROM_M (the 5 m tier reaches 60 m out)...
FAR_EDGE_FROM_M = 60.0  # terrain.tier_options: 5 m cells within 60 m of a pavement, 20 / 40 m cells beyond
MAX_EDGE_FAR_M = 40.0   # [invented] ...and beyond it (the far tiers' own 20-40 m cells)
ON_LATTICE = 0.01       # tools/rib_check.ON_LATTICE (base units)
PAVEMENT = ("1ROAD", "1KERB")
NOT_PAVEMENT = ("1KERB_RACE",)     # the race kerbs ride in the race kn5, not in data/track.obj
BUILDINGS = ("BUILDING", "HOUSE")
NODES_FILE = "terrain_thin.nodes.json.gz"
TERRAIN = ("1GRASS", "GRASS_FAR")   # the prep's terrain tiles (TERRAIN_TILES): physical ground + the visual far ring


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    blend = Path(argv[0])
    proj = Path(argv[argv.index("--project") + 1])
    jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else max(1, min(16, (os.cpu_count() or 2) - 2))
    return blend, proj, jobs


def _flat_bvh(prefixes, exclude=()):
    vs, fs = [], []
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        up = ob.name.upper()
        if not up.startswith(prefixes) or up.startswith(exclude):
            continue
        mw = ob.matrix_world
        base = len(vs)
        for v in ob.data.vertices:
            w = mw @ v.co
            vs.append((w.x, w.y, 0.0))
        fs.extend([base + i for i in p.vertices] for p in ob.data.polygons)
    return (BVHTree.FromPolygons(vs, fs, epsilon=0.0) if fs else None), vs


def main():
    t0 = time.time()
    blend, proj, jobs = _args()
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    pav_bvh, pav_v = _flat_bvh(PAVEMENT, NOT_PAVEMENT)
    if pav_bvh is None:
        raise SystemExit("[thin] no pavement in the scene")
    kd = KDTree(len(pav_v))
    for i, p in enumerate(pav_v):
        kd.insert(p, i)
    kd.balance()
    house_bvh, _ = _flat_bvh(BUILDINGS)
    tiers = json.loads(gzip.decompress((proj / "data" / "terrain.tiers.json.gz").read_bytes()).decode("utf-8"))
    x0, z0, ux, uz = tiers["frame"]       # local (x = E, z = N) = Blender (x, y)

    tiles = sorted((o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith(TERRAIN)),
                   key=lambda o: o.name)
    if not tiles:
        print("[thin] no terrain tile — nothing to do")
        return
    work = Path(tempfile.mkdtemp(prefix="thin_"))
    jobs_in = []
    meta = {}
    n_far = n_house = n_cell = n_ngons_all = 0
    for ob in tiles:
        me = ob.data
        if ob.matrix_world != ob.matrix_world.Identity(4):
            raise SystemExit(f"[thin] {ob.name} carries a transform — the prep leaves terrain tiles at identity")
        X = [v.co.x for v in me.vertices]; Y = [v.co.y for v in me.vertices]; Z = [v.co.z for v in me.vertices]
        tris, ngons = [], []
        for p in me.polygons:
            (tris if len(p.vertices) == 3 else ngons).append(tuple(p.vertices))
        n = len(X)
        tol_u = [0.0] * n; tol_d = [0.0] * n; cap = [0.0] * n; lock = [False] * n
        n_ngon = 0
        for f in ngons:                       # the prep's holes_fill n-gons pass through as they are, their corners kept
            for w in f:
                if not lock[w]:
                    lock[w] = True; n_ngon += 1
        keys = [None] * n
        fine = [0.0] * n
        for i in range(n):
            x, y = X[i], Y[i]
            d_exact = pav_bvh.find_nearest((x, y, 0.0), 1e5)[3]
            d_vert = kd.find((x, y, 0.0))[2]
            fi, fj = (x - x0) / ux, (y - z0) / uz
            I, J = round(fi), round(fj)
            on_i, on_j = abs(fi - I) < ON_LATTICE, abs(fj - J) < ON_LATTICE
            if on_i and on_j:
                keys[i] = (I, J)
            if lock[i]:
                continue                      # tolerance 0: no star holding it changes
            if house_bvh is not None and house_bvh.find_nearest((x, y, 0.0), HOUSE_CLEAR_M)[0] is not None:
                lock[i] = True; n_house += 1
                continue
            if d_exact is None or d_exact >= NEAR_ROAD_M:
                n_far += 1
                if d_exact is None or d_exact >= FAR_EDGE_FROM_M:
                    tol_u[i] = tol_d[i] = FAR_TOL_OUT_M; cap[i] = MAX_EDGE_FAR_M
                else:
                    tol_u[i] = tol_d[i] = FAR_TOL_M; cap[i] = MAX_EDGE_M
            elif d_exact <= 1e-4:
                tol_u[i] = UNDER_UP_M; tol_d[i] = UNDER_DOWN_M; cap[i] = MAX_EDGE_NEAR_M
            elif d_exact <= NEAR_EXACT_M:
                tol_u[i] = tol_d[i] = TOL_NEAR_M; cap[i] = MAX_EDGE_NEAR_M
            else:
                tol_u[i] = tol_d[i] = TOL_M; cap[i] = MAX_EDGE_M
            if d_vert >= JOG_ZONE_M:
                fine[i] = FINE_CAP_M
        # the cross-grain measure's FOLDS past CELL_LOCK_M stay: a plain lattice cell drawn as two triangles whose
        # diagonal leans across the grain by more than HALF_CELL_EX (taking one away could only hide a fold; a cell
        # that is no fold may go — the measure cannot count it either way)
        by_diag = {}
        for a, b, c in tris:
            ka, kb, kc = keys[a], keys[b], keys[c]
            if ka is None or kb is None or kc is None:
                continue
            for p_, q_, o_ in ((a, b, c), (b, c, a), (c, a, b)):
                kp, kq, ko = keys[p_], keys[q_], keys[o_]
                dI, dJ = abs(kp[0] - kq[0]), abs(kp[1] - kq[1])
                if dI and dI == dJ and ko[0] in (kp[0], kq[0]) and ko[1] in (kp[1], kq[1]) and ko not in (kp, kq):
                    by_diag.setdefault((min(p_, q_), max(p_, q_)), []).append(o_)
                    break
        for (p_, q_), opp in by_diag.items():
            if len(opp) != 2 or opp[0] == opp[1]:
                continue
            if abs(Z[p_] - Z[q_]) - abs(Z[opp[0]] - Z[opp[1]]) <= TT.HALF_CELL_EX:
                continue
            kp, kq = keys[p_], keys[q_]
            cx, cy = x0 + (kp[0] + kq[0]) / 2 * ux, z0 + (kp[1] + kq[1]) / 2 * uz
            if kd.find((cx, cy, 0.0))[2] > CELL_LOCK_M:
                for w in (p_, q_, opp[0], opp[1]):
                    if not lock[w]:
                        lock[w] = True; n_cell += 1
        uvl = me.uv_layers.active
        uv_scale = None
        if uvl is not None:
            for lp in me.loops:
                co = me.vertices[lp.vertex_index].co
                u = uvl.data[lp.index].uv
                if abs(u[0]) > 1e-6 and abs(u[1]) > 1e-6:
                    uv_scale = (co.x / u[0], co.y / u[1])
                    break
        smooth = all(p.use_smooth for p in me.polygons)
        mats = [m for m in me.materials]
        fin = work / f"{ob.name}.in.json"; fout = work / f"{ob.name}.out.json"
        fin.write_text(json.dumps({"X": X, "Y": Y, "Z": Z, "tris": tris, "tol_up": tol_u, "tol_dn": tol_d,
                                   "max_edge": cap, "locked": lock, "lattice": keys, "fine_cap": fine}),
                       encoding="utf-8")
        jobs_in.append((ob.name, fin, fout))
        meta[ob.name] = {"X": X, "Y": Y, "Z": Z, "tol_u": tol_u, "tol_d": tol_d, "uv_scale": uv_scale,
                         "smooth": smooth, "mats": mats, "n": n, "keys": keys, "f": len(tris) + len(ngons), "ngons": ngons,
                         "tri_set": {tuple(sorted(t)) for t in tris},
                         "down": sum(1 for p in me.polygons if p.normal.z <= 0.0)}
        n_ngons_all += n_ngon
    print(f"[thin] {len(tiles)} tiles, {sum(m['n'] for m in meta.values())} vertices read; stars left alone: "
          f"{n_house} vertices within {HOUSE_CLEAR_M:g} m of a building; {n_far} at {NEAR_ROAD_M:g} m or more from the "
          f"pavement (+- {FAR_TOL_M:g} m); kept as rib_check inputs: {n_cell} corners of cross-grain cells "
          f"(centre > {CELL_LOCK_M:g} m); {n_ngons_all} corners of the prep's hole-fill n-gons ({time.time() - t0:.0f} s)")
    py = sys.executable if sys.executable and "python" in Path(sys.executable).name.lower() else "python"
    running, pending, done = [], list(jobs_in), {}
    while pending or running:
        while pending and len(running) < jobs:
            name, fin, fout = pending.pop(0)
            running.append((name, fout, subprocess.Popen([py, "-I", str(HERE / "terrain_thin.py"), "worker",
                                                          str(fin), str(fout)])))
        time.sleep(0.5)
        for r in list(running):
            if r[2].poll() is not None:
                running.remove(r)
                if r[2].returncode != 0:
                    raise SystemExit(f"[thin] worker for {r[0]} exited {r[2].returncode}")
                done[r[0]] = json.loads(r[1].read_text(encoding="utf-8"))
    print(f"[thin] workers done ({time.time() - t0:.0f} s)")

    bad, rep = [], {"_doc": "tools/thin_terrain_blend.py (ledger 0054 P3 repair round 3)",
                    "params": {"under_up_m": UNDER_UP_M, "under_down_m": UNDER_DOWN_M, "near_exact_m": NEAR_EXACT_M, "tol_near_m": TOL_NEAR_M,
                               "near_road_m": NEAR_ROAD_M, "tol_m": TOL_M, "far_tol_m": FAR_TOL_M,
                               "far_tol_out_m": FAR_TOL_OUT_M,
                               "jog_zone_m": JOG_ZONE_M, "fine_cap_m": FINE_CAP_M, "nz_fine": TT.NZ_FINE,
                               "half_cell_ex_m": TT.HALF_CELL_EX,
                               "max_edge_far_m": MAX_EDGE_FAR_M, "far_edge_from_m": FAR_EDGE_FROM_M,
                               "cell_lock_m": CELL_LOCK_M, "house_clear_m": HOUSE_CLEAR_M,
                               "max_edge_near_m": MAX_EDGE_NEAR_M, "max_edge_m": MAX_EDGE_M, "aspect": TT.ASPECT,
                               "nz_lock": TT.NZ_LOCK},
                    "tiles": {}}
    worst = [0.0, 0.0]
    new_meshes = {}
    removed_nodes = []
    for ob in tiles:
        m, r = meta[ob.name], done[ob.name]
        X, Y, Z = m["X"], m["Y"], m["Z"]
        alive, tris = r["alive"], [tuple(t) for t in r["tris"]]
        # self-check 1: at every removed vertex the thinned surface lies within the vertex's own tolerance
        fan = [(f[0], f[k], f[k + 1]) for f in m["ngons"] for k in range(1, len(f) - 1)]
        at = TT.surface_at(X, Y, Z, tris + fan, None, None)
        for i in range(m["n"]):
            if alive[i]:
                continue
            zs = at(X[i], Y[i])
            if not zs:
                bad.append(f"{ob.name}: no surface over removed vertex {i} ({X[i]:.2f}, {Y[i]:.2f})")
                continue
            dz = min(zs, key=lambda z: abs(z - Z[i])) - Z[i]
            worst[0] = min(worst[0], dz); worst[1] = max(worst[1], dz)
            if dz > m["tol_u"][i] + 1e-4 or dz < -m["tol_d"][i] - 1e-4:
                bad.append(f"{ob.name}: removed vertex {i} ({X[i]:.2f}, {Y[i]:.2f}) now {dz:+.4f} m off (tolerance "
                           f"+{m['tol_u'][i]} / -{m['tol_d'][i]})")
        # self-check 2: every face the thinning made faces up (the chain's own vertical faces — a riser, a mended
        # sliver — are kept as they were, their corners locked)
        old_f = m["tri_set"]
        for a, b, c in tris:
            if tuple(sorted((a, b, c))) in old_f:
                continue
            if (X[b] - X[a]) * (Y[c] - Y[a]) - (Y[b] - Y[a]) * (X[c] - X[a]) <= 0.0:
                bad.append(f"{ob.name}: a thinned face does not face up at ({X[a]:.2f}, {Y[a]:.2f})")
                break
        new_meshes[ob.name] = (alive, tris)
        for i in range(m["n"]):
            if not alive[i]:
                fi, fj = (X[i] - x0) / ux, (Y[i] - z0) / uz
                if abs(fi - round(fi)) < ON_LATTICE or abs(fj - round(fj)) < ON_LATTICE:
                    removed_nodes.append([round(X[i], 4), round(Y[i], 4)])
        rep["tiles"][ob.name] = {"vertices": [m["n"], sum(alive)], "faces": [m["f"], len(tris) + len(m["ngons"])],
                                 "collapse": r["stats"]}
    if bad:
        raise SystemExit(f"[thin] self-check FAILED ({len(bad)}; the blend NOT saved): " + "; ".join(bad[:8]))
    for ob in tiles:
        m = meta[ob.name]
        alive, tris = new_meshes[ob.name]
        remap, verts = {}, []
        for i in range(m["n"]):
            if alive[i]:
                remap[i] = len(verts)
                verts.append((m["X"][i], m["Y"][i], m["Z"][i]))
        me = ob.data
        me.clear_geometry()
        me.from_pydata(verts, [], [(remap[a], remap[b], remap[c]) for a, b, c in tris]
                       + [tuple(remap[w] for w in f) for f in m["ngons"]])
        me.update()
        if [mm for mm in me.materials] != m["mats"]:
            raise SystemExit(f"[thin] {ob.name} lost its material (the blend NOT saved)")
        if m["uv_scale"] is not None:
            su, sv = m["uv_scale"]
            uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
            for lp in me.loops:
                co = me.vertices[lp.vertex_index].co
                uv.data[lp.index].uv = (co.x / su, co.y / sv)
        if m["smooth"]:
            for p in me.polygons:
                p.use_smooth = True
        me.update()
        down = sum(1 for p in me.polygons if p.normal.z <= 0.0)
        if down > m["down"]:
            raise SystemExit(f"[thin] {ob.name}: {down} rebuilt faces not facing up, {m['down']} before (the blend NOT saved)")
    tot0 = sum(t["vertices"][0] for t in rep["tiles"].values())
    tot1 = sum(t["vertices"][1] for t in rep["tiles"].values())
    rep["total_vertices"] = [tot0, tot1]
    rep["removed_vertex_offsets_m"] = [round(worst[0], 4), round(worst[1], 4)]
    rep["removed_lattice_vertices"] = len(removed_nodes)
    (proj / "data" / "terrain_thin.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    # where the thinning took a vertex off the lattice (a node, or a vertex on a lattice line), tools/rib_check.py still
    # reads it: a node's height off the shipped surface at that point, a line vertex as the row's own break
    (proj / "data" / NODES_FILE).write_bytes(gzip.compress(json.dumps(
        {"_doc": "tools/thin_terrain_blend.py: the plan position (local x = E, z = N) of every terrain vertex ON the "
                 "data/terrain.tiers.json.gz lattice (a node or a lattice-line vertex) the thinning removed — "
                 "tools/rib_check.py reads them as it read the vertices, the heights off the built surface",
         "frame": [x0, z0, ux, uz], "removed": removed_nodes}).encode("utf-8")))
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print(f"[thin] terrain {tot0} -> {tot1} vertices ({100.0 * (tot0 - tot1) / max(1, tot0):.1f} % fewer) over "
          f"{len(tiles)} tiles; removed vertices now {worst[0]:+.4f} .. {worst[1]:+.4f} m off the thinned surface; "
          f"saved {blend.name} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
