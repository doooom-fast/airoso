# E 56th Ave onto the lidar: grid_reach re-run with the 14 tiles (2026-11-23, the Mac)

`source/grid_reach.json` was re-run by `tools/grid_reach.py` on the same project and config as round 1 (ledger 0098:
`tracks/sand-creek-lm`, `lm_intake.connector_profiles` = round I's file). The tiles were round 1's cache plus the 14 EPT
tiles of row z 1300-1400 that round 1's `tiles_missing` listed (USGS CO_DRCOG_2_2020, fetched by the G10, `tiles_e56.tar`
md5 c15fb616…). Nothing was fetched here.

- **The 14 tiles** are in lidar_connector_profile's cache format: E / N / Z / C, the tile + 5 m, every EPT node read.
  Their (i, j) are the 14 in `tiles_missing`. Their 5 m margins hold the same returns, point for point, as the
  neighbouring tiles of round 1's cache (1,455-4,037 per margin), so they are in the same frame.
- **The setup is round 1's.** Round 1's cache alone gives round 1's record byte for byte (md5 c7b10bc6…).
- **The new record:** md5 7b4c4ef1…, 42,407 B. `tiles_missing` is now [].

| grid_primary_80 (start), E 56th Ave | round 1 | now |
|---|---|---|
| heights | 377 lidar, 466 3DEP + offset | 843 lidar |
| lidar_share | 0.447 | 1.0 |
| largest neighbour step | 0.168 m | 0.174 m (s 264-267, x -385: a steady 4-6 % climb) |
| steepest | 5.6 % | 5.8 % |
| tiles_missing | 14 | 0 |

- **The 466 points now on the lidar** lie in six stretches: x -598..-202, -97..-1, 101..398, 998..1097, 1199..1595 and
  1697..1793. Their heights moved |dy| p50 0.217 m, p90 0.720 m, max 1.032 m (x -300.8, z 1319.2, +1.032); signed
  median -0.061 m; 211 points moved more than 0.25 m, 104 more than 0.5 m. These numbers are the error of round 1's fill
  (3DEP moved by the lidar - 3DEP offset interpolated between measured neighbours).
- **The 377 points round 1 read off the lidar** are unchanged (0.000 m). Over all 843 points: p50 0.017 m, p90 0.560 m.
- **Lidar - 3DEP along the whole street** (past the 30 m ease): -0.36 .. +1.35 m, median +0.18 m.
- **The joint is unchanged.** from_y is 5.669 and the first point is 5.670 (0.001 m over 3 m). The first 15 points read
  the lidar in both runs. The largest step within ease_m is 0.053 m in both. The far end (x 1877.5) is 18.446 m in both.
- **No plan position moved.** Every point's x / z, from_xz and widths are identical. The grid_primary_71 and
  grid_primary_73 records are identical to round 1's.
- **On round 2's config** (`connector_profiles.lidar.round_2.json`, which puts grid_primary_71 on the lidar), 71's end
  height is 27.140, not the record's from_y of 27.051. `apply_grid_reach` re-eases its 7 points by +0.089 m. That gives
  the same heights a re-run on round 2's config writes (0.000 m apart). E 56th and 73 come out the same on either config.
