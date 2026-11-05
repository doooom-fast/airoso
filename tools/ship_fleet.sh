#!/usr/bin/env bash
# The fleet through the chain, one track after another — the matrix, holes included.
#
#   bash tools/ship_fleet.sh [--list] [--draft-only] [--include-deprioritised] [--no-install] [<track> ...]
#
# Kevin, 2026-11-01: "get a complete track list and installed by morning". docs/TRACKS.md is the list; this runs
# tools/ship_track.sh for every chain-ready track in docs/ONE-CHAIN.md §4's order (the four chain tracks first, then
# the Lariat, the rally stages, the freeway network, the Colorado circuits), on the Windows box, and writes the matrix.
# It adds nothing to the chain: every rule of tools/ship_track.sh holds — a red build is NEVER installed by this
# script (no --force-install here, ever: that is Kevin's call per track, with the July reference in the verdict), a
# refused config (the V1 frame: IMI, Second Creek) is a row that says "refused", and a track that dies is the next
# track's problem only in time. Per track: `--draft-only` first (Overpass + 3DEP + the draft's own gates), then the
# full run; a draft that stops skips the full run. Tracks whose track.config.json carries "_deprioritised" (the
# tarmac rally pair) are skipped unless --include-deprioritised. Named tracks on the command line replace the list
# (same rules). The matrix: $FLEET_OUT/fleet-<stamp>.md and .json (default D:/k10-scratch/fleet).
set -uo pipefail
export PYTHONUTF8=1
_here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && { pwd -W 2>/dev/null || pwd; })"   # the repo this script lives in
AIROSO="${AIROSO:-$_here}"   # AIROSO overrides; no machine path is spelled out (the repo moved to D:/k10/airoso, 2026-11-03)
FLEET_OUT="${FLEET_OUT:-D:/k10-scratch/fleet}"
# ONE-CHAIN §4 order (the four chain tracks first: installed 2026-10-29, re-run to the same gates)
ORDER=(exotics-racing-lv milford-road-course high-plains sand-creek
       lookout-lariat
       rally-dragon-tail-gravel rally-under-the-dragon-gravel rally-dragon-tail-tarmac rally-under-the-dragon-tarmac
       san-diego-freeway
       pueblo aspen grand-junction pikes-peak)
# not run by this script, each with its reason in docs/TRACKS.md: san-diego-lake-murray (its own chain of record,
# tools/ship_sd.sh, installed 0.19.1), imi and second-creek (fabricated geometry, L1: the chain refuses their frame)
LIST=0; DRAFT_ONLY=0; INC_DEP=0; EXTRA=()
TRACKS=()
for a in "$@"; do
  case "$a" in
    --list) LIST=1;; --draft-only) DRAFT_ONLY=1;; --include-deprioritised) INC_DEP=1;; --no-install) EXTRA+=(--no-install);;
    -*) echo "unknown flag: $a"; exit 2;;
    *) case "$a" in *[!a-z0-9-]*) echo "'$a' is not a track folder name"; exit 2;; esac; TRACKS+=("$a");;
  esac
done
[ "${#TRACKS[@]}" -gt 0 ] || TRACKS=("${ORDER[@]}")
pyq() { (cd "$AIROSO" && python -c "$@"); }
deprioritised() {  # 0 when track.config.json carries _deprioritised
  local r
  r=$(pyq "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print(1 if d.get('_deprioritised') else 0)" "$AIROSO/tracks/$1/track.config.json" 2>/dev/null)
  [ "${r%$'\r'}" = 1 ]
}
plan=()
for t in "${TRACKS[@]}"; do
  if [ ! -f "$AIROSO/tracks/$t/ship.json" ]; then plan+=("$t	skip	no ship.json (not chain-ready: docs/TRACKS.md)"); continue; fi
  if [ "$INC_DEP" = 0 ] && deprioritised "$t"; then plan+=("$t	skip	_deprioritised (track.config.json; --include-deprioritised runs it)"); continue; fi
  plan+=("$t	run	")
done
if [ "$LIST" = 1 ]; then
  echo "fleet plan (ONE-CHAIN §4 order; draft-only first, then the full run; the chain installs only green):"
  for row in "${plan[@]}"; do IFS=$'\t' read -r t act why <<< "$row"; printf '  %-32s %-5s %s\n' "$t" "$act" "$why"; done
  exit 0
fi
STAMP=$(date +%Y-%m-%d_%H%M%S)
mkdir -p "$FLEET_OUT"
MD="$FLEET_OUT/fleet-$STAMP.md"; JS="$FLEET_OUT/fleet-$STAMP.json"; LOGDIR="$FLEET_OUT/logs-$STAMP"; mkdir -p "$LOGDIR"
echo "# Fleet run $STAMP (tools/ship_fleet.sh; the chain tools/ship_track.sh per track; ONE-CHAIN §4 order)" > "$MD"
echo "" >> "$MD"; echo "| track | draft-only | full run | installed | note |" >> "$MD"; echo "|---|---|---|---|---|" >> "$MD"
echo "[" > "$JS"; first=1
row_out() {  # track draft full installed note
  local t="$1" d="$2" f="$3" i="$4" n="$5"
  echo "| $t | $d | $f | $i | $n |" >> "$MD"
  [ "$first" = 1 ] || echo "," >> "$JS"; first=0
  printf '  {"track": "%s", "draft_only_exit": "%s", "full_exit": "%s", "installed": "%s", "note": "%s"}' "$t" "$d" "$f" "$i" "${n//\"/\'}" >> "$JS"
}
for row in "${plan[@]}"; do
  IFS=$'\t' read -r t act why <<< "$row"
  if [ "$act" = skip ]; then echo; echo "### $t: SKIPPED — $why"; row_out "$t" "-" "-" "no" "$why"; continue; fi
  echo; echo "########## $t: draft-only ($(date +%H:%M:%S))"
  rc=0; bash "$AIROSO/tools/ship_track.sh" "$t" --draft-only > "$LOGDIR/$t.draft.log" 2>&1 || rc=$?
  tail -25 "$LOGDIR/$t.draft.log"
  if [ "$rc" != 0 ]; then
    if [ "$rc" = 2 ]; then note="refused before anything ran (exit 2: the frame, the spec or the inputs — see the log)"; else note="the draft stopped (exit $rc): the full run was not attempted"; fi
    row_out "$t" "$rc" "-" "no" "$note"; continue
  fi
  if [ "$DRAFT_ONLY" = 1 ]; then row_out "$t" "0" "-" "no" "--draft-only"; continue; fi
  echo; echo "########## $t: the full run ($(date +%H:%M:%S))"
  rc2=0; bash "$AIROSO/tools/ship_track.sh" "$t" ${EXTRA[@]+"${EXTRA[@]}"} > "$LOGDIR/$t.full.log" 2>&1 || rc2=$?
  tail -40 "$LOGDIR/$t.full.log"
  if grep -q "^installed: " "$LOGDIR/$t.full.log"; then inst="yes: $(grep '^installed: ' "$LOGDIR/$t.full.log" | tail -1 | cut -c12-)"; else inst="no"; fi
  if [ "$rc2" = 0 ]; then note="green"; else note="$(grep -m1 'NOT INSTALLED\|no blend yet\|refused\|FATAL' "$LOGDIR/$t.full.log" | cut -c1-160)"; fi
  row_out "$t" "0" "$rc2" "$inst" "${note:-exit $rc2}"
done
echo "" >> "$JS"; echo "]" >> "$JS"
echo; echo "matrix: $MD ($JS; logs in $LOGDIR)"; echo; cat "$MD"
