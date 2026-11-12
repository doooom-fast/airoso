# Aspen Motorsports Park (Woody Creek): lidar cross-slope survey

Research only. Nothing here is applied to any build. **No measurement: the USGS 3DEP EPT lidar has no coverage at this site.** No numbers are given and no `crossfall.json` is written.

Run on the G10 (Linux) with `tools/lidar_crossfall.py` from branch `claude/sand-creek-0.33.0`, 2026-11-03, with the batch-1 settings (half-width 3.5 m = 9 m `default_width_m` half minus 1 m; MAX_READ_PCT 12 %, MAX_SD_M 0.10 m, CAP_PCT 12 %).

- **Line:** `data/finished_centerline.json` from branch `claude/aspen-profile-kink`, lap 1671 m (557 stations at 3 m).
- **Result:** 0 of 557 stations had a road fit in any of the six EPT projects whose bounds or hierarchy touch the site: `USGS_LPC_CO_Central_Western_2016_LAS_2018`, `CO_SanLuisJuanMiguel_2_2020`, `CO_WestCentral_2019`, `CO_NWCO_2_2020`, `CO_ArkansasValley_2010`, `CO_UpperColorado_Hydroflattened_2020`. Each run fetched 2-9 coarse nodes and none held a point within the 5 m half-width plus margin of any station.
- **Nearest data:** for the three projects checked point by point, the nearest point to the line is 2.9 km away (`CO_SanLuisJuanMiguel_2_2020`), 10.7 km (`USGS_LPC_CO_Central_Western_2016_LAS_2018`) or 14.4 km (`CO_WestCentral_2019`). These nodes are the thinned upper levels of large projects, not dense data at the site.
- **Fetch failures:** none. The EPT requests all succeeded, so this is a coverage gap, not a network error, and a retry would give the same result.

## Compared with the repo's research

Config: "Flat road course, no banking". The lidar can neither confirm nor refute it. Another source would be needed (a Pitkin County lidar tile outside the 3DEP EPT bucket, a ground survey, or the Windows drive).

## Confidence

None. No measurement.

## Files

- This README only.
