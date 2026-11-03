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
