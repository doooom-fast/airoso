# Lake Murray north network: the real outer curbs, read off the 2024 lidar (pieces A-D)

These files are the measurements for the "road edges re-fit" round. For every 2.5 m station of the four north pieces in
`data/expansion.north.json` that no earlier lidar file had read, they give each outer road edge, the real road's middle and
width, and the difference between real and built for each. Everything here is read from the data; nothing is built and no
config is changed. The numbers are measured. Every setting the method chose is marked **[invented]** in the script and
listed under `settings` in each JSON.

Read on the G10 on 2026-11-24 (job lm-north-curbs-20261124), one piece per run, under `nice -n 19 ionice -c3`. Peak
memory was 330 MB. The source is USGS 3DEP `USGS_LPC_CA_SanDiegoCo_D24` (flown 2024-11, public domain, EPSG 6340). The
inputs were origin/main `d31cb9a8`: `tools/expansion_pieces.py`, plus `expansion.north.json`, `centerline.local.json`
and `osm.expansion.json` from Lake Murray's `data/`. Each JSON lists the tiles it read and the md5 of every input.

    python -I north_curbs_g10.py <D24 tiles dir> <lm-shrub tool dir> <repo checkout> <out dir> --piece A|B|C|D [--prior <earlier json>]

## Files

| file | what |
|---|---|
| `north_curbs_g10.py` | the script; its docstring is the method |
| `north_curbs_A.lidar.g10.json` | A, Waring Road (J1 to J2) |
| `north_curbs_B.lidar.g10.json` | B, Princess View Drive (J2 to J3) |
| `north_curbs_C.lidar.g10.json` | C, Mission Gorge Road (J3 to J4), only the stations the earlier files left out |
| `north_curbs_D.lidar.g10.json` | D, Jackson Drive north (J4 to J5), only the stations the earlier files left out |

## What was read where

| piece | stations | read here | read earlier (not redone) | check stations (overlap) |
|---|---|---|---|---|
| A | 393 | all, s 0-980 | none | none |
| B | 445 | all, s 0-1110 | none | none |
| C | 912 | 29: s 0-37.5, s 2247.5-2276 | s 40-250 and s 225-2245: `mg_median/mg_median_faces*.lidar.g10.json` | 20: s 40-62.5, s 2222.5-2245 |
| D | 803 | 670: s 0-222.5, s 495-1237.5, s 1302.5-2004 | s 225-492.5 and s 1240-1300: `jackson_paint/jackson_curbs_D.lidar.g10.json` (branch `claude/lm-jackson-paint-lidar-20261123`) | 19: s 225-247.5, s 1240-1260 |

## Signs

u is metres off the piece's line, with + to the left of travel along increasing s (the piece frame,
`tools/expansion_pieces.Piece.frame`). "Real minus built" is the lidar face's u minus the row's `left_m` / `right_m`.

- On the left, a negative value means the real curb is nearer the line than the built one (built too wide on that side).
- On the right, a positive value means the same thing.
- The middle is (left + right) / 2. A positive middle means the real road lies left of the built one.
- Width is left - right. A negative width means the built road is wider than the real one.

## What it found

A 25 m bin (s 0-25, 25-50, and so on) is "called" for a quantity when 5 or more stations read it and their IQR is 1 m or
less [invented]. The ranges below are runs of consecutive called bins: the range of those bins' medians. The JSONs also
give the same runs from a running median per station (`station_runs_*`), which is finer and ignores the bin edges.

**A, Waring Road.** 217 left faces, 200 right, 128 with both (of 393 stations). The built road is too wide, mostly on the left.
- Off by over 1 m:
  - left curb nearer the line by 1.1-1.9 m over s 0-247.5 (median -1.35), s 275-397.5 (-1.33 to -1.42) and s 525-572.5 (-1.37 to -1.56); +1.27 at s 700-722.5;
  - right curb nearer the line by 1.0-1.3 m at s 450-472.5, 650-672.5, 700-722.5, 875-897.5 and 925-947.5;
  - middle -1.0 to -1.4 at s 25-47.5 and 75-122.5;
  - width -1.7 to -2.3 at s 100-122.5, 300-347.5, 375-397.5 and 875-897.5.
- Within 0.3 m: left at s 775-797.5; right at s 100-122.5 and 750-772.5; middle at s 375-397.5 and 775-797.5; width at s 775-797.5.
- Unmeasured: left 176 stations (45 %), right 193 (49 %).

**B, Princess View Drive.** 248 left, 215 right, 123 with both (of 445). The real road lies about 2 m right of the built one over most of the piece.
- Off by over 1 m:
  - left curb 1.1-3.8 m nearer the line over s 25-47.5, 150-197.5, 225-322.5, 350-422.5, 450-522.5, 550-722.5, 750-772.5 and 975-1047.5;
  - right curb 1.9-3.7 m further out over s 475-522.5, 550-597.5, 675-697.5 and 750-972.5, and 1.06 m further out at s 1000-1022.5; nearer the line by 1.3 m at s 100-122.5 and 350-372.5, and by 2.8 m at s 1075-1097.5 (mostly inside the J3 pad);
  - middle -1.7 to -3.7 at s 475-497.5, 575-597.5, 750-772.5 and 825-872.5 (and +1.2 at s 1075-1097.5, mostly the J3 pad);
  - width -2.8 to -3.2 at s 25-47.5 and 350-372.5 (and -3.1 at s 1075-1097.5).
- Within 0.3 m: only the middle at s 350-372.5.
- Unmeasured: left 197 (44 %), right 230 (52 %).

**C, Mission Gorge Road (s 0-37.5 and s 2247.5-2276).** 7 left, 11 right, 5 with both (of 29).
- Off by over 1 m: no 25 m bin is called (the stretches are short). Per station:
  - the right curb is 1.0-1.2 m nearer the line over s 17.5-37.5 and 1.6 m nearer over s 2247.5-2265;
  - the left is within 0.3 m (s 25-37.5, called: median +0.07);
  - middle +0.60, width -0.77 (5 stations).
- Unmeasured: left 22 (76 %), right 18 (62 %), almost all inside the J3 and J4 pads.

**D, Jackson Drive north (the stations not read before).** 418 left, 474 right, 299 with both (of 670).
- Off by over 1 m:
  - left curb further out by 1.1-4.0 m over s 500-597.5, 700-772.5, 1125-1172.5, 1302.5-1322.5 and 1600-1622.5; nearer the line by 1.2-2.2 m over s 1700-1797.5;
  - right curb nearer the line by 4.0-4.2 m over s 175-222.5, 1.5-2.8 m over s 525-847.5, 2.0 at s 900-922.5, 1.1-1.2 over s 1025-1072.5, and 1.0-1.6 over s 1125-1237.5;
  - middle +1.1 to +2.8 over s 525-622.5, 700-772.5, 900-922.5, 1050-1072.5 and 1125-1172.5; -1.57 at s 1725-1747.5;
  - width -1.2 to -1.7 at s 700-722.5, 825-847.5, 900-922.5 and 1950-1972.5.
- Within 0.3 m:
  - left at s 825-847.5, 925-972.5, 1450-1472.5, 1675-1697.5 and 1875-1947.5;
  - right at s 25-47.5, 1400-1422.5, 1450-1472.5, 1500-1622.5, 1650-1722.5 and 1900-1922.5;
  - width at s 575-597.5, 725-772.5, 1000-1072.5, 1100-1172.5, 1325-1347.5, 1375-1422.5, 1450-1522.5, 1650-1672.5 and 1900-1922.5.
- Unmeasured: left 252 (38 %), right 196 (29 %).

### What can't be called, and why

Every side that gives no face has one category (`cant_call` per station; counts per piece in `summary.unmeasured`; runs per
25 m in `per_25m[].cant_call`):

| category | A left / right | B | C | D |
|---|---|---|---|---|
| step out of bounds: a candidate that, refined, steps under 0.05 m or the wrong way (a low or rolled curb, a gutter lip, a patch) | 97 / 97 | 90 / 110 | 4 / 0 | 91 / 70 |
| canopy (the road side stands off the road, or 25 %+ of the returns near the built edge are not last returns) | 42 / 49 | 49 / 28 | 0 / 2 | 80 / 51 |
| junction mouth (an OSM road or service way meets that side) | 17 / 19 | 26 / 66 | 0 / 0 | 47 / 42 |
| vehicle (a parked car or other non-ground object at the curb, no road behind it) | 12 / 15 | 19 / 16 | 0 / 0 | 11 / 15 |
| the piece's own junction pad or weld | 8 / 11 | 13 / 10 | 18 / 16 | 23 / 18 |
| no rise or drop (flush edge or unmapped driveway) | 0 / 2 | 0 / 0 | 0 / 0 | 0 / 0 |

The longest runs (4 or more stations in a row):

- **A**:
  - mouths: Galewood Street (s 115-135, both sides) and Eldridge Street (s 405-427.5, both);
  - canopy: left s 502.5-510; right s 247.5-255 and 547.5-555;
  - the J2 pad: s 965-980.
- **B**:
  - mouths, left: Glenroy Street s 65-85, Fontaine Street s 532.5-560, a service way s 812.5-822.5;
  - mouths, right: Glenroy s 70-90, Princess View Court s 170-190, Princess View Place s 310-325, Princess View Way s 375-395, Fontaine s 537.5-550, Laura Street s 705-727.5;
  - canopy: left s 775-787.5 and 802.5-810; right s 142.5-155;
  - steps out of bounds: right s 407.5-495 and 617.5-667.5, in several runs.
- **C**: only the J3 and J4 pads.
- **D**:
  - left: canopy s 30-50, 65-87.5, 185-207.5, 940-950 and 1180-1192.5; mouths at Winding Creek Drive (s 640-660), Tuxedo Road (s 790-810), Birchcreek Road (s 1795-1817.5) and three service ways; nothing read before s 100;
  - right: mouths at Hemingway Drive (s 495-515) and Park Ridge Boulevard (s 1615-1637.5); canopy s 622.5-630 and 1777.5-1787.5;
  - the J4 pad (s 0-25) and the J5 weld (s 1977.5-2004).

## Method

The method is `jackson_paint/jackson_curbs_g10.py`'s, which is itself the outer-curb reading of
`mg_median/mg_median_faces_g10.py`. Its edge finder is kept as it was:

- the returns are the last returns, not withheld and not noise;
- the along-road grade is taken out;
- each 0.10 m bin holds the 20th percentile of its returns;
- the step detector compares each bin with a line through the 1.2 m of bins just inside it;
- the face is the first rise outward past 0.05 m, or the first drop past 0.10 m;
- the face is refined on the returns themselves, to the gap between neighbouring returns where the fewest fall on the wrong side;
- each face is typed curb, edge (rise) or edge (drop).

What this script adds or changes:

- **Window.** The window runs to ±22 m, as on Mission Gorge (Jackson's was ±18 m). The built edges reach +17.1 / -16.3 m.
- **Search start past raised islands.** Where `medians[]` declares a raised island, the search starts 3 m past that side's island face [invented], so the island's outer face is not read as a drop.
- **Things inside the road.** A rise that comes back down to the road within 2.5 m, with a lane's width of road past it, is passed and the search goes on. It may be an undeclared divider, a post line, a bump or a car in a lane. On piece D, s 880-1010, a narrow raised divider runs from 8.5 m to 4.4 m right of the line. Where the search would begin on top of such a thing, it begins again where the road resumes (`search_from_moved`).
- **Vehicles at the curb.** A non-ground rise of 0.5 m or more that comes back down within 3 m is a vehicle or object. With road behind it, it is passed. Without road (a car parked at the curb), the side is not called.
- **Labels.** Every unread side gets one of the categories above. Junction mouths come from `osm.expansion.json`: a way meeting the built edge at 25° or more flags ±15 m (±7 m for a service way) [invented].
- **Neighbour check.** Each face carries `minus_neighbours_m`, its offset from the median of the other faces read on that side within ±12.5 m. Faces more than 0.5 m off are counted in `summary.faces_apart_from_neighbours` (a mouth, a bus bay, a curb return or a misread) and kept in the data.
  - A: 34 of 217 left, 47 of 199 right.
  - B: 36 / 246 and 18 / 207.
  - C: 1 / 7 and 2 / 11.
  - D: 30 / 416 and 44 / 472.

Tried and dropped: Jackson's hand-on distance (`CONT_M`, how far past a failed candidate the search may go) was raised from
1.0 m to 1.5 m, and to 3.0 m in a separate run. That read more faces. However, most of the added faces stood more than
0.3 m off their neighbours: past the real low curb, on the back of the walk. So it stays at 1.0 m. That is the main
reason "step out of bounds" is the largest unread category on A and B.

## The overlap check (the same stations, read by the earlier files)

- **D**, against `jackson_curbs_D.lidar.g10.json` (s 225-247.5, s 1240-1260): 27 sides read by both, all within 0.06 m, median 0.000. Three sides are read by one file only.
- **C**, against `mg_median_faces.lidar.g10.json`, which uses a different outer-curb method (all returns, rise only, one cross-fall line):
  - s 25-62.5: 13 sides read by both, median 0.00, 10 within 0.10 m; one at s 30 right is 0.84 m off.
  - Against `mg_median_faces_full.lidar.g10.json`, s 2222.5-2245: 15 sides read by both, median 0.00, 12 within 0.10 m.
  - The outliers are s 2230 left (this file reads a 0.47 m rise 2 m further out than the earlier 0.08 m curb) and s 2245 left (-4.2 m: the earlier file read a 1.3 m bank at 20.6 m).

## What these numbers are not

- They are **relative to the built rows** of `expansion.north.json` at `d31cb9a8`. A re-fit that changes the line or the rows changes "built".
- The lidar's absolute horizontal accuracy is not measured here. The NAD83(2011) to WGS84 step is pyproj's null transform, stated to 2 m. It moves both faces together, so widths are unaffected, but it limits what a middle shift under about a metre can say.
- A face's own uncertainty (`unc_m`, half the gap between the returns it lies between) is a few centimetres. The scatter between neighbouring stations (the IQRs in `per_25m`) is the honest error bar: typically 0.1-0.5 m.
- Junction mouths come from OSM positions. Driveways that OSM does not map read as "no rise or drop" or "step out of bounds".
- Where the asphalt meets a rolled curb or a sloping verge rather than an upright curb, the face read is the first rise past the flow line. D's right side at s 880-1010, beside the divider, is like this.

## Reading a JSON

- `coverage`: which stations were read here, and which earlier.
- `summary`:
  - per-piece counts and runs (`built_off_over_1m`, `built_within_0_3m`, `station_runs_*`);
  - `unmeasured` by category;
  - `cant_call_runs`;
  - `faces_apart_from_neighbours`.
- `per_25m[]`: per bin:
  - station counts;
  - median / min / max / IQR / n of `left_minus_built_m`, `right_minus_built_m`, `real_minus_built_middle_m` and `real_minus_built_width_m`;
  - a call per quantity;
  - face types;
  - can't-call runs per side.
- `stations[]`: per station:
  - `built` (left_m, right_m, middle_m, width_m);
  - `left` / `right`, each with: verdict, type, `face_u_m`, `unc_m`, `step_m`, `cant_call`, `minus_neighbours_m`, any `objects` passed, `search_from_m`, intensity inside and outside;
  - `real_middle_m`, `real_width_m` and the four real-minus-built values.
- `check_stations[]`: the overlap stations, read the same way and kept out of the summaries.
- `overlap_check[]`: per earlier file, the station-by-station comparison.
- `osm_mouths`: the side streets and service ways found meeting each side.
- `settings`: every setting.
