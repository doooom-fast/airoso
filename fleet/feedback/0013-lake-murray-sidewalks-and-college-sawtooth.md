---
id: 0013
title: Lake Murray — sidewalks run through the intersections, College Ave saws, medians too narrow
status: diagnosed
scope: k10-san-diego/project
layer: engine
train: 02
---

## Symptom (Kevin, from driving the v0.21.0 release)

> "The intersections of the network have sidewalks going through them so I'm not sure how the drive
> tests passed. Also on college ave there's a lot of sawtooth shapes on the edges where they should
> stay wide, also some of the turns got medians which is ok but they're very narrow now"

## Why no gate caught it — it never ran

San Diego's build path never invoked `drive_test` or `audit_mesh` (STANDARDS S8). Both read
`data/track.obj`, and the loop was built **Blender-first** — `loop.blend` → kn5, no OBJ ever
written — so the two geometry gates had nothing to read and were silently skipped. The shipped
v0.21.0 zip is that Blender-first build. **Nothing had ever looked at this track's geometry.**

Worse, the repo carried its own copy of 12 engine modules including `build_mesh.py`, `ribbon.py` and
`audit_mesh.py`, none of which had the inverted-skirt fix, audit check J, or per-track terrain
resolution. It was building from a fork that had gone stale.

Both are now fixed: the shadow tree is deleted and the loop builds through the engine's real
pipeline, which writes the OBJs and runs every gate. First honest result: drive_test **PASS**
(0 ground-on-top, 19 severe steps), audit 21 issues — B=3 pokes (worst 0.15 m), F=17 curb verts of
9,868, H=1 (0.36 m).

## 1. Sidewalks through the intersections

`build_loop_blend.py:658` sweeps **one continuous `curb_sidewalk` ribbon along the whole
centerline**, and `:677` sweeps another along every connector — "gives real sidewalks the WHOLE loop
(not just the sparse OSM footways)". Nothing breaks either sweep at a junction, so the loop's
sidewalk runs straight through every intersection and each connector's sidewalk crosses it.

That is the same defect class as [0001](0001-junction-flare-drags-the-sidewalks.md) but a different
mechanism: 0001 is a width flare dragging the edge outward, this is a sweep that never stops. The
fix is the same shape — **gap the sidewalk across a junction mouth** (and per 0001, a barrier
belongs there for an off-route crossing, not pavement).

## 2. College Ave sawtooth — confirmed, and violent

Measured from `centerline.local.json`: **105 vertex-to-vertex width jumps over 1 m** on a 13.46 km
loop whose widths run 9.00–30.00 m (median 17.00).

```
station 2286 m: 22.5 -> 24.0
station 2289 m: 24.0 ->  9.0     <-- 15 m collapse across one 3 m step
station 2307 m:  9.0 -> 30.0     <-- 21 m jump
station 2331 m: 30.0 ->  9.0
station 2355 m:  9.0 -> 24.1
```

The width is flipping between `route.split_width_m` (**9.0**, one carriageway) and junction/full
widths (24–30 m) from one vertex to the next. Swept into a ribbon, that is exactly a sawtooth edge.
Whatever assigns per-vertex width where a split carriageway meets a junction is switching
instantaneously instead of transitioning — and on a divided road it should simply stay wide.

## 3. Medians too narrow

`route.split_width_m` is **9.0 m** — the width of each carriageway once split, which sets how much
room is left between them. Kevin's read from the car is that the resulting median is too tight. This
is a config value, not a defect, so it can be tuned directly once 2 is fixed (the sawtooth makes the
median width read inconsistently anyway).

## Verification

- No sidewalk geometry inside a junction mouth on the Lake Murray loop.
- No width jump over ~1 m between adjacent centerline vertices; College Ave stays wide through its
  divided section.
- Kevin drives it and the edges read straight.
