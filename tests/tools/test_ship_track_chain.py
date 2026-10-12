"""tools/ship_track.sh — the ship chain for any track (V3-PLAN P1, Lariat; ledger 0048), pinned on the script text
and on guard-only runs (bash exits before the first file operation; nothing is built):

- the closed vocabulary: every step a ship.json names is a function in the script; an unknown name exits 2
  before anything is touched; tools/ship_track_spec.py refuses names, paths and keys outside its patterns; no
  value from ship.json is ever executed (no eval / bash -c / source);
- stage order and the exit-code flag on every Blender call;
- the scratch rails (SHIP_PROJ / SHIP_SPEC never sync back or install; nothing inside airoso), the install
  folder from config, the install refusing while AC / Content Manager runs, the old build parked in the archive;
- engine-july only when the slug is san-diego-lake-murray;
- San Diego parity: the step headers tracks/san-diego-lake-murray/ship.json selects are tools/ship_sd.sh's, in
  its order (ship_sd.sh at airoso 8a2f076; it must be re-synced when ship_sd.sh changes);
- the Lariat: the paint centreline wired into the draft order; with --skip-blend and no loop.blend its dry run
  stops cleanly at "no blend yet" (without it, the underlay can now build the blend, so the draft would run).
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
SD_TEXT = (ROOT / "tools" / "ship_sd.sh").read_text(encoding="utf-8").replace("\r\n", "\n")
sys.path.insert(0, str(ROOT / "tools"))
import ship_track_spec as spec_mod  # noqa: E402

SD_SPEC = ROOT / "tracks" / "san-diego-lake-murray" / "ship.json"
LARIAT_SPEC = ROOT / "tracks" / "lookout-lariat" / "ship.json"
PHASES = ("draft", "author", "prep", "ship", "gate")


def _first(marker: str, text: str = TEXT) -> int:
    i = text.find(marker)
    assert i >= 0, f"{marker!r} not in the script"
    return i


def _code_lines(text: str = TEXT):
    out, pos = [], 0
    for ln in text.splitlines(keepends=True):
        if not ln.lstrip().startswith("#"):
            out.append((pos, ln.rstrip("\n")))
        pos += len(ln)
    return out


def _functions() -> dict[str, str]:
    """name -> body of every vocabulary function (<phase>_<step>() { ... } up to the closing brace at column 0)"""
    out = {}
    for m in re.finditer(r"^((?:draft|author|prep|ship|gate)_[a-z0-9_]+)\(\) \{\n(.*?)^\}\n", TEXT, re.S | re.M):
        out[m.group(1)] = m.group(2)
    return out


def _headers(body: str) -> list[str]:
    return re.findall(r'^\s*(?:if .*?then )?step "([^"]*)"', body, re.M)


def _spec(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# --- the closed vocabulary -----------------------------------------------------------------------------------
def test_every_step_both_ship_jsons_name_is_a_function():
    fns = _functions()
    assert len(fns) >= 40, sorted(fns)
    for p in (SD_SPEC, LARIAT_SPEC):
        s = spec_mod.load(p, _spec(p)["track"])
        for ph in PHASES:
            for n in s["steps"][ph]:
                assert f"{ph}_{n}" in fns, f"{p.parent.name}: steps.{ph} names {n!r}, no {ph}_{n}() in ship_track.sh"


def test_the_script_checks_every_name_before_anything_runs():
    for ph, arr in (("draft", "DRAFT"), ("author", "AUTHOR"), ("prep", "PREP"), ("ship", "SHIP"), ("gate", "GATE")):
        line = f'declare -F "{ph}_$n" >/dev/null || {{ echo "ship.json steps.{ph}: unknown step'
        assert line in TEXT, ph
        assert _first(line) < _first('step "sync inputs airoso -> workshop ($PROJ)"')
    # names are dispatched only as "<phase>_$n": never eval'd, never a command from a value
    code = "\n".join(ln for _, ln in _code_lines())
    for bad in ("eval ", "bash -c", "sh -c", "source ", ". \"$", "$($v", "${!", "exec "):
        if bad == "${!":
            # the only indirect expansion allowed is the index list of the map arrays
            assert code.count("${!") == code.count('${!OUT_MAP_FROM[@]}'), "no indirect expansion of a value"
            continue
        assert bad not in code, bad
    for ph in PHASES:
        assert re.search(rf'"{ph}_\$n"', code), ph


def test_spec_refuses_what_is_not_in_its_patterns():
    base = _spec(LARIAT_SPEC)

    def refused(mut, needle):
        d = json.loads(json.dumps(base))
        mut(d)
        p = Path(tempfile.mkdtemp()) / "ship.json"
        p.write_text(json.dumps(d), encoding="utf-8")
        try:
            spec_mod.load(p, "lookout-lariat")
        except spec_mod.SpecError as e:
            assert needle in str(e), (needle, str(e))
            return
        raise AssertionError(f"accepted: {needle}")

    refused(lambda d: d["steps"]["draft"].append("rm -rf /"), "is not a step name")
    refused(lambda d: d["steps"]["draft"].append("gps; curl x"), "is not a step name")
    refused(lambda d: d["steps"].update(deploy=["x"]), "unknown phase")
    refused(lambda d: d["steps"].update(prep=["split", "prep"]), "exactly")
    refused(lambda d: d.update(engine="C:/Users/Owner/Documents/GitHub/engine-july"), "unknown key")
    refused(lambda d: d.update(track="san-diego-lake-murray"), "not 'lookout-lariat'")
    refused(lambda d: d.update(workshop="../k10-workshops"), "absolute")
    refused(lambda d: d.update(workshop="C:/x/../airoso"), "absolute")
    refused(lambda d: d["sync_in"]["required"].append("../../secrets.txt"), "climbs out")
    refused(lambda d: d["sync_in"]["required"].append("/etc/passwd"), "plain relative path")
    refused(lambda d: d["sync_in"]["required"].append("data/$(whoami)"), "plain relative path")
    refused(lambda d: d["sync_out"]["files"].append("data/{evil}.json"), "unknown template")
    refused(lambda d: d["sync_in"]["required"].append("data/{id}.json"), "sync_out only")
    refused(lambda d: d.update(ui_name_prefix="K10\tx"), "printable")
    refused(lambda d: d.update(workshop_project="a/b"), "one folder name")
    # the two real files pass, and the lines carry no tab inside a value
    for p in (SD_SPEC, LARIAT_SPEC):
        s = spec_mod.load(p, _spec(p)["track"])
        for ln in spec_mod.lines(s):
            k, *vals = ln.split("\t")
            assert k and len(vals) in (1, 2), ln


def _run(args, env_extra, cwd=None):
    bash = shutil.which("bash")
    env = dict(os.environ, AIROSO=ROOT.as_posix(), **env_extra)
    env.pop("SHIP_PROJ", None) if "SHIP_PROJ" not in env_extra else None
    env.pop("SHIP_SPEC", None) if "SHIP_SPEC" not in env_extra else None
    return subprocess.run([bash, str(SH), *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env, cwd=cwd or tempfile.mkdtemp(), timeout=120)


def test_unknown_step_exits_2_before_any_file_operation():
    if not shutil.which("bash"):
        print("  (no bash on PATH — skipped)")
        return
    d = _spec(LARIAT_SPEC)
    d["steps"]["draft"].insert(3, "frobnicate")
    tmp = Path(tempfile.mkdtemp())
    sp = tmp / "ship.json"
    sp.write_text(json.dumps(d), encoding="utf-8")
    proj = tmp / "proj"
    r = _run(["lookout-lariat", "--dry-run"], {"SHIP_SPEC": sp.as_posix(), "SHIP_PROJ": proj.as_posix()})
    assert r.returncode == 2, (r.returncode, r.stdout[-500:], r.stderr[-500:])
    assert "unknown step 'frobnicate'" in r.stdout, r.stdout[-500:]
    assert not proj.exists() and "sync inputs" not in r.stdout
    d["steps"]["draft"][3] = "gps && rm -rf ~"
    sp.write_text(json.dumps(d), encoding="utf-8")
    r = _run(["lookout-lariat", "--dry-run"], {"SHIP_SPEC": sp.as_posix(), "SHIP_PROJ": proj.as_posix()})
    assert r.returncode == 2 and "is not a step name" in r.stderr, (r.stdout[-300:], r.stderr[-300:])
    assert not proj.exists()


# --- order and the Blender flag --------------------------------------------------------------------------------
def test_main_flow_order():
    order = [
        'case "$STREET_AI" in draft|july) ;;',
        "SPEC_LINES=$(cd \"$AIROSO\" && python tools/ship_track_spec.py",
        'declare -F "draft_$n"',
        "must be an absolute path",
        "is inside airoso",
        'then SCRATCH=0; else SCRATCH=1; fi',
        "no blend yet: $PROJ/loop.blend does not exist",
        'step "sync inputs airoso -> workshop ($PROJ)"',
        "LAYOUT_IDS=$(pyq",
        'if [ "$SKIP_BLEND" = 0 ]; then\n  for n in ${DRAFT[@]+"${DRAFT[@]}"}; do',
        'for n in ${AUTHOR[@]+"${AUTHOR[@]}"}; do "author_$n"; done',
        'for n in "${PREP[@]}"; do "prep_$n"; done',
        "DRY RUN: stopping before the kn5 exports",
        'for n in ${SHIP[@]+"${SHIP[@]}"}; do "ship_$n"; done',
        'for lid in $LAYOUT_IDS; do rm -f "$PROJ/data/drive_test.$lid.json"; done',
        'for n in ${GATE[@]+"${GATE[@]}"}; do "gate_$n"; done',
        "RACE_RED=$(pyq",
        'step "sync outputs workshop -> airoso: SKIPPED"',
        'step "sync outputs workshop -> airoso"\n',
        'if [ -n "$RACE_RED" ]; then',
        'elif [ "$FORCE" = 1 ]; then',
        'step "install: $AC/$INSTALL_FOLDER',
    ]
    pos = [_first(m) for m in order]
    assert pos == sorted(pos), [m for m, p, q in zip(order, pos, sorted(pos)) if p != q]


def test_every_blender_call_carries_the_exit_code_flag():
    calls = [ln for _, ln in _code_lines() if '"$BL" --background' in ln]
    assert len(calls) >= 18, len(calls)
    for ln in calls:
        assert "--python-exit-code 1" in ln, ln


def test_safety_rails():
    assert "set -euo pipefail" in TEXT
    assert "--allow-missing-kn5" not in TEXT and "set_start_blend" not in TEXT and "track_race.obj" not in TEXT
    assert '(cd "$AIROSO" && python -m scripts.ac.verify_kn5 "$PROJ")' in TEXT
    assert '(cd "$AIROSO" && python -m scripts.ac.track_folder "$PROJ")' in TEXT
    # race stages run only when a layout declares race_furniture
    fns = _functions()
    for name in ("author_race_bands", "author_race_planned_gate", "author_race_author", "author_race_verify",
                 "ship_export_race", "ship_race_scenery_gate", "gate_race_gates"):
        assert fns[name].lstrip().startswith('[ -n "$RACE_IDS" ] || { no_race'), name
    assert "declare race_furniture but ship.json steps.author has no race_author" in TEXT
    # the five gate exits decide the install; a race layout red on its own gates is never forced
    assert '[ "$DT_S" != 0 ] || [ "$AU_S" != 0 ] || [ "$DT_R" != 0 ] || [ "$AU_R" != 0 ] || [ "$NR_R" != 0 ]' in TEXT
    assert _first('if [ -n "$RACE_RED" ]; then') < _first('elif [ "$FORCE" = 1 ]; then')


def test_bash_syntax():
    bash = shutil.which("bash")
    if not bash:
        print("  (no bash on PATH — syntax check skipped)")
        return
    r = subprocess.run([bash, "-n", str(SH)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


# --- the scratch rails ----------------------------------------------------------------------------------------
def test_every_step_runs_on_the_absolute_project():
    code = [(p, re.sub(r"\s+#\s.*$", "", ln)) for p, ln in _code_lines()]       # inline comments are prose
    rel = [ln for _, ln in code if not ln.lstrip().startswith(("echo", "step"))
           and (re.search(r"--\s+project(\s|$|\))", ln) or re.search(r"\s(\./)?project(/\S*)?(\s|$|\))", ln))]
    assert not rel, rel
    steps = [ln for _, ln in code if '"$BL" --background' in ln or re.search(r"python (tools/|-m scripts\.)", ln)]
    assert len(steps) >= 40, len(steps)
    for ln in steps:
        if "tools/ship_track_spec.py" in ln:
            continue
        assert '"$PROJ' in ln, ln
    assert 'WS_PROJ="$WS/$WS_SUB"' in TEXT and 'PROJ="${SHIP_PROJ:-$WS_PROJ}"' in TEXT
    # a rehearsal (SHIP_SPEC) is scratch whatever SHIP_PROJ says
    assert 'if [ "$REHEARSAL" = 0 ] && [ "$(norm "$PROJ")" = "$(norm "$WS_PROJ")" ]; then SCRATCH=0; else SCRATCH=1; fi' in TEXT
    # nothing inside airoso: the project AND the workshop, against AIROSO and the main checkout
    assert 'for root in "$AIROSO" "$AIROSO_MAIN"; do' in TEXT and "workshop '$WS' is inside airoso" in TEXT
    first_copy = _first('mkdir -p "$PROJ/data"')
    for g in ("must be an absolute path", "is inside airoso", "SCRATCH=1; fi", "would shadow the workshop's",
              "no blend yet: $PROJ/loop.blend"):
        assert _first(g) < first_copy, g


def test_sync_back_and_install_are_unreachable_from_a_scratch_project():
    skip_sync = _first('step "sync outputs workshop -> airoso: SKIPPED"')
    else_sync = _first('else\nstep "sync outputs workshop -> airoso"\n')
    end_sync = _first("# gate OBJs (66-78 MB each, regenerable from the kn5s) are never in a sync_out list\nfi\n")
    # a scratch project, or a D4 variant run (SHIP_VARIANT: tests/tools/test_drive1_build.py), never syncs back
    guard = TEXT.rfind('if [ "$SCRATCH" = 1 ] || [ -n "$VARIANT" ]; then\n', 0, skip_sync)
    assert guard >= 0 and skip_sync < else_sync < end_sync
    n_src = 0
    for pos, ln in _code_lines():
        writes_src = re.search(r'\b(cp|mv)( -r)? "[^"]*" "\$SRC', ln) or 'rm -rf "$SRC' in ln or 'rm -f "$SRC' in ln \
            or 'mkdir -p "$(dirname "$SRC' in ln
        if writes_src:
            n_src += 1
            assert else_sync < pos < end_sync, ("airoso write outside the guarded sync", ln)
    assert n_src >= 5, n_src
    skip_inst = _first('if [ "$INSTALL" = 1 ] && [ "$SCRATCH" = 1 ]; then')
    real_inst = _first('elif [ "$INSTALL" = 1 ]; then')
    assert skip_inst < real_inst
    n_ac = 0
    for pos, ln in _code_lines():
        words = ln.replace(";", " ").split()
        if any(w in ("cp", "mv", "rm", "mkdir") for w in words) and ('"$AC/' in ln or '"$ARCHIVE/' in ln):
            n_ac += 1
            assert pos > real_inst, ("AC / archive write outside the guarded install", ln)
    assert n_ac >= 2, n_ac
    assert _first("d['name']=sys.argv[3]") > real_inst
    # --dry-run and --draft-only never install
    assert 'if [ "$DRY" = 1 ] || [ "$DRAFT_ONLY" = 1 ]; then INSTALL=0; fi' in TEXT


def test_install_folder_from_config_parked_old_build_and_running_game_refused():
    assert "get('install_folder')" in TEXT and 'cp -r "$B" "$AC/$INSTALL_FOLDER"' in TEXT
    assert 'case "$INSTALL_FOLDER" in ""|*[!A-Za-z0-9_]*)' in TEXT
    for track in ("san-diego-lake-murray", "lookout-lariat"):
        cfg = json.loads((ROOT / "tracks" / track / "track.config.json").read_text(encoding="utf-8"))
        assert re.match(r"^[A-Za-z0-9_]+$", cfg["install_folder"]), cfg["install_folder"]
    assert json.loads((ROOT / "tracks" / "lookout-lariat" / "track.config.json").read_text(encoding="utf-8"))[
        "install_folder"] == "lookout_lariat_v3"                                          # plan A11
    install = TEXT[_first('step "install: $AC/$INSTALL_FOLDER'):]
    assert 'mv "$AC/$old" "$ARCHIVE/$STAMP/$old"' in install and 'ARCHIVE="D:/k10-track-archive"' in TEXT
    assert "_prev\"" not in install.replace('"${INSTALL_FOLDER}_prev"', ""), "never a _prev left in content/tracks"
    guard = _first("tasklist //FO CSV //NH")
    assert _first('elif [ "$INSTALL" = 1 ]; then') < guard < _first('mv "$AC/$old"')
    for frag in ("acs[.]exe", "Content Manager", "NOT INSTALLED: close"):
        assert frag in TEXT[guard:_first('mv "$AC/$old"')], frag


def test_argument_guards_exit_2_before_any_file_operation():
    if not shutil.which("bash"):
        print("  (no bash on PATH — guard run skipped)")
        return
    cwd = tempfile.mkdtemp()
    inside = (ROOT / "tracks" / "_never_a_scratch_project").as_posix()
    cases = [([], {}, "usage:"),
             (["lookout-lariat", "--bogus"], {}, "unknown flag"),
             (["lookout-lariat", "san-diego-lake-murray"], {}, "one track per run"),
             (["../etc"], {}, "not a track folder name"),
             (["no-such-track"], {}, "no track folder"),
             (["lookout-lariat", "--draft-only", "--skip-blend"], {}, "--draft-only runs the draft"),
             (["lookout-lariat"], {"STREET_AI": "bogus"}, "STREET_AI must be draft or july"),
             (["lookout-lariat", "--dry-run"], {"STREET_AI": "july"}, "names no street_ai_july"),
             (["lookout-lariat", "--dry-run"], {"SHIP_PROJ": "scratch/project"}, "must be an absolute path"),
             (["lookout-lariat", "--dry-run"], {"SHIP_PROJ": inside}, "is inside airoso"),
             (["lookout-lariat", "--dry-run"], {"SHIP_PROJ": inside.upper().replace("/", "\\")}, "is inside airoso")]
    for args, extra, msg in cases:
        r = _run(args, extra, cwd=cwd)
        assert r.returncode == 2, (args, extra, r.returncode, r.stdout[-400:], r.stderr[-400:])
        assert msg in r.stdout, (args, extra, r.stdout[-400:])
        assert "sync inputs" not in r.stdout
    assert os.listdir(cwd) == []
    assert not Path(inside).exists()


# --- engine-july -----------------------------------------------------------------------------------------------
def test_engine_july_only_for_san_diego():
    hits = [(p, ln) for p, ln in _code_lines() if "engine-july" in ln]
    assert len(hits) == 1, hits
    pos, ln = hits[0]
    assert ln.strip() == 'ENGINE="C:/Users/Owner/Documents/GitHub/engine-july"', ln
    cond = TEXT.rfind('if [ "$TRACK" = "san-diego-lake-murray" ]; then\n', 0, pos)
    assert cond >= 0 and TEXT[cond:pos].count("\n") == 1, "the engine-july line is the SD branch's only line"
    assert 'else\n  ENGINE="$AIROSO"\nfi' in TEXT[pos:pos + 160]
    assert "$ENG/" not in TEXT and '"$ENG"' not in TEXT
    fns = _functions()
    for name, frag in (("prep_prep", '"$ENGINE/scripts/ac/build_kn5_loop.py"'),
                       ("ship_export_road", '"$ENGINE/scripts/ac/export_kn5_addon.py"'),
                       ("ship_export_race", '"$ENGINE/scripts/ac/export_kn5_addon.py"'),
                       ("ship_spawn_kn5", '"$ENGINE/scripts/ac/build_spawn_kn5.py"')):
        assert frag in fns[name], name
    assert "engine" not in spec_mod.TOP


def test_engine_rule_and_no_blend_yet_on_guard_runs():
    """The Lariat's --skip-blend dry run (no loop.blend) stops cleanly at 'no blend yet' with airoso's engine; SD's
    spec, rehearsed on an empty scratch project with --skip-blend, names engine-july and stops the same way. Neither
    touches the project."""
    if not shutil.which("bash"):
        print("  (no bash on PATH — skipped)")
        return
    tmp = Path(tempfile.mkdtemp())
    proj = tmp / "lariat_scratch"
    # scripts/blender/underlay.py exists (P2 step 3), so the Lariat's draft CAN build a loop.blend: without
    # --skip-blend the chain no longer stops (it would run the whole draft, network included). The guard is
    # exercised with --skip-blend, which leaves nothing in this run able to build the missing blend.
    assert (ROOT / "scripts" / "blender" / "underlay.py").is_file()
    assert '    underlay) [ -f "$AIROSO/scripts/blender/underlay.py" ] && return 0;;' in TEXT
    r = _run(["lookout-lariat", "--skip-blend", "--dry-run"], {"SHIP_PROJ": proj.as_posix()})
    assert r.returncode == 0, (r.stdout[-600:], r.stderr[-400:])
    assert f"engine (prep / export / spawn): {ROOT.as_posix()}" in r.stdout, r.stdout
    assert "no blend yet" in r.stdout and "DRY RUN: stopped cleanly at 'no blend yet'." in r.stdout
    assert "--skip-blend resumes from an authored loop.blend" in r.stdout
    assert "sync inputs" not in r.stdout and not proj.exists()
    r = _run(["lookout-lariat", "--skip-blend"], {"SHIP_PROJ": proj.as_posix()})   # a real run with no blend fails
    assert r.returncode == 1 and "no blend yet" in r.stdout and not proj.exists()
    sd = tmp / "sd_scratch"
    r = _run(["san-diego-lake-murray", "--skip-blend", "--dry-run"],
             {"SHIP_SPEC": SD_SPEC.as_posix(), "SHIP_PROJ": sd.as_posix()})
    assert r.returncode == 0, (r.stdout[-600:], r.stderr[-400:])
    assert "engine (prep / export / spawn): C:/Users/Owner/Documents/GitHub/engine-july" in r.stdout
    assert "--skip-blend resumes from an authored loop.blend" in r.stdout and not sd.exists()


# --- San Diego parity ------------------------------------------------------------------------------------------
def _sd_headers(text, start, end):
    seg = text[start:end]
    return re.findall(r'^\s*step "([^"]*)"', seg, re.M)


def test_sd_spec_reproduces_ship_sd_step_sequence_before_the_dry_stop():
    """tools/ship_sd.sh at airoso 8a2f076 (byte-identical, pinned by test_ship_sd_chain.py): its step headers up to
    the --dry-run stop, every branch, in text order == the headers of the steps tracks/san-diego-lake-murray/ship.json
    selects, in its order. RE-SYNC when ship_sd.sh changes (the concurrent terrain job's ENG override, slim_far
    removed, terrain steps): this test fails on purpose until ship.json and the vocabulary follow."""
    sd = _sd_headers(SD_TEXT, 0, _first("DRY RUN: stopping before the kn5 exports", SD_TEXT))
    s = spec_mod.load(SD_SPEC, "san-diego-lake-murray")
    fns = _functions()
    mine = ["sync inputs airoso -> workshop ($PROJ)"]
    for ph in ("draft", "author", "prep"):
        for n in s["steps"][ph]:
            mine += _headers(fns[f"{ph}_{n}"])
    assert mine == sd, "\n".join(f"{a!r:110} | {b!r}" for a, b in zip(mine + [""] * 40, sd + [""] * 40) if a != b)


def test_sd_spec_reproduces_ship_sd_step_sequence_after_the_dry_stop():
    """the export / gate half (not part of the dry-run parity, but kept in step): identical headers but for the
    track-folder line, which no longer hard-codes three layouts"""
    a = _first("DRY RUN: stopping before the kn5 exports", SD_TEXT)
    sd = _sd_headers(SD_TEXT, a, _first("sync outputs workshop -> airoso: SKIPPED", SD_TEXT))
    s = spec_mod.load(SD_SPEC, "san-diego-lake-murray")
    fns = _functions()
    mine = []
    for ph in ("ship", "gate"):
        for n in s["steps"][ph]:
            hs = _headers(fns[f"{ph}_{n}"])
            if n == "audit_street":
                hs = [hs[0].replace("$AUDIT_NOTE", s["audit_note"])]
            mine += hs
    sd = [h.replace("models_<id>.ini x3", "models_<id>.ini per layout") for h in sd]
    assert mine == sd, "\n".join(f"{x!r:110} | {y!r}" for x, y in zip(mine + [""] * 40, sd + [""] * 40) if x != y)


def test_sd_spec_carries_ship_sds_sync_lists_and_names():
    s = spec_mod.load(SD_SPEC, "san-diego-lake-murray")
    assert s["workshop"] == "C:/Users/Owner/Documents/GitHub/k10-sd-v021" and s["workshop_project"] == "project"
    assert 'WS="C:/Users/Owner/Documents/GitHub/k10-sd-v021"' in SD_TEXT and 'WS_PROJ="$WS/project"' in SD_TEXT
    assert s["require_race_layout"] is True
    assert s["street_ai_july"] == "D:/k10-track-archive/2026-10-11/san_diego_lake_murray/ai"
    assert 'K10 - San Diego (V3) \\u2014 ' in SD_TEXT and s["ui_name_prefix"] == "K10 - San Diego (V3)"
    sync = SD_TEXT[_first('step "sync outputs workshop -> airoso"\n', SD_TEXT):_first("never synced.\nfi\n", SD_TEXT)]
    for f in ("centerline.local.json", "centerline.raw.local.json", "median_bands.json", "dummies.json",
              "finished_centerline.json", "gate_centerline.json", "lights.local.json", "connectors.local.json",
              "mouths.json", "mouth_welds.json", "verify_mouths.json", "signs.local.json", "signs_preview.svg",
              "signs_measured.json", "drive_test.json", "audit.json", "barrier_bands.json", "race_authored.json",
              "race_verify.json", "race_verify.scenery.json", "race_kn5.json"):
        assert f in sync and f"data/{f}" in s["sync_out"]["files"], f
    for f in ("data/dummies_{id}.json", "data/drive_test.{id}.json", "data/no_route.{race}.json",
              "data/no_route.{race}.planned.json", "data/audit.{race}.json", "data/closure_{race}.kn5.json"):
        assert f in s["sync_out"]["files"], f
    assert s["sync_out"]["required"] == ["loop.blend"] and s["sync_out"]["remove"] == ["data/audit.race.json"]
    assert s["sync_out"]["map"] == [["blender/split/split_manifest.json", "data/split_manifest.json"]]
    assert set(s["sync_out"]["dirs"]) == {"ai/{id}", "data/signs_plots", "data/race_plots"}
    assert s["sync_in"]["required"] == ["track.config.json", "start_positions.json"]
    assert s["sync_in"]["globs"] == ["source/trees/*.bin"]


# --- the Lariat --------------------------------------------------------------------------------------------------
def test_lariat_draft_wires_the_paint_centreline_before_any_elevation():
    s = spec_mod.load(LARIAT_SPEC, "lookout-lariat")
    d = s["steps"]["draft"]
    order = ["gps", "paint_centreline", "remap_config", "verify_centreline_paint", "route_oneway_check", "elev", "project"]
    assert [n for n in d if n in order] == order, d
    assert d.index("paint_centreline") == d.index("gps") + 1, "nothing reads the OSM line between gps and the paint"
    assert d[-1] == "underlay"
    fns = _functions()
    assert "python tools/remap_centreline_config.py \"$PROJ\" --write" in fns["draft_remap_config"]
    assert "python tools/verify_centreline_paint.py \"$PROJ\"" in fns["draft_verify_centreline_paint"]
    # the gps stage destroys the paint line the config points into: it is kept first, for the remap
    g = fns["draft_gps"]
    assert g.index('cp "$PROJ/data/centerline.geojson" "$PROJ/data/centerline.previous.geojson"') < \
        g.index("python -m scripts.gps.centerline")
    assert "'paint_centreline' in" in g
    # workshop outside airoso; airoso's engine; nothing of SD's
    assert s["workshop"] == "C:/Users/Owner/Documents/k10-workshops/lookout-lariat"
    assert "GitHub/airoso" not in s["workshop"]
    for n in ("build_loop_blend", "weld_mouths", "verify_mouths", "median", "route_connectors"):
        assert n not in sum(s["steps"].values(), []), n
    assert s["street_ai_july"] == "" and s["require_race_layout"] is False
    assert "track.config.json" in s["sync_out"]["files"], "the remapped config comes home with the draft"
    # every data step of the draft runs under --draft-only; underlay is where it stops
    for n in d[:-1]:
        assert re.search(rf"\b{n}\b", TEXT[_first("is_data_step() {"):_first("SPEC_LINES=$(")]), n


def test_lariat_draft_runs_its_data_stages_in_order():
    """P2 steps 1, 4, 5: the profile by station (decks held, capture.bridges written) before projection; the measured
    widths after the OSM table; the crossfall on the real-width footprint after them; its roll-rate gate hard."""
    d = spec_mod.load(LARIAT_SPEC, "lookout-lariat")["steps"]["draft"]
    order = ["elev", "road_profile", "project", "widths", "measured_widths", "crossfall", "verify_crossfall", "underlay"]
    assert [n for n in d if n in order] == order, d
    fns = _functions()
    assert "python -m scripts.elevation.road_profile \"$PROJ\" --write" in fns["draft_road_profile"]
    assert "python -m scripts.gps.measured_widths \"$PROJ\"" in fns["draft_measured_widths"]
    assert "python -m scripts.elevation.crossfall \"$PROJ\"" in fns["draft_crossfall"]
    assert "python tools/verify_crossfall.py \"$PROJ\"" in fns["draft_verify_crossfall"]
    for n in ("draft_road_profile", "draft_measured_widths", "draft_crossfall", "draft_verify_crossfall"):
        assert "|| " not in fns[n], f"{n}: a failing stage must stop the chain (set -e)"
    # the new block sits after every existing function (appended, nothing above it reordered)
    assert _first("draft_road_profile() {") > _first("gate_race_gates() {")
    cfg = json.loads((ROOT / "tracks" / "lookout-lariat" / "track.config.json").read_text(encoding="utf-8"))
    assert cfg["road_profile"]["crossfall"]["method"] == "footprint"
    assert cfg["bridges"]["declared"][0]["footprint_ways"] == [533503591, 533679737]
    s = spec_mod.load(LARIAT_SPEC, "lookout-lariat")
    for f in ("data/widths.measured.json", "data/bridge.spans.json", "data/crossfall.json", "data/crossfall_gate.json",
              "data/osm.widths.cache.json"):
        assert f in s["sync_out"]["files"], f


def test_ship_sd_is_untouched_by_this_chain():
    """ship_sd.sh stays San Diego's chain of record (not a shim): ship_track.sh never calls it"""
    assert "ship_sd.sh" not in "\n".join(ln for _, ln in _code_lines())
    assert "ship_track" not in SD_TEXT
