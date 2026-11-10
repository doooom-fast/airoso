#!/bin/bash
# The exporter A/B without the key (ledger 0084): engine-july's export_kn5_addon.py as the base had it (mf_work/eng2,
# md5 1bdc2628) and as this branch has it (83b231e8), each run on the A side's (a17, no road_wear key) split road scene,
# each into its own project copy. The kn5s and the .ini must be byte-identical.
set -u
W=/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys/work/roadtex
BL=/Users/kevinconboy/.cache/prodrive-ac-builder/Blender4.2.9.app/Contents/MacOS/Blender
q=0
while [ $q -lt 30 ]; do
  if pgrep -x blender >/dev/null || pgrep -x Blender >/dev/null; then q=0; else q=$((q+1)); fi
  sleep 2
done
export TMPDIR=$W/tmp
for side in old new; do
  P=$W/ex_$side; rm -rf "$P"; mkdir -p "$P/build" "$P/data"
  cp "$W/a17/track.config.json" "$P/"
  cp -R "$W/a17/textures" "$P/textures"; [ -d "$W/a17/assets" ] && cp -R "$W/a17/assets" "$P/assets"
  if [ $side = old ]; then E=/Volumes/Drive/codex/mf_work/eng2; else E=$W/eng; fi
  echo "$side: $(md5 -q $E/scripts/ac/export_kn5_addon.py)"
  "$BL" --background --python-exit-code 1 --python "$E/scripts/ac/export_kn5_addon.py" -- "$P" --blend "$W/a17/blender/split/loop_main.blend" > "$W/ex_$side.log" 2>&1
  echo "$side exit $?: $(grep 'KN5 EXISTS\|INI materials' $W/ex_$side.log | tr '\n' ' ')"
done
echo "kn5 old $(md5 -q $W/ex_old/build/milford_road_course.kn5) new $(md5 -q $W/ex_new/build/milford_road_course.kn5) a17-chain $(md5 -q $W/a17/build/milford_road_course.kn5)"
echo "ini old $(md5 -q $W/ex_old/build/milford_road_course.ini) new $(md5 -q $W/ex_new/build/milford_road_course.ini) a17-chain $(md5 -q $W/a17/build/milford_road_course.ini)"
