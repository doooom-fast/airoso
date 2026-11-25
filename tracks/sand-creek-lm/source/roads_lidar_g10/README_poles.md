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

## Second source: the DRAPP 2022 orthophoto (3 inch), read by eye

**Why a second source.** The 2020 lidar shows no pole in the window, but airborne lidar can miss thin shafts, and it
cannot show poles put up after 2020. This section reads a 2022 orthophoto of the same stretch.

| file | what |
|---|---|
| `colorado_ortho_g10.py` | `fetch` reads the crop, `chips` / `crop` draw views to read, `poles` turns the readings into the JSON |
| `colorado_ortho_picks.json` | the readings: each pole's base, shadow tip, arm and head, in crop pixels, with what agreed |
| `colorado_poles.ortho.json` | the result: poles, lamp verdicts, Q01-Q06, the shadow bearing |

### The photo

- **What it is.** The Denver Regional Aerial Photography Project's 2022 orthophoto (DRCOG). It has 4 bands (R, G, B,
  near infrared), 0.25 ft (7.62 cm) pixels, and is in NAD83(2011) / Colorado Central ftUS (EPSG:6428, read from each
  GeoTIFF).
- **Why this year.** It is the newest free year. DRCOG sells the current DRAPP (2024) and gives older years away.
- **Where it is.** It sits on the State of Colorado's public bucket, read anonymously:
  - `https://colorado-public-imagery.s3.us-west-2.amazonaws.com/DRAPP/DRAPP2022/N1E162d.tif`, S3 ETag (the whole
    tile's md5) `683065829fe062f90c462ce84c10a354`;
  - `https://colorado-public-imagery.s3.us-west-2.amazonaws.com/DRAPP/DRAPP2022/N1E163c.tif`, ETag
    `39ce5ed1406dc597b14312a63f3fef84`.
- **Licence.** The bucket's AWS Open Data listing gives CC0. DRCOG's own metadata (Jefferson County's DRAPP2022
  service) gives CC BY 3.0. Either way, the crop is not in git, as asked.
- **Date.** 2022. The flight date is not in the tiles: their TIFF DateTime, 2023-01-03, is the processing date, and the
  files were posted 2025-09-10. The sun stood in the south-east, so it was a morning flight: every shadow runs
  north-west, median bearing 312.4°.
- **The crop.** It covers the lap's s -20..435 and u -50..+50. It is every 2nd row of the tiles, so pixels are 7.62 cm
  across and 15.24 cm along.
  - File: `crop.npz`, 3242 x 1347 x 4, md5 `6e92fc8e333560afd1b5e526f1a30ad2`. The viewing PNG is md5
    `0bb30eda3720a5f3221da9b5a16e49da`.
  - Read: 17,649,560 bytes in 6,522 HTTP range requests. That is more than "a few MB": the tiles are uncompressed, so
    a crop costs every pixel it holds. Skipping every other row halved it while keeping 15.24 cm.

### How it was read

- **The rule.** A pole counts as READ only when a head or arm and its shadow line agree on its base.
- **The shadow.** The base is where the pole's shadow starts. That is also where the pole's own image starts: a short
  dark stroke leaning east, which is the photo's relief displacement.
- **The arm.** It is read either off its shadow, which branches from the pole shadow at the arm's height (the arm moved
  along the sun's ray), or off the arm and head themselves, seen over the road from the base.
- **Precision.** Every pick was read at 2-3x zoom, to about ±2 pixels (±0.15 m across, ±0.3 m along).
- **Frames.** NAD83(2011) is taken as WGS 84, PROJ's own null step, as the lap's frame does. The read poles stand
  symmetrically 0.3-1.8 m behind both curbs, so no lateral offset shows between the photo and the lidar curbs.

### The poles

The table gives each pole's s and u in the lap's Colorado frame (+u = west). The curbs are the measured ones: near
carriageway's curb u -5.25, median +5.75..+10, far curb about +21. An arm's length is read off its shadow.

| id | status | s | u | where | arm | shadow m | lon, lat |
|---|---|---|---|---|---|---|---|
| a | read | 7.7 | +21.53 | west, 0.53 m behind the far curb | 2.8 m, toward the road | 8.42 | -104.9406815, 39.7841966 |
| b | read | 37.3 | -7.09 | east, 1.84 m behind the near curb | 4.5 m, toward the road | 10.14 | -104.9403432, 39.7844599 |
| c | not read | 37.4 | +21.79 | west, 0.79 m behind the far curb | none seen | 9.81 | -104.9406803, 39.7844643 |
| z1 | not read | 53.8 | -15.14 | east, 9.89 m behind the near curb | none seen | 12.79 | -104.9402468, 39.7846077 |
| w2 | read | 69.3 | +21.61 | west, 0.61 m behind the far curb | seen itself, toward the road | 7.71 | -104.9406735, 39.7847511 |
| g | read | 105.4 | -5.22 | east, at the near curb | 5.5 m, toward the road | 7.22 | -104.9403552, 39.7850735 |
| f | read | 134.5 | +21.64 | west, 0.64 m behind the far curb | 2.9 m, toward the road | 7.77 | -104.9406662, 39.7853372 |
| i | read | 166.3 | -5.03 | east, at the near curb | 4.4 m, toward the road | 7.56 | -104.9403543, 39.7856226 |
| h | read | 195.5 | +21.32 | west, 0.32 m behind the far curb | 3.1 m, toward the road | 9.03 | -104.9406618, 39.7858862 |
| k | read | 226.5 | -6.75 | east, 1.50 m behind the near curb | 4.1 m, toward the road | 8.16 | -104.9403305, 39.7861633 |
| j | read | 256.7 | +21.63 | west, 0.63 m behind the far curb | 2.8 m, toward the road | 8.49 | -104.9406574, 39.7864380 |
| m | not read | 284.6 | +8.50 | median | none seen | 9.49 | -104.9405042, 39.7866871 |
| n | read | 341.8 | +7.26 | median, 1.51 m from its east face | twin: 3.5 m west, 3.1 m east | 9.62 | -104.9404912, 39.7872031 |
| p | read | 395.4 | +19.92 | west, at the far curb (corner island) | 2.8 m, toward the road | 11.42 | -104.9406323, 39.7876938 |
| o | read | 396.8 | -6.56 | east, 1.31 m behind the near curb (E 50th corner) | 3.6 m, toward the road | 8.55 | -104.9403227, 39.7876951 |

- **The pattern.** The read lights are cobra heads. They stand about every 60 m on each side, just behind the curb:
  - the west side at u +21.3..+21.6;
  - the east side at u -5.0..-7.1;
  - one twin-arm light in the median.
- **North of E 50th.** Two more lights, `nw` and `ne`, stand past the lap's turn. Their s and u are read against the
  lap's E 50th leg, so they are in the JSON only.
- **Not read.** Three poles have no head or arm seen:
  - c, on the west side at s 37, opposite b;
  - z1, 10 m behind the east curb, with a longer shadow;
  - m, in the median 20 m north of the railway crossing.
- **No overhead line.** No wire crosses or follows Colorado in the crop.

### The six lamps 0.2.11 built here, against the read poles

| lamp | s | u | nearest read pole | distance | verdict |
|---|---|---|---|---|---|
| 0 | 57.5 | +11.05 | w2 (s 69.3, u +21.61) | 15.82 m | no read pole within 15 m |
| 1 | 111.4 | -11.05 | g (s 105.4, u -5.22) | 8.39 m | g at 8.4 m |
| 2 | 165.4 | +11.05 | i (s 166.3, u -5.03) | 16.10 m | no read pole within 15 m |
| 3 | 222.3 | -11.05 | k (s 226.5, u -6.75) | 6.00 m | k at 6.0 m |
| 4 | 276.2 | +11.05 | j (s 256.7, u +21.63) | 22.02 m | no read pole within 15 m |
| 5 | 330.1 | -11.05 | n (s 341.8, u +7.26) | 21.72 m | no read pole within 15 m |

The west lamps (u +11.05) stand in the real far carriageway: every real west pole is about 10 m further west, at
+21.5. The east lamps stand 5.8 m behind the near curb, where the real east poles stand 0-1.8 m behind it.

### Q01-Q06 (the lidar's elevated objects west of the window)

None of them is a light:

| id | what the photo shows |
|---|---|
| Q01 | a pole sign: one pole, its 4 m panel at the top |
| Q02 | no pole: the lot's west building (roof edge, awning) |
| Q03 | a billboard on two posts |
| Q04 | a large sign or billboard panel |
| Q05 | a pole sign beside the railway |
| Q06 | a pole sign at the lot's corner |

The lidar's 13.7 m "tree" at s 85, u +43 is a large billboard.

### The 2023 NAIP shadow at lamp 2 (s 166)

It is cast by streetlight i: a cobra head at the near (east) curb, s 166.3, u -5.03.
- Its pole shadow crosses the lap's carriageway north-west.
- Its 4.4 m arm's shadow ends at u +4.0, 1.7 m short of the median's east face.
- Built lamp 2 stands across the median from it (u +11.05), 16.1 m away.

### Not settled

- This is the 2022 photo. Changes since then are not in it.
- A pole is read only by eye. The readings are in `colorado_ortho_picks.json`, so they can be re-checked.
- c, z1 and m may be lights whose arm does not show. They are not counted.
- The railway crossing near s 266-273 holds its gates and median signal, not light poles.
