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
#   <slug>_race_<lap>.kn5         LAPS (ledger 0054, opt-in: layouts[].lap + race.laps.<lap>, scripts/geometry/race_lap.py):
#                                 a race layout that names a lap loads THAT lap's common set (its curb strips + kerbs
#                                 on its own stitched line) instead of <slug>_race.kn5; its declaration is
#                                 data/barrier_bands.<lap>.json, its authored report race_authored.<lap>.json. Every
#                                 per-layout step below picks the right one (RK / BB per layout); with no lap declared
#                                 the chain is exactly the mainline one.
# (fleet/LAWS.md L8 as amended — the wording is in ledger 0047 pending Kevin's sign-off, Q9.)
#
# Stages (V3-PLAN §Phase 1 "the ONE pipeline"):
#   draft  : median_envelope → terrain_sample → build_loop_blend → trim_connectors → terrain_sample →
#            build_loop_blend → weld_mouths (GEN layer, regenerable; the weld mitres + warps every side-street
#            end onto its host, self-checked — 2026-10-11; terrain_sample = the ledger-0046 tiered 3DEP plan)
#   author : seat_terrain → median → gap_mouths → bridges → lamps → signs                 (scripted authoring)
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
# STUBS=<file>   PHASE 5 (ledger 0054, Kevin 2026-10-14: "a road we are not completing gets a barrier, not a curve"):
#                 the side-road stub declaration (tools/stub_roads.py declare; default $SRC/stubs.json). OPT-IN: with
#                 no declaration every stub step below is skipped and every output is what it was. With one, each
#                 `stub` entry becomes a short connector (tools/stub_roads.py apply, after divide / before trim) that
#                 the whole side-street chain builds and welds, tools/author_stubs_blend.py adds its curb returns,
#                 corner pavement and K-rail barrier around gap_mouths, and tools/verify_stubs.py gates it on the
#                 BUILT road (hard).
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

TERRAIN_DATA="terrain.samples.json.gz corridor.i8.json i8.local.json i8.legacy.local.json deck_datum.samples.json ground_release.samples.json.gz freeway_i8.samples.json.gz"
# the track's own textures (track.config.json texture_overrides with a project-relative path: the far ring's chaparral)
TRACK_TEXTURES="textures/chaparral_far_diffuse.jpg textures/sandstone_cut_diffuse.jpg textures/sandstone_cut_normal.jpg"
# P4 lamps: the OSM street_lamp research the north pieces' lamp planner reads (scenery.streetlights.expansion)
LAMP_RESEARCH="source/expansion/pipeline__osm_lamps_signals.json"
# ledger 0054 P4 (buildings): the two OSM footprint caches the assembler's buildings pass reads — the old one dresses the
# loop's own band exactly as v0.19.0, the expansion one (P0 step 7, provenance beside it) dresses the new band
BUILDING_CACHES="data/buildings.cache.json data/buildings.expansion.cache.json data/buildings.expansion.cache.json.provenance.json"
step() { echo; echo "=================== $1"; }
pyq() { (cd "$AIROSO" && python -c "$@"); }

step "sync inputs airoso -> workshop ($PROJ)"
cp "$SRC/track.config.json" "$PROJ/track.config.json"
cp "$SRC/start_positions.json" "$PROJ/start_positions.json"
# ledger 0054 P1: the authored intermediate of the north network (tools/author_expansion.py) — route_connectors reads it
# through route_connectors.authored_routes / authored_take; P2: terrain_sample plans the tiers + physical ground over it
# (terrain.tier_options.planned_pavement). P2 also grew the 40 m heightfield by whole cells (tools/grow_heightfield.py,
# terrain.grid_grow + tier_options.frame.pin): airoso's heightfield.npy + .meta.json are the source of truth, synced in
for f in centerline.raw.local.json.pre-median connectors.local.json.pre-trim expansion.north.json heightfield.npy heightfield.meta.json; do
  [ -f "$SRC/data/$f" ] && cp "$SRC/data/$f" "$PROJ/data/$f"
done
# ledger 0046: the 3DEP cache + the I-8 corridor (data with provenance, L2) — a fresh workshop never re-fetches them
for f in $TERRAIN_DATA; do
  [ -f "$SRC/data/$f" ] && cp "$SRC/data/$f" "$PROJ/data/$f"
done
for f in $TRACK_TEXTURES; do
  [ -f "$SRC/$f" ] && { mkdir -p "$(dirname "$PROJ/$f")"; cp "$SRC/$f" "$PROJ/$f"; }
done
# --- P4 lamps (ledger 0054 P4 step 2, EXPANSION-PLAN D4): the P0 research's OSM street_lamp nodes, read by the
# assembler's lamp planner (track.config.json scenery.streetlights.expansion.osm_lamps_file) — data with provenance
for f in $LAMP_RESEARCH; do
  [ -f "$SRC/$f" ] && { mkdir -p "$(dirname "$PROJ/$f")"; cp "$SRC/$f" "$PROJ/$f"; }
done
mkdir -p "$PROJ/source/trees" && cp "$SRC/source/trees/"*.bin "$PROJ/source/trees/" 2>/dev/null || true   # TreeFX models (gitignored, personal use)
# ledger 0054 P3: the junction pads' 3DEP cache (tools/junction_pad.py plan; data with provenance, L2)
[ -f "$SRC/data/pads.3dep.json" ] && cp "$SRC/data/pads.3dep.json" "$PROJ/data/pads.3dep.json"
for f in $BUILDING_CACHES; do
  [ -f "$SRC/$f" ] && cp "$SRC/$f" "$PROJ/$f"
done
# PHASE 5 side-road stubs (ledger 0054), opt-in: a declaration is synced down with its 3DEP cache; without one, no stub
# file of an earlier run survives in the project (the audit's barrier exemption reads stubs.built.json)
STUBS="${STUBS:-$SRC/stubs.json}"
if [ -f "$STUBS" ]; then
  cp "$STUBS" "$PROJ/data/stubs.json"
  [ -f "$SRC/data/stubs.3dep.json" ] && cp "$SRC/data/stubs.3dep.json" "$PROJ/data/stubs.3dep.json"
  echo "phase-5 stubs: declared in $STUBS"
else
  rm -f "$PROJ/data/stubs.json" "$PROJ/data/stubs.plan.json" "$PROJ/data/stubs.built.json" "$PROJ/data/verify_stubs.json"
fi
# the declared layouts drive every per-layout step below (never a hand-typed list)
LAYOUT_IDS=$(pyq "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print(' '.join(str(l['id']) for l in d['layouts']))" "$PROJ/track.config.json")
RACE_IDS=$(pyq "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print(' '.join(str(l['id']) for l in d['layouts'] if l.get('race_furniture')))" "$PROJ/track.config.json")
STREET_IDS=$(pyq "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print(' '.join(str(l['id']) for l in d['layouts'] if not l.get('race_furniture')))" "$PROJ/track.config.json")
echo "layouts: $LAYOUT_IDS   (race furniture: $RACE_IDS; street: $STREET_IDS; street AI = $STREET_AI)"
[ -n "$RACE_IDS" ] || { echo "no race layout declared — this chain is the three-version chain (ledger 0047)"; exit 2; }
# ledger 0054 LAPS: the laps the race layouts name (empty on every track today), whether any race layout still drives
# the mainline, and per race layout its COMMON race kn5 (RK) and its declaration (BB) — scripts/geometry/race_lap.py
LAP_IDS=$(pyq "import json,sys; from scripts.geometry import race_lap as L; print(' '.join(L.lap_ids(json.load(open(sys.argv[1],encoding='utf-8')))))" "$PROJ/track.config.json")
HAS_MAIN=$(pyq "import json,sys; from scripts.geometry import race_lap as L; print(1 if None in L.groups(json.load(open(sys.argv[1],encoding='utf-8'))) else 0)" "$PROJ/track.config.json")
declare -A RK BB
while read -r lid rk bb; do [ -n "$lid" ] && RK[$lid]=$rk && BB[$lid]=$bb; done < <(pyq "import json,sys
from scripts.geometry import race_lap as L
d=json.load(open(sys.argv[1],encoding='utf-8'))
for lo in d['layouts']:
    if lo.get('race_furniture'):
        lap=L.lap_of(lo); print(lo['id'], d['slug']+('_race.kn5' if not lap else '_race_%s.kn5'%lap), L.bands_file(lap))" "$PROJ/track.config.json" | tr -d '\r')   # (Windows python prints CRLF into the pipe; read keeps the CR)
if [ -n "$LAP_IDS" ]; then echo "laps: $LAP_IDS (mainline race layouts: $HAS_MAIN) — $(for lid in $RACE_IDS; do printf '%s->%s ' "$lid" "${RK[$lid]}"; done)"; fi

if [ "$SKIP_BLEND" = 0 ]; then
  step "draft: real bridge decks between their real abutments (tools/deck_datum.py; LAWS L3, 3DEP cached)"
  # ledger 0046 v0.18.0 integration fix round: College Ave's deck over I-8 was laid 25 m past its real north abutment
  # from a height read off the slope under the bridge (the road 2-3 m low for 60 m); track.config.json road_datum.decks
  # holds each deck straight between the abutments 3DEP shows, at the road's real height (y only, idempotent)
  (cd "$AIROSO" && python tools/deck_datum.py "$PROJ")
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
  if [ -f "$PROJ/data/stubs.json" ]; then
    step "draft: phase-5 side-road stubs -> short connectors at their real width, heading and 3DEP grade (tools/stub_roads.py)"
    (cd "$AIROSO" && python tools/stub_roads.py apply "$PROJ")
  fi
  step "draft: trim connectors at the mainline edge"
  (cd "$AIROSO" && python tools/trim_connectors.py "$PROJ")
  step "draft: the north pieces' authored paint + raised medians (tools/expansion_pieces.py decorate; none taken = no-op)"
  # ledger 0054 P3: per point of every north piece as trim left it, its paint (connector record `paint`, scripts-v021
  # ribbon.paint_markings — the assembler and the weld both read it) and its raised medians (median_bands.json
  # connector_islands, named after the piece); with route_connectors.authored_take naming no piece it prints one line
  (cd "$AIROSO" && python tools/expansion_pieces.py decorate "$PROJ")
  step "draft: junction pads plan (tools/junction_pad.py: the J2-J4 pads on the roads as built, the stubs' far-edge 3DEP; none declared = no-op)"
  # ledger 0054 P3 step 2: route.junction_pads -> data/pads.plan.json (each route arm's piece + end, each stub arm's far
  # edge at 3DEP, cached in data/pads.3dep.json, TLS verified); tools/author_junction_pad_blend.py builds it below
  (cd "$AIROSO" && python tools/junction_pad.py plan "$PROJ")
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
  step "author: corner aprons (route.aprons: the return pavement, its curb + walk, the ground under it; self-checked; none declared = no-op)"
  # ledger 0054 P1 fix round: J1's R 30 return (tools/author_aprons_blend.py, opt-in by track.config.json route.aprons):
  # 1ROAD_apron_<id> + 1KERB_sidewalk_ap<id>, the stub's curb on it removed, the ground seated; data/aprons.json for
  # gap_mouths / barrier_bands / verify_mouths / make_treefx / author_lamps. Exit 1 = loop.blend not saved
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_aprons_blend.py" -- "$PROJ" 2>&1 | grep "^\[apron\]\|Error\|Traceback" )
  step "author: junction pads (tools/author_junction_pad_blend.py: one deck per crossroads welded onto its arms, curb returns, K-rail stubs, the ground seated; self-checked; none planned = no-op)"
  # ledger 0054 P3 step 2 (EXPANSION-PLAN A4, docs/JUNCTIONS.md topology B): 1ROAD_pad_<id> + 1KERB_sidewalk_pad<id> +
  # 1WALL_STUB_PAD_<id>_<stub>; data/pads.built.json for audit_mesh (the barriers' D exemption) and verify_pads. Exit 1 =
  # loop.blend not saved
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_junction_pad_blend.py" -- "$PROJ" 2>&1 | grep "^\[pads\]\|Error\|Traceback" )
  # (the far-terrain decimation that paid for the prep's equal-width grass bands is gone — ledger 0046: the
  #  terrain is tiered at the source and the prep tiles 1GRASS by balanced bisection. It also triangulated every
  #  terrain face here, and the near-road ground the gates were tuned on is that triangulation's: kept, alone.)
  step "author: triangulate the terrain (BEAUTY, what the retired decimation did to every face; no vertex moves)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/triangulate_terrain_blend.py" -- "$PROJ" 2>&1 | grep "^\[tri\]\|Error\|Traceback" )
  step "author: release the near-road ground to the real earth in the declared zones + a rail on every new drop (self-checked)"
  # ledger 0046 v0.18.0 integration fix round (criterion 4's near-road rims): inside track.config.json
  # terrain.ground_release.zones (Alvarado Creek's bank, College Ave's south embankment, Alvarado Creek under Lake Murray
  # Blvd) the ground is 3DEP (data/ground_release.json, cached), never above a deck; a concrete rail stands on the curb
  # wherever the new ground drops within drive_test's excursion band. Before the bridge bodies (they read this ground);
  # the kn5 prep then leaves it alone (no contact feather, no kept-cell refinement). Exit 1 = loop.blend not saved
  (cd "$AIROSO" && python tools/ground_release.py "$PROJ")
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/ground_release_blend.py" -- "$PROJ" 2>&1 | grep "^\[release\]\|Error\|Traceback" )
  step "author: median island"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_median_blend.py" -- "$PROJ" 2>&1 | grep "^\[median" )
  if [ -f "$PROJ/data/stubs.plan.json" ]; then
    step "author: phase-5 stubs — curb returns, corner pavement, K-rail barrier (tools/author_stubs_blend.py, self-checked)"
    (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_stubs_blend.py" -- "$PROJ" --stage author 2>&1 | grep "^\[stubs\]\|Error\|Traceback" )
  fi
  step "author: gap the mainline sidewalk at every mouth"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/gap_mouths_blend.py" -- "$PROJ" 2>&1 | grep "^\[gap" )
  if [ -f "$PROJ/data/stubs.plan.json" ]; then
    (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_stubs_blend.py" -- "$PROJ" --stage tidy 2>&1 | grep "^\[stubs\]\|Error\|Traceback" )
  fi
  step "author: bridge bodies under the overcrossings (soffit, fascia, abutments, pier bents; visual only, self-checked)"
  # ledger 0046 fix round 4: with the I-8 cut out of the ground the two decks stood over it as paper-thin ribbons with
  # sky under them (AC culls back faces). tools/author_bridges_blend.py builds BRIDGESTRUCT_<span> under every declared
  # span that opens over the ground, all of it below the deck; exit 1 (loop.blend not saved) on a road under it or a
  # vertex over the deck
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_bridges_blend.py" -- "$PROJ" 2>&1 | grep "^\[bridges\]\|Error\|Traceback" )
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
if [ "$HAS_MAIN" = 1 ]; then
(cd "$AIROSO" && python tools/verify_race.py "$PROJ")            # data/race_verify.json; exit 1
fi
for lap in $LAP_IDS; do                                          # ledger 0054: each lap's group on its own line
  (cd "$AIROSO" && python tools/verify_race.py "$PROJ" --lap "$lap")   # data/race_verify.<lap>.json; exit 1
done
(cd "$AIROSO" && python tools/plot_race_furniture.py "$PROJ" | tail -3)   # data/race_plots/*.png

step "ship: prep (AC naming, 65k splits; multi-layout: NO AC_* dummies in the road scene)"
"$BL" --background --python-exit-code 1 --python "$ENG/scripts/ac/build_kn5_loop.py" -- "$PROJ" 2>&1 | grep "prepped\|FATAL\|split 1GRASS\|split GRASS_FAR\|terrain tiles\|terrain conform\|T-junctions\|kept-cell refinement\|house seat\|multi-layout\|Error\|Traceback" | cut -c1-200
# ledger 0054 P3 repair round 3 (an echo, not a `step`: tracks/san-diego-lake-murray/ship.json reproduces this chain's
# step headers and gains the thinning when the general chain does): the north roads' refinements left the ground with
# far more vertices than its surface needs (1GRASS 941,699 on r2run2, a 122.6 MB road kn5; v0.18.1 355k / 73.6 MB).
# tools/thin_terrain_blend.py thins every terrain tile of the PREPPED scene by error-bounded half-edge collapse (no
# vertex moves; +- 0.005-0.03 m within 22 m of a pavement, 0.10 / 0.15 m beyond; rib_check's lattice kept through
# data/terrain_thin.nodes.json.gz); self-checked, exit 1 = the blend not saved. Before the freeway drape (it reads this
# ground) and the split
rm -f "$PROJ/data/terrain_thin.json" "$PROJ/data/terrain_thin.nodes.json.gz"
echo; echo "=================== ship: thin the terrain, every vertex where the chain put it (tools/thin_terrain_blend.py; self-checked)"
"$BL" --background --python-exit-code 1 --python "$AIROSO/tools/thin_terrain_blend.py" -- "$PROJ/blender/$SLUG.blend" --project "$PROJ" 2>&1 | grep "^\[thin\]\|Error\|Traceback"
step "ship: the I-8's own pavement, lane lines and median barrier on the final ground (visual only; self-checked)"
# ledger 0046 v0.18.0 integration fix round (the view lens): track.config.json scenery.freeway — tools/freeway_i8.py
# plans both carriageways from the OSM ways the corridor was cut from, tools/author_freeway_blend.py drapes them on the
# PREPPED scene's final ground (the prep still moves it) and binds engine-july's pbr rows; no digit prefix, no gate
(cd "$AIROSO" && python tools/freeway_i8.py "$PROJ")
if [ -f "$PROJ/data/freeway_i8.json" ]; then
  "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_freeway_blend.py" -- "$PROJ" --eng "$ENG" 2>&1 | grep "^\[freeway\]\|Error\|Traceback"
fi
step "ship: the road cuts' rock faces split out of the ground tiles (tools/rock_faces_blend.py: 1GRASS_ROCK_*, the sandstone skin, GRASS physics kept; self-checked; no auto cut declared = no-op)"
# ledger 0054 P4 (buildings + rock): on the PREPPED, thinned ground — every ground triangle inside an auto-cut band standing
# terrain.rock_faces.slope_min_m_per_m or steeper moves into its own 1GRASS_ROCK_<tile> mesh (same prefix = same surfaces.ini
# key, same gates; pbr's own row = the rock texture; ext_config leaves it out of GRASS_MESHES). No vertex moves. Exit 1 =
# the blend not saved. data/rock_faces.json = the report
rm -f "$PROJ/data/rock_faces.json"
"$BL" --background --python-exit-code 1 --python "$AIROSO/tools/rock_faces_blend.py" -- "$PROJ/blender/$SLUG.blend" --project "$PROJ" 2>&1 | grep "^\[rock\]\|Error\|Traceback"
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
for lap in $LAP_IDS; do
  [ -f "$PROJ/blender/split/loop_race_$lap.blend" ] || { echo "split wrote no loop_race_$lap.blend — lap $lap would load no curb strip"; exit 1; }
done

if [ "$DRY" = 1 ]; then
  echo; echo "DRY RUN: stopping before the kn5 exports. Would now: export $SLUG.kn5 (road) + ${SLUG}_race.kn5 (common) +"
  echo "  $(for lid in $RACE_IDS; do printf '%s ' "${SLUG}_closure_$lid.kn5"; done)(one closure per race layout, each content-checked) +"
  if [ -n "$LAP_IDS" ]; then echo "  $(for lap in $LAP_IDS; do printf '%s ' "${SLUG}_race_$lap.kn5"; done)(one common set per lap, ledger 0054) +"; fi
  echo "  ${SLUG}__{$(echo $LAYOUT_IDS | tr ' ' ',')}.kn5 (spawns) -> AI per layout -> verify_kn5 -> track_folder -> verify_kn5 --inis"
  echo "  -> make_map -> make_treefx -> gates (street on track.obj; each race layout on its own track.<id>.obj:"
  echo "  drive_test, audit_mesh --layout, no_route BUILT) -> sync outputs -> install."
  echo "  Nothing exported, nothing synced back, nothing installed ($PROJ)."
  exit 0
fi

step "ship: export road kn5 (shared by all layouts, spawn-free)"
"$BL" --background --python-exit-code 1 --python "$ENG/scripts/ac/export_kn5_addon.py" -- "$PROJ" --blend "$PROJ/blender/split/loop_main.blend" 2>&1 | grep "KN5 EXISTS\|INI materials"
rm -f "$PROJ/build/${SLUG}_race_"*.kn5      # a retired lap's common kn5 never rides along (ledger 0054)
if [ "$HAS_MAIN" = 1 ]; then
step "ship: export the COMMON race-furniture kn5 (curb strips + kerbs; loaded by every race layout)"
"$BL" --background --python-exit-code 1 --python "$ENG/scripts/ac/export_kn5_addon.py" -- "$PROJ" --blend "$PROJ/blender/split/loop_race.blend" --out "${SLUG}_race.kn5" 2>&1 | grep "KN5 EXISTS\|INI materials"
# content guard (was a 20 MB size cap, which fired on a clean but flat-shaded 35.6 MB kn5): every mesh
# 1WALL_RACE* / 1KERB_RACE*, none a closure, >= 1 curb strip, exactly the declared kerb count, every texture
# from pbr.py's race rows, no AC_* node — exit 1 otherwise. The size is printed (WARN above 20 MB), never the gate.
(cd "$AIROSO" && python -m scripts.modkit.inspect_kn5 "$PROJ/build/${SLUG}_race.kn5" --json "$PROJ/data/race_kn5.json" >/dev/null)
(cd "$AIROSO" && python tools/check_race_kn5.py "$PROJ/data/race_kn5.json" --role common --bands "$PROJ/data/barrier_bands.json")
fi
for lap in $LAP_IDS; do
  # (an echo, not a `step`: the general chain's San Diego spec, tracks/san-diego-lake-murray/ship.json, reproduces this
  #  chain's step headers for the track as it is — no lap; the lap export joins that vocabulary when a spec first
  #  declares a lap)
  echo; echo "=================== ship: export lap $lap's COMMON race-furniture kn5 (its curb strips + kerbs; loaded by the race layouts on lap $lap)"
  "$BL" --background --python-exit-code 1 --python "$ENG/scripts/ac/export_kn5_addon.py" -- "$PROJ" --blend "$PROJ/blender/split/loop_race_$lap.blend" --out "${SLUG}_race_$lap.kn5" 2>&1 | grep "KN5 EXISTS\|INI materials"
  (cd "$AIROSO" && python -m scripts.modkit.inspect_kn5 "$PROJ/build/${SLUG}_race_$lap.kn5" --json "$PROJ/data/race_$lap.kn5.json" >/dev/null)
  (cd "$AIROSO" && python tools/check_race_kn5.py "$PROJ/data/race_$lap.kn5.json" --role common --lap "$lap" --bands "$PROJ/data/barrier_bands.$lap.json")
done
for lid in $RACE_IDS; do
  # the owner token is the declaration's (barrier_bands.json corridors.<id>.token, from layouts[].closure_token;
  # a layout on a lap: its barrier_bands.<lap>.json — BB)
  tok=$(pyq "import json,sys; print(json.load(open(sys.argv[1],encoding='utf-8'))['corridors'][sys.argv[2]]['token'])" "$PROJ/data/${BB[$lid]}" "$lid")
  step "ship: export the $lid CLOSURE kn5 (1WALL_RACE_CLOSE_${tok^^}_* only; loaded by $lid alone)"
  "$BL" --background --python-exit-code 1 --python "$ENG/scripts/ac/export_kn5_addon.py" -- "$PROJ" --blend "$PROJ/blender/split/loop_closure_$lid.blend" --out "${SLUG}_closure_$lid.kn5" 2>&1 | grep "KN5 EXISTS\|INI materials"
  (cd "$AIROSO" && python -m scripts.modkit.inspect_kn5 "$PROJ/build/${SLUG}_closure_$lid.kn5" --json "$PROJ/data/closure_$lid.kn5.json" >/dev/null)
  (cd "$AIROSO" && python tools/check_race_kn5.py "$PROJ/data/closure_$lid.kn5.json" --role closure --owner "$tok")
done
rm -f "$PROJ/build/${SLUG}_street.kn5" "$PROJ/data/street_kn5.json"   # a retired chicane's street set never rides along
if [ -f "$PROJ/blender/split/loop_street.blend" ]; then
  # ledger 0055 (an echo, not a `step`: tracks/san-diego-lake-murray/ship.json reproduces this chain's step headers
  # and gains the street set when the general chain learns race.chicanes): the median island over each declared
  # chicane's span (race.chicanes street_only_island) stands in Free Roam only — <slug>_street.kn5, loaded by every
  # non-race layout beside the road kn5; content-checked (street-only meshes, embedded textures, no AC_* node)
  echo; echo "=================== ship: export the STREET-ONLY kn5 (the median island over the Speedways' chicane span; the street layout alone)"
  "$BL" --background --python-exit-code 1 --python "$ENG/scripts/ac/export_kn5_addon.py" -- "$PROJ" --blend "$PROJ/blender/split/loop_street.blend" --out "${SLUG}_street.kn5" 2>&1 | grep "KN5 EXISTS\|INI materials"
  (cd "$AIROSO" && python -m scripts.modkit.inspect_kn5 "$PROJ/build/${SLUG}_street.kn5" --json "$PROJ/data/street_kn5.json" >/dev/null)
  (cd "$AIROSO" && python tools/check_street_kn5.py "$PROJ/data/street_kn5.json")
fi
STREET_KN5=""
[ -f "$PROJ/build/${SLUG}_street.kn5" ] && STREET_KN5="--kn5 $PROJ/build/${SLUG}_street.kn5"
step "ship: spawn kn5 per layout (nodes only: AC_START/PIT/HOTLAP/TIME from data/dummies_<id>.json)"
"$BL" --background --python-exit-code 1 --python "$ENG/scripts/ac/build_spawn_kn5.py" -- "$PROJ" 2>&1 | grep "^\[spawn_kn5\]"

step "ship: AI lines per layout (race: V3 lane-offset drafts — GENERATED, ledger 0023; street: $STREET_AI)"
# ledger 0052: with track.config.json "ai" the race writer seats the line on, and clamps it to, the BUILT walls and
# road of the kn5 set the layout loads (data/track.<id>.obj) and refuses a missing or stale OBJ — so that OBJ is
# extracted here, before the writer (the gate stage below re-extracts the same file from the same kn5s), and the
# written line is judged at once against it
for lid in $RACE_IDS; do
  (cd "$AIROSO" && python -m scripts.modkit.kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5" --kn5 "$PROJ/build/${RK[$lid]}" --kn5 "$PROJ/build/${SLUG}_closure_$lid.kn5" --out "$PROJ/data/track.$lid.obj")
  (cd "$AIROSO" && python -m scripts.ac.write_ai_line "$PROJ" --layout "$lid" | grep -v "^  v\|^frame")
  step "gate: verify_ai_line --layout $lid (hard; ledger 0052 - the written line vs the BUILT walls and road)"
  (cd "$AIROSO" && python tools/verify_ai_line.py "$PROJ" --layout "$lid")
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
rm -f "$PROJ/data/drive_test.expansion.json" "$PROJ/data/drive_test.line."*.json "$PROJ/data/verify_pads.json"
rm -f "$PROJ/data/verify_mouths.json" "$PROJ/data/rib_check.json" "$PROJ/data/house_seat_check.json" "$PROJ/data/verify_stubs.json"
for lid in $RACE_IDS; do rm -f "$PROJ/data/audit.$lid.json" "$PROJ/data/no_route.$lid.json" "$PROJ/data/track.$lid.obj"; done
rm -f "$PROJ/data/track.race.obj" "$PROJ/data/audit.race.json"
# the road gate OBJ is written BEFORE the track folder (ledger 0046): ext_config's GrassFX lists and make_treefx's
# SURFACE_MATERIALS read the mesh names off it, and the 1GRASS tile count now follows the terrain
step "gate: road kn5 -> gate OBJ (engine frame) + gate centreline"
# (+ the street-only kn5 when there is one, ledger 0055: data/track.obj is the STREET layout's kn5 set)
(cd "$AIROSO" && python -m scripts.modkit.kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5" $STREET_KN5)
step "ship: track folder (models_<id>.ini x3, ui/<id>/, <id>/{map,data,ai}; a race layout without its closure kn5 is a HARD error)"
(cd "$AIROSO" && python -m scripts.ac.track_folder "$PROJ") | grep -E "wrote|length_m|n_pits|layouts packed|removed stale|models|WARNING|ai/"
cp "$PROJ/build/$SLUG.kn5" "$PROJ/build/$SLUG/"          # the race, closure + spawn kn5s are copied by track_folder itself
# P4 lamps (ledger 0054 P4 step 2): one CSP [LIGHT_N] per lamp, at its lens, the approved look on every block — read back
# off the WRITTEN ext_config.ini (0043 / 0056's duplicate-light class, hard)
(cd "$AIROSO" && python tools/check_lights_ini.py "$PROJ" --json "$PROJ/data/lights_ini_check.json")
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
if [ "$HAS_MAIN" = 1 ]; then
(cd "$AIROSO" && python tools/verify_race.py "$PROJ" --scenery-only --trees "$PROJ/build/$SLUG/extension/trees/trees.txt")
fi
for lap in $LAP_IDS; do
  (cd "$AIROSO" && python tools/verify_race.py "$PROJ" --scenery-only --lap "$lap" --trees "$PROJ/build/$SLUG/extension/trees/trees.txt")
done

step "gate: verify_mouths on the built road (every side-street mouth: mouth line, host lane, notch, approach — hard)"
# tools/verify_mouths.py reads data/track.obj (the shipped road kn5) at every data/mouths.json record; exit 1 stops
# the chain (data/verify_mouths.json) — a mouth floating over its host or notched below it never reaches a gate run
(cd "$AIROSO" && python tools/verify_mouths.py "$PROJ")
if [ -f "$PROJ/data/stubs.plan.json" ]; then
  step "gate: verify_stubs on the built road (every declared stub: present, welded, drivable to its barrier, the barrier curb to curb and seated — hard)"
  # tools/verify_stubs.py reads data/track.obj (the shipped road kn5) at every data/stubs.plan.json stub; exit 1 stops the chain
  (cd "$AIROSO" && python tools/verify_stubs.py "$PROJ")
fi
if [ -f "$PROJ/data/pads.built.json" ]; then
  step "gate: verify_pads on the built road (every junction pad: present, single coverage, seams <= 10 mm, no grass / curb on the deck, barriers, node height vs 3DEP — hard)"
  # ledger 0054 P3 step 2 (EXPANSION-PLAN V3): tools/verify_pads.py reads data/track.obj; exit 1 stops the chain
  (cd "$AIROSO" && python tools/verify_pads.py "$PROJ")
fi
step "gate: terrain ribbing on the built ground (tools/rib_check.py: sub-cell features folded into staircases — hard)"
# ledger 0046 fix round 2: a feature narrower than two terrain cells (a concrete channel, a cut-slope bench) point-
# sampled every 5 m and folded across its grain shows as washboard ribs; exit 1 (data/rib_check.json) past the
# GATES-CHANGELOG 2026-10-13 limits, beyond 20 m of a pavement (the near-road ground is the drive gates')
(cd "$AIROSO" && python tools/rib_check.py "$PROJ" --json "$PROJ/data/rib_check.json")
step "gate: houses on the built ground (tools/house_seat_check.py: floating, sunken or buried buildings — hard)"
# ledger 0046 fix round 3: every OSM house / building stands on the ground that ships — its bottom touches the
# lowest ground under its walls (not above it, not a metre below it) and its roof clears the highest; exit 1
# (data/house_seat_check.json) past the GATES-CHANGELOG 2026-10-13 fix round 3 limits
(cd "$AIROSO" && python tools/house_seat_check.py "$PROJ" --json "$PROJ/data/house_seat_check.json")
step "gate: drive_test, street layout (hard)"
DT_S=0; (cd "$AIROSO" && python -m scripts.geometry.drive_test "$PROJ" --layout street 2>&1 | grep -v "drive-time\] sweep" | tail -30) || DT_S=$?
DT_L=0
if [ -f "$PROJ/data/expansion.north.json" ] && grep -q '"authored_take"' "$PROJ/track.config.json"; then
  step "gate: drive_test --line expansion (the north network's own lines, both directions, on the street OBJ — hard, never covered by --force-install)"
  # ledger 0054 P3 step 7 (EXPANSION-PLAN V6, Risk 10): tools/expansion_lines.py strings each direction's right-hand
  # carriageway J1 -> ... -> J5 (and back) through the pads; drive_test --line drives them (data/drive_test.expansion.json).
  # The new roads have no reference to be "no worse than": a red here is never installed
  (cd "$AIROSO" && python tools/expansion_lines.py "$PROJ")
  (cd "$AIROSO" && python -m scripts.geometry.drive_test "$PROJ" --line expansion 2>&1 | grep -v "drive-time\] sweep" | tail -40) || DT_L=$?
fi
step "gate: audit_mesh, street (hard total; the regression floor — D 0 / K 20 / I 20 / F 13 since v0.18.0: the I-8 deck rails stand on the curb, 0.15 m off the pavement; D 512 while they stood on its edge, since the 2026-10-11 mouth weld + fold mend, was 512 / 154 / 145 / 15)"
AU_S=0; (cd "$AIROSO" && python -m scripts.geometry.audit_mesh "$PROJ" 2>&1 | tail -16) || AU_S=$?
DT_R=0; AU_R=0; NR_R=0
for lid in $RACE_IDS; do
  step "gate: $lid — road + common race + ITS closure kn5 -> ONE gate OBJ (the kn5 set $lid loads) — data/track.$lid.obj"
  (cd "$AIROSO" && python -m scripts.modkit.kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5" --kn5 "$PROJ/build/${RK[$lid]}" --kn5 "$PROJ/build/${SLUG}_closure_$lid.kn5" --out "$PROJ/data/track.$lid.obj")
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
step "gate: verify_fold_fans (every levelled mainline fold pinch, all layouts, on the BUILT gate OBJs — hard)"
# ledger 0050: where the road ribbon is wider than twice its corner's radius the weld pinches the inside edge to one
# point at ONE height (the midpoint of its legs, both legs eased to it). This reads the three built gate OBJs at every
# such pinch: no road-on-road step, no grass on top in the lane, the pinch at its midpoint, the race walls inside
# no_route's band; exit 1 (data/verify_fold_fans.json) stops the chain, --force-install does not cover it
rm -f "$PROJ/data/verify_fold_fans.json"
(cd "$AIROSO" && python tools/verify_fold_fans.py "$PROJ")
step "gate: kn5_ground_check per layout (EXPANSION-PLAN V5: the kn5 set each layout loads — terrain sheets, furniture seating, lamp masts, the road on the ground)"
# ledger 0054 P3 repair round 1 (the gates lens: EXPANSION-PLAN V5 lists kn5_ground_check on all three layouts and
# neither chain ran it): scripts/ac/kn5_ground_check.py on the kn5 SET each layout loads (the road + the street-only kn5,
# or + the common race kn5 + its closure) — double-sheet terrain, furniture seating, lamp masts, the road on the ground
# (kn5-internal: data/track.obj is this kn5's own gate OBJ); data/kn5_ground_check.<id>.json. A red counts with the
# street gates (KG): --force-install covers it only where no key is worse than the reference (ledger 0047)
KG=0
for lid in $LAYOUT_IDS; do
  rm -f "$PROJ/data/kn5_ground_check.$lid.json"
  if [[ " $RACE_IDS " == *" $lid "* ]]; then KX="--kn5 $PROJ/build/${RK[$lid]} --kn5 $PROJ/build/${SLUG}_closure_$lid.kn5"; else KX="$STREET_KN5"; fi
  rc=0; (cd "$AIROSO" && python -m scripts.ac.kn5_ground_check "$PROJ" $KX --json "$PROJ/data/kn5_ground_check.$lid.json" 2>&1 | tail -14) || rc=$?
  echo "  kn5_ground_check $lid: exit $rc"
  [ "$rc" = 0 ] || KG=$rc
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
         finished_centerline.json gate_centerline.json lights.local.json lights_ini_check.json connectors.local.json \
         mouths.json mouth_welds.json aprons.json aprons.lamps.json pads.plan.json pads.built.json pads.3dep.json verify_pads.json verify_mouths.json verify_fold_fans.json rib_check.json house_seat_check.json signs.local.json signs_preview.svg signs_measured.json \
         drive_test.json drive_test.expansion.json drive_lines.expansion.json audit.json stubs.plan.json stubs.built.json verify_stubs.json stubs.3dep.json \
         barrier_bands.json race_authored.json race_verify.json race_verify.scenery.json race_kn5.json street_kn5.json \
         $TERRAIN_DATA terrain.tiers.report.json terrain_thin.json rock_faces.json bridges.authored.json          deck_datum.json ground_release.json ground_release.report.json ground_release.auto_cuts.json freeway_i8.json freeway_i8.report.json; do
  [ -f "$PROJ/data/$f" ] && cp "$PROJ/data/$f" "$SRC/data/$f"
done
rm -f "$SRC/data/audit.race.json"   # 0047's shared race audit: retired (ledger 0049 audits each race layout on its own OBJ)
for lid in $LAYOUT_IDS; do
  for f in "dummies_$lid.json" "drive_test.$lid.json" "kn5_ground_check.$lid.json"; do [ -f "$PROJ/data/$f" ] && cp "$PROJ/data/$f" "$SRC/data/$f"; done
  if [ -d "$PROJ/ai/$lid" ]; then rm -rf "$SRC/ai/$lid"; mkdir -p "$SRC/ai"; cp -r "$PROJ/ai/$lid" "$SRC/ai/$lid"; fi   # track_folder is reproducible from the repo
done
for lid in $RACE_IDS; do
  for f in "no_route.$lid.json" "no_route.$lid.planned.json" "audit.$lid.json" "closure_$lid.kn5.json" "ai_verify.$lid.json"; do
    [ -f "$PROJ/data/$f" ] && cp "$PROJ/data/$f" "$SRC/data/$f"
  done
done
for lap in $LAP_IDS; do                                         # ledger 0054: each lap's line, declaration and reports
  for f in "lap.$lap.json" "barrier_bands.$lap.json" "race_authored.$lap.json" "race_verify.$lap.json" \
           "race_verify.scenery.$lap.json" "race_$lap.kn5.json"; do
    [ -f "$PROJ/data/$f" ] && cp "$PROJ/data/$f" "$SRC/data/$f"
  done
done
[ -f "$PROJ/blender/split/split_manifest.json" ] && cp "$PROJ/blender/split/split_manifest.json" "$SRC/data/split_manifest.json"
for d in signs_plots race_plots; do
  if [ -d "$PROJ/data/$d" ]; then rm -rf "$SRC/data/$d"; cp -r "$PROJ/data/$d" "$SRC/data/$d"; fi
done
# track.obj / track.<id>.obj are 66-78 MB each and regenerable from the kn5s: never synced.
fi

if [ "$DT_L" != 0 ]; then
  echo; echo "  NOT INSTALLED: drive_test --line expansion exited $DT_L (the north network's own drive gate; no reference"
  echo "  exists to be 'no worse than', so --force-install does not apply — data/drive_test.expansion.json)"; exit 1
fi
echo; echo "GATES: street drive_test exit $DT_S, street audit exit $AU_S, race drive_test exit $DT_R, race audit exit $AU_R, race no_route exit $NR_R, kn5_ground_check exit $KG"
echo "  race layouts red on their own gates: ${RACE_RED:-none}"
if [ -n "$RACE_RED" ]; then
  echo "  NOT INSTALLED: race layout(s) $RACE_RED fail on their own gates (drive_test barrier_missing / obstruction,"
  echo "  the BUILT no_route containment fill) — no reference exists to be 'no worse than', so --force-install does not"
  echo "  apply (data/drive_test.<id>.json, data/no_route.<id>.json)"; exit 1
fi
if [ "$DT_S" != 0 ] || [ "$AU_S" != 0 ] || [ "$DT_R" != 0 ] || [ "$AU_R" != 0 ] || [ "$NR_R" != 0 ] || [ "$KG" != 0 ]; then
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
