"""Move the authored rail-like furniture with the ground the prep moved under it (ledger 0082 pass 3, Milford 0.1.8; opt-in:
track.config.json scenery.bespoke.reseat_on_prep true, read by tools/ship_track.sh prep_prep).

Why. tools/author_bespoke_blend.py seats every rail, tyre wall and screen on the AUTHOR scene's ground (loop.blend). The prep
that follows (engine-july's build_kn5_loop) re-conforms the ground near the road: a contact band at the lane edge and a feather
beyond (ledger 0087, 0.1.6). Furniture inside that reach is left where the author put it, so the BUILT ground can rise round
it: on Milford 0.1.5 / 0.1.6 the NW corner's W-beam G1 stood with its rail top a median 0.39 m UNDER the built grass (up to
1.45 m of fill under its SW end), and parts of G2 / G3 showed 0-0.5 m of their 0.70 m (source/furniture/pass3/scripts/
seat_built.py on the gate OBJ). The PC found Pikes Peak's rails buried on banking the same way.

What. Every vertex of every mesh named by PREFIXES moves up or down by (the built ground) - (the author ground) at its own
plan position: the height the author tool gave it over its ground is kept, now over the ground the car sees. "Ground" is the
top of the ground and the edge strip (the author tool seats an over_strip post on the strip's top) under the vertex, read by a
ray cast down from PROBE_UP_M above the vertex, so a deck or a layer far above is never read (L4: a conform pass never
crosses layers). The road is never read: no rail stands on it.

SELF-CHECKS, exit 1 and the blend NOT saved: a vertex with no author or no built ground under it; a move larger than
MAX_MOVE_M (a different layer, L4); a reseated object whose vertex count changed. One line per object (L12).

    blender --background --python-exit-code 1 --python tools/reseat_bespoke_blend.py -- <prepped.blend> --project <proj>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

PREFIXES = ("GUARDRAIL_W", "1WALL_GHOST_RAIL", "1WALL_TECPRO_TYRES", "1WALL_TILTUP_SCREEN")   # the rails kinds' objects
BUILT_GROUND = ("1GRASS", "1KERB")          # the prepped scene's ground and edge strip (the chain's names)
PROBE_UP_M = 6.0                            # [invented] the ray starts this far over the vertex: over any burial seen (1.45 m),
                                            # under any deck (Milford's one underpass is far from every rail)
MIN_MOVE_M = 1e-4                           # under this a vertex is left exactly where it was
MAX_MOVE_M = 3.0                            # [invented] a larger move reads another layer (L4's ~4 m shoulder gap, less a margin)


def bvh(objs):
    verts, polys = [], []
    for o in objs:
        m = o.matrix_world
        off = len(verts)
        verts += [m @ Vector(v.co) for v in o.data.vertices]
        polys += [[off + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys) if polys else None


def down(tree, x, y, z):
    hit = tree.ray_cast(Vector((x, y, z + PROBE_UP_M)), Vector((0.0, 0.0, -1.0)), 2.0 * PROBE_UP_M + 20.0)
    return None if hit[0] is None else float(hit[0].z)


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    blend = Path(a[0])
    proj = Path(a[a.index("--project") + 1])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    spec = (cfg.get("scenery") or {}).get("bespoke") or {}
    if spec.get("reseat_on_prep") is not True:
        print("[reseat] scenery.bespoke.reseat_on_prep not set: nothing to do")
        return
    names = spec.get("names") or {}
    author_prefixes = tuple(names.get("ground", ["1GRASS"])) + tuple(p for p in names.get("track_edge", ["1KERB"]) if p not in ("ROAD", "1ROAD"))
    # the author scene's ground, read from the workshop's loop.blend (what tools/author_bespoke_blend.py seated on)
    with bpy.data.libraries.load(str(proj / "loop.blend"), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.upper().startswith(tuple(p.upper() for p in author_prefixes))]
    author_objs = [o for o in dst.objects if o is not None and o.type == "MESH"]
    author = bvh(author_objs)
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    built = bvh([o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith(BUILT_GROUND)])
    if author is None or built is None:
        raise SystemExit(f"[reseat] FATAL: no author ground ({author_prefixes}) or no built ground ({BUILT_GROUND})")
    bad, rows = [], []
    for o in sorted((o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith(PREFIXES)), key=lambda o: o.name):
        m = o.matrix_world
        up = o.matrix_world.inverted().to_3x3() @ Vector((0.0, 0.0, 1.0))   # world +z in the object's frame
        n0 = len(o.data.vertices)
        touched = False
        moves, missing, cache = [], 0, {}
        for v in o.data.vertices:
            w = m @ Vector(v.co)
            key = (round(w.x, 3), round(w.y, 3))
            if key not in cache:
                ga, gb = down(author, w.x, w.y, w.z), down(built, w.x, w.y, w.z)
                cache[key] = None if ga is None or gb is None else gb - ga
            dz = cache[key]
            if dz is None:
                missing += 1
                continue
            if abs(dz) > MAX_MOVE_M:
                bad.append(f"{o.name}: a vertex at ({w.x:.1f}, {w.y:.1f}) would move {dz:+.2f} m (> {MAX_MOVE_M} m: another layer)")
                break
            moves.append(dz)
            if abs(dz) >= MIN_MOVE_M:            # an unmoved vertex keeps its exact bytes: a round trip through the inverse
                v.co = v.co + up * dz            # matrix perturbs it, and the exporter then splits more vertices (mesh_diff)
                touched = True
        if missing:
            bad.append(f"{o.name}: {missing} of {n0} vertices with no author or built ground under them")
        if len(o.data.vertices) != n0:
            bad.append(f"{o.name}: the vertex count changed")
        if touched:
            o.data.update()
        if moves:
            s = sorted(moves)
            q = lambda f: s[min(len(s) - 1, int(f * (len(s) - 1)))]   # noqa: E731
            rows.append({"object": o.name, "verts": n0, "dz_p5_p50_p95_m": [round(q(0.05), 3), round(q(0.5), 3), round(q(0.95), 3)],
                         "dz_min_max_m": [round(s[0], 3), round(s[-1], 3)], "moved_over_1cm": sum(abs(d) > 0.01 for d in moves)})
            print(f"[reseat] {o.name:28s} {n0:6d} verts  dz p5/p50/p95 {rows[-1]['dz_p5_p50_p95_m']}  min/max {rows[-1]['dz_min_max_m']}  "
                  f"moved > 1 cm {rows[-1]['moved_over_1cm']}")
    (proj / "data" / "reseat_bespoke.json").write_text(json.dumps({"ok": not bad, "bad": bad, "objects": rows}, indent=1) + "\n",
                                                       encoding="utf-8")
    if bad:
        for b in bad:
            print("[reseat] FAIL " + b)
        raise SystemExit(1)
    bpy.ops.wm.save_mainfile(filepath=str(blend))
    print(f"[reseat] {len(rows)} objects moved with the prepped ground; saved {blend.name}")


main()
