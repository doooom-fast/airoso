# Colorado Blvd's real light poles, off the 2020 lidar

This section belongs to this folder's README. The README itself (`README.md`, with the Colorado / Quebec road
measurements) is on branch `claude/sc-roads-lidar-20261124`. This file is kept separate so the two branches merge
cleanly.

**Purpose.** Round 0.2.13 should place lamps only where a pole really stands. NAIP 2023 (0.46 m/px) shows a pole only
as its shadow. Measured on the G10 on 2026-11-24. The files are data only.

| file | what |
|---|---|
| `colorado_poles.lidar.json` | every pole-like object, the window's evidence, the six built lamps' verdicts |
| `colorado_poles_g10.py` | the script (`fetch`, `measure`); its docstring gives the method and every [invented] constant |

## The read

- **Source and classes.** USGS CO_DRCOG_2_2020, read at every class from the EPT nodes themselves (not the 2/17 tile
  cache). The corridor held classes 1 (100,059 returns), 2 (152,379), 7 (355) and 18 (144). This survey has no
  separate vegetation, building or wire classes: all of them are in class 1.
- **Nodes.** 26 EPT nodes meet the corridor, which runs within 50 m of the lap's line over s -10..425. 22 nodes came
  from local copies of earlier fetches. This job fetched 4 nodes, 1,827,355 bytes: 10-444-564-507, 10-444-565-507,
  10-444-566-507 and 10-444-567-507.
- **The window.** It is the one asked for: s 0-415 along the lap (centerline.local.json from v0) and u -30..+30
  (+u = left of the lap's travel, west). The window holds 5.69 returns per m².

## In the window, s 0-415 and u -30..+30: no pole

These are the non-ground returns at heights over the ground:

| at least | 3 m | 4 m | 5 m | 6 m | 7 m | 8 m | 10 m |
|---|---|---|---|---|---|---|---|
| returns | 852 | 422 | 52 | 5 | 0 | 0 | 0 |

- Every return 4.5 m or more over the ground belongs to one of three tree crowns. Each is wide, with 173-225 returns
  and multiple returns per pulse:
  - s 60-66, u +24..+30, top 5.8 m;
  - s 75-84, u +21..+30, top 5.3 m;
  - s 303-312, u -18..-12, top 6.4 m.
- A light's head and arm at 6-11 m gives 12-83 returns where one stands: see the six objects just west of the window,
  below. So the empty count above is a measurement, not a gap in the data.
- There are no overhead lines. The 50 m corridor holds no wire object (long and thin in plan at 4 m or more).
- At the railway crossing near s 276, nothing stands 7 m or more over the ground inside the window, so there is no
  line pole there either. The nearest tall thing is Q05 below. It is 6.2 m tall, 2.8 m long across the road, with no
  shaft and no wire. By the rule (under 13 m, no wire) it is not a line pole.

## Just west of the window, u +36..+44: six elevated objects, no shaft (low confidence)

Each object below has these properties in common:
- It is narrow: 0.30-0.35 m wide in plan, as a standard deviation.
- It runs 2.2-5.5 m across the road.
- It stands 6-10 m up.
- Almost nothing is under it: 0-20 returns, spanning under the 2 m that would count as a shaft.

That pattern fits a light's head and arm, but also a sign's or a billboard's top. Which end stands on a pole is not
measured, so no arm direction is claimed. The base given below is the object's end farther from the road, which is an
assumption.

| id | s | u | base x, z | lon, lat | ground y | top y | top over ground | length across | returns (under the top band) |
|---|---|---|---|---|---|---|---|---|---|
| Q01 | 52.4 | +40.77 | -1551.00, -205.11 | -104.9408997, 39.7846015 | 19.48 | 29.63 | 10.21 | 2.15 | 12 (0) |
| Q02 | 149.5 | +41.51 | -1550.82, -108.55 | -104.9408976, 39.7854712 | 17.54 | 23.74 | 6.10 | 3.80 | 24 (10, an awning roof at 3.7-3.9 m beside it) |
| Q03 | 230.2 | +44.19 | -1553.12, -27.17 | -104.9409244, 39.7862041 | 16.79 | 26.54 | 10.00 | 4.59 | 29 (0) |
| Q04 | 245.3 | +43.55 | -1552.26, -12.33 | -104.9409144, 39.7863379 | 16.75 | 23.72 | 7.01 | 5.48 | 83 (20, spanning 1.4 m) |
| Q05 | 274.6 | +40.17 | -1548.75, 16.45 | -104.9408734, 39.7865971 | 16.78 | 23.05 | 6.24 | 2.76 | 25 (0) |
| Q06 | 319.2 | +35.95 | -1544.72, 61.10 | -104.9408263, 39.7869992 | 17.33 | 23.82 | 6.49 | 2.31 | 16 (1) |

The roads file on the other branch puts Colorado's west outer curb at u +20.1, so these objects stand 16-24 m past it.
In a first pass that kept points within 36 m, two more pole-like objects appeared at s 85 and s 358 (u +35). At 50 m
they join tree crowns 13.7 m and 9.9 m tall, which have multiple returns per pulse, so they are read as trees.

## The six lamps 0.2.11 built here (data/lights.local.json lamp_bases_xz 0-5)

| lamp | base x, z | s | u | nearest | distance | verdict |
|---|---|---|---|---|---|---|
| 0 | -1521.213, -200.414 | 57.5 | +11.05 | Q01 | 30.15 m | no pole within 15 m |
| 1 | -1498.468, -146.741 | 111.4 | -11.05 | Q02 | 64.80 m | no pole within 15 m |
| 2 | -1520.359, -92.731 | 165.4 | +11.05 | Q02 | 34.32 m | no pole within 15 m |
| 3 | -1498.002, -35.964 | 222.3 | -11.05 | Q03 | 55.82 m | no pole within 15 m |
| 4 | -1519.635, 18.084 | 276.2 | +11.05 | Q05 | 29.16 m | no pole within 15 m |
| 5 | -1497.722, 72.025 | 330.1 | -11.05 | Q06 | 48.25 m | no pole within 15 m |

Nothing pole-like stands on the east side (u < 0) out to 48 m.

## Not settled

- This is the 2020 survey. Poles put up since then are not in it.
- A pole's shaft is thin, and this survey caught none here. Q01-Q06 are read from their tops only.
- Q01-Q06 lie outside the window asked for. Whether they are lights (and for which road) or signs is not settled by
  the lidar.
- Heights over the ground come from a 1 m class-2 grid, with holes filled from the nearest read cell.

## Rerun

```
python -I colorado_poles_g10.py fetch   --repo <airoso checkout> --dl <new dir> --mirror <EPT copy dir> [--plan plan.json]
python -I colorado_poles_g10.py measure --repo <airoso checkout> --dl <same dir> --mirror <EPT copy dir> --out colorado_poles.lidar.json
```
