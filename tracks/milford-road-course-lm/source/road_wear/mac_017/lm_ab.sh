#!/bin/bash
# Lake Murray unchanged by Milford 0.1.7 (ledger 0084): the diff under tracks/san-diego-lake-murray against the base,
# the engine files' md5 against the base, the config's keys, and the trim A/B (base tools vs this branch's), as
# mf_work/v015/lm_checks.sh did for 0.1.5.
set -u
A=/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys/wt-roadtex
T=/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys/work/roadtex/lmcheck
PY=/Volumes/Drive/codex/airoso/.venv/bin/python
BASE=d8d1473
rm -rf "$T"; mkdir -p "$T/base"
cd "$A" || exit 1
echo "== diff vs $BASE under tracks/san-diego-lake-murray:"; git diff --stat "$BASE" -- tracks/san-diego-lake-murray
echo "== diff vs $BASE under scripts/:"; git diff --stat "$BASE" -- scripts
for f in scripts/ac/build_kn5_loop.py scripts/ac/build_spawn_kn5.py scripts/ac/pbr.py scripts/geometry/dummies.py tools/ship_sd.sh tools/trim_connectors.py; do
  for root in tracks/san-diego-lake-murray/engine-july-snapshot/ ""; do
    p="$root$f"; [ -f "$p" ] || continue
    printf '%s  base %s  branch %s\n' "$p" "$(git show "$BASE:$p" | md5 -q)" "$(md5 -q "$p")"
  done
done
echo "== the export driver: the one engine-july file this branch changes"
printf 'base %s  branch %s  (snapshot copy %s; ENG copy %s)\n' "$(git show "$BASE:scripts/ac/export_kn5_addon.py" | md5 -q)" "$(md5 -q scripts/ac/export_kn5_addon.py)" "$(md5 -q tracks/san-diego-lake-murray/engine-july-snapshot/scripts/ac/export_kn5_addon.py)" "$(md5 -q /private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys/work/roadtex/eng/scripts/ac/export_kn5_addon.py)"
echo "== Lake Murray's config names road_wear: $($PY -c "import json; print('road_wear' in json.load(open('tracks/san-diego-lake-murray/track.config.json')))")"
echo "== ship_sd.sh mentions road_wear: $(grep -c road_wear tools/ship_sd.sh)"
git archive -o "$T/base.tar" "$BASE" tools scripts
tar -x -C "$T/base" -f "$T/base.tar"
for side in a_base b_branch; do
  mkdir -p "$T/$side/data"
  cp tracks/san-diego-lake-murray/track.config.json "$T/$side/"
  cp tracks/san-diego-lake-murray/data/centerline.local.json tracks/san-diego-lake-murray/data/connectors.local.json.pre-trim "$T/$side/data/"
  [ -f tracks/san-diego-lake-murray/data/median_bands.json ] && cp tracks/san-diego-lake-murray/data/median_bands.json "$T/$side/data/"
done
(cd "$T/base" && PYTHONUTF8=1 "$PY" tools/trim_connectors.py "$T/a_base" > "$T/a_base.log" 2>&1)
(cd "$A" && PYTHONUTF8=1 "$PY" tools/trim_connectors.py "$T/b_branch" > "$T/b_branch.log" 2>&1)
for side in a_base b_branch; do
  echo "trim $side: $(md5 -q "$T/$side/data/connectors.local.json") $(md5 -q "$T/$side/data/mouths.json") $(md5 -q "$T/$side/data/median_bands.json" 2>/dev/null) log $(md5 -q "$T/$side.log")"
done
