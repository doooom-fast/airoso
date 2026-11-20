---
id: 0095
title: The road's texture repeats when a lot of road is in view
status: fixed-awaiting-rebuild
scope: milford-road-course-lm, high-plains-lm
layer: engine
train: -
---

## Symptom

Kevin, 2026-11-18: "i'm also still seeing repeated patterns in the roads, likely the base texture, it looks fine up close
but when i see a lot of road a head, the repeating is very obvious".

## Evidence

The texture audit of 2026-11-18 (`/Volumes/Sundowning/codex/mac/milford-hp-audit-20261118/texture/REPORT.md`): renders of
both roads from the seat, 16x anisotropic filtering, the contrast of the part of the road's brightness that repeats on the
detail's 4 m lattice, as a % of road brightness, at 20-50 / 50-100 / 100-200 m:

| detail | Milford | High Plains |
|---|---|---|
| as built: borrowed `asphalt_cracked` (LA Canyons, personal-use only) | 3.34 / 2.17 / 1.11 | 3.32 / 2.16 / 1.11 |
| owned `asphalt_dense` (`tools/make_owned_surfaces.py`, CC0) | 0.70 / 0.33 / 0.16 | 0.70 / 0.33 / 0.16 |
| owned + a 0.5 m high-pass | 0.29 / 0.09 / 0.05 | 0.29 / 0.10 / 0.06 |

All [measured] on the renders; the camera, its FOV and the 0.5 m cut are [invented]. Beyond 100 m the repeat reads as
streaks down the road; nearer, the cracks and stains recur in rows. An 8 m tile (each repeat as strong, 4x the bytes) and a
second detail layer (NMDetail has no slot) were measured and not worth their cost. Lighting and the normal's shading are
[not measured].

## Diagnosis

Road wear (ledger 0084) puts the road's large-scale tone in a unique macro off the aerial. The 4 m detail on top still
carries its own coarse variation: the borrowed tile's alligator cracks and stains, the same at every repeat. Far down the
road the mips average the fine grain away and what is left is that coarse part, on a 4 m lattice.

## Fix (branch `claude/road-owned-pilot-20261119`; opt-in, Milford and High Plains only)

Kevin 2026-11-19: "Yes, pilot the owned asphalt with the high-pass".

1. `claude/owned-surfaces-20261116` merged in (the owned pairs, their `licenses.json` row and `SOURCES.txt`; no track bound
   them until now).
2. Both configs bind `texture_overrides["1ROAD"]` to `asphalt_dense_diffuse.jpg` / `asphalt_dense_normal.jpg`; road wear
   reads it through `pbr.resolve` as the 1ROAD detail and its normal. The pair's mean colour and relief were measured off
   the borrowed tile (`make_owned_surfaces.py`), so m0 and road wear's calibration hold.
3. `road_wear.detail_highpass_m` (new, opt-in, no default: `{surface: cut m}`), `{"1ROAD": 0.5}` on both tracks.
   `scripts/aerial/road_wear.detail_highpass` is a periodic Gaussian high-pass, H = 1 - exp(-ln2 (f / fc)^2) with
   fc = 1 / cut (H = 0.5 at 0.5 m), the mean kept, on the tile's own period so it still wraps. `tools/road_wear_blend.py`
   step 5b applies it to the named surface's detail diffuse before the `/ m0`; the normal is not filtered.
   `highpass_cuts` refuses a surface the spec does not bake or a cut outside (0, detail_tile_m / 2]. The bake logs
   `[road_wear] 1ROAD: detail high-pass 0.5 m on asphalt_dense_diffuse.jpg: std/mean a -> b %` and `data/road_wear.json`
   records `detail.1ROAD.highpass_m`.
4. Both `ship.json` `sync_in.assets` lists name the pair.

`detail_tile_m` stays 4 (the multiplier stays 256, `detail_phase` unchanged), m0 is computed as before, and no gate or
threshold changes: no `road_wear_check` row reads the detail's pixels.

## Scope

Milford and High Plains only. No other config names `detail_highpass_m` or binds the owned pair, so every other track bakes
as before; `pbr.TEXTURES` is untouched (swapping the borrowed pair fleet-wide is Kevin's call). Lake Murray has no
`road_wear` key and is unchanged. The edge strip (`1KERB_SIDEWALK`, concrete) and the run-off (`1RUNOFF`) keep their
textures; their repeat was not measured.

## Verification

Mac:

- `detail_highpass` against the audit's own `util.fft_highpass` on both full tiles: max difference 0.0.
- On `asphalt_dense_diffuse.jpg` (Pillow decode, as Blender's Non-Color load): mean 0.38895 kept; std/mean 27.90 ->
  27.87 %; clip over m0 (the last bakes' m0: Milford 0.85588, High Plains 0.76923) 0.068 / 0.408 %. The cracked tile in
  those bakes clipped 0.444 / 1.27 % (their `data/road_wear.json`), and the same computation gives 0.444 / 1.27.
- `tests/aerial/test_road_wear_highpass.py` (new, 5): the cut's half power, the mean, the wrap, the opt-in (only these two
  tracks), the bindings and the sync lists, the real tile's close look. With the cut doubled on purpose, the first fails.
- Related suites before and after: `tests/aerial`, `tests/ac` and nine tool test files (owned surfaces, circuit buildings, Milford furniture, ground and line, the LM port, bespoke assets, house gate, ship_sd) on the merge commit (this entry's changes absent): 347 passed, 13 failed; with them: 352 passed, 13 failed. The 13 are the same list, each a track or engine snapshot this sparse checkout lacks (Sand Creek, Exotics, Lake Murray's engine-july snapshot, Pikes Peak, the Lariat, the freeway).

### PC runbook 0095-1 (rehearsal with 0091-0094, install only on Kevin's word)

1. Build from this branch's head, as runbooks 0091+0092, 0093-1 and 0094-1 say; md5-check the pair in the engine copy's
   `assets/textures`: `asphalt_dense_diffuse.jpg` 339c4244d8b07494be81df14eb963c8c (2,346,705 B),
   `asphalt_dense_normal.jpg` 7a71dfcefbbce0267cb0d17f0c931fb0 (3,198,685 B).
2. In the ship log read, for each track: `[road_wear] 1ROAD: detail high-pass 0.5 m on asphalt_dense_diffuse.jpg: std/mean
   27.90 -> 27.87 %` (about), and in `data/road_wear.json` `detail.1ROAD`: `from` asphalt_dense_diffuse.jpg, `normal`
   asphalt_dense_normal.jpg, `highpass_m` 0.5, `clipped_pct` about 0.07 (Milford) / 0.41 (High Plains), if m0 holds.
3. `road_wear_check` passes as before (`detail_phase`, `density`, `photo_rubber` on High Plains); `kn5_textures` 0 missing
   (`asphalt_dense_normal.jpg` embedded as txNormalDetail).
4. `kn5_equiv` / `mesh_diff` against the reference workshops: on top of what 0091-0094 change, the 1ROAD material's
   txDetail (`road_wear_detail_1road.jpg`, new pixels) and txNormalDetail (`asphalt_dense_normal.jpg` in place of
   `asphalt_cracked_normal.jpg`) change; the 1ROAD geometry and UVs change only as 0091 says. Report the kn5's bytes (the
   audit expected about +1.07 MB: txDetail about -0.15 MB, txNormalDetail +1.23 MB).
5. A still or a lap from the seat down the front straight on each track, next to the reference build's, if the PC can.

## Open (Kevin's)

- His drive: the far road, and the close look (dense-graded stone, no alligator cracks; more even than a real worn road, the
  large variation is meant to come from the aerial).
- Fleet-wide (every road-wear track, and `pbr.TEXTURES` 1ROAD / 1RUNOFF / HIGHWAY for the rest) after the drive.
- The run-off and the edge strip, if they repeat in his view.

## PC rehearsal (2026-11-20): Milford 0.1.13 and High Plains 0.1.8, not installed

Milford: ledger 0091's "PC rehearsal 3" (8aed08ff, SHIP OK). High Plains: ledger 0093's "PC rehearsal 2" (1941dfba, SHIP
OK; nothing after it changes what High Plains reads). Both from EMPTY workshops, compared with the main builds that
reproduce the installed 0.1.12 / 0.1.7.

- **The pair in both engine copies** (`eng_mflm_0113`, `eng_hplm_0108`): `asphalt_dense_diffuse.jpg`
  339c4244d8b07494be81df14eb963c8c (2,346,705 B), `asphalt_dense_normal.jpg` 7a71dfcefbbce0267cb0d17f0c931fb0
  (3,198,685 B), as the runbook says.
- **Ship log, both:** `[road_wear] 1ROAD: detail high-pass 0.5 m on asphalt_dense_diffuse.jpg: std/mean 27.90 -> 27.87 %`.
- **`data/road_wear.json` `detail.1ROAD`** (from / normal / highpass_m / clipped_pct; m0):

  | | from | normal | highpass_m | clipped_pct | m0 |
  |---|---|---|---|---|---|
  | Milford 0.1.12 | asphalt_cracked | asphalt_cracked | - | 0.444 | 0.85588 |
  | Milford 0.1.13 | asphalt_dense | asphalt_dense | 0.5 | **0.069** | 0.85537 |
  | High Plains 0.1.7 | asphalt_cracked | asphalt_cracked | - | 1.27 | 0.76923 |
  | High Plains 0.1.8 | asphalt_dense | asphalt_dense | 0.5 | **0.408** | 0.76923 |

  0091 moves Milford's road, so its m0 moved by 0.0005. High Plains' road is unchanged, and so is its m0.
- **road_wear_check:** PASS on every row, both.
  - Milford: density (111,836 triangles, 0 off), no_repeat (0 claimed twice), detail_phase (worst 1e-05), tone r 0.9555
    (0.1.12 0.959), rubber centroid 0.045 m / depth on line 0.2168 (declared 0.2073).
  - High Plains: tone r 0.8587 and photo_rubber (shipped depth 0.14095 against declared 0.14139) identical to 0.1.7;
    density, no_repeat, detail_phase and the three kerb rows PASS.
- **kn5_textures:** 0 missing on both, `asphalt_dense_normal.jpg` embedded (txNormalDetail) in place of
  `asphalt_cracked_normal.jpg`.
- **mesh_diff against the references:**
  - High Plains' `1ROAD_road` is **equal**: geometry and UVs unchanged; its material's two maps change as said.
  - Milford's 1ROAD changes as 0091 says. Its `road_wear_detail_1road.jpg`, `road_wear_detail_1kerb_sidewalk.jpg` and
    `road_wear_macro.png` change: the line moved.
- **kn5 bytes:** Milford 42,337,727 -> 62,055,573; High Plains 17,730,716 -> 22,156,060. The pilot's own share is small
  (the audit's +1.07 MB); the rest is 0091-0094: Milford's run-off pads alone +11.37 MB (ledger 0092).
- **Stills** (Blender, not the game: no computer use of AC on the PC): a driver's eye 1.1 m over the built road, looking
  60 m ahead along the lap, fov 60, the menu pictures' sun. Each is the reference's next to the rehearsal's from the same
  spot:
  - `tracks/high-plains-lm/source/road_wear/stills/front_straight_s3021_0107_vs_0108.jpg`;
  - `tracks/milford-road-course-lm/source/road_wear/stills/front_straight_s4600_0112_vs_0113.jpg` and `..._s4840_...`.
  The cracked 4 m tile's grid reads plainly in every reference; the owned asphalt shows none. Script: the PC's scratch
  copy of `tools/menu_preview_blend.py` with a seat camera (`SEAT_SPOTS`).
- **Not done:** the far road in game (Kevin's drive).
