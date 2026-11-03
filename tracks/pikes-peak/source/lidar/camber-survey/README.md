# Pikes Peak International Raceway (Fountain, CO): lidar cross-slope survey

Research only. Nothing here is applied to any build; the files live under `source/` so no build picks them up.
Measured on the G10 (Linux) with `tools/lidar_crossfall.py` from branch `claude/sand-creek-0.33.0` (algorithm identical to the `claude/sand-creek-camber` copy batches 1-2 used; the only differences are the TLS context and the mesh-frame handling of `finished_centerline.json`, neither of which changes the numbers here), 2026-11-03.

- **EPT project:** `CO_Eastern_ElPaso_2018` (USGS 3DEP, `https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_Eastern_ElPaso_2018/ept.json`). `CO_Eastern_B5_2018` also has the site inside its bounds but holds only coarse nodes there; ElPaso is the dense one (30 EPT nodes along the corridor).
- **Line:** `data/finished_centerline.json` from branch `claude/new-tracks-pueblo-pikes` (frame `kn5`, mirror_x false), lap 1665.2 m, 3 m stations, + = left side higher. The line is the config's reversed (counter-clockwise) oval, so station s matches the `cambers` windows in `track.config.json`.
- **Half-width used:** 6.5 m (config `default_width_m` 15 m, half 7.5 m minus 1 m). The tool hard-codes 4.5 m.
- **Thresholds, as batch 1 except the read and cap limits:** MAX_SD_M 0.08 -> 0.10 m. **MAX_READ_PCT and CAP_PCT 12 -> 20 % (a deviation from batch 1).** At batch 1's 12 % the run produced 97 of 556 usable stations: this is a 10-degree banked oval (tan 10 deg = 17.6 %) and 459 stations read 12.4-17.8 % and were rejected as "a bank, not a carriageway", leaving a composed tilt that is zero over most of the lap (|tilt| p50 0.0 %, max 9.07 % from filled ramps; kept on the G10 only, not committed). The 20 % limit keeps every station. Values are recorded in `crossfall.json` `params`. The 0.2 %/m roll-rate limit and 9 m smoothing are the tool's own.
- **Wall time on the G10:** 13 s (fetch + fit, nice 19, 4 GB cap), peak RSS 103 MB.

## Numbers (`crossfall.json` `tilt_pct`: filled, smoothed, rate-limited)

- Stations: 556; dropped (not a road fit, filled): 0
- Fit quality: ground (class 2) points, median 75 points per station, residual sd median 1.2 cm (max 2.1 cm). These are very clean planes.
- |tilt| p50 16.41 %, p95 17.60 %, max 17.75 %
- Banked (|tilt| >= 2 %): 100 % of stations; the sign is negative at every station (right edge higher; the turns are left-handers, so the raised edge is the outside)
- Worst roll change per 30 m: 3.03 % (tool); at the 0.2 %/m limiter's 6 % ceiling nothing is clipped
- In corners of >= 15 degrees per 30 m: 0 stations (the tightest bend turns 14 degrees per 30 m, R about 118 m). With the corner threshold lowered to 8 degrees per 30 m: 262 corner stations, all banked into the turn, 0 off-camber.

## Sustained banking and the turns

One run: the lap never drops under 2 % and never changes sign, so there is a single run (0-1665 m, - sign). By section, from `tilt_pct`:

| s (m) | section (per the config's `cambers`) | measured mean % | measured range % | equivalent deg (mean) |
|---|---|---|---|---|
| 0-215 | front stretch / dogleg (config: flat) | -13.1 | -12.4 to -15.8 | 7.5 |
| 215-265 | turn 1-2 ramp-in (config: ramp 0 -> 10 deg) | -16.9 | -16.0 to -17.4 | 9.6 |
| 265-680 | turns 1-2 plateau (config: -10 deg) | -17.2 | -13.7 to -17.7 | 9.7 |
| 680-730 | turn 2 exit ramp | -11.7 | -9.8 to -13.4 | 6.7 |
| 730-960 | back stretch (config: flat) | -6.2 | -5.1 to -9.7 | 3.6 (reads -5.1 to -5.7 % over 790-900 m) |
| 960-1010 | turn 3 ramp-in | -11.6 | -9.7 to -13.3 | 6.6 |
| 1010-1450 | turns 3-4 plateau (config: -10 deg) | -17.0 | -13.5 to -17.8 | 9.6 |
| 1450-1500 | turn 4 exit ramp | -15.9 | -14.7 to -16.6 | 9.0 |
| 1500-1665 | front stretch dogleg (config: flat) | -13.0 | -12.3 to -14.7 | 7.4 |

## Compared with the repo's research

LAWS L10 and the config: PPIR is banked 10 degrees in all four turns, two arcs (s 215-730 and 960-1500, 50 m ramps), the straights flat, raised edge the right one (outside). **Agrees on the turns, disagrees on the straights.**

- The plateaus measure 17.2 % and 17.0 % mean (9.7 and 9.6 degrees) against 17.6 % for 10 degrees. The sign and the outside-edge-up check both agree (right edge higher on a counter-clockwise lap).
- Where the config is flat the lidar is not: the back stretch bottoms at -5.1 % (about 3 degrees) and the front-stretch dogleg across the start line reads -12 to -13 % (about 7 degrees). This repo's "do not invent banking" rule stands, but the config is missing this one; the deck is measured, not invented. The back stretch reading 3 degrees and the front stretch 7 degrees are both plane fits at 1 cm residual.
- The measured ramps are longer than the config's 50 m: the roll from straight to full bank is spread over roughly 100-150 m (for example -12.8 % at s 144 to -17.6 % at s 288, and -17.2 % at s 612 to -5.2 % at s 792). The config's turn windows (from line curvature) sit inside the lidar's.
- There is no off-camber corner. The worst roll rate is 3.03 % per 30 m.

## Confidence

**High for the numbers, moderate for the sections.** Every station is a clean plane (1-2 cm residual) from 2018 ground points. The sign and magnitude are consistent from station to station. The caveats are that the plane fit across 13 m of a banked oval measures the true cross-slope of the surface only if the line is on the pavement (the residuals say it is), and the "front stretch" and "back stretch" names are by station order and the config's windows, not by the track's own turn map.

## Caveats

- The 12 -> 20 % limit change is the only deviation from batch 1's method; it was needed because the track banks above 12 %.
- Lidar vintage 2018; class 2 only, no deck points (no declared bridge spans).
- A plane fit reads hillside or run-off fall if the line is near it; the filter only catches non-planar sections.

## Files

- `crossfall.json`: per-station `station_m`, `tilt_pct`, `bank_rad`, `raw_pct` (None = dropped) and summary.
- `crossfall.lidar.json`: the cached per-station plane fits, so the survey recomposes without the lidar libraries.
