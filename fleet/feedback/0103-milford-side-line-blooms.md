---
id: 0103
title: Milford round 3 — the side lines' bulges, the whole lap (0.1.16); tools/edge_bulges.py for every track
track: milford-road-course-lm
status: fixed-awaiting-rebuild
opened: 2026-11-24
---

# Milford round 3: the side lines' blooms

Kevin, 2026-11-24, after 0.1.15 (installed 2026-11-23):

| Asked | Answer | Where |
|---|---|---|
| (his own note) | "looks good, getting there" | typed to the PC session |
| What still needs work on Milford? | "Road still wavy" | typed to the PC session |
| (clarifying) | "Not vertical waves, horizontal at the edges" | typed to the Mac, relayed verbatim |
| (clarifying) | "Long smooth curves get weird blooms" / "Look at the side lines" | typed to the Mac, relayed verbatim |
| (after 3e79e619, two spans) | "Mostly on supposedly smooth edges in very ugly unrealistic ways" / "Dreaded slop,a human would never do it because it's more work, both irl and digitally" / "The lines follow the edges though" / "Look for primarily bulges during otherwise smooth curves and straights" / "It's like flying a camera would see it faster" / "Data is noisy but the road is obvious in car" / "It's not even a 'curve' much as a bulge" / "Open up Milford's longest curve and look at the noise, it's should be entirely smooth" / "This is like a post build step, too complex for the main tool?" / "Like a review and fix agent and set of skills" / "Or: a tool that runs and listens to me verbally say when I see a dumb spot and it records that, and 3you learn from it or we do that every track, if you can't get this done on your own deterministically" / "Wehen I say records it, or 4mean all the meta data of where" | typed to the PC session |

The Mac's answer to the last three: deterministic first, as a shared tool (`tools/edge_bulges.py`, any track); the
spoken-tag fallback is not built unless the scan misses what he sees in the car (on the board).

Branch `claude/mf-edge-blooms-20261124` from main d31cb9a8. Every measurement below is read-only, on the installed
0.1.15's workshop (`D:/k10-scratch/milford_lm`, its `data/track.obj`) unless it says otherwise; the scripts are the PC
session's scratchpad (`r2/`).

## 1. Vertical first (dropped on Kevin's clarification)

Before "horizontal at the edges", the PC measured the road's heave. Kept here because it closes the question:

- Outside the bowl the built road is the measured surface (`road_surface_gm.fit.json`) at the G10 raw read's own points:
  felt heave (body band 0.5-4 Hz at drive_test's speed model) built minus fit 0.04-0.10 m/s2 RMS.
- The felt waves are the lidar's 30-120 m content. The G10's real-road profile (branch
  `claude/mf-road-profile-lidar-20261124` bb3bcab0) found them real: two flight strips (252 / 253), levelling them
  removes 0.01-0.04 cm, 97-105 % of each window's wave survives; built vs real gain 0.90-1.00 (30-60 m) / 0.98-0.99
  (60-120 m).
- Nothing vertical changes in this round.

## 2. What blooms

Read from 0.1.15's `track.obj` (ENU; `finished_centerline.json` is z-mirrored): the plan boundaries of 1ROAD, MARKINGS
(the paint), 1KERB (the edge strip) and 1RUNOFF, each side's offset off the lap line every 0.5 m (`r2/blooms.py`).

- Long smooth curves: one sign, R <= 800 m, the curvature within +-35 % of the curve's median over >= 50 m [all
  invented]: 11 on the lap.
- On every bloom the road edge, both edges of the paint and the strip's outer edge swell **together, on both sides**, by
  exactly the half-width's swell. The paint and the strip are not offset from a sparse polyline (no chord, no flipped
  normal); a pad touches one bloom only (s 156-176, right).
- The short edge wiggle (2-30 m) is 1.1-1.4 cm RMS, too small to be it. The width breathes 39 cm RMS at 60-120 m.

## 3. The cause: the width series

The ribbon is +-w/2 about the smoothed line, so a swell in the width blooms both side lines at once.

- The blooms are already in `tracks/milford-road-course/data_gm`'s widths (outside the GM piece these are the 0.6.0
  tracer's NAIP-mask perpendicular scans), carried by the intake bit for bit: s 1,583-1,731 10.82 -> 11.77 m (max
  12.21), s 1,199-1,270 11.39 -> 11.79, s 622-668 11.26 -> 11.75.
- `edge_fit` (judge) cuts 1-2 row spikes only (its own log: the edges a median 0.67 m / p90 2.02 m off the evidence,
  before = after). `width_smooth_m` 10 m cannot reach a 50-150 m swell. Real width changes here run 20-50 m, so more
  smoothing cannot tell them apart; the measured edges can.

## 4. Real or ours

Two measured sources, per long curve.

**The edge evidence** (`source/edges/edge_evidence_gm.json`, 17,513 points, NAIP 2022 + the 2017 lidar's intensity step;
5 m bins, >= 4 points a side; scatter within a bin p50 0.48-0.51 m): does holding the width straight fit the measured
width better than the trace?

| curve (s) | R m | verdict |
|---|---|---|
| 1,114-1,270 | 92 | hold: the trace swells, the measured does not |
| 1,557-1,857 | 93 | hold |
| 474-572, 778-832, 3,964-4,031, 4,144-4,248 | 76-322 | keep: the measured swells too (correlation +0.58..+0.74) |
| 156-239, 593-688, 2,059-2,152, 3,432-3,594 | 78-355 | no difference |
| 2,783-2,838 | 180 | inconclusive (10 bins, a flared wide area) |

**The G10's lidar re-read** (`milford_edges_curves.lidar.g10.json`, branch `claude/mf-road-profile-lidar-20261124`
19018b12; the intensity step, contrast p50 13k-28k against a 3k threshold; the height break 1.5-3 m off, reported, not
used):

- s 1,114-1,270: real width steady 10.4-10.8 m (residual 0.28 m against 0.27 m noise); 0.1.15 built +0.63 m median, up
  to +1.65 m.
- s 1,557-1,857: steady 10.6-10.7 m (0.26 against 0.24); built +0.76 m median, up to +1.96 m (s 1,625-1,695, the
  bloom's peak: real 10.2-10.7, built +1.58).
- The lidar reads ~0.26 m a side inside NAIP's edge (ledger 0087), so ~0.5 m of any built-minus-lidar width may be the
  sensors': in NAIP's terms the real width is ~11.1 m on both spans.

Both say the same: on the two spans the blooms are ours.

## 5. First: `lm_intake.width_hold` on two spans (3e79e619, superseded)

`tools/width_hold.py` held s 1,114-1,270 and 1,557-1,857 to the straight fit through the measured width (a fit through
the trace's own widths leaned with its late rise and was refused by its own check with `width_smooth_m` off): built minus
measured width median +0.437 -> +0.018 / +0.302 -> +0.042 m. The Mac's suite passed on it (1,897 / 0). Kevin's next words
(the table above) made it too narrow: every bulge on an otherwise smooth curve or straight, the whole lap. The tool stays,
opt-in, named by no track (`test_width_hold.py`); 0.1.16 names `width_design` instead, which takes those two out with the
rest.

## 6. The whole lap: `tools/edge_design.py`, `lm_intake.width_design`, `tools/edge_bulges.py`

The Mac's definition (2026-11-24), every number [invented]: a road as laid out is runs joined by tapers; a bulge goes out
and comes back over 15-200 m and over N cm; a step that does not come back is a width change; a bulge is real only when
the measured edge makes the same excursion beyond its own noise (the G10's lidar edges where they cover, the evidence
elsewhere); output the list, the count per km before and after, and the "flying camera" strip.

`tools/edge_design.py` (stdlib, shared):

- `layout(y)`: a morphological opening then closing over 200 m (a running minimum then maximum, then maximum then
  minimum): every swell and pinch narrower than 200 m taken down to the road either side; a step or a steady taper is
  monotone and comes through whole. An l1 trend filter was tried first and dropped: at any kink cost (300-3,000) it still
  rode a 1.2 m swell 0.4-0.9 m and rounded real steps into false excursions either side.
- `excursions(y, layout)`: where y leaves its layout by > 3 cm; a bulge at >= 10 cm and 15-200 m.
- `verdict`: the measured values' deviation from the same layout, median inside the bulge's core (over half its peak)
  minus median within 40 m outside: real at >= half the built peak and >= 2 standard errors (MADs); too few values in or
  out = unmeasured (kept: at Milford's gores the evidence, searched 3.5 m off the old edge, never reached a 4.7-9.4 m
  flare). A steady sensor bias and a real taper both cancel in the in-minus-out.
- `designed`: a bulge that is ours replaced by a cubic between its two ends on the layout's slope (the road's own slope
  just outside is the bulge's foot and rebuilt the bulges), the change rounded over 10 m (a Hann window, no kink at the
  joins; it reaches <= 5 m past a bulge).
- `measured`: the G10's lidar edges (`milford_edges_curves.lidar.g10.json`, merged from
  `claude/mf-road-profile-lidar-20261124` 19018b12) on its six stretches, `edge_evidence_gm.json`'s points on their
  nearest station elsewhere (the width per 5 m bin with >= 4 points a side).

`lm_intake.width_design` (Milford only; after `width_hold` and `width_smooth_m`, before `edge_retrace`): the width laid
out the whole lap; held: s 750-1,045 (the banked turn and `route.densify.section`'s spans + taper) and every
`edge_retrace` span and taper (re-traced to the measured edge after it). Without the key the intake writes main's line
byte for byte (both lines equal to d31cb9a8's committed ones). `data/width_design.json` logs every bulge and verdict.

`tools/edge_bulges.py` (numpy; a report, not a gate): from a built `track.obj` (the 1ROAD boundary cast along the line's
normals) or a line + widths; per side and on the width; the edge curvature's 2-30 m wobble and flips; the PNG strip
(rows of 400 m, the offset x10, built against the measured 5 m medians, bulges shaded). Per-track block
`track.config.json` "edge_bulges" {evidence, lidar_edges, skip}; the `edge_retrace` spans count apart by themselves.

### Milford, measured

On 0.1.15's built `track.obj` (`--workshop`, the bowl and the retraced stretches counted apart, as Milford's config has
it): width bulges the measured edge does not carry 11 (2.33 / km, max 1.59 m), real 4; left edge 9 / right 5 (per side
the line's own off-centre reading counts too). Counting the retraced stretches in: 16, real 15, unmeasured 5.

Unmeasured, kept (the Mac, 2026-11-24: "A gore or a junction flare the evidence never reached isn't a bulge we can call
ours"; `edge_bulges.py`'s "unmeasured_kept" list, for a look in the car), all five on the width and all inside retraced
stretches: s 0-20 (+0.65 m over 21 m), s 231-429 (+4.74 m, 199 m), s 2,388-2,512 (+9.41 m, 125 m: the gore),
s 3,230-3,287 (+1.46 m, 58 m), s 4,620-4,723 (+2.44 m, 104 m).

At intake (`data/width_design.json`), the width before the retrace:

| s | dir | peak | length | measured excursion |
|---|---|---|---|---|
| 535-603 | out | 0.30 m | 69 m | +0.16 +- 0.10 |
| 663-699 | in | 0.27 | 37 | -0.59 +- 0.12 |
| 1,186-1,322 | out | 1.59 | 137 | +0.24 +- 0.09 |
| 1,325-1,422 | in | 0.74 | 98 | -0.13 +- 0.40 |
| 1,436-1,534 | out | 0.27 | 99 | +0.07 +- 0.16 |
| 1,593-1,732 | out | 1.21 | 140 | -0.23 +- 0.07 |
| 1,742-1,819 | out | 0.49 | 78 | -0.07 +- 0.07 |
| 1,941-1,994 | in | 0.24 | 54 | +0.26 +- 0.13 |
| 2,002-2,074 | out | 0.10 | 73 | +0.05 +- 0.13 |
| 3,408-3,546 | out | 0.22 | 139 | -0.09 +- 0.20 |

- 10 taken out (2.12 -> 0.21 / km; the one the re-scan still finds, s 1,342-1,420, is 0.15 m), 6 real kept, 0
  unmeasured outside the held stretches; the edges moved max 0.78 m at 1,360 of 6,304 points; the line not moved.
- On the swept line (`edge_bulges.py --line`, the bowl and the retraced stretches counted apart), before -> after:
  width ours 11 -> 2 (2.33 -> 0.42 / km), left edge 9 -> 4, right 5 -> 1. The two left on the width: s 2,999-3,197 (0.42
  m; the measured edge says the road widens there even more, +1.35 +- 0.84 m, just inside its noise) and the 0.15 m one.
- The edges' curvature wobble (2-30 m, per 100 m) p50 0.18 -> 0.23 / 0.23 -> 0.24 per km (left / right), p90 and max
  unchanged.
- s 580-660 (the third swell, owed in 3e79e619) is taken out with the rest: the design keeps the trace's own level either
  side, so no pinch at s 565-580.
- Pictures (the PC's scratchpad `r2/`): `milford_edges_before_after.png` (four stretches, before / after / measured),
  `bulges_line_before.png` / `_after.png` (the whole lap), `mf_longest_straight.png` (the longest curve as built).

The records that read the width, re-made by their own tools (`source/round3/apply_0103.sh` rebuilds every file from
main's d31cb9a8 byte for byte):

- run-off pads (`runoff_pads.py --write`): the same 19 pads; L1355's inner and outer outline follow the lane edge in by
  <= 0.21 m (175 -> 170 m2), L3543 (left out) by 0.01 m;
- verge trees (`veg_naip_verge.py --write`): the same 884, `trees.lm.json` byte for byte; 111 recorded distances move
  <= 0.57 m;
- trunk colliders (`veg_trunks_reach.py --write`): 251 -> 249 (two trees now just past the 20 m reach), the reach still
  20 m (g4_infield_esses' standoff 19.07 -> 19.06 m).

## 7. Owed (not in 0.1.16)

- **The line's centre**: per side, the measured edges put the road's centre 0.3-0.45 m off the line on the long curves
  (the width is right, the line is not centred: left edge 4 / right 1 bulges left per side). The G10: no consistent offset
  it can settle under ~0.6 m (the build's and NAIP's registrations are 0.66 m apart); one larger reading, s 1,295-1,316
  (R < 50 m): +1.35 / +1.72 m toward the inside. Not moved.
- **The banked turn, s 750-1,015**: built 1.2-1.8 m UNDER the real at s 875-940 (the trace's 16 m cap; real 14-17.8 m on
  the inner banked part). On the board.
- s 2,999-3,197: a 0.42 m width swell the measured edge may carry (+1.35 +- 0.84 m); kept.
- Low-confidence edges (weak contrast): s 945-965 right, s 1,325-1,335.
- Kevin's spoken-tag tool: only if the scan misses what he sees in the car.

## Tests

- `tests/tools/test_edge_design.py` (7, the report's "unmeasured, kept" list included): the layout takes out swells and pinches and keeps steps and tapers; the design
  takes out only what the measured edge does not carry, keeps a real one, touches nothing else to the bit, never a held
  span; an unmeasured bulge is kept and reported; the lidar edges judge where they cover; width_design is opt-in, runs
  after width_hold and before the retrace, Milford only; Milford's config, script, ship.json and committed line;
  `edge_bulges.py --line` on a synthetic lap (needs numpy).
- `tests/tools/test_width_hold.py` (6): the tool's own tests; no track names it any more.
- `test_milford_finish_0100.py`: 249 trunk colliders, the standoff 19.06 m, 0.1.16; `test_milford_round2_0102.py`: 0.1.16.
- Every test file naming Milford, the intake, edge_design or width_hold (31): 256 passed on the PC's system python; its 9
  failures + 5 collection errors are numpy / Pillow missing, and under the lidar venv every one of those files passes
  except `test_bespoke_assets.py::test_generator_reproduces_the_committed_files` (traffic_cone.obj / .json), which fails
  the same on clean main on this PC and passes on the Mac (its suite on 3e79e619: 1,897 / 0).

## Not done

- The scratch chain on the PC (from an empty workshop, `--no-install`) when the queue reaches Milford; then
  `tools/edge_bulges.py --workshop` on its `track.obj` (before: 11 width bulges of ours on 0.1.15's, the retraced
  stretches counted apart), every gate, the kn5 against 0.1.15's 51,527,489 B. A green chain installs and merges (the
  Mac).
- `tools/edge_bulges.py` on Lake Murray, Sand Creek and High Plains (the Mac).
- Install on Kevin's standing word once green and matching; then his drive of the two curves.
