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
  lane now ending at their outer edge, every one starts inside it (`kerbs.built.json` in_vs_ribbon_edge -0.16..-1.89 m) and
  ends within -0.39..+0.48 m of it, but L s 2,843 (+1.94 m, in the merge's mouth). The 1.25 m wheel path now rides three of
  them: drive_test slope kinks 0.62 -> **1.87 /km** (6: L s 1,699-1,702 on the kerb L s 1,681-1,716, R s 627-630 on
  R s 622-638, L s 2,634 at L s 2,636-2,666; the worst 4.57 %/m), every one on a kerb; vertex bumps 2 -> 0;
  severe, bumps, floating, obstructions 0. The rails: 0 modules left out but rows 3 / 8 (below); the pit wall 3.5 m clear
  of the edge. The grid and pits: 50 cars inside the road, nearest edge 2.07 -> 2.27 m. The paint: read-back 0.00 mm, the
  S/F band 11.7 m as before. road_wear_check tone r 0.8587 -> 0.874 (the road now lies on the photo's asphalt).

### 2. The Full layout: its extra pieces measured, not built

The data half is in the port (`source/full/`, nothing reads it yet): the OSM snapshot of the ten raceway ways
(`osm_full_course.json`, 2026-10-28, ledger 0059's), 3DEP beside the north section (`corridor_3dep_north.json`, 295
stations of native samples every 6 m x 5 m, +-60 m), and `measure_north.py` -> `north_loop.json`: To Hell On A Bobsled +
Ladder To Heaven from the fork (node 1454637759) to the merge (node 1454637805) in the engine's connector shape, **1,001 m**,
502 points every 2 m, both ends within 6 m of the West lap's built line. Widths read as the lap's (the same reader, the 0.3 m
crop where it reaches, the z18 0.46 m photo to lat 39.73887): both sides read over **469 m, widths p5 / p50 / p95 10.6 /
11.2 / 13.0 m** (the centre 2.4 m left to 1.7 m right of OSM's); **carried 11.2 m** (that median, marked "carried" per point)
over the other 533 m: 346 m where neither side reads (the top of the loop is in no photo) and 188 m with one side only (a
gradual verge with no edge line that the step reader does not catch). Heights 1,514.1-1,536.0 m (3DEP, a 9 m mean). The
build itself is round 3 (below).

### 3. K-rail rows 3 and 8: not moved, not stood (Kevin's call needed)

Their "blue sections" are the kerbs' paint, not barriers. `paddock_row_3` (s 260-299, -6.48..-6.66 m off the built line)
lies on the blue / yellow edge stripe R s 263-299 (its paint -6.05..-6.95 m); `paddock_row_8` (s 210-237, +4.87 m) on the
blue / white kerb L s 212-239 (paint from +5.38 m). The photo shows no K-rail off the road beside either. Moving them onto
"the nearest measured ground where their blue sections show" would stand barriers that are not there, so neither moved;
each row's `_round2` says why, and the author still stands nothing over the road (0 of 12, 0 of 6). The still
`source/edges/rows_3_8_on_the_kerbs_2023_030.jpg` draws both rows (red) and the real paddock rows near them (green) over
the photo: `paddock_row_5`, 11.6 m out at s 207-250, is the pit-exit lane's own K-rail and already stands.

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
(the opt-in list now names High Plains). New: `tests/tools/test_high_plains_round2.py` (11 tests). Not touched: assets/licenses.json
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

- **The Full 2.55 mi layout (4,092 m on OSM): the build** (its pieces are measured, item 2 above). Its extra pieces are To Hell On A Bobsled (132189631, 568 m) and Ladder To
  Heaven (289314483, 433 m): they leave the West lap at the fork (OSM node 1454637759, built s ~2,709) and rejoin it at node
  1454637805 (s ~2,831, Prarie Corkscrew's vertex 7); the Full layout skips the West's first 130 m of the Corkscrew. On disk
  for it (no download): the ten ways' OSM snapshot of 2026-10-28 and its 3DEP (heightfield to lat 39.74124, the north
  section's corridor) from ledger 0059's full-course build, on the Mac (outside git). Photo coverage: the 0.3 m crop holds 127 m of
  Bobsled's 568 m and 69 m of Ladder's 433 m; the committed z18 photo (0.46 m, `tracks/high-plains/source/
  naip_2023_hp_z18.png`, to lat 39.73887) 376 m and 307 m; the top 318 m of the two are in no photo on disk, so widths there
  could only be carried from the measured stretch below (or a crop fetched on Kevin's word). What the build needs (Pikes Peak 0.2.0's road, ledger 0085): the north loop as a
  connector with junction pads at a fast Y fork and a merge, the heightfield widened north (lm_intake.heightfield "port"),
  `race.laps` for the Full lap, per-layout AC nodes for `race_start` (today's circuit dummies are single-layout), a
  second AI line, road wear per layout, and every gate on both layouts.
- Parapets: run the G10 job above on Kevin's word to the download.
- K-rail rows 3 / 8: Kevin's call (remove them from the config, or leave them standing nothing).

### Round 2 addendum (Mac, 2026-11-22): rows 3 and 8 removed

Round 2 found the two auto K-rail rows `paddock_row_3` (R s 263-299, -6.48..-6.66 m) and `paddock_row_8` (L s 212-239,
+4.87 m) were read off the photo's blue sections, and those are the kerb paint, not barriers. The photo shows no K-rail
off the road beside either. Kevin's answer ("Move them off the road and stand them") assumed they were K-rails; with
his later word to decide on my own and his rule "I just want real", the Mac removed both from the config rather than
invent barriers (`scenery.bespoke._rows_3_8_doc` says why; their entries are in git history at 165ab3f9).
`test_circuit_race_furniture` now expects 13 paddock rows; `test_high_plains_round2` checks they are gone.

## Round 3 (0.1.11, Mac, 2026-11-22): the Full layout

Kevin's answer on the calls page, "Yes, add the Full layout", built: High Plains is now two layouts on one road kn5
(fleet/LAWS.md L8), **West** (the 2.0 mi course every build until now drove, its id `full` renamed `west`:
tools/layout_dummies and scripts/ac/track_folder reserve `full`, which drops a layout's name from a multi-layout menu entry)
and **Full** (`full_course`, 2.55 mi: the West course to the end of High Plains Drifter, straight on up To Hell On A Bobsled,
round the north hairpin, down Ladder To Heaven and left onto the Prairie Corkscrew). Each loads the road kn5 and its own
nodes-only spawn kn5 (`models_west.ini`, `models_full_course.ini`); Content Manager lists "doooom Colorado - High Plains
Raceway — West" and "— Full". Built numbers are from Mac builds with Blender 4.2.9 from an EMPTY workshop (`SHIP_PROJ`
scratch, `--no-install`, ENG = the engine-july snapshot + the branch's `assets/textures`), compared with a Mac build of 0.1.10
(27ffccf3) made the same way.

### 1. The north loop, measured to the top

`source/full/north_loop.json` (round 2's `measure_north.py`) now reads three photos, all NAIP 2023-09-28 of the same item:
the 0.3 m crop, the committed z18 photo (0.46 m, to lat 39.73887) and, new, the z18 tiles above it
(`source/full/naip_2023_hp_north_z18.png`, x 55414-55415 / y 99488-99489, to lat 39.74099, public domain; the orchestrator's
fetch), read with the committed z18 as one mosaic (the seams are clean). **The top 318 m is measured**: 160 rows off the north
tiles, built widths p5 / p50 / p95 **10.71 / 11.47 / 12.68 m**; no row from s 376 to s 694 is carried. Over the whole loop,
**810 m read on both sides** (widths p5 / p25 / p50 / p75 / p95 10.6 / 10.9 / 11.2 / 12.15 / 13.0 m), **192 m carried**
[invented]: the fork's mouth (s 0-18, inside the FORK pad, dropped by the cut), the merge's mouth (s 988-1001) and 165 m of
verge with an edge line on one side only (s 218-352, 716-736). Two changes to how the measurement becomes a line, both
[invented] tuning:
- a carried row takes each edge interpolated between the nearest rows read on both sides (held past the last), not round 2's
  median width about OSM's centre: that jumped 1-2 m sideways at every measured / carried boundary, and the first Full build
  read 36 severe steps there (lap s 2,885-3,375, 0.09-0.12 m); both edges then run through a 10 m mean;
- the centre line runs through a 4 m Gaussian (each end padded straight on its own last 5 m, so the ends stay put: 0.15 /
  0.05 m): OSM's nodes stand 20-25 m apart and turned up to 23 deg at a node on the hairpin; now at most 4.9 deg per 2 m.
Heights are round 2's (3DEP beside the line, 1,514.1-1,536.0 m). `source/full/make_connectors.py` writes it as the port's
own connector `full_north` (`connectors.full.json`, `lm_intake.connectors_file`), painted with the mainline's own edge lines
(white, 0.55 m in, 0.12 m; no yellow centre line on a circuit).

### 2. The heightfield, north

`data/heightfield.npy` is now ledger 0059's full-course 3DEP grid (the same 40 m stage, west / east / south edges as the
West-only grid, north to lat 39.74124: 40 x 25 samples, was 40 x 15), kept on the Mac outside git until now. Against the
native 3DEP samples beside the north section (`corridor_3dep_north.json`, 7,375 samples) it reads -0.08 +- 0.35 m; the grid it
replaces -0.21 +- 0.39 m over its part of them. It moves the West's far ground too (sd 0.77 m at the old nodes, a 40 m grid
sampled on another lattice); the road's own heights are its profile's, not the grid's.

### 3. The fork: a measured pad (a fast Y)

High Plains Drifter runs straight on into To Hell On A Bobsled while the West course bends right, so the two roads' outer
edges are one line: no lateral line of the connector crosses the West lap's edge and the mitre weld refused it (the first
build: "a lateral line stops > 25.0 m short of the host edge"). NAIP shows the fork as one pavement (the flare, the gore's
tip), so it is built as Pikes Peak's and Sand Creek's junctions are (`lm_pads`, tools/lm_pads_blend.py):
- **the outline** (`source/full/measure_pads.py` -> `source/pads/FORK.json` + `FORK.png`): the 0.3 m crop's ground-ness
  (measure_widths' rule) under the threshold midway between the West lane between the cuts (15.3) and the verge (46.9): 31.1;
  closed / opened, small holes filled, both ribbons united in (10.2 m2 of the lap's, 1.8 m2 of the connector's), clipped to the
  declared box [authored, by eye on NAIP] and split at the cuts: **1,406 m2**, 295 points;
- **the cuts**: West v896 (s 2,682, before the flare) and v922 (s 2,759, past the gore's tip), the node v907; the north loop
  is cut at the box edge 36 m up Bobsled (`route.street_junctions.pad_arms`) and welded in as the arm;
- **the deck**: no lidar over the fork is on disk, so nothing measures the paving's height. New opt-in
  `lm_pads.deck.fill "membrane"`: the deck keeps the West lap's own ribbon surface (its profile and lidar camber) and the arm's
  row exactly, and the paving between them (the flare, the arm's approach) is the smoothest surface that meets both, the
  discrete Laplace equation on the deck's own edges [invented fill]. Built: 1,336 vertices / 2,481 faces, 1,441.5 m2 (the
  outline as built: the lap's edge and lip added); 777 vertices pinned on the ribbon, 9 on the seams, 550 free (89 sweeps;
  they moved up to 0.23 m off the plain inverse-distance fill); seam max 1.2 mm; no K-rail (no road the build does not
  complete meets it).

### 4. The merge: a welded mouth, and the T13 kerb re-traced

The merge is a 46.1 deg T (`tools/trim_connectors.py` cuts the north loop at the West lap's edge, landing on its cambered
deck, `route.trim_host_bank`; `tools/weld_mouths_blend.py` welds it, reading the host deck off its triangles,
`route.weld_exact_deck`; `gap_mouths` opens the West's edge strip across it). Its inside corner is the traced T13 kerb
(ledger 0081's L s 2,843-2,856, 1KERB_circuit_8):
- as a pad, verify_pads P5 refuses it (no curb over a pad's pavement: 18 kerb triangles; the kerb begins where Ladder's east
  edge meets the Corkscrew, so no cut keeps it out);
- welded, verify_mouths NOTCH refused it too at first: the run was laid at one in / out along the West lap's edge, and its west
  end (with the engine's 4 m end ramp) stood 1.3-3.3 cm over the road along the mouth's last 1.25 m. On NAIP its paint wraps
  round the corner. `source/edges/retrace_kerb_2843.py` re-traces it by round 2's own rule (retrace_stripe_2673.py: each edge
  point moved across by the paint it stands on, MOVE_MIN_M 0.3): **v0 +2.55 m** (paint 1.3-3.6 m out), **v1 +1.05**, v2-v4
  kept, v5-v7 -0.50 / -0.55 / -0.55 (paint further in). in / out, the ends and the other 19 runs unchanged. The kerb's west end
  now follows the paint off the lane; 9 of its section reads find no ROAD under them (the corner's grass; a miss keeps the lane
  edge's height, author_kerbs' rule).
The bellmouth on the west side and the paved fillet behind the kerb are not built (the Full lane does not use the west corner;
the east corner is the kerb): owed, `route.mouth_returns` at radii tools/mouth_radii.py reads off NAIP.

### 5. The Full lap

`race.laps.full` (scripts/geometry/race_lap.py, author step `race_laps` -> `data/lap.full.json`): the West lap v0-v900, across the
FORK pad, the north loop `full_north#0#0` v0-v478, through the merge, the West lap v951 round to v1072. The two joins (`via`)
are cubics on the pieces' own tangents [authored shape]: the fork's from West v900 onto the north loop's own line at its point
13, then that line to the box edge (48.4 m chord; the lap's tightest radius there 203 m: the Full goes straight on); the
merge's from the north loop's v478 onto West v951 (16.7 m chord, tightest radius 16.7 m: the widest cubic whose lane edges and
outer wheel paths stay on the built road and the T13 kerb). **Lap 4,085.7 m** (OSM's Full course 4,092 m; published 2.55 mi
= 4,104 m); the West lap 3,209.7 m as 0.1.10.

### 6. Each layout's start, grid and pits

New opt-in `race_start.layouts` (scripts/geometry/circuit_start.py, tools/circuit_dummies_blend.py): both layouts start at the
painted line, so the declared line, the 25 measured grid slots and the 25 pits are planned on each layout's own line (West:
the lap; Full: race.laps.full), every height read off the built road, the same self-checks, and written as
`data/dummies_<id>.json` (tools/layout_dummies.py's schema) for each spawn kn5 (`spawn_kn5`); the road scene carries no AC_*
node (verify_kn5 (a)). West: the line at s 12.2 of 3,209.7 m, sectors s 1,082 / 2,152 (as 0.1.10). Full: the line at s 12.2
of 4,085.7 m, sectors s 1,374 / 2,736 (its thirds). verify_kn5 judges each spawn kn5 with race_start's own rows on its own
line (fleet/GATES-CHANGELOG.md 2026-11-22: wiring, no threshold moved): both 51 facing nodes at local +Z . travel +1.00,
50 START / PIT cars inside the road, nearest edge +2.27 m. Spawn kn5s 5,058 B each.

### 7. The rest of the build

- **AI lines** (generated drafts, write_ai_line): West 2,140 points over 3,210.7 m (est 96.0 s, as 0.1.10); Full 2,725 points
  over 4,087.8 m (est 130.0 s).
- **Maps**: West `map "lap"` (the mainline alone); Full new opt-in `map "race_lap"` (tools/make_map.py: its own
  data/lap.full.json; "lap" keeps its meaning, which Lake Murray's Speedways use).
- **Road wear**: the atlas re-planned (100 cells of 64 m + 8 m margin, 61 % of the 4,096 px atlas) for the West road, the
  north loop and the FORK deck; tone r 0.8741 -> 0.8813 (2,848 samples). The north loop past the 0.3 m crop (about 800 of its
  1,001 m) has no photo in the bake's aerial: its tone is the bake's own fill from the nearest photographed asphalt, flat
  [invented by the fill rule]; owed: an aerial mosaic with the z18 photos.
- **No kerbs** on the north loop (none traced; the photos show some at T10-T12: owed, ledger 0081's method), no TreeFX (NAIP
  shows no shrub there); GrassFX as 0.1.10 (124 rectangles, 123 kept).

### 8. Three roofs from the 2018 lidar (commit cfd626e9)

The G10 job of round 2 item 5 ran (USGS 3DEP CO_Eastern_B3_2018, tools/lidar_roof_forms.py; heights over the lidar ground):
- osm289311820: **flat 4.28 m**, no parapet (n 280, residual 0.16 m); was gable 3.2 / 3.9 off the 2023 shadow (3.9 +- 0.47):
  they agree within the shadow's error;
- osm289311821, the carport row: **a gable along the row, eave 2.62 / ridge 3.72 m** (n 729, 0.11 m); the posts carry the
  soffit, 2.47 m (the eave less the 0.15 m ceiling plate [invented]), within 0.03 m of the official 8 ft (2.44 m) ceiling;
- osm289311823: **a gable across the box, eave 2.48 / ridge 4.74 m** (n 324, 0.08 m); the 2023 shadow read a 2.51 +- 0.4 m
  top: **they disagree by 2.2 m**, past the shadow's error (the fit took the eave's shadow, or the building changed between
  2018 and 2023: the photo cannot say which);
- traced_white_w_of_osm289311820: one plane, 2.92 m rising to 3.79 m NNE (n 118, 0.22 m; a gable fits 0.35 m). **Not
  applied**: the group's facade skin (garage) stands no shed (author_bespoke_blend drops it: the first try left 21 blocks),
  so the round-2 gable stands; the reading is in its row (`_lidar_2018`). The 2023 crop read a ridge along it; the 2018 lidar
  reads one plane.
The other 18 are not readable in the 2018 lidar and keep their values and markings: the container row (points up to 2.9 m
over 26 % of the ring, no roof fitted), the grey roof (median -0.02 m: the 2018 lidar finds no roof where the 2023 photo
shows one), the pit-entry canopy (nothing over 1.16 m in 2018), osm289311824 / 316523 / 314487 and the posts. house_seat: 22 buildings, 0 floating / sunken / buried, lowest roof 1.64 m (0.1.10: 1.639).

### Gates, both layouts (Mac, empty workshop) against 0.1.10

Built from a git archive of 11b836ea (the round's code and data commit) and from the working tree: the same verdicts and the
same kn5 bytes.

| | 0.1.10 (Mac) | 0.1.11 West | 0.1.11 Full |
|---|---|---|---|
| chain | SHIP OK | SHIP OK | (one run) |
| drive_test: lap / ground on top / severe / bumps /km / slope kinks /km | 3,209.7 m / 0 / 0 / 0.0 / 1.87 | 3,209.7 m / 0 / 0 / 0.0 / 1.87 | 4,085.7 m / 0 / 0 / 0.0 / 5.63 |
| drive_test: floating, undrivable corners, daylight, excursions, obstructed | 0 | 0 | 0 |
| drive_test: vertex bumps (reported) | 0 | 0 | 6 |
| kn5_ground_check | PASS | PASS | PASS (the same kn5 set) |
| verify_kn5 / --inis | PASS (road kn5 nodes) / - | PASS (spawn kn5) / PASS | PASS (spawn kn5) / PASS |
| audit_mesh | CLEAN | CLEAN (one OBJ) | |
| road_wear_check | PASS (r 0.8741) | PASS (r 0.8813) | |
| verify_pads FORK | - | PASS: coverage 0.0 m2, seam 1.2 mm, grass 0, curb 0, node 0.0 m vs 3DEP | |
| verify_mouths (the merge) | - | PASS: mouth line 0.012 m, notch 0.003 m, approach 0.61 %/m | |
| house_seat | PASS, 22 | PASS, 22 | |

kn5 22,270,313 -> **25,086,070 B**; split main 72 -> 73 meshes (+ 1ROAD_pad_FORK), 99,419 -> 126,303 positions; AUDIT roads
13,164 -> 25,881 v, grass 71,380 -> 90,077 v, walls 14,286 -> 14,200 v (the roofs' colliders), curbs 42,102 -> 58,302 v;
kn5_ground walls 35 -> 36 objects,
seat gap median -0.25 / p95 -0.17 m, hovering 0; road over ground 0 / 3,698 samples over 0.05 m (p95 +0.021, max +0.049 m);
edge_report at 1 m past the lane: kerb 97.2 %, ground 1.9 % (the FORK's and the merge's mouths), lane 0.9 %.

### Shared files touched (every change opt-in by a High Plains key; no other track's output changes)

- `scripts/geometry/circuit_start.py`: `race_start.layouts`, `layout_ids`, `layout_line`, `spawn_set`.
- `tools/circuit_dummies_blend.py`: the per-layout mode (`race_start.layouts`); the single-layout path refactored into
  `place()` (the same checks, the same order).
- `scripts/ac/verify_kn5.py`: `_verify_race_start_spawn` for a `race_start.layouts` track's spawn kn5s (fleet/GATES-CHANGELOG.md).
- `tools/lm_pads_blend.py`: `lm_pads.deck.fill "membrane"` (`membrane_fill`).
- `tools/trim_connectors.py`: a record's line paint carried through `_trim_against` and `cut_at_pads` (`carries_paint`,
  `sliced_paint`; only a record that carries paint at the trim, which no other track's does).
- `tools/weld_mouths_blend.py`: `_dev` reads an empty marking block as matching (it read inf and stopped the weld; no track
  reached that line before).
- `tools/make_map.py`: `map "race_lap"`.
- `fleet/GATES-CHANGELOG.md` (the entry above). Tests: `tests/tools/test_high_plains_round3.py` (new),
  `tests/tools/test_high_plains_round2.py` and `tests/tools/test_circuit_race_furniture.py` (round 3's state).
- Not touched: assets/licenses.json, fleet/ac-installed.json.
- The full suite on the Mac (airoso's venv): **1,737 passed** (round 2's head: 1,721; +16 in test_high_plains_round3.py).

### Still to do (round 4)

- The north loop's kerbs (T10-T12 show paint on NAIP), and the T13 kerb's curve onto Ladder's edge (traced along the West's
  edge only).
- The merge's bellmouth and the fillet behind the T13 kerb (`route.mouth_returns`, radii off NAIP).
- Road wear's aerial over the north loop (a mosaic of the 0.3 m crop and the z18 photos).
- The traced white building's measured shed (an atlas skin that stands a shed).
- The 192 m of carried edges: a second read (the verge's one-side rows) or Kevin's word that they stand.
- Kevin's drive of both layouts.

### Runbook 0097-3 (PC): rehearse 0.1.11; a green rehearsal installs and merges (Kevin's standing word)

1. EMPTY workshop, a worktree of `claude/hp-finish-r3-20261122` at the commit named in the Mac's message, ENG
   `eng_hplm_0111` = `eng_hplm_0110` unchanged (this round adds no texture: every texture's md5 = the branch's
   `assets/textures`), `AIROSO_NUMPY_PY` the lidar venv, `SHIP_PROJ` scratch, `--no-install`:
   `SHIP_PROJ=<scratch> AIROSO=<worktree> ENG=D:/k10-scratch/eng_hplm_0111 bash tools/ship_track.sh high-plains-lm --no-install`.
   If round 2 (0.1.10) has not been rehearsed or installed yet, rehearse it first (Runbook 0097-2): this round's numbers are
   read against it.
2. Read, against 0.1.10's PC rehearsal (or its install build):
   - `layouts: west full_course`; `[lm_intake] connectors: the port's own (source/full/connectors.full.json, 1 pieces)`;
   - `[trim] full_north: cut at pad FORK's box (19 pt(s) inside dropped ...)`, `mouth full_north#0#0 (end) -> MAINLINE ...
     angle 46.1 deg`; `[weld] full_north#0#0 (end) ... after max 0.0000 m`;
   - `[lm-pads] FORK: deck membrane {... 'free': 550 ...}`, 1,441.5 m2, seam residual 0.0;
   - `[kerbs] 20 kerb runs, 579 m ... (ROAD read missed 9)`; `[lap] full: 1527 vertices, 4085.7 m`;
   - `[circuit-dummies] west ... sectors at s 1082, 2152` and `full_course (lap full) ... sectors at s 1374, 2736`;
     `[spawn_kn5] west / full_course: kn5=True size=5058 dummies=57`;
   - every gate per layout: drive_test west (as 0.1.10: kinks 1.87 /km) and full_course (Mac: severe 0, kinks 5.63 /km,
     6 vertex bumps reported); kn5_ground_check west and full_course; verify_kn5 (`[race_start west]` / `[race_start
     full_course]` rows) and --inis; audit CLEAN; road_wear_check (Mac tone r 0.8813); verify_mouths PASS; verify_pads FORK
     PASS; house_seat 22;
   - the kn5's bytes (Mac: 25,086,070), the two spawn kn5s, `models_west.ini` / `models_full_course.ini`, `ui/west` and
     `ui/full_course` (names "... — West" / "... — Full").
3. Green: install as `high_plains` (0.1.10 parked as every install). The folder changes shape: one layout -> two
   (`west`, `full_course`), so Content Manager files the West course under a new id (its old records stay under
   `high_plains`); say so to Kevin with the install. Then the records and menu pictures (both layouts) to the branch (no
   force); the Mac merges. Red: records only, no install.

## Round 4 (0.1.12, Mac, 2026-11-23): the north loop's kerbs, its edges read again, its aerial, the merge's bellmouth, the white building's shed

The five items of "Still to do (round 4)" above, every number read off NAIP 2023-09-28 (the item
co_m_3910317_ne_13_030_20230928_20240104: the 0.3 m crop and its z18 web tiles, 0.46 m here, public domain) or the 2018 lidar
unless it says [invented]. Built numbers are from Mac builds with Blender 4.2.9 from an EMPTY workshop (`SHIP_PROJ` scratch,
`--no-install`, ENG = the engine-july snapshot + the branch's `assets/textures`), against a Mac build of 0.1.11 (a25b69c9)
made the same way (its kn5 25,086,070 B, the round-3 build's to the byte). No download: every source was on disk.

### 1. The north loop's kerbs, measured and built

**Found** by ledger 0081's method on the north loop's own line (`source/full/connectors.full.json`): a colour scan of each
lane-edge band (`tools/kerb_spans.paint_class`, blue present) over road wear's new mosaic (item 3) and straightened strips of the
whole loop; every span then checked by eye on zooms at 30 px/m with 1 m ticks. Eight runs of edge paint show: six blue / white
kerbs and two blue / yellow stripes.

**Measured** (`source/edges/trace_north_kerbs.py`): `tools/kerb_offsets.py`, ledger 0081 round 3's block reader (the light / dark
blocks along the edge, colour not used; calibrated against High Plains' 20 colour-measured runs: raised blue / white kerbs inside
its 0.4 m bar at 0.3 m and at 0.6 m), `--follow 1` (the loop's line is the pavement's measured centre, not the kerb: each band's middle
drifts 0.3-0.7 m along a run). On the z18 photo the kerbs' blue is faded, so kerb_spans' colour read is the weaker one; it is kept
beside each run (`colour_read`) and lands within 0.31 m of the block reader's in / out on every run. Ends: the reader's, except
where the end zooms showed it more than 1 m off the blocks (`:eye`). s is the north loop's own (from the fork's OSM node):

| run (north-loop s) | photo | in_m .. out_m (block reader) | colour read | block amp | stations | built |
|---|---|---|---|---|---|---|
| R 56.8-98.2 (Bobsled's first) | 0.3 m | -1.83 .. -0.19 | -1.90 .. -0.40 | 33.3 | 40/40 | 39.9 m |
| L 169.8-216.3 (eye end) | z18 | -1.96 .. -0.27 | -1.90 .. -0.55 | 24.5 | 47/47 | 45.4 m |
| R 307.5-334.8 (eye start) | z18 | -1.57 .. +0.06 | -1.75 .. -0.25 | 25.7 | 28/28 | 24.2 m |
| R 545.7-637.8 (the north hairpin; eye start) | z18 north | -1.92 .. -0.13 | -1.75 .. -0.25 | 28.0 | 93/93 | 80.8 m (its inside edge) |
| L 732.8-761.0 | z18 | -2.34 .. -0.48 | -2.20 .. -0.70 | 31.7 | 27/27 | 27.5 m |
| L 982.8-990.3 (T13 on Ladder's edge) | 0.3 m | -0.73 .. +1.15 | -0.70 .. +0.95 | 33.5 | 8/9 | 6.5 m |

**T13's curve onto Ladder's edge.** Round 3 re-traced the West's T13 run (L s 2,843-2,856) onto the corner's paint, so its first
two edge points already stand on the curve. The north loop's piece ends where that run begins: at the north-loop s whose left
lane edge lies nearest the West run's first edge point, s 990.3 (`trace_north_kerbs.t13_end`), so the two pieces meet. The
first build ran it to the line's end (s 995.8): the two pieces overlapped over about 4 m of the corner (road_wear_check
kerb_levels: 2 triangles matched to the other piece's face) and its last section stood 0.125-0.14 m over the West lap's deck
(audit K: 4). Both cleared with the end at s 990.3. Each piece keeps the engine's 4 m end ramp [invented, the config's] at the
corner where the paint is one.

**Not built: the two blue / yellow stripes** (L s 372-401, L s 648-682). Flat stripes fail the block reader's bar (ledger 0081
round 3: 0.48 / 0.67 m at 0.3 m), and on the z18 photo their blue does not read as blue (kerb_spans: no paint in L s 372-401, 4
of 35 stations in L s 648-682). Nothing measures them on the photos in reach.

**Built**: each run names its line, `"line": "full_north#0#0"` (the north loop as the chain's trim leaves it), keyed to that
connector's rows by `tools/author_kerbs_blend.py` (new opt-in) and laid exactly as the lap's 20 are (kerb.placement "measured",
the config's 0.08 m height and 4 m end ramps, both [invented] as before). `[kerbs] 26 kerb runs, 803 m` (was 20, 579 m). The five
along the loop lie inside the built lane edge, where their paint is (kerbs.built.json: in -2.25..-1.72, out -0.39..-0.09 m off
the ribbon's edge); T13's piece crosses Ladder's edge at the corner (-0.62..+1.26 m). Stills:
`source/edges/kerbs_north_blocks_strips.jpg` (each run straightened, the followed band over its blocks).

### 2. The merge: the west bellmouth measured and built; the corner behind the T13 kerb not measured

**Measured** (`source/edges/measure_merge_radii.py` -> `source/edges/mouth_radii.naip.json`, still `mouth_radii_merge.jpg`):
`tools/mouth_radii.py` (ledger 0086, Sand Creek's) on the built corner frames of an empty-workshop build of this branch, NAIP 2023
as z18 tiles (0.46 m, its own reader):
- **the west corner (the bellmouth, a 64.7 deg wedge): R 14.0 m**, contrast 29.2 (bar 12), prominence 1.91 (bar 1.4), both legs'
  edges found (host +0.2 m, street -0.8 m off the built edges). Checked by eye on a top-down overlay of the built road on the
  0.3 m crop: the built return's strip lies along the grass boundary that sweeps from Ladder's west edge to the lap's north edge;
- **the east corner (behind the T13 kerb, 120.1 deg): NOT measured**: the best arc runs to the 20 m grid's end (the kerb's paint
  wraps the corner wider than the reader looks). The same reading on 0.1.11's frames and on 0.1.12's: identical.

**Built**: `route.mouth_returns ["full_north"]` (tools/mouth_returns_blend.py, after lm_pads): the west corner a circular return at
R 14.0 m tangent to the West lap's and Ladder's pavement edges (built frame 78.6 deg, tangent 17.1 m, arc 24.8 m: 87 return
stations of the track's own edge profile, 83 corner-pavement triangles, 11 of Ladder's edge-strip rows replaced; 6,366
ground edges halved round it, 0 ground vertices pinned: the prep seats that ground). New opt-in `route.mouth_returns_measured_only`: a corner without its own measured radius is NOT
built at another corner's median (the tool's default), so the fillet behind the T13 kerb stays owed. The West lap's white edge
line ran across the opening; NAIP 0.3 m shows no line there, so `road_markings.gap_mouths` (ledger 0086's) breaks it (24 paint
faces). `verify_mouth_corners` (Sand Creek's gate, its limits as they are) now judges the merge: **lip 0.023 m (<= 0.05), teeth
1 / 354 = 0.28 % (<= 2.1 %), edge paint 0.0 m, R 9 turn drop 0.091 m (reported)**. Its first run read edge paint 14.0 m: the
line across the opening (GATES-CHANGELOG 2026-11-23).

### 3. Road wear's aerial over the north loop

`source/road_wear/make_aerial_mosaic.py` -> `naip_2023_hp_mosaic.png` (4,495 x 2,475 px, 12.0 MB; record `.json` beside it):
the 0.3 m crop's own lattice (its W, E, S and pixel) carried north by whole rows to the loop's top + 40 m [invented extent],
the crop's 1,202 rows copied unchanged into the bottom, the rows above it from the z18 photos (the committed
`tracks/high-plains/source/naip_2023_hp_z18.png` and round 3's north tiles, the same item) bilinear within 40 m [invented
extent] of the north loop (700,301 px), black elsewhere (no road reads there). **Registered** against the crop where both hold a
pixel (the fork and the merge): the best shift 0.0 / 0.0 m (normalised correlation 0.895, the same at 0), luminance ratio 0.999
(not applied). `road_wear.aerial` reads it (ship.json syncs it in place of the crop); the bake and its gate read it exactly as
they read the crop.

Built: the north loop's tone is the photo's, not the fill's; the bake's measured registration moves (-1.25, +1.00) -> (-0.75,
+1.00) m (it is one shift over both layouts' road now); road_wear_check tone **r 0.8813 -> 0.8831** over 2,848 -> 4,358 samples;
the macro atlas 2,336,697 -> 3,184,897 B; photo_rubber (West line) depth 0.1338 -> 0.1295; every road_wear_check row PASS.

### 4. The traced white building's measured shed

`traced_white_w_of_osm289311820` is now **form "shed" on the 2018 lidar's one plane** (its `_lidar_2018` reading,
hp_roof_forms.json): 3.35 m at its centroid, rising 0.0285 m per m east and 0.0864 m per m north, **2.92 m at its lowest corner
to 3.79 m at its highest (NNE)** (n 118, residual 0.216 m; a gable fits 0.35 m). The group's garage skin could not stand a shed
(round 3); new opt-in `"atlas_shed"` (tools/author_bespoke_blend.py) with `tools/circuit_facades.py facade_walls(shed_tops=...)`:
the skin's modules to the plane's lowest corner, every bay carried on in the plain cell up to the plane (10 bays, 10 faces), the
roof the ring on the plane. `[bespoke] ... shed 2.9..3.8 m`; house_seat 22, 0 floating / sunken / buried, lowest roof 1.64 m. The
2023 crop's ridge (round 2's gable 3.2 / 3.9 m, `_form_2023`) and the 2018 lidar's plane disagree on the form; the lidar is the
height's measurement, and the two agree on the heights within the shadow's error.

### 5. The carried edges, read again

Round 3 carried 192 m: the step reader (ground-ness rising 12 over 1 m to a ground level of 30) left one side unread where the
verge greys into the prairie over metres. **The second read** (`measure_north.py` SECOND_READ): what edges the pavement in each
carried stretch was checked by eye on straightened strips (the white edge line, or a north-loop kerb's paint where the kerb is
the paved edge), then read station by station inside an eye-set band [lo, hi]:
- "line": the first luminance ridge standing LINE_MIN 10 [invented] over the darkest asphalt in the metre inside it; the edge is
  the ridge + the photo's own **measured** line-to-edge offset (the median of the step reader's edge less the ridge within 1 m
  [invented] inside it, over the rows both hold: **0.3 m left (156 / 407 rows on the 0.3 m / z18 photo), 0.4 m right (66 / 477)**);
- "kerb": the lap's own kerb rule (measure_widths.kerb_edge: the outer end of the first paint run in the band).
Second-read rows go through the first read's outlier filter and running median; a row the first read holds keeps its value.

| stretch (north-loop s) | read | rows read / in it | built width change |
|---|---|---|---|
| L 216-240 | the edge line, clear, after the L s 170-216 kerb | 12 / 13 | -1.73 .. -0.58 m |
| L 240-300 | the edge line, faint | 26 / 31 | -1.45 .. +0.37 m |
| R 301-306.5 | the edge line before the kerb | 2 / 3 | +0.65 .. +1.36 m |
| R 306.5-335 | the kerb R s 308-335's paint (outside the edge line) | 14 / 14 | +1.39 .. +2.16 m |
| R 335-354 | the edge line past the kerb | 9 / 10 | +0.07 .. +1.14 m |
| L 714-733 | the edge line before the kerb L s 733 | 9 / 10 | -1.75 .. -0.05 m |
| L 733-739 | the kerb L s 733-761's paint | 2 / 3 | -1.52 .. -0.94 m |
| R 933-941 | the edge line where the read passes from z18 to the crop | 1 / 4 | -0.03 m |

**150 m more measured; 960 m measured, 42 m still carried [invented]**: the fork's mouth (R s 0-19, inside the FORK pad's measured
outline: the cut drops those rows), the merge's mouth (R s 988-1001, L s 998-1001: the West lap's pavement runs on; the weld meets
it there) and **L s 254-260** (the faint line gave readings, none survived the outlier filter). The interpolation round 3 carried
was off by up to 2.2 m: it ran each edge between a white line and a kerb's outer side as if they were one edge. Built widths
p5 / p50 / p95 10.66 / 11.18 / 12.81 m (round 3: 10.63 / 11.23 / 12.84); the line moved up to 0.83 m (s 208-360, 712-748);
measured widths p5 / p50 / p95 10.6 / 11.2 / 12.95 m. The Full lap 4,085.7 -> 4,085.3 m.

### Gates, both layouts (Mac, empty workshop) against 0.1.11

Built from a git archive of ccc4ee45 (the round's code and data commit), of 65442a3d (this ledger and the mosaic regenerated from
the final north-loop line) and from the working tree: the same verdicts in every row; the road kn5s 26,463,672 B and EQUIVALENT
(tools/kn5_equiv.py: tangents only, max 1.79e-07), the spawn kn5s byte-identical.

| | 0.1.11 West | 0.1.11 Full | 0.1.12 West | 0.1.12 Full |
|---|---|---|---|---|
| chain | SHIP OK | (one run) | SHIP OK | (one run) |
| drive_test: lap / ground on top / severe / bumps /km | 3,209.7 m / 0 / 0 / 0.0 | 4,085.7 m / 0 / 0 / 0.0 | 3,209.7 m / 0 / 0 / 0.0 | 4,085.3 m / 0 / 0 / 0.0 |
| drive_test: slope kinks /km (reported) | 1.87 | 5.63 | 1.87 | **8.57** |
| drive_test: vertex bumps (reported) | 0 | 6 | 0 | **14** |
| drive_test: floating, undrivable, daylight, excursions, obstructed | 0 | 0 | 0 | 0 |
| kn5_ground_check | PASS | PASS | PASS | PASS |
| verify_kn5 / --inis | PASS / PASS | PASS / PASS | PASS / PASS | PASS / PASS |
| audit_mesh | CLEAN | | CLEAN | |
| road_wear_check | PASS (r 0.8813) | | PASS (r 0.8831) | |
| verify_pads FORK | PASS (coverage 0.0 m2, seam 1.2 mm) | | the same | |
| verify_mouths (the merge) | PASS (0.012 / 0.003 m, 0.61 %/m) | | the same | |
| verify_mouth_corners (the merge) | - (not run) | | **PASS** (lip 0.023 m, teeth 0.28 %, paint 0.0 m) | |
| house_seat | PASS, 22 | | PASS, 22 | |

The Full's 12 more slope kinks (23 -> 35; the worst still 4.58 %/m, 0.1.11's, on the West's L s 1,681 kerb) and 8 more vertex
bumps (2.5-6 cm across a vertex hop, under 2.5 cm on the path's own travel) are the new north-loop kerbs' ends: each kerb lies 0.1-2.3 m inside the lane edge where its paint is, so the 1.25 m wheel path
rides onto it over the 4 m end ramp [invented], as the West's 1.87 /km are all on its kerbs. Neither is gated; no severe step.
The West layout's drive_test is unchanged to the digit.

kn5 25,086,070 -> **26,463,672 B**; split main 73 -> 79 meshes (+6 kerbs), 126,303 -> 133,633 positions; AUDIT roads 25,881 ->
26,130 v (the corner pavement), grass 90,077 -> 96,589 v (the ground round the return), curbs 58,302 -> 61,866 v, walls 14,200
v; kn5_ground road over ground 0 / 3,733 samples over 0.05 m (p95 +0.021 m), walls 36 objects, seat gap median -0.25 / p95
-0.17 m; edge_report at 1 m past the lane: kerb 97.0 %, ground 1.9 %, lane 1.1 % (0.1.11: 97.2 / 1.9 / 0.9). AI lines: West
2,140 points, 3,210.7 m, est 96.0 s (the same); Full 2,725 points over 4,087.5 m, est 130.5 s (was 4,087.8 m, 130.0 s). Spawn
kn5s 5,058 B each, as 0.1.11.

### [invented] numbers this round adds

- the mosaic's 40 m margin and 40 m corridor (extent only: the bake reads at most ~13 m off a road);
- the second read's LINE_MIN 10 and LINE_TO_EDGE_SEARCH_M 1.0 (reader tuning; the line-to-edge offset itself is measured);
- the 42 m still carried;
- the north-loop kerbs carry the config's kerb height 0.08 m and 4 m end ramps (both [invented] since ledger 0081).
The bands of the second read and the kerbs' spans are read by eye on the photos (ledger 0081's method), not tuned.

### Shared files touched (every change opt-in by a High Plains key; no other track's output changes)

- `tools/author_kerbs_blend.py`: a run's `"line"` (a kerb keyed to a connector's rows; a FATAL names a line the build lacks).
- `tools/author_bespoke_blend.py`: a row's `"atlas_shed"` (an atlas-skinned shed; without it refused as before).
- `tools/circuit_facades.py`: `facade_walls(shed_tops=...)` (absent = byte-identical walls).
- `tools/mouth_returns_blend.py`: `route.mouth_returns_measured_only`.
- `fleet/GATES-CHANGELOG.md` (2026-11-23: verify_mouth_corners wired onto High Plains, no threshold moved).
- Tests: `tests/tools/test_high_plains_round4.py` (new, 10); `tests/tools/test_high_plains_round2.py` and
  `tests/tools/test_high_plains_round3.py` (the version, the kerbs file's lap runs, the width kinds, the white building's form).
- Not touched: assets/licenses.json, fleet/ac-installed.json, assets/textures (no texture added).
- The full suite on the Mac (airoso's venv): **1,747 passed** (round 3's head: 1,737; +10 in test_high_plains_round4.py).

### Still to do (round 5)

- The fillet behind the T13 kerb (the merge's east corner): its radius is past mouth_radii's 20 m grid; a wider grid or another
  reading of the kerb's own arc would measure it.
- The north loop's two blue / yellow stripes (L s 372-401, 648-682): no reader measures a faded flat stripe on z18.
- L s 254-260 of the north loop (6 m still carried).
- Kevin's drive of both layouts.

### Runbook 0097-4 (PC): rehearse 0.1.12; a green rehearsal installs and merges (Kevin's standing word)

1. EMPTY workshop, a worktree of `claude/hp-finish-r4-20261123` at the commit named in the Mac's message, ENG
   `eng_hplm_0112` = `eng_hplm_0111` unchanged (this round adds no texture: every texture's md5 = the branch's
   `assets/textures`), `AIROSO_NUMPY_PY` the lidar venv, `SHIP_PROJ` scratch, `--no-install`:
   `SHIP_PROJ=<scratch> AIROSO=<worktree> ENG=D:/k10-scratch/eng_hplm_0112 bash tools/ship_track.sh high-plains-lm --no-install`.
   The branch carries round 3 (0.1.11) under it: if Runbook 0097-3 has not run on the PC, this one rehearses both rounds at once;
   read it against 0.1.10's PC build then, and say so.
2. Read, against 0.1.11's PC rehearsal (or its install build; Mac numbers in brackets):
   - sync: `source/road_wear/naip_2023_hp_mosaic.png` (12,031,563 B) and `source/edges/mouth_radii.naip.json` synced in;
   - `[returns] full_north#0#0|end|+1 -> MAINLINE: NOT built: its radius was not measured ...` and `[returns] 1 corner return(s)
     at 1 mouth(s) (radius measured 1, a median 0); 1 skipped; 87 return stations, 83 corner pavement tris`;
   - `[gap-mouths] ... the host's edge line broken at 1 mouth(s) (24 paint faces inside the openings deleted)`;
   - `[kerbs] 26 kerb runs, 803 m ... (ROAD read missed 9)`; `[lap] full: 1527 vertices, 4085.3 m`;
   - `[bespoke] ... 10 buildings stood, 0 dropped`; data/bespoke.report.json traced_white_w_of_osm289311820 `form "shed 2.9..3.8 m"`,
     `facade.shed_faces 10`;
   - `[road_wear] aerial registered to the built road: shift (-0.75, +1.00) m`; macro atlas 3,184,897 B;
   - every gate per layout: drive_test west (as 0.1.11: kinks 1.87 /km) and full_course (severe 0; kinks about 8.57 /km and 14
     vertex bumps, reported); kn5_ground_check west and full_course; verify_kn5 and --inis; audit CLEAN (K 0); road_wear_check
     PASS (tone r 0.8831); verify_mouths PASS; **verify_mouth_corners PASS** (new for High Plains: lip 0.023 m, teeth 0.28 %,
     edge paint 0.0 m); verify_pads FORK PASS; house_seat 22;
   - the road kn5's bytes (Mac: 26,463,672), the two spawn kn5s (5,058 B each).
3. Green: install as `high_plains` (0.1.11, or whatever stands, parked as every install); if 0.1.11 was never installed the
   folder changes shape here (one layout -> `west`, `full_course`; Runbook 0097-3 step 3), say so to Kevin. Then the records and
   menu pictures (both layouts) to the branch (no force); the Mac merges. Red: records only, no install.
