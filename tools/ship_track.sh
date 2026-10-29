#!/usr/bin/env bash
# The ship chain for any track — draft -> author -> ship -> gate -> install, one command, exits nonzero on any gate.
#
#   bash tools/ship_track.sh <track> [--no-install] [--skip-blend] [--force-install] [--dry-run] [--draft-only] [--from <step>]
#
# V3-PLAN P1 (tracks/lookout-lariat/V3-PLAN.md, "a ship chain that isn't San Diego"). tools/ship_sd.sh stays
# San Diego's chain of record (test_ship_sd_chain.py / test_engine_july_snapshot.py pin it; re-synced here after
# ledger 0046, 2026-10-12); this is the same chain with the track taken out of the script and put in
# tracks/<track>/ship.json.
#
# THE CLOSED VOCABULARY. ship.json (read and validated by tools/ship_track_spec.py) names WHICH steps run and
# in what order, per phase; it never says HOW. Every step name is a function written below, named
# <phase>_<step>; a name with no function exits 2 before any file is touched. Nothing from ship.json is ever
# executed: values reach this script as plain key<TAB>value lines (strict patterns, no eval, no bash -c, no
# command substitution on a value), and are used only as step names, relative paths and printed text.
#   draft  : steps --skip-blend skips (the engine draft and the scripted authoring that edit loop.blend)
#   author : steps every ship runs (layout dummies; the race furniture, idempotent — only when a layout
#            declares race_furniture; a config that declares one and a ship.json without the race author
#            step exits 2)
#   prep   : exactly prep, split (the --dry-run stop is right after the split)
#   ship   : exports, AI, packer, map, trees
#   gate   : the gates on the BUILT kn5 (every per-layout verdict file is removed first)
#
# Copied verbatim from tools/ship_sd.sh: set -euo pipefail; --python-exit-code 1 on every Blender call (a Python
# exception inside --python otherwise exits 0 and the chain ships what the last run left); absolute paths only;
# scratch isolation (SHIP_PROJ: a scratch project never syncs back and never installs); refusal to work inside
# airoso; --dry-run / --skip-blend / --force-install; the race layouts' own gates are never forced; refusal to
# install while Assetto Corsa runs (Content Manager may stay open — Kevin 2026-10-27); the previous install parked in
# $ARCHIVE/<stamp>/ (never a _prev beside it in content/tracks).
#
# Per track, from data, never from this script:
#   tracks/<track>/ship.json        workshop root + project folder, the steps, what syncs in and out, the
#                                   installed name prefix (tools/ship_track_spec.py has the schema)
#   track.config.json slug          every file name inside (<slug>.kn5, <slug>_race.kn5, ...)
#   track.config.json install_folder  the folder the install writes under content/tracks (plan A11)
#   track.config.json layouts[]     every per-layout step; race stages run only for race_furniture layouts
#
# THE ENGINE. The prep / exporter / spawn builder run from engine-july (SD's build of record, pinned by
# tracks/san-diego-lake-murray/engine-july-snapshot) ONLY when the track is san-diego-lake-murray; every other
# track runs airoso's own scripts/ac/. ship.json cannot name an engine (no such key). As in tools/ship_sd.sh, ENG=<dir>
# points San Diego's engine at a scratch COPY of engine-july (a change rehearsed before it is mirrored, recorded in
# the snapshot's PENDING-MIRROR.md5); it means nothing for any other track.
#
# SAN DIEGO'S ASSEMBLER runs from airoso's tracks/<track>/scripts-v021 (the tooling of record), registered as the
# `scripts` package inside Blender (V021_SHIM, as tools/ship_sd.sh) so its `from scripts.geometry import ...` can
# resolve neither to airoso's engine nor to anything beside the project.
#
# --skip-blend    resume from the authored loop.blend (skips the draft phase; the author phase still runs).
# --dry-run       stop right after the prep + split: nothing exported, synced back or installed. Pair with
#                 SHIP_PROJ=<scratch copy>. With no loop.blend and no draft step that can build one (or with
#                 --skip-blend), the chain stops before anything runs: "no blend yet" (exit 0 on a dry run,
#                 1 on a real one).
# --draft-only    sync the inputs and run the draft phase's DATA steps (route, paint centreline, config remap,
#                 their gates, elevation, projection, widths, the draft mesh; a network's graph, classes,
#                 elevation and mesh), stopping at the first step that needs Blender;
#                 nothing synced back, nothing installed.
# --from <step>   resume: every draft / author / prep / ship step BEFORE the named one is skipped (printed as skipped),
#                 the named step and everything after it run, and EVERY gate runs — a gate name is refused, as is
#                 --from with --skip-blend or --draft-only (its own resume rules). The sync-in still runs first (an
#                 edited config reaches the workshop). The skipped steps' outputs are whatever the last run left in the
#                 workshop: `--from split` re-splits the prepped blender/<slug>.blend (ledger 0060, 2026-10-29: the
#                 Exotics draft + prep is 22 minutes the split's fix did not need to repeat), `--from export_road`
#                 re-exports the last split, `--from verify_kn5` re-judges the last export.
# --force-install as tools/ship_sd.sh: install RED when the caller asserts no gate metric is worse than the
#                 reference; never covers a race layout red on its own gates or a no_route input error.
# SHIP_PROJ=<dir> run against a scratch copy of the workshop project (ABSOLUTE, outside airoso): builds, exports
#                 and gates into it, then SKIPS the sync-back and the install.
# SHIP_SPEC=<f>   use another ship.json (tests, rehearsals): the run is then a rehearsal — never synced back,
#                 never installed, whatever SHIP_PROJ says.
# AIROSO=<dir>    the airoso checkout whose tools/ and scripts/ run (default: the main checkout).
# ENG=<dir>       San Diego only: the engine-july tree the prep / exporter / spawn builder run from (default: the
#                 real one) — a scratch COPY to rehearse an engine-july change before it is mirrored.
# STREET_AI=draft|july  the street layouts' AI line; july needs ship.json street_ai_july (SD only).
set -euo pipefail
export PYTHONUTF8=1
AIROSO="${AIROSO:-C:/Users/Owner/Documents/GitHub/airoso}"
AIROSO_MAIN="C:/Users/Owner/Documents/GitHub/airoso"   # never a workshop, whatever AIROSO points at
BL="C:/Program Files/Blender Foundation/Blender 4.2/blender.exe"
AC="D:/SteamLibrary/steamapps/common/assettocorsa/content/tracks"
ARCHIVE="D:/k10-track-archive"   # old installs live here, never in content/tracks (Kevin 2026-10-11: "clear old versions")
STREET_AI="${STREET_AI:-draft}"
case "$STREET_AI" in draft|july) ;; *) echo "STREET_AI must be draft or july, got '$STREET_AI'"; exit 2;; esac
TRACK=""; INSTALL=1; SKIP_BLEND=0; FORCE=0; DRY=0; DRAFT_ONLY=0; FROM=""; WANT_FROM=0
for a in "$@"; do
  if [ "$WANT_FROM" = 1 ]; then FROM="$a"; WANT_FROM=0; continue; fi
  case "$a" in
  --no-install) INSTALL=0;; --skip-blend) SKIP_BLEND=1;; --force-install) FORCE=1;; --dry-run) DRY=1;;
  --draft-only) DRAFT_ONLY=1;;
  --from) WANT_FROM=1;;
  -*) echo "unknown flag: $a"; exit 2;;
  *) if [ -z "$TRACK" ]; then TRACK="$a"; else echo "one track per run (got '$TRACK' and '$a')"; exit 2; fi;;
esac; done
[ "$WANT_FROM" = 0 ] || { echo "--from needs a step name (the draft / author / prep / ship step to resume at)"; exit 2; }
[ -n "$TRACK" ] || { echo "usage: bash tools/ship_track.sh <track> [--no-install] [--skip-blend] [--force-install] [--dry-run] [--draft-only] [--from <step>]"; exit 2; }
case "$TRACK" in ""|-*|*[!a-z0-9-]*) echo "track '$TRACK' is not a track folder name"; exit 2;; esac
if [ "$DRAFT_ONLY" = 1 ] && [ "$SKIP_BLEND" = 1 ]; then echo "--draft-only runs the draft; --skip-blend skips it"; exit 2; fi
if [ -n "$FROM" ]; then
  case "$FROM" in *[!a-z0-9_]*) echo "--from '$FROM' is not a step name"; exit 2;; esac
  if [ "$DRAFT_ONLY" = 1 ] || [ "$SKIP_BLEND" = 1 ]; then echo "--from resumes at a step; --draft-only and --skip-blend have their own resume rules — one of the three"; exit 2; fi
fi
if [ "$DRY" = 1 ] || [ "$DRAFT_ONLY" = 1 ]; then INSTALL=0; fi
SRC="$AIROSO/tracks/$TRACK"
[ -d "$SRC" ] || { echo "no track folder $SRC"; exit 2; }
SPEC="${SHIP_SPEC:-$SRC/ship.json}"
if [ -n "${SHIP_SPEC:-}" ]; then REHEARSAL=1; else REHEARSAL=0; fi
[ -f "$SPEC" ] || { echo "no ship.json for $TRACK ($SPEC)"; exit 2; }
# the engine the prep / exporter / spawn builder run from: engine-july is San Diego's alone
if [ "$TRACK" = "san-diego-lake-murray" ]; then
  ENGINE="${ENG:-C:/Users/Owner/Documents/GitHub/engine-july}"
else
  ENGINE="$AIROSO"
fi

step() { echo; echo "=================== $1"; }
pyq() { (cd "$AIROSO" && python -c "$@"); }
no_race() { echo; echo "(no race layout declared: $1 skipped)"; }
# run_step <phase> <step>: the phase's function — with --from, skipped (and said so) until the named step is reached.
# The gates never go through here: every gate runs on every run, whatever --from says.
FROM_REACHED=0
run_step() {
  local phase="$1" n="$2"
  if [ -n "$FROM" ] && [ "$FROM_REACHED" = 0 ]; then
    if [ "$n" = "$FROM" ]; then FROM_REACHED=1; else echo "(--from $FROM: $phase $n skipped — the workshop keeps the last run's output)"; return 0; fi
  fi
  "${phase}_$n"
}

# =============================================================================================================
# THE VOCABULARY. One function per step name; ship.json picks from these and nothing else.
# =============================================================================================================

# --- draft: the route data (Lariat P2; tools run from airoso on "$PROJ") -------------------------------------
draft_gps() {
  step "draft: route centreline (scripts.gps.centerline -> data/centerline.geojson; by source.type: the OSM line, the KML route, or the traced / recorded track)"
  # the gps stage overwrites data/centerline.geojson with the OSM line. A paint centreline there is the line the
  # config's vertex indices and stations point into (track.config.json centerline_frame): keep it as
  # data/centerline.previous.geojson first, so tools/remap_centreline_config.py can map the config from it
  if pyq "import json,sys
f=next(f for f in json.load(open(sys.argv[1],encoding='utf-8'))['features'] if (f.get('properties') or {}).get('kind')=='full')
sys.exit(0 if 'paint_centreline' in (f.get('properties') or {}) else 1)" "$PROJ/data/centerline.geojson" 2>/dev/null; then
    cp "$PROJ/data/centerline.geojson" "$PROJ/data/centerline.previous.geojson"
    echo "kept the paint centreline as data/centerline.previous.geojson (the config's frame)"
  fi
  (cd "$AIROSO" && python -m scripts.gps.centerline "$PROJ")
}
draft_paint_centreline() {
  step "draft: paint centreline (tools/paint_centreline.py: the OSM line moved onto the traced paint, the climb at 1 m)"
  (cd "$AIROSO" && python tools/paint_centreline.py "$PROJ")
}
draft_remap_config() {
  step "draft: re-derive the config's vertices and stations onto the new line (tools/remap_centreline_config.py --write)"
  (cd "$AIROSO" && python tools/remap_centreline_config.py "$PROJ" --write)
}
draft_verify_centreline_paint() {
  step "gate: the centreline against the paint (tools/verify_centreline_paint.py: paint, curvature, topology, seam — hard)"
  (cd "$AIROSO" && python tools/verify_centreline_paint.py "$PROJ")
}
draft_route_oneway_check() {
  step "gate: no layout drives a one-way against its arrows outside its declared stretches (tools/route_oneway_check.py, hard)"
  (cd "$AIROSO" && python tools/route_oneway_check.py "$PROJ")
}
draft_elev() {
  step "draft: corridor elevation (scripts.elevation.heightfield, USGS 3DEP)"
  (cd "$AIROSO" && python -m scripts.elevation.heightfield "$PROJ")
}
draft_project() {
  step "draft: projection into the loop frame (scripts.geometry.projection)"
  (cd "$AIROSO" && python -m scripts.geometry.projection "$PROJ")
}
draft_widths() {
  step "draft: per-vertex OSM widths (scripts.gps.widths_from_osm)"
  (cd "$AIROSO" && python -m scripts.gps.widths_from_osm "$PROJ")
}
draft_aerial() {
  step "draft: aerial trace -> data/centerline.geojson (scripts.aerial.build_aerial: the asphalt off the georeferenced image; source.control_points, source.trace_px)"
  (cd "$AIROSO" && python -m scripts.aerial.build_aerial "$PROJ")
}
draft_mesh() {
  # the engine's draft geometry — road ribbon, kerbs, verge, the walls the data asks for, the ground — is the underlay's
  # input (fleet/REALISM.md §2 Job 1: the engine prepares truth, regenerable and unprecious). No furniture: build_env is
  # never a draft step (V3-PLAN P2 step 6)
  step "draft: the engine's draft geometry -> data/track.obj (scripts.geometry.build_mesh: 1ROAD / 1KERB / 1WALL / 1GRASS, no furniture)"
  (cd "$AIROSO" && python -m scripts.geometry.build_mesh "$PROJ")
}
# --- draft: a road NETWORK (source.type osm-network / kml-network; ONE-CHAIN §4 row 8) -------------------------
# the freeroam network draft that scripts/build_network.sh ran as its net -> classify -> elev -> mesh stages, as chain
# steps: a branching graph (both carriageways, every ramp and connector) instead of one ordered centreline, so it has
# its own elevation and mesh modules. No furniture: build_network_env is never a draft step (the chain's draft is
# geometry only, V3-PLAN P2 step 6). network_mesh writes data/track.obj, the underlay's input, unchanged.
draft_net() {
  step "draft: road network graph (scripts.gps.network: Overpass source.highways in source.bbox, mainlines held to source.refs -> data/network.geojson)"
  (cd "$AIROSO" && python -m scripts.gps.network "$PROJ")
}
draft_classify() {
  step "draft: network edge classes (scripts.gps.classify: OSM class, ref, lanes, layer, ramp -> width per edge, into data/network.geojson)"
  (cd "$AIROSO" && python -m scripts.gps.classify "$PROJ")
}
draft_network_elev() {
  step "draft: network elevation (scripts.elevation.network_elev, USGS 3DEP along every edge + the terrain grid -> data/network.elevation.json, data/heightfield.npy)"
  (cd "$AIROSO" && python -m scripts.elevation.network_elev "$PROJ")
}
draft_network_mesh() {
  step "draft: the network's draft geometry -> data/track.obj (scripts.geometry.build_network_mesh: 1ROAD / 1WALL / 1RUNOFF / 1GRASS tiles, OSM-layer flyover decks, no furniture)"
  (cd "$AIROSO" && python -m scripts.geometry.build_network_mesh "$PROJ")
}
draft_underlay() {
  step "draft: underlay -> loop.blend (scripts/blender/underlay.py: data/track.obj into GEN_* collections, never AUTH_*, never a scene reset)"
  [ -f "$AIROSO/scripts/blender/underlay.py" ] || { echo "no blend yet: scripts/blender/underlay.py (V3-PLAN P2 step 3) is not written"; exit 1; }
  "$BL" --background --python-exit-code 1 --python "$AIROSO/scripts/blender/underlay.py" -- "$PROJ" 2>&1 | grep "^\[underlay\]\|Error\|Traceback"
}

# --- draft: San Diego's assembler (tracks/<track>/scripts-v021 via V021_SHIM) + scripted authoring (airoso tools) ---
draft_deck_datum() {
  step "draft: real bridge decks between their real abutments (tools/deck_datum.py; LAWS L3, 3DEP cached)"
  # ledger 0046 v0.18.0 integration fix round: track.config.json road_datum.decks (y only, idempotent; no block = no-op)
  (cd "$AIROSO" && python tools/deck_datum.py "$PROJ")
}
draft_median_envelope() {
  step "draft: median envelope (self-gated)"
  (cd "$AIROSO" && python tools/median_envelope.py "$PROJ")
}
draft_terrain_sample() {
  step "draft: tiered terrain plan + 3DEP samples (cached; ledger 0046)"
  (cd "$AIROSO" && python -m scripts.elevation.terrain_sample "$PROJ")
}
draft_build_loop_blend() {
  step "draft: build loop.blend (scene regen — GEN layer)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python-expr "$V021_SHIM" --python "$V021/blender/build_loop_blend.py" -- "$PROJ" 2>&1 | grep "^\[blend\]\|Error\|Traceback" | tail -6)
}
draft_route_connectors() {
  step "draft: side streets from Kevin's routes (airoso data/routes.json)"
  (cd "$AIROSO" && python tools/route_connectors.py "$PROJ")
}
draft_divide_connectors() {
  step "draft: divided side streets -> one trunk + island (Del Cerro)"
  (cd "$AIROSO" && python tools/divide_connectors.py "$PROJ")
}
draft_stubs() {
  # PHASE 5 (ledger 0054), opt-in: STUBS=<file> (default $SRC/stubs.json) — as tools/ship_sd.sh. Without a declaration
  # no stub file of an earlier run survives in the project and no stub step does anything.
  local decl="${STUBS:-$SRC/stubs.json}"
  if [ -f "$decl" ]; then
    cp "$decl" "$PROJ/data/stubs.json"
    [ -f "$SRC/data/stubs.3dep.json" ] && cp "$SRC/data/stubs.3dep.json" "$PROJ/data/stubs.3dep.json"
  else
    rm -f "$PROJ/data/stubs.json" "$PROJ/data/stubs.plan.json" "$PROJ/data/stubs.built.json" "$PROJ/data/verify_stubs.json"
  fi
  if [ -f "$PROJ/data/stubs.json" ]; then
    step "draft: phase-5 side-road stubs -> short connectors at their real width, heading and 3DEP grade (tools/stub_roads.py)"
    (cd "$AIROSO" && python tools/stub_roads.py apply "$PROJ")
  fi
}
draft_trim_connectors() {
  step "draft: trim connectors at the mainline edge"
  (cd "$AIROSO" && python tools/trim_connectors.py "$PROJ")
}
draft_expansion_decorate() {
  step "draft: the north pieces' authored paint + raised medians (tools/expansion_pieces.py decorate; none taken = no-op)"
  # ledger 0054 P3: as tools/ship_sd.sh (the paint each north piece carries, its raised medians -> median_bands.json)
  (cd "$AIROSO" && python tools/expansion_pieces.py decorate "$PROJ")
}
draft_pads_plan() {
  [ -f "$SRC/data/pads.3dep.json" ] && cp "$SRC/data/pads.3dep.json" "$PROJ/data/pads.3dep.json"
  step "draft: junction pads plan (tools/junction_pad.py: the J2-J4 pads on the roads as built, the stubs' far-edge 3DEP; none declared = no-op)"
  (cd "$AIROSO" && python tools/junction_pad.py plan "$PROJ")
}
draft_terrain_resample() {
  step "draft: tiered terrain re-planned on the trimmed connectors (only new vertices fetched)"
  (cd "$AIROSO" && python -m scripts.elevation.terrain_sample "$PROJ")
}
draft_rebuild_loop_blend() {
  step "draft: rebuild loop.blend with trimmed connectors"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python-expr "$V021_SHIM" --python "$V021/blender/build_loop_blend.py" -- "$PROJ" 2>&1 | grep "^\[blend\]\|Error\|Traceback" | tail -6)
}
draft_weld_mouths() {
  step "draft: weld every side-street mouth onto its host (mitre + warp: road, curb/sidewalk, markings; self-checked)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python-expr "$V021_SHIM" --python "$AIROSO/tools/weld_mouths_blend.py" -- "$PROJ" 2>&1 | grep "^\[weld\]\|Error\|Traceback" )
}
draft_seat_terrain() {
  step "author: seat the terrain under every road (verge finer than the road)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/seat_terrain_blend.py" -- "$PROJ" 2>&1 | grep "^\[seat\]\|Error\|Traceback" )
}
draft_aprons() {
  step "author: corner aprons (route.aprons: the return pavement, its curb + walk, the ground under it; self-checked; none declared = no-op)"
  # ledger 0054 P1 fix round: corner aprons (tools/author_aprons_blend.py; track.config.json route.aprons, absent = no-op)
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_aprons_blend.py" -- "$PROJ" 2>&1 | grep "^\[apron\]\|Error\|Traceback" )
}
draft_pads() {
  step "author: junction pads (tools/author_junction_pad_blend.py: one deck per crossroads welded onto its arms, curb returns, K-rail stubs, the ground seated; self-checked; none planned = no-op)"
  # ledger 0054 P3 step 2 (as tools/ship_sd.sh): 1ROAD_pad_<id> + 1KERB_sidewalk_pad<id> + 1WALL_STUB_PAD_<id>_<stub>
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_junction_pad_blend.py" -- "$PROJ" 2>&1 | grep "^\[pads\]\|Error\|Traceback" )
}
draft_triangulate_terrain() {
  step "author: triangulate the terrain (BEAUTY, what the retired decimation did to every face; no vertex moves)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/triangulate_terrain_blend.py" -- "$PROJ" 2>&1 | grep "^\[tri\]\|Error\|Traceback" )
}
draft_ground_release() {
  step "author: release the near-road ground to the real earth in the declared zones + a rail on every new drop (self-checked)"
  # ledger 0046 v0.18.0 integration fix round: track.config.json terrain.ground_release.zones -> data/ground_release.json
  # (3DEP, cached), applied to TERRAIN before the bridge bodies; a rail on the curb at every new drop. No zones = no-op
  (cd "$AIROSO" && python tools/ground_release.py "$PROJ")
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/ground_release_blend.py" -- "$PROJ" 2>&1 | grep "^\[release\]\|Error\|Traceback" )
}
draft_median() {
  step "author: median island"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_median_blend.py" -- "$PROJ" 2>&1 | grep "^\[median" )
}
draft_stubs_author() {
  if [ -f "$PROJ/data/stubs.plan.json" ]; then
    step "author: phase-5 stubs — curb returns, corner pavement, K-rail barrier (tools/author_stubs_blend.py, self-checked)"
    (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_stubs_blend.py" -- "$PROJ" --stage author 2>&1 | grep "^\[stubs\]\|Error\|Traceback" )
  fi
}
draft_stubs_tidy() {
  if [ -f "$PROJ/data/stubs.plan.json" ]; then
    (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_stubs_blend.py" -- "$PROJ" --stage tidy 2>&1 | grep "^\[stubs\]\|Error\|Traceback" )
  fi
}
draft_gap_mouths() {
  step "author: gap the mainline sidewalk at every mouth"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/gap_mouths_blend.py" -- "$PROJ" 2>&1 | grep "^\[gap" )
}
draft_bridges() {
  step "author: bridge bodies under the overcrossings (soffit, fascia, abutments, pier bents; visual only, self-checked)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_bridges_blend.py" -- "$PROJ" 2>&1 | grep "^\[bridges\]\|Error\|Traceback" )
}
draft_scatter_strip() {
  step "author: export scatter positions, strip procedural vegetation (TreeFX replaces it)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/export_scatter_blend.py" -- "$PROJ" 2>&1 | grep "^\[scatter" )
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/strip_scenery_blend.py" -- "$PROJ" 2>&1 | grep "^\[strip" | cut -c1-160 )
}
draft_lamps() {
  step "author: Kevin's lamp model at every streetlight (LIGHTPOST + LIGHTS lens)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_lamps_blend.py" -- "$PROJ" 2>&1 | grep "^\[lamps\]\|Error\|Traceback" )
}
author_signs() {
  # ledger 0054 P4: after the race furniture, every ship (the furniture author empties the RACE_CLOSE_<TOKEN> collections
  # the race layouts' own plates live in); a track with no race layout gets its shared plates and nothing else
  step "author: W1-6 large-arrow signs at every tight corner (SIGNPLATE + SIGNARROW + SIGNPOST; the race layouts' own plates into RACE_CLOSE_<TOKEN>)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_signs_blend.py" -- "$PROJ" 2>&1 | grep "^\[signs\]\|Error\|Traceback" )
  (cd "$AIROSO" && python tools/verify_signs.py "$PROJ" --blend "$PROJ/loop.blend" --blender "$BL" | tail -8)
  (cd "$AIROSO" && PYTHONUTF8=1 python tools/plot_signs.py "$PROJ")
}

# --- author: every ship (idempotent) ------------------------------------------------------------------------
author_race_bands() {
  [ -n "$RACE_IDS" ] || { no_race race_bands; return 0; }
  local lid
  # the planned and built containment verdicts of an earlier run are never read as this run's: removed first
  for lid in $RACE_IDS; do rm -f "$PROJ/data/no_route.$lid.planned.json" "$PROJ/data/no_route.$lid.json"; done
  step "author: race-corridor declaration v2 (tools/barrier_bands.py: corridor solve + self-gates + PLANNED no_route per race layout, hard)"
  (cd "$AIROSO" && python tools/barrier_bands.py "$PROJ")
}
author_race_planned_gate() {
  [ -n "$RACE_IDS" ] || { no_race race_planned_gate; return 0; }
  step "gate: PLANNED no_route per race layout (the declared walls contain the lane — read back, hard)"
  # a declaration that skipped or lost its planned fill cannot reach Blender.
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
}
author_layout_dummies() {
  (cd "$AIROSO" && python tools/layout_dummies.py "$PROJ")         # data/dummies_<id>.json per layout; exit 1 on validation
}
author_race_author() {
  [ -n "$RACE_IDS" ] || { no_race race_author; return 0; }
  step "author: race furniture -> loop.blend: RACE (curb strips + kerbs, common) + RACE_CLOSE_<TOKEN> (one closure per race layout)"
  (cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_race_furniture_blend.py" -- "$PROJ" 2>&1 | grep "^\[race\]\|Error\|Traceback" )
}
author_race_verify() {
  [ -n "$RACE_IDS" ] || { no_race race_verify; return 0; }
  step "author: verify the authored furniture against its declaration (tools/verify_race.py, hard: common set + each layout)"
  (cd "$AIROSO" && python tools/verify_race.py "$PROJ")            # data/race_verify.json; exit 1
  (cd "$AIROSO" && python tools/plot_race_furniture.py "$PROJ" | tail -3)   # data/race_plots/*.png
}

# --- prep: exactly these two, in this order ------------------------------------------------------------------
prep_prep() {
  step "ship: prep (AC naming, 65k splits; multi-layout: NO AC_* dummies in the road scene)"
  "$BL" --background --python-exit-code 1 --python "$ENGINE/scripts/ac/build_kn5_loop.py" -- "$PROJ" 2>&1 | grep "prepped\|FATAL\|split 1GRASS\|split GRASS_FAR\|terrain tiles\|terrain conform\|T-junctions\|kept-cell refinement\|house seat\|multi-layout\|Error\|Traceback" | cut -c1-200
  # ledger 0046 v0.18.0 integration fix round: the I-8's own pavement on the PREPPED scene's final ground (scenery.freeway;
  # off = no data/freeway_i8.json = nothing runs). Part of prep: the split follows it (steps.prep stays prep, split)
  step "ship: the I-8's own pavement, lane lines and median barrier on the final ground (visual only; self-checked)"
  (cd "$AIROSO" && python tools/freeway_i8.py "$PROJ")
  if [ -f "$PROJ/data/freeway_i8.json" ]; then
    "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/author_freeway_blend.py" -- "$PROJ" --eng "$ENGINE" 2>&1 | grep "^\[freeway\]\|Error\|Traceback"
  fi
  # ledger 0054 P4 (buildings + rock), part of prep as the I-8 pavement is (steps.prep stays prep, split): the auto cuts'
  # steep faces -> 1GRASS_ROCK_<tile> on the prepped scene (no auto cut declared = no-op; exit 1 = the blend not saved).
  # ship_sd.sh thins the terrain before this (an echo there, not a step)
  step "ship: the road cuts' rock faces split out of the ground tiles (tools/rock_faces_blend.py: 1GRASS_ROCK_*, the sandstone skin, GRASS physics kept; self-checked; no auto cut declared = no-op)"
  rm -f "$PROJ/data/rock_faces.json"
  "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/rock_faces_blend.py" -- "$PROJ/blender/$SLUG.blend" --project "$PROJ" 2>&1 | grep "^\[rock\]\|Error\|Traceback"
}
prep_split() {
  local lid
  step "ship: split the prepped scene -> road / common race / closure per race layout / spawn scenes (tools/split_exports_blend.py)"
  "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/split_exports_blend.py" -- "$PROJ/blender/$SLUG.blend" --project "$PROJ" --out-dir "$PROJ/blender/split" 2>&1 | grep "^\[split\]"
  for lid in $RACE_IDS; do
    [ -f "$PROJ/blender/split/loop_closure_$lid.blend" ] || { echo "split wrote no loop_closure_$lid.blend — race layout $lid would load no closure"; exit 1; }
  done
}

# --- ship ----------------------------------------------------------------------------------------------------
ship_export_road() {
  step "ship: export road kn5 (shared by all layouts, spawn-free)"
  "$BL" --background --python-exit-code 1 --python "$ENGINE/scripts/ac/export_kn5_addon.py" -- "$PROJ" --blend "$PROJ/blender/split/loop_main.blend" 2>&1 | grep "KN5 EXISTS\|INI materials"
}
ship_export_race() {
  [ -n "$RACE_IDS" ] || { no_race export_race; return 0; }
  local lid tok
  step "ship: export the COMMON race-furniture kn5 (curb strips + kerbs; loaded by every race layout)"
  "$BL" --background --python-exit-code 1 --python "$ENGINE/scripts/ac/export_kn5_addon.py" -- "$PROJ" --blend "$PROJ/blender/split/loop_race.blend" --out "${SLUG}_race.kn5" 2>&1 | grep "KN5 EXISTS\|INI materials"
  # content guard: every mesh 1WALL_RACE* / 1KERB_RACE*, the race textures only, no AC_* node — exit 1 otherwise
  (cd "$AIROSO" && python -m scripts.modkit.inspect_kn5 "$PROJ/build/${SLUG}_race.kn5" --json "$PROJ/data/race_kn5.json" >/dev/null)
  (cd "$AIROSO" && python tools/check_race_kn5.py "$PROJ/data/race_kn5.json" --role common --bands "$PROJ/data/barrier_bands.json")
  for lid in $RACE_IDS; do
    # the owner token is the declaration's (barrier_bands.json corridors.<id>.token, from layouts[].closure_token)
    tok=$(pyq "import json,sys; print(json.load(open(sys.argv[1],encoding='utf-8'))['corridors'][sys.argv[2]]['token'])" "$PROJ/data/barrier_bands.json" "$lid")
    tok="${tok%$'\r'}"
    step "ship: export the $lid CLOSURE kn5 (1WALL_RACE_CLOSE_${tok^^}_* only; loaded by $lid alone)"
    "$BL" --background --python-exit-code 1 --python "$ENGINE/scripts/ac/export_kn5_addon.py" -- "$PROJ" --blend "$PROJ/blender/split/loop_closure_$lid.blend" --out "${SLUG}_closure_$lid.kn5" 2>&1 | grep "KN5 EXISTS\|INI materials"
    (cd "$AIROSO" && python -m scripts.modkit.inspect_kn5 "$PROJ/build/${SLUG}_closure_$lid.kn5" --json "$PROJ/data/closure_$lid.kn5.json" >/dev/null)
    (cd "$AIROSO" && python tools/check_race_kn5.py "$PROJ/data/closure_$lid.kn5.json" --role closure --owner "$tok")
  done
}
ship_spawn_kn5() {
  step "ship: spawn kn5 per layout (nodes only: AC_START/PIT/HOTLAP/TIME from data/dummies_<id>.json)"
  "$BL" --background --python-exit-code 1 --python "$ENGINE/scripts/ac/build_spawn_kn5.py" -- "$PROJ" 2>&1 | grep "^\[spawn_kn5\]"
}
# ledger 0052: is this race layout named in track.config.json "ai".layouts (the writer's opt-in)?
ai_layout() {
  local r
  r=$(pyq "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print(1 if sys.argv[2] in ((d.get('ai') or {}).get('layouts') or []) else 0)" "$PROJ/track.config.json" "$1")
  [ "${r%$'\r'}" = 1 ]
}
ship_ai() {
  local lid
  step "ship: AI lines per layout (race: V3 lane-offset drafts — GENERATED, ledger 0023; street: $STREET_AI)"
  for lid in $RACE_IDS; do
    # ledger 0052: a layout named in track.config.json "ai" is written on, and clamped to, the BUILT walls and road of
    # the kn5 set it loads (data/track.<id>.obj, extracted here: the writer refuses a missing or stale one) and is
    # judged at once against them. A track without the block writes the old draft, unjudged (as ship_sd.sh did).
    if ai_layout "$lid"; then
      (cd "$AIROSO" && python -m scripts.modkit.kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5" --kn5 "$PROJ/build/${SLUG}_race.kn5" --kn5 "$PROJ/build/${SLUG}_closure_$lid.kn5" --out "$PROJ/data/track.$lid.obj")
    fi
    (cd "$AIROSO" && python -m scripts.ac.write_ai_line "$PROJ" --layout "$lid" | grep -v "^  v\|^frame")
    if ai_layout "$lid"; then
      step "gate: verify_ai_line --layout $lid (hard; ledger 0052 - the written line vs the BUILT walls and road)"
      (cd "$AIROSO" && python tools/verify_ai_line.py "$PROJ" --layout "$lid")
    fi
  done
  for lid in $STREET_IDS; do
    rm -rf "$PROJ/ai/$lid"; mkdir -p "$PROJ/ai/$lid"     # never leave a stale ai_draft.json beside a copied line
    if [ "$STREET_AI" = july ]; then
      cp "$JULY_AI/fast_lane.ai" "$JULY_AI/pit_lane.ai" "$JULY_AI/side_l.csv" "$JULY_AI/side_r.csv" "$PROJ/ai/$lid/"
      echo "ai/$lid/: STREET_AI=july — the July write_ai_line DRAFT copied from $JULY_AI/ (generated, not an"
      echo "  in-game recording; ledger 0047 Notes)"
    else
      (cd "$AIROSO" && python -m scripts.ac.write_ai_line "$PROJ" --layout "$lid" | grep -v "^  v\|^frame")
    fi
  done
}
ship_verify_kn5() {
  step "ship: verify_kn5 (hard — spawn-free road, common race kn5 + one closure kn5 per race layout (its token only), one spawn kn5 per layout, facing, side, lane, sectors)"
  (cd "$AIROSO" && python -m scripts.ac.verify_kn5 "$PROJ")
}
ship_road_obj() {
  # written BEFORE the track folder (ledger 0046): ext_config's GrassFX lists and make_treefx's SURFACE_MATERIALS read
  # the mesh names off it, and the 1GRASS tile count follows the terrain
  step "gate: road kn5 -> gate OBJ (engine frame) + gate centreline"
  (cd "$AIROSO" && python -m scripts.modkit.kn5_to_gate_obj "$PROJ" --kn5 "$PROJ/build/$SLUG.kn5")
}
ship_track_folder() {
  step "ship: track folder (models_<id>.ini per layout, ui/<id>/, <id>/{map,data,ai}; a race layout without its closure kn5 is a HARD error)"
  (cd "$AIROSO" && python -m scripts.ac.track_folder "$PROJ") | grep -E "wrote|length_m|n_pits|layouts packed|removed stale|models|WARNING|ai/"
  cp "$PROJ/build/$SLUG.kn5" "$PROJ/build/$SLUG/"          # the race, closure + spawn kn5s are copied by track_folder itself
  # P4 lamps (ledger 0054 P4 step 2): one CSP [LIGHT_N] per lamp, at its lens, the approved look on every block — read
  # back off the WRITTEN ext_config.ini (0043 / 0056's duplicate-light class, hard); as in tools/ship_sd.sh
  (cd "$AIROSO" && python tools/check_lights_ini.py "$PROJ" --json "$PROJ/data/lights_ini_check.json")
}
ship_verify_inis() {
  step "ship: verify_kn5 --inis (hard — each race ini lists exactly road + common race + ITS closure + its spawns; none lists another layout's closure)"
  (cd "$AIROSO" && python -m scripts.ac.verify_kn5 "$PROJ" --inis)   # after the road-kn5 copy: every listed kn5 must be in the folder
}
ship_make_map() {
  step "ship: minimap in the KN5 frame, per layout (tools/make_map.py; a layout with map = lap gets its lap alone, map + outline)"
  (cd "$AIROSO" && python tools/make_map.py "$PROJ")
}
ship_treefx() {
  step "ship: TreeFX palms / street trees / scrub + the north network by zone (tools/make_treefx.py; the loop's cells byte-identical, the added cells per the aerial bins, caps by area)"
  # P4 trees (ledger 0054 P4 step 3 / A9): the loop's and the north's planted areas, densities and caps are printed here
  # before anything is written; data/treefx.report.json is the record (per zone, per species, the north per piece)
  (cd "$AIROSO" && python tools/make_treefx.py "$PROJ")
}
ship_race_scenery_gate() {
  [ -n "$RACE_IDS" ] || { no_race race_scenery_gate; return 0; }
  step "gate: scenery vs the race lanes and walls, on the WRITTEN trees.txt (tools/verify_race.py --scenery-only, hard)"
  (cd "$AIROSO" && python tools/verify_race.py "$PROJ" --scenery-only --trees "$PROJ/build/$SLUG/extension/trees/trees.txt")
}

# --- gate (exit codes collected; the verdict below decides the install) --------------------------------------
gate_verify_mouths() {
  step "gate: verify_mouths on the built road (every side-street mouth: mouth line, host lane, notch, approach — hard)"
  (cd "$AIROSO" && python tools/verify_mouths.py "$PROJ")
}
gate_verify_stubs() {
  if [ -f "$PROJ/data/stubs.plan.json" ]; then
    step "gate: verify_stubs on the built road (every declared stub: present, welded, drivable to its barrier, the barrier curb to curb and seated — hard)"
    rm -f "$PROJ/data/verify_stubs.json"
    (cd "$AIROSO" && python tools/verify_stubs.py "$PROJ")
  fi
}
gate_verify_pads() {
  rm -f "$PROJ/data/verify_pads.json"
  if [ -f "$PROJ/data/pads.built.json" ]; then
    step "gate: verify_pads on the built road (every junction pad: present, single coverage, seams <= 10 mm, no grass / curb on the deck, barriers, node height vs 3DEP — hard)"
    (cd "$AIROSO" && python tools/verify_pads.py "$PROJ")
  fi
}
gate_rib_check() {
  step "gate: terrain ribbing on the built ground (tools/rib_check.py: sub-cell features folded into staircases — hard)"
  (cd "$AIROSO" && python tools/rib_check.py "$PROJ" --json "$PROJ/data/rib_check.json")
}
gate_house_seat() {
  step "gate: houses on the built ground (tools/house_seat_check.py: floating, sunken or buried buildings — hard)"
  (cd "$AIROSO" && python tools/house_seat_check.py "$PROJ" --json "$PROJ/data/house_seat_check.json")
}
gate_drive_test_street() {
  local lid rc
  step "gate: drive_test, street layout (hard)"
  for lid in $STREET_IDS; do
    rc=0; (cd "$AIROSO" && python -m scripts.geometry.drive_test "$PROJ" --layout "$lid" 2>&1 | grep -v "drive-time\] sweep" | tail -30) || rc=$?
    [ "$rc" = 0 ] || DT_S=$rc
  done
}
gate_drive_test_lines() {
  # ledger 0054 P3 step 7 (as tools/ship_sd.sh): the north network's own lines, both directions; a red here is never
  # installed (no reference to be "no worse than")
  rm -f "$PROJ/data/drive_test.expansion.json" "$PROJ/data/drive_test.line."*.json
  DT_L=0
  if [ -f "$PROJ/data/expansion.north.json" ] && grep -q '"authored_take"' "$PROJ/track.config.json"; then
    step "gate: drive_test --line expansion (the north network's own lines, both directions, on the street OBJ — hard, never covered by --force-install)"
    (cd "$AIROSO" && python tools/expansion_lines.py "$PROJ")
    (cd "$AIROSO" && python -m scripts.geometry.drive_test "$PROJ" --line expansion 2>&1 | grep -v "drive-time\] sweep" | tail -40) || DT_L=$?
  fi
}
gate_audit_street() {
  if [ -n "$AUDIT_NOTE" ]; then step "gate: audit_mesh, street (hard total; $AUDIT_NOTE)"; else step "gate: audit_mesh, street (hard total)"; fi
  AU_S=0; (cd "$AIROSO" && python -m scripts.geometry.audit_mesh "$PROJ" 2>&1 | tail -16) || AU_S=$?
}
gate_race_gates() {
  [ -n "$RACE_IDS" ] || { no_race race_gates; return 0; }
  local lid rc
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
}
gate_fold_fans() {
  # ledger 0050: every levelled mainline fold pinch, read on every layout's BUILT gate OBJ (after race_gates wrote them);
  # hard — exit 1 stops the chain, --force-install does not cover it
  step "gate: verify_fold_fans (every levelled mainline fold pinch, all layouts, on the BUILT gate OBJs — hard)"
  rm -f "$PROJ/data/verify_fold_fans.json"
  (cd "$AIROSO" && python tools/verify_fold_fans.py "$PROJ")
}
gate_kn5_ground() {
  # ledger 0054 P3 repair round 1 (the gates lens: EXPANSION-PLAN V5 lists kn5_ground_check on all three layouts and
  # neither chain ran it): scripts/ac/kn5_ground_check.py on the kn5 SET each layout loads (the road + the street-only kn5,
  # or + the common race kn5 + its closure) — double-sheet terrain, furniture seating, lamp masts, the road on the ground
  # (kn5-internal: data/track.obj is this kn5's own gate OBJ); data/kn5_ground_check.<id>.json. A red counts with the
  # street gates (KG): --force-install covers it only where no key is worse than the reference (ledger 0047)
  local lid rc KX
  step "gate: kn5_ground_check per layout (EXPANSION-PLAN V5: the kn5 set each layout loads — terrain sheets, furniture seating, lamp masts, the road on the ground)"
  KG=0
  for lid in $LAYOUT_IDS; do
    rm -f "$PROJ/data/kn5_ground_check.$lid.json"
    if [[ " $RACE_IDS " == *" $lid "* ]]; then KX="--kn5 $PROJ/build/${SLUG}_race.kn5 --kn5 $PROJ/build/${SLUG}_closure_$lid.kn5"
    elif [ -f "$PROJ/build/${SLUG}_street.kn5" ]; then KX="--kn5 $PROJ/build/${SLUG}_street.kn5"; else KX=""; fi
    rc=0; (cd "$AIROSO" && python -m scripts.ac.kn5_ground_check "$PROJ" $KX --json "$PROJ/data/kn5_ground_check.$lid.json" 2>&1 | tail -14) || rc=$?
    echo "  kn5_ground_check $lid: exit $rc"
    [ "$rc" = 0 ] || KG=$rc
  done
}

# a draft step that needs no Blender (what --draft-only runs)
is_data_step() {
  case "$1" in
    gps|aerial|paint_centreline|remap_config|verify_centreline_paint|route_oneway_check|elev|project|widths|mesh) return 0;;
    net|classify|network_elev|network_mesh) return 0;;
    deck_datum|median_envelope|route_connectors|divide_connectors|trim_connectors|terrain_sample|terrain_resample) return 0;;
    *) return 1;;
  esac
}

# =============================================================================================================
# ship.json -> variables (tools/ship_track_spec.py validates; nothing read here is ever executed)
# =============================================================================================================
SPEC_LINES=$(cd "$AIROSO" && python tools/ship_track_spec.py "$SPEC" "$TRACK") || { echo "ship.json refused (above): $SPEC"; exit 2; }
WS=""; WS_SUB=""; REQUIRE_RACE=0; UI_PREFIX=""; AUDIT_NOTE=""; JULY_AI=""
DRAFT=(); AUTHOR=(); PREP=(); SHIP=(); GATE=()
IN_REQ=(); IN_OPT=(); IN_GLOB=(); IN_DIR=()
OUT_REQ=(); OUT_FILE=(); OUT_DIR=(); OUT_RM=(); OUT_MAP_FROM=(); OUT_MAP_TO=()
while IFS=$'\t' read -r k v w; do
  v="${v%$'\r'}"; w="${w%$'\r'}"
  case "$k" in
    workshop) WS="$v";;
    workshop_project) WS_SUB="$v";;
    require_race_layout) REQUIRE_RACE="$v";;
    ui_name_prefix) UI_PREFIX="$v";;
    audit_note) AUDIT_NOTE="$v";;
    street_ai_july) JULY_AI="$v";;
    step.draft) DRAFT+=("$v");;
    step.author) AUTHOR+=("$v");;
    step.prep) PREP+=("$v");;
    step.ship) SHIP+=("$v");;
    step.gate) GATE+=("$v");;
    in.required) IN_REQ+=("$v");;
    in.optional) IN_OPT+=("$v");;
    in.globs) IN_GLOB+=("$v");;
    in.dirs) IN_DIR+=("$v");;
    out.required) OUT_REQ+=("$v");;
    out.files) OUT_FILE+=("$v");;
    out.dirs) OUT_DIR+=("$v");;
    out.remove) OUT_RM+=("$v");;
    out.map) OUT_MAP_FROM+=("$v"); OUT_MAP_TO+=("$w");;
    "") ;;
    *) echo "tools/ship_track_spec.py wrote an unknown key '$k'"; exit 2;;
  esac
done <<< "$SPEC_LINES"
# the closed vocabulary: every name is a function above, or the chain stops here (exit 2, nothing touched)
for n in ${DRAFT[@]+"${DRAFT[@]}"}; do declare -F "draft_$n" >/dev/null || { echo "ship.json steps.draft: unknown step '$n' (no draft_$n in tools/ship_track.sh)"; exit 2; }; done
for n in ${AUTHOR[@]+"${AUTHOR[@]}"}; do declare -F "author_$n" >/dev/null || { echo "ship.json steps.author: unknown step '$n' (no author_$n in tools/ship_track.sh)"; exit 2; }; done
for n in ${PREP[@]+"${PREP[@]}"}; do declare -F "prep_$n" >/dev/null || { echo "ship.json steps.prep: unknown step '$n' (no prep_$n in tools/ship_track.sh)"; exit 2; }; done
for n in ${SHIP[@]+"${SHIP[@]}"}; do declare -F "ship_$n" >/dev/null || { echo "ship.json steps.ship: unknown step '$n' (no ship_$n in tools/ship_track.sh)"; exit 2; }; done
for n in ${GATE[@]+"${GATE[@]}"}; do declare -F "gate_$n" >/dev/null || { echo "ship.json steps.gate: unknown step '$n' (no gate_$n in tools/ship_track.sh)"; exit 2; }; done
if [ "$STREET_AI" = july ] && [ -z "$JULY_AI" ]; then echo "STREET_AI=july: ship.json names no street_ai_july for $TRACK"; exit 2; fi
# --from names a step of THIS ship.json's draft / author / prep / ship phases; never a gate (the gates always run)
if [ -n "$FROM" ]; then
  case " ${DRAFT[*]:-} ${AUTHOR[*]:-} ${PREP[*]:-} ${SHIP[*]:-} " in
    *" $FROM "*) ;;
    *) echo "--from '$FROM' is not a draft / author / prep / ship step of $SPEC (the gates always run); resume at one of: ${DRAFT[*]:-} ${AUTHOR[*]:-} ${PREP[*]:-} ${SHIP[*]:-}"; exit 2;;
  esac
fi

# =============================================================================================================
# the rails: absolute paths, nothing inside airoso, scratch derived from the workshop path — all before any copy
# =============================================================================================================
WS_PROJ="$WS/$WS_SUB"        # the real workshop's project folder (ship.json workshop + workshop_project)
PROJ="${SHIP_PROJ:-$WS_PROJ}"
case "$PROJ" in
  /*|[A-Za-z]:/*|[A-Za-z]:\\*) ;;
  *) echo "SHIP_PROJ must be an absolute path, got '$PROJ'"; exit 2;;
esac
# compare paths the way Windows does: one spelling (cygpath -m: C:/...), forward slashes, any case
norm() { local p; p=$(cygpath -m "$1" 2>/dev/null || printf '%s' "$1"); p="${p//\\//}"; p="${p%/}"; printf '%s' "${p,,}"; }
for root in "$AIROSO" "$AIROSO_MAIN"; do
  case "$(norm "$PROJ")" in
    "$(norm "$root")"|"$(norm "$root")"/*) echo "SHIP_PROJ '$PROJ' is inside airoso — use a scratch copy outside the repo"; exit 2;;
  esac
  case "$(norm "$WS")" in
    "$(norm "$root")"|"$(norm "$root")"/*) echo "ship.json workshop '$WS' is inside airoso — a workshop lives outside the repo"; exit 2;;
  esac
done
if [ "$REHEARSAL" = 0 ] && [ "$(norm "$PROJ")" = "$(norm "$WS_PROJ")" ]; then SCRATCH=0; else SCRATCH=1; fi
# the assembler's build_loop_blend.py / the weld do `from scripts.geometry import ...`: V021_SHIM (--python-expr runs
# before --python) registers `scripts` as the track's scripts-v021 package FIRST, so every `scripts.*` import inside
# them resolves there — never to airoso's engine, never to a scripts/ beside the project (as tools/ship_sd.sh)
V021="$SRC/scripts-v021"
V021_SHIM="import sys, importlib.util as u; s=u.spec_from_file_location('scripts', r'$V021/__init__.py', submodule_search_locations=[r'$V021']); m=u.module_from_spec(s); sys.modules['scripts']=m; s.loader.exec_module(m)"
for n in ${DRAFT[@]+"${DRAFT[@]}"}; do case "$n" in build_loop_blend|rebuild_loop_blend|weld_mouths)
  [ -f "$V021/blender/build_loop_blend.py" ] || { echo "ship.json steps.draft names $n but there is no assembler at $V021/blender/build_loop_blend.py"; exit 2; };;
esac; done
echo "track: $TRACK   workshop project: $PROJ$( [ "$SCRATCH" = 1 ] && printf ' (scratch: no sync-back, no install)')"
echo "engine (prep / export / spawn): $ENGINE"

# no blend and nothing in this run that can build one: stop before anything runs (V3-PLAN P1 done-when)
blend_builder_ready() {
  local n
  [ "$SKIP_BLEND" = 0 ] || return 1
  # resuming past the draft: nothing in this run builds the blend
  if [ -n "$FROM" ]; then case " ${DRAFT[*]:-} " in *" $FROM "*) ;; *) return 1;; esac; fi
  for n in ${DRAFT[@]+"${DRAFT[@]}"}; do case "$n" in
    build_loop_blend) [ -f "$V021/blender/build_loop_blend.py" ] && return 0;;
    underlay) [ -f "$AIROSO/scripts/blender/underlay.py" ] && return 0;;
  esac; done
  return 1
}
if [ "$DRAFT_ONLY" = 0 ] && [ ! -f "$PROJ/loop.blend" ] && ! blend_builder_ready; then
  echo; echo "no blend yet: $PROJ/loop.blend does not exist and nothing in this run can build it"
  if [ "$SKIP_BLEND" = 1 ]; then echo "  (--skip-blend resumes from an authored loop.blend)"
  elif [ -n "$FROM" ]; then echo "  (--from $FROM resumes past the draft; the draft that builds the blend ran in no earlier run)"
  else echo "  (draft steps: ${DRAFT[*]:-none}; the blend builder is build_loop_blend (tracks/$TRACK/scripts-v021) or underlay (scripts/blender/underlay.py, V3-PLAN P2 step 3) — list one in steps.draft)"; fi
  echo "  --draft-only runs the draft's data steps. Nothing synced in, nothing run, nothing installed."
  if [ "$DRY" = 1 ]; then echo "DRY RUN: stopped cleanly at 'no blend yet'."; exit 0; fi
  exit 1
fi

# THE FRAME (ledger 0060, 2026-10-29). This chain's frame is San Diego's: the prep imports the draft's local (E, up, N)
# as Blender (E, N, up), the exporter writes kn5 (E, up, -N) — geographically right with NO mirror and NO yaw (Lake
# Murray 0.19.1: mirror_x false, true_north_rotation_deg 0). mirror_x + true_north 180 were the V1 OBJ program's own
# import convention (x, -z, y) and its sun fix; through THIS chain they ship a MIRRORED track (every turn the wrong way)
# with the sun 180 deg off, every gate self-consistent and blind to it. Refused on the source config before any copy.
FRAME=$(pyq "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print('%s %s'%(bool(d.get('mirror_x',False)), float(d.get('true_north_rotation_deg') or 0.0)))" "$SRC/track.config.json")
FRAME="${FRAME%$'\r'}"
if [ "$FRAME" != "False 0.0" ]; then
  echo "track.config.json (mirror_x, true_north_rotation_deg) = ($FRAME): the chain's frame is San Diego's — mirror_x false, true_north_rotation_deg 0 (ledger 0060, 2026-10-29). mirror_x + 180 were the V1 OBJ program's import convention; through this chain they ship a mirrored track with the sun 180 deg off. Set both in tracks/$TRACK/track.config.json (a banked road_profile changes sign with mirror_x: profile.py)."
  exit 2
fi

# =============================================================================================================
# the chain
# =============================================================================================================
step "sync inputs airoso -> workshop ($PROJ)"
mkdir -p "$PROJ/data"
for f in ${IN_REQ[@]+"${IN_REQ[@]}"}; do mkdir -p "$(dirname "$PROJ/$f")"; cp "$SRC/$f" "$PROJ/$f"; done
for f in ${IN_OPT[@]+"${IN_OPT[@]}"}; do
  [ -f "$SRC/$f" ] && { mkdir -p "$(dirname "$PROJ/$f")"; cp "$SRC/$f" "$PROJ/$f"; }
done
for g in ${IN_GLOB[@]+"${IN_GLOB[@]}"}; do      # e.g. the TreeFX models (gitignored, personal use)
  d="$(dirname "$g")"; mkdir -p "$PROJ/$d"
  for f in "$SRC"/$g; do [ -f "$f" ] && cp "$f" "$PROJ/$d/"; done
done
for d in ${IN_DIR[@]+"${IN_DIR[@]}"}; do
  [ -d "$SRC/$d" ] && { mkdir -p "$PROJ/$d"; cp -r "$SRC/$d/." "$PROJ/$d/"; }
done
# the declared layouts drive every per-layout step below (never a hand-typed list)
LAYOUT_IDS=$(pyq "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print(' '.join(str(l['id']) for l in d['layouts']))" "$PROJ/track.config.json")
RACE_IDS=$(pyq "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print(' '.join(str(l['id']) for l in d['layouts'] if l.get('race_furniture')))" "$PROJ/track.config.json")
STREET_IDS=$(pyq "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print(' '.join(str(l['id']) for l in d['layouts'] if not l.get('race_furniture')))" "$PROJ/track.config.json")
SLUG=$(pyq "import json,sys; print(json.load(open(sys.argv[1],encoding='utf-8'))['slug'])" "$PROJ/track.config.json")
INSTALL_FOLDER=$(pyq "import json,sys; print(json.load(open(sys.argv[1],encoding='utf-8')).get('install_folder') or '')" "$PROJ/track.config.json")
LAYOUT_IDS="${LAYOUT_IDS%$'\r'}"; RACE_IDS="${RACE_IDS%$'\r'}"; STREET_IDS="${STREET_IDS%$'\r'}"; SLUG="${SLUG%$'\r'}"; INSTALL_FOLDER="${INSTALL_FOLDER%$'\r'}"
case "$SLUG" in ""|*[!a-z0-9_]*) echo "track.config.json slug '$SLUG' is not a file-name slug"; exit 2;; esac
case "$INSTALL_FOLDER" in ""|*[!A-Za-z0-9_]*) echo "track.config.json install_folder '$INSTALL_FOLDER' missing or not a folder name (plan A11)"; exit 2;; esac
echo "layouts: $LAYOUT_IDS   (race furniture: $RACE_IDS; street: $STREET_IDS; street AI = $STREET_AI)"
if [ -n "$FROM" ]; then echo "--from $FROM: every step before it is skipped (the sync-in ran above; every gate runs)"; fi
if [ "$REQUIRE_RACE" = 1 ] && [ -z "$RACE_IDS" ]; then echo "no race layout declared — ship.json says this chain is the three-version chain (ledger 0047)"; exit 2; fi
if [ -n "$RACE_IDS" ]; then
  case " ${AUTHOR[*]:-} " in *" race_author "*) ;; *) echo "layouts $RACE_IDS declare race_furniture but ship.json steps.author has no race_author — they would ship without it"; exit 2;; esac
fi

if [ "$SKIP_BLEND" = 0 ]; then
  for n in ${DRAFT[@]+"${DRAFT[@]}"}; do
    if [ "$DRAFT_ONLY" = 1 ] && ! is_data_step "$n"; then
      echo; echo "DRAFT ONLY: stopping before '$n' (the first draft step that needs Blender). Nothing synced back, nothing installed ($PROJ)."
      exit 0
    fi
    run_step draft "$n"
  done
fi
if [ "$DRAFT_ONLY" = 1 ]; then
  echo; echo "DRAFT ONLY: the draft's data steps ran. Nothing synced back, nothing installed ($PROJ)."
  exit 0
fi

for n in ${AUTHOR[@]+"${AUTHOR[@]}"}; do run_step author "$n"; done
for n in "${PREP[@]}"; do run_step prep "$n"; done

if [ "$DRY" = 1 ]; then
  echo; echo "DRY RUN: stopping before the kn5 exports. Would now run, in order:"
  echo "  ship: ${SHIP[*]:-none}"
  echo "  gate: ${GATE[*]:-none}"
  echo "  -> sync outputs -> install ($AC/$INSTALL_FOLDER; layouts $LAYOUT_IDS)."
  echo "  Nothing exported, nothing synced back, nothing installed ($PROJ)."
  exit 0
fi

for n in ${SHIP[@]+"${SHIP[@]}"}; do run_step ship "$n"; done

# A verdict from an earlier run is not this run's verdict: every per-layout gate file is removed before the gates
# run, so a gate that does not run reads as "not run" (red), never as last time's pass.
for lid in $LAYOUT_IDS; do rm -f "$PROJ/data/drive_test.$lid.json"; done
rm -f "$PROJ/data/verify_mouths.json" "$PROJ/data/rib_check.json" "$PROJ/data/house_seat_check.json"
for lid in $RACE_IDS; do rm -f "$PROJ/data/audit.$lid.json" "$PROJ/data/no_route.$lid.json" "$PROJ/data/track.$lid.obj"; done
rm -f "$PROJ/data/track.race.obj" "$PROJ/data/audit.race.json"
DT_S=0; AU_S=0; DT_R=0; AU_R=0; NR_R=0; DT_L=0; KG=0
for n in ${GATE[@]+"${GATE[@]}"}; do "gate_$n"; done
# a race layout red on its OWN gates is never installed, --force-install or not
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
RACE_RED="${RACE_RED%$'\r'}"

# expand {id} / {race} in a ship.json sync_out path: one path per line
expand() {
  local p="$1" lid
  case "$p" in
    *"{id}"*) for lid in $LAYOUT_IDS; do printf '%s\n' "${p//"{id}"/$lid}"; done;;
    *"{race}"*) for lid in $RACE_IDS; do printf '%s\n' "${p//"{race}"/$lid}"; done;;
    *) printf '%s\n' "$p";;
  esac
}
if [ "$SCRATCH" = 1 ]; then
  step "sync outputs workshop -> airoso: SKIPPED"
  echo "the project is a scratch copy or a rehearsal ($PROJ; ship.json $SPEC), not the workshop ($WS_PROJ): its outputs"
  echo "stay in the scratch copy — only the workshop feeds $SRC."
else
step "sync outputs workshop -> airoso"
for p in ${OUT_REQ[@]+"${OUT_REQ[@]}"}; do
  while IFS= read -r q; do mkdir -p "$(dirname "$SRC/$q")"; cp "$PROJ/$q" "$SRC/$q"; done < <(expand "$p")
done
for p in ${OUT_FILE[@]+"${OUT_FILE[@]}"}; do
  while IFS= read -r q; do
    if [ -f "$PROJ/$q" ]; then mkdir -p "$(dirname "$SRC/$q")"; cp "$PROJ/$q" "$SRC/$q"; fi
  done < <(expand "$p")
done
for i in ${OUT_MAP_FROM[@]+"${!OUT_MAP_FROM[@]}"}; do
  if [ -f "$PROJ/${OUT_MAP_FROM[$i]}" ]; then mkdir -p "$(dirname "$SRC/${OUT_MAP_TO[$i]}")"; cp "$PROJ/${OUT_MAP_FROM[$i]}" "$SRC/${OUT_MAP_TO[$i]}"; fi
done
for p in ${OUT_DIR[@]+"${OUT_DIR[@]}"}; do
  while IFS= read -r q; do
    if [ -d "$PROJ/$q" ]; then rm -rf "$SRC/$q"; mkdir -p "$(dirname "$SRC/$q")"; cp -r "$PROJ/$q" "$SRC/$q"; fi
  done < <(expand "$p")
done
for p in ${OUT_RM[@]+"${OUT_RM[@]}"}; do
  while IFS= read -r q; do rm -f "$SRC/$q"; done < <(expand "$p")
done
# gate OBJs (66-78 MB each, regenerable from the kn5s) are never in a sync_out list
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
    echo "  --force-install: installing RED (caller asserts no metric is worse than the reference)"
  else
    echo "  NOT INSTALLED (Kevin never loads a build the machine failed)"; exit 1
  fi
fi
if [ "$INSTALL" = 1 ] && [ "$SCRATCH" = 1 ]; then
  step "install: SKIPPED"
  echo "the project is a scratch copy or a rehearsal ($PROJ): never installed — only $WS_PROJ reaches $AC. The built"
  echo "folder is $PROJ/build/$SLUG (load it by hand if you mean to)."
elif [ "$INSTALL" = 1 ]; then
  step "install: $AC/$INSTALL_FOLDER (layouts $LAYOUT_IDS; previous build parked in $ARCHIVE/<stamp>/)"
  # Assetto Corsa holding the folder makes the park (mv) fail half-way: refuse while acs.exe runs. Content Manager may
  # stay open — Kevin, 2026-10-27: "you can install when that's running just not while AC is driving the track" (CM
  # does not lock the track files; a running acs.exe does). Until 2026-10-29 CM was refused too.
  if command -v tasklist >/dev/null 2>&1; then
    RUNNING=$(tasklist //FO CSV //NH 2>/dev/null | grep -i -E '^"(acs[.]exe|acs_x86[.]exe)"' | cut -d, -f1 | tr '\n' ' ' || true)
    if [ -n "$RUNNING" ]; then echo "NOT INSTALLED: close $RUNNING first (Assetto Corsa holds the track folder; Content Manager may stay open)"; exit 1; fi
  else
    echo "(tasklist not found — make sure Assetto Corsa is not running; Content Manager may stay open)"
  fi
  B="$PROJ/build/$SLUG"
  # the folder's shape follows the layout count (scripts/ac/track_folder.py): ONE layout = AC's single-config shape,
  # models.ini + ui/ui_track.json; more = models_<id>.ini + ui/<id>/ui_track.json per layout (Exotics' first install,
  # 2026-10-29, stopped on "missing models_full.ini" with a complete single-layout folder beside it)
  read -r -a _LAYOUTS <<< "$LAYOUT_IDS"; N_LAYOUTS=${#_LAYOUTS[@]}
  if [ "$N_LAYOUTS" = 1 ]; then
    [ -f "$B/models.ini" ] || { echo "missing $B/models.ini (one layout: track_folder packs models.ini, not models_$LAYOUT_IDS.ini)"; exit 1; }
  else
    for lid in $LAYOUT_IDS; do [ -f "$B/models_$lid.ini" ] || { echo "missing $B/models_$lid.ini"; exit 1; }; done
  fi
  STAMP=$(date +%Y-%m-%d_%H%M%S)
  for old in "$INSTALL_FOLDER" "${INSTALL_FOLDER}_prev"; do
    if [ -d "$AC/$old" ]; then mkdir -p "$ARCHIVE/$STAMP"; mv "$AC/$old" "$ARCHIVE/$STAMP/$old"; echo "parked $old in $ARCHIVE/$STAMP/"; fi
  done
  cp -r "$B" "$AC/$INSTALL_FOLDER"
  # the installed name: <ship.json ui_name_prefix> + an em dash + the layout's name (prefix passed as an argument);
  # one layout: ui/ui_track.json, the layout's name or, undeclared, the track's name (Exotics: "doooom Nevada — Nevada Nights")
  pyq "import json,glob,os,sys
cfg=json.load(open(sys.argv[1],encoding='utf-8'))
layouts=cfg['layouts']
names={str(lo['id']): lo.get('name', lo['id']) for lo in layouts}
seen=[]
if len(layouts)==1:
    lo=layouts[0]; p=os.path.join(sys.argv[2],'ui','ui_track.json')
    if not os.path.exists(p): raise SystemExit('installed folder lacks ui/ui_track.json (one layout: the single-config shape)')
    d=json.load(open(p,encoding='utf-8'))
    d['name']=sys.argv[3]+' '+chr(8212)+' '+str(lo.get('name') or cfg.get('name') or lo['id'])
    json.dump(d,open(p,'w',encoding='utf-8'),indent=2,ensure_ascii=False)
    seen.append(str(lo['id']))
    print('installed:',d['name'],d.get('version'))
else:
  for p in sorted(glob.glob(os.path.join(sys.argv[2],'ui','*','ui_track.json'))):
    lid=os.path.basename(os.path.dirname(p))
    d=json.load(open(p,encoding='utf-8'))
    d['name']=sys.argv[3]+' '+chr(8212)+' '+names[lid]
    json.dump(d,open(p,'w',encoding='utf-8'),indent=2,ensure_ascii=False)
    seen.append(lid)
    print('installed:',d['name'],d.get('version'))
missing=sorted(set(names)-set(seen))
if missing: raise SystemExit('installed folder lacks ui/<id>/ui_track.json for %s'%missing)" "$PROJ/track.config.json" "$AC/$INSTALL_FOLDER" "$UI_PREFIX"
fi
echo; echo "SHIP OK"
