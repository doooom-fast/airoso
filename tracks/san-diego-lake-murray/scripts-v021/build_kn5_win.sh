#!/usr/bin/env bash
# July v0.21.0 build_kn5.sh, patched for the Windows box ONLY (paths + no zip).
# Engine: worktree at the July pin v0.24.3 — NOT .engine, NOT the modern engine.
set -euo pipefail
PROJ="${1:-project}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
BL="${BLENDER:-C:/Program Files/Blender Foundation/Blender 4.2/blender.exe}"
ENGINE="$(cd "$ROOT/../engine-july" && pwd)"
cd "$PROJ" && PROJ_ABS="$(pwd -W 2>/dev/null || pwd)" && cd "$ROOT"
SLUG="$($PY -c "import json;print(json.load(open('$PROJ/track.config.json'))['slug'])")"
export PYTHONUTF8=1

echo "== prep loop.blend -> AC-ready .blend (JULY engine loop front-end, v0.24.3)"
"$BL" --background --python "$ENGINE/scripts/ac/build_kn5_loop.py"   -- "$PROJ_ABS"
echo "== export kn5 (JULY engine addon)"
"$BL" --background --python "$ENGINE/scripts/ac/export_kn5_addon.py" -- "$PROJ_ABS"
echo "== verify (JULY gates, reported not gating the install decision)"
(cd "$ENGINE" && "$PY" -m scripts.ac.verify_kn5 "$PROJ_ABS") || echo "  (july verify FAIL — reported)"
echo "== track folder (JULY engine)"
(cd "$ENGINE" && "$PY" -m scripts.ac.track_folder "$PROJ_ABS") | sed 's/^/   /'
cp "$PROJ/build/$SLUG.kn5" "$PROJ/build/$SLUG/"
echo "OK installable folder -> $PROJ/build/$SLUG"
