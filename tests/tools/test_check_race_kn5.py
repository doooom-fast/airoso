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

ALLOWED = {"kerb_race_worn_diffuse.jpg", "kerb_race_worn_normal.jpg", "concrete_barrier_diffuse.png",
           "concrete_barrier_normal.png"}
KERB_TEX = ("kerb_race_worn_diffuse.jpg", "kerb_race_worn_normal.jpg")
WALL_TEX = ("concrete_barrier_diffuse.png", "concrete_barrier_normal.png")


def _parse(names, textures=None, size=9_000_000):
    """inspect_kn5-shaped: by default it embeds exactly the textures the race rows bind for `names`"""
    if textures is None:
        textures = (KERB_TEX if any(n.upper().startswith("1KERB_RACE") for n in names) else ()) + WALL_TEX
    return {"file_bytes": size, "nodes": ["BlenderFile"], "textures": [{"name": t} for t in textures],
            "meshes": [{"name": n, "verts": 1000, "tris": 1200} for n in names]}


def _with_materials(parsed, kerb_slots=(("txDiffuse", KERB_TEX[0]), ("txNormal", KERB_TEX[1])), nbytes=None):
    """the same parse with materials (one per mesh, bound like the exporter does) and texture byte counts"""
    out = dict(parsed)
    mats, meshes = [], []
    for i, m in enumerate(parsed["meshes"]):
        kerb = m["name"].upper().startswith("1KERB_RACE")
        slots = list(kerb_slots) if kerb else [("txDiffuse", WALL_TEX[0]), ("txNormal", WALL_TEX[1])]
        mats.append({"name": m["name"] + "_mat", "shader": "ksPerPixelMultiMap", "props": {}, "textures": slots})
        meshes.append(dict(m, matid=i))
    out["materials"], out["meshes"] = mats, meshes
    out["textures"] = [dict(t, bytes=(nbytes or {}).get(t["name"], 1000)) for t in parsed["textures"]]
    return out


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


def test_ledger_0053_no_black_kerb_slot():
    """the worn kerb atlas only reaches the kn5 if it was in engine-july/assets/textures when the export ran (it
    stages from there; a missing file is skipped with a WARNING and the slot renders BLACK, LAWS L7). The guard
    fails a common kn5 whose kerbs' textures are absent, empty, or bound to the wrong slot — and the v0.17.1 shape
    (the old 771-byte stripe, no normal map) — while a closure kn5 (no kerb) needs only the K-rail pair."""
    assert ck.race_texture_set() == ALLOWED                        # read from pbr.py, never restated in the guard
    assert ck.expected_slots("1KERB_race_770_in") == {"txDiffuse": KERB_TEX[0], "txNormal": KERB_TEX[1]}
    assert ck.expected_slots("1WALL_race_close_cw_college_777_0") == {"txDiffuse": WALL_TEX[0], "txNormal": WALL_TEX[1]}
    assert ck.expected_slots("1ROAD_road") == {} and ck.expected_slots("1KERB_sidewalk") == {}
    good = _with_materials(_parse(COMMON))
    r = ck.check(good, ALLOWED, role="common", expect_kerbs=2)
    assert r["ok"], r["fails"]
    cases = [
        (_with_materials(_parse(COMMON, textures=WALL_TEX + (KERB_TEX[0],))), "NOT embedded"),          # normal never staged
        (_with_materials(_parse(COMMON), nbytes={KERB_TEX[1]: 0}), "0 bytes"),
        (_with_materials(_parse(COMMON), kerb_slots=(("txDiffuse", KERB_TEX[0]),)), "txNormal=None"),
        (_with_materials(_parse(COMMON), kerb_slots=(("txDiffuse", KERB_TEX[1]), ("txNormal", KERB_TEX[0]))),
         "the pbr row says"),
        (_parse(COMMON, textures=WALL_TEX), "NOT embedded"),                                          # no materials in the parse
    ]
    for parsed, msg in cases:
        r = ck.check(parsed, ALLOWED, role="common", expect_kerbs=2)
        assert not r["ok"] and any(msg in f for f in r["fails"]), (msg, r["fails"])
    # the installed v0.17.1 race kn5's shape: the old stripe, no normal map -> FAILS (alien + missing + bindings)
    old = _with_materials(_parse(COMMON, textures=("kerb_diffuse.png",) + WALL_TEX),
                          kerb_slots=(("txDiffuse", "kerb_diffuse.png"),))
    r = ck.check(old, ALLOWED, role="common", expect_kerbs=2)
    assert not r["ok"] and any("outside the race set" in f for f in r["fails"]) and         any("NOT embedded" in f for f in r["fails"]), r["fails"]
    # a closure kn5 carries no kerb: the K-rail pair is all it needs
    r = ck.check(_with_materials(_parse(CLOSE_CW)), ALLOWED, role="closure", owner="cw")
    assert r["ok"], r["fails"]
    r = ck.check(_with_materials(_parse(CLOSE_CW, textures=(WALL_TEX[0],))), ALLOWED, role="closure", owner="cw")
    assert not r["ok"] and any("NOT embedded" in f for f in r["fails"]), r["fails"]
