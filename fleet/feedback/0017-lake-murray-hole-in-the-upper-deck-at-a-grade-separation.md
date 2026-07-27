---
id: 0017
title: Lake Murray — a connector roofs the mainline (first read as "a hole in the upper deck")
status: fixed in part (v0.49.0); lap seam still open
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


---

## CORRECTION — the first reading above is inverted

"A 6 m hole in Del Cerro Blvd" is wrong, and `drop_over_road` is not involved: it is only ever
applied to `barrier`, `kerb` and `shoulder`, never to a road mesh.

The trace is along the LOOP's own centerline. `1ROAD_del_cerro_blvd` being the top surface at
stations 3238–3247 and 3254+ means **the connector is lying over the mainline**. The six metres at
3248–3253 are not a hole in the connector — they are the only stretch where the loop's own deck is
still the top surface. The car is not falling through Del Cerro; it is driving on Del Cerro's roof
either side of a gap.

Measured deltas, each connector at its closest approach to the loop:

| connector | closest approach | Δy |
|---|---|---|
| **del_cerro_blvd** | **1.0 m** | **+2.51 m** |
| college_avenue_opp | 11.2 m | +5.01 m |
| navajo_road_opp | 11.2 m | +0.31 m |
| wisconsin | 15.0 m | −0.18 m |
| del_cerro_ave, airoso, adelante, colorado, connecticut | 44–137 m | +0.79 … +13.54 m |

A connector's Y is sampled from 3DEP along its OWN line with no knowledge of the mainline. The
ones that physically meet the loop must agree with it; the ones 44–137 m away are separate streets
at their own legitimate elevations and must not be touched.

## Fix (v0.49.0)

Snap a connector to the loop's height within 12 m, smoothstep back to its own profile over 45 m.
Result on Lake Murray: 4 of 9 connectors reconciled (college_avenue 7.40 m, del_cerro 3.54 m,
navajo 0.83 m, wisconsin 0.18 m), 5 untouched. **Severe steps 28 → 20, and the 2.55 m pair is
gone** — the worst junction step is now 0.35 m.

## Still open

1. **The lap seam.** Worst severe step is now **0.78 m at station 13476** on a 13478 m lap, and
   both remaining `soft_top` hits are at stations 0.0 and 13478.0 — the same physical point. The
   ribbon does not close cleanly. Note v0.45.0 fixed the *elevation* seam (a closed centerline
   repeats its first vertex and every wrap-around filter double-counted it); this is the *mesh*
   seam and is a separate defect. Check whether the sweep closes the ribbon or leaves the first and
   last cross-sections unjoined.
2. **Residual junction lip, 0.29–0.35 m** at 3237–3254. The 12 m snap radius levels the decks but
   the blend still leaves a step where the connector's own crossfall meets the mainline's.
