#!/bin/bash
# re-shoot 0.1.7 only (the stand-in now ignores the macro's alpha), after no blender has run for 60 s
set -u
W=/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys/work/roadtex
A=/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys/wt-roadtex
BL=/Users/kevinconboy/.cache/prodrive-ac-builder/Blender4.2.9.app/Contents/MacOS/Blender
q=0
while [ $q -lt 30 ]; do
  if pgrep -x blender >/dev/null || pgrep -x Blender >/dev/null; then q=0; else q=$((q+1)); fi
  sleep 2
done
export TMPDIR=$W/tmp
"$BL" --background --factory-startup --python-exit-code 1 --python "$A/tracks/milford-road-course-lm/source/road_wear/road_wear_stills_blend.py" -- "$W/b17/blender/split/loop_main.blend" "$W/stills/v017" "$W/spots.json" > "$W/stills/v017.log" 2>&1
echo "0.1.7 exit $?"
