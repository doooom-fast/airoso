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
