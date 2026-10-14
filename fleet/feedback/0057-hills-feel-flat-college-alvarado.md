---
id: 0057
title: "Coming down college toward 8 should be pretty steep and doesn't feel that way, same with heading down Alvarado from 70th"
status: in-progress — fixed and rehearsed (2026-10-14, full scratch ship, not installed); closes on Kevin's drive
scope: tracks/san-diego-lake-murray mainline profile — the College -> Alvarado signal approach (pre-median s 2200-2530) and Lake Murray Blvd's two decks + 70th St + Alvarado's pitch (13280 -> seam -> 230); tools/deck_datum.py (road_datum.profiles), scripts-v021/geometry/smooth.py + blender/build_loop_blend.py (opt-in per-window sigma_y)
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

Built = the v0.18.0 gate OBJ's 1ROAD at the lane centre; real = fresh USGS 3DEP 1 m (TLS on) on the same lane points.
Stations s are metres along data/centerline.local.json unless marked pre-median.

- **College's main descent (Del Cerro -> I-8) is built at its real grade** — 100 m real -8.70 % / built -8.60 %, 200 m
  -8.43 / -7.93. That one is perception (the onboard camera pitches with the car, a 36 deg vertical FOV on a 21:9
  screen, no freeway below to judge the drop against). No fix.
- **Flattened: the College -> Alvarado signal** (stop line s 2313, OSM node 49123188 at s 2312.3; s 2305-2320 all say
  the same): last 30 m real **+5.93 %** on the lane, built **+3.52 %**; the junction 0.8-1.2 m under the real pavement
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
- **The hairpin's junction box is held straight** (`hold_straight_m` [2289, 2323], new): the first full rehearsal put
  the real hump inside the College/Alvarado hairpin's levelled fold fan (rows 763-774, ledger 0050), whose inside edge is
  pinched to one height — `verify_fold_fans` FAILED on all three layouts (DT 0.087 m on the inside paths) and race severe
  steps went 22/20 -> 39/37, all at the hump. Held straight between the real road at its two edges (like a deck span),
  the fan passes again. Price: the crest inside the box stays as low as v0.18.0 built it, and the College approach eases
  in its last few metres before the stop line (the box's edge), so the 30 m approach reads +5.44 % instead of +5.9 %.
- **Crossfall: left level** (chosen). The real junction tilts 4-7 % across, west side higher; the build carries no
  mainline bank, and the junction box, fold fan, mouth weld, median, race corridor and their gates all assume level
  cross-sections. Carrying it would be a ribbon change far beyond these windows (and would collide with ledger 0055's
  College work). The datum reads both carriageway centres instead, so a level slab sits midway: on College the lanes
  match each other within 0.1 points, so a level slab gives the southbound lane its real grade.

Sigmas, rehearsed (each a full `ship_sd.sh --no-install`): 1.5 / 1.5 -> College +5.23 %, every listed gate no worse;
1.0 / 1.0 -> +5.44 % but street kinks 3.41 -> 3.56 /km (refused); **1.0 / 1.5 shipped**. Every invented number is in
fleet/GATES-CHANGELOG.md (2026-10-14, ledger 0057). No gate threshold changed.

## Results (rehearsal 4, 2026-10-14: full chain on a fresh scratch copy of the workshop, ENG a fresh copy of engine-july, not installed)

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

## Kevin's drive (the only verdict that closes it)

- Street (Lake Murray Free Roam): College southbound down past I-8, stop at the Alvarado light in a manual car, clutch
  in, no brake: the car should roll back now (built +5.4 % over the last 30 m, was +3.5 %). Then Alvarado up to 70th,
  stop facing uphill: +7 % (was +5.6 %).
- Westbound down Alvarado from 70th: the drop should read steeper right off the junction.
- Ask: does the College light feel right, or does the flat box at the hairpin (held straight for the fold fan; the real
  crest is ~1 m higher) still read wrong? If so, the next step is authoring that junction as a pad (JUNCTIONS §2.0 B),
  not more smoothing changes.
