# Pikes Peak: the BUILT deck's banking against the 2018 lidar (ledger 0085)

Research only, in no chain. Kevin, 2026-11-07: "I also want to make sure our banking there is accurate".

## What was read

- **The built deck:** `pikes-peak-lm` 0.1.0 (Lake Murray v4's engine, ledger 0078), rebuilt on the Mac from an EMPTY
  workshop at `cf401bf4` (the head the PC installed it from) with `tools/ship_track.sh pikes-peak-lm --no-install`, ENG =
  `engine-july-snapshot` scripts + vendor plus airoso's `assets/textures` (REFERENCED.md5: 50 of 54 match; the 4 that do
  not are Lake Murray's tree / lamp textures, none of them in this kn5). SHIP OK. The rebuild's gate records
  (`drive_test.full.json`, `audit.json`, `kn5_ground_check.full.json`, `edge_report.json`, `lm_intake.json`,
  `crossfall.lm.json`) are byte-identical to the committed 0.1.0 records and the kn5 is the installed size (20,083,052 B;
  md5 b01cca4faf40592e7f669c79338b3fcb). The deck read is that kn5's own gate OBJ (`data/track.obj`, `1ROAD_*` faces).
- **The survey:** `../camber-survey/crossfall.lidar.json` (the raw class-2 plane fit per 3 m station, centre +-6.5 m) and
  `crossfall.json` (`tilt_pct`, the filled / smoothed / rate-limited line the intake builds from), keyed by POSITION
  (`tracks/pikes-peak-lm/data/crossfall.lm.json`).

`bank_check.py <workshop> <label>`: per station, the built deck's least-squares plane over the survey's own band (centre
+-6.5 m, 0.5 m steps), and its inner and outer halves. Output: `bank_check.lm010.json`.

## Numbers (`bank_check.lm010.json`)

| | mean | rms | worst |
|---|---|---|---|
| built vs the raw lidar fit, %-pts | +0.003 | 0.050 | -0.217 (s 1305: built -17.00, lidar -16.79) |
| built vs the raw lidar fit, degrees | +0.001 | 0.028 | -0.121 |
| built vs the survey's `tilt_pct` (what the intake took), %-pts | +0.001 | 0.007 | +0.047 |
| 0077's plateau windows vs the raw lidar, %-pts | -0.18 | 0.65 | -2.27 (s 666: window -16.72, lidar -14.45) |
| 0077's windows vs the raw lidar, degrees | -0.10 | 0.36 | -1.27 |

The survey's own noise: raw minus its smoothed line rms 0.048 %-pts; station-to-station sd 0.09 %-pts. **The built deck is
inside the survey's noise everywhere.** The LM move did NOT carry 0077's windows: `lm_intake.crossfall` takes the survey's
per-station line directly, which is 13x closer to the lidar than 0077's plateaus were (rms 0.05 vs 0.65 %-pts).

- Outside (right) edge up: 556 of 556 stations (CCW lap, every turn a left-hander).
- Sections (built / lidar, %): front stretch 13.11 / 13.11 (7.5 deg), turns 1-2 plateau 17.17 / 17.17 (9.74 deg), back
  stretch 6.17 / 6.16 (3.5 deg), turns 3-4 plateau 16.95 / 16.96 (9.62 deg), front dogleg 12.96 / 12.96 (7.4 deg). Steepest
  station: built 17.76 %, lidar 17.93 %.
- Ramps: |bank| crosses 15 % at s 198 / 660 / 1032 / 1497 built, 201 / 660 / 1032 / 1497 lidar; 9 % at 738 / 954 both.

## Constant or progressive across the width?

The raw lidar points are not on disk (the survey streamed them on the G10 and kept only the fits), so the halves could
not be re-fit. What the same 2018 returns already say (`prog_bank.py` -> `prog_bank.json`):

- `../wall-survey/wall_right.json` `road_slope_pct` is a SECOND plane fit of the class-2 returns, on a 3 m band from the
  centre to 3 m outside it (toward the wall). Against the 13 m plane at the same 556 stations: outer band minus 13 m plane
  mean -0.10, median -0.07 %-pts (p10 -0.58, p90 +0.36). By section: turn plateaus +0.03 and -0.13, front stretch +0.02,
  back stretch -0.35. **Constant across the measured 13 m: no steepening toward the wall.**
- The 13 m plane's residual sd is 1.21 cm median (p90 1.57 cm). Even if ALL of it were curvature, the slope could change by
  at most 2.5 %-pts across the 13 m.
- The built deck is one plane across the lane too (inner half minus outer half rms 0.006 %-pts).

What is NOT measured: the inside 5-11 m of the racing surface and the apron (see `../../road-course/README.md`, "The
inside edge"). The survey band stops 6.5 m inside the line; the pavement runs on to a median 18.3 m inside it.
