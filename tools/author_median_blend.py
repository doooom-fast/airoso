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

STREET-ONLY ISLAND (ledger 0055): where track.config.json race.chicanes declares a street-only span
(scripts/geometry/race_chicane.street_only_spans — the Speedways cross the road there), the mainline island's
curb and barrier over that span are authored as their OWN objects, STREET_CURB_OBJECT / STREET_RAIL_OBJECT (their
names carry race_chicane.STREET_TAG; the prep keeps their AC names, tools/split_exports_blend.py routes them to
<slug>_street.kn5, which only the street layout loads). The island stays ONE island in the street layout: the pieces
share their cut rings, no nose at a cut; each piece left in the road kn5 is capped at the cut (a race layout meets a
closed island end there). The grass deck stays in TERRAIN (the prep pins it under the road: no race-lane effect); no
shrub is planted over the span (they become TreeFX, which is track-wide — a race lane crosses there).

Local frame is x=east, y=up, z=north; the blend is Blender Z-up via the (x, z, y) remap —
apply the same remap here (LAWS L6: it is a reflection; wind faces deliberately).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy

SHRUB_EVERY_M = 3.2


def _load(name, rel):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# the island's own shape (its ring, deck, beam and posts, and the numbers they stand on) is ONE rule, tools/median_island.py,
# shared with tools/author_median_rebuild_blend.py since ledger 0099 round 3: this file lays the islands out, the rule
# shapes them. tests/tools/test_median_island_rule.py holds this tool's output to the checksums taken before the lift.
_MI = _load("_median_island_med", "tools/median_island.py")
LIFT, CURB_H, LIP_IN, DECK_INSET = _MI.LIFT, _MI.CURB_H, _MI.LIP_IN, _MI.DECK_INSET
NOSE_HALF, NOSE_VERTS, BARRIER_MIN_M = _MI.NOSE_HALF, _MI.NOSE_VERTS, _MI.BARRIER_MIN_M
STREET_CURB_OBJECT = "1KERB_sidewalk_streetonly_median"   # the street-only island's curb (same surface + texture key)
STREET_RAIL_OBJECT = "1WALL_guard_streetonly_median"      # ...and its centre barrier


def _race_chicane():
    return _load("_race_chicane_med", "scripts/geometry/race_chicane.py")


_RC = _race_chicane()


def pieces(i, j, spans):
    """race_chicane.island_pieces (pure, tested there)"""
    return _RC.island_pieces(i, j, spans)


B = _MI.B
_tangent = _MI.tangent
_segments = _MI.segments


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
    bands = json.loads((data / "median_bands.json").read_text(encoding="utf-8"))
    main_pts = [tuple(p) for p in local["points_xyz_m"]]
    main_iw = bands["island_w_by_vertex"]
    if len(main_iw) != len(main_pts):
        raise SystemExit(f"[median-blend] vertex count mismatch: bands {len(main_iw)} vs centerline {len(main_pts)}")
    # islands to author: the mainline's, plus divided connectors' (tools/divide_connectors.py)
    islands = [("mainline", main_pts, main_iw)]
    for ci in bands.get("connector_islands", []):
        islands.append((ci["name"], [tuple(p) for p in ci["points_xyz_m"]], ci["island_w_by_point"]))

    curbV, curbF, deckV, deckF = [], [], [], []
    railV, railF, shrubV, shrubF = [], [], [], []
    rng_state = 12345

    def rnd():
        nonlocal rng_state
        rng_state = (rng_state * 1103515245 + 12345) & 0x7FFFFFFF
        return rng_state / 0x7FFFFFFF

    total_len = 0.0
    segs = []
    for name, pts, iw in islands:
        segs += [(name, pts, iw, i, j) for (i, j) in _segments(iw)]
    # ledger 0055: the mainline island's street-only spans (race.chicanes) — their curb and barrier go to the
    # STREET_* objects; everything else exactly as before
    cfg_p = proj / "track.config.json"
    cfg = json.loads(cfg_p.read_text(encoding="utf-8")) if cfg_p.exists() else {}
    street_spans = _race_chicane().street_only_spans(cfg)
    scV, scF, srV, srF = [], [], [], []
    n_street_rings = 0

    def in_street(name, k):
        return name == "mainline" and any(a <= k <= b for a, b in street_spans)

    for (_name, pts, iw, i, j) in segs:
        deck_start = len(deckV)
        ks = list(range(i, j))
        seg_len = _MI.seg_length(pts, i, j)
        total_len += seg_len
        # per-station rings (tools/median_island.py: the curb ring's six vertices and the deck's two, nose-tapered)
        rings = []
        for k in ks:
            curb_ring, deck_pair = _MI.ring(pts, iw, i, j, k)
            rings.append(curb_ring)
            deckV += deck_pair
        # faces between rings (bands: 0-1 sideL, 1-2 lipL, 3-4 lipR, 4-5 sideR; deck separate)
        for si in range(len(ks) - 1):
            deckF.append(_MI.deck_face(deck_start + si * 2))
        # the curb, piece by piece (one piece unless a street-only span cuts the segment): each piece's own rings,
        # the cut ring in both pieces; end caps at the segment's real ends, and on a ROAD piece at a cut (the island
        # end a race layout meets) — a street piece is never capped at a cut (it closes onto the road piece's ring)
        spans_here = street_spans if _name == "mainline" else []
        for a_k, b_k, street in pieces(i, j, spans_here):
            V, F = (scV, scF) if street else (curbV, curbF)
            base = len(V)
            for k in range(a_k, b_k + 1):
                V += rings[k - i]
            if street:
                n_street_rings += b_k - a_k + 1
            for si in range(b_k - a_k):
                F += _MI.curb_span_faces(base + si * 6)
            if a_k == i or not street:
                F += _MI.curb_start_cap(base)
            if b_k == j - 1 or not street:
                F += _MI.curb_end_cap(base + (b_k - a_k) * 6)

        # shrubs/planting: cross-quads along the deck — placed within the NOSE-TAPERED half-width,
        # not the data width (the first build put 16 bushes on the pavement beside the noses:
        # drive_test obstruction stations 3204-3206 / 3771-3773, 2026-10-08)
        dist = 0.0
        for si in range(1, len(ks) - 1):
            k = ks[si]
            dist += math.hypot(pts[k][0] - pts[k - 1][0], pts[k][2] - pts[k - 1][2])
            half_here = _MI.half_width(iw, i, j, k)
            if dist < SHRUB_EVERY_M or half_here < 1.1:
                continue
            dist = 0.0
            tx, tz = _tangent(pts, k)
            lx, lz = -tz, tx
            off = (rnd() - 0.5) * max(0.2, 2.0 * half_here - 1.6)
            h = 0.35 + rnd() * 0.35
            w = 0.5 + rnd() * 0.4
            cx = pts[k][0] + lx * off
            cy = pts[k][1] + LIFT + CURB_H
            cz = pts[k][2] + lz * off
            if in_street(_name, k):
                continue          # no planting on a street-only island (the draws above keep every other shrub's place)
            for (dx, dz) in ((tx, tz), (lx, lz)):
                s = len(shrubV)
                shrubV += [B((cx - dx * w, cy, cz - dz * w)), B((cx + dx * w, cy, cz + dz * w)),
                           B((cx + dx * w, cy + h, cz + dz * w)), B((cx - dx * w, cy + h, cz - dz * w))]
                shrubF.append((s, s + 1, s + 2, s + 3))

        # barrier on long segments: center box beam + posts
        if seg_len >= BARRIER_MIN_M:
            bks = _MI.beam_points(i, j)
            # the beam piece by piece like the curb (a street-only piece shares its cut ring with the road piece)
            for a_k, b_k, street in pieces(bks[0], bks[-1] + 1, spans_here) if bks else []:
                V, F = (srV, srF) if street else (railV, railF)
                beam_start = len(V)
                for k in range(a_k, b_k + 1):
                    V += _MI.beam_ring(pts, k)
                for si in range(b_k - a_k):
                    F += _MI.beam_span_faces(beam_start + si * 4)
            # posts every ~8 m
            for k in _MI.post_points(pts, bks):
                V, F = (srV, srF) if in_street(_name, k) else (railV, railF)
                s = len(V)
                pv, pf = _MI.post(pts, k)
                V += pv
                F += [tuple(s + q for q in f) for f in pf]

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
    # ledger 0055: the street-only island pieces, standalone (their names route them to <slug>_street.kn5)
    for name, verts, faces in ((STREET_CURB_OBJECT, scV, scF), (STREET_RAIL_OBJECT, srV, srF)):
        old = bpy.data.objects.get(name)
        if old is not None:
            bpy.data.objects.remove(old, do_unlink=True)
        if verts:
            ob = _mk(name, verts, faces)
            print(f"[median-blend] {name}: {len(ob.data.vertices)} verts (street-only island over "
                  f"{[list(s) for s in street_spans]}, {n_street_rings} rings)")
    if street_spans and not scV:
        raise SystemExit(f"[median-blend] FATAL: street-only spans {street_spans} declared but no island stands there")
    for name in ("CURB", "TERRAIN", "GUARDRAIL", "SCRUB"):
        ob = bpy.data.objects.get(name)
        if ob:
            nv = len(ob.data.vertices)
            flag = "  <-- OVER 65,535 CAP" if nv > 65535 else ""
            print(f"[median-blend] {name}: {nv} verts{flag}")

    bpy.ops.wm.save_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[median-blend] saved {proj / 'loop.blend'}")


main()
