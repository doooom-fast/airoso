---
id: 0011
title: Degenerate 500 m terrain triangles span the map and cross over the road
status: diagnosed
scope: k10-colorado/aspen (measured); any track whose 1GRASS is split into chunks
layer: engine
train: 01
---

## Symptom

Aspen fails `drive_test` with **1,037** `soft_top_in_lane` hits — terrain on top of the road —
clustered from station 403 onward, all on the right-hand side (lateral +2.25 to +4.10).

## Evidence

At station 406, lateral +3.25, the surfaces stacked at that single point are:

```
   y =   6.27   1GRASS_g      <-- 2.1 m ABOVE the road
   y =   4.17   1ROAD_main
   y =   4.15   1GRASS_f      <-- the correct conformed sheet, 2 cm under the deck
   y = -25.14   1GRASS_g      <-- 29 m BELOW
```

So the terrain is correct (`1GRASS_f` sits 2 cm under the deck exactly as designed) and a **second**
mesh, `1GRASS_g`, contributes surfaces both far above and far below it. Inspecting the two
`1GRASS_g` triangles that cover that point:

| vertical span | longest horizontal edge |
|---|---|
| −28.16 … **+18.59** m (46.75 m) | **500.0 m** |
| −28.16 … −6.21 m (21.95 m) | **500.0 m** |

Aspen's terrain grid is 379×541 at 1.5 m cells — about **568 × 811 m total**. A triangle with a
500 m edge therefore spans *half the map*, and it is not a grid triangle: grid triangles are 1.5 m.

## Diagnosis

These are **degenerate triangles**, almost certainly a row/column wraparound introduced when
`1GRASS` is split into named chunks (`1GRASS_a` … `1GRASS_g`): a triangle that references vertices
from opposite ends of a row stretches straight across the terrain. Two of them happen to pass over
the road between stations 403 and 430, which is what `drive_test` reports.

This is not a terrain-conform problem, and no amount of grading or finer cells will fix it — which
explains why declaring `terrain_cell_m: 1.5` on Aspen changed the count barely at all (1063 → 1037).

It is also a **collision hazard, not just a visual one**: `1GRASS_*` is `1`-prefixed, so AC gives it
physics. A 500 m triangle hanging 2 m over the road is something the car hits.

## Why the audit did not catch it

`audit_mesh` check B (terrain poking through road) compares grass VERTICES against nearby road
vertices. A degenerate triangle's vertices are hundreds of metres away — outside every proximity
window — while its *surface* passes right over the pavement. Only `drive_test`, which samples the
triangle surface along wheel paths, sees it. Same structural blindness as the curb-flush case: a
vertex test cannot see a triangle that spans.

## Fix

1. Find where the chunk split can emit a triangle whose vertices are not grid-adjacent
   (`split_mesh_under_cap` and the grass chunking in `build_mesh`), and stop it.
2. Add a guard that is cheap and catches the whole class: **reject any `1GRASS` triangle whose
   longest horizontal edge exceeds a few grid cells**. On a 1.5 m grid nothing legitimate is 500 m
   wide, and the guard needs no proximity reasoning.
3. Consider the same check in `audit_mesh` as a new class — "terrain triangle spanning further than
   N cells" — so a vertex-based audit stops being blind to it.

## Verification

- No `1GRASS` triangle has a horizontal edge longer than a few grid cells on any track.
- Aspen's `soft_top_in_lane` goes to 0 without changing its terrain resolution.
- Aspen packages.
