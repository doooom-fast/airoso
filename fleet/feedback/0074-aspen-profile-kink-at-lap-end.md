---
id: 0074
title: Aspen's 17 severe steps at the lap's end were the fold pad's flat-zone rims
status: fixed-awaiting-rebuild
scope: tracks/aspen
layer: project (opt-in engine switch)
train: -
---

## Symptom

Aspen's first build through the chain (PC, 0.67.0) passed every gate with no force but rode rough: severe steps 17,
steps 14.96 /km, kinks 33.52 /km, vertex bumps 57; fold bumps 0, excursion drops 0; lap 1,670.6 m, ring rotated 382
points. All 17 severe steps sat at lap stations 1,551-1,557 and 1,597-1,599 m, 6-9 cm across every wheel path. The
config's `_owed` note pointed at an elevation kink near the lap's end (V1 stations 1517-1519, ledger 0025).

The Mac draft (gps -> elev -> project -> build_mesh -> drive_test on a copy without `loop.blend`, 3DEP fetched live)
gives the PC's numbers exactly: 17 / 14.96 / 33.52 / 57, worst 9.2 cm at 1,553 m. Every input is in the repo.

## Mechanism

Not the elevation data, and not the seam. The stretch is the 160 deg final hairpin before the start/finish chute.

- 3DEP climbs about 2.4 % through the corner: raw 2,276.95 m at local 1,542 m, 2,278.09 m at 1,590 m. That is a real
  rise. Then a local crest at 1,590-1,613 m (smoothed 2,278.09 m). `z_smooth_m` follows `z_raw_m` within 0.1 m and
  has no kink there; grade changes are under 3.4 % per 3 m. The grade cap (8 %) does not bind.
- Seam: the gps ring repeats vertex 0 (561 points, first = last). The projection's rotation skips the duplicate
  (`source_index` runs ..., 559, 0, 1, ...). Local and elevation ends match (2,277.74 m). The steps are 70-120 m
  from the seam. L13 is clean here.
- Draft vs finished stations: the finished line is 5.8 m shorter (corner rounding). The drive test walks the finished
  line, and the steps are at finished stations.
- The cause: `scripts/geometry/build_mesh.py` reads the hairpin as a fold apex (>110 deg within +-15 m, apex at
  finished 1,573.1 m). It plateaus the profile over +-40 m with a smoothstep. The +-60 m chord grade is 0.92 %, under
  the 2.5 % "flat" test, so it also lays a fold pad: a paved disc and a flat zone of radius w/2 + 16 = 20.5 m, with every
  pavement vertex inside SNAPPED to the apex plane (2.29 m local). The snap is hard-edged, and 20 m out the plateau
  is at half weight. On a corner that climbs 2.4 %, the first vertex inside the circle (finished 1,552.8 m, centreline
  2.06) jumps 0.23 m up to the plane, after 1.99 at 1,549.8 m: 0.30 m in 3 m against 0.07 before. The last vertex
  inside (1,592.9 m, 2.45) drops 0.16 m to the plane, with 2.49 just outside: about 0.20 m in 3 m. Across a 1 m wheel sample,
  that is the 6-9 cm second difference at 1,551-1,557 m (rim entry, the edge vertices crossing the circle at different
  stations) and 1,597-1,599 m (rim exit).
- This corner is not a fold the ribbon cannot sweep. The finished-line radius is 12.6-18 m at a 9 m width (inner
  edge R >= 8 m), and fold bumps read 0 with or without the pad.

The 0025 note's "V1 1517-1519 kink" was the same place on the old 1,600 m lap (the 76 m shorter smoothed line).

## Fix

Opt-in, per track. `build_mesh.fold_pads_enabled(cfg)`: `road_profile.fold_pads: false` drops the disc and the flat
zone at every fold apex and keeps the +-40 m plateau. Absent or true is the old path, unchanged.
`tracks/aspen/track.config.json` sets it (version 0.67.0 -> 0.67.1). No gate was touched.

Measured and not taken: also dropping the plateau, so the real smoothed climb rides through. That is closer to the
measured road (replication p95 0.16 vs 0.19 m) but rougher on the hairpin's inner lane: steps 5.39 /km, kinks
16.16 /km (new kinks at 1,575-1,576 m, offset -3.75), vertex bumps 57. It would take a second switch. Left for
Kevin's drive to decide.

## Proof (Mac, engine draft, no `loop.blend`)

| Aspen | baseline 0.67.0 | after 0.67.1 |
|---|---|---|
| severe steps | 17 | **0** |
| bumps >2.5 cm /km | 14.96 | 3.59 |
| slope kinks /km | 33.52 | 12.57 |
| vertex bumps (reported) | 57 | 52 |
| fold bumps / excursion drops / far ledges | 0 / 0 / 6 | 0 / 0 / 6 |
| ground on top / daylight / obstructed / floating | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| replication vs measured (median / p95 / max) | 0.03 / 0.19 / 0.42 | 0.03 / 0.19 / 0.42 |
| audit_mesh | CLEAN | CLEAN |

`centerline.elevation.json` and `finished_centerline.json` are byte-identical before and after. The profile, and so
every crest, is exactly the baseline's; only the pavement snap is gone (`flat_zones.json` `[]`). The lap's real crests
stand as the plateau already left them. The hairpin crest reads 2,278.05 against the smoothed 2,278.09, the same in
0.67.0. The lap's high point, 2,281.6 m, is untouched.

Engine control, High Plains (draft from scratch, origin/main scripts vs this branch): every data file and `track.obj`
byte-identical (md5 `59c5f56a562f1c6e8eda03942d6f1a67`). drive_test severe 0, bumps 1.24 /km, kinks 7.77 /km, audit
CLEAN. High Plains has no fold apex, so this shows only that the default path is unchanged.

Test: `tests/geometry/test_fold_pads_opt_out.py` (stdlib only). It checks that the switch defaults on, that only the
pad-selection loop is gated (the plateau loop still walks every apex, and the flat zones come from the pad set
alone), and that Aspen opts out.

No USGS lidar EPT covers Woody Creek. The four CO projects whose bounding boxes reach 39.26 N, -106.88 W
(SanLuisJuanMiguel_2, UpperColorado Hydroflattened and Topobathy, WestCentral_2019) do not contain the point. So
the corner's 2.4 % rests on 3DEP alone.

## Same mechanism elsewhere (not touched)

Replaying the apex and pad selection on each committed `finished_centerline.json`: Under the Dragon (gravel and tarmac)
has one pad apex at 2,498 m (chord 1.84 %). There the snap moves the centreline up to 0.32 m (gravel) and 0.23 m
(tarmac), so its rims likely step the same way. Dragon Tail's three apexes are steep (chord 9-10.5 %) and get no
pad. Exotics, High Plains, Milford, Lake Murray and Sand Creek have no apex. Pueblo, Grand Junction, Pikes Peak, IMI,
Second Creek, the Lariat and the freeway have no committed draft data and were not checked. Second Creek is known to
carry a pad (the ring guard's comment, 2638-2640). Whether the engine should feather the snap for every track is
owed. Doing it would change those tracks' bytes.

## Owed

A PC build of Aspen 0.67.1 through the chain (`tools/ship_track.sh aspen`). It should show severe 0 on the built
kn5's gate OBJ, the build log's `[fold pads] discs at 0/1 apexes ...; road_profile.fold_pads false` line, and the
rest of drive_test no worse than above. Then Kevin's drive through the final hairpin. Status moves on after that.
