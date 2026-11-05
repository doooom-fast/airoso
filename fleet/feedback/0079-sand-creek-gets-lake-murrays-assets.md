---
id: 0079
title: Sand Creek gets Lake Murray's asset set, built by the chain (round A: buildings, trees, lamps, textures)
status: in-progress
scope: tracks/sand-creek-lm (first user); the steps are general
layer: engine (chain steps + per-track config)
train: -
---

Cites ledger 0078 (the fleet builds on Lake Murray v4's engine; Sand Creek's port `tracks/sand-creek-lm` 0.1.1).

## Request (Kevin, 2026-11-04)

> "let's get the system building assets and tracks based on lake murray, starting with sand creek"

Kevin's standing words that apply: Lake Murray v4 is the engine and is not hand-authored; "same lamps as lake murray, race
curbs, no sidewalks, authored pad junctions"; "I just want real"; "Add textures"; "Lake Murray v4 had many more houses in it
this time, don't lose those".

Every asset is a chain step plus per-track config, and Sand Creek is the first track to use each one. Each key below is
absent in Lake Murray's config, or its default is Lake Murray's own value.

## Kevin's three calls (2026-11-05, through the coordinator)

- Where two Sand Creek side streets meet, real junctions or overlaps: **"Real junctions"**. This covers all 146 meetings in
  `data/grid_meetings.json`: the 17 arterial/arterial and 110 minor/minor overlaps each become one welded deck with the
  mouths cut; the 19 already welded stay as they are.
- "Same lamps": Lake Murray's sodium light or Sand Creek's own wash: **"Lake Murray's sodium"**.
- Signs: Lake Murray's rule-placed arrow signs, street-name signs from the real names, or both: **"Both"**.

## Round A (Mac): what was built, 0.2.0

Branch `claude/sand-creek-lm-assets` (cut from `origin/claude/fleet-lm-engine` de9aefa). Built on the Mac by
`tools/ship_track.sh` with the Blender path swapped, from an EMPTY workshop, `--no-install`, ENG = the engine-july snapshot's
`scripts/` + `vendor/` with airoso's `assets/textures`. **SHIP OK. Every gate is green and no gate is worse than 0.1.1.**

| asset | built | source data | step / config key |
|---|---|---|---|
| **buildings** | **2,261 blocks** (0.1.1: 451): 1,304 lap-siding houses, 759 tilt-up, 189 metal, 9 stucco; 60 dropped (56 on more relief than their height allows, 2 within 3 m of a road, 2 more than 450 m from the lap, off the ground); all on the built ground (no far block) | OSM `way[building]`, 1,237 (fetched 2026-11-04, `source/bespoke/osm_buildings.cache.json`) + Microsoft GlobalMLBuildingFootprints, 2,326 in the box, 1,213 where OSM has none (`source/bespoke/msft_buildings.json`, ODbL) -> `tools/plan_buildings.py` -> 2,321 planned. Heights of the stood blocks: Microsoft's ML estimate 1,763, OSM `building:levels` 20, class default [invented] 478 | `author.bespoke` (`scenery.bespoke.blocks` -> `source/bespoke/buildings.lm.json`); the planner's new `ml_height_check` and `lidar` plan keys |
| **ground** | the port's own 3DEP grid, margin 470 m (106 x 76 at 40 m) | `scripts.elevation.heightfield.build_heightfield` on the source's line; 470 = 150 + 8 x 40 on the source grid's lattice: all 5,400 old samples are samples of the new grid, 0.000 m apart (test pins it) | `lm_intake.heightfield: "port"` (new), ship.json `sync_in.optional` |
| **trees** | **5,615 crowns** read; 5,567 TreeFX trees once the PC's models resolve (46 within 5 m of a road, 2 on a building): 1,075 riparian (cottonwood zone), 4,492 street / yard trees. Every crown is drawn on `source/bespoke/trees_overview.jpg` | NAIP 2023-09-25 z18 (0.46 m/px): one tree per crown top, the brightness maximum of the canopy mask, no grid / jitter / random thinning. Crown width measured (p10 / p50 / p90 3.6 / 4.9 / 6.8 m); height = width / ratio [invented]; riparian = within 60 m of OSM's Sand Creek [invented reach] | `tools/plan_bespoke_vegetation.py` `place: "crowns"` (new) -> `source/bespoke/trees.lm.json`; ship `treefx`; `lm_intake.tree_models` (new) copies the PC's licensed `.bin` |
| **lamps** | 175 posts, Kevin's `led_cobra`, 2 arms; unchanged since 0.1.1 | the assembler's `build_streetlights`: Lake Murray's rule (every 55 m, alternating sides, half-width + 2.8 m out, >= 25 m apart, no post where the road stands > 6 m over the ground) + `tools/author_lamps_blend.py`, as on Lake Murray | draft `lamps`, `scenery.streetlights.model` |
| **textures** | 0 visible meshes untextured, across 29 materials and 21 embedded textures in the road kn5 | Lake Murray's wall / roof rows, plus `BUILDING_SIDING` for Sand Creek's houses, pointed at airoso's tracked files | `texture_overrides` (11 rows) + ship.json `sync_in.assets` (12 files, md5s in runbook 4g); new gate `textures` |

**Lamps vs Lake Murray.** The model and the spacing rule are the same code with the same values, so there is nothing to fix.
Two things differ:
- **The CSP light.** Sand Creek's `lighting.streetlight` is its own wide dim wash, not Lake Murray's 1980s low-pressure
  sodium. Ledger 0070 D1 kept it that way. Whether "same lamps" includes the light colour is Kevin's call.
- **Where the posts stand.** Lake Murray's posts stand on its sidewalk. Sand Creek has none, so they stand on the ground
  2.8 m past the lane.

**Trees vs 0.35.0's.** Sand Creek's live plan has an 11 m grid, 3.5 m random jitter, a 45 % random interior keep and a random
species share. That plan is not used here. The z16 colour rule (g/r 1.02, g/b 1.1) took lawns, dirt lots and the crowns'
shadows as canopy: 13.4 % of the box at z18. It was re-read on sampled pixels:
- crowns: mean 66-83, g/r 1.19-1.37, excess green 44-54;
- a dark lawn: g/r 1.08;
- a street: g/r 1.07;
- a lot: g/r 0.96.

The new rule (g/r >= 1.15, g/b >= 1.2, excess green >= 38) calls 3.0 % of the box canopy.

**What limits the building count is the real footprints.** Within reach of the lap there are 2,321 footprints, and 2,261 of
them are stood. Sand Creek is an industrial district. Its houses are the Swansea / Elyria blocks north of 56th and west of
Colorado, and Microsoft's tile is what adds them: OSM maps few houses there. Lake Murray's 7,600 come from a dense
neighbourhood (30,240 footprints planned).

**Heights.** CO_DRCOG_2_2020 covers the whole box: the ept.json `boundsConformance` contains Sand Creek (probed from the
Mac). The Mac has no LAZ reader, so `tools/lidar_buildings.py` is written for the PC (runbook 4g). It measures, per
footprint:
- ground: the median class-2 return in a 1.5-6 m ring round it;
- the roof: the p10 / p50 / p95 of the non-ground first returns inside the footprint shrunk 0.6 m.

`plan_buildings.py`'s new `lidar` key puts those measured heights first:
- flat roofs: p50;
- pitched roofs: eave at p10, ridge at p95.

The PC's step 1 fetches 1,769 EPT nodes, down to depth 11 (a 0.6 m voxel). The pip / shrink helpers and the planner's lidar
path are tested on synthetic roofs. **Until the PC runs it:** Microsoft's ML heights outside [2.5 m [invented], the class
cap] are not taken as measurements (`ml_height_check`; 345 rejected). Sand Creek's tile reads industrial blocks at 0.1-0.7 m
and 60 m² sheds at 24 m. The first build left 13, then 11 such blocks "buried" (house_seat), so the class default stands
for those footprints.

### Gates, BUILT kn5 (Mac, empty workshop)

| gate | 0.1.1 | **0.2.0** |
|---|---|---|
| drive_test race / street: soft top, severe, obstruction, floating furniture, undrivable | 0 / 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 / 0 |
| kinks /km, fold bumps, excursion drops, far ledges (both layouts) | 0.41, 4, 0, 1 | 0.41, 4, 0, 1 |
| drive_test verdict, both | PASS | PASS |
| audit_mesh | CLEAN (road 39,380 v, grass 170,108 v) | CLEAN (road 39,380 v, grass 212,722 v) |
| kn5_ground_check race / street | PASS (lamp heads 201, orphans 0) | PASS (201, 0) |
| house_seat | PASS, 450 judged | PASS, 2,261 judged (floating 0, sunken 0, buried 0) |
| houses (new on this track; floor = the count built) | - | PASS: roofs 2,261 / blocks 2,261 / colliders 0 |
| textures (new) | (0 untextured, run by hand) | PASS: 0 untextured |
| edge_report (not a gate) | strip on top at 1 m 99.7 %, ground 10 m out -0.20 / -0.18 / -0.16 | the same |

| kn5 | 0.1.1 | 0.2.0 |
|---|---|---|
| road `sand_creek_raceway_lm.kn5` | 41.0 MB | **48.4 MB** |
| street-only `_street.kn5` | 1.8 MB | 1.8 MB |
| spawn kn5s (x2) | 2 kB each | 2 kB each |

### Lake Murray unchanged

- **Untouched files.** Not one file under `tracks/san-diego-lake-murray/` or `scripts/` changed. The assembler, the weld and
  every other draft / author / prep tool Lake Murray's chain runs are the same bytes, so its `blend_digest` / `draft_equiv`
  records stand as ledger 0078 left them.
- **Spec lines.** Lake Murray's spec lines through `tools/ship_track_spec.py` are identical through this branch and origin's
  (Mac md5 `8839f38e56c9c90e057f53fb95bb4293` on both). `ship_track.sh` gained only the function `gate_textures`, a name
  Lake Murray's ship.json does not list.
- **Every new key is opt-in:**
  - `lm_intake.heightfield` and `lm_intake.tree_models`: the intake never runs on Lake Murray.
  - `place: "crowns"`, `lidar` and `ml_height_check` in the planners' plans: Lake Murray's `buildings.plan.json` names none
    of them.
- **The planners' default paths.** Origin's and this branch's `plan_buildings.py` and `plan_bespoke_vegetation.py`, run on
  Sand Creek's live plans in scratch copies, write byte-identical files, and both equal the committed ones:
  - `buildings.json` `42ac341a…`;
  - `trees.json` `c93bfc78…`.
- **Tests:**
  - `tests/tools/test_sand_creek_lm_assets.py`: 6 pass (Lake Murray names none of the keys; the port grid keeps every source
    sample; the crowns reader; the lidar helpers; the texture gate's input error).
  - `test_lm_engine_port.py`: 9 pass.
  - `test_ship_track_chain.py`: 29 pass.
  - `test_ship_track_drive1_gates.py`, `test_plan_buildings.py`, `test_make_treefx_plan.py`, `test_house_gate.py`,
    `test_bespoke_assets.py`: all pass.

## Rounds B and C: not built. Each needs new code, and one needs Kevin's call

Research on the Lake Murray junction tools (file:line in the round's notes):

- **The 106 grid streets.** These parts work with no code change:
  - `lm_intake.connectors` true;
  - `trim_connectors` -> `rebuild_loop_blend` -> `weld_mouths` -> `seat_terrain` -> `gap_mouths` -> `verify_mouths`;
  - `route_connectors`, `divide_connectors`, `stubs` and `aprons` are no-ops with their keys absent.

  Three gaps:
  1. `tools/trim_connectors.py` cuts a street against the LAP only, plus any street named in `route.divided_connectors`.
     Two grid streets that meet are left as two coplanar ribbons overlapping, with no mouth and no weld. Sand Creek's
     grid has 146 such meetings (grid.report.json `meetings_eased`).
  2. `seat_terrain_blend.py` holds the ground under a 3.1 m sidewalk (`SIDEWALK_M`, a constant). Sand Creek's edge is a
     1.8 m strip.
  3. `seat_terrain_blend.py` asserts the ribbon's vertex count, so it must run before `densify_ribbon`.
- **The six authored pad junctions** (ledger 0070: Colorado/50th, 50th/Ash, 50th/Dahlia, Dahlia/56th, Sand Creek
  Dr/Quebec, 46th/48th/Colorado). Neither existing pad tool fits:
  - Lake Murray's `junction_pad.py` + `author_junction_pad_blend.py` only take the north expansion's intermediate
    (`expansion_pieces.PIECE_CONN` is hard-coded), and they lay a 0.14 m curb + walk;
  - the Lariat's `lm_pads_blend.py` cuts the LAP only, with no connector arm. Its outline tool, `draft_pad_outline.py`,
    is not in this tree.

  A pad module with street arms on the no-curb edge is owed.
- **Race kerbs and the closed race.** These need the street mouths first: `barrier_bands` closes the race at the side
  streets it meets. Sand Creek's public streets carry no race-kerb paint (NAIP, ledger 0070 Q1), so at its race corners
  the kerbs are Lake Murray's race-furniture kerbs (`author_race_furniture_blend`, `1KERB_race_*`). Those are race
  furniture, placed by Lake Murray's corner rule, not measured.
- **Signs.** Lake Murray's `author_signs_blend` stands W1-6 arrows at tight corners (by rule) and per-layout plates. No
  chain step stands street-name blades from OSM names. Only airoso's `build_env` does (`scripts/environment/signs.py`), and
  it is not a chain step.

## Round B (Mac): the parts that do not wait on Kevin's three decisions

The coordinator, 2026-11-04 (Kevin's calls on street-to-street junctions, the light colour and the signs are pending):
seat_terrain's sidewalk becomes config; seat_terrain goes before densify; the grid streets go as far as the existing junction
code takes them, and their size is measured; the pad module; tree heights from lidar; then 0.2.1 when the PC pushes the
roofs.

### 1-2. seat_terrain on Sand Creek's chain (committed; Lake Murray's chain as it was)

- **The new key.** `route.seat_edge_m` (`tools/seat_terrain_blend.py`) is how far past the lane the ground is pinned under
  the edge. Absent = the old constant, 3.1 m (Lake Murray's curb + walk + grade). Sand Creek sets **1.8 m**: its no-curb strip,
  0.1 + 0.2 + 1.5 m. No sidewalk.
- **The chain.** Sand Creek's ship.json runs `seat_terrain` after `weld_mouths` and before `densify_ribbon`, because seat
  asserts the assembler's ROAD vertex count, which densify changes.
- **The build** (empty workshop, Mac): **every gate identical to 0.2.0**:
  - drive_test both layouts: kinks 0.41, fold bumps 4, drops 0, far ledges 1;
  - audit CLEAN; kn5_ground_check PASS; house_seat PASS;
  - houses 2,261 / 2,261 / 0; textures 0 untextured;
  - road kn5 48.4 MB.

  Changed:
  - grass 212,722 → 213,461 vertices;
  - 1,056 terrain faces cleared from under the mended folds;
  - strip-seam misses 19 of 6,434 (0.1.1: 24).

### 3. The 106 grid streets, as far as the existing junction code goes (scratch run, NOT committed to the chain)

**Run setup.** A scratch track folder (a copy of the port, never committed). Its config:
- `lm_intake.connectors` true;
- `route.connector_hosts ["grid_primary*", "grid_secondary*"]` (new in `tools/trim_connectors.py`: hosts that are not
  divided; absent = as before);
- `route.seat_edge_m` 1.8;
- `strip_seam.scope` local;
- `scenery.streetlights.drop_on_road`.

Chain: lm_intake → build_loop_blend → trim_connectors → rebuild_loop_blend → weld_mouths → seat_terrain → densify_ribbon →
seat_edges → strip_seam → gap_mouths → lamps → (author) layout_dummies, bespoke → prep → … → gates + verify_mouths.

**Fixes the run needed, all general, all opt-in or a no-op on Lake Murray:**
- **trim.** A mouth whose piece trim dropped is no longer a mouth. A frontage stub cut twice, between the lap and
  Colorado, left 2 orphan mouths that failed the weld. Lake Murray's committed inputs through origin's trim and this
  branch's give byte-identical outputs.
- **strip_seam.** It skips lap rows inside a mouth (the very rows gap_mouths deletes): 236 rows at 36 lap mouths. The
  global scope still missed 94 of 6,198 on the subdivided ground; the local scope (the Lariat's) joins all 6,170 with
  **0 missed**.
- **gap_mouths** runs after strip_seam. strip_seam reads the CURB layout that gap_mouths changes.
- **lamps.** `drop_on_road` leaves out a draft post that a later road stands on, and records it in `lights.local.json`
  `dropped_on_road`. 2 posts (7, 151). author_lamps' self-check had refused them.

**Results (BUILT kn5):**

| | 0.2.0 + seat_terrain (committed) | **with the grid streets (scratch)** |
|---|---|---|
| road kn5 | 48.4 MB | **63.7 MB** |
| street-only kn5 | 1.8 MB | **6.9 MB** (the streets' centre lines) |
| total against ~120 MB | 50.2 | **70.6 MB** |
| mouths | 0 | 52 cut, 50 welded (36 on the lap, 14 on arterial hosts) |
| drive_test race / street | PASS | **PASS** |
| kn5_ground_check | PASS | PASS |
| textures | PASS | PASS |
| audit_mesh | CLEAN | **525: I 292 (strip isolating pavement), K 233 (strip in a carriageway)**, worst 1.02 m |
| verify_mouths (new on the track) | - | **FAIL, 11 of 50 mouths** (below) |
| houses | 2,261 | 2,245 (16 blocks now stand on a street ribbon and are dropped; the floor would be re-set for a streets build) |
| lamps | 175 | 173 (2 dropped on a street) |
| roads / grass vertices | 39,380 / 213,461 | 50,123 / 335,253 |

**verify_mouths, by place.** 7 of the 11 failing mouths are at the authored pad junctions, where the lap corner, the
frontage roads and Colorado crowd one box. The pads replace exactly those mouths.
- 48th/Colorado: `grid_primary_49`, `grid_primary_52`, `grid_tertiary_98`, `grid_unclassified_67`.
- Sand Creek Dr/Quebec: `grid_primary_78`, `grid_primary_80`.
- Colorado/50th: `grid_unclassified_9`.

The other 4:
- `grid_tertiary_5`: approach grade change 3.9 %/m;
- `grid_tertiary_16` on Colorado: the approach changes 29 %/m (the host's own deck);
- `grid_unclassified_27` on Quebec: the host lane 0.43 m over the deck and a 21 %/m approach;
- `grid_unclassified_77`: the notch, the host's strip left across it.

The audit's I / K (525) are the streets' edge strips where two streets overlap and where a strip crosses a host's
carriageway. That is the street-to-street weld the coordinator held for Kevin.

**The 146 street-to-street meetings** (`tracks/sand-creek-lm/data/grid_meetings.json`, `tools/grid_meetings.py`: every
meeting with its pieces, kind, shape, local x / z and lon / lat). With the arterials as hosts:
- **19 become mouths:** arterial/minor, 14 L + 5 T;
- **127 stay overlaps:**
  - arterial/arterial: 17 L (two hosts are never cut against each other);
  - minor/minor: 53 L, 40 T, 17 X.

"L" is two pieces ending at one node: OSM ways split at a junction, so the through street is two pieces.

### 4. The pads: declared and ready to measure; the author with street arms is not built

- **The outline tool.** `tools/draft_pad_outline.py` was not in this branch. It is the Lariat's (origin/claude/lariat-pads-wip,
  4970fca5, "P3b method 1"), brought here unchanged except that it also reads an LM port's `lm_pads.pads`. It measures the
  asphalt outline from the CO_DRCOG_2_2020 lidar intensity edge and the deck from class-2 ground (±0.4 m). It needs the LAZ
  stack, so it runs on the PC. Its `aerial` (NAIP) source kind was never built.
- **The declarations.** New `tools/pad_boxes.py` writes `lm_pads.pads` from `lm_pads.plan`: ledger 0070's six nodes and
  0073's NAIP curb returns. For each pad:
  - node = the nearest lap vertex;
  - cuts 30 m of arc either side;
  - the junction box out to half width + curb return + 6 m [invented];
  - the street arms and their cut lines.

  The six:
  - **colorado_50th:** v140, cuts 129 / 151, arms unclassified_9, unclassified_10, primary_51, primary_53, unclassified_76;
  - **50th_ash:** v186, unclassified_17;
  - **50th_dahlia:** v411, unclassified_0, tertiary_44;
  - **dahlia_56th:** v780, primary_35;
  - **sandcreek_quebec:** v1942, primary_78, primary_84;
  - **48th_colorado:** v3205, cuts 3193 / 3216, primary_49, primary_52, tertiary_98.

  The 48th/Colorado out cut stops at the lap seam (L13: no cut wraps), 33 m past its node.
- **The PC.** Runbook 4g step 3 now measures the six outlines on the rehearsal workshop, together with the roofs and trees.
- **Not built: the author with street arms.**
  - `tools/lm_pads_blend.py` cuts the lap and lays the deck, but closes every road the lap does not take with a K-rail. The
    free roam needs those roads welded to the deck instead: each arm's ribbon cut on its line and its end row welded to the
    deck edge.
  - That extension and verify_pads' no-curb shape cannot be checked on the Mac before the outlines exist.
  - It is the next piece of work once the PC pushes `source/pads/*.json`.

### 5. Tree heights from lidar (for the PC)

`tools/lidar_buildings.py --trees source/bespoke/trees.plan.json` measures the crowns in the same EPT read as the roofs:
- canopy = the p95 of the non-ground first returns within the crown radius (at least 1.5 m);
- ground = the median class-2 return within the radius + 3 m.

The crowns planner's new `lidar` key takes the height before the [invented] width ratio, inside 2-35 m. Tested on a synthetic
crown. Runbook 4g step 3 runs roofs, trees and pad outlines as one job.

### Lake Murray unchanged (round B)

- **trim.** Its committed trim inputs through origin's and this branch's `trim_connectors.py` give byte-identical
  `connectors.local.json`, `mouths.json` and `median_bands.json` (`664da93b…`, `b73b70f4…`, `f0c97952…`).
- **seat_terrain.** With `route.seat_edge_m` absent, the only new code is a config read; the constant stays 3.1 (a test pins
  it).
  - I tried an A/B on Lake Murray's committed `loop.blend`. Both versions refused to seat it identically: the committed
    blend is post-stubs and post-pads, so it is not the layout seat runs on.
  - The real A/B is the PC's step 5(a) (`--dry-run` through both branches, `blend_digest` + `draft_equiv`). It now covers
    this change and should be re-run.
- **Other changed tools.**
  - `strip_seam`, `author_lamps`' `drop_on_road` and `pad_boxes`: Lake Murray never runs `strip_seam` or `pad_boxes`, and it
    does not set `drop_on_road`.
  - `gap_mouths` is unchanged.
- **Spec lines.** Lake Murray's ship.json and spec lines are unchanged.
- **Tests:** `test_sand_creek_lm_assets.py` 10 pass (round B keys absent from Lake Murray; host matching; lidar tree
  heights; the six declarations validate); `test_draft_pads.py` 13 pass.

## Round C (Mac): 0.2.1, the PC's lidar (da370cab) built in; the pads tried and held back

Built on the Mac from an empty workshop: SHIP OK, every gate green, nothing worse than 0.2.0.

| gate (BUILT kn5) | 0.2.0 | **0.2.1** |
|---|---|---|
| drive_test race / street | PASS: kinks 0.41, fold bumps 4, drops 0, far ledges 1, soft top 0, severe 0 | identical |
| audit_mesh | CLEAN | CLEAN |
| kn5_ground_check | PASS (201 lamp heads, 0 orphans) | PASS (201, 0) |
| house_seat | PASS, 2,261 | PASS, 2,215 (floating 0, sunken 0, buried 0; lowest roof over its ground 1.26 m) |
| houses | 2,261 / 2,261 / 0 | **2,214 / 2,215 / 0** (the floor re-set: below) |
| textures | 0 untextured | 0 untextured |
| road kn5 / `_street` | 48.4 / 1.8 MB | **48.3 / 1.8 MB** |

**Roofs.** CO_DRCOG_2_2020 measured 2,319 of 2,321 footprints. After the planner:

| | count |
|---|---|
| heights from lidar | 2,256 |
| Microsoft | 1 |
| class default | 1 |
| left out: the lidar reads no roof 2.5 m over the ground (`lidar.drop_low`) | 63 |

The 63 are slabs, open sheds and structures gone since the footprints were drawn. 21 are houses. Microsoft had stood
some of them at 14-15 m: `osm_buildings532` was 15.4 m and the lidar reads 1.7 m.

Height changed by more than 0.5 m on 1,667 of 2,321 footprints (median +0.7 m; 699 up by more than 2 m, 150 down). The
largest:

| footprint | before | after |
|---|---|---|
| `osm_buildings1232`, industrial | 9.9 m (Microsoft) | **38.7 m** (lidar p50: a tall refinery-side block) |
| `msft_buildings2324`, "shed" (34 m²) | 2.8 m (default) | **19.7 m**: a tower |
| `osm_buildings1212`, shed | 2.8 m | 14.5 m |
| `osm_buildings532` | 15.4 m | 1.7 m (left out) |

**The 85 "past the class cap".** The cap is plan_buildings' `CAP_M` (shed 6, house 12, industrial 20, commercial 25,
apartments 35 m). It is [invented]: the shadow stage's ceiling on a NAIP shadow read, not a measurement.

| what the 85 were | count | what was done |
|---|---|---|
| no lidar height (top 0 or less) | 5 | not counted as past the cap |
| sheds and houses with p50 3-6 m under a p95 of 11-16 m | 79 | tree crowns over the roof: the ridge read was misread by trees. Stood at the median return, uncapped (`lidar.past_cap: "median"`) |
| industrial block at p50 38.7 m (p95 60.8 m) | 1 | real; stood at 38.7 m |

None of these is thrown away any more.

**Trees.** 5,171 of the 5,615 crowns were measured.
- 3,216 read a canopy 2 m or more over the ground: these take the lidar height.
- 1,955 read under 2 m. That is the existing [invented] floor of `LIDAR_TREE_H`; the p10 of 0.08 m is in this group. They
  are a lawn, a shrub or a shadow the colour rule took, so `lidar.drop_low` leaves them out.
  - Checked on NAIP over the Swansea blocks: 166 tall, 24 low. The low ones sit on bushes and bare yard, not crowns.
- 444 the lidar did not reach keep the ratio height.

Planned: 3,660 crowns (3,216 lidar + 444 ratio). The PC places **3,643** TreeFX trees: Oak3 2,357, SycamoreV2 880,
SycamoreV1 237, SycamoreV3 169. 15 are within 5 m of a road and 2 stand on a building. (0.2.0: 5,567.)

**The light: Lake Murray's sodium (Kevin, 2026-11-05).** Sand Creek's `lighting.streetlight` is now Lake Murray's block,
copied verbatim into Sand Creek's own config; Lake Murray's file is untouched. The written `[LIGHT_0]`:

| key | before | after |
|---|---|---|
| COLOR | 255, 217, 76, 0.35 | **255, 165, 30, 0.015** |
| SPOT | 155 | 150 |
| SPOT_SHARPNESS | 0.1 | 0.2 |
| RANGE | 60.0 | 25.0 |
| RANGE_GRADIENT_OFFSET | 0.55 | 0.5 |
| SPECULAR_MULT | 0.12 | 0.1 |
| FADE_AT | 1200 | 800 |

New lines after: DIFFUSE_CONCENTRATION 0.25, SINGLE_FREQUENCY 0.9, SHADOWS 1, SHADOWS_HALF_RESOLUTION 1,
SHADOWS_EXTRA_BLUR 1, VOLUMETRIC_LIGHT 0, LONG_SPECULAR 0.

The posts are the same `led_cobra` as Lake Murray's, so the values carry over as they are.

**The pads: measured, tried, and held out of 0.2.1.** Each outline was drawn on NAIP z18:

| pad | outline vs NAIP | built on the Mac |
|---|---|---|
| colorado_50th | covers the lap's corner and Colorado's throat | yes (try) |
| 50th_ash | good | yes (try) |
| 50th_dahlia | the corner; the arms are short | yes (try) |
| 48th_colorado | the corner; misses the east half of the crossroads | yes (try) |
| dahlia_56th | the junction, plus 1,406 m² of the lap's ribbon | refused: a lane sample at its in-cut row is off the deck |
| sandcreek_quebec | 0 road-intensity points; the outline is the box and the ribbon, and misses the junction's NE and S arms | parked (`lm_pads.parked`, with its reason): its edge is owed off NAIP |

Built with `lm_pads.close_arms: false`: no K-rail, the arms open. The four pads turned the lap **red**:
- soft top in lane 26;
- severe steps 24;
- kinks 11.9 /km;
- the seam between each pad's deck and the lap's rows: 0.21-0.34 m.

The lidar deck and the assembler's 3DEP road profile disagree by up to a third of a metre at the cuts. A 1 m DEM profile
smoothed along the line is not the measured surface at a crossroads.

So 0.2.1 ships with **no pad**. The declarations stay; `lm_pads` is not in the chain. With no pads, verify_mouths has no
pad mouth to read.

**House floor.** Lowered to the count built: 63 footprints are gone by measurement, not lost. `tools/house_gate.py` read
2,214 / 2,215 / 0 off the built kn5.

## Owed (2026-11-05, after 0.2.1; in Kevin's order)

1. **Pads that hold the lap.**
   - The deck must meet the lap's rows within the drive gates. The 0.21-0.34 m seam is the lidar deck against the 3DEP
     profile. Two ways:
     - the lap's own profile through each pad from the same lidar (the Lariat's C18 precedent);
     - the deck faded to the rows over a longer run.
   - Then dahlia_56th's in-cut lane sample, sandcreek_quebec's edge traced off NAIP, and 48th_colorado's east half.
   - Then verify_pads, taught lm_pads' no-curb shape.
   - The NAIP stills of all six outlines are in `source/stills/pad_*_naip.jpg`.
2. **Real junctions at all 146 street meetings** ("Real junctions"), on Lake Murray's weld / mouth / pad tools:
   - trim streets against streets;
   - one welded deck per meeting;
   - verify_mouths 11 → 0;
   - audit I/K 525 → only the real ones;
   - size: 70.6 MB in round B's scratch run.
3. **Round C:**
   - the race curbs and race closure;
   - Lake Murray's W1-6 arrows on the lap and both layouts;
   - street-name blades from OSM names, with MUTCD dimensions cited ("Both").
4. **The night stills** from the PC (runbook 4h step 5).

Earlier list, kept for the record:

- **The lidar job** (the PC, runbook 4g step 3): the roofs, the tree heights and the six pad outlines, in one job. Then the Mac
  re-plans, rebuilds 0.2.1 and sets the houses floor again.
- **The pad author with street arms** (round B item 4): lm_pads' deck, with every grid street at a pad welded to it instead
  of a K-rail across it. Then verify_pads on the no-curb pads. It waits on the PC's `source/pads/*.json`.
- **The grid streets into the chain** (round B item 3). It waits on Kevin's call on street-to-street meetings (127
  overlaps), then on the pads, which own 7 of the 11 failing mouths. The 4 others are owed regardless: 2 approaches that
  change grade too fast on the host's own deck, a host lane 0.43 m over the deck, and a notch.
- **Round C:** the race corridor and closures over the grid mouths; the race kerbs; street-name blades as a chain step.
- **`colliders 0`:** no block stands within 60 m of the lap on fine ground (as in 0.1.1).
