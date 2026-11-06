---
id: 0083
title: Del Mar on Lake Murray's engine; buildings pass 1
status: in-progress
scope: tracks/del-mar-lm (new), tracks/del-mar (its source, ledger 0064); tools/seat_edges_blend.py, tools/plan_buildings.py (opt-in keys)
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

## Owed (after pass 1; start here)

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
