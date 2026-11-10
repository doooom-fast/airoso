# Dragon Tail (gravel): lidar cross-slope survey

Research only. Nothing here is applied to any build; the files live under `source/` so no build picks them up.
Measured on the G10 (Linux) with `tools/lidar_crossfall.py` from branch `claude/sand-creek-camber`, 2026-11-03.

**LOW CONFIDENCE. Most of this stage did not fit a road plane (see Reliability). Do not build from these numbers.**

- **EPT project:** `CO_NWCO_1_2020` (USGS 3DEP, `https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_NWCO_1_2020/ept.json`), the only project covering the stage origin.
- **Line:** `data/finished_centerline.json`, 25258.5 m, 3 m stations, + = left side higher, **open point-to-point (L11/L13)**.
- **Half-width used:** 2.25 m (config width 6.5 m, half 3.25 m minus 1 m). The tool hard-codes 4.5 m.
- **Open-stage handling (wrapper, tool unchanged):** heading clamped at both ends instead of wrapping, and `compose()` padded with 25 flat stations each end so the cyclic fill, smooth and roll-rate limiter never join the stage end to its start. The first and last ~75 m are therefore damped toward 0 and should be ignored.
- **Other thresholds overridden:** MAX_READ_PCT 8 -> 12 %, MAX_SD_M 0.08 -> 0.10 m, CAP_PCT 6 -> 12 %.
- **Wall time on the G10:** 520 s.

## Reliability

Station fits: 1540 usable, 5435 rejected for residual sd over 0.10 m, 1408 for a read over 12 %, 37 with fewer than 12 points. Median residual sd of all fits is 0.14 m, which is a rough gravel surface, a crowned or ditched section, or a line sitting off the road; a gravel road is not a flat plane. Only 18 % of stations are measured; the rest are filled between neighbours (gaps up to 30 m) or held flat. The tilt statistics below therefore describe the cleanest 18 % only, and the composed `tilt_pct` is zero over most of the stage.

## Numbers

- Stations: 8420; dropped (not a road fit, filled/flat): 6880
- Composed `tilt_pct` (mostly flat-filled): |tilt| p50 0.0 %, p95 6.76 %, max 11.38 %
- Measured stations only (`raw_pct`): |tilt| p50 5.1 %, p95 11.0 %, max 12.0 %
- Banked (|tilt| >= 2 %, composed): 28.4 % of stations
- Worst roll change per 30 m: 6.0 % at s 1404. 6.0 % is the roll-rate limiter's ceiling (0.2 %/m), so this is a clipped ramp from a filled gap edge, not a real roll.
- Runs of >= 2 % longer than 30 m: 76; relative to the turn: 14 banked into it, 22 off-camber, 40 on straights or gentle bends (net heading change under 8 degrees).

## Largest runs (12 of 76, by peak; full list recomputable from `crossfall.json`)

Sign: + = left side higher. Banked into the turn = inside edge lower.

| s start-end (m) | length (m) | sign | peak % | mean % | relative to the turn |
|---|---|---|---|---|---|
| 6804-6945 | 141 | + | +9.3 | +6.4 | straight/gentle (+8 deg) |
| 9909-10038 | 129 | + | +8.9 | +5.9 | OFF-CAMBER (+11 deg) |
| 12909-13212 | 303 | + | +11.4 | +7.0 | straight/gentle (-2 deg) |
| 13284-13437 | 153 | + | +9.0 | +6.1 | OFF-CAMBER (+11 deg) |
| 16134-16338 | 204 | - | -9.1 | -6.1 | OFF-CAMBER (-51 deg) |
| 16503-16632 | 129 | - | -8.9 | -4.9 | OFF-CAMBER (-57 deg) |
| 16656-16755 | 99 | - | -9.0 | -5.6 | banked into the turn (+12 deg) |
| 19518-19695 | 177 | - | -9.9 | -6.7 | OFF-CAMBER (-24 deg) |
| 21696-21774 | 78 | - | -9.2 | -5.8 | banked into the turn (+19 deg) |
| 22017-22206 | 189 | - | -9.8 | -6.2 | OFF-CAMBER (-41 deg) |
| 23934-24042 | 108 | + | +9.1 | +6.4 | straight/gentle (-4 deg) |
| 24195-24339 | 144 | + | +11.1 | +6.7 | OFF-CAMBER (+22 deg) |

## Compared with the repo's research

The repo has no banking research for this stage. Tilts of 4-6 % on straights and off-camber and banked-into runs in roughly equal numbers, with the sign changing between runs, look like road crown, ditches and hillside fall rather than designed superelevation. I would not read any of this as banking.

## Files

- `crossfall.json`: per-station `station_m`, `tilt_pct`, `bank_rad`, `raw_pct` (None = dropped) and summary.
- `crossfall.lidar.json`: cached per-station plane fits, with the sd for each, so another threshold can be recomposed without refetching.
