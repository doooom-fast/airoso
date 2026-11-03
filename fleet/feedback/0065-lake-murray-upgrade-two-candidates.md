---
id: 0065
title: Lake Murray's upgrade, two candidates side by side
status: in-progress
scope: tracks/san-diego-lake-murray
layer: project
train: -
---

## Symptom (Kevin, 2026-11-01)

> "Let's get Lake Murray started on an upgrade against all the other changes."

> "do both as separate versions"

0.19.2 stays installed and untouched, as do the repo's `loop.blend` and `tools/ship_sd.sh`, until Kevin picks a winner in the seat. 0.19.3 stays built and held.

## v4, keep the roads: 0.20.0, installed as `san_diego_lake_murray_v4`, not driven yet

Branch `claude/lm-v4`, worktree `D:/k10-worktrees/lm-v4`, project `D:/k10-scratch/lm_v4`. Road kn5 55f2026c, 107.1 MB against 94.4.

Airoso's prep is not a drop-in for Lake Murray. Against 0.19.3's road kn5 it took 14,356 of 85,741 sidewalk positions (its rule against kerb faces in a carriageway), emptied a race
kerb so the exporter refused the race kn5, and moved the ground and every house and lamp (no T-junction weld, no kept-terrain refine, no house seat). So v4 is the general chain with the
prep the approved roads were built with, from rehearsal 2's blend (ledger 0062). Moving to airoso's prep belongs to v5.

| Gate | 0.19.2 | v4 |
|---|---|---|
| soft top in lane, street / cw / acw | 8 / 8 / 4 | 0 / 0 / 0 |
| audit, each layout | 53 | 0 |
| race drive_test | FAIL | PASS |
| severe steps | 0 / 4 / 6 | 0 / 4 / 6 (not gating at that rate; worst 0.106 m at 11-12 m lateral) |
| street excursion drops, limit 13 | 96 | **96: forced** |

The repairs (`tools/red_repairs.py` names them off the built OBJ, `tools/red_repairs_blend.py` applies them on the prepped scene): 63 sidewalk faces removed at the Del Cerro mouths and near
(112, -1476); 401 ground vertices lowered, at most 0.172 m, at two places on the lap around s 2175 and 2250.

**The bypass.** `--force-install` over the street layout's excursion drops alone, Kevin's word: "Force". Recorded in `fleet/GATES-CHANGELOG.md`. The red is mostly the sidewalk's outer bevel, a
28 % slope that falls 0.14 m per the sweep's 0.5 m sample against the 0.12 m limit; a real one stands at s 2100, -13 m lateral (1.52 m). A gentler bevel (the low edge 0.30 m further out) put
ground over the kerb in 3,465 places (verify_kn5 TERRAIN POKE) and came out.

Owed: Microsoft footprints' ODbL attribution before any release. 7,600 blocks may cost load time or frame rate; only the seat can say.

## v5, redraft the roads: 0.21.0, `claude/lm-v5`, `D:/k10-scratch/lm_v5`, not built past the draft

The underlay only empties `GEN_*`, and Lake Murray's blend has none, so a redraft has to remove the v021 layers itself. The engine's OSM stitch does not reproduce the track: 22.5 km against
13.5, another origin, 690 of 4,499 authored points with no draft line within 150 m. From the authored loop as `source.type: from_track` with the origin pinned: 13,484 m, plan offset median
2.57 / p95 4.89 / max 5.93 m, height median 0.12 / p95 1.1 / max 8.65 m. Everything keyed to the current line must move with it.

The bare mainline's first gates are red, as expected with none of the authoring: severe steps up to 0.43 m around s 2254, ground on top around s 1782-1904, a 3.64 m gated drop at s 2102, audit 6 (walls on the road).

Estimate: 3-5 days of runs, because the authoring tools expect the v021 ribbon.

## v5-bare: 0.21.0 installed 2026-11-03 as `san_diego_lake_murray_v5`, the street layout alone, forced on one gate (not driven yet)

Kevin: "Continue v5 now", then "Yes, v5-bare early", then "yes" to forcing the 18. Branch `claude/lm-v5`, project `D:/k10-scratch/lm_v5`. Road kn5
645002e6151a7f648a9d4bc551f9c582. No sidewalks, no bridge rails, no buildings, no race layouts: the engine's road and ground on the approved line.

What it took (each kept, each opt-in so no other track moves):
- **The line and heights are the approved ones.** `source.type: from_track` on the authored loop, `smooth_window` 0, the origin pinned; the fixes carry
  `ele` and `tools/profile_from_fixes.py` (draft step `profile`) puts the approved profile on the projected line, decks held, Kevin's College hump
  kept. My first conversion used a spherical Earth and put the line 4.4 m off; the engine projects on the ellipsoid.
- **The levelled fold pinch in the engine** (`ribbon.fold_level_deltas`, `route.fold_treatment: "pinch"`): ledger 0050's rule. At the four
  junction corners a 24-30 m road turns on 8-10 m; the engine's plateau and flat disc would have flattened the College hump (ledger 0057) and
  left a 0.33 m rim. Severe steps 18 -> 0, kinks 10.99 -> 2.52 /km.
- **`scenery.warning_barriers` / `fences` / `parapets: false`**: a real street's barriers are the ones it has, authored later.
- **The corridor splice read the wrong side of the road** (ledger 0067): 110 double-sheet cells -> 0.
- **The sidewalk edge's contact pass** read the sidewalk's 6-point rows with the shoulder's 4-point stride (fixed). The engine's sidewalk still
  stands up to 1.7 m over Lake Murray's falling yards (281 excursion drops), so v5-bare runs the shoulder edge; sidewalks come as authoring.

| street gate | 0.19.2 | v5-bare |
|---|---|---|
| soft top in lane | 8 | 0 |
| severe steps | 0 | 0 |
| kinks /km | 2.67 | 2.52 |
| fold bumps | 20 | 18 |
| excursion drops, limit 13 | 96 | **18: forced** |
| audit | 53 | CLEAN |
| kn5_ground_check | PASS | PASS |

Owed before v5 can be judged against v4: sidewalks, bridge rails, the race layouts on the new line, buildings, trees, lamps, signs.
