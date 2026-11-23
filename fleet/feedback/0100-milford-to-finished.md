---
id: 0100
title: Milford to finished, round 1 — Kevin's eleven answers built as opt-in config (0.1.14), the PC's rehearsal runbook
status: fixed-awaiting-rebuild
scope: track:milford-road-course-lm (tools/author_bespoke_blend.py, tools/seat_pads_blend.py, tools/pad_clip.py; opt-in)
layer: project
train: -
---

## Request (Kevin, 2026-11-22)

Kevin added Milford to the tracks to finish on Nov 22 and said "go". His answers on the calls page, the option text verbatim:

| question | his answer |
|---|---|
| Length (ours 4,887 m on two branches first mapped in OSM in 2022; GM's 2.9 mi loop 4,664 m in OSM) | "Build the 2.9 mi loop" |
| Start/finish (the only painted line is at s 4,628.6, 64 m past today's timing line) | "Make the painted line the start/finish" |
| Verge trees (NAIP shows canopy the 2017 lidar missed: 8.6 % vs 18.4 % within 30 m; 428 blobs, 4.43 ha) | "Plant them from the photo" |
| Oakland County 2025 aerial at 7.6 cm (~150-600 MB) | "Yes, download it" |
| 32 far ledges | "Reshape the shoulder" |
| T3's first 0.6 m (the traced start reaches 0.18 m over the lane; moving it ~0.2 m, inside NAIP's 0.5 m pixel, stands module 0) | "Move the start 0.2 m" |
| Tree collider reach (30 m [invented], veg_plan.COLLIDER_REACH_M) | "Narrower" |
| Finer grass (6 m cells: 4,131 patches vs today's 1,285) | "Use the 6 m cells" |
| The dropped NW building (the NW complex's lowest roof, set into its slope; Del Mar's set-in form would stand it) | "Stand it with the set-in form" |
| Deeper 2017 lidar (~2-6 MB north strip / ~60-90 MB whole ring) | "The whole ring" |
| Track file (the run-off pads add 11.4 MB to 62.1 MB because they're flat-shaded, every triangle its own corners) | "Shrink it" |
| Owned asphalt and concrete | "On every track now" |

Round 1 (this entry, the Mac): everything that needs no download and keeps the 4,887 m layout. The 2.9 mi loop and the
shoulder reshape went to a PC session (the orchestrator's scope change, 2026-11-22); what this round found for them is under
"Round 2 notes". The two downloads are the orchestrator's; nothing was fetched here.

Rules held: measured numbers, anything chosen marked [invented]; all vegetation TreeFX; no gate threshold moved
(`fleet/GATES-CHANGELOG.md` 2026-11-22); every new behaviour opt-in by a key only Milford names; no other track's output moves.

## Evidence the round stands on

- The 0.1.13 build's swept line, `data/centerline.local.json` (6,537 points, lap 4,898.2 m; the PC's install build), is the line
  every station below is read on. A proxy of the built lane edge (that line +- half its width) reproduces the PC's own
  measurements on the 0.1.13 gate OBJ to the millimetre: T3 module 1's corner 0.214 m off the lane (PC: 0.214) and module 0
  0.184 m over it (PC: 0.18, read off the authored blend).
- **A finding:** 0.1.13's start is NOT on the front straight. engine-july's prep puts the grid on the lap's straightest 260 m;
  on 0.1.12's line that was the front straight (AC_TIME_0 64 m short of the paint), on 0.1.13's line it is the EAST straight
  (`data/dummies.json`: AC_START_0 at s 3017.2, AC_TIME_0 at s 3047.2, 8 pits). The "64 m past today's timing line" of the
  question was 0.1.12's. There, engine-july's reflected yaw happens to face the travel (+1.00 computed; on the front straight
  it reads about -1, ledger 0093).

## What changed, item by item (measured on the Mac unless said)

### 1. T3: the traced start 0.2 m off the lane — done

`scenery.bespoke.rails` t3_s1000_apron_back, point 0: [-83.6662312, 42.5690387] -> [-83.666229668, 42.5690373], **0.200 m square
to the built lane edge** at s 1016.1 (engine x +0.126, z -0.156), inside the 0.5 m pixel it was traced on. The rest of the line
is the inventory's.
- **Module 0's nearest corner: 0.184 m over the lane -> 0.011 m outside its edge** (the new face-to-lane distance; module 1
  0.214 -> 0.404 m, module 2 0.614 -> 0.800). 51 modules, all expected to stand (0.1.13: 50, 1 left out); the first segment
  15.207 -> 15.081 m keeps its 24 modules.
- Module 0 stands on the edge strip as modules 1-4 do (`stand_on` / `seat surface`, ledger 0091 round 2). drive_test's
  obstruction disc reaches w/2 - 0.1 m from the centre; the corner is 0.11 m past it.
- The margin is thin: 11 mm against a proxy that matched the PC to under 5 mm. If the PC's author log still says `1 left out`,
  the next step is the same move at 0.25 m (still inside the pixel; +0.06 m): Kevin's call, not taken here.

### 2. The painted line as the start / finish — done

`race_start` (ledger 0093's tools, as High Plains 0.1.8; `tools/circuit_dummies_blend.py` in prep, `verify_kn5`
`race_start_checks`):
- **line**: declared by its MEASURED lon/lat, -83.667339, 42.568319 (+-0.7 m, the furniture audit 2026-11-18 section 4.2), not
  by `station_m`: the brief asked for `line.station_m`, but a station moves whenever the line is rebuilt and the paint does
  not. It projects to **s 4,639.86, lateral +0.37 m** on 0.1.13's swept line (0.1.12's line put it at s 4,628.6).
- **grid**: `pattern` first -7.4 m, step -4.55 m, laterals [-2.25, +3.00], **20 slots** (the last 93.9 m behind the line).
  - Measured: the laterals, the middles of the painted line's two halves (its centre +0.37 m +- a quarter of its 10.5 m);
    that the grid stays on the straight (the lap runs within 2 deg [invented tolerance] of the line's heading from 101.0 m
    behind it to 67.0 m ahead).
  - **[invented]**: 7.4 m to the first slot and the 4.55 m stagger (9.1 m per column) = High Plains' measured grid
    borrowed; 20 slots; which column is pole (the right, as High Plains'). NAIP 2022 resolves no grid marks from s 4,500
    through the line to s 200.
- **pits**: `pattern` +8.0 / +4.55 m, the same laterals, 20 [invented]: no pit lane at Milford, so on the racing surface
  ahead of the line (s 4,647.9-4,734.3), as High Plains'.
- Sectors: none declared, the lap in thirds from the line (s 1,374.4, 3,007.1; engine-july's rule).
- `scripts/geometry/circuit_start.plan` on the committed line: no problem; 47 nodes (20 + 20 + hotlap + 3 timing pairs);
  every facing node's kn5 +Z . travel +1.000; the nearest car edge 2.91 m inside the road (AC_PIT_19); AC_TIME_0 7.4 m ahead
  of AC_START_0.
- **The paint**: `route.paint` sf_line, 1.0 m wide and 10.5 m long, square to the lap at the measured centre (lateral -4.88 to
  +5.62 m: the audit's -4.9 to +5.6), plain white [invented: no chequer resolves at 0.5 m]; `ship.json` runs the draft step
  `paint` after `kerbs` (`tools/author_paint_blend.py --stage draft`, as High Plains').
- The AI line's point 0 follows AC_TIME_0 (`write_ai_line` rotates to it), and the grid check reads it forward.

### 3. GrassFX at 6 m cells — done

`grassfx_zones.cell_m` 12 -> **6**, `near` dropped (it read only the cells within 30 m at 6 m). `tools/plan_grassfx_aerial.py` on
the committed line (today's config reproduces the installed `data/grassfx.aerial.json` byte for byte first):
- 200 x 262 cells, **3,952 rectangles** (0.1.13: 2,067; 0.1.5-0.1.12: 1,285; the question's 4,131 was 0082's plain reading,
  before 0092's projection frame and pad looks).
- Each zone under its own look (`source/vegetation/scripts/grass_coverage.py`): **C 93.0 -> 95.2 %, B 71.2 -> 77.1 %,
  D 63.8 -> 74.3 %**; rectangle area off its zone 14.55 -> 11.88 ha.
- Within 30 m of the lane edge nothing moves (6 m already): class = look C 89.3, B 76.8, D 61.9, base 86.8 %.
- What 3,952 `[GRASS_FX_ADJUSTMENT]` sections cost in CSP: VERIFY IN-GAME.

### 4. The tree collider reach, narrower — done (derived, not measured; flag for Kevin)

No car's stopping distance off this road is measured. What is measured is where the facility stands its barriers (every
W-beam and tyre wall a line off NAIP 2022, +-1 px); each barrier's standoff from the lane edge is the run-off the facility
leaves in front of it. Median standoffs off 0.1.13's lane edge: **G4 19.07 m**, T2 18.07, T1 15.71, T3 11.60, G1 4.35,
G2 0.51, G3 0.44 (the F1 screens, site fences, not counted).
- **Reach = 20 m**: the widest median standoff, rounded up (`source/vegetation/scripts/veg_trunks_reach.py`). A tree's distance
  is to the drivable surface: the lane edge less the 1.84 m edge strip (ledger 0092's 1KERB p99) and every pad outline (the
  ride pad and the 19 run-off pads, drivable since 0.1.13).
- **385 colliders -> 174** for the lidar's trees (261 with item 7's verge trees). At 30 m the same rule gives 419: all 385 plus 34
  beside the run-off pads, which 0.1.3's plan, made before the pads were drivable, could not see.
- `veg_plan.COLLIDER_REACH_M` 20.0; `veg_verify.py` reads it.
- **For Kevin**: 20 m is derived from the barrier lines, not a stopping distance. If he wants it narrower still, the next
  measured step down is T2's 18.07 m (19 m).

### 5. The NW building, set in its slope — done

`mpg_nw_complex_0` (roof 25.91 m, wall 5.11 m, 1,036 m2) is back in `source/furniture/pass4/blocks.json` with a `set_in` record,
out of `blocks_dropped.json`; `drop_set_in.py` drops nothing now.
- `tools/author_bespoke_blend.py` `far_roof_refusal` (opt-in by row): a far block carrying `set_in` keeps its roof at its
  measured `roof_z_m`, its walls to the lowest built ground under its rim (as every far block's), and the half-wall rule reads
  its DOWNHILL face (the lowest ground) instead of the highest. That is Del Mar's set-in form (ledger 0083 pass 4b) brought to a
  far block. A FARBLOCK needs no `_SETIN` object or lift (the prep's house seat moves only BUILDING meshes), and `house_seat` does
  not judge it.
- Its rim on the lidar's 5 m far ground (`data/far_ground.lidar.npy`, every cell measured): 19.79 m (north side 19.79-20.51,
  west 19.88-20.00) to 26.43 m (the south-east corner cell). So the roof stands **6.12 m over its downhill ground**, and at grade
  at its south-east end, where it is cut into the slope.
- No tree within 20.75 m of it; 299 m from the lane edge.

### 6. The track file, shrunk — done (the bytes are modelled; the PC measures them)

`scenery.bespoke.pads_shade` "smooth" (opt-in, `tools/seat_pads_blend.py`). Each rebuilt pad is shaded smooth, its vertex normals
the AREA-weighted mean of its faces' (`tools/pad_clip.area_normals`, set as custom normals). The kn5 writer keeps one vertex per
position + loop normal + UV + tangent (`vendor/io_import_accsv/kn5/node_writer.py`), so a smooth pad shares its corners.
Vertices, faces, heights, UVs and the self-check are exactly the flat build's.
- **Measured** (Blender 5.1.2, the 0.1.5 workshop's prepped ground, its one pad, the ride pad; `source/runoff/scripts/
  pads_shade_check.py` -> `records/pads_shade_v015_ride_pad.json`):
  - 5,837 triangles; **writer vertices 17,511 -> 3,041 (-82.6 %)**; positions and UVs identical.
  - The shading normal moves p50 0.015 / p95 0.28 / p99 0.95 deg by area, at most 3.25 deg on any face over 10 cm2, and 0.095 %
    of the area over 2 deg. The 1GRASS ground under the pads is smooth-shaded already.
  - No UV seam: the UVs are world-planar.
  - Blender's own smooth normals weight by corner ANGLE, and two clipping slivers (1-2 mm2, standing 60-90 deg) tipped two
    vertices 47-75 deg. That is why the normals are area-weighted (`tests/tools/test_milford_finish_0100.py` has the case).
- **Expected on 0.1.14 [modelled]**: 0.1.13's 20 aprons are 247,197 writer vertices for 82,408 triangles. At the vertex share of
  the PC's apron_9 (1,991 for 3,567) and of that ride pad (3,041 for 5,837), they become about **43,000-46,000**: **-8.86 to
  -8.99 MB** at 44 B a vertex. With the other items:
  - trunks 385 -> 261, about -0.23 MB at 40 writer vertices an octagon;
  - the owned concrete pair in place of building_*, about +0.07 MB if nothing else binds building_*;
  - the paint, the restored block and T3's module, a few kB.
  - **The road kn5 ≈ 53.0 MB (62,055,573 B -> about 52.9-53.1 MB)**.
- The PC reads the built pads with `source/runoff/scripts/pads_kn5_check.py`. It is checked here on 0.1.5's kn5: PADAPRON_0
  6,348 / 2,116, 3.000 a triangle, 0 deg.

### 7. The verge trees from the photo — done

The 428 NAIP-only blobs (4.43 ha; `inventory.json` flags.naip_new_since_2017) reproduced cell for cell from the vegetation
read's `crowns.npz` and committed as `source/vegetation/naip_only_canopy.png` / `.json` (2 m cells, 11,075 of them).
`source/vegetation/scripts/veg_naip_verge.py` plants each blob by a measured rule:
- **height and crown**: the median of the lidar's planted crowns within 30 m [invented] of the blob's centroid, when at least
  3 [invented] stand there (**780 trees**); fewer: the read's median 20.4 m / 9.0 m (**103 trees, [invented]**, each marked in
  `source/vegetation/naip_verge.json`);
- **positions**: a hexagonal lattice at that crown over the blob's own cells; 291 blobs take one tree, the largest 14; a lone
  tree's crown is the lesser of the neighbours' and the blob's own;
- the lidar planting's clearances (corridor margin + half a cell off the drivable surface, 1 m + half a cell off every
  footprint, on the built ground, h >= 5 m): **29 left out** within the corridor margin.
- **883 trees**: h p10 / p50 / p90 7.3 / 14.7 / 20.4 m. Their crowns cover 3.94 of the blobs' 4.43 ha. Within 30 m of the lane
  edge the crowns cover **8.6 -> 10.9 %** (NAIP's canopy 18.4 %: the rest is crowns overhanging from trunks further out, and
  canopy over cells the read counted paved or built).
- They go into `trees.lm.json` with keys from 1,000,000 and a 7th element "naip_verge", so the 11,247 lidar trees keep their
  keys, models and angles (`make_treefx` reads [:5] and the key). TreeFX Oak3 / SycamoreV2 as the rest.
- 87 of them stand within the 20 m reach and get colliders (item 4).

### 8. The owned concrete — done

`assets/textures` holds the owned pairs (`claude/owned-surfaces-20261116`, merged; CC0 row in `assets/licenses.json`).
`texture_overrides` **1RUNOFF** (the 20 pads) and **1KERB_SIDEWALK** (the concrete edge strip, whose detail road wear bakes
through `pbr.resolve`) = `concrete_plain_diffuse.jpg` / `_normal.jpg`, in place of `building_*` (Hamburg's, personal use):
- mean colour 0.5279 / 0.5159 / 0.4886 against 0.5286 / 0.5156 / 0.4891, so road wear's m0 holds;
- 0.000 % clipped over 0.1.13's m0 0.85537, either way.
- md5: diffuse d77c7ca9c8faa202951821133628a4e4 (262,056 B), normal 2692b4231be5d2c24c6b4f0f3705bb84 (370,970 B).
- Both sync in (`ship.json` `sync_in.assets`).
- Milford's other concrete is already owned (BARRIER: `tiltup_wall_*`). Its repeat on the 4 m tile is not measured.

### 10. Version 0.1.14 — done

`track.config.json` 0.1.13 -> 0.1.14 (slug and folder unchanged, `milford_road_course`).

## Shared files touched (each opt-in; no other track names a key)

- `tools/author_bespoke_blend.py`: `far_roof_refusal` (a row without `set_in` reads exactly as before, the same message).
- `tools/seat_pads_blend.py`: `pads_shade` (absent or "flat" = the flat build, byte for byte in its code path).
- `tools/pad_clip.py`: `area_normals` (new, pure).
- `fleet/GATES-CHANGELOG.md`: the 2026-11-22 entry.
- Tests: `tests/tools/test_milford_finish_0100.py` (new, 11). Updated to the new state:
  - `test_circuit_race_furniture.py`: Milford now declares race_start and route.paint;
  - `test_circuit_buildings.py`: 26 blocks;
  - `test_milford_furniture.py`: T3's point 0 is 0.2 m off the inventory's;
  - `test_milford_furniture_pass4.py`: nothing set in its slope is dropped;
  - `test_milford_ground_0092.py`: 6 m cells, 3,952 rectangles, the owned 1RUNOFF;
  - `test_milford_vegetation.py`: the 20 m reach, the verge trees aside.

Not touched: `assets/licenses.json` and `fleet/ac-installed.json`. **licenses.json needs** one change: the owned-surfaces row's
`_note` should add that the concrete_plain pair is bound per track as 1RUNOFF and 1KERB_SIDEWALK on Milford (ledger 0100;
Kevin 2026-11-22: "On every track now"). No new file needs a row. **ac-installed.json**: nothing until 0.1.14 is installed.

## What is still invented (each marked where it is written)

- The grid's 7.4 m first slot, 4.55 m stagger, 20 slots and pole column; the 20 pits on the racing surface; the line's plain white.
- The 2 deg straight tolerance.
- The verge neighbours' 30 m / 3 and the 103 trees on the read's median.
- The 20 m reach is derived from measured barrier lines, not measured as a stopping distance.
- Everything 0091-0095 already lists.

## Round 2 notes (handed to the PC session: GM's 2.9 mi loop, the shoulder)

- **The loop (4,664 m in OSM).** These keys sit on the 4,887 m line's stations and need re-reading on a new line:
  - `lm_intake.edge_retrace` spans: the front straight s 4,530 -> 150, the eight agree spans;
  - `route.start_at`;
  - the run-off pads (`runoff_pads.py --write`, ledger 0092 Owed 3);
  - the camber survey and the measured surface (their rows).

  These survive by construction: race_start and T3 (both lon/lat), the grass, and the two vegetation scripts (re-run
  `veg_trunks_reach.py --write`; the verge trees need nothing). The intake reads `tracks/milford-road-course`'s line, so a new
  layout needs its own source line first.
- **The 32 far ledges** are drive_test's excursion sweep, 4 m past the built edge. Ledger 0092 measured why: inside 9 m the
  prep's shelf and feather rule, and the lidar itself falls 0.12-0.28 m per 0.5 m on the low side of the banked corners
  (s 900-1201) and at s 1650, 3150, 3751, 4050, 4200. Reshaping the shoulder means authoring that 0-9 m band to the lidar where
  it is flat, and to a graded run-off where the real slope is the ledge. That needs the near ground at 1 m, which is the whole
  lidar ring below.
- **Oakland County 2025 aerial (7.6 cm, ~150-600 MB; the orchestrator fetches it, name / URL / size as its download records).**
  A georeferenced crop over the lap (lon -83.6700..-83.6570, lat 42.5605..42.5795) committed beside `naip_2022_mrc.jpg`
  would feed:
  - `road_wear.aerial` (the road's tone and rubber at 7.6 cm instead of 0.5 m);
  - the edge evidence (0091 Open 4: the far edges at s 2,571-2,600 and 2,655-2,676, which NAIP's shadow left to one sensor);
  - the furniture lines at +-8 cm instead of +-0.5 m: T3's start measured instead of moved; any grid marks; the S/F line's
    width and chequer;
  - the verge canopy's own crowns (the lattice replaced by measured crowns);
  - the run-off outlines.
- **The whole 2017 lidar ring (~60-90 MB, USGS_LPC_MI_31Co_Oakland_2016_LAS_2019 at full density; the orchestrator's).** It would
  feed:
  - the far ground's 20.3 % of ring cells read only at a 30 m radius;
  - the 22.26 ha of NAIP canopy the read never reached (more measured crowns, fewer of item 7's 103 invented heights);
  - the near ground at 1 m for the shoulder;
  - the NW complex's rim.

## Verification

Mac: `tests/tools/test_milford_finish_0100.py` (11) and the updated tests; the measurements above. The full suite on the
commit that files this entry: **1,721 passed, 0 failed** (main 9aacb34c: 1,710 / 0; the 11 new). PC: Runbook 0100-1. Then Kevin's drive.

## Runbook 0100-1 (PC): rehearse Milford 0.1.14 from an EMPTY workshop; report; NO install without Kevin's word

1. `git fetch && git checkout claude/mf-finish-20261122` (or the merge carrying it); `git status` clean. Blender 4.2 with the
   vendored exporter, as 0.1.13.
2. ENG = `eng_mflm_0113` plus the owned concrete pair, md5-checked in its `assets/textures` and in the checkout:
   `concrete_plain_diffuse.jpg` d77c7ca9c8faa202951821133628a4e4 (262,056 B), `concrete_plain_normal.jpg`
   2692b4231be5d2c24c6b4f0f3705bb84 (370,970 B). TreeFX bins in `source/trees/` (Oak3 24111ede..., SycamoreV2 7010d61f...),
   never committed.
3. Rehearse, numpy for the two numpy steps:
   `AIROSO_NUMPY_PY=<the lidar venv's python> SHIP_PROJ=<an empty scratch workshop> ENG=<ENG> AIROSO=<checkout> PYTHONUTF8=1
   bash tools/ship_track.sh milford-road-course-lm --no-install`.
4. The log must show (each against 0.1.13's rehearsal 3 / the install):
   - **intake** as 0.1.13 (`6537 pts, lap 4928 m`; `data/centerline.raw.local.json` 0923d812): this round moves no line;
   - **draft paint**: one `[paint] MARKINGS_paint_sf_line ...` line, read-back within 1 mm;
   - **author**:
     - `[bespoke] rail t3_s1000_apron_back: 51 tyres modules over 32 m, 0 left out` (0.1.13: 50, 1 left out).
       If it still says 1 left out: stop, report module 0's corner off the lane; the 0.25 m move is Kevin's.
     - 26 blocks, `mpg_nw_complex_0` among them, no self-check FAILED;
     - `[bespoke] trunks (...): 261 colliders` (0.1.13: 384-385);
   - **prep**:
     - `[seat-pads] PADAPRON_<k> -> 1RUNOFF_apron_<k>: ... ground over 0 / ..., smooth (corners shared)` for all 20, the same
       triangles and verts as 0.1.13's lines (apron_9's fold raise as before);
     - `[circuit-dummies] 16 prep dummies replaced by 47: the line at s 4639.9, 20 grid slots, 20 pits, sectors at s 1374,
       3007; kn5 heading min +1.000 (the prep's AC_START_0 read ...)`: report the prep's number (computed here about +1.00, the
       east straight);
   - **grassfx**: `[grassfx] 200 x 262 cells of 6 m, 0 of them read as 1 cells of 6 m ...; 3952 rectangles, 3952 kept`;
   - **verify_kn5**: PASS, plus `[race_start] heading: 41 facing nodes, local +Z . travel min +1.00` and `[race_start] road:
     40 START/PIT cars inside the road, nearest edge +2.91 m (AC_PIT_19)`;
   - **AI**: `grid check: +0.9x (...) -> FORWARD`; point 0 at s ≈ 4639.9 (the paint);
   - **treefx**: `[treefx] 12130 trees` less any make_treefx keeps off the roads (0.1.13: 11,247 of 11,247), both species;
   - **track folder**: `ui_track.json` pitboxes **20** (0.1.13: 8).
5. Compare against 0.1.13's **221 gate rows** and its **62,055,573 B** road kn5. Expected to differ, each to report:
   - **the road kn5 bytes**: about 52.9-53.1 MB [modelled]. Report the 20 aprons' vertices / triangles with
     `python tracks/milford-road-course-lm/source/runoff/scripts/pads_kn5_check.py <road kn5> --json <scratch>/pads_kn5.json`.
     Expected about 43,000-46,000 vertices for 82,408 triangles, by area p95 ≤ ~0.3 deg and at most ~3.3 deg on faces over
     10 cm2. A pad much worse: stop and report it.
   - **verify_kn5**: the two `race_start` rows are new.
   - **kn5_ground_check**: `seating.walls` objects and `seating_info.walls_trunk` fall with the colliders (0.1.13: 324 /
     312); verdict PASS, hovering 0.
   - **kn5_textures**: PASS, 0 missing; `concrete_plain_diffuse.jpg` / `_normal.jpg` embedded; `building_*` may drop out.
   - **road_wear_check**: PASS. `data/road_wear.json` `detail.1KERB_SIDEWALK.from` = `concrete_plain_diffuse.jpg`,
     clipped about 0.0 %.
   - **audit**: CLEAN; walls vertices fall with the colliders, the block's FARBLOCK vertices rise.
   - **drive_test**: severe 0; the gated excursion drops as 0.1.13 (3); far ledges as 0.1.13 (32), since this round reshapes
     no shoulder. Any new obstruction near s 1015 (T3's module 0): stop and report it.
   - **edge_smoothness, house_seat (3 judged)**: as 0.1.13.
   - **edge_report**: T3's module 0 may add a wall reading at 1 m near s 1016.
   - Every other row: the same; any other row that differs, report it with its two values.
6. Stills, if the PC can:
   - the grid from behind the pole, facing north up the front straight: the line, the cars facing forward;
   - a run-off pad up close: smooth shading, no faceting, no seam;
   - the NW complex from the lap;
   - a verge stand.
7. Report every number of steps 4-5; push the rehearsal records as data only. **No install** without Kevin's word. Then Kevin's
   drive:
   - a race start (20 cars on the front straight, facing T1, pole on the right);
   - the lap counted at the paint;
   - T3's start; the pads' look; the new verge trees and their colliders;
   - the 6 m grass's cost in frames;
   - the owned concrete on the edge strip and the pads. VERIFY IN-GAME.

## PC rehearsal (2026-11-22, 08a1c8f2): Milford 0.1.14 SHIP OK, NOT installed: the pads' shading fails step 5's stop rule

Runbook 0100-1 as written: an EMPTY workshop (`D:/k10-scratch/milford_0114_reh`), worktree `D:/k10-worktrees/mf-finish`
at 08a1c8f2, ENG `eng_mflm_0114` (= `eng_mflm_0113` + concrete_plain diffuse d77c7ca9 / normal 2692b423, md5 = the
checkout's), TreeFX bins Oak3 24111ede / SycamoreV2 7010d61f, `AIROSO_NUMPY_PY` the lidar venv, `--no-install`.
20:37-21:41: **SHIP OK**, every gate green, no force.

**Step 4, every line as the runbook expects:** intake `6537 pts, lap 4928 m`, `centerline.raw.local.json` 0923d812; one
`MARKINGS_paint_sf_line` (10.5 m, read-back 0.00 mm); `t3_s1000_apron_back: 51 tyres modules over 32 m, 0 left out`;
26 blocks with `mpg_nw_complex_0`-`_12`, no FAILED; `trunks: 261 colliders`; all 20 `[seat-pads] ... smooth (corners
shared)`, the same triangles / verts as 0.1.13 (apron_9's fold raise 1.8 mm); `[circuit-dummies] ... 47: the line at s
4639.9, 20 grid slots, 20 pits, sectors at s 1374, 3007; kn5 heading min +1.000 (the prep's AC_START_0 read 0.997)`;
`[grassfx] 200 x 262 cells of 6 m ... 3952 rectangles, 3952 kept`; verify_kn5 PASS with `[race_start] heading: 41 facing
nodes ... min +1.00` and `[race_start] road: 40 START/PIT cars inside the road, nearest edge +2.91 m (AC_PIT_19)`; AI
`grid check: +0.96 ... -> FORWARD`; `[treefx] 12130 trees`, both species; `ui_track.json` pitboxes 20.

**Step 5 against 0.1.13's install build** (`D:/k10-scratch/milford_lm`): 225 / 221 gate rows; the differences are this
round's own (paint, T3, the NW blocks, trunks 385 -> 261, the pads' "smooth", the 47 dummies, grassfx, split, grid check,
TYRES_6's reseat 400 -> 408 verts). drive_test as 0.1.13 (severe 0, kinks 1.84 /km, gated drops 3, far ledges 32, floating
0); AUDIT CLEAN, walls 45,550v -> 38,242v; kn5_ground walls 324 -> 245 objects, hovering 0. kn5_textures PASS, 0
missing, 25 embedded. road_wear.json `detail.1KERB_SIDEWALK.from` concrete_plain_diffuse.jpg, clipped 0.0 %; 1ROAD
asphalt_dense, 0.069 %. Road kn5 **53,067,848 B** (modelled 52.9-53.1 MB).

**The stop: `pads_kn5_check.py`** on the road kn5: `20 1RUNOFF_apron* meshes: 47724 vertices for 82408 triangles (0.579 a
triangle)` (expected ~43,000-46,000), and by area p95 / max on faces over 10 cm2, against the runbook's ~0.3 deg / ~3.3 deg:

| pad | p95 deg | max deg | pad | p95 deg | max deg |
|---|---|---|---|---|---|
| apron_0 | 0.276 | 3.25 | apron_10 | 4.712 | 78.71 |
| apron_1 | 0.387 | 0.73 | apron_11 | 2.159 | 12.44 |
| apron_2 | 2.006 | 5.63 | apron_12 | 1.479 | 50.92 |
| apron_3 | 1.523 | 7.52 | apron_13 | 2.444 | 7.30 |
| apron_4 | 6.851 | 73.30 | apron_14 | 2.784 | 9.73 |
| apron_5 | 4.313 | 26.14 | apron_15 | 2.433 | 9.28 |
| apron_6 | 4.121 | 25.01 | apron_16 | 23.657 | 117.20 |
| apron_7 | 6.520 | 37.49 | apron_17 | 30.771 | 79.58 |
| apron_8 | 1.625 | 19.62 | apron_18 | 3.881 | 18.50 |
| apron_9 | 2.846 | 75.74 | apron_19 | 5.814 | 50.73 |

Only apron_0 (the Mac's A/B pad) and apron_1 are inside the bound; apron_16 and _17 are far outside. Shared corners over
the ground's folds average across creases. Per step 5 ("A pad much worse: stop and report it") this build is **not
installed**; JSON `D:/k10-scratch/milford_0114_reh/pads_kn5.json`. Everything else in 0.1.14 is ready.

## Round 1b (Mac, 2026-11-22): the pads' crease limit, after the PC's stop

The PC's 0.1.14 pads shared every vertex, so their normals averaged across the ground's creases (dark streaks): 18 of 20 pads
were outside the runbook's bound. The fix (the orchestrator's decision under Kevin's "Shrink it") is
`scenery.bespoke.pads_shade_crease_deg` **10** [invented], opt-in beside `pads_shade` "smooth" (`tools/seat_pads_blend.py`,
`tools/pad_clip.crease_normals`). At each vertex the faces are grouped so that every two in a group have normals within 10 deg of
each other, and a group's corners share the area-weighted mean of its faces' normals. That mean stands within 10 deg of every
face it serves (about half that where the group is balanced). Across a sharper crease the corner splits. Without the key, 0.1.14's
one normal per vertex.

**The model's inputs are the PC's.** The 0.1.13 build's synced-out `loop.blend` (be6cbbdd, Blender 4.2) goes through
engine-july's prep (the frozen snapshot, `build_kn5_loop.py` md5 2a653ee1) and `tools/far_ground_prep_blend.py` on the Mac
(Blender 5.1.2), then `tools/seat_pads_blend.py` in three modes. Each pad is read back as the kn5 writer keeps it
(`source/runoff/scripts/pads_shade_check.py` -> `records/pads_shade_0113_20pads.json`):
- flat: 247,203 writer vertices for 82,410 triangles (the PC's 0.1.13: 247,197 / 82,408);
- 0.1.14's shared corners: 47,713 (the PC: 47,724);
- the PC's per-pad table is reproduced: every p95 within 0.03 deg, every max within 2.2 deg (apron_8, _16).

| pad | triangles | 0.1.14 on the PC, p95 / max deg | the Mac's model of it | **round 1b, p95 / max deg** | writer vertices flat / 0.1.14 / **1b** |
|---|---|---|---|---|---|
| apron_0 | 5,837 | 0.276 / 3.25 | 0.276 / 3.25 | **0.276 / 3.25** | 17,511 / 3,041 / **3,047** |
| apron_1 | 2,131 | 0.387 / 0.73 | 0.387 / 0.73 | **0.386 / 0.73** | 6,389 / 1,387 / **1,393** |
| apron_2 | 631 | 2.006 / 5.63 | 2.005 / 5.63 | **2.005 / 5.63** | 1,893 / 410 / **410** |
| apron_3 | 8,253 | 1.523 / 7.52 | 1.523 / 7.52 | **1.522 / 7.47** | 24,757 / 4,863 / **4,884** |
| apron_4 | 10,969 | 6.851 / 73.3 | 6.851 / 73.35 | **3.619 / 9.67** | 32,904 / 6,486 / **7,723** |
| apron_5 | 4,948 | 4.313 / 26.14 | 4.313 / 26.14 | **3.644 / 9.39** | 14,842 / 2,751 / **2,849** |
| apron_6 | 4,338 | 4.121 / 25.01 | 4.121 / 25.01 | **3.719 / 9.44** | 13,014 / 2,444 / **2,643** |
| apron_7 | 6,401 | 6.52 / 37.49 | 6.52 / 37.49 | **4.17 / 9.34** | 19,203 / 3,650 / **4,129** |
| apron_8 | 2,138 | 1.625 / 19.62 | 1.625 / 17.43 | **1.619 / 4.86** | 6,414 / 1,421 / **1,445** |
| apron_9 | 3,571 | 2.846 / 75.74 | 2.868 / 75.71 | **2.665 / 9.28** | 10,713 / 2,012 / **2,083** |
| apron_10 | 5,993 | 4.712 / 78.71 | 4.712 / 78.71 | **3.094 / 9.6** | 17,979 / 3,490 / **3,753** |
| apron_11 | 4,398 | 2.159 / 12.44 | 2.16 / 12.44 | **2.157 / 6.59** | 13,194 / 2,517 / **2,533** |
| apron_12 | 5,346 | 1.479 / 50.92 | 1.479 / 50.92 | **1.444 / 7.68** | 16,034 / 3,162 / **3,211** |
| apron_13 | 3,276 | 2.444 / 7.3 | 2.444 / 7.3 | **2.442 / 7.1** | 9,828 / 1,824 / **1,835** |
| apron_14 | 512 | 2.784 / 9.73 | 2.784 / 9.73 | **2.784 / 9.73** | 1,536 / 333 / **333** |
| apron_15 | 6,216 | 2.433 / 9.28 | 2.433 / 9.28 | **2.305 / 9.28** | 18,648 / 3,496 / **3,524** |
| apron_16 | 2,804 | 23.657 / 117.2 | 23.656 / 118.72 | **3.701 / 9.18** | 8,400 / 1,541 / **2,000** |
| apron_17 | 587 | 30.771 / 79.58 | 30.771 / 79.58 | **3.965 / 9.83** | 1,761 / 354 / **530** |
| apron_18 | 2,553 | 3.881 / 18.5 | 3.881 / 18.5 | **2.513 / 8.94** | 7,659 / 1,492 / **1,593** |
| apron_19 | 1,508 | 5.814 / 50.73 | 5.814 / 50.73 | **3.758 / 9.47** | 4,524 / 1,039 / **1,113** |
| **all 20** | 82,410 | | | **p95 <= 4.17, max <= 9.83** | 247,203 / 47,713 / **51,031** |

- **Every pad's corner normals stand within 9.83 deg of their faces** (faces over 10 cm2); p95 at most 4.17 deg. apron_16 / _17
  go from 23.7 / 30.8 deg p95 to 3.7 / 4.0.
- **51,031 writer vertices**: +3,318 on 0.1.14's 47,713, 0.619 a triangle.
- **The road kn5 about 53.21 MB**: the PC's 0.1.14 53,067,848 B + 3,318 x 44 B = 53,213,840 B, -8.84 MB on 0.1.13's
  62,055,573 B.
- Blender 4.2 keeps custom normals one per smooth fan. 438 of the 50,050 corner groups span faces that are not edge-connected
  around their vertex, so 4.2 may write up to about 440 vertices (+19 kB) more than this 5.1 model.
- `source/runoff/scripts/pads_kn5_check.py` now judges the 10 deg rule. It passes when every pad's largest corner-to-face angle
  on a face over 10 cm2 is within `--crease-deg` (10) + 0.5 deg [invented: float32 on thin faces and the normal's encoding;
  0.1.13's flat pads read up to 1.71 deg on such slivers], and exits 1 naming the pads otherwise.
  - It is a check the PC runs, not a chain gate: `tools/ship_track.sh` does not run it, so `fleet/GATES-CHANGELOG.md` only lists
    the 10 deg and the 0.5 deg among the round's numbers.
  - On the PC's 0.1.14 table it fails 13 pads; on this model it passes all 20.
- Tests: `tests/tools/test_milford_finish_0100.py`, three new.
  - 180 deg equals 0.1.14's per-vertex normals; every corner stays within the limit on a rough patch with a sliver; a plane
    keeps its corners shared.
  - Only Milford names the key.
  - The record reproduces the PC's table and meets the bound.

**Runbook 0100-1, delta for the rehearsal of this commit.**
- Run as 0100-1, from an empty workshop at this branch's head: ENG `eng_mflm_0114`, `AIROSO_NUMPY_PY`, a scratch `SHIP_PROJ`,
  `--no-install`.
- Step 4: every `[seat-pads]` line ends `smooth (corners shared) within 10 deg`, with the same triangles and verts as 0.1.13
  and 0.1.14 (apron_9's 1.8 mm fold raise).
- Step 5: run `python tracks/milford-road-course-lm/source/runoff/scripts/pads_kn5_check.py <road kn5> --crease-deg 10
  --json <scratch>/pads_kn5.json`. Expect:
  - `PASS`;
  - about 51,000 vertices (51,031-51,470) for 82,408 triangles;
  - every pad's max at most 10.5 deg, and p95 at most about 4.2;
  - the road kn5 about 53.21 MB (53,213,840 B +- 20 kB), against 0.1.14's 53,067,848 B and 0.1.13's 62,055,573 B;
  - every other row as the 0.1.14 rehearsal (225 rows): only the kn5 bytes and the seat-pads lines move.
- A FAIL names the pads: stop and report them. Install only on Kevin's word.
