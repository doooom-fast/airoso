"""scripts/blender/underlay.py — the data underlay (fleet/REALISM.md §4; V3-PLAN P2 step 3).

Without Blender: the OBJ reading, the frame remap (the prep's own: (x, y, z) -> (x, z, y), faces re-wound), the
GEN_ collection of every AC prefix, the plan a project yields, and the refusals (no track.obj = not ready).
With the ``bpy`` module importable (Blender 4.2 as a pip module, or inside Blender): the whole build, twice —
the second run after an AUTH_* object was added by hand — proving the collection contract: GEN_* replaced,
AUTH_* untouched, the scene never reset, and the written objects named exactly as the prep expects.

Plain ``test_*`` for tests/run_tests.py (no pytest fixtures).
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.blender import underlay as U

OBJ = """# a tiny engine draft: a 20 m road quad, a grass quad under it, a kerb, a wall, a painted line
o 1ROAD_road_0
v 0 10.0 0
v 8 10.0 0
v 8 10.2 20
v 0 10.2 20
vt 0 0
vt 1 0
vt 1 1
vt 0 1
f 1/1 2/2 3/3
f 1/1 3/3 4/4
o 1GRASS_0
v -20 9.5 -20
v 30 9.5 -20
v 30 9.5 40
v -20 9.5 40
f 5 6 7
f 5 7 8
o 1KERB_race_0
v 8 10.0 0
v 8.3 10.1 0
v 8.3 10.1 20
f 9 10 11
o 1WALL_barrier_0
v -1 10 0
v -1 11 0
v -1 11 20
f 12 13 14
o YLINE
v 4 10.01 0
v 4.1 10.01 0
v 4.1 10.01 20
f 15 16 17
o EMPTY_GROUP
"""
CL = {"points_xyz_m": [[4, 10.0, 0], [4, 10.05, 5], [4, 10.1, 10], [4, 10.15, 15], [4, 10.2, 20]], "widths_m": [8] * 5}


def _project(d: Path, *, loop=False) -> Path:
    (d / "data").mkdir(parents=True)
    (d / "track.config.json").write_text(json.dumps({"slug": "sq", "name": "sq", "version": "0.0.1", "loop": loop,
                                                     "layouts": [{"id": "full"}]}), encoding="utf-8")
    (d / "data" / "track.obj").write_text(OBJ, encoding="utf-8")
    (d / "data" / "centerline.local.json").write_text(json.dumps(CL), encoding="utf-8")
    return d


def test_collection_for_every_ac_prefix():
    assert U.collection_for("1ROAD_road_3") == "GEN_road"
    assert U.collection_for("1ROAD_shoulder") == "GEN_road"
    assert U.collection_for("1RUNOFF_corners") == "GEN_road", "paved run-off is a drivable surface"
    assert U.collection_for("1KERB_sidewalk_1") == "GEN_kerb"
    assert U.collection_for("1GRASS_12") == "GEN_terrain"
    assert U.collection_for("GRASS_FAR") == "GEN_terrain"
    for n in ("1WALL_barrier", "BARRIER_warning", "RETWALL_face", "ROCKCUT_face", "1WALL_CHAINL_warn"):
        assert U.collection_for(n) == "GEN_wall", n
    for n in ("YLINE", "ROADTEXT", "MARKINGS_2", "anything"):
        assert U.collection_for(n) == "GEN_misc", n
    assert set(U.COLLECTIONS) >= {U.collection_for(n) for n in ("1ROAD", "1KERB", "1GRASS", "1WALL", "x")}


def test_parse_obj_and_the_preps_frame():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.obj"
        p.write_text(OBJ, encoding="utf-8")
        verts, uvs, groups = U.parse_obj(p)
    assert len(verts) == 17 and len(uvs) == 4
    assert [g[0] for g in groups] == ["1ROAD_road_0", "1GRASS_0", "1KERB_race_0", "1WALL_barrier_0", "YLINE", "EMPTY_GROUP"]
    assert groups[-1][1] == [], "an 'o' with no faces is an empty group, skipped later"
    # the road: two triangles with UVs, in the prep's frame (local E,up,N -> Blender E,N,up), re-wound
    bverts, bfaces, buvs, has_uv = U.group_to_mesh(verts, uvs, groups[0][1])
    assert has_uv and len(bverts) == 4 and len(bfaces) == 2
    assert bverts[0] == (0.0, 0.0, 10.0) and bverts[2] == (8.0, 20.0, 10.2)       # (x, y, z) -> (x, z, y)
    assert bfaces[0] == (2, 1, 0), "winding reversed to cancel the reflection"
    assert buvs[2] == (1.0, 1.0)
    # a group without UVs gets none claimed
    _, _, _, has_uv2 = U.group_to_mesh(verts, uvs, groups[1][1])
    assert has_uv2 is False
    assert U.to_blender((1.0, 2.0, 3.0)) == (1.0, 3.0, 2.0)


def test_plan_lists_every_group_once_with_its_collection_and_refuses_an_unready_project():
    with tempfile.TemporaryDirectory() as td:
        d = _project(Path(td) / "p")
        p = U.plan(d)
        names = [g["name"] for g in p["groups"]]
        assert names == ["1ROAD_road_0", "1GRASS_0", "1KERB_race_0", "1WALL_barrier_0", "YLINE"], names
        assert {g["name"]: g["collection"] for g in p["groups"]}["1WALL_barrier_0"] == "GEN_wall"
        assert p["groups"][0] == {"name": "1ROAD_road_0", "collection": "GEN_road", "verts": 4, "faces": 2}
        assert p["collections"] == ["GEN_kerb", "GEN_misc", "GEN_road", "GEN_terrain", "GEN_wall"]
        assert p["refs"] == {"points": 5, "stations": 1, "closed": False}
        assert p["obj_md5"] == U.md5_of(d / "data" / "track.obj") and p["slug"] == "sq"
        (d / "data" / "track.obj").unlink()
        try:
            U.plan(d)
            raise AssertionError("a project with no track.obj must be refused")
        except SystemExit as e:
            assert "track.obj" in str(e) and "build_mesh" in str(e)
        empty = Path(td) / "e"
        empty.mkdir()
        try:
            U.plan(empty)
            raise AssertionError("no config must be refused")
        except SystemExit as e:
            assert "track.config.json" in str(e)


def test_station_points_every_500_m_plus_the_start():
    pts = [[0, 0, 0], [0, 0, 700], [0, 0, 1300]]
    st = U._station_points(pts, 500.0)
    assert [s for s, _ in st] == [0.0, 500.0, 1000.0]
    assert st[1][1] == (0.0, 0.0, 500.0) and st[2][1] == (0.0, 0.0, 1000.0)


def test_main_plan_flag_needs_no_blender(capsys=None):
    with tempfile.TemporaryDirectory() as td:
        d = _project(Path(td) / "p")
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = U.main(["underlay.py", "--", str(d), "--plan"])
        assert rc == 0
        out = json.loads(buf.getvalue())
        assert out["source_obj"] == "data/track.obj" and len(out["groups"]) == 5


def test_build_twice_keeps_auth_and_replaces_gen():
    try:
        import bpy
    except ImportError:
        print("  (no bpy module here — the Blender-side build is exercised on a machine with Blender)")
        return
    with tempfile.TemporaryDirectory() as td:
        d = _project(Path(td) / "p", loop=True)
        r1 = U.build(d)
        assert r1["existed"] is False and r1["gen_removed"] == [] and r1["auth_untouched"] == []
        assert [g["name"] for g in r1["groups"]] == ["1ROAD_road_0", "1GRASS_0", "1KERB_race_0", "1WALL_barrier_0", "YLINE"]
        assert (d / "loop.blend").is_file() and (d / "data" / U.REPORT).is_file()
        assert r1["refs"] == 2, "the centreline curve + REF_start (the lap is 20 m, no 500 m station)"
        # the written scene: objects named exactly as the prep expects, each in its GEN_ collection, refs non-mesh
        bpy.ops.wm.open_mainfile(filepath=str(d / "loop.blend"))
        names = {o.name: [c.name for c in o.users_collection] for o in bpy.data.objects}
        assert names["1ROAD_road_0"] == ["GEN_road"] and names["1GRASS_0"] == ["GEN_terrain"]
        assert names["1KERB_race_0"] == ["GEN_kerb"] and names["1WALL_barrier_0"] == ["GEN_wall"] and names["YLINE"] == ["GEN_misc"]
        assert names["REF_centreline"] == ["GEN_refs"] and names["REF_start"] == ["GEN_refs"]
        assert bpy.data.objects["REF_centreline"].type == "CURVE" and bpy.data.objects["REF_start"].type == "EMPTY"
        road = bpy.data.objects["1ROAD_road_0"]
        assert len(road.data.vertices) == 4 and len(road.data.polygons) == 2 and road.data.uv_layers
        assert tuple(round(c, 3) for c in road.data.vertices[2].co) == (8.0, 20.0, 10.2)
        assert bpy.data.objects["REF_centreline"].data.splines[0].use_cyclic_u is True
        # an author adds a hand-shaped object in an AUTH_ collection, and edits a GEN_ one
        auth = bpy.data.collections.new("AUTH_bridge")
        bpy.context.scene.collection.children.link(auth)
        me = bpy.data.meshes.new("AUTH_deck")
        me.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0)], [], [(0, 1, 2)])
        auth.objects.link(bpy.data.objects.new("AUTH_deck", me))
        bpy.data.objects["1ROAD_road_0"].data.vertices[0].co.z += 5.0
        bpy.ops.wm.save_as_mainfile(filepath=str(d / "loop.blend"))
        # the engine re-drafts: a changed OBJ comes through, the authored object stays, the hand edit to GEN_ is replaced
        obj = d / "data" / "track.obj"
        obj.write_text(obj.read_text(encoding="utf-8").replace("v 8 10.2 20", "v 8 10.6 20"), encoding="utf-8")
        r2 = U.build(d)
        assert r2["existed"] is True
        assert sorted(r2["gen_removed"]) == sorted(["1ROAD_road_0", "1GRASS_0", "1KERB_race_0", "1WALL_barrier_0", "YLINE",
                                                    "REF_centreline", "REF_start"])
        assert r2["auth_untouched"] == ["AUTH_deck"]
        bpy.ops.wm.open_mainfile(filepath=str(d / "loop.blend"))
        assert "AUTH_deck" in bpy.data.objects and bpy.data.objects["AUTH_deck"].users_collection[0].name == "AUTH_bridge"
        road = bpy.data.objects["1ROAD_road_0"]
        assert tuple(round(c, 3) for c in road.data.vertices[2].co) == (8.0, 20.0, 10.6), "the new draft, not the hand edit"
        assert tuple(round(c, 3) for c in road.data.vertices[0].co) == (0.0, 0.0, 10.0)
        assert len([c for c in bpy.data.collections if c.name.startswith("GEN_")]) == len(U.COLLECTIONS)
        assert len([o for o in bpy.data.objects if o.name.startswith("1ROAD")]) == 1, "no duplicate GEN objects on a re-run"
        rep = json.loads((d / "data" / U.REPORT).read_text(encoding="utf-8"))
        assert rep["obj_md5"] == U.md5_of(obj) and rep["auth_untouched"] == ["AUTH_deck"]
