"""scripts/blender/underlay.py in real Blender 4.2, headless, on a synthetic project (V3-PLAN P2 step 3; REALISM §4).

The collection contract, measured on the saved file: AUTH_* work survives two underlay runs byte-for-byte (its
fingerprint covers transforms, parents, collections, custom props, mesh/curve data and materials); the scene is
never reset (a plain user object and a scene setting survive); a re-run replaces only GEN objects, in place (same
digests, no ".001", no datablock growth); the D4 variant changes only the edge (the verge and the placeholder
ground pinned under it); a name held by something the underlay does not own is a refusal that saves nothing; an
AUTH promotion supersedes its role.
Skipped (with a note) where Blender 4.2 is not installed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BL = Path("C:/Program Files/Blender Foundation/Blender 4.2/blender.exe")   # tools/ship_sd.sh's BL=
UNDERLAY = ROOT / "scripts" / "blender" / "underlay.py"
PROBE = ROOT / "tests" / "tools" / "fixtures" / "underlay_probe.py"

_spec = importlib.util.spec_from_file_location("underlay_fixture", ROOT / "tests" / "geometry" / "underlay_fixture.py")
fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fx)


def _have_blender():
    if not BL.is_file():
        print("  (Blender 4.2 not installed — skipped)")
        return False
    return True


def _run(script, *args):
    env = dict(os.environ, PYTHONUTF8="1")
    r = subprocess.run([str(BL), "--background", "--python-exit-code", "1", "--python", str(script), "--", *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=600)
    return r


def _underlay(proj, *extra):
    r = _run(UNDERLAY, proj, *extra)
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith("[underlay]")]
    return r.returncode, lines, r.stdout + r.stderr


def _dump(blend, actions="dump"):
    out = Path(tempfile.mkdtemp()) / "state.json"
    r = _run(PROBE, blend, actions, out)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-800:]
    return json.loads(out.read_text(encoding="utf-8")) if "dump" in actions else None


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_auth_survives_two_runs_byte_for_byte_and_reruns_are_idempotent():
    if not _have_blender():
        return
    proj = fx.write_project(Path(tempfile.mkdtemp()) / "proj")
    blend = proj / "loop.blend"
    rc, lines, out = _underlay(proj)
    assert rc == 0, out[-2000:]
    assert any("no loop.blend yet: starting an empty file" in ln for ln in lines), lines
    rep = json.loads((proj / "data" / "underlay.json").read_text(encoding="utf-8"))
    assert rep["verge"]["width_m"] == 0.4 and rep["terrain"]["placeholder"] is True

    s0 = _dump(blend, "author+dump")                   # Kevin's work goes in; the state the runs must keep
    assert s0["up"]["1ROAD_road"]["down"] == 0 and s0["up"]["1RUNOFF_verge"]["down"] == 0
    assert s0["up"]["1GRASS_terrain_placeholder"]["down"] == 0
    assert len(s0["auth"]) == 7                        # 5 protected objects + 2 AUTH_ collections

    states = []
    for run in (1, 2):
        rc, lines, out = _underlay(proj)
        assert rc == 0, out[-2000:]
        assert any("edited in place: no scene reset" in ln for ln in lines), lines
        assert any("5 AUTH_* objects untouched" in ln for ln in lines), lines
        assert any("REF_st_00100: held by authored work" in ln for ln in lines), lines
        states.append(_dump(blend))
    for s in states:
        assert s["auth"] == s0["auth"], "AUTH_* changed"                     # byte-for-byte, both runs
        assert s["child_world"] == [7.0, 8.0, 9.0]                           # parented to 1ROAD_road, never moved
        assert s["kevin_note"] and s["kevin_setting"] == 42                  # no scene reset
        assert s["gen"] == s0["gen"], "a re-run changed GEN output"          # idempotent
        assert s["counts"] == s0["counts"], (s["counts"], s0["counts"])     # no orphan datablocks pile up
        assert not [n for n in s["objects"] if "." in n], s["objects"]       # no .001 duplicates
        assert {"GEN_road", "GEN_verge", "GEN_terrain", "GEN_refs", "AUTH_rocks", "AUTH_signs"} <= set(s["scene_children"])
    gen = states[1]["gen"]
    assert {gen[n]["role"] for n in gen} == {"road", "verge", "terrain", "refs"}
    assert gen["1ROAD_road"]["coll"] == "GEN_road" and gen["1RUNOFF_verge"]["coll"] == "GEN_verge"
    assert not [n for n in gen if n.upper().startswith(("HIGHWAY", "HWYSTRUCT", "MOUNTAINS", "LAMP", "LIGHT"))]
    assert "AUTH_inside_gen" not in gen and "AUTH_inside_gen" in states[1]["objects"]
    assert "REF_st_00100" not in gen and "REF_st_00100" in states[1]["objects"]     # adopted: his, not redrawn

    # D4 B: only the edge changes — the verge, and the placeholder ground pinned under it; the road and every ref
    # are identical. Back to A restores the A bytes.
    rc, lines, out = _underlay(proj, "--variant", "b_verge")
    assert rc == 0, out[-2000:]
    sb = _dump(blend)
    assert sb["auth"] == s0["auth"]
    edge = ("1RUNOFF_verge", "1GRASS_terrain_placeholder")
    for n in edge:
        assert sb["gen"][n]["data"] != gen[n]["data"], n
    assert {n: v for n, v in sb["gen"].items() if n not in edge} == {n: v for n, v in gen.items() if n not in edge}
    rc, lines, out = _underlay(proj, "--variant", "a_real_edge")
    assert rc == 0 and _dump(blend)["gen"] == gen


def test_a_name_it_does_not_own_is_refused_and_nothing_is_saved():
    if not _have_blender():
        return
    proj = fx.write_project(Path(tempfile.mkdtemp()) / "proj")
    blend = proj / "loop.blend"
    _dump(blend, "foreign")                            # a plain-collection 1ROAD_road, not GEN, not AUTH
    before = _sha(blend)
    rc, lines, out = _underlay(proj)
    assert rc != 0, out[-1500:]
    assert any("does not own it" in ln and "Nothing was saved" in ln for ln in lines), lines
    assert _sha(blend) == before
    assert not (proj / "data" / "underlay.json").exists()


def test_an_auth_promotion_supersedes_its_role():
    if not _have_blender():
        return
    proj = fx.write_project(Path(tempfile.mkdtemp()) / "proj")
    blend = proj / "loop.blend"
    assert _underlay(proj)[0] == 0
    s0 = _dump(blend, "promote+dump")                  # AUTH_road_mine: a copy carrying underlay_role = road
    rc, lines, out = _underlay(proj)
    assert rc == 0, out[-2000:]
    assert any("GEN_road: superseded by authored ['AUTH_road_mine']" in ln for ln in lines), lines
    s1 = _dump(blend)
    assert "1ROAD_road" not in s1["gen"] and "AUTH_road_mine" in s1["objects"]
    assert s1["auth"] == s0["auth"]
    assert "1RUNOFF_verge" in s1["gen"] and "1GRASS_terrain_placeholder" in s1["gen"]


def test_refusals_happen_before_the_blend_is_opened():
    if not _have_blender():
        return
    proj = fx.write_project(Path(tempfile.mkdtemp()) / "proj", verge_m=0.8)     # neither D4 A nor D4 B
    rc, lines, out = _underlay(proj)
    assert rc != 0 and any("neither D4 A" in ln for ln in lines), out[-1500:]
    assert not (proj / "loop.blend").exists()
    rc, lines, out = _underlay(proj, "--variant", "nope")
    assert rc != 0 and any("drive1_variants" in ln for ln in lines), out[-1500:]
