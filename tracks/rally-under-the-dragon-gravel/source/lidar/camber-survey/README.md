# Under the Dragon (gravel): lidar cross-slope survey

Research only. Nothing here is applied to any build; the files live under `source/` so no build picks them up.
Measured on the G10 (Linux) with `tools/lidar_crossfall.py` from branch `claude/sand-creek-camber`, 2026-11-03.

**LOW CONFIDENCE. Most of this stage did not fit a road plane (see Reliability). Do not build from these numbers.**

- **EPT project:** `CO_NWCO_1_2020` (USGS 3DEP, `https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_NWCO_1_2020/ept.json`), the only project covering the stage origin.
- **Line:** `data/finished_centerline.json`, 25706.1 m, 3 m stations, + = left side higher, **open point-to-point (L11/L13)**.
- **Half-width used:** 2.25 m (config width 6.5 m, half 3.25 m minus 1 m). The tool hard-codes 4.5 m.
- **Open-stage handling (wrapper, tool unchanged):** heading clamped at both ends instead of wrapping, and `compose()` padded with 25 flat stations each end so the cyclic fill, smooth and roll-rate limiter never join the stage end to its start. The first and last ~75 m are therefore damped toward 0 and should be ignored.
- **Other thresholds overridden:** MAX_READ_PCT 8 -> 12 %, MAX_SD_M 0.08 -> 0.10 m, CAP_PCT 6 -> 12 %.
- **Wall time on the G10:** 405 s.

## Reliability

Station fits: 2600 usable, 4858 rejected for residual sd over 0.10 m, 1072 for a read over 12 %, 39 with fewer than 12 points. Median residual sd of all fits is 0.13 m, which is a rough gravel surface, a crowned or ditched section, or a line sitting off the road; a gravel road is not a flat plane. Only 30 % of stations are measured; the rest are filled between neighbours (gaps up to 30 m) or held flat. The tilt statistics below therefore describe the cleanest 30 % only, and the composed `tilt_pct` is zero over most of the stage.

## Numbers

- Stations: 8569; dropped (not a road fit, filled/flat): 5969
- Composed `tilt_pct` (mostly flat-filled): |tilt| p50 0.53 %, p95 6.86 %, max 11.53 %
- Measured stations only (`raw_pct`): |tilt| p50 3.9 %, p95 10.5 %, max 12.0 %
- Banked (|tilt| >= 2 %, composed): 34.1 % of stations
- Worst roll change per 30 m: 6.0 % at s 2988. 6.0 % is the roll-rate limiter's ceiling (0.2 %/m), so this is a clipped ramp from a filled gap edge, not a real roll.
- Runs of >= 2 % longer than 30 m: 91; relative to the turn: 26 banked into it, 28 off-camber, 37 on straights or gentle bends (net heading change under 8 degrees).

## Largest runs (12 of 91, by peak; full list recomputable from `crossfall.json`)

Sign: + = left side higher. Banked into the turn = inside edge lower.

| s start-end (m) | length (m) | sign | peak % | mean % | relative to the turn |
|---|---|---|---|---|---|
| 1998-2148 | 150 | - | -10.5 | -6.7 | straight/gentle (-1 deg) |
| 6891-7197 | 306 | + | +10.0 | +6.2 | banked into the turn (-37 deg) |
| 9210-9348 | 138 | + | +9.0 | +6.0 | straight/gentle (-7 deg) |
| 11247-11478 | 231 | - | -11.4 | -6.9 | banked into the turn (+66 deg) |
| 12912-13020 | 108 | + | +8.9 | +5.6 | banked into the turn (-10 deg) |
| 13053-13455 | 402 | + | +11.5 | +6.8 | banked into the turn (-114 deg) |
| 13791-13974 | 183 | + | +9.8 | +6.0 | banked into the turn (-26 deg) |
| 15852-15933 | 81 | + | +9.1 | +5.9 | OFF-CAMBER (+12 deg) |
| 17571-17658 | 87 | - | -8.7 | -5.8 | banked into the turn (+42 deg) |
| 18417-18579 | 162 | + | +9.7 | +6.7 | OFF-CAMBER (+21 deg) |
| 18987-19134 | 147 | - | -9.5 | -6.3 | OFF-CAMBER (-16 deg) |
| 23244-23334 | 90 | - | -8.9 | -5.9 | OFF-CAMBER (-56 deg) |

## Compared with the repo's research

The repo has no banking research for this stage. Tilts of 4-6 % on straights and off-camber and banked-into runs in roughly equal numbers, with the sign changing between runs, look like road crown, ditches and hillside fall rather than designed superelevation. I would not read any of this as banking.

## Files

- `crossfall.json`: per-station `station_m`, `tilt_pct`, `bank_rad`, `raw_pct` (None = dropped) and summary.
- `crossfall.lidar.json`: cached per-station plane fits, with the sd for each, so another threshold can be recomposed without refetching.
