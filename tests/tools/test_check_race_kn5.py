"""tools/check_race_kn5.py — the race-furniture kn5s' content guard per ROLE (ledger 0049): the COMMON
<slug>_race.kn5 (curb strips + the declared number of kerbs, no closure, no retired centre chain) and each race
layout's <slug>_closure_<id>.kn5 (only that layout's 1WALL_RACE_CLOSE_<TOKEN>_* meshes). Both: race textures
only, no AC_* node, size only WARNS. (The role-free content guard is pinned in tests/tools/test_ship_sd_chain.py.)
Plain ``test_*`` functions on inspect_kn5-shaped dicts; the CLI is driven on temp files.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import check_race_kn5 as ck  # noqa: E402

ALLOWED = {"kerb_diffuse.png", "concrete_barrier_diffuse.png", "concrete_barrier_normal.png"}


def _parse(names, textures=("concrete_barrier_diffuse.png", "concrete_barrier_normal.png"), size=9_000_000):
    return {"file_bytes": size, "nodes": ["BlenderFile"], "textures": [{"name": t} for t in textures],
            "meshes": [{"name": n, "verts": 1000, "tris": 1200} for n in names]}


COMMON = ["1WALL_race_edge_L_alvarado_0_0", "1WALL_race_edge_R_alvarado_5_0", "1KERB_race_770_in", "1KERB_race_770_out"]
CLOSE_CW = ["1WALL_race_close_cw_college_777_0", "1WALL_race_close_cw_navajo_1521_0"]


def test_common_role():
    r = ck.check(_parse(COMMON, textures=sorted(ALLOWED)), ALLOWED, role="common", expect_kerbs=2)
    assert r["ok"] and r["warns"] == [] and r["summary"]["edges"] == 2 and r["summary"]["kerbs"] == 2, r
    cases = [
        (COMMON + ["1WALL_race_close_cw_college_777_0"], 2, "closure meshes in the COMMON kn5"),
        (COMMON + ["1WALL_race_kbar_navajo_2297_0"], 2, "retired centre-chain"),
        ([n for n in COMMON if "edge" not in n], 2, "no curb strip"),
        (COMMON, 10, "2 race kerbs (1KERB_RACE_*), the declaration has 10"),
        (COMMON + ["1ROAD_road"], 2, "non-race meshes"),
    ]
    for names, kerbs, msg in cases:
        r = ck.check(_parse(names), ALLOWED, role="common", expect_kerbs=kerbs)
        assert not r["ok"] and any(msg in f for f in r["fails"]), (msg, r["fails"])
    r = ck.check(_parse(COMMON), ALLOWED, role="common")                    # kerb count not pinned: a WARN
    assert r["ok"] and any("not pinned" in w for w in r["warns"]), r


def test_closure_role():
    r = ck.check(_parse(CLOSE_CW), ALLOWED, role="closure", owner="cw")
    assert r["ok"] and r["summary"]["closures"] == 2, r
    for names, owner, msg in (
            (CLOSE_CW, "acw", "not 'acw''s closure"),                       # the other direction's file
            (CLOSE_CW + ["1KERB_race_770_in"], "cw", "not 'cw''s closure"),
            (CLOSE_CW + ["1WALL_race_edge_L_alvarado_0_0"], "cw", "not 'cw''s closure"),
            ([], "cw", "no mesh in the race kn5"),
            (CLOSE_CW, None, "--role closure needs --owner")):
        r = ck.check(_parse(names), ALLOWED, role="closure", owner=owner)
        assert not r["ok"] and any(msg in f for f in r["fails"]), (msg, r["fails"])
    r = ck.check(_parse(CLOSE_CW, textures=("asphalt.jpg",)), ALLOWED, role="closure", owner="cw")
    assert any("textures outside the race set" in f for f in r["fails"])
    r = ck.check(dict(_parse(CLOSE_CW), nodes=["BlenderFile", "AC_START_0"]), ALLOWED, role="closure", owner="cw")
    assert any("AC_* nodes" in f for f in r["fails"])
    big = ck.check(_parse(CLOSE_CW, size=25_000_000), ALLOWED, role="closure", owner="cw")
    assert big["ok"] and len(big["warns"]) == 1                            # size is a WARN, never the gate
    try:
        ck.check(_parse(CLOSE_CW), ALLOWED, role="chain")
    except ValueError:
        pass
    else:
        raise AssertionError("an unknown role must be refused")


def test_cli_roles_and_the_kerb_count_from_the_declaration():
    d = Path(tempfile.mkdtemp())
    (d / "race_kn5.json").write_text(json.dumps(_parse(COMMON)))
    (d / "closure_race_cw.kn5.json").write_text(json.dumps(_parse(CLOSE_CW)))
    (d / "barrier_bands.json").write_text(json.dumps({"kerbs": [{"apex": 770, "kind": "inside"}, {"apex": 770, "kind": "outside"}]}))
    assert ck.main([str(d / "race_kn5.json")]) == 0                          # default role: common, 2 kerbs declared beside it
    assert ck.main([str(d / "race_kn5.json"), "--role", "common", "--expect-kerbs", "10"]) == 1
    assert ck.main([str(d / "closure_race_cw.kn5.json"), "--role", "closure", "--owner", "cw"]) == 0
    assert ck.main([str(d / "closure_race_cw.kn5.json"), "--role", "closure", "--owner", "acw"]) == 1
    assert ck.main([str(d / "closure_race_cw.kn5.json"), "--role", "common"]) == 1
    try:
        ck.main([str(d / "race_kn5.json"), "--role", "chain"])
    except SystemExit as e:
        assert "usage" in str(e)
    else:
        raise AssertionError("an unknown role must be a usage error")
