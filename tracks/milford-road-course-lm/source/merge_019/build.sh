#!/bin/bash
# Milford 0.1.9 (0.1.7 road wear + 0.1.8 furniture pass 3): tools/ship_track.sh with the Mac Blender from an EMPTY workshop,
# --no-install, no force; 0.1.7's recipe (source/road_wear/mac_017/build.sh) on the system disk. ENG = mf_work/eng2 with
# 0.1.7's export_kn5_addon.py (md5 83b231e8); the two 82 B TreeFX placeholders in the worktree (gitignored, never committed).
set -u
N="$1"
W=/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys/work/mf019
A="${2:-/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys/wt-mf019}"
q=0
while [ $q -lt 30 ]; do
  if pgrep -x blender >/dev/null || pgrep -x Blender >/dev/null; then q=0; else q=$((q+1)); fi
  sleep 2
done
mkdir -p "$W/tmp"
export TMPDIR="$W/tmp"
cp "$A/tools/ship_track.sh" "$W/ship_track_mac_$N.sh"
sed -i '' 's#^BL="C:/Program Files/Blender Foundation/Blender 4.2/blender.exe"#BL="/Users/kevinconboy/.cache/prodrive-ac-builder/Blender4.2.9.app/Contents/MacOS/Blender"#' "$W/ship_track_mac_$N.sh"
grep -q '^BL="/Users/kevinconboy' "$W/ship_track_mac_$N.sh" || { echo "the Blender path was not replaced"; exit 2; }
rm -rf "$W/$N"; mkdir -p "$W/$N/data"
mkdir -p "$W/D:/k10-scratch"
cd "$W" || exit 1
{ echo "quiet at $(date +%T); $(df -h /System/Volumes/Data | tail -1)"; echo "head $(git -C "$A" rev-parse HEAD)"; } > "$W/$N.log"
export SHIP_PROJ="$W/$N" AIROSO="$A" ENG="$W/eng" PYTHONUTF8=1 PATH="/Volumes/Drive/codex/mf_work/veg/shim:/Volumes/Drive/codex/airoso/.venv/bin:$PATH"
bash "$W/ship_track_mac_$N.sh" milford-road-course-lm --no-install >> "$W/$N.log" 2>&1
echo "exit $?" >> "$W/$N.log"
date +"end %T" >> "$W/$N.log"
tail -2 "$W/$N.log"
