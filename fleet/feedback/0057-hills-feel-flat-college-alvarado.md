---
id: 0057
title: "Coming down college toward 8 should be pretty steep and doesn't feel that way, same with heading down Alvarado from 70th"
status: in-progress — fixed, refuted, fixed again (fold-fan fit) and rehearsed (2026-10-14, full scratch ship, not installed); round 3 bounded the junction box (no in-gate change carries s 2305-2309; the stop line is s 2312.3); closes on Kevin's drive
scope: tracks/san-diego-lake-murray mainline profile — the College -> Alvarado signal approach (pre-median s 2200-2530) and Lake Murray Blvd's two decks + 70th St + Alvarado's pitch (13280 -> seam -> 230); tools/deck_datum.py (road_datum.profiles + fold_fan_fit), scripts-v021/geometry/smooth.py + blender/build_loop_blend.py (opt-in per-window sigma_y)
layer: project (+ the quarantined assembler of record, opt-in)
train: -
---

## Symptom (Kevin, 2026-10-14, v0.18.0)

> "Also diagnose some of the hills? Coming down college toward 8 should be pretty steep and doesn't feel that way, same
> with heading down Alvarado from 70th. It could be perceptual, real world vs sim but I know on those hills my cars with
> clutches would roll back from stoplights there"

> "Stoplight would be heading onto Alvarado from college" (Kevin, same day)

The roll-back spot is the **College -> Alvarado signal** at the bottom of College by I-8 (the College hairpin / College
interchange area, ~v761): the approach grade to that signal, in the direction a car waits facing uphill, is the number
that has to match the real hill.

## Diagnosis (read-only, independently checked, not refuted)

**Diagnosed 2026-10-14** (read-only, independently checked; outputs D:/k10-scratch/grades/). Two different things:

- **College's long descent (Del Cerro -> I-8) is built at its real grade** (100 m: real -8.70 %, built -8.60 %; 200 m
  -8.43 / -7.93). That part is perception: the onboard camera pitches with the car (camera_onboard.ini
  IS_WORLD_ALIGNED=0), so a steady 4.9 deg pitch looks flat; no inner-ear / seat cue without a motion rig.
- **Flattened, where a car waits facing uphill:** the **College -> Alvarado signal** approach (last 30 m: real +5.9 %
  on the lane, built +3.5 %; the junction built 0.8-1.2 m below the real pavement, which also cross-tilts 4-7 %), and
  **Alvarado / 70th** (100 m: real -7.69 %, built -6.08 %; the eastbound uphill wait at 70th real +8.3 %, built +5.6 %).
- **Mechanism:** the August heightfield smoothing baked into the frozen input (scripts-v021/elevation/heightfield.py
  :24-26, :53-79, :129; the lap-seam blend :136-142) plus the assembler's sigma_y 5 Gaussian
  (scripts-v021/blender/build_loop_blend.py:909-912 -> geometry/smooth.py). Short ~100 m features lose 1-2.4 points;
  long pitches barely change. The 12 % cap, deck_datum, the lift, box levelling, welds and the race corridor are ruled
  out.
- **Fix (running):** road_datum profile windows from fresh 3DEP at the two spots, Lake Murray Blvd's deck at its real
  abutments, and a per-vertex sigma_y only inside the windows.

Built = the v0.18.0 gate OBJ's 1ROAD at the lane centre; real = fresh USGS 3DEP 1 m (TLS on) on the same lane points.
Stations s are metres along data/centerline.local.json unless marked pre-median.

- **College's main descent (Del Cerro -> I-8) is built at its real grade** — 100 m real -8.70 % / built -8.60 %, 200 m
  -8.43 / -7.93. That one is perception (the onboard camera pitches with the car, a 36 deg vertical FOV on a 21:9
  screen, no freeway below to judge the drop against). No fix.
- **Flattened: the College -> Alvarado signal** (stop line s 2313, OSM node 49123188 at s 2312.3; v0.18.0 is equally
  flat for any stop from s 2305 to 2320, but a car waits only at s >= 2312.3: s 2273-2312 is the intersection box,
  see round 3): last 30 m real **+5.93 %** on the lane, built **+3.52 %**; the junction 0.8-1.2 m under the real pavement
  (s 2300 lane: real 112.07, built 110.83 m). The real junction is a hump (crest ~111.8 m at the road centre) that also
  tilts 4-7 % across, west side higher; the build is a level slab.
- **Flattened: Alvarado / 70th**: westbound 100 m (s 16-116) real -7.69 % / built -6.08 %; the eastbound uphill wait at
  70th (stop line s 12, last 30 m) real +8.29 % / built +5.55 %; the 70th junction 0.74 m low (s 0).
- **Mechanism** (to file:line): the August heightfield smoothing baked into the frozen pre-median input
  (scripts-v021/elevation/heightfield.py:24-26 constants, 53-79 smooth_profile, 129 call, 136-142 the lap-seam blend)
  then the assembler's sigma_y 5 Gaussian, run twice and wrapped across the seam (scripts-v021/blender/
  build_loop_blend.py:909-912 -> geometry/smooth.py smooth_centerline; track.config.json route.smooth_sigma_y_pts 5,
  ledger 0042). Both preserve a 200 m grade and round anything ~100 m long. Lake Murray Blvd's deck over I-8 and Alvarado
  Creek sits 1.2-2.1 m low in the frozen input (deferred in ledger 0046), so the 70th junction was a 12-point crest the
  Gaussian cut 0.7 m off.

## Fix

**road_datum PROFILE WINDOWS** (tools/deck_datum.py, the first draft step, beside the decks): inside each window declared
in track.config.json road_datum.profiles the pre-median y is replaced by fresh 3DEP 1 m read at **both carriageway
centres** (+-width/4 off the line; their mean is the slab height — the line itself reads the crown: +5.3 % on the
centre where both lanes run +5.8-5.9 %), every deck span inside held straight between its abutments, a 3 m Gaussian,
blended over 30 m at both ends. Cached with provenance in data/deck_datum.samples.json (L2). Only y moves.

| Window (pre-median s) | What | Assembler sigma_y |
|---|---|---|
| `college_alvarado_junction` 2200-2530 | Alvarado's climb to the junction, the hairpin, College down to the I-8 ramps (short of the College deck window at 2548) | 1.0 pt |
| `seventieth_alvarado` 13280 -> seam -> 230 (L13: wraps, the closing duplicate is v0) | Lake Murray Blvd north of I-8, both decks, 70th St, Alvarado's pitch to s 230 | 1.5 pts |

- **Lake Murray Blvd's decks** (the 0046 deferral) join road_datum.decks at their real abutments (fresh 3DEP, both
  carriageway centres): `lmb_over_i8` 13347-13424 (126.2 -> 126.2 m), `lmb_over_alvarado_creek` 13432-13457 (126.2 ->
  125.6 m), the fill between them at road height. Both lie inside `seventieth_alvarado`, which holds them straight; their
  own window pass is skipped (reported `re_derived_by_profile`).
- **The assembler stops re-flattening the windows** (option (a), opt-in): smooth_centerline takes per-vertex window
  weights and blends its sigma_y 5 result toward the window's own sigma (smoothstep over the blend); a vertex outside
  every window is byte-identical to the sigma_y 5 result, no declared window = the old call. The College main descent is
  identical to v0.18.0 (max |dy| 0.000 m on pre-median s 3200-3520); the largest change outside both windows is 0.02 m
  (the sigma 5 kernel's reach).
- **Round 1 (retired by the fix round below): the hairpin's junction box held straight** (`hold_straight_m` [2289,
  2323]): the first full rehearsal put
  the real hump inside the College/Alvarado hairpin's levelled fold fan (rows 763-774, ledger 0050), whose inside edge is
  pinched to one height — `verify_fold_fans` FAILED on all three layouts (DT 0.087 m on the inside paths) and race severe
  steps went 22/20 -> 39/37, all at the hump. Held straight between the real road at its two edges (like a deck span),
  the fan passes again. Price: the crest inside the box stays as low as v0.18.0 built it, and the College approach eases
  in its last few metres before the stop line (the box's edge), so the 30 m approach reads +5.44 % instead of +5.9 %.
- **Crossfall: left level** (chosen). The real junction tilts 4-8 % across, west side higher (fresh 3DEP at s 2300: the
  southbound lane 112.12 m, the centre 111.47, the northbound lane 110.81 — 1.3 m across 15 m). The race layouts run
  the full 28 m width here, and the race walls' containment is judged against the centre line (no_route BUILT and
  verify_fold_fans (7): a K-rail base within +-0.28 m of the centre line + 0.10); an 8 % tilt puts the walls 14 m out
  1.1 m off it, so a tilted slab fails both gates. Carrying it would also be a ribbon change far beyond these windows
  (and would collide with ledger 0055's College work). The datum reads both carriageway centres instead, so the level
  slab sits midway: on College's approach the lanes match within 0.1 points, so the slab gives the southbound lane its
  real grade there; at the junction itself it cannot (see the fix round).

Sigmas, rehearsed (each a full `ship_sd.sh --no-install`): 1.5 / 1.5 -> College +5.23 %, every listed gate no worse;
1.0 / 1.0 -> +5.44 % but street kinks 3.41 -> 3.56 /km (refused); **1.0 / 1.5 shipped**. Every invented number is in
fleet/GATES-CHANGELOG.md (2026-10-14, ledger 0057). No gate threshold changed.

## Results, round 1 (rehearsal 4, 2026-10-14: full chain on a fresh scratch copy of the workshop, ENG a fresh copy of engine-july, not installed)

Same lane points, same fresh 3DEP and same definitions as the diagnosis (real / v0.18.0 built / fixed):

| Spot | Real | v0.18.0 | Fixed |
|---|---|---|---|
| **College -> Alvarado, last 30 m to stop line s 2313** (lane) | +5.93 % | +3.52 % | **+5.44 %** |
| same, stop line s 2316 / s 2320 | +5.78 / +5.52 | +3.69 / +3.87 | +5.48 / +5.32 |
| same, last 15 m | +6.28 % | +3.06 % | +5.40 % |
| junction height, lane at s 2300 | 112.07 m | 110.83 m | 110.93 m (held: the fold fan) |
| **Alvarado westbound 100 m (s 16-116)** | -7.69 % | -6.08 % | **-7.55 %** |
| Alvarado westbound from 70th, s 0-25 / 0-50 / 0-100 | -3.69 / -6.04 / -6.92 | -3.41 / -4.97 / -5.69 | -2.91 / -5.48 / -6.82 |
| Alvarado steepest 25 m / 50 m in s 0-130 | -9.17 / -7.95 | -6.87 / -6.66 | -8.38 / -8.18 |
| drop s 0 -> 112 | 7.67 m | 6.31 m | 7.55 m |
| **70th eastbound uphill wait, last 30 m to s 12** (the diagnosis' lane rows) | +8.29 % | +5.55 % | **+6.95 %** |
| same, stop line s 8 / s 18 | +7.37 / +8.73 | +5.20 / +6.14 | +6.13 / +7.71 |
| 70th junction height s 0 / s 12 | 125.24 / 125.21 m | 124.52 / 124.26 | **125.26 / 125.22** |
| LMB over I-8, abutments (real / built) | 126.17 / 126.15 m | 125.17 / 124.27 | 126.24 / 126.24 |
| LMB over Alvarado Creek, abutments | 126.16 / 125.62 m | 124.19 / 124.13 | 126.20 / 125.74 |
| College main descent 25 / 50 / 100 / 200 m | -9.06 / -8.76 / -8.70 / -8.43 | -8.76 / -8.65 / -8.60 / -7.93 | identical to v0.18.0 |

The 70th eastbound row is on the diagnosis' westbound-lane points; the road centre there is real +7.5 %, so most of the
remaining gap is the westbound lane sitting higher than the centre, which a level slab cannot carry.

**Gates vs v0.18.0** (every one run on the BUILT artifacts):

| Gate | v0.18.0 | Fixed |
|---|---|---|
| street drive_test soft top / severe / kinks per km | 33 / 0 / 3.41 | **31 / 0 / 3.34** |
| street audit D / K / I / F | 0 / 20 / 20 / 13 | 0 / 20 / 20 / 13 |
| race_cw / race_acw severe steps | 22 / 20 | **17 / 17** |
| race barrier_missing, obstruction stations | 0, 0 | 0, 0 |
| race soft top | 9 / 9 | 9 / 8 |
| race kinks per km (not a listed gate) | 6.23 / 7.05 | 6.45 / 6.38 |
| no_route BUILT race_cw / race_acw | PASS / PASS | PASS / PASS (0 leaks, 0 / 406 probes, every spawn) |
| verify_fold_fans (3 pinches x 3 layouts) | PASS | PASS (hairpin DT max 0.028-0.034 m) |
| verify_mouths (4: Del Cerro x2, the medium route piece's two ends) | PASS | PASS (none sits in a window; only the route piece's worst-sample location moved) |
| verify_signs / verify_race / verify_race --scenery-only | PASS | PASS |
| verify_ai_line race_cw / race_acw | PASS | PASS (wall min 2.547 / 2.384 m) |
| rib_check / house_seat_check | PASS / PASS | PASS / PASS |

The Alvarado west leg, East Campus Dr and the 70th / Lake Murray Blvd side streets are not modelled as connectors in
this build, so no mouth re-welds onto the raised road; the four mouths that exist are outside both windows.

Plots (real / v0.18.0 / fixed, elevation + grade in the direction of travel): D:/k10-scratch/gradesfix/
profile_college_alvarado_signal.png, profile_alvarado_70th.png, profile_lmb_70th_alvarado.png (through the seam, both
decks), profile_college_descent.png (unchanged). Rehearsals: D:/k10-scratch/gradesfix/rehearsal{1..4}.log (1 = no hold,
fold fans FAIL; 2 = hold, 1.5/1.5; 3 = 1.0/1.0, street kinks over; 4 = shipped).

## Fix round (2026-10-14, after the refutation)

**Refuted on.** The truth lens confirmed every round-1 number and refuted the result. The held box (`hold_straight_m`,
pre-median 2289-2323 = local s 2283-2313) kept the junction flat. That had three effects:

- A car stopped a few metres into it got a much shallower hill than the real road. Last 15 m on the southbound lane:
  stop at s 2305 built +2.92 % against a real +7.16 %; stop at s 2313 built +5.42 % against +6.11 % (0.69 short).
- The crest stayed 1.15 m under the real southbound lane and 0.55 m under the real road centre (s 2300).
- The level slab sat ~0.2 m under the southbound lane at s 2318-2348.

The lens also flagged two disclosed items: Alvarado s 0-25 slightly flatter than v0.18.0, and terrace scenery
re-seated outside the windows.

**Cause (measured).** Two gates judge this hairpin on paths its tight turn bends.

1. **verify_fold_fans.** The levelled fold fan (rows 763-774) pinches the ribbon's inside edge to one point. Every
   wheel path inside folds too, is cut at its own self-intersection, and turns sharply on the corner's medial axis.
   Its grade jumps there by the surface's slope along that axis.
2. **drive_test.** Its fixed-offset wheel paths jump sideways each time the segment normal turns. On a 5-6 % slope
   that is a severe step and a kink.

The real crest inside the fan fails both. Rehearsal 5 fitted the fan alone and was refused: street severe steps 0 -> 10,
street kinks 3.41 -> 5.86 /km, race severe 22 / 20 -> 27 / 26, all at s 2296-2304. The box passed both gates only by
removing the crest.

To work this out I built models of both gates on the ribbon the build carries, and checked them against the built
gates:

- The fan model read 0.0868 / 0.0342 m where `verify_fold_fans` read 0.087 / 0.034 on rehearsals 1 / 4.
- The drive_test replica found rehearsal 5's 10 street severe steps at the same stations, heights within 1 mm.
- The assembler prediction matched the built centreline to 5e-5 m.

**Fix: `fold_fan_fit`, replacing the box** (tools/deck_datum.py; config `road_datum.profiles[0].fold_fan_fit`
`{fit_m: [2250, 2340], dt_max_m: 0.05}` and `road_datum.assembler_smooth`; `hold_straight_m` removed from code and
config).

- **What it does.** Inside `fit_m` the profile takes the change with the smallest misfit to the 3DEP target (heights,
  grades and grade changes, on the heights the assembler will build), subject to two limits:
  - every fan pinch stays within 0.05 m on `verify_fold_fans`' own survey (the gate allows 0.06);
  - drive_test's wheel paths over `fit_m` (street, plus a race lane in both directions) have no severe step and no more
    kinks than v0.18.0 built here.
- **What it reads.** Both limits are read on the ribbon the build will carry. Inside `fit_m`, the 3DEP is read on the
  plan the assembler builds: its smoothing moves the hairpin's line up to 3.6 m, and the junction tilts 8 % across, so
  round 1 read the road 0.1-0.3 m off.
- **What it leaves alone.** Outside `fit_m` nothing moves.
- **Determinism and cache.** The solve is deterministic. It is cached in data/deck_datum.samples.json `fold_fan_fits`,
  keyed by everything it reads; a fresh solve reproduces the cached output byte for byte.
- **Refusals.** It refuses, rather than ships, a fit that cannot meet both limits or that moves a height more than
  0.25 m. The message says "author the junction as a pad".
- **Why `fit_m` stops at 2340.** Rehearsal 6 ran it to 2360. The fit then steepened College's flank into a sag at
  s 2328-2346, where the seated ground's 10 m facets rose through the road by up to 9 mm. Soft tops went street
  33 -> 39 and race 9 -> 21 / 19, so that version was refused.

**Crossfall: still level, now with a measured reason.** The race layouts run the junction's full 28 m width, and
both no_route and verify_fold_fans (7) judge the race walls within +-0.28 m of the centre line. The real 8 % tilt
puts them 1.1 m off it 14 m out. A tilted slab fails both gates.

**Results (rehearsal 7, 2026-10-14):** full `ship_sd.sh --no-install` on fresh scratch copies (project7,
engine-july7), not installed. Measured with the truth lens's own method (D:/k10-scratch/gradesfix/verify5/grades.py):
the built 1ROAD at the lens's points against fresh 3DEP (TLS on), 6 m means. Columns are real / v0.18.0 / round 1 /
fix round.

| Spot | Real | v0.18.0 | Round 1 | **Fix round** |
|---|---|---|---|---|
| College -> Alvarado, last 30 m, stop s 2313 (S/B lane) | +5.93 % | +3.52 | +5.45 | **+5.88** |
| same, last 15 m, stop s 2313 | +6.11 % | +3.06 | +5.42 | **+6.17** |
| last 30 m / 15 m, stop s 2316 | +5.72 / +5.92 | +3.68 / +3.29 | +5.48 / +5.70 | +5.88 / +6.48 |
| last 30 m / 15 m, stop s 2320 | +5.45 / +5.77 | +3.86 / +3.56 | +5.30 / +5.74 | +5.63 / +6.39 |
| last 30 m / 15 m, stop s 2310 | +6.12 / +6.43 | +3.32 / +2.80 | +5.20 / +4.77 | +5.72 / +5.52 |
| last 30 m / 15 m, stop s 2308 | +6.29 / +6.76 | +3.18 / +2.62 | +4.90 / +4.11 | +5.53 / +4.94 |
| last 30 m / 15 m, stop s 2305 | +6.47 / +7.16 | +2.96 / +2.37 | +4.33 / +2.92 | +5.19 / +3.98 |
| same on the road centre, stop s 2310 / 2313, last 15 m | +5.64 / +5.63 | +2.79 / +3.05 | — | +5.52 / +6.16 |
| junction height s 2300, road centre | 111.48 m | 110.83 | 110.93 | **111.27** |
| junction height s 2300, S/B lane | 112.08 m | 110.83 | 110.93 | 111.27 |
| height s 2310 / s 2313, road centre | 111.14 / 110.98 | 110.68 / 110.61 | — | 111.14 / 111.04 |
| Alvarado W/B 100 m (s 16-116) | -7.68 % | -6.08 | -7.54 | -7.54 |
| Alvarado W/B s 0-25 / 0-50 (lane) | -3.70 / -6.10 | -3.40 / -4.97 | -2.92 / -5.49 | -2.92 / -5.49 |
| Alvarado s 0-25 / 0-50 (road centre) | -2.80 / -5.49 | -3.40 / -4.96 | — | -2.92 / -5.49 |
| 70th E/B wait, last 30 m to s 12: E/B lane / centre / W/B lane | +6.77 / +7.44 / +8.20 | +5.58 | +6.97 | +6.97 |
| 70th junction s 0 / s 12 (centre) | 125.17 / 125.23 m | 124.52 / 124.26 | 125.26 / 125.22 | 125.26 / 125.22 |
| LMB over I-8 abutments (centre s 13333 / 13416) | 126.22 / 126.19 m | 125.19 / 124.23 | 126.23 / 126.23 | 126.23 / 126.23 |
| LMB over Alvarado Creek, s 13449 / 13475 | 125.57 / 125.15 m | 124.16 / 124.51 | 125.66 / 125.26 | 125.66 / 125.26 |
| College main descent 25 / 50 / 100 / 200 m (S/B lane) | -9.01 / -8.82 / -8.75 / -8.44 | -8.79 / -8.66 / -8.59 / -7.93 | same | **same as v0.18.0** |
| max change vs v0.18.0 on the road outside the windows | — | — | — | 0.020 m at the window ends (s 228, s 2520), under 0.004 m 25 m on (corrected in round 3) |

What that table says:

- **The real stop line (s >= 2313; signal node 49123188 at s 2312.3).** Both the 30 m and the 15 m approach are now
  within 0.06 points of the real southbound lane. Round 1 was 0.69 short on the 15 m.
- **s 2310 and s 2316-2320.** The 30 m approaches are within 0.5 points. The 15 m ones are 0.9 points short at s 2310
  and 0.6 points steep at s 2316-2320, because the slab follows the mean of both carriageway centres.
- **Inside the box (s 2305-2308).** Against the real southbound lane the car gets 1.3 / 3.2 points less at s 2305
  (30 / 15 m) and 0.8 / 1.8 less at s 2308. On the road centre the 30 m approaches match (5.18 against 5.30, 5.54
  against 5.36), and the 15 m ones are 1.3 / 0.6 points short. These stations are inside the fan, and that is all the
  two gates allow there.
- **The crest.** It is now 0.21 m under the real road centre (round 1: 0.55). It is 0.81 m under the real southbound
  lane: that lane sits 0.6 m above the centre on the tilt the level slab cannot carry.
- **The 70th wait.** It was read on the wrong lane in round 1. On the eastbound lane, where the car actually waits,
  real is +6.77 % and built +6.97 %. The road centre is +7.44 % real.
- **Alvarado s 0-25.** Unchanged since round 1: -2.92 % against -3.70 % on the lane and -2.80 % on the road centre. The
  70th junction is level for ~12 m and then drops, and the window's 1.5-point assembler sigma rounds that knee. Sigma
  1.0 there was the variant that pushed street kinks over v0.18.0 in round 1.
- **"Byte-identical outside", stated precisely.** The road and the centreline outside the two windows move by at most
  0.020 m just past each window end (s 228, s 2520: the tail of the assembler Gaussian), falling under 0.004 m within
  ~25 m; no grade outside moves by more than 0.03 points (corrected in round 3; this line first said 0.004 m). The terrace scenery between the hairpin legs (ground_release `alvarado_college_terrace`) re-seats onto the
  raised College leg, by up to 0.23 m (one grass vertex 0.43 m). That is the release doing its job.

**Gates vs v0.18.0** (rehearsal 7; every one run on the BUILT artifacts):

| Gate | v0.18.0 | Round 1 | Fix round |
|---|---|---|---|
| street drive_test soft top / severe / kinks per km | 33 / 0 / 3.41 | 31 / 0 / 3.34 | **9 / 0 / 2.97** |
| street audit D / K / I / F | 0 / 20 / 20 / 13 | same | same |
| race severe steps cw / acw | 22 / 20 | 17 / 17 | 17 / 18 |
| race soft top cw / acw | 9 / 9 | 9 / 8 | 8 / 7 |
| race barrier_missing, obstruction | 0, 0 | 0, 0 | 0, 0 |
| no_route BUILT cw / acw | PASS | PASS | PASS (0 leaks, 0 / 406 probes) |
| verify_fold_fans (3 pinches x 3 layouts) | PASS | PASS | PASS (hairpin DT 0.047 / 0.044, grass-on-top 0) |
| verify_mouths (4), verify_signs, verify_race (+ scenery), verify_ai_line x2, rib_check, house_seat_check | PASS | PASS | PASS |
| race kinks per km (not a listed gate) | 6.23 / 7.05 | 6.45 / 6.38 | 6.68 / 6.82 |

**Plots** (real / v0.18.0 / fix round): D:/k10-scratch/gradesfix/profile_college_alvarado_signal.png,
profile_alvarado_70th.png, profile_lmb_70th_alvarado.png and profile_college_descent.png.

**Rehearsals:** D:/k10-scratch/gradesfix/rehearsal5.log (the fan alone, refused), rehearsal6.log (`fit_m` to 2360,
refused on soft tops) and rehearsal7.log (shipped config).

**What would carry the rest.** That needs the junction authored as a pad (JUNCTIONS §2.0 B), heighted and tilted from
3DEP. It also needs gates that judge a pad on its own wheel paths rather than on a ribbon's fixed offsets, with the
race walls measured against the local deck. That is a gate change, so it is Kevin's call.

## Round 3 (2026-10-14, after the second refutation): the bound, and no build change

**Refuted on.** The truth lens confirmed every fix-round number to ~0.05 and refuted on its own stop-line range: for a car
stopped at s 2305-2309 on the southbound lane, the last 15 m is built +3.9-5.2 % against a real +6.6-7.0 %, and the last
30 m is 0.6-1.25 points short. It passed s 2310-2320. Two minor items: the "0.004 m outside the windows" line was low (now
corrected above: 0.020 m tails at the window ends), and Alvarado s 0-25 is still -2.9 % against a real -3.6 % (disclosed).

**Where a car waits.** OSM's two signal nodes on this junction, projected onto the lap
(D:/k10-scratch/gradesfix/r3/signals_near.py, the diagnosis' fresh Overpass cache):

| Node | Tags | Lap s | Off the line |
|---|---|---|---|
| 49123188 | traffic_signals, direction=forward (College southbound) | 2312.3 | 0.5 m |
| 11352113569 | traffic_signals, direction=backward (Alvarado, the other side of the box) | 2273.2 | 1.7 m |

A signal node with a direction is mapped at the stop line, so College's stop line is s 2312.3 and s 2273-2312 is the
intersection box. A car at s 2305-2309 is 3-7 m past College's stop line and inside the intersection. It is not waiting at
the light Kevin named. The diagnosis line above that read "s 2305-2320 all say the same" is reworded: v0.18.0 was equally
flat for any stop in that range, but the stop line is s >= 2312.3.

**The bound: what any change could reach inside the box.** I re-ran the fold-fan fit offline with each limit relaxed in
turn (D:/k10-scratch/gradesfix/r3/variant.py; same solver and committed inputs). Each result is read on the assembler's
own predicted heights, which matched the built centreline to 5e-5 m in the fix round, against the same fresh 3DEP on the
southbound lane.

| Variant | Fan DT (gate 0.06) | drive_test wheel paths at the fit: street kinks (v0.18.0 12) / race kinks cw, acw (22 / 20) | Last 15 m to s 2305 / 2308 / 2310 / 2313 | Last 30 m to s 2305 / 2308 / 2313 | Crest s 2300 |
|---|---|---|---|---|---|
| **real, southbound lane** | — | — | **7.16 / 6.76 / 6.43 / 6.11** | **6.47 / 6.29 / 5.93** | **112.12** (centre 111.47) |
| shipped (fit to DT 0.05) | 0.047 | 8 / 22, 20 | 3.95 / 4.93 / 5.52 / 6.16 | 5.18 / 5.54 / 5.87 | 111.27 |
| fan allowed to 0.057 | 0.047 | 8 / 22, 20 | 3.97 / 4.95 / 5.52 / 6.15 | 5.18 / 5.54 / 5.87 | 111.27 |
| fan 0.059, race kinks free | 0.051 | 12 / **47, 46** | 4.35 / 5.23 / 5.70 / 6.05 | 5.06 / 5.42 / 5.73 | 111.29 |
| fan 0.059, every kink free | 0.056 | **24** / **55, 57** | 4.91 / 5.97 / 6.50 / 6.79 | 5.47 / 5.83 / 6.09 | 111.40 |
| no fit at all: the 3DEP target, the best any level slab can do | **0.076 (FAIL)** | 34 / 81, 88, race severe 13 / 12 | 6.36 / 6.25 / 6.16 / 6.04 | 6.08 / 5.98 / 5.76 | 111.73 |

What the table says:

- **The fan limit is not what binds.** Raising it to 0.057 changes nothing; the fit settles at 0.047 either way.
- **What binds is drive_test's kinks round the hairpin.** Freeing them buys about 1 point on the 15 m at s 2305-2308.
  The price is the corner's kinks doubling on the street (+16 over the lap takes street kinks/km 2.97 -> ~4.2, past
  v0.18.0's 3.41) and rising 2.5x in the race (cw 6.68 -> ~8.5 /km). Those are real slope breaks on the paths a wheel
  takes round that hairpin, so I did not ship that trade.
- **Even with no gate at all, a level slab misses s 2305.** The 15 m comes out at 6.36 against 7.16, and s 2308 at 6.25
  against 6.76. The southbound lane sits 0.65 m above the road centre at s 2300 because the junction tilts 4-8 % across;
  a level road gives each lane the centre's grade. That variant also fails verify_fold_fans (DT 0.076) and adds 13 / 12
  race severe steps.
- **What would carry it.** Inside the box the lane's grade needs crossfall. The race walls are judged within +-0.28 m of
  the centre line (no_route BUILT, verify_fold_fans (7)), and the walls stand ~14 m out, so a tilt over ~2 % fails both.
  The fold-fan ribbon and its levelled pinch would also have to tilt. That is the junction authored as a pad (JUNCTIONS
  2.0 B) plus gates that judge walls against the local deck: gate changes and a ribbon change outside this job's two
  windows (it would also collide with ledger 0055's College work). That is Kevin's call. No gate was loosened to try it.

**Decision: no build change this round.** The shipped fit (rehearsal 7) is the in-gate optimum at the stop line Kevin
named: s 2313 is +5.88 / +6.17 % on 30 / 15 m against a real +5.93 / +6.11. Every committed input is unchanged, so
rehearsal 7 and every gate number above stand.

Plot: D:/k10-scratch/gradesfix/profile_junction_bound.png. It shows the real southbound lane, the real carriageway mean,
the real northbound lane, the shipped build and the no-gate level slab across the junction, with both signals and the
intersection box marked, and the last-15 m grade to each stop.

## Kevin's drive (the only verdict that closes it)

- Street (Lake Murray Free Roam): drive College southbound past I-8 and stop at the Alvarado light in a manual car,
  clutch in, no brake. The car should roll back: the last 30 m are built at +5.9 % (real +5.9 %, v0.18.0 +3.5 %). Then
  climb Alvarado to 70th and stop facing uphill: +7.0 % (v0.18.0 +5.6 %).
- Westbound down Alvarado from 70th: the drop should read steeper right off the junction.
- Ask: does the hump at the College light feel right now? It is 0.2 m under the real road centre, and the junction is
  still a level slab. If a car stopped inside the junction, or the tilt, still reads wrong, the next step is authoring
  that junction as a pad (JUNCTIONS §2.0 B), with gates that judge a pad on its own wheel paths. That is a gate change,
  so it is Kevin's call. More smoothing changes are not the next step.


## v0.18.1 integration (2026-10-14; merged with 0055 + 0056, full rehearsal r2, NOT installed)

The lens's own points (real4.json, fresh 3DEP) sampled on the combined build give the same numbers as rehearsal 7, to
the hundredth: College southbound into the Alvarado light, last 30 m to the stop line s 2313: built +5.87 % vs real
+5.93 % (v0.18.0 +3.51 %); last 15 m +6.16 vs +6.11; Alvarado westbound from 70th s 0-100: -6.83 vs real -6.95 (v0.18.0
-5.69); 70th eastbound wait, last 30 m to s 12: +6.97 vs +6.77; LMB abutments within 0.02-0.09 m of 3DEP; College's
main descent changed by at most 0.012 % in any 25-200 m window. The stops at s 2305-2309 inside the junction are as
short as round 3 bounded (15 m: -3.14 on the +7.5 m lane at s 2305). LIGHTPOST_8 (the floating lamp by the creek deck) is
0056's lamp 237 in the combined build: moved off the deck onto its embankment (0056 v0.18.1 section). Still:
D:/k10-scratch/v0181/stills/freeroam_college_sb_*.png; lamp D:/k10-scratch/v0181/stills/lamp237_lightpost8_*_low.png.

### v0.18.1 fix round (2026-10-14, rehearsal r3)

The gates lens found that this ledger's `lmb_over_i8` deck (at its real 3DEP height, 126.2 m) raises Lake Murray Blvd's
deck-edge drop over the I-8 floor from v0.18.0's 4.4–5.2 m to 6.0–6.8 m (v4455–4473). One 150 m sample (v4457) now
lands on it. The drop is real and stands behind the deck's 0.95 m bridge-rail panels (±6.90 m). drive_test's guard
probe could not see a vertical panel; it now credits a 1WALL that the car's path crosses (GATES-CHANGELOG v0.18.1 fix
round). On the creek deck's far end (v4478–4484), the dense sweep's no-surface holes rise from 4 to 10. The cause is the
same: the deck now stands 8.3–10.5 m over the real creek bed, beyond the sweep's 8 m window, behind the creek deck's
Jersey rail. They are not gated on either build and were not changed. Grades re-measured on r3 are identical to r2's to
the hundredth: College stop line s 2313, last 30 m +5.87 % (real +5.93 %), Alvarado westbound s 0–100 −6.83 % (real
−6.95 %), 70th eastbound last 30 m to s 12 +6.97 % (real +6.77 %).

### v0.18.1 fix round 2 (2026-10-14, rehearsal r4)

The gates lens found race_cw bumps / km 4.38 -> 5.20 on r3, a gated rate missing from the tables. This ledger's real
grades were the cause, through two mechanisms (GATES-CHANGELOG v0.18.1 fix round 2). (1) drive_test's fixed-offset
wheel paths hop forward or creep at every centreline vertex round a corner, and the bump rule read grade x (hop - 1)
there; a steeper real grade reads more. Bumps are now re-measured on the wheel's own travel: a plane reads zero, a real
crease still counts, severe steps are untouched. (2) The lap seam's hook (70th / Alvarado, rows 4496 -> 5) was mended
by a forward chord whose rows kept their own heights, a 6-9 cm drop in under a metre (-17.8 % over 0.3 m on v0.18.0),
made worse by Alvarado's real -7.7 % pitch. The mainline's chord now carries its own straight grade (`mouth_weld`).
On r4, re-measured, race_cw counts 6 bumps against v0.18.0's 4 and race_acw 5 against 10. v0.18.0's 4 were that seam
sliver. r4's 6 are two 2.6 cm facet kinks where Alvarado rolls off the seam corner, two in the College fan's eased leg,
and two race-kerb crossings on geometry identical to v0.18.0's. Averaged over four sampling phases, v0.18.0 counts 8.75
and r4 5.25. Grades on r4 are r3's to the hundredth, except Alvarado westbound s 0-25 -2.89 % (r3 -2.92) and s 0-100
-6.82 % (r3 -6.83), from the seam's graded edge. Stills of the seam exit, race_cw, before (r1) and after (r4):
D:/k10-scratch/v0181/stills/r4/seam_race_cw*/seam_v{4494,1,4}.png.
