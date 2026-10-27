# P4 integration fix round — proofs (2026-10-26, ledger 0054 "P4 — dressing, integrated")

The four verification lenses refuted the merged branch's first rehearsal on the BUILT output (not on the gates, which
were all equal to v0.19.0's): trees on rock cut faces / walks / inside building footprints, the cut toes a sawtooth of
green teeth, buildings 0.3 % short of their true place with wall corners on a walk. Each was fixed at its cause
(never a gate loosened) and the full chain rehearsed again (`D:/k10-scratch/p4/integrate/`, run 2). What is here:

- `rock_faces.json` — run 2's rock report: the per-face slope rule as before plus the boundary clean-up measured
  (`boundary_smoothing`: grass / rock teeth before and after, per zone; `tongues_filled`; `patches_dropped`).
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
- `stills/` — day + night off run 2's gate OBJs (the toe of the Jackson 320–485 cut before / after, the walls, the
  trees, the buildings, the lamps, the signs, the maps); the full set stays in `D:/k10-scratch/p4/integrate/stills/`.
