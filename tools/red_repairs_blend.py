"""Apply data/red_repairs.plan.json (tools/red_repairs.py) to the prepped scene, before the split (ledger 0065).

Kerbs: every face touching a named K / I / F vertex goes: a sidewalk standing in a carriageway, stranding pavement, or hanging clear of
both road and ground. Ground: inside S_REACH_M of a named ground-on-top place, a 1GRASS vertex at or above the pavement within S_RING_M of it
drops to S_UNDER_M below that pavement. Nothing else moves. Exit 1, blend not saved, when a named kerb vertex is not found or a ground move
exceeds S_MOVE_MAX_M: the plan then belongs to another build.

    blender --background --python-exit-code 1 --python tools/red_repairs_blend.py -- <prepped.blend> --project <project-dir>
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

MATCH_M = 0.03          # [invented] a gate OBJ vertex is written at 6 decimals of a kn5 float: this finds it in the scene
S_REACH_M = 45.0        # [invented] the ground-on-top stations run in clusters; this covers a cluster and its lane edges
S_RING_M = 1.5          # [invented] past the pavement edge, so a triangle off the bank cannot rise over the lip
S_UNDER_M = 0.05        # the prep's own contact clearance
S_MOVE_MAX_M = 1.5      # [invented] a bigger move is not a repair of a sliver

argv = sys.argv[sys.argv.index("--") + 1:]
blend, proj = argv[0], Path(argv[argv.index("--project") + 1])
plan = json.loads((proj / "data" / "red_repairs.plan.json").read_text(encoding="utf-8"))
bpy.ops.wm.open_mainfile(filepath=blend)

# --- kerbs -----------------------------------------------------------------------------------------------------------------
want = {}
for row in plan["K"] + plan["I"] + plan["F"]:
    x, y, z = row[:3]
    want[(round(x, 3), round(z, 3), round(y, 3))] = (x, z, y)       # engine (E, up, N) -> scene (E, N, up)
cell = {}
for key, p in want.items():
    cell.setdefault((int(p[0] // 1.0), int(p[1] // 1.0)), []).append((key, p))
found, faces_gone = set(), 0
for ob in [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith("1KERB")]:
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    doomed = set()
    for v in bm.verts:
        c = (int(v.co.x // 1.0), int(v.co.y // 1.0))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for key, p in cell.get((c[0] + dx, c[1] + dy), ()):
                    if (v.co - Vector(p)).length <= MATCH_M:
                        found.add(key)
                        doomed.update(v.link_faces)
    if doomed:
        faces_gone += len(doomed)
        bmesh.ops.delete(bm, geom=list(doomed), context="FACES")
        bm.to_mesh(ob.data)
        print(f"[red] {ob.name}: {len(doomed)} kerb faces removed")
    bm.free()
missing = sorted(set(want) - found)
if missing:
    raise SystemExit(f"[red] {len(missing)} of {len(want)} named kerb vertices not in this scene, e.g. {missing[:3]}: the plan is another build's")

# --- ground ----------------------------------------------------------------------------------------------------------------
road_v, road_f = [], []
for ob in bpy.data.objects:
    if ob.type == "MESH" and ob.name.upper().startswith("1ROAD") and "SHOULDER" not in ob.name.upper():
        base = len(road_v)
        road_v += [ob.matrix_world @ v.co for v in ob.data.vertices]
        road_f += [[base + i for i in p.vertices] for p in ob.data.polygons]
road = BVHTree.FromPolygons(road_v, road_f)
RING = [(0.0, 0.0)] + [(S_RING_M * math.cos(a * math.pi / 4), S_RING_M * math.sin(a * math.pi / 4)) for a in range(8)]
spots = [(s["x"], s["z"], s["y"]) for s in plan["S_spots"]]
moved, worst = 0, 0.0
for ob in [o for o in bpy.data.objects if o.type == "MESH" and o.name.upper().startswith("1GRASS")]:
    changed = False
    for v in ob.data.vertices:
        if not any(math.hypot(v.co.x - sx, v.co.y - sy) <= S_REACH_M and abs(v.co.z - sz) < 12.0 for sx, sy, sz in spots):
            continue
        decks = []
        for dx, dy in RING:
            hit = road.ray_cast(Vector((v.co.x + dx, v.co.y + dy, v.co.z + 6.0)), Vector((0, 0, -1)), 12.0)
            if hit[0] is not None:
                decks.append(hit[0].z)
        if not decks:
            continue
        deck = min(decks)
        if v.co.z > deck - S_UNDER_M + 1e-4:
            move = v.co.z - (deck - S_UNDER_M)
            worst = max(worst, move)
            v.co.z = deck - S_UNDER_M
            moved += 1
            changed = True
    if changed:
        ob.data.update()
if worst > S_MOVE_MAX_M:
    raise SystemExit(f"[red] a ground vertex would move {worst:.2f} m (limit {S_MOVE_MAX_M}): not a sliver, look at it")
print(f"[red] {len(found)} named kerb vertices, {faces_gone} kerb faces removed; {moved} ground vertices lowered at {len(spots)} places, worst {worst:.3f} m")
bpy.ops.wm.save_as_mainfile(filepath=blend, copy=False)
