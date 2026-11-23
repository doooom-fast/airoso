# Mission Gorge Rd's raised median, measured off the 2024 lidar (G10, 2026-11-23)

An independent, colour-free reading of the island's two faces, for the photo readings in this folder (`README.md`,
`faces_md.py`, `fix_mg_median.py`). `mg_median_faces_g10.py` -> `mg_median_faces.lidar.g10.json`. It reads only and
builds nothing; nothing in the data was changed.

- **Source.** USGS CA_SanDiegoCo_D24, flown 2024-11. Tiles 11SMS492629 and 11SMS493630 (md5s in the JSON).
- **Frame.** Piece C's own frame (`tools/expansion_pieces.Piece.frame`). Metres off piece C's line, **+ = left of J3 -> J4
  travel = north-west**. Lidar -> local by the lm-shrub tool's own code (`shrub_heights.Track.to_local`: pyproj
  6340 -> 4326, then the WGS84 metres-per-degree series at the origin).
- **Stations.** Every 2.5 m over s 40-250 and s 980-1215, with check stations at s 25-37.5, 252.5-300, 930-977.5 and
  1217.5-1260. Each takes +-12 m across and +-1.25 m along **[invented window]**.
- **Method.** The script's docstring. In short: a step detector on 0.10 m bins (0.25 m for class 2), then each face is
  placed between the two neighbouring returns where the fewest fall on the wrong side. Its +- is half that gap: the
  point spacing, median **0.03 m**.

## The frame check

- The left normal points north-west at all 244 stations.
- MD11 / MD13 / MD13b's rings put side A at `median_off_m + w/2` in this frame to 7 mm (834 stations).
- The projection round trip is 0.0 m. The lidar road at the line is the plan's `y_3dep` to -0.005 m (median).
- **The sign is confirmed by strip B.** The photo's raw centroid is -2.24 m and the lidar's middle is -2.32 m.
- **The "full-width" reference stretches do not hold the plan's band.** These are s 930-985 and 1215-1260, where
  `faces_md.py` took the island to fill its band. There the lidar island is 0.61 m narrower and **0.86 m right**
  (south-east) of the declared band, over 41 stations. The photo's raw reading there was 0.30 m narrower and 0.49 m
  right. So `fix_mg_median.py` calibrated its +0.30 m / +0.49 m against a band that is itself off. The lidar sides with
  the photo's *uncorrected* middle: within 0.22 m there, 0.08 m on strip B and 0.06 m at MD13's start.

## What the lidar shows

| | lidar | photo (this folder) | lidar - photo |
|---|---|---|---|
| MD11 start | an island already at s 25 (1.0 m wide; the J3 pad cuts at s 24.74) | declared from s 45, 0.57 m nose | starts >= 20 m earlier |
| MD11, s 25-100 | 1.25 m wide, middle -1.01 | declared -0.50; photo: unresolved | 0.54 m SE of declared |
| MD11, s 102.5-130 | runs diagonally NW, middle -0.8 -> +2.65 | -- | -- |
| MD11, s 132.5-182.5 | faces +3.34 / +2.02, middle +2.66; flat road on the declared band | photo: R - G "about +2 for 4.5 m to the north-west" | 3.16 m NW of declared |
| MD11 end | last island station s 182.5 (0.61 m nose); runs on through the declared st 174 crossover | declared end s 167.5 | +15 m |
| opening 1 | s 185-192.5 ("none", 4 stations) | declared MD12 (s 182.5-195) "lies on the crossover's asphalt" | agrees |
| MD12 | s 195-207.5; at s 200-205 faces +2.94 / -0.65 (3.58 m wide, middle +1.14) | declared s 182.5-195, 1.70-1.77 m, middle -0.50 | +12.5 m on; 1.64 m NW |
| opening 2 | s 210-220 ("none", 5 stations) | declared crossover s 196-208; photo: no terracotta s 210-222.5 | agrees with the photo |
| MD13 start | nose s 222.5, first island station s 225; s 225-250 1.26 m wide, middle -0.90 | photo strip from s 225 (`md13_gaps.json`) | middle +0.06, width -0.25 (s 225-297.5, 30 stations) |
| taper s 982.5-1010 | 3.79 -> 1.08 m; the left face stays +1.4..+2.2, the right comes in from -2.08 to +0.33 | fit: linear 4.49 -> 1.96 | at s 1010 lidar faces +1.41 / +0.33, fit +1.82 / -0.14 |
| **strip A**, s 1012.5-1077.5 (26 island stations) | **1.24 m** (p10-p90 1.15-1.33), middle **-0.08** (-0.32..+0.50: it bends) = declared **-0.27** | fit 1.96 m, declared +0.43 (abs +0.69); raw 1.66 m, +0.18 | **-0.72 m, -0.70 m** vs the fit (left face -1.09, right -0.33); -0.42, -0.26 vs raw |
| strip A's nose | last island station s 1082.5 (1.06 m); s 1085 unclear (vegetation on the nose) | nose s 1085 | agrees |
| **gap** | **s 1087.5-1112.5 "none"** (11 stations) | s 1087.5-1117.5 (13 stations) | 5 m shorter at its east end |
| strip B's nose | s 1115 a 0.24 m tip; first island station s 1117.5 (1.08 m) | nose s 1120 | 2.5-5 m earlier |
| **strip B**, s 1127.5-1192.5 (25 island stations) | **1.30 m** (1.25-1.43), middle **-2.32** (-2.43..-2.15) = declared **-2.08** | fit 1.84 m, declared -1.50 (abs -1.75); raw 1.54 m, -2.24 | **-0.54 m, -0.58 m** vs the fit (left -0.82, right -0.32); -0.24, -0.08 vs raw |
| taper s 1192.5-1212.5 | s 1192.5-1197.5: right face only (-3.0); s 1200 -> 1212.5 the left face moves -1.16 -> +0.86, the right holds -2.0..-2.7 | fit: left -0.97 -> +2.21, right -2.8..-3.2 | narrower; the widening is on the left |

**The top** stands **0.136 m** over the mean road either side. That is the median of 147 island stations, p10-p90
0.116-0.161. The north-west step is 0.132 m and the south-east 0.145 m. For scale, `source/college_r2/STEP-DESIGN.md`
gives the median tool's built tops at 0.141-0.228 m, median 0.185.

**Class 2 does not see the narrow tops.** D24's ground class leaves most raised tops out. At 105 of the 145 island
stations read off all returns there is no class-2 return between the faces, and class 2 alone finds the plateau at only
11 of them. So the reading is all returns (non-withheld, noise 7 / 18 out). Only returns within -0.25..+0.40 m of a
class-2 TIN are kept **[invented]**, which takes out cars and canopy. Where vegetation sits on the top (5+ returns over
0.5 m), class 2 is used alone: at s 995 it shows the plateau, and at s 1085 it does not (unclear).

## Unclear, and what was changed after looking

The 13 unclear stations:

- **Top just under 0.10 m:** s 77.5, 115, 127.5, 1027.5 (0.092-0.099 m).
- **Noses:** s 222.5 and 1115 (one face, or a 0.24 m tip), and s 1085 (vegetation).
- **Tapers:** s 1002.5 and 1207.5.
- **One face only:** s 1175, and s 1192.5-1197.5, where strip B's left side is within 0.05 m of the pocket's surface.

The bounds are **[invented]**. The request held each side to 0.10-0.30 m, and the first run marked 30 of 85 J3-end
stations unclear. Most of those had a sharp north-west face only 0.05-0.10 m tall, because the top leans toward it. So
the 0.10-0.30 m bound now applies to the top over the mean road, and each face needs 0.05 m. Each station's
`both_steps_ge_step_lo` says whether it also passes the strict rule: 114 of 147 do. The detector's candidate threshold
moved from 0.06 to 0.05 m on the same run.

**Not measured here:**

- The lidar's absolute horizontal accuracy. pyproj's NAD83(2011) -> WGS84 step is the null transform, stated to 2 m.
- Whether the plan's line or the islands moved between NAIP 2022 and the lidar (2024-11).

## Re-run (on the G10, or anywhere with the tiles)

```bash
nice -n 19 ionice -c3 python -I tracks/san-diego-lake-murray/source/expansion/mg_median/mg_median_faces_g10.py \
    <tiles dir> <lm-shrub tool dir> <airoso checkout> <out dir>      # or MG_TILES / MG_LM_TOOL / MG_AIROSO / MG_OUT
```

The run takes 35 s and about 250 MB. `--reuse` reads `<out dir>/work/corridor.npz` again instead of the tiles. Run on
this commit's data: the declared band comes from `mg_median_correction.json` rows[0].
