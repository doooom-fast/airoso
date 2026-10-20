#!/usr/bin/env bash
# the ship_sd.sh gate stage after verify_mouths, run by hand on the rehearsal project (same commands, same order)
export PYTHONUTF8=1
A=C:/Users/Owner/Documents/GitHub/airoso/.claude/worktrees/wf_c6ab4b42-146-1
P=C:/Users/Owner/AppData/Local/Temp/claude/C--Users-Owner-Documents-GitHub-airoso/59395b0b-e098-4e22-9ea8-1346efc0cf70/scratchpad/exp/p1/project
SLUG=san_diego_lake_murray
cd "$A"
echo "=== rib_check"; python tools/rib_check.py "$P" --json "$P/data/rib_check.json" | tail -3; echo "rc $?"
echo "=== house_seat_check"; python tools/house_seat_check.py "$P" --json "$P/data/house_seat_check.json" | tail -3
echo "=== drive_test street"; python -m scripts.geometry.drive_test "$P" --layout street 2>&1 | grep -v "drive-time\] sweep" | tail -30
echo "=== audit street"; python -m scripts.geometry.audit_mesh "$P" 2>&1 | tail -16
for lid in race_cw race_acw; do
  echo "=== $lid gate OBJ"; python -m scripts.modkit.kn5_to_gate_obj "$P" --kn5 "$P/build/$SLUG.kn5" --kn5 "$P/build/${SLUG}_race.kn5" --kn5 "$P/build/${SLUG}_closure_$lid.kn5" --out "$P/data/track.$lid.obj" | tail -1
  echo "=== drive_test $lid"; python -m scripts.geometry.drive_test "$P" --layout "$lid" 2>&1 | grep -v "drive-time\] sweep" | tail -40
  echo "=== audit $lid"; python -m scripts.geometry.audit_mesh "$P" --layout "$lid" 2>&1 | tail -18
  echo "=== no_route $lid"; python tools/no_route.py "$P" --layout "$lid" 2>&1 | tail -6
done
echo "=== verify_fold_fans"; rm -f "$P/data/verify_fold_fans.json"; python tools/verify_fold_fans.py "$P" 2>&1 | tail -16
echo DONE
