#!/bin/bash
# Lake Murray unchanged by Milford 0.1.9 (0.1.7 + 0.1.8): the diff under tracks/san-diego-lake-murray against the shared base
# d8d1473 (0.1.6), the engine files' md5, the config's keys, the trim A/B and the make_treefx A/B (base tools vs this branch's),
# as source/road_wear/mac_017/lm_ab.sh (0.1.7) and 0.1.8's lm_checks.sh did. ab_treefx.py = mf_work/veg/lmcheck/ab_treefx.py.
set -u
S=/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys
A=$S/wt-mf019
T=$S/work/mf019/lmcheck
PY=/Volumes/Drive/codex/airoso/.venv/bin/python
BASE=d8d1473
export TMPDIR=$S/work/mf019/tmp
rm -rf "$T"; mkdir -p "$T/base" "$TMPDIR"
cd "$A" || exit 1
echo "== head $(git rev-parse --short HEAD)"
echo "== diff vs $BASE under tracks/san-diego-lake-murray:"; git diff --stat "$BASE" -- tracks/san-diego-lake-murray
echo "== the same diff's changed lines:"; git diff "$BASE" -- tracks/san-diego-lake-murray | grep '^[-+]' | grep -v '^+++\|^---'
echo "== diff vs 0.1.7 (7e95074) under tracks/san-diego-lake-murray: $(git diff --stat 7e95074 -- tracks/san-diego-lake-murray | wc -l | tr -d ' ') lines"
for f in scripts/ac/build_kn5_loop.py scripts/ac/build_spawn_kn5.py scripts/ac/pbr.py scripts/geometry/dummies.py tools/ship_sd.sh tools/trim_connectors.py tools/make_treefx.py; do
  for root in tracks/san-diego-lake-murray/engine-july-snapshot/ ""; do
    p="$root$f"; [ -f "$p" ] || continue
    printf '%s  base %s  branch %s\n' "$p" "$(git show "$BASE:$p" | md5 -q)" "$(md5 -q "$p")"
  done
done
printf 'export driver: base %s  branch %s  (snapshot copy %s; ENG copy %s)\n' "$(git show "$BASE:scripts/ac/export_kn5_addon.py" | md5 -q)" "$(md5 -q scripts/ac/export_kn5_addon.py)" "$(md5 -q tracks/san-diego-lake-murray/engine-july-snapshot/scripts/ac/export_kn5_addon.py)" "$(md5 -q $S/work/mf019/eng/scripts/ac/export_kn5_addon.py)"
echo "== Lake Murray's config names road_wear: $($PY -c "import json; print('road_wear' in json.load(open('tracks/san-diego-lake-murray/track.config.json')))")"
echo "== Lake Murray's config names reseat_on_prep / roof_z_m: $(grep -c 'reseat_on_prep\|roof_z_m' tracks/san-diego-lake-murray/track.config.json)"
echo "== ship_sd.sh mentions road_wear / reseat: $(grep -c 'road_wear\|reseat' tools/ship_sd.sh)"
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
echo "== make_treefx A/B (base $BASE vs branch; every track naming scenery.treefx but Milford)"
PYTHONUTF8=1 "$PY" "$A/tracks/milford-road-course-lm/source/merge_019/ab_treefx.py" "$A" "$T/base/tools/make_treefx.py"
