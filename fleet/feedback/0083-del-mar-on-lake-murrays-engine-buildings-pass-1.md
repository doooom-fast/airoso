---
id: 0083
title: Del Mar on Lake Murray's engine; buildings pass 1; pass 2 and 3 (lidar heights, canopies on posts)
status: in-progress
scope: tracks/del-mar-lm (new), tracks/del-mar (its source, ledger 0064); tools/seat_edges_blend.py, tools/plan_buildings.py (opt-in keys); tools/lidar_building_heights.py (new, pass 2), tools/author_bespoke_blend.py (posts form, pass 3)
layer: project + engine (opt-in)
train: -
---

## Request (Kevin, 2026-11-06, through the coordinator)

> "after that, we to keep going, prioritizing furniture passes on milford and buildings started on del mar"

Standing rules: every track builds on Lake Murray v4's engine (ledger 0078), and "I just want real" (measured geometry, no
invented limits). Del Mar's layout is still the **ESTIMATE** of ledger 0064 (the 1987-92 IMSA course placed from the ESPN
broadcasts; 2.0 km against the published 2.57 km); nothing here changes it.

## 1. The branch

`claude/del-mar-lm` from `origin/claude/fleet-lm-engine` (a98fa35b). Del Mar's source checked out from
`origin/claude/del-mar-source` (5611cdd), not merged: `tracks/del-mar/`, `docs/research/del-mar/`, ledger 0064 and its DoD
row (`43def7b`). The 288 MB `loop.blend` stays an LFS pointer (the port reads the source's data, not its blend).
**b176cfa's `write_ai_line` guard is not carried:** fleet-lm-engine lacks it, but it changes which fillet windows run on
every closed line (Lake Murray's included), and the port's AI line was written without it (9 corners filleted, no
IndexError). `scripts/` is untouched.

## 2. The port: `tracks/del-mar-lm` 0.1.0 (`42a041c`)

The 0078 shape (Pueblo's): `lm_intake.source_track del-mar`, the estimate's line and 13 m width unchanged, the measured 3DEP
profile with the elevation stage's 9 % cap undone (33 points moved, max 1.71 m, all at the two crossings of Jimmy Durante
Blvd), the port's own 3DEP grid (`data/heightfield.*`, 23 x 19 at 40 m, the elevation stage's `build_heightfield` over the
source's line + 150 m: the source commits none), the circuit edge, no lamps. `install_folder del_mar_fairgrounds_lm`
beside 0.1.0; `ui_description` opens "ESTIMATED layout".

**What the measured profile found.** Where the estimated line crosses Jimmy Durante Blvd (s 111-175 and s 1,050-1,100 of
the port) 3DEP reads the boulevard's planted banks: 25.3 % over 10 m (0.1.0 capped it at 9 %). That is today's ground on
an estimated crossing; the 1987 course's crossing surface is not known. It is built as measured, and it is the thing to
feel first.

| Run (Mac, empty workshop) | change | ground on top | kinks /km | result |
|---|---|---|---|---|
| p1 | as Pueblo's port (grid_upsample 2, 3 m rows) | **35** (the banks, s 111-118, 172) | 66.2 | red |
| p2 | `lm_intake.grid_upsample` 4 | 7 | 65.2 | red |
| p3 | `lm_intake.resample_m` 1.5 (Milford's round-5 rule; smoothing doubled in points) | 2 (s 1,099, 0.7 mm) | 6.68 | red |
| p4 | grid_upsample 8 | 2 (same) | 6.68 | red: not the grid |
| p5 / del_mar_lm | `route.seat_edges_grade_pct` 5 | **0** | 6.68 | **green** |

The last two were engine-july's 3 m edge shelf: a grass vertex on the shelf and one under the lane chord across the
grade's turn, 0.7 mm over the lane (read off the built OBJ: grass 2.6142 m over road 2.6135 m at (-37.015, -186.631)).
`seat_edges` already cuts the ground fine along a banked edge for the same chord; the new opt-in key gives that cut to the
line's points steeper than 5 % [invented: the lots read ~1 %, the banks 8-37 %] (`tools/seat_edges_grade.py`, 74 of 1,338
points; TERRAIN 26,305 -> 56,790 verts). Absent = the tool as before; only `del-mar-lm` names it (tested).

`tracks/del-mar/track.config.json`: `road_profile.ribbon_cols` 8 dropped. 0.1.0 was built on 6f7404e, whose build_mesh had
no `ribbon_cols`; under ledger 0069's rule the key would change the unbanked ribbon (`test_ribbon_cols_graded_corner`
failed on it). The v021 assembler never reads it.

### Gate table: the port against 0.1.0 (BUILT kn5)

| | 0.1.0 (installed, ledger 0064) | **port 0.1.0** | **port 0.2.0 (buildings)** |
|---|---|---|---|
| engine | airoso draft (build_mesh) | Lake Murray v4's | same |
| lap (drive_test) | 1,974.5 m | 1,947.0 m | 1,947.0 m |
| profile | 9 % cap | measured, 25.3 % / 10 m at the banks | same |
| drive_test | PASS | PASS | PASS |
| ground on top / severe steps | 0 / 7 (s 1,131-1,139, <= 7.9 cm) | 0 / **0** | 0 / 0 |
| bumps /km / kinks /km | 22.79 / 81.03 | **0 / 6.68** | 0 / 6.68 |
| fold / vertex / apron bumps | 9 / 3 / 53 | 0 / 0 / 3 | 0 / 0 / 3 |
| excursion drops gated / far ledges | 1 / 2 | **0 / 0** | 0 / 0 |
| obstructed / floating furniture | 0 / 0 | 0 / 0 | 0 / 0 |
| replication vs measured | 0.02 / 0.38 / 2.48 m | not read (the port carries no `centerline.elevation.json` record) | same |
| audit_mesh | CLEAN | CLEAN | CLEAN (wall verts 0 -> 1,888) |
| verify_kn5 | PASS | PASS | PASS |
| kn5_ground_check | PASS (walls 106 / hovering 0; road over ground 3/581, p95 0.014) | PASS (no walls; 0/2,292, p95 0.021, max 0.027) | PASS (walls 11 / hovering 0; 0/2,292) |
| house_seat | not run | PASS (none) | PASS (253 judged, contact -0.39..-0.15 m, 0 floating / sunken / buried) |
| edge at 1 m past the lane | (shoulder) | edge strip 99.7 % | same |
| road kn5 | 124.4 MB, md5 d924754d | 13,269,621 B (md5 50f83dce, workshop; kn5_equiv to p5: tangents only) | 15,811,691 B (md5 607655cd, workshop; kn5_equiv to b1: tangents only) |

**Gone or worse against 0.1.0:** its 106 wall objects (build_mesh's concrete danger-run barriers, a drop-guard construct,
not the course's K-rail); the replication row (no record carried). No gate row is worse.

**Found, not changed (the line is the estimate's):** both 0.1.0 and the port are built **clockwise** (signed area of the
line -92,051 / -91,913 m² with x east, z north; s 0 heads 105°, east along the straight; the grid lands in the east lobe at
x 312), while ledger 0064, the DOSSIER and `route._orientation_doc` say counter-clockwise, west down the straight. Owed.

## 3. Buildings pass 1 (inventory `b021a90`, built `88f0fb3`)

Through ledger 0062's pipeline. **Footprints:** one Overpass query (the pipeline's phase-1 data), every `building` way and
relation in the lap + 600 m (`source/bespoke/osm_buildings.json`, provenance beside it; 375 elements, the Hilton's
multipolygon as its outer rings). **Today's fairgrounds, not 1987's:** OSM maps the 1991-93 rebuild; 0064 says the 1987
hall stood elsewhere. **Class:** OSM's tag, else area (`yes_by_area` under 60 m² kiosk-shed / under 1,500 m² one-storey
block / exhibit hall [invented rule, by the NAIP]); the plan's new opt-in `tag_class` (tested; no other plan names it)
classes the tags the shared table lacks: `stable` -> shed (the barn rows), `grandstand` -> commercial, `pavilion` ->
canopy (left out: no open-sided form). **Height:** OSM `height` / `building:levels`, else the shadow on the NAIP, else the
class default `[invented]`. **The shadow stage was not used:** it voted a 76.5° sun (2012-05-19 13:02 PDT), unchecked (no
OSM heights in the photograph), and its `--debug` drawing ran the "shadows" across the barns' own solar panels.

**Inventory** (`tracks/del-mar-lm/source/bespoke/buildings.inventory.json`: every row's name, OSM way, area, class and its
source, height and its source, distance from the lap): 352 planned (left out: 9 canopies, 12 under 25 m²).

| | planned | in 450 m reach | stood |
|---|---|---|---|
| total | 352 | 152 | **254** (the author measures reach on the built line) |
| commercial / shed / industrial / house / apartments | 209 / 91 / 27 / 22 / 3 | 74 / 61 / 17 / 0 / 0 | 136 / 76 / 21 / 21 / 0 |
| height measured (OSM levels) | 3 | 1 | **2** (the Grand Stand, 6 levels -> 21.6 m; one block of 4) |
| height invented (class default) | 349 | 151 | **252** |

Named and standing: the Grand Stand (242 m from the lap), Surfside Race Place, the Expo Center, Wyland Center, Activity
Center, O'Brien Hall, Bing Crosby Hall, the Exhibit Hall, Mission Tower, the Arena Gate, the tennis club, the Hilton
(4.5 m [invented]: a hotel's class default), the businesses on Via de la Valle. **Dropped for cause, 6:** on the road, 5
(osm116794668 **Chevrolet Del Mar Arena**, osm116794616 **Barn W**, osm116794649, osm116794672, osm995030003): today's
buildings stand on the estimated course; at 2.4 m from it, 1 (osm995030004). 92 dropped past 450 m. Colliders 7 (within
60 m of the lap), far blocks 0.

**Invented in this pass:** 252 of 254 heights (class defaults: kiosk 2.1-2.8, block 4.5, hall 8.0 m); the area rule; the
roof forms and skins by class; the roof colour of buildings off the NAIP crop ("tan"); the 5 % grade trigger of item 2.

## 4. Stills (Mac, `del_mar_lm` 0.2.0's split scene; not in the repo)

`/Volumes/Drive/codex/dm_work/stills/del_mar_lm_020_{straight_east,straight_west,halls_north,halls_south,grandstand_view}.jpg`
(`dm_work/tools/station_stills_blend.py`: driver's eye at s 1,930 / 120 / 1,380 / 1,560 / 1,450). They show the straight
between grey tilt-up halls and the barn rows; plain boxes, no windows on the halls, the Arena gone from beside the
straight (dropped: it stands on the estimate). The look is pass 1's, not the place's.

## Lake Murray unchanged (Mac)

- `git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/`: empty.
- Trim A/B (`dm_work/lmtrim_b`): Lake Murray's committed trim inputs through fleet-lm-engine's and this head's
  `tools/trim_connectors.py`: byte-identical (`664da93b…`, `b73b70f4…`, `f0c97952…`), logs identical.
- The two changed tools: Lake Murray's ship.json never names `seat_edges` (`test_lm_engine_port`), and no other track's
  config names `route.seat_edges_grade_pct` nor any other plan `tag_class` (both tested).
- Tests: `tests/run_tests.py` (.venv python): 1,281 pass, 8 fail — the Mac baseline 0079 round K lists (`test_draft_equiv`
  x5, `test_registry_moves`, `test_bench_pad` x2); 4 new tests pass.

## Downloads: none beyond the pipeline's queries

The OSM query and the 3DEP `getSamples` grid (437 points, the elevation stage's own query). **Not fetched, Kevin's call**
(each would put measured heights on the 252 invented ones):
- USGS 3DEP lidar, CA_SanDiegoCo_D24 (newest over the lap): `USGS_LPC_CA_SanDiegoCo_D24_11SMS475648.laz` 62,882,222 B and
  `USGS_LPC_CA_SanDiegoCo_D24_11SMS476648.laz` 65,934,024 B, at
  `https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CA_SanDiegoCo_D24/CA_SanDiegoCo_1_D24/LAZ/`
  (the lap's NAIP extent; the 450 m reach west to the Grand Stand may need one tile more). Older: San_Diego_CA_2014_LiDAR
  `USGS_LPC_San_Diego_CA_2014_LiDAR_250930.laz` 44,925,923 B and `..._250935.laz` 37,371,149 B under
  `.../Projects/San_Diego_CA_2014_LiDAR/CA_SanDiegoQL2_2014/LAZ/`.
- Microsoft GlobalMLBuildingFootprints quadkey `023013221` (the same tile as Lake Murray's, 77.9 MB per ledger 0062; its URL
  is the row of `dataset-links.csv`; the PC may still hold it from 0062's rehearsal 2): ML heights; OSM already has the
  fairgrounds' footprints.
- Imagery newer than the 2012 NAIP (a lower sun for the shadow stage): none listed.

## PC runbook (0083; rehearse, NO install — the PC asks Kevin)

1. `git fetch && git checkout claude/del-mar-lm` (88f0fb36 or later) in a clean worktree; `GIT_LFS_SKIP_SMUDGE=1` is fine
   (no blend is read). ENG = the snapshot's `scripts/` + `vendor/` with airoso's `assets/textures`, as 0078's runbooks.
2. Rehearse from an EMPTY scratch workshop:
   `SHIP_PROJ=D:/k10-scratch/del_mar_lm_reh AIROSO=<worktree> ENG=<eng> bash tools/ship_track.sh del-mar-lm --no-install`.
3. Expect every row of the 0.2.0 column above: drive_test PASS (soft top 0, severe 0, kinks 6.68 /km, drops 0, obstructed
   0, floating 0), audit CLEAN (wall verts 1,888), verify_kn5 PASS, kn5_ground_check PASS (walls 11, 0/2,292), house_seat
   PASS (253 judged); the bespoke line "254 buildings stood, 98 dropped (92 of them past 450 m of the lap)"; seat-edges
   "74 line points steeper"; road kn5 15,811,691 B. Compare the kn5 with `tools/kn5_equiv.py` against a Mac copy if one is
   carried (tangents only is the Mac's own run-to-run noise); the ground may differ by ±1-3 grass vertices (the known
   tangent-merge noise, runbook 4m). Any other difference: stop and report the row.
4. Do **not** install. Ask Kevin: "Del Mar on Lake Murray's engine with the fairgrounds' buildings (estimated layout,
   0.2.0) beside 0.1.0 as `del_mar_fairgrounds_lm`?" Only on his word, drop `--no-install` from an empty
   `D:/k10-scratch/del_mar_lm`.

## Owed after pass 1 (superseded: the list after pass 2, at the end, is where to start)

1. **Buildings pass 2:** measured heights for the 252 invented (the lidar tiles above or Microsoft's tile, Kevin's go); the
   Grand Stand's form (a stepped stand, not a 21.6 m box); open-sided pavilions; the halls' skins (windows, the barns'
   red roofs and solar panels off the NAIP); the 5 buildings standing on the estimated course (today's Arena, Barn W): the
   estimate or the buildings, a call that waits on the layout (6 below).
2. **Walls:** the course was K-rail with debris fence everywhere (DOSSIER §8); the port has none (0.1.0's 106 were
   build_mesh's drop guards). Bespoke rails on both edges, measured off the 1987 frames where they show.
3. **Furniture:** bleachers on the straight and the hairpins, the sponsor bridges as plain spans, palms along the pit
   straight, the Spanish tower (DOSSIER §8).
4. **The boulevard banks:** 25 % over 10 m measured on today's planted banks of Jimmy Durante Blvd; the 1987 crossing
   surface is unknown. Feel it; an era frame decides.
5. **Direction:** the built line runs clockwise; the dossier says counter-clockwise. Check against the 1987 frames, then
   `route.reverse` or the doc.
6. **The layout itself, still estimated:** one georeferenced 1989-96 frame (USGS NAPP / Google Earth Pro history) for the
   correction pass (ledger 0064), then re-run the source from `aerial` and this port from `lm_intake`.

## 5. Buildings pass 2: heights measured off the lidar (`6e420ae`, `310558e`, built `b6de17b`)

**Request (Kevin, 2026-11-06, verbatim):** "Yes, fetch both" — to "Fetch the lidar for Milford (size unmeasured, est. tens
of MB) and Del Mar (2 tiles, 129 MB)?". For Del Mar: exactly the two D24 tiles below; no third tile, no 2014 tiles, no
Microsoft footprints.

**The tiles** (`https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CA_SanDiegoCo_D24/CA_SanDiegoCo_1_D24/LAZ/`;
on the Mac in `/Volumes/Drive/codex/lidar_dl/del_mar_d24/`, never in the repo):

| tile | bytes (as fetched = as listed) | md5 | points | track frame (x E, y N, m) |
|---|---|---|---|---|
| `USGS_LPC_CA_SanDiegoCo_D24_11SMS475648.laz` | 62,882,222 | 9f3d8dbb… | 10,648,506 | x -1,035..-34, y -512..490 |
| `USGS_LPC_CA_SanDiegoCo_D24_11SMS476648.laz` | 65,934,024 | 9af405e9… | 11,294,047 | x -37..966, y -510..493 |

Both decompress to their header counts. Flown **2024-11-09** (the points' GPS time; the files were written 2026-06-18),
NAD83(2011) / UTM 11N, NAVD88 (Geoid18), metres. Classes 1 / 2 / 7 / 9 / 17 / 18 / 20: **no building class (6)**. The
second tile hit HTTP 429 (rate limit) and was resumed; its size and point count check. The lap lies inside the pair; the
stood buildings run y -763..877, so the north (Via de la Valle, the barns' north rows) and the south edge are off it.
Each tile's corners in lon/lat and in the track frame are in `buildings.lidar.json` `tiles`.

**The method** (`tools/lidar_building_heights.py`, new, tested; the lidar venv's `python -I`; output
`source/bespoke/buildings.lidar.json`, 120 kB): per OSM footprint, in the tile's CRS: roof = the SINGLE returns that are
not ground / noise / water, at least 0.75 m inside the walls (a roof returns once, a tree several times; class 6 where a
cloud has it); ground = the median class-2 point 1-8 m outside the walls and outside every other footprint (widened to
15 / 30 m when thin); heights = the roof points' p05..p98 over that ground; levels = the roof's height modes (0.5 m bins,
15 % share, 2 m apart); cover = the footprint's 1 m cells holding a point (under 50 %: not measured). A footprint whose
first returns are more than half ground has no roof in the lidar ("no_roof"); more than half multiple returns is a tree
(none here). Every threshold is `[invented]` and listed in the file's `params`. **The planner** takes it through the plan's
opt-in `lidar` key (`tools/plan_buildings.py lidar_rows`; absent = as before: Del Mar's plan without it rewrites pass 1's
`buildings.json` byte-identical, and no other plan names it, tested): a measured flat roof's wall = the median (the deck;
the 0.7 m parapet stays `[invented]`), a pitched roof's eave = p10 and ridge = p95 (the pitch is measured, the form is
still the class's); the lidar wins over OSM levels.

**2024 lidar shows TODAY's fairgrounds, not 1987's.** The Grand Stand measured here is the 1993 one (SOURCES: the old
stand came down in 1991); the halls are the 1991-93 rebuild's. Measured is not period-correct. The five of today's
buildings on the estimated course stay dropped (the author refuses them: osm116794668 **Chevrolet Del Mar Arena**,
measured 16.8 m; osm116794616 **Barn W**, 6.4 m; osm116794649, osm116794672, osm995030003), and osm995030004 at 2.4 m.

### Covered vs not (pass 1's 254 stood)

| | stood in 0.2.0 | measured | off the tiles (default stays `[invented]`) | bare ground in the lidar (dropped) |
|---|---|---|---|---|
| total | 254 | **126** | **124** | **4** |
| commercial / shed / industrial / house | 136 / 76 / 21 / 21 | 60 / 53 / 13 / 0 | 75 / 20 / 8 / 21 | 1 / 3 / 0 / 0 |

- **Every stood building within 299 m of the lap is measured.** The 124 not measured are 299-877 m out, in
  `11SMS475649` (77), `11SMS476649` (32), both of those (3), `11SMS475647` (12): the Via de la Valle row (Whole Foods,
  Milton's, 7-Eleven, the Dalton offices, Winner Circle Resort, the banks), the 21 houses, the barns' north rows. The
  inventory's `lidar: "uncovered"` names each; osm929845974 (34 % on the tiles) is among them.
- **17 footprints cut by the tiles' north edge** (UTM y 3,649,000), 52-80 % on the tiles, 13 of them barn rows, are
  measured on that part (each `_h` says the share); the cut runs across the barns' ridges, so both eaves and the ridge
  are read.
- **Dropped, the lidar sees ground inside the walls:** osm929845992 / 993 / 996 (37-42 m², 88-91 % ground, 164-206 m from
  the lap) and osm1421065497 (670 m², 73 % ground, 100 m from the lap). Pass 1 stood them at class defaults.

### Measured against pass 1's defaults (126 stood)

- Median change of the top **+0.8 m**, mean |change| **1.4 m**. Sheds (the barn rows) **5.5 m** median top (3.0-5.8)
  against 2.8-3.9; exhibit halls **7.5 m** (3.6-12.7) against 8.0; blocks **4.1 m** (2.8-10.4) against 4.5.
- **Biggest rises:** osm116794628 4.5 -> 10.4 m; **Wyland Center** 8.0 -> 12.7; the **Hilton** 4.5 -> 8.9;
  osm116794663 / 630 4.5 -> 8.1 / 8.0; the **Expo Center** 8.0 -> 10.4; the shed rows 3.4 -> 5.8.
- **Biggest drops:** osm929875315 8.0 -> 3.6 m; the **Activity Center** 8.0 -> 5.5; osm66984140 8.0 -> 5.6; blocks
  4.5 -> 2.8-3.1 (osm929845985 / 986, osm116897947, osm929875351).
- Named: Surfside Race Place 9.3 m, O'Brien Hall 10.1, Bing Crosby Hall 7.9, the Exhibit Hall 8.3, Mission Tower 6.8
  (the building's median roof: the tower is a level the median does not stand), the Arena Gate 3.3, the tennis club 3.6,
  Pier One 5.2, Denny's 4.7, the Shell 3.8.
- **More than one roof level:** 40 of the measured stood; each row's `_levels` (the inventory's `roof_levels`) lists
  them. They stand at the median roof (only the Grand Stand is cut into its levels).

### The Grand Stand (osm116794621)

- **OSM's 6 levels x 3.6 m = 21.6 m against the lidar: the roof's median is 21.72 m** over its ground (4.47 m NAVD88,
  23,522 ground points) from 126,955 roof points. OSM's number holds for the main roof; levels 21.7 and 25.2 m.
- **Its measured form**, the roof's median in 2 m slices across the short axis (89 m; the long axis 256 m; the short
  axis points 14° east of north): 5-7 m along the south 36 m, a rise from 8.5 to 18 m over the next 12 m, 21.7 m for
  26 m, and **25.1 m** along the north 15 m. It stands as six flat tiers (`osm116794621_t0..t5`: **5.2 / 5.7 / 9.4 /
  16.4 / 21.7 / 25.1 m**), the footprint clipped to each band (`buildings.lidar.json` `stepped` has the slice profile).
  The two rise tiers' p10..p90 (9.4: 5.1..17.7; 16.4: 6.8..23.2) say it is a slope stood as two steps: 0062 has no
  sloped flat roof.

### Pavilions (open-sided)

0062's forms are flat / flat_parapet / hip / gable: **no roof-on-posts form**, so none is stood (the plan's `tag_class`
leaves `pavilion` and `roof` out, as in pass 1). Listed, measured:

| OSM | tag | m² | roof p50 (p10..p90) over ground | ground in its first returns |
|---|---|---|---|---|
| osm929845988 | pavilion | 64 | 3.59 m (3.30..3.93) | 1 % |
| osm929845989 | pavilion | 355 | 3.68 m (3.33..4.12) | 0 % |
| osm929845990 | pavilion | 64 | 3.00 m (2.73..3.33) | 0 % |
| osm929845991 | pavilion | 423 | 3.11 m (2.74..3.53) | 1 % |
| osm929845994 | pavilion | 429 | 3.66 m (3.32..4.10) | 1 % |
| osm929845995 | pavilion | 64 | 3.54 m (3.25..3.91) | 1 % |
| osm31816244; osm31817331 (Mobil); osm929875359 (Chevron) | roof | 127 / 294 / 291 | off the tiles | - |

A first return sees a roof from above either way; whether the sides are open is not in it.

### Build: candidate 0.2.1 (Mac, empty workshop `dm_work/v021b`, no force)

ENG = `dm_work/eng` (the engine snapshot) with `assets/textures` md5-equal to this head's (95 files, 0 differ). The
first try (`dm_work/v021`, the eave at p05) failed **house_seat**: osm1056063269, a 3.5 m shed whose p05 read a lean-to's
1.29 m (its p10 is 3.47), roof 0.82 m over its ground. The eave is now p10; that run is kept as it ran.

| | port 0.2.0 (pass 1) | **0.2.1 (pass 2)** |
|---|---|---|
| bespoke | 254 stood, 98 dropped (92 past 450 m) | **255 stood** (less 4 bare ground; the Grand Stand 6 tiers for 1 box), 98 dropped (92 past 450 m), the same 6 for cause |
| drive_test | PASS | PASS |
| ground on top / severe steps | 0 / 0 | 0 / 0 |
| bumps /km / kinks /km | 0 / 6.68 | 0 / 6.68 |
| excursion drops / far ledges / obstructed / floating furniture | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| audit_mesh | CLEAN (wall verts 1,888) | CLEAN (1,888) |
| verify_kn5 | PASS | PASS |
| kn5_ground_check | PASS (walls 11, hovering 0; 0/2,292) | PASS (walls 11, hovering 0; 0/2,292, p95 0.021) |
| house_seat | PASS (253 judged; lowest roof over its ground 1.05 m; buried share > 30 %: 16) | PASS (**252** judged: tiers re-join by position; contact -0.39..-0.15 m; 0 floating / sunken / buried; lowest roof 1.43 m; buried share > 30 %: 2) |
| edge at 1 m | kerb 99.7 % | same |
| road kn5 | 15,811,691 B (md5 607655cd) | **15,774,997 B (md5 d934ef81)** |

`data/audit.json`, `drive_test*.json`, `kn5_ground_check.full.json` and `edge_report.json` are byte-identical to 0.2.0's:
the road and the ground did not move. Version 0.2.1.

## 6. Stills, pass 2 (Mac; not in the repo)

`/Volumes/Drive/codex/dm_work/stills/p2_020_*.jpg` (0.2.0's scene, `dm_work/del_mar_lm`) against `p2_021_*.jpg`
(0.2.1's, `dm_work/v021b`), the same cameras: `grandstand_view` (s 1,443, looking 96° left, ~370 m to the stand),
`halls_side` (s 1,416, 107° left), `wyland_view` (s 1,428, 104° left), `halls_north` (s 1,380), `halls_south`
(s 1,560), `straight_east` (s 1,930), `surfside_view` (s 1,932, 88° left). Pass 1's own `del_mar_lm_020_*` cameras were not
recorded (their yaw), so 0.2.0 was re-shot. They show the Expo / Activity block in front standing taller (10.4 m against
8.0), the Grand Stand behind it stepping up in visible rises instead of one flat 21.6 m line, and the near hall in
`wyland_view` taller. Still plain grey boxes: the skins are pass 1's.

## PC runbook 0083-2 (rehearse from a clean checkout; NO install — the PC asks Kevin)

1. `git fetch`, then a clean worktree at `origin/claude/del-mar-lm` (b6de17b or later), `GIT_LFS_SKIP_SMUDGE=1` (no
   blend is read). No lidar is needed: the measured heights are committed (`source/bespoke/buildings.lidar.json` ->
   `buildings.json`); the build never reads a LAZ.
2. **ENG = the engine snapshot PLUS airoso's `assets/textures` at the head being built, md5-checked** (the rule since
   the Milford rehearsal 0082-1): copy `<worktree>/assets/textures` over ENG's, then compare every file's md5 (95 files
   on the Mac); any difference: stop.
3. From an EMPTY scratch workshop:
   `SHIP_PROJ=D:/k10-scratch/del_mar_lm_021_reh AIROSO=<worktree> ENG=<eng> bash tools/ship_track.sh del-mar-lm --no-install`.
4. Expect the 0.2.1 column above: bespoke "255 buildings stood, 98 dropped (92 of them past 450 m of the lap)", the same
   6 for cause; seat-edges "74 line points steeper"; drive_test PASS (soft top 0, severe 0, kinks 6.68 /km, drops 0,
   obstructed 0, floating 0); audit CLEAN (walls 1,888 v); verify_kn5 PASS; kn5_ground_check PASS (walls 11, 0/2,292);
   house_seat PASS (252 judged, 0 / 0 / 0); road kn5 15,774,997 B (±1-3 grass vertices of tangent-merge noise is known,
   runbook 4m; `tools/kn5_equiv.py` against a Mac copy if carried). Any other row: stop and report it.
5. Do **not** install. Ask Kevin: "Del Mar LM 0.2.1: the fairgrounds' buildings at their 2024 lidar heights (today's
   buildings; the Grand Stand stepped), over 0.2.0 as `del_mar_fairgrounds_lm`?" Only on his word, from an empty
   `D:/k10-scratch/del_mar_lm`.

## Lake Murray unchanged after pass 2 (Mac)

- `git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/`: empty.
- Trim A/B (`dm_work/lmtrim_d`: this head's `tools/trim_connectors.py` against fleet-lm-engine's): byte-identical
  (`664da93b…`, `b73b70f4…`, `f0c97952…`), logs identical.
- The changed tool (`tools/plan_buildings.py`): the `lidar` key is opt-in; no other track's plan names it (tested), and
  Del Mar's plan without it rewrites pass 1's file byte-identical.
- Tests: `tests/run_tests.py` (.venv python, a `python` on PATH): 1,288 pass, 8 fail — the known 8 (`test_draft_equiv`
  x5, `test_registry_moves`, `test_bench_pad` x2); the 7 new tests pass. (With no `python` on PATH,
  `test_ship_track_chain` x4 and `test_ship_fleet` x1 also fail on "python: command not found": the shell, not the code.)

## Downloads in pass 2

The two approved tiles (above). Sizes looked up by HTTP HEAD only (nothing fetched) for the tiles that would measure the
124 still at defaults — **not fetched, Kevin's call**, same URL directory:
- `USGS_LPC_CA_SanDiegoCo_D24_11SMS475649.laz` — 81,488,775 B (north-west: 80 stood buildings: the barns' north rows,
  the houses, Winner Circle).
- `USGS_LPC_CA_SanDiegoCo_D24_11SMS476649.laz` — 79,285,690 B (north-east: 35, the Via de la Valle row).
- `USGS_LPC_CA_SanDiegoCo_D24_11SMS475647.laz` — 90,940,763 B (south-west: 12).

## Owed after pass 2 (superseded: the list after pass 3, at the end, is where to start)

1. **The 124 at class defaults `[invented]`** (299-877 m from the lap): the three tiles above (251.7 MB together) would
   measure them, Kevin's go; then re-run `tools/lidar_building_heights.py` on the planner's output without the `lidar`
   key (its header says how) and the plan with it.
2. **A roof-on-posts form** for the 6 pavilions (measured 3.0-3.7 m) and the 3 fuel canopies: an opt-in open-sided form
   in `tools/author_bespoke_blend.py` (a roof slab on posts, no walls), then the plan's `tag_class` stops leaving them out.
3. **Multi-level roofs:** 40 measured buildings with more than one roof level stand at their median (Mission Tower's
   tower, the Wyland Center's 16.7 m level, O'Brien Hall's three): `--stepped` per building (the Grand Stand's way) or a
   level-by-area cut.
4. **The Grand Stand's rise** is a slope stood as two steps (9.4 / 16.4 m); a sloped-roof form would stand it as measured.
5. **The look:** the halls' skins (windows, the barns' red roofs and solar panels off the NAIP): pass 1's owed 1.
6. **Period:** everything measured is 2024's (the 1993 stand, the 1991-93 halls); the 1987 buildings need an era frame
   (item 9 decides where they stood).
7. **Walls** (K-rail + debris fence), **furniture** (bleachers, sponsor bridges, palms, the Spanish tower), **the
   boulevard banks** (25 % over 10 m, today's), **direction** (built clockwise; the dossier says counter-clockwise):
   pass 1's owed 2-5, unchanged.
8. **The 5 of today's buildings on the estimated course** stay dropped (the Arena measured 16.8 m, Barn W 6.4 m): the
   estimate or the buildings, a call that waits on the layout.
9. **The layout itself, still estimated:** one georeferenced 1989-96 frame for ledger 0064's correction pass.
10. **Install:** none from the Mac; 0.2.1 goes to the PC's rehearsal (runbook 0083-2) and Kevin's word.

## PC: rehearsal 0083-1 and the 0.2.0 install (2026-11-06)

- **0083-1 MATCHED** (fc7e09fa, `D:/k10-scratch/del_mar_lm_reh`, ENG `D:/k10-scratch/eng_dmlm` = eng_repro + airoso's 95
  `assets/textures`, md5-checked; SOURCES.txt differs only by CRLF): every row of the 0.2.0 column; `[bespoke] 254
  buildings stood, 98 dropped (92 of them past 450 m of the lap)`; `[seat-edges] 74 line points steeper`; road kn5
  15,811,691 B (the Mac's size; md5 84b7fd4c vs 607655cd, tangents); every texture its materials name is embedded.
- **INSTALLED on Kevin's word** (2026-11-06, "Install beside 0.1.0 (Recommended)", asked with: the layout is estimated,
  most heights are defaults, the halls are plain grey boxes): fc7e09fa from an empty `D:/k10-scratch/del_mar_lm`, ENG
  eng_dmlm; SHIP OK, no force; `content/tracks/del_mar_fairgrounds_lm` ("doooom California — Del Mar Grand Prix (LM
  engine)" 0.2.0) beside `del_mar_fairgrounds` 0.1.0; kn5 kn5_equiv-equivalent to the rehearsal (tangents only). The
  sync-back's records are on their own branch `claude/del-mar-lm-0200-installed` (ee61922): this branch's later rounds
  rewrote `house_seat_check.json` / `split_manifest.json`. Not driven yet.

## PC: rehearsal 0083-2 and the 0.2.1 install (2026-11-07)

- **0083-2 MATCHED** (557b7bdb, `D:/k10-scratch/del_mar_lm_021_reh`, ENG `D:/k10-scratch/eng_dmlm_021` = eng_repro +
  airoso's `assets/textures` at 557b7bdb, 95/95 md5-equal): `[bespoke] 255 buildings stood, 98 dropped (92 of them past
  450 m of the lap)`, drop reasons 5 on a road or kerb + 1 near a road or wall; `[seat-edges] 74 line points steeper`;
  drive_test PASS (soft 0, severe 0, kinks 6.68 /km, drops 0, obstructed 0, floating 0); audit CLEAN (walls 1,888 v);
  verify_kn5 + --inis PASS; kn5_ground_check PASS (walls 11, hovering 0, 0/2,292); house_seat PASS (252 judged, 0/0/0,
  lowest roof 1.425 m); road kn5 15,774,997 B (the Mac's size; md5 a93abe52 vs d934ef81, tangents); 15 textures, every one
  its materials name embedded.
- **INSTALLED on Kevin's word** (2026-11-07, "Install over 0.2.0 (Recommended)", asked with: today's buildings at their
  2024 lidar heights, not 1987-92, on the estimated layout): 557b7bdb from an empty `D:/k10-scratch/del_mar_lm` (0.2.0's
  workshop parked as `del_mar_lm.0.2.0`), ENG eng_dmlm_021; SHIP OK, no force; 0.2.0's folder parked in
  `D:/k10-track-archive/2026-11-07_120606/`; `del_mar_fairgrounds_lm` 0.2.1, kn5 kn5_equiv-equivalent to the rehearsal
  (tangents only); `del_mar_fairgrounds` 0.1.0 still beside it. Records with this note (no record path changed on this
  branch since 557b7bdb). Not driven yet.

## 7. Buildings pass 3: every footprint measured, canopies on posts (`8cfac96`, `f958367`, `c3a9c0e`, built `ef7d239`)

**Request (Kevin, 2026-11-07, verbatim, through the coordinator):** "Yes, fetch them" — the three tiles pass 2 listed.
Nothing else fetched.

**The tiles** (same URL directory; `/Volumes/Drive/codex/lidar_dl/del_mar_d24/`, and on the G10 in
`~/airoso-work/data/del_mar_d24/`, md5-equal; never in the repo):

| tile | bytes (as fetched = as listed) | md5 | points (= header) |
|---|---|---|---|
| `USGS_LPC_CA_SanDiegoCo_D24_11SMS475649.laz` | 81,488,775 | 3498fafa… | 12,793,553 |
| `USGS_LPC_CA_SanDiegoCo_D24_11SMS476649.laz` | 79,285,690 | ef01c39d… | 12,425,700 |
| `USGS_LPC_CA_SanDiegoCo_D24_11SMS475647.laz` | 90,940,763 | 00327c7a… | 13,636,337 |

USGS answered HTTP 429 to most first attempts; each tile was resumed from the bytes on disk after a 60 s back-off. All
flown 2024-11-09, the same CRS and classes as pass 2's two.

**Where it ran: the G10** (mirror-reaper.local; Kevin farms asset jobs out to it; `g10run.sh`, job `dm-p3`, code at
`f958367`, `systemd-run --scope MemoryMax=4G MemorySwapMax=0`, nice 19 / ionice idle). The input was pass 1's
`buildings.json` (the planner's output without `lidar`, md5 13b3cb01), the pass-2 flags, the five tiles:
`[lidar] 16,516,179 points from 5 tiles; 361 footprints: measured 352, no_roof 9; stepped osm116794621`;
**`TIMING wall=48.2s user=116.8s sys=1.1s maxrss=2056MB exit=0`**; afterwards surveillance / mirror-reaper / nginx /
cam-hls@mv / cam-hls@garden all active. To fit the cap the tool now reads each tile in 2M-point chunks and keeps only the
points in 5 m cells some footprint's query box (+ the 30 m ground ring + 1 m + 5 m) overlaps (`f958367`): on pass 2's two
tiles that run is **byte-identical** to 557b7bdb's `buildings.lidar.json` (md5 ad412647; Mac, 7.5 M of 21.9 M points
kept, maxrss 1.31 GB, 7.6 s; the whole-tile read was 3.0 GB on the G10). Only a docstring line of the tool changed after.

**The roof-on-posts form** (`8cfac96`, opt-in twice): `tools/author_bespoke_blend.py` blocks form `posts`
(`canopy_on_posts`, pure, tested): a slab whose top is the measured roof, 0.3 m thick, a 0.3 m square post at every ring
vertex and every 6 m along the edges `[invented sizes]`, each post welded to the slab at its outer corner so a canopy is
ONE island (the prep re-seats it by its feet; house_seat judges it by them), ribbed metal, no walls, no collider (refused
within 60 m of the lap: the nearest canopy is 163 m out). `tools/plan_buildings.py` plan key `canopy_posts` (with
`lidar`): a canopy-class footprint stands on posts only where the lidar measured its roof. Proofs: no other plan names
`canopy_posts` or `lidar` (tested); Del Mar's plan as 0.2.1 committed it rewrites 0.2.1's `buildings.json`
byte-identical, and without `lidar` pass 1's.

### Covered vs not, and the drops

- **All 361 footprints are on the five tiles: 352 measured, 9 bare ground, 0 uncovered.** No further tile is needed.
- **Pass 1's 254 stood: 246 measured, 8 dropped as bare ground, 0 at a class default.** `buildings.json`: 357 rows, every
  height lidar (342 buildings + the Grand Stand's 6 tiers + 9 canopies, Mobil's past the 450 m reach).
- **New bare-ground drops (4, past pass 2's 4):** osm1325614505 (91 m², 59 % ground, 566 m from the lap); osm1325617217
  (27 m², 99 %, 682 m); and two **multi-storey parking garages**, osm1353617974 (2,553 m², 477 m) and osm1427234829
  (3,599 m², OSM 4 levels, layer -1, 619 m): their top decks read 1.2 and 2.9 m UNDER the median ground of a 1-8 m ring
  that spans 18.7..30.0 m and 10.5..25.7 m NAVD88: garages built into a hillside. The median-ground reference cannot
  stand a building into a slope; their downhill faces are owed.

### Measured against the class defaults

The 120 newly measured (pass 2's 124 off the tiles, less 4 drops), the top (flat: p50; pitched: p95) against pass 1's:
- Median change **+1.4 m**, mean |change| **2.1 m**.
- Blocks (commercial, 74): **5.8 m** median (2.5-9.2) against 4.5. Houses (21): **8.3 m** (4.1-11.2) against tops of
  4.4-8.4. Halls (industrial, 6): **11.1 m** (5.1-13.4) against 8.0. Sheds (19): **4.1 m** (2.8-9.2) against 2.8-3.0.
- **Biggest rises:** osm882187417 (a house) 4.4 -> 11.2 m; osm1326361754 (shed) 2.8 -> 9.2; the **John W. Dalton Law
  Offices** 8.0 -> 13.4; osm1321702184 4.5 -> 9.2; four houses 5.2-5.3 -> 9.2-9.6.
- **Biggest drops:** osm1321707184 (house) 7.5 -> 4.5; osm929845974 8.0 -> 5.1; osm882187412 (house) 6.4 -> 4.1;
  **Winner Circle Resort** 8.0 -> 5.8; osm1326361752 and osm929875357 4.5 -> 2.5.
- Named: **Whole Foods Market** 8.0 -> 10.8 (levels 6.5 / 10.9), Milton's 4.5 -> 5.5, 7-Eleven 4.5 -> 4.2.
- All 246 measured of pass 1's stood (the Grand Stand apart): median change **+1.3 m**, mean |change| **1.7 m**; blocks
  5.2 m median (133), houses 8.3 (21), halls 7.9 (19), sheds 4.9 (72). 84 have more than one roof level (recorded, stood at
  the median).
- **The pitched eave changed** (all 72 sheds' and 21 houses' walls, 0.2.1's included): 2 x p25 - p50 (a gable's heights
  spread evenly over its plan), held between p05 and p50, not p10. The first try (`dm_work/v022`, eave p10) failed
  house_seat on osm1321702176, a 28 m² shed whose p10 read 1.03 m (roof 0.55 m over its ground); 2 x p25 - p50 reads
  2.55 m there. A hip's heights crowd its eaves, so this reads a hip's eave low (`[invented]` model: owed).

### Canopies on posts

| OSM | tag | roof (slab top) over ground | posts | stood |
|---|---|---|---|---|
| osm929845988 / 990 / 995 | pavilion, 64 m² each | 3.6 / 3.0 / 3.5 m | 8 each | yes |
| osm929845989 | pavilion, 355 m² | 3.7 m | 22 | yes |
| osm929845991 / 994 | pavilion, 423 / 429 m² | 3.1 / 3.7 m | 40 each | yes |
| osm31816244 | roof, 127 m² | 4.8 m | 8 | yes (413 m from the lap) |
| osm929875359 (Chevron) | roof, 291 m² | 6.5 m | 12 | yes (392 m) |
| osm31817331 (Mobil) | roof, 294 m² | 5.1 m | - | no: 700 m from the lap, past the author's 450 m reach |

### Build: candidate 0.2.2 (Mac, empty workshop `dm_work/v022b`, no force)

ENG = `dm_work/eng` with `assets/textures` md5-equal to this head's (95 files). `dm_work/v022` is the failed first try
(above), kept as it ran.

| | 0.2.1 (pass 2) | **0.2.2 (pass 3)** |
|---|---|---|
| bespoke | 255 stood, 98 dropped (92 past 450 m), 6 for cause | **259 stood** (less 4 bare ground, plus 8 canopies on posts), 98 dropped (92 past 450 m), the same 6 for cause |
| prep house seat | 255 seated, 113 with a foundation down a slope | 259 seated, 112 |
| drive_test | PASS (soft 0, severe 0, bumps 0, kinks 6.68 /km, drops 0, obstructed 0, floating 0) | PASS, every row the same |
| audit_mesh | CLEAN (walls 1,888 v) | CLEAN (1,888) |
| verify_kn5 | PASS | PASS |
| kn5_ground_check | PASS (walls 11, hovering 0, 0/2,292, p95 0.021) | PASS, the same |
| house_seat | PASS (252 judged; lowest roof 1.43 m; buried share > 30 %: 2) | PASS (**256** judged: each canopy one island, the tiers re-joined; contact -0.39..-0.15 m; 0 floating / sunken / buried; lowest roof 1.42 m; > 30 %: 1) |
| road kn5 | 15,774,997 B (md5 d934ef81) | **15,966,502 B (md5 7ae33c38)** |

**Road, ground and audit records byte-identical to 0.2.1's:** `audit.json`, `drive_test.json`, `drive_test.full.json`,
`kn5_ground_check.full.json`, `edge_report.json`, `lm_intake.json`, `mouth_welds.json`, `bridge.spans.auto.json`.
Version 0.2.2.

### Stills (Mac; not in the repo)

`/Volumes/Drive/codex/dm_work/stills/p3_022_*.jpg`, pass 2's seven cameras (against `p2_021_*` / `p2_020_*`), plus
`north_rows` (s 1,635, 119° left, toward Winner Circle and the barns' north rows ~410 m off: the barn rows stand as long
measured gables) and `via_de_la_valle` (s 536, against the line, 144° right, toward Whole Foods 620 m
off: a near hall fills the frame; the Via de la Valle row is behind it, not seen from the lap there).

### Still invented after pass 3

- **No height.** Every stood building is measured; the thresholds that read them are `[invented]` and listed in
  `buildings.lidar.json` `params`; the pitched eave's uniform-gable model (above).
- Form by class (hip / gable / flat / flat with a 0.7 m parapet), the canopy slab and post sizes, the skins, the roof
  colours off the NAIP crop, the area-class rule, the 5 % grade trigger of the seat-edges cut.
- Period: the measure is 2024's (the 1993 stand, the 1991-93 halls); the layout is the 0064 estimate.

### Lake Murray unchanged after pass 3 (Mac)

- `git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/`: empty.
- Trim A/B (`dm_work/lmtrim_e`): byte-identical (`664da93b…`, `b73b70f4…`, `f0c97952…`), logs identical.
- `tests/run_tests.py` (.venv python, a `python` on PATH): **1,291 pass, 8 fail — the known 8** (`test_draft_equiv` x5,
  `test_registry_moves`, `test_bench_pad` x2); 10 tests in `test_lidar_building_heights.py`, all pass.

## PC runbook 0083-3 (rehearse from a clean checkout; NO install — the PC asks Kevin)

1. `git fetch`; a clean worktree at `origin/claude/del-mar-lm` (`ef7d239` or the ledger commit after it),
   `GIT_LFS_SKIP_SMUDGE=1`. No lidar needed: the heights are committed (`buildings.lidar.json` -> `buildings.json`).
2. **ENG = the engine snapshot PLUS airoso's `assets/textures` at the head being built, md5-checked** (rule since 0082-1):
   95 files, any difference stops it.
3. From an EMPTY scratch workshop:
   `SHIP_PROJ=D:/k10-scratch/del_mar_lm_022_reh AIROSO=<worktree> ENG=<eng> bash tools/ship_track.sh del-mar-lm --no-install`.
4. Expect the 0.2.2 column: `[bespoke] ... 259 buildings stood, 98 dropped (92 of them past 450 m of the lap)`, drop
   reasons 5 on a road or kerb + 1 near a road or wall; prep "259 buildings seated"; `[seat-edges] 74 line points
   steeper`; drive_test PASS (soft 0, severe 0, kinks 6.68 /km, drops 0, obstructed 0, floating 0); audit CLEAN (walls
   1,888 v); verify_kn5 + --inis PASS; kn5_ground_check PASS (walls 11, 0/2,292); house_seat PASS (256 judged, 0 / 0 / 0);
   road kn5 15,966,502 B (tangent-only md5 difference is the known noise). Any other row: stop and report it.
5. Do **not** install. Ask Kevin: "Del Mar LM 0.2.2: every building at its 2024 lidar height (the north rows, Via de la
   Valle and the houses now measured; 8 dropped as bare ground, the two hillside garages among them) and the pavilions
   and two fuel canopies as open roofs on posts, over 0.2.1 as `del_mar_fairgrounds_lm`?" Only on his word, from an
   empty `D:/k10-scratch/del_mar_lm` (0.2.1's workshop parked first, as 0.2.0's was).

## Downloads in pass 3

The three approved tiles only. No fourth is needed: every footprint is on the five.

## Owed (after pass 3; start here)

1. **Hillside buildings:** the two multi-storey garages (osm1353617974, osm1427234829) were dropped because their decks
   sit under the median ground of a sloping ring; a downhill-face reference (the ring's low side) would stand them as
   measured.
2. **Multi-level roofs:** 84 measured buildings with more than one level stand at the median (Mission Tower's tower, the
   Wyland Center's 16.7 m level, Whole Foods' 10.9 over 6.5): `--stepped` per building or a level-by-area cut.
3. **The pitched-roof model:** the eave as 2 x p25 - p50 assumes a gable; a hip reads low. Form by class is still
   `[invented]`; a roof form read off the points (one ridge line, two or four planes) would replace both.
4. **The Grand Stand's rise** stood as two steps (9.4 / 16.4 m): a sloped-roof form.
5. **Canopy posts within 60 m of the lap** would need post colliders (none here yet); post spacing / slab `[invented]`.
6. **The look:** the halls' skins (windows, the barns' red roofs and solar panels off the NAIP).
7. **Period:** everything measured is 2024's; the 1987 buildings need an era frame (9).
8. **Walls** (K-rail + debris fence), **furniture** (bleachers, sponsor bridges, palms, the Spanish tower), **the
   boulevard banks**, **direction**: pass 1's owed 2-5, unchanged.
9. **The 5 of today's buildings on the estimated course** stay dropped; **the layout itself**, still estimated, waits on
   one georeferenced 1989-96 frame.
10. **Install:** none from the Mac; 0.2.2 goes to the PC's rehearsal (runbook 0083-3) and Kevin's word.

## PC: rehearsal 0083-3 and the 0.2.2 install (2026-11-07)

- **0083-3 MATCHED** (b26e2b03, `D:/k10-scratch/del_mar_lm_022_reh`, ENG `D:/k10-scratch/eng_dmlm_022` = eng_repro +
  airoso's `assets/textures` at b26e2b03, 95/95 md5-equal): `[bespoke] 259 buildings stood, 98 dropped (92 of them past
  450 m of the lap)`, drop reasons 5 on a road or kerb + 1 near a road or wall; prep "259 buildings seated"; seat-edges 74;
  drive_test PASS (soft 0, severe 0, kinks 6.68 /km, drops 0, obstructed 0, floating 0); audit CLEAN (walls 1,888 v);
  verify_kn5 + --inis PASS; kn5_ground_check PASS (walls 11, 0/2,292); house_seat PASS (256 judged, 0/0/0, lowest roof
  1.415 m); road kn5 15,966,502 B (the Mac's size; md5 c322e85d, tangents); 15 textures, all embedded.
- **INSTALLED on Kevin's word** (2026-11-07, "Install over 0.2.1 (Recommended)"): b26e2b03 from an empty
  `D:/k10-scratch/del_mar_lm` (0.2.1's workshop parked as `del_mar_lm.0.2.1`), ENG eng_dmlm_022; SHIP OK, no force; 0.2.1's
  folder parked in `D:/k10-track-archive/2026-11-07_142030/`; `del_mar_fairgrounds_lm` 0.2.2, kn5 kn5_equiv-equivalent to
  the rehearsal (tangents only); `del_mar_fairgrounds` 0.1.0 still beside it. Records with this note. Not driven yet.
