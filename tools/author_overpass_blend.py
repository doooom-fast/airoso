"""Write the C-470 bridges (data/overpass_decks.json, tools/overpass_decks.py) into loop.blend as AUTH_overpass_*.

Lookout Lariat V3-PLAN P3a ``overpass_decks`` (D5), ledger 0048. Scenery only: no digit prefix, so the prep and the
exporter give them a plain material and no physics, and no gate reads them as road. Each deck is a closed box
(top, underside, both faces, end caps) along its OSM bridge way at the measured width and DECK_DEPTH_M; each pier a
closed box from 1 m under the 3DEP ground to the deck's underside.

The tool owns exactly the objects it writes: everything in collection ``AUTH_overpass`` whose name starts with
``AUTH_overpass_`` and carries the custom property ``overpass_gen``. A re-run replaces those (idempotent) and touches
nothing else; the underlay never touches AUTH_* (REALISM §4), so the two never fight.

    blender --background --python-exit-code 1 --python tools/author_overpass_blend.py -- <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy  # noqa: provided by Blender
import bmesh  # noqa: provided by Blender

COLL = "AUTH_overpass"
PREFIX = "AUTH_overpass_"


def log(m):
    print(f"[overpass] {m}", flush=True)


def _box_strip(line, width, depth):
    """vertices (Blender frame) + quads of a closed box swept along line [(x, y_top, z_north), ...]"""
    n = len(line)
    verts, faces = [], []
    for i, (x, y, zn) in enumerate(line):
        a = line[max(0, i - 1)]
        b = line[min(n - 1, i + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / L, tx / L
        h = width / 2.0
        for side in (1, -1):
            for top in (True, False):
                verts.append((x + side * nx * h, zn + side * nz * h, y if top else y - depth))
    # per section: 0 = left top, 1 = left bottom, 2 = right top, 3 = right bottom
    for i in range(n - 1):
        a, b = 4 * i, 4 * (i + 1)
        faces += [(a + 0, a + 2, b + 2, b + 0),      # top
                  (a + 1, b + 1, b + 3, a + 3),      # underside
                  (a + 0, b + 0, b + 1, a + 1),      # left face
                  (a + 2, a + 3, b + 3, b + 2)]      # right face
    e = 4 * (n - 1)
    faces += [(0, 1, 3, 2), (e + 0, e + 2, e + 3, e + 1)]
    return verts, faces


def _pier(x, y0, zn, y1, s):
    h = s / 2.0
    verts = [(x - h, zn - h, y0), (x + h, zn - h, y0), (x + h, zn + h, y0), (x - h, zn + h, y0),
             (x - h, zn - h, y1), (x + h, zn - h, y1), (x + h, zn + h, y1), (x - h, zn + h, y1)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return verts, faces


def _mesh(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)     # closed boxes: outward
    bm.to_mesh(me)
    bm.free()
    me.update()
    return me


def main():
    rest = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(rest) != 1:
        raise SystemExit("[overpass] usage: blender ... --python tools/author_overpass_blend.py -- <project-dir>")
    proj = Path(rest[0]).resolve()
    spec_p = proj / "data" / "overpass_decks.json"
    blend = proj / "loop.blend"
    if not spec_p.is_file() or not blend.is_file():
        raise SystemExit(f"[overpass] missing {spec_p if not spec_p.is_file() else blend}")
    spec = json.loads(spec_p.read_text(encoding="utf-8"))
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    coll = bpy.data.collections.get(COLL)
    if coll is None:
        coll = bpy.data.collections.new(COLL)
        bpy.context.scene.collection.children.link(coll)
    removed = 0
    for ob in list(coll.objects):
        if ob.name.startswith(PREFIX) and ob.get("overpass_gen"):
            data = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if data is not None and data.users == 0:
                bpy.data.meshes.remove(data)
            removed += 1
    made = 0
    for d in spec["decks"]:
        line = [(p[0], p[1], p[2]) for p in d["line_xyz_ground"]]
        v, f = _box_strip(line, float(d["width_m"]), float(d["depth_m"]))
        parts = [(d["name"], v, f)]
        for k, (x, y0, zn, y1) in enumerate(d["piers"]):
            pv, pf = _pier(x, y0, zn, y1, spec["params"]["PIER_SIZE_M"])
            parts.append((f"{d['name']}_pier{k:02d}", pv, pf))
        for name, v, f in parts:
            if bpy.data.objects.get(name) is not None:
                raise SystemExit(f"[overpass] REFUSED: {name} exists and is not this tool's (no overpass_gen)")
            ob = bpy.data.objects.new(name, _mesh(name, v, f))
            ob["overpass_gen"] = "tools/author_overpass_blend.py"
            ob["overpass_way"] = int(d["way"])
            ob["overpass_clearance_m"] = d["clearance_over_lap_m"] if d["clearance_over_lap_m"] is not None else -1.0
            coll.objects.link(ob)
            made += 1
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    log(f"{made} objects written ({len(spec['decks'])} decks + piers), {removed} of its own replaced -> {blend}")


if __name__ == "__main__":
    main()
