---
id: 0062
title: A buildings pipeline (footprints, class, measured height, form, skin, gate) and Milford's squashed frame
status: landed
scope: kind:* — every chain track; Lake Murray on rehearsal
layer: engine
train: -
---

> *Renumbered from 0061 when the branch landed on main, 2026-11-01: main had already filed its own 0061 (the paved-hillside
> edges). Commits `82f653c` and `51a525c` say "ledger 0061" in their messages and mean this entry.*

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
0.19.2's 94.4, every other gate line identical to 0.19.2 (the installed build), floating furniture 2 (two single columns of a collider on Mission Gorge at (-2633, 2106) and (-2172, 2171), "99" = nothing found under them; pinned the same day, see the second rehearsal below: the collider's one flat foot at the footprint's lowest ground stood 2.9 m under the grass at the high corner of a sloped lot; 22 of the 554 near blocks carried a collider at all). The stills
(`tools/bespoke_lap_stills_blend.py` on the scratch split) show hip-roofed stucco houses with a window per bay, parapet commercial
blocks and tilt-up industrial beside the lap, and OSM's 11-storey apartment block at College as a 35 m slab. **Not installed:
Kevin's call after he sees them**; the installed 0.19.2 keeps the assembler's boxes.

## Lake Murray rehearsal 2 (2026-11-01, not installed): Microsoft's footprints, the collider skirt

Two things the first rehearsal left open, each measured before it was built.

**The two floating columns.** `drive_test` keys every `1WALL` vertex by 0.6 m cell, takes the LOWEST vertex in the cell, and looks
for a drivable surface within 2.5 m of it (`top_at`'s ±2.5 m window). A block's collider had one flat foot at the footprint's
lowest ground less 0.15 m; on a sloped lot the high corner's ground stood 2.9 m above that foot (the built OBJ at (−2633.5,
2105.7): `1WALL_TILTUP_0` from −48.44, `1GRASS_5` at −46.2..−44.9), outside the window — "99", floating. The 2 m rule meant to
refuse that compared the ground with the walls' bottom (the prep's floor), not the collider's. The collider is a skirt now:
`ring_points` every `COLLIDER_STEP_M` 3 m `[invented]`, each vertex `BOTTOM_UNDER_M` under its own ground; `COLLIDER_GROUND_M` is
gone. Floating furniture 0 on every layout, 275 colliders where the first rehearsal stood 22.

**The houses OSM lacks.** Microsoft GlobalMLBuildingFootprints (ODbL): `tools/msft_footprints.py --find` names the level-9
quadkey tile over `source/naip_box.json` (`023013221`, 77.9 MB, 698,177 rows); `source/bespoke/msft_buildings.json` is the
12,035 inside the box, 11,573 with the dataset's ML height. The self-check before trusting it: 10,549 stand where OSM has
nothing and 19,153 of OSM's 20,649 have no Microsoft polygon — the two sets are nearly disjoint, the houses OSM lacks, not OSM's
houses shifted (the overlay on the NAIP: OSM holds the commercial blocks and a few tracts, Microsoft the rest; of the 1,850 OSM
footprints with a Microsoft centroid within 40 m, 902 are within 3 m, median offset −0.8 / 0.1 m). Its heights against OSM's:
4.3 / 5.6 / 8.9 m at 1 / 2 / 3 `building:levels` (n 5 / 7 / 6), 23.7 m at 11 (the College slab). `tools/plan_buildings.py` reads
its sources in order of trust and drops a later footprint whose centroid lies inside an earlier one (1,489 Microsoft on OSM, 19
OSM on OSM), offering its height where the earlier has none (1,345 OSM houses took one); an untagged footprint that area alone
would class commercial or industrial is a house when a known height puts it under 7.5 m and it is under 1,000 m²
(`HOUSE_MAX_H_M`, `HOUSE_MAX_AREA_M2` `[invented]`: 1,225 of them, median 411 m², 6.6 m to the ridge). 30,240 planned (24,499
houses, 2,507 commercial, 2,583 sheds, 533 industrial, 118 apartments; heights: 11,259 Microsoft, 398 OSM levels, 9 OSM height,
18,574 class defaults `[invented]`). The shadow stage, with 996 known heights to check against now, read 0.59 of them and
switched itself off.

**The chain** (`SHIP_PROJ=D:/k10-scratch/lm_bespoke ENG=D:/k10-scratch/eng_rehearsal SD_BESPOKE=1 tools/ship_sd.sh --no-install`):
7,600 blocks stood (6,922 Microsoft's; 1,361 far blocks; 275 colliders), 21,452 dropped as past 450 m of the lap, 1,188 refused
for cause (the tool printed twelve: 7 relief over 2.5 m, 3 within 3 m of a road or wall, 2 on a road; it tallies every reason
from now on). `house_seat` PASS: 6,239 judged, contact −0.39..−0.05 m, 0 without ground, 1,003 buried more than 30 % on the
uphill side (the prep's floor rule, `PREP_SHOW` 0.5: a hillside house shows half its height on the high side), the least showing
1.05 m (a shed). `drive_test`: every key of every layout identical to the installed 0.19.2's committed file, floating furniture
0 (was 2). `audit_mesh`: wall verts 152,578 → 187,018 (the skirts), skirt-off-terrain 1,564 → 1,563. `kn5_ground_check` PASS:
wall objects 49 → 312, wall seating median −0.50 → −0.62 m (the colliders' feet). Road kn5 110.1 MB against 0.19.2's 94.4 and
the first rehearsal's 89.8. The stills (`tools/bespoke_lap_stills_blend.py`, six stations and the top) went to Kevin with this
entry; they are not in the repo.

**Open:** the hillside houses refused for relief over 2.5 m (`MAX_RELIEF_M`) — the real San Carlos houses on those lots are
split-level; a stepped foundation would stand them. The ODbL attribution for Microsoft's footprints is owed in the track's
credits before any release of a build carrying them (`assets/licenses.json`'s shared list credits every track at once, so it is
not added there yet; a local install is not a release).

**Installed 2026-11-03 as 0.19.4 over 0.19.2** (Kevin: "Over 0.19.2"; ledger 0065 has the install, the bypass is in
`fleet/GATES-CHANGELOG.md`). Not driven.
