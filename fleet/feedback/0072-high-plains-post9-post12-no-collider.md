---
id: 0072
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

## Built 2026-11-03: High Plains 0.72.1 installed on the PC (not driven)

On the installed 0.72.0 (the ledger 0067 rebuild, PR 18), `tools/ship_track.sh high-plains --from bespoke`: every gate green,
no force. `bespoke.report.json`: post9 and post12 `collider` true (both false in 0.72.0), every other block as it was;
post10 and post11 stay false as in 0.72.0 (ground at -0.4 and -3.3 m, a different place). `drive_test` floating
furniture 0; severe 0, kinks 7.77 /km, steps 1.24 /km, fold bumps 0, equal to 0.72.0. In the kn5, the merged collider
mesh `1WALL_TILTUP_0` (544 -> 578 verts) carries 16 verts inside post9's footprint and 18 inside post12's, where 0.72.0's
carried none; post4, the control, 16 in both. kn5 md5 `ceacafc7d1f9b8281a970fc3ca739e0e`; 0.72.0
(`c798d5dfd44dcb9386e1a7e4cbb4b400`) parked in `D:/k10-track-archive/2026-11-03_131424/`. Owed: the drive through both posts.
