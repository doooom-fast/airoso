"""The Lariat's Drive-1 build (V3-PLAN "-> Drive 1": road + ground only, two installs that differ only in the D4
edge; ledger 0048), pinned on the config, ship.json, the script text and guard-only runs of tools/ship_track.sh:

- the race layouts are PARKED (moved whole into layouts_parked, not deleted): layouts[] is street_full +
  street_reverse, the race block stays declared, and the config remap still moves a parked layout's start vertices;
- ship.json runs no race step, no AI and no TreeFX, and its gates are P5's Drive-1 set on the built road, ending
  in the Drive-1 verdict; the race steps it will need again are listed under _drive3_steps;
- SHIP_VARIANT: an unknown or malformed id exits 2 before anything is touched; the underlay gets --variant; the
  install goes to the variant's folder and name; a loop.blend drafted for the other edge is refused before the
  prep; a variant run never syncs back; --force-install is refused when the verdict says the run is worse than July;
- the new functions sit in one marked block after the Drive-1 gates block (nothing above reordered).
Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SH = ROOT / "tools" / "ship_track.sh"
TEXT = SH.read_text(encoding="utf-8").replace("\r\n", "\n")
CFG = json.loads((ROOT / "tracks" / "lookout-lariat" / "track.config.json").read_text(encoding="utf-8"))
SPEC = ROOT / "tracks" / "lookout-lariat" / "ship.json"
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import ship_track_spec as spec_mod  # noqa: E402
import remap_centreline_config as remap_mod  # noqa: E402
from scripts.geometry import underlay_draft as ud  # noqa: E402

MARK = "# LARIAT DRIVE-1 BUILD"


def _first(s: str) -> int:
    i = TEXT.find(s)
    assert i >= 0, s
    return i


def _body(fn: str) -> str:
    m = re.search(rf"^{fn}\(\) \{{\n(.*?)^\}}\n", TEXT, re.S | re.M)
    assert m, fn
    return m.group(1)


# --- the config ------------------------------------------------------------------------------------------------
def test_race_layouts_are_parked_not_deleted():
    assert [lo["id"] for lo in CFG["layouts"]] == ["street_full", "street_reverse"]
    parked = CFG["layouts_parked"]
    assert [lo["id"] for lo in parked] == ["race_acw", "race_cw"]
    for lo in parked:
        assert lo["race_furniture"] is True and lo["kind"] == "race" and lo["closure_token"] in ("acw", "cw")
        assert {"line_vertex", "grid_vertex", "sector_vertices"} <= set(lo["start"])
    assert "Drive 3" in CFG["_layouts_parked_doc"] and "not deleted" in CFG["_layouts_parked_doc"]
    assert CFG["race"], "the race block stays declared"
    assert all(not lo.get("race_furniture") for lo in CFG["layouts"])


def test_the_remap_still_moves_a_parked_layouts_vertices():
    class Shift:
        def local_index(self, v):
            return v + 3

        def local_station(self, s):
            return s + 1.0

        def geo_station(self, s):
            return s + 1.0

        def position_shift_m(self, a, b):
            return 0.0
    new, changes = remap_mod.remap(CFG, Shift())
    for old, lo in zip(CFG["layouts_parked"], new["layouts_parked"]):
        assert lo["start"]["grid_vertex"] == old["start"]["grid_vertex"] + 3
        assert lo["start"]["sector_vertices"] == [v + 3 for v in old["start"]["sector_vertices"]]
    assert any(c["path"].startswith("layouts_parked") for c in changes)


def test_the_d4_variants_differ_only_in_the_edge_and_the_install():
    v = CFG["drive1_variants"]
    a, b = v["a_real_edge"], v["b_verge"]
    assert set(a) == set(b) == {"road_profile.verge_m", "install_folder", "ui_name_prefix"}
    assert a["install_folder"] == CFG["install_folder"] == "lookout_lariat_v3" and b["install_folder"] == "lookout_lariat_v3_verge"
    assert a["road_profile.verge_m"] == CFG["road_profile"]["verge_m"] == 0.4 and b["road_profile.verge_m"] == 1.25
    assert a["ui_name_prefix"] != b["ui_name_prefix"]
    # the underlay applies only the edge: the ship chain's keys never reach its config
    out = ud.apply_variant(json.loads(json.dumps(CFG)), "b_verge")
    assert out["road_profile"]["verge_m"] == 1.25
    assert out["install_folder"] == CFG["install_folder"] and "ui_name_prefix" not in out


# --- ship.json --------------------------------------------------------------------------------------------------
def test_ship_json_is_the_drive1_chain():
    s = spec_mod.load(SPEC, "lookout-lariat")
    st = s["steps"]
    assert st["draft"][-1] == "underlay" and st["author"] == ["layout_dummies", "overpass_decks"]
    allsteps = sum(st.values(), [])
    for n in ("race_bands", "race_planned_gate", "race_author", "race_verify", "export_race", "race_scenery_gate",
              "race_gates", "ai", "treefx", "drive_test_street"):
        assert n not in allsteps, n
    assert st["prep"] == ["prep", "split_street"]
    # 2026-10-12: verify_kn5 / --inis keep their output as the reports the verdict reads; the built folder carries
    # the installed names (ui_names) before the map is drawn
    assert st["ship"] == ["export_road", "spawn_kn5", "verify_kn5_report", "track_folder", "verify_inis_report",
                          "ui_names", "make_map"]
    g = st["gate"]
    # kn5_ground_check runs kn5-internal, before road_obj writes the gate OBJ it would otherwise read as a source OBJ
    assert g[:2] == ["kn5_ground_check", "road_obj"] and g[-1] == "drive1_verdict"
    for n in ("drive_test_drive1", "audit_street", "road_inventory", "stacked_legs"):
        assert g.index("road_obj") < g.index(n) < g.index("drive1_verdict"), n
    for n in ("verify_centreline_paint", "route_oneway_check", "verify_crossfall"):      # the draft's hard gates
        assert n in st["draft"], n
    d3 = json.loads(SPEC.read_text(encoding="utf-8"))["_drive3_steps"]
    assert "race_author" in d3["author"] and "ai" in d3["ship"] and d3["gate_add"] == ["race_gates"]
    for f in ("data/underlay.json", "data/kn5_ground_check.txt", "data/drive1_gates.json", "data/verify_kn5.txt",
              "data/verify_inis.txt", "data/overpass_decks.json", "data/drive1_build.json"):
        assert f in s["sync_out"]["files"], f


# --- the script text --------------------------------------------------------------------------------------------
def test_the_block_is_one_marked_block_after_the_drive1_gates():
    i = _first(MARK)
    assert TEXT.count(MARK) == 1
    assert _first("# LARIAT DRIVE-1 GATES") < i < _first("is_data_step() {")
    names = re.findall(r"^([a-z0-9_]+)\(\) \{", TEXT, re.M)
    after = [n for n in names if i < TEXT.find(f"\n{n}() {{") and n != "is_data_step"
             and TEXT.find(f"\n{n}() {{") < _first("is_data_step() {")]
    assert after == ["prep_split_street", "gate_drive_test_drive1", "gate_kn5_ground_check", "gate_drive1_verdict",
                     "d4_variant_check", "d4_variant_apply", "d4_variant_guard",
                     # the 2026-10-12 fixes block, appended after the build block
                     "author_overpass_decks", "ship_verify_kn5_report", "ship_verify_inis_report", "ship_ui_names"], after
    assert _first("# LARIAT DRIVE-1 FIXES") > _first("d4_variant_guard() {")


def test_the_street_split_accepts_only_the_two_no_race_problems():
    b = _body("prep_split_street")
    assert b.find('[ -z "$RACE_IDS" ] ||') < b.find('"$BL" --background --python-exit-code 1 --python "$AIROSO/tools/split_exports_blend.py"')
    assert b.find('rm -f "$PROJ/blender/split/split_manifest.json"') < b.find('--python "$AIROSO/tools/split_exports_blend.py"')
    for frag in ("'input: no race furniture (run author_race_furniture_blend first)'",
                 "'race: no curb strip (1WALL_race_edge_*) in loop_race.blend'", "loop_spawn_%s.blend", "race_objects",
                 "m.get('tokens')"):
        assert frag in b, frag
    # the spec takes either split, nothing else
    assert spec_mod.PREP_FORMS == (["prep", "split"], ["prep", "split_street"])
    d = json.loads(SPEC.read_text(encoding="utf-8"))
    for bad in (["prep"], ["split_street", "prep"], ["prep", "split", "split_street"]):
        d["steps"]["prep"] = bad
        p = Path(tempfile.mkdtemp()) / "ship.json"
        p.write_text(json.dumps(d), encoding="utf-8")
        try:
            spec_mod.load(p, "lookout-lariat")
        except spec_mod.SpecError as e:
            assert "exactly" in str(e)
        else:
            raise AssertionError(bad)


def test_the_drive1_steps():
    b = _body("gate_drive_test_drive1")
    assert 'for lid in $STREET_IDS; do' in b and 'python -m scripts.geometry.drive_test "$PROJ" --layout "$lid"' in b
    assert "DT_S" not in b, "the Drive-1 set judges drive_test, not drive_test's own pass line"
    k = _body("gate_kn5_ground_check")
    assert k.find('rm -f "$PROJ/data/kn5_ground_check.txt" "$PROJ/data/track.obj"') <         k.find("python -m scripts.ac.kn5_ground_check \"$PROJ\"")
    assert "environment.obj" in k
    assert '[ "$rc" = 0 ] || D1_G=$rc' in k
    v = _body("gate_drive1_verdict")
    assert v.find('rm -f "$PROJ/data/drive1_gates.json"') < v.find('python tools/drive1_gates.py "$PROJ"')
    assert '[ "$rc" = 0 ] || D1_G=$rc' in v and "force_install_ok" in v
    # 2026-10-12: a forced install needs the verdict; without it (a run whose road gates were red but which never
    # reached drive1_verdict) the default refuses
    assert "D1_FORCE_OK=1\n" not in TEXT
    assert _first("D1_FORCE_OK=0") < _first('for n in ${GATE[@]+"${GATE[@]}"}; do "gate_$n"; done')
    # the verdict: a forced install is refused when the run is worse than July
    blk = TEXT[_first('echo "  Drive-1 road gates'):_first('if [ "$DT_S" != 0 ]')]
    assert blk.find('if [ "$FORCE" = 1 ] && [ "$D1_FORCE_OK" != 1 ]; then') < blk.find('elif [ "$FORCE" = 1 ]; then')
    assert "--force-install refused" in blk


def test_the_fix_steps():
    k = _body("ship_verify_kn5_report")
    assert k.find('rm -f "$PROJ/data/verify_kn5.txt"') < k.find('python -m scripts.ac.verify_kn5 "$PROJ" >')
    assert 'echo "exit $rc" >> "$PROJ/data/verify_kn5.txt"' in k and "exit 1; }" in k      # still hard
    i = _body("ship_verify_inis_report")
    assert '--inis > "$PROJ/data/verify_inis.txt"' in i and "exit 1; }" in i
    u = _body("ship_ui_names")
    assert '"$UI_PREFIX" "$VARIANT" "$INSTALL_FOLDER"' in u and "drive1_build.json" in u and "chr(8212)" in u
    o = _body("author_overpass_decks")
    assert 'python tools/overpass_decks.py "$PROJ"' in o and '--python "$AIROSO/tools/author_overpass_blend.py"' in o
    assert "--python-exit-code 1" in o


def test_the_variant_is_wired_at_each_point_of_the_chain():
    assert 'VARIANT="${SHIP_VARIANT:-}"' in TEXT
    assert '-- "$PROJ" ${VARIANT:+--variant "$VARIANT"} 2>&1' in _body("draft_underlay")
    chk = _first("\nd4_variant_check ")
    assert _first('declare -F "gate_$n"') < chk < _first('step "sync inputs airoso -> workshop ($PROJ)"')
    app = _first("\nd4_variant_apply ")
    assert _first('INSTALL_FOLDER=$(pyq') < app < _first('case "$INSTALL_FOLDER" in ""|*[!A-Za-z0-9_]*)')
    grd = _first("\nd4_variant_guard ")
    assert _first('for n in ${AUTHOR[@]+"${AUTHOR[@]}"}; do "author_$n"; done') < grd < \
        _first('for n in "${PREP[@]}"; do "prep_$n"; done')
    assert 'if [ "$SCRATCH" = 1 ] || [ -n "$VARIANT" ]; then\n  step "sync outputs workshop -> airoso: SKIPPED"' in TEXT
    a = _body("d4_variant_apply")
    assert "INSTALL_FOLDER=" in a and "UI_PREFIX=" in a


def _run(args, env_extra):
    bash = shutil.which("bash")
    env = dict(os.environ, AIROSO=ROOT.as_posix(), **env_extra)
    for k in ("SHIP_PROJ", "SHIP_SPEC", "SHIP_VARIANT"):
        if k not in env_extra:
            env.pop(k, None)
    return subprocess.run([bash, str(SH), *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env, cwd=tempfile.mkdtemp(), timeout=240)


def test_an_unknown_variant_exits_2_before_anything_is_touched():
    if not shutil.which("bash"):
        print("  (no bash on PATH — skipped)")
        return
    proj = Path(tempfile.mkdtemp()) / "proj"
    for var, needle in (("c_wide", "is not in track.config.json drive1_variants"), ("b-verge;x", "is not a variant id")):
        r = _run(["lookout-lariat", "--skip-blend", "--dry-run"], {"SHIP_PROJ": proj.as_posix(), "SHIP_VARIANT": var})
        assert r.returncode == 2, (var, r.returncode, r.stdout[-400:], r.stderr[-400:])
        assert needle in r.stdout + r.stderr, (var, r.stdout[-400:], r.stderr[-400:])
        assert not proj.exists() and "sync inputs" not in r.stdout


def _rehearsal_spec(tmp: Path) -> Path:
    d = json.loads(SPEC.read_text(encoding="utf-8"))
    d["steps"]["author"] = []                      # no layout_dummies: the guard is what this run reaches
    p = tmp / "ship.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    return p


def test_a_blend_drafted_for_the_other_edge_is_refused_before_the_prep():
    if not shutil.which("bash"):
        print("  (no bash on PATH — skipped)")
        return
    tmp = Path(tempfile.mkdtemp())
    sp = _rehearsal_spec(tmp)
    proj = tmp / "proj"
    (proj / "data").mkdir(parents=True)
    (proj / "loop.blend").write_bytes(b"not a blend")       # never opened: the guard stops first
    (proj / "data" / "underlay.json").write_text(json.dumps({"variant": None, "verge": {"width_m": 0.4}}), encoding="utf-8")
    env = {"SHIP_PROJ": proj.as_posix(), "SHIP_SPEC": sp.as_posix(), "SHIP_VARIANT": "b_verge"}
    r = _run(["lookout-lariat", "--skip-blend", "--dry-run"], env)
    assert r.returncode == 1, (r.returncode, r.stdout[-800:], r.stderr[-800:])
    out = r.stdout + r.stderr
    assert "D4 variant b_verge: install folder lookout_lariat_v3_verge" in out, out[-800:]
    assert "loop.blend carries a 0.4 m verge" in out and "this run builds 1.25 m (b_verge)" in out, out[-800:]
    assert "ship: prep" not in out
    (proj / "data" / "underlay.json").unlink()
    r = _run(["lookout-lariat", "--skip-blend", "--dry-run"], env)
    assert r.returncode == 1 and "nothing says which edge loop.blend carries" in r.stdout + r.stderr, r.stdout[-600:]
