---
id: 0021
title: Every track ships ONE grid slot — a race forms "in the pits"
status: diagnosed
scope: all kinds
layer: engine
train: R3
---

## Symptom (Kevin, first Race attempt on the restored Lake Murray, 2026-08-06)

> "you mixed up pitbox and grid somehow"

## Evidence (kn5 dummy probe, same day)

| installed track | AC_START_* | AC_PIT_* |
|---|---|---|
| san_diego_lake_murray | **1** (coincident with AC_HOTLAP_START_0) | 8 |
| imi_motorsports | **1** | 4 |
| pueblo_motorsports_park | **1** | 4 |

`scripts/geometry/dummies.py` emitted exactly one `AC_START_0` (at the hotlap point) and staggered
the pit boxes **forward up the start straight on the racing line** (no pit lane is modeled). In a
Race, AC places car 1 on the only grid slot and every other car falls back to a pit box — so the
whole field forms on the start straight in the pit cluster. From the driver's seat: pitbox and
grid, mixed up.

Never seen before today because Race mode was unreachable on every k10 track: no AI line existed
(R2 closed that) and the `circuit` ui tag was missing (fixed engine-side the same day). Two
blockers fell and the third stood up behind them.

## Fix (landed with this entry)

`dummies.py` now emits `AC_START_1..n_pits-1` as two staggered columns *behind* pole — 5.5 m per
slot, ±30% of a half-lane, on-road placement (the verge drops cars — same rule the pits learned),
wrap-safe on loops and clamp-safe on stages.

Reaches an installed track only via re-export (dummies live in the kn5), so it rides the **R3
Lake Murray pilot export** rather than shipping alone. Until then Track Day (pit spawns) is the
working AI mode on current installs.

## Verification

- kn5 dummy probe on the next export: `AC_START_0..N-1` present, none coincident with a pit box,
  all on the road surface (`verify_kn5` spawn check stays green).
- Kevin starts a Race with a full field and the grid forms as a grid, behind the line, in game.
