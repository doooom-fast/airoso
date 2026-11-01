---
name: buildings
description: Stand every building a track can see, measured, not invented — footprints from OSM or a trace, the class from the tag and the size, the height from OSM or a shadow on the track's NAIP checked against OSM, the roof form and the skins by class — through the chain's author step and the house_seat gate, with stills. Use when a track's dossier §5 names buildings, when a drive says "the boxes look wrong", when OSM is thin and footprints must be traced, or when Lake Murray's assembler-era boxes are to move onto the chain. Runs on the Windows box; the bespoke-assets skill holds the textures.
---

# Buildings

A building is standing right when its footprint is where the photograph has it, its height is where a source puts it, its roof
is the kind its class wears, and the car cannot drive through it. The pipeline is five stages, each a tool with a file in
between, so a re-run reproduces every box and a reader can see where each number came from (L1, L12).

```
footprints  ->  plan_buildings.py (class, height, form, skins)  ->  source/bespoke/buildings.json
            ->  author_bespoke_blend.py "blocks" (stand, collide)  ->  loop.blend AUTH_bespoke
            ->  the chain's prep / export                           ->  the kn5
            ->  tools/house_seat_check.py, drive_test               ->  the gate numbers
            ->  tools/bespoke_lap_stills_blend.py                   ->  what it looks like from the car
```

Read first: `fleet/LAWS.md` (L1, L5, L7, L12), `.claude/skills/bespoke-assets/SKILL.md` §3–§4 (the laws that bind an asset and
the author-tool contract), `tools/plan_buildings.py`'s header (the rules and every invented number), the track's `DOSSIER.md` §5.

## 1. Footprints

| Source | File | What it is good for | What it lacks |
|---|---|---|---|
| OSM `way["building"]` | `source/bespoke/osm_buildings.json` (Overpass `elements`), or the cache schema `tools/fetch_buildings_cache.py` writes | tags (`building=*`, `building:levels`, `height`), the whole of an industrial park (Sand Creek: 491) | whole neighbourhoods where nobody mapped them (Lake Murray's Waring houses, the Mission Gorge apartments) |
| Microsoft GlobalMLBuildingFootprints | `source/bespoke/msft_buildings.json` (cache schema, from `tools/msft_footprints.py`: `--find` names the level-9 quadkey tile over `source/naip_box.json`, then the tile → the rows inside the box, with the self-check printed) | whole neighbourhoods OSM lacks, each with the dataset's ML height (Lake Murray: 12,035 footprints, nearly disjoint from OSM's 20,649 — 10,549 where OSM has nothing — and a height on 11,573; at OSM's 1 / 2 / 3 levels its heights ran 4.3 / 5.6 / 8.9 m) | tags: `building=yes` throughout, so the class is the plan's size rule and the by-height rule; ODbL, so the track's licence file names it beside OSM |
| A trace off the track's NAIP | `data/buildings.traced.json` (cache schema, each row with `_source`) | the buildings OSM lacks that no dataset has, read by eye to about 3 m on a 0.6 m photograph | tags: the class comes from the plan's size rule |
| Hand-measured | `track.config.json` `scenery.bespoke.buildings` | the two Nevada tents: footprint and heights with their sources written beside them | — |

Fetch the NAIP at zoom 18 (0.6 m) with `tracks/exotics-racing-lv/source/trace/pc_tiles.py` (Planetary Computer; the STAC
item id carries the capture date); the planner needs the scene's `webmerc` georef (`x0`, `y0`, `z` from the `.georef.json`)
or a north-up `bbox_lonlat`. **A USGS ImageServer export has square-degree pixels and its true extent is not the requested
one** (Milford, `source/trace/unsquash_frame.py`): never take a request's corners as a raster's.

## 2. Class, height, form, skin — `tools/plan_buildings.py`

`python tools/plan_buildings.py <track> <plan.json> [--debug out.jpg]`

- **Sources in order of trust.** The plan's `footprints` list is read in order; a later source's footprint whose centroid
  lies inside an earlier one's is the same building twice and is dropped, and where the earlier one carries no height or
  levels the dropped one's height is offered to it (`_h` says so). Lake Murray: OSM cache, the traced apartments, then
  Microsoft; 1,489 Microsoft footprints dropped onto OSM's, 1,345 OSM houses took their height.
- **Class** from the OSM tag (`house`, `apartments`, `commercial`, `industrial`, `shed`; `roof` = a canopy, left out), else
  by floor area with the plan's `yes_by_area` rule — per track, since an untagged `yes` is a house in Allied Gardens and a
  shed in a paddock — except that an untagged footprint area alone would make a commercial or industrial block is a house
  when a known height puts it under 7.5 m and it is under 1,000 m² (`HOUSE_MAX_H_M`, `HOUSE_MAX_AREA_M2`, `[invented]`;
  Lake Murray's 1,225 big single-storey houses, median 411 m² and 6.6 m to the ridge).
- **Height**, in this order: the row's own height (OSM `height`, or Microsoft's estimate on a Microsoft footprint); OSM
  `building:levels` × the class's storey; a later source's height standing on this footprint; the **shadow** on the NAIP;
  the class default `[invented]`. Every row's `_h` says which.
- **The shadow stage** votes the shadow direction (the direction the dark ground runs farthest from each footprint), finds
  the time of day on the capture date that puts the sun opposite (`scripts/lighting/solar.py`) and its elevation, walks
  each building's shadow from its sun-away edges against the shadow's own darkness beside the wall, and takes
  height = length × tan(elevation). It refuses: a sun under 30° (NAIP's floor; a vote that needs one has found the
  camera's lean on tall walls — Sand Creek 2023), a run to the cap, a dark reference, a wide spread, a height past the
  class cap. Where five or more OSM heights exist it **checks itself** (shadow / OSM median within 0.6–1.6, else the stage
  is off for that photograph), and every shadow height says whether it was checked. `--debug` draws every reference and run
  over the photograph: look at it before believing a number. A sun read by hand (Nevada's pole shadows) can be pinned in
  the plan with its source.
- **Form** by class: house = hip at 4:12, shed = low gable, apartments and commercial = flat with a parapet, industrial =
  flat; the pitch numbers are `[invented by class]`. A pitched roof's wall is the measured top less the rise, floored per
  class.
- **Skin** by class and region: house `stucco` (SoCal) or `siding` (the Midwest and the plains), apartments stucco,
  commercial and industrial tilt-up, shed ribbed metal; roofs shingle on houses, else the colour class read inside the
  footprint on the NAIP (white / tan / dark). All generated by `tools/make_bespoke_assets.py`, CC0, one window per bay on
  the house skins so a wall of n floors shows n rows.

## 3. Stand — `tools/author_bespoke_blend.py` `blocks`

`{"file": "source/bespoke/buildings.json", "auto": true}` in `scenery.bespoke.blocks`. Per building: seated by the prep's
house-seat rule on the built ground (`1GRASS` + `GRASS_FAR`), walls batched by skin under the tile cap and never cut in
two, the roof by form (a ring that fills less than 82 % of its oriented box is roofed flat), a collider `1WALL_TILTUP_*`
only where the fine ground reaches (within 60 m of the lap, over ground triangles under 8 m: `drive_test` culls ground by
cell and reads a wall past it as floating — the High Plains / Sand Creek lesson) and built as a **skirt**, a vertex every
3 m each 0.15 m under its own ground, because the gate takes each wall vertex's lowest point and looks for ground within
2.5 m of it: one flat foot at the footprint's lowest ground stood 2.9 m under the grass at the high corner of a sloped lot
(Lake Murray's two Mission Gorge columns), a far block (`FARBLOCK_*`, no collider, never a GrassFX occluder) where the
footprint has no built ground under it. A planned footprint the checks refuse (on a road, on a cut edge, too close to the
road) is dropped and counted; more than 35 % dropped fails the run. A hand-measured entry refuses instead.

## 4. Gate and show

`house_seat` in `ship.json` `steps.gate` (`tools/house_seat_check.py`: floating / sunken / buried, hard), `drive_test`'s
floating-furniture and obstruction checks, `kn5_ground_check`. Then `tools/bespoke_lap_stills_blend.py` for a driver's eye
every sixth of the lap. The tier moves in `fleet/DEFINITION-OF-DONE.md` with the gate numbers, never before Kevin drives.

## 5. Lake Murray

Lake Murray's houses are the v021 assembler's (`scripts-v021/blender/build_loop_blend.py build_buildings`: OSM boxes, flat,
the Hamburg concrete), the ones Kevin has driven. Moving them onto this pipeline is a rehearsal first — the planner on its
two caches plus `data/buildings.traced.json`, the blocks stood in a scratch copy, `house_seat` and the stills laid beside
0.19.x — and Kevin's call after he sees them. `tools/merge_traced_buildings.py` already carries the traced apartments into
the assembler's copy (`tools/ship_sd.sh`), so the assembler path keeps working meanwhile.

## Do not

- Take a shadow height from an unchecked sun on a photograph with OSM heights to check it against.
- Invent a class default without `[invented]` in the row.
- Stand a collider past the fine ground, or on one flat foot across a slope (floating 99 both ways).
- Take Microsoft's footprints as OSM's houses shifted: check the overlap first (`tools/msft_footprints.py` prints it); at
  Lake Murray they were the houses OSM lacks.
- Regenerate `GEN_*` through `AUTH_bespoke`, or write a coordinate into a tool.
- Call the look done from the Blender stills: the game is the judge.
