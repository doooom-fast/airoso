#!/bin/bash
# Ledger 0084 stills: the same cameras (spots.json, off the 0.1.7 line) on 0.1.5's split road scene (the Drive, read-only)
# and 0.1.7's (b17). One Blender at a time.
set -u
W=/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys/work/roadtex
A=/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys/wt-roadtex
BL=/Users/kevinconboy/.cache/prodrive-ac-builder/Blender4.2.9.app/Contents/MacOS/Blender
S=$A/tracks/milford-road-course-lm/source/road_wear/road_wear_stills_blend.py
export TMPDIR=$W/tmp
mkdir -p "$W/stills"
"$BL" --background --factory-startup --python-exit-code 1 --python "$S" -- /Volumes/Drive/codex/mf_work/v015/b1/blender/split/loop_main.blend "$W/stills/v015" "$W/spots.json" > "$W/stills/v015.log" 2>&1
echo "0.1.5 exit $?"
"$BL" --background --factory-startup --python-exit-code 1 --python "$S" -- "$W/b17/blender/split/loop_main.blend" "$W/stills/v017" "$W/spots.json" > "$W/stills/v017.log" 2>&1
echo "0.1.7 exit $?"
grep "\[stills\]" "$W/stills/v015.log" "$W/stills/v017.log" | head -4
