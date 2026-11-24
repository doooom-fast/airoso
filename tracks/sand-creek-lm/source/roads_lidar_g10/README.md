# Sand Creek's real roads off the 2020 lidar (round 2 and after)

Kevin: "I just want real". These files hold measured numbers only. Every chosen constant is marked [invented] in
`roads_lidar_g10.py` and copied into each JSON's `constants`. They are data only: no config points at them, and no
build step reads them. Measured on the G10 on 2026-11-24.

The three items are the ones ledgers 0079 (round R item 4, "Full street width") and 0098 ("Measured and owed") name:

| file | item |
|---|---|
| `lap_colorado_quebec.lidar.json` | 1. Colorado Blvd (lap v3205 -> v140) and the lap's Quebec St (v1940 -> v2080), every 2.5 m of the lap's s |
| `quebec_arms_median.lidar.json` | 2. Quebec north of the lap: the median between the Northfield Quebec arms (grid_primary_78 / grid_primary_84#0#0), along their true lon / lat line, plus a record for each drawn row |
| `quebec_bridge_deck.lidar.json` | 3. The lap on the Quebec St bridge over Sand Creek: the class-17 deck every 1 m at the centre line and both wheel paths, the class-2 approaches, built minus real |
| `roads_lidar_g10.py` | the script (`tiles`, `measure`); its docstring gives the method |

## The lidar

- Source: USGS CO_DRCOG_2_2020, classes 2 (ground) and 17 (bridge deck), read through
  `tools/lidar_connector_profile.py`: its frame, its `tile_i_j.npz` cache and its `Ept.tile` reader.
- 18 tiles come from round 1's profile cache, complete: -16_-4..-16_1, -15_-4..-15_1, 16_-9, 16_-8, 16_-6, 17_-4,
  18_-5, 18_-4.
- 12 tiles were built here by the same reader: 14_-9, 14_-8, 15_-9, 15_-8, 16_-7, 17_-8, 17_-7, 17_-6, 17_-5, 18_-6,
  19_-5, 19_-4. These include 17_-5, 17_-6 and 18_-6, which 0079 lists as tiles the sandcreek_quebec pad needs.
- Most of their EPT nodes came from local copies of earlier fetches (2026-11-22 and 2026-11-23). This round fetched 11
  nodes, 2,847,563 bytes: 9-234-280-253, 9-237-281-253, 10-469-560-507, 10-473-560-507, 10-473-561-507, 10-474-562-507,
  10-474-563-507, 10-474-564-507, 11-945-1120-1014, 11-946-1120-1014 and 11-946-1121-1014.
- Frame: the lap's own. That is ENU metres about `data/centerline.local.json`'s origin (WGS84 series), with heights =
  las z - origin.elev_m, which is the lap's y.

## Conventions

- `u` is lateral, with + = left of travel: of the lap for item 1, of each arm's own direction for item 2.
- `s_lap` is plan metres along `centerline.local.json` from v0. `built` is the lap's (or the drawn piece's) `widths_m`,
  centred at +-w/2. The lap's widths are symmetric scalars.
- Each face has a `kind`:
  - an outer edge is `curb` (it steps up outward by 0.08 m or more), `drop` (it steps down outward by 0.08 m or more),
    `fall` (no step; the outward grade drops by 10 % or more, which is the edge of a road on a fill) or `none`;
  - a median face is `curb` or `none`.
- A `none` face's `u` only shows where the trace ran. It is not a measurement, and no width uses it.
- `real_minus_built_m` is the face's u minus the built edge on that side.
- A station is `divided` only when both median faces read as curbs, the far face drops onto a smooth carriageway, and
  the two carriageways' lines sit within 0.6 m at the faces.
- The lap is built as one 16.5 m ribbon on one side of each divided road, so the median lies on its left.

## Item 1: Colorado and the lap's Quebec

**Colorado.** The raised median runs from s 143 to s 353 (v47-v118).

- The median reads as divided on 58 stations. On the 25 of them where both outer curbs also read, the real width from
  curb to curb is 25.75 m (median; range 25.0-27.75). The built ribbon is 16.5 m.
- The median's faces sit at u +5.75 and +9.75 (medians). The median is 4.25 m wide and narrows to 1.5-2.5 m past
  s 315.
- Its top stands 0.14 m over the near carriageway's line and 0.15 m over the far one's. The face steps are 0.14 m
  (near) and 0.13 m (far).
- The carriageways are 11.0 m (near; range 10.25-13.5) and 10.5 m (far; range 9.75-13.25), face to face.
- On the divided stations the right curb is at u -5.25 (real minus built +3.0 m, step 0.19 m). The far carriageway's
  outer curb is at u +20.1 (19.25-22.75). The built ribbon's left edge (+8.25) therefore runs about 2.5 m onto the median.
- There is no raised median in the 2020 ground over s 9605-140:
  - the 48th approach, s 9605-63: 38-41 m wide, curbs at u -16..-12 / +24..+26;
  - s 63-140: one crowned surface, curbs at -5.25 / +21, 26.25 m.
- At the 50th corner (s 365-418), no left face reads.

| s_lap | divided | real width, divided stations | built width | median near / far face u | median width | top over near side | right edge u (curb / fall / none) | first left face (curb / none) |
|---|---|---|---|---|---|---|---|---|
| 9605.0-13.3 | 0/20 | - | 16.50 (16.50..32.90) | - / - | - | - | -12.75 (-16.00..-11.75) (10/7/3) | 7/13 |
| 15.8-63.3 | 0/20 | - | 16.50 | - / - | - | - | -14.75 (-16.00..-5.00) (16/0/4) | 12/8 |
| 65.8-113.3 | 0/20 | - | 16.50 | - / - | - | - | -5.25 (-5.50..-5.00) (20/0/0) | 7/13 |
| 115.8-163.3 | 7/20 | 26.12 (25.75..27.75) | 16.50 | 5.75 (5.25..6.00) / 10.25 (9.75..10.50) | 4.50 (4.00..5.00) | 0.15 (0.11..0.28) | -5.00 (-5.25..-4.75) (20/0/0) | 12/7 |
| 165.8-213.3 | 16/20 | 25.50 (25.25..26.00) | 16.50 | 5.75 (5.50..6.25) / 10.00 (9.50..10.50) | 4.25 (3.75..4.75) | 0.14 (0.10..0.17) | -5.25 (-5.75..-4.75) (16/0/4) | 19/1 |
| 215.8-263.3 | 16/20 | 25.12 (25.00..27.50) | 16.50 | 5.50 (5.25..5.75) / 9.75 (8.00..10.00) | 4.25 (2.75..4.75) | 0.14 (0.12..0.19) | -5.50 (-7.25..-4.25) (10/3/7) | 18/2 |
| 265.8-313.3 | 11/20 | 26.38 (26.00..26.75) | 16.50 | 5.25 (4.75..5.50) / 9.00 (6.50..9.50) | 3.75 (1.50..4.25) | 0.14 (0.11..0.17) | -7.00 (-7.75..-6.75) (6/0/14) | 16/4 |
| 315.8-363.3 | 8/20 | 27.00 (26.75..27.00) | 16.50 (16.50..19.25) | 5.75 (5.00..6.75) / 7.88 (6.50..8.75) | 2.00 (1.50..2.50) | 0.15 (0.09..0.20) | -6.75 (-7.00..-6.50) (20/0/0) | 12/8 |
| 365.8-413.3 | 0/20 | - | 24.15 (19.58..32.90) | - / - | - | - | -7.00 (-7.75..-6.50) (16/0/4) | 0/20 |

**The lap's Quebec.** The 2020 ground shows no raised median along it. Only 5 of 167 stations read as divided, and
they are scattered.

- The right edge is at u -1.5..-5 over s 5960-6110, on a road raised on fill. Over s 6010-6060 it reads as the
  fill's top edge (`fall`) on 17 of 20 stations. Elsewhere it is a mix of curbs and falls.
- The first left face is mostly `none`. Over s 6010-6060 a 0.04-0.08 m rise at u +9..+10.5 sits under the 0.08 m
  curb rule.
- Ledger 0079's NAIP reading at v2000 (2023 imagery) describes a planted median at +5..+17. The 2020 lidar does not
  show it raised. Whether the street changed between 2020 and 2023 is not settled here.

## Item 2: the Northfield Quebec arms (Quebec north of the lap)

**The drawn pieces.** Two pieces of `data/connectors.local.json` are drawn in the grid's sphere frame:

- grid_primary_78, rows 0-42, from the I-70 end to the sandcreek_quebec pad;
- grid_primary_84#0#0, rows 0-36, from the pad north.

Each is read at its true point (x * KX, z * KZ; KX 1.0024949, KZ 0.9985216). The true point lies 4.56-4.72 m from the
drawn one, almost all of it east.

**The median.**

- It is 2-4 m wide: the median width on divided rows is 2.96 m (78) and 2.12 m (84#0#0), range 1.24-5.5 m.
- Its near face is at u +6.76 (78) / +6.88 (84#0#0) off each arm's true line, with a step of 0.13-0.16 m. Its far face
  is at u +10.3 / +11.0, with a step of 0.13-0.14 m.
- Its top stands 0.13-0.17 m over the carriageways.
- Measured faces by row:
  - grid_primary_78: near face on rows 12-41, divided rows 15-41;
  - grid_primary_84#0#0: near face on rows 0-33, divided rows 12-33.
- Each arm's carriageway is 16.5-17 m from its outer curb (u -9.5 / -10.0) to the median's near face. The street is
  37-39 m from outer curb to outer curb.
- Each drawn piece is 9.5 m wide.

**Per row.** `rows_list` gives each face as:

- `u_drawn_m`, the face carried into the drawn frame, which is where to build it on the drawn line;
- `u_vs_drawn_point_as_lidar_m`, which includes the 4.6 m frame gap;
- the median's `top_minus_drawn_y_m`.

## Item 3: the lap on the Quebec St bridge over Sand Creek

**The deck.** The class-17 deck runs under the lap's centre line from s 5841 to s 5936 (v1950-v1982, 95 m).

- It is not flat. Along the centre it rises 23.59 -> 24.00, about 0.43 %. The wheel paths read within 0.03 m of the
  centre.
- The lap's centre line (centerline.local.json y) runs 23.99 -> 24.38. That is +0.32..+0.40 over the deck, median
  +0.34, and +0.33 / +0.36 on the wheel paths.

**The approaches (class 2).**

- North, s 5801-5840: the ground is 23.53-23.78 and the built line is +0.05..+0.43 over it, median +0.24.
- South, s 5937-5976: the ground is 24.00-24.25 and the built line is +0.29..+0.40 over it, median +0.34.

**The pad.** The sandcreek_quebec pad's S row is flat at 24.115. It stands +0.27 (E point) and +0.44 (middle) over the
deck. Its W point is off the deck, over the creek bed at 18.56.

## Not settled

- The lap's Quebec reads as one surface in 2020 (see item 1). The NAIP 2023 reading describes a median there.
- A station's face u is quantised to the 0.25 m raster bin.
- Where a narrow median's far face does not read as a curb, the station is not divided. Its first left face is then
  the median's near face, so its one-carriageway width is the near carriageway only. This happens on Colorado s 300-335
  at u +4.75.
- Junctions, driveways and median openings read as `none`.
- Item 3's built height is the centre line's y, applied to all three paths. The build's crossfall there is not read.

## Rerun

```
python -I roads_lidar_g10.py tiles   --repo <airoso checkout> --cache <tile dir> --tiles <i_j,...> --mirror <EPT copy dir> --dl <new dir> [--plan plan.json]
python -I roads_lidar_g10.py measure --repo <airoso checkout> --cache <tile dir> --out <dir> [--only lap,arms,bridge]
```
