---
id: 0093
title: High Plains race furniture — the start line, the grid, the pit lane's paint, the paddock
status: in-train
scope: project:tracks/high-plains-lm (tools opt-in for any circuit; Milford's config untouched)
layer: project
train: -
---

# 0093 — High Plains race furniture: start line, grid, pit lane, paddock

## Symptom

Kevin, 2026-11-18: "for milford and high plains, we need more race track focused furniture like starting line,
gridlines, other buildings with textures. the buildings are all flat on milford and high plains".

From the driver's seat at High Plains 0.1.7:
- There is no start/finish line on the front straight.
- There is no grid and only one AC_START, so only one car can start a race.
- The grid sits on the south straight (s 1080), not the front straight.
- The pit lane is grass between two K-rails, with no paint. The pit wall stops 63 m short of its nose.
- The paddock has rows of K-rail and three structures on the photo that are not built. One shed stands on top of post1.

This entry covers High Plains' placement, paint, dummies, pads and footprints. Building skins and facades belong to
another branch.

## Evidence

All of it was measured on NAIP 2023-09-28 at 0.3 m (`co_m_3910317_ne_13_030_20230928`), the crop already in the repo
at `tracks/high-plains-lm/source/road_wear/naip_2023_030_hp.png`. The furniture audit of 2026-11-18 is at
`codex/mac/milford-hp-audit-20261118/furniture/` on Sundowning (REPORT.md §4.1 and its `work/`). Stations are on
`data/centerline.local.json`: lap 3,204.7 m, clockwise, + lateral = left of travel.

**Start/finish line**
- A white band across the full width.
- Its half-maximum extent is s 11.50-12.85 on every fifth of the width, so its centre is **s 12.15 ± 0.3**
  (the audit read s 11.8 ± 1).
- It is 1.35-1.8 m wide.
- This agrees with the official account: the starter stand on the pit wall just past halfway along the 1,200 ft front
  straight (sources audit §3).

**Grid**
- The audit's mark list (`work/hp_front_marks.json`) falls into four rows of marks:
  - right column: lateral −4.45 / −1.09 m, 13 slots;
  - left column: +0.72 / +4.11 m, 12 slots.
- Each column repeats every 8.95-9.24 m. The left column stands 4.3-4.6 m behind the right.
- That gives **25 slots**. The forward slot (the right column's) is 7.4 m behind the line; the last is 116.4 m behind.

**Pit lane**
- **Yellow line:** from s 3185 to s 165, at lateral +20.5..+21.7 m, about 4.5 m off the paddock K-rail (+25.5).
- **White end line:** across the lane at s 152.2-152.6.
- **Pit-in gore:** s 3165-3180, +16..+22 m. Its outline is the hull of the paint pixels. Stripes every 1.0 m at −40° to
  the lap.
- **Pit-out gore:** s 162-191, +16.7..+26 m, outline traced by eye. Stripes every 1.5 m, square to the lap.
- Both hatches were drawn over the photo to check them (scratch renders).
- **Pit wall, nose to s 0:** visible on the photo, not built. It runs from (s 3144, +17.1) to (s 0, +9.7), where
  `pit_wall_lidar` begins.
- **Paddock rail:** likewise missing from s 3184.5 to s 0.
- **Nose:** a dark blob 4.8 × 3.0 m centred at s 3142.3, +17.6 m.
- **Pit-lane surface:** asphalt from the pit wall (+10.3, or +12.6 past its white line from s 10) to the paddock K-rail
  (+25).
- **Paddock sheet:** the PADAPRON quad reaches the pit lane only from s 51 (outside edge) and s 105 (whole width), so
  the lane west of there is built as terrain.

**Paddock**
- **K-rail rows:** 15 straight rows fitted to the audit's 163 blue sections and checked by eye on the photo. They use
  105 sections over 570 m. The other 58 sections are trailers, tarps, the container stack's blue box and rows of fewer
  than three sections.
- **Buildings, shadow fit:** `work/hp_shadow_fit.json`, sun 146.9° / 42.9°, heights ±0.4 m. NAIP's building lean is
  not removed.
- **osm289317403:** the same 17 m² roof as post1, centroid within 0.1 m.
- **osm289314487:** the planner's own `roof_class` reads it white on the 0.3 m crop, not dark.
- **OSM 289311821** is the 16-stall carport row. Its official ceiling is 8 ft (2.44 m) (HPR's RV-carport page,
  sources audit §3). Ledger 0094 stands it open-sided on posts, as it is.
- **Posts:** 9 of 12 have a white roof on the crop. post0 and post2 sit 5.1 m from their configured footprints.
  Each post stands on a dark pad of 59-68 m² of dark pixels (post9: 93 m²).

**Dummies**
- engine-july's prep (`engine-july-snapshot/scripts/ac/build_kn5_loop.py` about line 1462) yaws every facing node
  `atan2(tx, tz)` from pts[0] -> pts[1].
- The exporter maps that to kn5 local +Z = (tx, 0, tz) against the kn5 travel (tx, 0, −tz) (`tools/layout_dummies.py`
  FACING; `scripts/ac/verify_kn5` (c)).
- At High Plains' AC_START_0 (s 1080.4, the south straight) **kn5 +Z · travel = −0.974**: the car spawns facing back
  down the straight. This is computed, not seen in game.
- verify_kn5's heading check (c) runs only on multi-layout spawn kn5s, so no gate caught it.

## Diagnosis

1. **The grid and the line.** engine-july's `place_dummies` puts the grid on the straightest 260 m and the line 30 m
   ahead of it. It writes one AC_START and eight pits on the racing surface. `route.start_at` only rotates where s = 0
   falls. Nothing reads a measured line.
2. **The facing.** The yaw is the reflected `atan2(tx, tz)`, taken once from pts[0] -> pts[1]. It is not each node's own
   tangent, and not airoso's `atan2(tx, −tz)` (scripts/ac/build_kn5_loop.py fixed this for airoso's engine; the frozen
   snapshot keeps it).
3. **The paint.** The paint step drapes on ROAD only. The pit lane has no paved surface in the build west of s 51.
4. **The paddock.** The plan never ran its shadow stage: no OSM heights, and its z18 photo is an LFS pointer here.

## Fix

Every piece is opt-in by a track.config.json key, and only `tracks/high-plains-lm` declares them.

### The declared start: `race_start`

New files:
- `scripts/geometry/circuit_start.py`: pure.
- `tools/circuit_dummies_blend.py`: a prep step. `tools/ship_track.sh` prep_prep runs it only when `race_start` is
  declared, after the prep and before the road-wear bake.

What the step does:
- Removes the prep's AC_* set.
- Places AC_TIME_0 on the measured line.
- Places AC_START_0..24 on the 25 measured slots, each car's centre between its marks, in grid order (right column
  first).
- Places AC_HOTLAP_START_0 on the pole.
- Places AC_PIT_0..24 [invented]: on the racing surface ahead of the line, s 20-129, staggered like the grid. The pit
  lane is not drivable.
- Divides the lap into equal thirds for AC_TIME_1/2 (s 1080.4 and 2148.6; engine-july's rule, unmeasured).
- Yaws each facing node `atan2(ux, −uz)` from its own ±2.5 m tangent.
- Sets heights: the built 1ROAD top + 0.30 m (+0.10 m for the timing pair).

It refuses, and the blend is not saved, when:
- a car is not 0.30 m inside the road;
- a car corner or centre has no 1ROAD under it;
- two cars overlap;
- the grid is out of order;
- AC_TIME_0 is not 0 < d ≤ 35 m ahead of the pole;
- the sectors are out of order;
- the track is multi-layout;
- the kn5 heading is under cos 30°.

It rewrites `data/dummies.json` and writes `data/circuit_dummies.json`: what was placed and what it replaced.

The `pattern` form (`first_m` / `step_m` / `lateral_m` / `slots`) and `line.station_m` let a track with no marks use
it. That is Milford's case, on Kevin's word.

### verify_kn5: `race_start_checks`

Opt-in, single-layout branch, only with `race_start`. It applies the multi-layout rows' own thresholds (none moved):
- **(c) HEADING:** every facing node within HEADING_MIN_DEG.
- **ROAD:** every START/PIT car LANE_MARGIN_M inside the road. A circuit's grid stands on both sides, so "right of
  travel" does not apply.
- **(e) LINE:** AC_TIME_0 within LINE_TOL_M of the declared line, 0 < d ≤ LINE_AHEAD_MAX_M ahead of AC_START_0, sectors
  in order.
- The declared node set is present.

### Paint

`tools/author_paint_blend.py` gains, all opt-in per item:
- `surface` (mesh-name prefixes) and `--stage draft|author`. `draft_paint` passes `--stage draft`; Sand Creek's items
  name no surface, so they paint exactly as before.
- Lines declared in lon/lat, grid dots and gore hatches, through the new pure `tools/paint_shapes.py`.

New `author_paint` in `tools/ship_track.sh`. High Plains' `ship.json` runs `paint` in the draft (after kerbs) and in the
author phase (after bespoke).

`route.paint` items:

| Item | Object | Size | Surface |
|---|---|---|---|
| `sf_line` | MARKINGS_paint | 1.5 m across the built road | ROAD |
| `grid_marks` | MARKINGS_paint, 50 dots | 0.3 m [invented shape] | ROAD |
| `pit_lane_line` | YLINE_paint | 0.3 m | PADAPRON |
| `pit_lane_end` | MARKINGS_paint | 0.45 m | PADAPRON |
| `pit_in_gore` | YLINE_paint hatch + outline | | PADAPRON |
| `pit_out_gore` | YLINE_paint hatch + outline | | PADAPRON |

### Pads (`scenery.bespoke.pads`, appended)

- **`pitlane`:** a PADAPRON strip from s 3162 to s 104, its edges as measured. It runs 0.5 m onto the paddock sheet,
  where the texels are the same, so no paint ray finds a seam.
- **`post*_pad`:** nine PADAPRON squares, side = √(dark area) (7.7-9.6 m), centred on each post. Their material is
  [invented].
- PADAPRON_0 is still the paddock.

### Rails (`scenery.bespoke.rails`, appended; the first eight are unchanged, so no object is renamed)

- **`pit_wall_west`:** krail, 1.03 m, the lidar's height for the same wall.
- **`pit_paddock_west`:** krail, 0.59 m, likewise the lidar's.
- **`pit_wall_nose`:** tyres, 3.0 × 2.4 m. The kind's module and height are [invented].
- **`paddock_row_0..14`:** krail, 0.81 m [invented].

### Buildings and posts

These are the port's own files, synced in by ship.json. `tracks/high-plains` keeps its own.

`source/bespoke/buildings.race.json`:
- OSM's six paddock footprints, less osm289317403.
- Heights are the shadow fit's tops, marked as shadow estimates. A gable's ridge is the measured top; its wall is
  top − rise over the footprint's oriented box, floored at 2.1 m.
- The carport row: eave 2.44 m, official.
- Roofs as `plan_buildings.roof_class` reads the 0.3 m crop.
- Plus three traced structures:
  - the white building, 12.2 × 8.5 m, top 3.9 m;
  - the pit-entry canopy, 9.5 × 8.1 m, top 3.1 m. This commit stood it closed, because the `posts` form was refused
    within 60 m of the lap; ledger 0094 stands it open on posts, each with a collider (`post_collider`);
  - the container stack, 24.9 × 12.2 m, 2.6 m [invented: ISO 668's 2.59 m].

`source/bespoke/posts.race.json`:
- The 12 posts, 8 of them re-centred on their roofs.
- Each is a 3.5 m square, 2.8 m tall [invented, as before].

### Other

- `source/bespoke/buildings.plan.json` (the port's) points the planner at the real 0.3 m crop with the hand-read sun.
- Version 0.1.8.

## Scope

- **Changed:** High Plains (`tracks/high-plains-lm`) only.
- **Byte-identical:** every other track's output. No other config names the keys. `draft_paint`'s `--stage draft`
  paints Sand Creek's surface-less items the same way, and the new verify_kn5 rows run only under `race_start`.
- **Untouched:** Lake Murray, its engine-july snapshot and `tools/ship_sd.sh`.
- **Not done (Kevin's calls):**
  - Milford's line: a white transverse line at s 4628.6, 64 m past its AC_TIME_0, identity medium.
  - High Plains' layout: built as the West 2.0 mi (3,205 m), not the Full 2.55 mi.

## Verification

The PC runs the runbook below. The gates are unchanged; their thresholds are unchanged.

## PC runbook (0093-1)

1. **Config and code.** Branch `claude/hp-race-furniture-20261118`. `tracks/high-plains-lm/track.config.json` 0.1.8
   declares `race_start`, `route.paint`, the appended pads and rails, and the two port block files. The engine copy
   (ENG) is unchanged. `assets/textures` is unchanged: no new texture. The tyres bind TECPRO's skin; see the open
   decision below.
2. **Rehearse.** From an empty workshop, full draft (the paint step is in the draft):
   `SHIP_PROJ=<scratch> bash tools/ship_track.sh high-plains-lm --dry-run`, then the full build to a scratch install.
   No `--skip-blend`: the draft paint must run.
3. **Read, in order:**
   - **draft:** the `[paint] MARKINGS_paint_sf_line` and `MARKINGS_paint_grid_marks` lines, read-back ≤ 1 mm.
   - **author:** `[bespoke]`:
     - 9 + 12 blocks less any refused;
     - the pads paddock, pitlane and 9 post pads;
     - 26 rails;
     - `[paint] YLINE_paint_pit_lane_line`, `MARKINGS_paint_pit_lane_end`, `YLINE_paint_pit_in_gore` and
       `YLINE_paint_pit_out_gore`, each "over the built PADAPRON".
     - A `no PADAPRON under` FATAL means a strip cell was left out; report its station.
   - **prep:** `[circuit-dummies] 16 prep dummies replaced by 57: the line at s 12.2, 25 grid slots, 25 pits, sectors at
     s 1080, 2149; kn5 heading min +1.000 (the prep's AC_START_0 read -0.974)`.
   - **verify_kn5:** expect PASS, plus two new lines:
     - `[race_start] heading: 51 facing nodes, local +Z . travel min +1.00`;
     - `[race_start] road: 50 START/PIT cars inside the road, nearest edge ≈ +2.1 m`.
   - **AI:** `grid check: +0.9x (grid→timing chord over 8 m) -> FORWARD`; point 0 of the line at s ≈ 12.
   - **Track folder:** `ui_track.json` pitboxes 25.
   - **Gates:** drive_test (street, hard), audit, kn5_ground, road_wear, house_seat, edge_report: expect no worse
     than 0.1.7.
4. **Compare.** kn5_equiv and mesh_diff against the installed 0.1.7. Expect new objects only:
   - `MARKINGS_paint_*` and `YLINE_paint_*`;
   - `PADAPRON_1..10`;
   - 1WALL_KRAILBW_8, 9, 11..25 and 1WALL_TECPRO_TYRES_10;
   - re-numbered BUILDING/ROOFTOP;
   - the AC set.
5. **Stills.**
   - The front straight from the grid: band, dots, pit wall.
   - The pit-in gore and nose.
   - The pit-out gore and end line.
   - The paddock rows and containers.
   - Each post on its pad.
6. **In game, on Kevin's word to install.**
   - A 25-car race start: cars on the front straight facing T1, pole on the right.
   - A practice from the pits.
   - Is the lap counted at the band?

## Open decisions for Kevin

- **Pits on the racing surface** (s 20-129, the grid's stagger), until a drivable pit lane exists. Or keep 8.
- ~~**The pit-entry canopy as a closed box.**~~ Settled by ledger 0094: it and the carport row (open sides, an 8 ft
  ceiling) stand open on posts, a collider in every post.
- **The containers' 2.6 m height** [invented], and the 11 × 23 m grey roof east of them, not built: the photo cannot
  tell roof from ground.
- **The tyres' skin.** `1WALL_TECPRO_TYRES` is bound by `texture_overrides["1WALL_TECPRO"]` where a track declares one.
  Milford has it; High Plains does not yet, so its nose wears the Tec-Pro skin.
- **Milford.**
  - Its line at s 4628.6 as the S/F: `race_start` with `line.station_m` and a `grid.pattern`, both invented for lack of
    marks.
  - Its spawn: engine-july's reflected yaw reads ≈ −1 on a north-south straight like Milford's front straight
    (computed, not seen in game).

## PC rehearsal 1 (2026-11-20, 4fdb3c9f) and round 2

The PC's first 0.1.8 rehearsal (empty workshop, ENG eng_hplm_0108) stopped in the author paint:
`[paint] FATAL: pit_out_gore line 0: no PADAPRON under (435.20, -9.11)`. `pit_lane_line`, `pit_lane_end` and
`pit_in_gore` painted, read-back 0.00 mm.

- **Cause (measured on the Mac off this config):** the traced gore's tip lies past the paddock sheet. Its last outline
  corner (s 190.9, +16.7) is 4.2 m outside the PADAPRON quad (pad 0, the 0.1.7 sheet), the corner before it 0.75 m inside.
  Past the quad's edge the build has terrain, not paving. It is not a left-out cell: the point is 10.7 m off the road's
  edge, and 4 m cells are left out only over a road.
- **Fix (opt-in):** route.paint `clip_to_surface` (`tools/paint_shapes.drape`, which `tools/author_paint_blend.py` paint()
  now calls; without the key it is the old loop, vertex for vertex). It paints only where every stripe edge has surface
  under it, prints the length left out, and still stops if nothing is left. `pit_out_gore` alone names it.
- **Proof (Mac, Blender 5.1):** a stand-in scene of the 11 pads off this config, flat. Without the key the paint step stops
  on exactly the PC's line and point. With it: `[paint] pit_out_gore: clip_to_surface: 14.5 m of 144.3 m of line has no
  PADAPRON under it, not painted`, `YLINE_paint_pit_out_gore: 19 yellow lines, 129.8 m in all (273 quads, read-back
  0.00 mm)`. The other three items print as on the PC. Left out: hatch stripes 0 and 1 (1.2, 2.5 m), 1.0 m of stripe 2 and
  9.7 m of the outline. `tests/tools/test_paint_drape.py`.
- **Not fixed:** the pit exit's merge past the paddock sheet is built as terrain. Paving it needs its edges measured off
  the 0.3 m photo.

Two auto K-rail rows stand no module: `paddock_row_3` (37 m, 12 left out) and `paddock_row_8` (21 m, 6 left out). Measured
on this config's centreline (12 m road): row 3 runs s 262-299 at -6.5 to -6.7 m, its 0.6 m modules over the road's edge;
row 8 runs s 212-236 at +4.8 m, on the racing surface. The author is right to leave them out. What the photo's blue
sections there are (a layout's temporary rails?) is Kevin's call; they stay in the config, standing nothing.
