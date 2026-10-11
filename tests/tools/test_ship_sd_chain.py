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
        'tools/barrier_bands.py "$PROJ"',
        'tools/layout_dummies.py "$PROJ"',
        "tools/author_race_furniture_blend.py",
        'tools/verify_race.py "$PROJ"',
        "tools/plot_race_furniture.py",
        "scripts/ac/build_kn5_loop.py",
        "tools/split_exports_blend.py",
        "DRY RUN: stopping before the kn5 exports",
        "--blend \"$PROJ/blender/split/loop_main.blend\"",
        "--blend \"$PROJ/blender/split/loop_race.blend\" --out \"${SLUG}_race.kn5\"",
        'inspect_kn5 "$PROJ/build/${SLUG}_race.kn5" --json "$PROJ/data/race_kn5.json"',
        'tools/check_race_kn5.py "$PROJ/data/race_kn5.json"',
        "scripts/ac/build_spawn_kn5.py",
        "scripts.ac.write_ai_line",
        "scripts.ac.verify_kn5",
        "scripts.ac.track_folder",
        "tools/make_map.py",
        "tools/make_treefx.py",
        'kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5")',
        "drive_test \"$PROJ\" --layout street",
        "audit_mesh \"$PROJ\" 2>&1",
        '--kn5 "$PROJ/build/${SLUG}_race.kn5" --out "$PROJ/data/track.race.obj"',
        'drive_test "$PROJ" $RACE_FLAGS',
        "audit_mesh \"$PROJ\" --race --obj track.race.obj --out audit.race.json",
        "sync outputs workshop -> airoso",
        "NOT INSTALLED: race layout(s)",
        "install: $AC/${SLUG}_v3",
        'glob.glob(r"$AC/${SLUG}_v3/ui/*/ui_track.json")',
    ]
    pos = [_first(m) for m in order]
    assert pos == sorted(pos), [m for m, p, q in zip(order, pos, sorted(pos)) if p != q]


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
    assert '(cd "$AIROSO" && python tools/check_race_kn5.py "$PROJ/data/race_kn5.json")' in TEXT
    # the four gate exits all decide the install, and a race-furniture red is never forced
    assert '[ "$DT_S" != 0 ] || [ "$AU_S" != 0 ] || [ "$DT_R" != 0 ] || [ "$AU_R" != 0 ]' in TEXT
    assert 'if [ -n "$RACE_RED" ]; then' in TEXT
    # the race author runs on every ship (also with --skip-blend): it must sit OUTSIDE the SKIP_BLEND block
    fi_end = TEXT.find("\nfi\n", TEXT.find('if [ "$SKIP_BLEND" = 0 ]; then'))
    assert fi_end > 0 and TEXT.find("tools/author_race_furniture_blend.py") > fi_end


def test_sync_list_carries_the_new_outputs():
    for f in ("barrier_bands.json", "race_authored.json", "race_verify.json", "audit.race.json",
              '"dummies_$lid.json"', '"drive_test.$lid.json"', '"$SRC/ai/$lid"', "race_plots", "split_manifest.json"):
        assert f in TEXT, f


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
    # the workshop's build_loop_blend imports scripts.geometry from the project's PARENT: the WS root goes on sys.path
    blb = [ln for _, ln in code if "build_loop_blend.py" in ln]
    assert len(blb) == 2, blb
    for ln in blb:
        assert '--python-expr "$WS_SYSPATH" --python scripts/blender/build_loop_blend.py -- "$PROJ"' in ln, ln
    assert "WS_SYSPATH=\"import sys; sys.path.insert(0, r'$WS')\"" in TEXT
    # the guards: absolute, outside airoso, scratch derived from the workshop path, all before the first copy
    assert "/*|[A-Za-z]:/*|" in TEXT and '"$(norm "$AIROSO")"|"$(norm "$AIROSO")"/*)' in TEXT
    assert 'if [ "$(norm "$PROJ")" = "$(norm "$WS_PROJ")" ]; then SCRATCH=0; else SCRATCH=1; fi' in TEXT
    first_copy = _first('cp "$SRC/track.config.json" "$PROJ/track.config.json"')
    for g in ("must be an absolute path", "is inside airoso", "SCRATCH=1; fi", "would shadow the workshop's"):
        assert _first(g) < first_copy, g


def test_sync_back_and_install_are_unreachable_from_a_scratch_project():
    """(b) every write into airoso ($SRC) sits in the sync block's NON-scratch branch; every write into
    the AC folder sits in the install block's NON-scratch branch"""
    import re
    skip_sync = _first('step "sync outputs workshop -> airoso: SKIPPED"')
    else_sync = _first('else\nstep "sync outputs workshop -> airoso"\n')
    end_sync = _first("# track.race.obj / track.obj are 66+ MB each and regenerable from the kn5s: never synced.\nfi\n")
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
             ({"SHIP_PROJ": inside}, "is inside airoso"),
             ({"SHIP_PROJ": inside.upper().replace("/", "\\")}, "is inside airoso")]   # any spelling of it
    for extra, msg in cases:
        env = dict(os.environ, **extra)
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
    assert allowed == {"kerb_diffuse.png", "concrete_barrier_diffuse.png", "concrete_barrier_normal.png"}
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
