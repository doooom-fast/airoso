---
id: 0003
title: Switchbacks are built dead flat — real roads are crowned and superelevated
status: open
scope: kind:street_port, kind:rally_stage, kind:fictional_street_circuit
layer: standard
train: 01
---

## Symptom

> "realistic banking on switchbacks"

A hairpin on a real mountain road leans into the corner. Ours is flat, so it drives like a
featureless arc and the car has no cue about the corner's severity.

## Evidence and the standards conflict

This one needs a law amended before any code changes, which is why `layer: standard`.

`LAWS.md` L10 currently says, carried over verbatim from `k10-colorado`'s notes:

> Public streets are not superelevated — they get real elevation only.

That is **too strong, and it is why the switchbacks are flat.** It was written to prevent a real
failure — inventing racetrack banking on suburban streets, which looks absurd and drives worse — and
for a suburban grid it is correct. But it over-generalises:

- Roads are **crowned**: a normal 2-lane road has ~2% cross-slope each way from the centerline, for
  drainage. Ours are perfectly flat, which is already wrong on every straight.
- Curves **are** superelevated, by design standard, as a function of radius and design speed. A
  mountain switchback is the *most* superelevated thing on a public road, not the least — that is
  what makes it drivable at all in winter.

So the honest rule is not "no banking on streets" but "**no *racetrack* banking on streets; real
roads get the cross-slope a road engineer would have built**".

Existing machinery, for reference: the `track-grading` skill derives banking from the racing line's
own curvature, and is deliberately scoped to purpose-built circuits only — correctly, since a
racing line's curvature is not a road's design radius.

## Fix

1. **Amend L10** to distinguish racetrack banking (researched per circuit; road courses get none)
   from road cross-slope (crown + superelevation, engineered, applies to every real road).
2. Add a cross-slope pass for `real_road` / `street_circuit`:
   - **Crown** on tangents and gentle curves: configurable, ~2% default, from the centerline out.
   - **Superelevation** in curves, from the curve radius and a design speed, transitioning through
     the same spiral length a road design would use. Cap it well below racetrack values — a public
     road tops out around 6–8%, not 10°.
   - **Transitions matter more than peaks.** An abrupt roll-in is felt as a jolt; the runout length
     is what makes it read as a road.
3. Superelevation must compose with `0002`'s vertical profile and with the edge sweep — the curb
   sits on the banked edge, not on a flat one (`ribbon.curb_sidewalk` already takes a `bank_at`
   argument, so the seam exists).
4. Rally stages: gravel roads are superelevated too, but crudely and inconsistently. Worth a
   deliberately looser, noisier treatment rather than the clean highway model.

## Scope

`lookout-lariat` is the proof case — a 25 km mountain loop that is nothing but switchbacks. Then the
rally stages (canyon and mesa shelf roads), then `sand-creek` (flat, urban: crown only, near-zero
superelevation — the regression case that proves the model does not over-apply).

Circuits are explicitly **out of scope**: they already have researched banking per L10 and must not
be touched by this pass.

## Verification

- Cross-slope on a straight reads ~2% each side of the crown, both directions.
- On `lookout-lariat`, superelevation correlates with measured curve radius and never exceeds the
  configured road maximum.
- Curb and sidewalk sit flush on the banked edge — no lip opening up on the outside of a corner
  (`audit_mesh` curb-flush check clean).
- Kevin drives a switchback and it leans the way the real one does.
