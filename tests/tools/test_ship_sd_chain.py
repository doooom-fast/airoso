"""tools/ship_sd.sh — the three-version chain's order and safety rails (ledger 0047), pinned on the
script text: every stage in the order the handoffs fixed, every Blender call with --python-exit-code 1,
the gates on the right OBJ, the packer/verifier repointed to airoso, set_start gone, the race gate OBJ
never named track_*.obj; SHIP_PROJ isolation (every step on the absolute "$PROJ", the sync-back and the
install unreachable from a scratch project); the street AI default (`draft`, July opt-in). bash itself
runs only for `bash -n` and the argument guards, which exit 2 before the first file operation.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SH = ROOT / "tools" / "ship_sd.sh"
TEXT = SH.read_text(encoding="utf-8")


def _first(marker: str) -> int:
    i = TEXT.find(marker)
    assert i >= 0, f"{marker!r} not in ship_sd.sh"
    return i


def test_stage_order():
    order = [
        'rm -f "$PROJ/data/no_route.$lid.planned.json" "$PROJ/data/no_route.$lid.json"',
        'tools/barrier_bands.py "$PROJ"',
        "no_route.%s.planned.json",
        'tools/layout_dummies.py "$PROJ"',
        "tools/author_race_furniture_blend.py",
        'tools/verify_race.py "$PROJ"',
        "tools/plot_race_furniture.py",
        "scripts/ac/build_kn5_loop.py",
        "tools/split_exports_blend.py",
        'loop_closure_$lid.blend" ] ||',
        "DRY RUN: stopping before the kn5 exports",
        '--blend "$PROJ/blender/split/loop_main.blend"',
        '--blend "$PROJ/blender/split/loop_race.blend" --out "${SLUG}_race.kn5"',
        'inspect_kn5 "$PROJ/build/${SLUG}_race.kn5" --json "$PROJ/data/race_kn5.json"',
        'tools/check_race_kn5.py "$PROJ/data/race_kn5.json" --role common --bands "$PROJ/data/barrier_bands.json"',
        "['corridors'][sys.argv[2]]['token']",
        '--blend "$PROJ/blender/split/loop_closure_$lid.blend" --out "${SLUG}_closure_$lid.kn5"',
        'inspect_kn5 "$PROJ/build/${SLUG}_closure_$lid.kn5" --json "$PROJ/data/closure_$lid.kn5.json"',
        'tools/check_race_kn5.py "$PROJ/data/closure_$lid.kn5.json" --role closure --owner "$tok"',
        "scripts/ac/build_spawn_kn5.py",
        'step "ship: AI lines per layout',
        'kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5" --kn5 "$PROJ/build/${RK[$lid]}"',
        "scripts.ac.write_ai_line",
        'tools/verify_ai_line.py "$PROJ" --layout "$lid"',
        '(cd "$AIROSO" && python -m scripts.ac.verify_kn5 "$PROJ")',
        'rm -f "$PROJ/data/track.race.obj" "$PROJ/data/audit.race.json"',
        'kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5" $STREET_KN5)',
        "scripts.ac.track_folder",
        'cp "$PROJ/build/$SLUG.kn5" "$PROJ/build/$SLUG/"',
        '(cd "$AIROSO" && python -m scripts.ac.verify_kn5 "$PROJ" --inis)',
        "tools/make_map.py",
        "tools/make_treefx.py",
        'tools/verify_race.py "$PROJ" --scenery-only --trees "$PROJ/build/$SLUG/extension/trees/trees.txt"',
        'tools/verify_mouths.py "$PROJ"',
        'drive_test "$PROJ" --layout street',
        'audit_mesh "$PROJ" 2>&1',
        'step "gate: $lid — road + common race + ITS closure kn5 -> ONE gate OBJ',
        'drive_test "$PROJ" --layout "$lid"',
        'audit_mesh "$PROJ" --layout "$lid"',
        'tools/no_route.py "$PROJ" --layout "$lid"',
        'rm -f "$PROJ/data/verify_fold_fans.json"',
        'tools/verify_fold_fans.py "$PROJ"',
        'python -m scripts.ac.kn5_ground_check "$PROJ" $KX --json "$PROJ/data/kn5_ground_check.$lid.json"',
        "RACE_RED=$(pyq",
        "sync outputs workshop -> airoso",
        "NOT INSTALLED: race layout(s)",
        "install: $AC/${SLUG}_v3",
        'glob.glob(r"$AC/${SLUG}_v3/ui/*/ui_track.json")',
    ]
    pos = [_first(m) for m in order]
    assert pos == sorted(pos), [m for m, p, q in zip(order, pos, sorted(pos)) if p != q]


def test_race_corridor_chain_ledger_0049():
    """ledger 0049: each race layout loads road + common race + ITS OWN closure kn5; every per-layout gate runs
    on that layout's own gate OBJ; the 0047 shared race OBJ / audit are retired; the planned containment is read
    back before Blender; the BUILT no_route runs per race layout and decides the install"""
    import re
    code = "\n".join(ln for _, ln in _code_lines())
    # retired: the one shared race gate OBJ / audit (road + centre chain) — removed, never produced or synced
    assert '--out "$PROJ/data/track.race.obj"' not in code and "--obj track.race.obj" not in code
    assert "audit.race.json" not in code.replace('rm -f "$PROJ/data/track.race.obj" "$PROJ/data/audit.race.json"', "") \
        .replace('rm -f "$SRC/data/audit.race.json"', "")
    # the race gates loop over the declared race layouts, one OBJ each, all three kn5s
    loop = TEXT[_first('for lid in $RACE_IDS; do\n  step "gate: $lid'):_first("RACE_RED=$(pyq")]
    for frag in ("kn5_to_gate_obj", "drive_test", "audit_mesh", "tools/no_route.py", "|| rc=$?"):
        assert frag in loop, frag
    assert "--no-planned-route" not in code, "the ship never skips the planned containment fill"
    # the closure export is per race layout and content-checked against the DECLARED token
    exp = TEXT[_first("for lid in $RACE_IDS; do\n  # the owner token"):_first("scripts/ac/build_spawn_kn5.py")]
    assert "export_kn5_addon.py" in exp and "--python-exit-code 1" in exp and "--role closure --owner" in exp
    # the stale per-layout verdicts go before the gates that rewrite them
    clear = _first('for lid in $LAYOUT_IDS; do rm -f "$PROJ/data/drive_test.$lid.json"; done')
    assert clear < _first('drive_test "$PROJ" --layout street')
    assert _first('"$PROJ/data/no_route.$lid.json" "$PROJ/data/track.$lid.obj"') < _first('tools/no_route.py "$PROJ" --layout "$lid"')
    # RACE_RED keys on the declared race ids (a layout missing from drive_test.json is red), no_route missing or failing
    red = TEXT[_first("RACE_RED=$(pyq"):_first('"$PROJ/data/drive_test.json" "$PROJ/data" $RACE_IDS)')]
    for frag in ("drive_test not run", "barrier_missing", "obstruction_stations", "no_route not run", "no_route FAIL",
                 "leak_cells", "blocked", "forbidden_reached", "spawns_unreached", "is not False"):
        assert frag in red, frag
    # RACE_RED is decided BEFORE (and independently of) --force-install
    assert _first('if [ -n "$RACE_RED" ]; then') < _first('elif [ "$FORCE" = 1 ]; then')
    assert re.search(r'\[ "\$NR_R" != 0 \]', TEXT)


def test_every_blender_call_carries_the_exit_code_flag():
    calls = [ln for ln in TEXT.splitlines() if '"$BL" --background' in ln and not ln.lstrip().startswith("#")]
    assert len(calls) >= 12, calls
    for ln in calls:
        assert "--python-exit-code 1" in ln, ln


def test_safety_rails():
    assert "set -euo pipefail" in TEXT
    assert "set_start_blend" not in TEXT, "the per-issue spawn now rides in layout_dummies --issue-spawn"
    assert "track_race.obj" not in TEXT, "the prep merges data/track_*.obj into the scene"
    assert '(cd "$ENG" && python -m scripts.ac.verify_kn5' not in TEXT and '(cd "$ENG" && python -m scripts.ac.track_folder' not in TEXT
    assert '(cd "$AIROSO" && python -m scripts.ac.verify_kn5 "$PROJ")' in TEXT
    assert '(cd "$AIROSO" && python -m scripts.ac.track_folder "$PROJ")' in TEXT
    assert 'cp "$JULY_AI/fast_lane.ai"' in TEXT and '"$B/ai/"' not in TEXT, "the July copy moved to the ship stage (root ai/ no longer exists)"
    assert "--allow-missing-kn5" not in TEXT, "the ship chain never packs with a missing kn5"
    assert 'WS_PROJ="$WS/project"' in TEXT and 'PROJ="${SHIP_PROJ:-$WS_PROJ}"' in TEXT
    # the race kn5 is judged on CONTENT (2026-10-11): the 20 MB size cap fired on a clean, flat-shaded kn5
    assert "RACE_BYTES" not in TEXT and "20000000" not in TEXT and "stat -c %s" not in TEXT, "size is not the race-kn5 gate"
    assert '(cd "$AIROSO" && python tools/check_race_kn5.py "$PROJ/data/race_kn5.json" --role common --bands "$PROJ/data/barrier_bands.json")' in TEXT
    # the five gate exits all decide the install, and a race-layout red is never forced
    assert '[ "$DT_S" != 0 ] || [ "$AU_S" != 0 ] || [ "$DT_R" != 0 ] || [ "$AU_R" != 0 ] || [ "$NR_R" != 0 ]' in TEXT
    assert 'if [ -n "$RACE_RED" ]; then' in TEXT
    # the race author runs on every ship (also with --skip-blend): it must sit OUTSIDE the SKIP_BLEND block
    fi_end = TEXT.find("\nfi\n", TEXT.find('if [ "$SKIP_BLEND" = 0 ]; then'))
    assert fi_end > 0 and TEXT.find("tools/author_race_furniture_blend.py") > fi_end


def test_sync_list_carries_the_new_outputs():
    for f in ("barrier_bands.json", "race_authored.json", "race_verify.json", "race_verify.scenery.json", "race_kn5.json",
              '"dummies_$lid.json"', '"drive_test.$lid.json"', '"$SRC/ai/$lid"', "race_plots", "split_manifest.json",
              '"no_route.$lid.json"', '"no_route.$lid.planned.json"', '"audit.$lid.json"', '"closure_$lid.kn5.json"'):
        assert f in TEXT, f
    sync = TEXT[_first('step "sync outputs workshop -> airoso"\n'):_first("never synced.\nfi\n")]
    assert "track.$lid.obj" not in sync and "track.race.obj" not in sync, "gate OBJs (66-78 MB) are never synced"


def test_bash_syntax():
    bash = shutil.which("bash")
    if not bash:
        print("  (no bash on PATH — syntax check skipped)")
        return
    r = subprocess.run([bash, "-n", str(SH)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def _code_lines():
    """(offset into TEXT, line) for every non-comment line"""
    out, pos = [], 0
    for ln in TEXT.splitlines(keepends=True):
        if not ln.lstrip().startswith("#"):
            out.append((pos, ln.rstrip("\n")))
        pos += len(ln)
    return out


def test_every_step_runs_on_the_absolute_project():
    """(a) no relative `project` argument (after cd "$WS" or anywhere), no "$WS/project" literal except
    WS_PROJ's one definition — which only the PROJ default, the SCRATCH test and messages read"""
    import re
    code = _code_lines()
    rel = [ln for _, ln in code if not ln.lstrip().startswith(("echo", "step"))
           and (re.search(r"--\s+project(\s|$|\))", ln) or re.search(r"\s(\./)?project(/\S*)?(\s|$|\))", ln))]
    assert not rel, ("relative project argument", rel)
    ws_lit = [ln for _, ln in code if "$WS/project" in ln]
    assert ws_lit == ['WS_PROJ="$WS/project"        # the real workshop project: the ONLY spelling of it in this script'], ws_lit
    for _, ln in code:
        if "$WS_PROJ" in ln and not ln.startswith("WS_PROJ="):
            assert ln.startswith(('PROJ="${SHIP_PROJ:-$WS_PROJ}"', 'if [ "$(norm "$PROJ")" = "$(norm "$WS_PROJ")" ]')) or \
                ln.lstrip().startswith(("echo", "step")), ln
    # every tool invocation (Blender or python) is handed the project as "$PROJ..."
    steps = [ln for _, ln in code if '"$BL" --background' in ln or re.search(r"python (tools/|-m scripts\.)", ln)]
    assert len(steps) >= 30, len(steps)
    for ln in steps:
        assert '"$PROJ' in ln, ln
    # the assembler of record is airoso's scripts-v021, its `scripts` package registered by V021_SHIM (ledger 0046)
    blb = [ln for _, ln in code if "build_loop_blend.py" in ln and '"$BL"' in ln]
    assert len(blb) == 2, blb
    for ln in blb:
        assert '--python-expr "$V021_SHIM" --python "$V021/blender/build_loop_blend.py" -- "$PROJ"' in ln, ln
    assert 'V021="$SRC/scripts-v021"' in TEXT and "WS_SYSPATH" not in TEXT
    # the guards: absolute, outside airoso, scratch derived from the workshop path, all before the first copy
    assert "/*|[A-Za-z]:/*|" in TEXT and '"$(norm "$AIROSO")"|"$(norm "$AIROSO")"/*)' in TEXT
    assert 'if [ "$(norm "$PROJ")" = "$(norm "$WS_PROJ")" ]; then SCRATCH=0; else SCRATCH=1; fi' in TEXT
    first_copy = _first('cp "$SRC/track.config.json" "$PROJ/track.config.json"')
    for g in ("must be an absolute path", "is inside airoso", "SCRATCH=1; fi", "no assembler at"):
        assert _first(g) < first_copy, g


def test_sync_back_and_install_are_unreachable_from_a_scratch_project():
    """(b) every write into airoso ($SRC) sits in the sync block's NON-scratch branch; every write into
    the AC folder sits in the install block's NON-scratch branch"""
    import re
    skip_sync = _first('step "sync outputs workshop -> airoso: SKIPPED"')
    else_sync = _first('else\nstep "sync outputs workshop -> airoso"\n')
    end_sync = _first("# track.obj / track.<id>.obj are 66-78 MB each and regenerable from the kn5s: never synced.\nfi\n")
    guard = TEXT.rfind('if [ "$SCRATCH" = 1 ]; then\n', 0, skip_sync)
    assert guard >= 0 and TEXT.find("\nfi\n", guard) > end_sync - 1, "the SKIPPED branch and the sync share one if/else"
    assert skip_sync < else_sync < end_sync
    n_src = 0
    for pos, ln in _code_lines():
        # a copy/move whose DESTINATION is under $SRC (the sync-inputs copies read $SRC and write $PROJ)
        writes_src = re.search(r'\b(cp|mv)( -r)? "[^"]*" "\$SRC', ln) or 'rm -rf "$SRC' in ln or 'mkdir -p "$SRC' in ln
        if writes_src:
            n_src += 1
            assert else_sync < pos < end_sync, ("airoso write outside the guarded sync", ln)
    assert n_src >= 6, n_src
    skip_inst = _first('if [ "$INSTALL" = 1 ] && [ "$SCRATCH" = 1 ]; then')
    real_inst = _first('elif [ "$INSTALL" = 1 ]; then')
    assert skip_inst < real_inst
    n_ac = 0
    for pos, ln in _code_lines():
        words = ln.replace(";", " ").split()
        if any(w in ("cp", "mv", "rm", "mkdir") for w in words) and ('"$AC/' in ln or '"$ARCHIVE/' in ln):
            n_ac += 1
            assert pos > real_inst, ("AC / archive write outside the guarded install", ln)
    assert n_ac >= 2, n_ac                     # lines: park the previous build (mkdir + mv) + the copy
    assert _first("python - <<PY") > real_inst  # the ui_track.json name patch writes into the installed folder


def test_street_ai_defaults_to_the_v3_draft_and_july_is_an_opt_in_draft():
    import re
    assert 'STREET_AI="${STREET_AI:-draft}"' in TEXT
    assert 'case "$STREET_AI" in draft|july) ;;' in TEXT
    july = TEXT[_first('if [ "$STREET_AI" = july ]; then'):_first("scripts.ac.verify_kn5")]
    assert 'cp "$JULY_AI/fast_lane.ai"' in july
    # the July line is a July write_ai_line DRAFT: "recording" only ever appears negated
    hits = list(re.finditer("recording", TEXT))
    assert hits
    for m in hits:
        ctx = TEXT[max(0, m.start() - 60):m.start()].lower()
        assert "in-game" in ctx and ("not an" in ctx or "never an" in ctx), TEXT[m.start() - 60:m.end()]


def test_argument_guards_exit_2_before_any_file_operation():
    import os
    import tempfile
    bash = shutil.which("bash")
    if not bash:
        print("  (no bash on PATH — guard run skipped)")
        return
    cwd = tempfile.mkdtemp()
    inside = (ROOT / "tracks" / "_never_a_scratch_project").as_posix()
    cases = [({"STREET_AI": "bogus"}, "STREET_AI must be draft or july"),
             ({"SHIP_PROJ": "scratch/project"}, "must be an absolute path"),
             ({"SHIP_PROJ": inside}, "is inside airoso")]
    if os.name == "nt":   # any Windows spelling of it (C:\USERS\...); on POSIX a backslash path is simply not absolute
        cases.append(({"SHIP_PROJ": inside.upper().replace("/", "\\")}, "is inside airoso"))
    for extra, msg in cases:
        env = dict(os.environ, AIROSO=ROOT.as_posix(), **extra)   # the guard compares against this checkout, wherever it lives
        r = subprocess.run([bash, str(SH), "--dry-run", "--no-install"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env, cwd=cwd, timeout=60)
        assert r.returncode == 2, (extra, r.returncode, r.stdout[-400:], r.stderr[-400:])
        assert msg in r.stdout, (extra, r.stdout[-400:])
        assert "sync inputs" not in r.stdout
    assert os.listdir(cwd) == []
    assert not Path(inside).exists()


def test_previous_build_is_parked_outside_content_tracks():
    """Kevin 2026-10-11 "clear old versions": a same-named _v3_prev inside content/tracks showed up in
    Content Manager as a second "K10 - San Diego (V3)"; the install parks it in the archive instead."""
    install = TEXT[_first('step "install: $AC/${SLUG}_v3'):]
    assert 'mv "$AC/$old" "$ARCHIVE/$STAMP/$old"' in install
    assert 'mv "$AC/${SLUG}_v3" "$AC/${SLUG}_v3_prev"' not in TEXT
    assert 'ARCHIVE="D:/k10-track-archive"' in TEXT


def test_race_kn5_guard_is_a_content_check():
    """tools/check_race_kn5.py (the step after the race export): RACE meshes only, the race textures only
    (read from scripts/ac/pbr.py's 1WALL_RACE / 1KERB_RACE rows), no AC_* node; size only WARNS"""
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import check_race_kn5 as ck
    sys.path.insert(0, str(ROOT))
    from scripts.ac import pbr
    allowed = ck.race_texture_set()
    assert allowed == {"kerb_race_worn_diffuse.jpg", "kerb_race_worn_normal.jpg", "concrete_barrier_diffuse.png", "concrete_barrier_normal.png"}
    assert allowed == {f for k, row in pbr.TEXTURES.items() if k.startswith(("1WALL_RACE", "1KERB_RACE")) for f in row[:2] if f}
    assert ck.race_texture_set({"1WALL_RACE": ("a.png", "b.png"), "1WALL": ("c.png", None), "1KERB_RACE": ("d.png", None)}) == {"a.png", "b.png", "d.png"}
    clean = {"file_bytes": 35_553_024, "nodes": ["BlenderFile"],
             "textures": [{"name": t} for t in sorted(allowed)],
             "meshes": [{"name": "1WALL_race_kbar_navajo_2297_0", "verts": 12000, "tris": 14316},
                        {"name": "1KERB_race_770_out", "verts": 2100, "tris": 2094}]}
    r = ck.check(clean, allowed)
    assert r["ok"] and r["fails"] == [], r
    assert len(r["warns"]) == 1 and "35,553,024" in r["warns"][0]          # big: a WARN, not a FAIL
    assert r["summary"]["meshes"] == 2 and r["summary"]["verts"] == 14100 and r["summary"]["tris"] == 16410
    small = dict(clean, file_bytes=9_000_000)
    assert ck.check(small, allowed) == dict(ck.check(small, allowed), ok=True, warns=[])
    leaks = [
        (dict(clean, meshes=clean["meshes"] + [{"name": "1ROAD_road", "verts": 9, "tris": 3}]), "non-race meshes"),
        (dict(clean, textures=clean["textures"] + [{"name": "asphalt_cracked_diffuse.jpg"}]), "textures outside the race set"),
        (dict(clean, nodes=["BlenderFile", "AC_START_0"]), "AC_* nodes"),
        (dict(clean, meshes=[]), "no mesh"),
        ({k: v for k, v in clean.items() if k != "nodes"}, "no transform-node list"),
    ]
    for parsed, msg in leaks:
        r = ck.check(parsed, allowed)
        assert not r["ok"] and any(msg in f for f in r["fails"]), (msg, r["fails"])


def test_scenery_gate_judges_the_written_trees_and_is_hard():
    """0049 fix round: after make_treefx writes trees.txt, verify_race --scenery-only judges THAT file (TreeFX trunks
    and sign posts vs each race layout's lane and walls) — a plain step under set -e, never softened"""
    line = next(ln for _, ln in _code_lines() if 'python tools/verify_race.py "$PROJ" --scenery-only' in ln)
    assert '--trees "$PROJ/build/$SLUG/extension/trees/trees.txt"' in line
    assert "|| true" not in line and "|| rc" not in line and "tail" not in line, line
    assert (_first('python tools/make_treefx.py "$PROJ"') < _first('python tools/verify_race.py "$PROJ" --scenery-only')
            < _first('tools/verify_mouths.py "$PROJ"'))


def test_install_refuses_while_ac_runs_and_lets_content_manager_stay_open():
    """the install parks the old folder with mv: Assetto Corsa holding it makes that fail half-way, so the REAL
    install refuses while acs.exe runs (the scratch path never reaches it). Content Manager may stay open — Kevin,
    2026-10-27: "you can install when that's running just not while AC is driving the track" (CM does not lock the
    track files); until 2026-10-29 it was refused too."""
    real_inst = _first('elif [ "$INSTALL" = 1 ]; then')
    guard = _first("tasklist //FO CSV //NH")
    park = _first('mv "$AC/$old"')
    assert real_inst < guard < park
    blk = TEXT[guard:park]
    for frag in ("acs[.]exe", "acs_x86[.]exe", "NOT INSTALLED: close", "exit 1", "Content Manager may stay open"):
        assert frag in blk, frag
    assert "Content Manager[^\"]*[.]exe" not in blk


def test_install_folder_is_one_name_in_the_config_and_the_chain():
    # track_folder names the install folder in README.txt from track.config.json `install_folder`; the
    # chain installs as "${SLUG}_v3" — the two must stay one name (0047 fix round, finding E: the
    # installed README named <slug>, the wrong folder)
    import json
    cfg = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json").read_text(encoding="utf-8"))
    slug = cfg["slug"]
    assert 'SLUG="%s"' % slug in TEXT
    assert cfg["install_folder"] == f"{slug}_v3"
    assert 'cp -r "$B" "$AC/${SLUG}_v3"' in TEXT


def _pyq_program(start: str, end: str) -> str:
    """the python program of a `pyq "<program>" <args>` call: the text between the opening quote after `start`
    and the closing quote before `end` (the programs hold no shell expansion: no $, no backslash, no ")"""
    i = _first(start) + len(start)
    j = TEXT.index(end, i)
    prog = TEXT[i:j]
    assert prog.startswith('pyq "') or start.endswith('pyq "'), prog[:40]
    prog = prog[len('pyq "'):] if prog.startswith('pyq "') else prog
    assert prog.endswith('"'), prog[-40:]
    prog = prog[:-1]
    assert "$" not in prog and "\\" not in prog and '"' not in prog, "the program would be altered by bash"
    return prog


def _run_prog(prog, *args):
    import sys
    return subprocess.run([sys.executable, "-c", prog, *args], capture_output=True, text=True, encoding="utf-8")


def test_race_red_turns_red_on_every_own_gate_and_stays_quiet_on_a_clean_build():
    """RACE_RED, run as the script runs it, on crafted verdict files: a race layout is red when its drive_test row
    is missing / not run / has barrier_missing or obstruction_stations, or its BUILT no_route verdict is missing,
    fails, or reports a leak / block / reached probe / unreached spawn — and the street layout never counts"""
    import json
    import tempfile
    prog = _pyq_program("RACE_RED=$(", ' "$PROJ/data/drive_test.json" "$PROJ/data" $RACE_IDS)')
    d = Path(tempfile.mkdtemp())
    ok_dt = {"fail": True, "barrier_missing": 0, "obstruction_stations": 0}      # inherited counters: fail True
    ok_nr = {"fail": False, "leak_cells": 0, "blocked": [], "forbidden_reached": [], "spawns_unreached": []}

    def case(rows, nr: dict):
        for f in d.glob("*.json"):
            f.unlink()
        if rows is not None:
            (d / "drive_test.json").write_text(json.dumps({"layouts": rows}), encoding="utf-8")
        for lid, v in nr.items():
            if v is not None:
                (d / f"no_route.{lid}.json").write_text(json.dumps(v), encoding="utf-8")
        r = _run_prog(prog, str(d / "drive_test.json"), str(d), "race_cw", "race_acw")
        assert r.returncode == 0, r.stderr
        return r.stdout.strip()

    street_red = {"fail": True, "barrier_missing": 9, "obstruction_stations": 9}
    clean = {"street": street_red, "race_cw": ok_dt, "race_acw": ok_dt}
    assert case(clean, {"race_cw": ok_nr, "race_acw": ok_nr}) == ""
    assert case(dict(clean, race_cw=dict(ok_dt, fail=False)), {"race_cw": ok_nr, "race_acw": ok_nr}) == ""
    red = [
        (dict(clean, race_cw=dict(ok_dt, barrier_missing=3)), {}, "race_cw[barrier_missing 3]"),
        (dict(clean, race_acw=dict(ok_dt, obstruction_stations=1)), {}, "race_acw[obstruction_stations 1]"),
        ({"street": street_red, "race_acw": ok_dt}, {}, "race_cw[drive_test not run]"),
        (dict(clean, race_cw={"fail": None, "note": "not run"}), {}, "race_cw[drive_test not run]"),
        (clean, {"race_acw": None}, "race_acw[no_route not run]"),
        (clean, {"race_cw": dict(ok_nr, fail=True)}, "race_cw[no_route FAIL"),
        (clean, {"race_cw": dict(ok_nr, leak_cells=12)}, "race_cw[no_route FAIL (leak_cells 12"),
        (clean, {"race_acw": dict(ok_nr, blocked=[[5, 9]])}, "race_acw[no_route FAIL"),
        (clean, {"race_cw": dict(ok_nr, forbidden_reached=[{"vertex": 1}])}, "race_cw[no_route FAIL"),
        (clean, {"race_cw": dict(ok_nr, spawns_unreached=["AC_PIT_3"])}, "race_cw[no_route FAIL"),
        (clean, {"race_cw": {k: v for k, v in ok_nr.items() if k != "fail"}}, "race_cw[no_route FAIL"),
    ]
    for rows, nr_over, want in red:
        nr = {"race_cw": ok_nr, "race_acw": ok_nr}
        nr.update(nr_over)
        out = case(rows, nr)
        assert want in out, (want, out)
    assert case(None, {"race_cw": ok_nr, "race_acw": ok_nr}) == \
        "race_cw[drive_test not run] race_acw[drive_test not run]"           # no drive_test.json at all


def test_planned_no_route_read_back_stops_the_chain_before_blender():
    """the PLANNED read-back (after barrier_bands, before the author): exit nonzero unless every race layout has a
    data/no_route.<id>.planned.json with fail false and nothing reached / blocked / unreached"""
    import json
    import tempfile
    prog = _pyq_program('# that skipped or lost its planned fill cannot reach Blender.\n', ' "$PROJ/data" $RACE_IDS')
    d = Path(tempfile.mkdtemp())
    ok = {"fail": False, "leak_cells": 0, "blocked": [], "forbidden_reached": [], "spawns_unreached": [], "reached_m2": 139130}

    def run(files):
        for f in d.glob("*.json"):
            f.unlink()
        for lid, v in files.items():
            (d / f"no_route.{lid}.planned.json").write_text(json.dumps(v), encoding="utf-8")
        return _run_prog(prog, str(d), "race_cw", "race_acw")

    r = run({"race_cw": ok, "race_acw": ok})
    assert r.returncode == 0 and "race_cw   planned: PASS" in r.stdout, (r.stdout, r.stderr)
    for files, msg in (({"race_cw": ok}, "race_acw: no planned verdict"),
                       ({"race_cw": ok, "race_acw": dict(ok, fail=True)}, "race_acw: planned no_route FAIL"),
                       ({"race_cw": dict(ok, leak_cells=4), "race_acw": ok}, "race_cw: planned no_route FAIL"),
                       ({"race_cw": dict(ok, blocked=[[1, 2]]), "race_acw": ok}, "race_cw: planned no_route FAIL"),
                       ({"race_cw": "skipped", "race_acw": ok}, "race_cw: the planned verdict is not a no_route report")):
        r = run(files)
        assert r.returncode != 0, (files, r.stdout)
        assert msg in r.stderr, (msg, r.stderr[-300:])


def test_mouth_weld_and_its_gate_are_wired():
    """2026-10-11 side-street mouths: the weld runs right after the trimmed-connector rebuild and before the seat (the
    seat reads the WELDED deck), with the workshop on sys.path (it rebuilds each connector block with the assembler's
    own ribbon module) and the exit-code flag; verify_mouths judges the BUILT road right after its gate OBJ, hard
    (set -e: no `|| rc`), its stale verdict removed first; both reports sync back; AIROSO is overridable for a
    worktree rehearsal and defaults to the main checkout"""
    assert 'AIROSO="${AIROSO:-C:/Users/Owner/Documents/GitHub/airoso}"' in TEXT
    blb = [p for p, ln in _code_lines() if "build_loop_blend.py" in ln and '"$BL"' in ln]
    weld = [(p, ln) for p, ln in _code_lines() if "weld_mouths_blend.py" in ln]
    assert len(weld) == 1, weld
    wpos, wln = weld[0]
    assert blb[1] < wpos < _first("tools/seat_terrain_blend.py"), "the weld sits between the rebuild and the seat"
    for frag in ('--python-exit-code 1', '--python-expr "$V021_SHIM"', '--python "$AIROSO/tools/weld_mouths_blend.py" -- "$PROJ"'):
        assert frag in wln, frag
    skip = TEXT.find('if [ "$SKIP_BLEND" = 0 ]; then')
    assert skip < wpos < TEXT.find("\nfi\n", skip), "the weld is a draft step (skipped with --skip-blend)"
    vm = [(p, ln) for p, ln in _code_lines() if "tools/verify_mouths.py" in ln]
    assert len(vm) == 1 and vm[0][1].strip() == '(cd "$AIROSO" && python tools/verify_mouths.py "$PROJ")', vm
    vpos = vm[0][0]
    assert _first('rm -f "$PROJ/data/verify_mouths.json"') < _first('kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5" $STREET_KN5)') \
        < vpos < _first('drive_test "$PROJ" --layout street')
    sync = TEXT[_first('step "sync outputs workshop -> airoso"\n'):_first("never synced.\nfi\n")]
    assert "mouth_welds.json" in sync and "verify_mouths.json" in sync


def test_tiered_terrain_chain_ledger_0046():
    """ledger 0046: the sampler plans + fetches before EACH assembler run (the trimmed connectors re-plan the verge),
    the far-terrain decimation is gone, the 3DEP cache and the I-8 corridor ride the sync both ways (data with
    provenance, L2), ENG is overridable for a scratch rehearsal, and the road gate OBJ exists before the track folder
    reads its mesh names (GrassFX lists, TreeFX SURFACE_MATERIALS)"""
    code = _code_lines()
    blb = [p for p, ln in code if "build_loop_blend.py" in ln and '"$BL"' in ln]
    samp = [p for p, ln in code if 'python -m scripts.elevation.terrain_sample "$PROJ"' in ln]
    assert len(samp) == 2 and samp[0] < blb[0] < samp[1] < blb[1], (samp, blb)
    assert _first("tools/trim_connectors.py") < samp[1]
    assert "slim_far_terrain_blend" not in TEXT and not (ROOT / "tools" / "slim_far_terrain_blend.py").exists()
    # ...but the triangulation it applied to every terrain face stays, at the same point (after the seat, before
    # the median island joins TERRAIN): the near-road ground every gate was tuned on is that triangulation's
    tri = _first('--python "$AIROSO/tools/triangulate_terrain_blend.py" -- "$PROJ"')
    assert _first("tools/seat_terrain_blend.py") < tri < _first("tools/author_median_blend.py")
    src = (ROOT / "tools" / "triangulate_terrain_blend.py").read_text(encoding="utf-8")
    assert 'quad_method="BEAUTY"' in src and "vertex count changed" in src
    assert 'ENG="${ENG:-C:/Users/Owner/Documents/GitHub/engine-july}"' in TEXT
    assert ('TERRAIN_DATA="terrain.samples.json.gz corridor.i8.json i8.local.json i8.legacy.local.json '
            'deck_datum.samples.json ground_release.samples.json.gz freeway_i8.samples.json.gz"') in TEXT
    down = TEXT[_first('step "sync inputs airoso -> workshop'):_first("LAYOUT_IDS=$(pyq")]
    assert "for f in $TERRAIN_DATA; do" in down and 'cp "$SRC/data/$f" "$PROJ/data/$f"' in down
    sync = TEXT[_first('step "sync outputs workshop -> airoso"\n'):_first("never synced.\nfi\n")]
    assert "$TERRAIN_DATA terrain.tiers.report.json" in sync and "terrain.tiers.json.gz" not in sync
    assert _first('kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5" $STREET_KN5)') < _first("scripts.ac.track_folder") \
        < _first("tools/make_treefx.py")


def test_deck_datum_ground_release_and_freeway_chain_0046_integration():
    """ledger 0046 v0.18.0 integration fix round: the deck datum edits the pre-median centreline before median_envelope
    re-derives from it; the near-road ground is released (python plan, then Blender) after the BEAUTY triangulation and
    before the median island and the bridge bodies that read it; the I-8 pavement is draped on the PREPPED scene, after
    the prep and before the split, binding engine-july's pbr through --eng; their 3DEP caches cross the sync both ways"""
    dd = _first('(cd "$AIROSO" && python tools/deck_datum.py "$PROJ")')
    assert dd < _first('(cd "$AIROSO" && python tools/median_envelope.py "$PROJ")')
    assert _first('step "sync inputs airoso -> workshop') < dd
    gr = _first('(cd "$AIROSO" && python tools/ground_release.py "$PROJ")')
    grb = _first('--python "$AIROSO/tools/ground_release_blend.py" -- "$PROJ"')
    assert _first('--python "$AIROSO/tools/triangulate_terrain_blend.py" -- "$PROJ"') < gr < grb \
        < _first("tools/author_median_blend.py") < _first("tools/author_bridges_blend.py")
    fw = _first('(cd "$AIROSO" && python tools/freeway_i8.py "$PROJ")')
    fwb = _first('--python "$AIROSO/tools/author_freeway_blend.py" -- "$PROJ" --eng "$ENG"')
    assert _first('--python "$ENG/scripts/ac/build_kn5_loop.py"') < fw < fwb < _first("tools/split_exports_blend.py")
    assert fwb < _first('echo; echo "DRY RUN: stopping before the kn5 exports')
    sync = TEXT[_first('step "sync outputs workshop -> airoso"\n'):_first("never synced.\nfi\n")]
    for f in ("deck_datum.json", "ground_release.json", "ground_release.report.json", "freeway_i8.json",
              "freeway_i8.report.json"):
        assert f in sync, f


def test_v021_shim_resolves_the_assembler_package_not_the_engine():
    """the --python-expr V021_SHIM, run by plain Python: `scripts` becomes tracks/san-diego-lake-murray/scripts-v021, so
    the assembler's `from scripts.geometry import ribbon` (and weld_mouths_blend's) can only load that copy"""
    import re
    import subprocess
    import sys as _sys
    m = re.search(r'^V021_SHIM="(.*)"$', TEXT, re.M)
    assert m, "V021_SHIM definition"
    v021 = (ROOT / "tracks" / "san-diego-lake-murray" / "scripts-v021").as_posix()
    shim = m.group(1).replace("$V021", v021)
    prog = shim + "; import sys; sys.path.insert(0, r'" + ROOT.as_posix() + "'); from scripts.geometry import ribbon, smooth; " \
        "print(ribbon.__file__); print(smooth.__file__); print(sys.modules['scripts'].__file__)"
    r = subprocess.run([_sys.executable, "-c", prog], capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    for ln in r.stdout.split():
        assert Path(ln).resolve().as_posix().startswith(Path(v021).resolve().as_posix()), ln


def test_ai_writer_reads_the_built_race_obj_ledger_0052():
    """ledger 0052: the race writer (track.config.json "ai") seats the line on the BUILT walls and road of the kn5 set
    the layout loads and refuses a missing or stale OBJ — so each race layout's gate OBJ is extracted from road + common
    race + ITS closure kn5 right before the writer, after every export, and verify_ai_line judges the written line at
    once (hard, under set -e; no --baseline: the writer holds the box rule itself)"""
    ai = TEXT[_first('step "ship: AI lines per layout'):_first("for lid in $STREET_IDS; do\n  rm -rf")]
    obj = ai.index('(cd "$AIROSO" && python -m scripts.modkit.kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5" '
                   '--kn5 "$PROJ/build/${RK[$lid]}" --kn5 "$PROJ/build/${SLUG}_closure_$lid.kn5" '
                   '--out "$PROJ/data/track.$lid.obj")')
    assert obj < ai.index("scripts.ac.write_ai_line") < ai.index('python tools/verify_ai_line.py "$PROJ" --layout "$lid")')
    assert "for lid in $RACE_IDS; do" in ai and "--baseline" not in ai and "|| " not in ai.split("verify_ai_line.py")[1][:60]
    assert _first("scripts/ac/build_spawn_kn5.py") < _first('step "ship: AI lines per layout')
    sync = TEXT[_first('step "sync outputs workshop -> airoso"\n'):_first("never synced.\nfi\n")]
    assert '"ai_verify.$lid.json"' in sync
    import json
    cfg = json.loads((ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json").read_text(encoding="utf-8"))
    assert cfg["ai"]["layouts"] == ["race_cw", "race_acw"] and cfg["ai"]["surface"] == "gate_obj"


def test_fold_fans_gate_ledger_0050():
    """ledger 0050: verify_fold_fans reads every layout's BUILT gate OBJ, so it runs after the race gates wrote them,
    its stale verdict is removed first, it is hard (set -e: no `|| rc`), it comes before the install decision and its
    verdict is synced back"""
    i = _first('tools/verify_fold_fans.py "$PROJ"')
    assert _first('tools/no_route.py "$PROJ" --layout "$lid"') < _first('rm -f "$PROJ/data/verify_fold_fans.json"') < i \
        < _first("RACE_RED=$(pyq") < _first('elif [ "$FORCE" = 1 ]; then')
    line = TEXT[i:TEXT.index("\n", i)]
    assert "||" not in line, line
    sync = TEXT[_first('step "sync outputs workshop -> airoso"\n'):_first("never synced.\nfi\n")]
    assert "verify_fold_fans.json" in sync


def test_lap_groups_are_wired_and_inert_without_a_lap_ledger_0054():
    """ledger 0054 (phase 2 groundwork): a race layout may name its own LAP. The chain reads the laps and, per race
    layout, its common race kn5 (RK) and its declaration (BB) from scripts/geometry/race_lap.py — never a hand list;
    every per-layout step uses them; each lap's group is verified (--lap), exported (loop_race_<lap>.blend ->
    <slug>_race_<lap>.kn5), content-checked (--role common --lap) and synced. The mainline's steps run when a race
    layout still drives the mainline (HAS_MAIN) — on Lake Murray today: always, so the chain is the old one."""
    for frag in ("LAP_IDS=$(pyq", "L.lap_ids(", "HAS_MAIN=$(pyq", "L.groups(", "declare -A RK BB",
                 "L.bands_file(lap)", "'_race.kn5' if not lap else '_race_%s.kn5'%lap"):
        assert frag in TEXT, frag
    # every race gate OBJ (the AI writer's and the gate stage's) is road + RK + ITS closure
    assert TEXT.count('--kn5 "$PROJ/build/${RK[$lid]}" --kn5 "$PROJ/build/${SLUG}_closure_$lid.kn5"') == 2
    assert '--kn5 "$PROJ/build/${SLUG}_race.kn5" --kn5' not in TEXT
    # the closure token comes from the layout's OWN declaration
    assert "['corridors'][sys.argv[2]]['token'])\" \"$PROJ/data/${BB[$lid]}\" \"$lid\")" in TEXT
    # the lap groups: verify_race --lap (authored + scenery), the lap's split blend, export, inspect, check, sync
    for frag in ('tools/verify_race.py "$PROJ" --lap "$lap"',
                 'tools/verify_race.py "$PROJ" --scenery-only --lap "$lap" --trees',
                 '[ -f "$PROJ/blender/split/loop_race_$lap.blend" ] ||',
                 '--blend "$PROJ/blender/split/loop_race_$lap.blend" --out "${SLUG}_race_$lap.kn5"',
                 'inspect_kn5 "$PROJ/build/${SLUG}_race_$lap.kn5" --json "$PROJ/data/race_$lap.kn5.json"',
                 'check_race_kn5.py "$PROJ/data/race_$lap.kn5.json" --role common --lap "$lap" --bands "$PROJ/data/barrier_bands.$lap.json"',
                 'rm -f "$PROJ/build/${SLUG}_race_"*.kn5',
                 '"lap.$lap.json" "barrier_bands.$lap.json" "race_authored.$lap.json" "race_verify.$lap.json"'):
        assert frag in TEXT, frag
    # the mainline's own common kn5 + verify_race run under HAS_MAIN, in the old order
    assert _first('if [ "$HAS_MAIN" = 1 ]; then\n(cd "$AIROSO" && python tools/verify_race.py "$PROJ")') < \
        _first('tools/verify_race.py "$PROJ" --lap "$lap"')
    assert _first('if [ "$HAS_MAIN" = 1 ]; then\nstep "ship: export the COMMON race-furniture kn5') < \
        _first('--blend "$PROJ/blender/split/loop_race_$lap.blend"') < _first("for lid in $RACE_IDS; do\n  # the owner token")
    # the pyq programs, run on the real Lake Murray config: no lap, the mainline drives every race layout
    import json
    import subprocess
    import sys as _sys
    cfgp = ROOT / "tracks" / "san-diego-lake-murray" / "track.config.json"
    code = ("import json,sys\nfrom scripts.geometry import race_lap as L\nd=json.load(open(sys.argv[1],encoding='utf-8'))\n"
            "print(' '.join(L.lap_ids(d)), '|', 1 if None in L.groups(d) else 0)\n"
            "for lo in d['layouts']:\n    if lo.get('race_furniture'):\n        lap=L.lap_of(lo); "
            "print(lo['id'], d['slug']+('_race.kn5' if not lap else '_race_%s.kn5'%lap), L.bands_file(lap))")
    out = subprocess.run([_sys.executable, "-c", code, str(cfgp)], cwd=ROOT, capture_output=True, text=True, check=True)
    lines = out.stdout.strip().splitlines()
    assert lines[0].split() == ["|", "1"], lines
    slug = json.loads(cfgp.read_text(encoding="utf-8"))["slug"]
    assert lines[1:] == [f"race_cw {slug}_race.kn5 barrier_bands.json", f"race_acw {slug}_race.kn5 barrier_bands.json"]


def test_street_only_kn5_is_exported_checked_and_in_the_street_gate_obj_only():
    """ledger 0055: the median over a Speedway chicane's span ships in <slug>_street.kn5 (Free Roam only) — exported
    after the closures from loop_street.blend, content-checked, stale copies removed, and folded into data/track.obj
    (the street layout's kn5 set) but never into a race layout's gate OBJ"""
    order = ['rm -f "$PROJ/build/${SLUG}_street.kn5" "$PROJ/data/street_kn5.json"',
             'if [ -f "$PROJ/blender/split/loop_street.blend" ]; then',
             '--blend "$PROJ/blender/split/loop_street.blend" --out "${SLUG}_street.kn5"',
             'inspect_kn5 "$PROJ/build/${SLUG}_street.kn5" --json "$PROJ/data/street_kn5.json"',
             'python tools/check_street_kn5.py "$PROJ/data/street_kn5.json"',
             'STREET_KN5="--kn5 $PROJ/build/${SLUG}_street.kn5"',
             'kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5" $STREET_KN5)']
    pos = [_first(o) for o in order]
    assert pos == sorted(pos), list(zip(order, pos))
    assert _first('--out "${SLUG}_closure_$lid.kn5"') < pos[2] < _first("scripts/ac/build_spawn_kn5.py")
    race_obj = [ln for ln in TEXT.splitlines() if '--out "$PROJ/data/track.$lid.obj"' in ln]
    assert race_obj and not any("STREET_KN5" in ln or "_street.kn5" in ln for ln in race_obj)
    assert "street_kn5.json" in TEXT.split('step "sync outputs workshop -> airoso"')[1]


def test_kn5_ground_check_runs_per_layout_on_its_kn5_set_repair_round_1():
    """ledger 0054 P3 repair round 1 (the gates lens: EXPANSION-PLAN V5 lists kn5_ground_check on all three layouts and
    neither chain ran it): after the fold fans, per layout on the kn5 set it loads, its red counted with the street
    gates (--force-install only under 0047's no-key-worse rule) and its report synced"""
    i = _first('python -m scripts.ac.kn5_ground_check "$PROJ" $KX --json "$PROJ/data/kn5_ground_check.$lid.json"')
    assert _first('tools/verify_fold_fans.py "$PROJ"') < i < _first("RACE_RED=$(pyq")
    assert 'KX="--kn5 $PROJ/build/${RK[$lid]} --kn5 $PROJ/build/${SLUG}_closure_$lid.kn5"; else KX="$STREET_KN5"' in TEXT
    assert '[ "$NR_R" != 0 ] || [ "$KG" != 0 ]; then' in TEXT and "kn5_ground_check exit $KG" in TEXT
    assert '"kn5_ground_check.$lid.json"' in TEXT
