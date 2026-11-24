# Mission Gorge Rd's raised median, measured off the 2024 lidar (G10, 2026-11-23)

An independent, colour-free reading of the island's two faces and the road's two outer curbs, for the photo readings
in this folder (`README.md`, `faces_md.py`, `fix_mg_median.py`). `mg_median_faces_g10.py` writes two files:
`mg_median_faces.lidar.g10.json` (s 40-250 and s 980-1215, in detail) and, with `--full`,
`mg_median_faces_full.lidar.g10.json` (every station s 225-2245, one row per station of `columns`). It reads only and
builds nothing; nothing in the data was changed.

- **Source.** USGS CA_SanDiegoCo_D24, flown 2024-11. Tiles 11SMS492629, 493629, 493630, 494629, 494630 and 494631
  (md5s in the JSONs).
- **Frame.** Piece C's own frame (`tools/expansion_pieces.Piece.frame`). Metres off piece C's line, **+ = left of J3 -> J4
  travel = north-west**. Lidar -> local by the lm-shrub tool's own code (`shrub_heights.Track.to_local`: pyproj
  6340 -> 4326, then the WGS84 metres-per-degree series at the origin).
- **Stations.** Every 2.5 m over s 40-250 and s 980-1215, with check stations at s 25-37.5, 252.5-300, 930-977.5 and
  1217.5-1260; `--full`: every 2.5 m from s 225 to MD13b's end, s 2245 (809 stations). Each takes +-12 m across for
  the island and +-22 m for the outer curbs, and +-1.25 m along **[invented window]**.
- **Method.** The script's docstring. In short: a step detector on 0.10 m bins (0.25 m for class 2), then each face is
  placed between the two neighbouring returns where the fewest fall on the wrong side. Its +- is half that gap: the
  point spacing, median **0.03 m**.

## The frame check

- The left normal points north-west at all 244 stations.
- MD11 / MD13 / MD13b's rings put side A at `median_off_m + w/2` in this frame to 7 mm (834 stations).
- The projection round trip is 0.0 m. The lidar road at the line is the plan's `y_3dep` to -0.005 m (median; -0.002 m
  over the 809 stations of the whole run).
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

## The road's outer curbs

On the +-22 m section, the first rise outward past 7 m on each side is the curb face, refined like an island face. The
profile is every non-noise return, as the 20th percentile per 0.10 m bin **[invented]**. Past the curb the class-2 TIN
is no reference, because the walk often holds no class 2.

- **curb:** a step of 0.05-0.35 m **[invented]**.
- **edge:** a rise over 0.35 m, a wall, bank or hedge where the pavement ends. It counts as the road's edge.
- **none:** no rise at all (a mouth).
- **unclear:** the rest.

Over the whole run the left side reads 388 curb, 174 edge, 18 none and 229 unclear stations; the right side 525 curb,
30 edge, 15 none and 239 unclear. Curb steps are 0.11 m (left) and 0.10 m (right), medians. On the north-west side the ground
rises at the pavement (a bank or wall) over much of s 930-1080 and s 250-300, so there the side reads edge or unclear. `road_middle` is the mean of
the two outer faces where both are read (399 stations). The island's middle is then measured from it and set against
the plan's `median_off_m - (left_m + right_m) / 2`. Per 50 m, `reads` names which is off, with 0.30 m **[invented]** as
the line.

**What it settles.** Over s 1250-2000 both of the plan's curbs sit 1.6-3.0 m north-west of the real ones, by about the
same amount. So the real road is about as wide as planned (+0.38 m, median over the whole run) but displaced
south-east. The real island sits near the real road's middle (-0.6 to +0.5 m from it). The plan puts it 1.3-2.2 m
south-east of its own road's middle. So the larger error is the plan's road edges. The island itself is off by less:
0.3-1.1 m south-east of the declared band per 50 m, except at s 1900-1950 (0.04 m north-west). Over s 1100-1200 (strip B) the road edges are where the plan has them (middle -0.23 / -0.30 m), and the
island is off in the road, as strip B is by design. At the J3 end only the south-east curb reads cleanly (65 of 85
stations): it is 1.3 m inside the plan's at s 50-100 and 0.3 m outside it at s 100-200.

## The whole island, s 225-2245 (`mg_median_faces_full.lidar.g10.json`)

Of the 809 stations, 747 read island, 11 none and 51 unclear. Against the declared band the island is **0.73 m
narrower** (p10-p90 -2.66 to -0.11) and **0.68 m south-east** (-1.35 to +0.19), medians over 747 stations. The top
stands 0.152 m over the road (0.128-0.180).

| s | island / none / unclear | lidar width | declared width | lidar middle | declared middle | road middle, lidar - declared | island from road middle, lidar - declared |
|---|---|---|---|---|---|---|---|
| 225-247.5 | 10 / 0 / 0 | 1.25 (1.01 to 1.38) | 2.02 | -0.88 (-1.03 to -0.62) | -0.49 | +0.07 | -0.36 (6) |
| 250-297.5 | 20 / 0 / 0 | 1.39 (1.21 to 3.25) | 2.46 | -1.23 (-1.51 to -0.96) | -0.33 | -0.96 | -0.12 (14) |
| 300-347.5 | 19 / 0 / 1 | 4.75 (3.52 to 4.88) | 3.08 | +0.39 (-0.85 to +1.03) | -0.10 | -0.47 | +1.25 (12) |
| 350-397.5 | 20 / 0 / 0 | 4.56 (4.04 to 4.78) | 3.67 | +0.96 (+0.45 to +1.08) | +0.12 | +0.07 | +0.78 (8) |
| 400-447.5 | 17 / 0 / 3 | 4.40 (3.79 to 4.61) | 4.29 | +0.10 (-0.32 to +0.47) | +0.35 | -0.30 | -0.03 (4) |
| 450-497.5 | 19 / 0 / 1 | 4.35 (4.10 to 4.48) | 4.88 | +0.46 (+0.29 to +0.60) | +0.57 | +0.32 | -0.43 (8) |
| 500-547.5 | 19 / 0 / 1 | 4.37 (4.26 to 4.47) | 4.83 | -0.07 (-0.35 to +0.48) | +0.47 | +0.18 | -0.69 (11) |
| 550-597.5 | 19 / 0 / 1 | 4.20 (3.39 to 4.50) | 4.63 | -0.48 (-0.91 to -0.30) | +0.27 | -0.35 | -0.49 (15) |
| 600-647.5 | 20 / 0 / 0 | 3.85 (3.43 to 4.16) | 4.43 | -1.09 (-1.41 to -0.82) | +0.07 | -0.90 | -0.26 (15) |
| 650-697.5 | 20 / 0 / 0 | 3.58 (2.96 to 3.78) | 4.24 | -1.52 (-1.66 to -1.27) | -0.14 | -1.46 | +0.04 (10) |
| 700-747.5 | 18 / 0 / 2 | 3.41 (2.97 to 3.61) | 4.04 | -1.56 (-1.73 to -0.74) | -0.33 | -1.98 | +0.67 (8) |
| 750-797.5 | 19 / 0 / 1 | 3.44 (2.85 to 3.54) | 4.08 | -0.11 (-0.58 to +0.24) | -0.23 | -1.35 | +1.53 (2) |
| 800-847.5 | 18 / 0 / 2 | 3.37 (3.14 to 3.47) | 4.17 | -0.35 (-0.80 to +0.38) | -0.07 | -1.81 | +1.57 (6) |
| 850-897.5 | 17 / 0 / 3 | 3.26 (2.74 to 3.49) | 4.28 | -0.99 (-1.18 to -0.42) | +0.10 | -- | -- (0) |
| 900-947.5 | 17 / 0 / 3 | 3.63 (3.33 to 3.90) | 4.37 | -0.51 (-0.84 to +0.07) | +0.28 | -1.86 | +0.67 (1) |
| 950-997.5 | 19 / 0 / 1 | 3.80 (2.18 to 4.31) | 4.47 | -0.58 (-0.81 to +1.08) | +0.45 | -1.54 | +0.53 (5) |
| 1000-1047.5 | 18 / 0 / 2 | 1.22 (1.05 to 1.81) | 4.63 | +0.12 (-0.35 to +1.15) | +0.34 | -1.40 | +1.28 (11) |
| 1050-1097.5 | 14 / 5 / 1 | 1.25 (1.06 to 1.49) | 4.83 | -0.00 (-0.26 to +0.74) | +0.14 | -1.74 | +1.61 (9) |
| 1100-1147.5 | 13 / 6 / 1 | 1.28 (1.08 to 1.36) | 5.03 | -2.20 (-2.40 to -1.97) | -0.09 | -0.23 | -1.88 (11) |
| 1150-1197.5 | 16 / 0 / 4 | 1.37 (1.26 to 1.47) | 5.21 | -2.31 (-2.48 to -2.14) | -0.30 | -0.30 | -1.76 (15) |
| 1200-1247.5 | 19 / 0 / 1 | 4.44 (1.54 to 4.92) | 5.42 | -0.74 (-1.93 to -0.21) | -0.53 | -1.25 | +1.52 (14) |
| 1250-1297.5 | 20 / 0 / 0 | 4.88 (4.54 to 4.99) | 5.45 | -1.61 (-1.73 to -1.28) | -0.65 | -2.78 | +1.82 (12) |
| 1300-1347.5 | 20 / 0 / 0 | 4.96 (4.82 to 5.10) | 5.34 | -1.74 (-1.78 to -1.67) | -0.70 | -2.86 | +1.82 (12) |
| 1350-1397.5 | 20 / 0 / 0 | 5.07 (4.96 to 5.15) | 5.25 | -1.83 (-1.87 to -1.71) | -0.75 | -2.93 | +1.87 (14) |
| 1400-1447.5 | 20 / 0 / 0 | 4.91 (4.77 to 5.14) | 5.14 | -1.58 (-1.89 to -1.38) | -0.80 | -1.99 | +1.33 (8) |
| 1450-1497.5 | 20 / 0 / 0 | 4.84 (4.66 to 4.94) | 5.04 | -1.25 (-1.39 to -1.13) | -0.85 | -1.88 | +1.47 (6) |
| 1500-1547.5 | 20 / 0 / 0 | 4.80 (4.71 to 4.91) | 5.16 | -1.70 (-1.91 to -1.39) | -0.90 | -- | -- (0) |
| 1550-1597.5 | 20 / 0 / 0 | 4.78 (4.62 to 4.95) | 5.46 | -1.74 (-1.89 to -1.53) | -0.95 | -2.09 | +1.34 (8) |
| 1600-1647.5 | 20 / 0 / 0 | 4.72 (4.55 to 4.89) | 5.76 | -1.69 (-1.87 to -1.49) | -1.00 | -2.35 | +1.53 (9) |
| 1650-1697.5 | 19 / 0 / 1 | 4.76 (4.50 to 4.92) | 6.07 | -1.94 (-2.09 to -1.67) | -1.05 | -2.52 | +1.54 (7) |
| 1700-1747.5 | 19 / 0 / 1 | 4.85 (4.73 to 4.99) | 6.37 | -1.57 (-1.66 to -1.38) | -1.10 | -2.04 | +1.59 (13) |
| 1750-1797.5 | 19 / 0 / 1 | 4.85 (4.74 to 4.99) | 6.67 | -1.64 (-1.92 to -1.38) | -1.10 | -2.10 | +1.59 (16) |
| 1800-1847.5 | 18 / 0 / 2 | 4.86 (4.52 to 4.97) | 6.97 | -1.53 (-1.88 to -1.41) | -1.04 | -2.22 | +1.58 (12) |
| 1850-1897.5 | 14 / 0 / 6 | 4.82 (4.77 to 4.94) | 7.28 | -1.34 (-1.46 to -1.27) | -0.99 | -2.12 | +1.73 (4) |
| 1900-1947.5 | 15 / 0 / 5 | 4.88 (4.74 to 5.08) | 7.59 | -0.89 (-1.32 to -0.70) | -0.94 | -1.96 | +2.12 (13) |
| 1950-1997.5 | 20 / 0 / 0 | 5.40 (5.07 to 5.70) | 7.88 | -1.64 (-2.61 to -1.05) | -0.89 | -2.38 | +1.65 (16) |
| 2000-2047.5 | 20 / 0 / 0 | 5.22 (4.78 to 5.54) | 7.13 | -2.28 (-3.18 to -1.19) | -0.57 | -3.18 | +0.80 (3) |
| 2050-2097.5 | 19 / 0 / 1 | 4.42 (4.14 to 4.76) | 5.79 | -0.83 (-1.22 to -0.71) | -0.10 | +1.76 | -1.79 (5) |
| 2100-2147.5 | 19 / 0 / 1 | 4.29 (4.05 to 4.43) | 4.46 | -0.54 (-0.84 to -0.33) | +0.38 | +0.21 | -1.48 (9) |
| 2150-2197.5 | 15 / 0 / 5 | 1.40 (1.12 to 4.28) | 3.12 | +0.37 (-0.81 to +0.89) | +0.85 | +0.34 | -0.91 (7) |
| 2200-2245 | 19 / 0 / 0 | 1.27 (1.12 to 1.41) | 1.82 | +1.53 (+0.95 to +1.61) | +1.12 | +1.09 | -0.79 (15) |

Counts in the last column's brackets are the stations with the island and both outer faces read. Under 5 is too few to
call **[invented]**.

**Flags** (all in `summary.flags`):

- **Openings.** Only the crossing, s 1087.5-1112.5. The island ends after s 1082.5 and starts again at s 1117.5. There
  is no other opening, and no declared gap, between s 225 and s 2245.
- **Width changes over 0.3 m in 10 m:**
  - s 285-310 widens 1.37 -> 4.77 m (declared 2.54 -> 2.96).
  - s 975-1007.5 narrows 4.14 -> 1.14 m: strip A's taper.
  - s 1205-1230 widens 1.54 -> 4.83 m: strip B's taper.
  - s 2152.5-2160 narrows 4.3 -> 3.6 m. Over s 2162.5-2175 it reads unclear (narrow raised readings, 0.25-0.9 m).
    From s 2177.5 to s 2245 it is 1.1-1.4 m wide, where the plan has 3.0 -> 1.5 m.
  - Short +-0.3-0.4 m wobbles at s 407.5-447.5, 565, 955 and 2045.
- **Width steps between 50 m bins:** 250->300, 550->600, 850->900, 950->1000, 1150->1200, 1200->1250, 1900->1950,
  2000->2050 and 2100->2150.
- **The declared widening is not real.** The plan widens the island to 7.1-8.0 m over s 1850-2000. The lidar holds it
  at 4.8-5.4 m (bin medians), so the plan is 2.5-2.7 m too wide there.
- **Unclear runs (3+ stations):** s 920-925, 1192.5-1197.5, 1850-1857.5 and 2167.5-2175.
- **Outer curbs with no rise** (a driveway or street mouth, or a flush edge), runs of 3+ stations. Left: s 387.5-397.5,
  1687.5-1697.5 and 2015-2025. Right: s 750-755, 867.5-880 and 1252.5-1257.5.

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

**Widening the section changed two island readings.** It took in more class-2 returns at the old section's edge. At
s 1250 the right face's +- moved 0.039 -> 0.040 m; on the whole run, at s 2187.5 the right face moved 0.067 -> 0.054 m.
Nothing else in the island readings moved.

## Re-run (on the G10, or anywhere with the tiles)

```bash
nice -n 19 ionice -c3 python -I tracks/san-diego-lake-murray/source/expansion/mg_median/mg_median_faces_g10.py \
    <tiles dir> <lm-shrub tool dir> <airoso checkout> <out dir> [--full]   # or MG_TILES / MG_LM_TOOL / MG_AIROSO / MG_OUT
```

The detailed run takes about 35 s and 250 MB; `--full` about 75 s and 480 MB. `--reuse` reads the corridor saved in
`<out dir>/work/` again instead of the tiles. Run on this commit's data: the declared band comes from
`mg_median_correction.json` rows[0].
