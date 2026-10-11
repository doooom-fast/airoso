"""tools/ship_sd.sh — the three-version chain's order and safety rails (ledger 0047), pinned on the
script text (bash is not run here beyond `bash -n` when it exists): every stage in the order the
handoffs fixed, every Blender call with --python-exit-code 1, the gates on the right OBJ, the
packer/verifier repointed to airoso, set_start gone, the race gate OBJ never named track_*.obj.
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
    assert 'cp "$AC/$SLUG/ai/fast_lane.ai"' in TEXT and '"$B/ai/"' not in TEXT, "the July copy moved to the ship stage (root ai/ no longer exists)"
    assert "--allow-missing-kn5" not in TEXT, "the ship chain never packs with a missing kn5"
    assert 'PROJ="${SHIP_PROJ:-$WS/project}"' in TEXT
    assert "RACE_BYTES" in TEXT and "20000000" in TEXT, "race kn5 size cap"
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
