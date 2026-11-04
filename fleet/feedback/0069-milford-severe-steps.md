---
id: 0069
title: Milford's severe steps are one corner, an apron traced as road and a ribbon row that twists
status: fixed-awaiting-rebuild
scope: tracks/milford-road-course (data + config); engine opt-in road_profile.ribbon_cols, byte-identical for every other track
layer: project
train: -
---

## Symptom

Milford 0.4.0, installed, every gate green: drive_test reads 26 severe steps and 30.99 slope kinks per km, the worst of
the circuits. Not yet reported from the seat. Kevin's bar is that a track "drives and looks really good".

## Evidence

Mac draft of origin/main `eaf85b0` (terrain-mirror fix in; `build_mesh` then `drive_test` on a copy without `loop.blend`):
severe 26, kinks 30.99/km, bumps 2.45/km, apron steps 77. The drive tested the committed `gate_centerline.json`, which is
within 8 mm of the engine's own swept line.

- **Where.** All 26 severe steps, all 12 bumps, all 77 apron steps and 141 of the 152 kinks are at s 975-1025. The
  rest of the kinks are 4 at s 350-375 (the NW corner) and 7 at s 750-800 (the U-turn). Severe steps are on the centre
  wheel pair (±0.75 m): 22.2 cm at s 1001, 20.4 cm at s 1000, 17-18 cm at s 1003-1004. The kinks are on the third-line
  paths clamped to ±6 m (72) and the centre pair (40).
- **The corner.** The left-hander about 1 km in, heading south then north-east, descending 15 % at the apex. On the
  traced line it is 21.4 m wide around an 11.4 m radius (half-width / radius 0.93; nowhere else on the lap over 0.53).
- **What is under it.** No kerb, pad, fold bowl, bridge, splice or banking is involved: `flat_zones.json` and
  `bridge.spans.auto.json` are empty, no fold plateau fires, and Milford builds flat. The 1ROAD ribbon on its own,
  rebuilt from `finished_centerline` and walked the way drive_test walks it, reproduces the 26 severe steps to the
  millimetre (22.2, 20.4, 17.8, 17.6, 17.4, 17.2 cm).
- **The width.** In NAIP 2022 (`source/naip_2022_mrc.jpg`, on its true extent) the road at the apex is about 11 m of
  asphalt. Outside it, behind a joint line, is a pale concrete run-off apron. The trace scanned both as pavement. At
  fixes 395-409 the stored width is 17.1-21.4 m, and the centre (the scan's middle) sits on the asphalt's outer edge,
  about 5 m outside the road's centre. The inner edge, centre + w/2, is right: it lands on the inner edge line.
  `to_fixes.py` drops scans over 22 m as aprons. In the squashed frame this one read 15.7 m, so the rule never fired.
  `unsquash_frame.py` then scaled it by 1.357 to 21.4 m.

## Mechanism

Two parts, both needed.

1. **The source data (project).** The apron makes the ribbon 21 m wide on an 11.4 m radius. Its inside edge bunches to
   within 1.1 m of the turning centre, and each 3 m row there is 0.3 m long.
2. **The ribbon row (engine).** `ribbon.road_ribbon` with `cols=1` makes each row one quad. On a curve that descends,
   the quad's two radial edges are horizontal lines at different heights that are not parallel, so the quad cannot be
   planar. Its diagonal (`l0`-`r1`) splits off a sliver at the inside. That sliver carries about half of the row's
   0.44 m drop in its last 0.17 m before the next row line, at the centre path's radius, which is a step every 3 m.
   Worked through on the s 1,000 geometry, it predicts the 22 cm the drive test reads.

   `road_profile.ribbon_cols` already existed for the same kind of twist on camber ramps (Exotics T2, Pikes Peak).
   `build_mesh` honoured it only on a banked road.

The data fix alone narrows the corner to 11.3 m but leaves the twist on a 13 m radius at 13-14 %. Walking the surface
with a continuous normal (below), the bare ribbon still has 24 severe steps at s 990-1000. With 4 columns it has 0.

## Fix

- **`tracks/milford-road-course/source/trace/apron_corner.py`.** A one-run correction, like `unsquash_frame.py`. Fixes
  383-424 keep their inner edge and take the road's own width: 11.28 m, the median of the 25 traced fixes either side.
  Each centre moves (w − 11.28)/2 toward the inside, up to 4.71 m at fix 401. The move is averaged over ±4 fixes and
  eased in and out over 8, because the stored width jumps 4 m between fixes 394 and 395 where the scan's centre does not.
  Against the image, the new centre at the apex is within about 0.5 m of the middle of the asphalt band. The edges sit on
  the inner edge line and the apron joint.
- **Data regenerated** with gps, elev and project, which round-trip byte-identically on the unchanged source:
  `centerline.geojson`, `centerline.elevation.json`, `centerline.local.json`, `corridor.elev.json` (the lap now has 1635
  points, so the corridor cache missed and was re-sampled) and the two SVGs. `heightfield.npy` is kept as committed: a
  re-sample moved 6 of 875 nodes by up to 0.10 m, which is 3DEP service noise and not this fix.
- **`scripts/geometry/build_mesh.py`.** `ribbon_cols(road_profile)` now applies `road_profile.ribbon_cols` wherever it
  is declared, not only on a banked road. This is byte-identical for every track without the key. The two tracks that
  declared it before (Exotics, Pikes Peak) are banked, so they already built columns, and a test pins that. No gate
  threshold or wiring changed, so GATES-CHANGELOG is not touched.
- **Milford config.** `road_profile.ribbon_cols: 4`, the source `_note` amended, version 0.4.0 → 0.6.0 (0.5.0 is the
  PC's rebuild from before this fix).
- **Test.** `tests/geometry/test_ribbon_cols_graded_corner.py`, stdlib only:
  - a 120° left-hander, R 12 m, 20 m wide, 15 % down, unbanked: one quad per row reads a 22 cm centre-pair step, four
    columns read 2.8 cm;
  - the decision function;
  - every track that declared `ribbon_cols` before 0069 is banked.

## Before / after (Mac drafts: build_mesh + drive_test + audit_mesh, the PC's chain not run)

| | baseline (main) | data fix only | data fix + 4 cols (this branch) |
|---|---|---|---|
| severe steps | 26 (5.3/km) | 43 (8.78/km) | **15 (3.06/km)** |
| bumps /km | 2.45 | 4.9 | **0.2** |
| slope kinks /km | 30.99 | 26.75 | **16.13** |
| apron steps (reported) | 77 | 33 | 28 |
| vertex bumps (reported) | 23 | 27 | 25 |
| ground on top / obstruction / floating / daylight / undrivable / fold bumps | 0 / 0 / 0 / 0 / 0 / 0 | same | same |
| excursion drops (gated) | 0 | 1 | 1 |
| far ledges (reported) | 29 | 25 | 25 |
| replication vs 3DEP, max | 0.21 m | 0.35 m | 0.35 m |
| audit_mesh | CLEAN | — | CLEAN |
| lap | 4904.4 m | 4898.0 m | 4898.0 m |

Notes on the table:

- **"Data fix only" reads worse.** The narrower road brings the third-line paths (w/3 − 0.75 = 3.01 m) inside the 3.5 m
  apron exemption, so steps that used to be filed as apron steps now count as severe. The 4 columns are what take the
  surface step out.
- **The 15 severe steps left are the gate's own sampling, not the surface.**
  - All 15 are on the inner third-line path (+3.01 m) at s 990-1000.
  - drive_test offsets each wheel path along a piecewise-constant segment normal. On a 13 m radius that normal turns 13°
    at each vertex, so a path 3 m inside jumps about 0.7 m back along the road on a 17 % inner grade, which is 0.08-0.12 m.
  - The bare 4-column ribbon walked that way gives exactly these 15 (11.8, 11.4, 10.9 cm …).
  - The same ribbon walked with a continuously interpolated normal over s 950-1060 gives 0 severe steps and 0 kinks.
  - For the record, the same continuous walk gives 50 severe on main's surface and 24 with the data fix alone.
  - The gate is unchanged; this is reported, not exempted.
- **The excursion drop is 0.12 m at s 3752.5, −12.5 m out.** That is right at the tarmac threshold and 2.7 km from the
  corner. The fix changed the origin (centroid, 0.3 m) and re-sampled the corridor, and this is what moved under it.
  Installed 0.4.0 had one of the same size elsewhere (s 2700, 0.13 m). The PC chain re-samples the corridor too, so it
  will see the same thing.
- **The replication max is at s 1075-1078, just past the corner.** The line now runs on the asphalt, over a 0.35 m hollow
  in raw 3DEP that the profile's despike and smoothing (unchanged) take out.

## The lidar camber survey (origin/claude/lidar-camber-survey) and this corner

- Milford's draft is built flat (`cambers: []`, no `crossfall.json`), so no step or kink here comes from built camber
  changing.
- The survey's worst roll change (6 % per 30 m at s 984) and its off-camber +8.5 % run starting at s 1005 are both at
  this corner. They were fitted on the old `finished_centerline` with a 5 m half-width, and at s 995-1010 that line was
  on the asphalt's outer edge with the apron beside it. Those readings may be partly the apron and the joint, not the
  road's cross-slope.
- The survey should be re-fitted on this branch's line before anyone reads banking off it. Applying it is Kevin's call;
  nothing here applies it.

## Not done / owed

- **The NW corner** ("onto the wide apron", s 330-430: 21.7 m at R 19.6, half-width / radius 0.53) and other wide runs
  (s 2610-2665, s 4023-4723 at 17-19 m) may carry the same apron-as-road reading. They produce 4 kinks and no severe
  steps today. Not touched, because the colour scan is noisy there (tree shadow, other pavement); check them by eye.
- **Fleet question.** One quad per row twists on any graded curve, so `ribbon_cols` could become the default. That
  would change every track's mesh and needs its own fleet rebuild. It stays opt-in here.
- **Proof owed:**
  - a PC chain build of Milford 0.6.0 from this branch, all four gates on the built kn5;
  - Kevin's drive through the s 1,000 left-hander.
