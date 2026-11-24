# The Northfield Quebec arms on the lidar at their true lon / lat (2026-11-23, the G10)

`connector_profiles.lidar.round_2_quebec_arms.json` holds the two side-street arms of the sandcreek_quebec pad,
grid_primary_78 and grid_primary_84, read at each grid point's own lon / lat: lidar x = x * kx, z = z * kz (kx 1.0024949,
kz 0.9985216, `tools/grid_reach.frame_scale`). This is how `w3_connector_profiles.lidar.lonlat.json` read round I's
held streets.

The rules are `tools/lidar_connector_profile.py --surface`: the median of the class 2 + 17 returns within 1.0 m
[invented], with at least 3 returns [invented]. The file has the w3 lonlat file's shape. `lm_pieces` adds the LM's
grid_primary_84#0#0, which is not a source connector. It is **not wired**: no config points at it, and no plan position
moved.

**The tiles (USGS CO_DRCOG_2_2020, lidar_connector_profile's cache format).**
- 18_-4 and 18_-5 came from round 1's profile cache and were not fetched again. Every true point and the pieces' whole
  footprint lie in these two tiles.
- Read at the grid's x / z (round I's reading), these two tiles give `connector_profiles.lidar.round_i.json` exactly for
  both pieces: 0.000 m, with every returns count equal. So the tile grid and frame are round I's.
- 18_-3 was fetched new (13 EPT nodes, 3.08 MB) at the PC's request. No profile point reads it.
- No neighbour tile was added.

| piece | read / filled | on deck | minus round_i (min / max / median) | pad end, new vs round_i | max neighbour jump (round_i) |
|---|---|---|---|---|---|
| grid_primary_78 | 43 / 0 | 10 | +0.095 / +0.315 / +0.186 m | end 24.926 vs 24.765 | 0.184 m (0.214) |
| grid_primary_84 | 38 / 0 | 3 | +0.048 / +0.255 / +0.186 m | start 24.396 vs 24.348 | 0.203 m (0.215) |
| grid_primary_84#0#0 (LM) | 37 / 0 | 3 | +0.095 / +0.419 / +0.198 m (vs its built y) | start 24.738 vs 24.620 | 0.358 m (0.220) |

- **No neighbour jump is over round I's 0.5 m [invented] rule.**
  - 84#0#0's largest jump is at its last point, the weld point, which is not a source point. It reads 29.116 after 29.474.
- **Near the pad, the road over the port's 3DEP grid** (`grid_reach.heightfield_at`, at the street's own lon / lat):
  - grid_primary_78, points k36-k42: 2.64-3.00 m. At k41 the road reads 25.001 and the grid 22.360.
  - grid_primary_84, points k0-k8: 0.55-1.39 m. At k4 the road reads 24.876 and the grid 23.857.
- **The lidar ground beside the road does not show that height.** The class 2 returns 6-12 m [invented] either side of
  the true centre line, ±1.5 m [invented] along it, read:
  - grid_primary_78: -0.41 to +0.41 m against the road. The side toward grid_primary_84 (the median) is higher than the
    road; the far side is lower.
  - grid_primary_84: -0.22 to +0.13 m.
  - So the 2.6 m is the gap between the road and the 40 m grid, not an embankment in the lidar.
- **The pad's arm rows** (`data/pads.built.json`) sit at 24.865 and 24.720, each 0.100 m over the built arm end. The new
  ends read 24.926 (+0.061 over the row) and 24.738 (+0.018).
- **Not settled here:**
  - The plan stays in the grid frame, 4.6 m west of the true street. The ground at that drawn line (round I's reading) is
    0.05-0.32 m under the true road.
  - The 0.935 m deck-edge overhang is not located by this. Whether the build's grass there comes from the 40 m grid was
    not checked.
