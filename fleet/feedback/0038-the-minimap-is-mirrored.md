---
id: 0038
title: The HUD minimap does not track the car — it is drawn in the engine frame, the car moves in the kn5 frame
status: fixed
scope: engine (scripts/ac/track_folder.py map drawing) — every loop-path track; Lake Murray V3 patched in place
layer: engine
train: -
---

## Symptom (Kevin, seat, 2026-10-08, `san_diego_lake_murray_v3`)

> "the map is wrong. It doesn't seem to be tracking with the actual track or the car on it ...
> there's a chirality issue somewhere."

## Evidence

Objective test on the installed files (map.png sampled at the pixel AC computes for a known
world position, `pixel = (world + OFFSET) / SCALE_FACTOR`):

| point | car pixel (kn5 frame) → line alpha | north–south mirrored pixel → line alpha |
|---|---|---|
| AC_START_0 | (131, 549) → **0** | (131, 340) → 255 |
| vert 1500 | (35, 341) → **0** | (35, 548) → 255 |
| vert 3000 | (717, 306) → **0** | (717, 583) → 255 |

`track_folder.py:322` draws from `data/centerline.local.json` (engine frame, z = north) and
derives map.ini offsets from the same frame; AC positions the car in kn5 coordinates, where z is
mirrored (`scripts/modkit/kn5_to_gate_obj.py:8-10`). The July reference ships a byte-identical
map.ini — its map was wrong too (nobody had checked the map against the car). Same defect class
as the gate-centreline frame bug found earlier today (fleet/GATES-CHANGELOG.md): two frames, one
seam, nothing asserting which is which.

## Fix

`tools/make_map.py`: redraws map.png + data/map.ini from `data/finished_centerline.json` (the
kn5-frame line the prep writes) plus the connector pieces (z negated), with AC's exact
convention. Wired into `tools/ship_sd.sh` after the track-folder step; the installed V3 map was
patched in place (session restart picks it up). After: AC_START_0 pixel on-line alpha 255.
The engine's `track_folder.py` still draws mirrored for the loop path — fold `make_map`'s frame
handling into it when that module is next touched (it is the canonical emitter; this is a
loop-path seam, not a Blender-first exception).

## Verification

Kevin: the car dot sits on the line and moves with the track.
