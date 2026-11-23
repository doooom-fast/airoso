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
