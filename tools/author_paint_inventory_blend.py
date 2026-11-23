"""Paint a track's road from its surveyed paint inventory, and from nothing else (Denver Grand Prix PLAN 4b item 10;
ledger 0096; opt-in, the chain's author step ``paint_inventory``).

Kevin, 2026-11-23: "Same with road paint, we do a terrible job currently." Until now the road was painted by rule: the
assembler's double yellow, edge lines and dividers by width (scripts-v021 ribbon.lane_markings), the weld's connector
paint, and measured exceptions declared by hand (route.paint). A track that names a paint inventory,

    track.config.json  "inventory": {"paint": {"file": "source/survey/paint.json", "build_grades": ["measured"]}}

is painted here instead, item by item, in the survey pilot's schema (tools/inventory.py reads it):

  1. every paint object the inventory did not author is removed from loop.blend (YLINE*, MARKINGS*, ROADTEXT*, minus
     inventory.paint.keep_prefixes: a race layout's start line and grid are declared additions). The prep does the same
     again before the export (scripts/ac/build_kn5_loop.py drop_bywidth_paint), so paint a later step lays is gone too;
  2. every item of a built grade is draped on the BUILT road: the lap's ribbon and every junction pad alike, any mesh
     whose name starts with one of inventory.paint.surfaces (default ROAD, 1ROAD), 15 mm over it, as
     tools/author_paint_blend.py drapes route.paint (tools/paint_shapes.drape, clip = true: a stripe is painted only
     where the road is);
  3. the result is AUTH_paint_inventory: MARKINGS_inv_<n> (white) and YLINE_inv_<n> (yellow), rebuilt from scratch
     every run. Visual only (no digit prefix).

Written beside it: data/paint_inventory.json (what was built, what was held out by grade, every item with length that
found no road under it). Nothing is inferred between marks and nothing is filled in: an item of a built grade that
cannot be built as read (a symbol whose type was not read) stops the step.

Self-check, exit 1 and loop.blend not saved: no road mesh to drape on; an unbuildable item of a built grade; a painted
vertex not 15 mm over the road it was read from (re-read after the build, 1 mm); nothing painted at all.

Not judged here: whether the paint is RIGHT. That is tools/inventory_gate.py, on the built kn5 (LAWS L5).

No inventory.paint = no-op (every track but one that opts in).

    blender --background --python tools/author_paint_inventory_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inventory as INV  # noqa: E402
import paint_shapes  # noqa: E402

PAINT_LIFT_M = 0.015        # tools/author_paint_blend.PAINT_LIFT_M: Lake Murray's connector paint over its deck
PAINT_DS_M = 0.5            # tools/author_paint_blend.PAINT_DS_M [invented]: the drape's step along a stripe
COLLECTION = "AUTH_paint_inventory"
SURFACES = ("ROAD", "1ROAD")
PAINT_CLASS = INV.MESH_PREFIXES["paint"]
CHUNK_VERTS = 40000         # one object stays far under AC's 65,535 per mesh after the prep


def is_bywidth_paint(name: str, keep=()) -> bool:
    """scripts/ac/build_kn5_loop.is_bywidth_paint, restated (Blender's python loads this tool bare)"""
    up = str(name).upper()
    if not up.startswith(PAINT_CLASS) or up.startswith(tuple(p.upper() for p in INV.INVENTORY_PAINT.values())):
        return False
    return not up.startswith(tuple(str(k).upper() for k in keep if str(k)))


def surface_bvh(prefixes):
    pre = tuple(str(p).upper() for p in prefixes)
    verts, polys, names = [], [], []
    for ob in bpy.data.objects:
        up = ob.name.upper()
        if ob.type != "MESH" or not up.startswith(pre) or up.startswith(PAINT_CLASS):
            continue
        mw = ob.matrix_world
        off = len(verts)
        verts += [mw @ v.co for v in ob.data.vertices]
        polys += [tuple(off + i for i in p.vertices) for p in ob.data.polygons]
        names.append(ob.name)
    if not polys:
        raise SystemExit(f"[paint-inventory] FATAL: no {list(prefixes)} mesh in loop.blend to drape on; not saved")
    return BVHTree.FromPolygons(verts, polys), names


def top(bvh, x, z):
    """the built road's top at local (x, z): Blender (X, Y, Z) = local (x, z, y)"""
    hit = bvh.ray_cast((x, z, 1.0e4), (0.0, 0.0, -1.0), 2.0e4)
    return None if hit[0] is None else hit[0].z


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    proj = Path(argv[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    ccfg = INV.class_cfg(cfg, "paint")
    if ccfg is None:
        print("[paint-inventory] no track.config.json inventory.paint: nothing to do")
        return
    try:
        inv = INV.load_class(proj, cfg, "paint", INV.origin_of(proj))
        grades = INV.build_grades(ccfg)
    except INV.InventoryError as e:
        raise SystemExit(f"[paint-inventory] FATAL: {e}; not saved")
    stuck = INV.unbuildable(inv, grades)
    if stuck:
        raise SystemExit(f"[paint-inventory] FATAL: {len(stuck)} item(s) of a built grade cannot be built as read "
                         f"({', '.join(f'{it.id}: {it.why_not}' for it in stuck[:5])}); give each a shape or take its "
                         "grade out of inventory.paint.build_grades; not saved")
    built = inv.built()
    if not built:
        raise SystemExit(f"[paint-inventory] FATAL: {ccfg['file']} holds no item of a built grade {list(grades)}; not saved")

    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    keep = ccfg.get("keep_prefixes") or ()
    old = bpy.data.collections.get(COLLECTION)
    if old is not None:
        for ob in list(old.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(old)
    for ob in [o for o in bpy.data.objects if o.type == "MESH"
               and o.name.upper().startswith(tuple(p.upper() for p in INV.INVENTORY_PAINT.values()))]:
        bpy.data.objects.remove(ob, do_unlink=True)
    gone = [o.name for o in bpy.data.objects if o.type == "MESH" and is_bywidth_paint(o.name, keep)]
    for n in gone:
        bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    print(f"[paint-inventory] removed {len(gone)} paint object(s) the inventory did not author {sorted(gone)[:8]}"
          + (f"; kept the declared additions {list(keep)}" if keep else ""))

    bvh, surf_names = surface_bvh(ccfg.get("surfaces") or SURFACES)
    by_colour = {c: [] for c in INV.INVENTORY_PAINT}          # colour -> [(verts, faces)] chunks
    off_road, length = [], {c: 0.0 for c in INV.INVENTORY_PAINT}
    n_painted = 0
    for it in built:
        lines = [{**s, "color": it.colour} for s in it.strokes]
        verts, faces, made, clipped = paint_shapes.drape(lines, lambda x, z: top(bvh, x, z), PAINT_DS_M, PAINT_LIFT_M,
                                                         clip=True)
        drawn = sum(m[1] for m in made)
        if clipped > 1e-6:
            off_road.append({"id": it.id, "painted_m": round(drawn, 2), "no_road_under_m": round(clipped, 2)})
        if not faces:
            continue
        n_painted += 1
        length[it.colour] += drawn
        chunks = by_colour[it.colour]
        if not chunks or len(chunks[-1][0]) + len(verts) > CHUNK_VERTS:
            chunks.append(([], []))
        cv, cf = chunks[-1]
        base = len(cv)
        cv += verts
        cf += [tuple(base + i for i in f) for f in faces]
    if not n_painted:
        raise SystemExit("[paint-inventory] FATAL: no item has road under it (is the inventory in this track's frame? "
                         f"origin {INV.origin_of(proj)}); not saved")

    col = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(col)
    worst, objects = 0.0, []
    for colour, chunks in by_colour.items():
        for k, (verts, faces) in enumerate(chunks):
            name = f"{INV.INVENTORY_PAINT[colour]}{k:03d}"
            me = bpy.data.meshes.new(name)
            me.from_pydata(verts, [], faces)
            me.validate()
            for p in me.polygons:
                if p.normal.z < 0:
                    p.flip()
            me.update()
            col.objects.link(bpy.data.objects.new(name, me))
            objects.append(name)
            for v in verts:
                y = top(bvh, v[0], v[1])
                worst = max(worst, 1.0 if y is None else abs((v[2] - y) - PAINT_LIFT_M))
    if worst > 0.001:
        raise SystemExit(f"[paint-inventory] FATAL: paint {worst * 1000:.1f} mm off its lift over the road; not saved")

    held = {}
    for it in inv.items:
        if not it.built:
            held[it.why_not] = held.get(it.why_not, 0) + 1
    report = {"inventory": ccfg["file"], "build_grades": list(grades), "grades": inv.grade_shares(),
              "items_built": len(built), "items_painted": n_painted, "held_out": held, "not_items": inv.not_items,
              "painted_m": {c: round(v, 1) for c, v in length.items()}, "objects": objects, "surfaces": sorted(surf_names),
              "removed_not_from_the_inventory": sorted(gone), "kept_additions": list(keep),
              "no_road_under": off_road, "lift_m": PAINT_LIFT_M, "read_back_mm": round(worst * 1000, 3)}
    (proj / "data").mkdir(exist_ok=True)
    (proj / "data" / "paint_inventory.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[paint-inventory] {n_painted} of {len(built)} built-grade items painted on {len(surf_names)} road mesh(es): "
          f"white {length['white']:.1f} m, yellow {length['yellow']:.1f} m of stripe in {len(objects)} object(s); "
          f"{len(off_road)} item(s) with length off the built road; held out {held or 'none'}; "
          f"read-back {worst * 1000:.2f} mm; saved loop.blend")


main()
