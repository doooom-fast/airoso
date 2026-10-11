"""Stand a W1-6 Large Arrow sign AT every tight corner of loop.blend (Kevin, 2026-10-10: "arrow
signs on TIGHT corners, where they actually go ... AT the corner, just past the outside edge").

The rule lives in tools/place_signs.py (pure Python, importable here): corner detection, the
failed-to-turn ray, the sign point 1.63 m behind the outside curb face, the facing (-approach
tangent), the geometric outside assertion and the clearance checks. This script adds the two
things only Blender knows and emits the meshes:

  ground   a BVH ray-cast straight down onto CURB + SIDEWALK + TERRAIN (ROAD separately: a hit on
           pavement pushes the base 0.25 m further along the ray, <= 4 m — authoritative at the lap
           seam, where the ribbon width steps 27.5 -> 17 m). The analytic expectation is
           y_road(sC) + 0.24 (lift 0.10 + curb 0.14); more than 0.30 m apart = WARN + analytic.
  meshes   SIGNPLATE_k (yellow: plate + OM1-3 diamond), SIGNARROW_k (black: arrow + border),
           SIGNPOST_k (grey: 2 in post, sunk 0.30 m, + the plates' back faces on their own verts
           3 mm behind — Mesh.validate() deletes a reversed duplicate on shared verts). No
           materials, no UVs: the prep (engine-july build_kn5_loop) binds by name prefix via
           pbr.TEXTURES (SIGNPLATE / SIGNARROW / SIGNPOST -> 64x64 solid PNGs, immune to its
           planar-UV overwrite) and names the material <obj>_mat — a pre-existing one would give
           <obj>_mat.001 and ext_config references would miss.
  frames   place_signs works in the engine frame (x = E, y = up, z = N); B(p) = (x, z, y) maps to
           Blender. That swap is a reflection (LAWS L6), so every polygon is wound HERE to its
           intended normal in Blender space (cross(v1-v0, v2-v0) . B(normal) > 0) and the result
           is checked against Mesh.polygons[].normal — the prep's face-up flip never touches a
           non-drivable mesh, so nothing downstream corrects a wrong winding.

Idempotent: existing SIGNPLATE_* / SIGNARROW_* / SIGNPOST_* meshes are deleted first. Always
prints one "[signs] ..." line (the ship pipe greps for it under set -euo pipefail).

Runs INSIDE Blender 4.2 after author_lamps_blend, before the kn5 prep:

    blender --background --python tools/author_signs_blend.py -- <project-dir> [--blend PATH]
            [--signs PATH] [--connectors | --no-connectors]

SIGNS_BLEND=<path> (env) or --blend points at a COPY of loop.blend for dry runs; the default is
<project>/loop.blend, which is also where the result is saved.

Rebuild timing: this pass is config + loop.blend only; run the ship (tools/ship_sd.sh) after the
concurrent lights + GrassFX work (track.config.json lighting block, ext_config.py) has landed, so
one build carries both.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AIROSO / "tools"))
import place_signs as ps  # noqa: E402

PREFIXES = ("SIGNPLATE", "SIGNARROW", "SIGNPOST")
GROUND = ("CURB", "SIDEWALK", "TERRAIN", "1KERB", "1GRASS")
ROAD = ("ROAD", "1ROAD")
CAP = 60000             # the prep's SPLIT_CAP; 65,535 is FATAL there
PUSH_STEP, PUSH_MAX = 0.25, 4.0
RAY_TOP = 4000.0


def B(p):
    return (p[0], p[2], p[1])


def world_tris(ob):
    mw = ob.matrix_world
    vs = [tuple(mw @ v.co) for v in ob.data.vertices]
    tris = []
    for poly in ob.data.polygons:
        idx = poly.vertices
        for k in range(1, len(idx) - 1):
            tris.append((vs[idx[0]], vs[idx[k]], vs[idx[k + 1]]))
    return tris


def bvh_of(tris):
    if not tris:
        return None
    return BVHTree.FromPolygons([v for t in tris for v in t], [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tris))])


def top_hit(bvh, x, z):
    """highest surface height (engine y) under the engine-frame point (x, z); None if nothing"""
    if bvh is None:
        return None
    hit = bvh.ray_cast(Vector((x, z, RAY_TOP)), Vector((0.0, 0.0, -1.0)))
    return None if hit[0] is None else hit[0].z


def on_road(road, ground, x, z):
    """the top surface under (x, z) is pavement (a curb/walk hit above the road wins)"""
    r = top_hit(road, x, z)
    if r is None:
        return False
    g = top_hit(ground, x, z)
    return g is None or r >= g - 0.02


def mesh_sign_point(road, ground, A, t, walk_w, s_hint, step=0.05, s_max=90.0):
    """the failed-to-turn ray against the BUILT mesh: C = where the top surface stops being ROAD
    (the curb face), B = where the raised walk's top starts to drop (its back edge), and the post
    stands at the walk fraction 1 - setback/(curb_face + walk_w) between them, i.e. 0.25 m inside
    the back of the walk measured perpendicular — the same rule place_signs applies to the
    polyline, now on the geometry Kevin sees (at tight corners the swept ribbon's outside edge
    sits up to ~3 m inside the polyline half-width)"""
    s = max(0.0, s_hint - 8.0)
    while s <= s_max and on_road(road, ground, A[0] + t[0] * s, A[1] + t[1] * s):
        s += step
    if s > s_max:
        return None
    s_c = s
    out = {"s_C": round(s_c, 2), "C": (A[0] + t[0] * s_c, A[1] + t[1] * s_c)}
    # the curb top: the first sample within 0.6 m of the road edge at the walk height (the sample
    # right at the edge can land in the gutter at terrain height, under the curb face)
    tops = [(s_c + k * step, top_hit(ground, A[0] + t[0] * (s_c + k * step), A[1] + t[1] * (s_c + k * step))) for k in range(0, 13)]
    vals = [v for _, v in tops if v is not None]
    if not vals:
        return out
    h_walk = max(vals)
    s_top = next(sv for sv, v in tops if v is not None and v >= h_walk - 0.04)
    run_max = (ps.CURB_FACE_W + walk_w) * 4.0          # a ray nearly parallel to the curb is not a crossing
    s_b = s_top
    while s_b - s_c <= run_max:
        g = top_hit(ground, A[0] + t[0] * s_b, A[1] + t[1] * s_b)
        if g is None or g < h_walk - 0.04:
            break
        s_b += step
    run = s_b - s_c
    if run < 0.3 or run > run_max:
        out["walk_run_m"] = round(run, 2)
        return out
    frac = 1.0 - ps.BACK_OF_WALK_SETBACK / (ps.CURB_FACE_W + walk_w)
    s_S = s_c + run * frac
    out.update(s_B=round(s_b, 2), walk_run_m=round(run, 2), h_walk=round(h_walk, 3), s_S=round(s_S, 2),
               S=(A[0] + t[0] * s_S, A[1] + t[1] * s_S),
               mesh_clear_m=round((ps.CURB_FACE_W + walk_w) * frac, 2))
    return out


def built_edges(road, ground, rb, st0, side, half=30, step=2, reach=22.0, d_step=0.1):
    """the BUILT outside pavement edge and back-of-walk around a station, for the picture: per
    station a perpendicular probe outward (side = +1 left of forward travel, -1 right) — the last
    ROAD-top sample is the curb face, the last sample at the walk's height is its back edge"""
    edge, back = [], []
    for k in range(-half, half + 1, step):
        i = st0 + k
        if not rb.closed and (i < 0 or i >= rb.n):
            continue
        p = rb.xz(i)
        tx, tz = rb.tangent(i)
        nx, nz = -tz * side, tx * side
        d, last_road = 0.0, None
        while d <= reach:
            if on_road(road, ground, p[0] + nx * d, p[1] + nz * d):
                last_road = d
            elif last_road is not None and d - last_road > 1.0:
                break
            d += d_step
        if last_road is None:
            continue
        edge.append([round(p[0] + nx * last_road, 2), round(p[1] + nz * last_road, 2)])
        tops = [top_hit(ground, p[0] + nx * (last_road + j * d_step), p[1] + nz * (last_road + j * d_step)) for j in range(1, 8)]
        tops = [v for v in tops if v is not None]
        if not tops:
            continue
        h_walk, db = max(tops), last_road + d_step
        while db - last_road <= 4.0:
            g = top_hit(ground, p[0] + nx * db, p[1] + nz * db)
            if g is None or g < h_walk - 0.04:
                break
            db += d_step
        back.append([round(p[0] + nx * (db - d_step), 2), round(p[1] + nz * (db - d_step), 2)])
    return edge, back


def oriented(poly_b, normal_b):
    """vertex order whose Blender face normal (right-hand rule) points along normal_b"""
    v0, v1, v2 = poly_b[0], poly_b[1], poly_b[2]
    ax, ay, az = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
    bx, by, bz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
    cx, cy, cz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
    if cx * normal_b[0] + cy * normal_b[1] + cz * normal_b[2] < 0:
        return [poly_b[0]] + poly_b[1:][::-1]      # keep vertex 0 (the arrow tip) as the fan hub
    return poly_b


def _mk(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    blend = Path(os.environ.get("SIGNS_BLEND") or (argv[argv.index("--blend") + 1] if "--blend" in argv else proj / "loop.blend"))
    signs_path = argv[argv.index("--signs") + 1] if "--signs" in argv else None
    cfg, corners_cfg, ov_path = ps.load_overrides(proj, signs_path)
    if "--connectors" in argv:
        cfg["include_connectors"] = True
    if "--no-connectors" in argv:
        cfg["include_connectors"] = False

    out, ctx = ps.place_all(proj, cfg, corners_cfg, log=print)
    signs = out["signs"]

    bpy.ops.wm.open_mainfile(filepath=str(blend))
    removed = 0
    for ob in list(bpy.data.objects):
        if ob.type == "MESH" and ob.name.upper().startswith(PREFIXES):
            bpy.data.objects.remove(ob, do_unlink=True)
            removed += 1
    ground_tris, road_tris, ground_names, road_names = [], [], [], []
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        up = ob.name.upper()
        if up.startswith(ROAD):
            road_tris += world_tris(ob)
            road_names.append(ob.name)
        elif up.startswith(GROUND):
            ground_tris += world_tris(ob)
            ground_names.append(ob.name)
    ground, road = bvh_of(ground_tris), bvh_of(road_tris)

    batches = {k: [] for k in PREFIXES}
    cur = {k: ([], [], []) for k in PREFIXES}       # verts, faces, intended normals

    def flush(kind):
        V, F, N = cur[kind]
        if V:
            batches[kind].append((list(V), list(F), list(N)))
            V.clear(); F.clear(); N.clear()

    n_warn = 0
    cfg_lamp, cfg_plant = cfg["lamp_clear_m"], cfg["plant_clear_m"]
    for s in signs:
        x, z = s["base_xz"]
        s["base_xz_polyline"] = [x, z]
        t = (-s["face_dir_xz"][0], -s["face_dir_xz"][1])
        A = s["ray"]["A_xz"]
        walk_w = ps.SIDEWALK_W["MAINLINE" if s["ribbon"] == "MAINLINE" else "CONNECTOR"]
        pushed = 0.0
        m = mesh_sign_point(road, ground, A, t, walk_w, s["ray"]["len_m"])
        if m and m.get("S"):
            x, z = m["S"]
            shift = ((x - s["base_xz"][0]) ** 2 + (z - s["base_xz"][1]) ** 2) ** 0.5
            lamp = ctx.nearest_lamp((x, z))
            plant = ctx.nearest_plant((x, z))
            s["ray"].update(C_mesh_xz=[round(m["C"][0], 2), round(m["C"][1], 2)], len_mesh_m=m["s_C"],
                            back_of_walk_m=m["s_B"], walk_run_m=m["walk_run_m"], s_S_mesh_m=m["s_S"])
            s["checks"].update(mesh_clear_m=m["mesh_clear_m"], mesh_shift_m=round(shift, 2),
                               edge_clear_m=round(ctx.field.query(x, z)[0], 2),
                               gate_margin_m=round(ctx.field.gate_margin(x, z), 2),
                               lamp_m=round(lamp, 2), plant_m=round(plant[0], 2), plant_zone=plant[1])
            s["base_source"] = "mesh (curb face + back of walk ray-cast on ROAD/CURB)"
            if lamp < cfg_lamp:
                s["checks"]["warnings"].append("mesh-placed post %.1f m from a lamp post (< %.1f)" % (lamp, cfg_lamp))
            if plant[0] < cfg_plant and not any(e["sign"] == s["id"] for e in out["exclude_plants"]):
                out["exclude_plants"].append({"zone": plant[1], "index": plant[2], "dist_m": round(plant[0], 2), "sign": s["id"]})
            if s["checks"]["gate_margin_m"] < 0 and s["ribbon"] == "MAINLINE":
                s["checks"]["warnings"].append("mesh-placed post inside drive_test's obstacle disc by %.2f m" % -s["checks"]["gate_margin_m"])
        else:
            s["base_source"] = "polyline (no modelled walk under the ray%s)" % (": " + json.dumps(m) if m else "")
            s["checks"]["warnings"].append("no modelled curb+walk found along the ray; polyline placement kept")
            g = top_hit(ground, x, z)
            r = top_hit(road, x, z)
            while r is not None and (g is None or r >= g - 0.02) and pushed < PUSH_MAX:
                x += t[0] * PUSH_STEP
                z += t[1] * PUSH_STEP
                pushed += PUSH_STEP
                g, r = top_hit(ground, x, z), top_hit(road, x, z)
        g = top_hit(ground, x, z)
        r = top_hit(road, x, z)
        analytic = s["y_base"]["analytic"]
        if g is None:
            y_base, src = analytic, "analytic (no ground hit)"
        elif abs(g - analytic) > ps.GROUND_WARN_M:
            y_base, src = analytic, "analytic (ray-cast %.2f is %.2f m off, gapped walk?)" % (g, g - analytic)
            n_warn += 1
            s["checks"]["warnings"].append("ground ray-cast %.2f vs analytic %.2f" % (g, analytic))
        else:
            y_base, src = g, "raycast"
        if pushed:
            s["checks"]["warnings"].append("base was on ROAD; pushed %.2f m along the approach" % pushed)
        s["base_xz"] = [round(x, 3), round(z, 3)]
        # the built edge around the sign, for tools/plot_signs.py (the polyline ribbon it draws is
        # wider than the swept mesh at tight apexes)
        fwd = next(r for r in ctx.ribbons if r.name == s["ribbon"])
        sc = s["ray"]["sC_station"]
        st_fwd = sc if s["direction"] == "fwd" else ((-sc) % fwd.n if fwd.closed else fwd.n - 1 - sc)
        side = (1 if s["corner"]["D_deg"] < 0 else -1) * (1 if s["direction"] == "fwd" else -1)
        edge, back = built_edges(road, ground, fwd, st_fwd, side)
        s["built"] = {"outside_edge_xz": edge, "back_of_walk_xz": back}
        s["y_base"].update(raycast=None if g is None else round(g, 3), source=src, value=round(y_base, 3),
                           road_hit=None if r is None else round(r, 3), pushed_on_road_m=pushed)
        s["blender"] = {"base_xyz_engine": [round(x, 3), round(y_base, 3), round(z, 3)],
                        "base_xyz_blender": [round(x, 3), round(z, 3), round(y_base, 3)],
                        "plate_bottom_y": round(y_base + s["height_m"], 3),
                        "plate_top_y": round(y_base + s["height_m"] + ps.PLATE_H, 3),
                        "post_base_y": round(y_base - ps.POST_SINK, 3),
                        "post_top_y": round(y_base + s["height_m"] + ps.PLATE_H + ps.POST_OVER_TOP, 3)}
        polys = ps.sign_polygons(s, y_base)
        for kind, lst in polys.items():
            nv = sum(len(p[0]) for p in lst)
            V, F, N = cur[kind]
            if len(V) + nv > CAP:
                flush(kind)
                V, F, N = cur[kind]
            for verts, normal in lst:
                vb = oriented([B(v) for v in verts], B(normal))
                off = len(V)
                V.extend(vb)
                for k in range(1, len(vb) - 1):
                    F.append((off, off + k, off + k + 1))
                    N.append(B(normal))
        s["blender"]["meshes"] = {k: "%s_%d" % (k, len(batches[k])) for k in PREFIXES}
    for kind in PREFIXES:
        flush(kind)

    nverts = {k: 0 for k in PREFIXES}
    nfaces = {k: 0 for k in PREFIXES}
    bad = 0
    for kind, lst in batches.items():
        for k, (V, F, N) in enumerate(lst):
            ob = _mk("%s_%d" % (kind, k), V, F)
            nverts[kind] += len(ob.data.vertices)
            nfaces[kind] += len(ob.data.polygons)
            for poly, want in zip(ob.data.polygons, N):
                if poly.normal.x * want[0] + poly.normal.y * want[1] + poly.normal.z * want[2] < 0:
                    bad += 1
    bpy.ops.wm.save_mainfile(filepath=str(blend))

    out["blender"] = {"blend": str(blend), "ground_objects": ground_names, "road_objects": road_names,
                      "removed_existing": removed, "meshes": {k: ["%s_%d" % (k, i) for i in range(len(batches[k]))] for k in PREFIXES},
                      "vertices": nverts, "faces": nfaces, "normal_mismatches": bad, "ground_warnings": n_warn}
    ps.write_outputs(proj, out, ctx)
    for s in signs:
        print("[signs] %-11s %s %-20s base (%8.1f, %6.2f, %8.1f) faces %5.1f deg  curb %.2f m (mesh shift %.2f)  y_base %s%s"
              % (s["id"], s["kind"], s["ribbon"] + "/" + s["direction"], s["base_xz"][0], s["y_base"]["value"], s["base_xz"][1],
                 s["face_bearing_deg"], s["checks"].get("mesh_clear_m", s["checks"]["edge_clear_m"]), s["checks"].get("mesh_shift_m", 0.0),
                 s["y_base"]["source"], ("  WARN " + "; ".join(s["checks"]["warnings"])) if s["checks"]["warnings"] else ""))
    for s in out["skipped"]:
        print("[signs] skip %-11s %-20s v%-5d %s" % (s["id"], s["ribbon"], s["apex_vertex"], "; ".join(s["reasons"])))
    print("[signs] %s -> %s; %d verts, %d faces; normals %s; ground from %s (ROAD rejects %s); removed %d old; overrides %s; saved %s"
          % (ps.summary_line(out),
             " + ".join("%d %s" % (len(batches[k]), k) for k in PREFIXES),
             sum(nverts.values()), sum(nfaces.values()),
             "OK" if bad == 0 else "%d MISMATCHED" % bad,
             "+".join(ground_names) or "nothing", "+".join(road_names) or "nothing",
             removed, ov_path if ov_path.exists() else "(none)", blend))


main()
