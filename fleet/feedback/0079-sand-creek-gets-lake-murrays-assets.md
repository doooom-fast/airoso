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

## Round D (Mac): 0.2.2, three pads on the lap, every gate green

Built on the Mac from an empty workshop (`tools/ship_track.sh`, ship.json as committed): SHIP OK.

### What the 0.21-0.34 m seam was (measured, before any change)

At the cut rows of the four pads tried in round C, against the PC's lidar deck (`source/pads/*.json`):
- **The lap's 3DEP profile agrees with the lidar.** The line's centre is within 0.07 m of the lidar deck at every cut
  (colorado_50th +0.02 / -0.02, 50th_ash -0.07 / -0.01, 50th_dahlia -0.01 / -0.03, 48th_colorado -0.03 / ...).
- **0.10 m of it is the engine's own datum.** The assembler stands every ROAD vertex 0.10 m over its sampled ground
  (scripts-v021 `build_loop_blend.py`: `y + 0.10`, "~0.1 m proud of the terrain"). The lidar deck had no such lift.
- **The rest is the crown.** The lap's rows are straight across (all three vertices one height); the measured road is
  crowned and cross-sloped, its edges 0.1-0.2 m under its centre (48th_colorado's left edge 0.20 m).
- So neither measurement is wrong at the cuts. The round-C fade length was not the cause of the red rows either.

### What turned round C red (measured on the built OBJ)

- **Holes in the deck read through to the removed ribbon.** The PC's deck is a 2 m plane per 0.5 m node over the
  road-intensity points only. Crosswalk paint, concrete gutter pans and cars leave 10-20 % of the nodes inside the
  outline empty (477-1,647 per pad). `lm_pads` read the lap's removed ribbon there (0.10-0.33 m over the lidar): the
  severe steps at 50th/Ash, 50th/Dahlia and 48th/Colorado.
- **Lidar noise.** The 2 m planes jitter 1-6 cm node to node (3-8 % of 1 m second differences over 3 cm inside the
  outlines): the kinks.

### The fix (all opt-in, `lm_pads.deck`; Sand Creek only)

- **`fill: "lidar"`** (`tools/draft_pads.deck_filled`): a hole inside the measured outline takes the plane through the
  lidar nodes around it (slope and crown carried across). Filled: 1,647 / 477 / 883 nodes, 0 unfilled.
- **`datum_m: 0.10`**: the deck in the lap's own datum (the assembler's lift above). Seam residual max 0.27 / 0.11 /
  0.14 m (round C: 0.34 / 0.21 / 0.24): the crown alone, faded in over round C's unchanged `SEAM_FADE_M` 12 m.
- **`smooth_m: 1.0`** [invented]: a Gaussian over the deck nodes inside the outline. It moves them p95 1.7-3.1 cm, max
  0.075-0.26 m (one node per pad standing off its neighbours: an object, not asphalt).
- **`lane_lip: "route.edge"`**: where the measured asphalt is narrower than the lap's lane, the deck also keeps the lane's
  0.3 m flat lip paved (the strip's curb_face_w + sidewalk_w). Round C's last soft top, 50th/Ash s 525 at +5.16 m.
- **`ground_edge_m: 0.7`** [invented] and **`strip_seam.pads`**: the ground under and round each deck split to 0.7 m
  and seamed along the deck's outline (LAWS L3b). The whole-terrain seam then missed 79 of 7,355 points (over its 1 %), so
  Sand Creek's strip seam moves to the local scope the Lariat runs: 7,132 of 7,136 joined.
- **I did not lengthen the fade and did not change the lap's profile.** The lap's profile through the pads is already the
  lidar's within 0.07 m. Its flat rows against the crowned road (the crown) are what remains at the seams.

### Per pad

| pad | 0.2.2 | why |
|---|---|---|
| colorado_50th | **built**, verify_pads PASS | deck 2,357 m²; it covers the lap's corner. Colorado's north arm and 50th's west arm stay outside the box (the streets' weld, item 2) |
| 50th_ash | **built**, PASS | 1,099 m² |
| 50th_dahlia | **built**, PASS | 1,301 m²; the arms are as measured (short): the box ends there |
| 48th_colorado | **parked** | drive_test green with it (0 soft, 0 severe), but verify_pads P4 red: grass 8-10 mm over the deck 0.19-0.24 m inside its south-east edge, where the prep's contact band takes the lap ribbon's height across the cut corner (unchanged by the outline seam). Also 5 of the 18 kinks with it are its seam (Colorado Blvd's crown, 0.20 m at the left edge). And the box misses the east half of the crossroads |
| dahlia_56th | **parked** (as before) | the lap's ribbon there is 30-42 m wide (56th's merge); at its in-cut row v770 / v771 the lane edges stand 0.1-0.7 m off the measured asphalt, so the lane check refuses it |
| sandcreek_quebec | **parked** (as before) | the lidar tile has no intensity (road median 0): the outline is the box and the ribbon. Its deck (class-2, all points) is there. The edge has to come off NAIP; no NAIP tracer exists yet |

Stills from above, NAIP beside the built road (the deck orange by height, the measured outline cyan):
`source/stills/pad_colorado_50th_built.jpg`, `pad_50th_ash_built.jpg`, `pad_50th_dahlia_built.jpg`.

### verify_pads on lm_pads' shape

`tools/verify_pads.py` reads `lm_pads`' record (`lm_pads_shape`); its rules and numbers are unchanged. The one rule
that reads less: P1 does not ask for a curb (Kevin: "no sidewalks"). It is written up in GATES-CHANGELOG. P7's
reference is the lap's 3DEP at the node. Lake Murray's J2-J4 record takes the old path (a test pins it). Sand Creek's
ship.json now gates on it.

### Gates, BUILT kn5 (Mac, empty workshop `/Volumes/Drive/codex/sclm_work/d6`)

| gate | 0.2.1 | **0.2.2** |
|---|---|---|
| drive_test race / street | PASS: soft 0, severe 0, drops 0, far ledges 1, fold bumps 4, kinks 0.41 /km, bumps 0.0 /km | PASS: soft 0, severe 0, drops 0, far ledges 1, fold bumps 4, **kinks 1.24 /km, bumps 0.31 /km**, vertex bumps 1 |
| audit_mesh | CLEAN | CLEAN |
| kn5_ground_check | PASS (201 lamp heads, 0 orphans) | PASS (199, 0: posts 6 and 7 stood on the colorado_50th deck, `drop_on_road`) |
| verify_pads | - | **PASS x3** (seams 0.9-1.6 mm, grass 0, curb over pavement 0, multi-coverage 0, node -0.10 to 0.00 m vs 3DEP) |
| verify_mouths | - | - (no street mouth yet) |
| house_seat | PASS, 2,215 | PASS, 2,215 (lowest roof over its ground 1.26 m) |
| houses | 2,214 / 2,215 / 0 | 2,214 / 2,215 / 0 |
| textures | 0 untextured | 0 untextured (36 meshes) |
| road kn5 / `_street` | 48.3 / 1.8 MB | **52.7 / 1.7 MB** (the 0.7 m ground under the decks) |

The kinks (12 on 9.64 km): 11 at 50th/Ash s 531-584, the lidar's own surface through the junction (they survive
smoothing to 2 m, so they are the road's shape, not noise); 1 at 50th/Dahlia s 1194. Kinks do not gate. 0.2.1 had 4,
at 50th/Dahlia's lane edge.

### The two questions from 0.2.1

- **The block without a roof.** There is none. `msft_buildings1333` (Microsoft) is a copy of `osm_buildings1169`: six
  shared corners, both tan tilt-up, 4.5 m. Both stand. Their roofs coincide and the gate's 1 mm weld counts them as one
  shell; their walls fall in two mesh chunks (TILTUP_0, TILTUP_1) and count twice. It is a real duplicate building, not
  a missing roof.
  - Four more OSM / Microsoft pairs stand twice as two different buildings in one place (8-12 shared corners): 912 /
    1210, 973 / 1839, 1043 / 106, 1094 / 96. Each is a flat tan tilt-up and a shingle hip house.
  - Owed: the planner's de-duplication. It changes the house floor, so it is a separate build.
- **15.4 m to 1.7 m.** `osm_buildings532` was never stood. The lidar reads its roof p50 1.73 m and p95 2.37 m over the
  ground (1,304 returns, a ~430 m² slab), under `lidar.drop_low`'s 2.5 m. It is in no `buildings.lm.json`. Round C's
  table says "(left out)"; the hand-back's "became a 1.7 m slab" was wrong.

### Lake Murray and the Lariat unchanged

- `git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/`: empty.
- Shared tools: every change is opt-in or a new function.
  - `draft_pads.deck_filled` is new.
  - `lm_pads` runs its old path when `lm_pads.deck` is absent (the Lariat's config names none of it): `edges0` is the
    same dict, lip 0, `ground_under` at 1.4 m.
  - `strip_seam`'s pad seam needs `strip_seam.pads`.
  - `verify_pads` takes the new path only on a record with `rows` and no `seams`.
- Tests: `test_sand_creek_lm_assets.py` 13 pass (three new: the fill, the opt-in keys, verify_pads' two shapes);
  `test_draft_pads`, `test_lm_engine_port`, `test_ship_track_chain` pass.

## Round E (Mac): the doubled buildings out (toward 0.2.3; not an install)

The coordinator, 2026-11-05: where an OSM and a Microsoft footprint stand in the same place, OSM wins, found by
measurement ("two buildings in one place aren't real").
- **The measurement.** `plan_buildings.py`'s de-duplication already dropped a later footprint whose centroid lies in an
  earlier one (1,113 Microsoft footprints here). New, opt-in (`buildings.plan.json` `dedupe.overlap` 0.5 [invented]):
  also a later source's footprint covering, or covered by, an earlier source's over half of the smaller one.
  - It finds **38** (45 at 0.25, 35 at 0.8), the five named in round D among them (msft 1333 / osm 1169, 1210 / 912,
    1839 / 973, 106 / 1043, 96 / 1094).
  - Planned 2,258 -> 2,221 footprints; stood 2,215 -> **2,181**.
  - Without the key the planner writes the committed `buildings.lm.json` byte for byte (`cmp`).
- **The build** (Mac, empty workshop `sclm_work/d7`, then the gates re-judged with the new floor): SHIP OK.
  - Every gate as 0.2.2: drive_test both PASS (soft 0, severe 0, drops 0, kinks 1.24 /km), audit CLEAN,
    kn5_ground_check PASS, verify_pads PASS x3, textures 0 untextured.
  - houses **2,181 / 2,181 / 0**: roofs and blocks now equal. The floor is lowered to it, written in GATES-CHANGELOG as a
    weakening.
- Runbook 4i now pins the 0.2.2 install to f6dd8a63; round E ships with 0.2.3.

## Runbook 4i (PC, 2026-11-05): 0.2.2 installed on Kevin's word

- **Rehearsal** (`sand_creek_lm_d_reh`, empty, f6dd8a63, ENG `eng_sclm_a`, the four `.bin` in place): every row the
  runbook lists, as listed. Decks 1647 / 477 / 883 filled, verify_pads PASS x3 (seams 0.9-1.6 mm, grass 0, curb over
  pavement 0), 2,215 buildings stood / 43 dropped, 3,643 TreeFX trees, drive_test both PASS (kinks 1.24 /km), audit
  CLEAN, houses 2,214 / 2,215 / 0, road kn5 52.7 MB.
- **Kevin, 2026-11-05: "Yes, both"** (this and the Rangely renames). The 0.2.0 workshop moved aside to
  `D:/k10-scratch/sand_creek_lm.0.2.0`; the install ran from a fresh empty `D:/k10-scratch/sand_creek_lm` (no `SHIP_PROJ`,
  no `--no-install`). Rows equal the rehearsal's, SHIP OK. The installed 0.2.0 folder is parked in
  `D:/k10-track-archive/2026-11-05_112252/`. Installed: "doooom Colorado — Sand Creek Raceway (LM engine)" and
  "... Sand Creek Free Roam (LM engine)", 0.2.2. All four kn5s are byte-identical to the build; TreeFX trees are in
  `extension/trees/` (the four personal-use `.bin`, not committed).
- **The sync-back** is `4d607c5` on its own branch `claude/sand-creek-lm-0202-installed`, parented on f6dd8a63: on top
  of round E it would put 0.2.2's `house_gate.json`, `house_seat_check.json`, `pads.built.json`, `split_manifest.json`,
  `street_kn5.json` and `loop.blend` over round E's, so it is not merged here (the Mac's call). `treefx.report.json` is
  the only record with news: 3,643 trees (2,357 Oak3, 880 SycamoreV2, 237 SycamoreV1, 169 SycamoreV3; 2 rejected on a
  building) where the Mac's has 0.
- **Not done: step 5's pad stills.** Kevin did not pick them. The 4h night "before" stills can now only come from the
  parked 0.2.0.

## Round F (Mac): the street-to-street junctions, trimmed; the build stops at the weld (NOT 0.2.3, not an install)

0.2.2 (f6dd8a63) stays the build of record. This round commits the junction code and turns the streets on in
Sand Creek's config and chain, but no build of it has passed: the chain stops at `weld_mouths` on two forks (below).

### What is committed

- **`tools/trim_connectors.py`, opt-in `route.street_junctions`** (Lake Murray and the Lariat name none of it):
  - **JOIN.** OSM splits a street at every node, so one street arrives as pieces that end at one node. Pieces whose
    directions continue there (turn <= `join_turn_deg` 45) are joined into one piece; two pieces alone at a node that
    bend (turn <= `bend_turn_deg` 135) are joined too; a sharper pair is a fork and stays two pieces. The joined piece
    takes the higher-class / longer member's name and lists the members in `joined`. The two ends' heights are averaged
    and each side's profile is shifted onto the mean, faded over trim's own `BLEND_M` 30 m. This removes the 0.43 m step
    round B found on Quebec (grid_primary_30 ends 0.43 m over grid_primary_6's start: `grid_unclassified_27`'s failing
    mouth).
  - **RANK.** Where two pieces meet that no earlier pass cut (two arterials, then two minors), the through piece hosts and
    the other is cut at its pavement edge with a mouth: the ribbon-through topology every mouth here uses, cut by the
    existing `_trim_against`. A piece that ends on another's interior ranks below it; otherwise OSM's hierarchy, then the
    wider, then the longer. Pieces are cut in rank order, each against the final pieces of the higher-ranked pieces it
    meets, so no host is cut after a mouth is recorded on it.
  - **No reach from a cut end.** An end that is already a mouth's cut is never REACH-extended on to the next host.
    Round B's pass 2 stretched `grid_primary_49`, cut at the lap, 14 m on to `grid_primary_52`'s centre.
  - **Acute mouths.** A fork's mouth record carries `extend_max_m` (twice (half width + strip) / tan(angle) where that passes
    25 m). `tools/mouth_weld.py` / `weld_mouths_blend.py` read it as a keyword; absent = `EXTEND_MAX_M`, as before.
  - **Pad arms (`street_junctions.pad_arms`, written, NOT on in the config).** `cut_at_pads` cuts every street entering a
    built pad's box at the box edge and writes `data/pad_arms.json`; the lm_pads side that welds those end rows into
    the deck is not written yet (Owed 1b). A scratch trim found 6 arm ends: colorado_50th `grid_unclassified_9`,
    `grid_unclassified_10`, `grid_primary_51` (now in joined `grid_primary_15`), `grid_primary_53` (in `grid_primary_33`),
    `grid_unclassified_76`; 50th_ash `grid_unclassified_17`. 50th_dahlia's two declared arms never enter its box.
- **Sand Creek:** `lm_intake.connectors` true; `route.connector_hosts` (`grid_primary*`, `grid_secondary*`);
  `route.street_junctions`. ship.json draft: lm_intake, build_loop_blend, **trim_connectors, rebuild_loop_blend**,
  weld_mouths, seat_terrain, densify_ribbon, seat_edges, lm_pads, strip_seam, **gap_mouths**, lamps; gate **verify_mouths**
  after verify_pads; sync_out the mouths, connectors and `street_junctions.json`.
- `GATES-CHANGELOG` 2026-11-05 round F: the four numbers the junctions need, three [invented]. No gate moved.

### The 146 meetings after trim (Mac, workshop `sclm_work/j1`; scratch check on the trim's output)

- 32 nodes joined (30 straight, 2 bends): 106 pieces -> 89 after every cut.
- 127 mouths: 36 on the lap, 91 street-to-street or street-to-arterial (round B: 52).
- Of grid_meetings' 146, each is now a join, a mouth or both. The scratch check finds no two final pieces overlapping
  except:
  - two false positives at the end caps of mouths that are correct. Quebec x `grid_tertiary_65` is one.
  - the forks, where an acute weld overlaps by design.
- **Quebec's median at the `grid_unclassified_27` / `grid_tertiary_65` crossing (1656, 789).** Quebec is two carriageway
  ribbons 13.5 m apart. The cross street ends at each one with a mouth, and the 4 m between them stays grass; NAIP shows
  it paved. The 4 m piece would be under trim's `MIN_PIECE_M` 15 m and dropped. Owed (1c).

### Where the build stops: the forks

OSM draws four short paint-divided approaches as two one-way pieces leaving one node at 13-24 deg. On NAIP each is one
asphalt with a painted chevron median: `grid_tertiary_91` / `92` at (42, -752), `grid_unclassified_94` / `95` at
(847, -764). There is also a Y: `grid_tertiary_5` off `grid_tertiary_20` / `grid_unclassified_13` at (899, -292). And
a lens: `grid_tertiary_74` / `75`, 148 m long.
- Welded with the long reach: `grid_tertiary_5` (18.6 deg) and `grid_tertiary_74` at both ends (24 deg). Road cut arcs run
  +-12 m along the host edge; verify_mouths has not judged them yet.
- `grid_unclassified_94` (16.4 deg) fails the weld's self-check: 3 of its vertices stand 0.026-0.036 m over the host deck
  inside its pavement (`SELF_TOL_M` 0.02). Its blend onto the host (30 m smoothstep) leaves the overlapping rows off the
  host's level-across deck. `grid_tertiary_91` (13.3 deg) is next in line.

## Round G (Mac): the forks as one street, the acute welds held, the pad arms, Quebec's crossing (toward 0.2.3)

The coordinator's calls under "I just want real" (2026-11-05), each built as decided. All code opt-in; Lake Murray and the
Lariat name none of the keys (a test pins it).

### What is committed

- **The paint-divided forks: one street each** (`tools/trim_connectors.py merge_forks`, `route.street_junctions.merge_forks`).
  The two one-way OSM pieces are replaced, before JOIN, by one piece whose edges were **measured off NAIP**: cross-sections
  every 5 m from the fork node, sampled 0.5 m apart (each sample the mean over 1 m along the street); an edge is where the
  asphalt meets the first concrete band 1.5 m or wider (`edges_m` in the config, about +-0.5 m). The centre is the edges'
  middle, the width their distance; heights the two pieces' mean. Then JOIN makes each one street with the piece north
  of its node.
  - `grid_tertiary_91` / `92` -> `grid_tertiary_92` (joined with `grid_tertiary_36`): 14.0 m at the node to 24.5 m at s 75.
  - `grid_unclassified_94` / `95` -> `grid_unclassified_95` (joined with `grid_unclassified_62`): 13.5-14.5 m to s 55,
    15.5 m at s 60-65, 18-19 m at s 70-75.
  - **The median is not built.** Lake Murray's `divide_connectors` only makes a raised island from an out-and-back loop,
    so none is drawn. Missing: the yellow chevron paint (91/92 s 20-55; 94/95 s 15-75): no chain step paints a chevron
    median on a grid street (Lake Murray's hatched median is `tools/expansion_pieces.py`, authored pieces only).
  - **Measured, not as decided:** 91/92 is not paint all the way. From about s 57 to the lap crosswalk a 3.5-4 m band
    as bright as the sidewalks stands at +1 to +5 m off the midline: a raised concrete island. Not built (paved over).
  - Trim then cuts each merged street once at the lap: 127 -> 123 mouths before the other changes; the two fork
    overlaps are gone from the scratch check.
- **The acute welds held on the host deck** (`tools/mouth_weld.weld_end(hold_overlap=True)`, the mouth key
  `weld_hold: "overlap"`, written by trim on the acute mouths only, `route.street_junctions.weld_hold`). Every row up to
  the guest's furthest mitre (the length its ribbon overlaps the host) lies on the host deck, level across its edge; the
  30 m ease back to the guest's own profile starts only past it. Before, the ease ran from each line's own mitre, which
  left the overlapping rows off the host's deck (round F: `grid_unclassified_94`). No number added. Applies to the Y
  `grid_tertiary_5` (18.6 deg) and the lens `grid_tertiary_74` at both ends (24 deg).
- **The pad arms** (`lm_pads.arms: "streets"`, `route.street_junctions.pad_arms` on). 6 arm ends at colorado_50th (5)
  and 50th_ash (1); 50th_dahlia's declared arms never enter its box. In `tools/lm_pads_blend.py`:
  - each arm's end row (read through `mw.mesh_layout(pts3, connectors)`) is spliced into the outline along its box edge
    (`draft_pads.splice_rows`, `c` = `sealed_cut(box edge)`, `cr` = `row_cut(row)`), pinned as a seam;
  - its departure from the lidar is faded in with seam_profile's own rule, up to 45 % of the way to the node, and past
    the row's ends over the same length. Where fades overlap the rows share it (`draft_pads.seam_offset_multi`: exact on
    every row, `seam_offset` where only one reaches);
  - only the lap's own faces between the cuts are deleted: a face also has to lie within the lap's half width + its
    `route.edge` strip (0.1 + 0.2 + 1.5 m) of the lap line;
  - pads.built.json `rows` carries the arm rows after the two lap rows, `arm_rows` naming them; `verify_pads` reads them
    as seams `arm_<piece>_<end>`.
- **Quebec's median crossing** (`tools/trim_connectors.py median_crossings`, `route.street_junctions.median_crossings`).
  - **OSM has no piece across the median at all**: `grid_unclassified_27` ends at the west carriageway's node
    (1649.2, 789.4) and `grid_tertiary_65` starts at the east one's (1662.7, 789.4). So round F's "4 m piece dropped
    under 15 m" was not the mechanism.
  - The crossing is added node to node (13.5 m). Its own `min_piece_m` 0 keeps the 4.8 m left after both carriageways
    cut it; `MIN_PIECE_M` is unchanged for every other piece.
  - Both mouths are welded. Each end's weld eases over the piece's whole length with no extra re-spread
    (`weld_blend_m` = its length, `weld_remap_min_m` 0), so the two smoothsteps sum to one: every row lies between the
    two decks, each end on its own.
  - Width 10.0 m [rule]: `grid_tertiary_65`'s own, the wider of the two streets it joins.
- **Measured for Kevin, not built: Quebec's whole median.** The strip between Quebec's two OSM carriageway ribbons
  (`grid_primary_6` / `7`: 4-6 m, narrowing to 1-2.5 m south) reads asphalt or concrete on NAIP at 48 of 49 samples along
  860 m. It is never planted (one dark sample). Around the 27 / 65 crossing NAIP shows one road about 31 m curb to
  curb, divided by paint only. The cross street's approach is about 15 m wide, centred about 4 m south of OSM's line.
  So the build's grass strip down Quebec's middle is not real either: the carriageways' OSM widths are short.
- Tests: `test_sand_creek_lm_assets.py` 20 pass (five new: the fork merge, the crossing kept and welded at both ends,
  the acute hold, seam_offset_multi, the keys opt-in); `test_draft_pads`, `test_lm_engine_port`, `test_mouth_weld*`,
  `test_ship_track_chain`, `test_trim_connectors` pass. Lake Murray's committed trim inputs through fleet-lm-engine's
  trim and this branch's: byte-identical (`664da93b…`, `b73b70f4…`, `f0c97952…`).

### The builds (Mac, empty workshops `sclm_work/k2`, `k3`, `k4`): NOT 0.2.3, verify_mouths red

0.2.2 (f6dd8a63) stays the build of record. Each build fixed what the one before it found.
- **k2** stopped at verify_pads.
  - P3 holes at four arm row ends.
  - 50th_dahlia's two streets (`grid_unclassified_0`, `grid_tertiary_44`) end ON its box edge in the grid's own data (2-4 mm
    off it). Trim had stretched them on to the lap, so they stood under the deck (P2 128.5 m², P4, P5).
  - The arm seams faded 12 m and added 3 kinks to the lap at 50th/Ash (1.56 /km).
- Fixed in `lm_pads_blend` / `trim_connectors` (all inside the opt-in paths):
  - **An arm short of the measured asphalt.** colorado_50th's lidar outline stops 3-8 m short of the box edge at
    `grid_unclassified_10` and `_76`. The street's own ribbon to the measured ring is united in (`union_arms`, on
    `union_ribbon`'s grid and numbers), and the arm row is its splice line.
  - **Arm row lines** are drawn over the row's own span. At 30 m, `grid_primary_15`'s row line took
    `grid_unclassified_10`'s row end out of the outline.
  - **The deck corner beside each arm row is square** (`arm_edges`: `ribbon_edges` for a street, walked at the outline's
    own 0.75 m step).
  - **A street that ends on a box edge is an arm as it stands** (cut_at_pads; "on" = splice_rows' own 0.05 m).
  - **Lap faces are found by the assembler's layout index** (ROAD / CURB), the lateral test kept for the paint. The lap
    face counts are then exactly 0.2.2's: 92/264, 88/264, 88/264.
  - **An arm's seam fade stays off the lap's lane:** it ends at the lane edge (kinks back to 1.24 /km).
- **k3:** verify_pads still read a hole at three arm row ends. Each is a sample landing exactly ON the row's end vertex:
  an 8.00 m street's half row is 4.000 m, a multiple of the 0.25 m step. There the street side is its own 1KERB lip at
  the same height. `verify_pads` now samples strictly inside each segment (1 mm; GATES-CHANGELOG, a weakening): PASS x3.
  - verify_mouths then failed at the Quebec crossing: a 0.24 m step one row in. Trim's two 30 m blends (one per end)
    overwrote each other. The crossing's profile is now the straight line between its two cuts.
- **k4** (head of this round): every gate as below. verify_mouths is red at 8 mouths outside the parked pads.

| gate | 0.2.2 (d6) | round E (d7) | **round G (k4)** |
|---|---|---|---|
| drive_test race / street | PASS: soft 0, severe 0, drops 0, kinks 1.24 /km, bumps 0.31 /km, far ledges 1, fold bumps 4 | as 0.2.2 | **PASS / PASS: soft 0, severe 0, drops 0, kinks 1.24 /km, bumps 0.31 /km, far ledges 1, fold bumps 4** |
| audit_mesh | CLEAN | CLEAN | **CLEAN (I 0, K 0)** |
| kn5_ground_check | PASS (199 heads, 0 orphans) | PASS | **PASS (198 heads, 0 orphans; 172 lamps)** |
| verify_pads | PASS x3 | PASS x3 | **PASS x3** (seams 0.9-1.6 mm, multi-coverage 0, grass 0, curb 0; 8 arm rows in) |
| verify_mouths | - | - | **FAIL: 11 of 117** (3 at parked pads, 8 others, below) |
| house_seat | PASS | PASS | PASS (lowest roof 1.26 m) |
| houses (roofs / blocks / colliders) | 2,214 / 2,215 / 0 | 2,181 / 2,181 / 0 | **2,168 / 2,168 / 0: FAIL against the 2,181 floor** (below) |
| textures | 0 untextured | 0 | 0 untextured |
| kn5 | road 52.7, `_street` 1.7 MB | | **road 82.7, `_street` 6.5, spawn 0.002 x2 MB: 89.2 MB** (under 120) |

**verify_mouths (k4), the 11 failing of 117:**
- At parked pads (allowed): `grid_primary_52` (48th_colorado: HOST LANE grass, NOTCH); `grid_primary_78` (sandcreek_quebec:
  APPROACH 4.8 %/m); `grid_primary_80` (sandcreek_quebec: MOUTH LINE / HOST LANE / NOTCH up to 0.07 m).
  `grid_primary_49` and `grid_tertiary_98` pass.
- The 8 others:
  - `grid_tertiary_5#0#0` (end) -> MAINLINE: APPROACH 3.9 %/m.
  - `grid_unclassified_67#0` -> MAINLINE: APPROACH 3.1 %/m.
  - `grid_primary_84#0#0` -> `grid_primary_78#0` (arterial / arterial): APPROACH 8.6 %/m, 2 grass samples at the road.
  - `grid_tertiary_5#0#0` (start) -> `grid_tertiary_2#0` (the Y, 18.7 deg, held): NOTCH 15 / 109 samples with no road
    7.6-8.1 m along the host edge.
  - `grid_tertiary_74#0` (start) -> `grid_tertiary_1#1` (the lens, 24 deg, held): HOST LANE 185 samples with road / curb
    0.02-0.038 m over the host deck. Its other end passes.
  - `grid_unclassified_10#0#0` / `#0#1` -> `grid_tertiary_16#0#0` (a crossroads, 70 / 77 deg): MOUTH LINE / NOTCH up to
    0.07 m, HOST LANE 0.084 m.
  - `grid_residential_29#2` -> `grid_residential_22` (26.6 deg, not held: its reach is under 25 m): HOST LANE 3 samples at
    0.021 m (limit 0.02).
- Passing: the two forks' lap mouths, the Quebec crossing's two mouths, the lens's other end, and every other
  street-to-street mouth.
- Round B's list was "verify_mouths 11 -> 0 apart from the parked pads"; here 8 remain. They are owed (below).

**houses 2,168 (13 fewer than round E), measured.** The planner, footprints and floor are unchanged. The 13 blocks round E
stood and k4 drops (`[bespoke]`: within BUILDING_CLEAR_M of a road or wall) sit against the streets now built. Each
footprint against the nearest street ribbon (connector centreline +- half width):
- **INTO the ribbon: 5.**
  - `osm_buildings219`: 1.3 m into `grid_primary_11`.
  - `osm_buildings763`: 1.1 m into `grid_primary_11`.
  - `msft_buildings1341`: 0.7 m into `grid_residential_34`.
  - `osm_buildings206`: 0.2 m into `grid_primary_11`.
  - `osm_buildings316`: 0.1 m into `grid_secondary_39`.
- **0.8-1.2 m off the edge, inside the street's 1.8 m strip: 3.** `osm_buildings115`, `_691`, `_127`.
- **3.2-4.7 m off: 4.** `msft_buildings1214`, `_1565`, `osm_buildings399`, `_793`.
- **Not explained: 1.** `osm_buildings1182`, 23.8 m from any street.

A building on a real street is not real, but a 0.1-1.3 m overlap is also within OSM's street widths, which round G found
short at the forks and on Quebec. **The floor is NOT moved here** (Kevin / the coordinator: lower it to 2,168 on this
evidence, or measure those streets' widths first).

Stills, NAIP 2023 beside the BUILT k4 road (`source/stills/`):
- `junction_fork_92_k4.jpg`: the fork as one street.
- `junction_y_t5_k4.jpg`: the Y.
- `junction_minor_x_47_29_k4.jpg`: minor / minor.
- `junction_arterial_84_78_k4.jpg`: arterial / arterial.
- `pad_colorado_50th_arms_k4.jpg`: the pad with its five arms.
- `junction_quebec_crossing_k4.jpg`: Quebec's crossing.

Lake Murray unchanged:
- `git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/` is empty.
- Its trim inputs through both trims are byte-identical.
- Tests: 99 pass.

## Round H (Mac): the 8 mouths and the 13 houses, measured; 0.2.3 green (NOT installed)

The coordinator's calls under "I just want real" (2026-11-05): every fix from measurement, all opt-in for Sand Creek. The
Mac now reads the lidar too (CO_DRCOG_2_2020 EPT through laspy[lazrs] in a scratch venv; the repo's own fetch code).
Workshop `sclm_work/h2` (empty, this head's code but the docs): **every gate green**.

### Found on the way: round G's NAIP measures sat in a frame 0.44 % (north) / 0.14 % (east) off
Round G's NAIP helpers (scratch, not committed) turned local metres into lon/lat with 111,320 x cos(lat) / 110,540 m per
degree; the track's frame is `scripts.geometry.projection`'s WGS84 series (85,659 / 111,032 m here). At Quebec (789 m
north, 1,650 m east) that is 3.5 m north and 2.3 m east. So:
- "the cross street centred about 4 m south of OSM's line" (round G) was the frame: in the right frame 48th's west leg is
  centred 0.6 m south of OSM's line (`source/stills/quebec_48th_h.jpg`).
- Fork 94/95's `edges_m` (x about 849) sit about 1.2 m east of where they were meant, both edges the same way (the width
  stands). 91/92 (x about 45) moves 0.06 m. Not re-measured this round (owed below).
Every round H measure uses the track's own frame (`tools/lidar_connector_profile.py`; the scratch NAIP / lidar helpers).

### The 8 mouths: all PASS (verify_mouths: 117 mouths, only the parked pads' fail)
- **`grid_tertiary_5#0#0` at the lap (3.9 %/m): a bridge the grid could not hold.** The lidar has the street crossing
  Sand Creek on a 60 m deck (class 17 at 22.2-22.3 m, 833-893 m from the Y); the 3DEP grid (40 m, read at 20 m) dropped it
  5.0 m into the creek bed, and began the drop 7 m from the lap (13 % down: the 3.9 %/m). Measured ground beside the lap:
  22.73 at the mouth, 22.25 at 27 m, flat. Built on the lidar's surface: approach 0.38 %/m.
- **`grid_unclassified_67#0` at the lap (3.1 %/m): the weld, not the ground.** Lidar - 3DEP -0.03..+0.43 m along the
  street, a smooth 0.6 m fall over 45 m. The fault was the weld: its warp eased each vertex toward the host deck read at
  that vertex's own projection onto the lap, and 15-20 m out the projection jumped to the lap's other leg round the 48th /
  Colorado corner (lap vertex 3199 -> 3213, 0.34 m lower): a 0.1 m dip across the wheel line. `mouth_weld.weld_end
  (runon_at_mitre)`: past each lateral line's mitre the ease starts from the deck AT that mitre (on the host's pavement it
  reads where the vertex is, as before). Opt-in `route.street_junctions.weld_runon "mitre"`, every Sand Creek mouth. Plus
  the lidar profile. Approach now 0.43 %/m.
- **`grid_primary_84#0#0` -> `grid_primary_78#0` (8.6 %/m, 2 grass samples): the interstate bridge.** Both carriageways
  climb onto a deck (class 17 at 29.3 m); the grid held 78 up to 4.25 m low at its start and 84 dipped 1.3 m where the
  real road climbs 5 %. Measured: 84 rises 24.2 -> 29.3 m over 120 m, 78 falls 29.6 -> 24.6 m. On the lidar both:
  approach 0.95 %/m, no grass.
  - The real ground nowhere changes grade faster than 3 %/m on these three (no flattening, no limit moved).
- **The Y (`t5` at `t2`, 18.7 deg): the host's width stepped 1 m at the node.** The host there is two OSM ways joined:
  `grid_tertiary_20` (10 m) into the node, `grid_unclassified_13` (8 m) out of it. The guest's end row is a 13 m chord at
  18.7 deg; with the edge stepping 1 m at the node it ran 0.14 m OUTSIDE the host edge, and the ground showed through
  (the 15 NOTCH samples, a 0.1 m sliver over 5.5 m). NAIP + lidar sections at x 945, 960, 975, 1010, 1040 read
  `grid_unclassified_13` 10-12 m curb to curb, not 8. Built at 10.0 m (the measured lower bound; `lm_intake.
  connector_widths`). The Y is then one paved surface (`source/stills/junction_y_t5_h.jpg`). Lake Murray's mouth fill
  was tried first (k* = 1, 15 m2): its self-check refused a 2.9 % film triangle beside 0.7 % seams (+2 % [invented]), and
  it was not kept.
- **The lens `t74`, the crossroads `u10` at `t16`, `r29#2`: the guest now lies on the host's own triangles.** Lake
  Murray's `route.weld_exact_deck` (ledger 0054 P1) for `grid_tertiary_74`, `grid_unclassified_10#0`,
  `grid_residential_29`: the weld reads the host deck off the host's triangles. At the crossroads the host is not level
  across, and that is real: lidar across `grid_tertiary_16` 20 m from `grid_primary_33` falls 0.11 m over 9 m (built
  0.09 m: its own mouth's weld leans it onto 33's grade). verify_mouths read that host edge against its centre extended
  level, so the host's OWN sheet was 5-6 cm "off itself". New opt-in `route.weld_exact_deck_lines` (Sand Creek only):
  MOUTH LINE / NOTCH on an exact-deck mouth read the host's lowest road sheet on the mouth line at that station. No
  tolerance moved (GATES-CHANGELOG). Results: lens HOST LANE 0.0 m (was 0.038), crossroads mouth line 0.004 / 0.002, notch 0.001 / 0.002
  (was 0.065-0.084), `r29#2` HOST LANE 0.0 m, notch 0.027 (was 0.021 over).
- Parked pads (allowed, not worked): `grid_primary_52` (HOST LANE 1 grass sample), `grid_primary_80` (as round G).
  `grid_primary_78` at sandcreek_quebec now PASSES (on the lidar its approach is 2.33 %/m, was 4.77).
- **The parked-pad allowance** (a BYPASS, GATES-CHANGELOG): `route.verify_mouths_allowed` names the three mouths one
  by one; each is still measured and its row still FAILs, the gate does not. Without it the chain stopped at
  verify_mouths before house_seat / houses / textures and before any install (round G's k4 too).

### The 13 houses round G lost: 12 stand, 1 measured and still out (houses 2,182 / 2,182 / 0 against the 2,181 floor)
Each footprint against the BUILT k4 road (1ROAD and the 1.8 m 1KERB edge strip, plan distance from the ring):
| block | k4 rule | to ROAD edge | to the 1KERB strip | outcome |
|---|---|---|---|---|
| msft_buildings1214 | 2.4 m from a road | 2.41 m | 0.61 m | stands |
| msft_buildings1341 | clearance | 2.70 | 0.90 | stands |
| msft_buildings1565 | clearance | 2.59 | 0.79 | stands |
| osm_buildings115 | 2.5 m from a road | 3.07 | 1.27 | stands |
| osm_buildings127 | 2.9 m from a road | 4.38 | 2.58 | stands |
| osm_buildings206 | 2.6 m from a road | 3.74 | 1.94 | stands |
| osm_buildings219 | clearance | 2.52 | 0.72 | stands |
| osm_buildings399 | clearance | 4.34 | 2.54 | stands |
| osm_buildings691 | clearance | 4.04 | 2.24 | stands |
| osm_buildings763 | clearance | 2.23 | 0.43 | stands |
| osm_buildings793 | clearance | 3.70 | 1.90 | stands |
| osm_buildings316 | on a road or kerb | 1.07 | 0.00 (touches) | stands |
| osm_buildings1182 | relief 3.16 m (limit 2.64) | 26.5 | 24.7 | **still dropped** |
- **The clearance rule** (`author_bespoke_blend` BUILDING_CLEAR_M 3.0 m [invented], "a wall this close to a road would
  stand in the run-off") is a circuit's rule; measured as a 3D distance from 1 m over the ground it dropped houses 2.2-4.4 m
  from the ROAD edge. Opt-in blocks key `building_clear_m` (Sand Creek 0): a footprint ON the pavement still drops.
  It also stands round E's two clearance drops, `osm_buildings17` and `osm_buildings20` (1.5 / 1.1 m from a road).
- **316** (a 20,359 m2 warehouse) touched the 1KERB strip beside `grid_secondary_39`. Lidar section at x 250: the
  frontage road's low surface ends 3-8 m short of the wall (the strip between rises 0.4-0.8 m to the loading apron);
  NAIP: the wall's shadow band. Sand Creek's names.paved is now ROAD / 1ROAD only (no sidewalks here; the CURB object is
  the curb face and the 1.5 m [invented] graded band).
- **1182 is real and still out.** A 46 x 9.5 m, 1.7 m-tall structure (lidar: 2,208 roof returns, class 1 all along it;
  NAIP has a no-data stripe over it). Its own ground is flat (lidar 26.4-26.8 m; `lidar_roofs.json` ground 1,598.82 m).
  Round G's terrain beside `grid_primary_49` stands as a 20 m plateau at the street's 31.3 m and then one 28 m facet down
  through the footprint (built ground under the rim 26.35-29.51 m; round E's 26.35-27.46). The real thing there is a
  retaining wall: lidar ground 27.5 m at x -1562, 31.8 m at x -1560. A rule fix would not be real: the ground is wrong.
  Owed: the wall (lidar) or a finer verge, below.
- house_seat PASS (lowest roof 1.26 m), textures 0 untextured.

### Not built this round (measured; the next round's leads)
- **Fork 91/92's island.** Lidar across the merged street at z -800 .. -836 (x 31-61): from the west gutter (27.45 m) the
  carriageway crowns at 27.88 m (x 43-45), falls to 27.67 m at x 50; the NAIP concrete band is x 50.5-54.5 (4 m at
  z -824), rising 27.72 -> 27.87 m across it; the top 27.93 m at x 55, then down 0.44 m in 2.5 m to the east carriageway
  (27.38-27.45 m). So it stands over both sides (0.05-0.2 m over the west gutter, 0.4 m over the east), as a raised
  island. Built: not yet. `divide_connectors` / `author_median_blend` make a GRASS-topped island centred on the trunk with
  shrubs, at heights from the trunk's own pre-weld points; this one is concrete, off-centre (+3 m) and inside the lap
  mouth's 30 m weld, so it needs an island authored on the welded road (heights read off ROAD) with a concrete deck.
- **Quebec.** Lidar + NAIP sections at z 680, 720, 760, 840, 880, 940 (`xs` every 0.5 m, x 1634-1682): west curb about
  x 1645.5, east curb about x 1677 (31-32 m); a RAISED median (about +0.1 m on 0.5 m bins, NAIP concrete-bright) at
  x 1657.5-1664 (3.5-6 m wide; 0.5-12 m wide at 880-940 where turn bays open). It is NOT OSM's gap: OSM's two
  carriageway centres are x 1649.5 / 1662.9 (9.5 m each), so the real median lies 2-6 m east of the strip between the
  ribbons, inside OSM's east carriageway. Real carriageways: west about 12 m (1645.5-1657.5), east about 13-16 m. Not built:
  it needs the two carriageways re-centred on measured edges over 860 m (merge_forks' edges_m, per station) and the
  raised median of the measured width, through the 48th crossing. The cross street (48th) reads about 15 m (OSM 8 / 10).

### Gates, BUILT kn5 (Mac, empty workshop `sclm_work/h2`)
| gate | 0.2.2 (d6) | round G (k4) | **round H (h2)** |
|---|---|---|---|
| drive_test race / street | PASS: soft 0, severe 0, drops 0, kinks 1.24 /km | PASS, same | **PASS / PASS: soft 0, severe 0, drops 0 (1 far ledge), kinks 1.24 /km, bumps 0.31 /km, fold bumps 4** |
| audit_mesh | CLEAN | CLEAN | **CLEAN** |
| kn5_ground_check | PASS (199 heads) | PASS (198 heads, 172 lamps) | **PASS (198 heads, 0 orphans, 172 lamps)** |
| verify_pads | PASS x3 | PASS x3 | **PASS x3 (seams 0.9-1.6 mm, multi-coverage 0, grass 0, curb 0)** |
| verify_mouths | - | FAIL 11 / 117 | **PASS: 117 mouths; `grid_primary_52`, `grid_primary_80` (parked pads) FAIL in their rows, allowed** |
| house_seat | PASS | PASS | **PASS (lowest roof 1.26 m)** |
| houses | 2,214 / 2,215 / 0 | 2,168 / 2,168 / 0 FAIL | **2,182 / 2,182 / 0 PASS (floor 2,181)** |
| textures | 0 | 0 | **0 untextured** |
| kn5 | road 52.7 MB | 89.2 MB | **road 87.0, `_street` 6.8, spawn 0.002 x2: 93.8 MB** |
h2 was built before the allowance: its chain stopped at verify_mouths on the two parked-pad mouths, as k4's did. With
the allowance committed, verify_mouths, house_seat, houses and textures were re-run on h2 (`--from treefx`: every gate).

Stills, NAIP 2023 (track frame) beside the BUILT h2 surface, `source/stills/`: `mouth_bridge_t5_lap_h`,
`mouth_u67_lap_h`, `mouth_p84_p78_bridge_h`, `junction_y_t5_h`, `junction_lens_t74_h`, `junction_crossroads_u10_t16_h`,
`junction_r29_r22_h`, `quebec_48th_h` and `fork_92_island_h` (both as built, unchanged: not built this round).

Lake Murray unchanged: `git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/` is empty; its
committed trim inputs through fleet-lm-engine's trim and this branch's: byte-identical (`664da93b…`, `b73b70f4…`,
`f0c97952…`). Tests: `tests/run_tests.py` with `python` on PATH: 1,297 pass, 6 fail in files and tools this round does not touch
(`test_draft_equiv` x5, `test_registry_moves` x1; without `python` on PATH 5 more fail: `ship_track.sh` calls `python`).
3 new: the run-on, the keys opt-in, the profile intake.

## Round I (Mac): 0.2.4 green on the Mac (i2; NOT installed): fork 94/95 re-measured, the 91/92 island, 1182 standing

Round H's leads, built from measurement, all opt-in for Sand Creek. Every NAIP read this round goes through the track's own
frame (`scripts.geometry.projection._meters_per_degree`, the WGS84 series: 85,659.2 m per degree east, 111,030.5 m north
here); round G's scratch NAIP helpers (111,320 x cos(lat) / 110,540 m) are retired, and the round I helpers assert the
track frame on import.

### 1. Fork 94/95, re-measured in the track frame (config)
- The same cross-sections as round G (every 5 m from the fork node, samples 0.5 m apart from -16 to +16 m along the
  midline's normal, each the mean over 1 m along). The edge by rule: half-way to the first run of 3 samples (1.5 m) at
  NAIP gray >= 165, at least 4 m from the midline (1 m bright bands inside are the chevron paint). In round G's frame the
  rule gives round G's own reads at 12 of 15 stations (the other 3 within 0.5-1 m); 165 is fitted to them [invented].
- In the track frame both edges move +1.0 .. +1.5 m along the normal (east), as round H predicted (about 1.2 m): west
  edge -5.25 .. -7.25 m, east +8.25 .. +10.75 m; 13.5-15.0 m wide to s 65, 15.5 at s 70, 18.0 at s 75 (the flare). s 10's
  east edge has no concrete run (a car or driveway on the gutter): interpolated between s 5 and 15.
- 91/92 moves 0.06 m in the right frame (round H): kept.

### 2. Fork 91/92's concrete island, built as measured (`route.islands`, `tools/author_islands_blend.py`)
- **Measured again before building, row by row** (NAIP 2023 in the track frame, every 0.5 m; lidar class 2):
  - the outline: the bright run (gray >= 185) covering x 53, x 50.88 .. 53.62-54.62, from the north nose at z -811.0 to
    the crosswalk's stop bar at -838.0 (3.75 m wide from z -817; rows -835.0 / -835.5, broken by a shadow,
    interpolated). Through the crosswalk the refuge is cut flush, and the nose south of it (z -843 .. -847) lies past
    the mouth line on the lap's own deck: neither built.
  - the heights: the lidar median 0.25-1.25 m inside minus outside each edge, +-0.5 m along, 53 rows. **West edge
    +0.078 m** (range +0.024 .. +0.216: the spread is the lidar's, the curb one height, the median taken). **East edge
    -0.047 m** (-0.19 .. +0.05): the island is at or under the northbound lane beside it, which rises east (0.4 m over
    the 20 m street) where the built road is level across. Built flush there (0).
  - **Round H's "0.4 m over the east carriageway" does not hold along the island**: that was its one section, z -824,
    the one row where the east lane dips. Along the island the east side is flush.
- **The step** (new, opt-in `route.islands`, draft step `islands` after `gap_mouths`): each row's two edge points read
  the welded ROAD's top (a ray down through it), and the deck stands `rise_m` over it. The faces are the deck, the west
  curb face and the two end faces, in one object `1KERB_sidewalk_island_fork_92`. The prep keeps the AC name, binds the
  1KERB_SIDEWALK concrete and lays planar UVs. Physics KERB. No grass, no shrubs, no barrier.
  - Self-checks: no ROAD under an edge, under 2 rows, or a deck under the road.
  - i1 read-back: 55 rows over 27.6 m, 0.74-4.00 m wide, rise 0.078 / 0.000 m, 0.0 mm off the road it was read from.
- **Gates on i1** (empty workshop, items 1-2): every one as h2's. drive_test race / street PASS (soft 0, severe 0, drops
  0, 1 far ledge, kinks 1.24 /km, bumps 0.31 /km, fold bumps 4); audit CLEAN (K kerb in carriageway 0); kn5_ground_check
  PASS (198 heads, 0 orphans); verify_pads PASS x3; verify_mouths PASS (117 mouths); house_seat PASS (lowest roof
  1.26 m); houses 2,182 / 2,182 / 0; textures 0 untextured; kn5 93.9 MB.
- Fork 94/95 in i1: `[trim] fork ... -> one street grid_unclassified_95: 81.8 m, width 13.5-18.0 m (measured edges)`.

### 5. Building 1182 stands: the ground beside grid_primary_49 seated on the lidar (`terrain.lidar_patches`)
- **Measured** (lidar class 2, 1 m profiles every 5 m along z): a retaining wall beside grid_primary_49, a 2.1-4.5 m step
  within 3 m. Its line runs from x -1574.5 at z -865 to -1552.5 at -1000, and on past -1045, nearer the street. It is 4.3-4.5 m
  tall at 1182 (z -920 .. -945). Low side 27.2-27.6 m, high side 31.5-32.1 m.
  - The built ground (h2) held the street's 31.3 m for 20 m past the wall (to x -1572), then fell one facet to 27.3 m at
    x -1592, through 1182's footprint (x -1588.7 .. -1579.2).
- **The engine has no retaining-wall path for a street's verge.** `tools/lidar_wall.py` measures a wall at a lap's lane
  edge; Pikes Peak builds its wall from K-rail modules. So the wall stands as the terrain step the lidar shows.
- **Two new opt-in tools:**
  - `tools/lidar_ground_patch.py` measures the polygon's ground. The lattice is 1 m: each node is the median of the
    class-2 returns within 1 m (at least 3). 2,449 nodes under roofs are filled from their neighbours, the ground under
    a roof read from the ground around it. Output: `source/ground_patches.lidar.json`.
  - `tools/ground_patch_blend.py` is draft step `ground_patch`, after `islands`. It cuts TERRAIN's edges in the patch's
    box to <= 1.5 m, then seats every vertex inside the polygon on the lattice.
    - Outside the polygon it eases the built height toward the lidar over `feather_m` 10 [invented], past every edge
      except the wall's own line (`hard_edges`: there the step IS the ground).
  - The polygon: the wall's line (the step's middle) from z -862 to -1000, and x -1620 on the west. There the built and
    the real ground agree within 0.1 m.
- **i2:** `[ground-patch] wall_49: TERRAIN 517000 -> 555933 vertices, 28953 seated on the lidar ground (7032 in the
  feather), largest move 4.74 m`.
  - `osm_buildings1182` stands: ground 26.38-26.83 m (the lidar's 26.4-26.8), eave 29.47 m.
  - Houses 2,183 / 2,183 / 0 against the 2,181 floor. Drops: 36 relief, 2 past 450 m.
- **Not patched:** the wall south of z -1000. It comes within 2-7 m of the street there, in the street's verge (seat_terrain
  / the prep's contact band).
- **Gates on i2** (empty workshop, items 1, 2, 5), the same as i1 and h2:
  - drive_test race / street PASS: soft 0, severe 0, drops 0 (1 far ledge), kinks 1.24 /km, bumps 0.31 /km, fold
    bumps 4;
  - audit CLEAN; kn5_ground_check PASS (198 heads, 0 orphans); verify_pads PASS x3 (seams 0.9-1.6 mm); verify_mouths
    PASS (117);
  - house_seat PASS (lowest roof 1.26 m); textures 0 untextured; kn5 96.2 MB (road 89.4, `_street` 6.8).

### 4. The rest of the streets on the lidar: measured, NOT wired (one mouth)
- **Measured:** `tools/lidar_connector_profile.py` on all 102 streets still on 3DEP, against 353 lidar tiles on the Mac.
- **A street under a bridge was lifted onto it.** The median of ground and deck returns within 1 m puts a street that
  passes UNDER an overpass onto the deck above it:
  - grid_primary_73 and 71, grid_tertiary_99 / 101 / 103, grid_secondary_102 and grid_primary_80 rose 6-7.4 m over 3 m;
  - grid_primary_73 at x 1655, z -907 .. -889: ground 28.2-29.0 m, deck 35.5-35.8 m.
- **New opt-in `--surface`:**
  - Where a point has a deck 2 m [invented] or more over its ground, or a deck alone, the road is the chain of readings
    with the least height change between neighbours. A deck the street climbs onto is reached by its ramps; an overhead
    deck is not.
  - An unread point (ground hidden under the deck) is allowed only under a deck 2 m or more over the chain, at
    0.3 m [invented] per point. It is filled as before, from the 3DEP offset of its neighbours.
  - Round H's four streets read the same to the millimetre (the two bridges stay on their decks). A test pins both
    cases.
- **Held on 3DEP:** a street whose profile still jumps more than 0.5 m [invented; 3DEP's own largest is 0.56 m] between
  two neighbouring points (3 m apart). That is 6 streets: grid_secondary_8 (1.38 m), grid_primary_11 (1.35),
  grid_secondary_39 (2.61), grid_secondary_42 (0.74), grid_primary_71 (1.25), grid_unclassified_77 (3.23). Each is a
  point or two at a ditch, wall or curb within the 1 m radius. Owed: look at those points.
- **Moved: 96 streets** (100 with round H's four). Relative to 3DEP:
  - 68 move more than 0.25 m somewhere, 33 more than 0.5 m, 13 more than 1 m, 5 more than 2 m.
  - The largest:
    - grid_primary_15: -0.39 .. +7.91 m (108 points on a deck);
    - grid_primary_87 / 88: +1.07 .. +5.71 / +1.97 .. +4.76 (decks);
    - grid_primary_33: +2.56; grid_primary_64: +2.15; grid_primary_49: +1.97; grid_primary_66: +1.38;
      grid_primary_73: +1.31; grid_unclassified_0 / 56: -1.11.
  - The median street moves 0.00 m on average.
- **Builds i3 / i5 (every gate up to verify_mouths):**
  - drive_test race / street PASS: severe 0, kinks 1.24 /km, bumps 0.31 /km;
  - audit CLEAN; kn5_ground_check PASS (198 heads); verify_pads PASS x3.
  - **verify_mouths FAILs one mouth:** grid_tertiary_1#1 start on grid_tertiary_2#0. HOST LANE has a road sheet
    0.021 m over the host deck (LANE_TOL 0.02 m) and 2 grass samples 4 mm under it, 7 m along the host, past the span.
  - Two tries:
    - i4 read that mouth's host deck exact (`route.weld_exact_deck`): no change;
    - i5 put grid_tertiary_1 back on 3DEP: no change. So it is the host grid_tertiary_2 on the lidar.
  - No tolerance was moved.
- **So the 100 streets are parked** beside the chain's file: `source/connector_profiles.lidar.round_i.json`, whose
  `_doc` says how to wire it. The chain keeps round H's four (i2, green).
  - Next: hold grid_tertiary_2 on 3DEP (or mend that weld), point `lm_intake.connector_profiles` at the round I file,
    and build.

### 3. Quebec at its measured edges: NOT built (measured further; the lead below)
- A NAIP + lidar scan along grid_primary_6 / 7 (the 860 m south of 48th), every 60 m, -25 .. +25 m off the southbound
  ribbon, 0.5 m samples, in the track frame. Script: `quebec_scan.py` in round I's scratch.
- What it shows:
  - the bright bands are not one clean structure: lane lines, the median's concrete, turn-bay paint, the east slip lane
    and its island at 48th, driveways and parking aprons;
  - the lidar's class-2 surface rises 0.1-0.2 m toward the northbound side over most stations, a crossfall (no lone
    median step).
- Re-centring both carriageways and building the median needs a per-station tracer: a lidar curb step plus a NAIP edge,
  checked against these sections. A brightness rule like fork 94/95's picks lane paint here. Not built; owed.
- 48th: not changed, about 15 m (round H).
- `sandcreek_quebec` stays parked. Its lidar tile has no intensity, and `tools/draft_pad_outline.py`'s aerial (NAIP)
  source still raises "not built yet": the NAIP tracer is the same missing piece.

### 6. Parked pads `48th_colorado` and `dahlia_56th`: re-measured on the Mac; both still parked
- `tools/draft_pad_outline.py` was run on the Mac's lidar reader, in a scratch project with h2's line, each pad moved
  into `lm_pads.pads`.
- Both outputs are the committed `source/pads/*.json` (the PC's, da370cab) byte for byte, except the `written`
  timestamp:
  - 48th_colorado: 299 outline points, 2,247 m², 27,465 ground points;
  - dahlia_56th: 330 points, 3,098 m².
- The measurement was never the fault. Round D's reasons are construction:
  - 48th_colorado: verify_pads P4 grass 8-10 mm over the deck where the prep's contact band takes the lap ribbon's
    height across the cut corner, and the box misses the crossroads' east half;
  - dahlia_56th: the lap's ribbon is 30-42 m wide at 56th's merge, and its lane edges stand 0.1-0.7 m off the measured
    asphalt at the in-cut row.
- Neither is unparked. `route.verify_mouths_allowed` keeps its three rows: grid_primary_52 for 48th_colorado,
  grid_primary_78 / 80 for sandcreek_quebec.

### 7. Fork 94/95's chevrons and Quebec's divider: owed (no paint path to extend)
- `route.lane_dividers` is one switch inside Lake Murray's assembler. It is in
  `tracks/san-diego-lake-murray/scripts-v021/blender/build_loop_blend.py`: `max_lanes_side 0` on the MAINLINE's markings
  when false.
- Extending it to grid streets means editing that file, and Lake Murray's tree must not change. Lake Murray's hatched
  median is `expansion_pieces.py`, which paints authored pieces only.
- A Sand Creek paint step on a street's built road (as the island step reads it) is the lead.

### Gates, BUILT kn5 (Mac, empty workshop `sclm_work/i2`: this head; items 1, 2, 5)
| gate | 0.2.3 (h2) | **round I (i2)** |
|---|---|---|
| drive_test race / street | PASS: soft 0, severe 0, drops 0 (1 far ledge), kinks 1.24 /km, bumps 0.31 /km, fold bumps 4 | **PASS / PASS, the same** |
| audit_mesh | CLEAN | **CLEAN (K kerb in carriageway 0, with the island)** |
| kn5_ground_check | PASS (198 heads, 0 orphans) | **PASS (198 heads, 0 orphans)** |
| verify_pads | PASS x3 (seams 0.9-1.6 mm) | **PASS x3 (seams 0.9-1.6 mm)** |
| verify_mouths | PASS: 117, 2 parked-pad rows allowed | **PASS: 117, the same 2 allowed** |
| house_seat | PASS (lowest roof 1.26 m) | **PASS (1.26 m)** |
| houses | 2,182 / 2,182 / 0 | **2,183 / 2,183 / 0 (1182 stands; floor 2,181)** |
| textures | 0 untextured | **0 untextured** |
| kn5 | 93.8 MB (road 87.0, `_street` 6.8) | **96.2 MB (road 89.4, `_street` 6.8)** |

Stills, NAIP 2023 (track frame) beside the BUILT i2 surface, `source/stills/`:
- `fork_92_island_i`: the island (white) where NAIP has it;
- `h1182_wall_i`: the stepped ground and 1182's ground;
- `fork_95_i`: 94/95 on its re-measured edges.
- Quebec and the parked pads: not built, no still.

Lake Murray unchanged:
- `git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/` is empty.
- Its committed trim inputs through fleet-lm-engine's trim and this head's: byte-identical (`664da93b…`, `b73b70f4…`,
  `f0c97952…`).
- `test_round_i_keys_are_opt_in`: neither Lake Murray nor the Lariat names `route.islands`, `terrain.lidar_patches(_file)`,
  or the `islands` / `ground_patch` steps.

Tests: `tests/run_tests.py` (the .venv python, `python` on PATH): 1,301 pass. 6 fail, the same as round H's
(`test_draft_equiv` x5, `test_registry_moves` x1). 4 new: the round I keys, the island / patch declarations, the patch's
polygon test, the `--surface` chain.

## Round J (Mac): 0.2.5 green on the Mac (rj2; NOT installed): 99 streets on the lidar, the south wall, a NAIP tracer measured

Round I's leads under "just want real", all opt-in for Sand Creek. Workshops `sclm_work/rj1`, `rj2` (EMPTY, fresh names:
j1-k4 already existed from earlier rounds). Items 1 and 4 built; item 2's tracer written and measured on Quebec, not
built; items 3 and 5 not reached (owed, below).

### 1. The streets on the lidar: wired (99 streets), the mouth mended at its cause
- **The cause, measured on i3's OBJ and loop.blend** (not the host's profile itself): the extra sheet over
  grid_tertiary_2's lane, 7 m along from grid_tertiary_1#1's mouth, is **grid_tertiary_74#0's first rows** (ROAD
  vertices 31329-31334, CURB 81881). 74#0 meets grid_tertiary_1#1 at 24 deg at its v1, and #1 starts on
  grid_tertiary_2#0: 74's first rows lie past #1's open end, on grid_tertiary_2's pavement. The weld read "the host deck"
  there as #1's end row held level (18.026 m), while grid_tertiary_2's measured deck under them falls (18.015 -> 18.005
  m over 1 m): road 0.021 m over the host lane, and the terrain seated 0.02 m under that sheet (the 2 grass samples at
  -4 mm). On 3DEP (i2) the same sheet existed, but grid_tertiary_2 rose there, so it lay 9 mm under.
- **The fix** (opt-in `route.weld_deck_beyond_end`, piece prefixes; `mouth_weld.BeyondEndDeck`, used by
  `tools/weld_mouths_blend.py`): past the host's OPEN end, on a street that end is welded to, the weld reads that street's
  deck (its triangles) where the point lies; everywhere else as before. No number added. Sand Creek names
  `grid_tertiary_74#0`. rj1/rj2: `[weld] grid_tertiary_74 -> grid_tertiary_1#1 v1: past the host's open end, 19 point(s)
  read the deck of the street it is welded to`.
  - verify_mouths, the mouth: grid_tertiary_1#1 start on grid_tertiary_2#0 PASS (host lane above 0.0 m, grass max
    -0.020 m, 0 grass samples); 74#0's two mouths PASS (grass max -0.016 / -0.018 m). LANE_TOL not moved; tertiary_2
    stays on the lidar.
- **Wired:** `lm_intake.connector_profiles` -> `source/connector_profiles.lidar.round_i.json` (and in ship.json
  sync_in). Held on 3DEP, with reasons in the file's `_doc`:
  - round I's 6 jumpy streets (grid_secondary_8, grid_primary_11, grid_secondary_39, grid_secondary_42, grid_primary_71,
    grid_unclassified_77): profiles jump > 0.5 m [invented] between neighbouring points; their jump points still owed;
  - **grid_primary_15 (new):** rj1 (all 100) lost two houses, `osm_buildings766` and `msft_buildings2147` (houses
    2,181 < 2,183). Measured: its lidar profile is a VIADUCT's deck (class 17, ~8 m wide, from z ~500 to ~1000, up to
    7.9 m over 3DEP) with the ground at 9-11 m right up to both sides of the deck (1 m cells every 4 m across, z 810-925).
    The build has no street-bridge path, so the assembler's terrain band (22 m) raised an 8 m embankment beside the deck,
    and the two houses 15-40 m off sat on its toe (relief over the limit). Held on 3DEP until a street bridge exists.
- **rj2:** `[lm_intake] connector heights off the lidar (source/connector_profiles.lidar.round_i.json)`: 99 streets
  plus round H's four read as before; houses 2,183. Gates below.

### 4. The retaining wall south of z -1000: on the lidar ground (`terrain.lidar_patches` wall_49 extended)
- Measured (as round I's wall scan: class 2, 1 m profiles every 5 m along z): the wall runs on from x -1552.5 at z -1000
  to -1545.5 at -1075, a 2.1-2.4 m step (low 30.5-33.9 m, high 33.2-36.1 m). South of -1075 the ground climbs onto an
  embankment and a bridge abutment (4-10 m steps, decks): not a wall, not patched.
- **No street weld in the way:** grid_primary_49 ends at z -953 in the build (round I's "within 2-7 m of the street" is
  the real road east of the wall: NAIP shows a 4-lane road at x ~ -1530 .. -1515 that the build does not carry south of
  -953; still `wall_49_south_j`). The built ground (i2) held the step as a 10 m slope, 0.3-0.6 m under the lidar on both
  sides.
- The polygon: the wall's line on to (-1545.5, -1075), hard edges 1-34 (the step IS the ground), the south edge at
  -1075 and x -1620 west soft (feather 10 m [invented, round I]). Re-measured with `tools/lidar_ground_patch.py`: 96 x
  234 nodes, 17,516 read, 4,149 filled under roofs; every node round I's lattice shares reads the same (13,566 of 13,566).
- rj2: `[ground-patch] wall_49: TERRAIN 516981 -> 574373 vertices, 42509 seated on the lidar ground (8241 in the 10 m
  feather), largest move 5.10 m`. Houses 2,183 / 2,183 / 0 (1182 still stands).

### 2. A NAIP edge tracer: written, measured on Quebec; Quebec NOT re-centred, `sandcreek_quebec` still parked
- `tools/naip_edge.py` (new, no build step): `Naip` reads the 2023 NAIP mosaic at local metres through the track frame
  (the WGS84 series, as round I's helpers), vectorised; `road_runs` / `trace_section` take one cross-section (NAIP gray +
  lidar class-2 medians) and return the carriageway run at a seed with each edge classed `curb` (a lidar step >= 0.08 m
  within 1 m, within 1 m of the NAIP edge), `flush` (bright concrete past it, no step) or `no_step`. Its numbers are
  [invented] (GATES-CHANGELOG round J). The NAIP file in the repo is a Git LFS pointer on the Mac; the tool says so and
  takes the image's path.
- **Measured on grid_primary_6 (Quebec southbound), 44 stations every 20 m** (sections +-25 m, 0.5 m, lidar +-1.5 m
  along; the corridor's NAIP histogram puts asphalt at 150-195, verge under 140):
  - **a raised median, measured:** the median-side edge is a curb at +10.0 .. +11.0 m off the OSM line with a +0.08 ..
    +0.16 m step at 10 stations, s 140-460;
  - the outer edge does not hold: a curb at -3 .. -10 m at 9 stations, otherwise `no_step` / `flush` (driveways,
    aprons, the slip lane);
  - the road run is 4-41 m wide: on most stations north of s 480 it runs across both carriageways (the median reads
    road-gray in NAIP there), and at s 0-120 / 620 the OSM line sits on the median (the seed is not on asphalt).
  - So a brightness run plus a curb step separates the median's curb but not the outer edge; re-centring both
    carriageways from it would place edges on paint, aprons and the other carriageway. Not built. 48th unchanged (~15 m).
- `sandcreek_quebec`'s outline needs the same separation (a NAIP mask also takes the concrete median and aprons). Not
  traced; the pad stays parked, `route.verify_mouths_allowed` keeps its three rows.
- Lead: the lidar's own curb line, traced along (a continuous step line, not per-station), with NAIP only to tell asphalt
  from concrete; the 0.3 m NAIP crop (`tools/naip_crop.py` on `claude/circuit-kerbs-lm`) for the paint.

### 3, 5. Not reached this round
- The parked pads (`48th_colorado`: the prep's contact band at its cut corner; `dahlia_56th`: the 30-42 m lap ribbon's
  lane edges at v770/v771) and the paint step (fork 94/95's chevrons; Quebec's divider is a raised median at s 140-460,
  so not paint there): unchanged, owed (round I's reasons stand).

### Gates, BUILT kn5 (Mac, empty workshop `sclm_work/rj2`: this head; items 1, 4)
| gate | 0.2.4 (i2) | **round J (rj2)** |
|---|---|---|
| drive_test race / street | PASS: soft 0, severe 0, drops 0 (1 far ledge), kinks 1.24 /km, bumps 0.31 /km, fold bumps 4 | **PASS / PASS, the same (vertex bumps 1, reported)** |
| audit_mesh | CLEAN (K 0) | **CLEAN (K 0)** |
| kn5_ground_check | PASS (198 heads, 0 orphans) | **PASS (198 heads, 0 orphans)** |
| verify_pads | PASS x3 (seams 0.9-1.6 mm) | **PASS x3 (seams 0.9-1.6 mm)** |
| verify_mouths | PASS: 117, 2 parked-pad rows allowed | **PASS: 117, the same rows allowed; grid_tertiary_1#1 PASS** |
| house_seat | PASS (lowest roof 1.26 m) | **PASS (1.26 m)** |
| houses | 2,183 / 2,183 / 0 | **2,183 / 2,183 / 0** |
| textures | 0 untextured | **0 untextured** |
| kn5 | 96.2 MB (road 89.4, `_street` 6.8) | **96.4 MB (road 89.6, `_street` 6.8)** |

rj1 (item 1 with all 100 streets, before the wall): every gate as rj2 but houses 2,181 (the viaduct, above).

Stills, NAIP 2023 (track frame) beside the BUILT rj2 surface, `source/stills/`:
- `mouth_t1_t2_j`: grid_tertiary_1 across grid_tertiary_2 with 74 joining, on the lidar;
- `wall_49_south_j`: the patched ground west of the wall, z -975 .. -1085 (the unbuilt road east of it in NAIP).

Lake Murray unchanged:
- `git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray scripts/` is empty.
- Its committed trim inputs through fleet-lm-engine's trim and this head's: byte-identical (`664da93b…`, `b73b70f4…`,
  `f0c97952…`).
- `test_round_j_keys_are_opt_in`: neither Lake Murray nor the Lariat names `route.weld_deck_beyond_end` or the round I
  profile file. The weld's change is a no-op without the key (BeyondEndDeck is built only for a named piece).

Tests: `tests/run_tests.py` (the .venv python, `python` on PATH): 1,304 pass. 6 fail, the same as round I's
(`test_draft_equiv` x5, `test_registry_moves` x1). 3 new: the round J keys, BeyondEndDeck, the NAIP road runs.

## PC runbooks (round H)

4j. **Sand Creek 0.2.3** (ledger 0079 rounds E-H). This build carries:
   - the 106 grid streets welded into the lap, each other and three pads (rounds F-G), forks merged, Quebec's crossing;
   - four streets on the lidar's surface (two bridges), `grid_unclassified_13` at its measured 10 m, the run-on weld;
   - 2,182 houses (rounds E and H);
   - verify_mouths in the gate list, the two parked-pad mouths allowed by name (`route.verify_mouths_allowed`).

   It installs as `sand_creek_raceway_lm` 0.2.3, replacing 0.2.2. **Ask Kevin before installing.**
   1. `git -C D:/k10-worktrees/sclm-assets fetch` and check out this round's head of `claude/sand-creek-lm-assets`.
   2. Inputs, the same as step 4i: the four TreeFX `.bin` in `tracks/sand-creek/source/trees/`, ENG = the same plain copy
      of `eng_repro`, the 12 asset md5s of 4g, `source/pads/*.json` da370cab's. New and committed:
      `tracks/sand-creek-lm/source/connector_profiles.lidar.json` (the lidar job need not run).
   3. Rehearse from an EMPTY workshop:
      `SHIP_PROJ=D:/k10-scratch/sand_creek_lm_h_reh AIROSO=D:/k10-worktrees/sclm-assets ENG=D:/k10-scratch/eng_sclm_a bash tools/ship_track.sh sand-creek-lm --no-install`
      Expect the Mac's h2:
      - `[lm_intake] connector heights off the lidar ...: grid_tertiary_5 (-0.22..+5.02 m), grid_unclassified_67
        (-0.03..+0.43 m), grid_primary_78 (-1.37..+4.25 m), grid_primary_84 (-1.29..+2.02 m)` and `connector widths
        measured: {'grid_unclassified_13': 10.0}`;
      - lm-pads decks filled 1647 / 477 / 883, unfilled 0; `[strip-seam] 3 pad outline(s), 636 points`, local scope 2 missed;
      - `[lamps] drop_on_road: 3 draft post(s)` and 172 lamps;
      - `[bespoke] ... 2182 buildings stood, 39 dropped (2 of them past 450 m)`, drop reasons 37 relief;
      - drive_test both PASS: soft 0, severe 0, drops 0, far ledges 1, fold bumps 4, kinks 1.24 /km, bumps 0.31 /km;
      - audit CLEAN; kn5_ground_check PASS (198 heads, 0 orphans); verify_pads PASS x3 (seams 0.9-1.6 mm);
      - verify_mouths PASS: 117 mouths, `grid_primary_52#0` and `grid_primary_80#0` FAIL in their rows (ALLOWED);
      - house_seat PASS (lowest roof 1.26 m), houses 2,182 / 2,182 / 0, textures 0 untextured;
      - road kn5 87.0 MB, `_street` 6.8 MB; the PC plants TreeFX (the Mac has no `.bin`).
      Anything else, stop and send the log to the Mac.
   4. Install, with Kevin's word: the same command without `SHIP_PROJ` and `--no-install`. AC closed.
   5. Stills, from the car, CSP daylight, into `tracks/sand-creek-lm/source/stills/<name>_drive_0.2.3.jpg`: the t5 bridge
      off the lap (s 6,180 m of the race layout or wherever the lap passes 1,753 / -373), the Y (910 / -296), the
      interstate bridge ramps (1,864 / -389).

4k. **Shared tools A/B: Lake Murray and the Lariat rebuilt with this branch's tools** (no install). This branch changed
   tools both other tracks run: `draft_pads`, `lm_pads_blend`, `strip_seam_blend`, `verify_pads`, `plan_buildings`,
   `trim_connectors`, `mouth_weld`, `weld_mouths_blend` (rounds C-G), `seat_terrain_blend`, `author_lamps_blend`,
   `lm_engine_intake`, `ship_track.sh` (round B), and round H's `mouth_weld` (run-on), `weld_mouths_blend`,
   `trim_connectors`, `verify_mouths` (exact lines), `lm_engine_intake` (profiles, widths), `author_bespoke_blend`
   (building_clear_m). Every change is behind a key neither track names (`test_round_*_keys_are_opt_in`).
   1. Two worktrees: `D:/k10-worktrees/ab-origin` at `origin/claude/fleet-lm-engine`, `D:/k10-worktrees/ab-branch` at this
      head. ENG: one plain copy of `eng_repro` each (never the live engine-july).
   2. For each of `san-diego-lake-murray` and `lookout-lariat`, from EMPTY workshops:
      `SHIP_PROJ=D:/k10-scratch/ab_<track>_<side> AIROSO=D:/k10-worktrees/ab-<side> ENG=<its copy> bash tools/ship_track.sh <track> --no-install`
      (side = origin / branch), each log to a file.
   3. Compare: every gate row the same; `md5sum` of each workshop's `build/*.kn5`, `data/connectors.local.json`,
      `data/mouths.json`, `data/mouth_welds.json`, `data/pads.built.json` (where present) the same. The Mac's check
      (trim only, Lake Murray): byte-identical, 664da93b / b73b70f4 / f0c97952.
   4. Anything different: stop, send both logs and the differing file names to the Mac.

4l. **Sand Creek 0.2.4** (ledger 0079 round I). This build carries 0.2.3 (4j) plus:
   - fork 94/95 on its edges re-measured in the track frame;
   - fork 91/92's concrete island (`1KERB_sidewalk_island_fork_92`);
   - the ground beside grid_primary_49 on the lidar, its retaining wall as the measured step, and `osm_buildings1182`
     standing (2,183 houses).

   It installs as `sand_creek_raceway_lm` 0.2.4, replacing 0.2.3. **Ask Kevin before installing.**
   1. `git -C D:/k10-worktrees/sclm-assets fetch` and check out this round's head of `claude/sand-creek-lm-assets`.
   2. Inputs, the same as step 4j. New and committed: `tracks/sand-creek-lm/source/ground_patches.lidar.json` (the
      patch's lattice; the lidar job need not run). `source/connector_profiles.lidar.round_i.json` is NOT wired: leave it.
   3. Rehearse from an EMPTY workshop:
      `SHIP_PROJ=D:/k10-scratch/sand_creek_lm_i_reh AIROSO=D:/k10-worktrees/sclm-assets ENG=D:/k10-scratch/eng_sclm_a bash tools/ship_track.sh sand-creek-lm --no-install`
      Expect the Mac's i2:
      - 4j's lines (`[lm_intake]` the same four streets off the lidar, `connector widths measured: {'grid_unclassified_13': 10.0}`;
        lm-pads; `[lamps] drop_on_road`, 172 lamps), and
        `[trim] fork ['grid_unclassified_94', 'grid_unclassified_95'] -> one street grid_unclassified_95: 81.8 m, width 13.5-18.0 m`;
      - `[islands] 1KERB_sidewalk_island_fork_92: 55 rows over 27.6 m, 0.74-4.00 m wide, rise 0.078 / 0.000 m ...
        read-back 0.0 mm`;
      - `[ground-patch] wall_49: TERRAIN 517000 -> 555933 vertices ..., 28953 seated on the lidar ground (7032 in the
        10 m feather), largest move 4.74 m`;
      - `[bespoke] ... 2183 buildings stood, 38 dropped (2 of them past 450 m)`, drop reasons 36 relief;
      - drive_test both PASS: soft 0, severe 0, drops 0, far ledges 1, fold bumps 4, kinks 1.24 /km, bumps 0.31 /km;
      - audit CLEAN (K 0); kn5_ground_check PASS (198 heads, 0 orphans); verify_pads PASS x3 (seams 0.9-1.6 mm);
      - verify_mouths PASS: 117 mouths, `grid_primary_52#0` and `grid_primary_80#0` FAIL in their rows (ALLOWED);
      - house_seat PASS (lowest roof 1.26 m), houses 2,183 / 2,183 / 0, textures 0 untextured;
      - road kn5 89.4 MB, `_street` 6.8 MB.
      Anything else, stop and send the log to the Mac.
   4. Install, with Kevin's word: the same command without `SHIP_PROJ` and `--no-install`. AC closed.
   5. Stills, from the car, CSP daylight, into `tracks/sand-creek-lm/source/stills/<name>_drive_0.2.4.jpg`:
      - the island from 91/92's southbound lanes (52 / -826);
      - 1182 and the wall from grid_primary_49 (-1575 / -940).
   - 4k (the shared-tools A/B) also covers this round's tools: `ship_track.sh` gained two steps neither track lists, and
     `lidar_connector_profile.py` gained `--surface` (off by default).

4m. **Sand Creek 0.2.5** (ledger 0079 round J). This build carries 0.2.4 (4l) plus:
   - 99 more streets on their measured (lidar) profiles, grid_tertiary_74's first rows read off grid_tertiary_2's deck
     (`route.weld_deck_beyond_end`);
   - the ground west of grid_primary_49's wall on the lidar on south to z -1075.

   It installs as `sand_creek_raceway_lm` 0.2.5, replacing 0.2.4. **Ask Kevin before installing.**
   1. `git -C D:/k10-worktrees/sclm-assets fetch` and check out this round's head of `claude/sand-creek-lm-assets`.
   2. Inputs, the same as step 4l. Now WIRED and committed: `tracks/sand-creek-lm/source/connector_profiles.lidar.round_i.json`
      (ship.json syncs it in); `source/ground_patches.lidar.json` re-measured (the lidar jobs need not run).
   3. Rehearse from an EMPTY workshop:
      `SHIP_PROJ=D:/k10-scratch/sand_creek_lm_j_reh AIROSO=D:/k10-worktrees/sclm-assets ENG=D:/k10-scratch/eng_sclm_a bash tools/ship_track.sh sand-creek-lm --no-install`
      Expect the Mac's rj2:
      - 4l's lines, except: `[lm_intake] connector heights off the lidar (source/connector_profiles.lidar.round_i.json): ...`
        (103 streets in all; grid_primary_15 and round I's 6 not among them);
      - `[weld] grid_tertiary_74 -> grid_tertiary_1#1 v1: past the host's open end, 19 point(s) read the deck of the street
        it is welded to (1 street(s); route.weld_deck_beyond_end)` (and `v45: ... 0 point(s)`);
      - `[islands] 1KERB_sidewalk_island_fork_92: 55 rows over 27.6 m, 0.74-4.00 m wide, rise 0.078 / 0.000 m ...`;
      - `[ground-patch] wall_49: TERRAIN 516981 -> 574373 vertices ..., 42509 seated on the lidar ground (8241 in the
        10 m feather), largest move 5.10 m`;
      - `[bespoke] ... 2183 buildings stood, 38 dropped (2 of them past 450 m)`, drop reasons 36 relief;
      - drive_test both PASS: soft 0, severe 0, drops 0, far ledges 1, fold bumps 4, vertex bumps 1, kinks 1.24 /km,
        bumps 0.31 /km;
      - audit CLEAN (K 0); kn5_ground_check PASS (198 heads, 0 orphans); verify_pads PASS x3 (seams 0.9-1.6 mm);
      - verify_mouths PASS: 117 mouths, `grid_primary_52#0` and `grid_primary_80#0` FAIL in their rows (ALLOWED);
        `grid_tertiary_1#1 (start) -> grid_tertiary_2#0` PASS;
      - house_seat PASS (lowest roof 1.26 m), houses 2,183 / 2,183 / 0, textures 0 untextured;
      - road kn5 89.6 MB, `_street` 6.8 MB.
      Anything else, stop and send the log to the Mac.
   4. Install, with Kevin's word: the same command without `SHIP_PROJ` and `--no-install`. AC closed.
   5. Stills, from the car, CSP daylight, into `tracks/sand-creek-lm/source/stills/<name>_drive_0.2.5.jpg`:
      - grid_tertiary_1 crossing grid_tertiary_2, 74 joining (1466 / -134), from grid_tertiary_2 southbound;
      - a few lidar streets with the most change: grid_primary_87 / 88 (decks), grid_primary_33 (+2.56 m);
      - the wall south of 1182 (-1550 / -1040), from the ground west of it (free roam: no street reaches it).
   - 4k (the shared-tools A/B) also covers this round's tools: `mouth_weld.py` / `weld_mouths_blend.py` gained
     `route.weld_deck_beyond_end` (no key, no change); `tools/naip_edge.py` is new and no step calls it.

## Owed (2026-11-05, after round J; start here)

1. **Quebec (round J item 2): measured, not built.**
   - `tools/naip_edge.py` finds the raised median's curb (+10 .. +11 m off the southbound OSM line, +0.08 .. +0.16 m, s
     140-460) but not the outer edges (curb at 9 of 44 stations; the run crosses the median north of s 480; the OSM line
     sits on the median at s 0-120 / 620).
   - Next: trace the lidar's curb as a continuous line along (not per station), NAIP only for asphalt vs concrete; the
     0.3 m NAIP crop for paint. Then re-centre both carriageways, the median as measured, 48th at ~15 m.
   - Then `sandcreek_quebec`'s outline (still parked; `route.verify_mouths_allowed` keeps its rows).
2. **Parked pads (item 3): not reached.** Round I's reasons stand (48th_colorado: the prep's contact band at its cut
   corner, the box missing the east half; dahlia_56th: the 30-42 m lap ribbon's lane edges at v770 / v771).
3. **Paint (item 5): not reached.** Fork 94/95's chevrons; Quebec's divider is a raised median at s 140-460 (an island
   step, `route.islands`, not paint) and unmeasured further north.
4. **Streets held on 3DEP (7):**
   - grid_primary_15: a viaduct deck (class 17) over ground at 9-11 m. Needs a street-bridge path (the deck as a bridge,
     the ground left at the lidar under it), then wire its profile.
   - Round I's 6 jumpy streets: look at their jump points.
   - Check the other deck streets on the lidar (grid_primary_87 / 88, 33, 64, 73) for the same embankment-for-a-viaduct
     artefact; they lost no house, but their terrain bands may be embankments the real ground does not have.
5. **The road east of the wall** (NAIP: 4 lanes at x ~ -1530 .. -1515, z < -953): not in the build south of
   grid_primary_49's end.
6. Round C (race curbs, race closure, arrow signs, street-name signs) and round H's items 4-5, unchanged.

## Owed (2026-11-05, after round I; kept for the record)

1. **More streets on the lidar (item 4): measured, parked.**
   - 100 streets in `source/connector_profiles.lidar.round_i.json`.
   - Hold grid_tertiary_2 (its mouth with grid_tertiary_1 reads 0.021 m in the host lane), or mend that weld; wire the
     file; build.
   - The 6 held streets: look at their jump points.
2. **Quebec (item 3):** re-centre both carriageways and build the raised median.
   - Needs a per-station tracer (a lidar curb step plus a NAIP edge), validated on the sections in round I's
     `quebec_scan`.
   - Then `sandcreek_quebec`'s outline: `draft_pad_outline.py`'s aerial source is "not built yet".
3. **Parked pads (item 6):** the measurement reproduces, so the fix is in the build.
   - 48th_colorado: the prep's contact band across the cut corner, and the box missing the east half.
   - dahlia_56th: the 30-42 m lap ribbon's lane edges.
4. **Paint (item 7):** fork 94/95's chevrons and Quebec's divider need a Sand Creek paint step on a street's built road
   (Lake Murray's `lane_dividers` is a mainline switch in its own assembler).
5. **The wall south of z -1000** beside grid_primary_49 (within 2-7 m of the street): not patched.
6. Round H's items 4-5 and the lists below, unchanged.

## Owed (2026-11-05, after round H; kept for the record)

1. **Not built, measured (round H above):**
   - **Fork 91/92's raised island** (x 50.5-54.5 at z -824, s 57 to the lap; lidar raised 0.05-0.2 m over the west
     gutter, 0.4 m over the east). Lead: a Sand Creek island step after `weld_mouths` that authors a curb ring + a
     CONCRETE deck on its own measured centreline with heights read off the welded ROAD (author_median_blend reads the
     trunk's pre-weld points, centres the island on the trunk and plants grass + shrubs; none of that is this island).
     Fork 94/95's chevrons: no grid-street paint path exists (Lake Murray's hatched median is `expansion_pieces.py`,
     authored pieces only); owed as paint.
   - **Quebec at measured widths**: west curb x 1645.5, raised median x 1657.5-1664, east curb x 1677 (at z 680-940); the
     median sits inside OSM's east carriageway. Lead: Quebec's two carriageways merged (or re-centred) on measured
     `edges_m` per station over 860 m plus a raised median band; the 48th crossing re-cut at the real median; 48th at
     15 m.
   - **Fork 94/95's `edges_m`**: re-measure in the track frame (round G's sit about 1.2 m east).
2. **`osm_buildings1182`**: the terrain beside `grid_primary_49` (a 20 m plateau at the street's height, then one 28 m
   facet) where lidar has a 4.3 m retaining wall at x -1561. Lead: the wall from lidar (`tools/lidar_wall.py` does it for a
   lap edge) or a verge whose blend ends at seat_terrain's own BAND_M on a finer terrain. Then 1182 stands (2,183).
3. **More streets on the lidar.** Four streets are; the rest still ride the 3DEP grid (any other bridge or embankment is
   wrong the same way). `tools/lidar_connector_profile.py <project> <names>` measures any list; the Mac needs laspy.
4. **The parked-pad allowance** (`route.verify_mouths_allowed`, 3 mouths): remove each row when its pad is built.
5. Round G's items 4-5 and round F's / E's lists below, unchanged.

## Owed (2026-11-05, after round G; kept for the record)

1. **0.2.3: the 8 failing mouths** (reproduce: `EMPTY=1` from this head; k4 is the reference workshop):
   - **APPROACH** (`t5#0#0` at the lap 3.9, `u67#0` 3.1, `p84#0#0` -> `p78#0` 8.6 %/m): each street's 3DEP profile against
     its host's deck within 30 m. These are round B's "approaches that change grade too fast", and the 3 %/m is
     [invented]. Read each profile first: a real grade change, or 3DEP noise the lidar can replace (the lidar is on the
     PC).
   - **The Y** (`t5#0#0` at `t2#0`, 18.7 deg): its NOTCH has no road 7.6-8.1 m along the host edge. Look at the mitred
     outer line there (extend reach vs the host edge's bend).
   - **The lens** (`t74#0` start): HOST LANE road / curb up to 0.038 m over the host deck although held. Find which
     vertices (the curb lines' mitres, or later steps moving the host).
   - **`u10#0#0` / `#0#1` at `t16#0#0`:** a crossroads, both mouths 0.065-0.084 m off the host deck. `grid_unclassified_10`
     is also colorado_50th's arm: check whether the arm cut or the join changed `t16`'s profile there.
   - **`r29#2`** (26.6 deg, 0.021 m in 3 samples): either hold it too (every acute mouth, not only reach > 25 m) or find the
     1 mm.
2. **The houses floor** (2,168 vs 2,181): Kevin / the coordinator. The 13 are measured in round G.
3. **Kevin's calls from round G's measurements:**
   - **91/92's concrete island** (s 57 to the lap, 3.5-4 m, raised by its brightness): pave over it (as now) or build an
     island. Neither fork's chevrons are painted; that needs a paint step for grid streets.
   - **Quebec's median strip:** 4-6 m between the OSM carriageways, asphalt or concrete at 48 of 49 samples over 860 m.
     Widen the two carriageways to the measured curb-to-curb (about 31 m at 48th), or build the strip as concrete.
   - **The cross street's width** at Quebec: about 15 m on NAIP, 8 / 10 m from OSM.
4. **When 0.2.3 is green:** ledger 0078's runbook 4j (install over 0.2.2, the PC asks Kevin first) and the one shared-tool
   A/B runbook. This branch changed these shared tools since fleet-lm-engine:
   - `draft_pads`, `lm_pads_blend`, `strip_seam_blend`, `verify_pads`, `plan_buildings`, `trim_connectors`, `mouth_weld`,
     `weld_mouths_blend`;
   - also `seat_terrain_blend`, `author_lamps_blend`, `lm_engine_intake`, `ship_track.sh` (round B).
   Not written: the build is not green.
5. Round F's items 2, 4 and the round-E list below, unchanged.

## Owed (2026-11-05, after round F; in the coordinator's order)

1. **0.2.3 finishing the junctions** (round F's code is in; build `EMPTY=1` from the committed config to reproduce):
   a. **The forks.** Make the four acute guests weld. Options, in the order I'd try them:
      - blend an acute guest onto its host over the length its ribbon overlaps the host, not 30 m;
      - or rank the two paint-divided carriageways as one divided street, using Lake Murray's
        `divide_connectors` / median island.
      Then judge t5 / t74 on verify_mouths.
   b. **Pad arms in lm_pads** (`lm_pads.arms: "streets"`, opt-in). Turn `route.street_junctions.pad_arms` on. Then
      `tools/lm_pads_blend.py` must:
      - delete only the lap's own faces between the cuts. Today it deletes any ROAD / CURB face in the cut wedge whose
        nearest lap vertex is between the cuts, which would take the streets' faces too. Add a lateral test against
        the lap polyline, within half width + 1.8 m;
      - read the arm end rows through `mw.mesh_layout(pts3, connectors)`;
      - splice them into the outline (`draft_pads.splice_rows` with `c` = `sealed_cut(box edge)` and `cr` = `row_cut`);
      - add them to `seams` and the seam profile;
      - add them to pads.built.json `rows`, so verify_pads checks their seams.
      Unbuilt, lm_pads with streets in has not been run.
   c. **Quebec's median crossing.** A piece between two mouths is dropped under 15 m. An opt-in floor is needed so the
      4 m crossing is kept and welded at both ends.
   d. Then the gates: verify_mouths, audit I / K, both drive_tests against 0.2.2, verify_pads x3, houses (round B: 16
      blocks stand on a street ribbon), kn5 MB, and the stills beside NAIP.
2. **The parked pads, alongside the PC (not built yet):** as round E's list below.
3. **The shared-tool A/B for the PC**, once 0.2.3 is green. Round F adds `trim_connectors` and `mouth_weld` /
   `weld_mouths_blend` (the keyword) to round E's list. Lake Murray's committed trim inputs through fleet-lm-engine's
   trim and this branch's still give byte-identical outputs (`664da93b…`, `b73b70f4…`, `f0c97952…`).
4. Rounds C, 5, 6 of the list below, unchanged.

## Owed (2026-11-05, after round E; kept for the record)

1. **Real junctions at all 146 street meetings (0.2.3, the main work).** Kevin: "Real junctions".
   - Lake Murray's weld / mouth / junction-pad / stub tools, trimming streets against streets (round B item 3 is the
     wiring that already works: `lm_intake.connectors`, `route.connector_hosts`, trim -> rebuild -> weld -> gap_mouths).
   - One welded deck per meeting (`data/grid_meetings.json`: 19 weld today, 17 arterial / arterial and 110 minor / minor
     overlap).
   - verify_mouths 11 -> 0, apart from mouths at a parked pad, listed by name. 48th_colorado being parked leaves
     `grid_primary_49`, `grid_primary_52`, `grid_tertiary_98` there; sandcreek_quebec `grid_primary_78`, `grid_primary_80`.
   - audit I / K 525 -> only the real ones, each named with its reason.
   - Under 120 MB (round B's scratch with the streets: 70.6 MB; 0.2.2's road kn5 is 52.7 MB).
   - Round E's de-duplicated buildings ship with it (houses 2,181 / 2,181 / 0).
2. **The parked pads, alongside the PC (not built yet):**
   - **48th_colorado:** re-declare its box over the whole crossroads (the east half). If that needs the lidar again,
     a short PC step 4i.x re-measures it with the deck reaching past both cuts. Then its lap rows can take the lidar's
     cross-section (the crown seam) and the south-east grass is re-read.
   - **dahlia_56th:** re-declare its in-cut rows onto the measured road (the lap's ribbon is 30-42 m wide there and its
     edges at v770 / v771 stand 0.1-0.7 m off the asphalt); a 4i.x step if it needs re-measuring.
   - **sandcreek_quebec:** a NAIP outline tool, after the junctions.
3. **The shared-tool A/B for the PC, once 0.2.3 is green** (one runbook). This round changed `draft_pads`,
   `lm_pads_blend`, `strip_seam_blend`, `verify_pads` and `plan_buildings`:
   - Lake Murray: the 5(a) pattern, `draft_equiv --terrain-noise`, line 6f96224 against this branch;
   - the Lariat port: fleet-lm-engine's head against this branch.
4. **Round C:** the race curbs and race closure over the grid mouths; Lake Murray's W1-6 arrows (sign step, atlas,
   placement rule, signs gate unchanged) on the lap and both layouts, reported by s and corner; street-name signs from
   OSM `name` at real junctions only, MUTCD dimensions cited, seated and out of the drivable corridor.
5. **The night stills** from the PC (runbook 4h step 5), and runbook 4i's pad stills.
6. Kinks at 50th/Ash (1.24 /km): left for Kevin's drive (coordinator, 2026-11-05).

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
