"""Read-only scene diagnosis for the held north reference; NEVER saves the blend.

Run with pinned Blender, opening loop.blend, then --python this-file. Output is under build/phase2.
This judges the actual authored scene, NOT the exported KN5 and not a substitute for artifact gates.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "build/phase2/north-rehearsal"
RAY_DOWN_M = 4.0
RAY_LEN_M = 60.0


def surface(objects):
    vertices, polygons, owners = [], [], []
    for ob in objects:
        first = len(vertices)
        vertices.extend(ob.matrix_world @ v.co for v in ob.data.vertices)
        polygons.extend(tuple(first + i for i in p.vertices) for p in ob.data.polygons)
        owners.extend([ob.name] * len(ob.data.polygons))
    return BVHTree.FromPolygons(vertices, polygons), owners


def cast(tree, owners, x, y, z):
    loc, _normal, face, _distance = tree.ray_cast(Vector((x, z, y - RAY_DOWN_M)),
                                                Vector((0, 0, 1)), RAY_LEN_M)
    return None if loc is None else {"y": round(loc.z, 4), "object": owners[face]}


def main():
    scene = Path(bpy.data.filepath)
    before = hashlib.sha256(scene.read_bytes()).hexdigest()
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    roads = [o for o in meshes if o.name == "ROAD" or o.name.upper().startswith("1ROAD")]
    road, names = surface(roads)
    old, old_names = surface([bpy.data.objects["ROAD"]])
    rec = json.loads((OUT / "data/lap.north.json").read_text())
    pts, widths, sources = rec["points_xyz_m"], rec["widths_m"], rec["source_by_vertex"]
    m = len(pts) - 1
    rows, summaries = [], []
    for j, join in enumerate(rec["joins"]):
        ks = [k for k, src in enumerate(sources[:m]) if src == ["join", j]]
        samples = []
        for k in ks:
            p, a, b = pts[k], pts[(k - 1) % m], pts[(k + 1) % m]
            tx, tz = b[0] - a[0], b[2] - a[2]
            length = math.hypot(tx, tz)
            nx, nz = -tz / length, tx / length
            for f in (-1, -0.5, 0, 0.5, 1):
                off = f * (widths[k] / 2 - 0.82)  # existing barrier face inset, not a new gate
                x, z = p[0] + nx * off, p[2] + nz * off
                hit = cast(road, names, x, p[1], z)
                old_y = cast(old, old_names, x, p[1], z)
                samples.append({"vertex": k, "fraction_left": f, "xz": [round(x, 4), round(z, 4)],
                                "road": hit, "old_road_only_hit": old_y is not None})
        summaries.append({"join": j, "from": join["from"], "to": join["to"], "samples": len(samples),
                          "road_missing": sum(s["road"] is None for s in samples),
                          "centre_missing": sum(s["road"] is None and s["fraction_left"] == 0 for s in samples),
                          "old_road_only_missing": sum(not s["old_road_only_hit"] for s in samples)})
        rows.append({"join": j, "samples": samples})
    # The full-width Navajo start area: car centres, not clearance/timing proofs.
    spawns = {}
    for lid in ("north_cw", "north_acw"):
        ds = json.loads((OUT / f"data/dummies_{lid}.json").read_text())
        spawns[lid] = {name: cast(road, names, p[0], p[1], p[2]) for name, p in ds.items()
                       if name.startswith(("AC_START_", "AC_PIT_", "AC_HOTLAP_"))}
    report = {"evidence": "authored Blender scene only; not exported-artifact gates", "scene_sha256": before,
              "blender": bpy.app.version_string, "road_objects": [o.name for o in roads],
              "joins": summaries, "samples": rows, "spawn_centres": spawns,
              "scene_unchanged": before == hashlib.sha256(scene.read_bytes()).hexdigest()}
    (OUT / "scene-probe.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("evidence", "scene_sha256", "road_objects", "joins", "scene_unchanged")}, indent=2))
    print("SPAWN CENTRES", {lid: {"count": len(s), "missing": sum(h is None for h in s.values())}
                            for lid, s in spawns.items()})
    assert report["scene_unchanged"], "scene changed during read-only diagnosis"


if __name__ == "__main__":
    main()
