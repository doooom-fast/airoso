---
id: 0103
title: Milford round 3 — the side lines' blooms on the long smooth curves (0.1.16)
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

## 5. The fix: `lm_intake.width_hold` (0.1.16)

`tools/width_hold.py` (new, stdlib), run by `tools/lm_engine_intake.py` after `edge_fit` and `width_smooth_m`, before
`edge_retrace`, on the line `width_smooth_m` reads. Per span:

- the measured width: each evidence point on its nearest station of the span (within 20 m), per 5 m bin >= 4 points a
  side, the two sides' median |u|; at least 60 % of the span's bins measured [invented], or the span is refused;
- the width over the span is the straight fit through those bins (least squares, refitted 4 times without the bins
  further than 2.5 MADs + 2 cm [invented]), blended in and out over `blend_m` 15 m by a raised cosine [invented];
- self-check: built minus measured width, less its median, RMS before / after; a span the hold fits worse is refused.
- The line is not moved. `data/width_hold.json` logs every span. Without the key the intake is byte for byte as before
  (`predict_lines_0102.py --check` on main's config: "ARE the prediction").

A straight fit through the TRACE's own widths was built first (the Mac's first design): on s 1,114-1,270 it leans with
the trace's late rise (built minus measured +0.31 m median, 0.50 m RMS against -0.05 / 0.28 through the measured width),
and with `width_smooth_m` off (`test_milford_line_edges.py`'s comparison run) its own self-check refused that span. So
the hold fits the measured width.

Intake-level, on the GM line (the tool's own numbers; `r2/blooms_intake.py` on the swept line agrees):

| span | width before -> after | built - measured median | RMS about it | edges moved p50 / max | bloom a side |
|---|---|---|---|---|---|
| 1,114-1,270 | 10.59-12.18 -> 10.49-10.80 m | +0.437 -> +0.018 m | 0.518 -> 0.379 m | 0.23 / 0.69 m | +0.60 -> 0 |
| 1,557-1,857 | 10.74-12.17 -> 10.88-11.12 m | +0.302 -> +0.042 m | 0.628 -> 0.342 m | 0.12 / 0.60 m | +0.57 -> 0 |

- The held widths sit between the lidar-only real width (10.4-10.8 / 10.6-10.7) and NAIP's (~11.1): the evidence mixes
  both sensors. Not chased further (the Mac: "don't chase the last 0.5 m").
- The other nine long curves: widths, bloom and RMS identical before / after. Outside the spans + blends the width
  changes 0.0 m; the line moves 0.0 m.
- At the span ends the fit meets the trace with a step of -1.18 / -1.39 m (s 1,114 / 1,270) and +0.13 / -0.30 m (s 1,557
  / 1,857) of width over the 15 m blends. Both of s 1,114-1,270's sit where the measured road itself changes: the curve
  enters from the wide flare (measured 12.35 m at s 1,100 -> 11.13 at 1,110 -> 10.68 at 1,120) and leaves into the
  junction on the right (11.0 m at s 1,280 -> 12.0-12.2 at 1,290-1,300).

The records that read the width, re-made by their own tools (unchanged rules; `source/round3/apply_0103.sh`):

- the run-off pads (`runoff_pads.py --write`): the 19 pads identical; only `runoff_pads.json`'s line md5 changes;
- the verge trees (`veg_naip_verge.py --write`): the same 884, `trees.lm.json` byte for byte; 44 recorded distances to
  the drivable surface move up to 0.59 m;
- the trunk colliders (`veg_trunks_reach.py --write`): the same 251; 3 recorded distances move up to 0.2 m.

`source/round3/edit_config_0103.py` writes the key and 0.1.16 on top of 0.1.15 (refuses anything else).

## 6. Owed (not in 0.1.16)

- **s 580-660**, a third, smaller swell (G10: real 10.5-11.0 m steady, built +0.96 m). A hold there fits (built minus
  measured +0.49 -> -0.02 m median) but the trace before it is too wide as well (s 474-572: built 11.3-11.7 m, measured
  10.96-11.37 m, which really varies), so the blend at s 565-580 would pinch both lines ~0.53 m in 15 m where the road
  does not. It needs its own span design.
- **The banked turn, s 750-1,015**: built 1.2-1.8 m UNDER the real at s 875-940 (the trace's 16 m cap; real 14-17.8 m on
  the inner banked part). The opposite problem, and it changes the bowl. On the board.
- **The centre**: no shift. The lidar shows no consistent 0.3-0.8 m inside offset (the build's and NAIP's registrations
  are 0.66 m apart, so nothing under ~0.6 m can be settled); one larger reading, s 1,295-1,316 (R < 50 m): +1.35 / +1.72
  m toward the inside. Noted, not moved.
- Low-confidence edges (weak contrast): s 945-965 right, s 1,325-1,335.

## Tests

- `tests/tools/test_width_hold.py` (6): a swell the measured edge does not carry is held to the measured width; one it
  carries is refused; too few measured bins and bad spans refuse; the blend and the robust fit; opt-in only Milford names
  it, the intake runs it only with the key, after width_smooth and before edge_retrace; Milford's two spans, the
  edit script writes the key and its doc, and the committed line's width is straight across each span.
- `test_milford_finish_0100.py`, `test_milford_round2_0102.py`: the version pins move to 0.1.16 (round 2's version doc
  kept after round 3's); the trunks' line doc names 0.1.16's line.
- Every test file that names Milford or the intake (31): 249 passed on the PC's system python; the 9 failures + 5
  collection errors there are numpy / Pillow missing; under the lidar venv every one of those files passes except
  `test_bespoke_assets.py::test_generator_reproduces_the_committed_files` (`traffic_cone.obj` / `.json` differ),
  which fails the same on clean main d31cb9a8 on this PC.

## Not done

- The scratch chain on the PC (from an empty workshop, `--no-install`) when the queue reaches Milford; then the blooms
  re-measured on its `track.obj` (`r2/blooms.py`), every gate, the kn5 against 0.1.15's 51,527,489 B.
- Install on Kevin's standing word once green and matching; then his drive of the two curves.
