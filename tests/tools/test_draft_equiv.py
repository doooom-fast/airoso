"""tools/draft_equiv.py: two projects the same, path-only, and different (ledger 0078, the PC's apples-to-apples check)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import draft_equiv as de  # noqa: E402


def _proj(root: Path, note: str = "x", blend: bytes = b"A"):
    (root / "data").mkdir(parents=True)
    (root / "data" / "a.json").write_text(json.dumps({"src": str(root / "data" / "z.npy"), "n": 1}), encoding="utf-8")
    (root / "data" / "b.bin").write_bytes(b"\x00\x01" + note.encode())
    (root / "loop.blend").write_bytes(blend)                    # judged by digest, never by bytes
    (root / "build").mkdir()
    (root / "build" / "t.kn5").write_bytes(blend)               # kn5_equiv's job


def _digest(p: Path, **over):
    rec = {"type": "MESH", "parent": None, "matrix": [1.0] * 16, "materials": ["m"], "verts": 4, "faces": 2,
           "co_md5": "c", "faces_md5": "f", "uv_md5": {"UVMap": "u"}}
    rec.update(over)
    p.write_text(json.dumps({"objects": {"ROAD": rec}}), encoding="utf-8")
    return str(p)


def test_same_projects_in_different_scratch_copies_are_same(tmp_path=None):
    tmp_path = tmp_path or Path(tempfile.mkdtemp())     # tests/run_tests.py passes no fixtures
    _proj(tmp_path / "lm_line", blend=b"A")
    _proj(tmp_path / "lm_fleet", blend=b"B")
    assert de.main([str(tmp_path / "lm_line"), str(tmp_path / "lm_fleet")]) == 0
    n, diffs, path_only = de.compare_files(tmp_path / "lm_line", tmp_path / "lm_fleet")
    assert n == 2 and not diffs and path_only == ["data/a.json"]


def test_a_changed_data_file_and_a_missing_one_differ(tmp_path=None):
    tmp_path = tmp_path or Path(tempfile.mkdtemp())     # tests/run_tests.py passes no fixtures
    _proj(tmp_path / "a")
    _proj(tmp_path / "b", note="y")
    (tmp_path / "b" / "data" / "extra.json").write_text("{}", encoding="utf-8")
    assert de.main([str(tmp_path / "a"), str(tmp_path / "b")]) == 1
    _, diffs, _ = de.compare_files(tmp_path / "a", tmp_path / "b")
    assert diffs == ["only in B: data/extra.json", "differs: data/b.bin (3 vs 3 bytes)"]


def test_digests_name_the_object_and_what_moved(tmp_path=None):
    tmp_path = tmp_path or Path(tempfile.mkdtemp())     # tests/run_tests.py passes no fixtures
    _proj(tmp_path / "a")
    _proj(tmp_path / "b")
    da = _digest(tmp_path / "a.json")
    assert de.main([str(tmp_path / "a"), str(tmp_path / "b"), "--digest", da, _digest(tmp_path / "b.json")]) == 0
    db = _digest(tmp_path / "b2.json", verts=5, co_md5="d")
    assert de.main([str(tmp_path / "a"), str(tmp_path / "b"), "--digest", da, db]) == 1
    _, dd = de.compare_digests(Path(da), Path(db))
    assert dd == ["object ROAD: co_md5, verts differ (verts 4 vs 5, faces 2 vs 2)"]


def test_a_gzip_written_at_another_time_is_the_same(tmp_path=None):
    tmp_path = tmp_path or Path(tempfile.mkdtemp())     # tests/run_tests.py passes no fixtures
    import gzip
    _proj(tmp_path / "a")
    _proj(tmp_path / "b")
    (tmp_path / "a" / "data" / "t.json.gz").write_bytes(gzip.compress(b'{"z": 1}', mtime=1))
    (tmp_path / "b" / "data" / "t.json.gz").write_bytes(gzip.compress(b'{"z": 1}', mtime=2))
    assert de.main([str(tmp_path / "a"), str(tmp_path / "b")]) == 0
    (tmp_path / "b" / "data" / "t.json.gz").write_bytes(gzip.compress(b'{"z": 2}', mtime=2))
    assert de.main([str(tmp_path / "a"), str(tmp_path / "b")]) == 1


def test_a_json_written_at_another_time_is_the_same(tmp_path=None):
    tmp_path = tmp_path or Path(tempfile.mkdtemp())     # tests/run_tests.py passes no fixtures
    import gzip
    _proj(tmp_path / "a")
    _proj(tmp_path / "b")
    for k, t in (("a", "2026-11-04T05:01:26Z"), ("b", "2026-11-04T05:01:42Z")):
        doc = {"_provenance": {"written_utc": t}, "z": [1, 2]}
        (tmp_path / k / "data" / "t.json.gz").write_bytes(gzip.compress(json.dumps(doc).encode()))
    assert de.main([str(tmp_path / "a"), str(tmp_path / "b")]) == 0


def test_terrain_noise_allows_exactly_the_written_list(tmp_path=None):
    """--terrain-noise (ledger 0078 step 5): TERRAIN and the ground tiles may differ, a house only in its positions,
    the terrain-stage reports and any "seconds"; a road object or any other file still makes it DIFFERENT"""
    tmp_path = tmp_path or Path(tempfile.mkdtemp())     # tests/run_tests.py passes no fixtures
    import json as _j
    for side, z, secs in (("a", 0.0, 4.9), ("b", 0.01, 6.3)):
        d = tmp_path / side
        (d / "data").mkdir(parents=True)
        (d / "data" / "ground_release.report.json").write_text(_j.dumps({"welded": 6963 if side == "a" else 7014}))
        (d / "data" / "race_authored.json").write_text(_j.dumps({"rings": 4498, "seconds": secs}))
        (d / "data" / "mouths.json").write_text(_j.dumps({"mouths": 32}))
        objs = {"TERRAIN": {"verts": 632014 if side == "a" else 631989, "co_md5": side},
                "BUILDING_STUCCO_0": {"verts": 100, "co_md5": side},
                "1ROAD_road": {"verts": 50, "co_md5": "same"}}
        (tmp_path / f"{side}.digest.json").write_text(_j.dumps({"objects": objs}))
    a, b = tmp_path / "a", tmp_path / "b"
    da, db = str(tmp_path / "a.digest.json"), str(tmp_path / "b.digest.json")
    assert de.main([str(a), str(b), "--digest", da, db]) == 1                       # strict: different
    assert de.main([str(a), str(b), "--digest", da, db, "--terrain-noise"]) == 0    # only the written list
    (b / "data" / "mouths.json").write_text(_j.dumps({"mouths": 31}))                # any other file: still a difference
    assert de.main([str(a), str(b), "--digest", da, db, "--terrain-noise"]) == 1
    (b / "data" / "mouths.json").write_text(_j.dumps({"mouths": 32}))
    objs = _j.loads((tmp_path / "b.digest.json").read_text())["objects"]
    objs["BUILDING_STUCCO_0"]["verts"] = 101                                         # a house's COUNT is not noise
    (tmp_path / "b.digest.json").write_text(_j.dumps({"objects": objs}))
    assert de.main([str(a), str(b), "--digest", da, db, "--terrain-noise"]) == 1
    objs["BUILDING_STUCCO_0"]["verts"] = 100
    objs["1ROAD_road"]["co_md5"] = "moved"                                           # nor any road object
    (tmp_path / "b.digest.json").write_text(_j.dumps({"objects": objs}))
    assert de.main([str(a), str(b), "--digest", da, db, "--terrain-noise"]) == 1


def test_terrain_noise_allows_the_stubs_pinned_count_only(tmp_path=None):
    """stubs.built.json: terrain.verts_pinned follows the terrain's own vertex count (14,467 / 14,468 on one branch, the PC
    2026-11-05) and is noise; any other key of the stub report is not"""
    tmp_path = tmp_path or Path(tempfile.mkdtemp())     # tests/run_tests.py passes no fixtures
    for side, pinned in (("a", 14467), ("b", 14468)):
        (tmp_path / side / "data").mkdir(parents=True)
        (tmp_path / side / "data" / "stubs.built.json").write_text(
            json.dumps({"stubs": 12, "terrain": {"verts_pinned": pinned, "max_lift_m": 0.4}}), encoding="utf-8")
    a, b = tmp_path / "a", tmp_path / "b"
    assert de.main([str(a), str(b)]) == 1
    assert de.main([str(a), str(b), "--terrain-noise"]) == 0
    (b / "data" / "stubs.built.json").write_text(
        json.dumps({"stubs": 11, "terrain": {"verts_pinned": 14468, "max_lift_m": 0.4}}), encoding="utf-8")
    assert de.main([str(a), str(b), "--terrain-noise"]) == 1
