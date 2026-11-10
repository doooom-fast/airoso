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
           apart = WARN + analytic. Race furniture (1KERB_RACE / 1WALL_RACE, the RACE / RACE_CLOSE_*
           collections) is neither ground nor road for any of this (tools/signs_mesh.py, ledger
           0051): the signs ship in the road kn5 the street layout loads, the race kerbs do not.
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

  walls    (ledger 0054 P4) every post stands >= WALL_CLEAR_M (0.5 m, the lamp rule's number) from every
           1WALL* face (tools/signs_mesh.load_wall_bvhs "all"): the march along the ray goes on until it does
           (a north post behind a pad stub's K-rail, a mainline post beside a guard rail), capped as above.
  north    a post on the stitched "north" ribbon (place_signs module doc) is a CONNECTOR post for the walk
           (1.5 m), the gate minimum (1.0 m) and the cap; its ray crosses the junction pad's built deck
           (1ROAD_pad_*) and leaves it at the pad's curb return or down a stub arm.
  layout   a LAYOUT PLATE (place_signs: a per_layout MAINLINE corner's plate for ONE race layout, id
           <corner>-<dir>@<layout>) is placed against the WALLS that layout loads (load_wall_bvhs[token]: the
           common curb strips + its closure): along the same ray, the post stands lateral_offset_m (1.63 m)
           past the sealing wall's far face — the wall stands in for the curb — on whatever deck is there
           (the sealed opening's road, the apron, the loop's walk: y_base = the top hit over ROAD + ground).
           Its clearance is measured to that wall (>= GATE_MIN mainline 1.3, <= 3.0), its disc footprint
           against the MAINLINE alone (what that layout's drive_test sweeps), and it must stand on no wall.
           Its meshes are SIGNPLATE_<token>_<k> / SIGNARROW_<token>_<k> / SIGNPOST_<token>_<k> in the
           RACE_CLOSE_<TOKEN> collection (tools/race_furniture.layout_sign_owner): the export split routes them
           into that layout's closure kn5 and no other layout ever loads them. Because
           tools/author_race_furniture_blend.py removes every member of RACE_CLOSE_* when it re-authors, this
           script runs AFTER it on every ship (tools/ship_sd.sh "author: W1-6 ..." after the furniture).

Idempotent: existing SIGNPLATE_* / SIGNARROW_* / SIGNPOST_* meshes are deleted first (the layout plates'
SIGN*_<token>_* included). The stale outputs (data/signs.local.json, signs_preview.svg,
signs_measured.json) are unlinked at START so a crash can never leave the previous run's record behind for
the verifier. Always prints one "[signs] ..." line (the ship pipe greps for it under set -euo pipefail).

Runs INSIDE Blender 4.2 after author_lamps_blend and the race furniture, before the kn5 prep:

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
WALL_CLEAR_M = ps.WALL_CLEAR_M      # every post this far from every 1WALL* face (ledger 0054 P4)
LAYOUT_WALL_SCAN_M = 30.0           # a layout plate: the sealing wall is looked for this far along the ray past the lip
STALE_OUTPUTS = ("signs.local.json", "signs_preview.svg", "signs_measured.json")


def B(p):
    return (p[0], p[2], p[1])


def post_kind(s):
    """MAINLINE for a mainline post (a layout plate included), CONNECTOR for a side-street or north post"""
    return "MAINLINE" if s["ribbon"] == "MAINLINE" else "CONNECTOR"


def wall_dist(walls, x, y, z):
    """metres from the post base (engine x, y, z) to the nearest 1WALL* face, measured 0.6 m up the post (a K-rail's
    face stands above its base; inf when no wall)"""
    return sm.nearest_dist(walls, x, y + 0.6, z)


def ensure_collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


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


def mesh_place(s, ctx, cfg, road, ground, walls=None):
    """re-place one plate's post on the built mesh (see module doc); mutates the record and
    returns the fatal reasons (empty = placed). walls = the 1WALL* BVH every post keeps WALL_CLEAR_M from."""
    x0, z0 = s["base_xz"]
    s["base_xz_polyline"] = [x0, z0]
    t = (-s["face_dir_xz"][0], -s["face_dir_xz"][1])
    A = s["ray"]["A_xz"]
    u = s["curb_dir_xz"]
    rights = (s["right_xz"],)
    kind = post_kind(s)
    is_main = kind == "MAINLINE"
    walk_w = ps.SIDEWALK_W[kind]
    d_clear = s["lateral_offset_m"]
    gate_min = GATE_MIN[kind]
    disc_names = ps.disc_names_for(s["ribbon"], ctx.gated)     # None = every ribbon's disc is hard (mainline post)
    applied = s.get("overrides_applied", [])
    forced = "force" in applied
    reasons, warns = [], []
    chk = s["checks"]
    chk["slid_polyline_m"] = chk.get("slid_m", 0.0)
    walk_behind = None

    def polar(x, z, reach=sm.POLAR_REACH):
        return sm.polar_clearance(road, ground, x, z, reach=reach)

    def wall_at(x, z):
        g = sm.top_hit(ground, x, z)
        return wall_dist(walls, x, g if g is not None else s["y_base"]["analytic"], z)

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
            # ledger 0079 round L: with no walk along the ray the analytic base (the walk's y_road + 0.24) describes
            # nothing that was built (Sand Creek: "no sidewalks"); the ground under the post is the terrain ray-cast
            s["ray"]["no_walk"] = True
        # the authoritative march: along the ray only, until the built clearance AND the GATED
        # disc AND the wall clearance hold. Cap: mainline +6 m past the built curb; connector 1.5 m behind the walk.
        s_cap = s_C + ps.RAY_EXTRA_CAP_M if is_main else s_B + CONNECTOR_BEHIND_WALK_CAP_M
        cap_txt = "+%.0f m past the built curb" % ps.RAY_EXTRA_CAP_M if is_main else "%.1f m behind the modelled walk" % CONNECTOR_BEHIND_WALK_CAP_M
        s_m, capped = s_est, False
        while True:
            qx, qz = A[0] + t[0] * s_m, A[1] + t[1] * s_m
            pc = polar(qx, qz, reach=d_clear + 0.05)[0]
            fm = ctx.field.footprint_margin((qx, qz), rights, disc_names)
            if pc >= d_clear - CLEAR_TOL and fm >= DISC_CUSHION and wall_at(qx, qz) >= WALL_CLEAR_M:
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
        side_step = 0.0
        if capped and not is_main and (pc_m < gate_min - CLEAR_TOL or fm_m < 0 or wall_at(xm, zm) < WALL_CLEAR_M):
            # a grazing exit (ledger 0054 P4, the J2 / J3 reverse plates): the ray leaves the pad's curb return at so
            # flat an angle that no point on it within the cap is clear — the post steps square off the ray, to the
            # OUTSIDE of the turn, until the built clearance, the disc and the walls hold (SIDE_STEP_MAX_M)
            D = s["corner"]["D_deg"]
            n_out = (-t[1], t[0]) if D < 0 else (t[1], -t[0])
            q = MARCH_STEP
            while q <= ps.SIDE_STEP_MAX_M:
                qx, qz = xm + n_out[0] * q, zm + n_out[1] * q
                pc_q = polar(qx, qz, reach=d_clear + 0.05)[0]
                fm_q = ctx.field.footprint_margin((qx, qz), rights, disc_names)
                if pc_q >= d_clear - CLEAR_TOL and fm_q >= DISC_CUSHION and wall_at(qx, qz) >= WALL_CLEAR_M:
                    side_step = q
                    break
                q += MARCH_STEP
            if side_step:
                xm, zm = xm + n_out[0] * side_step, zm + n_out[1] * side_step
                capped = False
                pc_m, fm_m = polar(xm, zm)[0], ctx.field.footprint_margin((xm, zm), rights, disc_names)
                s["ray"].update(side_step_from_m=round(s_m, 2), side_step_m=round(side_step, 2))
                warns.append("grazing exit: no point on the ray within the %s cap clears the built curb; the post stepped %.2f m square "
                             "off the ray to the outside of the turn" % (cap_txt, side_step))
        chk["lateral_step_m"] = round(side_step, 2)
        if capped:
            if fm_m < 0:
                reasons.append("plate footprint inside drive_test's obstacle disc (%s) by %.2f m at the %s cap"
                               % (ps.gate_label(disc_names), -fm_m, cap_txt))
            if pc_m < gate_min - CLEAR_TOL:
                reasons.append("built-edge clearance %.2f m < %.1f m gate minimum at the %s cap" % (pc_m, gate_min, cap_txt))
            elif pc_m < d_clear - CLEAR_TOL:
                warns.append("built-edge clearance %.2f m (target %.2f) at the %s cap; passes the %.1f m gate minimum"
                             % (pc_m, d_clear, cap_txt, gate_min))
            if wall_at(xm, zm) < WALL_CLEAR_M:
                reasons.append("post %.2f m from a wall face (< %.1f m) at the %s cap" % (wall_at(xm, zm), WALL_CLEAR_M, cap_txt))
        if reasons and not forced:
            s["base_xz"] = [round(xm, 3), round(zm, 3)]
            s["base_source"] = "mesh march capped (%s start)" % src
            chk.update(walk_behind_m=walk_behind, gate_ribbons=ps.gate_label(disc_names))
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
    wd = wall_at(x, z)
    chk.update(mesh_clear_m=round(pc_f, 2), mesh_clear_bearing_deg=pc_bearing, mesh_shift_m=round(shift, 2),
               edge_clear_m=round(ctx.field.query(x, z)[0], 2), gate_margin_m=round(fm_f, 2),
               gate_margin_gated_m=round(fm_gated, 2), gate_ribbons=ps.gate_label(disc_names),
               walk_behind_m=walk_behind, wall_m=None if wd == float("inf") else round(wd, 2),
               lamp_m=round(lamp, 2), plant_m=round(plant[0], 2), plant_zone=plant[1], slid_m=round(slid, 2))
    if fm_gated < 0:
        reasons.append("plate footprint inside drive_test's obstacle disc by %.2f m (%s)" % (-fm_gated, ps.gate_label(disc_names)))
    elif fm_f < 0:
        warns.append("plate footprint %.2f m inside the obstacle disc of a connector centreline (%s): not gated, drive_test sweeps the mainline only; the post stays at the back of the walk (REALISM)"
                     % (-fm_f, s["ribbon"]))
    if pc_f < gate_min - CLEAR_TOL:
        reasons.append("built-edge clearance %.2f m < %.1f m" % (pc_f, gate_min))
    if is_main and pc_f > 3.0:
        reasons.append("built-edge clearance %.2f m > 3.0 m (too far from the curb)" % pc_f)
    if wd < WALL_CLEAR_M:
        reasons.append("post %.2f m from a wall face (< %.1f m)" % (wd, WALL_CLEAR_M))
    if "base_xz" in applied and lamp < cfg["lamp_clear_m"]:
        reasons.append("pinned base %.1f m from a lamp post (< %.1f)" % (lamp, cfg["lamp_clear_m"]))
    s["base_xz"] = [round(x, 3), round(z, 3)]
    chk["warnings"] = chk.get("warnings", []) + warns
    if reasons and forced:
        chk["warnings"] += ["FORCED past: " + r for r in reasons]
        reasons = []
    return reasons


def mesh_place_layout(s, ctx, cfg, road, ground, walls_all, walls_layout):
    """a LAYOUT PLATE on the built mesh (module doc "layout"): along the ray, the post stands lateral_offset_m past the
    far face of the layout's sealing wall (walls_layout: the walls that layout loads), on whatever deck is there.
    Mutates the record; returns the fatal reasons (empty = placed)."""
    x0, z0 = s["base_xz"]
    s["base_xz_polyline"] = [x0, z0]
    t = (-s["face_dir_xz"][0], -s["face_dir_xz"][1])
    A = s["ray"]["A_xz"]
    rights = (s["right_xz"],)
    d_clear = s["lateral_offset_m"]
    gate_min = GATE_MIN["MAINLINE"]
    disc_names = ps.GATED_RIBBONS                    # a race layout's drive_test sweeps the mainline alone
    reasons, warns = [], []
    chk = s["checks"]
    chk["slid_polyline_m"] = chk.get("slid_m", 0.0)
    if walls_layout is None:
        s["base_source"] = "polyline (no race wall built for layout %s)" % s["layout"]
        return ["no race wall built for layout %s (RACE / RACE_CLOSE_<TOKEN> collections empty)" % s["layout"]]

    def deck_y(x, z):
        ys = [v for v in (sm.top_hit(road, x, z), sm.top_hit(ground, x, z)) if v is not None]
        return max(ys) if ys else None

    def on_wall(x, z):
        """the point stands under the layout's wall (its footprint) — a top hit on the wall BVH above the deck"""
        w = sm.top_hit(walls_layout, x, z)
        d = deck_y(x, z)
        return w is not None and (d is None or w > d + 0.05)

    # walk the ray past the polyline lip: the first wall sample, then the sample where the wall ends (its far face)
    s_lip = max(0.0, s["ray"]["len_m"] - 4.0)
    s_in = s_out = None
    step = MARCH_STEP
    q = s_lip
    while q <= s["ray"]["len_m"] + LAYOUT_WALL_SCAN_M:
        hit = on_wall(A[0] + t[0] * q, A[1] + t[1] * q)
        if s_in is None and hit:
            s_in = q
        elif s_in is not None and not hit:
            s_out = q
            break
        q += step
    if s_in is None:
        s["base_source"] = "polyline (the ray crosses no wall of layout %s within %.0f m of the lip)" % (s["layout"], LAYOUT_WALL_SCAN_M)
        return ["the ray crosses no wall of layout %s within %.0f m past the lip (is the opening sealed there?)" % (s["layout"], LAYOUT_WALL_SCAN_M)]
    if s_out is None:
        return ["the wall of layout %s runs along the ray past the scan (%.0f m)" % (s["layout"], LAYOUT_WALL_SCAN_M)]
    # past the wall's far face, on along the ray until the NEAREST face of the layout's walls is lateral_offset_m
    # away (a ray that crosses a curved or oblique wall is closer to it than its own length says), capped at
    # RAY_EXTRA_CAP_M past the far face — the curb rule's own cap
    s_m = s_out + d_clear
    while s_m < s_out + ps.RAY_EXTRA_CAP_M:
        qx, qz = A[0] + t[0] * s_m, A[1] + t[1] * s_m
        qy = deck_y(qx, qz)
        if qy is not None and wall_dist(walls_layout, qx, qy, qz) >= d_clear - CLEAR_TOL and not on_wall(qx, qz):
            break
        s_m += step
    x, z = A[0] + t[0] * s_m, A[1] + t[1] * s_m
    s["base_xz_mesh"] = [round(x, 3), round(z, 3)]
    s["ray"].update(wall_in_m=round(s_in, 2), wall_out_m=round(s_out, 2), s_S_mesh_m=round(s_m, 2),
                    C_mesh_xz=[round(A[0] + t[0] * s_in, 2), round(A[1] + t[1] * s_in, 2)], len_mesh_m=round(s_in, 2))
    # the slide (lamps / plants) on the built position, along the curb direction, never onto the wall
    u = s["curb_dir_xz"]
    y_here = deck_y(x, z)
    slid, S, lamp, plant, excl, slide_reasons = ps.choose_slide(
        ctx, cfg, (x, z), u, d_clear,
        lambda qx, qz: (-1.0 if on_wall(qx, qz) else wall_dist(walls_layout, qx, deck_y(qx, qz) if deck_y(qx, qz) is not None else y_here, qz)),
        rights, disc_names)
    reasons += slide_reasons
    s["exclude_plant"] = excl
    x, z = S
    for a in s.get("overrides_applied", []):
        if a.startswith("slide_along_curb_m="):
            sl = float(a.split("=", 1)[1])
            x, z = x + u[0] * sl, z + u[1] * sl
            slid += sl
    # measure the final post: its clearance IS the distance to the layout's wall; every wall >= WALL_CLEAR_M; the
    # MAINLINE disc; on no wall; the deck under it
    yd = deck_y(x, z)
    if yd is None:
        reasons.append("no built deck under the post (nothing to stand on)")
        yd = s["y_base"]["analytic"]
    wl = wall_dist(walls_layout, x, yd, z)
    wa = wall_dist(walls_all, x, yd, z)
    fm_f = ctx.field.footprint_margin((x, z), rights)
    fm_gated = ctx.field.footprint_margin((x, z), rights, disc_names)
    pc_all = sm.polar_clearance(road, ground, x, z)[0]
    shift = math.hypot(x - x0, z - z0)
    chk.update(mesh_clear_m=round(wl, 2), mesh_clear_bearing_deg=None, mesh_shift_m=round(shift, 2),
               edge_clear_m=round(ctx.field.query(x, z, only=("MAINLINE",))[0], 2),
               edge_clear_all_m=round(ctx.field.query(x, z)[0], 2), pavement_clear_m=round(pc_all, 2),
               gate_margin_m=round(fm_f, 2), gate_margin_gated_m=round(fm_gated, 2), gate_ribbons=ps.gate_label(disc_names),
               walk_behind_m=None, wall_m=None if wa == float("inf") else round(wa, 2),
               lamp_m=round(lamp, 2), plant_m=round(plant[0], 2), plant_zone=plant[1], slid_m=round(slid, 2),
               on_deck=sm.on_road(road, ground, x, z))
    if on_wall(x, z):
        reasons.append("the post stands on a wall of layout %s" % s["layout"])
    if wl < gate_min - CLEAR_TOL:
        reasons.append("wall clearance %.2f m < %.1f m (the sealing wall stands in for the curb)" % (wl, gate_min))
    if wl > 3.0:
        reasons.append("wall clearance %.2f m > 3.0 m (too far behind the wall)" % wl)
    if wa < WALL_CLEAR_M:
        reasons.append("post %.2f m from a wall face (< %.1f m)" % (wa, WALL_CLEAR_M))
    if fm_gated < 0:
        reasons.append("plate footprint inside drive_test's obstacle disc by %.2f m (%s)" % (-fm_gated, ps.gate_label(disc_names)))
    warns.append("layout plate for %s: the sealing wall crossed %.2f-%.2f m along the ray, the post %.2f m past its far face "
                 "(the wall stands in for the curb); on %s; every centreline's disc %+.2f m (the sealed openings' not gated here)"
                 % (s["layout"], s_in, s_out, d_clear, "the sealed opening's deck" if chk["on_deck"] else "the walk / ground beside it", fm_f))
    s["base_xz"] = [round(x, 3), round(z, 3)]
    s["base_source"] = "mesh (layout %s: the ray through the sealing wall, %.2f m past its far face, slid %.2f m)" % (s["layout"], d_clear, slid)
    chk["warnings"] = chk.get("warnings", []) + warns
    if reasons and "force" in s.get("overrides_applied", []):
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
    race_excluded = list(sm.load_bvhs.last_race)     # ledger 0051: race furniture is never the signs' ground
    walls = sm.load_wall_bvhs()                      # ledger 0054 P4: every 1WALL* (clearance) + each race token's walls
    wall_names = dict(sm.load_wall_bvhs.names)
    tokens = {lo["id"]: lo["token"] for lo in ctx.layouts if lo["race"]}
    print("[signs] ground %s; road %s; race furniture left out of both: %d object%s; walls %d (race tokens %s)"
          % ("+".join(ground_names) or "nothing", "+".join(road_names) or "nothing", len(race_excluded), "" if len(race_excluded) == 1 else "s",
             len(wall_names.get("all", [])), ", ".join("%s:%d" % (k, len(v)) for k, v in sorted(wall_names.items()) if k != "all") or "none"))

    # 1) every plate on the built mesh; a plate that cannot be placed cleanly is skipped, loudly
    kept = []
    for s in out["signs"]:
        if s.get("layout"):
            tok = tokens.get(s["layout"], "")
            reasons = mesh_place_layout(s, ctx, cfg, road, ground, walls.get("all"), walls.get(tok))
        else:
            reasons = mesh_place(s, ctx, cfg, road, ground, walls.get("all"))
        if reasons:
            out["skipped"].append({"id": s["id"], "ribbon": s["ribbon"] + ("(rev)" if s["direction"] == "rev" else ""),
                                   **({"layout": s["layout"]} if s.get("layout") else {}),
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
                           gate_margin_gated_m=round(ctx.field.footprint_margin((x, z), rights, ps.disc_names_for(s["ribbon"], ctx.gated)), 2),
                           edge_clear_m=round(ctx.field.query(x, z)[0], 2),
                           lamp_m=round(ctx.nearest_lamp((x, z)), 2), plant_m=round(ctx.nearest_plant((x, z))[0], 2))
    out["signs"] = signs
    out["exclude_plants"] = [dict(s["exclude_plant"], sign=s["id"]) for s in signs if s.get("exclude_plant")]
    out["pairs"] = [s["id"] for s in signs if s.get("pair")]
    out["layout_plates"] = [s["id"] for s in signs if s.get("layout")]
    out["counts"] = {"placed": len(signs), "plates": sum(len(ps.plates_of(s)) for s in signs), "skipped": len(out["skipped"]),
                     "layout_plates": len(out["layout_plates"])}

    # 3) ground + meshes — one batch set per destination: the road kn5 (key ""), and one per race token for the
    #    layout plates (key = the token: SIGN*_<token>_<k> in RACE_CLOSE_<TOKEN>)
    batches = {}
    cur = {}

    def dest_of(s):
        return tokens.get(s["layout"], "") if s.get("layout") else ""

    def flush(dest, kind):
        V, F, N = cur[dest][kind]
        if V:
            batches[dest][kind].append((list(V), list(F), list(N)))
            V.clear(); F.clear(); N.clear()

    n_warn = 0
    for s in signs:
        dest = dest_of(s)
        if dest not in batches:
            batches[dest] = {k: [] for k in PREFIXES}
            cur[dest] = {k: ([], [], []) for k in PREFIXES}
        x, z = s["base_xz"]
        pushed = 0.0
        g = sm.top_hit(ground, x, z)
        r = sm.top_hit(road, x, z)
        t = (-s["face_dir_xz"][0], -s["face_dir_xz"][1])
        if s.get("layout"):
            # a layout plate stands where the sealing wall put it — on the sealed opening's deck if that is what is
            # there (never pushed off ROAD); its ground is the highest built surface under it
            ys = [v for v in (g, r) if v is not None]
            y_base, src = (max(ys), "raycast (deck: the highest of ROAD / ground under the post)") if ys else (s["y_base"]["analytic"], "analytic (no ground hit)")
            g = y_base if ys else None
        else:
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
            elif any(p["ray"].get("no_walk") for p in ps.plates_of(s)):
                # no modelled walk along the ray (ledger 0079 round L): no walk height to expect, the terrain is the ground
                y_base, src = g, "raycast (no modelled walk, %+.2f m vs a walk's analytic height)" % (g - analytic)
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
            V, F, N = cur[dest][kind]
            if len(V) + nv > CAP:
                flush(dest, kind)
                V, F, N = cur[dest][kind]
            for verts, normal in lst:
                vb = oriented([B(v) for v in verts], B(normal))
                off = len(V)
                V.extend(vb)
                for k in range(1, len(vb) - 1):
                    F.append((off, off + k, off + k + 1))
                    N.append(B(normal))
        s["blender"]["meshes"] = {k: mesh_name(k, dest, len(batches[dest][k])) for k in PREFIXES}
        if dest:
            s["blender"]["collection"] = sm.RACE_CLOSE_COLLECTION + dest.upper()
    for dest in batches:
        for kind in PREFIXES:
            flush(dest, kind)

    nverts = {k: 0 for k in PREFIXES}
    nfaces = {k: 0 for k in PREFIXES}
    bad = 0
    made = {}
    for dest, per_kind in batches.items():
        col = ensure_collection(sm.RACE_CLOSE_COLLECTION + dest.upper()) if dest else None
        for kind, lst in per_kind.items():
            for k, (V, F, N) in enumerate(lst):
                ob = _mk(mesh_name(kind, dest, k), V, F)
                if col is not None:               # a layout plate lives in its layout's closure collection
                    for c in list(ob.users_collection):
                        c.objects.unlink(ob)
                    col.objects.link(ob)
                made.setdefault(dest, []).append(ob.name)
                nverts[kind] += len(ob.data.vertices)
                nfaces[kind] += len(ob.data.polygons)
                for poly, want in zip(ob.data.polygons, N):
                    if poly.normal.x * want[0] + poly.normal.y * want[1] + poly.normal.z * want[2] < 0:
                        bad += 1
    bpy.ops.wm.save_mainfile(filepath=str(blend))

    out["blender"] = {"blend": str(blend), "ground_objects": ground_names, "road_objects": road_names,
                      **({"race_excluded": race_excluded} if race_excluded else {}),   # absent = none (a track with no race furniture keeps its bytes)
                      "walls": {k: len(v) for k, v in sorted(wall_names.items())},
                      "removed_existing": removed, "meshes": {k: [mesh_name(k, "", i) for i in range(len(batches.get("", {}).get(k, [])))] for k in PREFIXES},
                      "layout_meshes": {sm.RACE_CLOSE_COLLECTION + d.upper(): names for d, names in sorted(made.items()) if d},
                      "vertices": nverts, "faces": nfaces, "normal_mismatches": bad, "ground_warnings": n_warn,
                      "base_rule": "built mesh authoritative: walk-fraction start, marched along the ray to polar clearance >= lateral_offset, "
                                   "disc footprint >= 0 and every wall >= %.1f m; a layout plate lateral_offset past its layout's sealing wall" % WALL_CLEAR_M}
    ps.write_outputs(proj, out, ctx)
    for s in signs:
        c = s["checks"]
        print("[signs] %-11s %-12s %-20s base (%8.1f, %6.2f, %8.1f) faces %s deg  built clear %.2f m (shift %.2f, slid %+.2f)  walk-behind %s  wall %s  disc %+.2f (gated %s %+.2f)  y_base %s%s"
              % (s["id"], s["kind"], s["ribbon"] + "/" + s["direction"] + (("@" + s["layout"]) if s.get("layout") else ""), s["base_xz"][0], s["y_base"]["value"], s["base_xz"][1],
                 "/".join("%.1f" % p["face_bearing_deg"] for p in ps.plates_of(s)), c["mesh_clear_m"], c["mesh_shift_m"],
                 c["slid_m"], "%+.2f" % c["walk_behind_m"] if c.get("walk_behind_m") is not None else "-",
                 "%.2f" % c["wall_m"] if c.get("wall_m") is not None else "-",
                 c["gate_margin_m"], c.get("gate_ribbons", "all"), c.get("gate_margin_gated_m", c["gate_margin_m"]), s["y_base"]["source"],
                 ("  WARN " + "; ".join(c["warnings"])) if c["warnings"] else ""))
    for s in out["skipped"]:
        print("[signs] skip %-11s %-20s v%-5d %s" % (s["id"], s["ribbon"], s["apex_vertex"], "; ".join(s["reasons"])))
    print("[signs] %s -> %s%s; %d verts, %d faces; normals %s; ground from %s (ROAD rejects %s); removed %d old; overrides %s; saved %s"
          % (ps.summary_line(out),
             " + ".join("%d %s" % (len(batches.get("", {}).get(k, [])), k) for k in PREFIXES),
             "".join(" + %d in RACE_CLOSE_%s" % (len(v), d.upper()) for d, v in sorted(made.items()) if d),
             sum(nverts.values()), sum(nfaces.values()),
             "OK" if bad == 0 else "%d MISMATCHED" % bad,
             "+".join(ground_names) or "nothing", "+".join(road_names) or "nothing",
             removed, ov_path if ov_path.exists() else "(none)", blend))


def mesh_name(kind, dest, k):
    """SIGNPLATE_<k> in the road kn5; SIGNPLATE_<token>_<k> for a layout plate (tools/race_furniture.layout_sign_owner)"""
    return "%s_%d" % (kind, k) if not dest else "%s_%s_%d" % (kind, dest, k)


main()
