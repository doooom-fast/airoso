#!/bin/bash
# Milford 0.1.7 (ledger 0084 road wear): tools/ship_track.sh with the Mac Blender from an EMPTY workshop, --no-install, no
# force, as 0.1.5's mf_work/v015/build.sh (ledger 0082 M.5 / 0087) but on the system disk (the Drive stopped creating
# files 2026-11-09 13:35). $1 = workshop name (b17 = the branch; a17 = the no-key A side); $2 = the airoso tree (default the
# branch worktree; the A side = a second worktree at the same commit with road_wear taken out of the config and ship.json). ENG = engine-july's 0.1.5 copy (mf_work/eng2) with this branch's
# export_kn5_addon.py; the two 82 B TreeFX placeholders copied into the worktree (gitignored, never committed).
set -u
N="$1"
W=/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys/work/roadtex
A="${2:-/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys/wt-roadtex}"
q=0
while [ $q -lt 30 ]; do
  if pgrep -x blender >/dev/null || pgrep -x Blender >/dev/null; then q=0; else q=$((q+1)); fi
  sleep 2
done
echo "quiet at $(date +%T); $(df -h /System/Volumes/Data | tail -1)"
mkdir -p "$W/tmp"
export TMPDIR="$W/tmp"
cp "$A/tools/ship_track.sh" "$W/ship_track_mac_$N.sh"
sed -i '' 's#^BL="C:/Program Files/Blender Foundation/Blender 4.2/blender.exe"#BL="/Users/kevinconboy/.cache/prodrive-ac-builder/Blender4.2.9.app/Contents/MacOS/Blender"#' "$W/ship_track_mac_$N.sh"
grep -q '^BL="/Users/kevinconboy' "$W/ship_track_mac_$N.sh" || { echo "the Blender path was not replaced"; exit 2; }
rm -rf "$W/$N"; mkdir -p "$W/$N/data"
mkdir -p "$W/D:/k10-scratch"
cd "$W" || exit 1
export SHIP_PROJ="$W/$N" AIROSO="$A" ENG="$W/eng" PYTHONUTF8=1 PATH="/Volumes/Drive/codex/mf_work/veg/shim:/Volumes/Drive/codex/airoso/.venv/bin:$PATH"
bash "$W/ship_track_mac_$N.sh" milford-road-course-lm --no-install > "$W/$N.log" 2>&1
echo "exit $?" >> "$W/$N.log"
tail -1 "$W/$N.log"
