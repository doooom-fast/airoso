#!/usr/bin/env bash
# The engine's DRAFT for one track — Phases 1-4, from track.config.json to data/track.obj. Nothing here
# builds a track: a track is built by the chain, tools/ship_track.sh <track> (docs/ONE-CHAIN.md §1), whose
# draft phase runs exactly these stages and then the underlay (scripts/blender/underlay.py: the OBJ into
# loop.blend as GEN_* collections). Kevin, 2026-10-28, ONE-CHAIN §2 row 1: the env / blend / kn5 / pack stages
# that made a complete track out of generated geometry are retired (ledger 0060); the four gates run in the
# chain's gate phase, on the BUILT kn5, never here.
#
#   ./scripts/build.sh tracks/<track>              # the whole draft, Phases 1-4
#   ./scripts/build.sh tracks/<track> mesh         # resume from the mesh stage
#   ./scripts/build.sh tracks/<track> --list       # list stages and exit
#
# Stages (in order). The front half hits the network (Overpass / USGS) and only needs re-running when the
# route or region changes; mesh is offline + deterministic.
#   gps     centerline (+ street labels on OSM routes) by source.type: osm / kml / from_track   -> data/centerline.geojson
#           (an aerial source runs python -m scripts.aerial.build_aerial instead — the chain's `aerial` step)
#   elev    sample + smooth terrain          (USGS 3DEP)             -> data/heightfield.npy, dem
#   project lat/lon/elev -> local metres, origin + true north        -> data/*.local.json, writes config
#   mesh    road ribbon + kerbs + verge + walls + ground              -> data/track.obj  (the underlay's input)
set -euo pipefail
# Windows Python defaults stdout to cp1252, which cannot encode the gates' ✓/━ glyphs — a PASSING
# gate then dies printing its own verdict (seen on verify_kn5, 2026-08-07). Force UTF-8 everywhere.
export PYTHONUTF8=1

PROJ="${1:?usage: build.sh <project-dir> [from-stage|--list]}"
FROM="${2:-gps}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# Git Bash hands MSYS /c/... paths to a WINDOWS Python that cannot resolve them (every stage runs
# `python -m scripts... "$PROJ"`). Normalise to a native path here, once, for every consumer.
# The [ -d ] guard keeps --list working with a bogus path and keeps the case from tripping set -e.
if [ -d "$PROJ" ]; then
  case "$(uname -s)" in
    MINGW*|MSYS*) PROJ="$(cd "$PROJ" && pwd -W)" ;;
    CYGWIN*)      PROJ="$(cygpath -m "$(cd "$PROJ" && pwd)")" ;;
  esac
fi
PY="${PYTHON:-python3}"
STAGES=(gps elev project mesh)

# Pre-flight: AC/CSP can hard-CRASH THE GPU (whole-PC freeze) on load when a kn5 carries a
# non-power-of-two texture (mipmap/DXT upload hangs the driver). Fail loudly before building.

if [[ "$FROM" == "--list" ]]; then printf '%s\n' "${STAGES[@]}"; exit 0; fi
# index of the start stage
START=-1; for i in "${!STAGES[@]}"; do [[ "${STAGES[$i]}" == "$FROM" ]] && START=$i; done
[[ $START -lt 0 ]] && { echo "unknown stage '$FROM' (one of: ${STAGES[*]})" >&2; exit 1; }

run() { echo; echo "━━━━ [$1] ${*:2}"; "${@:2}"; }
active() { local s; for s in "${STAGES[@]:$START}"; do [[ "$s" == "$1" ]] && return 0; done; return 1; }

SLUG="$($PY -c "import json,sys;print(json.load(open('$PROJ/track.config.json'))['slug'])")"
VER="$($PY -c "import json,sys;print(json.load(open('$PROJ/track.config.json'))['version'])")"

active gps     && { run gps     "$PY" -m scripts.gps.centerline "$PROJ"
                    run gps     "$PY" -m scripts.gps.street_labels "$PROJ"; }
active elev    &&   run elev    "$PY" -m scripts.elevation.heightfield "$PROJ"
active project &&   run project "$PY" -m scripts.geometry.projection "$PROJ"
# Real street circuits (osm_road_widths=true): replace the flat default width with per-vertex OSM
# lane-derived curb-to-curb widths + intersection pads. Runs after project (which writes the widths it
# overrides) and hits Overpass. Racetracks keep their configured widths.
active project && [ "$($PY -c "import json;print(json.load(open('$PROJ/track.config.json')).get('osm_road_widths',False))")" = "True" ] \
               &&  run widths  "$PY" -m scripts.gps.widths_from_osm "$PROJ"
active mesh    &&   run mesh    "$PY" -m scripts.geometry.build_mesh "$PROJ"
echo; echo "✓ draft complete: $PROJ ($SLUG v$VER) — data/track.obj; next: the chain (tools/ship_track.sh) or its underlay step"
