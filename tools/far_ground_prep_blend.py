"""The sunk skirt out of the prepped ground tiles (ledger 0082 "Far ground (0.1.11)"; tools/far_ground_blend.py's opt-in
"object" mode). The draft left TERRAIN's topology as the assembler made it, its skirt SUNK (every floor vertex at one height,
data/far_ground.report.json object.skirt_sunk_z), so engine-july's prep tiled and welded the ground exactly as before; here,
on the prepped scene, every 1GRASS tile face with a vertex at that height goes (and the vertices left on no face), so the
shipped ground past the grid is the far ground's own object alone. Nothing else moves: the remaining faces keep their vertices'
exact positions.

Opt-in: terrain.far_ground.object in track.config.json (none = no-op, the blend not saved). Self-check (exit 1, not saved): the
faces taken out must be exactly the report's skirt_faces (each triangulated skirt quad is two), none of them inside the grid's
box, and no vertex of the far ground's object at that height. Writes data/far_ground.prep.json.

    blender --background --python-exit-code 1 --python tools/far_ground_prep_blend.py -- <blender/<slug>.blend> --project <dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bmesh
import bpy

TOL_Z = 0.01


def fail(msg):
    print(f"[far-ground-prep] FATAL: {msg}; the blend not saved")
    raise SystemExit(1)


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    blend, proj = Path(a[0]), Path(a[a.index("--project") + 1])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    spec = (cfg.get("terrain") or {}).get("far_ground") or {}
    name = spec.get("object")
    if not name:
        print("[far-ground-prep] no terrain.far_ground.object: nothing to do")
        return
    rep = json.loads((proj / "data" / "far_ground.report.json").read_text(encoding="utf-8"))
    zs = float(rep["object"]["skirt_sunk_z"])
    want = int(rep["object"]["skirt_faces"])
    x0, y0, x1, y1 = rep["grid"]["bbox_xy"]
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    ring = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith(name.upper())]
    if not ring:
        fail(f"no {name}* object in the prepped scene")
    for o in ring:
        if any((o.matrix_world @ v.co).z < zs + TOL_Z for v in o.data.vertices):
            fail(f"{o.name} has a vertex at the sunk skirt's height")
    tiles = [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith("1GRASS") and o not in ring]
    gone, per = 0, {}
    for o in tiles:
        m = o.matrix_world
        bm = bmesh.new()
        bm.from_mesh(o.data)
        low = {v for v in bm.verts if (m @ v.co).z < zs + TOL_Z}
        if not low:
            bm.free()
            continue
        faces = [f for f in bm.faces if any(v in low for v in f.verts)]
        for f in faces:
            c = m @ f.calc_center_median()
            if x0 < c.x < x1 and y0 < c.y < y1:
                fail(f"{o.name}: a sunk-skirt face centred inside the grid's box ({c.x:.1f}, {c.y:.1f})")
        n0 = len(bm.verts)
        bmesh.ops.delete(bm, geom=faces, context="FACES_ONLY")
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(o.data)
        o.data.update()
        bm.free()
        gone += len(faces)
        per[o.name] = {"faces": len(faces), "verts_out": n0 - len(o.data.vertices)}
    if gone != want:
        fail(f"{gone} sunk-skirt faces found in the tiles, the draft sank {want}")
    (proj / "data" / "far_ground.prep.json").write_text(json.dumps({"skirt_sunk_z": zs, "faces_out": gone, "tiles": per},
                                                                   indent=1) + "\n", encoding="utf-8")
    bpy.ops.wm.save_mainfile(filepath=str(blend))
    by_tile = ", ".join(f"{k} {v['faces']}" for k, v in sorted(per.items()))
    rings = ", ".join(o.name for o in ring)
    print(f"[far-ground-prep] the sunk skirt out of the prepped ground: {gone} faces from {len(per)} tiles ({by_tile}); "
          f"the far ground {rings} stands alone past the grid; saved {blend.name}")


main()
