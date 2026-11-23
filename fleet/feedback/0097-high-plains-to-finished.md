---
id: 0097
title: High Plains to finished (Kevin's calls, Nov 22)
track: high-plains-lm
status: in-train
opened: 2026-11-22
---

# High Plains to finished

Kevin, 2026-11-22: *"let's complete lake murray, sand creek, and high plains"*. He then answered the open calls on the
Mac's calls page ("Yes, start all three") and in the Mac chat said *"go"*. His High Plains answers, verbatim (the page's
option text):

| Call | Answer |
|---|---|
| Add the Full 2.55 mi layout? | Yes, add the Full layout |
| Which High Plains downloads? (track map 1.4 MB, paddock map 5.9 MB, ~4-6 MB lidar for posts 10/11) | All three |
| The two K-rail rows that stand nothing? | Move them off the road and stand them |
| Pit spots: 25 on the racing surface, or 8? | Keep 25 on the racing surface |
| The container stack and the grey roof? | Build the roof as a low shed [invented height] |
| The tyre nose's skin? | Use Milford's tyre skin |
| The paddock buildings' made-up details? | Measure the parapets from the lidar |
| The kerbs' height and end ramps? | Fine as built |
| How finely to read the grass zones? | 15 m cells |
| Rebuild the road at its measured width? | Rebuild at the measured widths |
| The owned asphalt and concrete on the other tracks? | On every track now |

## Round 1 (0.1.9): colliders, the tyre skin, the grass zones

**Drive-through buildings.** In 0.1.8 only post3 and the two canopies had colliders. 0.1.7 had post3 and post8; post8 lost
its own. Measured on the Mac (2026-11-22) on 0.1.8's `loop.blend` with the build's own helpers (`author_bespoke_blend.bvh`
over the config's ground names `["TERRAIN"]`, `ring_points` every 0.6 m on the 0.03 m inset ring, `down_edge` per sample):

| Block | From the line | Longest ground edge under it | 0.1.8 collider |
|---|---|---|---|
| post0, 1, 2, 4, 6, 7, 8, 9, 12 | 14.4-44.0 m | 14.17-14.27 m | none (group limit 14.0) |
| post3 | 15.4 m | 11.68 m | yes |
| post10, 11 | 249.7-262.1 m | 500 m (far ground) | none (past the 60 m reach; the lidar download is for them) |
| osm289311820, 289311823, 289314487, traced white shed | 15.1-39.6 m | 14.17-14.18 m | none (default 8 m) |

Every one sits on the TERRAIN grid's diagonals (a 10 m grid: 14.14 m, plus slope). Both block groups now declare
`collider_tri_m` 14.5, the limit the two canopies already stand on with drive_test reading 0 floating (ledger 0094
round 2). Distances are from `data/centerline.local.json` through `paint_shapes.to_xz`.

**The tyre skin.** `texture_overrides["1WALL_TECPRO"]` binds `assets/textures/tyre_wall_diffuse.png` (CC0, made by
`tools/make_bespoke_assets.py`), as on Milford. High Plains' only Tec-Pro row is `1WALL_TECPRO_TYRES_10`
(`data/split_manifest.json`), so nothing else changes skin. `ship.json sync_in.assets` carries the file.
`tests/tools/test_milford_furniture.py::test_keys_are_opt_in` now expects it on High Plains.

**The grass zones.** `grassfx_zones.cell_m` 30 -> 15, `max_rects` 48 -> 123: ledger 0089's measured reading at 15 m with
every rectangle kept (1,339 of the 1,986 card spots inside a zone, 1,716 within the fade; 906 / 1,186 at 30 m).

Version 0.1.8 -> 0.1.9.

### Runbook 0097-1 (PC): rehearse 0.1.9, NO install without Kevin's word

1. Fresh empty workshop, branch `claude/hp-finish-20261122` at the commit named in the Mac's message, `AIROSO_NUMPY_PY` =
   the lidar venv, rehearsal only (`SHIP_PROJ` scratch, `--no-install`).
2. Report against 0.1.8's install build:
   - `data/bespoke.report.json` blocks: `collider` per key. Expected true: post0-4, 6-9, 12 and the four buildings above,
     plus 38 / 8 post colliders on the canopies. Expected false: post10, post11 and the far blocks.
   - drive_test: floating walls (expect 0), severe, kinks, bumps; house_seat; every other gate row, same or not.
   - The GrassFX step: the zone count and the spots covered.
   - kn5: size against 22,156,060 B; `data/kn5_textures.json` names `tyre_wall_diffuse.png`.
3. Push the records to the branch (no force). The Mac merges. Kevin's word before any install.

## Still to do (rounds 2+)

- The road at its measured width (ledger 0059: 10.5 +/- 0.6 m; 11.7-12.0 m on the front straight).
- The Full 2.55 mi layout (4,100 m).
- K-rail rows 3 and 8 moved off the road and stood (row 3 s 262-299 over the road's edge, row 8 s 212-236 on the racing
  surface).
- The 11 x 23 m grey roof east of the containers as a low shed [invented height].
- Parapets read from the 2018 lidar (a G10 job, `tools/lidar_roof_forms.py`).
- Pit-exit merge paving (ledger 0093), the kerb stripe at R s 2,673-2,681 (ledger 0081).
- Downloads: the track map, the paddock map, the lidar for posts 10/11 (sources named when fetched).
- The owned concrete (the asphalt is in since 0.1.8).

## PC rehearsal (2026-11-22, 564c3152): High Plains 0.1.9 green, not installed

Runbook 0097-1 as written: an EMPTY workshop (`D:/k10-scratch/high_plains_lm_0109_reh`), worktree
`D:/k10-worktrees/hp-finish` on `claude/hp-finish-20261122` 564c3152, ENG `eng_hplm_0109` (= `eng_hplm_0108` +
`tyre_wall_diffuse.png` md5 c7f4764d + the branch's `SOURCES.txt`; the other 103 textures md5 = the branch's),
`AIROSO_NUMPY_PY` the lidar venv, `SHIP_PROJ` scratch, `--no-install`. 19:32-19:35: **SHIP OK**, no force, no FATAL, every
gate green. Compared with 0.1.8's install build (`D:/k10-scratch/high_plains_lm`, Nov 20).

- **Colliders** (`data/bespoke.report.json`), exactly as expected:
  - true: post0, post1, post2, post3 (already true in 0.1.8), post4, post6, post7, post8, post9, post12, osm289311820,
    osm289311823, osm289314487, traced_white_w_of_osm289311820; the canopies keep 38 (osm289311821) and 8
    (traced_pit_entry_canopy) post colliders.
  - false: post10, post11, osm289311824, osm289316523, traced_container_row.
  - So 13 more collider objects: walls 22 -> 35 objects, 13,844 -> 14,264 wall vertices, split main 99,945 -> 100,105 positions.
- **drive_test:** floating furniture 0, walls floating over ground 0 (worst +0.0 m), severe steps 0, bumps 0.0 /km,
  vertex bumps 2, slope kinks 0.62 /km: all as 0.1.8.
- **house_seat:** 21 buildings seated, 1 foundation down a slope (0.02 m); floating 0, sunken 0, buried 0, lowest roof
  1.639 m: as 0.1.8. **kn5_ground_check** walls: seat gap median -0.235 -> -0.239 m, p95 -0.168 -> -0.150 m, hovering 0.
- **Gate rows:** 180 / 180; four differ, all from the changes above: the split positions, the grassfx line, AUDIT walls
  13,844v -> 14,264v and the walls seating row (22 -> 35 objects). AI lines the same.
- **GrassFX:** `105 x 39 cells of 15 m; cells per look {'B': 414, 'C': 7}; 123 rectangles, 123 kept` (0.1.8: 53 x 20 of
  30 m, 32 kept). B 31 -> 118 rectangles (6.84 -> 9.31 ha), C 1 -> 5. Of 0.1.5's 1,986 card spots (its
  `source/bespoke/shrubs.json`, lon/lat into the track frame, kn5 z = -N): **1,339 inside a B box, 1,716 within the fade**
  (0.1.8: 906 / 1,186), ledger 0089's numbers exactly. `ext_config.ini` 6,635 -> 15,067 B.
- **kn5:** 22,156,060 -> 22,161,329 B (+5,269), kn5_equiv DIFFERENT from materials on, as expected. High Plains writes no
  `data/kn5_textures.json` (0.1.8 did not either), so read in the kn5 and the build instead: the kn5 names
  `tyre_wall_diffuse.png` (0.1.8: `tecpro_diffuse.png`), `high_plains.ini` `RES_0_TEXTURE=tyre_wall_diffuse.png`, and
  `build/texture/` holds `tyre_wall_diffuse.png` in place of `tecpro_diffuse.png`.
- Version 0.1.9 in `ui_track.json`. Not installed: Kevin's word first.

## Installed (PC, 2026-11-22): High Plains 0.1.9 as high_plains

Kevin's standing word on the PC ("Yes and I always want newer builds", 2026-11-09) and his Nov 22 word to the Mac about
the finish builds ("When they're done, install them").

- Built from an EMPTY workshop (`D:/k10-scratch/high_plains_lm`, 0.1.8's kept as `high_plains_lm.0.1.8`) at 9810abc7
  (= 564c3152 + this ledger), ENG `eng_hplm_0109`, `AIROSO_NUMPY_PY` the lidar venv; 19:44-19:47 SHIP OK, every gate
  green; 0.1.8 parked in `D:/k10-track-archive/2026-11-22_194738/`.
- The same as the rehearsal above: 180 / 180 gate rows; kn5 22,161,329 B, EQUIVALENT (tangents only: 31,044 values, max
  1.79e-07); AI lines the same; data JSON differs in paths only; road-wear atlases md5 the same (the macro fb88cea1, as
  0.1.8's). AC's folder equals the build but for `ui_track.json`'s name dash (as every install).
- Menu picture: s0 of 6 at -0.3 EV, the camera of 0.1.8's to the centimetre; no collider shows in it. The old picture is in
  `D:/k10-track-archive/2026-11-22_194834_previews/`.
- fleet/ac-installed.json: high_plains 0.1.9 (sha 564c3152). Not driven.

## Round 2 (0.1.10, Mac, 2026-11-22): the measured widths, the stripe, the roof, the pit-exit paving, the owned concrete

Kevin's round-2 answers are the table at the top. Every number below was read on the Mac off the committed 0.3 m photo
(NAIP 2023-09-28, `source/road_wear/naip_2023_030_hp.png`, public domain) unless it says otherwise; built numbers are from
Mac builds with Blender 4.2.9 from an EMPTY workshop (`SHIP_PROJ` scratch, `--no-install`, ENG = the engine-july snapshot +
the branch's `assets/textures`), compared with a Mac build of 0.1.9 (7e31699c) made the same way (its kn5 22,161,150 B
against the PC's 22,161,329 B).

### 1. The road at its measured width

The inherited constant 12.0 m (`default_width_m`, the source track's widths) is replaced along the whole lap by the
pavement edge read off the photo:

- **The reading** (`source/edges/measure_widths.py`, numpy + Pillow): every 1 m of 0.1.9's built line, both sides, every
  0.1 m from 2 to 10 m off it. The edge is the first outward step in ground-ness (max((R+G)/2 - B, 2G - R - B - 5): prairie
  and dirt are yellow, the draws green; asphalt, white line and kerb blue are neither), at least 12 over 0.2-1.0 m to a
  ground level of 30: the outer side of the white edge line or the asphalt's end. Inside ledger 0081's 20 kerb runs, the
  outer end of the run's first paint band instead (the kerb is the paved surface's edge). Not kept: five mouths where
  another road's paving runs on (the short-course link, s 1,335-1,395 R; the link road off the hairpin, s 2,595-2,672 R;
  the Full course's fork, s 2,690-2,752 L, and merge, s 2,812-2,852 L; the pit-in lane, s 2,992-3,082 L), one stretch
  rejected by eye (L s 1,715-1,772: dull grass read as asphalt), steps in the search's last metre, and outliers over 0.4 m
  off their neighbours' median. 5,355 readings kept (`edge_evidence.json`); every reading drawn over the straightened road
  in `widths_strips_2023_030.jpg`; every station in `widths_measured.json`. All thresholds are [invented] reader tuning.
- **The build**: `lm_intake.edge_retrace` with `tools/edge_retrace.py`'s new opt-in mode **"measured"** (mode "agree"'s
  in-or-out machinery on one sensor): each side goes to its reading, the line moves by (left - right) / 2 (-2.02..+1.25 m),
  the width is left + right; unread rows are interpolated within 60 m; `erode_m` 3 / `smooth_m` 4 [invented] (the tool's
  10 / 8 left the edges -0.47 / +0.80 m off the readings at p5 / p95); never onto the pit wall (rails clamp; none bound).
- **Built widths** (`data/gate_centerline.json`, 1,074 rows): p5 / p25 / p50 / p75 / p95 **10.85 / 11.17 / 11.48 / 12.40 /
  13.11 m**, min 10.05 (Drifter, s 2,624), max 14.30 (Drifter, the fork's flare). Per OSM way:

  | Way (built s) | p5 | p50 | p95 |
  |---|---|---|---|
  | Full West, the front straight (0-192, 3,035-3,210) | 12.01 / 12.49 | 12.33 / 12.62 | 12.49 / 12.97 |
  | unnamed 289314485, T1-T3 (195-771) | 10.85 | 12.41 | 13.98 |
  | Short North (774-1,355) | 10.88 | 11.25 | 11.45 |
  | Bikers Berm (1,358-1,664) | 10.97 | 11.48 | 12.16 |
  | Niagara (1,667-1,921) | 10.87 | 11.37 | 12.97 |
  | Dannys Lesson (1,924-2,240) | 10.57 | 11.26 | 11.86 |
  | High Plains Drifter (2,243-2,714) | 10.86 | 11.76 | 12.87 |
  | Prarie Corkscrew (2,717-3,032) | 10.70 | 11.61 | 13.33 |

  The straights' pavement is 11.25-11.37 m to the outer side of the edge lines; their centres are 10.5 m apart there
  (s 1,100: lines at -5.8 / +4.65 m), ledger 0059's 10.5 m. Built edge against the readings: median +0.03 m (left) /
  +0.01 m (right), p5 / p95 -0.27 / +0.43 and -0.28 / +0.39 m, 86 / 88 % within 0.3 m. Lap 3,204.7 -> 3,209.7 m.
- **What hangs off the edges**: the 20 kerbs stay where their paint is (absolute, `kerb_section.edge_delta`); with the
  lane now ending at their outer edge, 19 of them lie over the lane (`kerbs.built.json` out_vs_ribbon_edge -0.39..+0.48 m;
  L s 2,843, in the merge's mouth, +1.94 m). The 1.25 m wheel path now rides five of them: drive_test slope kinks 0.62 ->
  **1.87 /km** (6: L s 1,699-1,702, R s 627-630, L s 2,634; the worst 4.57 %/m), every one on a kerb; vertex bumps 2 -> 0;
  severe, bumps, floating, obstructions 0. The rails: 0 modules left out but rows 3 / 8 (below); the pit wall 3.5 m clear
  of the edge. The grid and pits: 50 cars inside the road, nearest edge 2.07 -> 2.27 m. The paint: read-back 0.00 mm, the
  S/F band 11.7 m as before. road_wear_check tone r 0.8587 -> 0.874 (the road now lies on the photo's asphalt).

### 2. The Full layout: not built this round

See "Still to do (round 3)" below: what it takes, and what is on disk for it.

### 3. K-rail rows 3 and 8: not moved, not stood (Kevin's call needed)

Their "blue sections" are the kerbs' paint, not barriers. `paddock_row_3` (s 260-299, -6.48..-6.66 m off the built line)
lies on the blue / yellow edge stripe R s 263-299 (its paint -6.05..-6.95 m); `paddock_row_8` (s 210-237, +4.87 m) on the
blue / white kerb L s 212-239 (paint from +5.38 m). The photo shows no K-rail off the road beside either. Moving them onto
"the nearest measured ground where their blue sections show" would stand barriers that are not there, so neither moved;
each row's `_round2` says why, and the author still stands nothing over the road (0 of 12, 0 of 6).

### 4. The grey roof: a low shed of invented height

Traced in the container stack's own frame (`buildings.race.json` `traced_grey_roof_e_of_containers`): the uniform grey
(mean 113-127) from the stack's east wall to a dark band 9.9 m east, and from 3.2 m north of the stack's south end to its
north edge (25.0 m): **21.8 x 9.9 m (215 m2)**; ledger 0093 read about 11 x 23 m. Flat, 2.6 m **[invented]** (the stack's
own, itself [invented]), roof "tan" by plan_buildings' rule (mean 119.3, R - B 16.9). A 2.5 m dark band along its north edge
would be a 3.3 m roof's shadow at the photo's sun, but a bright patch interrupts it and the dark runs on past the roof's east
edge: not used. house_seat: 21 -> 22 buildings, 0 floating / sunken / buried.

### 5. Parapets: a G10 job, not run (it needs a download)

`tools/lidar_roof_forms.py` needs laspy (not in the Mac venv) and 2018 points over the paddock (the Mac holds only the
posts 10/11 node). The job is written: the Mac's `g10/jobs-20261122/hp/` (`RUN.txt`, `hp_paddock_ept.py`): plan (metadata
and HEAD sizes), fetch, merge to UTM 13N, extract, fit, over `buildings.race.json` + `posts.race.json`. Steps 1-2 reach
s3-us-west-2.amazonaws.com (CO_Eastern_B3_2018 EPT): Kevin's word first; the plan step prints the exact bytes (estimate a
few MB). High Plains' flat roofs are the container stack and the grey roof; the others are gables.

### 6. The pit-exit merge paving

`scenery.bespoke.pads` `pit_exit` (appended, so the old PADAPRON numbers hold): the lane from the first pair outside the
paddock sheet (s 190) round T1-T2 to its merge at s 455, every 5 m, its edges read off the photo
(`source/edges/measure_pit_exit.py` -> `pit_exit_strip.json`: the asphalt run past the lap's own and a grass strip, paint
kept out): **3.6 / 4.4 / 9.0 m wide** (p5 / p50 / p95; the 9-10 m rows are the gore's apron, s 195-210); the last pair the
lap's own left edge (7.05 m) and the joined run's end (12.95 m). Built: 56 cells, 1 left out (over the road).

### 7. The kerb stripe at R s 2,673

The port's own kerbs file `source/edges/kerbs.lm.json` (route.kerbs_file; tracks/high-plains' kerbs.json untouched) is the
source's but for that run: its first five edge points moved out by the paint each stands on (`retrace_stripe_2673.py`:
paint centre less the band's -0.40 m): **+2.30, +1.80, +1.35, +0.95, +0.40 m**; the other nine read within 0.3 m and stay.
in_m / out_m and the ends unchanged. Built: 20 runs, 578 -> 579 m.

### 8. The owned concrete

`assets/textures` holds the owned pair (`concrete_plain_diffuse.jpg` d77c7ca9, 262,056 B; `concrete_plain_normal.jpg`
2692b423, 370,970 B; tools/make_owned_surfaces.py, CC0; already in licenses.json and SOURCES.txt). High Plains' one concrete
row is the edge strip (1KERB_sidewalk, the pbr row's mined building_diffuse.jpg): `texture_overrides["1KERB_SIDEWALK"]`
binds the pair, `ship.json` syncs it. Road wear: `detail.1KERB_SIDEWALK.from` concrete_plain_diffuse.jpg, clipped 0.0 %
(its mean is the replaced file's, so m0 holds); `building_normal.jpg` leaves the kn5, `concrete_plain_normal.jpg` enters.

### Shared files touched

`tools/edge_retrace.py` (mode "measured", opt-in: widen and agree as before), `tests/tools/test_edge_retrace_measured_surface.py`
(the opt-in list now names High Plains). New: `tests/tools/test_high_plains_round2.py`. Not touched: assets/licenses.json
(the concrete pair's row exists), fleet/ac-installed.json.

### Mac build against 0.1.9 (both from an empty workshop)

SHIP OK, every gate green, no force. kn5 22,161,150 -> **22,270,313 B** (Mac); split main 71 -> 72 meshes, 100,105 ->
99,419 positions; AUDIT roads 13,356 -> 13,164 v, grass 72,323 -> 71,380 v, walls 14,264 -> 14,286 v; kn5_ground walls 35,
seat gap median -0.24 / p95 -0.15, hovering 0; road over ground p95 +0.021 m; house_seat 22 judged, lowest roof 1.639 m;
the AI line 2,137 -> 2,140 points, lap 98.9 -> 96.0 s (generated); the circuit dummies at s 12.2, sectors s 1,082 / 2,152.

### Runbook 0097-2 (PC): rehearse 0.1.10; a green rehearsal installs and merges (Kevin's standing word)

1. EMPTY workshop, a worktree of `claude/hp-finish-r2-20261122` at the commit named in the Mac's message, ENG
   `eng_hplm_0110` = `eng_hplm_0109` + `concrete_plain_diffuse.jpg` (md5 d77c7ca9c8faa202951821133628a4e4) and
   `concrete_plain_normal.jpg` (2692b4231be5d2c24c6b4f0f3705bb84) from the branch's `assets/textures` (every other texture's
   md5 = the branch's), `AIROSO_NUMPY_PY` the lidar venv, `SHIP_PROJ` scratch, `--no-install`:
   `SHIP_PROJ=<scratch> AIROSO=<worktree> ENG=D:/k10-scratch/eng_hplm_0110 bash tools/ship_track.sh high-plains-lm --no-install`.
2. Read, against 0.1.9's install build (180 gate rows, kn5 22,161,329 B):
   - `[lm_intake] edge retrace (naip, measured, ...)`: widths 12.00..12.00 -> 10.05..14.30 m, the line moved -2.02..+1.25 m.
   - `[kerbs] 20 kerb runs, 579 m`; `[bespoke] pad pit_exit: 56 cells, 1 left out`; 22 blocks; rows 3 / 8 still 0 of 12 /
     0 of 6; the four pit-lane paint items as 0.1.9 (`pit_out_gore` clip 14.5 m as before).
   - drive_test: slope kinks about 1.87 /km (all on kerbs), severe / bumps / floating / obstructions 0; audit CLEAN;
     kn5_ground PASS; road_wear_check PASS with `detail.1KERB_SIDEWALK.from` concrete_plain_diffuse.jpg; house_seat 22.
   - Every gate row, same or not, and the kn5's bytes (Mac: 22,270,313).
3. Green: install as `high_plains` (0.1.9 parked), the records and menu picture to the branch (no force); the Mac merges.
   Red: records only, no install.

## Still to do (round 3)

- **The Full 2.55 mi layout (4,092 m on OSM).** Its extra pieces are To Hell On A Bobsled (132189631, 568 m) and Ladder To
  Heaven (289314483, 433 m): they leave the West lap at the fork (OSM node 1454637759, built s ~2,709) and rejoin it at node
  1454637805 (s ~2,831, Prarie Corkscrew's vertex 7); the Full layout skips the West's first 130 m of the Corkscrew. On disk
  for it (no download): the ten ways' OSM snapshot of 2026-10-28 and its 3DEP (heightfield to lat 39.74124, the north
  section's corridor) from ledger 0059's full-course build, on the Mac (outside git). Not on disk: any photo north of lat
  39.73887 (the north section's top ~110 m; the 0.3 m crop stops at 39.73681), so its widths there could only be carried
  from the measured stretch below. What the build needs (Pikes Peak 0.2.0's road, ledger 0085): the north loop as a
  connector with junction pads at a fast Y fork and a merge, the heightfield widened north (lm_intake.heightfield "port"),
  `race.laps` for the Full lap, per-layout AC nodes for `race_start` (today's circuit dummies are single-layout), a
  second AI line, road wear per layout, and every gate on both layouts.
- Parapets: run the G10 job above on Kevin's word to the download.
- K-rail rows 3 / 8: Kevin's call (remove them from the config, or leave them standing nothing).
