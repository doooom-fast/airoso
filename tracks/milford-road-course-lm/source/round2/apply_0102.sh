#!/usr/bin/env bash
# Milford round 2 (ledger 0102): round 1's 0.1.14 -> 0.1.15, every step in order, from the repo root.
#   NP=<a python with numpy, scipy and PIL> bash tracks/milford-road-course-lm/source/round2/apply_0102.sh
# 1. the config edits (edit_config_0102.py: GM's loop, the station-keyed spans, T3 off the lap, the banked turn's section,
#    the grid's registration, the shoulder);
# 2. the GM lap's intake line and swept line into data/ as the build will write them (predict_lines_0102.py);
# 3. the plans round 1 made on the swept line, re-made on the GM lap by their own tools, unchanged: the run-off pads
#    (runoff_pads.py --write, off the intake line it smooths itself), then the verge trees and the trunk colliders (both read
#    the pads as drivable, so after them);
# 4. the measured numbers into the docs (edit_config_0102.py --docs).
set -euo pipefail
NP="${NP:-python}"
MF=tracks/milford-road-course-lm
python -I "$MF/source/round2/edit_config_0102.py" "$MF/track.config.json"
python -I "$MF/source/round2/predict_lines_0102.py" | grep "^\[predict\]"
"$NP" -I "$MF/source/runoff/scripts/runoff_pads.py" --write --line "$MF/data/centerline.raw.local.json" | tail -1
"$NP" -I "$MF/source/vegetation/scripts/veg_naip_verge.py" "$MF" --write | grep "^\[verge\]"
"$NP" -I "$MF/source/vegetation/scripts/veg_trunks_reach.py" "$MF" --write \
  --line-doc "0.1.15's swept line (GM's loop: source/round2/predict_lines_0102.py, ledger 0102)" | grep "^\[reach\] \(REACH\|wrote\)"
python -I "$MF/source/round2/edit_config_0102.py" --docs "$MF/track.config.json"
