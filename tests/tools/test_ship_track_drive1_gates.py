"""tools/ship_track.sh — the Lariat's Drive-1 road gates block (V3-PLAN P5, ledger 0048), pinned on the script text
and the Lariat's ship.json:

- gate_road_inventory / gate_stacked_legs live in ONE marked block after the existing vocabulary (the San Diego
  re-sync edits the functions above it; nothing here reorders or rewrites them);
- each removes its stale report, runs its tool on the absolute project, and collects its exit in D1_G;
- the verdict reads D1_G: red stops the install, --force-install passes it (as for the street drive_test / audit);
- the Lariat's ship.json runs both after the gate OBJ exists, syncs the exemption file in and both reports out.
Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEXT = (ROOT / "tools" / "ship_track.sh").read_text(encoding="utf-8").replace("\r\n", "\n")
sys.path.insert(0, str(ROOT / "tools"))
import ship_track_spec as spec_mod  # noqa: E402

MARK = "# LARIAT DRIVE-1 GATES"


def _body(fn: str) -> str:
    m = re.search(rf"^{fn}\(\) \{{\n(.*?)^\}}\n", TEXT, re.S | re.M)
    assert m, fn
    return m.group(1)


def test_the_block_is_one_marked_block_after_the_existing_vocabulary():
    i = TEXT.find(MARK)
    assert i > 0 and TEXT.count(MARK) == 1
    assert TEXT.find("gate_race_gates() {") < i < TEXT.find("is_data_step() {")
    for fn in ("gate_road_inventory", "gate_stacked_legs"):
        assert i < TEXT.find(f"{fn}() {{") < TEXT.find("is_data_step() {"), fn
    # every other vocabulary function still precedes the block
    names = re.findall(r"^((?:draft|author|prep|ship|gate)_[a-z0-9_]+)\(\) \{", TEXT, re.M)
    after = [n for n in names if TEXT.find(f"{n}() {{") > i]
    assert after == ["gate_road_inventory", "gate_stacked_legs", "gate_drive1_verdict"], after   # + the verdict (793441f, on main 2026-11-01)


def test_each_gate_removes_its_stale_report_runs_its_tool_and_collects_its_exit():
    for fn, tool, report in (("gate_road_inventory", "tools/verify_road_inventory.py", "road_inventory.json"),
                             ("gate_stacked_legs", "tools/verify_stacked_legs.py", "stacked_legs.json")):
        b = _body(fn)
        assert f'rm -f "$PROJ/data/{report}"' in b
        assert f'python {tool} "$PROJ"' in b and '(cd "$AIROSO"' in b
        assert '[ "$rc" = 0 ] || D1_G=$rc' in b
        assert b.find("rm -f") < b.find(f"python {tool}")


def test_the_verdict_stops_a_red_install_unless_forced():
    i = TEXT.find('echo "  Drive-1 road gates')
    assert i > TEXT.find('echo "  race layouts red on their own gates')
    block = TEXT[i:TEXT.find('if [ "$DT_S" != 0 ]', i)]
    assert 'if [ "$D1_G" != 0 ]; then' in block
    assert 'if [ "$FORCE" = 1 ]; then' in block and "NOT INSTALLED" in block and "exit 1" in block
    assert TEXT.find("D1_G=0") < TEXT.find('for n in ${GATE[@]+"${GATE[@]}"}; do "gate_$n"; done')


def test_the_lariat_runs_both_gates_on_the_built_road_and_syncs_their_files():
    s = spec_mod.load(ROOT / "tracks" / "lookout-lariat" / "ship.json", "lookout-lariat")
    # road_obj (the gate OBJ off the shipped kn5) is a SHIP step on main since 2026-10-11 (make_treefx / ext_config read
    # the tile names off it before the track folder); the two gates follow it in the ship + gate order
    g = s["steps"]["ship"] + s["steps"]["gate"]
    assert g.index("road_obj") < g.index("road_inventory") and g.index("road_obj") < g.index("stacked_legs")
    assert "pavement_exemptions.json" in s["sync_in"]["required"]
    for f in ("data/road_inventory.json", "data/stacked_legs.json"):
        assert f in s["sync_out"]["files"], f
    assert (ROOT / "tracks" / "lookout-lariat" / "pavement_exemptions.json").exists()
    # San Diego's chain is not touched by the block (its ship.json never names these gates)
    sd = spec_mod.load(ROOT / "tracks" / "san-diego-lake-murray" / "ship.json", "san-diego-lake-murray")
    assert "road_inventory" not in sd["steps"]["gate"] and "stacked_legs" not in sd["steps"]["gate"]


def test_the_summary_line_names_each_gates_own_exit():
    # 2026-11-03 (ledger 0048): "Drive-1 road gates (road inventory, stacked legs): exit 1" printed the verdict's exit
    # beside two gates that had both passed
    assert 'echo "  Drive-1 road gates (road inventory, stacked legs): exit $D1_G"' not in TEXT
    assert "road inventory exit $D1_RI, stacked legs exit $D1_SL, the Drive-1 verdict exit $D1_V" in TEXT
    for fn, var in (("gate_road_inventory", "D1_RI"), ("gate_stacked_legs", "D1_SL"), ("gate_drive1_verdict", "D1_V")):
        b = _body(fn)
        assert f"{var}=$rc" in b and '[ "$rc" = 0 ] || D1_G=$rc' in b, fn
    assert TEXT.find("D1_RI=-; D1_SL=-; D1_V=-") < TEXT.find('for n in ${GATE[@]+"${GATE[@]}"}; do "gate_$n"; done')
