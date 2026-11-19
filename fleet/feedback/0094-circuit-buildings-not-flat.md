---
id: 0094
title: The buildings on Milford and High Plains look flat
status: diagnosed
scope: kind:circuit, milford-road-course-lm, high-plains-lm
layer: engine
train: -
---

## Symptom

Kevin, 2026-11-18: "for milford and high plains, we need ... other buildings with textures. the buildings are all flat on
milford and high plains".

## Evidence

The furniture audit of 2026-11-18 (`/Volumes/Sundowning/codex/mac/milford-hp-audit-20261118/furniture/REPORT.md` §2, its
`skins_as_built_24x6m.png`), measured off the committed files and `tools/author_bespoke_blend.py blocks()`:

- Every block is a bare prism: one quad per footprint edge, flat shaded; flat roofs are the ring, pitched roofs end at the
  wall line (no overhang, fascia or gutter); no door, window, louvre or rooftop unit anywhere.
- `tiltup_wall` (8 m a tile): luminance sd 12.1, one joint per 8 m; normal tilt p50 3.4 deg / p90 6.3 deg.
- `metal_wall` (0.914 m a tile): normal tilt p50 0.3 deg / p90 2.1 deg, essentially flat.
- `roof_white / tan / dark`: luminance sd 5.4 / 3.6 / 2.0 and no normal map, so `ksPerPixel`.
- Lake Murray's houses read well because `house_walls()` puts a window in every 3 m bay (ledger 0065).

## Diagnosis

The look is the content of three plain tiles on bare prisms. Two constraints shape the fix:

1. **engine-july's pbr table is frozen** (`tracks/san-diego-lake-murray/engine-july-snapshot/scripts/ac/pbr.py`): a new
   object prefix binds no texture (or the wrong row) and engine-july's prep re-plans its UVs unless the prefix is in its
   `planar_uv` skip list. A new skin can therefore only arrive through a row that already exists, re-bound per track by
   `texture_overrides` (the route ledgers 0065 / 0079 / 0083 use). One row = one texture per track, so the skins share
   **one atlas**, and a block's skin picks its cells by UV.
2. **engine-july's prep re-seats every `BUILDING*` island** (its base ring = the island's vertices within 0.05 m of its
   lowest z, in index order). The new walls are one island per building, the base ring first; rooftop units are never
   `BUILDING*` (they would be seated onto the ground) and ride `FARBLOCK_METAL_RTU`, which the prep neither seats nor
   re-plans.

## Fix (branch `claude/circuit-buildings-20261118`; opt-in, every key absent = as before)

**Textures** (`tools/make_bespoke_assets.py`, third batch; numpy + Pillow, `--only circuit` writes this batch alone so the
other batches' bytes are never re-encoded; CC0 in `assets/licenses.json`; the cell table is `tools/circuit_facades.py`):

| File | Size | What |
|---|---|---|
| `circuit_facade_diffuse.jpg` / `_normal.jpg` | 2048², 577 KB + 1,051 KB | 16 cells of one bay x one module: ribbed metal (plain, roll-up door, man door + window, window band), tilt-up (plain panel, dock door, man door + louvre, louvre + downspout), corrugated containers (white / tan / blue sides and door ends), a rooftop unit's side, metal and concrete grime bands. 24 px gutters of each cell's own edge pixels. The normal map is 4:4:4 so a 4 px rib face keeps its tilt |
| `roof_membrane_normal.jpg` | 1024², 64 KB | a single-ply membrane: a welded lap every 3 m, an end lap, fastener plates, a faint billow (12 m a tile) |
| `roof_rib_normal.jpg` | 2048², 888 KB | ribbed metal roofing on 0.3 m centres, faces at 52 deg (12 m a tile), the ribs running up a gable's slope |
| `fabric_tent_diffuse.jpg` / `_normal.jpg` | 512², 36 + 15 KB | a clearspan tent panel: the frame's keder every 5 m (legs on the walls, rafters on the roof), the panel bowing between them, tension creases (no skirt: the tile repeats up the roof's slope) |

Measured relief (the audit's measure, normal tilt): metal rib faces 52-53 deg at their centres, p90 45 deg (was 0.3 / 2.1);
container corrugation p90 52 deg; the rib roof p90 50 deg (the roofs had no normal at all).

**Geometry** (`tools/author_bespoke_blend.py blocks()` + the pure builders in `tools/circuit_facades.py`):

- `skin` takes the atlas skins `garage`, `post`, `shed`, `plant`, `container_white` / `_tan` / `_blue`
  (`facades.SKINS`). Each footprint edge is cut into whole bays (`bays()`, so an opening is never cut at a corner), one
  cell per bay; the door storey stands at the door level (the prep's floor; a far block's mean ground), plain modules above
  it, plain cells counted down to the foundation. On a file group, `skin` (and the detail keys) apply to every row (the
  planner writes `metal` on every shed), unless the row names an atlas skin itself.
- A gable on a rectangle carries its gable ends in the walls (the house seat then reads the building's full height, as the
  author's own floor rule already did); `eave_overhang_m` (+ `rake_m`, `fascia_m`, default `FASCIA_M` 0.2 m) stands the
  roof as a closed slab carried past the eaves and the gable ends with a fascia (`facades.gable_slab`).
- `base_grime_m`: a grime band at the foot of every bay without a door.
- `rooftop_units`: boxes at measured positions on a flat roof (a list, or a file keyed by block) ->
  `FARBLOCK_METAL_RTU_<k>`.
- `flat_parapet` with a row's `parapet_m` works in the atlas (the parapet's outer face, cap and inner face in the plain
  cell). Neither track's lidar products resolve a parapet (Milford's pass 3 / 4 are 2 m roof cells; High Plains has no
  building lidar read), so neither track names one: see Open.
- The row check (`atlas_rows_check`): a row carrying atlas UVs must be bound to the atlas by the track's
  `texture_overrides`, a row carrying the old tiled UVs must not be, and a row may not carry both. A track that names no
  atlas skin never reaches the check.

**Layouts, all [invented]** (no photograph of either site's walls is in the repo; kept plausible for an industrial proving
ground and a club paddock):

- garage: a roll-up door (2.74 x 2.44 m) in every bay of the long side facing the lap, a man door in every fourth bay of the back, one in the middle of each end;
- post: windows (2.44 x 1.0 m, sill 1.0 m) facing the lap and to both sides, the door on the far side;
- plant: a dock door (2.74 x 3.05 m, sill 1.22 m, seal and bumpers) in every third panel of the long walls, never a corner panel, a man door at each end of them; on the short walls a man door in the middle and louvres high in every other panel;
- container: corrugated long sides, the door end facing the lap, the corrugated front wall at the other end;
- bays: metal 3.658 m (12 R-panel ribs), tilt-up 8 m, container side 3.05 m, container end 2.438 m; modules 3.0 / 8.0 / 2.6 m;
- overhang 0.3 m, rake 0.3 m, fascia 0.2 m; grime 0.5 m (garages), 0.4 m (posts), 0.8 m (plants); rooftop-unit heights
  1.5 m (Milford plant A's big units) and 1.0 m (the small ones).

**Measured**: Milford's rooftop units, traced off NAIP 2022 (`tracks/milford-road-course-lm/source/furniture/rooftop/`,
`trace_rooftop_units.py`, evidence `rooftop_units_on_naip.jpg`): plant A 5 (its big units, 10-12 x 12-20 m), plant B 78 (small light units, 1.5-4 m), mpg_west_bldg_a 1 (the stack at its north end), mpg_west_bldg_c 1, mpg_nw_small none; a box whose footprint leaves its roof is dropped and counted by the author. The white and tan containers' colours are
S2's and S1's roofs on NAIP 2022 (rgb 199, 214, 205 and 218, 185, 153; `plan_buildings.roof_colour`). Milford's roof
colours (item 4): the 7 roofs wholly on NAIP 2022 measured (`source/furniture/rooftop/roof_palette_blocks.py`, Del Mar's `plan_buildings.roof_palette`): plant A rgb 228, 229, 226; plant B 196, 193, 183 (grey, not white); S1 218, 185, 153; S2 199, 214, 205; mpg_west_bldg_a 237, 238, 235; mpg_west_bldg_c 240, 239, 235; mpg_nw_small 225, 228, 225. mpg_west_bldg_b is not wholly on the photograph and keeps the white class, as do pass 4's 17 roofs west of it (with the membrane normal). A palette roof's UVs sit in one solid cell, so it takes the palette's flat normal, not the membrane's.

**Config** (skin / form / detail keys only; High Plains' building list, footprints and heights are the other coder's):

- Milford: plants A and B, pass 3 and pass 4 -> `plant` (grime 0.8 m), the rooftop units on plant A, plant B and the west
  buildings; pad sheds S1 / S2 -> `container_tan` / `container_white`; `texture_overrides` BUILDING_METAL, FARBLOCK_METAL,
  BUILDING_TILTUP, FARBLOCK_TILTUP -> the atlas, ROOFTOP_WHITE / ROOFTOP_TAN -> their own diffuse + the membrane normal,
  BUILDING_FABRIC (the pad tent) -> the tent fabric, ROOF -> the measured palette; `ship.json sync_in` carries them.
- High Plains (on top of ledger 0093's `buildings.race.json` / `posts.race.json`): the buildings group -> `garage` with a
  0.3 m overhang and a 0.2 m fascia (grime 0.5 m); the container stack -> `container_row` (ten 40 ft boxes side by side,
  their doors on the long side facing the lap, colours [invented]: NAIP shows stripes, not read); the carport row and the
  pit-entry canopy -> open on posts (below); the posts group -> `post` (grime 0.4 m); BUILDING_METAL / FARBLOCK_METAL ->
  the atlas, BUILDING_SIDING -> the canopies' metal skin, ROOFTOP_WHITE / TAN / DARK -> their own diffuse + the rib normal.

**Open canopies (the coordinator, 2026-11-19).** osm289311821 is HPR's 16-stall carport row (open sides, an 8 ft ceiling,
a concrete floor; ledger 0093's sources audit section 3), and the pit-entry canopy is open on the photo. Ledger 0093 stood
both closed because the `posts` form was refused within COLLIDER_REACH_M (60 m) of the lap: posts had no collider.

- `post_collider` (a posts row's opt-in key): a collider in every post (`canopy_post_colliders`), COLLIDER_INSET_M
  (0.03 m) inside the visible post along its diagonals, each corner BOTTOM_UNDER_M under its own ground, up to the soffit,
  under the wall collider's fine-ground rule (`collider_ground_ok`, the group's `collider_tri_m`), into the existing
  1WALL_TILTUP collider batch (the row drive_test and house_gate read as a building's collider). If one post is refused,
  the canopy is refused (dropped, as before), never stood half held.
- `post_step_m`: the carport's posts every 4.39 m (70.1 m / 16 stalls, a post between every two stalls): 36 posts.
- `canopy_roof: "gable"`: the posts carry a 0.15 m ceiling plate [invented] whose soffit is the row's wall_h_m (the
  official 8 ft ceiling, 2.4 m as 0093 wrote it), and the shadow fit's gable (ridge 3.0 m) over it as a ROOFTOP slab with
  the group's 0.3 m overhang and fascia, its gable ends closed.
- The pit-entry canopy: posts every 6 m at most (CANOPY_POST_M): 8 posts, the flat slab's top at 3.1 m.
- The canopy keeps its ribbed metal: where a track binds BUILDING_METAL to the atlas, the canopy batch rides
  CANOPY_SPARE_ROW, BUILDING_SIDING (a house row no circuit uses; engine-july's prep keeps its UVs and seats its islands as
  BUILDING_METAL's; house_gate counts it as a block), bound by the track's `texture_overrides` to `metal_wall_*`, the
  canopy's own skin. The tyre walls ride 1WALL_TECPRO the same way (ledger 0082). The author refuses a track whose spare
  row is not bound to that skin, or whose own siding houses would wear it, and the atlas row check sees no mix.
- Every existing posts row, and every track with no new key, stands as before (the A/B below).

## Scope

Milford and High Plains only. Every other track: no config names a new key or the new files, so `blocks()` runs the code
it ran before (the A/B below), and the existing skin files are byte-identical (`git diff --stat` touches no existing texture).
Lake Murray is unchanged: its config, its engine snapshot and its textures are untouched. A shader change reaches a track
only through its own `texture_overrides`: the ROOFTOP rows gain a normal map, and so `ksPerPixelMultiMap`, on these two
tracks alone.

## Verification

Mac (this branch, on ledger 0093's e668c064; the sparse worktree lacks other tracks' files, so the same 40 tests fail for
missing files before and after):

- 18 relevant test files on e668c064 (this branch's changes stashed): 122 passed, 40 failed, 1 skipped.
- The same files plus `tests/tools/test_circuit_buildings.py` on this branch: 142 passed, 40 failed, 1 skipped. The failure
  lists are identical; the 20 new tests pass.
- `tests/tools/test_lidar_roof_forms.py::test_no_other_track_overrides_the_roof_row` now allows Milford next to Del Mar
  (it pinned the ROOF row's opt-in to Del Mar; Milford opts in here, item 4).
- `make_bespoke_assets.py --check` passes (the old files within its tolerance), and `git status` shows no existing texture
  modified.
- Of the 40: `test_milford_furniture.py::test_keys_are_opt_in` fails on e668c064 itself, not for a missing file: High
  Plains' K-rail nose now uses rails kind `tyres` (ledger 0093), which that test allows on Milford only.

The A/B of `blocks()` (Blender 5.1, a synthetic sloped scene; `ab_blocks_blend.py` and `ab_blocks_result.json` in the
stills folder): e668c064's author tool against this branch's.

- Seven legacy rows (flat tilt-up, flat_parapet stucco, hip siding, two gable metal sheds (one ridge across), a far block
  with a measured roof, a canopy on posts past 60 m): the same 10 objects, vertex for vertex, face for face, uv for uv.
- The atlas rows (garage, post, container, far plant with a rooftop unit) and the two canopies, opt-in: no refusal. One wall
  island per building. The carport stands on 36 posts with 36 post colliders, the pit canopy on 8 with 8 (44 collider
  shells).
- Refused as they should be: the atlas rows with no texture_overrides, a legacy metal shed on the atlas row (a mix), the
  canopies with the spare row unbound, and a legacy canopy near the lap (refused by both copies alike).

Stills (Blender, the same pure builders, Eevee; before = the old skins and the legacy UVs):
`/Volumes/Sundowning/codex/mac/milford-hp-audit-20261118/buildings-stills/` — `garage_*`, `post_*` (High Plains),
`plant_*`, `containers_*`, `tent_*` (Milford), `carport_*` and `pit_canopy_*` (High Plains: ledger 0093's closed boxes,
then open on posts), each `_before.png` / `_after.png`.

### PC runbook 0094-1 (rehearsal, install only on Kevin's word)

1. Check out the branch. Copy the new textures into the engine copy's `assets/textures` and md5-check them with the rest:
   `circuit_facade_diffuse.jpg` a60a45baeb14326d51ce67ff25d5b4a8, `circuit_facade_normal.jpg`
   f6dacb3d56cd81910f04616bdda73c00, `roof_membrane_normal.jpg` 8e76d63c1456e43318eda5dcc450b3c7, `roof_rib_normal.jpg`
   d63b3d66c367dcaf74d129b1e3cb5ae5, `fabric_tent_diffuse.jpg` a95d410671c571705862677fca9ae177, `fabric_tent_normal.jpg`
   274272d4cc083247a5f4b1206f52c29a. Both ship.json `sync_in` lists name them too.
2. Rehearse each track from an empty workshop: `bash tools/ship_track.sh tracks/milford-road-course-lm` and
   `bash tools/ship_track.sh tracks/high-plains-lm` (draft -> author -> prep -> ship -> gate, as ship.json lists them).
3. Read in the author log: `[bespoke] block <key>: METAL|TILTUP ...` for every block, no `self-check FAILED`; in
   `data/bespoke.report.json` every row's `facade` (skin, bays, openings) and Milford's `rooftop_units` counts.
4. Gates: `house_seat` (`tools/house_seat_check.py`: 0 floating / sunken / buried; the canopies are BUILDING_SIDING
   islands now), `house_gate` (no floor is declared on either track: report the counts; Milford's rooftop units count
   under blocks, High Plains' 44 post colliders under colliders), `drive_test` (the post colliders must not read
   floating), `kn5_textures` (0 missing: the six new files and High Plains' metal_wall_* under BUILDING_SIDING embedded),
   `verify_textures` (0 untextured), and the rest of ship.json's gates as before. No gate threshold moves.
5. `kn5_equiv` / `mesh_diff` against the installed build: only `BUILDING_METAL*`, `FARBLOCK_*`, `ROOFTOP_*` and
   `BUILDING_FABRIC*` change; the road, ground, kerbs, walls and colliders must not.
6. Stills in game (or the PC's Blender stills): High Plains' carport row and pit canopy (open, drive into a post: it must
   stop the car), a garage and a marshal post from the paddock; Milford's
   plants from the front straight, the pad sheds and the tent from the ride pad. Note any shimmer on the ribs at distance
   (the normal's mips) and any seam between atlas cells.

## Open (Kevin's)

- Every layout is invented. A photograph of either paddock (or Kevin's own) would replace them.
- Parapets: none measured. The G10 could read them off the 2017 (Milford) / 2018 (High Plains) lidar point clouds
  (`tools/lidar_roof_forms.py`, as Del Mar's pass 4), and the rooftop units' heights with them.
- High Plains' roof palette (Del Mar's route) is the other coder's plan work (`buildings.plan.json`); this branch gives its
  roofs relief only.
- Owned concrete (`claude/owned-surfaces-20261116`) in place of the tilt-up base is still Kevin's call; the atlas cells
  would be repainted from it.
