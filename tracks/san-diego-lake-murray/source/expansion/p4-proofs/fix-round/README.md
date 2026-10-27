# P4 integration fix round — proofs (2026-10-26, ledger 0054 "P4 — dressing, integrated")

The four verification lenses refuted the merged branch's first rehearsal on the BUILT output (not on the gates, which
were all equal to v0.19.0's): trees on rock cut faces / walks / inside building footprints, the cut toes a sawtooth of
green teeth, buildings 0.3 % short of their true place with wall corners on a walk. Each was fixed at its cause
(never a gate loosened) and the full chain rehearsed again (`D:/k10-scratch/p4/integrate/`, run 2). What is here:

- `rock_faces.json` — run 2's rock report: the per-face slope rule as before plus the boundary clean-up measured
  (`boundary_smoothing`: grass / rock teeth before and after, per zone; `tongues_filled`; `patches_dropped`).
- `treefx_rerun.log` — run 2's own post-check found ONE plant (a loop Sage) 6 mm inside a building ring: 4 mm clear in the plan, inside once `trees.txt` rounded it to centimetres. The guard now judges the spot as written; this log is the TreeFX step and its gate re-run in place on run 2's built OBJ (20,463 plants, post-check 0 / 0 / 0, G PASS).
- `lights_ini_check_run2.json` — 323 `[LIGHT_n]` for 323 lamps, 323 at their lens.
- `rock_test6.log` — the offline run of the new rock step on run 1's own pre-rock scene (the same input, the old rule
  vs the new side by side: 379 / 893 teeth → 100 / 137).
- `treefx.report.json` — run 2's planting record with `rejected_on_built_surface` (rock / road / walk / building) and
  the same for the loop's own zones.
- `post_trees_check.json` — every line of the WRITTEN trees.txt re-read against the gate OBJ with the planter's own
  guard: rock / walk / building must be 0.
- `trees_in_buildings_run2.json` — the view lens's own script (a ray down onto HOUSE / BUILDING) on run 2's file.
- `buildings_replay.txt` — the buildings pass replayed offline on run 1's inputs, old rule vs new (334 → 329; the
  corner-clearance histogram).
- `gates_run2.txt`, `diff_gates_run2.txt` — the gate extract in r3run's shape and every gate-JSON scalar that moved
  against `D:/k10-scratch/phase1/r3run/proj/data/` (explained in the ledger entry).
- `stills/` — `*_run1_before.png` (run 1) and `*_run2.*` (run 2, JPG): the toe of the Jackson 320–485 cut before /
  after, the walls, the Cowles cut, the trees, the buildings, two night views, three signs, the maps and CM
  outlines; the full set stays in `D:/k10-scratch/p4/integrate/stills/`.
- Run 3 (`D:/k10-scratch/p4/integrate/run3.sh`, the as-written guard in the chain, fresh copies): ended Tue Oct 27 00:27:34 MDT 2026; `run3_outputs/` beside it holds gates.txt, diff_gates_vs_v0190.txt, diff_gates_run2_vs_run3.txt, post_trees_check.json, trees_in_buildings_run3.json, the rock / trees / houses / lights reports; EXIT 1 on the same two reds, 0 Tracebacks; road kn5 94,174,420 B, +656 B vs run 2 (the ground thinning's run-to-run jitter, 14 vertices; every gate value equal; the other kn5s the same bytes); 20463 plants, post-check 0 / 0 / 0, in-footprint 0; gate JSONs moved vs run 2: `audit.json` (1 leaves); `audit.race_cw.json` (1 leaves); `audit.race_acw.json` (1 leaves); `verify_mouths.json` (1 leaves); `rib_check.json` (3 leaves); `house_seat_check.json` (1 leaves); `race_verify.json` (7 leaves); `terrain_thin.json` (121 leaves); `ground_release.report.json` (457 leaves).
  Copied here: `gates_run3.txt`, `diff_gates_run2_vs_run3.txt` (every gate-JSON scalar that moved between the two runs — the thinning's run-to-run jitter and the plan-stage plant count; the written trees.txt is byte-identical), `post_trees_check_run3.json`, `trees_in_buildings_run3.json`, `after3_run3.log` (the kn5 sizes run 2 vs run 3, the byte comparisons), `stills/jackson_toe_run3.jpg`, `stills/trees_waring_median_run3.jpg`.
