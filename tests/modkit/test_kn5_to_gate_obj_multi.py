"""scripts/modkit/kn5_to_gate_obj.py — several kn5s into ONE gate OBJ (ledger 0047).

A race layout loads the road kn5 AND the race-furniture kn5, so its gates must read one OBJ
holding both. OBJ face indices are global: the second file's faces must be offset by the first
file's vertex count, and the single-file output must be unchanged. The fixture is the synthetic
200 m straight (tests/geometry/test_drive_test._project) written to a real kn5 by the engine's
native writer, then loaded twice as "road" + "race".
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from tests.geometry.test_drive_test import _project

from scripts.ac.kn5_write import build
from scripts.modkit import kn5_to_gate_obj as g


def _obj_stats(path: Path):
    verts = faces = 0
    groups = []
    max_idx = 0
    for ln in path.read_text(encoding="ascii").splitlines():
        if ln.startswith("v "):
            verts += 1
        elif ln.startswith("f "):
            faces += 1
            max_idx = max(max_idx, *(int(t) for t in ln.split()[1:4]))
        elif ln.startswith("o "):
            groups.append(ln[2:])
    return verts, faces, groups, max_idx


def test_two_kn5s_concatenate_with_a_global_vertex_offset():
    d = _project()
    road = build(d)                                   # build/t.kn5
    race = road.with_name("t_race.kn5")
    shutil.copyfile(road, race)
    single = d / "data" / "single.obj"
    both = d / "data" / "track.race.obj"
    s1 = g.kn5_to_obj(road, single)
    s2 = g.kn5_to_obj([road, race], both)
    v1, f1, g1, m1 = _obj_stats(single)
    v2, f2, g2, m2 = _obj_stats(both)
    assert v1 == s1["verts"] and f1 == s1["tris"] and len(g1) == s1["meshes"]
    assert v2 == 2 * v1 and f2 == 2 * f1 and g2 == g1 + g1
    assert m1 == v1 and m2 == v2, "face indices must reach exactly the last vertex of each file"
    assert s2["files"][1]["vertex_offset"] == v1 and s2["files"][0]["vertex_offset"] == 0
    # the single-file body is byte-identical to the first half of the pair (only the header names both)
    body1 = single.read_text(encoding="ascii").splitlines()[1:]
    body2 = both.read_text(encoding="ascii").splitlines()[1:1 + len(body1)]
    assert body1 == body2


def test_cli_repeats_kn5_and_refuses_the_preps_merge_glob_name():
    d = _project()
    road = build(d)
    race = road.with_name("t_race.kn5")
    shutil.copyfile(road, race)
    out = d / "data" / "track.race.obj"
    argv0 = sys.argv
    try:
        sys.argv = ["kn5_to_gate_obj", str(d), "--kn5", str(road), "--kn5", str(race), "--out", str(out)]
        g.main()
        single = d / "data" / "single.obj"
        g.kn5_to_obj(road, single)
        assert out.exists() and _obj_stats(out)[0] == 2 * _obj_stats(single)[0]
        # data/track_*.obj is what build_kn5_loop step 1b merges into the scene: never a gate OBJ name
        sys.argv = ["kn5_to_gate_obj", str(d), "--kn5", str(road), "--out", str(d / "data" / "track_race.obj")]
        try:
            g.main()
        except SystemExit as e:
            assert "track_" in str(e)
        else:
            raise AssertionError("track_race.obj was accepted as a gate OBJ name")
    finally:
        sys.argv = argv0
