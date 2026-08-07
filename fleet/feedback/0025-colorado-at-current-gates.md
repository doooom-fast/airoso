---
id: 0025
title: Colorado at current gates — two clean laps blocked at the runoff edge, two on surface roughness
status: diagnosed
scope: k10-colorado/imi, pueblo, high-plains, lookout-lariat
layer: engine
train: R4
---

## Context

First rebuild of the four installed Colorado tracks on a modern engine (v0.63.0, from v0.16-era
installs), 2026-08-07. All four builds were **stopped by `drive_test`** — the gates doing their
job against standards that didn't exist when these tracks last built. The installs in AC remain
the old artifacts (driveable; now at least `circuit`-tagged so Race/Track Day appear).

## The matrix (drive_test on the v0.63.0 builds)

| track | lap | soft-top | severe | kinks/km | excursion drops | far ledges | verdict class |
|---|---|---|---|---|---|---|---|
| imi | 1,441 m | 0 | **0** | 9.7 | **30** | 0 | clean lap, runoff edge only |
| pueblo | 3,451 m | 0 | **0** | 9.0 | **118** | 2 | clean lap, runoff edge only |
| high-plains | 3,102 m | 0 | 30 | 37.1 | 96 | 0 | runoff + 0018-class roughness |
| lookout-lariat | 24,803 m | 0 | 251 | 68.3 | 690 | 378 | roughness + edge (hogback legacy) |

IMI and Pueblo drive **perfectly clean laps** — zero severe steps, zero ground-through-road — and
fail exclusively on `excursion_drops` (ground falling >20 cm just beyond the pavement).

## Hypotheses

1. **KILLED: terrain cell size.** Declared `terrain_cell_m` 1.25 (imi) / 2.0 (pueblo) +
   `corridor_refine_factor` 6 per L3b; rebuilt; drops effectively unchanged (28→30, 128→118).
   The declarations are kept (L3b hygiene) but they are not this mechanism.
2. **KILLED: no archetype declared.** Checked same day — imi and pueblo already declare
   `race_circuit` (S6's "ten tracks undeclared" note predates these configs). The runoff preset
   applies; the defect is downstream of it.
3. **DIAGNOSED, primary: the apron's outer seam.** `worst_excursions` cluster at lateral
   ±9.5–10 m on a ~9.8 m road — **~4–5 m beyond the pavement edge, 0.26–0.4 m steps** — the
   built runoff/shoulder apron ends against the raw terrain grid without a feather, exactly the
   road-grounding drape class. Assigned to the geometry surgeon (2026-08-07 pm): feather the
   outer hem in `build_mesh.py`, prove on imi + pueblo (excursion_drops → 0, no regressions).
4. high-plains / lookout-lariat additionally carry the 0018 roughness class (mechanism still
   open) — they ride 0018's resolution plus hypothesis 3's fix.

## Verification

- imi + pueblo rebuild PASS drive_test after the archetype declaration (or hypothesis 2 joins 1
  in the killed list with numbers).
- The passing builds install with grid/AI/cameras and Kevin drives one.
