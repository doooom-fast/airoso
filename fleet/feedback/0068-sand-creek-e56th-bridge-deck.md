---
id: 0068
title: Sand Creek's E 56th bridge deck was held 0.4 m under the real one; it now follows the lidar-measured deck
status: fixed-awaiting-drive
scope: tracks/sand-creek (engine option general: capture.bridges[].profile_m)
layer: project + engine (scripts/capture/evidence.py, scripts/geometry/build_mesh.py)
train: -
---

## Evidence (2026-11-03, analysis only)

`tracks/sand-creek/source/lidar/e56th_bridge_deck.md` (+ .json, .png): the 2020 USGS source lidar's bridge-deck points
(ASPRS class 17) over Sand Creek on E 56th Ave, against 0.31.1's finished line.

- The real deck runs 2,404 to 2,522 m on 0.31.1's finished line (118 m). The declared span (center 2485, len 100) read
  as 2,435-2,535 by the gates and 2,421-2,521 finished by `level_bridge_decks`, which reads it on the draft line (below).
- The deck is crowned 0.29 m and sat a median 0.41 m (max 0.50 m at 2,464) above our deck, which
  `evidence.level_bridge_decks` holds as ONE straight grade between the bank crests: bare earth has no deck in it.
- The east approach ground is 0.13-0.23 m above our road out to 2,560 m. The west approach is within 0.10 m.
- No step at either abutment: the deck is within 4 cm of the approach ground at both ends.

## Fix

- **Engine, `capture.bridges[].profile_m`** (opt-in, per bridge): `evidence.deck_profiles` /
  `evidence.apply_deck_profiles`, called at the end of `build_mesh.finished_centerline` (shared with build_env).
  `profile_m` is `[[d, height], ...]`:
  - `d` = metres from the bridge's START, `center_m - len_m / 2`, along the FINISHED line (the line build_mesh sweeps
    and writes to `data/finished_centerline.json`; the gates, the lidar crossfall and road_profile dips use the same
    one); negative before the start (an approach point);
  - `height` = absolute, the 3DEP vertical datum (`y + origin elev_m`), as the lidar reads it: the real road's height,
    true on any line over the same deck.
  Inside the profile the road follows it, linearly between points; outside, the difference at each end eases back to
  the road over `profile_ramp_m` (default 20 m, [invented]) with a raised cosine, so no step and no grade break.
  Wraps on a closed lap (L13). A bridge with no `profile_m` runs nothing: every other track and bridge is byte-identical.
  `finished_centerline` refuses a profile without the origin datum (it would lay it at the wrong height).
  Test: `tests/capture/test_deck_profile.py` (stdlib).
- **Sand Creek, E 56th**: `center_m` 2463, `len_m` 118 (the deck 2,404-2,522 m on 0.31.1's finished line; was 2485 /
  100); `profile_m` from d = -4 to 156 m every 5 m: the note's recommended profile (d -4 and 121-126 approach ground,
  1-116 the cubic fit to the deck medians, rms 0.9 cm) plus the east approach to d 156 (2,560 m) from the lidar's
  ground medians. Version 0.32.0.
- No gate threshold or wiring changed: nothing in GATES-CHANGELOG. The crossfall was not rerun (the line did not move;
  `spans_m` [[2540, 2740]] holds the measured camber at the 56th Ave turn as before, and the tool's on-deck flag,
  which reads the span, only matters inside a camber span).
- Also on this branch: `tools/lidar_crossfall.py` passes `context=https_context()` inline, which
  `tests/net/test_https_everywhere.py` requires (it failed on the camber branch).

## Station frames: what to re-key after a line change

- **`profile_m` needs nothing**: it is measured from the bridge's start. Re-key the bridge by finding the deck's start
  on the new finished line (the class-17 points start at the old 2,404 m; `e56th_bridge_deck.json` has them by
  station) and setting `center_m = start + 59`. The heights stay.
- **`center_m`/`len_m` are read in two frames.** `level_bridge_decks` reads them on the DRAFT line
  (`centerline.local.json`), drive_test, kn5_ground_check, build_mesh's lip exemption and lidar_crossfall on the
  FINISHED line, which was 14 m shorter at E 56th on 0.31.1 (23 m by the lap's end). The new span is the finished-line
  one; on the draft line it falls 14 m early, which now only moves the approach grade's bank-crest anchors (simulated:
  the west approach moved at most 1.1 cm); the deck itself is the profile. The Quebec and E 46th-leg spans were declared
  before that difference was known and are not re-derived here.
- `build_mesh._bridge_detector` compares the finished line's height at finished station s with the raw 3DEP ground at
  DRAFT station s (`raw_ground` is keyed off `raw_pts`), so its auto spans (`bridge.spans.auto.json`, 2,429-2,528 m at
  E 56th) sit about 14 m downstream of the real creek. Not changed: it moves every track's spans; worth its own entry.

## E 45th Ave: superseded

The same day's line check on E 45th Ave (`source/lidar/e45th_line_check.md`, merged here as evidence) found the line on
the pavement but on the north edge line of a three-lane one-way at 6,320-6,420 m, 2.5-7 m from the curb above the creek
drop; the 2023 NAIP aerial, OSM and the lidar all put the carriageway centre south of it there (OSM +1.6 to +3.1 m, the
aerial +2.2 to +5.4 m), none past 6,440. A +1.5 m nudge through a `source.kml_overrides` was built and then dropped
unshipped: Kevin chose to re-source Sand Creek's whole line from OpenStreetMap instead ("Re-source from OSM"), which
supersedes it. The E 56th deck values above are keyed to survive that.

## Before / after (Mac draft: build_mesh + drive_test, no loop.blend)

Baseline: 0.31.1 (camber branch) + main (the terrain-mirror fix); after: this branch. Same commands on a copy of
`tracks/sand-creek` each: `scripts.geometry.build_mesh`, then `scripts.geometry.drive_test`.

The road: the finished line's plan is identical; its height changed on 77 vertices, 2,346-2,576 m, nowhere else.

| lidar minus built (m) | before: median (min, max) | after |
|---|---|---|
| west approach 2,380-2,404 | +0.03 (-0.03, +0.13) | -0.02 (-0.04, 0.00) |
| deck 2,404-2,522 | +0.41 (+0.15, +0.50) | 0.00 (-0.03, +0.02) |
| east approach 2,524-2,560 | +0.18 (+0.09, +0.25) | 0.00 (-0.01, +0.01) |

drive_test, both layouts (race and street read the same numbers):

| | before | after |
|---|---|---|
| fail | false | false |
| severe_steps | 1 | 1 |
| kinks_per_km | 15.61 | 14.89 |
| steps_per_km | 2.79 | 2.79 |
| fold_bumps (reported, not gated) | 21 | 23 |
| vertex_bumps | 9 | 9 |
| excursion_drops / far ledges | 4 / 10 | 4 / 10 |
| worst_gated_excursions | 7,950.5 (0.35), 8,102.7, 9,451.8, 3,001.5 | the same |
| soft_top_in_lane | 0 | 0 |

By stretch: outside 2,380-2,580 every per-station list (steps, severe steps, kinks, fold and vertex bumps, gated
excursions, apron steps and bumps, soft top, obstructions, floating furniture, daylight gaps) is unchanged, including
6,250-6,550. Inside 2,380-2,580: kinks 40 -> 33, apron steps 4 -> 2, apron bumps 26 -> 20; fold bumps 4 -> 6, the one
worsening: the -6 m wheel path where it runs backwards through the corner fold onto the bridge at 2,381-2,384 (the
road turns about 45 degrees there), 0.053 / 0.046 m -> 0.040 / 0.056 / 0.032 m. That fold reads the west ramp,
which lifts the road from 0 at 2,380 to +0.10 m at 2,400 to meet the measured approach; the readings are reported,
not gated, and the bump was there before.

## Proof owed

- Sand Creek 0.32.0 through the chain on the PC, every gate on the built kn5 (not built or installed here); after the
  OSM re-source, `center_m` re-keyed as above.
- Kevin's drive over the E 56th bridge into the 56th Ave turn: the deck now crowned and 0.4 m higher, the east approach
  0.2 m higher, no step at the abutments.
