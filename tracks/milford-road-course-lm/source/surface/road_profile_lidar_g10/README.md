# Milford's real road profile from the 2017 lidar (G10, 2026-11-24)

Kevin on 0.1.15 (2026-11-24): "Road still wavy". This measures the REAL road's longitudinal profile on the GM lap from
the raw 2017 lidar, so a PC session can tell whether the waviness is in the real road or ours. Measures only: no config
edits. Every number below is measured unless marked [invented], [model] or [inferred].

## Files

- `road_profile.lidar.g10.json`: per 0.5 m station (9,447, lap 4,723.7 m) and per path, the height `z_m` (null = gap),
  returns in the disc, noise, which flight strip(s) the returns come from, the two strips' offset where they overlap,
  each strip's own profile, the strip-levelled profiles; per 100 m window every metric; the build's profile on the same
  paths (`built`); the control (`control`). Station points are `x, z` + offset x `nx, nz` (+ = left of travel).
- `road_profile_lidar.py`: `read` (raw LAZ near the lap), `control`, `profile`, `built`. Its docstring has every rule.

## How

- **Line and lane.** `data/centerline.local.json` (md5 97e7b6f1), the build's swept line: the ribbon is +-w/2 about
  it, and the driven lane is its centre line (`ai/full/ai_draft.json` is a generated centreline draft, offset_max
  0.016 m). Paths: the lane centre and two wheel paths at +-0.8 m [invented, as asked].
- **Lidar.** USGS 3DEP Oakland 2016 (flown 2017), the EPT nodes at full depth (the ring read + the lap corridor read,
  union by node key; no node under the paths missing). Near the lap the cloud holds classes 1, 2 and 7 only: no road
  class, so class 2 (ground) alone; 63,380 returns within 3 m of the line, 7 / 10 / 15 per 1.25 m disc (p10/p50/p90).
- **Registration.** The build's: the lidar moved by `terrain.lidar_shift_m` (-0.375, +0.938) m (the measured surface's
  `registration_lidar_shift_m`, measured on 0.1.11's built OBJ), datum +0.1058 m (built - lidar, the deck inside), the
  G10 surface read's frame (EPSG:3857 -> lon/lat -> the port frame by mpd() about the line's origin).
- **Control.** At the G10 GM read's own centre-path points (the read `road_surface_gm.fit.json` was fitted from) this
  script's plane matches that read's y_m to p50 0.03 mm, p99 0.13 mm (98 % within 0.1 mm; 9,329 points).
- **Height.** wavy_survey's robust plane through the class-2 returns within 1.25 m (>= 6, two trimming passes); the
  disc averages ~2.5 m, so the band's 2-3 m end reads low [model]. Gaps: 136-157 stations per path, none over 2 m.
- **Metrics per 100 m.** 2-30 m: z less its 30 m moving average [invented, as asked], then 2 <= wavelength < 30 m; RMS,
  peak-to-peak, the dominant wavelength ("e" in the table: the spectrum's maximum sits on the band's 30 m edge, i.e. no
  peak inside, the spectrum keeps rising), the noise floor [model: the per-station noise, calibrated on this read's
  split halves (1.427), through the same band]. The steepest 5 m grade change [invented, as asked]:
  |(z(s+5) - z(s)) / 5 - (z(s) - z(s-5)) / 5| on the raw profile, with its noise. 30-60 / 60-120 m: band RMS.
- **Strips.** Two flight strips cover the lap, point_source_id 252 and 253, each one pass (~13 s of GPS time). 253
  alone on s 0-3,117 and 4,530-4,724; 252 alone on s 3,417-4,294; both on s 3,117-3,417 and 4,294-4,530 (3,124
  path-stations). Levelled two ways: a constant per strip (least squares over every overlap station), and linear in
  GPS time per strip [invented: the low-order fit].

## Results

Lap-wide (cm RMS, paths -0.8 / 0 / +0.8): 2-30 m 1.21 / 1.24 / 1.17 against a noise floor of 0.91-0.93 [model];
30-60 m 2.90 / 2.38 / 2.23; 60-120 m 10.35 / 9.93 / 9.42 (the 60-120 m band holds the hills' vertical curves).

**Strip offsets do not make the waves.** Where the strips overlap, 253 - 252 is p50 1.03 / p90 2.61 / max 6.35 cm per
station (the PC builder's 1.0 / 2.6 / 6.6), but that scatter is the per-station noise (the offset's own noise p50 1.0 cm;
mean -0.31 cm; zone means +0.3 and -1.2 cm). In the bands that matter the offset is 0.28-0.45 cm RMS at 30-60 m and
0.18-0.45 cm at 60-120 m (measured on the 300 m zone only; the 237 m zone is under 2 x 120 m), against 0.18-0.35 cm of
its own noise [model]: each strip's own along-track error there is
0-0.3 cm [inferred: two independent strips]. Levelling removes 0.01-0.04 cm of the lap's 30-60 / 60-120 m bands; per
100 m, 97-105 % of the band RMS survives. Away from the overlaps one strip covers the road alone and no strip offset can
reach its band. What this cannot see: an error both strips share.

**Built (committed files) against real.** The build's profile is `source/surface/road_surface_gm.fit.json` (c + u b at
the path, tools/measured_surface.py Product.at) plus `source/surface/road_section_gm.json` on s 870-1,030 (densify's
rule, 15 m taper); `data/centerline.local.json` Y + 0.10 + u tan(bank) (`data/crossfall.lm.json`) agrees with it to p50
0.1-0.2 mm, max 8.8 mm. 30-60 m: built 2.98 / 2.33 / 2.08 cm against real 2.90 / 2.38 / 2.23 (gain 1.00 / 0.94 / 0.90;
the difference 0.56-0.69 cm RMS); 60-120 m: gain 0.98-0.99 (difference 0.59-0.77 cm RMS). 2-30 m: built 0.41-0.53 cm
against real 1.17-1.24 (the fit cuts below 15-30 m by design). The installed mesh is the PC session's to compare.

Worst 2-30 m stretches (mean of the paths, cm; above the noise [model]): s 900-1,000 3.47 (3.03), 800-900 1.82 (1.51),
3,900-4,000 1.52 (0.90), 4,100-4,200 1.41 (0.91), 4,200-4,300 1.36 (0.84). Quietest: 2,800-2,900 0.80 (0.04),
4,400-4,500 0.83, 500-600 0.86. Steepest 5 m grade changes: 6.6 % at s 961 (-0.8 m), 6.15 % at s 922.5 (+0.8 m),
4.72 % at s 962.5 (centre), noise 0.7 %.

### Per 100 m (cm; the mean of the three paths; dominant per path -0.8 / 0 / +0.8; grade change the paths' max)

| s (m) | strips | 2-30 m RMS | noise [model] | dominant (m) | 5 m grade change max % (noise) | 30-60 m RMS | 60-120 m RMS | survives levelling (GPS-time linear) 30-60 / 60-120 | built - real band RMS 30-60 / 60-120 | gap stations (3 paths) |
|---|---|---|---|---|---|---|---|---|---|---|
| 0-100 | 253 | 1.05 | 0.84 | 26/25/24 | 1.61 (0.61) | 1.10 | 3.18 | 100 / 99 % | -0.02 / -0.04 | 26 |
| 100-200 | 253 | 1.06 | 0.89 | 8/19/21 | 1.68 (0.60) | 1.04 | 4.46 | 100 / 100 % | -0.03 / 0.15 | 29 |
| 200-300 | 253 | 0.97 | 0.92 | 22/23/20 | 2.03 (0.48) | 1.33 | 7.80 | 100 / 100 % | -0.21 / 0.10 | 7 |
| 300-400 | 253 | 1.10 | 0.86 | 15/24/22 | 2.21 (0.43) | 0.99 | 11.43 | 100 / 100 % | -0.14 / 0.07 | 2 |
| 400-500 | 253 | 0.98 | 0.85 | 30e/30e/30e | 2.65 (0.38) | 2.31 | 4.36 | 100 / 100 % | -0.54 / 0.02 | 0 |
| 500-600 | 253 | 0.86 | 0.83 | 26/20/20 | 1.38 (0.38) | 1.22 | 12.09 | 100 / 100 % | -0.01 / 0.33 | 1 |
| 600-700 | 253 | 1.11 | 0.90 | 29/28/28 | 2.98 (0.42) | 1.65 | 14.30 | 100 / 100 % | -0.10 / 0.15 | 14 |
| 700-800 | 253 | 1.22 | 0.92 | 30e/30e/30e | 3.12 (0.49) | 2.61 | 14.82 | 100 / 100 % | -0.39 / 0.08 | 17 |
| 800-900 | 253 | 1.82 | 1.02 | 30e/22/22 | 3.33 (0.75) | 4.24 | 21.45 | 100 / 100 % | -0.10 / -0.83 | 31 |
| 900-1000 | 253 | 3.47 | 1.60 | 21/22/30e | 6.60 (0.68) | 10.58 | 23.00 | 100 / 100 % | 1.02 / -0.19 | 14 |
| 1000-1100 | 253 | 1.23 | 0.95 | 7/21/30e | 2.90 (0.35) | 2.31 | 14.40 | 100 / 100 % | 0.11 / 0.35 | 11 |
| 1100-1200 | 253 | 1.02 | 0.88 | 25/25/23 | 1.38 (0.45) | 0.77 | 10.67 | 102 / 100 % | -0.11 / 0.39 | 2 |
| 1200-1300 | 253 | 1.05 | 0.87 | 20/15/16 | 1.65 (0.44) | 0.64 | 8.51 | 100 / 100 % | -0.15 / 0.06 | 1 |
| 1300-1400 | 253 | 1.18 | 0.97 | 6/22/9 | 2.09 (0.41) | 0.66 | 5.51 | 99 / 100 % | 0.24 / -0.01 | 6 |
| 1400-1500 | 253 | 1.09 | 0.92 | 22/30e/30e | 2.85 (0.33) | 2.59 | 16.41 | 100 / 100 % | -0.46 / -0.24 | 3 |
| 1500-1600 | 253 | 1.11 | 0.95 | 6/4/22 | 2.02 (0.45) | 1.92 | 20.19 | 100 / 100 % | -0.38 / -0.14 | 7 |
| 1600-1700 | 253 | 0.99 | 0.94 | 6/6/6 | 1.68 (0.38) | 0.76 | 15.48 | 100 / 100 % | 0.01 / -0.10 | 2 |
| 1700-1800 | 253 | 0.94 | 0.93 | 30e/15/24 | 1.81 (0.50) | 0.49 | 16.86 | 100 / 100 % | 0.09 / -0.22 | 2 |
| 1800-1900 | 253 | 1.04 | 0.88 | 30e/30e/30e | 2.68 (0.41) | 2.48 | 16.80 | 100 / 100 % | -0.43 / 0.02 | 1 |
| 1900-2000 | 253 | 1.01 | 0.82 | 21/6/27 | 2.32 (0.40) | 1.39 | 6.75 | 100 / 100 % | -0.03 / 0.00 | 0 |
| 2000-2100 | 253 | 0.98 | 0.84 | 13/22/8 | 1.81 (0.44) | 1.52 | 7.81 | 100 / 100 % | -0.06 / -0.01 | 0 |
| 2100-2200 | 253 | 0.99 | 0.90 | 10/24/26 | 1.61 (0.27) | 0.56 | 4.73 | 100 / 100 % | 0.04 / 0.21 | 1 |
| 2200-2300 | 253 | 1.12 | 0.89 | 19/29/28 | 1.95 (0.46) | 1.49 | 2.37 | 100 / 100 % | -0.30 / 0.05 | 2 |
| 2300-2400 | 253 | 0.90 | 0.87 | 18/18/9 | 1.72 (0.55) | 2.20 | 5.22 | 100 / 100 % | -0.35 / -0.15 | 3 |
| 2400-2500 | 253 | 1.10 | 0.95 | 30e/30e/30e | 3.06 (0.65) | 2.40 | 11.14 | 100 / 100 % | -0.29 / -0.47 | 4 |
| 2500-2600 | 253 | 0.97 | 0.84 | 30e/30e/30e | 2.00 (0.44) | 1.39 | 3.45 | 100 / 100 % | -0.32 / -0.36 | 0 |
| 2600-2700 | 253 | 1.00 | 0.83 | 14/8/8 | 2.07 (0.37) | 2.24 | 2.11 | 100 / 100 % | -0.30 / -0.12 | 0 |
| 2700-2800 | 253 | 0.96 | 0.79 | 11/28/30e | 2.32 (0.31) | 1.81 | 3.23 | 100 / 100 % | -0.17 / -0.14 | 0 |
| 2800-2900 | 253 | 0.80 | 0.82 | 8/8/25 | 2.15 (0.67) | 1.10 | 6.52 | 99 / 100 % | 0.16 / -0.15 | 0 |
| 2900-3000 | 253 | 0.96 | 0.84 | 30e/30e/30e | 1.75 (0.49) | 1.40 | 6.08 | 100 / 100 % | 0.01 / -0.20 | 1 |
| 3000-3100 | 253 | 0.98 | 0.81 | 19/8/22 | 1.71 (0.38) | 1.21 | 1.45 | 100 / 100 % | 0.09 / -0.12 | 2 |
| 3100-3200 | 252+253 | 0.98 | 0.65 | 30e/30e/22 | 1.67 (0.29) | 0.87 | 2.54 | 101 / 100 % | -0.07 / 0.17 | 0 |
| 3200-3300 | 252+253 | 1.02 | 0.77 | 22/16/17 | 2.02 (0.60) | 1.46 | 3.50 | 100 / 100 % | -0.67 / -0.34 | 0 |
| 3300-3400 | 252+253 | 0.98 | 0.64 | 30e/21/22 | 1.83 (0.41) | 1.73 | 8.02 | 100 / 100 % | -0.06 / -0.65 | 0 |
| 3400-3500 | 252+253 | 1.14 | 0.97 | 21/30e/30e | 2.34 (0.50) | 2.01 | 6.29 | 100 / 100 % | -0.62 / -0.30 | 1 |
| 3500-3600 | 252 | 1.06 | 0.97 | 10/21/22 | 2.21 (0.77) | 1.63 | 4.10 | 101 / 100 % | -0.12 / 0.11 | 4 |
| 3600-3700 | 252 | 1.14 | 0.90 | 8/15/16 | 1.91 (0.72) | 2.42 | 8.80 | 101 / 100 % | -0.40 / -0.47 | 0 |
| 3700-3800 | 252 | 1.10 | 0.94 | 30e/30e/30e | 2.08 (0.46) | 3.57 | 9.19 | 100 / 100 % | -0.59 / -1.05 | 0 |
| 3800-3900 | 252 | 1.12 | 0.99 | 24/7/6 | 1.91 (0.38) | 2.49 | 3.77 | 100 / 100 % | -0.08 / -0.16 | 2 |
| 3900-4000 | 252 | 1.52 | 1.20 | 8/8/30e | 2.19 (0.49) | 3.43 | 5.33 | 100 / 100 % | -0.08 / -0.01 | 23 |
| 4000-4100 | 252 | 1.28 | 1.08 | 14/20/20 | 2.27 (0.54) | 3.57 | 4.04 | 100 / 100 % | -0.27 / -0.16 | 29 |
| 4100-4200 | 252 | 1.41 | 1.06 | 10/18/11 | 2.58 (0.28) | 1.74 | 1.86 | 100 / 101 % | 0.17 / -0.40 | 37 |
| 4200-4300 | 252+253 | 1.36 | 1.05 | 29/30e/30e | 3.56 (0.60) | 2.83 | 7.39 | 101 / 100 % | -0.24 / -1.43 | 23 |
| 4300-4400 | 252+253 | 1.28 | 0.88 | 6/22/5 | 2.43 (0.65) | 2.60 | 7.11 | 100 / 100 % | -0.55 / -0.89 | 2 |
| 4400-4500 | 252+253 | 0.83 | 0.68 | 30e/30e/30e | 2.06 (0.38) | 1.78 | 2.69 | 99 / 100 % | -0.27 / 0.16 | 0 |
| 4500-4600 | 252+253 | 1.10 | 0.84 | 18/17/20 | 2.22 (0.82) | 0.80 | 2.17 | 105 / 97 % | -0.14 / 0.16 | 38 |
| 4600-4700 | 253 | 1.07 | 0.88 | 9/7/7 | 1.67 (0.40) | 0.84 | 3.03 | 101 / 100 % | -0.14 / 0.34 | 70 |
| 4700-4723 | 253 | 1.59 | 0.83 | 21/22/9 | 2.54 (0.34) | 0.65 | 4.11 | 101 / 99 % | -0.26 / -0.00 | 25 |
{"2-30 m rms_cm": {"worst5": [{"s": [900.0, 1000.0], "mean_of_paths_cm": 3.47}, {"s": [800.0, 900.0], "mean_of_paths_cm": 1.82}, {"s": [3900.0, 4000.0], "mean_of_paths_cm": 1.52}, {"s": [4100.0, 4200.0], "mean_of_paths_cm": 1.41}, {"s": [4200.0, 4300.0], "mean_of_paths_cm": 1.36}], "quietest3": [{"s": [2800.0, 2900.0], "mean_of_paths_cm": 0.8}, {"s": [4400.0, 4500.0], "mean_of_paths_cm": 0.83}, {"s": [500.0, 600.0], "mean_of_paths_cm": 0.86}]}, "2-30 m above_noise_rms_cm [model]": {"worst5": [{"s": [900.0, 1000.0], "mean_of_paths_cm": 3.03}, {"s": [800.0, 900.0], "mean_of_paths_cm": 1.51}, {"s": [4100.0, 4200.0], "mean_of_paths_cm": 0.91}, {"s": [4300.0, 4400.0], "mean_of_paths_cm": 0.9}, {"s": [3900.0, 4000.0], "mean_of_paths_cm": 0.9}], "quietest3": [{"s": [2800.0, 2900.0], "mean_of_paths_cm": 0.04}, {"s": [1700.0, 1800.0], "mean_of_paths_cm": 0.14}, {"s": [500.0, 600.0], "mean_of_paths_cm": 0.17}]}, "30-60 m merged_cm": {"worst5": [{"s": [900.0, 1000.0], "mean_of_paths_cm": 10.58}, {"s": [800.0, 900.0], "mean_of_paths_cm": 4.24}, {"s": [4000.0, 4100.0], "mean_of_paths_cm": 3.57}, {"s": [3700.0, 3800.0], "mean_of_paths_cm": 3.57}, {"s": [3900.0, 4000.0], "mean_of_paths_cm": 3.43}], "quietest3": [{"s": [1700.0, 1800.0], "mean_of_paths_cm": 0.49}, {"s": [2100.0, 2200.0], "mean_of_paths_cm": 0.56}, {"s": [1200.0, 1300.0], "mean_of_paths_cm": 0.64}]}, "60-120 m merged_cm": {"worst5": [{"s": [900.0, 1000.0], "mean_of_paths_cm": 23.0}, {"s": [800.0, 900.0], "mean_of_paths_cm": 21.45}, {"s": [1500.0, 1600.0], "mean_of_paths_cm": 20.19}, {"s": [1700.0, 1800.0], "mean_of_paths_cm": 16.86}, {"s": [1800.0, 1900.0], "mean_of_paths_cm": 16.8}], "quietest3": [{"s": [3000.0, 3100.0], "mean_of_paths_cm": 1.45}, {"s": [4100.0, 4200.0], "mean_of_paths_cm": 1.86}, {"s": [2600.0, 2700.0], "mean_of_paths_cm": 2.11}]}}
{"-0.8": {"station_off_fit_line_m": {"p50_abs": 0.048, "max_abs": 1.178}, "fit_minus_line_m": {"p50_abs": 0.0002, "max_abs": 0.0072}, "built_minus_real_m": {"median": 0.002, "p90_abs": 0.0359}, "2-30 m": {"built_cm": 0.41, "real_cm": 1.21, "real_levelled_cm": 1.21, "built_minus_real_rms_cm": 1.13, "gain_built_on_real": 0.12, "gain_built_on_levelled": 0.12}, "30-60 m": {"built_cm": 2.98, "real_cm": 2.9, "real_levelled_cm": 2.9, "built_minus_real_rms_cm": 0.69, "gain_built_on_real": 1.0, "gain_built_on_levelled": 1.0}, "60-120 m": {"built_cm": 10.13, "real_cm": 10.35, "real_levelled_cm": 10.35, "built_minus_real_rms_cm": 0.77, "gain_built_on_real": 0.98, "gain_built_on_levelled": 0.98}}, "+0.0": {"station_off_fit_line_m": {"p50_abs": 0.048, "max_abs": 1.178}, "fit_minus_line_m": {"p50_abs": 0.0001, "max_abs": 0.0082}, "built_minus_real_m": {"median": 0.0002, "p90_abs": 0.0359}, "2-30 m": {"built_cm": 0.53, "real_cm": 1.24, "real_levelled_cm": 1.24, "built_minus_real_rms_cm": 1.09, "gain_built_on_real": 0.21, "gain_built_on_levelled": 0.21}, "30-60 m": {"built_cm": 2.33, "real_cm": 2.38, "real_levelled_cm": 2.38, "built_minus_real_rms_cm": 0.67, "gain_built_on_real": 0.94, "gain_built_on_levelled": 0.94}, "60-120 m": {"built_cm": 9.77, "real_cm": 9.93, "real_levelled_cm": 9.93, "built_minus_real_rms_cm": 0.76, "gain_built_on_real": 0.98, "gain_built_on_levelled": 0.98}}, "+0.8": {"station_off_fit_line_m": {"p50_abs": 0.048, "max_abs": 1.178}, "fit_minus_line_m": {"p50_abs": 0.0002, "max_abs": 0.0088}, "built_minus_real_m": {"median": -0.0011, "p90_abs": 0.0316}, "2-30 m": {"built_cm": 0.47, "real_cm": 1.17, "real_levelled_cm": 1.17, "built_minus_real_rms_cm": 1.11, "gain_built_on_real": 0.13, "gain_built_on_levelled": 0.13}, "30-60 m": {"built_cm": 2.08, "real_cm": 2.23, "real_levelled_cm": 2.23, "built_minus_real_rms_cm": 0.56, "gain_built_on_real": 0.9, "gain_built_on_levelled": 0.9}, "60-120 m": {"built_cm": 9.35, "real_cm": 9.42, "real_levelled_cm": 9.42, "built_minus_real_rms_cm": 0.59, "gain_built_on_real": 0.99, "gain_built_on_levelled": 0.99}}}

## Rerun (on the G10; the lidar is not in the repo)

```
python -I road_profile_lidar.py read --line data/centerline.local.json --lidar RING_DIR --lidar MF_LIDAR_DIR --out points.npz
python -I road_profile_lidar.py control --line data/centerline.local.json --points points.npz --g10-read GM_READ.json --out control.json
python -I road_profile_lidar.py profile --line data/centerline.local.json --points points.npz --out profile.json
python -I road_profile_lidar.py built --profile profile.json --fit source/surface/road_surface_gm.fit.json \
    --section source/surface/road_section_gm.json --crossfall data/crossfall.lm.json \
    --line data/centerline.local.json --measured-surface tools/measured_surface.py --control control.json \
    --out road_profile.lidar.g10.json
```

Wall time on the G10: 5 + 10 + 53 + 2 s, peak RSS 151 MB, at nice 19 / idle IO.

## The real asphalt edges on six stretches (`edges_curves.py`, `milford_edges_curves.lidar.g10.json`)

Asked after the PC builder found width swells ("blooms", Kevin) on s 1,114-1,270 and 1,557-1,857 that its NAIP-mask
edges do not support, and the pavement's centre 0.3-0.8 m inside the line on the tight curves. Same line, stations and
registration as above. All six stretches lie in strip 253 alone.

- **Edge.** Per station and side, the class-2 returns within 3.5 m of the built lane edge (never nearer the line than
  1 m), each placed on the line exactly (its nearest point of a 0.1 m resampling, so a tight curve does not skew it).
  The edge is source/edges/measure_edges.py's lidar rule: the two-level intensity step, dark asphalt inside and bright
  verge outside, 1 m along, kept at contrast >= 3,000 (its measured threshold). Here the contrast is strong: p50
  13,000-28,000, t p50 4-11. A height break (two lines, a 3 cm step [invented]) is fitted too, but it lands 1.5-3 m
  (IQR) either side of the intensity step (ditches, cut slopes), so it is reported and never used. 437-597 stations per
  stretch read both edges (750-1,015: 437 of 530).
- **Width** (left - right) does not depend on the registration. **Centre** ((left + right) / 2) does: the build's
  lidar shift (-0.375, +0.938) and ledger 0087's edge registration of the lidar to NAIP, the frame the line was traced
  in (-0.119, +0.329), are 0.66 m apart. Both are given. Also, the lidar's intensity step reads 0.26 m per side inside
  NAIP's edge on average (ledger 0087), so about 0.5 m of any built - lidar width may be the sensor.
- **Steady or swelling.** A straight line is fitted through the real width. "Steady" unless 3 or more 5 m bins in a
  row sit more than 2 x their own noise off it on the same side [invented].

| s | turn, R median | real width (line fit start -> end; bin resid RMS / bin noise) | built width | built - real median (bin max) | centre toward inside: build reg / NAIP-frame reg |
|---|---|---|---|---|---|
| 1,114-1,270 | right, 92 m | steady, 10.39 -> 10.76 m (0.28 / 0.27) | 10.59-12.18 | +0.63 (+1.65) | -0.78 / -0.23 (outside) |
| 1,557-1,857 | left, 93 m | steady, 10.57 -> 10.69 m (0.26 / 0.24) | 10.74-12.17 | +0.76 (+1.96) | +0.37 / -0.05 |
| 580-660 | left, 81 m | steady, 10.46 -> 10.96 m (0.25 / 0.22) | 11.38-11.82 | +0.96 (+1.35) | -0.94 / -0.33 (outside) |
| 750-1,015 | left, 86 m (min 19) | not steady: 10.4-12.3 m on s 750-835, then 14-17.8 m on s 840-1,015 (the inner banked turn) | 11.82-16.00 | +0.33 (+2.35; -1.2 to -1.8 on s 875-940, the 16 m cap) | -0.47 / -0.48; on s 905-965 (R < 50 m) -0.42 / -0.94 |
| 1,275-1,335 | right, 96 m (min 28) | steady by the rule, 11.55 -> 10.00 m (0.70 / 0.32) | 10.41-12.19 | +0.69 (+2.36) | on s 1,295-1,316 (R < 50 m) +1.35 / +1.72 |
| 1,625-1,695 | left, 91 m | steady, 10.24 -> 10.73 m (0.17 / 0.21) | 11.64-12.17 | +1.58 (+1.91) | +0.60 / +0.01 |

So the real width holds steady through both bloom stretches, and the build is the wider one: 0.6-0.8 m in the median,
up to 1.6-2.0 m in places, past the 0.5 m the two sensors differ by. The centre is no single "inside" offset. Under the
build's registration, 1,557-1,857, 1,625-1,695 and 1,295-1,316 sit inside (0.4-1.4 m) while 1,114-1,270, 580-660 and
the banked turn sit outside (0.4-0.9 m). In NAIP's frame the sweepers' offsets shrink to 0.0-0.3 m. The lidar cannot
settle a centre offset under ~0.6 m until the registration is settled. On s 945-965 the banked turn's outer (right)
edge has weak contrast (1,300-4,800), and s 1,325-1,335 also reads weak (3,900-8,900): low confidence there.

```
python -I edges_curves.py read --line data/centerline.local.json --lidar RING_DIR --lidar MF_LIDAR_DIR --out edge_points.npz
python -I edges_curves.py edges --line data/centerline.local.json --points edge_points.npz --out milford_edges_curves.lidar.g10.json
```

G10: 3 + 18 s. edges_curves.py imports road_profile_lidar.py from beside it.
