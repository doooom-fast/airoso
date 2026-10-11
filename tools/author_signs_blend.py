"""Stand a W1-6 Large Arrow sign AT every tight corner of loop.blend (Kevin, 2026-10-10: "arrow
signs on TIGHT corners, where they actually go ... AT the corner, just past the outside edge").

The rule lives in tools/place_signs.py (pure Python, importable here): corner detection, the
failed-to-turn ray, the sign point behind the outside curb face, the facing (-approach tangent),
the geometric outside assertion and the clearance checks. That pass works on the polyline data,
which is only the INITIAL ESTIMATE: at R < 15 m apexes the swept ribbon's built outside edge sits
inside the json half-width (medium v313 4.1 of 5.0 m, v700 4.3, MED-6 v205 2.1), so this script
re-places every post on the BUILT mesh and is authoritative for the base:

  march    the same ray against the ROAD/CURB/TERRAIN BVHs (tools/signs_mesh.py): C_mesh = where
           the top surface stops being ROAD, the walk-fraction point 0.25 m inside the back of
           the modelled walk is the first candidate, then the post keeps marching ALONG THE RAY
           (never sideways — the plate stays square to the approach) until a 5-degree polar scan
           finds >= 1.63 m (mainline) / 1.33 m (connector) of clearance to built pavement in
           every direction AND no plate vertex (base +- 0.61 m) stands inside the obstacle disc
           a gate enforces. MAINLINE posts: the disc of EVERY centreline is hard (drive_test
           sweeps the mainline; a mainline post in a side street's corridor is wrong anyway),
           capped 6 m past C_mesh -> skip with a logged reason. CONNECTOR posts: only the
           mainline's disc is hard; the own-street disc is logged (checks.gate_margin_m) and a
           negative margin is a WARN, never a march criterion (drive_test never sweeps a
           connector; fleet/REALISM.md: a real sign stands at the back of the sidewalk, never in
           the front yard behind it). The connector march is capped 1.5 m beyond the back of the
           modelled walk (CONNECTOR_BEHIND_WALK_CAP_M); at the cap a post that reaches the 1.0 m
           gate minimum but not 1.33 m is kept with a WARN, below 1.0 m it is skipped. The
           record logs checks.walk_behind_m = how far behind the walk's back edge the post stands
           (-0.25 m = the design point on the walk).
  slide    place_signs' lamp/plant slide is re-chosen HERE on the built clearance (<= 1.0 m along
           the curb direction u, smallest first; beyond that the plant is excluded from TreeFX),
           then a signs.json slide_along_curb_m is added. The record keeps slid_m (mesh), the
           un-slid mesh point (base_xz_mesh) and the polyline point (base_xz_polyline).
  pair     after the march a two-way corner whose -fwd/-rev posts stand < 2.0 m apart becomes one
           post with both plates (place_signs.merge_pairs) — DCL-2's two points met at 0.44 m.
  ground   a BVH ray-cast straight down onto CURB + SIDEWALK + TERRAIN at the final base; the
           analytic expectation is y_road(sC) + 0.24 (lift 0.10 + curb 0.14); more than 0.30 m
           apart = WARN + analytic.
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

Idempotent: existing SIGNPLATE_* / SIGNARROW_* / SIGNPOST_* meshes are deleted first. The stale
outputs (data/signs.local.json, signs_preview.svg, signs_measured.json) are unlinked at START so
a crash can never leave the previous run's record behind for the verifier. Always prints one
"[signs] ..." line (the ship pipe greps for it under set -euo pipefail).

Runs INSIDE Blender 4.2 after author_lamps_blend, before the kn5 prep:

    blender --background --python-exit-code 1 --python tools/author_signs_blend.py -- <project-dir>
            [--blend PATH] [--signs PATH] [--connectors | --no-connectors]

SIGNS_BLEND=<path> (env) or --blend points at a COPY of loop.blend for dry runs; the default is
<project>/loop.blend, which is also where the result is saved.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import bpy

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AIROSO / "tools"))
import place_signs as ps  # noqa: E402
import signs_mesh as sm  # noqa: E402

PREFIXES = ("SIGNPLATE", "SIGNARROW", "SIGNPOST")
CAP = 60000             # the prep's SPLIT_CAP; 65,535 is FATAL there
PUSH_STEP, PUSH_MAX = 0.25, 4.0
MARCH_STEP = 0.05       # along the ray, on the built mesh
CLEAR_TOL = 0.02        # polar clearance may sit this far under the target (scan quantisation)
DISC_CUSHION = 0.05     # the march wants this much margin outside the gated disc (verify asks for >= 0)
GATE_MIN = {"MAINLINE": 1.3, "CONNECTOR": 1.0}    # tools/verify_signs.py check (c) minima
CONNECTOR_BEHIND_WALK_CAP_M = 1.5   # a connector post marches at most this far behind the modelled walk
STALE_OUTPUTS = ("signs.local.json", "signs_preview.svg", "signs_measured.json")


def B(p):
    return (p[0], p[2], p[1])


def mesh_curb_crossing(road, ground, A, t, walk_w, s_hint, step=0.05, s_max=90.0):
    """the failed-to-turn ray against the BUILT mesh: C = where the top surface stops being ROAD
    (the curb face), B = where the raised walk's top starts to drop (its back edge), S_est = the
    walk fraction 1 - setback/(curb_face + walk_w) between them, i.e. 0.25 m inside the back of
    the walk — the FIRST CANDIDATE for the post (the march in main() then makes it clear the
    built pavement in every direction). None when the ray never leaves built pavement."""
    s = max(0.0, s_hint - 8.0)
    while s <= s_max and sm.on_road(road, ground, A[0] + t[0] * s, A[1] + t[1] * s):
        s += step
    if s > s_max:
        return None
    s_c = s
    out = {"s_C": round(s_c, 2), "C": (A[0] + t[0] * s_c, A[1] + t[1] * s_c)}
    # the curb top: the first sample within 0.6 m of the road edge at the walk height (the sample
    # right at the edge can land in the gutter at terrain height, under the curb face)
    tops = [(s_c + k * step, sm.top_hit(ground, A[0] + t[0] * (s_c + k * step), A[1] + t[1] * (s_c + k * step))) for k in range(0, 13)]
    vals = [v for _, v in tops if v is not None]
    if not vals:
        return out
    h_walk = max(vals)
    s_top = next(sv for sv, v in tops if v is not None and v >= h_walk - 0.04)
    run_max = (ps.CURB_FACE_W + walk_w) * 4.0          # a ray nearly parallel to the curb is not a crossing
    s_b = s_top
    while s_b - s_c <= run_max:
        g = sm.top_hit(ground, A[0] + t[0] * s_b, A[1] + t[1] * s_b)
        if g is None or g < h_walk - 0.04:
            break
        s_b += step
    run = s_b - s_c
    if run < 0.3 or run > run_max:
        out["walk_run_m"] = round(run, 2)
        return out
    frac = 1.0 - ps.BACK_OF_WALK_SETBACK / (ps.CURB_FACE_W + walk_w)
    out.update(s_B=round(s_b, 2), walk_run_m=round(run, 2), h_walk=round(h_walk, 3), s_S=round(s_c + run * frac, 2))
    return out


def built_edges(road, ground, rb, st0, side, half=30, step=2, reach=22.0, d_step=0.1):
    """the BUILT outside pavement edge and back-of-walk around a station, for the picture and for
    tools/verify_signs.py check (c): per station a perpendicular probe outward (side = +1 left of
    forward travel, -1 right) — the last ROAD-top sample is the curb face, the last sample at the
    walk's height is its back edge"""
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
            if sm.on_road(road, ground, p[0] + nx * d, p[1] + nz * d):
                last_road = d
            elif last_road is not None and d - last_road > 1.0:
                break
            d += d_step
        if last_road is None:
            continue
        edge.append([round(p[0] + nx * last_road, 2), round(p[1] + nz * last_road, 2)])
        tops = [sm.top_hit(ground, p[0] + nx * (last_road + j * d_step), p[1] + nz * (last_road + j * d_step)) for j in range(1, 8)]
        tops = [v for v in tops if v is not None]
        if not tops:
            continue
        h_walk, db = max(tops), last_road + d_step
        while db - last_road <= 4.0:
            g = sm.top_hit(ground, p[0] + nx * db, p[1] + nz * db)
            if g is None or g < h_walk - 0.04:
                break
            db += d_step
        back.append([round(p[0] + nx * (db - d_step), 2), round(p[1] + nz * (db - d_step), 2)])
    return edge, back


def mesh_place(s, ctx, cfg, road, ground):
    """re-place one plate's post on the built mesh (see module doc); mutates the record and
    returns the fatal reasons (empty = placed)"""
    x0, z0 = s["base_xz"]
    s["base_xz_polyline"] = [x0, z0]
    t = (-s["face_dir_xz"][0], -s["face_dir_xz"][1])
    A = s["ray"]["A_xz"]
    u = s["curb_dir_xz"]
    rights = (s["right_xz"],)
    is_main = s["ribbon"] == "MAINLINE"
    walk_w = ps.SIDEWALK_W["MAINLINE" if is_main else "CONNECTOR"]
    d_clear = s["lateral_offset_m"]
    gate_min = GATE_MIN["MAINLINE" if is_main else "CONNECTOR"]
    disc_names = ps.disc_names_for(s["ribbon"])     # None = every ribbon's disc is hard (mainline post)
    applied = s.get("overrides_applied", [])
    forced = "force" in applied
    reasons, warns = [], []
    chk = s["checks"]
    chk["slid_polyline_m"] = chk.get("slid_m", 0.0)
    walk_behind = None

    def polar(x, z, reach=sm.POLAR_REACH):
        return sm.polar_clearance(road, ground, x, z, reach=reach)

    if "base_xz" in applied:
        x, z = x0, z0
        s["base_source"] = "signs.json base_xz (pinned; measured, not marched)"
        slid = chk["slid_polyline_m"]
    else:
        m = mesh_curb_crossing(road, ground, A, t, walk_w, s["ray"]["len_m"])
        if m is None:
            s["base_source"] = "polyline (ray never leaves BUILT pavement within 90 m)"
            return ["ray never leaves the built pavement within 90 m (through leg / junction on the mesh)"]
        s_C = m["s_C"]
        s["ray"].update(C_mesh_xz=[round(m["C"][0], 2), round(m["C"][1], 2)], len_mesh_m=m["s_C"])
        if m.get("s_S") is not None:
            s_est, src = m["s_S"], "walk fraction"
            s_B = m["s_B"]
            s["ray"].update(back_of_walk_m=m["s_B"], walk_run_m=m["walk_run_m"], s_S_walk_m=m["s_S"])
        else:
            s_est, src = s_C + d_clear, "no modelled walk (run %s)" % m.get("walk_run_m")
            s_B = s_C + ps.CURB_FACE_W + walk_w      # where the walk's back edge would be
            warns.append("no modelled curb+walk found along the ray; marched from the built curb face")
        # the authoritative march: along the ray only, until the built clearance AND the GATED
        # disc hold. Cap: mainline +6 m past the built curb; connector 1.5 m behind the walk.
        s_cap = s_C + ps.RAY_EXTRA_CAP_M if is_main else s_B + CONNECTOR_BEHIND_WALK_CAP_M
        cap_txt = "+%.0f m past the built curb" % ps.RAY_EXTRA_CAP_M if is_main else "%.1f m behind the modelled walk" % CONNECTOR_BEHIND_WALK_CAP_M
        s_m, capped = s_est, False
        while True:
            qx, qz = A[0] + t[0] * s_m, A[1] + t[1] * s_m
            pc = polar(qx, qz, reach=d_clear + 0.05)[0]
            fm = ctx.field.footprint_margin((qx, qz), rights, disc_names)
            if pc >= d_clear - CLEAR_TOL and fm >= DISC_CUSHION:
                break
            if s_m >= s_cap:
                capped = True
                break
            s_m = min(s_m + MARCH_STEP, s_cap)
        xm, zm = A[0] + t[0] * s_m, A[1] + t[1] * s_m
        s["base_xz_mesh"] = [round(xm, 3), round(zm, 3)]
        beyond_walk = m.get("s_B") is not None and s_m > m["s_B"]
        walk_behind = round(s_m - s_B, 2)
        s["ray"].update(s_S_mesh_m=round(s_m, 2), marched_m=round(s_m - s_est, 2), beyond_walk=beyond_walk)
        if beyond_walk:
            warns.append("post stands %.2f m behind the back of the modelled walk (marched for the built clearance%s); ground = terrain ray-cast"
                         % (s_m - m["s_B"], "/disc" if is_main else ""))
        pc_m, fm_m = polar(xm, zm)[0], ctx.field.footprint_margin((xm, zm), rights, disc_names)
        if capped:
            if fm_m < 0:
                reasons.append("plate footprint inside drive_test's obstacle disc (%s) by %.2f m at the %s cap"
                               % ("every ribbon" if disc_names is None else "+".join(disc_names), -fm_m, cap_txt))
            if pc_m < gate_min - CLEAR_TOL:
                reasons.append("built-edge clearance %.2f m < %.1f m gate minimum at the %s cap" % (pc_m, gate_min, cap_txt))
            elif pc_m < d_clear - CLEAR_TOL:
                warns.append("built-edge clearance %.2f m (target %.2f) at the %s cap; passes the %.1f m gate minimum"
                             % (pc_m, d_clear, cap_txt, gate_min))
        if reasons and not forced:
            s["base_xz"] = [round(xm, 3), round(zm, 3)]
            s["base_source"] = "mesh march capped (%s start)" % src
            chk.update(walk_behind_m=walk_behind, gate_ribbons="all" if disc_names is None else "+".join(disc_names))
            return reasons
        # the slide, re-chosen on the built clearance (lamps >= 3 m, plants >= 2.5 m, <= 1.0 m)
        slid, S, lamp, plant, excl, slide_reasons = ps.choose_slide(
            ctx, cfg, (xm, zm), u, min(d_clear, pc_m), lambda x, z: polar(x, z, reach=d_clear + 0.05)[0], rights, disc_names)
        reasons += slide_reasons
        s["exclude_plant"] = excl
        x, z = S
        for a in applied:
            if a.startswith("slide_along_curb_m="):
                sl = float(a.split("=", 1)[1])
                x, z = x + u[0] * sl, z + u[1] * sl
                slid += sl
        s["base_source"] = "mesh (%s start, marched %.2f m along the ray, slid %.2f m along the curb)" % (src, s_m - s_est, slid)
    # measure the final post
    pc_f, pc_bearing = polar(x, z)
    fm_f = ctx.field.footprint_margin((x, z), rights)                  # every centreline: logged
    fm_gated = ctx.field.footprint_margin((x, z), rights, disc_names)  # the discs a gate enforces
    lamp, plant = ctx.nearest_lamp((x, z)), ctx.nearest_plant((x, z))
    shift = math.hypot(x - x0, z - z0)
    chk.update(mesh_clear_m=round(pc_f, 2), mesh_clear_bearing_deg=pc_bearing, mesh_shift_m=round(shift, 2),
               edge_clear_m=round(ctx.field.query(x, z)[0], 2), gate_margin_m=round(fm_f, 2),
               gate_margin_gated_m=round(fm_gated, 2), gate_ribbons="all" if disc_names is None else "+".join(disc_names),
               walk_behind_m=walk_behind,
               lamp_m=round(lamp, 2), plant_m=round(plant[0], 2), plant_zone=plant[1], slid_m=round(slid, 2))
    if fm_gated < 0:
        reasons.append("plate footprint inside drive_test's obstacle disc by %.2f m (%s)" % (-fm_gated, "every ribbon" if disc_names is None else "+".join(disc_names)))
    elif fm_f < 0:
        warns.append("plate footprint %.2f m inside the obstacle disc of a connector centreline (%s): not gated, drive_test sweeps the mainline only; the post stays at the back of the walk (REALISM)"
                     % (-fm_f, s["ribbon"]))
    if pc_f < gate_min - CLEAR_TOL:
        reasons.append("built-edge clearance %.2f m < %.1f m" % (pc_f, gate_min))
    if is_main and pc_f > 3.0:
        reasons.append("built-edge clearance %.2f m > 3.0 m (too far from the curb)" % pc_f)
    if "base_xz" in applied and lamp < cfg["lamp_clear_m"]:
        reasons.append("pinned base %.1f m from a lamp post (< %.1f)" % (lamp, cfg["lamp_clear_m"]))
    s["base_xz"] = [round(x, 3), round(z, 3)]
    chk["warnings"] = chk.get("warnings", []) + warns
    if reasons and forced:
        chk["warnings"] += ["FORCED past: " + r for r in reasons]
        reasons = []
    return reasons


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
    data = proj / "data"
    for f in STALE_OUTPUTS:                     # a crash below must not leave the previous record
        (data / f).unlink(missing_ok=True)
    cfg, corners_cfg, ov_path = ps.load_overrides(proj, signs_path)
    if "--connectors" in argv:
        cfg["include_connectors"] = True
    if "--no-connectors" in argv:
        cfg["include_connectors"] = False

    out, ctx = ps.place_all(proj, cfg, corners_cfg, log=print, merge=False)

    bpy.ops.wm.open_mainfile(filepath=str(blend))
    removed = 0
    for ob in list(bpy.data.objects):
        if ob.type == "MESH" and ob.name.upper().startswith(PREFIXES):
            bpy.data.objects.remove(ob, do_unlink=True)
            removed += 1
    road, ground, road_names, ground_names = sm.load_bvhs()

    # 1) every plate on the built mesh; a plate that cannot be placed cleanly is skipped, loudly
    kept = []
    for s in out["signs"]:
        reasons = mesh_place(s, ctx, cfg, road, ground)
        if reasons:
            out["skipped"].append({"id": s["id"], "ribbon": s["ribbon"] + ("(rev)" if s["direction"] == "rev" else ""),
                                   "apex_vertex": s["corner"]["apex_vertex"], "apex_station_m": s["corner"]["apex_station_m"],
                                   "R_apex_m": s["corner"]["R_apex_m"], "D_deg": s["corner"]["D_deg"], "arc_m": s["corner"]["arc_m"],
                                   "apex_xz": s["corner"]["apex_xz"], "reasons": ["mesh stage: " + r for r in reasons],
                                   "would_be": s["base_xz"], "stage": "mesh"})
            print("[signs] mesh-skip %-11s %s" % (s["id"], "; ".join(reasons)))
            continue
        kept.append(s)
    # 2) pairs meet on the mesh, not on the polyline (DCL-2: 2.6 m apart there, 0.44 m here);
    #    the shared post stands at the mean base, so its clearances are measured again there
    signs = ps.merge_pairs(kept, log=print)
    for s in signs:
        if not s.get("pair"):
            continue
        x, z = s["base_xz"]
        rights = [p["right_xz"] for p in s["plates"]]
        pc, pb = sm.polar_clearance(road, ground, x, z)
        s["checks"].update(mesh_clear_m=round(pc, 2), mesh_clear_bearing_deg=pb,
                           gate_margin_m=round(ctx.field.footprint_margin((x, z), rights), 2),
                           gate_margin_gated_m=round(ctx.field.footprint_margin((x, z), rights, ps.disc_names_for(s["ribbon"])), 2),
                           edge_clear_m=round(ctx.field.query(x, z)[0], 2),
                           lamp_m=round(ctx.nearest_lamp((x, z)), 2), plant_m=round(ctx.nearest_plant((x, z))[0], 2))
    out["signs"] = signs
    out["exclude_plants"] = [dict(s["exclude_plant"], sign=s["id"]) for s in signs if s.get("exclude_plant")]
    out["pairs"] = [s["id"] for s in signs if s.get("pair")]
    out["counts"] = {"placed": len(signs), "plates": sum(len(ps.plates_of(s)) for s in signs), "skipped": len(out["skipped"])}

    # 3) ground + meshes
    batches = {k: [] for k in PREFIXES}
    cur = {k: ([], [], []) for k in PREFIXES}       # verts, faces, intended normals

    def flush(kind):
        V, F, N = cur[kind]
        if V:
            batches[kind].append((list(V), list(F), list(N)))
            V.clear(); F.clear(); N.clear()

    n_warn = 0
    for s in signs:
        x, z = s["base_xz"]
        pushed = 0.0
        g = sm.top_hit(ground, x, z)
        r = sm.top_hit(road, x, z)
        t = (-s["face_dir_xz"][0], -s["face_dir_xz"][1])
        while r is not None and (g is None or r >= g - 0.02) and pushed < PUSH_MAX:   # never on ROAD
            x += t[0] * PUSH_STEP
            z += t[1] * PUSH_STEP
            pushed += PUSH_STEP
            g, r = sm.top_hit(ground, x, z), sm.top_hit(road, x, z)
        analytic = s["y_base"]["analytic"]
        beyond = any(p["ray"].get("beyond_walk") for p in ps.plates_of(s))
        if g is None:
            y_base, src = analytic, "analytic (no ground hit)"
        elif beyond:        # off the back of the walk: the terrain under the post IS the ground
            y_base, src = g, "raycast (terrain behind the walk, %+.2f m vs the walk's analytic height)" % (g - analytic)
        elif abs(g - analytic) > ps.GROUND_WARN_M:
            y_base, src = analytic, "analytic (ray-cast %.2f is %.2f m off, gapped walk?)" % (g, g - analytic)
            n_warn += 1
            s["checks"]["warnings"].append("ground ray-cast %.2f vs analytic %.2f" % (g, analytic))
        else:
            y_base, src = g, "raycast"
        if pushed:
            s["checks"]["warnings"].append("base was on ROAD; pushed %.2f m along the approach" % pushed)
            s["base_xz"] = [round(x, 3), round(z, 3)]
        # the built edge around the sign (tools/plot_signs.py draws it; tools/verify_signs.py
        # measures check (c) against it)
        fwd = next(rb for rb in ctx.ribbons if rb.name == s["ribbon"])
        p0 = ps.plates_of(s)[0]
        sc = p0["ray"]["sC_station"]
        st_fwd = sc if p0["direction"] == "fwd" else ((-sc) % fwd.n if fwd.closed else fwd.n - 1 - sc)
        side = (1 if p0["corner"]["D_deg"] < 0 else -1) * (1 if p0["direction"] == "fwd" else -1)
        edge, back = built_edges(road, ground, fwd, st_fwd, side)
        s["built"] = {"outside_edge_xz": edge, "back_of_walk_xz": back}
        s["y_base"].update(raycast=None if g is None else round(g, 3), source=src, value=round(y_base, 3),
                           road_hit=None if r is None else round(r, 3), pushed_on_road_m=pushed)
        info = []
        polys = ps.sign_polygons(s, y_base, info)
        top = max(v[1] for lst in polys.values() for verts, _ in lst for v in verts)
        # the vertices the verifier measures (facing, height, arrow) — geometry, not this pass's
        # own numbers about itself: plates[k] = front/back faces + arrow glyph, post = base corners
        s["blender"] = {"base_xyz_engine": [round(x, 3), round(y_base, 3), round(z, 3)],
                        "base_xyz_blender": [round(x, 3), round(z, 3), round(y_base, 3)],
                        "plate_bottom_y": round(y_base + s["height_m"], 3),
                        "plate_top_y": round(y_base + s["height_m"] + ps.PLATE_H, 3),
                        "post_base_y": round(y_base - ps.POST_SINK, 3),
                        "post_top_y": round(top, 3),
                        "plates": [e for e in info if "front_xyz" in e],
                        "post": next((e for e in info if "post_base_xyz" in e), None)}
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
                      "vertices": nverts, "faces": nfaces, "normal_mismatches": bad, "ground_warnings": n_warn,
                      "base_rule": "built mesh authoritative: walk-fraction start, marched along the ray to polar clearance >= lateral_offset and disc footprint >= 0"}
    ps.write_outputs(proj, out, ctx)
    for s in signs:
        c = s["checks"]
        print("[signs] %-11s %-12s %-20s base (%8.1f, %6.2f, %8.1f) faces %s deg  built clear %.2f m (shift %.2f, slid %+.2f)  walk-behind %s  disc %+.2f (gated %s %+.2f)  y_base %s%s"
              % (s["id"], s["kind"], s["ribbon"] + "/" + s["direction"], s["base_xz"][0], s["y_base"]["value"], s["base_xz"][1],
                 "/".join("%.1f" % p["face_bearing_deg"] for p in ps.plates_of(s)), c["mesh_clear_m"], c["mesh_shift_m"],
                 c["slid_m"], "%+.2f" % c["walk_behind_m"] if c.get("walk_behind_m") is not None else "-",
                 c["gate_margin_m"], c.get("gate_ribbons", "all"), c.get("gate_margin_gated_m", c["gate_margin_m"]), s["y_base"]["source"],
                 ("  WARN " + "; ".join(c["warnings"])) if c["warnings"] else ""))
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
