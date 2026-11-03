---
id: 0068
title: High Plains post9 and post12 had no collider
status: fixed-awaiting-rebuild
scope: tracks/high-plains
layer: project
train: -
---

## Symptom

On the PC, a car drove straight through two High Plains blocks, post9 and post12. The other buildings were solid.

## Mechanism

`tools/author_bespoke_blend.py` `blocks()` writes a `1WALL_TILTUP_*` collider only when every 0.6 m sample of the footprint ring lies over ground polygons whose longest edge is at most `COLLIDER_TRI_M` (8 m, an `[invented]` rule from ledger 0062), within 60 m of the lap. post9 and post12 are 21 m from the lap, but the 1GRASS under them includes `1GRASS_ring` seating-fan slivers 12.3 m and 12.2 m long, so the footprint was refused a collider and `data/bespoke.report.json` recorded `"collider": false`. No gate looks for a missing collider, so `house_seat` and `drive_test` passed.

post10, post11 and the OSM blocks osm289311824 and osm289316523 also have no collider, by the 60 m reach rule (250 m, 250 m, 130 m, 134 m from the lap): see-through by design, unchanged.

## Fix

`blocks()` reads an optional `collider_tri_m` on a block group (default stays 8 m, so every other track's output is unchanged). `tracks/high-plains/track.config.json` sets 14 m on the `posts.json` group only. The rule that stays: no ground under a sample still refuses a collider.

## Proof

Bespoke step re-run on a scratch copy of `loop.blend` (Blender 5.1 here): post9 and post12 `collider` false to true, every other block, rail, pad, card and guardrail row identical. The collider foot of both, checked with `drive_test`'s own `TriField` seating test against the blend's 1GRASS/1ROAD triangles: 0 floating columns. `tests/tools/test_bespoke_collider_ground.py`.

## Owed

A High Plains rebuild on the PC to confirm `drive_test` floating furniture stays 0 against the real `track.obj`, then a drive through both posts. The 8 m rule was written before the collider's ground-following skirt (ledger 0062, 2026-11-01); it may be redundant now. Retiring it for Lake Murray and Sand Creek waits on a rebuild of each. The slivers may also change when the ledger 0067 terrain fix is rebuilt.
