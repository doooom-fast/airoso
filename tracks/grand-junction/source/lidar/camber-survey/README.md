# Grand Junction Motor Speedway: lidar cross-slope survey

Research only. Nothing here is applied to any build; the files live under `source/` so no build picks them up.
Measured on the G10 (Linux) with `tools/lidar_crossfall.py` from branch `claude/sand-creek-0.33.0` (algorithm identical to the `claude/sand-creek-camber` copy batches 1-2 used; the only differences are the TLS context and the mesh-frame handling of `finished_centerline.json`, neither of which changes the numbers here), 2026-11-03.

- **EPT project:** `USGS_LPC_CO_MesaCo_QL2_2015_LAS_2017` (USGS 3DEP, `https://s3-us-west-2.amazonaws.com/usgs-lidar-public/USGS_LPC_CO_MesaCo_QL2_2015_LAS_2017/ept.json`), 34 EPT nodes along the corridor. The other Mesa County projects (`QL1_2016`, `QL2_UTM13_2015`) and `CO_WestCentral_2019` do not contain the site.
- **Line:** `data/finished_centerline.json` from branch `claude/grand-junction-chain` (frame `kn5`, mirror_x false), lap 1304.4 m, 3 m stations, + = left side higher.
- **Half-width used:** 3.9 m (config `default_width_m` 9.75 m, half 4.875 m minus 1 m). The tool hard-codes 4.5 m.
- **Other thresholds overridden, as batch 1:** MAX_READ_PCT 8 -> 12 %, MAX_SD_M 0.08 -> 0.10 m, CAP_PCT 6 -> 12 %. The 0.2 %/m roll-rate limit and 9 m smoothing are the tool's own. Values are recorded in `crossfall.json` `params`.
- **Wall time on the G10:** 18 s (fetch + fit, nice 19, 4 GB cap), peak RSS 105 MB.

## Numbers (`crossfall.json` `tilt_pct`: filled, smoothed, rate-limited)

- Stations: 435; dropped (not a road fit, filled): 0
- Fit quality: ground (class 2) points, median 95 points per station, residual sd median 2.2 cm (p95 4.6 cm, max 6.0 cm).
- |tilt| p50 1.74 %, p95 2.99 %, max 3.53 %
- Banked (|tilt| >= 2 %): 33.6 % of stations
- Worst roll change per 30 m: 4.07 % (tool). The 11 corners include hairpins of up to 155 degrees per 30 m, where the fit's lateral axis swings quickly, so treat the roll rate as indicative.
- In corners of >= 15 degrees per 30 m that read >= 2 %: 90 stations banked into the turn, 17 off-camber

## Sustained banking (|tilt| >= 2 %, longer than 30 m, one sign)

Sign: + = left side higher. Banked into the turn = the inside edge is lower. Stations are along the finished line; the angle is the net heading change over the run (+ = left).

| s start-end (m) | length (m) | sign | peak % | mean % | relative to the turn |
|---|---|---|---|---|---|
| 165-204 | 42 | - | -3.5 | -2.8 | OFF-CAMBER (-14 deg) |
| 258-312 | 57 | - | -3.5 | -2.7 | banked into the turn (+165 deg) |
| 594-648 | 57 | + | +3.3 | +2.8 | banked into the turn (-130 deg) |
| 843-894 | 54 | - | -3.0 | -2.6 | banked into the turn (+118 deg) |
| 1041-1077 | 39 | + | +3.0 | +2.5 | banked into the turn (-97 deg) |
| 1197-1251 | 57 | + | +3.1 | +2.5 | banked into the turn (-126 deg) |

## Corners (turn >= 15 degrees per 30 m; tilt shown as into-the-turn, positive = inside edge lower, negative = off-camber)

| s (m) | dir | peak turn deg/30 m | into-turn mean % | min % | max % |
|---|---|---|---|---|---|
| 120-171 | R | 107 | +0.6 | -2.2 | +2.3 |
| 192-243 | R | 95 | -1.5 | -3.5 | -0.4 |
| 255-309 | L | 155 | +2.7 | +2.0 | +3.5 |
| 327-360 | R | 23 | -1.8 | -2.4 | -1.3 |
| 387-417 | R | 25 | -1.2 | -1.5 | -0.9 |
| 441-504 | R | 27 | -1.8 | -2.2 | -1.3 |
| 573-660 | R | 126 | +2.2 | +0.0 | +3.3 |
| 666-696 | L | 85 | -1.6 | -2.0 | -1.2 |
| 699-723 | R | 81 | +1.6 | +0.4 | +2.2 |
| 726-783 | L | 66 | -0.0 | -0.7 | +0.8 |
| 825-891 | L | 99 | +2.1 | -0.4 | +3.0 |
| 1011-1071 | R | 147 | +1.6 | -0.8 | +3.0 |
| 1137-1182 | L | 90 | +1.1 | -0.5 | +1.9 |
| 1185-1254 | R | 79 | +2.4 | +1.0 | +3.1 |

Right-turn stations average +0.50 % (left side higher), left-turn stations -1.15 %: the circuit leans in or out by a gentle 1-3 % rather than banking consistently.

## Compared with the repo's research

Config: "NO banking (road course)"; an earlier web claim of a banked 1.25-mile oval was rejected as a conflation. **Mostly agrees: no banking, but not flat.** The lidar finds no bank anywhere near a banked circuit (max 3.5 % = 2 degrees, p50 1.7 %), which confirms the rejection of the oval claim. It does show a gentle, irregular cross-slope that a flat deck lacks: 34 % of the lap at 2 % or more, in the range of normal road superelevation or drainage fall. Five of six sustained runs are banked into the turn (the left-hand 255-309 hairpin and four right-hand corners), so the track is not generally off-camber. The off-camber places are the 192-243 right-hander (-1.5 % mean, down to -3.5 %), the three long right-hand bends at 327-504 (-1.2 to -1.8 %), and the left-hander at 666-696 (-1.6 %). Repo law L10 does not require adding any of it; if the camber were ever applied, the corners above are where it changes the seat feel.

## Confidence

**Moderate.** All 435 stations are road planes (median residual 2.2 cm, none dropped), from 2015 QL2 ground points. Magnitudes are small (a few cm across the road), so the 2-3 cm residual is a meaningful fraction of the signal, and the hairpin stations (turns of 100+ degrees per 30 m, radius about 12-15 m on a 9.75 m road) fit a plane across a sharply curved surface. Treat the sign pattern as reliable and the individual tilt values as plus or minus about 1 %.

## Caveats

- A 3.9 m half-width covers only the central 7.8 m of the 9.75 m ribbon.
- Lidar vintage 2015; the site's current surface or resurfacing is not reflected.
- A plane fit reads hillside or run-off fall if the line is near it; the filter only catches non-planar sections.
- Class 2 only; no deck points (no declared bridge spans).

## Files

- `crossfall.json`: per-station `station_m`, `tilt_pct`, `bank_rad`, `raw_pct` (None = dropped) and summary.
- `crossfall.lidar.json`: the cached per-station plane fits, so the survey recomposes without the lidar libraries.
