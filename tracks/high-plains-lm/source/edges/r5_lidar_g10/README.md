# High Plains round 5: what NAIP left owed, read off the 2018 lidar

Ledger 0097, "Still to do (round 5)": the fillet behind the T13 kerb, the north loop's two blue / yellow stripes, and
the 42 m of carried edges. Kevin: "I just want real". Every number here is read off the lidar's returns unless it says
DERIVED or [invented]. Data only: no config, kerbs file or north_loop.json row is changed; the builder takes these numbers.

## Files

| file | what |
|---|---|
| `merge_east_fillet.json` | item 1: the merge's east corner (round 4's `full_north#0#0\|end\|+1`): the asphalt's edge round the corner, point by point, its radius, the kerb's white blocks behind it |
| `north_stripes.json` | item 2: the stripes L own s 372-401 and 648-682 (round 4's eye spans): their along-track ends, their inner side, the station-by-station reads |
| `carried_edges.json` | item 3: L row s 254-260, the fork's R row s 0-19, the merge's R row s 988-1001 and L row s 996-1001; the lidar-vs-NAIP registration; the merge's west corner |
| `hp_r5_lidar.py` | the job: `plan` / `fetch` (network), `extract`, `measure` (offline) |
| `measure.log` | the measure run's own output |

## Source and how it ran

USGS 3DEP **CO_Eastern_B3_2018** (public domain), the same EPT round 3's roofs read (EPSG:3857 XY, NAVD88 Z). Five spots
(boxes 22 m round the pieces of line they hold, `SPOTS` in the script) need 23 octree nodes (599,524 points); 18 were
already on disk from round 3's paddock download, **5 nodes were fetched: 642,413 B** (10-518-820-505, 10-519-816-505,
10-519-820-505, 8-129-205-126, 9-259-410-252). Kept: 99,918 returns (noise classes 7 / 18 dropped), **1.9-2.2 per m2,
one flight line (1141)** over every spot, so intensity is one calibration throughout.

Run on the lidar box (laspy + lazrs, pyproj, numpy, scipy; `python -I`, nice 19 / ionice 3, under 60 MB):

    python -I hp_r5_lidar.py plan    <repo> <DL> --reuse <round 3's DL>   # ept.json, hierarchy, HEADs
    python -I hp_r5_lidar.py fetch   <DL>
    python -I hp_r5_lidar.py extract <repo> <DL> points.npz --reuse <round 3's DL>
    python -I hp_r5_lidar.py measure <repo> points.npz <out>

`<repo>` is main at 2657f4a8 (the frame files, tools/mouth_radii.py and tools/verify_mouths.py for the built corner frame).

**The frame**: 3857 -> lon / lat (pyproj) -> the track frame through `scripts.geometry.projection._meters_per_degree`
about `data/centerline.local.json`'s origin (x E, z N), round 4's own mapping. Lines: the West lap as built
(`data/centerline.local.json` + widths); the north loop's own line (`source/full/connectors.full.json` + widths: **own s**,
the s of round 4's kerbs and stripes); OSM's line as `measure_north.py` builds it (**row s**, `north_loop.json`'s rows,
whose `left_m` / `right_m` are metres off it).

**The reader**: asphalt returns read ~700-1,300, grass and paint 3,000-9,000. Each read is one dark -> bright step: on a
station (returns within 1.5 m along), a polar ray (within 0.75 m across) or a row's normal, the edge is the middle of the
innermost best plateau of (the dark share over 1.2 m inside + the bright share over 1.2 m outside). The threshold is
sqrt(asphalt x what borders it), both medians of the spot's own returns. Every read is repeated at 0.8x and 1.25x its
threshold; `t_sens_m` is the spread, and a read is `kept` at score >= 1.6 of 2 and t_sens <= 0.5 m.

**Registration** (`carried_edges.json` registration): on 168 north-loop rows where both NAIP and the lidar read the edge
(kerbs and the stripes left out), lidar - NAIP (outward) fits **c = -0.49 m + a shift of (-0.24 E, -0.04 N) m**;
residuals p10 / p50 / p90 -0.21 / 0.00 / +0.21 m, 94 % within 0.3 m. c is what each reader calls the edge: the lidar's
first bright return is the INNER side of the first paint (the white edge line), NAIP's edge is the line's outer side plus
the photo's measured line-to-edge offset (round 4: 0.3 / 0.4 m). The shift is the 2018 lidar against the 2023 photo.
`*_naip_def_m` values take off both (what NAIP's reader would have read); `*_photo_frame` values the shift only (where no
edge line is involved: paint and kerb edges).

## 1. The fillet behind the T13 kerb (the merge's east corner)

- **The asphalt's edge round the corner: radius 23.0 m** (the circle tangent to both legs' lidar edges that best fits the
  outline's middle 70 %, tools/mouth_radii.py's model, R tried every 0.25 m from 5 to 60 m: median deviation 0.13 m over
  51 points, not at the grid's end; arc 29.1 m). Taking the legs over four other distances from K moves it **21.25-23.0 m**
  (deviations 0.08-0.13 m); a free circle through the arc reads 20.0-21.4 m. The corner eases in and out: a circle
  through every 10 m of the outline reads 14-19 m at its middle (tightest 13.8 m), 24-50 m toward the legs. Round 4's
  NAIP reader stopped at its 20 m grid's end: the lidar agrees the radius is past 20 m.
- **The outline** (`outline`, 113 rays every 1 deg, E / N and lon / lat each): from Ladder's straight left edge round to
  the West lap's. On the 2023 photo (by eye, 0.3 m crop) it lies along the inner side of the blue / white T13 kerb round
  the whole corner; the kerb sits behind it, grass behind the kerb.
- **The kerb behind it**: the brightest returns (over the grass's own p99, 6,906) lie **0-1.75 m behind the asphalt's
  edge, p50 0.88 / p90 1.38 m**, none past 2.0 m but one. The paved outline (asphalt + kerb: round 2's rule, the kerb is
  the paved surface's edge) is DERIVED: the asphalt outline 1.38 m further out, a concentric **21.6 m**. NAIP's kerb
  paint (kerbs.lm.json T13 runs) is 1.88-2.10 m wide, so 1.4-2.1 m is the honest range for the kerb's outer side.
- Read in tools/mouth_radii.py's own BUILT frame (phi 120.1 deg, K of the install build) the same returns give 9.25 m at
  a poor 0.29 m median deviation: that frame's street line is the built Ladder edge near the cut, which the real edge
  leaves as it sweeps round, so no circle tangent to it fits. Kept for the record, not the answer.

## 2. The two blue / yellow stripes (north loop, left side)

Along each stripe the first bright return stands 0.80-0.81 m further in than the white edge line either side: the
stripe's inner side. o and in_m are metres past the north loop's built lane edge (kerbs.lm.json's convention).

| | round 4 eye (2023) | lidar core | lidar with tapered ends | in_m (raw / photo frame) | edge line either side |
|---|---|---|---|---|---|
| L 372-401 | 372-401 | **372.0-396.5** | 368.5-398.5 | **-1.21 / -1.37** (p10-p90 -1.39..-0.98) | -0.40 |
| L 648-682 | 648-682 | **653.0-674.0** | 651.0-676.0 | **-1.78 / -1.60** (p10-p90 -1.83..-1.58) | -0.98 |

Ends +-1 m (the stations' window). **out_m is not measured**: the paint (intensity p50 4,320 / 3,488) and what lies past
it (4,464 / 3,488) read alike, so the lidar cannot place the stripe's outer side. DERIVED, if the paint runs to the
asphalt's end as the 2023 photo shows: 1.30 / 1.29 m wide, out_m +0.09 / -0.49 (photo frame -0.07 / -0.31). The 2023
photo's paint runs a few metres past the lidar's ends at both stripes (by eye on straightened z18 strips: ~371.5-401 and
~647.5-681.5): the paint may have changed between 2018 and 2023; the lidar's 648 stripe ramps in over 649-655 and out
over 674-681 (`stations`).

## 3. The 42 m of carried edges

- **L row s 254-260**: the asphalt's edge reads cleanly on every row: off OSM's line **5.37 / 5.40 / 5.36 / 5.27 m**
  (NAIP's definition; raw lidar 5.11 / 5.14 / 5.10 / 5.01; 0.35-0.43 m inside the built edge raw). On the 12 NAIP rows
  beside them (240-252, 262-272) the same values sit -0.03 m from NAIP's (p10 / p90 -0.17 / +0.04). Past the asphalt a
  grey strip (intensity ~2,200-2,900) runs 3-3.5 m before the prairie (~5,300): round 4's greying verge; not asphalt.
- **The fork, R row s 0-19**: **there is no edge of the north loop's own**: the gore's grass begins at its apex, E -179.27
  N 106.09 (lon / lat in the file), north-loop own s 19.5, 9.2 m right of the north loop's line and 9.25 m left of the West
  lap's. South of it the fork is one pavement: where a row's step reads cleanly it is the West lap's far (right) edge,
  7.97-10.72 m past the north loop's built edge (rows 2, 6). From row 26 the north loop's own right edge reads cleanly.
- **The merge, L row s 996-1001**: the asphalt's edge is the east corner's outline (item 1), 0.35 m inside to 0.95 m
  past the built edge, off OSM 5.51-6.77 m (photo frame); the kerb's outer side 1.38 m further (6.89-8.15 m).
- **The merge, R row s 988-1001**: no edge on these rows' normals: the right side is the mouth, the West lap's pavement;
  its real edge is the merge's west corner. Row 986 meets that corner 3.61 m past the built edge.
- **The west corner (the bellmouth round 4 built at NAIP's R 14.0 m)**: the lidar's asphalt edge turns much tighter:
  **R 6.75 m** (median deviation 0.17 m; 5.0-7.25 m over other leg windows). By eye on the 0.3 m photo the ground between
  that arc and a 14 m one is tan, not grey. A disagreement with round 4, reported, not acted on.

## [invented] numbers this adds

Reader tuning only (every one in `params` of each JSON): the 1.2 m step window, 1.5 m station and 0.75 m ray widths,
score 1.6, 3 returns a side, the 0.8x / 1.25x threshold check, the 0.5 m stripe core and 0.2 m taper depths, the 70 % arc
middle, the 22 m spot margin and the 5-60 m radius grid. The returns, the registration and the radii are measured.

## Uncertain

- 2 returns per m2: one read sees 3-9 returns a side; positions are good to ~0.2-0.3 m (the registration's residual).
- The east corner's single radius depends on where its legs are taken (21.25-23.0 m); the corner is not one circle.
- The kerb's outer side behind the fillet is 1.4 m by the lidar's white blocks, 1.9-2.1 m by NAIP's paint.
- The stripes' ends and the west corner differ from the 2023 photo's reads; the lidar is five years older.
