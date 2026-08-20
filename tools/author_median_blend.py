"""Author the raised median island into loop.blend — the rt_macau pattern (docs/JUNCTIONS.md):
one continuous pavement slab, median standing ON it as a raised landscaped island.

Run AFTER build_loop_blend (which regenerates the scene) and BEFORE the kn5 prep:

    blender --background --python tools/author_median_blend.py -- <project-dir>

Reads data/centerline.local.json (smoothed, median-shifted by tools/median_envelope.py) and
data/median_bands.json. Joins geometry into EXISTING objects so it inherits their material,
texture, rename and physics paths untouched:
  island curb faces + noses -> CURB      (-> 1KERB_sidewalk, collidable curb)
  island top deck           -> TERRAIN   (-> 1GRASS, the track's green-turf override: grass median)
  metal barrier + posts     -> GUARDRAIL (-> 1WALL_guard, collidable)
  shrub/planting clumps     -> SCRUB     (visual scenery)

Kevin (2026-08-20, ledger 0037): the real medians carry "flowers and barriers... grass etc...
shrubs". Flowers proper need a texture pass (parked); v1 = grass deck + shrub clumps + barriers.

Local frame is x=east, y=up, z=north; the blend is Blender Z-up via the (x, z, y) remap —
apply the same remap here (LAWS L6: it is a reflection; wind faces deliberately).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy

LIFT = 0.10          # road ribbon rides +0.10 above the local y (build_loop_blend's lift)
CURB_H = 0.18
LIP_IN = 0.15        # curb top inward batter
DECK_INSET = 0.22
NOSE_HALF = 0.25     # island end tapers to this half-width
NOSE_VERTS = 3
SHRUB_EVERY_M = 3.2
BARRIER_MIN_M = 120.0


def B(p):
    """local (x, y_up, z_north) -> blender (x, z_north, y_up)"""
    return (p[0], p[2], p[1])


def _tangent(pts, k):
    a, b = pts[max(0, k - 1)], pts[min(len(pts) - 1, k + 1)]
    dx, dz = b[0] - a[0], b[2] - a[2]
    d = math.hypot(dx, dz) or 1.0
    return dx / d, dz / d


def _segments(island_w):
    segs, i, n = [], 0, len(island_w)
    while i < n:
        if island_w[i] <= 0:
            i += 1
            continue
        j = i
        while j < n and island_w[j] > 0:
            j += 1
        if j - i >= 6:
            segs.append((i, j))
        i = j
    return segs


def _mk(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _join_into(target_name, ob):
    tgt = bpy.data.objects.get(target_name)
    if tgt is None:
        print(f"[median-blend] WARNING: no object '{target_name}' — leaving {ob.name} standalone")
        return
    bpy.ops.object.select_all(action='DESELECT')
    tgt.select_set(True)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = tgt
    bpy.ops.object.join()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    data = proj / "data"
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))

    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in local["points_xyz_m"]]
    bands = json.loads((data / "median_bands.json").read_text(encoding="utf-8"))
    iw = bands["island_w_by_vertex"]
    if len(iw) != len(pts):
        raise SystemExit(f"[median-blend] vertex count mismatch: bands {len(iw)} vs centerline {len(pts)}")

    segs = _segments(iw)
    curbV, curbF, deckV, deckF = [], [], [], []
    railV, railF, shrubV, shrubF = [], [], [], []
    rng_state = 12345

    def rnd():
        nonlocal rng_state
        rng_state = (rng_state * 1103515245 + 12345) & 0x7FFFFFFF
        return rng_state / 0x7FFFFFFF

    total_len = 0.0
    for (i, j) in segs:
        ring_start = len(curbV)
        deck_start = len(deckV)
        ks = list(range(i, j))
        seg_len = sum(math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][2] - pts[k][2])
                      for k in ks[:-1])
        total_len += seg_len
        # per-station rings
        for si, k in enumerate(ks):
            half = iw[k] / 2.0
            # nose taper at both ends
            if si < NOSE_VERTS:
                half = NOSE_HALF + (half - NOSE_HALF) * si / NOSE_VERTS
            if (len(ks) - 1 - si) < NOSE_VERTS:
                half = NOSE_HALF + (half - NOSE_HALF) * (len(ks) - 1 - si) / NOSE_VERTS
            tx, tz = _tangent(pts, k)
            lx, lz = -tz, tx
            cx, cy, cz = pts[k][0], pts[k][1] + LIFT, pts[k][2]

            def P(off, dy):
                return B((cx + lx * off, cy + dy, cz + lz * off))

            # ring: Lbase LtopO LtopI RtopI RtopO Rbase
            curbV += [P(-half, -0.02), P(-half + 0.04, CURB_H), P(-half + LIP_IN, CURB_H),
                      P(half - LIP_IN, CURB_H), P(half - 0.04, CURB_H), P(half, -0.02)]
            di = max(0.05, half - DECK_INSET)
            deckV += [P(-di, CURB_H + 0.005), P(di, CURB_H + 0.005)]
        # faces between rings (bands: 0-1 sideL, 1-2 lipL, 3-4 lipR, 4-5 sideR; deck separate)
        for si in range(len(ks) - 1):
            a = ring_start + si * 6
            b = a + 6
            for (p, q) in ((0, 1), (1, 2), (3, 4), (4, 5)):
                curbF.append((a + p, a + q, b + q, b + p))
            d = deck_start + si * 2
            deckF.append((d, d + 1, d + 3, d + 2))
        # end caps
        a = ring_start
        curbF.append((a + 0, a + 1, a + 2, a + 3))
        curbF.append((a + 0, a + 3, a + 4, a + 5))
        z = ring_start + (len(ks) - 1) * 6
        curbF.append((z + 3, z + 2, z + 1, z + 0))
        curbF.append((z + 5, z + 4, z + 3, z + 0))

        # shrubs/planting: cross-quads along the deck
        dist = 0.0
        for si in range(1, len(ks) - 1):
            k = ks[si]
            dist += math.hypot(pts[k][0] - pts[k - 1][0], pts[k][2] - pts[k - 1][2])
            if dist < SHRUB_EVERY_M or iw[k] < 2.2:
                continue
            dist = 0.0
            tx, tz = _tangent(pts, k)
            lx, lz = -tz, tx
            off = (rnd() - 0.5) * max(0.2, iw[k] - 1.6)
            h = 0.35 + rnd() * 0.35
            w = 0.5 + rnd() * 0.4
            cx = pts[k][0] + lx * off
            cy = pts[k][1] + LIFT + CURB_H
            cz = pts[k][2] + lz * off
            for (dx, dz) in ((tx, tz), (lx, lz)):
                s = len(shrubV)
                shrubV += [B((cx - dx * w, cy, cz - dz * w)), B((cx + dx * w, cy, cz + dz * w)),
                           B((cx + dx * w, cy + h, cz + dz * w)), B((cx - dx * w, cy + h, cz - dz * w))]
                shrubF.append((s, s + 1, s + 2, s + 3))

        # barrier on long segments: center box beam + posts
        if seg_len >= BARRIER_MIN_M:
            beam_start = len(railV)
            for k in ks[NOSE_VERTS:len(ks) - NOSE_VERTS]:
                tx, tz = _tangent(pts, k)
                lx, lz = -tz, tx
                cx, cz = pts[k][0], pts[k][2]
                yb = pts[k][1] + LIFT + CURB_H
                for off, dy in ((-0.12, 0.45), (-0.12, 0.75), (0.12, 0.75), (0.12, 0.45)):
                    railV.append(B((cx + lx * off, yb + dy, cz + lz * off)))
            nk = len(ks) - 2 * NOSE_VERTS
            for si in range(nk - 1):
                a = beam_start + si * 4
                b = a + 4
                for (p, q) in ((0, 1), (1, 2), (2, 3), (3, 0)):
                    railF.append((a + p, a + q, b + q, b + p))
            # posts every ~8 m
            dist = 0.0
            for k in ks[NOSE_VERTS:len(ks) - NOSE_VERTS]:
                dist += math.hypot(pts[k][0] - pts[k - 1][0], pts[k][2] - pts[k - 1][2])
                if dist < 8.0:
                    continue
                dist = 0.0
                cx, cz, yb = pts[k][0], pts[k][2], pts[k][1] + LIFT + CURB_H
                s = len(railV)
                for (ox, oz) in ((-0.06, -0.06), (0.06, -0.06), (0.06, 0.06), (-0.06, 0.06)):
                    railV.append(B((cx + ox, yb, cz + oz)))
                    railV.append(B((cx + ox, yb + 0.45, cz + oz)))
                for (p, q) in ((0, 2), (2, 4), (4, 6), (6, 0)):
                    railF.append((s + p, s + q, s + q + 1, s + p + 1))

    print(f"[median-blend] {len(segs)} island segment(s), {total_len:.0f} m total; "
          f"curb {len(curbV)}v, deck {len(deckV)}v, rail {len(railV)}v, shrubs {len(shrubV)}v")
    for name, verts, faces, target in (("MEDIAN_CURB", curbV, curbF, "CURB"),
                                       ("MEDIAN_DECK", deckV, deckF, "TERRAIN"),
                                       ("MEDIAN_RAIL", railV, railF, "GUARDRAIL"),
                                       ("MEDIAN_SHRUB", shrubV, shrubF, "SCRUB")):
        if not verts:
            continue
        ob = _mk(name, verts, faces)
        _join_into(target, ob)
    for name in ("CURB", "TERRAIN", "GUARDRAIL", "SCRUB"):
        ob = bpy.data.objects.get(name)
        if ob:
            nv = len(ob.data.vertices)
            flag = "  <-- OVER 65,535 CAP" if nv > 65535 else ""
            print(f"[median-blend] {name}: {nv} verts{flag}")

    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[median-blend] saved {proj / 'loop.blend'}")


main()
