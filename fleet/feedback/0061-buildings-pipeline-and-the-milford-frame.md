---
id: 0061
title: A buildings pipeline (footprints, class, measured height, form, skin, gate) and Milford's squashed frame
status: landed
scope: kind:* — every chain track; Lake Murray on rehearsal
layer: engine
train: -
---

## Symptom (Kevin, 2026-10-31)

> "Let's look into adding a pipeline for buildings" — then "Work as long as you need, we want quality work over speed."

The first bespoke batch stood buildings as flat grey boxes with one of three skins; Lake Murray's houses are the v021 assembler's
OSM boxes in Hamburg concrete; the chain tracks had no building step at all.

## Mechanism

Five stages with a file between each, every number naming its source (`.claude/skills/buildings/SKILL.md`):

1. **Footprints**: OSM `way["building"]`, or a trace off the NAIP (`data/buildings.traced.json`, the Mission Gorge apartments), or
   a hand-measured entry (the Nevada tents).
2. **`tools/plan_buildings.py`**: class from the tag, else by area per track; height from OSM `height`, OSM `building:levels`,
   the **shadow** on the NAIP, or the class default `[invented]`; form by class (hip 4:12, low gable, flat with a parapet, flat);
   skin by class and region (stucco / siding houses with a window per bay, tilt-up, metal; shingle or the NAIP's roof colour).
3. **`tools/author_bespoke_blend.py` `blocks`**: seated on the built ground, batched by skin under the tile cap, roofed by form on
   the footprint's oriented box, a collider only on the fine ground within 60 m of the lap, a far block past the built ground.
4. **Gates**: `house_seat`, `drive_test` (floating furniture, obstruction), `kn5_ground_check`.
5. **Stills**: `tools/bespoke_lap_stills_blend.py`, a driver's eye every sixth of the lap.

**What the shadow stage found, and refuses.** On a drawn photograph it recovers a box's height to 0.6 m
(`tests/tools/test_plan_buildings.py`). On the real ones: High Plains 2023 votes a 13:46 sun at 46 deg (self-consistent; 7
votes, no OSM heights to check it, so unused until `trust_unchecked` is set after the drawing is read); Sand Creek 2023 and
Nevada 2013 vote directions that only a 14–17 deg sun could cast, which NAIP never flies — the dark bands 2–3 m wide on every
west wall are the orthophoto's lean on tall buildings, not shadow. The stage now refuses a sun under 30 deg, checks itself
against OSM heights where five exist (shadow / OSM median within 0.6–1.6), and says in every row whether it was checked. Sand
Creek's 462 buildings therefore stand on 14 OSM heights and 448 class defaults, all marked.

**Milford's frame.** The 2026-10-28 trace read the USGS ImageServer export as the bbox it requested; the server answered with
square-degree pixels and a wider latitude extent (42.5605–42.5795), so every latitude was squashed by 0.737 about the frame's
centre. Laid over Planetary Computer tiles of the same scene the road missed by up to 190 m — what `route-notes.md` had put
down to OSM. OSM was right. `source/trace/unsquash_frame.py` (one run) puts the fixes back: lap 4.90 km (GM's 2.9 mi is 4.67),
and the rebuilt road sits within 0.21 m of the measured line. The rule for the skill: never take a request's corners as a
raster's; georeference from the raster.

## Evidence

- Installed 2026-10-31: Milford 0.3.0 (97bc0271), High Plains 0.69.0 (09f58bc5), Sand Creek 0.29.0 (39049824),
  Nevada Nights 0.5.0 (4c417509); every gate green on each (`fleet/DEFINITION-OF-DONE.md`).
- `tracks/<track>/source/bespoke/buildings.json` per track, each row with `_h`, `_class`, `_form`.
- `--debug` drawings were read for High Plains and Sand Creek before the refusals were written.
- Not yet driven. Lake Murray stays on the assembler path; the pipeline's rehearsal on its caches is the next step, Kevin's call
  after the stills.

## Open

- Microsoft's building footprints (ODbL) would fill OSM's holes (Waring's houses) without tracing; not fetched (a state file
  is hundreds of MB; Kevin's go).
- Roof form read off the photograph (a ridge shows as two tones) instead of by class.
- The Hamburg concrete on Sand Creek's `1WALL_barrier` and Nevada's `BARRIER_warning`; the LA Canyons asphalt everywhere.

## Lake Murray rehearsal (2026-11-01, not installed)

`SHIP_PROJ=D:/k10-scratch/lm_bespoke ENG=D:/k10-scratch/eng_rehearsal SD_BESPOKE=1 tools/ship_sd.sh --no-install`: the chain on a
scratch copy of the workshop, an engine-july scratch copy carrying the two pending files, and `scenery.bespoke.blocks` with
`replace: [HOUSE, BUILDING]` in place of the assembler's boxes. The planner read 19,931 footprints (14,450 houses, 2,635
commercial, 2,256 sheds, 472 industrial, 118 apartments; 408 heights from OSM, the rest class defaults); the author tool stood
689 — 554 on the physical ground within 450 m of the lap (the old loop and the north pieces), 135 as far blocks — and dropped
19,152 as past that reach.

What it took to get here, each now a rule in `tools/author_bespoke_blend.py`: the assembler names its ground TERRAIN / GRASS_FAR
and its road ROAD / CURB at the author stage (`scenery.bespoke.names`); engine-july's prep re-seats every `BUILDING*` ISLAND, so
the block is authored at the prep's floor (`prep_seats`) and the parapet shares the eave ring's vertices; a collider stands only
over ground triangles finer than 8 m, within 60 m of the lap, never over pavement — `drive_test` reads a column over anything
else as "floating 99" (31 columns on the College slope, then 2 on Mission Gorge's mouth fills).

Result: `house_seat` PASS (554 judged, contact -0.36..-0.07 m, 0 floating / sunken / buried), the road kn5 89.8 MB against
0.19.2's 94.4, every other gate line identical to 0.19.2 (the installed build), floating furniture 2 (two single columns of a collider on Mission Gorge at (-2633, 2106) and (-2172, 2171), "99" = nothing loaded under them; every column test so far has been that mechanism, this pair is not pinned down, 22 of the 554 near blocks carry a collider at all). The stills
(`tools/bespoke_lap_stills_blend.py` on the scratch split) show hip-roofed stucco houses with a window per bay, parapet commercial
blocks and tilt-up industrial beside the lap, and OSM's 11-storey apartment block at College as a 35 m slab. **Not installed:
Kevin's call after he sees them**; the installed 0.19.2 keeps the assembler's boxes.
