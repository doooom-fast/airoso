# High Plains Raceway: lidar cross-slope survey

Research only. Nothing here is applied to any build; the files live under `source/` so no build picks them up.
Measured on the G10 (Linux) with `tools/lidar_crossfall.py` from branch `claude/sand-creek-camber`, 2026-11-03.

- **EPT project:** `CO_Eastern_B3_2018` (USGS 3DEP, `https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_Eastern_B3_2018/ept.json`)
- **Line:** `data/finished_centerline.json` (identical on main), lap 3216.3 m, 3 m stations, + = left side higher.
- **Half-width used:** 5.0 m (track 12 m wide). The tool hard-codes 4.5 m (a 9 m street); it was overridden for this survey.
- **Other thresholds overridden:** MAX_READ_PCT 8 -> 12 %, MAX_SD_M 0.08 -> 0.10 m, CAP_PCT 6 -> 12 % (circuits bank more than streets; the 6 % cap would flatten Turn-2-class banks). The 0.2 %/m roll-rate limit and 9 m smoothing are the tool's own. Values are recorded in `crossfall.json` `params`.
- **Wall time on the G10:** 49 s (fetch + fit, nice 19, 4 GB cap).

## Numbers (`crossfall.json` `tilt_pct`: filled, smoothed, rate-limited)

- Stations: 1073; dropped (not a road fit, filled): 0
- |tilt| p50 1.18 %, p95 2.25 %, max 3.03 %
- Banked (|tilt| >= 2 %): 8.3 % of stations
- Worst roll change per 30 m: 1.51 % (tool); 1.51 % at s 3099 (re-measured on the composed tilt)
- In corners of >= 15 degrees per 30 m that read >= 2 %: 57 stations banked into the turn, 0 off-camber

## Sustained banking (|tilt| >= 2 %, longer than 30 m, one sign)

Sign: + = left side higher. Banked into the turn = the inside edge is lower. Stations are along the finished line.

| s start-end (m) | length (m) | sign | peak % | mean % | relative to the turn |
|---|---|---|---|---|---|
| 1497-1560 | 63 | + | +3.0 | +2.7 | banked into the turn (-48 deg) |
| 2253-2430 | 177 | + | +3.0 | +2.4 | banked into the turn (-86 deg) |

## Compared with the repo's research

LAWS L10: High Plains runs 1.5-4 % with a deliberately off-camber Turn 1. **Partly agrees.** The lidar finds a gentle, uniformly left-high-leaning lap (p50 1.2 %, max 3.0 %, inside the researched 1.5-4 % range), so the magnitude agrees. Two runs reach 2 % or more and both are right-handers banked into the turn. It does NOT show a clearly off-camber corner: the only left-hander on the early lap (s 189-258, 71 degrees, probably Turn 1 if the line runs in the researched direction, which was not checked) reads -1.0 % into-turn, i.e. 1 % off-camber, below the 2 % run threshold. Left-hand corners later in the lap (s 1659-1740, 2598-2688, 2940-2997) read banked into the turn by 0.9-1.7 % (the sign flips against the earlier left). Turn-1 identification is by station order only; confirm against the track's own turn map before drawing a conclusion.

## Caveats

- The 0 dropped stations and flat p50 (1.2 %) mean this is a well-behaved paved plane at 12 m; a 5 m half-width covers only the central 10 m of the 12 m ribbon.
- A plane fit across the half-width reads hillside or run-off fall if the line is near it; the tool's own filter (residual sd and read limit) only catches non-planar sections.
- Lidar vintage and class: ground (class 2) points only, no deck points used (no declared bridge spans).

## Files

- `crossfall.json`: per-station `station_m`, `tilt_pct`, `bank_rad`, `raw_pct` (None = dropped) and summary.
- `crossfall.lidar.json`: the cached per-station plane fits, so the survey recomposes without the lidar libraries.
