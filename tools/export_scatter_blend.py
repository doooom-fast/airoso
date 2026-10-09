"""Export the positions of every procedural palm, shade tree, scrub bush and median plant from
loop.blend — so real TreeFX models can stand exactly where the draft put them.

Kevin (2026-10-08, seat): "let's start replacing the trees and lamps. They're pretty trash right
now." The assembler's palm.scatter / scenery.scatter return meshes, not coordinates, and the
assembler is quarantined; the allowed route is a post-hoc read of the built scene. Each plant is
a connected island of its merged mesh (PALMTRUNK_A/B cylinders, TREETRUNK cylinders, SCRUB blobs,
and author_median_blend's 4-vert cross-quads for island planting), so island-walk each object and
record base (min y), height and centroid.

Runs INSIDE Blender, after gap_mouths_blend and BEFORE strip_scenery_blend / the kn5 prep:

    blender --background --python tools/export_scatter_blend.py -- <project-dir>

Writes data/scatter_positions.json in the ENGINE frame (x = E, y = up, z = N; the TreeFX
emitter negates z for the kn5 world). Deterministic: the scatter functions use index hashes, so
positions are stable for an unchanged centreline.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy


def islands(me):
    """connected components over edges -> list of vertex-index lists"""
    n = len(me.vertices)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for e in me.edges:
        a, b = e.vertices
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def summarize(me, vids):
    xs = [me.vertices[i].co.x for i in vids]
    ys = [me.vertices[i].co.y for i in vids]   # Blender y = local z (north)
    zs = [me.vertices[i].co.z for i in vids]   # Blender z = local y (up)
    # local frame: x=E, y=up, z=N  <- Blender (x, z, y)
    return {"x": round(sum(xs) / len(xs), 3), "z": round(sum(ys) / len(ys), 3),
            "y": round(min(zs), 3), "height": round(max(zs) - min(zs), 2), "verts": len(vids)}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    proj = Path(argv[0])
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    out = {"palms": [], "trees": [], "scrub": [], "median_planting": []}
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        name = ob.name.upper()
        if name.startswith("PALMTRUNK"):
            key = "palms"
        elif name == "TREETRUNK":
            key = "trees"
        elif name == "SCRUB":
            key = "scrub"
        else:
            continue
        for vids in islands(ob.data):
            s = summarize(ob.data, vids)
            if key == "scrub" and s["verts"] <= 4:
                out["median_planting"].append(s)    # author_median_blend's cross-quads
            else:
                out[key].append(s)
    # a cross-quad plant is two 4-vert quads sharing no vertices -> two islands at one spot; keep one
    seen, dedup = set(), []
    for e in out["median_planting"]:
        key = (round(e["x"] / 0.3), round(e["z"] / 0.3))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(e)
    out["median_planting"] = dedup
    (proj / "data" / "scatter_positions.json").write_text(json.dumps(out), encoding="utf-8")
    print(f"[scatter] palms {len(out['palms'])}, trees {len(out['trees'])}, scrub {len(out['scrub'])}, "
          f"median planting {len(out['median_planting'])} -> data/scatter_positions.json")


main()
