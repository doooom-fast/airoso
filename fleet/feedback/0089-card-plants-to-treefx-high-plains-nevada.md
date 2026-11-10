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

## PC: rehearsals and installs (2026-11-09)

- **Models**: Bush e150b090 / Bush3 e9299a59 copied from `san_diego_lake_murray_v4/extension/trees/`, never committed.
  - tree.ini [BASIC] read from each .bin (zip): Bush HEIGHT 20.66 / WIDTH 34.38, Bush3 2.02 / 3.49.
  - Bush's HEIGHT is ten times Bush3's though both are shrubs; their LOD0.mesh differ. Taken as read, as Oak3 / SycamoreV2 were.
  - Placeholders removed: 968cbed.
- **Rehearsals** from EMPTY workshops `D:/k10-scratch/{hp,nv}_treefx_reh`, ENG `eng_hplm` / `eng_nvlm`: SHIP OK, no force, every GATES row exit 0.
  - **High Plains 0.1.6**:
    - The road kn5 is 14,511,475 B, the Mac's to the byte.
    - `[grassfx] ... {'B': 76, 'C': 2}; 32 rectangles`; `grassfx.aerial.json` byte-equal (LF) to `records/grassfx.aerial.json`.
    - mesh_diff against the installed 0.1.5: only `PRAIRIECARD` x 3 gone, texture `prairie_atlas.png` gone, every other mesh equal.
    - drive_test / audit / kn5_ground rows equal to the installed build's.
  - **Nevada Nights 0.1.4**:
    - The road kn5 is 18,970,521 B, the Mac's to the byte.
    - `[treefx] gate: 49 written of 49 planned ... -> OK`.
    - trees.txt has the same 49 species, positions and angles as `records/trees.txt`; size and width move with the measured native sizes (Bush 0.94 -> 0.09 x 20.66 m = 1.86 m, as 0.94 x 2.0).
    - mesh_diff against 0.1.3: only `SCRUBCARD_0` gone, texture `desert_scrub_atlas.png` gone.
    - Rows equal to 0.1.3's.
- **Installed** 2026-11-09 18:30 / 18:34 from EMPTY workshops; the old ones are kept as `high_plains_lm.0.1.5` / `exotics_lm.0.1.3`.
  - kn5_equiv to the rehearsals (tangents only).
  - The install step parked 0.1.5 in `D:/k10-track-archive/2026-11-09_183038/` and 0.1.3 in `2026-11-09_183401/` (MOVES.tsv + README).
  - Nevada's folder carries both .bin (md5 as above) and 49 trees.
- **Menu pictures**: re-rendered with the same cameras; the packs' own are in `2026-11-09_183441_previews`.
- Not driven.

## The lidar reads (Kevin, 2026-11-09: "Yes, both")

### The downloads (Mac, 2026-11-09)

Each one has its own directory under the scratchpad's `sys/dl/`. They are not in the repo, and nothing is on /Volumes/Drive.

- **Size first**, by HTTP HEAD on every node the box needs: High Plains 16.2 MB (cap 120), Nevada 8.0 MB (cap 40).
- The points were decoded on the G10 (`systemd-run --user --scope -p MemoryMax=4G -p MemorySwapMax=0 nice -n 19 ionice -c3`;
  the five camera services were active before and after). The box's points came back as an npz.

| site | URL | files | bytes |
|---|---|---|---|
| High Plains | `https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_Eastern_B3_2018/` | `ept.json`; 3 `ept-hierarchy/*.json`; 108 `ept-data/<D-X-Y-Z>.laz` (depths 0-11, every node meeting -103.9065..-103.8885, 39.7327..39.7378); `ept-sources/list.json` | 2,522; 68,303; **16,228,435**; 5,542,645 (fetched to date the flight, not used: GPS time did that) |
| Nevada | `https://s3-us-west-2.amazonaws.com/usgs-lidar-public/NV_ClarkCo_2_B22/` | `ept.json`; 5 `ept-hierarchy/*.json`; 40 `ept-data/*.laz` (box -115.0214..-115.0185, 36.2836..36.2853) | 2,534; 266,369; **7,993,981** (`ept-sources/list.json`: 404) |

- Flights, read off the returns' GPS time: **High Plains 2018-06-12..16, 3.1 returns/m²**; **Nevada 2022-07-28, 10.0
  returns/m²**. That is seven weeks after NAIP 2022-06-11.
- Tools, committed beside each track: `source/vegetation/lidar/` (`ept_plan.py`, `ept_extract.py`, `hag.py`,
  `shrubs.py`, `clump_heights.py`).

### High Plains: nothing taller than 0.5 m in the draws or on the west bank. No build.

- Method: `lidar/shrubs.py` takes the highest return in each 0.5 m cell over the 1 m class-2 ground; cells over 0.5 m are
  joined into objects.
- Result: 1,613 "plant-sized" objects (2 or more returns, under 4 m tall and 6 m wide), 79 structures and 629 single specks.
- 356 of them lie within 7 m of a 0.1.5 card spot. On NAIP 2023 every one of those is a K-rail or wall run, the perimeter
  fence along the south boundary, a marshal post, or the steep cut of the west bank (a ground-model artefact on a slope).
  Evidence: `evidence/lidar2018_objects_over_0.5m.jpg`, `lidar/objects_over_0.5m.json`.
- **The draws themselves (the NE swale, the dendritic draws mid-infield, the east draws) hold no object over 0.5 m.**
- At 3.1 returns/m² a 1 m crown takes about 3 returns, so a shrub that size would show. Anything lower stays under the
  lidar, as under NAIP.
- High Plains stays 0.1.6, GrassFX on the draws.

### Nevada Nights 0.1.5: the clumps at their lidar heights

- Method (`lidar/clump_heights.py`, `scrub.lidar.json`):
  - Each of the 49 NAIP clumps takes the returns inside its crown radius, with noise classes 7 / 18 out.
  - Its **height = the second-highest return** over a plane fitted to the class-2 ground 1-4 m beyond it. One stray
    return doesn't make a shrub.
- Result: **p10 / p50 / p90 0.03 / 0.10 / 0.21 m**. 4 clumps reach 0.3 m or more (1.66, 0.44, 0.32, 0.30); 0.1.4 gave all
  49 between 1.0 and 2.0 m.
- Checks that this is not a registration error:
  - All 90 persistent NAIP clumps in the lidar box, the I-15 median's included, read the same (p50 0.09 m).
  - NAIP darkness and lidar height correlate at 0.03-0.05 at every shift up to ±5 m (2019 and 2022).
  - The lidar's own standing objects in the polygon (20 with 5 or more returns over 0.3 m) are not on the clumps. Some are
    flat-topped: a 5 m object 2 m tall, a 3 m slab at 0.62 m.
  - The vendor's class 18 (high noise) is spread over lots, roads and scrub alike. It is not vegetation.
- What the dark clumps are, the data can't say. They are not 1-2 m creosote: they stood 0.1-0.2 m tall in July 2022.
- **Planted:** a clump stands when its top clears **2× its own ground's scatter**, about 95 % confidence (`K_SD` 2.0, not
  tuned). **28 of 49 do, at their measured heights 0.05-1.68 m (median 0.13)** and their NAIP crowns.
  - The other 21 have no height the lidar separates from the ground and are not planted.
  - `scripts/plan_scrub_measured.py` writes `scrub.measured.json`, which the config now names.
- **Model: Bush3 only.**
  - Bush's tree.ini reads HEIGHT 20.66 / WIDTH 34.38 m: ten times Bush3 (2.02 / 3.49), with the same proportions
    (W/H 1.66 vs 1.72).
  - Lake Murray's own use says Bush draws as a 1-2 m shrub:
    - its median planting at Bush 0.35-0.6 was "a little too tall" to Kevin (2026-10-09). At 20.66 m that would be 7-12 m
      median "bushes".
    - its yard / scrub mixes use it at 0.6-1.0, which would be 12-20 m.
  - So HEIGHT is most likely not Bush's drawn height. **If so, 0.1.4's 24 Bush shrubs drew at about a tenth of their
    sizes** (about 0.1-0.2 m).
  - It can't be settled on the Mac (82 B stand-ins). Owed on the PC (runbook 0089-3 step 2).
  - `planted_desert_scrub` is Bush3 only until then. Lake Murray's planting is untouched: it sizes by mix ranges, not
    tree.ini.

### Nevada 0.1.5 build (Mac, empty workshop, stand-in bins)

- Built at this branch's head; compared against 0.1.4 rebuilt from `1aeecb8`.
- Gate column. Every gate scalar is equal between 0.1.4 and 0.1.5 (`records/0.1.5/gates_nv_014_vs_015.json`):

| gate | 0.1.4 → 0.1.5 |
|---|---|
| drive_test (soft top / severe / kinks per km / drops / undrivable) | 0 / 0 / 0.00 / 0 / 0 = |
| audit A-K | 0 = |
| kn5_ground (road over ground > 5 cm) | 0 / 1,422, p95 0.021 = |
| house_seat | PASS = |
| edge_report | 2,311 scalars equal |
| treefx gate | 49 / 49 → **28 / 28 OK**, species Bush3 only |
| SHIP | OK, no force |

- mesh_diff 0.1.4 → 0.1.5: every mesh equal, no texture changed. The road kn5 is 18,970,521 B both times; the md5 differs
  run to run (tangents).
- The gate OBJs are equal group by group (36 / 36).
- Track folders: only trees.txt, ext_config ([TREES] count), README / ui (version) differ, and `Bush.bin` is no longer copied.

Lake Murray:

- `git diff 07cc303 -- tracks/san-diego-lake-murray` is empty.
- make_treefx `plan(all_species=True)` against 07cc303 gives 8ce38a01…, 21,219 lines, on every TreeFX track.
- `trim_connectors.py` is byte-identical, so the trim A/B is equal as before.

Stills are stand-ins, one ellipsoid per clump at its height and crown: 0.1.4 (ranked 1-2 m) over 0.1.5 (lidar), the same
cameras. In 0.1.5 most clumps draw as low mats. Mac only: `work/treefx/stills/pair_nv014_nv015_*.jpg`.

### 0089-3 — Nevada Nights 0.1.5 PC runbook

1. `git -C D:/k10-worktrees/treefx fetch && git -C D:/k10-worktrees/treefx checkout --detach origin/claude/treefx-cards`.
   - `source/trees/Bush3.bin` must be there, md5 e9299a59…; copy it again from `san_diego_lake_murray_v4` if not.
   - Bush.bin is no longer used.
2. **Bush's drawn height (report only; nothing is changed by it):**
   - Unzip `Bush.bin` and `Bush3.bin` and read each `LOD0.mesh`'s vertex extent (the drawn geometry), set beside tree.ini HEIGHT.
   - Or plant one of each at `size = 1` side by side in a scratch trees.txt and look in game.
   - Record which is true in this ledger.
3. Rehearse from an EMPTY workshop:
   `SHIP_PROJ=D:/k10-scratch/nv_015_reh AIROSO=D:/k10-worktrees/treefx ENG=D:/k10-scratch/eng_nvlm bash tools/ship_track.sh exotics-racing-lv-lm --no-install`.
4. Compare with `tracks/exotics-racing-lv-lm/source/vegetation/records/0.1.5/`:
   - `[treefx] gate: 28 written of 28 planned ... -> OK`;
   - trees.txt equal to `records/0.1.5/trees.txt` (the native sizes are committed, so it should be byte-equal);
   - drive_test / audit / kn5_ground / house_seat rows as above;
   - mesh_diff against the installed 0.1.4: every mesh equal.
5. Green: install, as 0089-1 step 4 (old workshop to `exotics_lm.0.1.4`).

### Owed (updated)

- Bush's drawn height (0089-3 step 2).
- Nevada: what the dark NAIP clumps are. The lidar says they stand 0.1-0.2 m. A site photo or Street View from Speedway
  Blvd would settle it; nothing more to fetch.
