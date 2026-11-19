"""Author measured road paint on a street's built road (ledger 0079 round N; opt-in, Sand Creek's paint step).

Kevin, 2026-11-03: "I just want real". Lake Murray's assembler paints every street from its own centreline (a double
yellow down the middle, white edges and dividers by width; tracks/san-diego-lake-murray/scripts-v021, which no other
track may change). Where NAIP shows paint the assembler cannot draw — fork 94/95's painted median, a second yellow
line diverging from the street's centre line — this step paints it where it was measured, AFTER the weld, draped on
the welded road:

  track.config.json route.paint = [{
      "id": "fork_95_median",
      "lines": [{"pts": [[x, z], ...],      # the measured line, local x, z (track frame), end to end
                 "color": "yellow",          # "yellow" -> object YLINE_paint_<id>, "white" -> MARKINGS_paint_<id>
                 "w": 0.12,                  # one stripe's width (m)
                 "double_gap_m": 0.06}],     # optional: two stripes this far apart (a double line)
      "clear": [[x, z], ...],                # optional: a polygon; the assembler's paint faces (YLINE* / MARKINGS*)
      "surface": ["PADAPRON"],               # optional (ledger 0093): drape on these mesh-name prefixes, not on ROAD
  }, ...]                                    # whose centre lies inside it are removed (paint NAIP does not show)

Ledger 0093 (High Plains' race furniture; every key opt-in, an item without them is painted exactly as before):
  * a line may be declared in lon/lat ("pts_lonlat"), as grid marks ("dots_lonlat" + "size_m") or as a gore hatch
    ("hatch": {"polygon_lonlat", "spacing_m", "angle_deg", "outline"}); tools/paint_shapes.py expands them to plain lines
    on data/centerline.local.json's origin and tangents;
  * "surface": paint that lies on the bespoke dressing (the pit lane's PADAPRON sheets) drapes on those meshes. They exist
    only after tools/author_bespoke_blend.py, so the chain paints in two passes: `--stage draft` (tools/ship_track.sh
    draft_paint) paints the items with no surface (on ROAD), `--stage author` (author_paint, after author_bespoke) the items
    with one. No --stage = every item, each on its own surface.

Each line is resampled every PAINT_DS_M along its length; each stripe's two edge points read the surface's top
(a ray down through it) and stand PAINT_LIFT_M over it — Lake Murray's own connector paint height over its deck
(scripts-v021 build_loop_blend: +0.115 on points carrying the 0.10 deck lift). Visual only (no digit prefix): the prep
binds YLINE / MARKINGS by name and turns the faces up. No physics, no gate surface.

Self-check, exit 1 and loop.blend not saved: a line with fewer than 2 points; a stripe point with no surface under it; a
painted vertex not PAINT_LIFT_M over the surface it was read from (re-read after the build, 1 mm).

No route.paint = no-op (Lake Murray and the Lariat name none).

    blender --background --python tools/author_paint_blend.py -- <project-dir> [--stage draft|author]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paint_shapes  # noqa: E402

PAINT_LIFT_M = 0.015        # Lake Murray's connector paint over its deck (0.115 - the 0.10 deck lift)
PAINT_DS_M = 0.5            # [invented] resample step along a painted line (drapes it on the built road)
PREFIX = {"yellow": "YLINE_paint_", "white": "MARKINGS_paint_"}
STAGES = ("draft", "author")


def road_bvh():
    ob = bpy.data.objects.get("ROAD")
    if ob is None:
        raise SystemExit("[paint] FATAL: no ROAD object in loop.blend")
    mw = ob.matrix_world
    me = ob.data
    return BVHTree.FromPolygons([mw @ v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons])


def surface_bvh(prefixes, pid):
    """(ledger 0093) every mesh whose name starts with one of ``prefixes`` (case-blind), world space"""
    pre = tuple(str(p).upper() for p in prefixes)
    verts, polys = [], []
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.name.upper().startswith(pre) or ob.name.startswith(tuple(PREFIX.values())):
            continue
        mw = ob.matrix_world
        off = len(verts)
        verts += [mw @ v.co for v in ob.data.vertices]
        polys += [tuple(off + i for i in p.vertices) for p in ob.data.polygons]
    if not polys:
        raise SystemExit(f"[paint] FATAL: {pid}: no {list(prefixes)} mesh in loop.blend to drape on; not saved")
    return BVHTree.FromPolygons(verts, polys)


def road_top(bvh, x, z):
    """the built ROAD's top at local (x, z): Blender (X, Y, Z) = local (x, z, y)"""
    hit = bvh.ray_cast((x, z, 1.0e4), (0.0, 0.0, -1.0), 2.0e4)
    return None if hit[0] is None else hit[0].z


def inside(poly, x, z):
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, zi = poly[i]
        xj, zj = poly[j]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi) + xi:
            c = not c
        j = i
    return c


def clear(poly, pid):
    """remove the assembler's paint faces whose centre lies inside the polygon; returns {object: faces removed}"""
    out = {}
    for ob in list(bpy.data.objects):
        if ob.type != "MESH" or not ob.name.upper().startswith(("YLINE", "MARKINGS")) or ob.name.startswith(
                tuple(PREFIX.values())):
            continue
        mw = ob.matrix_world
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bad = []
        for f in bm.faces:
            c = mw @ f.calc_center_median()
            if inside(poly, c.x, c.y):
                bad.append(f)
        if bad:
            bmesh.ops.delete(bm, geom=bad, context="FACES")
            bm.to_mesh(ob.data)
            ob.data.update()
            out[ob.name] = len(bad)
        bm.free()
    print(f"[paint] {pid}: cleared {sum(out.values())} assembler paint faces inside the measured polygon {out}")
    return out


def resample(pts, ds):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(math.ceil(L / ds)))
        for k in range(1, n + 1):
            t = k / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def stripes(line):
    w = float(line.get("w", 0.12))
    g = line.get("double_gap_m")
    if g is None:
        return [(-w / 2.0, w / 2.0)]
    g = float(g)
    return [(-g / 2.0 - w, -g / 2.0), (g / 2.0, g / 2.0 + w)]


def paint(bvh, item, lines=None, surface="ROAD"):
    pid = item["id"]
    verts, faces, made = [], [], []
    for li, line in enumerate((item.get("lines") or []) if lines is None else lines):
        pts = [(float(p[0]), float(p[1])) for p in line["pts"]]
        if len(pts) < 2:
            raise SystemExit(f"[paint] FATAL: {pid} line {li}: fewer than 2 points; loop.blend not saved")
        P = resample(pts, PAINT_DS_M)
        for lo, hi in stripes(line):
            base = len(verts)
            for k, (x, z) in enumerate(P):
                a, b = P[max(0, k - 1)], P[min(len(P) - 1, k + 1)]
                tx, tz = b[0] - a[0], b[1] - a[1]
                L = math.hypot(tx, tz) or 1e-9
                nx, nz = -tz / L, tx / L
                for o in (lo, hi):
                    px, pz = x + nx * o, z + nz * o
                    y = road_top(bvh, px, pz)
                    if y is None:
                        raise SystemExit(f"[paint] FATAL: {pid} line {li}: no {surface} under ({px:.2f}, {pz:.2f}); "
                                         "loop.blend not saved")
                    verts.append((px, pz, y + PAINT_LIFT_M))
            for k in range(len(P) - 1):
                i0 = base + 2 * k
                faces.append((i0, i0 + 1, i0 + 3, i0 + 2))
        L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
        made.append((line.get("color", "yellow"), L, len(stripes(line))))
    colors = {m[0] for m in made}
    if len(colors) != 1 or next(iter(colors)) not in PREFIX:
        raise SystemExit(f"[paint] FATAL: {pid}: one colour per paint item (yellow / white); got {sorted(colors)}")
    name = PREFIX[next(iter(colors))] + pid
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    for p in me.polygons:
        if p.normal.z < 0:
            p.flip()
    me.update()
    ob = bpy.data.objects.new(name, me)
    road = bpy.data.objects.get("ROAD")
    for c in (road.users_collection if road is not None else [bpy.context.scene.collection]):
        c.objects.link(ob)
    worst = 0.0
    for v in verts:
        y = road_top(bvh, v[0], v[1])
        worst = max(worst, abs((v[2] - y) - PAINT_LIFT_M))
    if worst > 0.001:
        raise SystemExit(f"[paint] FATAL: {pid}: paint {worst * 1000:.1f} mm off its lift over the road; not saved")
    if lines is None or len(made) <= 6:
        print(f"[paint] {name}: " + ", ".join(f"{c} {L:.1f} m x {n} stripe(s)" for c, L, n in made)
              + f" ({len(faces)} quads, {PAINT_LIFT_M} m over the built {surface}, read-back {worst * 1000:.2f} mm)")
    else:
        print(f"[paint] {name}: {len(made)} {next(iter(colors))} lines, {sum(m[1] for m in made):.1f} m in all "
              f"({len(faces)} quads, {PAINT_LIFT_M} m over the built {surface}, read-back {worst * 1000:.2f} mm)")
    return ob


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    proj = Path(argv[0])
    stage = argv[argv.index("--stage") + 1] if "--stage" in argv else None
    if stage is not None and stage not in STAGES:
        raise SystemExit(f"[paint] FATAL: --stage {stage!r} (one of {list(STAGES)})")
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    items = (cfg.get("route") or {}).get("paint") or []
    if stage == "draft":
        items = [it for it in items if not it.get("surface")]
    elif stage == "author":
        items = [it for it in items if it.get("surface")]
    if not items:
        print(f"[paint] no route.paint{'' if stage is None else ' item for the ' + stage + ' stage'}: nothing to do")
        return
    local = None
    if any(paint_shapes.needs_line(it) for it in items):
        local = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    bvh = road_bvh() if any(not it.get("surface") for it in items) else None
    for item in items:
        for pre in PREFIX.values():
            old = bpy.data.objects.get(pre + item["id"])
            if old is not None:
                bpy.data.objects.remove(old, do_unlink=True)
        if item.get("clear"):
            clear([(float(p[0]), float(p[1])) for p in item["clear"]], item["id"])
        surf = item.get("surface")
        if isinstance(surf, str):
            surf = [surf]
        tree = surface_bvh(surf, item["id"]) if surf else bvh
        if paint_shapes.needs_line(item):
            lines = paint_shapes.expand(item, local["origin"], local["points_xyz_m"])
            paint(tree, item, lines, surface="+".join(surf) if surf else "ROAD")
        else:
            paint(tree, item, surface="+".join(surf) if surf else "ROAD")
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))
    print(f"[paint] {len(items)} paint item(s) authored{'' if stage is None else ' (' + stage + ' stage)'}; saved loop.blend")


main()
