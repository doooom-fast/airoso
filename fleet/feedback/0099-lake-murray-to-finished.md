---
id: 0099
title: Lake Murray toward finished, round 1 (0.20.3): it rebuilds from an empty workshop, both lamp heads lit, the kerb rumble on, the owned asphalt and concrete; kerb stills and the species check for Kevin
status: open
scope: tracks/san-diego-lake-murray (0.20.2 -> 0.20.3); tools/ship_track.sh + tools/ship_track_spec.py (sync_in.seed, opt-in); tools/author_lamp_heads_blend.py (new, opt-in); tools/check_lights_ini.py (both-heads count, opt-in); round 1c (0.20.3 -> 0.20.4): tools/author_walk_grade_blend.py (new, opt-in route.walk_back_grade: author step walk_grade + its --seat prep sub-step)
layer: project + tools
train: -
---

## Request (Kevin, 2026-11-22)

> "let's complete lake murray, sand creek, and high plains" — then "go".

His answers on the calls page (verbatim option text):

| Question | Kevin's answer | This round |
|---|---|---|
| 33 tall median plants | "Keep all 33 at their lidar heights" | no change |
| Median-nose K-rails | "Keep them one vertex before the tip" | no change |
| College/Navajo J1 | "Tilt it now" | notes for the PC (below); not built here |
| Kerb rumble | "Turn it on, sidewalks included" | done |
| How dirty the race kerbs look | "Show me stills first" | stills made |
| Road wear | "Full road wear at 10 cm" | notes for the PC |
| Roadmap phases 3-5 | "Phase 3 is part of finished" | notes for the PC |
| More tree species | "Now: those trees and flowering shrubs" | checked; the models are missing (below) |
| Two-arm lamps | "Yes, light both heads" | done |
| Owned asphalt and concrete | "On every track now" | done on Lake Murray's road and sidewalks |

The open work besides: College Ave "realism+" (ledger 0055: "can you split them up and do something fun? i would prefer
realism+"), the sidewalk re-author (the 96 forced street drops), and the rebuild from an empty workshop (ledger 0090
"Open").

Scope (the orchestrator, same day): this entry is round 1 on the Mac. College Ave, the J1 tilt, Phase 3 and road wear go
to a PC session, where `lm_phase2/project` lives. What the Mac found for them is under "Notes for the PC".

Nothing here is installed. Every number below was measured on the Mac on 2026-11-22 unless marked [invented] or
[estimate].

## 1. The rebuild from an empty workshop

**What was wrong (ledger 0090 "Open", confirmed).**
- `ship.json` named the `lm_v4` workshop. That workshop holds v4's own 0.20.1 blend and data; 0.20.2 was built in the
  scratch `lm_phase2/project`.
- `sync_in` never carried `loop.blend`, nor the draft's data the `--skip-blend` steps read. An empty workshop stopped at
  "no blend yet".
- Two more inputs the chain reads crossed neither way: `data/centerline.geojson` (`scripts/ac/track_folder.py`, the lap
  length; it would stop the track folder) and `data/centerline.elevation.json` (`scripts/geometry/drive_test.py`, the
  replication rows).
- **A new gap, found here.** `scenery.treefx.median_measured.file` (the 2026-11-19 config change, "B: lidar height each")
  names `source/vegetation/median_heights.lidar.json`. `tools/make_treefx.py` reads it from the project, and no list
  carried it. So every rebuild since 2026-11-19, from any workshop, would stop at the TreeFX step.

**The fix.**
- `tools/ship_track_spec.py`: a new `sync_in.seed` list (opt-in). It holds plain relative paths; templates are refused.
  A spec that names no seed emits no `in.seed` line, so every other track's chain reads exactly as before.
- `tools/ship_track.sh`:
  - a seed is copied into the project only where the project has no file there yet. It never overwrites a workshop's own
    file; a kept file that differs from airoso's is named.
  - every seed must exist in airoso. A Git LFS pointer (an un-pulled `loop.blend`) is refused, exit 1.
  - a seeded `loop.blend` passes the "no blend yet" guard (`seed_blend_ready`).
- `tracks/san-diego-lake-murray/ship.json`:
  - `workshop_project` `lm_v4` -> **`lm_line`**: a fresh workshop the chain creates and fills from airoso. `lm_v4` and
    `lm_phase2/project` stay as records; neither is touched.
  - `sync_in.seed`: **70 files**. The rule is: every sync_out file airoso holds that sync_in does not already bring.
    That is `loop.blend` (sha256 3f13b887…, 189,063,384 B, 0.20.2's), 67 data files, and the two centreline files above.
  - `sync_in.optional` + `source/vegetation/median_heights.lidar.json`.
  - `sync_out.files` + `data/centerline.geojson`, `data/centerline.elevation.json`, `data/lights.heads.json`.
  - The north layouts' own records (`lap.north.json`, `barrier_bands.north.json`, `dummies_north_*.json`, …) are not in
    airoso: 0.20.2 was built in a scratch workshop that never synced back. The author, ship and gate steps write every one.

**Proof on the Mac (as far as the Mac goes).**
- An empty scratch workshop, the real `ship.json`, `--skip-blend --dry-run`: the guard passed, and the sync-in printed
  `seeds: 70 copied from airoso, 0 kept as the workshop had them`. The workshop held 241 MB.
- The chain then stopped at `tools/ship_track.sh`'s `declare -A RK BB` (an associative array, bash 4): macOS's `/bin/bash` is 3.2. The PC's Git Bash
  runs it. That is a Mac limit, not a missing input.
- So the author phase was run by hand on the seeded workshop, step by step, as the chain runs it:

  | Step | Result | Against airoso's committed copy |
  |---|---|---|
  | `tools/barrier_bands.py` | exit 0, 15.1 s; planned no_route PASS on all 4 race layouts (leak 0; reached 138,756 / 138,195 / 88,417 / 91,688 m²) | `barrier_bands.json`: 4 leaves differ, all run seconds |
  | `tools/layout_dummies.py` | 5 layout files | `dummies_street`, `_race_cw`, `_race_acw`: byte-identical |
  | `tools/author_race_furniture_blend.py` (**Blender 5.1.2**, not 4.2) | exit 0 | `race_authored.json`: 3 leaves differ: `removed_existing` 43 -> 85 (the PC's 0090 proof saw exactly this: the seed blend already holds 2f's furniture), `seconds`, `blend` |
  | `tools/author_signs_blend.py` + `verify_signs.py` | 29 posts, PASS | `signs.local.json` / `signs_measured.json` differ in the north layouts' rows (walls, spawn checks; 27 / 11 leaves): airoso's copies are 0.20.1's three-layout records |
  | `tools/verify_race.py`, mainline and `--lap north` | exit 0, both | `race_verify.json`: 0 leaves differ |
  | `tools/author_lamp_heads_blend.py` (new, item 2) | exit 0 | 323 back lenses |

- The prep (engine-july's `build_kn5_loop.py`) and the split also ran under Blender 5.1.2, on the snapshot engine plus
  airoso's `assets/textures`: see "Mac prep attempt" below. The export needs Blender 4.2 and the installed AC add-on:
  PC only.

**Inputs that live only on the PC.**
1. **engine-july** (`ENG`): the prep, the exporter and the spawn builder. Its code is in
   `tracks/san-diego-lake-murray/engine-july-snapshot` (50 files in its MANIFEST.md5). The 56 textures it stages are recorded in
   `REFERENCED.md5`, not copied: 52 are md5-identical to airoso's `assets/textures`. The 4 that differ
   (`pine_leaves.png`, `poplar_bark.png`, `poplar_leaves.png`, `street_lamp_new.png`) bind PINETREE / POPLAR* / LAMPNEW,
   and Lake Murray has none of those. `PENDING-MIRROR.md5` says the snapshot is ahead of the live engine-july on three
   files: `build_kn5_loop.py`, `pbr.py`, `export_kn5_addon.py`. So "snapshot + assets/textures" may stand in for
   engine-july, but no build has shown it. Runbook 0099-1 run B tests it.
2. **Blender 4.2 with the AC Tools add-on v1.0.7 installed** (snapshotted under `appdata-addons/`, but it has to be
   installed to export).
3. **The 16 TreeFX models**, `source/trees/*.bin`: personal-use, gitignored, never committed. A fresh worktree has none.
   Without them `make_treefx` has no species to plant (0.20.2: 21,111 trees, 14 species). `sync_in.globs` copies them
   from airoso's track folder, so they must be put there first.
4. Only for `STREET_AI=july` (not the default): `D:/k10-track-archive/2026-10-11/san_diego_lake_murray/ai`.
5. For the comparison only: the installed `san_diego_lake_murray_v4` and the 0090 proof's records.

## 2. Both heads of the two-arm lamps lit

Kevin: "Yes, light both heads".

**What was dark.** The LED lamp (`led_cobra`, arms 2; ledger 0056) has two luminaires back to back. The draft gives it ONE
lens, `LIGHTS_0`, at the road-ward head only. `scripts/ac/ext_config.py` clusters the exported LIGHTS* vertices into one
CSP `[LIGHT_N]` per lens, so the back head has stood dark since v0.18.1.

**The fix (opt-in: `scenery.streetlights.light_both_heads` true; Lake Murray only).**
- `tools/author_lamp_heads_blend.py`: a new author step, `lamp_heads`, first in `steps.author` (it reads only the
  draft's LIGHTS_0 and lamp record, which no author step writes; the race steps keep their order). It runs on every ship and is
  idempotent. Each `LIGHTS_0` lens face is paired with its lamp (centroid within 0.01 m of `provenance.lens_xyz`), then
  turned half a turn about that lamp's own pole axis (`lamp_bases_xz`), into one new mesh, `LIGHTS_back`.
  - The twin model is symmetric: every vertex of `streetlight_led_post_twin.obj` has its mirror at -x, and the lens is
    symmetric across its own z = 0 (both tested). So the turned lens is exactly the back luminaire's lens.
  - It writes `data/lights.heads.json` (the back lenses, local frame, `lens_xyz`'s order).
  - Not opted in: the step removes a stale heads file and opens no blend.
- `ext_config.py` is unchanged: it clusters the new mesh like the old one, and the night glow covers every `LIGHTS*_mat`.
- `tools/check_lights_ini.py`: opted in, it wants one light at every front AND every back lens, each within the same
  0.05 m; opted in without the heads file = FAIL. Not opted in = the check as before. (GATES-CHANGELOG 2026-11-22.)

**Measured on Lake Murray's lamps** (the seeded workshop, Blender 5.1.2):
- 323 lamps -> 646 lenses; 323 back lenses written; the read-back worst 0.00058 m.
- Lens to pole: 4.0366-4.0386 m on every lamp (the model: 4.0376 m).
- The closest two lenses of all 646: 8.073 m apart. ext_config's link is 2 m, so they stay 646 lights.
- Each lens centroid to the nearest LIGHTPOST vertex (its luminaire housing): front p50 0.2055 m (0.2053-0.2057), back
  p50 0.2055 m (0.2044-0.2066).
- Run twice: one `LIGHTS_back`, 1,292 vertices / 323 faces, as `LIGHTS_0`.
- ext_config's own clustering, on the lens quads rebuilt from the record: 646 clusters, each within 0.01 m of a lens; the
  ini written from them passes the both-heads check (646 matched) and fails the one-per-lamp check (tested).
- Expected on the build: CSP lights 323 -> 646 with the same look per light. `kn5_ground_check`'s `lamp_heads` statistic
  reads about 646 (a statistic, not a threshold); every back lens has its housing within 0.21 m, inside that check's
  3 m / 2.5 m mast test. The night's frame cost of twice the lights (each light's `SHADOWS = 1`) is [not measured]:
  Kevin's drive.

## 3. Kerb rumble on, sidewalks included

Kevin: "Turn it on, sidewalks included".

- `track.config.json` `kerb_ff_effect: 1`. `scripts/ac/track_folder.surfaces_ini` (ledger 0053, already wired) writes
  `FF_EFFECT=1` on the KERB surface only; every other surface keeps 0.
- KEY=KERB is every `1KERB_*` mesh, so the race kerbs and the street sidewalks (`1KERB_sidewalk`, 114,081 m² per 0053)
  all give the wheel kerb effect. VIBRATION_GAIN 1.0, VIBRATION_LENGTH 1.5, kerb.wav and FRICTION 0.92 are unchanged.
- No other track's config sets it (tested).

## 4. Stills of the race kerbs as built, for the dirt question

Kevin: "Show me stills first". **Blender stand-ins, not Assetto Corsa**, and labelled so in each picture.

- `tracks/san-diego-lake-murray/source/stills/kerb_dirt_770_out_entry.jpg`: the College hairpin's outside kerb, race_cw's
  entry. The heaviest rubber is -59.1 to -49.8 m from the apex.
- `tracks/san-diego-lake-murray/source/stills/kerb_dirt_770_out_close.jpg`: the same kerb, close on that heaviest rubber.
- `tracks/san-diego-lake-murray/source/stills/kerb_dirt_3296_out.jpg`: Jackson / Lake Murray Blvd's outside kerb,
  race_cw's entry. The heaviest rubber is -16.1 to -11.3 m from the apex.

How they were made (`kerb_dirt_stills_blend.py` + `kerb_dirt_label.py` beside them; the camera record is
`kerb_dirt_stills.json`):
- The committed `loop.blend` (0.20.2's, race furniture authored) under Blender 5.1.2 Cycles, 128 samples. Nothing saved.
- Bound as the prep binds: the AC names, the prep's 4 m planar UVs, `pbr.setup_material` with the config's overrides AS
  0.20.2 BUILT THEM. So the road is still the borrowed cracked asphalt; the 0099 owned rows are left out.
- The kerbs wrap `kerb_race_worn_*` with their own UVs: the four rubber levels race_authored.json records. 770_out:
  119.9 m long, metres at level 0/1/2/3 = 86.2 / 10.1 / 8.8 / 14.8. 3296_out: 51.4 m, 28 / 8 / 5.8 / 9.6.
- The eye is 1.10 m over the road, 3.0 m in from the kerb (the close look: 1.5 m), fov 60 deg; all three numbers are
  [invented]. The sun is the menu pictures' (San Diego, 7 Nov, 15:30 PST: azimuth 228, elevation 22 deg).
- How dark level 3 is and how much of each kerb carries it are 0053's guesses: Kevin's call from these.

## 5. More tree species: what exists

Kevin: "Now: those trees and flowering shrubs" (ledger 0040: eucalyptus, jacaranda, flowering shrubs).

- **No TreeFX model is in the repo.** `*.bin` is gitignored (personal-use mod content, ledger 0040). `tools/make_treefx.py`
  names 15 models; 0.20.2 planted 14 of them (all but SycamoreV3; the workshop held 16 .bin) (`data/treefx.report.json`).
- **Eucalyptus: the model exists on the PC.** `Gum.bin` (Algarve, ledger 0040: "Gum = eucalyptus"). 0.20.2 already plants
  1,419 of them, in the uniform mixes and in Jackson's E1 gum belt (that zone holds 73 plants, mostly Gum). They stand by
  mix, not where the real groves stand.
  - What a measured rule has to work with: the G10's lm-shrub lidar tops (USGS 3DEP CA_SanDiegoCo_D24, flown Nov 2024, 24
    road tiles; `jobs-20261113/lm/out_24tiles/lm_shrub.tops.npz` on the scratch disk). There are 1,598,756 tops; 1,343,335
    are flagged plant and not solid.
    | Plant tops at least | Count | Within 40 m of pavement | Crown p50 |
    |---|---|---|---|
    | 20 m | 17,029 | 2,471 | 4.2 m |
    | 25 m | 3,642 | 494 | 4.5 m |
    | 30 m | 482 | 64 | 4.8 m |
    The tallest is 43.5 m. (A tree may hold more than one top.)
  - **Not wired here, for two reasons.** (1) Height does not name a species. A rule "a top of at least N m is a gum" has
    an [invented] N; it needs Kevin's word, or a NAIP / Street View check of a sample. (2) Planting at measured heights
    (`scenery.treefx.planted`) needs `Gum.bin`'s tree.ini HEIGHT / WIDTH, which only the PC can read (as 2026-11-19 read
    Bush.bin's).
- **Jacaranda: no model.** None in the repo, the tools, or 0040's inventory (No Hesi, Algarve, shuto).
- **Flowering shrubs** (bougainvillea, oleander, hibiscus, lantana, bird of paradise, India hawthorn; ledger 0040): **no
  model** of any of them. Ice plant is ground cover, so it may belong to GrassFX or the ground texture.
- **What is needed:** TreeFX `.bin` models of a jacaranda and of the flowering shrubs, from Kevin's own library or a mod he
  is licensed to use personally (as the No Hesi / Algarve sets), or self-made. Their source is not known here. Nothing was
  invented and nothing downloaded. All vegetation stays TreeFX.

## 6. The owned asphalt and concrete

Kevin: "On every track now". The High Plains / Milford pattern of ledger 0095.

- `texture_overrides["1ROAD"]` -> `assets/textures/asphalt_dense_{diffuse,normal}.jpg` (`tools/make_owned_surfaces.py`, seed
  84, CC0). It covers `1ROAD_road` and every `1ROAD_pad` / `_apron` / `_mouthfill`; it replaces pbr's borrowed
  `asphalt_cracked` pair (LA Canyons, personal use).
- `texture_overrides["1KERB_SIDEWALK"]` -> `assets/textures/concrete_plain_{diffuse,normal}.jpg` (seed 85, CC0, made for
  1KERB_SIDEWALK). It covers the street curb and sidewalk (CURB -> `1KERB_sidewalk`) and every `1KERB_sidewalk_*`; it
  replaces pbr's `building_*` (Hamburg board-formed wall concrete, mined). The race kerbs keep their worn atlas (tested).
- `ship.json` `sync_in.assets` + the four files: engine-july lacks them, so `pbr.load_overrides` falls back to the project's
  copy, as with the house textures (ledger 0065).
- **Lake Murray has no `road_wear` key, so no `detail_highpass_m`.** The pair is the road's own diffuse and normal, on the
  prep's 4 m planar grid (`UV_TILE = 4.0`), which is the pair's own tile.
- **The calibration.** Mean colour, Pillow-decoded:
  - `asphalt_cracked_diffuse.jpg` 0.3806 / 0.3871 / 0.3962 against `asphalt_dense_diffuse.jpg` 0.3816 / 0.3875 / 0.3978 (grey
    0.3880 -> 0.3889, +0.2 %);
  - `building_diffuse.jpg` 0.5286 / 0.5156 / 0.4891 against `concrete_plain_diffuse.jpg` 0.5279 / 0.5159 / 0.4886 (grey
    0.5111 -> 0.5108).
  So the road's and the sidewalks' tone holds. When road wear comes, its m0 is computed off asphalt_dense, as Milford's
  0.85537 was (0095).
- md5: asphalt_dense diffuse 339c4244d8b07494be81df14eb963c8c (2,346,705 B), normal 7a71dfcefbbce0267cb0d17f0c931fb0
  (3,198,685 B); concrete_plain diffuse d77c7ca9c8faa202951821133628a4e4 (262,056 B), normal
  2692b4231be5d2c24c6b4f0f3705bb84 (370,970 B).
- `assets/licenses.json` already lists all four (from 0095's merge); nothing is needed there.
- **Concrete still borrowed on Lake Murray:** `BRIDGESTRUCT_1` / `_2` (the bridge bodies) still bind `building_*` (seen in
  the Mac's prepped blend). They are not road or sidewalk; binding them is the next step of "on every track".

## 7. Version

`track.config.json` `version` 0.20.2 -> **0.20.3**. Nothing installed. `fleet/ac-installed.json` needs a 0.20.3 row only
if Kevin installs it.

## Mac prep attempt (the seeded workshop, after the author phase above)

- **The engine:** a scratch folder holding `engine-july-snapshot/scripts` and `/vendor`, plus airoso's `assets/textures`
  (the "snapshot plus assets/textures" engine ship_track.sh's header names). **Blender 5.1.2**, not the pinned 4.2.
- **The prep, `build_kn5_loop.py`:** exit 0 in about 3 minutes; `blender/san_diego_lake_murray.blend` is 244,129,952 B.
  - 3 bridge spans declared; 1GRASS 817,802 vertices -> 16 tiles (0.20.2's trees stand on 1GRASS_0..15, the same count);
    GRASS_FAR 4 tiles; 1KERB_sidewalk 2 tiles; 6,239 buildings seated; multi-layout, 5 layouts.
  - Bound in the prepped blend:
    - `1ROAD_road` and `1ROAD_pad_J2`: asphalt_dense diffuse + normal, packed;
    - `1KERB_sidewalk_0` and `_padJ3`: concrete_plain, packed;
    - `1KERB_race_770_out`: kerb_race_worn;
    - `LIGHTS_0` **and `LIGHTS_back`**: solid_lens_warm.png;
    - `BRIDGESTRUCT_1`: still building_*.
- **The split, `tools/split_exports_blend.py`** (on the prepped blend; the prep's thin / rock / red-repair sub-steps were
  not run here): exit 0.
  - main 121 meshes / 1,469,437 positions; race 21 / 94,092; race_north 20 / 63,322; closures 11 meshes each; street 4
    meshes; 5 spawn scenes.
  - `LIGHTS_back` and its material ride in `loop_main.blend`, so they go to the road kn5.
- **Not run on the Mac:** the export (Blender 4.2 and the installed AC add-on; installing it here is not allowed), and
  everything after it. Runbook 0099-1 is the PC's full run.

## Notes for the PC (round 2: College Ave realism+, the J1 tilt, Phase 3, road wear at 10 cm)

These are findings, not a plan. The PC session owns the plan.

**J1 (College / Navajo / Waring).** Kevin: "Tilt it now". Ledger 0054's numbers: the real crossroads falls about 2 m
toward Waring. Level, Waring's first 40 m ride 1.3-1.4 m over the ground at 8.8 %. 0054 recommended taking the tilt with
0055's College work as one change: it moves a corner every layout drives (the Speedway takes J1 as a slow right turn,
R 8.3 m).

**College Ave realism+** (0055, Drive 2). Kevin: "can you split them up and do something fun? i would prefer realism+".
His warning: "claude has a hard time splitting up lanes and keeping a coherent system in place".
- The real road (0055's measurements): split level from v1216 to v1414. Northbound rides a bench +2.4 m (v1216),
  +5.5-5.9 m (v1243-1290), +5.0-5.3 m (to v1342), +1.6-1.9 m (v1396-1414) over southbound.
- The real median's middle sits at -6.8 -> -7.8 -> -6.3 -> -5.2 m (v1250-1400; + = west) of the raw line. The hill east
  of northbound is a real cut, about 0.55-0.6 V:H, its toe at L -22 to -29.
- What the config still declares: `race.chicanes` `college_split` (walls v1253-1379, lanes 10.65 / 9.625 m, hold 160.2 m),
  `route.median_registration`, and `terrain.ground_release.zones` `college_split_cut`.
- 0055's seven-step bounded proof is the acceptance path.

**Phase 3** (`EXPANSION-PHASE3-PLAN.md`, revision 2, 2026-10-14; Kevin: "Phase 3 is part of finished").
- The road: Waring J2 -> J6 0.67 km, Zion J6 -> J7 1.57 km, Mission Gorge J7 -> J3 2.36 km. That is 4.60 km of new road
  on a 5.71 km loop; 30 public stubs, 5 junction arms and 45 curb cuts.
- **Its data needs downloads (Kevin's yes first):**
  - `osm.expansion.json` is dated 2026-10-14, past the 7-day guard;
  - about 177.4k 3DEP samples in about 395 requests, plus about 23 for the grid;
  - a buildings refetch over the grown box.
- With both heads lit, Phase 3's ~80 lamps [the plan's estimate] add ~160 CSP lights (646 -> ~806).

**Road wear at 10 cm** (0084; Kevin: "Full road wear at 10 cm").
- 0084's estimate: 8192² at 10 cm over ≈500,800 m² of road, 89 MB (BC7 with mips).
- A street needs a per-lane line source ("lanes", owed in 0084: one line per lane centre from the paint rule, a divider
  every 3.65 m, both directions, the tyre profile on each lane's wheel paths).
- **The aerial on disk:** `source/naip_2022_lm_z18.jpg` is 12,032 × 10,496 px = 47 × 41 = 1,927 z18 tiles. Only 608 are
  filled: its georef says `missing_tiles` 1,319 (68.4 %), and it was drawn from one NAIP item,
  `ca_m_3211716_sw_11_060_20220425`. The missing tiles most likely lie in the other three quarter-quads of the scene list
  beside it (`naip_2022_scenes.json`: `_se_`, `_nw_`, `_ne_`, 2022-04-25) [inferred, not checked tile by tile].
- **The source:** USDA NAIP 2022, 0.6 m, public domain (0084: "all NAIP and public domain"). The item ids are Microsoft
  Planetary Computer NAIP ids, the service `tools/naip_crop.py` reads.
- **The size:** ≈ 69 MB at the mosaic's own JPEG rate (31,861,774 B / 608 filled tiles ≈ 52 KB a tile, × 1,319) [estimate].
  Phase 3 also needs the box grown west from -117.0808 (`naip_box.json`) to at least -117.101.
- Not downloaded. 0084 also measured, inside Lake Murray's road: shadow pixels 16.0 %, paint ghosts 8.6 %.

**Also open:** the sidewalk re-author (the 96 street drops 0.20.2 was forced past); the bridge bodies' concrete (§6).

## Runbook 0099-1 (PC): rehearse 0.20.3 from an EMPTY workshop. NO install.

The branch is `claude/lm-finish-20261122` (pushed by the Mac). Nothing in `content/tracks`, `lm_v4`, `lm_phase2/project` or
`lm_line` is touched. No `--force-install`.

0. **The checkout.** A fresh worktree of the branch head (AIROSO=<worktree>). Then:
   `git lfs pull --include tracks/san-diego-lake-murray/loop.blend`. Check its sha256 is
   3f13b887446e6fe921faeec0672201d9d8846e538347bc8248ff5b453999a082 (189,063,384 B). The chain refuses a pointer.
1. **The TreeFX models.** Copy the 16 `*.bin` from `D:/k10-scratch/lm_phase2/project/source/trees/` into
   `<worktree>/tracks/san-diego-lake-murray/source/trees/`. They are gitignored: never `git add` them. Note their names and
   md5s.
2. **The engine, run A.** A fresh copy of the engine-july that built 0.20.2: the 0090 proof's `D:/k10-scratch/eng_repro`,
   copied to `D:/k10-scratch/eng_0099`. Copy it; never edit the real engine-july.
3. **Run A.** `D:/k10-scratch/rehearse_0099_1` must not exist.
   ```
   SHIP_PROJ=D:/k10-scratch/rehearse_0099_1 AIROSO=<worktree> ENG=D:/k10-scratch/eng_0099 \
     bash tools/ship_track.sh san-diego-lake-murray --no-install --skip-blend 2>&1 | tee D:/k10-scratch/rehearse_0099_1.log
   ```
   Expected: the sync-in prints `seeds: 70 copied from airoso, 0 kept as the workshop had them (0 of those differ from
   airoso's)`. The run ends NOT INSTALLED on the street drive_test's 96 inherited drops, as 0.20.2's run did.
4. **Run B (optional, if time): is engine-july still needed?** The same command with `ENG` = a new empty folder holding a
   copy of `tracks/san-diego-lake-murray/engine-july-snapshot/scripts` and `.../vendor`, plus airoso's `assets/textures`;
   `SHIP_PROJ` = `D:/k10-scratch/rehearse_0099_1b`. Compare B against A with kn5_equiv on every kn5.
5. **Report**, for A (and B):
   - the seeds line; every step header and its exit; the GATES line; the run's minutes;
   - **kn5:** `tools/kn5_equiv.py`, each kn5 against the installed 0.20.2 (`content/tracks/san_diego_lake_murray_v4`).
     - Expected EQUIVALENT: race, race_north, the four closures, street.
     - The road kn5 should differ only by the new `LIGHTS_back` mesh (1,292 vertices, 323 faces) and by the 1ROAD* /
       1KERB_sidewalk* materials, which now embed asphalt_dense / concrete_plain (md5s in §6) in place of
       asphalt_cracked / building_*.
     - Name any other mesh that differs, and the kn5's bytes before and after.
   - **lights:** the `[LIGHT_N]` count in `build/san_diego_lake_murray/extension/ext_config.ini` (expect 646);
     `data/lights_ini_check.json` (expect ok, matched 646, n_lenses 646); `data/lights.heads.json` closest_lenses_m (expect
     8.073); `kn5_ground_check`'s lamp_heads and lamp_orphans per layout (expect about 646 and 0).
   - **surfaces.ini:** KERB `FF_EFFECT=1`, every other surface 0.
   - **trees.txt** against the installed one (md5 aa0cfae01fe9308913e7e637dae04bdd, the 2026-11-13 and 2026-11-19
     patches): the line count and how many lines differ. Also `data/treefx.report.json`'s total (0.20.2: 21,111) and its
     `median_measured` (expect measured 252).
   - **AI lines** byte-identical to the installed ones; the gate rows against the 0090 proof's `proof_lm.rows_vs_2f.txt`.
   - every `ui_track.json` version reads 0.20.3.
6. **Write it back.** Record the results as a section of this ledger, on a branch off `claude/lm-finish-20261122`, and push
   that branch. No merge, no install. An install is Kevin's word, after the stills and his look at the lights.

## Tests (Mac)

- New: `tests/tools/test_lake_murray_0099.py`, 16 tests (the seed spec, the round trip, the blend's sha256, every config
  file synced in, the seed block and the guard probed in bash, the twin model's symmetry, the back lenses on Lake Murray's
  record, ext_config's clustering and the both-heads check, the kerb rumble, the owned pairs, the version).
- The full suite on this branch: **1,726 passed, 0 failed** (9 min 2 s; main had 1,710 / 0). The run before the last fix
  had one failure, `test_p4_signs`, which pins the race steps as the author phase's last three; `lamp_heads` moved first.

## Shared files touched

`tools/ship_track.sh`, `tools/ship_track_spec.py` (sync_in.seed, opt-in); `tools/check_lights_ini.py` (both heads,
opt-in); `tools/author_lamp_heads_blend.py` (new, opt-in); `fleet/GATES-CHANGELOG.md`; tests:
`tests/tools/test_ship_track_chain.py` (the SD guard run takes a seedless copy of the spec; V4_EXTRAS gains the
lamp_heads header; the workshop is lm_line), `tests/tools/test_house_gate.py` (Lake Murray's assets: 10 house + 4 owned),
`tests/aerial/test_road_wear_highpass.py` (Lake Murray may bind the owned pair with no road_wear),
`tests/tools/test_lake_murray_0099.py` (new). No other track's config or ship.json changed. Lake Murray's own files:
track.config.json, ship.json, README.md, source/stills/ (the three stills and their two scripts and record).

## Needs Kevin

- **The kerb dirt:** the three stills (§4). Keep the four levels as they are, or darker / lighter?
- **Eucalyptus:** a height rule for gums off the lidar (the counts in §5), with which N, or a sample check first?
- **Jacaranda and flowering shrubs:** where the TreeFX models come from (§5).
- **The install of 0.20.3**, after runbook 0099-1 (both heads mean twice the CSP lights; frame cost [not measured]).
- **Downloads for round 2** (Notes for the PC): fresh OSM, 3DEP and buildings for Phase 3; NAIP 2022 se / nw / ne for the
  road wear (≈ 69 MB [estimate]).

## PC run A (2026-11-22, 3b03aead): Lake Murray 0.20.3 from an EMPTY workshop, as expected; not installed

Runbook 0099-1 step 0-3: worktree `D:/k10-worktrees/lm-finish` at 3b03aead; `loop.blend` sha256 3f13b887...a082
(189,063,384 B) after `git lfs pull`; the 16 TreeFX models copied from `lm_phase2/project/source/trees/` (gitignored, not
added): Agave a77e318f, Bush e150b090, Bush2 877abeb5, Bush3 e9299a59, Gum c00ef5dc, Oak3 24111ede, PalmV1 5545bb15,
PalmV2 a9eb1ee3, PalmV3 3c3ea2b3, PepperV1 109f17bc, Pine_Aleppo 7e058b11, Sage 37a69c1f, SycamoreV1 0986f1ea, SycamoreV2
7010d61f, SycamoreV3 0ad53d67, Yucca ef643461. ENG `D:/k10-scratch/eng_0099` = a copy of `eng_repro` (diff -rq clean).
`SHIP_PROJ=D:/k10-scratch/rehearse_0099_1`, `--no-install --skip-blend`, 21:44-22:19 (35 min). Run B not run.

- **Seeds:** `seeds: 70 copied from airoso, 0 kept as the workshop had them (0 of those differ from airoso's)`.
- **GATES:** `street drive_test exit 1, street audit exit 0, race drive_test exit 0, race audit exit 0, race no_route exit
  0, kn5_ground_check exit 0`; race layouts red: none; **NOT INSTALLED** on the street drive_test's 96 inherited drops
  (`off-road excursion drops>20cm : 96`), as 0.20.2's run.
- **kn5 against the installed 0.20.2** (`san_diego_lake_murray_v4`), kn5_equiv:
  - the four closures, race and race_north: EQUIVALENT (tangents only); the five spawn kn5s byte-identical;
  - the road kn5 107,371,829 -> 109,292,738 B: `1 mesh(es) not equivalent` = `LIGHTS_back` (new: 1,836 vertices / 646
    triangles in the kn5, i.e. 323 quads; `LIGHTS_back_mat` new). Every other mesh equivalent. A material-by-material read:
    only texture bindings change, on 1ROAD_road / pad_J2 / pad_J3 / pad_J4 / mouthfill_0 / mouthfill_1 / apron_AP1
    (asphalt_cracked -> asphalt_dense, diffuse + normal) and 1KERB_sidewalk_0 / _1 / apAP1 / padJ2 / padJ3 / padJ4
    (building_* -> concrete_plain). Textures out: asphalt_cracked_*; in: asphalt_dense_*, concrete_plain_*; building_* stays
    (BRIDGESTRUCT).
  - **the street kn5 differs too** (the runbook expected it equivalent): 3,867,123 -> 4,500,236 B, 0 meshes not
    equivalent; `1KERB_sidewalk_streetonly_median_mat` now binds concrete_plain (it is a 1KERB_SIDEWALK stage); textures in:
    concrete_plain_*. Textures only.
- **Lights:** ext_config.ini 646 `[LIGHT_N]` (0.20.2: 323); `lights_ini_check.json` ok, n_lamps 323, n_lights 646, matched
  646, n_lenses 646, both_heads true; `lights.heads.json` closest_lenses_m 8.073; kn5_ground_check `lamp integrity: 781
  heads, orphaned 0` on each of the 5 layouts (the proof read 393 heads).
- **surfaces.ini:** `[SURFACE_1] KEY=KERB` `FF_EFFECT=1`; ROAD, RUNOFF, GRASS, LAWN, WALL `FF_EFFECT=0`.
- **trees.txt:** 21,159 lines as the installed (aa0cfae0 -> df2c722f); 1,015 lines differ, every one a `Bush.bin` size off by
  0.001 (the third decimal; at most 4.2 % of a 0.024-sized bush); models, positions and angles identical, so Nov 13's bush
  fix and Nov 19's medians hold. `[treefx] 21111 written of 21111 planned`; `treefx.report.json` total 21,111,
  median_measured {measured 252, crown_measured 201, kept_rank_rule 850}.
- **AI lines:** all 10 (5 layouts x fast / pit) byte-identical to the installed.
- **ui_track.json:** 0.20.3 on all 5 layouts.
- **Gate rows against the 0090 proof (`proof_lm`):** 1,035 / 1,033; every difference is this round's: the seeds and
  `[heads]` lines, the workshop name in `[bands]`, split main 128 -> 129 meshes, the kn5 vertex offsets (+1,836 v / +646 tri
  for LIGHTS_back), `[street-kn5]` textures (+concrete_plain), `[lights-ini] 646 ... PASS` (was 323), and the author-time
  `[verify-race]` plan count 21,171 (the proof 21,111; the written count after TreeFX is 21,111 in both).

Not installed: the street drive_test still refuses (as 0.20.2), and the runbook keeps the install for Kevin after the
stills and his look at the lights.

## Round 1c (Mac, 2026-11-22): the street drops — 0.20.4

Kevin: "let's complete lake murray"; the sidewalk re-author is on his list (the board's n-lm-sidewalk: the 96 street drops
0.20.2 was forced past, Nov 4). Branch `claude/lm-sidewalk-20261122` from round 1's head 3b03aead, plus the PC's run A
record above (f19e106c, cherry-picked so this section follows it). Nothing installed. Every number below was measured on the
Mac on 2026-11-22 unless marked [invented].

### What an "edge drop" is (scripts/geometry/drive_test.py, unchanged)

The excursion sweep: at a station every ~150 m of the gate centreline (90 on Free Roam's 13.47 km), both sides, the
highest built surface is read every 0.5 m from the lane edge - 0.5 m out to the lane edge + 9 m. A fall of more than 0.12 m
between two samples (a tall curb, the most a car survives at speed) is a drop; it GATES when it lies within 4 m of the
last pavement / kerb sample, outside a flare, with no 1WALL between the pavement and it. The lap rule allows
int(lap_m / 1000) = 13 on Free Roam. Neither the 0.12 m, the 4 m band nor the 13 was touched.

### Where the 96 are, and what makes each one

Read on a Mac stand-in of the 0.20.3 build (below), whose `data/drive_test.street.json` equals the PC's run A / 0090
proof report key for key (96 gated, 107 far ledges, soft top 0, severe 0, kinks 2.67 / km). Every drop with its station,
offset, height and the surfaces it falls from and onto: `tracks/san-diego-lake-murray/source/walk_grade/street_drops_0_20_3.json`.

| Cause | Drops | Stations (s m) | Where | Fall per 0.5 m |
|---|---|---|---|---|
| The walk's back grade, both samples on it (1KERB_sidewalk -> 1KERB_sidewalk) | 66 | 41 stations: 2.3, 302.6 ... 12900.8 (both sides: 30 left, 36 right) | 2.4-3.0 m past the lane edge | 0.137-0.142 m |
| The walk's back grade onto the grass the prep pins under its lip (1KERB_sidewalk -> 1GRASS) | 28 | 21 stations: 150.0 ... 12751.0 (17 left, 11 right) | 2.5 m past the lane edge | 0.126-0.141 m |
| Ground: a 1 m slot between Alvarado and College's south approach, 3.9 m above it (released 3DEP earth at 3.2 m between Alvarado's bank and College's walk) | 1 | 2100.3, right, 13.0 m off the centre line | 6.5 m past the lane edge | 1.52 m |
| Ground: the feather of the prep's pin falling to a fill | 1 | 2402.7, left, 15.0 m | 6.5 m past | 0.20 m |

**The walk (94 of the 96).** The draft's curb + walk (scripts-v021 `geometry/ribbon.curb_sidewalk`, Lake Murray's
EDGE_DEFAULTS, no `route.edge`): from the lane edge (0.10 m over the centre line) a 0.08 m batter up 0.14 m, the walk flat for
1.8 m, then a back grade 1.2 m wide down to 0.10 m UNDER the centre line, so the strip's outer lip sits under the grass. It
falls 0.34 m over 1.2 m: 28.3 %, 0.142 m per 0.5 m sample. Measured on the committed `loop.blend`'s CURB: 17,272 such lips,
15,711 of them falling 0.34 m to the centimetre (98 % over a 1.20-1.21 m run). The prep (engine-july `build_kn5_loop`) then pins the ground within
3 m of a pavement vertex to the deck - 0.02 m and clamps it under the lowest drivable sheet, so beside the walk the ground
lies at about the lane edge and the grade runs down into it. The sweep reads two samples on the grade as 0.142 m, or one on
the grade and the next on the grass just over its lower half as 0.126-0.141 m. A real sidewalk's back meets the ground (the
yard, the parkway); the 0.34 m / 1.2 m grade is the draft's way of tucking its edge under the grass [invented in the draft].
It is not a kerb or a ditch Free Roam should keep.

**The two ground drops are not the walk.** They are reported here, not hidden, and stay in the count:
- s 2100.3 right: the loop passes back beside itself here (College's south approach, s 2410-2545, about 3.8 m above
  Alvarado, 13.5 m to the right). Alvarado's bank rises 3.5 m, then the ground drops 1.52 m into a 1 m slot of released 3DEP
  earth (zone `college_approach_foot`, about 3.2 m) before College's walk. The real earth between the two roads is the
  embankment [inferred]; the slot is the release zone's earth showing between two strips pinned to their roads. A ground fix for a later
  round (it is the release zone's, not the walk's).
- s 2402.7 left: 6 m past the lane edge the ground falls 0.20 m per 0.5 m (40 %): the prep's feather from the pinned verge
  toward the natural ground of a fill. The real ground falls faster there (3DEP 1 m samples: about 2.5 m under the road 5.5 m
  past the edge, 6.1 m under it 11 m past, on the local datum read off the centre line). A real fill slope; kept.

### The fix (opt-in `route.walk_back_grade`; Lake Murray only)

`tools/author_walk_grade_blend.py`, two halves:

1. **Author step `walk_grade`** (`steps.author`, second, after `lamp_heads` and before the race steps), on the workshop's
   `loop.blend`: every back-grade lip of the named walks is raised so that no edge from it up to the walk's back edge is
   steeper than `max_slope` 0.20 [invented: 0.10 m per 0.5 m sample, under the gate's 0.12 with 0.02 to spare]. Nothing else
   moves: the curb, the walk top, the strip's plan footprint, every other object. At 0.20 the grade falls 0.24 m over its
   1.2 m and the lip lies at the centre line's own height (0.10 m under the lane edge, 0.08 m under the ground the prep pins).
   Objects: the draft's CURB and the four walks with the same grade (`1KERB_sidewalk_padJ2` / `J3` / `J4`, `_apAP1`); the
   street-only median has no back grade. Held where the draft put it:
   - a lip in a ground-release zone (`data/ground_release.json`, the 3DEP earth the prep leaves unpinned): at most 0.03 m
     [invented] under that earth;
   - a lip of a face furniture stands on (any 1WALL* / GUARDRAIL vertex over it: a stub's K-rail laid back of walk to back of
     walk, a pad's barrier, a rail). The first Mac try raised those too and verify_stubs failed 16 stubs on S5 (a K-rail base
     0.154-0.254 m into the stub, limit 0.15); held, every stub and pad barrier reads as 0.20.3's;
   - a lip with pavement 1 m over or under it (none on Lake Murray); a lip the red repairs plan names (10: the prep deletes
     those faces by place).
   On the seeded `loop.blend`: CURB 17,272 lips, 15,351 raised (p50 0.10 m, max 0.195 m), 910 already at the grade, 1,571
   held by released ground, 513 under furniture, 10 by the red plan; pads J2 / J3 / J4 156 / 193 / 200 raised (12 under
   their barriers each); apron AP1 30 raised (the Mac build had 31: one lip rose under 0.1 mm before the float32
   tolerance). Fall p50 0.34 -> 0.24 m. A second run raises none. Writes `data/walk_grade.json`.
2. **Prep sub-step `--seat`** (in `prep_prep`, after the red repairs), on the prepped scene: the ground is only final there.
   Where the prep's feather falls away 3 m out (a fill), the ground it leaves under a raised lip can lie below it and the
   walk's outer edge would stand in the air: the author step alone left 645 lips more than 0.05 m over the ground against
   0.20.3's 497. The seat lowers every 1KERB_sidewalk* lip standing over 0.03 m under the 1GRASS ground beneath it onto that
   height, never past the draft's own grade (0.34 over 1.2), never up. Mac: 3,280 lips lowered (p50 0.01-0.03 m, max
   0.24 m), 294 of them to the draft's grade; lips more than 0.05 m over the ground 343 (0.20.3: 497), more than 0.03 m 413 (624). Writes
   `data/walk_grade.seat.json`.

Both: absent key = no header, nothing runs, no blend saved, a stale report removed (every other track). Self-checked (exit
1, blend not saved): only lips move; the author half only up and never steeper than max_slope where it raised one; the seat
only down and never past the draft's grade. Idempotent (a second run finds the same lips at the grade and moves nothing).

### Proof on the Mac (Blender 5.1.2, not 4.2)

The Mac cannot export a kn5 (Blender 4.2 and the installed AC add-on). So the stand-in: round 1's seeded workshop (the
author phase already run), the prep under engine-july-snapshot + `assets/textures`, then the prep's sub-steps as the chain
runs them (thin, the I-8 no-op, rock faces, red repairs, and here the seat), the split, and the gate OBJs written straight
from the split blends' meshes in the engine frame (`source/walk_grade/blend_to_gate_obj.py`: scene (E, N, up) -> engine (E,
up, N), the frame red_repairs_blend uses) in the kn5 sets each layout loads. The gates then ran from airoso exactly as the
chain runs them.
- **The stand-in reproduces the PC.** On 0.20.3 as seeded: the street report equals the PC's key for key; rock 9,805 faces /
  11,935.7 m2 in 8 meshes and verify_pads seams 1.2 / 0.7 / 2.4 mm as ledger 0054's rehearsals, rib_check 69 jogs (v0.19.0's
  69), verify_mouths 32 and verify_stubs 26 + 29 PASS.
- **The street drive_test: 96 -> 8 gated drops, PASS (limit 13), no force.** Every drop after:
  `source/walk_grade/street_drops_0_20_4_mac.json`.

  | After | Drops | Stations |
  |---|---|---|
  | The walk at the draft's grade over the released 3DEP earth of `alvarado_creek_bank` (the real ground behind the walk lies low) | 3 | 1650.2 L, 1800.4 L, 1950.6 L (0.142 m) |
  | The walk lowered by the seat onto a fill | 3 | 602.0 R (0.127), 2402.7 R (0.142, the draft's grade), 5550.8 L (0.120) |
  | Ground (above, unchanged) | 2 | 2100.3 R (1.52 m), 2402.7 L (0.20 m) |

- **Every other row as 0.20.3's.**

  | Gate (Mac stand-in) | 0.20.3 | 0.20.4 |
  |---|---|---|
  | street drive_test: soft top / severe / kinks per km / daylight / obstructed / floating | 0 / 0 / 2.67 / 0 / 0 / 0 | the same |
  | street drive_test: excursion drops (gated) / far ledges (reported) | 96 / 107 FAIL | 8 / 53 PASS |
  | drive_test --line expansion fwd / rev (line gate) | PASS 40 drops / PASS 38 | PASS 13 / PASS 18 |
  | audit street (K / I / F / B ...) | CLEAN | CLEAN (F_skirt_off_terrain 1,563 -> 1,564, reported) |
  | race_cw / race_acw / north_cw / north_acw drive_test | PASS, 0 drops (far ledges 203 / 231 / 124 / 119) | PASS, 0 (61 / 100 / 34 / 37) |
  | the four race audits / no_route | CLEAN / PASS (leak 0, 0/439 probes) | the same |
  | verify_mouths / verify_stubs / verify_pads | 32 PASS / 26 + 29 PASS / J2-J4 PASS, barriers 1.077-1.086 m | the same, barriers the same |
  | rib_check / house_seat / fold fans | 69 jogs PASS / PASS / PASS 3 x 5 | the same |

- **What else moved in the scene** (mesh by mesh, the two gate OBJs): the walks' lips; the ground tiles (the prep's
  anti-poke holds the grass under the raised grade less deeply, so the thinning keeps 540,852 of 983,289 vertices against
  541,825 of 983,287); 1GRASS_ROCK 9,805 -> 9,807 faces; 9 building meshes by 0.2-5.9 mm (the prep's re-seat rides the ground's
  delta). The road, the markings, the lamps and their lenses, the walls, the race furniture: no vertex moved.
- **Not run on the Mac:** the kn5 export and everything that reads a kn5 (kn5_ground_check, house_gate, textures, the
  track folder, ext_config / check_lights_ini, TreeFX, the AI), Blender 4.2. Runbook 0099-2 is the PC's.

### Version

`track.config.json` `version` 0.20.3 -> **0.20.4**. Nothing installed; `fleet/ac-installed.json` unchanged.

## Runbook 0099-2 (PC): rehearse 0.20.4 from an EMPTY workshop. NO install.

The branch is `claude/lm-sidewalk-20261122` (pushed by the Mac). Nothing in `content/tracks`, `lm_v4`, `lm_phase2/project`,
`lm_line` or run A's `rehearse_0099_1` is touched. No `--force-install`.

0. **The checkout.** A fresh worktree of the branch head (AIROSO=<worktree>), `git lfs pull --include
   tracks/san-diego-lake-murray/loop.blend`; sha256 3f13b887446e6fe921faeec0672201d9d8846e538347bc8248ff5b453999a082
   (189,063,384 B, unchanged: the fix runs on the workshop's copy).
1. **The TreeFX models**, as run A: the 16 `*.bin` from `D:/k10-scratch/lm_phase2/project/source/trees/` into
   `<worktree>/tracks/san-diego-lake-murray/source/trees/` (gitignored; never `git add`). Their md5s as run A's.
2. **The engine:** a fresh copy of `D:/k10-scratch/eng_repro` at `D:/k10-scratch/eng_0099_2` (diff -rq clean against it).
3. **The run.** `D:/k10-scratch/rehearse_0099_2` must not exist.
   ```
   SHIP_PROJ=D:/k10-scratch/rehearse_0099_2 AIROSO=<worktree> ENG=D:/k10-scratch/eng_0099_2 \
     bash tools/ship_track.sh san-diego-lake-murray --no-install --skip-blend 2>&1 | tee D:/k10-scratch/rehearse_0099_2.log
   ```
   Expected:
   - seeds: `seeds: 70 copied from airoso, 0 kept as the workshop had them (0 of those differ from airoso's)`;
   - the new author header `author: the street walk's back grade no steeper than route.walk_back_grade ...` and
     `[walk-grade] CURB: 17272 lips, 15351 raised ... held 1571 by the released ground + 513 under furniture + 0 by pavement
     + 10 by the red plan` (pads 156 / 193 / 200 raised, AP1 30; the Mac's numbers, Blender 5.1.2);
   - the new prep header `ship: the walk's raised lips seated on the prepped ground ...`, after `red repairs`, about 3,280
     lips lowered (the Mac's; the PC's prep may differ by a few);
   - **the street drive_test PASS: `off-road excursion drops>20cm : 8`** (limit 13; the Mac's eight at the stations above);
   - `GATES: street drive_test exit 0, street audit exit 0, race drive_test exit 0, race audit exit 0, race no_route exit 0,
     kn5_ground_check exit 0`; race layouts red: none; then the scratch-copy line (`never installed`), no force anywhere.
4. **Report**, against run A (3b03aead, `rehearse_0099_1`):
   - every step header and exit, the GATES line, the minutes;
   - `data/drive_test.street.json`: the drops (8 expected) and every other key against run A's (expected equal but
     `excursion_drops`, `excursion_far_ledges`, `fail`); `drive_test --line expansion` fwd / rev (Mac: 13 / 18, line gate
     PASS); the race and north drive_tests (0 drops; far ledges fewer);
   - `data/walk_grade.json` and `data/walk_grade.seat.json` (counts as above);
   - **kn5:** `tools/kn5_equiv.py` against run A's kn5s. Expected: race, race_north, the four closures, the street-only kn5 and
     the five spawns EQUIVALENT; the road kn5 not equivalent only in 1KERB_sidewalk_* (the lips), the 1GRASS_* tiles and
     1GRASS_ROCK_* (the ground the prep left under the raised grades), and a few BUILDING_* by millimetres (the re-seat);
     LIGHTPOST_*, LIGHTS_0 / LIGHTS_back, 1ROAD_*, MARKINGS, YLINE, every 1WALL equivalent. Name any other mesh;
   - kn5_ground_check per layout (the lamp, sign and ground-sheet readings as run A's); check_lights_ini 646 / 646;
     house_seat and house_gate PASS;
   - `trees.txt` against run A's: the count (21,111 written) and how many lines differ (some plant heights near the walks may
     move with the ground [not measured on the Mac]);
   - AI lines byte-identical to run A's; every `ui_track.json` reads 0.20.4.
5. **Write it back** as a section of this ledger on a branch off `claude/lm-sidewalk-20261122`, and push that branch. No
   merge, no install: an install is Kevin's word (0.20.3's stills and lights questions stand).

## Tests (Mac, round 1c)

- New: `tests/tools/test_lake_murray_0099_walk_grade.py`, 16 tests: lips found as exactly the strip's outer row on strips the
  draft's own sweep builds (straight, a 40 m arc, a 12 % grade, rows 1.2 m apart up 15 %); the draft's grade read as 0.126-
  0.142 m drops by drive_test's own TriField and the re-authored one read as none; only lips move, only up, to the slope; the
  lip at the centre line; a second run moves nothing; the pavement, released-ground, furniture and red-plan holds; the seat
  (onto the ground, never past the draft's grade, a second seat moves nothing); the release zones are the file's; the opt-in
  is Lake Murray's alone; the chain wiring (author step second, the seat after the red repairs, sync_out); not opted in = no
  blend opened, a stale report removed; drive_test's 0.12 m line and lap rule untouched.
- Changed: `tests/tools/test_lake_murray_0099.py` (the version is 0.20.4), `tests/tools/test_ship_track_chain.py` (V4_EXTRAS
  gains the two new headers).
- The full suite on this branch: **1,742 passed, 0 failed** (8 min 24 s; round 1 had 1,726).

## Shared files touched (round 1c)

`tools/author_walk_grade_blend.py` (new, opt-in); `tools/ship_track.sh` (the author step and the prep sub-step, both
opt-in); tests: `tests/tools/test_lake_murray_0099_walk_grade.py` (new), `tests/tools/test_ship_track_chain.py`,
`tests/tools/test_lake_murray_0099.py`. No gate, threshold or other track's config or ship.json changed (so no
GATES-CHANGELOG entry). Lake Murray's own: track.config.json (`route.walk_back_grade`, version), ship.json (`walk_grade`,
sync_out + the two reports), README.md, source/walk_grade/ (the two drop lists and the stand-in OBJ writer).

## Needs Kevin (round 1c)

- **The install of 0.20.4**, after runbook 0099-2 (it replaces 0.20.3's ask: the same build plus the walk; no force needed
  if the PC reads the street drive_test as the Mac did).
- **The slot at s 2100** between Alvarado and College's south approach (1.52 m, the release zone's earth): a ground fix in a
  later round, or keep it as the counted drop it is now.

## PC rehearsal 0099-2 and install (2026-11-23, c8debb5f): Lake Murray 0.20.4 INSTALLED, no force

- **Rehearsal** (`D:/k10-scratch/rehearse_0099_2`, worktree `D:/k10-worktrees/lm-sidewalk`, ENG `eng_0099_2` = a copy of
  `eng_repro`, loop.blend 3f13b887, the 16 TreeFX models as run A, 00:36-01:13): seeds 70 copied. `[walk-grade] CURB: 17272
  lips, 15351 raised (rise p50 0.1 max 0.195 m), 910 already at grade, held 1571 + 513 + 0 + 10`; padJ2 / J3 / J4 156 / 193 /
  200, AP1 30: the Mac's numbers. `--seat`: 3,284 lips lowered. **Street drive_test: 8 drops** (far ledges 107 -> 53), fail
  False; its JSON differs from run A only in excursion_drops / excursion_far_ledges / fail / worst_*. Line gate fwd 13, rev
  18, both PASS; race and north drive_tests 0 drops. GATES all exit 0, race red none, **no force**.
- **kn5 against run A:** race, race_north, the four closures and the street-only kn5 EQUIVALENT; the five spawns
  byte-identical. The road kn5 109,292,738 -> 109,240,992 B: 37 meshes not equivalent: 1GRASS_* x16, 1GRASS_ROCK_6 / 13 / 14,
  1KERB_sidewalk_0 / _1 / padJ2 / padJ3 / padJ4 / apAP1, BUILDING_STUCCO_0-7 and BUILDING_TILTUP_0 (re-seated, dy +0.001 ..
  +0.006 m), and **SIGNPOST_0 / SIGNPLATE_0 / SIGNARROW_0**, not in the runbook's list: matched by position, the signs at 15
  places re-seat by -0.023 .. +0.007 m in height (the walks under them rose), nothing more. LIGHTPOST_*, LIGHTS_0 / _back,
  1ROAD_*, MARKINGS, YLINE and every 1WALL equivalent; materials: 0 differences.
- **As run A:** 646 lights (lights_ini ok, 646 / 646, both heads); `lamp integrity: 781 heads, orphaned 0` on all five
  layouts; house_seat 6,239 judged, 0 with no ground; house_gate PASS; trees.txt byte-identical (df2c722f, 21,111 written);
  AI lines identical; ui_track 0.20.4 on all five.
- **Install** (Kevin's standing word: "I always want newer builds"; his Nov 22 "When they're done, install them"; no
  `--force-install`): the chain's own new EMPTY workshop `D:/k10-scratch/lm_line`, 01:16-01:51, SHIP OK; 0.20.2 parked in
  `D:/k10-track-archive/2026-11-23_015157/`. The same as the rehearsal: 1048 / 1048 gate rows (workshop names only), every kn5
  EQUIVALENT (tangents only), AI the same; AC's 14 TreeFX models md5 = 0.20.2's. All five layouts read 0.20.4.
- The sync-back adds the north layouts' gate records and walk_grade*.json and drops 14 stale diagnostic plots (race_plots
  nose_*, signs_plots sign_*). fleet/ac-installed.json: san_diego_lake_murray_v4 0.20.4 (sha c8debb5f). Menu pictures: to
  come after the Sand Creek build (one Blender at a time). Not driven.

## The Mac's merge of 0.20.4's records (2026-11-23)

The full suite on the records head (4dcb76cf, origin/main b8d39f78 merged in) failed three of this ledger's own tests, all
from what the install synced back or what main brought, none from the build:
- **The round trip** (`test_the_round_trip_is_closed_...`): the install synced back 23 files airoso never held before: the
  north laps' records (lap, barrier bands, dummies, closures, drive tests, ground checks, no_route plans, race verify),
  `data/lights.heads.json`, `data/walk_grade.json` and `data/walk_grade.seat.json`. By the seed rule (every sync_out file
  airoso holds that sync_in does not bring) they are seeds now: `sync_in.seed` 70 -> 93. The steps rewrite every one.
- **The blend pin** (`test_the_committed_blend_is_...`): the committed `loop.blend` is now the one 0.20.4's install
  synced back, 189,120,404 B, sha256 495a2198067c3562... (0.20.2's was 189,063,384 B, 3f13b887...). The next empty
  workshop seeds it. Every author step on it is idempotent (above: walk_grade and the seat move nothing on a second run;
  the lamp heads pair each lens with its lamp), so a seed of an authored blend builds the same.
- **The owned concrete** (`test_the_road_and_the_sidewalks_bind_the_owned_pairs`): Milford binds `concrete_plain` since
  0.1.14 (ledger 0100). The test now allows the owned pairs on the four tracks Kevin is finishing (his "On every track
  now", scoped to those four on 2026-11-22) and refuses them everywhere else.
- The 14 older diagnostic plots the sync-back dropped (`race_plots/*/nose_1258|1374.png`, `signs_plots/sign_M*.png`,
  drawn before 0.20.2) are restored unchanged (4dcb76cf): nothing is deleted.

## Round 3, item 1 (the PC, 2026-11-23): Mission Gorge's median wears terracotta pavers. 0.20.6, green on scratch, not rehearsed

Round 3 as the Mac set it on 2026-11-23, after 0.20.5 installed (no force) and merged as main 366a5a4c: branch
`claude/lm-finish-r3-20261123` from that commit, version **0.20.6**. Its order: **1** terracotta on Mission Gorge's raised
median; **1b** that island's band over piece C s 990-1210 (a real intersection, below); **2** MD12, only on measured rows;
**3** road wear; **4** Jackson north's paint over rows 496-579; **5** the J1 tilt; then Phase 3. This section is item 1.
The side branch merged for it: `claude/lm-terracotta-tex-20261123` (4e4cab53, the CC0 paver and its measured tone).

**What 0.20.5 ships there.** Grass. All 14 islands' tops went into `1LAWN_median` (ledger 0055, the medians). The plan
(`data/expansion.north.json`) declares Mission Gorge's two built islands, MD11 and MD13, as `terracotta`.

**What the photo shows** (`source/expansion/mg_median/`, its README holds every number): on NAIP 2022, MD13's kept pixels
read terracotta (R - G +13 to +27) in every 50 m bin over s 260-1010 and s 1210-2245, and no bin is planted end to end
(highest canopy share 0.27). MD11's declared band reads near-grey: it is built terracotta as the plan declares, and its
tone is **[inferred from MD13]**, not measured. So both islands are paved over their whole built length: no grass
stretch, no concrete stretch. The plants keep their measured places.

*Corrected in item 2 (2026-11-23):* this paragraph first said MD11 reads grey because it is narrower than the photo's
colour resolution. That holds only for s 45-105. Over s 105-167.5 the declared band was not on the real strip, which
runs up to 3.8 m to its left, so the band's pixels were asphalt. Item 2 moves MD11 onto its measured line.

### What was built

1. **The surface is the name.** `scripts/ac/track_folder.py` writes only ROAD / KERB / RUNOFF / GRASS / LAWN (+ WALL).
   The hard row is KERB, the one every `1KERB_sidewalk` already has (friction 0.92, valid track, `kerb.wav`, and
   FF_EFFECT 1 on Lake Murray). The paved tops' object is `1KERB_PAVER_median`: no physical value is invented.
   **To know:** a car that drives onto the terracotta hears the kerb and feels its rumble in the wheel, exactly as on a
   sidewalk today. Accepted by the Mac as written.
2. **The material row.** `scripts/ac/pbr.py` binds a mesh by the first matching prefix, so `1KERB_...` would have worn the
   red racing kerb. One new row, `1KERB_PAVER`, stands above `1KERB` (stock skin: the untinted CC0 pair). It went into
   the engine of record the way the earlier rows did: the same file in airoso and in
   `engine-july-snapshot/scripts/ac/pbr.py`, refreshed by `tools/snapshot_engine_july.py` from a scratch engine copy that
   matched the snapshot file for file before the change. `MANIFEST.md5` and `PENDING-MIRROR.md5` carry the new md5
   (e414f407...; the live engine-july still holds 56c3307f...). The same refresh dropped two rows from `REFERENCED.md5`,
   `guardrail_diffuse.png` and `guardrail_normal.png`: the table's later `GUARDRAIL` row names `wbeam_rail_diffuse.png`
   since the bespoke-assets work (82f653c4), so no row reads those two any more. That staleness was there before this change; the tool's own
   `--check` already called it drift.
   **No other mesh name is bound differently:** `tests/tools/test_terracotta_median_0099.py` resolves every mesh name the
   repo writes (the table's keys, and each `1...` name in the tools, the engine scripts, every track's config, ship.json
   and assembler: 514 names) against the overrides of all 31 tracks, with and without the row, and they are identical; no
   other track's config or ship.json names the row.
3. **The tone and the scale.** `textures/make_terracotta_median.py` (PIL only) writes
   `textures/terracotta_median_diffuse.jpg` / `_normal.jpg`, bound by `texture_overrides["1KERB_PAVER"]` and carried into
   the workshop by `ship.json sync_in.optional`. It does two things. Each channel of the diffuse is multiplied by one
   gain (0.888 / 1.028 / 1.067, the method of `tools/make_owned_surfaces.py _match_mean`), so the file's mean is the
   mean the photo shows on MD13: target 147.9 / 127.8 / 115.6, the file measures **147.85 / 127.86 / 115.52**. And the
   image holds 2 x 2 repeats of the paver, because the prep lays every 1KERB mesh on its 4.0 m top-down grid and its
   list of meshes left alone is in the prep, which is not touched: one repeat is **2.0 m** on the ground, 5 % over the
   asset's own "ca. 1.9 m". To the eye the toned paver is a muted, greyer salmon, not brick red: that is what the 2022
   photo shows, and it is Kevin's to judge on a drive.
4. **The step.** `tools/author_median_tops_blend.py` reads `route.median_tops.paver` (`object`, and `islands` by line and
   first / last row, exactly as `data/median_bands.json` builds them) and gives those islands' tops their own object. It
   converges: a top still in TERRAIN is moved out; a top already in one object but declared for the other is moved
   across (the committed blend is 0.20.5's, whose 14 tops are all in `1LAWN_median`); a scene already right is not
   saved. New refusals, all fatal and nothing saved: a paved object not named `1KERB_PAVER...`; a listed island that is
   not built row for row, or has no top in the scene; a top that moves and is no longer a deck (the same 0.185 +- 0.06 m
   over the road); deck strips still in TERRAIN beside the tops' objects. No number of the step changed.
5. **Who else reads the top.** `tools/make_treefx.py` adds the paved object to the materials TreeFX seats a plant on.
   GrassFX takes only 1GRASS / 1LAWN meshes, so no blade grows on the pavers, with no change. The measure
   `source/college_r2/median_tops_check.py` counts paved rows apart from grass rows.

### Measured on a scratch workshop, through the chain's own commands

`source/college_r2/scratch/run_full.ps1` then `run_gates.ps1` on a workshop seeded as the chain seeds one, Blender 4.2 at
below-normal priority while the PC rehearsed Milford. `run_gates.ps1` now gates `north_cw` too (the north lap runs along
Mission Gorge with this median as its closed side). 0.20.5's column is its rehearsal 2 (c6352faf), unless marked.

| | 0.20.5 | item 1 on scratch |
|---|---|---|
| the median step | 14 tops in `1LAWN_median`, 4,282 vertices / 4,254 faces | 2 tops moved across: 12 islands in `1LAWN_median` (2,842 / 2,818), 2 in `1KERB_PAVER_median` (1,440 / 1,436); 2,123 rows checked, 0 without a top |
| the prep's conform | 79,062 edges split, 203,540 pinned, 53,792 feathered | the same three numbers |
| the thinning | 1,021,079 -> 540,064 vertices | 1,021,079 -> **540,045** (19 fewer, below) |
| the walk's seat | 3,202 lips | 3,202 |
| kn5_ground_check, street / race_cw / north_cw | 0 double-sheet cells; max +0.313; 43 of 10,900 over 0.05 m | the same on all three |
| street drive_test | PASS, 10 drops, 44 far | PASS, 10 drops, 44 far, severe 0 |
| street audit | CLEAN; F 0 of 97,526 curb verts | CLEAN; F 0 of 101,834 (+4,308: the paved top's 1,436 faces x 3); K 0, I 0 |
| race_cw drive_test | PASS, severe 7, 0 drops, 142 far | the same |
| race_cw audit / no_route | CLEAN, F 0 of 105,330 / PASS, leak 0, 138.2 k m2 | CLEAN, F 0 of 109,638, K 0, W 0 / PASS, leak 0, 138.2 k m2 |
| north_cw drive_test | PASS, severe 5, fold severe 12, 0 drops, 34 far | the same |
| north_cw audit / no_route | CLEAN, F 0 of 103,756 / PASS | CLEAN, F 0 of 108,064, K 0, W 0 / PASS, leak 0, 0 of 325 probes, 88.4 k m2 |
| the built medians (`median_tops_check.py` on the gate OBJ) | 2,123 rows grass, 0 asphalt | 1,419 grass + **704 paved** (MD11 25, MD13 679), 0 asphalt |

- **Nothing that stands on the two islands moved.** The prep seats props on 1GRASS / 1ROAD / 1KERB, and a paved top is
  1KERB where a grass top was 1LAWN, so anything standing there could have risen 0.185 m. Measured
  (`mg_median/props_on_islands.py`, the two road kn5s over the islands' bands + 0.6 m): the only mesh in the bands that is
  not ground, road, kerb or paint is `1WALL_guard`, 2,356 plan positions, every one at the same height. No lamp and no
  sign stands on them.
- **The 19 ground vertices.** The thinning reads its distances to the pavement's own vertices (1ROAD / 1KERB), and the
  paved top's 1,440 are pavement now. The ground differs in three tiles only (1GRASS_6, _7, _13: 104 positions only
  before, 85 only after), every one within 18.1 m of the paved island. The thinning's own self-check passed, and the
  ground check reads the same.
- **Not run on scratch:** race_acw and north_acw, the whole of verify_kn5, the AI lines, TreeFX, the track folder. The
  plant seat is held by a unit test; the rehearsal's `ext_config.ini` should list `1KERB_PAVER_median_mat` in
  SURFACE_MATERIALS.

### For the rehearsal

- The engine copy must carry the snapshot's `scripts/ac/pbr.py` (md5 e414f407..., CRLF read as LF): the row is not in
  `eng_repro` or the live engine-july. The textures need nothing: `sync_in.optional` brings the toned pair and the
  override resolves against the project.
- On the first build from the committed blend the median step prints `"from_one_top_object_to_the_other": 2` and saves;
  a second run prints "every top already lies in its own object" and saves nothing.
- Against 0.20.5 the road kn5 should differ in: `1LAWN_median` (smaller), the new `1KERB_PAVER_median` with its material
  and two textures, and 1GRASS_6 / _7 / _13 (the 19 vertices). Everything else equivalent.

### Known, and left for item 1b

The grey stretch of MD13 (s 1010-1210 reads R - G +3.5 to +10.7) is not grey paving. The photo shows a real crossing
there, Mission Gorge Rd with Margerum Avenue and Mission Vista Drive: no median for about 33 m (s 1087-1120), and a strip
about 2 m wide beside the turn pockets either side, where the plan's band is 4.6-5.3 m. The plan's width is linear
between eye readings 250 m apart and knows none of it, so the built island runs unbroken across the crossing. Both side
streets are already built as stubs there (ledger 0054 phase 5: `mission_vista_drive_5977531_L`,
`margerum_avenue_135149732_R`), so nothing but the median is wrong. Item 1 paves the island as built; item 1b re-reads its
band from the photo and re-declares the north lap's noses. Whether the crossing is signalised is **[inferred]** from its
crosswalks.

*Corrected before any push:* my first report to the Mac said the network had nothing at the crossing and owed two stubs.
I had read only the plan's junction arms (S1-S6), not `data/stubs.plan.json`. The north lap's no_route output on the
scratch run named the stub walls along Mission Gorge, and the plan file holds both.

### Tests

`tests/tools/test_terracotta_median_0099.py` (11 tests): the row and its order; no other mesh name bound differently on
any track; Lake Murray's override; the islands listed and what the step refuses; the lines the step leans on in the
prep's snapshot; the KERB row; GrassFX; the plant seat; the toned pair (tone within 0.5 of the target, 2 x 2 repeats);
the version. `test_median_tops_0055.py` and `test_lake_murray_0099.py` follow (the spec's new key, version 0.20.6). On the
PC: 1,681 pass; 11 fail and 10 files do not load, all this machine's own (no numpy, the live engine-july's exporter), none
in a file this item touches.

### Shared files touched

`scripts/ac/pbr.py` and its snapshot copy with `MANIFEST.md5` / `PENDING-MIRROR.md5` / `REFERENCED.md5`;
`tools/author_median_tops_blend.py`; `tools/make_treefx.py`; `assets/licenses.json`;
`source/college_r2/scratch/run_gates.ps1` (north_cw) and `source/college_r2/median_tops_check.py`.

### Needs Kevin

Nothing to decide. On the next drive: the paved median's colour (a muted salmon, matched to the 2022 photo), and that it
sounds and rumbles like a sidewalk if driven on.

## Round 3, item 1b (the PC, 2026-11-23): Mission Gorge's median no longer crosses a real intersection. Green on scratch, not rehearsed

***Superseded in its numbers by item 2 (below), the same day.*** *This section is the record of the first build
(ff406378), measured off the photo. Its finding stands: the island was built across a real crossing. Its strips do not:
I "corrected" the photo's readings against a band the island does not fill, and built the two strips 1.96 and 1.84 m
wide with their middles 0.70 and 0.58 m off. The lidar has them 1.24 and 1.30 m wide, and the gap at s 1087.5-1112.5
(11 stations, not 13). What ships is item 2's: the whole island on the lidar's faces. Nothing of this section was
rehearsed or installed.*

Item 1's aerial bins left four that read grey (MD13, s 1010-1210). Looked at on the mosaic, the grey is asphalt: the
photo shows the Margerum Avenue / Mission Vista Drive crossing there, with marked crosswalks on all four legs and no
median for about 33 m, and a narrow strip beside a left-turn pocket each side. The plan's median width on piece C is
linear between eye readings 250 m apart (st 1000: 4.5 m, st 1250: 5.5 m), so MD13 was declared, and built, as one
unbroken island 4.5-5.4 m wide straight across it. Both side streets are already built there as stubs (ledger 0054
phase 5: `mission_vista_drive_5977531_L`, `margerum_avenue_135149732_R`), so nothing was wrong but the median. The Mac
(2026-11-23): "A raised island across a signalised intersection is the kind of thing Kevin would see, so it joins THIS
round as item 1b." Everything measured is in `source/expansion/mg_median/` (README.md).

*Two things I first reported wrongly, both corrected with the Mac before any push.* (1) That the network had nothing at
the crossing and owed two stubs: I had read only the plan's junction arms S1-S6 and not `data/stubs.plan.json`. (2)
Strip widths of 1.75-2.5 m and 2.25 m with a 2 m offset: read off a threshold on blurred pixels, with no registration.
The measurement below replaces them. "Signalised" is **[inferred]** from the crosswalks.

### The measurement

A 2 m strip is four pixels and the mosaic stores one colour sample per about 1 m, so a face is not read off a
threshold. `faces_md.py` takes, per station, the **equivalent width** (the excess R - G over the asphalt's, summed
across the island, over a full island's plateau: +24.0 against -1.0) and that excess's **centroid**. Checked where the
island fills its band (37 stations): it reads the width 0.30 m short and the middle 0.49 m right of the declared band;
both are added back. One station scatters p10..p90 -1.41..+1.23 m in width. Piece frame, + = left = north-west:

| | measured | built from it |
|---|---|---|
| strip A, s 1010-1085 | 24 stations: 1.66 + 0.30 m wide, middle +0.18 against the band's +0.24, + 0.49 | **1.96 m wide, its middle 0.43 m left** of the line the full island's middle follows |
| strip B, s 1120-1192.5 | 26 stations: 1.54 + 0.30 m wide, middle -2.24 against the band's -0.25, + 0.49 | **1.84 m wide, its middle 1.50 m right** (its right face within 0.1-0.2 m of the declared one; the left comes in 3.1 m, one lane) |
| between the noses | 13 stations s 1087.5-1117.5, no terracotta | **no median**, noses at s 1085 and s 1120 |
| tapers | s 982.5-1010 and s 1192.5-1212.5 | linear to the declared band; the second lies under tree shadow: its ends are measured, the line between is **[inferred]** |

By count each strip's width holds to about +-0.15 m and its middle to about +-0.12 m; what the method does on a strip
narrower than the photo resolves, beyond that, is not measured. The lidar's ground returns across the median would
measure the faces directly; the lidar is on the G10 and was not read. **The centre line through the crossing: none**
(source: the photo; the centre reads no yellower than the asphalt beside it, at most 5.5 levels over it).

### What was built

1. **The data** (`fix_mg_median.py` + `mg_median_correction.json`, the MD7 precedent; idempotent, a further run leaves
   all four files byte-identical). Piece C's rows over s 982.5-1212.5 take the fit (91 change; 13 lose their median).
   **MD13 now ends at s 1085; a new MD13b runs from s 1120**, so no other median's id moves (722 ring stations as they
   were, 80 moved, 13 gone). `north_mission_gorge`'s island and paint are `tools/expansion_pieces.decorate`'s own output
   for piece C alone (decorate reproduces Mission Gorge's committed record exactly, so nothing rides along): 77 points
   change, 321-397; islands on points 8-48, 63-354 and 367-741. The two centre lines decorate's rule draws where a road
   has no median are cleared at the ten points between the noses. Lane and bike lines run on, as past every stub mouth.
2. **The island's rule, once** (`tools/median_island.py`). The draft tool `tools/author_median_blend.py` builds every
   island at once and never runs again on this chain. Its ring, deck, beam and post rule was lifted, line for line, into
   one module both it and the new step call. **The draft tool's output is byte-identical**: run against a stand-in bpy,
   what it hands to Blender matches the checksums taken before the lift, on the 0.20.4 fixture (a872da96...) and on the
   same fixture with a street-only span cutting an island (a3ec2944...); `tests/tools/test_median_island_rule.py`.
3. **The scene** (`tools/author_median_rebuild_blend.py`, author step `median_rebuild`, opt-in `route.median_rebuild`,
   between `college_split` and `median_tops`; `author_median_rebuild()` in `tools/ship_track.sh`). The Mac's rule: it
   must refuse unless the island it removes is exactly rows 63-741 as the committed blend holds them. It does more than
   count: from the record's data the rule gives every vertex the draft built, and each part must be in the scene as ONE
   loose part of exactly that many vertices, every vertex within 2 mm (the weld's own tolerance) of where the rule puts
   it. Then the old island goes and the corrected data's islands are built by the same rule, their changed paint by the
   assembler's own function (`ribbon.connector_markings`, as `tools/weld_mouths_blend.py` rebuilds it). The scene is
   stamped; a second run does nothing; a stamp of other data is fatal.
4. **The plants** (`mg_plants_data.py` -> `mg_median.median_spots.json`; `tools/make_treefx.py` now reads
   `median_spots.files` beside `file`). 39 spots stand on the changed stretch: 18 lie on the new deck and stay; **21
   are dropped** (6 between the noses, 14 on pavement beside the island, 1 on a strip's curb ring); none is moved. Every
   dropped spot is bare on the lidar (0.04-0.25 m, under its 0.3 m floor), and the script refuses to drop one the
   lidar saw.
5. **`median_tops` is unchanged.** The new decks go where the old one lay, so the tops step finds them in its own
   object and moves them across; its "half moved" refusal never has to become a move. `route.median_tops.paver` lists
   the three islands by their new rows.

### The corridor (`tools/barrier_bands.py`, not changed)

Nothing had to be declared. In a closure run the lane is sealed by the K-rail closure itself, one continuous strip, and
it runs straight through the gap. On the corrected data: exit 0, every self-gate, all four planned no_routes PASS. The
tool records the gap as one new opening, lap v1065-1076, and those 12 vertices go from zone "island" to "closure";
boxes, closure runs and whole are identical; the five noses are unchanged and still valid (v718 and v1451 are still the
first and last vertex of an authored island run). north_cw's closure moves on 77 vertices, at most 0.349 m (v1056);
north_acw's on 166, at most 0.954 m (v1052), following the island's left face in.

### Measured on a scratch workshop, through the chain's own commands

`run_full.ps1` then `run_gates.ps1` (street, race_cw, north_cw), a workshop seeded as the chain seeds one, Blender 4.2
below normal while the PC rehearsed. Pictures: `mg_median/crossing_before_after.png` (the photo, before, after).

| | item 1 on scratch | item 1b on scratch |
|---|---|---|
| `median_rebuild` | not there | the old island found whole: curb 4,074 v (CURB), deck 1,358 (`1LAWN_median`), beam 2,692 + 224 posts (GUARDRAIL), 74 + 156 paint strips; built: curb 1,752 + 2,250, deck 584 + 750, beams 1,144 + 1,476, 218 posts, 75 + 130 strips; new deck 0.177-0.196 m over the road; the curb's base -0.029..-0.009 m against the road, the old island's own range |
| `median_tops` | 2 tops across; paved 1,440 v; 2,123 rows | 3 tops across; 12 grass islands (2,842 v), 3 paved (1,416 v); 2,111 rows checked, 0 without a top |
| signs / verify_race G | 29 posts; 21,484 plants | 29 posts, the same; 21,463 plants (the 21 dropped), 0 in a lane or a wall on all three laps |
| the prep's conform | 79,062 / 203,540 / 53,792 | the same three numbers |
| the thinning / the walk's seat | 540,045 vertices / 3,202 lips | 540,042 / 3,201 (below) |
| kn5_ground_check, street / race_cw / north_cw | 0 cells; max +0.313; 43 of 10,900 | the same on all three |
| street drive_test / audit | PASS 10 drops, 44 far / CLEAN, F 0 of 101,834 | PASS 10 drops, 44 far / CLEAN, F 0 of 101,693, K 0, I 0 |
| race_cw drive_test / audit / no_route | PASS severe 7, fold 13, 0 drops / CLEAN / PASS | the same; F 0 of 109,497; leak 0, 138.2 k m2 |
| north_cw drive_test / audit / no_route | PASS severe 5, fold 12, 0 drops, 34 far / CLEAN / PASS, 88.4 k m2 | PASS severe 5, fold 12, 0 drops, 34 far / CLEAN, F 0 of 107,923, K 0, W 0 / PASS, leak 0, 0 of 325 probes, 88.5 k m2 |
| the built medians | 14 islands: 1,419 grass + 704 paved rows | 15 islands: 1,419 grass + **692 paved** (MD11 25, MD13 292, MD13b 375), 0 asphalt |

- **Three ground vertices and one lip.** The thinning keeps 540,042 ground vertices (item 1: 540,045; 0.20.5:
  540,064) and the walk's seat lowers 3,201 lips (3,202). The thinning reads its distances to the pavement's own
  vertices, and the island's curb is pavement; I have not traced the one lip. Every gate reads as before.
- **What stands on the paved islands:** still only their own barrier (`1WALL_guard`); where a vertex of it stands where
  it did, it stands at the same height.
- **Not run on scratch:** race_acw and north_acw, the whole of verify_kn5, the AI lines, TreeFX, the track folder.

### For the rehearsal

- As item 1: the engine copy must carry the snapshot's `scripts/ac/pbr.py`.
- On the first build from the committed blend `median_rebuild` prints the old island as found and saves;
  `median_tops` then prints `"from_one_top_object_to_the_other": 3`. A second run of either does nothing.
- Against 0.20.5 the road kn5 should differ, beyond item 1's list, in `1KERB_sidewalk_*` (the island's curb),
  `1WALL_guard`, MARKINGS and YLINE along Mission Gorge points 321-397, the trees (21 fewer), and the north layouts'
  closures (`1WALL_race_close_ncw_*` / `_nacw_*` on Mission Gorge) and AI lines, which follow the corridor.

### Tests

`tests/tools/test_mg_median_0099.py` (11: the fit, the rows, MD13 / MD13b, decorate's island and paint, idempotence,
the record giving back the committed island part for part, the old paint, the refusals, the plants, the wiring) and
`tests/tools/test_median_island_rule.py` (8: the draft tool's output against its checksums, the rule on small cases).
The step-order tests follow (`median_rebuild` second). `tests/tools/test_author_expansion.py` (the plan's generator
reproduces the committed intermediate) learns this correction as it knows Princess View's: the generator builds the
record's BEFORE rows and one island; the file holds the AFTER rows, MD13 and MD13b, and 722 ring stations outside the
stretch that are the generator's own points. On the PC the full run read 1,699 pass with that one test still failing
(it was not yet taught); it passes now, run with the files around it (140 pass). The other 11 failures and the 10
files that do not load are the same set as before item 1b, all this machine's own (no numpy, the live engine-july).
The full suite was not run again on the PC after that one test changed.

### Shared files touched

`tools/author_median_blend.py` (now builds from `tools/median_island.py`; output byte-identical), `tools/ship_track.sh`
(one new author function), `tools/make_treefx.py` (`median_spots.files`), `source/college_r2/scratch/run_full.ps1`.
`data/expansion.north.json`, `data/median_bands.json`, `data/connectors.local.json` (Mission Gorge's records only).

### Needs Kevin

Nothing to decide. On the next drive, Mission Gorge at Margerum Avenue: the median stops for the crossing and is a
narrow strip beside the turn lanes, as on the photo. The paint inside the crossing is plain lane dashes with no
crosswalks or stop lines (none are measured).

## Round 3, item 2 (the PC, 2026-11-23): Mission Gorge's median is the lidar's, in width and in place, and its J3 end stands where it is. Green on scratch, not rehearsed

The Mac's order asked for the plan's short island MD12 "only on measured rows". Looking for it on the aerial showed
the whole J3 end of the median off: MD11 leaves its declared line, the two openings stand about 13 m from the real
ones, and MD12 was declared on the first opening's asphalt. The Mac (2026-11-23): "make the J3 end true now, in this
round, with one rehearsal for 1 + 1b + 2." Then the G10 read the island's faces off the 2024 lidar
(`claude/lm-mg-median-lidar-20261123`, ef7c7bfa and 19cf9cc9), and that changed more than the J3 end: **the photo fit
item 1b was built on was wrong, and the whole island is narrower than the plan and off its place.** This item rebuilds
MD11, MD13 and MD13b over their full length on the lidar's faces. Everything measured is in
`source/expansion/mg_median/` (README.md; the G10's `mg_median_faces.lidar.g10.md`).

### What I got wrong

Item 1b measured the two strips beside the crossing's turn pockets off NAIP. To take out the photo's blur and
registration I read its bias on two stretches "where the island fills its declared band" (s 930-985, 1215-1260: width
0.30 m short, middle 0.49 m right) and added both back. **The island does not fill that band there.** The lidar has it
0.61 m narrower and 0.86 m right of it, over 41 stations. So what I took for the photo's error was the island's real
difference from the plan, and my correction moved good readings off: the photo's RAW readings agree with the lidar
(strip B's middle -2.24 against -2.32). Item 1b's commit ff406378 built the strips **1.96 and 1.84 m wide, their middles
0.70 and 0.58 m left of where the lidar has them**; they are 1.24 and 1.30 m. It was scratch-green and passed the
Mac's suite, because nothing in either measures the island against the ground. It was not rehearsed and not installed.
Item 1b's numbers above are the record of that first build; what ships is this section's.

The J3 end was first measured off the photo too (checkpoint d54f3909, scratch-green 12:56, never pushed on its own). No
correction was added there, and the lidar agrees with it to the photo's own +-0.75 m, except at MD11's end (below).

### The measurement

`mg_median_faces.lidar.g10.json` (s 25-300, 930-1260) and `mg_median_faces_full.lidar.g10.json` (s 225-2245): per 2.5 m
station the island's two curb faces (+- a median 0.03 m) and the road's two outer curbs, in piece C's frame (+ = left
of J3 -> J4 travel = north-west). Not measured there: the lidar's absolute horizontal accuracy (stated to 2 m).

| | the plan | the lidar |
|---|---|---|
| MD11 | s 45-167.5, on the line | s 25-182.5, 1.25 m wide; over s 132.5-182.5 it stands 3.2 m north-west of the declared band |
| the two openings | s 167.5-182.5, s 195-210 | s 185-192.5, s 210-220 |
| MD12 | s 182.5-195, 1.7 m wide | s 195-207.5, up to 3.6 m wide |
| MD13's start | s 210 | a nose at s 222.5 |
| the crossing | one island straight across | no median s 1087.5-1112.5; the strips 1.24 and 1.30 m wide |
| MD13b, s 1850-2000 | widens to 7.1-8.0 m | 4.8-5.4 m: the widening is not real |
| MD13b's last 70 m | 3-4 m wide | 1.1-1.4 m wide from s 2177.5 |
| MD13 / MD13b, 747 stations | | 0.73 m narrower than declared; the top 0.152 m over the road |

The photo had MD11 ending at s 177.5: the terracotta stops there and a paler strip runs on along the same line. That is
the island's plain nose (the lidar: raised to s 182.5).

### Where in the road the island goes

Its width needs no frame; its place does. The plan's road edges are eye readings on NAIP every 250 m (+-1.0 to 1.5 m
each) and the median was declared on the middle between them, so "0.7 m south-east of the declared band" could be the
island off in the road or the road off in the world. I asked for the road's outer curbs off the same lidar; the G10
read them (both curbs at 399 stations) and called each 50 m bin. **Over s 1250-2000 both of the plan's curbs sit
1.6-3.0 m north-west of the real ones**: the real road is about as wide as planned but displaced, and the real island
stands within 0.6 m of the real road's middle. Over s 1100-1200 the plan's edges are right and the island is off in the
road, as strip B really is.

The Mac's rule (2026-11-23), with three refinements it accepted the same hour:

- **Width:** the lidar's everywhere.
- **Place, per bin.** Edges true (6 bins): the lidar's own place. Edges off (28): the island's middle measured from the
  REAL road's middle, set from the PLAN's road's middle, so the lane room either side is the real one inside a road that
  is itself misplaced. Too few curb readings (7: s 400, 750, 850, 900, 1500, 1850, 2000): **[inferred: interpolated]**
  the shift drawn straight between the nearest called bins either side.
- **No jog at a bin's edge:** a bin's rule holds at its centre and is drawn straight to the next centre, inside one
  island (neighbouring bins differ by up to 1.5 m). Nothing is drawn across a real gap.
- **The J3 end (MD11, MD12) stays at the lidar's own place:** the bins there are not sound (the north-west "edges" are
  the side street's mouth and a bank), the south-east curb reads clean and within 0.33 m of the plan's over s 100-200,
  and the plan's middle cannot carry MD11's 3.2 m veer.

The first form of the too-few rule (the plan's own middle) would have swung the island off its line and back by up to
1.95 m (s 772.5; over 0.3 m at 172 stations).

**What the rule does.** Over MD13 / MD13b the island is set a median 1.65 m north-west of where the lidar has it (2.93 m
north-west to 1.71 m south-east). Against the plan it is a median 0.70 m narrower and 1.07 m north-west. At the 374
stations where the island and both real curbs read, lane room as built minus the real one:

| the island at | north-west side | south-east side |
|---|---|---|
| this rule | -0.15 m (p10 -1.44) | -0.18 m (p10 -1.41) |
| the lidar's own place everywhere | +1.41 m | -1.74 m |
| the plan's place (0.20.5, installed) | +0.11 m | -1.44 m |

Painted lanes (decorate spreads 3 + 3 evenly and drops to 2 under a 2.9 m lane): 0.20.5 has 2 instead of 3 on one side
at 220 station-sides, the south-east side over s 1585-2020 (435 m) among them. This build has 111 (north-west
s 345-362.5, 755-827.5, 897.5-1010; south-east s 2000-2042.5, 2060-2080), all where the plan's road is narrower than the
real one.

### What was built

1. **The data** (`fix_mg_median.py`, rewritten; `mg_median_correction.json`). 881 rows of piece C (s 45-2245) take the
   lidar: each face the median of its own station and the two beside it in its island; the 55 unclear stations from the
   nearest clear lidar (the record lists each); a row with no median gets an offset drawn straight between the islands
   either side, so the lane lines do not jog across an opening **[inferred]**. Islands: **MD11 s 45-182.5, MD12
   s 195-207.5, MD13 s 222.5-1085, MD13b s 1115-2245**; on connector points 8-53, 67-354, 365-741 and MD12's four
   points 58-61. 733 of the line's 746 points change; 4,433 paint offsets; 34 centre-line offsets cleared at the 17
   points with no median (source: the photo). Idempotent; the record keeps every declared value.
2. **The scene step takes several islands** (`tools/author_median_rebuild_blend.py`; `route.median_rebuild.was_rows` is
   one pair or a list). Each old island is found on its own, exactly, or the step refuses; an island left unnamed
   between them is refused; the stamp's checksum covers the list. No tolerance moved (GATES-CHANGELOG).
3. **The plants** (`mg_plants_data.py`, `mg_median.median_spots.json`, `mg_plant_tops.g10.json`). Of the island's 329
   spots, 226 lie on the new deck and stay, 97 are dropped (every one bare on the lidar), and **6 have a plant on the
   lidar that the deck no longer reaches**. The Mac: "a real plant the lidar saw is never dropped because the island
   moved under it" (Kevin, 2026-11-18: "we've reduced lake murrays center bushes far too much"). They are moved, by a new
   opt-in list in `tools/make_treefx.py` (`median_spots.move`; a move over 5 m [invented] is refused): three to the
   lm-shrub plant top within 2 m (tops 400701, 401191, 403275, read by the Mac off the G10's `lm_shrub.tops.npz`),
   carried across by the shift their island was given so each keeps its place ON its island; three straight across onto
   the deck, an **[inferred position]** (two have no top within 2 m; one's top lands off the deck). They move 0.44 to
   1.53 m; each keeps its own lidar height. None is 10 m or taller.
4. **`route.median_tops.paver`** lists the three islands by their new rows (8-53, 67-354, 365-741).
5. **Item 1's MD11 sentence** is corrected above.

### The corridor (`tools/barrier_bands.py`, not changed)

On the corrected data, before the scene: exit 0, every self-gate, all four planned no_routes PASS. The north lap's
openings are v764-776 (the J3 end; 0.20.5's data: v759-772), v1065-1074 (the crossing, new) and the two corners'; whole,
boxes and closure runs are identical, and the five noses are unchanged. Against 0.20.5's data the closure follows the
island on 736 vertices of north_cw (at most 2.93 m, v1344) and 699 of north_acw (1.95 m, v970). On Mission Gorge the
clockwise lane is 8.35 m at its narrowest (0.20.5's data: 7.87) and the anticlockwise 8.12 (8.88).

**MD11 from s 25 was tried and is not built.** The corridor tool refuses it: "v718 is not the first vertex of an
authored island run", and the closure's pin at v712-713 goes to 1:0.17 with a 9-10 m plan radius (limits 1:3 and 20 m).
It needs the J3 corner re-declared. The Mac: "Don't force it."

### Measured on a scratch workshop, through the chain's own commands

`run_full.ps1` then `run_gates.ps1` (street, race_cw, north_cw), a workshop seeded as the chain seeds one, Blender 4.2
below normal. Every step exit 0. Pictures: `mg_median/j3_before_after.png`, `crossing_before_after.png`,
`crossing_before_after_close.png` (the photo, 0.20.5, this build).

| | 0.20.5's islands, paved (item 1 on scratch) | this build |
|---|---|---|
| `median_rebuild` | not there | both old islands found whole: curb 246 + 4,074 v (CURB), deck 82 + 1,358 (`1LAWN_median`), beams 140 + 2,692 and 235 posts (GUARDRAIL), 693 + 1,480 paint strips; built: curb 276 / 1,728 / 2,262, deck 92 / 576 / 754, beams 160 / 1,128 / 1,484, 230 posts, 716 + 1,428 strips; new decks 0.173-0.202 m over the road; the curbs' base -0.033..-0.003 m against the road (the old islands': -0.030..-0.009) |
| `median_tops` | 2 tops across; paved 1,440 v; 2,123 rows | 3 tops across; 12 grass islands (2,842 v), 3 paved (1,422 v); 2,110 rows checked, 0 without a top; MD12's 4 rows reported as too short to be an island |
| signs / verify_race G | 29 posts; 21,484 plants | 29 posts, PASS; 21,387 plants (97 dropped, 6 moved), 0 in a lane or a wall on all three laps |
| planned no_route, the north lap | PASS | PASS, 89.9 k m2 (cw) and 91.6 k m2 (acw) |
| the prep's conform | 79,062 / 203,540 / 53,792 | the same three numbers |
| the thinning / the walk's seat | 540,045 vertices / 3,202 lips | 540,057 / 3,201 |
| kn5_ground_check, street / race_cw / north_cw | 0 cells; max +0.313; 43 of 10,900 | the same on all three |
| street drive_test / audit | PASS 10 drops, 44 far / CLEAN, F 0 of 101,834 | PASS 10 drops, 44 far, severe 0 / CLEAN, F 0 of 101,739, K 0, I 0 |
| race_cw drive_test / audit / no_route | PASS severe 7, fold 13, 0 drops / CLEAN / PASS | PASS severe 7, fold 13, 0 drops, 142 far / CLEAN, F 0 of 109,543, W 0 / PASS, leak 0, 0 of 377 probes, 138.2 k m2 |
| north_cw drive_test / audit / no_route | PASS severe 5, fold 12, 0 drops, 34 far / CLEAN / PASS, 88.4 k m2 | PASS severe 5, fold 12, 0 drops, 34 far / CLEAN, F 0 of 107,969, W 0 / PASS, leak 0, 0 of 326 probes, 90.0 k m2 |
| the built medians (`median_tops_check.py`) | 14 islands: 1,419 grass + 704 paved rows | 15 islands: 1,419 grass + **691 paved** (MD11 40, MD13 279, MD13b 372), 0 asphalt; 22 rows under 1.2 m wide are not probed |

- **A red gate on the way, kept red.** The mechanism was first run on the stations the first lidar file covered. It
  stopped at verify_race G on the anticlockwise north lap: one median plant (spot 880, 3.87 m tall on the lidar), left
  standing where the corrected island's deck no longer reached it, read 0.015 m inside the closure. Nothing was forced
  or loosened; that gate is why the plants have a move rule. With the island placed by the road's bins spot 880 is back
  on the deck, and the six spots listed above are the ones moved.
- **What stands on the paved islands:** only their own barrier (`1WALL_guard`), rebuilt with them.
- **The thinning and the lip** differ by a handful as in item 1b (540,057 ground vertices against 540,045; 3,201 lips
  against 3,202): the thinning reads its distances to the pavement's own vertices, and the islands' curbs are pavement.
  Every gate reads as before.
- **Not run on scratch:** race_acw and north_acw, the whole of verify_kn5, the AI lines, TreeFX, the track folder.
  The rehearsal runs them.

### Owed, on the board

- **Piece C's road edges.** 28 of the 41 bins read the plan's edges off, 22 of them by 1 m or more (1,100 m), up to
  2.9 m. Blast radius of re-fitting them: the ROAD ribbon of `north_mission_gorge` in the committed blend (746 points,
  both edges), both curbs and sidewalks, all 14 paint lines, the ground's conform band beside the road; 7 side-street
  stubs with their 7 welded mouths (Conestoga Way, Mission Vista Dr twice, Margerum Ave, Mission Montana Dr, Deerfield
  Crescent, Deerfield St) and 16 curb cuts; 40 lamp posts (every one within 3 m of a plan curb); the north ribbon's
  signs; the trees and houses beside it (not counted); the north lap's closure (2,204 m on both layouts), curb strips,
  the J3 and J4 corner kerbs and pads, both AI lines; every north gate. Lake Murray never re-drafts, so it needs an
  author step that re-ribbons a road in the scene, which nothing in round 3 does. Its own round (the Mac agreed).
- **The painted lanes** that drop to 2 at 111 station-sides go with it.
- **MD12**, the island itself (12.5-17.5 m long; four connector points; the tools build on six).
- **MD11, s 25-45** (with the J3 corner).
- For that round, from the outer curbs: over s 50-100 the plan's south-east edge is 1.27 m too far out (16 curb stations).

### For the rehearsal

- As items 1 and 1b: the engine copy must carry the snapshot's `scripts/ac/pbr.py`.
- On the first build from the committed blend `median_rebuild` prints both old islands as found (curb [246, 4074]) and
  saves; `median_tops` then prints `"from_one_top_object_to_the_other": 3`. A second run of either does nothing.
- `make_treefx` reports `"median_spots": {"dropped": N, "foot_moved": M, "moved": 6}`.
- Against 0.20.5 the road kn5 differs along the whole of Mission Gorge: `1KERB_sidewalk_*` (the islands' curbs),
  `1KERB_PAVER_median`, `1LAWN_median`, `1WALL_guard`, MARKINGS and YLINE, the trees, and the north layouts' closures
  and AI lines.

### Tests

`tests/tools/test_mg_median_0099.py` (13): the row rule on a made-up piece (the median of three, an unclear nose, an
unclear station inside an island, a gap's offsets, the return to the plan where coverage ends, the held start); the
placement on a made-up piece (edges true, edges off, a too-few bin both ways, nothing drawn across a gap) and the G10's
41 bins as the script reads them; piece C's rows against the lidar, station by station; the islands; decorate's island
and paint; idempotence; the record giving back the committed islands part for part; the old paint; the refusals; the
several-islands form; the plants (no spot with a plant dropped, every move lands with its trunk on the deck, the tops);
the wiring. `tests/tools/test_make_treefx_plan.py` gains the move list's test (the spot at its new place with its
model, angle, size and measured height; the three refusals). `tests/tools/test_author_expansion.py` learns the lidar
correction as it knows Princess View's. `test_terracotta_median_0099.py` and `test_median_tops_0055.py` follow the rows.

On the PC the full run reads **1,703 pass**; the 11 failures and the 10 files that do not load are the same set as
before item 1, all this machine's own (no numpy; the live engine-july), none in a file this item touches. The nine test
files around the change were run again after the last edit: 130 pass.

### Shared files touched

`tools/author_median_rebuild_blend.py` (several islands), `tools/make_treefx.py` (`median_spots.move`, opt-in),
`data/expansion.north.json`, `data/median_bands.json`, `data/connectors.local.json` (Mission Gorge's records only).
`fleet/GATES-CHANGELOG.md`.

### Needs Kevin

Nothing to decide. On the next drive, Mission Gorge Rd: the median is narrower (about 0.7 m), paved terracotta, stops
for the Margerum Avenue crossing with a narrow strip beside each turn lane, and near J3 it swings toward the north-west
side and has its two openings where they really are. Known and owed: the road itself is up to 3 m off its real place
over about 750 m (its edges were read by eye), a short island near J3 (MD12) is only a painted outline, and the painted
lanes drop from 3 to 2 on one side in five short stretches where the road as built is too narrow.
