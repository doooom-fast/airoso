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
  its order (re-synced 2026-10-12 to ship_sd.sh after ledger 0046's tiered terrain; it must be re-synced whenever
  ship_sd.sh changes);
- the Lariat: the paint centreline wired into the draft order; its dry run stops cleanly at "no blend yet";
- the four chain specs (ledger 0060) and the San Diego freeway network (ONE-CHAIN §4 row 8): the network's draft
  steps (net, classify, network_elev, network_mesh) are data steps on "$PROJ", then the underlay.
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
ALL_SPECS = sorted((ROOT / "tracks").glob("*/ship.json"))
CHAIN_SPECS = [ROOT / "tracks" / t / "ship.json" for t in ("milford-road-course", "exotics-racing-lv", "sand-creek", "high-plains")]


def test_every_step_every_ship_json_names_is_a_function():
    fns = _functions()
    assert len(fns) >= 40, sorted(fns)
    assert {SD_SPEC, LARIAT_SPEC, *CHAIN_SPECS} <= set(ALL_SPECS), ALL_SPECS
    for p in ALL_SPECS:
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
    for g in ("must be an absolute path", "is inside airoso", "SCRATCH=1; fi", "but there is no assembler at",
              "no blend yet: $PROJ/loop.blend"):
        assert _first(g) < first_copy, g


def test_sync_back_and_install_are_unreachable_from_a_scratch_project():
    skip_sync = _first('step "sync outputs workshop -> airoso: SKIPPED"')
    else_sync = _first('else\nstep "sync outputs workshop -> airoso"\n')
    end_sync = _first("# gate OBJs (66-78 MB each, regenerable from the kn5s) are never in a sync_out list\nfi\n")
    guard = TEXT.rfind('if [ "$SCRATCH" = 1 ]; then\n', 0, skip_sync)
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
             (["lookout-lariat", "--dry-run"], {"SHIP_PROJ": inside}, "is inside airoso")]
    if os.name == "nt":   # any Windows spelling of it (C:\USERS\...); on POSIX a backslash path is simply not absolute
        cases.append((["lookout-lariat", "--dry-run"], {"SHIP_PROJ": inside.upper().replace("/", "\\")}, "is inside airoso"))
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
    # ENG=<dir> overrides it for San Diego alone (a scratch copy of engine-july, as in tools/ship_sd.sh)
    assert ln.strip() == 'ENGINE="${ENG:-C:/Users/Owner/Documents/GitHub/engine-july}"', ln
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
    """The Lariat's dry run stops cleanly at 'no blend yet' with airoso's engine; SD's spec, rehearsed on an empty
    scratch project with --skip-blend, names engine-july and stops the same way. Neither touches the project."""
    if not shutil.which("bash"):
        print("  (no bash on PATH — skipped)")
        return
    tmp = Path(tempfile.mkdtemp())
    proj = tmp / "lariat_scratch"
    # the Lariat's draft ends in the underlay, which exists (scripts/blender/underlay.py, 2026-10-28): its dry run
    # would now sync inputs and run the draft. The 'no blend yet' guard is the case of a draft that lists NO blend
    # builder, so it is exercised on a copy of the Lariat spec with the underlay removed (SHIP_SPEC = a rehearsal)
    assert (ROOT / "scripts" / "blender" / "underlay.py").is_file(), "the underlay is the Lariat's blend builder"
    no_builder = json.loads(LARIAT_SPEC.read_text(encoding="utf-8"))
    no_builder["steps"]["draft"] = [n for n in no_builder["steps"]["draft"] if n != "underlay"]
    nb = tmp / "ship.no_builder.json"
    nb.write_text(json.dumps(no_builder), encoding="utf-8")
    r = _run(["lookout-lariat", "--dry-run"], {"SHIP_SPEC": nb.as_posix(), "SHIP_PROJ": proj.as_posix()})
    assert r.returncode == 0, (r.stdout[-600:], r.stderr[-400:])
    assert f"engine (prep / export / spawn): {ROOT.as_posix()}" in r.stdout, r.stdout
    assert "no blend yet" in r.stdout and "DRY RUN: stopped cleanly at 'no blend yet'." in r.stdout
    assert "underlay" in r.stdout and "sync inputs" not in r.stdout and not proj.exists()
    assert "not written yet" not in r.stdout, "the message must not claim the underlay is unwritten"
    r = _run(["lookout-lariat"], {"SHIP_SPEC": nb.as_posix(), "SHIP_PROJ": proj.as_posix()})   # a real run with no blend is a failure
    assert r.returncode == 1 and "no blend yet" in r.stdout and not proj.exists()
    # blend_builder_ready: the underlay counts as a builder exactly when scripts/blender/underlay.py exists
    body = TEXT[_first("blend_builder_ready() {"):_first("if [ \"$DRAFT_ONLY\" = 0 ] && [ ! -f \"$PROJ/loop.blend\" ]")]
    assert 'underlay) [ -f "$AIROSO/scripts/blender/underlay.py" ] && return 0;;' in body
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
    """tools/ship_sd.sh (pinned on its text by test_ship_sd_chain.py): its step headers up to the --dry-run stop,
    every branch, in text order == the headers of the steps tracks/san-diego-lake-murray/ship.json selects, in its
    order. Re-synced 2026-10-12 after ledger 0046 (terrain_sample / terrain_resample, triangulate_terrain,
    slim_far_terrain retired, the ENG override); RE-SYNC whenever ship_sd.sh changes — this test fails until
    ship.json and the vocabulary follow."""
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
    # ledger 0046: the 3DEP cache and the I-8 corridor cross both ways, as ship_sd.sh's TERRAIN_DATA
    m = re.search(r'^TERRAIN_DATA="([^"]*)"', SD_TEXT, re.M)
    assert m, "ship_sd.sh declares TERRAIN_DATA"
    for f in m.group(1).split():
        assert f"data/{f}" in s["sync_in"]["optional"] and f"data/{f}" in s["sync_out"]["files"], f
    assert "terrain.tiers.report.json" in sync and "data/terrain.tiers.report.json" in s["sync_out"]["files"]


def test_sd_assembler_runs_through_the_v021_shim_as_in_ship_sd():
    """ship_sd.sh runs the loop assembler and the weld from airoso's tracks/<track>/scripts-v021, registered as the
    `scripts` package (V021_SHIM) — ship_track.sh carries the same shim, byte for byte, and no workshop sys.path"""
    shim = re.search(r'^V021_SHIM="([^\n]*)"$', SD_TEXT, re.M).group(1)
    assert f'V021_SHIM="{shim}"' in TEXT
    assert 'V021="$SRC/scripts-v021"' in TEXT and "WS_SYSPATH" not in TEXT
    fns = _functions()
    for name in ("draft_build_loop_blend", "draft_rebuild_loop_blend", "draft_weld_mouths"):
        assert '--python-expr "$V021_SHIM"' in fns[name], name
    assert '"$V021/blender/build_loop_blend.py"' in fns["draft_build_loop_blend"]
    assert "slim_far" not in TEXT
    # the road gate OBJ is a ship step before the track folder (make_treefx / ext_config read tile names off it)
    for spec in (SD_SPEC, LARIAT_SPEC):
        sh = _spec(spec)["steps"]["ship"]
        assert sh.index("road_obj") < sh.index("track_folder") < sh.index("treefx"), spec
        assert "road_obj" not in _spec(spec)["steps"]["gate"], spec


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


def test_ship_sd_is_untouched_by_this_chain():
    """ship_sd.sh stays San Diego's chain of record (not a shim): ship_track.sh never calls it"""
    assert "ship_sd.sh" not in "\n".join(ln for _, ln in _code_lines())
    assert "ship_track" not in SD_TEXT


# --- the four tracks rebuilt through the chain (Kevin, 2026-10-28: "Rebuild all four with the Lake Murray chain") ---
def test_the_four_chain_specs_draft_the_engine_then_the_underlay_and_run_on_airosos_engine():
    fns = _functions()
    data_steps = TEXT[_first("is_data_step() {"):_first("SPEC_LINES=$(")]
    for p in CHAIN_SPECS:
        track = p.parent.name
        s = spec_mod.load(p, track)
        d = s["steps"]["draft"]
        assert d[-1] == "underlay" and d[-2] == "mesh", (track, d)
        assert d[0] in ("gps", "aerial") and "elev" in d and "project" in d, (track, d)
        assert d.index("elev") < d.index("project") < d.index("mesh"), (track, d)
        for n in d[:-1]:
            assert re.search(rf"\b{n}\b", data_steps), f"{track}: {n} must be a --draft-only data step"
        for n in ("build_loop_blend", "rebuild_loop_blend", "weld_mouths", "verify_mouths", "median", "route_connectors",
                  "treefx", "export_race", "race_author"):
            assert n not in [x for ph in PHASES for x in s["steps"][ph]], (track, n)
        assert s["steps"]["prep"] == ["prep", "split"]
        assert {"export_road", "ai", "verify_kn5", "road_obj", "track_folder", "verify_inis", "make_map"} <= set(s["steps"]["ship"])
        assert s["steps"]["gate"] == ["drive_test_street", "audit_street", "kn5_ground"], (track, s["steps"]["gate"])
        assert s["workshop"] == f"C:/Users/Owner/Documents/k10-workshops/{track}" and "airoso" not in s["workshop"].lower()
        assert s["require_race_layout"] is False and s["street_ai_july"] == ""
        assert "loop.blend" in s["sync_out"]["required"] and "data/underlay.report.json" in s["sync_out"]["files"]
        assert "source" in s["sync_in"]["dirs"] and "track.config.json" in s["sync_in"]["required"]
        cfg = json.loads((p.parent / "track.config.json").read_text(encoding="utf-8"))
        assert re.fullmatch(r"[A-Za-z0-9_]+", cfg["install_folder"]), (track, cfg.get("install_folder"))
        assert cfg["layouts"] and not any(l.get("race_furniture") for l in cfg["layouts"]), track
        assert track != "san-diego-lake-murray"
    # the two new draft steps run the engine on the absolute project and nothing else
    assert 'python -m scripts.aerial.build_aerial "$PROJ"' in fns["draft_aerial"]
    assert 'python -m scripts.geometry.build_mesh "$PROJ"' in fns["draft_mesh"]
    mesh_code = "\n".join(ln for ln in fns["draft_mesh"].splitlines() if not ln.lstrip().startswith("#"))
    assert "build_env" not in mesh_code, "no furniture in the draft (V3-PLAN P2 step 6)"
    # the aerial front-end is the Exotics draft's first step; from_track / kml go through gps
    assert spec_mod.load(ROOT / "tracks" / "exotics-racing-lv" / "ship.json", "exotics-racing-lv")["steps"]["draft"][0] == "aerial"
    for t in ("milford-road-course", "sand-creek", "high-plains"):
        assert spec_mod.load(ROOT / "tracks" / t / "ship.json", t)["steps"]["draft"][0] == "gps", t


# --- the San Diego freeway network through the chain (ONE-CHAIN §4 row 8; Kevin 2026-10-28: "rebuild, by an agent") ---
NETWORK_SPECS = [ROOT / "tracks" / "san-diego-freeway" / "ship.json"]
NETWORK_STEPS = {"net": "scripts.gps.network", "classify": "scripts.gps.classify",
                 "network_elev": "scripts.elevation.network_elev", "network_mesh": "scripts.geometry.build_network_mesh"}


def test_the_network_spec_drafts_the_network_then_the_underlay_and_runs_on_airosos_engine():
    """The network's draft is build_network.sh's net -> classify -> elev -> mesh as chain steps, then the underlay;
    everything after the draft is the four chain specs' shape (no authoring yet, no race layout, the street gates)."""
    fns = _functions()
    data_steps = TEXT[_first("is_data_step() {"):_first("SPEC_LINES=$(")]
    for p in NETWORK_SPECS:
        track = p.parent.name
        s = spec_mod.load(p, track)
        d = s["steps"]["draft"]
        assert d == ["net", "classify", "network_elev", "network_mesh", "underlay"], (track, d)
        for n in d[:-1]:
            assert re.search(rf"\b{n}\b", data_steps), f"{track}: {n} must be a --draft-only data step"
        everything = [x for ph in PHASES for x in s["steps"][ph]]
        for n in ("gps", "elev", "project", "mesh", "build_loop_blend", "rebuild_loop_blend", "weld_mouths",
                  "verify_mouths", "median", "route_connectors", "treefx", "export_race", "race_author"):
            assert n not in everything, (track, n)
        assert s["steps"]["author"] == [] and s["steps"]["prep"] == ["prep", "split"]
        assert {"export_road", "ai", "verify_kn5", "road_obj", "track_folder", "verify_inis", "make_map"} <= set(s["steps"]["ship"])
        assert s["steps"]["gate"] == ["drive_test_street", "audit_street", "kn5_ground"], (track, s["steps"]["gate"])
        assert s["workshop"] == f"C:/Users/Owner/Documents/k10-workshops/{track}" and "airoso" not in s["workshop"].lower()
        assert s["require_race_layout"] is False and s["street_ai_july"] == ""
        assert s["ui_name_prefix"] == "doooom San Diego"
        assert "loop.blend" in s["sync_out"]["required"] and "data/underlay.report.json" in s["sync_out"]["files"]
        assert "source" in s["sync_in"]["dirs"] and "track.config.json" in s["sync_in"]["required"]
        assert not any(f.endswith((".obj", ".blend")) for f in s["sync_out"]["files"]), "no generated mesh comes home"
        # the config: the name set (ONE-CHAIN §3) and the network the shipped 0.5.0 was built from
        cfg = json.loads((p.parent / "track.config.json").read_text(encoding="utf-8"))
        assert cfg["slug"] == "san_diego_freeway" == cfg["install_folder"] == track.replace("-", "_")
        assert cfg["ui_series"] == s["ui_name_prefix"] and cfg["name"].endswith("Free Roam")
        assert len(cfg["layouts"]) == 1 and cfg["layouts"][0]["name"].endswith("Free Roam")
        assert not any(lo.get("race_furniture") for lo in cfg["layouts"])
        assert cfg["source"]["type"] == "osm-network" and cfg["source"]["refs"] == ["I 5", "I 8", "CA 52", "CA 163"]
        assert cfg["mirror_x"] is False and cfg["loop"] is False and "K10" not in cfg["name"] + cfg["ui_series"]
        assert cfg["_doc"].startswith("The San Diego freeway network") and "project_freeway_net" in cfg["_doc"]
    # each network step runs its engine module on the absolute project, needs no Blender, and has a step header
    for n, mod in NETWORK_STEPS.items():
        body = fns[f"draft_{n}"]
        assert f'(cd "$AIROSO" && python -m {mod} "$PROJ")' in body, n
        assert '"$BL"' not in body and len(_headers(body)) == 1, n
        assert _headers(body)[0].startswith("draft: "), n
    # no generated furniture: the network's env stage is never a step
    assert "build_network_env" not in "\n".join(ln for _, ln in _code_lines()), "no furniture in the draft"
    assert not any(re.match(r"^(draft|author|prep|ship|gate)_(network_)?env$", f) for f in fns)
    # the underlay's contract is unchanged: the network mesh writes data/track.obj, the file the underlay reads
    nm = (ROOT / "scripts" / "geometry" / "build_network_mesh.py").read_text(encoding="utf-8")
    assert 'write_obj(data / "track.obj"' in nm
    ul = (ROOT / "scripts" / "blender" / "underlay.py").read_text(encoding="utf-8")
    assert 'obj = proj / "data" / "track.obj"' in ul and 'parse_obj(proj / "data" / "track.obj")' in ul


def test_is_data_step_takes_the_network_draft_and_stops_at_the_underlay():
    """--draft-only runs exactly the data steps: the four network steps are, the underlay is not (run in bash on the
    function's own text, nothing else of the script)"""
    bash = shutil.which("bash")
    if not bash:
        print("  (no bash on PATH — skipped)")
        return
    fn = TEXT[_first("is_data_step() {"):_first("SPEC_LINES=$(")]
    fn = fn[:fn.index("\n}\n") + 3]
    probe = fn + 'for n in "$@"; do if is_data_step "$n"; then echo "$n data"; else echo "$n blender"; fi; done\n'
    names = ["net", "classify", "network_elev", "network_mesh", "underlay", "build_loop_blend", "network_env"]
    r = subprocess.run([bash, "-c", probe, "probe", *names], capture_output=True, text=True, timeout=30, check=False)
    assert r.returncode == 0, r.stderr
    got = dict(ln.split() for ln in r.stdout.split("\n") if ln.strip())
    assert got == {"net": "data", "classify": "data", "network_elev": "data", "network_mesh": "data",
                   "underlay": "blender", "build_loop_blend": "blender", "network_env": "blender"}, got
