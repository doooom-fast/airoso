---
id: 0009
title: Point-to-point stages bury their own start cap — terrain over the road where the car spawns
status: diagnosed
scope: kind:rally_stage — all four Rally Colorado stages
layer: engine
train: 01
---

## Symptom

Every rally stage fails `drive_test` on `soft_top_in_lane` — terrain sitting on top of the road in
the driving lane. It is the only thing blocking all four from packaging.

## Evidence

The samples are not scattered along the stage. **Every one is at station 0.0**, spanning the full
carriageway, all from a single grass mesh (Dragon Tail, `data/drive_test.json`):

```
[0.0, -2.85, '1GRASS_cr'] [0.0, -2.0, …] [0.0, -1.42, …] [0.0, -0.75, …]
[0.0, +0.75, …] [0.0, +1.42, …] [0.0, +2.0, …] [0.0, +2.85, …]
```

and the worst steps sit 2 m further in: `[2.0, -0.75, 0.838] [2.0, +0.75, 0.784] [2.0, +1.42, 0.760]`
— 0.7–0.84 m.

Counts: Dragon Tail 10, Under the Dragon 53. Everything else on these stages is within limits —
severe steps 8.0–9.6/km against a 12 limit, gravel bumps 113/km against 150.

`loop: false` puts the grid at the **start of the road** (L11). So the defect is precisely where
the car spawns: it starts under terrain, with a 0.8 m step 2 m ahead.

## It is NOT a terrain-resolution problem

Dragon Tail declares 8 m cells for a 6.5 m road, which violates L3b, so that looked like the cause.
Rebuilt at **5.7 m cells** (finer than the carriageway, 2.87 M verts, 7.06 GB peak):

| cells | soft_top | severe | bumps/km |
|---|---|---|---|
| 8.0 m | 10 | 243 | 113.15 |
| 5.7 m | **10** | **243** | **113.15** |

Byte-identical. The config's own note that x7 once OOM'd still roughly holds — it completes now but
costs 7 GB and buys nothing. **Left at its tuned 8.0 m / 1.6 M.**

## Also rejected

A tangent-apron pass (grade terrain 40 m past each stage end, since `grade_embankment` has no road
samples beyond a non-loop centerline) was written and reverted earlier: it ran, logged its aprons,
and changed the measured outcome by exactly zero. So the cause is not missing grading past the
ribbon end.

## Where to look next

The road ribbon's first cross-section and the terrain that meets it. Two candidates, both cheap to
distinguish:

1. **Real geometry** — the terrain genuinely covers the road's end cap, and
   `clamp_terrain_below_road` never pushes it down there because the cap is at the very edge of the
   road vertex set.
2. **A sampling artifact** — at exactly station 0.0 the first road triangle spans 0→3 m, so a
   barycentric lookup at the boundary can miss the road and hit grass beneath. That would make the
   0.8 m steps at station 2.0 the real defect and station 0.0 a false positive.

Distinguish by sampling the built `track.obj` at station 0.5 and 1.0: if the road surface is present
and above the grass there, it is (2).

## Verification

- `soft_top_in_lane` is 0 on all four stages.
- The car spawns on pavement and the first 5 m are step-free.
