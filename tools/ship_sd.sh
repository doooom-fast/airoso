#!/usr/bin/env bash
# The San Diego ship chain — draft → author → gate → install, one command, exits nonzero on any gate.
#
#   bash tools/ship_sd.sh [--no-install] [--skip-blend]
#
# Runs in the v021 workshop (C:/Users/Owner/Documents/GitHub/k10-sd-v021) because the loop
# assembler + prep/export live there at the pin that built the drive-feel reference; the V3 tools
# (median, trim, gap, start) run from airoso. Source of truth stays tracks/san-diego-lake-murray/
# in airoso: edit there, this script syncs the inputs down and the outputs back up.
#
# Stages (V3-PLAN §Phase 1 "the ONE pipeline"):
#   draft  : median_envelope → trim_connectors → build_loop_blend        (GEN layer, regenerable)
#   author : author_median_blend → gap_mouths_blend                      (scripted authoring)
#   ship   : build_kn5_loop prep → set_start → export → verify → folder  (kn5)
#   gate   : kn5_to_gate_obj → drive_test → audit_mesh                   (deterministic gates)
#   install: copy to AC as san_diego_lake_murray_v3 + the reference's recorded AI line
set -euo pipefail
export PYTHONUTF8=1
AIROSO="C:/Users/Owner/Documents/GitHub/airoso"
WS="C:/Users/Owner/Documents/GitHub/k10-sd-v021"
PROJ="$WS/project"
SRC="$AIROSO/tracks/san-diego-lake-murray"
ENG="C:/Users/Owner/Documents/GitHub/engine-july"
BL="C:/Program Files/Blender Foundation/Blender 4.2/blender.exe"
AC="D:/SteamLibrary/steamapps/common/assettocorsa/content/tracks"
SLUG="san_diego_lake_murray"
INSTALL=1; SKIP_BLEND=0; FORCE=0
for a in "$@"; do case "$a" in --no-install) INSTALL=0;; --skip-blend) SKIP_BLEND=1;; --force-install) FORCE=1;; esac; done
# --force-install: the gates have never passed on this track (the July reference fails them too,
# on inherited defects). During the campaign a build may be installed red ONLY when it is no worse
# than the reference on every gate metric; the caller owns that comparison and the handoff note
# must say so. This flag is the honest version of the old GATE_*_ADVISORY env vars: loud, per-run,
# never silent.

step() { echo; echo "=================== $1"; }

step "sync inputs airoso -> workshop"
cp "$SRC/track.config.json" "$PROJ/track.config.json"
cp "$SRC/start_positions.json" "$PROJ/start_positions.json"
for f in centerline.raw.local.json.pre-median connectors.local.json.pre-trim; do
  [ -f "$SRC/data/$f" ] && cp "$SRC/data/$f" "$PROJ/data/$f"
done
mkdir -p "$PROJ/source/trees" && cp "$SRC/source/trees/"*.bin "$PROJ/source/trees/" 2>/dev/null || true   # TreeFX models (gitignored, personal use)

if [ "$SKIP_BLEND" = 0 ]; then
  step "draft: median envelope (self-gated)"
  (cd "$AIROSO" && python tools/median_envelope.py "$PROJ")
  step "draft: build loop.blend (scene regen — GEN layer)"
  (cd "$WS" && "$BL" --background --python scripts/blender/build_loop_blend.py -- project 2>&1 | grep "^\[blend\]" | tail -4)
  step "draft: divided side streets -> one trunk + island (Del Cerro)"
  (cd "$AIROSO" && python tools/divide_connectors.py "$PROJ")
  step "draft: trim connectors at the mainline edge"
  (cd "$AIROSO" && python tools/trim_connectors.py "$PROJ")
  step "draft: rebuild loop.blend with trimmed connectors"
  (cd "$WS" && "$BL" --background --python scripts/blender/build_loop_blend.py -- project 2>&1 | grep "^\[blend\]" | tail -3)
  step "author: median island"
  (cd "$WS" && "$BL" --background --python "$AIROSO/tools/author_median_blend.py" -- project 2>&1 | grep "^\[median" )
  step "author: gap the mainline sidewalk at every mouth"
  (cd "$WS" && "$BL" --background --python "$AIROSO/tools/gap_mouths_blend.py" -- project 2>&1 | grep "^\[gap" )
  step "author: export scatter positions, strip procedural vegetation (TreeFX replaces it)"
  (cd "$WS" && "$BL" --background --python "$AIROSO/tools/export_scatter_blend.py" -- project 2>&1 | grep "^\[scatter" )
  (cd "$WS" && "$BL" --background --python "$AIROSO/tools/strip_scenery_blend.py" -- project 2>&1 | grep "^\[strip" | cut -c1-160 )
  step "author: Kevin's lamp model at every streetlight (LIGHTPOST + LIGHTS lens)"
  (cd "$WS" && "$BL" --background --python "$AIROSO/tools/author_lamps_blend.py" -- project 2>&1 | grep "^\[lamps\]\|Error\|Traceback" )
fi

step "ship: prep (AC naming, dummies, 65k splits)"
"$BL" --background --python "$ENG/scripts/ac/build_kn5_loop.py" -- "$PROJ" 2>&1 | grep "prepped" | cut -c1-120
step "ship: per-issue start position"
"$BL" --background --python "$AIROSO/tools/set_start_blend.py" -- "$PROJ" 2>&1 | grep "^\[set-start\]"
step "ship: export kn5"
"$BL" --background --python "$ENG/scripts/ac/export_kn5_addon.py" -- "$PROJ" 2>&1 | grep "KN5 EXISTS"
step "ship: verify_kn5 (hard)"
(cd "$ENG" && python -m scripts.ac.verify_kn5 "$PROJ")
step "ship: track folder"
(cd "$ENG" && python -m scripts.ac.track_folder "$PROJ") | grep -E "wrote|length_m|n_pits"
cp "$PROJ/build/$SLUG.kn5" "$PROJ/build/$SLUG/"
step "ship: minimap in the KN5 frame (track_folder draws it mirrored — tools/make_map.py)"
(cd "$AIROSO" && python tools/make_map.py "$PROJ")
step "ship: TreeFX palms / street trees / scrub (tools/make_treefx.py)"
(cd "$AIROSO" && python tools/make_treefx.py "$PROJ")

step "gate: kn5 -> gate OBJ (engine frame) + gate centreline"
(cd "$AIROSO" && python -m scripts.modkit.kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5")
step "gate: drive_test (hard)"
DT=0; (cd "$AIROSO" && python -m scripts.geometry.drive_test "$PROJ" 2>&1 | grep -v drive-time | tail -14) || DT=$?
step "gate: audit_mesh (hard total; K advisory until C2 lands)"
AU=0; (cd "$AIROSO" && python -m scripts.geometry.audit_mesh "$PROJ" 2>&1 | tail -16) || AU=$?

step "sync outputs workshop -> airoso"
cp "$PROJ/loop.blend" "$SRC/loop.blend"
for f in centerline.local.json centerline.raw.local.json median_bands.json dummies.json \
         finished_centerline.json gate_centerline.json lights.local.json connectors.local.json \
         mouths.json drive_test.json audit.json; do
  [ -f "$PROJ/data/$f" ] && cp "$PROJ/data/$f" "$SRC/data/$f"
done

if [ "$DT" != 0 ] || [ "$AU" != 0 ]; then
  echo; echo "GATES: drive_test exit $DT, audit exit $AU"
  if [ "$FORCE" = 1 ]; then
    echo "  --force-install: installing RED (caller asserts no metric is worse than the July reference)"
  else
    echo "  NOT INSTALLED (Kevin never loads a build the machine failed)"; exit 1
  fi
fi
if [ "$INSTALL" = 1 ]; then
  step "install: $AC/${SLUG}_v3"
  B="$PROJ/build/$SLUG"
  cp "$AC/$SLUG/ai/fast_lane.ai" "$AC/$SLUG/ai/pit_lane.ai" "$AC/$SLUG/ai/side_l.csv" "$AC/$SLUG/ai/side_r.csv" "$B/ai/"
  if [ -d "$AC/${SLUG}_v3" ]; then rm -rf "$AC/${SLUG}_v3_prev"; mv "$AC/${SLUG}_v3" "$AC/${SLUG}_v3_prev"; fi
  cp -r "$B" "$AC/${SLUG}_v3"
  python - <<PY
import json
p = r"$AC/${SLUG}_v3/ui/ui_track.json"
d = json.load(open(p, encoding="utf-8"))
d["name"] = "K10 - San Diego (V3)"
json.dump(d, open(p, "w", encoding="utf-8"), indent=2)
print("installed:", d["name"], d.get("version"))
PY
fi
echo; echo "SHIP OK"
