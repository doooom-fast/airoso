# Nevada Nights / Exotics Racing LV: lidar cross-slope survey

Research only. Nothing here is applied to any build; the files live under `source/` so no build picks them up.
Measured on the G10 (Linux) with `tools/lidar_crossfall.py` from branch `claude/sand-creek-camber`, 2026-11-03.

- **EPT project:** `NV_ClarkCo_2_B22` (USGS 3DEP, `https://s3-us-west-2.amazonaws.com/usgs-lidar-public/NV_ClarkCo_2_B22/ept.json`)
- **Line:** `data/finished_centerline.json` (identical on main), lap 1819.2 m, 3 m stations, + = left side higher.
- **Half-width used:** 5.8 m (track median 13.6 m wide). The tool hard-codes 4.5 m (a 9 m street); it was overridden for this survey.
- **Other thresholds overridden:** MAX_READ_PCT 8 -> 12 %, MAX_SD_M 0.08 -> 0.10 m, CAP_PCT 6 -> 12 % (circuits bank more than streets; the 6 % cap would flatten Turn-2-class banks). The 0.2 %/m roll-rate limit and 9 m smoothing are the tool's own. Values are recorded in `crossfall.json` `params`.
- **Wall time on the G10:** 62 s (fetch + fit, nice 19, 4 GB cap).

## Numbers (`crossfall.json` `tilt_pct`: filled, smoothed, rate-limited)

- Stations: 607; dropped (not a road fit, filled): 7
- |tilt| p50 2.01 %, p95 10.37 %, max 10.58 %
- Banked (|tilt| >= 2 %): 51.1 % of stations
- Worst roll change per 30 m: 3.08 % (tool); 3.08 % at s 954 (re-measured on the composed tilt)
- In corners of >= 15 degrees per 30 m that read >= 2 %: 78 stations banked into the turn, 7 off-camber

## Sustained banking (|tilt| >= 2 %, longer than 30 m, one sign)

Sign: + = left side higher. Banked into the turn = the inside edge is lower. Stations are along the finished line.

| s start-end (m) | length (m) | sign | peak % | mean % | relative to the turn |
|---|---|---|---|---|---|
| 42-75 | 33 | + | +2.2 | +2.1 | straight/gentle (+0 deg) |
| 198-537 | 339 | + | +10.6 | +7.4 | banked into the turn (-129 deg) |
| 576-648 | 72 | + | +2.2 | +2.1 | straight/gentle (+2 deg) |
| 705-774 | 69 | + | +2.1 | +2.1 | banked into the turn (-67 deg) |
| 780-819 | 39 | + | +2.1 | +2.0 | banked into the turn (-17 deg) |
| 972-1134 | 162 | + | +3.7 | +2.6 | OFF-CAMBER (+15 deg) |
| 1251-1305 | 54 | + | +2.2 | +2.1 | banked into the turn (-12 deg) |
| 1332-1392 | 60 | + | +2.1 | +2.1 | straight/gentle (+5 deg) |

## Compared with the repo's research

Config: only T2 banked, 10.5 % (6.0 deg), measured by lidar at +10.0..+11.2 % across +/-5 m, window s 215-525 with ~80 m ramps; elsewhere ~2 % crossfall falling to the infield (left edge up), not modelled. **The lidar agrees closely.** T2 run s 198-537 peaks +10.6 %, mean +7.4 %, banked into the right-hander (sign convention validated: positive = left/outside edge up in a right-hander, as the config's `_sign_doc` says), 10.3 % mean through the corner proper (s 303-450). The rest of the lap sits at +2.0..+2.2 % left-high, matching the config's 'about 2 % crossfall'. Only one run is off-camber: s 972-1134 (+2.6 % mean, peak +3.7 %) through the 80-degree left-hander at s 879-996, which the config does not mention.

## Caveats

- The default 8 % read limit would have dropped T2 as 'not a road'; it was raised to 12 % for this survey.
- A plane fit across the half-width reads hillside or run-off fall if the line is near it; the tool's own filter (residual sd and read limit) only catches non-planar sections.
- Lidar vintage and class: ground (class 2) points only, no deck points used (no declared bridge spans).

## Files

- `crossfall.json`: per-station `station_m`, `tilt_pct`, `bank_rad`, `raw_pct` (None = dropped) and summary.
- `crossfall.lidar.json`: the cached per-station plane fits, so the survey recomposes without the lidar libraries.
