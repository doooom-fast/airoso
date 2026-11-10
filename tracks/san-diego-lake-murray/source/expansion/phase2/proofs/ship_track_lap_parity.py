"""Parity harness for tools/ship_track.sh's lap port (ledger 0054 Phase 2): extract the race-touching functions from a
ship_track.sh, run them under stubs (python / blender / pyq log their argv; nothing runs) and log every command, so the
old script and the new one can be diffed command for command on Lake Murray's layouts (no lap) — and the new one shown
on the north lap. bash 3.2 here (the Mac): `${tok^^}` and the RK / BB associative arrays are rewritten identically for
both scripts (an upper-casing helper; rk_of / bb_of lookups), nothing else is touched.

    python ship_track_lap_parity.py <ship_track.sh> <out.sh> <case: nolap|lap> <proj dir> <log file>
    bash <out.sh>        # then diff the two logs (proj dir paths normalised)

2026-11-04 on the Mac, ship_track.sh before (2ce9495) vs after the port, case nolap: every logged command identical
but two, both intended — the ported `rm -f build/<slug>_race_*.kn5` (ship_sd.sh's: a retired lap's common kn5 never
rides along; matches nothing on Lake Murray's workshop) and the new {lap} sync_out template, which expands to nothing.
"""
import re
import sys
from pathlib import Path

src, out, case, proj, log = sys.argv[1:6]
text = Path(src).read_text(encoding="utf-8")
FUNCS = ["author_race_bands", "author_race_planned_gate", "author_race_author", "author_race_verify", "prep_split",
         "ship_export_race", "ship_ai", "ai_layout", "ship_race_scenery_gate", "gate_race_gates", "gate_kn5_ground",
         "expand"]
bodies = []
for f in FUNCS:
    m = re.search(r"^" + f + r"\(\) \{\n.*?^\}\n", text, re.M | re.S)
    if not m:
        raise SystemExit(f"no function {f}")
    bodies.append(m.group(0))
code = "\n".join(bodies)
code = code.replace("${tok^^}", "$(upper \"$tok\")")
code = code.replace("${RK[$lid]}", "$(rk_of \"$lid\")").replace("${BB[$lid]}", "$(bb_of \"$lid\")")
if case == "nolap":
    lays = "street race_cw race_acw"
    race = "race_cw race_acw"
    laps = ""
    has_main = 1
    rk = 'rk_of() { printf "%s" "${SLUG}_race.kn5"; }\nbb_of() { printf "%s" barrier_bands.json; }'
else:
    lays = "street race_cw race_acw north_cw north_acw"
    race = "race_cw race_acw north_cw north_acw"
    laps = "north"
    has_main = 1
    rk = ('rk_of() { case "$1" in north_*) printf "%s" "${SLUG}_race_north.kn5";; *) printf "%s" "${SLUG}_race.kn5";; esac; }\n'
          'bb_of() { case "$1" in north_*) printf "%s" barrier_bands.north.json;; *) printf "%s" barrier_bands.json;; esac; }')
head = f"""#!/bin/bash
LOG="{log}"
: > "$LOG"
PROJ="{proj}"; AIROSO="{proj}/airoso"; WS="{proj}/ws"; ENGINE="{proj}/engine"; SLUG=san_diego_lake_murray
LAYOUT_IDS="{lays}"; RACE_IDS="{race}"; STREET_IDS="street"; BARE_RACE_IDS=""; LAP_IDS="{laps}"; HAS_MAIN={has_main}
STREET_AI=draft; JULY_AI="{proj}/july"
mkdir -p "$AIROSO" "$WS" "$ENGINE" "$PROJ/build" "$PROJ/data" "$PROJ/blender/split" "$PROJ/ai"
for lid in $RACE_IDS; do : > "$PROJ/blender/split/loop_closure_$lid.blend"; done
for lap in $LAP_IDS; do : > "$PROJ/blender/split/loop_race_$lap.blend"; done
: > "$PROJ/build/${{SLUG}}_race_stale.kn5"
upper() {{ printf '%s' "$1" | tr a-z A-Z; }}
{rk}
step() {{ echo "STEP $1" >> "$LOG"; }}
no_race() {{ echo "NO_RACE $1" >> "$LOG"; }}
pyq() {{ echo "pyq ${{*: -2}}" >> "$LOG"; case "$*" in *corridors*) printf 'tok_%s\\n' "${{@: -1}}";; *) printf '1\\n';; esac; }}
python() {{ echo "python $* (cwd ${{PWD#$PROJ}})" >> "$LOG"; }}
blstub() {{ echo "blender $*" >> "$LOG"; echo "KN5 EXISTS"; echo "[race] stub"; echo "[split] stub"; }}
BL=blstub
grep() {{ command grep "$@" || true; }}
"""
tail = """
for f in author_race_bands author_race_planned_gate author_race_author author_race_verify prep_split ship_export_race ship_ai \\
         ship_race_scenery_gate gate_race_gates gate_kn5_ground; do
  echo "== $f" >> "$LOG"; "$f" > /dev/null 2>> "$LOG.err"; echo "   rc $?" >> "$LOG"
done
echo "== stale lap kn5 left: $(ls "$PROJ/build" | tr '\\n' ' ')" >> "$LOG"
for p in data/barrier_bands.json data/dummies_{id}.json data/no_route.{race}.json data/lap.{lap}.json data/race_{lap}.kn5.json; do
  echo "expand $p -> $(expand "$p" | tr '\\n' ' ')" >> "$LOG"
done
"""
Path(out).write_text(head + code + tail, encoding="utf-8")
