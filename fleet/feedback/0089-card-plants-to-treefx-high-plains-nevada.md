---
id: 0089
title: The card plants out of High Plains and Nevada Nights. Nevada's scrub is measured and planted as TreeFX; High Plains' cards were grass and go to GrassFX. New gate fails a TreeFX build that plants fewer trees than it planned
status: in-progress
scope: tracks/high-plains-lm (0.1.6), tracks/exotics-racing-lv-lm (0.1.4); the gate covers every TreeFX track (tools/make_treefx.py)
layer: project (measured inputs per track) + tools (one gate in make_treefx, opt-in keys only these tracks and Milford set)
train: -
---

(Numbered 0089: 0082-0087 are on the Milford branches and `claude/aerial-engine` holds 0088.)

## Symptom

Kevin, 2026-11-08: "We want all treefx as a rule." The PC's audit of all 14 installed tracks (2026-11-09) found two with
card plants in the kn5 and no TreeFX at all:

- **High Plains** (`high_plains` 0.1.5): `PRAIRIECARD_0/1/2` on the ksTree shader with `prairie_atlas.png`.
- **Nevada Nights** (`exotics_racing_lvms` 0.1.3): `SCRUBCARD_0` on ksTree with `desert_scrub_atlas.png`.

And a hole: a fresh worktree on the PC, without the gitignored `.bin` models, planted 0 trees and every gate stayed green.

## What the cards were

| | High Plains 0.1.5 | Nevada Nights 0.1.3 |
|---|---|---|
| Written by | `tools/author_bespoke_blend.py` `cards` (config `scenery.bespoke.cards`) | `author_bespoke_blend.py` `scrub` (config `scenery.bespoke.scrub`) |
| Positions | `source/bespoke/shrubs.json` (`tools/plan_bespoke_vegetation.py`): a 7 m grid with 2.5 m jitter over the pixels NAIP 2023 shows darker green (mean 35-105, G/R > 1.03, G/B > 1.3). These are the draws and swales. | A seeded scatter of 36 points in a polygon over the undisturbed strip north of the lap. 36 is the count of dark clumps NAIP 2019 shows there, but the scatter does not put them where the clumps are. |
| How many | 1,986 planned, **1,898 stood** (88 within 3 m of pavement; `data/bespoke.report.json`) | **36** |
| Species and heights | rabbitbrush 45 % (0.7-1.4 m), bunchgrass 35 % (0.5-0.9), snakeweed 15 % (0.3-0.6), soapweed yucca 5 % (0.5-0.9). All `[invented]` (the plan file says so). | creosote 70 % / bursage 30 %, 1-2 m, "from the plant's habit, not measured" |
| kn5 | 3 meshes, 7,592 gate-OBJ faces, `prairie_atlas.png` | 1 mesh, 144 faces, `desert_scrub_atlas.png` |

## Evidence: the real plants

Data on disk only. Neither site has lidar on this Mac. The 3DEP lidar the G10 read for the camber surveys
(`CO_Eastern_B3_2018`, `NV_ClarkCo_2_B22`) was streamed and not kept.

**Nevada Nights: shrubs, measured.** I used two NAIP years at 0.6 m (2019-07-06 and 2022-06-11, Planetary Computer, public
domain; both committed as `source/vegetation/naip_{2019,2022}_060.png`).

- Method (`source/vegetation/scripts/plan_scrub_naip.py`):
  - Per year, a clump is a run of pixels darker than the 9 m median background by 4 robust spreads, from 2 px to 12 m².
  - A clump counts as a **plant** only when the other year shows one within 1.0 m of it, after the two years' registration shift.
  - The shift is E +0.60 / N −0.60 m: the median nearest-clump offset across the whole crop, over 264 pairs.
  - Shrubs repeat between years. JPEG noise, cars and shadows don't.
- Inside the cards' own polygon: 103 clumps in 2019 and 97 in 2022, **49 in both**.
  - The count holds steady as the match distance changes: 45 at 0.8 m, 49 at 1.0 m, 50 at 1.2 m, 52 at 1.5 m.
  - Each one sits on a visible dark clump (`source/vegetation/clumps_on_naip2019.jpg`).
- **Measured:** each position (2019) and each crown. A crown is the mean area-equivalent diameter over the two years:
  p10 / p50 / p90 **1.07 / 1.59 / 2.25 m**. That includes part of the plant's shadow, so it is an upper bound.
- **Not measured:**
  - Height. Creosote here is about 1-2 m (DOSSIER §6, USDA ESD R030XB005NV; the species reaches 1-3 m). Each clump gets a
    height in 1.0-2.0 m ranked by its measured crown, widest = tallest. This is the published plant community, marked as such.
  - White bursage (0.3-0.8 m, pale grey) can't be told apart from the caliche at 0.6 m. None is planted.

**High Plains: the cards were grass.** NAIP 2023 at 0.3 m (`co_m_3910317_ne_13_030_20230928`, the crop
`tools/naip_crop.py` made for ledger 0081; not committed, 10.7 MB). Stills in `tracks/high-plains-lm/source/vegetation/evidence/`.

- The card ground is the draws and swales. At 0.3 m they show as **continuous** mottled green bands with no discrete crown
  in them (`naip2023_030_draw_ne.jpg`, `naip2023_030_draw_mid.jpg`).
  - That is still-green swale grass on 2023-09-28, when the uplands are straw.
  - Rabbitbrush flowers bright yellow in late September. No yellow points show anywhere.
- The uplands: the same blob reader as Nevada found 1,433 candidates, crown p50 0.68 m.
  - The strongest are shadows of posts, krails, buildings and signs.
  - A random sample of the rest shows road edges, ruts, cars, lot gravel and ant mounds (`naip2023_030_upland_dark_spots_sample.jpg`).
  - None can be told to be a plant, and there is no second 0.3 m year to test which ones persist.
- The published community (Loamy Plains, the eastern Colorado shortgrass) does carry low shrubs: soapweed yucca, broom
  snakeweed, fringed sage, scattered rabbitbrush. They are mostly under 0.6 m and below what NAIP resolves here. QL2 lidar
  (about 2 pts/m²) would not resolve them either. **Not planted.** Seeded positions would be invented.
- So the cards were grass, and the engine already has the answer:
  - `lighting.grassfx` carries a look "B" ("the greener draws taller and full").
  - `scenery.bespoke.grassfx_zones` reads it off the same photo with **the same colour rule the cards used**.
  - The LM port's ship.json never ran `grassfx_aerial`, so 0.1.5 drew the draws in the thin base look, with cards on top.

## What replaced them

**Nevada Nights 0.1.4:**

- The `scrub` key is gone. The new key is `scenery.treefx.planted` (file `source/vegetation/scrub.naip.json`, `clear_m` 4.0 =
  the cards' own `SCRUB_ROAD_CLEAR_M`, the 0.1.3 polygon kept for the planner).
- New zone `planted_desert_scrub` = **Bush.bin : Bush3.bin**, 1 : 1, Lake Murray's generic shrubs as creosote stand-ins by
  growth form. There is no creosote model, and Sage reads as bursage, which isn't planted.
- **49 TreeFX shrubs: Bush 24, Bush3 25.** All 49 clear the roads by 4 m, and the built-surface guard dropped 0.
- Size = height / the model's height and width = crown / (the model's width × size): Milford's opt-in `native_h_m` /
  `native_w_m`, ported verbatim from `claude/milford-019`.
- **The two models' native sizes are not measured on the Mac** (its models are 82 B stand-ins). The config carries 2.0 m
  placeholders under `"_placeholder"`. The new gate refuses real models while that key stands, so the PC must read
  `tree.ini` HEIGHT / WIDTH first (runbook 0089-2 step 2), as it did for Oak3 / SycamoreV2 on Milford.
- `ship.json`: `treefx` after `make_map`, `globs` `source/trees/*.bin`, the points file synced in, `data/treefx.report.json` out.

**High Plains 0.1.6:**

- The `cards` key is gone, documented in `_cards_doc`. **No TreeFX: 0 plants, because NAIP shows no shrub to plant.**
- `ship.json` gains `grassfx_aerial` before `track_folder`. `lm_intake.carry_source` brings `source/naip_2023_hp.jpg` in.
- It writes 32 `[GRASS_FX_ADJUSTMENT_...]` rectangles:
  - **31 × B** (the draws' long grass), 6.84 ha.
  - **1 × C**: the config's own bright-bare-ground look, which comes with the same reading. Deleting class C from
    `grassfx_zones` is the one-line revert if Kevin wants only the draws.
- Frame checked against NAIP: kn5 z = −N; the B boxes sit on the draws (`evidence/grassfx_zones_on_naip2023.jpg`).
- The config's reading is coarse: `cell_m` 30, a cell counts at half fill, at most 48 rectangles. **Only 906 of the 1,986
  card spots fall inside a B box (1,186 within its 10 m fade).**
  - `cell_m` 15 with every rectangle kept (123) would cover 1,339 (1,716 within the fade); `cell_m` 10 (178) 1,458 (1,878).
  - Not changed: it is the config's existing reading. Kevin's call.

## The new gate (tools/make_treefx.py `treefx_gate`, hard; fleet/GATES-CHANGELOG.md 2026-11-09)

`build()` stops with exit 1 in three cases:

1. Fewer trees are written than `plan(all_species=True)` places (the same positions and guards; only the model choice
   needs the files).
2. A model `trees.txt` names is not beside it, or not in `source/trees/`.
3. `planted.native_h_m` / `native_w_m` still say `_placeholder` while the copied models are real (> 4 kB).

Notes:

- It reads only. `trees.txt`, `ext_config.ini` and `treefx.report.json` are unchanged; one `[treefx] gate:` line is printed.
- A mixed zone short of one model plants every spot with the zone's other models and only **warns**. The existing tests
  (and the Lake Murray plan) count on that.
- Every TreeFX track gets it: `tools/ship_track.sh` and `tools/ship_sd.sh` both call `build()`.
- **Proof:** Nevada 0.1.4 from an empty workshop without the models stops at the treefx step:
  `0 trees written, 49 planned (short per zone {'planted_desert_scrub': 49}; models absent: ['Bush.bin', 'Bush3.bin'])`,
  exit 1 (`records/gate_proof_no_models.txt`). With the stand-ins: `49 written of 49 planned -> OK`.
- `tests/tools/test_treefx_gate.py` has 6 tests.

## The builds (Mac, 2026-11-09)

Each built with `tools/ship_track.sh <track> --no-install` (Blender path swapped to the Mac's 4.2.9) from an **empty**
workshop:

- ENG = the engine-july snapshot's `scripts/` + `vendor/` with airoso's `assets/textures`.
- Baseline = `07cc303` (`git archive`); branch = this head.
- Placeholder bins: 82 B text files copied into the source tree's `tracks/<track>/source/trees/` (Milford's way).
- No force. Every chain gate is green.

Gate column, baseline 07cc303 → branch. Every scalar in every gate JSON is equal; only file paths differ (`records/gates_*_base_vs_br.json`).

| gate | High Plains 0.1.5 → 0.1.6 | Nevada 0.1.3 → 0.1.4 |
|---|---|---|
| drive_test: soft top / severe / kinks per km / drops / undrivable | 0 / 0 / 0.62 / 0 / 0 = | 0 / 0 / 0.00 / 0 / 0 = |
| audit_mesh: A-K defects | 0 = | 0 = |
| kn5_ground_check: road over ground > 5 cm | 0 / 1,908, p95 0.021 = | 0 / 1,422, p95 0.021 = |
| house_seat | PASS = | PASS = |
| edge_report (not a gate) | 4,051 scalars equal | 2,311 scalars equal |
| treefx gate | (no TreeFX) | 49 / 49 OK |
| SHIP | OK | OK |

**mesh_diff vs 07cc303** (`records/mesh_diff_*.json`): only the card meshes are gone.

- High Plains: `PRAIRIECARD` × 3 only in 0.1.5; every 1GRASS, 1KERB, 1ROAD, 1WALL, BUILDING, MARKINGS, PADAPRON and
  ROOFTOP mesh equal. Texture `prairie_atlas.png` gone.
- Nevada: `SCRUBCARD` × 1 only in 0.1.3; every 1GRASS, 1KERB, 1ROAD, 1RUNOFF, 1WALL, BUILDING, FARBLOCK, MARKINGS,
  PROPCONE and ROOFTOP mesh equal. Texture `desert_scrub_atlas.png` gone.
- Gate OBJ, group by group: 39 / 36 groups equal, and only the card groups are missing.
- Track folders: only the kn5, `ext_config.ini` ([TREES] / GrassFX adjustments), README / ui_track (version) and the new
  `extension/trees/` differ; the AI, map and inis are equal.

Sizes (road kn5):

| track | before | after |
|---|---|---|
| High Plains | 15,643,426 B (md5 694473d4…) | **14,511,475 B** (4b06720e…) |
| Nevada | 19,103,062 B (ce9218de…) | **18,970,521 B** (34bbb818…) |

The PC's builds will differ in bytes (tangents; kn5_equiv), not in meshes.

**Lake Murray unchanged:**

- `git diff 07cc303 -- tracks/san-diego-lake-murray` is empty, and no Lake Murray key is touched.
- trim A/B: `tools/trim_connectors.py` is byte-identical (md5 8a456516…). Run on both sides: connectors 664da93b…,
  mouths b73b70f4…, and the log, all equal.
- make_treefx A/B: `plan(all_species=True)` against 07cc303 gives the same md5 on every TreeFX track; Lake Murray is
  8ce38a01…, 21,219 lines.
- With 15 placeholder models in place, Lake Murray writes 21,171 of 21,171 planned with 14 species, so the gate passes.
- Records: `records/lm_checks.log`, `ab_treefx.log`, `lm_gate_sim.log`.

**Stills** (Blender Eevee on the split scene, car height 1.2 m and above, the same cameras before and after). The plants
are **stand-ins**: one ellipsoid per shrub at its height and crown. High Plains' "after" frame is shown twice, once bare
and once with the B zones drawn as flat green sheets standing in for GrassFX, which Blender can't draw. Mac only:
`work/treefx/stills/pair_{nv,hp}_*.jpg`.

## Owed

- **PC:** measure Bush / Bush3 `tree.ini` HEIGHT / WIDTH (runbook 0089-2 step 2), commit them, then rehearse and install both.
- **Lidar, if Kevin approves the download:**
  - a vegetation-return read over High Plains' draws and west escarpment (`CO_Eastern_B3_2018`, the EPT the camber survey
    used): it would show whether any plant stands taller than 0.5 m there;
  - and over Nevada's strip (`NV_ClarkCo_2_B22`): it would turn the ranked heights into measured ones.
- High Plains' GrassFX reading resolution (`cell_m` / `max_rects`, above): Kevin's call.
- Menu pictures: unchanged (not regenerated; neither showed the cards prominently).
- Not driven.

## PC runbooks

Both use the same ENG copies as the edge-flush installs (`eng_hplm`, `eng_nvlm`; ledger 0078 table). No new texture is
needed: the card atlases are simply no longer referenced.

**0089-1 — High Plains 0.1.6** (`high-plains-lm`, workshop `D:/k10-scratch/high_plains_lm`, installs as `high_plains`):

1. `git fetch && git worktree add D:/k10-worktrees/treefx origin/claude/treefx-cards`.
2. Rehearse from an EMPTY workshop:
   `mkdir -p D:/k10-scratch/hp_treefx_reh/data`, then
   `SHIP_PROJ=D:/k10-scratch/hp_treefx_reh AIROSO=D:/k10-worktrees/treefx ENG=D:/k10-scratch/eng_hplm bash tools/ship_track.sh high-plains-lm --no-install`.
3. Compare every row with the Mac's (`tracks/high-plains-lm/source/vegetation/records/`):
   - drive_test 0 / 0 / 0.62 / 0 / 0, audit 0, kn5_ground 0 / 1,908;
   - `[grassfx] ... cells per look {'B': 76, 'C': 2}; 32 rectangles` and `grassfx.aerial.json` byte-equal;
   - mesh_diff against the installed 0.1.5 kn5: only `PRAIRIECARD_*` gone.
4. Green: install. Move the old workshop to `high_plains_lm.0.1.5`, then run the same command without `SHIP_PROJ` and
   without `--no-install` (AC closed). The old folder goes to the archive as usual.

**0089-2 — Nevada Nights 0.1.4** (`exotics-racing-lv-lm`, workshop `D:/k10-scratch/exotics_lm`, installs as `exotics_racing_lvms`):

1. Worktree as 0089-1.
2. **Models and their sizes.**
   - Copy `Bush.bin` and `Bush3.bin` from `content/tracks/san_diego_lake_murray_v4/extension/trees/` into
     `D:/k10-worktrees/treefx/tracks/exotics-racing-lv-lm/source/trees/`.
   - Check the md5s: **Bush e150b090…, Bush3 e9299a59…**. Stop if they differ.
   - Read each model's `tree.ini` HEIGHT and WIDTH, as Milford's Oak3 / SycamoreV2 were read.
   - Write them into `track.config.json` `scenery.treefx.planted.native_h_m` / `native_w_m` (both models) and delete both
     `"_placeholder"` keys. Until then the chain stops at treefx: "placeholders but ... are real models".
   - Commit ("Nevada 0.1.4: the shrub models' measured sizes (PC)") and push with fetch + rebase.
3. Rehearse from an EMPTY workshop:
   `SHIP_PROJ=D:/k10-scratch/nv_treefx_reh AIROSO=D:/k10-worktrees/treefx ENG=D:/k10-scratch/eng_nvlm bash tools/ship_track.sh exotics-racing-lv-lm --no-install`.
4. Compare every row with the Mac's (`tracks/exotics-racing-lv-lm/source/vegetation/records/`):
   - drive_test 0 / 0 / 0.00 / 0 / 0, audit 0, kn5_ground 0 / 1,422, house_seat PASS;
   - `[treefx] gate: 49 written of 49 planned ... -> OK`; `trees.txt` positions equal to `records/trees.txt`
     (only `size` / `width` move with the measured native sizes);
   - mesh_diff against the installed 0.1.3 kn5: only `SCRUBCARD_0` gone.
5. Green: install as 0089-1 step 4 (old workshop to `exotics_lm.0.1.3`).
