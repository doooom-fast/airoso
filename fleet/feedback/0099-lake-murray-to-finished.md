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
