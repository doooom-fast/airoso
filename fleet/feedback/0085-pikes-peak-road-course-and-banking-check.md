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

## Re-trace (2026-11-07): edges measured, not drawn

Kevin, on the first overlays: **"Those tracings aren't very accurate."** Then: **"Follow curbs and road wear, it's easy
for human eye"**, **"There are smaller variations on there too"**, **"One seems to avoid the issue oval"** and **"It just
avoid the oval, like an interior track only version"** (an infield-only layout; reading (a)). Standing rule: "I just
want real". Tools and data in `tracks/pikes-peak/source/road-course/` (README "Re-trace"); the eyeball files kept as
`*.eyeball.json`. Stills: `/Volumes/Drive/codex/pp_work/retrace/`. Nothing downloaded, nothing built.

**1. Registration** (`register_wall.py`, `registration.json`). The wall's concrete top on NAIP (its road-side edge,
sub-pixel) against the lidar face at 374 of 556 stations, fitted `offset = b + dE nE + dN nN`: **the image sits 0.42 m off
(E +0.09, N -0.41 m; block-bootstrap sd 0.04 m each)**, bias b -0.01 m, residual rms 0.16 m (p50 0.12, p95 0.32). Over a
pixel, so applied to every NAIP coordinate. Caveat: the band is the wall's TOP, 1.27 m up; relief displacement of a
1.27 m top is a uniform shift too, so 0.42 m is an upper bound on the ground's misregistration in that direction;
nothing on disk separates them (the lidar ground returns are not on disk).

**2. The infield pieces** (`pieces.py`, `retrace.py`, `infield_pieces.naip.json`). Each piece is named by 2-11 via
pixels (which road); its geometry is measured: pavement score (grey asphalt, or smooth texture for the older dusty
asphalt that has dirt's colour; green run-off paint excluded), both edges every 0.5 m at the score's steepest fall
(sub-pixel), a kerb or white edge line within 1.5 m taking precedence (asphalt edge = its inner face), robust smoothing
splines (outliers dropped at max(0.35 m, 3 MAD-sigma)), centre = midline, then again on that centre. Kerb runs traced
along each fitted edge (red blocks, or white blocks in a 1 m rhythm). Residual = seen edge point to fitted edge.

| piece | length m | width m p50 (min-max) | residual L / R p50-p95 m | inferred (not seen) | kerb on L / R |
|---|---|---|---|---|---|
| ne_lane (oval diverge -> hairpin top) | 150.4 | 12.2 (11.9-22.3 at the diverge) | 0.11-0.35 / 0.10-0.33 | 16 m: diverge mouth, weak | 29 / 42 % |
| hairpin_w | 56.0 | 12.4 (12.0-20.3 at mouths) | 0.13-0.44 / 0.13-0.54 | 0 | 100 / 26 % |
| diag_n | 25.9 | 12.4 (12.0-12.8) | 0.06-0.24 / 0.13-0.47 | 0 | 0 / 75 % |
| diag_s | 73.8 | 12.3 (12.0-15.9) | 0.08-0.25 / 0.08-0.24 | 4 m | 0 / 10 % |
| n_road (NW junction -> hairpin top) | 139.3 | 12.1 (11.6-23.0) | 0.10-0.35 / 0.08-0.26 | 8 m | 7 / 16 % |
| arc_nw (kerbed sweeper) | 82.8 | 12.6 (12.3-12.8) | 0.05-0.13 / 0.09-0.57 | 2 m | 0 / 96 % |
| c_road (older) | 77.3 | 10.3 (5.1-14.5) | 0.24-0.65 / 0.18-0.71 | 29 m: S-curve mouth, weak | 9 / 0 % |
| west_n | 27.3 | 18.9 (14.4-20.3, junction-wide) | 0.21-0.59 / 0.11-0.32 | 4 m | 30 / 29 % |
| bottom | 142.4 | 14.0 (11.7-20.1) | 0.22-0.72 / 0.26-0.65 | 23 m: paddock side, weak | 41 / 6 % |
| s_curve (older) | 132.0 | 7.8 (4.0-11.6) | 0.21-0.69 / 0.23-0.65 | 30 m: weak (faded kerbs, dust) | 13 / 4 % |
| par_lane (older) | 196.3 | 7.8 (5.4-9.7) | 0.22-0.62 / 0.19-0.80 | 66 m: weak (dust) | 17 / 10 % |
| ring_nw / ring_ne / ring_s (the lot ring) | 51.3 / 121.6 / 264.0 | one edge: the lot's interior is paved; driven band 3.2 / 3.4 / 6.0 m wide | 0.16-0.45 / 0.09-0.22 / 0.18-0.72 (outer edge) | 2 / 46 / 140 m (grey vs tan concrete is a weak edge) | 48 / 0 / 0 % |

The newer pieces are 12.1-12.6 m wide (40-41 ft) and fit to 0.05-0.13 m p50; the older dusty pieces 0.18-0.26 m p50 with
a third of their edge inferred. Kerb detection misses faded S-curve kerbs (white-only blocks): their edges are found,
labelled edge-surface, not kerb.

**3. The oval's inside edge** (`inside_edge.naip.json`): 1,666 stations, 1,001 seen; residual p50 0.16, p95 0.66,
max 1.88 m. 21 junction / opening runs bridged, never followed (pit exit and service roads s 129-397, s 650-726, the NE
diverge s 945-995 and 1018-1034, the NW merge s 1309-1377 and 1450-1481); 9 short inferred runs. Bridges are straight in
width, so the edge kinks where a bridge meets the spline (min radius 0.3 m at a bridge end).

| section | wall face -> inside edge m (p50, seen) | apron line (painted) from edge m | wall face -> apron line m |
|---|---|---|---|
| front stretch | 23.7 (23.6-24.9) | 3.1 (27 stations) | **20.5** |
| turns 1-2 | 25.9 (25.6-26.0) | not found | - |
| back stretch | 23.3 (22.8-25.7) | 3.6 (28 stations) | **20.4** |
| turns 3-4 | 25.8 (25.3-35.8; 34-36 m at s 1380-1450 where a second paved lane runs inside) | 6.1 (179 stations) | **19.7** |

Wall to apron line 19.7-20.5 m = 65-67 ft, inside the published 60-71 ft; the apron 3-6 m beyond it. The oval's
mid-surface line (wall face to inside edge, halved) laps **1,622.8 m**; 15 ft off the inside edge 1,573.7 m (published
1.0 mi = 1,609 m); the port line 1,665.9 m.

**4. Wear and the layouts** (`routes.py`, `layouts.naip.json`). Wear index = the median, over a piece's sections, of
the darkest band's darkening against that section's clean (80th-percentile) asphalt. Ranked: lot ring 0.21-0.26
(inflated: the ring's asphalt is darker than the lot interior it is compared with), arc_nw 0.165, bottom 0.165, west_n
0.126, s_curve 0.125, diag_n 0.102, hairpin_w 0.094, n_road 0.082, diag_s 0.081, ne_lane 0.069, par_lane 0.059,
c_road 0.055. **Direction from wear is NOT established**: the apex-shift read (late apex = travel direction) flipped
for s_curve and arc_nw when the centre's smoothing changed by 2 m; it is reported per piece, not relied on.

Oval share of a CCW road-course lap on the mid line: NW merge (s 1,317.7) -> NE diverge (s 957.3) = 1,262.4 m.
Lap = pieces' centre lines + oval share, +-6 m per junction [invented allowance].

| id | layout | lap m | vs 2,074 / 2,116 | wear |
|---|---|---|---|---|
| RC-A | oval + lane, hairpin, diag, lot corner, bottom, west road, sweeper (the previous "newest loop") | 1,872 +-54 | -202 / -244 | 0.128 |
| RC-B | RC-A with the S-curve and C road west in place of the west road | 2,038 +-60 | -36 / -78 | 0.122 |
| RC-C | RC-A with the parallel lane and the lot ring's north-east side in place of diag south | **2,092 +-60** | **+18 / -24** | 0.129 |
| RC-D | RC-A round the lot ring the long way | 2,207 +-66 | +133 / +91 | 0.160 |
| RC-E | oval + lane, hairpin, N road back (bypass) | 1,574 +-18 | -500 / -543 | 0.075 |
| IF-1 | infield only: RC-A's infield closed by the N road over the NW apron | 599 +-48 | - | 0.132 |
| IF-2 | infield only: C road, west road, bottom, lot corner, diag | 398 +-42 | - | 0.133 |
| IF-3 | infield only: C road east, S-curve, bottom, lot corner, diag | 442 +-36 | - | 0.142 |
| IF-4 | infield only: N road, hairpin, C road, sweeper | 355 +-30 | - | 0.097 |
| LOT-1 | the lot ring alone (reading (b); kept because its wear is the heaviest) | 437 +-24 | - | 0.227 |

RC-B and RC-C both sit within the junction uncertainty of the published length; RC-A is ~200 m short. The wear does not
separate B from C: the S-curve carries twice the parallel lane's darkening, but the lane and C road are the least worn
pieces either way. Which is the 1.3 mi course stays Kevin's call (or the SCCA course map, owed). Every infield-only loop is
assembled from the same pieces, ready to become `layouts[]` on one kn5 (L8).

**What would still improve it** (not on disk): the 2018 lidar over the infield and the oval's inside half would
(1) settle the 0.42 m shift between ground and wall-top relief, (2) give kerb heights and the dusty edges' true
positions (a 3-8 cm kerb step is a clean edge where NAIP has 0.2-0.7 m of dust-blurred residual), (3) measure the apron's
cross-slope. OSM raceway ways would at best name pieces; at their usual 1-3 m accuracy they would not improve a 0.1-0.3 m
edge.

## Route from the published maps (2026-11-07)

Kevin: **"Why aren't you using actual track maps?"**, **"Stop guessing"**, then on his own strokes **"Do them as
published, i just drew shape"**. Two maps, downloaded on his word, not committed (`/Volumes/Drive/codex/pp_work/maps_dl`):
SCCA Track Night in America (scca.com, 2026; 9 corners, start/finish arrow, pit entry / exit) and racingcircuits.info's
road course "2017 to date" (T1-T9, arrows, unused pavement grey). Tool: `source/road-course/maps_route.py` ->
`route_from_maps.naip.json`, `still_route_from_maps.jpg`; working stills `pp_work/maps_route/` (`lot_band.jpg`,
`top_hairpin_refit.jpg`). L1 held: a map picks WHICH measured pieces, in what order and direction; every coordinate of
the route is a measured piece centre line, the lot band measured below, or the oval's mid-surface line. Nothing built.

**1. Registration** (each map's oval outline onto the 2018 lidar wall face, similarity ICP from every 10 deg start, both
handednesses; the S/F painted on NAIP and the infield's side choose between the near-symmetric fits):

| map | outline to wall face rms / p95 m | S/F miss m | infield labels miss m (chosen / mirror) | affine rms, axis ratio |
|---|---|---|---|---|
| racingcircuits.info | **0.62 / 1.09** | 1.4 | 65 / 227 | 0.47 m, 1.005 |
| SCCA | 6.9 / 11.4 | 6.5 | 39 / 278 | 2.7 m, 1.072 (drawn 7 % fatter one way) |

The mirror about the oval's short axis fits the outline equally (rms within 0.01 m, S/F within 1 m: the line is mid
front stretch); it puts the infield on the wrong side by 160-240 m, so the infield decides, not the outline.

**2. The pieces each map's line runs over** (per metre: nearest measured centre line, mode-filtered, runs under 20 m
dropped as junction flicker). **Both maps give the same route, in the same order and direction:** oval (S/F, turns 1-2,
back stretch) -> NE lane -> top hairpin -> diag north -> diag south -> round the skid pad lot the long way (north-east
side, east end, south side, west end) -> bottom road west -> west road -> sweeper -> NW merge onto the oval. That is
**RC-D** of the Re-trace's ten candidates. The RC line sits 0.43-1.02 m p50 from the newer pieces' centre lines (west road
2.8 m). SCCA's top hairpin is drawn as a loop out over the N road (12.2 m p50 off every measured centre line, read as
n_road): refit locally (`local_refit`, line within 50 m of the hairpin's top junction, proper similarity ICP onto every
infield centre line near it at once, blended out by 80 m): scale 0.983, -0.75 deg, its centre moved 23.4 m; 0.77 m p50 /
2.27 m p95 after. Then it reads ne_lane -> hairpin_w -> diag like the RC map. The RC line was not refit (0.57 m p50).
Registered, the maps' own lines measure 2,189 m (RC) and 2,186 m (SCCA).

**3. The lot.** Both lines run over open pavement there (4-12 m from the ring pieces, whose measured edge is the LOT's
outer boundary, not the driven road), so the driven band is measured (`lot_band`): cross-sections every 1 m along the RC
line through the lot, luminance smoothed 1 m across / +-4 m along (cracks and kerb gaps are 0.3-1 m), samples beyond the
lot's measured outer edge read as its interior; floor = darkest point within 6 m of the line; each side normalised
against its own surface (80th percentile 3-12 m out); limits at half depth; [unseen] when less than 6 grey levels below
either side, when 3-20 m wide fails, or when a limit jumps > 1.5 m off its 15 m running median.

| | |
|---|---|
| sections (RC line +-15 m) / in the lot | 361 / 331 |
| used: the longest run with no [unseen] gap over 5 m | **281 m (east end, south side, west end), 269 seen** |
| width p10 / p50 / p90 | 6.6 / **9.2** / 11.5 m |
| depth below the inner / outer surface (p50) | 30 / 32 grey levels |
| limit residual to its running median p50 / p95 | 0.06 / 0.66 m |
| [unseen] | 30 not 6 grey levels below both sides, 9 jumps, 2 too narrow: the lot's NORTH-EAST side, where the concrete carries no darker band |

The north-east side is therefore **bridged, not measured: 64.3 m straight** from diag south's end to the band's first
seen section, along the lot's straight north-east edge [inferred].

**4. The laps** (`route_from_maps.naip.json` `routes`, centre lines every 1 m; joins straight, gap listed):

| layout | pieces | lap m | joins (gap m) |
|---|---|---|---|
| **RC-D road course**, counter-clockwise (both maps' arrows), from the painted S/F | oval S/F -> NE 944.8, ne_lane 150.0, hairpin_w 55.0, diag_n 25.0, diag_s 73.0, lot band 289.6, bottom 142.0 (rev), west_n 27.0 (rev), arc_nw 82.0 (rev), oval NW -> S/F 317.6 | **2,217.8 +-54** | 9.2, 6.7, 6.2, 3.8, **64.3 bridge**, 6.4, 5.4, 5.8, 6.0 |
| **IF-K infield only** (Kevin's shape) | diag_n, diag_s, lot band, bottom (rev), S-curve (rev), C road east (c_road.b) | **760.3 +-36** | 3.8, **64.3 bridge**, 6.4, 2.2, 2.0, 4.9 |

RC-D against the published 2,074 / 2,116 m: **+144 / +102 m**. The maps' own registered lines (2,186-2,189 m) are as long,
so the difference is not the assembly. Most is the measuring line: the oval share here is the mid-surface line
(1,262.4 m); on a line 15 ft off the inside edge it scales by 1,573.7 / 1,622.8 to ~1,224 m, leaving ~+64 m against
2,116 [not resolved; the publishers' measuring line is not stated].

**Direction.** The road course: counter-clockwise, as both maps draw it. Kevin's strokes give shape only (his road-course
stroke runs the same pieces, drawn clockwise). **The infield-only layout runs the way the published road course runs on
the pieces they share** (diag north -> diag south -> the lot the long way -> bottom road west), then north up the S-curve
and east on the C road back to the diag; Kevin's infield stroke happens to run that way too. No map publishes an
infield-only course. One old listing (search snippet only) says Track Sprints run the infield in the reverse direction:
**unconfirmed** (no page reached), so not adopted.

**5. The corners** (each label: the map line's nearest point, then that point's station on RC-D from the S/F; labels
are printed 19-47 m off the line, so a station is good to a corner's length, not to an apex). The two maps number
different corners:

| corner on RC-D | racingcircuits.info | SCCA |
|---|---|---|
| oval turns 1-2 ("the longest corner") | **T1** s 299, **T2** s 529 | **1** s 220 |
| leaving the back stretch (NE diverge) | **T3** s 879 | **2** s 926 |
| top hairpin | **T4** s 1,119 | **3** s 1,152 |
| lot, east end | **T5** s 1,437 | **4** s 1,417 |
| lot, west end onto the bottom road | **T6** s 1,589 | **5** s 1,605 |
| bottom road | **T7** s 1,636 | **6** s 1,647 |
| bottom road, west end | **T8** s 1,704 | **7** s 1,743 |
| west road / sweeper | **T9** s 1,842 | **8** s 1,804 |
| NW merge onto the oval | - | **9** s 1,993 |

The racingcircuits.info map counts the oval's turns 1 and 2 separately and leaves the merge unnumbered; SCCA counts
turns 1-2 as one and numbers the merge. Same nine-plus corners, offset by one through the infield. On IF-K: RC T5-T8
(s 266 / 417 / 464 / 532 from the diag's start).

**Still owed before a build** (unchanged from above): the join onto the oval's unbuilt inside pavement (its slope is
unmeasured; the 2018 lidar), the infield ground (40 m 3DEP grid now), the lot's north-east side (a measured band, or
Kevin's word that the straight bridge is the driven line), and which measuring line the published 1.3 mi uses.

## The build (PC, 2026-11-08; Kevin, asked here: "Pikes Peak road course", then "Straight is fine" and "Oval + road course + infield")

Kevin picked this as the PC's next job; the option said the 2018 lidar for the oval's inside and infield would be downloaded
first (est. 30-80 MB), his pick the yes. Asked next: the lot's north-east side built straight along the lot's edge
(**"Straight is fine"**, so it is inferred, said so here), and the layouts (**"Oval + road course + infield"**: three on
one track; he was told the oval is widened to its measured width in this build). Branch `claude/pikes-peak-road-course-build`
= Sand Creek's engine head `34521fa` (the most capable engine: connectors, mouths, pads, ground patches) + this branch +
the lidar commit; the oval's 0.1.0 config rebuilt from an empty workshop on it is kn5_equiv to the installed oval
(tangents only, 1.8e-7) and every record equal but paths and two new null keys (`D:/k10-scratch/pp_ab`).

**1. The lidar** (`source/lidar/infield/fetch_infield.py`, `infield.summary.json`): CO_Eastern_ElPaso_2018 EPT, 38 nodes,
**7.5 MB** (the plan said ~13 MB at 9 B/pt; the estimate given to Kevin was 30-80), 789,608 points in E -284..300 /
N -352..320 m, ground 1.9 points/m2. Too sparse for a 3-8 cm kerb step; ample for planes. Raw LAZ and the npz stay on the
PC (`D:/k10-scratch/pp_lidar`).

**2. The oval's inside** (`inside_slope.py` -> `inside_slope.json`; per 3 m station of the 0.1.0 built line, class-2
points +-1.5 m along): the lane read itself first, -12.7 / -17.3 / -5.4 / -17.0 % by section against the G10 survey's
-13.1 / -17.2 / -6.2 / -17.0 (the read is sound). A continuous two-line fit across the inside (residual sd 1.2-2.9 cm):
**the bank's plane runs on past the built lane's left edge** (knee +4.75 T1-2, +5.25 front, +3.25 back, +7.25 T3-4,
+8.25 at the NW merge, p50) **at the lane's own slope**, then the **apron** falls -6.4 / -7.5 / -3.6 / -6.6 % to the NAIP
inside edge, 5.4-6.2 m wide. Wall face to knee 17.0-21.4 m (published 60-71 ft = 18.3-21.6 m): the built 12-15 m lane
was the racing surface's outer three quarters. The knee sits 0-3 m past the painted apron line. Where the two slopes
differ by under 1.75 %-pts (the back stretch s 885-906, -5.4 vs -4.0 %) the knee's place is noise (it wandered -1.75..+2.25
m) and is filled from its neighbours (`oval_surface.py`, 21 stations); carrying the plane 3 m on there is 4 cm. The ground
1 m past the inside edge stands level with the apron's edge (p50 +2 mm, p10/p90 -4 / +5 cm). The 0.1.0 deck stood
**+0.13..+0.34 m (p50 +0.22)** over the lidar ground under it (the assembler's lift is 0.10).

**3. The infield ground** (`infield_ground.py` -> `infield_ground.json`, 1 m DEM on the PC): the pieces' grades p50
0.3-1.3 %, max 4.1 % (the sweeper), cross-falls 1-2.4 %. The port's 20 m grid sat within 0.25 m under most pieces and
**1.3 m (n_road) / 1.8 m (arc_nw)** off near the NW junction, where it smears the bank.

**4. What the build changes** (every key opt-in; Lake Murray and every other track declare none):

| key / step | what |
|---|---|
| `lm_intake.edge_on_bank` (`tools/lm_engine_intake.py`) | the left edge onto the knee (smoothed per station), the right edge kept on the wall; the moved centre on the lidar plane's height; the banking's position keys move with the line |
| `edge_on_bank.apron` -> `route.edge_apron_file` | the edge strip's left side IS the measured apron (scripts-v021 `ribbon.curb_sidewalk(apron=)`, `build_loop_blend.edge_apron`): its width and fall per vertex, its lip on the measured ground. Without an apron the strip is the function before the change, byte for byte (`tests/geometry/test_v021_curb_apron.py`) |
| draft `apron_road` (`tools/apron_road_blend.py`) | those strip faces moved into `1ROAD_apron` (CURB keeps every vertex): engine-july's prep pins the ground under 1ROAD only and holds a 3 m band at the LANE edge's height then feathers 6 m; as CURB the apron's low lip would have had ground standing over it |
| `terrain.lidar_patches` "infield" + draft `ground_patch` | the oval's whole inside seated on the 1 m DEM (`make_ground_patch.py`: 90-point outline 0.5 m inside the bank's edge); `split_m` 3 (opt-in per patch; the tool's 1.5 m took the terrain 173k -> 552k vertices and the prep past 20 min) |
| `lm_intake.connectors_file` | the infield roads (`make_connectors.py`, below) carried by the port (the source track has none) |

**5. The infield roads** (`make_connectors.py` -> `source/connectors.infield.json`): **rc_infield** = RC-D off the oval
(NE lane, hairpin, diag, the lot: the 64.3 m straight + the measured band, bottom road, west road, sweeper), both ends on
the deck; **if_link** = IF-K's own piece (S-curve, C road east), both ends on rc_infield (`route.connector_hosts`).
Widths: the pieces' own per metre, a 15 m running median, junction-wide runs capped at 14.5 m, a floor of 85 % of each
piece's p50 (the S-curve's dusty edges dipped to 4 m), the lot band its p50 9.16 m. Heights: the DEM, 9 m mean. The route's
straight joins turned 35-100 deg in 4 m (a 12 m road cannot): each exit off the oval is redrawn as one cubic over 25 m
either side of the deck's edge (the pavement there is continuous: the apron and the diverge's mouth), and every spot
tighter than R 12 m relaxes towards its neighbours, never more than 3 m off the route (RC-D: max 1.45 m, p95 0.04 m;
IF-K: max 3.0, p95 1.27; its two junction turns stay tight, inside the mouths).

**6. Where it stands (PC, 2026-11-08 23:35; head ba4f836, workshop `D:/k10-scratch/pp_b3`, last full run `pp_b3w.log`
= the committed config).** kn5 and models_<id>.ini verification PASS for all three layouts. The oval's drive_test PASS,
and its wall is fixed: 0.1.0's outer wall (bespoke rails seated on the author stage's terrain, up to 1.6 m under the banked
strip) topped out at +0.61 m over the pavement, with 635 of 1,128 modules below it. Now `rails[].seat "surface"` +
`overlap_m` give every module +1.27..+1.36 m. 0.1.0's AC_TIME_0 also sat on the back stretch; the line is now on the
published S/F.

Still red:
- Road course drive_test: ground over the lane at 3 spots (the NE join s 948/966, the lot s 1626) and one 8.9 cm step at
  s 1887.
- verify_mouths: the NW mouth's APPROACH, 3.08 %/m against 3.
- Infield drive_test: the S-curve's real hairpin (8.3-8.7 m wide, centre R ~8-9 m) breaks the >110 deg on <9 m rule, plus
  2 ground spots at s 456. Asked of Kevin: "Drop infield for now" or "Exempt that hairpin". Nothing forced.

The NW mouth is the hard part. The infield road meets the 17 % bank at 32-36 deg across the measured knee (bank to 4 %
apron), and a connector ribbon (three lateral lines) cannot follow a bank, a knee and an acute edge sliver at once. Tried
and kept:
- `apron_road` cuts the apron along the road's edges (ground spots 78 -> 3).
- `weld_deck_apron` (the weld reads the apron past the edge).
- The NW exit eased over 15 m (24.7 -> 31.8 deg).

Tried and NOT kept: `edge_on_bank.round_m` 2.0 (a rounded knee). The NW approach went 3.08 -> 4.40 %/m and the steps
1 -> 2; the code stays, opt-in, undeclared.

Owed:
- The NW junction as a measured pad (lm_pads-style: one lidar deck over the junction, the oval's and the road's rows
  welded to its outline).
- The two oval mouths' corner radii and the skid-pad lot's paved outline. Both need the NAIP crop: asked of the Mac; the
  PC has none, and fetching it needs Kevin's yes.
- Kevin's call on the infield hairpin.
- The road course's grid_vertex: the lap gained vertices and the pole now stands 20.8 m behind the line. Reset it at the
  final rehearsal.

**7. The two oval junctions as measured pads; the clean rehearsal (PC, 2026-11-09).** Kevin's yes to the NAIP crop,
asked through the remote-control session and relayed verbatim: "Yes, download it". That covers the one 2023 crop:
co_m_3810427_ne_13_030_20230920_20240104, 8.46 MB, tools/naip_crop.py, the frame `road-course/naip_2023_030.json`
describes, to the pixel, at D:/k10-scratch/pp_naip. No other download.

What NAIP showed at both junctions is one continuous pavement: the lap's lane, the apron, the diverge's wedge and gore,
and the infield road. The NE has a grass island's round tip; the NW has the road's kerbed bend, the kerbed island and
the NE branch road beside the oval. The corners the welded mouths left as grass were real pavement. So each junction
is now built as the Lariat's mouths and Sand Creek's junctions are: one deck out to its measured outline (lm_pads,
`lm_pads.arms "streets"`).

- **The measurement** (`source/lidar/infield/junction_pads.py` -> `tracks/pikes-peak-lm/source/pads/NE|NW.json`, with
  pictures). A cell is pavement where NAIP reads grey and the 2018 lidar's ground intensity reads asphalt-dark, or
  where NAIP reads a red / white kerb.
  - The brownish sealed patches (NE north of the island, NW between the road and the branch) are pavement: intensity
    1,140-1,230, darker than the asphalt.
  - The infield's pale dirt is not: NAIP calls it grey, its intensity is 3,360.
  - The deck is the class-2 ground's local planes. NE: 2,348 m2, cuts v310 / v334. NW: 4,566 m2, cuts v428 / v465.
  - The boxes are authored by eye on NAIP and the mask: every vertex on grass or an island, except the arm crossings
    and the NW branch crossing.
- **The NW branch road** is not built. A 13.8 m K-rail closes it where the box crosses it (`close_arms "branches"`,
  Kevin's rule for a road not taken). The infield road's arms stay open.
- **The race lap** crosses each pad on the infield road's own measured line. That is the old connector's points
  through the box, with a cubic onto the oval on its own tangent (race_lap `via`). The lane is never wider than the
  measured pavement less 0.3 m a side. The straight NW join had turned 21 deg in one vertex on the 17 % bank, a
  7.1 cm step.
- **The wall's foot**: the deck runs 0.7 m past the lane under the outer wall, held at the lane edge's height. The
  wall seats on it (rails `stand_on`). Without that deck one module's base went 2.6 m under the surface. audit_mesh D
  counts the wall's footing on that band as exempt (1,780 verts; GATES-CHANGELOG 2026-11-09).
- **The apron at the cuts**: the apron strip's row is pinned with the lane's (`cut_strip`). Before, the NW deck met
  the apron 0.14 m low at its out-cut, a lip no gate drove.
- **The skid-pad band's end** tapers into the measured road (LOT_TAPER, 5 points, 9.16 -> 11.39 m). Its 2.7 m step in
  2 m was the last road-course grass spot (s 1626) and the infield's two (s 458).
- **Not done:**
  - The two mouth corner radii were not measured as radii. The pads' outlines are the measured corners themselves
    (the NE island tip, the NW kerb arc).
  - The skid pad itself (the big concrete circle) is still unbuilt ground beside the road.
  - The oval's inside white line stops across both pads (the lap's paint goes with its surface there).

**The clean rehearsal from an empty workshop** (`D:/k10-scratch/pp_b5`, `pp_b5.log`, head below):

| check | oval | road course | infield |
|---|---|---|---|
| drive_test | PASS (0 / 0 / 0) | PASS: ground 0 (was 3), severe 0 (was 1), kinks 7.2 /km (was 14.9) | FAIL: the real S-curve hairpin only (5 corners); ground 0 (was 2) |
| kn5 + models_<id>.ini | PASS | PASS | PASS |

Every other check passed:
- verify_pads: NE seam 1.4 mm, NW 8.2 mm (limit 10). No grass, no multi-coverage, no curb. The branch K-rail stands
  1.08 m.
- verify_mouths: if_link's two mouths. The two oval mouths are pads now.
- audit_mesh 0. houses PASS.
- The outer wall: 546 modules, 18 left out (as every earlier build).
- The road course's pole is 8.9 m behind the line (grid_vertex 910).

Stills: `tracks/pikes-peak-lm/source/pads/still_*.jpg`. Nothing installed. The install waits on Kevin's word (it
replaces `pikes_peak_international_raceway_lm`: archive it first, then ac_tidy record and the menu pictures).

**8. The edge strip flush (PC, 2026-11-09; ledger 0087's fix, Kevin "Yes, check them").** route.edge.grass_clearance
0.05 -> -0.08. The strip's outer lip had ended 0.12-0.14 m under the lane edge, while the prep holds the ground at
lane - 0.02, so the ground stood over the strip.

The fix, measured with the 0087 gutter probe on pp_b5 -> pp_b6:

| | before | after |
|---|---|---|
| rc_infield: ground over the strip (median) | 46 % | 4 % |
| rc_infield: side-stations more than half covered | 129 of 284 | 5 |
| if_link: side-stations more than half covered | 10 of 46 | 0 |
| oval wall side: ground more than 5 cm over the lip (behind the wall) | 98 of 278 | 0 |

The apron side keeps its measured lip. The clean rehearsal at this head (`D:/k10-scratch/pp_b6`, `pp_b6.log`) gives the
same verdicts as pp_b5: oval PASS, road course PASS, infield red on its real hairpin only. Every other gate passes.
Nothing installed.
