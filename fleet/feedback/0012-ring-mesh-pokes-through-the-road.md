---
id: 0012
title: 1GRASS_ring pokes through the road — the last blocker on Aspen and Grand Junction
status: diagnosed
scope: k10-colorado/aspen, k10-colorado/grand-junction
layer: engine
train: 01
---

## Symptom

Both tracks fail `drive_test` on `soft_top_in_lane`, and after the v0.27.0 skirt fix it is the
**only** thing failing them. Every hit comes from the same mesh:

| Track | hits | mesh | stations |
|---|---|---|---|
| aspen | 2 | `1GRASS_ring` | 1466 |
| grand-junction | 38 | `1GRASS_ring` | 472, 473, 476, 477, 688 |

Aspen's audit is otherwise clean on every check A–J; its only other issue is the same spot showing
as check B, a **+0.19 m** poke.

## What the ring is

`build_mesh` sweeps an annulus of grass columns beside the pavement (the "welded ring", `#17`). While
building each column it already clamps itself under the pavement — but only where it finds pavement
**directly under that column point** (`_pv17`). Where the road passes *between* column samples,
nothing clamps and the ring rides over the deck.

## Attempts, and what each proved

All reverted; recorded so they are not repeated.

1. **Sink ring vertices below the local road** (sampling `_road_tops` at each vertex and ±0.5 m).
   Fired on **zero** vertices for either track. So the ring's *vertices* are not above the road —
   its *faces* span over it between vertices.
2. **`drop_over_road(ring_mesh, …)`** — the existing helper, 7-point sampling (verts + edge midpoints
   + centroid), the same guard the warning barriers use. Grand Junction dropped 17 tris,
   38 → 32 hits. Aspen dropped **nothing**.
3. **Dense barycentric sampling** (a 4×4 grid over each face) added to that helper. Grand Junction
   dropped 20 tris, 32 → **27**. Aspen still dropped nothing and stayed at **2**.

So the direction is right for Grand Junction and simply does not see Aspen's case at all.

Two further observations that should shape the real fix:

- **Dropping triangles makes the surface worse.** Grand Junction's severe steps went **39 → 44** as
  tris were removed — holes leave edges the car reads as steps. Sinking or re-seating the ring is
  likely better than deleting it.
- Even at 27, Grand Junction still fails `severe_per_km` (~31 against a 12 limit), so the ring is
  not its only problem. Aspen, by contrast, is 2 hits away from passing everything.

## Where to look next

Why `drop_over_road` sees nothing on Aspen while `drive_test` sees 2 hits at station 1466 is the
crux — the same geometry, judged by two samplers, disagreeing. `_road_tops` reads the `road` mesh
built earlier in the function; `drive_test` reads `1ROAD_*` out of the finished `track.obj`. If a
later pass moves the deck (fold pads, flat zones, the lift), the ring is clamped against a road that
is no longer where it ends up. Compare the two surfaces at station 1466 before writing any more code.

## Verification

- `soft_top_in_lane` is 0 on both tracks.
- Grand Junction's severe steps do not rise as a side effect.
- Aspen packages (it has nothing else outstanding).
