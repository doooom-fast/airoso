---
id: 0006
title: Engine HEAD regresses rally terrain 630x vs v0.19.0 — do not converge pins onto it
status: diagnosed
scope: kind:rally_stage (measured); all kinds (suspected)
layer: engine
train: 01
---

## Symptom

Dragon Tail (gravel) builds far worse on the absorbed engine HEAD than on the tag it is pinned to.

## Evidence

Same track, same project data, same command (`./build.sh tracks/dragon-tail-gravel mesh`), only
`.engine/` moved. Measured 2026-07-25:

| `.engine` at | ground on top mid-lane | severe steps (>6 cm) | bumps /km |
|---|---|---|---|
| **`v0.19.0`** (rally's pin) | **10** | **243** | 113.15 |
| `3e1aa52` (absorbed HEAD) | **6314** | **2097** | 83.11 |

630× more terrain-over-road, 8.6× more severe steps. Both still FAIL the gate, but they are not the
same failure — at HEAD the road is buried across the stage rather than at its start cap.

The only commit between them touching terrain is **#18, "SD terrain: freeway cut-carve + loop
conform + honest wall-seating lens"** — SD-motivated work that was never gated against a rally
stage, because rally is pinned two tags back and nothing rebuilds the fleet on an engine change.

## Diagnosis

Not yet traced to a line — the bisect is one commit wide, so the next step is to read #18's terrain
changes against a point-to-point gravel stage rather than the SD freeway it was written for. The
likely candidate is the loop-conform path being applied where a stage does not close.

## Consequence — this blocks train 01

`fleet/MIGRATION.md` M6 and `STANDARDS.md` S3 both say to converge every repo onto one engine tag.
**Converging onto HEAD today would ship this to all fifteen tracks.** The pin disagreement that S3
flags as a fault is, right now, the only thing protecting the rally stages.

So: fix this *before* M6, and treat "the fleet is on one pin" as the goal it serves, not a thing to
do quickly. This is the first regression the control plane has caught, and it was caught by
rebuilding one track on two engines — which is the whole argument for the build matrix.

## Note on a rejected fix

A tangent-apron pass (grade terrain 40 m past each stage end, since `grade_embankment` has no road
samples beyond a non-loop centerline) was written and **reverted**. It ran — the aprons were built
and logged — and changed the measured outcome by **exactly zero** on both engine versions. So the
station-0 grass-over-road at `v0.19.0` is *not* caused by missing grading past the ribbon end, and
that hypothesis is closed. Worth knowing before someone tries it again.

## Verification

- Dragon Tail on the fixed HEAD reports ≤ 10 ground-on-top and ≤ 243 severe steps (parity with
  `v0.19.0`), on both gravel and tarmac.
- The SD freeway network still builds and passes whatever #18 was fixing — the regression fix must
  not simply undo it.
