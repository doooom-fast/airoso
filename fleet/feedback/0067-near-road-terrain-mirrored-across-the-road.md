---
id: 0067
title: Near-road terrain was mirrored across the road
status: fixed-awaiting-rebuild
scope: tracks/sand-creek, tracks/milford, tracks/high-plains, tracks/nevada-nights
layer: engine
train: -
---

## Symptom

Found by another session while looking at Lake Murray v5: one grid node 50 m up the hill read the downhill height (53.0 m against 81.4 m true), which made a 30 m fold in the ground. Within 60 m of the road, every terrain node took its height from the same distance on the OTHER side of the road.

## Mechanism

`scripts/elevation/heightfield.py` `fetch_corridor` writes `data/corridor.elev.json` with one row per station, offsets -60..+60 m along the LEFT normal (`nx, nz = -tz / L, tx / L`, tangent in east/north), so + is left of travel.

`scripts/geometry/build_mesh.py`, the corridor splice (about lines 883-939), computed the lateral as `-(-tz*dx + tx*dz) * sxc`. For `mirror_x: false` (`sxc = 1`) that is minus the left-positive lateral, so the row was read at the mirrored offset.

`mirror_x: true` was wrong too. In the local frame x is negated, which negates both the tangent's x and the node's dx, so `-tz*dx + tx*dz` is already minus the real left-positive value. The correct lateral is that expression times `sxc`; the old code had the extra minus in both cases. Only tracks with `mirror_x: false` were measured.

## Measured impact (mirror_x false), left-against-right ground under the old read

| Track | Median | Max |
|---|---|---|
| Sand Creek | 2.4 m | 15 m |
| Milford | 1.6 m | 17 m |
| High Plains | 0.3 m | 10 m |
| Nevada Nights | 0.6 m | 3 m |

## Fix and test

`corridor_lateral(tx, tz, dx, dz, mirror_x)` and `corridor_row_height(row, lat, half_l, step_l)` are now small pure functions in `build_mesh.py`, used by the splice. The lateral is left-positive for both values of `mirror_x`.

`tests/geometry/test_corridor_splice_side.py` builds a synthetic corridor with the left side high and the right side low, and checks a node left of travel gets the left height and a node right gets the right height, for `mirror_x` false and true.

## Not affected

Lake Murray 0.19.x and v4 are built by the authored assembler, not by this splice, so they are unaffected.

## Owed

Rebuilding Sand Creek, Milford, High Plains and Nevada Nights waits on Kevin's word. No track data was touched. Status moves on after a rebuild and a drive.

## Rebuilt 2026-11-03 (Kevin: "Yes, rebuild all four"), three installed, not driven

Each rebuilt from its draft mesh on the corrected splice through `tools/ship_track.sh <track> --from mesh` on the Windows box, installed
only with every gate green and no force, and with severe steps, kinks/km, steps/km and fold bumps no worse than the build it replaced.
Each replaced build is parked whole in `D:/k10-track-archive/<stamp>/`.

| Track | Installed | kn5 md5 | severe | kinks /km | steps /km | fold bumps | excursion drops | far ledges | parked |
|---|---|---|---|---|---|---|---|---|---|
| Nevada Nights | 0.7.0 -> **0.8.0** | deb60e23c06926ea1b25d2f4653e0fb5 | 0 -> 0 | 0.0 -> 0.0 | 0.0 -> 0.0 | 3 -> 3 | 0 -> 0 | 8 -> 0 | 2026-11-03_120339 |
| High Plains | 0.71.0 -> **0.72.0** | c798d5dfd44dcb9386e1a7e4cbb4b400 | 0 -> 0 | 7.77 -> 7.77 | 1.24 -> 1.24 | 0 -> 0 | 0 -> 1 | 13 -> 16 | 2026-11-03_123313 |
| Milford | 0.4.0 -> **0.5.0** | 8da5df6a3ab609776f1f141003d71290 | 26 -> 26 | 30.99 -> 30.99 | 2.45 -> 2.45 | 0 -> 0 | 1 -> 0 | 33 -> 29 | 2026-11-03_124243 |

- **Milford**: `kn5_ground_check` double-sheet terrain cells 7 -> 0 (the mirror's folds); road-over-ground 1/1401 on both, its one sample 0.229 -> 0.38 m.
- **High Plains**: the corrected ground beside the paddock corner (E -505 N 131) is a real drop, and the measured-guard set a stone lip there.
  The planned shelter `post5` and the OSM shed `osm289314487` both stood 1.2-2.0 m from it and the bespoke step refused them; `post5` was
  the same building drawn twice (its ring inside the shed's footprint, both standing one inside the other in 0.71.0), so it left the
  plan and the posts plan loses 4 of 12 (post0-post3, on the pavement since the plan was written). 13 buildings stand where 15 did.
- **Sand Creek** is on its own branch: its first rebuild (0.31.2) went red on `audit_mesh` B, the seam weld lifting the grass through a
  grid street's deck where the street joins the lap in a cut; the fix is `seam_weld_tables` (the connectors' decks in the floor's cap).
