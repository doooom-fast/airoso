# Milford Road Course: lidar cross-slope survey

Research only. Nothing here is applied to any build; the files live under `source/` so no build picks them up.
Measured on the G10 (Linux) with `tools/lidar_crossfall.py` from branch `claude/sand-creek-camber`, 2026-11-03.

- **EPT project:** `USGS_LPC_MI_31Co_Oakland_2016_LAS_2019` (USGS 3DEP, `https://s3-us-west-2.amazonaws.com/usgs-lidar-public/USGS_LPC_MI_31Co_Oakland_2016_LAS_2019/ept.json`)
- **Line:** `data/finished_centerline.json` (identical on main), lap 4904.4 m, 3 m stations, + = left side higher.
- **Half-width used:** 5.0 m (track 9-21.7 m wide, median 12.2 m). The tool hard-codes 4.5 m (a 9 m street); it was overridden for this survey.
- **Other thresholds overridden:** MAX_READ_PCT 8 -> 12 %, MAX_SD_M 0.08 -> 0.10 m, CAP_PCT 6 -> 12 % (circuits bank more than streets; the 6 % cap would flatten Turn-2-class banks). The 0.2 %/m roll-rate limit and 9 m smoothing are the tool's own. Values are recorded in `crossfall.json` `params`.
- **Wall time on the G10:** 97 s (fetch + fit, nice 19, 4 GB cap).

## Numbers (`crossfall.json` `tilt_pct`: filled, smoothed, rate-limited)

- Stations: 1635; dropped (not a road fit, filled): 109
- |tilt| p50 4.36 %, p95 10.71 %, max 11.87 %
- Banked (|tilt| >= 2 %): 66.9 % of stations
- Worst roll change per 30 m: 6.0 % (tool); 6.0 % at s 984 (re-measured on the composed tilt)
- In corners of >= 15 degrees per 30 m that read >= 2 %: 135 stations banked into the turn, 24 off-camber

## Sustained banking (|tilt| >= 2 %, longer than 30 m, one sign)

Sign: + = left side higher. Banked into the turn = the inside edge is lower. Stations are along the finished line.

| s start-end (m) | length (m) | sign | peak % | mean % | relative to the turn |
|---|---|---|---|---|---|
| 0-384 | 384 | + | +11.9 | +7.8 | banked into the turn (-89 deg) |
| 429-513 | 84 | + | +5.4 | +3.7 | banked into the turn (-54 deg) |
| 894-984 | 90 | - | -6.8 | -4.3 | banked into the turn (+27 deg) |
| 1005-1143 | 138 | + | +8.5 | +5.1 | OFF-CAMBER (+69 deg) |
| 1224-1269 | 45 | + | +5.4 | +3.9 | banked into the turn (-11 deg) |
| 1530-1569 | 39 | + | +2.6 | +2.4 | straight/gentle (-5 deg) |
| 1908-2106 | 198 | - | -10.6 | -7.4 | banked into the turn (+86 deg) |
| 2472-3102 | 630 | + | +11.4 | +8.8 | banked into the turn (-138 deg) |
| 3165-3318 | 153 | + | +3.7 | +2.9 | straight/gentle (+2 deg) |
| 3336-4722 | 1386 | + | +11.7 | +8.4 | banked into the turn (-185 deg) |
| 4731-4809 | 78 | + | +2.6 | +2.2 | straight/gentle (+5 deg) |
| 4869-4905 | 36 | + | +2.2 | +2.1 | straight/gentle (+1 deg) |

## Compared with the repo's research

No banking is authored (config `road_profile`, L10); its note records 1 m lidar sections of -4.3 % in the esses (s 620), -7.1 % at the U-turn (s 780, likeliest Carousel) and +8.0 % at s 995, and that applying a measured 6 %-capped crossfall made drive_test worse (ledger-0018 class). DOSSIER lists the Circle Track as a banked concrete parabolic curve and Seven Sisters superelevation 1.5-7 %. **The lidar agrees in kind and magnitude**: a -6.8 % peak run at s 894-984 (left turn, banked into it), -10.6 % at s 1908-2106 (193-degree left, banked into), and +8.5 % at s 1005-1143. The station numbers differ from the config note by roughly 100-300 m, which is not explained here: the config's s values likely come from another line. Treat the config's values as the same features, not a precise match. The 1.4 km run at +8..+10 % (s 3336-4722) and the 630 m run at +10 % (s 2472-3102) are new to the repo's notes: they follow right-hand sweepers, consistent with the dossier's banked Circle Track, but they could include hillside cross-fall (the config describes a hillside cut near s 3650), so they are not proof of road banking.

## Caveats

- Milford is the least trustworthy of the three: 67 % of the lap reads at least 2 % and the 109 dropped stations are where the fit failed. A fixed 5 m half-width is narrower than the widest sections (up to 21.7 m) and wider than the narrowest (9 m, where it would reach past the edge).
- A plane fit across the half-width reads hillside or run-off fall if the line is near it; the tool's own filter (residual sd and read limit) only catches non-planar sections.
- Lidar vintage and class: ground (class 2) points only, no deck points used (no declared bridge spans).

## Files

- `crossfall.json`: per-station `station_m`, `tilt_pct`, `bank_rad`, `raw_pct` (None = dropped) and summary.
- `crossfall.lidar.json`: the cached per-station plane fits, so the survey recomposes without the lidar libraries.
