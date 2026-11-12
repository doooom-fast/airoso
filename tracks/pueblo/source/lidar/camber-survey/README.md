# Pueblo Motorsports Park: lidar cross-slope survey

Research only. Nothing here is applied to any build. **No measurement: the USGS 3DEP EPT lidar has no coverage at this site.** No numbers are given and no `crossfall.json` is written.

Run on the G10 (Linux) with `tools/lidar_crossfall.py` from branch `claude/sand-creek-0.33.0`, 2026-11-03, with the batch-1 settings (half-width 5.0 m = 12 m `default_width_m` half minus 1 m; MAX_READ_PCT 12 %, MAX_SD_M 0.10 m, CAP_PCT 12 %).

- **Line:** `data/finished_centerline.json` from branch `claude/new-tracks-pueblo-pikes`, lap 3507 m (1169 stations at 3 m).
- **Result:** 0 of 1169 stations had a road fit. The tool fetched 4 EPT nodes from `CO_Eastern_B5_2018` (the only EPT project whose bounds contain the site) and none held a point within the 5 m half-width plus margin of the line. A point-by-point check of those nodes (class 1/2/7/9/18/17 histogram, distance to the line) found the nearest point 10.7 km from the line, i.e. the nodes are the coarse thinned levels of a project whose dense data stops elsewhere.
- **Other projects:** bounding-box or hierarchy check of every Colorado, New Mexico, Utah, Wyoming and Kansas project in the `usgs-lidar-public` bucket: `USGS_LPC_CO_Central_Western_2016_LAS_2018` and two `USGS_LPC_NM_NRCS_Central_*` projects also overlap the site's bounding box but have no nodes deeper than 1-2 levels there. None is dense at the site.
- **Fetch failures:** none. The EPT requests all succeeded, so this is a coverage gap, not a network error, and a retry would give the same result.

## Compared with the repo's research

Config: "Flat road course, no banking (not an oval)". The lidar can neither confirm nor refute it. Another source would be needed (a county or state lidar tile not in the 3DEP EPT bucket, a ground survey, or the Windows drive).

## Confidence

None. No measurement.

## Files

- This README only.
