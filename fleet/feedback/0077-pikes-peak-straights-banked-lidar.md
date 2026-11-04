---
id: 0077
title: "Pikes Peak's straights are banked: front ~7°, back ~3° (lidar)"
status: fixed-installed
scope: tracks/pikes-peak
layer: project (track.config.json road_profile.cambers)
train: -
---

## Symptom

The research (LAWS L10, the config's `_arcs_doc`) gave PPIR 10° in all four turns over 50 m ramps, with the straights flat.
The G10's lidar camber survey (branch `claude/lidar-camber-survey`, 7d01d15, batch 3) measured the deck itself and disagreed
on the straights:
- the front stretch's dogleg reads about 7°;
- the back stretch reads about 3°;
- the rolls between straight and turn run 130-165 m, not 50 m.

## Evidence

`tracks/pikes-peak/source/lidar/camber-survey/` (now on this branch: `README.md`, `crossfall.json`, `crossfall.lidar.json`):
- source: USGS 3DEP `CO_Eastern_ElPaso_2018` EPT, `tools/lidar_crossfall.py`;
- 556 stations every 3 m on the config's reversed oval (the `cambers` station frame);
- class-2 plane fits, median 75 points a station, residual sd median 1.2 cm;
- negative (right edge, the outside, higher) at every station.

| section | stations (m) | measured | equivalent |
|---|---|---|---|
| front stretch dogleg | 1,560-1,665 and 0-150 | -12.5 to -12.8 % | 7.1-7.3° |
| roll into turn 1 | 150 -> 285 (135 m) | -12.7 -> -17.6 % | |
| turns 1-2 | 285-624 | -17.0 to -17.7 % | 9.6-10.0° |
| roll out of turn 2 | 624 -> 790 (165 m) | -17.0 -> -5.2 % | |
| back stretch | 790-900 | -5.1 to -5.3 % | 2.9-3.1° |
| roll into turn 3 | 900 -> 1,056 (156 m) | -5.3 -> -16.8 % | |
| turns 3-4 | 1,056-1,430 | -16.7 to -17.7 % | 9.5-10.0° |
| roll out of turn 4 | 1,430 -> 1,560 (130 m) | -17.6 -> -12.5 % | |

## Fix (0.4.0, branch `claude/pikes-peak-banking` from PR 27's a506888)

`road_profile.cambers`: the lidar's plateaus and ramps, not its per-station profile (L10: researched + measured, plateaus
and ramps only).
- The windows are summed (scripts/geometry/profile.py `bank_at`), each a raised-cosine trapezoid.
- Every ramp is 150 m, the measured 130-165 m. Neighbouring windows' ramps coincide, so the sum rolls from one plateau to the
  next exactly where the lidar does.
- The dogleg wraps the start line, so it is two windows. One runs past the lap's end (1,665.2 m); the other starts that far
  before 0, so the plateau holds across s 0.
- The turns keep L10's 10°: the research and the lidar agree within 0.4°.
- Every entry carries its `_source`.

| entry | before (0.3.0) | after (0.4.0) |
|---|---|---|
| front dogleg | flat | -7.2°: `front_dogleg_in` 1,420 + 400 and `front_dogleg_out` -245.2 + 545.2, ramps 150 m |
| turns 1-2 | -10°, 215 + 515, ramps 50 m | -10°, 150 + 640, ramps 150 m |
| back stretch | flat | -3.0°, 640 + 416, ramps 150 m |
| turns 3-4 | -10°, 960 + 540, ramps 50 m | -10°, 906 + 664, ramps 150 m |

**Against the survey:** the config's bank, station by station, is off by a mean of -0.10°, rms 0.36° and worst 1.23° (inside
a ramp). The steepest roll is 0.130 %/m, under the crossfall tool's 0.2 %/m limit; the old 50 m ramps peaked near 0.55 %/m.

## Verification (the PC chain, full, 2026-11-03)

- **The built deck** (the 1ROAD triangles' cross-slope across ±7 m at five stations):
  - s 60: 7.20°;
  - s 400: 10.00°;
  - s 850: 3.00°;
  - s 1,250: 10.00°;
  - s 1,600: 7.20°;
  - the outside edge is up at every one.
- **drive_test, 0.3.0 -> 0.4.0:**
  - severe 0 -> 0;
  - bumps 0.0 -> 0.0 /km;
  - kinks 0.0 -> 0.0 /km;
  - excursion drops 0 -> 0 (far ledges 0);
  - ground on top, floating, undrivable, obstruction, daylight 0 -> 0;
  - PASS.
- **audit:** CLEAN.
- **kn5_ground_check:** PASS, p95 0.025 m, 0 of 3,806 samples over 0.05 m, double-sheet cells 0. verify_kn5 PASS.
- **Installed** over `pikes_peak_international_raceway`, every gate green with no force.
  - 0.3.0 is parked in `D:/k10-track-archive/2026-11-03_173157/`.
  - `pikes_peak_international_raceway.kn5`: md5 `7ec2589f64afe20e14257ec4f750ed9e`, 84,200,155 B.

Kevin's drive is the verdict: the front stretch and the back stretch should now lean into the oval, not sit flat between
the turns.
