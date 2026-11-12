"""Lake Murray v4's houses (ledger 0065, Kevin 2026-11-03: "Lake Murray v4 had many more houses I[n] it this time, don't lose
those"): tools/house_gate.py counts the blocks on the BUILT road kn5 as connected shells and holds them to the floors in
track.config.json scenery.bespoke.house_gate; the chain stands them (ship.json draft 'bespoke') and gates them (gate 'houses');
the house textures engine-july lacks reach the exporter from airoso's assets (sync_in.assets + texture_overrides).

stdlib only: the kn5s here are written by a minimal writer in the layout scripts.ac.verify_kn5._parse_full reads, with every
face's corners split the way the exporter splits them at UV seams and normals.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LM = ROOT / "tracks" / "san-diego-lake-murray"
SNAP = LM / "engine-july-snapshot"
V4 = {"roofs": 7600, "blocks": 7600, "colliders": 275}          # v4 0.20.0's road kn5 (55f2026c), counted on the PC


def _gate():
    spec = importlib.util.spec_from_file_location("house_gate_under_test", ROOT / "tools" / "house_gate.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# --- a minimal kn5 writer ------------------------------------------------------------------------------------
def _s(b, t):
    e = t.encode("utf-8"); b += struct.pack("<I", len(e)) + e


def _box_faces(x, z, w, h, y0=0.0):
    """a block's four walls as separate quads (every corner its own vertex: the exporter's split), two triangles each"""
    c = [(x, z), (x + w, z), (x + w, z + w), (x, z + w)]
    P, T = [], []
    for i in range(4):
        (ax, az), (bx, bz) = c[i], c[(i + 1) % 4]
        k = len(P)
        P += [(ax, y0, az), (bx, y0, bz), (bx, y0 + h, bz), (ax, y0 + h, az)]
        T += [k, k + 1, k + 2, k, k + 2, k + 3]
    return P, T


def _roof(x, z, w, h):
    P = [(x, h, z), (x + w, h, z), (x + w, h, z + w), (x, h, z + w), (x + w / 2, h + 1.5, z + w / 2)]
    T = []
    for i in range(4):
        T += [i, (i + 1) % 4, 4]       # a hip roof: four triangles meeting at the ridge point
    return P, T


def _mesh_node(b, name, P, T):
    b += struct.pack("<I", 2); _s(b, name); b += struct.pack("<I", 0) + b"\x01"
    b += b"\x01\x01\x01" + struct.pack("<I", len(P))
    for p in P:
        b += struct.pack("<11f", p[0], p[1], p[2], 0, 1, 0, 0, 0, 1, 0, 0)
    b += struct.pack("<I", len(T)) + struct.pack(f"<{len(T)}H", *T)
    b += struct.pack("<I", 0) + struct.pack("<I", 0) + struct.pack("<ff", 0, 0) + b"\x00" * 16 + b"\x00"


def write_kn5(path, meshes):
    """meshes = [(name, P, T)]; one material, one root transform node holding every mesh"""
    b = bytearray(b"sc6969") + struct.pack("<i", 5) + struct.pack("<i", 0)
    b += struct.pack("<I", 1); _s(b, "m"); _s(b, "ksPerPixel"); b += b"\x00\x00" + struct.pack("<i", 0)
    b += struct.pack("<I", 0) + struct.pack("<I", 0)
    b += struct.pack("<I", 1); _s(b, "root"); b += struct.pack("<I", len(meshes)) + b"\x01"
    b += struct.pack("<16f", 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
    for name, P, T in meshes:
        _mesh_node(b, name, P, T)
    Path(path).write_bytes(bytes(b))


def _town(n_near, n_far, n_coll):
    """n_near BUILDING_STUCCO blocks + n_far FARBLOCK_TILTUP ones, a roof each, a collider skirt on the first n_coll near"""
    walls, far, roofs, coll = ([], []), ([], []), ([], []), ([], [])

    def add(acc, P, T):
        k = len(acc[0]); acc[0].extend(P); acc[1].extend(t + k for t in T)
    for i in range(n_near + n_far):
        x, z = (i % 40) * 20.0, (i // 40) * 20.0          # 20 m apart: no two blocks share a position
        add(walls if i < n_near else far, *_box_faces(x, z, 10.0, 3.0))
        add(roofs, *_roof(x, z, 10.0, 3.0))
        if i < n_coll:
            add(coll, *_box_faces(x + 0.4, z + 0.4, 9.2, 3.2, -0.3))
    out = []
    for name, (P, T) in (("BUILDING_STUCCO_0", walls), ("FARBLOCK_TILTUP_0", far), ("ROOFTOP_SHINGLE_0", roofs), ("1WALL_TILTUP_0", coll)):
        if P:
            out.append((name, P, T))
    out.append(("1GRASS_a", [(0, 0, 0), (1, 0, 0), (0, 0, 1)], [0, 1, 2]))     # not a house: never counted
    return out


def _project(tmp, floor, meshes):
    proj = Path(tmp)
    (proj / "build").mkdir(parents=True, exist_ok=True)
    cfg = {"slug": "t", "scenery": {"bespoke": {"house_gate": floor}}}
    (proj / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
    write_kn5(proj / "build" / "t.kn5", meshes)
    return proj


def _run(proj):
    return subprocess.run([sys.executable, str(ROOT / "tools" / "house_gate.py"), str(proj), "--json", str(proj / "hg.json")],
                          capture_output=True, text=True)


# --- the counter -----------------------------------------------------------------------------------------------
def test_a_split_box_is_one_shell_and_two_apart_are_two():
    g = _gate()
    P, T = _box_faces(0, 0, 10, 3)
    assert len(P) == 16 and g.shells(P, T) == 1           # 16 split corners, welded back to 8 positions: one shell
    P2, T2 = _box_faces(30, 0, 10, 3)
    assert g.shells(P + P2, T + [t + len(P) for t in T2]) == 2


def test_the_counter_reads_the_kn5_by_name_class():
    from scripts.ac.verify_kn5 import _parse_full
    g = _gate()
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "x.kn5"
        write_kn5(p, _town(30, 12, 9))
        _n, meshes, _m = _parse_full(p)
        counts, detail = g.count(meshes)
    assert counts == {"roofs": 42, "blocks": 42, "colliders": 9}, counts
    assert detail == {"1WALL_TILTUP": 9, "BUILDING_STUCCO": 30, "FARBLOCK_TILTUP": 12, "ROOFTOP_SHINGLE": 42}, detail


def test_the_gate_passes_at_its_floor_and_fails_one_block_short():
    floor = {"roofs": 42, "blocks": 42, "colliders": 9}
    with tempfile.TemporaryDirectory() as tmp:
        r = _run(_project(tmp, floor, _town(30, 12, 9)))
        assert r.returncode == 0 and "PASS" in r.stdout, r.stdout + r.stderr
        rep = json.loads((Path(tmp) / "hg.json").read_text())
        assert rep["fail"] is False and rep["counts"] == floor
    with tempfile.TemporaryDirectory() as tmp:            # one house fewer: its walls and its roof gone
        r = _run(_project(tmp, floor, _town(29, 12, 9)))
        assert r.returncode == 1 and "FAIL" in r.stdout, r.stdout
        rep = json.loads((Path(tmp) / "hg.json").read_text())
        assert {b["key"] for b in rep["below"]} == {"roofs", "blocks"}
    with tempfile.TemporaryDirectory() as tmp:            # one collider fewer
        r = _run(_project(tmp, floor, _town(30, 12, 8)))
        assert r.returncode == 1 and [b["key"] for b in json.loads((Path(tmp) / "hg.json").read_text())["below"]] == ["colliders"]


def test_no_floor_is_a_skip_and_no_kn5_is_an_input_error():
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp)
        (proj / "track.config.json").write_text(json.dumps({"slug": "t"}), encoding="utf-8")
        r = _run(proj)
        assert r.returncode == 0 and "no floor declared" in r.stdout
        (proj / "track.config.json").write_text(json.dumps({"slug": "t", "scenery": {"bespoke": {"house_gate": V4}}}), encoding="utf-8")
        assert _run(proj).returncode == 2


def test_v4_counts_pass_and_one_fewer_of_any_fails():
    g = _gate()
    floor = g.floors(json.loads((LM / "track.config.json").read_text(encoding="utf-8")))
    assert floor == V4, floor
    assert g.verdict(dict(V4), floor) == []
    assert g.verdict({"roofs": 7601, "blocks": 7650, "colliders": 300}, floor) == []      # a floor, not a target
    for k in V4:
        short = dict(V4, **{k: V4[k] - 1})
        assert g.verdict(short, floor) == [(k, V4[k] - 1, V4[k])], k


def test_v4_blocks_record_matches_the_floors():
    """data/bespoke.report.json: the 7,600 blocks the chain's bespoke step stands from source/bespoke/buildings.json on v4's
    loop.blend (rim_step_m 2.0), vertex for vertex the 23 AUTH_bespoke batches v4 shipped (ledger 0065)"""
    rows = json.loads((LM / "data" / "bespoke.report.json").read_text(encoding="utf-8"))["blocks"]
    near = [r for r in rows if not r["off_terrain"]]
    assert len(rows) == 7600 and len({r["key"] for r in rows}) == 7600
    assert len(near) == 6239 and len(rows) - len(near) == 1361
    assert sum(1 for r in rows if r["collider"]) == 275
    skins = {}
    for r in near:
        skins[r["skin"]] = skins.get(r["skin"], 0) + 1
    assert skins == {"STUCCO": 5795, "METAL": 226, "TILTUP": 218}, skins
    plan = {b["key"] for b in json.loads((LM / "source" / "bespoke" / "buildings.json").read_text(encoding="utf-8"))}
    assert {r["key"] for r in rows} <= plan


# --- the chain -------------------------------------------------------------------------------------------------
def test_lm_chain_stands_the_blocks_and_gates_them():
    ship = json.loads((LM / "ship.json").read_text(encoding="utf-8"))
    dr, gt = ship["steps"]["draft"], ship["steps"]["gate"]
    i = dr.index("bespoke")
    assert dr[i - 1] == "stubs_author" and dr[i + 1] == "gap_mouths"     # where ship_sd.sh's SD_BESPOKE=1 rehearsal stood them
    assert gt.index("houses") == gt.index("house_seat") + 1
    assert "source/bespoke/buildings.json" in ship["sync_in"]["optional"]
    assert {"data/bespoke.report.json", "data/house_gate.json"} <= set(ship["sync_out"]["files"])
    b = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))["scenery"]["bespoke"]
    assert b["blocks"][0]["file"] == "source/bespoke/buildings.json" and b["blocks"][0]["rim_step_m"] == 2.0
    assert b["prep_seats"] is True and "ship_track.sh" in b["_doc"] and "REHEARSAL" not in b["_doc"]
    sh = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8")
    body = re.search(r"^draft_bespoke\(\) \{\n(.*?)^\}\n", sh, re.S | re.M).group(1)
    assert "tools/author_bespoke_blend.py" in body and "--python-exit-code 1" in body
    body = re.search(r"^gate_houses\(\) \{\n(.*?)^\}\n", sh, re.S | re.M).group(1)
    assert "tools/house_gate.py" in body and '$PROJ/build/$SLUG.kn5' in body


def _snap_pbr():
    spec = importlib.util.spec_from_file_location("pbr_snapshot_under_test", SNAP / "scripts" / "ac" / "pbr.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_the_house_textures_reach_the_exporter_from_airosos_assets():
    """every pbr row (engine-july's, as snapshotted) a v4 block class matches names a file engine-july lacks; the config
    points that row at airoso's tracked file, ship.json copies it into the project, same bytes; FARBLOCK_STUCCO has no row"""
    pbr = _snap_pbr()
    cfg = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))
    ship = json.loads((LM / "ship.json").read_text(encoding="utf-8"))
    ref = {}
    for ln in (SNAP / "REFERENCED.md5").read_text(encoding="utf-8").splitlines():
        if ln and not ln.startswith("#"):
            md5, _size, path = ln.split()
            ref[path] = md5
    classes = ["BUILDING_STUCCO", "BUILDING_METAL", "BUILDING_TILTUP", "FARBLOCK_METAL", "FARBLOCK_TILTUP", "1WALL_TILTUP",
               "ROOFTOP_SHINGLE", "ROOFTOP_WHITE", "ROOFTOP_TAN", "ROOFTOP_DARK"]
    want = set()
    for c in classes:
        key = next(k for k in pbr.TEXTURES if (c + "_0").startswith(k))
        assert key == c, (c, key)
        ov = cfg["texture_overrides"][c]
        for slot, f in (("diffuse", pbr.TEXTURES[key][0]), ("normal", pbr.TEXTURES[key][1])):
            if f is None:
                assert slot not in ov
                continue
            rel = f"assets/textures/{f}"
            assert ov[slot] == rel, (c, slot, ov)
            assert rel not in ref or ref[rel] == hashlib.md5((ROOT / rel).read_bytes()).hexdigest(), rel
            want.add(rel)
    assert next((k for k in pbr.TEXTURES if "FARBLOCK_STUCCO_0".startswith(k)), None) is None
    assert "FARBLOCK_STUCCO" not in cfg["texture_overrides"]
    assert set(ship["sync_in"]["assets"]) == want and len(want) == 10
    for rel in want:
        assert (ROOT / rel).is_file() and rel not in ref       # engine-july has none of them: the project's copy is the one used
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=ROOT, capture_output=True)
        assert tracked.returncode == 0, rel


def test_load_overrides_resolves_to_the_projects_copy_when_the_engine_lacks_it():
    pbr = _snap_pbr()
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp)
        cfg = {"texture_overrides": {"BUILDING_STUCCO": {"diffuse": "assets/textures/stucco_wall_diffuse.jpg",
                                                         "normal": "assets/textures/stucco_wall_normal.jpg"}}}
        (proj / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
        ov = pbr.load_overrides(proj)
    assert Path(ov["BUILDING_STUCCO"]["diffuse"]) == proj / "assets" / "textures" / "stucco_wall_diffuse.jpg"


def test_spec_takes_assets_only_under_assets():
    spec = importlib.util.spec_from_file_location("ship_track_spec_under_test", ROOT / "tools" / "ship_track_spec.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    s = m.load(LM / "ship.json", "san-diego-lake-murray")
    assert all(p.startswith("assets/textures/") for p in s["sync_in"]["assets"])
    assert sum(1 for ln in m.lines(s) if ln.startswith("in.assets\t")) == 10
    with tempfile.TemporaryDirectory() as tmp:
        d = json.loads((LM / "ship.json").read_text(encoding="utf-8"))
        d["sync_in"]["assets"] = ["tracks/x.jpg"]
        p = Path(tmp) / "ship.json"
        p.write_text(json.dumps(d), encoding="utf-8")
        try:
            m.load(p, "san-diego-lake-murray")
        except m.SpecError as e:
            assert "assets/" in str(e)
        else:
            raise AssertionError("a sync_in.assets path outside assets/ was taken")
