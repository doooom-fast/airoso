"""The road shoulder graded onto the lidar ground, on the prepped scene (ledger 0102, Milford round 2; Kevin 2026-11-22 on
the calls page, "the 32 far ledges?" -> "Reshape the shoulder").

What was wrong (measured on Milford 0.1.13's gate OBJ, ledger 0102): drive_test's excursion sweep (every 150 m) counts 32
far ledges, drops over 0.12 m per 0.5 m between the built edge + 4 m and the line + w/2 + 9 m. The same sweep every 3 m
finds 1,491 of them on 404 of 3,266 crossings, about 1.2 km of edge; at 1,382 the 2017 lidar under them is flatter than the
drop, and the built ground at the drop's foot sits a median 0.58 m (p5 2.04 m) UNDER it. The cross-sections show why: the
prep holds a shelf at the deck for 3 m and feathers 3-9 m onto TERRAIN, and in the corridor patch's ramp (0 lidar at 9 m,
1 at 16 m off the lane edge) TERRAIN is still the assembler's draft ground, up to 3 m under the real ground, so the built
ground falls into a trench 3-14 m out and climbs back, even where the real ground rises away from the road.

The fix: every ground vertex between from_m and to_m off the drivable surface's outer edge (1ROAD / 1KERB, after the prep)
takes a graded shoulder T instead of the trench:
  T is built on the committed 1 m lidar grid, outward from the road: the cells under the road and within from_m of its
  edge hold the edge's own height less the prep's 0.02 m clearance (the shelf the prep already built), and every cell
  further out, in order of its distance to the edge, takes the lidar's ground, held no lower than any neighbour already
  graded less fall_max per metre between them (the shoulder never falls away faster than fall_max) and no higher than one
  plus rise_max per metre (a cut never steps up faster than rise_max). Where the real ground falls no faster than
  fall_max (most of the lap) T IS the lidar; where it falls faster, T is a graded fill at fall_max until it meets it.
  Vertices to full_m take T; full_m to to_m blend back onto the prepped ground (smoothstep); past to_m nothing moves.
Nothing under the drivable surface or within from_m of its edge moves (the prep's pin and shelf stay bit for bit).

Opt-in: terrain.shoulder_grade in track.config.json:
    {"npz": "source/lidar/milford_lidar_1m.npz", "lidar_shift_m": [-0.375, 0.938], "from_m": 2.0, "full_m": 15.0,
     "to_m": 20.0, "fall_max": 0.1667, "rise_max": 0.5, "max_fill_m": 1.0, "keep_patches": ["culvert_4349_w"]}
(none = no-op, the blend not saved, no report). Self-check (exit 1, the blend not saved): the graded grid must hold the
fall_max / rise_max rule between every pair of graded neighbours, no moved vertex may lie under the drivable surface or
within from_m of its edge, and the npz must cover every edge point. Writes data/shoulder_grade.json.

    blender --background --python-exit-code 1 --python tools/shoulder_grade_blend.py -- <blender/<slug>.blend> --project <dir>
"""
from __future__ import annotations

import heapq
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

DRIVABLE = ("1ROAD", "1KERB")
GROUND_CLEAR = 0.02      # the prep's shelf: the deck less 0.02 m (engine-july's GROUND_CLEAR)
EDGE_STEP_M = 0.25       # the outer edge densified this fine before the nearest-edge reads
SEAM_MM = 1.0            # a boundary edge whose midpoint another drivable boundary edge shares within this is a tile seam


def fail(msg):
    print(f"[shoulder] FATAL: {msg}; the blend not saved")
    raise SystemExit(1)


def smoothstep(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def poly_dist(poly, x, y):
    """0 inside the polygon, else the distance to its boundary (plan)"""
    inside, best, n = False, math.inf, len(poly)
    for k in range(n):
        (x1, y1), (x2, y2) = poly[k], poly[(k + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
        best = min(best, math.hypot(x - x1 - t * dx, y - y1 - t * dy))
    return 0.0 if inside else best


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    blend = Path(a[0])
    proj = Path(a[a.index("--project") + 1])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    terr = cfg.get("terrain") or {}
    sg = terr.get("shoulder_grade")
    if not sg:
        print("[shoulder] no terrain.shoulder_grade: no-op")
        return
    FROM, FULL, TO = float(sg.get("from_m", 2.0)), float(sg.get("full_m", 15.0)), float(sg.get("to_m", 20.0))
    FALL = float(sg.get("fall_max", 1.0 / 6.0))
    RISE = sg.get("rise_max")
    RISE = float(RISE) if RISE is not None else math.inf
    if not (0.0 <= FROM < FULL < TO):
        fail(f"from_m {FROM} / full_m {FULL} / to_m {TO}: need 0 <= from < full < to")
    # the deepest fill the shoulder builds over the real ground: where the graded slope would stand higher than this over the
    # lidar, the drop is the real ground's (a culvert's ravine, an embankment's foot) and stays, the fill held at this depth
    MAX_FILL = float(sg.get("max_fill_m", math.inf))
    exclude = set(sg.get("exclude") or [])
    fg = (terr.get("far_ground") or {}).get("object")
    if fg:
        exclude.add(fg)
    ground_prefix = tuple(sg.get("objects") or ["1GRASS"])
    # real ground the shoulder leaves alone: lidar patches named by id (a culvert's headwall, a real ditch the lidar
    # shows), each grown by its own feather_m; the shoulder blends in over KEEP_BLEND_M outside it
    KEEP_BLEND = float(sg.get("keep_blend_m", 5.0))
    patches = {p_.get("id"): p_ for p_ in (terr.get("lidar_patches") or [])}
    keep = []
    for pid in sg.get("keep_patches") or []:
        if pid not in patches:
            fail(f"keep_patches names {pid!r}, which terrain.lidar_patches does not declare")
        keep.append((pid, [tuple(map(float, q)) for q in patches[pid]["polygon"]], float(patches[pid].get("feather_m", 0.0))))
    line = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    elev0 = float(line["origin"]["elev_m"])

    bpy.ops.wm.open_mainfile(filepath=str(blend))
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    driv = [o for o in objs if o.name.upper().startswith(DRIVABLE)]
    ground = [o for o in objs if o.name.startswith(ground_prefix) and o.name not in exclude]
    if not driv or not ground:
        fail(f"{len(driv)} drivable / {len(ground)} ground objects")

    # --- the drivable surface's outer edge: every object's boundary edges, less the seams two objects share ----------------
    seg, verts, polys = [], [], []
    keycount = {}
    for o in driv:
        mw = o.matrix_world
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.verts.ensure_lookup_table()
        W = [mw @ v.co for v in bm.verts]
        base = len(verts)
        verts += [(p.x, p.y, p.z) for p in W]
        for f in bm.faces:
            idx = [v.index for v in f.verts]
            for k in range(1, len(idx) - 1):
                polys.append((base + idx[0], base + idx[k], base + idx[k + 1]))
        for e in bm.edges:
            if len(e.link_faces) == 1:
                p, q = W[e.verts[0].index], W[e.verts[1].index]
                key = (round((p.x + q.x) * 500 / SEAM_MM), round((p.y + q.y) * 500 / SEAM_MM))
                keycount[key] = keycount.get(key, 0) + 1
                seg.append((p.copy(), q.copy(), key))
        bm.free()
    outer = [(p, q) for p, q, k in seg if keycount[k] == 1]
    seams = len(seg) - len(outer)
    dbvh = BVHTree.FromPolygons(verts, polys)
    pts = []
    for p, q in outer:
        L = (q - p).length
        n = max(1, int(math.ceil(L / EDGE_STEP_M)))
        for t in range(n):
            r = p.lerp(q, t / n)
            pts.append((r.x, r.y, r.z))
    kd = KDTree(len(pts))
    for i, (x, y, _) in enumerate(pts):
        kd.insert((x, y, 0.0), i)
    kd.balance()
    print(f"[shoulder] drivable: {len(driv)} objects, {len(outer)} outer boundary edges ({seams} seam edges dropped), "
          f"{len(pts)} edge points every {EDGE_STEP_M} m")

    def under_road(x, y):
        h = dbvh.ray_cast(Vector((x, y, 5000.0)), Vector((0, 0, -1)))
        return h[0] is not None

    # --- the lidar grid --------------------------------------------------------------------------------------------------
    npz = np.load(str(proj / sg.get("npz", "source/lidar/milford_lidar_1m.npz")))
    e0, n0, cell = float(npz["e0"]), float(npz["n0"]), float(npz["cell"])
    # lidar_shift_m (opt-in): the grid's registration to the line's frame, frame = lidar + shift (tools/measured_surface.py's
    # registration_lidar_shift_m; Milford's committed grid sits (-0.375, +0.938) m off the frame the road is built in, and
    # on the banked turn's 45 % outer slope that metre is ~0.45 m of height). Absent = the grid as committed
    SHIFT = [float(v) for v in (sg.get("lidar_shift_m") or [0.0, 0.0])]
    e0, n0 = e0 + SHIFT[0], n0 + SHIFT[1]
    gz = npz["ground_z_cm_over_z0"]
    ny, nx = gz.shape
    Lg = np.where(gz != -1, float(npz["z0_m"]) + gz / 100.0 - elev0, np.nan)
    xs = np.asarray([p[0] for p in pts]); ys = np.asarray([p[1] for p in pts])
    if xs.min() < e0 or ys.min() < n0 or xs.max() > e0 + nx * cell or ys.max() > n0 + ny * cell:
        fail("the lidar grid does not cover every edge point")

    # every cell within to_m + 2 cells of the edge: its distance, its nearest edge point, under the road or not
    reach = TO + 2.0 * cell
    i0, i1 = max(0, int((xs.min() - reach - e0) / cell)), min(nx, int((xs.max() + reach - e0) / cell) + 1)
    j0, j1 = max(0, int((ys.min() - reach - n0) / cell)), min(ny, int((ys.max() + reach - n0) / cell) + 1)
    D = np.full((ny, nx), np.inf)
    H = np.full((ny, nx), np.nan)          # the nearest edge point's height
    inside = np.zeros((ny, nx), bool)
    for j in range(j0, j1):
        yc = n0 + (j + 0.5) * cell
        for i in range(i0, i1):
            xc = e0 + (i + 0.5) * cell
            co, k, d = kd.find((xc, yc, 0.0))
            if d > reach:
                continue
            D[j, i] = d
            H[j, i] = pts[k][2]
            if d <= 30.0 and under_road(xc, yc):
                inside[j, i] = True
    corr = np.isfinite(D)
    kept = np.zeros((ny, nx), bool)
    for _, poly, fe in keep:
        xs_, ys_ = [q[0] for q in poly], [q[1] for q in poly]
        ia_, ib_ = max(0, int((min(xs_) - fe - e0) / cell) - 1), min(nx, int((max(xs_) + fe - e0) / cell) + 2)
        ja_, jb_ = max(0, int((min(ys_) - fe - n0) / cell) - 1), min(ny, int((max(ys_) + fe - n0) / cell) + 2)
        for j in range(ja_, jb_):
            for i in range(ia_, ib_):
                if poly_dist(poly, e0 + (i + 0.5) * cell, n0 + (j + 0.5) * cell) <= fe:
                    kept[j, i] = True
    corr &= ~kept
    # lidar holes in the corridor filled from their neighbours (as tools/lidar_ground_patch.py does under roofs)
    Lf = Lg.copy()
    filled = 0
    for _ in range(60):
        hole = np.isnan(Lf) & corr & ~inside
        if not hole.any():
            break
        pad = np.pad(Lf, 1, constant_values=np.nan)
        nb = np.stack([pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]])
        cnt = (~np.isnan(nb)).sum(0)
        take = hole & (cnt > 0)
        if not take.any():
            break
        Lf[take] = np.nansum(nb, 0)[take] / cnt[take]
        filled += int(take.sum())

    # --- the graded shoulder T, outward in order of distance ---------------------------------------------------------------
    T = np.full((ny, nx), np.nan)
    conflict = np.zeros((ny, nx), bool)
    seed = corr & (inside | (D <= FROM))
    T[seed] = H[seed] - GROUND_CLEAR
    order = np.argwhere(corr & ~seed)
    order = order[np.argsort(D[order[:, 0], order[:, 1]], kind="stable")]
    nbrs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    held_low = held_high = conflicts = no_nb = capped = 0
    conflict_at, capped_at = [], []
    for j, i in order:
        lo, hi = -math.inf, math.inf
        for dj, di in nbrs:
            jj, ii = j + dj, i + di
            if 0 <= jj < ny and 0 <= ii < nx:
                t = T[jj, ii]
                if t == t:
                    dist = cell * math.hypot(dj, di)
                    lo = max(lo, t - FALL * dist)
                    hi = min(hi, t + RISE * dist)
        base = Lf[j, i]
        if lo == -math.inf:
            no_nb += 1
            T[j, i] = base if base == base else H[j, i] - GROUND_CLEAR
            continue
        if base != base:
            base = lo
        if lo > hi:
            conflicts += 1
            if len(conflict_at) < 200:
                conflict_at.append([round(e0 + (i + 0.5) * cell, 1), round(n0 + (j + 0.5) * cell, 1), round(float(D[j, i]), 1),
                                    round(lo - hi, 3)])
            T[j, i] = 0.5 * (lo + hi)
            conflict[j, i] = True
        elif base < lo:
            if lo - base > MAX_FILL:
                capped += 1
                conflict[j, i] = True          # off the rule on purpose: the self-check skips it as it skips a conflict
                if len(capped_at) < 400:
                    capped_at.append([round(e0 + (i + 0.5) * cell, 1), round(n0 + (j + 0.5) * cell, 1), round(float(D[j, i]), 1),
                                      round(lo - base, 2)])
                T[j, i] = base + MAX_FILL
            else:
                held_low += 1
                T[j, i] = lo
        elif base > hi:
            held_high += 1
            T[j, i] = hi
        else:
            T[j, i] = base
    # self-check: the rule between every graded cell and each neighbour graded before it (or a seed)
    worst_fall = worst_rise = 0.0
    rank = np.full((ny, nx), -1, np.int64)
    rank[order[:, 0], order[:, 1]] = np.arange(len(order))
    for r, (j, i) in enumerate(order):
        if conflict[j, i]:
            continue
        for dj, di in nbrs:
            jj, ii = j + dj, i + di
            if (0 <= jj < ny and 0 <= ii < nx and T[jj, ii] == T[jj, ii] and not conflict[jj, ii]
                    and (seed[jj, ii] or 0 <= rank[jj, ii] < r)):
                dist = cell * math.hypot(dj, di)
                g = (T[jj, ii] - T[j, i]) / dist
                worst_fall = max(worst_fall, g)
                worst_rise = max(worst_rise, -g)
    if worst_fall > FALL + 1e-6 or worst_rise > RISE + 1e-6:
        fail(f"the graded grid breaks its own rule: fall {worst_fall:.4f} (max {FALL}), rise {worst_rise:.4f} (max {RISE})")

    def keep_w(x, y):
        """1 = the shoulder applies, 0 = inside a kept patch (grown by its feather), smoothstep over keep_blend_m"""
        w = 1.0
        for _, poly, fe in keep:
            d_ = poly_dist(poly, x, y) - fe
            if d_ <= 0.0:
                return 0.0
            if d_ < KEEP_BLEND:
                w = min(w, smoothstep(d_ / KEEP_BLEND))
        return w

    def L_at(x, y):
        fx, fy = (x - e0) / cell - 0.5, (y - n0) / cell - 0.5
        i, j = int(math.floor(fx)), int(math.floor(fy))
        if i < 0 or j < 0 or i + 1 >= nx or j + 1 >= ny:
            return None
        u, v = fx - i, fy - j
        q = ((Lf[j, i], (1 - u) * (1 - v)), (Lf[j, i + 1], u * (1 - v)), (Lf[j + 1, i], (1 - u) * v), (Lf[j + 1, i + 1], u * v))
        got = [(t, w) for t, w in q if t == t and w > 0]
        sw = sum(w for _, w in got)
        return None if sw < 1e-9 else sum(t * w for t, w in got) / sw

    def T_at(x, y):
        fx, fy = (x - e0) / cell - 0.5, (y - n0) / cell - 0.5
        i, j = int(math.floor(fx)), int(math.floor(fy))
        if i < 0 or j < 0 or i + 1 >= nx or j + 1 >= ny:
            return None
        u, v = fx - i, fy - j
        q = ((T[j, i], (1 - u) * (1 - v)), (T[j, i + 1], u * (1 - v)), (T[j + 1, i], (1 - u) * v), (T[j + 1, i + 1], u * v))
        got = [(t, w) for t, w in q if t == t and w > 0]
        sw = sum(w for _, w in got)
        if sw < 1e-9:
            return None
        return sum(t * w for t, w in got) / sw

    # --- the ground vertices ----------------------------------------------------------------------------------------------
    moved = up = down = 0
    worst_up = worst_down = 0.0
    zone = {"full": 0, "blend": 0}
    big = []
    kept_v = 0
    bad = 0
    for o in ground:
        mw = o.matrix_world
        mi = mw.inverted()
        me = o.data
        for v in me.vertices:
            w_ = mw @ v.co
            co, k, d = kd.find((w_.x, w_.y, 0.0))
            if d <= FROM or d >= TO:
                continue
            if under_road(w_.x, w_.y):
                continue
            t = T_at(w_.x, w_.y)
            if t is None:
                continue
            # the exact cone off the nearest edge point (the grid's 1 m cells let a vertex just past from_m fall a whole
            # cell's fall_max from the shelf it meets over less than a metre of mesh)
            he = pts[k][2] - GROUND_CLEAR
            t = min(max(t, he - FALL * (d - FROM)), he + RISE * (d - FROM))
            if MAX_FILL < math.inf:
                lv = L_at(w_.x, w_.y)
                if lv is not None and t - lv > MAX_FILL:
                    t = lv + MAX_FILL
            wgt = 1.0 if d <= FULL else 1.0 - smoothstep((d - FULL) / (TO - FULL))
            if keep:
                kw = keep_w(w_.x, w_.y)
                if kw <= 0.0:
                    kept_v += 1
                    continue
                wgt *= kw
            dz = (t - w_.z) * wgt
            if abs(dz) < 1e-5:
                continue
            new = Vector((w_.x, w_.y, w_.z + dz))
            v.co = mi @ new
            moved += 1
            zone["full" if d <= FULL else "blend"] += 1
            if abs(dz) > 1.0 and len(big) < 400:
                big.append([round(w_.x, 1), round(w_.y, 1), round(d, 1), round(dz, 2)])
            if dz > 0:
                up += 1
                worst_up = max(worst_up, dz)
            else:
                down += 1
                worst_down = max(worst_down, -dz)
            if d <= FROM + 1e-6:
                bad += 1
        me.update()
    if bad:
        fail(f"{bad} moved vertices within from_m of the edge")
    rep = {"_doc": "ledger 0102: the road shoulder graded onto the lidar ground (tools/shoulder_grade_blend.py)",
           "params": {"from_m": FROM, "full_m": FULL, "to_m": TO, "fall_max": FALL,
                      "max_fill_m": None if MAX_FILL == math.inf else MAX_FILL, "lidar_shift_m": SHIFT,
                      "rise_max": None if RISE == math.inf else RISE, "ground_clear_m": GROUND_CLEAR},
           "edge": {"outer_edges": len(outer), "seam_edges_dropped": seams, "points": len(pts)},
           "grid": {"cells_corridor": int(corr.sum()), "cells_seed": int(seed.sum()), "cells_graded": int(len(order)),
                    "lidar_filled": filled, "held_by_fall": held_low, "capped_fill": capped, "held_by_rise": held_high, "conflicts": conflicts,
                    "no_neighbour": no_nb, "worst_fall_per_m": round(worst_fall, 4), "worst_rise_per_m": round(worst_rise, 4)},
           "keep": {"patches": [k_[0] for k_ in keep], "cells": int(kept.sum()), "vertices_kept": kept_v, "blend_m": KEEP_BLEND},
           "vertices": {"ground_objects": len(ground), "moved": moved, "up": up, "down": down,
                        "largest_up_m": round(worst_up, 3), "largest_down_m": round(worst_down, 3), "by_zone": zone},
           "conflict_cells": conflict_at, "capped_cells": capped_at, "moves_over_1m": big}
    (proj / "data" / "shoulder_grade.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"[shoulder] grid: {rep['grid']}")
    print(f"[shoulder] ground: {rep['vertices']}; {len(big)} moves over 1 m logged")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print(f"[shoulder] saved {blend.name}")


if __name__ == "__main__":      # blender --python runs it as __main__; the tests import the helpers
    main()
