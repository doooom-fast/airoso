#!/bin/bash
# Lake Murray unchanged (Milford 0.1.11): the diff, the trim A/B and the make_treefx A/B (as ledger 0082 P4.5), fleet-lm-engine's
# tools and 0.1.10's make_treefx against this branch's.
set -u
S=<scratchpad>/sys
A=$S/wt-mf0111
T=$S/work/mf0111/lmcheck
PY=/Volumes/Drive/codex/airoso/.venv/bin/python
export TMPDIR=$S/work/mf0111/tmp
rm -rf "$T"; mkdir -p "$T/eng_fle"
cd "$A" || exit 1
echo "head $(git rev-parse --short HEAD)"
echo "diff vs origin/claude/milford-0110 (this branch's base), tracks/san-diego-lake-murray: $(git diff origin/claude/milford-0110 --stat -- tracks/san-diego-lake-murray | wc -l | tr -d ' ') lines"
echo "diff vs origin/claude/milford-0110, scripts/ + tools/:"; git diff origin/claude/milford-0110 --stat -- scripts tools
git archive -o "$T/eng_fle.tar" origin/claude/fleet-lm-engine tools scripts
tar -x -C "$T/eng_fle" -f "$T/eng_fle.tar"
for side in a_fle b_branch; do
  mkdir -p "$T/$side/data"
  cp "$A/tracks/san-diego-lake-murray/track.config.json" "$T/$side/"
  cp "$A/tracks/san-diego-lake-murray/data/centerline.local.json" "$A/tracks/san-diego-lake-murray/data/connectors.local.json.pre-trim" "$T/$side/data/"
  [ -f "$A/tracks/san-diego-lake-murray/data/median_bands.json" ] && cp "$A/tracks/san-diego-lake-murray/data/median_bands.json" "$T/$side/data/"
done
(cd "$T/eng_fle" && PYTHONUTF8=1 "$PY" tools/trim_connectors.py "$T/a_fle" > "$T/a_fle.log" 2>&1)
(cd "$A" && PYTHONUTF8=1 "$PY" tools/trim_connectors.py "$T/b_branch" > "$T/b_branch.log" 2>&1)
for side in a_fle b_branch; do
  echo "trim $side: $(md5 -q $T/$side/data/connectors.local.json) $(md5 -q $T/$side/data/mouths.json) $(md5 -q $T/$side/data/median_bands.json 2>/dev/null) log $(md5 -q $T/$side.log)"
done
git show origin/claude/milford-0110:tools/make_treefx.py > "$T/make_treefx_0110.py"
echo "== make_treefx A/B: fleet-lm-engine vs this branch"
cd "$A" && PYTHONUTF8=1 "$PY" /Volumes/Drive/codex/mf_work/veg/lmcheck/ab_treefx.py "$A" "$T/eng_fle/tools/make_treefx.py"
echo "== make_treefx A/B: 0.1.10 (origin/claude/milford-0110) vs this branch"
cd "$A" && PYTHONUTF8=1 "$PY" /Volumes/Drive/codex/mf_work/veg/lmcheck/ab_treefx.py "$A" "$T/make_treefx_0110.py"
