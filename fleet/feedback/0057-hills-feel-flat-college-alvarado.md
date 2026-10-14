---
id: 0057
title: "Coming down college toward 8 should be pretty steep and doesn't feel that way, same with heading down Alvarado from 70th"
status: open
scope: tracks/san-diego-lake-murray mainline profile (College southbound v1506 -> v761; Alvarado westbound v0 -> v761)
layer: project or engine (to be diagnosed)
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

## Diagnosis

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
