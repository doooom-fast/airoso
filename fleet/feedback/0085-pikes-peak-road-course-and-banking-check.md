---
id: 0085
title: Pikes Peak — the banking checked on the built deck; the road course researched, measured where the disk allows, not built
status: open
scope: tracks/pikes-peak, tracks/pikes-peak-lm
layer: project
train: -
---

## Request (Kevin, 2026-11-07)

> "Also; pikes peak is an oval yes but also it has a road course we're supposed to be building in, that takes advantage of
> the existing oval. I also want to make sure our banking there is accurate"

Standing rule: "I just want real". Branch `claude/pikes-peak-road-course`, based on `cf401bf4` (the head the PC built and
installed `pikes_peak_international_raceway_lm` 0.1.0 from).

## Part 1: the banking is accurate (on the built deck)

**The deck read.** `pikes-peak-lm` 0.1.0 rebuilt on the Mac from an EMPTY workshop at `cf401bf4`
(`SHIP_PROJ=<empty> AIROSO=<this worktree> ENG=<snapshot scripts + vendor + airoso assets/textures> bash tools/ship_track.sh
pikes-peak-lm --no-install`, Blender 4.2.9). ENG's textures md5-checked against REFERENCED.md5: 50 of 54 match; the four
that differ (`pine_leaves`, `poplar_bark`, `poplar_leaves`, `street_lamp_new`) are Lake Murray's and none is in this kn5
(its textures: asphalt_cracked x2, building x2, concrete_barrier x2, ground_dry, line_white). SHIP OK; every gate record
(`drive_test.full.json`, `audit.json`, `kn5_ground_check.full.json`, `edge_report.json`, `lm_intake.json`,
`crossfall.lm.json`) byte-identical to the committed 0.1.0 records; kn5 20,083,052 B as installed (md5 b01cca4f…).

**Station by station, the kn5's own gate OBJ against the 2018 lidar** (`tracks/pikes-peak/source/lidar/built-deck-check/`,
`bank_check.py`; the built deck's plane over the survey's own band, centre +-6.5 m, at each of the 556 survey stations,
keyed by position):

| | mean | rms | worst |
|---|---|---|---|
| built vs the raw lidar fit | +0.003 %-pts (+0.001 deg) | **0.050 %-pts (0.028 deg)** | -0.217 %-pts at s 1305 (built 17.00 %, lidar 16.79 %) |
| 0077's plateau windows vs the raw lidar | -0.18 %-pts | 0.65 %-pts (0.36 deg) | -2.27 %-pts at s 666 (window 16.72 %, lidar 14.45 %) |

The survey's own noise: raw minus its smoothed line rms 0.048 %-pts, station-to-station sd 0.09 %-pts. **The built deck is
inside it everywhere; nothing to fix.** The LM move did not carry 0077's windows: `lm_intake.crossfall` takes the survey's
per-station line (`crossfall.json`) itself, 13x closer to the lidar than 0077's plateaus.

- Outside edge up: 556 of 556 stations (CCW, every turn a left-hander).
- Plateaus, built / lidar: turns 1-2 17.17 / 17.17 % (9.74 deg); turns 3-4 16.95 / 16.96 % (9.62 deg); front stretch
  13.11 / 13.11 % (7.5 deg), its dogleg 12.96 / 12.96 % (7.4 deg); back stretch 6.17 / 6.16 % (3.5 deg).
- Ramps: |bank| crosses 15 % at s 198 / 660 / 1032 / 1497 built against 201 / 660 / 1032 / 1497 lidar; 9 % at 738 / 954 both.

**Constant across the width, as far as the lidar on disk reaches.** The raw points are not on disk (the G10 streamed them
and kept the fits), so no new band fits. A second fit of the same 2018 class-2 returns exists: `wall_right.json`
`road_slope_pct`, a 3 m band from the centre toward the wall. Against the 13 m plane (`prog_bank.py`): mean -0.10, median
-0.07 %-pts (p10 -0.58, p90 +0.36); turn plateaus +0.03 / -0.13. No steepening toward the wall. The 13 m plane's residual
sd (1.21 cm median) caps any curvature across it at 2.5 %-pts. The built deck is one plane too (inner minus outer half rms
0.006 %-pts).

**The inside edge is wrong, and it is not a banking error.** Off NAIP 2023 0.3 m (`source/road-course/inner_edge.py`,
`inside_edge.naip.json`, `still_oval_inside_edge.jpg`): the oval's pavement runs a median **18.3 m** inside the port's
centre line (p10 15.9 m), **11.4 m past the built lane's left edge** (p10 8.6 m; turns 1-2 10.8 m, turns 3-4 13.1 m,
back stretch 8.6 m, front stretch 11.0 m). Wall face to inside edge ~25 m: the
published 60-71 ft (18.3-21.6 m) racing surface (racingcircuits.info) plus an apron. Its slope is unmeasured (the survey
band stops 6.5 m inside the line), so it is NOT built here: carrying the 17 % plane 11 m further in would invent the
apron [owed: the lidar read below].

## Part 2: the road course

**What it is** (sources in `tracks/pikes-peak/source/road-course/README.md`): 1.289 mi / 2.074 km (Wikipedia) or 1.315 mi /
2.116 km (racingcircuits.info), "1.3-mile interior road course" (SCCA), 9 turns, counter-clockwise, Turn 1 the long banked
oval turn and eight turns in the infield (LapMeta, the-fastlane: search snippets, both pages refuse fetches
[unverified at the source]). No corner names found.

**Measured on disk (NAIP 2023 0.3 m, `still_road_course_candidates.jpg`):**
- the course leaves the oval on the back stretch: a diverge lane from s 947 (bank 4.9 deg) separating behind a gore by
  s 1037 (8.9 deg); a CCW car can only leave here;
- it rejoins at the end of turns 3-4, **s 1344, on the full 9.8 deg bank, ~14 m inside the built lane's left edge**, on the
  oval's unbuilt inside pavement;
- the infield's newest pavement is one loop between them, **623.6 m** (`infield_network.naip.json`, centre line by eye on
  the masked crop, ~1-2 m [unverified]). With the oval's 1,263 m that is **1,887 m, 187-229 m short of the published
  length**: the lap also takes the older S-curve section or the skidpad lot, which the aerial cannot decide.

**Not built**, for two reasons, both data not on disk:
1. **The route.** Three plausible infield routes, none confirmed. L1: a guessed line named after the real course is a
   defect. Needs the published map (below) or Kevin's word.
2. **The join.** The NW junction stands on the oval's inside 14 m, whose cross-slope nobody has measured; the infield's
   ground is the port's 40 m 3DEP grid. Welding a road onto a 10 deg bank onto an invented apron is the hard part built
   on a guess.

So no 0.2.0, no ship. The oval's gates are unchanged (nothing in the build changed):

| `pikes-peak-lm` | LM 0.1.0 (PC record) | Mac rebuild at cf401bf4 (this entry) |
|---|---|---|
| chain | SHIP OK | SHIP OK |
| drive_test (full): soft top / severe / bumps /km / kinks /km | 0 / 0 / 0 / 0.0 | 0 / 0 / 0 / 0.0 |
| gated drops (far ledges) / obstructed | 0 (37) / 0 | 0 (37) / 0 |
| audit_mesh | CLEAN | CLEAN |
| verify_kn5 / --inis | PASS / PASS | PASS / PASS |
| kn5_ground_check | PASS, 0 / 1,211 over 5 cm | PASS, 0 / 1,211 over 5 cm |
| house_seat | PASS (0 buildings) | PASS (0 buildings) |

## Lake Murray unchanged

`git diff origin/claude/fleet-lm-engine -- tracks/san-diego-lake-murray` is empty (this branch's base `cf401bf4` is an ancestor of
`fleet-lm-engine`; this branch adds only this entry and `tracks/pikes-peak/source/` files). No `scripts/` or `tools/` file changed, so no trim A/B was needed. Tests (`python tests/run_tests.py`,
`python` = airoso's venv on PATH): **1,233 passed, 6 failed**, all six from the known list (draft_equiv x5, registry_moves
x1); the known bench_pad pair is not in this base's suite (`cf401bf4` predates it).

## Owed (not on disk; nothing downloaded)

1. **The course map**: SCCA's `https://www.scca.com/wp-content/uploads/2026/02/trackmap_Pikes-Peak-International-Raceway.webp`
   (one image, size not read), a selection aid for which infield roads (never traced, L1). Or Kevin names the route.
2. **The 2018 lidar over the oval's inside half and the infield** (USGS 3DEP `CO_Eastern_ElPaso_2018` EPT, as the camber and
   wall surveys read it on the G10): the apron's cross-slope (then the inside edge can be built), true narrow-band fits
   across the banking, the infield ground and kerb heights. Size [unverified estimate] 30-80 MB for a ~600 x 700 m box.
3. **OSM raceway ways in the infield**: one Overpass query (a few kB).

Then the build this entry stops short of: the oval's inside pavement on its measured slope; the infield road as connectors
(`connectors.local.json`) welded at s 947-1037 and s 1344; a race layout on a stitched lap (`race.laps`, `layouts[].lap`)
on the one kn5 (L8); kerbs where NAIP / lidar show them; every gate on every layout; version 0.2.0.
