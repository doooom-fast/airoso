---
id: 0017
title: Lake Murray — a 6 m hole in the upper deck where two roads cross
status: diagnosed
scope: k10-san-diego/project (Lake Murray loop)
layer: engine
train: 02
---

## How it surfaced

Porting the loop off the Blender-first kn5 to the native OBJ→kn5 writer (`KN5_WRITER=native`,
task #16). The port itself worked — 73 OBJ groups → 73 meshes, `verify_kn5` PASS, and the
100%-no-OBJ-counterpart fidelity failure disappeared because the kn5 *is* the audited geometry now.
Then the OBJ geometry got measured for the first time and it is not seated: p95 float **1.644 m**
over 93.5% of samples, and 28 severe steps with a worst of **2.552 m**.

Corridor refinement (8 m cells, ×4 → 2 m sub-cells, ledger 0014) took the float down and left the
steps. Those are a different defect.

## The defect

Wheel path at −0.75 m lateral, stations 3238–3261, sampling the top drivable surface:

```
3247  y 40.943  1ROAD_del_cerro_blvd
3248  y 38.822  1ROAD_main             dh -2.121
3249  y 38.822  1ROAD_main
3250  y 38.822  1ROAD_main
3251  y 39.002  1ROAD_main
3252  y 39.002  1ROAD_main
3253  y 39.002  1ROAD_main
3254  y 41.620  1ROAD_del_cerro_blvd   dh +2.618
```

The centerline here IS Del Cerro Blvd. For **six metres** its ribbon has no surface at all, and the
only thing under the wheel is `1ROAD_main` 2.1 m below. The car falls through the deck at a grade
separation and climbs back out the far side.

Not an elevation-profile problem: `centerline.elevation.json` is smooth through the window
(141.51 → 141.60 → 141.96 raw, matching smoothed). Not stacked-surface confusion either — at
station 3250 there is exactly ONE road surface present, the lower one. The upper ribbon is simply
missing there.

`bridge.spans.auto.json` is `[]` and `flat_zones.json` is empty, so neither the bridge detector nor
the junction-pad logic is involved.

## Where to look

A pass that removes upper-ribbon triangles where another road passes beneath — the same shape as
`drop_over_road`, which legitimately drops GRASS/KERB triangles that sit over pavement. Applied to
a road-over-road crossing it punches a hole in the flyover instead of the thing it was aimed at.
Check every `drop_over_road` call and any ramp/junction trim for a road-vs-road case, and confirm
whether Del Cerro genuinely crosses the loop at a 2.1 m separation (real grade separation → the
upper deck must be continuous and the lower one passes under) or whether the 2.1 m is itself wrong
(at-grade junction → both should merge to one sheet, which is what flat zones exist for).

## Why no gate caught it before

The loop shipped a Blender-first kn5: `scripts/build_kn5.sh` preps `loop.blend` and exports that,
so `drive_test`/`audit_mesh` measured `track.obj` while the driver loaded the blend, where the
geometry had been seated by hand. Two different geometries, and the hole lived only in the one the
gates measured but nobody drove. It is exactly the "gates green, game broken" gap
`scripts/ac/kn5_write.py` was written to close.

## Verification

- No station on any wheel path drops onto a lower road surface and climbs back.
- `drive_test` severe steps fall from 28 with the 2.5 m pair gone.
- Lake Murray's kn5 is written by `kn5_write` (fidelity 0.00 m by construction), not from a blend.
