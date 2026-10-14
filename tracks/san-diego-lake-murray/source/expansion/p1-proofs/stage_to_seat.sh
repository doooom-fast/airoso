#!/usr/bin/env bash
# the ship_sd.sh draft stage up to (and including) seat_terrain, same commands, on a fresh scratch project (iteration only)
set -euo pipefail
export PYTHONUTF8=1
AIROSO=C:/Users/Owner/Documents/GitHub/airoso/.claude/worktrees/wf_c6ab4b42-146-1
WS=C:/Users/Owner/Documents/GitHub/k10-sd-v021
PROJ="$1"
SRC="$AIROSO/tracks/san-diego-lake-murray"
V021="$SRC/scripts-v021"
BL="C:/Program Files/Blender Foundation/Blender 4.2/blender.exe"
V021_SHIM="import sys, importlib.util as u; s=u.spec_from_file_location('scripts', r'$V021/__init__.py', submodule_search_locations=[r'$V021']); m=u.module_from_spec(s); sys.modules['scripts']=m; s.loader.exec_module(m)"
TERRAIN_DATA="terrain.samples.json.gz corridor.i8.json i8.local.json i8.legacy.local.json deck_datum.samples.json ground_release.samples.json.gz freeway_i8.samples.json.gz"
cp "$SRC/track.config.json" "$PROJ/track.config.json"
cp "$SRC/start_positions.json" "$PROJ/start_positions.json"
for f in centerline.raw.local.json.pre-median connectors.local.json.pre-trim expansion.north.json; do [ -f "$SRC/data/$f" ] && cp "$SRC/data/$f" "$PROJ/data/$f"; done
for f in $TERRAIN_DATA; do [ -f "$SRC/data/$f" ] && cp "$SRC/data/$f" "$PROJ/data/$f"; done
mkdir -p "$PROJ/textures" && cp "$SRC/textures/chaparral_far_diffuse.jpg" "$PROJ/textures/" 2>/dev/null || true
(cd "$AIROSO" && python tools/deck_datum.py "$PROJ")
(cd "$AIROSO" && python tools/median_envelope.py "$PROJ")
(cd "$AIROSO" && python -m scripts.elevation.terrain_sample "$PROJ")
(cd "$WS" && "$BL" --background --python-exit-code 1 --python-expr "$V021_SHIM" --python "$V021/blender/build_loop_blend.py" -- "$PROJ" 2>&1 | grep "^\[blend\]\|Error\|Traceback" | tail -6)
(cd "$AIROSO" && python tools/route_connectors.py "$PROJ")
(cd "$AIROSO" && python tools/divide_connectors.py "$PROJ")
(cd "$AIROSO" && python tools/trim_connectors.py "$PROJ")
(cd "$AIROSO" && python -m scripts.elevation.terrain_sample "$PROJ")
(cd "$WS" && "$BL" --background --python-exit-code 1 --python-expr "$V021_SHIM" --python "$V021/blender/build_loop_blend.py" -- "$PROJ" 2>&1 | grep "^\[blend\]\|Error\|Traceback" | tail -6)
(cd "$WS" && "$BL" --background --python-exit-code 1 --python-expr "$V021_SHIM" --python "$AIROSO/tools/weld_mouths_blend.py" -- "$PROJ" 2>&1 | grep "^\[weld\]\|Error\|Traceback" )
cp "$PROJ/loop.blend" "$PROJ/loop.welded.blend"
(cd "$WS" && "$BL" --background --python-exit-code 1 --python "$AIROSO/tools/seat_terrain_blend.py" -- "$PROJ" 2>&1 | grep "^\[seat\]\|Error\|Traceback" )
cp "$PROJ/loop.blend" "$PROJ/loop.seated.blend"
echo STAGED
