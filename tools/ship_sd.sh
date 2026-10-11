#!/usr/bin/env bash
# The San Diego ship chain — draft → author → ship → gate → install, one command, exits nonzero on any gate.
#
#   bash tools/ship_sd.sh [--no-install] [--skip-blend] [--force-install] [--dry-run]
#
# Runs in the v021 workshop (C:/Users/Owner/Documents/GitHub/k10-sd-v021) because the loop
# assembler + prep/export live there at the pin that built the drive-feel reference; the V3 tools
# (median, trim, gap, signs, race furniture, dummies, the packer and every gate) run from airoso.
# Source of truth stays tracks/san-diego-lake-murray/ in airoso: edit there, this script syncs the
# inputs down and the outputs back up.
#
# THREE VERSIONS (ledger 0047, Kevin 2026-10-10): `street` (the open two-way loop as today),
# `race_cw` and `race_acw` (the loop as a one-way race track in each direction). One shared ROAD
# kn5 (no AC_* nodes) + one RACE-FURNITURE kn5 (centre K-rail chain, kerb-line barriers, race
# kerbs — loaded by the two race layouts only) + one nodes-only SPAWN kn5 per layout
# (fleet/LAWS.md L8 as amended — the wording is in ledger 0047 pending Kevin's sign-off, Q9).
#
# Stages (V3-PLAN §Phase 1 "the ONE pipeline"):
#   draft  : median_envelope → trim_connectors → build_loop_blend              (GEN layer, regenerable)
#   author : seat_terrain → median → gap_mouths → lamps → signs                 (scripted authoring)
#            → barrier_bands → layout_dummies → author_race_furniture → verify_race   (0047, idempotent)
#   ship   : build_kn5_loop prep → split_exports → export road / race / spawn kn5s → AI per layout
#            → verify_kn5 → track_folder (three layouts) → make_map → make_treefx
#   gate   : kn5_to_gate_obj (road; road+race) → drive_test per layout → audit_mesh (street; --race)
#   install: copy to AC as san_diego_lake_murray_v3; the previous build is parked in $ARCHIVE/<stamp>/
#            (outside content/tracks, so Content Manager never lists two "K10 - San Diego (V3)")
#
# Every Blender call carries --python-exit-code 1: a Python exception inside a --python script
# otherwise exits 0 and the chain ships whatever the previous run left behind (found on the
# W1-6 signs dry run, 2026-10-10).
#
# --skip-blend    resume from the authored loop.blend (skips draft + the hand-authoring stages). The
#                 race-furniture author step still runs: it is idempotent (removes and re-adds the RACE
#                 collection) and is the only thing that keeps loop.blend in step with race.* in
#                 track.config.json (Q1/Q2/Q5/Q6/Q7 are config edits).
# --dry-run       stop right before the first kn5 export: everything up to the prep + split runs,
#                 nothing is exported, synced back or installed. Pair with SHIP_PROJ=<scratch copy>.
# --force-install the gates have never passed on this track (the July reference fails them too, on
#                 inherited defects). During the campaign a build may be installed red ONLY when it is
#                 no worse than the reference on every gate metric; the caller owns that comparison and
#                 the handoff note must say so. This flag is the honest version of the old
#                 GATE_*_ADVISORY env vars: loud, per-run, never silent. It does NOT cover the race
#                 layouts' own furniture gates (barrier_missing / obstruction): there is no reference
#                 to be "no worse than", so a race layout red on those is never installed.
# SHIP_PROJ=<dir> run the whole chain against a scratch copy of the workshop project (an ABSOLUTE path
#                 outside airoso). Every step takes "$PROJ" — no relative `project` argument, no
#                 workshop literal past WS_PROJ below. With a scratch PROJ the chain is safe
#                 to run for real (no --dry-run): it builds, exports and gates into the scratch copy,
#                 then SKIPS the sync-back to airoso and the install (it prints why) — only the real
#                 workshop ($WS_PROJ) feeds tracks/san-diego-lake-murray/ and the AC folder.
# STREET_AI=draft|july  the street layout's AI line (Q8). Default `draft` = the V3 right-hand-lane draft
#                 (scripts/ac/write_ai_line.py --layout street). `july` (explicit opt-in) copies the
#                 installed July line — a July write_ai_line DRAFT, never an in-game recording, and
#                 measured in the ONCOMING carriageway on every divided run (ledger 0047 Notes).
set -euo pipefail
export PYTHONUTF8=1
AIROSO="C:/Users/Owner/Documents/GitHub/airoso"
WS="C:/Users/Owner/Documents/GitHub/k10-sd-v021"
WS_PROJ="$WS/project"        # the real workshop project: the ONLY spelling of it in this script
PROJ="${SHIP_PROJ:-$WS_PROJ}"
SRC="$AIROSO/tracks/san-diego-lake-murray"
ENG="C:/Users/Owner/Documents/GitHub/engine-july"
BL="C:/Program Files/Blender Foundation/Blender 4.2/blender.exe"
AC="D:/SteamLibrary/steamapps/common/assettocorsa/content/tracks"
ARCHIVE="D:/k10-track-archive"   # old installs live here, never in content/tracks (Kevin 2026-10-11: "clear old versions")
JULY_AI="$ARCHIVE/2026-10-11/san_diego_lake_murray/ai"   # the old v0.22 install, archived 2026-10-11
SLUG="san_diego_lake_murray"
# Q8 (0047): the street layout's AI line. Default `draft` = the V3 forward right-hand-lane draft from
# the built centreline (write_ai_line --layout street: 100 % right side, 0 island hits on the dry
# run). `july` = opt-in copy of the installed fast_lane.ai — the July write_ai_line DRAFT (generated,
# NOT an in-game recording), which drives the LEFT/oncoming carriageway on every divided run (measured
# 2026-10-11, 1,642/1,642 island stations). Every line shipped is a generated draft: ledger 0023 stays
# open, no tier claimed; the race layouts always get V3 drafts.
STREET_AI="${STREET_AI:-draft}"
case "$STREET_AI" in draft|july) ;; *) echo "STREET_AI must be draft or july, got '$STREET_AI'"; exit 2;; esac
INSTALL=1; SKIP_BLEND=0; FORCE=0; DRY=0
for a in "$@"; do case "$a" in
  --no-install) INSTALL=0;; --skip-blend) SKIP_BLEND=1;; --force-install) FORCE=1;; --dry-run) DRY=1;;
  *) echo "unknown flag: $a"; exit 2;;
esac; done
if [ "$DRY" = 1 ]; then INSTALL=0; fi
# SHIP_PROJ isolation: the project must be absolute; a scratch project never syncs back or installs,
# and never lives inside airoso (the sync-inputs step would then write into the source of truth).
case "$PROJ" in
  /*|[A-Za-z]:/*|[A-Za-z]:\\*) ;;
  *) echo "SHIP_PROJ must be an absolute path, got '$PROJ'"; exit 2;;
esac
# compare paths the way Windows does: one spelling (cygpath -m: C:/...), forward slashes, any case
norm() { local p; p=$(cygpath -m "$1" 2>/dev/null || printf '%s' "$1"); p="${p//\\//}"; p="${p%/}"; printf '%s' "${p,,}"; }
case "$(norm "$PROJ")" in
  "$(norm "$AIROSO")"|"$(norm "$AIROSO")"/*) echo "SHIP_PROJ '$PROJ' is inside airoso — use a scratch copy outside the repo"; exit 2;;
esac
if [ "$(norm "$PROJ")" = "$(norm "$WS_PROJ")" ]; then SCRATCH=0; else SCRATCH=1; fi
# build_loop_blend.py (the workshop's) does `from scripts.geometry import ...` with only the PROJECT'S
# PARENT on sys.path (Blender adds neither the cwd nor the script dir) — for a scratch PROJ that is not
# $WS, so the workshop root is put on sys.path first (--python-expr runs before --python).
WS_SYSPATH="import sys; sys.path.insert(0, r'$WS')"
if [ "$SCRATCH" = 1 ] && [ "$SKIP_BLEND" = 0 ] && [ -d "$(dirname "$PROJ")/scripts" ]; then
  # the workshop's build_loop_blend.py imports scripts.geometry from the PROJECT'S PARENT first
  echo "SHIP_PROJ '$PROJ': its parent holds a scripts/ package that would shadow the workshop's — copy the project elsewhere"; exit 2
fi

step() { echo; echo "=================== $1"; }
pyq() { (cd "$AIROSO" && python -c "$@"); }

step "sync inputs airoso -> workshop ($PROJ)"
cp "$SRC/track.config.json" "$PROJ/track.config.json"
cp "$SRC/start_positions.json" "$PROJ/start_positions.json"
for f in centerline.raw.local.json.pre-median connectors.local.json.pre-trim; do
  [ -f "$SRC/data/$f" ] && cp "$SRC/data/$f" "$PROJ/data/$f"
done
mkdir -p "$PROJ/source/trees" && cp "$SRC/source/trees/"*.bin "$PROJ/source/trees/" 2>/dev/null || true   # TreeFX models (gitignored, personal use)
# the declared layouts drive every per-layout step below (never a hand-typed list)
LAYOUT_IDS=$(pyq "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print(' '.join(str(l['id']) for l in d['layouts']))" "$PROJ/track.config.json")
RACE_IDS=$(pyq "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print(' '.join(str(l['id']) for l in d['layouts'] if l.get('race_furniture')))" "$PROJ/track.config.json")
STREET_IDS=$(pyq "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print(' '.join(str(l['id']) for l in d['layouts'] if not l.get('race_furniture')))" "$PROJ/track.config.json")
echo "layouts: $LAYOUT_IDS   (race furniture: $RACE_IDS; street: $STREET_IDS; street AI = $STREET_AI)"
[ -n "$RACE_IDS" ] || { echo "no race layout declared — this chain is the three-version chain (ledger 0047)"; exit 2; }

if [ "$SKIP_BLEND" = 0 ]; then
  step "draft: median envelope (self-gated)"
  (cd "$AIROSO" && python tools/median_envelope.py "$PROJ")
  step "draft: build loop.blend (scene regen — GEN layer)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python-expr "$WS_SYSPATH" --python scripts/blender/build_loop_blend.py -- "$PROJ" 2>&1 | grep "^\[blend\]" | tail -4)
  step "draft: side streets from Kevin's routes (airoso data/routes.json)"
  (cd "$AIROSO" && python tools/route_connectors.py "$PROJ")
  step "draft: divided side streets -> one trunk + island (Del Cerro)"
  (cd "$AIROSO" && python tools/divide_connectors.py "$PROJ")
  step "draft: trim connectors at the mainline edge"
  (cd "$AIROSO" && python tools/trim_connectors.py "$PROJ")
  step "draft: rebuild loop.blend with trimmed connectors"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python-expr "$WS_SYSPATH" --python scripts/blender/build_loop_blend.py -- "$PROJ" 2>&1 | grep "^\[blend\]" | tail -3)
  step "author: seat the terrain under every road (verge finer than the road)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/seat_terrain_blend.py" -- "$PROJ" 2>&1 | grep "^\[seat\]\|Error\|Traceback" )
  step "author: thin the far terrain (headroom for the prep's grass tiles)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/slim_far_terrain_blend.py" -- "$PROJ" 2>&1 | grep "^\[slim\]\|Error\|Traceback" )
  step "author: median island"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_median_blend.py" -- "$PROJ" 2>&1 | grep "^\[median" )
  step "author: gap the mainline sidewalk at every mouth"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/gap_mouths_blend.py" -- "$PROJ" 2>&1 | grep "^\[gap" )
  step "author: export scatter positions, strip procedural vegetation (TreeFX replaces it)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/export_scatter_blend.py" -- "$PROJ" 2>&1 | grep "^\[scatter" )
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/strip_scenery_blend.py" -- "$PROJ" 2>&1 | grep "^\[strip" | cut -c1-160 )
  step "author: Kevin's lamp model at every streetlight (LIGHTPOST + LIGHTS lens)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_lamps_blend.py" -- "$PROJ" 2>&1 | grep "^\[lamps\]\|Error\|Traceback" )
  step "author: W1-6 large-arrow signs at every tight corner (SIGNPLATE + SIGNARROW + SIGNPOST)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_signs_blend.py" -- "$PROJ" 2>&1 | grep "^\[signs\]\|Error\|Traceback" )
  (cd "$AIROSO" && python tools/verify_signs.py "$PROJ" --blend "$PROJ/loop.blend" --blender "$BL" | tail -8)
  (cd "$AIROSO" && PYTHONUTF8=1 python tools/plot_signs.py "$PROJ")
fi

# --- 0047: the race furniture. Runs on every ship (idempotent; see --skip-blend above). ----------
step "author: race-furniture declaration (tools/barrier_bands.py, self-gated) + per-layout dummies"
(cd "$AIROSO" && python tools/barrier_bands.py "$PROJ")          # data/barrier_bands.json: exit 1 on a bad band
(cd "$AIROSO" && python tools/layout_dummies.py "$PROJ")         # data/dummies_<id>.json x3 (engine frame + _yaw_deg); exit 1 on validation
step "author: race furniture -> RACE collection in loop.blend (1WALL_race_* chain + kerb-line strips, 1KERB_race_* kerbs)"
(cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_race_furniture_blend.py" -- "$PROJ" 2>&1 | grep "^\[race\]\|Error\|Traceback" )
step "author: verify the authored furniture against its declaration (tools/verify_race.py, hard)"
(cd "$AIROSO" && python tools/verify_race.py "$PROJ")            # data/race_verify.json; exit 1
(cd "$AIROSO" && python tools/plot_race_furniture.py "$PROJ" | tail -3)   # data/race_plots/*.png

step "ship: prep (AC naming, 65k splits; multi-layout: NO AC_* dummies in the road scene)"
"$BL" --background --python-exit-code 1 --python "$ENG/scripts/ac/build_kn5_loop.py" -- "$PROJ" 2>&1 | grep "prepped\|FATAL\|split 1GRASS\|multi-layout" | cut -c1-160
step "ship: split the prepped scene -> road / race / spawn scenes (tools/split_exports_blend.py)"
"$BL" --background --python-exit-code 1 --python "$AIROSO/tools/split_exports_blend.py" -- "$PROJ/blender/$SLUG.blend" --project "$PROJ" --out-dir "$PROJ/blender/split" 2>&1 | grep "^\[split\]"
# the split asserts: loop_main.blend holds 0 AC_* and 0 RACE objects/materials, loop_race.blend only
# RACE-named objects + RACE-named materials, each spawn blend only that layout's AC_* empties.

if [ "$DRY" = 1 ]; then
  echo; echo "DRY RUN: stopping before the kn5 exports. Would now: export $SLUG.kn5 (road) + ${SLUG}_race.kn5 +"
  echo "  ${SLUG}__{$(echo $LAYOUT_IDS | tr ' ' ',')}.kn5 (spawns) -> AI per layout -> verify_kn5 -> track_folder -> make_map -> make_treefx"
  echo "  -> gates (street on track.obj; race layouts on track.race.obj) -> sync outputs -> install."
  echo "  Nothing exported, nothing synced back, nothing installed ($PROJ)."
  exit 0
fi

step "ship: export road kn5 (shared by all layouts, spawn-free)"
"$BL" --background --python-exit-code 1 --python "$ENG/scripts/ac/export_kn5_addon.py" -- "$PROJ" --blend "$PROJ/blender/split/loop_main.blend" 2>&1 | grep "KN5 EXISTS\|INI materials"
step "ship: export race-furniture kn5 (loaded by the race layouts only)"
"$BL" --background --python-exit-code 1 --python "$ENG/scripts/ac/export_kn5_addon.py" -- "$PROJ" --blend "$PROJ/blender/split/loop_race.blend" --out "${SLUG}_race.kn5" 2>&1 | grep "KN5 EXISTS\|INI materials"
# content guard (was a 20 MB size cap, which fired on a clean but flat-shaded 35.6 MB kn5): every mesh
# 1WALL_RACE* / 1KERB_RACE*, every texture from pbr.py's race rows, no AC_* node — exit 1 otherwise.
# The size is printed (WARN above 20 MB), never the gate.
(cd "$AIROSO" && python -m scripts.modkit.inspect_kn5 "$PROJ/build/${SLUG}_race.kn5" --json "$PROJ/data/race_kn5.json" >/dev/null)
(cd "$AIROSO" && python tools/check_race_kn5.py "$PROJ/data/race_kn5.json")
step "ship: spawn kn5 per layout (nodes only: AC_START/PIT/HOTLAP/TIME from data/dummies_<id>.json)"
"$BL" --background --python-exit-code 1 --python "$ENG/scripts/ac/build_spawn_kn5.py" -- "$PROJ" 2>&1 | grep "^\[spawn_kn5\]"

step "ship: AI lines per layout (race: V3 lane-offset drafts — GENERATED, ledger 0023; street: $STREET_AI)"
for lid in $RACE_IDS; do
  (cd "$AIROSO" && python -m scripts.ac.write_ai_line "$PROJ" --layout "$lid" | grep -v "^  v\|^frame")
done
for lid in $STREET_IDS; do
  rm -rf "$PROJ/ai/$lid"; mkdir -p "$PROJ/ai/$lid"     # never leave a stale ai_draft.json beside a copied line
  if [ "$STREET_AI" = july ]; then
    cp "$JULY_AI/fast_lane.ai" "$JULY_AI/pit_lane.ai" "$JULY_AI/side_l.csv" "$JULY_AI/side_r.csv" "$PROJ/ai/$lid/"
    echo "ai/$lid/: STREET_AI=july — the July write_ai_line DRAFT copied from $JULY_AI/ (generated, not an"
    echo "  in-game recording; it drives the oncoming carriageway on every divided run — ledger 0047 Notes)"
  else
    (cd "$AIROSO" && python -m scripts.ac.write_ai_line "$PROJ" --layout "$lid" | grep -v "^  v\|^frame")
  fi
done

step "ship: verify_kn5 (hard — spawn-free road + race kn5, one spawn kn5 per layout, facing, side, line, sectors)"
(cd "$AIROSO" && python -m scripts.ac.verify_kn5 "$PROJ")
step "ship: track folder (models_<id>.ini x3, ui/<id>/, <id>/{map,data,ai}; stale single-layout structure removed)"
(cd "$AIROSO" && python -m scripts.ac.track_folder "$PROJ") | grep -E "wrote|length_m|n_pits|layouts packed|removed stale|models|WARNING|ai/"
cp "$PROJ/build/$SLUG.kn5" "$PROJ/build/$SLUG/"          # the race + spawn kn5s are copied by track_folder itself
step "ship: minimap in the KN5 frame, per layout (tools/make_map.py)"
(cd "$AIROSO" && python tools/make_map.py "$PROJ")
step "ship: TreeFX palms / street trees / scrub (tools/make_treefx.py)"
(cd "$AIROSO" && python tools/make_treefx.py "$PROJ")

step "gate: road kn5 -> gate OBJ (engine frame) + gate centreline"
(cd "$AIROSO" && python -m scripts.modkit.kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5")
step "gate: drive_test, street layout (hard)"
DT_S=0; (cd "$AIROSO" && python -m scripts.geometry.drive_test "$PROJ" --layout street 2>&1 | grep -v "drive-time\] sweep" | tail -30) || DT_S=$?
step "gate: audit_mesh, street (hard total; the regression floor — must equal today's D 512 / K 154 / I 145 / F 15)"
AU_S=0; (cd "$AIROSO" && python -m scripts.geometry.audit_mesh "$PROJ" 2>&1 | tail -16) || AU_S=$?
step "gate: road + race kn5 -> ONE gate OBJ (the kn5 set the race layouts load) — data/track.race.obj"
(cd "$AIROSO" && python -m scripts.modkit.kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5" --kn5 "$PROJ/build/${SLUG}_race.kn5" --out "$PROJ/data/track.race.obj")
step "gate: drive_test, race layouts (hard; lane-relative sweep, barrier_missing must be 0)"
RACE_FLAGS=""; for lid in $RACE_IDS; do RACE_FLAGS="$RACE_FLAGS --layout $lid"; done
DT_R=0; (cd "$AIROSO" && python -m scripts.geometry.drive_test "$PROJ" $RACE_FLAGS 2>&1 | grep -v "drive-time\] sweep" | tail -60) || DT_R=$?
step "gate: audit_mesh --race (D exempt on the declared bands only; E/F unchanged)"
AU_R=0; (cd "$AIROSO" && python -m scripts.geometry.audit_mesh "$PROJ" --race --obj track.race.obj --out audit.race.json 2>&1 | tail -18) || AU_R=$?
# a race layout red on its OWN furniture gates is never installed, --force-install or not
RACE_RED=$(pyq "import json,sys
d=json.load(open(sys.argv[1],encoding='utf-8')); bad=[]
for lid,r in (d.get('layouts') or {}).items():
    if r.get('kind')=='race' and ((r.get('barrier_missing') or 0)>0 or (r.get('obstruction_stations') or 0)>0 or r.get('fail') is None): bad.append(lid)
print(' '.join(bad))" "$PROJ/data/drive_test.json")

if [ "$SCRATCH" = 1 ]; then
  step "sync outputs workshop -> airoso: SKIPPED"
  echo "SHIP_PROJ is a scratch project ($PROJ), not the workshop ($WS_PROJ): its outputs stay in the scratch copy —"
  echo "only the workshop feeds $SRC (loop.blend, data/, ai/)."
else
step "sync outputs workshop -> airoso"
cp "$PROJ/loop.blend" "$SRC/loop.blend"
for f in centerline.local.json centerline.raw.local.json median_bands.json dummies.json \
         finished_centerline.json gate_centerline.json lights.local.json connectors.local.json \
         mouths.json signs.local.json signs_preview.svg signs_measured.json drive_test.json audit.json \
         barrier_bands.json race_authored.json race_verify.json audit.race.json; do
  [ -f "$PROJ/data/$f" ] && cp "$PROJ/data/$f" "$SRC/data/$f"
done
for lid in $LAYOUT_IDS; do
  for f in "dummies_$lid.json" "drive_test.$lid.json"; do [ -f "$PROJ/data/$f" ] && cp "$PROJ/data/$f" "$SRC/data/$f"; done
  if [ -d "$PROJ/ai/$lid" ]; then rm -rf "$SRC/ai/$lid"; mkdir -p "$SRC/ai"; cp -r "$PROJ/ai/$lid" "$SRC/ai/$lid"; fi   # track_folder is reproducible from the repo
done
[ -f "$PROJ/blender/split/split_manifest.json" ] && cp "$PROJ/blender/split/split_manifest.json" "$SRC/data/split_manifest.json"
for d in signs_plots race_plots; do
  if [ -d "$PROJ/data/$d" ]; then rm -rf "$SRC/data/$d"; cp -r "$PROJ/data/$d" "$SRC/data/$d"; fi
done
# track.race.obj / track.obj are 66+ MB each and regenerable from the kn5s: never synced.
fi

if [ "$DT_S" != 0 ] || [ "$AU_S" != 0 ] || [ "$DT_R" != 0 ] || [ "$AU_R" != 0 ]; then
  echo; echo "GATES: street drive_test exit $DT_S, street audit exit $AU_S, race drive_test exit $DT_R, race audit exit $AU_R"
  if [ -n "$RACE_RED" ]; then
    echo "  NOT INSTALLED: race layout(s) [$RACE_RED] fail on their own furniture gates (barrier_missing / obstruction) —"
    echo "  no reference exists to be 'no worse than', so --force-install does not apply (data/drive_test.<id>.json)"; exit 1
  elif [ "$FORCE" = 1 ]; then
    echo "  --force-install: installing RED (caller asserts no metric is worse than the July reference)"
  else
    echo "  NOT INSTALLED (Kevin never loads a build the machine failed)"; exit 1
  fi
fi
if [ "$INSTALL" = 1 ] && [ "$SCRATCH" = 1 ]; then
  step "install: SKIPPED"
  echo "SHIP_PROJ is a scratch project ($PROJ): never installed — only $WS_PROJ reaches $AC. The built folder is"
  echo "$PROJ/build/$SLUG (load it by hand if you mean to)."
elif [ "$INSTALL" = 1 ]; then
  step "install: $AC/${SLUG}_v3 (three layouts; previous build parked in $ARCHIVE/<stamp>/)"
  B="$PROJ/build/$SLUG"
  for lid in $LAYOUT_IDS; do [ -f "$B/models_$lid.ini" ] || { echo "missing $B/models_$lid.ini"; exit 1; }; done
  STAMP=$(date +%Y-%m-%d_%H%M%S)
  for old in "${SLUG}_v3" "${SLUG}_v3_prev"; do
    if [ -d "$AC/$old" ]; then mkdir -p "$ARCHIVE/$STAMP"; mv "$AC/$old" "$ARCHIVE/$STAMP/$old"; echo "parked $old in $ARCHIVE/$STAMP/"; fi
  done
  cp -r "$B" "$AC/${SLUG}_v3"
  python - <<PY
import json, glob, os
cfg = json.load(open(r"$PROJ/track.config.json", encoding="utf-8"))
names = {str(lo["id"]): lo.get("name", lo["id"]) for lo in cfg["layouts"]}
seen = []
for p in sorted(glob.glob(r"$AC/${SLUG}_v3/ui/*/ui_track.json")):
    lid = os.path.basename(os.path.dirname(p))
    d = json.load(open(p, encoding="utf-8"))
    d["name"] = "K10 - San Diego (V3) \u2014 " + names[lid]
    json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    seen.append(lid)
    print("installed:", d["name"], d.get("version"))
missing = sorted(set(names) - set(seen))
if missing:
    raise SystemExit(f"installed folder lacks ui/<id>/ui_track.json for {missing}")
PY
fi
echo; echo "SHIP OK"
