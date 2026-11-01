"""tools/ship_fleet.sh — the fleet through the chain, one track after another (Kevin 2026-11-01: "a complete track list
and installed by morning"; docs/TRACKS.md). Pinned on the script text and on a --list run: ONE-CHAIN §4's order, the
deprioritised skip, no ship.json = skip, and above all that this script adds nothing to the chain — it never passes
--force-install, never writes under content/tracks itself, and runs tools/ship_track.sh draft-only before the full run.
Plain ``test_*`` for tests/run_tests.py.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SH = ROOT / "tools" / "ship_fleet.sh"
TEXT = SH.read_text(encoding="utf-8").replace("\r\n", "\n")


def _order():
    m = re.search(r"^ORDER=\((.*?)\)$", TEXT, re.S | re.M)
    assert m, "ORDER=( ... ) not found"
    return m.group(1).split()


def test_the_order_is_one_chains_and_every_name_has_a_ship_json():
    order = _order()
    assert order[:4] == ["exotics-racing-lv", "milford-road-course", "high-plains", "sand-creek"]
    assert order[4] == "lookout-lariat"
    assert order[5:9] == ["rally-dragon-tail-gravel", "rally-under-the-dragon-gravel", "rally-dragon-tail-tarmac",
                          "rally-under-the-dragon-tarmac"]
    assert order[9] == "san-diego-freeway"
    assert order[10:] == ["pueblo", "aspen", "grand-junction", "pikes-peak"]
    for t in order:
        assert (ROOT / "tracks" / t / "ship.json").is_file(), t
    # not in the list, each for a reason docs/TRACKS.md states
    for t in ("san-diego-lake-murray", "imi", "second-creek"):
        assert t not in order, t
    assert "san-diego-lake-murray" in TEXT and "imi" in TEXT and "second-creek" in TEXT


def test_the_runner_adds_nothing_to_the_chain():
    code = "\n".join(ln for ln in TEXT.splitlines() if not ln.lstrip().startswith("#"))
    assert "--force-install" not in code, "a red build is Kevin's call per track, never this script's"
    assert "$AC/" not in code and "content/tracks" not in code, "only tools/ship_track.sh installs"
    assert 'tools/ship_track.sh" "$t" --draft-only' in code
    assert code.index('"$t" --draft-only') < code.index('"$t" ${EXTRA[@]+"${EXTRA[@]}"}'), "draft-only before the full run"
    assert "set -uo pipefail" in TEXT and "set -e" not in TEXT.replace("set -uo", ""), "a red track must not stop the fleet"


def test_list_names_the_plan_and_skips_the_deprioritised_pair():
    bash = shutil.which("bash")
    if not bash:
        print("  (no bash on PATH — skipped)")
        return
    env = dict(os.environ, AIROSO=ROOT.as_posix())
    r = subprocess.run([bash, str(SH), "--list"], capture_output=True, text=True, env=env, timeout=120)
    assert r.returncode == 0, r.stderr
    rows = {ln.split()[0]: ln.split()[1] for ln in r.stdout.splitlines() if ln.startswith("  ")}
    assert rows["rally-dragon-tail-tarmac"] == "skip" and rows["rally-under-the-dragon-tarmac"] == "skip"
    assert rows["lookout-lariat"] == "run" and rows["san-diego-freeway"] == "run" and rows["pikes-peak"] == "run"
    r2 = subprocess.run([bash, str(SH), "--list", "--include-deprioritised"], capture_output=True, text=True, env=env,
                        timeout=120)
    rows2 = {ln.split()[0]: ln.split()[1] for ln in r2.stdout.splitlines() if ln.startswith("  ")}
    assert rows2["rally-dragon-tail-tarmac"] == "run"
    r3 = subprocess.run([bash, str(SH), "--list", "imi"], capture_output=True, text=True, env=env, timeout=120)
    assert "no ship.json" in r3.stdout
    r4 = subprocess.run([bash, str(SH), "--list", "rm -rf /"], capture_output=True, text=True, env=env, timeout=120)
    assert r4.returncode == 2
