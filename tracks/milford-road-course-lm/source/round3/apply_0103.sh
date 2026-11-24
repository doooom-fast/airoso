#!/usr/bin/env bash
# Milford round 3 (ledger 0103): round 2's 0.1.15 -> 0.1.16, every step in order, from the repo root.
#   NP=<a python with numpy, scipy and PIL> bash tracks/milford-road-course-lm/source/round3/apply_0103.sh
# 1. the config edits (edit_config_0103.py: lm_intake.width_design, the whole lap; the edge_bulges report block);
# 2. the intake line and swept line into data/ as the build will write them (round 2's predict_lines_0102.py: the
#    intake now takes the width's bulges out);
# 3. the records that read the width, re-made by their own tools, unchanged: the run-off pads, then the verge trees and
#    the trunk colliders (both read the pads as drivable, so after them).
set -euo pipefail
NP="${NP:-python}"
MF=tracks/milford-road-course-lm
python -I "$MF/source/round3/edit_config_0103.py" "$MF/track.config.json"
python -I "$MF/source/round2/predict_lines_0102.py" | grep "^\[predict\]"
"$NP" -I "$MF/source/runoff/scripts/runoff_pads.py" --write --line "$MF/data/centerline.raw.local.json" | tail -1
"$NP" -I "$MF/source/vegetation/scripts/veg_naip_verge.py" "$MF" --write | grep "^\[verge\]"
"$NP" -I "$MF/source/vegetation/scripts/veg_trunks_reach.py" "$MF" --write \
  --line-doc "0.1.16's swept line (GM's loop, the width's bulges taken out: source/round2/predict_lines_0102.py, ledger 0103)" | grep "^\[reach\] \(REACH\|wrote\)"
