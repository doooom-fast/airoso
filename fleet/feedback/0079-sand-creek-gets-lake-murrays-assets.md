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

## Owed

- **The lidar roofs** (the PC, runbook 4g step 1): `tools/lidar_buildings.py`. Then re-plan, rebuild 0.2.1 and set the
  houses floor again.
- Round B: a street-to-street trim / weld (or Kevin's word on arterials as the only hosts), `seat_terrain`'s strip width
  from `route.edge`, and the pad module with street arms.
- Round C: the race corridor and closures over the grid mouths; the race kerbs; street-name blades as a chain step.
- `colliders 0`: no block stands within 60 m of the lap on fine ground (as in 0.1.1).
