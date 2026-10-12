"""Blender-side probe for tests/tools/test_underlay_blend.py (runs INSIDE Blender, never by the test runner).

    blender --background --python-exit-code 1 --python underlay_probe.py -- <blend> <action> <out.json>

actions (each may be joined with '+', run left to right, then one save if any action edits):
  author    add authored work the underlay must never touch: AUTH_rock (a mesh in collection AUTH_rocks, sharing
            GEN_road_mat), rock_in_auth_coll (no AUTH_ name, protected by its AUTH_ collection), AUTH_inside_gen
            (an AUTH_ object linked INTO GEN_road), AUTH_child_of_road (an empty parented to 1ROAD_road), the GEN
            station marker REF_st_00100 adopted (linked into AUTH_signs and moved), and a
            plain user object Kevin_note (neither GEN nor AUTH) + a scene setting, which a scene reset would lose
  promote   copy 1ROAD_road into AUTH_road as AUTH_road_mine (custom props copied: underlay_role = road)
  foreign   a fresh file whose plain 'Collection' holds an object named 1ROAD_road
  dump      write the state to <out.json>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.blender import underlay as U  # noqa: E402  (guarded: importing runs nothing)


def _coll(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def author():
    me = bpy.data.meshes.new("AUTH_rock_mesh")
    me.from_pydata([(0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 1.5)], [], [(0, 1, 2, 3)])
    mat = bpy.data.materials.get("GEN_road_mat")
    if mat is not None:
        me.materials.append(mat)
    rock = bpy.data.objects.new("AUTH_rock", me)
    rock.location = (12.5, -3.0, 4.0)
    rock["note"] = "Kevin's rock"
    _coll("AUTH_rocks").objects.link(rock)
    me2 = bpy.data.meshes.new("rock2_mesh")
    me2.from_pydata([(5, 5, 0), (6, 5, 0), (6, 6, 0)], [], [(0, 1, 2)])
    r2 = bpy.data.objects.new("rock_in_auth_coll", me2)
    bpy.data.collections["AUTH_rocks"].objects.link(r2)
    ins = bpy.data.objects.new("AUTH_inside_gen", None)
    ins.location = (1, 2, 3)
    bpy.data.collections["GEN_road"].objects.link(ins)
    child = bpy.data.objects.new("AUTH_child_of_road", None)
    child.parent = bpy.data.objects["1ROAD_road"]
    child.location = (7, 8, 9)
    _coll("AUTH_signs").objects.link(child)
    # a station marker Kevin adopted: linked into an AUTH_ collection, it stays in GEN_refs too, and is now his
    bpy.data.collections["AUTH_signs"].objects.link(bpy.data.objects["REF_st_00100"])
    bpy.data.objects["REF_st_00100"].location = (1.0, 1.0, 1.0)
    note = bpy.data.objects.new("Kevin_note", None)
    bpy.context.scene.collection.objects.link(note)
    bpy.context.scene["kevin_setting"] = 42
    return True


def promote():
    src = bpy.data.objects["1ROAD_road"]
    dup = src.copy()
    dup.data = src.data.copy()
    dup.name = "AUTH_road_mine"
    dup.data.name = "AUTH_road_mine_mesh"
    _coll("AUTH_road").objects.link(dup)
    return True


def foreign():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new("x")
    me.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0)], [], [(0, 1, 2)])
    ob = bpy.data.objects.new("1ROAD_road", me)
    _coll("Collection").objects.link(ob)
    return True


def _data_hash(ob):
    h = hashlib.sha256()
    if ob.type == "MESH":
        co = [0.0] * (len(ob.data.vertices) * 3)
        ob.data.vertices.foreach_get("co", co)
        h.update(repr([round(c, 5) for c in co]).encode())
        vi = [0] * len(ob.data.loops)
        ob.data.loops.foreach_get("vertex_index", vi)
        h.update(repr(vi).encode())
    elif ob.type == "CURVE":
        for sp in ob.data.splines:
            p = [0.0] * (len(sp.points) * 4)
            sp.points.foreach_get("co", p)
            h.update(repr([round(c, 5) for c in p]).encode())
    else:
        h.update(repr([round(c, 5) for c in ob.location]).encode())
    return h.hexdigest()[:16]


def dump(out):
    bpy.context.view_layer.update()          # matrix_world of objects made in this session is lazy
    gen = {}
    for cname in U.ud.COLLECTIONS.values():
        c = bpy.data.collections.get(cname)
        if c is None:
            continue
        for ob in c.all_objects:
            if not U.is_protected(ob):
                gen[ob.name] = {"coll": cname, "type": ob.type, "data": _data_hash(ob),
                                "role": ob.get("underlay_role"), "digest": ob.get("underlay_digest"),
                                "parent": ob.parent.name if ob.parent else None}
    up_faces = {}
    for name in ("1ROAD_road", "1RUNOFF_verge", "1GRASS_terrain_placeholder"):
        ob = bpy.data.objects.get(name)
        if ob is not None and ob.type == "MESH":
            ob.data.calc_loop_triangles() if hasattr(ob.data, "calc_loop_triangles") else None
            n = [0.0] * (len(ob.data.polygons) * 3)
            ob.data.polygons.foreach_get("normal", n)
            down = sum(1 for k in range(2, len(n), 3) if n[k] <= 0)
            up_faces[name] = {"faces": len(ob.data.polygons), "down": down}
    state = {
        "auth": U.auth_fingerprint(),
        "gen": gen,
        "objects": sorted(o.name for o in bpy.data.objects),
        "counts": {"meshes": len(bpy.data.meshes), "curves": len(bpy.data.curves),
                   "materials": len(bpy.data.materials), "collections": len(bpy.data.collections)},
        "scene_children": sorted(c.name for c in bpy.context.scene.collection.children),
        "kevin_setting": bpy.context.scene.get("kevin_setting"),
        "kevin_note": "Kevin_note" in bpy.data.objects,
        "up": up_faces,
        "child_world": [round(v, 6) for v in bpy.data.objects["AUTH_child_of_road"].matrix_world.translation]
        if "AUTH_child_of_road" in bpy.data.objects else None,
    }
    Path(out).write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    blend, actions, out = Path(argv[0]), argv[1].split("+"), argv[2]
    if "foreign" not in actions:
        bpy.ops.wm.open_mainfile(filepath=str(blend))
    edited = False
    for a in actions:
        if a == "author":
            edited |= author()
        elif a == "promote":
            edited |= promote()
        elif a == "foreign":
            edited |= foreign()
        elif a == "dump":
            dump(out)
        else:
            raise SystemExit(f"unknown action {a}")
    if edited:
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))


main()
