#!/usr/bin/env bash
# The San Diego ship chain — draft → author → ship → gate → install, one command, exits nonzero on any gate.
#
#   bash tools/ship_sd.sh [--no-install] [--skip-blend] [--force-install] [--dry-run]
#
# Builds the v021 workshop PROJECT (C:/Users/Owner/Documents/GitHub/k10-sd-v021/project). The loop
# assembler runs from airoso's tooling of record, tracks/san-diego-lake-murray/scripts-v021 (diff-identical
# to the retired workshop's scripts/ when it was switched, 2026-10-11, ledger 0046 — never edit the workshop),
# through V021_SHIM: inside Blender `scripts` is registered as THAT package, so its `from scripts.geometry
# import ...` cannot resolve to airoso's engine or to anything beside the project. The prep/export run from
# ENG (engine-july) at the pin that built the drive-feel reference; the V3 tools (median, trim, gap, signs,
# race furniture, dummies, the packer and every gate) run from airoso. Source of truth stays
# tracks/san-diego-lake-murray/ in airoso: edit there, this script syncs the inputs down and the outputs back up.
#
# TIERED TERRAIN (ledger 0046, Kevin 2026-10-10: "more terrain near the roads, and the I-8 trench and adjacent
# causeway cut out"; "I want to see cowles mountain"): before each assembler run scripts.elevation.terrain_sample
# plans the multi-resolution lattice on the current roads and fetches 3DEP at every vertex it lacks (cached in
# data/terrain.samples.json.gz); the assembler meshes TERRAIN (physical, -> 1GRASS tiles by balanced bisection in
# the prep) and GRASS_FAR (the visual-only far ring). The far-terrain decimation pass is gone.
#
# THREE VERSIONS (ledger 0047, Kevin 2026-10-10): `street` (the open two-way loop as today),
# `race_cw` and `race_acw` (the loop as a one-way race track in each direction).
# RACE CORRIDORS (ledger 0049, Kevin 2026-10-11: "the entire other lane blocked off from access", "more or
# less an Alvarado's width for the entire track", full intersections open at the corners the race turns at,
# side streets sealed). The kn5 set:
#   <slug>.kn5                    the ROAD, no AC_* node — all three layouts
#   <slug>_race.kn5               COMMON race furniture: both curb strips (one closed loop per side, across
#                                 all three bridges) + the declared kerbs (8) — race_cw and race_acw
#   <slug>_closure_<id>.kn5       ONE per race layout: the wall closing off the other direction's lanes.
#                                 Each race layout loads ONLY its own (the clockwise closure stands in the
#                                 anticlockwise lane); a race layout without its closure kn5 never packs
#   <slug>__<id>.kn5              nodes-only SPAWN kn5, one per layout
# (fleet/LAWS.md L8 as amended — the wording is in ledger 0047 pending Kevin's sign-off, Q9.)
#
# Stages (V3-PLAN §Phase 1 "the ONE pipeline"):
#   draft  : median_envelope → terrain_sample → build_loop_blend → trim_connectors → terrain_sample →
#            build_loop_blend → weld_mouths (GEN layer, regenerable; the weld mitres + warps every side-street
#            end onto its host, self-checked — 2026-10-11; terrain_sample = the ledger-0046 tiered 3DEP plan)
#   author : seat_terrain → median → gap_mouths → lamps → signs                 (scripted authoring)
#            → barrier_bands v2 (corridor solve + self-gates + PLANNED no_route per race layout, hard)
#            → layout_dummies → author_race_furniture (RACE + RACE_CLOSE_<TOKEN>) → verify_race (idempotent)
#   ship   : build_kn5_loop prep → split_exports (road / common race / closure per race layout / spawns)
#            → export road / race / closure x race layouts (each content-checked) / spawn kn5s
#            → AI per layout → verify_kn5 → kn5_to_gate_obj (road; the track folder reads its mesh names)
#            → track_folder (three layouts) → verify_kn5 --inis
#            → make_map → make_treefx → verify_race --scenery-only on the written trees.txt (hard)
#   gate   : street: verify_mouths (every side-street mouth on the BUILT road, hard)
#            → drive_test --layout street → audit_mesh
#            per race layout: kn5_to_gate_obj (road + race + ITS closure → data/track.<id>.obj)
#            → drive_test --layout <id> → audit_mesh --layout <id> → no_route --layout <id> (BUILT)
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
#                 layouts' own gates (drive_test barrier_missing / obstruction, the BUILT no_route
#                 containment fill): there is no reference to be "no worse than", so a race layout red
#                 on those is never installed.
# SHIP_PROJ=<dir> run the whole chain against a scratch copy of the workshop project (an ABSOLUTE path
#                 outside airoso). Every step takes "$PROJ" — no relative `project` argument, no
#                 workshop literal past WS_PROJ below. With a scratch PROJ the chain is safe
#                 to run for real (no --dry-run): it builds, exports and gates into the scratch copy,
#                 then SKIPS the sync-back to airoso and the install (it prints why) — only the real
#                 workshop ($WS_PROJ) feeds tracks/san-diego-lake-murray/ and the AC folder.
# AIROSO=<dir>    the airoso checkout whose tools/ and scripts/ the chain runs (default: the main checkout). Point
#                 it at a worktree to rehearse that worktree's tools; pair with SHIP_PROJ (the guards below still
#                 refuse a project inside it).
# ENG=<dir>       the engine-july tree the prep / exporter / spawn builder run from (default: the real one). Point
#                 it at a scratch COPY to rehearse an engine-july change before it is mirrored (the change itself is
#                 recorded in tracks/san-diego-lake-murray/engine-july-snapshot/, see its PENDING-MIRROR.md5).
# STREET_AI=draft|july  the street layout's AI line (Q8). Default `draft` = the V3 right-hand-lane draft
#                 (scripts/ac/write_ai_line.py --layout street). `july` (explicit opt-in) copies the
#                 installed July line — a July write_ai_line DRAFT, never an in-game recording, and
#                 measured in the ONCOMING carriageway on every divided run (ledger 0047 Notes).
set -euo pipefail
export PYTHONUTF8=1
AIROSO="${AIROSO:-C:/Users/Owner/Documents/GitHub/airoso}"
WS="C:/Users/Owner/Documents/GitHub/k10-sd-v021"
WS_PROJ="$WS/project"        # the real workshop project: the ONLY spelling of it in this script
PROJ="${SHIP_PROJ:-$WS_PROJ}"
SRC="$AIROSO/tracks/san-diego-lake-murray"
V021="$SRC/scripts-v021"     # the loop assembler of record (build_loop_blend + its ribbon/smooth/palm/scenery modules)
ENG="${ENG:-C:/Users/Owner/Documents/GitHub/engine-july}"
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
# build_loop_blend.py does `from scripts.geometry import ...` after putting the PROJECT'S PARENT on sys.path.
# V021_SHIM (--python-expr runs before --python) registers `scripts` as the scripts-v021 package FIRST, so every
# `scripts.*` import inside the assembler (and in weld_mouths_blend, which rebuilds connector blocks with the
# same ribbon module) resolves there — never to airoso's engine `scripts`, never to a scripts/ beside the project.
V021_SHIM="import sys, importlib.util as u; s=u.spec_from_file_location('scripts', r'$V021/__init__.py', submodule_search_locations=[r'$V021']); m=u.module_from_spec(s); sys.modules['scripts']=m; s.loader.exec_module(m)"
[ -f "$V021/blender/build_loop_blend.py" ] || { echo "no assembler at $V021/blender/build_loop_blend.py"; exit 2; }

TERRAIN_DATA="terrain.samples.json.gz corridor.i8.json i8.local.json i8.legacy.local.json"
# the track's own textures (track.config.json texture_overrides with a project-relative path: the far ring's chaparral)
TRACK_TEXTURES="textures/chaparral_far_diffuse.jpg"
step() { echo; echo "=================== $1"; }
pyq() { (cd "$AIROSO" && python -c "$@"); }

step "sync inputs airoso -> workshop ($PROJ)"
cp "$SRC/track.config.json" "$PROJ/track.config.json"
cp "$SRC/start_positions.json" "$PROJ/start_positions.json"
for f in centerline.raw.local.json.pre-median connectors.local.json.pre-trim; do
  [ -f "$SRC/data/$f" ] && cp "$SRC/data/$f" "$PROJ/data/$f"
done
# ledger 0046: the 3DEP cache + the I-8 corridor (data with provenance, L2) — a fresh workshop never re-fetches them
for f in $TERRAIN_DATA; do
  [ -f "$SRC/data/$f" ] && cp "$SRC/data/$f" "$PROJ/data/$f"
done
for f in $TRACK_TEXTURES; do
  [ -f "$SRC/$f" ] && { mkdir -p "$(dirname "$PROJ/$f")"; cp "$SRC/$f" "$PROJ/$f"; }
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
  step "draft: tiered terrain plan + 3DEP samples (cached; ledger 0046)"
  (cd "$AIROSO" && python -m scripts.elevation.terrain_sample "$PROJ")
  step "draft: build loop.blend (scene regen — GEN layer)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python-expr "$V021_SHIM" --python "$V021/blender/build_loop_blend.py" -- "$PROJ" 2>&1 | grep "^\[blend\]\|Error\|Traceback" | tail -6)
  step "draft: side streets from Kevin's routes (airoso data/routes.json)"
  (cd "$AIROSO" && python tools/route_connectors.py "$PROJ")
  step "draft: divided side streets -> one trunk + island (Del Cerro)"
  (cd "$AIROSO" && python tools/divide_connectors.py "$PROJ")
  step "draft: trim connectors at the mainline edge"
  (cd "$AIROSO" && python tools/trim_connectors.py "$PROJ")
  step "draft: tiered terrain re-planned on the trimmed connectors (only new vertices fetched)"
  (cd "$AIROSO" && python -m scripts.elevation.terrain_sample "$PROJ")
  step "draft: rebuild loop.blend with trimmed connectors"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python-expr "$V021_SHIM" --python "$V021/blender/build_loop_blend.py" -- "$PROJ" 2>&1 | grep "^\[blend\]\|Error\|Traceback" | tail -6)
  step "draft: weld every side-street mouth onto its host (mitre + warp: road, curb/sidewalk, markings; self-checked)"
  # tools/weld_mouths_blend.py rebuilds each connector block with the assembler's own ribbon module (V021_SHIM) and
  # refuses to move a vertex unless the mesh matches it; exit 1 on its self-check (end row off the host deck, a
  # connector vertex over the host's pavement, a folded quad) — loop.blend is then NOT saved
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python-expr "$V021_SHIM" --python "$AIROSO/tools/weld_mouths_blend.py" -- "$PROJ" 2>&1 | grep "^\[weld\]\|Error\|Traceback" )
  step "author: seat the terrain under every road (verge finer than the road)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/seat_terrain_blend.py" -- "$PROJ" 2>&1 | grep "^\[seat\]\|Error\|Traceback" )
  # (the far-terrain decimation that paid for the prep's equal-width grass bands is gone — ledger 0046: the
  #  terrain is tiered at the source and the prep tiles 1GRASS by balanced bisection. It also triangulated every
  #  terrain face here, and the near-road ground the gates were tuned on is that triangulation's: kept, alone.)
  step "author: triangulate the terrain (BEAUTY, what the retired decimation did to every face; no vertex moves)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/triangulate_terrain_blend.py" -- "$PROJ" 2>&1 | grep "^\[tri\]\|Error\|Traceback" )
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

# --- 0047/0049: the race furniture. Runs on every ship (idempotent; see --skip-blend above). -----
# The planned and built containment verdicts of an earlier run are never read as this run's: removed first.
for lid in $RACE_IDS; do rm -f "$PROJ/data/no_route.$lid.planned.json" "$PROJ/data/no_route.$lid.json"; done
step "author: race-corridor declaration v2 (tools/barrier_bands.py: corridor solve + self-gates + PLANNED no_route per race layout, hard)"
# data/barrier_bands.json v2 + data/no_route.<id>.planned.json per race layout; exit 1 on any self-gate,
# a planned leak included. --no-planned-route is a look-only flag and never appears in the ship.
(cd "$AIROSO" && python tools/barrier_bands.py "$PROJ")
step "gate: PLANNED no_route per race layout (the declared walls contain the lane — read back, hard)"
# barrier_bands already exited 1 on a planned leak; this reads the verdict files it wrote, so a declaration
# that skipped or lost its planned fill cannot reach Blender.
pyq "import json,os,sys
data=sys.argv[1]; bad=[]
for lid in sys.argv[2:]:
    p=os.path.join(data,'no_route.%s.planned.json'%lid)
    if not os.path.exists(p):
        bad.append(lid+': no planned verdict (data/no_route.%s.planned.json missing)'%lid); continue
    r=json.load(open(p,encoding='utf-8'))
    if not isinstance(r,dict):
        bad.append(lid+': the planned verdict is not a no_route report'); continue
    print('  %-9s planned: %s  leak_cells %s  blocked %s  forbidden_reached %s  spawns_unreached %s  reached %s m2'%(lid,
          'FAIL' if r.get('fail') else 'PASS', r.get('leak_cells'), len(r.get('blocked') or []),
          len(r.get('forbidden_reached') or []), len(r.get('spawns_unreached') or []), r.get('reached_m2')))
    if r.get('fail') is not False or (r.get('leak_cells') or 0)>0 or r.get('blocked') or r.get('forbidden_reached') or r.get('spawns_unreached'):
        bad.append(lid+': planned no_route FAIL')
if bad: raise SystemExit('PLANNED no_route: '+'; '.join(bad))" "$PROJ/data" $RACE_IDS
(cd "$AIROSO" && python tools/layout_dummies.py "$PROJ")         # data/dummies_<id>.json x3 (engine frame + _yaw_deg); exit 1 on validation
step "author: race furniture -> loop.blend: RACE (curb strips + kerbs, common) + RACE_CLOSE_<TOKEN> (one closure per race layout)"
(cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_race_furniture_blend.py" -- "$PROJ" 2>&1 | grep "^\[race\]\|Error\|Traceback" )
step "author: verify the authored furniture against its declaration (tools/verify_race.py, hard: common set + each layout)"
(cd "$AIROSO" && python tools/verify_race.py "$PROJ")            # data/race_verify.json; exit 1
(cd "$AIROSO" && python tools/plot_race_furniture.py "$PROJ" | tail -3)   # data/race_plots/*.png

step "ship: prep (AC naming, 65k splits; multi-layout: NO AC_* dummies in the road scene)"
"$BL" --background --python-exit-code 1 --python "$ENG/scripts/ac/build_kn5_loop.py" -- "$PROJ" 2>&1 | grep "prepped\|FATAL\|split 1GRASS\|split GRASS_FAR\|terrain tiles\|terrain conform\|T-junctions\|kept-cell refinement\|multi-layout\|Error\|Traceback" | cut -c1-200
step "ship: split the prepped scene -> road / common race / closure per race layout / spawn scenes (tools/split_exports_blend.py)"
"$BL" --background --python-exit-code 1 --python "$AIROSO/tools/split_exports_blend.py" -- "$PROJ/blender/$SLUG.blend" --project "$PROJ" --out-dir "$PROJ/blender/split" 2>&1 | grep "^\[split\]"
# the split asserts: loop_main.blend holds 0 AC_* and 0 RACE objects/materials; loop_race.blend only the
# COMMON RACE objects (curb strips + kerbs, never a 1WALL_RACE_CLOSE_*) + RACE-named materials;
# loop_closure_<id>.blend per race layout only 1WALL_RACE_CLOSE_<its token>_* (non-empty; an undeclared
# token, a retired KBAR object, race + closures != every RACE object -> exit 1); each spawn blend only that
# layout's AC_* empties.
for lid in $RACE_IDS; do
  [ -f "$PROJ/blender/split/loop_closure_$lid.blend" ] || { echo "split wrote no loop_closure_$lid.blend — race layout $lid would load no closure"; exit 1; }
done

if [ "$DRY" = 1 ]; then
  echo; echo "DRY RUN: stopping before the kn5 exports. Would now: export $SLUG.kn5 (road) + ${SLUG}_race.kn5 (common) +"
  echo "  $(for lid in $RACE_IDS; do printf '%s ' "${SLUG}_closure_$lid.kn5"; done)(one closure per race layout, each content-checked) +"
  echo "  ${SLUG}__{$(echo $LAYOUT_IDS | tr ' ' ',')}.kn5 (spawns) -> AI per layout -> verify_kn5 -> track_folder -> verify_kn5 --inis"
  echo "  -> make_map -> make_treefx -> gates (street on track.obj; each race layout on its own track.<id>.obj:"
  echo "  drive_test, audit_mesh --layout, no_route BUILT) -> sync outputs -> install."
  echo "  Nothing exported, nothing synced back, nothing installed ($PROJ)."
  exit 0
fi

step "ship: export road kn5 (shared by all layouts, spawn-free)"
"$BL" --background --python-exit-code 1 --python "$ENG/scripts/ac/export_kn5_addon.py" -- "$PROJ" --blend "$PROJ/blender/split/loop_main.blend" 2>&1 | grep "KN5 EXISTS\|INI materials"
step "ship: export the COMMON race-furniture kn5 (curb strips + kerbs; loaded by every race layout)"
"$BL" --background --python-exit-code 1 --python "$ENG/scripts/ac/export_kn5_addon.py" -- "$PROJ" --blend "$PROJ/blender/split/loop_race.blend" --out "${SLUG}_race.kn5" 2>&1 | grep "KN5 EXISTS\|INI materials"
# content guard (was a 20 MB size cap, which fired on a clean but flat-shaded 35.6 MB kn5): every mesh
# 1WALL_RACE* / 1KERB_RACE*, none a closure, >= 1 curb strip, exactly the declared kerb count, every texture
# from pbr.py's race rows, no AC_* node — exit 1 otherwise. The size is printed (WARN above 20 MB), never the gate.
(cd "$AIROSO" && python -m scripts.modkit.inspect_kn5 "$PROJ/build/${SLUG}_race.kn5" --json "$PROJ/data/race_kn5.json" >/dev/null)
(cd "$AIROSO" && python tools/check_race_kn5.py "$PROJ/data/race_kn5.json" --role common --bands "$PROJ/data/barrier_bands.json")
for lid in $RACE_IDS; do
  # the owner token is the declaration's (barrier_bands.json corridors.<id>.token, from layouts[].closure_token)
  tok=$(pyq "import json,sys; print(json.load(open(sys.argv[1],encoding='utf-8'))['corridors'][sys.argv[2]]['token'])" "$PROJ/data/barrier_bands.json" "$lid")
  step "ship: export the $lid CLOSURE kn5 (1WALL_RACE_CLOSE_${tok^^}_* only; loaded by $lid alone)"
  "$BL" --background --python-exit-code 1 --python "$ENG/scripts/ac/export_kn5_addon.py" -- "$PROJ" --blend "$PROJ/blender/split/loop_closure_$lid.blend" --out "${SLUG}_closure_$lid.kn5" 2>&1 | grep "KN5 EXISTS\|INI materials"
  (cd "$AIROSO" && python -m scripts.modkit.inspect_kn5 "$PROJ/build/${SLUG}_closure_$lid.kn5" --json "$PROJ/data/closure_$lid.kn5.json" >/dev/null)
  (cd "$AIROSO" && python tools/check_race_kn5.py "$PROJ/data/closure_$lid.kn5.json" --role closure --owner "$tok")
done
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

step "ship: verify_kn5 (hard — spawn-free road, common race kn5 + one closure kn5 per race layout (its token only), one spawn kn5 per layout, facing, side, lane, sectors)"
(cd "$AIROSO" && python -m scripts.ac.verify_kn5 "$PROJ")
# A verdict from an earlier run is not this run's verdict: every per-layout gate file is removed before its
# gate runs, so a gate that does not run reads as "not run" (red), never as last time's pass. 0047's ONE
# shared race gate OBJ / audit (road + the retired centre chain) are retired: each race layout is judged on
# its own kn5 set (ledger 0049).
for lid in $LAYOUT_IDS; do rm -f "$PROJ/data/drive_test.$lid.json"; done
rm -f "$PROJ/data/verify_mouths.json"
for lid in $RACE_IDS; do rm -f "$PROJ/data/audit.$lid.json" "$PROJ/data/no_route.$lid.json" "$PROJ/data/track.$lid.obj"; done
rm -f "$PROJ/data/track.race.obj" "$PROJ/data/audit.race.json"
# the road gate OBJ is written BEFORE the track folder (ledger 0046): ext_config's GrassFX lists and make_treefx's
# SURFACE_MATERIALS read the mesh names off it, and the 1GRASS tile count now follows the terrain
step "gate: road kn5 -> gate OBJ (engine frame) + gate centreline"
(cd "$AIROSO" && python -m scripts.modkit.kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5")
step "ship: track folder (models_<id>.ini x3, ui/<id>/, <id>/{map,data,ai}; a race layout without its closure kn5 is a HARD error)"
(cd "$AIROSO" && python -m scripts.ac.track_folder "$PROJ") | grep -E "wrote|length_m|n_pits|layouts packed|removed stale|models|WARNING|ai/"
cp "$PROJ/build/$SLUG.kn5" "$PROJ/build/$SLUG/"          # the race, closure + spawn kn5s are copied by track_folder itself
step "ship: verify_kn5 --inis (hard — each race ini lists exactly road + common race + ITS closure + its spawns; none lists another layout's closure)"
(cd "$AIROSO" && python -m scripts.ac.verify_kn5 "$PROJ" --inis)   # after the road-kn5 copy: every listed kn5 must be in the folder
step "ship: minimap in the KN5 frame, per layout (tools/make_map.py)"
(cd "$AIROSO" && python tools/make_map.py "$PROJ")
step "ship: TreeFX palms / street trees / scrub (tools/make_treefx.py)"
(cd "$AIROSO" && python tools/make_treefx.py "$PROJ")
step "gate: scenery vs the race lanes and walls, on the WRITTEN trees.txt (tools/verify_race.py --scenery-only, hard)"
# TreeFX trunks and sign posts are not physical in AC: one standing in a race lane or inside a wall is a car
# driving through a palm. verify_race G already judged make_treefx's PLAN before Blender; this judges the file
# that ships (data/race_verify.scenery.json; exit 1 on any trunk / post in a lane or a wall — ledger 0049 fix round).
(cd "$AIROSO" && python tools/verify_race.py "$PROJ" --scenery-only --trees "$PROJ/build/$SLUG/extension/trees/trees.txt")

step "gate: verify_mouths on the built road (every side-street mouth: mouth line, host lane, notch, approach — hard)"
# tools/verify_mouths.py reads data/track.obj (the shipped road kn5) at every data/mouths.json record; exit 1 stops
# the chain (data/verify_mouths.json) — a mouth floating over its host or notched below it never reaches a gate run
(cd "$AIROSO" && python tools/verify_mouths.py "$PROJ")
step "gate: drive_test, street layout (hard)"
DT_S=0; (cd "$AIROSO" && python -m scripts.geometry.drive_test "$PROJ" --layout street 2>&1 | grep -v "drive-time\] sweep" | tail -30) || DT_S=$?
step "gate: audit_mesh, street (hard total; the regression floor — D 512 / K 20 / I 20 / F 13 since the 2026-10-11 mouth weld + fold mend, was 512 / 154 / 145 / 15)"
AU_S=0; (cd "$AIROSO" && python -m scripts.geometry.audit_mesh "$PROJ" 2>&1 | tail -16) || AU_S=$?
DT_R=0; AU_R=0; NR_R=0
for lid in $RACE_IDS; do
  step "gate: $lid — road + common race + ITS closure kn5 -> ONE gate OBJ (the kn5 set $lid loads) — data/track.$lid.obj"
  (cd "$AIROSO" && python -m scripts.modkit.kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5" --kn5 "$PROJ/build/${SLUG}_race.kn5" --kn5 "$PROJ/build/${SLUG}_closure_$lid.kn5" --out "$PROJ/data/track.$lid.obj")
  step "gate: drive_test --layout $lid (hard; the declared corridor lane — barrier_missing and obstruction_stations must be 0)"
  rc=0; (cd "$AIROSO" && python -m scripts.geometry.drive_test "$PROJ" --layout "$lid" 2>&1 | grep -v "drive-time\] sweep" | tail -40) || rc=$?
  [ "$rc" = 0 ] || DT_R=$rc
  step "gate: audit_mesh --layout $lid (D exempt on THIS layout's bands only; W: no race strip through another wall)"
  rc=0; (cd "$AIROSO" && python -m scripts.geometry.audit_mesh "$PROJ" --layout "$lid" 2>&1 | tail -18) || rc=$?
  [ "$rc" = 0 ] || AU_R=$rc
  step "gate: no_route --layout $lid, BUILT (hard; flood fill from AC_START_0 on data/track.$lid.obj — 0 leaks, lap complete, every spawn reached)"
  rc=0; (cd "$AIROSO" && python tools/no_route.py "$PROJ" --layout "$lid" 2>&1 | tail -30) || rc=$?
  [ "$rc" = 0 ] || NR_R=$rc
done
# a race layout red on its OWN gates is never installed, --force-install or not: drive_test barrier_missing /
# obstruction_stations / not run, or the BUILT no_route verdict missing or failing (a leak, a blocked lap, a
# reached forbidden probe, an unreached spawn). check_race_kn5 / verify_kn5 / verify_kn5 --inis already
# stopped the chain (set -e) before this point.
RACE_RED=$(pyq "import json,os,sys
d=json.load(open(sys.argv[1],encoding='utf-8')) if os.path.exists(sys.argv[1]) else {}; rows=d.get('layouts') or {}; bad=[]
for lid in sys.argv[3:]:
    r=rows.get(lid) or {}; why=[]
    if r.get('fail') is None: why.append('drive_test not run')
    if (r.get('barrier_missing') or 0)>0: why.append('barrier_missing %s'%r.get('barrier_missing'))
    if (r.get('obstruction_stations') or 0)>0: why.append('obstruction_stations %s'%r.get('obstruction_stations'))
    p=os.path.join(sys.argv[2],'no_route.%s.json'%lid)
    if not os.path.exists(p): why.append('no_route not run')
    else:
        n=json.load(open(p,encoding='utf-8'))
        if n.get('fail') is not False or (n.get('leak_cells') or 0)>0 or n.get('blocked') or n.get('forbidden_reached') or n.get('spawns_unreached'):
            why.append('no_route FAIL (leak_cells %s, blocked %s, forbidden_reached %s, spawns_unreached %s)'%(n.get('leak_cells'),
                       len(n.get('blocked') or []), len(n.get('forbidden_reached') or []), len(n.get('spawns_unreached') or [])))
    if why: bad.append(lid+'['+'; '.join(why)+']')
print(' '.join(bad))" "$PROJ/data/drive_test.json" "$PROJ/data" $RACE_IDS)

if [ "$SCRATCH" = 1 ]; then
  step "sync outputs workshop -> airoso: SKIPPED"
  echo "SHIP_PROJ is a scratch project ($PROJ), not the workshop ($WS_PROJ): its outputs stay in the scratch copy —"
  echo "only the workshop feeds $SRC (loop.blend, data/, ai/)."
else
step "sync outputs workshop -> airoso"
cp "$PROJ/loop.blend" "$SRC/loop.blend"
for f in centerline.local.json centerline.raw.local.json median_bands.json dummies.json \
         finished_centerline.json gate_centerline.json lights.local.json connectors.local.json \
         mouths.json mouth_welds.json verify_mouths.json signs.local.json signs_preview.svg signs_measured.json \
         drive_test.json audit.json \
         barrier_bands.json race_authored.json race_verify.json race_verify.scenery.json race_kn5.json \
         $TERRAIN_DATA terrain.tiers.report.json; do
  [ -f "$PROJ/data/$f" ] && cp "$PROJ/data/$f" "$SRC/data/$f"
done
rm -f "$SRC/data/audit.race.json"   # 0047's shared race audit: retired (ledger 0049 audits each race layout on its own OBJ)
for lid in $LAYOUT_IDS; do
  for f in "dummies_$lid.json" "drive_test.$lid.json"; do [ -f "$PROJ/data/$f" ] && cp "$PROJ/data/$f" "$SRC/data/$f"; done
  if [ -d "$PROJ/ai/$lid" ]; then rm -rf "$SRC/ai/$lid"; mkdir -p "$SRC/ai"; cp -r "$PROJ/ai/$lid" "$SRC/ai/$lid"; fi   # track_folder is reproducible from the repo
done
for lid in $RACE_IDS; do
  for f in "no_route.$lid.json" "no_route.$lid.planned.json" "audit.$lid.json" "closure_$lid.kn5.json"; do
    [ -f "$PROJ/data/$f" ] && cp "$PROJ/data/$f" "$SRC/data/$f"
  done
done
[ -f "$PROJ/blender/split/split_manifest.json" ] && cp "$PROJ/blender/split/split_manifest.json" "$SRC/data/split_manifest.json"
for d in signs_plots race_plots; do
  if [ -d "$PROJ/data/$d" ]; then rm -rf "$SRC/data/$d"; cp -r "$PROJ/data/$d" "$SRC/data/$d"; fi
done
# track.obj / track.<id>.obj are 66-78 MB each and regenerable from the kn5s: never synced.
fi

echo; echo "GATES: street drive_test exit $DT_S, street audit exit $AU_S, race drive_test exit $DT_R, race audit exit $AU_R, race no_route exit $NR_R"
echo "  race layouts red on their own gates: ${RACE_RED:-none}"
if [ -n "$RACE_RED" ]; then
  echo "  NOT INSTALLED: race layout(s) $RACE_RED fail on their own gates (drive_test barrier_missing / obstruction,"
  echo "  the BUILT no_route containment fill) — no reference exists to be 'no worse than', so --force-install does not"
  echo "  apply (data/drive_test.<id>.json, data/no_route.<id>.json)"; exit 1
fi
if [ "$DT_S" != 0 ] || [ "$AU_S" != 0 ] || [ "$DT_R" != 0 ] || [ "$AU_R" != 0 ] || [ "$NR_R" != 0 ]; then
  if [ "$NR_R" != 0 ]; then
    echo "  NOT INSTALLED: no_route exited $NR_R (2 = an input error: the containment verdict could not be computed)"; exit 1
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
  # Assetto Corsa or Content Manager holding the folder makes the park (mv) fail half-way: refuse while either runs
  if command -v tasklist >/dev/null 2>&1; then
    RUNNING=$(tasklist //FO CSV //NH 2>/dev/null | grep -i -E '^"(acs[.]exe|acs_x86[.]exe|Content Manager[^"]*[.]exe)"' | cut -d, -f1 | tr '\n' ' ' || true)
    if [ -n "$RUNNING" ]; then echo "NOT INSTALLED: close $RUNNING first (Assetto Corsa / Content Manager hold the track folder)"; exit 1; fi
  else
    echo "(tasklist not found — make sure Assetto Corsa and Content Manager are closed)"
  fi
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
